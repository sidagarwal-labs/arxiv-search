# OpenAI-large candidate title/abstract experiment

Eight prespecified settings: concatenated control and separate25/50/75% title at baseline prefixes10/100. Scoring recipe: Pure cosine for concat; t*cos(query,title)+(1-t)*cos(query,abstract) for fields. Unit3072vectors, no baseline blending, stable baseline ties. Exactly the same OpenAI-large model,3072 dimensions and cached query vectors. Body means abstract. Candidate-only; no new full-corpus retrieval. The approved Decision36 baseline remains unchanged.

Embedding workload/cost: `{"candidate_documents": 7644, "dimensions": 3072, "embedding_tokens_estimate": 2081960, "field_inputs": 15288, "judge_calls": 0, "model": "text-embedding-3-large", "new_accounted_usd": 0.2706548, "shared_lifetime_accounting": {"accounted_usd": 1.01450596, "api_seconds": 1047.239601600084, "requests": 605}}`

Unjudged new top10 pairs: **397**. No judging calls. Incomplete nDCG/P10 are diagnostic, not comparable winner evidence; graded paired intervals withheld. Adding labels can revise ideal DCG. Source metrics remain complete.

| System | nDCG10 | P10 | Judged10 | Source MRR10 | R10 | R20 | Coverage |
|---|---|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.7176 | 0.6890 | 1.0000 | 0.6967 | 0.8600 | 0.8900 | complete |
| `oai-field+text=concat+d=10` | 0.6903 | 0.6890 | 1.0000 | 0.6088 | 0.8600 | 0.8900 | complete |
| `oai-field+text=concat+d=100` | 0.6438 | 0.6370 | 1.0000 | 0.5993 | 0.8200 | 0.8800 | complete |
| `oai-field+text=title25+d=10` | 0.7011 | 0.6890 | 1.0000 | 0.6303 | 0.8600 | 0.8900 | complete |
| `oai-field+text=title25+d=100` | 0.6275 | 0.5770 | 0.8560 | 0.6185 | 0.8100 | 0.8900 | PROVISIONAL |
| `oai-field+text=title50+d=10` | 0.6903 | 0.6890 | 1.0000 | 0.6039 | 0.8600 | 0.8900 | complete |
| `oai-field+text=title50+d=100` | 0.5980 | 0.5490 | 0.7990 | 0.5992 | 0.8100 | 0.8400 | PROVISIONAL |
| `oai-field+text=title75+d=10` | 0.6808 | 0.6890 | 1.0000 | 0.5720 | 0.8600 | 0.8900 | complete |
| `oai-field+text=title75+d=100` | 0.5421 | 0.4970 | 0.7230 | 0.5405 | 0.7900 | 0.8000 | PROVISIONAL |

## Paired nDCG comparisons

| Setting | Versus baseline delta [95% CI] | Versus same-depth concat [95% CI] |
|---|---|---|
| `oai-field+text=concat+d=10` | -0.0273 [-0.0395,-0.0150] | +0.0000 [+0.0000,+0.0000] |
| `oai-field+text=title25+d=10` | -0.0165 [-0.0287,-0.0038] | +0.0108 [+0.0013,+0.0203] |
| `oai-field+text=title50+d=10` | -0.0273 [-0.0426,-0.0134] | -0.0001 [-0.0118,+0.0107] |
| `oai-field+text=title75+d=10` | -0.0367 [-0.0520,-0.0216] | -0.0095 [-0.0217,+0.0024] |
| `oai-field+text=concat+d=100` | -0.0738 [-0.1015,-0.0477] | +0.0000 [+0.0000,+0.0000] |
| `oai-field+text=title25+d=100` | withheld | withheld |
| `oai-field+text=title50+d=100` | withheld | withheld |
| `oai-field+text=title75+d=100` | withheld | withheld |

## Segments

