# arXiv Search

Hybrid search over **23,304 recent arXiv papers** in information retrieval (cs.IR),
computation and language (cs.CL) and machine learning (cs.LG). 

The project treats search quality as a measurement problem. Every ranking change is
tested on the same development queries before it becomes the working baseline, and
a 300-query held-out test set is reserved for the final evaluation.

## Highlights

- **Hybrid retrieval:** BM25 keyword search and OpenAI `text-embedding-3-large`
  semantic search, combined with rank fusion and score-based reordering.
- **Measured progress:** on the same 3,533-pair label layer, nDCG@10 rose from
  **0.5090** (tuned BM25) to **0.7036** (hybrid retrieval) and **0.7684**
  (two-pass LLM reranking) on 100 development queries.
- **Evaluation set:** 400 LLM-generated keyword, question, paraphrase and
  known-item queries, split into 100 development and 300 held-out test queries.
- **Calibrated LLM judge:** GPT-5.4 mini grades relevance offline. Against
  100 reference labels from a higher-reasoning model (GPT-6 ASTRA), it reached
  **77% exact agreement** and **0.802 quadratic kappa**, with no opposite (0 vs. 2)
  grades. This is model-to-model agreement; no human labels exist yet.
- **Cost-controlled experiments:** cached embeddings and rankings make most
  experiments free to rerun. Paid API steps run under explicit budget caps; the
  full-corpus OpenAI embeddings cost $0.74.

## How it works

```
 1. DOWNLOAD     →   2. CLEAN UP     →   3. SEARCH        →   4. TEST          →   5. ANSWER
 arXiv catalog       23,304 papers       BM25 + embeddings     400 test queries     LLM answers
 (raw pages)         (corpus.jsonl)      find top papers       score each method    using top papers
```

The offline search and development-evaluation pipeline is built. A
[mock-backed search UI](web/README.md) is being developed locally; its demo
ranking and summaries are not measurements of the real system. Backend/API
integration, retrieval-augmented answers and public deployment remain pending.

## Current working baselines

