"""Tests for evaluate/make_queries.py. A fake LLM stands in for Gemini, so no network."""

from collections import Counter

from arxiv_search.evaluate.make_queries import (
    GeneratedBatch,
    GeneratedQuery,
    check_query,
    generate_queries,
    overlap,
    plan_slots,
    shares_run,
    words,
)

PAPER = {
    "arxiv_id": "2501.00001",
    "title": "Attention Calibration for Transformer-based Sequential Recommendation",
    "abstract": "We propose a method that calibrates attention weights in sequential recommenders.",
    "authors": ["Peilin Zhou", "Qichen Ye", "Sunghun Kim"],
    "primary_category": "cs.IR",
}


def slot(query_type, specificity="specific"):
    return {"slot_id": "x", "query_type": query_type, "specificity": specificity, "category": "cs.IR"}


# --- Plan -------------------------------------------------------------------


def test_plan_has_400_balanced_slots():
    slots = plan_slots()
    assert len(slots) == 400
    assert Counter(s["query_type"] for s in slots) == {
        "keyword": 100, "question": 100, "paraphrase": 100, "known_item": 100}
    assert Counter(s["specificity"] for s in slots) == {"specific": 300, "broad": 100}
    assert Counter(s["category"] for s in slots) == {"cs.IR": 136, "cs.CL": 132, "cs.LG": 132}


def test_every_call_of_four_has_one_of_each_type():
    slots = plan_slots()
    for start in range(0, 400, 4):
        assert len({s["query_type"] for s in slots[start : start + 4]}) == 4


def test_only_keyword_and_question_are_ever_broad():
    broad_types = {s["query_type"] for s in plan_slots() if s["specificity"] == "broad"}
    assert broad_types == {"keyword", "question"}


# --- Checks -----------------------------------------------------------------


def test_shares_run():
    assert shares_run(words("new attention calibration for transformer"), words(PAPER["title"]), 4)
    assert not shares_run(words("attention calibration recommenders"), words(PAPER["title"]), 4)


def test_overlap():
    # content words: fixing, attention, recommenders -> 2 of 3 appear in the paper
    assert overlap("fixing attention in recommenders", PAPER) == 2 / 3


def test_check_accepts_good_queries():
    assert check_query("attention calibration recommenders", slot("keyword"), PAPER) == []
    assert check_query("zhou attention sequential recommendation", slot("known_item"), PAPER) == []


def test_check_rejects_title_copy_and_bad_length():
    problems = check_query("attention calibration for transformer based recommender models", slot("keyword"), PAPER)
    assert any("title" in p for p in problems)
    assert any("length" in p for p in problems)  # 7 words > 6


def test_check_question_needs_question_mark():
    problems = check_query("how can attention weights be fixed in recommenders", slot("question"), PAPER)
    assert problems == ["question does not end with '?'"]


def test_check_known_item_needs_author():
    assert check_query("attention fix recommender paper", slot("known_item"), PAPER) == [
        "known_item query names no author"]


def test_check_paraphrase_overlap():
    reused = "a method that calibrates attention weights inside sequential recommenders systems"
    assert any("reuses" in p for p in check_query(reused, slot("paraphrase"), PAPER))


def test_check_rejects_reshuffled_title():
    # All 4 content words come from the title, but never 4 in a row.
    problems = check_query("sequential recommendation attention calibration", slot("keyword"), PAPER)
    assert problems == ["mostly the title's own words, rearranged"]


def test_known_item_may_reuse_title_words():
    query = "zhou attention calibration sequential recommendation"
    assert check_query(query, slot("known_item"), PAPER) == []


def test_check_rejects_self_reference():
    query = "This paper teaches recommenders to pay attention to the right past items for users"
    assert "refers to 'this paper' / 'the authors'" in check_query(query, slot("paraphrase"), PAPER)


# --- Generation loop with a fake LLM -----------------------------------------


def make_corpus(n_per_category=200):
    corpus = []
    for category in ("cs.IR", "cs.CL", "cs.LG"):
        for i in range(n_per_category):
            corpus.append({
                "arxiv_id": f"{category}-{i:04d}", "title": f"Study number {i}",
                "abstract": "Some abstract text about a topic.", "authors": [f"Ann Author{i}"],
                "primary_category": category,
            })
    return corpus


def fake_generate(prompt):
    """Returns a valid query for every paper in the prompt, built from the TASK line."""
    queries = []
    for block in prompt.split("PAPER ")[1:]:
        arxiv_id = block.split("\n")[0]
        task = block.split("type=")[1].split(",")[0]
        surname = block.split("Authors: ")[1].split()[1].lower()
        text = {"keyword": "graph learning methods",
                "question": "how do graph methods help retrieval?",
                "paraphrase": "teaching computers to find related documents more quickly overall",
                "known_item": f"{surname} graph retrieval"}[task]
        queries.append(GeneratedQuery(arxiv_id=arxiv_id, query=text))
    return GeneratedBatch(queries=queries)


def test_generation_fills_all_slots_and_writes_files(tmp_path):
    queries = generate_queries(make_corpus(), tmp_path, generate=fake_generate, max_calls=200)
    assert len(queries) == 400
    assert len({q["source_arxiv_id"] for q in queries}) == 400  # every query from a different paper
    assert all(q["category"] == q["source_arxiv_id"].split("-")[0] for q in queries)
    assert (tmp_path / "queries.jsonl").exists() and (tmp_path / "attempts.jsonl").exists()


def test_generation_resumes_without_repeating_work(tmp_path):
    corpus = make_corpus()
    first = generate_queries(corpus, tmp_path, generate=fake_generate, max_calls=3)
    assert len(first) == 12  # the pilot: 3 calls x 4 papers
    calls = []

    def counting_generate(prompt):
        calls.append(prompt)
        return fake_generate(prompt)

    rest = generate_queries(corpus, tmp_path, generate=counting_generate, max_calls=200)
    assert len(rest) == 400
    assert len(calls) == 97  # only the remaining 388 queries were requested
    assert [q["source_arxiv_id"] for q in rest[:12]] == [q["source_arxiv_id"] for q in first]


def test_failing_slot_is_retried_then_gets_new_paper(tmp_path):
    prompts_seen = []

    def bad_for_first_paper(prompt):
        prompts_seen.append(prompt)
        batch = fake_generate(prompt)
        for q in batch.queries:
            if q.arxiv_id == first_paper[0]:
                q.query = "x"  # too short -> rejected
        return batch

    first_paper = []
    plan_paper = generate_queries(make_corpus(), tmp_path / "probe", generate=fake_generate, max_calls=1)
    first_paper.append(plan_paper[0]["source_arxiv_id"])

    queries = generate_queries(make_corpus(), tmp_path / "run", generate=bad_for_first_paper, max_calls=200)
    assert len(queries) == 400
    assert first_paper[0] not in {q["source_arxiv_id"] for q in queries}  # replaced after 2 failures
    # The retry told the model why the first attempt was rejected.
    assert "NOTE: your previous query for this paper was rejected (length 1 words" in prompts_seen[1]
