"""Cached-only field-aware hybrid follow-up; no embedding or judging API path."""

from __future__ import annotations

import hashlib
import json

import numpy as np

from arxiv_search import config
from arxiv_search.evaluate import fusion_experiment as fusion, judge, results_catalog as catalog
from arxiv_search.evaluate import openai_field_experiment as fields
from arxiv_search.evaluate.cross_encoder_experiment import freeze
from arxiv_search.evaluate.field_score_experiment import validate_scope
from arxiv_search.search.rerank import rerank_prefix

OUT = config.RESULTS_DIR / "openai-field-hybrid-dev"


def plan() -> dict:
    experiment = fields.plan()
    experiment["settings"] = {name.replace("oai-field+", "oai-field-hybrid+"): options
                              for name, options in experiment["settings"].items()}
    experiment.update(
        hypothesis="Field separation can help same-model semantic ordering; retaining lexical "
                   "evidence may close the gap to the current hybrid baseline.",
        scoring="25% candidate-max-normalized original BM25 (including authors/title2x) "
                "+75% candidate-max-normalized semantic score, where semantic is concat cosine "
                "or t*title_cosine+(1-t)*abstract_cosine. Same candidate100 normalization for "
                "every setting, fixed weights, baseline ties. Reorder prefixes10/100.",
        followup="Prespecified after pure-semantic outcomes; distinct experiment identity. "
                 "Exploratory cached-score follow-up, not independent confirmation.",
        automatic_embedding_calls=False,
    )
    return experiment


def hybrid_signal(lexical: np.ndarray, semantic: np.ndarray) -> np.ndarray:
    if (lexical.ndim != 1 or lexical.shape != semantic.shape or not len(lexical)
            or not np.isfinite(lexical).all() or not np.isfinite(semantic).all()
            or np.any(lexical < 0) or semantic.max() <= 0):
        raise ValueError("Invalid hybrid field score arrays")
    lex_max = lexical.max()
    normalized_lexical = lexical / lex_max if lex_max > 0 else np.zeros_like(lexical)
    return .25 * normalized_lexical + .75 * semantic / semantic.max()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    experiment = plan()
    freeze(OUT / "preregistration.json", experiment)
    parent = fields.OUT
    raw_path = parent / "raw-field-scores.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    parent_report_path = parent / "report.json"
    parent_report = json.loads(parent_report_path.read_text(encoding="utf-8"))
    manifest_path = parent / "input-provenance.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    papers, queries, split = judge.load_inputs()
    qids = sorted(split["dev"])
    base_path = parent / f"{fields.BASELINE}.run.json"
    base = json.loads(base_path.read_text(encoding="utf-8"))
    validate_scope(base, qids, split["test"], papers)
    if set(raw) != set(qids) or qids != manifest["query_ids"]:
        raise ValueError("Parent candidate score scope differs")
    snapshot_path, snapshot_raw, snapshot, _ = catalog.load_snapshot(config.RESULTS_DIR)
    if (hashlib.sha256(snapshot_raw).hexdigest() != manifest["labels_bytes_sha256"]
            or fusion.fingerprint(snapshot) != parent_report["label_snapshot_sha256"]
            or fusion.fingerprint(base) != parent_report["run_fingerprints"][fields.BASELINE]):
        raise ValueError("Parent baseline or label snapshot changed")
    if (fields.full.fingerprint([queries[q]["query"] for q in qids]) != manifest["query_sha256"]
            or any(fields.full.fingerprint([papers[p][f] for p in manifest["candidate_ids"]])
                   != manifest["fields_sha256"][f] for f in ("title", "abstract"))):
        raise ValueError("Parent query/document field text changed")
    inputs_path = config.RESULTS_DIR / "score-fusion-dev" / "input-scores.json"
    inputs = json.loads(inputs_path.read_text(encoding="utf-8"))
    if hashlib.sha256(inputs_path.read_bytes()).hexdigest() != manifest["retrieval_bytes_sha256"]:
        raise ValueError("Frozen lexical score inputs changed")
    freeze(OUT / "input-provenance.json", {
        "raw_field_scores_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        "parent_report_sha256": hashlib.sha256(parent_report_path.read_bytes()).hexdigest(),
        "parent_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "labels_bytes_sha256": hashlib.sha256(snapshot_raw).hexdigest(),
        "label_snapshot": snapshot_path.relative_to(config.RESULTS_DIR).as_posix(),
        "baseline_sha256": fusion.fingerprint(base),
        "lexical_inputs_sha256": hashlib.sha256(inputs_path.read_bytes()).hexdigest(),
    })
    runs = {fields.BASELINE: base}
    for name, options in experiment["settings"].items():
        weight = options["title_weight"]
        runs[name] = {}
        for q in qids:
            ids = base[q]
            row = raw[q]
            if row["candidate_ids"] != ids:
                raise ValueError("Unaligned candidate field scores")
            semantic = np.asarray(row["concat"] if weight is None else
                                  weight * np.asarray(row["title"])
                                  + (1 - weight) * np.asarray(row["abstract"]))
            lex_scores = dict(inputs[q]["lexical"])
            # Absence means no positive lexical score in the frozen top500 input.
            lexical = np.asarray([lex_scores.get(p, 0.) for p in ids])
            scores = hybrid_signal(lexical, semantic)
            runs[name][q] = rerank_prefix(ids, dict(zip(ids, scores.tolist())), options["depth"])
    for n, run in runs.items():
        fusion.validate_run(n, run, qids, papers, exact_depth=100)
        fusion._write_json(OUT / f"{n}.run.json", run)
    execution = {
        "new_accounted_usd": 0., "new_embedding_api_calls": 0, "judge_calls": 0,
        "parent_embedding_accounted_usd": parent_report["execution"]["new_accounted_usd"],
        "source": "Existing frozen OpenAI field cosine and lexical score caches only",
    }
    report = fields.publish(OUT, runs, snapshot, papers, queries, qids, experiment, execution)
    print(f"Completed8 cached hybrid settings; {report['missing_pairs']} missing judgments; "
          "zero embedding/judge calls; no promotion.")


if __name__ == "__main__":
    main()
