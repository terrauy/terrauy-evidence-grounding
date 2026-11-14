"""Derive the public dataset files from the frozen tasks (dataset/tasks.jsonl). Deterministic; no network.

    python dataset/build_public_files.py

Writes:
  dataset/fact_sheets.jsonl          condition-neutral fact sheet per task (every leaf of the canonical evidence units)
  dataset/provenance.jsonl           provenance class per task (real_derived / synthetic_derived)
  conditions/{raw,text,structured}/prompts.jsonl   exact system + user prompt per task and condition, with SHA-256
tasks.jsonl itself is never modified (its SHA-256 must equal the preregistration lock).
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))
from render import PROMPT_VERSION, RENDER_VERSION, build_prompt  # noqa: E402

COND_DIR = {"A": "raw", "B": "text", "C": "structured"}


def leaves(x, path=""):
    out = []
    if isinstance(x, dict):
        for k, v in x.items():
            if k == "code" or (k == "type" and path.endswith("claim")):
                continue
            out += leaves(v, f"{path}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            out += leaves(v, f"{path}[{i}]")
    elif x is not None:
        out.append((path, x))
    return out


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def main() -> int:
    tasks = [json.loads(x) for x in (ROOT / "dataset" / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    synth_area = set(json.loads((ROOT / "dataset" / "area_substitution.json").read_text(encoding="utf-8"))["task_ids"])
    fs, prov = [], []
    prompts = {c: [] for c in COND_DIR}
    for t in tasks:
        fs.append({"task_id": t["task_id"], "fact_sheet": [{"unit": i, "facts": [{"path": p, "value": v} for p, v in leaves(u)]}
                                                           for i, u in enumerate(t["units"], 1)]})
        prov.append({"task_id": t["task_id"], "case": t["case"],
                     "provenance": "synthetic_derived" if (t.get("synthetic_derived") or t["task_id"] in synth_area) else "real_derived",
                     "note": "; ".join(n for n in [
                         "evidence structure and statuses from a real TerraUY-owned assessment" if t["task_id"] in synth_area else
                         "evidence values extracted read-only from a TerraUY-owned monitored asset (no area values present)",
                         "area values >= 2 ha replaced by synthetic equivalents (thresholds preserved; mapping not published)" if t["task_id"] in synth_area else "",
                         "evidence-version scenario constructed from the real case" if t.get("synthetic_derived") else "",
                         "question and answer key authored"] if n)})
        for c in COND_DIR:
            system, user = build_prompt(t, c)
            prompts[c].append({"task_id": t["task_id"], "condition": c, "prompt_version": PROMPT_VERSION, "render_version": RENDER_VERSION,
                               "system": system, "user": user, "system_sha256": sha(system), "user_sha256": sha(user)})

    def dump(path: Path, rows: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n").encode("utf-8"))

    dump(ROOT / "dataset" / "fact_sheets.jsonl", fs)
    dump(ROOT / "dataset" / "provenance.jsonl", prov)
    for c, d in COND_DIR.items():
        dump(ROOT / "conditions" / d / "prompts.jsonl", prompts[c])
    print(f"{len(tasks)} tasks; fact sheets, provenance and 3 x {len(tasks)} prompts written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
