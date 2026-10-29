# OpenAI field-aware hybrid (cached follow-up)

Six fixed settings: concat control, abstract-only,10% title, 25% title control, and25% title anchored50/75% to concat. Scoring recipe: semantic = a*concat + (1-a)*(t*title+(1-t)*abstract); then 25% candidate100-max BM25 +75% candidate100-max semantic. Stable baseline ties; reorder baseline top10 only, preserve positions11+. No query routing. Exactly the same OpenAI-large model,3072 dimensions and cached query vectors. Body means abstract. Candidate-only; no new full-corpus retrieval. The approved Decision36 baseline remains unchanged.

Embedding workload/cost: `{"judge_calls": 0, "new_accounted_usd": 0.0, "new_embedding_api_calls": 0}`

Unjudged new top10 pairs: **0**. No judging calls. Incomplete nDCG/P10 are diagnostic, not comparable winner evidence; graded paired intervals withheld. Adding labels can revise ideal DCG. Source metrics remain complete.

| System | nDCG10 | P10 | Judged10 | Source MRR10 | R10 | R20 | Coverage |
|---|---|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.7176 | 0.6890 | 1.0000 | 0.6967 | 0.8600 | 0.8900 | complete |
| `oai-field-recovery+text=abstract+anchor=0+d=10` | 0.7210 | 0.6890 | 1.0000 | 0.6799 | 0.8600 | 0.8900 | complete |
| `oai-field-recovery+text=concat+anchor=1+d=10` | 0.7175 | 0.6890 | 1.0000 | 0.6967 | 0.8600 | 0.8900 | complete |
| `oai-field-recovery+text=title10+anchor=0+d=10` | 0.7214 | 0.6890 | 1.0000 | 0.6985 | 0.8600 | 0.8900 | complete |
| `oai-field-recovery+text=title25+anchor=0+d=10` | 0.7204 | 0.6890 | 1.0000 | 0.7047 | 0.8600 | 0.8900 | complete |
| `oai-field-recovery+text=title25+anchor=0.5+d=10` | 0.7202 | 0.6890 | 1.0000 | 0.6940 | 0.8600 | 0.8900 | complete |
| `oai-field-recovery+text=title25+anchor=0.75+d=10` | 0.7191 | 0.6890 | 1.0000 | 0.7036 | 0.8600 | 0.8900 | complete |

## Paired nDCG comparisons

| Setting | Versus baseline delta [95% CI] | Versus same-depth concat [95% CI] |
|---|---|---|
| `oai-field-recovery+text=concat+anchor=1+d=10` | -0.0001 [-0.0002,+0.0000] | +0.0000 [+0.0000,+0.0000] |
| `oai-field-recovery+text=abstract+anchor=0+d=10` | +0.0034 [-0.0024,+0.0094] | +0.0035 [-0.0023,+0.0094] |
| `oai-field-recovery+text=title10+anchor=0+d=10` | +0.0039 [-0.0008,+0.0092] | +0.0039 [-0.0008,+0.0092] |
| `oai-field-recovery+text=title25+anchor=0+d=10` | +0.0028 [-0.0019,+0.0078] | +0.0029 [-0.0019,+0.0078] |
| `oai-field-recovery+text=title25+anchor=0.5+d=10` | +0.0026 [-0.0002,+0.0058] | +0.0027 [-0.0002,+0.0058] |
| `oai-field-recovery+text=title25+anchor=0.75+d=10` | +0.0015 [-0.0013,+0.0044] | +0.0016 [-0.0012,+0.0044] |

## Segments

