import json

import httpx

from arxiv_search import answer, config, openai_answer as client
from arxiv_search.evaluate import answer_eval_v2 as l2

PAPER = {"title": "T", "authors": ["A"], "submitted_month": "2026-01", "abstract": "Abstract text."}


def test_v1_payload_unchanged_and_v2_uses_its_own_prompt_and_budget():
    v1 = json.loads(answer.encode_payload("m", "q", [PAPER]))
    assert v1["instructions"] == answer.SYSTEM and v1["max_output_tokens"] == answer.MAX_OUTPUT_TOKENS
    assert answer.encode_payload("m", "q", [PAPER]) == answer.encode_payload("m", "q", [PAPER],
                                                                             version=answer.VERSION)
    v2 = json.loads(answer.encode_payload("m", "q", [PAPER], version=answer.VERSION_V2))
    assert v2["instructions"] == answer.SYSTEM_V2 and v2["max_output_tokens"] == 1200
    assert "a citation never carries over" in answer.SYSTEM_V2


def _body(output):
    return {"status": "completed", "model": client.MODELS["luna"], "output": output,
            "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15,
                      "output_tokens_details": {"reasoning_tokens": 0}}}


def _message(text, phase=None):
    item = {"type": "message", "content": [{"type": "output_text", "text": text}]}
    return {**item, "phase": phase} if phase else item


def test_call_once_reads_only_the_final_answer_phase(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OPENAI_TOKEN_LIMITS", {"mini": 10_000_000, "large": 10_000_000})
    monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key")
    final = json.dumps({"grounded": True, "answer": "It does X [1]."})
    draft = final + " (draft note)"
    monkeypatch.setattr(client.httpx, "post", lambda *a, **k: httpx.Response(
        200, json=_body([_message(draft, "commentary"), _message(final, "final_answer")])))
    ledger = client.TaskLedger("t", cap_nanodollars=10**9, max_requests=5, path=tmp_path / "l.db")
    encoded = answer.encode_payload(client.MODELS["luna"], "q", [PAPER], version=answer.VERSION_V2)
    result, _ = client.call_once(encoded, ledger, validate=lambda v: answer.validate(v, 1))
    assert result["cited"] == [1] and result["answer"] == "It does X [1]."


def test_contract_b_lets_an_ungrounded_answer_cite_the_closest_papers():
    closest = {"grounded": False, "answer": "None of these answer it; the closest is [2]."}
    try:
        answer.validate(closest, 3)
        raise AssertionError("contract A must reject an ungrounded answer with citations")
    except ValueError:
        pass
    assert answer.validate(closest, 3, ungrounded_may_cite=True)["cited"] == [2]
    for bad in ({"grounded": True, "answer": "No label here."}, {"grounded": False, "answer": "x [9]."}):
        try:
            answer.validate(bad, 3, ungrounded_may_cite=True)
            raise AssertionError("grounded answers still need labels; labels must be supplied")
        except ValueError:
            pass


def test_recheck_rescores_only_saved_contract_a_failures(tmp_path, monkeypatch):
    monkeypatch.setattr(l2, "OUT", tmp_path)
    item = {"item_id": "i1", "paper_ids": ["p1", "p2"]}
    path = l2.response_path("luna", item)
    path.parent.mkdir(parents=True)
    text = json.dumps({"grounded": False, "answer": "None answer it; the closest is [1]."})
    path.with_suffix(".failure.json").write_text(json.dumps(
        {"output": [_message("draft", "commentary"), _message(text, "final_answer")]}), encoding="utf-8")
    failed = {"outcome": {"status": "invalid_answer"}, "request_sha256": "k"}
    fixed = l2.recheck_reply(failed, item, "luna")
    assert fixed["outcome"] == {"status": "ok", "grounded": False, "cited": [1], "contract": "B",
                                "answer": "None answer it; the closest is [1]."}
    assert l2.recheck_reply({"outcome": {"status": "incomplete"}}, item, "luna")["outcome"]["status"] == "incomplete"
    assert l2.recheck_reply(None, item, "luna") is None


def _rows(faith, n=20):
    rows = [{"item_id": f"a{i}", "kind": "answerable", "faithfulness": faith,
             "citation_precision": 1.0} for i in range(n)]
    return rows + [{"item_id": f"b{i}", "kind": "abstain"} for i in range(5)]


def test_checks_compare_against_the_fixed_yardstick():
    table = {"abstain_accuracy_v2": 0.9, "false_abstain_v2": 0.05, "format_valid": 0.97}
    assert l2.checks(_rows(0.80), table, _rows(0.82))["qualifies"]
    worse = l2.checks(_rows(0.70), table, _rows(0.82))
    assert not worse["qualifies"] and not worse["faithfulness"]
    assert not l2.checks(_rows(0.82), {**table, "format_valid": 0.9}, _rows(0.82))["qualifies"]


def test_decide_needs_cheaper_qualifying_challenger_and_stable_grader():
    ok = {"abstain_accuracy_v2": 0.9, "false_abstain_v2": 0.05, "format_valid": 0.97}
    summary = {"rows": {"luna": _rows(0.82), "mini": _rows(0.82)},
               "table": {"luna": {**ok, "usd_per_answer": 0.0004}, "mini": {**ok, "usd_per_answer": 0.003}},
               "v1_rows": {"gpt-5.4": _rows(0.83)}, "v1_table": {"mini": {"usd_per_answer": 0.003}}}
    assert l2.decide(summary, {"within_limit": True})["replace_incumbent"]
    assert not l2.decide(summary, {"within_limit": False})["replace_incumbent"]
