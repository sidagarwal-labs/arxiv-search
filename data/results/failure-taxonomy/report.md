# Decision 50 failure taxonomy (dev)

**Scope:** the saved Decision 50 ranking on the **100 dev queries**, scored on the completed top-20 label layer (3,678 pairs: 3,479 GPT-5.4 mini judge, 100 GPT-6 ASTRA reference override, 99 GPT-6 Terra top-20 completion). Grades are LLM judgments, not human-validated. Cause labels are **AI-assisted annotation** by a single annotator (no inter-annotator agreement). Held-out queries were not read or scored; no API calls or new labels. The only new ranking is the offline unpinned fix test, rebuilt from saved replies.

Reproduction check: nDCG@10 **0.8418**, source MRR@10 **0.7659**, source R@10 **93%** match the published [dev100 summary](../top20-confirm/dev100-summary.json).

Segment cells range from 8 to 74 queries (query type x category 8-9), so most are small. Intervals are query-bootstrap 95% CIs (1000 resamples, seed 6188), shown only for n>=5; exploratory, no multiple-testing correction. Source R@10 is the share of queries whose source paper is in the top 10.

## By query type

| Segment | n | nDCG@10 [95% CI] | Source MRR@10 [95% CI] | Source R@10 [95% CI] | Source misses | Failure cases |
|---|---:|---:|---:|---:|---:|---:|
| **all** | 100 | 0.842 [0.821, 0.863] | 0.766 [0.702, 0.830] | 93% [88%, 97%] | 7 | 16 |
| keyword | 25 | 0.823 [0.771, 0.869] | 0.720 [0.574, 0.848] | 96% [88%, 100%] | 1 | 4 |
| known_item | 25 | 0.807 [0.768, 0.848] | 1.000 [1.000, 1.000] | 100% [100%, 100%] | 0 | 5 |
| paraphrase | 25 | 0.866 [0.829, 0.904] | 0.633 [0.493, 0.773] | 84% [68%, 96%] | 4 | 5 |
| question | 25 | 0.871 [0.837, 0.905] | 0.710 [0.580, 0.840] | 92% [80%, 100%] | 2 | 2 |

## By category

| Segment | n | nDCG@10 [95% CI] | Source MRR@10 [95% CI] | Source R@10 [95% CI] | Source misses | Failure cases |
|---|---:|---:|---:|---:|---:|---:|
| **all** | 100 | 0.842 [0.821, 0.863] | 0.766 [0.702, 0.830] | 93% [88%, 97%] | 7 | 16 |
| cs.CL | 34 | 0.846 [0.813, 0.877] | 0.759 [0.639, 0.871] | 94% [85%, 100%] | 2 | 5 |
| cs.IR | 33 | 0.835 [0.787, 0.877] | 0.715 [0.591, 0.828] | 91% [79%, 100%] | 3 | 7 |
| cs.LG | 33 | 0.844 [0.811, 0.875] | 0.824 [0.721, 0.924] | 94% [85%, 100%] | 2 | 4 |

## By specificity

| Segment | n | nDCG@10 [95% CI] | Source MRR@10 [95% CI] | Source R@10 [95% CI] | Source misses | Failure cases |
|---|---:|---:|---:|---:|---:|---:|
| **all** | 100 | 0.842 [0.821, 0.863] | 0.766 [0.702, 0.830] | 93% [88%, 97%] | 7 | 16 |
| broad | 26 | 0.873 [0.839, 0.904] | 0.587 [0.454, 0.721] | 92% [81%, 100%] | 2 | 2 |
| specific | 74 | 0.831 [0.807, 0.857] | 0.829 [0.764, 0.890] | 93% [86%, 99%] | 5 | 14 |

## By query type x category

