"""tegb: run a model on TEGB, score it, and package / validate a leaderboard submission.

    python -m tegb run      --adapter openai-compatible --base-url http://HOST/v1 --model my-model --output results/my-model
    python -m tegb score    results/my-model
    python -m tegb judge    results/my-model          # optional reference evaluation (your own judge API keys)
    python -m tegb submit   results/my-model --model-name "My Model" --model-version 1.0 --provider "Me" --submitter "me"
    python -m tegb validate submissions/v0.1/my-model
    python -m tegb leaderboard                        # maintainers: regenerate the community tables
    python -m tegb unpack / attach-reference          # maintainers: reference evaluation of a core-only submission

Nothing here calls a model unless you run `tegb run` or `tegb judge` with your own endpoint or keys.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from tegb import BENCHMARK_VERSION, SUBMISSION_SCHEMA, TOOLS_VERSION, adapters, core

ROOT = core.ROOT


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _refuse_frozen(path: Path) -> None:
    if _inside(path, core.FROZEN):
        raise SystemExit("refusing to write inside results/baseline (the frozen v0.1 baseline); choose another directory")


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", s.lower()).strip("-.")[:63] or "model"


def _pct(x) -> str:
    return "  n/a" if x is None else f"{100 * x:5.1f}%"


def _model_keys(results: Path) -> list[str]:
    return sorted(p.name for p in (results / "raw").iterdir() if p.is_dir()) if (results / "raw").is_dir() else []


def _pick_key(results: Path, wanted: str | None) -> str:
    keys = _model_keys(results)
    if wanted:
        if wanted not in keys:
            raise SystemExit(f"no responses for model key '{wanted}' in {results}/raw (found: {keys})")
        return wanted
    if len(keys) != 1:
        raise SystemExit(f"{results}/raw holds {len(keys)} model keys {keys}; pass --model-key")
    return keys[0]


# ---- run ----------------------------------------------------------------------------------------
def cmd_run(a: argparse.Namespace) -> int:
    out = Path(a.output)
    _refuse_frozen(out)
    try:
        adapter = adapters.build(a.adapter, a.model, base_url=a.base_url, api_key_env=a.api_key_env, command=a.command,
                                 adapter_path=a.adapter_path, max_tokens_param=a.max_tokens_param)
    except adapters.AdapterError as e:
        raise SystemExit(f"adapter error: {e}") from None
    key = _slug(a.model_key or a.model)
    tasks, prompts = core.load_tasks(), core.load_prompts()
    ids = sorted(tasks)
    if a.task_ids:
        wanted = [x.strip() for x in a.task_ids.split(",") if x.strip()]
        unknown = [x for x in wanted if x not in tasks]
        if unknown:
            raise SystemExit(f"unknown task ids: {', '.join(unknown)} (ids look like A01, D01; see dataset/tasks.jsonl)")
        ids = [t for t in ids if t in wanted]
    if a.limit:
        ids = ids[: a.limit]
    raw = out / "raw" / key
    raw.mkdir(parents=True, exist_ok=True)
    jobs = [(t, c, r) for r in range(len(core.RUN_TEMPERATURES)) for t in ids for c in core.CONDITIONS]
    todo = [j for j in jobs if not (raw / f"{j[0]}_{j[1]}_r{j[2]}.json").exists()]
    print(f"TEGB {BENCHMARK_VERSION}: {len(jobs)} prompts ({len(ids)} tasks x 3 conditions x 3 runs), {len(todo)} to run, adapter {adapter.name}, model {a.model}")
    started = datetime.now(UTC).isoformat(timespec="seconds")
    failed, lock, n_done, stop = [], threading.Lock(), [0], threading.Event()

    def one(job) -> None:
        if stop.is_set():
            return
        t, c, r = job
        p = prompts[(t, c)]
        err = ""
        for attempt in range(3):
            t0 = time.perf_counter()
            try:
                res = adapter.generate(p["system"], p["user"], max_tokens=a.max_tokens, temperature=core.RUN_TEMPERATURES[r])
                break
            except Exception as e:  # noqa: BLE001 - recorded, bounded retries
                msg = " ".join(str(e).split())
                err = re.sub(r"(sk-|hf_)[A-Za-z0-9_\-\*]{4,}", "[REDACTED]", f"{type(e).__name__}: {msg if len(msg) <= 500 else msg[:150] + ' ... ' + msg[-340:]}")
                if stop.is_set():
                    return
                time.sleep(2 * (attempt + 1))
        else:
            with lock:
                failed.append((job, err))
                if len(failed) <= 3:
                    print(f"FAILED {job}: {err}", flush=True)
                if len(failed) >= 8 and n_done[0] == 0 and not stop.is_set():
                    stop.set()
                    print("STOPPING: the first calls all failed. Fix the adapter or endpoint and run again; finished answers are kept.", flush=True)
            return
        rec = {"task_id": t, "condition": c, "run": r, "temperature": res["temperature_used"], "model_key": key, "provider": adapter.name,
               "adapter": adapter.name, "model_requested": a.model, "text": res["text"], "model_returned": res["model_returned"],
               "input_tokens": res["input_tokens"], "output_tokens": res["output_tokens"], "stop_reason": res["stop_reason"],
               "latency_s": round(time.perf_counter() - t0, 2), "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
               "task_version": tasks[t].get("task_version"), "prompt_version": p.get("prompt_version"), "render_version": p.get("render_version"),
               "system_sha256": core.sha256_text(p["system"]), "user_sha256": core.sha256_text(p["user"]), "max_tokens": a.max_tokens}
        (raw / f"{t}_{c}_r{r}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
        with lock:
            n_done[0] += 1
            if n_done[0] % 50 == 0:
                print(f"  {n_done[0]}/{len(todo)}", flush=True)

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(ex.map(one, todo))
    cfg = {"benchmark_version": BENCHMARK_VERSION, "tools_version": TOOLS_VERSION, "model_key": key, "model_requested": a.model,
           "adapter": adapter.name, "max_tokens": a.max_tokens, "temperatures": core.RUN_TEMPERATURES, "started_at": started,
           "finished_at": datetime.now(UTC).isoformat(timespec="seconds"), "python": sys.version.split()[0]}
    (out / f"run_config_{key}.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    if len(failed) > 3:
        print(f"... and {len(failed) - 3} more failed calls (last error: {failed[-1][1]})")
    print(f"done: {n_done[0]} new responses, {len(failed)} failed, results in {raw}")
    return 2 if failed else 0


# ---- judge (optional reference evaluation; uses the submitter's own keys) -------------------------
def cmd_judge(a: argparse.Namespace) -> int:
    results = Path(a.results)
    _refuse_frozen(results)
    key = _pick_key(results, a.model_key)
    base = json.loads((ROOT / "harness" / "config.baseline.json").read_text(encoding="utf-8"))
    envs = {"anthropic": a.anthropic_key_env, "openai": a.openai_key_env}
    judges = []
    for j in base["judges"]:
        judges.append({**j, "key_env": envs[j["provider"]]})
    cfg = {"tasks": base["tasks"], "conditions": base["conditions"], "runs": base["runs"], "budget_usd": a.budget_usd, "models": [], "judges": judges}
    cfg_path = results / "judge_config.json"
    cfg_path.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    n = len(list((results / "raw" / key).glob("*.json")))
    print(f"reference judges: {', '.join(core.REFERENCE_JUDGES.values())}; {n} responses x 2 judges; budget cap USD {a.budget_usd}")
    if a.dry_run:
        print("dry run: nothing was sent. Rough cost in the v0.1 baseline: about USD 0.0065 per judgment "
              f"(about USD {0.0065 * 2 * n:.2f} here); check your providers' current prices.")
        return 0
    if a.retry_unparsed:
        for jk in core.REFERENCE_JUDGES:
            for p in (results / "judged" / jk).glob(f"{key}__*.json"):
                if not json.loads(p.read_text(encoding="utf-8")).get("parsed"):
                    p.unlink()
    env = {**os.environ, "TEGB_RESULTS_DIR": str(results.resolve())}
    return subprocess.run([sys.executable, str(ROOT / "harness" / "judge.py"), "--config", str(cfg_path), "--only-model", key,
                           "--workers", str(a.workers)], env=env).returncode  # noqa: S603


# ---- score --------------------------------------------------------------------------------------
def _print_score(key: str, sc: dict, stats: dict, why_no_ref: str | None) -> None:
    print(f"\nModel key: {key}   responses: {stats['n_responses']}   empty: {stats['empty_responses']}   truncated: {stats['truncated_responses']}")
    for track, title in (("reference", "REFERENCE evaluation (two blind LLM judges + detector; comparable with the official baseline)"),
                         ("core", "CORE detector score (deterministic; screening only, NOT comparable with reference UCR)")):
        s = sc[track]
        print(f"\n{title}")
        if s is None:
            print(f"  not available: {why_no_ref}")
            continue
        ucr = "UCR" if track == "reference" else "Detector UCR"
        print(f"  {'condition':<11}{ucr:>13}{'Constraint viol.':>18}{'Observability err.':>20}{'Scope err.':>12}{'Factual acc.':>14}")
        for cond, m in s["by_condition"].items():
            print(f"  {cond:<11}{_pct(m['ucr']):>13}{_pct(m['constraint_violations']):>18}{_pct(m['observability_errors']):>20}"
                  f"{_pct(m['scope_errors']):>12}{_pct(m['factual_accuracy']):>14}")
        print(f"  {ucr} by category (RAW / TEXT / STRUCTURED):")
        for cat, v in s["ucr_by_category"].items():
            print(f"    {cat:<24} {_pct(v['RAW'])} {_pct(v['TEXT'])} {_pct(v['STRUCTURED'])}")


def _score_dir(results: Path, key: str) -> tuple[dict, list[dict], dict | None, str | None]:
    tasks = core.load_tasks()
    responses, judgments, why = core.read_results(results, key)
    missing = core.expected_keys(tasks) - {(r["task_id"], r["condition"], r["run"]) for r in responses}
    sc = core.score(responses, judgments, tasks)
    sc.update({"benchmark_version": BENCHMARK_VERSION, "tools_version": TOOLS_VERSION, "model_key": key, "complete": not missing,
               "missing_responses": len(missing), "stats": core.response_stats(responses), "reference_unavailable_reason": why})
    return sc, responses, judgments, why


def cmd_score(a: argparse.Namespace) -> int:
    results = Path(a.results)
    out = Path(a.out) if a.out else results / "scores"
    _refuse_frozen(out)
    keys = [a.model_key] if a.model_key else _model_keys(results)
    if not keys:
        raise SystemExit(f"no responses under {results}/raw")
    for key in keys:
        sc, _, _, why = _score_dir(results, _pick_key(results, key))
        out.mkdir(parents=True, exist_ok=True)
        (out / f"score_{key}.json").write_text(json.dumps(sc, indent=1), encoding="utf-8")
        _print_score(key, sc, sc["stats"], why)
        if not sc["complete"]:
            print(f"\n  INCOMPLETE: {sc['missing_responses']} of {len(core.expected_keys(core.load_tasks()))} responses are missing; a submission needs all of them.")
        print(f"\n  written: {out / f'score_{key}.json'}")
    return 0


# ---- submit -------------------------------------------------------------------------------------
def cmd_submit(a: argparse.Namespace) -> int:
    results = Path(a.results)
    key = _pick_key(results, a.model_key)
    sc, responses, judgments, why = _score_dir(results, key)
    if not sc["complete"]:
        raise SystemExit(f"incomplete run: {sc['missing_responses']} responses missing; finish `tegb run` first")
    if not a.i_can_share_outputs:
        raise SystemExit("add --i-can-share-outputs after confirming that your provider's terms allow publishing the raw model outputs "
                         "(they are published with the submission); nothing was written")
    sid = _slug(a.submission_id or a.model_name)
    folder = Path(a.out) if a.out else ROOT / "submissions" / BENCHMARK_VERSION / sid
    _refuse_frozen(folder)
    if folder.name != sid:
        folder = folder / sid
    folder.mkdir(parents=True, exist_ok=True)
    core.write_jsonl(core.slim_responses(responses), folder / "responses.jsonl")
    hashes = {k: v for k, v in core.task_hashes().items() if k in ("tasks_file_sha256", "prompt_files_sha256")}
    hashes["responses_sha256"] = core.sha256_bytes((folder / "responses.jsonl").read_bytes())
    if judgments is not None:
        core.write_jsonl(core.slim_judgments(judgments), folder / "judgments.jsonl")
        hashes["judgments_sha256"] = core.sha256_bytes((folder / "judgments.jsonl").read_bytes())
    elif (folder / "judgments.jsonl").exists():
        (folder / "judgments.jsonl").unlink()
    cfg_path = results / f"run_config_{key}.json"
    run_cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    dev = core.protocol_deviations(responses)
    sub = {
        "schema": SUBMISSION_SCHEMA, "benchmark_version": BENCHMARK_VERSION, "submission_id": sid,
        "date": a.date or datetime.now(UTC).date().isoformat(),
        "model": {"name": a.model_name, "version": a.model_version, "provider": a.provider, "url": a.model_url,
                  "ids_returned": sc["stats"]["models_returned"], "weights": a.weights, "training_cutoff": a.training_cutoff},
        "submitter": {"name": a.submitter, "contact": a.contact, "affiliation": a.affiliation},
        "protocol": {**core.protocol_of(responses), "system_prompt": "TEGB v0.1 common system prompt (unchanged)",
                     "deviations": [*dev, *(a.deviation or [])]},
        "run": {"adapter": responses[0].get("adapter") or responses[0].get("provider") or run_cfg.get("adapter") or "unknown",
                "tools_version": TOOLS_VERSION, "started_at": run_cfg.get("started_at"), "finished_at": run_cfg.get("finished_at"),
                "python": run_cfg.get("python"), "decoding_notes": a.decoding_notes},
        "hashes": hashes,
        "stats": sc["stats"],
        "metrics": {"core": sc["core"], "reference": sc["reference"]},
        "declarations": {"contamination": a.contamination, "contamination_notes": a.contamination_notes,
                         "tuned_on_tegb": bool(a.tuned_on_tegb), "rights_to_share_outputs": bool(a.i_can_share_outputs),
                         "outputs_are_ai_generated": True},
        "notes": a.notes,
    }
    if judgments is not None:
        sub["reference_evaluation"] = {"evaluated_by": "submitter", "date": datetime.now(UTC).date().isoformat()}
    (folder / "submission.json").write_text(json.dumps(sub, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    rep = core.validate_submission(folder, allow_mock=a.allow_mock)
    print(f"submission written to {folder}  (submission id: {sid})")
    print("reference evaluation:", "included" if judgments is not None else f"not included ({why})")
    for w in rep["warnings"]:
        print("warning:", w)
    print("validation:", rep["result"], *rep["errors"], sep="\n  ")
    return 0 if rep["result"] == "PASS" else 1


# ---- maintainers: reference evaluation of a submission that arrived with the core score only ----------
def cmd_unpack(a: argparse.Namespace) -> int:
    """Rebuild a results directory from a submission folder so the reference judges can be run on it."""
    folder, out = Path(a.submission), Path(a.output)
    _refuse_frozen(out)
    rep = core.validate_submission(folder, allow_mock=a.allow_mock)
    if rep["result"] != "PASS":
        raise SystemExit(f"submission does not validate: {rep['errors']}")
    key = json.loads((folder / "submission.json").read_text(encoding="utf-8"))["submission_id"]
    raw = out / "raw" / key
    raw.mkdir(parents=True, exist_ok=True)
    for r in core.read_jsonl(folder / "responses.jsonl"):
        r["model_key"] = key
        (raw / f"{r['task_id']}_{r['condition']}_r{r['run']}.json").write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"unpacked {len(list(raw.glob('*.json')))} responses to {raw}; next: python -m tegb judge {out}")
    return 0


def cmd_attach_reference(a: argparse.Namespace) -> int:
    """Add the reference judges' verdicts (run on the unpacked responses) to a submission folder."""
    folder, results = Path(a.submission), Path(a.results)
    sub = json.loads((folder / "submission.json").read_text(encoding="utf-8"))
    key = sub["submission_id"]
    responses, judgments, why = core.read_results(results, key)
    if judgments is None:
        raise SystemExit(f"reference judgments are not complete: {why}")
    submitted = {(r["task_id"], r["condition"], r["run"]): r["text"] for r in core.read_jsonl(folder / "responses.jsonl")}
    judged = {(r["task_id"], r["condition"], r["run"]): r["text"] for r in responses}
    if submitted != judged:
        raise SystemExit("the judged responses are not the submitted responses; unpack the submission again")
    core.write_jsonl(core.slim_judgments(judgments), folder / "judgments.jsonl")
    sub["hashes"]["judgments_sha256"] = core.sha256_bytes((folder / "judgments.jsonl").read_bytes())
    sub["metrics"]["reference"] = core.score(responses, judgments, core.load_tasks())["reference"]
    sub["reference_evaluation"] = {"evaluated_by": a.evaluated_by, "date": a.date or datetime.now(UTC).date().isoformat()}
    (folder / "submission.json").write_text(json.dumps(sub, indent=1, ensure_ascii=False) + chr(10), encoding="utf-8", newline=chr(10))
    rep = core.validate_submission(folder, allow_mock=a.allow_mock)
    print(f"reference evaluation attached to {folder} (evaluated by: {a.evaluated_by})")
    print("validation:", rep["result"], *rep["errors"], sep=chr(10) + "  ")
    return 0 if rep["result"] == "PASS" else 1


