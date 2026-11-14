# TEGB Leaderboard: Initial TEGB v0.1 baseline

There is no web service. This file defines the format and holds the **Initial TEGB v0.1 baseline**: four models evaluated by the authors under one fixed configuration (prompt, decoding, model version). It is **not a universal evaluation or ranking** of these models and does not certify any model. Labels come from two blind LLM judges and a deterministic detector; they have not been reviewed by independent experts.

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

All columns follow [METHODOLOGY.md](METHODOLOGY.md).

## Track R: RAW (Initial TEGB v0.1 baseline, 2026-11-13)

<!-- TEGB:leaderboard_raw -->
| Model | UCR ↓ | Constraint Violations ↓ | Observability Errors ↓ | Scope Errors ↓ | Factual Accuracy ↑ |
|---|---:|---:|---:|---:|---:|
| EVE-Instruct | 79.7% | 52.8% | 63.2% | 31.0% | 31.7% |
| Mistral Small 3.2 | 72.8% | 47.2% | 60.7% | 33.3% | 40.2% |
| Claude Sonnet 5.5 | 37.8% | 10.2% | 18.3% | 2.4% | 87.2% |
| GPT-6.1 Terra | 13.0% | 5.7% | 14.5% | 7.1% | 89.6% |
<!-- /TEGB:leaderboard_raw -->

## Track S: TEXT (Initial TEGB v0.1 baseline, 2026-11-13)

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

## Submission requirements (for future entries)

1. Use the frozen prompts in `conditions/` unchanged, with ≤ 600 output tokens.
2. Run 3 runs per task and condition. Report decoding parameters and the exact model id returned by the API.
3. Score with the unchanged `harness/judge.py` (`judge-v2`) and `harness/evaluate.py` (`evaluate-v1`), using the same judge models, or state any change.
4. Submit the raw responses, judgments, `summary_*.json` and a `REPRODUCTION_REPORT.json`.
5. No fine-tuning on, or prompt engineering against, the v0.1 tasks. Report whether the model may have seen them.
