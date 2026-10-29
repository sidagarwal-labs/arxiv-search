# arXiv Search

A search engine and question-answering system for recent arXiv papers in **cs.IR, cs.CL and
cs.LG**. Built for DSBA 6188.

Every design choice is decided by **measuring** it on a test set of queries, not by guessing.

## How it works, in one picture

```
 1. DOWNLOAD     →   2. CLEAN UP     →   3. SEARCH        →   4. TEST          →   5. ANSWER
 arXiv catalog       23,304 papers       BM25 + embeddings     400 test queries     LLM answers
 (raw pages)         (corpus.jsonl)      find top papers       score each method    using top papers
```

## Progress

- [x] 1. Download papers from arXiv
- [x] 2. Clean up into one file of 23,304 papers
- [x] 3. Search: BM25 baseline → BM25 variants → four embedding models → hybrid (dev MRR: 0.635)
- [ ] 4. Test: scoring metrics ✅, 400 test queries ✅, results table ✅, LLM relevance judge (built; piloting vs. human grades)
- [ ] 5. Answer: RAG with an LLM
- [ ] 6. Website: database, API, web page, deploy

## Read more

| Doc | What's in it |
|---|---|
| [How it works](docs/01-how-it-works.md) | Every step and every file in plain English, plus the folder layout |
| [Decisions](docs/02-decisions.md) | Every choice we made and why |
| [Findings](docs/03-findings.md) | Measurements behind the decisions |
| [Glossary](docs/04-glossary.md) | What BM25, embedding, MRR, etc. mean |
| [Results](docs/05-results.md) | One table comparing every search system we've tried |

## Run it

```powershell
# One-time setup
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,experiments]"   # experiments = embedding models
copy .env.example .env        # then paste your Gemini API key into .env

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
# Add --run only for the approved $0.25 total embedding pilot, not a full-corpus run

# Run the tests
.\.venv\Scripts\python.exe -m pytest -q
```

## Folders

```
arxiv_search/       the system (settings in config.py)
tests/              automatic checks
experiments/        one-off measurements
docs/               explanations
data/               downloaded + processed data (not in git; rebuilt by the steps above)
```
