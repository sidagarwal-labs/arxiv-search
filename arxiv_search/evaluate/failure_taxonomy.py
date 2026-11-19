"""Failure taxonomy of the Decision 50 ranking on frozen dev evidence; never calls models.

    python -m arxiv_search.evaluate.failure_taxonomy --cases-only        # evidence to annotate
    python -m arxiv_search.evaluate.failure_taxonomy --freeze-fix-plan   # freeze the fix test
    python -m arxiv_search.evaluate.failure_taxonomy                     # report; needs both

Dev queries only: held-out rows of queries.jsonl are dropped before any use. Reads saved
rankings, the saved GPT-5.4 refinement replies behind Decision 50, the completed top-20
label layer that produced the published D50 nDCG@10, and the hand-authored
annotations.json. Writes cases.json, fix-plan.json, report.json and report.md. No API
calls, label changes, re-embedding or held-out scoring.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path

from arxiv_search import config
from arxiv_search.evaluate import judge, metrics
from arxiv_search.evaluate.cross_encoder_experiment import freeze
from arxiv_search.evaluate.judge_pilot import read_human_grades
from arxiv_search.evaluate.rerank_loss import aggregate, decompose

R = config.RESULTS_DIR
OUT = R / "failure-taxonomy"
ANNOTATIONS = OUT / "annotations.json"
LABELS = R / "top20-label-completion" / "labels.json"
PARENT_LABELS = R / "shared-labels" / "labels-d47.json"
LABEL_CORRECTION = R / "top20-label-completion" / "evaluator-correction.json"
PUBLISHED = R / "top20-confirm" / "dev100-summary.json"
D50_RUN_ID = "llm-gpt54-refine20+d=20+avg2+scores+pin1-d46"
RUNS = {  # D47 is the previous baseline, a sibling of D50 (both refine D46), not its input
    "d36": R / "shortlist-score-dev" / f"{config.WORKING_BASELINE_SYSTEM}.run.json",
    "d46": R / config.DECISION46_RUN_DIR / f"{config.DECISION46_RERANK_SYSTEM}.run.json",
    "d47": R / config.RERANK_BASELINE_RUN_DIR / f"{config.RERANK_BASELINE_SYSTEM}.run.json",
    "d50": R / "top20-confirm" / f"{D50_RUN_ID}.run.json",
}
COMPONENT_RUNS = {  # Decision 36 inputs; only their top 100 were saved
    "lexical": R / "dev" / f"{config.WORKING_BASELINE_LEXICAL}.run.json",
    "semantic": R / "dev" / f"{config.WORKING_BASELINE_SEMANTIC}.run.json",
}
K = config.NDCG_K
POOL = config.RERANK_BASELINE_DEPTH
REFINE = config.RERANK_REFINE_DEPTH
LOWEST = 10
MIN_CI_N = 5
SEGMENTS = (("query_type",), ("category",), ("specificity",), ("query_type", "category"))
STAGES = {
    "stage1_retrieval": f"Stage 1 (Decision 36) did not rank it in the top {POOL}; no reranker saw it",
    "d46_rerank": f"In the top {POOL}, but Decision 46 left it outside the top {REFINE} that "
                  "Decision 50 re-scores",
    "d50_refine": f"In Decision 50's top-{REFINE} pool, but the refinement ranked it below 10",
}
LOSS_STAGE = {"ordering_top10": "d50_refine", "selection_11_20": "d50_refine",
              "screening_21_50": "d46_rerank", "outside_top50": "stage1_retrieval"}
LABELERS = {"mini": "GPT-5.4 mini judge", "astra": "GPT-6 ASTRA reference override",
            "terra": "GPT-6 Terra top-20 completion", "unjudged": "unjudged"}
REQUIRED_PROVENANCE = ("Annotator model/name", "Collection method", "Annotation date",
                       "Annotators", "Inter-annotator agreement")
FIX_PLAN = OUT / "fix-plan.json"
REFINE_SOURCES = (R / "top20-model-pilot", R / "top20-confirm")  # pilot20 + remaining80 replies
MIN_GAIN = 0.0106  # Decision 50's frozen noise threshold (top20_confirm.MIN_GAIN)
MAX_SOURCE_MRR_LOSS = 0.02


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def rank_of(ranking: list[str], paper: str) -> int | None:
    return ranking.index(paper) + 1 if paper in ranking else None


# --- Inputs -------------------------------------------------------------------


def dev_queries(split_raw: bytes, queries_raw: bytes) -> tuple[list[str], dict]:
    """Dev IDs and rows; held-out rows are parsed only to be discarded."""
    split = json.loads(split_raw)
    qids = sorted(split["dev"])
    if len(set(qids)) != len(qids) or set(qids) & set(split["test"]):
        raise ValueError("Dev split must be unique and disjoint from test")
    dev = set(qids)
    queries = {}
    for line in queries_raw.decode("utf-8").splitlines():
        if line.strip() and (q := json.loads(line))["query_id"] in dev:
            queries[q["query_id"]] = q
    if set(queries) != dev:
        raise ValueError("queries.jsonl is missing dev queries")
    return qids, queries


def check_labels(layer: dict, parent: dict, parent_raw: bytes, qids: list[str]) -> dict:
    """Return the Terra additions after checking the layer is parent + exactly those grades."""
    if layer.get("parent_sha256") != sha256(parent_raw):
        raise ValueError("Completed top-20 layer was built from a different D47 layer")
    if parent.get("rubric_version") != judge.RUBRIC_VERSION:
        raise ValueError("Rubric changed since the label layer")
    labels = layer["labels"]
    if set(labels) != set(qids):
        raise ValueError("Label layer does not contain exactly the dev queries")
    if any(type(g) is not int or g not in (0, 1, 2) for gs in labels.values() for g in gs.values()):
        raise ValueError("Grades must be integers 0/1/2")
    if any(labels[q].get(p) != g for q, gs in parent["labels"].items() for p, g in gs.items()):
        raise ValueError("Completed layer changed or removed a parent grade")
    terra = {(r["query_id"], r["arxiv_id"]): r for r in layer["new_judgments"]}
    added = {(q, p) for q, gs in labels.items() for p in gs if p not in parent["labels"].get(q, {})}
    if added != set(terra) or any(labels[q][p] != r["grade"] for (q, p), r in terra.items()):
        raise ValueError("Added grades must be exactly the recorded top-20 completion")
    return terra


def check_lineage(runs: dict, qids: list[str]) -> None:
    """D46 reorders only the D36 top 50; D50 reorders only the D46 top 20 and keeps rank 1."""
    for name, run in runs.items():
        if set(run) != set(qids):
            raise ValueError(f"{name}: expected exactly the dev query IDs")
        for ids in run.values():
            if len(ids) < POOL or len(set(ids)) != len(ids):
                raise ValueError(f"{name}: rankings need {POOL}+ unique papers")
    for q in qids:
        d36, d46, d50 = runs["d36"][q], runs["d46"][q], runs["d50"][q]
        if set(d46[:POOL]) != set(d36[:POOL]) or d46[POOL:] != d36[POOL:]:
            raise ValueError(f"{q}: Decision 46 must reorder only the Decision 36 top {POOL}")
        if set(d50[:REFINE]) != set(d46[:REFINE]) or d50[REFINE:] != d46[REFINE:] or d50[0] != d46[0]:
            raise ValueError(f"{q}: Decision 50 must reorder only the Decision 46 top {REFINE}")


def check_published(rows: list[dict], published: dict) -> dict:
    computed = {k: statistics.fmean(r[k] for r in rows)
                for k in ("ndcg@10", "source_mrr@10", "source_recall@10")}
    for key, value in computed.items():
        if abs(value - published["d50"][key]) > 1e-9:
            raise ValueError(f"D50 {key} {value:.4f} does not reproduce the published "
                             f"{published['d50'][key]:.4f}")
    return computed


# --- Per-query evidence -------------------------------------------------------


def source_stage(ranks: dict) -> str | None:
    """Where the source paper left the top 10; None if D50 kept it there."""
    if ranks["d50"] is not None and ranks["d50"] <= K:
        return None
    if ranks["d36"] is None or ranks["d36"] > POOL:
        return "stage1_retrieval"
    if ranks["d46"] > REFINE:
        return "d46_rerank"
    return "d50_refine"


def loss_by_stage(loss: dict) -> dict:
    out = dict.fromkeys(STAGES, 0.0)
    for component, value in loss.items():
        out[LOSS_STAGE[component]] += value
    return out


def query_rows(runs: dict, components: dict, labels: dict, queries: dict) -> tuple[list, list]:
    """One row per query plus the D50 loss decomposition (all from the same labels)."""
    rows, decompositions = [], []
    for qid in sorted(labels):
        q, grades, d50 = queries[qid], labels[qid], runs["d50"][qid]
        src = q["source_arxiv_id"]
        ranks = {name: rank_of(run[qid], src) for name, run in {**components, **runs}.items()}
        parts = decompose(d50, runs["d36"][qid], grades)
        decompositions.append(parts)
        by_stage = loss_by_stage(parts["loss"])
        rows.append({
            "query_id": qid, "query": q["query"], "query_type": q["query_type"],
            "category": q["category"], "specificity": q["specificity"], "overlap": q["overlap"],
            "source_arxiv_id": src,
            "ndcg@10": metrics.ndcg_at_k(d50, grades),
            "source_mrr@10": metrics.reciprocal_rank(d50, {src: 2}),
            "source_recall@10": float(src in d50[:K]),
            "judged@10": metrics.judged_at_k(d50, grades),
            "source_grade": grades.get(src),
            "source_ranks": ranks, "source_stage": source_stage(ranks),
            "graded_loss": by_stage,
            "graded_loss_stage": (max(STAGES, key=lambda s: by_stage[s])
                                  if sum(by_stage.values()) > 1e-12 else None),
        })
    return rows, decompositions


def failure_stage(row: dict) -> str | None:
    """Source stage for a source miss, else the stage holding most graded loss."""
    return row["source_stage"] or row["graded_loss_stage"]


def select_cases(rows: list[dict], lowest: int = LOWEST) -> dict[str, list[str]]:
    """Every source miss plus the `lowest` nDCG@10 queries (ties by query ID)."""
    scored = sorted((r for r in rows if r["ndcg@10"] is not None),
                    key=lambda r: (r["ndcg@10"], r["query_id"]))
    low = {r["query_id"] for r in scored[:lowest]}
    cases = {}
    for r in sorted(rows, key=lambda r: r["query_id"]):
        reasons = (["source_outside_top10"] if not r["source_recall@10"] else []) + (
            ["lowest_ndcg"] if r["query_id"] in low else [])
        if reasons:
            cases[r["query_id"]] = reasons
    return cases


# --- Segments -----------------------------------------------------------------


def interval(values: list[float]) -> dict | None:
    if not values:
        return None
    if len(values) < MIN_CI_N:
        return {"mean": statistics.fmean(values), "ci95": None}
    mean, low, high = metrics.bootstrap_ci(values)
    return {"mean": mean, "ci95": [low, high]}


def segment_rows(rows: list[dict], case_ids: set[str]) -> list[dict]:
    def cell(group: str, segment: str, members: list[dict]) -> dict:
        ndcg = [r["ndcg@10"] for r in members if r["ndcg@10"] is not None]
        return {"group": group, "segment": segment, "n": len(members), "ndcg_n": len(ndcg),
                "ndcg@10": interval(ndcg),
                "source_mrr@10": interval([r["source_mrr@10"] for r in members]),
                "source_recall@10": interval([r["source_recall@10"] for r in members]),
                "source_misses": sum(not r["source_recall@10"] for r in members),
                "failure_cases": sum(r["query_id"] in case_ids for r in members)}

    out = [cell("all", "all", rows)]
    for fields in SEGMENTS:
        for value in sorted({tuple(r[f] for f in fields) for r in rows}):
            members = [r for r in rows if tuple(r[f] for f in fields) == value]
            out.append(cell(" x ".join(fields), " / ".join(value), members))
    return out


# --- Case evidence for annotation ---------------------------------------------


def labeler(qid: str, pid: str, labels: dict, terra: dict, astra: dict) -> str:
    if pid not in labels[qid]:
        return "unjudged"
    if (qid, pid) in terra:
        return "terra"
    return "astra" if (qid, pid) in astra else "mini"


def paper_entry(qid: str, pid: str, ctx: dict, abstract: bool = True) -> dict:
    paper, labels = ctx["papers"][pid], ctx["labels"]
    source = labeler(qid, pid, labels, ctx["terra"], ctx["astra"])
    reason = None
    if source == "terra":
        reason = ctx["terra"][(qid, pid)]["reason"]
    elif source == "mini":
        row = ctx["cache"].get(judge.pair_key("openai-mini", ctx["queries"][qid]["query"], paper))
        reason = row["reason"] if row else None
    return {"arxiv_id": pid, "title": paper["title"],
            **({"abstract": paper["abstract"]} if abstract else {}),
            "grade": labels[qid].get(pid), "label_provenance": LABELERS[source],
            "label_reason": reason,
            "is_source": pid == ctx["queries"][qid]["source_arxiv_id"],
            "ranks": {name: rank_of(run[qid], pid) for name, run in ctx["runs"].items()}}


def case_evidence(row: dict, reasons: list[str], ctx: dict) -> dict:
    qid, d50 = row["query_id"], ctx["runs"]["d50"][row["query_id"]]
    grades = ctx["labels"][qid]
    outside = sorted((p for p, g in grades.items() if g > 0 and p not in d50[:REFINE]),
                     key=lambda p: (-grades[p], rank_of(d50, p) or 10**6, p))
    return {
        **{k: row[k] for k in ("query_id", "query", "query_type", "category", "specificity",
                               "overlap", "ndcg@10", "source_mrr@10", "source_ranks",
                               "source_stage", "graded_loss", "graded_loss_stage")},
        "selected_because": reasons, "failure_stage": failure_stage(row),
        "judged_grades": {str(g): sum(v == g for v in grades.values()) for g in (0, 1, 2)},
        "source_paper": paper_entry(qid, row["source_arxiv_id"], ctx),
        "d50_top20": [{"rank": i, **paper_entry(qid, p, ctx, abstract=i <= K)}
                      for i, p in enumerate(d50[:REFINE], 1)],
        "relevant_outside_d50_top20": [paper_entry(qid, p, ctx, abstract=grades[p] == 2)
                                       for p in outside],
    }


# --- Annotations and taxonomy -------------------------------------------------


def validate_annotations(data: dict, case_ids: set[str]) -> dict[str, dict]:
    """Refuse incomplete, stale or malformed annotations; return them by query ID."""
    causes = (data.get("codebook") or {}).get("causes") or []
    ids = [c.get("id") for c in causes]
    if not ids or len(set(ids)) != len(ids) or any(
            not c.get("definition") or not c.get("decision_rule") for c in causes):
        raise ValueError("Codebook needs unique cause IDs with definitions and decision rules")
    provenance = data.get("provenance") or {}
    if missing := [k for k in REQUIRED_PROVENANCE if not provenance.get(k)]:
        raise ValueError(f"Annotation provenance is missing {missing}")
    by_id = {}
    for item in data.get("annotations") or []:
        qid, primary = item.get("query_id"), item.get("primary_cause")
        secondary = item.get("secondary_causes", [])
        if qid in by_id:
            raise ValueError(f"Duplicate annotation: {qid}")
        if primary not in ids:
            raise ValueError(f"{qid}: unknown primary cause {primary!r}")
        if (not isinstance(secondary, list) or len(set(secondary)) != len(secondary)
                or any(s not in ids or s == primary for s in secondary)):
            raise ValueError(f"{qid}: secondary causes must be distinct codebook IDs")
        if not str(item.get("rationale", "")).strip():
            raise ValueError(f"{qid}: rationale required")
        by_id[qid] = item
    if extra := sorted(set(by_id) - case_ids):
        raise ValueError(f"Annotations reference queries that are not current failure cases: {extra}")
    if missing := sorted(case_ids - set(by_id)):
        raise ValueError(f"Unannotated failure cases: {missing}")
    for fix in data.get("candidate_fixes") or []:
        if fix.get("cause") not in ids or not fix.get("proposal"):
            raise ValueError("Each candidate fix needs a codebook cause and a proposal")
    return by_id


def taxonomy(cases: dict, rows: dict, annotations: dict, cause_ids: list[str]) -> dict:
    def count(qids: list[str]) -> dict:
        found = Counter(annotations[q]["primary_cause"] for q in qids)
        return {c: found[c] for c in cause_ids if found[c]}

    qids = sorted(cases)
    secondary = Counter(s for q in qids for s in annotations[q]["secondary_causes"])
    return {
        "cases": len(qids),
        "primary": count(qids),
        "secondary": {c: secondary[c] for c in cause_ids if secondary[c]},
        "by_failure_stage": {s: count([q for q in qids if failure_stage(rows[q]) == s])
                             for s in STAGES},
        "by_query_type": {t: count([q for q in qids if rows[q]["query_type"] == t])
                          for t in sorted({rows[q]["query_type"] for q in qids})},
        "by_selection": {r: count([q for q in qids if r in cases[q]])
                         for r in ("source_outside_top10", "lowest_ndcg")},
    }


# --- Offline fix test: Decision 50 without the rank-one pin --------------------


def refine_scores(reply: dict) -> dict[str, int]:
    if (set(reply) != {f"P{i}" for i in range(1, REFINE + 1)}
            or any(type(v) is not int or not 0 <= v <= 10 for v in reply.values())):
        raise ValueError("Expected one integer score 0-10 for each presented paper")
    return reply


def refine_inputs(qids: list[str]) -> tuple[dict, dict, dict]:
    """Presented order and the two saved GPT-5.4 replies per dev query; no provider calls."""
    presented, replies, hashes = {}, {}, {}
    for directory in REFINE_SOURCES:
        plan_raw = (directory / "preregistration.json").read_bytes()
        hashes[f"{directory.name}/preregistration.json"] = sha256(plan_raw)
        for request in json.loads(plan_raw)["requests"]:
            qid = request["query_id"]
            if qid in presented:
                raise ValueError(f"{qid}: refinement replies saved twice")
            passes = []
            for n in (1, 2):
                path = directory / "responses" / f"{qid}-pass{n}.json"
                raw = path.read_bytes()
                hashes[f"{directory.name}/responses/{path.name}"] = sha256(raw)
                saved = json.loads(raw)
                if (saved["request_sha256"] != request["payload_sha256"]
                        or saved["outcome"]["status"] != "ok"):
                    raise ValueError(f"{qid}: saved reply does not match its frozen request")
                passes.append(refine_scores({k: v for k, v in saved["outcome"].items()
                                             if k != "status"}))
            presented[qid], replies[qid] = request["presented_ids"], passes
    if set(presented) != set(qids):
        raise ValueError("Saved refinement replies must cover exactly the dev queries")
    return presented, replies, hashes


def refine_order(base: list[str], presented: list[str], replies: list[dict],
                 pin: bool = True) -> list[str]:
    """Decision 50's rule: averaged scores, base order breaks ties, tail unchanged."""
    if len(presented) != REFINE or len(set(presented)) != REFINE or set(presented) != set(base[:REFINE]):
        raise ValueError(f"Expected the base top {REFINE} as the presented papers")
    score = {p: statistics.fmean(r[f"P{i}"] for r in replies) for i, p in enumerate(presented, 1)}
    position = {p: i for i, p in enumerate(base[:REFINE])}
    order = sorted(base[:REFINE], key=lambda p: (-score[p], position[p]))
    if pin:
        order = [base[0]] + [p for p in order if p != base[0]]
    return order + base[REFINE:]


