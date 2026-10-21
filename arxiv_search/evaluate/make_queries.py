"""Step 4 (test): generate the evaluation query set with an LLM.

Plan (Decisions 14, 16, 22, 23):

    400 query "slots" = 4 types x 100, spread evenly over the 3 categories
      keyword    100  (50 specific, 50 broad)
      question   100  (50 specific, 50 broad)
      paraphrase 100  (all specific)
      known_item 100  (all specific)

    each slot gets its own random paper from the corpus (fixed seed)
    -> 4 papers per API call, one of each type   (100 calls)
    -> every query is checked automatically       (check_query)
    -> failures are retried, then given a new paper
    -> data/eval/queries.jsonl                    (one row per accepted query)

Every call's raw output is appended to data/eval/attempts.jsonl, so rerunning after a
crash or the daily limit skips work already done.

Usage:
    python -m arxiv_search.evaluate.make_queries --max-calls 3    # pilot: 12 queries
    python -m arxiv_search.evaluate.make_queries                  # everything
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from arxiv_search import config
from arxiv_search.evaluate import prompts

QUERY_TYPES = ("keyword", "question", "paraphrase", "known_item")
TYPES_WITH_BROAD = ("keyword", "question")

# Allowed length in words, per type (matches the prompt).
WORD_LIMITS = {"keyword": (2, 6), "question": (6, 25), "paraphrase": (8, 30), "known_item": (3, 12)}
COPY_RUN_WORDS = 4  # sharing 4+ consecutive words with the title/abstract counts as copying
TITLE_RESHUFFLE_SHARE = 0.8  # 80%+ of a query's content words come from the title -> reshuffled title
TITLE_RESHUFFLE_MIN_WORDS = 3  # ...and at least this many of them (so "graph learning" isn't flagged)
PAPER_SELF_REFERENCE = re.compile(r"\b(this|the present) (paper|study|work|article)\b|\bthe authors\b")
PARAPHRASE_MAX_OVERLAP = 0.5  # at most half of a paraphrase's content words may come from the paper
MAX_ATTEMPTS_PER_PAPER = 2  # then the slot gets a different paper

# Common words ignored when measuring overlap: they say nothing about copying.
STOPWORDS = set(
    "a an and are as at be by can do does for from has have how i in is it its of on or "
    "that the their this to use used using via what when which with without".split()
)

# Short fingerprint of prompts.py. Saved on every query so we can tell which wording made it.
PROMPT_VERSION = hashlib.sha256(Path(prompts.__file__).read_bytes()).hexdigest()[:8]


# --- Response shape we force the model to return ---------------------------


class GeneratedQuery(BaseModel):
    arxiv_id: str
    query: str


class GeneratedBatch(BaseModel):
    queries: list[GeneratedQuery]


# --- 1. Plan the slots -------------------------------------------------------


def plan_slots() -> list[dict]:
    """The 400 (type, specificity, category) combinations we need, in call order.

    Slot i of each type uses category i % 3 (so categories rotate evenly) and, for
    keyword/question, specificity alternates (even i = specific, odd i = broad).
    Slots are ordered so that each group of 4 consecutive slots has one of each type.
    """
    slots = []
    for i in range(config.EVAL_QUERIES_PER_TYPE):
        for query_type in QUERY_TYPES:
            broad = query_type in TYPES_WITH_BROAD and i % 2 == 1
            slots.append({
                "slot_id": f"{query_type}-{i:03d}",
                "query_type": query_type,
                "specificity": "broad" if broad else "specific",
                "category": config.CATEGORIES[i % len(config.CATEGORIES)],
            })
    return slots


# --- 2. Pick papers -----------------------------------------------------------


def shuffled_papers_by_category(corpus: list[dict], seed: int) -> dict[str, list[str]]:
    """Each category's paper IDs in a fixed random order. Slots take papers from the front;
    the rest are reserves for slots whose paper keeps failing the checks."""
    rng = random.Random(seed)
    by_category: dict[str, list[str]] = {}
    for doc in sorted(corpus, key=lambda d: d["arxiv_id"]):
        by_category.setdefault(doc["primary_category"], []).append(doc["arxiv_id"])
    for ids in by_category.values():
        rng.shuffle(ids)
    return by_category


# --- 3. Automatic checks ------------------------------------------------------


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def shares_run(query_words: list[str], source_words: list[str], n: int) -> bool:
    """True if `n` consecutive query words also appear consecutively in the source."""
    source_runs = {tuple(source_words[i : i + n]) for i in range(len(source_words) - n + 1)}
    return any(tuple(query_words[i : i + n]) in source_runs for i in range(len(query_words) - n + 1))


def paper_words_in(query: str, paper: dict, fields: tuple[str, ...] = ("title", "abstract")) -> list[str]:
    """The query's content words that also appear in the paper's text."""
    paper_words = set(words(" ".join(paper[field] for field in fields)))
    return [w for w in words(query) if w not in STOPWORDS and w in paper_words]


def overlap(query: str, paper: dict, fields: tuple[str, ...] = ("title", "abstract")) -> float:
    """Share of the query's content words that also appear in the paper's text.

    0.0 = entirely new wording, 1.0 = every content word comes from the paper.
    Saved for every query: it tells us how much a query favors word-matching (BM25).
    """
    content = [w for w in words(query) if w not in STOPWORDS]
    if not content:
        return 0.0
    return len(paper_words_in(query, paper, fields)) / len(content)


def reshuffles_title(query: str, paper: dict) -> bool:
    """True if the query is mostly the title's own words, e.g. "post editing llm text personal
    style" for "Post-Editing LLM-Generated Text for Personal Style"."""
    title_words = set(words(paper["title"]))
    from_title = [w for w in words(query) if w not in STOPWORDS and w in title_words]
    return (
        len(from_title) >= TITLE_RESHUFFLE_MIN_WORDS
        and overlap(query, paper, fields=("title",)) >= TITLE_RESHUFFLE_SHARE
    )


