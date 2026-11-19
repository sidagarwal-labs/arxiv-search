import copy
import json

import pytest

from arxiv_search.evaluate import failure_taxonomy as tax

PAPERS = [f"p{i:02d}" for i in range(60)]


def ranks(d36, d46, d50):
    return {"lexical": None, "semantic": None, "d36": d36, "d46": d46, "d47": d46, "d50": d50}


def test_source_stage_attribution():
    assert tax.source_stage(ranks(1, 1, 3)) is None
    assert tax.source_stage(ranks(None, None, None)) == "stage1_retrieval"
    assert tax.source_stage(ranks(58, 58, 58)) == "stage1_retrieval"
    assert tax.source_stage(ranks(27, 21, 21)) == "d46_rerank"
    assert tax.source_stage(ranks(5, 12, 14)) == "d50_refine"
    assert tax.failure_stage({"source_stage": None, "graded_loss_stage": "d46_rerank"}) == "d46_rerank"
    assert tax.failure_stage({"source_stage": "stage1_retrieval",
                              "graded_loss_stage": "d50_refine"}) == "stage1_retrieval"


def test_query_rows_attribute_source_and_graded_loss():
    queries = {"q": {"query": "topic", "query_type": "keyword", "category": "cs.IR",
                     "specificity": "broad", "overlap": 0.5, "source_arxiv_id": "p25"}}
    d36 = list(PAPERS)
    d46 = list(PAPERS)  # source stays at 26: outside the D50 re-scoring window
    runs = {"d36": {"q": d36}, "d46": {"q": d46}, "d47": {"q": d46}, "d50": {"q": d46}}
    components = {"lexical": {"q": d36[:30]}, "semantic": {"q": ["p59"]}}
    grades = {**{p: 0 for p in PAPERS[:10]}, "p00": 2, "p25": 2}
    rows, parts = tax.query_rows(runs, components, {"q": grades}, queries)
    row = rows[0]
    assert row["source_ranks"] == {"lexical": 26, "semantic": None, "d36": 26, "d46": 26,
                                   "d47": 26, "d50": 26}
    assert row["source_stage"] == "d46_rerank"
    assert row["source_recall@10"] == 0.0 and row["source_mrr@10"] == 0.0
    assert row["judged@10"] == 1.0 and row["source_grade"] == 2
    assert row["graded_loss_stage"] == "d46_rerank"
    assert row["graded_loss"]["d46_rerank"] == pytest.approx(parts[0]["loss"]["screening_21_50"])
    assert sum(row["graded_loss"].values()) == pytest.approx(1 - row["ndcg@10"])


def row(qid, ndcg, hit=True, **extra):
    base = {"query_id": qid, "ndcg@10": ndcg, "source_recall@10": float(hit),
            "source_mrr@10": 1.0 if hit else 0.0, "query_type": "keyword",
            "category": "cs.IR", "specificity": "specific", "source_stage": None,
            "graded_loss_stage": "d50_refine"}
    return {**base, **extra}


def test_select_cases_combines_source_misses_and_lowest_ndcg():
    rows = [row("q-a", 0.5), row("q-b", 0.5), row("q-c", 0.4, hit=False), row("q-d", 0.9, hit=False),
            row("q-e", 0.8), row("q-f", None)]
    assert tax.select_cases(rows, lowest=2) == {
        "q-a": ["lowest_ndcg"],  # tie at 0.5 broken by query ID
        "q-c": ["source_outside_top10", "lowest_ndcg"],
        "q-d": ["source_outside_top10"],
    }


def test_segment_rows_count_cells_and_omit_small_ci():
    rows = ([row(f"q-k{i}", 0.5 + i / 10, hit=i != 0) for i in range(5)]
            + [row("q-q", 0.3, query_type="question", category="cs.CL", specificity="broad")])
    cells = {(c["group"], c["segment"]): c for c in tax.segment_rows(rows, {"q-k0", "q-q"})}
    assert cells[("all", "all")]["n"] == 6 and cells[("all", "all")]["failure_cases"] == 2
    keyword = cells[("query_type", "keyword")]
    assert (keyword["n"], keyword["source_misses"], keyword["failure_cases"]) == (5, 1, 1)
    assert keyword["ndcg@10"]["mean"] == pytest.approx(0.7)
    assert keyword["ndcg@10"]["ci95"] is not None
    assert keyword["source_recall@10"]["mean"] == pytest.approx(0.8)
    question = cells[("query_type x category", "question / cs.CL")]
    assert question["n"] == 1 and question["ndcg@10"] == {"mean": 0.3, "ci95": None}
    assert "(n<5, no CI)" in tax._fmt(question["ndcg@10"])
    assert {c["segment"] for c in cells.values() if c["group"] == "specificity"} == {"broad", "specific"}


