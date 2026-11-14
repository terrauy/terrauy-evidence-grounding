# Evaluate your model on TEGB

This guide takes a model you can call (hosted API, local server or your own code) and produces a validated TEGB v0.1 result that can be added to the [leaderboard](LEADERBOARD.md).

```text
install  →  configure a model adapter  →  run TEGB  →  score  →  generate a submission  →  open a pull request
```

**In short:**
- TEGB measures whether a model's conclusion stays within what the given Earth-observation evidence supports. It does not measure tool use or retrieval. Each item is single-turn: one prompt in, one answer out, no tool calls.
- `tegb score` always gives the free **core detector score**, a screening and pipeline check. It also gives the **reference evaluation** (two LLM judges) once the judges have run. Only the reference evaluation is comparable with the official baseline.
- You submit by pull request: one folder with your raw outputs and a `submission.json`.
- For the first five valid external TEGB v0.1 submissions, TerraUY may provide the reference LLM-judge evaluation at no cost to the submitting team, subject to the Early Evaluation Program limits. See [Early Evaluation Program](#early-evaluation-program).

You do not need access to the providers used by the official baseline. You need Python 3.11 or later and a way to call your model. The tools use only the Python standard library.

## 1. Install

```bash
git clone https://github.com/terrauy/terrauy-evidence-grounding.git
cd terrauy-evidence-grounding
python -m tegb --help
```

Optional: `pip install -e .` gives you the same commands as `tegb ...` instead of `python -m tegb ...`.

Multi-line commands in this guide are written for a POSIX shell. In PowerShell, write the command on one line or replace each trailing `\` with a backtick.

## 2. Configure a model adapter

An adapter turns one prompt into one answer. Pick the one that matches how you serve the model.

| Your model | Adapter | Example |
|---|---|---|
| Any OpenAI-compatible server: vLLM, llama.cpp, LM Studio, TGI, Hugging Face Inference Endpoints, most hosted APIs | `openai-compatible` | `--adapter openai-compatible --base-url http://localhost:8000/v1 --model my-model` |
| OpenAI API | `openai-compatible` | `--adapter openai-compatible --base-url https://api.openai.com/v1 --api-key-env OPENAI_API_KEY --model <model id>` |
| Ollama | `ollama` | `--adapter ollama --model llama3.1` (uses `http://localhost:11434/v1`) |
| Anthropic API | `anthropic` | `--adapter anthropic --api-key-env ANTHROPIC_API_KEY --model <model id>` (needs `pip install anthropic`) |
| A local program | `command` | `--adapter command --command "python my_model.py" --model my-model` |
| Your own Python code: transformers, a custom client, anything | `python` | `--adapter python --adapter-path my_adapter.py --model my-model` |

`--api-key-env` takes the **name** of an environment variable. The key itself is never passed on the command line and is never written to disk.

### Custom adapter in Python

Create a file with one function:

```python
# my_adapter.py
def generate(system: str, user: str, max_tokens: int = 600, temperature: float | None = None) -> str:
    return my_model(system=system, user=user, max_tokens=max_tokens, temperature=temperature)
```

A shorter form also works: `def generate(prompt: str) -> str`, which receives the system prompt and the user prompt joined by a blank line. That form cannot receive `temperature` or `max_tokens`, so the run is recorded as a protocol deviation and marked † on the leaderboard. Prefer the full signature.

For a local Hugging Face model, the function body is your usual `transformers` generation code. This sketch is not executed by our tests:

```python
from transformers import pipeline
pipe = pipeline("text-generation", model="org/model", device_map="auto")

def generate(system: str, user: str, max_tokens: int = 600, temperature: float | None = None) -> str:
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    sample = bool(temperature)
    out = pipe(messages, max_new_tokens=max_tokens, do_sample=sample, **({"temperature": temperature} if sample else {}))
    return out[0]["generated_text"][-1]["content"]
```

### Custom adapter as a program

The `command` adapter runs your program once per prompt. It writes `{"system", "user", "max_tokens", "temperature"}` as JSON to standard input and reads the answer from standard output. The program starts 738 times, so a model that loads slowly should be served behind an OpenAI-compatible server or used through the `python` adapter instead.

To check the pipeline without any model, `--adapter mock --model careful` (or `naive`) produces fixed fake answers at no cost. Mock results are never accepted as submissions.

## 3. Run TEGB

Start with a smoke test on two tasks (18 prompts), then run everything:

```bash
python -m tegb run --adapter openai-compatible --base-url http://localhost:8000/v1 --model my-model --output results/my-model --task-ids A01,D01
python -m tegb run --adapter openai-compatible --base-url http://localhost:8000/v1 --model my-model --output results/my-model
```

The full run sends 738 prompts: 82 tasks × 3 conditions (RAW, TEXT, STRUCTURED) × 3 runs. The protocol is fixed:
- the published prompts in `conditions/`, unchanged, with the common system prompt;
- at most 600 output tokens;
- run 0 at temperature 0, runs 1 and 2 at temperature 0.7. If your provider rejects `temperature`, its default sampling is used and recorded as a deviation.

The run can be interrupted and resumed: finished responses are kept.

Calls are made from 4 threads by default. For an in-process model (the `python` adapter with transformers) or a single-GPU program, add `--workers 1`. Failed calls are retried three times and reported as they happen; if the first calls all fail, the run stops.

Cost is yours: the prompts total roughly 1 million input tokens and at most 0.45 million output tokens. Check your provider's prices before running.

## 4. Score

```bash
python -m tegb score results/my-model
```

`score` always prints the core detector score. It also prints the reference evaluation once the judges have run; until then that part says "not available". They are different instruments and must not be confused.

| | Core detector score | Reference evaluation |
|---|---|---|
| Instrument | `harness/detect.py`: public regular-expression rules | Two blind LLM judges (`judge-v2`) plus the detector, merged by `harness/evaluate.py` |
| Cost | Free, offline, deterministic | Your own Anthropic and OpenAI keys. In the v0.1 baseline a judgment cost about USD 0.0065, so about USD 10 per model; check current prices. For the first five external submissions TerraUY may run it for you (Early Evaluation Program). |
| Metrics | Detector UCR (unsupported conclusion rate by the detector alone), constraint violations, scope errors, per-category rates | UCR, Constraint Violations, Observability Errors, Scope Errors, Factual Accuracy, per-category UCR |
| Comparable with the official baseline | **No.** Screening and pipeline check only. | **Yes.** Same instrument as the official baseline. |

**Limits of the core score.** It only sees forbidden phrases that are asserted. It misses unsupported stances and invented conclusions, it flags some careful answers by mistake, and it cannot tell a grounded answer from an empty or evasive one. Observability Errors and Factual Accuracy need the judges and are reported as `n/a`. The leaderboard shows how far the two instruments disagree on the baseline models.

To add the reference evaluation:

```bash
pip install anthropic openai
python -m tegb judge results/my-model --dry-run     # shows the number of calls and a rough cost; sends nothing
python -m tegb judge results/my-model               # reads ANTHROPIC_API_KEY and OPENAI_API_KEY; hard budget cap USD 15
python -m tegb score results/my-model
```

The reference judges are `claude-sonnet-5-5` and `gpt-6.1-terra`, as in the official baseline. Judge models can change over time, so the judging date is part of the result.

If you prefer not to run the judges yourself, submit with the core score only and ask for the reference evaluation in your pull request: see the [Early Evaluation Program](#early-evaluation-program).

## 5. Generate a submission

```bash
python -m tegb submit results/my-model \
  --model-name "My Model" --model-version "exact version or checkpoint" \
  --provider "who serves or publishes it" --submitter "your name or team" \
  --contamination no-known-exposure \
  --i-can-share-outputs
```

This writes `submissions/v0.1/<id>/`. `<id>` is the model name in lowercase with hyphens (`"My Model"` gives `my-model`), and `submit` prints it. To keep several versions of one model, set it yourself, for example `--submission-id my-model-1.0`.

The folder contains:
- `submission.json`: model, version, provider, date, prompt and decoding configuration, adapter, TEGB version, hashes of the task and prompt files, hash of the raw outputs, metrics, and your declarations;
- `responses.jsonl`: the 738 raw answers;
- `judgments.jsonl`: the judge verdicts, if you ran the reference evaluation.

The format is described in [submissions/README.md](submissions/README.md). No API key or other secret is stored, and the validator rejects files that contain something that looks like a credential.

Then check it:

```bash
python -m tegb validate submissions/v0.1/<id>      # PASS or FAIL, with reasons
```

## 6. Open the pull request

Fork the repository on GitHub, then push a branch that adds only your submission folder (your `results/` directory is ignored by git):

```bash
git checkout -b submit-<id>
git add submissions/v0.1/<id>
git commit -m "TEGB v0.1 submission: <model>"
git remote add fork <URL of your fork>
git push fork submit-<id>
```

Open the pull request with the submission template: on the "Open a pull request" page, add `?template=tegb_submission.md` to the URL (or `&template=tegb_submission.md` if the URL already has a `?`). The template holds the checklist, including the request for the Early Evaluation Program.

CI runs the same validation on the pull request. It never runs a model.

## Early Evaluation Program

For the first five valid external TEGB v0.1 submissions, TerraUY may provide the reference LLM-judge evaluation at no cost to the submitting team, subject to the Early Evaluation Program limits.

How it works:
1. Run your model and submit with the core score only (steps 1 to 5, without `tegb judge`).
2. In the pull request (submission template, see step 6), tick "I request the reference evaluation under the Early Evaluation Program".
3. If the submission is eligible, the maintainers run the two reference judges on your submitted answers and add the verdicts and the reference metrics to your pull request. The leaderboard shows who ran the judges.
4. Nothing is published without your approval: the result goes on the leaderboard only when your pull request is merged.

Evaluations used so far: **0 of 5** (this line is updated when a covered evaluation is merged).

Limits:
- the first five valid external submissions on TEGB v0.1, normally one per team and model;
- a real model: a constant or scripted responder is not eligible, even if it validates;
- declared protocol deviations do not exclude a submission; they are shown with the result;
- eligibility is decided by the maintainers, who answer in the pull request;
- the submitter is a third party not related to TerraUY;
- complete outputs (all 738 answers), `python -m tegb validate` prints `PASS`, and the model and its configuration are documented well enough to describe the result;
- the program covers the reference judges only. It does not cover the inference cost of your model or further experiments;
- it is a limited offer for early evaluations, not a permanent service, and it may end without notice once the five evaluations or its budget are used.

## Declarations you make

- **Contamination.** TEGB v0.1 has been public since 2026-11-13. Say, to the best of your knowledge, whether the model could have seen it: `no-known-exposure`, `possible-exposure`, `known-exposure` or `unknown`. Add `--training-cutoff YYYY-MM` when you know it. Nobody can verify this perfectly; it is recorded with the result.
- **No tuning on TEGB.** Do not tune prompts, fine-tune or select checkpoints on the v0.1 tasks and report the result as held-out. If you did, pass `--tuned-on-tegb`.
- **Rights to share outputs.** The raw outputs are published with the submission under [MODEL_OUTPUTS_NOTICE.md](MODEL_OUTPUTS_NOTICE.md). Confirm with `--i-can-share-outputs` that your provider's terms allow it.
- **Deviations.** Token-cap and temperature differences are detected and recorded automatically. Anything else that differs from the protocol (for example a model-specific system prompt or chat template) must be declared with `--deviation "..."`, which can be repeated. Deviations are shown on the leaderboard.

## What a TEGB result means

A result describes one model version, with one prompt, one decoding setup, on one date. It is not a universal ranking and not a certification. See [LEADERBOARD.md](LEADERBOARD.md#comparability-and-fairness) and [LIMITATIONS.md](LIMITATIONS.md).

Questions and problems: open a [GitHub issue](https://github.com/terrauy/terrauy-evidence-grounding/issues).