| Segment | n | nDCG@10 [95% CI] | Source MRR@10 [95% CI] | Source R@10 [95% CI] | Source misses | Failure cases |
|---|---:|---:|---:|---:|---:|---:|
| **all** | 100 | 0.842 [0.821, 0.863] | 0.766 [0.702, 0.830] | 93% [88%, 97%] | 7 | 16 |
| keyword / cs.CL | 9 | 0.848 [0.789, 0.897] | 0.590 [0.335, 0.834] | 89% [67%, 100%] | 1 | 2 |
| keyword / cs.IR | 8 | 0.763 [0.630, 0.875] | 0.812 [0.625, 0.938] | 100% [100%, 100%] | 0 | 2 |
| keyword / cs.LG | 8 | 0.856 [0.823, 0.895] | 0.775 [0.550, 1.000] | 100% [100%, 100%] | 0 | 0 |
| known_item / cs.CL | 8 | 0.814 [0.743, 0.870] | 1.000 [1.000, 1.000] | 100% [100%, 100%] | 0 | 2 |
| known_item / cs.IR | 8 | 0.822 [0.765, 0.878] | 1.000 [1.000, 1.000] | 100% [100%, 100%] | 0 | 1 |
| known_item / cs.LG | 9 | 0.787 [0.710, 0.861] | 1.000 [1.000, 1.000] | 100% [100%, 100%] | 0 | 2 |
| paraphrase / cs.CL | 9 | 0.839 [0.764, 0.904] | 0.778 [0.611, 0.944] | 100% [100%, 100%] | 0 | 0 |
| paraphrase / cs.IR | 8 | 0.900 [0.837, 0.948] | 0.479 [0.250, 0.729] | 75% [38%, 100%] | 2 | 3 |
| paraphrase / cs.LG | 8 | 0.863 [0.813, 0.909] | 0.625 [0.312, 0.938] | 75% [50%, 100%] | 2 | 2 |
| question / cs.CL | 8 | 0.886 [0.855, 0.919] | 0.688 [0.438, 0.938] | 88% [62%, 100%] | 1 | 1 |
| question / cs.IR | 9 | 0.851 [0.779, 0.913] | 0.583 [0.389, 0.806] | 89% [67%, 100%] | 1 | 1 |
| question / cs.LG | 8 | 0.877 [0.812, 0.945] | 0.875 [0.750, 1.000] | 100% [100%, 100%] | 0 | 0 |

## Where D50's graded loss sits

Same telescoping decomposition as the D47 analysis, applied to D50 on the same labels: perfectly reorder the top 10, then select from the top 20, then the top 50, then the pooled-label ideal. Unjudged papers count as zero; oracles are label-informed diagnostics, not achievable systems.

| Component | Controlled by | Mean loss [95% CI] | Queries affected |
|---|---|---:|---:|
| ordering_top10 | d50_refine | 0.0388 [0.0306, 0.0479] | 87 |
| selection_11_20 | d50_refine | 0.0718 [0.0578, 0.0855] | 73 |
| screening_21_50 | d46_rerank | 0.0282 [0.0210, 0.0365] | 41 |
| outside_top50 | stage1_retrieval | 0.0195 [0.0115, 0.0290] | 23 |

## Stage attribution: source paper outside the D50 top 10

Ranks are the source paper's position in each saved ranking; `>100` means outside the saved top 100. D46 re-scores the D36 top 50; D50 re-scores the D46 top 20 and keeps D46 rank 1. D47 is the previous baseline (comparison only).

| Query | Type | Category | Lexical | Semantic | D36 | D46 | D47 | D50 | Lost at | Source grade |
|---|---|---|---:|---:|---:|---:|---:|---:|---|---|
| q-keyword-049 | keyword | cs.CL | 6 | >100 | 27 | 21 | 21 | 21 | d46_rerank | 2 |
| q-paraphrase-012 | paraphrase | cs.IR | >100 | 91 | >100 | >100 | >100 | >100 | stage1_retrieval | unjudged |
| q-paraphrase-050 | paraphrase | cs.LG | >100 | >100 | >100 | >100 | >100 | >100 | stage1_retrieval | unjudged |
| q-paraphrase-077 | paraphrase | cs.LG | >100 | 32 | 58 | 58 | 58 | 58 | stage1_retrieval | 2 |
| q-paraphrase-096 | paraphrase | cs.IR | >100 | >100 | >100 | >100 | >100 | >100 | stage1_retrieval | unjudged |
| q-question-003 | question | cs.IR | >100 | 88 | >100 | >100 | >100 | >100 | stage1_retrieval | unjudged |
| q-question-094 | question | cs.CL | >100 | >100 | >100 | >100 | >100 | >100 | stage1_retrieval | unjudged |

Lost at: stage1_retrieval 6, d46_rerank 1, d50_refine 0. `stage1_retrieval`: Stage 1 (Decision 36) did not rank it in the top 50; no reranker saw it. `d46_rerank`: In the top 50, but Decision 46 left it outside the top 20 that Decision 50 re-scores. `d50_refine`: In Decision 50's top-20 pool, but the refinement ranked it below 10.

