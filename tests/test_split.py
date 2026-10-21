from collections import Counter

from arxiv_search.evaluate.split import split_queries


def make_queries():
    """400 queries with the real plan's mix: 4 types, keyword/question half broad, 3 categories."""
    queries = []
    for t in ["keyword", "question", "paraphrase", "known_item"]:
        for i in range(100):
            broad = t in ("keyword", "question") and i % 2 == 1
            queries.append({
                "query_id": f"q-{t}-{i:03d}",
                "query_type": t,
                "specificity": "broad" if broad else "specific",
                "category": ["cs.IR", "cs.CL", "cs.LG"][i % 3],
            })
    return queries


def test_split_sizes_and_no_overlap():
    split = split_queries(make_queries())
    assert len(split["dev"]) == 100 and len(split["test"]) == 300
    assert not set(split["dev"]) & set(split["test"])


def test_split_is_balanced():
    queries = make_queries()
    by_id = {q["query_id"]: q for q in queries}
    dev = [by_id[i] for i in split_queries(queries)["dev"]]
    assert Counter(q["query_type"] for q in dev) == {t: 25 for t in
                                                      ["keyword", "question", "paraphrase", "known_item"]}
    assert abs(Counter(q["specificity"] for q in dev)["broad"] - 25) <= 1
    assert all(abs(n - 33) <= 2 for n in Counter(q["category"] for q in dev).values())


def test_split_is_repeatable_and_order_independent():
    queries = make_queries()
    assert split_queries(queries) == split_queries(list(reversed(queries)))
