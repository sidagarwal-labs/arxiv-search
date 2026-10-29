"""Audit scored-fusion gains/losses using saved evidence, without API calls.

python -m arxiv_search.evaluate.score_candidate_review
"""

from __future__ import annotations

import hashlib
import json

from arxiv_search import config
from arxiv_search.evaluate import fusion_experiment as fusion, fusion_review as review
from arxiv_search.evaluate import judge, results_catalog
from arxiv_search.search.score_fusion import fuse_scores

CANDIDATE = "score-max+w=0.75+d=500"
OUT = config.RESULTS_DIR / "score-candidate-review-dev"


def query_changes(runs: dict, rows: dict, queries: dict, baseline: str,
                  candidate: str) -> list[dict]:
    scores = {name: {r["query_id"]: r for r in values} for name, values in rows.items()}
    if scores[baseline].keys() != scores[candidate].keys():
        raise ValueError("Comparison requires identical query IDs")
    changes = []
    for qid in sorted(scores[baseline]):
        target = queries[qid]["source_arxiv_id"]
        before, after = scores[baseline][qid], scores[candidate][qid]
        old = review.rank(runs[baseline][qid], target)
        new = review.rank(runs[candidate][qid], target)
        changes.append({
            "query_id": qid, "query": queries[qid]["query"],
            "query_type": queries[qid]["query_type"], "source_arxiv_id": target,
            "baseline_source_rank": old, "candidate_source_rank": new,
            "lost_source_top10": old is not None and old <= 10 and (new is None or new > 10),
            "gained_source_top10": new is not None and new <= 10 and (old is None or old > 10),
            "baseline": before, "candidate": after,
            "ndcg_difference": (after["ndcg@10"] - before["ndcg@10"]
                                if after["ndcg@10"] is not None and before["ndcg@10"] is not None
                                else None),
        })
    return changes


def score_components(pid: str, inputs: dict) -> dict:
    parts = {}
    for family, weight in (("lexical", 0.25), ("semantic", 0.75)):
        scores = dict(inputs[family][:500])
        values = list(scores.values())
        if not values or values[0] <= 0:
            raise ValueError(f"{family}: expected a positive maximum score")
        raw = scores.get(pid)
        parts[family] = {
            "rank": review.rank(list(scores), pid), "raw_score": raw,
            "normalized_score": raw / values[0] if raw is not None else 0.0,
            "weighted_contribution": weight * raw / values[0] if raw is not None else 0.0,
        }
    return {**parts, "total": sum(p["weighted_contribution"] for p in parts.values())}


