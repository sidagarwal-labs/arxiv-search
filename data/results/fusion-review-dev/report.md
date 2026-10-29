# Pre-promotion fusion review

Offline dev-only review; no API calls, new labels, or baseline changes. All compared top-10 results are judged using the same frozen 3,190-pair snapshot.
Source metrics credit only the generation-source paper; graded metrics credit all labeled relevant papers. Intervals are exploratory paired bootstraps, not multiplicity-adjusted or independent held-out confirmation. Judge reasons are diagnostic evidence, not ground truth.

| System | Segment | nDCG@10 | P@10 | Source MRR@10 | Source R@1 | Source R@10 |
|---|---|---|---|---|---|---|
| baseline-original-equal-rrf-c10-d100 | all | 0.6641 | 0.6330 | 0.6534 | 0.5600 | 0.8400 |
| baseline-original-equal-rrf-c10-d100 | keyword | 0.7001 | 0.6920 | 0.7167 | 0.6000 | 0.9600 |
| baseline-original-equal-rrf-c10-d100 | known_item | 0.6948 | 0.6040 | 0.9800 | 0.9600 | 1.0000 |
| baseline-original-equal-rrf-c10-d100 | paraphrase | 0.5940 | 0.5760 | 0.3644 | 0.2400 | 0.6400 |
| baseline-original-equal-rrf-c10-d100 | question | 0.6676 | 0.6600 | 0.5527 | 0.4400 | 0.7600 |
| fusion-rrf+w=0.75+d=100+c=100 | all | 0.7095 | 0.6900 | 0.6181 | 0.5200 | 0.8400 |
| fusion-rrf+w=0.75+d=100+c=100 | keyword | 0.7347 | 0.7440 | 0.6437 | 0.5200 | 0.9200 |
| fusion-rrf+w=0.75+d=100+c=100 | known_item | 0.7137 | 0.6200 | 0.9433 | 0.9200 | 1.0000 |
| fusion-rrf+w=0.75+d=100+c=100 | paraphrase | 0.6580 | 0.6480 | 0.3206 | 0.2000 | 0.6800 |
| fusion-rrf+w=0.75+d=100+c=100 | question | 0.7315 | 0.7480 | 0.5647 | 0.4400 | 0.7600 |
| fusion-rrf+w=0.55+d=100+c=30 | all | 0.7106 | 0.6890 | 0.6459 | 0.5500 | 0.8600 |
| fusion-rrf+w=0.55+d=100+c=30 | keyword | 0.7373 | 0.7440 | 0.6632 | 0.5200 | 0.9600 |
| fusion-rrf+w=0.55+d=100+c=30 | known_item | 0.7156 | 0.6240 | 0.9800 | 0.9600 | 1.0000 |
| fusion-rrf+w=0.55+d=100+c=30 | paraphrase | 0.6662 | 0.6480 | 0.3823 | 0.2800 | 0.7200 |
| fusion-rrf+w=0.55+d=100+c=30 | question | 0.7234 | 0.7400 | 0.5580 | 0.4400 | 0.7600 |
| fusion-rrf+w=0.6+d=100+c=60 | all | 0.7139 | 0.7000 | 0.6302 | 0.5300 | 0.8300 |
| fusion-rrf+w=0.6+d=100+c=60 | keyword | 0.7449 | 0.7520 | 0.6614 | 0.5200 | 0.9600 |
| fusion-rrf+w=0.6+d=100+c=60 | known_item | 0.7213 | 0.6360 | 0.9533 | 0.9200 | 1.0000 |
| fusion-rrf+w=0.6+d=100+c=60 | paraphrase | 0.6618 | 0.6680 | 0.3468 | 0.2400 | 0.6000 |
| fusion-rrf+w=0.6+d=100+c=60 | question | 0.7276 | 0.7440 | 0.5593 | 0.4400 | 0.7600 |

## Candidate minus baseline-original-equal-rrf-c10-d100

