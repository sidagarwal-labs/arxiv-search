"""Frozen dev cross-encoder experiment; CPU inference, no paid or judging API.

python -m arxiv_search.evaluate.cross_encoder_experiment
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import time
from pathlib import Path

import numpy as np

from arxiv_search import config
from arxiv_search.evaluate import fusion_experiment as fusion, judge, results_catalog as catalog
from arxiv_search.evaluate import openai_full as full
from arxiv_search.evaluate.rank_score_experiment import screen
from arxiv_search.evaluate.score_fusion_experiment import summarize
from arxiv_search.search.rank_score import rescore_shortlist
from arxiv_search.search.rerank import rerank_pool, rerank_prefix
from arxiv_search.search.text import paper_text

MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2"
REVISION = "233902d25c440f23af6f7d6e94d2946bac0bee0a"
OUT = config.RESULTS_DIR / "cross-encoder-dev"
MAX_LENGTH = 512
BASELINE = "fusion-shortlist+a=1+d=500"
SETTINGS = {
    **{f"cross-minilm-l6+pool=baseline+d={d}": {"pool": "baseline", "depth": d}
       for d in (10, 30, 100)},
    "cross-minilm-l6+pool=union100+w=1": {"pool": "union100", "cross_weight": 1.0},
    "cross-minilm-l6+pool=union100+w=0.5": {"pool": "union100", "cross_weight": 0.5},
}


def plan() -> dict:
    return {
        "hypothesis": "Query-document interaction rejects partial intent matches and promotes "
                      "relevant candidates that global lexical/semantic scores miss.",
        "baseline": BASELINE,
        "model": MODEL, "revision": REVISION, "license": "Apache-2.0",
        "training_domain": "MS MARCO passage ranking; not tuned on this dev set",
        "primary_metric": "ndcg@10", "settings": SETTINGS,
        "input": "query paired with title + abstract; no authors or labels",
        "pool": "Current baseline top100, then lexical top100, then semantic top100; "
                "deduplicated in that order. Never inject the source paper.",
        "inference": {"device": "cpu", "dtype": "float32", "max_length": MAX_LENGTH,
                      "truncation": "only_second", "output": "raw logit; not a probability"},
        "blend": "50/50 RRF c30 of cross-encoder pool ranking and frozen baseline top100; "
                 "absent baseline papers contribute zero",
        "screen": [
            "Both top10s fully judged; positive paired nDCG lower CI endpoint",
            "Source Recall10/20 no lower; no individual known-item rank regression",
            "No query-type nDCG mean loss; grade0 first results do not increase",
        ],
        "scope": "100 dev queries only; held-out test untouched; exploratory after dev tuning",
        "paid_calls": False, "automatic_promotion": False,
    }


def freeze(path: Path, value: dict) -> None:
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != value:
            raise ValueError(f"{path}: frozen inputs or plan changed; use a new experiment identity")
    else:
        fusion._write_json(path, value)


def candidate_pool(baseline: list[str], lexical: list[str], semantic: list[str]) -> list[str]:
    for ranking in (baseline, lexical, semantic):
        if len(ranking) < 100 or len(ranking) != len(set(ranking)):
            raise ValueError("Expected unique top100 retrieval inputs")
    return list(dict.fromkeys(baseline[:100] + lexical[:100] + semantic[:100]))


def cache_key(query: str, pool: list[str], papers: dict) -> str:
    return fusion.fingerprint({
        "model": MODEL, "revision": REVISION, "max_length": MAX_LENGTH,
        "dtype": "float32", "truncation": "only_second", "query": query,
        "papers": [[p, paper_text(papers[p])] for p in pool],
    })


def read_scores(path: Path, expected: str, pool: list[str]) -> dict | None:
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if value["input_sha256"] != expected:
        raise ValueError(f"{path}: cached cross-encoder inputs changed")
    scores = value["scores"]
    if (set(scores) != set(pool) or any(type(s) not in (int, float)
                                   or not np.isfinite(s) for s in scores.values())
            or value["pairs"] != len(pool)):
        raise ValueError(f"{path}: invalid or incomplete cross-encoder cache")
    return value


class CpuScorer:
    def __init__(self, threads: int):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        torch.set_num_threads(threads)
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(
            MODEL, revision=REVISION, trust_remote_code=False)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            MODEL, revision=REVISION, trust_remote_code=False,
            use_safetensors=True, dtype=torch.float32).to("cpu").eval()
        self.versions = {p: importlib.metadata.version(p)
                         for p in ("torch", "transformers", "tokenizers")}

    def score(self, query: str, texts: list[str], batch_size: int) -> tuple[list[float], int]:
        scores: list[float] = []
        truncated = 0
        query_length = len(self.tokenizer.encode(query, add_special_tokens=False))
        if query_length + 3 >= MAX_LENGTH:
            raise ValueError("Query exceeds pair budget; refusing to truncate the query")
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            lengths = self.tokenizer(batch, add_special_tokens=False, truncation=False,
                                     verbose=False)["input_ids"]
            truncated += sum(query_length + len(ids) + 3 > MAX_LENGTH for ids in lengths)
            tokens = self.tokenizer(
                [query] * len(batch), batch, padding=True, truncation="only_second",
                max_length=MAX_LENGTH, return_tensors="pt")
            with self.torch.inference_mode():
                logits = self.model(**tokens).logits.detach().cpu().numpy()
            if logits.shape != (len(batch), 1) or not np.isfinite(logits).all():
                raise ValueError("Invalid cross-encoder outputs")
            scores.extend(float(v) for v in logits[:, 0])
        return scores, truncated


def build_runs(base: dict, pools: dict, scores: dict) -> dict:
    if set(base) != set(pools) or set(base) != set(scores):
        raise ValueError("Baseline, pool and score query IDs differ")
    return {
        name: {
            q: (rerank_prefix(base[q], scores[q], opts["depth"])
                if opts["pool"] == "baseline" else
                rerank_pool(pools[q], scores[q], base[q], cross_weight=opts["cross_weight"]))
            for q in base
        } for name, opts in SETTINGS.items()
    }


def report_runs(out: Path, runs: dict, snapshot: dict, papers: dict, queries: dict,
                qids: list[str], baseline: str, inference: dict) -> dict:
    entries = {n: {"run": r, "paths": [], "metadata": {}} for n, r in runs.items()}
    results = catalog.score_catalog(entries, snapshot, papers, queries, qids, baseline)
    rows = {name: r["per_query"] for name, r in results.items()}
    summary = summarize(rows, baseline)
    labels = snapshot["labels"]
    missing = {q: sorted({p for r in runs.values() for p in r[q][:10]} - set(labels[q]))
               for q in qids}
    screens = {
        n: screen(results[n], results[baseline], runs[n], runs[baseline], queries, labels)
        for n in runs if n != baseline
    }
    cases = {}
    for n, check in screens.items():
        source_rows = summary[n]["all"]["source_mrr@10"]["paired_vs_working"]
        differences = source_rows["per_query_difference"]
        selected = set(sorted(differences, key=lambda q: (differences[q], q))[:5])
        selected.update(sorted(differences, key=lambda q: (-differences[q], q))[:5])
        selected.update(check["lost_source_top10"])
        selected.update(check["gained_source_top10"])
        selected.update(check["known_item_rank_regressions"])
        for q in sorted(selected):
            target = queries[q]["source_arxiv_id"]
            pids = list(dict.fromkeys(runs[baseline][q][:10] + runs[n][q][:10] + [target]))
            cases.setdefault(q, {"query": queries[q], "systems": {}})["systems"][n] = {
                "source_ranks": {
                    system: run[q].index(target) + 1 if target in run[q] else None
                    for system, run in runs.items()},
                "papers": [
                    {"arxiv_id": p, "title": papers[p]["title"], "abstract": papers[p]["abstract"],
                     "grade": labels[q].get(p),
                     "baseline_rank": runs[baseline][q].index(p) + 1 if p in runs[baseline][q] else None,
                     "candidate_rank": runs[n][q].index(p) + 1 if p in runs[n][q] else None}
                    for p in pids],
            }
    report = {
        "baseline": baseline, "promoted": False, "api_calls": 0,
        "summary": summary, "systems": results, "screens": screens,
        "missing": missing, "missing_pairs": sum(map(len, missing.values())),
        "query_ids": qids, "inference": inference,
        "label_snapshot_sha256": fusion.fingerprint(snapshot),
        "run_fingerprints": {n: fusion.fingerprint(r) for n, r in runs.items()},
    }
    fusion._write_json(out / "report.json", report)
    fusion._write_json(out / "cases.json", cases)
    lines = [
        "# Local cross-encoder: bounded dev experiment", "",
        f"Model: `{MODEL}` at `{REVISION}` (Apache-2.0). MS MARCO passage ranker, "
        "not specifically fine-tuned here for scientific abstracts or these dev queries. CPU float32, "
        "512 tokens per query/document pair, preserve query and truncate document only. "
        "Scores are raw logits, not calibrated probabilities.", "",
        f"Frozen baseline: `{baseline}`. Five settings fixed before outcomes; no promotion. "
        "Baseline-prefix depth10 isolates ordering; depth30/100 and union100 can replace "
        "the top10. Union100 is each retriever's top100, plus baseline100. "
        "50/50 blend uses RRF c30, not averaged logits and cosine scores.", "",
        f"Missing judgments across new top10s: **{report['missing_pairs']}**. "
        "Unjudged is not irrelevant. Incomplete nDCG/P10 are diagnostic values treating "
        "missing gains as zero under the current frozen pool; not ranked or used for promotion. "
        "Adding labels can also revise ideal DCG, so these are not bounds on future nDCG. "
        "Graded paired intervals are withheld until coverage is complete; source "
        "metrics and their paired intervals remain valid.", "",
        "| System | nDCG10 (diagnostic if incomplete) | P10 | Judged10 | Source MRR10 | R10 | R20 | Coverage |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for n, result in results.items():
        values = [result["all"][f]["mean"] for f in (
            "ndcg@10", "precision@10", "judged@10", "source_mrr@10",
            "source_recall@10", "source_recall@20")]
        lines.append(f"| `{n}` | " + " | ".join(
            "undefined" if v is None else f"{v:.4f}" for v in values)
            + f" | {'fully judged' if result['top10_fully_judged'] else 'PROVISIONAL'} |")
    lines += [
        "", "## Source metrics by segment", "",
        "| System | Segment | Source MRR10 | R10 | R20 |",
        "|---|---|---|---|---|",
    ]
    for n in runs:
        for kind in catalog.QUERY_TYPES:
            group = summary[n][kind]
            lines.append(f"| `{n}` | {kind} | " + " | ".join(
                f"{group[f]['mean']:.4f}" for f in (
                    "source_mrr@10", "source_recall@10", "source_recall@20")) + " |")
    lines += [
        "", "## Paired comparisons and guardrails", "",
        "Differences are candidate minus frozen baseline; exploratory query-bootstrap "
        "95% intervals, conditional on labels and not adjusted for repeated dev tuning.", "",
        "| System | nDCG delta [95% CI] | Source MRR delta [95% CI] | Source top10 losses / gains | Known-item regressions | Screen |",
        "|---|---|---|---|---|---|",
    ]
    for n, check in screens.items():
        comparisons = []
        for field in ("ndcg@10", "source_mrr@10"):
            paired = summary[n]["all"][field]["paired_vs_working"]
            comparisons.append("withheld: incomplete judgments" if paired is None else
                               f"{paired['difference']:+.4f} "
                               f"[{paired['ci95'][0]:+.4f}, {paired['ci95'][1]:+.4f}]")
        lines.append(
            f"| `{n}` | " + " | ".join(comparisons) + " | "
            f"{len(check['lost_source_top10'])} / {len(check['gained_source_top10'])} | "
            f"{len(check['known_item_rank_regressions'])} | "
            f"{'PASS' if check['passes'] else 'not passed'} |")
    lines += [
        "", "## Original inference workload", "",
        f"- Pairs: {inference['pairs']}; "
        f"aggregate per-query seconds: {inference['seconds']:.1f}.",
        f"- Documents truncated at the pair token limit: "
        f"{inference['truncated_documents']}.",
    ]
    lines += [
        "", "## Reproducibility", "",
        "- `preregistration.json` and `input-provenance.json` freeze settings and inputs.",
        "- Per-query `score-cache` files validate query/text/model fingerprints and complete "
        "candidate membership. Delete a specific damaged cache only deliberately; mismatches fail.",
        "- Repeated runs reuse cached logits; no remote inference, paid embeddings or judging.",
        "- `report.json`: paired bootstrap intervals, coverage, screening and per-query metrics.",
        "- `cases.json`: source-rank wins/losses and top10 paper evidence, with missing grades explicit.",
        "- Wall time includes tokenization and CPU inference, excludes model loading; it is an "
        "offline throughput measurement, not production request latency or a GPU benchmark.",
        "- Broad-query source recall is only a single-target proxy. Dev intervals are exploratory; "
        "held-out test and human overrides remain untouched.",
    ]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args(argv)
    if not 1 <= args.threads <= 12 or not 1 <= args.batch_size <= 128:
        parser.error("threads must be 1..12 and batch size 1..128")
    OUT.mkdir(parents=True, exist_ok=True)
    freeze(OUT / "preregistration.json", plan())
    papers, queries, split = judge.load_inputs()
    qids = sorted(split["dev"])
    if len(qids) != 100 or set(qids) & set(split["test"]):
        raise ValueError("Expected 100 dev queries and disjoint held-out test")
    source = config.RESULTS_DIR / "score-fusion-dev"
    parent_report = json.loads((source / "report.json").read_text(encoding="utf-8"))
    provenance = parent_report["provenance"]
    if (provenance["paper_text_sha256"] != full.fingerprint([paper_text(p) for p in papers.values()])
            or provenance["query_text_sha256"] != full.fingerprint([queries[q]["query"] for q in qids])):
        raise ValueError("Current corpus/query texts differ from frozen retrieval inputs")
    input_path = source / "input-scores.json"
    inputs = json.loads(input_path.read_text(encoding="utf-8"))
    base_path = config.RESULTS_DIR / "shortlist-score-dev" / f"{BASELINE}.run.json"
    base = json.loads(base_path.read_text(encoding="utf-8"))
    if set(inputs) != set(qids) or set(base) != set(qids):
        raise ValueError("Inputs must contain exactly dev queries")
    for q in qids:
        s = inputs[q]
        if rescore_shortlist(dict(s["lexical"]), dict(s["semantic"]),
                             score_fraction=1.0, depth=500, score_semantic_weight=.75,
                             shortlist_size=10, k=100) != base[q]:
            raise ValueError(f"{q}: frozen baseline no longer reproduces exactly")
    pools = {q: candidate_pool(base[q], list(dict(inputs[q]["lexical"])),
                              list(dict(inputs[q]["semantic"]))) for q in qids}
    for q, pool in pools.items():
        if set(pool) - set(papers):
            raise ValueError(f"{q}: unknown candidate paper")
    snapshot_path, raw_snapshot, snapshot, _ = catalog.load_snapshot(config.RESULTS_DIR)
    if not snapshot["complete"]:
        raise ValueError("Expected a complete frozen parent snapshot")
    keys = {q: cache_key(queries[q]["query"], pools[q], papers) for q in qids}
    provenance = {
        "baseline_sha256": hashlib.sha256(base_path.read_bytes()).hexdigest(),
        "retrieval_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "label_snapshot": snapshot_path.relative_to(config.RESULTS_DIR).as_posix(),
        "label_bytes_sha256": hashlib.sha256(raw_snapshot).hexdigest(),
        "query_candidate_text_keys": keys, "query_ids": qids,
        "candidate_pool_sha256": fusion.fingerprint(pools),
    }
    freeze(OUT / "input-provenance.json", provenance)
    fusion._write_json(OUT / "candidate-pools.json", pools)
    cache_dir = OUT / "score-cache"
    cache_dir.mkdir(exist_ok=True)
    scorer = None
    cached = {}
    for i, q in enumerate(qids, 1):
        path = cache_dir / f"{q}.json"
        value = read_scores(path, keys[q], pools[q])
        if value is None:
            if scorer is None:
                scorer = CpuScorer(args.threads)
            start = time.perf_counter()
            values, truncated = scorer.score(
                queries[q]["query"], [paper_text(papers[p]) for p in pools[q]], args.batch_size)
            value = {
                "input_sha256": keys[q], "scores": dict(zip(pools[q], values)),
                "pairs": len(values), "truncated_documents": truncated,
                "seconds": time.perf_counter() - start, "versions": scorer.versions,
                "threads": args.threads, "batch_size": args.batch_size,
            }
            temp = path.with_suffix(".tmp")
            fusion._write_json(temp, value)
            temp.replace(path)
        cached[q] = value
        print(f"{i}/{len(qids)} {q}: {value['pairs']} pairs, "
              f"{value['seconds']:.1f}s (original inference)", flush=True)
    scores = {q: v["scores"] for q, v in cached.items()}
    runs = {BASELINE: base, **build_runs(base, pools, scores)}
    for name, run in runs.items():
        fusion.validate_run(name, run, qids, papers, exact_depth=100)
        fusion._write_json(OUT / f"{name}.run.json", run)
    inference = {
        "pairs": sum(v["pairs"] for v in cached.values()),
        "seconds": sum(v["seconds"] for v in cached.values()),
        "truncated_documents": sum(v["truncated_documents"] for v in cached.values()),
        "device": "cpu", "model": MODEL, "revision": REVISION,
        "execution_settings": {q: {k: v[k] for k in ("versions", "threads", "batch_size")}
                               for q, v in cached.items()},
    }
    report = report_runs(OUT, runs, snapshot, papers, queries, qids,
                         BASELINE, inference)
    print(f"Completed {len(SETTINGS)} settings; {report['missing_pairs']} missing judgments; "
          f"{inference['pairs']} local pairs; {inference['seconds']:.1f}s CPU inference; "
          "zero paid calls; baseline unchanged.", flush=True)


if __name__ == "__main__":
    main()
