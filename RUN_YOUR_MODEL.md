# Evaluate your model on TEGB

This guide takes a model you can call (hosted API, local server or your own code) and produces a validated TEGB v0.1 result that can be added to the [leaderboard](LEADERBOARD.md).

```text
install  →  configure a model adapter  →  run TEGB  →  score  →  generate a submission
```

**In short:**
- TEGB measures whether a model's conclusion stays within what the given Earth-observation evidence supports. It does not measure tool use or retrieval.
- `tegb score` gives two results. Only the **reference evaluation** (two LLM judges) is comparable with the official baseline. The free **core detector score** is a screening and pipeline check.
- You submit by pull request: one folder with your raw outputs and a `submission.json`.
- For the first five valid external TEGB v0.1 submissions, TerraUY may provide the reference LLM-judge evaluation at no cost to the submitting team, subject to the Early Evaluation Program limits. See [Early Evaluation Program](#early-evaluation-program).

You do not need access to the providers used by the official baseline. You need Python 3.11 or later and a way to call your model. The tools use only the Python standard library.

## 1. Install

```bash
git clone https://github.com/terrauy/terrauy-evidence-grounding.git
cd terrauy-evidence-grounding
python -m tegb --help
```

The commands below are written for a POSIX shell. In PowerShell, write each command on one line or replace the trailing `\` with a backtick.

Optional: `pip install -e .` gives you the same commands as `tegb ...` instead of `python -m tegb ...`.

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

Create a file with one function. Any of these signatures works:

```python
# my_adapter.py
def generate(prompt: str) -> str:
    """Receives the system prompt and the user prompt joined by a blank line."""
    return my_model(prompt)

# or, if your model takes a system prompt separately:
# def generate(system: str, user: str, max_tokens: int = 600, temperature: float | None = None) -> str: ...
```

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

The `command` adapter runs your program once per prompt. It writes `{"system", "user", "max_tokens", "temperature"}` as JSON to standard input and reads the answer from standard output.

## 3. Run TEGB

```bash
python -m tegb run \
  --adapter openai-compatible --base-url http://localhost:8000/v1 \
  --model my-model \
  --output results/my-model
```

This sends 738 prompts: 82 tasks × 3 conditions (RAW, TEXT, STRUCTURED) × 3 runs. The protocol is fixed:
- the published prompts in `conditions/`, unchanged, with the common system prompt;
- at most 600 output tokens;
- run 0 at temperature 0, runs 1 and 2 at temperature 0.7. If your provider rejects `temperature`, its default sampling is used and recorded as a deviation.

The run can be interrupted and resumed: finished responses are kept. Try a small smoke test first with `--task-ids A01,D01`.

Cost is yours: the prompts total roughly 1 million input tokens and at most 0.45 million output tokens. Check your provider's prices before running.

## 4. Score

```bash
python -m tegb score results/my-model
```

You get two results. They are different instruments and must not be confused.

| | Core detector score | Reference evaluation |
|---|---|---|
| Instrument | `harness/detect.py`: public regular-expression rules | Two blind LLM judges (`judge-v2`) plus the detector, merged by `harness/evaluate.py` |
| Cost | Free, offline, deterministic | Your own Anthropic and OpenAI keys. In the v0.1 baseline a judgment cost about USD 0.0065, so about USD 10 per model; check current prices. For the first five external submissions TerraUY may run it for you (Early Evaluation Program). |
| Metrics | Unsupported conclusion rate by the detector, constraint violations, scope errors, per-category rates | UCR, Constraint Violations, Observability Errors, Scope Errors, Factual Accuracy, per-category UCR |
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

This writes `submissions/v0.1/<id>/` with:
- `submission.json`: model, version, provider, date, prompt and decoding configuration, adapter, TEGB version, hashes of the task and prompt files, hash of the raw outputs, metrics, and your declarations;
- `responses.jsonl`: the 738 raw answers;
- `judgments.jsonl`: the judge verdicts, if you ran the reference evaluation.

The format is described in [submissions/README.md](submissions/README.md). No API key or other secret is stored, and the validator rejects files that contain something that looks like a credential.

Then check it and open a pull request that adds only that folder:

```bash
python -m tegb validate submissions/v0.1/<id>      # PASS or FAIL, with reasons
```

CI runs the same validation on the pull request. It never runs a model.

## Early Evaluation Program

For the first five valid external TEGB v0.1 submissions, TerraUY may provide the reference LLM-judge evaluation at no cost to the submitting team, subject to the Early Evaluation Program limits.

How it works:
1. Run your model and submit with the core score only (steps 1 to 5, without `tegb judge`).
2. In the pull request, tick "I request the reference evaluation under the Early Evaluation Program".
3. If the submission is eligible, the maintainers run the two reference judges on your submitted answers and add the verdicts and the reference metrics to your pull request. The leaderboard shows who ran the judges.
4. Nothing is published without your approval: the result goes on the leaderboard only when your pull request is merged.

Limits:
- the first five valid external submissions on TEGB v0.1, normally one per team and model;
- the submitter is a third party not related to TerraUY;
- complete outputs (all 738 answers), `python -m tegb validate` prints `PASS`, and the model and its configuration are documented well enough to describe the result;
- the program covers the reference judges only. It does not cover the inference cost of your model or further experiments;
- it is a limited offer for early evaluations, not a permanent service, and it may end without notice once the five evaluations or its budget are used.

## Declarations you make

- **Contamination.** TEGB v0.1 has been public since 2026-11-13. Say, to the best of your knowledge, whether the model could have seen it: `no-known-exposure`, `possible-exposure`, `known-exposure` or `unknown`. Add `--training-cutoff YYYY-MM` when you know it. Nobody can verify this perfectly; it is recorded with the result.
- **No tuning on TEGB.** Do not tune prompts, fine-tune or select checkpoints on the v0.1 tasks and report the result as held-out. If you did, pass `--tuned-on-tegb`.
- **Rights to share outputs.** The raw outputs are published with the submission under [MODEL_OUTPUTS_NOTICE.md](MODEL_OUTPUTS_NOTICE.md). Confirm with `--i-can-share-outputs` that your provider's terms allow it.
- **Deviations.** Anything that differs from the protocol (token cap, sampling, a model-specific system prompt) must be declared with `--deviation "..."`. Declared deviations are shown on the leaderboard; undeclared ones fail validation.

## What a TEGB result means

A result describes one model version, with one prompt, one decoding setup, on one date. It is not a universal ranking and not a certification. See [LEADERBOARD.md](LEADERBOARD.md#comparability-and-fairness) and [LIMITATIONS.md](LIMITATIONS.md).

Questions and problems: open a [GitHub issue](https://github.com/terrauy/terrauy-evidence-grounding/issues).
