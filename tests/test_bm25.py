import math
import random

import pytest

from arxiv_search.search.bm25 import BM25
from arxiv_search.search.text import paper_text, tokenize


def test_paper_text_options():
    paper = {"title": "Dense Retrieval", "abstract": "We study it.", "authors": ["Ada Lovelace", "Alan Turing"]}
    assert paper_text(paper) == "Dense Retrieval We study it."
    assert paper_text(paper, authors=True) == "Dense Retrieval We study it. Ada Lovelace Alan Turing"
    assert paper_text(paper, title_repeats=2) == "Dense Retrieval Dense Retrieval We study it."


def test_tokenize_lowercases_and_splits_on_non_letters():
    assert tokenize("State-of-the-art RAG, SO(3).") == ["state", "of", "the", "art", "rag", "so", "3"]
    assert tokenize("BM25 vs. dense_retrieval") == ["bm25", "vs", "dense", "retrieval"]
    assert tokenize("Café") == ["café"]


def test_tokenize_can_drop_stopwords():
    text = "How is the retrieval of papers not working?"
    assert tokenize(text, drop_stopwords=True) == ["how", "retrieval", "papers", "working"]


def test_tokenize_can_stem():
    assert tokenize("Recommending recommendations, modeling models", stem=True) == [
        "recommend", "recommend", "model", "model"
    ]
    assert tokenize("The retrieval", drop_stopwords=True, stem=True) == ["retriev"]
    assert tokenize("Models of retrieval", add_stems=True) == [
        "models", "of", "retrieval", "~model", "~of", "~retriev"
    ]


def test_bm25_hand_worked_example():
    """Three tiny papers, query "graph". Every number below can be checked by hand.

    N = 3, average length = (2 + 3 + 1) / 3 = 2. "graph" is in 2 papers:
        idf = ln(1 + (3 - 2 + 0.5) / (2 + 0.5)) = ln(1.6) = 0.470
    Paper A: tf 1, length 2: brake = 1.2 × (0.25 + 0.75 × 2/2) = 1.2
             1 × 2.2 / (1 + 1.2)   = 1.000  → score 0.470
    Paper B: tf 2, length 3: brake = 1.2 × (0.25 + 0.75 × 3/2) = 1.65
             2 × 2.2 / (2 + 1.65)  = 1.205  → score 0.567
    Paper C: no "graph"                     → score 0, not returned
    """
    index = BM25([["graph", "search"], ["graph", "graph", "neural"], ["text"]], ["A", "B", "C"])
    scores = index.scores(["graph"])
    assert scores[0] == pytest.approx(math.log(1.6) * 1.0, abs=1e-4)
    assert scores[1] == pytest.approx(math.log(1.6) * 4.4 / 3.65, abs=1e-4)
    assert scores[2] == 0
    assert index.search(["graph"], k=10) == ["B", "A"]


def test_bm25_unknown_word_and_ties():
    index = BM25([["a", "x"], ["a", "y"]], ["P1", "P2"])
    assert index.search(["never-seen"], k=10) == []
    assert index.search(["a"], k=10) == ["P1", "P2"]  # tie: corpus order


def test_bm25_matches_rank_bm25_library():
    """Same scores as the rank_bm25 library, once its idf is set to the same formula."""
    rank_bm25 = pytest.importorskip("rank_bm25")
    rng = random.Random(0)
    vocab = [f"w{i}" for i in range(30)]
    docs = [[rng.choice(vocab) for _ in range(rng.randint(3, 40))] for _ in range(50)]
    ours = BM25(docs, [str(i) for i in range(50)])
    theirs = rank_bm25.BM25Okapi(docs, k1=1.2, b=0.75)
    theirs.idf = ours.idf  # rank_bm25's default idf differs slightly; the rest must match
    for _ in range(10):
        query = rng.sample(vocab, 3)
        assert ours.scores(query) == pytest.approx(theirs.get_scores(query))
