import numpy as np
import pytest

from arxiv_search.evaluate import embedding_compression as comp


def _unit(rows, dims, seed=0):
    v = np.random.default_rng(seed).normal(size=(rows, dims)).astype(np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def test_truncate_keeps_prefix_and_renormalizes():
    v = _unit(5, 8)
    t = comp.truncate(v, 4)
    assert t.shape == (5, 4) and np.allclose(np.linalg.norm(t, axis=1), 1)
    assert np.allclose(t * np.linalg.norm(v[:, :4], axis=1, keepdims=True), v[:, :4], atol=1e-6)
    with pytest.raises(ValueError):
        comp.truncate(v, 9)


@pytest.mark.parametrize("storage,bytes_per,tol", [("float32", 4, 1e-6), ("float16", 2, 1e-3),
                                                   ("int8", 1, 2e-2)])
def test_stored_forms_keep_cosine_scores_close(storage, bytes_per, tol):
    papers, queries = _unit(200, 64, 1), _unit(3, 64, 2)
    matrix, scale = comp.store(papers, storage)
    assert comp.stored_bytes(matrix, scale) == 200 * 64 * bytes_per + (200 * 4 if storage == "int8" else 0)
    assert np.abs(comp.similarities(matrix, scale, queries) - queries @ papers.T).max() < tol


def test_unknown_storage_rejected():
    with pytest.raises(ValueError):
        comp.store(_unit(2, 4), "bf16")


def test_top_scores_and_overlap():
    ids = ["a", "b", "c", "d"]
    assert list(comp.top_scores(np.array([0.1, 0.9, 0.5, 0.9]), ids, 3)) == ["b", "d", "c"]
    assert comp.overlap(["a", "b", "c"], ["c", "x", "a"], 2) == 0.0
    assert comp.overlap(["a", "b"], ["b", "a"], 2) == 1.0


def test_plan_is_api_free_dev_only_and_includes_control():
    assert comp.PLAN["api_calls"] == 0 and comp.PLAN["held_out_queries_used"] is False
    assert comp.VARIANTS[comp.CONTROL] == (3072, "float32")
