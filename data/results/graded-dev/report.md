# Graded dev retrieval

Judge: `openai-mini` (`gpt-5.4-mini`); rubric `b8b0c14a`. 100 dev queries, 2857/2857 pooled pairs judged; 100 human pair labels take priority.

**Calibration limitation:** one person's 100 pilot labels, no fresh-human validation. Selecting the judge on these labels is calibration, not independent confirmation. Gemma wrote the queries. No held-out test scores here.

**Metric definitions:** linear-gain nDCG@10; P@10 counts grades 1 and 2 as relevant; unjudged papers count as zero. Ideal DCG uses the same pooled labels plus human overrides for every system. nDCG is undefined if no relevant label exists; the nDCG n column shows how many queries are included. P@10 and judged@10 include all dev queries.



| System | nDCG@10 [95% CI] | nDCG n | P@10 [95% CI] | judged@10 |
|---|---|---|---|---|
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | 0.538 [0.499, 0.577] | 100/100 | 0.512 [0.468, 0.565] | 100.0% |
| `dense-gte-small` | 0.603 [0.567, 0.641] | 100/100 | 0.581 [0.537, 0.623] | 100.0% |
| `dense-bge-small` | 0.599 [0.559, 0.635] | 100/100 | 0.584 [0.540, 0.627] | 100.0% |
| `hybrid-gte-small+rrf+w=0.5+c=10` | 0.655 [0.620, 0.687] | 100/100 | 0.611 [0.570, 0.652] | 100.0% |
| `hybrid-bge-small+rrf+w=0.5+c=10` | 0.652 [0.617, 0.683] | 100/100 | 0.614 [0.571, 0.656] | 100.0% |
| `dense-openai-large` | 0.668 [0.634, 0.700] | 100/100 | 0.637 [0.592, 0.682] | 100.0% |
| `hybrid-openai-large+rrf+w=0.5+c=10` | 0.686 [0.659, 0.712] | 100/100 | 0.633 [0.595, 0.673] | 100.0% |

## Planned paired comparisons

Differences are B minus A on identical query IDs. Intervals describe query sampling uncertainty conditional on these labels, not judge accuracy. These exploratory dev comparisons are not adjusted for multiple testing.

| A | B | Metric | Queries | Difference [95% CI] |
|---|---|---|---|---|
| `hybrid-gte-small+rrf+w=0.5+c=10` | `hybrid-openai-large+rrf+w=0.5+c=10` | ndcg@10 | 100 | +0.030 [+0.007, +0.055] |
| `hybrid-gte-small+rrf+w=0.5+c=10` | `hybrid-openai-large+rrf+w=0.5+c=10` | precision@10 | 100 | +0.022 [-0.005, +0.049] |
| `dense-openai-large` | `hybrid-openai-large+rrf+w=0.5+c=10` | ndcg@10 | 100 | +0.018 [-0.011, +0.046] |
| `dense-openai-large` | `hybrid-openai-large+rrf+w=0.5+c=10` | precision@10 | 100 | -0.004 [-0.035, +0.028] |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | `hybrid-openai-large+rrf+w=0.5+c=10` | ndcg@10 | 100 | +0.148 [+0.116, +0.177] |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | `hybrid-openai-large+rrf+w=0.5+c=10` | precision@10 | 100 | +0.121 [+0.087, +0.153] |

## By query type

