"""Run search systems on the test queries and keep one big results table.

Every search method we try (BM25 variants, embeddings, hybrid, ...) is one "system" in
SYSTEMS below. Running systems:

    python -m arxiv_search.evaluate.experiments bm25-baseline          # one system, on dev
    python -m arxiv_search.evaluate.experiments "bm25*"                # every BM25 system
    python -m arxiv_search.evaluate.experiments --tune bm25+stem       # k1/b grid on dev
    python -m arxiv_search.evaluate.experiments bm25-baseline --split test   # finalists only
    python -m arxiv_search.evaluate.experiments --list

For each system:
1. build its index over all 23,304 papers (timed)
2. search every query in the split and keep the top RUN_DEPTH papers (timed)
3. score the rankings with metrics.py
4. save rankings and scores under data/results/<split>/
Then docs/05-results.md is rebuilt from everything saved.

Rule (Decision 26): experiment on dev as much as we like; run only finalists on test.
"""

from __future__ import annotations

import argparse
import fnmatch
import itertools
import json
import time
from dataclasses import dataclass, field
from functools import cache
from typing import Callable

from arxiv_search import config
from arxiv_search.evaluate import metrics
from arxiv_search.evaluate.openai_full import register_systems
from arxiv_search.evaluate.make_queries import load_jsonl
from arxiv_search.search import dense
from arxiv_search.search.bm25 import BM25, DEFAULT_B, DEFAULT_K1
from arxiv_search.search.text import paper_text, tokenize
from arxiv_search.search.hybrid import fuse

Searcher = Callable[[str], list[str]]  # query text -> arxiv_ids, best first
BuildResult = Searcher | tuple[Searcher, dict]

QUERY_TYPES = ("keyword", "question", "paraphrase", "known_item")
MRR = f"mrr@{config.MRR_CUTOFF}"


@dataclass
class System:
    build: Callable[[list[dict]], BuildResult]  # corpus -> search function, optionally with timing info
    description: str
    factors: dict = field(default_factory=dict)  # grid settings, for the factor analysis


# --- BM25 -------------------------------------------------------------------

# How each stemming setting maps onto tokenize()'s options.
STEMMING = {
    "none": {},
    "stem": {"stem": True},  # every word replaced by its stem
    "exact+stems": {"add_stems": True},  # exact word kept, stem added: score = BM25(exact) + BM25(stems)
}

# Decision 29: every combination of these is run (2 × 3 × 2 × 2 = 24 systems).
# The first value of each is "off", i.e. the baseline.
BM25_GRID = {
    "stopwords": [False, True],  # drop Lucene's 33 English stopwords
    "stemming": list(STEMMING),  # none / stem / exact+stems (Snowball English)
    "authors": [False, True],  # append author names to the paper's text
    "title_x2": [False, True],  # write the title twice (title boost)
}


def bm25_index(corpus: list[dict], factors: dict) -> tuple[BM25, Callable[[str], list[str]]]:
    """Build the index for one combination. Returns it with the tokenizer, which must be the
    same for papers and queries (otherwise "models" could never match "models")."""
    options = {"drop_stopwords": factors["stopwords"], **STEMMING[factors["stemming"]]}

    def words(text: str) -> list[str]:
        return tokenize(text, **options)

    texts = [paper_text(p, authors=factors["authors"], title_repeats=2 if factors["title_x2"] else 1)
             for p in corpus]
    index = BM25([words(t) for t in texts], [p["arxiv_id"] for p in corpus],
                 k1=factors.get("k1", DEFAULT_K1), b=factors.get("b", DEFAULT_B))
    return index, words


def bm25_system(factors: dict) -> System:
    def build(corpus: list[dict]) -> Searcher:
        index, words = bm25_index(corpus, factors)
        return lambda query: index.search(words(query), config.RUN_DEPTH)

    on = [name for name, value in factors.items() if name in BM25_GRID and value not in (False, "none")]
    described = ", ".join(f"stemming={factors['stemming']}" if f == "stemming" else f for f in on)
    k1b = f"k1={factors.get('k1', DEFAULT_K1)} b={factors.get('b', DEFAULT_B)}"
    return System(build, f"BM25 ({described or 'no preprocessing'}), {k1b}", factors)


