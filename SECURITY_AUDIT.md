# Security audit: TEGB v0.1

| | |
|---|---|
| **Date** | 2026-11-13 |
| **Scope** | Every file in the v0.1 release |
| **Tool** | `audit/scan.py`, output in `audit/security_scan.json` |
| **Result** | **PASS** |

| Check | Result |
|---|---|
| API keys: Anthropic (`sk-ant-…`), OpenAI (`sk-…`, `sk-proj-…`), Hugging Face (`hf_…`), GitHub, AWS, Google, Stripe | 0 hits |
| JWTs / Supabase tokens, bearer tokens | 0 hits |
| Private keys (`-----BEGIN … PRIVATE KEY-----`) | 0 hits |
| Credentials in URLs, password/secret assignments | 0 hits |
| `.env` files | none |
| Production credentials and cloud tokens | none |
| Internal endpoint credentials and hostnames | none. The private inference-endpoint hostnames used during the run are only in the internal archive. |
| Private logs | none. The spend ledger and the key-capture log are not included; the cost summary (`results/baseline/cost_final.json`) holds amounts only. |

**How credentials were handled during the original run:**
- Keys were read only from dedicated environment variables and never written to any file.
- Provider error messages were redacted before logging.
- The production assistant key was verified, by comparing values without revealing them, to differ from the benchmark key and to have never been used.
- Unused benchmark credentials were revoked. The two remaining active benchmark credentials (one OpenAI key that expires 2026-11-20, one Hugging Face token) are not part of this release, and revoking them is left to the owner.
- Both GPU inference endpoints are paused, and billing was verified as stopped.

**Model configuration.** `harness/config.baseline.json` names environment variables (e.g. `TERRAUY_BENCH_OPENAI_API_KEY`), never values. A user running new models supplies their own keys.
