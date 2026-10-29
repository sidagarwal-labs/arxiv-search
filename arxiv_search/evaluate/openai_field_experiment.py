"""Candidate-only OpenAI-large field ablation; dry-run unless --run is supplied."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np
from dotenv import load_dotenv

from arxiv_search import config
from arxiv_search.evaluate import fusion_experiment as fusion, judge, openai_full as full
from arxiv_search.evaluate import results_catalog as catalog
from arxiv_search.evaluate.cross_encoder_experiment import freeze
from arxiv_search.evaluate.field_score_experiment import changes, validate_scope
from arxiv_search.evaluate.rank_score_experiment import screen
from arxiv_search.evaluate.score_fusion_experiment import cached_vectors, summarize
from arxiv_search.search.rank_score import rescore_shortlist
from arxiv_search.search.rerank import rerank_prefix
from arxiv_search.search.text import paper_text

OUT = config.RESULTS_DIR / "openai-field-dev"
CACHE = config.EMBEDDINGS_DIR / "openai-candidate-fields"
BASELINE = "fusion-shortlist+a=1+d=500"
LOCAL_CAP = 300_000_000  # $0.30; shared full-run $1.25 lifetime cap remains unchanged.


def plan() -> dict:
    return {
        "hypothesis": "Separate OpenAI-large title/abstract representations improve candidate "
                      "ordering compared with same-model concatenated document embeddings.",
        "baseline": BASELINE, "model": full.MODEL, "dimensions": full.DIMENSIONS,
        "settings": {
            f"oai-field+text={recipe}+d={depth}": {
                "title_weight": weight, "depth": depth,
            }
            for depth in (10, 100)
            for recipe, weight in (("concat", None), ("title25", .25),
                                   ("title50", .5), ("title75", .75))
        },
        "scoring": "Pure cosine for concat; t*cos(query,title)+(1-t)*cos(query,abstract) "
                   "for fields. Unit3072vectors, no baseline blending, stable baseline ties.",
        "candidates": "Exactly frozen Decision36 top100 per dev query; no retrieval/source injection.",
        "scope": "100 dev queries only; body=abstract, no full text; no held-out test.",
        "controls": "Same OpenAI model/dimensions/query vectors for concat and separate; "
                    "concat document vectors and dev query vectors reused from full-run cache.",
        "labels": "Frozen shared snapshot including human overrides; no judge API calls. "
                  "Incomplete graded comparisons withheld; source comparisons remain valid.",
        "budget": {"maximum_new_accounted_usd": LOCAL_CAP / 1e9,
                   "shared_lifetime_usd": full.CAP / 1e9,
                   "ledger": "data/openai/embedding-full-large.sqlite3",
                   "no_retries": True, "unknown_attempts_keep_reservations": True},
        "primary_metric": "ndcg@10", "automatic_promotion": False,
        "interpretation": "Candidate reranking, not field-specific full-corpus retrieval. "
                          "Exploratory dev results conditional on current labels.",
    }


def accounted_nanodollars(ledger: full.Ledger) -> int:
    with ledger.connect() as db:
        return db.execute("SELECT COALESCE(SUM(nanodollars),0) FROM calls").fetchone()[0]


class CappedLedger(full.Ledger):
    """Reuse the shared durable reservations and retain the approved task ceiling."""

    def __init__(self, path: Path, origin: int):
        super().__init__(path)
        self.origin = origin

    def reserve(self, tokens: int) -> str:
        if accounted_nanodollars(self) - self.origin + tokens * full.PRICE > LOCAL_CAP:
            raise full.BudgetExceeded("$0.30 field experiment cap reached; no request sent")
        return super().reserve(tokens)


def field_scores(query: np.ndarray, concat: np.ndarray, title: np.ndarray,
                 abstract: np.ndarray, weight: float | None) -> np.ndarray:
    if weight is not None and (not np.isfinite(weight) or not 0 <= weight <= 1):
        raise ValueError("Invalid title weight")
    if (query.ndim != 1 or concat.ndim != 2 or concat.shape != title.shape
            or concat.shape != abstract.shape or concat.shape[1] != query.shape[0]
            or any(not np.isfinite(a).all() for a in (query, concat, title, abstract))):
        raise ValueError("Expected finite aligned field/query vectors")
    return concat @ query if weight is None else (
        weight * (title @ query) + (1 - weight) * (abstract @ query))


def build_runs(base: dict, raw: dict, settings: dict) -> dict:
    if set(base) != set(raw):
        raise ValueError("Candidate and score query scopes differ")
    runs = {BASELINE: base}
    for name, options in settings.items():
        weight = options["title_weight"]
        runs[name] = {}
        for q, ids in base.items():
            fields = raw[q]
            if fields["candidate_ids"] != ids:
                raise ValueError("Field scores are not aligned with frozen candidates")
            values = np.asarray(fields["concat"] if weight is None else
                                weight * np.asarray(fields["title"])
                                + (1 - weight) * np.asarray(fields["abstract"]))
            if values.shape != (len(ids),) or not np.isfinite(values).all():
                raise ValueError("Invalid candidate field scores")
            runs[name][q] = rerank_prefix(ids, dict(zip(ids, values.tolist())), options["depth"])
    return runs


def publish(out: Path, runs: dict, snapshot: dict, papers: dict, queries: dict,
            qids: list[str], experiment: dict, execution: dict) -> dict:
    results = catalog.score_catalog(
        {n: {"run": r, "paths": [], "metadata": {}} for n, r in runs.items()},
        snapshot, papers, queries, qids, BASELINE)
    rows = {n: r["per_query"] for n, r in results.items()}
    summary = summarize(rows, BASELINE)
    same_model = {}
    for depth in sorted({v["depth"] for v in experiment["settings"].values()}):
        control = next(n for n, options in experiment["settings"].items()
                       if options["depth"] == depth and options["title_weight"] is None)
        same_model[str(depth)] = summarize(
            {n: values for n, values in rows.items()
             if n in experiment["settings"] and experiment["settings"][n]["depth"] == depth},
            control)
    missing = {q: sorted({p for r in runs.values() for p in r[q][:10]}
                         - set(snapshot["labels"][q])) for q in qids}
    checks = {
        n: screen(results[n], results[BASELINE], run, runs[BASELINE], queries, snapshot["labels"])
        for n, run in runs.items() if n != BASELINE}
    report = {
        "baseline": BASELINE, "model": full.MODEL, "dimensions": full.DIMENSIONS,
        "summary": summary, "systems": results, "screens": checks,
        "same_model_concat_comparisons": same_model,
        "changes": {n: changes(r, runs[BASELINE], queries) for n, r in runs.items()},
        "missing": missing, "missing_pairs": sum(map(len, missing.values())),
        "execution": execution, "judge_api_calls": 0, "promoted": False,
        "run_fingerprints": {n: fusion.fingerprint(r) for n, r in runs.items()},
        "label_snapshot_sha256": fusion.fingerprint(snapshot),
    }
    cases = {}
    for n, result in results.items():
        if n == BASELINE:
            continue
        paired = summary[n]["all"]["ndcg@10"]["paired_vs_working"]
        source = summary[n]["all"]["source_mrr@10"]["paired_vs_working"]
        deltas = (paired or source)["per_query_difference"]
        selected = set(sorted(deltas, key=lambda q: (deltas[q], q))[:5])
        selected.update(sorted(deltas, key=lambda q: (-deltas[q], q))[:5])
        selected.update(checks[n]["lost_source_top10"])
        selected.update(checks[n]["gained_source_top10"])
        selected.update(checks[n]["known_item_rank_regressions"])
        for q in sorted(selected):
            ids = list(dict.fromkeys(runs[BASELINE][q][:10] + runs[n][q][:10]
                                     + [queries[q]["source_arxiv_id"]]))
            cases.setdefault(q, {"query": queries[q], "systems": {}})["systems"][n] = [
                {"arxiv_id": p, "title": papers[p]["title"], "abstract": papers[p]["abstract"],
                 "grade": snapshot["labels"][q].get(p),
                 "baseline_rank": runs[BASELINE][q].index(p) + 1 if p in runs[BASELINE][q] else None,
                 "candidate_rank": runs[n][q].index(p) + 1 if p in runs[n][q] else None}
                for p in ids]
    fusion._write_json(out / "cases.json", cases)
    fusion._write_json(out / "report.json", report)
    cached_only = experiment.get("automatic_embedding_calls") is False
    title = ("OpenAI field-aware hybrid (cached follow-up)" if cached_only
             else "OpenAI-large candidate title/abstract experiment")
    lines = [
        f"# {title}", "",
        experiment.get("setting_description",
                       "Eight prespecified settings: concatenated control and separate25/50/75% title "
                       "at baseline prefixes10/100. ") +
        f"Scoring recipe: {experiment['scoring']} "
        "Exactly the same OpenAI-large model,3072 dimensions and cached query vectors. "
        "Body means abstract. Candidate-only; no new full-corpus retrieval. "
        "The approved Decision36 baseline remains unchanged.", "",
        f"Embedding workload/cost: `{json.dumps(execution, sort_keys=True)}`", "",
        f"Unjudged new top10 pairs: **{report['missing_pairs']}**. No judging calls. "
        "Incomplete nDCG/P10 are diagnostic, not comparable winner evidence; graded paired "
        "intervals withheld. Adding labels can revise ideal DCG. Source metrics remain complete.",
        "", "| System | nDCG10 | P10 | Judged10 | Source MRR10 | R10 | R20 | Coverage |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for n, r in results.items():
        values = [r["all"][f]["mean"] for f in (
            "ndcg@10", "precision@10", "judged@10", "source_mrr@10",
            "source_recall@10", "source_recall@20")]
        lines.append(f"| `{n}` | " + " | ".join(
            "undefined" if v is None else f"{v:.4f}" for v in values)
            + f" | {'complete' if r['top10_fully_judged'] else 'PROVISIONAL'} |")
    lines += ["", "## Paired nDCG comparisons", "",
              "| Setting | Versus baseline delta [95% CI] | Versus same-depth concat [95% CI] |",
              "|---|---|---|"]
    def delta(value: dict | None) -> str:
        return ("withheld" if value is None else
                f"{value['difference']:+.4f} [{value['ci95'][0]:+.4f},{value['ci95'][1]:+.4f}]")
    for n, options in experiment["settings"].items():
        lines.append(
            f"| `{n}` | {delta(summary[n]['all']['ndcg@10']['paired_vs_working'])} | "
            f"{delta(same_model[str(options['depth'])][n]['all']['ndcg@10']['paired_vs_working'])} |")
    lines += ["", "## Segments", "",
              "| Setting | Segment | nDCG10 (diagnostic if incomplete) | Source MRR10 | R10 | R20 |",
              "|---|---|---|---|---|---|"]
    for n in runs:
        for kind in catalog.QUERY_TYPES:
            group = summary[n][kind]
            lines.append(f"| `{n}` | {kind} | " + " | ".join(
                "undefined" if group[f]["mean"] is None else f"{group[f]['mean']:.4f}"
                for f in ("ndcg@10", "source_mrr@10", "source_recall@10", "source_recall@20")) + " |")
    lines += [
        "", "## Reproducibility and cautions", "",
        ("- Cached scores only; no embedding/judging API execution path." if cached_only
         else "- Dry-run default; --run explicitly enables missing embeddings, not judging."),
        "- Parent embeddings use the shared $1.25 lifetime ledger plus $0.30 task ceiling. "
        "No automatic retries; unknown outcomes retain reservations.",
        "- Reported cost is local accounting at the stored $0.13/M token price, "
        "not a guarantee about provider billing/free credits.",
        "- Input/label hashes and plan frozen; cached document vectors bind exact text, "
        "model and dimensions. Query/concat caches are read-only; missing cache aborts.",
        ("- `../openai-field-dev/raw-field-scores.json`: frozen parent cosine signals; "
         "`cases.json`: wins/losses." if cached_only else
         "- `raw-field-scores.json`: aligned cosine signals; `cases.json`: wins/losses."),
        "- `report.json`: screening, paired source intervals and same-model controls.",
        "- Held-out300 untouched; human overrides preserved. Exploratory dev comparisons "
        "are not corrected for repeated selection or multiple testing.",
    ]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    experiment = plan()
    freeze(OUT / "preregistration.json", experiment)
    papers, queries, split = judge.load_inputs()
    qids = sorted(split["dev"])
    base_path = config.RESULTS_DIR / "shortlist-score-dev" / f"{BASELINE}.run.json"
    base = json.loads(base_path.read_text(encoding="utf-8"))
    validate_scope(base, qids, split["test"], papers)
    if len(qids) != 100:
        raise ValueError("Expected100 dev queries")
    inputs_path = config.RESULTS_DIR / "score-fusion-dev" / "input-scores.json"
    inputs = json.loads(inputs_path.read_text(encoding="utf-8"))
    for q in qids:
        if rescore_shortlist(dict(inputs[q]["lexical"]), dict(inputs[q]["semantic"]),
                             score_fraction=1, depth=500, k=100) != base[q]:
            raise ValueError("Frozen baseline does not reproduce")
    ids = sorted({p for ranked in base.values() for p in ranked})
    field_texts = {f: [papers[p][f] for p in ids] for f in ("title", "abstract")}
    query_texts = [queries[q]["query"] for q in qids]
    all_texts = [paper_text(p) for p in papers.values()]
    parent = json.loads((config.RESULTS_DIR / "score-fusion-dev" / "report.json").read_text())
    if (full.fingerprint(all_texts) != parent["provenance"]["paper_text_sha256"]
            or full.fingerprint(query_texts) != parent["provenance"]["query_text_sha256"]):
        raise ValueError("Corpus/query text differs from frozen parent")
    snapshot_path, snapshot_raw, snapshot, _ = catalog.load_snapshot(config.RESULTS_DIR)
    if not snapshot["complete"]:
        raise ValueError("Expected complete frozen parent labels")
    freeze(OUT / "input-provenance.json", {
        "baseline_bytes_sha256": hashlib.sha256(base_path.read_bytes()).hexdigest(),
        "retrieval_bytes_sha256": hashlib.sha256(inputs_path.read_bytes()).hexdigest(),
        "labels_bytes_sha256": hashlib.sha256(snapshot_raw).hexdigest(),
        "label_snapshot": snapshot_path.relative_to(config.RESULTS_DIR).as_posix(),
        "candidate_ids": ids, "query_ids": qids, "query_sha256": full.fingerprint(query_texts),
        "fields_sha256": {f: full.fingerprint(t) for f, t in field_texts.items()},
        "parent_text_fingerprints": parent["provenance"],
    })
    # Read-only original vectors must exist before making any new paid request.
    qvectors = cached_vectors(query_texts)
    combined_full = cached_vectors(all_texts)
    corpus_ids = list(papers)
    positions = {p: i for i, p in enumerate(corpus_ids)}
    concat = combined_full[[positions[p] for p in ids]]
    del combined_full
    counts = {f: full.token_counts(t) for f, t in field_texts.items()}
    ledger = full.Ledger()
    origin_path = OUT / "accounting-origin.json"
    if origin_path.exists():
        origin = json.loads(origin_path.read_text(encoding="utf-8"))["nanodollars"]
    else:
        origin = accounted_nanodollars(ledger)
        freeze(origin_path, {"nanodollars": origin, "ledger": str(full.LEDGER)})
    task_ledger = CappedLedger(full.LEDGER, origin)
    needed = {f: full.planned_tokens(t, counts[f], {}, CACHE)[0]
              for f, t in field_texts.items()}
    estimate = {
        "candidate_documents": len(ids), "field_inputs": 2 * len(ids),
        "tokens": {f: sum(c) for f, c in counts.items()},
        "new_reserved_tokens": needed,
        "new_reserved_usd": sum(needed.values()) * full.PRICE / 1e9,
        "shared_accounting_before": ledger.summary(),
        "task_already_accounted_usd": (accounted_nanodollars(ledger) - origin) / 1e9,
        "task_cap_usd": LOCAL_CAP / 1e9, "run_enabled": args.run,
    }
    fusion._write_json(OUT / "preflight.json", estimate)
    print(json.dumps(estimate, indent=2), flush=True)
    accounting_path = OUT / "embedding-accounting.json"
    if accounting_path.exists() and any(needed.values()):
        raise full.EmbeddingError("Completed experiment cache missing; refusing automatic paid repair")
    if any(needed.values()) and (
            (accounted_nanodollars(ledger) - origin + sum(needed.values()) * full.PRICE > LOCAL_CAP)
            or accounted_nanodollars(ledger) + sum(needed.values()) * full.PRICE > full.CAP):
        raise full.BudgetExceeded("Preflight exceeds task or shared lifetime cap; no requests sent")
    if not args.run:
        return
    load_dotenv(config.PROJECT_ROOT / ".env")
    key = os.environ.get("OPENAI_API_KEY", "")
    if any(needed.values()) and not key:
        raise full.EmbeddingError("OPENAI_API_KEY is required for new field embeddings")
    start = time.perf_counter()
    vectors = {f: full.embed(t, counts[f], {}, CACHE, task_ledger, key)
               for f, t in field_texts.items()}
    lookup = {p: i for i, p in enumerate(ids)}
    raw = {}
    for q, query_vector in zip(qids, qvectors):
        indices = [lookup[p] for p in base[q]]
        raw[q] = {
            "candidate_ids": base[q],
            "concat": field_scores(query_vector, concat[indices], vectors["title"][indices],
                                   vectors["abstract"][indices], None).tolist(),
            "title": (vectors["title"][indices] @ query_vector).tolist(),
            "abstract": (vectors["abstract"][indices] @ query_vector).tolist(),
        }
    fusion._write_json(OUT / "raw-field-scores.json", raw)
    runs = build_runs(base, raw, experiment["settings"])
    for name, run in runs.items():
        fusion.validate_run(name, run, qids, papers, exact_depth=100)
        if any(set(run[q]) != set(base[q]) for q in qids):
            raise ValueError("Experiment candidate set changed")
        fusion._write_json(OUT / f"{name}.run.json", run)
    measured_execution = {
        "new_accounted_usd": (accounted_nanodollars(ledger) - origin) / 1e9,
        "shared_lifetime_accounting": ledger.summary(),
        "model": full.MODEL, "dimensions": full.DIMENSIONS, "candidate_documents": len(ids),
        "field_inputs": 2 * len(ids), "embedding_tokens_estimate": sum(map(sum, counts.values())),
        "judge_calls": 0,
    }
    if accounting_path.exists():
        execution = json.loads(accounting_path.read_text(encoding="utf-8"))
    else:
        execution = measured_execution
        freeze(accounting_path, execution)
    report = publish(OUT, runs, snapshot, papers, queries, qids, experiment, execution)
    print(f"Completed8 settings in {time.perf_counter() - start:.1f}s this invocation; "
          f"new accounted ${execution['new_accounted_usd']:.6f}; "
          f"{report['missing_pairs']} missing judgments; baseline unchanged.", flush=True)


if __name__ == "__main__":
    main()