# ---- validate -----------------------------------------------------------------------------------
def cmd_validate(a: argparse.Namespace) -> int:
    folders = [Path(p) for p in a.paths] or sorted(p for p in (ROOT / "submissions" / BENCHMARK_VERSION).glob("*") if p.is_dir())
    worst = 0
    for f in folders:
        if not f.is_dir():
            print(f"FAIL  folder not found: {f.resolve()}")
            worst = 1
            continue
        rep = core.validate_submission(f, allow_mock=a.allow_mock)
        print(json.dumps(rep, indent=1))
        print(f"{rep['result']}  {f}" + (f"  (with {len(rep['warnings'])} warning(s): {'; '.join(rep['warnings'])})" if rep["warnings"] else ""))
        worst |= rep["result"] != "PASS"
    if not folders:
        print("no submissions to validate")
    return 1 if worst else 0


# ---- leaderboard (maintainers) ------------------------------------------------------------------
BASELINE_NAMES = {"eve-instruct-24b": "EVE-Instruct", "mistral-small-3.2-base": "Mistral Small 3.2", "claude-sonnet-5-5": "Claude Sonnet 5.5",
                  "gpt-6.1-terra": "GPT-6.1 Terra"}


def _fp(x) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def leaderboard_blocks(subs_root: Path) -> dict[str, str]:
    tasks = core.load_tasks()
    # official baseline, CORE detector score (derived from the frozen responses; the published results are untouched)
    rows = ["| Model | RAW | TEXT | STRUCTURED |", "|---|---:|---:|---:|"]
    for key, name in BASELINE_NAMES.items():
        responses, _, _ = core.read_results(core.FROZEN, key)
        c = core.aggregate(core.label_rows(responses, None, tasks), reference=False)["by_condition"]
        rows.append(f"| {name} | {_fp(c['RAW']['ucr'])} | {_fp(c['TEXT']['ucr'])} | {_fp(c['STRUCTURED']['ucr'])} |")
    blocks = {"baseline_core": "\n".join(rows)}
    subs = []
    for folder in sorted(p for p in subs_root.glob("*") if p.is_dir()):
        rep = core.validate_submission(folder)
        if rep["result"] != "PASS":
            raise SystemExit(f"submission {folder.name} does not validate: {rep['errors']}")
        subs.append(json.loads((folder / "submission.json").read_text(encoding="utf-8")))
    none = "No external submissions yet."

    def name(s: dict) -> str:
        flag = " †" if s["protocol"].get("deviations") else ""
        return f"[{s['model']['name']} {s['model']['version']}](submissions/{BENCHMARK_VERSION}/{s['submission_id']}/submission.json){flag}"

    ref = [s for s in subs if s["metrics"]["reference"]]
    if ref:
        lines = ["| Model | Submitter | Date | Judges run by | Condition | UCR ↓ | Constraint Violations ↓ | Observability Errors ↓ | Scope Errors ↓ | Factual Accuracy ↑ |",
                 "|---|---|---|---|---|---:|---:|---:|---:|---:|"]
        for s in sorted(ref, key=lambda s: s["metrics"]["reference"]["by_condition"]["RAW"]["ucr"]):
            for cond in ("RAW", "TEXT"):
                m = s["metrics"]["reference"]["by_condition"][cond]
                lines.append(f"| {name(s)} | {s['submitter']['name']} | {s['date']} | {s['reference_evaluation']['evaluated_by']} | {cond} | {_fp(m['ucr'])} | {_fp(m['constraint_violations'])} | "
                             f"{_fp(m['observability_errors'])} | {_fp(m['scope_errors'])} | {_fp(m['factual_accuracy'])} |")
        blocks["community_reference"] = "\n".join(lines)
    else:
        blocks["community_reference"] = none
    if subs:
        lines = ["| Model | Submitter | Date | RAW | TEXT | STRUCTURED | Reference evaluation |", "|---|---|---|---:|---:|---:|---|"]
        for s in sorted(subs, key=lambda s: s["submission_id"]):
            c = s["metrics"]["core"]["by_condition"]
            lines.append(f"| {name(s)} | {s['submitter']['name']} | {s['date']} | {_fp(c['RAW']['ucr'])} | {_fp(c['TEXT']['ucr'])} | "
                         f"{_fp(c['STRUCTURED']['ucr'])} | {'yes' if s['metrics']['reference'] else 'no'} |")
        blocks["community_core"] = "\n".join(lines)
    else:
        blocks["community_core"] = none
    return blocks


