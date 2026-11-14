"""Human blind review analysis (EVIDENCE-GROUNDING-001). Runs ONLY when all 120 items are complete;
only then does it open results/blind_key_main.json.

    python harness/human_review_analysis.py

Writes results/human_review_main.json. Human labels: YES=1, NO=0; UNCERTAIN excluded (sensitivity: UNCERTAIN=YES).
The review sample over-represents judge disagreements (half of each condition's 40 items); population-level
human UCR is therefore also reported re-weighted by stratum (disputed / non-disputed) sizes per condition.
"""

from __future__ import annotations

import csv
import json
import os
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from evaluate import kappa, wilson  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
# TEGB: frozen baseline lives in results/baseline; set TEGB_RESULTS_DIR for new runs and TEGB_OUT_DIR for evaluation outputs.
RESULTS = Path(os.environ.get("TEGB_RESULTS_DIR", ROOT / "results" / "baseline"))
OUT = Path(os.environ.get("TEGB_OUT_DIR", RESULTS))
DONE = RESULTS / "blind_review" / "blind_review_completed.csv"
KEY = RESULTS / "blind_review" / "blind_key.json"
FIELDS = ["human_unsupported_conclusion", "human_constraint_violation", "human_observability_handling", "human_factual_correctness"]


def yn(v, uncertain_as=None):
    return {"YES": True, "NO": False}.get(v, uncertain_as)


def rate(xs):
    xs = [x for x in xs if x is not None]
    return None if not xs else round(sum(xs) / len(xs), 3)


def compare(human, other):
    pairs = [(h, o) for h, o in zip(human, other) if h is not None and o is not None]
    n = len(pairs)
    if not n:
        return None
    tp = sum(1 for h, o in pairs if h and o)
    tn = sum(1 for h, o in pairs if not h and not o)
    fp = sum(1 for h, o in pairs if o and not h)  # evaluator says UC, human says no
    fn = sum(1 for h, o in pairs if h and not o)  # evaluator misses a human-flagged UC
    return {"n": n, "agreement": round((tp + tn) / n, 3), "kappa": kappa([h for h, _ in pairs], [o for _, o in pairs]),
            "false_positives": fp, "false_negatives": fn, "precision": round(tp / (tp + fp), 3) if tp + fp else None,
            "recall": round(tp / (tp + fn), 3) if tp + fn else None}


def diff_ci(a, b, iters=4000, seed=11):
    """Unpaired bootstrap CI of rate(a) - rate(b)."""
    a, b = [x for x in a if x is not None], [x for x in b if x is not None]
    rng = random.Random(seed)
    ds = sorted(sum(rng.choice(a) for _ in a) / len(a) - sum(rng.choice(b) for _ in b) / len(b) for _ in range(iters))
    return round(sum(a) / len(a) - sum(b) / len(b), 3), (round(ds[int(.025 * iters)], 3), round(ds[int(.975 * iters) - 1], 3))


def fisher_two_sided(a_yes, a_n, b_yes, b_n):
    def p(k):
        return math.comb(a_n, k) * math.comb(b_n, a_yes + b_yes - k) / math.comb(a_n + b_n, a_yes + b_yes)
    tot = a_yes + b_yes
    obs = p(a_yes)
    return round(min(1.0, sum(p(k) for k in range(max(0, tot - b_n), min(a_n, tot) + 1) if p(k) <= obs * (1 + 1e-9))), 5)


