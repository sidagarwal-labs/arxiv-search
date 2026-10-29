# Graded dev retrieval

Judge: `openai-mini` (`gpt-5.4-mini`); rubric `b8b0c14a`. 100 dev queries, 175/2857 pooled pairs judged; 100 human pair labels take priority.

**Calibration limitation:** one person's 100 pilot labels, no fresh-human validation. Selecting the judge on these labels is calibration, not independent confirmation. Gemma wrote the queries. No held-out test scores here.

**Metric definitions:** linear-gain nDCG@10; P@10 counts grades 1 and 2 as relevant; unjudged papers count as zero. Ideal DCG uses the same pooled labels plus human overrides for every system. nDCG is undefined if no relevant label exists; the nDCG n column shows how many queries are included. P@10 and judged@10 include all dev queries.

**INCOMPLETE / PROVISIONAL: do not rank systems by these scores until all compared top-10 lists are judged.**

| System | nDCG@10 [95% CI] | nDCG n | P@10 [95% CI] | judged@10 |
|---|---|---|---|---|
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | 0.475 [0.333, 0.604] | 15/100 | 0.045 [0.020, 0.075] | 7.2% |
| `dense-gte-small` | 0.532 [0.392, 0.662] | 15/100 | 0.047 [0.024, 0.075] | 8.1% |
| `dense-bge-small` | 0.509 [0.392, 0.625] | 15/100 | 0.047 [0.022, 0.074] | 7.3% |
| `hybrid-gte-small+rrf+w=0.5+c=10` | 0.585 [0.436, 0.711] | 15/100 | 0.055 [0.027, 0.087] | 7.9% |
| `hybrid-bge-small+rrf+w=0.5+c=10` | 0.555 [0.419, 0.675] | 15/100 | 0.052 [0.025, 0.084] | 7.8% |
| `dense-openai-large` | 0.510 [0.398, 0.628] | 15/100 | 0.042 [0.020, 0.067] | 5.8% |
| `hybrid-openai-large+rrf+w=0.5+c=10` | 0.517 [0.374, 0.644] | 15/100 | 0.045 [0.021, 0.073] | 6.7% |

## By query type

| System | Type | Queries | nDCG@10 [95% CI] | P@10 [95% CI] | judged@10 |
|---|---|---|---|---|---|
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | keyword | 25 | 0.557 [0.342, 0.696] | 0.104 [0.024, 0.208] | 15.2% |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | known_item | 25 | 0.792 [0.760, 0.855] | 0.024 [0.000, 0.060] | 5.2% |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | paraphrase | 25 | 0.165 [0.096, 0.229] | 0.020 [0.000, 0.044] | 2.8% |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | question | 25 | 0.305 [0.149, 0.386] | 0.032 [0.000, 0.072] | 5.6% |
| `dense-gte-small` | keyword | 25 | 0.580 [0.382, 0.725] | 0.104 [0.032, 0.200] | 16.0% |
| `dense-gte-small` | known_item | 25 | 0.821 [0.702, 0.887] | 0.024 [0.000, 0.056] | 6.4% |
| `dense-gte-small` | paraphrase | 25 | 0.280 [0.109, 0.421] | 0.024 [0.000, 0.056] | 4.8% |
| `dense-gte-small` | question | 25 | 0.398 [0.160, 0.728] | 0.036 [0.000, 0.088] | 5.2% |
| `dense-bge-small` | keyword | 25 | 0.511 [0.330, 0.671] | 0.092 [0.028, 0.180] | 16.4% |
| `dense-bge-small` | known_item | 25 | 0.781 [0.702, 0.880] | 0.020 [0.000, 0.044] | 4.4% |
| `dense-bge-small` | paraphrase | 25 | 0.369 [0.253, 0.427] | 0.036 [0.000, 0.088] | 4.0% |
| `dense-bge-small` | question | 25 | 0.374 [0.182, 0.567] | 0.040 [0.000, 0.088] | 4.4% |
| `hybrid-gte-small+rrf+w=0.5+c=10` | keyword | 25 | 0.663 [0.436, 0.805] | 0.124 [0.040, 0.232] | 17.2% |
| `hybrid-gte-small+rrf+w=0.5+c=10` | known_item | 25 | 0.844 [0.786, 0.875] | 0.028 [0.000, 0.064] | 4.4% |
| `hybrid-gte-small+rrf+w=0.5+c=10` | paraphrase | 25 | 0.281 [0.109, 0.497] | 0.028 [0.000, 0.068] | 4.0% |
| `hybrid-gte-small+rrf+w=0.5+c=10` | question | 25 | 0.476 [0.160, 0.755] | 0.040 [0.000, 0.092] | 6.0% |
| `hybrid-bge-small+rrf+w=0.5+c=10` | keyword | 25 | 0.655 [0.442, 0.783] | 0.128 [0.040, 0.236] | 18.0% |
| `hybrid-bge-small+rrf+w=0.5+c=10` | known_item | 25 | 0.774 [0.760, 0.802] | 0.020 [0.000, 0.048] | 3.6% |
| `hybrid-bge-small+rrf+w=0.5+c=10` | paraphrase | 25 | 0.293 [0.224, 0.424] | 0.028 [0.000, 0.064] | 4.4% |
| `hybrid-bge-small+rrf+w=0.5+c=10` | question | 25 | 0.398 [0.109, 0.699] | 0.032 [0.000, 0.072] | 5.2% |
| `dense-openai-large` | keyword | 25 | 0.468 [0.289, 0.628] | 0.084 [0.020, 0.180] | 13.6% |
| `dense-openai-large` | known_item | 25 | 0.750 [0.606, 1.000] | 0.024 [0.000, 0.056] | 3.2% |
| `dense-openai-large` | paraphrase | 25 | 0.412 [0.354, 0.499] | 0.028 [0.000, 0.064] | 2.8% |
| `dense-openai-large` | question | 25 | 0.452 [0.329, 0.699] | 0.032 [0.000, 0.068] | 3.6% |
| `hybrid-openai-large+rrf+w=0.5+c=10` | keyword | 25 | 0.584 [0.392, 0.707] | 0.104 [0.032, 0.200] | 15.2% |
| `hybrid-openai-large+rrf+w=0.5+c=10` | known_item | 25 | 0.785 [0.670, 0.924] | 0.020 [0.000, 0.044] | 3.2% |
| `hybrid-openai-large+rrf+w=0.5+c=10` | paraphrase | 25 | 0.205 [0.124, 0.331] | 0.020 [0.000, 0.052] | 2.8% |
| `hybrid-openai-large+rrf+w=0.5+c=10` | question | 25 | 0.429 [0.109, 0.699] | 0.036 [0.000, 0.084] | 5.6% |
