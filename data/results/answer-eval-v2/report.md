# Experiment L: citation-discipline prompt (answer-v2) for the AI summary

Same 125 answer-dev-v1 items and Decision46 top10 as Decision 48. Yardstick: gpt-5.4 answer-v1, graded by GPT-6.1 Terra in session 1; answer-v2 graded by Terra in session 2.

| Model (prompt) | Format valid | False abstain | Abstain acc. | Citation precision | Faithfulness | Fully faithful | Answers request | Words | $ per 1k | p50 s |
|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5.4 (answer-v1) | 0.896 | 0.032 | 0.889 | 0.926 | 0.836 | 0.319 | 1.95 | 142 | $11.58 | 5.2 |
| mini (answer-v1) | 0.960 | 0.082 | 0.857 | 0.947 | 0.821 | 0.364 | 1.92 | 101 | $3.24 | 2.6 |
| luna (answer-v1) | 0.896 | 0.034 | 0.917 | 0.988 | 0.695 | 0.386 | 1.95 | 71 | $0.41 | 3.5 |
| **luna (answer-v2)** | 0.936 | 0.030 | 0.941 | 0.993 | 0.935 | 0.770 | 1.90 | 65 | $0.41 | 2.4 |
| **mini (answer-v2)** | 0.944 | 0.051 | 0.889 | 0.945 | 0.895 | 0.610 | 1.90 | 82 | $3.23 | 2.3 |

| answer-v2 model | Faithfulness Δ vs gpt-5.4 v1 [95% CI] | Citation precision Δ [95% CI] | Qualifies |
|---|---|---|---|
| luna | +0.105 [+0.070, +0.141] (n=94) | +0.067 [+0.040, +0.095] (n=94) | no (format_valid) |
| mini | +0.054 [+0.011, +0.097] (n=94) | +0.016 [-0.020, +0.049] (n=94) | no (format_valid) |

Grader drift (same answer-v1 answers, Terra session 2 minus session 1): 40 answers, sentence agreement 0.947, kappa 0.880, faithfulness shift -0.028 (limit ±0.05).

**Decision:** serve mini (answer-v1): challenger does not qualify.

Cautions: Prompt written after reading answer-v1 failures on these dev items; the rules are general (cite every sentence) but a pass is optimistic until confirmed on held-out queries. Graders are models, not people.
