"""Bounded global field-weight recovery experiment; cached only, never promotes."""

from __future__ import annotations

import json

import numpy as np

from arxiv_search import config
from arxiv_search.evaluate import fusion_experiment as fusion, judge, results_catalog as catalog
from arxiv_search.evaluate import openai_field_experiment as fields, openai_field_hybrid as hybrid
from arxiv_search.evaluate.cross_encoder_experiment import freeze
from arxiv_search.evaluate.score_fusion_experiment import summarize
from arxiv_search.search.rerank import rerank_prefix

OUT = config.RESULTS_DIR / "openai-field-recovery-dev"
CHALLENGER = "oai-field-hybrid+text=title25+d=10"


def plan() -> dict:
    settings = {}
    for recipe, title, anchor in (
            ("concat", None, 1.), ("abstract", 0., 0.), ("title10", .1, 0.),
            ("title25", .25, 0.), ("title25", .25, .5), ("title25", .25, .75)):
        settings[f"oai-field-recovery+text={recipe}+anchor={anchor:g}+d=10"] = {
            "title_weight": title, "concat_fraction": anchor, "depth": 10}
    return {
        "baseline": fields.BASELINE, "challenger": CHALLENGER, "settings": settings,
        "hypothesis": "Less title emphasis or anchoring semantic scores to original concat "
                      "cosines reduces paraphrase intent drift without losing other-segment gains.",
        "scoring": "semantic = a*concat + (1-a)*(t*title+(1-t)*abstract); then "
                   "25% candidate100-max BM25 +75% candidate100-max semantic. Stable baseline "
                   "ties; reorder baseline top10 only, preserve positions11+. No query routing.",
        "setting_description": "Six fixed settings: concat control, abstract-only,10% title, "
                               "25% title control, and25% title anchored50/75% to concat. ",
        "scope": "100 dev queries, frozen labels/candidate100/score caches. Held-out untouched.",
        "automatic_embedding_calls": False, "automatic_promotion": False,
        "recovery_rules": [
            "Paraphrase nDCG and source MRR at least approved baseline.",
            "Other segment nDCG at least both baseline and field25 challenger; "
            "other segment source MRR at least baseline.",
            "Existing baseline promotion screen must pass for promotion eligibility.",
        ],
        "interpretation": "Post-investigation exploratory experiment, no multiple-testing "
                          "correction. Freeze plan before scoring; do not extend grid after outcomes.",
    }


def semantic_signal(row: dict, title_weight: float | None, concat_fraction: float) -> np.ndarray:
    if not np.isfinite(concat_fraction) or not 0 <= concat_fraction <= 1:
        raise ValueError("Invalid concat fraction")
    vectors = [np.asarray(row[f], dtype=float) for f in ("concat", "title", "abstract")]
    if (any(v.ndim != 1 or v.shape != vectors[0].shape or not np.isfinite(v).all()
            for v in vectors) or not vectors[0].size):
        raise ValueError("Expected finite aligned nonempty score vectors")
    concat, title, abstract = vectors
    if title_weight is None:
        if concat_fraction != 1:
            raise ValueError("Concat control must use concat fraction1")
        return concat
    if not np.isfinite(title_weight) or not 0 <= title_weight <= 1:
        raise ValueError("Invalid title weight")
    return (concat_fraction * concat + (1 - concat_fraction)
            * (title_weight * title + (1 - title_weight) * abstract))


