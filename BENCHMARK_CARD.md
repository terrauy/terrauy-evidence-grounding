# Benchmark Card: TerraUY Evidence Grounding Benchmark (TEGB)

| Field | Value |
|---|---|
| **Name** | TerraUY Evidence Grounding Benchmark (TEGB) |
| **Subtitle** | Trustworthy Reasoning over Earth Observation Evidence |
| **Version** | v0.1 — Research Preview (not v1.0) |
| **Maintainer** | TerraUY Intelligence |
| **Status** | Open research benchmark, research preview. Not peer-reviewed; not validated by any space agency; not a production standard. |
| **Copyright** | © 2026 Jairo Rifrán (TerraUY Intelligence) |

<!-- TEGB:validation_note -->
> **Validation status.** TEGB v0.1 has not yet undergone independent expert human review. The primary results are based on two blind model judges, deterministic checks, paired statistical analysis and multiple sensitivity analyses. A blind robustness review was also performed using ChatGPT-generated assessments adopted by the project owner; this is not treated as independent human validation.
<!-- /TEGB:validation_note -->

## Purpose

To measure whether AI agents respect the epistemic limits of Earth Observation (EO) evidence when producing conclusions. In plain terms: can an agent tell what EO evidence supports apart from what it does not establish?

## Scope

- **In scope:** the evidence-to-conclusion step. The evidence is given; TEGB evaluates the conclusion the agent draws from it, including:
  - overclaiming;
  - causal, legal and actor attribution;
  - non-detection and non-observability;
  - source attribution;
  - temporal and spatial scope;
  - versioning;
  - contradictory sources.
- **Evidence types in v0.1:**
  - stand-replacing tree-cover loss (Hansen/UMD Global Forest Change);
  - the 2020 forest reference (JRC GFC2020);
  - national forest cartography (Uruguay MGAP 2021);
  - thermal anomaly detections (NASA FIRMS).

## Non-goals

TEGB does **not** evaluate:
- retrieval;
- tool calling or orchestration;
- geospatial processing;
- image or visual interpretation;
- generic factual QA;
- general hallucination outside the given evidence.

It complements those benchmarks and does not replace them.

## Task families

| Family | Tasks |
|---|---:|
| Overclaim | 8 |
| Causality | 7 |
| Legality | 6 |
| Non-detection | 10 |
| Non-observability | 9 |
| Source attribution | 8 |
| Temporal scope | 8 |
| Spatial scope | 6 |
| Versioning | 6 |
| Contradictory evidence | 6 |
| **Affirmative controls** | **8** |

Definitions are in [METHODOLOGY.md](METHODOLOGY.md).

## Conditions

| Condition | What the agent sees |
|---|---|
| RAW | Tool outputs without explicit semantics |
| TEXT | Explicit semantics in prose |
| STRUCTURED | The same semantics as a machine-readable record |

TEXT and STRUCTURED are automatically verified to be factually equivalent.

## Metrics

- **Primary:** Unsupported Conclusion Rate (UCR, ↓).
- **Secondary:**
  - Constraint Violation Rate ↓;
  - Observability Confusion Rate ↓;
  - Appropriate Abstention ↑;
  - Source Attribution Accuracy ↑;
  - Temporal Scope Accuracy ↑;
  - Spatial Scope Accuracy ↑;
  - Version Compliance ↑;
  - Factual Correctness ↑.

## Dataset provenance

- **82 tasks:** 15 `real_derived` and 67 `synthetic_derived`.
- **Origin:** evidence structure and statuses come from read-only EO assessments of assets monitored by TerraUY's own organization, anonymized. Questions and answer keys were written by the authors.
- **Synthetic area values:** in 66 tasks, every area value ≥ 2 ha was replaced by a synthetic equivalent for privacy (method thresholds preserved). The real-to-synthetic mapping is not published.
- **Other synthetic tasks:** the versioning scenarios are synthetic by construction.
- **No customer data.** Two fire contexts belonging to another organization existed in the extraction; no task uses them and they are not distributed.
- Details: [DATASET_CARD.md](DATASET_CARD.md).

## Privacy

The release contains none of the following:
- organization, user or asset identifiers;
- geometry, coordinates or bounding boxes;
- cadastral references;
- place names;
- private URLs.

**Quasi-identifiers:** real asset and event areas were replaced by synthetic equivalents, so no original identifying area value remains. See [PRIVACY_AUDIT.md](PRIVACY_AUDIT.md).

## Evaluation methodology

