# Mini LLM reranker pilot:20 queries, top10 versus top50

Separate pilot benchmark, not comparable to the100-query leaderboard. Planned20 frozen queries for baseline and both arms; five per segment. **Matched successful queries used below: 7/20.** Failed queries are excluded identically from both arms and baseline, with no silent fallback.
Completed queries per system: `{"fusion-shortlist+a=1+d=500": 20, "llm-mini-pilot+d=10": 16, "llm-mini-pilot+d=50": 7}`.
Model `gpt-5.4-mini-2026-03-17`; full title/authors/abstract; reasoning disabled; hash-shuffled candidates, no tools, no retries. No promotion or new judging.

| System | nDCG10 | P10 | Judged10 | Source MRR10 | R10 | R20 |
|---|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.7356 | 0.7000 | 1.0000 | 0.8571 | 0.8571 | 0.8571 |
| `llm-mini-pilot+d=10` | 0.7485 | 0.7000 | 1.0000 | 0.7857 | 0.8571 | 0.8571 |
| `llm-mini-pilot+d=50` | withheld | withheld | 0.7143 | 0.5952 | 0.8571 | 0.8571 |

Missing new top10 judgments: **20**. Incomplete graded scores in JSON are diagnostic only; paired intervals withheld. Adding labels may revise IDCG, so these are not bounds on final nDCG.

## Paired candidate minus pilot baseline

| Arm | nDCG delta [95% CI] | Source MRR delta [95% CI] |
|---|---|---|
| top10 | +0.0129 [-0.0246,+0.0604] | -0.0714 [-0.2143,+0.0000] |
| top50 | withheld | -0.2619 [-0.5000,+0.0000] |

## Segment results (matched successful queries)

| System | Segment | Queries | nDCG10 | Source MRR10 | R10 | R20 |
|---|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | keyword | 3 | 0.7845 | 1.0000 | 1.0000 | 1.0000 |
| `fusion-shortlist+a=1+d=500` | question | 0 | withheld | withheld | withheld | withheld |
| `fusion-shortlist+a=1+d=500` | paraphrase | 1 | 0.5258 | 0.0000 | 0.0000 | 0.0000 |
| `fusion-shortlist+a=1+d=500` | known_item | 3 | 0.7567 | 1.0000 | 1.0000 | 1.0000 |
| `llm-mini-pilot+d=10` | keyword | 3 | 0.7979 | 1.0000 | 1.0000 | 1.0000 |
| `llm-mini-pilot+d=10` | question | 0 | withheld | withheld | withheld | withheld |
| `llm-mini-pilot+d=10` | paraphrase | 1 | 0.6611 | 0.0000 | 0.0000 | 0.0000 |
| `llm-mini-pilot+d=10` | known_item | 3 | 0.7283 | 0.8333 | 1.0000 | 1.0000 |
| `llm-mini-pilot+d=50` | keyword | 3 | withheld | 0.5556 | 1.0000 | 1.0000 |
| `llm-mini-pilot+d=50` | question | 0 | withheld | withheld | withheld | withheld |
| `llm-mini-pilot+d=50` | paraphrase | 1 | withheld | 0.0000 | 0.0000 | 0.0000 |
| `llm-mini-pilot+d=50` | known_item | 3 | withheld | 0.8333 | 1.0000 | 1.0000 |

## Accounting and reproducibility

- New locally accounted cost: $0.375672; task cap $1.00. Standard uncached rates; not provider billing.
- Requests: 40; input/output tokens: 404,536/16,060; reasoning tokens: 0.
- Successful-response latency: `{"max_successful": 5.170331200002693, "mean_successful": 3.5807324695671685, "median_successful": 3.401110400009202, "total_successful": 82.35684680004488}`. Accounting retains failed-attempt latency too. Not production end-to-end search latency.
- Plans, input hashes, presentation order, response cache and usage are persisted. Replay must validate cached answers and make zero new calls.
- Frozen parent label bytes/human overrides preserved. No held-out queries sent.

## Known-item target changes

| Arm | Query | Source rank before -> after |
|---|---|---|
| `llm-mini-pilot+d=10` | q-known_item-042 | 1 -> 2 |
| `llm-mini-pilot+d=50` | q-known_item-042 | 1 -> 2 |

## Explicit failures (no retries)

| Arm | Query | Failure category |
|---|---|---|
| `llm-mini-pilot+d=10` | q-keyword-081 | output_not_retained |
| `llm-mini-pilot+d=10` | q-paraphrase-077 | valid_permutation_rejected_evidence |
| `llm-mini-pilot+d=10` | q-question-077 | valid_permutation_rejected_evidence |
| `llm-mini-pilot+d=10` | q-question-088 | valid_permutation_rejected_evidence |
| `llm-mini-pilot+d=50` | q-keyword-079 | valid_permutation_rejected_evidence |
| `llm-mini-pilot+d=50` | q-keyword-081 | valid_permutation_rejected_evidence |
| `llm-mini-pilot+d=50` | q-known_item-019 | invalid_permutation |
| `llm-mini-pilot+d=50` | q-known_item-031 | valid_permutation_rejected_evidence |
| `llm-mini-pilot+d=50` | q-paraphrase-020 | invalid_permutation |
| `llm-mini-pilot+d=50` | q-paraphrase-043 | invalid_permutation |
| `llm-mini-pilot+d=50` | q-paraphrase-063 | valid_permutation_rejected_evidence |
| `llm-mini-pilot+d=50` | q-paraphrase-077 | invalid_permutation |
| `llm-mini-pilot+d=50` | q-question-040 | invalid_permutation |
| `llm-mini-pilot+d=50` | q-question-056 | invalid_permutation |
| `llm-mini-pilot+d=50` | q-question-077 | invalid_permutation |
| `llm-mini-pilot+d=50` | q-question-088 | valid_permutation_rejected_evidence |
| `llm-mini-pilot+d=50` | q-question-095 | valid_permutation_rejected_evidence |

## Post-hoc ranking-only diagnostic

Post-hoc ranking-only diagnostic, NOT the strict primary pilot. Use only exact full permutations; ignore rejected evidence notes. Never repair missing/duplicate IDs, generate labels or change strict run files. Still success-selected; no promotion or generalized quality claim.

Additional cached exact permutations yield **12** matched queries for this secondary comparison. Strict acceptance/failure counts above do not change; details in `ranking-only-diagnostic.json`.

| System | Queries | nDCG10 | Source MRR10 | R10 | Judged10 |
|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 12 | 0.7219 | 0.9167 | 0.9167 | 1.0000 |
| `llm-mini-pilot+d=10` | 12 | 0.7438 | 0.8333 | 0.9167 | 1.0000 |
| `llm-mini-pilot+d=50` | 12 | withheld | 0.6508 | 0.9167 | 0.7333 |

## Interpretation limits

- Only20 already-examined dev queries; five per segment; exploratory.
- Failures are explicit, not replaced with baseline results. Matched successful queries are complete-case diagnostics, susceptible to failure-selection bias.
- Most evaluation labels use the same model family as the reranker.
- One frozen presentation order; no order-sensitivity or repeat runs.
- Unjudged new top10s require independent labels before comparable nDCG/P10.
- Reranker notes are not labels. Not a100-query leaderboard entry.
