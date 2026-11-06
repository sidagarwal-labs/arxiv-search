"""Free pilot20-only ablations of saved GPT-5.4 scores. No provider transport."""

from __future__ import annotations

import hashlib
import json
import statistics

from arxiv_search import config, openai_rerank
from arxiv_search.evaluate import metrics
from arxiv_search.evaluate.cross_encoder_experiment import freeze

OUT = config.RESULTS_DIR / "top20-ablations"
SOURCE = config.RESULTS_DIR / "top20-model-pilot"
METHODS = ("equal_rrf", "model_heavy_rrf", "scores_only")
PASSES = ("average", "pass1", "pass2")


def ranking(base: list[str], presented: list[str], replies: list[dict], method: str,
            passes: str) -> list[str]:
    if method not in METHODS or passes not in PASSES:
        raise ValueError("Undeclared ablation variant")
    if (len(base) < 20 or len(set(base)) != len(base)
            or len(presented) != 20 or len(set(presented)) != 20
            or set(presented) != set(base[:20]) or len(replies) != 2):
        raise ValueError("Expected two passes over the same twenty unique candidates")
    scores = [openai_rerank.validate_refine_scores(reply) for reply in replies]
    chosen = scores if passes == "average" else [scores[0 if passes == "pass1" else 1]]
    values = {p: statistics.fmean(s[f"P{i}"] for s in chosen)
              for i, p in enumerate(presented, 1)}
    original_rank = {p: i for i, p in enumerate(base[:20], 1)}
    scored = sorted(base[:20], key=lambda p: (-values[p], original_rank[p]))
    if method != "scores_only":
        model_rank = {p: i for i, p in enumerate(scored, 1)}
        weight = 1 if method == "equal_rrf" else 2
        scored = sorted(base[:20], key=lambda p: (
            -(1 / (30 + original_rank[p]) + weight / (30 + model_rank[p])), original_rank[p]))
    pinned = [base[0]] + [p for p in scored if p != base[0]]
    return pinned + base[20:]


def summarize(rows: list[dict]) -> dict:
    def paired(key: str) -> dict:
        mean, low, high = metrics.bootstrap_ci([r[key] for r in rows])
        return {"mean": mean, "ci95": [low, high]}

    return {
        "queries": len(rows),
        "ndcg": statistics.fmean(r["ndcg"] for r in rows),
        "delta_vs_d47": paired("delta_vs_d47"),
        "delta_vs_stronger_reference": paired("delta_vs_stronger_reference"),
        "source_mrr_delta_vs_d47": statistics.fmean(r["source_delta"] for r in rows),
        "source_mrr_delta_vs_stronger_reference": statistics.fmean(
            r["source_delta_vs_reference"] for r in rows),
        "fully_judged": all(r["fully_judged"] for r in rows),
        "wins_losses_ties_vs_reference": [
            sum(r["delta_vs_stronger_reference"] > 1e-12 for r in rows),
            sum(r["delta_vs_stronger_reference"] < -1e-12 for r in rows),
            sum(abs(r["delta_vs_stronger_reference"]) <= 1e-12 for r in rows),
        ],
        "cached_refinement_usd_per_query": statistics.fmean(r["cost_usd"] for r in rows),
        "mean_api_seconds": statistics.fmean(r["api_seconds"] for r in rows),
    }


