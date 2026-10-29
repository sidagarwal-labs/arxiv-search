# Rank/score interpolation: bounded dev experiment

Interpolating rank evidence with max-score fusion reduces weak-overlap boosting while retaining graded-relevance gains.

6 prespecified settings, depths100/500. Rank evidence is fixed RRF55%/c30/depth100 divided by1/31; score evidence is max-normalized75% semantic. Combined = a*score + (1-a)*normalized_RRF. These are not probabilities. No query-type routing, source IDs, or labels are used in ranking. Interpolation reranks the union of rank and score candidates.

Controls exactly reproduce frozen runs. All rows use the same parent snapshot. Paired graded comparisons are withheld for incomplete top10s; source metrics remain valid. Intervals are exploratory after dev tuning, not adjusted for selection or multiple testing. No automatic promotion or API calls.

Missing judgments: **1**.

| System | nDCG10 | P10 | Judged10 | Source MRR10 | R10 | R20 | Screening |
|---|---|---|---|---|---|---|---|
| `fusion-rrf+w=0.55+d=100+c=30` | 0.7064 | 0.6890 | 1.0000 | 0.6459 | 0.8600 | 0.8900 | control |
| `score-max+w=0.75+d=500` | 0.7197 | 0.6970 | 1.0000 | 0.6916 | 0.8200 | 0.8400 | control |
| `fusion-rankscore+a=0.25+d=100` | 0.7071 | 0.6920 | 1.0000 | 0.6459 | 0.8500 | 0.8800 | not passed |
| `fusion-rankscore+a=0.5+d=100` | 0.7066 | 0.6910 | 1.0000 | 0.6485 | 0.8500 | 0.8800 | not passed |
| `fusion-rankscore+a=0.75+d=100` | 0.7108 | 0.6910 | 1.0000 | 0.6648 | 0.8400 | 0.8700 | not passed |
| `fusion-rankscore+a=0.25+d=500` | 0.7050 | 0.6900 | 1.0000 | 0.6462 | 0.8500 | 0.8800 | not passed |
| `fusion-rankscore+a=0.5+d=500` | 0.7067 | 0.6900 | 1.0000 | 0.6502 | 0.8500 | 0.8700 | not passed |
| `fusion-rankscore+a=0.75+d=500` | 0.7168 | 0.6960 | 0.9990 | 0.6785 | 0.8400 | 0.8600 | not passed; PROVISIONAL |

## Screening rules (fixed before outcomes)

- All dev top10 positions judged in candidate and baseline
- Mean nDCG improves and paired bootstrap lower endpoint exceeds zero
- Source R@10 and R@20 at least baseline; known-item target ranks never worsen
- No query-type mean nDCG regression; grade0 first count does not increase

Per-query ranks, grades and score components: cases.json. All segment means, paired intervals and missing pairs: report.json. A failed screen is not proof a method is useless; it is a reason not to replace the balanced baseline under this conservative experiment policy.

## Screening outcomes

| System | Failed checks | Grade0 first | Lost / gained source top10 hits |
|---|---|---|---|
| `fusion-rankscore+a=0.25+d=100` | ndcg_positive_interval, source_recall@10, source_recall@20, no_segment_ndcg_regression, grade0_first_not_increased | 7 | 1 / 0 |
| `fusion-rankscore+a=0.5+d=100` | ndcg_positive_interval, source_recall@10, source_recall@20, no_segment_ndcg_regression, grade0_first_not_increased | 7 | 1 / 0 |
| `fusion-rankscore+a=0.75+d=100` | ndcg_positive_interval, source_recall@10, source_recall@20, no_segment_ndcg_regression | 6 | 2 / 0 |
| `fusion-rankscore+a=0.25+d=500` | ndcg_positive_interval, source_recall@10, source_recall@20, no_segment_ndcg_regression, grade0_first_not_increased | 7 | 1 / 0 |
| `fusion-rankscore+a=0.5+d=500` | ndcg_positive_interval, source_recall@10, source_recall@20, no_segment_ndcg_regression, grade0_first_not_increased | 7 | 1 / 0 |
| `fusion-rankscore+a=0.75+d=500` | complete_top10, ndcg_positive_interval, source_recall@10, source_recall@20, no_segment_ndcg_regression | 5 | 2 / 0 |

## Selection

No setting passes the fixed screening rules; retain the working baseline.
Passing screening is not held-out confirmation or automatic promotion. Review individual losses and obtain a baseline decision before changing configuration.
