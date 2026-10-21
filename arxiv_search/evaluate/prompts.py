"""The exact text we send to the query-writing LLM. Kept separate so it can be read and
reviewed on its own, like a questionnaire.

One API call covers 4 papers. Each paper is assigned one query TYPE and one SPECIFICITY,
and the model writes one query per paper.
"""

# Shared rules, sent once per call as the "system instruction".
SYSTEM_INSTRUCTION = """\
You write realistic search queries for evaluating an academic search engine over arXiv papers
in information retrieval, NLP and machine learning.

For each paper you are given, imagine a real researcher typing into a search box. Write ONE query
of the requested TYPE and SPECIFICITY.

Rules for every query:
- Sound like a person searching, not like the paper. Never copy the title or a phrase from the
  abstract, and don't just rearrange or trim the title's words; a real user hasn't read the
  paper yet.
- Do not mention arXiv, "this paper", "this study", "the authors", or the arXiv ID.
- Plain text only: no quotes, no boolean operators, no markdown.

SPECIFICITY
- specific: the user is looking for the particular idea, method or finding of THIS paper.
  Only a handful of papers should match it well.
- broad: the user has a general topic need that this paper is one good answer to.
  Many papers could satisfy it. Do not mention the paper's specific method or contribution.

TYPES
- keyword: 2 to 6 words, the way people type into a search box. No full sentences.
- question: a natural-language question of 6 to 25 words, ending with "?". Use at most one
  technical term or method name from the paper; say the rest in your own words.
- paraphrase: 8 to 30 words describing what the user is looking for, in everyday wording,
  phrased as a search rather than a summary. At most HALF of your content words may appear
  anywhere in the title or abstract, and that includes ordinary words like "training",
  "game", "model" or "loss", not just technical terms. Describe what the paper does
  from the outside, the way someone who hasn't read it would.
  Example, for "Superhuman AI for Generals.io Using Self-Play Reinforcement Learning":
    BAD:  "training a strategy game bot to play like a pro using only win or loss signals"
          (training, strategy, game, play, only, win, loss all come from the paper: 64%)
    GOOD: "teaching a computer opponent to beat top human players in an online conquest
          game just by playing against itself" (only beat, human, game: 21%)
  Avoid the paper's method names and acronyms. Don't start with "This paper", "This system"
  or "This approach".
- known_item: the user remembers this paper vaguely and wants to find it again. 3 to 12 words:
  the surname of the first or last author plus a few words about the topic, e.g.
  "smith contrastive pretraining retrieval". Use the surname only, not the first name.
"""


def paper_block(slot: dict, paper: dict, feedback: list[str] | None = None) -> str:
    """One paper as shown to the model, with its assigned task on top.

    `feedback` lists why the previous query for this paper was rejected, so a retry
    doesn't repeat the same mistake.
    """
    authors = paper["authors"]
    # Long collaborations: show first and last authors only, which is all known_item needs.
    if len(authors) > 6:
        authors = authors[:3] + ["..."] + authors[-2:]
    retry_note = (
        f"NOTE: your previous query for this paper was rejected ({'; '.join(feedback)}). "
        "Write a different one that fixes this.\n"
        if feedback
        else ""
    )
    return (
        f"PAPER {paper['arxiv_id']}\n"
        f"TASK: type={slot['query_type']}, specificity={slot['specificity']}\n"
        f"{retry_note}"
        f"Title: {paper['title']}\n"
        f"Authors: {', '.join(authors)}\n"
        f"Abstract: {paper['abstract']}\n"
    )


def build_prompt(batch: list[tuple[dict, dict, list[str] | None]]) -> str:
    """The user message for one call: every (slot, paper, feedback) in the batch."""
    blocks = "\n".join(paper_block(slot, paper, feedback) for slot, paper, feedback in batch)
    return (
        f"Write one query for each of the {len(batch)} papers below. Treat each paper "
        f"independently and follow its TASK line.\n\n{blocks}"
    )