## Lowest nDCG@10 (10 queries, any source rank)

| Query | Type | Category | nDCG@10 | Source D50 rank | Loss: D50 refine | D46 rerank | Stage 1 | Largest |
|---|---|---|---:|---:|---:|---:|---:|---|
| q-keyword-078 | keyword | cs.IR | 0.394 | 2 | 0.475 | 0.070 | 0.061 | d50_refine |
| q-keyword-072 | keyword | cs.IR | 0.543 | 1 | 0.169 | 0.124 | 0.163 | d50_refine |
| q-known_item-047 | known_item | cs.LG | 0.611 | 1 | 0.000 | 0.216 | 0.173 | d46_rerank |
| q-question-003 | question | cs.IR | 0.626 | >100 | 0.374 | 0.000 | 0.000 | d50_refine |
| q-known_item-032 | known_item | cs.LG | 0.628 | 1 | 0.320 | 0.052 | 0.000 | d50_refine |
| q-known_item-088 | known_item | cs.CL | 0.642 | 1 | 0.262 | 0.096 | 0.000 | d50_refine |
| q-known_item-031 | known_item | cs.CL | 0.674 | 1 | 0.068 | 0.000 | 0.258 | stage1_retrieval |
| q-keyword-004 | keyword | cs.CL | 0.675 | 1 | 0.273 | 0.052 | 0.000 | d50_refine |
| q-known_item-039 | known_item | cs.IR | 0.681 | 1 | 0.202 | 0.117 | 0.000 | d50_refine |
| q-paraphrase-006 | paraphrase | cs.IR | 0.684 | 2 | 0.264 | 0.000 | 0.052 | d50_refine |

## Taxonomy

16 failure cases (7 source misses, 10 lowest nDCG@10, overlapping). One primary cause per case; secondary causes are additional explanations. Annotation provenance: Copilot SDK AI assistant (subagent; model version not exposed), 2026-11-16. AI-assisted cause annotation via Copilot SDK in VS Code; not human annotation. Inter-annotator agreement: Not measured; single annotator, no adjudication. Codebook codebook-v1 (decision rules and pre-annotation changes in [annotations.json](annotations.json)).

| Cause | Primary | Secondary mentions | Definition |
|---|---:|---:|---|
| vocabulary_gap | 3 (19%) | 2 | The query describes the source's contribution in different words from its title and abstract (paraphrase or terminology mismatch). |
| acronym_or_rare_term | 0 (0%) | 0 | The query hinges on an acronym, named method, dataset or rare term that retrieval or reranking fails to match or resolve. |
| broad_or_underspecified_query | 2 (12%) | 1 | Many papers fit the query about as well as the source; the source is not uniquely best, so the miss is more a measurement limit than a system error. |
| competing_near_duplicate | 3 (19%) | 0 | A top-ranked paper addresses nearly the same specific problem and method as the source, displacing it. |
| query_generation_artifact | 0 (0%) | 0 | The generated query does not describe the source well: it emphasizes details absent from, peripheral to or inconsistent with the source abstract. |
| label_gap | 2 (12%) | 6 | Relevance labels understate or distort quality: relevant-looking top-10 papers are graded 0 or are unjudged, or grades are inconsistent with the abstracts. |
| single_target_partial_credit | 6 (38%) | 1 | The query has one clear target (the source), which D50 ranks first or second; few or no other papers meet all its constraints, so the loss comes from how partial matches (grade 0 vs 1) are ordered below it, a metric and label-pool effect more than a user-visible failure. |
| stage1_miss | 0 (0%) | 0 | Residual mechanism code: the source or most missing relevant papers never reached the Decision 36 top 50, and no content-level cause is evident. |
| rerank_demotion | 0 (0%) | 4 | Residual mechanism code: the reranker had the source or better-graded papers in its pool but ranked less relevant papers above them. |

### Primary cause by failure stage

| Failure stage | Cases | vocabulary_gap | broad_or_underspecified_query | competing_near_duplicate | label_gap | single_target_partial_credit |
|---|---:|---:|---:|---:|---:|---:|
| stage1_retrieval | 7 | 2 (29%) | 1 (14%) | 3 (43%) | 1 (14%) | 0 (0%) |
| d46_rerank | 2 | 0 (0%) | 1 (50%) | 0 (0%) | 0 (0%) | 1 (50%) |
| d50_refine | 7 | 1 (14%) | 0 (0%) | 0 (0%) | 1 (14%) | 5 (71%) |

