"""Step 4 (test): score a search system's rankings against known right answers.

Two inputs, both plain dictionaries keyed by query ID:

    run    = {"q1": ["2501.00001", "2501.00042", ...]}    # what the system returned, best first
    labels = {"q1": {"2501.00042": 2, "2501.00007": 1}}   # paper -> grade (0, 1 or 2)

A grade of 1 or more counts as "relevant" for Recall and MRR. For queries with a
single known answer, labels look like {"q1": {"2501.00042": 2}}.

Three per-query metrics (each returns one number for one query):

    recall_at_k      share of relevant papers found in the top k
    reciprocal_rank  1 / rank of the first relevant paper (0 if below the cutoff)
    ndcg_at_k        graded score: good papers near the top earn the most

Then:

    score_run        every metric for every query -> one row per query
    bootstrap_ci     average of one metric with a 95% confidence interval
    paired_diff_ci   is system B really better than system A on the same queries?
    summarize        averages + intervals, overall or per group (category / query type)

All settings (k values, cutoff, number of resamples) come from config.py (Decision 21).
"""

from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

from arxiv_search import config


# --- Per-query metrics ------------------------------------------------------


def relevant_papers(grades: dict[str, int]) -> set[str]:
    """Papers graded 1 or 2. Grade 0 means "judged and not relevant"."""
    return {paper for paper, grade in grades.items() if grade >= 1}


def recall_at_k(ranked: list[str], grades: dict[str, int], k: int) -> float:
    """Share of the relevant papers that appear in the top k.

    Example: relevant = {B, D}; ranked = [A, B, C, D]
        k=2 -> found {B}    -> 1/2 = 0.5
        k=4 -> found {B, D} -> 2/2 = 1.0
    With one relevant paper this is simply 1 (found) or 0 (missed).
    """
    relevant = relevant_papers(grades)
    if not relevant:
        raise ValueError("Recall is undefined for a query with no relevant papers.")
    found = relevant & set(ranked[:k])
    return len(found) / len(relevant)


def reciprocal_rank(ranked: list[str], grades: dict[str, int], cutoff: int = config.MRR_CUTOFF) -> float:
    """1 / (rank of the first relevant paper), or 0 if it is not in the top `cutoff`.

    Example: relevant = {C}; ranked = [A, B, C, ...]
        C is at rank 3 -> 1/3 = 0.333
    Ranks start at 1, so a perfect result scores 1.0.
    """
    relevant = relevant_papers(grades)
    for rank, paper in enumerate(ranked[:cutoff], start=1):
        if paper in relevant:
            return 1 / rank
    return 0.0


def dcg(gains: list[int]) -> float:
    """Discounted cumulative gain: each grade is divided by log2(rank + 1).

    Rank 1 is divided by log2(2) = 1 (full credit), rank 3 by log2(4) = 2 (half credit).
    """
    return sum(gain / math.log2(rank + 1) for rank, gain in enumerate(gains, start=1))


def ndcg_at_k(ranked: list[str], grades: dict[str, int], k: int = config.NDCG_K) -> float | None:
    """DCG of our top k divided by the DCG of the best possible top k.

    Uses linear gain (the grade itself) and counts unjudged papers as 0.

    Example: grades = {A: 0, B: 2, C: 1}; ranked = [A, B, C], k=3
        ours  = 0/1 + 2/1.585 + 1/2 = 1.762
        ideal = 2/1 + 1/1.585 + 0/2 = 2.631   (best order: B, C, A)
        nDCG  = 1.762 / 2.631 = 0.670

    Returns None if no paper has a grade above 0: there is nothing to rank well,
    so the score is undefined and the query is left out of the average.
    """
    ideal_gains = sorted(grades.values(), reverse=True)[:k]
    ideal = dcg(ideal_gains)
    if ideal == 0:
        return None
    our_gains = [grades.get(paper, 0) for paper in ranked[:k]]
    return dcg(our_gains) / ideal


