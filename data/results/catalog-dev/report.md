# Dev leaderboard: all-experiment catalog

176 distinct saved systems; 100 dev queries; current corpus: 23,304 papers. **Working baseline: `fusion-shortlist+a=1+d=500`**. **Success score = nDCG@10**, descending using unrounded means; exact ties use stable system ID. Only fully judged runs with defined nDCG receive positions. The baseline stays at its actual position, not pinned first. Provisional runs appear separately, unranked. A leaderboard lead is not automatic baseline promotion.

**Technique guide:** Embedding identifies the vector model; Ranker / fusion identifies how retrieval results are ordered, not a separate LLM reranker. Tuned BM25 means exact terms + stems, authors, title x2, k1=0.8, b=0.75, no stopword removal. RRF uses reciprocal ranks; score fusion combines normalized BM25/cosine values. Depth is candidates per retriever, not final results. Frozen aliases can represent identical rankings under different experiment IDs. Readable names are presentation only: original IDs and files are preserved below.

All graded scores are recomputed from the **same immutable `score-fusion-dev/labels.json`**, including its 100 frozen human overrides. **Revised shared ideal-DCG denominator:** approved additive expansion preserves all 3190 original labels and adds 104 labels. Every system is rescored against this expanded denominator; original reports remain unchanged and their nDCG values must not be mixed with these revised scores. Other report scores/label pools and later judge-cache or workbook changes are NOT combined. Linear-gain nDCG@10 uses that shared ideal DCG; undefined queries are excluded only from nDCG (n shown). P@10 counts grades ≥1 with denominator 10. Unjudged gains count as zero. judged@10 is the judged fraction of returned results; short/missing lists still fail the full top-10 coverage gate.

**PROVISIONAL** means a dev top-10 position is missing or unjudged: source-paper MRR/recall remain valid on the full dev denominator (missing queries score zero), but graded scores are lower-bound diagnostics, not winner evidence. Paired nDCG against the CURRENT working baseline is withheld unless BOTH runs have every dev top-10 position judged. Intervals are exploratory query bootstraps conditional on these labels, not judge accuracy; no multiple-testing correction or test-query scoring. Known-item MRR is source-paper MRR on that type only.

**Snapshot/corpus caveat:** these are saved rankings, not fresh retrieval. Current corpus and dev-query fingerprints, the frozen label SHA256, ranking fingerprints, and all duplicate paths are recorded in the machine report. Older runs may not record a corpus fingerprint; matching paper IDs cannot prove identical build snapshots. Reduced-corpus embedding pilots are a separate scope, never scorecard rows. Costs/latencies are not estimated or assigned zero: only actually saved `.info.json` metadata is preserved per system, with its original timing scope. Historical reports retain their original labels, denominators, and controls.

### Ranked leaderboard (fully judged)

| Rank | System | Keyword retrieval | Embedding | Ranker / fusion | Status | Success: nDCG@10 (n) | P@10 | judged@10 | Source MRR@10 | R@1 | R@5 | R@10 | R@20 | Known-item MRR@10 | Δ nDCG vs working baseline [95% CI] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | OpenAI-large paraphrase recovery | Tuned BM25 including authors/title2x | OpenAI text-embedding-3-large | 25% lexical / 75% semantic; 10% title / 90% abstract; 0% combined-text anchor; candidate-max normalization; reorder baseline top10 only, preserve tail | covered | 0.7214 (100) | 0.689 | 1.000 | 0.698 | 0.620 | 0.790 | 0.860 | 0.890 | 0.980 | +0.004 [-0.001, +0.009] |
| 2 | OpenAI-large paraphrase recovery | Tuned BM25 including authors/title2x | OpenAI text-embedding-3-large | 25% lexical / 75% semantic; abstract only; 0% combined-text anchor; candidate-max normalization; reorder baseline top10 only, preserve tail | covered | 0.7210 (100) | 0.689 | 1.000 | 0.680 | 0.580 | 0.790 | 0.860 | 0.890 | 0.980 | +0.003 [-0.002, +0.009] |
| 3 | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 25% / abstract 75%; max-score25% lexical / 75% field semantic; reorder baseline top10 only, preserve tail | covered | 0.7204 (100) | 0.689 | 1.000 | 0.705 | 0.640 | 0.780 | 0.860 | 0.890 | 0.980 | +0.003 [-0.002, +0.008] |
| 4 | OpenAI-large paraphrase recovery | Tuned BM25 including authors/title2x | OpenAI text-embedding-3-large | 25% lexical / 75% semantic; 25% title / 75% abstract; 0% combined-text anchor; candidate-max normalization; reorder baseline top10 only, preserve tail | covered | 0.7204 (100) | 0.689 | 1.000 | 0.705 | 0.640 | 0.780 | 0.860 | 0.890 | 0.980 | +0.003 [-0.002, +0.008] |
| 5 | OpenAI-large paraphrase recovery | Tuned BM25 including authors/title2x | OpenAI text-embedding-3-large | 25% lexical / 75% semantic; 25% title / 75% abstract; 50% combined-text anchor; candidate-max normalization; reorder baseline top10 only, preserve tail | covered | 0.7202 (100) | 0.689 | 1.000 | 0.694 | 0.610 | 0.800 | 0.860 | 0.890 | 0.980 | +0.003 [-0.000, +0.006] |
| 6 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Max-normalized scores; 75% semantic / 25% lexical; depth 500 | covered | 0.7197 (100) | 0.697 | 1.000 | 0.692 | 0.610 | 0.800 | 0.820 | 0.840 | 0.980 | +0.002 [-0.007, +0.012] |
| 7 | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | concatenated title + abstract control; max-score25% lexical / 75% field semantic; reorder baseline top100 only, preserve tail | covered | 0.7192 (100) | 0.697 | 1.000 | 0.692 | 0.610 | 0.800 | 0.820 | 0.840 | 0.980 | +0.002 [-0.008, +0.012] |
| 8 | OpenAI-large paraphrase recovery | Tuned BM25 including authors/title2x | OpenAI text-embedding-3-large | 25% lexical / 75% semantic; 25% title / 75% abstract; 75% combined-text anchor; candidate-max normalization; reorder baseline top10 only, preserve tail | covered | 0.7191 (100) | 0.689 | 1.000 | 0.704 | 0.620 | 0.800 | 0.860 | 0.890 | 0.980 | +0.002 [-0.001, +0.004] |
| 9 | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | concatenated title + abstract control; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 | covered | 0.7176 (100) | 0.689 | 1.000 | 0.697 | 0.610 | 0.800 | 0.860 | 0.890 | 0.980 | +0.000 [+0.000, +0.000] |
| 10 | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | separate title 25% / abstract 75%; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 | covered | 0.7176 (100) | 0.689 | 1.000 | 0.697 | 0.610 | 0.800 | 0.860 | 0.890 | 0.980 | +0.000 [+0.000, +0.000] |
| 11 | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | separate title 50% / abstract 50%; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 | covered | 0.7176 (100) | 0.689 | 1.000 | 0.697 | 0.610 | 0.800 | 0.860 | 0.890 | 0.980 | +0.000 [+0.000, +0.000] |
| 12 | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | separate title 75% / abstract 25%; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 | covered | 0.7176 (100) | 0.689 | 1.000 | 0.697 | 0.610 | 0.800 | 0.860 | 0.890 | 0.980 | +0.000 [+0.000, +0.000] |
| 13 | **Fixed-shortlist score ordering (WORKING BASELINE)** | Tuned BM25 | OpenAI text-embedding-3-large | RRF55%/c30/depth100 selects top10; order by max-score 75% semantic / 25% lexical at depth 500; preserve tail | covered | 0.7176 (100) | 0.689 | 1.000 | 0.697 | 0.610 | 0.800 | 0.860 | 0.890 | 0.980 | withheld: working baseline itself |
| 14 | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | concatenated title + abstract control; max-score25% lexical / 75% field semantic; reorder baseline top10 only, preserve tail | covered | 0.7175 (100) | 0.689 | 1.000 | 0.697 | 0.610 | 0.800 | 0.860 | 0.890 | 0.980 | -0.000 [-0.000, +0.000] |
| 15 | OpenAI-large paraphrase recovery | Tuned BM25 including authors/title2x | OpenAI text-embedding-3-large | 25% lexical / 75% semantic; combined title + abstract; 100% combined-text anchor; candidate-max normalization; reorder baseline top10 only, preserve tail | covered | 0.7175 (100) | 0.689 | 1.000 | 0.697 | 0.610 | 0.800 | 0.860 | 0.890 | 0.980 | -0.000 [-0.000, +0.000] |
| 16 | Fixed-shortlist score ordering | Tuned BM25 | OpenAI text-embedding-3-large | RRF55%/c30/depth100 selects top10; order by max-score 75% semantic / 25% lexical at depth 100; preserve tail | covered | 0.7138 (100) | 0.689 | 1.000 | 0.674 | 0.590 | 0.770 | 0.860 | 0.890 | 0.980 | -0.004 [-0.010, +0.001] |
| 17 | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 50% / abstract 50%; max-score25% lexical / 75% field semantic; reorder baseline top10 only, preserve tail | covered | 0.7126 (100) | 0.689 | 1.000 | 0.679 | 0.600 | 0.760 | 0.860 | 0.890 | 0.980 | -0.005 [-0.014, +0.003] |
| 18 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Max-normalized scores; 75% semantic / 25% lexical; depth 100 | covered | 0.7111 (100) | 0.686 | 1.000 | 0.668 | 0.590 | 0.760 | 0.820 | 0.870 | 0.980 | -0.006 [-0.018, +0.005] |
| 19 | Rank + score interpolation | Tuned BM25 | OpenAI text-embedding-3-large | 75% max-score75% + 25% normalized RRF55%/c30/d100; score depth 100 | covered | 0.7108 (100) | 0.691 | 1.000 | 0.665 | 0.580 | 0.760 | 0.840 | 0.870 | 0.980 | -0.007 [-0.018, +0.004] |
| 20 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 60% semantic / 40% lexical; depth 100 | covered | 0.7097 (100) | 0.700 | 1.000 | 0.630 | 0.530 | 0.760 | 0.830 | 0.870 | 0.953 | -0.008 [-0.019, +0.005] |
| 21 | Fixed-shortlist score ordering | Tuned BM25 | OpenAI text-embedding-3-large | 50% max-score75% + 50% normalized RRF55%/c30/d100; score depth 500; reorder baseline top10 only, preserve tail | covered | 0.7071 (100) | 0.689 | 1.000 | 0.652 | 0.550 | 0.770 | 0.860 | 0.890 | 0.980 | -0.010 [-0.017, -0.004] |
| 22 | Rank + score interpolation | Tuned BM25 | OpenAI text-embedding-3-large | 25% max-score75% + 75% normalized RRF55%/c30/d100; score depth 100 | covered | 0.7071 (100) | 0.692 | 1.000 | 0.646 | 0.550 | 0.770 | 0.850 | 0.880 | 0.980 | -0.010 [-0.019, -0.002] |
| 23 | Fixed-shortlist score ordering | Tuned BM25 | OpenAI text-embedding-3-large | 50% max-score75% + 50% normalized RRF55%/c30/d100; score depth 100; reorder baseline top10 only, preserve tail | covered | 0.7070 (100) | 0.689 | 1.000 | 0.650 | 0.550 | 0.770 | 0.860 | 0.890 | 0.980 | -0.011 [-0.018, -0.004] |
| 24 | Rank + score interpolation | Tuned BM25 | OpenAI text-embedding-3-large | 50% max-score75% + 50% normalized RRF55%/c30/d100; score depth 500 | covered | 0.7067 (100) | 0.690 | 1.000 | 0.650 | 0.550 | 0.770 | 0.850 | 0.870 | 0.980 | -0.011 [-0.021, -0.002] |
| 25 | Rank + score interpolation | Tuned BM25 | OpenAI text-embedding-3-large | 50% max-score75% + 50% normalized RRF55%/c30/d100; score depth 100 | covered | 0.7066 (100) | 0.691 | 1.000 | 0.649 | 0.550 | 0.770 | 0.850 | 0.880 | 0.980 | -0.011 [-0.020, -0.001] |
| 26 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 55% semantic / 45% lexical; depth 100 | covered | 0.7064 (100) | 0.689 | 1.000 | 0.646 | 0.550 | 0.760 | 0.860 | 0.890 | 0.980 | -0.011 [-0.019, -0.004] |
| 27 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 65% semantic / 35% lexical; depth 100 | covered | 0.7063 (100) | 0.694 | 1.000 | 0.626 | 0.520 | 0.770 | 0.840 | 0.890 | 0.953 | -0.011 [-0.024, +0.001] |
| 28 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 55% semantic / 45% lexical; depth 200 | covered | 0.7058 (100) | 0.691 | 1.000 | 0.639 | 0.540 | 0.750 | 0.840 | 0.880 | 0.980 | -0.012 [-0.021, -0.003] |
| 29 | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | concatenated title + abstract control; pure semantic field score; reorder baseline top10 only, preserve tail | covered | 0.7057 (100) | 0.689 | 1.000 | 0.622 | 0.510 | 0.780 | 0.860 | 0.890 | 0.801 | -0.012 [-0.024, -0.000] |
| 30 | Lexical field-score ablation | Independent BM25 fields; 10% authors | OpenAI large candidate retrieval | separate title 25% / abstract 75%; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 | covered | 0.7056 (100) | 0.686 | 1.000 | 0.670 | 0.580 | 0.810 | 0.850 | 0.880 | 0.980 | -0.012 [-0.023, -0.002] |
| 31 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 75% semantic / 25% lexical; depth 100 | covered | 0.7052 (100) | 0.690 | 1.000 | 0.618 | 0.520 | 0.770 | 0.840 | 0.890 | 0.943 | -0.012 [-0.025, -0.000] |
| 32 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 70% semantic / 30% lexical; depth 100 | covered | 0.7051 (100) | 0.687 | 1.000 | 0.627 | 0.530 | 0.760 | 0.840 | 0.890 | 0.950 | -0.012 [-0.023, -0.001] |
| 33 | Rank + score interpolation | Tuned BM25 | OpenAI text-embedding-3-large | 25% max-score75% + 75% normalized RRF55%/c30/d100; score depth 500 | covered | 0.7050 (100) | 0.690 | 1.000 | 0.646 | 0.550 | 0.760 | 0.850 | 0.880 | 0.980 | -0.013 [-0.021, -0.005] |
| 34 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30 + 10% top-1 bonus; 55% semantic / 45% lexical; depth 100 | covered | 0.7048 (100) | 0.689 | 1.000 | 0.653 | 0.560 | 0.790 | 0.850 | 0.890 | 0.980 | -0.013 [-0.020, -0.005] |
| 35 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 60% semantic / 40% lexical; depth 100 | covered | 0.7041 (100) | 0.688 | 1.000 | 0.636 | 0.530 | 0.790 | 0.860 | 0.890 | 0.953 | -0.013 [-0.023, -0.005] |
| 36 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 55% semantic / 45% lexical; depth 100 | covered | 0.7039 (100) | 0.695 | 1.000 | 0.627 | 0.530 | 0.740 | 0.820 | 0.870 | 0.960 | -0.014 [-0.027, +0.000] |
| 37 | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | separate title 25% / abstract 75%; pure semantic field score; reorder baseline top10 only, preserve tail | covered | 0.7038 (100) | 0.689 | 1.000 | 0.621 | 0.510 | 0.780 | 0.860 | 0.890 | 0.781 | -0.014 [-0.026, -0.002] |
| 38 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 55% semantic / 45% lexical; depth 500 | covered | 0.7035 (100) | 0.690 | 1.000 | 0.640 | 0.540 | 0.760 | 0.840 | 0.880 | 0.980 | -0.014 [-0.024, -0.004] |
| 39 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 65% semantic / 35% lexical; depth 100 | covered | 0.7031 (100) | 0.685 | 1.000 | 0.640 | 0.540 | 0.780 | 0.850 | 0.890 | 0.953 | -0.014 [-0.026, -0.004] |
| 40 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Min-max-normalized scores; 55% semantic / 45% lexical; depth 500 | covered | 0.7030 (100) | 0.674 | 1.000 | 0.684 | 0.590 | 0.790 | 0.840 | 0.880 | 0.980 | -0.015 [-0.025, -0.005] |
| 41 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 75% semantic / 25% lexical; depth 100 | covered | 0.7028 (100) | 0.685 | 1.000 | 0.624 | 0.530 | 0.750 | 0.840 | 0.890 | 0.947 | -0.015 [-0.026, -0.003] |
| 42 | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 75% / abstract 25%; max-score25% lexical / 75% field semantic; reorder baseline top10 only, preserve tail | covered | 0.7025 (100) | 0.689 | 1.000 | 0.655 | 0.570 | 0.760 | 0.860 | 0.890 | 0.953 | -0.015 [-0.027, -0.004] |
| 43 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30 + 25% top-1 bonus; 55% semantic / 45% lexical; depth 100 | covered | 0.7022 (100) | 0.687 | 1.000 | 0.653 | 0.560 | 0.790 | 0.850 | 0.890 | 0.980 | -0.015 [-0.024, -0.006] |
| 44 | Local cross-encoder reranking | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large candidate retrieval | MiniLM-L6 cross-encoder raw logits; reorder current baseline top10 only, preserve tail | covered | 0.7021 (100) | 0.689 | 1.000 | 0.659 | 0.570 | 0.790 | 0.860 | 0.890 | 0.933 | -0.015 [-0.028, -0.004] |
| 45 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 75% semantic / 25% lexical; depth 100 | covered | 0.7019 (100) | 0.680 | 1.000 | 0.630 | 0.540 | 0.770 | 0.840 | 0.890 | 0.943 | -0.016 [-0.027, -0.004] |
| 46 | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 25% / abstract 75%; pure cosine; reorder baseline top10 only, preserve tail | covered | 0.7011 (100) | 0.689 | 1.000 | 0.630 | 0.520 | 0.740 | 0.860 | 0.890 | 0.873 | -0.016 [-0.029, -0.004] |
| 47 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Max-normalized scores; 55% semantic / 45% lexical; depth 100 | covered | 0.6994 (100) | 0.686 | 1.000 | 0.656 | 0.570 | 0.760 | 0.790 | 0.860 | 0.980 | -0.018 [-0.034, -0.001] |
| 48 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 70% semantic / 30% lexical; depth 100 | covered | 0.6969 (100) | 0.676 | 1.000 | 0.642 | 0.540 | 0.800 | 0.860 | 0.900 | 0.950 | -0.021 [-0.035, -0.007] |
| 49 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 75% semantic / 25% lexical; depth 50 | covered | 0.6963 (100) | 0.686 | 1.000 | 0.617 | 0.520 | 0.760 | 0.840 | 0.890 | 0.947 | -0.021 [-0.036, -0.008] |
| 50 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Min-max-normalized scores; 75% semantic / 25% lexical; depth 500 | covered | 0.6962 (100) | 0.668 | 1.000 | 0.684 | 0.600 | 0.810 | 0.860 | 0.900 | 0.960 | -0.021 [-0.039, -0.006] |
| 51 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 50% semantic / 50% lexical; depth 100 | covered | 0.6953 (100) | 0.689 | 1.000 | 0.626 | 0.540 | 0.740 | 0.780 | 0.870 | 0.960 | -0.022 [-0.039, -0.005] |
| 52 | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | separate title 50% / abstract 50%; pure semantic field score; reorder baseline top10 only, preserve tail | covered | 0.6952 (100) | 0.689 | 1.000 | 0.599 | 0.480 | 0.790 | 0.860 | 0.890 | 0.830 | -0.022 [-0.035, -0.010] |
| 53 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 75% semantic / 25% lexical; depth 50 | covered | 0.6946 (100) | 0.676 | 1.000 | 0.626 | 0.530 | 0.760 | 0.850 | 0.890 | 0.947 | -0.023 [-0.037, -0.010] |
| 54 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 75% semantic / 25% lexical; depth 100 | covered | 0.6937 (100) | 0.668 | 1.000 | 0.644 | 0.550 | 0.810 | 0.870 | 0.900 | 0.943 | -0.024 [-0.040, -0.008] |
| 55 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 50% semantic / 50% lexical; depth 100 | covered | 0.6924 (100) | 0.689 | 1.000 | 0.627 | 0.540 | 0.740 | 0.770 | 0.840 | 0.960 | -0.025 [-0.042, -0.008] |
| 56 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 50% semantic / 50% lexical; depth 100 | covered | 0.6917 (100) | 0.673 | 1.000 | 0.646 | 0.560 | 0.740 | 0.840 | 0.890 | 0.980 | -0.026 [-0.039, -0.013] |
| 57 | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | concatenated title + abstract control; pure cosine; reorder baseline top10 only, preserve tail | covered | 0.6903 (100) | 0.689 | 1.000 | 0.609 | 0.500 | 0.750 | 0.860 | 0.890 | 0.802 | -0.027 [-0.040, -0.015] |
| 58 | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 50% / abstract 50%; pure cosine; reorder baseline top10 only, preserve tail | covered | 0.6903 (100) | 0.689 | 1.000 | 0.604 | 0.480 | 0.760 | 0.860 | 0.890 | 0.830 | -0.027 [-0.043, -0.013] |
| 59 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 50% semantic / 50% lexical; depth 100 | covered | 0.6902 (100) | 0.684 | 1.000 | 0.627 | 0.540 | 0.740 | 0.790 | 0.880 | 0.960 | -0.027 [-0.042, -0.012] |
| 60 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Max-normalized scores; 55% semantic / 45% lexical; depth 500 | covered | 0.6874 (100) | 0.670 | 1.000 | 0.657 | 0.570 | 0.760 | 0.810 | 0.840 | 0.980 | -0.030 [-0.049, -0.012] |
| 61 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 60% semantic / 40% lexical; depth 100 | covered | 0.6868 (100) | 0.661 | 1.000 | 0.655 | 0.540 | 0.820 | 0.870 | 0.890 | 0.953 | -0.031 [-0.047, -0.016] |
| 62 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 75% semantic / 25% lexical; depth 50 | covered | 0.6861 (100) | 0.664 | 1.000 | 0.632 | 0.530 | 0.780 | 0.870 | 0.890 | 0.947 | -0.031 [-0.049, -0.014] |
| 63 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Min-max-normalized scores; 55% semantic / 45% lexical; depth 100 | covered | 0.6853 (100) | 0.647 | 1.000 | 0.690 | 0.590 | 0.820 | 0.850 | 0.900 | 0.980 | -0.032 [-0.048, -0.018] |
| 64 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 65% semantic / 35% lexical; depth 100 | covered | 0.6843 (100) | 0.662 | 1.000 | 0.648 | 0.540 | 0.800 | 0.870 | 0.890 | 0.953 | -0.033 [-0.052, -0.017] |
| 65 | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 75% / abstract 25%; pure cosine; reorder baseline top10 only, preserve tail | covered | 0.6808 (100) | 0.689 | 1.000 | 0.572 | 0.440 | 0.740 | 0.860 | 0.890 | 0.798 | -0.037 [-0.052, -0.022] |
| 66 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 70% semantic / 30% lexical; depth 100 | covered | 0.6804 (100) | 0.656 | 1.000 | 0.647 | 0.540 | 0.790 | 0.860 | 0.900 | 0.950 | -0.037 [-0.057, -0.020] |
| 67 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 55% semantic / 45% lexical; depth 100 | covered | 0.6803 (100) | 0.652 | 1.000 | 0.658 | 0.550 | 0.820 | 0.860 | 0.900 | 0.980 | -0.037 [-0.052, -0.024] |
| 68 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Min-max-normalized scores; 75% semantic / 25% lexical; depth 100 | covered | 0.6791 (100) | 0.651 | 1.000 | 0.671 | 0.590 | 0.810 | 0.860 | 0.900 | 0.950 | -0.039 [-0.059, -0.019] |
| 69 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 50% semantic / 50% lexical; depth 50 | covered | 0.6781 (100) | 0.660 | 1.000 | 0.630 | 0.540 | 0.740 | 0.830 | 0.890 | 0.960 | -0.039 [-0.055, -0.024] |
| 70 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 75% semantic / 25% lexical; depth 20 | covered | 0.6775 (100) | 0.658 | 1.000 | 0.625 | 0.520 | 0.760 | 0.850 | 0.880 | 0.947 | -0.040 [-0.061, -0.021] |
| 71 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 75% semantic / 25% lexical; depth 20 | covered | 0.6775 (100) | 0.658 | 1.000 | 0.625 | 0.520 | 0.760 | 0.850 | 0.880 | 0.947 | -0.040 [-0.061, -0.021] |
| 72 | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | separate title 75% / abstract 25%; pure semantic field score; reorder baseline top10 only, preserve tail | covered | 0.6767 (100) | 0.689 | 1.000 | 0.527 | 0.390 | 0.760 | 0.860 | 0.890 | 0.791 | -0.041 [-0.056, -0.026] |
| 73 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 50% semantic / 50% lexical; depth 50 | covered | 0.6764 (100) | 0.659 | 1.000 | 0.630 | 0.540 | 0.740 | 0.820 | 0.890 | 0.960 | -0.041 [-0.057, -0.026] |
| 74 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 75% semantic / 25% lexical; depth 100 | covered | 0.6762 (100) | 0.651 | 1.000 | 0.654 | 0.560 | 0.770 | 0.860 | 0.900 | 0.940 | -0.041 [-0.063, -0.022] |
| 75 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 75% semantic / 25% lexical; depth 50 | covered | 0.6752 (100) | 0.648 | 1.000 | 0.658 | 0.570 | 0.770 | 0.860 | 0.890 | 0.940 | -0.042 [-0.064, -0.022] |
| 76 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Max-normalized scores; 35% semantic / 65% lexical; depth 100 | covered | 0.6742 (100) | 0.670 | 1.000 | 0.636 | 0.560 | 0.730 | 0.750 | 0.780 | 1.000 | -0.043 [-0.065, -0.023] |
| 77 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 50% semantic / 50% lexical; depth 50 | covered | 0.6729 (100) | 0.652 | 1.000 | 0.633 | 0.540 | 0.750 | 0.830 | 0.900 | 0.960 | -0.045 [-0.061, -0.030] |
| 78 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 75% semantic / 25% lexical; depth 20 | covered | 0.6728 (100) | 0.645 | 1.000 | 0.658 | 0.570 | 0.760 | 0.850 | 0.880 | 0.947 | -0.045 [-0.067, -0.025] |
| 79 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 75% semantic / 25% lexical; depth 20 | covered | 0.6661 (100) | 0.636 | 1.000 | 0.642 | 0.550 | 0.760 | 0.820 | 0.890 | 0.933 | -0.052 [-0.076, -0.029] |
| 80 | Original hybrid control | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 50% semantic / 50% lexical; depth 100 | covered | 0.6604 (100) | 0.633 | 1.000 | 0.653 | 0.560 | 0.800 | 0.840 | 0.900 | 0.980 | -0.057 [-0.074, -0.041] |
| 81 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 50% semantic / 50% lexical; depth 100 | covered | 0.6604 (100) | 0.633 | 1.000 | 0.653 | 0.560 | 0.800 | 0.840 | 0.900 | 0.980 | -0.057 [-0.074, -0.041] |
| 82 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 50% semantic / 50% lexical; depth 100 | covered | 0.6604 (100) | 0.633 | 1.000 | 0.653 | 0.560 | 0.800 | 0.840 | 0.900 | 0.980 | -0.057 [-0.074, -0.041] |
| 83 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 25% semantic / 75% lexical; depth 100 | covered | 0.6594 (100) | 0.646 | 1.000 | 0.630 | 0.560 | 0.720 | 0.750 | 0.790 | 0.980 | -0.058 [-0.082, -0.034] |
| 84 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 50% semantic / 50% lexical; depth 50 | covered | 0.6565 (100) | 0.631 | 1.000 | 0.645 | 0.550 | 0.780 | 0.840 | 0.900 | 0.980 | -0.061 [-0.078, -0.045] |
| 85 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 25% semantic / 75% lexical; depth 50 | covered | 0.6469 (100) | 0.623 | 1.000 | 0.630 | 0.560 | 0.710 | 0.750 | 0.770 | 0.980 | -0.071 [-0.096, -0.045] |
| 86 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Min-max-normalized scores; 35% semantic / 65% lexical; depth 500 | covered | 0.6449 (100) | 0.626 | 1.000 | 0.631 | 0.540 | 0.750 | 0.790 | 0.830 | 1.000 | -0.073 [-0.098, -0.048] |
| 87 | Embedding search | None | OpenAI text-embedding-3-large | Cosine similarity | covered | 0.6438 (100) | 0.637 | 1.000 | 0.599 | 0.500 | 0.740 | 0.820 | 0.880 | 0.793 | -0.074 [-0.101, -0.048] |
| 88 | Semantic-only fusion control | None (0% weight) | OpenAI text-embedding-3-large | RRF c=10; depth 100 | covered | 0.6438 (100) | 0.637 | 1.000 | 0.599 | 0.500 | 0.740 | 0.820 | 0.880 | 0.793 | -0.074 [-0.101, -0.048] |
| 89 | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | concatenated title + abstract control; pure cosine; reorder baseline top100 only, preserve tail | covered | 0.6438 (100) | 0.637 | 1.000 | 0.599 | 0.500 | 0.740 | 0.820 | 0.880 | 0.793 | -0.074 [-0.101, -0.048] |
| 90 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 50% semantic / 50% lexical; depth 20 | covered | 0.6437 (100) | 0.615 | 1.000 | 0.639 | 0.540 | 0.800 | 0.840 | 0.890 | 0.980 | -0.074 [-0.094, -0.054] |
| 91 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 50% semantic / 50% lexical; depth 20 | covered | 0.6435 (100) | 0.619 | 1.000 | 0.627 | 0.530 | 0.780 | 0.840 | 0.890 | 0.960 | -0.074 [-0.095, -0.054] |
| 92 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 50% semantic / 50% lexical; depth 20 | covered | 0.6435 (100) | 0.619 | 1.000 | 0.628 | 0.530 | 0.780 | 0.840 | 0.890 | 0.960 | -0.074 [-0.095, -0.054] |
| 93 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Max-normalized scores; 35% semantic / 65% lexical; depth 500 | covered | 0.6373 (100) | 0.635 | 1.000 | 0.619 | 0.540 | 0.720 | 0.770 | 0.800 | 1.000 | -0.080 [-0.110, -0.052] |
| 94 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 25% semantic / 75% lexical; depth 100 | covered | 0.6371 (100) | 0.614 | 1.000 | 0.636 | 0.570 | 0.720 | 0.740 | 0.770 | 0.980 | -0.080 [-0.108, -0.054] |
| 95 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 25% semantic / 75% lexical; depth 100 | covered | 0.6332 (100) | 0.618 | 1.000 | 0.626 | 0.560 | 0.720 | 0.740 | 0.780 | 0.980 | -0.084 [-0.112, -0.057] |
| 96 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 50% semantic / 50% lexical; depth 20 | covered | 0.6321 (100) | 0.605 | 1.000 | 0.635 | 0.530 | 0.800 | 0.840 | 0.890 | 0.960 | -0.085 [-0.107, -0.066] |
| 97 | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=10; 50% semantic / 50% lexical; depth 100 | covered | 0.6312 (100) | 0.611 | 1.000 | 0.635 | 0.540 | 0.760 | 0.800 | 0.840 | 0.973 | -0.086 [-0.116, -0.056] |
| 98 | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=10; 50% semantic / 50% lexical; depth 100 | covered | 0.6280 (100) | 0.614 | 1.000 | 0.602 | 0.500 | 0.770 | 0.790 | 0.850 | 0.930 | -0.090 [-0.123, -0.061] |
| 99 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 25% semantic / 75% lexical; depth 50 | covered | 0.6262 (100) | 0.604 | 1.000 | 0.626 | 0.560 | 0.710 | 0.740 | 0.770 | 0.980 | -0.091 [-0.119, -0.064] |
| 100 | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Min-max-normalized scores; 35% semantic / 65% lexical; depth 100 | covered | 0.6100 (100) | 0.577 | 1.000 | 0.626 | 0.540 | 0.720 | 0.790 | 0.860 | 1.000 | -0.108 [-0.135, -0.083] |
| 101 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 25% semantic / 75% lexical; depth 50 | covered | 0.5892 (100) | 0.557 | 1.000 | 0.618 | 0.560 | 0.690 | 0.720 | 0.750 | 0.980 | -0.128 [-0.162, -0.094] |
| 102 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 25% semantic / 75% lexical; depth 20 | covered | 0.5825 (100) | 0.547 | 1.000 | 0.614 | 0.560 | 0.690 | 0.700 | 0.710 | 0.980 | -0.135 [-0.169, -0.099] |
| 103 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 25% semantic / 75% lexical; depth 20 | covered | 0.5825 (100) | 0.547 | 1.000 | 0.614 | 0.560 | 0.690 | 0.700 | 0.710 | 0.980 | -0.135 [-0.169, -0.099] |
| 104 | Embedding search | None | GTE-small | Cosine similarity | covered | 0.5811 (100) | 0.581 | 1.000 | 0.525 | 0.430 | 0.660 | 0.710 | 0.780 | 0.633 | -0.136 [-0.175, -0.101] |
| 105 | Embedding search | None | BGE-small | Cosine similarity | covered | 0.5763 (100) | 0.584 | 1.000 | 0.506 | 0.420 | 0.600 | 0.700 | 0.790 | 0.667 | -0.141 [-0.180, -0.107] |
| 106 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 25% semantic / 75% lexical; depth 100 | covered | 0.5693 (100) | 0.557 | 1.000 | 0.602 | 0.540 | 0.680 | 0.730 | 0.780 | 0.980 | -0.148 [-0.183, -0.111] |
| 107 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 25% semantic / 75% lexical; depth 50 | covered | 0.5682 (100) | 0.555 | 1.000 | 0.603 | 0.540 | 0.680 | 0.730 | 0.760 | 0.980 | -0.149 [-0.185, -0.113] |
| 108 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 25% semantic / 75% lexical; depth 20 | covered | 0.5580 (100) | 0.538 | 1.000 | 0.605 | 0.550 | 0.680 | 0.710 | 0.710 | 0.980 | -0.160 [-0.196, -0.122] |
| 109 | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 25% semantic / 75% lexical; depth 20 | covered | 0.5504 (100) | 0.526 | 1.000 | 0.614 | 0.560 | 0.680 | 0.710 | 0.870 | 0.980 | -0.167 [-0.204, -0.129] |
| 110 | Keyword search | BM25: exact + stems; authors; title x2; k1=0.8,b=0.75 | None | BM25 score | covered | 0.5187 (100) | 0.512 | 1.000 | 0.569 | 0.510 | 0.660 | 0.710 | 0.710 | 1.000 | -0.199 [-0.239, -0.160] |
| 111 | Lexical-only fusion control | Tuned BM25 | None (0% weight) | RRF c=10; depth 100 | covered | 0.5187 (100) | 0.512 | 1.000 | 0.569 | 0.510 | 0.660 | 0.710 | 0.710 | 1.000 | -0.199 [-0.239, -0.160] |