def main() -> None:
    root = config.RESULTS_DIR / "score-fusion-dev"
    baseline = config.WORKING_BASELINE_SYSTEM
    snapshot_path, raw, snapshot, _ = results_catalog.load_snapshot(config.RESULTS_DIR)
    if snapshot_path != root / "labels.json" or not snapshot["complete"]:
        raise ValueError("Review requires the completed score-fusion label snapshot")
    papers, queries, split = judge.load_inputs()
    qids = sorted(split["dev"])
    if set(qids) & set(split["test"]):
        raise ValueError("Dev/test overlap")
    experiment = json.loads((root / "report.json").read_text(encoding="utf-8"))
    if experiment["snapshot_sha256"] != fusion.fingerprint(snapshot):
        raise ValueError("Experiment label snapshot changed")
    runs = {name: json.loads((root / f"{name}.run.json").read_text(encoding="utf-8"))
            for name in (baseline, CANDIDATE)}
    for name, run in runs.items():
        fusion.validate_run(name, run, qids, papers, exact_depth=100)
        if fusion.fingerprint(run) != experiment["provenance"]["run_fingerprints"][name]:
            raise ValueError(f"{name}: ranking changed since experiment")
    entries = {name: {"run": run, "paths": [], "metadata": {}} for name, run in runs.items()}
    catalog = results_catalog.score_catalog(entries, snapshot, papers, queries, qids, baseline)
    if not all(r["top10_fully_judged"] for r in catalog.values()):
        raise ValueError("Review requires all compared top10 results to be judged")
    rows = {name: result["per_query"] for name, result in catalog.items()}
    changes = query_changes(runs, rows, queries, baseline, CANDIDATE)
    paired = {}
    for kind in ("all", *results_catalog.QUERY_TYPES):
        left = [r for r in rows[baseline] if kind == "all" or r["query_type"] == kind]
        right = [r for r in rows[CANDIDATE] if kind == "all" or r["query_type"] == kind]
        paired[kind] = {field: fusion.paired_rows(left, right, field)
                        for field in results_catalog.FIELDS if field != "judged@10"}
    valid = [r for r in changes if r["ndcg_difference"] is not None]
    loss = sorted((r for r in valid if r["ndcg_difference"] < -1e-12),
                  key=lambda r: (r["ndcg_difference"], r["query_id"]))
    gains = sorted((r for r in valid if r["ndcg_difference"] > 1e-12),
                   key=lambda r: (-r["ndcg_difference"], r["query_id"]))
    buckets = {
        "largest_ndcg_losses": [r["query_id"] for r in loss[:10]],
        "largest_ndcg_gains": [r["query_id"] for r in gains[:5]],
        "lost_source_top10": [r["query_id"] for r in changes if r["lost_source_top10"]],
        "gained_source_top10": [r["query_id"] for r in changes if r["gained_source_top10"]],
    }
    inputs = json.loads((root / "input-scores.json").read_text(encoding="utf-8"))
    labels = snapshot["labels"]
    cases = {}
    for qid in sorted({q for ids in buckets.values() for q in ids}):
        recomputed = fuse_scores(dict(inputs[qid]["lexical"]), dict(inputs[qid]["semantic"]),
                                 normalization="max", semantic_weight=0.75, depth=500, k=100)
        if recomputed != runs[CANDIDATE][qid]:
            raise ValueError(f"{qid}: saved raw-score evidence does not reproduce candidate")
        target = queries[qid]["source_arxiv_id"]
        evidence = []
        for pid in dict.fromkeys(runs[baseline][qid][:10] + runs[CANDIDATE][qid][:10] + [target]):
            evidence.append({
                "arxiv_id": pid, "title": papers[pid]["title"],
                "authors": papers[pid]["authors"], "abstract": papers[pid]["abstract"],
                "grade": labels[qid].get(pid),
                "ranks": {name: review.rank(run[qid], pid) for name, run in runs.items()},
                "candidate_components": score_components(pid, inputs[qid]),
            })
        cases[qid] = {"change": next(r for r in changes if r["query_id"] == qid),
                      "papers": evidence}
    report = {
        "baseline": baseline, "candidate": CANDIDATE, "api_calls": 0, "promoted": False,
        "recommendation": "Retain working baseline; keep scored fusion as challenger pending recall tradeoff approval.",
        "snapshot_sha256": hashlib.sha256(raw).hexdigest(),
        "paired": paired, "changes": changes, "buckets": buckets,
        "all_known_item_source_ranks_unchanged": all(
            r["baseline_source_rank"] == r["candidate_source_rank"]
            for r in changes if r["query_type"] == "known_item"),
        "grade0_first": {name: sum(labels[q][run[q][0]] == 0 for q in qids)
                         for name, run in runs.items()},
    }
    lines = ["# Score-fusion challenger: loss and recall review", "",
             f"Baseline `{baseline}`; challenger `{CANDIDATE}`. "
             f"Same immutable {sum(map(len, snapshot['labels'].values())):,}-pair "
             "dev label snapshot; no API calls or promotion.",
             "Exploratory paired bootstrap intervals are conditional on labels, not "
             "selection/multiple-testing adjusted. Source recall measures the original target, "
             "not every possible useful answer. A null evidence grade is unjudged, not grade0.",
             "", "## Overall candidate minus baseline", "",
             "| Metric | Baseline | Challenger | Delta [95% CI] | Wins / losses / ties |",
             "|---|---|---|---|---|"]
    for field in paired["all"]:
        p = paired["all"][field]
        before, after = catalog[baseline]["all"][field]["mean"], catalog[CANDIDATE]["all"][field]["mean"]
        delta = (f"{p['difference']:+.4f} [{p['ci95'][0]:+.4f}, {p['ci95'][1]:+.4f}]"
                 if p["difference"] is not None else "undefined")
        values = [f"{v:.4f}" if v is not None else "undefined" for v in (before, after)]
        lines.append(f"| {field} | {values[0]} | {values[1]} | {delta} | "
                     f"{p['wins']} / {p['regressions']} / {p['ties']} |")
    for bucket, ids in buckets.items():
        lines += ["", f"## {bucket.replace('_', ' ')}", "",
                  "| Query | Source rank: baseline / challenger | nDCG: baseline / challenger | Delta |",
                  "|---|---|---|---|"]
        for qid in ids:
            r = cases[qid]["change"]
            query = r["query"].replace("|", "\\|").replace("\n", " ")
            delta = r["ndcg_difference"]
            lines.append(f"| {qid}: {query} | {r['baseline_source_rank']} / "
                         f"{r['candidate_source_rank']} | {r['baseline']['ndcg@10']:.4f} / "
                         f"{r['candidate']['ndcg@10']:.4f} | {delta:+.4f} |")
    lines += ["", "## Decision", "", report["recommendation"],
              "Improved mean nDCG/MRR and first-place hits do not erase source recall "
              "regressions. Review all lost hits and lower-list relevance losses rather "
              "than treating leaderboard position as automatic promotion. Known-item "
              "target ranks are checked independently; the held-out test remains untouched.",
              "Full abstracts, per-paper grades, raw normalized score contributions and "
              f"ranks are in cases.json. All {len(changes)} query changes and segment CIs are in report.json."]
    OUT.mkdir(parents=True, exist_ok=True)
    fusion._write_json(OUT / "report.json", report)
    fusion._write_json(OUT / "cases.json", cases)
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Reviewed {len(changes)} dev queries: {len(loss)} nDCG losses; "
          f"{len(buckets['lost_source_top10'])} lost top10 targets, "
          f"{len(buckets['gained_source_top10'])} new hits; baseline unchanged.")


if __name__ == "__main__":
    main()
