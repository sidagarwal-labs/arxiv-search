import json

import numpy as np
import pytest

from arxiv_search import answer, openai_answer as client, openai_api as api
from arxiv_search.evaluate import answer_eval as ev

PAPER = {"title": " A  Title ", "authors": ["A", "B", "C", "D", "E"], "submitted_month": "2026-03",
         "abstract": "Line one.\n  Line   two.", "arxiv_id": "2603.00001", "comments": "NeurIPS",
         "url": "https://arxiv.org/abs/2603.00001"}


def test_evidence_has_only_the_approved_fields():
    card = answer.evidence([PAPER])[0]
    assert card == {"label": "[1]", "title": "A  Title",
                    "authors": "A, B, C, et al. (5 authors)", "month": "2026-03",
                    "abstract": "Line one. Line two."}
    assert answer.author_line(["A", "B"]) == "A, B" and answer.author_line([]) == "Unknown"
    with pytest.raises(ValueError):
        answer.evidence([PAPER] * 11)


def test_payload_is_strict_json_with_no_ids_or_urls():
    payload = json.loads(answer.encode_payload("gpt-6-luna", "q", [PAPER, PAPER]))
    body = payload["input"]
    assert "2603.00001" not in body and "arxiv.org" not in body and "NeurIPS" not in body
    assert payload["text"]["format"]["strict"] is True and payload["store"] is False
    assert payload["reasoning"] == {"effort": "none"} and payload["instructions"] == answer.SYSTEM
    with pytest.raises(ValueError):
        answer.encode_payload("gpt-6-luna", " ", [PAPER])


def test_validate_parses_citations_and_enforces_grounding():
    ok = answer.validate({"grounded": True, "answer": "X does Y [2]. Z [1, 2]."}, 3)
    assert ok["cited"] == [2, 1]
    assert answer.validate({"grounded": False, "answer": "None of these answer it."}, 3)["cited"] == []
    bad = [{"grounded": True, "answer": "No citations."},
           {"grounded": False, "answer": "Cites [1]."},
           {"grounded": True, "answer": "Out of range [4]."},
           {"grounded": True, "answer": "See https://arxiv.org/abs/1 [1]."},
           {"grounded": True, "answer": "Paper 2603.00001 [1]."},
           {"grounded": "yes", "answer": "x [1]"},
           {"grounded": True, "answer": "word " * 181 + "[1]"},
           {"grounded": True, "answer": "x [1]", "extra": 1}]
    for value in bad:
        with pytest.raises(ValueError):
            answer.validate(value, 3)


def test_sentences_split_deterministically():
    assert answer.sentences("First claim [1]. Second one [2]! [3] shows more.") == \
        ["First claim [1].", "Second one [2]!", "[3] shows more."]


def test_every_candidate_has_a_price_and_a_ledger_tier():
    for model in client.MODELS.values():
        assert model in client.PRICES and model in api.MODEL_TIERS
    assert api.MODEL_TIERS[client.MODELS["gpt-5.4"]] == "large"
    assert client.cost_nanodollars("gpt-6-luna", 1_000_000, 1_000_000) == 600_000_000


def test_task_ledger_enforces_dollar_cap_and_single_attempt(tmp_path, monkeypatch):
    from arxiv_search import config
    monkeypatch.setattr(config, "OPENAI_TOKEN_LIMITS", {"mini": 10_000_000, "large": 10_000_000})
    ledger = client.TaskLedger("t", cap_nanodollars=1_000_000, max_requests=5, path=tmp_path / "l.db")
    rid = ledger.reserve_request("k" * 64, "gpt-6-luna", 1000, 100)  # 150,000 nanodollars
    ledger.finish(rid, "completed", 0.1, {"input_tokens": 1000, "output_tokens": 100, "reasoning_tokens": 0})
    assert ledger.attempted("k" * 64)
    with pytest.raises(api.OpenAIError):
        ledger.reserve_request("k" * 64, "gpt-6-luna", 1000, 100)
    with pytest.raises(api.BudgetExceeded):
        ledger.reserve_request("j" * 64, "gpt-5.4-2026-03-05", 1000, 100)  # 4,000,000 > remaining
    assert ledger.summary()["by_model"]["gpt-6-luna"]["requests"] == 1


