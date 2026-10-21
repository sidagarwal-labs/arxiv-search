"""BM25: rank papers by how well their words match the query's words.

For each query word that appears in a paper, the paper earns points. Summed over the query's
words, the points are the paper's score; highest score = rank 1.

    points for one word = idf × tf_part

idf ("inverse document frequency"): rare words are worth more.
    idf = ln(1 + (N - df + 0.5) / (df + 0.5))
    N  = number of papers (23,304)
    df = number of papers containing the word
    "the" is in nearly every paper → idf ≈ 0.  "bm25" is in a few → idf ≈ 8.

tf_part ("term frequency", with two brakes):
    tf_part = tf × (k1 + 1) / (tf + k1 × (1 - b + b × length / avg_length))
    tf     = how often the word appears in this paper
    k1     = saturation: the 2nd mention counts less than the 1st, the 10th barely counts.
             Higher k1 → repeated words keep counting longer.
    b      = length penalty: long papers mention everything more, so their tf is scaled
             down. b = 0 → no penalty, b = 1 → full penalty.

Defaults k1 = 1.2, b = 0.75 are the standard ones (Lucene / Elasticsearch).

How it's stored (an "inverted index"): for every word, the list of papers that contain it
and how many times. Answering a query only touches the papers that contain a query word,
not all 23,304.
"""

from __future__ import annotations

from collections import Counter

import numpy as np

DEFAULT_K1 = 1.2
DEFAULT_B = 0.75


class BM25:
    def __init__(self, docs: list[list[str]], ids: list[str], k1: float = DEFAULT_K1, b: float = DEFAULT_B):
        """docs[i] is paper i's list of tokens; ids[i] is its arxiv_id."""
        self.ids = ids
        self.k1 = k1
        self.b = b
        self.doc_len = np.array([len(doc) for doc in docs], dtype=float)
        self.avg_len = self.doc_len.mean()

        # word -> (which papers, how many times in each)
        papers_with: dict[str, list[int]] = {}
        counts_in: dict[str, list[int]] = {}
        for i, doc in enumerate(docs):
            for word, tf in Counter(doc).items():
                papers_with.setdefault(word, []).append(i)
                counts_in.setdefault(word, []).append(tf)
        self.postings = {
            word: (np.array(papers_with[word]), np.array(counts_in[word], dtype=float))
            for word in papers_with
        }

        n = len(docs)
        self.idf = {
            word: float(np.log(1 + (n - len(papers) + 0.5) / (len(papers) + 0.5)))
            for word, (papers, _) in self.postings.items()
        }

    def scores(self, query_tokens: list[str]) -> np.ndarray:
        """BM25 score of every paper for this query (0 for papers sharing no word)."""
        scores = np.zeros(len(self.ids))
        length_norm = self.k1 * (1 - self.b + self.b * self.doc_len / self.avg_len)
        for word in query_tokens:  # a word typed twice counts twice
            if word not in self.postings:
                continue  # word appears in no paper
            papers, tf = self.postings[word]
            scores[papers] += self.idf[word] * tf * (self.k1 + 1) / (tf + length_norm[papers])
        return scores

    def search(self, query_tokens: list[str], k: int) -> list[str]:
        """arxiv_ids of the top k papers, best first. Papers scoring 0 are not returned."""
        scores = self.scores(query_tokens)
        # Stable sort: ties keep corpus order, so results are identical every run.
        order = np.argsort(-scores, kind="stable")[:k]
        return [self.ids[i] for i in order if scores[i] > 0]
