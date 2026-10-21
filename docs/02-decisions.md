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

---

## Which LLMs

**#4 Swappable LLMs.** The model that writes test queries never changes, and is a different model
from the ones being tested.
*Why:* a model can score unfairly well on questions it wrote itself.

**#17 Google Gemini free tier**, with a model chosen for each job.

**#20 The model for each job** (all set in `config.py`):

| Job | Model |
|---|---|
| Write test queries | `gemini-3.6-flash` |
| Judge relevance | `gemma-4-31b-it` (different family from the writer) |
| Write RAG answers, rerank | compare `gemini-3.5-flash-lite` vs `gemini-3.5-flash` |
| Hosted embeddings | `gemini-embedding-2`, 768 numbers per paper |

*Limit:* Gemini and Gemma are both from Google, so bias is only partly removed. The hand check
measures how much remains.

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
