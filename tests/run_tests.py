"""TEGB v0.1 local test suite (offline, no API keys). Works with or without pytest.

    python tests/run_tests.py            # quick checks
    python tests/run_tests.py --full     # + full reproduction (about 1 minute)
    python -m pytest tests -q            # same quick checks via pytest
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))


def _tasks():
    return [json.loads(x) for x in (ROOT / "dataset" / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]


def test_task_counts():
    ts = _tasks()
    assert len(ts) == 82
    assert sum(1 for t in ts if t["category"] == "K_control") == 8
    assert len({t["task_id"] for t in ts}) == 82


def test_tasks_frozen_hash():
    am = json.loads((ROOT / "results" / "baseline" / "preregistration" / "PREREGISTRATION.amendment-2.json").read_text(encoding="utf-8"))
    assert hashlib.sha256((ROOT / "dataset" / "tasks.jsonl").read_bytes()).hexdigest() == am["change"]["public_tasks_sha256"]


def test_schema_validation():
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
    except ImportError:
        print("  (skipped: jsonschema not installed)")
        return
    ts = json.loads((ROOT / "dataset" / "task_schema.json").read_text(encoding="utf-8"))
    eu = json.loads((ROOT / "dataset" / "evidence_unit.schema.json").read_text(encoding="utf-8"))
    reg = Registry().with_resource(urljoin(ts["$id"], "evidence_unit.schema.json"), Resource.from_contents(eu))
    v = Draft202012Validator(ts, registry=reg)
    errs = [(t["task_id"], e.message) for t in _tasks() for e in v.iter_errors(t)]
    assert not errs, errs[:5]


def test_condition_equivalence():
    r = subprocess.run([sys.executable, str(ROOT / "evaluation" / "check_condition_equivalence.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-1000:]


def test_published_prompts_match_renderer():
    from render import build_prompt
    tasks = {t["task_id"]: t for t in _tasks()}
    for d, c in (("raw", "A"), ("text", "B"), ("structured", "C")):
        for line in (ROOT / "conditions" / d / "prompts.jsonl").read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            s, u = build_prompt(tasks[r["task_id"]], c)
            assert (s, u) == (r["system"], r["user"]), (d, r["task_id"])


def test_detector_phrases():
    from detect import classify
    cases = [("The evidence does not establish deforestation.", "negated"), ("This is deforestation.", "asserted"),
             ("It may be deforestation.", "hedged")]
    pat = [r"deforest"]
    for text, want in cases:
        got = classify(text, pat)
        assert got == want, (text, got, want)


def test_generated_tables_consistent_with_summary():
    T = json.loads((ROOT / "results" / "baseline" / "tables.json").read_text(encoding="utf-8"))
    S = json.loads((ROOT / "results" / "baseline" / "summary_main.json").read_text(encoding="utf-8"))
    for c, name in (("A", "RAW"), ("B", "TEXT"), ("C", "STRUCTURED")):
        assert abs(T["pooled"][name]["uc"] - round(100 * S["rates"]["POOLED"][c]["uc"], 1)) < 1e-9
    assert T["counts"]["agent_responses"] == 2952 and T["counts"]["judgments"] == 5904
    assert S["verdict"] in ("PASS", "FAIL", "INCONCLUSIVE")


def test_docs_consistency():
    r = subprocess.run([sys.executable, str(ROOT / "analysis" / "docs_sync.py"), "--check"], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout[-3000:]


def test_privacy_security_scan():
    r = subprocess.run([sys.executable, str(ROOT / "audit" / "scan.py")], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout[-2000:]


def main() -> int:
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL {t.__name__}: {str(e)[:500]}")
    if "--full" in sys.argv:
        r = subprocess.run([sys.executable, str(ROOT / "analysis" / "reproduce.py")], capture_output=True, text=True)
        ok = r.returncode == 0
        failed += 0 if ok else 1
        print(("PASS" if ok else "FAIL"), "full reproduction")
    print(f"{len(tests) - failed if '--full' not in sys.argv else len(tests) + 1 - failed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
