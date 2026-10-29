"""Review cached fusion finalists without labeling, test access, or promotion.

python -m arxiv_search.evaluate.fusion_review
"""

from __future__ import annotations

import hashlib
import json

from arxiv_search import config
from arxiv_search.evaluate import fusion_experiment as fusion, graded, judge, metrics
from arxiv_search.search.hybrid import fuse

CANDIDATE = "fusion-rrf+w=0.55+d=100+c=30"
ALTERNATIVE = "fusion-rrf+w=0.6+d=100+c=60"
PREVIOUS = "fusion-rrf+w=0.75+d=100+c=100"
OUT = config.RESULTS_DIR / "fusion-review-dev"


def rank(ids: list[str], paper: str) -> int | None:
    return ids.index(paper) + 1 if paper in ids else None


def validate_snapshot(snapshot: dict, runs: dict, qids: list[str]) -> None:
    if not snapshot["complete"]:
        raise ValueError("Review requires a complete frozen label snapshot")
    if snapshot["rubric_version"] != judge.RUBRIC_VERSION:
        raise ValueError("Rubric changed since snapshot")
    if snapshot["human_workbook_sha256"] != hashlib.sha256(graded.SHEET_PATH.read_bytes()).hexdigest():
        raise ValueError("Human workbook changed since snapshot")
    if set(snapshot["labels"]) != set(qids) or set(snapshot["query_ids"]) != set(qids):
        raise ValueError("Snapshot must contain exactly the dev queries")
    for name in (fusion.BASELINE, PREVIOUS, fusion.LEXICAL, fusion.SEMANTIC):
        if snapshot["run_fingerprints"][name] != fusion.fingerprint(runs[name]):
            raise ValueError(f"{name}: ranking changed since snapshot")
    for name, run in runs.items():
        for qid, ids in run.items():
            if any(p not in snapshot["labels"][qid] for p in ids[:config.NDCG_K]):
                raise ValueError(f"{name}/{qid}: unjudged top-10 pair; review withheld")


def score(runs: dict, labels: dict, queries: dict) -> dict:
    rows = {}
    for name, run in runs.items():
        rows[name] = graded.score_graded(run, labels, queries)
        for row in rows[name]:
            qid = row["query_id"]
            target = {queries[qid]["source_arxiv_id"]: 2}
            row["source_mrr@10"] = metrics.reciprocal_rank(run[qid], target, cutoff=10)
            for k in (1, 5, 10, 20):
                row[f"source_recall@{k}"] = metrics.recall_at_k(run[qid], target, k)
    return rows


def comparisons(rows: dict) -> dict:
    result = {}
    kinds = ["all", *sorted({r["query_type"] for r in rows[CANDIDATE]})]
    fields = [k for k in rows[CANDIDATE][0] if k not in ("query_id", "query_type")]
    for control in (fusion.BASELINE, PREVIOUS, ALTERNATIVE):
        result[control] = {}
        for kind in kinds:
            left = [r for r in rows[control] if kind == "all" or r["query_type"] == kind]
            right = [r for r in rows[CANDIDATE] if kind == "all" or r["query_type"] == kind]
            result[control][kind] = {field: fusion.paired_rows(left, right, field)
                                     for field in fields}
    return result


