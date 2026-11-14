<!-- Use this template for a model result: append ?template=tegb_submission.md to the pull-request URL. -->

## TEGB model submission (benchmark version v0.1)

**Model:** <!-- name and exact version -->
**Folder added:** `submissions/v0.1/<id>/`

### Checklist

- [ ] The pull request adds only `submissions/v0.1/<id>/` (`submission.json`, `responses.jsonl`, optionally `judgments.jsonl` and `README.md`).
- [ ] The files were written by `python -m tegb submit` and were not edited by hand.
- [ ] `python -m tegb validate submissions/v0.1/<id>` prints `PASS`.
- [ ] The run used the published prompts, at most 600 output tokens and 3 runs, or every deviation is declared in `submission.json`.
- [ ] The contamination declaration reflects my best knowledge of whether the model saw TEGB.
- [ ] I did not tune prompts, fine-tune or select checkpoints on TEGB v0.1 tasks (or I declared it with `--tuned-on-tegb`).
- [ ] I am allowed to publish these raw model outputs, and I accept that they are released under `MODEL_OUTPUTS_NOTICE.md`.
- [ ] No API key, token, private endpoint or personal data is included.

### Evaluation included

- [ ] Core detector score only (screening; not comparable with the official baseline)
- [ ] Reference evaluation (both reference judges, run with my own keys on: <!-- date -->)
- [ ] I request the reference evaluation under the Early Evaluation Program (first five valid external submissions; see RUN_YOUR_MODEL.md). I am not related to TerraUY, and I agree that the maintainers add the judge verdicts and reference metrics to this pull request. The result is published only if this pull request is merged.

### Notes for the maintainers

<!-- Serving stack, quantization, anything unusual about the run. -->