def recovery_checks(summary: dict, name: str) -> dict:
    checks = {}
    for kind in catalog.QUERY_TYPES:
        candidate, baseline = summary[name][kind], summary[fields.BASELINE][kind]
        checks[f"{kind}_ndcg_vs_baseline"] = (
            candidate["ndcg@10"]["mean"] >= baseline["ndcg@10"]["mean"] - 1e-12)
        checks[f"{kind}_source_mrr_vs_baseline"] = (
            candidate["source_mrr@10"]["mean"] >= baseline["source_mrr@10"]["mean"] - 1e-12)
        if kind != "paraphrase":
            checks[f"{kind}_ndcg_vs_challenger"] = (
                candidate["ndcg@10"]["mean"]
                >= summary[CHALLENGER][kind]["ndcg@10"]["mean"] - 1e-12)
    return {"passes": all(checks.values()), "checks": checks}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    experiment = plan()
    freeze(OUT / "preregistration.json", experiment)
    hybrid.main()
    parent_path = hybrid.OUT / "report.json"
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    raw_path = fields.OUT / "raw-field-scores.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    lexical_path = config.RESULTS_DIR / "score-fusion-dev" / "input-scores.json"
    lexical = json.loads(lexical_path.read_text(encoding="utf-8"))
    papers, queries, split = judge.load_inputs()
    qids = sorted(split["dev"])
    _, label_bytes, snapshot, _ = catalog.load_snapshot(config.RESULTS_DIR)
    base = json.loads((hybrid.OUT / f"{fields.BASELINE}.run.json").read_text(encoding="utf-8"))
    freeze(OUT / "input-provenance.json", {
        "parent_report": fusion.fingerprint(parent), "raw_scores": fusion.fingerprint(raw),
        "lexical_inputs": fusion.fingerprint(lexical), "labels": fusion.fingerprint(snapshot),
        "baseline": fusion.fingerprint(base), "plan": fusion.fingerprint(experiment)})
    runs = {fields.BASELINE: base}
    for n, options in experiment["settings"].items():
        runs[n] = {}
        for q in qids:
            if raw[q]["candidate_ids"] != base[q]:
                raise ValueError("Frozen candidate alignment changed")
            semantic = semantic_signal(raw[q], options["title_weight"], options["concat_fraction"])
            lex_scores = dict(lexical[q]["lexical"])
            scores = hybrid.hybrid_signal(
                np.asarray([lex_scores.get(p, 0.) for p in base[q]]), semantic)
            runs[n][q] = rerank_prefix(base[q], dict(zip(base[q], scores.tolist())), 10)
        fusion.validate_run(n, runs[n], qids, papers, exact_depth=100)
        if any(set(runs[n][q][:10]) != set(base[q][:10])
               or runs[n][q][10:] != base[q][10:] for q in qids):
            raise ValueError("Recovery changed membership or preserved tail")
        fusion._write_json(OUT / f"{n}.run.json", runs[n])
    for recipe, reference in (
            ("concat+anchor=1", "oai-field-hybrid+text=concat+d=10"),
            ("title25+anchor=0", CHALLENGER)):
        if runs[f"oai-field-recovery+text={recipe}+d=10"] != json.loads(
                (hybrid.OUT / f"{reference}.run.json").read_text(encoding="utf-8")):
            raise ValueError("Same-recipe control did not reproduce parent")
    report = fields.publish(OUT, runs, snapshot, papers, queries, qids, experiment,
                            {"new_embedding_api_calls": 0, "judge_calls": 0,
                             "new_accounted_usd": 0.})
    rows = {n: v["per_query"] for n, v in report["systems"].items()}
    rows[CHALLENGER] = parent["systems"][CHALLENGER]["per_query"]
    summary = summarize(rows, CHALLENGER)
    report["paired_vs_field25_challenger"] = summary
    report["recovery_checks"] = {
        n: recovery_checks(summary, n) for n in experiment["settings"]}
    if label_bytes != catalog.load_snapshot(config.RESULTS_DIR)[1]:
        raise ValueError("Frozen labels changed during recovery experiment")
    fusion._write_json(OUT / "report.json", report)
    with (OUT / "report.md").open("a", encoding="utf-8") as file:
        file.write("\n## Recovery safety versus both references\n\n"
                   "Paraphrase nDCG/source MRR must reach baseline. Other segment nDCG must "
                   "reach both references, and source MRR must reach baseline. These are "
                   "observed-mean screens, not equivalence tests. No automatic promotion.\n\n"
                   "| Setting | Recovery screen | Baseline promotion screen |\n|---|---|---|\n")
        for n, check in report["recovery_checks"].items():
            file.write(f"| `{n}` | {check['passes']} | {report['screens'][n]['passes']} |\n")
    print("Completed six fixed recovery settings; zero API calls; baseline unchanged.")


if __name__ == "__main__":
    main()
