| Model key | Exact model id returned by the API / server | Serving |
|---|---|---|
| eve-instruct-24b | `eve-esa/EVE-Instruct` | HF Inference Endpoint, vLLM 0.29.0, 1× A100 80 GB, BF16, revision eecb769f; T = 0 / 0.7 / 0.7 |
| mistral-small-3.2-base | `mistralai/Mistral-Small-3.2-24B-Instruct-2506` | HF Inference Endpoint, vLLM 0.29.0, 1× A100 80 GB, BF16, revision 95a6d26c; T = 0 / 0.7 / 0.7 |
| claude-sonnet-5-5 | `claude-sonnet-5-5` | Anthropic API; provider-default sampling (temperature not accepted) |
| gpt-6.1-terra | `gpt-6.1-terra` | OpenAI API; reasoning_effort=none; T = 0 / 0.7 / 0.7 |
