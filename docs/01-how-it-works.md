# How It Works

A plain-English tour of the system: what each step does, which file does it, and what it
produces. Read this before the code.

## The big picture

```
 1. DOWNLOAD        2. CLEAN UP          3. SEARCH              4. TEST
 ───────────        ──────────           ──────────             ──────────
 arXiv website  →   one tidy file    →   find papers for    →   did we find the
 (raw pages)        of 23,304 papers     a user's query         right papers?
```

| Step | Status | In one sentence |
|---|---|---|
| 1. Download | ✅ Done | Ask arXiv for every paper in three categories from the last year, and save its answers untouched. |
| 2. Clean up | ✅ Done | Turn those saved pages into one row per paper, and keep only the papers we want. |
| 3. Search | ⏳ Next | Rank papers for a query using word matching (BM25), meaning (embeddings), or both. |
| 4. Test | ⏳ Next | Score each search method on 400 test queries whose right answers we know. |
| 5. Answer (RAG) | Later | Send the top papers to an LLM and have it answer the question, citing them. |
| 6. Website | Later | A public page where anyone can search. |

## Recommended reading order

1. [`config.py`](../arxiv_search/config.py): every setting in one place
2. [`download.py`](../arxiv_search/ingest/download.py): step 1
3. [`parse.py`](../arxiv_search/ingest/parse.py): step 2a
4. [`clean.py`](../arxiv_search/ingest/clean.py): step 2b
5. [`test_ingest.py`](../tests/test_ingest.py): small examples showing exactly what steps 1–2 do

---

## Step 1: Download (`download.py`)

**What it does:** asks arXiv for paper information, one page at a time, and saves each page as-is.

**How talking to arXiv works.** arXiv offers a service called OAI-PMH, which lets you copy its
paper information in bulk. The conversation goes like this:

```
us:     "Give me papers in cs.IR changed since 2025-10-20."
arXiv:  "Here are ~1,300. Ask again with this bookmark for more: abc123"
us:     "Give me more, bookmark abc123."
arXiv:  "Here are ~1,300 more. Bookmark: def456"
 ...
arXiv:  "Here are the last few. No bookmark."   ← that means we're finished
```

**Rules we follow:**
- **Wait 3 seconds between requests.** arXiv asks for this.
- **If arXiv replies "busy" (error 503),** wait as long as it says and try again.
- **After every page, save the bookmark** to `state.json`. If the program stops halfway,
  running it again carries on from the last page instead of starting over.

**Key functions:**

| Function | Job |
|---|---|
| `category_to_set_spec` | Converts `cs.IR` into arXiv's name for it, `cs:cs:IR` |
| `fetch_page` | Makes one request, retrying when arXiv says it's busy |
| `parse_page_control` | Reads the bookmark (or error) out of a page |
| `download_category` | The loop: fetch → save → update bookmark → wait 3 s → repeat |