### Unranked diagnostics (incomplete judgments or undefined nDCG)

Sorted by diagnostic nDCG only; these runs are not eligible to win.

| Rank | System | Keyword retrieval | Embedding | Ranker / fusion | Status | Success: nDCG@10 (n) | P@10 | judged@10 | Source MRR@10 | R@1 | R@5 | R@10 | R@20 | Known-item MRR@10 | Δ nDCG vs working baseline [95% CI] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| - | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 25% / abstract 75%; max-score25% lexical / 75% field semantic; reorder baseline top100 only, preserve tail | PROVISIONAL | 0.7184 (100) | 0.687 | 0.962 | 0.701 | 0.640 | 0.780 | 0.830 | 0.840 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Rank + score interpolation | Tuned BM25 | OpenAI text-embedding-3-large | 75% max-score75% + 25% normalized RRF55%/c30/d100; score depth 500 | PROVISIONAL | 0.7168 (100) | 0.696 | 0.999 | 0.678 | 0.590 | 0.800 | 0.840 | 0.860 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 70% semantic / 30% lexical; depth 100 | PROVISIONAL | 0.7073 (100) | 0.695 | 0.997 | 0.618 | 0.520 | 0.740 | 0.840 | 0.870 | 0.947 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 60% semantic / 40% lexical; depth 100 | PROVISIONAL | 0.7055 (100) | 0.693 | 0.999 | 0.627 | 0.530 | 0.750 | 0.810 | 0.870 | 0.953 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 65% semantic / 35% lexical; depth 100 | PROVISIONAL | 0.7041 (100) | 0.693 | 0.997 | 0.621 | 0.520 | 0.750 | 0.820 | 0.870 | 0.953 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 55% semantic / 45% lexical; depth 100 | PROVISIONAL | 0.7022 (100) | 0.693 | 0.998 | 0.620 | 0.520 | 0.740 | 0.800 | 0.860 | 0.960 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Lexical field-score ablation | Independent BM25 fields; 10% authors | OpenAI large candidate retrieval | separate title 50% / abstract 50%; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 | PROVISIONAL | 0.6960 (100) | 0.682 | 0.999 | 0.647 | 0.530 | 0.810 | 0.850 | 0.870 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| - | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 50% / abstract 50%; max-score25% lexical / 75% field semantic; reorder baseline top100 only, preserve tail | PROVISIONAL | 0.6935 (100) | 0.665 | 0.937 | 0.677 | 0.600 | 0.770 | 0.820 | 0.840 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Lexical field-score ablation | Independent BM25 fields; 10% authors | OpenAI large candidate retrieval | separate title 75% / abstract 25%; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 | PROVISIONAL | 0.6800 (100) | 0.674 | 0.999 | 0.606 | 0.490 | 0.800 | 0.840 | 0.880 | 0.960 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Local cross-encoder reranking | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large candidate retrieval | 50% cross-encoder rank + 50% baseline rank, RRF c30; union of lexical100, semantic100 and baseline100 | PROVISIONAL | 0.6777 (100) | 0.645 | 0.934 | 0.687 | 0.610 | 0.780 | 0.840 | 0.850 | 0.960 | withheld: both runs must have all dev top-10 positions present and judged |
| - | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 75% / abstract 25%; max-score25% lexical / 75% field semantic; reorder baseline top100 only, preserve tail | PROVISIONAL | 0.6533 (100) | 0.615 | 0.884 | 0.656 | 0.580 | 0.760 | 0.810 | 0.820 | 0.953 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=60; 75% semantic / 25% lexical; depth 100 | PROVISIONAL | 0.6450 (100) | 0.627 | 0.949 | 0.586 | 0.490 | 0.720 | 0.770 | 0.840 | 0.806 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=100; 75% semantic / 25% lexical; depth 100 | PROVISIONAL | 0.6405 (100) | 0.619 | 0.910 | 0.578 | 0.480 | 0.690 | 0.770 | 0.830 | 0.805 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | GTE-small | Linear rank fusion; 75% semantic / 25% lexical; depth 100 | PROVISIONAL | 0.6379 (100) | 0.621 | 0.947 | 0.570 | 0.460 | 0.710 | 0.760 | 0.830 | 0.801 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Local cross-encoder reranking | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large candidate retrieval | MiniLM-L6 cross-encoder raw logits; reorder current baseline top30 only, preserve tail | PROVISIONAL | 0.6332 (100) | 0.613 | 0.904 | 0.620 | 0.540 | 0.710 | 0.790 | 0.850 | 0.907 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=60; 50% semantic / 50% lexical; depth 100 | PROVISIONAL | 0.6328 (100) | 0.598 | 0.876 | 0.603 | 0.510 | 0.710 | 0.770 | 0.810 | 0.920 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | GTE-small | Linear rank fusion; 50% semantic / 50% lexical; depth 100 | PROVISIONAL | 0.6310 (100) | 0.603 | 0.885 | 0.603 | 0.510 | 0.720 | 0.760 | 0.810 | 0.920 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=60; 50% semantic / 50% lexical; depth 100 | PROVISIONAL | 0.6306 (100) | 0.600 | 0.877 | 0.581 | 0.490 | 0.710 | 0.780 | 0.820 | 0.892 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | BGE-small | Linear rank fusion; 75% semantic / 25% lexical; depth 100 | PROVISIONAL | 0.6290 (100) | 0.612 | 0.939 | 0.559 | 0.470 | 0.690 | 0.740 | 0.830 | 0.856 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=100; 50% semantic / 50% lexical; depth 100 | PROVISIONAL | 0.6287 (100) | 0.591 | 0.854 | 0.601 | 0.510 | 0.720 | 0.770 | 0.810 | 0.920 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=60; 75% semantic / 25% lexical; depth 100 | PROVISIONAL | 0.6275 (100) | 0.614 | 0.942 | 0.561 | 0.480 | 0.700 | 0.750 | 0.840 | 0.856 | withheld: both runs must have all dev top-10 positions present and judged |
| - | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 25% / abstract 75%; pure cosine; reorder baseline top100 only, preserve tail | PROVISIONAL | 0.6275 (100) | 0.577 | 0.856 | 0.618 | 0.520 | 0.740 | 0.810 | 0.890 | 0.866 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | BGE-small | Linear rank fusion; 50% semantic / 50% lexical; depth 100 | PROVISIONAL | 0.6272 (100) | 0.601 | 0.889 | 0.569 | 0.470 | 0.690 | 0.790 | 0.830 | 0.891 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=100; 50% semantic / 50% lexical; depth 100 | PROVISIONAL | 0.6266 (100) | 0.594 | 0.857 | 0.578 | 0.490 | 0.720 | 0.770 | 0.820 | 0.891 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=100; 75% semantic / 25% lexical; depth 100 | PROVISIONAL | 0.6258 (100) | 0.604 | 0.894 | 0.563 | 0.480 | 0.690 | 0.760 | 0.850 | 0.856 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=10; 75% semantic / 25% lexical; depth 100 | PROVISIONAL | 0.6166 (100) | 0.607 | 0.997 | 0.576 | 0.480 | 0.710 | 0.760 | 0.850 | 0.766 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=100; 25% semantic / 75% lexical; depth 100 | PROVISIONAL | 0.6152 (100) | 0.591 | 0.920 | 0.591 | 0.490 | 0.710 | 0.750 | 0.770 | 0.960 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=100; 25% semantic / 75% lexical; depth 100 | PROVISIONAL | 0.6150 (100) | 0.591 | 0.918 | 0.590 | 0.500 | 0.710 | 0.740 | 0.770 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=10; 75% semantic / 25% lexical; depth 100 | PROVISIONAL | 0.6124 (100) | 0.616 | 0.997 | 0.552 | 0.470 | 0.650 | 0.760 | 0.840 | 0.797 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | BGE-small | Linear rank fusion; 25% semantic / 75% lexical; depth 100 | PROVISIONAL | 0.6064 (100) | 0.583 | 0.956 | 0.587 | 0.490 | 0.710 | 0.740 | 0.750 | 0.948 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=60; 25% semantic / 75% lexical; depth 100 | PROVISIONAL | 0.6062 (100) | 0.586 | 0.957 | 0.588 | 0.500 | 0.720 | 0.730 | 0.760 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | GTE-small | Linear rank fusion; 25% semantic / 75% lexical; depth 100 | PROVISIONAL | 0.6056 (100) | 0.584 | 0.956 | 0.588 | 0.490 | 0.720 | 0.740 | 0.760 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=60; 25% semantic / 75% lexical; depth 100 | PROVISIONAL | 0.6046 (100) | 0.587 | 0.959 | 0.585 | 0.480 | 0.720 | 0.740 | 0.760 | 0.960 | withheld: both runs must have all dev top-10 positions present and judged |
| - | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 50% / abstract 50%; pure cosine; reorder baseline top100 only, preserve tail | PROVISIONAL | 0.5980 (100) | 0.549 | 0.799 | 0.599 | 0.480 | 0.780 | 0.810 | 0.840 | 0.821 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Local cross-encoder reranking | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large candidate retrieval | MiniLM-L6 cross-encoder raw logits; reorder current baseline top100 only, preserve tail | PROVISIONAL | 0.5639 (100) | 0.511 | 0.733 | 0.605 | 0.540 | 0.690 | 0.740 | 0.820 | 0.905 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=10; 25% semantic / 75% lexical; depth 100 | PROVISIONAL | 0.5591 (100) | 0.547 | 0.999 | 0.579 | 0.500 | 0.670 | 0.720 | 0.770 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=10; 25% semantic / 75% lexical; depth 100 | PROVISIONAL | 0.5568 (100) | 0.545 | 0.996 | 0.581 | 0.490 | 0.680 | 0.730 | 0.760 | 0.960 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Local cross-encoder reranking | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large candidate retrieval | MiniLM-L6 cross-encoder raw logits; union of lexical100, semantic100 and baseline100 | PROVISIONAL | 0.5448 (100) | 0.487 | 0.686 | 0.604 | 0.540 | 0.690 | 0.740 | 0.790 | 0.905 | withheld: both runs must have all dev top-10 positions present and judged |
| - | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 75% / abstract 25%; pure cosine; reorder baseline top100 only, preserve tail | PROVISIONAL | 0.5421 (100) | 0.497 | 0.723 | 0.541 | 0.440 | 0.690 | 0.790 | 0.800 | 0.765 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact + stems; remove stopwords; authors; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.5217 (100) | 0.515 | 0.936 | 0.559 | 0.500 | 0.650 | 0.700 | 0.730 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact + stems; remove stopwords; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.5189 (100) | 0.515 | 0.912 | 0.544 | 0.470 | 0.660 | 0.710 | 0.730 | 0.940 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact + stems; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.5186 (100) | 0.518 | 0.934 | 0.545 | 0.470 | 0.670 | 0.710 | 0.720 | 0.940 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact + stems; authors; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.5185 (100) | 0.509 | 0.937 | 0.557 | 0.510 | 0.650 | 0.700 | 0.730 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact + stems; remove stopwords; authors; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.5180 (100) | 0.513 | 0.918 | 0.547 | 0.490 | 0.650 | 0.700 | 0.730 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact + stems; authors; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.5158 (100) | 0.508 | 0.956 | 0.560 | 0.500 | 0.670 | 0.710 | 0.730 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact + stems; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.5123 (100) | 0.507 | 0.911 | 0.521 | 0.440 | 0.650 | 0.700 | 0.730 | 0.873 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact + stems; remove stopwords; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.5115 (100) | 0.508 | 0.894 | 0.516 | 0.430 | 0.650 | 0.710 | 0.730 | 0.873 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact terms; remove stopwords; authors; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4971 (100) | 0.478 | 0.849 | 0.530 | 0.470 | 0.610 | 0.680 | 0.700 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact terms; authors; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4969 (100) | 0.482 | 0.854 | 0.523 | 0.470 | 0.600 | 0.670 | 0.710 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact terms; remove stopwords; authors; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4958 (100) | 0.481 | 0.831 | 0.525 | 0.470 | 0.610 | 0.680 | 0.700 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact terms; remove stopwords; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4957 (100) | 0.482 | 0.831 | 0.519 | 0.450 | 0.610 | 0.690 | 0.700 | 0.940 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact terms; authors; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4931 (100) | 0.476 | 0.866 | 0.534 | 0.480 | 0.620 | 0.670 | 0.700 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact terms; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4900 (100) | 0.478 | 0.845 | 0.517 | 0.450 | 0.610 | 0.670 | 0.700 | 0.940 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: stems only; remove stopwords; authors; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4895 (100) | 0.456 | 0.779 | 0.549 | 0.490 | 0.620 | 0.710 | 0.720 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact terms; remove stopwords; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4880 (100) | 0.475 | 0.809 | 0.501 | 0.430 | 0.600 | 0.680 | 0.700 | 0.907 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: exact terms; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4875 (100) | 0.472 | 0.823 | 0.501 | 0.430 | 0.610 | 0.670 | 0.700 | 0.907 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: stems only; authors; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4857 (100) | 0.452 | 0.792 | 0.549 | 0.490 | 0.630 | 0.700 | 0.730 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: stems only; remove stopwords; authors; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4853 (100) | 0.448 | 0.760 | 0.550 | 0.490 | 0.610 | 0.690 | 0.730 | 0.960 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: stems only; remove stopwords; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4841 (100) | 0.452 | 0.755 | 0.515 | 0.430 | 0.620 | 0.720 | 0.730 | 0.830 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: stems only; title x2; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4784 (100) | 0.446 | 0.763 | 0.512 | 0.430 | 0.630 | 0.720 | 0.730 | 0.830 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: stems only; authors; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4774 (100) | 0.437 | 0.762 | 0.544 | 0.480 | 0.630 | 0.690 | 0.730 | 0.960 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: stems only; remove stopwords; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4739 (100) | 0.441 | 0.742 | 0.492 | 0.400 | 0.590 | 0.700 | 0.730 | 0.746 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Keyword search | BM25: stems only; k1=1.2, b=0.75 | None | BM25 score | PROVISIONAL | 0.4699 (100) | 0.433 | 0.749 | 0.492 | 0.400 | 0.610 | 0.700 | 0.730 | 0.748 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Embedding search | None | MiniLM-L6-v2 | Cosine similarity | PROVISIONAL | 0.4399 (100) | 0.380 | 0.545 | 0.407 | 0.330 | 0.530 | 0.590 | 0.680 | 0.549 | withheld: both runs must have all dev top-10 positions present and judged |
| - | Embedding search | None | E5-small | Cosine similarity | PROVISIONAL | 0.4234 (100) | 0.359 | 0.516 | 0.485 | 0.390 | 0.610 | 0.690 | 0.750 | 0.626 | withheld: both runs must have all dev top-10 positions present and judged |