def bm25_name(factors: dict) -> str:
    """bm25-baseline, or e.g. bm25+stop+exact+stems+authors+title2x."""
    parts = []
    if factors["stopwords"]:
        parts.append("stop")
    if factors["stemming"] != "none":
        parts.append(factors["stemming"])
    if factors["authors"]:
        parts.append("authors")
    if factors["title_x2"]:
        parts.append("title2x")
    if "k1" in factors:
        parts.append(f"k1={factors['k1']},b={factors['b']}")
    return "bm25+" + "+".join(parts) if parts else config.BASELINE_SYSTEM


SYSTEMS: dict[str, System] = {}
for values in itertools.product(*BM25_GRID.values()):
    grid_factors = dict(zip(BM25_GRID, values))
    SYSTEMS[bm25_name(grid_factors)] = bm25_system(grid_factors)

# Decision 30: the best grid combination with tuned k1. The k1/b grid on dev picked k1 = 0.8
# for all top-3 systems; b made no clear difference, so it stays at the default 0.75.
BM25_BEST = {"stopwords": False, "stemming": "exact+stems", "authors": True, "title_x2": True,
             "k1": 0.8, "b": 0.75}
SYSTEMS[bm25_name(BM25_BEST)] = bm25_system(BM25_BEST)


# --- Dense (embeddings) -----------------------------------------------------


def dense_system(model_key: str) -> System:
    def build(corpus: list[dict]) -> BuildResult:
        ids = [p["arxiv_id"] for p in corpus]
        vectors, info = dense.paper_vectors(model_key, [paper_text(p) for p in corpus], ids, model_key)
        index = dense.DenseIndex(vectors, ids)
        dense.embed_queries(model_key, ["warm up"])  # load the model now, not during the timed queries

        def search(query: str) -> list[str]:
            return index.search(dense.embed_queries(model_key, [query])[0], config.RUN_DEPTH)

        # Building = embedding every paper, which only happens once; report that time.
        return search, {"build_seconds": info["embed_seconds"]}

    model = config.EMBEDDING_MODELS[model_key]["hf_name"]
    return System(build, f"Dense: {model}, title + abstract, cosine similarity", {"model": model_key})


for model_key in config.EMBEDDING_MODELS:
    SYSTEMS[f"dense-{model_key}"] = dense_system(model_key)


# --- Hybrid: fixed grid, dev only until we select finalists ------------------

HYBRID_GRID = {}
for model_key, weight, (method, c) in itertools.product(
    ("gte-small", "bge-small"), (0.25, 0.5, 0.75),
    (("rrf", 10), ("rrf", 60), ("rrf", 100), ("linear", 60)),
):
    name = f"hybrid-{model_key}+{method}+w={weight}" + (f"+c={c}" if method == "rrf" else "")
    HYBRID_GRID[name] = {"model": model_key, "method": method, "semantic_weight": weight, "c": c}


def hybrid_system(settings: dict) -> System:
    def build(corpus: list[dict]) -> Searcher:
        lexical_built = bm25_system(BM25_BEST).build(corpus)
        semantic_built = dense_system(settings["model"]).build(corpus)
        lexical = lexical_built[0] if isinstance(lexical_built, tuple) else lexical_built
        semantic = semantic_built[0] if isinstance(semantic_built, tuple) else semantic_built

        def search(query: str) -> list[str]:
            return fuse(lexical(query), semantic(query), method=settings["method"],
                        semantic_weight=settings["semantic_weight"], c=settings["c"],
                        depth=config.RUN_DEPTH, k=config.RUN_DEPTH)

        return search

    return System(build, f"Hybrid: best BM25 + {settings['model']}, {settings['method']}",
                  {"hybrid": True, **settings})


for name, settings in HYBRID_GRID.items():
    SYSTEMS[name] = hybrid_system(settings)

register_systems(SYSTEMS, System)


# --- Running ---------------------------------------------------------------


@cache
def load_eval() -> tuple[list[dict], dict, dict, dict]:
    """corpus, queries by id, labels, split. Loaded once, however many systems we run."""
    corpus = load_jsonl(config.PROCESSED_DIR / "corpus.jsonl")
    queries = {q["query_id"]: q for q in load_jsonl(config.EVAL_DIR / "queries.jsonl")}
    labels = json.loads((config.EVAL_DIR / "labels.json").read_text())
    split = json.loads((config.EVAL_DIR / "split.json").read_text())
    return corpus, queries, labels, split


