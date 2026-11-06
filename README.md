# arXiv Search

Hybrid search over **23,304 recent arXiv papers** in information retrieval (cs.IR),
computation and language (cs.CL) and machine learning (cs.LG). 

The project treats search quality as a measurement problem. Every ranking change is
tested on the same development queries before it becomes the working baseline, and
a 300-query held-out test set is reserved for the final evaluation.

<a id="highlights"></a>

## What this project demonstrates

- **Hybrid retrieval:** BM25 keyword search and OpenAI `text-embedding-3-large`
  semantic search, combined with rank fusion and score-based reordering.
- **Evaluation discipline:** frozen query splits, shared relevance labels,
  paired comparisons, noise checks and explicit promotion gates.
- **Grounded answers:** model selection based on citation quality, faithfulness,
  abstention, cost and latency, not fluency alone.
- **Engineering tradeoffs:** cached experiments, API budget controls and
  measured storage compression. Failed experiments remain part of the evidence.

## How it works

Download and clean title/abstract records, retrieve candidates, rerank them,
then generate cited answers. Evaluate each stage separately.

Retrieval, reranking and cited answer generation have been evaluated offline.
Serving: **local preview, not deployed**. Saved experiment timings are not
end-to-end production latency.

## Current working baselines

Stage 1 finds candidates; Stage 2 reranks them. GPT-5.4 mini also serves as the
offline relevance judge; GPT-6 Luna writes the AI summary. These roles have
separate prompts and evaluations.

| Component | Current selection |
|---|---|
| Corpus and vectors | 23,304 title/abstract records; normalized OpenAI-large embeddings, 3,072 dimensions; local NumPy exact search |
| Stage 1 retrieval | Tuned BM25 + semantic retrieval; RRF shortlist followed by score reordering ([Decision 36](docs/02-decisions.md#36-recall-preserving-shortlist-score-baseline-promoted-2026-10-29)) |
| Stage 2 reranking | Two GPT-5.4 mini passes over the top 50 fused with retrieval order (Decision 46), then two GPT-5.4 passes re-score the top 20, ordered by averaged score, keeping rank 1 ([Decision 50](docs/02-decisions.md#50-gpt-54-re-scores-the-top-20-ordered-by-its-scores-2026-11-06)); approximately $0.066 per uncached query; serving still runs [Decision 47](docs/02-decisions.md#47-top-20-refinement-promoted-as-the-reranking-baseline-2026-11-04) until a new release |
| AI summary | GPT-6 Luna (prompt `answer-v2`) answers from the top 10 with an [n] citation in every sentence, or says the results don't answer and cites the closest papers ([Decision 49](docs/02-decisions.md#49-gpt-6-luna-writes-the-ai-summary-2026-11-04)); approximately $0.0004 per answer, p50 2.4 s |
| Relevance labels | GPT-5.4 mini 0/1/2 grades with 100 ASTRA reference overrides; current Decision 47 layer has 3,579 pairs; no human validation |
| Evaluation | 100 dev / 300 held-out queries; graded relevance, source ranking, coverage, cost and reliability |

Exact weights, model snapshot and cached timing scope are in the
[configuration details](docs/10-reproduction-guide.md#selected-configuration-details).
Reranker scores vary between calls; offline evaluation is not a serving guarantee.

## Development results

100 development queries, 23,304 papers, shared Decision 47 label layer
(3,579 pairs). Compare scores only within the same corpus, query and label scope.

| Two-stage baselines (shared labels) | nDCG@10 | Source MRR@10 | Source R@10 |
|---|---|---|---|
| Stage 1 retrieval baseline | 0.7007 | 0.6967 | 86% |
| Stage 2: + LLM top-50 reranker, one pass (Decision 45) | 0.7490 | 0.7197 | 87% |
| Stage 2: + LLM top-50 reranker, two passes averaged (Decision 46) | 0.7652 | 0.7232 | 87% |
| **Stage 2: + top-20 refinement, keep rank 1 (current, Decision 47)** | **0.7939** | **0.7383** | **92%** |

nDCG measures graded relevance; source MRR measures the source paper's rank;
source recall measures whether it appears in the top 10.

**Decision 50** (GPT-5.4 top-20 re-scoring) is measured on the completed top-20
label layer, so compare it with D47 on that layer: nDCG@10 0.7886 → **0.8418**,
source MRR 0.738 → 0.766, source R@10 92% → 93% (100 dev); on the 80 queries not
used to choose it, 0.7912 → **0.8449** (+0.054 [+0.037, +0.071]).

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

<a id="tested-but-not-adopted"></a>

### Lessons from experiments

- Unrestricted score fusion traded source-paper recall for graded relevance.
- Local MiniLM cross-encoder reranking regressed on the measured task.
- Separate title/abstract embeddings did not justify promotion.
- LLM scores without the safeguard improved graded relevance but hurt source ranking.
- Compression changed the tradeoff: full-dimensional float16 nearly preserved
  retrieval quality, while reducing dimensions lost candidate overlap.
- Requiring a citation in every sentence turned the cheapest answer model into
  the most faithful one; most unsupported sentences had simply lacked their own [n].

The [experiment digest](docs/07-experiment-log.md#recent-experiments-at-a-glance)
connects hypotheses, outcomes and lessons to detailed reports.

## Status

**Selected:** Decision 50 reranking (serving still on Decision 47) and Decision 49 AI summaries.
**Still open:** final held-out evaluation, human validation, public deployment
and end-to-end serving measurements.

## Read more

Older plans and controls in the learning history are not necessarily current selections.

| Doc | What's in it |
|---|---|
| [How it works](docs/01-how-it-works.md) | Architecture, worked examples and historical walkthroughs |
| [Decisions](docs/02-decisions.md) | Every choice and why it was made |
| [Findings](docs/03-findings.md) | Measurements behind the decisions |
| [Glossary](docs/04-glossary.md) | What BM25, embedding, MRR, etc. mean |
| [Results](docs/05-results.md) | Stage 1 retrieval and Stage 2 reranker progress; links to the full every-system tables |
| [Charts](docs/06-charts.md) | Hill-climbing milestones (retrieval + reranker), latest Stage 1 and Stage 2 scores, and measured remaining headroom |
| [Experiment log](docs/07-experiment-log.md) | Detailed experiment history, budgets and caveats |
| [Provenance and retention](docs/08-provenance-and-retention.md) | Experiment evidence checklist and what maintenance must preserve |
| [Labeler comparison](docs/09-labeler-comparison.md) | Separate relevance-label and answer-grading provenance |
| [Reproduction guide](docs/10-reproduction-guide.md) | Setup, historical milestones, local reproduction and explicitly separated API-spending commands |

Maintenance follows [the working rules](AGENTS.md).

## Run it

**Read results without setup:** open the [complete metrics tables](data/results/catalog-dev/report.md)
or [charts](docs/06-charts.md). No credentials or model calls are needed.

<a id="quick-offline-experiment-loop"></a>
<a id="folders"></a>

For [local setup](docs/10-reproduction-guide.md#local-environment-and-input-requirements)
and [cached experiments](docs/10-reproduction-guide.md#cached-experiment-loop),
use the reproduction guide. Full replay needs original local artifacts.
API steps require credentials and separate approval; historical commands are
not a blanket setup script.
