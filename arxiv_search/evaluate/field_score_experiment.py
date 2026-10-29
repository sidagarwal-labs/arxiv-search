"""Dev-only, candidate-fixed title/abstract field ablation; no hosted calls.

Run: python -m arxiv_search.evaluate.field_score_experiment
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np

from arxiv_search import config
from arxiv_search.evaluate import judge, results_catalog as catalog
from arxiv_search.evaluate.score_fusion_experiment import summarize
from arxiv_search.search.bm25 import BM25
from arxiv_search.search.text import paper_text, tokenize

OUT = config.RESULTS_DIR / "field-score-dev"
CACHE = config.EMBEDDINGS_DIR / "field-score-dev"
# Historical Decision36 control, independent of later baseline promotions.
BASELINE = "fusion-shortlist+a=1+d=500"
MODEL = "thenlper/gte-small"
REVISION = "17e1f347d17fe144873b1201da91788898c639cd"
FIELDS = ("title", "abstract", "authors")
BATCH = 32


def fingerprint(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8")


def freeze(path: Path, value: object) -> None:
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != value:
            raise ValueError(f"Frozen experiment input changed: {path.name}")
    else:
        write_json(path, value)


def plan() -> dict:
    settings = {
        f"field-lexical+t={weight:g}": {"family": "lexical", "title_weight": weight}
        for weight in (.25, .5, .75)}
    settings["field-gte-concat"] = {"family": "semantic-concat"}
    settings.update({
        f"field-gte-separate+t={weight:g}": {
            "family": "semantic-separate", "title_weight": weight}
        for weight in (.25, .5, .75)})
    return {
        "baseline": BASELINE, "split": "dev", "settings": settings,
        "hypothesis": "Explicit title/abstract scores improve fixed-candidate ordering.",
        "candidate_policy": "Exactly Decision36 top100 per dev query; no routing or retrieval.",
        "body_definition": "Abstract only; no full text.",
        "lexical": {"k1": .8, "b": .75, "tokens": "exact plus marked English stems",
                    "statistics": "Independent title/abstract/author BM25 indexes on full corpus",
                    "normalization": "Each field divided by its maximum over fixed candidates",
                    "author_weight": .1,
                    "formula": ".9*(t*title+(1-t)*abstract)+.1*authors"},
        "semantic": {"model": MODEL, "revision": REVISION, "device": "cpu",
                     "dtype": "float32", "threads": 4, "batch_size": BATCH,
                     "normalization": "Unit vectors; cosine mapped to [0,1] via (cos+1)/2",
                     "concat_recipe": "title + single space + abstract; same GTE/query encoding",
                     "separate_recipe": "t*title_cosine+(1-t)*abstract_cosine",
                     "authors": "Inherited baseline signal only; identical for all GTE settings",
                     "scope": "Candidate-unique documents only; queries dev only",
                     "budget_seconds": 1200},
        "reranking": ".75*31/(30+baseline_rank)+.25*field_signal; stable baseline ties",
        "primary_metric": "ndcg@10",
        "interpretation": "Dev exploratory ablation, not baseline promotion; lexical and semantic "
                          "families are separate interventions. Concat vs separate controls model "
                          "change. Original baseline retains OpenAI semantic/author evidence.",
        "labels": "Frozen score-fusion-dev/labels.json unchanged including human overrides",
        "missing_labels": "Unjudged zero is provisional; withhold graded paired intervals.",
        "no_paid_calls": True, "no_test_evaluation": True, "automatic_promotion": False,
    }


def validate_scope(base: dict, dev_ids: list[str], test_ids: list[str],
                   papers: dict, depth: int = 100) -> None:
    if (len(dev_ids) != len(set(dev_ids)) or not dev_ids
            or set(dev_ids) & set(test_ids) or set(base) != set(dev_ids)):
        raise ValueError("Expected exactly unique dev rankings and disjoint heldout IDs")
    for qid, ids in base.items():
        if (len(ids) != depth or len(set(ids)) != depth or set(ids) - set(papers)):
            raise ValueError(f"Invalid fixed candidates: {qid}")


def max_normalize(values: np.ndarray) -> np.ndarray:
    if values.ndim != 1 or not np.isfinite(values).all() or np.any(values < 0):
        raise ValueError("Expected finite nonnegative lexical field scores")
    maximum = float(values.max())
    return values / maximum if maximum else np.zeros_like(values)


def field_signal(raw: dict[str, np.ndarray], setting: dict) -> np.ndarray:
    family = setting["family"]
    if family == "lexical":
        t = setting["title_weight"]
        return .9 * (t * max_normalize(raw["lexical_title"])
                     + (1 - t) * max_normalize(raw["lexical_abstract"])) + (
                         .1 * max_normalize(raw["lexical_authors"]))
    if family == "semantic-concat":
        return (raw["semantic_concat"] + 1) / 2
    if family == "semantic-separate":
        t = setting["title_weight"]
        return (t * raw["semantic_title"] + (1 - t) * raw["semantic_abstract"] + 1) / 2
    raise ValueError(f"Unknown family: {family}")


def reorder(ids: list[str], signal: np.ndarray, base_fraction: float = .75) -> list[str]:
    if signal.shape != (len(ids),) or not np.isfinite(signal).all():
        raise ValueError("Invalid candidate signal")
    if not 0 <= base_fraction <= 1:
        raise ValueError("Invalid baseline fraction")
    ranks = np.arange(1, len(ids) + 1)
    scores = base_fraction * 31 / (30 + ranks) + (1 - base_fraction) * signal
    return [ids[i] for i in np.argsort(-scores, kind="stable")]


def cache_identity(ids: list[str], texts: list[str], field: str,
                   revision: str = REVISION) -> dict:
    if len(ids) != len(texts) or len(set(ids)) != len(ids):
        raise ValueError("Cache requires aligned unique IDs and texts")
    return {"model": MODEL, "revision": revision, "field": field, "ids": ids,
            "text_sha256": [hashlib.sha256(t.encode()).hexdigest() for t in texts],
            "normalized": True, "dtype": "float32"}


def validate_vectors(vectors: np.ndarray, count: int) -> None:
    if (vectors.ndim != 2 or vectors.shape != (count, 384)
            or vectors.dtype != np.float32 or not np.isfinite(vectors).all()
            or not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-4)):
        raise ValueError("Invalid normalized GTE cache vectors")


def read_cache(path: Path, identity: dict) -> np.ndarray | None:
    if not path.exists():
        return None
    with np.load(path, allow_pickle=False) as archive:
        if json.loads(str(archive["identity"])) != identity:
            return None
        vectors = archive["vectors"]
    validate_vectors(vectors, len(identity["ids"]))
    return vectors


class SemanticBudgetExceeded(RuntimeError):
    pass


def encode_cached(model, ids: list[str], texts: list[str], field: str,
                  deadline: float, progress: dict) -> np.ndarray:
    chunks = []
    for start in range(0, len(ids), BATCH):
        group_ids, group_texts = ids[start:start + BATCH], texts[start:start + BATCH]
        identity = cache_identity(group_ids, group_texts, field)
        path = CACHE / f"{field}-{fingerprint(identity)}.npz"
        vectors = read_cache(path, identity)
        if vectors is None:
            if time.perf_counter() >= deadline:
                raise SemanticBudgetExceeded(f"Budget exhausted at {field}/{start}; rerun to resume")
            vectors = model.encode(group_texts, batch_size=BATCH, normalize_embeddings=True,
                                   convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
            validate_vectors(vectors, len(group_ids))
            partial = path.with_suffix(".npz.partial")
            with partial.open("wb") as stream:
                np.savez(stream, vectors=vectors, identity=json.dumps(identity, sort_keys=True))
            partial.replace(path)
            progress["encoded_texts"] += len(group_ids)
        else:
            progress["cached_texts"] += len(group_ids)
        chunks.append(vectors)
        if start % (BATCH * 16) == 0:
            print(f"GTE {field}: {start + len(group_ids)}/{len(ids)}", flush=True)
    return np.concatenate(chunks)


def lexical_scores(papers: dict, queries: dict, base: dict) -> dict:
    ids = list(papers)
    positions = {pid: i for i, pid in enumerate(ids)}
    result = {q: {} for q in base}
    for field in FIELDS:
        docs = [tokenize(" ".join(papers[p][field]) if field == "authors" else papers[p][field],
                         add_stems=True) for p in ids]
        if not any(docs):
            raise ValueError(f"Empty corpus field: {field}")
        index = BM25(docs, ids, k1=.8, b=.75)
        for qid, candidates in base.items():
            all_scores = index.scores(tokenize(queries[qid]["query"], add_stems=True))
            result[qid][f"lexical_{field}"] = all_scores[[positions[p] for p in candidates]]
    return result


def changes(run: dict, base: dict, queries: dict) -> dict:
    lost, gained, known = [], [], []
    for qid, ids in run.items():
        target = queries[qid]["source_arxiv_id"]
        old = base[qid].index(target) + 1 if target in base[qid] else None
        new = ids.index(target) + 1 if target in ids else None
        if target in base[qid][:10] and target not in ids[:10]:
            lost.append(qid)
        if target not in base[qid][:10] and target in ids[:10]:
            gained.append(qid)
        if queries[qid]["query_type"] == "known_item" and old != new:
            known.append({"query_id": qid, "baseline_rank": old, "candidate_rank": new})
    return {"queries_with_top10_order_changes": sum(run[q][:10] != base[q][:10] for q in base),
            "queries_with_any_order_changes": sum(run[q] != base[q] for q in base),
            "lost_source_top10": lost, "gained_source_top10": gained,
            "known_item_target_rank_changes": known}


def publish(raw: dict, base: dict, snapshot: dict, papers: dict, queries: dict,
            preregistration: dict, provenance: dict, runtime: dict) -> dict:
    runs = {BASELINE: base}
    settings = preregistration["settings"]
    for name, setting in settings.items():
        required = {
            "lexical": ("lexical_title", "lexical_abstract", "lexical_authors"),
            "semantic-concat": ("semantic_concat",),
            "semantic-separate": ("semantic_title", "semantic_abstract"),
        }[setting["family"]]
        if all(all(key in fields for key in required) for fields in raw.values()):
            runs[name] = {q: reorder(base[q], field_signal(raw[q], setting)) for q in base}
    for name in set(settings) - set(runs):
        for suffix in (".run.json", ".info.json"):
            (OUT / f"{name}{suffix}").unlink(missing_ok=True)
    entries = {}
    for name, run in runs.items():
        validate_scope(run, list(base), [], papers)
        if any(set(run[q]) != set(base[q]) for q in base):
            raise ValueError("Candidate set changed")
        filename = f"{name}.run.json"
        write_json(OUT / filename, run)
        metadata = {"experiment": "field-score-dev", "baseline": BASELINE,
                    "setting": settings.get(name), "preregistration": "preregistration.json",
                    "provenance": "input-provenance.json"}
        write_json(OUT / f"{name}.info.json", metadata)
        entries[name] = {"run": run, "paths": [f"field-score-dev/{filename}"],
                         "metadata": {f"field-score-dev/{name}.info.json": metadata}}
    scored = catalog.score_catalog(entries, snapshot, papers, queries, list(base), BASELINE)
    missing = [{"query_id": q, "arxiv_id": p,
                "systems": [n for n, run in runs.items() if p in run[q][:10]]}
               for q in base for p in dict.fromkeys(p for run in runs.values() for p in run[q][:10])
               if p not in snapshot["labels"][q]]
    write_json(OUT / "missing-judgments.json", missing)
    write_json(OUT / "raw-field-scores.json", {
        q: {"candidate_ids": base[q], "scores": {k: v.tolist() for k, v in fields.items()}}
        for q, fields in raw.items()})
    report = {
        "baseline": BASELINE, "provenance": provenance, "runtime": runtime,
        "completed_settings": [n for n in runs if n != BASELINE],
        "incomplete_settings": [n for n in settings if n not in runs],
        "systems": scored, "summary": summarize({n: s["per_query"] for n, s in scored.items()},
                                               BASELINE),
        "changes": {n: changes(run, base, queries) for n, run in runs.items()},
        "missing_pairs": len(missing), "labels_modified": False, "api_calls": 0,
        "promoted": False, "candidate_set_preserved": True,
    }
    if "field-gte-concat" in runs:
        report["semantic_vs_same_model_concat"] = {
            n: changes(run, runs["field-gte-concat"], queries)
            for n, run in runs.items() if n.startswith("field-gte-separate+")}
    write_json(OUT / "report.json", report)
    lines = ["# Fixed-candidate field score experiment", "",
             "Dev only; body = abstract. Frozen labels and human overrides unchanged. "
             "No paid calls or heldout evaluation. No promotion.", "",
             "Seven prespecified configurations; all reorder exactly the Decision36 top100. "
             "Score = 75% baseline reciprocal rank (31/(30+r)) + 25% field evidence. "
             "Lexical: full-corpus independent BM25 exact+stems k1=.8/b=.75, candidate-max "
             "normalization; 10% author + 90% weighted title/abstract. Semantic: same local "
             "GTE model for concat and separate fields, normalized cosine mapped to [0,1].", "",
             f"Model: `{MODEL}` revision `{REVISION}`; CPU float32, <=4 torch threads.", "",
             f"Runtime: `{json.dumps(runtime)}`", "",
             f"Missing distinct top10 judgments: **{len(missing)}**. Graded means are provisional "
             "where incomplete; graded paired intervals withheld. Source metrics remain valid.", "",
             "| System | nDCG@10 | P@10 | Judged@10 | Source MRR@10 | R@10 | R@20 | Status |",
             "|---|---:|---:|---:|---:|---:|---:|---|"]
    for name, score in scored.items():
        fields = score["all"]
        values = [fields[f]["mean"] for f in
                  ("ndcg@10", "precision@10", "judged@10", "source_mrr@10",
                   "source_recall@10", "source_recall@20")]
        lines.append(f"| {name} | " + " | ".join(f"{v:.6f}" if v is not None else "undefined"
                                                for v in values) + f" | {score['status']} |")
    lines += ["", "## Segment and target changes", "",
              "Per-query and query-type metrics, source paired intervals, and all lost/gained "
              "source/known-item rank changes are in report.json. Missing pairs are explicitly "
              "listed in missing-judgments.json; no new grades were inferred.", "",
              "## Interpretation boundary", "",
              "The semantic comparison tests a conservative 25% additional signal, not pure "
              "semantic ranking or retriever recall. Inspect top10-order-change counts before "
              "interpreting equal metrics: an unchanged top10 is no observable intervention at "
              "the primary cutoff, not evidence that separate field representations are useless. "
              "Same-model concat comparisons are recorded separately in report.json.", "",
              "## Completion", "", f"Incomplete configurations: {report['incomplete_settings']}.",
              "Embedding shards are resumable and validate model/revision, ordered IDs, exact "
              "text hashes, dtype, finite values, shape, and unit norms."]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def order_shortlist(ids: list[str], signal: np.ndarray) -> list[str]:
    """Pure field ordering inside the declared top10, preserving all tail ranks."""
    if signal.shape != (len(ids),) or not np.isfinite(signal).all() or len(ids) < 10:
        raise ValueError("Expected finite scores for at least ten baseline candidates")
    order = np.argsort(-signal[:10], kind="stable")
    return [ids[i] for i in order] + ids[10:]


def signal_plan() -> dict:
    return {
        "baseline": BASELINE, "split": "dev", "exploratory": True,
        "motivation": "Follow-up to conservative field-score-dev semantic top10 no-op; "
                      "remove base-rank dominance. Post-outcome exploratory, not confirmatory.",
        "settings": {
            "field-order-gte-concat": {"family": "semantic-concat"},
            **{f"field-order-gte-separate+t={t:g}": {
                "family": "semantic-separate", "title_weight": t} for t in (.25, .5, .75)}},
        "formula": "Concat: (cos(q,title+space+abstract)+1)/2; separate: "
                   "(t*cos(q,title)+(1-t)*cos(q,abstract)+1)/2",
        "ranking": "Sort Decision36 top10 by descending field signal only; stable baseline "
                   "ties; preserve tail exactly. No query/label-dependent routing.",
        "model": MODEL, "revision": REVISION, "primary_metric": "ndcg@10",
        "source": "Existing field-score-dev/raw-field-scores.json only",
        "new_inference_calls": 0, "paid_calls": 0, "automatic_promotion": False,
    }


def signal_followup() -> None:
    """Independent cached-score-only experiment; never invokes an encoder or judge."""
    start = time.perf_counter()
    out = config.RESULTS_DIR / "field-signal-dev"
    out.mkdir(parents=True, exist_ok=True)
    registered = signal_plan()
    freeze(out / "preregistration.json", registered)
    source = config.RESULTS_DIR / "field-score-dev"
    source_report_raw = (source / "report.json").read_bytes()
    source_report = json.loads(source_report_raw)
    raw_path = source / "raw-field-scores.json"
    raw_bytes = raw_path.read_bytes()
    saved = json.loads(raw_bytes)
    base_path = source / f"{BASELINE}.run.json"
    base_bytes = base_path.read_bytes()
    base = json.loads(base_bytes)
    papers, all_queries, splits = judge.load_inputs()
    qids = sorted(splits["dev"])
    queries = {q: all_queries[q] for q in qids}
    validate_scope(base, qids, splits["test"], papers)
    _, label_raw, snapshot, _ = catalog.load_snapshot(config.RESULTS_DIR)
    parent = source_report["provenance"]
    if (hashlib.sha256(label_raw).hexdigest() != parent["snapshot_sha256"]
            or fingerprint(papers) != parent["corpus_fields_sha256"]
            or fingerprint(queries) != parent["dev_queries_sha256"]
            or parent["semantic_model"] != MODEL or parent["semantic_revision"] != REVISION):
        raise ValueError("Frozen field-score inputs/model/labels changed")
    if set(saved) != set(qids):
        raise ValueError("Raw field scores must contain exactly dev IDs")
    raw = {}
    for qid, row in saved.items():
        if row["candidate_ids"] != base[qid]:
            raise ValueError(f"{qid}: raw score candidate order changed")
        raw[qid] = {key: np.asarray(value, dtype=float) for key, value in row["scores"].items()}
        for field in ("semantic_concat", "semantic_title", "semantic_abstract"):
            values = raw[qid][field]
            if values.shape != (100,) or not np.isfinite(values).all() or np.any(abs(values) > 1.00001):
                raise ValueError(f"{qid}: invalid cached cosine scores")
    provenance = {
        "parent_report_sha256": hashlib.sha256(source_report_raw).hexdigest(),
        "raw_field_scores_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "baseline_file_sha256": hashlib.sha256(base_bytes).hexdigest(),
        "baseline_ranking_sha256": fingerprint(base), "frozen_parent_inputs": parent,
        "labels_sha256": hashlib.sha256(label_raw).hexdigest(),
        "source_runtime_seconds": source_report["runtime"]["cumulative_total_seconds"],
    }
    freeze(out / "input-provenance.json", provenance)
    runs = {BASELINE: base}
    for name, setting in registered["settings"].items():
        runs[name] = {q: order_shortlist(base[q], field_signal(raw[q], setting)) for q in qids}
    entries = {}
    for name, run in runs.items():
        validate_scope(run, qids, [], papers)
        if any(set(run[q][:10]) != set(base[q][:10]) or run[q][10:] != base[q][10:]
               for q in qids):
            raise ValueError("Follow-up changed shortlist membership or tail")
        filename = f"{name}.run.json"
        write_json(out / filename, run)
        info = {"baseline": BASELINE, "setting": registered["settings"].get(name),
                "ranker": "Pure field cosine within fixed baseline top10; preserve tail",
                "model": MODEL, "revision": REVISION, "exploratory": True,
                "no_new_inference": True}
        write_json(out / f"{name}.info.json", info)
        entries[name] = {"run": run, "paths": [f"field-signal-dev/{filename}"],
                         "metadata": {f"field-signal-dev/{name}.info.json": info}}
    scored = catalog.score_catalog(entries, snapshot, papers, queries, qids, BASELINE)
    if not all(s["top10_fully_judged"] for s in scored.values()):
        raise ValueError("Expected fully judged fixed baseline shortlist")
    labels = snapshot["labels"]
    comparisons = {}
    for name, run in runs.items():
        first_zero = [q for q in qids if labels[q][run[q][0]] == 0]
        old_zero = [q for q in qids if labels[q][base[q][0]] == 0]
        comparisons[name] = {
            **changes(run, base, queries), "grade0_first": len(first_zero),
            "new_grade0_first_queries": sorted(set(first_zero) - set(old_zero)),
            "removed_grade0_first_queries": sorted(set(old_zero) - set(first_zero))}
    report = {
        "baseline": BASELINE, "exploratory": True, "provenance": provenance,
        "systems": scored, "summary": summarize({n: s["per_query"] for n, s in scored.items()},
                                               BASELINE),
        "changes": comparisons, "missing_pairs": 0,
        "candidate_sets_preserved": True, "top10_membership_preserved": True,
        "tails_exactly_preserved": True, "labels_modified": False,
        "inference_calls": 0, "paid_calls": 0, "promoted": False,
        "runtime_seconds": round(time.perf_counter() - start, 3),
    }
    concat_name = "field-order-gte-concat"
    concat_rows = {r["query_id"]: r for r in scored[concat_name]["per_query"]}
    from arxiv_search.evaluate import metrics
    report["paired_ndcg_vs_same_model_concat"] = {}
    for name, result in scored.items():
        if not name.startswith("field-order-gte-separate+"):
            continue
        rows = {r["query_id"]: r for r in result["per_query"]}
        mean, low, high = metrics.paired_diff_ci(
            [concat_rows[q]["ndcg@10"] for q in qids],
            [rows[q]["ndcg@10"] for q in qids])
        report["paired_ndcg_vs_same_model_concat"][name] = {
            "difference": mean, "ci95": [low, high], "n": len(qids)}
    write_json(out / "report.json", report)
    write_json(out / "missing-judgments.json", [])
    lines = ["# Pure semantic field ordering within Decision36 top10", "",
             registered["motivation"], "", registered["ranking"], "", registered["formula"], "",
             "All top10 positions fully judged against unchanged frozen labels/human overrides. "
             "Source R@10/R@20 invariant by construction; ordering/MRR and nDCG can change. "
             "Cached scores only: no inference or paid calls.", "",
             "| System | nDCG@10 | P@10 | Source MRR@10 | R@1 | Grade0 first | ΔnDCG / 95% CI |",
             "|---|---:|---:|---:|---:|---:|---|"]
    for name, result in scored.items():
        values = result["all"]
        paired = result["paired_ndcg_vs_working_baseline"]
        interval = ("control" if paired is None else
                    f"{paired['difference']:.6f} [{paired['ci95'][0]:.6f}, {paired['ci95'][1]:.6f}]")
        lines.append(f"| {name} | " + " | ".join(f"{values[f]['mean']:.6f}" for f in
                     ("ndcg@10", "precision@10", "source_mrr@10", "source_recall@1"))
                     + f" | {comparisons[name]['grade0_first']} | {interval} |")
    lines += ["", "Query-type metrics, paired comparisons to same-model concat, known-item rank "
              "changes, grade0 gained/removed cases, and all per-query metrics are in report.json.",
              "", f"Model `{MODEL}`, revision `{REVISION}`. Cache-only runtime "
              f"{report['runtime_seconds']}s; original cumulative encoding/experiment runtime "
              f"{provenance['source_runtime_seconds']}s. Fingerprints in input-provenance.json.",
              "", "No automatic promotion. Follow-up selection is post-outcome exploratory."]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"folder": str(out), "runtime_seconds": report["runtime_seconds"],
                      "missing_pairs": 0, "settings": list(registered["settings"])}))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lexical-only", action="store_true",
                        help="Persist lexical results; semantic settings explicitly incomplete")
    parser.add_argument("--signal-followup", action="store_true",
                        help="New exploratory fixed-top10 ordering using existing scores only")
    args = parser.parse_args(argv)
    if args.signal_followup:
        if args.lexical_only:
            parser.error("--signal-followup and --lexical-only are mutually exclusive")
        signal_followup()
        return
    start = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    history_path = OUT / "runtime-history.json"
    history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.exists() else []
    previous_report = OUT / "report.json"
    if not history and previous_report.exists():
        previous_runtime = json.loads(previous_report.read_text(encoding="utf-8"))["runtime"]
        if "total_seconds" in previous_runtime:
            history = [previous_runtime]
    preregistration = plan()
    freeze(OUT / "preregistration.json", preregistration)
    papers, all_queries, splits = judge.load_inputs()
    qids = sorted(splits["dev"])
    queries = {q: all_queries[q] for q in qids}
    base_path = config.RESULTS_DIR / "shortlist-score-dev" / f"{BASELINE}.run.json"
    base_raw = base_path.read_bytes()
    base = json.loads(base_raw)
    validate_scope(base, qids, splits["test"], papers)
    snapshot_path, snapshot_raw, snapshot, label_provenance = catalog.load_snapshot(
        config.RESULTS_DIR)
    if snapshot_path != config.RESULTS_DIR / "score-fusion-dev" / "labels.json":
        raise ValueError("Required frozen score-fusion label snapshot missing")
    candidate_ids = sorted({p for ids in base.values() for p in ids})
    provenance = {
        "baseline_path": str(base_path.relative_to(config.PROJECT_ROOT)),
        "baseline_sha256": hashlib.sha256(base_raw).hexdigest(),
        "snapshot_sha256": hashlib.sha256(snapshot_raw).hexdigest(),
        "snapshot_path": str(snapshot_path.relative_to(config.PROJECT_ROOT)),
        "label_provenance": label_provenance,
        "corpus_fields_sha256": fingerprint(papers),
        "dev_queries_sha256": fingerprint(queries), "dev_query_ids": qids,
        "candidate_ids_sha256": fingerprint(candidate_ids),
        "candidate_unique_documents": len(candidate_ids),
        "semantic_model": MODEL, "semantic_revision": REVISION,
    }
    freeze(OUT / "input-provenance.json", provenance)
    raw = lexical_scores(papers, queries, base)
    lexical_seconds = time.perf_counter() - start
    runtime = {"lexical_seconds": round(lexical_seconds, 3), "semantic_status": "not requested",
               "encoded_texts": 0, "cached_texts": 0,
               "prior_invocations": len(history),
               "prior_total_seconds": round(sum(r["total_seconds"] for r in history), 3)}
    publish(raw, base, snapshot, papers, queries, preregistration, provenance, runtime)
    if not args.lexical_only:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        from huggingface_hub import snapshot_download
        import torch
        from sentence_transformers import SentenceTransformer

        torch.set_num_threads(4)
        torch.set_num_interop_threads(1)
        model_path = snapshot_download(MODEL, revision=REVISION, local_files_only=True)
        if Path(model_path).name != REVISION:
            raise ValueError("Unexpected local model revision")
        model = SentenceTransformer(model_path, device="cpu", local_files_only=True,
                                    model_kwargs={"torch_dtype": torch.float32})
        CACHE.mkdir(parents=True, exist_ok=True)
        semantic_start = time.perf_counter()
        deadline = semantic_start + preregistration["semantic"]["budget_seconds"]
        runtime.update(semantic_status="running", max_tokens=model.max_seq_length,
                       torch_threads=torch.get_num_threads())
        try:
            qvectors = encode_cached(model, qids, [queries[q]["query"] for q in qids],
                                     "queries", deadline, runtime)
            locations = {pid: i for i, pid in enumerate(candidate_ids)}
            for field in ("concat", "title", "abstract"):
                texts = [paper_text(papers[p]) if field == "concat" else papers[p][field]
                         for p in candidate_ids]
                vectors = encode_cached(model, candidate_ids, texts, field, deadline, runtime)
                for qid, qvector in zip(qids, qvectors):
                    raw[qid][f"semantic_{field}"] = (
                        vectors[[locations[p] for p in base[qid]]] @ qvector)
                publish(raw, base, snapshot, papers, queries, preregistration, provenance, runtime)
            runtime["semantic_status"] = "completed"
        except SemanticBudgetExceeded as error:
            runtime.update(semantic_status="budget exceeded; partial cache resumable",
                           blocker=str(error))
        runtime["semantic_seconds"] = round(time.perf_counter() - semantic_start, 3)
    runtime["total_seconds"] = round(time.perf_counter() - start, 3)
    runtime["cumulative_total_seconds"] = round(runtime["prior_total_seconds"]
                                                + runtime["total_seconds"], 3)
    write_json(history_path, [*history, runtime])
    report = publish(raw, base, snapshot, papers, queries, preregistration, provenance, runtime)
    print(json.dumps({"completed": report["completed_settings"],
                      "incomplete": report["incomplete_settings"],
                      "missing_pairs": report["missing_pairs"], "runtime": runtime}), flush=True)


if __name__ == "__main__":
    main()
