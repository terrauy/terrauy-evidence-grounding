| Comparison (66 substituted tasks) | n pairs | UCR, real values (development run) | UCR, synthetic values (public run) | Difference [95 % CI] | Label agreement | McNemar p |
|---|---:|---:|---:|---|---:|---|
| All conditions | 2376 | 30.1% | 31.5% | +1.4 pp [0.0, 2.6] | 86.7% | 0.081 |
| RAW | 792 | 48.6% | 51.6% | +3.0 pp [0.5, 5.6] | 84.6% | 0.037 |
| TEXT | 792 | 19.6% | 19.6% | +0.0 pp [-2.3, 2.3] | 87.9% | 1.0 |
| STRUCTURED | 792 | 22.2% | 23.2% | +1.0 pp [-1.1, 3.4] | 87.6% | 0.48 |

Noise reference: label agreement between two repeated runs with identical prompts (run 1 vs run 2, T = 0.7, same 66 tasks) is 86.9% (public run) and 85.1% (development run); real vs synthetic agreement at T = 0 (non-Claude models) is 90.4%. Within these 66 tasks, TEXT − RAW was -29.0 pp (real) vs -32.1 pp (synthetic), and STRUCTURED − TEXT was +2.6 pp vs +3.7 pp. Exploratory; requires private data, not reproducible from public files.
