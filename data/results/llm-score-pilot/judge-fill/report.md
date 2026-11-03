# Fixed-key v2 pilot: missing judgments filled

Judge `openai-mini` (`gpt-5.4-mini`), rubric `b8b0c14a`; same prompt, shuffle and batching as all frozen labels. One HTTP attempt per call, no validation retries. Existing grades unchanged; leaderboard snapshot untouched.

Missing pairs: **34** (human-graded: 0); grades added: **34**; grade counts 0/1/2: 7/20/7.

| System | nDCG10 | P10 | Judged10 | Source MRR10 | R10 | R20 |
|---|---|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.6959 | 0.6750 | 1.0000 | 0.8375 | 0.9000 | 0.9000 |
| `llm-mini-score-pilot+d=10` | 0.7095 | 0.6750 | 1.0000 | 0.8417 | 0.9000 | 0.9000 |
| `llm-mini-score-pilot+d=50` | 0.7553 | 0.7700 | 1.0000 | 0.6875 | 0.8500 | 0.9000 |

## Paired versus baseline (same 20 queries, same child labels)

| Arm | nDCG10 delta [95% CI] | P10 delta [95% CI] | Wins/losses/ties |
|---|---|---|---|
| top10 | +0.0136 [+0.0002,+0.0275] | +0.0000 [+0.0000,+0.0000] | 13/4/3 |
| top50 | +0.0593 [+0.0006,+0.1155] | +0.0950 [+0.0250,+0.1650] | 13/4/3 |

## Segment nDCG10

| System | keyword | question | paraphrase | known_item |
|---|---|---|---|---|
| `fusion-shortlist+a=1+d=500` | 0.7188 | 0.7211 | 0.6575 | 0.6863 |
| `llm-mini-score-pilot+d=10` | 0.7494 | 0.7328 | 0.6789 | 0.6770 |
| `llm-mini-score-pilot+d=50` | 0.7396 | 0.8276 | 0.7531 | 0.7008 |

## New grades

| Query | Type | Paper | Grade | Rank in top10 arm | Rank in top50 arm |
|---|---|---|---|---|---|
| q-keyword-005 | keyword | Beyond Search-Imitation: Prior-Directed Exploration for Searchless Che | 2 | 28 | 5 |
| q-keyword-017 | keyword | OSDN: Improving Delta Rule with Provable Online Preconditioning in Lin | 2 | 49 | 2 |
| q-keyword-079 | keyword | Konkani LLM: Multi-Script Instruction Tuning and Evaluation for a Low- | 1 | 26 | 9 |
| q-keyword-081 | keyword | LLMDiRec: LLM-Enhanced Intent Diffusion for Sequential Recommendation | 1 | 42 | 4 |
| q-known_item-019 | known_item | From Self to Other: Evaluating Demographic Perspective-Taking in LLM H | 1 | 34 | 4 |
| q-known_item-019 | known_item | Demographic Prompting at Scale: When More Attributes Hurt LLM--Human A | 1 | 21 | 2 |
| q-known_item-042 | known_item | SelfDR: Self-Distillation from Reasoning for LLM-Based Recommendation | 0 | 22 | 8 |
| q-paraphrase-020 | paraphrase | Communication-Efficient Learning for Satellite Constellations | 1 | 50 | 8 |
| q-paraphrase-020 | paraphrase | OptINC: Optical In-Network-Computing for Scalable Distributed Learning | 1 | 44 | 3 |
| q-paraphrase-020 | paraphrase | KV Cache Translation across Heterogeneous Large Language Models | 0 | 36 | 2 |
| q-paraphrase-043 | paraphrase | Detecting Emotion Drift in Mental Health Text Using Pre-Trained Transf | 1 | 41 | 3 |
| q-paraphrase-043 | paraphrase | Multilingual and Continuous Backchannel Prediction: A Cross-lingual St | 0 | 24 | 8 |
| q-paraphrase-043 | paraphrase | LLM-MC-Affect: LLM-Based Monte Carlo Modeling of Affective Trajectorie | 1 | 39 | 10 |
| q-paraphrase-043 | paraphrase | SCoPE: Shift-Aware Speaker-Conditioned Priors for Emotion Recognition  | 1 | 21 | 2 |
| q-paraphrase-063 | paraphrase | Evaluating Austrian A-Level German Essays with Large Language Models f | 0 | 18 | 7 |
| q-paraphrase-063 | paraphrase | EDIT: Evidence-Diagnosed Intervention Training for Rule-Faithful LLM G | 0 | 32 | 9 |
| q-paraphrase-063 | paraphrase | A Human-in-the-Loop Framework for AI-Assisted Scoring in Large-Scale W | 1 | 16 | 6 |
| q-paraphrase-063 | paraphrase | Alice: A Large-Scale German Benchmark for Rubric-Based Multi-Dimension | 1 | 30 | 8 |
| q-paraphrase-077 | paraphrase | Is Finer Better? The Limits of Microscaling Formats in Large Language  | 1 | 34 | 4 |
| q-paraphrase-077 | paraphrase | HiFloat4 Format for Language Model Pre-training on Ascend NPUs | 1 | 37 | 5 |
| q-paraphrase-096 | paraphrase | LLM-guided Hierarchical Search for End-to-end Reasoning Intensive Retr | 2 | 22 | 6 |
| q-paraphrase-096 | paraphrase | Beyond Patch Aggregation: 3-Pass Pyramid Indexing for Vision-Enhanced  | 1 | 48 | 7 |
| q-paraphrase-096 | paraphrase | EviMap: Evidence-Grounded Hierarchical Topic Maps for Exploring Unlabe | 1 | 23 | 2 |
| q-question-040 | question | Unlocking Implicit Experience: Synthesizing Tool-Use Trajectories from | 1 | 22 | 6 |
| q-question-040 | question | ToolRACER: A Robust Agentic Conversation Emulation Resource for Agent  | 1 | 28 | 7 |
| q-question-056 | question | Multi-stage Bayesian optimisation for dynamic decision-making in self- | 0 | 40 | 9 |
| q-question-056 | question | Agentic Fusion of Large Atomic and Language Models to Accelerate Super | 2 | 15 | 6 |
| q-question-056 | question | LEAP: A closed-loop framework for perovskite precursor additive discov | 1 | 41 | 10 |
| q-question-056 | question | Molecular LLM Agents: From Architectural Design to Scientific Autonomy | 1 | 39 | 8 |
| q-question-088 | question | RRM: Experience-Driven Reflective Retrieval Memory for Long-Horizon Mu | 2 | 49 | 10 |
| q-question-088 | question | TRIAGE: Three-level Routing and Intelligent Agent Guidance for Efficie | 2 | 43 | 1 |
| q-question-095 | question | OmniCast: A Masked Latent Diffusion Model for Weather Forecasting Acro | 2 | 45 | 2 |
| q-question-095 | question | China Regional 3km Downscaling Based on Residual Corrective Diffusion  | 0 | 33 | 10 |
| q-question-095 | question | Skillful Kilometer-Scale Regional Weather Forecasting via Global and R | 1 | 36 | 5 |

## Accounting

- Paid judge calls: 15; input/output/reasoning tokens 17,544/1,183/0; ledger-accounted 18,727; cost $0.018482 (task ceiling $0.05).

## Cautions

- 20 previously examined dev queries; exploratory CIs; no promotion.
- The judge and the reranker share a model family: possible same-family preference is not ruled out by these grades.
- Adding grades can raise a query's ideal DCG, so baseline numbers can move too.
