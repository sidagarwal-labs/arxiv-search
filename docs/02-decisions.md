# Decisions

Every design choice we made, in plain language. Each one says **what we chose**, **why**, and
(where we have it) **the evidence**. The numbers (#1, #2…) are the order we decided in.
Measurements behind the evidence are in [Findings](03-findings.md).

---

## What goes into the search system

**#1 Which papers.** Titles and abstracts from three arXiv categories: cs.IR (information
retrieval), cs.CL (language), cs.LG (machine learning).
*Why:* a focused topic makes test queries realistic and keeps costs inside free tiers.

**#2 Where the data comes from.** Our own downloader using arXiv's bulk service (OAI-PMH), not a
ready-made dataset.
*Why:* we can explain every step, and each download is frozen in a dated folder so results are
repeatable.

**#8 Which papers exactly.** Keep a paper if its **main** category is one of the three and it was
**first submitted in the last 12 months**. Cap each category at 10,000, picked at random with
seed 6188.
*Why:* cs.LG is several times larger than cs.IR; without the cap it would swamp the others.
Using only the main category drops papers from other fields that are merely cross-listed.

**#9 Submission date comes from the ID.** `2308.09419` → August 2023.
*Evidence:* the `<created>` field sometimes holds the date of the latest revision. In a test
sample, 22% of "new" papers were actually old papers that had just been revised.

**#10 One row per paper.** Each paper has: `arxiv_id` (unique key), `title`, `abstract`,
`authors`, `primary_category`, `categories`, `submitted_month`, `updated`, `comments`, `license`,
`url`, plus the text we embed and a corpus version.
*Why:* a stable ID lets test answers and citations always point to the same paper.
*Limit:* arXiv only gives us the newest version of each abstract.

**#13 Keep the real category sizes, balance the tests instead.** The corpus stays cs.LG 10k /
cs.CL 10k / cs.IR 3.3k, but the test set has equal queries per category.
*Why:* the corpus should look like real arXiv. Balanced tests stop cs.IR results from being
hidden inside an overall average.

**#18 Abstracts now, full papers later as an experiment.**
*Evidence:* a full paper is about 32× longer than its abstract. Indexing every full paper would
take ~20 h to download, ~15 h to embed, and ~3 GB of storage, which is over the free limit. We'll
test full text on a small, legally reusable subset: about 2,000 cs.IR papers.

*Planned pilot (agreed 2026-10-28, runs after the judge exists):*
- Same ~2,000 papers indexed two ways: abstracts only vs. full text in 512-token chunks
  (a paper scores as its best chunk). Also test a cheap middle option: abstract index, with
  full-text passages pulled only for the top 20 (at rerank / answer time).
- Our 400 queries were written from abstracts, so they favour the abstract index. We add
  ~100 queries written from paper bodies (methods, datasets, results) and score with nDCG
  from the judge, whose rubric then also shows the matching passage.
- Report quality per query type next to download time, embedding hours, storage, index size
  and ms/query. Expand to all papers only if the gain's 95% interval excludes zero and the
  middle option doesn't capture most of it.

---

## How search works

**#11 Search by meaning and by exact words.** We combine embedding search with keyword search
(BM25), and add an author filter.
*Why:* embeddings understand topics but not names or rare acronyms.

**#12 Embed each paper as one piece (title + abstract), no chunking.**
*Evidence:* title + abstract has a median of 287 tokens and a maximum of 782. MiniLM (the model
from class) reads only the first 256 tokens, so it **cuts off 68%** of our papers. BGE-small and
E5-small read 512 tokens and cut off only 0.2%.

**#19 Two-stage search.**
- **Stage 1:** find candidates using BM25 (the baseline), embeddings, or both combined.
- **Stage 2 (optional, tested later):** a reranker or LLM reorders the top results.

*Why:* stage 2 can only reorder what stage 1 found, so stage 1 has to catch the right paper.
*Evidence:* in a 30-query test, embeddings ranked the paper for "ANNS" at #1,361; BM25 ranked it
#5. For topic questions, the two were tied.