def fix_plan(fingerprints: dict) -> dict:
    return {
        "version": "failure-taxonomy-unpinned-v1",
        "status": "Frozen before any unpinned ranking or metric was computed.",
        "motivation": "rerank_demotion is a secondary cause in four failure cases; in two the "
                      "rank-one pin kept a grade-0 Decision 46 rank-1 paper first. Chosen after "
                      "reading the failure cases (post hoc). An unpinned GPT-5.4 mini refinement "
                      "raised source MRR on new80 in Finding 36, but the GPT-5.4 replies behind "
                      "Decision 50 were never evaluated without the pin.",
        "candidate": "Decision 50 without the rank-one pin: the same saved GPT-5.4 two-pass "
                     "replies, averaged scores, Decision 46 order as tie-break, ranks 21+ unchanged.",
        "baseline": "Saved Decision 50 ranking, which must be reproduced exactly from the same "
                    "replies with the pin.",
        "scope": "100 dev queries; held-out test not read or scored; completed top-20 label "
                 "layer unchanged.",
        "metrics": ["nDCG@10 paired difference with query-bootstrap 95% CI",
                    "source MRR@10 and source R@10 paired differences with 95% CI",
                    "judged@10 coverage", "wins/losses/ties", "query-type mean differences",
                    "rank-1 papers graded 0"],
        "supportive_if": f"nDCG@10 delta > {MIN_GAIN} with 95% CI lower bound > 0, source MRR@10 "
                         f"delta >= -{MAX_SOURCE_MRR_LOSS}, judged@10 100%",
        "interpretation": "Exploratory dev evidence on queries already used to design and select "
                          "Decision 50. A supportive result would still need confirmation on "
                          "queries not used here; it is not a promotion. If any top-10 paper is "
                          "unjudged the result is PROVISIONAL.",
        "fingerprints": fingerprints,
        "provider_calls": False, "new_labels": False, "automatic_promotion": False,
        "test_evaluation": False,
    }