### Primary cause by query type

| Query type | Cases | vocabulary_gap | broad_or_underspecified_query | competing_near_duplicate | label_gap | single_target_partial_credit |
|---|---:|---:|---:|---:|---:|---:|
| keyword | 4 | 0 (0%) | 1 (25%) | 0 (0%) | 1 (25%) | 2 (50%) |
| known_item | 5 | 0 (0%) | 0 (0%) | 0 (0%) | 1 (20%) | 4 (80%) |
| paraphrase | 5 | 3 (60%) | 0 (0%) | 2 (40%) | 0 (0%) | 0 (0%) |
| question | 2 | 0 (0%) | 1 (50%) | 1 (50%) | 0 (0%) | 0 (0%) |

### Primary cause by selection reason

| Selection reason | Cases | vocabulary_gap | broad_or_underspecified_query | competing_near_duplicate | label_gap | single_target_partial_credit |
|---|---:|---:|---:|---:|---:|---:|
| source_outside_top10 | 7 | 2 (29%) | 2 (29%) | 3 (43%) | 0 (0%) | 0 (0%) |
| lowest_ndcg | 10 | 1 (10%) | 1 (10%) | 0 (0%) | 2 (20%) | 6 (60%) |

Failure stage = where the source left the top 10 for source misses, otherwise the stage holding most of the query's graded loss.

## Examples

### single_target_partial_credit

- **q-keyword-072** (keyword, cs.IR; nDCG@10 0.543; source D50 rank 1): "BL19 digital collection retrieval benchmark" Source: *Cultural Analytics for Good: Building Inclusive Evaluation Frameworks for Historical IR*. The BL19 source (inclusive evaluation frameworks for historical IR) is at rank 1 and is the only grade-2 paper; ranks 2-10 are generic IR benchmarks and cultural-heritage retrieval systems graded mostly 0, with inconsistent splits such as NeuCLIRBench graded 0 at rank 9 but NeuCLIRTech graded 1 at rank 10.
- **q-known_item-047** (known_item, cs.LG; nDCG@10 0.611; source D50 rank 1): "van der Klis lorentz neural networks" Source: *Fast and Geometrically Grounded Lorentz Neural Networks*. The Lorentz neural network source is at rank 1 and is the only grade-2 paper in a corpus with few hyperbolic papers; the remaining loss is partial matches (Lorentz-equivariant jet taggers, hyperbolic retrieval for RAG) that Decision 46 left at 22 and 24 behind grade-0 generic neural-network theory papers, so the refinement never re-scored them.

### competing_near_duplicate

- **q-question-094** (question, cs.CL; nDCG@10 0.817; source D50 rank >100): "how can we measure if a model can learn new rules or knowledge from a provided text?" Source: *CL-bench: A Benchmark for Context Learning*. RuleWorld (the benchmark in 'Beyond Factual Knowledge', rank 3) and 'LLMs Learn Better In-Context from Rules than from Examples' (rank 1) measure learning externally provided rules from context as directly as the CL-bench source, and the general question fits many in-context-learning papers, so CL-bench was outside both Stage 1 components' top 100.
- **q-paraphrase-096** (paraphrase, cs.IR; nDCG@10 0.861; source D50 rank >100): "a way to find relevant text chunks using a hierarchy of summaries to connect search terms and documents" Source: *Bridge-RAG: An Abstract Bridge Tree Based Retrieval Augmented Generation Algorithm*. DTCRS (recursive summarization trees), SVD-RAG (tree-organized RAG) and LLM-guided Hierarchical Search implement the query's 'hierarchy of summaries' retrieval as directly as the source, whose own terms ('abstract bridge tree', query entities) differ from the query, so Bridge-RAG was outside both Stage 1 components' top 100.

### vocabulary_gap

