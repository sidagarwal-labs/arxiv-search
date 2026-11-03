# Experiment log

This page keeps the detailed experiment summary that used to live in the README.
All scores use the 100 development queries unless a row says otherwise. Settings
were chosen by testing repeatedly on those queries, so the scores are optimistic.
The 300 held-out test queries have not been run.

For the full leaderboard, confidence intervals and caveats, see [Results](05-results.md).
For the reasoning behind each choice, see [Decisions](02-decisions.md) and
[Findings](03-findings.md).

## Best measured scores by scope

Keep benchmark scopes separate: these rows use different corpora, label pools or purposes.

| Measurement | Configuration and scope | Scores |
|---|---|---|
| Full-corpus retrieval reference | BM25 + **GTE-small**, RRF 0.5/0.5, c=10; 23,304 papers, 100 dev queries | MRR@10 **0.635** [0.56, 0.72]; R@1 **0.54**, R@10 **0.80**, R@20 **0.84**; one warm run **26.4 ms/query** |
| Selected embedding pilot | OpenAI large **alone**; 2,000 papers, same 100 dev queries | MRR@10 **0.844** [0.784, 0.902]; R@10 **0.95**, R@20 **0.98**; embedding cost **$0.0701** including queries |
| Selected judge calibration | GPT-5.4 mini vs. 100 human-labeled pairs from 12 dev searches | Exact agreement **77%**; quadratic kappa **0.802**; relevant/not agreement **84%**; **0** opposite 0-vs-2 errors |
| Original OpenAI hybrid control | BM25 + **OpenAI large**, equal-weight RRF c=10; 23,304 papers, 100 dev queries | MRR@10 **0.653** [0.572, 0.737]; R@1 **0.56**, R@10 **0.84**, R@20 **0.90** |
| Original seven-system graded snapshot | Original OpenAI hybrid; GPT-5.4 mini with 100 human overrides | nDCG@10 **0.686** [0.659, 0.712]; P@10 **0.633** [0.595, 0.673]; judged@10 **100%** |
| **Current working baseline** | **RRF shortlist + max-score 75% ordering, score depth 500**; 100 dev queries, same 3,294-pair snapshot | **nDCG@10 0.7176; P@10 0.689; source MRR@10 0.6967; R@1 0.61; R@10 0.86; R@20 0.89; known-item MRR 0.980** |
| Full-corpus semantic retrieval | OpenAI large alone; same corpus and dev queries | MRR@10 **0.599** [0.518, 0.679]; R@10 **0.82**, R@20 **0.88** |

The pilot has fewer distractors and cannot be compared directly with the full-corpus
reference. Judge agreement measures label quality, not retrieval quality. These are
development and calibration results, not final held-out scores. The original
`bm25-baseline` stays unchanged as the historical control.

OpenAI hybrid minus GTE hybrid is **+0.018 MRR** (paired 95% CI
**[-0.028, +0.065]**): promising, not an established gain. Cached query-vector
search took 5.3 ms dense / 8.0 ms hybrid; these exclude the embedding API and
are not live serving latency. The seven-system graded dev pool contains
2,857 unique query-paper pairs, now fully covered. OpenAI hybrid minus GTE
hybrid is **+0.030 nDCG** [0.007, 0.055] under these labels; the gain over
OpenAI dense alone is uncertain (+0.018 [-0.011, 0.046]).

## Fusion grid and label expansion

Fusion outputs live under `data/results/fusion-dev/`, separate from the frozen
baseline. The first grid expanded the pool from 2,857 to 3,190 pairs, so
**333 additional pairs needed labels** before winners could be compared. That
labeling batch ran under an effective cumulative text-token cap of 1,600,000,
with existing usage counted. Offline experiments do not spend tokens or re-embed papers.

The batch completed with **3,190/3,190 pairs covered**: 333 added labels using
153,596 tokens. The best observed grid candidate was **75% semantic / 25% lexical,
RRF c=100, depth=100**, with nDCG@10 **0.709** and P@10 **0.690**. The unchanged
baseline rescored on this expanded pool has nDCG **0.664**; paired gain
**+0.045 [0.028, 0.064]**. Its original 0.686 used a smaller ideal-relevance pool
and is not directly comparable. Source-paper MRR falls from **0.653 to 0.618**, so
this is a quality tradeoff, not universal dominance. The candidate was selected on
dev among 38 settings; its unadjusted interval does not capture selection
uncertainty. The original baseline stays frozen.

