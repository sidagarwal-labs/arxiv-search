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

## 12. Relevance judge pilot (in progress, 2026-10-28)

The first shared query, "linear time long context recall", has 26 pooled papers.
These are smoke-test observations, not evidence that either judge is accurate.

| Observation | Gemma 4 31B (API) | Qwen 2.5 7B (local CPU) |
|---|---|---|
| Wall time for the first query | 729.7 s, including six API retries | 1,014.4 s |
| Grades 2 / 1 / 0 | 7 / 11 / 8 | 2 / 15 / 9 |
| Source paper grade | 2 | 2 |

The judges agree on 16 of 26 grades. This is agreement between models, not
human-validated quality. Qwen used 9,029 input tokens and 754 output tokens.
Gemma encountered HTTP 500, 429 and 503 responses before succeeding; its measured
wall time must not be reported as pure inference time.

At the evening checkpoint, Gemma had saved 71 pairs across 3 queries and Qwen
26 pairs across 1 query. Neither process was still running; the empty logs did
not establish why. Both were resumed with unbuffered output and exit-code logging.
Cached pairs are reused. The CLI's retrieval pool contains 263 pairs; the pilot
sample including source-paper sanity checks contains 266. Complete coverage of
that expanded sample must be checked before interpreting the agreement report.

Next: finish the pilot, collect the 100 blind human grades, then compare agreement
and runtime before selecting a judge. No judge has been selected yet.

**Reliability changes (2026-10-28):** a subsequent Gemma batch repeatedly returned
`es` instead of `P17` and was correctly rejected. The SDK's default retry policy
also allowed up to five attempts inside each application attempt. We now disable
nested SDK retries, set a 120-second request timeout, retry transient HTTP
408/429/500/502/503/504 responses with bounded backoff and jitter, and preserve
the existing daily-quota stop. Gemini judge batches are capped at 10 papers and
validation retries include corrective label instructions. The rubric and cache
keys stay unchanged: batch size and corrective delivery instructions can still
affect grades, so timing and quality should be rechecked rather than assumed.
API capacity failures remain outside our control. No unlimited retry loop or
paid-model fallback was added.

## 13. First OpenAI pilots (2026-10-28)

**Judging:** Gemma completed all 266 pilot pairs after the reliability changes.
OpenAI nano and mini each graded exactly the 100 frozen human-labeled pairs,
blind and with the same rubric/evidence. Neither model received human grades or
notes. The human workbook is preserved, including its original reasoning.

| Judge | Human pairs compared | Exact | Quadratic kappa | Relevant agreement | 0-vs-2 errors |
|---|---|---|---|---|---|
| Gemma 4 31B | 100 | 79% | 0.81 | 83% | 0 |
| GPT-5.4 mini | 100 | 77% | 0.80 | 84% | 0 |
| GPT-5.4 nano | 100 | 65% | 0.66 | 77% | 1 |

Mini and Gemma are close on this pilot; this is not evidence that a 2-point
difference is meaningful. Nano was less aligned with these labels, especially
known-item searches. Mini offers an independent model family from the query
writer and much lower observed latency: about 3 seconds per small batch here.
All OpenAI judge calls succeeded on their first HTTP attempt.
Nano used 38,660 total input/output tokens and mini 38,611: 77,271 combined,
about 3.1% of the displayed 2.5-million-token shared daily allowance. These are
our calls only, not a check of organization-wide usage or a billing invoice.
Fresh human labels are still needed for validation after any rubric tuning.
Qwen remains partial and must not be compared on different pair coverage.
Detailed confusion matrices and coverage are in [Results](05-results.md).

**Embeddings:** approved pilot budget was $0.25 total. We selected 2,000 papers
before looking at scores (all dev sources plus seeded random distractors) and
used the same subset and 100 dev queries for every model. Cached local paper
vectors were sliced to that subset; local query vectors were recomputed.

| Model | Dimensions | MRR@10 | R@10 | Paid embedding cost |
|---|---|---|---|---|
| GTE-small | 384 | 0.755 | 0.94 | no API charge |
| BGE-small | 384 | 0.740 | 0.92 | no API charge |
| OpenAI small | 1,536 | 0.792 | 0.93 | $0.0108 |
| OpenAI large | 3,072 | 0.844 | 0.95 | $0.0701 |

Large minus GTE: +0.088 MRR, paired 95% interval [+0.027, +0.148].
Large minus small: +0.052 [-0.006, +0.110], so a large-over-small gain is
promising but not established. Small minus GTE also has an interval crossing zero.
This is dev screening with fewer distractors, not a full-corpus or held-out result.
OpenAI reads the full title/abstract while GTE/BGE truncate at 512 tokens; do not
attribute the difference only to model capacity.