def main() -> int:
    rows = list(csv.DictReader(DONE.open(encoding="utf-8", newline=""))) if DONE.exists() else []
    complete = [r for r in rows if all(r.get(f) for f in FIELDS)]
    if len(complete) < 120:
        print(f"NOT COMPLETE: {len(complete)} / 120. The key stays closed.")
        return 2
    print("BLIND REVIEW COMPLETE — opening key")
    key = json.loads(KEY.read_text(encoding="utf-8"))
    labels = {(r["model"], r["task_id"], r["condition"], r["run"]): r
              for r in map(json.loads, (RESULTS / "labels_main.jsonl").read_text(encoding="utf-8").splitlines())}
    items = []
    for r in complete:
        k = key[r["review_id"]]
        lab = labels[(k["model"], k["task_id"], k["condition"], k["run"])]
        disputed = lab["stance"] == "DISPUTED" or (len(lab["judge_uc"]) == 2 and lab["judge_uc"][0] != lab["judge_uc"][1])
        items.append({"review_id": r["review_id"], **k, "category": lab["category"], "disputed_stratum": disputed,
                      "h_uc": yn(r["human_unsupported_conclusion"]), "h_uc_unc_yes": yn(r["human_unsupported_conclusion"], True),
                      "h_cv": yn(r["human_constraint_violation"]), "h_obs": r["human_observability_handling"],
                      "h_fact": r["human_factual_correctness"], "notes": r.get("human_notes", ""),
                      "final_uc": lab["uc"], "final_cv": lab["cv"], "claude_uc": lab["judge_uc"][0] if lab["judge_uc"] else None,
                      "gpt_uc": lab["judge_uc"][1] if len(lab["judge_uc"]) > 1 else None, "detector_uc": lab["detector_uc"],
                      "final_factual_ok": lab["factual_ok"], "final_ocr": lab["ocr"]})
    out = {"n": len(items), "uncertain_uc": sum(1 for i in items if i["h_uc"] is None)}
    conds, models = "ABC", sorted({i["model"] for i in items})
    # population counts per condition x stratum (for re-weighting)
    pop = defaultdict(int)
    for lab in labels.values():
        d = lab["stance"] == "DISPUTED" or (len(lab["judge_uc"]) == 2 and lab["judge_uc"][0] != lab["judge_uc"][1])
        pop[(lab["condition"], d)] += 1

    def weighted(c, key_="h_uc"):
        tot, acc = 0, 0.0
        for d in (True, False):
            sub = [i[key_] for i in items if i["condition"] == c and i["disputed_stratum"] == d and i[key_] is not None]
            if sub:
                acc += pop[(c, d)] * sum(sub) / len(sub)
                tot += pop[(c, d)]
        return round(acc / tot, 3) if tot else None

    out["global"] = {c: {"n": sum(1 for i in items if i["condition"] == c),
                         "human_ucr_sample": rate([i["h_uc"] for i in items if i["condition"] == c]),
                         "human_ucr_sample_ci95": wilson([i["h_uc"] for i in items if i["condition"] == c and i["h_uc"] is not None]),
                         "human_ucr_uncertain_as_yes": rate([i["h_uc_unc_yes"] for i in items if i["condition"] == c]),
                         "human_ucr_reweighted_to_population": weighted(c),
                         "final_label_ucr_same_items": rate([i["final_uc"] for i in items if i["condition"] == c]),
                         "human_cvr": rate([i["h_cv"] for i in items if i["condition"] == c]),
                         "human_observability_errors": sum(1 for i in items if i["condition"] == c and i["h_obs"] == "INCORRECT"),
                         "human_observability_applicable": sum(1 for i in items if i["condition"] == c and i["h_obs"] in ("CORRECT", "INCORRECT")),
                         "human_factual": {v: sum(1 for i in items if i["condition"] == c and i["h_fact"] == v) for v in ("CORRECT", "PARTIAL", "INCORRECT", "UNCERTAIN")}}
                     for c in conds}
    out["per_model"] = {m: {c: {"n": sum(1 for i in items if i["model"] == m and i["condition"] == c),
                                "human_ucr": rate([i["h_uc"] for i in items if i["model"] == m and i["condition"] == c])} for c in conds} for m in models}
    hu = lambda c: [i["h_uc"] for i in items if i["condition"] == c]  # noqa: E731
    out["contrasts_human"] = {}
    for a, b in (("A", "B"), ("C", "B"), ("A", "C")):
        d, ci = diff_ci(hu(a), hu(b))
        ay, an = sum(x for x in hu(a) if x is not None), len([x for x in hu(a) if x is not None])
        by, bn = sum(x for x in hu(b) if x is not None), len([x for x in hu(b) if x is not None])
        out["contrasts_human"][f"{a}_minus_{b}"] = {"diff": d, "ci95": ci, "fisher_p": fisher_two_sided(ay, an, by, bn)}
    H = [i["h_uc"] for i in items]
    out["human_vs_evaluators_uc"] = {name: compare(H, [i[k] for i in items]) for name, k in
                                     (("claude_judge", "claude_uc"), ("gpt_judge", "gpt_uc"), ("deterministic_detector", "detector_uc"), ("final_label", "final_uc"))}
    out["human_vs_final_cv"] = compare([i["h_cv"] for i in items], [i["final_cv"] for i in items])
    out["human_vs_final_factual"] = compare([None if i["h_fact"] == "UNCERTAIN" else i["h_fact"] == "CORRECT" for i in items],
                                            [i["final_factual_ok"] for i in items])
    for strat in (True, False):
        sub = [i for i in items if i["disputed_stratum"] == strat]
        out[f"human_vs_evaluators_uc_{'disputed' if strat else 'non_disputed'}_stratum"] = {
            name: compare([i["h_uc"] for i in sub], [i[k] for i in sub]) for name, k in
            (("claude_judge", "claude_uc"), ("gpt_judge", "gpt_uc"), ("deterministic_detector", "detector_uc"), ("final_label", "final_uc"))}
    out["items"] = items
    (OUT / "human_review_main.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "items"}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
