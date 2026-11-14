"""Supplementary analyses for EVIDENCE-GROUNDING-001 (EXPLORATORY: not part of the preregistered verdict).

Reads results/labels_<tag>.jsonl (written by evaluate.py) plus raw responses and writes results/extra_<tag>.json.

    python harness/analysis_extra.py --tag main
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from evaluate import bootstrap_rr, mcnemar, paired, rate, wilson  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
# TEGB: frozen baseline lives in results/baseline; set TEGB_RESULTS_DIR for new runs and TEGB_OUT_DIR for evaluation outputs.
RESULTS = Path(os.environ.get("TEGB_RESULTS_DIR", ROOT / "results" / "baseline"))
OUT = Path(os.environ.get("TEGB_OUT_DIR", RESULTS))
METRICS = ["uc", "cv", "ocr", "source_ok", "scope_ok", "version_ok", "abstention_ok", "factual_ok", "limitation"]


def table(rows):
    out = {}
    for c in "ABC":
        sub = [r for r in rows if r["condition"] == c]
        out[c] = {k: (None if rate([r[k] for r in sub]) is None else round(rate([r[k] for r in sub]), 3)) for k in METRICS}
        out[c]["uc_ci95"] = wilson([r["uc"] for r in sub])
        out[c]["n"] = len(sub)
    return out


def compare(rows, ref, treat):
    return {**bootstrap_rr(rows, ref, treat), **paired(rows, ref, treat, "uc")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="main")
    args = ap.parse_args()
    rows = [json.loads(x) for x in (OUT / f"labels_{args.tag}.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    raw = {}
    for p in (RESULTS / "raw").glob("*/*.json"):
        r = json.loads(p.read_text(encoding="utf-8"))
        raw[(r["model_key"], r["task_id"], r["condition"], r["run"])] = r
    for r in rows:
        rr = raw[(r["model"], r["task_id"], r["condition"], r["run"])]
        r["truncated"] = rr.get("stop_reason") in ("max_tokens", "length")
        r["text"] = rr["text"]
    models = sorted({r["model"] for r in rows})
    out = {"note": "EXPLORATORY analyses; the preregistered verdict is in summary_<tag>.json"}

    # 1. per model: A/B/C tables and the three paired comparisons
    out["per_model"] = {m: {"rates": table([r for r in rows if r["model"] == m]),
                            "C_vs_B": compare([r for r in rows if r["model"] == m], "B", "C"),
                            "C_vs_A": compare([r for r in rows if r["model"] == m], "A", "C"),
                            "B_vs_A": compare([r for r in rows if r["model"] == m], "A", "B")} for m in models}

    # 2. EVE vs its base model, same task/condition/run (paired; ref = base, treat = EVE)
    def eve_vs_base(cond):
        idx = defaultdict(dict)
        for r in rows:
            if r["condition"] == cond and r["model"] in ("eve-instruct-24b", "mistral-small-3.2-base"):
                idx[(r["task_id"], r["run"])][r["model"]] = r["uc"]
        pairs = [(v["mistral-small-3.2-base"], v["eve-instruct-24b"]) for v in idx.values() if len(v) == 2]
        base = sum(a for a, _ in pairs) / len(pairs) if pairs else None
        eve = sum(b for _, b in pairs) / len(pairs) if pairs else None
        return {"n_pairs": len(pairs), "ucr_base": None if base is None else round(base, 3), "ucr_eve": None if eve is None else round(eve, 3), **mcnemar(pairs)}
    out["eve_vs_base_by_condition"] = {c: eve_vs_base(c) for c in "ABC"}
    # 2x2 decomposition: specialization effect vs Evidence-Unit effect
    g = {(m, c): rate([r["uc"] for r in rows if r["model"] == m and r["condition"] == c]) for m in ("eve-instruct-24b", "mistral-small-3.2-base") for c in "ABC"}
    out["eve_base_2x2_ucr"] = {f"{m}|{c}": None if v is None else round(v, 3) for (m, c), v in g.items()}

    # 3. sensitivity analyses on the primary contrast (C vs B)
    trunc_keys = {(r["model"], r["task_id"], r["run"]) for r in rows if r["truncated"]}
    out["sensitivity_C_vs_B"] = {
        "all": compare(rows, "B", "C"),
        "exclude_pairs_with_any_truncated_response": compare([r for r in rows if (r["model"], r["task_id"], r["run"]) not in trunc_keys], "B", "C"),
        "run0_only": compare([r for r in rows if r["run"] == 0], "B", "C"),
        "exclude_controls": compare([r for r in rows if not r["control"]], "B", "C"),
        "exclude_claude_default_temperature": compare([r for r in rows if r["model"] != "claude-sonnet-5-5"], "B", "C"),
        "open_weights_only": compare([r for r in rows if r["model"] in ("eve-instruct-24b", "mistral-small-3.2-base")], "B", "C"),
        "frontier_api_only": compare([r for r in rows if r["model"] in ("claude-sonnet-5-5", "gpt-6.1-terra")], "B", "C"),
    }
    out["truncation"] = {m: dict(Counter(r["condition"] for r in rows if r["model"] == m and r["truncated"])) for m in models}

    # 3b. instrument sensitivity: Claude judge only / deterministic only / both judges agree
    from evaluate import label  # noqa: PLC0415
    from run import load_tasks  # noqa: PLC0415

    cfg = json.loads((ROOT / "harness" / "config.baseline.json").read_text(encoding="utf-8"))
    tasks = {t["task_id"]: t for t in load_tasks(ROOT / cfg["tasks"])}

    def relabel(judge_keys):
        res = []
        for (mk, tid, cond, run), resp in raw.items():
            js = []
            for k in judge_keys:
                jp = RESULTS / "judged" / k / f"{mk}__{tid}_{cond}_r{run}.json"
                js.append(json.loads(jp.read_text(encoding="utf-8")) if jp.exists() else None)
            res.append(label(tasks[tid], resp, js))
        return res

    claude_only = relabel(["judge-claude-sonnet-5-5"])
    gpt_only = relabel(["judge-gpt-6.1-terra"])
    det_rows = [{**r, "uc": r["detector_uc"]} for r in rows]
    agree = [r for r in rows if len(r["judge_uc"]) == 2 and r["judge_uc"][0] == r["judge_uc"][1]]
    gpt_cov = sum(1 for r in rows if len(r["judge_uc"]) == 2)
    out["instrument_sensitivity"] = {}
    for name, rs in (("both_judges_plus_detector (primary)", rows), ("claude_judge_only", claude_only),
                     ("gpt_judge_only", [r for r in gpt_only if r["stance"] is not None]),
                     ("deterministic_detector_only", det_rows), ("subset_both_judges_agree", agree)):
        ucr = {c: round(rate([r["uc"] for r in rs if r["condition"] == c]) or 0, 3) for c in "ABC"}
        out["instrument_sensitivity"][name] = {"n": len(rs), "ucr": ucr, "C_vs_B": compare(rs, "B", "C"), "C_vs_A": compare(rs, "A", "C")}
    out["second_judge_coverage"] = {"responses_with_both_judges": gpt_cov, "total": len(rows), "pct": round(100 * gpt_cov / len(rows), 1)}
    # judge-vs-judge disagreement structure on UC
    dis = [r for r in rows if len(r["judge_uc"]) == 2 and r["judge_uc"][0] != r["judge_uc"][1]]
    out["judge_disagreement"] = {"n": len(dis), "claude_uc_gpt_not": sum(1 for r in dis if r["judge_uc"][0]), "gpt_uc_claude_not": sum(1 for r in dis if r["judge_uc"][1]),
                                 "by_condition": dict(Counter(r["condition"] for r in dis)), "by_model": dict(Counter(r["model"] for r in dis))}

    # 4. category x condition (pooled) and per model
    cats = sorted({r["category"] for r in rows})
    out["uc_by_category"] = {cat: {c: round(rate([r["uc"] for r in rows if r["category"] == cat and r["condition"] == c]) or 0, 3) for c in "ABC"} for cat in cats}
    out["uc_by_category_model"] = {m: {cat: {c: round(rate([r["uc"] for r in rows if r["model"] == m and r["category"] == cat and r["condition"] == c]) or 0, 3)
                                             for c in "ABC"} for cat in cats} for m in models}

    # 5. observability confusion detail (D = NOT_DETECTED tasks, E = INSUFFICIENT_EVIDENCE tasks)
    out["stance_distribution_D_E"] = {cat: {c: dict(Counter(r["stance"] for r in rows if r["category"] == cat and r["condition"] == c))
                                            for c in "ABC"} for cat in ("D_non_detection", "E_non_observability")}
    out["families_asserted"] = {c: dict(Counter(f for r in rows if r["condition"] == c for f in r["families_asserted"])) for c in "ABC"}

    # 6. paired transitions B->C (for failure analysis): helped / hurt per model and category
    idx = defaultdict(dict)
    for r in rows:
        idx[(r["model"], r["task_id"], r["run"])][r["condition"]] = r
    helped, hurt = [], []
    for k, v in idx.items():
        if "B" in v and "C" in v:
            if v["B"]["uc"] and not v["C"]["uc"]:
                helped.append(k)
            elif v["C"]["uc"] and not v["B"]["uc"]:
                hurt.append(k)
    out["B_to_C_transitions"] = {"helped": len(helped), "hurt": len(hurt),
                                 "helped_by_model": dict(Counter(k[0] for k in helped)), "hurt_by_model": dict(Counter(k[0] for k in hurt)),
                                 "helped_by_task": dict(Counter(k[1] for k in helped).most_common(12)), "hurt_by_task": dict(Counter(k[1] for k in hurt).most_common(12))}
    ex = {}
    for name, keys in (("helped", helped), ("hurt", hurt)):
        ex[name] = [{"model": k[0], "task": k[1], "run": k[2], "B_families": idx[k]["B"]["families_asserted"], "B_stance": idx[k]["B"]["stance"],
                     "C_families": idx[k]["C"]["families_asserted"], "C_stance": idx[k]["C"]["stance"],
                     "B_text": idx[k]["B"]["text"][:500], "C_text": idx[k]["C"]["text"][:500]} for k in sorted(keys)[:40]]
    out["examples"] = ex
    (OUT / f"extra_{args.tag}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("eve_vs_base_by_condition", "eve_base_2x2_ucr", "sensitivity_C_vs_B", "truncation", "B_to_C_transitions")}, indent=1, default=str)[:6000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
