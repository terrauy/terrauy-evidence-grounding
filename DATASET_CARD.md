# Dataset Card: TEGB v0.1 tasks

<!-- TEGB:validation_note -->
> **Validation status.** TEGB v0.1 has not yet undergone independent expert human review. The primary results are based on two blind model judges, deterministic checks, paired statistical analysis and multiple sensitivity analyses. A blind robustness review was also performed using ChatGPT-generated assessments adopted by the project owner; this is not treated as independent human validation.
<!-- /TEGB:validation_note -->

<!-- TEGB:doi -->
**DOI:** [10.5281/zenodo.24210391](https://doi.org/10.5281/zenodo.24210391) (v0.1, archived on Zenodo). Concept DOI for all versions: [10.5281/zenodo.24210390](https://doi.org/10.5281/zenodo.24210390).
<!-- /TEGB:doi -->

Hugging Face (Parquet, `load_dataset("TerraUY/TEGB")`): https://huggingface.co/datasets/TerraUY/TEGB · GitHub: https://github.com/terrauy/terrauy-evidence-grounding · Overview: https://www.terrauy.com/en/research/tegb

## Summary

- **82 tasks** (`dataset/tasks.jsonl`, `tasks-v0.1`): 74 test tasks in 10 failure families plus 8 affirmative controls.
- **What a task is:** an analyst question about a physical asset, the EO evidence returned by tools, and an answer key.
- **Public variant:** the file is the public variant of the preregistered tasks. In 66 tasks every area value ≥ 2 ha was replaced by a synthetic equivalent for privacy (preregistration amendment 2); nothing else changed. Its SHA-256 is recorded in `PREREGISTRATION.amendment-2.json`, and `analysis/reproduce.py` checks it. The preregistered original stays in the internal archive.

## Files

| File | Content |
|---|---|
| `tasks.jsonl` | One task per line. Fields: `task_id`, `category`, `question`, `units` (canonical evidence), `expected_safe_conclusion`, `allowed_claims`, `forbidden_claims` (family, description, detector patterns), `evaluation_rules` (acceptable/unsupported stances, abstention, required source, current version, observability-wrong stances), `rationale`, `evidence_state`, `case`, `synthetic_derived`, `emblematic`, `task_version` |
| `fact_sheets.jsonl` | Condition-neutral fact sheet per task: every leaf value of the evidence units. This is what the judges see. |
| `provenance.jsonl` | Provenance class per task |
| `area_substitution.json` | IDs of the 66 tasks whose area values are synthetic. The mapping is not published. |
| `task_schema.json` | JSON Schema of a task record |
| `evidence_unit.schema.json` | Experimental schema of the canonical evidence record (`evidence-unit/0.1-exp`) |
| `../conditions/{raw,text,structured}/prompts.jsonl` | The exact system and user prompt per task and condition, with SHA-256. All 2,952 baseline responses are verified to come from exactly these prompts. |

## Composition

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
| Controls | 8 |

**Evidence states:**
- tree-cover loss: 71 tasks (SUPPORTED, NOT_DETECTED, PENDING_CORROBORATION, INSUFFICIENT_EVIDENCE, CONTRADICTED);
- thermal detection: 11 tasks (NOT_DETECTED, partial coverage).

**Sources that actually appear in the evidence:**
- Hansen/UMD Global Forest Change: GFC-2025-v1.13; older versions appear only in versioning tasks.
- JRC Global Forest Cover 2020: V4.
- Uruguay MGAP national forest cartography: 2021.
- NASA FIRMS: VIIRS S-NPP, VIIRS NOAA-20, VIIRS NOAA-21 and MODIS.

Sentinel-2 appears only as a distractor in a source-attribution question; it is not part of any evidence.

## Dataset anonymization and provenance policy

**Provenance classes:**

| Class | Meaning | Tasks |
|---|---|---:|
| `real_derived` | Evidence values come from a real EO assessment, extracted read-only from production and anonymized. No area values are present in these tasks. The question, answer key and forbidden claims were written by the authors. | 15 |
| `synthetic_derived` | Evidence structure and statuses come from a real case, but values were deliberately changed. Either area values ≥ 2 ha were replaced by synthetic equivalents for privacy (66 tasks), or the case was modified to build a scenario the real data did not contain (versioning). | 67 |
| `synthetic` | Fully invented evidence | 0 |

**Origin of the real cases:**
- 11 Land & Forest Change assessments (16 events) and the fire contexts used by 11 tasks.
- The extraction (2026-11-12) used an allow-list of fields.
- An aggregate check (2026-11-13) confirmed that **all assets behind the tasks belong to TerraUY's own organization**, not to customers.
- The extraction also contained two fire contexts from another organization. No task uses them, and the case file that contained them is **not** distributed.

**Removed or never extracted:**
- organization, tenant, user and asset identifiers;
- database and record ids;
- geometry, centroids, bounding boxes;
- cadastral (padrón) references;
- place names;
- URLs and object-store paths;
- hashes of private windows;
- private production metadata.

Case labels (`LFC-01`, `FIRE-03`, …) are sequential labels with no meaning outside this dataset.

**Replaced by synthetic equivalents** (66 tasks):
- asset areas;
- event, forest-type and sub-threshold areas ≥ 2 ha;
- the percentages derived from them.

Each value received an independent secret factor (0.65–0.89 or 1.15–1.50). Values below 2 ha were kept. The method thresholds (0.5 ha, 2 ha, 2 %) are preserved for every value, and sums and percentages are recomputed. Only the numbers changed in questions, answer keys and detector patterns.

**Retained as evidence:**
- years;
- forest-type context, including planted species;
- dataset versions;
- method parameters;
- fire-monitoring periods and detection counts.

These are needed to pose the reasoning tasks. See [PRIVACY_AUDIT.md](PRIVACY_AUDIT.md).

## Intended use and limits

Use the dataset for evaluating evidence-to-conclusion grounding. Do not use it as information about any real property. Most area values are synthetic, and the evidence describes method outputs at a point in time, under specific method versions.

The dataset is small. It covers a single region and one EO domain. Its labels come from two blind LLM judges and a deterministic detector; it has not yet been reviewed by independent EO / remote sensing experts (future work). See [LIMITATIONS.md](LIMITATIONS.md).

## Intended use

TEGB is for **research, model evaluation and benchmarking** of evidence-to-conclusion grounding in Earth-observation agents.

## Prohibited / unsupported use

- **TEGB is not a training corpus.** TEGB raw proprietary-model outputs are not distributed as training material for alternative foundation models. They are not a fine-tuning corpus and not a reinforcement-learning dataset.
- Do not train, fine-tune or tune prompts on the tasks and then report TEGB results as held-out (contamination).
- Do not use the tasks or outputs as information about any real property, or for regulatory, legal, credit or insurance decisions.
- Do not present model outputs as human-written content.
- Do not imply endorsement by any model provider, data provider or space agency.

## Licensing and attribution

- **Tasks, annotations and documentation:** CC BY 4.0.
- **Code:** Apache-2.0.
- **Third-party EO values:** their original terms. See [THIRD_PARTY_DATA.md](THIRD_PARTY_DATA.md).
- **Model outputs:** a separate notice. See [MODEL_OUTPUTS_NOTICE.md](MODEL_OUTPUTS_NOTICE.md).

The full structure is in [LICENSING.md](LICENSING.md).