def _ranking_metrics(ranked: list[str], grades: dict, source: str) -> dict:
    return {"ndcg@10": metrics.ndcg_at_k(ranked, grades),
            "source_mrr@10": metrics.reciprocal_rank(ranked, {source: 2}),
            "source_recall@10": float(source in ranked[:K]),
            "judged@10": metrics.judged_at_k(ranked, grades),
            "rank1_grade": grades.get(ranked[0])}


def fix_test(runs: dict, labels: dict, queries: dict, presented: dict, replies: dict,
             case_ids: set[str]) -> dict:
    rows = []
    for qid in sorted(labels):
        base, d50 = runs["d46"][qid], runs["d50"][qid]
        if refine_order(base, presented[qid], replies[qid], pin=True) != d50:
            raise ValueError(f"{qid}: saved replies do not reproduce the Decision 50 ranking")
        unpinned = refine_order(base, presented[qid], replies[qid], pin=False)
        src = queries[qid]["source_arxiv_id"]
        rows.append({"query_id": qid, "query_type": queries[qid]["query_type"],
                     "rank1_changed": unpinned[0] != d50[0],
                     "d50": _ranking_metrics(d50, labels[qid], src),
                     "unpinned": _ranking_metrics(unpinned, labels[qid], src)})
    return {**summarize_fix(rows, case_ids), "rows": rows}


