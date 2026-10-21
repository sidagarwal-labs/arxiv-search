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
| 4. Test | 🔨 In progress | Score each search method on 400 test queries whose right answers we know. Scoring code ✅; test queries ✅. |
| 5. Answer (RAG) | Later | Send the top papers to an LLM and have it answer the question, citing them. |
| 6. Website | Later | A public page where anyone can search. |

## Recommended reading order

1. [`config.py`](../arxiv_search/config.py): every setting in one place
2. [`download.py`](../arxiv_search/ingest/download.py): step 1
3. [`parse.py`](../arxiv_search/ingest/parse.py): step 2a
4. [`clean.py`](../arxiv_search/ingest/clean.py): step 2b
5. [`test_ingest.py`](../tests/test_ingest.py): small examples showing exactly what steps 1–2 do
6. [`metrics.py`](../arxiv_search/evaluate/metrics.py): step 4 scoring, with
   [`test_metrics.py`](../tests/test_metrics.py) as worked examples
7. [`prompts.py`](../arxiv_search/evaluate/prompts.py): the exact words we send the LLM to
   write test queries, then [`make_queries.py`](../arxiv_search/evaluate/make_queries.py)

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

## Step 4: Scoring (`evaluate/metrics.py`)

**What it does:** given a search system's rankings and the right answers, it says how good the
system is, as numbers with error bars.

**Two inputs, both plain dictionaries:**

```python
run    = {"q1": ["2501.00001", "2501.00042", ...]}    # what the system returned, best first
labels = {"q1": {"2501.00042": 2, "2501.00007": 1}}   # right answers with grades 0/1/2
```

Grade 1 or 2 counts as "relevant". A query written from one paper has one label:
`{"q1": {"2501.00042": 2}}`.

**The metrics, with one worked example each.** In each example the right paper is C, and the
system returned `[A, B, C, D, E]`.

| Metric | Question it answers | Example |
|---|---|---|
| **Recall@k** (k = 1, 5, 10, 20) | Is the right paper in the top k? | @1 = 0 (missed); @5 = 1 (found) |
| **MRR@10** | How high is the first right paper? 1 ÷ rank, or 0 if below rank 10 | C at rank 3 → 1/3 = 0.33 |
| **nDCG@10** | Using grades: are the best papers at the top? 1.0 = perfect order | grades A=0, B=2, C=1 → 0.67 (worked out below) |
| **judged@10** | What share of the top 10 has a grade at all? | If under ~90%, don't trust nDCG yet |

**nDCG worked out.** Each result earns its grade ÷ log₂(rank + 1), so rank 1 gets full credit
and rank 3 gets half:

```
ours  [A=0, B=2, C=1]:  0/1 + 2/1.585 + 1/2 = 1.762
best  [B=2, C=1, A=0]:  2/1 + 1/1.585 + 0/2 = 2.631
nDCG = 1.762 / 2.631 = 0.670
```

**Error bars (bootstrap).** An average from ~33 queries could shift a lot with a different set of
queries. To measure that, we redraw the queries 1,000 times at random (some twice, some not at
all), average each draw, and keep the middle 95% of those averages. The result is reported like
`MRR 0.62 [0.57–0.67]`.

**Is system B really better than A?** `paired_diff_ci` compares the two **on the same queries**,
query by query: `B − A = +0.04 [0.01–0.07]`. If the range doesn't include 0, the win is real,
not luck.

**Key functions:**

| Function | Job |
|---|---|
| `recall_at_k`, `reciprocal_rank`, `ndcg_at_k`, `judged_at_k` | Score one query |
| `score_run` | Score every query → one row per query. A query the system returned nothing for scores 0. |
| `bootstrap_ci` | Average with a 95% interval |
| `paired_diff_ci` | Difference between two systems with a 95% interval |
| `summarize` | All averages, overall and per group (e.g. per category or query type) |

**Input:** a run and labels. **Output:** numbers; nothing is written to disk.

---

## Step 4b: Test queries (`evaluate/make_queries.py`, `evaluate/prompts.py`, `llm.py`)

**What it does:** has an LLM write 400 realistic search queries, each from one paper, so we
know the right answer to each.

**The plan (fixed before any LLM call).** 400 "slots" = 4 query types × 100. Each slot has a
category (cs.IR / cs.CL / cs.LG, taking turns) and a **specificity**:

