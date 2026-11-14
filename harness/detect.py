"""Deterministic detectors (no LLM): forbidden-claim patterns with negation/hedge handling, and
numbers that do not appear in the evidence or the question.

A pattern match counts as ASSERTED unless, within the same sentence and up to 10 words before it,
there is a negation/limitation cue ("not", "no", "cannot", "does not establish", "whether"...) — or
a hedge cue ("may", "might", "could", "possibly") which makes it HEDGED (reported separately, not a
violation). Deliberately simple and auditable; its agreement with judges is reported.
"""

from __future__ import annotations

import re
from typing import Any

DETECT_VERSION = "detect-v1"
NEG = re.compile(r"\b(not|no|never|cannot|can't|can ?not|isn't|wasn't|aren't|weren't|doesn't|don't|didn't|"
                 r"won't|without|nor|neither|unable|insufficient|whether|rather than|instead of|unknown|unclear|"
                 r"undetermined|unconfirmed|no evidence|nothing|absence of evidence|does not|did not|do not)\b")
HEDGE = re.compile(r"\b(may|might|could|possibly|perhaps|potentially|likely|plausibl\w*|suggests?|consistent with|"
                   r"if|would need|would require|cannot rule out|can't rule out)\b")
SENT = re.compile(r"(?<=[.!?;:\n])\s+")


def sentences(text: str) -> list[str]:
    return [s for s in SENT.split(text.lower()) if s.strip()]


def classify(text: str, patterns: list[str]) -> str:
    """'asserted' | 'hedged' | 'negated' | 'absent' for one forbidden claim."""
    found = "absent"
    for s in sentences(text):
        for p in patterns:
            for m in re.finditer(p, s):
                before = " ".join(s[: m.start()].split()[-10:])
                if NEG.search(before):
                    found = found if found in ("asserted", "hedged") else "negated"
                elif HEDGE.search(before):
                    found = "hedged" if found != "asserted" else found
                else:
                    return "asserted"
    return found


NUM = re.compile(r"(?<![\w.])(\d{1,5}(?:[.,]\d+)?)(?![\w])")


def numbers(x: Any) -> set[float]:
    out: set[float] = set()
    if isinstance(x, dict):
        for v in x.values():
            out |= numbers(v)
    elif isinstance(x, list):
        for v in x:
            out |= numbers(v)
    elif isinstance(x, bool):
        pass
    elif isinstance(x, (int, float)):
        out.add(float(x))
    elif isinstance(x, str):
        for m in NUM.finditer(x):
            out.add(float(m.group(1).replace(",", ".")))
    return out


def numbers_outside(text: str, task: dict) -> list[float]:
    """Numbers in the answer not present (±0.05 abs or 1% rel) in the evidence or the question, and
    not a sum/difference of two evidence numbers (simple arithmetic is allowed). Small integers 0-10
    (list markers, counts) are ignored."""
    allowed = numbers(task["units"]) | numbers(task["question"])
    pool = sorted(allowed)
    sums = {round(a + b, 2) for a in pool for b in pool} | {round(abs(a - b), 2) for a in pool for b in pool}
    out = []
    for m in NUM.finditer(text):
        v = float(m.group(1).replace(",", "."))
        if v <= 10 and float(v).is_integer():
            continue
        if any(abs(v - a) <= max(0.05, 0.01 * abs(a)) for a in pool):
            continue
        if any(abs(v - s) <= 0.1 for s in sums):
            continue
        out.append(v)
    return out


def detect(text: str, task: dict) -> dict:
    fc = [{"family": f["family"], "verdict": classify(text, f["patterns"])} for f in task["forbidden_claims"]]
    return {"detect_version": DETECT_VERSION, "forbidden": fc,
            "any_asserted": any(f["verdict"] == "asserted" for f in fc),
            "numbers_outside": numbers_outside(text, task)}
