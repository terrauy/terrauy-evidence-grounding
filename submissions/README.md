# TEGB submissions

One folder per submitted model, grouped by benchmark version:

```text
submissions/
  submission.schema.json        JSON Schema of submission.json (tegb-submission/1)
  v0.1/
    <submission_id>/
      submission.json           metadata, hashes, metrics, declarations
      responses.jsonl           the 738 raw model answers (82 tasks x 3 conditions x 3 runs)
      judgments.jsonl           optional: verdicts of the two reference judges
      README.md                 optional: notes from the submitter
```

There are no external submissions yet. `v0.1/` is empty.

## How the files are made

`python -m tegb submit` writes them from a finished run. Do not edit them by hand: `python -m tegb validate` recomputes every hash and metric and fails on any difference. The full walkthrough is in [RUN_YOUR_MODEL.md](../RUN_YOUR_MODEL.md).

## submission.json

| Field | Content |
|---|---|
| `schema`, `benchmark_version`, `submission_id`, `date` | Format version, TEGB version (`v0.1`), folder name, date of the submission |
| `model` | Name, exact version, provider, model ids returned by the API, open or closed weights, training cutoff if known |
| `submitter` | Public name; optional public contact and affiliation |
| `protocol` | Runs, temperature per run, output-token cap, prompt source, declared deviations |
| `run` | Adapter, tools version, start and end time, decoding notes |
| `hashes` | SHA-256 of the task file, of the three prompt files, of `responses.jsonl` and of `judgments.jsonl` |
| `stats` | Number of responses, empty responses, truncated responses |
| `metrics.core` | Core detector score: deterministic, screening only |
| `metrics.reference` | Reference evaluation, or `null` when the judges were not run |
| `reference_evaluation` | Who ran the two reference judges and when: the submitter, or the maintainers (for example under the Early Evaluation Program) |
| `declarations` | Contamination statement, tuning on TEGB, right to share the outputs |

No API keys, tokens or endpoint credentials belong in any of these files. The validator rejects anything that looks like a credential.

## What the validator checks

1. Required metadata and the benchmark version.
2. Only the expected files, each under 12 MB, with nothing that looks like a credential.
3. The task and prompt file hashes equal those of this benchmark version.
4. All 738 responses are present, with no duplicates, and each was produced from the published prompt (prompt hashes).
5. `responses.jsonl` matches its recorded hash. At most 5 % of the answers may be empty.
6. Protocol deviations are declared.
7. If `judgments.jsonl` is present: both reference judges for every response, answered by the reference judge models, and each verdict tied to the submitted answer (judge prompt hash).
8. Every metric is recomputed from the raw files and must equal the reported value. Rates must lie between 0 and 1.

The result is `PASS` or `FAIL` with the reasons. The validator cannot prove that a model was really the one named, that judge verdicts were not fabricated, or that the model never saw TEGB. Those rest on the submitter's declaration.

## Licensing of submitted material

Raw model outputs and judge verdicts are published under [MODEL_OUTPUTS_NOTICE.md](../MODEL_OUTPUTS_NOTICE.md): for research, evaluation and benchmark reproducibility, not as training data. By submitting, you confirm that your provider's terms allow you to share them.