| Type | Specific | Broad | Scored by |
|---|---|---|---|
| keyword | 50 | 50 | specific → Recall/MRR on the source paper |
| question | 50 | 50 | broad → nDCG@10 from the LLM judge |
| paraphrase | 100 | 0 | |
| known_item | 100 | 0 | |

**One call = 4 papers**, one of each type, sent with the instructions in `prompts.py`. That
means ~100 calls instead of 400, which matters on the free tier.

**Every query is checked automatically** (`check_query`). It is rejected if it:

| Check | Why |
|---|---|
| Has the wrong length for its type (keyword 2–6 words, question 6–25, paraphrase 8–30, known_item 3–12) | Real searches of that type look like this |
| Copies 4+ words in a row from the title or abstract | Real users haven't read the paper |
| Is mostly the title's words rearranged (not checked for known_item) | Same reason; people re-finding a paper *do* remember title words |
| Says "this paper", "the authors", etc. | Nobody searches like that |
| Is a paraphrase with more than half its words from the paper | Otherwise "paraphrase" just tests word matching |
| Is a known_item query with no author surname | That's what makes it known-item |
| Is a question not ending in "?" | |

**Retries.** A rejected slot is retried on the same paper, and the prompt says **why** it was
rejected (e.g. which words were reused). After 2 failures the slot gets a different paper.

**Resume.** Every attempt is saved the moment it comes back, so stopping (daily limit, Google
outage, laptop sleep) loses nothing: run the same command again. The script refuses to mix
queries made with different prompt wordings (`prompt_version`).

**`llm.py`** is the one place that calls Google. It waits 6 s between calls, retries on
"busy" errors (429/500/503) waiting 10 s, 20 s, 40 s…, re-asks if the JSON comes back broken,
and stops cleanly on a daily limit.

**Output** (in `data/eval/`):

| File | Contents |
|---|---|
| `queries.jsonl` | The 400 accepted queries: `query_id`, `query`, `query_type`, `specificity`, `category`, `source_arxiv_id`, `overlap`, `model`, `prompt_version` |
| `attempts.jsonl` | Every attempt, accepted or not, with the reasons |
| `labels.json` | Right answers in the shape `metrics.py` expects: `{query_id: {source_arxiv_id: 2}}` |
| `run.log` | What the script printed |

**`overlap`** = share of the query's words that appear in the paper. It's saved for analysis:
we expect BM25 to win on high-overlap queries and embeddings on low-overlap ones.

