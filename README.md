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
analysis/                one-off measurements behind design decisions (e.g. full-text cost)
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
| 12 | Embedding unit | `title + abstract` as one unit, no chunking (v1). RAG context size (top-k, or passage-level context) is a later experiment | Measured with the real tokenizers on the 23,304-paper corpus: median 287 tokens, p90 381, p99 466, max 782. `all-MiniLM-L6-v2` (256-token limit) **truncates 67.8%** of papers; BGE-small / E5-small (512) truncate 0.2%. |
| 13 | Category imbalance | Keep corpus as harvested (cs.LG 10k, cs.CL 10k, cs.IR 3.3k); balance the **evaluation set** with equal queries per category | The corpus reflects real arXiv volume; balanced evaluation stops cs.IR performance from being hidden inside an overall average. Report metrics per category as well as overall. |
| 14 | Evaluation query types | Four types in equal numbers: keyword, natural-language question, paraphrased (no copied abstract words), known-item/author | Each type tests a different retrieval ability; per-type metrics show where lexical vs. dense vs. hybrid search wins. |
| 15 | Relevance labels | One labeled source paper per query (Recall@k, MRR), plus **pooled graded relevance (0/1/2)** from an LLM judge on a subset, enabling nDCG@10 | Single-label synthetic sets mark genuinely relevant papers as misses; pooling the top-10 results of every system reduces that bias. |
| 16 | Evaluation set size | 400 queries (balanced across 3 categories × 4 types); ~60 stratified queries hand-reviewed | Enough to detect MRR differences of roughly 0.03–0.05 between systems; the hand review measures query realism and LLM-judge agreement. |
| 17 | LLM provider | Google Gemini free tier (AI Studio). The model is chosen **per task** by how much reasoning it needs; model IDs live in config. Generator and judge use different models | Free and sufficient for our volume. A single provider family risks self-preference bias, so we use different models per role and report agreement with human labels. |
| 18 | Full text | Title + abstract is the production index. Full-text chunking (512-token chunks) is a **later experiment** on cs.IR Creative Commons papers (~2,010 papers, ~39k chunks) | Measured: full text is ~32× the abstract; indexing every paper would take ~20 h to download, ~15 h to embed per model, and ~3 GB of storage (over the free tier). 36% of papers carry arXiv's standard license, which doesn't let us republish full text. The subset answers "does full text help, and for which queries?" at about 3 hours total cost. |

### Hosting data flow

Heavy steps run offline on a laptop; the cloud holds only what search needs.

| Location | Contents |
|---|---|
| Local, git-ignored | Raw XML snapshot (hundreds of MB), `corpus.jsonl`, per-model experiment vectors, evaluation runs |
| Postgres + pgvector | `papers` table with the schema above + one embedding column for the winning model (~100–150 MB) |
| FastAPI | Embeds the query with the same model, runs vector/hybrid SQL, calls the LLM for RAG |
| Next.js on Vercel | UI only; calls FastAPI |

### Full-text vs. abstract: measured cost

From [`analysis/measure_fulltext.py`](analysis/measure_fulltext.py) (45-paper stratified sample, arXiv HTML,
BGE tokenizer) and [`analysis/estimate_costs.py`](analysis/estimate_costs.py) (CPU embedding throughput
measured on the dev laptop: 22.8 abstracts/s, 8.2 chunks/s).

| Per paper | Median | p90 |
|---|---|---|
| Title + abstract tokens | 290 | 376 |
| Full body tokens (excl. references, tables, equations) | 8,590 | 12,309 |
| Body ÷ abstract | 31.7× | 44.2× |
| 512-token chunks (64 overlap) | 20 | 28 |
| Distinct body words absent from the abstract | 94% | — |

HTML was available for 96% of sampled papers (43/45).

| Scenario | Papers | Vectors | Download | Embed time per model (CPU) | DB size | Free tier (500 MB)? |
|---|---|---|---|---|---|---|
| A. Title + abstract (current) | 23,304 | 23,304 | done | ~17 min | ~137 MB | ✅ |
| B. Full text, all papers | 23,304 | ~450k | ~20 h | ~15 h | ~3.0 GB | ❌ |
| C. Full text, cs.IR CC-licensed | 2,010 | ~39k | ~1.7 h | ~1.3 h | ~256 MB | ✅ |

### Data-quality notes

- OAI-PMH `from=` filters on the record *datestamp* (last modification), so it is only a
  coarse pre-filter. The real date rule is applied in `build_corpus.py`.
- A category set (e.g. `cs:cs:IR`) includes cross-listed papers whose primary category is
  elsewhere (cs.CV, cs.AI, …); these are removed by the primary-category filter.
- `corpus_stats.json` records counts per category after every filter stage.
- **Corpus v1 (harvest 2026-10-20): 23,304 papers.** cs.LG 10,000 (sampled from 33,613),
  cs.CL 10,000 (sampled from 19,361), cs.IR 3,304 (all eligible). Of 102,008 unique harvested
  records, 33% had a primary category outside our three, and 18% of the rest were older papers
  that had been recently revised.
- The harvest `from` date filters on last modification, so papers first submitted in early
  October 2025 and never revised are under-represented in the first month (2025-10).
- Author lists vary widely (median 4, p90 9, max 3,435 for one large collaboration), so the UI
  should cap displayed authors.
