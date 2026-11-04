"""Verify the approved Decision36 profile and generate comparable progress charts.

python -m arxiv_search.evaluate.baseline_promotion
"""

from __future__ import annotations

import json
import math

from arxiv_search import config
from arxiv_search.evaluate import fusion_experiment as fusion, judge, metrics, results_catalog
from arxiv_search.search.hybrid import fuse_working_baseline

MILESTONES = results_catalog.RETRIEVAL_MILESTONES
assert dict(MILESTONES)["Tuned BM25"] == fusion.LEXICAL
assert dict(MILESTONES)["OpenAI hybrid"] == fusion.ORIGINAL
assert dict(MILESTONES)["RRF55 c30"] == config.RRF_BASELINE_SYSTEM


def bottlenecks(run: dict, labels: dict, inputs: dict, queries: dict) -> dict:
    if not run or set(run) != set(labels) or set(run) != set(inputs):
        raise ValueError("Headroom requires identical nonempty dev query sets")
    values = []
    for q, ids in run.items():
        if len(ids) < 10 or any(p not in labels[q] for p in ids[:10]):
            raise ValueError("Selected top10 must be fully judged for exact oracle ordering")
        oracle = sorted(ids[:10], key=lambda pid: -labels[q][pid])
        value = metrics.ndcg_at_k(oracle, labels[q], 10)
        if value is None:
            raise ValueError("Undefined ideal relevance for headroom query")
        values.append(value)
    return {
        "queries": len(run), "oracle_ndcg_with_fixed_top10": sum(values) / len(values),
        "oracle_scope": "Exact best permutation of current top10 under frozen labels; "
                        "not an achievable model estimate or full-corpus upper bound.",
        "source_hits_in_retriever_union": {
            str(depth): sum(
                queries[q]["source_arxiv_id"] in {
                    p for pairs in families.values() for p, _ in pairs[:depth]}
                for q, families in inputs.items()) for depth in (10, 100, 500)},
        "source_hits_current_top10": sum(
            queries[q]["source_arxiv_id"] in ids[:10] for q, ids in run.items()),
        "top10_grade_counts": {
            str(grade): sum(labels[q][p] == grade for q, ids in run.items() for p in ids[:10])
            for grade in (0, 1, 2)},
    }


RERANK_MILESTONE = "2-pass LLM rerank + safeguard"  # current reranking baseline
PRIOR_RERANK_MILESTONE = "LLM rerank + safeguard"  # Decision45, single pass


def _comparison_bounds(scores: list[float]) -> tuple[float, float]:
    return (
        max(0, (math.floor(min(scores) * 100) - 1) / 100),
        min(1, (math.ceil(max(scores) * 100) + 1) / 100),
    )