def score(run: dict[str, list[str]]) -> list[dict]:
    """Per-query scores, with each query's type/specificity/category kept next to them."""
    _, queries, labels, _ = load_eval()
    rows = metrics.score_run(run, {qid: labels[qid] for qid in run})
    for row in rows:
        q = queries[row["query_id"]]
        row.update(query_type=q["query_type"], specificity=q["specificity"], category=q["category"])
    return rows


def run_system(name: str, split: str) -> dict:
    """Build, search, score and save one system on one split. Returns its saved summary."""
    system = SYSTEMS[name]
    corpus, queries, _, splits = load_eval()
    query_ids = splits[split]

    start = time.perf_counter()
    built = system.build(corpus)
    build_seconds = time.perf_counter() - start
    # A builder may also return extra info, e.g. dense systems report their one-time embedding time.
    search, extra = built if isinstance(built, tuple) else (built, {})

    start = time.perf_counter()
    run = {qid: search(queries[qid]["query"]) for qid in query_ids}
    ms_per_query = (time.perf_counter() - start) * 1000 / len(query_ids)

    return save_run(name, split, run, build_seconds, ms_per_query, extra)


def save_run(name: str, split: str, run: dict[str, list[str]], build_seconds: float,
             ms_per_query: float, extra: dict) -> dict:
    system = SYSTEMS[name]
    rows = score(run)
    out = config.RESULTS_DIR / split
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}.run.json").write_text(json.dumps(run))
    (out / f"{name}.scores.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    info = {
        "system": name, "description": system.description, "factors": system.factors,
        "split": split, "queries": len(rows), "mrr@10": round(sum(r[MRR] for r in rows) / len(rows), 4),
        "build_seconds": round(build_seconds, 1), "ms_per_query": round(ms_per_query, 1),
    }
    info.update(extra)
    (out / f"{name}.info.json").write_text(json.dumps(info, indent=2))
    return info


def run_hybrid_grid() -> None:
    """Fuse saved dev top-100 lists; never silently use a different candidate depth."""
    _, _, _, splits = load_eval()
    sources = {}
    for name in (bm25_name(BM25_BEST), "dense-gte-small", "dense-bge-small"):
        path = config.RESULTS_DIR / "dev" / f"{name}.run.json"
        run = json.loads(path.read_text())
        if set(run) != set(splits["dev"]) or any(len(v) != config.RUN_DEPTH for v in run.values()):
            raise ValueError(f"{path}: expected every dev query with {config.RUN_DEPTH} candidates")
        sources[name] = run
    lexical = sources[bm25_name(BM25_BEST)]
    for name, settings in HYBRID_GRID.items():
        semantic = sources[f"dense-{settings['model']}"]
        start = time.perf_counter()
        run = {qid: fuse(lexical[qid], semantic[qid], method=settings["method"],
                         semantic_weight=settings["semantic_weight"], c=settings["c"],
                         depth=config.RUN_DEPTH, k=config.RUN_DEPTH) for qid in splits["dev"]}
        elapsed = (time.perf_counter() - start) * 1000 / len(run)
        info = save_run(name, "dev", run, 0, elapsed, {"timing_scope": "fusion_only"})
        print(f"{name}: MRR@10 {info['mrr@10']:.3f}")


# --- Tuning k1 and b (dev only) --------------------------------------------

K1_GRID = [0.4, 0.8, 1.2, 1.6, 2.0, 2.4]
B_GRID = [0.3, 0.5, 0.6, 0.75, 0.9, 1.0]


def tune_bm25(name: str) -> dict:
    """MRR@10 on dev for every (k1, b) in the grid, for one BM25 system.

    The index is built once: k1 and b are only used at query time, so changing them on the
    index is the same as rebuilding it with the new values.
    """
    corpus, queries, _, splits = load_eval()
    index, words = bm25_index(corpus, SYSTEMS[name].factors)
    query_words = {qid: words(queries[qid]["query"]) for qid in splits["dev"]}
    grid = {}
    for k1, b in itertools.product(K1_GRID, B_GRID):
        index.k1, index.b = k1, b
        rows = score({qid: index.search(w, config.RUN_DEPTH) for qid, w in query_words.items()})
        grid[f"{k1},{b}"] = round(sum(r[MRR] for r in rows) / len(rows), 4)
    best = max(grid, key=grid.get)
    result = {"system": name, "metric": MRR, "split": "dev", "mrr_by_k1_b": grid, "best": best,
              "best_mrr": grid[best], "default_mrr": grid[f"{DEFAULT_K1},{DEFAULT_B}"]}
    folder = config.RESULTS_DIR / "dev" / "tuning"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.json").write_text(json.dumps(result, indent=2))
    return result


