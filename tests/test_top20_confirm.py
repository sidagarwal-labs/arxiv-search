from arxiv_search.evaluate import top20_confirm as tc


def test_scope_is_remaining80_dev_only():
    plan = tc.prepare()
    assert len(plan["query_ids"]) == 80 and len(plan["requests"]) == 80
    assert plan["test_evaluation"] is False and plan["automatic_promotion"] is False
    assert all(len(r["presented_ids"]) == 20 for r in plan["requests"])


def test_summary_and_markdown():
    usage = [{"latency_seconds": 1.0, "input_tokens": 7000, "output_tokens": 100}] * 2
    rows = [{"query_id": f"q{i}", "query_type": "t", "d47": 0.5, "usage": usage,
             **{f"{n}{s}": v for n in ("candidate", "one_pass", "equal_rrf")
                for s, v in (("", 0.6), ("_source_delta", 0.0), ("_fully_judged", True),
                             ("_top20", []))}} for i in range(80)]
    acct = {"requests": 160, "unknown_outcomes": 0, "accounted_usd": 3.0}
    report = tc.summarize(rows, acct)
    assert report["confirmed"] and abs(report["variants"]["candidate"]["delta_vs_d47"] - 0.1) < 1e-9
    assert "Confirmed: **True**" in tc.markdown(report)


def test_run_requires_explicit_approval():
    import pytest
    with pytest.raises(SystemExit):
        tc.main(["--run"])
