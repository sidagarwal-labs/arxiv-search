# Findings

Measurements we took to make decisions. Each section names the decision it supports
(see [Decisions](02-decisions.md)).

---

## 1. The corpus (download of 2026-10-20)

**23,304 papers.**

| Category | Papers eligible | Papers kept |
|---|---|---|
| cs.LG | 33,613 | 10,000 (random sample) |
| cs.CL | 19,361 | 10,000 (random sample) |
| cs.IR | 3,304 | 3,304 (all of them) |

What we learned along the way:
- **33%** of downloaded papers had a main category outside our three (cross-listed papers).
- **18%** of the rest were old papers that had only been *revised* recently → decision #9.
- **64%** of kept papers have a Creative Commons license; **36%** use arXiv's standard license,
  which doesn't allow republishing the full text → decision #18.
- Authors per paper: median 4, top 10% have 9 or more, maximum 3,435 (one huge collaboration).
  The website should show only the first few authors.
- arXiv's date filter works on "last modified", not "first submitted", so October 2025 papers
  that were never revised are under-counted.

---

## 2. How long is title + abstract? (decision #12)

Measured with real model tokenizers on all 23,304 papers.

| | Tokens |
|---|---|
| Median | 287 |
| 90% of papers are under | 381 |
| 99% of papers are under | 466 |
| Longest | 782 |

| Model | Max tokens it reads | Papers cut off |
|---|---|---|
| all-MiniLM-L6-v2 (from class) | 256 | **67.8%** |
| BGE-small, E5-small | 512 | 0.2% |

---

## 3. Full paper vs. abstract (decision #18)

45 sample papers, downloaded as HTML from arxiv.org
([`measure_fulltext.py`](../experiments/measure_fulltext.py)).

| Per paper | Median |
|---|---|
| Title + abstract | 290 tokens |
| Full paper body | 8,590 tokens (**~32× longer**) |
| Chunks needed (512 tokens each) | 20 |
| Words in the body that never appear in the abstract | 94% |

Cost of each option ([`estimate_costs.py`](../experiments/estimate_costs.py), embedding speed timed
on this laptop):

| Option | Vectors | Download | Embed time | Storage | Fits free DB (500 MB)? |
|---|---|---|---|---|---|
| A. Abstracts (current) | 23,304 | done | ~17 min | ~137 MB | ✅ |
| B. Full text, all papers | ~450,000 | ~20 h | ~15 h | ~3 GB | ❌ |
| C. Full text, cs.IR reusable subset | ~39,000 | ~1.7 h | ~1.3 h | ~256 MB | ✅ |

---

## 4. BM25 vs. embeddings, quick probe (decision #19)

30 probe queries on cs.IR (3,304 papers), 10 of each type. "Found" = the right paper is in
the top 10.

| Query type | BM25 found | Embeddings (BGE-small) found |
|---|---|---|
| Author name | 10 / 10 | 1 / 10 |
| Rare acronym (e.g. "ANNS") | 7 / 10 | 4 / 10 |
| Topic description | 10 / 10 | 10 / 10 |

*Caveat:* author names weren't in the text we embedded, so the author row is unfair to
embeddings. It still shows we need word matching for names.

---

## 5. Which Gemini models work on the free tier (checked 2026-10-20)

| Model | Works? | Notes |
|---|---|---|
| `gemini-3.8-flash`, `3.7-flash`, `3.6-flash`, `3.5-flash` | ✅ | ~1.5 s per reply |
| `gemini-3.5-flash-lite`, `3.1-flash-lite` | ✅ | ~0.6 s per reply |
| `gemma-4-31b-it`, `gemma-4-26b-a4b-it` | ✅ | Google's open models |
| `gemini-embedding-2`, `gemini-embedding-001` | ✅ | 3,072 numbers by default; we'll use 768 |
| `gemini-3.1-pro-preview`, `gemini-4-argon` | ❌ | No free quota |
| `gemini-2.5-*` | ❌ | Retired |

The API doesn't report rate limits, so our code waits and retries whenever it gets a
"too many requests" (429) error.

---

## 6. How precise will our scores be? (decisions #16, #21)

Bootstrap 95% intervals for a Recall of 0.60, computed with our own `bootstrap_ci`:

| Queries in the group | Example | Interval | ± |
|---|---|---|---|
| 33 | one category × one query type | 0.42–0.79 | 0.18 |
| 100 | one query type | 0.50–0.70 | 0.10 |
| 133 | one category | 0.51–0.68 | 0.09 |
| 400 | everything | 0.55–0.65 | 0.05 |

