import json

import pytest

from arxiv_search import openai_rerank as client
from arxiv_search.evaluate import llm_score_refine as refine
from arxiv_search.evaluate import results_catalog as catalog

PAPERS = {f"p{i}": {"title": f"Title {i}", "authors": ["A. Author"], "abstract": f"Abstract {i}."}
          for i in range(50)}
IDS = [f"p{i}" for i in range(20)]


def test_refine_version_has_its_own_cap_and_output_limit(tmp_path):
    assert client.separate_caps()[client.REFINE_VERSION] == (1_500_000_000, 200)
    assert client.REFINE_VERSION in client.VERSIONS
    assert client.PilotLedger(tmp_path / "r.db", version=client.REFINE_VERSION).output_cap \
        == client.REFINE_MAX_OUTPUT


def test_refine_payload_uses_the_score_evidence_with_a_0_to_10_schema():
    plain = json.loads(client.encode_score_payload("q", IDS[:10], PAPERS))
    payload = json.loads(client.encode_refine_payload("q", IDS, PAPERS))
    papers = json.loads(payload["input"])["papers"]
    assert papers[:10] == json.loads(plain["input"])["papers"] and len(papers) == 20
    assert payload["model"] == plain["model"] and payload["reasoning"] == plain["reasoning"]
    assert payload["instructions"] == client.REFINE_SYSTEM
    assert payload["max_output_tokens"] == client.REFINE_MAX_OUTPUT
    fmt = payload["text"]["format"]
    assert fmt["name"] == "paper_refine_scores" and fmt["strict"] is True
    assert fmt["schema"]["required"] == [f"P{i}" for i in range(1, 21)]
    assert fmt["schema"]["properties"]["P7"] == {"type": "integer", "minimum": 0, "maximum": 10}


@pytest.mark.parametrize("ids,query", [(IDS[:19], "q"), (IDS[:19] + ["p0"], "q"), (IDS, " ")])
def test_refine_payload_requires_exactly_20_unique_candidates_and_a_query(ids, query):
    with pytest.raises(ValueError):
        client.encode_refine_payload(query, ids, PAPERS)


def test_validate_refine_scores():
    good = {f"P{i}": i % 11 for i in range(1, 21)}
    assert client.validate_refine_scores(good) == good
    for bad in ({**good, "P1": 11}, {**good, "P1": -1}, {**good, "P1": 5.0}, {**good, "P1": True},
                {k: v for k, v in good.items() if k != "P20"}, {**good, "P21": 1}, [1]):
        with pytest.raises(ValueError):
            client.validate_refine_scores(bad)
    with pytest.raises(ValueError):
        client.validate_refine_scores(good, 10)


def test_refine_sorts_top20_by_average_ties_keep_decision46_order_tail_unchanged():
    d46 = [f"p{i}" for i in range(30)]
    presented = list(reversed(d46[:20]))  # P1 = p19 ... P20 = p0
    first = {f"P{i}": 5 for i in range(1, 21)}
    second = dict(first)
    first["P1"], second["P1"] = 10, 9  # p19 -> 9.5
    first["P20"], second["P20"] = 0, 1  # p0 -> 0.5
    first["P10"], second["P10"] = 9, 10  # p10 -> 9.5, ties p19 and keeps Decision46 order
    out = refine.refine(d46, presented, [first, second])
    assert out[:2] == ["p10", "p19"]
    assert out[2:19] == [p for p in d46[1:20] if p not in ("p10", "p19")]
    assert out[19] == "p0" and out[20:] == d46[20:]
    with pytest.raises(ValueError):
        refine.refine(d46, presented[:19] + ["p25"], [first, second])


def test_plan_is_one_change_on_decision46_and_systems_are_described():
    assert refine.REFERENCE == "llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30"
    assert refine.PRIMARY == "llm-mini-refine20+d=20+avg2+rrf-d46+c=30"
    assert refine.PLAN["held_out_queries_used"] is False and refine.PLAN["automatic_retries"] is False
    assert refine.PLAN["pilot_gate"] == refine.facets.PLAN["pilot_gate"]
    assert "safeguard" in catalog.describe_system(refine.PRIMARY)["name"]
    assert "no safeguard" in catalog.describe_system(refine.SECONDARY)["ranker"]


def test_verdicts_use_this_experiments_systems_and_reference():
    def scope(d):
        systems = {refine.REFERENCE: {"all": {"source_mrr@10": {"mean": 0.8}}, "top10_fully_judged": True}}
        summary = {}
        for n in refine.SYSTEMS:
            systems[n] = {"all": {"source_mrr@10": {"mean": 0.8}}, "top10_fully_judged": True}
            summary[n] = {"all": {"ndcg@10": {"paired_vs_working": {"difference": d, "ci95": [d - .01, d + .01]}}}}
        return {"systems": systems, "summary": summary}
    out = refine.verdicts({"pilot20": scope(0.01)}, ("pilot20",), None)
    assert set(out) == set(refine.SYSTEMS) and all(v["passes"] for v in out.values())
