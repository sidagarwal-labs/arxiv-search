# Glossary

Short, plain definitions of every term used in this project, grouped by topic.

## Data

| Term | Meaning |
|---|---|
| **arXiv** | A free website where researchers post papers. Each paper has an ID like `2308.09419`. |
| **arXiv ID** | `YYMM.NNNNN`: year and month of first submission, then a counter. `2308.09419` = August 2023. |
| **Primary category** | The paper's main subject area. Listed first among its categories. |
| **Cross-list** | A paper that also appears in categories other than its main one. |
| **OAI-PMH** | A standard way for websites to share their catalog in bulk. We use it to download arXiv's paper information. |
| **Resumption token** | The "bookmark" arXiv gives us to fetch the next page of results. |
| **Harvest** | OAI-PMH's word for a bulk download. `harvest_date` in our files means "the date we downloaded". |
| **Corpus** | The set of documents we search over. Here, 23,304 papers in `corpus.jsonl`. |
| **JSONL** | A text file with one JSON object (one paper) per line. |
| **Seed** | A fixed starting number for random choices, so they come out the same every run. |
| **Stratified sample** | A random sample taken separately within each group (here, each category). |

## Search

| Term | Meaning |
|---|---|
| **Token** | A piece of a word that a model reads. Roughly 1 token ≈ ¾ of a word. |
| **BM25** | Classic keyword search. Scores a paper higher when it contains the query's words, especially rare words. |
| **Tokenize** | Split text into words. Our baseline: lowercase, then split on anything that isn't a letter or digit. |
| **Inverted index** | For every word, the list of papers containing it (like a book's index). Makes keyword search fast. |
| **tf / df** | Term frequency: how often a word is in one paper. Document frequency: how many papers contain it. |
| **idf** | Inverse document frequency: rare words (low df) are worth more points in BM25. |
| **k1, b** | BM25's two settings. k1: how fast repeated words stop counting. b: how much long papers are penalized. |
| **Stopwords** | Very common words ("the", "of", "for") that some systems drop before searching. |
| **Stemming** | Cutting words to a root so "models", "modeling" and "model" all match. |
| **Baseline** | The simplest system, which every other system is compared against. |
| **Title boost** | Making title words count more than abstract words; we do it by writing the title twice. |
| **Full grid (factorial design)** | Running every combination of settings, so each one's effect can be measured across all the others. |
| **Interaction** | When one technique's effect depends on another (e.g. stemming hurts alone but helps with authors). |
| **Tuning** | Trying several values of a setting (e.g. k1) and keeping the best, on dev queries only. |
| **Winner's curse** | The best of many systems on a small query set looks better than it really is, partly by luck. |
| **Query / passage prefix** | A fixed text some embedding models expect in front of queries or papers (e.g. E5's "query: "), because they were trained that way. |
| **Embedding / vector** | A list of numbers (e.g. 384 of them) that captures what a text means. Similar meanings give similar lists. |
| **Embedding model** | The model that turns text into vectors. Examples: MiniLM, BGE-small, E5-small, gemini-embedding-2. |
| **Dense search** | Search by comparing the query's vector to every paper's vector. |
| **Cosine similarity** | How closely two vectors point in the same direction: 1 = same meaning, 0 = unrelated. |
| **Normalize** | Scale a vector to length 1, so a simple dot product equals cosine similarity. |
| **Truncation** | When text is longer than a model's limit, the extra is cut off and ignored. |
| **Chunking** | Splitting a long document into smaller pieces that each get their own vector. |
| **Hybrid search** | Running BM25 and dense search, then merging their rankings. |
| **RRF (Reciprocal Rank Fusion)** | A simple way to merge rankings: each paper scores 1/(60 + its rank) in each list, and the scores are added. |
| **Reranker** | A slower, smarter model that reorders the top results from a first search. |
| **pgvector** | A Postgres add-on that stores vectors and finds the nearest ones. |

## RAG

| Term | Meaning |
|---|---|
| **LLM** | Large language model, e.g. Gemini. |
| **RAG** | Retrieval-Augmented Generation: find relevant papers first, then have the LLM answer using only them. |
| **Top-k** | The k best results (e.g. the top 5 papers sent to the LLM). |
| **Faithfulness** | Whether the LLM's answer is actually supported by the papers it was given. |

## Testing

| Term | Meaning |
|---|---|
| **Eval set** | Test queries with known right answers. |
| **Known-item query** | A search for one specific paper you already know exists. |
| **Recall@k** | Share of queries where the right paper appears in the top k. |
| **MRR (Mean Reciprocal Rank)** | Average of 1 ÷ (rank of the right paper). Rank 1 → 1.0, rank 2 → 0.5, not found → 0. |
| **nDCG@10** | Scores the top 10 using graded relevance (0/1/2), giving more credit to good papers ranked higher. |
| **DCG** | The sum behind nDCG: each result's grade ÷ log₂(rank + 1). nDCG = our DCG ÷ the best possible DCG. |
| **judged@10** | Share of the top 10 that the judge has graded. Low values mean nDCG is unreliable. |
| **Bootstrap** | Estimating uncertainty by redrawing the queries at random many times and seeing how much the average moves. |
| **95% confidence interval** | The range the true average likely falls in, e.g. `0.62 [0.57–0.67]`. |
| **Paired comparison** | Comparing two systems query by query on the same queries; this removes noise from some queries simply being harder. |
| **Pooling** | Grading the combined top results from every system, so no system's finds go unjudged. |
| **LLM judge** | An LLM that grades how relevant a result is. We check it against human grades. |
| **Self-preference bias** | A model favoring text written by itself or its relatives. |
| **Specificity** | Whether a test query targets one paper's idea (specific) or a general topic many papers answer (broad). |
| **Overlap** | Share of a query's words that also appear in its source paper. High overlap favors word-matching (BM25). |
| **Pilot** | A small trial run (a few LLM calls) to check prompt quality before the full run. |
| **Structured output** | Asking the LLM to reply in an exact JSON shape, so we never parse free text. |
| **Rate limit / quota** | How many calls the free tier allows per minute or per day. 429 = too many; 503 / 500 = Google busy or failing. |
| **Prompt version** | A fingerprint of `prompts.py` saved on every query, so we know which wording produced it. |
| **Dev / test split** | Dev queries are for tuning; test queries are only for the final score, so tuning can't inflate it. |
