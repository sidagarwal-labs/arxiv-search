# Full-dev evaluation: top50 LLM reranker and baseline safeguard

Same method as the v2 top50 pilot arm and the Decision42 safeguard rule, on all 100 dev queries. The 20 pilot queries reuse cached responses; `new80` is the out-of-sample check because the safeguard was designed on the 20. Held-out queries untouched.

New top10 pairs graded: **133** of 133; still missing: **0**.

## all100 (100 queries)

| System | nDCG10 | P10 | Judged10 | Source MRR10 | R10 | R20 |
|---|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.7092 | 0.6890 | 1.0000 | 0.6967 | 0.8600 | 0.8900 |
| `llm-mini-score-pilot+d=50` | 0.7789 | 0.7770 | 1.0000 | 0.6775 | 0.8800 | 0.9200 |
| `llm-mini-score-pilot+d=50+rrf-baseline+c=30` | 0.7583 | 0.7360 | 1.0000 | 0.7197 | 0.8700 | 0.9100 |

| Arm vs baseline | nDCG10 delta [95% CI] | P10 delta [95% CI] | Source MRR10 delta [95% CI] | nDCG W/L/T |
|---|---|---|---|---|
| `llm-mini-score-pilot+d=50` | +0.0697 [+0.0446,+0.0954] | +0.0880 [+0.0610,+0.1130] | -0.0192 [-0.0825,+0.0460] | 68/22/10 |
| `llm-mini-score-pilot+d=50+rrf-baseline+c=30` | +0.0491 [+0.0347,+0.0633] | +0.0470 [+0.0300,+0.0640] | +0.0230 [-0.0144,+0.0639] | 69/21/10 |

Pre-registered safeguard criteria: source_mrr@10 0.7197 vs >= 0.6767 (pass); ndcg@10 0.7583 vs >= 0.7440 (pass)

| Segment | `fusion-shortlist+a=1+d=500` | `llm-mini-score-pilot+d=50` | `llm-mini-score-pilot+d=50+rrf-baseline+c=30` |
|---|---|---|---|
| keyword (nDCG / MRR) | 0.7318 / 0.720 | 0.7516 / 0.652 | 0.7604 / 0.709 |
| question (nDCG / MRR) | 0.7150 / 0.588 | 0.8432 / 0.585 | 0.7854 / 0.595 |
| paraphrase (nDCG / MRR) | 0.6759 / 0.498 | 0.7693 / 0.493 | 0.7517 / 0.574 |
| known_item (nDCG / MRR) | 0.7140 / 0.980 | 0.7515 / 0.980 | 0.7357 / 1.000 |

## new80 (80 queries)

| System | nDCG10 | P10 | Judged10 | Source MRR10 | R10 | R20 |
|---|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.7125 | 0.6925 | 1.0000 | 0.6615 | 0.8500 | 0.8875 |
| `llm-mini-score-pilot+d=50` | 0.7848 | 0.7787 | 1.0000 | 0.6750 | 0.8875 | 0.9250 |
| `llm-mini-score-pilot+d=50+rrf-baseline+c=30` | 0.7643 | 0.7400 | 1.0000 | 0.6923 | 0.8625 | 0.9125 |

| Arm vs baseline | nDCG10 delta [95% CI] | P10 delta [95% CI] | Source MRR10 delta [95% CI] | nDCG W/L/T |
|---|---|---|---|---|
| `llm-mini-score-pilot+d=50` | +0.0723 [+0.0464,+0.1004] | +0.0862 [+0.0587,+0.1137] | +0.0135 [-0.0513,+0.0802] | 55/18/7 |
| `llm-mini-score-pilot+d=50+rrf-baseline+c=30` | +0.0518 [+0.0351,+0.0689] | +0.0475 [+0.0288,+0.0663] | +0.0308 [-0.0056,+0.0722] | 58/15/7 |

Pre-registered safeguard criteria: source_mrr@10 0.6923 vs >= 0.6415 (pass); ndcg@10 0.7643 vs >= 0.7486 (pass)

