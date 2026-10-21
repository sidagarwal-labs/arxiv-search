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
