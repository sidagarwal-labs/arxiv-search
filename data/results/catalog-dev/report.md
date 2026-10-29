# Unified all-experiment dev catalog

128 distinct saved systems; 100 dev queries; current corpus: 23,304 papers. **Working baseline: `fusion-rrf+w=0.55+d=100+c=30`**. Rows are alphabetical after the baseline, not a winner ranking.

All graded scores are recomputed from the **same immutable `score-fusion-dev/labels.json`**, including its 100 frozen human overrides. **Revised shared ideal-DCG denominator:** approved additive expansion preserves all 3190 original labels and adds 104 labels. Every system is rescored against this expanded denominator; original reports remain unchanged and their nDCG values must not be mixed with these revised scores. Other report scores/label pools and later judge-cache or workbook changes are NOT combined. Linear-gain nDCG@10 uses that shared ideal DCG; undefined queries are excluded only from nDCG (n shown). P@10 counts grades ≥1 with denominator 10. Unjudged gains count as zero. judged@10 is the judged fraction of returned results; short/missing lists still fail the full top-10 coverage gate.

**PROVISIONAL** means a dev top-10 position is missing or unjudged: source-paper MRR/recall remain valid on the full dev denominator (missing queries score zero), but graded scores are lower-bound diagnostics, not winner evidence. Paired nDCG against the CURRENT working baseline is withheld unless BOTH runs have every dev top-10 position judged. Intervals are exploratory query bootstraps conditional on these labels, not judge accuracy; no multiple-testing correction or test-query scoring. Known-item MRR is source-paper MRR on that type only.

**Snapshot/corpus caveat:** these are saved rankings, not fresh retrieval. Current corpus and dev-query fingerprints, the frozen label SHA256, ranking fingerprints, and all duplicate paths are recorded in the machine report. Older runs may not record a corpus fingerprint; matching paper IDs cannot prove identical build snapshots. Reduced-corpus embedding pilots are a separate scope, never scorecard rows. Costs/latencies are not estimated or assigned zero: only actually saved `.info.json` metadata is preserved per system, with its original timing scope. Historical reports retain their original labels, denominators, and controls.

