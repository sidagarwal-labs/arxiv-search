# arXiv Search

Hybrid search over **23,304 recent arXiv papers** in information retrieval (cs.IR),
computation and language (cs.CL) and machine learning (cs.LG). Built for DSBA 6188
in UNC Charlotte's M.S. in Data Science and Business Analytics.

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
  100 human labels, it reached **77% exact agreement** and **0.802 quadratic
  kappa**, with no opposite (0 vs. 2) grades.
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

## Current working baseline

GPT-5.4 mini grades results offline; it is not part of the search path.

| Component | Selected configuration | Status |
|---|---|---|
| Corpus | 23,304 arXiv papers; title + abstract | Indexed with local models and OpenAI large |
| Keyword retrieval | BM25 with exact terms + stems, authors and title weighted x2; k1=0.8, b=0.75; no stopword removal | Measured on full corpus |
| Embeddings | OpenAI `text-embedding-3-large`, 3,072 dimensions; normalized vectors | Full-corpus vectors cached; $0.7439 under a separate $1.25 cap |
| Hybrid selection + ordering | RRF (55% semantic / 45% lexical, c=30, depth 100) selects the top 10; max-normalized score fusion (75% semantic / 25% lexical, depth 500) reorders those ten; the tail is unchanged | Selected in [Decision 36](docs/02-decisions.md#36-recall-preserving-shortlist-score-baseline-promoted-2026-10-29); deterministic, with no learned or LLM reranker |
| Relevance judge | OpenAI `gpt-5.4-mini`; blind 0/1/2 pair labels; human labels override | Selected 2026-10-29; the 3,294-pair dev pool is covered for finalists; some older exploratory rows may be provisional; fresh human validation deferred |
| Evaluation | 100 dev / 300 held-out test queries; source-paper MRR and recall, plus graded nDCG and judgment coverage | Full dev evaluation complete; held-out test untouched |
| Vector storage | Offline NumPy arrays + paper-ID metadata; exact cosine search | Hosted Postgres/pgvector planned, not deployed |
| Reranker / RAG | Local MiniLM cross-encoder, title/abstract field scores and a 20-query LLM reranker pilot tested; RAG not implemented | Experiments only; not baseline components |

## Development results

Selected milestones from the [hill-climbing charts](docs/06-charts.md). Every row
is rescored against the same frozen 3,294-pair label snapshot: 100 development
queries over all 23,304 papers.

| Milestone | nDCG@10 | Source MRR@10 | Source R@10 |
|---|---|---|---|
| Tuned BM25 | 0.5187 | 0.5687 | 71% |
| GTE-small embeddings | 0.5811 | 0.5254 | 71% |
| BM25 + GTE-small hybrid | 0.6312 | 0.6350 | 80% |
| BM25 + OpenAI-large hybrid | 0.6604 | 0.6534 | 84% |
| RRF, 55% semantic, c=30 | 0.7064 | 0.6459 | 86% |
| **Shortlist + score reordering (current)** | **0.7176** | **0.6967** | **86%** |

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
- **LLM reranker pilot:** on 20 queries, top-10 nDCG improved from 0.7055 to
  0.7194, but deeper results were not fully judged; it is not a baseline.

The [experiment log](docs/07-experiment-log.md) has the full history, budgets and
caveats.

## Status

- [x] Download and clean 23,304 papers
- [x] Keyword, embedding and hybrid search, tuned on development queries
- [x] Evaluation tooling: 400 queries, metrics, results table, calibrated LLM judge and full development evaluation
- [ ] Final held-out test on 300 queries
- [ ] Fresh human validation of judge labels
- [ ] Retrieval-augmented answers with an LLM
- [ ] Web app: database, API, web page and deployment

Next quality targets are better task and constraint matching and deeper candidate
selection: 133 known highly relevant query-paper pairs currently rank in positions 11-50.

## Read more

| Doc | What's in it |
|---|---|
| [How it works](docs/01-how-it-works.md) | Every step and every file in plain English, plus the folder layout |
| [Decisions](docs/02-decisions.md) | Every choice and why it was made |
| [Findings](docs/03-findings.md) | Measurements behind the decisions |
| [Glossary](docs/04-glossary.md) | What BM25, embedding, MRR, etc. mean |
| [Results](docs/05-results.md) | One table comparing every search system tried |
| [Charts](docs/06-charts.md) | Hill-climbing milestones, latest leaderboard leaders and measured remaining headroom |
| [Experiment log](docs/07-experiment-log.md) | Detailed experiment history, budgets and caveats |

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
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.judge_pilot report   # agreement with human grades

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