# --- The results page --------------------------------------------------------

METRIC_COLUMNS = [f"recall@{k}" for k in config.RECALL_KS] + [MRR]


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def load_results(split: str) -> dict[str, tuple[list[dict], dict]]:
    """name -> (per-query scores sorted by query_id, info), for every system run on split."""
    folder = config.RESULTS_DIR / split
    found = {}
    for name in SYSTEMS:
        if (folder / f"{name}.scores.jsonl").exists():
            rows = sorted(load_jsonl(folder / f"{name}.scores.jsonl"), key=lambda r: r["query_id"])
            found[name] = (rows, json.loads((folder / f"{name}.info.json").read_text()))
    return found


def main_table(results: dict) -> str:
    """One row per system, best MRR@10 first."""
    baseline = results.get(config.BASELINE_SYSTEM)
    header = (["System", "R@1", "R@5", "R@10", "R@20", "MRR@10", "Δ MRR vs baseline"]
              + list(QUERY_TYPES) + ["specific", "broad", "Build s", "ms/query"])
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    by_mrr = sorted(results, key=lambda n: -_mean([r[MRR] for r in results[n][0]]))
    for n in by_mrr:
        rows, info = results[n]
        cells = [f"**`{n}`**" if n == config.BASELINE_SYSTEM else f"`{n}`"]
        for m in METRIC_COLUMNS:
            mean, low, high = metrics.bootstrap_ci([r[m] for r in rows])
            cells.append(f"{mean:.3f} [{low:.2f}–{high:.2f}]" if m == MRR else f"{mean:.3f}")
        if baseline is None or n == config.BASELINE_SYSTEM:
            cells.append("—")
        else:
            diff, low, high = metrics.paired_diff_ci([r[MRR] for r in baseline[0]], [r[MRR] for r in rows])
            cells.append(f"{diff:+.3f} [{low:+.2f}, {high:+.2f}]")
        cells += [f"{_mean([r[MRR] for r in rows if r['query_type'] == t]):.3f}" for t in QUERY_TYPES]
        cells += [f"{_mean([r[MRR] for r in rows if r['specificity'] == s]):.3f}" for s in ("specific", "broad")]
        fusion_only = info.get("timing_scope") == "fusion_only"
        cached_query = info.get("timing_scope") == "sequential_search_excludes_offline_query_embedding"
        latency = str(info["ms_per_query"])
        if fusion_only:
            latency += " (fusion only)"
        elif cached_query:
            latency += " (cached vector; embedding API excluded)"
        cells += ["—" if fusion_only else str(info["build_seconds"]),
                  latency]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def factor_analysis(results: dict) -> str | None:
    """Average effect of each BM25 grid factor, over all combinations of the other factors.

    For each query we average MRR@10 over every grid system with the factor on, and over
    every one with it off; the paired difference of those per-query averages (with a 95%
    interval) is the factor's effect. Needs all grid systems to have been run.
    """
    grid = {n: results[n][0] for n in results if set(BM25_GRID) <= set(results[n][1]["factors"])
            and "k1" not in results[n][1]["factors"]}
    if len(grid) < len(list(itertools.product(*BM25_GRID.values()))):
        return None
    factors = {n: results[n][1]["factors"] for n in grid}
    n_queries = len(next(iter(grid.values())))
    query_types = [r["query_type"] for r in next(iter(grid.values()))]

    def per_query_mean(names: list[str]) -> list[float]:
        return [_mean([grid[n][i][MRR] for n in names]) for i in range(n_queries)]

    lines = [
        "| Factor | Setting | Systems | Mean MRR@10 | Δ vs off [95% CI] | "
        + " | ".join(f"Δ {t}" for t in QUERY_TYPES) + " |",
        "|---|---|---|---|---|" + "---|" * len(QUERY_TYPES),
    ]
    for factor, levels in BM25_GRID.items():
        off = per_query_mean([n for n in grid if factors[n][factor] == levels[0]])
        for level in levels:
            names = [n for n in grid if factors[n][factor] == level]
            these = per_query_mean(names)
            if level == levels[0]:
                delta, by_type = "—", ["—"] * len(QUERY_TYPES)
            else:
                d, low, high = metrics.paired_diff_ci(off, these)
                delta = f"{d:+.3f} [{low:+.2f}, {high:+.2f}]"
                by_type = [f"{_mean([b - a for a, b, qt in zip(off, these, query_types) if qt == t]):+.3f}"
                           for t in QUERY_TYPES]
            lines.append(f"| {factor} | {level} | {len(names)} | {_mean(these):.3f} | {delta} | "
                         + " | ".join(by_type) + " |")

    # Two-way tables: does a factor's effect depend on another factor's setting?
    interactions = []
    for f1, f2 in itertools.combinations(BM25_GRID, 2):
        rows = [f"| {f1} ↓ / {f2} → | " + " | ".join(str(v) for v in BM25_GRID[f2]) + " |",
                "|---|" + "---|" * len(BM25_GRID[f2])]
        for v1 in BM25_GRID[f1]:
            cells = []
            for v2 in BM25_GRID[f2]:
                names = [n for n in grid if factors[n][f1] == v1 and factors[n][f2] == v2]
                cells.append(f"{_mean(per_query_mean(names)):.3f}")
            rows.append(f"| {v1} | " + " | ".join(cells) + " |")
        interactions.append("\n".join(rows))

    return "\n".join(lines) + "\n\n**Interactions** (mean MRR@10 for each pair of settings, " \
        "averaged over the other two factors):\n\n" + "\n\n".join(interactions)