## RRF 55% / c=30 working baseline (Decision 35)

The finer cached review selected **55% semantic / 45% lexical, RRF c=30,
depth=100** as the **working baseline on 2026-10-29**. It preserves every original
known-item target rank (MRR 0.980), with overall nDCG 0.7106, P@10 0.689 and
source MRR 0.6459. Keyword source MRR still decreases versus the original control,
despite improved keyword graded relevance. The 60%/c60 option has slightly higher
nDCG but weaker exact-target performance. All four finalists have complete top-10
coverage on the same frozen snapshot. Reproducible scorecards, paired intervals,
all source-rank changes and the largest gain/loss evidence are in
`data/results/fusion-review-dev/`. See
[the pre-promotion findings](03-findings.md#20-pre-promotion-review-of-the-55c30-candidate)
for the remaining tradeoffs.

The selected profile is versioned as `WORKING_BASELINE_*` in `arxiv_search/config.py`;
`fuse_working_baseline` applies it to best-BM25/OpenAI-large rankings. Generic
`fuse` defaults and historical experiment controls stay unchanged. The saved
pre-promotion report remains a historical review, not a mutable promotion record.
The selection is recorded in Decision 35; live serving is not deployed.

## Score-based fusion and candidate depth

The next 16 experiments are complete, including 104 additional GPT-5.4 mini
judgments (55,489 tokens; unchanged 1,600,000 cumulative cap). The shared pool
now has 3,294 pairs. On this larger denominator, the unchanged working-baseline
nDCG is 0.7064 (previously 0.7106); rankings, P@10 and source metrics did not
change. The best observed new candidate is **max-normalized score fusion,
75% semantic, depth 500**: nDCG 0.7197, P@10 0.697, source MRR 0.6916 and
known-item MRR 0.980. Source R@10 falls from 0.86 to 0.82, so it was
**not promoted**. See
[score/depth findings](03-findings.md#21-score-based-fusion-top-rank-bonuses-and-candidate-depth)
and the unified scorecard before comparing numbers from different snapshots.

## Recall-preserving shortlist-score baseline (Decision 36)

Unrestricted max-normalized score fusion (75% semantic, depth 500) leads at
nDCG 0.7197 and source MRR 0.6916, but source R@10 falls from 0.86 to 0.82
(four lost targets, no gained targets), and R@20 falls from 0.89 to 0.84.
All 25 known-item target ranks stay unchanged. **Unrestricted score fusion
remains a challenger.**

The selected alternative keeps the RRF top-10 membership and reorders only those
ten papers by score: nDCG 0.7176 and MRR 0.6967, with R@10 and R@20 unchanged from
RRF. All 25 known-paper target ranks are individually unchanged. The helper
requires descending raw BM25/cosine score mappings, not just ranks. Frozen
historical experiments retain the previous RRF control and reports. See the
[loss review](../data/results/score-candidate-review-dev/report.md) and
[explanation](03-findings.md#22-leaderboard-and-score-fusion-challenger-loss-review).

The label-collection UI is deferred; the existing 100 human labels remain the
calibration set.

## Cross-encoder and field-score experiments

Local cross-encoder and title/abstract field-score experiments tested new relevance
signals; the working baseline remained unchanged. **All 16 new settings completed
locally; none warranted promotion.** The fully judged cross-encoder top-10 test
regresses nDCG from 0.7176 to 0.7021; pure semantic title/abstract ordering and
independent lexical field mixtures also underperform. Broader-pool graded scores
remain coverage-gated; no new paid calls were made. See the
[cross-encoder findings](03-findings.md#24-query-document-interaction-first-local-cross-encoder)
and [field-score findings](03-findings.md#25-separate-titleabstract-field-scores).
LLM reranking and a new dev set were left as later steps.

## OpenAI-large title and abstract fields

The OpenAI-large field test used separate title/abstract vectors for 7,644
candidate papers, costing an accounted **$0.2707**. A cached hybrid follow-up with
25% title / 75% abstract semantic weights reaches mean **nDCG 0.7204,
MRR 0.7047**, retaining lexical evidence and the existing top-10 membership. Its
nDCG gain interval crosses zero and paraphrase quality regresses, so it is
**a challenger only; Decision 36 remains the working baseline**. Higher title
weights hurt. See the
[same-model field findings](03-findings.md#26-openai-large-titleabstract-candidate-experiment).

The [promotion investigation](03-findings.md#27-field-aware-challenger-investigation-before-promotion)
verified all 100 rankings and found that much of the paraphrase source-MRR drop
comes from alternate relevant answers, but genuine graded losses and uncertainty
remain. The challenger is frozen; promotion is still pending.

The [cached paraphrase-recovery experiment](03-findings.md#28-recovering-paraphrases-without-query-type-routing)
finds a 50% combined-text anchor with nDCG 0.7202 and all four segment mean nDCGs
above baseline. A 10%-title variant reaches 0.7214 but regresses question nDCG.
Neither passes promotion; uncertainty and source-MRR tradeoffs remain.

## Question audit and LLM reranker pilots

The [question audit and next-step hypothesis](03-findings.md#29-question-audit-and-the-next-substantial-quality-improvement)
identify task/constraint matching and deeper candidate selection as the next
quality targets: 133 known highly relevant query-paper pairs sit in positions
11-50. A blinded label audit is still pending.

The [mini-LLM pilot](03-findings.md#30-mini-llm-pilot-results-and-output-reliability)
attempted 40 requests for an accounted $0.3757 with no retries. Only 23 responses
passed the strict output contract, leaving 7 matched queries; top-50 graded
quality is incomplete. It is not a new baseline or a 100-query leaderboard entry.

The [fixed-key v2 rerun](03-findings.md#31-fixed-key-reranker-v2-reliable-output-and-pilot-quality)
then passed **40/40** responses with no retries. On the same 20-query pilot,
top-10 nDCG improves from 0.7055 to 0.7194; top-50 still loses one source hit and
has 34 unjudged selected pairs. V2 costs an accounted $0.3326, bringing both
pilots to $0.7083 combined. Decision 36 remains the working baseline.

The [gap fill](03-findings.md#31a-top50-after-filling-the-34-missing-judgments)
graded those 34 pairs with the frozen judge ($0.0185, 15 calls, no failures).
With all three systems fully judged on the same child labels, top-50 reaches
nDCG@10 **0.7553** vs. baseline 0.6959 (+0.059 [+0.001, +0.116]) and P@10 0.770
vs. 0.675, but source MRR still falls 0.8375 → 0.6875. The judge and reranker
share a model family, so this is a reason to stabilize top-50, not to promote it.

A free [offline safeguard](03-findings.md#31b-why-top50-loses-and-an-offline-safeguard)
fuses the top-50 LLM order with the baseline order (RRF, c=30, rule frozen before
computing). It keeps most of the gain (nDCG@10 about 0.733 vs. 0.696) while
restoring source MRR to 0.829 (baseline 0.8375); both pre-registered criteria pass.

On the [full dev set](03-findings.md#31c-full-dev-set-the-safeguard-holds-on-80-unseen-queries)
the same method and rule hold: on the 80 queries not used to design the rule,
the safeguard reaches nDCG@10 **0.7643** vs. 0.7125 (+0.052 [+0.035, +0.069]) with
source MRR 0.692 vs. 0.662; on all 100, 0.7583 vs. 0.7092. Cost $1.10 reranking
plus $0.07 judging, no failures. It is the leading candidate; not yet promoted.

A [repeatability check](03-findings.md#31d-repeatability-identical-requests-different-scores)
re-sent 20 identical requests ($0.27): a third of LLM scores moved by a point,
but the safeguard kept a median 9/10 top10 overlap and both runs beat the
baseline. Estimated run-to-run noise on a 100-query mean (SD ≈ .003) is far
below the +.049 gain. The pre-registered 0.01 mean-change guide failed on 20
queries (+.014 to +.021), which we judge too tight for that sample size.

Repeated global fusion tuning is showing diminishing returns. See the
[experiment/promotion findings](03-findings.md#23-rankscore-experiments-and-recall-preserving-baseline)
and [interaction experiment design](02-decisions.md#37-local-query-document-interaction-and-field-score-experiments-2026-10-29).

## Unified leaderboard

The [dev leaderboard](05-results.md#unified-dev-scorecard) includes saved BM25,
dense, hybrid, rank-fusion, score-fusion and depth experiments regardless of
registry membership, with source and graded metrics on one shared label snapshot.
Fully judged runs rank by descending **nDCG@10**, the primary success metric;
incomplete runs are separate, unranked diagnostics. Readable keyword-retrieval,
embedding-model and ranker/fusion columns explain each technique; original IDs
remain in expandable details and machine reports. Historical tables and
smaller-corpus pilots remain separately scoped.
