# Dev leaderboard: all-experiment catalog

176 distinct saved systems; 100 dev queries; current corpus: 23,304 papers. **Two-stage tracking (Decision45):** Stage 1 **retrieval baseline** `fusion-shortlist+a=1+d=500` (Decision36) produces candidates; Stage 2 **reranking baseline** `llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30` reorders its top50. Retrieval experiments compete in Stage 1 (watch R@50 / grade-2 recall@50: what a top-50 reranker can reach); reranker experiments compete in Stage 2 on the same retrieval candidates. **Success score = nDCG@10**, descending using unrounded means; exact ties use stable system ID. Only fully judged runs with defined nDCG receive positions. The baseline stays at its actual position, not pinned first. Provisional runs appear separately, unranked. A leaderboard lead is not automatic baseline promotion.

**Technique guide:** Embedding identifies the vector model; Ranker / fusion identifies how retrieval results are ordered, not a separate LLM reranker. Tuned BM25 means exact terms + stems, authors, title x2, k1=0.8, b=0.75, no stopword removal. RRF uses reciprocal ranks; score fusion combines normalized BM25/cosine values. Depth is candidates per retriever, not final results. Frozen aliases can represent identical rankings under different experiment IDs. Readable names are presentation only: original IDs and files are preserved below.

All graded scores are recomputed from the **same immutable `shared-labels/labels-d46.json`**, including its 100 frozen reference overrides (GPT-6 ASTRA grades; legacy key `human_overrides`, no human labels). **Revised shared ideal-DCG denominator:** approved additive expansion preserves all 3190 original labels and adds 343 labels (239 of them from the shared reranker label layers, latest Decision46 shared layer: LLM-reranker top-10 fills). Every system is rescored against this expanded denominator; original reports remain unchanged and their nDCG values must not be mixed with these revised scores. Other report scores/label pools and later judge-cache or workbook changes are NOT combined. Linear-gain nDCG@10 uses that shared ideal DCG; undefined queries are excluded only from nDCG (n shown). P@10 counts grades ≥1 with denominator 10. Unjudged gains count as zero. judged@10 is the judged fraction of returned results; short/missing lists still fail the full top-10 coverage gate. R@50 = source paper in the top 50; grade-2 recall@50 = share of known grade-2 papers in the top 50 (judged pool only, so an upper-bound-style reachability check for a top-50 reranker, not a complete recall).

**PROVISIONAL** means a dev top-10 position is missing or unjudged: source-paper MRR/recall remain valid on the full dev denominator (missing queries score zero), but graded scores are lower-bound diagnostics, not winner evidence. Paired nDCG against the CURRENT retrieval baseline is withheld unless BOTH runs have every dev top-10 position judged. Intervals are exploratory query bootstraps conditional on these labels, not judge accuracy; no multiple-testing correction or test-query scoring. Known-item MRR is source-paper MRR on that type only.

**Snapshot/corpus caveat:** these are saved rankings, not fresh retrieval. Current corpus and dev-query fingerprints, the frozen label SHA256, ranking fingerprints, and all duplicate paths are recorded in the machine report. Older runs may not record a corpus fingerprint; matching paper IDs cannot prove identical build snapshots. Reduced-corpus embedding pilots are a separate scope, never scorecard rows. Costs/latencies are not estimated or assigned zero: only actually saved `.info.json` metadata is preserved per system, with its original timing scope. Historical reports retain their original labels, denominators, and controls.

### Stage 1 — retrieval progress

Retrieval baseline: `fusion-shortlist+a=1+d=500` (Decision36). Free and deterministic, so every retrieval idea is tested here first. R@50 and grade-2 recall@50 show what the top-50 reranker can reach.

**Milestones** (each step changed several settings, so gains are not isolated effects of one feature):

