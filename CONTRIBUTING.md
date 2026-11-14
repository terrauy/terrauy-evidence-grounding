# Contributing to TEGB

TEGB v0.1 is a research preview published to be checked. Criticism, replications and results on new models are welcome.

## What you can contribute

| Contribution | How |
|---|---|
| **Bug report** (code, data, documentation, a wrong label) | Open an issue with the "Bug report" template |
| **External model result** | Follow [RUN_YOUR_MODEL.md](RUN_YOUR_MODEL.md) and open a pull request with the "TEGB model submission" template |
| **Reproduction report** (you re-ran the analysis or the baseline) | Open an issue with the "Reproduction report" template, whether it matched or not |
| **Adapter** for another way of serving models | Pull request to `tegb/adapters.py` with a test in `tests/test_external_flow.py` |
| **New task proposal** | Open an issue with the "New task proposal" template |

## Early Evaluation Program

For the first five valid external TEGB v0.1 submissions, TerraUY may provide the reference LLM-judge evaluation at no cost to the submitting team, subject to the Early Evaluation Program limits. The steps and limits are in [RUN_YOUR_MODEL.md](RUN_YOUR_MODEL.md#early-evaluation-program).

## Rules that keep results comparable

1. **v0.1 is frozen.** Tasks, answer keys, prompts, the baseline responses, judgments, labels and metrics of v0.1 do not change. A confirmed error is documented in `LIMITATIONS.md` and fixed in a later version.
2. **New tasks do not enter v0.1.** Accepted proposals are collected for a future version, which will have its own hashes, baseline and leaderboard.
3. **No results without artifacts.** A leaderboard entry needs the raw outputs and a `submission.json` that passes `python -m tegb validate`. Numbers typed by hand are not accepted.
4. **Scores of different benchmark versions are never mixed.**
5. **No tuning on the benchmark.** Do not tune prompts or models on the v0.1 tasks and report the result as held-out.

## Pull requests

- A model submission adds only `submissions/v0.1/<id>/`. CI validates it; it never runs a model and has no secrets.
- Code changes need the tests to pass:

```bash
python tests/run_tests.py --full        # includes the full reproduction and the external-submitter simulation
python analysis/docs_sync.py --check
python audit/scan.py
```

- Do not commit API keys, private endpoints, personal data or data about real properties. The scanners in `audit/` run on every file.
- By contributing you agree that your contribution is released under the repository's terms: Apache-2.0 for code, CC BY 4.0 for tasks and documentation, and [MODEL_OUTPUTS_NOTICE.md](MODEL_OUTPUTS_NOTICE.md) for model outputs.

## What TEGB is not

- Not a universal ranking of models, and not a certification for regulatory, legal, credit or insurance decisions.
- Not a training dataset. Do not use the tasks or outputs to train, fine-tune or distill models.
- Not information about any real property.

## Contact

- Technical questions, bugs and results: [GitHub issues](https://github.com/terrauy/terrauy-evidence-grounding/issues).
- Research collaboration: contacto@terrauy.com.

TEGB has not yet been reviewed by independent Earth Observation or remote sensing experts. If you are one and want to review a sample of the labels, the blind sample is in `results/baseline/blind_review/`; please open an issue first.