**What this means:** overall, per-category and per-type numbers are useful. A single
category × type cell (33 queries) is too noisy on its own. When comparing two systems, the paired
comparison is tighter than these intervals, because both systems face the same hard and easy
queries.

---

## 7. Making the 400 test queries (decisions #22–#24, run of 2026-10-21)

**Choosing the writer model.**
- `gemini-3.6-flash`: wrote good queries (~3 s per call), but its free tier allows only **20 calls
  a day** (Google's 429 message: `GenerateRequestsPerDayPerProjectPerModel-FreeTier, limit 20`).
- `gemma-4-31b-it`: large free quota. It needs the exact JSON shape given to it (plain "JSON
  mode" returned a 500 error), and it sometimes wraps the JSON in ``` fences, which `llm.py` strips.

**Pilots (4 calls each) before the full run:**

| Pilot | Change | Accepted | Main problem left |
|---|---|---|---|
| 1 | first prompt | 7 / 12 | keyword reshuffled the title; paraphrase said "This paper…" |
| 2 | + reshuffle and "this paper" checks | 9 / 16 | paraphrases reused paper words; questions copied method names |
| 3 | Gemma; retry says why it was rejected | 11 / 16 | paraphrases still reused ordinary paper words |
| Full run, first try | — | 30 / 48 (62%) | paraphrase only 39% |
| **Full run, final** | + BAD/GOOD paraphrase example | **400 / 483 (83%)** | keyword queries shrink the title |

**Final run, by type:**

| Type | Accepted / attempts | Median words | Median overlap |
|---|---|---|---|
| keyword (specific / broad) | 100 / 144 (69%) | 5 / 4 | 1.00 / 0.75 |
| question (specific / broad) | 100 / 116 (86%) | 14.5 / 13 | 0.62 / 0.50 |
| paraphrase | 100 / 115 (87%) | 18 | 0.25 |
| known_item | 100 / 108 (93%) | 5 | 0.75 |

Split: 300 specific / 100 broad; cs.IR 136, cs.CL 132, cs.LG 132.

**Why attempts were rejected** (83 rejected; one attempt can fail several checks):

| Reason | Count |
|---|---|
| Mostly the title's words rearranged (mostly keyword) | 38 |
| Copies 4+ words in a row from the abstract | 23 |
| Copies 4+ words in a row from the title | 17 |
| Paraphrase reuses more than half its words from the paper | 13 |
| Wrong length | 9 |
| Model skipped a paper | 4 |

**What this means.**
- Specific keyword queries use almost only the paper's own words (median overlap 1.0), so
  they'll favor BM25. Paraphrases (0.25) are the real test of embeddings. That's why every
  query keeps its `overlap`.
- **Reliability:** 121 calls hit 154 server errors (77 × 503 "busy", 77 × 500 "internal"). Two
  long outages stopped the run, and a closed laptop lid cut the connection once. Resuming lost
  nothing. Total time was about 3 hours, almost all of it waiting.

Sample queries:

| Type | Specificity | Query |
|---|---|---|
| keyword | broad | video recommendation testing framework |
| question | broad | How can we improve the accuracy of reranking documents for a retrieval augmented generation system? |
| paraphrase | specific | maximizing income for power conversion tools and cells by using actual device behavior in Nordic power exchanges |
| known_item | specific | Shukla generative recommendation hierarchical supervision |

---

## 8. BM25 baseline on dev (decision #27)

Full table: [Results](05-results.md). 100 dev queries, BM25 with no preprocessing.
Build 3.2 s, 1.5 ms per query.

| Overall | R@1 | R@5 | R@10 | R@20 | MRR@10 |
|---|---|---|---|---|---|
| bm25-baseline | 0.43 | 0.61 | 0.67 | 0.70 | 0.50 [0.42–0.59] |

**By query type** (source paper in top 20 / MRR@10):

| Type | Specific | Broad |
|---|---|---|
| keyword | 12/12, 0.90 | 85%, 0.31 |
| question | 92%, 0.63 | 46%, 0.21 |
| paraphrase | 20%, 0.10 | — |
| known_item | 25/25, 0.91 | — |

**By word overlap with the source paper:**

| Overlap | Queries | Found in top 20 | MRR@10 |
|---|---|---|---|
| under 1/3 | 22 | **0%** | 0.00 |
| 1/3 to 2/3 | 29 | 72% | 0.37 |
| over 2/3 | 49 | 100% | 0.80 |

**What this means.**
- BM25 is excellent when the user types the paper's words (keyword, known_item) and **blind when
  they don't**: not one low-overlap query found its paper in the top 20. That's the gap
  embeddings must close.
- Example misses: "managing delivery drivers who work for several different apps…" for *Partially
  Observable Learning for Multi-Platform Dispatch Optimization*; "an automated system that decides
  if an image is actually helpful or harmful for verifying a claim" for *Adaptive Multimodal
  Fact-Checking*. Same meaning, different words.
- Broad queries score low partly because many other papers are right answers too; the LLM judge
  will tell us how much.
- Stemming may help a little in the middle band ("recommendations" vs "recommendation") but can't
  fix the bottom band.

---

## 9. BM25 techniques, full grid (decisions #28–#30)

All 24 combinations on dev, plus k1/b tuning. Full tables: [Results](05-results.md).

**Each technique's average effect** (averaged over every setting of the other three; Δ MRR@10
with a 95% interval):

| Technique | Δ MRR@10 | Who gains | Who loses |
|---|---|---|---|
| Stopwords | −0.000 [−0.01, +0.01] | nobody | nobody |
| Stemming (replace words) | +0.006 [−0.04, +0.05] | paraphrase +0.07, keyword +0.06 | known_item −0.08 |
| **exact+stems** | **+0.025 [+0.01, +0.05]** | keyword +0.05, paraphrase +0.03, question +0.03 | (known_item −0.01) |
| **Authors** | **+0.030 [+0.01, +0.05]** | known_item +0.12 | — |
| **Title ×2** | **+0.014 [+0.00, +0.02]** | known_item +0.03 | — |

**The interaction that matters** (mean MRR@10):

| Stemming ↓ / authors → | off | on |
|---|---|---|
| none | 0.510 | 0.528 |
| stem | 0.503 | 0.548 |
| exact+stems | 0.531 | 0.556 |

Stemming alone is slightly harmful, but with authors it's helpful: authors put back the exact
matches that known-item queries lost.

**Tuning k1/b** (top 3 grid systems): all three prefer k1 = 0.8 over the default 1.2 (+0.01).
b between 0.5 and 1.0 changes MRR by under 0.01, which is noise on 100 queries.

**Best BM25:** `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75`, MRR@10 **0.569** vs 0.501
(Δ +0.067 [+0.03, +0.10]). Known-item is now perfect (1.000), keyword 0.71.

**What this means.**
- Text tricks fix *word-form* mismatches ("recommendations" vs "recommend") and add missing
  fields (authors). That's worth about +0.07.
- **Paraphrase is still 0.13** and R@20 stays at ~0.72: no BM25 setting finds papers described
  in different words. That's the job for embeddings next.
- Build times in the table vary 2–3× between identical runs (laptop load), so treat them as
  rough.

---

## 10. Four small embedding models (decision #31)

All four embed title + abstract without our BM25 preprocessing, then rank by cosine
similarity. Model-specific prefixes still apply. Same 23,304 papers and 100 dev queries;
the 300 test queries remain untouched. Full results: [Results](05-results.md).

| System | MRR@10 | R@20 | Paraphrase MRR | Known-item MRR | Low-overlap R@20 |
|---|---|---|---|---|---|
| Best BM25 | 0.569 | 0.71 | 0.13 | 1.00 | 0.05 |
| GTE-small | 0.525 | 0.78 | 0.36 | 0.63 | 0.59 |
| BGE-small | 0.506 | 0.79 | 0.28 | 0.67 | 0.59 |
| E5-small | 0.485 | 0.75 | 0.26 | 0.63 | 0.41 |
| MiniLM | 0.407 | 0.68 | 0.26 | 0.55 | 0.45 |

Low-overlap means the query's recorded word overlap with its source paper is below 0.34.
These scores measure finding the source paper, not every relevant paper.

**What changed.**
- BM25 still has the highest overall MRR, especially for exact titles and author names.
- Embeddings find many more papers when users describe them in different words.
- GTE's paired difference from best BM25 is -0.043 (95% interval -0.13 to +0.05);
  BGE's is -0.063 (-0.16 to +0.03). Neither interval establishes a clear difference,
  and neither proves equivalence.
- An oracle that succeeds whenever *either* system finds the source paper in its top 20
  reaches 0.87 for BM25 + GTE and 0.88 for BM25 + BGE. This motivates trying hybrid
  rankings; it is **not a measured hybrid score**, nor a promise that a fused top 20
  will retain those papers.

**Timing lessons.**
- GTE loaded in float16 by default. A small CPU check took about 89 seconds for 64
  papers, versus 6 seconds in float32. We now explicitly load all four models in
  float32; MiniLM, BGE and E5 were already using it.
- Recorded paper-embedding times: MiniLM 1,814 s, E5 2,701 s, GTE 2,975 s,
  BGE 7,077 s (about 118 minutes).
- The original BGE run included laptop standby and its timing was discarded. The
  replacement produced identical per-query scores. Its elapsed time is still a
  rough laptop measurement, not a controlled speed benchmark or production estimate.
- Vectors are cached locally. These runs use no paid embedding API. Production
  still needs the same model available to embed incoming queries.

**Next experiment to decide together:** combine BM25's exact matching with GTE/BGE's
meaning matching, tune on dev, and reserve test for the finalists.

---

## 11. Hybrid rank fusion (decision #32)

We compared 24 settings: two embedding models, three embedding weights, and four
rank formulas (RRF c = 10/60/100, or linear). Input: saved top-100 rankings from
best BM25 and each dense model. No new embeddings or API calls.
All rows and group winners are in [Results](05-results.md).

| System | MRR@10 | R@20 | Keyword | Question | Paraphrase | Known-item |
|---|---|---|---|---|---|---|
| Best BM25 | 0.569 | 0.71 | 0.710 | 0.432 | 0.132 | 1.000 |
| GTE alone | 0.525 | 0.78 | 0.688 | 0.417 | 0.364 | 0.633 |
| BM25 + GTE, equal RRF c=10 | **0.635** | 0.84 | 0.728 | 0.518 | 0.321 | 0.973 |
| BM25 + BGE, equal RRF c=10 | 0.602 | **0.85** | 0.709 | 0.536 | 0.232 | 0.930 |
| BM25 + GTE, equal linear | 0.603 | 0.81 | 0.707 | 0.531 | 0.255 | 0.920 |

**What we learned.**
- The best dev MRR is GTE + equal-weight RRF, c=10: +0.066 over best BM25
  (paired 95% interval +0.014 to +0.121). This interval does not account for
  choosing the best of 24 settings, so it is encouraging dev evidence, not
  independent confirmation.
- RRF c=10 with equal weights wins within both embedding models. More smoothing
  or more embedding weight does not automatically help.
- The blend recovers much of GTE's paraphrase benefit without giving up most of
  BM25's known-item strength. It does not preserve every individual advantage:
  GTE alone still has higher paraphrase MRR.
- BGE's best-MRR blend has slightly higher R@20 than GTE's (0.85 vs 0.84),
  which may matter for reranking even though its MRR is lower.
- Linear rank blending is competitive but no better on dev. We have not yet
  compared normalized raw-score fusion.
- An actual live run of the winning configuration reproduced all 100 offline
  rankings exactly, using cached paper vectors and freshly embedded queries.
  It measured 26.4 ms/query after initialization (69 s build/model setup).
  This is one warm laptop run, not a production latency guarantee. Other grid
  rows still report fusion-only timings.

**Experiment roadmap, in order.**
1. Human-review about 60 evaluation queries; record quality problems rather than
   quietly rewriting the benchmark after seeing system failures.
2. Choose an LLM relevance judge and check agreement with human grades. Pool and
   deduplicate candidates from finalists; measure judgment coverage before
   trusting nDCG. Budget calls and use resumable, rate-limit-aware execution.
   *Status (2026-10-28):* judge built (Decision 33); piloting Gemma 4 31B vs.
   Qwen 2.5 7B on 266 pairs against 100 blind human grades.
3. Test a small reranker on hybrid candidates: measure MRR/nDCG and latency/cost;
   try candidate depths such as 20 and 50. Retrieval recall limits what it can fix.
4. Benchmark the proposed serving environment: query embedding plus both searches
   and fusion, memory, cold starts and cost. Offline fusion timings cannot answer this.
5. Freeze finalists and settings, then evaluate on the 300 held-out queries once.
6. For RAG, measure answer correctness, citation support and appropriate abstention,
   not just whether an answer sounds fluent.

Optional follow-ups if these expose a need: adding authors to dense input, a longer
MiniLM input configuration, one stronger affordable embedding model, normalized
raw-score fusion, and full-paper chunking. Full-paper ingestion is a separate
scope expansion, not a prerequisite for validating abstract search. Its pilot design
(abstract vs. full-text chunks on ~2,000 papers, plus body-text queries graded by the
judge, weighed against cost) is under Decision 18.