def cmd_leaderboard(a: argparse.Namespace) -> int:
    subs_root = Path(a.submissions) if a.submissions else ROOT / "submissions" / BENCHMARK_VERSION
    blocks = leaderboard_blocks(subs_root)
    out = Path(a.blocks_dir) if a.blocks_dir else ROOT / "analysis" / "blocks"
    stale = [k for k, v in blocks.items() if not (out / f"{k}.md").exists() or (out / f"{k}.md").read_text(encoding="utf-8").rstrip("\n") != v]
    if a.check:
        print("leaderboard blocks", "up to date" if not stale else f"STALE: {stale} (run `python -m tegb leaderboard`)")
        return 1 if stale else 0
    out.mkdir(parents=True, exist_ok=True)
    for k, v in blocks.items():
        (out / f"{k}.md").write_text(v + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {len(blocks)} blocks to {out}; now run: python analysis/docs_sync.py --render")
    return 0


def cmd_hashes(a: argparse.Namespace) -> int:
    th = core.task_hashes()
    path = ROOT / "dataset" / "task_hashes.json"
    text = json.dumps(th, indent=1) + "\n"
    if a.check:
        ok = path.exists() and path.read_text(encoding="utf-8") == text
        print("task hashes", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    path.write_text(text, encoding="utf-8", newline="\n")
    print("written", path)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tegb", description=f"TEGB {BENCHMARK_VERSION} tools {TOOLS_VERSION}")
    sp = ap.add_subparsers(dest="cmd", required=True)

    r = sp.add_parser("run", help="run your model on the 82 tasks x 3 conditions x 3 runs")
    r.add_argument("--adapter", required=True, choices=adapters.ADAPTERS)
    r.add_argument("--model", required=True, help="model name sent to the adapter")
    r.add_argument("--output", required=True, help="results directory (created)")
    r.add_argument("--model-key", help="folder name for this model (default: slug of --model)")
    r.add_argument("--base-url", help="openai-compatible: URL ending in /v1")
    r.add_argument("--api-key-env", help="NAME of the environment variable holding the API key (never the key itself)")
    r.add_argument("--command", help="command adapter: program to run per prompt")
    r.add_argument("--adapter-path", help="python adapter: file that defines generate()")
    r.add_argument("--max-tokens-param", choices=["max_tokens", "max_completion_tokens"])
    r.add_argument("--max-tokens", type=int, default=core.MAX_TOKENS, help="protocol value is 600; changing it is a declared deviation")
    r.add_argument("--workers", type=int, default=4, help="parallel calls (default 4); use 1 for an in-process or single-GPU model")
    r.add_argument("--limit", type=int, help="first N tasks only (smoke test)")
    r.add_argument("--task-ids", help="comma-separated task ids (smoke test)")
    r.set_defaults(fn=cmd_run)

    j = sp.add_parser("judge", help="optional reference evaluation with the two reference judges (your keys, your cost)")
    j.add_argument("results")
    j.add_argument("--model-key")
    j.add_argument("--anthropic-key-env", default="ANTHROPIC_API_KEY")
    j.add_argument("--openai-key-env", default="OPENAI_API_KEY")
    j.add_argument("--budget-usd", type=float, default=15.0)
    j.add_argument("--workers", type=int, default=6)
    j.add_argument("--dry-run", action="store_true")
    j.add_argument("--retry-unparsed", action="store_true")
    j.set_defaults(fn=cmd_judge)

    s = sp.add_parser("score", help="core detector score, plus the reference score when judgments exist")
    s.add_argument("results")
    s.add_argument("--model-key")
    s.add_argument("--out", help="where to write score_<key>.json (default: <results>/scores)")
    s.set_defaults(fn=cmd_score)

    u = sp.add_parser("submit", help="package a complete run as a leaderboard submission")
    u.add_argument("results")
    u.add_argument("--model-key")
    u.add_argument("--model-name", required=True)
    u.add_argument("--model-version", required=True, help="exact version, checkpoint or revision")
    u.add_argument("--provider", required=True, help="who serves or publishes the model")
    u.add_argument("--submitter", required=True, help="person or team (public)")
    u.add_argument("--contact", help="public contact, for example a GitHub handle or URL (optional)")
    u.add_argument("--affiliation")
    u.add_argument("--model-url")
    u.add_argument("--weights", choices=["open", "closed", "unknown"], default="unknown")
    u.add_argument("--training-cutoff", help="YYYY-MM if known")
    u.add_argument("--contamination", required=True, choices=["no-known-exposure", "possible-exposure", "known-exposure", "unknown"],
                   help="your best knowledge of whether the model saw TEGB during training")
    u.add_argument("--contamination-notes")
    u.add_argument("--tuned-on-tegb", action="store_true", help="set if prompts, fine-tuning or selection used TEGB tasks")
    u.add_argument("--i-can-share-outputs", action="store_true", help="confirm you may publish the raw model outputs")
    u.add_argument("--decoding-notes", help="serving stack, quantization, sampling details")
    u.add_argument("--deviation", action="append", help="describe a protocol deviation not detected automatically (repeatable)")
    u.add_argument("--notes")
    u.add_argument("--submission-id", help="folder name; default is the model name in lowercase with hyphens. Include the version to keep several versions")
    u.add_argument("--date")
    u.add_argument("--out", help=f"folder (default: submissions/{BENCHMARK_VERSION}/<id>)")
    u.add_argument("--allow-mock", action="store_true", help=argparse.SUPPRESS)
    u.set_defaults(fn=cmd_submit)

    v = sp.add_parser("validate", help="validate submission folders: PASS / FAIL")
    v.add_argument("paths", nargs="*")
    v.add_argument("--allow-mock", action="store_true", help=argparse.SUPPRESS)
    v.set_defaults(fn=cmd_validate)

    k = sp.add_parser("unpack", help="maintainers: rebuild a results directory from a submission, to run the reference judges on it")
    k.add_argument("submission")
    k.add_argument("--output", required=True)
    k.add_argument("--allow-mock", action="store_true", help=argparse.SUPPRESS)
    k.set_defaults(fn=cmd_unpack)

    t = sp.add_parser("attach-reference", help="maintainers: add reference judgments to a submission that had the core score only")
    t.add_argument("submission")
    t.add_argument("--results", required=True, help="results directory produced by `tegb unpack` and `tegb judge`")
    t.add_argument("--evaluated-by", default="TerraUY (TEGB Early Evaluation Program)")
    t.add_argument("--date")
    t.add_argument("--allow-mock", action="store_true", help=argparse.SUPPRESS)
    t.set_defaults(fn=cmd_attach_reference)

    lb = sp.add_parser("leaderboard", help="maintainers: regenerate the community leaderboard blocks")
    lb.add_argument("--check", action="store_true")
    lb.add_argument("--submissions")
    lb.add_argument("--blocks-dir")
    lb.set_defaults(fn=cmd_leaderboard)

    h = sp.add_parser("hashes", help="write or check dataset/task_hashes.json")
    h.add_argument("--check", action="store_true")
    h.set_defaults(fn=cmd_hashes)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