def summarize_fix(rows: list[dict], case_ids: set[str]) -> dict:
    def paired(key: str, members: list[dict]) -> dict:
        delta, low, high = metrics.paired_diff_ci([r["d50"][key] for r in members],
                                                  [r["unpinned"][key] for r in members])
        return {"d50": statistics.fmean(r["d50"][key] for r in members),
                "unpinned": statistics.fmean(r["unpinned"][key] for r in members),
                "delta": delta, "ci95": [low, high]}

    diffs = [r["unpinned"]["ndcg@10"] - r["d50"]["ndcg@10"] for r in rows]
    result = {key: paired(key, rows) for key in ("ndcg@10", "source_mrr@10", "source_recall@10")}
    judged = statistics.fmean(r["unpinned"]["judged@10"] for r in rows)
    failures = [r for r in rows if r["query_id"] in case_ids]
    nd, mrr = result["ndcg@10"], result["source_mrr@10"]
    return {
        **result,
        "queries": len(rows),
        "judged@10": judged, "provisional": judged < 1,
        "wins_losses_ties": [sum(d > 1e-12 for d in diffs), sum(d < -1e-12 for d in diffs),
                             sum(abs(d) <= 1e-12 for d in diffs)],
        "rank1_changed": sum(r["rank1_changed"] for r in rows),
        "rank1_grade0": {name: sum(r[name]["rank1_grade"] == 0 for r in rows)
                         for name in ("d50", "unpinned")},
        "by_query_type": {t: {"n": len(m),
                              "ndcg_delta": statistics.fmean(r["unpinned"]["ndcg@10"]
                                                             - r["d50"]["ndcg@10"] for r in m),
                              "source_mrr_delta": statistics.fmean(
                                  r["unpinned"]["source_mrr@10"] - r["d50"]["source_mrr@10"]
                                  for r in m)}
                          for t in sorted({r["query_type"] for r in rows})
                          if (m := [r for r in rows if r["query_type"] == t])},
        "failure_cases": {"n": len(failures),
                          "ndcg_delta": statistics.fmean(r["unpinned"]["ndcg@10"]
                                                         - r["d50"]["ndcg@10"] for r in failures)
                          if failures else None},
        "supportive": (nd["delta"] > MIN_GAIN and nd["ci95"][0] > 0
                       and mrr["delta"] >= -MAX_SOURCE_MRR_LOSS and judged == 1),
    }