**#3 Which embedding model.** Compare several (MiniLM, BGE-small, E5-small, and Google's hosted
model) on our test set, then pick the winner.

**#5 Where vectors live.** On the laptop (NumPy files) during experiments, then in a cloud
Postgres database with pgvector for the website.

**#27 Start from a BM25 baseline with no text preprocessing, then add one technique at a time.**
- Baseline: lowercase + split on non-letters/digits; no stopwords, no stemming; title +
  abstract; standard k1 = 1.2, b = 0.75.
- Every technique (stopwords, stemming, authors, tuned k1/b, embeddings, hybrid...) becomes one
  row in [the results table](05-results.md), compared with the baseline on the same queries.
- We wrote BM25 ourselves (~70 lines, NumPy) and a test proves it matches the `rank_bm25`
  library exactly.

*Why:* without a plain baseline we can't say what each technique adds. Our own code means
every score can be explained line by line.

**#28 Which stopwords and which stemmer.** Stopwords: Lucene/Elasticsearch's 33-word English
list, written out in `text.py`. Stemmer: Snowball English via PyStemmer (the one Lucene uses).
Plus a third stemming option, **exact+stems**: keep each exact word and add its stem marked
`~` ("models" → `models`, `~model`), so an exact match earns points twice and a near match once.
*Why:* plain stemming hurt known-item queries (0.91 → 0.75) by merging rare words into common
ones ("generalization" → "general"). exact+stems keeps most of the gain without that loss.

**#29 Test BM25 techniques as a full grid, not one at a time.** Every combination of
stopwords (off/on) × stemming (none/stem/exact+stems) × authors (off/on) × title×2 (off/on) =
24 systems. Each technique's effect is averaged over all settings of the others, and two-way
tables show interactions.
*Why:* a technique's effect can depend on the others. *Evidence:* plain stemming **hurts**
without authors (0.510 → 0.503) but **helps** with them (0.528 → 0.548): author names give back
the exact matches known-item queries lost. One-at-a-time testing would have rejected it.

**#30 Our best BM25: exact+stems + authors + title×2, k1 = 0.8, b = 0.75.** Dev MRR@10 0.569,
+0.067 [+0.03, +0.10] over the baseline. k1 was tuned on dev only for the top 3 grid systems;
all three picked k1 = 0.8. b made no clear difference (±0.007), so it stays at the default.
Stopwords are left out: no effect either way.
*Why:* tuning only what is consistent across systems limits overfitting the 100 dev queries.

**#31 First embedding comparison: four small local models.** MiniLM-L6 (from class),
BGE-small, E5-small and GTE-small, each with its own query/paper prefixes, embedding title +
abstract. All output 384 numbers and are small candidates for cheap live query embedding
(Decision 25); production serving still needs testing. Paper vectors are computed once
and saved in `data/embeddings/`.
*Why:* compare practical small models for arXiv search. Training, architecture and input
limits differ, so this does not isolate a single cause of quality differences.

**#32 Compare hybrid rank blends on dev.** Best BM25 + either GTE-small or BGE-small.
Try RRF with c = 10, 60, 100 and linear rank blending, each with embedding weights
0.25, 0.5, 0.75 (24 combinations). Both inputs contribute their top 100 papers;
missing papers earn zero from that input. Break score ties by first appearance
(BM25 first, then embedding-only papers). Weight is not query-dependent.
*Why:* rank fusion avoids mixing incompatible raw score scales and reuses saved rankings.
This comparison does not test normalized raw-score fusion. Choose settings using dev
MRR@10, inspect Recall@20 and query-type trade-offs, and compare against best BM25.
The best dev row is GTE + equal-weight RRF, c = 10 (MRR 0.635); it is a candidate,
not a confirmed test winner. Offline grid timings exclude source retrieval.

---

## How we test

**#14 Four kinds of test queries, equal numbers of each:**

