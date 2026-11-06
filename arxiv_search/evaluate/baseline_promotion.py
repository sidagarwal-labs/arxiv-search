"""Verify the approved Decision36 profile and generate comparable progress charts.

python -m arxiv_search.evaluate.baseline_promotion
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics

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


RERANK_MILESTONE = "GPT-5.4 mini top-20 refinement + safeguard"
PRIOR_RERANK_MILESTONE = "GPT-5.4 mini top-50 rerank + safeguard"
D50_MILESTONE = "GPT-5.4 2-pass top-20 refinement"
D50_SYSTEM = "llm-gpt54-refine20+d=20+avg2+scores+pin1-d46"


def _comparison_bounds(scores: list[float]) -> tuple[float, float]:
    return (
        max(0, (math.floor(min(scores) * 100) - 1) / 100),
        min(1, (math.ceil(max(scores) * 100) + 1) / 100),
    )


def load_d50_comparison(root) -> dict:
    old_raw = (root / "shared-labels" / "labels-d47.json").read_bytes()
    old = json.loads(old_raw)["labels"]
    expanded_raw = (root / "top20-label-completion" / "labels.json").read_bytes()
    expanded = json.loads(expanded_raw)
    labels = expanded["labels"]
    if expanded["parent_sha256"] != hashlib.sha256(old_raw).hexdigest():
        raise ValueError("D50 labels do not match the D47 parent snapshot")
    if len(labels) != 100 or set(labels) != set(old) or any(
        labels[q].get(p) != grade for q, grades in old.items() for p, grade in grades.items()
    ):
        raise ValueError("D50 label layer must preserve the D47 queries and grades")
    summary = json.loads((root / "top20-confirm" / "dev100-summary.json").read_bytes())
    confirm = json.loads((root / "top20-confirm" / "report.json").read_bytes())
    plan = json.loads((root / "top20-confirm" / "preregistration.json").read_bytes())
    if plan["fingerprints"]["labels"] != hashlib.sha256(expanded_raw).hexdigest():
        raise ValueError("D50 confirmation used a different label layer")
    if not confirm["confirmed"] or not all(confirm["checks"].values()):
        raise ValueError("D50 confirmation is not complete")
    runs = {
        "d47": root / "llm-score-refine-pin" / (
            "llm-mini-refine20+d=20+avg2+rrf-d46+c=30+pin1-d46.run.json"),
        "d50": root / "top20-confirm" / f"{D50_SYSTEM}.run.json",
    }
    scored = {}
    precisions = {}
    for name, path in runs.items():
        run = json.loads(path.read_bytes())
        if name == "d47" and plan["fingerprints"]["d47"] != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError("D50 confirmation used a different D47 ranking")
        if set(run) != set(labels) or any(
            len(run[q]) < 10 or any(p not in labels[q] for p in run[q][:10])
            for q in labels
        ):
            raise ValueError(f"{name} must have fully judged top-10s for every query")
        values = [metrics.ndcg_at_k(run[q], labels[q]) for q in sorted(labels)]
        if any(value is None for value in values):
            raise ValueError(f"{name} has undefined nDCG")
        score = statistics.fmean(value for value in values if value is not None)
        if not math.isclose(score, summary[name]["ndcg@10"], abs_tol=1e-10):
            raise ValueError(f"{name} saved summary does not match rankings and labels")
        precisions[name] = statistics.fmean(
            sum(labels[q][paper] >= 1 for paper in run[q][:10]) / 10 for q in labels
        )
        scored[name] = dict(zip(sorted(labels), values))
    rows = confirm["rows"]
    if len(rows) != 80 or {row["query_id"] for row in rows} != set(plan["query_ids"]) or any(
        row["query_id"] not in labels or not row["candidate_fully_judged"] for row in rows
    ):
        raise ValueError("D50 confirmation must contain 80 fully judged dev queries")
    if any(not math.isclose(row[key], scored[name][row["query_id"]], abs_tol=1e-10)
           for row in rows for name, key in (("d47", "d47"), ("d50", "candidate"))):
        raise ValueError("D50 confirmation scores do not match the saved rankings")
    if not math.isclose(summary["ndcg_delta"],
                        summary["d50"]["ndcg@10"] - summary["d47"]["ndcg@10"],
                        abs_tol=1e-10):
        raise ValueError("D50 summary delta does not match the scores")
    return {
        "summary": summary,
        "confirm_d47": statistics.fmean(row["d47"] for row in rows),
        "confirm_d50": statistics.fmean(row["candidate"] for row in rows),
        "precision_at_10": precisions["d50"],
        "pair_count": sum(len(grades) for grades in labels.values()),
        "parent_sha256": expanded["parent_sha256"],
    }


def render_charts(report: dict, diagnosis: dict, d50: dict | None = None) -> str:
    if d50 and report["label_snapshot_sha256"] != d50["parent_sha256"]:
        raise ValueError("Historical chart and D50 comparison use different parent labels")
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
    if d50:
        scores_for_bounds = scores + [d50["summary"]["d50"]["ndcg@10"]]
    else:
        scores_for_bounds = scores
    upper = max(0.75, math.ceil(max(
        scores_for_bounds + ([ceiling] if ceiling and not d50 else [])) * 20) / 20)
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
    latest_points = sorted(enumerate(latest, 1),
                           key=lambda point: systems[point[1]]["all"]["ndcg@10"]["mean"])
    latest_scores = [systems[n]["all"]["ndcg@10"]["mean"] for _, n in latest_points]
    latest_lower, latest_upper = _comparison_bounds(latest_scores)
    new_scores = ([d50["summary"]["d47"]["ndcg@10"], d50["summary"]["d50"]["ndcg@10"]]
                  if d50 else [])
    lines = [
        "# Search quality charts", "",
        "*Generated by `python -m arxiv_search.evaluate.baseline_promotion`; do not edit by hand.*",
        "", '<a id="hill-climbing-major-comparable-milestones"></a>', "",
        "## Hill climbing: major milestones", "",
        f"Milestones use 100 dev queries, 23,304 searchable papers. "
        + (f"Earlier results use the **{label_text}**. " if d50 else
           f"Results use the **{label_text}**. ") +
        "Stage 1 points are retrieval baselines "
        "and turning points; the Stage 2 point adds the LLM reranker on top of the current "
        "retrieval baseline. These are selected milestones, not "
        "every trial, independent experiments, or equally spaced dates. The x-axis is "
        f"milestone order. **Zoomed linear y-axis: {lower:.2f}-{upper:.2f}, not zero-based.** "
        "This focuses on score changes, not their magnitude relative to zero. "
        "All plotted top10s are fully judged; no held-out test scores are included. "
        + ("D50 includes 20 queries used to select it. " if d50 else "") +
        "Scores "
        "shifted down slightly from older versions of this page when reranker top-10 grades "
        "joined the shared labels (167 in Decision45, 72 in Decision46); the curve's shape "
        "is unchanged.",
        "",
        *([f"**Current reranking baseline: GPT-5.4 two-pass top-20 refinement, "
           f"{new_scores[1]:.4f} nDCG@10**, with a measured "
           f"{d50['summary']['ndcg_delta']:+.4f} gain against D47.", ""] if d50 else []),
        f"**First plotted baseline to D47 on the historical layer: {scores[0]:.4f} to {current:.4f} "
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
        "    x-axis [" + ", ".join(
            [f'\"{label}\"' for label, *_ in points]
            + ([f'"{D50_MILESTONE}"'] if d50 else [])) + "]",
        f'    y-axis "nDCG@10 (zoomed, higher is better)" {lower:g} --> {upper:g}',
        "    line [" + ", ".join(f"{v:.4f}" for v in scores + new_scores[1:]) + "]",
        *(["    line [" + ", ".join(f"{ceiling:.4f}" for _ in scores) + "]"]
          if ceiling and not d50 else []),
        "```", "",
        *([f"**Historical north star: {ceiling:.4f}** — a perfect reranker of the "
           f"retrieval top{oracle['depth']} under the same labels. Not a system; optimistic "
           "because labels were pooled from saved systems' results. D47 on that historical "
           f"layer is {ceiling - current:.4f} below it.", ""] if ceiling else []),
        *([f"*D50 and its +{d50['summary']['ndcg_delta']:.4f} step are measured on "
           f"{d50['pair_count']:,} judgments; the same-pool D47 control scores "
           f"{new_scores[0]:.4f}. Earlier points use 3,579 judgments, so the plotted "
           "difference from the preceding point is not the measured step gain.*", ""] if d50 else []),
        "| Stage | Milestone | Saved identity | nDCG@10 | Step gain | Source MRR@10 | Source R@10 |",
        "|---|---|---|---|---|---|---|", *milestone_rows,
        *([f"| 2 reranking | {D50_MILESTONE} | `{D50_SYSTEM}` | {new_scores[1]:.4f} | "
           f"{d50['summary']['ndcg_delta']:+.4f} | "
           f"{d50['summary']['d50']['source_mrr@10']:.4f} | "
           f"{d50['summary']['d50']['source_recall@10']:.0%} |"] if d50 else []), "",
        "**Reading the curve:** big earlier jumps came from complementary lexical/semantic "
        "retrieval and better embeddings. The 75%-RRF point was a challenger, not an approved "
        "baseline. The balanced RRF55% point recovered known-paper ranks. The current "
        "shortlist-score baseline improves ordering while preserving its top10 membership. "
        "These steps also change other parameters, so step differences are not isolated "
        "causal effects of one feature. The reranker step is one of the largest on the "
        "curve. Without the safeguard, the top-50 reranker scores higher on "
        "nDCG but pushes source papers down; the safeguard keeps most of the gain and "
        "improves source MRR.", "",
        *([f"**GPT-5.4 refinement confirmation:** on the 80 confirmation queries, "
           f"{d50['confirm_d47']:.4f} → "
           f"**{d50['confirm_d50']:.4f}**; the other 20 informed selection. "
           "[Confirmation report](../data/results/top20-confirm/report.md).", ""] if d50 else []),
        "## Latest scores: Stage 1 retrieval leaders", "",
        "Labels L1 onward below are chart keys, not separate system names. "
        "The top five ranked retrieval systems are shown, plus the retrieval baseline if it falls "
        "outside those five. Exact score ties use stable system IDs for ordering; a "
        "different ordinal rank within a tie is not a quality change. Highest nDCG "
        "does not automatically mean best balanced baseline. "
        f"**Zoomed linear y-axis: {latest_lower:.2f}-{latest_upper:.2f}, not zero-based.** "
        "The chart runs from lowest to highest score; the table stays highest-first. "
        "Chart keys still identify the same table rows. This is score order, "
        "not time or a development trajectory. Small gaps are not evidence of "
        "statistically significant differences; "
        "use the table for exact scores. Each comparison chart has its own scale.", "",
        "```mermaid", "xychart-beta", '    title "Latest dev leaderboard nDCG@10"',
        "    x-axis [" + ", ".join(f"L{i}" for i, _ in latest_points) + "]",
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
        if d50:
            stage2 = dict(stage2)
            result = d50["summary"]["d50"]
            stage2[D50_SYSTEM] = {
                "all": {key: {"mean": result[key]} for key in
                        ("ndcg@10", "source_mrr@10", "source_recall@10")},
                "d50_baseline": True,
            }
            order = sorted(order + [D50_SYSTEM],
                           key=lambda n: -stage2[n]["all"]["ndcg@10"]["mean"])
        stage2_points = sorted(enumerate(order, 1),
                               key=lambda point: stage2[point[1]]["all"]["ndcg@10"]["mean"])
        stage2_scores = [stage2[n]["all"]["ndcg@10"]["mean"] for _, n in stage2_points]
        stage2_lower, stage2_upper = _comparison_bounds(stage2_scores)
        lines += [
            "", "## Latest scores: Stage 2 reranking (retrieval + reranker)", "",
            ("D50 uses the completed 3,678-judgment pool; other rows use 3,579 judgments. "
             if d50 else "") +
            "Every row reorders the same retrieval-baseline candidates for all 100 dev "
            "queries. Δ is paired against the retrieval baseline; the noise band comes from "
            "re-sending identical requests (Decision44). "
            f"**Zoomed linear y-axis: {stage2_lower:.2f}-{stage2_upper:.2f}, not zero-based.** "
            "The chart runs from lowest to highest score; the table stays highest-first. "
            "Chart keys still identify the same table rows. This is score order, "
            "not time or a development trajectory. "
            "It shows mean scores, not uncertainty; use the paired intervals in the table "
            "to assess gains against the retrieval baseline. Each comparison chart has "
            "its own scale.", "",
            "```mermaid", "xychart-beta", '    title "Stage 2 nDCG@10 (100 dev queries)"',
            "    x-axis [" + ", ".join(f"S{i}" for i, _ in stage2_points) + "]",
            f'    y-axis "nDCG@10 (zoomed, higher is better)" {stage2_lower:g} --> {stage2_upper:g}',
            "    line [" + ", ".join(f"{score:.4f}" for score in stage2_scores) + "]",
            "```", "",
            "| Chart key | System | nDCG@10 | Δ vs retrieval baseline | Source MRR@10 | R@10 "
            "| LLM $/query | Status |", "|---|---|---|---|---|---|---|---|",
        ]
        for index, name in enumerate(order, 1):
            result = stage2[name]
            paired = result.get("paired_ndcg_vs_retrieval_baseline")
            if result.get("d50_baseline"):
                status = "**APPROVED BASELINE** (GPT-5.4 two-pass top-20 refinement)"
            elif result.get("reranking_baseline"):
                status = ("historical reranking baseline (D47)" if d50 else
                          "**APPROVED BASELINE** (reranking)")
            elif result.get("retrieval_baseline"):
                status = "**APPROVED BASELINE** (retrieval, no reranker)"
            else:
                status = "experiment"
            system = (f"GPT-5.4 two-pass top-20 scoring; average scores; keep rank 1<br>`{name}`"
                      if result.get("d50_baseline") else f"`{name}`")
            lines.append(
                f"| S{index} | {system} | {result['all']['ndcg@10']['mean']:.4f} | "
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
        *([f"- {'Historical reranking baseline' if d50 else 'Reranking baseline'}: `{rerank}` (Decision{config.RERANK_BASELINE_DECISION}): "
           f"Decision46's {config.RERANK_BASELINE_PASSES}-pass top-{config.RERANK_BASELINE_DEPTH} "
           f"scores, then a {config.RERANK_REFINE_PASSES}-pass top-{config.RERANK_REFINE_DEPTH} "
           "refinement keeping its rank 1; LLM scores vary "
           "run to run, so its point uses the saved, cached rankings."]
          if rerank in stage2 else []),
        *(["- Current reranking baseline: Decision50; its expanded-label comparison is above."]
          if d50 else []),
        f"- Label snapshot: `{report['label_snapshot']}`; SHA256 `{report['label_snapshot_sha256']}`.",
        "- Original plain-BM25 graded coverage is incomplete, so it is excluded from the hill curve.",
        "- Frozen experiment reports retain their original controls; the historical unified "
        "leaderboard uses its D47-era baseline for paired differences.",
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
    charts = render_charts(report, diagnosis, load_d50_comparison(root))
    (config.PROJECT_ROOT / "docs" / "06-charts.md").write_text(charts, encoding="utf-8")
    print(f"Verified {len(run)} approved rankings; baseline rank "
          f"{diagnosis['leaderboard_rank']}; generated charts; zero API calls.")


if __name__ == "__main__":
    main()