def surnames(paper: dict) -> set[str]:
    return {words(name)[-1] for name in paper["authors"] if words(name)}


def check_query(query: str, slot: dict, paper: dict) -> list[str]:
    """Return a list of problems; an empty list means the query is accepted."""
    problems = []
    query_words = words(query)
    low, high = WORD_LIMITS[slot["query_type"]]
    if not low <= len(query_words) <= high:
        problems.append(f"length {len(query_words)} words, expected {low}-{high}")
    if slot["query_type"] == "question" and not query.strip().endswith("?"):
        problems.append("question does not end with '?'")
    if shares_run(query_words, words(paper["title"]), COPY_RUN_WORDS):
        problems.append(f"copies {COPY_RUN_WORDS}+ consecutive words from the title")
    if shares_run(query_words, words(paper["abstract"]), COPY_RUN_WORDS):
        problems.append(f"copies {COPY_RUN_WORDS}+ consecutive words from the abstract")
    # Known-item searchers often do remember title words, so they're allowed to reuse them.
    if slot["query_type"] != "known_item" and reshuffles_title(query, paper):
        problems.append("mostly the title's own words, rearranged")
    if PAPER_SELF_REFERENCE.search(query.lower()):
        problems.append("refers to 'this paper' / 'the authors'")
    if slot["query_type"] == "paraphrase" and overlap(query, paper) > PARAPHRASE_MAX_OVERLAP:
        reused = ", ".join(dict.fromkeys(paper_words_in(query, paper)))
        problems.append(
            f"paraphrase reuses too many paper words ({overlap(query, paper):.0%}): {reused}"
        )
    if slot["query_type"] == "known_item" and not surnames(paper) & set(query_words):
        problems.append("known_item query names no author")
    return problems


# --- 4. Generation loop -------------------------------------------------------


GenerateFn = Callable[[str], GeneratedBatch]


