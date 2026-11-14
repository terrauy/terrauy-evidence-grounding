# Changelog

## Unreleased: external evaluation tools (tools 0.1.1; benchmark version still v0.1)

- `tegb` command-line tools: provider-agnostic adapters, `run`, `score`, `judge`, `submit`, `validate`, `leaderboard`, `hashes`.
- Submission format `tegb-submission/1` (`submissions/`), validator, pull-request and issue templates, CI that validates submissions without running any model.
- `RUN_YOUR_MODEL.md`, `CONTRIBUTING.md`, leaderboard split into the official baseline and community submissions (none yet), contamination and comparability notes, `dataset/task_hashes.json`.
- Technical report revised as a preprint manuscript: research questions, contributions, extended related work and limitations. No result changed.
- No v0.1 task, prompt, response, judgment, label or metric changed; `analysis/reproduce.py` and the test `test_scorer_reproduces_official_baseline` verify this.

## Unreleased (documentation only)

- Added the Zenodo DOI, Hugging Face and overview-page links to the README, cards, citation file and technical report. No task, prompt, response, judgment, label or metric changed; the archived v0.1 snapshot is unchanged.

## v0.1 — Research Preview (2026-11-13)

First public release: 82 tasks, three conditions (RAW, TEXT, STRUCTURED), initial baseline of four models (2,952 responses, 5,904 judge verdicts), preregistration with two amendments, reproduction scripts, technical report.

Archived on Zenodo: DOI 10.5281/zenodo.24210391 (concept DOI 10.5281/zenodo.24210390).

Results and data files of v0.1 are frozen. Later changes to documentation (for example adding the DOI) do not change tasks, prompts, responses, judgments, labels or metrics; `analysis/reproduce.py` verifies this.
