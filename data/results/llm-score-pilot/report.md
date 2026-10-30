# Fixed-key mini reranker v2: same20-query pilot

Model `gpt-5.4-mini-2026-03-17`; reasoning disabled; all title/authors/abstract text preserved. One required integer0-4 per candidate ID, no generated permutations or explanations. Descending score with approved-baseline order for ties. No retries, new labels or promotion.
Matched queries: **20/20**. Failures, if any, are excluded identically from both arms and baseline, never replaced with fallback rankings. This is separate from the100-query leaderboard.

| System | nDCG10 | P10 | Judged10 | Source MRR10 | R10 | R20 |
|---|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.7055 | 0.6750 | 1.0000 | 0.8375 | 0.9000 | 0.9000 |
| `llm-mini-score-pilot+d=10` | 0.7194 | 0.6750 | 1.0000 | 0.8417 | 0.9000 | 0.9000 |
| `llm-mini-score-pilot+d=50` | withheld | withheld | 0.8300 | 0.6875 | 0.8500 | 0.9000 |

Missing new top10 judgments: **34**. Incomplete JSON scores are diagnostic only, not bounds on future nDCG; paired graded comparisons are withheld. Rejudging can change IDCG.

## Paired versus baseline

| Arm | nDCG delta [95% CI] | Source MRR delta [95% CI] |
|---|---|---|
| top10 | +0.0139 [+0.0003,+0.0278] | +0.0042 [-0.1168,+0.1169] |
| top50 | withheld | -0.1500 [-0.3083,+0.0000] |

## Segment results

| System | Segment | Queries | nDCG10 | Source MRR10 | R10 | R20 |
|---|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | keyword | 5 | 0.7255 | 0.9000 | 1.0000 | 1.0000 |
| `fusion-shortlist+a=1+d=500` | question | 5 | 0.7463 | 1.0000 | 1.0000 | 1.0000 |
| `fusion-shortlist+a=1+d=500` | paraphrase | 5 | 0.6639 | 0.4500 | 0.6000 | 0.6000 |
| `fusion-shortlist+a=1+d=500` | known_item | 5 | 0.6863 | 1.0000 | 1.0000 | 1.0000 |
| `llm-mini-score-pilot+d=10` | keyword | 5 | 0.7561 | 0.7667 | 1.0000 | 1.0000 |
| `llm-mini-score-pilot+d=10` | question | 5 | 0.7584 | 1.0000 | 1.0000 | 1.0000 |
| `llm-mini-score-pilot+d=10` | paraphrase | 5 | 0.6858 | 0.6000 | 0.6000 | 0.6000 |
| `llm-mini-score-pilot+d=10` | known_item | 5 | 0.6770 | 1.0000 | 1.0000 | 1.0000 |
| `llm-mini-score-pilot+d=50` | keyword | 5 | withheld | 0.6667 | 0.8000 | 1.0000 |
| `llm-mini-score-pilot+d=50` | question | 5 | withheld | 0.7333 | 1.0000 | 1.0000 |
| `llm-mini-score-pilot+d=50` | paraphrase | 5 | withheld | 0.4500 | 0.6000 | 0.6000 |
| `llm-mini-score-pilot+d=50` | known_item | 5 | withheld | 0.9000 | 1.0000 | 1.0000 |

## Accounting and reliability

- New v2 requests: 40; completed: `{"fusion-shortlist+a=1+d=500": 20, "llm-mini-score-pilot+d=10": 20, "llm-mini-score-pilot+d=50": 20}`.
- New input/output/reasoning tokens: 405,336/6,360/0.
- New local cost: $0.332622; combined v1+v2 $0.708294 against the same$1.00 ceiling.
- Shared accounted tokens at completion: 2,244,267. Sequential API-time sum: 83.1s.
- No reset, retry, silent paid cache repair or reranker-generated evaluation labels.

## Known-item source changes

| Arm | Query | Source rank before -> after |
|---|---|---|
| `llm-mini-score-pilot+d=50` | q-known_item-042 | 1 -> 2 |

## Explicit failures

{"llm-mini-score-pilot+d=10": {}, "llm-mini-score-pilot+d=50": {}}

## Interpretation

- 20 previously examined dev queries; five per segment; exploratory only.
- Evaluation judge and reranker share a model family; no independent validation.
- Missing selected-result grades withhold comparable nDCG/P10; scores are not grades.
- Fixed0-4 usefulness scores and baseline tie-breaking change scoring as well as output format.
- v1 comparisons use only its successful queries; this is a selected subset, not a fresh test.
- Exact paired v1 comparisons and score-tie counts are in `report.json`; v1's primary artifacts remain unchanged.
