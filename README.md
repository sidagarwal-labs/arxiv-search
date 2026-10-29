# arXiv Search

A search engine and question-answering system for recent arXiv papers in **cs.IR, cs.CL and
cs.LG**. Built for DSBA 6188.

Every design choice is decided by **measuring** it on a test set of queries, not by guessing.

## How it works, in one picture

```
 1. DOWNLOAD     →   2. CLEAN UP     →   3. SEARCH        →   4. TEST          →   5. ANSWER
 arXiv catalog       23,304 papers       BM25 + embeddings     400 test queries     LLM answers
 (raw pages)         (corpus.jsonl)      find top papers       score each method    using top papers
```

## Current working baseline (updated 2026-10-29)

This is our chosen direction, not yet a fully measured end-to-end configuration.
GPT-5.4 mini grades results offline; it is not part of the live search path.

| Component | Selected configuration | Status |
|---|---|---|
| Corpus | 23,304 arXiv papers; title + abstract | Indexed with local models and OpenAI large |
| Keyword retrieval | BM25 exact+stems, authors, title x2; k1=0.8, b=0.75; no stopword removal | Measured on full corpus |
| Embeddings | OpenAI `text-embedding-3-large`, 3,072 dimensions; normalized vectors | Full-corpus vectors cached; new run cost $0.7439 under separate $1.25 cap |
| Hybrid selection + ordering | **RRF55% semantic /45% lexical, c=30, depth100 selects top10; max-normalized score75% semantic /25% lexical using depth500 reorders those ten; tail unchanged** | User-approved Decision36; deterministic, no learned/LLM reranker |
| Relevance judge | OpenAI `gpt-5.4-mini`; blind 0/1/2 pair labels; human labels override | Selected 2026-10-29; expanded 3,294-pair dev pool covered for finalists; older exploratory rows may be provisional; fresh-human validation deferred |
| Evaluation | 100 dev / 300 held-out test queries; source-paper MRR/recall plus graded nDCG and judgment coverage | Full-dev evaluation complete; held-out test untouched |
| Vector storage | Offline NumPy arrays + paper-ID metadata; exact cosine search | Hosted Postgres/pgvector planned, not deployed |
| Reranker / RAG | Local MiniLM cross-encoder and title/abstract ablations tested; no winner; RAG not implemented | Experiments only; not baseline components |

### Best measured scores (keep benchmark scopes separate)

| Measurement | Configuration and scope | Scores |
|---|---|---|
| Full-corpus retrieval reference | BM25 + **GTE-small**, RRF 0.5/0.5, c=10; 23,304 papers, 100 dev queries | MRR@10 **0.635** [0.56, 0.72]; R@1 **0.54**, R@10 **0.80**, R@20 **0.84**; one warm run **26.4 ms/query** |
| Selected embedding pilot | OpenAI large **alone**; 2,000 papers, same 100 dev queries | MRR@10 **0.844** [0.784, 0.902]; R@10 **0.95**, R@20 **0.98**; embedding cost **$0.0701** including queries |
| Selected judge calibration | GPT-5.4 mini vs. 100 human-labeled pairs from 12 dev searches | Exact agreement **77%**; quadratic kappa **0.802**; relevant/not agreement **84%**; **0** opposite 0-vs-2 errors |
| Original OpenAI hybrid control | BM25 + **OpenAI large**, equal-weight RRF c=10; 23,304 papers, 100 dev queries | MRR@10 **0.653** [0.572, 0.737]; R@1 **0.56**, R@10 **0.84**, R@20 **0.90** |
| Original seven-system graded snapshot | Original OpenAI hybrid; GPT-5.4 mini with 100 human overrides | nDCG@10 **0.686** [0.659, 0.712]; P@10 **0.633** [0.595, 0.673]; judged@10 **100%** |
| **Current working baseline** | **RRF shortlist + max-score75% ordering, score depth500**; 100 dev queries, same 3,294-pair snapshot | **nDCG@10 0.7176; P@10 0.689; source MRR@10 0.6967; R@1 0.61; R@10 0.86; R@20 0.89; known-item MRR 0.980** |
| Full-corpus semantic retrieval | OpenAI large alone; same corpus and dev queries | MRR@10 **0.599** [0.518, 0.679]; R@10 **0.82**, R@20 **0.88** |

