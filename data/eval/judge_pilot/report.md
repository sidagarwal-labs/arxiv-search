# Judge pilot (rubric b8b0c14a)

12 dev queries, 266 query-paper pairs. Human grades so far: 100.

Preliminary calibration on one person's pilot labels, not held-out validation. Models with different coverage must be compared on the same pair subset. OpenAI's human-only run intentionally grades 100 pairs, not all 266 pooled pairs.

| Judge | Pairs graded | Calls | Mean s/call | Source papers graded 2 | Grade 0/1/2 shares |
|---|---|---|---|---|---|
| gemma-31b | 266 / 266 | 18 | 106 | 12 / 12 | 47% / 42% / 11% |
| qwen2.5-7b | 263 / 266 | 12 | 625 | 5 / 9 | 44% / 51% / 5% |
| openai-nano | 100 / 266 | 13 | 3 | 11 / 12 | 29% / 46% / 25% |
| openai-mini | 100 / 266 | 13 | 3 | 11 / 12 | 42% / 35% / 23% |

**Exact** = same grade. **κ** = Cohen's kappa (1 perfect, 0 chance; quadratic: 0-vs-2 costs most). **Relevant** = agree on 0 vs 1-or-2. **Opposite** = one said 0, the other 2.

| Comparison | Pairs | Exact | κ (quadratic) | Relevant agree | κ (relevant) | Opposite |
|---|---|---|---|---|---|---|
| gemma-31b vs human | 100 | 79% | 0.81 | 83% | 0.65 | 0 |
| qwen2.5-7b vs human | 97 | 59% | 0.43 | 67% | 0.32 | 3 |
| openai-nano vs human | 100 | 65% | 0.66 | 77% | 0.51 | 1 |
| openai-mini vs human | 100 | 77% | 0.80 | 84% | 0.67 | 0 |
| gemma-31b vs qwen2.5-7b | 263 | 51% | 0.28 | 58% | 0.16 | 5 |

## Fair comparison: identical 97 human-labeled pairs

| Judge | Exact | Quadratic kappa | Relevant agreement | 0-vs-2 errors |
|---|---|---|---|---|
| gemma-31b | 78.4% | 0.791 | 82.5% | 0 |
| qwen2.5-7b | 58.8% | 0.432 | 67.0% | 3 |
| openai-nano | 63.9% | 0.635 | 76.3% | 1 |
| openai-mini | 76.3% | 0.785 | 83.5% | 0 |

## API usage (successful cached responses)

Tokens are deduplicated by request ID where available. Older cache entries have no request IDs; their calls are estimated from query, batch size and duration. Gemma usage may omit failed API attempts; OpenAI's ledger separately accounts for unknown attempts conservatively. Wall time includes retries.

| Judge | Input tokens | Output tokens | Thinking tokens (included where applicable) |
|---|---|---|---|
| gemma-31b | 87,293 | 9,396 | 0 |
| qwen2.5-7b | 85,263 | 7,841 | 0 |
| openai-nano | 35,638 | 3,022 | 0 |
| openai-mini | 35,638 | 2,973 | 0 |

**gemma-31b vs human**: exact agreement by type: keyword 80% (n=25), question 88% (n=25), paraphrase 72% (n=25), known_item 76% (n=25)

| gemma-31b ↓ / human → | 0 | 1 | 2 |
|---|---|---|---|
| 0 | 35 | 10 | 0 |
| 1 | 7 | 28 | 2 |
| 2 | 0 | 2 | 16 |

**qwen2.5-7b vs human**: exact agreement by type: keyword 67% (n=24), question 58% (n=24), paraphrase 46% (n=24), known_item 64% (n=25)

| qwen2.5-7b ↓ / human → | 0 | 1 | 2 |
|---|---|---|---|
| 0 | 24 | 11 | 3 |
| 1 | 18 | 27 | 6 |
| 2 | 0 | 2 | 6 |

**openai-nano vs human**: exact agreement by type: keyword 68% (n=25), question 80% (n=25), paraphrase 60% (n=25), known_item 52% (n=25)

| openai-nano ↓ / human → | 0 | 1 | 2 |
|---|---|---|---|
| 0 | 24 | 5 | 0 |
| 1 | 17 | 26 | 3 |
| 2 | 1 | 9 | 15 |

**openai-mini vs human**: exact agreement by type: keyword 72% (n=25), question 92% (n=25), paraphrase 76% (n=25), known_item 68% (n=25)

| openai-mini ↓ / human → | 0 | 1 | 2 |
|---|---|---|---|
| 0 | 34 | 8 | 0 |
| 1 | 8 | 26 | 1 |
| 2 | 0 | 6 | 17 |

**gemma-31b vs qwen2.5-7b**: exact agreement by type: keyword 58% (n=71), question 51% (n=63), paraphrase 33% (n=67), known_item 61% (n=62)

| gemma-31b ↓ / qwen2.5-7b → | 0 | 1 | 2 |
|---|---|---|---|
| 0 | 66 | 60 | 0 |
| 1 | 45 | 60 | 6 |
| 2 | 5 | 14 | 7 |
