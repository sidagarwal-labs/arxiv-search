# Reproduction guide and historical milestones

Start with the [current system](../README.md), [complete metrics tables](../data/results/catalog-dev/report.md)
and [machine report](../data/results/catalog-dev/report.json).
This page preserves the detailed commands and historical table formerly in the
README. It is not a script to execute from top to bottom.

## Selected configuration details

These are the selections summarized in the README, not new promotions:

| Component | Configuration and scope |
|---|---|
| BM25 | Exact terms + stems, authors, title weighted x2; k1=0.8, b=0.75; no stopword removal |
| Embeddings | `text-embedding-3-large`, 3,072 dimensions; normalized vectors; full-corpus cached embedding cost $0.7439 under the historical $1.25 lifetime cap |
| Stage 1 | RRF 55% semantic / 45% lexical, c=30, depth 100 selects top10; max-normalized fusion 75% semantic / 25% lexical, depth 500 reorders those ten; tail unchanged (Decision 36) |
| Stage 2 | `gpt-5.4-mini-2026-03-17` scores top50 0-4 twice; average scores; RRF with retrieval order c=30 (Decision 46); then `gpt-5.4-2026-03-05` (reasoning none) re-scores that top20 0-10 twice with `refine20-v1`, averages, sorts by score (Decision 46 order breaks ties), keeps its rank 1; ranks below 20 unchanged (Decision 50; Decision 47's mini + RRF refinement is the historical control and still the served release) |
| Reranker resources | Approximately $0.066 per uncached query (Decision 46 ~$0.028 + GPT-5.4 refinement ~$0.038); refinement provider time 3.24 s mean / 3.76 s p95 with both passes in parallel; not end-to-end website latency |
| AI summary | `gpt-6-luna`, prompt `answer-v2`, answer contract B (an ungrounded answer may cite the closest papers), top-10 evidence (Decision 49; Decision 48's GPT-5.4 mini / `answer-v1` is the historical control); approximately $0.0004 per answer, p50 2.4 s |
| Storage and serving | Offline NumPy arrays with paper-ID metadata and exact cosine search; hosted Postgres/pgvector was a plan, not a deployed service |

See the [decisions](02-decisions.md), [configuration source](../arxiv_search/config.py)
and [generated results](05-results.md) for identity and evidence. These settings
do not make stochastic model responses deterministic.

## Historical retrieval milestones

100 development queries, 23,304 papers, frozen **3,294-pair** label snapshot.
These original numbers are retained, not rescored. The current Decision 47 layer
has 3,579 pairs; use the [generated results](05-results.md) and
[charts](06-charts.md) for milestones on that common layer.

| Milestone | nDCG@10 | Source MRR@10 | Source R@10 |
|---|---|---|---|
| Tuned BM25 | 0.5187 | 0.5687 | 71% |
| GTE-small embeddings | 0.5811 | 0.5254 | 71% |
| BM25 + GTE-small hybrid | 0.6312 | 0.6350 | 80% |
| BM25 + OpenAI-large hybrid | 0.6604 | 0.6534 | 84% |
| RRF, 55% semantic, c=30 | 0.7064 | 0.6459 | 86% |
| Shortlist + score reordering (Decision 36) | 0.7176 | 0.6967 | 86% |

Repeated dev selection makes these scores optimistic. Each milestone may change
several settings; differences are not isolated causal effects. Negative results,
budgets and promotion reasoning remain in the [experiment log](07-experiment-log.md).

## Inspect saved evidence without running anything

No environment or credentials are needed to read the tracked results, labels
and configuration records. The full metrics have not been removed:

- [Results](05-results.md): stage summaries, historical comparisons and report links.
- [Complete catalog](../data/results/catalog-dev/report.md): all-system and segment tables.
- [Machine catalog](../data/results/catalog-dev/report.json): detailed metrics and provenance.
- [Findings](03-findings.md): measurements, failures and limitations.
- [Labeler comparison](09-labeler-comparison.md): separate ASTRA relevance references
  and Terra/ASTRA answer grading; neither is human validation.
- [Answer-model report](../data/results/answer-eval/report.md): Decision 48 selection
  using Decision 46 evidence, with cost, latency and quality tradeoffs.
- [Experiment L report](../data/results/answer-eval-v2/report.md) and
  [contract-B recheck](../data/results/answer-eval-v2/report-recheck.md): Decision 49.
- [Recent experiment digest](07-experiment-log.md#recent-experiments-at-a-glance):
  hypotheses, outcomes and links to the original evidence.

## Local environment and input requirements

Use Python 3.11 or newer from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,experiments]"
.\.venv\Scripts\python.exe -m pytest -q
```

Installing dependencies requires network access. Local model runs may download
model weights on first use and consume substantial compute.
Raw downloads, the processed corpus, indexes and embedding caches are not all
tracked in git. Saved evidence is readable from a clone, but a full replay needs
the original local artifacts and matching fingerprints. Do not repair missing
paid caches automatically or regenerate frozen queries, splits or grades.

For fresh corpus reconstruction, see the [ingestion walkthrough](01-how-it-works.md#step-1-download-downloadpy).
These commands contact arXiv and write local data; check the frozen experiment
inputs before using their output for a historical replay:

```powershell
.\.venv\Scripts\python.exe -m arxiv_search.ingest.download
.\.venv\Scripts\python.exe -m arxiv_search.ingest.clean
```

## Cached experiment loop

These historical commands use existing local inputs and may write reports.
They do not authorize spending, held-out evaluation or baseline promotion.

```powershell
# Inventory configured systems without running them.
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.experiments --list

# Local BM25 evaluation on dev; requires the original corpus and evaluation files.
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.experiments "bm25*"
# Saved dev rankings; no model API calls.
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.experiments --hybrid-grid
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.fusion_experiment
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.failure_analysis
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.fusion_review
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.score_fusion_experiment
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.fusion_refinement
```

Fusion experiments preserve different controls and label snapshots. Inspect the
owning module's requirements before execution; do not mix the resulting numbers.
For presentation-only refresh commands, see [provenance and retention](08-provenance-and-retention.md#offline-presentation-refresh).

## Local embedding runs

```powershell
# Four local embedding models; several hours on first run, cached thereafter.
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.experiments "dense*"
```

This is not a no-setup metrics viewer. It needs the corpus, model dependencies,
available disk space and potentially network access to download model weights.

## API experiments: separate approval required

Create a local environment file only when needed:

```powershell
Copy-Item .env.example .env
```

Google/Gemma-backed generation and judging need `GEMINI_API_KEY`; OpenAI-backed
judging and embeddings need `OPENAI_API_KEY`. Neither is needed to read saved
results or run the unit tests. Never commit credentials.

The commands below are historical entry points, not approval to execute them.
Quota, task caps and account pricing must be checked at execution time.

```powershell
# OFFLINE PREFLIGHT: estimate embedding inputs and costs.
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.embedding_pilot
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.openai_full
```

The historical pilot ceiling was $0.25; the full-corpus lifetime embedding cap
was $1.25. Adding `--run` can spend money. Those ceilings are not a fresh budget.

```powershell
# API CALLS: historical judge entry points, only with explicit approval.
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.judge --judge gemma-31b --queries pilot
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.judge --judge openai-nano --queries human --max-calls 1
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.judge --judge openai-mini --queries human --max-calls 1
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.graded --judge openai-mini --label --max-calls 20
```

`--queries human` is a legacy selector for the 100 **ASTRA reference** pairs,
not evidence of human grading. The selected judge is GPT-5.4 mini; other entries
are historical comparisons. API access can cost money even if previously covered
by an account offer.

```powershell
# OFFLINE REPORTING: requires original caches; may overwrite derived reports.
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.graded
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.judge_pilot report
```

Do not refresh a historical report just to read it: later cache additions can
change its coverage rows. Preserve its original scope.

The original query-generation workflow used `arxiv_search.evaluate.make_queries`
and `arxiv_search.evaluate.split`. The saved queries and split are frozen.
Generating replacements requires separate approval and a new dataset identity;
it is not part of reproducing the current benchmark.