## Every run by query type

| System | Type | Queries | nDCG@10 (n) | P@10 | judged@10 | Source MRR@10 | R@1 | R@5 | R@10 | R@20 |
|---|---|---|---|---|---|---|---|---|---|---|
| `baseline-original-equal-rrf-c10-d100` | keyword | 25 | 0.696 (25) | 0.692 | 1.000 | 0.717 | 0.600 | 0.920 | 0.960 | 1.000 |
| `baseline-original-equal-rrf-c10-d100` | question | 25 | 0.662 (25) | 0.660 | 1.000 | 0.553 | 0.440 | 0.760 | 0.760 | 0.800 |
| `baseline-original-equal-rrf-c10-d100` | paraphrase | 25 | 0.591 (25) | 0.576 | 1.000 | 0.364 | 0.240 | 0.520 | 0.640 | 0.800 |
| `baseline-original-equal-rrf-c10-d100` | known_item | 25 | 0.692 (25) | 0.604 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `bm25+authors` | keyword | 25 | 0.587 (25) | 0.572 | 0.904 | 0.589 | 0.480 | 0.760 | 0.920 | 0.920 |
| `bm25+authors` | question | 25 | 0.405 (25) | 0.416 | 0.820 | 0.408 | 0.320 | 0.520 | 0.560 | 0.680 |
| `bm25+authors` | paraphrase | 25 | 0.340 (25) | 0.376 | 0.812 | 0.096 | 0.080 | 0.120 | 0.200 | 0.240 |
| `bm25+authors` | known_item | 25 | 0.656 (25) | 0.564 | 0.880 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `bm25+authors+title2x` | keyword | 25 | 0.577 (25) | 0.552 | 0.896 | 0.611 | 0.480 | 0.880 | 0.920 | 0.920 |
| `bm25+authors+title2x` | question | 25 | 0.401 (25) | 0.416 | 0.844 | 0.427 | 0.360 | 0.480 | 0.560 | 0.680 |
| `bm25+authors+title2x` | paraphrase | 25 | 0.330 (25) | 0.364 | 0.820 | 0.096 | 0.080 | 0.120 | 0.200 | 0.200 |
| `bm25+authors+title2x` | known_item | 25 | 0.665 (25) | 0.572 | 0.904 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `bm25+exact+stems` | keyword | 25 | 0.598 (25) | 0.584 | 0.944 | 0.650 | 0.560 | 0.840 | 0.920 | 0.920 |
| `bm25+exact+stems` | question | 25 | 0.460 (25) | 0.488 | 0.948 | 0.434 | 0.360 | 0.520 | 0.600 | 0.720 |
| `bm25+exact+stems` | paraphrase | 25 | 0.354 (25) | 0.392 | 0.920 | 0.125 | 0.080 | 0.240 | 0.280 | 0.280 |
| `bm25+exact+stems` | known_item | 25 | 0.637 (25) | 0.564 | 0.832 | 0.873 | 0.760 | 1.000 | 1.000 | 1.000 |
| `bm25+exact+stems+authors` | keyword | 25 | 0.602 (25) | 0.592 | 0.948 | 0.648 | 0.560 | 0.840 | 0.920 | 0.920 |
| `bm25+exact+stems+authors` | question | 25 | 0.454 (25) | 0.468 | 0.940 | 0.454 | 0.400 | 0.520 | 0.600 | 0.720 |
| `bm25+exact+stems+authors` | paraphrase | 25 | 0.356 (25) | 0.400 | 0.936 | 0.127 | 0.080 | 0.240 | 0.280 | 0.280 |
| `bm25+exact+stems+authors` | known_item | 25 | 0.663 (25) | 0.576 | 0.924 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `bm25+exact+stems+authors+title2x` | keyword | 25 | 0.594 (25) | 0.588 | 0.960 | 0.657 | 0.520 | 0.920 | 0.920 | 0.920 |
| `bm25+exact+stems+authors+title2x` | question | 25 | 0.440 (25) | 0.456 | 0.964 | 0.459 | 0.400 | 0.560 | 0.640 | 0.720 |
| `bm25+exact+stems+authors+title2x` | paraphrase | 25 | 0.360 (25) | 0.404 | 0.952 | 0.124 | 0.080 | 0.200 | 0.280 | 0.280 |
| `bm25+exact+stems+authors+title2x` | known_item | 25 | 0.669 (25) | 0.584 | 0.948 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | keyword | 25 | 0.610 (25) | 0.596 | 1.000 | 0.710 | 0.600 | 0.880 | 0.920 | 0.920 |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | question | 25 | 0.434 (25) | 0.452 | 1.000 | 0.432 | 0.360 | 0.520 | 0.640 | 0.640 |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | paraphrase | 25 | 0.365 (25) | 0.412 | 1.000 | 0.132 | 0.080 | 0.240 | 0.280 | 0.280 |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | known_item | 25 | 0.666 (25) | 0.588 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `bm25+exact+stems+title2x` | keyword | 25 | 0.597 (25) | 0.592 | 0.960 | 0.657 | 0.520 | 0.920 | 0.920 | 0.920 |
| `bm25+exact+stems+title2x` | question | 25 | 0.456 (25) | 0.480 | 0.960 | 0.459 | 0.400 | 0.560 | 0.640 | 0.680 |
| `bm25+exact+stems+title2x` | paraphrase | 25 | 0.361 (25) | 0.400 | 0.940 | 0.125 | 0.080 | 0.200 | 0.280 | 0.280 |
| `bm25+exact+stems+title2x` | known_item | 25 | 0.661 (25) | 0.600 | 0.876 | 0.940 | 0.880 | 1.000 | 1.000 | 1.000 |
| `bm25+stem` | keyword | 25 | 0.573 (25) | 0.528 | 0.848 | 0.665 | 0.600 | 0.760 | 0.840 | 0.920 |
| `bm25+stem` | question | 25 | 0.403 (25) | 0.384 | 0.732 | 0.388 | 0.280 | 0.520 | 0.680 | 0.680 |
| `bm25+stem` | paraphrase | 25 | 0.305 (25) | 0.308 | 0.664 | 0.166 | 0.120 | 0.240 | 0.320 | 0.320 |
| `bm25+stem` | known_item | 25 | 0.599 (25) | 0.512 | 0.752 | 0.748 | 0.600 | 0.920 | 0.960 | 1.000 |
| `bm25+stem+authors` | keyword | 25 | 0.577 (25) | 0.540 | 0.844 | 0.676 | 0.600 | 0.760 | 0.880 | 0.920 |
| `bm25+stem+authors` | question | 25 | 0.391 (25) | 0.372 | 0.712 | 0.377 | 0.280 | 0.520 | 0.600 | 0.680 |
| `bm25+stem+authors` | paraphrase | 25 | 0.299 (25) | 0.304 | 0.664 | 0.161 | 0.120 | 0.240 | 0.280 | 0.320 |
| `bm25+stem+authors` | known_item | 25 | 0.642 (25) | 0.532 | 0.828 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `bm25+stem+authors+title2x` | keyword | 25 | 0.582 (25) | 0.548 | 0.860 | 0.653 | 0.560 | 0.800 | 0.880 | 0.920 |
| `bm25+stem+authors+title2x` | question | 25 | 0.400 (25) | 0.388 | 0.752 | 0.384 | 0.280 | 0.560 | 0.640 | 0.680 |
| `bm25+stem+authors+title2x` | paraphrase | 25 | 0.310 (25) | 0.324 | 0.696 | 0.178 | 0.160 | 0.160 | 0.280 | 0.320 |
| `bm25+stem+authors+title2x` | known_item | 25 | 0.651 (25) | 0.548 | 0.860 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `bm25+stem+title2x` | keyword | 25 | 0.585 (25) | 0.552 | 0.868 | 0.650 | 0.560 | 0.800 | 0.920 | 0.920 |
| `bm25+stem+title2x` | question | 25 | 0.400 (25) | 0.384 | 0.736 | 0.385 | 0.280 | 0.560 | 0.640 | 0.680 |
| `bm25+stem+title2x` | paraphrase | 25 | 0.304 (25) | 0.312 | 0.676 | 0.182 | 0.160 | 0.160 | 0.320 | 0.320 |
| `bm25+stem+title2x` | known_item | 25 | 0.624 (25) | 0.536 | 0.772 | 0.830 | 0.720 | 1.000 | 1.000 | 1.000 |
| `bm25+stop` | keyword | 25 | 0.577 (25) | 0.560 | 0.892 | 0.592 | 0.480 | 0.800 | 0.920 | 0.920 |
| `bm25+stop` | question | 25 | 0.403 (25) | 0.416 | 0.776 | 0.410 | 0.320 | 0.480 | 0.600 | 0.680 |
| `bm25+stop` | paraphrase | 25 | 0.335 (25) | 0.376 | 0.776 | 0.097 | 0.080 | 0.120 | 0.200 | 0.200 |
| `bm25+stop` | known_item | 25 | 0.637 (25) | 0.548 | 0.792 | 0.907 | 0.840 | 1.000 | 1.000 | 1.000 |
| `bm25+stop+authors` | keyword | 25 | 0.586 (25) | 0.572 | 0.896 | 0.595 | 0.480 | 0.800 | 0.920 | 0.920 |
| `bm25+stop+authors` | question | 25 | 0.407 (25) | 0.420 | 0.792 | 0.415 | 0.320 | 0.520 | 0.640 | 0.680 |
| `bm25+stop+authors` | paraphrase | 25 | 0.336 (25) | 0.376 | 0.768 | 0.092 | 0.080 | 0.120 | 0.160 | 0.200 |
| `bm25+stop+authors` | known_item | 25 | 0.654 (25) | 0.556 | 0.868 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `bm25+stop+authors+title2x` | keyword | 25 | 0.580 (25) | 0.560 | 0.896 | 0.613 | 0.480 | 0.840 | 0.920 | 0.920 |
| `bm25+stop+authors+title2x` | question | 25 | 0.409 (25) | 0.416 | 0.804 | 0.436 | 0.360 | 0.480 | 0.640 | 0.680 |
| `bm25+stop+authors+title2x` | paraphrase | 25 | 0.323 (25) | 0.352 | 0.788 | 0.072 | 0.040 | 0.120 | 0.160 | 0.200 |
| `bm25+stop+authors+title2x` | known_item | 25 | 0.675 (25) | 0.584 | 0.908 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `bm25+stop+exact+stems` | keyword | 25 | 0.584 (25) | 0.572 | 0.940 | 0.629 | 0.520 | 0.880 | 0.920 | 0.920 |
| `bm25+stop+exact+stems` | question | 25 | 0.461 (25) | 0.484 | 0.916 | 0.431 | 0.360 | 0.480 | 0.640 | 0.720 |
| `bm25+stop+exact+stems` | paraphrase | 25 | 0.365 (25) | 0.412 | 0.892 | 0.129 | 0.080 | 0.240 | 0.280 | 0.280 |
| `bm25+stop+exact+stems` | known_item | 25 | 0.636 (25) | 0.564 | 0.828 | 0.873 | 0.760 | 1.000 | 1.000 | 1.000 |
| `bm25+stop+exact+stems+authors` | keyword | 25 | 0.591 (25) | 0.584 | 0.940 | 0.630 | 0.520 | 0.840 | 0.920 | 0.920 |
| `bm25+stop+exact+stems+authors` | question | 25 | 0.456 (25) | 0.476 | 0.920 | 0.432 | 0.360 | 0.520 | 0.640 | 0.720 |
| `bm25+stop+exact+stems+authors` | paraphrase | 25 | 0.360 (25) | 0.416 | 0.896 | 0.128 | 0.080 | 0.240 | 0.240 | 0.280 |
| `bm25+stop+exact+stems+authors` | known_item | 25 | 0.665 (25) | 0.576 | 0.916 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `bm25+stop+exact+stems+authors+title2x` | keyword | 25 | 0.596 (25) | 0.588 | 0.952 | 0.663 | 0.520 | 0.920 | 0.920 | 0.920 |
| `bm25+stop+exact+stems+authors+title2x` | question | 25 | 0.459 (25) | 0.472 | 0.928 | 0.452 | 0.400 | 0.480 | 0.640 | 0.720 |
| `bm25+stop+exact+stems+authors+title2x` | paraphrase | 25 | 0.359 (25) | 0.412 | 0.920 | 0.122 | 0.080 | 0.200 | 0.240 | 0.280 |
| `bm25+stop+exact+stems+authors+title2x` | known_item | 25 | 0.673 (25) | 0.588 | 0.944 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `bm25+stop+exact+stems+title2x` | keyword | 25 | 0.592 (25) | 0.584 | 0.948 | 0.657 | 0.520 | 0.920 | 0.920 | 0.920 |
| `bm25+stop+exact+stems+title2x` | question | 25 | 0.459 (25) | 0.468 | 0.924 | 0.453 | 0.400 | 0.520 | 0.640 | 0.720 |
| `bm25+stop+exact+stems+title2x` | paraphrase | 25 | 0.362 (25) | 0.408 | 0.904 | 0.125 | 0.080 | 0.200 | 0.280 | 0.280 |
| `bm25+stop+exact+stems+title2x` | known_item | 25 | 0.662 (25) | 0.600 | 0.872 | 0.940 | 0.880 | 1.000 | 1.000 | 1.000 |
| `bm25+stop+stem` | keyword | 25 | 0.577 (25) | 0.540 | 0.848 | 0.649 | 0.560 | 0.760 | 0.880 | 0.920 |
| `bm25+stop+stem` | question | 25 | 0.414 (25) | 0.392 | 0.708 | 0.409 | 0.320 | 0.480 | 0.640 | 0.680 |
| `bm25+stop+stem` | paraphrase | 25 | 0.309 (25) | 0.320 | 0.660 | 0.164 | 0.120 | 0.200 | 0.320 | 0.320 |
| `bm25+stop+stem` | known_item | 25 | 0.596 (25) | 0.512 | 0.752 | 0.746 | 0.600 | 0.920 | 0.960 | 1.000 |
| `bm25+stop+stem+authors` | keyword | 25 | 0.577 (25) | 0.540 | 0.844 | 0.652 | 0.560 | 0.760 | 0.840 | 0.920 |
| `bm25+stop+stem+authors` | question | 25 | 0.419 (25) | 0.396 | 0.708 | 0.430 | 0.360 | 0.480 | 0.640 | 0.680 |
| `bm25+stop+stem+authors` | paraphrase | 25 | 0.299 (25) | 0.312 | 0.644 | 0.159 | 0.120 | 0.200 | 0.280 | 0.320 |
| `bm25+stop+stem+authors` | known_item | 25 | 0.647 (25) | 0.544 | 0.844 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `bm25+stop+stem+authors+title2x` | keyword | 25 | 0.582 (25) | 0.548 | 0.860 | 0.651 | 0.560 | 0.800 | 0.920 | 0.920 |
| `bm25+stop+stem+authors+title2x` | question | 25 | 0.418 (25) | 0.400 | 0.724 | 0.407 | 0.320 | 0.520 | 0.640 | 0.680 |
| `bm25+stop+stem+authors+title2x` | paraphrase | 25 | 0.302 (25) | 0.324 | 0.668 | 0.157 | 0.120 | 0.160 | 0.280 | 0.280 |
| `bm25+stop+stem+authors+title2x` | known_item | 25 | 0.657 (25) | 0.552 | 0.864 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `bm25+stop+stem+title2x` | keyword | 25 | 0.584 (25) | 0.552 | 0.868 | 0.660 | 0.560 | 0.800 | 0.920 | 0.920 |
| `bm25+stop+stem+title2x` | question | 25 | 0.421 (25) | 0.400 | 0.716 | 0.407 | 0.320 | 0.520 | 0.640 | 0.680 |
| `bm25+stop+stem+title2x` | paraphrase | 25 | 0.302 (25) | 0.312 | 0.660 | 0.161 | 0.120 | 0.160 | 0.320 | 0.320 |
| `bm25+stop+stem+title2x` | known_item | 25 | 0.629 (25) | 0.544 | 0.776 | 0.830 | 0.720 | 1.000 | 1.000 | 1.000 |
| `bm25+stop+title2x` | keyword | 25 | 0.579 (25) | 0.564 | 0.900 | 0.606 | 0.480 | 0.840 | 0.920 | 0.920 |
| `bm25+stop+title2x` | question | 25 | 0.417 (25) | 0.424 | 0.804 | 0.435 | 0.360 | 0.480 | 0.640 | 0.680 |
| `bm25+stop+title2x` | paraphrase | 25 | 0.328 (25) | 0.364 | 0.800 | 0.096 | 0.080 | 0.120 | 0.200 | 0.200 |
| `bm25+stop+title2x` | known_item | 25 | 0.658 (25) | 0.576 | 0.820 | 0.940 | 0.880 | 1.000 | 1.000 | 1.000 |
| `bm25+title2x` | keyword | 25 | 0.577 (25) | 0.560 | 0.904 | 0.603 | 0.480 | 0.840 | 0.920 | 0.920 |
| `bm25+title2x` | question | 25 | 0.401 (25) | 0.412 | 0.836 | 0.427 | 0.360 | 0.480 | 0.560 | 0.680 |
| `bm25+title2x` | paraphrase | 25 | 0.324 (25) | 0.360 | 0.812 | 0.097 | 0.080 | 0.120 | 0.200 | 0.200 |
| `bm25+title2x` | known_item | 25 | 0.659 (25) | 0.580 | 0.828 | 0.940 | 0.880 | 1.000 | 1.000 | 1.000 |
| `bm25-baseline` | keyword | 25 | 0.576 (25) | 0.560 | 0.896 | 0.593 | 0.480 | 0.800 | 0.920 | 0.920 |
| `bm25-baseline` | question | 25 | 0.408 (25) | 0.420 | 0.812 | 0.408 | 0.320 | 0.520 | 0.560 | 0.680 |
| `bm25-baseline` | paraphrase | 25 | 0.335 (25) | 0.368 | 0.796 | 0.097 | 0.080 | 0.120 | 0.200 | 0.200 |
| `bm25-baseline` | known_item | 25 | 0.631 (25) | 0.540 | 0.788 | 0.907 | 0.840 | 1.000 | 1.000 | 1.000 |
| `cross-minilm-l6+pool=baseline+d=10` | keyword | 25 | 0.745 (25) | 0.744 | 1.000 | 0.763 | 0.680 | 0.880 | 0.960 | 0.960 |
| `cross-minilm-l6+pool=baseline+d=10` | question | 25 | 0.711 (25) | 0.740 | 1.000 | 0.538 | 0.440 | 0.720 | 0.760 | 0.800 |
| `cross-minilm-l6+pool=baseline+d=10` | paraphrase | 25 | 0.642 (25) | 0.648 | 1.000 | 0.402 | 0.280 | 0.560 | 0.720 | 0.800 |
| `cross-minilm-l6+pool=baseline+d=10` | known_item | 25 | 0.710 (25) | 0.624 | 1.000 | 0.933 | 0.880 | 1.000 | 1.000 | 1.000 |
| `cross-minilm-l6+pool=baseline+d=100` | keyword | 25 | 0.609 (25) | 0.528 | 0.724 | 0.764 | 0.680 | 0.840 | 0.920 | 0.920 |
| `cross-minilm-l6+pool=baseline+d=100` | question | 25 | 0.565 (25) | 0.532 | 0.736 | 0.493 | 0.440 | 0.600 | 0.640 | 0.800 |
| `cross-minilm-l6+pool=baseline+d=100` | paraphrase | 25 | 0.425 (25) | 0.436 | 0.684 | 0.256 | 0.200 | 0.360 | 0.400 | 0.560 |
| `cross-minilm-l6+pool=baseline+d=100` | known_item | 25 | 0.657 (25) | 0.548 | 0.788 | 0.905 | 0.840 | 0.960 | 1.000 | 1.000 |
| `cross-minilm-l6+pool=baseline+d=30` | keyword | 25 | 0.658 (25) | 0.612 | 0.868 | 0.768 | 0.680 | 0.880 | 0.920 | 0.960 |
| `cross-minilm-l6+pool=baseline+d=30` | question | 25 | 0.654 (25) | 0.668 | 0.932 | 0.518 | 0.440 | 0.600 | 0.720 | 0.760 |
| `cross-minilm-l6+pool=baseline+d=30` | paraphrase | 25 | 0.527 (25) | 0.560 | 0.908 | 0.287 | 0.200 | 0.400 | 0.520 | 0.680 |
| `cross-minilm-l6+pool=baseline+d=30` | known_item | 25 | 0.695 (25) | 0.612 | 0.908 | 0.907 | 0.840 | 0.960 | 1.000 | 1.000 |
| `cross-minilm-l6+pool=union100+w=0.5` | keyword | 25 | 0.692 (25) | 0.652 | 0.912 | 0.774 | 0.680 | 0.880 | 0.960 | 0.960 |
| `cross-minilm-l6+pool=union100+w=0.5` | question | 25 | 0.702 (25) | 0.708 | 0.968 | 0.587 | 0.480 | 0.680 | 0.760 | 0.760 |
| `cross-minilm-l6+pool=union100+w=0.5` | paraphrase | 25 | 0.599 (25) | 0.584 | 0.904 | 0.429 | 0.360 | 0.560 | 0.640 | 0.680 |
| `cross-minilm-l6+pool=union100+w=0.5` | known_item | 25 | 0.718 (25) | 0.636 | 0.952 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `cross-minilm-l6+pool=union100+w=1` | keyword | 25 | 0.598 (25) | 0.512 | 0.692 | 0.764 | 0.680 | 0.840 | 0.920 | 0.920 |
| `cross-minilm-l6+pool=union100+w=1` | question | 25 | 0.540 (25) | 0.504 | 0.688 | 0.493 | 0.440 | 0.600 | 0.640 | 0.760 |
| `cross-minilm-l6+pool=union100+w=1` | paraphrase | 25 | 0.401 (25) | 0.408 | 0.616 | 0.254 | 0.200 | 0.360 | 0.400 | 0.480 |
| `cross-minilm-l6+pool=union100+w=1` | known_item | 25 | 0.640 (25) | 0.524 | 0.748 | 0.905 | 0.840 | 0.960 | 1.000 | 1.000 |
| `dense-bge-small` | keyword | 25 | 0.630 (25) | 0.656 | 1.000 | 0.654 | 0.600 | 0.680 | 0.800 | 0.880 |
| `dense-bge-small` | question | 25 | 0.594 (25) | 0.624 | 1.000 | 0.418 | 0.320 | 0.560 | 0.680 | 0.720 |
| `dense-bge-small` | paraphrase | 25 | 0.462 (25) | 0.496 | 1.000 | 0.284 | 0.200 | 0.360 | 0.480 | 0.640 |
| `dense-bge-small` | known_item | 25 | 0.620 (25) | 0.560 | 1.000 | 0.667 | 0.560 | 0.800 | 0.840 | 0.920 |
| `dense-e5-small` | keyword | 25 | 0.491 (25) | 0.412 | 0.552 | 0.602 | 0.480 | 0.800 | 0.880 | 0.880 |
| `dense-e5-small` | question | 25 | 0.411 (25) | 0.384 | 0.564 | 0.447 | 0.360 | 0.520 | 0.640 | 0.680 |
| `dense-e5-small` | paraphrase | 25 | 0.283 (25) | 0.244 | 0.416 | 0.264 | 0.240 | 0.280 | 0.320 | 0.480 |
| `dense-e5-small` | known_item | 25 | 0.508 (25) | 0.396 | 0.532 | 0.626 | 0.480 | 0.840 | 0.920 | 0.960 |
| `dense-gte-small` | keyword | 25 | 0.657 (25) | 0.652 | 1.000 | 0.688 | 0.600 | 0.840 | 0.840 | 0.840 |
| `dense-gte-small` | question | 25 | 0.582 (25) | 0.616 | 1.000 | 0.417 | 0.320 | 0.520 | 0.640 | 0.760 |
| `dense-gte-small` | paraphrase | 25 | 0.505 (25) | 0.536 | 1.000 | 0.364 | 0.280 | 0.440 | 0.520 | 0.640 |
| `dense-gte-small` | known_item | 25 | 0.580 (25) | 0.520 | 1.000 | 0.633 | 0.520 | 0.840 | 0.840 | 0.880 |
| `dense-minilm` | keyword | 25 | 0.519 (25) | 0.452 | 0.588 | 0.459 | 0.400 | 0.560 | 0.680 | 0.800 |
| `dense-minilm` | question | 25 | 0.436 (25) | 0.396 | 0.544 | 0.358 | 0.280 | 0.520 | 0.520 | 0.640 |
| `dense-minilm` | paraphrase | 25 | 0.364 (25) | 0.352 | 0.552 | 0.260 | 0.200 | 0.320 | 0.440 | 0.520 |
| `dense-minilm` | known_item | 25 | 0.440 (25) | 0.320 | 0.496 | 0.549 | 0.440 | 0.720 | 0.720 | 0.760 |
| `dense-openai-large` | keyword | 25 | 0.642 (25) | 0.676 | 1.000 | 0.577 | 0.480 | 0.800 | 0.800 | 0.880 |
| `dense-openai-large` | question | 25 | 0.688 (25) | 0.704 | 1.000 | 0.560 | 0.440 | 0.720 | 0.800 | 0.840 |
| `dense-openai-large` | paraphrase | 25 | 0.644 (25) | 0.652 | 1.000 | 0.466 | 0.400 | 0.520 | 0.720 | 0.800 |
| `dense-openai-large` | known_item | 25 | 0.600 (25) | 0.516 | 1.000 | 0.793 | 0.680 | 0.920 | 0.960 | 1.000 |
| `field-gte-concat` | keyword | 25 | 0.739 (25) | 0.744 | 1.000 | 0.720 | 0.600 | 0.880 | 0.960 | 0.960 |
| `field-gte-concat` | question | 25 | 0.728 (25) | 0.740 | 1.000 | 0.588 | 0.480 | 0.720 | 0.760 | 0.800 |
| `field-gte-concat` | paraphrase | 25 | 0.686 (25) | 0.648 | 1.000 | 0.498 | 0.400 | 0.600 | 0.720 | 0.800 |
| `field-gte-concat` | known_item | 25 | 0.718 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `field-gte-separate+t=0.25` | keyword | 25 | 0.739 (25) | 0.744 | 1.000 | 0.720 | 0.600 | 0.880 | 0.960 | 0.960 |
| `field-gte-separate+t=0.25` | question | 25 | 0.728 (25) | 0.740 | 1.000 | 0.588 | 0.480 | 0.720 | 0.760 | 0.800 |
| `field-gte-separate+t=0.25` | paraphrase | 25 | 0.686 (25) | 0.648 | 1.000 | 0.498 | 0.400 | 0.600 | 0.720 | 0.800 |
| `field-gte-separate+t=0.25` | known_item | 25 | 0.718 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `field-gte-separate+t=0.5` | keyword | 25 | 0.739 (25) | 0.744 | 1.000 | 0.720 | 0.600 | 0.880 | 0.960 | 0.960 |
| `field-gte-separate+t=0.5` | question | 25 | 0.728 (25) | 0.740 | 1.000 | 0.588 | 0.480 | 0.720 | 0.760 | 0.800 |
| `field-gte-separate+t=0.5` | paraphrase | 25 | 0.686 (25) | 0.648 | 1.000 | 0.498 | 0.400 | 0.600 | 0.720 | 0.800 |
| `field-gte-separate+t=0.5` | known_item | 25 | 0.718 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `field-gte-separate+t=0.75` | keyword | 25 | 0.739 (25) | 0.744 | 1.000 | 0.720 | 0.600 | 0.880 | 0.960 | 0.960 |
| `field-gte-separate+t=0.75` | question | 25 | 0.728 (25) | 0.740 | 1.000 | 0.588 | 0.480 | 0.720 | 0.760 | 0.800 |
| `field-gte-separate+t=0.75` | paraphrase | 25 | 0.686 (25) | 0.648 | 1.000 | 0.498 | 0.400 | 0.600 | 0.720 | 0.800 |
| `field-gte-separate+t=0.75` | known_item | 25 | 0.718 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `field-lexical+t=0.25` | keyword | 25 | 0.734 (25) | 0.736 | 1.000 | 0.722 | 0.600 | 0.920 | 0.960 | 1.000 |
| `field-lexical+t=0.25` | question | 25 | 0.714 (25) | 0.732 | 1.000 | 0.580 | 0.480 | 0.720 | 0.760 | 0.800 |
| `field-lexical+t=0.25` | paraphrase | 25 | 0.645 (25) | 0.636 | 1.000 | 0.397 | 0.280 | 0.600 | 0.680 | 0.720 |
| `field-lexical+t=0.25` | known_item | 25 | 0.730 (25) | 0.640 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `field-lexical+t=0.5` | keyword | 25 | 0.722 (25) | 0.732 | 0.996 | 0.690 | 0.520 | 0.880 | 0.960 | 0.960 |
| `field-lexical+t=0.5` | question | 25 | 0.702 (25) | 0.720 | 1.000 | 0.562 | 0.440 | 0.720 | 0.760 | 0.800 |
| `field-lexical+t=0.5` | paraphrase | 25 | 0.629 (25) | 0.636 | 1.000 | 0.354 | 0.200 | 0.640 | 0.680 | 0.720 |
| `field-lexical+t=0.5` | known_item | 25 | 0.732 (25) | 0.640 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `field-lexical+t=0.75` | keyword | 25 | 0.700 (25) | 0.716 | 0.996 | 0.649 | 0.520 | 0.880 | 0.920 | 0.960 |
| `field-lexical+t=0.75` | question | 25 | 0.673 (25) | 0.700 | 1.000 | 0.486 | 0.320 | 0.720 | 0.760 | 0.800 |
| `field-lexical+t=0.75` | paraphrase | 25 | 0.616 (25) | 0.640 | 1.000 | 0.331 | 0.200 | 0.600 | 0.680 | 0.760 |
| `field-lexical+t=0.75` | known_item | 25 | 0.731 (25) | 0.640 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `field-order-gte-concat` | keyword | 25 | 0.757 (25) | 0.744 | 1.000 | 0.734 | 0.640 | 0.840 | 0.960 | 0.960 |
| `field-order-gte-concat` | question | 25 | 0.698 (25) | 0.740 | 1.000 | 0.461 | 0.320 | 0.720 | 0.760 | 0.800 |
| `field-order-gte-concat` | paraphrase | 25 | 0.660 (25) | 0.648 | 1.000 | 0.489 | 0.400 | 0.600 | 0.720 | 0.800 |
| `field-order-gte-concat` | known_item | 25 | 0.708 (25) | 0.624 | 1.000 | 0.801 | 0.680 | 0.960 | 1.000 | 1.000 |
| `field-order-gte-separate+t=0.25` | keyword | 25 | 0.742 (25) | 0.744 | 1.000 | 0.696 | 0.600 | 0.800 | 0.960 | 0.960 |
| `field-order-gte-separate+t=0.25` | question | 25 | 0.700 (25) | 0.740 | 1.000 | 0.496 | 0.360 | 0.680 | 0.760 | 0.800 |
| `field-order-gte-separate+t=0.25` | paraphrase | 25 | 0.670 (25) | 0.648 | 1.000 | 0.510 | 0.440 | 0.640 | 0.720 | 0.800 |
| `field-order-gte-separate+t=0.25` | known_item | 25 | 0.703 (25) | 0.624 | 1.000 | 0.781 | 0.640 | 1.000 | 1.000 | 1.000 |
| `field-order-gte-separate+t=0.5` | keyword | 25 | 0.734 (25) | 0.744 | 1.000 | 0.646 | 0.520 | 0.840 | 0.960 | 0.960 |
| `field-order-gte-separate+t=0.5` | question | 25 | 0.691 (25) | 0.740 | 1.000 | 0.454 | 0.320 | 0.680 | 0.760 | 0.800 |
| `field-order-gte-separate+t=0.5` | paraphrase | 25 | 0.653 (25) | 0.648 | 1.000 | 0.465 | 0.360 | 0.640 | 0.720 | 0.800 |
| `field-order-gte-separate+t=0.5` | known_item | 25 | 0.702 (25) | 0.624 | 1.000 | 0.830 | 0.720 | 1.000 | 1.000 | 1.000 |
| `field-order-gte-separate+t=0.75` | keyword | 25 | 0.721 (25) | 0.744 | 1.000 | 0.608 | 0.520 | 0.800 | 0.960 | 0.960 |
| `field-order-gte-separate+t=0.75` | question | 25 | 0.666 (25) | 0.740 | 1.000 | 0.354 | 0.160 | 0.680 | 0.760 | 0.800 |
| `field-order-gte-separate+t=0.75` | paraphrase | 25 | 0.623 (25) | 0.648 | 1.000 | 0.354 | 0.200 | 0.600 | 0.720 | 0.800 |
| `field-order-gte-separate+t=0.75` | known_item | 25 | 0.697 (25) | 0.624 | 1.000 | 0.791 | 0.680 | 0.960 | 1.000 | 1.000 |
| `fusion-linear+w=0.25+d=100` | keyword | 25 | 0.696 (25) | 0.692 | 1.000 | 0.741 | 0.640 | 0.880 | 0.880 | 0.960 |
| `fusion-linear+w=0.25+d=100` | question | 25 | 0.606 (25) | 0.588 | 1.000 | 0.557 | 0.480 | 0.640 | 0.720 | 0.720 |
| `fusion-linear+w=0.25+d=100` | paraphrase | 25 | 0.531 (25) | 0.540 | 1.000 | 0.267 | 0.200 | 0.360 | 0.360 | 0.400 |
| `fusion-linear+w=0.25+d=100` | known_item | 25 | 0.716 (25) | 0.636 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-linear+w=0.25+d=20` | keyword | 25 | 0.644 (25) | 0.624 | 1.000 | 0.759 | 0.640 | 0.880 | 0.920 | 1.000 |
| `fusion-linear+w=0.25+d=20` | question | 25 | 0.490 (25) | 0.460 | 1.000 | 0.525 | 0.480 | 0.600 | 0.640 | 0.760 |
| `fusion-linear+w=0.25+d=20` | paraphrase | 25 | 0.391 (25) | 0.424 | 1.000 | 0.193 | 0.160 | 0.240 | 0.280 | 0.720 |
| `fusion-linear+w=0.25+d=20` | known_item | 25 | 0.676 (25) | 0.596 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-linear+w=0.25+d=50` | keyword | 25 | 0.675 (25) | 0.652 | 1.000 | 0.739 | 0.640 | 0.880 | 0.920 | 0.920 |
| `fusion-linear+w=0.25+d=50` | question | 25 | 0.544 (25) | 0.508 | 1.000 | 0.546 | 0.480 | 0.600 | 0.680 | 0.720 |
| `fusion-linear+w=0.25+d=50` | paraphrase | 25 | 0.447 (25) | 0.452 | 1.000 | 0.207 | 0.160 | 0.280 | 0.280 | 0.360 |
| `fusion-linear+w=0.25+d=50` | known_item | 25 | 0.692 (25) | 0.616 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-linear+w=0.5+d=100` | keyword | 25 | 0.729 (25) | 0.744 | 1.000 | 0.692 | 0.600 | 0.840 | 0.880 | 1.000 |
| `fusion-linear+w=0.5+d=100` | question | 25 | 0.693 (25) | 0.708 | 1.000 | 0.553 | 0.440 | 0.680 | 0.760 | 0.800 |
| `fusion-linear+w=0.5+d=100` | paraphrase | 25 | 0.616 (25) | 0.636 | 1.000 | 0.303 | 0.200 | 0.440 | 0.520 | 0.720 |
| `fusion-linear+w=0.5+d=100` | known_item | 25 | 0.723 (25) | 0.648 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-linear+w=0.5+d=20` | keyword | 25 | 0.665 (25) | 0.652 | 1.000 | 0.706 | 0.600 | 0.920 | 0.920 | 1.000 |
| `fusion-linear+w=0.5+d=20` | question | 25 | 0.635 (25) | 0.608 | 1.000 | 0.545 | 0.440 | 0.680 | 0.760 | 0.800 |
| `fusion-linear+w=0.5+d=20` | paraphrase | 25 | 0.555 (25) | 0.568 | 1.000 | 0.329 | 0.160 | 0.600 | 0.680 | 0.760 |
| `fusion-linear+w=0.5+d=20` | known_item | 25 | 0.674 (25) | 0.592 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-linear+w=0.5+d=50` | keyword | 25 | 0.712 (25) | 0.716 | 1.000 | 0.693 | 0.600 | 0.840 | 0.880 | 1.000 |
| `fusion-linear+w=0.5+d=50` | question | 25 | 0.672 (25) | 0.676 | 1.000 | 0.550 | 0.440 | 0.720 | 0.760 | 0.800 |
| `fusion-linear+w=0.5+d=50` | paraphrase | 25 | 0.601 (25) | 0.592 | 1.000 | 0.330 | 0.200 | 0.440 | 0.680 | 0.800 |
| `fusion-linear+w=0.5+d=50` | known_item | 25 | 0.707 (25) | 0.624 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-linear+w=0.75+d=100` | keyword | 25 | 0.731 (25) | 0.744 | 1.000 | 0.640 | 0.520 | 0.800 | 0.920 | 0.920 |
| `fusion-linear+w=0.75+d=100` | question | 25 | 0.717 (25) | 0.736 | 1.000 | 0.563 | 0.440 | 0.760 | 0.760 | 0.840 |
| `fusion-linear+w=0.75+d=100` | paraphrase | 25 | 0.665 (25) | 0.660 | 1.000 | 0.347 | 0.240 | 0.440 | 0.680 | 0.800 |
| `fusion-linear+w=0.75+d=100` | known_item | 25 | 0.698 (25) | 0.600 | 1.000 | 0.947 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-linear+w=0.75+d=20` | keyword | 25 | 0.663 (25) | 0.676 | 1.000 | 0.620 | 0.520 | 0.760 | 0.800 | 0.960 |
| `fusion-linear+w=0.75+d=20` | question | 25 | 0.704 (25) | 0.700 | 1.000 | 0.579 | 0.440 | 0.760 | 0.800 | 0.800 |
| `fusion-linear+w=0.75+d=20` | paraphrase | 25 | 0.662 (25) | 0.648 | 1.000 | 0.436 | 0.320 | 0.560 | 0.720 | 0.800 |
| `fusion-linear+w=0.75+d=20` | known_item | 25 | 0.636 (25) | 0.520 | 1.000 | 0.933 | 0.920 | 0.960 | 0.960 | 1.000 |
| `fusion-linear+w=0.75+d=50` | keyword | 25 | 0.704 (25) | 0.720 | 1.000 | 0.631 | 0.520 | 0.760 | 0.920 | 0.920 |
| `fusion-linear+w=0.75+d=50` | question | 25 | 0.714 (25) | 0.720 | 1.000 | 0.578 | 0.440 | 0.760 | 0.800 | 0.840 |
| `fusion-linear+w=0.75+d=50` | paraphrase | 25 | 0.655 (25) | 0.652 | 1.000 | 0.373 | 0.240 | 0.600 | 0.760 | 0.800 |
| `fusion-linear+w=0.75+d=50` | known_item | 25 | 0.671 (25) | 0.564 | 1.000 | 0.947 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rankscore+a=0.25+d=100` | keyword | 25 | 0.730 (25) | 0.744 | 1.000 | 0.665 | 0.520 | 0.880 | 0.960 | 0.960 |
| `fusion-rankscore+a=0.25+d=100` | question | 25 | 0.716 (25) | 0.740 | 1.000 | 0.561 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-rankscore+a=0.25+d=100` | paraphrase | 25 | 0.667 (25) | 0.660 | 1.000 | 0.377 | 0.280 | 0.440 | 0.680 | 0.760 |
| `fusion-rankscore+a=0.25+d=100` | known_item | 25 | 0.715 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rankscore+a=0.25+d=500` | keyword | 25 | 0.730 (25) | 0.744 | 1.000 | 0.665 | 0.520 | 0.880 | 0.960 | 0.960 |
| `fusion-rankscore+a=0.25+d=500` | question | 25 | 0.717 (25) | 0.744 | 1.000 | 0.560 | 0.440 | 0.720 | 0.760 | 0.800 |
| `fusion-rankscore+a=0.25+d=500` | paraphrase | 25 | 0.659 (25) | 0.648 | 1.000 | 0.379 | 0.280 | 0.440 | 0.680 | 0.760 |
| `fusion-rankscore+a=0.25+d=500` | known_item | 25 | 0.714 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rankscore+a=0.5+d=100` | keyword | 25 | 0.724 (25) | 0.736 | 1.000 | 0.674 | 0.520 | 0.880 | 0.960 | 0.960 |
| `fusion-rankscore+a=0.5+d=100` | question | 25 | 0.715 (25) | 0.736 | 1.000 | 0.565 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-rankscore+a=0.5+d=100` | paraphrase | 25 | 0.668 (25) | 0.664 | 1.000 | 0.375 | 0.280 | 0.440 | 0.680 | 0.760 |
| `fusion-rankscore+a=0.5+d=100` | known_item | 25 | 0.721 (25) | 0.628 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rankscore+a=0.5+d=500` | keyword | 25 | 0.727 (25) | 0.744 | 1.000 | 0.674 | 0.520 | 0.880 | 0.960 | 0.960 |
| `fusion-rankscore+a=0.5+d=500` | question | 25 | 0.714 (25) | 0.736 | 1.000 | 0.561 | 0.440 | 0.720 | 0.760 | 0.800 |
| `fusion-rankscore+a=0.5+d=500` | paraphrase | 25 | 0.663 (25) | 0.648 | 1.000 | 0.386 | 0.280 | 0.480 | 0.680 | 0.720 |
| `fusion-rankscore+a=0.5+d=500` | known_item | 25 | 0.722 (25) | 0.632 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rankscore+a=0.75+d=100` | keyword | 25 | 0.736 (25) | 0.744 | 1.000 | 0.700 | 0.560 | 0.880 | 0.960 | 0.960 |
| `fusion-rankscore+a=0.75+d=100` | question | 25 | 0.717 (25) | 0.728 | 1.000 | 0.568 | 0.440 | 0.720 | 0.760 | 0.800 |
| `fusion-rankscore+a=0.75+d=100` | paraphrase | 25 | 0.667 (25) | 0.664 | 1.000 | 0.412 | 0.360 | 0.440 | 0.640 | 0.720 |
| `fusion-rankscore+a=0.75+d=100` | known_item | 25 | 0.723 (25) | 0.628 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rankscore+a=0.75+d=500` | keyword | 25 | 0.732 (25) | 0.740 | 1.000 | 0.700 | 0.560 | 0.880 | 0.960 | 0.960 |
| `fusion-rankscore+a=0.75+d=500` | question | 25 | 0.719 (25) | 0.736 | 0.996 | 0.563 | 0.440 | 0.720 | 0.720 | 0.800 |
| `fusion-rankscore+a=0.75+d=500` | paraphrase | 25 | 0.689 (25) | 0.672 | 1.000 | 0.471 | 0.400 | 0.600 | 0.680 | 0.680 |
| `fusion-rankscore+a=0.75+d=500` | known_item | 25 | 0.727 (25) | 0.636 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0+d=100+c=10` | keyword | 25 | 0.610 (25) | 0.596 | 1.000 | 0.710 | 0.600 | 0.880 | 0.920 | 0.920 |
| `fusion-rrf+w=0+d=100+c=10` | question | 25 | 0.434 (25) | 0.452 | 1.000 | 0.432 | 0.360 | 0.520 | 0.640 | 0.640 |
| `fusion-rrf+w=0+d=100+c=10` | paraphrase | 25 | 0.365 (25) | 0.412 | 1.000 | 0.132 | 0.080 | 0.240 | 0.280 | 0.280 |
| `fusion-rrf+w=0+d=100+c=10` | known_item | 25 | 0.666 (25) | 0.588 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.25+d=100+c=10` | keyword | 25 | 0.665 (25) | 0.652 | 1.000 | 0.725 | 0.600 | 0.880 | 0.920 | 1.000 |
| `fusion-rrf+w=0.25+d=100+c=10` | question | 25 | 0.503 (25) | 0.488 | 1.000 | 0.505 | 0.440 | 0.560 | 0.680 | 0.720 |
| `fusion-rrf+w=0.25+d=100+c=10` | paraphrase | 25 | 0.420 (25) | 0.468 | 1.000 | 0.199 | 0.160 | 0.280 | 0.320 | 0.400 |
| `fusion-rrf+w=0.25+d=100+c=10` | known_item | 25 | 0.689 (25) | 0.620 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.25+d=100+c=100` | keyword | 25 | 0.705 (25) | 0.708 | 1.000 | 0.743 | 0.640 | 0.880 | 0.880 | 1.000 |
| `fusion-rrf+w=0.25+d=100+c=100` | question | 25 | 0.646 (25) | 0.652 | 1.000 | 0.547 | 0.480 | 0.640 | 0.720 | 0.720 |
| `fusion-rrf+w=0.25+d=100+c=100` | paraphrase | 25 | 0.556 (25) | 0.576 | 1.000 | 0.251 | 0.160 | 0.360 | 0.400 | 0.440 |
| `fusion-rrf+w=0.25+d=100+c=100` | known_item | 25 | 0.731 (25) | 0.648 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.25+d=100+c=60` | keyword | 25 | 0.694 (25) | 0.688 | 1.000 | 0.743 | 0.640 | 0.880 | 0.880 | 0.960 |
| `fusion-rrf+w=0.25+d=100+c=60` | question | 25 | 0.603 (25) | 0.604 | 1.000 | 0.544 | 0.480 | 0.640 | 0.720 | 0.720 |
| `fusion-rrf+w=0.25+d=100+c=60` | paraphrase | 25 | 0.518 (25) | 0.536 | 1.000 | 0.237 | 0.160 | 0.360 | 0.360 | 0.440 |
| `fusion-rrf+w=0.25+d=100+c=60` | known_item | 25 | 0.718 (25) | 0.644 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.25+d=20+c=10` | keyword | 25 | 0.650 (25) | 0.632 | 1.000 | 0.725 | 0.600 | 0.880 | 0.920 | 0.920 |
| `fusion-rrf+w=0.25+d=20+c=10` | question | 25 | 0.500 (25) | 0.480 | 1.000 | 0.522 | 0.480 | 0.560 | 0.640 | 0.640 |
| `fusion-rrf+w=0.25+d=20+c=10` | paraphrase | 25 | 0.401 (25) | 0.432 | 1.000 | 0.195 | 0.160 | 0.280 | 0.280 | 0.280 |
| `fusion-rrf+w=0.25+d=20+c=10` | known_item | 25 | 0.682 (25) | 0.608 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.25+d=20+c=100` | keyword | 25 | 0.657 (25) | 0.640 | 1.000 | 0.717 | 0.600 | 0.880 | 0.880 | 0.920 |
| `fusion-rrf+w=0.25+d=20+c=100` | question | 25 | 0.541 (25) | 0.500 | 1.000 | 0.533 | 0.480 | 0.600 | 0.640 | 0.640 |
| `fusion-rrf+w=0.25+d=20+c=100` | paraphrase | 25 | 0.433 (25) | 0.424 | 1.000 | 0.227 | 0.200 | 0.280 | 0.280 | 0.280 |
| `fusion-rrf+w=0.25+d=20+c=100` | known_item | 25 | 0.699 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.25+d=20+c=60` | keyword | 25 | 0.657 (25) | 0.640 | 1.000 | 0.717 | 0.600 | 0.880 | 0.880 | 0.920 |
| `fusion-rrf+w=0.25+d=20+c=60` | question | 25 | 0.541 (25) | 0.500 | 1.000 | 0.533 | 0.480 | 0.600 | 0.640 | 0.640 |
| `fusion-rrf+w=0.25+d=20+c=60` | paraphrase | 25 | 0.433 (25) | 0.424 | 1.000 | 0.227 | 0.200 | 0.280 | 0.280 | 0.280 |
| `fusion-rrf+w=0.25+d=20+c=60` | known_item | 25 | 0.699 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.25+d=50+c=10` | keyword | 25 | 0.663 (25) | 0.648 | 1.000 | 0.725 | 0.600 | 0.880 | 0.920 | 0.960 |
| `fusion-rrf+w=0.25+d=50+c=10` | question | 25 | 0.504 (25) | 0.488 | 1.000 | 0.506 | 0.440 | 0.560 | 0.680 | 0.720 |
| `fusion-rrf+w=0.25+d=50+c=10` | paraphrase | 25 | 0.421 (25) | 0.468 | 1.000 | 0.199 | 0.160 | 0.280 | 0.320 | 0.360 |
| `fusion-rrf+w=0.25+d=50+c=10` | known_item | 25 | 0.686 (25) | 0.616 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.25+d=50+c=100` | keyword | 25 | 0.693 (25) | 0.680 | 1.000 | 0.738 | 0.640 | 0.840 | 0.880 | 0.960 |
| `fusion-rrf+w=0.25+d=50+c=100` | question | 25 | 0.625 (25) | 0.616 | 1.000 | 0.551 | 0.480 | 0.640 | 0.720 | 0.720 |
| `fusion-rrf+w=0.25+d=50+c=100` | paraphrase | 25 | 0.536 (25) | 0.540 | 1.000 | 0.251 | 0.160 | 0.360 | 0.400 | 0.400 |
| `fusion-rrf+w=0.25+d=50+c=100` | known_item | 25 | 0.733 (25) | 0.656 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.25+d=50+c=60` | keyword | 25 | 0.688 (25) | 0.680 | 1.000 | 0.740 | 0.640 | 0.840 | 0.880 | 0.960 |
| `fusion-rrf+w=0.25+d=50+c=60` | question | 25 | 0.598 (25) | 0.592 | 1.000 | 0.548 | 0.480 | 0.640 | 0.720 | 0.720 |
| `fusion-rrf+w=0.25+d=50+c=60` | paraphrase | 25 | 0.501 (25) | 0.504 | 1.000 | 0.237 | 0.160 | 0.360 | 0.360 | 0.400 |
| `fusion-rrf+w=0.25+d=50+c=60` | known_item | 25 | 0.717 (25) | 0.640 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.5+d=100+c=10` | keyword | 25 | 0.696 (25) | 0.692 | 1.000 | 0.717 | 0.600 | 0.920 | 0.960 | 1.000 |
| `fusion-rrf+w=0.5+d=100+c=10` | question | 25 | 0.662 (25) | 0.660 | 1.000 | 0.553 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-rrf+w=0.5+d=100+c=10` | paraphrase | 25 | 0.591 (25) | 0.576 | 1.000 | 0.364 | 0.240 | 0.520 | 0.640 | 0.800 |
| `fusion-rrf+w=0.5+d=100+c=10` | known_item | 25 | 0.692 (25) | 0.604 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.5+d=100+c=100` | keyword | 25 | 0.727 (25) | 0.752 | 1.000 | 0.692 | 0.600 | 0.840 | 0.880 | 0.960 |
| `fusion-rrf+w=0.5+d=100+c=100` | question | 25 | 0.707 (25) | 0.720 | 1.000 | 0.549 | 0.440 | 0.680 | 0.720 | 0.760 |
| `fusion-rrf+w=0.5+d=100+c=100` | paraphrase | 25 | 0.616 (25) | 0.640 | 1.000 | 0.305 | 0.200 | 0.440 | 0.480 | 0.640 |
| `fusion-rrf+w=0.5+d=100+c=100` | known_item | 25 | 0.720 (25) | 0.644 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.5+d=100+c=30` | keyword | 25 | 0.727 (25) | 0.740 | 1.000 | 0.709 | 0.600 | 0.840 | 0.960 | 1.000 |
| `fusion-rrf+w=0.5+d=100+c=30` | question | 25 | 0.693 (25) | 0.688 | 1.000 | 0.548 | 0.440 | 0.680 | 0.760 | 0.800 |
| `fusion-rrf+w=0.5+d=100+c=30` | paraphrase | 25 | 0.620 (25) | 0.616 | 1.000 | 0.348 | 0.240 | 0.440 | 0.640 | 0.760 |
| `fusion-rrf+w=0.5+d=100+c=30` | known_item | 25 | 0.727 (25) | 0.648 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.5+d=100+c=60` | keyword | 25 | 0.730 (25) | 0.748 | 1.000 | 0.697 | 0.600 | 0.840 | 0.920 | 1.000 |
| `fusion-rrf+w=0.5+d=100+c=60` | question | 25 | 0.709 (25) | 0.720 | 1.000 | 0.542 | 0.440 | 0.680 | 0.720 | 0.760 |
| `fusion-rrf+w=0.5+d=100+c=60` | paraphrase | 25 | 0.619 (25) | 0.644 | 1.000 | 0.304 | 0.200 | 0.440 | 0.480 | 0.720 |
| `fusion-rrf+w=0.5+d=100+c=60` | known_item | 25 | 0.723 (25) | 0.644 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.5+d=20+c=10` | keyword | 25 | 0.680 (25) | 0.668 | 1.000 | 0.713 | 0.600 | 0.920 | 0.920 | 1.000 |
| `fusion-rrf+w=0.5+d=20+c=10` | question | 25 | 0.646 (25) | 0.628 | 1.000 | 0.542 | 0.440 | 0.680 | 0.760 | 0.800 |
| `fusion-rrf+w=0.5+d=20+c=10` | paraphrase | 25 | 0.559 (25) | 0.560 | 1.000 | 0.320 | 0.160 | 0.600 | 0.680 | 0.760 |
| `fusion-rrf+w=0.5+d=20+c=10` | known_item | 25 | 0.691 (25) | 0.604 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.5+d=20+c=100` | keyword | 25 | 0.684 (25) | 0.676 | 1.000 | 0.696 | 0.600 | 0.880 | 0.920 | 1.000 |
| `fusion-rrf+w=0.5+d=20+c=100` | question | 25 | 0.645 (25) | 0.628 | 1.000 | 0.544 | 0.440 | 0.680 | 0.760 | 0.800 |
| `fusion-rrf+w=0.5+d=20+c=100` | paraphrase | 25 | 0.554 (25) | 0.560 | 1.000 | 0.313 | 0.160 | 0.560 | 0.680 | 0.760 |
| `fusion-rrf+w=0.5+d=20+c=100` | known_item | 25 | 0.691 (25) | 0.612 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.5+d=20+c=60` | keyword | 25 | 0.684 (25) | 0.676 | 1.000 | 0.696 | 0.600 | 0.880 | 0.920 | 1.000 |
| `fusion-rrf+w=0.5+d=20+c=60` | question | 25 | 0.645 (25) | 0.628 | 1.000 | 0.537 | 0.440 | 0.680 | 0.760 | 0.800 |
| `fusion-rrf+w=0.5+d=20+c=60` | paraphrase | 25 | 0.554 (25) | 0.560 | 1.000 | 0.313 | 0.160 | 0.560 | 0.680 | 0.760 |
| `fusion-rrf+w=0.5+d=20+c=60` | known_item | 25 | 0.691 (25) | 0.612 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.5+d=50+c=10` | keyword | 25 | 0.690 (25) | 0.688 | 1.000 | 0.711 | 0.600 | 0.840 | 0.960 | 1.000 |
| `fusion-rrf+w=0.5+d=50+c=10` | question | 25 | 0.659 (25) | 0.656 | 1.000 | 0.553 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-rrf+w=0.5+d=50+c=10` | paraphrase | 25 | 0.586 (25) | 0.576 | 1.000 | 0.338 | 0.200 | 0.520 | 0.640 | 0.800 |
| `fusion-rrf+w=0.5+d=50+c=10` | known_item | 25 | 0.691 (25) | 0.604 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.5+d=50+c=100` | keyword | 25 | 0.719 (25) | 0.724 | 1.000 | 0.692 | 0.600 | 0.840 | 0.880 | 1.000 |
| `fusion-rrf+w=0.5+d=50+c=100` | question | 25 | 0.667 (25) | 0.668 | 1.000 | 0.555 | 0.440 | 0.680 | 0.760 | 0.800 |
| `fusion-rrf+w=0.5+d=50+c=100` | paraphrase | 25 | 0.597 (25) | 0.600 | 1.000 | 0.314 | 0.200 | 0.440 | 0.640 | 0.760 |
| `fusion-rrf+w=0.5+d=50+c=100` | known_item | 25 | 0.722 (25) | 0.644 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.5+d=50+c=60` | keyword | 25 | 0.720 (25) | 0.724 | 1.000 | 0.696 | 0.600 | 0.840 | 0.920 | 1.000 |
| `fusion-rrf+w=0.5+d=50+c=60` | question | 25 | 0.672 (25) | 0.672 | 1.000 | 0.548 | 0.440 | 0.680 | 0.760 | 0.800 |
| `fusion-rrf+w=0.5+d=50+c=60` | paraphrase | 25 | 0.597 (25) | 0.600 | 1.000 | 0.314 | 0.200 | 0.440 | 0.640 | 0.760 |
| `fusion-rrf+w=0.5+d=50+c=60` | known_item | 25 | 0.724 (25) | 0.644 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.55+d=100+c=10` | keyword | 25 | 0.698 (25) | 0.688 | 1.000 | 0.680 | 0.520 | 0.880 | 0.960 | 1.000 |
| `fusion-rrf+w=0.55+d=100+c=10` | question | 25 | 0.696 (25) | 0.700 | 1.000 | 0.575 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-rrf+w=0.55+d=100+c=10` | paraphrase | 25 | 0.640 (25) | 0.624 | 1.000 | 0.396 | 0.280 | 0.640 | 0.720 | 0.800 |
| `fusion-rrf+w=0.55+d=100+c=10` | known_item | 25 | 0.688 (25) | 0.596 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.55+d=100+c=100` | keyword | 25 | 0.737 (25) | 0.752 | 0.996 | 0.660 | 0.520 | 0.840 | 0.960 | 0.960 |
| `fusion-rrf+w=0.55+d=100+c=100` | question | 25 | 0.713 (25) | 0.720 | 1.000 | 0.542 | 0.440 | 0.680 | 0.720 | 0.800 |
| `fusion-rrf+w=0.55+d=100+c=100` | paraphrase | 25 | 0.634 (25) | 0.656 | 0.996 | 0.317 | 0.200 | 0.440 | 0.520 | 0.680 |
| `fusion-rrf+w=0.55+d=100+c=100` | known_item | 25 | 0.724 (25) | 0.644 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.55+d=100+c=30` | keyword | 25 | 0.733 (25) | 0.744 | 1.000 | 0.663 | 0.520 | 0.840 | 0.960 | 0.960 |
| `fusion-rrf+w=0.55+d=100+c=30` | question | 25 | 0.717 (25) | 0.740 | 1.000 | 0.558 | 0.440 | 0.720 | 0.760 | 0.800 |
| `fusion-rrf+w=0.55+d=100+c=30` | paraphrase | 25 | 0.662 (25) | 0.648 | 1.000 | 0.382 | 0.280 | 0.480 | 0.720 | 0.800 |
| `fusion-rrf+w=0.55+d=100+c=30` | known_item | 25 | 0.713 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.55+d=100+c=60` | keyword | 25 | 0.733 (25) | 0.748 | 1.000 | 0.660 | 0.520 | 0.840 | 0.960 | 0.960 |
| `fusion-rrf+w=0.55+d=100+c=60` | question | 25 | 0.715 (25) | 0.728 | 1.000 | 0.547 | 0.440 | 0.680 | 0.760 | 0.800 |
| `fusion-rrf+w=0.55+d=100+c=60` | paraphrase | 25 | 0.645 (25) | 0.660 | 1.000 | 0.341 | 0.240 | 0.440 | 0.560 | 0.720 |
| `fusion-rrf+w=0.55+d=100+c=60` | known_item | 25 | 0.722 (25) | 0.644 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.55+d=200+c=30` | keyword | 25 | 0.739 (25) | 0.752 | 1.000 | 0.663 | 0.520 | 0.840 | 0.960 | 0.960 |
| `fusion-rrf+w=0.55+d=200+c=30` | question | 25 | 0.714 (25) | 0.736 | 1.000 | 0.557 | 0.440 | 0.680 | 0.760 | 0.800 |
| `fusion-rrf+w=0.55+d=200+c=30` | paraphrase | 25 | 0.655 (25) | 0.648 | 1.000 | 0.356 | 0.240 | 0.480 | 0.640 | 0.760 |
| `fusion-rrf+w=0.55+d=200+c=30` | known_item | 25 | 0.715 (25) | 0.628 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.55+d=500+c=30` | keyword | 25 | 0.737 (25) | 0.752 | 1.000 | 0.663 | 0.520 | 0.840 | 0.960 | 0.960 |
| `fusion-rrf+w=0.55+d=500+c=30` | question | 25 | 0.711 (25) | 0.736 | 1.000 | 0.557 | 0.440 | 0.680 | 0.760 | 0.800 |
| `fusion-rrf+w=0.55+d=500+c=30` | paraphrase | 25 | 0.653 (25) | 0.648 | 1.000 | 0.361 | 0.240 | 0.520 | 0.640 | 0.760 |
| `fusion-rrf+w=0.55+d=500+c=30` | known_item | 25 | 0.713 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.6+d=100+c=10` | keyword | 25 | 0.695 (25) | 0.696 | 1.000 | 0.675 | 0.520 | 0.880 | 0.960 | 0.960 |
| `fusion-rrf+w=0.6+d=100+c=10` | question | 25 | 0.718 (25) | 0.724 | 1.000 | 0.588 | 0.440 | 0.760 | 0.800 | 0.800 |
| `fusion-rrf+w=0.6+d=100+c=10` | paraphrase | 25 | 0.649 (25) | 0.628 | 1.000 | 0.402 | 0.280 | 0.640 | 0.720 | 0.800 |
| `fusion-rrf+w=0.6+d=100+c=10` | known_item | 25 | 0.684 (25) | 0.596 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.6+d=100+c=100` | keyword | 25 | 0.736 (25) | 0.744 | 1.000 | 0.660 | 0.520 | 0.840 | 0.960 | 0.960 |
| `fusion-rrf+w=0.6+d=100+c=100` | question | 25 | 0.717 (25) | 0.728 | 1.000 | 0.556 | 0.440 | 0.720 | 0.760 | 0.800 |
| `fusion-rrf+w=0.6+d=100+c=100` | paraphrase | 25 | 0.644 (25) | 0.656 | 0.996 | 0.337 | 0.240 | 0.440 | 0.520 | 0.720 |
| `fusion-rrf+w=0.6+d=100+c=100` | known_item | 25 | 0.725 (25) | 0.644 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.6+d=100+c=30` | keyword | 25 | 0.724 (25) | 0.736 | 1.000 | 0.659 | 0.520 | 0.880 | 0.960 | 0.960 |
| `fusion-rrf+w=0.6+d=100+c=30` | question | 25 | 0.721 (25) | 0.744 | 1.000 | 0.563 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-rrf+w=0.6+d=100+c=30` | paraphrase | 25 | 0.668 (25) | 0.656 | 1.000 | 0.369 | 0.240 | 0.520 | 0.720 | 0.800 |
| `fusion-rrf+w=0.6+d=100+c=30` | known_item | 25 | 0.704 (25) | 0.616 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.6+d=100+c=60` | keyword | 25 | 0.741 (25) | 0.752 | 1.000 | 0.661 | 0.520 | 0.840 | 0.960 | 0.960 |
| `fusion-rrf+w=0.6+d=100+c=60` | question | 25 | 0.721 (25) | 0.744 | 1.000 | 0.559 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-rrf+w=0.6+d=100+c=60` | paraphrase | 25 | 0.658 (25) | 0.668 | 1.000 | 0.347 | 0.240 | 0.440 | 0.600 | 0.720 |
| `fusion-rrf+w=0.6+d=100+c=60` | known_item | 25 | 0.719 (25) | 0.636 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.65+d=100+c=10` | keyword | 25 | 0.686 (25) | 0.692 | 1.000 | 0.653 | 0.520 | 0.840 | 0.920 | 0.960 |
| `fusion-rrf+w=0.65+d=100+c=10` | question | 25 | 0.722 (25) | 0.724 | 1.000 | 0.602 | 0.480 | 0.760 | 0.800 | 0.800 |
| `fusion-rrf+w=0.65+d=100+c=10` | paraphrase | 25 | 0.661 (25) | 0.664 | 1.000 | 0.383 | 0.240 | 0.600 | 0.760 | 0.800 |
| `fusion-rrf+w=0.65+d=100+c=10` | known_item | 25 | 0.667 (25) | 0.568 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.65+d=100+c=100` | keyword | 25 | 0.736 (25) | 0.744 | 0.996 | 0.655 | 0.520 | 0.840 | 0.960 | 0.960 |
| `fusion-rrf+w=0.65+d=100+c=100` | question | 25 | 0.715 (25) | 0.732 | 1.000 | 0.556 | 0.440 | 0.720 | 0.760 | 0.800 |
| `fusion-rrf+w=0.65+d=100+c=100` | paraphrase | 25 | 0.639 (25) | 0.644 | 0.992 | 0.318 | 0.200 | 0.440 | 0.560 | 0.720 |
| `fusion-rrf+w=0.65+d=100+c=100` | known_item | 25 | 0.726 (25) | 0.652 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.65+d=100+c=30` | keyword | 25 | 0.722 (25) | 0.740 | 1.000 | 0.658 | 0.520 | 0.880 | 0.920 | 0.960 |
| `fusion-rrf+w=0.65+d=100+c=30` | question | 25 | 0.724 (25) | 0.744 | 1.000 | 0.570 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-rrf+w=0.65+d=100+c=30` | paraphrase | 25 | 0.673 (25) | 0.652 | 1.000 | 0.380 | 0.280 | 0.480 | 0.720 | 0.800 |
| `fusion-rrf+w=0.65+d=100+c=30` | known_item | 25 | 0.694 (25) | 0.604 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.65+d=100+c=60` | keyword | 25 | 0.735 (25) | 0.748 | 1.000 | 0.656 | 0.520 | 0.840 | 0.960 | 0.960 |
| `fusion-rrf+w=0.65+d=100+c=60` | question | 25 | 0.725 (25) | 0.748 | 1.000 | 0.559 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-rrf+w=0.65+d=100+c=60` | paraphrase | 25 | 0.650 (25) | 0.648 | 1.000 | 0.334 | 0.200 | 0.480 | 0.640 | 0.800 |
| `fusion-rrf+w=0.65+d=100+c=60` | known_item | 25 | 0.715 (25) | 0.632 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.7+d=100+c=10` | keyword | 25 | 0.685 (25) | 0.700 | 1.000 | 0.644 | 0.520 | 0.840 | 0.920 | 0.960 |
| `fusion-rrf+w=0.7+d=100+c=10` | question | 25 | 0.717 (25) | 0.716 | 1.000 | 0.602 | 0.480 | 0.760 | 0.800 | 0.840 |
| `fusion-rrf+w=0.7+d=100+c=10` | paraphrase | 25 | 0.658 (25) | 0.652 | 1.000 | 0.393 | 0.240 | 0.560 | 0.720 | 0.800 |
| `fusion-rrf+w=0.7+d=100+c=10` | known_item | 25 | 0.662 (25) | 0.556 | 1.000 | 0.950 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.7+d=100+c=100` | keyword | 25 | 0.736 (25) | 0.752 | 0.992 | 0.646 | 0.520 | 0.800 | 0.960 | 0.960 |
| `fusion-rrf+w=0.7+d=100+c=100` | question | 25 | 0.721 (25) | 0.736 | 1.000 | 0.560 | 0.440 | 0.720 | 0.760 | 0.800 |
| `fusion-rrf+w=0.7+d=100+c=100` | paraphrase | 25 | 0.653 (25) | 0.656 | 0.996 | 0.321 | 0.200 | 0.440 | 0.640 | 0.720 |
| `fusion-rrf+w=0.7+d=100+c=100` | known_item | 25 | 0.719 (25) | 0.636 | 1.000 | 0.947 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.7+d=100+c=30` | keyword | 25 | 0.715 (25) | 0.728 | 1.000 | 0.650 | 0.520 | 0.840 | 0.920 | 0.960 |
| `fusion-rrf+w=0.7+d=100+c=30` | question | 25 | 0.722 (25) | 0.736 | 1.000 | 0.577 | 0.440 | 0.760 | 0.760 | 0.840 |
| `fusion-rrf+w=0.7+d=100+c=30` | paraphrase | 25 | 0.670 (25) | 0.660 | 1.000 | 0.390 | 0.280 | 0.600 | 0.760 | 0.800 |
| `fusion-rrf+w=0.7+d=100+c=30` | known_item | 25 | 0.680 (25) | 0.580 | 1.000 | 0.950 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.7+d=100+c=60` | keyword | 25 | 0.728 (25) | 0.740 | 1.000 | 0.645 | 0.520 | 0.840 | 0.920 | 0.960 |
| `fusion-rrf+w=0.7+d=100+c=60` | question | 25 | 0.728 (25) | 0.748 | 1.000 | 0.567 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-rrf+w=0.7+d=100+c=60` | paraphrase | 25 | 0.660 (25) | 0.644 | 1.000 | 0.348 | 0.240 | 0.440 | 0.680 | 0.800 |
| `fusion-rrf+w=0.7+d=100+c=60` | known_item | 25 | 0.704 (25) | 0.616 | 1.000 | 0.950 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.75+d=100+c=10` | keyword | 25 | 0.682 (25) | 0.700 | 1.000 | 0.644 | 0.520 | 0.800 | 0.920 | 0.960 |
| `fusion-rrf+w=0.75+d=100+c=10` | question | 25 | 0.709 (25) | 0.708 | 1.000 | 0.593 | 0.480 | 0.760 | 0.800 | 0.840 |
| `fusion-rrf+w=0.75+d=100+c=10` | paraphrase | 25 | 0.666 (25) | 0.660 | 1.000 | 0.438 | 0.320 | 0.560 | 0.720 | 0.800 |
| `fusion-rrf+w=0.75+d=100+c=10` | known_item | 25 | 0.648 (25) | 0.536 | 1.000 | 0.940 | 0.920 | 0.960 | 1.000 | 1.000 |
| `fusion-rrf+w=0.75+d=100+c=100` | keyword | 25 | 0.731 (25) | 0.744 | 1.000 | 0.644 | 0.520 | 0.840 | 0.920 | 0.960 |
| `fusion-rrf+w=0.75+d=100+c=100` | question | 25 | 0.725 (25) | 0.748 | 1.000 | 0.565 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-rrf+w=0.75+d=100+c=100` | paraphrase | 25 | 0.654 (25) | 0.648 | 1.000 | 0.321 | 0.200 | 0.480 | 0.680 | 0.800 |
| `fusion-rrf+w=0.75+d=100+c=100` | known_item | 25 | 0.711 (25) | 0.620 | 1.000 | 0.943 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.75+d=100+c=30` | keyword | 25 | 0.709 (25) | 0.720 | 1.000 | 0.643 | 0.520 | 0.880 | 0.920 | 0.960 |
| `fusion-rrf+w=0.75+d=100+c=30` | question | 25 | 0.727 (25) | 0.724 | 1.000 | 0.608 | 0.480 | 0.760 | 0.800 | 0.840 |
| `fusion-rrf+w=0.75+d=100+c=30` | paraphrase | 25 | 0.665 (25) | 0.660 | 1.000 | 0.382 | 0.280 | 0.600 | 0.760 | 0.800 |
| `fusion-rrf+w=0.75+d=100+c=30` | known_item | 25 | 0.673 (25) | 0.568 | 1.000 | 0.943 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.75+d=100+c=60` | keyword | 25 | 0.726 (25) | 0.736 | 1.000 | 0.646 | 0.520 | 0.840 | 0.920 | 0.960 |
| `fusion-rrf+w=0.75+d=100+c=60` | question | 25 | 0.721 (25) | 0.736 | 1.000 | 0.573 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-rrf+w=0.75+d=100+c=60` | paraphrase | 25 | 0.670 (25) | 0.656 | 1.000 | 0.359 | 0.280 | 0.480 | 0.680 | 0.800 |
| `fusion-rrf+w=0.75+d=100+c=60` | known_item | 25 | 0.691 (25) | 0.592 | 1.000 | 0.943 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.75+d=20+c=10` | keyword | 25 | 0.672 (25) | 0.688 | 1.000 | 0.629 | 0.520 | 0.760 | 0.880 | 0.880 |
| `fusion-rrf+w=0.75+d=20+c=10` | question | 25 | 0.706 (25) | 0.704 | 1.000 | 0.599 | 0.480 | 0.760 | 0.800 | 0.840 |
| `fusion-rrf+w=0.75+d=20+c=10` | paraphrase | 25 | 0.662 (25) | 0.648 | 1.000 | 0.458 | 0.360 | 0.560 | 0.720 | 0.800 |
| `fusion-rrf+w=0.75+d=20+c=10` | known_item | 25 | 0.651 (25) | 0.540 | 1.000 | 0.947 | 0.920 | 0.960 | 1.000 | 1.000 |
| `fusion-rrf+w=0.75+d=20+c=100` | keyword | 25 | 0.695 (25) | 0.720 | 1.000 | 0.628 | 0.520 | 0.760 | 0.880 | 0.880 |
| `fusion-rrf+w=0.75+d=20+c=100` | question | 25 | 0.706 (25) | 0.708 | 1.000 | 0.565 | 0.440 | 0.720 | 0.800 | 0.840 |
| `fusion-rrf+w=0.75+d=20+c=100` | paraphrase | 25 | 0.639 (25) | 0.640 | 1.000 | 0.361 | 0.200 | 0.560 | 0.720 | 0.800 |
| `fusion-rrf+w=0.75+d=20+c=100` | known_item | 25 | 0.671 (25) | 0.564 | 1.000 | 0.947 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.75+d=20+c=60` | keyword | 25 | 0.695 (25) | 0.720 | 1.000 | 0.628 | 0.520 | 0.760 | 0.880 | 0.880 |
| `fusion-rrf+w=0.75+d=20+c=60` | question | 25 | 0.706 (25) | 0.708 | 1.000 | 0.565 | 0.440 | 0.720 | 0.800 | 0.840 |
| `fusion-rrf+w=0.75+d=20+c=60` | paraphrase | 25 | 0.639 (25) | 0.640 | 1.000 | 0.361 | 0.200 | 0.560 | 0.720 | 0.800 |
| `fusion-rrf+w=0.75+d=20+c=60` | known_item | 25 | 0.671 (25) | 0.564 | 1.000 | 0.947 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.75+d=50+c=10` | keyword | 25 | 0.682 (25) | 0.700 | 1.000 | 0.637 | 0.520 | 0.800 | 0.920 | 0.920 |
| `fusion-rrf+w=0.75+d=50+c=10` | question | 25 | 0.705 (25) | 0.704 | 1.000 | 0.596 | 0.480 | 0.760 | 0.800 | 0.840 |
| `fusion-rrf+w=0.75+d=50+c=10` | paraphrase | 25 | 0.663 (25) | 0.648 | 1.000 | 0.458 | 0.360 | 0.560 | 0.720 | 0.800 |
| `fusion-rrf+w=0.75+d=50+c=10` | known_item | 25 | 0.651 (25) | 0.540 | 1.000 | 0.940 | 0.920 | 0.960 | 1.000 | 1.000 |
| `fusion-rrf+w=0.75+d=50+c=100` | keyword | 25 | 0.718 (25) | 0.732 | 1.000 | 0.636 | 0.520 | 0.800 | 0.880 | 0.920 |
| `fusion-rrf+w=0.75+d=50+c=100` | question | 25 | 0.709 (25) | 0.740 | 1.000 | 0.569 | 0.440 | 0.760 | 0.800 | 0.840 |
| `fusion-rrf+w=0.75+d=50+c=100` | paraphrase | 25 | 0.641 (25) | 0.644 | 1.000 | 0.317 | 0.200 | 0.480 | 0.680 | 0.800 |
| `fusion-rrf+w=0.75+d=50+c=100` | known_item | 25 | 0.718 (25) | 0.628 | 1.000 | 0.947 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.75+d=50+c=60` | keyword | 25 | 0.723 (25) | 0.736 | 1.000 | 0.640 | 0.520 | 0.800 | 0.920 | 0.920 |
| `fusion-rrf+w=0.75+d=50+c=60` | question | 25 | 0.710 (25) | 0.728 | 1.000 | 0.578 | 0.440 | 0.760 | 0.800 | 0.840 |
| `fusion-rrf+w=0.75+d=50+c=60` | paraphrase | 25 | 0.659 (25) | 0.652 | 1.000 | 0.340 | 0.240 | 0.480 | 0.680 | 0.800 |
| `fusion-rrf+w=0.75+d=50+c=60` | known_item | 25 | 0.688 (25) | 0.588 | 1.000 | 0.947 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=1+d=100+c=10` | keyword | 25 | 0.642 (25) | 0.676 | 1.000 | 0.577 | 0.480 | 0.800 | 0.800 | 0.880 |
| `fusion-rrf+w=1+d=100+c=10` | question | 25 | 0.688 (25) | 0.704 | 1.000 | 0.560 | 0.440 | 0.720 | 0.800 | 0.840 |
| `fusion-rrf+w=1+d=100+c=10` | paraphrase | 25 | 0.644 (25) | 0.652 | 1.000 | 0.466 | 0.400 | 0.520 | 0.720 | 0.800 |
| `fusion-rrf+w=1+d=100+c=10` | known_item | 25 | 0.600 (25) | 0.516 | 1.000 | 0.793 | 0.680 | 0.920 | 0.960 | 1.000 |
| `fusion-shortlist+a=0.5+d=100` | keyword | 25 | 0.731 (25) | 0.744 | 1.000 | 0.674 | 0.520 | 0.880 | 0.960 | 0.960 |
| `fusion-shortlist+a=0.5+d=100` | question | 25 | 0.718 (25) | 0.740 | 1.000 | 0.565 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-shortlist+a=0.5+d=100` | paraphrase | 25 | 0.663 (25) | 0.648 | 1.000 | 0.380 | 0.280 | 0.440 | 0.720 | 0.800 |
| `fusion-shortlist+a=0.5+d=100` | known_item | 25 | 0.715 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-shortlist+a=0.5+d=500` | keyword | 25 | 0.730 (25) | 0.744 | 1.000 | 0.674 | 0.520 | 0.880 | 0.960 | 0.960 |
| `fusion-shortlist+a=0.5+d=500` | question | 25 | 0.716 (25) | 0.740 | 1.000 | 0.562 | 0.440 | 0.720 | 0.760 | 0.800 |
| `fusion-shortlist+a=0.5+d=500` | paraphrase | 25 | 0.667 (25) | 0.648 | 1.000 | 0.391 | 0.280 | 0.480 | 0.720 | 0.800 |
| `fusion-shortlist+a=0.5+d=500` | known_item | 25 | 0.716 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-shortlist+a=1+d=100` | keyword | 25 | 0.740 (25) | 0.744 | 1.000 | 0.720 | 0.600 | 0.880 | 0.960 | 0.960 |
| `fusion-shortlist+a=1+d=100` | question | 25 | 0.731 (25) | 0.740 | 1.000 | 0.591 | 0.480 | 0.760 | 0.760 | 0.800 |
| `fusion-shortlist+a=1+d=100` | paraphrase | 25 | 0.666 (25) | 0.648 | 1.000 | 0.403 | 0.320 | 0.440 | 0.720 | 0.800 |
| `fusion-shortlist+a=1+d=100` | known_item | 25 | 0.718 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-shortlist+a=1+d=500` | keyword | 25 | 0.739 (25) | 0.744 | 1.000 | 0.720 | 0.600 | 0.880 | 0.960 | 0.960 |
| `fusion-shortlist+a=1+d=500` | question | 25 | 0.728 (25) | 0.740 | 1.000 | 0.588 | 0.480 | 0.720 | 0.760 | 0.800 |
| `fusion-shortlist+a=1+d=500` | paraphrase | 25 | 0.686 (25) | 0.648 | 1.000 | 0.498 | 0.400 | 0.600 | 0.720 | 0.800 |
| `fusion-shortlist+a=1+d=500` | known_item | 25 | 0.718 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-top1bonus+b=0.1+w=0.55+d=100+c=30` | keyword | 25 | 0.729 (25) | 0.744 | 1.000 | 0.686 | 0.560 | 0.880 | 0.960 | 0.960 |
| `fusion-top1bonus+b=0.1+w=0.55+d=100+c=30` | question | 25 | 0.722 (25) | 0.748 | 1.000 | 0.563 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-top1bonus+b=0.1+w=0.55+d=100+c=30` | paraphrase | 25 | 0.655 (25) | 0.640 | 1.000 | 0.383 | 0.280 | 0.520 | 0.680 | 0.800 |
| `fusion-top1bonus+b=0.1+w=0.55+d=100+c=30` | known_item | 25 | 0.713 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-top1bonus+b=0.25+w=0.55+d=100+c=30` | keyword | 25 | 0.726 (25) | 0.740 | 1.000 | 0.707 | 0.600 | 0.920 | 0.960 | 0.960 |
| `fusion-top1bonus+b=0.25+w=0.55+d=100+c=30` | question | 25 | 0.726 (25) | 0.748 | 1.000 | 0.541 | 0.400 | 0.720 | 0.760 | 0.800 |
| `fusion-top1bonus+b=0.25+w=0.55+d=100+c=30` | paraphrase | 25 | 0.644 (25) | 0.636 | 1.000 | 0.382 | 0.280 | 0.520 | 0.680 | 0.800 |
| `fusion-top1bonus+b=0.25+w=0.55+d=100+c=30` | known_item | 25 | 0.713 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `hybrid-bge-small+linear+w=0.25` | keyword | 25 | 0.693 (25) | 0.688 | 0.960 | 0.700 | 0.520 | 0.880 | 0.920 | 0.920 |
| `hybrid-bge-small+linear+w=0.25` | question | 25 | 0.561 (25) | 0.528 | 0.952 | 0.521 | 0.440 | 0.640 | 0.680 | 0.720 |
| `hybrid-bge-small+linear+w=0.25` | paraphrase | 25 | 0.467 (25) | 0.504 | 0.956 | 0.178 | 0.080 | 0.320 | 0.360 | 0.360 |
| `hybrid-bge-small+linear+w=0.25` | known_item | 25 | 0.705 (25) | 0.612 | 0.956 | 0.948 | 0.920 | 1.000 | 1.000 | 1.000 |
| `hybrid-bge-small+linear+w=0.5` | keyword | 25 | 0.688 (25) | 0.676 | 0.896 | 0.653 | 0.480 | 0.880 | 0.880 | 0.960 |
| `hybrid-bge-small+linear+w=0.5` | question | 25 | 0.613 (25) | 0.592 | 0.880 | 0.519 | 0.440 | 0.600 | 0.720 | 0.760 |
| `hybrid-bge-small+linear+w=0.5` | paraphrase | 25 | 0.504 (25) | 0.528 | 0.872 | 0.211 | 0.120 | 0.320 | 0.560 | 0.600 |
| `hybrid-bge-small+linear+w=0.5` | known_item | 25 | 0.704 (25) | 0.608 | 0.908 | 0.891 | 0.840 | 0.960 | 1.000 | 1.000 |
| `hybrid-bge-small+linear+w=0.75` | keyword | 25 | 0.672 (25) | 0.656 | 0.924 | 0.667 | 0.560 | 0.840 | 0.920 | 0.960 |
| `hybrid-bge-small+linear+w=0.75` | question | 25 | 0.644 (25) | 0.652 | 0.956 | 0.495 | 0.400 | 0.640 | 0.680 | 0.760 |
| `hybrid-bge-small+linear+w=0.75` | paraphrase | 25 | 0.495 (25) | 0.528 | 0.932 | 0.217 | 0.120 | 0.360 | 0.400 | 0.640 |
| `hybrid-bge-small+linear+w=0.75` | known_item | 25 | 0.705 (25) | 0.612 | 0.944 | 0.856 | 0.800 | 0.920 | 0.960 | 0.960 |
| `hybrid-bge-small+rrf+w=0.25+c=10` | keyword | 25 | 0.660 (25) | 0.648 | 0.996 | 0.727 | 0.560 | 0.920 | 0.920 | 0.960 |
| `hybrid-bge-small+rrf+w=0.25+c=10` | question | 25 | 0.501 (25) | 0.484 | 1.000 | 0.485 | 0.400 | 0.560 | 0.680 | 0.720 |
| `hybrid-bge-small+rrf+w=0.25+c=10` | paraphrase | 25 | 0.384 (25) | 0.448 | 1.000 | 0.152 | 0.080 | 0.240 | 0.320 | 0.360 |
| `hybrid-bge-small+rrf+w=0.25+c=10` | known_item | 25 | 0.682 (25) | 0.600 | 0.988 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `hybrid-bge-small+rrf+w=0.25+c=100` | keyword | 25 | 0.679 (25) | 0.660 | 0.920 | 0.700 | 0.520 | 0.880 | 0.920 | 0.920 |
| `hybrid-bge-small+rrf+w=0.25+c=100` | question | 25 | 0.588 (25) | 0.568 | 0.920 | 0.522 | 0.440 | 0.640 | 0.680 | 0.720 |
| `hybrid-bge-small+rrf+w=0.25+c=100` | paraphrase | 25 | 0.488 (25) | 0.520 | 0.900 | 0.180 | 0.080 | 0.320 | 0.400 | 0.440 |
| `hybrid-bge-small+rrf+w=0.25+c=100` | known_item | 25 | 0.706 (25) | 0.616 | 0.940 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `hybrid-bge-small+rrf+w=0.25+c=60` | keyword | 25 | 0.679 (25) | 0.668 | 0.964 | 0.703 | 0.520 | 0.920 | 0.920 | 0.920 |
| `hybrid-bge-small+rrf+w=0.25+c=60` | question | 25 | 0.569 (25) | 0.540 | 0.948 | 0.520 | 0.440 | 0.640 | 0.680 | 0.720 |
| `hybrid-bge-small+rrf+w=0.25+c=60` | paraphrase | 25 | 0.464 (25) | 0.516 | 0.952 | 0.157 | 0.040 | 0.320 | 0.360 | 0.400 |
| `hybrid-bge-small+rrf+w=0.25+c=60` | known_item | 25 | 0.706 (25) | 0.624 | 0.972 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `hybrid-bge-small+rrf+w=0.5+c=10` | keyword | 25 | 0.696 (25) | 0.692 | 1.000 | 0.709 | 0.560 | 0.960 | 0.960 | 0.960 |
| `hybrid-bge-small+rrf+w=0.5+c=10` | question | 25 | 0.622 (25) | 0.616 | 1.000 | 0.536 | 0.440 | 0.680 | 0.720 | 0.760 |
| `hybrid-bge-small+rrf+w=0.5+c=10` | paraphrase | 25 | 0.480 (25) | 0.528 | 1.000 | 0.232 | 0.120 | 0.440 | 0.480 | 0.680 |
| `hybrid-bge-small+rrf+w=0.5+c=10` | known_item | 25 | 0.714 (25) | 0.620 | 1.000 | 0.930 | 0.880 | 1.000 | 1.000 | 1.000 |
| `hybrid-bge-small+rrf+w=0.5+c=100` | keyword | 25 | 0.691 (25) | 0.672 | 0.876 | 0.673 | 0.520 | 0.880 | 0.880 | 0.960 |
| `hybrid-bge-small+rrf+w=0.5+c=100` | question | 25 | 0.604 (25) | 0.576 | 0.852 | 0.514 | 0.440 | 0.640 | 0.680 | 0.760 |
| `hybrid-bge-small+rrf+w=0.5+c=100` | paraphrase | 25 | 0.507 (25) | 0.520 | 0.820 | 0.233 | 0.160 | 0.400 | 0.520 | 0.560 |
| `hybrid-bge-small+rrf+w=0.5+c=100` | known_item | 25 | 0.705 (25) | 0.608 | 0.880 | 0.891 | 0.840 | 0.960 | 1.000 | 1.000 |
| `hybrid-bge-small+rrf+w=0.5+c=60` | keyword | 25 | 0.697 (25) | 0.680 | 0.904 | 0.673 | 0.520 | 0.880 | 0.880 | 0.960 |
| `hybrid-bge-small+rrf+w=0.5+c=60` | question | 25 | 0.615 (25) | 0.600 | 0.876 | 0.516 | 0.440 | 0.640 | 0.680 | 0.760 |
| `hybrid-bge-small+rrf+w=0.5+c=60` | paraphrase | 25 | 0.506 (25) | 0.516 | 0.844 | 0.240 | 0.160 | 0.360 | 0.560 | 0.560 |
| `hybrid-bge-small+rrf+w=0.5+c=60` | known_item | 25 | 0.705 (25) | 0.604 | 0.884 | 0.892 | 0.840 | 0.960 | 1.000 | 1.000 |
| `hybrid-bge-small+rrf+w=0.75+c=10` | keyword | 25 | 0.657 (25) | 0.672 | 1.000 | 0.656 | 0.560 | 0.760 | 0.880 | 0.960 |
| `hybrid-bge-small+rrf+w=0.75+c=10` | question | 25 | 0.627 (25) | 0.648 | 0.992 | 0.475 | 0.400 | 0.600 | 0.680 | 0.760 |
| `hybrid-bge-small+rrf+w=0.75+c=10` | paraphrase | 25 | 0.487 (25) | 0.532 | 0.996 | 0.281 | 0.200 | 0.360 | 0.520 | 0.640 |
| `hybrid-bge-small+rrf+w=0.75+c=10` | known_item | 25 | 0.679 (25) | 0.612 | 1.000 | 0.797 | 0.720 | 0.880 | 0.960 | 1.000 |
| `hybrid-bge-small+rrf+w=0.75+c=100` | keyword | 25 | 0.672 (25) | 0.660 | 0.880 | 0.666 | 0.560 | 0.880 | 0.920 | 0.960 |
| `hybrid-bge-small+rrf+w=0.75+c=100` | question | 25 | 0.624 (25) | 0.616 | 0.884 | 0.491 | 0.400 | 0.600 | 0.720 | 0.760 |
| `hybrid-bge-small+rrf+w=0.75+c=100` | paraphrase | 25 | 0.507 (25) | 0.544 | 0.892 | 0.239 | 0.160 | 0.360 | 0.440 | 0.680 |
| `hybrid-bge-small+rrf+w=0.75+c=100` | known_item | 25 | 0.701 (25) | 0.596 | 0.920 | 0.856 | 0.800 | 0.920 | 0.960 | 1.000 |
| `hybrid-bge-small+rrf+w=0.75+c=60` | keyword | 25 | 0.672 (25) | 0.664 | 0.936 | 0.665 | 0.560 | 0.880 | 0.920 | 0.960 |
| `hybrid-bge-small+rrf+w=0.75+c=60` | question | 25 | 0.641 (25) | 0.648 | 0.948 | 0.482 | 0.400 | 0.640 | 0.680 | 0.800 |
| `hybrid-bge-small+rrf+w=0.75+c=60` | paraphrase | 25 | 0.491 (25) | 0.532 | 0.924 | 0.242 | 0.160 | 0.360 | 0.440 | 0.640 |
| `hybrid-bge-small+rrf+w=0.75+c=60` | known_item | 25 | 0.706 (25) | 0.612 | 0.960 | 0.856 | 0.800 | 0.920 | 0.960 | 0.960 |
| `hybrid-gte-small+linear+w=0.25` | keyword | 25 | 0.663 (25) | 0.636 | 0.944 | 0.677 | 0.520 | 0.920 | 0.920 | 0.920 |
| `hybrid-gte-small+linear+w=0.25` | question | 25 | 0.575 (25) | 0.560 | 0.968 | 0.522 | 0.440 | 0.640 | 0.680 | 0.720 |
| `hybrid-gte-small+linear+w=0.25` | paraphrase | 25 | 0.467 (25) | 0.516 | 0.964 | 0.172 | 0.040 | 0.320 | 0.360 | 0.400 |
| `hybrid-gte-small+linear+w=0.25` | known_item | 25 | 0.717 (25) | 0.624 | 0.948 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `hybrid-gte-small+linear+w=0.5` | keyword | 25 | 0.684 (25) | 0.644 | 0.864 | 0.707 | 0.600 | 0.800 | 0.840 | 0.960 |
| `hybrid-gte-small+linear+w=0.5` | question | 25 | 0.612 (25) | 0.612 | 0.892 | 0.531 | 0.440 | 0.640 | 0.680 | 0.760 |
| `hybrid-gte-small+linear+w=0.5` | paraphrase | 25 | 0.525 (25) | 0.560 | 0.896 | 0.255 | 0.120 | 0.440 | 0.520 | 0.520 |
| `hybrid-gte-small+linear+w=0.5` | known_item | 25 | 0.703 (25) | 0.596 | 0.888 | 0.920 | 0.880 | 1.000 | 1.000 | 1.000 |
| `hybrid-gte-small+linear+w=0.75` | keyword | 25 | 0.694 (25) | 0.668 | 0.924 | 0.712 | 0.640 | 0.800 | 0.880 | 0.880 |
| `hybrid-gte-small+linear+w=0.75` | question | 25 | 0.633 (25) | 0.656 | 0.960 | 0.469 | 0.320 | 0.640 | 0.720 | 0.800 |
| `hybrid-gte-small+linear+w=0.75` | paraphrase | 25 | 0.544 (25) | 0.568 | 0.952 | 0.298 | 0.160 | 0.480 | 0.480 | 0.640 |
| `hybrid-gte-small+linear+w=0.75` | known_item | 25 | 0.681 (25) | 0.592 | 0.952 | 0.801 | 0.720 | 0.920 | 0.960 | 1.000 |
| `hybrid-gte-small+rrf+w=0.25+c=10` | keyword | 25 | 0.654 (25) | 0.640 | 1.000 | 0.707 | 0.560 | 0.880 | 0.920 | 0.960 |
| `hybrid-gte-small+rrf+w=0.25+c=10` | question | 25 | 0.497 (25) | 0.480 | 1.000 | 0.479 | 0.400 | 0.560 | 0.680 | 0.720 |
| `hybrid-gte-small+rrf+w=0.25+c=10` | paraphrase | 25 | 0.389 (25) | 0.448 | 1.000 | 0.151 | 0.080 | 0.240 | 0.280 | 0.400 |
| `hybrid-gte-small+rrf+w=0.25+c=10` | known_item | 25 | 0.697 (25) | 0.620 | 0.996 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `hybrid-gte-small+rrf+w=0.25+c=100` | keyword | 25 | 0.669 (25) | 0.640 | 0.908 | 0.672 | 0.520 | 0.880 | 0.920 | 0.920 |
| `hybrid-gte-small+rrf+w=0.25+c=100` | question | 25 | 0.582 (25) | 0.576 | 0.928 | 0.519 | 0.440 | 0.640 | 0.680 | 0.720 |
| `hybrid-gte-small+rrf+w=0.25+c=100` | paraphrase | 25 | 0.497 (25) | 0.536 | 0.908 | 0.191 | 0.080 | 0.320 | 0.360 | 0.440 |
| `hybrid-gte-small+rrf+w=0.25+c=100` | known_item | 25 | 0.712 (25) | 0.612 | 0.928 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `hybrid-gte-small+rrf+w=0.25+c=60` | keyword | 25 | 0.672 (25) | 0.660 | 0.964 | 0.677 | 0.520 | 0.920 | 0.920 | 0.920 |
| `hybrid-gte-small+rrf+w=0.25+c=60` | question | 25 | 0.567 (25) | 0.552 | 0.952 | 0.519 | 0.440 | 0.640 | 0.680 | 0.720 |
| `hybrid-gte-small+rrf+w=0.25+c=60` | paraphrase | 25 | 0.473 (25) | 0.516 | 0.956 | 0.175 | 0.080 | 0.320 | 0.320 | 0.400 |
| `hybrid-gte-small+rrf+w=0.25+c=60` | known_item | 25 | 0.714 (25) | 0.616 | 0.956 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `hybrid-gte-small+rrf+w=0.5+c=10` | keyword | 25 | 0.708 (25) | 0.688 | 1.000 | 0.728 | 0.600 | 0.920 | 0.960 | 0.960 |
| `hybrid-gte-small+rrf+w=0.5+c=10` | question | 25 | 0.602 (25) | 0.596 | 1.000 | 0.518 | 0.400 | 0.640 | 0.720 | 0.760 |
| `hybrid-gte-small+rrf+w=0.5+c=10` | paraphrase | 25 | 0.514 (25) | 0.556 | 1.000 | 0.321 | 0.200 | 0.480 | 0.520 | 0.640 |
| `hybrid-gte-small+rrf+w=0.5+c=10` | known_item | 25 | 0.700 (25) | 0.604 | 1.000 | 0.973 | 0.960 | 1.000 | 1.000 | 1.000 |
| `hybrid-gte-small+rrf+w=0.5+c=100` | keyword | 25 | 0.681 (25) | 0.624 | 0.840 | 0.701 | 0.600 | 0.800 | 0.880 | 0.960 |
| `hybrid-gte-small+rrf+w=0.5+c=100` | question | 25 | 0.610 (25) | 0.596 | 0.860 | 0.507 | 0.400 | 0.640 | 0.680 | 0.760 |
| `hybrid-gte-small+rrf+w=0.5+c=100` | paraphrase | 25 | 0.517 (25) | 0.536 | 0.840 | 0.276 | 0.160 | 0.440 | 0.520 | 0.520 |
| `hybrid-gte-small+rrf+w=0.5+c=100` | known_item | 25 | 0.707 (25) | 0.608 | 0.876 | 0.920 | 0.880 | 1.000 | 1.000 | 1.000 |
| `hybrid-gte-small+rrf+w=0.5+c=60` | keyword | 25 | 0.686 (25) | 0.636 | 0.876 | 0.702 | 0.600 | 0.800 | 0.880 | 0.960 |
| `hybrid-gte-small+rrf+w=0.5+c=60` | question | 25 | 0.615 (25) | 0.608 | 0.876 | 0.507 | 0.400 | 0.640 | 0.680 | 0.760 |
| `hybrid-gte-small+rrf+w=0.5+c=60` | paraphrase | 25 | 0.524 (25) | 0.544 | 0.860 | 0.282 | 0.160 | 0.400 | 0.520 | 0.520 |
| `hybrid-gte-small+rrf+w=0.5+c=60` | known_item | 25 | 0.706 (25) | 0.604 | 0.892 | 0.920 | 0.880 | 1.000 | 1.000 | 1.000 |
| `hybrid-gte-small+rrf+w=0.75+c=10` | keyword | 25 | 0.675 (25) | 0.656 | 0.996 | 0.703 | 0.600 | 0.840 | 0.840 | 0.920 |
| `hybrid-gte-small+rrf+w=0.75+c=10` | question | 25 | 0.624 (25) | 0.656 | 1.000 | 0.469 | 0.360 | 0.640 | 0.720 | 0.800 |
| `hybrid-gte-small+rrf+w=0.75+c=10` | paraphrase | 25 | 0.527 (25) | 0.552 | 0.992 | 0.366 | 0.280 | 0.480 | 0.520 | 0.680 |
| `hybrid-gte-small+rrf+w=0.75+c=10` | known_item | 25 | 0.640 (25) | 0.564 | 1.000 | 0.766 | 0.680 | 0.880 | 0.960 | 1.000 |
| `hybrid-gte-small+rrf+w=0.75+c=100` | keyword | 25 | 0.695 (25) | 0.664 | 0.892 | 0.714 | 0.640 | 0.800 | 0.880 | 0.920 |
| `hybrid-gte-small+rrf+w=0.75+c=100` | question | 25 | 0.636 (25) | 0.652 | 0.936 | 0.468 | 0.320 | 0.640 | 0.720 | 0.800 |
| `hybrid-gte-small+rrf+w=0.75+c=100` | paraphrase | 25 | 0.545 (25) | 0.560 | 0.896 | 0.323 | 0.240 | 0.400 | 0.480 | 0.600 |
| `hybrid-gte-small+rrf+w=0.75+c=100` | known_item | 25 | 0.686 (25) | 0.600 | 0.916 | 0.805 | 0.720 | 0.920 | 1.000 | 1.000 |
| `hybrid-gte-small+rrf+w=0.75+c=60` | keyword | 25 | 0.692 (25) | 0.664 | 0.924 | 0.716 | 0.640 | 0.840 | 0.880 | 0.920 |
| `hybrid-gte-small+rrf+w=0.75+c=60` | question | 25 | 0.645 (25) | 0.664 | 0.968 | 0.489 | 0.360 | 0.640 | 0.720 | 0.800 |
| `hybrid-gte-small+rrf+w=0.75+c=60` | paraphrase | 25 | 0.557 (25) | 0.580 | 0.944 | 0.333 | 0.240 | 0.480 | 0.480 | 0.640 |
| `hybrid-gte-small+rrf+w=0.75+c=60` | known_item | 25 | 0.686 (25) | 0.600 | 0.960 | 0.806 | 0.720 | 0.920 | 1.000 | 1.000 |
| `hybrid-openai-large+rrf+w=0.5+c=10` | keyword | 25 | 0.696 (25) | 0.692 | 1.000 | 0.717 | 0.600 | 0.920 | 0.960 | 1.000 |
| `hybrid-openai-large+rrf+w=0.5+c=10` | question | 25 | 0.662 (25) | 0.660 | 1.000 | 0.553 | 0.440 | 0.760 | 0.760 | 0.800 |
| `hybrid-openai-large+rrf+w=0.5+c=10` | paraphrase | 25 | 0.591 (25) | 0.576 | 1.000 | 0.364 | 0.240 | 0.520 | 0.640 | 0.800 |
| `hybrid-openai-large+rrf+w=0.5+c=10` | known_item | 25 | 0.692 (25) | 0.604 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `oai-field+text=concat+d=10` | keyword | 25 | 0.716 (25) | 0.744 | 1.000 | 0.606 | 0.480 | 0.800 | 0.960 | 0.960 |
| `oai-field+text=concat+d=10` | question | 25 | 0.710 (25) | 0.740 | 1.000 | 0.558 | 0.440 | 0.720 | 0.760 | 0.800 |
| `oai-field+text=concat+d=10` | paraphrase | 25 | 0.658 (25) | 0.648 | 1.000 | 0.469 | 0.400 | 0.560 | 0.720 | 0.800 |
| `oai-field+text=concat+d=10` | known_item | 25 | 0.677 (25) | 0.624 | 1.000 | 0.802 | 0.680 | 0.920 | 1.000 | 1.000 |
| `oai-field+text=concat+d=100` | keyword | 25 | 0.642 (25) | 0.676 | 1.000 | 0.577 | 0.480 | 0.800 | 0.800 | 0.880 |
| `oai-field+text=concat+d=100` | question | 25 | 0.688 (25) | 0.704 | 1.000 | 0.560 | 0.440 | 0.720 | 0.800 | 0.840 |
| `oai-field+text=concat+d=100` | paraphrase | 25 | 0.644 (25) | 0.652 | 1.000 | 0.466 | 0.400 | 0.520 | 0.720 | 0.800 |
| `oai-field+text=concat+d=100` | known_item | 25 | 0.600 (25) | 0.516 | 1.000 | 0.793 | 0.680 | 0.920 | 0.960 | 1.000 |
| `oai-field+text=title25+d=10` | keyword | 25 | 0.718 (25) | 0.744 | 1.000 | 0.604 | 0.440 | 0.760 | 0.960 | 0.960 |
| `oai-field+text=title25+d=10` | question | 25 | 0.713 (25) | 0.740 | 1.000 | 0.607 | 0.480 | 0.720 | 0.760 | 0.800 |
| `oai-field+text=title25+d=10` | paraphrase | 25 | 0.673 (25) | 0.648 | 1.000 | 0.438 | 0.360 | 0.520 | 0.720 | 0.800 |
| `oai-field+text=title25+d=10` | known_item | 25 | 0.701 (25) | 0.624 | 1.000 | 0.873 | 0.800 | 0.960 | 1.000 | 1.000 |
| `oai-field+text=title25+d=100` | keyword | 25 | 0.631 (25) | 0.604 | 0.876 | 0.568 | 0.440 | 0.720 | 0.800 | 0.920 |
| `oai-field+text=title25+d=100` | question | 25 | 0.680 (25) | 0.672 | 0.892 | 0.612 | 0.480 | 0.760 | 0.800 | 0.880 |
| `oai-field+text=title25+d=100` | paraphrase | 25 | 0.594 (25) | 0.544 | 0.832 | 0.427 | 0.360 | 0.520 | 0.640 | 0.760 |
| `oai-field+text=title25+d=100` | known_item | 25 | 0.604 (25) | 0.488 | 0.824 | 0.866 | 0.800 | 0.960 | 1.000 | 1.000 |
| `oai-field+text=title50+d=10` | keyword | 25 | 0.719 (25) | 0.744 | 1.000 | 0.611 | 0.480 | 0.760 | 0.960 | 0.960 |
| `oai-field+text=title50+d=10` | question | 25 | 0.701 (25) | 0.740 | 1.000 | 0.537 | 0.360 | 0.760 | 0.760 | 0.800 |
| `oai-field+text=title50+d=10` | paraphrase | 25 | 0.649 (25) | 0.648 | 1.000 | 0.438 | 0.360 | 0.520 | 0.720 | 0.800 |
| `oai-field+text=title50+d=10` | known_item | 25 | 0.692 (25) | 0.624 | 1.000 | 0.830 | 0.720 | 1.000 | 1.000 | 1.000 |
| `oai-field+text=title50+d=100` | keyword | 25 | 0.613 (25) | 0.580 | 0.792 | 0.589 | 0.480 | 0.760 | 0.800 | 0.800 |
| `oai-field+text=title50+d=100` | question | 25 | 0.633 (25) | 0.620 | 0.812 | 0.554 | 0.360 | 0.800 | 0.840 | 0.880 |
| `oai-field+text=title50+d=100` | paraphrase | 25 | 0.550 (25) | 0.520 | 0.800 | 0.432 | 0.360 | 0.560 | 0.600 | 0.680 |
| `oai-field+text=title50+d=100` | known_item | 25 | 0.596 (25) | 0.476 | 0.792 | 0.821 | 0.720 | 1.000 | 1.000 | 1.000 |
| `oai-field+text=title75+d=10` | keyword | 25 | 0.723 (25) | 0.744 | 1.000 | 0.597 | 0.480 | 0.720 | 0.960 | 0.960 |
| `oai-field+text=title75+d=10` | question | 25 | 0.687 (25) | 0.740 | 1.000 | 0.455 | 0.280 | 0.760 | 0.760 | 0.800 |
| `oai-field+text=title75+d=10` | paraphrase | 25 | 0.632 (25) | 0.648 | 1.000 | 0.438 | 0.360 | 0.520 | 0.720 | 0.800 |
| `oai-field+text=title75+d=10` | known_item | 25 | 0.682 (25) | 0.624 | 1.000 | 0.798 | 0.640 | 0.960 | 1.000 | 1.000 |
| `oai-field+text=title75+d=100` | keyword | 25 | 0.561 (25) | 0.528 | 0.708 | 0.520 | 0.440 | 0.680 | 0.720 | 0.720 |
| `oai-field+text=title75+d=100` | question | 25 | 0.551 (25) | 0.544 | 0.736 | 0.463 | 0.320 | 0.600 | 0.880 | 0.880 |
| `oai-field+text=title75+d=100` | paraphrase | 25 | 0.482 (25) | 0.452 | 0.704 | 0.414 | 0.360 | 0.520 | 0.600 | 0.640 |
| `oai-field+text=title75+d=100` | known_item | 25 | 0.575 (25) | 0.464 | 0.744 | 0.765 | 0.640 | 0.960 | 0.960 | 0.960 |
| `oai-field-hybrid+text=concat+d=10` | keyword | 25 | 0.739 (25) | 0.744 | 1.000 | 0.720 | 0.600 | 0.880 | 0.960 | 0.960 |
| `oai-field-hybrid+text=concat+d=10` | question | 25 | 0.728 (25) | 0.740 | 1.000 | 0.588 | 0.480 | 0.720 | 0.760 | 0.800 |
| `oai-field-hybrid+text=concat+d=10` | paraphrase | 25 | 0.686 (25) | 0.648 | 1.000 | 0.498 | 0.400 | 0.600 | 0.720 | 0.800 |
| `oai-field-hybrid+text=concat+d=10` | known_item | 25 | 0.718 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `oai-field-hybrid+text=concat+d=100` | keyword | 25 | 0.732 (25) | 0.740 | 1.000 | 0.716 | 0.600 | 0.880 | 0.920 | 0.960 |
| `oai-field-hybrid+text=concat+d=100` | question | 25 | 0.725 (25) | 0.732 | 1.000 | 0.583 | 0.480 | 0.720 | 0.720 | 0.760 |
| `oai-field-hybrid+text=concat+d=100` | paraphrase | 25 | 0.693 (25) | 0.680 | 1.000 | 0.487 | 0.400 | 0.600 | 0.640 | 0.640 |
| `oai-field-hybrid+text=concat+d=100` | known_item | 25 | 0.726 (25) | 0.636 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `oai-field-hybrid+text=title25+d=10` | keyword | 25 | 0.745 (25) | 0.744 | 1.000 | 0.746 | 0.640 | 0.840 | 0.960 | 0.960 |
| `oai-field-hybrid+text=title25+d=10` | question | 25 | 0.732 (25) | 0.740 | 1.000 | 0.625 | 0.560 | 0.720 | 0.760 | 0.800 |
| `oai-field-hybrid+text=title25+d=10` | paraphrase | 25 | 0.681 (25) | 0.648 | 1.000 | 0.467 | 0.400 | 0.560 | 0.720 | 0.800 |
| `oai-field-hybrid+text=title25+d=10` | known_item | 25 | 0.724 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `oai-field-hybrid+text=title25+d=100` | keyword | 25 | 0.736 (25) | 0.724 | 0.956 | 0.742 | 0.640 | 0.840 | 0.920 | 0.960 |
| `oai-field-hybrid+text=title25+d=100` | question | 25 | 0.729 (25) | 0.736 | 0.976 | 0.625 | 0.560 | 0.720 | 0.760 | 0.760 |
| `oai-field-hybrid+text=title25+d=100` | paraphrase | 25 | 0.676 (25) | 0.656 | 0.960 | 0.458 | 0.400 | 0.560 | 0.640 | 0.640 |
| `oai-field-hybrid+text=title25+d=100` | known_item | 25 | 0.733 (25) | 0.632 | 0.956 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `oai-field-hybrid+text=title50+d=10` | keyword | 25 | 0.749 (25) | 0.744 | 1.000 | 0.729 | 0.600 | 0.840 | 0.960 | 0.960 |
| `oai-field-hybrid+text=title50+d=10` | question | 25 | 0.723 (25) | 0.740 | 1.000 | 0.572 | 0.480 | 0.720 | 0.760 | 0.800 |
| `oai-field-hybrid+text=title50+d=10` | paraphrase | 25 | 0.659 (25) | 0.648 | 1.000 | 0.434 | 0.360 | 0.480 | 0.720 | 0.800 |
| `oai-field-hybrid+text=title50+d=10` | known_item | 25 | 0.719 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `oai-field-hybrid+text=title50+d=100` | keyword | 25 | 0.727 (25) | 0.708 | 0.936 | 0.724 | 0.600 | 0.840 | 0.920 | 0.960 |
| `oai-field-hybrid+text=title50+d=100` | question | 25 | 0.707 (25) | 0.720 | 0.944 | 0.587 | 0.480 | 0.760 | 0.760 | 0.760 |
| `oai-field-hybrid+text=title50+d=100` | paraphrase | 25 | 0.616 (25) | 0.600 | 0.932 | 0.416 | 0.360 | 0.480 | 0.600 | 0.640 |
| `oai-field-hybrid+text=title50+d=100` | known_item | 25 | 0.724 (25) | 0.632 | 0.936 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `oai-field-hybrid+text=title75+d=10` | keyword | 25 | 0.736 (25) | 0.744 | 1.000 | 0.664 | 0.520 | 0.840 | 0.960 | 0.960 |
| `oai-field-hybrid+text=title75+d=10` | question | 25 | 0.714 (25) | 0.740 | 1.000 | 0.575 | 0.480 | 0.720 | 0.760 | 0.800 |
| `oai-field-hybrid+text=title75+d=10` | paraphrase | 25 | 0.651 (25) | 0.648 | 1.000 | 0.428 | 0.360 | 0.480 | 0.720 | 0.800 |
| `oai-field-hybrid+text=title75+d=10` | known_item | 25 | 0.709 (25) | 0.624 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 |
| `oai-field-hybrid+text=title75+d=100` | keyword | 25 | 0.670 (25) | 0.640 | 0.864 | 0.657 | 0.520 | 0.800 | 0.920 | 0.920 |
| `oai-field-hybrid+text=title75+d=100` | question | 25 | 0.650 (25) | 0.628 | 0.880 | 0.610 | 0.520 | 0.760 | 0.760 | 0.760 |
| `oai-field-hybrid+text=title75+d=100` | paraphrase | 25 | 0.598 (25) | 0.596 | 0.888 | 0.404 | 0.360 | 0.480 | 0.560 | 0.600 |
| `oai-field-hybrid+text=title75+d=100` | known_item | 25 | 0.695 (25) | 0.596 | 0.904 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 |
| `oai-field-recovery+text=abstract+anchor=0+d=10` | keyword | 25 | 0.739 (25) | 0.744 | 1.000 | 0.681 | 0.520 | 0.880 | 0.960 | 0.960 |
| `oai-field-recovery+text=abstract+anchor=0+d=10` | question | 25 | 0.726 (25) | 0.740 | 1.000 | 0.609 | 0.520 | 0.680 | 0.760 | 0.800 |
| `oai-field-recovery+text=abstract+anchor=0+d=10` | paraphrase | 25 | 0.696 (25) | 0.648 | 1.000 | 0.449 | 0.320 | 0.600 | 0.720 | 0.800 |
| `oai-field-recovery+text=abstract+anchor=0+d=10` | known_item | 25 | 0.723 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `oai-field-recovery+text=concat+anchor=1+d=10` | keyword | 25 | 0.739 (25) | 0.744 | 1.000 | 0.720 | 0.600 | 0.880 | 0.960 | 0.960 |
| `oai-field-recovery+text=concat+anchor=1+d=10` | question | 25 | 0.728 (25) | 0.740 | 1.000 | 0.588 | 0.480 | 0.720 | 0.760 | 0.800 |
| `oai-field-recovery+text=concat+anchor=1+d=10` | paraphrase | 25 | 0.686 (25) | 0.648 | 1.000 | 0.498 | 0.400 | 0.600 | 0.720 | 0.800 |
| `oai-field-recovery+text=concat+anchor=1+d=10` | known_item | 25 | 0.718 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `oai-field-recovery+text=title10+anchor=0+d=10` | keyword | 25 | 0.739 (25) | 0.744 | 1.000 | 0.721 | 0.600 | 0.880 | 0.960 | 0.960 |
| `oai-field-recovery+text=title10+anchor=0+d=10` | question | 25 | 0.726 (25) | 0.740 | 1.000 | 0.604 | 0.520 | 0.680 | 0.760 | 0.800 |
| `oai-field-recovery+text=title10+anchor=0+d=10` | paraphrase | 25 | 0.697 (25) | 0.648 | 1.000 | 0.488 | 0.400 | 0.600 | 0.720 | 0.800 |
| `oai-field-recovery+text=title10+anchor=0+d=10` | known_item | 25 | 0.724 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `oai-field-recovery+text=title25+anchor=0+d=10` | keyword | 25 | 0.745 (25) | 0.744 | 1.000 | 0.746 | 0.640 | 0.840 | 0.960 | 0.960 |
| `oai-field-recovery+text=title25+anchor=0+d=10` | question | 25 | 0.732 (25) | 0.740 | 1.000 | 0.625 | 0.560 | 0.720 | 0.760 | 0.800 |
| `oai-field-recovery+text=title25+anchor=0+d=10` | paraphrase | 25 | 0.681 (25) | 0.648 | 1.000 | 0.467 | 0.400 | 0.560 | 0.720 | 0.800 |
| `oai-field-recovery+text=title25+anchor=0+d=10` | known_item | 25 | 0.724 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `oai-field-recovery+text=title25+anchor=0.5+d=10` | keyword | 25 | 0.741 (25) | 0.744 | 1.000 | 0.729 | 0.600 | 0.880 | 0.960 | 0.960 |
| `oai-field-recovery+text=title25+anchor=0.5+d=10` | question | 25 | 0.730 (25) | 0.740 | 1.000 | 0.565 | 0.440 | 0.720 | 0.760 | 0.800 |
| `oai-field-recovery+text=title25+anchor=0.5+d=10` | paraphrase | 25 | 0.687 (25) | 0.648 | 1.000 | 0.502 | 0.440 | 0.600 | 0.720 | 0.800 |
| `oai-field-recovery+text=title25+anchor=0.5+d=10` | known_item | 25 | 0.723 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `oai-field-recovery+text=title25+anchor=0.75+d=10` | keyword | 25 | 0.740 (25) | 0.744 | 1.000 | 0.730 | 0.600 | 0.880 | 0.960 | 0.960 |
| `oai-field-recovery+text=title25+anchor=0.75+d=10` | question | 25 | 0.727 (25) | 0.740 | 1.000 | 0.568 | 0.440 | 0.720 | 0.760 | 0.800 |
| `oai-field-recovery+text=title25+anchor=0.75+d=10` | paraphrase | 25 | 0.687 (25) | 0.648 | 1.000 | 0.536 | 0.480 | 0.600 | 0.720 | 0.800 |
| `oai-field-recovery+text=title25+anchor=0.75+d=10` | known_item | 25 | 0.722 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `score-max+w=0.35+d=100` | keyword | 25 | 0.722 (25) | 0.740 | 1.000 | 0.727 | 0.600 | 0.880 | 0.880 | 0.960 |
| `score-max+w=0.35+d=100` | question | 25 | 0.667 (25) | 0.688 | 1.000 | 0.510 | 0.400 | 0.640 | 0.720 | 0.720 |
| `score-max+w=0.35+d=100` | paraphrase | 25 | 0.586 (25) | 0.612 | 1.000 | 0.307 | 0.240 | 0.400 | 0.400 | 0.440 |
| `score-max+w=0.35+d=100` | known_item | 25 | 0.721 (25) | 0.640 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `score-max+w=0.35+d=500` | keyword | 25 | 0.712 (25) | 0.716 | 1.000 | 0.732 | 0.600 | 0.880 | 0.920 | 0.960 |
| `score-max+w=0.35+d=500` | question | 25 | 0.605 (25) | 0.628 | 1.000 | 0.502 | 0.400 | 0.640 | 0.720 | 0.720 |
| `score-max+w=0.35+d=500` | paraphrase | 25 | 0.510 (25) | 0.540 | 1.000 | 0.241 | 0.160 | 0.360 | 0.440 | 0.520 |
| `score-max+w=0.35+d=500` | known_item | 25 | 0.723 (25) | 0.656 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `score-max+w=0.55+d=100` | keyword | 25 | 0.739 (25) | 0.748 | 1.000 | 0.775 | 0.680 | 0.920 | 0.920 | 0.960 |
| `score-max+w=0.55+d=100` | question | 25 | 0.702 (25) | 0.716 | 1.000 | 0.532 | 0.400 | 0.680 | 0.720 | 0.800 |
| `score-max+w=0.55+d=100` | paraphrase | 25 | 0.633 (25) | 0.648 | 1.000 | 0.336 | 0.240 | 0.440 | 0.520 | 0.680 |
| `score-max+w=0.55+d=100` | known_item | 25 | 0.724 (25) | 0.632 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `score-max+w=0.55+d=500` | keyword | 25 | 0.737 (25) | 0.728 | 1.000 | 0.779 | 0.680 | 0.920 | 0.960 | 1.000 |
| `score-max+w=0.55+d=500` | question | 25 | 0.681 (25) | 0.704 | 1.000 | 0.532 | 0.400 | 0.680 | 0.720 | 0.720 |
| `score-max+w=0.55+d=500` | paraphrase | 25 | 0.604 (25) | 0.600 | 1.000 | 0.336 | 0.240 | 0.440 | 0.560 | 0.640 |
| `score-max+w=0.55+d=500` | known_item | 25 | 0.728 (25) | 0.648 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `score-max+w=0.75+d=100` | keyword | 25 | 0.731 (25) | 0.732 | 1.000 | 0.716 | 0.600 | 0.880 | 0.920 | 0.960 |
| `score-max+w=0.75+d=100` | question | 25 | 0.727 (25) | 0.728 | 1.000 | 0.583 | 0.480 | 0.720 | 0.720 | 0.800 |
| `score-max+w=0.75+d=100` | paraphrase | 25 | 0.660 (25) | 0.652 | 1.000 | 0.394 | 0.320 | 0.440 | 0.640 | 0.720 |
| `score-max+w=0.75+d=100` | known_item | 25 | 0.727 (25) | 0.632 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `score-max+w=0.75+d=500` | keyword | 25 | 0.732 (25) | 0.740 | 1.000 | 0.716 | 0.600 | 0.880 | 0.920 | 0.960 |
| `score-max+w=0.75+d=500` | question | 25 | 0.725 (25) | 0.732 | 1.000 | 0.583 | 0.480 | 0.720 | 0.720 | 0.760 |
| `score-max+w=0.75+d=500` | paraphrase | 25 | 0.695 (25) | 0.680 | 1.000 | 0.487 | 0.400 | 0.600 | 0.640 | 0.640 |
| `score-max+w=0.75+d=500` | known_item | 25 | 0.726 (25) | 0.636 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `score-minmax+w=0.35+d=100` | keyword | 25 | 0.701 (25) | 0.688 | 1.000 | 0.732 | 0.600 | 0.880 | 0.920 | 1.000 |
| `score-minmax+w=0.35+d=100` | question | 25 | 0.578 (25) | 0.560 | 1.000 | 0.516 | 0.400 | 0.640 | 0.720 | 0.760 |
| `score-minmax+w=0.35+d=100` | paraphrase | 25 | 0.482 (25) | 0.492 | 1.000 | 0.256 | 0.160 | 0.360 | 0.520 | 0.680 |
| `score-minmax+w=0.35+d=100` | known_item | 25 | 0.680 (25) | 0.568 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `score-minmax+w=0.35+d=500` | keyword | 25 | 0.717 (25) | 0.712 | 1.000 | 0.736 | 0.600 | 0.880 | 0.960 | 1.000 |
| `score-minmax+w=0.35+d=500` | question | 25 | 0.624 (25) | 0.628 | 1.000 | 0.519 | 0.400 | 0.680 | 0.720 | 0.720 |
| `score-minmax+w=0.35+d=500` | paraphrase | 25 | 0.532 (25) | 0.556 | 1.000 | 0.268 | 0.160 | 0.440 | 0.480 | 0.600 |
| `score-minmax+w=0.35+d=500` | known_item | 25 | 0.707 (25) | 0.608 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `score-minmax+w=0.55+d=100` | keyword | 25 | 0.709 (25) | 0.700 | 1.000 | 0.700 | 0.560 | 0.880 | 0.920 | 1.000 |
| `score-minmax+w=0.55+d=100` | question | 25 | 0.707 (25) | 0.712 | 1.000 | 0.586 | 0.440 | 0.760 | 0.800 | 0.800 |
| `score-minmax+w=0.55+d=100` | paraphrase | 25 | 0.643 (25) | 0.600 | 1.000 | 0.492 | 0.400 | 0.640 | 0.680 | 0.800 |
| `score-minmax+w=0.55+d=100` | known_item | 25 | 0.682 (25) | 0.576 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `score-minmax+w=0.55+d=500` | keyword | 25 | 0.727 (25) | 0.728 | 1.000 | 0.699 | 0.560 | 0.880 | 0.920 | 1.000 |
| `score-minmax+w=0.55+d=500` | question | 25 | 0.706 (25) | 0.724 | 1.000 | 0.560 | 0.440 | 0.680 | 0.760 | 0.800 |
| `score-minmax+w=0.55+d=500` | paraphrase | 25 | 0.669 (25) | 0.636 | 1.000 | 0.498 | 0.400 | 0.600 | 0.680 | 0.720 |
| `score-minmax+w=0.55+d=500` | known_item | 25 | 0.710 (25) | 0.608 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `score-minmax+w=0.75+d=100` | keyword | 25 | 0.678 (25) | 0.696 | 1.000 | 0.642 | 0.520 | 0.880 | 0.920 | 0.960 |
| `score-minmax+w=0.75+d=100` | question | 25 | 0.712 (25) | 0.716 | 1.000 | 0.596 | 0.480 | 0.760 | 0.800 | 0.840 |
| `score-minmax+w=0.75+d=100` | paraphrase | 25 | 0.678 (25) | 0.660 | 1.000 | 0.496 | 0.440 | 0.600 | 0.720 | 0.800 |
| `score-minmax+w=0.75+d=100` | known_item | 25 | 0.648 (25) | 0.532 | 1.000 | 0.950 | 0.920 | 1.000 | 1.000 | 1.000 |
| `score-minmax+w=0.75+d=500` | keyword | 25 | 0.697 (25) | 0.704 | 1.000 | 0.669 | 0.560 | 0.880 | 0.920 | 0.960 |
| `score-minmax+w=0.75+d=500` | question | 25 | 0.727 (25) | 0.736 | 1.000 | 0.602 | 0.480 | 0.760 | 0.800 | 0.840 |
| `score-minmax+w=0.75+d=500` | paraphrase | 25 | 0.695 (25) | 0.672 | 1.000 | 0.504 | 0.440 | 0.600 | 0.720 | 0.800 |
| `score-minmax+w=0.75+d=500` | known_item | 25 | 0.667 (25) | 0.560 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |

