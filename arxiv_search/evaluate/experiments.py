"""Run search systems on the test queries and keep one big results table.

Every search method we try (BM25 baseline, BM25 + stemming, embeddings, hybrid, ...) is one
"system" in SYSTEMS below. Running a system:

    python -m arxiv_search.evaluate.experiments bm25-baseline            # on dev (default)
    python -m arxiv_search.evaluate.experiments bm25-baseline --split test

1. builds the system's index over all 23,304 papers (timed)
2. searches every query in the split and keeps the top RUN_DEPTH papers (timed)
3. scores the rankings with metrics.py
4. saves the rankings and scores under data/results/, then rebuilds docs/05-results.md,
   the table comparing every system run so far.

Rule (Decision 26): experiment on dev as much as we like; run only finalists on test.
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Callable

from arxiv_search import config
from arxiv_search.evaluate import metrics
from arxiv_search.evaluate.make_queries import load_jsonl
from arxiv_search.search.bm25 import BM25
from arxiv_search.search.text import paper_text, tokenize

Searcher = Callable[[str], list[str]]  # query text -> arxiv_ids, best first

QUERY_TYPES = ("keyword", "question", "paraphrase", "known_item")


# --- The systems ------------------------------------------------------------
# Each builder takes the corpus and returns a search function.


def bm25_baseline(corpus: list[dict]) -> Searcher:
    """BM25 over title + abstract, lowercase + split on non-letters, k1=1.2, b=0.75."""
    index = BM25([tokenize(paper_text(p)) for p in corpus], [p["arxiv_id"] for p in corpus])
    return lambda query: index.search(tokenize(query), config.RUN_DEPTH)


# name -> (builder, one-line description shown in the results table)
SYSTEMS: dict[str, tuple[Callable[[list[dict]], Searcher], str]] = {
    "bm25-baseline": (bm25_baseline, "BM25, lowercase + split on non-letters, k1=1.2 b=0.75"),
}


# --- Running ---------------------------------------------------------------


def run_system(name: str, split: str) -> dict:
    """Build, search, score and save one system on one split. Returns its saved summary."""
    builder, description = SYSTEMS[name]
    corpus = load_jsonl(config.PROCESSED_DIR / "corpus.jsonl")
    queries = {q["query_id"]: q for q in load_jsonl(config.EVAL_DIR / "queries.jsonl")}
    labels = json.loads((config.EVAL_DIR / "labels.json").read_text())
    query_ids = json.loads((config.EVAL_DIR / "split.json").read_text())[split]

    start = time.perf_counter()
    search = builder(corpus)
    build_seconds = time.perf_counter() - start

    start = time.perf_counter()
    run = {qid: search(queries[qid]["query"]) for qid in query_ids}
    ms_per_query = (time.perf_counter() - start) * 1000 / len(query_ids)

    rows = metrics.score_run(run, {qid: labels[qid] for qid in query_ids})
    for row in rows:  # keep the groups next to the scores, for per-type averages
        q = queries[row["query_id"]]
        row.update(query_type=q["query_type"], specificity=q["specificity"], category=q["category"])

    out = config.RESULTS_DIR / split
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}.run.json").write_text(json.dumps(run))
    (out / f"{name}.scores.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    info = {
        "system": name, "description": description, "split": split, "queries": len(rows),
        "build_seconds": round(build_seconds, 1), "ms_per_query": round(ms_per_query, 1),
    }
    (out / f"{name}.info.json").write_text(json.dumps(info, indent=2))
    return info


# --- The results table -----------------------------------------------------

METRIC_COLUMNS = [f"recall@{k}" for k in config.RECALL_KS] + [f"mrr@{config.MRR_CUTOFF}"]
MRR = f"mrr@{config.MRR_CUTOFF}"


def _mean(rows: list[dict], metric: str) -> float:
    return sum(r[metric] for r in rows) / len(rows) if rows else float("nan")


def split_table(split: str) -> str | None:
    """Markdown table of every system run on this split, or None if none has been run."""
    folder = config.RESULTS_DIR / split
    names = [n for n in SYSTEMS if (folder / f"{n}.scores.jsonl").exists()]
    if not names:
        return None
    scores = {n: load_jsonl(folder / f"{n}.scores.jsonl") for n in names}
    infos = {n: json.loads((folder / f"{n}.info.json").read_text()) for n in names}
    baseline = scores.get(config.BASELINE_SYSTEM)

    header = (["System", "n"] + [m.replace("recall", "R") for m in METRIC_COLUMNS[:-1]] + ["MRR@10"]
              + ["Δ MRR vs baseline"]
              + list(QUERY_TYPES) + ["specific", "broad"]
              + ["Build s", "ms/query"])
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for n in names:
        rows = sorted(scores[n], key=lambda r: r["query_id"])
        cells = [f"`{n}`", str(len(rows))]
        for m in METRIC_COLUMNS:
            mean, low, high = metrics.bootstrap_ci([r[m] for r in rows])
            cells.append(f"{mean:.3f} [{low:.2f}–{high:.2f}]" if m == MRR else f"{mean:.3f}")
        if baseline is None or n == config.BASELINE_SYSTEM:
            cells.append("—")
        else:
            base = sorted(baseline, key=lambda r: r["query_id"])
            diff, low, high = metrics.paired_diff_ci([r[MRR] for r in base], [r[MRR] for r in rows])
            cells.append(f"{diff:+.3f} [{low:+.2f}, {high:+.2f}]")
        cells += [f"{_mean([r for r in rows if r['query_type'] == t], MRR):.3f}" for t in QUERY_TYPES]
        cells += [f"{_mean([r for r in rows if r['specificity'] == s], MRR):.3f}"
                  for s in ("specific", "broad")]
        cells += [str(infos[n]["build_seconds"]), str(infos[n]["ms_per_query"])]
        lines.append("| " + " | ".join(cells) + " |")

    described = "\n".join(f"- `{n}`: {infos[n]['description']}" for n in names)
    return "\n".join(lines) + "\n\n" + described


def write_results_doc() -> None:
    parts = [
        "# Results",
        "",
        "*Generated by `python -m arxiv_search.evaluate.experiments`. Don't edit by hand.*",
        "",
        "Each row is one search system. Scores are against each query's source paper:",
        "**R@k** = share of queries whose source paper is in the top k; **MRR@10** = average of",
        "1 ÷ its rank (0 if below 10), with a 95% interval. **Δ vs baseline** is the paired",
        "difference from `bm25-baseline` on the same queries: if its interval excludes 0, the",
        "difference is real. Broad queries have many right answers, so their scores here are a",
        "lower bound until the LLM judge grades other papers (nDCG@10 comes then).",
        "The columns *keyword* to *broad* are MRR@10 within that group of queries (25 per type on",
        "dev; 74 specific, 26 broad).",
    ]
    for split, title in (("dev", "Dev (100 queries): experiments"), ("test", "Test (300 queries): finalists only")):
        table = split_table(split)
        parts += ["", f"## {title}", "", table or "_Nothing run yet._"]
    (config.PROJECT_ROOT / "docs" / "05-results.md").write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a search system and update the results table.")
    parser.add_argument("system", choices=list(SYSTEMS))
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    args = parser.parse_args()
    info = run_system(args.system, args.split)
    write_results_doc()
    print(json.dumps(info, indent=2))
    print("Table updated: docs/05-results.md")


if __name__ == "__main__":
    main()
