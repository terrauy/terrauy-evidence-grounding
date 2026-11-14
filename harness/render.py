"""Render one task's canonical evidence (`units`) into the three experimental conditions.

A — RAW: tool-style outputs (measurements, source metadata, coverage, run metadata) WITHOUT the
    semantic layer: no assessment status, no supports, no does_not_establish, no context labels,
    no source-role descriptions, no version status words.
B — TEXT: every value of C rendered as natural-language prose (no field names, no codes).
C — UNIT: the structured Evidence Unit JSON (experimental schema evidence-unit/0.1-exp).

check_equivalence(units, text) verifies that every informative leaf value of C appears in B
(codes and key names excluded: they are the experimental variable "structure").
"""

from __future__ import annotations

import json
from typing import Any

PROMPT_VERSION = "prompt-v1"
RENDER_VERSION = "render-v1"
SYSTEM_PROMPT = (
    "You are an assistant that answers analysts' questions about physical assets using Earth-observation "
    "evidence returned by tools. Answer the analyst's question in plain language, in at most 150 words, "
    "based on the tool output provided."
)

STATUS_WORDS = {
    "SUPPORTED": "supported", "CONTRADICTED": "contradicted", "NOT_SUPPORTED": "not supported",
    "NOT_DETECTED": "not detected", "INSUFFICIENT_EVIDENCE": "insufficient evidence",
    "PENDING_CORROBORATION": "pending corroboration", "CURRENT": "current", "SUPERSEDED": "superseded",
}
REASON_WORDS = {"missing_coverage": "missing coverage", "temporal_gap": "temporal gap"}


def fmt(v: Any) -> str:
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:g}" if abs(v) >= 1e-4 or v == 0 else repr(v)
    return str(v)


def human(k: str) -> str:
    return k.replace("_", " ").replace("pct", "%").strip()


# ---- C ------------------------------------------------------------------------------------------
def render_unit(units: list[dict]) -> str:
    payload = units[0] if len(units) == 1 else {"evidence_units": units}
    return json.dumps(payload, indent=2, ensure_ascii=False)


# ---- B ------------------------------------------------------------------------------------------
def _pairs(d: dict, skip: tuple[str, ...] = ()) -> str:
    parts = []
    for k, v in d.items():
        if k in skip or v is None:
            continue
        if isinstance(v, dict):
            parts.append(f"{human(k)}: " + _pairs(v))
        elif isinstance(v, list):
            if v and isinstance(v[0], dict):
                parts.append(f"{human(k)}: " + "; ".join(_pairs(x) for x in v))
            else:
                parts.append(f"{human(k)}: " + (", ".join(fmt(x) for x in v) if v else "none"))
        else:
            parts.append(f"{human(k)} {STATUS_WORDS.get(v, fmt(v)) if isinstance(v, str) else fmt(v)}")
    return ", ".join(parts)


def render_text_one(u: dict) -> str:
    ver = u["version"]
    s = [f"This is evidence unit {u['unit_id']}, version {ver['number']}, which is {STATUS_WORDS[ver['status']]}"
         + (f" and supersedes {ver['supersedes']}" if ver.get("supersedes") else "") + f". It reflects what was known as of {u['knowledge_at']}."]
    a = u["asset_reference"]
    s.append(f"It concerns asset {a['id']}, a {a['type']}" + (f" of {fmt(a['area_ha'])} ha" if a.get("area_ha") is not None else "") + ".")
    c = u["claim"]
    s.append(f"The claim evaluated is: {c['statement']}, for the interval {c['interval']}, over the {c['scope']}.")
    asm = u["assessment"]
    line = f"The assessment of this claim is {STATUS_WORDS[asm['status']]}"
    if asm.get("reasons"):
        line += " because of " + " and ".join(REASON_WORDS.get(r, r) for r in asm["reasons"])
    line += "."
    if asm.get("context"):
        line += f" The {asm['context']}."
    if asm.get("not_covered"):
        line += " Not covered: " + "; ".join(asm["not_covered"]) + "."
    s.append(line)
    for o in u["observations"]:
        s.append(f"From {o['source']}, {o['observed']}: " + _pairs(o, skip=("source", "observed")) + ".")
    s.append("Regarding observability, " + _pairs(u["observability"]) + ".")
    if u["supports"]:
        s.append("What this evidence supports: " + " ".join(u["supports"]))
    else:
        s.append("This evidence does not support any positive statement about the claim.")
    s.append("What this evidence does not establish: " + "; ".join(f"({i}) {d['text']}" for i, d in enumerate(u["does_not_establish"], 1)) + ".")
    s.append("Sources: " + "; ".join(f"{x['provider']}, {x['dataset']} version {x['version']} ({x['role']}; license {x['license']})" for x in u["source_lineage"]) + ".")
    p = u["processing_lineage"]
    s.append(f"Processing: {p['engine']} {p['version']}, with parameters " + _pairs(p["parameters"]) + ".")
    return " ".join(s)


