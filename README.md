# arXiv Search

Hybrid search over **23,304 recent arXiv papers** in information retrieval (cs.IR),
computation and language (cs.CL) and machine learning (cs.LG). 

The project treats search quality as a measurement problem. Every ranking change is
tested on the same development queries before it becomes the working baseline, and
a 300-query held-out test set is reserved for the final evaluation.

## Highlights

- **Hybrid retrieval:** BM25 keyword search and OpenAI `text-embedding-3-large`
  semantic search, combined with rank fusion and score-based reordering.
- **Better rankings:** graded nDCG@10 rose from **0.519** (tuned BM25) to
  **0.718** on 100 development queries.
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

Steps 1-4 are built. Step 5, retrieval-augmented answers, and a web app are planned.

## Current working baselines

Search runs in two stages ([Decision 45](docs/02-decisions.md#45-safeguard-promoted-as-the-reranking-baseline-two-stage-leaderboard-2026-11-03)):
**Stage 1 retrieval** (Decision 36, free and deterministic) finds candidates;
**Stage 2 reranking** asks GPT-5.4 mini to score the top 50 twice, averages the
two scores ([Decision 46](docs/02-decisions.md#46-two-pass-score-averaging-promoted-as-the-reranking-baseline-2026-11-03)) and blends that order with the retrieval order. GPT-5.4 mini also grades results offline as the judge.

| Component | Selected configuration | Status |
|---|---|---|
| Corpus | 23,304 arXiv papers; title + abstract | Indexed with local models and OpenAI large |
| Keyword retrieval | BM25 with exact terms + stems, authors and title weighted x2; k1=0.8, b=0.75; no stopword removal | Measured on full corpus |
| Embeddings | OpenAI `text-embedding-3-large`, 3,072 dimensions; normalized vectors | Full-corpus vectors cached; $0.7439 under a separate $1.25 cap |
| Stage 1: hybrid selection + ordering | RRF (55% semantic / 45% lexical, c=30, depth 100) selects the top 10; max-normalized score fusion (75% semantic / 25% lexical, depth 500) reorders those ten; the tail is unchanged | **Retrieval baseline**, [Decision 36](docs/02-decisions.md#36-recall-preserving-shortlist-score-baseline-promoted-2026-10-29); deterministic |
| Stage 2: LLM reranker | GPT-5.4 mini (`2026-03-17` snapshot) scores the retrieval top 50 from 0-4 in two identical requests; the two scores are averaged; RRF of LLM order and retrieval order (c=30); ranks below 50 unchanged | **Reranking baseline**, [Decision 46](docs/02-decisions.md#46-two-pass-score-averaging-promoted-as-the-reranking-baseline-2026-11-03) (single-pass [Decision 45](docs/02-decisions.md#45-safeguard-promoted-as-the-reranking-baseline-two-stage-leaderboard-2026-11-03) kept as a control); ≈ $0.028 per uncached query, p50 2.9 s with the two requests in parallel; scores vary run to run, so production must cache and fall back to Stage 1 |
| Relevance judge | OpenAI `gpt-5.4-mini`; blind 0/1/2 pair labels; 100 GPT-6 ASTRA reference labels override | Selected 2026-10-29; the 3,294-pair dev pool is covered for finalists; some older exploratory rows may be provisional; human validation not yet done |
| Evaluation | 100 dev / 300 held-out test queries; source-paper MRR and recall, plus graded nDCG and judgment coverage | Full dev evaluation complete; held-out test untouched |
| Vector storage | Offline NumPy arrays + paper-ID metadata; exact cosine search | Hosted Postgres/pgvector planned, not deployed |
| RAG | Not implemented | Planned |

## Development results

### Historical retrieval milestones

These rows preserve the earlier frozen 3,294-pair label snapshot: 100 development
queries over all 23,304 papers.
The [generated charts](docs/06-charts.md) rescore milestones on the newer shared
layer; their numbers should not be substituted into this historical table.

| Milestone | nDCG@10 | Source MRR@10 | Source R@10 |
|---|---|---|---|
| Tuned BM25 | 0.5187 | 0.5687 | 71% |
| GTE-small embeddings | 0.5811 | 0.5254 | 71% |
| BM25 + GTE-small hybrid | 0.6312 | 0.6350 | 80% |
| BM25 + OpenAI-large hybrid | 0.6604 | 0.6534 | 84% |
| RRF, 55% semantic, c=30 | 0.7064 | 0.6459 | 86% |
| **Shortlist + score reordering (retrieval baseline)** | **0.7176** | **0.6967** | **86%** |

After the LLM-reranker work added 239 grades (167 in Decision 45, 72 in Decision 46),
the leaderboard uses a shared 3,533-pair label layer; scores drop slightly on that
larger denominator, so compare rows only within one label set:

| Two-stage baselines (shared labels) | nDCG@10 | Source MRR@10 | Source R@10 |
|---|---|---|---|
| Stage 1 retrieval baseline | 0.7036 | 0.6967 | 86% |
| Stage 2: + LLM top-50 reranker, one pass (Decision 45) | 0.7521 | 0.7197 | 87% |
| **Stage 2: + LLM top-50 reranker, two passes averaged (current)** | **0.7684** | **0.7232** | **87%** |

- **nDCG@10:** graded relevance of the top 10 results, using 0/1/2 labels.
- **Source MRR@10:** how high the paper each query was written from appears.
- **Source R@10:** share of queries whose source paper appears in the top 10.

These are development scores. Settings were chosen by testing repeatedly on these
100 queries, so the scores are optimistic. Each milestone also changed other
parameters, so step gains are not isolated effects of one feature. The held-out
test has not been run.

### Tested but not adopted

- **Unrestricted score fusion:** nDCG@10 0.7197, but source R@10 fell from
  0.86 to 0.82. The working baseline keeps RRF's top 10 and reorders only those papers.
- **Local MiniLM cross-encoder reranking:** nDCG@10 fell from 0.7176 to 0.7021.
- **Separate title and abstract embeddings:** reached up to 0.7214 nDCG@10,
  but gains were within uncertainty and came with source-MRR or query-type tradeoffs.
- **LLM reranker without the safeguard:** highest nDCG@10 (0.7789 on shared
  labels) but source MRR fell; the RRF safeguard keeps most of the gain and
  protects exact source-paper hits, so it was promoted instead.

The [experiment log](docs/07-experiment-log.md) has the full history, budgets and
caveats.

## Status

- [x] Download and clean 23,304 papers
- [x] Keyword, embedding and hybrid search, tuned on development queries
- [x] Evaluation tooling: 400 queries, metrics, results table, calibrated LLM judge and full development evaluation
- [ ] Final held-out test on 300 queries
- [ ] Human validation of judge labels (none collected yet)
- [ ] Retrieval-augmented answers with an LLM
- [ ] Web app: database, API, web page and deployment

Next quality targets are better task and constraint matching and deeper candidate
selection: 133 known highly relevant query-paper pairs currently rank in positions 11-50.

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

Repository maintenance follows [the working rules](AGENTS.md): investigate,
coordinate with development, propose exact changes, obtain user approval, then
apply and verify. Cleanup does not automatically delete historical experiments
or promote a new baseline.

## Run it

```powershell
# One-time setup
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,experiments]"   # experiments = embedding models
copy .env.example .env        # then add GEMINI_API_KEY; OPENAI_API_KEY is optional

# Step 1: download (~20 min; if it stops, run again to resume)
.\.venv\Scripts\python.exe -m arxiv_search.ingest.download

# Step 2: clean up → data/processed/corpus.jsonl
.\.venv\Scripts\python.exe -m arxiv_search.ingest.clean

# Step 4b: write 400 test queries with an LLM → data/eval/ (~3 h on the free tier; resumable)
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.make_queries
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.split    # 100 dev / 300 test

# Step 4c: run search systems on the dev queries → docs/05-results.md (seconds each)
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.experiments "bm25*"   # all 25 BM25 systems
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.experiments "dense*"  # 4 embedding models (several hours first time; cached after)
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.experiments --hybrid-grid  # 24 blends of saved dev top-100 rankings
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.experiments --list    # what systems exist

# Step 4d: LLM relevance judge (resumable; see docs/01-how-it-works.md)
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.judge --judge gemma-31b --queries pilot
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.judge_pilot report   # agreement with GPT-6 ASTRA reference grades

# OpenAI pilots: set OPENAI_API_KEY in .env first (never commit a key)
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.judge --judge openai-nano --queries human --max-calls 1
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.judge --judge openai-mini --queries human --max-calls 1
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.embedding_pilot       # offline token/cost preflight
# Add --run only within the $0.25 total embedding-pilot budget, not for a full-corpus run
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.openai_full          # full-corpus cache/budget preflight
# openai_full --run uses a separate $1.25 lifetime cap; completed inputs are cached
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.graded                # score cached dev labels only
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.graded --label --max-calls 20  # selected judge, resumable
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.graded --judge openai-mini --label --max-calls 20  # selected GPT-5.4 mini, shared token cap

# Run the tests
.\.venv\Scripts\python.exe -m pytest -q
```

### Quick offline experiment loop

```powershell
# Cached rankings only: 38 lexical/semantic fusion settings, no API calls
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.fusion_experiment
# Frozen-baseline segment comparisons and concrete failure evidence, no API calls
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.failure_analysis
# Pre-promotion review of 55%/c30 versus original, 75%/c100 and 60%/c60; no API calls
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.fusion_review
# Score-based fusion, top-rank bonuses and top-500 retrieval; cached embeddings, no API calls
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.score_fusion_experiment
# Persist all 24 finer rank-fusion settings for the unified scorecard, no API calls
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.fusion_refinement
```

## Folders

```
arxiv_search/       the system (settings in config.py)
tests/              automatic checks
experiments/        one-off measurements
docs/               explanations
data/               eval queries, labels and results are in git; downloads, corpus and embeddings are rebuilt locally
```
