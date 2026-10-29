# Score-fusion challenger: loss and recall review

Baseline `fusion-rrf+w=0.55+d=100+c=30`; challenger `score-max+w=0.75+d=500`. Same immutable 3,294-pair dev label snapshot; no API calls or promotion.
Exploratory paired bootstrap intervals are conditional on labels, not selection/multiple-testing adjusted. Source recall measures the original target, not every possible useful answer. A null evidence grade is unjudged, not grade0.

## Overall candidate minus baseline

| Metric | Baseline | Challenger | Delta [95% CI] | Wins / losses / ties |
|---|---|---|---|---|
| ndcg@10 | 0.7064 | 0.7197 | +0.0133 [+0.0015, +0.0251] | 56 / 38 / 6 |
| precision@10 | 0.6890 | 0.6970 | +0.0080 [-0.0060, +0.0230] | 25 / 16 / 59 |
| source_mrr@10 | 0.6459 | 0.6916 | +0.0457 [+0.0093, +0.0909] | 12 / 8 / 80 |
| source_recall@1 | 0.5500 | 0.6100 | +0.0600 [+0.0100, +0.1200] | 7 / 1 / 92 |
| source_recall@5 | 0.7600 | 0.8000 | +0.0400 [-0.0100, +0.1000] | 6 / 2 / 92 |
| source_recall@10 | 0.8600 | 0.8200 | -0.0400 [-0.0800, -0.0100] | 0 / 4 / 96 |
| source_recall@20 | 0.8900 | 0.8400 | -0.0500 [-0.0900, -0.0100] | 0 / 5 / 95 |

## largest ndcg losses

| Query | Source rank: baseline / challenger | nDCG: baseline / challenger | Delta |
|---|---|---|---|
| q-known_item-061: Ko decoupling content delivery medical qa | 1 / 1 | 0.8444 / 0.6659 | -0.1785 |
| q-keyword-090: video watch time mixture model | 1 / 1 | 0.8120 / 0.6715 | -0.1405 |
| q-question-053: How can we inspect the internal activations of large language models during inference without slowing them down? | 15 / 13 | 0.8375 / 0.7393 | -0.0981 |
| q-question-019: how does repeating training data affect model performance during pretraining? | 2 / 2 | 0.6604 / 0.5667 | -0.0937 |
| q-keyword-049: multimodal llm decoding strategies | 27 / 23 | 0.7279 / 0.6486 | -0.0793 |
| q-keyword-061: robust intent classification for chatbots | 3 / 3 | 0.8286 / 0.7493 | -0.0792 |
| q-question-039: how to make a retrieval system that cares about the date of the information? | 31 / 77 | 0.7421 / 0.6722 | -0.0699 |
| q-question-027: How can we determine the compute requirements for large scale suggesting systems? | 5 / 55 | 0.5752 / 0.5085 | -0.0667 |
| q-known_item-039: Fernandes brazilian legal document segmentation | 1 / 1 | 0.6412 / 0.5766 | -0.0645 |
| q-keyword-054: Bifocal diffusion R2LM throughput | 1 / 1 | 0.8306 / 0.7772 | -0.0534 |

## largest ndcg gains

| Query | Source rank: baseline / challenger | nDCG: baseline / challenger | Delta |
|---|---|---|---|
| q-question-077: can standard graph neural networks perform link prediction on unknown knowledge graphs? | 6 / 1 | 0.4610 / 0.6986 | +0.2375 |
| q-paraphrase-032: maximizing income for power conversion tools and cells by using actual device behavior in Nordic power exchanges | 9 / 1 | 0.3443 / 0.5596 | +0.2153 |
| q-keyword-022: lifecycle memory strength control | 1 / 1 | 0.6039 / 0.7532 | +0.1493 |
| q-paraphrase-008: managing delivery drivers who work for several different apps using reinforcement learning without seeing all their data | 9 / 2 | 0.6974 / 0.8244 | +0.1270 |
| q-keyword-074: distributional RL chaotic dynamics | 1 / 1 | 0.5684 / 0.6899 | +0.1216 |

## lost source top10

| Query | Source rank: baseline / challenger | nDCG: baseline / challenger | Delta |
|---|---|---|---|
| q-keyword-053: graph machine learning chemical reaction | 9 / 12 | 0.7078 / 0.6547 | -0.0531 |
| q-paraphrase-006: fixing systemic prejudices in generative suggestion engines by erasing the impact of problematic data points without full model updates | 5 / 34 | 0.6556 / 0.7150 | +0.0594 |
| q-paraphrase-062: guessing the number of tokens an AI will generate for a prompt that can have wildly different response sizes | 10 / 92 | 0.3206 / 0.3669 | +0.0462 |
| q-question-027: How can we determine the compute requirements for large scale suggesting systems? | 5 / 55 | 0.5752 / 0.5085 | -0.0667 |

## gained source top10

| Query | Source rank: baseline / challenger | nDCG: baseline / challenger | Delta |
|---|---|---|---|

## Decision

Retain working baseline; keep scored fusion as challenger pending recall tradeoff approval.
Improved mean nDCG/MRR and first-place hits do not erase source recall regressions. Review all lost hits and lower-list relevance losses rather than treating leaderboard position as automatic promotion. Known-item target ranks are checked independently; the held-out test remains untouched.
Full abstracts, per-paper grades, raw normalized score contributions and ranks are in cases.json. All 100 query changes and segment CIs are in report.json.