| Step | System | nDCG@10 | Δ vs previous | P@10 | Source MRR@10 | R@10 | R@50 | Grade-2 recall@50 |
|---|---|---|---|---|---|---|---|---|
| Tuned BM25 | `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | 0.5090 | — | 0.512 | 0.569 | 0.710 | 0.770 | 0.691 |
| GTE dense | `dense-gte-small` | 0.5688 | +0.0598 | 0.581 | 0.525 | 0.710 | 0.870 | 0.706 |
| GTE hybrid | `hybrid-gte-small+rrf+w=0.5+c=10` | 0.6188 | +0.0499 | 0.611 | 0.635 | 0.800 | 0.880 | 0.819 |
| OpenAI hybrid | `hybrid-openai-large+rrf+w=0.5+c=10` | 0.6476 | +0.0288 | 0.633 | 0.653 | 0.840 | 0.940 | 0.945 |
| RRF75 c100 | `fusion-rrf+w=0.75+d=100+c=100` | 0.6913 | +0.0438 | 0.690 | 0.618 | 0.840 | 0.940 | 0.928 |
| RRF55 c30 | `fusion-rrf+w=0.55+d=100+c=30` | 0.6925 | +0.0012 | 0.689 | 0.646 | 0.860 | 0.940 | 0.952 |
| **Shortlist scores (RETRIEVAL BASELINE)** | `fusion-shortlist+a=1+d=500` | 0.7036 | +0.0111 | 0.689 | 0.697 | 0.860 | 0.940 | 0.952 |

**Current top 5 retrieval systems** (fully judged; a lead inside the confidence interval is not a promotion):

| Rank | System | nDCG@10 | Δ vs retrieval baseline [95% CI] | P@10 | Source MRR@10 | R@10 | R@50 | Grade-2 recall@50 |
|---|---|---|---|---|---|---|---|---|
| 1 | OpenAI-large paraphrase recovery<br>`oai-field-recovery+text=title10+anchor=0+d=10` | 0.707 | +0.004 [-0.001, +0.009] | 0.689 | 0.698 | 0.860 | 0.940 | 0.952 |
| 2 | OpenAI-large paraphrase recovery<br>`oai-field-recovery+text=abstract+anchor=0+d=10` | 0.707 | +0.003 [-0.002, +0.009] | 0.689 | 0.680 | 0.860 | 0.940 | 0.952 |
| 3 | OpenAI-large paraphrase recovery<br>`oai-field-recovery+text=title25+anchor=0.5+d=10` | 0.706 | +0.003 [-0.000, +0.006] | 0.689 | 0.694 | 0.860 | 0.940 | 0.952 |
| 4 | OpenAI-large semantic field ablation<br>`oai-field-hybrid+text=title25+d=10` | 0.706 | +0.003 [-0.002, +0.007] | 0.689 | 0.705 | 0.860 | 0.940 | 0.952 |
| 5 | OpenAI-large paraphrase recovery<br>`oai-field-recovery+text=title25+anchor=0+d=10` | 0.706 | +0.003 [-0.002, +0.007] | 0.689 | 0.705 | 0.860 | 0.940 | 0.952 |
| 13 | **Fixed-shortlist score ordering (RETRIEVAL BASELINE)**<br>`fusion-shortlist+a=1+d=500` | 0.704 | itself | 0.689 | 0.697 | 0.860 | 0.940 | 0.952 |

### Stage 2 — reranker progress

Reranking baseline: `llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30` (Decision46): gpt-5.4-mini-2026-03-17 scores the retrieval top50 in 2 identical requests whose scores are averaged, fused with the retrieval order by RRF c=30. Decision45's single-pass system stays as a control row.

**Pilot history** — the same 20 dev queries, rescored on the shared labels. Missing rankings (failed LLM responses) score zero, so they show the reliability problem as well as quality. These queries were used to design the safeguard rule, so they are not the evidence for it.

| Step | Method | Valid rankings | nDCG@10 | Δ vs retrieval baseline (W/L) | P@10 | Source MRR@10 | Unjudged top-10 pairs | Report |
|---|---|---|---|---|---|---|---|---|
| 0 | Retrieval baseline, no reranker | 20/20 | 0.6904 | — | 0.675 | 0.838 | 0 | — |
| 1 | v1 listwise order, top10 | 16/20 | 0.5781 | -0.1123 (9/10) | 0.535 | 0.700 | 0 | [report](../llm-reranker-pilot/report.md) |
| 2 | v1 listwise order, top50 | 7/20 | 0.2530 | -0.4375 (2/17) | 0.235 | 0.208 | 13 | [report](../llm-reranker-pilot/report.md) |
| 3 | v2 0-4 scores, top10 | 20/20 | 0.7036 | +0.0131 (13/4) | 0.675 | 0.842 | 0 | [report](../llm-score-pilot/report.md) |
| 4 | v2 0-4 scores, top50 | 20/20 | 0.7503 | +0.0598 (13/4) | 0.770 | 0.688 | 0 | [report](../llm-score-pilot/report.md) |
| 5 | v2 top50 + RRF safeguard c30 | 20/20 | 0.7290 | +0.0386 (11/6) | 0.720 | 0.829 | 0 | [report](../llm-score-pilot/safeguard/report.md) |

**Full dev set (100 queries)** — every row reranks the same retrieval-baseline candidates. Paired deltas against BOTH baselines. LLM cost and API time are measured means over uncached requests; saved rankings replay cached responses (LLM scores are not deterministic). Differences smaller than the MDD (1.96·√2·SD of the 100-query mean, from the Decision44 repeat run) are within run-to-run noise.

| Rank | System | Stage 1 retrieval | Stage 2 reranker | Status | nDCG@10 (n) | P@10 | Source MRR@10 | R@1 | R@10 | Δ nDCG vs retrieval baseline [95% CI] W/L | Δ nDCG vs reranking baseline [95% CI] W/L | LLM $/query | API s/query | Run-to-run noise (SD of 100-q mean; MDD) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2-pass LLM reranker (scores only)<br>`llm-mini-score-pilot+d=50+avg2` | Retrieval baseline (Decision36) | GPT-5.4 mini scores retrieval-baseline top50 0-4, average of two independent requests; sort by score, ties keep retrieval order | covered | 0.7877 (100) | 0.788 | 0.686 | 0.570 | 0.880 | +0.084 [+0.057, +0.111] W/L 73/22 | +0.019 [+0.002, +0.036] W/L 56/39 | $0.0275 | parallel | unmeasured |
| 2 | LLM reranker + rank blend<br>`llm-mini-score-pilot+d=50+blend-rank-prior+b=2+c=30` | Retrieval baseline (Decision36) | GPT-5.4 mini scores retrieval-baseline top50 0-4, one request; sort by score + 2·31/(30+retrieval rank), ties keep retrieval order | covered | 0.7742 (100) | 0.777 | 0.686 | 0.580 | 0.880 | +0.071 [+0.046, +0.096] W/L 68/22 | +0.006 [-0.010, +0.022] W/L 54/38 | $0.0138 | 2.48 | unmeasured |
| 3 | LLM reranker (scores only)<br>`llm-mini-score-pilot+d=50` | Retrieval baseline (Decision36) | GPT-5.4 mini scores retrieval-baseline top50 0-4, one request; sort by score, ties keep retrieval order | covered | 0.7726 (100) | 0.777 | 0.677 | 0.570 | 0.880 | +0.069 [+0.044, +0.095] W/L 68/22 | +0.004 [-0.013, +0.020] W/L 54/38 | $0.0138 | 2.48 | 0.0063; 0.018 |
| 4 | LLM reranker + rank blend<br>`llm-mini-score-pilot+d=50+blend-rank-prior+b=3+c=30` | Retrieval baseline (Decision36) | GPT-5.4 mini scores retrieval-baseline top50 0-4, one request; sort by score + 3·31/(30+retrieval rank), ties keep retrieval order | covered | 0.7719 (100) | 0.767 | 0.697 | 0.590 | 0.890 | +0.068 [+0.046, +0.091] W/L 71/19 | +0.003 [-0.010, +0.017] W/L 49/43 | $0.0138 | 2.48 | unmeasured |
| 5 | **2-pass LLM reranker + safeguard (RERANKING BASELINE)**<br>`llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30` | Retrieval baseline (Decision36) | GPT-5.4 mini scores retrieval-baseline top50 0-4, average of two independent requests; RRF of LLM order with retrieval order, c30 | covered | 0.7684 (100) | 0.751 | 0.723 | 0.630 | 0.870 | +0.065 [+0.048, +0.081] W/L 76/16 | itself | $0.0275 | parallel | unmeasured |
| 6 | LLM reranker + rank blend<br>`llm-mini-score-pilot+d=50+blend-rank-prior+b=4+c=30` | Retrieval baseline (Decision36) | GPT-5.4 mini scores retrieval-baseline top50 0-4, one request; sort by score + 4·31/(30+retrieval rank), ties keep retrieval order | covered | 0.7639 (100) | 0.753 | 0.702 | 0.590 | 0.890 | +0.060 [+0.040, +0.081] W/L 69/21 | -0.005 [-0.017, +0.008] W/L 44/46 | $0.0138 | 2.48 | unmeasured |
| 7 | LLM reranker + safeguard<br>`llm-mini-score-pilot+d=50+rrf-baseline+c=30` | Retrieval baseline (Decision36) | GPT-5.4 mini scores retrieval-baseline top50 0-4, one request; RRF of LLM order with retrieval order, c30 | covered | 0.7521 (100) | 0.736 | 0.720 | 0.640 | 0.870 | +0.049 [+0.034, +0.063] W/L 69/21 | -0.016 [-0.024, -0.009] W/L 22/57 | $0.0138 | 2.48 | 0.0033; 0.009 |
| 8 | **Fixed-shortlist score ordering (RETRIEVAL BASELINE, no reranker)**<br>`fusion-shortlist+a=1+d=500` | Retrieval baseline (Decision36) | None | covered | 0.7036 (100) | 0.689 | 0.697 | 0.610 | 0.860 | itself | -0.065 [-0.081, -0.048] W/L 16/76 | $0.0000 | 0.00 | deterministic |

### Stage 1 — full retrieval leaderboard (fully judged)

| Rank | System | Keyword retrieval | Embedding | Ranker / fusion | Status | Success: nDCG@10 (n) | P@10 | judged@10 | Source MRR@10 | R@1 | R@5 | R@10 | R@20 | R@50 | Grade-2 recall@50 | Known-item MRR@10 | Δ nDCG vs retrieval baseline [95% CI] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | OpenAI-large paraphrase recovery | Tuned BM25 including authors/title2x | OpenAI text-embedding-3-large | 25% lexical / 75% semantic; 10% title / 90% abstract; 0% combined-text anchor; candidate-max normalization; reorder baseline top10 only, preserve tail | covered | 0.7071 (100) | 0.689 | 1.000 | 0.698 | 0.620 | 0.790 | 0.860 | 0.890 | 0.940 | 0.952 | 0.980 | +0.004 [-0.001, +0.009] |
| 2 | OpenAI-large paraphrase recovery | Tuned BM25 including authors/title2x | OpenAI text-embedding-3-large | 25% lexical / 75% semantic; abstract only; 0% combined-text anchor; candidate-max normalization; reorder baseline top10 only, preserve tail | covered | 0.7067 (100) | 0.689 | 1.000 | 0.680 | 0.580 | 0.790 | 0.860 | 0.890 | 0.940 | 0.952 | 0.980 | +0.003 [-0.002, +0.009] |
| 3 | OpenAI-large paraphrase recovery | Tuned BM25 including authors/title2x | OpenAI text-embedding-3-large | 25% lexical / 75% semantic; 25% title / 75% abstract; 50% combined-text anchor; candidate-max normalization; reorder baseline top10 only, preserve tail | covered | 0.7061 (100) | 0.689 | 1.000 | 0.694 | 0.610 | 0.800 | 0.860 | 0.890 | 0.940 | 0.952 | 0.980 | +0.003 [-0.000, +0.006] |
| 4 | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 25% / abstract 75%; max-score25% lexical / 75% field semantic; reorder baseline top10 only, preserve tail | covered | 0.7061 (100) | 0.689 | 1.000 | 0.705 | 0.640 | 0.780 | 0.860 | 0.890 | 0.940 | 0.952 | 0.980 | +0.003 [-0.002, +0.007] |
| 5 | OpenAI-large paraphrase recovery | Tuned BM25 including authors/title2x | OpenAI text-embedding-3-large | 25% lexical / 75% semantic; 25% title / 75% abstract; 0% combined-text anchor; candidate-max normalization; reorder baseline top10 only, preserve tail | covered | 0.7061 (100) | 0.689 | 1.000 | 0.705 | 0.640 | 0.780 | 0.860 | 0.890 | 0.940 | 0.952 | 0.980 | +0.003 [-0.002, +0.007] |
| 6 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Max-normalized scores; 75% semantic / 25% lexical; depth 500 | covered | 0.7058 (100) | 0.697 | 1.000 | 0.692 | 0.610 | 0.800 | 0.820 | 0.840 | 0.900 | 0.893 | 0.980 | +0.002 [-0.007, +0.012] |
| 7 | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | concatenated title + abstract control; max-score25% lexical / 75% field semantic; reorder baseline top100 only, preserve tail | covered | 0.7053 (100) | 0.697 | 1.000 | 0.692 | 0.610 | 0.800 | 0.820 | 0.840 | 0.910 | 0.923 | 0.980 | +0.002 [-0.007, +0.012] |
| 8 | OpenAI-large paraphrase recovery | Tuned BM25 including authors/title2x | OpenAI text-embedding-3-large | 25% lexical / 75% semantic; 25% title / 75% abstract; 75% combined-text anchor; candidate-max normalization; reorder baseline top10 only, preserve tail | covered | 0.7050 (100) | 0.689 | 1.000 | 0.704 | 0.620 | 0.800 | 0.860 | 0.890 | 0.940 | 0.952 | 0.980 | +0.001 [-0.001, +0.004] |
| 9 | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | concatenated title + abstract control; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 | covered | 0.7036 (100) | 0.689 | 1.000 | 0.697 | 0.610 | 0.800 | 0.860 | 0.890 | 0.940 | 0.953 | 0.980 | +0.000 [+0.000, +0.000] |
| 10 | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | separate title 25% / abstract 75%; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 | covered | 0.7036 (100) | 0.689 | 1.000 | 0.697 | 0.610 | 0.800 | 0.860 | 0.890 | 0.940 | 0.953 | 0.980 | +0.000 [+0.000, +0.000] |
| 11 | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | separate title 50% / abstract 50%; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 | covered | 0.7036 (100) | 0.689 | 1.000 | 0.697 | 0.610 | 0.800 | 0.860 | 0.890 | 0.940 | 0.952 | 0.980 | +0.000 [+0.000, +0.000] |
| 12 | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | separate title 75% / abstract 25%; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 | covered | 0.7036 (100) | 0.689 | 1.000 | 0.697 | 0.610 | 0.800 | 0.860 | 0.890 | 0.940 | 0.952 | 0.980 | +0.000 [+0.000, +0.000] |
| 13 | **Fixed-shortlist score ordering (RETRIEVAL BASELINE)** | Tuned BM25 | OpenAI text-embedding-3-large | RRF55%/c30/depth100 selects top10; order by max-score 75% semantic / 25% lexical at depth 500; preserve tail | covered | 0.7036 (100) | 0.689 | 1.000 | 0.697 | 0.610 | 0.800 | 0.860 | 0.890 | 0.940 | 0.952 | 0.980 | withheld: working baseline itself |
| 14 | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | concatenated title + abstract control; max-score25% lexical / 75% field semantic; reorder baseline top10 only, preserve tail | covered | 0.7035 (100) | 0.689 | 1.000 | 0.697 | 0.610 | 0.800 | 0.860 | 0.890 | 0.940 | 0.952 | 0.980 | -0.000 [-0.000, +0.000] |
| 15 | OpenAI-large paraphrase recovery | Tuned BM25 including authors/title2x | OpenAI text-embedding-3-large | 25% lexical / 75% semantic; combined title + abstract; 100% combined-text anchor; candidate-max normalization; reorder baseline top10 only, preserve tail | covered | 0.7035 (100) | 0.689 | 1.000 | 0.697 | 0.610 | 0.800 | 0.860 | 0.890 | 0.940 | 0.952 | 0.980 | -0.000 [-0.000, +0.000] |
| 16 | Fixed-shortlist score ordering | Tuned BM25 | OpenAI text-embedding-3-large | RRF55%/c30/depth100 selects top10; order by max-score 75% semantic / 25% lexical at depth 100; preserve tail | covered | 0.6999 (100) | 0.689 | 1.000 | 0.674 | 0.590 | 0.770 | 0.860 | 0.890 | 0.940 | 0.952 | 0.980 | -0.004 [-0.009, +0.001] |
| 17 | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 50% / abstract 50%; max-score25% lexical / 75% field semantic; reorder baseline top10 only, preserve tail | covered | 0.6985 (100) | 0.689 | 1.000 | 0.679 | 0.600 | 0.760 | 0.860 | 0.890 | 0.940 | 0.952 | 0.980 | -0.005 [-0.014, +0.003] |
| 18 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Max-normalized scores; 75% semantic / 25% lexical; depth 100 | covered | 0.6975 (100) | 0.686 | 1.000 | 0.668 | 0.590 | 0.760 | 0.820 | 0.870 | 0.940 | 0.922 | 0.980 | -0.006 [-0.017, +0.005] |
| 19 | Rank + score interpolation | Tuned BM25 | OpenAI text-embedding-3-large | 75% max-score75% + 25% normalized RRF55%/c30/d100; score depth 100 | covered | 0.6970 (100) | 0.691 | 1.000 | 0.665 | 0.580 | 0.760 | 0.840 | 0.870 | 0.940 | 0.922 | 0.980 | -0.007 [-0.017, +0.004] |
| 20 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 60% semantic / 40% lexical; depth 100 | covered | 0.6957 (100) | 0.700 | 1.000 | 0.630 | 0.530 | 0.760 | 0.830 | 0.870 | 0.950 | 0.938 | 0.953 | -0.008 [-0.019, +0.004] |
| 21 | Rank + score interpolation | Tuned BM25 | OpenAI text-embedding-3-large | 25% max-score75% + 75% normalized RRF55%/c30/d100; score depth 100 | covered | 0.6933 (100) | 0.692 | 1.000 | 0.646 | 0.550 | 0.770 | 0.850 | 0.880 | 0.950 | 0.937 | 0.980 | -0.010 [-0.019, -0.002] |
| 22 | Fixed-shortlist score ordering | Tuned BM25 | OpenAI text-embedding-3-large | 50% max-score75% + 50% normalized RRF55%/c30/d100; score depth 500; reorder baseline top10 only, preserve tail | covered | 0.6933 (100) | 0.689 | 1.000 | 0.652 | 0.550 | 0.770 | 0.860 | 0.890 | 0.940 | 0.952 | 0.980 | -0.010 [-0.017, -0.004] |
| 23 | Fixed-shortlist score ordering | Tuned BM25 | OpenAI text-embedding-3-large | 50% max-score75% + 50% normalized RRF55%/c30/d100; score depth 100; reorder baseline top10 only, preserve tail | covered | 0.6931 (100) | 0.689 | 1.000 | 0.650 | 0.550 | 0.770 | 0.860 | 0.890 | 0.940 | 0.952 | 0.980 | -0.010 [-0.018, -0.004] |
| 24 | Rank + score interpolation | Tuned BM25 | OpenAI text-embedding-3-large | 50% max-score75% + 50% normalized RRF55%/c30/d100; score depth 500 | covered | 0.6928 (100) | 0.690 | 1.000 | 0.650 | 0.550 | 0.770 | 0.850 | 0.870 | 0.940 | 0.949 | 0.980 | -0.011 [-0.020, -0.002] |
| 25 | Rank + score interpolation | Tuned BM25 | OpenAI text-embedding-3-large | 50% max-score75% + 50% normalized RRF55%/c30/d100; score depth 100 | covered | 0.6928 (100) | 0.691 | 1.000 | 0.649 | 0.550 | 0.770 | 0.850 | 0.880 | 0.940 | 0.922 | 0.980 | -0.011 [-0.020, -0.002] |
| 26 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 55% semantic / 45% lexical; depth 100 | covered | 0.6925 (100) | 0.689 | 1.000 | 0.646 | 0.550 | 0.760 | 0.860 | 0.890 | 0.940 | 0.952 | 0.980 | -0.011 [-0.019, -0.004] |
| 27 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 65% semantic / 35% lexical; depth 100 | covered | 0.6924 (100) | 0.694 | 1.000 | 0.626 | 0.520 | 0.770 | 0.840 | 0.890 | 0.940 | 0.928 | 0.953 | -0.011 [-0.023, +0.001] |
| 28 | Lexical field-score ablation | Independent BM25 fields; 10% authors | OpenAI large candidate retrieval | separate title 25% / abstract 75%; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 | covered | 0.6918 (100) | 0.686 | 1.000 | 0.670 | 0.580 | 0.810 | 0.850 | 0.880 | 0.940 | 0.944 | 0.980 | -0.012 [-0.023, -0.002] |
| 29 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 55% semantic / 45% lexical; depth 200 | covered | 0.6918 (100) | 0.691 | 1.000 | 0.639 | 0.540 | 0.750 | 0.840 | 0.880 | 0.940 | 0.949 | 0.980 | -0.012 [-0.021, -0.003] |
| 30 | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | concatenated title + abstract control; pure semantic field score; reorder baseline top10 only, preserve tail | covered | 0.6916 (100) | 0.689 | 1.000 | 0.622 | 0.510 | 0.780 | 0.860 | 0.890 | 0.940 | 0.952 | 0.801 | -0.012 [-0.023, -0.001] |
| 31 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 75% semantic / 25% lexical; depth 100 | covered | 0.6913 (100) | 0.690 | 1.000 | 0.618 | 0.520 | 0.770 | 0.840 | 0.890 | 0.940 | 0.928 | 0.943 | -0.012 [-0.025, -0.000] |
| 32 | Rank + score interpolation | Tuned BM25 | OpenAI text-embedding-3-large | 25% max-score75% + 75% normalized RRF55%/c30/d100; score depth 500 | covered | 0.6912 (100) | 0.690 | 1.000 | 0.646 | 0.550 | 0.760 | 0.850 | 0.880 | 0.940 | 0.950 | 0.980 | -0.012 [-0.020, -0.005] |
| 33 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 70% semantic / 30% lexical; depth 100 | covered | 0.6911 (100) | 0.687 | 1.000 | 0.627 | 0.530 | 0.760 | 0.840 | 0.890 | 0.940 | 0.928 | 0.950 | -0.012 [-0.023, -0.001] |
| 34 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30 + 10% top-1 bonus; 55% semantic / 45% lexical; depth 100 | covered | 0.6910 (100) | 0.689 | 1.000 | 0.653 | 0.560 | 0.790 | 0.850 | 0.890 | 0.940 | 0.952 | 0.980 | -0.013 [-0.020, -0.005] |
| 35 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 60% semantic / 40% lexical; depth 100 | covered | 0.6902 (100) | 0.688 | 1.000 | 0.636 | 0.530 | 0.790 | 0.860 | 0.890 | 0.940 | 0.947 | 0.953 | -0.013 [-0.023, -0.005] |
| 36 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 55% semantic / 45% lexical; depth 100 | covered | 0.6901 (100) | 0.695 | 1.000 | 0.627 | 0.530 | 0.740 | 0.820 | 0.870 | 0.940 | 0.940 | 0.960 | -0.013 [-0.027, +0.000] |
| 37 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 55% semantic / 45% lexical; depth 500 | covered | 0.6897 (100) | 0.690 | 1.000 | 0.640 | 0.540 | 0.760 | 0.840 | 0.880 | 0.940 | 0.954 | 0.980 | -0.014 [-0.023, -0.004] |
| 38 | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | separate title 25% / abstract 75%; pure semantic field score; reorder baseline top10 only, preserve tail | covered | 0.6896 (100) | 0.689 | 1.000 | 0.621 | 0.510 | 0.780 | 0.860 | 0.890 | 0.940 | 0.952 | 0.781 | -0.014 [-0.026, -0.003] |
| 39 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Min-max-normalized scores; 55% semantic / 45% lexical; depth 500 | covered | 0.6891 (100) | 0.674 | 1.000 | 0.684 | 0.590 | 0.790 | 0.840 | 0.880 | 0.940 | 0.947 | 0.980 | -0.014 [-0.024, -0.005] |
| 40 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 65% semantic / 35% lexical; depth 100 | covered | 0.6890 (100) | 0.685 | 1.000 | 0.640 | 0.540 | 0.780 | 0.850 | 0.890 | 0.950 | 0.940 | 0.953 | -0.015 [-0.026, -0.004] |
| 41 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 75% semantic / 25% lexical; depth 100 | covered | 0.6888 (100) | 0.685 | 1.000 | 0.624 | 0.530 | 0.750 | 0.840 | 0.890 | 0.940 | 0.896 | 0.947 | -0.015 [-0.026, -0.003] |
| 42 | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 75% / abstract 25%; max-score25% lexical / 75% field semantic; reorder baseline top10 only, preserve tail | covered | 0.6886 (100) | 0.689 | 1.000 | 0.655 | 0.570 | 0.760 | 0.860 | 0.890 | 0.940 | 0.952 | 0.953 | -0.015 [-0.027, -0.004] |
| 43 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30 + 25% top-1 bonus; 55% semantic / 45% lexical; depth 100 | covered | 0.6885 (100) | 0.687 | 1.000 | 0.653 | 0.560 | 0.790 | 0.850 | 0.890 | 0.940 | 0.952 | 0.980 | -0.015 [-0.024, -0.007] |
| 44 | Local cross-encoder reranking | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large candidate retrieval | MiniLM-L6 cross-encoder raw logits; reorder current baseline top10 only, preserve tail | covered | 0.6879 (100) | 0.689 | 1.000 | 0.659 | 0.570 | 0.790 | 0.860 | 0.890 | 0.940 | 0.952 | 0.933 | -0.016 [-0.028, -0.004] |
| 45 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 75% semantic / 25% lexical; depth 100 | covered | 0.6879 (100) | 0.680 | 1.000 | 0.630 | 0.540 | 0.770 | 0.840 | 0.890 | 0.940 | 0.927 | 0.943 | -0.016 [-0.027, -0.004] |
| 46 | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 25% / abstract 75%; pure cosine; reorder baseline top10 only, preserve tail | covered | 0.6870 (100) | 0.689 | 1.000 | 0.630 | 0.520 | 0.740 | 0.860 | 0.890 | 0.940 | 0.952 | 0.873 | -0.017 [-0.028, -0.004] |
| 47 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Max-normalized scores; 55% semantic / 45% lexical; depth 100 | covered | 0.6858 (100) | 0.686 | 1.000 | 0.656 | 0.570 | 0.760 | 0.790 | 0.860 | 0.940 | 0.923 | 0.980 | -0.018 [-0.034, -0.001] |
| 48 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 70% semantic / 30% lexical; depth 100 | covered | 0.6829 (100) | 0.676 | 1.000 | 0.642 | 0.540 | 0.800 | 0.860 | 0.900 | 0.940 | 0.930 | 0.950 | -0.021 [-0.035, -0.007] |
| 49 | Lexical field-score ablation | Independent BM25 fields; 10% authors | OpenAI large candidate retrieval | separate title 50% / abstract 50%; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 | covered | 0.6826 (100) | 0.683 | 1.000 | 0.647 | 0.530 | 0.810 | 0.850 | 0.870 | 0.930 | 0.944 | 0.980 | -0.021 [-0.032, -0.011] |
| 50 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 75% semantic / 25% lexical; depth 50 | covered | 0.6825 (100) | 0.686 | 1.000 | 0.617 | 0.520 | 0.760 | 0.840 | 0.890 | 0.930 | 0.873 | 0.947 | -0.021 [-0.036, -0.008] |
| 51 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Min-max-normalized scores; 75% semantic / 25% lexical; depth 500 | covered | 0.6823 (100) | 0.668 | 1.000 | 0.684 | 0.600 | 0.810 | 0.860 | 0.900 | 0.940 | 0.930 | 0.960 | -0.021 [-0.039, -0.006] |
| 52 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 50% semantic / 50% lexical; depth 100 | covered | 0.6819 (100) | 0.689 | 1.000 | 0.626 | 0.540 | 0.740 | 0.780 | 0.870 | 0.940 | 0.935 | 0.960 | -0.022 [-0.038, -0.005] |
| 53 | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | separate title 50% / abstract 50%; pure semantic field score; reorder baseline top10 only, preserve tail | covered | 0.6813 (100) | 0.689 | 1.000 | 0.599 | 0.480 | 0.790 | 0.860 | 0.890 | 0.940 | 0.952 | 0.830 | -0.022 [-0.035, -0.010] |
| 54 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 75% semantic / 25% lexical; depth 50 | covered | 0.6807 (100) | 0.676 | 1.000 | 0.626 | 0.530 | 0.760 | 0.850 | 0.890 | 0.930 | 0.873 | 0.947 | -0.023 [-0.036, -0.010] |
| 55 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 75% semantic / 25% lexical; depth 100 | covered | 0.6799 (100) | 0.668 | 1.000 | 0.644 | 0.550 | 0.810 | 0.870 | 0.900 | 0.940 | 0.926 | 0.943 | -0.024 [-0.039, -0.008] |
| 56 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 50% semantic / 50% lexical; depth 100 | covered | 0.6791 (100) | 0.689 | 1.000 | 0.627 | 0.540 | 0.740 | 0.770 | 0.840 | 0.940 | 0.934 | 0.960 | -0.024 [-0.042, -0.007] |
| 57 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 50% semantic / 50% lexical; depth 100 | covered | 0.6782 (100) | 0.673 | 1.000 | 0.646 | 0.560 | 0.740 | 0.840 | 0.890 | 0.940 | 0.941 | 0.980 | -0.025 [-0.038, -0.013] |
| 58 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 50% semantic / 50% lexical; depth 100 | covered | 0.6768 (100) | 0.684 | 1.000 | 0.627 | 0.540 | 0.740 | 0.790 | 0.880 | 0.940 | 0.940 | 0.960 | -0.027 [-0.042, -0.012] |
| 59 | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | concatenated title + abstract control; pure cosine; reorder baseline top10 only, preserve tail | covered | 0.6767 (100) | 0.689 | 1.000 | 0.609 | 0.500 | 0.750 | 0.860 | 0.890 | 0.940 | 0.952 | 0.802 | -0.027 [-0.039, -0.015] |
| 60 | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 50% / abstract 50%; pure cosine; reorder baseline top10 only, preserve tail | covered | 0.6766 (100) | 0.689 | 1.000 | 0.604 | 0.480 | 0.760 | 0.860 | 0.890 | 0.940 | 0.952 | 0.830 | -0.027 [-0.042, -0.014] |
| 61 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Max-normalized scores; 55% semantic / 45% lexical; depth 500 | covered | 0.6739 (100) | 0.670 | 1.000 | 0.657 | 0.570 | 0.760 | 0.810 | 0.840 | 0.880 | 0.872 | 0.980 | -0.030 [-0.048, -0.012] |
| 62 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 60% semantic / 40% lexical; depth 100 | covered | 0.6730 (100) | 0.661 | 1.000 | 0.655 | 0.540 | 0.820 | 0.870 | 0.890 | 0.940 | 0.945 | 0.953 | -0.031 [-0.047, -0.016] |
| 63 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 75% semantic / 25% lexical; depth 50 | covered | 0.6724 (100) | 0.664 | 1.000 | 0.632 | 0.530 | 0.780 | 0.870 | 0.890 | 0.950 | 0.920 | 0.947 | -0.031 [-0.049, -0.014] |
| 64 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Min-max-normalized scores; 55% semantic / 45% lexical; depth 100 | covered | 0.6716 (100) | 0.647 | 1.000 | 0.690 | 0.590 | 0.820 | 0.850 | 0.900 | 0.950 | 0.926 | 0.980 | -0.032 [-0.047, -0.018] |
| 65 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 65% semantic / 35% lexical; depth 100 | covered | 0.6706 (100) | 0.662 | 1.000 | 0.648 | 0.540 | 0.800 | 0.870 | 0.890 | 0.950 | 0.945 | 0.953 | -0.033 [-0.051, -0.017] |
| 66 | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 75% / abstract 25%; pure cosine; reorder baseline top10 only, preserve tail | covered | 0.6673 (100) | 0.689 | 1.000 | 0.572 | 0.440 | 0.740 | 0.860 | 0.890 | 0.940 | 0.952 | 0.798 | -0.036 [-0.051, -0.022] |
| 67 | Lexical field-score ablation | Independent BM25 fields; 10% authors | OpenAI large candidate retrieval | separate title 75% / abstract 25%; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 | covered | 0.6669 (100) | 0.675 | 1.000 | 0.606 | 0.490 | 0.800 | 0.840 | 0.880 | 0.930 | 0.942 | 0.960 | -0.037 [-0.049, -0.024] |
| 68 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 55% semantic / 45% lexical; depth 100 | covered | 0.6669 (100) | 0.652 | 1.000 | 0.658 | 0.550 | 0.820 | 0.860 | 0.900 | 0.940 | 0.948 | 0.980 | -0.037 [-0.051, -0.024] |
| 69 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 70% semantic / 30% lexical; depth 100 | covered | 0.6668 (100) | 0.656 | 1.000 | 0.647 | 0.540 | 0.790 | 0.860 | 0.900 | 0.950 | 0.935 | 0.950 | -0.037 [-0.056, -0.019] |
| 70 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Min-max-normalized scores; 75% semantic / 25% lexical; depth 100 | covered | 0.6655 (100) | 0.651 | 1.000 | 0.671 | 0.590 | 0.810 | 0.860 | 0.900 | 0.950 | 0.913 | 0.950 | -0.038 [-0.058, -0.019] |
| 71 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 50% semantic / 50% lexical; depth 50 | covered | 0.6648 (100) | 0.660 | 1.000 | 0.630 | 0.540 | 0.740 | 0.830 | 0.890 | 0.940 | 0.925 | 0.960 | -0.039 [-0.054, -0.023] |
| 72 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 75% semantic / 25% lexical; depth 20 | covered | 0.6639 (100) | 0.658 | 1.000 | 0.625 | 0.520 | 0.760 | 0.850 | 0.880 | 0.920 | 0.835 | 0.947 | -0.040 [-0.061, -0.021] |
| 73 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 75% semantic / 25% lexical; depth 20 | covered | 0.6639 (100) | 0.658 | 1.000 | 0.625 | 0.520 | 0.760 | 0.850 | 0.880 | 0.920 | 0.835 | 0.947 | -0.040 [-0.061, -0.021] |
| 74 | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | separate title 75% / abstract 25%; pure semantic field score; reorder baseline top10 only, preserve tail | covered | 0.6633 (100) | 0.689 | 1.000 | 0.527 | 0.390 | 0.760 | 0.860 | 0.890 | 0.940 | 0.952 | 0.791 | -0.040 [-0.055, -0.025] |
| 75 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 50% semantic / 50% lexical; depth 50 | covered | 0.6632 (100) | 0.659 | 1.000 | 0.630 | 0.540 | 0.740 | 0.820 | 0.890 | 0.940 | 0.925 | 0.960 | -0.040 [-0.056, -0.025] |
| 76 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 75% semantic / 25% lexical; depth 100 | covered | 0.6625 (100) | 0.651 | 1.000 | 0.654 | 0.560 | 0.770 | 0.860 | 0.900 | 0.950 | 0.920 | 0.940 | -0.041 [-0.062, -0.022] |
| 77 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 75% semantic / 25% lexical; depth 50 | covered | 0.6615 (100) | 0.648 | 1.000 | 0.658 | 0.570 | 0.770 | 0.860 | 0.890 | 0.950 | 0.900 | 0.940 | -0.042 [-0.064, -0.023] |
| 78 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Max-normalized scores; 35% semantic / 65% lexical; depth 100 | covered | 0.6613 (100) | 0.670 | 1.000 | 0.636 | 0.560 | 0.730 | 0.750 | 0.780 | 0.800 | 0.777 | 1.000 | -0.042 [-0.064, -0.022] |
| 79 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 50% semantic / 50% lexical; depth 50 | covered | 0.6597 (100) | 0.652 | 1.000 | 0.633 | 0.540 | 0.750 | 0.830 | 0.900 | 0.940 | 0.919 | 0.960 | -0.044 [-0.060, -0.029] |
| 80 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 75% semantic / 25% lexical; depth 20 | covered | 0.6592 (100) | 0.645 | 1.000 | 0.658 | 0.570 | 0.760 | 0.850 | 0.880 | 0.920 | 0.835 | 0.947 | -0.044 [-0.067, -0.025] |
| 81 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 75% semantic / 25% lexical; depth 20 | covered | 0.6525 (100) | 0.636 | 1.000 | 0.642 | 0.550 | 0.760 | 0.820 | 0.890 | 0.920 | 0.835 | 0.933 | -0.051 [-0.076, -0.028] |
| 82 | Original hybrid control | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 50% semantic / 50% lexical; depth 100 | covered | 0.6476 (100) | 0.633 | 1.000 | 0.653 | 0.560 | 0.800 | 0.840 | 0.900 | 0.940 | 0.945 | 0.980 | -0.056 [-0.073, -0.040] |
| 83 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 50% semantic / 50% lexical; depth 100 | covered | 0.6476 (100) | 0.633 | 1.000 | 0.653 | 0.560 | 0.800 | 0.840 | 0.900 | 0.940 | 0.945 | 0.980 | -0.056 [-0.073, -0.040] |
| 84 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 50% semantic / 50% lexical; depth 100 | covered | 0.6476 (100) | 0.633 | 1.000 | 0.653 | 0.560 | 0.800 | 0.840 | 0.900 | 0.940 | 0.945 | 0.980 | -0.056 [-0.073, -0.040] |
| 85 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 25% semantic / 75% lexical; depth 100 | covered | 0.6467 (100) | 0.646 | 1.000 | 0.630 | 0.560 | 0.720 | 0.750 | 0.790 | 0.790 | 0.759 | 0.980 | -0.057 [-0.080, -0.033] |
| 86 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 50% semantic / 50% lexical; depth 50 | covered | 0.6438 (100) | 0.631 | 1.000 | 0.645 | 0.550 | 0.780 | 0.840 | 0.900 | 0.940 | 0.925 | 0.980 | -0.060 [-0.076, -0.044] |
| 87 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 25% semantic / 75% lexical; depth 50 | covered | 0.6345 (100) | 0.623 | 1.000 | 0.630 | 0.560 | 0.710 | 0.750 | 0.770 | 0.770 | 0.691 | 0.980 | -0.069 [-0.094, -0.044] |
| 88 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Min-max-normalized scores; 35% semantic / 65% lexical; depth 500 | covered | 0.6322 (100) | 0.626 | 1.000 | 0.631 | 0.540 | 0.750 | 0.790 | 0.830 | 0.870 | 0.865 | 1.000 | -0.071 [-0.096, -0.047] |
| 89 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 50% semantic / 50% lexical; depth 20 | covered | 0.6311 (100) | 0.615 | 1.000 | 0.639 | 0.540 | 0.800 | 0.840 | 0.890 | 0.920 | 0.835 | 0.980 | -0.072 [-0.093, -0.053] |
| 90 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 50% semantic / 50% lexical; depth 20 | covered | 0.6309 (100) | 0.619 | 1.000 | 0.627 | 0.530 | 0.780 | 0.840 | 0.890 | 0.920 | 0.835 | 0.960 | -0.073 [-0.092, -0.053] |
| 91 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 50% semantic / 50% lexical; depth 20 | covered | 0.6309 (100) | 0.619 | 1.000 | 0.628 | 0.530 | 0.780 | 0.840 | 0.890 | 0.920 | 0.835 | 0.960 | -0.073 [-0.092, -0.053] |
| 92 | Embedding search | None | OpenAI text-embedding-3-large | Cosine similarity | covered | 0.6306 (100) | 0.637 | 1.000 | 0.599 | 0.500 | 0.740 | 0.820 | 0.880 | 0.930 | 0.873 | 0.793 | -0.073 [-0.100, -0.048] |
| 93 | Semantic-only fusion control | None (0% weight) | OpenAI text-embedding-3-large | RRF c=10; depth 100 | covered | 0.6306 (100) | 0.637 | 1.000 | 0.599 | 0.500 | 0.740 | 0.820 | 0.880 | 0.930 | 0.873 | 0.793 | -0.073 [-0.100, -0.048] |
| 94 | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | concatenated title + abstract control; pure cosine; reorder baseline top100 only, preserve tail | covered | 0.6306 (100) | 0.637 | 1.000 | 0.599 | 0.500 | 0.740 | 0.820 | 0.880 | 0.930 | 0.873 | 0.793 | -0.073 [-0.100, -0.048] |
| 95 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Max-normalized scores; 35% semantic / 65% lexical; depth 500 | covered | 0.6251 (100) | 0.635 | 1.000 | 0.619 | 0.540 | 0.720 | 0.770 | 0.800 | 0.850 | 0.837 | 1.000 | -0.078 [-0.108, -0.051] |
| 96 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 25% semantic / 75% lexical; depth 100 | covered | 0.6248 (100) | 0.614 | 1.000 | 0.636 | 0.570 | 0.720 | 0.740 | 0.770 | 0.790 | 0.730 | 0.980 | -0.079 [-0.105, -0.052] |
| 97 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 25% semantic / 75% lexical; depth 100 | covered | 0.6211 (100) | 0.618 | 1.000 | 0.626 | 0.560 | 0.720 | 0.740 | 0.780 | 0.790 | 0.757 | 0.980 | -0.083 [-0.109, -0.055] |
| 98 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 50% semantic / 50% lexical; depth 20 | covered | 0.6197 (100) | 0.605 | 1.000 | 0.635 | 0.530 | 0.800 | 0.840 | 0.890 | 0.920 | 0.835 | 0.960 | -0.084 [-0.105, -0.064] |
| 99 | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=10; 50% semantic / 50% lexical; depth 100 | covered | 0.6188 (100) | 0.611 | 1.000 | 0.635 | 0.540 | 0.760 | 0.800 | 0.840 | 0.880 | 0.819 | 0.973 | -0.085 [-0.115, -0.055] |
| 100 | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=10; 50% semantic / 50% lexical; depth 100 | covered | 0.6158 (100) | 0.614 | 1.000 | 0.602 | 0.500 | 0.770 | 0.790 | 0.850 | 0.900 | 0.805 | 0.930 | -0.088 [-0.120, -0.060] |
| 101 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 25% semantic / 75% lexical; depth 50 | covered | 0.6142 (100) | 0.604 | 1.000 | 0.626 | 0.560 | 0.710 | 0.740 | 0.770 | 0.770 | 0.691 | 0.980 | -0.089 [-0.116, -0.062] |
| 102 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Min-max-normalized scores; 35% semantic / 65% lexical; depth 100 | covered | 0.5984 (100) | 0.577 | 1.000 | 0.626 | 0.540 | 0.720 | 0.790 | 0.860 | 0.910 | 0.881 | 1.000 | -0.105 [-0.133, -0.081] |
| 103 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 25% semantic / 75% lexical; depth 50 | covered | 0.5780 (100) | 0.557 | 1.000 | 0.618 | 0.560 | 0.690 | 0.720 | 0.750 | 0.900 | 0.883 | 0.980 | -0.126 [-0.158, -0.092] |
| 104 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 25% semantic / 75% lexical; depth 20 | covered | 0.5715 (100) | 0.547 | 1.000 | 0.614 | 0.560 | 0.690 | 0.700 | 0.710 | 0.920 | 0.835 | 0.980 | -0.132 [-0.165, -0.097] |
| 105 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 25% semantic / 75% lexical; depth 20 | covered | 0.5715 (100) | 0.547 | 1.000 | 0.614 | 0.560 | 0.690 | 0.700 | 0.710 | 0.920 | 0.835 | 0.980 | -0.132 [-0.165, -0.097] |
| 106 | Embedding search | None | GTE-small | Cosine similarity | covered | 0.5688 (100) | 0.581 | 1.000 | 0.525 | 0.430 | 0.660 | 0.710 | 0.780 | 0.870 | 0.706 | 0.633 | -0.135 [-0.173, -0.100] |
| 107 | Embedding search | None | BGE-small | Cosine similarity | covered | 0.5647 (100) | 0.584 | 1.000 | 0.506 | 0.420 | 0.600 | 0.700 | 0.790 | 0.890 | 0.713 | 0.667 | -0.139 [-0.177, -0.105] |
| 108 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 25% semantic / 75% lexical; depth 100 | covered | 0.5586 (100) | 0.557 | 1.000 | 0.602 | 0.540 | 0.680 | 0.730 | 0.780 | 0.880 | 0.851 | 0.980 | -0.145 [-0.179, -0.109] |
| 109 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 25% semantic / 75% lexical; depth 50 | covered | 0.5575 (100) | 0.555 | 1.000 | 0.603 | 0.540 | 0.680 | 0.730 | 0.760 | 0.900 | 0.834 | 0.980 | -0.146 [-0.180, -0.111] |
| 110 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 25% semantic / 75% lexical; depth 20 | covered | 0.5476 (100) | 0.538 | 1.000 | 0.605 | 0.550 | 0.680 | 0.710 | 0.710 | 0.920 | 0.835 | 0.980 | -0.156 [-0.192, -0.119] |
| 111 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 25% semantic / 75% lexical; depth 20 | covered | 0.5401 (100) | 0.526 | 1.000 | 0.614 | 0.560 | 0.680 | 0.710 | 0.870 | 0.920 | 0.835 | 0.980 | -0.163 [-0.199, -0.126] |
| 112 | Keyword search | BM25: exact + stems; authors; title x2; k1=0.8,b=0.75 | None | BM25 score | covered | 0.5090 (100) | 0.512 | 1.000 | 0.569 | 0.510 | 0.660 | 0.710 | 0.710 | 0.770 | 0.691 | 1.000 | -0.195 [-0.233, -0.156] |
| 113 | Lexical-only fusion control | Tuned BM25 | None (0% weight) | RRF c=10; depth 100 | covered | 0.5090 (100) | 0.512 | 1.000 | 0.569 | 0.510 | 0.660 | 0.710 | 0.710 | 0.770 | 0.691 | 1.000 | -0.195 [-0.233, -0.156] |

### Unranked diagnostics (incomplete judgments or undefined nDCG)

Sorted by diagnostic nDCG only; these runs are not eligible to win.

| Rank | System | Keyword retrieval | Embedding | Ranker / fusion | Status | Success: nDCG@10 (n) | P@10 | judged@10 | Source MRR@10 | R@1 | R@5 | R@10 | R@20 | R@50 | Grade-2 recall@50 | Known-item MRR@10 | Δ nDCG vs retrieval baseline [95% CI] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| - | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 25% / abstract 75%; max-score25% lexical / 75% field semantic; reorder baseline top100 only, preserve tail | PROVISIONAL | 0.7050 (100) | 0.689 | 0.965 | 0.701 | 0.640 | 0.780 | 0.830 | 0.840 | 0.910 | 0.919 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Rank + score interpolation | Tuned BM25 | OpenAI text-embedding-3-large | 75% max-score75% + 25% normalized RRF55%/c30/d100; score depth 500 | PROVISIONAL | 0.7029 (100) | 0.696 | 0.999 | 0.678 | 0.590 | 0.800 | 0.840 | 0.860 | 0.910 | 0.935 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 70% semantic / 30% lexical; depth 100 | PROVISIONAL | 0.6938 (100) | 0.696 | 0.998 | 0.618 | 0.520 | 0.740 | 0.840 | 0.870 | 0.940 | 0.924 | 0.947 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 60% semantic / 40% lexical; depth 100 | PROVISIONAL | 0.6917 (100) | 0.693 | 0.999 | 0.627 | 0.530 | 0.750 | 0.810 | 0.870 | 0.940 | 0.922 | 0.953 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 65% semantic / 35% lexical; depth 100 | PROVISIONAL | 0.6906 (100) | 0.694 | 0.998 | 0.621 | 0.520 | 0.750 | 0.820 | 0.870 | 0.940 | 0.922 | 0.953 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 55% semantic / 45% lexical; depth 100 | PROVISIONAL | 0.6888 (100) | 0.694 | 0.999 | 0.620 | 0.520 | 0.740 | 0.800 | 0.860 | 0.950 | 0.939 | 0.960 | withheld: both runs must have all dev top-10 positions present and judged |
| - | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 50% / abstract 50%; max-score25% lexical / 75% field semantic; reorder baseline top100 only, preserve tail | PROVISIONAL | 0.6808 (100) | 0.668 | 0.943 | 0.677 | 0.600 | 0.770 | 0.820 | 0.840 | 0.910 | 0.906 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Local cross-encoder reranking | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large candidate retrieval | 50% cross-encoder rank + 50% baseline rank, RRF c30; union of lexical100, semantic100 and baseline100 | PROVISIONAL | 0.6674 (100) | 0.651 | 0.945 | 0.687 | 0.610 | 0.780 | 0.840 | 0.850 | 0.930 | 0.936 | 0.960 | withheld: both runs must have all dev top-10 positions present and judged |
| - | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 75% / abstract 25%; max-score25% lexical / 75% field semantic; reorder baseline top100 only, preserve tail | PROVISIONAL | 0.6438 (100) | 0.622 | 0.895 | 0.656 | 0.580 | 0.760 | 0.810 | 0.820 | 0.910 | 0.885 | 0.953 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=60; 75% semantic / 25% lexical; depth 100 | PROVISIONAL | 0.6333 (100) | 0.630 | 0.952 | 0.586 | 0.490 | 0.720 | 0.770 | 0.840 | 0.900 | 0.777 | 0.806 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Local cross-encoder reranking | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large candidate retrieval | MiniLM-L6 cross-encoder raw logits; reorder current baseline top30 only, preserve tail | PROVISIONAL | 0.6307 (100) | 0.628 | 0.926 | 0.620 | 0.540 | 0.710 | 0.790 | 0.850 | 0.940 | 0.952 | 0.907 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=100; 75% semantic / 25% lexical; depth 100 | PROVISIONAL | 0.6294 (100) | 0.623 | 0.914 | 0.578 | 0.480 | 0.690 | 0.770 | 0.830 | 0.900 | 0.778 | 0.805 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | GTE-small | Linear rank fusion; 75% semantic / 25% lexical; depth 100 | PROVISIONAL | 0.6268 (100) | 0.625 | 0.951 | 0.570 | 0.460 | 0.710 | 0.760 | 0.830 | 0.890 | 0.737 | 0.801 | withheld: both runs must have all dev top-10 positions present and judged |
| - | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 25% / abstract 75%; pure cosine; reorder baseline top100 only, preserve tail | PROVISIONAL | 0.6231 (100) | 0.590 | 0.872 | 0.618 | 0.520 | 0.740 | 0.810 | 0.890 | 0.920 | 0.870 | 0.866 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=60; 50% semantic / 50% lexical; depth 100 | PROVISIONAL | 0.6216 (100) | 0.601 | 0.879 | 0.603 | 0.510 | 0.710 | 0.770 | 0.810 | 0.880 | 0.816 | 0.920 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=60; 50% semantic / 50% lexical; depth 100 | PROVISIONAL | 0.6207 (100) | 0.606 | 0.883 | 0.581 | 0.490 | 0.710 | 0.780 | 0.820 | 0.890 | 0.814 | 0.892 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | GTE-small | Linear rank fusion; 50% semantic / 50% lexical; depth 100 | PROVISIONAL | 0.6203 (100) | 0.607 | 0.889 | 0.603 | 0.510 | 0.720 | 0.760 | 0.810 | 0.880 | 0.818 | 0.920 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | BGE-small | Linear rank fusion; 75% semantic / 25% lexical; depth 100 | PROVISIONAL | 0.6192 (100) | 0.618 | 0.945 | 0.559 | 0.470 | 0.690 | 0.740 | 0.830 | 0.910 | 0.727 | 0.856 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=100; 50% semantic / 50% lexical; depth 100 | PROVISIONAL | 0.6185 (100) | 0.596 | 0.860 | 0.601 | 0.510 | 0.720 | 0.770 | 0.810 | 0.880 | 0.816 | 0.920 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | BGE-small | Linear rank fusion; 50% semantic / 50% lexical; depth 100 | PROVISIONAL | 0.6180 (100) | 0.608 | 0.896 | 0.569 | 0.470 | 0.690 | 0.790 | 0.830 | 0.900 | 0.806 | 0.891 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=100; 50% semantic / 50% lexical; depth 100 | PROVISIONAL | 0.6179 (100) | 0.602 | 0.866 | 0.578 | 0.490 | 0.720 | 0.770 | 0.820 | 0.890 | 0.814 | 0.891 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=100; 75% semantic / 25% lexical; depth 100 | PROVISIONAL | 0.6170 (100) | 0.612 | 0.902 | 0.563 | 0.480 | 0.690 | 0.760 | 0.850 | 0.930 | 0.759 | 0.856 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=60; 75% semantic / 25% lexical; depth 100 | PROVISIONAL | 0.6170 (100) | 0.619 | 0.947 | 0.561 | 0.480 | 0.700 | 0.750 | 0.840 | 0.930 | 0.754 | 0.856 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=100; 25% semantic / 75% lexical; depth 100 | PROVISIONAL | 0.6054 (100) | 0.596 | 0.923 | 0.590 | 0.500 | 0.710 | 0.740 | 0.770 | 0.790 | 0.739 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=10; 75% semantic / 25% lexical; depth 100 | PROVISIONAL | 0.6037 (100) | 0.607 | 0.997 | 0.576 | 0.480 | 0.710 | 0.760 | 0.850 | 0.910 | 0.767 | 0.766 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=100; 25% semantic / 75% lexical; depth 100 | PROVISIONAL | 0.6036 (100) | 0.592 | 0.921 | 0.591 | 0.490 | 0.710 | 0.750 | 0.770 | 0.790 | 0.743 | 0.960 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=10; 75% semantic / 25% lexical; depth 100 | PROVISIONAL | 0.6000 (100) | 0.616 | 0.997 | 0.552 | 0.470 | 0.650 | 0.760 | 0.840 | 0.940 | 0.756 | 0.797 | withheld: both runs must have all dev top-10 positions present and judged |
| - | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 50% / abstract 50%; pure cosine; reorder baseline top100 only, preserve tail | PROVISIONAL | 0.5965 (100) | 0.567 | 0.819 | 0.599 | 0.480 | 0.780 | 0.810 | 0.840 | 0.910 | 0.855 | 0.821 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=60; 25% semantic / 75% lexical; depth 100 | PROVISIONAL | 0.5959 (100) | 0.589 | 0.960 | 0.588 | 0.500 | 0.720 | 0.730 | 0.760 | 0.790 | 0.738 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | GTE-small | Linear rank fusion; 25% semantic / 75% lexical; depth 100 | PROVISIONAL | 0.5956 (100) | 0.588 | 0.960 | 0.588 | 0.490 | 0.720 | 0.740 | 0.760 | 0.790 | 0.715 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | BGE-small | Linear rank fusion; 25% semantic / 75% lexical; depth 100 | PROVISIONAL | 0.5950 (100) | 0.584 | 0.957 | 0.587 | 0.490 | 0.710 | 0.740 | 0.750 | 0.790 | 0.718 | 0.948 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=60; 25% semantic / 75% lexical; depth 100 | PROVISIONAL | 0.5930 (100) | 0.587 | 0.959 | 0.585 | 0.480 | 0.720 | 0.740 | 0.760 | 0.790 | 0.737 | 0.960 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Local cross-encoder reranking | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large candidate retrieval | MiniLM-L6 cross-encoder raw logits; reorder current baseline top100 only, preserve tail | PROVISIONAL | 0.5629 (100) | 0.527 | 0.756 | 0.605 | 0.540 | 0.690 | 0.740 | 0.820 | 0.890 | 0.863 | 0.905 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=10; 25% semantic / 75% lexical; depth 100 | PROVISIONAL | 0.5485 (100) | 0.547 | 0.999 | 0.579 | 0.500 | 0.670 | 0.720 | 0.770 | 0.840 | 0.796 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=10; 25% semantic / 75% lexical; depth 100 | PROVISIONAL | 0.5463 (100) | 0.545 | 0.996 | 0.581 | 0.490 | 0.680 | 0.730 | 0.760 | 0.870 | 0.806 | 0.960 | withheld: both runs must have all dev top-10 positions present and judged |
| - | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 75% / abstract 25%; pure cosine; reorder baseline top100 only, preserve tail | PROVISIONAL | 0.5431 (100) | 0.516 | 0.749 | 0.541 | 0.440 | 0.690 | 0.790 | 0.800 | 0.880 | 0.825 | 0.765 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Local cross-encoder reranking | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large candidate retrieval | MiniLM-L6 cross-encoder raw logits; union of lexical100, semantic100 and baseline100 | PROVISIONAL | 0.5430 (100) | 0.501 | 0.707 | 0.604 | 0.540 | 0.690 | 0.740 | 0.790 | 0.890 | 0.789 | 0.905 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact + stems; remove stopwords; authors; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.5126 (100) | 0.516 | 0.938 | 0.559 | 0.500 | 0.650 | 0.700 | 0.730 | 0.760 | 0.694 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact + stems; remove stopwords; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.5103 (100) | 0.517 | 0.915 | 0.544 | 0.470 | 0.660 | 0.710 | 0.730 | 0.760 | 0.684 | 0.940 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact + stems; authors; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.5098 (100) | 0.511 | 0.940 | 0.557 | 0.510 | 0.650 | 0.700 | 0.730 | 0.770 | 0.702 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact + stems; remove stopwords; authors; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.5096 (100) | 0.515 | 0.921 | 0.547 | 0.490 | 0.650 | 0.700 | 0.730 | 0.760 | 0.697 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact + stems; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.5092 (100) | 0.519 | 0.936 | 0.545 | 0.470 | 0.670 | 0.710 | 0.720 | 0.760 | 0.691 | 0.940 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact + stems; authors; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.5071 (100) | 0.510 | 0.959 | 0.560 | 0.500 | 0.670 | 0.710 | 0.730 | 0.760 | 0.692 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact + stems; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.5038 (100) | 0.509 | 0.915 | 0.521 | 0.440 | 0.650 | 0.700 | 0.730 | 0.770 | 0.696 | 0.873 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact + stems; remove stopwords; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.5030 (100) | 0.510 | 0.897 | 0.516 | 0.430 | 0.650 | 0.710 | 0.730 | 0.760 | 0.690 | 0.873 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact terms; remove stopwords; authors; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4889 (100) | 0.480 | 0.855 | 0.530 | 0.470 | 0.610 | 0.680 | 0.700 | 0.740 | 0.640 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact terms; authors; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4880 (100) | 0.483 | 0.859 | 0.523 | 0.470 | 0.600 | 0.670 | 0.710 | 0.740 | 0.643 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact terms; remove stopwords; authors; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4869 (100) | 0.482 | 0.838 | 0.525 | 0.470 | 0.610 | 0.680 | 0.700 | 0.740 | 0.654 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact terms; remove stopwords; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4868 (100) | 0.483 | 0.835 | 0.519 | 0.450 | 0.610 | 0.690 | 0.700 | 0.740 | 0.641 | 0.940 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact terms; authors; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4849 (100) | 0.478 | 0.872 | 0.534 | 0.480 | 0.620 | 0.670 | 0.700 | 0.750 | 0.633 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: stems only; remove stopwords; authors; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4830 (100) | 0.461 | 0.786 | 0.549 | 0.490 | 0.620 | 0.710 | 0.720 | 0.750 | 0.661 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact terms; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4819 (100) | 0.480 | 0.850 | 0.517 | 0.450 | 0.610 | 0.670 | 0.700 | 0.750 | 0.632 | 0.940 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: stems only; remove stopwords; authors; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4798 (100) | 0.454 | 0.768 | 0.550 | 0.490 | 0.610 | 0.690 | 0.730 | 0.750 | 0.658 | 0.960 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact terms; remove stopwords; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4797 (100) | 0.477 | 0.817 | 0.501 | 0.430 | 0.600 | 0.680 | 0.700 | 0.740 | 0.649 | 0.907 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: stems only; authors; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4794 (100) | 0.457 | 0.799 | 0.549 | 0.490 | 0.630 | 0.700 | 0.730 | 0.750 | 0.659 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact terms; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4791 (100) | 0.474 | 0.829 | 0.501 | 0.430 | 0.610 | 0.670 | 0.700 | 0.740 | 0.644 | 0.907 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: stems only; remove stopwords; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4781 (100) | 0.458 | 0.763 | 0.515 | 0.430 | 0.620 | 0.720 | 0.730 | 0.750 | 0.655 | 0.830 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: stems only; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4727 (100) | 0.452 | 0.771 | 0.512 | 0.430 | 0.630 | 0.720 | 0.730 | 0.750 | 0.652 | 0.830 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: stems only; authors; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4721 (100) | 0.443 | 0.770 | 0.544 | 0.480 | 0.630 | 0.690 | 0.730 | 0.750 | 0.663 | 0.960 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: stems only; remove stopwords; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4683 (100) | 0.447 | 0.750 | 0.492 | 0.400 | 0.590 | 0.700 | 0.730 | 0.750 | 0.652 | 0.746 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: stems only; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4645 (100) | 0.439 | 0.757 | 0.492 | 0.400 | 0.610 | 0.700 | 0.730 | 0.750 | 0.646 | 0.748 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Embedding search | None | MiniLM-L6-v2 | Cosine similarity | PROVISIONAL | 0.4381 (100) | 0.390 | 0.557 | 0.407 | 0.330 | 0.530 | 0.590 | 0.680 | 0.810 | 0.640 | 0.549 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Embedding search | None | E5-small | Cosine similarity | PROVISIONAL | 0.4217 (100) | 0.366 | 0.524 | 0.485 | 0.390 | 0.610 | 0.690 | 0.750 | 0.800 | 0.655 | 0.626 | withheld: both runs must have all dev top-10 positions present and judged |

## Every run by query type

| System | Type | Queries | nDCG@10 (n) | P@10 | judged@10 | Source MRR@10 | R@1 | R@5 | R@10 | R@20 | R@50 | Grade-2 recall@50 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `baseline-original-equal-rrf-c10-d100` | keyword | 25 | 0.680 (25) | 0.692 | 1.000 | 0.717 | 0.600 | 0.920 | 0.960 | 1.000 | 1.000 | 0.934 |
| `baseline-original-equal-rrf-c10-d100` | question | 25 | 0.644 (25) | 0.660 | 1.000 | 0.553 | 0.440 | 0.760 | 0.760 | 0.800 | 0.920 | 0.901 |
| `baseline-original-equal-rrf-c10-d100` | paraphrase | 25 | 0.580 (25) | 0.576 | 1.000 | 0.364 | 0.240 | 0.520 | 0.640 | 0.800 | 0.840 | 0.959 |
| `baseline-original-equal-rrf-c10-d100` | known_item | 25 | 0.687 (25) | 0.604 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.987 |
| `bm25+authors` | keyword | 25 | 0.573 (25) | 0.572 | 0.912 | 0.589 | 0.480 | 0.760 | 0.920 | 0.920 | 0.960 | 0.790 |
| `bm25+authors` | question | 25 | 0.394 (25) | 0.416 | 0.824 | 0.408 | 0.320 | 0.520 | 0.560 | 0.680 | 0.680 | 0.553 |
| `bm25+authors` | paraphrase | 25 | 0.332 (25) | 0.376 | 0.816 | 0.096 | 0.080 | 0.120 | 0.200 | 0.240 | 0.320 | 0.408 |
| `bm25+authors` | known_item | 25 | 0.652 (25) | 0.568 | 0.884 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.812 |
| `bm25+authors+title2x` | keyword | 25 | 0.565 (25) | 0.556 | 0.904 | 0.611 | 0.480 | 0.880 | 0.920 | 0.920 | 1.000 | 0.798 |
| `bm25+authors+title2x` | question | 25 | 0.390 (25) | 0.416 | 0.848 | 0.427 | 0.360 | 0.480 | 0.560 | 0.680 | 0.680 | 0.507 |
| `bm25+authors+title2x` | paraphrase | 25 | 0.325 (25) | 0.368 | 0.832 | 0.096 | 0.080 | 0.120 | 0.200 | 0.200 | 0.320 | 0.408 |
| `bm25+authors+title2x` | known_item | 25 | 0.660 (25) | 0.572 | 0.904 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.809 |
| `bm25+exact+stems` | keyword | 25 | 0.585 (25) | 0.584 | 0.952 | 0.650 | 0.560 | 0.840 | 0.920 | 0.920 | 0.960 | 0.810 |
| `bm25+exact+stems` | question | 25 | 0.448 (25) | 0.488 | 0.948 | 0.434 | 0.360 | 0.520 | 0.600 | 0.720 | 0.720 | 0.564 |
| `bm25+exact+stems` | paraphrase | 25 | 0.347 (25) | 0.392 | 0.920 | 0.125 | 0.080 | 0.240 | 0.280 | 0.280 | 0.400 | 0.515 |
| `bm25+exact+stems` | known_item | 25 | 0.636 (25) | 0.572 | 0.840 | 0.873 | 0.760 | 1.000 | 1.000 | 1.000 | 1.000 | 0.889 |
| `bm25+exact+stems+authors` | keyword | 25 | 0.588 (25) | 0.592 | 0.952 | 0.648 | 0.560 | 0.840 | 0.920 | 0.920 | 0.960 | 0.810 |
| `bm25+exact+stems+authors` | question | 25 | 0.442 (25) | 0.468 | 0.940 | 0.454 | 0.400 | 0.520 | 0.600 | 0.720 | 0.720 | 0.564 |
| `bm25+exact+stems+authors` | paraphrase | 25 | 0.348 (25) | 0.400 | 0.936 | 0.127 | 0.080 | 0.240 | 0.280 | 0.280 | 0.400 | 0.515 |
| `bm25+exact+stems+authors` | known_item | 25 | 0.661 (25) | 0.584 | 0.932 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.913 |
| `bm25+exact+stems+authors+title2x` | keyword | 25 | 0.580 (25) | 0.588 | 0.964 | 0.657 | 0.520 | 0.920 | 0.920 | 0.920 | 0.960 | 0.810 |
| `bm25+exact+stems+authors+title2x` | question | 25 | 0.429 (25) | 0.456 | 0.964 | 0.459 | 0.400 | 0.560 | 0.640 | 0.720 | 0.720 | 0.565 |
| `bm25+exact+stems+authors+title2x` | paraphrase | 25 | 0.352 (25) | 0.404 | 0.952 | 0.124 | 0.080 | 0.200 | 0.280 | 0.280 | 0.360 | 0.494 |
| `bm25+exact+stems+authors+title2x` | known_item | 25 | 0.667 (25) | 0.592 | 0.956 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.893 |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | keyword | 25 | 0.595 (25) | 0.596 | 1.000 | 0.710 | 0.600 | 0.880 | 0.920 | 0.920 | 0.960 | 0.786 |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | question | 25 | 0.423 (25) | 0.452 | 1.000 | 0.432 | 0.360 | 0.520 | 0.640 | 0.640 | 0.720 | 0.569 |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | paraphrase | 25 | 0.357 (25) | 0.412 | 1.000 | 0.132 | 0.080 | 0.240 | 0.280 | 0.280 | 0.400 | 0.490 |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | known_item | 25 | 0.661 (25) | 0.588 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.913 |
| `bm25+exact+stems+title2x` | keyword | 25 | 0.582 (25) | 0.592 | 0.964 | 0.657 | 0.520 | 0.920 | 0.920 | 0.920 | 0.960 | 0.810 |
| `bm25+exact+stems+title2x` | question | 25 | 0.444 (25) | 0.480 | 0.960 | 0.459 | 0.400 | 0.560 | 0.640 | 0.680 | 0.720 | 0.564 |
| `bm25+exact+stems+title2x` | paraphrase | 25 | 0.353 (25) | 0.400 | 0.940 | 0.125 | 0.080 | 0.200 | 0.280 | 0.280 | 0.360 | 0.494 |
| `bm25+exact+stems+title2x` | known_item | 25 | 0.658 (25) | 0.604 | 0.880 | 0.940 | 0.880 | 1.000 | 1.000 | 1.000 | 1.000 | 0.889 |
| `bm25+stem` | keyword | 25 | 0.562 (25) | 0.532 | 0.856 | 0.665 | 0.600 | 0.760 | 0.840 | 0.920 | 0.960 | 0.746 |
| `bm25+stem` | question | 25 | 0.392 (25) | 0.384 | 0.732 | 0.388 | 0.280 | 0.520 | 0.680 | 0.680 | 0.680 | 0.492 |
| `bm25+stem` | paraphrase | 25 | 0.301 (25) | 0.312 | 0.672 | 0.166 | 0.120 | 0.240 | 0.320 | 0.320 | 0.360 | 0.473 |
| `bm25+stem` | known_item | 25 | 0.603 (25) | 0.528 | 0.768 | 0.748 | 0.600 | 0.920 | 0.960 | 1.000 | 1.000 | 0.866 |
| `bm25+stem+authors` | keyword | 25 | 0.566 (25) | 0.544 | 0.852 | 0.676 | 0.600 | 0.760 | 0.880 | 0.920 | 0.960 | 0.758 |
| `bm25+stem+authors` | question | 25 | 0.381 (25) | 0.372 | 0.712 | 0.377 | 0.280 | 0.520 | 0.600 | 0.680 | 0.680 | 0.498 |
| `bm25+stem+authors` | paraphrase | 25 | 0.294 (25) | 0.308 | 0.672 | 0.161 | 0.120 | 0.240 | 0.280 | 0.320 | 0.360 | 0.494 |
| `bm25+stem+authors` | known_item | 25 | 0.647 (25) | 0.548 | 0.844 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.893 |
| `bm25+stem+authors+title2x` | keyword | 25 | 0.571 (25) | 0.552 | 0.868 | 0.653 | 0.560 | 0.800 | 0.880 | 0.920 | 0.960 | 0.772 |
| `bm25+stem+authors+title2x` | question | 25 | 0.389 (25) | 0.388 | 0.752 | 0.384 | 0.280 | 0.560 | 0.640 | 0.680 | 0.680 | 0.494 |
| `bm25+stem+authors+title2x` | paraphrase | 25 | 0.305 (25) | 0.328 | 0.704 | 0.178 | 0.160 | 0.160 | 0.280 | 0.320 | 0.360 | 0.473 |
| `bm25+stem+authors+title2x` | known_item | 25 | 0.653 (25) | 0.560 | 0.872 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.890 |
| `bm25+stem+title2x` | keyword | 25 | 0.573 (25) | 0.556 | 0.876 | 0.650 | 0.560 | 0.800 | 0.920 | 0.920 | 0.960 | 0.769 |
| `bm25+stem+title2x` | question | 25 | 0.389 (25) | 0.384 | 0.736 | 0.385 | 0.280 | 0.560 | 0.640 | 0.680 | 0.680 | 0.487 |
| `bm25+stem+title2x` | paraphrase | 25 | 0.300 (25) | 0.316 | 0.684 | 0.182 | 0.160 | 0.160 | 0.320 | 0.320 | 0.360 | 0.473 |
| `bm25+stem+title2x` | known_item | 25 | 0.628 (25) | 0.552 | 0.788 | 0.830 | 0.720 | 1.000 | 1.000 | 1.000 | 1.000 | 0.873 |
| `bm25+stop` | keyword | 25 | 0.563 (25) | 0.560 | 0.900 | 0.592 | 0.480 | 0.800 | 0.920 | 0.920 | 0.960 | 0.790 |
| `bm25+stop` | question | 25 | 0.394 (25) | 0.420 | 0.788 | 0.410 | 0.320 | 0.480 | 0.600 | 0.680 | 0.680 | 0.554 |
| `bm25+stop` | paraphrase | 25 | 0.328 (25) | 0.376 | 0.784 | 0.097 | 0.080 | 0.120 | 0.200 | 0.200 | 0.320 | 0.427 |
| `bm25+stop` | known_item | 25 | 0.634 (25) | 0.552 | 0.796 | 0.907 | 0.840 | 1.000 | 1.000 | 1.000 | 1.000 | 0.815 |
| `bm25+stop+authors` | keyword | 25 | 0.573 (25) | 0.572 | 0.904 | 0.595 | 0.480 | 0.800 | 0.920 | 0.920 | 0.960 | 0.790 |
| `bm25+stop+authors` | question | 25 | 0.395 (25) | 0.420 | 0.800 | 0.415 | 0.320 | 0.520 | 0.640 | 0.680 | 0.680 | 0.554 |
| `bm25+stop+authors` | paraphrase | 25 | 0.329 (25) | 0.376 | 0.776 | 0.092 | 0.080 | 0.120 | 0.160 | 0.200 | 0.320 | 0.431 |
| `bm25+stop+authors` | known_item | 25 | 0.650 (25) | 0.560 | 0.872 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.832 |
| `bm25+stop+authors+title2x` | keyword | 25 | 0.568 (25) | 0.564 | 0.904 | 0.613 | 0.480 | 0.840 | 0.920 | 0.920 | 1.000 | 0.798 |
| `bm25+stop+authors+title2x` | question | 25 | 0.399 (25) | 0.416 | 0.808 | 0.436 | 0.360 | 0.480 | 0.640 | 0.680 | 0.680 | 0.514 |
| `bm25+stop+authors+title2x` | paraphrase | 25 | 0.319 (25) | 0.356 | 0.800 | 0.072 | 0.040 | 0.120 | 0.160 | 0.200 | 0.280 | 0.402 |
| `bm25+stop+authors+title2x` | known_item | 25 | 0.670 (25) | 0.584 | 0.908 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.836 |
| `bm25+stop+exact+stems` | keyword | 25 | 0.570 (25) | 0.572 | 0.944 | 0.629 | 0.520 | 0.880 | 0.920 | 0.920 | 0.960 | 0.810 |
| `bm25+stop+exact+stems` | question | 25 | 0.449 (25) | 0.484 | 0.916 | 0.431 | 0.360 | 0.480 | 0.640 | 0.720 | 0.720 | 0.555 |
| `bm25+stop+exact+stems` | paraphrase | 25 | 0.357 (25) | 0.412 | 0.892 | 0.129 | 0.080 | 0.240 | 0.280 | 0.280 | 0.360 | 0.499 |
| `bm25+stop+exact+stems` | known_item | 25 | 0.635 (25) | 0.572 | 0.836 | 0.873 | 0.760 | 1.000 | 1.000 | 1.000 | 1.000 | 0.889 |
| `bm25+stop+exact+stems+authors` | keyword | 25 | 0.578 (25) | 0.584 | 0.944 | 0.630 | 0.520 | 0.840 | 0.920 | 0.920 | 0.960 | 0.810 |
| `bm25+stop+exact+stems+authors` | question | 25 | 0.444 (25) | 0.476 | 0.920 | 0.432 | 0.360 | 0.520 | 0.640 | 0.720 | 0.720 | 0.560 |
| `bm25+stop+exact+stems+authors` | paraphrase | 25 | 0.352 (25) | 0.416 | 0.896 | 0.128 | 0.080 | 0.240 | 0.240 | 0.280 | 0.360 | 0.499 |
| `bm25+stop+exact+stems+authors` | known_item | 25 | 0.664 (25) | 0.584 | 0.924 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.913 |
| `bm25+stop+exact+stems+authors+title2x` | keyword | 25 | 0.581 (25) | 0.588 | 0.956 | 0.663 | 0.520 | 0.920 | 0.920 | 0.920 | 0.960 | 0.810 |
| `bm25+stop+exact+stems+authors+title2x` | question | 25 | 0.447 (25) | 0.472 | 0.928 | 0.452 | 0.400 | 0.480 | 0.640 | 0.720 | 0.720 | 0.568 |
| `bm25+stop+exact+stems+authors+title2x` | paraphrase | 25 | 0.352 (25) | 0.412 | 0.920 | 0.122 | 0.080 | 0.200 | 0.240 | 0.280 | 0.360 | 0.500 |
| `bm25+stop+exact+stems+authors+title2x` | known_item | 25 | 0.670 (25) | 0.592 | 0.948 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.893 |
| `bm25+stop+exact+stems+title2x` | keyword | 25 | 0.578 (25) | 0.584 | 0.952 | 0.657 | 0.520 | 0.920 | 0.920 | 0.920 | 0.960 | 0.810 |
| `bm25+stop+exact+stems+title2x` | question | 25 | 0.447 (25) | 0.468 | 0.924 | 0.453 | 0.400 | 0.520 | 0.640 | 0.720 | 0.720 | 0.560 |
| `bm25+stop+exact+stems+title2x` | paraphrase | 25 | 0.355 (25) | 0.408 | 0.904 | 0.125 | 0.080 | 0.200 | 0.280 | 0.280 | 0.360 | 0.491 |
| `bm25+stop+exact+stems+title2x` | known_item | 25 | 0.661 (25) | 0.608 | 0.880 | 0.940 | 0.880 | 1.000 | 1.000 | 1.000 | 1.000 | 0.869 |
| `bm25+stop+stem` | keyword | 25 | 0.565 (25) | 0.544 | 0.856 | 0.649 | 0.560 | 0.760 | 0.880 | 0.920 | 0.960 | 0.749 |
| `bm25+stop+stem` | question | 25 | 0.403 (25) | 0.392 | 0.708 | 0.409 | 0.320 | 0.480 | 0.640 | 0.680 | 0.680 | 0.500 |
| `bm25+stop+stem` | paraphrase | 25 | 0.304 (25) | 0.324 | 0.668 | 0.164 | 0.120 | 0.200 | 0.320 | 0.320 | 0.360 | 0.473 |
| `bm25+stop+stem` | known_item | 25 | 0.601 (25) | 0.528 | 0.768 | 0.746 | 0.600 | 0.920 | 0.960 | 1.000 | 1.000 | 0.879 |
| `bm25+stop+stem+authors` | keyword | 25 | 0.566 (25) | 0.544 | 0.852 | 0.652 | 0.560 | 0.760 | 0.840 | 0.920 | 0.960 | 0.758 |
| `bm25+stop+stem+authors` | question | 25 | 0.408 (25) | 0.396 | 0.708 | 0.430 | 0.360 | 0.480 | 0.640 | 0.680 | 0.680 | 0.500 |
| `bm25+stop+stem+authors` | paraphrase | 25 | 0.294 (25) | 0.316 | 0.652 | 0.159 | 0.120 | 0.200 | 0.280 | 0.320 | 0.360 | 0.473 |
| `bm25+stop+stem+authors` | known_item | 25 | 0.651 (25) | 0.560 | 0.860 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.893 |
| `bm25+stop+stem+authors+title2x` | keyword | 25 | 0.570 (25) | 0.552 | 0.868 | 0.651 | 0.560 | 0.800 | 0.920 | 0.920 | 0.960 | 0.762 |
| `bm25+stop+stem+authors+title2x` | question | 25 | 0.407 (25) | 0.400 | 0.724 | 0.407 | 0.320 | 0.520 | 0.640 | 0.680 | 0.680 | 0.502 |
| `bm25+stop+stem+authors+title2x` | paraphrase | 25 | 0.297 (25) | 0.328 | 0.676 | 0.157 | 0.120 | 0.160 | 0.280 | 0.280 | 0.360 | 0.473 |
| `bm25+stop+stem+authors+title2x` | known_item | 25 | 0.658 (25) | 0.564 | 0.876 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.900 |
| `bm25+stop+stem+title2x` | keyword | 25 | 0.572 (25) | 0.556 | 0.876 | 0.660 | 0.560 | 0.800 | 0.920 | 0.920 | 0.960 | 0.762 |
| `bm25+stop+stem+title2x` | question | 25 | 0.409 (25) | 0.400 | 0.716 | 0.407 | 0.320 | 0.520 | 0.640 | 0.680 | 0.680 | 0.491 |
| `bm25+stop+stem+title2x` | paraphrase | 25 | 0.298 (25) | 0.316 | 0.668 | 0.161 | 0.120 | 0.160 | 0.320 | 0.320 | 0.360 | 0.473 |
| `bm25+stop+stem+title2x` | known_item | 25 | 0.633 (25) | 0.560 | 0.792 | 0.830 | 0.720 | 1.000 | 1.000 | 1.000 | 1.000 | 0.887 |
| `bm25+stop+title2x` | keyword | 25 | 0.567 (25) | 0.568 | 0.904 | 0.606 | 0.480 | 0.840 | 0.920 | 0.920 | 1.000 | 0.801 |
| `bm25+stop+title2x` | question | 25 | 0.406 (25) | 0.424 | 0.808 | 0.435 | 0.360 | 0.480 | 0.640 | 0.680 | 0.680 | 0.549 |
| `bm25+stop+title2x` | paraphrase | 25 | 0.321 (25) | 0.364 | 0.808 | 0.096 | 0.080 | 0.120 | 0.200 | 0.200 | 0.280 | 0.402 |
| `bm25+stop+title2x` | known_item | 25 | 0.653 (25) | 0.576 | 0.820 | 0.940 | 0.880 | 1.000 | 1.000 | 1.000 | 1.000 | 0.802 |
| `bm25+title2x` | keyword | 25 | 0.565 (25) | 0.564 | 0.912 | 0.603 | 0.480 | 0.840 | 0.920 | 0.920 | 1.000 | 0.801 |
| `bm25+title2x` | question | 25 | 0.390 (25) | 0.412 | 0.840 | 0.427 | 0.360 | 0.480 | 0.560 | 0.680 | 0.680 | 0.507 |
| `bm25+title2x` | paraphrase | 25 | 0.319 (25) | 0.364 | 0.820 | 0.097 | 0.080 | 0.120 | 0.200 | 0.200 | 0.320 | 0.408 |
| `bm25+title2x` | known_item | 25 | 0.653 (25) | 0.580 | 0.828 | 0.940 | 0.880 | 1.000 | 1.000 | 1.000 | 1.000 | 0.802 |
| `bm25-baseline` | keyword | 25 | 0.563 (25) | 0.560 | 0.904 | 0.593 | 0.480 | 0.800 | 0.920 | 0.920 | 0.960 | 0.790 |
| `bm25-baseline` | question | 25 | 0.399 (25) | 0.424 | 0.820 | 0.408 | 0.320 | 0.520 | 0.560 | 0.680 | 0.680 | 0.547 |
| `bm25-baseline` | paraphrase | 25 | 0.328 (25) | 0.368 | 0.800 | 0.097 | 0.080 | 0.120 | 0.200 | 0.200 | 0.320 | 0.408 |
| `bm25-baseline` | known_item | 25 | 0.627 (25) | 0.544 | 0.792 | 0.907 | 0.840 | 1.000 | 1.000 | 1.000 | 1.000 | 0.822 |
| `cross-minilm-l6+pool=baseline+d=10` | keyword | 25 | 0.728 (25) | 0.744 | 1.000 | 0.763 | 0.680 | 0.880 | 0.960 | 0.960 | 1.000 | 0.948 |
| `cross-minilm-l6+pool=baseline+d=10` | question | 25 | 0.692 (25) | 0.740 | 1.000 | 0.538 | 0.440 | 0.720 | 0.760 | 0.800 | 0.920 | 0.933 |
| `cross-minilm-l6+pool=baseline+d=10` | paraphrase | 25 | 0.628 (25) | 0.648 | 1.000 | 0.402 | 0.280 | 0.560 | 0.720 | 0.800 | 0.840 | 0.959 |
| `cross-minilm-l6+pool=baseline+d=10` | known_item | 25 | 0.704 (25) | 0.624 | 1.000 | 0.933 | 0.880 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `cross-minilm-l6+pool=baseline+d=100` | keyword | 25 | 0.611 (25) | 0.552 | 0.752 | 0.764 | 0.680 | 0.840 | 0.920 | 0.920 | 0.960 | 0.857 |
| `cross-minilm-l6+pool=baseline+d=100` | question | 25 | 0.558 (25) | 0.548 | 0.760 | 0.493 | 0.440 | 0.600 | 0.640 | 0.800 | 0.840 | 0.813 |
| `cross-minilm-l6+pool=baseline+d=100` | paraphrase | 25 | 0.428 (25) | 0.452 | 0.716 | 0.256 | 0.200 | 0.360 | 0.400 | 0.560 | 0.760 | 0.858 |
| `cross-minilm-l6+pool=baseline+d=100` | known_item | 25 | 0.655 (25) | 0.556 | 0.796 | 0.905 | 0.840 | 0.960 | 1.000 | 1.000 | 1.000 | 0.923 |
| `cross-minilm-l6+pool=baseline+d=30` | keyword | 25 | 0.656 (25) | 0.632 | 0.892 | 0.768 | 0.680 | 0.880 | 0.920 | 0.960 | 1.000 | 0.948 |
| `cross-minilm-l6+pool=baseline+d=30` | question | 25 | 0.644 (25) | 0.684 | 0.952 | 0.518 | 0.440 | 0.600 | 0.720 | 0.760 | 0.920 | 0.933 |
| `cross-minilm-l6+pool=baseline+d=30` | paraphrase | 25 | 0.530 (25) | 0.576 | 0.944 | 0.287 | 0.200 | 0.400 | 0.520 | 0.680 | 0.840 | 0.959 |
| `cross-minilm-l6+pool=baseline+d=30` | known_item | 25 | 0.693 (25) | 0.620 | 0.916 | 0.907 | 0.840 | 0.960 | 1.000 | 1.000 | 1.000 | 0.967 |
| `cross-minilm-l6+pool=union100+w=0.5` | keyword | 25 | 0.684 (25) | 0.668 | 0.932 | 0.774 | 0.680 | 0.880 | 0.960 | 0.960 | 1.000 | 0.922 |
| `cross-minilm-l6+pool=union100+w=0.5` | question | 25 | 0.683 (25) | 0.708 | 0.972 | 0.587 | 0.480 | 0.680 | 0.760 | 0.760 | 0.920 | 0.903 |
| `cross-minilm-l6+pool=union100+w=0.5` | paraphrase | 25 | 0.590 (25) | 0.588 | 0.920 | 0.429 | 0.360 | 0.560 | 0.640 | 0.680 | 0.800 | 0.944 |
| `cross-minilm-l6+pool=union100+w=0.5` | known_item | 25 | 0.713 (25) | 0.640 | 0.956 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.977 |
| `cross-minilm-l6+pool=union100+w=1` | keyword | 25 | 0.599 (25) | 0.532 | 0.716 | 0.764 | 0.680 | 0.840 | 0.920 | 0.920 | 0.960 | 0.808 |
| `cross-minilm-l6+pool=union100+w=1` | question | 25 | 0.531 (25) | 0.516 | 0.708 | 0.493 | 0.440 | 0.600 | 0.640 | 0.760 | 0.880 | 0.748 |
| `cross-minilm-l6+pool=union100+w=1` | paraphrase | 25 | 0.403 (25) | 0.424 | 0.648 | 0.254 | 0.200 | 0.360 | 0.400 | 0.480 | 0.720 | 0.757 |
| `cross-minilm-l6+pool=union100+w=1` | known_item | 25 | 0.638 (25) | 0.532 | 0.756 | 0.905 | 0.840 | 0.960 | 1.000 | 1.000 | 1.000 | 0.840 |
| `dense-bge-small` | keyword | 25 | 0.614 (25) | 0.656 | 1.000 | 0.654 | 0.600 | 0.680 | 0.800 | 0.880 | 0.960 | 0.733 |
| `dense-bge-small` | question | 25 | 0.577 (25) | 0.624 | 1.000 | 0.418 | 0.320 | 0.560 | 0.680 | 0.720 | 0.880 | 0.669 |
| `dense-bge-small` | paraphrase | 25 | 0.453 (25) | 0.496 | 1.000 | 0.284 | 0.200 | 0.360 | 0.480 | 0.640 | 0.760 | 0.631 |
| `dense-bge-small` | known_item | 25 | 0.614 (25) | 0.560 | 1.000 | 0.667 | 0.560 | 0.800 | 0.840 | 0.920 | 0.960 | 0.815 |
| `dense-e5-small` | keyword | 25 | 0.480 (25) | 0.416 | 0.556 | 0.602 | 0.480 | 0.800 | 0.880 | 0.880 | 0.880 | 0.709 |
| `dense-e5-small` | question | 25 | 0.407 (25) | 0.392 | 0.572 | 0.447 | 0.360 | 0.520 | 0.640 | 0.680 | 0.760 | 0.602 |
| `dense-e5-small` | paraphrase | 25 | 0.289 (25) | 0.252 | 0.428 | 0.264 | 0.240 | 0.280 | 0.320 | 0.480 | 0.560 | 0.557 |
| `dense-e5-small` | known_item | 25 | 0.511 (25) | 0.404 | 0.540 | 0.626 | 0.480 | 0.840 | 0.920 | 0.960 | 1.000 | 0.750 |
| `dense-gte-small` | keyword | 25 | 0.640 (25) | 0.652 | 1.000 | 0.688 | 0.600 | 0.840 | 0.840 | 0.840 | 0.880 | 0.732 |
| `dense-gte-small` | question | 25 | 0.566 (25) | 0.616 | 1.000 | 0.417 | 0.320 | 0.520 | 0.640 | 0.760 | 0.880 | 0.653 |
| `dense-gte-small` | paraphrase | 25 | 0.495 (25) | 0.536 | 1.000 | 0.364 | 0.280 | 0.440 | 0.520 | 0.640 | 0.720 | 0.647 |
| `dense-gte-small` | known_item | 25 | 0.574 (25) | 0.520 | 1.000 | 0.633 | 0.520 | 0.840 | 0.840 | 0.880 | 1.000 | 0.789 |
| `dense-minilm` | keyword | 25 | 0.507 (25) | 0.456 | 0.592 | 0.459 | 0.400 | 0.560 | 0.680 | 0.800 | 0.920 | 0.661 |
| `dense-minilm` | question | 25 | 0.432 (25) | 0.408 | 0.556 | 0.358 | 0.280 | 0.520 | 0.520 | 0.640 | 0.720 | 0.571 |
| `dense-minilm` | paraphrase | 25 | 0.374 (25) | 0.368 | 0.576 | 0.260 | 0.200 | 0.320 | 0.440 | 0.520 | 0.720 | 0.618 |
| `dense-minilm` | known_item | 25 | 0.439 (25) | 0.328 | 0.504 | 0.549 | 0.440 | 0.720 | 0.720 | 0.760 | 0.880 | 0.710 |
| `dense-openai-large` | keyword | 25 | 0.626 (25) | 0.676 | 1.000 | 0.577 | 0.480 | 0.800 | 0.800 | 0.880 | 0.920 | 0.848 |
| `dense-openai-large` | question | 25 | 0.669 (25) | 0.704 | 1.000 | 0.560 | 0.440 | 0.720 | 0.800 | 0.840 | 0.920 | 0.840 |
| `dense-openai-large` | paraphrase | 25 | 0.632 (25) | 0.652 | 1.000 | 0.466 | 0.400 | 0.520 | 0.720 | 0.800 | 0.880 | 0.929 |
| `dense-openai-large` | known_item | 25 | 0.595 (25) | 0.516 | 1.000 | 0.793 | 0.680 | 0.920 | 0.960 | 1.000 | 1.000 | 0.877 |
| `field-gte-concat` | keyword | 25 | 0.721 (25) | 0.744 | 1.000 | 0.720 | 0.600 | 0.880 | 0.960 | 0.960 | 1.000 | 0.952 |
| `field-gte-concat` | question | 25 | 0.708 (25) | 0.740 | 1.000 | 0.588 | 0.480 | 0.720 | 0.760 | 0.800 | 0.920 | 0.933 |
| `field-gte-concat` | paraphrase | 25 | 0.672 (25) | 0.648 | 1.000 | 0.498 | 0.400 | 0.600 | 0.720 | 0.800 | 0.840 | 0.959 |
| `field-gte-concat` | known_item | 25 | 0.713 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `field-gte-separate+t=0.25` | keyword | 25 | 0.721 (25) | 0.744 | 1.000 | 0.720 | 0.600 | 0.880 | 0.960 | 0.960 | 1.000 | 0.952 |
| `field-gte-separate+t=0.25` | question | 25 | 0.708 (25) | 0.740 | 1.000 | 0.588 | 0.480 | 0.720 | 0.760 | 0.800 | 0.920 | 0.933 |
| `field-gte-separate+t=0.25` | paraphrase | 25 | 0.672 (25) | 0.648 | 1.000 | 0.498 | 0.400 | 0.600 | 0.720 | 0.800 | 0.840 | 0.959 |
| `field-gte-separate+t=0.25` | known_item | 25 | 0.713 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `field-gte-separate+t=0.5` | keyword | 25 | 0.721 (25) | 0.744 | 1.000 | 0.720 | 0.600 | 0.880 | 0.960 | 0.960 | 1.000 | 0.948 |
| `field-gte-separate+t=0.5` | question | 25 | 0.708 (25) | 0.740 | 1.000 | 0.588 | 0.480 | 0.720 | 0.760 | 0.800 | 0.920 | 0.933 |
| `field-gte-separate+t=0.5` | paraphrase | 25 | 0.672 (25) | 0.648 | 1.000 | 0.498 | 0.400 | 0.600 | 0.720 | 0.800 | 0.840 | 0.959 |
| `field-gte-separate+t=0.5` | known_item | 25 | 0.713 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `field-gte-separate+t=0.75` | keyword | 25 | 0.721 (25) | 0.744 | 1.000 | 0.720 | 0.600 | 0.880 | 0.960 | 0.960 | 1.000 | 0.948 |
| `field-gte-separate+t=0.75` | question | 25 | 0.708 (25) | 0.740 | 1.000 | 0.588 | 0.480 | 0.720 | 0.760 | 0.800 | 0.920 | 0.933 |
| `field-gte-separate+t=0.75` | paraphrase | 25 | 0.672 (25) | 0.648 | 1.000 | 0.498 | 0.400 | 0.600 | 0.720 | 0.800 | 0.840 | 0.959 |
| `field-gte-separate+t=0.75` | known_item | 25 | 0.713 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `field-lexical+t=0.25` | keyword | 25 | 0.716 (25) | 0.736 | 1.000 | 0.722 | 0.600 | 0.920 | 0.960 | 1.000 | 1.000 | 0.918 |
| `field-lexical+t=0.25` | question | 25 | 0.695 (25) | 0.732 | 1.000 | 0.580 | 0.480 | 0.720 | 0.760 | 0.800 | 0.920 | 0.912 |
| `field-lexical+t=0.25` | paraphrase | 25 | 0.632 (25) | 0.636 | 1.000 | 0.397 | 0.280 | 0.600 | 0.680 | 0.720 | 0.840 | 0.959 |
| `field-lexical+t=0.25` | known_item | 25 | 0.724 (25) | 0.640 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.987 |
| `field-lexical+t=0.5` | keyword | 25 | 0.705 (25) | 0.736 | 1.000 | 0.690 | 0.520 | 0.880 | 0.960 | 0.960 | 1.000 | 0.921 |
| `field-lexical+t=0.5` | question | 25 | 0.683 (25) | 0.720 | 1.000 | 0.562 | 0.440 | 0.720 | 0.760 | 0.800 | 0.880 | 0.912 |
| `field-lexical+t=0.5` | paraphrase | 25 | 0.616 (25) | 0.636 | 1.000 | 0.354 | 0.200 | 0.640 | 0.680 | 0.720 | 0.840 | 0.963 |
| `field-lexical+t=0.5` | known_item | 25 | 0.726 (25) | 0.640 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.980 |
| `field-lexical+t=0.75` | keyword | 25 | 0.683 (25) | 0.720 | 1.000 | 0.649 | 0.520 | 0.880 | 0.920 | 0.960 | 1.000 | 0.913 |
| `field-lexical+t=0.75` | question | 25 | 0.656 (25) | 0.700 | 1.000 | 0.486 | 0.320 | 0.720 | 0.760 | 0.800 | 0.880 | 0.913 |
| `field-lexical+t=0.75` | paraphrase | 25 | 0.603 (25) | 0.640 | 1.000 | 0.331 | 0.200 | 0.600 | 0.680 | 0.760 | 0.840 | 0.963 |
| `field-lexical+t=0.75` | known_item | 25 | 0.725 (25) | 0.640 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.980 |
| `field-order-gte-concat` | keyword | 25 | 0.738 (25) | 0.744 | 1.000 | 0.734 | 0.640 | 0.840 | 0.960 | 0.960 | 1.000 | 0.948 |
| `field-order-gte-concat` | question | 25 | 0.679 (25) | 0.740 | 1.000 | 0.461 | 0.320 | 0.720 | 0.760 | 0.800 | 0.920 | 0.933 |
| `field-order-gte-concat` | paraphrase | 25 | 0.646 (25) | 0.648 | 1.000 | 0.489 | 0.400 | 0.600 | 0.720 | 0.800 | 0.840 | 0.959 |
| `field-order-gte-concat` | known_item | 25 | 0.703 (25) | 0.624 | 1.000 | 0.801 | 0.680 | 0.960 | 1.000 | 1.000 | 1.000 | 0.967 |
| `field-order-gte-separate+t=0.25` | keyword | 25 | 0.723 (25) | 0.744 | 1.000 | 0.696 | 0.600 | 0.800 | 0.960 | 0.960 | 1.000 | 0.948 |
| `field-order-gte-separate+t=0.25` | question | 25 | 0.681 (25) | 0.740 | 1.000 | 0.496 | 0.360 | 0.680 | 0.760 | 0.800 | 0.920 | 0.933 |
| `field-order-gte-separate+t=0.25` | paraphrase | 25 | 0.656 (25) | 0.648 | 1.000 | 0.510 | 0.440 | 0.640 | 0.720 | 0.800 | 0.840 | 0.959 |
| `field-order-gte-separate+t=0.25` | known_item | 25 | 0.698 (25) | 0.624 | 1.000 | 0.781 | 0.640 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `field-order-gte-separate+t=0.5` | keyword | 25 | 0.716 (25) | 0.744 | 1.000 | 0.646 | 0.520 | 0.840 | 0.960 | 0.960 | 1.000 | 0.948 |
| `field-order-gte-separate+t=0.5` | question | 25 | 0.672 (25) | 0.740 | 1.000 | 0.454 | 0.320 | 0.680 | 0.760 | 0.800 | 0.920 | 0.933 |
| `field-order-gte-separate+t=0.5` | paraphrase | 25 | 0.641 (25) | 0.648 | 1.000 | 0.465 | 0.360 | 0.640 | 0.720 | 0.800 | 0.840 | 0.959 |
| `field-order-gte-separate+t=0.5` | known_item | 25 | 0.697 (25) | 0.624 | 1.000 | 0.830 | 0.720 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `field-order-gte-separate+t=0.75` | keyword | 25 | 0.703 (25) | 0.744 | 1.000 | 0.608 | 0.520 | 0.800 | 0.960 | 0.960 | 1.000 | 0.948 |
| `field-order-gte-separate+t=0.75` | question | 25 | 0.648 (25) | 0.740 | 1.000 | 0.354 | 0.160 | 0.680 | 0.760 | 0.800 | 0.920 | 0.933 |
| `field-order-gte-separate+t=0.75` | paraphrase | 25 | 0.611 (25) | 0.648 | 1.000 | 0.354 | 0.200 | 0.600 | 0.720 | 0.800 | 0.840 | 0.959 |
| `field-order-gte-separate+t=0.75` | known_item | 25 | 0.691 (25) | 0.624 | 1.000 | 0.791 | 0.680 | 0.960 | 1.000 | 1.000 | 1.000 | 0.967 |
| `fusion-linear+w=0.25+d=100` | keyword | 25 | 0.681 (25) | 0.692 | 1.000 | 0.741 | 0.640 | 0.880 | 0.880 | 0.960 | 1.000 | 0.819 |
| `fusion-linear+w=0.25+d=100` | question | 25 | 0.589 (25) | 0.588 | 1.000 | 0.557 | 0.480 | 0.640 | 0.720 | 0.720 | 0.720 | 0.606 |
| `fusion-linear+w=0.25+d=100` | paraphrase | 25 | 0.519 (25) | 0.540 | 1.000 | 0.267 | 0.200 | 0.360 | 0.360 | 0.400 | 0.440 | 0.557 |
| `fusion-linear+w=0.25+d=100` | known_item | 25 | 0.710 (25) | 0.636 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.933 |
| `fusion-linear+w=0.25+d=20` | keyword | 25 | 0.629 (25) | 0.624 | 1.000 | 0.759 | 0.640 | 0.880 | 0.920 | 1.000 | 1.000 | 0.829 |
| `fusion-linear+w=0.25+d=20` | question | 25 | 0.476 (25) | 0.460 | 1.000 | 0.525 | 0.480 | 0.600 | 0.640 | 0.760 | 0.840 | 0.758 |
| `fusion-linear+w=0.25+d=20` | paraphrase | 25 | 0.384 (25) | 0.424 | 1.000 | 0.193 | 0.160 | 0.240 | 0.280 | 0.720 | 0.840 | 0.887 |
| `fusion-linear+w=0.25+d=20` | known_item | 25 | 0.671 (25) | 0.596 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.867 |
| `fusion-linear+w=0.25+d=50` | keyword | 25 | 0.659 (25) | 0.652 | 1.000 | 0.739 | 0.640 | 0.880 | 0.920 | 0.920 | 1.000 | 0.894 |
| `fusion-linear+w=0.25+d=50` | question | 25 | 0.529 (25) | 0.508 | 1.000 | 0.546 | 0.480 | 0.600 | 0.680 | 0.720 | 0.800 | 0.782 |
| `fusion-linear+w=0.25+d=50` | paraphrase | 25 | 0.437 (25) | 0.452 | 1.000 | 0.207 | 0.160 | 0.280 | 0.280 | 0.360 | 0.800 | 0.867 |
| `fusion-linear+w=0.25+d=50` | known_item | 25 | 0.686 (25) | 0.616 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.987 |
| `fusion-linear+w=0.5+d=100` | keyword | 25 | 0.712 (25) | 0.744 | 1.000 | 0.692 | 0.600 | 0.840 | 0.880 | 1.000 | 1.000 | 0.931 |
| `fusion-linear+w=0.5+d=100` | question | 25 | 0.675 (25) | 0.708 | 1.000 | 0.553 | 0.440 | 0.680 | 0.760 | 0.800 | 0.920 | 0.895 |
| `fusion-linear+w=0.5+d=100` | paraphrase | 25 | 0.604 (25) | 0.636 | 1.000 | 0.303 | 0.200 | 0.440 | 0.520 | 0.720 | 0.840 | 0.959 |
| `fusion-linear+w=0.5+d=100` | known_item | 25 | 0.717 (25) | 0.648 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.977 |
| `fusion-linear+w=0.5+d=20` | keyword | 25 | 0.649 (25) | 0.652 | 1.000 | 0.706 | 0.600 | 0.920 | 0.920 | 1.000 | 1.000 | 0.829 |
| `fusion-linear+w=0.5+d=20` | question | 25 | 0.617 (25) | 0.608 | 1.000 | 0.545 | 0.440 | 0.680 | 0.760 | 0.800 | 0.840 | 0.758 |
| `fusion-linear+w=0.5+d=20` | paraphrase | 25 | 0.545 (25) | 0.568 | 1.000 | 0.329 | 0.160 | 0.600 | 0.680 | 0.760 | 0.840 | 0.887 |
| `fusion-linear+w=0.5+d=20` | known_item | 25 | 0.668 (25) | 0.592 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.867 |
| `fusion-linear+w=0.5+d=50` | keyword | 25 | 0.695 (25) | 0.716 | 1.000 | 0.693 | 0.600 | 0.840 | 0.880 | 1.000 | 1.000 | 0.914 |
| `fusion-linear+w=0.5+d=50` | question | 25 | 0.654 (25) | 0.676 | 1.000 | 0.550 | 0.440 | 0.720 | 0.760 | 0.800 | 0.920 | 0.856 |
| `fusion-linear+w=0.5+d=50` | paraphrase | 25 | 0.588 (25) | 0.592 | 1.000 | 0.330 | 0.200 | 0.440 | 0.680 | 0.800 | 0.840 | 0.951 |
| `fusion-linear+w=0.5+d=50` | known_item | 25 | 0.702 (25) | 0.624 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.957 |
| `fusion-linear+w=0.75+d=100` | keyword | 25 | 0.713 (25) | 0.744 | 1.000 | 0.640 | 0.520 | 0.800 | 0.920 | 0.920 | 0.960 | 0.872 |
| `fusion-linear+w=0.75+d=100` | question | 25 | 0.698 (25) | 0.736 | 1.000 | 0.563 | 0.440 | 0.760 | 0.760 | 0.840 | 0.920 | 0.846 |
| `fusion-linear+w=0.75+d=100` | paraphrase | 25 | 0.652 (25) | 0.660 | 1.000 | 0.347 | 0.240 | 0.440 | 0.680 | 0.800 | 0.880 | 0.943 |
| `fusion-linear+w=0.75+d=100` | known_item | 25 | 0.693 (25) | 0.600 | 1.000 | 0.947 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.923 |
| `fusion-linear+w=0.75+d=20` | keyword | 25 | 0.646 (25) | 0.676 | 1.000 | 0.620 | 0.520 | 0.760 | 0.800 | 0.960 | 1.000 | 0.829 |
| `fusion-linear+w=0.75+d=20` | question | 25 | 0.684 (25) | 0.700 | 1.000 | 0.579 | 0.440 | 0.760 | 0.800 | 0.800 | 0.840 | 0.758 |
| `fusion-linear+w=0.75+d=20` | paraphrase | 25 | 0.649 (25) | 0.648 | 1.000 | 0.436 | 0.320 | 0.560 | 0.720 | 0.800 | 0.840 | 0.887 |
| `fusion-linear+w=0.75+d=20` | known_item | 25 | 0.630 (25) | 0.520 | 1.000 | 0.933 | 0.920 | 0.960 | 0.960 | 1.000 | 1.000 | 0.867 |
| `fusion-linear+w=0.75+d=50` | keyword | 25 | 0.687 (25) | 0.720 | 1.000 | 0.631 | 0.520 | 0.760 | 0.920 | 0.920 | 1.000 | 0.918 |
| `fusion-linear+w=0.75+d=50` | question | 25 | 0.694 (25) | 0.720 | 1.000 | 0.578 | 0.440 | 0.760 | 0.800 | 0.840 | 0.920 | 0.872 |
| `fusion-linear+w=0.75+d=50` | paraphrase | 25 | 0.643 (25) | 0.652 | 1.000 | 0.373 | 0.240 | 0.600 | 0.760 | 0.800 | 0.880 | 0.977 |
| `fusion-linear+w=0.75+d=50` | known_item | 25 | 0.666 (25) | 0.564 | 1.000 | 0.947 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.917 |
| `fusion-rankscore+a=0.25+d=100` | keyword | 25 | 0.713 (25) | 0.744 | 1.000 | 0.665 | 0.520 | 0.880 | 0.960 | 0.960 | 1.000 | 0.904 |
| `fusion-rankscore+a=0.25+d=100` | question | 25 | 0.697 (25) | 0.740 | 1.000 | 0.561 | 0.440 | 0.760 | 0.760 | 0.800 | 0.920 | 0.918 |
| `fusion-rankscore+a=0.25+d=100` | paraphrase | 25 | 0.654 (25) | 0.660 | 1.000 | 0.377 | 0.280 | 0.440 | 0.680 | 0.760 | 0.880 | 0.972 |
| `fusion-rankscore+a=0.25+d=100` | known_item | 25 | 0.710 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.957 |
| `fusion-rankscore+a=0.25+d=500` | keyword | 25 | 0.713 (25) | 0.744 | 1.000 | 0.665 | 0.520 | 0.880 | 0.960 | 0.960 | 1.000 | 0.937 |
| `fusion-rankscore+a=0.25+d=500` | question | 25 | 0.698 (25) | 0.744 | 1.000 | 0.560 | 0.440 | 0.720 | 0.760 | 0.800 | 0.920 | 0.937 |
| `fusion-rankscore+a=0.25+d=500` | paraphrase | 25 | 0.646 (25) | 0.648 | 1.000 | 0.379 | 0.280 | 0.440 | 0.680 | 0.760 | 0.840 | 0.959 |
| `fusion-rankscore+a=0.25+d=500` | known_item | 25 | 0.708 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `fusion-rankscore+a=0.5+d=100` | keyword | 25 | 0.706 (25) | 0.736 | 1.000 | 0.674 | 0.520 | 0.880 | 0.960 | 0.960 | 0.960 | 0.880 |
| `fusion-rankscore+a=0.5+d=100` | question | 25 | 0.695 (25) | 0.736 | 1.000 | 0.565 | 0.440 | 0.760 | 0.760 | 0.800 | 0.920 | 0.911 |
| `fusion-rankscore+a=0.5+d=100` | paraphrase | 25 | 0.655 (25) | 0.664 | 1.000 | 0.375 | 0.280 | 0.440 | 0.680 | 0.760 | 0.880 | 0.964 |
| `fusion-rankscore+a=0.5+d=100` | known_item | 25 | 0.715 (25) | 0.628 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.937 |
| `fusion-rankscore+a=0.5+d=500` | keyword | 25 | 0.710 (25) | 0.744 | 1.000 | 0.674 | 0.520 | 0.880 | 0.960 | 0.960 | 1.000 | 0.931 |
| `fusion-rankscore+a=0.5+d=500` | question | 25 | 0.695 (25) | 0.736 | 1.000 | 0.561 | 0.440 | 0.720 | 0.760 | 0.800 | 0.920 | 0.929 |
| `fusion-rankscore+a=0.5+d=500` | paraphrase | 25 | 0.650 (25) | 0.648 | 1.000 | 0.386 | 0.280 | 0.480 | 0.680 | 0.720 | 0.840 | 0.969 |
| `fusion-rankscore+a=0.5+d=500` | known_item | 25 | 0.716 (25) | 0.632 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `fusion-rankscore+a=0.75+d=100` | keyword | 25 | 0.718 (25) | 0.744 | 1.000 | 0.700 | 0.560 | 0.880 | 0.960 | 0.960 | 0.960 | 0.880 |
| `fusion-rankscore+a=0.75+d=100` | question | 25 | 0.698 (25) | 0.728 | 1.000 | 0.568 | 0.440 | 0.720 | 0.760 | 0.800 | 0.920 | 0.911 |
| `fusion-rankscore+a=0.75+d=100` | paraphrase | 25 | 0.655 (25) | 0.664 | 1.000 | 0.412 | 0.360 | 0.440 | 0.640 | 0.720 | 0.880 | 0.964 |
| `fusion-rankscore+a=0.75+d=100` | known_item | 25 | 0.717 (25) | 0.628 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.937 |
| `fusion-rankscore+a=0.75+d=500` | keyword | 25 | 0.715 (25) | 0.740 | 1.000 | 0.700 | 0.560 | 0.880 | 0.960 | 0.960 | 1.000 | 0.925 |
| `fusion-rankscore+a=0.75+d=500` | question | 25 | 0.700 (25) | 0.736 | 0.996 | 0.563 | 0.440 | 0.720 | 0.720 | 0.800 | 0.880 | 0.909 |
| `fusion-rankscore+a=0.75+d=500` | paraphrase | 25 | 0.676 (25) | 0.672 | 1.000 | 0.471 | 0.400 | 0.600 | 0.680 | 0.680 | 0.760 | 0.929 |
| `fusion-rankscore+a=0.75+d=500` | known_item | 25 | 0.721 (25) | 0.636 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.977 |
| `fusion-rrf+w=0+d=100+c=10` | keyword | 25 | 0.595 (25) | 0.596 | 1.000 | 0.710 | 0.600 | 0.880 | 0.920 | 0.920 | 0.960 | 0.786 |
| `fusion-rrf+w=0+d=100+c=10` | question | 25 | 0.423 (25) | 0.452 | 1.000 | 0.432 | 0.360 | 0.520 | 0.640 | 0.640 | 0.720 | 0.569 |
| `fusion-rrf+w=0+d=100+c=10` | paraphrase | 25 | 0.357 (25) | 0.412 | 1.000 | 0.132 | 0.080 | 0.240 | 0.280 | 0.280 | 0.400 | 0.490 |
| `fusion-rrf+w=0+d=100+c=10` | known_item | 25 | 0.661 (25) | 0.588 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.913 |
| `fusion-rrf+w=0.25+d=100+c=10` | keyword | 25 | 0.650 (25) | 0.652 | 1.000 | 0.725 | 0.600 | 0.880 | 0.920 | 1.000 | 1.000 | 0.879 |
| `fusion-rrf+w=0.25+d=100+c=10` | question | 25 | 0.489 (25) | 0.488 | 1.000 | 0.505 | 0.440 | 0.560 | 0.680 | 0.720 | 0.760 | 0.707 |
| `fusion-rrf+w=0.25+d=100+c=10` | paraphrase | 25 | 0.412 (25) | 0.468 | 1.000 | 0.199 | 0.160 | 0.280 | 0.320 | 0.400 | 0.760 | 0.856 |
| `fusion-rrf+w=0.25+d=100+c=10` | known_item | 25 | 0.684 (25) | 0.620 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.963 |
| `fusion-rrf+w=0.25+d=100+c=100` | keyword | 25 | 0.689 (25) | 0.708 | 1.000 | 0.743 | 0.640 | 0.880 | 0.880 | 1.000 | 1.000 | 0.838 |
| `fusion-rrf+w=0.25+d=100+c=100` | question | 25 | 0.629 (25) | 0.652 | 1.000 | 0.547 | 0.480 | 0.640 | 0.720 | 0.720 | 0.720 | 0.665 |
| `fusion-rrf+w=0.25+d=100+c=100` | paraphrase | 25 | 0.545 (25) | 0.576 | 1.000 | 0.251 | 0.160 | 0.360 | 0.400 | 0.440 | 0.440 | 0.588 |
| `fusion-rrf+w=0.25+d=100+c=100` | known_item | 25 | 0.725 (25) | 0.648 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.939 |
| `fusion-rrf+w=0.25+d=100+c=60` | keyword | 25 | 0.678 (25) | 0.688 | 1.000 | 0.743 | 0.640 | 0.880 | 0.880 | 0.960 | 1.000 | 0.842 |
| `fusion-rrf+w=0.25+d=100+c=60` | question | 25 | 0.586 (25) | 0.604 | 1.000 | 0.544 | 0.480 | 0.640 | 0.720 | 0.720 | 0.720 | 0.652 |
| `fusion-rrf+w=0.25+d=100+c=60` | paraphrase | 25 | 0.508 (25) | 0.536 | 1.000 | 0.237 | 0.160 | 0.360 | 0.360 | 0.440 | 0.440 | 0.588 |
| `fusion-rrf+w=0.25+d=100+c=60` | known_item | 25 | 0.713 (25) | 0.644 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.939 |
| `fusion-rrf+w=0.25+d=20+c=10` | keyword | 25 | 0.635 (25) | 0.632 | 1.000 | 0.725 | 0.600 | 0.880 | 0.920 | 0.920 | 1.000 | 0.829 |
| `fusion-rrf+w=0.25+d=20+c=10` | question | 25 | 0.486 (25) | 0.480 | 1.000 | 0.522 | 0.480 | 0.560 | 0.640 | 0.640 | 0.840 | 0.758 |
| `fusion-rrf+w=0.25+d=20+c=10` | paraphrase | 25 | 0.393 (25) | 0.432 | 1.000 | 0.195 | 0.160 | 0.280 | 0.280 | 0.280 | 0.840 | 0.887 |
| `fusion-rrf+w=0.25+d=20+c=10` | known_item | 25 | 0.677 (25) | 0.608 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.867 |
| `fusion-rrf+w=0.25+d=20+c=100` | keyword | 25 | 0.642 (25) | 0.640 | 1.000 | 0.717 | 0.600 | 0.880 | 0.880 | 0.920 | 1.000 | 0.829 |
| `fusion-rrf+w=0.25+d=20+c=100` | question | 25 | 0.526 (25) | 0.500 | 1.000 | 0.533 | 0.480 | 0.600 | 0.640 | 0.640 | 0.840 | 0.758 |
| `fusion-rrf+w=0.25+d=20+c=100` | paraphrase | 25 | 0.424 (25) | 0.424 | 1.000 | 0.227 | 0.200 | 0.280 | 0.280 | 0.280 | 0.840 | 0.887 |
| `fusion-rrf+w=0.25+d=20+c=100` | known_item | 25 | 0.693 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.867 |
| `fusion-rrf+w=0.25+d=20+c=60` | keyword | 25 | 0.642 (25) | 0.640 | 1.000 | 0.717 | 0.600 | 0.880 | 0.880 | 0.920 | 1.000 | 0.829 |
| `fusion-rrf+w=0.25+d=20+c=60` | question | 25 | 0.526 (25) | 0.500 | 1.000 | 0.533 | 0.480 | 0.600 | 0.640 | 0.640 | 0.840 | 0.758 |
| `fusion-rrf+w=0.25+d=20+c=60` | paraphrase | 25 | 0.424 (25) | 0.424 | 1.000 | 0.227 | 0.200 | 0.280 | 0.280 | 0.280 | 0.840 | 0.887 |
| `fusion-rrf+w=0.25+d=20+c=60` | known_item | 25 | 0.693 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.867 |
| `fusion-rrf+w=0.25+d=50+c=10` | keyword | 25 | 0.648 (25) | 0.648 | 1.000 | 0.725 | 0.600 | 0.880 | 0.920 | 0.960 | 1.000 | 0.869 |
| `fusion-rrf+w=0.25+d=50+c=10` | question | 25 | 0.490 (25) | 0.488 | 1.000 | 0.506 | 0.440 | 0.560 | 0.680 | 0.720 | 0.800 | 0.690 |
| `fusion-rrf+w=0.25+d=50+c=10` | paraphrase | 25 | 0.413 (25) | 0.468 | 1.000 | 0.199 | 0.160 | 0.280 | 0.320 | 0.360 | 0.800 | 0.827 |
| `fusion-rrf+w=0.25+d=50+c=10` | known_item | 25 | 0.680 (25) | 0.616 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.950 |
| `fusion-rrf+w=0.25+d=50+c=100` | keyword | 25 | 0.677 (25) | 0.680 | 1.000 | 0.738 | 0.640 | 0.840 | 0.880 | 0.960 | 0.960 | 0.786 |
| `fusion-rrf+w=0.25+d=50+c=100` | question | 25 | 0.609 (25) | 0.616 | 1.000 | 0.551 | 0.480 | 0.640 | 0.720 | 0.720 | 0.720 | 0.569 |
| `fusion-rrf+w=0.25+d=50+c=100` | paraphrase | 25 | 0.525 (25) | 0.540 | 1.000 | 0.251 | 0.160 | 0.360 | 0.400 | 0.400 | 0.400 | 0.490 |
| `fusion-rrf+w=0.25+d=50+c=100` | known_item | 25 | 0.728 (25) | 0.656 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.913 |
| `fusion-rrf+w=0.25+d=50+c=60` | keyword | 25 | 0.672 (25) | 0.680 | 1.000 | 0.740 | 0.640 | 0.840 | 0.880 | 0.960 | 0.960 | 0.786 |
| `fusion-rrf+w=0.25+d=50+c=60` | question | 25 | 0.582 (25) | 0.592 | 1.000 | 0.548 | 0.480 | 0.640 | 0.720 | 0.720 | 0.720 | 0.569 |
| `fusion-rrf+w=0.25+d=50+c=60` | paraphrase | 25 | 0.491 (25) | 0.504 | 1.000 | 0.237 | 0.160 | 0.360 | 0.360 | 0.400 | 0.400 | 0.490 |
| `fusion-rrf+w=0.25+d=50+c=60` | known_item | 25 | 0.712 (25) | 0.640 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.913 |
| `fusion-rrf+w=0.5+d=100+c=10` | keyword | 25 | 0.680 (25) | 0.692 | 1.000 | 0.717 | 0.600 | 0.920 | 0.960 | 1.000 | 1.000 | 0.934 |
| `fusion-rrf+w=0.5+d=100+c=10` | question | 25 | 0.644 (25) | 0.660 | 1.000 | 0.553 | 0.440 | 0.760 | 0.760 | 0.800 | 0.920 | 0.901 |
| `fusion-rrf+w=0.5+d=100+c=10` | paraphrase | 25 | 0.580 (25) | 0.576 | 1.000 | 0.364 | 0.240 | 0.520 | 0.640 | 0.800 | 0.840 | 0.959 |
| `fusion-rrf+w=0.5+d=100+c=10` | known_item | 25 | 0.687 (25) | 0.604 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.987 |
| `fusion-rrf+w=0.5+d=100+c=100` | keyword | 25 | 0.710 (25) | 0.752 | 1.000 | 0.692 | 0.600 | 0.840 | 0.880 | 0.960 | 1.000 | 0.915 |
| `fusion-rrf+w=0.5+d=100+c=100` | question | 25 | 0.688 (25) | 0.720 | 1.000 | 0.549 | 0.440 | 0.680 | 0.720 | 0.760 | 0.920 | 0.899 |
| `fusion-rrf+w=0.5+d=100+c=100` | paraphrase | 25 | 0.604 (25) | 0.640 | 1.000 | 0.305 | 0.200 | 0.440 | 0.480 | 0.640 | 0.840 | 0.947 |
| `fusion-rrf+w=0.5+d=100+c=100` | known_item | 25 | 0.715 (25) | 0.644 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.976 |
| `fusion-rrf+w=0.5+d=100+c=30` | keyword | 25 | 0.710 (25) | 0.740 | 1.000 | 0.709 | 0.600 | 0.840 | 0.960 | 1.000 | 1.000 | 0.921 |
| `fusion-rrf+w=0.5+d=100+c=30` | question | 25 | 0.674 (25) | 0.688 | 1.000 | 0.548 | 0.440 | 0.680 | 0.760 | 0.800 | 0.920 | 0.899 |
| `fusion-rrf+w=0.5+d=100+c=30` | paraphrase | 25 | 0.608 (25) | 0.616 | 1.000 | 0.348 | 0.240 | 0.440 | 0.640 | 0.760 | 0.840 | 0.959 |
| `fusion-rrf+w=0.5+d=100+c=30` | known_item | 25 | 0.722 (25) | 0.648 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.987 |
| `fusion-rrf+w=0.5+d=100+c=60` | keyword | 25 | 0.713 (25) | 0.748 | 1.000 | 0.697 | 0.600 | 0.840 | 0.920 | 1.000 | 1.000 | 0.915 |
| `fusion-rrf+w=0.5+d=100+c=60` | question | 25 | 0.690 (25) | 0.720 | 1.000 | 0.542 | 0.440 | 0.680 | 0.720 | 0.760 | 0.920 | 0.899 |
| `fusion-rrf+w=0.5+d=100+c=60` | paraphrase | 25 | 0.607 (25) | 0.644 | 1.000 | 0.304 | 0.200 | 0.440 | 0.480 | 0.720 | 0.840 | 0.947 |
| `fusion-rrf+w=0.5+d=100+c=60` | known_item | 25 | 0.718 (25) | 0.644 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.980 |
| `fusion-rrf+w=0.5+d=20+c=10` | keyword | 25 | 0.664 (25) | 0.668 | 1.000 | 0.713 | 0.600 | 0.920 | 0.920 | 1.000 | 1.000 | 0.829 |
| `fusion-rrf+w=0.5+d=20+c=10` | question | 25 | 0.628 (25) | 0.628 | 1.000 | 0.542 | 0.440 | 0.680 | 0.760 | 0.800 | 0.840 | 0.758 |
| `fusion-rrf+w=0.5+d=20+c=10` | paraphrase | 25 | 0.548 (25) | 0.560 | 1.000 | 0.320 | 0.160 | 0.600 | 0.680 | 0.760 | 0.840 | 0.887 |
| `fusion-rrf+w=0.5+d=20+c=10` | known_item | 25 | 0.685 (25) | 0.604 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.867 |
| `fusion-rrf+w=0.5+d=20+c=100` | keyword | 25 | 0.668 (25) | 0.676 | 1.000 | 0.696 | 0.600 | 0.880 | 0.920 | 1.000 | 1.000 | 0.829 |
| `fusion-rrf+w=0.5+d=20+c=100` | question | 25 | 0.627 (25) | 0.628 | 1.000 | 0.544 | 0.440 | 0.680 | 0.760 | 0.800 | 0.840 | 0.758 |
| `fusion-rrf+w=0.5+d=20+c=100` | paraphrase | 25 | 0.543 (25) | 0.560 | 1.000 | 0.313 | 0.160 | 0.560 | 0.680 | 0.760 | 0.840 | 0.887 |
| `fusion-rrf+w=0.5+d=20+c=100` | known_item | 25 | 0.686 (25) | 0.612 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.867 |
| `fusion-rrf+w=0.5+d=20+c=60` | keyword | 25 | 0.668 (25) | 0.676 | 1.000 | 0.696 | 0.600 | 0.880 | 0.920 | 1.000 | 1.000 | 0.829 |
| `fusion-rrf+w=0.5+d=20+c=60` | question | 25 | 0.627 (25) | 0.628 | 1.000 | 0.537 | 0.440 | 0.680 | 0.760 | 0.800 | 0.840 | 0.758 |
| `fusion-rrf+w=0.5+d=20+c=60` | paraphrase | 25 | 0.543 (25) | 0.560 | 1.000 | 0.313 | 0.160 | 0.560 | 0.680 | 0.760 | 0.840 | 0.887 |
| `fusion-rrf+w=0.5+d=20+c=60` | known_item | 25 | 0.686 (25) | 0.612 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.867 |
| `fusion-rrf+w=0.5+d=50+c=10` | keyword | 25 | 0.673 (25) | 0.688 | 1.000 | 0.711 | 0.600 | 0.840 | 0.960 | 1.000 | 1.000 | 0.927 |
| `fusion-rrf+w=0.5+d=50+c=10` | question | 25 | 0.641 (25) | 0.656 | 1.000 | 0.553 | 0.440 | 0.760 | 0.760 | 0.800 | 0.920 | 0.856 |
| `fusion-rrf+w=0.5+d=50+c=10` | paraphrase | 25 | 0.575 (25) | 0.576 | 1.000 | 0.338 | 0.200 | 0.520 | 0.640 | 0.800 | 0.840 | 0.940 |
| `fusion-rrf+w=0.5+d=50+c=10` | known_item | 25 | 0.685 (25) | 0.604 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.977 |
| `fusion-rrf+w=0.5+d=50+c=100` | keyword | 25 | 0.702 (25) | 0.724 | 1.000 | 0.692 | 0.600 | 0.840 | 0.880 | 1.000 | 1.000 | 0.927 |
| `fusion-rrf+w=0.5+d=50+c=100` | question | 25 | 0.650 (25) | 0.668 | 1.000 | 0.555 | 0.440 | 0.680 | 0.760 | 0.800 | 0.920 | 0.856 |
| `fusion-rrf+w=0.5+d=50+c=100` | paraphrase | 25 | 0.585 (25) | 0.600 | 1.000 | 0.314 | 0.200 | 0.440 | 0.640 | 0.760 | 0.840 | 0.940 |
| `fusion-rrf+w=0.5+d=50+c=100` | known_item | 25 | 0.717 (25) | 0.644 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.977 |
| `fusion-rrf+w=0.5+d=50+c=60` | keyword | 25 | 0.703 (25) | 0.724 | 1.000 | 0.696 | 0.600 | 0.840 | 0.920 | 1.000 | 1.000 | 0.927 |
| `fusion-rrf+w=0.5+d=50+c=60` | question | 25 | 0.654 (25) | 0.672 | 1.000 | 0.548 | 0.440 | 0.680 | 0.760 | 0.800 | 0.920 | 0.856 |
| `fusion-rrf+w=0.5+d=50+c=60` | paraphrase | 25 | 0.585 (25) | 0.600 | 1.000 | 0.314 | 0.200 | 0.440 | 0.640 | 0.760 | 0.840 | 0.940 |
| `fusion-rrf+w=0.5+d=50+c=60` | known_item | 25 | 0.718 (25) | 0.644 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.977 |
| `fusion-rrf+w=0.55+d=100+c=10` | keyword | 25 | 0.681 (25) | 0.688 | 1.000 | 0.680 | 0.520 | 0.880 | 0.960 | 1.000 | 1.000 | 0.941 |
| `fusion-rrf+w=0.55+d=100+c=10` | question | 25 | 0.677 (25) | 0.700 | 1.000 | 0.575 | 0.440 | 0.760 | 0.760 | 0.800 | 0.920 | 0.924 |
| `fusion-rrf+w=0.55+d=100+c=10` | paraphrase | 25 | 0.627 (25) | 0.624 | 1.000 | 0.396 | 0.280 | 0.640 | 0.720 | 0.800 | 0.840 | 0.959 |
| `fusion-rrf+w=0.55+d=100+c=10` | known_item | 25 | 0.682 (25) | 0.596 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `fusion-rrf+w=0.55+d=100+c=100` | keyword | 25 | 0.721 (25) | 0.756 | 1.000 | 0.660 | 0.520 | 0.840 | 0.960 | 0.960 | 1.000 | 0.916 |
| `fusion-rrf+w=0.55+d=100+c=100` | question | 25 | 0.694 (25) | 0.720 | 1.000 | 0.542 | 0.440 | 0.680 | 0.720 | 0.800 | 0.920 | 0.928 |
| `fusion-rrf+w=0.55+d=100+c=100` | paraphrase | 25 | 0.622 (25) | 0.656 | 0.996 | 0.317 | 0.200 | 0.440 | 0.520 | 0.680 | 0.880 | 0.968 |
| `fusion-rrf+w=0.55+d=100+c=100` | known_item | 25 | 0.719 (25) | 0.644 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.946 |
| `fusion-rrf+w=0.55+d=100+c=30` | keyword | 25 | 0.716 (25) | 0.744 | 1.000 | 0.663 | 0.520 | 0.840 | 0.960 | 0.960 | 1.000 | 0.948 |
| `fusion-rrf+w=0.55+d=100+c=30` | question | 25 | 0.697 (25) | 0.740 | 1.000 | 0.558 | 0.440 | 0.720 | 0.760 | 0.800 | 0.920 | 0.933 |
| `fusion-rrf+w=0.55+d=100+c=30` | paraphrase | 25 | 0.649 (25) | 0.648 | 1.000 | 0.382 | 0.280 | 0.480 | 0.720 | 0.800 | 0.840 | 0.959 |
| `fusion-rrf+w=0.55+d=100+c=30` | known_item | 25 | 0.708 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `fusion-rrf+w=0.55+d=100+c=60` | keyword | 25 | 0.716 (25) | 0.748 | 1.000 | 0.660 | 0.520 | 0.840 | 0.960 | 0.960 | 1.000 | 0.932 |
| `fusion-rrf+w=0.55+d=100+c=60` | question | 25 | 0.695 (25) | 0.728 | 1.000 | 0.547 | 0.440 | 0.680 | 0.760 | 0.800 | 0.920 | 0.923 |
| `fusion-rrf+w=0.55+d=100+c=60` | paraphrase | 25 | 0.633 (25) | 0.660 | 1.000 | 0.341 | 0.240 | 0.440 | 0.560 | 0.720 | 0.840 | 0.955 |
| `fusion-rrf+w=0.55+d=100+c=60` | known_item | 25 | 0.717 (25) | 0.644 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.950 |
| `fusion-rrf+w=0.55+d=200+c=30` | keyword | 25 | 0.721 (25) | 0.752 | 1.000 | 0.663 | 0.520 | 0.840 | 0.960 | 0.960 | 1.000 | 0.938 |
| `fusion-rrf+w=0.55+d=200+c=30` | question | 25 | 0.694 (25) | 0.736 | 1.000 | 0.557 | 0.440 | 0.680 | 0.760 | 0.800 | 0.920 | 0.928 |
| `fusion-rrf+w=0.55+d=200+c=30` | paraphrase | 25 | 0.642 (25) | 0.648 | 1.000 | 0.356 | 0.240 | 0.480 | 0.640 | 0.760 | 0.840 | 0.955 |
| `fusion-rrf+w=0.55+d=200+c=30` | known_item | 25 | 0.710 (25) | 0.628 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.977 |
| `fusion-rrf+w=0.55+d=500+c=30` | keyword | 25 | 0.719 (25) | 0.752 | 1.000 | 0.663 | 0.520 | 0.840 | 0.960 | 0.960 | 1.000 | 0.942 |
| `fusion-rrf+w=0.55+d=500+c=30` | question | 25 | 0.691 (25) | 0.736 | 1.000 | 0.557 | 0.440 | 0.680 | 0.760 | 0.800 | 0.920 | 0.933 |
| `fusion-rrf+w=0.55+d=500+c=30` | paraphrase | 25 | 0.641 (25) | 0.648 | 1.000 | 0.361 | 0.240 | 0.520 | 0.640 | 0.760 | 0.840 | 0.963 |
| `fusion-rrf+w=0.55+d=500+c=30` | known_item | 25 | 0.708 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.977 |
| `fusion-rrf+w=0.6+d=100+c=10` | keyword | 25 | 0.678 (25) | 0.696 | 1.000 | 0.675 | 0.520 | 0.880 | 0.960 | 0.960 | 1.000 | 0.942 |
| `fusion-rrf+w=0.6+d=100+c=10` | question | 25 | 0.699 (25) | 0.724 | 1.000 | 0.588 | 0.440 | 0.760 | 0.800 | 0.800 | 0.920 | 0.924 |
| `fusion-rrf+w=0.6+d=100+c=10` | paraphrase | 25 | 0.637 (25) | 0.628 | 1.000 | 0.402 | 0.280 | 0.640 | 0.720 | 0.800 | 0.840 | 0.959 |
| `fusion-rrf+w=0.6+d=100+c=10` | known_item | 25 | 0.679 (25) | 0.596 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.957 |
| `fusion-rrf+w=0.6+d=100+c=100` | keyword | 25 | 0.719 (25) | 0.744 | 1.000 | 0.660 | 0.520 | 0.840 | 0.960 | 0.960 | 0.960 | 0.880 |
| `fusion-rrf+w=0.6+d=100+c=100` | question | 25 | 0.698 (25) | 0.728 | 1.000 | 0.556 | 0.440 | 0.720 | 0.760 | 0.800 | 0.920 | 0.911 |
| `fusion-rrf+w=0.6+d=100+c=100` | paraphrase | 25 | 0.632 (25) | 0.656 | 0.996 | 0.337 | 0.240 | 0.440 | 0.520 | 0.720 | 0.880 | 0.964 |
| `fusion-rrf+w=0.6+d=100+c=100` | known_item | 25 | 0.719 (25) | 0.644 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.937 |
| `fusion-rrf+w=0.6+d=100+c=30` | keyword | 25 | 0.706 (25) | 0.736 | 1.000 | 0.659 | 0.520 | 0.880 | 0.960 | 0.960 | 1.000 | 0.949 |
| `fusion-rrf+w=0.6+d=100+c=30` | question | 25 | 0.702 (25) | 0.744 | 1.000 | 0.563 | 0.440 | 0.760 | 0.760 | 0.800 | 0.920 | 0.927 |
| `fusion-rrf+w=0.6+d=100+c=30` | paraphrase | 25 | 0.655 (25) | 0.656 | 1.000 | 0.369 | 0.240 | 0.520 | 0.720 | 0.800 | 0.840 | 0.955 |
| `fusion-rrf+w=0.6+d=100+c=30` | known_item | 25 | 0.698 (25) | 0.616 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.957 |
| `fusion-rrf+w=0.6+d=100+c=60` | keyword | 25 | 0.723 (25) | 0.752 | 1.000 | 0.661 | 0.520 | 0.840 | 0.960 | 0.960 | 1.000 | 0.906 |
| `fusion-rrf+w=0.6+d=100+c=60` | question | 25 | 0.701 (25) | 0.744 | 1.000 | 0.559 | 0.440 | 0.760 | 0.760 | 0.800 | 0.920 | 0.918 |
| `fusion-rrf+w=0.6+d=100+c=60` | paraphrase | 25 | 0.645 (25) | 0.668 | 1.000 | 0.347 | 0.240 | 0.440 | 0.600 | 0.720 | 0.880 | 0.972 |
| `fusion-rrf+w=0.6+d=100+c=60` | known_item | 25 | 0.713 (25) | 0.636 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.957 |
| `fusion-rrf+w=0.65+d=100+c=10` | keyword | 25 | 0.670 (25) | 0.692 | 1.000 | 0.653 | 0.520 | 0.840 | 0.920 | 0.960 | 1.000 | 0.935 |
| `fusion-rrf+w=0.65+d=100+c=10` | question | 25 | 0.702 (25) | 0.724 | 1.000 | 0.602 | 0.480 | 0.760 | 0.800 | 0.800 | 0.920 | 0.912 |
| `fusion-rrf+w=0.65+d=100+c=10` | paraphrase | 25 | 0.649 (25) | 0.664 | 1.000 | 0.383 | 0.240 | 0.600 | 0.760 | 0.800 | 0.880 | 0.977 |
| `fusion-rrf+w=0.65+d=100+c=10` | known_item | 25 | 0.662 (25) | 0.568 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.957 |
| `fusion-rrf+w=0.65+d=100+c=100` | keyword | 25 | 0.720 (25) | 0.748 | 1.000 | 0.655 | 0.520 | 0.840 | 0.960 | 0.960 | 0.960 | 0.880 |
| `fusion-rrf+w=0.65+d=100+c=100` | question | 25 | 0.695 (25) | 0.732 | 1.000 | 0.556 | 0.440 | 0.720 | 0.760 | 0.800 | 0.920 | 0.911 |
| `fusion-rrf+w=0.65+d=100+c=100` | paraphrase | 25 | 0.628 (25) | 0.644 | 0.992 | 0.318 | 0.200 | 0.440 | 0.560 | 0.720 | 0.880 | 0.964 |
| `fusion-rrf+w=0.65+d=100+c=100` | known_item | 25 | 0.720 (25) | 0.652 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.937 |
| `fusion-rrf+w=0.65+d=100+c=30` | keyword | 25 | 0.704 (25) | 0.740 | 1.000 | 0.658 | 0.520 | 0.880 | 0.920 | 0.960 | 1.000 | 0.920 |
| `fusion-rrf+w=0.65+d=100+c=30` | question | 25 | 0.704 (25) | 0.744 | 1.000 | 0.570 | 0.440 | 0.760 | 0.760 | 0.800 | 0.920 | 0.914 |
| `fusion-rrf+w=0.65+d=100+c=30` | paraphrase | 25 | 0.660 (25) | 0.652 | 1.000 | 0.380 | 0.280 | 0.480 | 0.720 | 0.800 | 0.880 | 0.972 |
| `fusion-rrf+w=0.65+d=100+c=30` | known_item | 25 | 0.688 (25) | 0.604 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.957 |
| `fusion-rrf+w=0.65+d=100+c=60` | keyword | 25 | 0.717 (25) | 0.748 | 1.000 | 0.656 | 0.520 | 0.840 | 0.960 | 0.960 | 0.960 | 0.893 |
| `fusion-rrf+w=0.65+d=100+c=60` | question | 25 | 0.705 (25) | 0.748 | 1.000 | 0.559 | 0.440 | 0.760 | 0.760 | 0.800 | 0.920 | 0.911 |
| `fusion-rrf+w=0.65+d=100+c=60` | paraphrase | 25 | 0.638 (25) | 0.648 | 1.000 | 0.334 | 0.200 | 0.480 | 0.640 | 0.800 | 0.880 | 0.964 |
| `fusion-rrf+w=0.65+d=100+c=60` | known_item | 25 | 0.709 (25) | 0.632 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.943 |
| `fusion-rrf+w=0.7+d=100+c=10` | keyword | 25 | 0.669 (25) | 0.700 | 1.000 | 0.644 | 0.520 | 0.840 | 0.920 | 0.960 | 1.000 | 0.909 |
| `fusion-rrf+w=0.7+d=100+c=10` | question | 25 | 0.697 (25) | 0.716 | 1.000 | 0.602 | 0.480 | 0.760 | 0.800 | 0.840 | 0.920 | 0.909 |
| `fusion-rrf+w=0.7+d=100+c=10` | paraphrase | 25 | 0.645 (25) | 0.652 | 1.000 | 0.393 | 0.240 | 0.560 | 0.720 | 0.800 | 0.880 | 0.977 |
| `fusion-rrf+w=0.7+d=100+c=10` | known_item | 25 | 0.656 (25) | 0.556 | 1.000 | 0.950 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.947 |
| `fusion-rrf+w=0.7+d=100+c=100` | keyword | 25 | 0.720 (25) | 0.756 | 0.996 | 0.646 | 0.520 | 0.800 | 0.960 | 0.960 | 0.960 | 0.880 |
| `fusion-rrf+w=0.7+d=100+c=100` | question | 25 | 0.702 (25) | 0.736 | 1.000 | 0.560 | 0.440 | 0.720 | 0.760 | 0.800 | 0.920 | 0.911 |
| `fusion-rrf+w=0.7+d=100+c=100` | paraphrase | 25 | 0.640 (25) | 0.656 | 0.996 | 0.321 | 0.200 | 0.440 | 0.640 | 0.720 | 0.880 | 0.964 |
| `fusion-rrf+w=0.7+d=100+c=100` | known_item | 25 | 0.713 (25) | 0.636 | 1.000 | 0.947 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.943 |
| `fusion-rrf+w=0.7+d=100+c=30` | keyword | 25 | 0.698 (25) | 0.728 | 1.000 | 0.650 | 0.520 | 0.840 | 0.920 | 0.960 | 0.960 | 0.903 |
| `fusion-rrf+w=0.7+d=100+c=30` | question | 25 | 0.702 (25) | 0.736 | 1.000 | 0.577 | 0.440 | 0.760 | 0.760 | 0.840 | 0.920 | 0.907 |
| `fusion-rrf+w=0.7+d=100+c=30` | paraphrase | 25 | 0.657 (25) | 0.660 | 1.000 | 0.390 | 0.280 | 0.600 | 0.760 | 0.800 | 0.880 | 0.968 |
| `fusion-rrf+w=0.7+d=100+c=30` | known_item | 25 | 0.674 (25) | 0.580 | 1.000 | 0.950 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.943 |
| `fusion-rrf+w=0.7+d=100+c=60` | keyword | 25 | 0.711 (25) | 0.740 | 1.000 | 0.645 | 0.520 | 0.840 | 0.920 | 0.960 | 0.960 | 0.893 |
| `fusion-rrf+w=0.7+d=100+c=60` | question | 25 | 0.708 (25) | 0.748 | 1.000 | 0.567 | 0.440 | 0.760 | 0.760 | 0.800 | 0.920 | 0.911 |
| `fusion-rrf+w=0.7+d=100+c=60` | paraphrase | 25 | 0.647 (25) | 0.644 | 1.000 | 0.348 | 0.240 | 0.440 | 0.680 | 0.800 | 0.880 | 0.964 |
| `fusion-rrf+w=0.7+d=100+c=60` | known_item | 25 | 0.699 (25) | 0.616 | 1.000 | 0.950 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.943 |
| `fusion-rrf+w=0.75+d=100+c=10` | keyword | 25 | 0.665 (25) | 0.700 | 1.000 | 0.644 | 0.520 | 0.800 | 0.920 | 0.960 | 1.000 | 0.906 |
| `fusion-rrf+w=0.75+d=100+c=10` | question | 25 | 0.690 (25) | 0.708 | 1.000 | 0.593 | 0.480 | 0.760 | 0.800 | 0.840 | 0.920 | 0.859 |
| `fusion-rrf+w=0.75+d=100+c=10` | paraphrase | 25 | 0.652 (25) | 0.660 | 1.000 | 0.438 | 0.320 | 0.560 | 0.720 | 0.800 | 0.880 | 0.972 |
| `fusion-rrf+w=0.75+d=100+c=10` | known_item | 25 | 0.643 (25) | 0.536 | 1.000 | 0.940 | 0.920 | 0.960 | 1.000 | 1.000 | 1.000 | 0.947 |
| `fusion-rrf+w=0.75+d=100+c=100` | keyword | 25 | 0.713 (25) | 0.744 | 1.000 | 0.644 | 0.520 | 0.840 | 0.920 | 0.960 | 0.960 | 0.893 |
| `fusion-rrf+w=0.75+d=100+c=100` | question | 25 | 0.705 (25) | 0.748 | 1.000 | 0.565 | 0.440 | 0.760 | 0.760 | 0.800 | 0.920 | 0.911 |
| `fusion-rrf+w=0.75+d=100+c=100` | paraphrase | 25 | 0.641 (25) | 0.648 | 1.000 | 0.321 | 0.200 | 0.480 | 0.680 | 0.800 | 0.880 | 0.964 |
| `fusion-rrf+w=0.75+d=100+c=100` | known_item | 25 | 0.706 (25) | 0.620 | 1.000 | 0.943 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.943 |
| `fusion-rrf+w=0.75+d=100+c=30` | keyword | 25 | 0.692 (25) | 0.720 | 1.000 | 0.643 | 0.520 | 0.880 | 0.920 | 0.960 | 0.960 | 0.890 |
| `fusion-rrf+w=0.75+d=100+c=30` | question | 25 | 0.708 (25) | 0.724 | 1.000 | 0.608 | 0.480 | 0.760 | 0.800 | 0.840 | 0.920 | 0.907 |
| `fusion-rrf+w=0.75+d=100+c=30` | paraphrase | 25 | 0.652 (25) | 0.660 | 1.000 | 0.382 | 0.280 | 0.600 | 0.760 | 0.800 | 0.880 | 0.964 |
| `fusion-rrf+w=0.75+d=100+c=30` | known_item | 25 | 0.668 (25) | 0.568 | 1.000 | 0.943 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.943 |
| `fusion-rrf+w=0.75+d=100+c=60` | keyword | 25 | 0.709 (25) | 0.736 | 1.000 | 0.646 | 0.520 | 0.840 | 0.920 | 0.960 | 0.960 | 0.893 |
| `fusion-rrf+w=0.75+d=100+c=60` | question | 25 | 0.701 (25) | 0.736 | 1.000 | 0.573 | 0.440 | 0.760 | 0.760 | 0.800 | 0.920 | 0.907 |
| `fusion-rrf+w=0.75+d=100+c=60` | paraphrase | 25 | 0.656 (25) | 0.656 | 1.000 | 0.359 | 0.280 | 0.480 | 0.680 | 0.800 | 0.880 | 0.964 |
| `fusion-rrf+w=0.75+d=100+c=60` | known_item | 25 | 0.685 (25) | 0.592 | 1.000 | 0.943 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.943 |
| `fusion-rrf+w=0.75+d=20+c=10` | keyword | 25 | 0.655 (25) | 0.688 | 1.000 | 0.629 | 0.520 | 0.760 | 0.880 | 0.880 | 1.000 | 0.829 |
| `fusion-rrf+w=0.75+d=20+c=10` | question | 25 | 0.687 (25) | 0.704 | 1.000 | 0.599 | 0.480 | 0.760 | 0.800 | 0.840 | 0.840 | 0.758 |
| `fusion-rrf+w=0.75+d=20+c=10` | paraphrase | 25 | 0.650 (25) | 0.648 | 1.000 | 0.458 | 0.360 | 0.560 | 0.720 | 0.800 | 0.840 | 0.887 |
| `fusion-rrf+w=0.75+d=20+c=10` | known_item | 25 | 0.645 (25) | 0.540 | 1.000 | 0.947 | 0.920 | 0.960 | 1.000 | 1.000 | 1.000 | 0.867 |
| `fusion-rrf+w=0.75+d=20+c=100` | keyword | 25 | 0.678 (25) | 0.720 | 1.000 | 0.628 | 0.520 | 0.760 | 0.880 | 0.880 | 1.000 | 0.829 |
| `fusion-rrf+w=0.75+d=20+c=100` | question | 25 | 0.686 (25) | 0.708 | 1.000 | 0.565 | 0.440 | 0.720 | 0.800 | 0.840 | 0.840 | 0.758 |
| `fusion-rrf+w=0.75+d=20+c=100` | paraphrase | 25 | 0.626 (25) | 0.640 | 1.000 | 0.361 | 0.200 | 0.560 | 0.720 | 0.800 | 0.840 | 0.887 |
| `fusion-rrf+w=0.75+d=20+c=100` | known_item | 25 | 0.665 (25) | 0.564 | 1.000 | 0.947 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.867 |
| `fusion-rrf+w=0.75+d=20+c=60` | keyword | 25 | 0.678 (25) | 0.720 | 1.000 | 0.628 | 0.520 | 0.760 | 0.880 | 0.880 | 1.000 | 0.829 |
| `fusion-rrf+w=0.75+d=20+c=60` | question | 25 | 0.686 (25) | 0.708 | 1.000 | 0.565 | 0.440 | 0.720 | 0.800 | 0.840 | 0.840 | 0.758 |
| `fusion-rrf+w=0.75+d=20+c=60` | paraphrase | 25 | 0.626 (25) | 0.640 | 1.000 | 0.361 | 0.200 | 0.560 | 0.720 | 0.800 | 0.840 | 0.887 |
| `fusion-rrf+w=0.75+d=20+c=60` | known_item | 25 | 0.665 (25) | 0.564 | 1.000 | 0.947 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.867 |
| `fusion-rrf+w=0.75+d=50+c=10` | keyword | 25 | 0.665 (25) | 0.700 | 1.000 | 0.637 | 0.520 | 0.800 | 0.920 | 0.920 | 1.000 | 0.909 |
| `fusion-rrf+w=0.75+d=50+c=10` | question | 25 | 0.686 (25) | 0.704 | 1.000 | 0.596 | 0.480 | 0.760 | 0.800 | 0.840 | 0.920 | 0.846 |
| `fusion-rrf+w=0.75+d=50+c=10` | paraphrase | 25 | 0.650 (25) | 0.648 | 1.000 | 0.458 | 0.360 | 0.560 | 0.720 | 0.800 | 0.880 | 0.942 |
| `fusion-rrf+w=0.75+d=50+c=10` | known_item | 25 | 0.645 (25) | 0.540 | 1.000 | 0.940 | 0.920 | 0.960 | 1.000 | 1.000 | 1.000 | 0.903 |
| `fusion-rrf+w=0.75+d=50+c=100` | keyword | 25 | 0.701 (25) | 0.732 | 1.000 | 0.636 | 0.520 | 0.800 | 0.880 | 0.920 | 0.920 | 0.848 |
| `fusion-rrf+w=0.75+d=50+c=100` | question | 25 | 0.690 (25) | 0.740 | 1.000 | 0.569 | 0.440 | 0.760 | 0.800 | 0.840 | 0.920 | 0.840 |
| `fusion-rrf+w=0.75+d=50+c=100` | paraphrase | 25 | 0.628 (25) | 0.644 | 1.000 | 0.317 | 0.200 | 0.480 | 0.680 | 0.800 | 0.880 | 0.929 |
| `fusion-rrf+w=0.75+d=50+c=100` | known_item | 25 | 0.712 (25) | 0.628 | 1.000 | 0.947 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.877 |
| `fusion-rrf+w=0.75+d=50+c=60` | keyword | 25 | 0.706 (25) | 0.736 | 1.000 | 0.640 | 0.520 | 0.800 | 0.920 | 0.920 | 0.920 | 0.848 |
| `fusion-rrf+w=0.75+d=50+c=60` | question | 25 | 0.690 (25) | 0.728 | 1.000 | 0.578 | 0.440 | 0.760 | 0.800 | 0.840 | 0.920 | 0.840 |
| `fusion-rrf+w=0.75+d=50+c=60` | paraphrase | 25 | 0.645 (25) | 0.652 | 1.000 | 0.340 | 0.240 | 0.480 | 0.680 | 0.800 | 0.880 | 0.929 |
| `fusion-rrf+w=0.75+d=50+c=60` | known_item | 25 | 0.682 (25) | 0.588 | 1.000 | 0.947 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.877 |
| `fusion-rrf+w=1+d=100+c=10` | keyword | 25 | 0.626 (25) | 0.676 | 1.000 | 0.577 | 0.480 | 0.800 | 0.800 | 0.880 | 0.920 | 0.848 |
| `fusion-rrf+w=1+d=100+c=10` | question | 25 | 0.669 (25) | 0.704 | 1.000 | 0.560 | 0.440 | 0.720 | 0.800 | 0.840 | 0.920 | 0.840 |
| `fusion-rrf+w=1+d=100+c=10` | paraphrase | 25 | 0.632 (25) | 0.652 | 1.000 | 0.466 | 0.400 | 0.520 | 0.720 | 0.800 | 0.880 | 0.929 |
| `fusion-rrf+w=1+d=100+c=10` | known_item | 25 | 0.595 (25) | 0.516 | 1.000 | 0.793 | 0.680 | 0.920 | 0.960 | 1.000 | 1.000 | 0.877 |
| `fusion-shortlist+a=0.5+d=100` | keyword | 25 | 0.714 (25) | 0.744 | 1.000 | 0.674 | 0.520 | 0.880 | 0.960 | 0.960 | 1.000 | 0.948 |
| `fusion-shortlist+a=0.5+d=100` | question | 25 | 0.699 (25) | 0.740 | 1.000 | 0.565 | 0.440 | 0.760 | 0.760 | 0.800 | 0.920 | 0.933 |
| `fusion-shortlist+a=0.5+d=100` | paraphrase | 25 | 0.650 (25) | 0.648 | 1.000 | 0.380 | 0.280 | 0.440 | 0.720 | 0.800 | 0.840 | 0.959 |
| `fusion-shortlist+a=0.5+d=100` | known_item | 25 | 0.710 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `fusion-shortlist+a=0.5+d=500` | keyword | 25 | 0.713 (25) | 0.744 | 1.000 | 0.674 | 0.520 | 0.880 | 0.960 | 0.960 | 1.000 | 0.948 |
| `fusion-shortlist+a=0.5+d=500` | question | 25 | 0.696 (25) | 0.740 | 1.000 | 0.562 | 0.440 | 0.720 | 0.760 | 0.800 | 0.920 | 0.933 |
| `fusion-shortlist+a=0.5+d=500` | paraphrase | 25 | 0.653 (25) | 0.648 | 1.000 | 0.391 | 0.280 | 0.480 | 0.720 | 0.800 | 0.840 | 0.959 |
| `fusion-shortlist+a=0.5+d=500` | known_item | 25 | 0.710 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `fusion-shortlist+a=1+d=100` | keyword | 25 | 0.723 (25) | 0.744 | 1.000 | 0.720 | 0.600 | 0.880 | 0.960 | 0.960 | 1.000 | 0.948 |
| `fusion-shortlist+a=1+d=100` | question | 25 | 0.711 (25) | 0.740 | 1.000 | 0.591 | 0.480 | 0.760 | 0.760 | 0.800 | 0.920 | 0.933 |
| `fusion-shortlist+a=1+d=100` | paraphrase | 25 | 0.653 (25) | 0.648 | 1.000 | 0.403 | 0.320 | 0.440 | 0.720 | 0.800 | 0.840 | 0.959 |
| `fusion-shortlist+a=1+d=100` | known_item | 25 | 0.713 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `fusion-shortlist+a=1+d=500` | keyword | 25 | 0.721 (25) | 0.744 | 1.000 | 0.720 | 0.600 | 0.880 | 0.960 | 0.960 | 1.000 | 0.948 |
| `fusion-shortlist+a=1+d=500` | question | 25 | 0.708 (25) | 0.740 | 1.000 | 0.588 | 0.480 | 0.720 | 0.760 | 0.800 | 0.920 | 0.933 |
| `fusion-shortlist+a=1+d=500` | paraphrase | 25 | 0.672 (25) | 0.648 | 1.000 | 0.498 | 0.400 | 0.600 | 0.720 | 0.800 | 0.840 | 0.959 |
| `fusion-shortlist+a=1+d=500` | known_item | 25 | 0.713 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `fusion-top1bonus+b=0.1+w=0.55+d=100+c=30` | keyword | 25 | 0.712 (25) | 0.744 | 1.000 | 0.686 | 0.560 | 0.880 | 0.960 | 0.960 | 1.000 | 0.948 |
| `fusion-top1bonus+b=0.1+w=0.55+d=100+c=30` | question | 25 | 0.703 (25) | 0.748 | 1.000 | 0.563 | 0.440 | 0.760 | 0.760 | 0.800 | 0.920 | 0.933 |
| `fusion-top1bonus+b=0.1+w=0.55+d=100+c=30` | paraphrase | 25 | 0.642 (25) | 0.640 | 1.000 | 0.383 | 0.280 | 0.520 | 0.680 | 0.800 | 0.840 | 0.959 |
| `fusion-top1bonus+b=0.1+w=0.55+d=100+c=30` | known_item | 25 | 0.708 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `fusion-top1bonus+b=0.25+w=0.55+d=100+c=30` | keyword | 25 | 0.709 (25) | 0.740 | 1.000 | 0.707 | 0.600 | 0.920 | 0.960 | 0.960 | 1.000 | 0.948 |
| `fusion-top1bonus+b=0.25+w=0.55+d=100+c=30` | question | 25 | 0.706 (25) | 0.748 | 1.000 | 0.541 | 0.400 | 0.720 | 0.760 | 0.800 | 0.920 | 0.933 |
| `fusion-top1bonus+b=0.25+w=0.55+d=100+c=30` | paraphrase | 25 | 0.631 (25) | 0.636 | 1.000 | 0.382 | 0.280 | 0.520 | 0.680 | 0.800 | 0.840 | 0.959 |
| `fusion-top1bonus+b=0.25+w=0.55+d=100+c=30` | known_item | 25 | 0.708 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `hybrid-bge-small+linear+w=0.25` | keyword | 25 | 0.677 (25) | 0.688 | 0.960 | 0.700 | 0.520 | 0.880 | 0.920 | 0.920 | 1.000 | 0.812 |
| `hybrid-bge-small+linear+w=0.25` | question | 25 | 0.545 (25) | 0.528 | 0.952 | 0.521 | 0.440 | 0.640 | 0.680 | 0.720 | 0.720 | 0.589 |
| `hybrid-bge-small+linear+w=0.25` | paraphrase | 25 | 0.457 (25) | 0.504 | 0.956 | 0.178 | 0.080 | 0.320 | 0.360 | 0.360 | 0.440 | 0.530 |
| `hybrid-bge-small+linear+w=0.25` | known_item | 25 | 0.702 (25) | 0.616 | 0.960 | 0.948 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.933 |
| `hybrid-bge-small+linear+w=0.5` | keyword | 25 | 0.673 (25) | 0.680 | 0.900 | 0.653 | 0.480 | 0.880 | 0.880 | 0.960 | 1.000 | 0.854 |
| `hybrid-bge-small+linear+w=0.5` | question | 25 | 0.596 (25) | 0.596 | 0.884 | 0.519 | 0.440 | 0.600 | 0.720 | 0.760 | 0.800 | 0.725 |
| `hybrid-bge-small+linear+w=0.5` | paraphrase | 25 | 0.498 (25) | 0.536 | 0.880 | 0.211 | 0.120 | 0.320 | 0.560 | 0.600 | 0.800 | 0.740 |
| `hybrid-bge-small+linear+w=0.5` | known_item | 25 | 0.705 (25) | 0.620 | 0.920 | 0.891 | 0.840 | 0.960 | 1.000 | 1.000 | 1.000 | 0.903 |
| `hybrid-bge-small+linear+w=0.75` | keyword | 25 | 0.657 (25) | 0.660 | 0.928 | 0.667 | 0.560 | 0.840 | 0.920 | 0.960 | 0.960 | 0.753 |
| `hybrid-bge-small+linear+w=0.75` | question | 25 | 0.625 (25) | 0.652 | 0.956 | 0.495 | 0.400 | 0.640 | 0.680 | 0.760 | 0.880 | 0.689 |
| `hybrid-bge-small+linear+w=0.75` | paraphrase | 25 | 0.487 (25) | 0.532 | 0.936 | 0.217 | 0.120 | 0.360 | 0.400 | 0.640 | 0.840 | 0.646 |
| `hybrid-bge-small+linear+w=0.75` | known_item | 25 | 0.707 (25) | 0.628 | 0.960 | 0.856 | 0.800 | 0.920 | 0.960 | 0.960 | 0.960 | 0.815 |
| `hybrid-bge-small+rrf+w=0.25+c=10` | keyword | 25 | 0.645 (25) | 0.648 | 0.996 | 0.727 | 0.560 | 0.920 | 0.920 | 0.960 | 1.000 | 0.852 |
| `hybrid-bge-small+rrf+w=0.25+c=10` | question | 25 | 0.487 (25) | 0.484 | 1.000 | 0.485 | 0.400 | 0.560 | 0.680 | 0.720 | 0.760 | 0.688 |
| `hybrid-bge-small+rrf+w=0.25+c=10` | paraphrase | 25 | 0.376 (25) | 0.448 | 1.000 | 0.152 | 0.080 | 0.240 | 0.320 | 0.360 | 0.720 | 0.750 |
| `hybrid-bge-small+rrf+w=0.25+c=10` | known_item | 25 | 0.677 (25) | 0.600 | 0.988 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.933 |
| `hybrid-bge-small+rrf+w=0.25+c=100` | keyword | 25 | 0.664 (25) | 0.660 | 0.920 | 0.700 | 0.520 | 0.880 | 0.920 | 0.920 | 1.000 | 0.834 |
| `hybrid-bge-small+rrf+w=0.25+c=100` | question | 25 | 0.571 (25) | 0.568 | 0.920 | 0.522 | 0.440 | 0.640 | 0.680 | 0.720 | 0.720 | 0.642 |
| `hybrid-bge-small+rrf+w=0.25+c=100` | paraphrase | 25 | 0.478 (25) | 0.520 | 0.900 | 0.180 | 0.080 | 0.320 | 0.400 | 0.440 | 0.440 | 0.574 |
| `hybrid-bge-small+rrf+w=0.25+c=100` | known_item | 25 | 0.702 (25) | 0.620 | 0.944 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.916 |
| `hybrid-bge-small+rrf+w=0.25+c=60` | keyword | 25 | 0.664 (25) | 0.668 | 0.964 | 0.703 | 0.520 | 0.920 | 0.920 | 0.920 | 1.000 | 0.838 |
| `hybrid-bge-small+rrf+w=0.25+c=60` | question | 25 | 0.553 (25) | 0.540 | 0.948 | 0.520 | 0.440 | 0.640 | 0.680 | 0.720 | 0.720 | 0.613 |
| `hybrid-bge-small+rrf+w=0.25+c=60` | paraphrase | 25 | 0.454 (25) | 0.516 | 0.952 | 0.157 | 0.040 | 0.320 | 0.360 | 0.400 | 0.440 | 0.574 |
| `hybrid-bge-small+rrf+w=0.25+c=60` | known_item | 25 | 0.701 (25) | 0.624 | 0.972 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.916 |
| `hybrid-bge-small+rrf+w=0.5+c=10` | keyword | 25 | 0.679 (25) | 0.692 | 1.000 | 0.709 | 0.560 | 0.960 | 0.960 | 0.960 | 1.000 | 0.854 |
| `hybrid-bge-small+rrf+w=0.5+c=10` | question | 25 | 0.604 (25) | 0.616 | 1.000 | 0.536 | 0.440 | 0.680 | 0.720 | 0.760 | 0.800 | 0.718 |
| `hybrid-bge-small+rrf+w=0.5+c=10` | paraphrase | 25 | 0.471 (25) | 0.528 | 1.000 | 0.232 | 0.120 | 0.440 | 0.480 | 0.680 | 0.800 | 0.744 |
| `hybrid-bge-small+rrf+w=0.5+c=10` | known_item | 25 | 0.709 (25) | 0.620 | 1.000 | 0.930 | 0.880 | 1.000 | 1.000 | 1.000 | 1.000 | 0.903 |
| `hybrid-bge-small+rrf+w=0.5+c=100` | keyword | 25 | 0.676 (25) | 0.676 | 0.884 | 0.673 | 0.520 | 0.880 | 0.880 | 0.960 | 1.000 | 0.840 |
| `hybrid-bge-small+rrf+w=0.5+c=100` | question | 25 | 0.590 (25) | 0.584 | 0.860 | 0.514 | 0.440 | 0.640 | 0.680 | 0.760 | 0.800 | 0.747 |
| `hybrid-bge-small+rrf+w=0.5+c=100` | paraphrase | 25 | 0.500 (25) | 0.528 | 0.828 | 0.233 | 0.160 | 0.400 | 0.520 | 0.560 | 0.760 | 0.771 |
| `hybrid-bge-small+rrf+w=0.5+c=100` | known_item | 25 | 0.705 (25) | 0.620 | 0.892 | 0.891 | 0.840 | 0.960 | 1.000 | 1.000 | 1.000 | 0.896 |
| `hybrid-bge-small+rrf+w=0.5+c=60` | keyword | 25 | 0.682 (25) | 0.684 | 0.908 | 0.673 | 0.520 | 0.880 | 0.880 | 0.960 | 1.000 | 0.840 |
| `hybrid-bge-small+rrf+w=0.5+c=60` | question | 25 | 0.599 (25) | 0.604 | 0.880 | 0.516 | 0.440 | 0.640 | 0.680 | 0.760 | 0.800 | 0.747 |
| `hybrid-bge-small+rrf+w=0.5+c=60` | paraphrase | 25 | 0.499 (25) | 0.524 | 0.852 | 0.240 | 0.160 | 0.360 | 0.560 | 0.560 | 0.760 | 0.771 |
| `hybrid-bge-small+rrf+w=0.5+c=60` | known_item | 25 | 0.703 (25) | 0.612 | 0.892 | 0.892 | 0.840 | 0.960 | 1.000 | 1.000 | 1.000 | 0.896 |
| `hybrid-bge-small+rrf+w=0.75+c=10` | keyword | 25 | 0.640 (25) | 0.672 | 1.000 | 0.656 | 0.560 | 0.760 | 0.880 | 0.960 | 1.000 | 0.792 |
| `hybrid-bge-small+rrf+w=0.75+c=10` | question | 25 | 0.609 (25) | 0.648 | 0.992 | 0.475 | 0.400 | 0.600 | 0.680 | 0.760 | 0.880 | 0.703 |
| `hybrid-bge-small+rrf+w=0.75+c=10` | paraphrase | 25 | 0.478 (25) | 0.532 | 0.996 | 0.281 | 0.200 | 0.360 | 0.520 | 0.640 | 0.880 | 0.685 |
| `hybrid-bge-small+rrf+w=0.75+c=10` | known_item | 25 | 0.673 (25) | 0.612 | 1.000 | 0.797 | 0.720 | 0.880 | 0.960 | 1.000 | 1.000 | 0.840 |
| `hybrid-bge-small+rrf+w=0.75+c=100` | keyword | 25 | 0.657 (25) | 0.664 | 0.884 | 0.666 | 0.560 | 0.880 | 0.920 | 0.960 | 1.000 | 0.776 |
| `hybrid-bge-small+rrf+w=0.75+c=100` | question | 25 | 0.608 (25) | 0.620 | 0.888 | 0.491 | 0.400 | 0.600 | 0.720 | 0.760 | 0.880 | 0.737 |
| `hybrid-bge-small+rrf+w=0.75+c=100` | paraphrase | 25 | 0.500 (25) | 0.552 | 0.900 | 0.239 | 0.160 | 0.360 | 0.440 | 0.680 | 0.840 | 0.703 |
| `hybrid-bge-small+rrf+w=0.75+c=100` | known_item | 25 | 0.703 (25) | 0.612 | 0.936 | 0.856 | 0.800 | 0.920 | 0.960 | 1.000 | 1.000 | 0.819 |
| `hybrid-bge-small+rrf+w=0.75+c=60` | keyword | 25 | 0.657 (25) | 0.668 | 0.940 | 0.665 | 0.560 | 0.880 | 0.920 | 0.960 | 1.000 | 0.784 |
| `hybrid-bge-small+rrf+w=0.75+c=60` | question | 25 | 0.624 (25) | 0.652 | 0.952 | 0.482 | 0.400 | 0.640 | 0.680 | 0.800 | 0.880 | 0.721 |
| `hybrid-bge-small+rrf+w=0.75+c=60` | paraphrase | 25 | 0.483 (25) | 0.536 | 0.928 | 0.242 | 0.160 | 0.360 | 0.440 | 0.640 | 0.840 | 0.690 |
| `hybrid-bge-small+rrf+w=0.75+c=60` | known_item | 25 | 0.703 (25) | 0.620 | 0.968 | 0.856 | 0.800 | 0.920 | 0.960 | 0.960 | 1.000 | 0.819 |
| `hybrid-gte-small+linear+w=0.25` | keyword | 25 | 0.649 (25) | 0.640 | 0.948 | 0.677 | 0.520 | 0.920 | 0.920 | 0.920 | 1.000 | 0.806 |
| `hybrid-gte-small+linear+w=0.25` | question | 25 | 0.558 (25) | 0.560 | 0.968 | 0.522 | 0.440 | 0.640 | 0.680 | 0.720 | 0.720 | 0.584 |
| `hybrid-gte-small+linear+w=0.25` | paraphrase | 25 | 0.458 (25) | 0.516 | 0.964 | 0.172 | 0.040 | 0.320 | 0.360 | 0.400 | 0.440 | 0.530 |
| `hybrid-gte-small+linear+w=0.25` | known_item | 25 | 0.717 (25) | 0.636 | 0.960 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.933 |
| `hybrid-gte-small+linear+w=0.5` | keyword | 25 | 0.669 (25) | 0.648 | 0.868 | 0.707 | 0.600 | 0.800 | 0.840 | 0.960 | 1.000 | 0.836 |
| `hybrid-gte-small+linear+w=0.5` | question | 25 | 0.595 (25) | 0.612 | 0.892 | 0.531 | 0.440 | 0.640 | 0.680 | 0.760 | 0.800 | 0.739 |
| `hybrid-gte-small+linear+w=0.5` | paraphrase | 25 | 0.514 (25) | 0.560 | 0.896 | 0.255 | 0.120 | 0.440 | 0.520 | 0.520 | 0.720 | 0.770 |
| `hybrid-gte-small+linear+w=0.5` | known_item | 25 | 0.703 (25) | 0.608 | 0.900 | 0.920 | 0.880 | 1.000 | 1.000 | 1.000 | 1.000 | 0.927 |
| `hybrid-gte-small+linear+w=0.75` | keyword | 25 | 0.678 (25) | 0.672 | 0.928 | 0.712 | 0.640 | 0.800 | 0.880 | 0.880 | 0.960 | 0.776 |
| `hybrid-gte-small+linear+w=0.75` | question | 25 | 0.617 (25) | 0.660 | 0.964 | 0.469 | 0.320 | 0.640 | 0.720 | 0.800 | 0.880 | 0.684 |
| `hybrid-gte-small+linear+w=0.75` | paraphrase | 25 | 0.533 (25) | 0.568 | 0.952 | 0.298 | 0.160 | 0.480 | 0.480 | 0.640 | 0.720 | 0.677 |
| `hybrid-gte-small+linear+w=0.75` | known_item | 25 | 0.680 (25) | 0.600 | 0.960 | 0.801 | 0.720 | 0.920 | 0.960 | 1.000 | 1.000 | 0.809 |
| `hybrid-gte-small+rrf+w=0.25+c=10` | keyword | 25 | 0.639 (25) | 0.640 | 1.000 | 0.707 | 0.560 | 0.880 | 0.920 | 0.960 | 1.000 | 0.864 |
| `hybrid-gte-small+rrf+w=0.25+c=10` | question | 25 | 0.483 (25) | 0.480 | 1.000 | 0.479 | 0.400 | 0.560 | 0.680 | 0.720 | 0.760 | 0.653 |
| `hybrid-gte-small+rrf+w=0.25+c=10` | paraphrase | 25 | 0.381 (25) | 0.448 | 1.000 | 0.151 | 0.080 | 0.240 | 0.280 | 0.400 | 0.600 | 0.740 |
| `hybrid-gte-small+rrf+w=0.25+c=10` | known_item | 25 | 0.691 (25) | 0.620 | 0.996 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.926 |
| `hybrid-gte-small+rrf+w=0.25+c=100` | keyword | 25 | 0.655 (25) | 0.644 | 0.912 | 0.672 | 0.520 | 0.880 | 0.920 | 0.920 | 1.000 | 0.839 |
| `hybrid-gte-small+rrf+w=0.25+c=100` | question | 25 | 0.566 (25) | 0.576 | 0.928 | 0.519 | 0.440 | 0.640 | 0.680 | 0.720 | 0.720 | 0.627 |
| `hybrid-gte-small+rrf+w=0.25+c=100` | paraphrase | 25 | 0.487 (25) | 0.536 | 0.908 | 0.191 | 0.080 | 0.320 | 0.360 | 0.440 | 0.440 | 0.544 |
| `hybrid-gte-small+rrf+w=0.25+c=100` | known_item | 25 | 0.714 (25) | 0.628 | 0.944 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.936 |
| `hybrid-gte-small+rrf+w=0.25+c=60` | keyword | 25 | 0.656 (25) | 0.660 | 0.964 | 0.677 | 0.520 | 0.920 | 0.920 | 0.920 | 1.000 | 0.836 |
| `hybrid-gte-small+rrf+w=0.25+c=60` | question | 25 | 0.550 (25) | 0.552 | 0.952 | 0.519 | 0.440 | 0.640 | 0.680 | 0.720 | 0.720 | 0.626 |
| `hybrid-gte-small+rrf+w=0.25+c=60` | paraphrase | 25 | 0.463 (25) | 0.516 | 0.956 | 0.175 | 0.080 | 0.320 | 0.320 | 0.400 | 0.440 | 0.549 |
| `hybrid-gte-small+rrf+w=0.25+c=60` | known_item | 25 | 0.714 (25) | 0.628 | 0.968 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.936 |
| `hybrid-gte-small+rrf+w=0.5+c=10` | keyword | 25 | 0.691 (25) | 0.688 | 1.000 | 0.728 | 0.600 | 0.920 | 0.960 | 0.960 | 1.000 | 0.847 |
| `hybrid-gte-small+rrf+w=0.5+c=10` | question | 25 | 0.585 (25) | 0.596 | 1.000 | 0.518 | 0.400 | 0.640 | 0.720 | 0.760 | 0.800 | 0.733 |
| `hybrid-gte-small+rrf+w=0.5+c=10` | paraphrase | 25 | 0.505 (25) | 0.556 | 1.000 | 0.321 | 0.200 | 0.480 | 0.520 | 0.640 | 0.720 | 0.770 |
| `hybrid-gte-small+rrf+w=0.5+c=10` | known_item | 25 | 0.695 (25) | 0.604 | 1.000 | 0.973 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.927 |
| `hybrid-gte-small+rrf+w=0.5+c=100` | keyword | 25 | 0.666 (25) | 0.628 | 0.848 | 0.701 | 0.600 | 0.800 | 0.880 | 0.960 | 1.000 | 0.834 |
| `hybrid-gte-small+rrf+w=0.5+c=100` | question | 25 | 0.593 (25) | 0.596 | 0.860 | 0.507 | 0.400 | 0.640 | 0.680 | 0.760 | 0.800 | 0.734 |
| `hybrid-gte-small+rrf+w=0.5+c=100` | paraphrase | 25 | 0.509 (25) | 0.540 | 0.844 | 0.276 | 0.160 | 0.440 | 0.520 | 0.520 | 0.720 | 0.765 |
| `hybrid-gte-small+rrf+w=0.5+c=100` | known_item | 25 | 0.707 (25) | 0.620 | 0.888 | 0.920 | 0.880 | 1.000 | 1.000 | 1.000 | 1.000 | 0.930 |
| `hybrid-gte-small+rrf+w=0.5+c=60` | keyword | 25 | 0.669 (25) | 0.636 | 0.876 | 0.702 | 0.600 | 0.800 | 0.880 | 0.960 | 1.000 | 0.834 |
| `hybrid-gte-small+rrf+w=0.5+c=60` | question | 25 | 0.597 (25) | 0.608 | 0.876 | 0.507 | 0.400 | 0.640 | 0.680 | 0.760 | 0.800 | 0.734 |
| `hybrid-gte-small+rrf+w=0.5+c=60` | paraphrase | 25 | 0.515 (25) | 0.544 | 0.860 | 0.282 | 0.160 | 0.400 | 0.520 | 0.520 | 0.720 | 0.765 |
| `hybrid-gte-small+rrf+w=0.5+c=60` | known_item | 25 | 0.706 (25) | 0.616 | 0.904 | 0.920 | 0.880 | 1.000 | 1.000 | 1.000 | 1.000 | 0.930 |
| `hybrid-gte-small+rrf+w=0.75+c=10` | keyword | 25 | 0.658 (25) | 0.656 | 0.996 | 0.703 | 0.600 | 0.840 | 0.840 | 0.920 | 1.000 | 0.818 |
| `hybrid-gte-small+rrf+w=0.75+c=10` | question | 25 | 0.606 (25) | 0.656 | 1.000 | 0.469 | 0.360 | 0.640 | 0.720 | 0.800 | 0.880 | 0.693 |
| `hybrid-gte-small+rrf+w=0.75+c=10` | paraphrase | 25 | 0.517 (25) | 0.552 | 0.992 | 0.366 | 0.280 | 0.480 | 0.520 | 0.680 | 0.760 | 0.700 |
| `hybrid-gte-small+rrf+w=0.75+c=10` | known_item | 25 | 0.634 (25) | 0.564 | 1.000 | 0.766 | 0.680 | 0.880 | 0.960 | 1.000 | 1.000 | 0.853 |
| `hybrid-gte-small+rrf+w=0.75+c=100` | keyword | 25 | 0.679 (25) | 0.668 | 0.896 | 0.714 | 0.640 | 0.800 | 0.880 | 0.920 | 0.960 | 0.789 |
| `hybrid-gte-small+rrf+w=0.75+c=100` | question | 25 | 0.618 (25) | 0.652 | 0.936 | 0.468 | 0.320 | 0.640 | 0.720 | 0.800 | 0.880 | 0.743 |
| `hybrid-gte-small+rrf+w=0.75+c=100` | paraphrase | 25 | 0.534 (25) | 0.560 | 0.896 | 0.323 | 0.240 | 0.400 | 0.480 | 0.600 | 0.760 | 0.724 |
| `hybrid-gte-small+rrf+w=0.75+c=100` | known_item | 25 | 0.687 (25) | 0.612 | 0.928 | 0.805 | 0.720 | 0.920 | 1.000 | 1.000 | 1.000 | 0.856 |
| `hybrid-gte-small+rrf+w=0.75+c=60` | keyword | 25 | 0.676 (25) | 0.668 | 0.928 | 0.716 | 0.640 | 0.840 | 0.880 | 0.920 | 0.960 | 0.789 |
| `hybrid-gte-small+rrf+w=0.75+c=60` | question | 25 | 0.627 (25) | 0.664 | 0.968 | 0.489 | 0.360 | 0.640 | 0.720 | 0.800 | 0.880 | 0.743 |
| `hybrid-gte-small+rrf+w=0.75+c=60` | paraphrase | 25 | 0.546 (25) | 0.580 | 0.944 | 0.333 | 0.240 | 0.480 | 0.480 | 0.640 | 0.760 | 0.720 |
| `hybrid-gte-small+rrf+w=0.75+c=60` | known_item | 25 | 0.684 (25) | 0.608 | 0.968 | 0.806 | 0.720 | 0.920 | 1.000 | 1.000 | 1.000 | 0.856 |
| `hybrid-openai-large+rrf+w=0.5+c=10` | keyword | 25 | 0.680 (25) | 0.692 | 1.000 | 0.717 | 0.600 | 0.920 | 0.960 | 1.000 | 1.000 | 0.934 |
| `hybrid-openai-large+rrf+w=0.5+c=10` | question | 25 | 0.644 (25) | 0.660 | 1.000 | 0.553 | 0.440 | 0.760 | 0.760 | 0.800 | 0.920 | 0.901 |
| `hybrid-openai-large+rrf+w=0.5+c=10` | paraphrase | 25 | 0.580 (25) | 0.576 | 1.000 | 0.364 | 0.240 | 0.520 | 0.640 | 0.800 | 0.840 | 0.959 |
| `hybrid-openai-large+rrf+w=0.5+c=10` | known_item | 25 | 0.687 (25) | 0.604 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.987 |
| `oai-field+text=concat+d=10` | keyword | 25 | 0.699 (25) | 0.744 | 1.000 | 0.606 | 0.480 | 0.800 | 0.960 | 0.960 | 1.000 | 0.948 |
| `oai-field+text=concat+d=10` | question | 25 | 0.691 (25) | 0.740 | 1.000 | 0.558 | 0.440 | 0.720 | 0.760 | 0.800 | 0.920 | 0.933 |
| `oai-field+text=concat+d=10` | paraphrase | 25 | 0.645 (25) | 0.648 | 1.000 | 0.469 | 0.400 | 0.560 | 0.720 | 0.800 | 0.840 | 0.959 |
| `oai-field+text=concat+d=10` | known_item | 25 | 0.672 (25) | 0.624 | 1.000 | 0.802 | 0.680 | 0.920 | 1.000 | 1.000 | 1.000 | 0.967 |
| `oai-field+text=concat+d=100` | keyword | 25 | 0.626 (25) | 0.676 | 1.000 | 0.577 | 0.480 | 0.800 | 0.800 | 0.880 | 0.920 | 0.848 |
| `oai-field+text=concat+d=100` | question | 25 | 0.669 (25) | 0.704 | 1.000 | 0.560 | 0.440 | 0.720 | 0.800 | 0.840 | 0.920 | 0.840 |
| `oai-field+text=concat+d=100` | paraphrase | 25 | 0.632 (25) | 0.652 | 1.000 | 0.466 | 0.400 | 0.520 | 0.720 | 0.800 | 0.880 | 0.929 |
| `oai-field+text=concat+d=100` | known_item | 25 | 0.595 (25) | 0.516 | 1.000 | 0.793 | 0.680 | 0.920 | 0.960 | 1.000 | 1.000 | 0.877 |
| `oai-field+text=title25+d=10` | keyword | 25 | 0.701 (25) | 0.744 | 1.000 | 0.604 | 0.440 | 0.760 | 0.960 | 0.960 | 1.000 | 0.948 |
| `oai-field+text=title25+d=10` | question | 25 | 0.693 (25) | 0.740 | 1.000 | 0.607 | 0.480 | 0.720 | 0.760 | 0.800 | 0.920 | 0.933 |
| `oai-field+text=title25+d=10` | paraphrase | 25 | 0.659 (25) | 0.648 | 1.000 | 0.438 | 0.360 | 0.520 | 0.720 | 0.800 | 0.840 | 0.959 |
| `oai-field+text=title25+d=10` | known_item | 25 | 0.695 (25) | 0.624 | 1.000 | 0.873 | 0.800 | 0.960 | 1.000 | 1.000 | 1.000 | 0.967 |
| `oai-field+text=title25+d=100` | keyword | 25 | 0.617 (25) | 0.608 | 0.880 | 0.568 | 0.440 | 0.720 | 0.800 | 0.920 | 0.920 | 0.823 |
| `oai-field+text=title25+d=100` | question | 25 | 0.670 (25) | 0.684 | 0.904 | 0.612 | 0.480 | 0.760 | 0.800 | 0.880 | 0.920 | 0.843 |
| `oai-field+text=title25+d=100` | paraphrase | 25 | 0.605 (25) | 0.576 | 0.872 | 0.427 | 0.360 | 0.520 | 0.640 | 0.760 | 0.840 | 0.906 |
| `oai-field+text=title25+d=100` | known_item | 25 | 0.600 (25) | 0.492 | 0.832 | 0.866 | 0.800 | 0.960 | 1.000 | 1.000 | 1.000 | 0.910 |
| `oai-field+text=title50+d=10` | keyword | 25 | 0.701 (25) | 0.744 | 1.000 | 0.611 | 0.480 | 0.760 | 0.960 | 0.960 | 1.000 | 0.948 |
| `oai-field+text=title50+d=10` | question | 25 | 0.682 (25) | 0.740 | 1.000 | 0.537 | 0.360 | 0.760 | 0.760 | 0.800 | 0.920 | 0.933 |
| `oai-field+text=title50+d=10` | paraphrase | 25 | 0.637 (25) | 0.648 | 1.000 | 0.438 | 0.360 | 0.520 | 0.720 | 0.800 | 0.840 | 0.959 |
| `oai-field+text=title50+d=10` | known_item | 25 | 0.686 (25) | 0.624 | 1.000 | 0.830 | 0.720 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `oai-field+text=title50+d=100` | keyword | 25 | 0.596 (25) | 0.580 | 0.800 | 0.589 | 0.480 | 0.760 | 0.800 | 0.800 | 0.920 | 0.807 |
| `oai-field+text=title50+d=100` | question | 25 | 0.627 (25) | 0.644 | 0.836 | 0.554 | 0.360 | 0.800 | 0.840 | 0.880 | 0.920 | 0.823 |
| `oai-field+text=title50+d=100` | paraphrase | 25 | 0.572 (25) | 0.568 | 0.848 | 0.432 | 0.360 | 0.560 | 0.600 | 0.680 | 0.800 | 0.876 |
| `oai-field+text=title50+d=100` | known_item | 25 | 0.591 (25) | 0.476 | 0.792 | 0.821 | 0.720 | 1.000 | 1.000 | 1.000 | 1.000 | 0.913 |
| `oai-field+text=title75+d=10` | keyword | 25 | 0.705 (25) | 0.744 | 1.000 | 0.597 | 0.480 | 0.720 | 0.960 | 0.960 | 1.000 | 0.948 |
| `oai-field+text=title75+d=10` | question | 25 | 0.668 (25) | 0.740 | 1.000 | 0.455 | 0.280 | 0.760 | 0.760 | 0.800 | 0.920 | 0.933 |
| `oai-field+text=title75+d=10` | paraphrase | 25 | 0.620 (25) | 0.648 | 1.000 | 0.438 | 0.360 | 0.520 | 0.720 | 0.800 | 0.840 | 0.959 |
| `oai-field+text=title75+d=10` | known_item | 25 | 0.677 (25) | 0.624 | 1.000 | 0.798 | 0.640 | 0.960 | 1.000 | 1.000 | 1.000 | 0.967 |
| `oai-field+text=title75+d=100` | keyword | 25 | 0.552 (25) | 0.544 | 0.736 | 0.520 | 0.440 | 0.680 | 0.720 | 0.720 | 0.840 | 0.754 |
| `oai-field+text=title75+d=100` | question | 25 | 0.554 (25) | 0.572 | 0.764 | 0.463 | 0.320 | 0.600 | 0.880 | 0.880 | 0.920 | 0.836 |
| `oai-field+text=title75+d=100` | paraphrase | 25 | 0.497 (25) | 0.484 | 0.748 | 0.414 | 0.360 | 0.520 | 0.600 | 0.640 | 0.760 | 0.819 |
| `oai-field+text=title75+d=100` | known_item | 25 | 0.570 (25) | 0.464 | 0.748 | 0.765 | 0.640 | 0.960 | 0.960 | 0.960 | 1.000 | 0.890 |
| `oai-field-hybrid+text=concat+d=10` | keyword | 25 | 0.721 (25) | 0.744 | 1.000 | 0.720 | 0.600 | 0.880 | 0.960 | 0.960 | 1.000 | 0.948 |
| `oai-field-hybrid+text=concat+d=10` | question | 25 | 0.708 (25) | 0.740 | 1.000 | 0.588 | 0.480 | 0.720 | 0.760 | 0.800 | 0.920 | 0.933 |
| `oai-field-hybrid+text=concat+d=10` | paraphrase | 25 | 0.672 (25) | 0.648 | 1.000 | 0.498 | 0.400 | 0.600 | 0.720 | 0.800 | 0.840 | 0.959 |
| `oai-field-hybrid+text=concat+d=10` | known_item | 25 | 0.713 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `oai-field-hybrid+text=concat+d=100` | keyword | 25 | 0.715 (25) | 0.740 | 1.000 | 0.716 | 0.600 | 0.880 | 0.920 | 0.960 | 1.000 | 0.939 |
| `oai-field-hybrid+text=concat+d=100` | question | 25 | 0.706 (25) | 0.732 | 1.000 | 0.583 | 0.480 | 0.720 | 0.720 | 0.760 | 0.880 | 0.876 |
| `oai-field-hybrid+text=concat+d=100` | paraphrase | 25 | 0.680 (25) | 0.680 | 1.000 | 0.487 | 0.400 | 0.600 | 0.640 | 0.640 | 0.760 | 0.915 |
| `oai-field-hybrid+text=concat+d=100` | known_item | 25 | 0.721 (25) | 0.636 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.963 |
| `oai-field-hybrid+text=title25+d=10` | keyword | 25 | 0.727 (25) | 0.744 | 1.000 | 0.746 | 0.640 | 0.840 | 0.960 | 0.960 | 1.000 | 0.948 |
| `oai-field-hybrid+text=title25+d=10` | question | 25 | 0.712 (25) | 0.740 | 1.000 | 0.625 | 0.560 | 0.720 | 0.760 | 0.800 | 0.920 | 0.933 |
| `oai-field-hybrid+text=title25+d=10` | paraphrase | 25 | 0.668 (25) | 0.648 | 1.000 | 0.467 | 0.400 | 0.560 | 0.720 | 0.800 | 0.840 | 0.959 |
| `oai-field-hybrid+text=title25+d=10` | known_item | 25 | 0.718 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `oai-field-hybrid+text=title25+d=100` | keyword | 25 | 0.718 (25) | 0.724 | 0.960 | 0.742 | 0.640 | 0.840 | 0.920 | 0.960 | 1.000 | 0.912 |
| `oai-field-hybrid+text=title25+d=100` | question | 25 | 0.711 (25) | 0.740 | 0.980 | 0.625 | 0.560 | 0.720 | 0.760 | 0.760 | 0.880 | 0.899 |
| `oai-field-hybrid+text=title25+d=100` | paraphrase | 25 | 0.664 (25) | 0.660 | 0.964 | 0.458 | 0.400 | 0.560 | 0.640 | 0.640 | 0.760 | 0.896 |
| `oai-field-hybrid+text=title25+d=100` | known_item | 25 | 0.727 (25) | 0.632 | 0.956 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `oai-field-hybrid+text=title50+d=10` | keyword | 25 | 0.731 (25) | 0.744 | 1.000 | 0.729 | 0.600 | 0.840 | 0.960 | 0.960 | 1.000 | 0.948 |
| `oai-field-hybrid+text=title50+d=10` | question | 25 | 0.703 (25) | 0.740 | 1.000 | 0.572 | 0.480 | 0.720 | 0.760 | 0.800 | 0.920 | 0.933 |
| `oai-field-hybrid+text=title50+d=10` | paraphrase | 25 | 0.646 (25) | 0.648 | 1.000 | 0.434 | 0.360 | 0.480 | 0.720 | 0.800 | 0.840 | 0.959 |
| `oai-field-hybrid+text=title50+d=10` | known_item | 25 | 0.714 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `oai-field-hybrid+text=title50+d=100` | keyword | 25 | 0.710 (25) | 0.712 | 0.948 | 0.724 | 0.600 | 0.840 | 0.920 | 0.960 | 0.960 | 0.894 |
| `oai-field-hybrid+text=title50+d=100` | question | 25 | 0.689 (25) | 0.724 | 0.948 | 0.587 | 0.480 | 0.760 | 0.760 | 0.760 | 0.920 | 0.882 |
| `oai-field-hybrid+text=title50+d=100` | paraphrase | 25 | 0.607 (25) | 0.604 | 0.940 | 0.416 | 0.360 | 0.480 | 0.600 | 0.640 | 0.760 | 0.900 |
| `oai-field-hybrid+text=title50+d=100` | known_item | 25 | 0.718 (25) | 0.632 | 0.936 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.947 |
| `oai-field-hybrid+text=title75+d=10` | keyword | 25 | 0.718 (25) | 0.744 | 1.000 | 0.664 | 0.520 | 0.840 | 0.960 | 0.960 | 1.000 | 0.948 |
| `oai-field-hybrid+text=title75+d=10` | question | 25 | 0.694 (25) | 0.740 | 1.000 | 0.575 | 0.480 | 0.720 | 0.760 | 0.800 | 0.920 | 0.933 |
| `oai-field-hybrid+text=title75+d=10` | paraphrase | 25 | 0.639 (25) | 0.648 | 1.000 | 0.428 | 0.360 | 0.480 | 0.720 | 0.800 | 0.840 | 0.959 |
| `oai-field-hybrid+text=title75+d=10` | known_item | 25 | 0.704 (25) | 0.624 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `oai-field-hybrid+text=title75+d=100` | keyword | 25 | 0.659 (25) | 0.652 | 0.888 | 0.657 | 0.520 | 0.800 | 0.920 | 0.920 | 0.960 | 0.890 |
| `oai-field-hybrid+text=title75+d=100` | question | 25 | 0.637 (25) | 0.640 | 0.892 | 0.610 | 0.520 | 0.760 | 0.760 | 0.760 | 0.920 | 0.854 |
| `oai-field-hybrid+text=title75+d=100` | paraphrase | 25 | 0.590 (25) | 0.600 | 0.896 | 0.404 | 0.360 | 0.480 | 0.560 | 0.600 | 0.760 | 0.871 |
| `oai-field-hybrid+text=title75+d=100` | known_item | 25 | 0.690 (25) | 0.596 | 0.904 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.923 |
| `oai-field-recovery+text=abstract+anchor=0+d=10` | keyword | 25 | 0.722 (25) | 0.744 | 1.000 | 0.681 | 0.520 | 0.880 | 0.960 | 0.960 | 1.000 | 0.948 |
| `oai-field-recovery+text=abstract+anchor=0+d=10` | question | 25 | 0.706 (25) | 0.740 | 1.000 | 0.609 | 0.520 | 0.680 | 0.760 | 0.800 | 0.920 | 0.933 |
| `oai-field-recovery+text=abstract+anchor=0+d=10` | paraphrase | 25 | 0.681 (25) | 0.648 | 1.000 | 0.449 | 0.320 | 0.600 | 0.720 | 0.800 | 0.840 | 0.959 |
| `oai-field-recovery+text=abstract+anchor=0+d=10` | known_item | 25 | 0.717 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `oai-field-recovery+text=concat+anchor=1+d=10` | keyword | 25 | 0.721 (25) | 0.744 | 1.000 | 0.720 | 0.600 | 0.880 | 0.960 | 0.960 | 1.000 | 0.948 |
| `oai-field-recovery+text=concat+anchor=1+d=10` | question | 25 | 0.708 (25) | 0.740 | 1.000 | 0.588 | 0.480 | 0.720 | 0.760 | 0.800 | 0.920 | 0.933 |
| `oai-field-recovery+text=concat+anchor=1+d=10` | paraphrase | 25 | 0.672 (25) | 0.648 | 1.000 | 0.498 | 0.400 | 0.600 | 0.720 | 0.800 | 0.840 | 0.959 |
| `oai-field-recovery+text=concat+anchor=1+d=10` | known_item | 25 | 0.713 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `oai-field-recovery+text=title10+anchor=0+d=10` | keyword | 25 | 0.721 (25) | 0.744 | 1.000 | 0.721 | 0.600 | 0.880 | 0.960 | 0.960 | 1.000 | 0.948 |
| `oai-field-recovery+text=title10+anchor=0+d=10` | question | 25 | 0.706 (25) | 0.740 | 1.000 | 0.604 | 0.520 | 0.680 | 0.760 | 0.800 | 0.920 | 0.933 |
| `oai-field-recovery+text=title10+anchor=0+d=10` | paraphrase | 25 | 0.682 (25) | 0.648 | 1.000 | 0.488 | 0.400 | 0.600 | 0.720 | 0.800 | 0.840 | 0.959 |
| `oai-field-recovery+text=title10+anchor=0+d=10` | known_item | 25 | 0.719 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `oai-field-recovery+text=title25+anchor=0+d=10` | keyword | 25 | 0.727 (25) | 0.744 | 1.000 | 0.746 | 0.640 | 0.840 | 0.960 | 0.960 | 1.000 | 0.948 |
| `oai-field-recovery+text=title25+anchor=0+d=10` | question | 25 | 0.712 (25) | 0.740 | 1.000 | 0.625 | 0.560 | 0.720 | 0.760 | 0.800 | 0.920 | 0.933 |
| `oai-field-recovery+text=title25+anchor=0+d=10` | paraphrase | 25 | 0.668 (25) | 0.648 | 1.000 | 0.467 | 0.400 | 0.560 | 0.720 | 0.800 | 0.840 | 0.959 |
| `oai-field-recovery+text=title25+anchor=0+d=10` | known_item | 25 | 0.718 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `oai-field-recovery+text=title25+anchor=0.5+d=10` | keyword | 25 | 0.723 (25) | 0.744 | 1.000 | 0.729 | 0.600 | 0.880 | 0.960 | 0.960 | 1.000 | 0.948 |
| `oai-field-recovery+text=title25+anchor=0.5+d=10` | question | 25 | 0.711 (25) | 0.740 | 1.000 | 0.565 | 0.440 | 0.720 | 0.760 | 0.800 | 0.920 | 0.933 |
| `oai-field-recovery+text=title25+anchor=0.5+d=10` | paraphrase | 25 | 0.673 (25) | 0.648 | 1.000 | 0.502 | 0.440 | 0.600 | 0.720 | 0.800 | 0.840 | 0.959 |
| `oai-field-recovery+text=title25+anchor=0.5+d=10` | known_item | 25 | 0.717 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `oai-field-recovery+text=title25+anchor=0.75+d=10` | keyword | 25 | 0.722 (25) | 0.744 | 1.000 | 0.730 | 0.600 | 0.880 | 0.960 | 0.960 | 1.000 | 0.948 |
| `oai-field-recovery+text=title25+anchor=0.75+d=10` | question | 25 | 0.708 (25) | 0.740 | 1.000 | 0.568 | 0.440 | 0.720 | 0.760 | 0.800 | 0.920 | 0.933 |
| `oai-field-recovery+text=title25+anchor=0.75+d=10` | paraphrase | 25 | 0.674 (25) | 0.648 | 1.000 | 0.536 | 0.480 | 0.600 | 0.720 | 0.800 | 0.840 | 0.959 |
| `oai-field-recovery+text=title25+anchor=0.75+d=10` | known_item | 25 | 0.716 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `score-max+w=0.35+d=100` | keyword | 25 | 0.705 (25) | 0.740 | 1.000 | 0.727 | 0.600 | 0.880 | 0.880 | 0.960 | 1.000 | 0.860 |
| `score-max+w=0.35+d=100` | question | 25 | 0.650 (25) | 0.688 | 1.000 | 0.510 | 0.400 | 0.640 | 0.720 | 0.720 | 0.720 | 0.673 |
| `score-max+w=0.35+d=100` | paraphrase | 25 | 0.575 (25) | 0.612 | 1.000 | 0.307 | 0.240 | 0.400 | 0.400 | 0.440 | 0.480 | 0.630 |
| `score-max+w=0.35+d=100` | known_item | 25 | 0.715 (25) | 0.640 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.940 |
| `score-max+w=0.35+d=500` | keyword | 25 | 0.695 (25) | 0.716 | 1.000 | 0.732 | 0.600 | 0.880 | 0.920 | 0.960 | 1.000 | 0.854 |
| `score-max+w=0.35+d=500` | question | 25 | 0.589 (25) | 0.628 | 1.000 | 0.502 | 0.400 | 0.640 | 0.720 | 0.720 | 0.760 | 0.743 |
| `score-max+w=0.35+d=500` | paraphrase | 25 | 0.500 (25) | 0.540 | 1.000 | 0.241 | 0.160 | 0.360 | 0.440 | 0.520 | 0.640 | 0.807 |
| `score-max+w=0.35+d=500` | known_item | 25 | 0.717 (25) | 0.656 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.943 |
| `score-max+w=0.55+d=100` | keyword | 25 | 0.721 (25) | 0.748 | 1.000 | 0.775 | 0.680 | 0.920 | 0.920 | 0.960 | 0.960 | 0.880 |
| `score-max+w=0.55+d=100` | question | 25 | 0.684 (25) | 0.716 | 1.000 | 0.532 | 0.400 | 0.680 | 0.720 | 0.800 | 0.920 | 0.915 |
| `score-max+w=0.55+d=100` | paraphrase | 25 | 0.621 (25) | 0.648 | 1.000 | 0.336 | 0.240 | 0.440 | 0.520 | 0.680 | 0.880 | 0.964 |
| `score-max+w=0.55+d=100` | known_item | 25 | 0.718 (25) | 0.632 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.933 |
| `score-max+w=0.55+d=500` | keyword | 25 | 0.719 (25) | 0.728 | 1.000 | 0.779 | 0.680 | 0.920 | 0.960 | 1.000 | 1.000 | 0.886 |
| `score-max+w=0.55+d=500` | question | 25 | 0.662 (25) | 0.704 | 1.000 | 0.532 | 0.400 | 0.680 | 0.720 | 0.720 | 0.840 | 0.791 |
| `score-max+w=0.55+d=500` | paraphrase | 25 | 0.592 (25) | 0.600 | 1.000 | 0.336 | 0.240 | 0.440 | 0.560 | 0.640 | 0.680 | 0.846 |
| `score-max+w=0.55+d=500` | known_item | 25 | 0.722 (25) | 0.648 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.963 |
| `score-max+w=0.75+d=100` | keyword | 25 | 0.713 (25) | 0.732 | 1.000 | 0.716 | 0.600 | 0.880 | 0.920 | 0.960 | 0.960 | 0.880 |
| `score-max+w=0.75+d=100` | question | 25 | 0.708 (25) | 0.728 | 1.000 | 0.583 | 0.480 | 0.720 | 0.720 | 0.800 | 0.920 | 0.911 |
| `score-max+w=0.75+d=100` | paraphrase | 25 | 0.648 (25) | 0.652 | 1.000 | 0.394 | 0.320 | 0.440 | 0.640 | 0.720 | 0.880 | 0.964 |
| `score-max+w=0.75+d=100` | known_item | 25 | 0.722 (25) | 0.632 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.937 |
| `score-max+w=0.75+d=500` | keyword | 25 | 0.715 (25) | 0.740 | 1.000 | 0.716 | 0.600 | 0.880 | 0.920 | 0.960 | 1.000 | 0.932 |
| `score-max+w=0.75+d=500` | question | 25 | 0.706 (25) | 0.732 | 1.000 | 0.583 | 0.480 | 0.720 | 0.720 | 0.760 | 0.880 | 0.821 |
| `score-max+w=0.75+d=500` | paraphrase | 25 | 0.682 (25) | 0.680 | 1.000 | 0.487 | 0.400 | 0.600 | 0.640 | 0.640 | 0.720 | 0.863 |
| `score-max+w=0.75+d=500` | known_item | 25 | 0.721 (25) | 0.636 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.953 |
| `score-minmax+w=0.35+d=100` | keyword | 25 | 0.685 (25) | 0.688 | 1.000 | 0.732 | 0.600 | 0.880 | 0.920 | 1.000 | 1.000 | 0.882 |
| `score-minmax+w=0.35+d=100` | question | 25 | 0.562 (25) | 0.560 | 1.000 | 0.516 | 0.400 | 0.640 | 0.720 | 0.760 | 0.840 | 0.789 |
| `score-minmax+w=0.35+d=100` | paraphrase | 25 | 0.472 (25) | 0.492 | 1.000 | 0.256 | 0.160 | 0.360 | 0.520 | 0.680 | 0.800 | 0.909 |
| `score-minmax+w=0.35+d=100` | known_item | 25 | 0.675 (25) | 0.568 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.947 |
| `score-minmax+w=0.35+d=500` | keyword | 25 | 0.700 (25) | 0.712 | 1.000 | 0.736 | 0.600 | 0.880 | 0.960 | 1.000 | 1.000 | 0.879 |
| `score-minmax+w=0.35+d=500` | question | 25 | 0.607 (25) | 0.628 | 1.000 | 0.519 | 0.400 | 0.680 | 0.720 | 0.720 | 0.800 | 0.778 |
| `score-minmax+w=0.35+d=500` | paraphrase | 25 | 0.520 (25) | 0.556 | 1.000 | 0.268 | 0.160 | 0.440 | 0.480 | 0.600 | 0.680 | 0.838 |
| `score-minmax+w=0.35+d=500` | known_item | 25 | 0.701 (25) | 0.608 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.963 |
| `score-minmax+w=0.55+d=100` | keyword | 25 | 0.692 (25) | 0.700 | 1.000 | 0.700 | 0.560 | 0.880 | 0.920 | 1.000 | 1.000 | 0.912 |
| `score-minmax+w=0.55+d=100` | question | 25 | 0.687 (25) | 0.712 | 1.000 | 0.586 | 0.440 | 0.760 | 0.800 | 0.800 | 0.920 | 0.874 |
| `score-minmax+w=0.55+d=100` | paraphrase | 25 | 0.630 (25) | 0.600 | 1.000 | 0.492 | 0.400 | 0.640 | 0.680 | 0.800 | 0.880 | 0.973 |
| `score-minmax+w=0.55+d=100` | known_item | 25 | 0.677 (25) | 0.576 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.947 |
| `score-minmax+w=0.55+d=500` | keyword | 25 | 0.710 (25) | 0.728 | 1.000 | 0.699 | 0.560 | 0.880 | 0.920 | 1.000 | 1.000 | 0.938 |
| `score-minmax+w=0.55+d=500` | question | 25 | 0.686 (25) | 0.724 | 1.000 | 0.560 | 0.440 | 0.680 | 0.760 | 0.800 | 0.920 | 0.939 |
| `score-minmax+w=0.55+d=500` | paraphrase | 25 | 0.656 (25) | 0.636 | 1.000 | 0.498 | 0.400 | 0.600 | 0.680 | 0.720 | 0.840 | 0.954 |
| `score-minmax+w=0.55+d=500` | known_item | 25 | 0.705 (25) | 0.608 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.957 |
| `score-minmax+w=0.75+d=100` | keyword | 25 | 0.662 (25) | 0.696 | 1.000 | 0.642 | 0.520 | 0.880 | 0.920 | 0.960 | 1.000 | 0.904 |
| `score-minmax+w=0.75+d=100` | question | 25 | 0.693 (25) | 0.716 | 1.000 | 0.596 | 0.480 | 0.760 | 0.800 | 0.840 | 0.920 | 0.860 |
| `score-minmax+w=0.75+d=100` | paraphrase | 25 | 0.664 (25) | 0.660 | 1.000 | 0.496 | 0.440 | 0.600 | 0.720 | 0.800 | 0.880 | 0.952 |
| `score-minmax+w=0.75+d=100` | known_item | 25 | 0.643 (25) | 0.532 | 1.000 | 0.950 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.937 |
| `score-minmax+w=0.75+d=500` | keyword | 25 | 0.680 (25) | 0.704 | 1.000 | 0.669 | 0.560 | 0.880 | 0.920 | 0.960 | 0.960 | 0.904 |
| `score-minmax+w=0.75+d=500` | question | 25 | 0.707 (25) | 0.736 | 1.000 | 0.602 | 0.480 | 0.760 | 0.800 | 0.840 | 0.920 | 0.908 |
| `score-minmax+w=0.75+d=500` | paraphrase | 25 | 0.681 (25) | 0.672 | 1.000 | 0.504 | 0.440 | 0.600 | 0.720 | 0.800 | 0.880 | 0.972 |
| `score-minmax+w=0.75+d=500` | known_item | 25 | 0.662 (25) | 0.560 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 | 1.000 | 0.937 |
| `llm-mini-score-pilot+d=50` | keyword | 25 | 0.741 (25) | 0.800 | 1.000 | 0.652 | 0.560 | 0.760 | 0.880 | 0.920 | 1.000 | 0.948 |
| `llm-mini-score-pilot+d=50` | question | 25 | 0.835 (25) | 0.860 | 1.000 | 0.585 | 0.440 | 0.800 | 0.840 | 0.920 | 0.920 | 0.933 |
| `llm-mini-score-pilot+d=50` | paraphrase | 25 | 0.765 (25) | 0.768 | 1.000 | 0.493 | 0.320 | 0.720 | 0.800 | 0.840 | 0.840 | 0.959 |
| `llm-mini-score-pilot+d=50` | known_item | 25 | 0.750 (25) | 0.680 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `llm-mini-score-pilot+d=50+avg2` | keyword | 25 | 0.755 (25) | 0.804 | 1.000 | 0.618 | 0.520 | 0.800 | 0.840 | 0.920 | 1.000 | 0.948 |
| `llm-mini-score-pilot+d=50+avg2` | question | 25 | 0.868 (25) | 0.884 | 1.000 | 0.644 | 0.480 | 0.840 | 0.920 | 0.920 | 0.920 | 0.933 |
| `llm-mini-score-pilot+d=50+avg2` | paraphrase | 25 | 0.779 (25) | 0.780 | 1.000 | 0.503 | 0.320 | 0.760 | 0.760 | 0.800 | 0.840 | 0.959 |
| `llm-mini-score-pilot+d=50+avg2` | known_item | 25 | 0.749 (25) | 0.684 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30` | keyword | 25 | 0.759 (25) | 0.792 | 1.000 | 0.697 | 0.560 | 0.880 | 0.920 | 0.960 | 1.000 | 0.948 |
| `llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30` | question | 25 | 0.800 (25) | 0.816 | 1.000 | 0.646 | 0.520 | 0.760 | 0.800 | 0.920 | 0.920 | 0.933 |
| `llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30` | paraphrase | 25 | 0.769 (25) | 0.736 | 1.000 | 0.550 | 0.440 | 0.680 | 0.760 | 0.840 | 0.840 | 0.959 |
| `llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30` | known_item | 25 | 0.746 (25) | 0.660 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `llm-mini-score-pilot+d=50+blend-rank-prior+b=2+c=30` | keyword | 25 | 0.743 (25) | 0.800 | 1.000 | 0.665 | 0.560 | 0.800 | 0.880 | 0.920 | 1.000 | 0.948 |
| `llm-mini-score-pilot+d=50+blend-rank-prior+b=2+c=30` | question | 25 | 0.836 (25) | 0.860 | 1.000 | 0.606 | 0.480 | 0.840 | 0.840 | 0.920 | 0.920 | 0.933 |
| `llm-mini-score-pilot+d=50+blend-rank-prior+b=2+c=30` | paraphrase | 25 | 0.768 (25) | 0.772 | 1.000 | 0.493 | 0.320 | 0.720 | 0.800 | 0.840 | 0.840 | 0.959 |
| `llm-mini-score-pilot+d=50+blend-rank-prior+b=2+c=30` | known_item | 25 | 0.749 (25) | 0.676 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `llm-mini-score-pilot+d=50+blend-rank-prior+b=3+c=30` | keyword | 25 | 0.748 (25) | 0.800 | 1.000 | 0.690 | 0.600 | 0.840 | 0.920 | 0.960 | 1.000 | 0.948 |
| `llm-mini-score-pilot+d=50+blend-rank-prior+b=3+c=30` | question | 25 | 0.828 (25) | 0.852 | 1.000 | 0.605 | 0.480 | 0.800 | 0.840 | 0.920 | 0.920 | 0.933 |
| `llm-mini-score-pilot+d=50+blend-rank-prior+b=3+c=30` | paraphrase | 25 | 0.767 (25) | 0.752 | 1.000 | 0.511 | 0.320 | 0.760 | 0.800 | 0.840 | 0.840 | 0.959 |
| `llm-mini-score-pilot+d=50+blend-rank-prior+b=3+c=30` | known_item | 25 | 0.744 (25) | 0.664 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `llm-mini-score-pilot+d=50+blend-rank-prior+b=4+c=30` | keyword | 25 | 0.749 (25) | 0.796 | 1.000 | 0.701 | 0.600 | 0.880 | 0.920 | 0.960 | 1.000 | 0.948 |
| `llm-mini-score-pilot+d=50+blend-rank-prior+b=4+c=30` | question | 25 | 0.815 (25) | 0.840 | 1.000 | 0.612 | 0.480 | 0.800 | 0.840 | 0.920 | 0.920 | 0.933 |
| `llm-mini-score-pilot+d=50+blend-rank-prior+b=4+c=30` | paraphrase | 25 | 0.754 (25) | 0.724 | 1.000 | 0.517 | 0.320 | 0.760 | 0.800 | 0.840 | 0.840 | 0.959 |
| `llm-mini-score-pilot+d=50+blend-rank-prior+b=4+c=30` | known_item | 25 | 0.737 (25) | 0.652 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |
| `llm-mini-score-pilot+d=50+rrf-baseline+c=30` | keyword | 25 | 0.749 (25) | 0.784 | 1.000 | 0.709 | 0.600 | 0.920 | 0.920 | 0.960 | 1.000 | 0.948 |
| `llm-mini-score-pilot+d=50+rrf-baseline+c=30` | question | 25 | 0.778 (25) | 0.812 | 1.000 | 0.595 | 0.480 | 0.760 | 0.800 | 0.840 | 0.920 | 0.933 |
| `llm-mini-score-pilot+d=50+rrf-baseline+c=30` | paraphrase | 25 | 0.747 (25) | 0.704 | 1.000 | 0.574 | 0.480 | 0.720 | 0.760 | 0.840 | 0.840 | 0.959 |
| `llm-mini-score-pilot+d=50+rrf-baseline+c=30` | known_item | 25 | 0.734 (25) | 0.644 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.967 |

