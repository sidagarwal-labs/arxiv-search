Reduced-corpus screening only: easier than the 23,304-paper benchmark; **do not compare its scores directly with the main table**.
All models use the identical saved subset and 100 dev queries. MRR/recall credit only the source paper; graded nDCG is not yet available. All inputs use title + abstract; local models retain their 512-token truncation while OpenAI receives the full input (up to 8,191 tokens).

| Model | Papers | Dimensions | MRR@10 [95% CI] | R@10 | R@20 | Vector MB |
|---|---|---|---|---|---|---|
| bge-small | 2000 | 384 | 0.740 [0.675, 0.808] | 0.920 | 0.980 | 3.1 |
| gte-small | 2000 | 384 | 0.755 [0.687, 0.821] | 0.940 | 0.990 | 3.1 |
| text-embedding-3-large | 2000 | 3072 | 0.844 [0.784, 0.902] | 0.950 | 0.980 | 24.6 |
| text-embedding-3-small | 2000 | 1536 | 0.792 [0.725, 0.859] | 0.930 | 0.980 | 12.3 |

| Model vs. GTE-small | Paired MRR difference [95% CI] |
|---|---|
| bge-small | -0.016 [-0.063, +0.033] |
| text-embedding-3-large | +0.088 [+0.027, +0.148] |
| text-embedding-3-small | +0.036 [-0.029, +0.104] |

Large minus small: **+0.052 [-0.006, +0.110]** (paired 95% interval). These are dev screening comparisons, not held-out wins.

| Paid model | Requests | Accounted tokens | Accounted USD | API seconds |
|---|---|---|---|---|
| text-embedding-3-large | 34 | 538,881 | $0.0701 | 68.1 |
| text-embedding-3-small | 34 | 538,881 | $0.0108 | 62.4 |

Accounted cost includes conservative reservations for failed/unknown requests and is not a provider invoice. $0.25 lifetime cap; no automatic retries.
