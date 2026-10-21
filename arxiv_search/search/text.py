"""How text is split into words ("tokens") before word-matching search.

The baseline does the least that is still fair (Decision 27):
  1. lowercase everything                 "Retrieval" -> "retrieval"
  2. split on anything that isn't a letter or digit
         "state-of-the-art RAG, SO(3)."  -> ["state", "of", "the", "art", "rag", "so", "3"]

No stopword removal and no stemming: those are separate experiments, so we can measure
what each one adds.
"""

from __future__ import annotations

import re

import Stemmer  # PyStemmer: the Snowball stemmers, written in C

# One or more letters/digits in a row. [^\W_] = "a word character, but not underscore",
# which covers accented letters (e.g. "é") too.
WORD = re.compile(r"[^\W_]+")


# Lucene / Elasticsearch's default English stopword list (Decision 28): very common words
# that carry almost no meaning. Note "no" and "not" are on it.
STOPWORDS = frozenset(
    "a an and are as at be but by for if in into is it no not of on or such "
    "that the their then there these they this to was will with".split()
)


# Snowball English stemmer (Decision 28), the one Lucene / Elasticsearch use. It cuts words
# to a root so different forms match: "recommendations", "recommending" -> "recommend";
# "retrieval", "retrieve" -> "retriev". Roots don't have to be real words.
STEMMER = Stemmer.Stemmer("english")


def tokenize(
    text: str, drop_stopwords: bool = False, stem: bool = False, add_stems: bool = False
) -> list[str]:
    """add_stems keeps each exact word AND adds its stem marked with "~" ("models" ->
    "models", "~model"). An exact match then earns points twice, a near match once."""
    words = WORD.findall(text.lower())
    if drop_stopwords:  # before stemming, so the list matches the words as written
        words = [w for w in words if w not in STOPWORDS]
    if stem:
        words = STEMMER.stemWords(words)
    if add_stems:
        words = words + ["~" + s for s in STEMMER.stemWords(words)]
    return words


def paper_text(paper: dict, authors: bool = False, title_repeats: int = 1) -> str:
    """The text we search over for each paper: title, then abstract.

    authors=True appends the author names, so "Tannenbaum conversation context" can match.
    title_repeats=2 writes the title twice: a "title boost", since title words then count
    twice in BM25 (the title is the paper's most concentrated description).
    """
    parts = [paper["title"]] * title_repeats + [paper["abstract"]]
    if authors:
        parts.append(" ".join(paper["authors"]))
    return " ".join(parts)
