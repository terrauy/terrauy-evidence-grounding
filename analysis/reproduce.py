"""Reproduce every published TEGB v0.1 baseline number from the frozen raw responses and judgments. No API calls.

    python analysis/reproduce.py

Checks (all must PASS):
  1. dataset/tasks.jsonl SHA-256 == the public-variant hash recorded in preregistration amendment 2 (the tasks the models saw).
  2. Every one of the 2,952 responses was produced from exactly the prompt published in conditions/*/prompts.jsonl
     (system and user SHA-256 recorded at run time == SHA-256 of the regenerated prompt).
  3. TEXT/STRUCTURED equivalence (evaluation/check_condition_equivalence.py).
  4. Re-running the preregistered evaluation (harness/evaluate.py), the exploratory analyses (harness/analysis_extra.py)
     into results/reproduction/ yields outputs identical
     to the frozen ones in results/baseline/.
Writes results/reproduction/REPRODUCTION_REPORT.json.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results" / "baseline"
REPRO = ROOT / "results" / "reproduction"
sys.path.insert(0, str(ROOT / "harness"))
from render import build_prompt  # noqa: E402


def sha_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def run(script: str, *args: str) -> None:
    env = {**os.environ, "TEGB_RESULTS_DIR": str(BASE), "TEGB_OUT_DIR": str(REPRO), "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, str(ROOT / script), *args], cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise SystemExit(f"{script} failed:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    checks = {}
    lock = load_json(BASE / "preregistration" / "PREREGISTRATION.amendment-2.json")["change"]["public_tasks_sha256"]
    checks["public_tasks_sha256_matches_amendment_2"] = hashlib.sha256((ROOT / "dataset" / "tasks.jsonl").read_bytes()).hexdigest() == lock

    tasks = {t["task_id"]: t for t in map(json.loads, (ROOT / "dataset" / "tasks.jsonl").read_text(encoding="utf-8").splitlines())}
    published = {}
    for d in ("raw", "text", "structured"):
        for line in (ROOT / "conditions" / d / "prompts.jsonl").read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            published[(r["task_id"], r["condition"])] = r
    n, bad = 0, []
    for p in sorted((BASE / "raw").glob("*/*.json")):
        rec = load_json(p)
        system, user = build_prompt(tasks[rec["task_id"]], rec["condition"])
        pub = published[(rec["task_id"], rec["condition"])]
        ok = (sha_text(system) == rec["system_sha256"] == pub["system_sha256"]) and (sha_text(user) == rec["user_sha256"] == pub["user_sha256"])
        n += 1
        if not ok:
            bad.append(str(p.relative_to(ROOT)))
    checks["responses_checked"] = n
    checks["all_response_prompts_match_published_prompts"] = n == 2952 and not bad
    eq = subprocess.run([sys.executable, str(ROOT / "evaluation" / "check_condition_equivalence.py")], cwd=ROOT, capture_output=True, text=True)
    checks["text_structured_equivalence"] = eq.returncode == 0

    REPRO.mkdir(parents=True, exist_ok=True)
    (REPRO / "blind_review").mkdir(exist_ok=True)
    run("harness/evaluate.py", "--config", "harness/config.baseline.json", "--tag", "main", "--review-n", "120")
    run("harness/analysis_extra.py", "--tag", "main")
    pairs = {"summary_main.json": "summary_main.json", "extra_main.json": "extra_main.json",
             "blind_review/blind_key_main.json": "blind_review/blind_key_main.json"}
    for new, old in pairs.items():
        checks[f"identical:{old}"] = load_json(REPRO / new) == load_json(BASE / old)
    labels_new = (REPRO / "labels_main.jsonl").read_text(encoding="utf-8").splitlines()
    labels_old = (BASE / "labels_main.jsonl").read_text(encoding="utf-8").splitlines()
    checks["identical:labels_main.jsonl"] = [json.loads(x) for x in labels_new] == [json.loads(x) for x in labels_old]
    sample_new = (REPRO / "blind_review" / "blind_review_main.csv").read_text(encoding="utf-8").splitlines()
    sample_old = (BASE / "blind_review" / "blind_review_main.csv").read_text(encoding="utf-8").splitlines()
    checks["identical:blind_review_sample.csv"] = sample_new == sample_old
    result = "PASS" if all(v for k, v in checks.items() if k != "responses_checked") else "FAIL"
    report = {"result": result, "checks": checks, "mismatched_prompt_files": bad[:20]}
    (REPRO / "REPRODUCTION_REPORT.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
