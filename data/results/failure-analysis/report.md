# Frozen baseline failure analysis

Judge `openai-mini`, rubric `b8b0c14a`. 100 dev queries; no API calls or label changes.
Cases are diagnostic leads, not proven causes. Read full abstracts and label provenance in cases.json. A judge reason is not ground truth.

## Dense versus hybrid by segment

Paired nDCG difference = hybrid minus dense; exploratory, no multiple-testing correction. Overlap is query/source word overlap, not a live routing feature.

| Group | Segment | nDCG queries / total | Dense | Hybrid | Difference [95% CI] |
|---|---|---|---|---|---|
| query_type | keyword | 25/25 | 0.668 | 0.723 | +0.054 [-0.004, +0.114] |
| query_type | known_item | 25/25 | 0.620 | 0.718 | +0.098 [+0.052, +0.146] |
| query_type | paraphrase | 25/25 | 0.670 | 0.616 | -0.054 [-0.123, +0.010] |
| query_type | question | 25/25 | 0.713 | 0.686 | -0.027 [-0.068, +0.013] |
| specificity | broad | 26/26 | 0.684 | 0.725 | +0.042 [-0.012, +0.104] |
| specificity | specific | 74/74 | 0.662 | 0.672 | +0.009 [-0.026, +0.047] |
| category | cs.CL | 34/34 | 0.639 | 0.703 | +0.064 [+0.019, +0.109] |
| category | cs.IR | 33/33 | 0.676 | 0.679 | +0.003 [-0.051, +0.057] |
| category | cs.LG | 33/33 | 0.689 | 0.674 | -0.015 [-0.071, +0.040] |
| overlap_band | high (>=0.5) | 70/70 | 0.656 | 0.710 | +0.054 [+0.020, +0.088] |
| overlap_band | low (<0.5) | 30/30 | 0.696 | 0.629 | -0.067 [-0.120, -0.013] |

## largest hybrid regressions

| Query ID | Query | Dense nDCG | Hybrid nDCG | Difference |
|---|---|---|---|---|
| q-paraphrase-030 | a way to suggest places to visit based on the idea that some spots require prior knowledge from other spots | 0.819 | 0.426 | -0.393 |
| q-paraphrase-032 | maximizing income for power conversion tools and cells by using actual device behavior in Nordic power exchanges | 0.698 | 0.313 | -0.385 |
| q-question-027 | How can we determine the compute requirements for large scale suggesting systems? | 0.792 | 0.484 | -0.308 |
| q-paraphrase-062 | guessing the number of tokens an AI will generate for a prompt that can have wildly different response sizes | 0.526 | 0.218 | -0.308 |
| q-paraphrase-093 | finding a way to group chip design manual snippets into logical blocks to help a bot answer technical questions better | 0.931 | 0.629 | -0.302 |

## largest hybrid gains

| Query ID | Query | Dense nDCG | Hybrid nDCG | Difference |
|---|---|---|---|---|
| q-keyword-085 | AI consciousness and self-awareness | 0.518 | 0.967 | +0.449 |
| q-paraphrase-020 | reducing data exchange by avoiding error signal propagation in shared neural architectures | 0.283 | 0.698 | +0.415 |
| q-known_item-054 | Tannenbaum conversation context effect | 0.314 | 0.685 | +0.371 |
| q-keyword-017 | linear time long context recall | 0.584 | 0.881 | +0.298 |
| q-known_item-032 | Bekkers equivariant neural fields | 0.509 | 0.785 | +0.276 |

## lowest hybrid ndcg

| Query ID | Query | Dense nDCG | Hybrid nDCG | Difference |
|---|---|---|---|---|
| q-paraphrase-062 | guessing the number of tokens an AI will generate for a prompt that can have wildly different response sizes | 0.526 | 0.218 | -0.308 |
| q-paraphrase-032 | maximizing income for power conversion tools and cells by using actual device behavior in Nordic power exchanges | 0.698 | 0.313 | -0.385 |
| q-keyword-072 | BL19 digital collection retrieval benchmark | 0.106 | 0.352 | +0.246 |
| q-paraphrase-096 | a way to find relevant text chunks using a hierarchy of summaries to connect search terms and documents | 0.419 | 0.392 | -0.027 |
| q-paraphrase-030 | a way to suggest places to visit based on the idea that some spots require prior knowledge from other spots | 0.819 | 0.426 | -0.393 |