def judged_at_k(ranked: list[str], grades: dict[str, int], k: int = config.NDCG_K) -> float:
    """Share of the top k that has a grade at all (0, 1 or 2).

    If this is low (say under 90%), nDCG is unreliable: many of the system's results
    were never judged and were silently counted as 0.
    """
    top = ranked[:k]
    return sum(paper in grades for paper in top) / len(top) if top else 0.0


# --- Whole run --------------------------------------------------------------


def score_run(run: dict[str, list[str]], labels: dict[str, dict[str, int]]) -> list[dict]:
    """Score every labeled query. Returns one row per query, for example:

        {"query_id": "q1", "recall@1": 0.0, "recall@5": 1.0, ..., "mrr@10": 0.5,
         "ndcg@10": 0.67, "judged@10": 0.9}

    A query the system returned nothing for is scored as an empty ranking (all zeros),
    so a system can't look better by skipping hard queries.
    """
    rows = []
    for query_id, grades in labels.items():
        ranked = run.get(query_id, [])
        row = {"query_id": query_id}
        for k in config.RECALL_KS:
            row[f"recall@{k}"] = recall_at_k(ranked, grades, k)
        row[f"mrr@{config.MRR_CUTOFF}"] = reciprocal_rank(ranked, grades)
        row[f"ndcg@{config.NDCG_K}"] = ndcg_at_k(ranked, grades)
        row[f"judged@{config.NDCG_K}"] = judged_at_k(ranked, grades)
        rows.append(row)
    return rows


# --- Uncertainty ------------------------------------------------------------


def bootstrap_ci(
    values: list[float], samples: int = config.BOOTSTRAP_SAMPLES, seed: int = config.RANDOM_SEED
) -> tuple[float, float, float]:
    """Mean with a 95% confidence interval: (mean, low, high).

    How it works: pretend our queries are a sample from all possible queries. Draw
    `samples` new query sets of the same size *with replacement* (some queries twice,
    some not at all), average each one, and take the middle 95% of those averages.
    """
    data = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    picks = rng.integers(0, len(data), size=(samples, len(data)))
    means = data[picks].mean(axis=1)
    low, high = np.percentile(means, [2.5, 97.5])
    return float(data.mean()), float(low), float(high)


def paired_diff_ci(
    values_a: list[float], values_b: list[float], samples: int = config.BOOTSTRAP_SAMPLES,
    seed: int = config.RANDOM_SEED,
) -> tuple[float, float, float]:
    """How much better B is than A, with a 95% interval: (mean diff, low, high).

    Both lists must score the same queries in the same order. Working on per-query
    differences (B - A) removes noise from query difficulty, since a hard query is
    hard for both systems. If the interval does not include 0, the difference is
    unlikely to be luck.
    """
    if len(values_a) != len(values_b):
        raise ValueError("Paired comparison needs the same queries for both systems.")
    diffs = np.asarray(values_b, dtype=float) - np.asarray(values_a, dtype=float)
    return bootstrap_ci(diffs.tolist(), samples, seed)


def summarize(rows: list[dict], group_by: dict[str, str] | None = None) -> dict[str, dict]:
    """Average every metric with a 95% interval, overall and (optionally) per group.

    group_by maps query_id -> group name, e.g. {"q1": "cs.IR", "q2": "cs.CL"}.
    Returns {"all": {"recall@1": (mean, low, high), ..., "n": 400}, "cs.IR": {...}, ...}.
    Queries with an undefined score (nDCG None) are left out of that metric only.
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups["all"].append(row)
        if group_by:
            groups[group_by[row["query_id"]]].append(row)

    metric_names = [name for name in rows[0] if name != "query_id"] if rows else []
    summary = {}
    for group, group_rows in groups.items():
        summary[group] = {"n": len(group_rows)}
        for name in metric_names:
            values = [row[name] for row in group_rows if row[name] is not None]
            summary[group][name] = bootstrap_ci(values) if values else None
    return summary