| Segment | `fusion-shortlist+a=1+d=500` | `llm-mini-score-pilot+d=50` | `llm-mini-score-pilot+d=50+rrf-baseline+c=30` |
|---|---|---|---|
| keyword (nDCG / MRR) | 0.7351 / 0.675 | 0.7546 / 0.648 | 0.7666 / 0.674 |
| question (nDCG / MRR) | 0.7135 / 0.485 | 0.8471 / 0.547 | 0.7860 / 0.527 |
| paraphrase (nDCG / MRR) | 0.6805 / 0.511 | 0.7733 / 0.504 | 0.7611 / 0.568 |
| known_item (nDCG / MRR) | 0.7209 / 0.975 | 0.7642 / 1.000 | 0.7435 / 1.000 |

## pilot20 (20 queries)

| System | nDCG10 | P10 | Judged10 | Source MRR10 | R10 | R20 |
|---|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.6959 | 0.6750 | 1.0000 | 0.8375 | 0.9000 | 0.9000 |
| `llm-mini-score-pilot+d=50` | 0.7553 | 0.7700 | 1.0000 | 0.6875 | 0.8500 | 0.9000 |
| `llm-mini-score-pilot+d=50+rrf-baseline+c=30` | 0.7344 | 0.7200 | 1.0000 | 0.8292 | 0.9000 | 0.9000 |

| Arm vs baseline | nDCG10 delta [95% CI] | P10 delta [95% CI] | Source MRR10 delta [95% CI] | nDCG W/L/T |
|---|---|---|---|---|
| `llm-mini-score-pilot+d=50` | +0.0593 [+0.0006,+0.1155] | +0.0950 [+0.0250,+0.1650] | -0.1500 [-0.3083,+0.0000] | 13/4/3 |
| `llm-mini-score-pilot+d=50+rrf-baseline+c=30` | +0.0385 [+0.0028,+0.0727] | +0.0450 [+0.0100,+0.0800] | -0.0083 [-0.1417,+0.1125] | 11/6/3 |

Pre-registered safeguard criteria: source_mrr@10 0.8292 vs >= 0.8175 (pass); ndcg@10 0.7344 vs >= 0.7256 (pass)

| Segment | `fusion-shortlist+a=1+d=500` | `llm-mini-score-pilot+d=50` | `llm-mini-score-pilot+d=50+rrf-baseline+c=30` |
|---|---|---|---|
| keyword (nDCG / MRR) | 0.7188 / 0.900 | 0.7396 / 0.667 | 0.7358 / 0.850 |
| question (nDCG / MRR) | 0.7211 / 1.000 | 0.8276 / 0.733 | 0.7834 / 0.867 |
| paraphrase (nDCG / MRR) | 0.6575 / 0.450 | 0.7531 / 0.450 | 0.7139 / 0.600 |
| known_item (nDCG / MRR) | 0.6863 / 1.000 | 0.7008 / 0.900 | 0.7046 / 1.000 |

## Largest source-rank drops (safeguard vs baseline)

| Query | Type | Baseline | Top50 LLM | Safeguard |
|---|---|---|---|---|
| q-keyword-009 | keyword | 2 | 35 | 13 |
| q-keyword-079 | keyword | 1 | 15 | 4 |
| q-keyword-078 | keyword | 1 | 10 | 3 |
| q-question-095 | question | 1 | 6 | 3 |
| q-keyword-057 | keyword | 3 | 6 | 4 |
| q-keyword-085 | keyword | 4 | 5 | 5 |

## Accounting

- Reranker (new80): 80 requests, input/output/reasoning 1,343,080/20,720/0, $1.1005.
- Judge: 62 calls, 72,602 tokens, $0.0723.

## Cautions

- Dev queries only; settings were developed on dev, so scores are optimistic.
- Judge and reranker share a model family; possible same-family preference.
- No promotion without explicit approval.