<details>
<summary>Readable techniques and original system IDs</summary>

| Original system ID | System | Keyword retrieval | Embedding | Ranker / fusion |
|---|---|---|---|---|
| `oai-field-recovery+text=title10+anchor=0+d=10` | OpenAI-large paraphrase recovery | Tuned BM25 including authors/title2x | OpenAI text-embedding-3-large | 25% lexical / 75% semantic; 10% title / 90% abstract; 0% combined-text anchor; candidate-max normalization; reorder baseline top10 only, preserve tail |
| `oai-field-recovery+text=abstract+anchor=0+d=10` | OpenAI-large paraphrase recovery | Tuned BM25 including authors/title2x | OpenAI text-embedding-3-large | 25% lexical / 75% semantic; abstract only; 0% combined-text anchor; candidate-max normalization; reorder baseline top10 only, preserve tail |
| `oai-field-recovery+text=title25+anchor=0.5+d=10` | OpenAI-large paraphrase recovery | Tuned BM25 including authors/title2x | OpenAI text-embedding-3-large | 25% lexical / 75% semantic; 25% title / 75% abstract; 50% combined-text anchor; candidate-max normalization; reorder baseline top10 only, preserve tail |
| `oai-field-hybrid+text=title25+d=10` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 25% / abstract 75%; max-score25% lexical / 75% field semantic; reorder baseline top10 only, preserve tail |
| `oai-field-recovery+text=title25+anchor=0+d=10` | OpenAI-large paraphrase recovery | Tuned BM25 including authors/title2x | OpenAI text-embedding-3-large | 25% lexical / 75% semantic; 25% title / 75% abstract; 0% combined-text anchor; candidate-max normalization; reorder baseline top10 only, preserve tail |
| `score-max+w=0.75+d=500` | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Max-normalized scores; 75% semantic / 25% lexical; depth 500 |
| `oai-field-hybrid+text=concat+d=100` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | concatenated title + abstract control; max-score25% lexical / 75% field semantic; reorder baseline top100 only, preserve tail |
| `oai-field-recovery+text=title25+anchor=0.75+d=10` | OpenAI-large paraphrase recovery | Tuned BM25 including authors/title2x | OpenAI text-embedding-3-large | 25% lexical / 75% semantic; 25% title / 75% abstract; 75% combined-text anchor; candidate-max normalization; reorder baseline top10 only, preserve tail |
| `field-gte-concat` | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | concatenated title + abstract control; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 |
| `field-gte-separate+t=0.25` | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | separate title 25% / abstract 75%; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 |
| `field-gte-separate+t=0.5` | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | separate title 50% / abstract 50%; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 |
| `field-gte-separate+t=0.75` | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | separate title 75% / abstract 25%; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 |
| `fusion-shortlist+a=1+d=500` | Fixed-shortlist score ordering | Tuned BM25 | OpenAI text-embedding-3-large | RRF55%/c30/depth100 selects top10; order by max-score 75% semantic / 25% lexical at depth 500; preserve tail |
| `oai-field-hybrid+text=concat+d=10` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | concatenated title + abstract control; max-score25% lexical / 75% field semantic; reorder baseline top10 only, preserve tail |
| `oai-field-recovery+text=concat+anchor=1+d=10` | OpenAI-large paraphrase recovery | Tuned BM25 including authors/title2x | OpenAI text-embedding-3-large | 25% lexical / 75% semantic; combined title + abstract; 100% combined-text anchor; candidate-max normalization; reorder baseline top10 only, preserve tail |
| `fusion-shortlist+a=1+d=100` | Fixed-shortlist score ordering | Tuned BM25 | OpenAI text-embedding-3-large | RRF55%/c30/depth100 selects top10; order by max-score 75% semantic / 25% lexical at depth 100; preserve tail |
| `oai-field-hybrid+text=title50+d=10` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 50% / abstract 50%; max-score25% lexical / 75% field semantic; reorder baseline top10 only, preserve tail |
| `score-max+w=0.75+d=100` | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Max-normalized scores; 75% semantic / 25% lexical; depth 100 |
| `fusion-rankscore+a=0.75+d=100` | Rank + score interpolation | Tuned BM25 | OpenAI text-embedding-3-large | 75% max-score75% + 25% normalized RRF55%/c30/d100; score depth 100 |
| `fusion-rrf+w=0.6+d=100+c=60` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 60% semantic / 40% lexical; depth 100 |
| `fusion-rankscore+a=0.25+d=100` | Rank + score interpolation | Tuned BM25 | OpenAI text-embedding-3-large | 25% max-score75% + 75% normalized RRF55%/c30/d100; score depth 100 |
| `fusion-shortlist+a=0.5+d=500` | Fixed-shortlist score ordering | Tuned BM25 | OpenAI text-embedding-3-large | 50% max-score75% + 50% normalized RRF55%/c30/d100; score depth 500; reorder baseline top10 only, preserve tail |
| `fusion-shortlist+a=0.5+d=100` | Fixed-shortlist score ordering | Tuned BM25 | OpenAI text-embedding-3-large | 50% max-score75% + 50% normalized RRF55%/c30/d100; score depth 100; reorder baseline top10 only, preserve tail |
| `fusion-rankscore+a=0.5+d=500` | Rank + score interpolation | Tuned BM25 | OpenAI text-embedding-3-large | 50% max-score75% + 50% normalized RRF55%/c30/d100; score depth 500 |
| `fusion-rankscore+a=0.5+d=100` | Rank + score interpolation | Tuned BM25 | OpenAI text-embedding-3-large | 50% max-score75% + 50% normalized RRF55%/c30/d100; score depth 100 |
| `fusion-rrf+w=0.55+d=100+c=30` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 55% semantic / 45% lexical; depth 100 |
| `fusion-rrf+w=0.65+d=100+c=60` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 65% semantic / 35% lexical; depth 100 |
| `field-lexical+t=0.25` | Lexical field-score ablation | Independent BM25 fields; 10% authors | OpenAI large candidate retrieval | separate title 25% / abstract 75%; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 |
| `fusion-rrf+w=0.55+d=200+c=30` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 55% semantic / 45% lexical; depth 200 |
| `field-order-gte-concat` | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | concatenated title + abstract control; pure semantic field score; reorder baseline top10 only, preserve tail |
| `fusion-rrf+w=0.75+d=100+c=100` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 75% semantic / 25% lexical; depth 100 |
| `fusion-rankscore+a=0.25+d=500` | Rank + score interpolation | Tuned BM25 | OpenAI text-embedding-3-large | 25% max-score75% + 75% normalized RRF55%/c30/d100; score depth 500 |
| `fusion-rrf+w=0.7+d=100+c=60` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 70% semantic / 30% lexical; depth 100 |
| `fusion-top1bonus+b=0.1+w=0.55+d=100+c=30` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30 + 10% top-1 bonus; 55% semantic / 45% lexical; depth 100 |
| `fusion-rrf+w=0.6+d=100+c=30` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 60% semantic / 40% lexical; depth 100 |
| `fusion-rrf+w=0.55+d=100+c=60` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 55% semantic / 45% lexical; depth 100 |
| `fusion-rrf+w=0.55+d=500+c=30` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 55% semantic / 45% lexical; depth 500 |
| `field-order-gte-separate+t=0.25` | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | separate title 25% / abstract 75%; pure semantic field score; reorder baseline top10 only, preserve tail |
| `score-minmax+w=0.55+d=500` | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Min-max-normalized scores; 55% semantic / 45% lexical; depth 500 |
| `fusion-rrf+w=0.65+d=100+c=30` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 65% semantic / 35% lexical; depth 100 |
| `fusion-linear+w=0.75+d=100` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 75% semantic / 25% lexical; depth 100 |
| `oai-field-hybrid+text=title75+d=10` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 75% / abstract 25%; max-score25% lexical / 75% field semantic; reorder baseline top10 only, preserve tail |
| `fusion-top1bonus+b=0.25+w=0.55+d=100+c=30` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30 + 25% top-1 bonus; 55% semantic / 45% lexical; depth 100 |
| `cross-minilm-l6+pool=baseline+d=10` | Local cross-encoder reranking | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large candidate retrieval | MiniLM-L6 cross-encoder raw logits; reorder current baseline top10 only, preserve tail |
| `fusion-rrf+w=0.75+d=100+c=60` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 75% semantic / 25% lexical; depth 100 |
| `oai-field+text=title25+d=10` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 25% / abstract 75%; pure cosine; reorder baseline top10 only, preserve tail |
| `score-max+w=0.55+d=100` | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Max-normalized scores; 55% semantic / 45% lexical; depth 100 |
| `fusion-rrf+w=0.7+d=100+c=30` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 70% semantic / 30% lexical; depth 100 |
| `field-lexical+t=0.5` | Lexical field-score ablation | Independent BM25 fields; 10% authors | OpenAI large candidate retrieval | separate title 50% / abstract 50%; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 |
| `fusion-rrf+w=0.75+d=50+c=100` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 75% semantic / 25% lexical; depth 50 |
| `score-minmax+w=0.75+d=500` | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Min-max-normalized scores; 75% semantic / 25% lexical; depth 500 |
| `fusion-rrf+w=0.5+d=100+c=60` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 50% semantic / 50% lexical; depth 100 |
| `field-order-gte-separate+t=0.5` | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | separate title 50% / abstract 50%; pure semantic field score; reorder baseline top10 only, preserve tail |
| `fusion-rrf+w=0.75+d=50+c=60` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 75% semantic / 25% lexical; depth 50 |
| `fusion-rrf+w=0.75+d=100+c=30` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 75% semantic / 25% lexical; depth 100 |
| `fusion-rrf+w=0.5+d=100+c=100` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 50% semantic / 50% lexical; depth 100 |
| `fusion-rrf+w=0.5+d=100+c=30` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 50% semantic / 50% lexical; depth 100 |
| `fusion-linear+w=0.5+d=100` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 50% semantic / 50% lexical; depth 100 |
| `oai-field+text=concat+d=10` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | concatenated title + abstract control; pure cosine; reorder baseline top10 only, preserve tail |
| `oai-field+text=title50+d=10` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 50% / abstract 50%; pure cosine; reorder baseline top10 only, preserve tail |
| `score-max+w=0.55+d=500` | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Max-normalized scores; 55% semantic / 45% lexical; depth 500 |
| `fusion-rrf+w=0.6+d=100+c=10` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 60% semantic / 40% lexical; depth 100 |
| `fusion-linear+w=0.75+d=50` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 75% semantic / 25% lexical; depth 50 |
| `score-minmax+w=0.55+d=100` | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Min-max-normalized scores; 55% semantic / 45% lexical; depth 100 |
| `fusion-rrf+w=0.65+d=100+c=10` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 65% semantic / 35% lexical; depth 100 |
| `oai-field+text=title75+d=10` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 75% / abstract 25%; pure cosine; reorder baseline top10 only, preserve tail |
| `field-lexical+t=0.75` | Lexical field-score ablation | Independent BM25 fields; 10% authors | OpenAI large candidate retrieval | separate title 75% / abstract 25%; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 |
| `fusion-rrf+w=0.55+d=100+c=10` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 55% semantic / 45% lexical; depth 100 |
| `fusion-rrf+w=0.7+d=100+c=10` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 70% semantic / 30% lexical; depth 100 |
| `score-minmax+w=0.75+d=100` | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Min-max-normalized scores; 75% semantic / 25% lexical; depth 100 |
| `fusion-rrf+w=0.5+d=50+c=60` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 50% semantic / 50% lexical; depth 50 |
| `fusion-rrf+w=0.75+d=20+c=60` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 75% semantic / 25% lexical; depth 20 |
| `fusion-rrf+w=0.75+d=20+c=100` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 75% semantic / 25% lexical; depth 20 |
| `field-order-gte-separate+t=0.75` | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | separate title 75% / abstract 25%; pure semantic field score; reorder baseline top10 only, preserve tail |
| `fusion-rrf+w=0.5+d=50+c=100` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 50% semantic / 50% lexical; depth 50 |
| `fusion-rrf+w=0.75+d=100+c=10` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 75% semantic / 25% lexical; depth 100 |
| `fusion-rrf+w=0.75+d=50+c=10` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 75% semantic / 25% lexical; depth 50 |
| `score-max+w=0.35+d=100` | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Max-normalized scores; 35% semantic / 65% lexical; depth 100 |
| `fusion-linear+w=0.5+d=50` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 50% semantic / 50% lexical; depth 50 |
| `fusion-rrf+w=0.75+d=20+c=10` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 75% semantic / 25% lexical; depth 20 |
| `fusion-linear+w=0.75+d=20` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 75% semantic / 25% lexical; depth 20 |
| `baseline-original-equal-rrf-c10-d100` | Original hybrid control | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 50% semantic / 50% lexical; depth 100 |
| `fusion-rrf+w=0.5+d=100+c=10` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 50% semantic / 50% lexical; depth 100 |
| `hybrid-openai-large+rrf+w=0.5+c=10` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 50% semantic / 50% lexical; depth 100 |
| `fusion-rrf+w=0.25+d=100+c=100` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 25% semantic / 75% lexical; depth 100 |
| `fusion-rrf+w=0.5+d=50+c=10` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 50% semantic / 50% lexical; depth 50 |
| `fusion-rrf+w=0.25+d=50+c=100` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 25% semantic / 75% lexical; depth 50 |
| `score-minmax+w=0.35+d=500` | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Min-max-normalized scores; 35% semantic / 65% lexical; depth 500 |
| `fusion-rrf+w=0.5+d=20+c=10` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 50% semantic / 50% lexical; depth 20 |
| `fusion-rrf+w=0.5+d=20+c=60` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 50% semantic / 50% lexical; depth 20 |
| `fusion-rrf+w=0.5+d=20+c=100` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 50% semantic / 50% lexical; depth 20 |
| `dense-openai-large` | Embedding search | None | OpenAI text-embedding-3-large | Cosine similarity |
| `fusion-rrf+w=1+d=100+c=10` | Semantic-only fusion control | None (0% weight) | OpenAI text-embedding-3-large | RRF c=10; depth 100 |
| `oai-field+text=concat+d=100` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | concatenated title + abstract control; pure cosine; reorder baseline top100 only, preserve tail |
| `score-max+w=0.35+d=500` | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Max-normalized scores; 35% semantic / 65% lexical; depth 500 |
| `fusion-linear+w=0.25+d=100` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 25% semantic / 75% lexical; depth 100 |
| `fusion-rrf+w=0.25+d=100+c=60` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 25% semantic / 75% lexical; depth 100 |
| `fusion-linear+w=0.5+d=20` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 50% semantic / 50% lexical; depth 20 |
| `hybrid-gte-small+rrf+w=0.5+c=10` | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=10; 50% semantic / 50% lexical; depth 100 |
| `hybrid-bge-small+rrf+w=0.5+c=10` | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=10; 50% semantic / 50% lexical; depth 100 |
| `fusion-rrf+w=0.25+d=50+c=60` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 25% semantic / 75% lexical; depth 50 |
| `score-minmax+w=0.35+d=100` | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Min-max-normalized scores; 35% semantic / 65% lexical; depth 100 |
| `fusion-linear+w=0.25+d=50` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 25% semantic / 75% lexical; depth 50 |
| `fusion-rrf+w=0.25+d=20+c=100` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 25% semantic / 75% lexical; depth 20 |
| `fusion-rrf+w=0.25+d=20+c=60` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 25% semantic / 75% lexical; depth 20 |
| `dense-gte-small` | Embedding search | None | GTE-small | Cosine similarity |
| `dense-bge-small` | Embedding search | None | BGE-small | Cosine similarity |
| `fusion-rrf+w=0.25+d=100+c=10` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 25% semantic / 75% lexical; depth 100 |
| `fusion-rrf+w=0.25+d=50+c=10` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 25% semantic / 75% lexical; depth 50 |
| `fusion-rrf+w=0.25+d=20+c=10` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 25% semantic / 75% lexical; depth 20 |
| `fusion-linear+w=0.25+d=20` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 25% semantic / 75% lexical; depth 20 |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | Keyword search | BM25: exact + stems; authors; title x2; k1=0.8,b=0.75 | None | BM25 score |
| `fusion-rrf+w=0+d=100+c=10` | Lexical-only fusion control | Tuned BM25 | None (0% weight) | RRF c=10; depth 100 |
| `oai-field-hybrid+text=title25+d=100` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 25% / abstract 75%; max-score25% lexical / 75% field semantic; reorder baseline top100 only, preserve tail |
| `fusion-rankscore+a=0.75+d=500` | Rank + score interpolation | Tuned BM25 | OpenAI text-embedding-3-large | 75% max-score75% + 25% normalized RRF55%/c30/d100; score depth 500 |
| `fusion-rrf+w=0.7+d=100+c=100` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 70% semantic / 30% lexical; depth 100 |
| `fusion-rrf+w=0.6+d=100+c=100` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 60% semantic / 40% lexical; depth 100 |
| `fusion-rrf+w=0.65+d=100+c=100` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 65% semantic / 35% lexical; depth 100 |
| `fusion-rrf+w=0.55+d=100+c=100` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 55% semantic / 45% lexical; depth 100 |
| `oai-field-hybrid+text=title50+d=100` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 50% / abstract 50%; max-score25% lexical / 75% field semantic; reorder baseline top100 only, preserve tail |
| `cross-minilm-l6+pool=union100+w=0.5` | Local cross-encoder reranking | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large candidate retrieval | 50% cross-encoder rank + 50% baseline rank, RRF c30; union of lexical100, semantic100 and baseline100 |
| `oai-field-hybrid+text=title75+d=100` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 75% / abstract 25%; max-score25% lexical / 75% field semantic; reorder baseline top100 only, preserve tail |
| `hybrid-gte-small+rrf+w=0.75+c=60` | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=60; 75% semantic / 25% lexical; depth 100 |
| `cross-minilm-l6+pool=baseline+d=30` | Local cross-encoder reranking | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large candidate retrieval | MiniLM-L6 cross-encoder raw logits; reorder current baseline top30 only, preserve tail |
| `hybrid-gte-small+rrf+w=0.75+c=100` | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=100; 75% semantic / 25% lexical; depth 100 |
| `hybrid-gte-small+linear+w=0.75` | Hybrid rank fusion | Tuned BM25 | GTE-small | Linear rank fusion; 75% semantic / 25% lexical; depth 100 |
| `oai-field+text=title25+d=100` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 25% / abstract 75%; pure cosine; reorder baseline top100 only, preserve tail |
| `hybrid-gte-small+rrf+w=0.5+c=60` | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=60; 50% semantic / 50% lexical; depth 100 |
| `hybrid-bge-small+rrf+w=0.5+c=60` | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=60; 50% semantic / 50% lexical; depth 100 |
| `hybrid-gte-small+linear+w=0.5` | Hybrid rank fusion | Tuned BM25 | GTE-small | Linear rank fusion; 50% semantic / 50% lexical; depth 100 |
| `hybrid-bge-small+linear+w=0.75` | Hybrid rank fusion | Tuned BM25 | BGE-small | Linear rank fusion; 75% semantic / 25% lexical; depth 100 |
| `hybrid-gte-small+rrf+w=0.5+c=100` | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=100; 50% semantic / 50% lexical; depth 100 |
| `hybrid-bge-small+linear+w=0.5` | Hybrid rank fusion | Tuned BM25 | BGE-small | Linear rank fusion; 50% semantic / 50% lexical; depth 100 |
| `hybrid-bge-small+rrf+w=0.5+c=100` | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=100; 50% semantic / 50% lexical; depth 100 |
| `hybrid-bge-small+rrf+w=0.75+c=100` | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=100; 75% semantic / 25% lexical; depth 100 |
| `hybrid-bge-small+rrf+w=0.75+c=60` | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=60; 75% semantic / 25% lexical; depth 100 |
| `hybrid-gte-small+rrf+w=0.25+c=100` | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=100; 25% semantic / 75% lexical; depth 100 |
| `hybrid-gte-small+rrf+w=0.75+c=10` | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=10; 75% semantic / 25% lexical; depth 100 |
| `hybrid-bge-small+rrf+w=0.25+c=100` | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=100; 25% semantic / 75% lexical; depth 100 |
| `hybrid-bge-small+rrf+w=0.75+c=10` | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=10; 75% semantic / 25% lexical; depth 100 |
| `oai-field+text=title50+d=100` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 50% / abstract 50%; pure cosine; reorder baseline top100 only, preserve tail |
| `hybrid-gte-small+rrf+w=0.25+c=60` | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=60; 25% semantic / 75% lexical; depth 100 |
| `hybrid-gte-small+linear+w=0.25` | Hybrid rank fusion | Tuned BM25 | GTE-small | Linear rank fusion; 25% semantic / 75% lexical; depth 100 |
| `hybrid-bge-small+linear+w=0.25` | Hybrid rank fusion | Tuned BM25 | BGE-small | Linear rank fusion; 25% semantic / 75% lexical; depth 100 |
| `hybrid-bge-small+rrf+w=0.25+c=60` | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=60; 25% semantic / 75% lexical; depth 100 |
| `cross-minilm-l6+pool=baseline+d=100` | Local cross-encoder reranking | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large candidate retrieval | MiniLM-L6 cross-encoder raw logits; reorder current baseline top100 only, preserve tail |
| `hybrid-gte-small+rrf+w=0.25+c=10` | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=10; 25% semantic / 75% lexical; depth 100 |
| `hybrid-bge-small+rrf+w=0.25+c=10` | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=10; 25% semantic / 75% lexical; depth 100 |
| `oai-field+text=title75+d=100` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 75% / abstract 25%; pure cosine; reorder baseline top100 only, preserve tail |
| `cross-minilm-l6+pool=union100+w=1` | Local cross-encoder reranking | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large candidate retrieval | MiniLM-L6 cross-encoder raw logits; union of lexical100, semantic100 and baseline100 |
| `bm25+stop+exact+stems+authors+title2x` | Keyword search | BM25: exact + stems; remove stopwords; authors; title x2; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stop+exact+stems+title2x` | Keyword search | BM25: exact + stems; remove stopwords; title x2; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+exact+stems+authors` | Keyword search | BM25: exact + stems; authors; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stop+exact+stems+authors` | Keyword search | BM25: exact + stems; remove stopwords; authors; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+exact+stems+title2x` | Keyword search | BM25: exact + stems; title x2; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+exact+stems+authors+title2x` | Keyword search | BM25: exact + stems; authors; title x2; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+exact+stems` | Keyword search | BM25: exact + stems; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stop+exact+stems` | Keyword search | BM25: exact + stems; remove stopwords; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stop+authors+title2x` | Keyword search | BM25: exact terms; remove stopwords; authors; title x2; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+authors` | Keyword search | BM25: exact terms; authors; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stop+authors` | Keyword search | BM25: exact terms; remove stopwords; authors; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stop+title2x` | Keyword search | BM25: exact terms; remove stopwords; title x2; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+authors+title2x` | Keyword search | BM25: exact terms; authors; title x2; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stop+stem+authors+title2x` | Keyword search | BM25: stems only; remove stopwords; authors; title x2; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+title2x` | Keyword search | BM25: exact terms; title x2; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stop+stem+authors` | Keyword search | BM25: stems only; remove stopwords; authors; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stop` | Keyword search | BM25: exact terms; remove stopwords; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stem+authors+title2x` | Keyword search | BM25: stems only; authors; title x2; k1=1.2, b=0.75 | None | BM25 score |
| `bm25-baseline` | Keyword search | BM25: exact terms; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stop+stem+title2x` | Keyword search | BM25: stems only; remove stopwords; title x2; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stem+title2x` | Keyword search | BM25: stems only; title x2; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stem+authors` | Keyword search | BM25: stems only; authors; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stop+stem` | Keyword search | BM25: stems only; remove stopwords; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stem` | Keyword search | BM25: stems only; k1=1.2, b=0.75 | None | BM25 score |
| `dense-minilm` | Embedding search | None | MiniLM-L6-v2 | Cosine similarity |
| `dense-e5-small` | Embedding search | None | E5-small | Cosine similarity |

