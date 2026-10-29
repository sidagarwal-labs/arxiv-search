# Fixed-candidate field score experiment

Dev only; body = abstract. Frozen labels and human overrides unchanged. No paid calls or heldout evaluation. No promotion.

Seven prespecified configurations; all reorder exactly the Decision36 top100. Score = 75% baseline reciprocal rank (31/(30+r)) + 25% field evidence. Lexical: full-corpus independent BM25 exact+stems k1=.8/b=.75, candidate-max normalization; 10% author + 90% weighted title/abstract. Semantic: same local GTE model for concat and separate fields, normalized cosine mapped to [0,1].

Model: `thenlper/gte-small` revision `17e1f347d17fe144873b1201da91788898c639cd`; CPU float32, <=4 torch threads.

Runtime: `{"cached_texts": 20604, "cumulative_total_seconds": 4410.056, "encoded_texts": 2428, "lexical_seconds": 11.376, "max_tokens": 512, "prior_invocations": 3, "prior_total_seconds": 3768.08, "semantic_seconds": 582.608, "semantic_status": "completed", "torch_threads": 4, "total_seconds": 641.976}`

Missing distinct top10 judgments: **1**. Graded means are provisional where incomplete; graded paired intervals withheld. Source metrics remain valid.

| System | nDCG@10 | P@10 | Judged@10 | Source MRR@10 | R@10 | R@20 | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| field-gte-concat | 0.717568 | 0.689000 | 1.000000 | 0.696734 | 0.860000 | 0.890000 | covered |
| field-gte-separate+t=0.25 | 0.717568 | 0.689000 | 1.000000 | 0.696734 | 0.860000 | 0.890000 | covered |
| field-gte-separate+t=0.5 | 0.717568 | 0.689000 | 1.000000 | 0.696734 | 0.860000 | 0.890000 | covered |
| field-gte-separate+t=0.75 | 0.717568 | 0.689000 | 1.000000 | 0.696734 | 0.860000 | 0.890000 | covered |
| field-lexical+t=0.25 | 0.705606 | 0.686000 | 1.000000 | 0.669734 | 0.850000 | 0.880000 | covered |
| field-lexical+t=0.5 | 0.696032 | 0.682000 | 0.999000 | 0.646607 | 0.850000 | 0.870000 | PROVISIONAL |
| field-lexical+t=0.75 | 0.680029 | 0.674000 | 0.999000 | 0.606417 | 0.840000 | 0.880000 | PROVISIONAL |
| fusion-shortlist+a=1+d=500 | 0.717568 | 0.689000 | 1.000000 | 0.696734 | 0.860000 | 0.890000 | covered |

## Segment and target changes

Per-query and query-type metrics, source paired intervals, and all lost/gained source/known-item rank changes are in report.json. Missing pairs are explicitly listed in missing-judgments.json; no new grades were inferred.

## Interpretation boundary

The semantic comparison tests a conservative 25% additional signal, not pure semantic ranking or retriever recall. Inspect top10-order-change counts before interpreting equal metrics: an unchanged top10 is no observable intervention at the primary cutoff, not evidence that separate field representations are useless. Same-model concat comparisons are recorded separately in report.json.

## Completion

Incomplete configurations: [].
Embedding shards are resumable and validate model/revision, ordered IDs, exact text hashes, dtype, finite values, shape, and unit norms.