| Type | Example |
|---|---|
| Keyword | `contrastive retrieval dense passage` |
| Question | "How can I make dense retrievers work for new domains?" |
| Paraphrase | Same idea, but using none of the abstract's words |
| Known item | "Peilin Zhou's paper on attention calibration for recommendation" |

*Why:* each type tests a different skill, which tells us where BM25 or embeddings win.

**#15 How we know the right answer.**
1. Each query is written from one paper. That paper is the answer, which gives Recall@k and MRR.
2. For a subset, an LLM judge grades the top 10 results from every system as 0 (not relevant),
   1 (partly) or 2 (very relevant). That gives nDCG@10.

*Why:* other papers can also be good answers, and step 2 gives them credit.

**#16 400 test queries.** That's 3 categories × 4 types, about 33 per group. We'll hand-check
~60 of them.
*Why:* enough to tell systems apart, and the hand check tells us whether the queries look real
and whether the LLM judge agrees with a human.

**#22 How the test queries are made.**
- **4 papers per LLM call**, one query type each, so ~100 calls instead of 400.
  *Why:* the free tier limits calls, not words.
- **Each query is either specific or broad.** Keyword and question queries are split 50/50;
  paraphrase and known_item are always specific (300 specific, 100 broad in total).
  *Why:* real users type both. A broad query ("personalized text generation") has many right
  answers, so it's scored by nDCG@10 from the LLM judge; Recall on its one source paper is
  only a lower bound. Specific queries are scored by Recall/MRR on the source paper.

**#23 Automatic checks on every query** (listed in [How it works](01-how-it-works.md)).
- A rejected query is retried with the reason ("reused: training, game, loss…"), then the
  slot moves to a new paper after 2 failures.
- No word-overlap cap on specific keyword/question queries; instead `overlap` is saved on
  every query, so we can later show where BM25 vs. embeddings win.
- known_item is exempt from the "title words rearranged" check: people re-finding a paper
  really do remember title words.
- Paraphrases may reuse at most 50% of their words from the paper. We kept 50% and instead
  added a worked BAD/GOOD example to the prompt.
  *Evidence:* paraphrase acceptance rose from 39% to 84% (see [Findings](03-findings.md)).

**#24 Gemma writes the test queries, not Gemini Flash.**
*Evidence:* Gemini 3.6 Flash's free tier allows only **20 calls per day**; we need ~130–170.
`gemma-4-31b-it` has a much larger free quota and wrote realistic queries in the pilot.
*Cost:* the judge was going to be Gemma to differ from the writer; we revisit the judge choice
(e.g. a local Qwen model, or a Gemini model) when we build it.

**#26 Split the queries: 100 dev / 300 test.** Tune settings (BM25 parameters, hybrid
weights, prompts) only on dev; report final scores only on test. Balanced by type,
specificity and category, with a fixed seed.
*Why:* if we tuned on the queries we report, scores would look better than the system really
is. 300 test queries still give ±0.06 error bars overall (see [Findings](03-findings.md) §6).
Every experiment runs on dev; only the finalists are run once on test (Decision 27).

**#21 How we score.**

| Choice | Picked | Alternative we rejected |
|---|---|---|
| Recall cutoffs | k = 1, 5, 10, 20 | — k=20 shows whether a reranker *could* fix the order |
| MRR cutoff | MRR@10: below rank 10 scores 0 | Full MRR (rank 500 still earns 0.002) |
| nDCG gain | Linear: grade 2 is worth 2× grade 1 | Exponential (2^grade − 1, worth 3×) |
| Unjudged papers | Count as 0, and report % judged next to nDCG | Skip them ("condensed" nDCG) |
| Uncertainty | 95% bootstrap intervals on every number, paired comparison between systems | Plain averages |

*Why:* MRR@10 matches what a user sees and is the standard (MS MARCO). Linear gain is simpler to
explain, and with only 3 grades it rarely changes which system wins. Counting unjudged papers as 0
is standard (TREC); the % judged shows when that is unfair. With ~33 queries per group, error bars
are needed to tell a real win from noise.

