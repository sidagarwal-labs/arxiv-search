# Experiment E2: top20 refinement keeping the Decision46 rank 1

System `llm-mini-refine20+d=20+avg2+rrf-d46+c=30+pin1-d46` vs `llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30` (Decision46). Decision scope: new80 (queries never scored before the plan was frozen). Noise threshold (MDD): 0.0106.

**Qualifies: yes** (fully_judged_top10: True, ndcg_gain_beyond_noise: True, source_mrr: True). Not promoted.

## new80 (decision)

| System | nDCG@10 | Δ vs D46 [95% CI] | Source MRR@10 | R@1 | P@10 |
|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.7041 | -0.0658 [-0.0827, -0.0473] | 0.6615 | 56% | 0.693 |
| `llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30` | 0.7699 | — | 0.6884 | 57% | 0.751 |
| `llm-mini-refine20+d=20+avg2+rrf-d46+c=30` | 0.7967 | +0.0268 [+0.0127, +0.0407] | 0.7550 | 66% | 0.779 |
| `llm-mini-refine20+d=20+avg2` | 0.7965 | +0.0266 [+0.0062, +0.0465] | 0.7876 | 71% | 0.782 |
| `llm-mini-refine20+d=20+avg2+rrf-d46+c=30+pin1-d46` | 0.7969 | +0.0270 [+0.0138, +0.0398] | 0.7086 | 57% | 0.779 |

## pilot20 (diagnostic)

| System | nDCG@10 | Δ vs D46 [95% CI] | Source MRR@10 | R@1 | P@10 |
|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.6870 | -0.0595 [-0.0976, -0.0200] | 0.8375 | 80% | 0.675 |
| `llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30` | 0.7465 | — | 0.8625 | 85% | 0.750 |
| `llm-mini-refine20+d=20+avg2+rrf-d46+c=30` | 0.7885 | +0.0420 [+0.0146, +0.0690] | 0.8313 | 80% | 0.800 |
| `llm-mini-refine20+d=20+avg2` | 0.7907 | +0.0442 [+0.0097, +0.0792] | 0.7333 | 65% | 0.825 |
| `llm-mini-refine20+d=20+avg2+rrf-d46+c=30+pin1-d46` | 0.7818 | +0.0353 [+0.0119, +0.0597] | 0.8562 | 85% | 0.800 |

## all100 (diagnostic)

| System | nDCG@10 | Δ vs D46 [95% CI] | Source MRR@10 | R@1 | P@10 |
|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.7007 | -0.0645 [-0.0808, -0.0474] | 0.6967 | 61% | 0.689 |
| `llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30` | 0.7652 | — | 0.7232 | 63% | 0.751 |
| `llm-mini-refine20+d=20+avg2+rrf-d46+c=30` | 0.7951 | +0.0299 [+0.0172, +0.0414] | 0.7703 | 69% | 0.783 |
| `llm-mini-refine20+d=20+avg2` | 0.7953 | +0.0301 [+0.0132, +0.0472] | 0.7768 | 70% | 0.791 |
| `llm-mini-refine20+d=20+avg2+rrf-d46+c=30+pin1-d46` | 0.7939 | +0.0287 [+0.0166, +0.0394] | 0.7381 | 63% | 0.783 |

## Cost

- Refinement ledger (E and E2 share it): $1.1409.
- Judge: $0.0259.

## Cautions

- Dev only; the judge and reranker share a model family.
- The pin rule was designed on pilot20 after seeing E's pilot; only new80 decides.
- Not promoted; promotion needs the owner's approval.
