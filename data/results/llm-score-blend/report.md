# Score-aware blend: LLM score + retrieval-rank prior (no reranker calls)

Rule: `LLM score + beta*(30+1)/(30+retrieval rank)` over the top 50; ties keep retrieval order; betas [2, 3, 4] fixed before scoring. Reference: `llm-mini-score-pilot+d=50+rrf-baseline+c=30` (reranking baseline). Noise threshold (MDD): 0.0090.

| System | nDCG@10 | Δ vs reference [95% CI] | pilot20 Δ | new80 Δ | Source MRR@10 | R@1 | judged@10 | Qualifies |
|---|---|---|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.7092 | -0.0491 [-0.0633, -0.0347] | -0.0385 | -0.0518 | 0.6967 | 61% | 1.000 | — |
| `llm-mini-score-pilot+d=50` | 0.7789 | +0.0206 [+0.0044, +0.0358] | +0.0208 | +0.0205 | 0.6775 | 57% | 1.000 | — |
| `llm-mini-score-pilot+d=50+rrf-baseline+c=30` | 0.7583 | — | — | — | 0.7197 | 64% | 1.000 | — |
| `llm-mini-score-pilot+d=50+blend-rank-prior+b=2+c=30` | 0.7804 | +0.0221 [+0.0069, +0.0370] | +0.0205 | +0.0225 | 0.6860 | 58% | 1.000 | no (source_mrr) |
| `llm-mini-score-pilot+d=50+blend-rank-prior+b=3+c=30` | 0.7782 | +0.0199 [+0.0069, +0.0322] | +0.0158 | +0.0209 | 0.6966 | 59% | 1.000 | no (source_mrr) |
| `llm-mini-score-pilot+d=50+blend-rank-prior+b=4+c=30` | 0.7702 | +0.0119 [+0.0010, +0.0231] | +0.0121 | +0.0118 | 0.7023 | 59% | 1.000 | **yes** |

## nDCG@10 by query type (diagnostic only; the rule has no type input)

| System | keyword | question | paraphrase | known_item |
|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.7318 | 0.7150 | 0.6759 | 0.7140 |
| `llm-mini-score-pilot+d=50` | 0.7516 | 0.8432 | 0.7693 | 0.7515 |
| `llm-mini-score-pilot+d=50+rrf-baseline+c=30` | 0.7604 | 0.7854 | 0.7517 | 0.7357 |
| `llm-mini-score-pilot+d=50+blend-rank-prior+b=2+c=30` | 0.7545 | 0.8443 | 0.7726 | 0.7503 |
| `llm-mini-score-pilot+d=50+blend-rank-prior+b=3+c=30` | 0.7594 | 0.8360 | 0.7722 | 0.7452 |
| `llm-mini-score-pilot+d=50+blend-rank-prior+b=4+c=30` | 0.7606 | 0.8230 | 0.7590 | 0.7382 |

Selected: **llm-mini-score-pilot+d=50+blend-rank-prior+b=4+c=30**. Not promoted.

## Cautions

- Three configs chosen on the same 100 dev queries; the winner's gain is optimistic.
- One cached LLM pass; run-to-run noise applies to every blend.
- Judge and reranker share a model family.
- Judge spend: $0.0000.
