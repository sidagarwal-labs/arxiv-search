"""Combine exact-match and meaning-search rankings without mixing their score scales."""

import math

from arxiv_search import config


def fuse_working_baseline(
    lexical: dict[str, float], semantic: dict[str, float], *, k: int = config.RUN_DEPTH,
) -> list[str]:
    """Apply Decision36 to descending raw top500 BM25/cosine score mappings.

    Rank-only inputs cannot reproduce score ordering and are explicitly rejected.
    """
    from arxiv_search.search.rank_score import rescore_shortlist

    if not isinstance(lexical, dict) or not isinstance(semantic, dict):
        raise TypeError("Working baseline requires descending raw score mappings, not rankings")
    return rescore_shortlist(lexical, semantic, score_fraction=1,
                             depth=config.WORKING_BASELINE_SCORE_DEPTH, k=k,
                             score_semantic_weight=config.WORKING_BASELINE_SCORE_SEMANTIC_WEIGHT,
                             shortlist_size=config.WORKING_BASELINE_SHORTLIST_SIZE)


def fuse_rrf_baseline(
    lexical: list[str], semantic: list[str], *, k: int = config.RUN_DEPTH,
) -> list[str]:
    """Reproduce the immutable Decision35 shortlist/control, not current ordering."""
    return fuse(
        lexical, semantic, method="rrf", semantic_weight=0.55, c=30, depth=100, k=k,
    )


def fuse(
    lexical: list[str], semantic: list[str], *, method: str = "rrf",
    semantic_weight: float = 0.5, c: int = 60, depth: int = 100, k: int = 100,
) -> list[str]:
    """Weighted RRF or linear rank scores; absent papers earn zero from that list.

    RRF gives rank r score 1/(c+r). Linear gives (depth-r+1)/depth.
    Ties keep first appearance: lexical order, then semantic-only papers.
    """
    if method not in ("rrf", "linear"):
        raise ValueError("method must be rrf or linear")
    if not math.isfinite(semantic_weight) or not 0 <= semantic_weight <= 1:
        raise ValueError("semantic_weight must be between 0 and 1")
    if c < 0 or depth <= 0 or k < 0:
        raise ValueError("c and k must be nonnegative; depth must be positive")
    scores: dict[str, float] = {}
    for ranking, weight in ((lexical, 1 - semantic_weight), (semantic, semantic_weight)):
        if len(set(ranking)) != len(ranking):
            raise ValueError("rankings must not contain duplicate paper IDs")
        if weight == 0:
            continue
        for rank, paper_id in enumerate(ranking[:depth], 1):
            value = 1 / (c + rank) if method == "rrf" else (depth - rank + 1) / depth
            scores[paper_id] = scores.get(paper_id, 0.0) + weight * value
    return sorted(scores, key=lambda paper_id: -scores[paper_id])[:k]
