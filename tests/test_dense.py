import numpy as np

from arxiv_search import config
from arxiv_search.search.dense import DenseIndex


def normalized(rows):
    v = np.array(rows, dtype=np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def test_dense_index_ranks_by_cosine_similarity():
    # Three papers as 2-number "embeddings": A points right, B up, C diagonally.
    index = DenseIndex(normalized([[1, 0], [0, 1], [1, 1]]), ["A", "B", "C"])
    query = normalized([[1, 0.2]])[0]  # mostly "right"
    assert index.search(query, k=3) == ["A", "C", "B"]
    assert index.scores(query)[0] > 0.98  # nearly the same direction → cosine close to 1
    assert index.search(query, k=1) == ["A"]


def test_dense_index_ties_keep_corpus_order():
    index = DenseIndex(normalized([[1, 0], [1, 0]]), ["P1", "P2"])
    assert index.search(normalized([[1, 0]])[0], k=2) == ["P1", "P2"]


def test_every_embedding_model_has_its_prefixes():
    for key, settings in config.EMBEDDING_MODELS.items():
        assert {"hf_name", "query_prefix", "paper_prefix"} <= set(settings), key
    assert config.EMBEDDING_MODELS["e5-small"]["query_prefix"] == "query: "