Both OpenAI embedding pilots together cost about **$0.0808** at the checked
standard prices, comfortably under the approved cap. Each used 538,881 tokens
including queries and 34 requests, with no unknown reservations. The full corpus
contains 6,259,638 `cl100k_base` tokens. At
[$0.02/million for small](https://developers.openai.com/api/docs/models/text-embedding-3-small)
and [$0.13/million for large](https://developers.openai.com/api/docs/models/text-embedding-3-large),
embedding all papers once would be about **$0.1252 / $0.8138**, respectively,
excluding future queries, retries and taxes. No full-corpus OpenAI embedding run
was made at that pilot checkpoint. Paper vectors stay offline; the paid API is needed to embed new queries.

## 14. Full-corpus OpenAI large (2026-10-29)

All 23,304 title/abstract paper vectors and 100 dev query vectors are cached.
The new job reused 2,000 pilot papers and all dev queries; the pilot cache and
budget were left unchanged. A separate transactional lifetime ledger records
365 successful requests, 5,721,932 billed tokens and **$0.74385116** against
the newly approved **$1.25** cap. Unknown attempts retain reservations and are
not automatically retried. No held-out query embeddings were requested.

| System | MRR@10 [95% CI] | R@1 | R@5 | R@10 | R@20 |
|---|---|---|---|---|---|
| OpenAI large alone | 0.599 [0.518, 0.679] | 0.50 | 0.74 | 0.82 | 0.88 |
| Best BM25 + OpenAI large, equal RRF c=10 | 0.653 [0.572, 0.737] | 0.56 | 0.80 | 0.84 | 0.90 |

Compared with GTE hybrid's 0.635, the paired MRR difference is +0.018
[-0.028, +0.065]: not an established improvement. The 2,000-paper pilot was
much easier because it had fewer distractors; its 0.844 dense MRR must not be
presented as a full-corpus result.

Normalized float32 paper vectors occupy 286,359,552 bytes. Search with cached
query vectors took 5.3 ms/query dense and 8.0 ms/query hybrid in one sequential
warm run; **query embedding API latency is excluded**, not a serving estimate.
BM25 initialization took 9.76 seconds; embedding/cache preparation took
635.82 seconds. These stages are recorded separately in saved metadata.

The expanded graded dev pool contains **2,857 unique pairs across seven
systems and 100 queries**. Initially 266 pairs had cached/human judgments.
Gemma labeling is resumable; its report stays explicitly provisional until all
pooled top-10 results are judged. Existing 100 human grades override Gemma.
They remain calibration data, not fresh independent validation.

**Gemma reliability follow-up (2026-10-29):** the expanded run saved its first
10 new labels after HTTP 500/503 retries (128.6 seconds for that batch), then
encountered repeated 500s on the next batch. This is not yet a throughput
estimate. A successful request with the same configuration argues against a
universally unsupported parameter, but does not rule out input-specific errors.
[Google recommends bounded exponential backoff and jitter](https://ai.google.dev/gemini-api/docs/troubleshooting).
A [Google forum report](https://discuss.ai.google.dev/t/constant-500s-on-gemma-4/140940)
describes intermittent 31B failures; it is corroborating anecdotal evidence,
not proof of the cause of our failures.

We found and fixed two retry-delivery gaps: the wrapper ignored HTTP
`Retry-After` headers and truncated fractional `retryDelay` values. Provider
delays now respect an exponential-backoff floor. Per-attempt status/timing
logs and saved usage histories let us separate API time from retry waiting.
The run was resumed from its cache with the same model, rubric, full abstracts
and 10-paper cap. These changes improve observability and retry compliance;
they do not establish that Google's 500/503 error rate is reduced.

## 15. Four OpenAI judges against the same human labels (2026-10-29)

GPT-4.1 mini and GPT-4o mini each graded exactly the same 100 frozen human
pairs, without seeing human grades, notes or reasoning. Full title/authors/
abstract evidence, rubric and 10-paper limit match the earlier OpenAI pilots.
Each new pilot completed 13 successful HTTP requests with no retries.

| Model | Exact | Quadratic kappa | Relevant agreement | Opposite 0-vs-2 | Mean s/call | Input + output tokens |
|---|---|---|---|---|---|---|
| GPT-5.4 mini | 77% | 0.802 | 84% | 0 | 2.72 | 38,611 |
| GPT-5.4 nano | 65% | 0.661 | 77% | 1 | 3.33 | 38,660 |
| GPT-4.1 mini | 57% | 0.583 | 71% | 3 | 2.98 | 38,806 |
| GPT-4o mini | 57% | 0.489 | 71% | 4 | 3.22 | 38,326 |

GPT-5.4 mini is the best supported OpenAI choice on this calibration sample;
the older minis are not improvements. Gemma scored 79% exact, kappa 0.809,
83% relevant agreement and zero opposites on these same 100 pairs, but has
intermittent 500/503 failures and shares the query-writer family.
No statistical superiority over Gemma is established.

All four OpenAI pilots account for **154,403 tokens**, cumulatively, in our
shared mini ledger. The two new pilots used 77,132 tokens. The user reports
2.5 million eligible shared tokens per day; we retain the stricter local
1.35-million effective cumulative ceiling and do not infer a provider reset
or available organization-wide allowance. Embeddings are billed separately.

Gemma was paused with its saved progress intact. Expanded dev labeling now
uses **GPT-5.4 mini only**, with human overrides. It must not reuse Gemma's
missing-pair labels as though they came from OpenAI. Raw caches remain
separate; the selected graded report records its judge identity and stays
provisional until full coverage. The 300 held-out test queries remain unused.

## 16. Complete graded dev baseline (2026-10-29)

All **2,857/2,857** pooled pairs are covered, using GPT-5.4 mini plus 100
human overrides. All seven systems have 100% judged@10 and defined nDCG on
all 100 queries. These are dev results under a calibration-selected judge,
not independent human validation or held-out test performance.

| System | nDCG@10 | P@10 |
|---|---|---|
| Best BM25 | 0.538 | 0.512 |
| GTE-small dense | 0.603 | 0.581 |
| BGE-small dense | 0.599 | 0.584 |
| BM25 + GTE RRF | 0.655 | 0.611 |
| BM25 + BGE RRF | 0.652 | 0.614 |
| OpenAI large dense | 0.668 | 0.637 |
| **BM25 + OpenAI large RRF** | **0.686** | **0.633** |

OpenAI hybrid minus GTE hybrid: **+0.030 nDCG** [0.007, 0.055].
OpenAI hybrid minus OpenAI dense: +0.018 [-0.011, 0.046], uncertain.
Dense OpenAI has slightly higher P@10, but hybrid minus dense precision is
-0.004 [-0.035, 0.028], also uncertain. Keep the chosen hybrid as the working
baseline; do not claim it dominates dense retrieval on every metric.
Intervals are exploratory paired query bootstraps, conditional on the
same label snapshot, and not adjusted for multiple comparisons.

The expanded job saved 2,757 new labels in 320 successful requests; the
100-pair mini pilot was already cached. It consumed **1,048,487** input/output
tokens. All successful cached mini calls used one HTTP attempt. Across all
four OpenAI pilots and expanded labeling, the shared ledger records
**1,202,890 tokens**, all completed, below the local 1.35-million ceiling.
The mini cache contains 2,857 raw labels; human labels still take priority.
Local accounting is not verification of organization-wide free eligibility.

Next: serve the unchanged baseline through a search API/UI and measure
actual query embedding plus retrieval latency. Then compare a separate
reranker on fixed hybrid candidates (top 20, then 50 if warranted), measuring
quality, latency and token/cost budgets. New candidates outside the current
pool need additional judgments. Freeze final choices before using held-out test.

## 17. Baseline failure-analysis leads (2026-10-29)

Before tuning fusion, freeze the original complete seven-system label snapshot
and inspect per-query evidence. Hybrid minus OpenAI dense paired nDCG:
known-item +0.098 [0.052, 0.146]; keyword +0.054 [-0.004, 0.114];
paraphrase -0.054 [-0.123, 0.010]; question -0.027 [-0.068, 0.013].
With 25 queries per type these are exploratory, not routing rules.

Low query/source word overlap (<0.5; 30 queries) shows -0.067
[-0.120, -0.013], versus +0.054 [0.020, 0.088] for higher overlap
(70 queries). Source overlap requires knowing the target paper, so it is
an offline diagnostic, not information available to a live query router.
These comparisons are not adjusted for multiple testing.

Concrete saved examples:

- `q-paraphrase-030`: dense places the grade-2 prerequisite-aware location
  recommendation paper first; hybrid moves a grade-0 creativity paper above
  it and introduces other irrelevant top results. nDCG falls 0.819 to 0.426.
- `q-paraphrase-062`: predicting LLM output length; dense has a grade-2
  remaining-output-length paper second, while hybrid's first three are all
  grade 0. Both systems also have an irrelevant first result, so not every
  failure is caused by fusion.
- `q-known_item-054`: adding lexical retrieval promotes the grade-2 Tannenbaum
  conversation-context paper from dense rank 2 to hybrid rank 1.

Full abstracts, grades, label provenance, model reasons and per-system ranks
are saved in `data/results/failure-analysis/cases.json`. Reasons are model
explanations, not verified causes. No labels were changed. This supports
testing semantic-heavy weights, not assuming they will solve every failure.
Sid deferred reranking and approved bounded fusion/depth experiments first.

**Offline grid preflight:** 38 candidate fusion configurations plus baseline/
pool controls produce 3,190 unique top-10 pairs. Existing cache and human
overrides cover 2,857; **333 pairs are missing**. No additional labeling calls
were made. Graded comparisons are withheld until coverage is complete. A wider
pool can change ideal DCG, so use the rescored frozen control inside the grid,
not the older baseline nDCG denominator, for gain/regression comparisons.
After confusion between token units and currency, additional API labeling is
paused: 147,110 was remaining local **tokens**, not dollars. No spending-cap
increase or quota reset was made.

## 18. Complete bounded fusion experiment (2026-10-29)

After explicit approval, effective cumulative token allowance was increased to
1,600,000 without resetting usage. All 333 missing pairs were saved in 95
successful calls; full pool **3,190/3,190**, retaining 100 human overrides.
Additional actual usage: **153,596 tokens**, cumulative **1,356,486**;
all 467 ledger attempts are completed. No new embeddings or held-out test runs.
At standard rates the preflight estimated ~$0.16 absent free eligibility;
actual token accounting does not verify provider billing/free eligibility.

| Candidate | nDCG@10 | P@10 | Source MRR@10 |
|---|---|---|---|
| Frozen 50/50 RRF c=10, depth100, rescored | 0.664 | 0.633 | 0.653 |
| 75% semantic RRF c=100, depth100 | **0.709** | **0.690** | 0.618 |
| 75% semantic linear rank, depth100 | 0.707 | 0.685 | 0.624 |
| 75% semantic RRF c=60, depth100 | 0.706 | 0.680 | 0.630 |

Best observed nDCG candidate improves **+0.045 [0.028, 0.064]** paired
against the frozen control: 67 queries improve, 30 regress, 3 tie.
Mean nDCG improves across all four query types, but not every individual
query; source-paper MRR decreases. Do not equate higher graded relevance
with better exact-target retrieval. Nearby c=60/linear settings are close;
the coarse grid does not establish a uniquely optimal constant.

Expanded-pool nDCG for the unchanged control is 0.664 versus the original
seven-system report's 0.686: extra relevant pool papers increase ideal DCG.
Rankings and P@10 did not change. Compare candidates only within this snapshot.
These 38-setting dev results and unadjusted intervals are exploratory; winner
selection can inflate gains. Preserve the frozen baseline while reviewing the
graded-relevance versus source-target tradeoff. UI/RAG/test remain deferred.

## 19. Why known-item source ranking regresses; offline refinement

The 75% semantic c=100 setting changes source ranks on only **two of 25**
known-item queries relative to the frozen control. Known-item MRR falls
0.980 to 0.9433, top-1 hits fall 24/25 to 23/25, and top-10 target recall
stays 25/25. Known-item graded nDCG actually rises 0.6948 to 0.7137:
broader useful results and exact-target ranking are different objectives.

| Query | Source rank: original / 75% c100 | Source lexical / dense ranks |
|---|---|---|
| Mathur rag policy qa | 1 / 4 | 1 / 16 |
| Qiao variable length semantic ids | 2 / 3 | 1 / 8 |

For Mathur, the 75% blend ranks generic RAG/QA papers ahead of the target;
the first result has lexical rank18 and dense rank3. The target's exact
author/topic signal makes it BM25 rank1 but dense rank16. Qiao similarly
has a strong lexical author/title match but several close semantic neighbors.
Dense input contains title/abstract, while BM25 also contains authors.

RRF score is `(1-w)/(c+lexical_rank) + w/(c+semantic_rank)`, with an absent
list contributing zero. Two variables changed: semantic weight rose and c
rose from10 to100. A larger c flattens the rank1 advantage, so a clear
lexical winner gets less protection. This explains the measured score
ordering, not necessarily every retrieval failure.

An offline 24-setting refinement (weights .50/.55/.60/.65/.70/.75 and
c10/30/60/100, depth100) reused the fixed 3,190-pair snapshot. No API calls.
Some settings expose 1-5 unjudged pairs; their provisional nDCG must not
be used for winner selection. Two fully covered refinements:

| Setting | nDCG@10 | P@10 | Known-item source MRR |
|---|---|---|---|
| Original 50%, c10 | 0.6641 | 0.633 | 0.980 |
| Previous 75%, c100 | 0.7095 | 0.690 | 0.9433 |
| **55% semantic / 45% lexical, c30** | **0.7106** | **0.689** | **0.980** |
| 60% semantic / 40% lexical, c60 | 0.7139 | 0.700 | 0.9533 |

The 55%/c30 setting restores Mathur rank1 and Qiao rank2, matching original
known-item MRR while retaining graded-relevance gains. Its paired nDCG
difference versus75%/c100 has CI [-0.0104, +0.0125]; do not claim a meaningful
nDCG superiority. It is an attractive tradeoff candidate, not independently
validated optimum. The 60%/c60 option's corresponding CI is
[-0.0055, +0.0146]. Further source-target regressions outside known-item
must still be reviewed before promoting a new default.

Next targeted tests, if needed: author/title-aware lexical protection,
explicit user-selected exact-paper mode, or bounded query-dependent fusion.
Do not route on synthetic `query_type`, source overlap or known source IDs:
those are evaluation metadata, not available live intent signals.

## 20. Pre-promotion review of the 55%/c30 candidate

Ran `python -m arxiv_search.evaluate.fusion_review` against the immutable
fusion label snapshot. Four finalists, all 100 dev queries, all top-10
results judged; identical 3,190-pair ideal-DCG denominator and human overrides.
No labeling, embeddings, API calls, held-out test scoring, or baseline changes.
The review validates rubric, workbook and source-ranking fingerprints before
scoring and refuses any unjudged top-10 pair. Outputs are isolated under
`data/results/fusion-review-dev/`; original reports are preserved.

### Overall scorecard

| Semantic weight / c | nDCG@10 | P@10 | Source MRR@10 | Source R@1 | Source R@10 |
|---|---|---|---|---|---|
| Original 50% / 10 | 0.6641 | 0.633 | 0.6534 | 0.56 | 0.84 |
| Candidate 55% / 30 | 0.7106 | 0.689 | 0.6459 | 0.55 | 0.86 |
| Alternative 60% / 60 | 0.7139 | 0.700 | 0.6302 | 0.53 | 0.83 |
| Previous 75% / 100 | 0.7095 | 0.690 | 0.6181 | 0.52 | 0.84 |

Candidate versus original nDCG: **+0.0465 [0.0311, 0.0628]**, 70 wins,
26 losses, four ties. P@10: +0.056 [0.0360, 0.0780].
Source MRR: -0.0076 [-0.0330, 0.0162], eight wins, 13 losses, 79 ties.
This is not a claim of source-MRR equivalence or noninferiority.

Candidate versus75%: nDCG +0.0011 [-0.0104, 0.0125], 41 wins, 52 losses,
seven ties; similar means do not mean identical lists. Source MRR improves
**+0.0278 [0.0077, 0.0550]**, 12 wins, six losses, 82 ties.
Candidate versus60%: nDCG -0.0033 [-0.0123, 0.0056], source MRR
**+0.0156 [0.0024, 0.0353]**. These intervals are conditional on fixed labels
and exploratory dev selection, without multiplicity adjustment.

### All query types, original versus candidate

Each segment contains25 queries.

| Type | Original / candidate nDCG | Original / candidate source MRR | Candidate-minus-original nDCG CI |
|---|---|---|---|
| Keyword | 0.7001 / 0.7373 | 0.7167 / 0.6632 | [0.0113, 0.0633] |
| Known-item | 0.6948 / 0.7156 | 0.9800 / 0.9800 | [-0.0050, 0.0484] |
| Paraphrase | 0.5940 / 0.6662 | 0.3644 / 0.3823 | [0.0360, 0.1083] |
| Question | 0.6676 / 0.7234 | 0.5527 / 0.5580 | [0.0290, 0.0824] |

Every known-item source rank, not just mean MRR, is unchanged versus original.
Known-item first hits remain24/25 and top-10 hits25/25.
Paraphrase top-10 source hits rise16/25 to18/25.

The remaining clear segment tradeoff is keyword source MRR:
**-0.0535 [-0.1125, -0.0090]**, five losses and one gain.
Top-10 keyword source recall stays24/25, but first hits fall15/25 to13/25.
Two large reciprocal-rank losses are rank1 to2 swaps:

- `q-keyword-009`, automated community clustering/topic models: the support-group
  formation source moves1 to2, and TopiCLEAR moves2 to1. Both are grade2.
  Abstracts show the source is more community-specific, while TopiCLEAR covers
  embedding-based topic discovery. This is a useful alternative, but may weaken
  the community intent. Graded nDCG improves0.8817 to0.8890.
- `q-keyword-062`, GNN proxy for SDP relaxations: the Max-Cut-specific neural
  proxy moves1 to2 behind a general GNN/linear-SDP surrogate paper. Both full
  abstracts directly address the query and both are grade2. **The nDCG loss
  0.7819 to0.6736 is not caused by swapping two grade2 papers**: lower ranks
  lose grade1 papers and introduce grade0 GNN papers. This is a genuine
  relevance-list regression under the fixed labels, shared by75% and60%.

Other keyword source losses: clinical knowledge graphs4 to7, parameter
importance/freezing5 to8, popularity prediction2 to3. Clinical-query nDCG
improves0.8126 to0.8810 despite source demotion; popularity-query nDCG slips
0.6332 to0.6287. All source-rank changes, including beyond top10, are saved.

### Concrete gains and remaining losses

- Biggest gain over original: `q-paraphrase-030`, prerequisite-aware places to
  visit, nDCG **0.4265 to0.7391**. The intended recommendation paper moves2 to1;
  unrelated creativity and retrieval-blind-spot papers fall. It also improves
  over both other finalists (0.5823).
- Chip-design documentation grouping, `q-paraphrase-093`: **0.6057 to0.8672**.
  Source stays first; structure-aware technical-document retrieval and
  chunking papers replace logical-QA/contextual-help distractors.
- A known-item nDCG loss does not necessarily mean a lost target:
  `q-known_item-062` (Flek physics/adversarial attacks) stays first but nDCG
  falls0.6141 to0.5164. A different Flek-authored physics/adversarial paper,
  graded2, falls7 to22. Its authors and full abstract support topical overlap;
  this short query is ambiguous. Whether a second grade2 fits the rubric's
  specific-paper clause needs human interpretation. Do not silently rewrite
  its label or count the nDCG drop as an exact-target failure.
- Largest nDCG loss versus75%: `q-question-077`, vanilla GNNs on unseen
  knowledge graphs, **0.5519 to0.4610**. The directly relevant zero-shot source
  moves3 to6. Both settings still put grade0 distractors above it: the candidate
  favors temporal KG category forecasting, while75% favors traffic forecasting.
  The candidate is not a universal improvement in question understanding.
- Repeated-pretraining-data question, `q-question-019`: **0.7487 to0.6604**
  versus75%, though still better than original0.5266. The candidate promotes
  grade0 pre-pretraining material and demotes grade2 duplication/retention papers.
  GraphER known-item search also loses supporting-list relevance versus60%
  and75%, although the exact GraphER paper stays first.

### Pre-promotion recommendation (subsequently approved)

55%/c30 is the preferred **balanced dev candidate**, not a statistically
unique optimum or universally dominant system. It restores all known-item
target ranks, retains broad relevance gains, and improves source MRR over
the other two finalists. Accepting it means explicitly accepting remaining
keyword/source-rank and individual question/list-quality tradeoffs.

No automatic promotion was made during the review. Keep the original frozen control for future
comparisons even if the user approves a new working baseline. Held-out test
remains untouched; independent generalization and fresh-human validation
remain unproven. Full rankings, aligned per-query scores, paired intervals
and diagnostic abstracts/reasons are reproducible with the review command.

**Promotion update, 2026-10-29:** Sid approved55% semantic /45% lexical,
RRF c=30, depth100 as the new working baseline (Decision35). The approved
profile is now versioned in config with a dedicated fusion helper. Original
controls, pre-promotion artifacts, labels and held-out test remain unchanged.

## 21. Score-based fusion, top-rank bonuses and candidate depth

Ran16 bounded dev experiments plus the approved working control:

- 12 score settings: max or minmax normalization, semantic weights0.35/0.55/0.75,
 depths100/500.
- 2 depth-only controls: existing55%/c30 RRF at depths200/500.
- 2 top-rank protection settings: existing RRF plus10%/25% of each retriever's
 weighted rank-one RRF contribution, added only to its first result.

Each scored input is truncated before per-query normalization. Max divides
scores by that list's maximum; minmax subtracts its minimum and divides by
its range. A missing-list score contributes zero. Equal positive scores
receive equal unit values; zero lists receive zero. Ties are lexical-first.
Score weights are not interchangeable with rank-fusion weights.

BM25 scores and cosine similarities were recomputed using existing full-corpus
vectors and cached100 dev query vectors. **Every recomputed source top100
exactly matches its frozen ranking**, and the working helper reproduces all
approved rankings. No paper or query was re-embedded; no test query was scored.
The scorer explicitly refuses a missing or invalid cache rather than making
an API repair call.

### Complete shared labeling and budget

Initial cached grid had104 new query-paper pairs across46 query-specific
batches. Sid approved judging those pairs within the existing effective
1,600,000-token cumulative cap; no cap increase or reset.
Estimated total was about66,000 tokens, about$0.06 at previously recorded
standard rates absent free coverage; no-retry output-cap estimate about$0.47,
not a hard billing ceiling.

Actual job: **104 new labels,46 successful calls,55,489 tokens**.
Ledger total is1,411,975 tokens over513 attempts, leaving188,025 under the
local effective cap. These are token counts, not currency charges; account
free eligibility/billing is not verified by this ledger.

An additive3,294-pair snapshot preserves every original3,190 grade including
human overrides. All16 settings' top10s and the working control are fully
judged. Original reports/snapshots remain frozen. Main scorecard rescoring
uses the expanded snapshot for every saved system, never mixes denominators.

The unchanged working baseline's nDCG is now0.7064 versus earlier0.7106:
additional relevant papers increased idealDCG. This is **not a ranking
regression**; P@10 remains0.689 and source MRR0.6459.

### Main results (same3,294-pair snapshot)

| System | nDCG@10 | P@10 | Source MRR@10 | Known-item MRR | Source R@10 |
|---|---|---|---|---|---|
| Approved RRF55%, c30, d100 | 0.7064 | 0.689 | 0.6459 | 0.980 | 0.86 |
| **Max-score75%, d500** | **0.7197** | **0.697** | **0.6916** | **0.980** | **0.82** |
| Max-score75%, d100 | 0.7111 | 0.686 | 0.6682 | 0.980 | 0.82 |
| Minmax-score55%, d500 | 0.7030 | 0.674 | 0.6842 | 0.980 | 0.84 |
| Minmax-score55%, d100 | 0.6853 | 0.647 | 0.6897 | 0.980 | 0.85 |
| RRF55%, c30, d200 | 0.7058 | 0.691 | 0.6390 | 0.980 | 0.84 |
| RRF55%, c30, d500 | 0.7035 | 0.690 | 0.6402 | 0.980 | 0.84 |
| RRF plus10% top1 bonus | 0.7048 | 0.689 | 0.6530 | 0.980 | 0.85 |
| RRF plus25% top1 bonus | 0.7022 | 0.687 | 0.6527 | 0.980 | 0.85 |

Best observed max-score75%/d500 versus working RRF:
nDCG **+0.0133 [0.0015,0.0251]**,56 wins38 losses6 ties.
This is exploratory, selected from16 settings after earlier dev tuning;
the unadjusted interval is not independent confirmation.
It improves first-relevant-target placement on average but **loses four
top10 source hits**,82/100 versus86/100. Higher MRR can coexist with lower
recall: some hits move toward first while other targets fall out of top10.

| Segment | Working / max-score nDCG | Working / max-score source MRR | Working / max-score source R@10 |
|---|---|---|---|
| Keyword | 0.7333 / 0.7324 | 0.6632 / 0.7157 | 0.96 / 0.92 |
| Known-item | 0.7132 / 0.7262 | 0.9800 / 0.9800 | 1.00 / 1.00 |
| Paraphrase | 0.6622 / 0.6951 | 0.3823 / 0.4873 | 0.72 / 0.64 |
| Question | 0.7169 / 0.7252 | 0.5580 / 0.5833 | 0.76 / 0.72 |

### Failure-driven conclusions

- Nordic power-market battery/electrolyser query: source **9 to1**,
  nDCG0.3443 to0.5596. Score fusion recovers the strong dense result.
- Vanilla GNNs on unseen knowledge graphs: source **6 to1**,
  nDCG0.4610 to0.6986. Another intended fusion failure improves.
- BL19 benchmark: source **2 to1**, nDCG0.3543 to0.4731.
- Output-length prediction: source **10 to92** despite slightly improved
  list nDCG0.3206 to0.3669. Score fusion does not fix a dense list that
  itself favors token-price/output distractors. This is an important
  candidate regression, not a reason to cherry-pick only successful cases.
- All three targets absent from the original top100 union are present
  within top500. Poisoned-result defense is dense116; summary-tree
  retrieval is dense259. Neither reaches the best candidate's top100
  fused output: deeper retrieval alone does not ensure useful final ranks.
- Depth-only RRF and the tested top1 bonuses do not improve mean nDCG
  versus the working profile. Do not expand these grids without a new
  hypothesis.

**Keep approved RRF baseline unchanged.** Max-score75%/d500 is promising
but needs loss-case review and explicit recall tradeoff approval before
promotion. The low-output-length and missing-top100 cases motivate later
query/document representation experiments rather than endless fusion grids.

### Results table visibility fixed

The previous top table was driven by the experiment registry and omitted
fusion runs stored in separate experiment folders; those appeared only far
down in appended reports. A new unified scorecard discovers saved dev run
files independently of registry membership across all experiment folders.
All24 earlier fine rank-weight/constant settings are now persisted, not just
the two finalists previously saved. Any fine setting exposing additional
unjudged pairs remains explicitly provisional; the approved104-pair batch
was for the16 new score/depth/bonus experiments, not unlimited relabeling.
It displays source MRR/R@1/5/10/20, graded nDCG/P@10/coverage, known-item
MRR and paired nDCG versus the approved working profile. Per-type metrics
and snapshot provenance are saved in the catalog JSON; historical tables,
BM25 tuning and reduced-corpus pilots remain separately scoped.

Reproduce the cache-only experiments with
`python -m arxiv_search.evaluate.score_fusion_experiment`, then regenerate
the central results using `experiments.write_results_doc()`. Do not rerun
the full experiment CLI without selectors just to refresh documentation.

## 22. Leaderboard and score-fusion challenger loss review

The generated [leaderboard](05-results.md#unified-dev-scorecard) now ranks fully
judged runs by descending **nDCG@10**, our existing primary success metric,
not a new composite score. Exact ties use stable experiment IDs; sorting uses
unrounded means. There are **76 eligible and52 unranked diagnostic runs**,
128 saved identities total (including aliases, not128 independent algorithms).
The approved RRF baseline appears at its actual position, **fourth**, rather
than being pinned first. Provisional runs cannot win. Separate keyword,
embedding and ranker/fusion columns explain the methods, with original IDs
in expandable details and machine-readable descriptions/ranks.

### Same-snapshot comparison

| Metric | Working RRF55%, c30, d100 | Max-score75%, d500 | Paired difference [95% CI] |
|---|---|---|---|
| nDCG@10 | 0.7064 | 0.7197 | +0.0133 [0.0015,0.0251] |
| P@10 | 0.689 | 0.697 | +0.008 [-0.006,0.023] |
| Source MRR@10 | 0.6459 | 0.6916 | +0.0457 [0.0093,0.0909] |
| Source R@1 | 0.55 | 0.61 | +0.06 [0.01,0.12] |
| Source R@10 | 0.86 | 0.82 | -0.04 [-0.08,-0.01] |
| Source R@20 | 0.89 | 0.84 | -0.05 [-0.09,-0.01] |

Across100 dev queries:56 nDCG wins,38 losses,6 ties. Grade0 first results
decrease6 to4. **All25 known-item source ranks are individually unchanged**,
not just their mean MRR. These are exploratory label-conditional intervals
after repeated dev tuning, not multiplicity-adjusted or held-out confirmation.

### Every lost top10 target, not just net recall

| Intent | Working source rank | Challenger source rank | List nDCG change |
|---|---|---|---|
| Graph learning for chemical reactions | 9 | 12 | -0.0531 |
| Recommendation debiasing through unlearning | 5 | 34 | +0.0594 |
| Heavy-tailed output-length prediction | 10 | 92 | +0.0462 |
| Compute scaling for recommender systems | 5 | 55 | -0.0667 |

There are **four lost hits and zero newly gained hits**, not four net losses
concealing offsetting gains. Two lost-target queries improve list nDCG:
useful alternative papers do count, but finding the original specific paper
is a different objective.

### Why score fusion loses them

Saved raw scores reproduce the challenger exactly for all inspected cases.
The key failure is **overlap advantage under max-normalized scores**, not
simply "the dense retriever failed." Cosine scores can be tightly clustered;
weak lexical support then outweighs a strong semantic-only hit.

- **Output length:** the grade2 target is semantic6, absent from lexical500.
  Its score is0.75 x0.90193 = **0.67645**, with no lexical contribution.
  Of91 documents above it,90 have lexical support. The same75% score blend
  at depth100 ranks it18; depth500 worsens it to92. A legitimate alternative,
  *How Much is Left?*, rises6 to2 with lexical173 and semantic2, while
  token-value and lottery-number distractors remain near the top. Hence the
  small nDCG gain does not solve the specific heavy-tailed-length intent.
- **Compute scaling:** the source is semantic2, absent lexical500, scoring
  **0.73199**. Of54 papers above it,53 have lexical support. Depth100 score
  fusion already drops it to12; depth500 drops it55. This is a fusion
  failure despite an excellent dense target rank, compounded by a vague
  synthetic query ("suggesting systems" rather than "recommender systems").
- **Debiasing/unlearning:** the target is semantic4, absent lexical500,
  scoring **0.74646**. It ranks7 under depth100 score fusion and34 at500.
  The candidate instead places a grade2 CRAGRU recommendation-unlearning
  alternative first, helping list nDCG while losing the exact source hit.
- **Chemical reactions:** the target has lexical35/semantic5. Its
  contributions0.1429 +0.6800 put it12 rather than9; the score margin and
  other documents' overlap matter, not just the rank5 semantic position.

### Largest list-quality regressions

The two largest nDCG losses do **not** lose their exact targets:

- *Ko decoupling content delivery medical qa*: source remains1;
  nDCG0.8444 to0.6659. A grade0 memory/knowledge-fusion QA paper rises13 to3,
  while a grade1 medical-QA evaluation paper falls10 to18. The first
  result is protected, but the rest of the answer list is not.
- *Video watch time mixture model*: source remains1;
  nDCG0.8120 to0.6715. The grade2 RQ-Reg continuous-value prediction paper
  falls10 to12. Exact-target success does not imply supporting-list success.

The next losses concern activation inspection (-0.0981), repeated
pretraining data (-0.0937), and multimodal decoding (-0.0793). Their targets
move15 to13,2 to2, and27 to23 respectively: nDCG losses can come from the
other results even when the target rank improves. Known-item alternative
grades can be ambiguous under our rubric; this review leaves all frozen
human/model labels unchanged rather than relabeling to favor a system.

### Decision and next hypothesis

**Keep approved RRF55%/c30/depth100 as working baseline. Retain
max-score75%/depth500 as the strongest graded-relevance challenger.**
Promotion would explicitly accept worse source R@10 and R@20, despite
better first-position hits/MRR and average graded relevance. That tradeoff
has not been approved; leaderboard position alone does not make the decision.

The next focused hypothesis should distinguish *candidate discovery* from
*how much weak lexical overlap is allowed to boost an otherwise weak semantic
match*, with explicit source-recall guardrails. Merely shrinking depth is not
a complete fix (the output-length target is still18 at depth100), and blindly
increasing semantic weight does not remove compressed cosine-score margins.
Do not add query-specific exceptions. Representation/query wording changes
are another justified future direction, not an already demonstrated fix.

[Reproducible loss report](../data/results/score-candidate-review-dev/report.md),
[all query changes and segment CIs](../data/results/score-candidate-review-dev/report.json),
and [case abstracts, grades and score components](../data/results/score-candidate-review-dev/cases.json)
are generated by `python -m arxiv_search.evaluate.score_candidate_review`.
The command validates frozen snapshot/run fingerprints and recomputes case
rankings from saved scores; it has no API path. No new labels, embeddings,
spending or test-query scoring were needed. Decision35 and baseline config
remain unchanged.

## 23. Rank/score experiments and recall-preserving baseline

### First hypothesis: rank evidence offsets weak-overlap score boosts

Prespecified six interpolations of max-score75% with normalized
RRF55%/c30/depth100: score fractions25/50/75%, score depths100/500.
RRF values are divided by their theoretical maximum1/31, not fitted to
query outcomes. No source IDs, query-type routing, or labels enter ranking.

The conservative screening policy requires fully judged top10s, a positive
paired nDCG lower endpoint, no mean segment nDCG regression, no loss of mean
source R@10/20, no known-item rank regression, and no increase in grade0
first results. These are exploratory dev checks, not formal noninferiority
or held-out guarantees.

**Result: zero of six pass.** Interpolation recovers many of the unrestricted
score challenger's lost sources, but every setting still loses the
output-length target from top10. Source R@10 ranges0.84-0.85 versus0.86.
Five settings are fully judged; the75%/depth500 setting has one unjudged
pair (`q-question-064`, `2602.05471`) and is explicitly provisional.
No new judgment was purchased: its source-recall failure cannot be fixed by
changing that paper's relevance grade. Fully covered nDCG ranges0.7050-0.7108,
with no paired interval excluding zero versus RRF.

### Second hypothesis: change ordering without changing membership

After that result, prespecified four fixed-shortlist experiments: score
fractions50/100%, score depths100/500. RRF selects the ten; score evidence
orders only those ten; the tail stays identical. This is a general
architecture rule, not exceptions for individual queries.

All four need **zero new labels**. Both pure-score ordering settings pass;
the50% interpolations do not. Best passing setting:
`fusion-shortlist+a=1+d=500`.

| Metric | Previous RRF baseline | Approved shortlist baseline | Paired difference [95% CI] |
|---|---|---|---|
| nDCG@10 | 0.7064 | 0.7176 | +0.0112 [0.0041,0.0186] |
| P@10 | 0.689 | 0.689 | 0, same selected papers |
| Source MRR@10 | 0.6459 | 0.6967 | +0.0509 [0.0148,0.0956] |
| Source R@1 | 0.55 | 0.61 | +0.06 [0.01,0.12] |
| Source R@5 | 0.76 | 0.80 | +0.04 [-0.01,0.10] |
| Source R@10 | 0.86 | 0.86 | 0, preserved by construction |
| Source R@20 | 0.89 | 0.89 | 0, preserved by construction |

| Segment (25 queries each) | Previous / new nDCG | Previous / new source MRR | Source R@10, unchanged |
|---|---|---|---|
| Keyword | 0.7333 / 0.7385 | 0.6632 / 0.7202 | 0.96 |
| Known-item | 0.7132 / 0.7183 | 0.9800 / 0.9800 | 1.00 |
| Paraphrase | 0.6622 / 0.6858 | 0.3823 / 0.4984 | 0.72 |
| Question | 0.7169 / 0.7277 | 0.5580 / 0.5883 | 0.76 |

Each segment mean nDCG improves, but only the paraphrase segment's paired
interval excludes zero; do not claim independent improvements for all four.
All25 known-item source ranks are individually unchanged. Overall49 nDCG
wins,37 losses,14 ties; source MRR has12 wins,6 losses,82 ties. Grade0
first results decrease6 to4, though a new grade0 first result is introduced
on the multimodal decoding query.

Versus unrestricted score fusion, the shortlist candidate has0.0021 lower
nDCG (paired interval[-0.0123,0.0075], unresolved),0.0051 higher source MRR,
and preserves four additional top10 target hits and five top20 hits.

### Loss review and accepted limitations

- **Multimodal decoding:** nDCG-0.0793. *Modality Collapse as Mismatched
  Decoding* rises2 to1 (cached model grade0); a grade2 parallel-decoding
  paper drops1 to2. The model reason distinguishes theoretical mismatched
  decoding from decoding strategies; this boundary is worth future human
  audit, not post-hoc relabeling to favor the candidate.
- **Regional language/social media:** nDCG-0.0488. A grade0 Bengali
  regional speech corpus rises7 to2; its abstract concerns dialects/ASR,
  not social media. This is a real intent mismatch supported by the abstract.
- **Compute requirements for recommenders:** nDCG-0.0426; source5 to8,
  rather than55 under unrestricted fusion. A grade1 data-scaling paper
  rises6 to2 while a grade2 behavioral compute-scaling paper drops3 to7.
- **Output-length prediction:** source stays10 rather than92; nDCG
  improves0.0860 over RRF by moving a grade2 remaining-length alternative6
  to2. Grade0 distractors remain. This is recovery of coverage, not a fully
  solved query.
- Other source-rank losses: popularity bias2 to3, debiasing/unlearning5
  to6, shared-network communication3 to4, evidence subgraphs8 to9, and
  programmable-script assistant survey1 to2. No source leaves top10.

Sid explicitly approved promotion after the segment summary (Decision36).
The working helper reproduces all100 saved candidate top100 rankings exactly;
the leaderboard now highlights this identity and recomputes paired deltas
against it. The unrestricted score challenger remains first by raw nDCG;
the approved baseline is second. Original RRF and historical reports remain
frozen, not overwritten.

### Why further fusion tuning is yielding smaller gains

We are mostly reshuffling the **same representations and candidates**.
The approved top10 contains311 grade0,423 grade1 and266 grade2 results
across100 queries. Even a perfect label-aware permutation of those same
ten papers reaches only **nDCG0.7790**, versus current0.7176. That leaves
about0.0614 of within-shortlist ordering headroom on this fixed snapshot;
it is an oracle bound, not a predicted gain from a model.

The current shortlist contains the source in86/100 queries. The raw
lexical/semantic union contains it in97/100 at depth100 per retriever and
100/100 at depth500. Thus a lot of the remaining exact-source problem is
**candidate selection/ranking**, not simply failure to retrieve anything.
Presence at500 does not mean a practical ranker can recognize the target.

Larger gains need a changed information signal:

1. **Query-document interaction**, evaluated on a broader candidate pool,
   could distinguish "regional speech" from "social media" and reasoning
   about compute from generic data scaling. A cross-encoder/LLM reranker
   would add this signal, unlike another weighted sum. This is a future
   option, not approved/deployed in this experiment.
2. **Better query/document representations:** controlled query expansion
   for awkward paraphrases, separate title/abstract representations,
   explicit author/identifier handling, and eventually passage-level
   evidence if abstracts omit the answer. Each changes the candidate
   signal and needs its own cost/coverage checks.
3. **More trustworthy evaluation:** synthetic Gemma wording, a calibrated
   LLM judge, only25 queries per segment, and repeated dev selection limit
   confidence. Fresh-human loss audits and a larger independent dev set
   would distinguish actual product gains from fitting this benchmark.
   The300 held-out queries remain untouched until the approach is frozen.

Do not treat nDCG1.0 or finding the synthetic source as guaranteed user
success. Broad questions can have multiple right papers, and some relevance
grades are ambiguous. A larger measured jump needs evidence, not just
more tuning parameters.

Reproduce the two offline experiments with
`python -m arxiv_search.evaluate.rank_score_experiment` and
`python -m arxiv_search.evaluate.rank_score_experiment --family shortlist`.
Their plans are saved before outcomes; input fingerprints and controls
are verified; changed plans/inputs require a new experiment identity.
`python -m arxiv_search.evaluate.baseline_promotion` verifies the promoted
helper, refreshes the leaderboard and regenerates [hill-climbing charts](06-charts.md)
and the machine-readable headroom audit. All work used cached scores and
labels: zero new API calls, embeddings, labels or spending.

## 24. Query-document interaction: first local cross-encoder

Sid approved a new signal family rather than another global fusion grid
([Decision37](02-decisions.md#37-local-query-document-interaction-and-field-score-experiments-2026-10-29)).
Decision36 stays the control; nothing is promoted automatically.

### Hypothesis and experiment

Query-document interaction may distinguish a complete intent match from a paper
that mentions only some concepts. The first model is
`cross-encoder/ms-marco-MiniLM-L6-v2`, revision
`233902d25c440f23af6f7d6e94d2946bac0bee0a` (Apache-2.0), trained for MS MARCO
passage ranking. It scores query + title/abstract locally, using CPU float32.
No labels or source IDs enter its candidate selection or scoring.

Five settings were fixed before outcomes: reorder baseline top10/30/100;
rerank the lexical100/semantic100/baseline100 union; and blend its ranks with
baseline ranks at50/50 using RRF c30. The fixed100-query dev scope,
revision-pinned model, token budget, candidate order, input hashes and cache
validation are persisted. Held-out test and human grades are unchanged.

### Fully judged ordering test: a regression

Top10-only reranking changes no membership and needs no new labels.

| Metric | Decision36 baseline | Cross-encoder top10 |
|---|---:|---:|
| nDCG@10 | 0.7176 | 0.7021 |
| Precision@10 | 0.6890 | 0.6890 |
| Source MRR@10 | 0.6967 | 0.6593 |
| Source Recall@10 | 0.86 | 0.86 |
| Source Recall@20 | 0.89 | 0.89 |
| Grade0 first results | 4 | 7 |

Paired nDCG delta: **-0.01549**, exploratory95% CI
**[-0.02783, -0.00371]**, with38 wins /57 losses /5 ties.
MRR delta is-0.03742, CI[-0.09935, +0.01939]; that interval includes zero.
Two known-item target ranks regress, despite both staying within the top10.

| Segment (25 queries each) | Baseline nDCG | Cross-encoder nDCG | Mean delta |
|---|---:|---:|---:|
| Keyword | 0.7385 | 0.7453 | +0.0068 |
| Known item | 0.7183 | 0.7097 | -0.0086 |
| Paraphrase | 0.6858 | 0.6420 | -0.0438 |
| Question | 0.7277 | 0.7113 | -0.0164 |

The paraphrase drop has CI[-0.07437,-0.01394]. The keyword increase's interval
includes zero; it is not evidence for deploying query-type routing.

### Broader pools: source regressions, graded comparison incomplete

| Setting | Source MRR10 | R10 | R20 | Judged top10 positions |
|---|---:|---:|---:|---:|
| Baseline | 0.6967 | 0.86 | 0.89 | 100% |
| Cross-encoder, baseline30 | 0.6201 | 0.79 | 0.85 | 90.4% |
| Cross-encoder, baseline100 | 0.6046 | 0.74 | 0.82 | 73.3% |
| Cross-encoder, union100 | 0.6041 | 0.74 | 0.79 | 68.6% |
| 50/50 rank blend, union100 | 0.6875 | 0.84 | 0.85 | 93.4% |

There are **392 unique unjudged top10 pairs** across these settings. Their
diagnostic nDCG values must not be interpreted as measured graded quality or
compared to the fully judged control. The leaderboard keeps them unranked and
withholds graded paired intervals. Source metrics remain complete.

Pure baseline100 reranking loses13 previously found source top10s and gains1;
the blend loses3 and gains1. All five configurations fail the prespecified
screen. Additional labels could change the graded verdict for broad-pool
settings, but cannot repair their measured source-recall guardrail failures.
No new judging calls were made.

### Concrete failures and one useful recovery

- **Author-bearing lookup:** "Bekkers equivariant neural fields" has the source
  1->3 under top10 reranking,1->8 under baseline100, and1->2 with the blend.
  The top10 reranker promotes two grade0 papers above the grade2 target.
  The cross-encoder does not receive authors, unlike our lexical retriever;
  that missing evidence is a plausible contributor, not a proven sole cause.
- **Output-length paraphrase:** source10->77 with baseline100 and10->29 with
  the blend. The grade2 remaining-output-length alternative stays at rank2
  in the blend, while a grade0 token-value paper remains first. This is not
  just a case of choosing a different relevant source.
- **Diverse self-training:** source1->7 even within the selected top10, and
  1->12 with the blend. The promoted rank1 alternative is also grade2;
  source MRR alone would overstate the quality of that particular loss.
- **Multimodal decoding keyword:** source27->2 with baseline100 and27->6
  with the blend. There are genuine recoveries; they do not offset the losses.

### Compute, caching and interpretation

We scored **17,849 query-paper pairs**, taking **2,714 seconds (45.2 minutes)**
of aggregate per-query tokenization/inference time on the Snapdragon CPU.
Model load/download is excluded; another local embedding experiment ran
concurrently. This is offline throughput, not a production latency benchmark.
Only56 pairs exceeded the512-token budget (0.31%); query text is preserved
and document endings are truncated. This small overall rate does not exclude
individual truncation failures.

The complete score cache was replayed without loading a model or making
inference/API requests. No new paid embeddings, judgments or spending occurred.

**Decision: retain Decision36.** This particular small, web-passage-trained
cross-encoder is not a win on our benchmark. It does not show that all
query-document interaction models fail. Domain fit, author input and stronger
models remain hypotheses; none has been measured here. An LLM reranker is not
automatically justified by these results.

Reproduce with `python -m arxiv_search.evaluate.cross_encoder_experiment`.
See the [full report](../data/results/cross-encoder-dev/report.md), its
machine-readable segment/paired results and case evidence alongside it.

### Cost boundary for OpenAI title/abstract separation

The local field experiment does not silently replace OpenAI with newly billed
vectors. A separate exact-token dry estimate at the repository's stored
`text-embedding-3-large` rate ($0.13 per million tokens) found:

| Scope | Input tokens | Estimated new embedding charge before cache reuse |
|---|---:|---:|
| All23,304 titles | 389,197 | $0.0506 |
| All23,304 abstracts | 5,873,208 | $0.7635 |
| Both full-corpus fields | 6,262,405 | $0.8141 |
| Both fields for7,644 unique baseline100 candidates only | 2,081,960 | $0.2707 |

These are estimated dollars, not token allowances or measured charges. Existing
query embeddings could be reused; the estimate concerns document fields.
The full-corpus option does not fit the remaining approximately$0.5061 under
the separate$1.25 full-run embedding cap. Even a candidate-only option needs
explicit approval before paid requests; it would test reranking, not a new
full-corpus retriever.

The text-judge ledger is unchanged at1,411,975 accounted tokens over513 attempts,
leaving188,025 under its effective1,600,000 cumulative cap. This is separate
from the embedding-dollar cap and does not reset daily. None of these estimates
triggered a request, reservation, labeling job, or budget increase.

## 25. Separate title/abstract field scores

The first bounded field experiment holds Decision36's100 candidates per query
fixed and changes only their ordering. "Body" here is the abstract; no full text
was downloaded. Settings and input hashes were saved before outcomes.

### Independent lexical fields: no improvement

Build separate full-corpus BM25 indexes for title, abstract and authors, using
exact+stem tokens, k1=.8 and b=.75. Divide each field's scores by its maximum
among the query's100 candidates, then form:

`F = .9 * [t * title + (1-t) * abstract] + .1 * authors`.

The final score is `.75 * 31/(30+baseline_rank) + .25 * F`, not an average of raw
BM25 and cosine scores. The author channel is explicit so author-bearing
queries do not silently lose all author evidence. These choices test this
particular normalization and mixture, not every possible fielded BM25 recipe.

| Title share t (of title/abstract channel) | nDCG10 | Source MRR10 | R10 | R20 | Judgments |
|---|---:|---:|---:|---:|---|
| Baseline | 0.7176 | 0.6967 | 0.86 | 0.89 | Complete |
| 25% | 0.7056 | 0.6697 | 0.85 | 0.88 | Complete |
| 50% | 0.6960 | 0.6466 | 0.85 | 0.87 | Provisional |
| 75% | 0.6800 | 0.6064 | 0.84 | 0.88 | Provisional |

The fully judged25% setting's paired nDCG interval is[-0.023295,-0.001640].
Grade0 first results increase from4 to7/8/8. The75% setting also worsens one
known-item target from1->2. Missing pair `q-keyword-085 / 2512.20578` affects
the50% and75% settings; their graded comparisons remain withheld.

### Semantic fields: conservative first-stage results are inconclusive

Use the local GTE-small model, revision
`17e1f347d17fe144873b1201da91788898c639cd`, to embed query, title, abstract and
concatenated title+abstract independently. Candidate document vectors are cached,
normalized and validated against IDs, text and model revision. No OpenAI field
embedding calls were made.

The same-model concat control has `F=(cos(query,title+abstract)+1)/2`.
Separate fields use `F=[t*cos(query,title)+(1-t)*cos(query,abstract)+1]/2`
for t=.25/.5/.75. All use the same75% baseline rank /25% field mixture
as the lexical test.

All four semantic settings have **exactly the baseline top10 order**:
nDCG0.717568396, MRR0.696734127, R10/20 .86/.89. Their lower-ranked tails do
change on all100 queries, so the scores are not constant or ignored.
The field signals range .85747-.97954, while the baseline term's adjacent-rank
gaps dominate the differences at the top10. The minimum surviving boundary/
top10 score margins are positive for every configuration.

**This is a no-op at the measured cutoff, not proof that title/abstract
separation is useless or equivalent.** The mixture is too conservative to
test a meaningful top10 change on this snapshot. These are valid reproducible
experiments, but not four independent improvements despite tied leaderboard
positions.

All seven initial settings finished. Cumulative local field-experiment runtime
was4,410.056 seconds (73.5 minutes) over four resumable invocations, including
overlap with cross-encoder inference. It is not a production latency estimate.
See the [field report](../data/results/field-score-dev/report.md).

### Cached follow-up: isolate the semantic ordering signal

After observing the conservative semantic no-op, preregister a separate
follow-up identity rather than changing the completed experiment. Remove the
baseline contribution and sort **only the existing top10** by each of the
four semantic field signals (concat and title weights25/50/75%). Preserve
positions11+ and use baseline order for ties. This directly compares
same-model field representations without adding unjudged papers, extra
inference or paid calls. It cannot change Precision10 or Recall10/20.

| Pure ordering signal | nDCG10 | Paired delta vs baseline [95% CI] | Source MRR10 | Grade0 first |
|---|---:|---|---:|---:|
| Baseline | 0.7176 | Reference | 0.6967 | 4 |
| GTE concat | 0.7057 | -0.01183 [-0.02354,-0.00019] | 0.6216 | 7 |
| GTE separate,25% title | 0.7038 | -0.01379 [-0.02589,-0.00205] | 0.6207 | 8 |
| GTE separate,50% title | 0.6952 | -0.02240 [-0.03548,-0.00979] | 0.5988 | 9 |
| GTE separate,75% title | 0.6767 | -0.04089 [-0.05619,-0.02552] | 0.5269 | 14 |

All four top10s are fully judged, Precision10 stays.689 and Recall10/20 stays
.86/.89 by construction. Individual known-item target ranks regress for
8/9/7/8 queries respectively. Increasing title weight is not a recovery on
this benchmark. Compared with the same-model concat control, separate25%
has nDCG delta-0.00196 with an interval crossing zero;50% and75% have mean
deltas-0.01057 and-0.02906. Separating fields does not demonstrate a gain.

The follow-up took2.034 seconds using the cached scores, with no new model
inference. Parent text/label fingerprints, top10 membership and exact tails
were verified. See the [pure field ordering report](../data/results/field-signal-dev/report.md).

**Combined conclusion:** keep Decision36. Neither this MiniLM cross-encoder
nor these lexical/local-semantic field recipes improves our chosen success
metric. This does not disprove field-aware matching with OpenAI embeddings:
we explicitly measured local GTE fields, not separate OpenAI fields. Do not
silently promote a tied no-op or proceed to an LLM reranker as though the
cross-encoder had shown a general win. A targeted author-input/domain-fit
follow-up or an independent dev set are reasonable next decisions, not
results established by this experiment.