- Two blind LLM judges from different families, plus a deterministic detector.
- Majority voting on forbidden claims.
- Paired McNemar tests and task-cluster bootstrap CIs.
- Preregistered success criterion.

## Baseline models (initial baseline, not a ranking)

<!-- TEGB:models -->
| Model key | Exact model id returned by the API / server | Serving |
|---|---|---|
| eve-instruct-24b | `eve-esa/EVE-Instruct` | HF Inference Endpoint, vLLM 0.29.0, 1× A100 80 GB, BF16, revision eecb769f; T = 0 / 0.7 / 0.7 |
| mistral-small-3.2-base | `mistralai/Mistral-Small-3.2-24B-Instruct-2506` | HF Inference Endpoint, vLLM 0.29.0, 1× A100 80 GB, BF16, revision 95a6d26c; T = 0 / 0.7 / 0.7 |
| claude-sonnet-5-5 | `claude-sonnet-5-5` | Anthropic API; provider-default sampling (temperature not accepted) |
| gpt-6.1-terra | `gpt-6.1-terra` | OpenAI API; reasoning_effort=none; T = 0 / 0.7 / 0.7 |
<!-- /TEGB:models -->

<!-- TEGB:main_results -->
| Model | RAW UCR ↓ | TEXT UCR ↓ | STRUCTURED UCR ↓ |
|---|---:|---:|---:|
| EVE-Instruct | 79.7% | 42.7% | 48.4% |
| Mistral Small 3.2 | 72.8% | 24.0% | 31.3% |
| Claude Sonnet 5.5 | 37.8% | 2.0% | 4.1% |
| GPT-6.1 Terra | 13.0% | 0.8% | 0.0% |
| **All models (pooled)** | **50.8%** | **17.4%** | **20.9%** |

UCR = Unsupported Conclusion Rate (lower is better). n = 246 responses per model and condition (82 tasks × 3 runs); pooled n = 984 per condition. 95 % Wilson CI (pooled): RAW [47.7, 53.9], TEXT [15.1, 19.9], STRUCTURED [18.5, 23.6].
<!-- /TEGB:main_results -->

**Findings:**
- **Explicit evidence semantics.** Going from RAW to TEXT changes UCR by −33.4 pp (paired p < 0.001, all four models).
- **Structured representation.** Going from TEXT to STRUCTURED changes UCR by +3.6 pp (95 % CI [0.1, 6.9]). The preregistered hypothesis that structure helps failed.
- **EO specialization.** In this evaluation, EVE-Instruct showed higher unsupported-conclusion rates than its Mistral Small 3.2 base model across all three conditions, with the same common system prompt. This is not a causal claim: domain specialization did not guarantee stronger evidence grounding in this benchmark, which does not mean that it worsens grounding or that EVE-Instruct is weaker in general.

## Known limitations

Summary (full list in [LIMITATIONS.md](LIMITATIONS.md)):
- small dataset from one region and one EO domain;
- LLM-as-judge labels;
- not yet reviewed by independent EO / remote sensing experts (the only blind review covered the development run and used ChatGPT-generated assessments adopted by the owner, which is not independent human validation);
- Claude agent truncations and default sampling;
- EVE evaluated with a common system prompt;
- results do not show that JSON is inherently worse, nor that EO specialization causes weaker grounding.

## Future work

- Independent review by Earth Observation / remote sensing experts.
- See also [FUTURE_TRACKS.md](FUTURE_TRACKS.md).

## Intended use

- Evaluating and comparing the evidence-grounding reliability of LLM agents that consume EO evidence.
- Studying how evidence presentation affects agent conclusions.
- Testing guardrails that keep conclusions inside the evidence.

## Misuse

TEGB is **not** a training dataset, fine-tuning corpus or reinforcement-learning dataset. Its proprietary-model outputs are not distributed as training material for alternative foundation models.

Do not use TEGB:
- as a certification of a model for regulatory, legal, credit or insurance decisions;
- as evidence about any real property;
- to rank models outside the tested configuration (prompt, decoding, version);
- to claim that a model is "safe" for EO decisions.

A low UCR on 82 tasks is not a guarantee of grounded behavior in deployment.

## License

- **Code:** Apache-2.0.
- **Authored content:** CC BY 4.0.
- **Third-party data:** original terms.
- **Model outputs:** separate notice.

See [LICENSING.md](LICENSING.md).

## Citation

See [CITATION.cff](CITATION.cff).

<!-- TEGB:doi -->
**DOI:** not yet assigned. A Zenodo DOI will be added here once the archived v0.1 record exists; no provisional DOI is used.
<!-- /TEGB:doi -->
