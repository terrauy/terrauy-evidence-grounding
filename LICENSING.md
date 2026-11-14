# Licensing architecture

**Owner decision (2026-11-13):**
- **Code:** Apache-2.0.
- **TEGB-authored content:** CC BY 4.0.
- **Model outputs:** under a separate notice, not CC BY 4.0.
- **Third-party EO values:** under their original terms.

This document describes the release structure. It is not legal advice.

<!-- TEGB:copyright -->
Copyright © 2026 Jairo Rifrán. Project/brand: TerraUY Intelligence.

| Component | License / terms |
|---|---|
| TEGB code (`harness/`, `evaluation/`, `analysis/`, `audit/`, `tests/`, `dataset/build_public_files.py`) | Apache License 2.0 (`LICENSE`) |
| TEGB-authored tasks, answer keys, annotations, fact-sheet structure, documentation and figures | CC BY 4.0 (`LICENSES/CC-BY-4.0.md`) |
| Third-party EO source values embedded in the evidence | Original source terms + attribution (`THIRD_PARTY_DATA.md`) |
| Model outputs (agent responses and LLM-judge verdicts) | **Not** licensed under CC BY 4.0. See `MODEL_OUTPUTS_NOTICE.md` and `MODEL_OUTPUTS_RIGHTS_MATRIX.md` |
<!-- /TEGB:copyright -->

## Tiers

| Tier | What | Terms | File |
|---|---|---|---|
| 1. TerraUY-authored code | `harness/`, `evaluation/`, `analysis/`, `audit/`, `tests/`, `dataset/build_public_files.py` | **Apache-2.0** | `LICENSE` |
| 2. TerraUY-authored benchmark content | Tasks (questions, answer keys, allowed/forbidden claims, rules, rationales), fact-sheet structure, provenance annotations, documentation, figures | **CC BY 4.0** | `LICENSES/CC-BY-4.0.md` |
| 3. Third-party EO source values | Values derived from Hansen/UMD GFC, JRC GFC2020, NASA FIRMS and MGAP, quoted inside evidence records | **Original source terms, with attribution** | `THIRD_PARTY_DATA.md` |
| 4a. Proprietary model outputs | Responses and judge verdicts produced by `claude-sonnet-5-5` (Anthropic) and `gpt-6.1-terra` (OpenAI) | **Not CC BY 4.0.** Redistributed for research, evaluation and reproducibility under the provider's terms. | `MODEL_OUTPUTS_NOTICE.md`, `MODEL_OUTPUTS_RIGHTS_MATRIX.md` |
| 4b. Open-weight model outputs | Responses by `eve-esa/EVE-Instruct` and `mistralai/Mistral-Small-3.2-24B-Instruct-2506` (self-served) | **Not CC BY 4.0.** Subject to each model's own license, verified individually. | `MODEL_OUTPUTS_NOTICE.md`, `MODEL_OUTPUTS_RIGHTS_MATRIX.md` |

**Model outputs** are:
- `results/baseline/raw/` (agent responses);
- `results/baseline/judged/` (judge verdicts);
- the `text`/`rationale` fields copied into `extra_main.json` (examples).

Each of those directories carries a `MODEL_OUTPUTS_NOTICE.txt`. The labels, metrics and statistics computed from the outputs are TEGB-authored (tier 2).

**Copyright.** The copyright holder is set in `release_config.json`; the default is the individual author, because no legal entity has been confirmed as IP holder. `analysis/release_meta.py` regenerates `NOTICE` and the block above. No IP transfer is implied.

## Checks completed for v0.1

1. Provider and data terms re-verified on the publication date: `terms_verified_at` = 2026-11-13T23:35:02Z (UTC), recorded in `release_config.json` and `MODEL_OUTPUTS_RIGHTS_MATRIX.md`. No material incompatibility was found.
2. JRC GFC2020 V4 terms re-verified (free of charge, without restriction of use, acknowledgement required).
3. Copyright holder confirmed by the owner: © 2026 Jairo Rifrán; project/brand TerraUY Intelligence. No IP transfer to any legal entity is implied.