def hybrid_comparison(results: dict) -> str | None:
    baseline = results.get(bm25_name(BM25_BEST))
    if baseline is None or not any(n in results for n in HYBRID_GRID):
        return None
    lines = [
        "Best dev MRR row in each model/method group; these are selected on dev, not",
        "independent confirmations. Intervals do not correct for selecting the winners.",
        "Weights are the embedding share (the remainder goes to BM25).",
        "Offline grid timings cover fusion only, excluding both retrieval systems.",
        "",
        "| Model | Method | Embedding weight | c | MRR@10 | R@20 | Δ vs best BM25 [95% CI] |",
        "|---|---|---|---|---|---|---|",
    ]
    for model, method in itertools.product(("gte-small", "bge-small"), ("rrf", "linear")):
        names = [n for n, s in HYBRID_GRID.items()
                 if n in results and s["model"] == model and s["method"] == method]
        if not names:
            continue
        name = max(names, key=lambda n: _mean([r[MRR] for r in results[n][0]]))
        rows = results[name][0]
        settings = HYBRID_GRID[name]
        delta, low, high = metrics.paired_diff_ci(
            [r[MRR] for r in baseline[0]], [r[MRR] for r in rows])
        c = str(settings["c"]) if method == "rrf" else "—"
        lines.append(f"| {model} | {method} | {settings['semantic_weight']} | {c} | "
                     f"{_mean([r[MRR] for r in rows]):.3f} | "
                     f"{_mean([r['recall@20'] for r in rows]):.2f} | "
                     f"{delta:+.3f} [{low:+.2f}, {high:+.2f}] |")
    return "\n".join(lines)