<details>
<summary>Readable techniques and original system IDs</summary>

| Original system ID | System | Keyword retrieval | Embedding | Ranker / fusion |
|---|---|---|---|---|
| `oai-field-recovery+text=title10+anchor=0+d=10` | OpenAI-large paraphrase recovery | Tuned BM25 including authors/title2x | OpenAI text-embedding-3-large | 25% lexical / 75% semantic; 10% title / 90% abstract; 0% combined-text anchor; candidate-max normalization; reorder baseline top10 only, preserve tail |
| `oai-field-recovery+text=abstract+anchor=0+d=10` | OpenAI-large paraphrase recovery | Tuned BM25 including authors/title2x | OpenAI text-embedding-3-large | 25% lexical / 75% semantic; abstract only; 0% combined-text anchor; candidate-max normalization; reorder baseline top10 only, preserve tail |
| `oai-field-hybrid+text=title25+d=10` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 25% / abstract 75%; max-score25% lexical / 75% field semantic; reorder baseline top10 only, preserve tail |
| `oai-field-recovery+text=title25+anchor=0+d=10` | OpenAI-large paraphrase recovery | Tuned BM25 including authors/title2x | OpenAI text-embedding-3-large | 25% lexical / 75% semantic; 25% title / 75% abstract; 0% combined-text anchor; candidate-max normalization; reorder baseline top10 only, preserve tail |
| `oai-field-recovery+text=title25+anchor=0.5+d=10` | OpenAI-large paraphrase recovery | Tuned BM25 including authors/title2x | OpenAI text-embedding-3-large | 25% lexical / 75% semantic; 25% title / 75% abstract; 50% combined-text anchor; candidate-max normalization; reorder baseline top10 only, preserve tail |
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
| `fusion-shortlist+a=0.5+d=500` | Fixed-shortlist score ordering | Tuned BM25 | OpenAI text-embedding-3-large | 50% max-score75% + 50% normalized RRF55%/c30/d100; score depth 500; reorder baseline top10 only, preserve tail |
| `fusion-rankscore+a=0.25+d=100` | Rank + score interpolation | Tuned BM25 | OpenAI text-embedding-3-large | 25% max-score75% + 75% normalized RRF55%/c30/d100; score depth 100 |
| `fusion-shortlist+a=0.5+d=100` | Fixed-shortlist score ordering | Tuned BM25 | OpenAI text-embedding-3-large | 50% max-score75% + 50% normalized RRF55%/c30/d100; score depth 100; reorder baseline top10 only, preserve tail |
| `fusion-rankscore+a=0.5+d=500` | Rank + score interpolation | Tuned BM25 | OpenAI text-embedding-3-large | 50% max-score75% + 50% normalized RRF55%/c30/d100; score depth 500 |
| `fusion-rankscore+a=0.5+d=100` | Rank + score interpolation | Tuned BM25 | OpenAI text-embedding-3-large | 50% max-score75% + 50% normalized RRF55%/c30/d100; score depth 100 |
| `fusion-rrf+w=0.55+d=100+c=30` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 55% semantic / 45% lexical; depth 100 |
| `fusion-rrf+w=0.65+d=100+c=60` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 65% semantic / 35% lexical; depth 100 |
| `fusion-rrf+w=0.55+d=200+c=30` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 55% semantic / 45% lexical; depth 200 |
| `field-order-gte-concat` | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | concatenated title + abstract control; pure semantic field score; reorder baseline top10 only, preserve tail |
| `field-lexical+t=0.25` | Lexical field-score ablation | Independent BM25 fields; 10% authors | OpenAI large candidate retrieval | separate title 25% / abstract 75%; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 |
| `fusion-rrf+w=0.75+d=100+c=100` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 75% semantic / 25% lexical; depth 100 |
| `fusion-rrf+w=0.7+d=100+c=60` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 70% semantic / 30% lexical; depth 100 |
| `fusion-rankscore+a=0.25+d=500` | Rank + score interpolation | Tuned BM25 | OpenAI text-embedding-3-large | 25% max-score75% + 75% normalized RRF55%/c30/d100; score depth 500 |
| `fusion-top1bonus+b=0.1+w=0.55+d=100+c=30` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30 + 10% top-1 bonus; 55% semantic / 45% lexical; depth 100 |
| `fusion-rrf+w=0.6+d=100+c=30` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 60% semantic / 40% lexical; depth 100 |
| `fusion-rrf+w=0.55+d=100+c=60` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 55% semantic / 45% lexical; depth 100 |
| `field-order-gte-separate+t=0.25` | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | separate title 25% / abstract 75%; pure semantic field score; reorder baseline top10 only, preserve tail |
| `fusion-rrf+w=0.55+d=500+c=30` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 55% semantic / 45% lexical; depth 500 |
| `fusion-rrf+w=0.65+d=100+c=30` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 65% semantic / 35% lexical; depth 100 |
| `score-minmax+w=0.55+d=500` | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Min-max-normalized scores; 55% semantic / 45% lexical; depth 500 |
| `fusion-linear+w=0.75+d=100` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 75% semantic / 25% lexical; depth 100 |
| `oai-field-hybrid+text=title75+d=10` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 75% / abstract 25%; max-score25% lexical / 75% field semantic; reorder baseline top10 only, preserve tail |
| `fusion-top1bonus+b=0.25+w=0.55+d=100+c=30` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30 + 25% top-1 bonus; 55% semantic / 45% lexical; depth 100 |
| `cross-minilm-l6+pool=baseline+d=10` | Local cross-encoder reranking | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large candidate retrieval | MiniLM-L6 cross-encoder raw logits; reorder current baseline top10 only, preserve tail |
| `fusion-rrf+w=0.75+d=100+c=60` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 75% semantic / 25% lexical; depth 100 |
| `oai-field+text=title25+d=10` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 25% / abstract 75%; pure cosine; reorder baseline top10 only, preserve tail |
| `score-max+w=0.55+d=100` | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Max-normalized scores; 55% semantic / 45% lexical; depth 100 |
| `fusion-rrf+w=0.7+d=100+c=30` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 70% semantic / 30% lexical; depth 100 |
| `fusion-rrf+w=0.75+d=50+c=100` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 75% semantic / 25% lexical; depth 50 |
| `score-minmax+w=0.75+d=500` | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Min-max-normalized scores; 75% semantic / 25% lexical; depth 500 |
| `fusion-rrf+w=0.5+d=100+c=60` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 50% semantic / 50% lexical; depth 100 |
| `field-order-gte-separate+t=0.5` | Local semantic field-score ablation | Tuned BM25 candidate retrieval | GTE-small field scoring; OpenAI large candidate retrieval | separate title 50% / abstract 50%; pure semantic field score; reorder baseline top10 only, preserve tail |
| `fusion-rrf+w=0.75+d=50+c=60` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 75% semantic / 25% lexical; depth 50 |
| `fusion-rrf+w=0.75+d=100+c=30` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 75% semantic / 25% lexical; depth 100 |
| `fusion-rrf+w=0.5+d=100+c=100` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 50% semantic / 50% lexical; depth 100 |
| `fusion-rrf+w=0.5+d=100+c=30` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=30; 50% semantic / 50% lexical; depth 100 |
| `oai-field+text=concat+d=10` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | concatenated title + abstract control; pure cosine; reorder baseline top10 only, preserve tail |
| `oai-field+text=title50+d=10` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 50% / abstract 50%; pure cosine; reorder baseline top10 only, preserve tail |
| `fusion-linear+w=0.5+d=100` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 50% semantic / 50% lexical; depth 100 |
| `score-max+w=0.55+d=500` | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Max-normalized scores; 55% semantic / 45% lexical; depth 500 |
| `fusion-rrf+w=0.6+d=100+c=10` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 60% semantic / 40% lexical; depth 100 |
| `fusion-linear+w=0.75+d=50` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | Linear rank fusion; 75% semantic / 25% lexical; depth 50 |
| `score-minmax+w=0.55+d=100` | Hybrid score fusion | Tuned BM25 | OpenAI text-embedding-3-large | Min-max-normalized scores; 55% semantic / 45% lexical; depth 100 |
| `fusion-rrf+w=0.65+d=100+c=10` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 65% semantic / 35% lexical; depth 100 |
| `oai-field+text=title75+d=10` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 75% / abstract 25%; pure cosine; reorder baseline top10 only, preserve tail |
| `fusion-rrf+w=0.7+d=100+c=10` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 70% semantic / 30% lexical; depth 100 |
| `fusion-rrf+w=0.55+d=100+c=10` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 55% semantic / 45% lexical; depth 100 |
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
| `dense-openai-large` | Embedding search | None | OpenAI text-embedding-3-large | Cosine similarity |
| `fusion-rrf+w=1+d=100+c=10` | Semantic-only fusion control | None (0% weight) | OpenAI text-embedding-3-large | RRF c=10; depth 100 |
| `oai-field+text=concat+d=100` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | concatenated title + abstract control; pure cosine; reorder baseline top100 only, preserve tail |
| `fusion-rrf+w=0.5+d=20+c=10` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=10; 50% semantic / 50% lexical; depth 20 |
| `fusion-rrf+w=0.5+d=20+c=60` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=60; 50% semantic / 50% lexical; depth 20 |
| `fusion-rrf+w=0.5+d=20+c=100` | Hybrid rank fusion | Tuned BM25 | OpenAI text-embedding-3-large | RRF c=100; 50% semantic / 50% lexical; depth 20 |
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
| `field-lexical+t=0.5` | Lexical field-score ablation | Independent BM25 fields; 10% authors | OpenAI large candidate retrieval | separate title 50% / abstract 50%; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 |
| `oai-field-hybrid+text=title50+d=100` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 50% / abstract 50%; max-score25% lexical / 75% field semantic; reorder baseline top100 only, preserve tail |
| `field-lexical+t=0.75` | Lexical field-score ablation | Independent BM25 fields; 10% authors | OpenAI large candidate retrieval | separate title 75% / abstract 25%; 75% baseline 31/(30+rank) + 25% field signal; reorder frozen baseline100 |
| `cross-minilm-l6+pool=union100+w=0.5` | Local cross-encoder reranking | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large candidate retrieval | 50% cross-encoder rank + 50% baseline rank, RRF c30; union of lexical100, semantic100 and baseline100 |
| `oai-field-hybrid+text=title75+d=100` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 75% / abstract 25%; max-score25% lexical / 75% field semantic; reorder baseline top100 only, preserve tail |
| `hybrid-gte-small+rrf+w=0.75+c=60` | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=60; 75% semantic / 25% lexical; depth 100 |
| `hybrid-gte-small+rrf+w=0.75+c=100` | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=100; 75% semantic / 25% lexical; depth 100 |
| `hybrid-gte-small+linear+w=0.75` | Hybrid rank fusion | Tuned BM25 | GTE-small | Linear rank fusion; 75% semantic / 25% lexical; depth 100 |
| `cross-minilm-l6+pool=baseline+d=30` | Local cross-encoder reranking | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large candidate retrieval | MiniLM-L6 cross-encoder raw logits; reorder current baseline top30 only, preserve tail |
| `hybrid-gte-small+rrf+w=0.5+c=60` | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=60; 50% semantic / 50% lexical; depth 100 |
| `hybrid-gte-small+linear+w=0.5` | Hybrid rank fusion | Tuned BM25 | GTE-small | Linear rank fusion; 50% semantic / 50% lexical; depth 100 |
| `hybrid-bge-small+rrf+w=0.5+c=60` | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=60; 50% semantic / 50% lexical; depth 100 |
| `hybrid-bge-small+linear+w=0.75` | Hybrid rank fusion | Tuned BM25 | BGE-small | Linear rank fusion; 75% semantic / 25% lexical; depth 100 |
| `hybrid-gte-small+rrf+w=0.5+c=100` | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=100; 50% semantic / 50% lexical; depth 100 |
| `hybrid-bge-small+rrf+w=0.75+c=60` | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=60; 75% semantic / 25% lexical; depth 100 |
| `oai-field+text=title25+d=100` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 25% / abstract 75%; pure cosine; reorder baseline top100 only, preserve tail |
| `hybrid-bge-small+linear+w=0.5` | Hybrid rank fusion | Tuned BM25 | BGE-small | Linear rank fusion; 50% semantic / 50% lexical; depth 100 |
| `hybrid-bge-small+rrf+w=0.5+c=100` | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=100; 50% semantic / 50% lexical; depth 100 |
| `hybrid-bge-small+rrf+w=0.75+c=100` | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=100; 75% semantic / 25% lexical; depth 100 |
| `hybrid-gte-small+rrf+w=0.75+c=10` | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=10; 75% semantic / 25% lexical; depth 100 |
| `hybrid-bge-small+rrf+w=0.25+c=100` | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=100; 25% semantic / 75% lexical; depth 100 |
| `hybrid-gte-small+rrf+w=0.25+c=100` | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=100; 25% semantic / 75% lexical; depth 100 |
| `hybrid-bge-small+rrf+w=0.75+c=10` | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=10; 75% semantic / 25% lexical; depth 100 |
| `hybrid-bge-small+linear+w=0.25` | Hybrid rank fusion | Tuned BM25 | BGE-small | Linear rank fusion; 25% semantic / 75% lexical; depth 100 |
| `hybrid-gte-small+rrf+w=0.25+c=60` | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=60; 25% semantic / 75% lexical; depth 100 |
| `hybrid-gte-small+linear+w=0.25` | Hybrid rank fusion | Tuned BM25 | GTE-small | Linear rank fusion; 25% semantic / 75% lexical; depth 100 |
| `hybrid-bge-small+rrf+w=0.25+c=60` | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=60; 25% semantic / 75% lexical; depth 100 |
| `oai-field+text=title50+d=100` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 50% / abstract 50%; pure cosine; reorder baseline top100 only, preserve tail |
| `cross-minilm-l6+pool=baseline+d=100` | Local cross-encoder reranking | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large candidate retrieval | MiniLM-L6 cross-encoder raw logits; reorder current baseline top100 only, preserve tail |
| `hybrid-gte-small+rrf+w=0.25+c=10` | Hybrid rank fusion | Tuned BM25 | GTE-small | RRF c=10; 25% semantic / 75% lexical; depth 100 |
| `hybrid-bge-small+rrf+w=0.25+c=10` | Hybrid rank fusion | Tuned BM25 | BGE-small | RRF c=10; 25% semantic / 75% lexical; depth 100 |
| `cross-minilm-l6+pool=union100+w=1` | Local cross-encoder reranking | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large candidate retrieval | MiniLM-L6 cross-encoder raw logits; union of lexical100, semantic100 and baseline100 |
| `oai-field+text=title75+d=100` | OpenAI-large semantic field ablation | Tuned BM25 candidate retrieval | OpenAI text-embedding-3-large; same-model query/concat control | separate title 75% / abstract 25%; pure cosine; reorder baseline top100 only, preserve tail |
| `bm25+stop+exact+stems+authors+title2x` | Keyword search | BM25: exact + stems; remove stopwords; authors; title x2; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stop+exact+stems+title2x` | Keyword search | BM25: exact + stems; remove stopwords; title x2; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+exact+stems+title2x` | Keyword search | BM25: exact + stems; title x2; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+exact+stems+authors` | Keyword search | BM25: exact + stems; authors; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stop+exact+stems+authors` | Keyword search | BM25: exact + stems; remove stopwords; authors; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+exact+stems+authors+title2x` | Keyword search | BM25: exact + stems; authors; title x2; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+exact+stems` | Keyword search | BM25: exact + stems; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stop+exact+stems` | Keyword search | BM25: exact + stems; remove stopwords; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stop+authors+title2x` | Keyword search | BM25: exact terms; remove stopwords; authors; title x2; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+authors` | Keyword search | BM25: exact terms; authors; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stop+authors` | Keyword search | BM25: exact terms; remove stopwords; authors; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stop+title2x` | Keyword search | BM25: exact terms; remove stopwords; title x2; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+authors+title2x` | Keyword search | BM25: exact terms; authors; title x2; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+title2x` | Keyword search | BM25: exact terms; title x2; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stop+stem+authors+title2x` | Keyword search | BM25: stems only; remove stopwords; authors; title x2; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stop` | Keyword search | BM25: exact terms; remove stopwords; k1=1.2, b=0.75 | None | BM25 score |
| `bm25-baseline` | Keyword search | BM25: exact terms; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stem+authors+title2x` | Keyword search | BM25: stems only; authors; title x2; k1=1.2, b=0.75 | None | BM25 score |
| `bm25+stop+stem+authors` | Keyword search | BM25: stems only; remove stopwords; authors; k1=1.2, b=0.75 | None | BM25 score |
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
- [llm-score-pilot/report.json](../llm-score-pilot/report.json) — historical report/configuration; original scope
- [llm-score-pilot/report.md](../llm-score-pilot/report.md) — historical report/configuration; original scope
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