The pilot has fewer distractors and cannot be compared directly with the full-corpus
reference. Judge agreement measures label quality, not retrieval quality. These are dev
and calibration results, not final held-out scores. Keep the original `bm25-baseline`
unchanged as the historical control.

OpenAI hybrid minus GTE hybrid is **+0.018 MRR** (paired 95% CI
**[-0.028, +0.065]**): promising, not an established gain. Cached query-vector
search took 5.3 ms dense / 8.0 ms hybrid; these exclude the embedding API and
are not live serving latency. The seven-system graded dev pool contains
2,857 unique query-paper pairs, now fully covered. OpenAI hybrid minus GTE
hybrid is **+0.030 nDCG** [0.007, 0.055] under these labels; the gain over
OpenAI dense alone is uncertain (+0.018 [-0.011, 0.046]).

Full experiment tables, confidence intervals, usage and caveats: [Results](docs/05-results.md).
Current selection rationale: [Decision 36](docs/02-decisions.md#36-recall-preserving-shortlist-score-baseline-promoted-2026-10-29).
Progress visualization: [Hill-climbing charts and latest scores](docs/06-charts.md).

**All experiments in one leaderboard:** [Dev leaderboard](docs/05-results.md#unified-dev-scorecard).
It includes saved BM25, dense, hybrid, rank-fusion, score-fusion and depth experiments
regardless of registry membership, with source and graded metrics on one shared
label snapshot. Fully judged runs rank by descending **nDCG@10**, our primary success
metric; incomplete runs are separate, unranked diagnostics. Readable keyword-retrieval,
embedding-model and ranker/fusion columns explain each technique; original IDs remain
in expandable details and machine reports. Historical tables and smaller-corpus pilots
remain separately scoped.

**Challenger review:** max-normalized score fusion (75% semantic, depth500) leads
at nDCG0.7197 and source MRR0.6916, but source R@10 falls0.86 to0.82
(four lost targets, no gained targets), and R@20 falls0.89 to0.84.
All25 known-item target ranks stay unchanged. **Unrestricted score fusion remains
a challenger.** Sid instead approved the recall-preserving shortlist-score baseline:
nDCG0.7176 and MRR0.6967 with R@10/20 unchanged from RRF. All25 known-paper
target ranks are individually unchanged. The new helper requires descending raw
BM25/cosine score mappings, not just ranks. Frozen historical experiments retain
the previous RRF control and reports.
[Loss review](data/results/score-candidate-review-dev/report.md) and
[explanation](docs/03-findings.md#22-leaderboard-and-score-fusion-challenger-loss-review).
The label-collection UI is deferred; the existing 100 human labels remain our
calibration set. Sid has now approved local cross-encoder and title/abstract
field-score experiments to test new relevance signals; the working baseline
remains unchanged. **All16 new settings completed locally; no improvement
warranted promotion.** The fully judged cross-encoder top10 test regresses
nDCG0.7176->0.7021; pure semantic title/abstract ordering and independent
lexical field mixtures also underperform. Broader-pool graded scores remain
coverage-gated; no new paid calls were made.
See the [cross-encoder findings](docs/03-findings.md#24-query-document-interaction-first-local-cross-encoder)
and [field-score findings](docs/03-findings.md#25-separate-titleabstract-field-scores).
LLM reranking and a new dev set are later steps.
The subsequent **OpenAI-large field test** used separate title/abstract vectors
for7,644 candidate papers, costing an accounted**$0.2707**. A cached hybrid
follow-up with25% title /75% abstract semantic weights reaches mean
**nDCG0.7204, MRR0.7047**, retaining lexical evidence and the existing top10
membership. Its nDCG gain interval crosses zero and paraphrase quality regresses:
**challenger only; Decision36 remains approved**. Higher title weights hurt.
See the [same-model field findings](docs/03-findings.md#26-openai-large-titleabstract-candidate-experiment).
Repeated global fusion tuning is showing diminishing returns.
See the [experiment/promotion findings](docs/03-findings.md#23-rankscore-experiments-and-recall-preserving-baseline)
and [interaction experiment design](docs/02-decisions.md#37-local-query-document-interaction-and-field-score-experiments-2026-10-29).

## Progress

- [x] 1. Download papers from arXiv
- [x] 2. Clean up into one file of 23,304 papers
- [x] 3. Search: BM25 baseline → BM25 variants → local/OpenAI embeddings → tuned hybrid + shortlist ordering (working dev nDCG: 0.7176; source MRR: 0.6967)
- [ ] 4. Test: scoring metrics ✅, 400 test queries ✅, results table ✅, GPT-5.4 mini selected ✅, full-dev graded evaluation ✅; fresh-human validation deferred; final held-out test untouched
- [ ] 5. Answer: RAG with an LLM
- [ ] 6. Website: database, API, web page, deploy

## Read more

| Doc | What's in it |
|---|---|
| [How it works](docs/01-how-it-works.md) | Every step and every file in plain English, plus the folder layout |
| [Decisions](docs/02-decisions.md) | Every choice we made and why |
| [Findings](docs/03-findings.md) | Measurements behind the decisions |
| [Glossary](docs/04-glossary.md) | What BM25, embedding, MRR, etc. mean |
| [Results](docs/05-results.md) | One table comparing every search system we've tried |
| [Charts](docs/06-charts.md) | Hill-climbing milestones, latest leaderboard leaders and measured remaining headroom |

## Run it

```powershell
# One-time setup
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,experiments]"   # experiments = embedding models
copy .env.example .env        # then paste your Gemini API key into .env

# Step 1: download (~20 min; if it stops, run again to resume)
.\.venv\Scripts\python.exe -m arxiv_search.ingest.download

# Step 2: clean up → data/processed/corpus.jsonl
.\.venv\Scripts\python.exe -m arxiv_search.ingest.clean

# Step 4b: write 400 test queries with an LLM → data/eval/ (~3 h on the free tier; resumable)
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.make_queries
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.split    # 100 dev / 300 test

# Step 4c: run search systems on the dev queries → docs/05-results.md (seconds each)
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.experiments "bm25*"   # all 25 BM25 systems
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.experiments "dense*"  # 4 embedding models (several hours first time; cached after)
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.experiments --hybrid-grid  # 24 blends of saved dev top-100 rankings
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.experiments --list    # what systems exist

# Step 4d: LLM relevance judge (resumable; see docs/01-how-it-works.md)
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.judge --judge gemma-31b --queries pilot
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.judge_pilot report   # agreement with human grades

# OpenAI pilots: set OPENAI_API_KEY in .env first (never commit a key)
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.judge --judge openai-nano --queries human --max-calls 1
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.judge --judge openai-mini --queries human --max-calls 1
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.embedding_pilot       # offline token/cost preflight
# Add --run only for the approved $0.25 total embedding pilot, not a full-corpus run
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.openai_full          # full-corpus cache/budget preflight
# openai_full --run uses a separate approved $1.25 lifetime cap; completed inputs are cached
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.graded                # score cached dev labels only
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.graded --label --max-calls 20  # selected judge, resumable
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.graded --judge openai-mini --label --max-calls 20  # selected GPT-5.4 mini, shared token cap

# Run the tests
.\.venv\Scripts\python.exe -m pytest -q
```

### Quick offline experiment loop

```powershell
# Cached rankings only: 38 lexical/semantic fusion settings, no API calls
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.fusion_experiment
# Frozen-baseline segment comparisons and concrete failure evidence, no API calls
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.failure_analysis
# Pre-promotion review of 55%/c30 versus original, 75%/c100 and 60%/c60; no API calls
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.fusion_review
# Score-based fusion, top-rank bonuses and top500 retrieval; cached embeddings, no API calls
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.score_fusion_experiment
# Persist all24 finer rank-fusion settings for the unified scorecard, no API calls
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.fusion_refinement
```

Fusion outputs live under `data/results/fusion-dev/`, separate from the frozen
baseline. The first grid expands the pool from 2,857 to 3,190 pairs: **333
additional pairs need labels**. Until then, reports are provisional and paired
winner comparisons are withheld. The additional labeling batch was approved
after budget clarification: effective cumulative text-token cap 1,600,000,
with existing usage retained. Offline experiments do not spend tokens or re-embed papers.

The approved batch is complete: **3,190/3,190 pairs covered**, 333 added labels
using 153,596 tokens. Best observed grid candidate: **75% semantic / 25%
lexical, RRF c=100, depth=100**, nDCG@10 **0.709**, P@10 **0.690**.
The unchanged baseline rescored on this expanded pool has nDCG **0.664**;
paired gain **+0.045 [0.028, 0.064]**. Its original 0.686 used a smaller
ideal-relevance pool and is not directly comparable. Source-paper MRR falls
from **0.653 to 0.618**, so this is a quality tradeoff, not universal dominance.
The candidate was selected on dev among 38 settings; selection uncertainty
is not captured by its unadjusted interval. The original baseline stays frozen.

The finer cached review led to user approval of **55% semantic / 45% lexical,
RRF c=30, depth=100** as the **new working baseline on 2026-10-29**.
It preserves every original known-item target rank (MRR 0.980), with overall
nDCG 0.7106, P@10 0.689 and source MRR 0.6459. Keyword source MRR still
decreases versus the original control, despite improved keyword graded relevance.
The 60%/c60 option has slightly higher nDCG but weaker exact-target performance.
All four finalists have complete top-10 coverage on the same frozen snapshot.
Reproducible scorecards, paired intervals, all source-rank changes and largest
gain/loss evidence are in `data/results/fusion-review-dev/`.
See [the pre-promotion findings](docs/03-findings.md#20-pre-promotion-review-of-the-55c30-candidate)
for the remaining tradeoffs; no held-out test evaluation has been run.

The selected profile is versioned as `WORKING_BASELINE_*` in `arxiv_search/config.py`;
`fuse_working_baseline` applies it to best-BM25/OpenAI-large rankings.
Generic `fuse` defaults and historical experiment controls stay unchanged.
The saved pre-promotion report remains a historical review, not a mutable
promotion record. Approval is recorded in Decision35; live serving is not deployed.

The next16 experiments are complete, including104 approved additional GPT-5.4-mini
judgments (55,489 tokens; unchanged1,600,000 cumulative cap). The shared pool now
has3,294 pairs. On this larger denominator, unchanged working-baseline nDCG is
0.7064 (previously0.7106); rankings, P@10 and source metrics did not change.
Best observed new candidate is **max-normalized score fusion,75% semantic,
depth500**: nDCG0.7197, P@10 0.697, source MRR0.6916, known-item MRR0.980.
Source R@10 falls0.86 to0.82, so it is **not promoted**. See
[score/depth findings](docs/03-findings.md#21-score-based-fusion-top-rank-bonuses-and-candidate-depth)
and the unified scorecard before comparing numbers from different snapshots.

## Folders

```
arxiv_search/       the system (settings in config.py)
tests/              automatic checks
experiments/        one-off measurements
docs/               explanations
data/               downloaded + processed data (not in git; rebuilt by the steps above)
```
