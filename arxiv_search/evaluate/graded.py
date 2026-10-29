"""Score dev retrieval with cached Gemma relevance labels and human overrides.

python -m arxiv_search.evaluate.graded             # no API calls; publish coverage
python -m arxiv_search.evaluate.graded --label --max-calls 20

Source-paper MRR/recall stay separate in experiments.py. This report uses graded
relevance and a shared pool of seven finalists, not the held-out test queries.
"""

from __future__ import annotations

import argparse
import hashlib
import json

from arxiv_search import config
from arxiv_search.evaluate import judge, metrics
from arxiv_search.evaluate.judge_pilot import SHEET_PATH, read_human_grades

SYSTEMS = [
    *config.JUDGE_POOL_SYSTEMS,
    "dense-openai-large",
    "hybrid-openai-large+rrf+w=0.5+c=10",
]
OUT = config.RESULTS_DIR / "graded-dev"


def load_runs(names: list[str], qids: list[str], papers: dict) -> dict:
    runs = {}
    for name in names:
        path = config.RESULTS_DIR / "dev" / f"{name}.run.json"
        run = json.loads(path.read_text(encoding="utf-8"))
        if set(run) != set(qids):
            raise ValueError(f"{name}: expected exactly the dev query IDs")
        for qid, ids in run.items():
            if len(ids) < config.NDCG_K or len(ids) != len(set(ids)) or set(ids) - set(papers):
                raise ValueError(f"{name}/{qid}: incomplete, duplicate or unknown paper IDs")
        runs[name] = run
    return runs


def pooled_pairs(runs: dict, qids: list[str], depth: int = config.NDCG_K) -> dict:
    return {q: list(dict.fromkeys(p for run in runs.values() for p in run[q][:depth]))
            for q in qids}


def merged_labels(pairs: dict, queries: dict, papers: dict, human: dict) -> tuple[dict, int]:
    labels = judge.grades_for("gemma-31b", pairs, queries, papers)
    for qid in pairs:
        labels.setdefault(qid, {})
    overrides = 0
    for (qid, paper), grade in human.items():
        if qid in pairs:
            if paper not in papers or grade not in (0, 1, 2):
                raise ValueError("Invalid human label")
            labels[qid][paper] = grade
            overrides += 1
    return labels, overrides


def score_graded(run: dict, labels: dict, queries: dict, k: int = config.NDCG_K) -> list[dict]:
    """Unjudged gains count as zero. Precision always divides by k, not list length."""
    rows = []
    for qid, grades in labels.items():
        ranked = run.get(qid, [])
        rows.append({
            "query_id": qid, "query_type": queries[qid]["query_type"],
            f"ndcg@{k}": metrics.ndcg_at_k(ranked, grades, k),
            f"precision@{k}": sum(grades.get(p, 0) >= 1 for p in ranked[:k]) / k,
            f"judged@{k}": metrics.judged_at_k(ranked, grades, k),
        })
    return rows


def summarize_rows(rows: list[dict], field: str) -> str:
    values = [r[field] for r in rows if r[field] is not None]
    if not values:
        return "undefined (n=0)"
    mean, low, high = metrics.bootstrap_ci(values)
    return f"{mean:.3f} [{low:.3f}, {high:.3f}]"


def publish(runs: dict, labels: dict, pairs: dict, queries: dict, overrides: int) -> str:
    OUT.mkdir(parents=True, exist_ok=True)
    k = config.NDCG_K
    total = sum(len(p) for p in pairs.values())
    covered = sum(p in labels[q] for q, ids in pairs.items() for p in ids)
    snapshot = {"judge": "gemma-31b", "rubric_version": judge.RUBRIC_VERSION,
                "systems": list(runs), "depth": k, "query_ids": list(pairs),
                "pool_pairs": total, "pool_judged": covered, "human_overrides": overrides,
                "human_workbook_sha256": hashlib.sha256(SHEET_PATH.read_bytes()).hexdigest(),
                "labels": labels,
                "run_fingerprints": {name: hashlib.sha256(json.dumps(run, sort_keys=True).encode()).hexdigest()
                                     for name, run in runs.items()}}
    (OUT / "labels.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    all_rows = {}
    lines = ["# Graded dev retrieval", "",
             f"Judge: Gemma; rubric `{judge.RUBRIC_VERSION}`. {len(pairs)} dev queries, "
             f"{covered}/{total} pooled pairs judged; {overrides} human pair labels take priority.",
             "", "**Calibration limitation:** one person's 100 pilot labels, no fresh-human "
             "validation. Gemma also wrote the queries. No held-out test scores here.",
             "", "**Metric definitions:** linear-gain nDCG@10; P@10 counts grades 1 and 2 as "
             "relevant; unjudged papers count as zero. Ideal DCG uses the same pooled labels "
             "plus human overrides for every system. nDCG is undefined if no relevant label "
             "exists; the nDCG n column shows how many queries are included. P@10 and judged@10 "
             "include all dev queries.",
             "", "**INCOMPLETE / PROVISIONAL: do not rank systems by these scores until "
             "all compared top-10 lists are judged.**" if covered < total else
             "", "",
             "| System | nDCG@10 [95% CI] | nDCG n | P@10 [95% CI] | judged@10 |",
             "|---|---|---|---|---|"]
    for name, run in runs.items():
        rows = score_graded(run, labels, queries)
        all_rows[name] = rows
        (OUT / f"{name}.scores.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        n = sum(r[f"ndcg@{k}"] is not None for r in rows)
        judged = sum(r[f"judged@{k}"] for r in rows) / len(rows)
        lines.append(f"| `{name}` | {summarize_rows(rows, f'ndcg@{k}')} | {n}/{len(rows)} | "
                     f"{summarize_rows(rows, f'precision@{k}')} | {judged:.1%} |")
    lines += ["", "## By query type", "",
              "| System | Type | Queries | nDCG@10 [95% CI] | P@10 [95% CI] | judged@10 |",
              "|---|---|---|---|---|---|"]
    for name, rows in all_rows.items():
        for kind in sorted({r["query_type"] for r in rows}):
            group = [r for r in rows if r["query_type"] == kind]
            coverage = sum(r[f"judged@{k}"] for r in group) / len(group)
            lines.append(f"| `{name}` | {kind} | {len(group)} | "
                         f"{summarize_rows(group, f'ndcg@{k}')} | "
                         f"{summarize_rows(group, f'precision@{k}')} | {coverage:.1%} |")
    report = "\n".join(lines).rstrip() + "\n"
    (OUT / "report.md").write_text(report, encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", action="store_true", help="make Gemma calls for missing pairs")
    parser.add_argument("--max-calls", type=int, default=20, help="successful batches per invocation")
    args = parser.parse_args()
    if args.max_calls < 0:
        parser.error("--max-calls must be nonnegative")
    papers, queries, split = judge.load_inputs()
    qids = sorted(split["dev"])
    runs = load_runs(SYSTEMS, qids, papers)
    pairs = pooled_pairs(runs, qids)
    human = read_human_grades()
    # Human labels already override the judge, so don't spend calls regrading them.
    missing_human = {q: [p for p in ids if (q, p) not in human] for q, ids in pairs.items()}
    try:
        if args.label:
            print(judge.judge_pairs("gemma-31b", missing_human, queries, papers,
                                    max_calls=args.max_calls), flush=True)
    finally:
        labels, overrides = merged_labels(pairs, queries, papers, human)
        print(publish(runs, labels, pairs, queries, overrides))
        from arxiv_search.evaluate.experiments import write_results_doc
        write_results_doc()


if __name__ == "__main__":
    main()
