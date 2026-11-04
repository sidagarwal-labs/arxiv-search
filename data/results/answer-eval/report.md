# Answer-model comparison (full stage)

Same prompt (answer-v1), same Decision46 top10 evidence, reasoning effort none. Label metrics use existing relevance labels; faithfulness and answers-request are graded blind by GPT-6.1 Terra (not a candidate).

Abstain columns use the v2 rule (no citations, or a graded clear not-a-direct-answer caveat); v1 strict values are in report.json.

| Model | Format valid | False abstain | Abstain acc. | Citation precision | Grade-2 coverage | Source cited | Faithfulness | Fully faithful | Answers request (0-2) | Words | $/answer | s/answer |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nano (`gpt-5.4-nano-2026-03-17`) | 0.592 | 0.090 | 0.714 | 0.911 | 0.729 | 0.967 | 0.563 | 0.134 | 1.93 | 135 | $0.00096 | 2.8 |
| luna (`gpt-6-luna`) | 0.896 | 0.034 | 0.917 | 0.988 | 0.711 | 1.000 | 0.695 | 0.386 | 1.95 | 71 | $0.00041 | 3.8 |
| mini (`gpt-5.4-mini-2026-03-17`) | 0.960 | 0.082 | 0.857 | 0.947 | 0.810 | 1.000 | 0.821 | 0.364 | 1.92 | 101 | $0.00324 | 2.6 |
| gpt-5.4 (`gpt-5.4-2026-03-05`) | 0.896 | 0.032 | 0.889 | 0.926 | 0.847 | 1.000 | 0.836 | 0.319 | 1.95 | 142 | $0.01158 | 12.1 |

## Price and latency trade-off

Measured on every attempt (including invalid answers). Latency is wall-clock for one request at a time from the dev machine, network included: compare models, not SLAs. Projections multiply measured $/answer by volume (one summary per search, standard uncached prices).

| Model | $/answer | $ per 1k searches | $ per 100k searches | Output tokens | Latency mean / p50 / p95 (s) | Faithfulness |
|---|---|---|---|---|---|---|
| nano | $0.00096 | $0.96 | $96 | 212 | 2.8 / 2.8 / 3.7 | 0.563 |
| luna | $0.00041 | $0.41 | $41 | 130 | 3.8 / 3.5 / 6.5 | 0.695 |
| mini | $0.00324 | $3.24 | $324 | 142 | 2.6 / 2.6 / 3.3 | 0.821 |
| gpt-5.4 | $0.01158 | $11.58 | $1,158 | 194 | 12.1 / 5.2 / 7.4 | 0.836 |

Best faithfulness: `gpt-5.4`. Pick (cheapest qualifying serving-eligible): `mini`.

| Model | Faithfulness Δ vs best [95% CI] | Citation precision Δ vs best [95% CI] | Qualifies |
|---|---|---|---|
| nano | -0.282 [-0.367, -0.199] (n=66) | -0.033 [-0.089, +0.018] (n=66) | no (faithfulness, citation_precision, abstain_accuracy, format_valid) |
| luna | -0.142 [-0.218, -0.068] (n=84) | +0.062 [+0.035, +0.093] (n=84) | no (faithfulness, format_valid) |
| mini | -0.007 [-0.046, +0.031] (n=93) | +0.023 [-0.009, +0.055] (n=93) | yes |
| gpt-5.4 | — | — | no (format_valid) |

Grades come from the GPT-6.1 Terra blinded workbook the owner graded in a chat session (same rubric and evidence as the API grader, many answers per session instead of one per request); a GPT-6 ASTRA sample measures grader agreement.

Cautions: dev queries only; one prompt; the graders are models, not people; abstain items are constructed (mismatched results), not natural; cost uses standard uncached prices. Nano is deprecated and GPT-5.4 is a ceiling, so neither can be picked.
