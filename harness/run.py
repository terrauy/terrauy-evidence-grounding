"""Run agents on the benchmark: tasks x conditions (A/B/C) x models x runs.

    uv run --no-project --with anthropic --with openai python harness/run.py --config harness/config.json [--dry-run]

Every response is cached (results/raw/<model_key>/<task>_<cond>_r<run>.json) with the full request
record (exact model id returned by the API, parameters, prompt hashes, versions, token usage, cost).
A spend ledger (results/spend.json) is updated after every call; the run stops before exceeding
`budget_usd` (hard cap) and never retries a failed call more than twice.
Keys come only from environment variables named in the config; they are never written anywhere.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render import PROMPT_VERSION, RENDER_VERSION, build_prompt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
# TEGB: frozen baseline lives in results/baseline; set TEGB_RESULTS_DIR for new runs and TEGB_OUT_DIR for evaluation outputs.
RESULTS = Path(os.environ.get("TEGB_RESULTS_DIR", ROOT / "results" / "baseline"))
OUT = Path(os.environ.get("TEGB_OUT_DIR", RESULTS))
RAW = RESULTS / "raw"
LEDGER = RESULTS / "spend.json"


def redact(s: str) -> str:
    """Mask anything that looks like a credential (providers echo masked keys in auth errors)."""
    import re

    return re.sub(r"(sk-|hf_)[A-Za-z0-9_\-\*]{4,}", "[REDACTED]", s)


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_tasks(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def ledger() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {"total_usd": 0.0, "calls": 0, "by_model": {}}


def save_ledger(lg: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(lg, indent=1), encoding="utf-8")


# ---- providers ----------------------------------------------------------------------------------
def call_anthropic(m: dict, system: str, user: str, temperature: float) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ[m["key_env"]], max_retries=2, timeout=120)
    kwargs = dict(model=m["model"], max_tokens=m.get("max_tokens", 600), system=system,
                  messages=[{"role": "user", "content": user}])
    if temperature is not None and not m.get("no_temperature"):
        kwargs["temperature"] = temperature
    r = client.messages.create(**kwargs)
    text = "".join(b.text for b in r.content if b.type == "text")
    return {"text": text, "model_returned": r.model, "input_tokens": r.usage.input_tokens,
            "output_tokens": r.usage.output_tokens, "stop_reason": r.stop_reason}


def call_openai(m: dict, system: str, user: str, temperature: float) -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ[m["key_env"]], base_url=m.get("base_url") or os.environ.get(m.get("base_url_env", "")) or None, max_retries=2, timeout=180)
    kwargs = dict(model=m["model"], messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    if m.get("max_tokens_param", "max_completion_tokens") == "max_tokens":
        kwargs["max_tokens"] = m.get("max_tokens", 600)
    else:
        kwargs["max_completion_tokens"] = m.get("max_tokens", 600)
    if temperature is not None and not m.get("no_temperature"):
        kwargs["temperature"] = temperature
    if m.get("reasoning_effort"):
        kwargs["reasoning_effort"] = m["reasoning_effort"]
    r = client.chat.completions.create(**kwargs)
    return {"text": r.choices[0].message.content or "", "model_returned": r.model,
            "input_tokens": r.usage.prompt_tokens, "output_tokens": r.usage.completion_tokens,
            "stop_reason": r.choices[0].finish_reason}


STUB_NAIVE = "Yes. The asset experienced deforestation: about 100 ha of forest was cleared in 2021, most likely due to harvest. No fire occurred."
STUB_CAREFUL = "The evidence supports tree-cover loss but does not establish deforestation, its cause or legality. Where nothing was detected, that is not proof that nothing happened."


def call_stub(m: dict, system: str, user: str, temperature: float) -> dict:
    """Deterministic fake agents to validate the pipeline at zero cost: 'naive' overclaims in every
    condition; 'careful' never does. 'cond_sensitive' overclaims in A/B and is careful in C."""
    cond = "C" if '"does_not_establish"' in user else ("B" if "does not establish:" in user else "A")
    kind = m["model"]
    text = STUB_NAIVE if kind == "naive" or (kind == "cond_sensitive" and cond != "C") else STUB_CAREFUL
    return {"text": text, "model_returned": f"stub-{kind}", "input_tokens": len(user) // 4, "output_tokens": len(text) // 4, "stop_reason": "end"}


PROVIDERS = {"anthropic": call_anthropic, "openai": call_openai, "stub": call_stub}


def price(m: dict, inp: int, out: int) -> float:
    return inp / 1e6 * m["price_in_per_mtok"] + out / 1e6 * m["price_out_per_mtok"]


def estimate(cfg: dict, tasks: list[dict]) -> dict:
    est = {}
    for m in cfg["models"]:
        n = len(tasks) * len(cfg["conditions"]) * len(cfg["runs"])
        inp = sum(len(build_prompt(t, c)[0] + build_prompt(t, c)[1]) / (36 / 10) for t in tasks for c in cfg["conditions"]) * len(cfg["runs"])
        out = n * m.get("expected_output_tokens", 220)
        est[m["key"]] = {"calls": n, "input_tokens": int(inp), "output_tokens": int(out), "usd": round(price(m, inp, out), 2)}
    est["total_usd"] = round(sum(v["usd"] for v in est.values()), 2)
    return est


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--dry-run", action="store_true", help="only estimate cost")
    ap.add_argument("--only", help="comma-separated model keys")
    ap.add_argument("--limit", type=int, help="first N tasks")
    ap.add_argument("--task-ids", help="comma-separated task ids (pilot)")
    ap.add_argument("--runs", type=int, help="only the first N runs (pilot uses 1: T=0)")
    ap.add_argument("--workers", type=int, default=4, help="concurrent requests per model")
    args = ap.parse_args()
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    tasks = load_tasks(ROOT / cfg["tasks"])
    if args.task_ids:
        keep = args.task_ids.split(",")
        tasks = [t for t in tasks if t["task_id"] in keep]
    if args.limit:
        tasks = tasks[: args.limit]
    if args.runs:
        cfg["runs"] = cfg["runs"][: args.runs]
    models = [m for m in cfg["models"] if not args.only or m["key"] in args.only.split(",")]
    cfg["models"] = models
    est = estimate(cfg, tasks)
    print("estimate:", json.dumps(est))
    if args.dry_run:
        return 0
    lg = ledger()
    if lg["total_usd"] + est["total_usd"] > cfg["budget_usd"]:
        print(f"STOP: projected {lg['total_usd'] + est['total_usd']:.2f} > budget {cfg['budget_usd']}")
        return 2
    import threading
    from concurrent.futures import ThreadPoolExecutor

    lock = threading.Lock()
    stop = threading.Event()

    def one(m: dict, t: dict, cond: str, run_i: int, temp: float, path: Path) -> None:
        if stop.is_set():
            return
        with lock:
            if lg["total_usd"] >= cfg["budget_usd"] * 0.95:
                stop.set(); print("STOP: spend reached 95% of budget"); return
        system, user = build_prompt(t, cond)
        started = time.perf_counter()
        err = ""
        for attempt in range(3):
            try:
                res = PROVIDERS[m["provider"]](m, system, user, temp)
                break
            except Exception as error:  # noqa: BLE001 — recorded, bounded retries
                err = redact(f"{type(error).__name__}: {str(error)[:200]}")
                if "temperature" in err.lower() and temp is not None:
                    m["no_temperature"] = True
                time.sleep(3 * (attempt + 1))
        else:
            print(f"FAILED {m['key']} {t['task_id']} {cond} r{run_i}: {err}", flush=True)
            return
        cost = price(m, res["input_tokens"], res["output_tokens"])
        rec = {"task_id": t["task_id"], "condition": cond, "run": run_i, "temperature": None if m.get("no_temperature") else temp,
               "model_key": m["key"], "provider": m["provider"], "model_requested": m["model"], **res,
               "latency_s": round(time.perf_counter() - started, 2), "cost_usd": round(cost, 6),
               "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
               "task_version": t["task_version"], "prompt_version": PROMPT_VERSION, "render_version": RENDER_VERSION,
               "system_sha256": sha(system), "user_sha256": sha(user), "max_tokens": m.get("max_tokens", 600),
               "reasoning_effort": m.get("reasoning_effort")}
        path.write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
        with lock:
            lg["total_usd"] = round(lg["total_usd"] + cost, 6)
            lg["calls"] += 1
            bm = lg["by_model"].setdefault(m["key"], {"usd": 0.0, "calls": 0})
            bm["usd"] = round(bm["usd"] + cost, 6)
            bm["calls"] += 1
            if lg["calls"] % 20 == 0:
                save_ledger(lg)
                print(f"  {m['key']} calls={bm['calls']} spend_total=${lg['total_usd']:.2f}", flush=True)

    for m in models:
        if m["provider"] != "stub" and not os.environ.get(m.get("key_env", "")):
            print(f"skip {m['key']}: env {m.get('key_env')} not set")
            continue
        if m.get("base_url_env") and not os.environ.get(m["base_url_env"]):
            print(f"skip {m['key']}: env {m['base_url_env']} not set")
            continue
        out_dir = RAW / m["key"]
        out_dir.mkdir(parents=True, exist_ok=True)
        jobs = [(t, cond, run_i, temp, out_dir / f"{t['task_id']}_{cond}_r{run_i}.json")
                for run_i, temp in enumerate(cfg["runs"]) for t in tasks for cond in cfg["conditions"]]
        jobs = [j for j in jobs if not j[4].exists()]
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            list(ex.map(lambda j: one(m, *j), jobs))
        save_ledger(lg)
        if stop.is_set():
            return 2
    print("done; spend:", json.dumps(lg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
