# Repeatability: identical top50 reranker requests sent twice

The 20 pilot queries' v2 top50 payloads were re-sent byte-for-byte. Run A is the cached v2 response, run B the repeat. No judge calls; run-B top10 papers without a grade (**11**) are bounded as grade 0 and grade 2.

## LLM score agreement (20 queries x 50 papers)

- Identical score: **665/1000** (66.5%); changed by 1: 325; by 2+: 10.
- Mean absolute change 0.345 points (0-4 scale); mean signed change +0.091.

## Ranking and metric stability

| System | Median top10 overlap | Min | Identical top10 | Identical order | nDCG10 A -> B (unjudged=0) | (unjudged=2) | Mean abs query nDCG change | Source MRR A -> B | Source ranks changed |
|---|---|---|---|---|---|---|---|---|---|
| `llm-mini-score-pilot+d=50` | 7/10 | 5 | 2/20 | 1/20 | 0.7553 -> 0.7414 | 0.7360 -> 0.7757 | 0.0605 | 0.6875 -> 0.7333 | 5 |
| `llm-mini-score-pilot+d=50+rrf-baseline+c=30` | 9/10 | 6 | 3/20 | 2/20 | 0.7344 -> 0.7480 | 0.7155 -> 0.7360 | 0.0324 | 0.8292 -> 0.8625 | 1 |

| System | SD of per-query nDCG change | Estimated run-to-run SD of a 100-query mean |
|---|---|---|
| `llm-mini-score-pilot+d=50` | 0.0896 | 0.0063 |
| `llm-mini-score-pilot+d=50+rrf-baseline+c=30` | 0.0461 | 0.0033 |

## Source rank changes

| System | Query | Run A | Run B |
|---|---|---|---|
| `llm-mini-score-pilot+d=50` | q-keyword-079 | 15 | 16 |
| `llm-mini-score-pilot+d=50` | q-paraphrase-020 | 4 | 2 |
| `llm-mini-score-pilot+d=50` | q-paraphrase-043 | 1 | 3 |
| `llm-mini-score-pilot+d=50` | q-question-088 | 2 | 1 |
| `llm-mini-score-pilot+d=50` | q-question-095 | 6 | 1 |
| `llm-mini-score-pilot+d=50+rrf-baseline+c=30` | q-question-095 | 3 | 1 |

## Pre-registered stability guide

- Safeguard mean nDCG@10 change (worst bound) 0.0205 vs <= 0.01: **fail**.
- Safeguard median top10 overlap >= 8/10: **pass**.

## Accounting

- 20 requests; input/output tokens 334,739/5,180; $0.2744.

## Cautions

- One repeat of 20 queries; the 100-query noise estimate is an extrapolation.
- Run A was sent on an earlier day; provider-side changes cannot be ruled out.
- Same-family judge caveat unchanged; no promotion.