# --- Report -------------------------------------------------------------------


def _fmt(cell: dict | None, percent: bool = False) -> str:
    if cell is None:
        return "undefined"
    f = (lambda v: f"{v:.0%}") if percent else (lambda v: f"{v:.3f}")
    if cell["ci95"] is None:
        return f"{f(cell['mean'])} (n<{MIN_CI_N}, no CI)"
    return f"{f(cell['mean'])} [{f(cell['ci95'][0])}, {f(cell['ci95'][1])}]"


def _text(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _rank(value: int | None, depth: int = 100) -> str:
    return f">{depth}" if value is None else str(value)


def _pct(n: int, total: int) -> str:
    return f"{n} ({n / total:.0%})" if total else "0"


def markdown(report: dict, cases_evidence: dict, annotations: dict, data: dict) -> str:
    rows = {r["query_id"]: r for r in report["rows"]}
    rep, lab, tax = report["reproduction"], report["labels"], report["taxonomy"]
    causes = {c["id"]: c for c in data["codebook"]["causes"]}
    sizes = [s["n"] for s in report["segments"] if s["group"] != "all"]
    cross = [s["n"] for s in report["segments"] if s["group"] == "query_type x category"]
    lines = [
        "# Decision 50 failure taxonomy (dev)", "",
        f"**Scope:** the saved Decision 50 ranking on the **{len(rows)} dev queries**, scored on "
        f"the completed top-20 label layer ({lab['pairs']:,} pairs: {lab['by_labeler']}). "
        "Grades are LLM judgments, not human-validated. Cause labels are **AI-assisted "
        "annotation** by a single annotator (no inter-annotator agreement). Held-out queries "
        "were not read or scored; no API calls or new labels. The only new ranking is the "
        "offline unpinned fix test, rebuilt from saved replies.", "",
        f"Reproduction check: nDCG@10 **{rep['ndcg@10']:.4f}**, source MRR@10 "
        f"**{rep['source_mrr@10']:.4f}**, source R@10 **{rep['source_recall@10']:.0%}** "
        "match the published [dev100 summary](../top20-confirm/dev100-summary.json).", "",
        f"Segment cells range from {min(sizes)} to {max(sizes)} queries (query type x category "
        f"{min(cross)}-{max(cross)}), so most are small. Intervals are "
        f"query-bootstrap 95% CIs ({config.BOOTSTRAP_SAMPLES} resamples, seed "
        f"{config.RANDOM_SEED}), shown only for n>={MIN_CI_N}; exploratory, no "
        "multiple-testing correction. Source R@10 is the share of queries whose source paper "
        "is in the top 10.", ""]
    for fields in SEGMENTS:
        group = " x ".join(fields)
        lines += [f"## By {group.replace('_', ' ')}", "",
                  "| Segment | n | nDCG@10 [95% CI] | Source MRR@10 [95% CI] | Source R@10 [95% CI] "
                  "| Source misses | Failure cases |", "|---|---:|---:|---:|---:|---:|---:|"]
        for s in (x for x in report["segments"] if x["group"] in (group, "all")):
            name = "**all**" if s["group"] == "all" else s["segment"]
            lines.append(f"| {name} | {s['n']} | {_fmt(s['ndcg@10'])} | {_fmt(s['source_mrr@10'])} "
                         f"| {_fmt(s['source_recall@10'], True)} | {s['source_misses']} "
                         f"| {s['failure_cases']} |")
        lines.append("")
    loss = report["d50_loss"]
    lines += ["## Where D50's graded loss sits", "",
              "Same telescoping decomposition as the D47 analysis, applied to D50 on the same "
              "labels: perfectly reorder the top 10, then select from the top 20, then the top "
              f"{POOL}, then the pooled-label ideal. Unjudged papers count as zero; oracles are "
              "label-informed diagnostics, not achievable systems.", "",
              "| Component | Controlled by | Mean loss [95% CI] | Queries affected |",
              "|---|---|---:|---:|"]
    for name, value in loss["loss"].items():
        lines.append(f"| {name} | {LOSS_STAGE[name]} | {value['mean']:.4f} "
                     f"[{value['ci95'][0]:.4f}, {value['ci95'][1]:.4f}] | "
                     f"{value['queries_affected']} |")
    lines += ["", "## Stage attribution: source paper outside the D50 top 10", "",
              "Ranks are the source paper's position in each saved ranking; `>100` means "
              "outside the saved top 100. D46 re-scores the D36 top 50; D50 re-scores the D46 "
              "top 20 and keeps D46 rank 1. D47 is the previous baseline (comparison only).", "",
              "| Query | Type | Category | Lexical | Semantic | D36 | D46 | D47 | D50 | Lost at | "
              "Source grade |", "|---|---|---|---:|---:|---:|---:|---:|---:|---|---|"]
    for qid in (q for q in sorted(cases_evidence) if rows[q]["source_stage"]):
        r, ranks = rows[qid], rows[qid]["source_ranks"]
        lines.append(f"| {qid} | {r['query_type']} | {r['category']} | " + " | ".join(
            _rank(ranks[n]) for n in ("lexical", "semantic", "d36", "d46", "d47", "d50")) +
            f" | {r['source_stage']} | "
            f"{'unjudged' if r['source_grade'] is None else r['source_grade']} |")
    counts = Counter(r["source_stage"] for r in rows.values() if r["source_stage"])
    lines += ["", "Lost at: " + ", ".join(f"{s} {counts[s]}" for s in STAGES) + ". "
              + " ".join(f"`{s}`: {d}." for s, d in STAGES.items()), "",
              f"## Lowest nDCG@10 ({LOWEST} queries, any source rank)", "",
              "| Query | Type | Category | nDCG@10 | Source D50 rank | Loss: D50 refine | "
              "D46 rerank | Stage 1 | Largest |", "|---|---|---|---:|---:|---:|---:|---:|---|"]
    for qid in sorted((q for q in cases_evidence if "lowest_ndcg" in cases_evidence[q]["selected_because"]),
                      key=lambda q: (rows[q]["ndcg@10"], q)):
        r, g = rows[qid], rows[qid]["graded_loss"]
        lines.append(f"| {qid} | {r['query_type']} | {r['category']} | {r['ndcg@10']:.3f} | "
                     f"{_rank(r['source_ranks']['d50'])} | {g['d50_refine']:.3f} | "
                     f"{g['d46_rerank']:.3f} | {g['stage1_retrieval']:.3f} | "
                     f"{r['graded_loss_stage']} |")
    total = tax["cases"]
    lines += ["", "## Taxonomy", "",
              f"{total} failure cases ({sum('source_outside_top10' in v for v in report['cases'].values())} "
              f"source misses, {LOWEST} lowest nDCG@10, overlapping). One primary cause per case; "
              "secondary causes are additional explanations. Annotation provenance: "
              f"{data['provenance']['Annotator model/name']}, "
              f"{data['provenance']['Annotation date']}. "
              f"{data['provenance']['Collection method']} Inter-annotator agreement: "
              f"{data['provenance']['Inter-annotator agreement']} Codebook "
              f"{data['codebook']['version']} (decision rules and pre-annotation changes in "
              "[annotations.json](annotations.json)).", "",
              "| Cause | Primary | Secondary mentions | Definition |", "|---|---:|---:|---|"]
    for cid, cause in causes.items():
        primary = tax["primary"].get(cid, 0)
        lines.append(f"| {cid} | {_pct(primary, total)} | {tax['secondary'].get(cid, 0)} | "
                     f"{_text(cause['definition'])} |")
    for title, key, labels in (("failure stage", "by_failure_stage", list(STAGES)),
                               ("query type", "by_query_type", list(tax["by_query_type"])),
                               ("selection reason", "by_selection", list(tax["by_selection"]))):
        used = [c for c in causes if any(tax[key][x].get(c) for x in labels)]
        lines += ["", f"### Primary cause by {title}", "",
                  f"| {title.capitalize()} | Cases | " + " | ".join(used) + " |",
                  "|---|---:|" + "---:|" * len(used)]
        for x in labels:
            n = sum(tax[key][x].values())
            lines.append(f"| {x} | {n} | " + " | ".join(
                _pct(tax[key][x].get(c, 0), n) for c in used) + " |")
    lines += ["", "Failure stage = where the source left the top 10 for source misses, otherwise "
              "the stage holding most of the query's graded loss.", "", "## Examples", ""]
    for cid in sorted(tax["primary"], key=lambda c: (-tax["primary"][c], c)):
        lines += [f"### {cid}", ""]
        chosen = sorted((q for q in annotations if annotations[q]["primary_cause"] == cid),
                        key=lambda q: (rows[q]["ndcg@10"], q))[:2]
        for qid in chosen:
            case = cases_evidence[qid]
            lines.append(f"- **{qid}** ({case['query_type']}, {case['category']}; nDCG@10 "
                         f"{case['ndcg@10']:.3f}; source D50 rank "
                         f"{_rank(case['source_ranks']['d50'])}): \"{_text(case['query'])}\" "
                         f"Source: *{_text(case['source_paper']['title'])}*. "
                         f"{_text(annotations[qid]['rationale'])}")
        lines.append("")
    fix = report["fix_test"]
    status = "PROVISIONAL (unjudged top-10 papers)" if fix["provisional"] else "fully judged"
    lines += ["## Offline fix test: drop the rank-one pin", "",
              "Plan frozen in [fix-plan.json](fix-plan.json) before any unpinned metric was "
              "computed. Same saved GPT-5.4 two-pass replies as Decision 50, averaged scores, "
              "Decision 46 order as tie-break, ranks 21+ unchanged; only the rule that keeps "
              "Decision 46's rank 1 first is removed. The pinned rule reproduces the saved D50 "
              f"ranking for all {fix['queries']} dev queries. Chosen after reading the failure "
              "cases, on queries already used to design Decision 50: exploratory, not a promotion.",
              "", "| Metric | D50 (pinned) | Unpinned | Paired delta [95% CI] |",
              "|---|---:|---:|---:|"]
    for key, name in (("ndcg@10", "nDCG@10"), ("source_mrr@10", "Source MRR@10"),
                      ("source_recall@10", "Source R@10")):
        v = fix[key]
        lines.append(f"| {name} | {v['d50']:.4f} | {v['unpinned']:.4f} | {v['delta']:+.4f} "
                     f"[{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}] |")
    w, l, t = fix["wins_losses_ties"]
    lines += ["", f"Unpinned judged@10: **{fix['judged@10']:.0%}** ({status}). nDCG@10 "
              f"wins/losses/ties: {w}/{l}/{t}. Rank 1 changes in {fix['rank1_changed']} queries; "
              f"rank-1 papers graded 0: {fix['rank1_grade0']['d50']} pinned vs "
              f"{fix['rank1_grade0']['unpinned']} unpinned. Mean nDCG@10 delta on the "
              f"{fix['failure_cases']['n']} failure cases: {fix['failure_cases']['ndcg_delta']:+.4f}.",
              "", "| Query type | n | nDCG@10 delta | Source MRR@10 delta |", "|---|---:|---:|---:|"]
    lines += [f"| {t} | {v['n']} | {v['ndcg_delta']:+.4f} | {v['source_mrr_delta']:+.4f} |"
              for t, v in fix["by_query_type"].items()]
    type_sizes = sorted({v["n"] for v in fix["by_query_type"].values()})
    lines += ["", f"Frozen rule (nDCG@10 delta > {MIN_GAIN} with CI lower bound > 0, source "
              f"MRR@10 delta >= -{MAX_SOURCE_MRR_LOSS}, judged@10 100%) met: "
              f"**{'yes' if fix['supportive'] else 'no'}**. Query-type cells have "
              f"{'-'.join(map(str, type_sizes))} queries each; no multiple-testing correction.", ""]
    fixes = data.get("candidate_fixes") or []
    if fixes:
        lines += ["## Candidate fixes (general rules, not query-specific)", "",
                  "| Cause | Proposal | Status | Evidence |", "|---|---|---|---|"]
        lines += [f"| {f['cause']} | {_text(f['proposal'])} | {_text(f.get('status', 'proposed'))} "
                  f"| {_text(f.get('evidence', ''))} |" for f in fixes]
        lines.append("")
    match = report["annotation_evidence_matches"]
    lines += ["## Limits", "",
              "- 100 repeatedly analyzed dev queries; segment cells are small and exploratory.",
              "- Labels are pooled LLM judgments (no human validation). Unjudged papers count "
              "as zero, so a never-judged source paper does not lower nDCG.",
              "- Source MRR/R@10 treat the generating paper as the single right answer; "
              "graded nDCG can be high when the source is missing.",
              "- Cause labels are one AI assistant's reading of titles and abstracts, with no "
              "agreement study; they are leads, not established causes.",
              "- Stage 1 component ranks only cover the saved top 100.",
              f"- Annotated evidence matches the current cases.json: **{match}**.", "",
              "Per-query rows, segment values and input hashes: [report.json](report.json); "
              "case evidence: [cases.json](cases.json); codebook and annotations: "
              "[annotations.json](annotations.json)."]
    return "\n".join(lines) + "\n"


# --- Main ---------------------------------------------------------------------


def _write(path: Path, value: object) -> bytes:
    raw = (json.dumps(value, indent=2) + "\n").encode("utf-8")
    path.write_bytes(raw)
    return raw


def build(out: Path = OUT) -> dict:
    """Load and check every input; return the computed evidence (no writes)."""
    paths = {"split": config.EVAL_DIR / "split.json", "queries": config.EVAL_DIR / "queries.jsonl",
             "labels": LABELS, "parent_labels": PARENT_LABELS, "label_correction": LABEL_CORRECTION,
             "published": PUBLISHED, **RUNS, **COMPONENT_RUNS}
    raw = {name: path.read_bytes() for name, path in paths.items()}
    qids, queries = dev_queries(raw["split"], raw["queries"])
    layer = json.loads(raw["labels"])
    terra = check_labels(layer, json.loads(raw["parent_labels"]), raw["parent_labels"], qids)
    labels = layer["labels"]
    astra = read_human_grades()
    if any(labels[q].get(p) != g for (q, p), g in astra.items()):
        raise ValueError("Reference overrides differ from the label layer")
    runs = {name: json.loads(raw[name]) for name in RUNS}
    check_lineage(runs, qids)
    presented, replies, reply_hashes = refine_inputs(qids)
    components = {name: json.loads(raw[name]) for name in COMPONENT_RUNS}
    rows, parts = query_rows(runs, components, labels, queries)
    reproduction = check_published(rows, json.loads(raw["published"]))
    cases = select_cases(rows)
    papers = {p["arxiv_id"]: p for p in judge.load_jsonl(config.PROCESSED_DIR / "corpus.jsonl")}
    ctx = {"papers": papers, "labels": labels, "terra": terra, "astra": astra, "runs": runs,
           "queries": queries, "cache": judge.load_judgments("openai-mini")}
    by_id = {r["query_id"]: r for r in rows}
    evidence = {q: case_evidence(by_id[q], reasons, ctx) for q, reasons in cases.items()}
    sources = Counter(labeler(q, p, labels, terra, astra) for q in qids for p in labels[q])
    correction = json.loads(raw["label_correction"])
    replies_sha = sha256(json.dumps(reply_hashes, sort_keys=True).encode("utf-8"))
    return {
        "rows": rows, "decompositions": parts, "cases": cases, "evidence": evidence,
        "reproduction": reproduction, "runs": runs, "labels_by_query": labels, "queries": queries,
        "refine": (presented, replies),
        "fix_fingerprints": {"d46": sha256(raw["d46"]), "d50": sha256(raw["d50"]),
                             "labels": sha256(raw["labels"]), "refine_files": len(reply_hashes),
                             "refine_files_sha256": replies_sha},
        "labels": {"layer": LABELS.relative_to(config.PROJECT_ROOT).as_posix(),
                   "pairs": sum(sources.values()),
                   "by_labeler": ", ".join(f"{sources[k]:,} {LABELERS[k]}"
                                           for k in ("mini", "astra", "terra")),
                   "terra_attribution": correction["evaluator"],
                   "rubric_version": judge.RUBRIC_VERSION},
        "provenance": {**{name: {"path": paths[name].relative_to(config.PROJECT_ROOT).as_posix(),
                                 "sha256": sha256(value)} for name, value in raw.items()},
                       "refine_replies": {"paths": [d.relative_to(config.PROJECT_ROOT).as_posix()
                                                    for d in REFINE_SOURCES],
                                          "files": len(reply_hashes), "sha256": replies_sha}},
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cases-only", action="store_true",
                        help="write cases.json for annotation; skip the annotated report")
    parser.add_argument("--freeze-fix-plan", action="store_true",
                        help="freeze the offline fix-test plan before any unpinned metric")
    args = parser.parse_args(argv)
    built = build()
    evidence_raw = (json.dumps({"cases": built["evidence"]}, indent=2) + "\n").encode("utf-8")
    if args.cases_only:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "cases.json").write_bytes(evidence_raw)
        print(f"{len(built['cases'])} cases -> {OUT / 'cases.json'}")
        return
    plan = fix_plan(built["fix_fingerprints"])
    if args.freeze_fix_plan:
        OUT.mkdir(parents=True, exist_ok=True)
        freeze(FIX_PLAN, plan)
        print(f"fix plan frozen -> {FIX_PLAN}")
        return
    if not FIX_PLAN.exists():
        raise SystemExit("Freeze the fix-test plan first: --freeze-fix-plan")
    freeze(FIX_PLAN, plan)  # refuses if the plan or its input fingerprints changed
    data = json.loads(ANNOTATIONS.read_text(encoding="utf-8"))
    annotations = validate_annotations(data, set(built["cases"]))
    cause_ids = [c["id"] for c in data["codebook"]["causes"]]
    rows = {r["query_id"]: r for r in built["rows"]}
    presented, replies = built["refine"]
    report = {
        "scope": "Decision 50 saved ranking, 100 dev queries, completed top-20 label layer; "
                 "no provider calls, label changes or held-out scoring",
        "labels": built["labels"], "reproduction": built["reproduction"],
        "segments": segment_rows(built["rows"], set(built["cases"])),
        "d50_loss": aggregate(built["decompositions"]),
        "cases": built["cases"],
        "taxonomy": taxonomy(built["cases"], rows, annotations, cause_ids),
        "fix_test": {"plan_sha256": sha256(FIX_PLAN.read_bytes()),
                     **fix_test(built["runs"], built["labels_by_query"], built["queries"],
                                presented, replies, set(built["cases"]))},
        "annotation_evidence_matches": data["provenance"].get("Annotated cases.json sha256")
                                       == sha256(evidence_raw),
        "provenance": {**built["provenance"],
                       "annotations": {"path": ANNOTATIONS.relative_to(config.PROJECT_ROOT).as_posix(),
                                       "sha256": sha256(ANNOTATIONS.read_bytes())}},
        "rows": built["rows"],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cases.json").write_bytes(evidence_raw)
    _write(OUT / "report.json", report)
    text = markdown(report, built["evidence"], annotations, data)
    (OUT / "report.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
