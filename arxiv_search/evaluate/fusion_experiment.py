"""Offline dev fusion of cached top-100 rankings, without a reranker.

python -m arxiv_search.evaluate.fusion_experiment
python -m arxiv_search.evaluate.fusion_experiment --label --max-calls 20
python -m arxiv_search.evaluate.fusion_experiment --judge openai-mini --label --max-calls 20

The default only reads cached judgments. Outputs under data/results/fusion-dev
are independent of experiments.SYSTEMS/save_run. All graded scores use one
shared snapshot; paired comparisons are withheld until its pool is complete.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from arxiv_search import config
from arxiv_search.evaluate import graded, judge, metrics
from arxiv_search.search.hybrid import fuse

LEXICAL = "bm25+exact+stems+authors+title2x+k1=0.8,b=0.75"
SEMANTIC = "dense-openai-large"
ORIGINAL = "hybrid-openai-large+rrf+w=0.5+c=10"
BASELINE = "baseline-original-equal-rrf-c10-d100"
SOURCE_DEPTH = 100
OUT = config.RESULTS_DIR / "fusion-dev"


def fingerprint(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def grid() -> dict[str, dict]:
    """38 settings: two full-depth endpoints and 36 mixed fusion candidates."""
    settings = {}
    for depth in (20, 50, 100):
        for weight in (0.0, 0.25, 0.5, 0.75, 1.0):
            if weight in (0, 1) and depth != SOURCE_DEPTH:
                continue
            methods = (("rrf", 10),) if weight in (0, 1) else (
                ("rrf", 10), ("rrf", 60), ("rrf", 100), ("linear", 60))
            for method, c in methods:
                name = f"fusion-{method}+w={weight:g}+d={depth}"
                if method == "rrf":
                    name += f"+c={c}"
                settings[name] = dict(method=method, semantic_weight=weight,
                                      c=c, depth=depth, k=SOURCE_DEPTH)
    return settings


def validate_run(name: str, run: dict, qids: list[str], papers: dict,
                 *, exact_depth: int | None = None) -> None:
    if not isinstance(run, dict) or set(run) != set(qids):
        raise ValueError(f"{name}: expected exactly the dev query IDs")
    for qid, ids in run.items():
        if (not isinstance(ids, list) or not all(isinstance(p, str) for p in ids)
                or len(ids) < config.NDCG_K
                or (exact_depth is not None and len(ids) != exact_depth)):
            raise ValueError(f"{name}/{qid}: insufficient IDs or expected depth {exact_depth}")
        if len(set(ids)) != len(ids) or set(ids) - set(papers):
            raise ValueError(f"{name}/{qid}: duplicate or unknown paper IDs")


def prepare(papers: dict, qids: list[str]) -> tuple[dict, dict, dict]:
    """Read immutable source runs and retain the original graded pool members."""
    if not qids or len(qids) != len(set(qids)):
        raise ValueError("Expected nonempty, unique dev query IDs")
    qids = sorted(qids)
    names = list(dict.fromkeys([LEXICAL, SEMANTIC, ORIGINAL, *graded.SYSTEMS]))
    sources, provenance = {}, {}
    for name in names:
        path = config.RESULTS_DIR / "dev" / f"{name}.run.json"
        raw = path.read_bytes()
        run = json.loads(raw)
        validate_run(name, run, qids, papers,
                     exact_depth=SOURCE_DEPTH if name in (LEXICAL, SEMANTIC, ORIGINAL) else None)
        sources[name] = {q: run[q] for q in qids}
        provenance[name] = {
            "path": str(path), "file_sha256": hashlib.sha256(raw).hexdigest(),
            "ranking_sha256": fingerprint(sources[name]),
        }
    settings = grid()
    runs = {BASELINE: sources[ORIGINAL]}
    configs = {BASELINE: {
        "method": "rrf", "semantic_weight": 0.5, "c": 10, "depth": 100,
        "k": 100, "frozen_from": ORIGINAL,
    }}
    for name, options in settings.items():
        runs[name] = {q: fuse(sources[LEXICAL][q], sources[SEMANTIC][q], **options) for q in qids}
        configs[name] = options
        validate_run(name, runs[name], qids, papers)
    for name in graded.SYSTEMS:
        runs[name] = sources[name]
        configs[name] = {"original_pool_member": True}
    return runs, configs, provenance


def paired_rows(left: list[dict], right: list[dict], field: str) -> dict:
    """Align by query ID, not file order, and expose every win/regression."""
    a = {r["query_id"]: r for r in left}
    b = {r["query_id"]: r for r in right}
    if len(a) != len(left) or len(b) != len(right) or a.keys() != b.keys():
        raise ValueError("Paired comparison needs unique, identical query IDs")
    ids = sorted(q for q in a if a[q][field] is not None and b[q][field] is not None)
    differences = {q: b[q][field] - a[q][field] for q in ids}
    interval = metrics.paired_diff_ci([a[q][field] for q in ids],
                                      [b[q][field] for q in ids]) if ids else None
    return {
        "n": len(ids), "difference": interval[0] if interval else None,
        "ci95": list(interval[1:]) if interval else None,
        "wins": sum(d > 1e-12 for d in differences.values()),
        "regressions": sum(d < -1e-12 for d in differences.values()),
        "ties": sum(abs(d) <= 1e-12 for d in differences.values()),
        "per_query_difference": differences,
    }


def summarize(all_rows: dict, *, complete: bool) -> dict:
    """Means are descriptive when incomplete; no provisional winners or deltas."""
    result = {}
    for name, rows in all_rows.items():
        fields = [f for f in rows[0] if f not in ("query_id", "query_type")]
        groups = [("all", rows)]
        groups += [(kind, [r for r in rows if r["query_type"] == kind])
                   for kind in sorted({r["query_type"] for r in rows})]
        result[name] = {}
        for kind, group in groups:
            baseline = [r for r in all_rows[BASELINE]
                        if kind == "all" or r["query_type"] == kind]
            summary = {}
            for field in fields:
                values = [r[field] for r in group if r[field] is not None]
                summary[field] = {
                    "n": len(values), "mean": sum(values) / len(values) if values else None,
                    "paired_vs_baseline": paired_rows(baseline, group, field) if complete else None,
                }
            result[name][kind] = summary
    return result


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8")


def publish(runs: dict, configs: dict, provenance: dict, labels: dict, pairs: dict,
            queries: dict, source_labels: dict, overrides: int, judge_key: str,
            out: Path = OUT) -> str:
    """Persist rankings, both per-query score families, and one auditable snapshot."""
    out.mkdir(parents=True, exist_ok=True)
    total = sum(map(len, pairs.values()))
    covered = sum(p in labels[q] for q, ids in pairs.items() for p in ids)
    complete = covered == total
    snapshot = {
        "judge": judge_key, "model": config.JUDGES[judge_key]["model"],
        "rubric_version": judge.RUBRIC_VERSION, "complete": complete,
        "provisional": not complete, "query_ids": sorted(pairs),
        "pool_pairs": total, "pool_judged": covered, "pool": pairs,
        "human_overrides": overrides, "labels": labels,
        "human_workbook_sha256": (hashlib.sha256(graded.SHEET_PATH.read_bytes()).hexdigest()
                                  if graded.SHEET_PATH.exists() else None),
        "run_fingerprints": {name: fingerprint(run) for name, run in runs.items()},
    }
    _write_json(out / "configs.json", {
        "baseline": BASELINE, "lexical": LEXICAL, "semantic": SEMANTIC,
        "source_depth": SOURCE_DEPTH, "score_depth": config.NDCG_K,
        "sources": provenance, "systems": configs,
    })
    _write_json(out / "labels.json", snapshot)
    source_rows, graded_rows = {}, {}
    for name, run in runs.items():
        _write_json(out / f"{name}.run.json", run)
        graded_rows[name] = graded.score_graded(run, labels, queries, k=config.NDCG_K)
        source_rows[name] = metrics.score_run(run, {q: source_labels[q] for q in sorted(run)})
        for row in source_rows[name]:
            row["query_type"] = queries[row["query_id"]]["query_type"]
        for family, rows in (("source", source_rows[name]), ("graded", graded_rows[name])):
            (out / f"{name}.{family}.scores.jsonl").write_text(
                "".join(json.dumps(r, sort_keys=True, allow_nan=False) + "\n" for r in rows),
                encoding="utf-8")
    report = {
        "baseline": BASELINE, "complete": complete, "provisional": not complete,
        "label_snapshot_sha256": fingerprint(snapshot),
        "source": summarize(source_rows, complete=complete),
        "graded": summarize(graded_rows, complete=complete),
    }
    _write_json(out / "report.json", report)
    lines = ["# Offline fusion dev experiment", "",
             f"Fixed baseline: `{BASELINE}` (saved original equal RRF, c=10, depth=100).",
             f"Judge: `{judge_key}`; rubric `{judge.RUBRIC_VERSION}`; "
             f"{covered}/{total} pooled top-{config.NDCG_K} pairs judged; "
             f"{overrides} human overrides.", "",
             "**COMPLETE**" if complete else
             "**INCOMPLETE / PROVISIONAL: paired comparisons and winner claims withheld.**",
             "",
             "All systems use the same pooled labels plus human overrides for ideal DCG. "
             "Original graded.SYSTEMS top-10s remain in the pool. Unjudged gains are zero; "
             "nDCG with no positive labels is undefined. Source-paper metrics are separate. "
             "Candidate outputs contain up to 100 papers; a depth-20 union can be shorter.",
             "",
             "Exploratory dev results, not held-out confirmation; no reranker. Judge "
             "calibration used one person's pilot labels, not independent validation. "
             "Paired 95% intervals are query-bootstrap intervals conditional on these labels, "
             "without multiple-comparison correction. Deltas are candidate minus fixed baseline.",
             ""]
    for family in ("graded", "source"):
        lines += [f"## {family.title()} metrics (overall and by query type)", "",
                  "| System | Type | Metric | n | Mean | Paired delta [95% CI] | Wins / regressions / ties |",
                  "|---|---|---|---|---|---|---|"]
        for name, groups in report[family].items():
            for kind, fields in groups.items():
                for field, summary in fields.items():
                    mean = summary["mean"]
                    mean_text = f"{mean:.4f}" if mean is not None else "undefined"
                    paired = summary["paired_vs_baseline"]
                    delta, counts = "withheld", "withheld"
                    if paired is not None:
                        difference, ci = paired["difference"], paired["ci95"]
                        delta = (f"{difference:+.4f} [{ci[0]:+.4f}, {ci[1]:+.4f}]"
                                 if difference is not None else "undefined")
                        counts = f"{paired['wins']} / {paired['regressions']} / {paired['ties']}"
                    lines.append(f"| `{name}` | {kind} | {field} | {summary['n']} | "
                                 f"{mean_text} | {delta} | {counts} |")
    text = "\n".join(lines) + "\n"
    (out / "report.md").write_text(text, encoding="utf-8")
    return text


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--judge", choices=list(config.JUDGES), default=config.DEFAULT_JUDGE)
    parser.add_argument("--label", action="store_true", help="explicitly enable incremental API labeling")
    parser.add_argument("--max-calls", type=int, default=20, help="maximum successful judge batches")
    parser.add_argument("--output-dir", type=Path, default=OUT)
    args = parser.parse_args(argv)
    if args.max_calls < 0:
        parser.error("--max-calls must be nonnegative")
    papers, queries, split = judge.load_inputs()
    qids = sorted(split["dev"])
    runs, configs, provenance = prepare(papers, qids)
    pairs = graded.pooled_pairs(runs, qids)
    source_labels = json.loads((config.EVAL_DIR / "labels.json").read_text(encoding="utf-8"))
    human = graded.read_human_grades()
    missing_human = {q: [p for p in ids if (q, p) not in human] for q, ids in pairs.items()}
    cached_labels, _ = graded.merged_labels(pairs, queries, papers, human, args.judge)
    total = sum(map(len, pairs.values()))
    covered = sum(p in cached_labels[q] for q, ids in pairs.items() for p in ids)
    print(f"Shared pool: {total} pairs; {covered} cached/human covered; "
          f"{total - covered} missing before labeling.", flush=True)
    try:
        if args.label and args.max_calls:
            print(judge.judge_pairs(args.judge, missing_human, queries, papers,
                                    max_calls=args.max_calls), flush=True)
    finally:
        labels, overrides = graded.merged_labels(pairs, queries, papers, human, args.judge)
        publish(runs, configs, provenance, labels, pairs, queries, source_labels,
                overrides, args.judge, args.output_dir)
        print(f"Published {len(runs)} systems to {args.output_dir}; "
              "see report.md / report.json (comparisons require complete coverage).")


if __name__ == "__main__":
    main()