| Setting | Segment | nDCG10 (diagnostic if incomplete) | Source MRR10 | R10 | R20 |
|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | keyword | 0.7385 | 0.7202 | 0.9600 | 0.9600 |
| `fusion-shortlist+a=1+d=500` | question | 0.7277 | 0.5883 | 0.7600 | 0.8000 |
| `fusion-shortlist+a=1+d=500` | paraphrase | 0.6858 | 0.4984 | 0.7200 | 0.8000 |
| `fusion-shortlist+a=1+d=500` | known_item | 0.7183 | 0.9800 | 1.0000 | 1.0000 |
| `oai-field-recovery+text=concat+anchor=1+d=10` | keyword | 0.7385 | 0.7202 | 0.9600 | 0.9600 |
| `oai-field-recovery+text=concat+anchor=1+d=10` | question | 0.7277 | 0.5883 | 0.7600 | 0.8000 |
| `oai-field-recovery+text=concat+anchor=1+d=10` | paraphrase | 0.6855 | 0.4984 | 0.7200 | 0.8000 |
| `oai-field-recovery+text=concat+anchor=1+d=10` | known_item | 0.7183 | 0.9800 | 1.0000 | 1.0000 |
| `oai-field-recovery+text=abstract+anchor=0+d=10` | keyword | 0.7392 | 0.6811 | 0.9600 | 0.9600 |
| `oai-field-recovery+text=abstract+anchor=0+d=10` | question | 0.7260 | 0.6094 | 0.7600 | 0.8000 |
| `oai-field-recovery+text=abstract+anchor=0+d=10` | paraphrase | 0.6955 | 0.4490 | 0.7200 | 0.8000 |
| `oai-field-recovery+text=abstract+anchor=0+d=10` | known_item | 0.7232 | 0.9800 | 1.0000 | 1.0000 |
| `oai-field-recovery+text=title10+anchor=0+d=10` | keyword | 0.7390 | 0.7211 | 0.9600 | 0.9600 |
| `oai-field-recovery+text=title10+anchor=0+d=10` | question | 0.7258 | 0.6044 | 0.7600 | 0.8000 |
| `oai-field-recovery+text=title10+anchor=0+d=10` | paraphrase | 0.6965 | 0.4884 | 0.7200 | 0.8000 |
| `oai-field-recovery+text=title10+anchor=0+d=10` | known_item | 0.7244 | 0.9800 | 1.0000 | 1.0000 |
| `oai-field-recovery+text=title25+anchor=0+d=10` | keyword | 0.7449 | 0.7461 | 0.9600 | 0.9600 |
| `oai-field-recovery+text=title25+anchor=0+d=10` | question | 0.7317 | 0.6250 | 0.7600 | 0.8000 |
| `oai-field-recovery+text=title25+anchor=0+d=10` | paraphrase | 0.6811 | 0.4675 | 0.7200 | 0.8000 |
| `oai-field-recovery+text=title25+anchor=0+d=10` | known_item | 0.7237 | 0.9800 | 1.0000 | 1.0000 |
| `oai-field-recovery+text=title25+anchor=0.5+d=10` | keyword | 0.7410 | 0.7287 | 0.9600 | 0.9600 |
| `oai-field-recovery+text=title25+anchor=0.5+d=10` | question | 0.7301 | 0.5650 | 0.7600 | 0.8000 |
| `oai-field-recovery+text=title25+anchor=0.5+d=10` | paraphrase | 0.6866 | 0.5022 | 0.7200 | 0.8000 |
| `oai-field-recovery+text=title25+anchor=0.5+d=10` | known_item | 0.7232 | 0.9800 | 1.0000 | 1.0000 |
| `oai-field-recovery+text=title25+anchor=0.75+d=10` | keyword | 0.7397 | 0.7302 | 0.9600 | 0.9600 |
| `oai-field-recovery+text=title25+anchor=0.75+d=10` | question | 0.7271 | 0.5683 | 0.7600 | 0.8000 |
| `oai-field-recovery+text=title25+anchor=0.75+d=10` | paraphrase | 0.6874 | 0.5360 | 0.7200 | 0.8000 |
| `oai-field-recovery+text=title25+anchor=0.75+d=10` | known_item | 0.7221 | 0.9800 | 1.0000 | 1.0000 |

## Reproducibility and cautions

- Cached scores only; no embedding/judging API execution path.
- Parent embeddings use the shared $1.25 lifetime ledger plus $0.30 task ceiling. No automatic retries; unknown outcomes retain reservations.
- Reported cost is local accounting at the stored $0.13/M token price, not a guarantee about provider billing/free credits.
- Input/label hashes and plan frozen; cached document vectors bind exact text, model and dimensions. Query/concat caches are read-only; missing cache aborts.
- `../openai-field-dev/raw-field-scores.json`: frozen parent cosine signals; `cases.json`: wins/losses.
- `report.json`: screening, paired source intervals and same-model controls.
- Held-out300 untouched; human overrides preserved. Exploratory dev comparisons are not corrected for repeated selection or multiple testing.

## Recovery safety versus both references

Paraphrase nDCG/source MRR must reach baseline. Other segment nDCG must reach both references, and source MRR must reach baseline. These are observed-mean screens, not equivalence tests. No automatic promotion.

| Setting | Recovery screen | Baseline promotion screen |
|---|---|---|
| `oai-field-recovery+text=concat+anchor=1+d=10` | False | False |
| `oai-field-recovery+text=abstract+anchor=0+d=10` | False | False |
| `oai-field-recovery+text=title10+anchor=0+d=10` | False | False |
| `oai-field-recovery+text=title25+anchor=0+d=10` | False | False |
| `oai-field-recovery+text=title25+anchor=0.5+d=10` | False | False |
| `oai-field-recovery+text=title25+anchor=0.75+d=10` | False | False |
