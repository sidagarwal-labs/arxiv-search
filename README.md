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
- [ ] 3. Search: BM25 baseline → embeddings → hybrid
- [ ] 4. Test: test-query set + scoring metrics
- [ ] 5. Answer: RAG with an LLM
- [ ] 6. Website: database, API, web page, deploy

## Read more

| Doc | What's in it |
|---|---|
| [How it works](docs/01-how-it-works.md) | Every step and every file in plain English, plus the folder layout |
| [Decisions](docs/02-decisions.md) | Every choice we made and why |
| [Findings](docs/03-findings.md) | Measurements behind the decisions |
| [Glossary](docs/04-glossary.md) | What BM25, embedding, MRR, etc. mean |

## Run it

```powershell
# One-time setup
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
copy .env.example .env        # then paste your Gemini API key into .env

# Step 1: download (~20 min; if it stops, run again to resume)
.\.venv\Scripts\python.exe -m arxiv_search.ingest.download

# Step 2: clean up → data/processed/corpus.jsonl
.\.venv\Scripts\python.exe -m arxiv_search.ingest.clean

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
