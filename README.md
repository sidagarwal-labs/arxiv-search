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

## Current working baseline (selected 2026-10-28)

This is our chosen direction, not yet a fully measured end-to-end configuration.
GPT-5.4 mini grades results offline; it is not part of the live search path.

| Component | Selected configuration | Status |
|---|---|---|
| Corpus | 23,304 arXiv papers; title + abstract | Indexed with local models and OpenAI large |
| Keyword retrieval | BM25 exact+stems, authors, title x2; k1=0.8, b=0.75; no stopword removal | Measured on full corpus |
| Embeddings | OpenAI `text-embedding-3-large`, 3,072 dimensions; normalized vectors | Full-corpus vectors cached; new run cost $0.7439 under separate $1.25 cap |
| Hybrid fusion | Equal-weight RRF, c=10, top 100 from each retriever | Full-corpus dev measured; improvement over GTE uncertain |
| Relevance judge | OpenAI `gpt-5.4-mini`; blind 0/1/2 pair labels; human labels override | Selected 2026-10-29; all 2,857 dev pool pairs covered; fresh-human validation deferred |
| Evaluation | 100 dev / 300 held-out test queries; source-paper MRR/recall plus graded nDCG and judgment coverage | Full-dev evaluation complete; held-out test untouched |
| Vector storage | Offline NumPy arrays + paper-ID metadata; exact cosine search | Hosted Postgres/pgvector planned, not deployed |
| Reranker / RAG | None yet | Next phases, not baseline components |

### Best measured scores (keep benchmark scopes separate)

| Measurement | Configuration and scope | Scores |
|---|---|---|
| Full-corpus retrieval reference | BM25 + **GTE-small**, RRF 0.5/0.5, c=10; 23,304 papers, 100 dev queries | MRR@10 **0.635** [0.56, 0.72]; R@1 **0.54**, R@10 **0.80**, R@20 **0.84**; one warm run **26.4 ms/query** |
| Selected embedding pilot | OpenAI large **alone**; 2,000 papers, same 100 dev queries | MRR@10 **0.844** [0.784, 0.902]; R@10 **0.95**, R@20 **0.98**; embedding cost **$0.0701** including queries |
| Selected judge calibration | GPT-5.4 mini vs. 100 human-labeled pairs from 12 dev searches | Exact agreement **77%**; quadratic kappa **0.802**; relevant/not agreement **84%**; **0** opposite 0-vs-2 errors |
| New full-corpus baseline | BM25 + **OpenAI large**, equal-weight RRF c=10; 23,304 papers, 100 dev queries | MRR@10 **0.653** [0.572, 0.737]; R@1 **0.56**, R@10 **0.84**, R@20 **0.90** |
| Complete graded dev baseline | Same OpenAI hybrid; GPT-5.4 mini with 100 human overrides, all seven systems' top 10 fully judged | nDCG@10 **0.686** [0.659, 0.712]; P@10 **0.633** [0.595, 0.673]; judged@10 **100%** |
| Full-corpus semantic retrieval | OpenAI large alone; same corpus and dev queries | MRR@10 **0.599** [0.518, 0.679]; R@10 **0.82**, R@20 **0.88** |

The pilot has fewer distractors and cannot be compared directly with the full-corpus
reference. Judge agreement measures label quality, not retrieval quality. These are dev
and calibration results, not final held-out scores. Keep the original `bm25-baseline`
unchanged as the historical control.

OpenAI hybrid minus GTE hybrid is **+0.018 MRR** (paired 95% CI
**[-0.028, +0.065]**): promising, not an established gain. Cached query-vector
search took 5.3 ms dense / 8.0 ms hybrid; these exclude the embedding API and
are not live serving latency. The seven-system graded dev pool contains
2,857 unique query-paper pairs, now fully covered. OpenAI hybrid minus GTE
hybrid is **+0.030 nDCG** [0.007, 0.055] under these labels; the gain over
OpenAI dense alone is uncertain (+0.018 [-0.011, 0.046]).

Full experiment tables, confidence intervals, usage and caveats: [Results](docs/05-results.md).
Selection rationale and next milestones: [Decision 34](docs/02-decisions.md#34-working-baseline-selected-2026-10-28).
The label-collection UI is deferred; the existing 100 human labels remain our
calibration set. A separate reranker comes after full-corpus retrieval and graded
evaluation, not before.

## Progress

- [x] 1. Download papers from arXiv
- [x] 2. Clean up into one file of 23,304 papers
- [x] 3. Search: BM25 baseline → BM25 variants → local/OpenAI embeddings → hybrid (dev MRR: 0.653)
- [ ] 4. Test: scoring metrics ✅, 400 test queries ✅, results table ✅, GPT-5.4 mini selected ✅, full-dev graded evaluation ✅; fresh-human validation deferred; final held-out test untouched
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
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.openai_full          # full-corpus cache/budget preflight
# openai_full --run uses a separate approved $1.25 lifetime cap; completed inputs are cached
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.graded                # score cached dev labels only
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.graded --label --max-calls 20  # selected judge, resumable
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.graded --judge openai-mini --label --max-calls 20  # selected GPT-5.4 mini, shared token cap

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
