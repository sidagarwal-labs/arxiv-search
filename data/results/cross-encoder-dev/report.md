# Local cross-encoder: bounded dev experiment

Model: `cross-encoder/ms-marco-MiniLM-L6-v2` at `233902d25c440f23af6f7d6e94d2946bac0bee0a` (Apache-2.0). MS MARCO passage ranker, not specifically fine-tuned here for scientific abstracts or these dev queries. CPU float32, 512 tokens per query/document pair, preserve query and truncate document only. Scores are raw logits, not calibrated probabilities.

Frozen baseline: `fusion-shortlist+a=1+d=500`. Five settings fixed before outcomes; no promotion. Baseline-prefix depth10 isolates ordering; depth30/100 and union100 can replace the top10. Union100 is each retriever's top100, plus baseline100. 50/50 blend uses RRF c30, not averaged logits and cosine scores.

Missing judgments across new top10s: **392**. Unjudged is not irrelevant. Incomplete nDCG/P10 are diagnostic values treating missing gains as zero under the current frozen pool; not ranked or used for promotion. Adding labels can also revise ideal DCG, so these are not bounds on future nDCG. Graded paired intervals are withheld until coverage is complete; source metrics and their paired intervals remain valid.

| System | nDCG10 (diagnostic if incomplete) | P10 | Judged10 | Source MRR10 | R10 | R20 | Coverage |
|---|---|---|---|---|---|---|---|
| `cross-minilm-l6+pool=baseline+d=10` | 0.7021 | 0.6890 | 1.0000 | 0.6593 | 0.8600 | 0.8900 | fully judged |
| `cross-minilm-l6+pool=baseline+d=100` | 0.5639 | 0.5110 | 0.7330 | 0.6046 | 0.7400 | 0.8200 | PROVISIONAL |
| `cross-minilm-l6+pool=baseline+d=30` | 0.6332 | 0.6130 | 0.9040 | 0.6201 | 0.7900 | 0.8500 | PROVISIONAL |
| `cross-minilm-l6+pool=union100+w=0.5` | 0.6777 | 0.6450 | 0.9340 | 0.6875 | 0.8400 | 0.8500 | PROVISIONAL |
| `cross-minilm-l6+pool=union100+w=1` | 0.5448 | 0.4870 | 0.6860 | 0.6041 | 0.7400 | 0.7900 | PROVISIONAL |
| `fusion-shortlist+a=1+d=500` | 0.7176 | 0.6890 | 1.0000 | 0.6967 | 0.8600 | 0.8900 | fully judged |

## Source metrics by segment

| System | Segment | Source MRR10 | R10 | R20 |
|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | keyword | 0.7202 | 0.9600 | 0.9600 |
| `fusion-shortlist+a=1+d=500` | question | 0.5883 | 0.7600 | 0.8000 |
| `fusion-shortlist+a=1+d=500` | paraphrase | 0.4984 | 0.7200 | 0.8000 |
| `fusion-shortlist+a=1+d=500` | known_item | 0.9800 | 1.0000 | 1.0000 |
| `cross-minilm-l6+pool=baseline+d=10` | keyword | 0.7631 | 0.9600 | 0.9600 |
| `cross-minilm-l6+pool=baseline+d=10` | question | 0.5383 | 0.7600 | 0.8000 |
| `cross-minilm-l6+pool=baseline+d=10` | paraphrase | 0.4025 | 0.7200 | 0.8000 |
| `cross-minilm-l6+pool=baseline+d=10` | known_item | 0.9333 | 1.0000 | 1.0000 |
| `cross-minilm-l6+pool=baseline+d=30` | keyword | 0.7680 | 0.9200 | 0.9600 |
| `cross-minilm-l6+pool=baseline+d=30` | question | 0.5183 | 0.7200 | 0.7600 |
| `cross-minilm-l6+pool=baseline+d=30` | paraphrase | 0.2874 | 0.5200 | 0.6800 |
| `cross-minilm-l6+pool=baseline+d=30` | known_item | 0.9067 | 1.0000 | 1.0000 |
| `cross-minilm-l6+pool=baseline+d=100` | keyword | 0.7644 | 0.9200 | 0.9200 |
| `cross-minilm-l6+pool=baseline+d=100` | question | 0.4933 | 0.6400 | 0.8000 |
| `cross-minilm-l6+pool=baseline+d=100` | paraphrase | 0.2558 | 0.4000 | 0.5600 |
| `cross-minilm-l6+pool=baseline+d=100` | known_item | 0.9050 | 1.0000 | 1.0000 |
| `cross-minilm-l6+pool=union100+w=1` | keyword | 0.7644 | 0.9200 | 0.9200 |
| `cross-minilm-l6+pool=union100+w=1` | question | 0.4933 | 0.6400 | 0.7600 |
| `cross-minilm-l6+pool=union100+w=1` | paraphrase | 0.2538 | 0.4000 | 0.4800 |
| `cross-minilm-l6+pool=union100+w=1` | known_item | 0.9050 | 1.0000 | 1.0000 |
| `cross-minilm-l6+pool=union100+w=0.5` | keyword | 0.7744 | 0.9600 | 0.9600 |
| `cross-minilm-l6+pool=union100+w=0.5` | question | 0.5867 | 0.7600 | 0.7600 |
| `cross-minilm-l6+pool=union100+w=0.5` | paraphrase | 0.4287 | 0.6400 | 0.6800 |
| `cross-minilm-l6+pool=union100+w=0.5` | known_item | 0.9600 | 1.0000 | 1.0000 |

## Paired comparisons and guardrails

Differences are candidate minus frozen baseline; exploratory query-bootstrap 95% intervals, conditional on labels and not adjusted for repeated dev tuning.

| System | nDCG delta [95% CI] | Source MRR delta [95% CI] | Source top10 losses / gains | Known-item regressions | Screen |
|---|---|---|---|---|---|
| `cross-minilm-l6+pool=baseline+d=10` | -0.0155 [-0.0278, -0.0037] | -0.0374 [-0.0994, +0.0194] | 0 / 0 | 2 | not passed |
| `cross-minilm-l6+pool=baseline+d=30` | withheld: incomplete judgments | -0.0766 [-0.1428, -0.0130] | 8 / 1 | 3 | not passed |
| `cross-minilm-l6+pool=baseline+d=100` | withheld: incomplete judgments | -0.0921 [-0.1624, -0.0263] | 13 / 1 | 3 | not passed |
| `cross-minilm-l6+pool=union100+w=1` | withheld: incomplete judgments | -0.0926 [-0.1626, -0.0268] | 13 / 1 | 3 | not passed |
| `cross-minilm-l6+pool=union100+w=0.5` | withheld: incomplete judgments | -0.0093 [-0.0616, +0.0372] | 3 / 1 | 1 | not passed |

## Original inference workload

- Pairs: 17849; aggregate per-query seconds: 2714.0.
- Documents truncated at the pair token limit: 56.

## Reproducibility

- `preregistration.json` and `input-provenance.json` freeze settings and inputs.
- Per-query `score-cache` files validate query/text/model fingerprints and complete candidate membership. Delete a specific damaged cache only deliberately; mismatches fail.
- Repeated runs reuse cached logits; no remote inference, paid embeddings or judging.
- `report.json`: paired bootstrap intervals, coverage, screening and per-query metrics.
- `cases.json`: source-rank wins/losses and top10 paper evidence, with missing grades explicit.
- Wall time includes tokenization and CPU inference, excludes model loading; it is an offline throughput measurement, not production request latency or a GPU benchmark.
- Broad-query source recall is only a single-target proxy. Dev intervals are exploratory; held-out test and human overrides remain untouched.
