# Harness

This is the code that produced the v0.1 baseline. The only changes from the archived run are the directory constants (`RESULTS`, `OUT`) and the config path.

| File | Role |
|---|---|
| `render.py` | Renders the three conditions from the canonical evidence (`render-v1`, `prompt-v1`) and checks TEXT/STRUCTURED equivalence |
| `run.py` | Runs agents (providers: Anthropic Messages API, OpenAI-compatible chat completions, stub). Caches one file per response, keeps a spend ledger with a hard budget cap, and redacts credentials. |
| `judge.py` | Blind LLM judges (`judge-v2`, with the neutral fact sheet) |
| `detect.py` | Deterministic detector (`detect-v1`) |
| `evaluate.py` | Final labels, metrics, preregistered statistics and verdict (`evaluate-v1`) |
| `analysis_extra.py` | Exploratory analyses |
| `human_review_analysis.py` | Blind-review analysis. Refuses to open the key until the review is complete. |
| `config.baseline.json` | Baseline models, prices and judges. It contains environment-variable names only. |

## Evaluating a new model (costs money; uses your own keys)

```bash
# 1. add your model to a copy of config.baseline.json (provider, model id, key_env, prices)
# 2. write to a NEW results directory so the frozen baseline is never touched
export TEGB_RESULTS_DIR=results/my_run
python harness/run.py   --config harness/my_config.json --dry-run      # cost estimate
python harness/run.py   --config harness/my_config.json --only my-model
python harness/judge.py --config harness/my_config.json --only-model my-model
TEGB_OUT_DIR=results/my_run python harness/evaluate.py --config harness/my_config.json --tag main
```

Keep the prompts, 600-token cap, 3 runs, judges and scoring unchanged for comparability (see `LEADERBOARD.md`).

**Known provider quirks:**
- `claude-sonnet-5-5` rejects `temperature`, and its default reasoning counts toward `max_tokens`.
- Some OpenAI models accept only the default temperature.
