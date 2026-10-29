# OpenAI field-aware hybrid (cached follow-up)

Eight prespecified settings: concatenated control and separate25/50/75% title at baseline prefixes10/100. Scoring recipe: 25% candidate-max-normalized original BM25 (including authors/title2x) +75% candidate-max-normalized semantic score, where semantic is concat cosine or t*title_cosine+(1-t)*abstract_cosine. Same candidate100 normalization for every setting, fixed weights, baseline ties. Reorder prefixes10/100. Exactly the same OpenAI-large model,3072 dimensions and cached query vectors. Body means abstract. Candidate-only; no new full-corpus retrieval. The approved Decision36 baseline remains unchanged.

Embedding workload/cost: `{"judge_calls": 0, "new_accounted_usd": 0.0, "new_embedding_api_calls": 0, "parent_embedding_accounted_usd": 0.2706548, "source": "Existing frozen OpenAI field cosine and lexical score caches only"}`

Unjudged new top10 pairs: **141**. No judging calls. Incomplete nDCG/P10 are diagnostic, not comparable winner evidence; graded paired intervals withheld. Adding labels can revise ideal DCG. Source metrics remain complete.

| System | nDCG10 | P10 | Judged10 | Source MRR10 | R10 | R20 | Coverage |
|---|---|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.7176 | 0.6890 | 1.0000 | 0.6967 | 0.8600 | 0.8900 | complete |
| `oai-field-hybrid+text=concat+d=10` | 0.7175 | 0.6890 | 1.0000 | 0.6967 | 0.8600 | 0.8900 | complete |
| `oai-field-hybrid+text=concat+d=100` | 0.7192 | 0.6970 | 1.0000 | 0.6916 | 0.8200 | 0.8400 | complete |
| `oai-field-hybrid+text=title25+d=10` | 0.7204 | 0.6890 | 1.0000 | 0.7047 | 0.8600 | 0.8900 | complete |
| `oai-field-hybrid+text=title25+d=100` | 0.7184 | 0.6870 | 0.9620 | 0.7012 | 0.8300 | 0.8400 | PROVISIONAL |
| `oai-field-hybrid+text=title50+d=10` | 0.7126 | 0.6890 | 1.0000 | 0.6789 | 0.8600 | 0.8900 | complete |
| `oai-field-hybrid+text=title50+d=100` | 0.6935 | 0.6650 | 0.9370 | 0.6768 | 0.8200 | 0.8400 | PROVISIONAL |
| `oai-field-hybrid+text=title75+d=10` | 0.7025 | 0.6890 | 1.0000 | 0.6551 | 0.8600 | 0.8900 | complete |
| `oai-field-hybrid+text=title75+d=100` | 0.6533 | 0.6150 | 0.8840 | 0.6563 | 0.8100 | 0.8200 | PROVISIONAL |

## Paired nDCG comparisons

| Setting | Versus baseline delta [95% CI] | Versus same-depth concat [95% CI] |
|---|---|---|
| `oai-field-hybrid+text=concat+d=10` | -0.0001 [-0.0002,+0.0000] | +0.0000 [+0.0000,+0.0000] |
| `oai-field-hybrid+text=title25+d=10` | +0.0028 [-0.0019,+0.0078] | +0.0029 [-0.0019,+0.0078] |
| `oai-field-hybrid+text=title50+d=10` | -0.0050 [-0.0141,+0.0033] | -0.0049 [-0.0140,+0.0034] |
| `oai-field-hybrid+text=title75+d=10` | -0.0150 [-0.0271,-0.0041] | -0.0150 [-0.0271,-0.0041] |
| `oai-field-hybrid+text=concat+d=100` | +0.0016 [-0.0078,+0.0117] | +0.0000 [+0.0000,+0.0000] |
| `oai-field-hybrid+text=title25+d=100` | withheld | withheld |
| `oai-field-hybrid+text=title50+d=100` | withheld | withheld |
| `oai-field-hybrid+text=title75+d=100` | withheld | withheld |

## Segments