| Setting | Segment | nDCG10 (diagnostic if incomplete) | Source MRR10 | R10 | R20 |
|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | keyword | 0.7385 | 0.7202 | 0.9600 | 0.9600 |
| `fusion-shortlist+a=1+d=500` | question | 0.7277 | 0.5883 | 0.7600 | 0.8000 |
| `fusion-shortlist+a=1+d=500` | paraphrase | 0.6858 | 0.4984 | 0.7200 | 0.8000 |
| `fusion-shortlist+a=1+d=500` | known_item | 0.7183 | 0.9800 | 1.0000 | 1.0000 |
| `oai-field+text=concat+d=10` | keyword | 0.7163 | 0.6064 | 0.9600 | 0.9600 |
| `oai-field+text=concat+d=10` | question | 0.7100 | 0.5580 | 0.7600 | 0.8000 |
| `oai-field+text=concat+d=10` | paraphrase | 0.6578 | 0.4690 | 0.7200 | 0.8000 |
| `oai-field+text=concat+d=10` | known_item | 0.6772 | 0.8017 | 1.0000 | 1.0000 |
| `oai-field+text=title25+d=10` | keyword | 0.7185 | 0.6038 | 0.9600 | 0.9600 |
| `oai-field+text=title25+d=10` | question | 0.7127 | 0.6067 | 0.7600 | 0.8000 |
| `oai-field+text=title25+d=10` | paraphrase | 0.6726 | 0.4376 | 0.7200 | 0.8000 |
| `oai-field+text=title25+d=10` | known_item | 0.7006 | 0.8733 | 1.0000 | 1.0000 |
| `oai-field+text=title50+d=10` | keyword | 0.7186 | 0.6107 | 0.9600 | 0.9600 |
| `oai-field+text=title50+d=10` | question | 0.7012 | 0.5367 | 0.7600 | 0.8000 |
| `oai-field+text=title50+d=10` | paraphrase | 0.6492 | 0.4383 | 0.7200 | 0.8000 |
| `oai-field+text=title50+d=10` | known_item | 0.6919 | 0.8300 | 1.0000 | 1.0000 |
| `oai-field+text=title75+d=10` | keyword | 0.7232 | 0.5972 | 0.9600 | 0.9600 |
| `oai-field+text=title75+d=10` | question | 0.6865 | 0.4547 | 0.7600 | 0.8000 |
| `oai-field+text=title75+d=10` | paraphrase | 0.6315 | 0.4383 | 0.7200 | 0.8000 |
| `oai-field+text=title75+d=10` | known_item | 0.6820 | 0.7978 | 1.0000 | 1.0000 |
| `oai-field+text=concat+d=100` | keyword | 0.6424 | 0.5773 | 0.8000 | 0.8800 |
| `oai-field+text=concat+d=100` | question | 0.6881 | 0.5604 | 0.8000 | 0.8400 |
| `oai-field+text=concat+d=100` | paraphrase | 0.6444 | 0.4664 | 0.7200 | 0.8000 |
| `oai-field+text=concat+d=100` | known_item | 0.6002 | 0.7930 | 0.9600 | 1.0000 |
| `oai-field+text=title25+d=100` | keyword | 0.6310 | 0.5683 | 0.8000 | 0.9200 |
| `oai-field+text=title25+d=100` | question | 0.6804 | 0.6124 | 0.8000 | 0.8800 |
| `oai-field+text=title25+d=100` | paraphrase | 0.5944 | 0.4269 | 0.6400 | 0.7600 |
| `oai-field+text=title25+d=100` | known_item | 0.6040 | 0.8663 | 1.0000 | 1.0000 |
| `oai-field+text=title50+d=100` | keyword | 0.6133 | 0.5890 | 0.8000 | 0.8000 |
| `oai-field+text=title50+d=100` | question | 0.6327 | 0.5540 | 0.8400 | 0.8800 |
| `oai-field+text=title50+d=100` | paraphrase | 0.5505 | 0.4324 | 0.6000 | 0.6800 |
| `oai-field+text=title50+d=100` | known_item | 0.5956 | 0.8213 | 1.0000 | 1.0000 |
| `oai-field+text=title75+d=100` | keyword | 0.5610 | 0.5204 | 0.7200 | 0.7200 |
| `oai-field+text=title75+d=100` | question | 0.5508 | 0.4633 | 0.8800 | 0.8800 |
| `oai-field+text=title75+d=100` | paraphrase | 0.4822 | 0.4137 | 0.6000 | 0.6400 |
| `oai-field+text=title75+d=100` | known_item | 0.5746 | 0.7647 | 0.9600 | 0.9600 |

## Reproducibility and cautions

- Dry-run default; --run explicitly enables missing embeddings, not judging.
- Parent embeddings use the shared $1.25 lifetime ledger plus $0.30 task ceiling. No automatic retries; unknown outcomes retain reservations.
- Reported cost is local accounting at the stored $0.13/M token price, not a guarantee about provider billing/free credits.
- Input/label hashes and plan frozen; cached document vectors bind exact text, model and dimensions. Query/concat caches are read-only; missing cache aborts.
- `raw-field-scores.json`: aligned cosine signals; `cases.json`: wins/losses.
- `report.json`: screening, paired source intervals and same-model controls.
- Held-out300 untouched; human overrides preserved. Exploratory dev comparisons are not corrected for repeated selection or multiple testing.
