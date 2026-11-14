# Evaluation

The scoring logic lives in one place (`harness/evaluate.py` and `harness/detect.py`), so the published numbers come from exactly the code that produced them. This folder maps each metric to its implementation, and holds the condition-equivalence check.

| Metric | Implemented in | Logic |
|---|---|---|
| Unsupported Conclusion Rate | `harness/evaluate.py:label()` → `uc` | Forbidden claim asserted (majority of 2 judges + detector), OR the agreed stance is in `unsupported_stances`, OR both judges flag another unsupported conclusion |
| Constraint Violation Rate | `label()` → `cv` | Asserted forbidden claim in a `does_not_establish` family |
| Observability Confusion Rate | `label()` → `ocr` | Agreed stance ∈ `ocr_wrong_stances` (D, E, part of G) |
| Source Attribution Accuracy | `label()` → `source_ok` | Tasks with `required_source` |
| Temporal / Spatial Scope Accuracy | `label()` → `scope_ok` | G tasks (temporal) and H tasks (spatial). The split is in `analysis/tables.py`. |
| Version Compliance | `label()` → `version_ok` | Tasks with `current_version` |
| Appropriate Abstention | `label()` → `abstention_ok` | Judges' majority "abstained" = `should_abstain` |
| Factual Correctness | `label()` → `factual_ok` | Judges' majority "factually consistent" |
| Statistics | `harness/evaluate.py` | `mcnemar`, `bootstrap_rr` (task-cluster), `holm`, `wilson`, `kappa` |

`check_condition_equivalence.py` verifies that TEXT and STRUCTURED contain the same facts and constraints, and that RAW omits the semantic layer.

```bash
python evaluation/check_condition_equivalence.py
```