| Segment | Metric | Delta | 95% CI | Wins / losses / ties |
|---|---|---|---|---|
| all | ndcg@10 | +0.0465 | [+0.0311, +0.0628] | 70 / 26 / 4 |
| all | precision@10 | +0.0560 | [+0.0360, +0.0780] | 46 / 11 / 43 |
| all | source_mrr@10 | -0.0076 | [-0.0330, +0.0162] | 8 / 13 / 79 |
| keyword | ndcg@10 | +0.0371 | [+0.0113, +0.0633] | 18 / 6 / 1 |
| keyword | precision@10 | +0.0520 | [+0.0159, +0.0960] | 10 / 1 / 14 |
| keyword | source_mrr@10 | -0.0535 | [-0.1125, -0.0090] | 1 / 5 / 19 |
| known_item | ndcg@10 | +0.0208 | [-0.0050, +0.0484] | 15 / 7 / 3 |
| known_item | precision@10 | +0.0200 | [-0.0200, +0.0600] | 8 / 5 / 12 |
| known_item | source_mrr@10 | +0.0000 | [+0.0000, +0.0000] | 0 / 0 / 25 |
| paraphrase | ndcg@10 | +0.0723 | [+0.0360, +0.1083] | 17 / 8 / 0 |
| paraphrase | precision@10 | +0.0720 | [+0.0360, +0.1160] | 14 / 3 / 8 |
| paraphrase | source_mrr@10 | +0.0178 | [-0.0581, +0.0960] | 5 / 6 / 14 |
| question | ndcg@10 | +0.0558 | [+0.0290, +0.0824] | 20 / 5 / 0 |
| question | precision@10 | +0.0800 | [+0.0400, +0.1240] | 14 / 2 / 9 |
| question | source_mrr@10 | +0.0053 | [-0.0053, +0.0213] | 2 / 2 / 21 |

## Candidate minus fusion-rrf+w=0.75+d=100+c=100

| Segment | Metric | Delta | 95% CI | Wins / losses / ties |
|---|---|---|---|---|
| all | ndcg@10 | +0.0011 | [-0.0104, +0.0125] | 41 / 52 / 7 |
| all | precision@10 | -0.0010 | [-0.0150, +0.0130] | 21 / 21 / 58 |
| all | source_mrr@10 | +0.0278 | [+0.0077, +0.0550] | 12 / 6 / 82 |
| keyword | ndcg@10 | +0.0026 | [-0.0145, +0.0210] | 12 / 12 / 1 |
| keyword | precision@10 | -0.0000 | [-0.0240, +0.0240] | 4 / 4 / 17 |
| keyword | source_mrr@10 | +0.0194 | [-0.0040, +0.0451] | 4 / 2 / 19 |
| known_item | ndcg@10 | +0.0019 | [-0.0162, +0.0223] | 10 / 12 / 3 |
| known_item | precision@10 | +0.0040 | [-0.0280, +0.0360] | 5 / 4 / 16 |
| known_item | source_mrr@10 | +0.0367 | [+0.0000, +0.1033] | 2 / 0 / 23 |
| paraphrase | ndcg@10 | +0.0083 | [-0.0174, +0.0339] | 10 / 14 / 1 |
| paraphrase | precision@10 | -0.0000 | [-0.0320, +0.0320] | 7 / 6 / 12 |
| paraphrase | source_mrr@10 | +0.0617 | [+0.0088, +0.1254] | 6 / 3 / 16 |
| question | ndcg@10 | -0.0081 | [-0.0255, +0.0114] | 9 / 14 / 2 |
| question | precision@10 | -0.0080 | [-0.0360, +0.0200] | 5 / 7 / 13 |
| question | source_mrr@10 | -0.0067 | [-0.0200, +0.0000] | 0 / 1 / 24 |

## Candidate minus fusion-rrf+w=0.6+d=100+c=60

| Segment | Metric | Delta | 95% CI | Wins / losses / ties |
|---|---|---|---|---|
| all | ndcg@10 | -0.0033 | [-0.0123, +0.0056] | 33 / 47 / 20 |
| all | precision@10 | -0.0110 | [-0.0240, +0.0010] | 11 / 20 / 69 |
| all | source_mrr@10 | +0.0156 | [+0.0024, +0.0353] | 9 / 2 / 89 |
| keyword | ndcg@10 | -0.0076 | [-0.0188, +0.0028] | 6 / 14 / 5 |
| keyword | precision@10 | -0.0080 | [-0.0320, +0.0120] | 2 / 3 / 20 |
| keyword | source_mrr@10 | +0.0017 | [-0.0011, +0.0053] | 2 / 1 / 22 |
| known_item | ndcg@10 | -0.0058 | [-0.0222, +0.0112] | 8 / 9 / 8 |
| known_item | precision@10 | -0.0120 | [-0.0360, +0.0080] | 2 / 4 / 19 |
| known_item | source_mrr@10 | +0.0267 | [+0.0000, +0.0800] | 1 / 0 / 24 |
| paraphrase | ndcg@10 | +0.0045 | [-0.0168, +0.0264] | 10 / 12 / 3 |
| paraphrase | precision@10 | -0.0200 | [-0.0440, +0.0040] | 3 / 7 / 15 |
| paraphrase | source_mrr@10 | +0.0355 | [+0.0061, +0.0782] | 6 / 0 / 19 |
| question | ndcg@10 | -0.0042 | [-0.0214, +0.0134] | 9 / 12 / 4 |
| question | precision@10 | -0.0040 | [-0.0320, +0.0280] | 4 / 6 / 15 |
| question | source_mrr@10 | -0.0013 | [-0.0040, +0.0000] | 0 / 1 / 24 |