def main() -> None:
    snapshot_path = fusion.OUT / "labels.json"
    raw = snapshot_path.read_bytes()
    snapshot = json.loads(raw)
    papers, queries, split = judge.load_inputs()
    qids = sorted(split["dev"])
    if set(qids) & set(split["test"]):
        raise ValueError("Dev/test query overlap")
    sources, _, provenance = fusion.prepare(papers, qids)
    runs = {fusion.BASELINE: sources[fusion.BASELINE], PREVIOUS: sources[PREVIOUS]}
    settings = {
        CANDIDATE: dict(semantic_weight=0.55, c=30, depth=100, k=100),
        ALTERNATIVE: dict(semantic_weight=0.6, c=60, depth=100, k=100),
    }
    for name, options in settings.items():
        runs[name] = {q: fuse(sources[fusion.LEXICAL][q], sources[fusion.SEMANTIC][q],
                              **options) for q in qids}
        fusion.validate_run(name, runs[name], qids, papers, exact_depth=100)
    validate_snapshot(snapshot, {**runs, fusion.LEXICAL: sources[fusion.LEXICAL],
                                fusion.SEMANTIC: sources[fusion.SEMANTIC]}, qids)
    labels = snapshot["labels"]
    rows = score(runs, labels, queries)
    paired = comparisons(rows)
    summary = fusion.summarize(rows, complete=True)
    buckets = {}
    for control in paired:
        for field in ("ndcg@10", "source_mrr@10"):
            deltas = paired[control]["all"][field]["per_query_difference"]
            for direction, sign in (("gains", 1), ("regressions", -1)):
                ids = [q for q, d in deltas.items() if sign * d > 1e-12]
                buckets[f"{control}/{field}/{direction}"] = sorted(
                    ids, key=lambda q: (-sign * deltas[q], q))[:5]
    source_changes = {}
    for control in paired:
        source_changes[control] = []
        for qid in qids:
            target = queries[qid]["source_arxiv_id"]
            old, new = rank(runs[control][qid], target), rank(runs[CANDIDATE][qid], target)
            if old != new:
                source_changes[control].append({
                    "query_id": qid, "query": queries[qid]["query"],
                    "query_type": queries[qid]["query_type"],
                    "control_rank": old, "candidate_rank": new,
                    "mrr_difference": paired[control]["all"]["source_mrr@10"][
                        "per_query_difference"][qid],
                })
    cached = judge.load_judgments(snapshot["judge"])
    human = graded.read_human_grades()
    evidence_runs = {**runs, fusion.LEXICAL: sources[fusion.LEXICAL],
                     fusion.SEMANTIC: sources[fusion.SEMANTIC]}
    cases = {}
    selected = sorted({q for ids in buckets.values() for q in ids} | {
        r["query_id"] for changes in source_changes.values() for r in changes
        if r["mrr_difference"] < -1e-12
    })
    for qid in selected:
        evidence = []
        ids = list(dict.fromkeys(p for run in runs.values() for p in run[qid][:10]))
        for pid in ids:
            paper = papers[pid]
            cached_label = cached.get(judge.pair_key(snapshot["judge"], queries[qid]["query"], paper))
            evidence.append({
                "arxiv_id": pid, "title": paper["title"], "authors": paper["authors"],
                "abstract": paper["abstract"], "grade": labels[qid][pid],
                "provenance": "human" if (qid, pid) in human else snapshot["judge"],
                "cached_judge_reason": cached_label["reason"] if cached_label else None,
                "ranks": {name: rank(run[qid], pid) for name, run in evidence_runs.items()},
            })
        cases[qid] = {
            "query": queries[qid], "papers": evidence,
            "scores": {name: next(r for r in values if r["query_id"] == qid)
                       for name, values in rows.items()},
            "source_ranks": {name: rank(run[qid], queries[qid]["source_arxiv_id"])
                             for name, run in evidence_runs.items()},
        }
    report = {
        "candidate": CANDIDATE, "promoted": False, "api_calls": 0,
        "snapshot_sha256": hashlib.sha256(raw).hexdigest(),
        "query_ids": qids, "settings": settings, "sources": provenance,
        "run_fingerprints": {name: fusion.fingerprint(run) for name, run in runs.items()},
        "summary": summary, "candidate_minus_control": paired,
        "source_rank_changes": source_changes, "buckets": buckets,
    }
    lines = ["# Pre-promotion fusion review", "",
             "Offline dev-only review; no API calls, new labels, or baseline changes. "
             f"All compared top-10 results are judged using the same frozen "
             f"{sum(map(len, labels.values())):,}-pair snapshot.",
             "Source metrics credit only the generation-source paper; graded metrics credit "
             "all labeled relevant papers. Intervals are exploratory paired bootstraps, not "
             "multiplicity-adjusted or independent held-out confirmation. Judge reasons are "
             "diagnostic evidence, not ground truth.", "",
             "| System | Segment | nDCG@10 | P@10 | Source MRR@10 | Source R@1 | Source R@10 |",
             "|---|---|---|---|---|---|---|"]
    for name, groups in summary.items():
        for kind, fields in groups.items():
            values = [fields[f]["mean"] for f in (
                "ndcg@10", "precision@10", "source_mrr@10", "source_recall@1", "source_recall@10")]
            text = " | ".join("undefined" if v is None else f"{v:.4f}" for v in values)
            lines.append(f"| {name} | {kind} | {text} |")
    for control, groups in paired.items():
        lines += ["", f"## Candidate minus {control}", "",
                  "| Segment | Metric | Delta | 95% CI | Wins / losses / ties |",
                  "|---|---|---|---|---|"]
        for kind, fields in groups.items():
            for field in ("ndcg@10", "precision@10", "source_mrr@10"):
                r = fields[field]
                interval = r["ci95"]
                delta = "undefined" if r["difference"] is None else f"{r['difference']:+.4f}"
                ci = "undefined" if interval is None else f"[{interval[0]:+.4f}, {interval[1]:+.4f}]"
                lines.append(f"| {kind} | {field} | {delta} | {ci} | "
                             f"{r['wins']} / {r['regressions']} / {r['ties']} |")
    for bucket, ids in buckets.items():
        control, field, _ = bucket.split("/")
        lines += ["", f"## {bucket}", "",
                  "| Query | Text | Candidate minus control |",
                  "|---|---|---|"]
        for qid in ids:
            text = queries[qid]["query"].replace("|", "\\|").replace("\n", " ")
            delta = paired[control]["all"][field]["per_query_difference"][qid]
            lines.append(f"| {qid} | {text} | {delta:+.4f} |")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, run in runs.items():
        fusion._write_json(OUT / f"{name}.run.json", run)
        (OUT / f"{name}.scores.jsonl").write_text(
            "".join(json.dumps(r, allow_nan=False) + "\n" for r in rows[name]), encoding="utf-8")
    fusion._write_json(OUT / "report.json", report)
    fusion._write_json(OUT / "cases.json", cases)
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Review saved to {OUT}; baseline unchanged.")


if __name__ == "__main__":
    main()