def tuning_tables() -> str | None:
    folder = config.RESULTS_DIR / "dev" / "tuning"
    if not folder.exists():
        return None
    parts = []
    for path in sorted(folder.glob("*.json")):
        t = json.loads(path.read_text())
        lines = [f"**`{t['system']}`**: best k1={t['best'].split(',')[0]}, b={t['best'].split(',')[1]} "
                 f"→ MRR@10 {t['best_mrr']:.3f} (default k1={DEFAULT_K1}, b={DEFAULT_B}: {t['default_mrr']:.3f})",
                 "", "| k1 ↓ / b → | " + " | ".join(str(b) for b in B_GRID) + " |",
                 "|---|" + "---|" * len(B_GRID)]
        for k1 in K1_GRID:
            lines.append(f"| {k1} | " + " | ".join(f"{t['mrr_by_k1_b'][f'{k1},{b}']:.3f}" for b in B_GRID) + " |")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def write_results_doc() -> None:
    parts = [
        "# Results",
        "",
        "*Generated by `python -m arxiv_search.evaluate.experiments`. Don't edit by hand.*",
        "",
        "Each row is one search system, best first. Scores are against each query's source paper:",
        "**R@k** = share of queries whose source paper is in the top k; **MRR@10** = average of",
        "1 ÷ its rank (0 if below 10), with a 95% interval. **Δ vs baseline** is the paired",
        "difference from `bm25-baseline` on the same queries: if its interval excludes 0, the",
        "difference is real. The columns *keyword* to *broad* are MRR@10 within that group (dev:",
        "25 per type, 74 specific, 26 broad). Broad queries have many right answers, so their",
        "scores are a lower bound until the LLM judge grades other papers (nDCG@10 comes then).",
        "",
        "**Careful:** picking the best of many rows on 100 dev queries flatters the winner a",
        "little (winner's curse). The honest score is the finalist's run on test.",
    ]
    dev = load_results("dev")
    parts += ["", "## Dev (100 queries): experiments", "", main_table(dev) if dev else "_Nothing run yet._"]
    hybrid = hybrid_comparison(dev)
    if hybrid:
        parts += ["", "### Hybrid: comparison against best BM25", "", hybrid]

    analysis = factor_analysis(dev)
    if analysis:
        parts += ["", "### BM25: what each technique adds (Decision 29)", "",
                  "Every combination of the four settings below was run (24 systems). Each factor's",
                  "effect is averaged over all combinations of the other three, so it isn't tied to",
                  "one starting point. *Δ by type* columns show who gains and who loses.", "", analysis]
    tuning = tuning_tables()
    if tuning:
        parts += ["", "### BM25: tuning k1 and b on dev", "",
                  "MRR@10 on dev for each (k1, b). k1 = how fast repeated words stop counting;",
                  "b = how much long papers are penalized.", "", tuning]

    test = load_results("test")
    parts += ["", "## Test (300 queries): finalists only", "", main_table(test) if test else "_Nothing run yet._"]
    pilot_report = config.EVAL_DIR / "judge_pilot" / "report.md"
    if pilot_report.exists():
        parts += ["", "## Relevance judge calibration (separate from retrieval scores)", "",
                  pilot_report.read_text(encoding="utf-8").replace("# Judge pilot", "### Judge pilot", 1)]
    embedding_report = config.RESULTS_DIR / "embedding-pilot" / "report.md"
    if embedding_report.exists():
        parts += ["", "## Embedding pilot (reduced corpus; separate benchmark)", "",
                  embedding_report.read_text(encoding="utf-8")]
    graded_report = config.RESULTS_DIR / "graded-dev" / "report.md"
    if graded_report.exists():
        parts += ["", "## Graded full-corpus dev retrieval", "",
                  graded_report.read_text(encoding="utf-8").replace(
                      "# Graded dev retrieval", "### Graded dev retrieval", 1)]
    for folder, title in (("fusion-dev", "Cached OpenAI fusion experiments"),
                          ("fusion-review-dev", "Pre-promotion fusion review"),
                          ("failure-analysis", "Frozen baseline failure analysis")):
        report = config.RESULTS_DIR / folder / "report.md"
        if report.exists():
            parts += ["", f"## {title}", "", report.read_text(encoding="utf-8")]
    (config.PROJECT_ROOT / "docs" / "05-results.md").write_text(
        "\n".join(parts).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run search systems and update docs/05-results.md.")
    parser.add_argument("systems", nargs="*", help="system names or patterns like 'bm25*'")
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--tune", nargs="+", metavar="SYSTEM", help="k1/b grid on dev for these BM25 systems")
    parser.add_argument("--list", action="store_true", help="list every system")
    parser.add_argument("--hybrid-grid", action="store_true", help="fuse saved dev rankings across the fixed hybrid grid")
    args = parser.parse_args()

    if args.hybrid_grid and (args.split != "dev" or args.systems or args.tune):
        parser.error("--hybrid-grid runs on dev only and cannot be combined with systems or --tune")
    if args.hybrid_grid:
        run_hybrid_grid()
    if args.list:
        for name, system in SYSTEMS.items():
            print(f"{name:45} {system.description}")
        return
    names = [n for n in SYSTEMS if any(fnmatch.fnmatchcase(n, p) for p in args.systems)]
    if args.systems and not names:
        parser.error(f"no system matches {args.systems}; see --list")
    for name in names:
        info = run_system(name, args.split)
        print(f"{name:45} MRR@10 {info['mrr@10']:.3f}  build {info['build_seconds']} s")
    for name in args.tune or []:
        t = tune_bm25(name)
        print(f"tuned {name}: best k1,b = {t['best']} → {t['best_mrr']:.3f} (default {t['default_mrr']:.3f})")
    write_results_doc()
    print("Updated docs/05-results.md")


if __name__ == "__main__":
    main()
