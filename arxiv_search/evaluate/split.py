"""Split the 400 test queries into DEV (100) and TEST (300).

- DEV is for tuning: trying BM25 settings, hybrid weights, prompt tweaks. Look at it freely.
- TEST is for the final report only. If we tuned on it, our scores would look better than the
  system really is (we'd be fitting to these exact queries).

The split is balanced: each query type is exactly 1/4 dev, and specificity and category are
within a query or two of 1/4. How: group the queries by (type, specificity), shuffle each
category with a fixed seed, deal the categories out in turn (IR, CL, LG, IR, CL, LG, ...),
then send every 4th query to dev. Same seed -> same split, every time.

Output: data/eval/split.json = {"dev": [query_id, ...], "test": [query_id, ...]}
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from itertools import zip_longest

from arxiv_search import config
from arxiv_search.evaluate.make_queries import load_jsonl

DEV_EVERY = 4  # every 4th query in a group -> dev (100 of 400)


def split_queries(queries: list[dict], seed: int = config.RANDOM_SEED) -> dict[str, list[str]]:
    blocks: dict[tuple, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for q in queries:
        blocks[(q["query_type"], q["specificity"])][q["category"]].append(q["query_id"])

    rng = random.Random(seed)
    ordered = []
    for b, key in enumerate(sorted(blocks)):  # sorted so the result doesn't depend on file order
        by_category = [sorted(blocks[key][c]) for c in sorted(blocks[key])]
        for ids in by_category:
            rng.shuffle(ids)
        # Rotate which category goes first, so no category always gets the leftover dev spot.
        by_category = by_category[b % len(by_category):] + by_category[: b % len(by_category)]
        # Deal out one query per category in turn, so every 4th pick mixes categories evenly.
        ordered.extend(i for row in zip_longest(*by_category) for i in row if i is not None)

    dev = ordered[::DEV_EVERY]
    dev_set = set(dev)
    return {"dev": sorted(dev), "test": sorted(i for i in ordered if i not in dev_set)}


def main() -> None:
    queries = load_jsonl(config.EVAL_DIR / "queries.jsonl")
    split = split_queries(queries)
    (config.EVAL_DIR / "split.json").write_text(json.dumps(split, indent=2))
    print(f"dev {len(split['dev'])}, test {len(split['test'])} -> {config.EVAL_DIR / 'split.json'}")


if __name__ == "__main__":
    main()