def render_charts(report: dict, diagnosis: dict) -> str:
    systems = report["systems"]
    stage2 = report.get("stage2", {}).get("systems", {})
    rerank = report.get("reranking_baseline")
    # Stage 2 points share the same labels and dev queries, so they extend the same curve.
    points = [(label, name, "1 retrieval", systems.get(name)) for label, name in MILESTONES]
    prior = config.DECISION45_RERANK_SYSTEM
    if prior in stage2 and prior != rerank:
        points.append((PRIOR_RERANK_MILESTONE, prior, "2 reranking", stage2[prior]))
    if rerank in stage2:
        points.append((RERANK_MILESTONE, rerank, "2 reranking", stage2[rerank]))
    milestone_rows = []
    previous = None
    for label, name, stage, result in points:
        if result is None:
            raise ValueError(f"Cannot chart missing milestone: {name}")
        if not result["top10_fully_judged"]:
            raise ValueError(f"Cannot chart provisional milestone: {name}")
        score = result["all"]["ndcg@10"]["mean"]
        if score is None:
            raise ValueError(f"Cannot chart undefined milestone: {name}")
        delta = "-" if previous is None else f"{score - previous:+.4f}"
        milestone_rows.append(
            f"| {stage} | {label} | `{name}` | {score:.4f} | {delta} | "
            f"{result['all']['source_mrr@10']['mean']:.4f} | "
            f"{result['all']['source_recall@10']['mean']:.0%} |")
        previous = score
    scores = [result["all"]["ndcg@10"]["mean"] for *_, result in points]
    oracle = report.get("stage2", {}).get("oracle")
    ceiling = oracle["all"]["ndcg@10"]["mean"] if oracle else None
    lower = min(0.5, math.floor(min(scores) * 20) / 20)
    upper = max(0.75, math.ceil(max(scores + ([ceiling] if ceiling else [])) * 20) / 20)
    current = scores[-1]
    gain = current - scores[0]
    retrieval_score = systems[report["working_baseline"]]["all"]["ndcg@10"]["mean"]
    provenance = report.get("label_snapshot_provenance", {})
    pairs = provenance.get("original_pairs", 0) + provenance.get("added_pairs", 0)
    label_text = (f"same {pairs:,}-pair dev label set (`{report['label_snapshot']}`)"
                  if pairs else f"same dev label set (`{report['label_snapshot']}`)")
    latest = report["leaderboard"]["ranked"][:5]
    if report["working_baseline"] not in latest:
        latest = [*latest, report["working_baseline"]]
    latest_scores = [systems[n]["all"]["ndcg@10"]["mean"] for n in latest]
    latest_lower, latest_upper = _comparison_bounds(latest_scores)
    lines = [
        "# Search quality charts", "",
        "*Generated by `python -m arxiv_search.evaluate.baseline_promotion`; do not edit by hand.*",
        "", "## Hill climbing: major comparable milestones", "",
        f"Every point is rescored against the **{label_text}**, "
        "100 dev queries, 23,304 searchable papers. Stage 1 points are retrieval baselines "
        "and turning points; the Stage 2 point adds the LLM reranker on top of the current "
        "retrieval baseline. These are selected milestones, not "
        "every trial, independent experiments, or equally spaced dates. The x-axis is "
        f"milestone order. **Zoomed linear y-axis: {lower:.2f}-{upper:.2f}, not zero-based.** "
        "This focuses on score changes, not their magnitude relative to zero. "
        "All plotted top10s are fully judged; no pilot/test scores are mixed in. Scores "
        "shifted down slightly from older versions of this page when reranker top-10 grades "
        "joined the shared labels (167 in Decision45, 72 in Decision46); the curve's shape "
        "is unchanged.",
        "",
        f"**First plotted baseline to current: {scores[0]:.4f} to {current:.4f} "
        f"({gain:+.4f} nDCG, {gain / scores[0]:+.1%} relative)"
        + (f"; retrieval alone reaches {retrieval_score:.4f}, the reranker adds "
           f"{current - retrieval_score:+.4f}.** " if len(points) > len(MILESTONES) else ".** ")
        +
        "The first point is tuned BM25, not the original plain-BM25 control, "
        "whose graded coverage is incomplete. "
        "Use a linear scale: nDCG is a bounded relevance score, not a quantity spanning "
        "orders of magnitude; a log axis would obscure additive improvements.",
        "", "```mermaid", "xychart-beta",
        '    title "Hill climbing: graded relevance nDCG@10"',
        "    x-axis [" + ", ".join(f'\"{label}\"' for label, *_ in points) + "]",
        f'    y-axis "nDCG@10 (zoomed, higher is better)" {lower:g} --> {upper:g}',
        "    line [" + ", ".join(f"{v:.4f}" for v in scores) + "]",
        *(["    line [" + ", ".join(f"{ceiling:.4f}" for _ in scores) + "]"] if ceiling else []),
        "```", "",
        *([f"**North star (flat upper line): {ceiling:.4f}** — a perfect reranker of the "
           f"retrieval top{oracle['depth']} under the same labels. Not a system; optimistic "
           "because labels were pooled from saved systems' results. The current reranking "
           f"baseline is {ceiling - current:.4f} below it.", ""] if ceiling else []),
        "| Stage | Milestone | Saved identity | nDCG@10 | Step gain | Source MRR@10 | Source R@10 |",
        "|---|---|---|---|---|---|---|", *milestone_rows, "",
        "**Reading the curve:** big earlier jumps came from complementary lexical/semantic "
        "retrieval and better embeddings. The 75%-RRF point was a challenger, not an approved "
        "baseline. The balanced RRF55% point recovered known-paper ranks. The current "
        "shortlist-score baseline improves ordering while preserving its top10 membership. "
        "These steps also change other parameters, so step differences are not isolated "
        "causal effects of one feature. The reranker step is one of the largest on the "
        "curve. Without the safeguard, the top-50 reranker scores higher on "
        "nDCG but pushes source papers down; the safeguard keeps most of the gain and "
        "improves source MRR.", "",
        "## Latest scores: Stage 1 retrieval leaders", "",
        "Labels L1 onward below are chart keys, not separate system names. "
        "The top five ranked retrieval systems are shown, plus the retrieval baseline if it falls "
        "outside those five. Exact score ties use stable system IDs for ordering; a "
        "different ordinal rank within a tie is not a quality change. Highest nDCG "
        "does not automatically mean best balanced baseline. "
        f"**Zoomed linear y-axis: {latest_lower:.2f}-{latest_upper:.2f}, not zero-based.** "
        "The line connects systems in displayed rank order, not time or a development "
        "trajectory. Small gaps are not evidence of statistically significant differences; "
        "use the table for exact scores. Each comparison chart has its own scale.", "",
        "```mermaid", "xychart-beta", '    title "Latest dev leaderboard nDCG@10"',
        "    x-axis [" + ", ".join(f"L{i}" for i in range(1, len(latest) + 1)) + "]",
        f'    y-axis "nDCG@10 (zoomed, higher is better)" {latest_lower:g} --> {latest_upper:g}',
        "    line [" + ", ".join(f"{score:.4f}" for score in latest_scores) + "]",
        "```", "",
        "| Chart key / rank | Ranker | nDCG@10 | Source MRR@10 | R@10 | Status |",
        "|---|---|---|---|---|---|",
    ]
    for index, name in enumerate(latest, 1):
        result = systems[name]
        status = ("**APPROVED BASELINE** (retrieval)" if result["working_baseline"]
                  else "experiment / control")
        lines.append(
            f"| L{index} / #{result['leaderboard_rank']} | {result['description']['ranker']} | "
            f"{result['all']['ndcg@10']['mean']:.4f} | "
            f"{result['all']['source_mrr@10']['mean']:.4f} | "
            f"{result['all']['source_recall@10']['mean']:.0%} | {status} |")
    if stage2:
        order = report["stage2"].get("ranked", []) + report["stage2"].get("unranked", [])
        stage2_scores = [stage2[n]["all"]["ndcg@10"]["mean"] for n in order]
        stage2_lower, stage2_upper = _comparison_bounds(stage2_scores)
        lines += [
            "", "## Latest scores: Stage 2 reranking (retrieval + reranker)", "",
            "Every row reorders the same retrieval-baseline candidates for all 100 dev "
            "queries. Δ is paired against the retrieval baseline; the noise band comes from "
            "re-sending identical requests (Decision44). "
            f"**Zoomed linear y-axis: {stage2_lower:.2f}-{stage2_upper:.2f}, not zero-based.** "
            "The line connects systems in table order, not time or a development trajectory. "
            "It shows mean scores, not uncertainty; use the paired intervals in the table "
            "to assess gains against the retrieval baseline. Each comparison chart has "
            "its own scale.", "",
            "```mermaid", "xychart-beta", '    title "Stage 2 nDCG@10 (100 dev queries)"',
            "    x-axis [" + ", ".join(f"S{i}" for i in range(1, len(order) + 1)) + "]",
            f'    y-axis "nDCG@10 (zoomed, higher is better)" {stage2_lower:g} --> {stage2_upper:g}',
            "    line [" + ", ".join(f"{score:.4f}" for score in stage2_scores) + "]",
            "```", "",
            "| Chart key | System | nDCG@10 | Δ vs retrieval baseline | Source MRR@10 | R@10 "
            "| LLM $/query | Status |", "|---|---|---|---|---|---|---|---|",
        ]
        for index, name in enumerate(order, 1):
            result = stage2[name]
            paired = result.get("paired_ndcg_vs_retrieval_baseline")
            status = ("**APPROVED BASELINE** (reranking)" if result.get("reranking_baseline")
                      else "**APPROVED BASELINE** (retrieval, no reranker)"
                      if result.get("retrieval_baseline") else "experiment")
            lines.append(
                f"| S{index} | `{name}` | {result['all']['ndcg@10']['mean']:.4f} | "
                + (f"{paired['difference']:+.3f} [{paired['ci95'][0]:+.3f}, "
                   f"{paired['ci95'][1]:+.3f}]" if paired else "—")
                + f" | {result['all']['source_mrr@10']['mean']:.4f} | "
                f"{result['all']['source_recall@10']['mean']:.0%} | "
                + (f"${result['cost']['usd_per_query']:.4f}" if result.get("cost") else "—")
                + f" | {status} |")
    lines += [
        "", "## Where the next big jump would have to come from", "",
        f"- Retrieval baseline nDCG: **{retrieval_score:.4f}** (diagnostics below are for "
        "Stage 1, the candidates the reranker sees).",
        f"- Perfect label-aware ordering of the **same selected ten papers** reaches only "
        f"**{diagnosis['oracle_ndcg_with_fixed_top10']:.4f}** on this snapshot. This is a "
        "diagnostic oracle, not a measured model or a prediction of achievable gains.",
        f"- Current shortlist contains the source in **{diagnosis['source_hits_current_top10']}/"
        f"{diagnosis['queries']}** queries. The raw lexical/semantic union contains it in "
        f"**{diagnosis['source_hits_in_retriever_union']['100']}/"
        f"{diagnosis['queries']}** at depth100 per retriever and "
        f"**{diagnosis['source_hits_in_retriever_union']['500']}/"
        f"{diagnosis['queries']}** at depth500. Candidate availability is not final ranking quality.",
        f"- Of {diagnosis['queries'] * 10} selected results, "
        f"**{diagnosis['top10_grade_counts']['0']} are grade0**, "
        f"{diagnosis['top10_grade_counts']['1']} grade1, and "
        f"{diagnosis['top10_grade_counts']['2']} grade2. A fixed shortlist cannot replace the grade0s.",
        "", "Next hypotheses: improve candidate selection with query-document interaction "
        "or better query/document representations, rather than endlessly tuning global fusion "
        "weights. The Stage 2 LLM reranker (Decision45) is the first step past the fixed "
        "shortlist: it reorders the top 50 rather than the top 10. "
        "More independent evaluation is also needed: 100 synthetic dev queries and a calibrated "
        "LLM judge are not proof of generalization. The held-out 300 queries remain untouched.",
        "", "## Reproducibility and cautions", "",
        f"- Retrieval baseline: `{report['working_baseline']}` (Decision36).",
        *([f"- Reranking baseline: `{rerank}` (Decision{config.RERANK_BASELINE_DECISION}): "
           f"Decision46's {config.RERANK_BASELINE_PASSES}-pass top-{config.RERANK_BASELINE_DEPTH} "
           f"scores, then a {config.RERANK_REFINE_PASSES}-pass top-{config.RERANK_REFINE_DEPTH} "
           "refinement keeping its rank 1; LLM scores vary "
           "run to run, so its point uses the saved, cached rankings."]
          if rerank in stage2 else []),
        f"- Label snapshot: `{report['label_snapshot']}`; SHA256 `{report['label_snapshot_sha256']}`.",
        "- Original plain-BM25 graded coverage is incomplete, so it is excluded from the hill curve.",
        "- Frozen experiment reports retain their original controls; only the unified leaderboard "
        "uses the latest working baseline for paired differences.",
        "- All intervals elsewhere are exploratory after repeated dev selection. No fresh-human "
        "validation or held-out claim is implied.",
        "- Charts use Mermaid, rendered by GitHub; the tables are an exact readable fallback.",
        "- [Full leaderboard](05-results.md#unified-dev-scorecard)",
        "- [Promotion and loss findings](03-findings.md#23-rankscore-experiments-and-recall-preserving-baseline)",
        "- [Machine-readable promotion/headroom audit](../data/results/baseline-promotion-dev/report.json)",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    from arxiv_search.evaluate.experiments import write_results_doc

    root = config.RESULTS_DIR
    papers, queries, split = judge.load_inputs()
    _, _, snapshot, _ = results_catalog.load_shared_labels(root)
    inputs = json.loads((root / "score-fusion-dev" / "input-scores.json").read_text())
    run = json.loads((root / "shortlist-score-dev" / f"{config.WORKING_BASELINE_SYSTEM}.run.json").read_text())
    fusion.validate_run(config.WORKING_BASELINE_SYSTEM, run, sorted(split["dev"]), papers, exact_depth=100)
    if set(split["dev"]) & set(split["test"]):
        raise ValueError("Dev/test overlap")
    for q, values in inputs.items():
        if q not in run or fuse_working_baseline(dict(values["lexical"]), dict(values["semantic"])) != run[q]:
            raise ValueError(f"{q}: working helper differs from approved rankings")
    if set(inputs) != set(run):
        raise ValueError("Raw inputs and approved dev rankings differ")
    diagnosis = bottlenecks(run, snapshot["labels"], inputs, queries)
    write_results_doc()
    report = json.loads((root / "catalog-dev" / "report.json").read_text())
    if report["systems"][config.WORKING_BASELINE_SYSTEM]["ranking_sha256"] != results_catalog._fingerprint(run):
        raise ValueError("Leaderboard baseline differs from approved ranking")
    diagnosis.update(
        working_baseline=config.WORKING_BASELINE_SYSTEM, decision=36,
        approved=True, exact_rankings_verified=len(run), api_calls=0,
        ranking_sha256=fusion.fingerprint(run),
        label_snapshot_sha256=report["label_snapshot_sha256"],
        leaderboard_rank=report["systems"][config.WORKING_BASELINE_SYSTEM]["leaderboard_rank"],
    )
    out = root / "baseline-promotion-dev"
    out.mkdir(parents=True, exist_ok=True)
    fusion._write_json(out / "report.json", diagnosis)
    charts = render_charts(report, diagnosis)
    (config.PROJECT_ROOT / "docs" / "06-charts.md").write_text(charts, encoding="utf-8")
    print(f"Verified {len(run)} approved rankings; baseline rank "
          f"{diagnosis['leaderboard_rank']}; generated charts; zero API calls.")


if __name__ == "__main__":
    main()