## baseline-original-equal-rrf-c10-d100/ndcg@10/gains

| Query | Text | Candidate minus control |
|---|---|---|
| q-paraphrase-030 | a way to suggest places to visit based on the idea that some spots require prior knowledge from other spots | +0.3126 |
| q-known_item-061 | Ko decoupling content delivery medical qa | +0.2647 |
| q-paraphrase-093 | finding a way to group chip design manual snippets into logical blocks to help a bot answer technical questions better | +0.2614 |
| q-question-095 | Can a single general purpose model be used for various atmospheric science tasks? | +0.2163 |
| q-paraphrase-006 | fixing systemic prejudices in generative suggestion engines by erasing the impact of problematic data points without full model updates | +0.2153 |

## baseline-original-equal-rrf-c10-d100/ndcg@10/regressions

| Query | Text | Candidate minus control |
|---|---|---|
| q-keyword-062 | GNN proxy for SDP relaxations | -0.1083 |
| q-known_item-062 | Flek physics constraint adversarial attacks | -0.0977 |
| q-known_item-031 | Boyd clinical provenance categorization | -0.0879 |
| q-question-088 | how can llm agents reuse specific workflows from previous tasks to avoid forgetting? | -0.0714 |
| q-known_item-047 | van der Klis lorentz neural networks | -0.0672 |

## baseline-original-equal-rrf-c10-d100/source_mrr@10/gains

| Query | Text | Candidate minus control |
|---|---|---|
| q-paraphrase-088 | a review of using programmable scripts as the core structure for managing ai assistant reasoning and tool execution | +0.6667 |
| q-paraphrase-030 | a way to suggest places to visit based on the idea that some spots require prior knowledge from other spots | +0.5000 |
| q-question-019 | how does repeating training data affect model performance during pretraining? | +0.1667 |
| q-paraphrase-087 | finding the best evidence subgraphs from a hidden knowledge graph without needing to train the system | +0.1250 |
| q-paraphrase-062 | guessing the number of tokens an AI will generate for a prompt that can have wildly different response sizes | +0.1000 |

## baseline-original-equal-rrf-c10-d100/source_mrr@10/regressions

| Query | Text | Candidate minus control |
|---|---|---|
| q-keyword-009 | automated community clustering topic models | -0.5000 |
| q-keyword-062 | GNN proxy for SDP relaxations | -0.5000 |
| q-paraphrase-043 | exploring how many previous turns in a chat are actually needed to identify a speaker's mood and the role of sentence starters | -0.5000 |
| q-keyword-081 | llm popularity prediction recommendation | -0.1667 |
| q-paraphrase-020 | reducing data exchange by avoiding error signal propagation in shared neural architectures | -0.1667 |

## fusion-rrf+w=0.75+d=100+c=100/ndcg@10/gains

| Query | Text | Candidate minus control |
|---|---|---|
| q-paraphrase-030 | a way to suggest places to visit based on the idea that some spots require prior knowledge from other spots | +0.1568 |
| q-paraphrase-088 | a review of using programmable scripts as the core structure for managing ai assistant reasoning and tool execution | +0.1517 |
| q-known_item-070 | Chenrun Wang research idea benchmark | +0.1364 |
| q-paraphrase-014 | finding a probabilistic upper limit on how far the actor parameter stays from the optimal value in a slow-fast reinforcement learning setup | +0.1131 |
| q-keyword-072 | BL19 digital collection retrieval benchmark | +0.1087 |

