# Cached GPT-5.4 refinement ablations

Nine declared cached variants, eight alternatives to the stronger reference. Post-hoc exploratory selection; paired intervals are unadjusted and not independent confirmation. Pass2 is diagnostic, not permission to choose the better pass per query.

D47 pilot20 nDCG@10: 0.7783.

| Variant | nDCG | Delta vs stronger reference [95% CI] | Source MRR delta vs D47 | $ refinement/query | API seconds* |
|---|---:|---:|---:|---:|---:|
| equal_rrf/average | 0.8111 | +0.0000 [+0.0000, +0.0000] | +0.0021 | $0.0382 | 3.13 |
| equal_rrf/pass1 | 0.7988 | -0.0122 [-0.0261, -0.0019] | +0.0038 | $0.0191 | 3.01 |
| equal_rrf/pass2 | 0.8035 | -0.0075 [-0.0188, +0.0009] | +0.0021 | $0.0191 | 2.97 |
| model_heavy_rrf/average | 0.8230 | +0.0119 [-0.0050, +0.0301] | +0.0009 | $0.0382 | 3.13 |
| model_heavy_rrf/pass1 | 0.8072 | -0.0039 [-0.0226, +0.0109] | +0.0009 | $0.0191 | 3.01 |
| model_heavy_rrf/pass2 | 0.8222 | +0.0111 [-0.0092, +0.0304] | +0.0009 | $0.0191 | 2.97 |
| scores_only/average | 0.8291 | +0.0180 [-0.0062, +0.0437] | -0.0007 | $0.0382 | 3.13 |
| scores_only/pass1 | 0.8195 | +0.0085 [-0.0155, +0.0296] | -0.0007 | $0.0191 | 3.01 |
| scores_only/pass2 | 0.8331 | +0.0221 [-0.0007, +0.0500] | -0.0007 | $0.0191 | 2.97 |

* Saved uncached refinement cost only; excludes common D46 upstream cost. Two-pass latency is max of sequential call durations, a hypothetical parallel estimate, not measured serving latency.

All variants retain the rank-one pin; no new model requests, remaining80 scoring, test evaluation or promotion. Intervals do not account for variant selection.

Source fingerprints, per-query and query-type results: [report.json](report.json).
