# Experiment provenance and retention

This is the evidence contract for development and recurring maintenance, not a
claim that every historical experiment already records every field.
Start with the [current system](../README.md) and [experiment log](07-experiment-log.md).

## Minimum experiment record

Reuse existing run metadata, preregistrations and accounting rather than creating
a second competing source of truth. If a field was not recorded, say so; do not
retroactively present an exploratory plan as preregistered.

| Field | What readers should be able to verify |
|---|---|
| Question and hypothesis | What changed, why it might help, and the control |
| Identity | Stable experiment/system ID, code revision and run date |
| Inputs | Corpus identity/hash, query split and counts, candidate provenance |
| Configuration | Model snapshot/revision, dimensions, text fields, depths, weights, seeds and tie handling |
| Labels | Judge/model identity, prompt/rubric version, snapshot/hash, overrides and missing judgments |
| Outcome | Source metrics and graded metrics; cutoffs, aggregation and judgment coverage |
| Comparison | Same corpus, queries and label snapshot; paired deltas and uncertainty |
| Reliability | Failures, retries, missing rankings and stochastic repeatability |
| Resources | Actual versus estimated cost, token usage, elapsed time and cached versus uncached measurement |
| Decision | Adopted, rejected, pending or diagnostic; tradeoffs and next hypothesis |
| Reproduction | Exact command, required local artifacts and whether execution can spend money |

Never compare a pilot directly with a full-corpus run, or scores on different
label snapshots as if only the ranking changed. A larger judgment pool can change
nDCG's ideal denominator without changing rankings. Keep historical reports
scoped to their original inputs; unified reports must state their rescoring layer.

Repeated dev selection and synthetic queries limit generalization claims.
Report negative results, selection uncertainty and judge/reranker model-family
bias alongside improvements. An oracle using labels is a diagnostic, not a model.

## Retention classes

| Class | Examples | Default action |
|---|---|---|
| Irreplaceable evidence | Frozen queries/splits, human/model grades, paid responses, plans and accounting | Keep immutable, with provenance |
| Historical experiment evidence | Rankings, raw scores, configurations, failure cases and rejected controls | Keep; label historical or superseded |
| Derived presentation | Catalogs, charts and reports rebuilt from retained inputs | Regenerate through the owning generator; do not hand-edit |
| Rebuildable local artifacts | Virtual environments, indexes and document vectors | Keep outside git where existing policy permits; verify reproducibility before proposing removal |
| Temporary artifacts | Scratch diagnostics and caches with no remaining consumers | Propose exact paths after checking dependencies and active work |

Being reproducible does not mean being free to reproduce: retain paid caches.
Moving files can break generators or links; leaving historical evidence in place
with better navigation is often safer than physical archiving.

## Maintenance review record

Each proposal should name the inspected revision, active development handoff,
exact paths, evidence of staleness/duplication, replacement or archive location,
dependent links/generators, user approval and validation. Record uncertainties
explicitly. Never remove evidence just to reduce repository size.

Prefer concise summaries linking detailed artifacts. Before adding an automation
tool, check existing generators/tests and prove it can audit without inference,
held-out evaluation or writes. This policy does not introduce a new automated
deletion job or a requirement to rerun every experiment.

## Offline presentation refresh

From the repository root, after an approved handoff:

```powershell
# Rebuild the results page and catalog from saved evidence; no model calls.
.\.venv\Scripts\python.exe -c "from arxiv_search.evaluate.experiments import write_results_doc; write_results_doc()"

# Only when chart regeneration is part of the approved scope:
.\.venv\Scripts\python.exe -m arxiv_search.evaluate.baseline_promotion

# Focused generator checks:
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests\test_results_catalog.py tests\test_baseline_promotion.py
```

These commands write derived presentation files; they are not read-only audit
commands. Inspect their diff and confirm frozen evidence and numeric leaderboard
values remain unchanged when the intended change is presentation only.
