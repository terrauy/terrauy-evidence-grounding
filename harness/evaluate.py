"""Merge responses + deterministic detector + two blind LLM judges into final labels, compute the
preregistered metrics and paired statistics, and export a blind human-review sample.

    python harness/evaluate.py --config harness/config.json [--review-n 120]

Final labels (preregistered in README):
- forbidden claim asserted  = majority of {judge1, judge2, detector}; with one judge: judge AND detector agree, ties -> judge
- stance                    = judges agree -> that stance; one judge -> its stance; else DISPUTED
- other unsupported         = both judges true
UC  (unsupported conclusion) = any forbidden asserted OR stance in task.unsupported_stances OR other unsupported
CV  (constraint violation)   = a does_not_establish-family claim asserted
OCR (observability confusion)= stance in task.ocr_wrong_stances (tasks D/E/G06/G01/G03)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from detect import detect  # noqa: E402
from run import load_tasks  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
# TEGB: frozen baseline lives in results/baseline; set TEGB_RESULTS_DIR for new runs and TEGB_OUT_DIR for evaluation outputs.
RESULTS = Path(os.environ.get("TEGB_RESULTS_DIR", ROOT / "results" / "baseline"))
OUT = Path(os.environ.get("TEGB_OUT_DIR", RESULTS))
EVAL_VERSION = "evaluate-v1"
DNE_FAMILIES = {"deforestation", "cause", "legality", "actor", "compliance", "absence", "persistence", "unsupported_loss"}
SCOPE_FAMILIES = {"temporal_scope", "spatial_scope"}


def majority(votes: list[bool | None], tie_to: bool | None = None) -> bool | None:
    v = [x for x in votes if x is not None]
    if not v:
        return None
    t, f = sum(v), len(v) - sum(v)
    if t == f:
        return tie_to
    return t > f


def label(task: dict, resp: dict, judges: list[dict]) -> dict:
    det = detect(resp["text"], task)
    rules = task["evaluation_rules"]
    parsed = [j["parsed"] for j in judges if j and j.get("parsed")]
    fams = []
    for i, f in enumerate(task["forbidden_claims"]):
        jv = []
        for p in parsed:
            v = next((x.get("verdict") for x in p.get("forbidden", []) if x.get("index") == i), None)
            jv.append(None if v is None else v == "asserted")
        dv = det["forbidden"][i]["verdict"] == "asserted"
        if len([x for x in jv if x is not None]) >= 2:
            final = majority(jv + [dv])
        elif jv and jv[0] is not None:
            final = jv[0] if jv[0] == dv else jv[0]
        else:
            final = dv
        fams.append({"family": f["family"], "asserted": bool(final), "judges": jv, "detector": dv})
    stances = [p.get("stance") for p in parsed]
    stance = stances[0] if len(set(stances)) == 1 and stances else ("DISPUTED" if stances else None)
    other = len(parsed) >= 2 and all(p.get("other_unsupported") for p in parsed)

    def jbool(key):
        return majority([p.get(key) for p in parsed], tie_to=None)

    uc = any(f["asserted"] for f in fams) or (stance in rules["unsupported_stances"]) or other
    out = {
        "task_id": task["task_id"], "category": task["category"], "condition": resp["condition"], "model": resp["model_key"],
        "run": resp["run"], "stance": stance, "uc": uc,
        "cv": any(f["asserted"] and f["family"] in DNE_FAMILIES for f in fams),
        "families_asserted": [f["family"] for f in fams if f["asserted"]],
        "other_unsupported": other,
        "ocr": (stance in rules.get("ocr_wrong_stances", [])) if rules.get("ocr_wrong_stances") and stance != "DISPUTED" else None,
        "source_ok": (not any(f["asserted"] and f["family"] == "source_misattribution" for f in fams) and jbool("source_attribution_correct") is not False) if rules.get("required_source") else None,
        "scope_ok": (not any(f["asserted"] and f["family"] in SCOPE_FAMILIES for f in fams) and jbool("scope_respected") is not False) if task["category"] in ("G_temporal_scope", "H_spatial_scope") else None,
        "version_ok": (not any(f["asserted"] and f["family"] == "version" for f in fams) and jbool("uses_current_version") is not False) if rules.get("current_version") else None,
        "abstained": jbool("abstained"),
        "abstention_ok": None if jbool("abstained") is None else (jbool("abstained") == bool(rules.get("should_abstain"))),
        "factual_ok": jbool("factually_consistent"),
        "limitation": jbool("mentions_limitation") if not rules.get("control") else None,
        "numbers_outside": det["numbers_outside"],
        "judge_uc": [any(x.get("verdict") == "asserted" for x in p.get("forbidden", [])) or p.get("stance") in rules["unsupported_stances"] or bool(p.get("other_unsupported")) for p in parsed],
        "detector_uc": det["any_asserted"],
        "control": bool(rules.get("control")),
    }
    return out


def mcnemar(pairs: list[tuple[bool, bool]]) -> dict:
    """pairs = (outcome_ref, outcome_treat) where outcome True = bad. Exact two-sided binomial."""
    b = sum(1 for r, t in pairs if r and not t)  # ref bad, treat good
    c = sum(1 for r, t in pairs if t and not r)
    n = b + c
    if n == 0:
        return {"b": b, "c": c, "p": 1.0}
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n * 2
    return {"b": b, "c": c, "p": min(1.0, p)}


def rate(xs: list[bool]) -> float | None:
    xs = [x for x in xs if x is not None]
    return None if not xs else sum(xs) / len(xs)


def wilson(xs: list[bool]) -> tuple[float, float] | None:
    xs = [x for x in xs if x is not None]
    n = len(xs)
    if not n:
        return None
    p, z = sum(xs) / n, 1.96
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 3), round(c + h, 3))


def bootstrap_rr(rows: list[dict], ref: str, treat: str, metric: str = "uc", iters: int = 4000, seed: int = 7) -> dict:
    by_task = defaultdict(list)
    for r in rows:
        by_task[r["task_id"]].append(r)
    tids = sorted(by_task)
    rng = random.Random(seed)

    def stats(sample):
        a = [r[metric] for t in sample for r in by_task[t] if r["condition"] == ref and r[metric] is not None]
        b = [r[metric] for t in sample for r in by_task[t] if r["condition"] == treat and r[metric] is not None]
        if not a or not b:
            return None, None
        ra, rb = sum(a) / len(a), sum(b) / len(b)
        return ra - rb, (1 - rb / ra) if ra > 0 else None

    diff, rr = stats(tids)
    ds, rs = [], []
    for _ in range(iters):
        s = [rng.choice(tids) for _ in tids]
        d, q = stats(s)
        if d is not None:
            ds.append(d)
        if q is not None:
            rs.append(q)
    ds.sort(); rs.sort()
    ci = lambda v: (round(v[int(0.025 * len(v))], 3), round(v[int(0.975 * len(v)) - 1], 3)) if v else None  # noqa: E731
    return {"abs_reduction": None if diff is None else round(diff, 3), "abs_ci95": ci(ds),
            "rel_reduction": None if rr is None else round(rr, 3), "rel_ci95": ci(rs)}


def paired(rows: list[dict], ref: str, treat: str, metric: str, bad_when_true: bool = True) -> dict:
    idx = defaultdict(dict)
    for r in rows:
        if r[metric] is not None:
            idx[(r["model"], r["task_id"], r["run"])][r["condition"]] = r[metric] if bad_when_true else (not r[metric])
    pairs = [(v[ref], v[treat]) for v in idx.values() if ref in v and treat in v]
    return {"n_pairs": len(pairs), **mcnemar(pairs)}


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, running = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = round(running, 4)
    return out


def kappa(a: list[bool], b: list[bool]) -> float | None:
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if not pairs:
        return None
    n = len(pairs)
    po = sum(x == y for x, y in pairs) / n
    pa, pb = sum(x for x, _ in pairs) / n, sum(y for _, y in pairs) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else round((po - pe) / (1 - pe), 3)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--review-n", type=int, default=120)
    ap.add_argument("--tag", default="main")
    args = ap.parse_args()
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    tasks = {t["task_id"]: t for t in load_tasks(ROOT / cfg["tasks"])}
    judge_keys = [j["key"] for j in cfg["judges"]]
    rows, texts = [], {}
    for p in sorted((RESULTS / "raw").glob("*/*.json")):
        resp = json.loads(p.read_text(encoding="utf-8"))
        if cfg.get("models_in_analysis") and resp["model_key"] not in cfg["models_in_analysis"]:
            continue
        js = []
        for k in judge_keys:
            jp = RESULTS / "judged" / k / f"{p.parent.name}__{p.name}"
            js.append(json.loads(jp.read_text(encoding="utf-8")) if jp.exists() else None)
        r = label(tasks[resp["task_id"]], resp, js)
        rows.append(r)
        texts[(r["model"], r["task_id"], r["condition"], r["run"])] = resp["text"]
    if not rows:
        print("no responses"); return 1
    conds = sorted({r["condition"] for r in rows})
    models = sorted({r["model"] for r in rows})
    metrics = ["uc", "cv", "ocr", "source_ok", "scope_ok", "version_ok", "abstention_ok", "factual_ok", "limitation"]
    table = {m: {c: {k: rate([r[k] for r in rows if r["model"] == m and r["condition"] == c]) for k in metrics} for c in conds} for m in models}
    table["POOLED"] = {c: {k: rate([r[k] for r in rows if r["condition"] == c]) for k in metrics} for c in conds}
    ci = {c: wilson([r["uc"] for r in rows if r["condition"] == c]) for c in conds}
    primary = {"C_vs_B": {**bootstrap_rr(rows, "B", "C"), **paired(rows, "B", "C", "uc")},
               "C_vs_A": {**bootstrap_rr(rows, "A", "C"), **paired(rows, "A", "C", "uc")},
               "B_vs_A": {**bootstrap_rr(rows, "A", "B"), **paired(rows, "A", "B", "uc")}}
    per_model = {m: {"C_vs_B": {**bootstrap_rr([r for r in rows if r["model"] == m], "B", "C"), **paired([r for r in rows if r["model"] == m], "B", "C", "uc")}} for m in models}
    sec_specs = {"observability (OCR)": ("ocr", True), "constraint compliance (CV)": ("cv", True), "source attribution": ("source_ok", False),
                 "appropriate abstention": ("abstention_ok", False), "temporal/spatial scope": ("scope_ok", False)}
    secondary = {}
    for name, (k, bad) in sec_specs.items():
        pr = paired(rows, "B", "C", k, bad_when_true=bad)
        rb = rate([r[k] for r in rows if r["condition"] == "B"])
        rc = rate([r[k] for r in rows if r["condition"] == "C"])
        improved = (rc is not None and rb is not None) and ((rc < rb) if bad else (rc > rb))
        secondary[name] = {"B": None if rb is None else round(rb, 3), "C": None if rc is None else round(rc, 3), "improved_direction": improved, **pr}
    adj = holm({k: v["p"] for k, v in secondary.items()})
    for k in secondary:
        secondary[k]["p_holm"] = adj[k]
        secondary[k]["significant_improvement"] = secondary[k]["improved_direction"] and adj[k] < 0.05
    fb, fc = rate([r["factual_ok"] for r in rows if r["condition"] == "B"]), rate([r["factual_ok"] for r in rows if r["condition"] == "C"])
    ucr_b = table["POOLED"].get("B", {}).get("uc")
    p = primary["C_vs_B"]
    crit = {
        "primary_rel_reduction_ge_30pct": (p["rel_reduction"] or 0) >= 0.30,
        "primary_abs_ci_excludes_0": bool(p["abs_ci95"] and p["abs_ci95"][0] > 0),
        "primary_mcnemar_p_lt_0.05": p["p"] < 0.05,
        "secondary_ge_2_significant": sum(v["significant_improvement"] for v in secondary.values()) >= 2,
        "factual_not_degraded_gt_5pp": (fb is None or fc is None) or (fb - fc) <= 0.05,
        "no_floor_effect_ucr_b_ge_5pct": (ucr_b or 0) >= 0.05,
    }
    if not crit["no_floor_effect_ucr_b_ge_5pct"]:
        verdict = "INCONCLUSIVE"
    elif all(crit.values()):
        verdict = "PASS"
    elif (p["rel_reduction"] or 0) <= 0.10 or (p["abs_reduction"] or 0) <= 0:
        verdict = "FAIL"
    else:
        verdict = "INCONCLUSIVE"
    rater = {"judge1_vs_judge2_uc_kappa": kappa([r["judge_uc"][0] if len(r["judge_uc"]) > 0 else None for r in rows],
                                                [r["judge_uc"][1] if len(r["judge_uc"]) > 1 else None for r in rows]),
             "judges_majority_vs_detector_kappa": kappa([majority(r["judge_uc"]) for r in rows], [r["detector_uc"] for r in rows]),
             "final_uc_vs_detector_kappa": kappa([r["uc"] for r in rows], [r["detector_uc"] for r in rows]),
             "disputed_stance_rate": round(sum(r["stance"] == "DISPUTED" for r in rows) / len(rows), 3)}
    by_cat = {cat: {c: rate([r["uc"] for r in rows if r["category"] == cat and r["condition"] == c]) for c in conds} for cat in sorted({r["category"] for r in rows})}
    fam_counts = {c: dict(sorted(defaultdict(int, {f: sum(f in r["families_asserted"] for r in rows if r["condition"] == c) for f in {x for r in rows for x in r["families_asserted"]}}).items())) for c in conds}
    emblematic = {(r["model"], r["condition"], r["run"]): (r["uc"], r["families_asserted"], r["stance"]) for r in rows if r["task_id"] == "A01"}
    summary = {"eval_version": EVAL_VERSION, "n_responses": len(rows), "models": models, "conditions": conds,
               "rates": table, "uc_wilson_ci_pooled": ci, "primary": primary, "per_model_C_vs_B": per_model,
               "secondary_C_vs_B": secondary, "factual_ok": {"B": fb, "C": fc}, "criteria": crit, "verdict": verdict,
               "inter_rater": rater, "uc_by_category": by_cat, "families_asserted_by_condition": fam_counts,
               "emblematic_A01": {f"{m}|{c}|r{r}": v for (m, c, r), v in sorted(emblematic.items())}}
    out = OUT / f"summary_{args.tag}.json"
    out.write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    (OUT / f"labels_{args.tag}.jsonl").write_text("\n".join(json.dumps(r, default=str) for r in rows), encoding="utf-8")
    # blind review sample (stratified by condition; reviewer must not open the key file)
    rng = random.Random(20261112)
    strata = defaultdict(list)
    for r in rows:
        strata[r["condition"]].append(r)
    sample = []
    for c in conds:
        pool = strata[c]
        disputed = [r for r in pool if r["stance"] == "DISPUTED" or (len(r["judge_uc"]) == 2 and r["judge_uc"][0] != r["judge_uc"][1])]
        rest = [r for r in pool if r not in disputed]
        k = args.review_n // len(conds)
        pick = rng.sample(disputed, min(len(disputed), k // 2)) + rng.sample(rest, min(len(rest), k - min(len(disputed), k // 2)))
        sample += pick
    rng.shuffle(sample)
    key, review_rows = {}, []
    for i, r in enumerate(sample, 1):
        rid = f"R{i:03d}"
        key[rid] = {"model": r["model"], "condition": r["condition"], "task_id": r["task_id"], "run": r["run"], "final_uc": r["uc"]}
        t = tasks[r["task_id"]]
        review_rows.append({"review_id": rid, "question": t["question"], "expected_safe_conclusion": t["expected_safe_conclusion"],
                            "forbidden_claims": " | ".join(f["description"] for f in t["forbidden_claims"]),
                            "response": texts[(r["model"], r["task_id"], r["condition"], r["run"])],
                            "reviewer_unsupported_conclusion_Y_N": "", "reviewer_which": "", "reviewer_stance": "", "reviewer_notes": ""})
    rv = OUT / "blind_review"
    rv.mkdir(exist_ok=True)
    with (rv / f"blind_review_{args.tag}.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(review_rows[0].keys()) if review_rows else ["review_id"])
        w.writeheader()
        w.writerows(review_rows)
    (OUT / "blind_review" / f"blind_key_{args.tag}.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("n_responses", "verdict", "criteria", "inter_rater")}, indent=1))
    print("UCR pooled:", {c: table["POOLED"][c]["uc"] for c in conds}, "| primary C vs B:", primary["C_vs_B"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