## fusion-rrf+w=0.75+d=100+c=100/ndcg@10/regressions

| Query | Text | Candidate minus control |
|---|---|---|
| q-question-077 | can standard graph neural networks perform link prediction on unknown knowledge graphs? | -0.0909 |
| q-question-019 | how does repeating training data affect model performance during pretraining? | -0.0883 |
| q-keyword-074 | distributional RL chaotic dynamics | -0.0883 |
| q-known_item-059 | Roth GraphER reranking RAG | -0.0863 |
| q-paraphrase-077 | a comprehensive look at using low precision numbers to speed up training across distributed private devices | -0.0834 |

## fusion-rrf+w=0.75+d=100+c=100/source_mrr@10/gains

| Query | Text | Candidate minus control |
|---|---|---|
| q-known_item-088 | Mathur rag policy qa | +0.7500 |
| q-paraphrase-088 | a review of using programmable scripts as the core structure for managing ai assistant reasoning and tool execution | +0.6667 |
| q-paraphrase-030 | a way to suggest places to visit based on the idea that some spots require prior knowledge from other spots | +0.5000 |
| q-keyword-072 | BL19 digital collection retrieval benchmark | +0.2500 |
| q-keyword-021 | transformer recommender popularity bias | +0.1667 |

## fusion-rrf+w=0.75+d=100+c=100/source_mrr@10/regressions

| Query | Text | Candidate minus control |
|---|---|---|
| q-question-077 | can standard graph neural networks perform link prediction on unknown knowledge graphs? | -0.1667 |
| q-keyword-011 | medical knowledge graphs clinical llm | -0.0571 |
| q-keyword-053 | graph machine learning chemical reaction | -0.0556 |
| q-paraphrase-087 | finding the best evidence subgraphs from a hidden knowledge graph without needing to train the system | -0.0179 |
| q-paraphrase-032 | maximizing income for power conversion tools and cells by using actual device behavior in Nordic power exchanges | -0.0139 |

## fusion-rrf+w=0.6+d=100+c=60/ndcg@10/gains

| Query | Text | Candidate minus control |
|---|---|---|
| q-paraphrase-030 | a way to suggest places to visit based on the idea that some spots require prior knowledge from other spots | +0.1568 |
| q-paraphrase-014 | finding a probabilistic upper limit on how far the actor parameter stays from the optimal value in a slow-fast reinforcement learning setup | +0.1307 |
| q-question-040 | How can tool specifications be used to create synthetic test cases for AI agents? | +0.1016 |
| q-known_item-054 | Tannenbaum conversation context effect | +0.0945 |
| q-paraphrase-093 | finding a way to group chip design manual snippets into logical blocks to help a bot answer technical questions better | +0.0870 |

## fusion-rrf+w=0.6+d=100+c=60/ndcg@10/regressions

| Query | Text | Candidate minus control |
|---|---|---|
| q-paraphrase-047 | identifying clusters by removing odd ones out using a few starting markers | -0.1185 |
| q-known_item-059 | Roth GraphER reranking RAG | -0.1088 |
| q-known_item-073 | Wei complexity structural generalization | -0.0889 |
| q-question-003 | how can large language models actively gather information to improve product recommendations? | -0.0884 |
| q-keyword-005 | rl self play strategy games | -0.0858 |

## fusion-rrf+w=0.6+d=100+c=60/source_mrr@10/gains

| Query | Text | Candidate minus control |
|---|---|---|
| q-known_item-088 | Mathur rag policy qa | +0.6667 |
| q-paraphrase-030 | a way to suggest places to visit based on the idea that some spots require prior knowledge from other spots | +0.5000 |
| q-paraphrase-097 | improving language model self training by picking varied ways to solve a problem instead of just correct ones | +0.1429 |
| q-paraphrase-014 | finding a probabilistic upper limit on how far the actor parameter stays from the optimal value in a slow-fast reinforcement learning setup | +0.1000 |
| q-paraphrase-062 | guessing the number of tokens an AI will generate for a prompt that can have wildly different response sizes | +0.1000 |

## fusion-rrf+w=0.6+d=100+c=60/source_mrr@10/regressions

| Query | Text | Candidate minus control |
|---|---|---|
| q-question-077 | can standard graph neural networks perform link prediction on unknown knowledge graphs? | -0.0333 |
| q-keyword-053 | graph machine learning chemical reaction | -0.0139 |