**Input:** nothing (it calls the internet).
**Output:** `data/raw/<date>/` (see [the data folder](#the-data-folder) below).

**Run it:** `python -m arxiv_search.ingest.download` (took about 20 minutes).

---

## Step 2a: Translate (`parse.py`)

**What it does:** reads the saved pages and turns each paper into a simple Python dictionary.
It does **not** decide which papers to keep. That's step 2b.

One paper in the raw XML looks like this (shortened):

```xml
<id>2308.09419</id>
<created>2026-10-03</created>
<authors><author><keyname>Zhou</keyname><forenames>Peilin</forenames></author>...</authors>
<title>Attention Calibration for Transformer-based
       Sequential Recommendation</title>
<categories>cs.IR</categories>
<abstract>Transformer-based sequential recommendation ...</abstract>
```

…and after `parse.py` it becomes:

```python
{
  "arxiv_id": "2308.09419",
  "title": "Attention Calibration for Transformer-based Sequential Recommendation",
  "abstract": "Transformer-based sequential recommendation ...",
  "authors": ["Peilin Zhou", ...],
  "primary_category": "cs.IR",       # arXiv always lists the main category first
  "categories": ["cs.IR"],
  "submitted_month": "2023-08",      # read from the ID: 23 = 2023, 08 = August
  "created": "2026-10-03",           # NOT the first-submission date (see below)
  "url": "https://arxiv.org/abs/2308.09419",
  ...
}
```

**Why we read the date from the ID.** The `<created>` field above says 2026, but this paper was
first submitted in **August 2023**; 2026 was when it was last revised. The arXiv ID always starts
with the year and month of first submission (`2308` = 2023-08), so we trust that instead.

**Key functions:**

| Function | Job |
|---|---|
| `clean_text` | Collapses line breaks and extra spaces into single spaces |
| `submitted_month_from_id` | `"2308.09419"` → `"2023-08"` |
| `parse_record` | One XML paper → one dictionary (returns `None` for deleted papers) |
| `parse_page` | Every paper on one saved page |
| `iter_snapshot_records` | Every paper on every saved page |

---

## Step 2b: Filter and sample (`clean.py`)

**What it does:** takes every parsed paper and keeps only the ones we want, in four filters. It
records how many papers survive each filter.

| Filter | Rule | Papers left |
|---|---|---|
| Start | Everything downloaded, duplicates removed (`deduplicate`) | 102,008 |
| 1. Right category | Main category is cs.IR, cs.CL or cs.LG (drops e.g. a cs.CV paper cross-listed to cs.IR) | 68,643 |
| 2. Recent | First submitted in the last 12 months (by ID month) | 56,367 |
| 3. Real abstract | Not withdrawn, and abstract has at least 20 words (`is_withdrawn_or_stub`) | 56,278 |
| 4. Balance | At most 10,000 per category, chosen at random with a fixed seed (`stratified_sample`) | **23,304** |

**Why duplicates exist:** the same paper can show up in more than one category's download, for
example a cs.CL paper cross-listed to cs.LG.

The random pick uses a **fixed seed** (6188), so running it again picks exactly the same papers.

**Output:** `data/processed/corpus.jsonl`, which **every later step reads**.

**Run it:** `python -m arxiv_search.ingest.clean` (a few seconds).

---

## Settings (`config.py`)

Every number that changes the results lives here, so nothing important is hidden inside the code.

| Setting | Value | Meaning |
|---|---|---|
| `CATEGORIES` | cs.IR, cs.CL, cs.LG | Which arXiv areas we include |
| `WINDOW_DAYS` | 365 | How far back to go |
| `MAX_PER_CATEGORY` | 10,000 | Balancing cap |
| `MIN_ABSTRACT_WORDS` | 20 | Shorter abstracts are treated as stubs |
| `RANDOM_SEED` | 6188 | Makes random sampling repeatable |
| `REQUEST_DELAY_SECONDS` | 3 | Politeness delay for arXiv |
| `QUERY_WRITER_MODEL` | `gemini-3.6-flash` | LLM that writes test queries |
| `JUDGE_MODEL` | `gemma-4-31b-it` | LLM that grades whether a result is relevant |
| `RAG_MODEL_CANDIDATES` | two Gemini models | LLMs we'll compare for writing answers |
| `HOSTED_EMBEDDING_MODEL` | `gemini-embedding-2` (768 numbers) | A cloud embedding model to compare with local ones |

---

## Tests (`tests/test_ingest.py`)

Tests are small examples that check the code does what we say. They use a tiny made-up XML page,
so they run in under a second without the internet.

| Test | What it proves |
|---|---|
| `test_set_spec` | `cs.IR` is converted to arXiv's naming, `cs:cs:IR` |
| `test_submitted_month_from_id` | `2308.09419` → `2023-08` |
| `test_parse_page_extracts_fields_and_skips_deleted` | Fields are read correctly and deleted papers are skipped |
| `test_resumption_token_and_errors` | The bookmark and the "no results" reply are both understood |
| `test_clean_corpus_filters` | Duplicates, wrong categories, old papers, stubs and withdrawn papers are all removed |
| `test_stratified_sample_caps_and_is_deterministic` | The cap works, and the same seed gives the same papers |

**Run them:** `python -m pytest -q`

---

## Measurement scripts (`experiments/`)

These aren't part of the search system. They're one-off experiments we ran to make design
decisions. Their results are in [Findings](03-findings.md).

| Script | Question it answers |
|---|---|
| `measure_fulltext.py` | How much longer is a full paper than its abstract? (downloads 45 sample papers) |
| `estimate_costs.py` | How long and how much storage would full-text search need? (also times embedding speed on this laptop) |

---

## The data folder

`data/` is **not** in git: it's big, and anyone can rebuild it by running the steps above.

```
data/
├── raw/                          STEP 1 OUTPUT: arXiv's answers, never edited
│   └── 2026-10-20/               one folder per download date
│       ├── manifest.json         what we asked for (categories, dates, URL)
│       ├── download.log          what the download printed while running
│       ├── cs.IR/
│       │   ├── page_0001.xml     one saved page (~1,300 papers each)
│       │   ├── ...               (5 pages)
│       │   └── state.json        bookmark + "done" flag, used to resume
│       ├── cs.CL/                (27 pages)
│       └── cs.LG/                (56 pages)
├── processed/                    STEP 2 OUTPUT
│   ├── corpus.jsonl              23,304 papers, one per line (42 MB) ← used by everything after
│   └── corpus_stats.json         paper counts after each filter
└── experiments/                  results of the scripts in experiments/
```

## The code folder

```
arxiv-search/
├── README.md                     start here
├── docs/                         plain-English explanations (this folder)
├── arxiv_search/                 the actual system (a Python package)
│   ├── config.py                 all settings
│   └── ingest/                   steps 1–2
│       ├── download.py           step 1:  arXiv → data/raw/
│       ├── parse.py              step 2a: XML → Python dicts
│       └── clean.py              step 2b: filter + sample → data/processed/corpus.jsonl
├── tests/                        automatic checks
├── experiments/                  one-off measurement scripts
├── pyproject.toml                project name + which libraries to install
├── .env.example                  template for secrets (copy it to .env)
└── .gitignore                    keeps data/, .env, .venv/ out of git
```

Future steps get their own folder inside `arxiv_search/` when we build them: `search/`,
`evaluate/`, `rag/`, `api/`.

**Things you may see that aren't ours:** `.venv/` (installed libraries), `__pycache__/`,
`.pytest_cache/` and `arxiv_search.egg-info/` are generated automatically by Python. They're not
in git and are hidden in the VS Code Explorer.
