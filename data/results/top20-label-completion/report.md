# D47 top20 label completion

Evaluator: Copilot SDK AI assistants (subagent model versions not exposed).
Collection: AI-assisted judgments via Copilot SDK in VS Code; not human labels..

99 new judgments: {1: 77, 0: 19, 2: 3}

| Counterfactual | Original D47 labels | Completed top20 labels |
|---|---:|---:|
| actual | 0.7939 | 0.7886 |
| oracle10 | 0.8394 | 0.8337 |
| oracle20 | 0.9498 | 0.9524 |
| oracle50 | 0.9803 | 0.9805 |
| ideal | 1.0000 | 1.0000 |

- No model version inferred beyond workbook provenance.
- Mixed evaluator pool; new labels do not establish grader agreement.
- No existing labels, frozen reports, catalog or baseline changed.