def test_abstain_pairs_skip_contexts_with_source_or_relevant_papers():
    qids = ["a", "b", "c"]
    sim = np.array([[1, .1, .5], [.1, 1, .2], [.5, .2, 1]])
    top10 = {"a": ["pa"], "b": ["pb"], "c": ["pc"]}
    labels = {"a": {"pb": 1}, "b": {}, "c": {}}
    pairs = ev.abstain_pairs(qids, sim, top10, labels, {"a": "sa", "b": "pa", "c": "sc"})
    assert pairs == {"a": "c", "b": "c", "c": "b"}


def test_interleave_by_type_round_robins():
    order = ev.interleave_by_type(["a1", "a2", "b1"], {"a1": "x", "a2": "x", "b1": "y"})
    assert sorted(order[:2], key=lambda q: q[0]) and {order[0][0], order[1][0]} == {"a", "b"}


def test_validate_grade_requires_one_verdict_per_sentence_in_order():
    good = {"sentences": [{"id": "S1", "verdict": "supported", "reason": "r"},
                          {"id": "S2", "verdict": "no_claim", "reason": "r"}], "answers_request": 2}
    assert ev.validate_grade(good, 2) == good
    for bad in ({**good, "answers_request": 3}, {**good, "answers_request": True},
                {**good, "sentences": good["sentences"][::-1]},
                {**good, "sentences": [{"id": "S1", "verdict": "maybe", "reason": "r"}] * 2}):
        with pytest.raises(ValueError):
            ev.validate_grade(bad, 2)


def _state():
    return {"labels": {"q": {"p1": 2, "p2": 0, "p3": 1}},
            "queries": {"q": {"source_arxiv_id": "p1", "query_type": "keyword"}}}


def test_item_metrics_from_labels_and_grades():
    item = {"item_id": "A-q", "kind": "answerable", "query_id": "q", "pilot": True,
            "paper_ids": ["p1", "p2", "p3"], "grade2_in_context": 1}
    reply = {"outcome": {"status": "ok", "grounded": True, "answer": "a [2]. b [3].", "cited": [2, 3]}}
    grade = {"outcome": {"status": "ok", "answers_request": 1, "sentences": [
        {"verdict": "supported"}, {"verdict": "partial"}, {"verdict": "no_claim"}]}}
    m = ev.item_metrics(_state(), item, reply, grade)
    assert m["citation_precision"] == 0.5 and m["grade2_coverage"] == 0 and m["source_cited"] is False
    assert m["faithfulness"] == 0.75 and m["fully_faithful"] is False and m["false_abstain"] is False
    invalid = ev.item_metrics(_state(), item, {"outcome": {"status": "invalid_answer"}}, None)
    assert invalid["format_valid"] is False and "citation_precision" not in invalid
    abstain = ev.item_metrics(_state(), {**item, "kind": "abstain"},
                              {"outcome": {"status": "ok", "grounded": False, "answer": "No.", "cited": []}}, None)
    assert abstain["abstained"] is True


def test_paired_bootstrap_and_decision_rule():
    def rows(f, p):
        return [{"item_id": str(i), "kind": "answerable", "faithfulness": f, "citation_precision": p,
                 "false_abstain": False} for i in range(20)]
    base = {"format_valid": 1.0, "false_abstain": 0.0, "abstain_accuracy": 0.9}
    summary = {"rows": {"nano": rows(.9, .9), "luna": rows(.98, .97), "mini": rows(1.0, 1.0),
                        "gpt-5.4": rows(1.0, 1.0)},
               "table": {"nano": {**base, "faithfulness": .9, "usd_per_answer": .0005},
                         "luna": {**base, "faithfulness": .98, "usd_per_answer": .0006},
                         "mini": {**base, "faithfulness": 1.0, "usd_per_answer": .004},
                         "gpt-5.4": {**base, "faithfulness": 1.0, "usd_per_answer": .014}}}
    d = ev.decide(summary)
    assert d["best"] == "mini" and d["checks"]["nano"]["qualifies"] is False
    # Luna is within .03 of the best on every item: non-inferior, and cheaper than mini.
    assert d["checks"]["luna"]["qualifies"] is True and d["pick"] == "luna"
    summary["table"]["luna"]["abstain_accuracy"] = 0.5
    assert ev.decide(summary)["pick"] == "mini"


def test_plan_freezes_eligibility_and_grader():
    assert ev.SERVING_ELIGIBLE == ("luna", "mini") and ev.GRADER == "gpt-5.4"
    assert ev.PLAN["held_out_queries_used"] is False and "none" in ev.PLAN["retries"]
