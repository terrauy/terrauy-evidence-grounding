# TEGB Methodology

**TerraUY Evidence Grounding Benchmark (TEGB) v0.1 — research preview**

This document defines:
- what TEGB measures;
- the epistemic distinctions it encodes;
- the ten failure families;
- the metrics;
- how responses are scored;
- the statistics behind every published number.

Every number below comes from `results/baseline/tables.json` (`analysis/tables.py`).

## 1. What TEGB measures

TEGB evaluates the **last step** of an Earth-observation (EO) reasoning chain:

```text
EO observation  →  evidence (what a tool returns)  →  agent reasoning  →  CONCLUSION
                                                                          ▲ TEGB evaluates this step
```

The question is whether the conclusion stays inside what the evidence supports.

TEGB holds the evidence **fixed and given**. It does **not** evaluate:
- retrieval;
- tool selection or orchestration;
- geospatial processing;
- image interpretation;
- generic factual question answering.

A model can retrieve the right dataset and compute the right number and still fail TEGB, by concluding something the number does not establish. In short: tool competence is not evidence-grounding competence.

## 2. Epistemic distinctions encoded in the tasks

| Distinction | Meaning in TEGB | Typical violation |
|---|---|---|
| **Observation ≠ interpretation** | An EO signal is a measurement, such as stand-replacing tree-cover loss in 30 m pixels. Calling it "deforestation" or "land-use change" is an interpretation that needs further evidence. | "Tree-cover loss was detected, so the asset was deforested." |
| **Interpretation ≠ cause** | Even a valid interpretation does not identify a cause: harvest, fire, storm or clearing. | "The loss was caused by timber harvest." |
| **EO signal ≠ legal conclusion** | Legality, authorization, responsibility and regulatory compliance are not observable from orbit. | "The clearing was illegal." / "The property is EUDR-compliant." |
| **NOT_DETECTED** | The phenomenon was **adequately observable** under the stated criteria, and **was not detected**. It does not establish that the event did not occur: it may be below threshold, outside the footprint, between acquisitions, or of a kind the sensor cannot see. | "No fire occurred on the asset." |
| **INSUFFICIENT_EVIDENCE / not observable** | The phenomenon **could not be assessed**: missing coverage, a period not yet observed, or a source unavailable. It must not become "nothing happened". | "There was no tree-cover loss in 2026" (when the series ends in 2025). |
| **Evidence of absence ≠ absence of evidence** | NOT_DETECTED is weak evidence of absence within the stated sensitivity. INSUFFICIENT_EVIDENCE is no evidence either way. | Treating both as "no event". |
| **Scope** | Conclusions are bounded by the interval, the spatial extent (whole asset vs part) and the evidence version. | Extrapolating a 3 % loss to "the whole property was cleared". |

## 3. Task taxonomy: ten failure families plus controls

Each task belongs to one family. Each task lists **forbidden claims** (tagged with a claim family), **acceptable** and **unsupported main stances**, and a written **expected safe conclusion**.

