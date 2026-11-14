# Model Outputs Notice

> **Model outputs are provided for research, evaluation and benchmark reproducibility. Their inclusion does not grant rights beyond those permitted by the originating model provider's applicable terms.**

## What counts as a model output in TEGB

- **Agent responses:** `results/baseline/raw/`, produced by:
  - `claude-sonnet-5-5` (Anthropic);
  - `gpt-6.1-terra` (OpenAI);
  - `eve-esa/EVE-Instruct` (open weights, ESA Φ-lab EVE project);
  - `mistralai/Mistral-Small-3.2-24B-Instruct-2506` (open weights, Mistral AI).
- **LLM-judge verdicts:**
  - `results/baseline/judged/`, produced by `claude-sonnet-5-5` and `gpt-6.1-terra`;
- **Model-generated text copied into analysis files:** for example the response excerpts in `extra_main.json`.

## Terms

1. Model outputs are **separate from TEGB-authored content**. They are **not** licensed under CC BY 4.0 and **not** under Apache-2.0.
2. **Proprietary models (OpenAI, Anthropic).**
   - Under the providers' commercial terms applicable to the API customer, the customer owns the outputs.
   - TEGB redistributes them **only** for research, model evaluation and benchmarking, to allow results to be reproduced.
3. **Open-weight models (EVE-Instruct, Mistral Small 3.2).** The models are released under Apache-2.0, and the licenses state no restriction on outputs. EVE-Instruct's model card requests citation of the EVE work.
4. **Not human content.** All model outputs are AI-generated. They are not presented as human-written content, and factual statements in them should not be relied upon.
5. **Not training material.**
   - TEGB does not grant permission to use any model output as training data, fine-tuning data, distillation data, reward/preference/label signals, or any other training material for AI models, where that may conflict with the originating provider's terms.
   - TEGB raw proprietary-model outputs are not distributed as training material for alternative foundation models.
6. **No endorsement.** Anthropic, OpenAI, Mistral AI, ESA and Hugging Face are named only as providers of the evaluated models or infrastructure. None of them sponsors, collaborates on, endorses or has reviewed TEGB.
7. **Use is separated from training.** Benchmark and evaluation use is permitted. Use as training material or signals (including labels, scores and rankings) for models intended to be alternatives to or substitutes for a provider's models or services is not permitted by the provider terms, and TEGB does not grant it. See `MODEL_OUTPUTS_RIGHTS_MATRIX.md`.

This notice describes the release design. It is not legal advice. Provider terms change; check the rights matrix date.
