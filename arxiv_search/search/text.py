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

# One or more letters/digits in a row. [^\W_] = "a word character, but not underscore",
# which covers accented letters (e.g. "é") too.
WORD = re.compile(r"[^\W_]+")


def tokenize(text: str) -> list[str]:
    return WORD.findall(text.lower())


def paper_text(paper: dict) -> str:
    """The text we search over for each paper: title, then abstract."""
    return f"{paper['title']} {paper['abstract']}"