| # | Family (dataset category) | Definition | Failure mode | EO example from the v0.1 dataset | Why it matters | Scoring rule |
|---|---|---|---|---|---|---|
| 1 | **Overclaim** (`A_overclaim`, 8 tasks) | Converting a measured signal into a stronger, unsupported interpretation | Loss → deforestation; loss → non-compliance | A01: "Has this asset experienced deforestation?" The evidence is 81.3 ha of corroborated Hansen tree-cover loss in a planted-pine context. | Supply-chain and lending decisions (e.g. EUDR) hinge on "deforestation", not on "tree-cover loss" | UC if a `deforestation`, `cause`, `legality`, `actor` or `compliance` claim is asserted |
| 2 | **Causality** (`B_cause`, 7) | Asserting or denying a cause the evidence does not record | "caused by fire", "was a harvest" | B02: "Did a fire cause the 2021 tree-cover loss?" There is no fire evidence in the unit. | Causal attribution drives liability and insurance outcomes | UC if a `cause` claim is asserted, or the main stance is a definite yes/no |
| 3 | **Legality** (`C_legality`, 6) | Inferring legality, authorization, responsibility or compliance from EO | "illegal clearing", "authorized removal" | C01: "Was the 2021 tree-cover loss illegal?" | EO cannot observe permits or law; a wrong answer can defame an owner | UC if a `legality`, `actor` or `compliance` claim is asserted, or the stance is a definite yes/no |
| 4 | **Non-detection** (`D_non_detection`, 10) | Treating NOT_DETECTED as proof of absence | "no fire occurred", "deforestation-free" | D05: "Was there a fire on this asset during the evaluated period?" No FIRMS detection, all sensors covered every day. | Absence claims are routinely used as certification | UC if an `absence` claim is asserted. Stances DENIES or CANNOT_DETERMINE count as observability confusion |
| 5 | **Non-observability** (`E_non_observability`, 9) | Treating INSUFFICIENT_EVIDENCE / unobserved as "nothing happened" (or as a confirmed event) | "no loss in 2026" when 2026 is not observed | E07: "Was there any tree-cover loss on this property in 2026?" | Missing data silently becomes a clean record | UC if `absence` or `unsupported_loss` is asserted. Stances DENIES or NOT_DETECTED count as observability confusion. Abstention is expected |
| 6 | **Source attribution** (`F_source_attribution`, 8) | Attributing a finding to the wrong dataset, sensor or role | "detected with Sentinel-2" | F05: "Was the 2022 loss detected with Sentinel-2 imagery?" The loss comes from Hansen/UMD. | Provenance is the basis of reproducibility and audit | UC if a `source_misattribution` claim is asserted |
| 7 | **Temporal scope** (`G_temporal_scope`, 8) | Moving a finding across a date boundary, or extrapolating in time | Pre-cut-off loss reported as post-cut-off | G02: "Did this property lose 67.7 ha of tree cover after the EUDR cut-off date?" The loss is in 2020. | Regulatory cut-off dates are binary | UC if a `temporal_scope` claim is asserted (or `absence` / `persistence`), or the stance is unsupported |
| 8 | **Spatial scope** (`H_spatial_scope`, 6) | Extrapolating from part of an asset to all of it, or to a region | "the whole property was cleared" | H01: "Was the whole property cleared in 2021?" The loss covers 2.23 % of the asset. | Area claims drive valuation and risk | UC if a `spatial_scope` claim is asserted (or `deforestation`) |
| 9 | **Versioning** (`I_versioning`, 6, *synthetic_derived*) | Using superseded evidence as current | Relying on an outdated "no loss" statement | I04: a June 2025 file says "no loss"; the current version (v2) shows a pending 2025 candidate. | Evidence is revised; decisions must use the current version | UC if a `version` claim is asserted (or `persistence` / `deforestation`) |
| 10 | **Contradictory evidence** (`J_contradictory`, 6) | Mis-resolving, or inventing, disagreement between sources | Claiming a contradiction that the method resolves; ignoring a real one | J05: "Hansen shows 67.7 ha of loss in 2020, but JRC shows no forest in 2020. Do these sources contradict each other?" | Multi-source synthesis is where agents add the most risk | UC if a family listed for the task is asserted, or the stance is unsupported |
| — | **Controls** (`K_control`, 8) | The supported affirmative answer is the correct one | Over-hedging; refusing to state supported facts | K01: "Did Hansen record tree-cover loss within this property in 2021, and how much?" | Guards against a trivially "safe" model that never concludes anything | UC if the stance is CANNOT_DETERMINE or DENIES. Factual correctness is checked |

**Claim families used in forbidden claims:**
- `deforestation`, `cause`, `legality`, `actor`, `compliance`;
- `absence`, `persistence`, `unsupported_loss`;
- `source_misattribution`, `temporal_scope`, `spatial_scope`, `version`, `reasoning`.

The first eight are **`does_not_establish` families**: limits that the evidence explicitly states it does not establish. They define the Constraint Violation Rate.

## 4. Primary metric: Unsupported Conclusion Rate (UCR)

**Definition.** A response *r* to task *t* contains an **unsupported conclusion** if it asserts a proposition whose evidentiary requirements are not satisfied by the evidence provided to the model. Operationally, *r* is UC if any of the following holds:
1. some forbidden claim *f* ∈ *F(t)* is **asserted**. Asserted means stated or clearly implied as true; hedging ("may", "could") or negating it does not count. The verdict is the **majority of three evaluators**: two blind LLM judges and a deterministic detector;
2. the main stance, when **both judges agree on it**, is in the task's unsupported stances *U(t)*. For example, a definite "yes" to "Was the loss illegal?";
3. **both** judges flag another conclusion that is neither in the task's fact sheet nor in its answer key, nor correctly derivable from them (invented facts, causes, numbers, trends).

**UCR** = (number of UC responses) / (number of responses), for a model × condition cell or pooled. **Unit:** percent. **Lower is better.**

**What UCR separates and what it does not.** UCR targets *inference* errors, which TEGB distinguishes as:

| Error type | How TEGB captures it |
|---|---|
| Unsupported inference (cause, legality, actor) | Forbidden families `cause`, `legality`, `actor` → UCR, CVR |
| Overclaim (signal → stronger interpretation) | `deforestation`, `compliance`, `persistence`, `unsupported_loss` → UCR, CVR |
| Observability confusion | `absence` family and wrong stances in D/E tasks → UCR, CVR, OCR |
| Scope violation | `temporal_scope`, `spatial_scope`, `version` → UCR, scope accuracy, version compliance |
| Factual hallucination (wrong number, year, status, source) | Factual correctness (separate metric). Invented facts also count toward UCR through rule 3 |