def annotations():
    return {
        "codebook": {"version": "v1", "causes": [
            {"id": cid, "definition": "d", "decision_rule": "r"}
            for cid in ("vocabulary_gap", "label_gap", "rerank_demotion")]},
        "provenance": {k: "x" for k in tax.REQUIRED_PROVENANCE},
        "annotations": [
            {"query_id": "q-a", "primary_cause": "vocabulary_gap",
             "secondary_causes": ["rerank_demotion"], "rationale": "why"},
            {"query_id": "q-b", "primary_cause": "label_gap", "secondary_causes": [],
             "rationale": "why"}],
        "candidate_fixes": [{"cause": "label_gap", "proposal": "audit"}],
    }


def test_valid_annotations_are_indexed_by_query():
    assert set(tax.validate_annotations(annotations(), {"q-a", "q-b"})) == {"q-a", "q-b"}


@pytest.mark.parametrize("change, cases, message", [
    (lambda d: d["annotations"].append({**d["annotations"][0], "query_id": "q-z"}),
     {"q-a", "q-b"}, "not current failure cases"),
    (lambda d: None, {"q-a", "q-b", "q-c"}, "Unannotated failure cases"),
    (lambda d: d["annotations"].append(dict(d["annotations"][0])), {"q-a", "q-b"}, "Duplicate"),
    (lambda d: d["annotations"][0].update(primary_cause="other"), {"q-a", "q-b"},
     "unknown primary cause"),
    (lambda d: d["annotations"][0].update(secondary_causes=["vocabulary_gap"]), {"q-a", "q-b"},
     "secondary causes"),
    (lambda d: d["annotations"][0].update(secondary_causes=["other"]), {"q-a", "q-b"},
     "secondary causes"),
    (lambda d: d["annotations"][1].update(rationale="  "), {"q-a", "q-b"}, "rationale required"),
    (lambda d: d["provenance"].pop("Annotators"), {"q-a", "q-b"}, "provenance is missing"),
    (lambda d: d["codebook"]["causes"][0].pop("decision_rule"), {"q-a", "q-b"}, "Codebook"),
    (lambda d: d["candidate_fixes"].append({"cause": "other", "proposal": "x"}), {"q-a", "q-b"},
     "candidate fix"),
])
def test_invalid_or_stale_annotations_refused(change, cases, message):
    data = copy.deepcopy(annotations())
    change(data)
    with pytest.raises(ValueError, match=message):
        tax.validate_annotations(data, cases)


def test_main_refuses_stale_annotations_before_writing(tmp_path, monkeypatch):
    built = {"evidence": {}, "cases": {"q-a": ["lowest_ndcg"]}, "fix_fingerprints": {}}
    monkeypatch.setattr(tax, "build", lambda: built)
    monkeypatch.setattr(tax, "freeze", lambda path, plan: None)
    monkeypatch.setattr(tax, "OUT", tmp_path)
    monkeypatch.setattr(tax, "FIX_PLAN", tmp_path / "fix-plan.json")
    monkeypatch.setattr(tax, "ANNOTATIONS", tmp_path / "annotations.json")
    (tmp_path / "fix-plan.json").write_text("{}")
    (tmp_path / "annotations.json").write_text(json.dumps(annotations()))
    with pytest.raises(ValueError, match="not current failure cases"):
        tax.main([])
    assert not (tmp_path / "report.json").exists() and not (tmp_path / "cases.json").exists()


def test_main_requires_frozen_fix_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(tax, "build", lambda: {"evidence": {}, "cases": {}, "fix_fingerprints": {}})
    monkeypatch.setattr(tax, "FIX_PLAN", tmp_path / "missing.json")
    with pytest.raises(SystemExit, match="Freeze the fix-test plan"):
        tax.main([])


def test_taxonomy_counts_primary_secondary_stage_and_type():
    data = annotations()
    data["annotations"].append({"query_id": "q-c", "primary_cause": "vocabulary_gap",
                                "secondary_causes": ["label_gap", "rerank_demotion"],
                                "rationale": "why"})
    by_id = tax.validate_annotations(data, {"q-a", "q-b", "q-c"})
    rows = {"q-a": row("q-a", 0.9, hit=False, source_stage="stage1_retrieval",
                       query_type="paraphrase"),
            "q-b": row("q-b", 0.4),
            "q-c": row("q-c", 0.5, graded_loss_stage="d46_rerank")}
    cases = {"q-a": ["source_outside_top10"], "q-b": ["lowest_ndcg"], "q-c": ["lowest_ndcg"]}
    out = tax.taxonomy(cases, rows, by_id, ["vocabulary_gap", "label_gap", "rerank_demotion"])
    assert out["cases"] == 3
    assert out["primary"] == {"vocabulary_gap": 2, "label_gap": 1}
    assert out["secondary"] == {"label_gap": 1, "rerank_demotion": 2}
    assert out["by_failure_stage"] == {"stage1_retrieval": {"vocabulary_gap": 1},
                                       "d46_rerank": {"vocabulary_gap": 1},
                                       "d50_refine": {"label_gap": 1}}
    assert out["by_query_type"] == {"keyword": {"vocabulary_gap": 1, "label_gap": 1},
                                    "paraphrase": {"vocabulary_gap": 1}}
    assert out["by_selection"] == {"source_outside_top10": {"vocabulary_gap": 1},
                                   "lowest_ndcg": {"vocabulary_gap": 1, "label_gap": 1}}


