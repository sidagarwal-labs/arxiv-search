"""Immutable, checksummed corpus and model configuration for one deployment."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import gzip
from importlib.metadata import version
import json
from pathlib import Path

import numpy as np


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class EmbeddingSpec:
    provider: str
    model: str
    dimensions: int
    text_recipe: str


@dataclass(frozen=True)
class Release:
    manifest: dict
    fingerprint: str
    papers: tuple[dict, ...]
    vectors: np.ndarray
    embedding: EmbeddingSpec
    directory: Path | None = None

    @classmethod
    def load(cls, directory: Path) -> Release:
        manifest_bytes = (directory / "manifest.json").read_bytes()
        manifest = json.loads(manifest_bytes)
        if manifest["schema_version"] != 1:
            raise ValueError("Unsupported serving release schema")
        for package, expected_version in manifest.get("runtime_dependencies", {}).items():
            if version(package) != expected_version:
                raise ValueError(f"Runtime dependency differs from the exported release: {package}")
        retrieval, reranking = manifest["retrieval"], manifest["reranking"]
        if (retrieval["adapter"] != "shortlist-v1"
                or not 0 < retrieval["bm25_k1"] <= 10
                or not 0 <= retrieval["bm25_b"] <= 1
                or type(retrieval["score_depth"]) is not int or retrieval["score_depth"] < 100
                or not 0 <= retrieval["score_semantic_weight"] <= 1
                or type(retrieval["shortlist_size"]) is not int
                or not 1 <= retrieval["shortlist_size"] <= 100
                or type(reranking["depth"]) is not int or not 1 <= reranking["depth"] <= 100
                or type(reranking["passes"]) is not int or not 1 <= reranking["passes"] <= 4
                or type(reranking["rrf_c"]) is not int or reranking["rrf_c"] < 0):
            raise ValueError("Invalid pinned retrieval or reranking settings")
        refinement = manifest.get("refinement")
        if refinement is not None and (
            not isinstance(refinement, dict)
            or type(refinement.get("depth")) is not int
            or not 1 <= refinement["depth"] <= reranking["depth"]
            or type(refinement.get("passes")) is not int
            or not 1 <= refinement["passes"] <= 4
            or "rrf_c" not in refinement
            or (refinement["rrf_c"] is not None
                and (type(refinement["rrf_c"]) is not int or refinement["rrf_c"] < 0))
            or type(refinement.get("pin_first")) is not bool
        ):
            raise ValueError("Invalid pinned refinement settings")
        for relative, expected in manifest.get("runtime_sha256", {}).items():
            path = directory.parent / "arxiv_search" / relative
            if not path.resolve().is_relative_to((directory.parent / "arxiv_search").resolve()):
                raise ValueError("Runtime path escapes release")
            if sha256_file(path) != expected:
                raise ValueError(f"Runtime code differs from the exported release: {relative}")
        shards = manifest.get("vector_shards", ["vectors.npy"])
        if (not isinstance(shards, list) or not shards or len(set(shards)) != len(shards)
                or any(not isinstance(name, str) or Path(name).name != name
                       or not name.endswith(".npy") for name in shards)):
            raise ValueError("Invalid vector shard list")
        corpus_file = manifest.get("corpus_file", "corpus.jsonl")
        if corpus_file not in ("corpus.jsonl", "corpus.jsonl.gz"):
            raise ValueError("Unsupported corpus artifact format")
        for name in (corpus_file, "bm25.npz", "terms.json", *shards):
            if sha256_file(directory / name) != manifest["sha256"][name]:
                raise ValueError(f"Serving artifact checksum mismatch: {name}")
        corpus_bytes = (directory / corpus_file).read_bytes()
        if corpus_file.endswith(".gz"):
            corpus_bytes = gzip.decompress(corpus_bytes)
        papers = tuple(json.loads(line) for line in corpus_bytes.splitlines() if line)
        ids = [paper["arxiv_id"] for paper in papers]
        spec = EmbeddingSpec(**manifest["embedding"])
        if not ids or len(set(ids)) != len(ids) or len(ids) != manifest["papers"]:
            raise ValueError("Serving corpus has missing or duplicate paper IDs")
        if spec.dimensions <= 0 or spec.text_recipe != "title-abstract-v1":
            raise ValueError("Unsupported embedding dimensions or text recipe")
        storage = manifest.get("vector_storage", "float32")
        if storage not in ("float16", "float32"):
            raise ValueError("Unsupported serving vector storage")
        if len(shards) == 1:
            vectors = np.load(directory / shards[0], mmap_mode="r", allow_pickle=False)
        else:
            vectors = np.empty((len(papers), spec.dimensions), dtype=np.dtype(storage))
            offset = 0
            for name in shards:
                block = np.load(directory / name, mmap_mode="r", allow_pickle=False)
                if (block.dtype != np.dtype(storage) or block.ndim != 2
                        or block.shape[1] != spec.dimensions or not len(block)
                        or offset + len(block) > len(papers)):
                    raise ValueError("Vector shard does not match corpus or embedding dimensions")
                vectors[offset:offset + len(block)] = block
                offset += len(block)
            if offset != len(papers):
                raise ValueError("Vector shard rows do not match corpus")
            vectors.flags.writeable = False
        if vectors.dtype != np.dtype(storage) or vectors.shape != (len(papers), spec.dimensions):
            raise ValueError("Serving vectors do not match corpus or embedding dimensions")
        for start in range(0, len(papers), 256):
            chunk = vectors[start:start + 256].astype(np.float32, copy=False)
            norms = np.linalg.norm(chunk, axis=1)
            tolerance = 5e-4 if storage == "float16" else 1e-5
            if not np.isfinite(chunk).all() or not np.allclose(norms, 1, atol=tolerance, rtol=0):
                raise ValueError("Serving vectors must be finite and normalized")
        return cls(manifest, hashlib.sha256(manifest_bytes).hexdigest(),
                   papers, vectors, spec, directory)

    def cache_key(self, operation: str, payload: dict) -> str:
        value = json.dumps(
            [self.fingerprint, operation, payload], sort_keys=True,
            separators=(",", ":"), ensure_ascii=False, allow_nan=False,
        )
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def metadata(self) -> dict:
        return {
            key: self.manifest[key] for key in
            ("papers", "categories", "from_month", "to_month", "fields",
             "corpus_note", "baseline")
        } | {
            "release": self.manifest["release_id"], "fingerprint": self.fingerprint,
            "summary": self.manifest["summary"],
        }