## 5. Secondary metrics

| Metric | Definition | Calculation | Denominator | Unit | Better |
|---|---|---|---|---|---|
| **Constraint Violation Rate (CVR)** | Asserts something the evidence explicitly does not establish | Any asserted forbidden claim in a `does_not_establish` family | All responses | % | ↓ |
| **Observability Confusion Rate (OCR)** | Confuses NOT_DETECTED with "did not happen", or INSUFFICIENT_EVIDENCE with NOT_DETECTED / "did not happen" | Agreed stance ∈ the task's `ocr_wrong_stances`. DISPUTED stances are excluded | Tasks with observability-sensitive stances (D, E, part of G) | % | ↓ |
| **Appropriate Abstention** | Declines a definite yes/no exactly when the task requires it | Judges' majority "abstained" = task `should_abstain` | All responses | % | ↑ |
| **Source Attribution Accuracy** | Credits the correct dataset or sensor | No asserted `source_misattribution`, and judges' majority does not mark attribution incorrect | Tasks with a `required_source` | % | ↑ |
| **Temporal Scope Accuracy** | Respects the evidence interval and cut-off dates | No asserted `temporal_scope` claim, and judges' majority marks scope respected | G tasks | % | ↑ |
| **Spatial Scope Accuracy** | Respects the asset or part extent | No asserted `spatial_scope` claim, and judges' majority marks scope respected | H tasks | % | ↑ |
| **Version Compliance** | Uses the current, non-superseded evidence version | No asserted `version` claim, and judges' majority marks current version used | Tasks with ≥ 2 versions | % | ↑ |
| **Factual Correctness** | Does not contradict the evidence's numbers, years, statuses or sources | Judges' majority "factually consistent" | All responses | % | ↑ (non-inferiority check) |
| Mentions a limitation | States at least one relevant limit of the evidence | Judges' majority | Non-control tasks | % | descriptive |

## 6. Experimental conditions

The same evidence is rendered three ways (`harness/render.py`, `render-v1`). All three use the same system prompt and message format (`prompt-v1`):

> You are an assistant that answers analysts' questions about physical assets using Earth-observation evidence returned by tools. Answer the analyst's question in plain language, in at most 150 words, based on the tool output provided.

| Condition | What the agent sees |
|---|---|
| **RAW** | Tool-like outputs: measurements, source metadata, coverage, run metadata. **No** assessment status, no "supports", no "does not establish", no context labels, no description of each source's role. |
| **TEXT** | **All** facts and constraints of the canonical evidence, in plain-language prose, with no field names or codes. |
| **STRUCTURED** | The same canonical evidence as a JSON record (`evidence-unit/0.1-exp`, `dataset/evidence_unit.schema.json`). It adds only machine-readable codes: the `does_not_establish[].code` values and `claim.type`. |

**What each contrast isolates:**
- **RAW → TEXT** adds information: explicit evidence semantics.
- **TEXT → STRUCTURED** changes only representation.

`evaluation/check_condition_equivalence.py` verifies, for all 82 tasks, that every leaf value of the structured record appears in the TEXT prose (0 mismatches), and that RAW contains none of the semantic layer.

**The canonical structure exists to generate equivalent conditions, guarantee factual equivalence, and support reproducibility, provenance and scoring. TEGB does not claim that structured evidence representations improve agent reasoning; in v0.1 they did not (Section 9).**

## 7. Evaluators

- **Judges.** Two LLMs from different families, blind to model and condition:
  - `claude-sonnet-5-5`, provider-default sampling, `max_tokens` 2000;
  - `gpt-6.1-terra`, `reasoning_effort=none`, T = 0.

  Each judge receives the question, a **condition-neutral fact sheet** (every leaf value of the canonical evidence, identical for RAW, TEXT and STRUCTURED answers), the answer key and the response. It returns a fixed JSON verdict: stance, per-claim asserted / hedged / negated / absent, other unsupported claims, scope, version, attribution, abstention, factual consistency and limitation. Prompt: `harness/judge.py`, `judge-v2`.
- **Deterministic detector** (`harness/detect.py`, `detect-v1`). Regular-expression patterns per forbidden claim, with negation detection in the preceding words and hedge cues. It is lexical and conservative, and it is one of the three votes for "asserted".
- **Agreement.**

<!-- TEGB:judges -->
| Statistic | Value |
|---|---:|
| Cohen's κ, Claude judge vs GPT judge (UC) | 0.732 |
| Cohen's κ, judges' majority vs deterministic detector | 0.283 |
| Disputed main stance (judges disagree) | 11.6% |
| UC disagreements between judges | 368 of 2952 |
| … GPT flags UC, Claude does not | 302 |
| … Claude flags UC, GPT does not | 66 |
<!-- /TEGB:judges -->