def default_generate(prompt: str) -> GeneratedBatch:
    from arxiv_search import llm  # imported here so tests never need an API key

    parsed, _usage = llm.generate_json(
        config.QUERY_WRITER_MODEL, prompt, GeneratedBatch, prompts.SYSTEM_INSTRUCTION
    )
    return parsed


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def append_jsonl(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def generate_queries(
    corpus: list[dict],
    out_dir: Path,
    generate: GenerateFn = default_generate,
    max_calls: int = config.EVAL_MAX_CALLS_PER_RUN,
) -> list[dict]:
    """Fill every slot with an accepted query, resuming from files in out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    queries_path, attempts_path = out_dir / "queries.jsonl", out_dir / "attempts.jsonl"
    papers = {doc["arxiv_id"]: doc for doc in corpus}
    queues = shuffled_papers_by_category(corpus, config.RANDOM_SEED)

    accepted = {row["slot_id"]: row for row in load_jsonl(queries_path)}
    if any(row["prompt_version"] != PROMPT_VERSION for row in accepted.values()):
        raise SystemExit(
            f"{queries_path} was made with a different prompt. Delete {out_dir} to start over."
        )

    # Replay history: which paper each slot has, how often it failed, and why it last failed.
    slots = plan_slots()
    used: set[str] = set()
    paper_of: dict[str, str] = {}
    failures: dict[str, int] = {}
    last_problems: dict[str, list[str]] = {}
    for attempt in load_jsonl(attempts_path):
        sid = attempt["slot_id"]
        if paper_of.get(sid) != attempt["arxiv_id"]:  # slot moved to a new paper: count afresh
            failures[sid] = 0
        paper_of[sid] = attempt["arxiv_id"]
        used.add(attempt["arxiv_id"])
        last_problems[sid] = attempt["problems"]
        if not attempt["accepted"]:
            failures[sid] += 1

    def next_paper(category: str) -> str:
        while (candidate := queues[category].pop(0)) in used:
            pass
        used.add(candidate)
        return candidate

    calls = 0
    while pending := [s for s in slots if s["slot_id"] not in accepted]:
        if calls >= max_calls:
            print(f"Reached the limit of {max_calls} calls for this run.")
            break
        batch = []
        for slot in pending[: config.EVAL_PAPERS_PER_CALL]:
            sid = slot["slot_id"]
            if sid not in paper_of or failures.get(sid, 0) >= MAX_ATTEMPTS_PER_PAPER:
                paper_of[sid], failures[sid], last_problems[sid] = next_paper(slot["category"]), 0, []
            batch.append((slot, papers[paper_of[sid]], last_problems.get(sid)))

        result = generate(prompts.build_prompt(batch))
        calls += 1
        returned = {q.arxiv_id: q.query.strip() for q in result.queries}

        for slot, paper, _feedback in batch:
            sid, query = slot["slot_id"], returned.get(paper["arxiv_id"], "")
            problems = check_query(query, slot, paper) if query else ["model returned no query"]
            append_jsonl(attempts_path, {
                "slot_id": sid, "arxiv_id": paper["arxiv_id"], "query": query,
                "accepted": not problems, "problems": problems,
            })
            if problems:
                failures[sid] = failures.get(sid, 0) + 1
                last_problems[sid] = problems
                continue
            row = {
                "query_id": f"q-{sid}",
                "slot_id": sid,
                "query": query,
                "query_type": slot["query_type"],
                "specificity": slot["specificity"],
                "category": slot["category"],
                "source_arxiv_id": paper["arxiv_id"],
                "source_title": paper["title"],
                "word_count": len(words(query)),
                "overlap": round(overlap(query, paper), 3),
                "model": config.QUERY_WRITER_MODEL,
                "prompt_version": PROMPT_VERSION,
            }
            append_jsonl(queries_path, row)
            accepted[sid] = row
        print(f"call {calls}: {len(accepted)}/{len(slots)} queries accepted")

    return [accepted[s["slot_id"]] for s in slots if s["slot_id"] in accepted]


def write_labels(queries: list[dict], out_dir: Path) -> None:
    """labels.json in the shape metrics.py expects: {query_id: {source paper: grade 2}}."""
    labels = {q["query_id"]: {q["source_arxiv_id"]: 2} for q in queries}
    (out_dir / "labels.json").write_text(json.dumps(labels, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the evaluation query set.")
    parser.add_argument("--max-calls", type=int, default=config.EVAL_MAX_CALLS_PER_RUN,
                        help="Stop after this many API calls (use 3 for a pilot).")
    args = parser.parse_args()

    from arxiv_search import llm
    from google.genai import errors

    corpus = load_jsonl(config.PROCESSED_DIR / "corpus.jsonl")
    try:
        queries = generate_queries(corpus, config.EVAL_DIR, max_calls=args.max_calls)
    except (llm.DailyLimitReached, errors.APIError) as error:  # progress is already saved
        print(f"Stopped: {error}\nRerun the same command later to resume.")
        queries = load_jsonl(config.EVAL_DIR / "queries.jsonl")
    write_labels(queries, config.EVAL_DIR)
    print(f"{len(queries)} queries in {config.EVAL_DIR / 'queries.jsonl'}")


if __name__ == "__main__":
    main()
