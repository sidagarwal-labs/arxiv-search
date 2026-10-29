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
| 3. Search | 🔨 In progress | Rank papers for a query using word matching (BM25), meaning (embeddings), or both. BM25 baseline ✅. |
| 4. Test | 🔨 In progress | Score each search method on 400 test queries whose right answers we know. Scoring code ✅; test queries ✅; results table ✅. |
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
8. [`text.py`](../arxiv_search/search/text.py) and [`bm25.py`](../arxiv_search/search/bm25.py):
   step 3 keyword search, with [`test_bm25.py`](../tests/test_bm25.py) as a worked example
9. [`experiments.py`](../arxiv_search/evaluate/experiments.py): runs a search system on the
   test queries and updates the [results table](05-results.md)

---

## Experimental reranking: what new information does it use?

An embedding model represents a paper without knowing the user's current query.
A cross-encoder instead reads the query **together with** the paper text.
It can learn interactions between their words: for example, matching the
language but missing the requested application should not be enough.
This is a hypothesis about why it may help, not a guarantee of better results.

[`rerank.py`](../arxiv_search/search/rerank.py) only orders a supplied pool.
[`cross_encoder_experiment.py`](../arxiv_search/evaluate/cross_encoder_experiment.py)
supplies the frozen dev candidates, runs MiniLM locally on CPU, and caches
one raw logit per query-paper pair. It never uses the source paper ID or
relevance grades to choose candidates or compute scores.

- **Rerank top10:** only changes order. It cannot change Precision@10 or
  source Recall@10/20 because membership stays the same.
- **Rerank top30/100 or a retriever union:** can replace a weak top10 result.
  New selected papers may lack labels, so graded quality cannot yet be
  compared fairly even when source-paper recall is measurable.
- **Blend ranks:** gives the baseline and cross-encoder a vote without
  pretending raw neural logits and BM25/cosine scores share a scale.

The model sees title plus abstract, not full text or author names. Its512-token
pair limit can cut off abstract endings; the experiment records how often.
The model and tokenizer are revision-pinned; changing texts, candidates or
settings cannot silently reuse old scores. Cached reruns make later rank
comparisons cheap, but do not make first-time inference free of compute.

Run `python -m arxiv_search.evaluate.cross_encoder_experiment`.
Results, missing judgments, runtime and case evidence are saved under
[`data/results/cross-encoder-dev`](../data/results/cross-encoder-dev).
No model API, new embeddings API, or relevance-labeling API is called.
These are experiments; the approved live-search direction remains Decision36.

### OpenAI-large field experiment

[`openai_field_experiment.py`](../arxiv_search/evaluate/openai_field_experiment.py)
tests whether separating title and abstract helps our selected embedding model.
It is **not a cross-encoder**: it compares independent query/title/abstract vectors.
The first experiment used GTE locally; this follow-up keeps the model fixed
to OpenAI-large,3072 dimensions, including the combined-text control.

Only7,644 papers already present in the frozen baseline100 candidates are
embedded in two fields. Existing query and combined-document caches are
read-only. A field score is
`t*cos(query,title)+(1-t)*cos(query,abstract)`, with title shares25/50/75%.
One setting uses the original combined-document cosine instead. Each recipe
reorders either the existing top10 or all100 candidates, with stable baseline
tie order. This isolates field separation without a conservative baseline-score
blend hiding changes. No candidate can enter from outside the frozen100.

The CLI defaults to dry-run. `python -m arxiv_search.evaluate.openai_field_experiment`
validates inputs/caches and reports cost; add `--run` only for approved calls.
Its$0.30 task ceiling shares the existing$1.25 lifetime embedding ledger.
Failed or unknown requests keep their reservation; there are no automatic retries.
Caches bind exact texts, model and dimensions, and completed experiments refuse
automatic paid repair of missing vectors.

No relevance judging is performed. The top10-only recipes have complete grades;
top100 recipes can select unjudged papers and must keep graded conclusions
provisional. Compare separate fields against the same-depth, same-model combined
control, as well as against Decision36. A gain over pure combined cosine alone
is not necessarily a gain over the stronger lexical/semantic working baseline.

