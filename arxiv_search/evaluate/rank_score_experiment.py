"""Bounded rank/score experiment using frozen dev scores; never embeds or promotes.

python -m arxiv_search.evaluate.rank_score_experiment
"""

from __future__ import annotations

import hashlib
import json
import argparse

from arxiv_search import config
from arxiv_search.evaluate import fusion_experiment as fusion, fusion_review as review
from arxiv_search.evaluate import judge, openai_full as full, results_catalog as catalog
from arxiv_search.evaluate.score_candidate_review import CANDIDATE
from arxiv_search.evaluate.score_fusion_experiment import summarize
from arxiv_search.search.hybrid import fuse_rrf_baseline
from arxiv_search.search.rank_score import components, fuse_rank_score, rescore_shortlist
from arxiv_search.search.score_fusion import fuse_scores
from arxiv_search.search.text import paper_text

OUT = config.RESULTS_DIR / "rank-score-dev"


def plan(family: str = "interpolation") -> dict:
    """Fixed before reading outcomes; thresholds are conservative dev screening."""
    if family not in ("interpolation", "shortlist"):
        raise ValueError(f"Unknown experiment family: {family}")
    return {
        "hypothesis": ("Interpolating rank evidence with max-score fusion reduces weak-overlap "
                       "boosting while retaining graded-relevance gains." if family == "interpolation"
                       else "Score evidence improves ordering within the baseline top10 without "
                       "sacrificing recall at10/20; MRR and known-item rank safety remain empirical."),
        "primary_metric": "ndcg@10",
        "baseline": config.RRF_BASELINE_SYSTEM, "challenger": CANDIDATE,
        "scope": "100 dev queries; full corpus; no held-out test; exploratory not confirmatory",
        "rank_recipe": {"semantic_weight": 0.55, "c": 30, "depth": 100,
                        "normalization": "divide by theoretical maximum 1/31"},
        "score_recipe": {"semantic_weight": 0.75, "normalization": "max"},
        "settings": {
            f"fusion-{'rankscore' if family == 'interpolation' else 'shortlist'}+a={alpha:g}+d={depth}": {
                "score_fraction": alpha, "depth": depth, "k": 100}
            for depth in (100, 500)
            for alpha in ((0.25, 0.5, 0.75) if family == "interpolation" else (0.5, 1.0))},
        "screening_rules": [
            "All dev top10 positions judged in candidate and baseline",
            "Mean nDCG improves and paired bootstrap lower endpoint exceeds zero",
            "Source R@10 and R@20 at least baseline; known-item target ranks never worsen",
            "No query-type mean nDCG regression; grade0 first count does not increase",
        ],
        "selection_policy": "Among passing settings, highest mean nDCG; stable ID breaks exact ties. "
                            "No passing setting means retain baseline. No automatic promotion.",
        "no_query_specific_rules": True, "automatic_api_calls": False,
    }