def render_text(units: list[dict]) -> str:
    return "\n\n".join(render_text_one(u) for u in units)


# ---- A ------------------------------------------------------------------------------------------
def render_raw(units: list[dict]) -> str:
    outs = []
    for u in units:
        run = {"tool": "run_metadata", "run": f"run-{u['version']['number']}", "run_date": u["knowledge_at"],
               "engine": u["processing_lineage"]["engine"], "engine_version": u["processing_lineage"]["version"],
               "parameters": u["processing_lineage"]["parameters"], "asset": u["asset_reference"]["id"],
               "asset_area_ha": u["asset_reference"].get("area_ha"),
               "datasets": [{k: x[k] for k in ("provider", "dataset", "version", "license")} for x in u["source_lineage"]]}
        tools = [run]
        if u["claim"]["type"] == "thermal_detection":
            tools.append({"tool": "firms_detections", "period": u["claim"]["interval"],
                          "detections_intersecting_asset": u["observations"][0]["count"],
                          "coverage_by_sensor": u["observability"]["coverage_by_sensor"]})
        elif "reasons" in u["assessment"] and "missing_coverage" in u["assessment"]["reasons"]:
            tools.append({"tool": "land_change_zonal_stats", "status": "error",
                          "message": u["observability"]["reason"]})
        else:
            meta = dict(u["observability"])
            for o in u["observations"]:
                o2 = {k: v for k, v in o.items() if k not in ("event_status", "territorial_context")}
                if o2.get("source", "").startswith("JRC") and "agreeing_fraction_of_event_area" in o2:
                    frac = o2.pop("agreeing_fraction_of_event_area")
                    forest = frac if o2["observed"].startswith("forest at 2020") else (None if frac is None else round(1 - frac, 2))
                    o2 = {"source": o2["source"], "observed": "share of the event area mapped as forest in 2020",
                          "fraction": forest}
                if "events" in o2:
                    o2["events"] = [{k: v for k, v in e.items() if k != "event_status"} for e in o2["events"]]
                if "jrc_agreement" in o2:  # asset-level event rows: report forest fraction at 2020 instead
                    o2["jrc_forest_2020_fraction_of_event_area"] = o2.pop("jrc_agreement")
                tools.append(dict(tool="observation", **o2))
            tools.append(dict(tool="coverage_metadata", **meta))
        outs.append(tools)
    flat = outs[0] if len(outs) == 1 else [{"run": f"run-{u['version']['number']}", "outputs": o} for u, o in zip(units, outs)]
    return json.dumps(flat, indent=2, ensure_ascii=False)


RENDERERS = {"A": render_raw, "B": render_text, "C": render_unit}


def build_prompt(task: dict, condition: str) -> tuple[str, str]:
    body = RENDERERS[condition](task["units"])
    fence = "" if condition == "B" else "```json\n"
    end = "" if condition == "B" else "\n```"
    user = f"Analyst question: {task['question']}\n\nOutput of the evidence tool(s):\n\n{fence}{body}{end}"
    return SYSTEM_PROMPT, user


# ---- equivalence check B vs C -------------------------------------------------------------------
def _leaves(x: Any, path: str = "") -> list[tuple[str, Any]]:
    out = []
    if isinstance(x, dict):
        for k, v in x.items():
            if k == "code" or (k == "type" and path.endswith("claim")):  # structure-only tokens (the experimental variable)
                continue
            out += _leaves(v, f"{path}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            out += _leaves(v, f"{path}[{i}]")
    elif x is not None:
        out.append((path, x))
    return out


def check_equivalence(units: list[dict], text: str) -> list[str]:
    missing = []
    for path, v in _leaves(units):
        token = STATUS_WORDS.get(v, REASON_WORDS.get(v, fmt(v))) if isinstance(v, str) else fmt(v)
        if token not in text:
            missing.append(f"{path}={token!r}")
    return missing
