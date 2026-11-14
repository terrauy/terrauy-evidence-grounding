# TEGB Leaderboard: benchmark version v0.1

This file holds the **Official TEGB v0.1 baseline** (four models evaluated by the authors) and the **community submissions** for benchmark version v0.1. There is no web service: the tables are generated from files in this repository.

TEGB is **not a universal ranking of models**. A score describes one model version, under one prompt, one decoding setup and one date. See [Comparability and fairness](#comparability-and-fairness) before comparing rows.

To add a model, follow [RUN_YOUR_MODEL.md](RUN_YOUR_MODEL.md).

## Tracks

| Track | Condition | What it measures |
|---|---|---|
| **R (primary)** | RAW | The model's own epistemic restraint when tools return results without explicit semantics |
| **S** | TEXT | Whether the model respects limits when they are stated explicitly |
| (diagnostic) | STRUCTURED | Representation sensitivity. Reported in the technical report, not ranked. |

## Columns

| Column | Definition |
|---|---|
| UCR ↓ | Unsupported Conclusion Rate |
| Constraint Violations ↓ | CVR |
| Observability Errors ↓ | OCR |
| Scope Errors ↓ | 1 − temporal/spatial scope accuracy |
| Factual Accuracy ↑ | Factual Correctness |

All columns follow [METHODOLOGY.md](METHODOLOGY.md). They are produced by the **reference evaluation**: two blind LLM judges (`judge-v2`) and a deterministic detector, merged by `harness/evaluate.py` (`evaluate-v1`). The labels have not been reviewed by independent experts.

## Official TEGB v0.1 baseline

Four models evaluated by the authors under one fixed configuration (prompt, decoding, model version). It is the **Initial TEGB v0.1 baseline**: it does not certify any model and is not a universal evaluation of these models.

### Track R: RAW (Initial TEGB v0.1 baseline, 2026-11-13)

<!-- TEGB:leaderboard_raw -->
| Model | UCR ↓ | Constraint Violations ↓ | Observability Errors ↓ | Scope Errors ↓ | Factual Accuracy ↑ |
|---|---:|---:|---:|---:|---:|
| EVE-Instruct | 79.7% | 52.8% | 63.2% | 31.0% | 31.7% |
| Mistral Small 3.2 | 72.8% | 47.2% | 60.7% | 33.3% | 40.2% |
| Claude Sonnet 5.5 | 37.8% | 10.2% | 18.3% | 2.4% | 87.2% |
| GPT-6.1 Terra | 13.0% | 5.7% | 14.5% | 7.1% | 89.6% |
<!-- /TEGB:leaderboard_raw -->

### Track S: TEXT (Initial TEGB v0.1 baseline, 2026-11-13)

<!-- TEGB:leaderboard_text -->
| Model | UCR ↓ | Constraint Violations ↓ | Observability Errors ↓ | Scope Errors ↓ | Factual Accuracy ↑ |
|---|---:|---:|---:|---:|---:|
| EVE-Instruct | 42.7% | 17.1% | 27.6% | 21.4% | 73.8% |
| Mistral Small 3.2 | 24.0% | 11.4% | 16.4% | 23.8% | 89.2% |
| Claude Sonnet 5.5 | 2.0% | 0.4% | 0.0% | 0.0% | 100.0% |
| GPT-6.1 Terra | 0.8% | 0.0% | 0.0% | 0.0% | 99.2% |
<!-- /TEGB:leaderboard_text -->

**Reading notes:**
- Each cell has n = 246: 82 tasks × 3 runs. Per-model differences of a few points are within noise; see the CIs in the technical report.
- The Claude agent used provider-default sampling, and 121 of its RAW answers were truncated at the 600-token cap.
- GPT-6.1 Terra and Claude Sonnet 5.5 reach a floor in Track S. v0.1 cannot discriminate between them there.
- In 66 tasks the area values are synthetic (privacy); see the Dataset Card.

## Community submissions (benchmark version v0.1)

Results sent by people outside the project, each with its raw model outputs and a validated `submission.json` in `submissions/v0.1/`. A dagger (†) marks a declared protocol deviation.

### Reference evaluation (comparable with the official baseline)

Same instrument as the official baseline. The judge verdicts are run by the submitter with their own keys, so they are self-reported; the validator checks that every verdict belongs to the submitted answer and recomputes every metric.

<!-- TEGB:community_reference -->
No external submissions yet.
<!-- /TEGB:community_reference -->

### Core detector score (screening only)

The core score uses only the deterministic detector (`harness/detect.py`). Anyone can reproduce it for free, and the validator recomputes it for every submission. It is **not** the UCR of the tables above and must not be used to rank models:
- it only sees forbidden phrases that are asserted, so it misses unsupported stances and invented conclusions, and it cannot see over-hedging or empty answers;
- it produces false positives on careful, heavily qualified answers;
- its agreement with the reference labels is low (κ = 0.283 between the judges' majority and the detector).

Unsupported conclusion rate **by the detector alone**, community submissions:

<!-- TEGB:community_core -->
No external submissions yet.
<!-- /TEGB:community_core -->

For orientation, the same detector-only rate for the official baseline models. Compare it with the reference tables above to see how far the two instruments can disagree:

<!-- TEGB:baseline_core -->
| Model | RAW | TEXT | STRUCTURED |
|---|---:|---:|---:|
| EVE-Instruct | 32.9% | 13.0% | 18.3% |
| Mistral Small 3.2 | 36.2% | 14.6% | 15.4% |
| Claude Sonnet 5.5 | 2.8% | 13.8% | 16.3% |
| GPT-6.1 Terra | 2.4% | 7.7% | 6.5% |
<!-- /TEGB:baseline_core -->

## How to submit

1. Fork the repository and run your model: `python -m tegb run ...` (see [RUN_YOUR_MODEL.md](RUN_YOUR_MODEL.md)).
2. Score it: `python -m tegb score results/my-model`. Optionally add the reference evaluation: `python -m tegb judge results/my-model`.
3. Package it: `python -m tegb submit results/my-model ...`. This writes `submissions/v0.1/<id>/`.
4. Open a pull request that adds only that folder. Use the "TEGB model submission" template.
5. CI validates the submission: hashes, completeness, prompt identity and recomputed metrics. It never runs a model.
6. A maintainer reviews the declaration and merges. The tables above are regenerated with `python -m tegb leaderboard`.

Results without a reproducible artifact (raw outputs plus `submission.json`) are not accepted. Numbers typed by hand are not accepted.

## Comparability and fairness

A TEGB score depends on, at least:
- the prompt (the common system prompt and the frozen task prompts in `conditions/`);
- the exact model version or checkpoint, and the date for hosted models;
- sampling (temperature per run, provider defaults, reasoning settings) and the 600-token output cap;
- the serving stack (quantization, chat template, context handling) and the adapter implementation;
- for the reference evaluation, the judge model versions at the time of judging.

Every submission records this configuration. Rows with different configurations are not directly comparable, and a model-specific prompt or setup may change its result. Do not use TEGB to claim that a model is safe for Earth-observation decisions, or to rank models outside the tested configuration.

## Benchmark contamination

TEGB v0.1 has been public since 2026-11-13 (DOI 10.5281/zenodo.24210391; task hashes in `dataset/task_hashes.json`). Models trained after that date may have seen the tasks, the answer keys or the baseline outputs.
- Every submission declares, to the best of the submitter's knowledge, whether the model was exposed to TEGB (`no-known-exposure`, `possible-exposure`, `known-exposure`, `unknown`), its training cutoff when known, and whether prompts or training were tuned on TEGB tasks.
- These declarations cannot be verified, and contamination cannot be detected reliably from scores. Treat results of models released after the publication date with corresponding caution.
- Tuning prompts or models on the v0.1 tasks and reporting the result as held-out is not accepted.

## Versioning

- Scores are valid only for the benchmark version they were run on. Every submission stores `benchmark_version` and the hashes of the task and prompt files.
- Scores from different benchmark versions are never mixed. A future v0.2 will have its own folder (`submissions/v0.2/`) and its own tables.
- The v0.1 tasks, prompts and baseline are frozen. New tasks proposed by the community go to a future version, never into v0.1.