</details>

## Report inventory (separate historical scopes)

- [baseline-promotion-dev/report.json](../baseline-promotion-dev/report.json) — historical report/configuration; original scope
- [cross-encoder-dev/report.json](../cross-encoder-dev/report.json) — historical report/configuration; original scope
- [cross-encoder-dev/report.md](../cross-encoder-dev/report.md) — historical report/configuration; original scope
- [dev/tuning/bm25+exact+stems+authors+title2x.json](../dev/tuning/bm25%2Bexact%2Bstems%2Bauthors%2Btitle2x.json) — BM25 tuning, source-paper objective
- [dev/tuning/bm25+exact+stems+authors.json](../dev/tuning/bm25%2Bexact%2Bstems%2Bauthors.json) — BM25 tuning, source-paper objective
- [dev/tuning/bm25+stop+exact+stems+authors+title2x.json](../dev/tuning/bm25%2Bstop%2Bexact%2Bstems%2Bauthors%2Btitle2x.json) — BM25 tuning, source-paper objective
- [embedding-pilot/report.md](../embedding-pilot/report.md) — reduced-corpus embedding pilot, separate scope
- [failure-analysis/report.md](../failure-analysis/report.md) — historical report/configuration; original scope
- [field-score-dev/report.json](../field-score-dev/report.json) — historical report/configuration; original scope
- [field-score-dev/report.md](../field-score-dev/report.md) — historical report/configuration; original scope
- [field-signal-dev/report.json](../field-signal-dev/report.json) — historical report/configuration; original scope
- [field-signal-dev/report.md](../field-signal-dev/report.md) — historical report/configuration; original scope
- [fusion-dev/configs.json](../fusion-dev/configs.json) — historical report/configuration; original scope
- [fusion-dev/report.json](../fusion-dev/report.json) — historical report/configuration; original scope
- [fusion-dev/report.md](../fusion-dev/report.md) — historical report/configuration; original scope
- [fusion-review-dev/report.json](../fusion-review-dev/report.json) — historical report/configuration; original scope
- [fusion-review-dev/report.md](../fusion-review-dev/report.md) — historical report/configuration; original scope
- [graded-dev/report.md](../graded-dev/report.md) — historical report/configuration; original scope
- [llm-reranker-pilot/report.json](../llm-reranker-pilot/report.json) — historical report/configuration; original scope
- [llm-reranker-pilot/report.md](../llm-reranker-pilot/report.md) — historical report/configuration; original scope
- [llm-score-blend/report.json](../llm-score-blend/report.json) — historical report/configuration; original scope
- [llm-score-blend/report.md](../llm-score-blend/report.md) — historical report/configuration; original scope
- [llm-score-dev100/report.json](../llm-score-dev100/report.json) — historical report/configuration; original scope
- [llm-score-dev100/report.md](../llm-score-dev100/report.md) — historical report/configuration; original scope
- [llm-score-pass2/report.json](../llm-score-pass2/report.json) — historical report/configuration; original scope
- [llm-score-pass2/report.md](../llm-score-pass2/report.md) — historical report/configuration; original scope
- [llm-score-pilot/judge-fill/report.json](../llm-score-pilot/judge-fill/report.json) — historical report/configuration; original scope
- [llm-score-pilot/judge-fill/report.md](../llm-score-pilot/judge-fill/report.md) — historical report/configuration; original scope
- [llm-score-pilot/report.json](../llm-score-pilot/report.json) — historical report/configuration; original scope
- [llm-score-pilot/report.md](../llm-score-pilot/report.md) — historical report/configuration; original scope
- [llm-score-pilot/safeguard/report.json](../llm-score-pilot/safeguard/report.json) — historical report/configuration; original scope
- [llm-score-pilot/safeguard/report.md](../llm-score-pilot/safeguard/report.md) — historical report/configuration; original scope
- [llm-score-repeat/report.json](../llm-score-repeat/report.json) — historical report/configuration; original scope
- [llm-score-repeat/report.md](../llm-score-repeat/report.md) — historical report/configuration; original scope
- [openai-field-dev/report.json](../openai-field-dev/report.json) — historical report/configuration; original scope
- [openai-field-dev/report.md](../openai-field-dev/report.md) — historical report/configuration; original scope
- [openai-field-hybrid-dev/report.json](../openai-field-hybrid-dev/report.json) — historical report/configuration; original scope
- [openai-field-hybrid-dev/report.md](../openai-field-hybrid-dev/report.md) — historical report/configuration; original scope
- [openai-field-recovery-dev/report.json](../openai-field-recovery-dev/report.json) — historical report/configuration; original scope
- [openai-field-recovery-dev/report.md](../openai-field-recovery-dev/report.md) — historical report/configuration; original scope
- [openai-field-review-dev/report.json](../openai-field-review-dev/report.json) — historical report/configuration; original scope
- [openai-field-review-dev/report.md](../openai-field-review-dev/report.md) — historical report/configuration; original scope
- [rank-score-dev/configs.json](../rank-score-dev/configs.json) — historical report/configuration; original scope
- [rank-score-dev/report.json](../rank-score-dev/report.json) — historical report/configuration; original scope
- [rank-score-dev/report.md](../rank-score-dev/report.md) — historical report/configuration; original scope
- [refinement-dev/configs.json](../refinement-dev/configs.json) — historical report/configuration; original scope
- [refinement-dev/report.md](../refinement-dev/report.md) — historical report/configuration; original scope
- [score-candidate-review-dev/report.json](../score-candidate-review-dev/report.json) — historical report/configuration; original scope
- [score-candidate-review-dev/report.md](../score-candidate-review-dev/report.md) — historical report/configuration; original scope
- [score-fusion-dev/configs.json](../score-fusion-dev/configs.json) — historical report/configuration; original scope
- [score-fusion-dev/report.json](../score-fusion-dev/report.json) — historical report/configuration; original scope
- [score-fusion-dev/report.md](../score-fusion-dev/report.md) — historical report/configuration; original scope
- [shortlist-score-dev/configs.json](../shortlist-score-dev/configs.json) — historical report/configuration; original scope
- [shortlist-score-dev/report.json](../shortlist-score-dev/report.json) — historical report/configuration; original scope
- [shortlist-score-dev/report.md](../shortlist-score-dev/report.md) — historical report/configuration; original scope