Search runs in two stages ([Decision 45](docs/02-decisions.md#45-safeguard-promoted-as-the-reranking-baseline-two-stage-leaderboard-2026-11-03)):
**Stage 1 retrieval** (Decision 36, free and deterministic) finds candidates;
**Stage 2 reranking** asks GPT-5.4 mini to score the top 50 twice, averages the
two scores ([Decision 46](docs/02-decisions.md#46-two-pass-score-averaging-promoted-as-the-reranking-baseline-2026-11-03)) and blends that order with the retrieval order. GPT-5.4 mini also grades results offline as the judge.

| Component | Current selection |
|---|---|
| Corpus and vectors | 23,304 title/abstract records; normalized OpenAI-large embeddings, 3,072 dimensions; local NumPy exact search |
| Stage 1 retrieval | Tuned BM25 + semantic retrieval; RRF shortlist followed by score reordering ([Decision 36](docs/02-decisions.md#36-recall-preserving-shortlist-score-baseline-promoted-2026-10-29)) |
| Stage 2 reranking | Two GPT-5.4 mini passes over the top 50, averaged and fused with retrieval order ([Decision 46](docs/02-decisions.md#46-two-pass-score-averaging-promoted-as-the-reranking-baseline-2026-11-03)); approximately $0.028 per uncached query |
| Relevance labels | GPT-5.4 mini 0/1/2 grades with 100 ASTRA reference overrides; current Decision 46 layer has 3,533 pairs; no human validation |
| Evaluation | 100 dev / 300 held-out queries; graded relevance, source ranking, coverage, cost and reliability |

Exact weights, model snapshot and cached timing scope are in the
[configuration details](docs/10-reproduction-guide.md#selected-configuration-details).
Reranker scores vary between calls; live serving must account for caching and
retrieval fallback. Hosted vector storage and real RAG are not deployed.

## Development results

100 development queries, 23,304 papers, shared Decision 46 label layer
(3,533 pairs). Compare scores only within the same corpus, query and label scope.

| Two-stage baselines (shared labels) | nDCG@10 | Source MRR@10 | Source R@10 |
|---|---|---|---|
| Stage 1 retrieval baseline | 0.7036 | 0.6967 | 86% |
| Stage 2: + LLM top-50 reranker, one pass (Decision 45) | 0.7521 | 0.7197 | 87% |
| **Stage 2: + LLM top-50 reranker, two passes averaged (current)** | **0.7684** | **0.7232** | **87%** |

- **nDCG@10:** graded relevance of the top 10 results, using 0/1/2 labels.
- **Source MRR@10:** how high the paper each query was written from appears.
- **Source R@10:** share of queries whose source paper appears in the top 10.

<a id="historical-retrieval-milestones"></a>

**Complete metrics remain available:** [all-system metrics tables](data/results/catalog-dev/report.md),
[machine-readable results](data/results/catalog-dev/report.json),
[results and historical comparisons](docs/05-results.md), and
[milestone charts](docs/06-charts.md). The earlier 3,294-pair milestone table is
preserved in the [reproduction guide](docs/10-reproduction-guide.md#historical-retrieval-milestones).

Repeated selection on these 100 dev queries makes scores optimistic; the 300-query
held-out test has not been run. Judge/reranker model-family overlap and the lack
of human validation limit quality claims. Milestones can change several settings,
so their gains are not isolated causal effects.

### Tested but not adopted

- Unrestricted score fusion traded source-paper recall for graded relevance.
- Local MiniLM cross-encoder reranking regressed on the measured task.
- Separate title/abstract embeddings did not justify promotion.
- LLM scores without the safeguard improved graded relevance but hurt source ranking.

The [experiment log](docs/07-experiment-log.md) has the full history, budgets and
caveats.

## Status

- [x] Download and clean 23,304 papers
- [x] Keyword, embedding and hybrid search, tuned on development queries
- [x] Evaluation tooling: 400 queries, metrics, results table, calibrated LLM judge and full development evaluation
- [ ] Final held-out test on 300 queries
- [ ] Human validation of judge labels (none collected yet)
- [ ] Retrieval-augmented answers with an LLM
- [ ] Integrate the locally developed mock-backed UI with the real API
- [ ] Public deployment and serving measurements

## Read more

Start with the current baselines above, then the generated results and charts.
Decisions, findings and the experiment log preserve the learning history; older
plans and controls are not necessarily current configurations.

| Doc | What's in it |
|---|---|
| [How it works](docs/01-how-it-works.md) | Every step and every file in plain English, plus the folder layout |
| [Decisions](docs/02-decisions.md) | Every choice and why it was made |
| [Findings](docs/03-findings.md) | Measurements behind the decisions |
| [Glossary](docs/04-glossary.md) | What BM25, embedding, MRR, etc. mean |
| [Results](docs/05-results.md) | Stage 1 retrieval and Stage 2 reranker progress; links to the full every-system tables |
| [Charts](docs/06-charts.md) | Hill-climbing milestones (retrieval + reranker), latest Stage 1 and Stage 2 scores, and measured remaining headroom |
| [Experiment log](docs/07-experiment-log.md) | Detailed experiment history, budgets and caveats |
| [Provenance and retention](docs/08-provenance-and-retention.md) | Experiment evidence checklist and what maintenance must preserve |
| [Labeler comparison](docs/09-labeler-comparison.md) | Matched-pair comparisons and GPT-6 ASTRA reference-label provenance |
| [Reproduction guide](docs/10-reproduction-guide.md) | Setup, historical milestones, local reproduction and explicitly separated API-spending commands |
| [Web UI](web/README.md) | Local demo, API contract and deployment plan; not live benchmark evidence |

Repository maintenance follows [the working rules](AGENTS.md): investigate,
coordinate with development, propose exact changes, obtain user approval, then
apply and verify. Cleanup does not automatically delete historical experiments
or promote a new baseline.

## Run it

**Read results without setup:** open the [complete metrics tables](data/results/catalog-dev/report.md)
or [charts](docs/06-charts.md). No credentials or model calls are needed.

**Local development setup:**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,experiments]"   # experiments = embedding models
.\.venv\Scripts\python.exe -m pytest -q
```

For corpus/index reconstruction and model experiments, follow the
[reproduction guide](docs/10-reproduction-guide.md). API steps require relevant
credentials and separate approval; do not run the historical commands as a
blanket setup script.

### Quick offline experiment loop

The [cached-experiment commands](docs/10-reproduction-guide.md#cached-experiment-loop)
preserve the historical controls. They require the original local inputs and can
write derived reports; they are not necessary just to inspect the metrics.

## Folders

```
arxiv_search/       the system (settings in config.py)
tests/              automatic checks
experiments/        one-off measurements
docs/               explanations
data/               eval queries, labels and results are in git; downloads, corpus and embeddings are rebuilt locally
```
