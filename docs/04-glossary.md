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
| **Corpus** | The set of documents we search over. Here, 23,304 papers in `corpus.jsonl`. |
| **JSONL** | A text file with one JSON object (one paper) per line. |
| **Seed** | A fixed starting number for random choices, so they come out the same every run. |
| **Stratified sample** | A random sample taken separately within each group (here, each category). |

## Search

| Term | Meaning |
|---|---|
| **Token** | A piece of a word that a model reads. Roughly 1 token ≈ ¾ of a word. |
| **BM25** | Classic keyword search. Scores a paper higher when it contains the query's words, especially rare words. |
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
| **Pooling** | Grading the combined top results from every system, so no system's finds go unjudged. |
| **LLM judge** | An LLM that grades how relevant a result is. We check it against human grades. |
| **Self-preference bias** | A model favoring text written by itself or its relatives. |
