"""Generate every published number of TEGB v0.1 from the frozen baseline outputs. Single source of truth.

    python analysis/tables.py

Reads results/baseline/{summary_main.json, extra_main.json, cost_final.json, raw/, development_run/, invariance_exploratory.json}.
Writes results/baseline/tables.json and results/baseline/TABLES.md, plus the markdown blocks used by the docs
(analysis/blocks/*.md, inserted by analysis/render_docs.py and verified by analysis/check_consistency.py).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results" / "baseline"
BLOCKS = ROOT / "analysis" / "blocks"
COND = {"A": "RAW", "B": "TEXT", "C": "STRUCTURED"}
MODELS = [  # display order and names; ids are read from the response logs
    ("eve-instruct-24b", "EVE-Instruct"),
    ("mistral-small-3.2-base", "Mistral Small 3.2"),
    ("claude-sonnet-5-5", "Claude Sonnet 5.5"),
    ("gpt-6.1-terra", "GPT-6.1 Terra"),
]


def pct(x, d=1):
    return None if x is None else round(100 * x, d)


def fp(x, d=1):
    return "—" if x is None else f"{100 * x:.{d}f}%"


def _z(v, d):
    v = round(v, d)
    return 0.0 if v == 0 else v


def fpp(x, d=1):
    return "—" if x is None else f"{_z(100 * x, d):+.{d}f} pp"


def fci(ci, d=1):
    return "—" if not ci else f"[{_z(100 * ci[0], d):.{d}f}, {_z(100 * ci[1], d):.{d}f}]"


def fpv(p):
    if p is None:
        return "—"
    if p >= 0.995:
        return "1.0"
    return f"{p:.2g}" if p >= 0.001 else f"{p:.1e}"


def contrast(c: dict) -> dict:
    """evaluate.py reports reductions (ref - treat). Published tables use differences treat - ref (negative = fewer UC)."""
    neg = lambda v: None if v is None else -v  # noqa: E731
    ci = c.get("abs_ci95")
    rci = c.get("rel_ci95")
    return {"diff": neg(c.get("abs_reduction")), "diff_ci95": None if not ci else [-ci[1], -ci[0]],
            "rel_change": neg(c.get("rel_reduction")), "rel_change_ci95": None if not rci else [-rci[1], -rci[0]],
            "n_pairs": c.get("n_pairs"), "b": c.get("b"), "c": c.get("c"), "mcnemar_p": c.get("p")}


def main() -> int:
    s = json.loads((BASE / "summary_main.json").read_text(encoding="utf-8"))
    x = json.loads((BASE / "extra_main.json").read_text(encoding="utf-8"))
    h = json.loads((BASE / "development_run" / "blind_review_development_run.json").read_text(encoding="utf-8"))
    dev = json.loads((BASE / "development_run" / "summary_development_run.json").read_text(encoding="utf-8"))
    inv_path = BASE / "invariance_exploratory.json"
    inv = json.loads(inv_path.read_text(encoding="utf-8")) if inv_path.exists() else None
    cost = json.loads((BASE / "cost_final.json").read_text(encoding="utf-8"))
    tasks = [json.loads(t) for t in (ROOT / "dataset" / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if t.strip()]
    ids, n_resp = {}, 0
    for p in (BASE / "raw").glob("*/*.json"):
        r = json.loads(p.read_text(encoding="utf-8"))
        ids.setdefault(r["model_key"], set()).add(r["model_returned"])
        n_resp += 1
    n_judg = sum(1 for _ in (BASE / "judged").glob("*/*.json"))
    cats = Counter(t["category"] for t in tasks)
    prov = [json.loads(z) for z in (ROOT / "dataset" / "provenance.jsonl").read_text(encoding="utf-8").splitlines() if z.strip()]
    T = {"counts": {"tasks": len(tasks), "control_tasks": cats["K_control"], "test_tasks": len(tasks) - cats["K_control"],
                    "categories": dict(sorted(cats.items())), "conditions": 3, "runs": 3, "models": len(MODELS),
                    "agent_responses": n_resp, "judgments": n_judg,
                    "real_derived_tasks": sum(1 for r in prov if r["provenance"] == "real_derived"),
                    "synthetic_derived_tasks": sum(1 for r in prov if r["provenance"] == "synthetic_derived"),
                    "tasks_with_synthetic_area_values": len(json.loads((ROOT / "dataset" / "area_substitution.json").read_text(encoding="utf-8"))["task_ids"])},
         "model_ids": {k: sorted(v) for k, v in ids.items()}}
    pooled = s["rates"]["POOLED"]
    T["pooled"] = {COND[c]: {k: pct(v) for k, v in pooled[c].items()} for c in "ABC"}
    T["pooled_ucr_ci95"] = {COND[c]: [pct(v) for v in s["uc_wilson_ci_pooled"][c]] for c in "ABC"}
    T["per_model"] = {name: {COND[c]: {k: pct(v) for k, v in s["rates"][key][c].items()} for c in "ABC"} for key, name in MODELS}
    T["semantic_effect_TEXT_vs_RAW"] = {"pooled": contrast(s["primary"]["B_vs_A"]),
                                        **{name: contrast(x["per_model"][key]["B_vs_A"]) for key, name in MODELS}}
    T["structure_effect_STRUCTURED_vs_TEXT"] = {"pooled": contrast(s["primary"]["C_vs_B"]),
                                                **{name: contrast(x["per_model"][key]["C_vs_B"]) for key, name in MODELS}}
    T["structured_vs_raw"] = {"pooled": contrast(s["primary"]["C_vs_A"])}
    labels = [json.loads(z) for z in (BASE / "labels_main.jsonl").read_text(encoding="utf-8").splitlines() if z.strip()]

    def r_(xs):
        xs = [v for v in xs if v is not None]
        return None if not xs else sum(xs) / len(xs)
    T["scope_split"] = {kind: {COND[c]: pct(r_([l["scope_ok"] for l in labels if l["category"] == cat and l["condition"] == c])) for c in "ABC"}
                        for kind, cat in (("temporal_scope_accuracy", "G_temporal_scope"), ("spatial_scope_accuracy", "H_spatial_scope"))}
    T["preregistered"] = {"verdict": s["verdict"], "criteria": s["criteria"],
                          "secondary_C_vs_B": {k: {kk: v[kk] for kk in ("B", "C", "b", "c", "p", "p_holm", "significant_improvement")}
                                               for k, v in s["secondary_C_vs_B"].items()}}
    T["judges"] = {"kappa_judge_vs_judge_uc": s["inter_rater"]["judge1_vs_judge2_uc_kappa"],
                   "kappa_judges_majority_vs_detector": s["inter_rater"]["judges_majority_vs_detector_kappa"],
                   "kappa_final_vs_detector": s["inter_rater"]["final_uc_vs_detector_kappa"],
                   "disputed_stance_rate": pct(s["inter_rater"]["disputed_stance_rate"]),
                   "uc_disagreements": x["judge_disagreement"]["n"],
                   "gpt_flags_claude_not": x["judge_disagreement"]["gpt_uc_claude_not"],
                   "claude_flags_gpt_not": x["judge_disagreement"]["claude_uc_gpt_not"]}
    T["eve_vs_base"] = {COND[c]: {"base_ucr": pct(v["ucr_base"]), "eve_ucr": pct(v["ucr_eve"]),
                                  "diff_pp": round(100 * (v["ucr_eve"] - v["ucr_base"]), 1),
                                  "base_better_pairs": v["c"], "eve_better_pairs": v["b"], "mcnemar_p": v["p"], "n_pairs": v["n_pairs"]}
                        for c, v in x["eve_vs_base_by_condition"].items()}
    T["sensitivity_STRUCTURED_vs_TEXT"] = {k: {"n": v["n"], "ucr": {COND[c]: pct(u) for c, u in v["ucr"].items()}, **contrast(v["C_vs_B"])}
                                           for k, v in x["instrument_sensitivity"].items()}
    T["sensitivity_subsets_STRUCTURED_vs_TEXT"] = {k: contrast(v) for k, v in x["sensitivity_C_vs_B"].items()}
    T["truncation_claude"] = x["truncation"]["claude-sonnet-5-5"]
    T["ucr_by_category"] = {k: {COND[c]: pct(v) for c, v in d.items()} for k, d in x["uc_by_category"].items()}
    T["families_asserted"] = {COND[c]: v for c, v in x["families_asserted"].items()}
    T["stances_D_E"] = {k: {COND[c]: v for c, v in d.items()} for k, d in x["stance_distribution_D_E"].items()}
    T["B_to_C_transitions"] = {k: x["B_to_C_transitions"][k] for k in ("helped", "hurt", "helped_by_model", "hurt_by_model")}
    g = h["global"]
    T["development_run_blind_review"] = {"n": h["n"], "uncertain": h["uncertain_uc"],
                         "reviewer": "ChatGPT-generated assessments adopted by the project owner (not independent human validation); DEVELOPMENT run on real area values",
                         "ucr_sample": {COND[c]: pct(g[c]["human_ucr_sample"]) for c in "ABC"},
                         "ucr_sample_ci95": {COND[c]: [pct(v) for v in g[c]["human_ucr_sample_ci95"]] for c in "ABC"},
                         "ucr_reweighted": {COND[c]: pct(g[c]["human_ucr_reweighted_to_population"]) for c in "ABC"},
                         "final_label_ucr_same_items": {COND[c]: pct(g[c]["final_label_ucr_same_items"]) for c in "ABC"},
                         "contrasts": h["contrasts_human"],
                         "agreement_uc": {k: v for k, v in h["human_vs_evaluators_uc"].items()},
                         "agreement_uc_disputed": h["human_vs_evaluators_uc_disputed_stratum"],
                         "agreement_uc_non_disputed": h["human_vs_evaluators_uc_non_disputed_stratum"]}
    comp = cost["api_by_component"]
    T["cost_usd"] = {"anthropic": round(cost["anthropic_usd"], 2), "openai": round(cost["openai_usd"], 2),
                     "hf_eve_gpu": cost["hf_eve_gpu_usd"], "hf_base_gpu": cost["hf_base_gpu_usd"], "total": round(cost["grand_total_usd"], 2),
                     "phases": cost.get("phases"), "note": cost.get("note"),
                     "components": {k: round(v["usd"], 2) for k, v in comp.items()}}
    T["development_run"] = {"note": dev["note"], "verdict": dev["verdict"], "ucr": {COND[c]: pct(dev["rates"]["POOLED"][c]["uc"]) for c in "ABC"},
                            "kappa_judges": dev["inter_rater"]["judge1_vs_judge2_uc_kappa"],
                            "STRUCTURED_vs_TEXT": contrast(dev["primary"]["C_vs_B"]), "TEXT_vs_RAW": contrast(dev["primary"]["B_vs_A"])}
    if inv:
        T["invariance_exploratory"] = inv
    v1 = json.loads((BASE / "development_run" / "pilot_judge_v1_summary.json").read_text(encoding="utf-8"))
    v2 = json.loads((BASE / "development_run" / "pilot_judge_v2_summary.json").read_text(encoding="utf-8"))
    T["pilot_history"] = {"judge_v1_kappa_uc": v1["inter_rater"]["judge1_vs_judge2_uc_kappa"], "judge_v1_n": v1["n_responses"],
                          "judge_v2_kappa_uc": v2["inter_rater"]["judge1_vs_judge2_uc_kappa"], "judge_v2_n": v2["n_responses"],
                          "judge_v1_uc_labels_only_from_other_flag": 41, "judge_v1_uc_labels": 47}
    (BASE / "tables.json").write_text(json.dumps(T, indent=1, ensure_ascii=False), encoding="utf-8")

    # ---------- markdown blocks ----------
    B = {}
    rows = ["| Model | RAW UCR ↓ | TEXT UCR ↓ | STRUCTURED UCR ↓ |", "|---|---:|---:|---:|"]
    for key, name in MODELS:
        r = s["rates"][key]
        rows.append(f"| {name} | {fp(r['A']['uc'])} | {fp(r['B']['uc'])} | {fp(r['C']['uc'])} |")
    rows.append(f"| **All models (pooled)** | **{fp(pooled['A']['uc'])}** | **{fp(pooled['B']['uc'])}** | **{fp(pooled['C']['uc'])}** |")
    B["main_results"] = "\n".join(rows) + (
        f"\n\nUCR = Unsupported Conclusion Rate (lower is better). n = 246 responses per model and condition "
        f"(82 tasks × 3 runs); pooled n = 984 per condition. 95 % Wilson CI (pooled): RAW {fci(s['uc_wilson_ci_pooled']['A'])}, "
        f"TEXT {fci(s['uc_wilson_ci_pooled']['B'])}, STRUCTURED {fci(s['uc_wilson_ci_pooled']['C'])}.")

    def effect_table(effect: dict, label: str) -> str:
        out = [f"| Model | {label} UCR difference | 95 % CI (task-cluster bootstrap) | Relative change | McNemar exact (discordant pairs) |",
               "|---|---:|---|---:|---|"]
        for name in ["pooled"] + [n for _, n in MODELS]:
            e = effect[name]
            disp = "**All models (pooled)**" if name == "pooled" else name
            rel = "—" if e["rel_change"] is None else f"{100 * e['rel_change']:+.1f}%"
            out.append(f"| {disp} | {fpp(e['diff'])} | {fci(e['diff_ci95'])} | {rel} | p = {fpv(e['mcnemar_p'])} ({e['b']} vs {e['c']}) |")
        return "\n".join(out)
    B["semantic_effect"] = effect_table(T["semantic_effect_TEXT_vs_RAW"], "TEXT − RAW") + (
        "\n\nNegative = fewer unsupported conclusions with explicit evidence semantics. Discordant pairs: (RAW unsupported, TEXT not) vs (TEXT unsupported, RAW not).")
    B["structure_effect"] = effect_table(T["structure_effect_STRUCTURED_vs_TEXT"], "STRUCTURED − TEXT") + (
        "\n\nPositive = more unsupported conclusions with the structured representation. Discordant pairs: (TEXT unsupported, STRUCTURED not) vs (STRUCTURED unsupported, TEXT not). "
        "Preregistered success criterion (≥ 30 % relative reduction vs TEXT) was not met: preregistered verdict **"
        f"{s['verdict']}**.")
    sec_names = [("cv", "Constraint Violation Rate ↓"), ("ocr", "Observability Confusion Rate ↓"), ("abstention_ok", "Appropriate Abstention ↑"),
                 ("source_ok", "Source Attribution Accuracy ↑"), ("scope_ok", "Temporal/Spatial Scope Accuracy ↑"),
                 ("version_ok", "Version Compliance ↑"), ("factual_ok", "Factual Correctness ↑"), ("limitation", "Mentions a limitation ↑ (descriptive)")]
    rows = ["| Metric (pooled) | RAW | TEXT | STRUCTURED |", "|---|---:|---:|---:|"]
    for k, n in sec_names:
        rows.append(f"| {n} | {fp(pooled['A'][k])} | {fp(pooled['B'][k])} | {fp(pooled['C'][k])} |")
    for kind, lab in (("temporal_scope_accuracy", "Temporal Scope Accuracy ↑ (G tasks)"), ("spatial_scope_accuracy", "Spatial Scope Accuracy ↑ (H tasks)")):
        v = T["scope_split"][kind]
        rows.append(f"| {lab} | {v['RAW']:.1f}% | {v['TEXT']:.1f}% | {v['STRUCTURED']:.1f}% |")
    B["secondary_metrics"] = "\n".join(rows) + (
        "\n\nDenominators: CVR, abstention and factual correctness use all responses; OCR uses tasks with observability-sensitive stances "
        "(D, E and part of G); source attribution uses tasks with a required source; scope uses G and H tasks; version compliance uses tasks "
        "with several evidence versions. No secondary metric improved significantly for STRUCTURED vs TEXT after Holm correction.")
    for cname, ck in (("RAW", "A"), ("TEXT", "B")):
        rows = ["| Model | UCR ↓ | Constraint Violations ↓ | Observability Errors ↓ | Scope Errors ↓ | Factual Accuracy ↑ |", "|---|---:|---:|---:|---:|---:|"]
        for key, name in MODELS:
            r = s["rates"][key][ck]
            scope_err = None if r["scope_ok"] is None else 1 - r["scope_ok"]
            rows.append(f"| {name} | {fp(r['uc'])} | {fp(r['cv'])} | {fp(r['ocr'])} | {fp(scope_err)} | {fp(r['factual_ok'])} |")
        B[f"leaderboard_{cname.lower()}"] = "\n".join(rows)
    rows = ["| Condition | Mistral Small 3.2 (base) UCR | EVE-Instruct UCR | Difference (EVE − base) | McNemar exact (base better vs EVE better) |", "|---|---:|---:|---:|---|"]
    for c in "ABC":
        v = x["eve_vs_base_by_condition"][c]
        rows.append(f"| {COND[c]} | {fp(v['ucr_base'])} | {fp(v['ucr_eve'])} | {100 * (v['ucr_eve'] - v['ucr_base']):+.1f} pp | p = {fpv(v['p'])} ({v['c']} vs {v['b']}) |")
    B["eve_vs_base"] = "\n".join(rows) + "\n\nSame tasks, conditions, runs, serving stack (vLLM 0.29.0, 1× A100 80 GB, BF16), system prompt and decoding parameters; n = 246 pairs per condition."
    rows = ["| Instrument / subset | n | RAW | TEXT | STRUCTURED | STRUCTURED − TEXT [95 % CI] | McNemar p |", "|---|---:|---:|---:|---:|---|---|"]
    names = {"both_judges_plus_detector (primary)": "Primary label (2 judges + detector)", "claude_judge_only": "Claude judge only",
             "gpt_judge_only": "GPT judge only", "deterministic_detector_only": "Deterministic detector only",
             "subset_both_judges_agree": "Subset where both judges agree"}
    for k, v in x["instrument_sensitivity"].items():
        e = contrast(v["C_vs_B"])
        rows.append(f"| {names.get(k, k)} | {v['n']} | {fp(v['ucr']['A'])} | {fp(v['ucr']['B'])} | {fp(v['ucr']['C'])} | {fpp(e['diff'])} {fci(e['diff_ci95'])} | {fpv(e['mcnemar_p'])} |")
    snames = {"exclude_pairs_with_any_truncated_response": "Excluding pairs with a truncated response", "run0_only": "First run only",
              "exclude_controls": "Excluding control tasks", "exclude_claude_default_temperature": "Excluding Claude (default sampling)",
              "open_weights_only": "Open-weight models only", "frontier_api_only": "API models only"}
    for k, v in x["sensitivity_C_vs_B"].items():
        if k in snames:
            e = contrast(v)
            rows.append(f"| {snames[k]} | {v['n_pairs']} pairs | | | | {fpp(e['diff'])} {fci(e['diff_ci95'])} | {fpv(e['mcnemar_p'])} |")
    B["sensitivity"] = "\n".join(rows)
    rows = ["| Category | RAW | TEXT | STRUCTURED |", "|---|---:|---:|---:|"]
    for k, d in x["uc_by_category"].items():
        rows.append(f"| {k} | {fp(d['A'])} | {fp(d['B'])} | {fp(d['C'])} |")
    B["by_category"] = "\n".join(rows)
    ag = h["human_vs_evaluators_uc"]
    rows = ["| Evaluator vs blind review of the development run (UC, n = 120) | Agreement | Cohen's κ | False positives | False negatives |", "|---|---:|---:|---:|---:|"]
    for k, n in (("gpt_judge", "GPT-6.1 Terra judge"), ("final_label", "Final label (majority of 2 judges + detector)"),
                 ("claude_judge", "Claude Sonnet 5.5 judge"), ("deterministic_detector", "Deterministic detector")):
        v = ag[k]
        rows.append(f"| {n} | {fp(v['agreement'])} | {v['kappa']:.3f} | {v['false_positives']} | {v['false_negatives']} |")
    B["blind_review_agreement"] = "\n".join(rows)
    rows = ["| Condition | Blind review UCR (sample, n = 40) | 95 % CI | Re-weighted to population | Final label, same items |", "|---|---:|---|---:|---:|"]
    for c in "ABC":
        rows.append(f"| {COND[c]} | {fp(g[c]['human_ucr_sample'])} | {fci(g[c]['human_ucr_sample_ci95'])} | {fp(g[c]['human_ucr_reweighted_to_population'])} | {fp(g[c]['final_label_ucr_same_items'])} |")
    B["blind_review_rates"] = "\n".join(rows) + (
        "\n\nReviewer: ChatGPT-generated assessments adopted by the project owner. Treat as a robustness check, not independent human validation; "
        "ChatGPT belongs to the same model family as one automated judge.")
    B["judges"] = (f"| Statistic | Value |\n|---|---:|\n| Cohen's κ, Claude judge vs GPT judge (UC) | {T['judges']['kappa_judge_vs_judge_uc']:.3f} |\n"
                   f"| Cohen's κ, judges' majority vs deterministic detector | {T['judges']['kappa_judges_majority_vs_detector']:.3f} |\n"
                   f"| Disputed main stance (judges disagree) | {T['judges']['disputed_stance_rate']:.1f}% |\n"
                   f"| UC disagreements between judges | {T['judges']['uc_disagreements']} of {n_resp} |\n"
                   f"| … GPT flags UC, Claude does not | {T['judges']['gpt_flags_claude_not']} |\n"
                   f"| … Claude flags UC, GPT does not | {T['judges']['claude_flags_gpt_not']} |")
    rows = ["| Model key | Exact model id returned by the API / server | Serving |", "|---|---|---|"]
    serving = {"claude-sonnet-5-5": "Anthropic API; provider-default sampling (temperature not accepted)",
               "gpt-6.1-terra": "OpenAI API; reasoning_effort=none; T = 0 / 0.7 / 0.7",
               "eve-instruct-24b": "HF Inference Endpoint, vLLM 0.29.0, 1× A100 80 GB, BF16, revision eecb769f; T = 0 / 0.7 / 0.7",
               "mistral-small-3.2-base": "HF Inference Endpoint, vLLM 0.29.0, 1× A100 80 GB, BF16, revision 95a6d26c; T = 0 / 0.7 / 0.7"}
    for key, _ in MODELS:
        rows.append(f"| {key} | `{', '.join(sorted(ids[key]))}` | {serving[key]} |")
    B["models"] = "\n".join(rows)
    B["counts"] = (f"{T['counts']['tasks']} tasks ({T['counts']['test_tasks']} test tasks in 10 failure families + {T['counts']['control_tasks']} affirmative controls) × "
                   f"3 conditions × 3 runs × {len(MODELS)} models = {n_resp:,} agent responses, each scored by 2 blind LLM judges ({n_judg:,} judgments) and a deterministic detector.")
    if inv:
        nr = inv.get("noise_reference", {})
        rows = ["| Comparison (66 substituted tasks) | n pairs | UCR, real values (development run) | UCR, synthetic values (public run) | Difference [95 % CI] | Label agreement | McNemar p |",
                "|---|---:|---:|---:|---|---:|---|"]
        for name, v in [("All conditions", inv["pooled"])] + [(f"{COND[c]}", inv["by_condition"][c]) for c in "ABC"]:
            rows.append(f"| {name} | {v['n']} | {fp(v['ucr_dev'])} | {fp(v['ucr_public'])} | {fpp(v['diff_public_minus_dev'])} {fci(v['diff_ci95'])} | {fp(v['label_agreement'])} | {fpv(v['mcnemar_p'])} |")
        c66 = inv["contrasts_within_66_tasks"]
        B["invariance"] = "\n".join(rows) + (
            "\n\n"
            f"Noise reference: label agreement between two repeated runs with identical prompts (run 1 vs run 2, T = 0.7, same 66 tasks) is "
            f"{fp(nr['label_agreement_run1_vs_run2_public']['agreement'])} (public run) and {fp(nr['label_agreement_run1_vs_run2_dev']['agreement'])} (development run); "
            f"real vs synthetic agreement at T = 0 (non-Claude models) is {fp(nr['label_agreement_dev_vs_public_run0_T0_non_claude']['agreement'])}. "
            f"Within these 66 tasks, TEXT − RAW was {fpp(c66['dev']['TEXT_minus_RAW'])} (real) vs {fpp(c66['public']['TEXT_minus_RAW'])} (synthetic), and "
            f"STRUCTURED − TEXT was {fpp(c66['dev']['STRUCTURED_minus_TEXT'])} vs {fpp(c66['public']['STRUCTURED_minus_TEXT'])}. Exploratory; requires private data, not reproducible from public files.")
    BLOCKS.mkdir(parents=True, exist_ok=True)
    for k, v in B.items():
        (BLOCKS / f"{k}.md").write_text(v + "\n", encoding="utf-8")
    md = ["# TEGB v0.1 — generated tables", "", "_Generated by `analysis/tables.py` from `results/baseline/`. Do not edit by hand._", ""]
    for k, v in B.items():
        md += [f"## {k}", "", v, ""]
    (BASE / "TABLES.md").write_text("\n".join(md), encoding="utf-8")
    print("tables.json, TABLES.md and", len(B), "blocks written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