- **q-paraphrase-006** (paraphrase, cs.IR; nDCG@10 0.684; source D50 rank 2): "fixing systemic prejudices in generative suggestion engines by erasing the impact of problematic data points without full model updates" Source: *Towards Fair Large Language Model-based Recommender Systems without Costly Retraining*. The source is at rank 2 behind a grade-2 recommendation-unlearning paper, but the paraphrase 'systemic prejudices' in 'generative suggestion engines' also pulled generic LLM-debiasing papers graded 0 into ranks 4 and 6-8, while recommender-specific erasure or debiasing papers graded 1 (TRACER at 76, CRAB unranked) sit outside the Stage 1 top 50; grades are also inconsistent (Fairness Pruning 0 vs the similar Fairness Evaluation and Inference Level Mitigation 2).
- **q-paraphrase-050** (paraphrase, cs.LG; nDCG@10 0.760; source D50 rank >100): "blocking fake info in external search results by checking how removing a page changes the answer" Source: *RAGuard: A Layered Defense Framework for Retrieval-Augmented Generation Systems Against Data Poisoning*. The query restates RAG corpus-poisoning defense ('fake info', 'external search results', 'removing a page' for leave-one-out decoding) in web-search words, so both Stage 1 components rank RAGuard outside their top 100 and the top 10 fills with AI-search credibility and generative-engine-optimization papers (no grade-2 paper anywhere in the pool).

### broad_or_underspecified_query

- **q-question-003** (question, cs.IR; nDCG@10 0.626; source D50 rank >100): "how can large language models actively gather information to improve product recommendations?" Source: *RecThinker: An Agentic Framework for Tool-Augmented Reasoning in Recommendation*. 'Actively gather information' fits preference elicitation, clarifying questions, cold-start querying and agentic tool use alike, so many papers partly fit and only one pool paper is graded 2 (Ask to Be Sure, rank 2); the agentic tool-use source RecThinker never reached the Decision 36 top 100 (semantic rank 88), and the rank-one pin kept the grade-0 semantic-augmentation paper first.
- **q-keyword-049** (keyword, cs.CL; nDCG@10 0.895; source D50 rank 21): "multimodal llm decoding strategies" Source: *Revisiting Greedy Decoding for Visual Question Answering: A Calibration Perspective*. The topic-only query 'multimodal llm decoding strategies' fits many papers (seven top-10 papers are grade-2 multimodal decoding methods, mostly for diffusion MLLMs), so the greedy-decoding-for-VQA source is one good answer among many; Decision 46 placed it at 21, below grade-1 text-only dLLM decoding papers and the grade-0 Modality Collapse paper, so the refinement never re-scored it.

### label_gap

- **q-keyword-078** (keyword, cs.IR; nDCG@10 0.394; source D50 rank 2): "llm synthetic slate preference" Source: *Offline A/B Testing of Slate Recommendation Systems with LLMs: Reducing the Dependency on Pre-Collected User Interaction Data*. The keyword query hinges on 'slate', yet three of its four grade-2 papers have no slate component (Learning What Evaluators Value at rank 9, Pedagogically Aligned LLM Tutors at 38, the unranked LLM-evaluator narcissism paper), which inflates the ideal; separately, Decision 46 moved the source from Decision 36 rank 1 to 4 and the rank-one pin kept the grade-0 'Once Generated, Ranked' slate paper above it.
- **q-known_item-031** (known_item, cs.CL; nDCG@10 0.674; source D50 rank 1): "Boyd clinical provenance categorization" Source: *Towards Multidisciplinary Summarization of Hospital Stays: Efficient Sentence-Level Clinical Provenance Categorization*. The source (sentence-level clinical provenance categorization) is at rank 1, but grade 2 also goes to papers that share only the word 'provenance' in another sense (PhysioTRACE provenance-aware stress tests at rank 7, DeconDTN provenance shift at 58, concept provenance in LLM query simulation at 81), which inflates the ideal and produces most of the Stage 1 loss.

## Offline fix test: drop the rank-one pin

Plan frozen in [fix-plan.json](fix-plan.json) before any unpinned metric was computed. Same saved GPT-5.4 two-pass replies as Decision 50, averaged scores, Decision 46 order as tie-break, ranks 21+ unchanged; only the rule that keeps Decision 46's rank 1 first is removed. The pinned rule reproduces the saved D50 ranking for all 100 dev queries. Chosen after reading the failure cases, on queries already used to design Decision 50: exploratory, not a promotion.

