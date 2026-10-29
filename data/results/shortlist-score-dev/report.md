# Fixed-shortlist score ordering: bounded dev experiment

Score evidence improves ordering within the baseline top10 without sacrificing recall at10/20; MRR and known-item rank safety remain empirical.

4 prespecified settings, depths100/500. Rank evidence is fixed RRF55%/c30/depth100 divided by1/31; score evidence is max-normalized75% semantic. Combined = a*score + (1-a)*normalized_RRF. These are not probabilities. No query-type routing, source IDs, or labels are used in ranking. Shortlist mode only reorders baseline top10 and preserves the tail; it cannot introduce a paper or improve recall at10/20.

Controls exactly reproduce frozen runs. All rows use the same parent snapshot. Paired graded comparisons are withheld for incomplete top10s; source metrics remain valid. Intervals are exploratory after dev tuning, not adjusted for selection or multiple testing. No automatic promotion or API calls.

Missing judgments: **0**.

| System | nDCG10 | P10 | Judged10 | Source MRR10 | R10 | R20 | Screening |
|---|---|---|---|---|---|---|---|
| `fusion-rrf+w=0.55+d=100+c=30` | 0.7064 | 0.6890 | 1.0000 | 0.6459 | 0.8600 | 0.8900 | control |
| `score-max+w=0.75+d=500` | 0.7197 | 0.6970 | 1.0000 | 0.6916 | 0.8200 | 0.8400 | control |
| `fusion-shortlist+a=0.5+d=100` | 0.7070 | 0.6890 | 1.0000 | 0.6497 | 0.8600 | 0.8900 | not passed |
| `fusion-shortlist+a=1+d=100` | 0.7138 | 0.6890 | 1.0000 | 0.6736 | 0.8600 | 0.8900 | PASS |
| `fusion-shortlist+a=0.5+d=500` | 0.7071 | 0.6890 | 1.0000 | 0.6516 | 0.8600 | 0.8900 | not passed |
| `fusion-shortlist+a=1+d=500` | 0.7176 | 0.6890 | 1.0000 | 0.6967 | 0.8600 | 0.8900 | PASS |

## Screening rules (fixed before outcomes)

- All dev top10 positions judged in candidate and baseline
- Mean nDCG improves and paired bootstrap lower endpoint exceeds zero
- Source R@10 and R@20 at least baseline; known-item target ranks never worsen
- No query-type mean nDCG regression; grade0 first count does not increase

Per-query ranks, grades and score components: cases.json. All segment means, paired intervals and missing pairs: report.json. A failed screen is not proof a method is useless; it is a reason not to replace the balanced baseline under this conservative experiment policy.

## Screening outcomes

| System | Failed checks | Grade0 first | Lost / gained source top10 hits |
|---|---|---|---|
| `fusion-shortlist+a=0.5+d=100` | ndcg_positive_interval, no_segment_ndcg_regression, grade0_first_not_increased | 7 | 0 / 0 |
| `fusion-shortlist+a=1+d=100` | none | 5 | 0 / 0 |
| `fusion-shortlist+a=0.5+d=500` | ndcg_positive_interval, no_segment_ndcg_regression, grade0_first_not_increased | 7 | 0 / 0 |
| `fusion-shortlist+a=1+d=500` | none | 4 | 0 / 0 |

## Selection

Recommended dev candidate: `fusion-shortlist+a=1+d=500`.
Passing screening is not held-out confirmation or automatic promotion. Review individual losses and obtain a baseline decision before changing configuration.
