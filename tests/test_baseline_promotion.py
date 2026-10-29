import copy

import pytest

from arxiv_search import config
from arxiv_search.evaluate import baseline_promotion as promotion
from arxiv_search.search.hybrid import fuse_working_baseline
from arxiv_search.search.rank_score import rescore_shortlist


def test_headroom_is_exact_ordering_bound_with_fixed_membership():
    ids = [f"p{i}" for i in range(12)]
    labels = {"q": {p: 2 if i < 2 else 1 if i < 4 else 0 for i, p in enumerate(ids)}}
    run = {"q": ids[:10][::-1] + ids[10:]}
    inputs = {"q": {"lexical": [[p, 12 - i] for i, p in enumerate(ids)],
                    "semantic": [[p, 1.] for p in ids]}}
    queries = {"q": {"source_arxiv_id": "p11"}}
    result = promotion.bottlenecks(run, labels, inputs, queries)
    assert result["oracle_ndcg_with_fixed_top10"] == 1
    assert result["source_hits_current_top10"] == 0
    assert result["source_hits_in_retriever_union"] == {"10": 0, "100": 1, "500": 1}
    assert result["top10_grade_counts"] == {"0": 6, "1": 2, "2": 2}
    incomplete = copy.deepcopy(labels)
    del incomplete["q"]["p0"]
    with pytest.raises(ValueError, match="fully judged"):
        promotion.bottlenecks(run, incomplete, inputs, queries)
    with pytest.raises(ValueError, match="identical nonempty"):
        promotion.bottlenecks({}, {}, {}, {})


def test_charts_use_same_snapshot_and_real_milestones_not_provisional_scores():
    systems = {}
    for i, (_, name) in enumerate(promotion.MILESTONES):
        systems[name] = {
            "top10_fully_judged": True, "working_baseline": name == config.WORKING_BASELINE_SYSTEM,
            "all": {"ndcg@10": {"mean": .5 + i * .02}, "source_mrr@10": {"mean": .6},
                    "source_recall@10": {"mean": .86}},
            "description": {"ranker": name}, "leaderboard_rank": 7 - i,
        }
    report = {"systems": systems, "working_baseline": config.WORKING_BASELINE_SYSTEM,
              "leaderboard": {"ranked": list(reversed(systems))},
              "label_snapshot": "score-fusion-dev/labels.json", "label_snapshot_sha256": "frozen"}
    diagnosis = {"oracle_ndcg_with_fixed_top10": .78, "source_hits_current_top10": 86,
                 "queries": 100, "source_hits_in_retriever_union": {"100": 97, "500": 100},
                 "top10_grade_counts": {"0": 311, "1": 423, "2": 266}}
    text = promotion.render_charts(report, diagnosis)
    assert text.count("```mermaid") == 2
    assert "line [0.5000, 0.5200, 0.5400, 0.5600, 0.5800, 0.6000, 0.6200]" in text
    assert "**APPROVED BASELINE**" in text
    assert "0.7800" in text
    assert "y-axis \"nDCG@10 (higher is better)\" 0 --> 1" in text
    systems[promotion.MILESTONES[0][1]]["top10_fully_judged"] = False
    with pytest.raises(ValueError, match="provisional"):
        promotion.render_charts(report, diagnosis)


def test_working_helper_reproduces_approved_saved_rankings():
    import json

    root = config.RESULTS_DIR
    inputs = root / "score-fusion-dev" / "input-scores.json"
    saved = root / "shortlist-score-dev" / "fusion-shortlist+a=1+d=500.run.json"
    if not inputs.exists() or not saved.exists():
        pytest.skip("Full dev evidence not present in this checkout")
    values = json.loads(inputs.read_text())
    run = json.loads(saved.read_text())
    assert len(run) == 100
    for q, families in values.items():
        lex, sem = dict(families["lexical"]), dict(families["semantic"])
        assert fuse_working_baseline(lex, sem) == run[q]
        assert fuse_working_baseline(lex, sem, k=5) == run[q][:5]
        assert fuse_working_baseline(lex, sem, k=20) == run[q][:20]
    assert config.WORKING_BASELINE_SYSTEM == "fusion-shortlist+a=1+d=500"


def test_shortlist_configuration_and_missing_scores():
    lexical = {f"p{i}": 300. - i for i in range(150)}
    semantic = {f"p{i}": 1. - i / 200 for i in range(150)}
    assert rescore_shortlist(lexical, semantic, score_fraction=1, depth=500,
                             score_semantic_weight=.75, shortlist_size=10) == (
        fuse_working_baseline(lexical, semantic))
    with pytest.raises(ValueError, match="shortlist_size"):
        rescore_shortlist(lexical, semantic, score_fraction=1, depth=500, shortlist_size=0)