**#33 An LLM judge grades (search, paper) pairs 0/1/2, checked against human grades.**

| Choice | Picked | Alternative we rejected |
|---|---|---|
| What is graded | One (search, paper) pair at a time, 0 / 1 / 2 | Grading a whole ranked list (can't be reused across systems) |
| Which papers | Top 10 of 5 main systems, de-duplicated (~23 per search, ~2,260 for dev) | Every system's top 10 (~4,400 pairs, mostly near-duplicates) |
| What the grader sees | Search text + title + authors (first 10) + full abstract | Title only (too little); full paper (slow, costly, and we only index abstracts) |
| Blindness | No rank, no system name, no "source paper" flag; papers shuffled and labelled P1…Pn | Showing the ranked list (graders favour rank 1) |
| Calls | One call per search, each paper graded on its own, reason (≤ 20 words) before grade | One call per pair (~23× more calls) |
| Judge | Pilot Gemma 4 31B (API) vs. Qwen 2.5 7B (local) on the same 266 pairs, pick by agreement with Sid's 100 blind human grades | Picking a judge without measuring it |
| Re-use | Grades cached by (judge, rubric version, search text, paper text); human grades override LLM grades | Re-grading every run |

*Why:* grading pairs once means every system — including future rerankers and OpenAI models —
is scored from the same cached labels, and only new papers cost calls. Humans and the LLM see
the same information, so disagreements are about judgement, not information.

*How we keep the judge honest:* tune the rubric on the pilot human grades; confirm on fresh
human grades it was not tuned on (e.g. from teammates via the website); then audit a sample of
new LLM grades whenever new systems add pairs. Agreement is reported as exact agreement,
quadratic-weighted Cohen's kappa, and agreement on "relevant (1–2) vs not (0)". Sanity check:
the paper a query was written from should almost always get 2.

*Later:* RAG answers need a separate rubric (correctness, citation support, abstention).

---

## OpenAI experiment plan (2026-10-28)

The account's data-sharing offer shows two shared daily token pools: 250,000 for
listed large models and 2,500,000 for listed mini/nano models. These are aggregate
allowances across eligible models, not per-model budgets. Usage beyond the offer,
and other models, can incur charges. Embeddings are not listed in the screenshot:
treat them as paid and require a separate approved budget. Do not assume Batch API
or tool charges are covered without checking current account terms.

**Order and measurements (planned, not implemented):**

1. **Independent relevance judge:** compare `gpt-5.4-mini` and `gpt-5.4-nano` on
   the same 100 frozen human-labeled pairs. Use the same evidence and rubric as
   Gemma/Qwen. Measure exact agreement, quadratic kappa, relevant-vs-not agreement,
   0-vs-2 disagreements, per-query-type results, tokens, retries and wall time.
   Use `gpt-5.4` on the same pilot only if the smaller models leave meaningful
   quality gaps. Human grades remain authoritative; model consensus is not truth.
2. **Reranking:** compare the winning affordable OpenAI candidate against no reranker
   and a local cross-encoder, using identical hybrid candidates at depths 20 and 50.
   Measure nDCG@10, MRR@10, coverage, latency and tokens. Freeze the judge first;
   audit self-preference if the same model family judges and reranks.
3. **Embeddings, separately budgeted:** compare `text-embedding-3-small` and
   `text-embedding-3-large` with GTE/BGE, alone and with the same BM25/fusion recipe.
   Start on the same small corpus for every model, then evaluate finalists on the
   full corpus. Measure quality, dimensions/storage, build cost and query latency.
   Reduced-corpus results are not directly comparable with full-corpus scores.
   *Approved 2026-10-28:* $0.25 total for an initial 2,000-paper small/large
   comparison, including the 100 dev query embeddings. Use default 1,536/3,072
   dimensions first; compare cached GTE/BGE vectors on the exact same subset.
   Keep every dev source paper, then add seeded random distractors. No full-corpus
   OpenAI embedding run is authorized by this pilot approval.
4. **Query rewriting:** test raw queries vs. one cached rewrite or multi-query
   retrieval, especially questions and paraphrases. Measure quality and added
   latency/tokens; check that rewriting does not lose known-item identifiers.
5. **RAG answers:** after retrieval is stable, compare small-model answers grounded
   in the same retrieved evidence. Evaluate correctness, citation support,
   abstention, latency and tokens with a separate answer-level rubric.

**Budget controls required before automated runs:** dedicated project/key;
allowlisted models; persistent daily counters by allowance pool; conservative
preflight input estimates plus reserved maximum output; actual usage reconciliation;
bounded retries counted conservatively when usage is unknown; caching and resume;
concurrency-safe reservations across jobs; explicit stop rather than paid fallback.
Initial local ceilings: 150,000 large-model tokens and 1,500,000 mini/nano tokens per
day (60% of the displayed allowances). Start each model with one measured smoke call
and a small call cap. Verify the provider's reset rules before implementing resets.

These controls cannot guarantee organization-wide free usage if other projects or
clients consume the same pools. Dashboard budgets/alerts are additional safeguards,
not assumed hard spending caps. Confirm account usage before each experiment.

Data sharing is enabled for all projects in the screenshot. Prefer selecting only
the public-data research project. Send public arXiv material and synthetic queries
only, not secrets, private documents or identifiable human notes. Keep the key in
the Git-ignored `.env` as `OPENAI_API_KEY`, server-side only. Adding the key does
not start any calls; the OpenAI adapter and quota controls still need implementation.

---

## Which LLMs

**#4 Swappable LLMs.** The model that writes test queries never changes, and is a different model
from the ones being tested.
*Why:* a model can score unfairly well on questions it wrote itself.

**#17 Google Gemini free tier**, with a model chosen for each job.

**#20 The model for each job** (all set in `config.py`):

| Job | Model |
|---|---|
| Write test queries | `gemma-4-31b-it` (was `gemini-3.6-flash`; changed in #24) |
| Judge relevance | piloting `gemma-4-31b-it` vs. local `qwen2.5:7b` (#33) |
| Write RAG answers, rerank | compare `gemini-3.5-flash-lite` vs `gemini-3.5-flash` |
| Hosted embeddings | `gemini-embedding-2`, 768 numbers per paper |

*Limit:* all of these are from Google, so bias is only partly removed. The hand check
measures how much remains.

**Local models.** We have Ollama on the laptop (Snapdragon CPU only; Ollama can't use its NPU)
and a desktop with an RTX 2070 (8 GB, fits ~8B models). They're options for offline jobs like
judging, timed against the API before we choose.

---

## Hosting

**#6 Website setup.**

| Part | Runs where |
|---|---|
| Search engine (Python, FastAPI) | Render, Railway or Hugging Face Spaces |
| Web page (Next.js) | Vercel |
| Paper database (Postgres + pgvector) | Supabase or Neon free tier |

*Why:* Vercel can't run the embedding model, because PyTorch is too large for it.

**#7 Code lives on GitHub** at
[sidagarwal-labs/arxiv-search](https://github.com/sidagarwal-labs/arxiv-search).

**#25 Only test embedding models we can serve cheaply.** Offline work (embedding the 23k
papers, making the eval set) can use any machine. But every user query must be embedded **by
the same model that embedded the papers**, live, in under a second. So every model we test
must be servable in one of three ways, and we pick the way after seeing the results:

| Option | Pros | Cons |
|---|---|---|
| Hosted API (e.g. `gemini-embedding-2`) | Nothing to host | Uses our quota per search |
| Small open model on our backend (MiniLM, BGE-small, E5-small via ONNX) | No per-search cost; ~tens of ms on CPU | Needs a backend host (not Vercel) |
| Same small model in the user's browser (transformers.js) | No server cost | 20–30 MB download; slower on phones |

The vector search itself always runs on our server.
