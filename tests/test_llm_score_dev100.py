from arxiv_search import openai_rerank as client
from arxiv_search.evaluate import llm_score_dev100 as dev, llm_score_pilot as score


def test_pilot_requests_reuse_v2_cache_and_new_requests_use_own_folder():
    pilot = {"request_key": "a" * 64, "pilot": True}
    new = {"request_key": "b" * 64, "pilot": False}
    assert dev.cache_path(pilot) == score.OUT / "responses" / f"{'a' * 64}.json"
    assert dev.cache_path(new) == dev.OUT / "responses" / f"{'b' * 64}.json"


def test_judge_accounting_counts_each_call_once():
    usage = {"request_id": "r1", "input_tokens": 1000, "output_tokens": 100,
             "reasoning_tokens": 0, "accounted_tokens": 1100}
    rows = [{"usage": usage}, {"usage": usage},
            {"usage": {**usage, "request_id": "r2"}}]
    out = dev.judge_accounting(rows)
    assert out["calls"] == 2 and out["input_tokens"] == 2000
    assert out["usd"] == (2000 * client.INPUT_PRICE + 200 * client.OUTPUT_PRICE) / 1e9


def test_plan_reuses_frozen_safeguard_criteria_and_never_promotes():
    plan = dev.plan(["q1", "q2"], ["q1"])
    assert plan["success_criteria"] == dev.guard.PLAN["success_criteria"]
    assert plan["version"] == client.DEV100_VERSION
    assert plan["automatic_promotion"] is False and plan["held_out_queries_used"] is False
