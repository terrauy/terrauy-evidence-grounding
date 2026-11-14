"""check_condition_equivalence: verify that TEXT (B) and STRUCTURED (C) carry the same facts and constraints.

    python evaluation/check_condition_equivalence.py [--verbose]

For every task, every leaf value of the canonical evidence units (what C shows as JSON) must appear in the B prose,
after the same normalisation the renderer applies (enum statuses -> words, numbers formatted identically).
Structure-only tokens are excluded by design: the machine-readable `does_not_establish[].code` values and
`claim.type` are the experimental manipulation (structure), not information.
Also checks that RAW (A) omits the semantic layer it is defined to omit (assessment status, supports,
does_not_establish). Exit code 1 on any mismatch.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))
from render import build_prompt, check_equivalence  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    tasks = [json.loads(x) for x in (ROOT / "dataset" / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    bad, raw_leaks = {}, {}
    for t in tasks:
        _, user_b = build_prompt(t, "B")
        missing = check_equivalence(t["units"], user_b)
        if missing:
            bad[t["task_id"]] = missing
        _, user_a = build_prompt(t, "A")
        leaks = [k for k in ('"does_not_establish"', '"supports"', '"assessment"', "does not establish") if k in user_a]
        if leaks:
            raw_leaks[t["task_id"]] = leaks
    report = {"tasks": len(tasks), "text_vs_structured_mismatches": len(bad), "raw_semantic_leaks": len(raw_leaks),
              "result": "PASS" if not bad and not raw_leaks else "FAIL"}
    if args.verbose or bad or raw_leaks:
        report["details"] = {"mismatches": bad, "raw_leaks": raw_leaks}
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
