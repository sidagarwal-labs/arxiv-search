"""Combine per-query retrieval scores after putting each list on a common scale."""

from __future__ import annotations

import math


def fuse_scores(
    lexical: dict[str, float], semantic: dict[str, float], *,
    normalization: str, semantic_weight: float, depth: int, k: int = 100,
) -> list[str]:
    """Rank the union by independently normalized, weighted retrieval scores."""
    if k < 0:
        raise ValueError("k must be nonnegative")
    scores = normalized_fusion_scores(
        lexical, semantic, normalization=normalization,
        semantic_weight=semantic_weight, depth=depth)
    return sorted(scores, key=lambda p: -scores[p])[:k]


def normalized_fusion_scores(
    lexical: dict[str, float], semantic: dict[str, float], *,
    normalization: str, semantic_weight: float, depth: int,
) -> dict[str, float]:
    """Normalize each top-depth list independently; an absent paper contributes zero.

    max: score / maximum. minmax: (score - minimum) / (maximum - minimum).
    Inputs must be descending, finite, nonnegative scores. A constant positive
    list receives equal unit scores (no within-list preference); all-zero lists
    receive zero. Ties keep lexical order then semantic-only order.
    """
    if normalization not in ("max", "minmax"):
        raise ValueError("normalization must be max or minmax")
    if not math.isfinite(semantic_weight) or not 0 <= semantic_weight <= 1:
        raise ValueError("semantic_weight must be between zero and one")
    if depth <= 0:
        raise ValueError("depth must be positive")
    combined: dict[str, float] = {}
    for scores, weight in ((lexical, 1 - semantic_weight), (semantic, semantic_weight)):
        values = list(scores.values())
        if any(not math.isfinite(s) or s < 0 for s in values):
            raise ValueError("scores must be finite and nonnegative")
        if any(a < b for a, b in zip(values, values[1:])):
            raise ValueError("scores must be descending")
        if weight == 0:
            continue
        top = list(scores.items())[:depth]
        if not top:
            continue
        high, low = top[0][1], top[-1][1]
        for pid, value in top:
            if high == 0:
                scaled = 0.0
            elif normalization == "max" or high == low:
                scaled = value / high
            else:
                scaled = (value - low) / (high - low)
            combined[pid] = combined.get(pid, 0.0) + weight * scaled
    return combined


def fuse_top1_bonus(
    lexical: list[str], semantic: list[str], *, bonus: float, k: int = 100,
) -> list[str]:
    """Fixed 55%/c30 RRF plus a bounded bonus to each retriever's first result.

    bonus is a fraction of that retriever's weighted rank-one RRF contribution.
    No intent labels or known target IDs are used.
    """
    if not math.isfinite(bonus) or bonus < 0:
        raise ValueError("bonus must be finite and nonnegative")
    if k < 0:
        raise ValueError("k must be nonnegative")
    combined: dict[str, float] = {}
    for ids, weight in ((lexical[:100], 1 - 0.55), (semantic[:100], 0.55)):
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate IDs")
        for rank, pid in enumerate(ids, 1):
            combined[pid] = combined.get(pid, 0.0) + weight * (1 / (30 + rank))
            if rank == 1:
                combined[pid] += bonus * weight / 31
    return sorted(combined, key=lambda p: -combined[p])[:k]