def screen(candidate: dict, baseline: dict, run: dict, base_run: dict,
           queries: dict, labels: dict) -> dict:
    complete = candidate["top10_fully_judged"] and baseline["top10_fully_judged"]
    paired = candidate["paired_ndcg_vs_working_baseline"]
    known_regressions, known_changes = [], []
    lost_hits, gained_hits = [], []
    for qid, ids in run.items():
        target = queries[qid]["source_arxiv_id"]
        old, new = review.rank(base_run[qid], target), review.rank(ids, target)
        if queries[qid]["query_type"] == "known_item" and old != new:
            known_changes.append({"query_id": qid, "baseline_rank": old, "candidate_rank": new})
        if queries[qid]["query_type"] == "known_item" and old is not None and (
                new is None or new > old):
            known_regressions.append(qid)
        was_hit, now_hit = target in base_run[qid][:10], target in ids[:10]
        if was_hit and not now_hit:
            lost_hits.append(qid)
        if now_hit and not was_hit:
            gained_hits.append(qid)
    grades_known = all(ids and ids[0] in labels[q] for q, ids in run.items())
    grade0 = sum(labels[q][ids[0]] == 0 for q, ids in run.items()) if grades_known else None
    base_grade0 = sum(labels[q][ids[0]] == 0 for q, ids in base_run.items())
    checks = {
        "complete_top10": complete,
        "ndcg_positive_interval": bool(paired and paired["difference"] > 0
                                       and paired["ci95"][0] > 0),
        **{field: candidate["all"][field]["mean"] >= baseline["all"][field]["mean"] - 1e-12
           for field in ("source_recall@10", "source_recall@20")},
        "known_item_ranks_preserved": not known_regressions,
        "no_segment_ndcg_regression": complete and all(
            candidate["by_query_type"][kind]["ndcg@10"]["mean"] is not None
            and baseline["by_query_type"][kind]["ndcg@10"]["mean"] is not None
            and candidate["by_query_type"][kind]["ndcg@10"]["mean"]
            >= baseline["by_query_type"][kind]["ndcg@10"]["mean"] - 1e-12
            for kind in catalog.QUERY_TYPES),
        "grade0_first_not_increased": grade0 is not None and grade0 <= base_grade0,
    }
    return {"passes": all(checks.values()), "checks": checks,
            "lost_source_top10": sorted(lost_hits), "gained_source_top10": sorted(gained_hits),
            "known_item_rank_regressions": sorted(known_regressions),
            "known_item_target_rank_changes": known_changes,
            "grade0_first": grade0, "baseline_grade0_first": base_grade0}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=("interpolation", "shortlist"), default="interpolation")
    args = parser.parse_args(argv)
    experiment_plan = plan(args.family)
    out = OUT if args.family == "interpolation" else config.RESULTS_DIR / "shortlist-score-dev"
    out.mkdir(parents=True, exist_ok=True)
    plan_path = out / "preregistration.json"
    if plan_path.exists():
        if json.loads(plan_path.read_text(encoding="utf-8")) != experiment_plan:
            raise ValueError("Preregistered experiment changed; use a new experiment identity")
    else:
        fusion._write_json(plan_path, experiment_plan)
    root = config.RESULTS_DIR / "score-fusion-dev"
    papers, queries, splits = judge.load_inputs()
    qids = sorted(splits["dev"])
    if set(qids) & set(splits["test"]):
        raise ValueError("Dev/test overlap")
    raw_snapshot = (root / "labels.json").read_bytes()
    snapshot = json.loads(raw_snapshot)
    source_report = json.loads((root / "report.json").read_text(encoding="utf-8"))
    if not snapshot["complete"] or source_report["snapshot_sha256"] != fusion.fingerprint(snapshot):
        raise ValueError("Parent snapshot incomplete or changed")
    provenance = source_report["provenance"]
    if (provenance["paper_text_sha256"] != full.fingerprint([paper_text(p) for p in papers.values()])
            or provenance["query_text_sha256"] != full.fingerprint([queries[q]["query"] for q in qids])):
        raise ValueError("Corpus or dev query texts changed since saved score retrieval")
    input_path = root / "input-scores.json"
    inputs = json.loads(input_path.read_text(encoding="utf-8"))
    input_provenance = {
        "parent_snapshot_sha256": hashlib.sha256(raw_snapshot).hexdigest(),
        "input_scores_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "parent_report_sha256": hashlib.sha256((root / "report.json").read_bytes()).hexdigest(),
        "corpus_and_query_fingerprints": provenance,
    }
    input_manifest = out / "input-provenance.json"
    if input_manifest.exists():
        if json.loads(input_manifest.read_text(encoding="utf-8")) != input_provenance:
            raise ValueError("Frozen experiment inputs changed; use a new experiment identity")
    else:
        fusion._write_json(input_manifest, input_provenance)
    if set(inputs) != set(qids):
        raise ValueError("Expected exactly the dev score inputs")
    scored = {q: {family: dict(values) for family, values in families.items()}
              for q, families in inputs.items()}
    for q, families in inputs.items():
        if set(families) != {"lexical", "semantic"} or any(
                len(values) != len(scored[q][family]) for family, values in families.items()):
            raise ValueError("Invalid or duplicate retrieval score IDs")
        if any(pid not in papers for scores in scored[q].values() for pid in scores):
            raise ValueError("Unknown score paper ID")
    baseline = config.RRF_BASELINE_SYSTEM
    controls = {
        baseline: {q: fuse_rrf_baseline(list(s["lexical"]), list(s["semantic"]))
                   for q, s in scored.items()},
        CANDIDATE: {q: fuse_scores(s["lexical"], s["semantic"], normalization="max",
                                  semantic_weight=0.75, depth=500) for q, s in scored.items()},
    }
    for name, run in controls.items():
        frozen = json.loads((root / f"{name}.run.json").read_text(encoding="utf-8"))
        if run != frozen or fusion.fingerprint(run) != provenance["run_fingerprints"][name]:
            raise ValueError(f"{name}: raw inputs do not reproduce frozen control")
    for family, name in (("lexical", fusion.LEXICAL), ("semantic", fusion.SEMANTIC)):
        frozen = json.loads((config.RESULTS_DIR / "dev" / f"{name}.run.json").read_text())
        if any(list(scored[q][family])[:100] != frozen[q] for q in qids):
            raise ValueError(f"{family}: raw input order differs from frozen top100")
    combine = fuse_rank_score if args.family == "interpolation" else rescore_shortlist
    runs = {**controls, **{
        name: {q: combine(s["lexical"], s["semantic"], **options) for q, s in scored.items()}
        for name, options in experiment_plan["settings"].items()}}
    for name, run in runs.items():
        fusion.validate_run(name, run, qids, papers, exact_depth=100)
        if args.family == "shortlist" and name not in controls and any(
                set(run[q][:10]) != set(controls[baseline][q][:10])
                or run[q][10:] != controls[baseline][q][10:] for q in qids):
            raise ValueError(f"{name}: shortlist membership or tail changed")
    labels = snapshot["labels"]
    pairs = {q: list(dict.fromkeys(p for run in runs.values() for p in run[q][:10])) for q in qids}
    missing = {q: [p for p in ids if p not in labels[q]] for q, ids in pairs.items()}
    entries = {name: {"run": run, "paths": [], "metadata": {}} for name, run in runs.items()}
    results = catalog.score_catalog(entries, snapshot, papers, queries, qids, baseline)
    rows = {name: r["per_query"] for name, r in results.items()}
    summaries = summarize(rows, baseline)
    for name in summaries:
        for kind, fields in summaries[name].items():
            group = [r for r in rows[name] if kind == "all" or r["query_type"] == kind]
            challenger = [r for r in rows[CANDIDATE] if kind == "all" or r["query_type"] == kind]
            complete = all(r["judged@10"] == 1 for r in group + challenger)
            for field, summary in fields.items():
                summary["paired_vs_challenger"] = (
                    fusion.paired_rows(challenger, group, field)
                    if complete or field.startswith("source_") else None)
    screens = {name: screen(results[name], results[baseline], runs[name], runs[baseline],
                            queries, labels) for name in experiment_plan["settings"]}
    passing = sorted((n for n, s in screens.items() if s["passes"]),
                     key=lambda n: (-results[n]["all"]["ndcg@10"]["mean"], n))
    outcomes = {
        "baseline": baseline, "challenger": CANDIDATE, "promoted": False, "api_calls": 0,
        "parent_snapshot_sha256": hashlib.sha256(raw_snapshot).hexdigest(),
        "input_scores_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "preregistration_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        "missing": missing, "missing_pairs": sum(map(len, missing.values())),
        "summary": summaries, "screens": screens, "passing_candidates": passing,
        "recommended_candidate": passing[0] if passing else None,
        "controls_exactly_reproduced": True,
        "run_fingerprints": {name: fusion.fingerprint(run) for name, run in runs.items()},
        "query_ids": qids,
    }
    cases = {}
    for name in experiment_plan["settings"]:
        diffs = summaries[name]["all"]["ndcg@10"]["paired_vs_working"]
        ids = set(screens[name]["lost_source_top10"]) | set(screens[name]["gained_source_top10"])
        if diffs:
            changes = diffs["per_query_difference"]
            ids.update(sorted(changes, key=lambda q: (changes[q], q))[:5])
            ids.update(sorted(changes, key=lambda q: (-changes[q], q))[:5])
        ids.update(q for q in qids if review.rank(runs[name][q], queries[q]["source_arxiv_id"])
                   != review.rank(runs[baseline][q], queries[q]["source_arxiv_id"]))
        ids.update(("q-paraphrase-062", "q-question-027", "q-paraphrase-006", "q-keyword-053"))
        for q in sorted(ids & set(qids)):
            evidence = components(scored[q]["lexical"], scored[q]["semantic"],
                                  **experiment_plan["settings"][name])
            target = queries[q]["source_arxiv_id"]
            case = cases.setdefault(q, {"query": queries[q], "systems": {}})
            pids = list(dict.fromkeys(runs[baseline][q][:10] + runs[name][q][:10] + [target]))
            case["systems"][name] = {
                "source_ranks": {n: review.rank(run[q], target) for n, run in runs.items()},
                "papers": [{
                    "arxiv_id": pid, "title": papers[pid]["title"],
                    "abstract": papers[pid]["abstract"], "grade": labels[q].get(pid),
                    "components": evidence.get(pid),
                    "ranks": {n: review.rank(run[q], pid) for n, run in runs.items()},
                } for pid in pids],
            }
    lines = [f"# {'Rank/score interpolation' if args.family == 'interpolation' else 'Fixed-shortlist score ordering'}: bounded dev experiment", "",
             experiment_plan["hypothesis"], "",
             f"{len(experiment_plan['settings'])} prespecified settings, depths100/500. "
             "Rank evidence is fixed RRF55%/c30/depth100 divided by1/31; score evidence "
             "is max-normalized75% semantic. Combined = a*score + (1-a)*normalized_RRF. "
             "These are not probabilities. No query-type routing, source IDs, or labels "
             "are used in ranking. " + (
                 "Shortlist mode only reorders baseline top10 and preserves the tail; "
                 "it cannot introduce a paper or improve recall at10/20." if args.family == "shortlist"
                 else "Interpolation reranks the union of rank and score candidates."), "",
             "Controls exactly reproduce frozen runs. All rows use the same parent snapshot. "
             "Paired graded comparisons are withheld for incomplete top10s; source metrics "
             "remain valid. Intervals are exploratory after dev tuning, not adjusted for "
             "selection or multiple testing. No automatic promotion or API calls.", "",
             f"Missing judgments: **{outcomes['missing_pairs']}**.", "",
             "| System | nDCG10 | P10 | Judged10 | Source MRR10 | R10 | R20 | Screening |",
             "|---|---|---|---|---|---|---|---|"]
    for name in runs:
        summary = results[name]["all"]
        numbers = [summary[m]["mean"] for m in (
            "ndcg@10", "precision@10", "judged@10", "source_mrr@10",
            "source_recall@10", "source_recall@20")]
        status = "control" if name in controls else "PASS" if screens[name]["passes"] else "not passed"
        if not results[name]["top10_fully_judged"]:
            status += "; PROVISIONAL"
        lines.append(f"| `{name}` | " + " | ".join(
            "undefined" if v is None else f"{v:.4f}" for v in numbers) + f" | {status} |")
    lines += ["", "## Screening rules (fixed before outcomes)", "",
              *[f"- {r}" for r in experiment_plan["screening_rules"]], "",
              "Per-query ranks, grades and score components: cases.json. All segment means, "
              "paired intervals and missing pairs: report.json. "
              "A failed screen is not proof a method is useless; it is a reason not to "
              "replace the balanced baseline under this conservative experiment policy."]
    lines += ["", "## Screening outcomes", "",
              "| System | Failed checks | Grade0 first | Lost / gained source top10 hits |",
              "|---|---|---|---|"]
    for name, status in screens.items():
        failed = ", ".join(k for k, v in status["checks"].items() if not v) or "none"
        lines.append(f"| `{name}` | {failed} | {status['grade0_first']} | "
                     f"{len(status['lost_source_top10'])} / {len(status['gained_source_top10'])} |")
    lines += ["", "## Selection", "",
              f"Recommended dev candidate: `{passing[0]}`." if passing else
              "No setting passes the fixed screening rules; retain the working baseline.",
              "Passing screening is not held-out confirmation or automatic promotion. "
              "Review individual losses and obtain a baseline decision before changing configuration."]
    for name, run in runs.items():
        fusion._write_json(out / f"{name}.run.json", run)
        (out / f"{name}.scores.jsonl").write_text(
            "".join(json.dumps(r, allow_nan=False) + "\n" for r in rows[name]), encoding="utf-8")
    fusion._write_json(out / "configs.json", experiment_plan["settings"])
    fusion._write_json(out / "report.json", outcomes)
    fusion._write_json(out / "cases.json", cases)
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(experiment_plan['settings'])} experiments; {outcomes['missing_pairs']} missing judgments; "
          f"{len(passing)} pass conservative screening; zero API calls; baseline unchanged.")


if __name__ == "__main__":
    main()