[`openai_field_hybrid.py`](../arxiv_search/evaluate/openai_field_hybrid.py)
is a separate cached-score follow-up that keeps lexical evidence:
25% normalized BM25 +75% normalized semantic field score. It uses the same
top10/top100 scopes and combined-text controls. Each score is normalized by
its candidate100 maximum; absent saved lexical-top500 scores contribute zero.
This module has no embedding or judging execution path. Its plan is saved
after observing the pure-semantic outcomes, so it is exploratory, not a second
independent confirmation. Run `python -m arxiv_search.evaluate.openai_field_hybrid`.

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

## Step 3a: Keyword search, BM25 (`search/text.py`, `search/bm25.py`)

**What it does:** ranks papers by how well their words match the query's words.

**1. Turn text into words** (`text.py`). The baseline does the least possible:

```
tokenize("State-of-the-art RAG, SO(3).")  →  ["state", "of", "the", "art", "rag", "so", "3"]
```

Lowercase, then split on anything that isn't a letter or digit. No stopword removal, no
stemming ("models" ≠ "model"). Each paper is `title + " " + abstract` (`paper_text`).

**Options we tested** (Decisions 28–30; results in [Findings](03-findings.md) §9):

| Option | Function | Example |
|---|---|---|
| `drop_stopwords` | `tokenize` | "how is the retrieval" → `how`, `retrieval` (Lucene's 33 words) |
| `stem` | `tokenize` | "recommendations" → `recommend`, "retrieval" → `retriev` (Snowball) |
| `add_stems` (exact+stems) | `tokenize` | "models" → `models`, `~model`: exact match scores twice |
| `authors` | `paper_text` | adds "Ada Lovelace Alan Turing" to the searched text |
| `title_repeats=2` | `paper_text` | the title is written twice, so its words count double |

**Our best BM25** uses exact+stems + authors + title×2 with k1 = 0.8.

---

**2. Build an inverted index** (`bm25.py`, built once, ~3 s for 23,304 papers). For every word,
the papers containing it and how many times:

```
"retrieval" → papers [12, 40, 977, ...], counts [3, 1, 2, ...]
```

**3. Score a query.** Each query word found in a paper earns it `idf × tf_part` points:

| Part | Meaning | Effect |
|---|---|---|
| **idf** = ln(1 + (N − df + 0.5) / (df + 0.5)) | How rare the word is (df = papers containing it) | "the" ≈ 0 points, "bm25" ≈ 8 |
| **tf_part** = tf × (k1 + 1) / (tf + k1 × (1 − b + b × length / avg length)) | How often it's in this paper, with two brakes | |
| **k1** = 1.2 | Saturation brake | the 2nd mention counts less than the 1st |
| **b** = 0.75 | Length brake | long papers' counts are scaled down |

A worked example with three tiny papers is in the docstring of `test_bm25_hand_worked_example`.
Ties keep corpus order, so results are identical every run.

**Why our own code** (~70 lines) instead of a library: so every number can be explained. A test
checks it gives exactly the same scores as the `rank_bm25` library.

---

## Step 3b: Meaning search, embeddings (`search/dense.py`)

**What it does:** ranks papers by how close their *meaning* is to the query, even with no
words in common. That's what BM25 can't do (paraphrase queries scored 0.13).

**1. Embed every paper once.** An embedding model reads `title + abstract` and outputs 384
numbers (a vector). Papers about similar things get vectors pointing in similar directions.
Recorded runs took about 30–118 minutes per model on the laptop CPU, so the vectors are
saved to `data/embeddings/<model>.npy` and reused (not in git; rebuildable).
Laptop load and standby can distort elapsed times; these are not controlled benchmarks.

**2. Embed the query** with the same model (milliseconds).

**3. Score = cosine similarity** (1 = same direction; 0 = perpendicular, not a calibrated
relevance probability). Vectors are scaled to length 1, so this is a single matrix
multiplication: `paper_vectors @ query_vector`.

**The four models** (Decision 31), all output 384 numbers and were selected as small
candidates for cheap query serving (Decision 25). Production serving still needs testing:

| Key | Model | Reads up to | Text put in front |
|---|---|---|---|
| `minilm` | all-MiniLM-L6-v2 (from class) | 256 tokens: **cuts off 68% of papers** | — |
| `bge-small` | BAAI/bge-small-en-v1.5 | 512 tokens | query: "Represent this sentence for searching relevant passages: " |
| `e5-small` | intfloat/e5-small-v2 | 512 tokens | query: "query: ", paper: "passage: " |
| `gte-small` | thenlper/gte-small | 512 tokens | — |

The prefixes follow each model's retrieval recipe. They live in `config.EMBEDDING_MODELS`.
We explicitly use float32 on CPU: GTE's default float16 was about 15 times slower in a
small timing check on this laptop. See [Findings, section 10](03-findings.md#10-four-small-embedding-models-decision-31).

**Where is the vector store?** For experiments we do not use a hosted vector
database: NumPy arrays on disk plus paper-ID metadata are the store. `DenseIndex`
loads them and does exact cosine search in memory. Document embeddings are
computed once and cached offline; new queries still need the same embedding
model (local for GTE/BGE, an API call for OpenAI). The planned hosted website uses
Postgres/pgvector; that migration has not happened yet.

**Paid embedding pilot** (`evaluate/embedding_pilot.py`): compare OpenAI small and
large with cached GTE/BGE on the same seeded 2,000-paper subset and all 100 dev
queries. Every dev source is retained. The CLI defaults to token/cost estimates
without calling OpenAI; `--run` permits calls under the approved $0.25 lifetime
cap, shared across both models. It uses exact `cl100k_base` token counts,
transactional SQLite reservations before requests and no automatic paid retries.
Unknown failures retain their reservations. OpenAI vectors are cached locally
under `data/embeddings/openai-pilot/`; scores, subset manifest and sanitized usage
summaries go to `data/results/embedding-pilot/`.

The smaller corpus has fewer distractors, so its scores must not be mixed with
the full-corpus table. The results page has a separate pilot section. OpenAI
uses the full title and abstract while GTE/BGE keep their 512-token input limit;
this is an end-to-end configuration comparison, not a pure model-size ablation.
Prices checked against OpenAI's model pages: small $0.02 and large $0.13 per
million input tokens. Recheck prices before future runs.

---

## Step 3c: Hybrid search (`search/hybrid.py`)

BM25 matches exact wording; embeddings match meaning. We retrieve the top 100 from
each, score their union, then keep the best 100. There are no new paper embeddings.

- **RRF:** a rank r contributes `weight / (c + r)`. A small c emphasizes the first
  few positions; a larger c makes nearby ranks more alike.
- **Linear rank blend:** a rank r contributes `weight * (101 - r) / 100`.
- A paper missing from a list earns zero from that list. The embedding weight is
  0.25, 0.5 or 0.75; BM25 gets the remainder. Ties keep BM25 order first, followed
  by embedding-only papers in their original order.

`python -m arxiv_search.evaluate.experiments --hybrid-grid` compares 24 combinations
using saved dev rankings, without loading models. Missing or incomplete source runs
raise an error. Reported times are **fusion only**, not end-to-end search time.
The normal named-system runner builds both retrievers and uses the same fusion
function for live queries, including new ones. For example:

```powershell
python -m arxiv_search.evaluate.experiments "hybrid-gte-small+rrf+w=0.5+c=10"
```

We have not run the held-out test queries yet.

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

Here **dev means development/validation**, not a subset of a training split.
We do not currently train or fine-tune an embedding model, so there is no
supervised training set and no third, separate validation split. All 23,304
papers are searchable in both evaluations; the 400 queries, not the corpus,
are split into dev and test. The 100 human judgments calibrate the judge on
dev queries; they are pair labels, not another 100-query split. If we later
train a reranker, define a training/validation protocol using development data
or new labels without consuming the frozen 300-query test set.

---

## Step 4c: Experiments (`evaluate/experiments.py`)

**What it does:** runs one search system on the test queries and adds it to one big table,
[docs/05-results.md](05-results.md), so every technique is compared the same way.

Each system is a `System` in `SYSTEMS`: a function that builds an index and returns a search
function, plus a description. The 24 BM25 combinations are generated from `BM25_GRID`.

| Command | Does |
|---|---|
| `python -m arxiv_search.evaluate.experiments bm25-baseline` | run one system on dev |
| `python -m arxiv_search.evaluate.experiments "bm25*"` | run every system matching a pattern |
| `python -m arxiv_search.evaluate.experiments --tune <system>` | try a 6 × 6 grid of k1/b on dev |
| `python -m arxiv_search.evaluate.experiments --list` | list all systems |

For each system it:

1. builds the index (timed → "Build s")
2. searches each of the 100 **dev** queries, keeping the top 100 papers (timed → "ms/query")
3. scores them with `metrics.py`
4. saves everything to `data/results/dev/` and rebuilds the table

Every row is compared with `bm25-baseline` **on the same queries** (Δ MRR with a 95% interval).
Add `--split test` only for the finalists.

| File in `data/results/<split>/` | Contents |
|---|---|
| `<system>.run.json` | Top 100 arxiv_ids per query |
| `<system>.scores.jsonl` | One row per query: Recall@k, MRR@10, query type, specificity, category |
| `<system>.info.json` | Description, settings, build seconds, ms per query |
| `tuning/<system>.json` | MRR@10 for every k1/b pair tried |

**The results page** has the main table (best first), the **factor analysis** (each BM25
technique's effect averaged over all settings of the others, with a paired 95% interval),
**interaction tables** (does one technique's effect depend on another?), and k1/b grids.

---

## Step 4d: LLM relevance judge (`evaluate/judge.py`, `judge_prompts.py`, `judge_pilot.py`)

**Why:** Recall and MRR only credit the one paper a query was written from. Many other papers
can be just as good an answer, especially for questions and broad topics. A judge grades every
paper a system returns, so we can compute nDCG@10 (Decision 33).

**What it does:**

1. **Pool** (`pool`): for each query, take the top 10 of the 5 main systems in
   `JUDGE_POOL_SYSTEMS` and remove duplicates (~23 papers per query).
2. **Grade** (`judge_query`): papers are shuffled with a fixed seed and
   labelled P1…Pn, so the judge never sees rank, system or which paper is the "source". It
   sees the search text, title, first 10 authors and the full abstract, and for each paper
   writes a short reason, then a grade: **2** = highly relevant (what the user is looking for;
   for a search describing one specific paper, only that paper), **1** = partly relevant,
   **0** = not relevant (rubric in `judge_prompts.py`). A bad answer (missing or extra label)
   is retried up to 3 times, with the validation error and exact allowed labels
   included in the retry prompt. Gemini judge batches are capped at 10 papers;
   local batches remain capped at 30. Each completed batch is cached immediately.
   This reduces the amount lost to an invalid reply without guessing label mappings.
3. **Cache** (`judge_pairs`): each grade is appended to `data/eval/judgments/<judge>.jsonl`,
   keyed by (judge, rubric version, search text, paper text). Re-runs skip cached pairs;
   editing the rubric changes its version, so everything is re-graded.

**API reliability:** `llm.py` owns bounded retries; SDK retries are disabled to
avoid nested retry loops. It respects both numeric/HTTP-date `Retry-After`
headers and fractional Google `retryDelay` seconds, never shortening exponential
backoff. Daily quota errors stop immediately. UTC timestamps, a local request
ID, prompt character count, HTTP status, attempt duration and token usage
are logged without prompts, keys, response bodies or headers. Successful
labels retain the attempt history and retry-wait time in usage metadata.
The local ID correlates our logs; it is not a Google support request ID.
No automatic model fallback, rubric change or abstract truncation is used.
The current process must be restarted to load wrapper changes; saved labels
are reused and at most an in-flight batch needs to be repeated.

OpenAI calibration also supports `openai-4.1-mini` and `openai-4o-mini`
alongside the original `openai-mini` (GPT-5.4 mini) and nano. All use the
same persistent shared mini-pool ledger; there is no automatic daily reset.
Calibrate with `judge --judge <key> --queries human`. Then
`graded --judge <key> --label --max-calls 20` labels the expanded dev pool
with that one model, not a mixture with Gemma. Human overrides still apply.
The published graded snapshot identifies the selected judge and model;
raw per-model caches remain separate even when the displayed report changes.
The original judge CLI remains restricted to human-only OpenAI pilots;
expanded labeling is explicit through the graded CLI.

**The pilot** (`judge_pilot.py`) picks which judge to trust: 12 dev queries (3 per type),
266 pairs (including source-paper checks, also used by the pilot CLI). Sid grades
100 of them blind in `human_grades.xlsx` (25 per type), then the report
compares each judge with Sid: exact agreement, Cohen's kappa (quadratic), agreement on
relevant-vs-not, a confusion table, seconds per call, and how often source papers got a 2.

| Command | Does |
|---|---|
| `python -m arxiv_search.evaluate.judge_pilot sheet` | write the blind human grading sheet (won't overwrite) |
| `python -m arxiv_search.evaluate.judge --judge gemma-31b --queries pilot` | grade the pilot pairs (resumable) |
| `python -m arxiv_search.evaluate.judge --judge qwen2.5-7b --queries pilot` | same, with the local model via Ollama |
| `python -m arxiv_search.evaluate.judge_pilot report` | agreement report → `data/eval/judge_pilot/report.md` |
| `python -m arxiv_search.evaluate.judge --judge <key> --queries dev --max-calls 20` | grade all dev pairs, at most 20 calls this run |

**OpenAI calibration:** `--judge openai-nano` and `--judge openai-mini` select
`gpt-5.4-nano` and `gpt-5.4-mini`. `--queries human` grades only the pairs with
completed human labels, never sending the human grades, notes or reasoning.
Only the query, paper title/authors/abstract and rubric go to the API.
These runs use batches of up to 10, strict JSON output, no reasoning budget,
bounded retries and `OPENAI_API_KEY` from the local `.env`.

`openai_api.py` reserves tokens transactionally in a local SQLite ledger before
every attempt, then reconciles successful requests against actual input/output
usage. Unknown failures retain their conservative reservations. Mini/nano share
one allowance; the configured ceilings are 1.5 million mini/nano and 150,000 large
tokens with additional reservation headroom. There is deliberately **no automatic
reset**: limits remain conservative across restarts and dates, pending verification
of account reset rules. Only the four explicitly approved mini/nano models are enabled.
Other projects' usage is not visible to this ledger, so verify account usage too.

Run `judge_pilot report`, then `evaluate.experiments` to refresh both the detailed
agreement report and the central results page. Retrieval scores and judge
agreement remain separate: a better judge does not itself improve search ranking.

**Full-dev graded retrieval** (`evaluate/graded.py`): pools the top 10 from the
five original finalists plus OpenAI large dense/hybrid results, all on the same
100 dev queries. It defaults to GPT-5.4 mini (`DEFAULT_JUDGE = "openai-mini"`),
reuses only that judge's current-rubric labels, skips API calls for
human-graded pairs and applies human labels last (including grade 0). The default
command only scores cached labels. `--label --max-calls 20` grades up to 20
successful batches then publishes progress; API/validation failures also publish
the saved partial coverage before propagating the error.

Outputs in `data/results/graded-dev/` include the merged label snapshot, rubric
version, human-workbook fingerprint, ranking fingerprints, per-query graded
scores and a report. nDCG uses linear gains from the shared pool, P@10 treats
grades 1/2 as relevant, and judged@10 shows coverage. Undefined nDCG queries are
counted explicitly. Until every compared top 10 is judged, the table is marked
provisional and must not be used to select a winner. Source-paper metrics remain
unchanged in the original retrieval table. Adding pool papers can change ideal
DCG, so rebuild all graded rows together rather than comparing stale snapshots.
Once coverage is complete, the report adds planned paired nDCG/P@10 differences
for OpenAI hybrid against GTE hybrid, OpenAI dense and BM25. Queries are aligned
by ID, and undefined nDCG values are omitted explicitly. These exploratory
intervals describe query uncertainty conditional on labels, not judge accuracy;
they are not multiple-testing-adjusted.

**Cached fusion loop** (`evaluate/fusion_experiment.py`): the default CLI makes
no network calls. It combines saved BM25/OpenAI top-100 rankings into 38
candidates: two pure endpoints plus three mixed semantic weights (0.25, 0.5,
0.75), four methods/settings (RRF c=10/60/100 or linear rank fusion), and
three candidate depths (20/50/100). It also includes the frozen baseline and
original pool systems as controls. All systems use a common expanded label
snapshot; original baseline files are not overwritten. Outputs include config/
ranking fingerprints, source and graded per-query metrics, overall/type paired
differences and win/tie/regression counts when coverage is complete.
An explicit `--label --max-calls N` can fill missing pairs using the existing
shared token ledger. After budget clarification, Sid approved the 333-pair
batch and an effective cumulative cap of 1,600,000 tokens, without resetting
usage. No automatic cap increase or daily reset is allowed.

`evaluate/failure_analysis.py` is also offline. It verifies the frozen snapshot's
rubric, workbook and ranking fingerprints, then saves segment comparisons and
largest gains/regressions with full abstracts, ranks, grades and label provenance.

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
| `JUDGES` | Gemma 4 31B (API) and Qwen 2.5 7B (local), piloted | LLMs that grade whether a result is relevant (Decision 33) |
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
| `RUN_DEPTH` | 100 | Papers kept per query in experiments |
| `BASELINE_SYSTEM` | `bm25-baseline` | The row every other system is compared with |
| `EMBEDDING_MODELS` | minilm, bge-small, e5-small, gte-small | Local embedding models and their prefixes |
| `EMBEDDING_BATCH_SIZE` | 32 | Papers embedded at a time |

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

**`test_bm25.py`** (7 tests): the tokenizer on tricky text, with stopwords, stemming and
exact+stems; the authors and title×2 options; BM25 scores for three tiny papers worked out by
hand; unknown words and ties; and identical scores to the `rank_bm25` library.

**`test_dense.py`** (3 tests): dense search ranks tiny 2-number vectors by cosine similarity;
ties keep corpus order; every model in config has its prefixes. (No model is downloaded.)

**`test_hybrid.py`** (13 tests): hand-worked RRF and linear scores, weights, ties,
candidate limits, empty inputs, invalid settings and duplicates; live/offline fusion
agreement; rejection of incomplete saved rankings. No models are downloaded.

**`test_judge.py`** (6 tests, with a fake LLM): Cohen's kappa on a hand-worked example;
shuffled labels map back to the right papers and the prompt hides rank/source; bad answers
are rejected and retried; cached pairs are skipped but re-graded if the paper text changes,
and judges don't share caches; `--max-calls` stops and a re-run resumes.

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
**Exceptions:** `data/eval/queries.jsonl`, `labels.json` and `split.json` *are* in git, because
an LLM wouldn't write the same 400 queries twice, and every score we report must use the same
test set. `data/results/` is in git too: it's small, and the results table is rebuilt from it.
`data/eval/judgments/` (LLM grades) and `data/eval/judge_pilot/` (human grades and the
agreement report) are in git as well: neither an LLM nor a person would grade exactly the
same way twice.

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
├── results/                      STEP 4c OUTPUT: every search system's rankings + scores
│   ├── dev/                      bm25-baseline.run.json, .scores.jsonl, .info.json, ...
│   └── test/                     finalists only
├── embeddings/                   STEP 3b OUTPUT: <model>.npy (23,304 × 384 numbers) + <model>.json
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
│   ├── search/                   step 3
│   │   ├── text.py               text → words (tokenize), paper → title + abstract
│   │   ├── bm25.py               keyword search (BM25)
│   │   ├── dense.py              meaning search (embeddings + cosine similarity)
│   │   └── hybrid.py             combine BM25 and embedding rankings
│   └── evaluate/                 step 4
│       ├── metrics.py            Recall, MRR, nDCG + error bars
│       ├── prompts.py            the exact instructions given to the query-writing LLM
│       ├── make_queries.py       step 4b: writes + checks 400 test queries → data/eval/
│       ├── split.py              100 dev / 300 test split → data/eval/split.json
│       └── experiments.py        step 4c: run a search system → data/results/, docs/05-results.md
├── tests/                        automatic checks
├── experiments/                  one-off measurement scripts
├── pyproject.toml                project name + which libraries to install
├── .env.example                  template for secrets (copy it to .env)
└── .gitignore                    keeps data/, .env, .venv/ out of git
```

Future steps get their own folder inside `arxiv_search/` when we build them: `rag/`, `api/`.

**Things you may see that aren't ours:** `.venv/` (installed libraries), `__pycache__/`,
`.pytest_cache/` and `arxiv_search.egg-info/` are generated automatically by Python. They're not
in git and are hidden in the VS Code Explorer.
