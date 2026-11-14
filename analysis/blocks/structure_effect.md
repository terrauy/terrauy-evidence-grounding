| Model | STRUCTURED − TEXT UCR difference | 95 % CI (task-cluster bootstrap) | Relative change | McNemar exact (discordant pairs) |
|---|---:|---|---:|---|
| **All models (pooled)** | +3.6 pp | [0.1, 6.9] | +20.5% | p = 0.0068 (62 vs 97) |
| EVE-Instruct | +5.7 pp | [-3.3, 14.2] | +13.3% | p = 0.13 (30 vs 44) |
| Mistral Small 3.2 | +7.3 pp | [-0.8, 15.0] | +30.5% | p = 0.038 (25 vs 43) |
| Claude Sonnet 5.5 | +2.0 pp | [-1.6, 5.7] | +100.0% | p = 0.3 (5 vs 10) |
| GPT-6.1 Terra | -0.8 pp | [-2.4, 0.0] | -100.0% | p = 0.5 (2 vs 0) |

Positive = more unsupported conclusions with the structured representation. Discordant pairs: (TEXT unsupported, STRUCTURED not) vs (STRUCTURED unsupported, TEXT not). Preregistered success criterion (≥ 30 % relative reduction vs TEXT) was not met: preregistered verdict **FAIL**.
