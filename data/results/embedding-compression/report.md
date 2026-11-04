# Embedding compression check (hosting)

Stage 1 (Decision36) rebuilt from cached OpenAI vectors stored in smaller forms. Only the stored paper vectors change; BM25 scores and every setting are frozen. Dev queries only, existing labels, zero API calls. Differences are against the float32 control rebuilt the same way.

Control sanity: top10 identical to the frozen Decision36 run on 100/100 queries; top50 overlap 1.0000 (the cached scores differ only by float rounding).

| Variant | MB | nDCG@10 | Δ vs control | Queries changed | Grade-2 R@50 Δ | Top10 overlap | Top50 overlap | Identical top50 sets | Judged@10 | Equivalent |
|---|---|---|---|---|---|---|---|---|---|---|
| `f32-3072` | 286 | 0.7036 | +0.0000 | 0 | +0.0000 | 1.000 | 1.000 | 100/100 | 1.000 | **yes** |
| `f16-3072` | 143 | 0.7031 | -0.0005 | 3 | +0.0000 | 0.996 | 1.000 | 98/100 | 1.000 | **yes** |
| `int8-3072` | 72 | 0.7060 | +0.0024 | 10 | +0.0000 | 0.993 | 0.997 | 83/100 | 1.000 | **yes** |
| `f32-1536` | 143 | 0.6959 | -0.0076 | 84 | -0.0102 | 0.911 | 0.921 | 1/100 | 0.995 | no (reranker_input, top10, quality) |
| `f16-1536` | 72 | 0.6959 | -0.0076 | 84 | -0.0102 | 0.911 | 0.921 | 1/100 | 0.995 | no (reranker_input, top10, quality) |
| `int8-1536` | 36 | 0.6970 | -0.0065 | 85 | -0.0102 | 0.905 | 0.921 | 1/100 | 0.994 | no (reranker_input, top10, quality) |
| `f16-1024` | 48 | 0.6912 | -0.0124 | 94 | -0.0213 | 0.848 | 0.881 | 0/100 | 0.981 | no (reranker_input, top10, quality) |
| `f16-768` | 36 | 0.6853 | -0.0182 | 95 | -0.0258 | 0.806 | 0.839 | 0/100 | 0.969 | no (reranker_input, top10, quality, coverage) |
| `int8-768` | 18 | 0.6856 | -0.0180 | 95 | -0.0255 | 0.807 | 0.839 | 0/100 | 0.969 | no (reranker_input, top10, quality, coverage) |
| `f16-512` | 24 | 0.6681 | -0.0355 | 97 | -0.0434 | 0.747 | 0.792 | 0/100 | 0.931 | no (reranker_input, top10, quality, coverage) |
| `f16-256` | 12 | 0.6235 | -0.0801 | 98 | -0.1114 | 0.636 | 0.688 | 0/100 | 0.844 | no (reranker_input, top10, quality, coverage) |

Recommended (smallest equivalent): `int8-3072`.

Rule (frozen before scoring): reranker_input: mean top50 overlap with the control >= 0.98 (the Decision46 reranker sees exactly the Stage 1 top50); top10: mean top10 overlap with the control >= 0.95; quality: nDCG@10 mean difference vs control >= -0.005 and grade2_recall@50 difference >= -0.01; coverage: top10 judged share >= 0.98 (otherwise label gaps hide the effect).

Cautions: dev queries only; unjudged top10 papers count as not relevant, so a variant that surfaces new papers can look slightly worse than it is. This decides storage for hosting only; it does not change any baseline.
