"""Inspect frozen baseline failures offline; never generates or changes labels."""

from __future__ import annotations

import hashlib
import json

from arxiv_search import config
from arxiv_search.evaluate import graded, judge, metrics
from arxiv_search.evaluate.judge_pilot import SHEET_PATH, read_human_grades

DENSE = "dense-openai-large"
HYBRID = "hybrid-openai-large+rrf+w=0.5+c=10"
OUT = config.RESULTS_DIR / "failure-analysis"


def fingerprint(run: dict) -> str:
    return hashlib.sha256(json.dumps(run, sort_keys=True).encode()).hexdigest()


def query_rows(runs: dict, labels: dict, queries: dict) -> list[dict]:
    scores = {
        name: {r["query_id"]: r for r in graded.score_graded(run, labels, queries)}
        for name, run in runs.items()
    }
    rows = []
    for qid, grades in labels.items():
        q = queries[qid]
        dense_score = scores[DENSE][qid]["ndcg@10"]
        hybrid_score = scores[HYBRID][qid]["ndcg@10"]
        rows.append({
            "query_id": qid, "query": q["query"], "query_type": q["query_type"],
            "category": q["category"], "specificity": q["specificity"],
            "overlap_band": "low (<0.5)" if q["overlap"] < 0.5 else "high (>=0.5)",
            "dense_ndcg": dense_score, "hybrid_ndcg": hybrid_score,
            "hybrid_minus_dense": (hybrid_score - dense_score
                                   if dense_score is not None and hybrid_score is not None else None),
            "source_ranks": {
                name: (run[qid].index(q["source_arxiv_id"]) + 1
                       if q["source_arxiv_id"] in run[qid] else None)
                for name, run in runs.items()
            },
            "relevant_in_pool": sum(g >= 1 for g in grades.values()),
        })
    return rows


def segment_report(rows: list[dict]) -> list[str]:
    lines = ["## Dense versus hybrid by segment", "",
             "Paired nDCG difference = hybrid minus dense; exploratory, no multiple-testing "
             "correction. Overlap is query/source word overlap, not a live routing feature.",
             "", "| Group | Segment | nDCG queries / total | Dense | Hybrid | Difference [95% CI] |",
             "|---|---|---|---|---|---|"]
    for field in ("query_type", "specificity", "category", "overlap_band"):
        for value in sorted({r[field] for r in rows}):
            group = [r for r in rows if r[field] == value]
            valid = [r for r in group if r["hybrid_minus_dense"] is not None]
            if not valid:
                lines.append(f"| {field} | {value} | 0/{len(group)} | undefined | undefined | undefined |")
                continue
            diff, low, high = metrics.paired_diff_ci(
                [r["dense_ndcg"] for r in valid], [r["hybrid_ndcg"] for r in valid])
            dense = sum(r["dense_ndcg"] for r in valid) / len(valid)
            hybrid = sum(r["hybrid_ndcg"] for r in valid) / len(valid)
            lines.append(f"| {field} | {value} | {len(valid)}/{len(group)} | {dense:.3f} | "
                         f"{hybrid:.3f} | {diff:+.3f} [{low:+.3f}, {high:+.3f}] |")
    return lines


def main() -> None:
    snapshot_path = graded.OUT / "labels.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if not snapshot["complete"]:
        raise ValueError("Failure analysis requires a complete frozen graded snapshot")
    if snapshot["rubric_version"] != judge.RUBRIC_VERSION:
        raise ValueError("Rubric changed since snapshot")
    if snapshot["human_workbook_sha256"] != hashlib.sha256(SHEET_PATH.read_bytes()).hexdigest():
        raise ValueError("Human workbook changed since snapshot")
    papers, queries, split = judge.load_inputs()
    qids = sorted(split["dev"])
    runs = graded.load_runs(graded.SYSTEMS, qids, papers)
    if set(snapshot["labels"]) != set(qids):
        raise ValueError("Snapshot does not contain exactly the dev queries")
    for name, run in runs.items():
        if snapshot["run_fingerprints"][name] != fingerprint(run):
            raise ValueError(f"{name}: ranking changed since snapshot")
        if any(p not in snapshot["labels"][q] for q in qids for p in run[q][:10]):
            raise ValueError(f"{name}: incomplete top-10 judgments")
    labels = snapshot["labels"]
    rows = query_rows(runs, labels, queries)
    valid = [r for r in rows if r["hybrid_minus_dense"] is not None]
    buckets = {
        "largest_hybrid_regressions": sorted(valid, key=lambda r: (r["hybrid_minus_dense"], r["query_id"]))[:5],
        "largest_hybrid_gains": sorted(valid, key=lambda r: (-r["hybrid_minus_dense"], r["query_id"]))[:5],
        "lowest_hybrid_ndcg": sorted(valid, key=lambda r: (r["hybrid_ndcg"], r["query_id"]))[:5],
    }
    cached = judge.load_judgments(snapshot["judge"])
    human = read_human_grades()
    cases = {}
    for row in (r for group in buckets.values() for r in group):
        qid = row["query_id"]
        evidence = []
        for pid in dict.fromkeys(runs[HYBRID][qid][:10] + runs[DENSE][qid][:10]):
            paper = papers[pid]
            llm = cached.get(judge.pair_key(snapshot["judge"], queries[qid]["query"], paper))
            evidence.append({
                "arxiv_id": pid, "title": paper["title"], "abstract": paper["abstract"],
                "grade": labels[qid][pid],
                "provenance": "human" if (qid, pid) in human else snapshot["judge"],
                "judge_reason": llm["reason"] if llm else None,
                "ranks": {name: (run[qid].index(pid) + 1 if pid in run[qid] else None)
                          for name, run in runs.items()},
            })
        cases[qid] = {**row, "papers": evidence}
    lines = ["# Frozen baseline failure analysis", "",
             f"Judge `{snapshot['judge']}`, rubric `{snapshot['rubric_version']}`. "
             "100 dev queries; no API calls or label changes.",
             "Cases are diagnostic leads, not proven causes. Read full abstracts and label "
             "provenance in cases.json. A judge reason is not ground truth.", ""]
    lines += segment_report(rows)
    for name, group in buckets.items():
        lines += ["", f"## {name.replace('_', ' ')}", "",
                  "| Query ID | Query | Dense nDCG | Hybrid nDCG | Difference |",
                  "|---|---|---|---|---|"]
        for r in group:
            text = r["query"].replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {r['query_id']} | {text} | {r['dense_ndcg']:.3f} | "
                         f"{r['hybrid_ndcg']:.3f} | {r['hybrid_minus_dense']:+.3f} |")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "queries.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    (OUT / "cases.json").write_text(json.dumps({
        "snapshot_sha256": hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
        "buckets": {name: [r["query_id"] for r in group] for name, group in buckets.items()},
        "cases": cases,
    }, indent=2), encoding="utf-8")
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
