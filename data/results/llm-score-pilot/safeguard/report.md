# Offline safeguard replay: top50 LLM order fused with baseline order

Rule (frozen before computing): `1/(30+baseline rank) + 1/(30+LLM rank)` over the top 50; ties keep baseline order; ranks 51-100 unchanged. No API calls, no sweep.

Missing top10 grades: **1**.

| System | nDCG10 | P10 | Judged10 | Source MRR10 | R10 | R20 |
|---|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.6959 | 0.6750 | 1.0000 | 0.8375 | 0.9000 | 0.9000 |
| `llm-mini-score-pilot+d=10` | 0.7095 | 0.6750 | 1.0000 | 0.8417 | 0.9000 | 0.9000 |
| `llm-mini-score-pilot+d=50` | 0.7553 | 0.7700 | 1.0000 | 0.6875 | 0.8500 | 0.9000 |
| `llm-mini-score-pilot+d=50+rrf-baseline+c=30` | withheld | withheld | 0.9950 | 0.8292 | 0.9000 | 0.9000 |

## Pre-registered criteria

| Criterion | Threshold | Result |
|---|---|---|
| source_mrr@10 | >= 0.8175 | 0.8292 (pass) |
| ndcg@10 | >= 0.7256 | withheld |

## Paired versus baseline

| System | nDCG10 delta [95% CI] | Source MRR10 delta [95% CI] |
|---|---|---|
| `llm-mini-score-pilot+d=50` | +0.0593 [+0.0006,+0.1155] | -0.1500 [-0.3083,+0.0000] |
| `llm-mini-score-pilot+d=50+rrf-baseline+c=30` | withheld | -0.0083 [-0.1417,+0.1125] |

## Segment nDCG10

| System | keyword | question | paraphrase | known_item |
|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.7188 | 0.7211 | 0.6575 | 0.6863 |
| `llm-mini-score-pilot+d=10` | 0.7494 | 0.7328 | 0.6789 | 0.6770 |
| `llm-mini-score-pilot+d=50` | 0.7396 | 0.8276 | 0.7531 | 0.7008 |
| `llm-mini-score-pilot+d=50+rrf-baseline+c=30` | 0.7358 | withheld | 0.7139 | 0.7046 |

## Missing-grade sensitivity (diagnostic, not a label)

Every unjudged top10 pair set to the same assumed grade; all systems rescored.

| Assumed grade | Baseline | Top50 LLM | Safeguard | Threshold | Delta [95% CI] | Passes |
|---|---|---|---|---|---|---|
| 0 | 0.6959 | 0.7553 | 0.7321 | 0.7256 | +0.0362 [+0.0001,+0.0704] | yes |
| 1 | 0.6959 | 0.7553 | 0.7344 | 0.7256 | +0.0385 [+0.0028,+0.0727] | yes |
| 2 | 0.6927 | 0.7519 | 0.7334 | 0.7223 | +0.0407 [+0.0039,+0.0746] | yes |

## Source ranks that differ from baseline

| Query | Baseline | Top50 LLM | Safeguard |
|---|---|---|---|
| q-keyword-017 | 1 | 3 | 1 |
| q-keyword-079 | 1 | 15 | 4 |
| q-keyword-081 | 2 | 1 | 1 |
| q-known_item-042 | 1 | 2 | 1 |
| q-paraphrase-020 | 4 | 4 | 1 |
| q-question-088 | 1 | 2 | 1 |
| q-question-095 | 1 | 6 | 3 |

## Cautions

- 20 previously examined dev queries; the rule was motivated by these same losses.
- Judge and reranker share a model family; no independent validation.
- No promotion.
