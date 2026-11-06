"""Offline disagreement analysis of the frozen pilot20; never calls a provider."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import Counter

from arxiv_search import config, openai_rerank
from arxiv_search.evaluate import metrics, top20_ablations as ab
from arxiv_search.evaluate import top20_model_pilot as model, top20_reasoning_pilot as reasoning
from arxiv_search.evaluate.cross_encoder_experiment import freeze

OUT = config.RESULTS_DIR / "top20-reasoning-diagnostics"


def disagreements(before: list[str], after: list[str], grades: dict[str, int],
                  k: int = 10) -> dict:
    if (len(before) != 20 or len(set(before)) != 20 or set(before) != set(after)
            or len(after) != 20 or not 1 <= k <= 20
            or any(p not in grades for p in before)):
        raise ValueError("Expected the same fully judged twenty unique papers")
    ideal = metrics.dcg(sorted(grades.values(), reverse=True)[:k])
    if ideal <= 0:
        raise ValueError("Undefined nDCG")
    old = {p: i for i, p in enumerate(before, 1)}
    new = {p: i for i, p in enumerate(after, 1)}

    def weight(rank: int) -> float:
        return 1 / math.log2(rank + 1) if rank <= k else 0

    contributions = [{"paper_id": p, "grade": grades[p], "before_rank": old[p],
                      "after_rank": new[p],
                      "ndcg_contribution": grades[p] * (weight(new[p]) - weight(old[p])) / ideal}
                     for p in before if old[p] != new[p]]
    corrected = introduced = 0
    for i, a in enumerate(before):
        for b in before[i + 1:]:
            if grades[a] == grades[b] or new[a] < new[b]:
                continue
            corrected += grades[a] < grades[b]
            introduced += grades[a] > grades[b]
    entrants = [p for p in after[:k] if old[p] > k]
    exits = [p for p in before[:k] if new[p] > k]
    return {
        "delta": sum(r["ndcg_contribution"] for r in contributions),
        "entrants": entrants, "exits": exits,
        "entrants_by_grade": dict(Counter(str(grades[p]) for p in entrants)),
        "exits_by_grade": dict(Counter(str(grades[p]) for p in exits)),
        "unequal_grade_inversions_corrected": corrected,
        "unequal_grade_inversions_introduced": introduced,
        "contributions": contributions,
    }


def run() -> dict:
    hashes = {}

    def read(path):
        raw = path.read_bytes()
        hashes[str(path.relative_to(config.PROJECT_ROOT))] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    plan = read(reasoning.OUT / "preregistration.json")
    source = read(model.OUT / "preregistration.json")
    split = read(config.EVAL_DIR / "split.json")
    reasoning.validate_scope(plan["pilot_queries"], plan["requests"], split)
    if plan["pilot_queries"] != source["pilot_queries"]:
        raise ValueError("Pilot scopes differ")
    base_path = config.RESULTS_DIR / "llm-score-pass2" / (
        "llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30.run.json")
    labels_path = config.RESULTS_DIR / "top20-label-completion" / "labels.json"
    base, labels = read(base_path), read(labels_path)["labels"]
    for name, path in (("labels", labels_path), ("d46", base_path)):
        if hashes[str(path.relative_to(config.PROJECT_ROOT))] != plan["evidence_sha256"][name]:
            raise ValueError("Frozen evidence changed")
    expected = {r["query_id"]: r for r in read(reasoning.OUT / "report.json")["rows"]
                if r["method"] == "scores_only"}
    files = {"queries": config.EVAL_DIR / "queries.jsonl",
             "papers": config.PROJECT_ROOT / "data" / "processed" / "corpus.jsonl"}
    records = {}
    for name, path in files.items():
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        key = "corpus" if name == "papers" else name
        if digest != plan["evidence_sha256"][key]:
            raise ValueError("Frozen query or corpus evidence changed")
        hashes[str(path.relative_to(config.PROJECT_ROOT))] = digest
        id_key = "arxiv_id" if name == "papers" else "query_id"
        records[name] = {r[id_key]: r for line in raw.decode("utf-8").splitlines()
                         if (r := json.loads(line))}
    rows = []
    for index, request in enumerate(plan["requests"]):
        q, presented = request["query_id"], request["presented_ids"]
        replies = {"none": [], "low": []}
        for setting in replies:
            for n in (1, 2):
                path = (model.OUT / "responses" if setting == "none" else
                        reasoning.OUT / ("feasibility" if index == 0 else "responses"))
                saved = read(path / f"{q}-pass{n}.json")
                frozen = source["requests"][index] if setting == "none" else request
                if (frozen["query_id"] != q or frozen["presented_ids"] != presented
                        or saved["request_sha256"] != frozen["payload_sha256"]
                        or saved["outcome"]["status"] != "ok"):
                    raise ValueError("Invalid cached evidence")
                replies[setting].append(openai_rerank.validate_refine_scores(
                    {k: v for k, v in saved["outcome"].items() if k != "status"}))
        rankings = {s: ab.ranking(base[q], presented, r, "scores_only", "average")
                    for s, r in replies.items()}
        if rankings["low"][:20] != expected[q]["top20"]:
            raise ValueError("Does not reproduce saved reasoning ranking")
        scores = {s: metrics.ndcg_at_k(r, labels[q]) for s, r in rankings.items()}
        if (scores["none"] != expected[q]["reference"]
                or scores["low"] != expected[q]["candidate"]):
            raise ValueError("Does not reproduce saved metrics")
        detail = disagreements(rankings["none"][:20], rankings["low"][:20], labels[q])
        if not math.isclose(detail["delta"], scores["low"] - scores["none"], abs_tol=1e-12):
            raise ValueError("Per-paper contributions do not reconcile")
        paper_rows = []
        contribution = {r["paper_id"]: r for r in detail["contributions"]}
        for i, p in enumerate(presented, 1):
            values = {s: [r[f"P{i}"] for r in replies[s]] for s in replies}
            paper = records["papers"][p]
            paper_rows.append({
                "paper_id": p, "grade": labels[q][p], "title": paper["title"],
                "abstract": paper["abstract"], "authors": paper["authors"],
                "scores": values, "means": {s: statistics.fmean(v) for s, v in values.items()},
                "before_rank": rankings["none"].index(p) + 1,
                "after_rank": rankings["low"].index(p) + 1,
                "ndcg_contribution": contribution.get(p, {}).get("ndcg_contribution", 0),
            })
        query = records["queries"][q]
        rows.append({"query_id": q, "query": query["query"], "query_type": query["query_type"],
                     "ndcg": scores, **detail, "papers": paper_rows})
    summary = {
        "queries": len(rows),
        "none_ndcg": statistics.fmean(r["ndcg"]["none"] for r in rows),
        "low_ndcg": statistics.fmean(r["ndcg"]["low"] for r in rows),
        "mean_delta": statistics.fmean(r["delta"] for r in rows),
        "gross_positive_query_gain": sum(max(0, r["delta"]) for r in rows) / len(rows),
        "gross_negative_query_loss": sum(min(0, r["delta"]) for r in rows) / len(rows),
        "corrected_inversions": sum(r["unequal_grade_inversions_corrected"] for r in rows),
        "introduced_inversions": sum(r["unequal_grade_inversions_introduced"] for r in rows),
        "entrants_by_grade": dict(sum((Counter(r["entrants_by_grade"]) for r in rows), Counter())),
        "exits_by_grade": dict(sum((Counter(r["exits_by_grade"]) for r in rows), Counter())),
    }
    result = {"summary": summary, "rows": sorted(rows, key=lambda r: -r["delta"]),
              "provenance": hashes, "scope": "Saved pilot20 only; no provider or ledger access.",
              "limitations": "Post-hoc descriptive diagnostics against pooled model labels. "
                              "Corrected/introduced inversions use all20 and are not nDCG. "
                              "Per-paper contributions are accounting, not causal explanations. "
                              "No hidden reasoning text is available; infer no model rationale."}
    OUT.mkdir(parents=True, exist_ok=True)
    freeze(OUT / "report.json", result)
    return result


if __name__ == "__main__":
    report = run()
    print(json.dumps(report["summary"], indent=2))
    for row in report["rows"]:
        print(f"{row['query_id']}: {row['delta']:+.5f} | {row['query']}")
