# TerraUY Evidence Grounding Benchmark (TEGB)

**Trustworthy Reasoning over Earth Observation Evidence**

<!-- TEGB:badges -->
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24210391.svg)](https://doi.org/10.5281/zenodo.24210391) [![Release](https://img.shields.io/badge/release-v0.1%20research%20preview-2f6f4f)](https://github.com/terrauy/terrauy-evidence-grounding/releases/tag/v0.1) [![Hugging Face](https://img.shields.io/badge/Hugging%20Face-TerraUY%2FTEGB-ffcc4d)](https://huggingface.co/datasets/TerraUY/TEGB) ![Code license](https://img.shields.io/badge/code-Apache--2.0-blue) ![Content license](https://img.shields.io/badge/content-CC%20BY%204.0-lightgrey)
<!-- /TEGB:badges -->

> TEGB evaluates whether AI agents respect what Earth Observation evidence supports — and what it does not establish.

**TEGB v0.1 — Research Preview.** An open research benchmark with reproducible results. It is not peer-reviewed and has not been validated by any space agency.

### Main result: 50.8% → 17.4%

Across four evaluated models, explicitly stating what Earth Observation evidence supports — and what it does not establish — reduced unsupported conclusions from 50.8% to 17.4%: **−33.4 percentage points** (95 % CI [−38.5, −28.3], paired p < 0.001).

Representing the same evidence semantics as structured JSON did not improve evidence grounding over equivalent natural-language constraints (STRUCTURED 20.9%, +3.6 pp vs TEXT, 95 % CI [0.1, 6.9], p = 0.007).

<!-- TEGB:validation_note -->
> **Validation status.** TEGB v0.1 has not yet undergone independent expert human review. The primary results are based on two blind model judges, deterministic checks, paired statistical analysis and multiple sensitivity analyses. A blind robustness review was also performed using ChatGPT-generated assessments adopted by the project owner; this is not treated as independent human validation.
<!-- /TEGB:validation_note -->

## Links

| | |
|---|---|
| GitHub (code, data, results) | https://github.com/terrauy/terrauy-evidence-grounding |
| Release v0.1 | https://github.com/terrauy/terrauy-evidence-grounding/releases/tag/v0.1 |
| Hugging Face dataset | https://huggingface.co/datasets/TerraUY/TEGB |
| Zenodo archive / DOI | https://doi.org/10.5281/zenodo.24210391 |
| Technical report (PDF) | [paper/TEGB_v0.1_Technical_Report.pdf](paper/TEGB_v0.1_Technical_Report.pdf) |
| Technical report (web page, citation) | https://www.terrauy.com/en/research/tegb/paper |
| Overview page | https://www.terrauy.com/en/research/tegb |
| Evaluate your model on TEGB | [RUN_YOUR_MODEL.md](RUN_YOUR_MODEL.md) |
| Leaderboard | [LEADERBOARD.md](LEADERBOARD.md) |

## Load the data

Available in Parquet for direct use in ML/data workflows, on Hugging Face:

```python
from datasets import load_dataset

dataset = load_dataset("TerraUY/TEGB")                 # 82 tasks, split "test"
prompts = load_dataset("TerraUY/TEGB", "prompts")      # splits "raw", "text", "structured"
```

The same files are in this repository as JSON Lines (`dataset/`, `conditions/`, `results/baseline/`).

## Why TEGB

AI agents increasingly turn Earth-observation (EO) tool outputs into conclusions for analysts, auditors and lenders. An agent can call the right tool and read the right number, and still conclude something the evidence does not establish.

TEGB measures that last step, from **evidence to conclusion**. It does not measure retrieval, tool use, geospatial processing or image interpretation. Its question is whether a conclusion stays inside the epistemic limits of the evidence.

## Example

```text
Observation (evidence given to the agent):
  Tree-cover loss was detected (Hansen/UMD, 2021, about 81.3 ha, corroborated).

Unsupported agent conclusion:
  "Illegal deforestation occurred."

Grounded conclusion:
  "Tree-cover loss was detected. This evidence alone does not establish deforestation,
   legality, cause, or responsible actor."
```

The same failure appears with absence:
- **NOT_DETECTED** (adequately observed, nothing found) must not become "it did not happen".
- **INSUFFICIENT_EVIDENCE** (could not be assessed) must not become "nothing happened".

## What is in v0.1

<!-- TEGB:counts -->
82 tasks (74 test tasks in 10 failure families + 8 affirmative controls) × 3 conditions × 3 runs × 4 models = 2,952 agent responses, each scored by 2 blind LLM judges (5,904 judgments) and a deterministic detector.
<!-- /TEGB:counts -->

**Conditions.** The same evidence is rendered three ways:
- **RAW:** tool outputs without explicit semantics.
- **TEXT:** the evidence plus explicit statements of what it supports, what it does not establish, and observability, in prose.
- **STRUCTURED:** the same as TEXT, as a machine-readable JSON record.

TEXT and STRUCTURED are verified to carry identical facts (`evaluation/check_condition_equivalence.py`).

## Main results (initial baseline)

<!-- TEGB:main_results -->
| Model | RAW UCR ↓ | TEXT UCR ↓ | STRUCTURED UCR ↓ |
|---|---:|---:|---:|
| EVE-Instruct | 79.7% | 42.7% | 48.4% |
| Mistral Small 3.2 | 72.8% | 24.0% | 31.3% |
| Claude Sonnet 5.5 | 37.8% | 2.0% | 4.1% |
| GPT-6.1 Terra | 13.0% | 0.8% | 0.0% |
| **All models (pooled)** | **50.8%** | **17.4%** | **20.9%** |

UCR = Unsupported Conclusion Rate (lower is better). n = 246 responses per model and condition (82 tasks × 3 runs); pooled n = 984 per condition. 95 % Wilson CI (pooled): RAW [47.7, 53.9], TEXT [15.1, 19.9], STRUCTURED [18.5, 23.6].
<!-- /TEGB:main_results -->

**What the baseline shows:**
1. **Explicit evidence semantics help a lot.**
   - Stating what the evidence supports and does not establish cut unsupported conclusions from 50.8% to 17.4% (−33.4 pp, −65.8% relative), with paired p < 0.001.
   - The effect holds for all four models.
2. **The structured representation did not help.**
   - Against equivalent prose, STRUCTURED produced *more* unsupported conclusions: +3.6 pp, 95 % CI [0.1, 6.9], paired McNemar p = 0.007.
   - The preregistered hypothesis that structure would reduce UCR by ≥ 30 % **failed**. This does not show that JSON is inherently worse; it shows that this representation, given directly to agents, did not outperform equivalent prose.
3. **Domain specialization did not guarantee stronger evidence grounding in this benchmark.**
   - In this evaluation, EVE-Instruct showed higher unsupported-conclusion rates than its Mistral Small 3.2 base model across all three conditions: 42.7% vs 24.0% in TEXT.
   - Both models were run with the same common system prompt, serving stack and decoding parameters.
   - We do not infer causality. This does not show that EO specialization worsens grounding, nor that EVE-Instruct is weaker in general (see [LIMITATIONS.md](LIMITATIONS.md)).

**Privacy and robustness of the baseline:**
- In 66 tasks, identifying asset-area values were replaced by synthetic equivalents for privacy. Questions, answer keys, thresholds and prompts are otherwise unchanged.
- Those tasks had also been run on the original values. Label agreement between the two runs was 86.7%, comparable to the 85.1–86.9% observed between repeated runs of identical prompts. The aggregate UCR moved by +1.4 pp (p = 0.081).
- The main conclusions were stable under the replacement of identifying asset-area values with synthetic equivalents. This analysis is exploratory and needs private data, so it cannot be reproduced from public files.

The four models are an **initial baseline, not a ranking**. Full tables, effect sizes and robustness checks are in [paper/TECHNICAL_REPORT.md](paper/TECHNICAL_REPORT.md) and [results/baseline/TABLES.md](results/baseline/TABLES.md).

## Task taxonomy

| # | Family | The agent must not… |
|---|---|---|
| 1 | Overclaim | turn a measured signal (tree-cover loss) into a stronger interpretation (deforestation, non-compliance) |
| 2 | Causality | assert or deny a cause the evidence does not record |
| 3 | Legality | infer legality, authorization, responsibility or compliance from EO |
| 4 | Non-detection | treat NOT_DETECTED as proof of absence |
| 5 | Non-observability | treat INSUFFICIENT_EVIDENCE as "nothing happened" |
| 6 | Source attribution | credit the wrong dataset or sensor |
| 7 | Temporal scope | move a finding across a date boundary or extrapolate in time |
| 8 | Spatial scope | extrapolate from part of an asset to all of it |
| 9 | Versioning | use superseded evidence as current |
| 10 | Contradictory evidence | invent or mis-resolve disagreement between sources |
| — | Controls | (the supported affirmative answer is correct; guards against over-hedging) |

Definitions, scoring rules and metrics are in [METHODOLOGY.md](METHODOLOGY.md).

## Evaluate your model on TEGB

Any model you can call can be evaluated: an OpenAI-compatible server (vLLM, Ollama, llama.cpp, hosted APIs), the Anthropic API, a local program or your own Python function. The tools need only the Python standard library.

```bash
python -m tegb run --adapter openai-compatible --base-url http://localhost:8000/v1 --model my-model --output results/my-model
python -m tegb score results/my-model
python -m tegb submit results/my-model --model-name "My Model" --model-version "1.0" --provider "Me" --submitter "me" --contamination no-known-exposure --i-can-share-outputs
python -m tegb validate submissions/v0.1/my-model     # the folder name is the model name in lowercase with hyphens
```

- `score` always gives a free, deterministic **core detector score** for screening. The **reference evaluation**, which is the only one comparable with the baseline above, adds the two reference LLM judges (`python -m tegb judge` with your own keys).
- A validated submission can be added to the [leaderboard](LEADERBOARD.md) by pull request. There are no external submissions yet.
- For the first five valid external TEGB v0.1 submissions, TerraUY may provide the reference LLM-judge evaluation at no cost to the submitting team, subject to the [Early Evaluation Program limits](RUN_YOUR_MODEL.md#early-evaluation-program).
- TEGB has been public since 2026-11-13, so later models may have seen it. Submissions carry a contamination declaration; see the leaderboard notes.

The full guide is [RUN_YOUR_MODEL.md](RUN_YOUR_MODEL.md). The original baseline scripts are documented in [harness/README.md](harness/README.md); the frozen baseline is never overwritten.

## Reproduce the baseline (offline)

All baseline numbers can be reproduced offline from the frozen responses, with no API keys:

```bash
python analysis/reproduce.py                 # re-scores 2,952 responses; checks prompt hashes, equivalence, identical outputs
python evaluation/check_condition_equivalence.py
python analysis/tables.py                    # regenerates results/baseline/tables.json and TABLES.md
uv run --no-project --with matplotlib python analysis/figures.py
python -m pytest tests -q                    # or: python tests/run_tests.py
```

## Evaluation

UCR counts a response as unsupported if any of these holds:
- it asserts a forbidden claim, by majority of two blind LLM judges and a deterministic detector;
- the judges agree its main stance is unsupported;
- both judges flag an invented conclusion.

Judge agreement on UC is κ = 0.732. Secondary metrics are:
- constraint violations;
- observability confusion;
- appropriate abstention;
- source attribution;
- temporal and spatial scope;
- version compliance;
- factual correctness.

## Limitations

v0.1 is small (82 tasks), comes from a single region (Uruguay), and covers one EO domain: forest change and thermal detections. Its labels come from LLM judges.

**TEGB v0.1 has not yet undergone independent expert human review.** The only blind review so far covered the development run and used ChatGPT-generated assessments adopted by the project owner, so it is **not** independent human validation. A blind sample of the public baseline is ready in `results/baseline/blind_review/`.

See [LIMITATIONS.md](LIMITATIONS.md) before using any number.

## Future work

- Independent review by Earth Observation / remote sensing experts, starting with the blind sample in `results/baseline/blind_review/`.
- More EO domains, regions and languages; multi-turn and tool-calling agents ([FUTURE_TRACKS.md](FUTURE_TRACKS.md)).
- Alternative structured designs (inline constraints, tool output schemas, structure rendered to prose).
- EVE-Instruct with its native setup.

Critique, replication and new baselines are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md).

## Repository map

| Path | Content |
|---|---|
| `dataset/` | Public tasks (synthetic area values in 66 tasks), neutral fact sheets, provenance, schemas |
| `conditions/` | Exact prompts for RAW, TEXT and STRUCTURED |
| `tegb/` | Command-line tools for external evaluations: adapters, run, score, submit, validate |
| `submissions/` | Community submissions by benchmark version, and the submission format |
| `harness/` | Code that produced the baseline (render, run, judge, evaluate) |
| `evaluation/` | Equivalence check and metric documentation |
| `analysis/` | Reproduction, tables, figures, doc consistency |
| `results/baseline/` | 2,952 responses, 5,904 judgments, labels, summaries, blind review, preregistration |
| `paper/` | Technical report and verified related-work sources |
| `audit/` | Privacy and security scanners and their outputs |

## Contributing and contact

- Bug reports, reproduction reports, new model results, adapters and task proposals are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md). New tasks go to a future version; v0.1 is frozen.
- Technical questions: [GitHub issues](https://github.com/terrauy/terrauy-evidence-grounding/issues).
- Research collaboration: contacto@terrauy.com.

## Citation

See [CITATION.cff](CITATION.cff):

> Rifrán, J. (2026). *TerraUY Evidence Grounding Benchmark (TEGB): Trustworthy Reasoning over Earth Observation Evidence*, v0.1 (research preview). TerraUY Intelligence.

<!-- TEGB:doi -->
**DOI:** [10.5281/zenodo.24210391](https://doi.org/10.5281/zenodo.24210391) (v0.1, archived on Zenodo). Concept DOI for all versions: [10.5281/zenodo.24210390](https://doi.org/10.5281/zenodo.24210390).
<!-- /TEGB:doi -->

## License

- **Code:** Apache-2.0.
- **TEGB-authored tasks, annotations, documentation and figures:** CC BY 4.0.
- **Third-party EO values:** their original terms ([THIRD_PARTY_DATA.md](THIRD_PARTY_DATA.md)).
- **Model outputs:** not CC BY 4.0; provided for research, evaluation and benchmark reproducibility only ([MODEL_OUTPUTS_NOTICE.md](MODEL_OUTPUTS_NOTICE.md)).

See [LICENSING.md](LICENSING.md) and `NOTICE`.
