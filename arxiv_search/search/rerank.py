"""Reorder an explicit candidate pool; never retrieve or inspect relevance labels."""

from __future__ import annotations

import math


def rerank_prefix(ranking: list[str], scores: dict[str, float], depth: int) -> list[str]:
    if not ranking or len(ranking) != len(set(ranking)):
        raise ValueError("Expected a nonempty unique ranking")
    if type(depth) is not int or not 1 <= depth <= len(ranking):
        raise ValueError("Reranking depth must be within the ranking")
    selected = ranking[:depth]
    if any(p not in scores or not math.isfinite(scores[p]) for p in selected):
        raise ValueError("Missing or nonfinite candidate scores")
    return sorted(selected, key=lambda p: -scores[p]) + ranking[depth:]


def score_rank_blend(ranking: list[str], scores: dict[str, float], depth: int,
                     beta: float, c: int) -> list[str]:
    """Order the top `depth` by LLM score + beta * (c+1)/(c+retrieval rank).

    The retrieval prior is worth `beta` points at rank 1 and decays smoothly, so a
    large LLM score gap still wins while near-ties fall back to retrieval evidence.
    Ties keep retrieval order; ranks below `depth` are unchanged.
    """
    if not math.isfinite(beta) or beta < 0 or type(c) is not int or c < 0:
        raise ValueError("beta must be finite and >= 0; c a nonnegative int")
    rank = {p: i for i, p in enumerate(ranking[:depth], 1)}
    blended = {p: scores[p] + beta * (c + 1) / (c + rank[p]) if p in scores else math.nan
               for p in rank}
    return rerank_prefix(ranking, blended, depth)


def rerank_pool(pool: list[str], scores: dict[str, float], baseline: list[str],
                *, cross_weight: float = 1.0, k: int = 100) -> list[str]:
    """Pure cross-encoder or rank blend; ties retain the declared pool order."""
    if not pool or len(pool) != len(set(pool)) or set(scores) != set(pool):
        raise ValueError("Pool and scores must contain exactly the same unique IDs")
    if any(not math.isfinite(v) for v in scores.values()):
        raise ValueError("Cross-encoder scores must be finite")
    if (not baseline or len(baseline) != len(set(baseline))
            or not set(baseline) <= set(pool)):
        raise ValueError("Unique baseline ranking must be contained in pool")
    if (not math.isfinite(cross_weight) or not 0 <= cross_weight <= 1
            or type(k) is not int or not 1 <= k <= len(pool)):
        raise ValueError("Invalid weight or output depth")
    cross = sorted(pool, key=lambda p: -scores[p])
    if cross_weight == 1:
        return cross[:k]
    base_rank = {p: i for i, p in enumerate(baseline, 1)}
    cross_rank = {p: i for i, p in enumerate(cross, 1)}
    combined = {
        p: cross_weight / (30 + cross_rank[p])
        + ((1 - cross_weight) / (30 + base_rank[p]) if p in base_rank else 0)
        for p in pool
    }
    return sorted(pool, key=lambda p: -combined[p])[:k]
