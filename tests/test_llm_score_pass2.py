from arxiv_search import openai_rerank as client


def test_pass2_has_its_own_capped_ledger_identity():
    cap, requests = client.separate_caps()[client.PASS2_VERSION]
    assert requests == 80 and cap == 1_400_000_000
    assert client.PASS2_VERSION in client.VERSIONS
    # Identical bytes with a different intent get a distinct ledger key.
    assert client.repeat_key(b"x", 1) != client.repeat_key(b"x", 2)