def run() -> dict:
    plan_path = SOURCE / "preregistration.json"
    plan = json.loads(plan_path.read_bytes())
    split = json.loads((config.EVAL_DIR / "split.json").read_bytes())
    qids = plan["pilot_queries"]
    if len(qids) != 20 or len(set(qids)) != 20 or not set(qids) <= set(split["dev"]):
        raise ValueError("Expected the existing twenty pilot dev queries only")
    if set(qids) & set(split["test"]):
        raise ValueError("Test overlap")
    ablation_plan = {
        "version": "top20-cached-ablation-v1", "scope": qids,
        "source_plan_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        "methods": {"equal_rrf": "base + model RRF weights1:1, c30",
                    "model_heavy_rrf": "base + model RRF weights1:2, c30",
                    "scores_only": "model score order, stable base tie-break"},
        "passes": list(PASSES), "pin_first": True, "tail_unchanged": True,
        "interpretation": "Nine declared cached variants, eight alternatives to the stronger "
                          "reference. Post-hoc exploratory selection; paired intervals are "
                          "unadjusted and not independent confirmation. Pass2 is diagnostic, "
                          "not permission to choose the better pass per query.",
        "cost_scope": "Saved uncached refinement cost only; excludes common D46 upstream cost. "
                      "Two-pass latency is max of sequential call durations, a hypothetical "
                      "parallel estimate, not measured serving latency.",
        "no_provider_calls": True, "no_remaining80_scoring": True, "no_promotion": True,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    freeze(OUT / "plan.json", ablation_plan)
    paths = {
        "d46": config.RESULTS_DIR / "llm-score-pass2" /
               "llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30.run.json",
        "d47": config.RESULTS_DIR / "llm-score-refine-pin" /
               "llm-mini-refine20+d=20+avg2+rrf-d46+c=30+pin1-d46.run.json",
        "labels": config.RESULTS_DIR / "top20-label-completion" / "labels.json",
        "queries": config.EVAL_DIR / "queries.jsonl",
        "source_report": SOURCE / "report.json",
    }
    raw = {k: p.read_bytes() for k, p in paths.items()}
    d46, d47 = json.loads(raw["d46"]), json.loads(raw["d47"])
    labels = json.loads(raw["labels"])["labels"]
    if hashlib.sha256(raw["labels"]).hexdigest() != plan["label_sha256"]:
        raise ValueError("Completed label pool changed")
    queries = {q["query_id"]: q for line in raw["queries"].decode().splitlines()
               if (q := json.loads(line))["query_id"] in qids}
    old_reference = {r["query_id"]: r for r in json.loads(raw["source_report"])["rows"]}
    rows = {f"{m}/{p}": [] for m in METHODS for p in PASSES}
    provenance = {k: hashlib.sha256(v).hexdigest() for k, v in raw.items()}
    agreement = []
    for request in plan["requests"]:
        q = request["query_id"]
        if q not in qids:
            raise ValueError("Unexpected query outside pilot20")
        base = d46[q]
        presented = request["presented_ids"]
        replies, usage = [], []
        for n in (1, 2):
            path = SOURCE / "responses" / f"{q}-pass{n}.json"
            saved_raw = path.read_bytes()
            provenance[path.name] = hashlib.sha256(saved_raw).hexdigest()
            saved = json.loads(saved_raw)
            if (saved["request_sha256"] != request["payload_sha256"]
                    or saved["outcome"]["status"] != "ok"):
                raise ValueError("Cached request mismatch or invalid reply")
            replies.append({k: v for k, v in saved["outcome"].items() if k != "status"})
            usage.append(saved["usage"])
        agreement += [abs(replies[0][f"P{i}"] - replies[1][f"P{i}"]) for i in range(1, 21)]
        reference = ranking(base, presented, replies, "equal_rrf", "average")
        if reference[:20] != old_reference[q]["top20"]:
            raise ValueError("Ablation reference does not reproduce the original pilot")
        if any(p not in labels[q] for p in base[:20]):
            raise ValueError("Top20 must be completely judged")
        if set(base[:20]) != set(d47[q][:20]):
            raise ValueError("D47 and D46 top20 sets differ")
        grades = labels[q]
        src = {queries[q]["source_arxiv_id"]: 2}
        baseline_score = metrics.ndcg_at_k(d47[q], grades)
        reference_score = metrics.ndcg_at_k(reference, grades)
        for method in METHODS:
            for passes in PASSES:
                ranked = ranking(base, presented, replies, method, passes)
                selected_usage = usage if passes == "average" else [usage[0 if passes == "pass1" else 1]]
                cost = sum(u["input_tokens"] * 2500 + u["output_tokens"] * 15000
                           for u in selected_usage) / 1e9
                score = metrics.ndcg_at_k(ranked, grades)
                rows[f"{method}/{passes}"].append({
                    "query_id": q, "query_type": queries[q]["query_type"], "ndcg": score,
                    "delta_vs_d47": score - baseline_score,
                    "delta_vs_stronger_reference": score - reference_score,
                    "source_delta": metrics.reciprocal_rank(ranked, src) -
                                    metrics.reciprocal_rank(d47[q], src),
                    "source_delta_vs_reference": metrics.reciprocal_rank(ranked, src) -
                                                 metrics.reciprocal_rank(reference, src),
                    "fully_judged": metrics.judged_at_k(ranked, grades) == 1,
                    "cost_usd": cost,
                    "api_seconds": max(u["latency_seconds"] for u in selected_usage),
                    "top20": ranked[:20],
                })
    if any(len(r) != 20 or len({x["query_id"] for x in r}) != 20 for r in rows.values()):
        raise ValueError("Incomplete pilot coverage")
    report = {
        "plan": ablation_plan, "provenance": provenance,
        "baseline_d47": statistics.fmean(r["ndcg"] - r["delta_vs_d47"]
                                        for r in rows["equal_rrf/average"]),
        "variants": {name: summarize(r) for name, r in rows.items()},
        "by_query_type": {name: {
            t: summarize([x for x in r if x["query_type"] == t])
            for t in sorted({x["query_type"] for x in r})} for name, r in rows.items()},
        "score_repeatability": {"exact": sum(g == 0 for g in agreement) / len(agreement),
                                "mean_absolute_gap": statistics.fmean(agreement)},
        "rows": rows,
    }
    freeze(OUT / "report.json", report)
    lines = ["# Cached GPT-5.4 refinement ablations", "", ablation_plan["interpretation"], "",
             f"D47 pilot20 nDCG@10: {report['baseline_d47']:.4f}.", "",
             "| Variant | nDCG | Delta vs stronger reference [95% CI] | Source MRR delta vs D47 | $ refinement/query | API seconds* |",
             "|---|---:|---:|---:|---:|---:|"]
    for name, v in report["variants"].items():
        d = v["delta_vs_stronger_reference"]
        lines.append(f"| {name} | {v['ndcg']:.4f} | {d['mean']:+.4f} "
                     f"[{d['ci95'][0]:+.4f}, {d['ci95'][1]:+.4f}] | "
                     f"{v['source_mrr_delta_vs_d47']:+.4f} | "
                     f"${v['cached_refinement_usd_per_query']:.4f} | {v['mean_api_seconds']:.2f} |")
    lines += ["", "* " + ablation_plan["cost_scope"], "",
              "All variants retain the rank-one pin; no new model requests, remaining80 scoring, "
              "test evaluation or promotion. Intervals do not account for variant selection.",
              "", "Source fingerprints, per-query and query-type results: [report.json](report.json)."]
    output = "\n".join(lines) + "\n"
    path = OUT / "report.md"
    if path.exists() and path.read_text(encoding="utf-8") != output:
        raise FileExistsError("Refusing to overwrite different ablation report")
    path.write_text(output, encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps({k: v for k, v in run().items()
                      if k in ("baseline_d47", "variants", "score_repeatability")}, indent=2))
