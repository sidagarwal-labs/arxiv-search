# D47: where the remaining ranking loss sits

D47, 100 dev queries, frozen D47 pooled labels; no provider calls or test scoring

Sequential perfect reordering of the D47 top10, top20, top50; same global pooled-label ideal denominator and linear gains. Components telescope to 1 - actual. Unjudged candidates count as zero, not confirmed irrelevant.

| Ordering | Mean nDCG@10 |
|---|---:|
| actual | 0.7939 |
| oracle10 | 0.8394 |
| oracle20 | 0.9498 |
| oracle50 | 0.9803 |
| ideal | 1.0000 |

| Loss component | Mean [95% bootstrap CI] | Queries affected | Share of top50 gap |
|---|---:|---:|---:|
| ordering_top10 | 0.0455 [0.0370, 0.0548] | 90 | 24.4% |
| selection_11_20 | 0.1105 [0.0935, 0.1268] | 86 | 59.3% |
| screening_21_50 | 0.0305 [0.0228, 0.0390] | 42 | 16.3% |
| outside_top50 | 0.0197 [0.0116, 0.0293] | 23 | — |

Unjudged query-paper pairs in the top50: **2139**.
Keeping D47 rank 1 fixed reduces the top20 oracle by **0.0132** on average.

| D47 rank band | Grade 0 | Grade 1 | Grade 2 | Unjudged |
|---|---:|---:|---:|---:|
| top10 | 217 | 449 | 334 | 0 |
| ranks11_20 | 396 | 421 | 84 | 99 |
| ranks21_50 | 580 | 335 | 45 | 2040 |

## By query type

| Type | Actual | Ordering top10 | Selection 11–20 | Screening 21–50 | Outside top50 |
|---|---:|---:|---:|---:|---:|
| keyword | 0.7691 | 0.0517 | 0.1082 | 0.0485 | 0.0225 |
| known_item | 0.7593 | 0.0517 | 0.1245 | 0.0355 | 0.0290 |
| paraphrase | 0.8010 | 0.0420 | 0.1292 | 0.0195 | 0.0084 |
| question | 0.8462 | 0.0366 | 0.0800 | 0.0183 | 0.0189 |

## Largest known gaps

| Query | Type | Actual | Top50 oracle | Largest component |
|---|---|---:|---:|---|
| Ziaoddini music graph recommendation | known_item | 0.5027 | 1.0000 | selection_11_20 |
| llm synthetic slate preference | keyword | 0.4757 | 0.9394 | ordering_top10 |
| maximizing income for power conversion tools and cells by using actual device behavior in Nordic power exchanges | paraphrase | 0.5418 | 1.0000 | selection_11_20 |
| using a mix of slot-based training and preference optimization to spot political leaning in social posts | paraphrase | 0.5639 | 1.0000 | selection_11_20 |
| regional language social media | keyword | 0.5789 | 1.0000 | selection_11_20 |
| computational political bias wales | keyword | 0.6224 | 1.0000 | selection_11_20 |
| blocking fake info in external search results by checking how removing a page changes the answer | paraphrase | 0.6325 | 1.0000 | selection_11_20 |
| BL19 digital collection retrieval benchmark | keyword | 0.4698 | 0.8366 | selection_11_20 |
| van der Klis lorentz neural networks | known_item | 0.4646 | 0.8274 | screening_21_50 |
| how can a graph structure stop generative rerankers from producing repetitive item lists? | question | 0.6420 | 1.0000 | selection_11_20 |
| improving how ai follows complex rules by creating its own feedback without needing human labels | paraphrase | 0.6204 | 0.9682 | selection_11_20 |
| how can large language models actively gather information to improve product recommendations? | question | 0.6725 | 1.0000 | ordering_top10 |
| Feng coding agents sufficient evidence | known_item | 0.6731 | 1.0000 | selection_11_20 |
| Mathur rag policy qa | known_item | 0.6848 | 1.0000 | selection_11_20 |
| Zhou wind bridge forecasting | known_item | 0.6871 | 1.0000 | selection_11_20 |

## Limits

- Oracle bounds are label-informed diagnostics, not achievable system predictions.
- Partially judged top50 and pooled labels make the ceiling optimistic/incomplete.
- Bootstrap intervals describe dev-query variation, not unbiased generalization.
- Candidate inversions are not proof of label noise; no independent label audit performed.
- Pin penalty is an idealized bound, not a recommendation to remove the safeguard.
- Allocation is sequential/order-dependent: top10 ordering is credited first, then selection from top20, then top50. Selection increments include optimal new ordering.

Per-query counts, candidate inversions and input hashes: [report.json](report.json).