def replies_for(scores_by_paper, presented):
    return {f"P{i}": scores_by_paper.get(p, 0) for i, p in enumerate(presented, 1)}


def test_refine_order_pin_tiebreak_and_unchanged_tail():
    base = PAPERS[:25]
    presented = list(reversed(base[:20]))
    first = replies_for({"p05": 10, "p03": 8, "p07": 8, "p00": 2}, presented)
    second = replies_for({"p05": 9, "p03": 8, "p07": 8, "p00": 2}, presented)
    pinned = tax.refine_order(base, presented, [first, second])
    unpinned = tax.refine_order(base, presented, [first, second], pin=False)
    assert unpinned[:4] == ["p05", "p03", "p07", "p00"]  # p03 before p07: base order breaks the tie
    assert pinned[:4] == ["p00", "p05", "p03", "p07"]
    assert pinned[20:] == unpinned[20:] == base[20:]
    assert sorted(pinned[:20]) == sorted(unpinned[:20]) == sorted(base[:20])
    with pytest.raises(ValueError, match="presented papers"):
        tax.refine_order(base, presented[:-1] + ["p20"], [first, second])


@pytest.mark.parametrize("reply", [
    {f"P{i}": 5 for i in range(1, 20)},
    {**{f"P{i}": 5 for i in range(1, 21)}, "P1": 5.5},
    {**{f"P{i}": 5 for i in range(1, 21)}, "P2": 11},
    {**{f"P{i}": 5 for i in range(1, 21)}, "P3": True},
])
def test_refine_scores_rejects_malformed_replies(reply):
    with pytest.raises(ValueError, match="integer score"):
        tax.refine_scores(reply)


def fix_row(qid, d50, unpinned, judged=1.0, mrr=(1.0, 1.0)):
    def m(ndcg, source_mrr, judged_at_10, grade):
        return {"ndcg@10": ndcg, "source_mrr@10": source_mrr, "source_recall@10": 1.0,
                "judged@10": judged_at_10, "rank1_grade": grade}
    return {"query_id": qid, "query_type": "keyword", "rank1_changed": d50 != unpinned,
            "d50": m(d50, mrr[0], 1.0, 0), "unpinned": m(unpinned, mrr[1], judged, 2)}


def test_summarize_fix_applies_frozen_rule_and_flags_provisional():
    rows = [fix_row(f"q{i}", 0.5, 0.6) for i in range(10)]
    out = tax.summarize_fix(rows, {"q0"})
    assert out["supportive"] and not out["provisional"]
    assert out["ndcg@10"]["delta"] == pytest.approx(0.1)
    assert out["wins_losses_ties"] == [10, 0, 0] and out["rank1_changed"] == 10
    assert out["rank1_grade0"] == {"d50": 10, "unpinned": 0}
    assert out["failure_cases"] == {"n": 1, "ndcg_delta": pytest.approx(0.1)}

    small = [fix_row(f"q{i}", 0.5, 0.505) for i in range(10)]
    assert not tax.summarize_fix(small, set())["supportive"]
    mrr_loss = [fix_row(f"q{i}", 0.5, 0.6, mrr=(1.0, 0.5)) for i in range(10)]
    assert not tax.summarize_fix(mrr_loss, set())["supportive"]
    unjudged = rows[:-1] + [fix_row("q9", 0.5, 0.6, judged=0.9)]
    out = tax.summarize_fix(unjudged, set())
    assert out["provisional"] and not out["supportive"]
    assert out["failure_cases"] == {"n": 0, "ndcg_delta": None}


def test_dev_queries_drop_held_out_rows():
    split = json.dumps({"dev": ["q-b", "q-a"], "test": ["q-t"]}).encode()
    lines = [{"query_id": q, "query": q} for q in ("q-a", "q-t", "q-b")]
    queries = "\n".join(json.dumps(x) for x in lines).encode()
    qids, rows = tax.dev_queries(split, queries)
    assert qids == ["q-a", "q-b"] and set(rows) == {"q-a", "q-b"}
    overlap = json.dumps({"dev": ["q-a"], "test": ["q-a"]}).encode()
    with pytest.raises(ValueError, match="disjoint"):
        tax.dev_queries(overlap, queries)
