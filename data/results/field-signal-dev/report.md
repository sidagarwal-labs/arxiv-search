# Pure semantic field ordering within Decision36 top10

Follow-up to conservative field-score-dev semantic top10 no-op; remove base-rank dominance. Post-outcome exploratory, not confirmatory.

Sort Decision36 top10 by descending field signal only; stable baseline ties; preserve tail exactly. No query/label-dependent routing.

Concat: (cos(q,title+space+abstract)+1)/2; separate: (t*cos(q,title)+(1-t)*cos(q,abstract)+1)/2

All top10 positions fully judged against unchanged frozen labels/human overrides. Source R@10/R@20 invariant by construction; ordering/MRR and nDCG can change. Cached scores only: no inference or paid calls.

| System | nDCG@10 | P@10 | Source MRR@10 | R@1 | Grade0 first | ΔnDCG / 95% CI |
|---|---:|---:|---:|---:|---:|---|
| field-order-gte-concat | 0.705739 | 0.689000 | 0.621635 | 0.510000 | 7 | -0.011830 [-0.023537, -0.000186] |
| field-order-gte-separate+t=0.25 | 0.703778 | 0.689000 | 0.620718 | 0.510000 | 8 | -0.013791 [-0.025891, -0.002046] |
| field-order-gte-separate+t=0.5 | 0.695170 | 0.689000 | 0.598790 | 0.480000 | 9 | -0.022399 [-0.035476, -0.009794] |
| field-order-gte-separate+t=0.75 | 0.676682 | 0.689000 | 0.526944 | 0.390000 | 14 | -0.040886 [-0.056188, -0.025517] |
| fusion-shortlist+a=1+d=500 | 0.717568 | 0.689000 | 0.696734 | 0.610000 | 4 | control |

Query-type metrics, paired comparisons to same-model concat, known-item rank changes, grade0 gained/removed cases, and all per-query metrics are in report.json.

Model `thenlper/gte-small`, revision `17e1f347d17fe144873b1201da91788898c639cd`. Cache-only runtime 2.034s; original cumulative encoding/experiment runtime 4410.056s. Fingerprints in input-provenance.json.

No automatic promotion. Follow-up selection is post-outcome exploratory.