| Metric | D50 (pinned) | Unpinned | Paired delta [95% CI] |
|---|---:|---:|---:|
| nDCG@10 | 0.8418 | 0.8476 | +0.0058 [-0.0015, +0.0135] |
| Source MRR@10 | 0.7659 | 0.8819 | +0.1160 [+0.0753, +0.1567] |
| Source R@10 | 0.9300 | 0.9300 | +0.0000 [+0.0000, +0.0000] |

Unpinned judged@10: **100%** (fully judged). nDCG@10 wins/losses/ties: 10/9/81. Rank 1 changes in 32 queries; rank-1 papers graded 0: 3 pinned vs 0 unpinned. Mean nDCG@10 delta on the 16 failure cases: +0.0169.

| Query type | n | nDCG@10 delta | Source MRR@10 delta |
|---|---:|---:|---:|
| keyword | 25 | +0.0190 | +0.1406 |
| known_item | 25 | +0.0000 | +0.0000 |
| paraphrase | 25 | +0.0068 | +0.1800 |
| question | 25 | -0.0025 | +0.1433 |

Frozen rule (nDCG@10 delta > 0.0106 with CI lower bound > 0, source MRR@10 delta >= -0.02, judged@10 100%) met: **no**. Query-type cells have 25 queries each; no multiple-testing correction.

## Candidate fixes (general rules, not query-specific)

| Cause | Proposal | Status | Evidence |
|---|---|---|---|
| single_target_partial_credit | Report source MRR@10 and success@1 beside nDCG@10 for single-target (known-item) queries, and report their below-source partial-credit loss as its own bucket rather than as a ranking failure. | proposal (evaluation reporting change; no ranking change to test) | Six of 16 cases; all have the source at rank 1, and in five it is the only grade-2 paper in the judged pool (the sixth has one more, at rank 2); known-item source MRR@10 is already 1.000. |
| vocabulary_gap | Rewrite or expand every query into the corpus's technical terms (for example an LLM terminology rewrite or a hypothetical-abstract embedding) before Stage 1, fused with the original query. | proposal only: needs new LLM and embedding calls (paid), so not testable offline on saved data | Three primary and two secondary cases; in the two vocabulary-gap source misses the source is outside the lexical top 100 and either outside the semantic top 100 or at semantic rank 32. |
| competing_near_duplicate | Treat this as a measurement limit: report 'source or any grade-2 paper in the top 10' beside source R@10, and keep diverse near-duplicates rather than tuning toward the generating paper. | proposal (evaluation reporting change) | Three source misses where several grade-2 top-10 papers address the source's specific problem. |
| broad_or_underspecified_query | For future query sets, have the query generator add a distinguishing constraint for broad queries, and read broad-query source MRR as a measurement limit; frozen queries stay unchanged. | proposal (affects future query generation only) | Two cases; broad-specificity source MRR@10 is lower than specific queries' while nDCG@10 is higher (segment table). |
| label_gap | Tighten the rubric so grade 2 requires the query's sense of each key term (not a shared word), calibrate 0 versus 1 for partial matches, and audit the top-20 pool with a second judge in a new versioned label layer. | proposal only: needs new paid judgments and owner approval; no labels changed here | Two primary and six secondary cases. |
| rerank_demotion | Drop Decision 50's rank-one pin so the GPT-5.4 refinement can move a better paper above Decision 46's rank 1 (same saved replies; general rule, no query-specific logic). | tested offline on saved replies (dev only, post hoc, frozen plan): frozen nDCG@10 rule not met; not promoted | See the offline fix test section: the nDCG@10 gain is below the frozen threshold with a CI that includes zero, while source MRR@10 rises with a CI above zero; top 10 fully judged. Widening the Decision 50 re-scoring depth for the two Decision 46 demotions would need paid calls. |

## Limits

- 100 repeatedly analyzed dev queries; segment cells are small and exploratory.
- Labels are pooled LLM judgments (no human validation). Unjudged papers count as zero, so a never-judged source paper does not lower nDCG.
- Source MRR/R@10 treat the generating paper as the single right answer; graded nDCG can be high when the source is missing.
- Cause labels are one AI assistant's reading of titles and abstracts, with no agreement study; they are leads, not established causes.
- Stage 1 component ranks only cover the saved top 100.
- Annotated evidence matches the current cases.json: **True**.

Per-query rows, segment values and input hashes: [report.json](report.json); case evidence: [cases.json](cases.json); codebook and annotations: [annotations.json](annotations.json).
