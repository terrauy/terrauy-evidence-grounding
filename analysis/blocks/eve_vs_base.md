| Condition | Mistral Small 3.2 (base) UCR | EVE-Instruct UCR | Difference (EVE − base) | McNemar exact (base better vs EVE better) |
|---|---:|---:|---:|---|
| RAW | 72.8% | 79.7% | +6.9 pp | p = 0.016 (31 vs 14) |
| TEXT | 24.0% | 42.7% | +18.7 pp | p = 9.8e-08 (61 vs 15) |
| STRUCTURED | 31.3% | 48.4% | +17.1 pp | p = 2.0e-06 (60 vs 18) |

Same tasks, conditions, runs, serving stack (vLLM 0.29.0, 1× A100 80 GB, BF16), system prompt and decoding parameters; n = 246 pairs per condition.