| Setting | Segment | nDCG10 (diagnostic if incomplete) | Source MRR10 | R10 | R20 |
|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | keyword | 0.7385 | 0.7202 | 0.9600 | 0.9600 |
| `fusion-shortlist+a=1+d=500` | question | 0.7277 | 0.5883 | 0.7600 | 0.8000 |
| `fusion-shortlist+a=1+d=500` | paraphrase | 0.6858 | 0.4984 | 0.7200 | 0.8000 |
| `fusion-shortlist+a=1+d=500` | known_item | 0.7183 | 0.9800 | 1.0000 | 1.0000 |
| `oai-field-hybrid+text=concat+d=10` | keyword | 0.7385 | 0.7202 | 0.9600 | 0.9600 |
| `oai-field-hybrid+text=concat+d=10` | question | 0.7277 | 0.5883 | 0.7600 | 0.8000 |
| `oai-field-hybrid+text=concat+d=10` | paraphrase | 0.6855 | 0.4984 | 0.7200 | 0.8000 |
| `oai-field-hybrid+text=concat+d=10` | known_item | 0.7183 | 0.9800 | 1.0000 | 1.0000 |
| `oai-field-hybrid+text=title25+d=10` | keyword | 0.7449 | 0.7461 | 0.9600 | 0.9600 |
| `oai-field-hybrid+text=title25+d=10` | question | 0.7317 | 0.6250 | 0.7600 | 0.8000 |
| `oai-field-hybrid+text=title25+d=10` | paraphrase | 0.6811 | 0.4675 | 0.7200 | 0.8000 |
| `oai-field-hybrid+text=title25+d=10` | known_item | 0.7237 | 0.9800 | 1.0000 | 1.0000 |
| `oai-field-hybrid+text=title50+d=10` | keyword | 0.7493 | 0.7294 | 0.9600 | 0.9600 |
| `oai-field-hybrid+text=title50+d=10` | question | 0.7230 | 0.5717 | 0.7600 | 0.8000 |
| `oai-field-hybrid+text=title50+d=10` | paraphrase | 0.6587 | 0.4344 | 0.7200 | 0.8000 |
| `oai-field-hybrid+text=title50+d=10` | known_item | 0.7193 | 0.9800 | 1.0000 | 1.0000 |
| `oai-field-hybrid+text=title75+d=10` | keyword | 0.7357 | 0.6644 | 0.9600 | 0.9600 |
| `oai-field-hybrid+text=title75+d=10` | question | 0.7138 | 0.5750 | 0.7600 | 0.8000 |
| `oai-field-hybrid+text=title75+d=10` | paraphrase | 0.6512 | 0.4278 | 0.7200 | 0.8000 |
| `oai-field-hybrid+text=title75+d=10` | known_item | 0.7094 | 0.9533 | 1.0000 | 1.0000 |
| `oai-field-hybrid+text=concat+d=100` | keyword | 0.7324 | 0.7157 | 0.9200 | 0.9600 |
| `oai-field-hybrid+text=concat+d=100` | question | 0.7252 | 0.5833 | 0.7200 | 0.7600 |
| `oai-field-hybrid+text=concat+d=100` | paraphrase | 0.6931 | 0.4873 | 0.6400 | 0.6400 |
| `oai-field-hybrid+text=concat+d=100` | known_item | 0.7262 | 0.9800 | 1.0000 | 1.0000 |
| `oai-field-hybrid+text=title25+d=100` | keyword | 0.7363 | 0.7417 | 0.9200 | 0.9600 |
| `oai-field-hybrid+text=title25+d=100` | question | 0.7288 | 0.6250 | 0.7600 | 0.7600 |
| `oai-field-hybrid+text=title25+d=100` | paraphrase | 0.6757 | 0.4581 | 0.6400 | 0.6400 |
| `oai-field-hybrid+text=title25+d=100` | known_item | 0.7331 | 0.9800 | 1.0000 | 1.0000 |
| `oai-field-hybrid+text=title50+d=100` | keyword | 0.7273 | 0.7244 | 0.9200 | 0.9600 |
| `oai-field-hybrid+text=title50+d=100` | question | 0.7065 | 0.5867 | 0.7600 | 0.7600 |
| `oai-field-hybrid+text=title50+d=100` | paraphrase | 0.6164 | 0.4161 | 0.6000 | 0.6400 |
| `oai-field-hybrid+text=title50+d=100` | known_item | 0.7239 | 0.9800 | 1.0000 | 1.0000 |
| `oai-field-hybrid+text=title75+d=100` | keyword | 0.6701 | 0.6574 | 0.9200 | 0.9200 |
| `oai-field-hybrid+text=title75+d=100` | question | 0.6500 | 0.6100 | 0.7600 | 0.7600 |
| `oai-field-hybrid+text=title75+d=100` | paraphrase | 0.5978 | 0.4044 | 0.5600 | 0.6000 |
| `oai-field-hybrid+text=title75+d=100` | known_item | 0.6954 | 0.9533 | 1.0000 | 1.0000 |

## Reproducibility and cautions

- Cached scores only; no embedding/judging API execution path.
- Parent embeddings use the shared $1.25 lifetime ledger plus $0.30 task ceiling. No automatic retries; unknown outcomes retain reservations.
- Reported cost is local accounting at the stored $0.13/M token price, not a guarantee about provider billing/free credits.
- Input/label hashes and plan frozen; cached document vectors bind exact text, model and dimensions. Query/concat caches are read-only; missing cache aborts.
- `../openai-field-dev/raw-field-scores.json`: frozen parent cosine signals; `cases.json`: wins/losses.
- `report.json`: screening, paired source intervals and same-model controls.
- Held-out300 untouched; human overrides preserved. Exploratory dev comparisons are not corrected for repeated selection or multiple testing.
