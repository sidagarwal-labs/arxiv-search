# Repository working rules

## Purpose

Show the learning behind an end-to-end search system: ingestion, indexing,
embeddings, query processing, ranking, reranking, evaluation, and eventually
LLM answers and UI/UX. Prefer reproducible evidence and honest tradeoffs to a
larger leaderboard or unsupported claims. Planned features are not shipped features.

## Development

- Inspect existing code, tests, decisions and saved evidence before changing behavior.
- Use general rules, not query IDs, source-paper identities, relevance labels or
  dev-specific exceptions in retrieval or reranking.
- Tune on dev only. Do not inspect held-out query content or run the held-out test
  as part of maintenance. Final evaluation requires explicit user approval.
- Baseline promotion is a separate decision, not an automatic consequence of a
  leaderboard lead. Record scope, paired comparisons, uncertainty, regressions,
  coverage, cost and reliability; preserve the historical controls.
- No paid inference, labeling, re-embedding, cache repair or budget increase
  without explicit approval. Maintenance is read-only/offline by default.
- Never publish credentials, environment files, private account information or
  restricted paper content. Check public artifacts before committing them.

## Recurring maintenance: "Run arXiv maintenance"

The maintenance chat owns investigating, implementing and validating maintenance
changes. The development chat owns building and experimentation. Read its recent
context first; ask only for missing context or a narrowly scoped file handoff,
not for implementation, cleanup, report regeneration or testing on maintenance's
behalf. Do not pause all development when only a few shared files need coordination.

1. Inspect git status and the current revision. Consult the active development
   chat for latest decisions, pending promotions, protected files and a safe
   handoff for overlapping files. Do not overwrite concurrent work. Recheck the
   diff before editing or staging; integrate existing edits and stage only owned
   changes. A shared generated output requires coordination with its generator.
2. Investigate documentation freshness, links, duplication, provenance and
   retention. Age alone is not evidence that a file is obsolete.
3. Present exact proposed additions, edits, moves and deletions, with reasons,
   evidence, development-chat feedback, risks and validation.
4. Wait for explicit user approval before repository changes. Development-chat
   approval is coordination evidence, not user authorization. Apply only the
   approved scope; ask again if it materially changes.
5. Verify links, relevant tests and generated output where applicable. Report
   completed changes and deferred work, and return the handoff to development.
   Do not commit or push unless requested.

## Documentation ownership

- README: concise current state, representative results with scope, limitations,
  setup and navigation. Avoid copying the entire experiment history.
- How It Works: architecture and learning tour; label historical explanations.
- Decisions: stable numbered history; mark superseded/planned choices without
  renumbering or breaking existing anchors.
- Findings and experiment log: preserve measurements, failed approaches and
  caveats. Link detailed artifacts instead of repeating them across summaries.
- Results, charts and experiment reports: generated outputs. Change their
  generators and regenerate with approved offline commands; never hand-edit.
- Follow [provenance and retention](docs/08-provenance-and-retention.md) and
  [labeler comparison](docs/09-labeler-comparison.md) for evidence claims.

## Protected evidence

Never silently overwrite or delete frozen queries/splits, human or model labels,
shared label snapshots, prompts/rubric versions, preregistrations, saved rankings,
responses, input provenance or accounting records. Historical experiments may
depend on them even when their configuration was rejected. Generated reports
can be rebuilt, but their underlying evidence must remain intact.

Archive or delete only after identifying dependents and obtaining approval for
the exact paths. Do not rewrite git history as routine cleanup.
