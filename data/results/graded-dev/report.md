# Graded dev retrieval

Judge: Gemma; rubric `b8b0c14a`. 100 dev queries, 276/2857 pooled pairs judged; 100 human pair labels take priority.

**Calibration limitation:** one person's 100 pilot labels, no fresh-human validation. Gemma also wrote the queries. No held-out test scores here.

**Metric definitions:** linear-gain nDCG@10; P@10 counts grades 1 and 2 as relevant; unjudged papers count as zero. Ideal DCG uses the same pooled labels plus human overrides for every system. nDCG is undefined if no relevant label exists; the nDCG n column shows how many queries are included. P@10 and judged@10 include all dev queries.

**INCOMPLETE / PROVISIONAL: do not rank systems by these scores until all compared top-10 lists are judged.**

| System | nDCG@10 [95% CI] | nDCG n | P@10 [95% CI] | judged@10 |
|---|---|---|---|---|
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | 0.656 [0.563, 0.749] | 13/100 | 0.079 [0.040, 0.125] | 13.0% |
| `dense-gte-small` | 0.573 [0.483, 0.663] | 13/100 | 0.070 [0.034, 0.114] | 12.4% |
| `dense-bge-small` | 0.584 [0.507, 0.652] | 13/100 | 0.073 [0.039, 0.116] | 12.5% |
| `hybrid-gte-small+rrf+w=0.5+c=10` | 0.711 [0.629, 0.784] | 13/100 | 0.086 [0.046, 0.136] | 12.8% |
| `hybrid-bge-small+rrf+w=0.5+c=10` | 0.689 [0.613, 0.755] | 13/100 | 0.077 [0.040, 0.120] | 12.7% |
| `dense-openai-large` | 0.563 [0.505, 0.620] | 13/100 | 0.059 [0.030, 0.092] | 7.2% |
| `hybrid-openai-large+rrf+w=0.5+c=10` | 0.686 [0.627, 0.746] | 13/100 | 0.073 [0.038, 0.114] | 10.4% |

## By query type

| System | Type | Queries | nDCG@10 [95% CI] | P@10 [95% CI] | judged@10 |
|---|---|---|---|---|---|
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | keyword | 25 | 0.816 [0.732, 0.900] | 0.120 [0.024, 0.236] | 16.0% |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | known_item | 25 | 0.682 [0.537, 0.780] | 0.056 [0.000, 0.124] | 12.0% |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | paraphrase | 25 | 0.498 [0.303, 0.766] | 0.068 [0.000, 0.152] | 12.0% |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | question | 25 | 0.573 [0.416, 0.673] | 0.072 [0.000, 0.168] | 12.0% |
| `dense-gte-small` | keyword | 25 | 0.685 [0.628, 0.793] | 0.100 [0.020, 0.204] | 13.6% |
| `dense-gte-small` | known_item | 25 | 0.681 [0.581, 0.847] | 0.056 [0.000, 0.136] | 12.0% |
| `dense-gte-small` | paraphrase | 25 | 0.428 [0.256, 0.587] | 0.060 [0.000, 0.136] | 12.0% |
| `dense-gte-small` | question | 25 | 0.461 [0.286, 0.633] | 0.064 [0.000, 0.136] | 12.0% |
| `dense-bge-small` | keyword | 25 | 0.565 [0.413, 0.718] | 0.076 [0.012, 0.156] | 14.0% |
| `dense-bge-small` | known_item | 25 | 0.673 [0.581, 0.732] | 0.056 [0.000, 0.132] | 12.0% |
| `dense-bge-small` | paraphrase | 25 | 0.591 [0.354, 0.739] | 0.080 [0.000, 0.176] | 12.0% |
| `dense-bge-small` | question | 25 | 0.516 [0.446, 0.574] | 0.080 [0.000, 0.180] | 12.0% |
| `hybrid-gte-small+rrf+w=0.5+c=10` | keyword | 25 | 0.838 [0.825, 0.849] | 0.124 [0.028, 0.240] | 15.2% |
| `hybrid-gte-small+rrf+w=0.5+c=10` | known_item | 25 | 0.779 [0.718, 0.829] | 0.072 [0.000, 0.164] | 12.0% |
| `hybrid-gte-small+rrf+w=0.5+c=10` | paraphrase | 25 | 0.492 [0.413, 0.633] | 0.068 [0.000, 0.148] | 12.0% |
| `hybrid-gte-small+rrf+w=0.5+c=10` | question | 25 | 0.692 [0.600, 0.794] | 0.080 [0.000, 0.180] | 12.0% |
| `hybrid-bge-small+rrf+w=0.5+c=10` | keyword | 25 | 0.798 [0.750, 0.843] | 0.108 [0.028, 0.212] | 14.8% |
| `hybrid-bge-small+rrf+w=0.5+c=10` | known_item | 25 | 0.771 [0.731, 0.793] | 0.068 [0.000, 0.156] | 12.0% |
| `hybrid-bge-small+rrf+w=0.5+c=10` | paraphrase | 25 | 0.540 [0.352, 0.682] | 0.064 [0.000, 0.140] | 12.0% |
| `hybrid-bge-small+rrf+w=0.5+c=10` | question | 25 | 0.612 [0.496, 0.705] | 0.068 [0.000, 0.152] | 12.0% |
| `dense-openai-large` | keyword | 25 | 0.573 [0.407, 0.721] | 0.076 [0.016, 0.144] | 8.4% |
| `dense-openai-large` | known_item | 25 | 0.563 [0.507, 0.649] | 0.040 [0.000, 0.092] | 6.0% |
| `dense-openai-large` | paraphrase | 25 | 0.514 [0.464, 0.569] | 0.056 [0.000, 0.124] | 6.8% |
| `dense-openai-large` | question | 25 | 0.601 [0.553, 0.692] | 0.064 [0.000, 0.148] | 7.6% |
| `hybrid-openai-large+rrf+w=0.5+c=10` | keyword | 25 | 0.774 [0.715, 0.854] | 0.104 [0.024, 0.204] | 12.4% |
| `hybrid-openai-large+rrf+w=0.5+c=10` | known_item | 25 | 0.687 [0.622, 0.782] | 0.052 [0.000, 0.120] | 9.6% |
| `hybrid-openai-large+rrf+w=0.5+c=10` | paraphrase | 25 | 0.558 [0.519, 0.633] | 0.060 [0.000, 0.132] | 8.8% |
| `hybrid-openai-large+rrf+w=0.5+c=10` | question | 25 | 0.697 [0.626, 0.832] | 0.076 [0.000, 0.172] | 10.8% |