| System | Status | nDCG@10 (n) | P@10 | judged@10 | Source MRR@10 | R@1 | R@5 | R@10 | R@20 | Known-item MRR@10 | Δ nDCG vs working baseline [95% CI] |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **`fusion-rrf+w=0.55+d=100+c=30` (WORKING BASELINE)** | covered | 0.706 (100) | 0.689 | 1.000 | 0.646 | 0.550 | 0.760 | 0.860 | 0.890 | 0.980 | withheld: working baseline itself |
| `baseline-original-equal-rrf-c10-d100` | covered | 0.660 (100) | 0.633 | 1.000 | 0.653 | 0.560 | 0.800 | 0.840 | 0.900 | 0.980 | -0.046 [-0.062, -0.031] |
| `bm25+authors` | PROVISIONAL | 0.497 (100) | 0.482 | 0.854 | 0.523 | 0.470 | 0.600 | 0.670 | 0.710 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25+authors+title2x` | PROVISIONAL | 0.493 (100) | 0.476 | 0.866 | 0.534 | 0.480 | 0.620 | 0.670 | 0.700 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25+exact+stems` | PROVISIONAL | 0.512 (100) | 0.507 | 0.911 | 0.521 | 0.440 | 0.650 | 0.700 | 0.730 | 0.873 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25+exact+stems+authors` | PROVISIONAL | 0.518 (100) | 0.509 | 0.937 | 0.557 | 0.510 | 0.650 | 0.700 | 0.730 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25+exact+stems+authors+title2x` | PROVISIONAL | 0.516 (100) | 0.508 | 0.956 | 0.560 | 0.500 | 0.670 | 0.710 | 0.730 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | covered | 0.519 (100) | 0.512 | 1.000 | 0.569 | 0.510 | 0.660 | 0.710 | 0.710 | 1.000 | -0.188 [-0.226, -0.151] |
| `bm25+exact+stems+title2x` | PROVISIONAL | 0.519 (100) | 0.518 | 0.934 | 0.545 | 0.470 | 0.670 | 0.710 | 0.720 | 0.940 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25+stem` | PROVISIONAL | 0.470 (100) | 0.433 | 0.749 | 0.492 | 0.400 | 0.610 | 0.700 | 0.730 | 0.748 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25+stem+authors` | PROVISIONAL | 0.477 (100) | 0.437 | 0.762 | 0.544 | 0.480 | 0.630 | 0.690 | 0.730 | 0.960 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25+stem+authors+title2x` | PROVISIONAL | 0.486 (100) | 0.452 | 0.792 | 0.549 | 0.490 | 0.630 | 0.700 | 0.730 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25+stem+title2x` | PROVISIONAL | 0.478 (100) | 0.446 | 0.763 | 0.512 | 0.430 | 0.630 | 0.720 | 0.730 | 0.830 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25+stop` | PROVISIONAL | 0.488 (100) | 0.475 | 0.809 | 0.501 | 0.430 | 0.600 | 0.680 | 0.700 | 0.907 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25+stop+authors` | PROVISIONAL | 0.496 (100) | 0.481 | 0.831 | 0.525 | 0.470 | 0.610 | 0.680 | 0.700 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25+stop+authors+title2x` | PROVISIONAL | 0.497 (100) | 0.478 | 0.849 | 0.530 | 0.470 | 0.610 | 0.680 | 0.700 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25+stop+exact+stems` | PROVISIONAL | 0.511 (100) | 0.508 | 0.894 | 0.516 | 0.430 | 0.650 | 0.710 | 0.730 | 0.873 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25+stop+exact+stems+authors` | PROVISIONAL | 0.518 (100) | 0.513 | 0.918 | 0.547 | 0.490 | 0.650 | 0.700 | 0.730 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25+stop+exact+stems+authors+title2x` | PROVISIONAL | 0.522 (100) | 0.515 | 0.936 | 0.559 | 0.500 | 0.650 | 0.700 | 0.730 | 1.000 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25+stop+exact+stems+title2x` | PROVISIONAL | 0.519 (100) | 0.515 | 0.912 | 0.544 | 0.470 | 0.660 | 0.710 | 0.730 | 0.940 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25+stop+stem` | PROVISIONAL | 0.474 (100) | 0.441 | 0.742 | 0.492 | 0.400 | 0.590 | 0.700 | 0.730 | 0.746 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25+stop+stem+authors` | PROVISIONAL | 0.485 (100) | 0.448 | 0.760 | 0.550 | 0.490 | 0.610 | 0.690 | 0.730 | 0.960 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25+stop+stem+authors+title2x` | PROVISIONAL | 0.489 (100) | 0.456 | 0.779 | 0.549 | 0.490 | 0.620 | 0.710 | 0.720 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25+stop+stem+title2x` | PROVISIONAL | 0.484 (100) | 0.452 | 0.755 | 0.515 | 0.430 | 0.620 | 0.720 | 0.730 | 0.830 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25+stop+title2x` | PROVISIONAL | 0.496 (100) | 0.482 | 0.831 | 0.519 | 0.450 | 0.610 | 0.690 | 0.700 | 0.940 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25+title2x` | PROVISIONAL | 0.490 (100) | 0.478 | 0.845 | 0.517 | 0.450 | 0.610 | 0.670 | 0.700 | 0.940 | withheld: both runs must have all dev top-10 positions present and judged |
| `bm25-baseline` | PROVISIONAL | 0.488 (100) | 0.472 | 0.823 | 0.501 | 0.430 | 0.610 | 0.670 | 0.700 | 0.907 | withheld: both runs must have all dev top-10 positions present and judged |
| `dense-bge-small` | covered | 0.576 (100) | 0.584 | 1.000 | 0.506 | 0.420 | 0.600 | 0.700 | 0.790 | 0.667 | -0.130 [-0.171, -0.095] |
| `dense-e5-small` | PROVISIONAL | 0.423 (100) | 0.359 | 0.516 | 0.485 | 0.390 | 0.610 | 0.690 | 0.750 | 0.626 | withheld: both runs must have all dev top-10 positions present and judged |
| `dense-gte-small` | covered | 0.581 (100) | 0.581 | 1.000 | 0.525 | 0.430 | 0.660 | 0.710 | 0.780 | 0.633 | -0.125 [-0.164, -0.088] |
| `dense-minilm` | PROVISIONAL | 0.440 (100) | 0.380 | 0.545 | 0.407 | 0.330 | 0.530 | 0.590 | 0.680 | 0.549 | withheld: both runs must have all dev top-10 positions present and judged |
| `dense-openai-large` | covered | 0.644 (100) | 0.637 | 1.000 | 0.599 | 0.500 | 0.740 | 0.820 | 0.880 | 0.793 | -0.063 [-0.091, -0.035] |
| `fusion-linear+w=0.25+d=100` | covered | 0.637 (100) | 0.614 | 1.000 | 0.636 | 0.570 | 0.720 | 0.740 | 0.770 | 0.980 | -0.069 [-0.094, -0.044] |
| `fusion-linear+w=0.25+d=20` | covered | 0.550 (100) | 0.526 | 1.000 | 0.614 | 0.560 | 0.680 | 0.710 | 0.870 | 0.980 | -0.156 [-0.191, -0.121] |
| `fusion-linear+w=0.25+d=50` | covered | 0.589 (100) | 0.557 | 1.000 | 0.618 | 0.560 | 0.690 | 0.720 | 0.750 | 0.980 | -0.117 [-0.149, -0.085] |
| `fusion-linear+w=0.5+d=100` | covered | 0.690 (100) | 0.684 | 1.000 | 0.627 | 0.540 | 0.740 | 0.790 | 0.880 | 0.960 | -0.016 [-0.029, -0.003] |
| `fusion-linear+w=0.5+d=20` | covered | 0.632 (100) | 0.605 | 1.000 | 0.635 | 0.530 | 0.800 | 0.840 | 0.890 | 0.960 | -0.074 [-0.093, -0.056] |
| `fusion-linear+w=0.5+d=50` | covered | 0.673 (100) | 0.652 | 1.000 | 0.633 | 0.540 | 0.750 | 0.830 | 0.900 | 0.960 | -0.033 [-0.047, -0.020] |
| `fusion-linear+w=0.75+d=100` | covered | 0.703 (100) | 0.685 | 1.000 | 0.624 | 0.530 | 0.750 | 0.840 | 0.890 | 0.947 | -0.004 [-0.013, +0.006] |
| `fusion-linear+w=0.75+d=20` | covered | 0.666 (100) | 0.636 | 1.000 | 0.642 | 0.550 | 0.760 | 0.820 | 0.890 | 0.933 | -0.040 [-0.065, -0.017] |
| `fusion-linear+w=0.75+d=50` | covered | 0.686 (100) | 0.664 | 1.000 | 0.632 | 0.530 | 0.780 | 0.870 | 0.890 | 0.947 | -0.020 [-0.037, -0.004] |
| `fusion-rrf+w=0+d=100+c=10` | covered | 0.519 (100) | 0.512 | 1.000 | 0.569 | 0.510 | 0.660 | 0.710 | 0.710 | 1.000 | -0.188 [-0.226, -0.151] |
| `fusion-rrf+w=0.25+d=100+c=10` | covered | 0.569 (100) | 0.557 | 1.000 | 0.602 | 0.540 | 0.680 | 0.730 | 0.780 | 0.980 | -0.137 [-0.171, -0.102] |
| `fusion-rrf+w=0.25+d=100+c=100` | covered | 0.659 (100) | 0.646 | 1.000 | 0.630 | 0.560 | 0.720 | 0.750 | 0.790 | 0.980 | -0.047 [-0.069, -0.025] |
| `fusion-rrf+w=0.25+d=100+c=60` | covered | 0.633 (100) | 0.618 | 1.000 | 0.626 | 0.560 | 0.720 | 0.740 | 0.780 | 0.980 | -0.073 [-0.099, -0.048] |
| `fusion-rrf+w=0.25+d=20+c=10` | covered | 0.558 (100) | 0.538 | 1.000 | 0.605 | 0.550 | 0.680 | 0.710 | 0.710 | 0.980 | -0.148 [-0.183, -0.113] |
| `fusion-rrf+w=0.25+d=20+c=100` | covered | 0.583 (100) | 0.547 | 1.000 | 0.614 | 0.560 | 0.690 | 0.700 | 0.710 | 0.980 | -0.124 [-0.156, -0.090] |
| `fusion-rrf+w=0.25+d=20+c=60` | covered | 0.583 (100) | 0.547 | 1.000 | 0.614 | 0.560 | 0.690 | 0.700 | 0.710 | 0.980 | -0.124 [-0.156, -0.090] |
| `fusion-rrf+w=0.25+d=50+c=10` | covered | 0.568 (100) | 0.555 | 1.000 | 0.603 | 0.540 | 0.680 | 0.730 | 0.760 | 0.980 | -0.138 [-0.172, -0.104] |
| `fusion-rrf+w=0.25+d=50+c=100` | covered | 0.647 (100) | 0.623 | 1.000 | 0.630 | 0.560 | 0.710 | 0.750 | 0.770 | 0.980 | -0.060 [-0.084, -0.036] |
| `fusion-rrf+w=0.25+d=50+c=60` | covered | 0.626 (100) | 0.604 | 1.000 | 0.626 | 0.560 | 0.710 | 0.740 | 0.770 | 0.980 | -0.080 [-0.106, -0.055] |
| `fusion-rrf+w=0.5+d=100+c=10` | covered | 0.660 (100) | 0.633 | 1.000 | 0.653 | 0.560 | 0.800 | 0.840 | 0.900 | 0.980 | -0.046 [-0.062, -0.031] |
| `fusion-rrf+w=0.5+d=100+c=100` | covered | 0.692 (100) | 0.689 | 1.000 | 0.627 | 0.540 | 0.740 | 0.770 | 0.840 | 0.960 | -0.014 [-0.029, +0.001] |
| `fusion-rrf+w=0.5+d=100+c=30` | covered | 0.692 (100) | 0.673 | 1.000 | 0.646 | 0.560 | 0.740 | 0.840 | 0.890 | 0.980 | -0.015 [-0.026, -0.004] |
| `fusion-rrf+w=0.5+d=100+c=60` | covered | 0.695 (100) | 0.689 | 1.000 | 0.626 | 0.540 | 0.740 | 0.780 | 0.870 | 0.960 | -0.011 [-0.025, +0.002] |
| `fusion-rrf+w=0.5+d=20+c=10` | covered | 0.644 (100) | 0.615 | 1.000 | 0.639 | 0.540 | 0.800 | 0.840 | 0.890 | 0.980 | -0.063 [-0.082, -0.044] |
| `fusion-rrf+w=0.5+d=20+c=100` | covered | 0.643 (100) | 0.619 | 1.000 | 0.628 | 0.530 | 0.780 | 0.840 | 0.890 | 0.960 | -0.063 [-0.081, -0.044] |
| `fusion-rrf+w=0.5+d=20+c=60` | covered | 0.644 (100) | 0.619 | 1.000 | 0.627 | 0.530 | 0.780 | 0.840 | 0.890 | 0.960 | -0.063 [-0.081, -0.044] |
| `fusion-rrf+w=0.5+d=50+c=10` | covered | 0.657 (100) | 0.631 | 1.000 | 0.645 | 0.550 | 0.780 | 0.840 | 0.900 | 0.980 | -0.050 [-0.066, -0.035] |
| `fusion-rrf+w=0.5+d=50+c=100` | covered | 0.676 (100) | 0.659 | 1.000 | 0.630 | 0.540 | 0.740 | 0.820 | 0.890 | 0.960 | -0.030 [-0.044, -0.016] |
| `fusion-rrf+w=0.5+d=50+c=60` | covered | 0.678 (100) | 0.660 | 1.000 | 0.630 | 0.540 | 0.740 | 0.830 | 0.890 | 0.960 | -0.028 [-0.042, -0.015] |
| `fusion-rrf+w=0.55+d=100+c=10` | covered | 0.680 (100) | 0.652 | 1.000 | 0.658 | 0.550 | 0.820 | 0.860 | 0.900 | 0.980 | -0.026 [-0.040, -0.014] |
| `fusion-rrf+w=0.55+d=100+c=100` | PROVISIONAL | 0.702 (100) | 0.693 | 0.998 | 0.620 | 0.520 | 0.740 | 0.800 | 0.860 | 0.960 | withheld: both runs must have all dev top-10 positions present and judged |
| `fusion-rrf+w=0.55+d=100+c=60` | covered | 0.704 (100) | 0.695 | 1.000 | 0.627 | 0.530 | 0.740 | 0.820 | 0.870 | 0.960 | -0.003 [-0.012, +0.008] |
| `fusion-rrf+w=0.55+d=200+c=30` | covered | 0.706 (100) | 0.691 | 1.000 | 0.639 | 0.540 | 0.750 | 0.840 | 0.880 | 0.980 | -0.001 [-0.005, +0.004] |
| `fusion-rrf+w=0.55+d=500+c=30` | covered | 0.704 (100) | 0.690 | 1.000 | 0.640 | 0.540 | 0.760 | 0.840 | 0.880 | 0.980 | -0.003 [-0.008, +0.002] |
| `fusion-rrf+w=0.6+d=100+c=10` | covered | 0.687 (100) | 0.661 | 1.000 | 0.655 | 0.540 | 0.820 | 0.870 | 0.890 | 0.953 | -0.020 [-0.034, -0.007] |
| `fusion-rrf+w=0.6+d=100+c=100` | PROVISIONAL | 0.706 (100) | 0.693 | 0.999 | 0.627 | 0.530 | 0.750 | 0.810 | 0.870 | 0.953 | withheld: both runs must have all dev top-10 positions present and judged |
| `fusion-rrf+w=0.6+d=100+c=30` | covered | 0.704 (100) | 0.688 | 1.000 | 0.636 | 0.530 | 0.790 | 0.860 | 0.890 | 0.953 | -0.002 [-0.009, +0.004] |
| `fusion-rrf+w=0.6+d=100+c=60` | covered | 0.710 (100) | 0.700 | 1.000 | 0.630 | 0.530 | 0.760 | 0.830 | 0.870 | 0.953 | +0.003 [-0.005, +0.012] |
| `fusion-rrf+w=0.65+d=100+c=10` | covered | 0.684 (100) | 0.662 | 1.000 | 0.648 | 0.540 | 0.800 | 0.870 | 0.890 | 0.953 | -0.022 [-0.040, -0.005] |
| `fusion-rrf+w=0.65+d=100+c=100` | PROVISIONAL | 0.704 (100) | 0.693 | 0.997 | 0.621 | 0.520 | 0.750 | 0.820 | 0.870 | 0.953 | withheld: both runs must have all dev top-10 positions present and judged |
| `fusion-rrf+w=0.65+d=100+c=30` | covered | 0.703 (100) | 0.685 | 1.000 | 0.640 | 0.540 | 0.780 | 0.850 | 0.890 | 0.953 | -0.003 [-0.013, +0.006] |
| `fusion-rrf+w=0.65+d=100+c=60` | covered | 0.706 (100) | 0.694 | 1.000 | 0.626 | 0.520 | 0.770 | 0.840 | 0.890 | 0.953 | -0.000 [-0.009, +0.008] |
| `fusion-rrf+w=0.7+d=100+c=10` | covered | 0.680 (100) | 0.656 | 1.000 | 0.647 | 0.540 | 0.790 | 0.860 | 0.900 | 0.950 | -0.026 [-0.045, -0.008] |
| `fusion-rrf+w=0.7+d=100+c=100` | PROVISIONAL | 0.707 (100) | 0.695 | 0.997 | 0.618 | 0.520 | 0.740 | 0.840 | 0.870 | 0.947 | withheld: both runs must have all dev top-10 positions present and judged |
| `fusion-rrf+w=0.7+d=100+c=30` | covered | 0.697 (100) | 0.676 | 1.000 | 0.642 | 0.540 | 0.800 | 0.860 | 0.900 | 0.950 | -0.010 [-0.023, +0.003] |
| `fusion-rrf+w=0.7+d=100+c=60` | covered | 0.705 (100) | 0.687 | 1.000 | 0.627 | 0.530 | 0.760 | 0.840 | 0.890 | 0.950 | -0.001 [-0.011, +0.008] |
| `fusion-rrf+w=0.75+d=100+c=10` | covered | 0.676 (100) | 0.651 | 1.000 | 0.654 | 0.560 | 0.770 | 0.860 | 0.900 | 0.940 | -0.030 [-0.052, -0.008] |
| `fusion-rrf+w=0.75+d=100+c=100` | covered | 0.705 (100) | 0.690 | 1.000 | 0.618 | 0.520 | 0.770 | 0.840 | 0.890 | 0.943 | -0.001 [-0.013, +0.010] |
| `fusion-rrf+w=0.75+d=100+c=30` | covered | 0.694 (100) | 0.668 | 1.000 | 0.644 | 0.550 | 0.810 | 0.870 | 0.900 | 0.943 | -0.013 [-0.029, +0.003] |
| `fusion-rrf+w=0.75+d=100+c=60` | covered | 0.702 (100) | 0.680 | 1.000 | 0.630 | 0.540 | 0.770 | 0.840 | 0.890 | 0.943 | -0.005 [-0.015, +0.006] |
| `fusion-rrf+w=0.75+d=20+c=10` | covered | 0.673 (100) | 0.645 | 1.000 | 0.658 | 0.570 | 0.760 | 0.850 | 0.880 | 0.947 | -0.034 [-0.056, -0.011] |
| `fusion-rrf+w=0.75+d=20+c=100` | covered | 0.678 (100) | 0.658 | 1.000 | 0.625 | 0.520 | 0.760 | 0.850 | 0.880 | 0.947 | -0.029 [-0.050, -0.010] |
| `fusion-rrf+w=0.75+d=20+c=60` | covered | 0.678 (100) | 0.658 | 1.000 | 0.625 | 0.520 | 0.760 | 0.850 | 0.880 | 0.947 | -0.029 [-0.050, -0.010] |
| `fusion-rrf+w=0.75+d=50+c=10` | covered | 0.675 (100) | 0.648 | 1.000 | 0.658 | 0.570 | 0.770 | 0.860 | 0.890 | 0.940 | -0.031 [-0.054, -0.010] |
| `fusion-rrf+w=0.75+d=50+c=100` | covered | 0.696 (100) | 0.686 | 1.000 | 0.617 | 0.520 | 0.760 | 0.840 | 0.890 | 0.947 | -0.010 [-0.022, +0.000] |
| `fusion-rrf+w=0.75+d=50+c=60` | covered | 0.695 (100) | 0.676 | 1.000 | 0.626 | 0.530 | 0.760 | 0.850 | 0.890 | 0.947 | -0.012 [-0.023, -0.001] |
| `fusion-rrf+w=1+d=100+c=10` | covered | 0.644 (100) | 0.637 | 1.000 | 0.599 | 0.500 | 0.740 | 0.820 | 0.880 | 0.793 | -0.063 [-0.091, -0.035] |
| `fusion-top1bonus+b=0.1+w=0.55+d=100+c=30` | covered | 0.705 (100) | 0.689 | 1.000 | 0.653 | 0.560 | 0.790 | 0.850 | 0.890 | 0.980 | -0.002 [-0.006, +0.002] |
| `fusion-top1bonus+b=0.25+w=0.55+d=100+c=30` | covered | 0.702 (100) | 0.687 | 1.000 | 0.653 | 0.560 | 0.790 | 0.850 | 0.890 | 0.980 | -0.004 [-0.012, +0.002] |
| `hybrid-bge-small+linear+w=0.25` | PROVISIONAL | 0.606 (100) | 0.583 | 0.956 | 0.587 | 0.490 | 0.710 | 0.740 | 0.750 | 0.948 | withheld: both runs must have all dev top-10 positions present and judged |
| `hybrid-bge-small+linear+w=0.5` | PROVISIONAL | 0.627 (100) | 0.601 | 0.889 | 0.569 | 0.470 | 0.690 | 0.790 | 0.830 | 0.891 | withheld: both runs must have all dev top-10 positions present and judged |
| `hybrid-bge-small+linear+w=0.75` | PROVISIONAL | 0.629 (100) | 0.612 | 0.939 | 0.559 | 0.470 | 0.690 | 0.740 | 0.830 | 0.856 | withheld: both runs must have all dev top-10 positions present and judged |
| `hybrid-bge-small+rrf+w=0.25+c=10` | PROVISIONAL | 0.557 (100) | 0.545 | 0.996 | 0.581 | 0.490 | 0.680 | 0.730 | 0.760 | 0.960 | withheld: both runs must have all dev top-10 positions present and judged |
| `hybrid-bge-small+rrf+w=0.25+c=100` | PROVISIONAL | 0.615 (100) | 0.591 | 0.920 | 0.591 | 0.490 | 0.710 | 0.750 | 0.770 | 0.960 | withheld: both runs must have all dev top-10 positions present and judged |
| `hybrid-bge-small+rrf+w=0.25+c=60` | PROVISIONAL | 0.605 (100) | 0.587 | 0.959 | 0.585 | 0.480 | 0.720 | 0.740 | 0.760 | 0.960 | withheld: both runs must have all dev top-10 positions present and judged |
| `hybrid-bge-small+rrf+w=0.5+c=10` | covered | 0.628 (100) | 0.614 | 1.000 | 0.602 | 0.500 | 0.770 | 0.790 | 0.850 | 0.930 | -0.078 [-0.110, -0.050] |
| `hybrid-bge-small+rrf+w=0.5+c=100` | PROVISIONAL | 0.627 (100) | 0.594 | 0.857 | 0.578 | 0.490 | 0.720 | 0.770 | 0.820 | 0.891 | withheld: both runs must have all dev top-10 positions present and judged |
| `hybrid-bge-small+rrf+w=0.5+c=60` | PROVISIONAL | 0.631 (100) | 0.600 | 0.877 | 0.581 | 0.490 | 0.710 | 0.780 | 0.820 | 0.892 | withheld: both runs must have all dev top-10 positions present and judged |
| `hybrid-bge-small+rrf+w=0.75+c=10` | PROVISIONAL | 0.612 (100) | 0.616 | 0.997 | 0.552 | 0.470 | 0.650 | 0.760 | 0.840 | 0.797 | withheld: both runs must have all dev top-10 positions present and judged |
| `hybrid-bge-small+rrf+w=0.75+c=100` | PROVISIONAL | 0.626 (100) | 0.604 | 0.894 | 0.563 | 0.480 | 0.690 | 0.760 | 0.850 | 0.856 | withheld: both runs must have all dev top-10 positions present and judged |
| `hybrid-bge-small+rrf+w=0.75+c=60` | PROVISIONAL | 0.627 (100) | 0.614 | 0.942 | 0.561 | 0.480 | 0.700 | 0.750 | 0.840 | 0.856 | withheld: both runs must have all dev top-10 positions present and judged |
| `hybrid-gte-small+linear+w=0.25` | PROVISIONAL | 0.606 (100) | 0.584 | 0.956 | 0.588 | 0.490 | 0.720 | 0.740 | 0.760 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| `hybrid-gte-small+linear+w=0.5` | PROVISIONAL | 0.631 (100) | 0.603 | 0.885 | 0.603 | 0.510 | 0.720 | 0.760 | 0.810 | 0.920 | withheld: both runs must have all dev top-10 positions present and judged |
| `hybrid-gte-small+linear+w=0.75` | PROVISIONAL | 0.638 (100) | 0.621 | 0.947 | 0.570 | 0.460 | 0.710 | 0.760 | 0.830 | 0.801 | withheld: both runs must have all dev top-10 positions present and judged |
| `hybrid-gte-small+rrf+w=0.25+c=10` | PROVISIONAL | 0.559 (100) | 0.547 | 0.999 | 0.579 | 0.500 | 0.670 | 0.720 | 0.770 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| `hybrid-gte-small+rrf+w=0.25+c=100` | PROVISIONAL | 0.615 (100) | 0.591 | 0.918 | 0.590 | 0.500 | 0.710 | 0.740 | 0.770 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| `hybrid-gte-small+rrf+w=0.25+c=60` | PROVISIONAL | 0.606 (100) | 0.586 | 0.957 | 0.588 | 0.500 | 0.720 | 0.730 | 0.760 | 0.980 | withheld: both runs must have all dev top-10 positions present and judged |
| `hybrid-gte-small+rrf+w=0.5+c=10` | covered | 0.631 (100) | 0.611 | 1.000 | 0.635 | 0.540 | 0.760 | 0.800 | 0.840 | 0.973 | -0.075 [-0.104, -0.046] |
| `hybrid-gte-small+rrf+w=0.5+c=100` | PROVISIONAL | 0.629 (100) | 0.591 | 0.854 | 0.601 | 0.510 | 0.720 | 0.770 | 0.810 | 0.920 | withheld: both runs must have all dev top-10 positions present and judged |
| `hybrid-gte-small+rrf+w=0.5+c=60` | PROVISIONAL | 0.633 (100) | 0.598 | 0.876 | 0.603 | 0.510 | 0.710 | 0.770 | 0.810 | 0.920 | withheld: both runs must have all dev top-10 positions present and judged |
| `hybrid-gte-small+rrf+w=0.75+c=10` | PROVISIONAL | 0.617 (100) | 0.607 | 0.997 | 0.576 | 0.480 | 0.710 | 0.760 | 0.850 | 0.766 | withheld: both runs must have all dev top-10 positions present and judged |
| `hybrid-gte-small+rrf+w=0.75+c=100` | PROVISIONAL | 0.640 (100) | 0.619 | 0.910 | 0.578 | 0.480 | 0.690 | 0.770 | 0.830 | 0.805 | withheld: both runs must have all dev top-10 positions present and judged |
| `hybrid-gte-small+rrf+w=0.75+c=60` | PROVISIONAL | 0.645 (100) | 0.627 | 0.949 | 0.586 | 0.490 | 0.720 | 0.770 | 0.840 | 0.806 | withheld: both runs must have all dev top-10 positions present and judged |
| `hybrid-openai-large+rrf+w=0.5+c=10` | covered | 0.660 (100) | 0.633 | 1.000 | 0.653 | 0.560 | 0.800 | 0.840 | 0.900 | 0.980 | -0.046 [-0.062, -0.031] |
| `score-max+w=0.35+d=100` | covered | 0.674 (100) | 0.670 | 1.000 | 0.636 | 0.560 | 0.730 | 0.750 | 0.780 | 1.000 | -0.032 [-0.053, -0.013] |
| `score-max+w=0.35+d=500` | covered | 0.637 (100) | 0.635 | 1.000 | 0.619 | 0.540 | 0.720 | 0.770 | 0.800 | 1.000 | -0.069 [-0.096, -0.043] |
| `score-max+w=0.55+d=100` | covered | 0.699 (100) | 0.686 | 1.000 | 0.656 | 0.570 | 0.760 | 0.790 | 0.860 | 0.980 | -0.007 [-0.021, +0.006] |
| `score-max+w=0.55+d=500` | covered | 0.687 (100) | 0.670 | 1.000 | 0.657 | 0.570 | 0.760 | 0.810 | 0.840 | 0.980 | -0.019 [-0.036, -0.002] |
| `score-max+w=0.75+d=100` | covered | 0.711 (100) | 0.686 | 1.000 | 0.668 | 0.590 | 0.760 | 0.820 | 0.870 | 0.980 | +0.005 [-0.006, +0.017] |
| `score-max+w=0.75+d=500` | covered | 0.720 (100) | 0.697 | 1.000 | 0.692 | 0.610 | 0.800 | 0.820 | 0.840 | 0.980 | +0.013 [+0.002, +0.025] |
| `score-minmax+w=0.35+d=100` | covered | 0.610 (100) | 0.577 | 1.000 | 0.626 | 0.540 | 0.720 | 0.790 | 0.860 | 1.000 | -0.096 [-0.124, -0.071] |
| `score-minmax+w=0.35+d=500` | covered | 0.645 (100) | 0.626 | 1.000 | 0.631 | 0.540 | 0.750 | 0.790 | 0.830 | 1.000 | -0.062 [-0.086, -0.039] |
| `score-minmax+w=0.55+d=100` | covered | 0.685 (100) | 0.647 | 1.000 | 0.690 | 0.590 | 0.820 | 0.850 | 0.900 | 0.980 | -0.021 [-0.037, -0.007] |
| `score-minmax+w=0.55+d=500` | covered | 0.703 (100) | 0.674 | 1.000 | 0.684 | 0.590 | 0.790 | 0.840 | 0.880 | 0.980 | -0.003 [-0.014, +0.007] |
| `score-minmax+w=0.75+d=100` | covered | 0.679 (100) | 0.651 | 1.000 | 0.671 | 0.590 | 0.810 | 0.860 | 0.900 | 0.950 | -0.027 [-0.049, -0.006] |
| `score-minmax+w=0.75+d=500` | covered | 0.696 (100) | 0.668 | 1.000 | 0.684 | 0.600 | 0.810 | 0.860 | 0.900 | 0.960 | -0.010 [-0.029, +0.008] |

## Every run by query type

| System | Type | Queries | nDCG@10 (n) | P@10 | judged@10 | Source MRR@10 | R@1 | R@5 | R@10 | R@20 |
|---|---|---|---|---|---|---|---|---|---|---|
| `baseline-original-equal-rrf-c10-d100` | keyword | 25 | 0.696 (25) | 0.692 | 1.000 | 0.717 | 0.600 | 0.920 | 0.960 | 1.000 |
| `baseline-original-equal-rrf-c10-d100` | question | 25 | 0.662 (25) | 0.660 | 1.000 | 0.553 | 0.440 | 0.760 | 0.760 | 0.800 |
| `baseline-original-equal-rrf-c10-d100` | paraphrase | 25 | 0.591 (25) | 0.576 | 1.000 | 0.364 | 0.240 | 0.520 | 0.640 | 0.800 |
| `baseline-original-equal-rrf-c10-d100` | known_item | 25 | 0.692 (25) | 0.604 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `bm25+authors` | keyword | 25 | 0.587 (25) | 0.572 | 0.904 | 0.589 | 0.480 | 0.760 | 0.920 | 0.920 |
| `bm25+authors` | question | 25 | 0.405 (25) | 0.416 | 0.820 | 0.408 | 0.320 | 0.520 | 0.560 | 0.680 |
| `bm25+authors` | paraphrase | 25 | 0.340 (25) | 0.376 | 0.812 | 0.096 | 0.080 | 0.120 | 0.200 | 0.240 |
| `bm25+authors` | known_item | 25 | 0.656 (25) | 0.564 | 0.880 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `bm25+authors+title2x` | keyword | 25 | 0.577 (25) | 0.552 | 0.896 | 0.611 | 0.480 | 0.880 | 0.920 | 0.920 |
| `bm25+authors+title2x` | question | 25 | 0.401 (25) | 0.416 | 0.844 | 0.427 | 0.360 | 0.480 | 0.560 | 0.680 |
| `bm25+authors+title2x` | paraphrase | 25 | 0.330 (25) | 0.364 | 0.820 | 0.096 | 0.080 | 0.120 | 0.200 | 0.200 |
| `bm25+authors+title2x` | known_item | 25 | 0.665 (25) | 0.572 | 0.904 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `bm25+exact+stems` | keyword | 25 | 0.598 (25) | 0.584 | 0.944 | 0.650 | 0.560 | 0.840 | 0.920 | 0.920 |
| `bm25+exact+stems` | question | 25 | 0.460 (25) | 0.488 | 0.948 | 0.434 | 0.360 | 0.520 | 0.600 | 0.720 |
| `bm25+exact+stems` | paraphrase | 25 | 0.354 (25) | 0.392 | 0.920 | 0.125 | 0.080 | 0.240 | 0.280 | 0.280 |
| `bm25+exact+stems` | known_item | 25 | 0.637 (25) | 0.564 | 0.832 | 0.873 | 0.760 | 1.000 | 1.000 | 1.000 |
| `bm25+exact+stems+authors` | keyword | 25 | 0.602 (25) | 0.592 | 0.948 | 0.648 | 0.560 | 0.840 | 0.920 | 0.920 |
| `bm25+exact+stems+authors` | question | 25 | 0.454 (25) | 0.468 | 0.940 | 0.454 | 0.400 | 0.520 | 0.600 | 0.720 |
| `bm25+exact+stems+authors` | paraphrase | 25 | 0.356 (25) | 0.400 | 0.936 | 0.127 | 0.080 | 0.240 | 0.280 | 0.280 |
| `bm25+exact+stems+authors` | known_item | 25 | 0.663 (25) | 0.576 | 0.924 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `bm25+exact+stems+authors+title2x` | keyword | 25 | 0.594 (25) | 0.588 | 0.960 | 0.657 | 0.520 | 0.920 | 0.920 | 0.920 |
| `bm25+exact+stems+authors+title2x` | question | 25 | 0.440 (25) | 0.456 | 0.964 | 0.459 | 0.400 | 0.560 | 0.640 | 0.720 |
| `bm25+exact+stems+authors+title2x` | paraphrase | 25 | 0.360 (25) | 0.404 | 0.952 | 0.124 | 0.080 | 0.200 | 0.280 | 0.280 |
| `bm25+exact+stems+authors+title2x` | known_item | 25 | 0.669 (25) | 0.584 | 0.948 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | keyword | 25 | 0.610 (25) | 0.596 | 1.000 | 0.710 | 0.600 | 0.880 | 0.920 | 0.920 |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | question | 25 | 0.434 (25) | 0.452 | 1.000 | 0.432 | 0.360 | 0.520 | 0.640 | 0.640 |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | paraphrase | 25 | 0.365 (25) | 0.412 | 1.000 | 0.132 | 0.080 | 0.240 | 0.280 | 0.280 |
| `bm25+exact+stems+authors+title2x+k1=0.8,b=0.75` | known_item | 25 | 0.666 (25) | 0.588 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `bm25+exact+stems+title2x` | keyword | 25 | 0.597 (25) | 0.592 | 0.960 | 0.657 | 0.520 | 0.920 | 0.920 | 0.920 |
| `bm25+exact+stems+title2x` | question | 25 | 0.456 (25) | 0.480 | 0.960 | 0.459 | 0.400 | 0.560 | 0.640 | 0.680 |
| `bm25+exact+stems+title2x` | paraphrase | 25 | 0.361 (25) | 0.400 | 0.940 | 0.125 | 0.080 | 0.200 | 0.280 | 0.280 |
| `bm25+exact+stems+title2x` | known_item | 25 | 0.661 (25) | 0.600 | 0.876 | 0.940 | 0.880 | 1.000 | 1.000 | 1.000 |
| `bm25+stem` | keyword | 25 | 0.573 (25) | 0.528 | 0.848 | 0.665 | 0.600 | 0.760 | 0.840 | 0.920 |
| `bm25+stem` | question | 25 | 0.403 (25) | 0.384 | 0.732 | 0.388 | 0.280 | 0.520 | 0.680 | 0.680 |
| `bm25+stem` | paraphrase | 25 | 0.305 (25) | 0.308 | 0.664 | 0.166 | 0.120 | 0.240 | 0.320 | 0.320 |
| `bm25+stem` | known_item | 25 | 0.599 (25) | 0.512 | 0.752 | 0.748 | 0.600 | 0.920 | 0.960 | 1.000 |
| `bm25+stem+authors` | keyword | 25 | 0.577 (25) | 0.540 | 0.844 | 0.676 | 0.600 | 0.760 | 0.880 | 0.920 |
| `bm25+stem+authors` | question | 25 | 0.391 (25) | 0.372 | 0.712 | 0.377 | 0.280 | 0.520 | 0.600 | 0.680 |
| `bm25+stem+authors` | paraphrase | 25 | 0.299 (25) | 0.304 | 0.664 | 0.161 | 0.120 | 0.240 | 0.280 | 0.320 |
| `bm25+stem+authors` | known_item | 25 | 0.642 (25) | 0.532 | 0.828 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `bm25+stem+authors+title2x` | keyword | 25 | 0.582 (25) | 0.548 | 0.860 | 0.653 | 0.560 | 0.800 | 0.880 | 0.920 |
| `bm25+stem+authors+title2x` | question | 25 | 0.400 (25) | 0.388 | 0.752 | 0.384 | 0.280 | 0.560 | 0.640 | 0.680 |
| `bm25+stem+authors+title2x` | paraphrase | 25 | 0.310 (25) | 0.324 | 0.696 | 0.178 | 0.160 | 0.160 | 0.280 | 0.320 |
| `bm25+stem+authors+title2x` | known_item | 25 | 0.651 (25) | 0.548 | 0.860 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `bm25+stem+title2x` | keyword | 25 | 0.585 (25) | 0.552 | 0.868 | 0.650 | 0.560 | 0.800 | 0.920 | 0.920 |
| `bm25+stem+title2x` | question | 25 | 0.400 (25) | 0.384 | 0.736 | 0.385 | 0.280 | 0.560 | 0.640 | 0.680 |
| `bm25+stem+title2x` | paraphrase | 25 | 0.304 (25) | 0.312 | 0.676 | 0.182 | 0.160 | 0.160 | 0.320 | 0.320 |
| `bm25+stem+title2x` | known_item | 25 | 0.624 (25) | 0.536 | 0.772 | 0.830 | 0.720 | 1.000 | 1.000 | 1.000 |
| `bm25+stop` | keyword | 25 | 0.577 (25) | 0.560 | 0.892 | 0.592 | 0.480 | 0.800 | 0.920 | 0.920 |
| `bm25+stop` | question | 25 | 0.403 (25) | 0.416 | 0.776 | 0.410 | 0.320 | 0.480 | 0.600 | 0.680 |
| `bm25+stop` | paraphrase | 25 | 0.335 (25) | 0.376 | 0.776 | 0.097 | 0.080 | 0.120 | 0.200 | 0.200 |
| `bm25+stop` | known_item | 25 | 0.637 (25) | 0.548 | 0.792 | 0.907 | 0.840 | 1.000 | 1.000 | 1.000 |
| `bm25+stop+authors` | keyword | 25 | 0.586 (25) | 0.572 | 0.896 | 0.595 | 0.480 | 0.800 | 0.920 | 0.920 |
| `bm25+stop+authors` | question | 25 | 0.407 (25) | 0.420 | 0.792 | 0.415 | 0.320 | 0.520 | 0.640 | 0.680 |
| `bm25+stop+authors` | paraphrase | 25 | 0.336 (25) | 0.376 | 0.768 | 0.092 | 0.080 | 0.120 | 0.160 | 0.200 |
| `bm25+stop+authors` | known_item | 25 | 0.654 (25) | 0.556 | 0.868 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `bm25+stop+authors+title2x` | keyword | 25 | 0.580 (25) | 0.560 | 0.896 | 0.613 | 0.480 | 0.840 | 0.920 | 0.920 |
| `bm25+stop+authors+title2x` | question | 25 | 0.409 (25) | 0.416 | 0.804 | 0.436 | 0.360 | 0.480 | 0.640 | 0.680 |
| `bm25+stop+authors+title2x` | paraphrase | 25 | 0.323 (25) | 0.352 | 0.788 | 0.072 | 0.040 | 0.120 | 0.160 | 0.200 |
| `bm25+stop+authors+title2x` | known_item | 25 | 0.675 (25) | 0.584 | 0.908 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `bm25+stop+exact+stems` | keyword | 25 | 0.584 (25) | 0.572 | 0.940 | 0.629 | 0.520 | 0.880 | 0.920 | 0.920 |
| `bm25+stop+exact+stems` | question | 25 | 0.461 (25) | 0.484 | 0.916 | 0.431 | 0.360 | 0.480 | 0.640 | 0.720 |
| `bm25+stop+exact+stems` | paraphrase | 25 | 0.365 (25) | 0.412 | 0.892 | 0.129 | 0.080 | 0.240 | 0.280 | 0.280 |
| `bm25+stop+exact+stems` | known_item | 25 | 0.636 (25) | 0.564 | 0.828 | 0.873 | 0.760 | 1.000 | 1.000 | 1.000 |
| `bm25+stop+exact+stems+authors` | keyword | 25 | 0.591 (25) | 0.584 | 0.940 | 0.630 | 0.520 | 0.840 | 0.920 | 0.920 |
| `bm25+stop+exact+stems+authors` | question | 25 | 0.456 (25) | 0.476 | 0.920 | 0.432 | 0.360 | 0.520 | 0.640 | 0.720 |
| `bm25+stop+exact+stems+authors` | paraphrase | 25 | 0.360 (25) | 0.416 | 0.896 | 0.128 | 0.080 | 0.240 | 0.240 | 0.280 |
| `bm25+stop+exact+stems+authors` | known_item | 25 | 0.665 (25) | 0.576 | 0.916 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `bm25+stop+exact+stems+authors+title2x` | keyword | 25 | 0.596 (25) | 0.588 | 0.952 | 0.663 | 0.520 | 0.920 | 0.920 | 0.920 |
| `bm25+stop+exact+stems+authors+title2x` | question | 25 | 0.459 (25) | 0.472 | 0.928 | 0.452 | 0.400 | 0.480 | 0.640 | 0.720 |
| `bm25+stop+exact+stems+authors+title2x` | paraphrase | 25 | 0.359 (25) | 0.412 | 0.920 | 0.122 | 0.080 | 0.200 | 0.240 | 0.280 |
| `bm25+stop+exact+stems+authors+title2x` | known_item | 25 | 0.673 (25) | 0.588 | 0.944 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `bm25+stop+exact+stems+title2x` | keyword | 25 | 0.592 (25) | 0.584 | 0.948 | 0.657 | 0.520 | 0.920 | 0.920 | 0.920 |
| `bm25+stop+exact+stems+title2x` | question | 25 | 0.459 (25) | 0.468 | 0.924 | 0.453 | 0.400 | 0.520 | 0.640 | 0.720 |
| `bm25+stop+exact+stems+title2x` | paraphrase | 25 | 0.362 (25) | 0.408 | 0.904 | 0.125 | 0.080 | 0.200 | 0.280 | 0.280 |
| `bm25+stop+exact+stems+title2x` | known_item | 25 | 0.662 (25) | 0.600 | 0.872 | 0.940 | 0.880 | 1.000 | 1.000 | 1.000 |
| `bm25+stop+stem` | keyword | 25 | 0.577 (25) | 0.540 | 0.848 | 0.649 | 0.560 | 0.760 | 0.880 | 0.920 |
| `bm25+stop+stem` | question | 25 | 0.414 (25) | 0.392 | 0.708 | 0.409 | 0.320 | 0.480 | 0.640 | 0.680 |
| `bm25+stop+stem` | paraphrase | 25 | 0.309 (25) | 0.320 | 0.660 | 0.164 | 0.120 | 0.200 | 0.320 | 0.320 |
| `bm25+stop+stem` | known_item | 25 | 0.596 (25) | 0.512 | 0.752 | 0.746 | 0.600 | 0.920 | 0.960 | 1.000 |
| `bm25+stop+stem+authors` | keyword | 25 | 0.577 (25) | 0.540 | 0.844 | 0.652 | 0.560 | 0.760 | 0.840 | 0.920 |
| `bm25+stop+stem+authors` | question | 25 | 0.419 (25) | 0.396 | 0.708 | 0.430 | 0.360 | 0.480 | 0.640 | 0.680 |
| `bm25+stop+stem+authors` | paraphrase | 25 | 0.299 (25) | 0.312 | 0.644 | 0.159 | 0.120 | 0.200 | 0.280 | 0.320 |
| `bm25+stop+stem+authors` | known_item | 25 | 0.647 (25) | 0.544 | 0.844 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `bm25+stop+stem+authors+title2x` | keyword | 25 | 0.582 (25) | 0.548 | 0.860 | 0.651 | 0.560 | 0.800 | 0.920 | 0.920 |
| `bm25+stop+stem+authors+title2x` | question | 25 | 0.418 (25) | 0.400 | 0.724 | 0.407 | 0.320 | 0.520 | 0.640 | 0.680 |
| `bm25+stop+stem+authors+title2x` | paraphrase | 25 | 0.302 (25) | 0.324 | 0.668 | 0.157 | 0.120 | 0.160 | 0.280 | 0.280 |
| `bm25+stop+stem+authors+title2x` | known_item | 25 | 0.657 (25) | 0.552 | 0.864 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `bm25+stop+stem+title2x` | keyword | 25 | 0.584 (25) | 0.552 | 0.868 | 0.660 | 0.560 | 0.800 | 0.920 | 0.920 |
| `bm25+stop+stem+title2x` | question | 25 | 0.421 (25) | 0.400 | 0.716 | 0.407 | 0.320 | 0.520 | 0.640 | 0.680 |
| `bm25+stop+stem+title2x` | paraphrase | 25 | 0.302 (25) | 0.312 | 0.660 | 0.161 | 0.120 | 0.160 | 0.320 | 0.320 |
| `bm25+stop+stem+title2x` | known_item | 25 | 0.629 (25) | 0.544 | 0.776 | 0.830 | 0.720 | 1.000 | 1.000 | 1.000 |
| `bm25+stop+title2x` | keyword | 25 | 0.579 (25) | 0.564 | 0.900 | 0.606 | 0.480 | 0.840 | 0.920 | 0.920 |
| `bm25+stop+title2x` | question | 25 | 0.417 (25) | 0.424 | 0.804 | 0.435 | 0.360 | 0.480 | 0.640 | 0.680 |
| `bm25+stop+title2x` | paraphrase | 25 | 0.328 (25) | 0.364 | 0.800 | 0.096 | 0.080 | 0.120 | 0.200 | 0.200 |
| `bm25+stop+title2x` | known_item | 25 | 0.658 (25) | 0.576 | 0.820 | 0.940 | 0.880 | 1.000 | 1.000 | 1.000 |
| `bm25+title2x` | keyword | 25 | 0.577 (25) | 0.560 | 0.904 | 0.603 | 0.480 | 0.840 | 0.920 | 0.920 |
| `bm25+title2x` | question | 25 | 0.401 (25) | 0.412 | 0.836 | 0.427 | 0.360 | 0.480 | 0.560 | 0.680 |
| `bm25+title2x` | paraphrase | 25 | 0.324 (25) | 0.360 | 0.812 | 0.097 | 0.080 | 0.120 | 0.200 | 0.200 |
| `bm25+title2x` | known_item | 25 | 0.659 (25) | 0.580 | 0.828 | 0.940 | 0.880 | 1.000 | 1.000 | 1.000 |
| `bm25-baseline` | keyword | 25 | 0.576 (25) | 0.560 | 0.896 | 0.593 | 0.480 | 0.800 | 0.920 | 0.920 |
| `bm25-baseline` | question | 25 | 0.408 (25) | 0.420 | 0.812 | 0.408 | 0.320 | 0.520 | 0.560 | 0.680 |
| `bm25-baseline` | paraphrase | 25 | 0.335 (25) | 0.368 | 0.796 | 0.097 | 0.080 | 0.120 | 0.200 | 0.200 |
| `bm25-baseline` | known_item | 25 | 0.631 (25) | 0.540 | 0.788 | 0.907 | 0.840 | 1.000 | 1.000 | 1.000 |
| `dense-bge-small` | keyword | 25 | 0.630 (25) | 0.656 | 1.000 | 0.654 | 0.600 | 0.680 | 0.800 | 0.880 |
| `dense-bge-small` | question | 25 | 0.594 (25) | 0.624 | 1.000 | 0.418 | 0.320 | 0.560 | 0.680 | 0.720 |
| `dense-bge-small` | paraphrase | 25 | 0.462 (25) | 0.496 | 1.000 | 0.284 | 0.200 | 0.360 | 0.480 | 0.640 |
| `dense-bge-small` | known_item | 25 | 0.620 (25) | 0.560 | 1.000 | 0.667 | 0.560 | 0.800 | 0.840 | 0.920 |
| `dense-e5-small` | keyword | 25 | 0.491 (25) | 0.412 | 0.552 | 0.602 | 0.480 | 0.800 | 0.880 | 0.880 |
| `dense-e5-small` | question | 25 | 0.411 (25) | 0.384 | 0.564 | 0.447 | 0.360 | 0.520 | 0.640 | 0.680 |
| `dense-e5-small` | paraphrase | 25 | 0.283 (25) | 0.244 | 0.416 | 0.264 | 0.240 | 0.280 | 0.320 | 0.480 |
| `dense-e5-small` | known_item | 25 | 0.508 (25) | 0.396 | 0.532 | 0.626 | 0.480 | 0.840 | 0.920 | 0.960 |
| `dense-gte-small` | keyword | 25 | 0.657 (25) | 0.652 | 1.000 | 0.688 | 0.600 | 0.840 | 0.840 | 0.840 |
| `dense-gte-small` | question | 25 | 0.582 (25) | 0.616 | 1.000 | 0.417 | 0.320 | 0.520 | 0.640 | 0.760 |
| `dense-gte-small` | paraphrase | 25 | 0.505 (25) | 0.536 | 1.000 | 0.364 | 0.280 | 0.440 | 0.520 | 0.640 |
| `dense-gte-small` | known_item | 25 | 0.580 (25) | 0.520 | 1.000 | 0.633 | 0.520 | 0.840 | 0.840 | 0.880 |
| `dense-minilm` | keyword | 25 | 0.519 (25) | 0.452 | 0.588 | 0.459 | 0.400 | 0.560 | 0.680 | 0.800 |
| `dense-minilm` | question | 25 | 0.436 (25) | 0.396 | 0.544 | 0.358 | 0.280 | 0.520 | 0.520 | 0.640 |
| `dense-minilm` | paraphrase | 25 | 0.364 (25) | 0.352 | 0.552 | 0.260 | 0.200 | 0.320 | 0.440 | 0.520 |
| `dense-minilm` | known_item | 25 | 0.440 (25) | 0.320 | 0.496 | 0.549 | 0.440 | 0.720 | 0.720 | 0.760 |
| `dense-openai-large` | keyword | 25 | 0.642 (25) | 0.676 | 1.000 | 0.577 | 0.480 | 0.800 | 0.800 | 0.880 |
| `dense-openai-large` | question | 25 | 0.688 (25) | 0.704 | 1.000 | 0.560 | 0.440 | 0.720 | 0.800 | 0.840 |
| `dense-openai-large` | paraphrase | 25 | 0.644 (25) | 0.652 | 1.000 | 0.466 | 0.400 | 0.520 | 0.720 | 0.800 |
| `dense-openai-large` | known_item | 25 | 0.600 (25) | 0.516 | 1.000 | 0.793 | 0.680 | 0.920 | 0.960 | 1.000 |
| `fusion-linear+w=0.25+d=100` | keyword | 25 | 0.696 (25) | 0.692 | 1.000 | 0.741 | 0.640 | 0.880 | 0.880 | 0.960 |
| `fusion-linear+w=0.25+d=100` | question | 25 | 0.606 (25) | 0.588 | 1.000 | 0.557 | 0.480 | 0.640 | 0.720 | 0.720 |
| `fusion-linear+w=0.25+d=100` | paraphrase | 25 | 0.531 (25) | 0.540 | 1.000 | 0.267 | 0.200 | 0.360 | 0.360 | 0.400 |
| `fusion-linear+w=0.25+d=100` | known_item | 25 | 0.716 (25) | 0.636 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-linear+w=0.25+d=20` | keyword | 25 | 0.644 (25) | 0.624 | 1.000 | 0.759 | 0.640 | 0.880 | 0.920 | 1.000 |
| `fusion-linear+w=0.25+d=20` | question | 25 | 0.490 (25) | 0.460 | 1.000 | 0.525 | 0.480 | 0.600 | 0.640 | 0.760 |
| `fusion-linear+w=0.25+d=20` | paraphrase | 25 | 0.391 (25) | 0.424 | 1.000 | 0.193 | 0.160 | 0.240 | 0.280 | 0.720 |
| `fusion-linear+w=0.25+d=20` | known_item | 25 | 0.676 (25) | 0.596 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-linear+w=0.25+d=50` | keyword | 25 | 0.675 (25) | 0.652 | 1.000 | 0.739 | 0.640 | 0.880 | 0.920 | 0.920 |
| `fusion-linear+w=0.25+d=50` | question | 25 | 0.544 (25) | 0.508 | 1.000 | 0.546 | 0.480 | 0.600 | 0.680 | 0.720 |
| `fusion-linear+w=0.25+d=50` | paraphrase | 25 | 0.447 (25) | 0.452 | 1.000 | 0.207 | 0.160 | 0.280 | 0.280 | 0.360 |
| `fusion-linear+w=0.25+d=50` | known_item | 25 | 0.692 (25) | 0.616 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-linear+w=0.5+d=100` | keyword | 25 | 0.729 (25) | 0.744 | 1.000 | 0.692 | 0.600 | 0.840 | 0.880 | 1.000 |
| `fusion-linear+w=0.5+d=100` | question | 25 | 0.693 (25) | 0.708 | 1.000 | 0.553 | 0.440 | 0.680 | 0.760 | 0.800 |
| `fusion-linear+w=0.5+d=100` | paraphrase | 25 | 0.616 (25) | 0.636 | 1.000 | 0.303 | 0.200 | 0.440 | 0.520 | 0.720 |
| `fusion-linear+w=0.5+d=100` | known_item | 25 | 0.723 (25) | 0.648 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-linear+w=0.5+d=20` | keyword | 25 | 0.665 (25) | 0.652 | 1.000 | 0.706 | 0.600 | 0.920 | 0.920 | 1.000 |
| `fusion-linear+w=0.5+d=20` | question | 25 | 0.635 (25) | 0.608 | 1.000 | 0.545 | 0.440 | 0.680 | 0.760 | 0.800 |
| `fusion-linear+w=0.5+d=20` | paraphrase | 25 | 0.555 (25) | 0.568 | 1.000 | 0.329 | 0.160 | 0.600 | 0.680 | 0.760 |
| `fusion-linear+w=0.5+d=20` | known_item | 25 | 0.674 (25) | 0.592 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-linear+w=0.5+d=50` | keyword | 25 | 0.712 (25) | 0.716 | 1.000 | 0.693 | 0.600 | 0.840 | 0.880 | 1.000 |
| `fusion-linear+w=0.5+d=50` | question | 25 | 0.672 (25) | 0.676 | 1.000 | 0.550 | 0.440 | 0.720 | 0.760 | 0.800 |
| `fusion-linear+w=0.5+d=50` | paraphrase | 25 | 0.601 (25) | 0.592 | 1.000 | 0.330 | 0.200 | 0.440 | 0.680 | 0.800 |
| `fusion-linear+w=0.5+d=50` | known_item | 25 | 0.707 (25) | 0.624 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-linear+w=0.75+d=100` | keyword | 25 | 0.731 (25) | 0.744 | 1.000 | 0.640 | 0.520 | 0.800 | 0.920 | 0.920 |
| `fusion-linear+w=0.75+d=100` | question | 25 | 0.717 (25) | 0.736 | 1.000 | 0.563 | 0.440 | 0.760 | 0.760 | 0.840 |
| `fusion-linear+w=0.75+d=100` | paraphrase | 25 | 0.665 (25) | 0.660 | 1.000 | 0.347 | 0.240 | 0.440 | 0.680 | 0.800 |
| `fusion-linear+w=0.75+d=100` | known_item | 25 | 0.698 (25) | 0.600 | 1.000 | 0.947 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-linear+w=0.75+d=20` | keyword | 25 | 0.663 (25) | 0.676 | 1.000 | 0.620 | 0.520 | 0.760 | 0.800 | 0.960 |
| `fusion-linear+w=0.75+d=20` | question | 25 | 0.704 (25) | 0.700 | 1.000 | 0.579 | 0.440 | 0.760 | 0.800 | 0.800 |
| `fusion-linear+w=0.75+d=20` | paraphrase | 25 | 0.662 (25) | 0.648 | 1.000 | 0.436 | 0.320 | 0.560 | 0.720 | 0.800 |
| `fusion-linear+w=0.75+d=20` | known_item | 25 | 0.636 (25) | 0.520 | 1.000 | 0.933 | 0.920 | 0.960 | 0.960 | 1.000 |
| `fusion-linear+w=0.75+d=50` | keyword | 25 | 0.704 (25) | 0.720 | 1.000 | 0.631 | 0.520 | 0.760 | 0.920 | 0.920 |
| `fusion-linear+w=0.75+d=50` | question | 25 | 0.714 (25) | 0.720 | 1.000 | 0.578 | 0.440 | 0.760 | 0.800 | 0.840 |
| `fusion-linear+w=0.75+d=50` | paraphrase | 25 | 0.655 (25) | 0.652 | 1.000 | 0.373 | 0.240 | 0.600 | 0.760 | 0.800 |
| `fusion-linear+w=0.75+d=50` | known_item | 25 | 0.671 (25) | 0.564 | 1.000 | 0.947 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0+d=100+c=10` | keyword | 25 | 0.610 (25) | 0.596 | 1.000 | 0.710 | 0.600 | 0.880 | 0.920 | 0.920 |
| `fusion-rrf+w=0+d=100+c=10` | question | 25 | 0.434 (25) | 0.452 | 1.000 | 0.432 | 0.360 | 0.520 | 0.640 | 0.640 |
| `fusion-rrf+w=0+d=100+c=10` | paraphrase | 25 | 0.365 (25) | 0.412 | 1.000 | 0.132 | 0.080 | 0.240 | 0.280 | 0.280 |
| `fusion-rrf+w=0+d=100+c=10` | known_item | 25 | 0.666 (25) | 0.588 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.25+d=100+c=10` | keyword | 25 | 0.665 (25) | 0.652 | 1.000 | 0.725 | 0.600 | 0.880 | 0.920 | 1.000 |
| `fusion-rrf+w=0.25+d=100+c=10` | question | 25 | 0.503 (25) | 0.488 | 1.000 | 0.505 | 0.440 | 0.560 | 0.680 | 0.720 |
| `fusion-rrf+w=0.25+d=100+c=10` | paraphrase | 25 | 0.420 (25) | 0.468 | 1.000 | 0.199 | 0.160 | 0.280 | 0.320 | 0.400 |
| `fusion-rrf+w=0.25+d=100+c=10` | known_item | 25 | 0.689 (25) | 0.620 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.25+d=100+c=100` | keyword | 25 | 0.705 (25) | 0.708 | 1.000 | 0.743 | 0.640 | 0.880 | 0.880 | 1.000 |
| `fusion-rrf+w=0.25+d=100+c=100` | question | 25 | 0.646 (25) | 0.652 | 1.000 | 0.547 | 0.480 | 0.640 | 0.720 | 0.720 |
| `fusion-rrf+w=0.25+d=100+c=100` | paraphrase | 25 | 0.556 (25) | 0.576 | 1.000 | 0.251 | 0.160 | 0.360 | 0.400 | 0.440 |
| `fusion-rrf+w=0.25+d=100+c=100` | known_item | 25 | 0.731 (25) | 0.648 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.25+d=100+c=60` | keyword | 25 | 0.694 (25) | 0.688 | 1.000 | 0.743 | 0.640 | 0.880 | 0.880 | 0.960 |
| `fusion-rrf+w=0.25+d=100+c=60` | question | 25 | 0.603 (25) | 0.604 | 1.000 | 0.544 | 0.480 | 0.640 | 0.720 | 0.720 |
| `fusion-rrf+w=0.25+d=100+c=60` | paraphrase | 25 | 0.518 (25) | 0.536 | 1.000 | 0.237 | 0.160 | 0.360 | 0.360 | 0.440 |
| `fusion-rrf+w=0.25+d=100+c=60` | known_item | 25 | 0.718 (25) | 0.644 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.25+d=20+c=10` | keyword | 25 | 0.650 (25) | 0.632 | 1.000 | 0.725 | 0.600 | 0.880 | 0.920 | 0.920 |
| `fusion-rrf+w=0.25+d=20+c=10` | question | 25 | 0.500 (25) | 0.480 | 1.000 | 0.522 | 0.480 | 0.560 | 0.640 | 0.640 |
| `fusion-rrf+w=0.25+d=20+c=10` | paraphrase | 25 | 0.401 (25) | 0.432 | 1.000 | 0.195 | 0.160 | 0.280 | 0.280 | 0.280 |
| `fusion-rrf+w=0.25+d=20+c=10` | known_item | 25 | 0.682 (25) | 0.608 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.25+d=20+c=100` | keyword | 25 | 0.657 (25) | 0.640 | 1.000 | 0.717 | 0.600 | 0.880 | 0.880 | 0.920 |
| `fusion-rrf+w=0.25+d=20+c=100` | question | 25 | 0.541 (25) | 0.500 | 1.000 | 0.533 | 0.480 | 0.600 | 0.640 | 0.640 |
| `fusion-rrf+w=0.25+d=20+c=100` | paraphrase | 25 | 0.433 (25) | 0.424 | 1.000 | 0.227 | 0.200 | 0.280 | 0.280 | 0.280 |
| `fusion-rrf+w=0.25+d=20+c=100` | known_item | 25 | 0.699 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.25+d=20+c=60` | keyword | 25 | 0.657 (25) | 0.640 | 1.000 | 0.717 | 0.600 | 0.880 | 0.880 | 0.920 |
| `fusion-rrf+w=0.25+d=20+c=60` | question | 25 | 0.541 (25) | 0.500 | 1.000 | 0.533 | 0.480 | 0.600 | 0.640 | 0.640 |
| `fusion-rrf+w=0.25+d=20+c=60` | paraphrase | 25 | 0.433 (25) | 0.424 | 1.000 | 0.227 | 0.200 | 0.280 | 0.280 | 0.280 |
| `fusion-rrf+w=0.25+d=20+c=60` | known_item | 25 | 0.699 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.25+d=50+c=10` | keyword | 25 | 0.663 (25) | 0.648 | 1.000 | 0.725 | 0.600 | 0.880 | 0.920 | 0.960 |
| `fusion-rrf+w=0.25+d=50+c=10` | question | 25 | 0.504 (25) | 0.488 | 1.000 | 0.506 | 0.440 | 0.560 | 0.680 | 0.720 |
| `fusion-rrf+w=0.25+d=50+c=10` | paraphrase | 25 | 0.421 (25) | 0.468 | 1.000 | 0.199 | 0.160 | 0.280 | 0.320 | 0.360 |
| `fusion-rrf+w=0.25+d=50+c=10` | known_item | 25 | 0.686 (25) | 0.616 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.25+d=50+c=100` | keyword | 25 | 0.693 (25) | 0.680 | 1.000 | 0.738 | 0.640 | 0.840 | 0.880 | 0.960 |
| `fusion-rrf+w=0.25+d=50+c=100` | question | 25 | 0.625 (25) | 0.616 | 1.000 | 0.551 | 0.480 | 0.640 | 0.720 | 0.720 |
| `fusion-rrf+w=0.25+d=50+c=100` | paraphrase | 25 | 0.536 (25) | 0.540 | 1.000 | 0.251 | 0.160 | 0.360 | 0.400 | 0.400 |
| `fusion-rrf+w=0.25+d=50+c=100` | known_item | 25 | 0.733 (25) | 0.656 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.25+d=50+c=60` | keyword | 25 | 0.688 (25) | 0.680 | 1.000 | 0.740 | 0.640 | 0.840 | 0.880 | 0.960 |
| `fusion-rrf+w=0.25+d=50+c=60` | question | 25 | 0.598 (25) | 0.592 | 1.000 | 0.548 | 0.480 | 0.640 | 0.720 | 0.720 |
| `fusion-rrf+w=0.25+d=50+c=60` | paraphrase | 25 | 0.501 (25) | 0.504 | 1.000 | 0.237 | 0.160 | 0.360 | 0.360 | 0.400 |
| `fusion-rrf+w=0.25+d=50+c=60` | known_item | 25 | 0.717 (25) | 0.640 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.5+d=100+c=10` | keyword | 25 | 0.696 (25) | 0.692 | 1.000 | 0.717 | 0.600 | 0.920 | 0.960 | 1.000 |
| `fusion-rrf+w=0.5+d=100+c=10` | question | 25 | 0.662 (25) | 0.660 | 1.000 | 0.553 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-rrf+w=0.5+d=100+c=10` | paraphrase | 25 | 0.591 (25) | 0.576 | 1.000 | 0.364 | 0.240 | 0.520 | 0.640 | 0.800 |
| `fusion-rrf+w=0.5+d=100+c=10` | known_item | 25 | 0.692 (25) | 0.604 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.5+d=100+c=100` | keyword | 25 | 0.727 (25) | 0.752 | 1.000 | 0.692 | 0.600 | 0.840 | 0.880 | 0.960 |
| `fusion-rrf+w=0.5+d=100+c=100` | question | 25 | 0.707 (25) | 0.720 | 1.000 | 0.549 | 0.440 | 0.680 | 0.720 | 0.760 |
| `fusion-rrf+w=0.5+d=100+c=100` | paraphrase | 25 | 0.616 (25) | 0.640 | 1.000 | 0.305 | 0.200 | 0.440 | 0.480 | 0.640 |
| `fusion-rrf+w=0.5+d=100+c=100` | known_item | 25 | 0.720 (25) | 0.644 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.5+d=100+c=30` | keyword | 25 | 0.727 (25) | 0.740 | 1.000 | 0.709 | 0.600 | 0.840 | 0.960 | 1.000 |
| `fusion-rrf+w=0.5+d=100+c=30` | question | 25 | 0.693 (25) | 0.688 | 1.000 | 0.548 | 0.440 | 0.680 | 0.760 | 0.800 |
| `fusion-rrf+w=0.5+d=100+c=30` | paraphrase | 25 | 0.620 (25) | 0.616 | 1.000 | 0.348 | 0.240 | 0.440 | 0.640 | 0.760 |
| `fusion-rrf+w=0.5+d=100+c=30` | known_item | 25 | 0.727 (25) | 0.648 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.5+d=100+c=60` | keyword | 25 | 0.730 (25) | 0.748 | 1.000 | 0.697 | 0.600 | 0.840 | 0.920 | 1.000 |
| `fusion-rrf+w=0.5+d=100+c=60` | question | 25 | 0.709 (25) | 0.720 | 1.000 | 0.542 | 0.440 | 0.680 | 0.720 | 0.760 |
| `fusion-rrf+w=0.5+d=100+c=60` | paraphrase | 25 | 0.619 (25) | 0.644 | 1.000 | 0.304 | 0.200 | 0.440 | 0.480 | 0.720 |
| `fusion-rrf+w=0.5+d=100+c=60` | known_item | 25 | 0.723 (25) | 0.644 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.5+d=20+c=10` | keyword | 25 | 0.680 (25) | 0.668 | 1.000 | 0.713 | 0.600 | 0.920 | 0.920 | 1.000 |
| `fusion-rrf+w=0.5+d=20+c=10` | question | 25 | 0.646 (25) | 0.628 | 1.000 | 0.542 | 0.440 | 0.680 | 0.760 | 0.800 |
| `fusion-rrf+w=0.5+d=20+c=10` | paraphrase | 25 | 0.559 (25) | 0.560 | 1.000 | 0.320 | 0.160 | 0.600 | 0.680 | 0.760 |
| `fusion-rrf+w=0.5+d=20+c=10` | known_item | 25 | 0.691 (25) | 0.604 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.5+d=20+c=100` | keyword | 25 | 0.684 (25) | 0.676 | 1.000 | 0.696 | 0.600 | 0.880 | 0.920 | 1.000 |
| `fusion-rrf+w=0.5+d=20+c=100` | question | 25 | 0.645 (25) | 0.628 | 1.000 | 0.544 | 0.440 | 0.680 | 0.760 | 0.800 |
| `fusion-rrf+w=0.5+d=20+c=100` | paraphrase | 25 | 0.554 (25) | 0.560 | 1.000 | 0.313 | 0.160 | 0.560 | 0.680 | 0.760 |
| `fusion-rrf+w=0.5+d=20+c=100` | known_item | 25 | 0.691 (25) | 0.612 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.5+d=20+c=60` | keyword | 25 | 0.684 (25) | 0.676 | 1.000 | 0.696 | 0.600 | 0.880 | 0.920 | 1.000 |
| `fusion-rrf+w=0.5+d=20+c=60` | question | 25 | 0.645 (25) | 0.628 | 1.000 | 0.537 | 0.440 | 0.680 | 0.760 | 0.800 |
| `fusion-rrf+w=0.5+d=20+c=60` | paraphrase | 25 | 0.554 (25) | 0.560 | 1.000 | 0.313 | 0.160 | 0.560 | 0.680 | 0.760 |
| `fusion-rrf+w=0.5+d=20+c=60` | known_item | 25 | 0.691 (25) | 0.612 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.5+d=50+c=10` | keyword | 25 | 0.690 (25) | 0.688 | 1.000 | 0.711 | 0.600 | 0.840 | 0.960 | 1.000 |
| `fusion-rrf+w=0.5+d=50+c=10` | question | 25 | 0.659 (25) | 0.656 | 1.000 | 0.553 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-rrf+w=0.5+d=50+c=10` | paraphrase | 25 | 0.586 (25) | 0.576 | 1.000 | 0.338 | 0.200 | 0.520 | 0.640 | 0.800 |
| `fusion-rrf+w=0.5+d=50+c=10` | known_item | 25 | 0.691 (25) | 0.604 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.5+d=50+c=100` | keyword | 25 | 0.719 (25) | 0.724 | 1.000 | 0.692 | 0.600 | 0.840 | 0.880 | 1.000 |
| `fusion-rrf+w=0.5+d=50+c=100` | question | 25 | 0.667 (25) | 0.668 | 1.000 | 0.555 | 0.440 | 0.680 | 0.760 | 0.800 |
| `fusion-rrf+w=0.5+d=50+c=100` | paraphrase | 25 | 0.597 (25) | 0.600 | 1.000 | 0.314 | 0.200 | 0.440 | 0.640 | 0.760 |
| `fusion-rrf+w=0.5+d=50+c=100` | known_item | 25 | 0.722 (25) | 0.644 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.5+d=50+c=60` | keyword | 25 | 0.720 (25) | 0.724 | 1.000 | 0.696 | 0.600 | 0.840 | 0.920 | 1.000 |
| `fusion-rrf+w=0.5+d=50+c=60` | question | 25 | 0.672 (25) | 0.672 | 1.000 | 0.548 | 0.440 | 0.680 | 0.760 | 0.800 |
| `fusion-rrf+w=0.5+d=50+c=60` | paraphrase | 25 | 0.597 (25) | 0.600 | 1.000 | 0.314 | 0.200 | 0.440 | 0.640 | 0.760 |
| `fusion-rrf+w=0.5+d=50+c=60` | known_item | 25 | 0.724 (25) | 0.644 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.55+d=100+c=10` | keyword | 25 | 0.698 (25) | 0.688 | 1.000 | 0.680 | 0.520 | 0.880 | 0.960 | 1.000 |
| `fusion-rrf+w=0.55+d=100+c=10` | question | 25 | 0.696 (25) | 0.700 | 1.000 | 0.575 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-rrf+w=0.55+d=100+c=10` | paraphrase | 25 | 0.640 (25) | 0.624 | 1.000 | 0.396 | 0.280 | 0.640 | 0.720 | 0.800 |
| `fusion-rrf+w=0.55+d=100+c=10` | known_item | 25 | 0.688 (25) | 0.596 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.55+d=100+c=100` | keyword | 25 | 0.737 (25) | 0.752 | 0.996 | 0.660 | 0.520 | 0.840 | 0.960 | 0.960 |
| `fusion-rrf+w=0.55+d=100+c=100` | question | 25 | 0.713 (25) | 0.720 | 1.000 | 0.542 | 0.440 | 0.680 | 0.720 | 0.800 |
| `fusion-rrf+w=0.55+d=100+c=100` | paraphrase | 25 | 0.634 (25) | 0.656 | 0.996 | 0.317 | 0.200 | 0.440 | 0.520 | 0.680 |
| `fusion-rrf+w=0.55+d=100+c=100` | known_item | 25 | 0.724 (25) | 0.644 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.55+d=100+c=30` | keyword | 25 | 0.733 (25) | 0.744 | 1.000 | 0.663 | 0.520 | 0.840 | 0.960 | 0.960 |
| `fusion-rrf+w=0.55+d=100+c=30` | question | 25 | 0.717 (25) | 0.740 | 1.000 | 0.558 | 0.440 | 0.720 | 0.760 | 0.800 |
| `fusion-rrf+w=0.55+d=100+c=30` | paraphrase | 25 | 0.662 (25) | 0.648 | 1.000 | 0.382 | 0.280 | 0.480 | 0.720 | 0.800 |
| `fusion-rrf+w=0.55+d=100+c=30` | known_item | 25 | 0.713 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.55+d=100+c=60` | keyword | 25 | 0.733 (25) | 0.748 | 1.000 | 0.660 | 0.520 | 0.840 | 0.960 | 0.960 |
| `fusion-rrf+w=0.55+d=100+c=60` | question | 25 | 0.715 (25) | 0.728 | 1.000 | 0.547 | 0.440 | 0.680 | 0.760 | 0.800 |
| `fusion-rrf+w=0.55+d=100+c=60` | paraphrase | 25 | 0.645 (25) | 0.660 | 1.000 | 0.341 | 0.240 | 0.440 | 0.560 | 0.720 |
| `fusion-rrf+w=0.55+d=100+c=60` | known_item | 25 | 0.722 (25) | 0.644 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.55+d=200+c=30` | keyword | 25 | 0.739 (25) | 0.752 | 1.000 | 0.663 | 0.520 | 0.840 | 0.960 | 0.960 |
| `fusion-rrf+w=0.55+d=200+c=30` | question | 25 | 0.714 (25) | 0.736 | 1.000 | 0.557 | 0.440 | 0.680 | 0.760 | 0.800 |
| `fusion-rrf+w=0.55+d=200+c=30` | paraphrase | 25 | 0.655 (25) | 0.648 | 1.000 | 0.356 | 0.240 | 0.480 | 0.640 | 0.760 |
| `fusion-rrf+w=0.55+d=200+c=30` | known_item | 25 | 0.715 (25) | 0.628 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.55+d=500+c=30` | keyword | 25 | 0.737 (25) | 0.752 | 1.000 | 0.663 | 0.520 | 0.840 | 0.960 | 0.960 |
| `fusion-rrf+w=0.55+d=500+c=30` | question | 25 | 0.711 (25) | 0.736 | 1.000 | 0.557 | 0.440 | 0.680 | 0.760 | 0.800 |
| `fusion-rrf+w=0.55+d=500+c=30` | paraphrase | 25 | 0.653 (25) | 0.648 | 1.000 | 0.361 | 0.240 | 0.520 | 0.640 | 0.760 |
| `fusion-rrf+w=0.55+d=500+c=30` | known_item | 25 | 0.713 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.6+d=100+c=10` | keyword | 25 | 0.695 (25) | 0.696 | 1.000 | 0.675 | 0.520 | 0.880 | 0.960 | 0.960 |
| `fusion-rrf+w=0.6+d=100+c=10` | question | 25 | 0.718 (25) | 0.724 | 1.000 | 0.588 | 0.440 | 0.760 | 0.800 | 0.800 |
| `fusion-rrf+w=0.6+d=100+c=10` | paraphrase | 25 | 0.649 (25) | 0.628 | 1.000 | 0.402 | 0.280 | 0.640 | 0.720 | 0.800 |
| `fusion-rrf+w=0.6+d=100+c=10` | known_item | 25 | 0.684 (25) | 0.596 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.6+d=100+c=100` | keyword | 25 | 0.736 (25) | 0.744 | 1.000 | 0.660 | 0.520 | 0.840 | 0.960 | 0.960 |
| `fusion-rrf+w=0.6+d=100+c=100` | question | 25 | 0.717 (25) | 0.728 | 1.000 | 0.556 | 0.440 | 0.720 | 0.760 | 0.800 |
| `fusion-rrf+w=0.6+d=100+c=100` | paraphrase | 25 | 0.644 (25) | 0.656 | 0.996 | 0.337 | 0.240 | 0.440 | 0.520 | 0.720 |
| `fusion-rrf+w=0.6+d=100+c=100` | known_item | 25 | 0.725 (25) | 0.644 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.6+d=100+c=30` | keyword | 25 | 0.724 (25) | 0.736 | 1.000 | 0.659 | 0.520 | 0.880 | 0.960 | 0.960 |
| `fusion-rrf+w=0.6+d=100+c=30` | question | 25 | 0.721 (25) | 0.744 | 1.000 | 0.563 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-rrf+w=0.6+d=100+c=30` | paraphrase | 25 | 0.668 (25) | 0.656 | 1.000 | 0.369 | 0.240 | 0.520 | 0.720 | 0.800 |
| `fusion-rrf+w=0.6+d=100+c=30` | known_item | 25 | 0.704 (25) | 0.616 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.6+d=100+c=60` | keyword | 25 | 0.741 (25) | 0.752 | 1.000 | 0.661 | 0.520 | 0.840 | 0.960 | 0.960 |
| `fusion-rrf+w=0.6+d=100+c=60` | question | 25 | 0.721 (25) | 0.744 | 1.000 | 0.559 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-rrf+w=0.6+d=100+c=60` | paraphrase | 25 | 0.658 (25) | 0.668 | 1.000 | 0.347 | 0.240 | 0.440 | 0.600 | 0.720 |
| `fusion-rrf+w=0.6+d=100+c=60` | known_item | 25 | 0.719 (25) | 0.636 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.65+d=100+c=10` | keyword | 25 | 0.686 (25) | 0.692 | 1.000 | 0.653 | 0.520 | 0.840 | 0.920 | 0.960 |
| `fusion-rrf+w=0.65+d=100+c=10` | question | 25 | 0.722 (25) | 0.724 | 1.000 | 0.602 | 0.480 | 0.760 | 0.800 | 0.800 |
| `fusion-rrf+w=0.65+d=100+c=10` | paraphrase | 25 | 0.661 (25) | 0.664 | 1.000 | 0.383 | 0.240 | 0.600 | 0.760 | 0.800 |
| `fusion-rrf+w=0.65+d=100+c=10` | known_item | 25 | 0.667 (25) | 0.568 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.65+d=100+c=100` | keyword | 25 | 0.736 (25) | 0.744 | 0.996 | 0.655 | 0.520 | 0.840 | 0.960 | 0.960 |
| `fusion-rrf+w=0.65+d=100+c=100` | question | 25 | 0.715 (25) | 0.732 | 1.000 | 0.556 | 0.440 | 0.720 | 0.760 | 0.800 |
| `fusion-rrf+w=0.65+d=100+c=100` | paraphrase | 25 | 0.639 (25) | 0.644 | 0.992 | 0.318 | 0.200 | 0.440 | 0.560 | 0.720 |
| `fusion-rrf+w=0.65+d=100+c=100` | known_item | 25 | 0.726 (25) | 0.652 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.65+d=100+c=30` | keyword | 25 | 0.722 (25) | 0.740 | 1.000 | 0.658 | 0.520 | 0.880 | 0.920 | 0.960 |
| `fusion-rrf+w=0.65+d=100+c=30` | question | 25 | 0.724 (25) | 0.744 | 1.000 | 0.570 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-rrf+w=0.65+d=100+c=30` | paraphrase | 25 | 0.673 (25) | 0.652 | 1.000 | 0.380 | 0.280 | 0.480 | 0.720 | 0.800 |
| `fusion-rrf+w=0.65+d=100+c=30` | known_item | 25 | 0.694 (25) | 0.604 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.65+d=100+c=60` | keyword | 25 | 0.735 (25) | 0.748 | 1.000 | 0.656 | 0.520 | 0.840 | 0.960 | 0.960 |
| `fusion-rrf+w=0.65+d=100+c=60` | question | 25 | 0.725 (25) | 0.748 | 1.000 | 0.559 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-rrf+w=0.65+d=100+c=60` | paraphrase | 25 | 0.650 (25) | 0.648 | 1.000 | 0.334 | 0.200 | 0.480 | 0.640 | 0.800 |
| `fusion-rrf+w=0.65+d=100+c=60` | known_item | 25 | 0.715 (25) | 0.632 | 1.000 | 0.953 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.7+d=100+c=10` | keyword | 25 | 0.685 (25) | 0.700 | 1.000 | 0.644 | 0.520 | 0.840 | 0.920 | 0.960 |
| `fusion-rrf+w=0.7+d=100+c=10` | question | 25 | 0.717 (25) | 0.716 | 1.000 | 0.602 | 0.480 | 0.760 | 0.800 | 0.840 |
| `fusion-rrf+w=0.7+d=100+c=10` | paraphrase | 25 | 0.658 (25) | 0.652 | 1.000 | 0.393 | 0.240 | 0.560 | 0.720 | 0.800 |
| `fusion-rrf+w=0.7+d=100+c=10` | known_item | 25 | 0.662 (25) | 0.556 | 1.000 | 0.950 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.7+d=100+c=100` | keyword | 25 | 0.736 (25) | 0.752 | 0.992 | 0.646 | 0.520 | 0.800 | 0.960 | 0.960 |
| `fusion-rrf+w=0.7+d=100+c=100` | question | 25 | 0.721 (25) | 0.736 | 1.000 | 0.560 | 0.440 | 0.720 | 0.760 | 0.800 |
| `fusion-rrf+w=0.7+d=100+c=100` | paraphrase | 25 | 0.653 (25) | 0.656 | 0.996 | 0.321 | 0.200 | 0.440 | 0.640 | 0.720 |
| `fusion-rrf+w=0.7+d=100+c=100` | known_item | 25 | 0.719 (25) | 0.636 | 1.000 | 0.947 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.7+d=100+c=30` | keyword | 25 | 0.715 (25) | 0.728 | 1.000 | 0.650 | 0.520 | 0.840 | 0.920 | 0.960 |
| `fusion-rrf+w=0.7+d=100+c=30` | question | 25 | 0.722 (25) | 0.736 | 1.000 | 0.577 | 0.440 | 0.760 | 0.760 | 0.840 |
| `fusion-rrf+w=0.7+d=100+c=30` | paraphrase | 25 | 0.670 (25) | 0.660 | 1.000 | 0.390 | 0.280 | 0.600 | 0.760 | 0.800 |
| `fusion-rrf+w=0.7+d=100+c=30` | known_item | 25 | 0.680 (25) | 0.580 | 1.000 | 0.950 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.7+d=100+c=60` | keyword | 25 | 0.728 (25) | 0.740 | 1.000 | 0.645 | 0.520 | 0.840 | 0.920 | 0.960 |
| `fusion-rrf+w=0.7+d=100+c=60` | question | 25 | 0.728 (25) | 0.748 | 1.000 | 0.567 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-rrf+w=0.7+d=100+c=60` | paraphrase | 25 | 0.660 (25) | 0.644 | 1.000 | 0.348 | 0.240 | 0.440 | 0.680 | 0.800 |
| `fusion-rrf+w=0.7+d=100+c=60` | known_item | 25 | 0.704 (25) | 0.616 | 1.000 | 0.950 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.75+d=100+c=10` | keyword | 25 | 0.682 (25) | 0.700 | 1.000 | 0.644 | 0.520 | 0.800 | 0.920 | 0.960 |
| `fusion-rrf+w=0.75+d=100+c=10` | question | 25 | 0.709 (25) | 0.708 | 1.000 | 0.593 | 0.480 | 0.760 | 0.800 | 0.840 |
| `fusion-rrf+w=0.75+d=100+c=10` | paraphrase | 25 | 0.666 (25) | 0.660 | 1.000 | 0.438 | 0.320 | 0.560 | 0.720 | 0.800 |
| `fusion-rrf+w=0.75+d=100+c=10` | known_item | 25 | 0.648 (25) | 0.536 | 1.000 | 0.940 | 0.920 | 0.960 | 1.000 | 1.000 |
| `fusion-rrf+w=0.75+d=100+c=100` | keyword | 25 | 0.731 (25) | 0.744 | 1.000 | 0.644 | 0.520 | 0.840 | 0.920 | 0.960 |
| `fusion-rrf+w=0.75+d=100+c=100` | question | 25 | 0.725 (25) | 0.748 | 1.000 | 0.565 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-rrf+w=0.75+d=100+c=100` | paraphrase | 25 | 0.654 (25) | 0.648 | 1.000 | 0.321 | 0.200 | 0.480 | 0.680 | 0.800 |
| `fusion-rrf+w=0.75+d=100+c=100` | known_item | 25 | 0.711 (25) | 0.620 | 1.000 | 0.943 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.75+d=100+c=30` | keyword | 25 | 0.709 (25) | 0.720 | 1.000 | 0.643 | 0.520 | 0.880 | 0.920 | 0.960 |
| `fusion-rrf+w=0.75+d=100+c=30` | question | 25 | 0.727 (25) | 0.724 | 1.000 | 0.608 | 0.480 | 0.760 | 0.800 | 0.840 |
| `fusion-rrf+w=0.75+d=100+c=30` | paraphrase | 25 | 0.665 (25) | 0.660 | 1.000 | 0.382 | 0.280 | 0.600 | 0.760 | 0.800 |
| `fusion-rrf+w=0.75+d=100+c=30` | known_item | 25 | 0.673 (25) | 0.568 | 1.000 | 0.943 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.75+d=100+c=60` | keyword | 25 | 0.726 (25) | 0.736 | 1.000 | 0.646 | 0.520 | 0.840 | 0.920 | 0.960 |
| `fusion-rrf+w=0.75+d=100+c=60` | question | 25 | 0.721 (25) | 0.736 | 1.000 | 0.573 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-rrf+w=0.75+d=100+c=60` | paraphrase | 25 | 0.670 (25) | 0.656 | 1.000 | 0.359 | 0.280 | 0.480 | 0.680 | 0.800 |
| `fusion-rrf+w=0.75+d=100+c=60` | known_item | 25 | 0.691 (25) | 0.592 | 1.000 | 0.943 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.75+d=20+c=10` | keyword | 25 | 0.672 (25) | 0.688 | 1.000 | 0.629 | 0.520 | 0.760 | 0.880 | 0.880 |
| `fusion-rrf+w=0.75+d=20+c=10` | question | 25 | 0.706 (25) | 0.704 | 1.000 | 0.599 | 0.480 | 0.760 | 0.800 | 0.840 |
| `fusion-rrf+w=0.75+d=20+c=10` | paraphrase | 25 | 0.662 (25) | 0.648 | 1.000 | 0.458 | 0.360 | 0.560 | 0.720 | 0.800 |
| `fusion-rrf+w=0.75+d=20+c=10` | known_item | 25 | 0.651 (25) | 0.540 | 1.000 | 0.947 | 0.920 | 0.960 | 1.000 | 1.000 |
| `fusion-rrf+w=0.75+d=20+c=100` | keyword | 25 | 0.695 (25) | 0.720 | 1.000 | 0.628 | 0.520 | 0.760 | 0.880 | 0.880 |
| `fusion-rrf+w=0.75+d=20+c=100` | question | 25 | 0.706 (25) | 0.708 | 1.000 | 0.565 | 0.440 | 0.720 | 0.800 | 0.840 |
| `fusion-rrf+w=0.75+d=20+c=100` | paraphrase | 25 | 0.639 (25) | 0.640 | 1.000 | 0.361 | 0.200 | 0.560 | 0.720 | 0.800 |
| `fusion-rrf+w=0.75+d=20+c=100` | known_item | 25 | 0.671 (25) | 0.564 | 1.000 | 0.947 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.75+d=20+c=60` | keyword | 25 | 0.695 (25) | 0.720 | 1.000 | 0.628 | 0.520 | 0.760 | 0.880 | 0.880 |
| `fusion-rrf+w=0.75+d=20+c=60` | question | 25 | 0.706 (25) | 0.708 | 1.000 | 0.565 | 0.440 | 0.720 | 0.800 | 0.840 |
| `fusion-rrf+w=0.75+d=20+c=60` | paraphrase | 25 | 0.639 (25) | 0.640 | 1.000 | 0.361 | 0.200 | 0.560 | 0.720 | 0.800 |
| `fusion-rrf+w=0.75+d=20+c=60` | known_item | 25 | 0.671 (25) | 0.564 | 1.000 | 0.947 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.75+d=50+c=10` | keyword | 25 | 0.682 (25) | 0.700 | 1.000 | 0.637 | 0.520 | 0.800 | 0.920 | 0.920 |
| `fusion-rrf+w=0.75+d=50+c=10` | question | 25 | 0.705 (25) | 0.704 | 1.000 | 0.596 | 0.480 | 0.760 | 0.800 | 0.840 |
| `fusion-rrf+w=0.75+d=50+c=10` | paraphrase | 25 | 0.663 (25) | 0.648 | 1.000 | 0.458 | 0.360 | 0.560 | 0.720 | 0.800 |
| `fusion-rrf+w=0.75+d=50+c=10` | known_item | 25 | 0.651 (25) | 0.540 | 1.000 | 0.940 | 0.920 | 0.960 | 1.000 | 1.000 |
| `fusion-rrf+w=0.75+d=50+c=100` | keyword | 25 | 0.718 (25) | 0.732 | 1.000 | 0.636 | 0.520 | 0.800 | 0.880 | 0.920 |
| `fusion-rrf+w=0.75+d=50+c=100` | question | 25 | 0.709 (25) | 0.740 | 1.000 | 0.569 | 0.440 | 0.760 | 0.800 | 0.840 |
| `fusion-rrf+w=0.75+d=50+c=100` | paraphrase | 25 | 0.641 (25) | 0.644 | 1.000 | 0.317 | 0.200 | 0.480 | 0.680 | 0.800 |
| `fusion-rrf+w=0.75+d=50+c=100` | known_item | 25 | 0.718 (25) | 0.628 | 1.000 | 0.947 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=0.75+d=50+c=60` | keyword | 25 | 0.723 (25) | 0.736 | 1.000 | 0.640 | 0.520 | 0.800 | 0.920 | 0.920 |
| `fusion-rrf+w=0.75+d=50+c=60` | question | 25 | 0.710 (25) | 0.728 | 1.000 | 0.578 | 0.440 | 0.760 | 0.800 | 0.840 |
| `fusion-rrf+w=0.75+d=50+c=60` | paraphrase | 25 | 0.659 (25) | 0.652 | 1.000 | 0.340 | 0.240 | 0.480 | 0.680 | 0.800 |
| `fusion-rrf+w=0.75+d=50+c=60` | known_item | 25 | 0.688 (25) | 0.588 | 1.000 | 0.947 | 0.920 | 1.000 | 1.000 | 1.000 |
| `fusion-rrf+w=1+d=100+c=10` | keyword | 25 | 0.642 (25) | 0.676 | 1.000 | 0.577 | 0.480 | 0.800 | 0.800 | 0.880 |
| `fusion-rrf+w=1+d=100+c=10` | question | 25 | 0.688 (25) | 0.704 | 1.000 | 0.560 | 0.440 | 0.720 | 0.800 | 0.840 |
| `fusion-rrf+w=1+d=100+c=10` | paraphrase | 25 | 0.644 (25) | 0.652 | 1.000 | 0.466 | 0.400 | 0.520 | 0.720 | 0.800 |
| `fusion-rrf+w=1+d=100+c=10` | known_item | 25 | 0.600 (25) | 0.516 | 1.000 | 0.793 | 0.680 | 0.920 | 0.960 | 1.000 |
| `fusion-top1bonus+b=0.1+w=0.55+d=100+c=30` | keyword | 25 | 0.729 (25) | 0.744 | 1.000 | 0.686 | 0.560 | 0.880 | 0.960 | 0.960 |
| `fusion-top1bonus+b=0.1+w=0.55+d=100+c=30` | question | 25 | 0.722 (25) | 0.748 | 1.000 | 0.563 | 0.440 | 0.760 | 0.760 | 0.800 |
| `fusion-top1bonus+b=0.1+w=0.55+d=100+c=30` | paraphrase | 25 | 0.655 (25) | 0.640 | 1.000 | 0.383 | 0.280 | 0.520 | 0.680 | 0.800 |
| `fusion-top1bonus+b=0.1+w=0.55+d=100+c=30` | known_item | 25 | 0.713 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `fusion-top1bonus+b=0.25+w=0.55+d=100+c=30` | keyword | 25 | 0.726 (25) | 0.740 | 1.000 | 0.707 | 0.600 | 0.920 | 0.960 | 0.960 |
| `fusion-top1bonus+b=0.25+w=0.55+d=100+c=30` | question | 25 | 0.726 (25) | 0.748 | 1.000 | 0.541 | 0.400 | 0.720 | 0.760 | 0.800 |
| `fusion-top1bonus+b=0.25+w=0.55+d=100+c=30` | paraphrase | 25 | 0.644 (25) | 0.636 | 1.000 | 0.382 | 0.280 | 0.520 | 0.680 | 0.800 |
| `fusion-top1bonus+b=0.25+w=0.55+d=100+c=30` | known_item | 25 | 0.713 (25) | 0.624 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `hybrid-bge-small+linear+w=0.25` | keyword | 25 | 0.693 (25) | 0.688 | 0.960 | 0.700 | 0.520 | 0.880 | 0.920 | 0.920 |
| `hybrid-bge-small+linear+w=0.25` | question | 25 | 0.561 (25) | 0.528 | 0.952 | 0.521 | 0.440 | 0.640 | 0.680 | 0.720 |
| `hybrid-bge-small+linear+w=0.25` | paraphrase | 25 | 0.467 (25) | 0.504 | 0.956 | 0.178 | 0.080 | 0.320 | 0.360 | 0.360 |
| `hybrid-bge-small+linear+w=0.25` | known_item | 25 | 0.705 (25) | 0.612 | 0.956 | 0.948 | 0.920 | 1.000 | 1.000 | 1.000 |
| `hybrid-bge-small+linear+w=0.5` | keyword | 25 | 0.688 (25) | 0.676 | 0.896 | 0.653 | 0.480 | 0.880 | 0.880 | 0.960 |
| `hybrid-bge-small+linear+w=0.5` | question | 25 | 0.613 (25) | 0.592 | 0.880 | 0.519 | 0.440 | 0.600 | 0.720 | 0.760 |
| `hybrid-bge-small+linear+w=0.5` | paraphrase | 25 | 0.504 (25) | 0.528 | 0.872 | 0.211 | 0.120 | 0.320 | 0.560 | 0.600 |
| `hybrid-bge-small+linear+w=0.5` | known_item | 25 | 0.704 (25) | 0.608 | 0.908 | 0.891 | 0.840 | 0.960 | 1.000 | 1.000 |
| `hybrid-bge-small+linear+w=0.75` | keyword | 25 | 0.672 (25) | 0.656 | 0.924 | 0.667 | 0.560 | 0.840 | 0.920 | 0.960 |
| `hybrid-bge-small+linear+w=0.75` | question | 25 | 0.644 (25) | 0.652 | 0.956 | 0.495 | 0.400 | 0.640 | 0.680 | 0.760 |
| `hybrid-bge-small+linear+w=0.75` | paraphrase | 25 | 0.495 (25) | 0.528 | 0.932 | 0.217 | 0.120 | 0.360 | 0.400 | 0.640 |
| `hybrid-bge-small+linear+w=0.75` | known_item | 25 | 0.705 (25) | 0.612 | 0.944 | 0.856 | 0.800 | 0.920 | 0.960 | 0.960 |
| `hybrid-bge-small+rrf+w=0.25+c=10` | keyword | 25 | 0.660 (25) | 0.648 | 0.996 | 0.727 | 0.560 | 0.920 | 0.920 | 0.960 |
| `hybrid-bge-small+rrf+w=0.25+c=10` | question | 25 | 0.501 (25) | 0.484 | 1.000 | 0.485 | 0.400 | 0.560 | 0.680 | 0.720 |
| `hybrid-bge-small+rrf+w=0.25+c=10` | paraphrase | 25 | 0.384 (25) | 0.448 | 1.000 | 0.152 | 0.080 | 0.240 | 0.320 | 0.360 |
| `hybrid-bge-small+rrf+w=0.25+c=10` | known_item | 25 | 0.682 (25) | 0.600 | 0.988 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `hybrid-bge-small+rrf+w=0.25+c=100` | keyword | 25 | 0.679 (25) | 0.660 | 0.920 | 0.700 | 0.520 | 0.880 | 0.920 | 0.920 |
| `hybrid-bge-small+rrf+w=0.25+c=100` | question | 25 | 0.588 (25) | 0.568 | 0.920 | 0.522 | 0.440 | 0.640 | 0.680 | 0.720 |
| `hybrid-bge-small+rrf+w=0.25+c=100` | paraphrase | 25 | 0.488 (25) | 0.520 | 0.900 | 0.180 | 0.080 | 0.320 | 0.400 | 0.440 |
| `hybrid-bge-small+rrf+w=0.25+c=100` | known_item | 25 | 0.706 (25) | 0.616 | 0.940 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `hybrid-bge-small+rrf+w=0.25+c=60` | keyword | 25 | 0.679 (25) | 0.668 | 0.964 | 0.703 | 0.520 | 0.920 | 0.920 | 0.920 |
| `hybrid-bge-small+rrf+w=0.25+c=60` | question | 25 | 0.569 (25) | 0.540 | 0.948 | 0.520 | 0.440 | 0.640 | 0.680 | 0.720 |
| `hybrid-bge-small+rrf+w=0.25+c=60` | paraphrase | 25 | 0.464 (25) | 0.516 | 0.952 | 0.157 | 0.040 | 0.320 | 0.360 | 0.400 |
| `hybrid-bge-small+rrf+w=0.25+c=60` | known_item | 25 | 0.706 (25) | 0.624 | 0.972 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |
| `hybrid-bge-small+rrf+w=0.5+c=10` | keyword | 25 | 0.696 (25) | 0.692 | 1.000 | 0.709 | 0.560 | 0.960 | 0.960 | 0.960 |
| `hybrid-bge-small+rrf+w=0.5+c=10` | question | 25 | 0.622 (25) | 0.616 | 1.000 | 0.536 | 0.440 | 0.680 | 0.720 | 0.760 |
| `hybrid-bge-small+rrf+w=0.5+c=10` | paraphrase | 25 | 0.480 (25) | 0.528 | 1.000 | 0.232 | 0.120 | 0.440 | 0.480 | 0.680 |
| `hybrid-bge-small+rrf+w=0.5+c=10` | known_item | 25 | 0.714 (25) | 0.620 | 1.000 | 0.930 | 0.880 | 1.000 | 1.000 | 1.000 |
| `hybrid-bge-small+rrf+w=0.5+c=100` | keyword | 25 | 0.691 (25) | 0.672 | 0.876 | 0.673 | 0.520 | 0.880 | 0.880 | 0.960 |
| `hybrid-bge-small+rrf+w=0.5+c=100` | question | 25 | 0.604 (25) | 0.576 | 0.852 | 0.514 | 0.440 | 0.640 | 0.680 | 0.760 |
| `hybrid-bge-small+rrf+w=0.5+c=100` | paraphrase | 25 | 0.507 (25) | 0.520 | 0.820 | 0.233 | 0.160 | 0.400 | 0.520 | 0.560 |
| `hybrid-bge-small+rrf+w=0.5+c=100` | known_item | 25 | 0.705 (25) | 0.608 | 0.880 | 0.891 | 0.840 | 0.960 | 1.000 | 1.000 |
| `hybrid-bge-small+rrf+w=0.5+c=60` | keyword | 25 | 0.697 (25) | 0.680 | 0.904 | 0.673 | 0.520 | 0.880 | 0.880 | 0.960 |
| `hybrid-bge-small+rrf+w=0.5+c=60` | question | 25 | 0.615 (25) | 0.600 | 0.876 | 0.516 | 0.440 | 0.640 | 0.680 | 0.760 |
| `hybrid-bge-small+rrf+w=0.5+c=60` | paraphrase | 25 | 0.506 (25) | 0.516 | 0.844 | 0.240 | 0.160 | 0.360 | 0.560 | 0.560 |
| `hybrid-bge-small+rrf+w=0.5+c=60` | known_item | 25 | 0.705 (25) | 0.604 | 0.884 | 0.892 | 0.840 | 0.960 | 1.000 | 1.000 |
| `hybrid-bge-small+rrf+w=0.75+c=10` | keyword | 25 | 0.657 (25) | 0.672 | 1.000 | 0.656 | 0.560 | 0.760 | 0.880 | 0.960 |
| `hybrid-bge-small+rrf+w=0.75+c=10` | question | 25 | 0.627 (25) | 0.648 | 0.992 | 0.475 | 0.400 | 0.600 | 0.680 | 0.760 |
| `hybrid-bge-small+rrf+w=0.75+c=10` | paraphrase | 25 | 0.487 (25) | 0.532 | 0.996 | 0.281 | 0.200 | 0.360 | 0.520 | 0.640 |
| `hybrid-bge-small+rrf+w=0.75+c=10` | known_item | 25 | 0.679 (25) | 0.612 | 1.000 | 0.797 | 0.720 | 0.880 | 0.960 | 1.000 |
| `hybrid-bge-small+rrf+w=0.75+c=100` | keyword | 25 | 0.672 (25) | 0.660 | 0.880 | 0.666 | 0.560 | 0.880 | 0.920 | 0.960 |
| `hybrid-bge-small+rrf+w=0.75+c=100` | question | 25 | 0.624 (25) | 0.616 | 0.884 | 0.491 | 0.400 | 0.600 | 0.720 | 0.760 |
| `hybrid-bge-small+rrf+w=0.75+c=100` | paraphrase | 25 | 0.507 (25) | 0.544 | 0.892 | 0.239 | 0.160 | 0.360 | 0.440 | 0.680 |
| `hybrid-bge-small+rrf+w=0.75+c=100` | known_item | 25 | 0.701 (25) | 0.596 | 0.920 | 0.856 | 0.800 | 0.920 | 0.960 | 1.000 |
| `hybrid-bge-small+rrf+w=0.75+c=60` | keyword | 25 | 0.672 (25) | 0.664 | 0.936 | 0.665 | 0.560 | 0.880 | 0.920 | 0.960 |
| `hybrid-bge-small+rrf+w=0.75+c=60` | question | 25 | 0.641 (25) | 0.648 | 0.948 | 0.482 | 0.400 | 0.640 | 0.680 | 0.800 |
| `hybrid-bge-small+rrf+w=0.75+c=60` | paraphrase | 25 | 0.491 (25) | 0.532 | 0.924 | 0.242 | 0.160 | 0.360 | 0.440 | 0.640 |
| `hybrid-bge-small+rrf+w=0.75+c=60` | known_item | 25 | 0.706 (25) | 0.612 | 0.960 | 0.856 | 0.800 | 0.920 | 0.960 | 0.960 |
| `hybrid-gte-small+linear+w=0.25` | keyword | 25 | 0.663 (25) | 0.636 | 0.944 | 0.677 | 0.520 | 0.920 | 0.920 | 0.920 |
| `hybrid-gte-small+linear+w=0.25` | question | 25 | 0.575 (25) | 0.560 | 0.968 | 0.522 | 0.440 | 0.640 | 0.680 | 0.720 |
| `hybrid-gte-small+linear+w=0.25` | paraphrase | 25 | 0.467 (25) | 0.516 | 0.964 | 0.172 | 0.040 | 0.320 | 0.360 | 0.400 |
| `hybrid-gte-small+linear+w=0.25` | known_item | 25 | 0.717 (25) | 0.624 | 0.948 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `hybrid-gte-small+linear+w=0.5` | keyword | 25 | 0.684 (25) | 0.644 | 0.864 | 0.707 | 0.600 | 0.800 | 0.840 | 0.960 |
| `hybrid-gte-small+linear+w=0.5` | question | 25 | 0.612 (25) | 0.612 | 0.892 | 0.531 | 0.440 | 0.640 | 0.680 | 0.760 |
| `hybrid-gte-small+linear+w=0.5` | paraphrase | 25 | 0.525 (25) | 0.560 | 0.896 | 0.255 | 0.120 | 0.440 | 0.520 | 0.520 |
| `hybrid-gte-small+linear+w=0.5` | known_item | 25 | 0.703 (25) | 0.596 | 0.888 | 0.920 | 0.880 | 1.000 | 1.000 | 1.000 |
| `hybrid-gte-small+linear+w=0.75` | keyword | 25 | 0.694 (25) | 0.668 | 0.924 | 0.712 | 0.640 | 0.800 | 0.880 | 0.880 |
| `hybrid-gte-small+linear+w=0.75` | question | 25 | 0.633 (25) | 0.656 | 0.960 | 0.469 | 0.320 | 0.640 | 0.720 | 0.800 |
| `hybrid-gte-small+linear+w=0.75` | paraphrase | 25 | 0.544 (25) | 0.568 | 0.952 | 0.298 | 0.160 | 0.480 | 0.480 | 0.640 |
| `hybrid-gte-small+linear+w=0.75` | known_item | 25 | 0.681 (25) | 0.592 | 0.952 | 0.801 | 0.720 | 0.920 | 0.960 | 1.000 |
| `hybrid-gte-small+rrf+w=0.25+c=10` | keyword | 25 | 0.654 (25) | 0.640 | 1.000 | 0.707 | 0.560 | 0.880 | 0.920 | 0.960 |
| `hybrid-gte-small+rrf+w=0.25+c=10` | question | 25 | 0.497 (25) | 0.480 | 1.000 | 0.479 | 0.400 | 0.560 | 0.680 | 0.720 |
| `hybrid-gte-small+rrf+w=0.25+c=10` | paraphrase | 25 | 0.389 (25) | 0.448 | 1.000 | 0.151 | 0.080 | 0.240 | 0.280 | 0.400 |
| `hybrid-gte-small+rrf+w=0.25+c=10` | known_item | 25 | 0.697 (25) | 0.620 | 0.996 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `hybrid-gte-small+rrf+w=0.25+c=100` | keyword | 25 | 0.669 (25) | 0.640 | 0.908 | 0.672 | 0.520 | 0.880 | 0.920 | 0.920 |
| `hybrid-gte-small+rrf+w=0.25+c=100` | question | 25 | 0.582 (25) | 0.576 | 0.928 | 0.519 | 0.440 | 0.640 | 0.680 | 0.720 |
| `hybrid-gte-small+rrf+w=0.25+c=100` | paraphrase | 25 | 0.497 (25) | 0.536 | 0.908 | 0.191 | 0.080 | 0.320 | 0.360 | 0.440 |
| `hybrid-gte-small+rrf+w=0.25+c=100` | known_item | 25 | 0.712 (25) | 0.612 | 0.928 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `hybrid-gte-small+rrf+w=0.25+c=60` | keyword | 25 | 0.672 (25) | 0.660 | 0.964 | 0.677 | 0.520 | 0.920 | 0.920 | 0.920 |
| `hybrid-gte-small+rrf+w=0.25+c=60` | question | 25 | 0.567 (25) | 0.552 | 0.952 | 0.519 | 0.440 | 0.640 | 0.680 | 0.720 |
| `hybrid-gte-small+rrf+w=0.25+c=60` | paraphrase | 25 | 0.473 (25) | 0.516 | 0.956 | 0.175 | 0.080 | 0.320 | 0.320 | 0.400 |
| `hybrid-gte-small+rrf+w=0.25+c=60` | known_item | 25 | 0.714 (25) | 0.616 | 0.956 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `hybrid-gte-small+rrf+w=0.5+c=10` | keyword | 25 | 0.708 (25) | 0.688 | 1.000 | 0.728 | 0.600 | 0.920 | 0.960 | 0.960 |
| `hybrid-gte-small+rrf+w=0.5+c=10` | question | 25 | 0.602 (25) | 0.596 | 1.000 | 0.518 | 0.400 | 0.640 | 0.720 | 0.760 |
| `hybrid-gte-small+rrf+w=0.5+c=10` | paraphrase | 25 | 0.514 (25) | 0.556 | 1.000 | 0.321 | 0.200 | 0.480 | 0.520 | 0.640 |
| `hybrid-gte-small+rrf+w=0.5+c=10` | known_item | 25 | 0.700 (25) | 0.604 | 1.000 | 0.973 | 0.960 | 1.000 | 1.000 | 1.000 |
| `hybrid-gte-small+rrf+w=0.5+c=100` | keyword | 25 | 0.681 (25) | 0.624 | 0.840 | 0.701 | 0.600 | 0.800 | 0.880 | 0.960 |
| `hybrid-gte-small+rrf+w=0.5+c=100` | question | 25 | 0.610 (25) | 0.596 | 0.860 | 0.507 | 0.400 | 0.640 | 0.680 | 0.760 |
| `hybrid-gte-small+rrf+w=0.5+c=100` | paraphrase | 25 | 0.517 (25) | 0.536 | 0.840 | 0.276 | 0.160 | 0.440 | 0.520 | 0.520 |
| `hybrid-gte-small+rrf+w=0.5+c=100` | known_item | 25 | 0.707 (25) | 0.608 | 0.876 | 0.920 | 0.880 | 1.000 | 1.000 | 1.000 |
| `hybrid-gte-small+rrf+w=0.5+c=60` | keyword | 25 | 0.686 (25) | 0.636 | 0.876 | 0.702 | 0.600 | 0.800 | 0.880 | 0.960 |
| `hybrid-gte-small+rrf+w=0.5+c=60` | question | 25 | 0.615 (25) | 0.608 | 0.876 | 0.507 | 0.400 | 0.640 | 0.680 | 0.760 |
| `hybrid-gte-small+rrf+w=0.5+c=60` | paraphrase | 25 | 0.524 (25) | 0.544 | 0.860 | 0.282 | 0.160 | 0.400 | 0.520 | 0.520 |
| `hybrid-gte-small+rrf+w=0.5+c=60` | known_item | 25 | 0.706 (25) | 0.604 | 0.892 | 0.920 | 0.880 | 1.000 | 1.000 | 1.000 |
| `hybrid-gte-small+rrf+w=0.75+c=10` | keyword | 25 | 0.675 (25) | 0.656 | 0.996 | 0.703 | 0.600 | 0.840 | 0.840 | 0.920 |
| `hybrid-gte-small+rrf+w=0.75+c=10` | question | 25 | 0.624 (25) | 0.656 | 1.000 | 0.469 | 0.360 | 0.640 | 0.720 | 0.800 |
| `hybrid-gte-small+rrf+w=0.75+c=10` | paraphrase | 25 | 0.527 (25) | 0.552 | 0.992 | 0.366 | 0.280 | 0.480 | 0.520 | 0.680 |
| `hybrid-gte-small+rrf+w=0.75+c=10` | known_item | 25 | 0.640 (25) | 0.564 | 1.000 | 0.766 | 0.680 | 0.880 | 0.960 | 1.000 |
| `hybrid-gte-small+rrf+w=0.75+c=100` | keyword | 25 | 0.695 (25) | 0.664 | 0.892 | 0.714 | 0.640 | 0.800 | 0.880 | 0.920 |
| `hybrid-gte-small+rrf+w=0.75+c=100` | question | 25 | 0.636 (25) | 0.652 | 0.936 | 0.468 | 0.320 | 0.640 | 0.720 | 0.800 |
| `hybrid-gte-small+rrf+w=0.75+c=100` | paraphrase | 25 | 0.545 (25) | 0.560 | 0.896 | 0.323 | 0.240 | 0.400 | 0.480 | 0.600 |
| `hybrid-gte-small+rrf+w=0.75+c=100` | known_item | 25 | 0.686 (25) | 0.600 | 0.916 | 0.805 | 0.720 | 0.920 | 1.000 | 1.000 |
| `hybrid-gte-small+rrf+w=0.75+c=60` | keyword | 25 | 0.692 (25) | 0.664 | 0.924 | 0.716 | 0.640 | 0.840 | 0.880 | 0.920 |
| `hybrid-gte-small+rrf+w=0.75+c=60` | question | 25 | 0.645 (25) | 0.664 | 0.968 | 0.489 | 0.360 | 0.640 | 0.720 | 0.800 |
| `hybrid-gte-small+rrf+w=0.75+c=60` | paraphrase | 25 | 0.557 (25) | 0.580 | 0.944 | 0.333 | 0.240 | 0.480 | 0.480 | 0.640 |
| `hybrid-gte-small+rrf+w=0.75+c=60` | known_item | 25 | 0.686 (25) | 0.600 | 0.960 | 0.806 | 0.720 | 0.920 | 1.000 | 1.000 |
| `hybrid-openai-large+rrf+w=0.5+c=10` | keyword | 25 | 0.696 (25) | 0.692 | 1.000 | 0.717 | 0.600 | 0.920 | 0.960 | 1.000 |
| `hybrid-openai-large+rrf+w=0.5+c=10` | question | 25 | 0.662 (25) | 0.660 | 1.000 | 0.553 | 0.440 | 0.760 | 0.760 | 0.800 |
| `hybrid-openai-large+rrf+w=0.5+c=10` | paraphrase | 25 | 0.591 (25) | 0.576 | 1.000 | 0.364 | 0.240 | 0.520 | 0.640 | 0.800 |
| `hybrid-openai-large+rrf+w=0.5+c=10` | known_item | 25 | 0.692 (25) | 0.604 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `score-max+w=0.35+d=100` | keyword | 25 | 0.722 (25) | 0.740 | 1.000 | 0.727 | 0.600 | 0.880 | 0.880 | 0.960 |
| `score-max+w=0.35+d=100` | question | 25 | 0.667 (25) | 0.688 | 1.000 | 0.510 | 0.400 | 0.640 | 0.720 | 0.720 |
| `score-max+w=0.35+d=100` | paraphrase | 25 | 0.586 (25) | 0.612 | 1.000 | 0.307 | 0.240 | 0.400 | 0.400 | 0.440 |
| `score-max+w=0.35+d=100` | known_item | 25 | 0.721 (25) | 0.640 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `score-max+w=0.35+d=500` | keyword | 25 | 0.712 (25) | 0.716 | 1.000 | 0.732 | 0.600 | 0.880 | 0.920 | 0.960 |
| `score-max+w=0.35+d=500` | question | 25 | 0.605 (25) | 0.628 | 1.000 | 0.502 | 0.400 | 0.640 | 0.720 | 0.720 |
| `score-max+w=0.35+d=500` | paraphrase | 25 | 0.510 (25) | 0.540 | 1.000 | 0.241 | 0.160 | 0.360 | 0.440 | 0.520 |
| `score-max+w=0.35+d=500` | known_item | 25 | 0.723 (25) | 0.656 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `score-max+w=0.55+d=100` | keyword | 25 | 0.739 (25) | 0.748 | 1.000 | 0.775 | 0.680 | 0.920 | 0.920 | 0.960 |
| `score-max+w=0.55+d=100` | question | 25 | 0.702 (25) | 0.716 | 1.000 | 0.532 | 0.400 | 0.680 | 0.720 | 0.800 |
| `score-max+w=0.55+d=100` | paraphrase | 25 | 0.633 (25) | 0.648 | 1.000 | 0.336 | 0.240 | 0.440 | 0.520 | 0.680 |
| `score-max+w=0.55+d=100` | known_item | 25 | 0.724 (25) | 0.632 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `score-max+w=0.55+d=500` | keyword | 25 | 0.737 (25) | 0.728 | 1.000 | 0.779 | 0.680 | 0.920 | 0.960 | 1.000 |
| `score-max+w=0.55+d=500` | question | 25 | 0.681 (25) | 0.704 | 1.000 | 0.532 | 0.400 | 0.680 | 0.720 | 0.720 |
| `score-max+w=0.55+d=500` | paraphrase | 25 | 0.604 (25) | 0.600 | 1.000 | 0.336 | 0.240 | 0.440 | 0.560 | 0.640 |
| `score-max+w=0.55+d=500` | known_item | 25 | 0.728 (25) | 0.648 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `score-max+w=0.75+d=100` | keyword | 25 | 0.731 (25) | 0.732 | 1.000 | 0.716 | 0.600 | 0.880 | 0.920 | 0.960 |
| `score-max+w=0.75+d=100` | question | 25 | 0.727 (25) | 0.728 | 1.000 | 0.583 | 0.480 | 0.720 | 0.720 | 0.800 |
| `score-max+w=0.75+d=100` | paraphrase | 25 | 0.660 (25) | 0.652 | 1.000 | 0.394 | 0.320 | 0.440 | 0.640 | 0.720 |
| `score-max+w=0.75+d=100` | known_item | 25 | 0.727 (25) | 0.632 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `score-max+w=0.75+d=500` | keyword | 25 | 0.732 (25) | 0.740 | 1.000 | 0.716 | 0.600 | 0.880 | 0.920 | 0.960 |
| `score-max+w=0.75+d=500` | question | 25 | 0.725 (25) | 0.732 | 1.000 | 0.583 | 0.480 | 0.720 | 0.720 | 0.760 |
| `score-max+w=0.75+d=500` | paraphrase | 25 | 0.695 (25) | 0.680 | 1.000 | 0.487 | 0.400 | 0.600 | 0.640 | 0.640 |
| `score-max+w=0.75+d=500` | known_item | 25 | 0.726 (25) | 0.636 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `score-minmax+w=0.35+d=100` | keyword | 25 | 0.701 (25) | 0.688 | 1.000 | 0.732 | 0.600 | 0.880 | 0.920 | 1.000 |
| `score-minmax+w=0.35+d=100` | question | 25 | 0.578 (25) | 0.560 | 1.000 | 0.516 | 0.400 | 0.640 | 0.720 | 0.760 |
| `score-minmax+w=0.35+d=100` | paraphrase | 25 | 0.482 (25) | 0.492 | 1.000 | 0.256 | 0.160 | 0.360 | 0.520 | 0.680 |
| `score-minmax+w=0.35+d=100` | known_item | 25 | 0.680 (25) | 0.568 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `score-minmax+w=0.35+d=500` | keyword | 25 | 0.717 (25) | 0.712 | 1.000 | 0.736 | 0.600 | 0.880 | 0.960 | 1.000 |
| `score-minmax+w=0.35+d=500` | question | 25 | 0.624 (25) | 0.628 | 1.000 | 0.519 | 0.400 | 0.680 | 0.720 | 0.720 |
| `score-minmax+w=0.35+d=500` | paraphrase | 25 | 0.532 (25) | 0.556 | 1.000 | 0.268 | 0.160 | 0.440 | 0.480 | 0.600 |
| `score-minmax+w=0.35+d=500` | known_item | 25 | 0.707 (25) | 0.608 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `score-minmax+w=0.55+d=100` | keyword | 25 | 0.709 (25) | 0.700 | 1.000 | 0.700 | 0.560 | 0.880 | 0.920 | 1.000 |
| `score-minmax+w=0.55+d=100` | question | 25 | 0.707 (25) | 0.712 | 1.000 | 0.586 | 0.440 | 0.760 | 0.800 | 0.800 |
| `score-minmax+w=0.55+d=100` | paraphrase | 25 | 0.643 (25) | 0.600 | 1.000 | 0.492 | 0.400 | 0.640 | 0.680 | 0.800 |
| `score-minmax+w=0.55+d=100` | known_item | 25 | 0.682 (25) | 0.576 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `score-minmax+w=0.55+d=500` | keyword | 25 | 0.727 (25) | 0.728 | 1.000 | 0.699 | 0.560 | 0.880 | 0.920 | 1.000 |
| `score-minmax+w=0.55+d=500` | question | 25 | 0.706 (25) | 0.724 | 1.000 | 0.560 | 0.440 | 0.680 | 0.760 | 0.800 |
| `score-minmax+w=0.55+d=500` | paraphrase | 25 | 0.669 (25) | 0.636 | 1.000 | 0.498 | 0.400 | 0.600 | 0.680 | 0.720 |
| `score-minmax+w=0.55+d=500` | known_item | 25 | 0.710 (25) | 0.608 | 1.000 | 0.980 | 0.960 | 1.000 | 1.000 | 1.000 |
| `score-minmax+w=0.75+d=100` | keyword | 25 | 0.678 (25) | 0.696 | 1.000 | 0.642 | 0.520 | 0.880 | 0.920 | 0.960 |
| `score-minmax+w=0.75+d=100` | question | 25 | 0.712 (25) | 0.716 | 1.000 | 0.596 | 0.480 | 0.760 | 0.800 | 0.840 |
| `score-minmax+w=0.75+d=100` | paraphrase | 25 | 0.678 (25) | 0.660 | 1.000 | 0.496 | 0.440 | 0.600 | 0.720 | 0.800 |
| `score-minmax+w=0.75+d=100` | known_item | 25 | 0.648 (25) | 0.532 | 1.000 | 0.950 | 0.920 | 1.000 | 1.000 | 1.000 |
| `score-minmax+w=0.75+d=500` | keyword | 25 | 0.697 (25) | 0.704 | 1.000 | 0.669 | 0.560 | 0.880 | 0.920 | 0.960 |
| `score-minmax+w=0.75+d=500` | question | 25 | 0.727 (25) | 0.736 | 1.000 | 0.602 | 0.480 | 0.760 | 0.800 | 0.840 |
| `score-minmax+w=0.75+d=500` | paraphrase | 25 | 0.695 (25) | 0.672 | 1.000 | 0.504 | 0.440 | 0.600 | 0.720 | 0.800 |
| `score-minmax+w=0.75+d=500` | known_item | 25 | 0.667 (25) | 0.560 | 1.000 | 0.960 | 0.920 | 1.000 | 1.000 | 1.000 |

## Report inventory (separate historical scopes)

- [dev/tuning/bm25+exact+stems+authors+title2x.json](../dev/tuning/bm25%2Bexact%2Bstems%2Bauthors%2Btitle2x.json) — BM25 tuning, source-paper objective
- [dev/tuning/bm25+exact+stems+authors.json](../dev/tuning/bm25%2Bexact%2Bstems%2Bauthors.json) — BM25 tuning, source-paper objective
- [dev/tuning/bm25+stop+exact+stems+authors+title2x.json](../dev/tuning/bm25%2Bstop%2Bexact%2Bstems%2Bauthors%2Btitle2x.json) — BM25 tuning, source-paper objective
- [embedding-pilot/report.md](../embedding-pilot/report.md) — reduced-corpus embedding pilot, separate scope
- [failure-analysis/report.md](../failure-analysis/report.md) — historical report/configuration; original scope
- [fusion-dev/configs.json](../fusion-dev/configs.json) — historical report/configuration; original scope
- [fusion-dev/report.json](../fusion-dev/report.json) — historical report/configuration; original scope
- [fusion-dev/report.md](../fusion-dev/report.md) — historical report/configuration; original scope
- [fusion-review-dev/report.json](../fusion-review-dev/report.json) — historical report/configuration; original scope
- [fusion-review-dev/report.md](../fusion-review-dev/report.md) — historical report/configuration; original scope
- [graded-dev/report.md](../graded-dev/report.md) — historical report/configuration; original scope
- [refinement-dev/configs.json](../refinement-dev/configs.json) — historical report/configuration; original scope
- [refinement-dev/report.md](../refinement-dev/report.md) — historical report/configuration; original scope
- [score-fusion-dev/configs.json](../score-fusion-dev/configs.json) — historical report/configuration; original scope
- [score-fusion-dev/report.json](../score-fusion-dev/report.json) — historical report/configuration; original scope
- [score-fusion-dev/report.md](../score-fusion-dev/report.md) — historical report/configuration; original scope
