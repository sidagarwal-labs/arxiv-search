import json

import pytest

from arxiv_search import openai_rerank as client
from arxiv_search.evaluate import llm_score_facets as facets

PAPERS = {f"p{i}": {"title": f"Title {i}", "authors": ["A. Author"], "abstract": f"Abstract {i}."}
          for i in range(50)}


def test_facet_versions_have_their_own_caps_and_output_limits():
    caps = client.separate_caps()
    assert caps[client.FACET_VERSION] == (100_000_000, 100)
    assert caps[client.FACET_SCORE_VERSION] == (5_200_000_000, 200)
    assert client.FACET_VERSION in client.VERSIONS and client.FACET_SCORE_VERSION in client.VERSIONS


def test_facet_extraction_payload_sees_only_the_query():
    payload = json.loads(client.encode_facet_payload("regional language social media"))
    assert json.loads(payload["input"]) == {"query": "regional language social media"}
    assert payload["text"]["format"]["name"] == "query_facets"
    assert payload["max_output_tokens"] == client.FACET_MAX_OUTPUT
    assert payload["reasoning"] == {"effort": "none"}
    with pytest.raises(ValueError):
        client.encode_facet_payload("  ")


@pytest.mark.parametrize("bad", [
    {"facets": []}, {"facets": ["a", "b", "c", "d", "e"]}, {"facets": ["  ", ""]},
    {"facets": [1]}, {"facets": ["a"], "extra": 1}, ["a"]])
def test_validate_facets_rejects_malformed_lists(bad):
    with pytest.raises(ValueError):
        client.validate_facets(bad)


def test_validate_facets_canonicalizes_schema_valid_quirks_instead_of_burning_a_request():
    assert client.validate_facets({"facets": [" speech  corpus", "Speech corpus", "", "social media"]}) \
        == ["speech corpus", "social media"]
    schema = json.loads(client.encode_facet_payload("q"))["text"]["format"]["schema"]
    assert schema["properties"]["facets"]["minItems"] == 1
    assert schema["properties"]["facets"]["maxItems"] == client.MAX_FACETS


def test_facet_score_payload_keeps_plain_paper_order_and_adds_checklist():
    ids = [f"p{i}" for i in range(50)]
    plain = json.loads(client.encode_score_payload("q", ids, PAPERS))
    payload = json.loads(client.encode_facet_score_payload("q", ["speech", "social media"], ids, PAPERS))
    body = json.loads(payload["input"])
    assert body["papers"] == json.loads(plain["input"])["papers"]
    assert body["required_facets"] == [{"id": "F1", "facet": "speech"}, {"id": "F2", "facet": "social media"}]
    assert payload["model"] == plain["model"] and payload["reasoning"] == plain["reasoning"]
    assert payload["instructions"] == client.FACET_SCORE_SYSTEM
    entry = payload["text"]["format"]["schema"]["properties"]["P1"]
    assert entry["properties"]["missing"]["items"]["enum"] == ["F1", "F2"]
    assert client.facet_count(json.dumps(payload).encode()) == 2


def test_validate_facet_scores_checks_ids_and_scores():
    good = {f"P{i}": {"missing": [], "score": 3} for i in range(1, 11)}
    assert client.validate_facet_scores(good, 10, 2) == good
    assert client.validate_facet_scores({**good, "P1": {"missing": ["F2", "F1", "F2"], "score": 4}},
                                        10, 2)["P1"] == {"missing": ["F1", "F2"], "score": 4}
    for change in ({"missing": ["F3"], "score": 3},
                   {"missing": [], "score": 5}, {"missing": [], "score": 2.0}, {"score": 1}):
        with pytest.raises(ValueError):
            client.validate_facet_scores({**good, "P1": change}, 10, 2)
    with pytest.raises(ValueError):
        client.validate_facet_scores({k: v for k, v in good.items() if k != "P10"}, 10, 2)


def test_ledgers_reserve_each_versions_own_output_cap(tmp_path):
    assert client.PilotLedger(tmp_path / "a.db", version=client.FACET_VERSION).output_cap == client.FACET_MAX_OUTPUT
    assert client.PilotLedger(tmp_path / "b.db", version=client.FACET_SCORE_VERSION).output_cap \
        == client.FACET_SCORE_MAX_OUTPUT


def test_cap_applies_only_to_papers_missing_a_facet():
    assert facets.adjusted({"missing": ["F1"], "score": 4}, 2) == 2.0
    assert facets.adjusted({"missing": ["F1"], "score": 1}, 2) == 1.0
    assert facets.adjusted({"missing": [], "score": 4}, 2) == 4.0
    assert facets.adjusted({"missing": ["F1"], "score": 4}, None) == 4.0


def _results(delta, mrr_delta):
    def scope(d):
        systems = {facets.REFERENCE: {"all": {"source_mrr@10": {"mean": 0.8}}, "top10_fully_judged": True}}
        summary = {}
        for n in facets.SYSTEMS:
            systems[n] = {"all": {"source_mrr@10": {"mean": 0.8 + mrr_delta}}, "top10_fully_judged": True}
            summary[n] = {"all": {"ndcg@10": {"paired_vs_working": {"difference": d, "ci95": [d - 0.01, d + 0.01]}}}}
        return {"systems": systems, "summary": summary}
    return {"pilot20": scope(delta), "new80": scope(delta), "all100": scope(delta)}


def test_pilot_gate_and_full_rules():
    assert all(v["passes"] for v in facets.verdicts(_results(0.01, 0.0), ("pilot20",), None).values())
    assert not any(v["passes"] for v in facets.verdicts(_results(0.01, -0.03), ("pilot20",), None).values())
    assert not any(v["passes"] for v in facets.verdicts(_results(-0.001, 0.0), ("pilot20",), None).values())
    scopes = ("all100", "pilot20", "new80")
    assert all(v["passes"] for v in facets.verdicts(_results(0.02, 0.0), scopes, 0.0106).values())
    # A gain inside the noise band, or a CI touching zero, does not qualify.
    assert not any(v["passes"] for v in facets.verdicts(_results(0.009, 0.0), scopes, 0.0106).values())


def test_plan_names_one_change_against_the_reranking_baseline():
    assert facets.REFERENCE == "llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30"
    assert facets.PRIMARY == "llm-mini-facet-score+d=50+cap=2+avg2+rrf-baseline+c=30"
    assert facets.PLAN["held_out_queries_used"] is False and facets.PLAN["automatic_retries"] is False


def test_cached_response_must_match_its_request_and_metadata(tmp_path):
    from arxiv_search.evaluate import fusion_experiment as fusion
    answer = {"facets": ["speech"]}
    value = {"attempt_key": "k", "model": client.MODEL, "request_sha256": client.request_key(b"req"),
             "query_id": "q1", "answer": answer, "answer_sha256": fusion.fingerprint(answer),
             "usage": {"status": "completed"}}
    path = tmp_path / "k.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    assert facets._read(path, "k", b"req", {"query_id": "q1"}, client.validate_facets) == ["speech"]
    for key, encoded, meta in (("k", b"other", {"query_id": "q1"}), ("k", b"req", {"query_id": "q2"}),
                               ("x", b"req", {"query_id": "q1"})):
        with pytest.raises(ValueError):
            facets._read(path, key, encoded, meta, client.validate_facets)
    assert facets._read(tmp_path / "absent.json", "k", b"req", {}, client.validate_facets) is None
