# Score-based fusion and deeper retrieval (dev only)

Cached embeddings; no baseline promotion. Judge calls this invocation: 0. All source top100 rankings exactly reproduce the frozen experiment. Cosine/BM25 scores are recomputed from cached vectors and the same lexical recipe.
max divides each list by its maximum; minmax subtracts its top-depth minimum then divides by its range. Each input is truncated to depth before normalization. Missing-list scores are zero. Constant positive lists receive unit scores.
Score weights are not comparable numerically to RRF weights. Top1 bonuses are fractions of each retriever's weighted rank-one RRF contribution.
**Incomplete graded scores are PROVISIONAL, not winner evidence.** All graded rows use one additive shared label snapshot; original grades are preserved and new cached judgments extend the ideal denominator. Unjudged gains count as zero. Source metrics are complete and remain valid. Label only missing pairs before comparing provisional graded results. Exploratory dev results and intervals are not multiple-testing adjusted.

New unjudged query-paper pairs across this grid: 0.

| System | nDCG10 (provisional if coverage <100%) | P10 | Judged10 | Source MRR10 | Known-item MRR | Source R10 | Source R20 |
|---|---|---|---|---|---|---|---|
| `score-max+w=0.35+d=100` | 0.6742 | 0.6700 | 1.0000 | 0.6358 | 1.0000 | 0.7500 | 0.7800 |
| `score-max+w=0.35+d=500` | 0.6373 | 0.6350 | 1.0000 | 0.6189 | 1.0000 | 0.7700 | 0.8000 |
| `score-max+w=0.55+d=100` | 0.6994 | 0.6860 | 1.0000 | 0.6559 | 0.9800 | 0.7900 | 0.8600 |
| `score-max+w=0.55+d=500` | 0.6874 | 0.6700 | 1.0000 | 0.6568 | 0.9800 | 0.8100 | 0.8400 |
| `score-max+w=0.75+d=100` | 0.7111 | 0.6860 | 1.0000 | 0.6682 | 0.9800 | 0.8200 | 0.8700 |
| `score-max+w=0.75+d=500` | 0.7197 | 0.6970 | 1.0000 | 0.6916 | 0.9800 | 0.8200 | 0.8400 |
| `score-minmax+w=0.35+d=100` | 0.6100 | 0.5770 | 1.0000 | 0.6259 | 1.0000 | 0.7900 | 0.8600 |
| `score-minmax+w=0.35+d=500` | 0.6449 | 0.6260 | 1.0000 | 0.6307 | 1.0000 | 0.7900 | 0.8300 |
| `score-minmax+w=0.55+d=100` | 0.6853 | 0.6470 | 1.0000 | 0.6897 | 0.9800 | 0.8500 | 0.9000 |
| `score-minmax+w=0.55+d=500` | 0.7030 | 0.6740 | 1.0000 | 0.6842 | 0.9800 | 0.8400 | 0.8800 |
| `score-minmax+w=0.75+d=100` | 0.6791 | 0.6510 | 1.0000 | 0.6709 | 0.9500 | 0.8600 | 0.9000 |
| `score-minmax+w=0.75+d=500` | 0.6962 | 0.6680 | 1.0000 | 0.6838 | 0.9600 | 0.8600 | 0.9000 |
| `fusion-rrf+w=0.55+d=200+c=30` | 0.7058 | 0.6910 | 1.0000 | 0.6390 | 0.9800 | 0.8400 | 0.8800 |
| `fusion-rrf+w=0.55+d=500+c=30` | 0.7035 | 0.6900 | 1.0000 | 0.6402 | 0.9800 | 0.8400 | 0.8800 |
| `fusion-top1bonus+b=0.1+w=0.55+d=100+c=30` | 0.7048 | 0.6890 | 1.0000 | 0.6530 | 0.9800 | 0.8500 | 0.8900 |
| `fusion-top1bonus+b=0.25+w=0.55+d=100+c=30` | 0.7022 | 0.6870 | 1.0000 | 0.6527 | 0.9800 | 0.8500 | 0.8900 |
| `fusion-rrf+w=0.55+d=100+c=30` | 0.7064 | 0.6890 | 1.0000 | 0.6459 | 0.9800 | 0.8600 | 0.8900 |

## Worst baseline queries and target ranks within top500

| Query | nDCG10 | Lexical target rank | Dense target rank | Fused target rank |
|---|---|---|---|---|
| q-paraphrase-062: guessing the number of tokens an AI will generate for a prompt that can have wildly different response sizes | 0.3206 | None | 6 | 10 |
| q-paraphrase-032: maximizing income for power conversion tools and cells by using actual device behavior in Nordic power exchanges | 0.3443 | 147 | 1 | 9 |
| q-keyword-072: BL19 digital collection retrieval benchmark | 0.3543 | 1 | 22 | 2 |
| q-question-077: can standard graph neural networks perform link prediction on unknown knowledge graphs? | 0.4610 | 27 | 1 | 6 |
| q-known_item-047: van der Klis lorentz neural networks | 0.4646 | 1 | 1 | 1 |
| q-paraphrase-050: blocking fake info in external search results by checking how removing a page changes the answer | 0.4937 | None | 116 | None |
| q-paraphrase-096: a way to find relevant text chunks using a hierarchy of summaries to connect search terms and documents | 0.4958 | None | 259 | None |
| q-known_item-062: Flek physics constraint adversarial attacks | 0.5164 | 1 | 1 | 1 |
| q-known_item-031: Boyd clinical provenance categorization | 0.5214 | 1 | 2 | 1 |
| q-paraphrase-049: improving how ai follows complex rules by creating its own feedback without needing human labels | 0.5267 | None | 19 | 35 |
