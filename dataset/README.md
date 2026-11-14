# TEGB v0.1 dataset files

| File | Content |
|---|---|
| `tasks.jsonl` | 82 public tasks. Public variant of the preregistered file (synthetic area values ≥ 2 ha in 66 tasks; hash in amendment 2). **Never edit.** |
| `area_substitution.json` | IDs of the 66 tasks with synthetic area values (no mapping) |
| `fact_sheets.jsonl` | Condition-neutral fact sheet per task, as given to the judges |
| `provenance.jsonl` | `real_derived` (15) or `synthetic_derived` (67), with a note |
| `task_schema.json` | JSON Schema of a task, validated by `tests/run_tests.py` |
| `evidence_unit.schema.json` | Experimental canonical evidence schema (`evidence-unit/0.1-exp`). It is used to generate equivalent conditions, not proposed as a standard. |
| `build_public_files.py` | Regenerates the fact sheets, provenance and `../conditions/*/prompts.jsonl` from `tasks.jsonl` |

Composition, provenance policy and attribution are in [../DATASET_CARD.md](../DATASET_CARD.md).
