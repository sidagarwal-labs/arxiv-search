# Experiment D: requirement checklist reranker (pilot stage)

Reference: `llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30` (Decision46). Primary: cap 2 for papers missing a required facet; secondary: same responses, no cap. Pilot gate only: a sanity screen, not evidence.

| System | nDCG@10 | pilot20 Δ | Source MRR@10 | R@1 | P@10 | Passes |
|---|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.6904 | -0.0603 [-0.0988, -0.0208] | 0.8375 | 80% | 0.675 | — |
| `llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30` | 0.7508 | — | 0.8625 | 85% | 0.750 | — |
| `llm-mini-facet-score+d=50+cap=2+avg2+rrf-baseline+c=30` | 0.7278 | -0.0230 [-0.0634, +0.0149] | 0.7833 | 75% | 0.740 | no (pilot20_ndcg_gain, pilot20_source_mrr) |
| `llm-mini-facet-score+d=50+avg2+rrf-baseline+c=30` | 0.7317 | -0.0191 [-0.0600, +0.0187] | 0.8167 | 80% | 0.740 | no (pilot20_ndcg_gain, pilot20_source_mrr) |

## nDCG@10 by query type (diagnostic only)

| System | keyword | question | paraphrase | known_item |
|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.7104 | 0.7211 | 0.6503 | 0.6800 |
| `llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30` | 0.7436 | 0.8197 | 0.7300 | 0.7099 |
| `llm-mini-facet-score+d=50+cap=2+avg2+rrf-baseline+c=30` | 0.7572 | 0.7501 | 0.6923 | 0.7115 |
| `llm-mini-facet-score+d=50+avg2+rrf-baseline+c=30` | 0.7567 | 0.7663 | 0.6923 | 0.7115 |

## Checklist diagnostics

- Facets per query: {2: 8, 3: 11, 4: 1}.
- Paper-passes with any missing facet: 97.2%; capped (score above 2 and a missing facet): 0.5%.
- Source paper flagged as missing a facet: 17/36 paper-passes (evaluation-only error proxy; the source should meet every requirement).
- Grade-0 papers in the top10: `fusion-shortlist+a=1+d=500` 65, `llm-mini-score-pilot+d=50+avg2+rrf-baseline+c=30` 50, `llm-mini-facet-score+d=50+cap=2+avg2+rrf-baseline+c=30` 52, `llm-mini-facet-score+d=50+avg2+rrf-baseline+c=30` 52.

<details><summary>Extracted facets per query</summary>

- `q-keyword-005`: reinforcement learning; self-play; strategy games
- `q-keyword-008`: LLM logical rules; time series causality
- `q-keyword-017`: linear time; long context recall
- `q-keyword-079`: regional language; social media
- `q-keyword-081`: LLM popularity prediction; recommendation
- `q-known_item-017`: Yang GraDE; frequent subgraph discovery
- `q-known_item-019`: AI alignment; sociodemographic; Shani-Narkiss
- `q-known_item-031`: Boyd; clinical provenance categorization
- `q-known_item-042`: Jiang; personalized dense retrieval; reasoning
- `q-known_item-048`: music graph recommendation; Ziaoddini
- `q-paraphrase-020`: reducing data exchange; avoiding error signal propagation; shared neural architectures
- `q-paraphrase-043`: identify speaker's mood; previous chat turns needed; role of sentence starters
- `q-paraphrase-063`: grade science tests; network of reference answers; one paragraph for several questions
- `q-paraphrase-077`: low precision training; distributed private devices; speeding up training; comprehensive look
- `q-paraphrase-096`: find relevant text chunks; hierarchy of summaries; connect search terms and documents
- `q-question-040`: use tool specifications; create synthetic test cases; for AI agents
- `q-question-056`: LLM suggests new experiments; materials science; without training a model
- `q-question-077`: standard graph neural networks; link prediction; unknown knowledge graphs
- `q-question-088`: LLM agents; reuse specific workflows from previous tasks; avoid forgetting
- `q-question-095`: single general-purpose model; various atmospheric science tasks

</details>

## Cost

- Extraction: 20 requests, $0.0054.
- Scoring: 40 requests, $0.6986 (uncached prices; caching may lower the bill).
- Judge: $0.0007.

## Cautions

- Dev only; the judge and reranker share a model family.
- The loss analysis that motivated this experiment read dev queries.
- Not promoted.
