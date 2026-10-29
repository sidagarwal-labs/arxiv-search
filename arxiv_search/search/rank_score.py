"""Interpolate magnitude and rank evidence without query-specific routing."""

from __future__ import annotations

import math

from arxiv_search.search.hybrid import fuse
from arxiv_search.search.score_fusion import normalized_fusion_scores


def components(lexical: dict[str, float], semantic: dict[str, float], *,
               score_fraction: float, depth: int, k: int = 100,
               score_semantic_weight: float = 0.75) -> dict[str, dict[str, float]]:
    """Combine max-score75% with RRF55%/c30/depth100 on a common [0,1] scale.

    The theoretical RRF maximum is 1/31 (rank1 in both inputs). Dividing by
    that constant does not make rank values into calibrated probabilities.
    Rank depth stays100 so deeper score-only overlap receives no rank boost.
    """
    if not math.isfinite(score_fraction) or not 0 <= score_fraction <= 1:
        raise ValueError("score_fraction must be finite and between zero and one")
    if k < 0:
        raise ValueError("k must be nonnegative")
    magnitude = normalized_fusion_scores(
        lexical, semantic, normalization="max", semantic_weight=score_semantic_weight, depth=depth)
    rank_values: dict[str, float] = {}
    for scores, weight in ((lexical, 1 - 0.55), (semantic, 0.55)):
        for rank, pid in enumerate(list(scores)[:100], 1):
            rank_values[pid] = rank_values.get(pid, 0.0) + weight * (1 / (30 + rank))
    ids = list(rank_values) if score_fraction == 0 else list(magnitude)
    if score_fraction not in (0, 1):
        ids = list(dict.fromkeys([*rank_values, *magnitude]))
    return {
        pid: {"max_score": magnitude.get(pid, 0.0),
              "normalized_rrf": rank_values.get(pid, 0.0) * 31,
              "combined": score_fraction * magnitude.get(pid, 0.0)
              + (1 - score_fraction) * (rank_values.get(pid, 0.0) * 31)}
        for pid in ids
    }


def fuse_rank_score(lexical: dict[str, float], semantic: dict[str, float], *,
                    score_fraction: float, depth: int, k: int = 100) -> list[str]:
    values = components(lexical, semantic, score_fraction=score_fraction, depth=depth, k=k)
    if score_fraction == 0:
        return fuse(list(lexical), list(semantic), semantic_weight=0.55, c=30, depth=100, k=k)
    return sorted(values, key=lambda pid: -values[pid]["combined"])[:k]


def rescore_shortlist(lexical: dict[str, float], semantic: dict[str, float], *,
                      score_fraction: float, depth: int, k: int = 100,
                      score_semantic_weight: float = 0.75,
                      shortlist_size: int = 10) -> list[str]:
    """Reorder only the fixed RRF baseline top10; preserve its entire tail.

    Membership at cutoffs10 and above is invariant. Smaller-cutoff recall,
    MRR, known-item ranks and graded ordering can still improve or regress.
    """
    if shortlist_size <= 0:
        raise ValueError("shortlist_size must be positive")
    values = components(lexical, semantic, score_fraction=score_fraction, depth=depth, k=k,
                        score_semantic_weight=score_semantic_weight)
    baseline = fuse(list(lexical), list(semantic), semantic_weight=0.55, c=30, depth=100,
                    k=max(k, shortlist_size))
    if score_fraction == 0:
        return baseline[:k]
    top = sorted(baseline[:shortlist_size], key=lambda pid: -values[pid]["combined"])
    return (top + baseline[shortlist_size:])[:k]
