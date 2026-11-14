"""Keep every published number in the docs tied to the generated tables (Gate 4) and lint for over-claiming (Gate 5).

    python analysis/docs_sync.py --render   # fill <!-- TEGB:block --> ... <!-- /TEGB:block --> regions from analysis/blocks/
    python analysis/docs_sync.py --check    # verify blocks + prose numbers + restraint lint; exit 1 on failure

Prose check: every decimal percentage ("17.4%"), percentage-point figure ("-31.0 pp") and kappa ("κ = 0.709") written
outside the generated blocks must equal a value present in results/baseline/tables.json (after rounding to the shown
precision). Integers are not checked (design constants such as "30 %" or "150 words").
Restraint lint: phrases that would overstate the evidence are rejected unless the sentence negates them.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCKS = ROOT / "analysis" / "blocks"
DOCS = ["README.md", "BENCHMARK_CARD.md", "METHODOLOGY.md", "DATASET_CARD.md", "LIMITATIONS.md", "LEADERBOARD.md", "FUTURE_TRACKS.md",
        "PRIVACY_AUDIT.md", "SECURITY_AUDIT.md", "LICENSING.md", "paper/TECHNICAL_REPORT.md", "dataset/README.md", "results/baseline/README.md",
        "MODEL_OUTPUTS_NOTICE.md", "MODEL_OUTPUTS_RIGHTS_MATRIX.md", "THIRD_PARTY_DATA.md", "LICENSES/CC-BY-4.0.md"]
BLOCK_RX = re.compile(r"(<!-- TEGB:(?P<name>[a-z_]+) -->\n)(?P<body>.*?)(\n?<!-- /TEGB:(?P=name) -->)", re.S)
RESTRAINT = [r"ESA needs", r"needed by ESA", r"validated by ESA", r"ESA (has )?validated", r"endorsed by", r"solves? (ESA|the problem)",
             r"state[- ]of[- ]the[- ]art", r"independent human (review|validation)", r"expert review", r"EVE is worse", r"\bproves?\b",
             r"ESA-EO-Bench", r"Evidence Fabric", r"specialization (reduces|harms|degrades|hurts)", r"fine-tuning (reduces|harms|degrades|hurts)",
             r"JSON is (inherently )?worse", r"recommended system prompt", r"Mistral[- ]Small[- ]3\.1"]
NEGATIONS = re.compile(r"\b(not|no|never|nor|cannot|does not|do not|is not|are not|neither|without|rather than|avoid|instead of|nothing|future|planned|candidate|requires?|prerequisite|blocker|should)\b", re.I)


def numbers_in_tables() -> set[str]:
    T = json.loads((ROOT / "results" / "baseline" / "tables.json").read_text(encoding="utf-8"))
    vals = set()

    def walk(x):
        if isinstance(x, bool) or x is None:
            return
        if isinstance(x, (int, float)):
            for v in (x, 100 * x):
                for d in (1, 2, 3):
                    vals.add(f"{abs(round(v, d)):.{d}f}")
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(T)
    # dataset facts quoted in the docs (e.g. a share of the asset) are also legitimate numbers
    for line in (ROOT / "dataset" / "tasks.jsonl").read_text(encoding="utf-8").splitlines():
        for m in re.finditer(r"\d+\.\d+", line):
            vals.add(m.group(0))
    return vals


def render() -> None:
    for d in DOCS:
        p = ROOT / d
        if not p.exists():
            continue
        s = p.read_text(encoding="utf-8")

        def rep(m):
            body = (BLOCKS / f"{m.group('name')}.md").read_text(encoding="utf-8").rstrip("\n")
            return m.group(1) + body + "\n" + m.group(4).lstrip("\n")
        s2 = BLOCK_RX.sub(rep, s)
        if s2 != s:
            p.write_text(s2, encoding="utf-8")
            print("rendered", d)


def check() -> int:
    allowed = numbers_in_tables()
    problems = []
    for d in DOCS:
        p = ROOT / d
        if not p.exists():
            problems.append(f"missing doc: {d}")
            continue
        s = p.read_text(encoding="utf-8")
        for m in BLOCK_RX.finditer(s):
            want = (BLOCKS / f"{m.group('name')}.md").read_text(encoding="utf-8").rstrip("\n")
            if not m.group(4).startswith("\n") or m.group("body") != want:
                problems.append(f"{d}: block '{m.group('name')}' is stale (run --render)")
        prose = BLOCK_RX.sub("", s)
        for m in re.finditer(r"([−\-+]?\d+\.\d+)\s?(%|pp\b)|κ\s*(?:=|≈|of)?\s*(\d\.\d+)", prose):
            num = (m.group(1) or m.group(3)).lstrip("+−-")
            if num not in allowed:
                problems.append(f"{d}: number '{m.group(0)}' not found in generated tables")
        for sent in re.split(r"(?<=[.!?])\s+|\n", prose):
            for pat in RESTRAINT:
                if re.search(pat, sent, re.I) and not NEGATIONS.search(sent):
                    problems.append(f"{d}: restraint lint '{pat}' in: {sent.strip()[:140]}")
    print(json.dumps({"docs_checked": len(DOCS), "problems": problems, "result": "PASS" if not problems else "FAIL"}, indent=1, ensure_ascii=False))
    return 0 if not problems else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.render:
        render()
    sys.exit(check() if a.check else 0)
