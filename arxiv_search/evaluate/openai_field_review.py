"""Audit the frozen field-aware challenger without tuning, API calls or promotion."""

from __future__ import annotations

import json

import numpy as np

from arxiv_search import config
from arxiv_search.evaluate import fusion_experiment as fusion, judge, metrics, results_catalog
from arxiv_search.evaluate import openai_field_experiment as fields, openai_field_hybrid as hybrid
from arxiv_search.evaluate.score_candidate_review import query_changes
from arxiv_search.search.rerank import rerank_prefix

CANDIDATE = "oai-field-hybrid+text=title25+d=10"
OUT = config.RESULTS_DIR / "openai-field-review-dev"


def concentration(differences: dict[str, float]) -> dict:
    if len(differences) < 6 or not all(np.isfinite(v) for v in differences.values()):
        raise ValueError("Concentration requires at least six finite paired differences")
    ordered = sorted(differences, key=lambda q: (-differences[q], q))
    total = sum(differences.values())
    return {
        "total_delta": total, "mean_delta": total / len(ordered),
        "leave_one_out_mean_range": [
            min((total - v) / (len(ordered) - 1) for v in differences.values()),
            max((total - v) / (len(ordered) - 1) for v in differences.values())],
        "excluding_largest_gains": {
            str(k): {"excluded": ordered[:k],
                     "mean_delta": (total - sum(differences[q] for q in ordered[:k]))
                     / (len(ordered) - k)}
            for k in (1, 2, 3, 5)},
        "caution": "Adversarial descriptive sensitivity, not a significance test or new dataset.",
    }


def evidence(ids: list[str], row: dict, lexical: dict[str, float]) -> dict:
    if row["candidate_ids"] != ids:
        raise ValueError("Field evidence is not aligned with frozen candidates")
    title, abstract = np.asarray(row["title"]), np.asarray(row["abstract"])
    semantic = .25 * title + .75 * abstract
    lex = np.asarray([lexical.get(p, 0.) for p in ids])
    total = hybrid.hybrid_signal(lex, semantic)
    lex_max = lex.max()
    parts = {
        p: {"lexical": float(.25 * lex[i] / lex_max) if lex_max > 0 else 0.,
            "title": float(.75 * .25 * title[i] / semantic.max()),
            "abstract": float(.75 * .75 * abstract[i] / semantic.max()),
            "total": float(total[i]),
            "cosine": {f: row[f][i] for f in ("concat", "title", "abstract")}}
        for i, p in enumerate(ids)}
    if any(not np.isclose(v["lexical"] + v["title"] + v["abstract"], v["total"])
           for v in parts.values()):
        raise ValueError("Weighted contributions do not reproduce hybrid scores")
    return parts


def inversions(before: list[str], after: list[str], grades: dict,
               parts: dict) -> list[dict]:
    if len(before) != 10 or set(before) != set(after):
        raise ValueError("Inversion audit requires identical top10 membership")
    positions = {p: i for i, p in enumerate(after)}
    result = []
    for i, demoted in enumerate(before):
        for promoted in before[i + 1:]:
            if positions[promoted] >= positions[demoted]:
                continue
            margins = {f: parts[promoted][f] - parts[demoted][f]
                       for f in ("lexical", "title", "abstract", "total")}
            result.append({
                "promoted": promoted, "demoted": demoted,
                "grade_difference": grades[promoted] - grades[demoted],
                "weighted_score_margins": margins,
                "title_decisive_at_fixed_normalizer": (
                    margins["total"] > 0 and margins["lexical"] + margins["abstract"] <= 0),
            })
    return result


def label_sensitivity(before: list[str], after: list[str], grades: dict) -> dict:
    original = metrics.ndcg_at_k(after, grades) - metrics.ndcg_at_k(before, grades)
    alternatives = []
    for p in before[:10]:
        for grade in (grades[p] - 1, grades[p] + 1):
            if grade not in (0, 1, 2):
                continue
            changed = {**grades, p: grade}
            a, b = metrics.ndcg_at_k(before, changed), metrics.ndcg_at_k(after, changed)
            if a is None or b is None:
                raise ValueError("Undefined ideal relevance in label sensitivity")
            alternatives.append({"arxiv_id": p, "from": grades[p], "to": grade,
                                 "change_to_query_delta": b - a - original})
    return min(alternatives, key=lambda v: v["change_to_query_delta"])


