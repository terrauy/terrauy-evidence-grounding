"""Benchmark constants, hashes, scoring, submission packaging and validation (standard library only).

Two scores exist and must not be confused:

* CORE detector score: `harness/detect.py` only (public regular-expression rules). Free, deterministic and
  reproducible by anyone, but a weak instrument: it cannot see stances, invented conclusions or over-hedging.
  It is a screening and pipeline check, NOT comparable with the published UCR.
* REFERENCE evaluation: the preregistered v0.1 label (two blind LLM judges `judge-v2` plus the detector, merged
  by `harness/evaluate.py`). This is the instrument of the official baseline and of the leaderboard.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

from tegb import BENCHMARK_VERSION, SUBMISSION_SCHEMA, TOOLS_VERSION

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))

CONDITIONS = {"A": "RAW", "B": "TEXT", "C": "STRUCTURED"}
COND_DIRS = {"A": "raw", "B": "text", "C": "structured"}
RUN_TEMPERATURES = [0.0, 0.7, 0.7]  # run 0, 1, 2 of the v0.1 protocol
MAX_TOKENS = 600
REFERENCE_JUDGES = {"judge-claude-sonnet-5-5": "claude-sonnet-5-5", "judge-gpt-6.1-terra": "gpt-6.1-terra"}
FROZEN = ROOT / "results" / "baseline"
RATE_KEYS = ("ucr", "constraint_violations", "observability_errors", "scope_errors", "factual_accuracy",
             "source_attribution_accuracy", "version_compliance", "appropriate_abstention")
SECRET_PATTERNS = [r"sk-[A-Za-z0-9_\-]{16,}", r"hf_[A-Za-z0-9]{20,}", r"gh[pousr]_[A-Za-z0-9]{20,}", r"AKIA[0-9A-Z]{16}",
                   r"xox[baprs]-[A-Za-z0-9\-]{10,}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}",
                   r"AIza[0-9A-Za-z_\-]{30,}"]
SUBMISSION_FILES = {"submission.json", "responses.jsonl", "judgments.jsonl", "README.md"}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_text(s: str) -> str:
    return sha256_bytes(s.encode("utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        return [json.loads(x) for x in fh if x.strip()]


def write_jsonl(rows: list[dict], path: Path) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8", newline="\n")


def load_tasks() -> dict[str, dict]:
    return {t["task_id"]: t for t in read_jsonl(ROOT / "dataset" / "tasks.jsonl")}


def load_prompts() -> dict[tuple[str, str], dict]:
    out = {}
    for c, d in COND_DIRS.items():
        for r in read_jsonl(ROOT / "conditions" / d / "prompts.jsonl"):
            out[(r["task_id"], c)] = r
    return out


def task_hashes() -> dict:
    """Identity of the benchmark inputs: file hashes plus one hash per task line and per prompt."""
    lines = (ROOT / "dataset" / "tasks.jsonl").read_text(encoding="utf-8").splitlines()
    prompts = load_prompts()
    return {
        "benchmark_version": BENCHMARK_VERSION,
        "tasks_file_sha256": sha256_bytes((ROOT / "dataset" / "tasks.jsonl").read_bytes()),
        "prompt_files_sha256": {CONDITIONS[c]: sha256_bytes((ROOT / "conditions" / d / "prompts.jsonl").read_bytes()) for c, d in COND_DIRS.items()},
        "system_prompt_sha256": sorted({sha256_text(p["system"]) for p in prompts.values()}),
        "tasks": {json.loads(x)["task_id"]: sha256_text(x) for x in lines if x.strip()},
        "user_prompts": {f"{t}|{CONDITIONS[c]}": sha256_text(p["user"]) for (t, c), p in sorted(prompts.items())},
    }


def expected_keys(tasks: dict) -> set[tuple[str, str, int]]:
    return {(t, c, r) for t in tasks for c in CONDITIONS for r in range(len(RUN_TEMPERATURES))}


# ---- scoring ------------------------------------------------------------------------------------
def _rate(xs):
    xs = [x for x in xs if x is not None]
    return None if not xs else round(sum(bool(x) for x in xs) / len(xs), 6)



def label_rows(responses: list[dict], judgments: dict | None, tasks: dict) -> list[dict]:
    """One label per response. judgments: {(task, cond, run): [judge_record, judge_record]} or None for CORE."""
    from evaluate import label

    rows = []
    for r in responses:
        js = [] if judgments is None else judgments[(r["task_id"], r["condition"], r["run"])]
        rows.append(label(tasks[r["task_id"]], {"text": r["text"], "condition": r["condition"], "model_key": r.get("model_key", "model"), "run": r["run"]}, js))
    return rows


def aggregate(rows: list[dict], reference: bool) -> dict:
    by_cond = {}
    for c, name in CONDITIONS.items():
        sub = [r for r in rows if r["condition"] == c]
        m = {"n": len(sub), "ucr": _rate([r["uc"] for r in sub]), "constraint_violations": _rate([r["cv"] for r in sub]),
             "scope_errors": _rate([not r["scope_ok"] for r in sub if r["scope_ok"] is not None]),
             "source_attribution_accuracy": _rate([r["source_ok"] for r in sub]), "version_compliance": _rate([r["version_ok"] for r in sub]),
             "observability_errors": _rate([r["ocr"] for r in sub]) if reference else None,
             "factual_accuracy": _rate([r["factual_ok"] for r in sub]) if reference else None,
             "appropriate_abstention": _rate([r["abstention_ok"] for r in sub]) if reference else None}
        by_cond[name] = m
    cats = sorted({r["category"] for r in rows})
    by_cat = {cat: {name: _rate([r["uc"] for r in rows if r["category"] == cat and r["condition"] == c]) for c, name in CONDITIONS.items()} for cat in cats}
    return {"by_condition": by_cond, "ucr_by_category": by_cat}


def judge_agreement(rows: list[dict]) -> float | None:
    from evaluate import kappa

    return kappa([r["judge_uc"][0] if len(r["judge_uc"]) > 0 else None for r in rows], [r["judge_uc"][1] if len(r["judge_uc"]) > 1 else None for r in rows])


def score(responses: list[dict], judgments: dict | None, tasks: dict) -> dict:
    core = aggregate(label_rows(responses, None, tasks), reference=False)
    core["instrument"] = "detect-v1 (deterministic regular-expression detector); screening only, not comparable with reference UCR"
    out = {"core": core, "reference": None}
    if judgments is not None:
        rows = label_rows(responses, judgments, tasks)
        ref = aggregate(rows, reference=True)
        ref["instrument"] = "evaluate-v1: majority of two blind LLM judges (judge-v2) and detect-v1"
        ref["judge_agreement_kappa_uc"] = judge_agreement(rows)
        out["reference"] = ref
    return out


def response_stats(responses: list[dict]) -> dict:
    return {"n_responses": len(responses), "empty_responses": sum(1 for r in responses if not (r.get("text") or "").strip()),
            "truncated_responses": sum(1 for r in responses if r.get("stop_reason") in ("max_tokens", "length")),
            "models_returned": sorted({str(r.get("model_returned")) for r in responses})}


# ---- reading a results directory (same layout as the v0.1 harness) -------------------------------
def read_results(results_dir: Path, model_key: str) -> tuple[list[dict], dict | None, str | None]:
    """Returns (responses, judgments or None, reason why judgments are None)."""
    raw = sorted((results_dir / "raw" / model_key).glob("*.json"))
    responses = [json.loads(p.read_text(encoding="utf-8")) for p in raw]
    judgments, missing, wrong_model = {}, 0, 0
    for p, r in zip(raw, responses):
        js = []
        for jk in REFERENCE_JUDGES:
            jp = results_dir / "judged" / jk / f"{model_key}__{p.name}"
            j = json.loads(jp.read_text(encoding="utf-8")) if jp.exists() else None
            if not j or not j.get("parsed"):
                missing += 1
            elif not str(j.get("judge_model_returned") or "").startswith(REFERENCE_JUDGES[jk]):
                wrong_model += 1
            js.append(j)
        judgments[(r["task_id"], r["condition"], r["run"])] = js
    if not (results_dir / "judged").exists():
        return responses, None, "no judgments (run `tegb judge` for the reference evaluation)"
    if missing:
        return responses, None, f"{missing} judge verdicts missing or unparsed"
    if wrong_model:
        return responses, None, f"{wrong_model} verdicts were not produced by the reference judge models"
    return responses, judgments, None


# ---- submission ---------------------------------------------------------------------------------
RESP_FIELDS = ("task_id", "condition", "run", "text", "model_returned", "stop_reason", "temperature", "max_tokens",
               "system_sha256", "user_sha256", "created_at", "input_tokens", "output_tokens")


def slim_responses(responses: list[dict]) -> list[dict]:
    rows = [{k: r.get(k) for k in RESP_FIELDS} for r in responses]
    return sorted(rows, key=lambda r: (r["task_id"], r["condition"], r["run"]))


def slim_judgments(judgments: dict) -> list[dict]:
    rows = []
    for (t, c, run), js in sorted(judgments.items()):
        for j in js:
            rows.append({"task_id": t, "condition": c, "run": run, "judge": j["judge"], "judge_model_returned": j.get("judge_model_returned"),
                         "judge_version": j.get("judge_version"), "prompt_sha256": j.get("prompt_sha256"), "parsed": j["parsed"]})
    return rows


def judgments_from_rows(rows: list[dict]) -> dict:
    out: dict = {}
    order = list(REFERENCE_JUDGES)
    for j in sorted(rows, key=lambda j: order.index(j["judge"]) if j["judge"] in order else 99):
        out.setdefault((j["task_id"], j["condition"], j["run"]), []).append(j)
    return out


def protocol_of(responses: list[dict]) -> dict:
    temps = {}
    for r in responses:
        temps.setdefault(r["run"], set()).add(r.get("temperature"))
    return {"runs": len(temps), "temperatures_by_run": {str(k): sorted(v, key=lambda x: (x is None, x)) for k, v in sorted(temps.items())},
            "max_tokens": sorted({r.get("max_tokens") for r in responses}), "prompt_source": "conditions/*/prompts.jsonl (unchanged)"}


def protocol_deviations(responses: list[dict]) -> list[str]:
    dev = []
    if {r.get("max_tokens") for r in responses} != {MAX_TOKENS}:
        dev.append(f"max_tokens differs from {MAX_TOKENS}")
    for i, t in enumerate(RUN_TEMPERATURES):
        seen = {r.get("temperature") for r in responses if r["run"] == i}
        if seen and seen != {t}:
            dev.append(f"run {i}: temperature {sorted(seen, key=str)} instead of {t} (None = provider default sampling)")
    return dev


def validate_submission(folder: Path, allow_mock: bool = False) -> dict:
    """Checks a submission folder against the frozen benchmark. Returns {"result": "PASS"|"FAIL", "errors", "warnings"}."""
    errors, warnings = [], []
    info: dict = {"folder": folder.as_posix()}

    def done():
        return {"result": "PASS" if not errors else "FAIL", "errors": errors, "warnings": warnings, **info}

    sj = folder / "submission.json"
    if not sj.is_file() or not (folder / "responses.jsonl").is_file():
        errors.append("submission.json and responses.jsonl are required")
        return done()
    extra = {p.name for p in folder.iterdir()} - SUBMISSION_FILES
    if extra:
        errors.append(f"unexpected files: {sorted(extra)}")
    for p in folder.iterdir():
        if p.is_file():
            if p.stat().st_size > 12_000_000:
                errors.append(f"{p.name} is larger than 12 MB")
            text = p.read_text(encoding="utf-8", errors="replace")
            if any(re.search(pat, text) for pat in SECRET_PATTERNS):
                errors.append(f"{p.name} contains something that looks like a credential")
    try:
        sub = json.loads(sj.read_text(encoding="utf-8"))
        responses = read_jsonl(folder / "responses.jsonl")
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        errors.append(f"unreadable JSON: {e}")
        return done()

    # required metadata
    def need(path: str, kind=str, nonempty=True):
        cur = sub
        for k in path.split("."):
            cur = cur.get(k) if isinstance(cur, dict) else None
        if cur is None or not isinstance(cur, kind) or (nonempty and kind is str and not cur.strip()):
            errors.append(f"missing or invalid field: {path}")
        return cur

    if sub.get("schema") != SUBMISSION_SCHEMA:
        errors.append(f"schema must be {SUBMISSION_SCHEMA}")
    if sub.get("benchmark_version") != BENCHMARK_VERSION:
        errors.append(f"benchmark_version must be {BENCHMARK_VERSION} (scores of different versions are never mixed)")
    for f in ("submission_id", "date", "model.name", "model.version", "model.provider", "submitter.name", "run.adapter", "run.tools_version",
              "declarations.contamination"):
        need(f)
    need("declarations.rights_to_share_outputs", bool)
    need("declarations.tuned_on_tegb", bool)
    need("protocol", dict)
    need("hashes", dict)
    need("metrics", dict)
    if errors:
        return done()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", sub["date"]):
        errors.append("date must be YYYY-MM-DD")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,62}", sub["submission_id"]) or sub["submission_id"] != folder.name:
        errors.append("submission_id must be lowercase [a-z0-9._-] and equal to the folder name")
    if folder.parent.name != BENCHMARK_VERSION and folder.parent.parent.name == "submissions":
        errors.append(f"folder must live under submissions/{BENCHMARK_VERSION}/")
    if sub["declarations"]["contamination"] not in ("no-known-exposure", "possible-exposure", "known-exposure", "unknown"):
        errors.append("declarations.contamination must be one of: no-known-exposure, possible-exposure, known-exposure, unknown")
    if sub["declarations"]["rights_to_share_outputs"] is not True:
        errors.append("declarations.rights_to_share_outputs must be true: the raw outputs are published with the submission")
    if sub["run"]["adapter"] == "mock" and not allow_mock:
        errors.append("the mock adapter is for pipeline tests only and is never accepted")

    # benchmark identity
    th = task_hashes()
    if sub["hashes"].get("tasks_file_sha256") != th["tasks_file_sha256"]:
        errors.append("hashes.tasks_file_sha256 does not match dataset/tasks.jsonl of this benchmark version")
    if sub["hashes"].get("prompt_files_sha256") != th["prompt_files_sha256"]:
        errors.append("hashes.prompt_files_sha256 does not match conditions/*/prompts.jsonl")
    if sub["hashes"].get("responses_sha256") != sha256_bytes((folder / "responses.jsonl").read_bytes()):
        errors.append("hashes.responses_sha256 does not match responses.jsonl")

    # completeness and prompt identity
    tasks, prompts = load_tasks(), load_prompts()
    want = expected_keys(tasks)
    got = [(r.get("task_id"), r.get("condition"), r.get("run")) for r in responses]
    if len(got) != len(set(got)):
        errors.append("duplicate responses")
    if set(got) != want:
        errors.append(f"responses must cover all {len(want)} task x condition x run cells: {len(want - set(got))} missing, {len(set(got) - want)} unexpected")
        return done()
    bad_prompt = [k for k, r in zip(got, responses) if r.get("user_sha256") != sha256_text(prompts[(k[0], k[1])]["user"])
                  or r.get("system_sha256") != sha256_text(prompts[(k[0], k[1])]["system"])]
    if bad_prompt:
        errors.append(f"{len(bad_prompt)} responses were not produced from the published prompts (prompt hash mismatch), e.g. {bad_prompt[0]}")
    if any(not isinstance(r.get("text"), str) for r in responses):
        errors.append("every response needs a string 'text'")
        return done()
    stats = response_stats(responses)
    info["stats"] = stats
    if stats["empty_responses"] > 0.05 * len(responses):
        errors.append(f"{stats['empty_responses']} empty responses (more than 5%)")
    elif stats["empty_responses"]:
        warnings.append(f"{stats['empty_responses']} empty responses")
    dev = protocol_deviations(responses)
    declared = sub["protocol"].get("deviations") or []
    if dev and not declared:
        errors.append(f"undeclared protocol deviations: {dev}")
    if dev or declared:
        warnings.append(f"non-standard protocol: {declared or dev}")

    # judgments (optional): must be the reference judges, complete, and tied to the responses
    judgments = None
    if (folder / "judgments.jsonl").is_file():
        from judge import judge_prompt

        jrows = read_jsonl(folder / "judgments.jsonl")
        if sub["hashes"].get("judgments_sha256") != sha256_bytes((folder / "judgments.jsonl").read_bytes()):
            errors.append("hashes.judgments_sha256 does not match judgments.jsonl")
        text_of = {k: r["text"] for k, r in zip(got, responses)}
        seen = {}
        for j in jrows:
            k = (j.get("task_id"), j.get("condition"), j.get("run"))
            seen.setdefault(k, set()).add(j.get("judge"))
            if j.get("judge") not in REFERENCE_JUDGES:
                errors.append(f"unknown judge '{j.get('judge')}': the reference evaluation uses {sorted(REFERENCE_JUDGES)}")
                break
            if not str(j.get("judge_model_returned") or "").startswith(REFERENCE_JUDGES[j["judge"]]):
                errors.append(f"judge {j['judge']} was answered by '{j.get('judge_model_returned')}', not the reference model")
                break
            if not isinstance(j.get("parsed"), dict):
                errors.append("a judgment has no parsed verdict")
                break
            if k in text_of and j.get("prompt_sha256") != sha256_text(judge_prompt(tasks[k[0]], text_of[k])):
                errors.append(f"judgment {k} was not produced from the submitted response (judge prompt hash mismatch)")
                break
        if not errors and (set(seen) != want or any(v != set(REFERENCE_JUDGES) for v in seen.values())):
            errors.append("judgments.jsonl must contain both reference judges for every response")
        who = (sub.get("reference_evaluation") or {}).get("evaluated_by")
        if not isinstance(who, str) or not who.strip():
            errors.append("reference_evaluation.evaluated_by is required when judgments.jsonl is present (who ran the judges)")
        if not errors:
            judgments = judgments_from_rows(jrows)
    elif sub["metrics"].get("reference") is not None:
        errors.append("metrics.reference is reported but judgments.jsonl is missing")
    if errors:
        return done()

    # metric recomputation
    for r in responses:
        r.setdefault("model_key", sub["submission_id"])
    recomputed = score(responses, judgments, tasks)
    for track in ("core", "reference"):
        mine, theirs = recomputed[track], sub["metrics"].get(track)
        if mine is None and theirs is None:
            continue
        if (mine is None) != (theirs is None):
            errors.append(f"metrics.{track}: reported and recomputed presence differ")
            continue
        for cond, vals in mine["by_condition"].items():
            rep = (theirs.get("by_condition") or {}).get(cond) or {}
            if rep.get("n") != vals["n"] or vals["n"] != len(tasks) * len(RUN_TEMPERATURES):
                errors.append(f"metrics.{track}.{cond}.n is not {len(tasks) * len(RUN_TEMPERATURES)}")
            for k in RATE_KEYS:
                a, b = vals.get(k), rep.get(k)
                if b is not None and not (isinstance(b, (int, float)) and 0 <= b <= 1):
                    errors.append(f"metrics.{track}.{cond}.{k} = {b} is not a rate in [0, 1]")
                elif (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-5):
                    errors.append(f"metrics.{track}.{cond}.{k}: reported {b}, recomputed {a}")
        if mine["ucr_by_category"] != theirs.get("ucr_by_category"):
            errors.append(f"metrics.{track}.ucr_by_category does not match the recomputed values")
    info["recomputed"] = {t: (None if recomputed[t] is None else {c: v["ucr"] for c, v in recomputed[t]["by_condition"].items()}) for t in ("core", "reference")}
    info["tools_version"] = TOOLS_VERSION
    return done()