| System | Type | Queries | nDCG@10 [95% CI] | P@10 [95% CI] | judged@10 |
|---|---|---|---|---|---|
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | keyword | 25 | 0.632 [0.571, 0.692] | 0.596 [0.472, 0.708] | 100.0% |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | known_item | 25 | 0.690 [0.650, 0.731] | 0.588 [0.496, 0.680] | 100.0% |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | paraphrase | 25 | 0.380 [0.288, 0.463] | 0.412 [0.316, 0.500] | 100.0% |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | question | 25 | 0.449 [0.399, 0.505] | 0.452 [0.380, 0.532] | 100.0% |
| `dense-gte-small` | keyword | 25 | 0.682 [0.611, 0.746] | 0.652 [0.552, 0.744] | 100.0% |
| `dense-gte-small` | known_item | 25 | 0.600 [0.513, 0.684] | 0.520 [0.432, 0.612] | 100.0% |
| `dense-gte-small` | paraphrase | 25 | 0.525 [0.465, 0.585] | 0.536 [0.476, 0.596] | 100.0% |
| `dense-gte-small` | question | 25 | 0.605 [0.555, 0.660] | 0.616 [0.548, 0.684] | 100.0% |
| `dense-bge-small` | keyword | 25 | 0.656 [0.588, 0.716] | 0.656 [0.572, 0.732] | 100.0% |
| `dense-bge-small` | known_item | 25 | 0.644 [0.581, 0.702] | 0.560 [0.472, 0.652] | 100.0% |
| `dense-bge-small` | paraphrase | 25 | 0.480 [0.394, 0.562] | 0.496 [0.392, 0.588] | 100.0% |
| `dense-bge-small` | question | 25 | 0.615 [0.559, 0.674] | 0.624 [0.560, 0.692] | 100.0% |
| `hybrid-gte-small+rrf+w=0.5+c=10` | keyword | 25 | 0.735 [0.681, 0.785] | 0.688 [0.596, 0.764] | 100.0% |
| `hybrid-gte-small+rrf+w=0.5+c=10` | known_item | 25 | 0.726 [0.676, 0.778] | 0.604 [0.512, 0.696] | 100.0% |
| `hybrid-gte-small+rrf+w=0.5+c=10` | paraphrase | 25 | 0.536 [0.469, 0.599] | 0.556 [0.488, 0.628] | 100.0% |
| `hybrid-gte-small+rrf+w=0.5+c=10` | question | 25 | 0.624 [0.574, 0.678] | 0.596 [0.528, 0.668] | 100.0% |
| `hybrid-bge-small+rrf+w=0.5+c=10` | keyword | 25 | 0.722 [0.677, 0.765] | 0.692 [0.608, 0.768] | 100.0% |
| `hybrid-bge-small+rrf+w=0.5+c=10` | known_item | 25 | 0.741 [0.689, 0.789] | 0.620 [0.528, 0.712] | 100.0% |
| `hybrid-bge-small+rrf+w=0.5+c=10` | paraphrase | 25 | 0.500 [0.426, 0.570] | 0.528 [0.440, 0.608] | 100.0% |
| `hybrid-bge-small+rrf+w=0.5+c=10` | question | 25 | 0.643 [0.596, 0.694] | 0.616 [0.544, 0.692] | 100.0% |
| `dense-openai-large` | keyword | 25 | 0.668 [0.596, 0.738] | 0.676 [0.592, 0.760] | 100.0% |
| `dense-openai-large` | known_item | 25 | 0.620 [0.547, 0.696] | 0.516 [0.416, 0.620] | 100.0% |
| `dense-openai-large` | paraphrase | 25 | 0.670 [0.608, 0.730] | 0.652 [0.584, 0.720] | 100.0% |
| `dense-openai-large` | question | 25 | 0.713 [0.670, 0.757] | 0.704 [0.648, 0.768] | 100.0% |
| `hybrid-openai-large+rrf+w=0.5+c=10` | keyword | 25 | 0.723 [0.667, 0.772] | 0.692 [0.604, 0.772] | 100.0% |
| `hybrid-openai-large+rrf+w=0.5+c=10` | known_item | 25 | 0.718 [0.676, 0.764] | 0.604 [0.520, 0.692] | 100.0% |
| `hybrid-openai-large+rrf+w=0.5+c=10` | paraphrase | 25 | 0.616 [0.552, 0.676] | 0.576 [0.508, 0.644] | 100.0% |
| `hybrid-openai-large+rrf+w=0.5+c=10` | question | 25 | 0.686 [0.647, 0.725] | 0.660 [0.616, 0.708] | 100.0% |
