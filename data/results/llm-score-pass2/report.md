# Two-pass score averaging (100 dev queries)

One change vs the reranking baseline: LLM scores are the mean of two byte-identical passes. Reference: `llm-mini-score-pilot+d=50+rrf-baseline+c=30`; its noise threshold (MDD) is 0.0090.

| System | nDCG@10 | Δ vs reference [95% CI] | pilot20 Δ | new80 Δ | Source MRR@10 | R@1 | Qualifies |
|---|---|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.7036 | -0.0485 [-0.0628, -0.0343] | -0.0386 | -0.0510 | 0.6967 | 61% | — |
| `llm-mini-score-pilot+d=50` | 0.7726 | +0.0205 [+0.0044, +0.0356] | +0.0213 | +0.0204 | 0.6775 | 57% | — |
| `llm-mini-score-pilot+d=50+rrf-baseline+c=30` | 0.7521 | — | — | — | 0.7197 | 64% | — |
| `llm-mini-score-pilot+d=50+avg2` | 0.7877 | +0.0356 [+0.0178, +0.0529] | +0.0411 | +0.0342 | 0.6863 | 57% | no (source_mrr) |
| `llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30` | 0.7684 | +0.0163 [+0.0094, +0.0240] | +0.0218 | +0.0149 | 0.7232 | 63% | **yes** |

## nDCG@10 by query type (diagnostic only)

| System | keyword | question | paraphrase | known_item |
|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.7211 | 0.7084 | 0.6721 | 0.7127 |
| `llm-mini-score-pilot+d=50` | 0.7405 | 0.8353 | 0.7646 | 0.7502 |
| `llm-mini-score-pilot+d=50+rrf-baseline+c=30` | 0.7490 | 0.7780 | 0.7470 | 0.7345 |
| `llm-mini-score-pilot+d=50+avg2` | 0.7548 | 0.8680 | 0.7786 | 0.7494 |
| `llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30` | 0.7592 | 0.7995 | 0.7689 | 0.7460 |

## Run-to-run noise, 100 queries (pass A vs pass B, single pass)

- LLM scores identical in 3510/5000 pairs (70.2%); changed by 2+: 100; mean absolute change 0.319.

| System | Mean abs per-query nDCG change | Est. SD of 100-q mean | Single-pass MDD | Avg-of-2 MDD (if passes independent) | Unjudged pass-B pairs |
|---|---|---|---|---|---|
| top50 | 0.0639 | 0.0062 | 0.0172 | 0.0121 | 25 |
| safeguard | 0.0362 | 0.0038 | 0.0106 | 0.0075 | 3 |

## Cost

- New pass-B requests: 80; $1.1006.
- Two passes cost ≈ $0.0275 per uncached query (2x).
- Judge: $0.0437.

## Cautions

- Dev only; judge and reranker share a model family.
- Pass A for the pilot queries was sent on an earlier day than pass B.
- Not promoted.
