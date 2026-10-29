"""Step 4d: an LLM judge grades how relevant each retrieved paper is (Decision 33).

Our first metrics only know one right answer per query: the paper the query was
written from. Other good papers count as misses. The judge fixes that by grading
query-paper pairs 0 (not relevant), 1 (partly) or 2 (highly relevant).

How it works:

1. Pool: for each query, take the top 10 from a few representative systems and
   remove duplicates (JUDGE_POOL_SYSTEMS in config.py).
2. Judge: one call per query with all its pooled papers, labeled P1, P2, ... in a
   shuffled order. The judge never sees which system found a paper, its rank, or
   which paper the query was written from.
3. Cache: every grade is saved with a key made from the judge model, the rubric
   version, the query text and the paper text. Anything already graded is never
   sent again, so reruns resume and new systems only pay for papers no one found
   before. Changing the query, paper, model or rubric changes the key.

Usage:
    python -m arxiv_search.evaluate.judge --judge gemma-31b --queries pilot
    python -m arxiv_search.evaluate.judge --judge gemma-31b --queries dev
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from arxiv_search import config
from arxiv_search.evaluate import judge_prompts
from arxiv_search.evaluate.make_queries import append_jsonl, load_jsonl

# Short fingerprint of the judge's wording, stored with every grade.
RUBRIC_VERSION = hashlib.sha256(Path(judge_prompts.__file__).read_bytes()).hexdigest()[:8]
MAX_AUTHORS_SHOWN = 10  # long author lists add tokens but not meaning
MAX_ATTEMPTS = 3  # a reply with missing/extra labels is asked again


# --- Answer shape ------------------------------------------------------------


class PaperGrade(BaseModel):
    paper: str  # "P1", "P2", ...
    reason: str
    grade: int


class Grades(BaseModel):
    grades: list[PaperGrade]


CallFn = Callable[[str], tuple[Grades, dict]]  # prompt -> (answer, usage info)


# --- Pieces ------------------------------------------------------------------


def paper_block(label: str, paper: dict) -> str:
    authors = paper["authors"][:MAX_AUTHORS_SHOWN]
    more = " et al." if len(paper["authors"]) > MAX_AUTHORS_SHOWN else ""
    return (f"[{label}] {paper['title']}\nAuthors: {', '.join(authors)}{more}\n"
            f"Abstract: {paper['abstract']}")


def pair_key(judge_key: str, query: str, paper: dict) -> str:
    """Same judge + rubric + query text + paper text -> same key -> reuse the grade."""
    model = config.JUDGES[judge_key]["model"]
    content = [model, RUBRIC_VERSION, query, paper["title"], paper["abstract"], paper["authors"]]
    return hashlib.sha256(json.dumps(content).encode()).hexdigest()[:20]


def pool(query_ids: list[str], systems: list[str] = config.JUDGE_POOL_SYSTEMS,
         depth: int = config.JUDGE_POOL_DEPTH, split: str = "dev") -> dict[str, list[str]]:
    """query_id -> unique papers in the top `depth` of any of `systems` (first-seen order)."""
    runs = []
    for name in systems:
        path = config.RESULTS_DIR / split / f"{name}.run.json"
        if not path.exists():
            raise FileNotFoundError(f"{path}: run this system first")
        runs.append(json.loads(path.read_text()))
    return {qid: list(dict.fromkeys(p for run in runs for p in run[qid][:depth])) for qid in query_ids}


def check_answer(answer: Grades, labels: list[str]) -> str | None:
    """Why the answer is unusable, or None if every label got exactly one valid grade."""
    given = [g.paper.strip().strip("[]") for g in answer.grades]
    if sorted(given) != sorted(labels):
        missing = sorted(set(labels) - set(given))
        extra = sorted(set(given) - set(labels))
        return f"labels don't match (missing {missing}, extra {extra}, {len(given)} given)"
    if any(g.grade not in (0, 1, 2) for g in answer.grades):
        return "grade outside 0-2"
    return None


def judge_query(judge_key: str, query: dict, papers: list[dict], call: CallFn) -> list[dict]:
    """Grade papers for one query in one call. Returns one cache row per paper."""
    order = papers[:]
    random.Random(f"{config.RANDOM_SEED}-{query['query_id']}").shuffle(order)  # same shuffle every run
    labels = [f"P{i}" for i in range(1, len(order) + 1)]
    prompt = judge_prompts.build_prompt(query["query"], [paper_block(l, p) for l, p in zip(labels, order)])

    start = time.perf_counter()
    for attempt in range(1, MAX_ATTEMPTS + 1):
        answer, usage = call(prompt)
        seconds = time.perf_counter() - start
        problem = check_answer(answer, labels)
        if problem is None:
            break
        print(f"  {query['query_id']}: {problem}; asking again ({attempt}/{MAX_ATTEMPTS})")
        prompt = judge_prompts.build_prompt(
            query["query"], [paper_block(l, p) for l, p in zip(labels, order)]
        ) + (f"\n\nYour previous response failed validation: {problem}.\n"
             f"Return exactly one grade for each of these labels: {', '.join(labels)}. "
             "Do not invent labels or omit any papers. Return the complete JSON again.")
    else:
        raise ValueError(f"{query['query_id']}: judge never returned a usable answer: {problem}")

    by_label = {g.paper.strip().strip("[]"): g for g in answer.grades}
    return [{
        "key": pair_key(judge_key, query["query"], paper), "judge": judge_key,
        "model": config.JUDGES[judge_key]["model"], "rubric_version": RUBRIC_VERSION,
        "query_id": query["query_id"], "arxiv_id": paper["arxiv_id"],
        "grade": by_label[label].grade, "reason": by_label[label].reason,
        "position": int(label[1:]), "batch_size": len(order),
        "call_seconds": round(seconds, 1), "attempts": attempt, "usage": usage,
    } for label, paper in zip(labels, order)]


# --- Backends ----------------------------------------------------------------


def gemini_call(model: str) -> CallFn:
    def call(prompt: str) -> tuple[Grades, dict]:
        from arxiv_search import llm  # imported here so tests never need an API key

        return llm.generate_json(model, prompt, Grades, judge_prompts.SYSTEM_INSTRUCTION, temperature=0)
    return call


def ollama_call(model: str) -> CallFn:
    """A model running locally in Ollama, forced to answer in the Grades JSON shape."""
    def call(prompt: str) -> tuple[Grades, dict]:
        import httpx

        response = httpx.post(f"{config.OLLAMA_URL}/api/chat", timeout=1800, json={
            "model": model, "stream": False, "format": Grades.model_json_schema(),
            "options": {"temperature": 0, "num_ctx": config.OLLAMA_CONTEXT_TOKENS},
            "messages": [{"role": "system", "content": judge_prompts.SYSTEM_INSTRUCTION},
                         {"role": "user", "content": prompt}],
        })
        response.raise_for_status()
        body = response.json()
        usage = {"model": model, "input_tokens": body.get("prompt_eval_count"),
                 "output_tokens": body.get("eval_count")}
        return Grades.model_validate_json(body["message"]["content"]), usage
    return call


def default_call(judge_key: str) -> CallFn:
    settings = config.JUDGES[judge_key]
    return {"gemini": gemini_call, "ollama": ollama_call}[settings["backend"]](settings["model"])


# --- Cache -------------------------------------------------------------------


def cache_path(judge_key: str) -> Path:
    return config.JUDGMENTS_DIR / f"{judge_key}.jsonl"


def load_judgments(judge_key: str) -> dict[str, dict]:
    """key -> cached row for this judge (any rubric version; keys keep them apart)."""
    return {row["key"]: row for row in load_jsonl(cache_path(judge_key))}


def grades_for(judge_key: str, pairs: dict[str, list[str]], queries: dict, papers: dict) -> dict:
    """query_id -> {arxiv_id: grade} for the pairs this judge has already graded."""
    cached = load_judgments(judge_key)
    out: dict[str, dict[str, int]] = {}
    for qid, ids in pairs.items():
        for arxiv_id in ids:
            row = cached.get(pair_key(judge_key, queries[qid]["query"], papers[arxiv_id]))
            if row is not None:
                out.setdefault(qid, {})[arxiv_id] = row["grade"]
    return out


def judge_pairs(judge_key: str, pairs: dict[str, list[str]], queries: dict, papers: dict,
                call: CallFn | None = None, max_calls: int | None = None) -> dict[str, int]:
    """Grade every (query, paper) pair not yet in the cache. Returns counts for reporting."""
    call = call or default_call(judge_key)
    path = cache_path(judge_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    cached = load_judgments(judge_key)
    counts = {"cached": 0, "judged": 0, "calls": 0}
    for qid, ids in pairs.items():
        query = queries[qid]
        todo = [papers[a] for a in ids if pair_key(judge_key, query["query"], papers[a]) not in cached]
        counts["cached"] += len(ids) - len(todo)
        batch_limit = (config.GEMMA_JUDGE_MAX_PAPERS_PER_CALL
                       if config.JUDGES[judge_key]["backend"] == "gemini"
                       else config.JUDGE_MAX_PAPERS_PER_CALL)
        for start in range(0, len(todo), batch_limit):
            if max_calls is not None and counts["calls"] >= max_calls:
                return counts
            batch = todo[start:start + batch_limit]
            rows = judge_query(judge_key, query, batch, call)
            for row in rows:
                append_jsonl(path, row)  # saved immediately: a crash loses at most one call
                cached[row["key"]] = row
            counts["judged"] += len(rows)
            counts["calls"] += 1
            print(f"  {qid}: {len(rows)} papers in {rows[0]['call_seconds']} s")
    return counts


# --- Command line ------------------------------------------------------------


def load_inputs() -> tuple[dict, dict, dict]:
    papers = {p["arxiv_id"]: p for p in load_jsonl(config.PROCESSED_DIR / "corpus.jsonl")}
    queries = {q["query_id"]: q for q in load_jsonl(config.EVAL_DIR / "queries.jsonl")}
    split = json.loads((config.EVAL_DIR / "split.json").read_text())
    return papers, queries, split


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--judge", choices=list(config.JUDGES), required=True)
    parser.add_argument("--queries", choices=["pilot", "dev"], required=True)
    parser.add_argument("--max-calls", type=int, default=None)
    args = parser.parse_args()

    papers, queries, split = load_inputs()
    if args.queries == "pilot":
        from arxiv_search.evaluate.judge_pilot import pilot_pairs
        pairs = pilot_pairs(queries, split)
    else:
        pairs = pool(split["dev"])
    print(f"{args.judge}: {sum(map(len, pairs.values()))} pairs over {len(pairs)} queries "
          f"(rubric {RUBRIC_VERSION})")
    counts = judge_pairs(args.judge, pairs, queries, papers, max_calls=args.max_calls)
    print(f"done: {counts['judged']} newly judged in {counts['calls']} calls, {counts['cached']} from cache")


if __name__ == "__main__":
    main()
