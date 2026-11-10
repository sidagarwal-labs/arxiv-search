"""Persist BM25's numeric postings; reuse its scorer without runtime tokenization of the corpus."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from arxiv_search.search.bm25 import BM25
from arxiv_search.search.text import paper_text, tokenize


def write_index(papers: tuple[dict, ...] | list[dict], settings: dict, directory: Path) -> None:
    index = BM25(
        [tokenize(paper_text(p, authors=True, title_repeats=2), add_stems=True) for p in papers],
        [p["arxiv_id"] for p in papers], k1=settings["bm25_k1"], b=settings["bm25_b"],
    )
    terms = list(index.postings)
    offsets = np.concatenate(([0], np.cumsum([len(index.postings[t][0]) for t in terms])))
    np.savez_compressed(
        directory / "bm25.npz", doc_len=index.doc_len,
        offsets=offsets, idf=np.array([index.idf[t] for t in terms]),
        papers=np.concatenate([index.postings[t][0] for t in terms]).astype(np.int32),
        counts=np.concatenate([index.postings[t][1] for t in terms]),
    )
    (directory / "terms.json").write_text(json.dumps(terms), encoding="utf-8")


class PackedBM25(BM25):
    def __init__(self, directory: Path, ids: list[str], settings: dict):
        self.ids = ids
        self.k1 = settings["bm25_k1"]
        self.b = settings["bm25_b"]
        terms = json.loads((directory / "terms.json").read_text(encoding="utf-8"))
        with np.load(directory / "bm25.npz", allow_pickle=False) as packed:
            self.doc_len = packed["doc_len"]
            offsets = packed["offsets"]
            idf, papers, counts = packed["idf"], packed["papers"], packed["counts"]
        if (len(terms) != len(set(terms)) or self.doc_len.shape != (len(ids),)
                or offsets.shape != (len(terms) + 1,) or idf.shape != (len(terms),)
                or offsets[0] != 0 or offsets[-1] != len(papers)
                or len(papers) != len(counts) or np.any(np.diff(offsets) <= 0)
                or np.any(papers < 0) or np.any(papers >= len(ids))
                or not np.isfinite(counts).all() or np.any(counts <= 0)
                or not np.isfinite(idf).all() or not np.isfinite(self.doc_len).all()
                or np.any(self.doc_len <= 0)):
            raise ValueError("Invalid packed BM25 postings")
        self.avg_len = self.doc_len.mean()
        self.postings = {
            term: (papers[offsets[i]:offsets[i + 1]], counts[offsets[i]:offsets[i + 1]])
            for i, term in enumerate(terms)
        }
        self.idf = dict(zip(terms, idf))