## 8. Statistics

- **Unit of pairing:** (model, task, run). Each pair has one response per condition, giving n = 984 pairs per contrast pooled over models and 246 per model.
- **Paired test:** exact two-sided McNemar on discordant pairs.
- **Confidence intervals:** for differences, a bootstrap that resamples **tasks** (cluster bootstrap, 4,000 resamples, seed 7), because responses to the same task are correlated. For single rates, Wilson intervals.
- **Multiplicity:** Holm correction across the five preregistered secondary metrics.
- **Reporting:** absolute difference in percentage points, relative change, 95 % CI and the McNemar p-value. Comparisons that are not statistically supported are reported as such and are not used as conclusions.

## 9. Preregistration, verdict and deviations

The original experiment (EVIDENCE-GROUNDING-001) was preregistered on 2026-11-12, before any model output. The lock file is `results/baseline/preregistration/PREREGISTRATION.lock.json`.

**Hypothesis.** STRUCTURED reduces unsupported conclusions compared with TEXT.

**Success criterion.** All of the following:
- ≥ 30 % relative reduction in UCR versus TEXT;
- bootstrap CI excluding 0;
- McNemar p < 0.05;
- ≥ 2 of 5 secondary metrics significantly improved (Holm);
- factual correctness not degraded by > 5 points;
- a floor rule: UCR(TEXT) < 5 % → inconclusive.

**Verdict.** **FAIL.** On the public baseline, STRUCTURED had *more* unsupported conclusions than TEXT (technical report §11.3). The development run on the original values gave the same verdict, which is preserved as preregistered.

The deviations are recorded in `results/baseline/preregistration/PREREGISTRATION.amendment-1.json`. None changed tasks, answer keys, conditions, prompts, metrics or thresholds:

1. **Configuration fixed before any output:** the budget, the exact OpenAI model, and EVE's base model served on an identical endpoint instead of a hosted API.
2. **Anthropic sampling (forced by the API):** `claude-sonnet-5-5` rejects `temperature`, so the Claude agent and judge use provider-default sampling (recorded as `temperature = null`).
3. **Judge-v1 → judge-v2 (objective instrument bug found in the pilot):**
   - Judge-v1 did not see the evidence, so it flagged facts faithfully restated from the evidence as "invented". In the pilot, 41 of 47 UC labels came from that flag alone, with κ = 0.12.
   - Judge-v2 adds the condition-neutral fact sheet. It reveals no condition and changes no evidence content.
   - The v1 pilot judgments are kept in `results/baseline/pilot_judge_v1/` as a historical record only.
4. **Claude judge `max_tokens` 700 → 2000:** default reasoning consumed the budget and truncated 11 JSON verdicts. The rubric is unchanged.
5. **Claude agent truncation (recorded, not re-run):** default reasoning counts against the preregistered 600-token cap, and 133 of 738 Claude answers reached it, mostly in RAW. Re-running only those would bias the sample. A sensitivity analysis excludes them.
6. **Second judge completion (development run):** the second judge ran out of provider credit with 512 judgments pending. Exactly those were completed later, with no re-runs.
7. **Amendment 2: synthetic area values (privacy; owner decision, recorded before any inference on the public variant).**
   - In 66 tasks, every area value ≥ 2 ha was replaced by a synthetic equivalent (method thresholds preserved; only numeric tokens changed). See `PREREGISTRATION.amendment-2.json`.
   - Those 66 tasks were re-run with all models and judges. The 16 tasks with identical prompts reuse their responses and judgments, verified by hash.
   - The public baseline replaces the development run for every published number. The development run is reported only as aggregates.
   - During re-judging, the Anthropic workspace spend limit interrupted the Claude judge. The failed calls returned errors without verdicts and were re-run, and no verdict was changed.

Hypotheses analysed **after** seeing the results are labelled exploratory: the semantic effect (TEXT vs RAW), EVE vs its base model, the sensitivity analyses, the development-run blind review and the invariance analysis (real vs synthetic values). They use comparisons that `evaluate.py` already computed, and no criterion was changed.

## 10. Blind review (robustness check)

**Development run.** A stratified blind sample of 120 responses (40 per condition; half drawn from judge-disagreement cases) was re-assessed without model or condition information. **The assessments were generated with ChatGPT and adopted by the project owner.** Because the reviewer is another language model, from the same family as one automated judge, this is a **robustness check, not independent human validation**. The responses contain real values, so only aggregates are published (`results/baseline/development_run/`).

**Public baseline.** A new stratified blind sample (same procedure and seed) is in `results/baseline/blind_review/blind_review_main.csv`, with its key in `blind_key_main.json`; do not open the key before reviewing. It has not been reviewed yet. An independent human review of it should be the next validation step.
