# What did low reasoning change?

Offline descriptive analysis of the same frozen pilot20. No provider requests,
credential reads, ledger access, remaining80 evaluation or label changes.
The [machine-readable report](report.json) contains full abstracts, scores,
ranking changes, exact per-paper nDCG contributions and input hashes.

## Measured result

| Measure | Result |
|---|---:|
| Non-reasoning score-only averaged nDCG@10 | 0.829053 |
| Low-reasoning score-only averaged nDCG@10 | 0.844317 |
| Paired difference | +0.015264 |
| Previously reported paired 95% interval | [-0.002362, +0.034424] |
| Unequal-grade inversions corrected, across all top20 pairs | 90 |
| Unequal-grade inversions introduced, across all top20 pairs | 58 |
| New top10 entrants: grade2 / grade1 / grade0 | 6 / 11 / 4 |
| Top10 exits: grade2 / grade1 / grade0 | 3 / 12 / 6 |

These are pooled model grades, not human ground truth. Pair counts weight every
pair equally and include ranks11-20; they do not measure nDCG or causal effects.
Summing exact per-paper discounted contributions reproduces every query delta.

The twelve improving queries contribute +0.023009 to the twenty-query mean,
while the seven regressing queries subtract 0.007746. One query is unchanged.
The two largest positive deltas are 46.2% of the gross positive query gains.
Excluding those two leaves a descriptive mean delta of about +0.00514 over18
queries. This is a sensitivity diagnostic, not permission to redefine the set.

## Highest-impact evidence checks

### Unknown knowledge graphs: +0.13552

Query: "can standard graph neural networks perform link prediction on unknown
knowledge graphs?"

- **TIEG-Youpu Solution for NeurIPS 2022 WikiKG90Mv2-LSC** (2603.28512,
  grade2) moves13 ->8, contributing +0.08880. Its averaged score rises only
  2.5 ->3. The abstract describes large-scale graph embeddings, candidate
  retrieval and ensemble reranking. It does not clearly establish transfer of
  standard GNNs to unknown knowledge graphs.
- **Multi-Faceted Continual Knowledge Graph Embedding for Semantic-Aware Link
  Prediction** (2604.10947, grade2) moves11 ->10, contributing +0.08137,
  despite an unchanged average score of2.5. Other papers' score changes move
  it across the boundary. The abstract concerns continual embeddings for new
  knowledge, not clearly the requested standard-GNN transfer capability.

These grade2 assignments merit a blinded relevance review. They are not changed
here, and the observations do not establish that the labels are wrong.
Their low absolute scores also mean the reasoning model was not necessarily
recognizing either paper as a direct answer.

### General-purpose atmospheric model: +0.07717

Query: "Can a single general purpose model be used for various atmospheric
science tasks?"

**Scalable and Trustworthy Earth Observation Foundation Models** (2607.07758,
grade2) moves14 ->10, contributing the entire net gain of +0.07717. Its score
rises2 ->4. The abstract is a review of remote-sensing foundation models and
adaptation, including evidence that no single geospatial model is universally
best. It is plausibly useful background, but not clearly a direct demonstration
of one model across atmospheric tasks. This is another label-review candidate,
not clean evidence that a stricter task-matching prompt will reproduce the gain.

### Avoiding error-signal propagation: +0.07508

Query: "reducing data exchange by avoiding error signal propagation in shared
neural architectures"

**Communication-Efficient LLM Adaptation over Decentralized GPU Meshes**
(2609.14339, grade2) moves6 ->2, contributing +0.07334. Scores change[4,6] ->
[6,6]. Its compressed fast circuit and occasional unmasked forward-backward
anchor passes establish related communication savings, but do not clearly
establish elimination of error-signal propagation. This can reflect improved
partial-match calibration or merely score variability; it is not proof of
better essential-constraint detection.

### Low-precision distributed/private training: -0.05841

Query: "a comprehensive look at using low precision numbers to speed up training
across distributed private devices"

**Understanding and Exploiting Weight Update Sparsity for Communication-Efficient
Distributed RL** (2602.03839, grade2) moves10 ->11, contributing -0.08662,
despite unchanged averaged score4.5. Its abstract explicitly connects BF16
rounding and distributed synchronization savings. Other promotions displace it.
Meanwhile the grade2 AGoQ paper moves4 ->2, contributing +0.06001.
Reasoning improves one useful ordering while damaging the top10 boundary.

### Sociodemographic alignment lookup: -0.06635

Query: "shani-narkiss ai alignment sociodemographic"

The known source stays pinned at1. **Group Alignment-Induced Sycophancy**
(2608.11528, grade2) moves2 ->4, contributing -0.05637, as its average score
drops7 ->6. The abstract explicitly studies alignment to demographic groups.
Reasoning does not consistently improve the order of related work even when
source-paper protection works.

## Interpretation and next candidate

There is no clean, universal "reasoning found the missing constraint" explanation.
Some wins are weakly supported by the query/abstract evidence, and some come from
half-point changes around ties. In particular, a paper moving up without its own
score changing is not evidence that the model understood that paper better.
Hidden reasoning text was not requested or saved; the model's rationale is unknown.

The existing prompt already distinguishes main contributions, related work and
missing constraints. Repeating that instruction or introducing a rigid facet
checklist is not a well-supported next step.

A narrow **untested** non-reasoning prompt hypothesis is better partial-match
calibration. A possible addition to the existing prompt, without changing its
schema, score anchors or evidence policy, is:

> Distinguish an explicit mismatch from an important detail that the abstract
> does not establish. Missing evidence prevents the highest scores, but does not
> erase a paper's supported partial relevance. Judge the supported relationship
> to the requested task rather than keyword overlap, and never assume an
> unreported capability.

This is a proposal, not a frozen paid experiment or a claim that the gap is
closed. It may add little beyond the existing instructions, or make partial
matches too generous. It must not be tuned to the listed query IDs or labels.
No explanations or extra JSON fields are needed, limiting visible-output growth;
runtime and quality would still need measurement.

Before spending on that prompt, prioritize a blinded audit of the high-impact
query-paper labels above using the existing rubric. Do not silently replace
labels or rescore only selected cases as if that were confirmation. Any accepted
correction needs a separately versioned snapshot and matched rescoring of every
candidate on the same pilot scope. Preserve the remaining80 for a frozen
candidate confirmation.

The 0.8443 result is a useful diagnostic target, not a reliable production-quality
requirement. Selecting a new prompt after this analysis remains pilot overfitting
risk; no promotion, deployment or new spending is authorized by this report.
