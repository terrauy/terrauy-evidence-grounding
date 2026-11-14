# Model outputs: rights matrix

**terms_verified_at: 2026-11-13T23:35:02Z (UTC)**, on the publication date, against the live public documents listed. Result: no material incompatibility with publishing the outputs for research, evaluation and benchmark reproducibility. This is a factual summary of what those documents say. It is not legal advice.

OpenAI's updated Usage Policies (already shown at the policy URL) take effect on 2026-11-20; their wording is applied below. Anthropic's Usage Policy in force is the version effective 2026-11-12.

**Status scale:**
- `PERMITTED FOR BENCHMARK RELEASE`: the documents allow the use, subject to the listed conditions.
- `RESTRICTED`: the documents forbid the use.
- `UNCLEAR`: the documents do not settle the question.

Each output type is assessed separately for two uses:
- **Benchmark / evaluation use:** publishing the outputs so others can inspect, reproduce and compare the benchmark results.
- **Training use:** using the outputs as training material or signals for AI models.

## Matrix

| | Claude Sonnet 5.5: agent responses and judge verdicts | GPT-6.1 Terra: agent responses and judge verdicts | EVE-Instruct: agent responses | Mistral Small 3.2: agent responses |
|---|---|---|---|---|
| **Exact model id** (from logs) | `claude-sonnet-5-5` | `gpt-6.1-terra` | `eve-esa/EVE-Instruct`, rev `eecb769f` | `mistralai/Mistral-Small-3.2-24B-Instruct-2506`, rev `95a6d26c` |
| **Provider** | Anthropic (API) | OpenAI (API) | ESA Φ-lab EVE project; open weights, self-served on a private Hugging Face Endpoint | Mistral AI; open weights, self-served on a private Hugging Face Endpoint |
| **Terms / license source** | Commercial Terms of Service (effective 2025-06-17); Usage Policy (effective 2026-11-12) | Services Agreement (effective 2026-01-01); Usage Policies (current version 2025-10-29; **updated version effective 2026-11-20**); Sharing & Publication Policy | Apache-2.0 (model metadata); model card | Apache-2.0 (model metadata); model card |
| **Output ownership** | Customer owns its Outputs (§B), subject to compliance with the Terms | Customer owns all Output (§4.1), to the extent permitted by law; output may not be unique | Apache-2.0 has no output clause; the card sets no restriction | Apache-2.0 has no output clause; the card sets no restriction |
| **Benchmark / evaluation use (redistribution)** | No clause forbids publishing. The customer must evaluate outputs before sharing (§D.3). → **PERMITTED FOR BENCHMARK RELEASE** | The Usage Policies state that OpenAI models may be used "for research, software development, model evaluation and benchmarking, and product development, within these limits". Research publication is welcomed by the Sharing & Publication Policy. → **PERMITTED FOR BENCHMARK RELEASE** | Not restricted → **PERMITTED FOR BENCHMARK RELEASE** | Not restricted → **PERMITTED FOR BENCHMARK RELEASE** |
| **Training use** | No using outputs to train competing models (§D.4(a)), and no supporting third parties in doing so (§D.4(c)). Usage Policy: no training an AI model on outputs without prior authorization. → **RESTRICTED** | From 2026-11-20, outputs must not be used to generate, prepare, select or provide training material or signals (including labels, scores, rankings, preferences, rewards or corrections) **for models intended to be alternatives to, or substitutes for, OpenAI's models or services**. This also applies when evaluation outputs are later supplied for those purposes. Earlier, the Services Agreement already barred using Output to develop competing models (§3.3(e)). → **RESTRICTED** for that purpose | None stated → not restricted by the license. TEGB still does not offer outputs as training data. | None stated → not restricted by the license. TEGB still does not offer outputs as training data. |
| **Required attribution / disclosure** | Do not mislead about origin or attribute falsely. Factual assertions in outputs should not be relied upon (§D.3). No implied endorsement. | Do not represent outputs as human-written; make clear they are AI-generated. No use of OpenAI name or logo as relationship or endorsement (§10). | Citation of EVE requested by the model card. Outputs are machine-generated. | Apache-2.0 notices for the weights (the weights are not redistributed) |
| **Conclusion for TEGB** | **PERMITTED FOR BENCHMARK RELEASE**, with conditions | **PERMITTED FOR BENCHMARK RELEASE**, with conditions | **PERMITTED FOR BENCHMARK RELEASE** | **PERMITTED FOR BENCHMARK RELEASE**. Residual: whether Mistral's platform terms reach self-served weights was not verified. |

**Conditions applied to every published model output:**
1. **Purpose.** Research, model evaluation and benchmarking only. Explicitly **not** a training dataset, fine-tuning corpus, distillation set or RL / label / preference dataset. `MODEL_OUTPUTS_NOTICE.md` and a notice in each output directory say so.
2. **Disclosure.** All outputs are AI-generated and not presented as human content. No reliance on factual assertions.
3. **No endorsement.** Providers are named only as providers of the evaluated models. No sponsor, collaborator or endorser relationship is stated or implied.
4. **Re-check.** Provider terms were re-checked on the publication date (2026-11-13T23:35:02Z) and should be re-checked for any later release.
5. **No logos, no relationship claims.** No OpenAI or Anthropic logos are used, and no partnership or relationship is stated (OpenAI Services Agreement §10).

**Not published, for privacy and not for rights reasons:**
- The development run on real area values.
- The 120-item blind review of that run (ChatGPT-generated assessments adopted by the owner). Its responses contain real values.

Only its aggregate statistics are reported, labelled as development-run results.

**Not verified:**
- the scope of OpenAI §10 "No Publicity" with respect to naming the model in results;
- Anthropic brand guidelines;
- whether Mistral's commercial terms reach self-served Apache-2.0 weights;
- Hugging Face Endpoint output ownership, on which the Hugging Face documents are silent.

Sources: https://openai.com/policies/usage-policies/ (version effective 2026-11-20, read 2026-11-13) · https://openai.com/policies/services-agreement/ · https://openai.com/policies/sharing-publication-policy/ · https://www.anthropic.com/legal/commercial-terms · https://www.anthropic.com/legal/aup · https://huggingface.co/eve-esa/EVE-Instruct · https://huggingface.co/mistralai/Mistral-Small-3.2-24B-Instruct-2506 · https://www.apache.org/licenses/LICENSE-2.0 · https://legal.mistral.ai/terms/commercial-terms-of-service · https://huggingface.co/terms-of-service
