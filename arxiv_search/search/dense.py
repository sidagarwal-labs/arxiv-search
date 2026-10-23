"""Dense search: rank papers by how close their meaning is to the query's.

1. Embed every paper once: an embedding model turns its text into 384 numbers (a vector).
   Papers about similar things get similar vectors, even with no words in common.
2. At search time, embed the query with the same model.
3. Score = cosine similarity between the query vector and each paper vector
   (1 = same direction/meaning, 0 = unrelated). The vectors are normalized to length 1,
   so cosine similarity is just a dot product: one matrix multiplication for all papers.

Embedding 23,304 papers took ~30-118 minutes per model in these laptop runs, so the vectors
are saved to data/embeddings/<model>.npy and reused. Embedding one query takes milliseconds.
"""

from __future__ import annotations

import json
import time
from functools import cache

import numpy as np

from arxiv_search import config


@cache
def load_model(model_key: str):
    """The embedding model, downloaded from Hugging Face on first use (~130 MB)."""
    from sentence_transformers import SentenceTransformer  # slow import, so only when needed
    import torch

    # Always float32: gte-small loads as float16 by default, which this laptop's CPU runs
    # ~15x slower in a small timing check (89 s vs 6 s for 64 papers).
    return SentenceTransformer(config.EMBEDDING_MODELS[model_key]["hf_name"], device="cpu",
                               model_kwargs={"torch_dtype": torch.float32})


def embed_queries(model_key: str, queries: list[str]) -> np.ndarray:
    prefix = config.EMBEDDING_MODELS[model_key]["query_prefix"]
    return load_model(model_key).encode(
        [prefix + q for q in queries], normalize_embeddings=True, convert_to_numpy=True
    ).astype(np.float32)


def paper_vectors(model_key: str, texts: list[str], ids: list[str], name: str) -> tuple[np.ndarray, dict]:
    """Vectors for every paper, computed once then loaded from data/embeddings/<name>.npy.

    name identifies model + text recipe (e.g. "bge-small" or "bge-small+authors"), so a
    different text never silently reuses old vectors. Returns (vectors, info).
    """
    vectors_path = config.EMBEDDINGS_DIR / f"{name}.npy"
    info_path = config.EMBEDDINGS_DIR / f"{name}.json"
    if vectors_path.exists() and info_path.exists():
        info = json.loads(info_path.read_text())
        if info["ids"] == ids:
            return np.load(vectors_path), info

    model = load_model(model_key)
    prefix = config.EMBEDDING_MODELS[model_key]["paper_prefix"]
    start = time.perf_counter()
    vectors = model.encode(
        [prefix + t for t in texts], batch_size=config.EMBEDDING_BATCH_SIZE,
        normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=True,
    ).astype(np.float32)
    info = {
        "model": config.EMBEDDING_MODELS[model_key]["hf_name"], "name": name,
        "max_tokens": model.max_seq_length, "dimensions": vectors.shape[1],
        "embed_seconds": round(time.perf_counter() - start, 1), "ids": ids,
    }
    config.EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    np.save(vectors_path, vectors)
    info_path.write_text(json.dumps(info))
    return vectors, info


class DenseIndex:
    def __init__(self, vectors: np.ndarray, ids: list[str]):
        """vectors[i] is paper i's normalized vector; ids[i] is its arxiv_id."""
        self.vectors = vectors
        self.ids = ids

    def scores(self, query_vector: np.ndarray) -> np.ndarray:
        """Cosine similarity of every paper to the query."""
        return self.vectors @ query_vector

    def search(self, query_vector: np.ndarray, k: int) -> list[str]:
        """arxiv_ids of the k most similar papers, best first (ties keep corpus order)."""
        scores = self.scores(query_vector)
        order = np.argsort(-scores, kind="stable")[:k]
        return [self.ids[i] for i in order]
