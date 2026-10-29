# Field-aware hybrid challenger: promotion investigation

Retain baseline: safety mostly passes, but gains are concentrated, paraphrase relevance losses are real, and the gain interval includes zero.

Frozen100-query dev comparison; cached-only, no tuning, paid calls, new labels or held-out test access. Reproduce: `python -m arxiv_search.evaluate.openai_field_review`.
All100 rankings reconstructed from weighted score components; identical top10 sets and positions11+ verified. Human overrides remain unchanged.

## Graded alternatives versus original-source metrics

| Segment | Relevant-paper MRR delta [95% CI] | Grade2-first rate delta [95% CI] |
|---|---|---|
| all | +0.00500 [+0.00000,+0.01500] | +0.01000 [-0.03025,+0.05000] |
| keyword | +0.00000 [+0.00000,+0.00000] | +0.04000 [+0.00000,+0.12000] |
| question | +0.02000 [+0.00000,+0.06000] | +0.00000 [-0.12000,+0.12000] |
| paraphrase | +0.00000 [+0.00000,+0.00000] | +0.00000 [-0.12000,+0.12000] |
| known_item | +0.00000 [+0.00000,+0.00000] | +0.00000 [+0.00000,+0.00000] |

## Gain concentration

Excluding largest observed gains is adversarial sensitivity, not a new test set.

| Metric | All100 delta | Exclude top1 | Exclude top3 | Exclude top5 |
|---|---|---|---|---|
| ndcg@10 | +0.002803 | +0.001904 | +0.000081 | -0.001342 |
| source_mrr@10 | +0.007917 | +0.001263 | -0.009021 | -0.019737 |

## Label sensitivity (hypothetical, no edits)

Adversarial one-grade-step changes to top10 labels; at most one label per query. Recompute both systems and pool IDCG. Hypothetical only; no labels or human overrides changed. Not estimated annotation error.

{'1': 0.0017664048986756123, '3': 9.980747031889054e-05, '5': -0.001334637420168044, '10': -0.004238590356993617}

## Reversed top10 pairs by frozen grade

Pair counts are descriptive, not independent samples or DCG contributions. Title-decisive means removing only the title contribution changes the pair's margin sign while holding normalization fixed; it is not an abstract-only experiment.

| Segment | Helpful | Harmful | Equal grade | Harmful title-decisive |
|---|---|---|---|---|
| all | 190 | 144 | 290 | 58 |
| keyword | 47 | 22 | 66 | 8 |
| question | 52 | 40 | 68 | 14 |
| paraphrase | 42 | 52 | 72 | 27 |
| known_item | 49 | 30 | 84 | 9 |

## Largest graded losses and gains

| Query | Source rank | nDCG delta | Query text |
|---|---|---|---|
| q-paraphrase-088 | 2 -> 3 | -0.053884 | a review of using programmable scripts as the core structure for managing ai assistant reasoning and tool execution |
| q-paraphrase-008 | 2 -> 4 | -0.040250 | managing delivery drivers who work for several different apps using reinforcement learning without seeing all their data |
| q-paraphrase-096 | None -> None | -0.037319 | a way to find relevant text chunks using a hierarchy of summaries to connect search terms and documents |
| q-paraphrase-087 | 9 -> 7 | -0.036937 | finding the best evidence subgraphs from a hidden knowledge graph without needing to train the system |
| q-known_item-029 | 1 -> 1 | -0.034392 | Zhou wind bridge forecasting |
| q-known_item-025 | 1 -> 1 | -0.034370 | poliakov metadata filtering RAG |
| q-paraphrase-014 | 2 -> 1 | +0.091833 | finding a probabilistic upper limit on how far the actor parameter stays from the optimal value in a slow-fast reinforcement learning setup |
| q-question-027 | 8 -> 8 | +0.090375 | How can we determine the compute requirements for large scale suggesting systems? |
| q-keyword-021 | 3 -> 1 | +0.090195 | transformer recommender popularity bias |

All100 query cases, exact inversions, grades, abstracts and score contributions are in `cases.json`. `report.json` retains every query delta and sensitivity.
Existing promotion rules still fail: positive nDCG lower interval and no segment regression. This investigation does not silently waive those rules. Fresh evaluation or an explicit policy exception is needed before promotion.