def main() -> None:
    hybrid.main()
    report_path = hybrid.OUT / "report.json"
    parent = json.loads(report_path.read_text(encoding="utf-8"))
    papers, queries, split = judge.load_inputs()
    qids = sorted(split["dev"])
    _, raw_labels, snapshot, _ = results_catalog.load_snapshot(config.RESULTS_DIR)
    runs = {n: json.loads((hybrid.OUT / f"{n}.run.json").read_text(encoding="utf-8"))
            for n in (fields.BASELINE, CANDIDATE)}
    rows = {n: parent["systems"][n]["per_query"] for n in runs}
    changes = query_changes(runs, rows, queries, fields.BASELINE, CANDIDATE)
    raw = json.loads((fields.OUT / "raw-field-scores.json").read_text(encoding="utf-8"))
    inputs = json.loads((config.RESULTS_DIR / "score-fusion-dev" / "input-scores.json")
                        .read_text(encoding="utf-8"))
    before, after = runs[fields.BASELINE], runs[CANDIDATE]
    paired, cases, flips, sensitivities = {}, {}, [], []
    additional = {}
    for n, run in runs.items():
        additional[n] = [{
            "query_id": q, "query_type": queries[q]["query_type"],
            "relevant_mrr@10": metrics.reciprocal_rank(run[q], snapshot["labels"][q]),
            "grade2_first": float(snapshot["labels"][q][run[q][0]] == 2),
        } for q in qids]
    for kind in ("all", *results_catalog.QUERY_TYPES):
        left, right = [
            [r for r in additional[n] if kind == "all" or r["query_type"] == kind]
            for n in runs]
        paired[kind] = {m: fusion.paired_rows(left, right, m)
                        for m in ("relevant_mrr@10", "grade2_first")}
    for q in qids:
        if set(before[q][:10]) != set(after[q][:10]) or before[q][10:] != after[q][10:]:
            raise ValueError("Candidate changed top10 membership or preserved tail")
        grades = snapshot["labels"][q]
        parts = evidence(before[q], raw[q], dict(inputs[q]["lexical"]))
        reconstructed = rerank_prefix(before[q], {p: v["total"] for p, v in parts.items()}, 10)
        if reconstructed != after[q]:
            raise ValueError("Weighted cached evidence does not reproduce candidate")
        flipped = inversions(before[q][:10], after[q][:10], grades, parts)
        flips.extend({**v, "query_id": q, "query_type": queries[q]["query_type"]}
                     for v in flipped)
        sensitivities.append({"query_id": q, **label_sensitivity(before[q], after[q], grades)})
        cases[q] = {
            "query": queries[q], "inversions": flipped,
            "papers": [{
                "arxiv_id": p, "title": papers[p]["title"], "abstract": papers[p]["abstract"],
                "grade": grades[p], "baseline_rank": before[q].index(p) + 1,
                "candidate_rank": after[q].index(p) + 1, "contributions": parts[p],
            } for p in before[q][:10]],
        }
    stats = {}
    for kind in ("all", *results_catalog.QUERY_TYPES):
        group = [v for v in flips if kind == "all" or v["query_type"] == kind]
        stats[kind] = {
            label: {"pairs": sum(test(v) for v in group),
                    "title_decisive_pairs": sum(
                        test(v) and v["title_decisive_at_fixed_normalizer"] for v in group)}
            for label, test in (
                ("harmful", lambda v: v["grade_difference"] < 0),
                ("helpful", lambda v: v["grade_difference"] > 0),
                ("equal_grade", lambda v: v["grade_difference"] == 0))}
    ndcg = parent["summary"][CANDIDATE]["all"]["ndcg@10"]["paired_vs_working"]
    source = parent["summary"][CANDIDATE]["all"]["source_mrr@10"]["paired_vs_working"]
    sensitivity_order = sorted(sensitivities, key=lambda v: (v["change_to_query_delta"], v["query_id"]))
    result = {
        "baseline": fields.BASELINE, "candidate": CANDIDATE, "api_calls": 0, "promoted": False,
        "recommendation": "Retain baseline: safety mostly passes, but gains are concentrated, "
                          "paraphrase relevance losses are real, and the gain interval includes zero.",
        "parent_report_sha256": fusion.fingerprint(parent),
        "label_snapshot_sha256": fusion.fingerprint(snapshot),
        "labels_unchanged": raw_labels == results_catalog.load_snapshot(config.RESULTS_DIR)[1],
        "all_100_rankings_reproduced": True, "changes": changes,
        "screen": parent["screens"][CANDIDATE], "secondary_paired_metrics": paired,
        "gain_concentration": {
            "ndcg@10": concentration(ndcg["per_query_difference"]),
            "source_mrr@10": concentration(source["per_query_difference"])},
        "inversion_summary": stats,
        "label_sensitivity": {
            "method": "Adversarial one-grade-step changes to top10 labels; at most one label "
                      "per query. Recompute both systems and pool IDCG. Hypothetical only; "
                      "no labels or human overrides changed. Not estimated annotation error.",
            "worst_per_query": sensitivity_order,
            "mean_delta_after_k_changes": {
                str(k): ndcg["difference"] + sum(
                    v["change_to_query_delta"] for v in sensitivity_order[:k]) / len(qids)
                for k in (1, 3, 5, 10)}},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    fusion._write_json(OUT / "report.json", result)
    fusion._write_json(OUT / "cases.json", cases)
    lines = [
        "# Field-aware hybrid challenger: promotion investigation", "",
        result["recommendation"], "",
        "Frozen100-query dev comparison; cached-only, no tuning, paid calls, new labels or "
        "held-out test access. Reproduce: `python -m arxiv_search.evaluate.openai_field_review`.",
        "All100 rankings reconstructed from weighted score components; identical top10 sets "
        "and positions11+ verified. Human overrides remain unchanged.", "",
        "## Graded alternatives versus original-source metrics", "",
        "| Segment | Relevant-paper MRR delta [95% CI] | Grade2-first rate delta [95% CI] |",
        "|---|---|---|"]
    for kind, values in paired.items():
        parts = []
        for m in ("relevant_mrr@10", "grade2_first"):
            v = values[m]
            parts.append(f"{v['difference']:+.5f} [{v['ci95'][0]:+.5f},{v['ci95'][1]:+.5f}]")
        lines.append(f"| {kind} | " + " | ".join(parts) + " |")
    lines += ["", "## Gain concentration", "",
              "Excluding largest observed gains is adversarial sensitivity, not a new test set.",
              "", "| Metric | All100 delta | Exclude top1 | Exclude top3 | Exclude top5 |",
              "|---|---|---|---|---|"]
    for m, v in result["gain_concentration"].items():
        lines.append(f"| {m} | {v['mean_delta']:+.6f} | " + " | ".join(
            f"{v['excluding_largest_gains'][str(k)]['mean_delta']:+.6f}" for k in (1, 3, 5)) + " |")
    lines += ["", "## Label sensitivity (hypothetical, no edits)", "",
              result["label_sensitivity"]["method"], "",
              str(result["label_sensitivity"]["mean_delta_after_k_changes"]), "",
              "## Reversed top10 pairs by frozen grade", "",
              "Pair counts are descriptive, not independent samples or DCG contributions. "
              "Title-decisive means removing only the title contribution changes the pair's "
              "margin sign while holding normalization fixed; it is not an abstract-only experiment.",
              "", "| Segment | Helpful | Harmful | Equal grade | Harmful title-decisive |",
              "|---|---|---|---|---|"]
    for kind, v in stats.items():
        lines.append(f"| {kind} | {v['helpful']['pairs']} | {v['harmful']['pairs']} | "
                     f"{v['equal_grade']['pairs']} | {v['harmful']['title_decisive_pairs']} |")
    lines += ["", "## Largest graded losses and gains", "",
              "| Query | Source rank | nDCG delta | Query text |", "|---|---|---|---|"]
    ordered = sorted(changes, key=lambda v: (v["ndcg_difference"], v["query_id"]))
    for v in ordered[:6] + list(reversed(ordered[-3:])):
        lines.append(f"| {v['query_id']} | {v['baseline_source_rank']} -> "
                     f"{v['candidate_source_rank']} | {v['ndcg_difference']:+.6f} | "
                     f"{v['query'].replace('|', '/')} |")
    lines += ["", "All100 query cases, exact inversions, grades, abstracts and score contributions "
              "are in `cases.json`. `report.json` retains every query delta and sensitivity.",
              "Existing promotion rules still fail: positive nDCG lower interval and no segment "
              "regression. This investigation does not silently waive those rules. Fresh evaluation "
              "or an explicit policy exception is needed before promotion."]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Reviewed100 queries; baseline unchanged; zero API calls.")


if __name__ == "__main__":
    main()
