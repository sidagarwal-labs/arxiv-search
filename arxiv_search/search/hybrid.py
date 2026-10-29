"""Combine exact-match and meaning-search rankings without mixing their score scales."""

import math

from arxiv_search import config


def fuse_working_baseline(
    lexical: list[str], semantic: list[str], *, k: int = config.RUN_DEPTH,
) -> list[str]:
    """Fuse best-BM25/OpenAI-large rankings using the approved working profile."""
    return fuse(
        lexical, semantic, method=config.WORKING_BASELINE_METHOD,
        semantic_weight=config.WORKING_BASELINE_SEMANTIC_WEIGHT,
        c=config.WORKING_BASELINE_RRF_C, depth=config.WORKING_BASELINE_DEPTH, k=k,
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
