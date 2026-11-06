import json

from arxiv_search import openai_rerank
from arxiv_search.evaluate import top20_model_pilot as pilot


def test_stronger_model_payload_changes_only_model():
    ids = [str(i) for i in range(20)]
    papers = {p: {"title": p, "authors": ["A"], "abstract": "Evidence"} for p in ids}
    old = json.loads(openai_rerank.encode_refine_payload("Q", ids, papers))
    new = json.loads(pilot.payload("Q", ids, papers))
    assert new["model"] == "gpt-5.4-2026-03-05"
    assert new["model"] != old["model"]
    new["model"] = old["model"]
    assert new == old


def test_ranking_preserves_pin_pool_and_tail():
    ids = [str(i) for i in range(100)]
    presented = list(reversed(ids[:20]))
    replies = [{f"P{i}": 10 if i == 1 else 0 for i in range(1, 21)}] * 2
    result = pilot.build_ranking(ids, presented, replies)
    assert result[0] == ids[0]
    assert set(result[:20]) == set(ids[:20])
    assert result[20:] == ids[20:]
