# Remaining80 dev confirmation: GPT-5.4 two-pass scores-only

D47 nDCG@10: 0.7912. Confirmed: **True** (ndcg=True, source_mrr=True, complete=True, fully_judged=True).

| Variant | nDCG@10 | Delta vs D47 [95% CI] | W/L/T | Source MRR delta |
|---|---:|---:|---:|---:|
| candidate | 0.8449 | +0.0537 [+0.0371, +0.0713] | 59/20/1 | +0.0350 |
| one_pass | 0.8410 | +0.0498 [+0.0344, +0.0664] | 60/19/1 | +0.0310 |
| equal_rrf | 0.8194 | +0.0281 [+0.0156, +0.0406] | 58/22/0 | +0.0055 |

Refinement cost/query: two-pass $0.0380, one-pass $0.0190. Total $3.0395.

API seconds: two-pass max-of-two mean 3.24 (p95 3.76); one-pass mean 3.14.

Latency is max of two sequential provider calls, not measured serving latency. Labels are pooled AI judgments. One-pass and equal-RRF are diagnostics from the same replies, not gated candidates.

Per-query rows: [report.json](report.json).
