# arXiv Search — Semantic Search + RAG over arXiv (DSBA 6188)

Search and question-answering over recent arXiv papers in **cs.IR, cs.CL, and cs.LG**.
Every retrieval and generation choice is selected by measuring it against an evaluation set,
not by intuition.

## Architecture

```
arXiv OAI-PMH ──► raw XML ──► parsed records ──► corpus.jsonl
                                                     │
                     ┌───────────────────────────────┼─────────────────────────┐
                     ▼                               ▼                         ▼
              BM25 / TF-IDF index         embedding models (N)          LLM-generated eval set
                     │                               │                 (query → relevant docs)
                     └──────────► retrievers ◄───────┘                         │
                                     │                                         │
                                     ├──► experiment runner ◄──────────────────┘
                                     │       (Recall@k, MRR, nDCG@10, latency, cost)
                                     ▼
                         FastAPI: /search, /ask (RAG) ──► Next.js frontend (Vercel)
```

## Project status

- [x] **Ingestion**: OAI-PMH harvest → parsed records → stratified corpus
- [ ] Lexical baseline (BM25)
- [ ] Evaluation set (LLM-generated queries + human review)
- [ ] Metrics + experiment runner
- [ ] Embedding experiments (MiniLM vs. BGE vs. hosted)
- [ ] RAG answer generation + faithfulness evaluation
- [ ] Production store (Postgres + pgvector), FastAPI, Next.js frontend, deployment

## Quickstart

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# 1. Download raw metadata (about 10–30 min; resumable — rerun to continue)
.\.venv\Scripts\python.exe -m arxiv_search.ingest.harvest

# 2. Filter + sample into data/processed/corpus.jsonl (+ corpus_stats.json)
.\.venv\Scripts\python.exe -m arxiv_search.ingest.build_corpus

# Tests
.\.venv\Scripts\python.exe -m pytest -q
```

All tunable values (categories, window, cap, seed) live in
[`src/arxiv_search/config.py`](src/arxiv_search/config.py).

## Repository layout

```
src/arxiv_search/
  config.py              every tunable decision in one place
  ingest/
    harvest.py           stage 1: OAI-PMH → data/raw/<date>/<category>/page_*.xml
    parse.py             stage 2: XML → dicts (translation only, no filtering)
    build_corpus.py      stage 3: dedupe, filter, stratified sample → corpus.jsonl
tests/                   offline unit tests (no network)
data/                    git-ignored; fully reproducible from code
```

## Design decision log

| # | Decision | Choice | Why |
|---|----------|--------|-----|
| 1 | Corpus scope | Title + abstract of cs.IR, cs.CL, cs.LG papers | A focused domain makes evaluation queries realistic and keeps embedding/storage costs within free tiers. |
| 2 | Data source | Our own arXiv OAI-PMH harvester | We own and can explain the full ingestion layer; raw pages are frozen per harvest date for reproducibility. |
| 3 | Embedding model | Compare several (MiniLM baseline, BGE-small, a hosted model) against BM25; deploy the winner | Model choice is decided by evaluation results, not assumption. |
| 4 | LLMs | Swappable behind interfaces; chosen by experiment. The LLM that generates evaluation queries stays **fixed** and, where possible, differs from the models under test | Avoids self-preference bias (a model scoring well on queries it wrote itself). |
| 5 | Vector storage | Local NumPy/FAISS for experiments → Postgres + pgvector for production | Fast, transparent iteration locally; a managed database for the hosted app. |
| 6 | App stack | Python FastAPI backend (Render/Railway/HF Spaces) + Next.js frontend on Vercel | Vercel serverless cannot run PyTorch embedders well. |
| 7 | Repository | `arxiv-search` on GitHub | — |
| 8 | Selection rule | Primary category ∈ {cs.IR, cs.CL, cs.LG}, first submitted in the last ~12 months, stratified cap of 10k per category, seed 6188 | cs.LG is several times larger than cs.IR; the cap keeps the corpus and evaluation set balanced. Primary-only drops cross-listed papers from other fields. |
| 9 | Submission date | Month taken from the arXiv ID (`YYMM.NNNNN`), not the `<created>` field | Finding: `<created>` can hold the latest revision date (e.g. `2308.09419` showed 2026-10-03, its v3). In a 30-day test sample, 22% of papers were older papers that had been recently revised. |

| 10 | Document schema | One row per submission (latest version): `arxiv_id` (PK), `title`, `abstract`, `authors[]`, `primary_category`, `categories[]`, `submitted_month`, `updated`, `comments`, `license`, `url`, derived `embed_text`, `corpus_version` | Stable IDs anchor evaluation labels and citations. OAI-PMH exposes only the latest version, so abstracts reflect the newest revision. |
| 11 | Author search | Hybrid retriever (BM25 + vectors, fused with Reciprocal Rank Fusion) evaluated alongside pure dense search, **plus** a structured author filter | Embeddings capture meaning, not names; lexical matching handles names, acronyms and method names. |
| 12 | Embedding unit | `title + abstract` as one unit, no chunking (v1). Measure truncation with each model's real tokenizer. RAG context size (top-k, or passage-level context) is a later experiment | Title + abstract ≈ 245 tokens median, ≈ 370 at p99, so one focused passage per paper. `all-MiniLM-L6-v2` (256-token limit) likely truncates about half the abstracts; 512-token models fit nearly all. |

### Hosting data flow

Heavy steps run offline on a laptop; the cloud holds only what search needs.

| Location | Contents |
|---|---|
| Local, git-ignored | Raw XML snapshot (hundreds of MB), `corpus.jsonl`, per-model experiment vectors, evaluation runs |
| Postgres + pgvector | `papers` table with the schema above + one embedding column for the winning model (~100–150 MB) |
| FastAPI | Embeds the query with the same model, runs vector/hybrid SQL, calls the LLM for RAG |
| Next.js on Vercel | UI only; calls FastAPI |

### Data-quality notes

- OAI-PMH `from=` filters on the record *datestamp* (last modification), so it is only a
  coarse pre-filter. The real date rule is applied in `build_corpus.py`.
- A category set (e.g. `cs:cs:IR`) includes cross-listed papers whose primary category is
  elsewhere (cs.CV, cs.AI, …); these are removed by the primary-category filter.
- `corpus_stats.json` records counts per category after every filter stage.
- Author lists vary widely (median 4, p90 9, max 3,435 for one large collaboration), so the UI
  should cap displayed authors.
