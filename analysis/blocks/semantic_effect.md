| Model | TEXT − RAW UCR difference | 95 % CI (task-cluster bootstrap) | Relative change | McNemar exact (discordant pairs) |
|---|---:|---|---:|---|
| **All models (pooled)** | -33.4 pp | [-38.5, -28.3] | -65.8% | p = 3.8e-80 (347 vs 18) |
| EVE-Instruct | -37.0 pp | [-45.5, -28.5] | -46.4% | p = 3.0e-22 (97 vs 6) |
| Mistral Small 3.2 | -48.8 pp | [-58.9, -38.6] | -67.0% | p = 5.8e-29 (128 vs 8) |
| Claude Sonnet 5.5 | -35.8 pp | [-44.7, -27.2] | -94.6% | p = 1.7e-24 (90 vs 2) |
| GPT-6.1 Terra | -12.2 pp | [-19.5, -5.7] | -93.8% | p = 6.9e-08 (32 vs 2) |

Negative = fewer unsupported conclusions with explicit evidence semantics. Discordant pairs: (RAW unsupported, TEXT not) vs (TEXT unsupported, RAW not).