**Run it:** `python -m arxiv_search.evaluate.make_queries` (needs `GEMINI_API_KEY` in `.env`;
~2–3 hours on the free tier, mostly waiting out Google's "busy" errors).

**Then split it** (`evaluate/split.py`): `python -m arxiv_search.evaluate.split` writes
`data/eval/split.json`:

| Part | Queries | Use |
|---|---|---|
| **dev** | 100 | Tuning: try BM25 settings, hybrid weights, prompts. Look at it freely. |
| **test** | 300 | Final scores only. Never tune on it. |

Each query type is exactly 25 dev / 75 test; specificity and category are within a query or
two of 1/4. The split uses the fixed seed, so it's the same every time.

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
| `QUERY_WRITER_MODEL` | `gemma-4-31b-it` | LLM that writes test queries |
| `JUDGE_MODEL` | `gemma-4-31b-it` (to be revisited) | LLM that grades whether a result is relevant |
| `RAG_MODEL_CANDIDATES` | two Gemini models | LLMs we'll compare for writing answers |
| `HOSTED_EMBEDDING_MODEL` | `gemini-embedding-2` (768 numbers) | A cloud embedding model to compare with local ones |
| `RECALL_KS` | 1, 5, 10, 20 | Which top-k cutoffs Recall is reported at |
| `MRR_CUTOFF` | 10 | Right paper below rank 10 scores 0 |
| `NDCG_K` | 10 | nDCG looks at the top 10 |
| `BOOTSTRAP_SAMPLES` | 1,000 | Redraws used for error bars |
| `LLM_SECONDS_BETWEEN_CALLS` | 6 | At most 10 LLM calls a minute |
| `LLM_MAX_RETRIES` | 6 | How often to retry when Google is busy |
| `EVAL_QUERIES_PER_TYPE` | 100 | Test queries per type (× 4 types = 400) |
| `EVAL_PAPERS_PER_CALL` | 4 | Papers per LLM call |
| `EVAL_MAX_CALLS_PER_RUN` | 150 | Safety cap on calls per run |

---

## Tests (`tests/`)

Tests are small examples that check the code does what we say. They run in under a second
without the internet.

**`test_ingest.py`** (uses a tiny made-up XML page):
| Test | What it proves |
|---|---|
| `test_set_spec` | `cs.IR` is converted to arXiv's naming, `cs:cs:IR` |
| `test_submitted_month_from_id` | `2308.09419` → `2023-08` |
| `test_parse_page_extracts_fields_and_skips_deleted` | Fields are read correctly and deleted papers are skipped |
| `test_resumption_token_and_errors` | The bookmark and the "no results" reply are both understood |
| `test_clean_corpus_filters` | Duplicates, wrong categories, old papers, stubs and withdrawn papers are all removed |
| `test_stratified_sample_caps_and_is_deterministic` | The cap works, and the same seed gives the same papers |

**`test_metrics.py`** (18 tests, papers named A–E so you can check each number by hand):

| Tests | What they prove |
|---|---|
| `test_recall_*` | One answer → hit or miss; several answers → share found; grade 0 doesn't count |
| `test_reciprocal_rank*` | 1 ÷ rank; the first relevant paper counts; rank 11 scores 0 |
| `test_dcg_*`, `test_ndcg_*` | The worked example above (0.670); perfect = 1; unjudged = 0; no relevant papers → left out |
| `test_judged_at_k` | 2 of 5 graded → 0.4 |
| `test_score_run_*` | Skipping a query scores 0 rather than being ignored |
| `test_bootstrap_*`, `test_paired_*` | Intervals contain the mean, the same seed gives the same answer, a consistent +0.1 gain is detected |
| `test_summarize_groups` | Per-group averages are correct |

**`test_make_queries.py`** (16 tests, using a fake LLM so no internet or quota is needed):

| Tests | What they prove |
|---|---|
| plan tests | 400 slots, 100 per type, 300 specific / 100 broad, categories balanced |
| check tests | Each rejection rule fires on a bad example and passes a good one |
| resume test | Stopping after 3 calls and rerunning finishes the rest without redoing anything |
| retry test | A failing paper is retried with the rejection reason, then replaced |

**`test_split.py`** (3 tests): dev is exactly 100 and never overlaps test; each type is 25 dev;
specificity and category stay balanced; the split doesn't depend on file order.

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
**Exception:** `data/eval/queries.jsonl` and `labels.json` *are* in git, because an LLM wouldn't
write the same 400 queries twice, and every score we report must use the same test set.

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
├── eval/                         STEP 4b OUTPUT: test queries + right answers
│   ├── queries.jsonl             400 test queries
│   ├── attempts.jsonl            every LLM attempt, with rejection reasons
│   ├── labels.json               right answers for metrics.py
│   ├── split.json                which 100 queries are dev, which 300 are test
│   └── run.log
└── experiments/                  results of the scripts in experiments/
```

## The code folder

```
arxiv-search/
├── README.md                     start here
├── docs/                         plain-English explanations (this folder)
├── arxiv_search/                 the actual system (a Python package)
│   ├── config.py                 all settings
│   ├── llm.py                    the one place that calls Google's LLMs (free-tier safe)
│   ├── ingest/                   steps 1–2
│   │   ├── download.py           step 1:  arXiv → data/raw/
│   │   ├── parse.py              step 2a: XML → Python dicts
│   │   └── clean.py              step 2b: filter + sample → data/processed/corpus.jsonl
│   └── evaluate/                 step 4
│       ├── metrics.py            Recall, MRR, nDCG + error bars
│       ├── prompts.py            the exact instructions given to the query-writing LLM
│       ├── make_queries.py       step 4b: writes + checks 400 test queries → data/eval/
│       └── split.py              100 dev / 300 test split → data/eval/split.json
├── tests/                        automatic checks
├── experiments/                  one-off measurement scripts
├── pyproject.toml                project name + which libraries to install
├── .env.example                  template for secrets (copy it to .env)
└── .gitignore                    keeps data/, .env, .venv/ out of git
```

Future steps get their own folder inside `arxiv_search/` when we build them: `search/`,
`rag/`, `api/`.

**Things you may see that aren't ours:** `.venv/` (installed libraries), `__pycache__/`,
`.pytest_cache/` and `arxiv_search.egg-info/` are generated automatically by Python. They're not
in git and are hidden in the VS Code Explorer.
