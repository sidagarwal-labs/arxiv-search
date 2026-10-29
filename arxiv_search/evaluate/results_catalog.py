"""Offline catalog of saved dev rankings, rescored against one frozen label pool.

No system registry, judge cache, or historical summary supplies scores here. An
explicit additive score-fusion snapshot may expand the shared denominator, but
must preserve every original grade, including frozen human overrides.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from urllib.parse import quote

from arxiv_search import config
from arxiv_search.evaluate import graded, judge, metrics

RUN_FOLDERS = ("dev", "fusion-dev", "fusion-review-dev", "score-fusion-dev", "refinement-dev")
QUERY_TYPES = ("keyword", "question", "paraphrase", "known_item")
FIELDS = ("ndcg@10", "precision@10", "judged@10", "source_mrr@10",
          "source_recall@1", "source_recall@5", "source_recall@10", "source_recall@20")


def _fingerprint(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def load_snapshot(root: Path) -> tuple[Path, bytes, dict, dict]:
    """Prefer the approved expansion, failing closed on incompatible snapshots."""
    original_path = root / "fusion-dev" / "labels.json"
    original_raw = original_path.read_bytes()
    original = json.loads(original_raw)
    expanded_path = root / "score-fusion-dev" / "labels.json"
    original_pairs = sum(len(grades) for grades in original["labels"].values())
    provenance = {
        "original_snapshot": "fusion-dev/labels.json",
        "original_snapshot_sha256": hashlib.sha256(original_raw).hexdigest(),
        "original_pairs": original_pairs, "added_pairs": 0,
        "frozen_human_overrides": original.get("human_overrides"),
        "denominator_revised": False,
    }
    if not expanded_path.exists():
        return original_path, original_raw, original, provenance
    raw = expanded_path.read_bytes()
    expanded = json.loads(raw)
    if not isinstance(expanded, dict):
        raise ValueError("Expanded label snapshot must be an object")
    for field in ("judge", "model", "rubric_version", "query_ids", "human_workbook_sha256"):
        if field not in original or field not in expanded or expanded[field] != original[field]:
            raise ValueError(f"Expanded label snapshot has incompatible {field}")
    if type(expanded.get("complete")) is not bool:
        raise ValueError("Expanded label snapshot requires boolean complete")
    labels = expanded.get("labels")
    if not isinstance(labels, dict) or set(labels) != set(original["labels"]):
        raise ValueError("Expanded label snapshot must preserve exactly the original query IDs")
    for qid, grades in original["labels"].items():
        added = labels[qid]
        if not isinstance(added, dict):
            raise ValueError(f"Expanded label snapshot has invalid labels for {qid}")
        if any(pid not in added or type(added[pid]) is not int or added[pid] != grade
               for pid, grade in grades.items()):
            raise ValueError(f"Expanded label snapshot changed or removed original grade: {qid}")
    added_pairs = sum(len(grades) for grades in labels.values()) - original_pairs
    if added_pairs <= 0:
        raise ValueError("Expanded label snapshot must be a strict additive extension")
    if ("human_overrides" in expanded
            and expanded["human_overrides"] != original.get("human_overrides")):
        raise ValueError("Expanded label snapshot changed human_overrides")
    provenance.update(added_pairs=added_pairs, denominator_revised=True)
    return expanded_path, raw, expanded, provenance


def discover_runs(root: Path) -> dict:
    """Deduplicate by filename identity, refusing conflicting saved rankings."""
    found = {}
    for folder in RUN_FOLDERS:
        for path in sorted((root / folder).glob("*.run.json")):
            name = path.name.removesuffix(".run.json")
            run = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(run, dict):
                raise ValueError(f"{path}: expected a query-to-ranking mapping")
            relative = path.relative_to(root).as_posix()
            if name in found:
                if found[name]["run"] != run:
                    raise ValueError(f"Conflicting duplicate rankings for {name}: "
                                     f"{found[name]['paths'][0]} and {relative}")
                found[name]["paths"].append(relative)
            else:
                found[name] = {"run": run, "paths": [relative], "metadata": {}}
            info = path.with_name(f"{name}.info.json")
            if info.exists():
                found[name]["metadata"][info.relative_to(root).as_posix()] = json.loads(
                    info.read_text(encoding="utf-8"))
    return found


def _summary(rows: list[dict]) -> dict:
    result = {"queries": len(rows)}
    for field in FIELDS:
        values = [row[field] for row in rows if row[field] is not None]
        result[field] = {"mean": sum(values) / len(values) if values else None,
                         "n": len(values)}
    return result


def score_catalog(runs: dict, snapshot: dict, papers: dict, queries: dict,
                  dev_ids: list[str], baseline: str) -> dict:
    """Score only dev, using exactly the same frozen labels for every run."""
    qids = sorted(dev_ids)
    if not qids or len(qids) != len(set(qids)):
        raise ValueError("Expected unique, nonempty dev query IDs")
    labels = snapshot["labels"]
    if set(labels) != set(qids) or set(snapshot.get("query_ids", qids)) != set(qids):
        raise ValueError("Frozen snapshot must contain exactly the dev queries")
    for qid, grades in labels.items():
        if qid not in queries or queries[qid]["query_type"] not in QUERY_TYPES:
            raise ValueError(f"Unknown query or query type: {qid}")
        if any(pid not in papers or type(grade) is not int or grade not in (0, 1, 2)
               for pid, grade in grades.items()):
            raise ValueError(f"Invalid frozen labels: {qid}")
    source_labels = {q: {queries[q]["source_arxiv_id"]: 2} for q in qids}
    if any(next(iter(grades)) not in papers for grades in source_labels.values()):
        raise ValueError("Source paper absent from current corpus")
    systems = {}
    for name in sorted(runs):
        entry = runs[name]
        run = entry["run"]
        if set(run) - set(qids):
            raise ValueError(f"{name}: rankings contain non-dev query IDs")
        for qid, ids in run.items():
            if (not isinstance(ids, list) or any(not isinstance(p, str) for p in ids)
                    or len(ids) != len(set(ids)) or set(ids) - set(papers)):
                raise ValueError(f"{name}/{qid}: invalid, duplicate, or unknown paper IDs")
        # Both scorers iterate the entire frozen dev set, including missing rankings.
        graded_rows = {r["query_id"]: r for r in graded.score_graded(run, labels, queries)}
        rows = []
        for source in metrics.score_run(run, source_labels):
            qid = source["query_id"]
            rows.append({
                **graded_rows[qid],
                "source_mrr@10": source["mrr@10"],
                **{f"source_recall@{k}": source[f"recall@{k}"] for k in (1, 5, 10, 20)},
            })
        complete = all(len(run.get(q, [])) >= 10
                       and all(p in labels[q] for p in run[q][:10]) for q in qids)
        systems[name] = {
            "paths": entry["paths"], "metadata": entry["metadata"],
            "ranking_sha256": _fingerprint(run), "working_baseline": name == baseline,
            "queries_present": len(run), "queries_expected": len(qids),
            "top10_fully_judged": complete,
            "status": "covered" if complete else "PROVISIONAL",
            "all": _summary(rows),
            "by_query_type": {kind: _summary([r for r in rows if r["query_type"] == kind])
                              for kind in QUERY_TYPES},
            "known_item_source_mrr@10": _summary([
                r for r in rows if r["query_type"] == "known_item"])["source_mrr@10"],
            "per_query": rows,
        }
    control = systems.get(baseline)
    for name, result in systems.items():
        result["paired_ndcg_vs_working_baseline"] = None
        if control is None:
            reason = "working baseline ranking is missing"
        elif not control["top10_fully_judged"] or not result["top10_fully_judged"]:
            reason = "both runs must have all dev top-10 positions present and judged"
        elif name == baseline:
            reason = "working baseline itself"
        else:
            left = {r["query_id"]: r["ndcg@10"] for r in control["per_query"]}
            right = {r["query_id"]: r["ndcg@10"] for r in result["per_query"]}
            paired_ids = [q for q in qids if left[q] is not None and right[q] is not None]
            if paired_ids:
                mean, low, high = metrics.paired_diff_ci(
                    [left[q] for q in paired_ids], [right[q] for q in paired_ids])
                result["paired_ndcg_vs_working_baseline"] = {
                    "difference": mean, "ci95": [low, high], "query_ids": paired_ids,
                    "n": len(paired_ids),
                }
                reason = None
            else:
                reason = "no queries with defined nDCG"
        result["paired_withheld_reason"] = reason
    return systems


def _link(path: Path, base: Path) -> str:
    return quote(Path(os.path.relpath(path, base)).as_posix(), safe="/")


def _value(summary: dict, field: str) -> str:
    value = summary[field]["mean"]
    return "undefined (n=0)" if value is None else f"{value:.3f}"


def _table(systems: dict) -> str:
    lines = [
        "| System | Status | nDCG@10 (n) | P@10 | judged@10 | Source MRR@10 | "
        "R@1 | R@5 | R@10 | R@20 | Known-item MRR@10 | Δ nDCG vs working baseline [95% CI] |",
        "|" + "---|" * 12,
    ]
    for name in sorted(systems, key=lambda n: (not systems[n]["working_baseline"], n)):
        result = systems[name]
        summary = result["all"]
        title = f"**`{name}` (WORKING BASELINE)**" if result["working_baseline"] else f"`{name}`"
        ndcg = f"{_value(summary, 'ndcg@10')} ({summary['ndcg@10']['n']})"
        cells = [title, result["status"], ndcg]
        cells += [_value(summary, field) for field in FIELDS[1:]]
        known = result["known_item_source_mrr@10"]["mean"]
        cells.append(f"{known:.3f}" if known is not None else "undefined (n=0)")
        paired = result["paired_ndcg_vs_working_baseline"]
        cells.append(f"{paired['difference']:+.3f} "
                     f"[{paired['ci95'][0]:+.3f}, {paired['ci95'][1]:+.3f}]"
                     if paired else f"withheld: {result['paired_withheld_reason']}")
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_catalog() -> str:
    """Persist deterministic catalog reports and return the near-top docs section."""
    root = config.RESULTS_DIR
    out = root / "catalog-dev"
    snapshot_path = root / "fusion-dev" / "labels.json"
    if not snapshot_path.exists():
        if (root / "score-fusion-dev" / "labels.json").exists():
            raise ValueError("Cannot validate expanded labels without original fusion-dev snapshot")
        return ('<a id="unified-dev-scorecard"></a>\n\n'
                "## Unified all-experiment dev scorecard\n\n"
                "Unavailable: frozen `fusion-dev/labels.json` has not been saved yet.")
    snapshot_path, raw_snapshot, snapshot, provenance = load_snapshot(root)
    papers, queries, splits = judge.load_inputs()
    if set(splits["dev"]) & set(splits["test"]):
        raise ValueError("Dev/test query overlap")
    systems = score_catalog(discover_runs(root), snapshot, papers, queries,
                            splits["dev"], config.WORKING_BASELINE_SYSTEM)
    out.mkdir(parents=True, exist_ok=True)
    inventory = sorted({
        path for path in root.rglob("*")
        if path.is_file() and "catalog-dev" not in path.relative_to(root).parts
        and (path.name in ("report.json", "report.md", "configs.json")
             or path.parent == root / "dev" / "tuning")
    })
    report = {
        "scope": "dev only; full current corpus; saved rankings; no retrieval or API calls",
        "working_baseline": config.WORKING_BASELINE_SYSTEM,
        "corpus_papers": len(papers), "corpus_sha256": _fingerprint(papers),
        "dev_queries": len(splits["dev"]),
        "dev_queries_sha256": _fingerprint({q: queries[q] for q in sorted(splits["dev"])}),
        "label_snapshot": snapshot_path.relative_to(root).as_posix(),
        "label_snapshot_sha256": hashlib.sha256(raw_snapshot).hexdigest(),
        "label_snapshot_provenance": provenance,
        "human_overrides": provenance["frozen_human_overrides"],
        "human_workbook_sha256": snapshot.get("human_workbook_sha256"),
        "judge": snapshot.get("judge"), "model": snapshot.get("model"),
        "rubric_version": snapshot.get("rubric_version"),
        "graded_labels_sha256": _fingerprint(snapshot["labels"]),
        "inventory": [p.relative_to(root).as_posix() for p in inventory],
        "systems": systems,
    }
    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                                    encoding="utf-8")
    caveats = (
        f"{len(systems)} distinct saved systems; {len(splits['dev'])} dev queries; "
        f"current corpus: {len(papers):,} papers. **Working baseline: "
        f"`{config.WORKING_BASELINE_SYSTEM}`**. Rows are alphabetical after the baseline, "
        "not a winner ranking.\n\n"
        f"All graded scores are recomputed from the **same immutable "
        f"`{report['label_snapshot']}`**, "
        f"including its {report['human_overrides']} frozen human overrides. "
        + (f"**Revised shared ideal-DCG denominator:** approved additive expansion preserves "
           f"all {provenance['original_pairs']} original labels and adds "
           f"{provenance['added_pairs']} labels. Every system is rescored against this "
           "expanded denominator; original reports remain unchanged and their nDCG values "
           "must not be mixed with these revised scores. "
           if provenance["denominator_revised"] else
           "The original frozen fusion-dev denominator is unchanged. ")
        +
        "Other report scores/label pools and later judge-cache or workbook changes are NOT "
        "combined. Linear-gain nDCG@10 uses that shared ideal DCG; undefined queries are "
        "excluded only from nDCG (n shown). P@10 counts grades ≥1 with denominator 10. "
        "Unjudged gains count as zero. judged@10 is the judged fraction of returned results; "
        "short/missing lists still fail the full top-10 coverage gate.\n\n"
        "**PROVISIONAL** means a dev top-10 position is missing or unjudged: source-paper "
        "MRR/recall remain valid on the full dev denominator (missing queries score zero), "
        "but graded scores are lower-bound diagnostics, not winner evidence. Paired nDCG "
        "against the CURRENT working baseline is withheld unless BOTH runs have every dev "
        "top-10 position judged. Intervals are exploratory query bootstraps conditional on "
        "these labels, not judge accuracy; no multiple-testing correction or test-query "
        "scoring. Known-item MRR is source-paper MRR on that type only.\n\n"
        "**Snapshot/corpus caveat:** these are saved rankings, not fresh retrieval. Current "
        "corpus and dev-query fingerprints, the frozen label SHA256, ranking fingerprints, "
        "and all duplicate paths are recorded in the machine report. Older runs may not "
        "record a corpus fingerprint; matching paper IDs cannot prove identical build "
        "snapshots. Reduced-corpus embedding pilots are a separate scope, never scorecard "
        "rows. Costs/latencies are not estimated or assigned zero: only actually saved "
        "`.info.json` metadata is preserved per system, with its original timing scope. "
        "Historical reports retain their original labels, denominators, and controls."
    )
    table = _table(systems) if systems else "_No saved dev rankings._"
    inventory_lines = []
    for path in inventory:
        relative = path.relative_to(root).as_posix()
        scope = (" — reduced-corpus embedding pilot, separate scope" if
                 "embedding-pilot" in relative else
                 " — BM25 tuning, source-paper objective" if "/tuning/" in relative else
                 " — historical report/configuration; original scope")
        inventory_lines.append(f"- [{relative}]({_link(path, out)}){scope}")
    lines = ["# Unified all-experiment dev catalog", "", caveats, "", table, "",
             "## Every run by query type", "",
             "| System | Type | Queries | nDCG@10 (n) | P@10 | judged@10 | "
             "Source MRR@10 | R@1 | R@5 | R@10 | R@20 |",
             "|" + "---|" * 11]
    for name, result in systems.items():
        for kind, summary in result["by_query_type"].items():
            cells = [f"`{name}`", kind, str(summary["queries"]),
                     f"{_value(summary, 'ndcg@10')} ({summary['ndcg@10']['n']})"]
            cells += [_value(summary, field) for field in FIELDS[1:]]
            lines.append("| " + " | ".join(cells) + " |")
    lines += ["", "## Report inventory (separate historical scopes)", "", *inventory_lines]
    (out / "report.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    docs = config.PROJECT_ROOT / "docs"
    docs_inventory = [
        f"- [{p.relative_to(root).as_posix()}]({_link(p, docs)})" for p in inventory
    ]
    return "\n\n".join([
        '<a id="unified-dev-scorecard"></a>\n\n## Unified all-experiment dev scorecard',
        caveats, table,
        f"[Per-type results for EVERY run]({_link(out / 'report.md', docs)}) · "
        f"[Machine report, coverage, provenance and saved timing/cost metadata]"
        f"({_link(out / 'report.json', docs)}) · "
        f"[Frozen labels]({_link(snapshot_path, docs)})",
        "### Report inventory (historical / separate scopes)",
        "\n".join(docs_inventory) or "_No additional reports._",
    ])
