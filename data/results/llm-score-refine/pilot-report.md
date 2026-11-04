# Experiment E: top20 refinement (pilot stage)

Reference: `llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30` (Decision46). Primary re-scores its top20 0-10 (two passes averaged) and applies RRF c=30 with the Decision46 order; secondary: same responses, no RRF. Pilot gate only: a sanity screen, not evidence.

| System | nDCG@10 | pilot20 Δ | Source MRR@10 | R@1 | P@10 | Passes |
|---|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.6870 | -0.0595 [-0.0976, -0.0200] | 0.8375 | 80% | 0.675 | — |
| `llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30` | 0.7465 | — | 0.8625 | 85% | 0.750 | — |
| `llm-mini-refine20+d=20+avg2+rrf-d46+c=30` | 0.7885 | +0.0420 [+0.0146, +0.0690] | 0.8313 | 80% | 0.800 | no (pilot20_source_mrr) |
| `llm-mini-refine20+d=20+avg2` | 0.7907 | +0.0442 [+0.0097, +0.0792] | 0.7333 | 65% | 0.825 | no (pilot20_source_mrr) |

## nDCG@10 by query type (diagnostic only)

| System | keyword | question | paraphrase | known_item |
|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.7104 | 0.7132 | 0.6445 | 0.6800 |
| `llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30` | 0.7436 | 0.8101 | 0.7226 | 0.7099 |
| `llm-mini-refine20+d=20+avg2+rrf-d46+c=30` | 0.7827 | 0.8610 | 0.7870 | 0.7234 |
| `llm-mini-refine20+d=20+avg2` | 0.7903 | 0.8867 | 0.7910 | 0.6948 |

## Diagnostics

- 0-10 score histogram (all paper-passes): {'0': 131, '1': 187, '2': 92, '3': 64, '4': 101, '5': 75, '6': 50, '7': 37, '8': 42, '9': 8, '10': 13}.
- Pass agreement: 43% identical; mean gap 0.87 points.
- Grade-2 papers promoted into the top10 / dropped from it: `llm-mini-refine20+d=20+avg2+rrf-d46+c=30` +11 / -6; `llm-mini-refine20+d=20+avg2` +17 / -11.
- Grade-0 papers in the top10: `fusion-shortlist+a=1+d=500` 65, `llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30` 50, `llm-mini-refine20+d=20+avg2+rrf-d46+c=30` 40, `llm-mini-refine20+d=20+avg2` 35.

## Cost

- Refinement: 40 requests, $0.2291 (uncached prices).
- Judge: $0.0048.

## Cautions

- Dev only; the judge and reranker share a model family.
- The loss analysis that motivated this experiment read dev queries.
- Label overrides called "human" in older files are GPT-6 ASTRA reference grades; no labels here are human.
- Not promoted.
