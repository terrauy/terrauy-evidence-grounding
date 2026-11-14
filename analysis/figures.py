"""Figures for TEGB v0.1, generated only from results/baseline/tables.json and summary/extra outputs.

    uv run --no-project --with matplotlib python analysis/figures.py

Writes analysis/figures/fig{1..6}_*.png (200 dpi) and .svg. Plain academic style; Okabe-Ito colours.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results" / "baseline"
OUT = ROOT / "analysis" / "figures"
T = json.loads((BASE / "tables.json").read_text(encoding="utf-8"))
X = json.loads((BASE / "extra_main.json").read_text(encoding="utf-8"))
S = json.loads((BASE / "summary_main.json").read_text(encoding="utf-8"))
CONDS = ["RAW", "TEXT", "STRUCTURED"]
COL = {"RAW": "#E69F00", "TEXT": "#0072B2", "STRUCTURED": "#009E73"}
MODELS = ["EVE-Instruct", "Mistral Small 3.2", "Claude Sonnet 5.5", "GPT-6.1 Terra"]
KEYS = {"EVE-Instruct": "eve-instruct-24b", "Mistral Small 3.2": "mistral-small-3.2-base", "Claude Sonnet 5.5": "claude-sonnet-5-5", "GPT-6.1 Terra": "gpt-6.1-terra"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#dddddd", "grid.linewidth": 0.6, "axes.axisbelow": True,
                     "savefig.bbox": "tight", "figure.dpi": 100})
NOTE = "TEGB v0.1 baseline (4 models × 82 tasks × 3 runs). UCR = unsupported conclusion rate; lower is better."


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.png", dpi=200)
    fig.savefig(OUT / f"{name}.svg")
    plt.close(fig)


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return c - h, c + h


# Fig 1: pooled UCR by condition
fig, ax = plt.subplots(figsize=(4.2, 3.2))
vals = [T["pooled"][c]["uc"] for c in CONDS]
ci = [T["pooled_ucr_ci95"][c] for c in CONDS]
ax.bar(CONDS, vals, color=[COL[c] for c in CONDS], width=0.6)
ax.errorbar(CONDS, vals, yerr=[[v - lo for v, (lo, hi) in zip(vals, ci)], [hi - v for v, (lo, hi) in zip(vals, ci)]],
            fmt="none", ecolor="black", capsize=3, lw=0.8)
for i, v in enumerate(vals):
    ax.text(i, v + 3.5, f"{v:.1f}%", ha="center")
ax.set_ylabel("UCR (%)")
ax.set_ylim(0, 60)
ax.set_title("Fig. 1  Unsupported conclusions by condition (pooled)", loc="left", fontsize=9)
ax.text(0, -0.2, "n = 984 responses per condition; error bars: 95% Wilson CI.", transform=ax.transAxes, fontsize=7, color="#555")
save(fig, "fig1_ucr_by_condition")

# Fig 2: UCR by model and condition
fig, ax = plt.subplots(figsize=(6.4, 3.3))
w = 0.26
for j, c in enumerate(CONDS):
    xs = [i + (j - 1) * w for i in range(len(MODELS))]
    ys = [T["per_model"][m][c]["uc"] for m in MODELS]
    los, his = [], []
    for m, y in zip(MODELS, ys):
        lo, hi = wilson(round(y * 246 / 100), 246)
        los.append(y - 100 * lo)
        his.append(100 * hi - y)
    ax.bar(xs, ys, width=w, color=COL[c], label=c)
    ax.errorbar(xs, ys, yerr=[los, his], fmt="none", ecolor="black", capsize=2, lw=0.6)
ax.set_xticks(range(len(MODELS)), MODELS)
ax.set_ylabel("UCR (%)")
ax.set_ylim(0, 100)
ax.legend(frameon=False, ncol=3, loc="upper right")
ax.set_title("Fig. 2  UCR by model and condition", loc="left", fontsize=9)
ax.text(0, -0.17, "n = 246 per bar (82 tasks × 3 runs); error bars: 95% Wilson CI.", transform=ax.transAxes, fontsize=7, color="#555")
save(fig, "fig2_ucr_by_model_condition")


def effect_plot(key, title, fname, note):
    fig, ax = plt.subplots(figsize=(5.2, 2.9))
    names = ["pooled"] + MODELS
    labels = ["All models (pooled)"] + MODELS
    for i, n in enumerate(names):
        e = T[key][n]
        d = round(100 * e["diff"], 1) + 0.0
        d = 0.0 if d == 0 else d
        lo, hi = (100 * e["diff_ci95"][0], 100 * e["diff_ci95"][1]) if e["diff_ci95"] else (d, d)
        ax.errorbar([d], [i], xerr=[[d - lo], [hi - d]], fmt="o", color="black" if n == "pooled" else "#444", capsize=3, ms=5 if n == "pooled" else 4)
        ax.text(max(hi, d) + 1.2, i, f"{d:+.1f} pp", va="center", fontsize=8)
    ax.axvline(0, color="#999", lw=0.8)
    ax.set_yticks(range(len(names)), labels)
    ax.invert_yaxis()
    ax.set_xlabel("Difference in UCR (percentage points)")
    ax.set_title(title, loc="left", fontsize=9)
    ax.text(0, -0.3, note, transform=ax.transAxes, fontsize=7, color="#555")
    xs = [100 * T[key][n]["diff_ci95"][0] for n in names if T[key][n]["diff_ci95"]] + [100 * T[key][n]["diff_ci95"][1] for n in names if T[key][n]["diff_ci95"]]
    ax.set_xlim(min(xs + [0]) - 3, max(xs + [0]) + 7)
    save(fig, fname)


effect_plot("semantic_effect_TEXT_vs_RAW", "Fig. 3  Effect of explicit evidence semantics (TEXT − RAW)", "fig3_semantic_effect",
            "Paired by task and run; 95% CI from task-cluster bootstrap (4,000 resamples). Negative = fewer unsupported conclusions.")
effect_plot("structure_effect_STRUCTURED_vs_TEXT", "Fig. 4  Effect of structured representation (STRUCTURED − TEXT)", "fig4_structure_effect",
            "Paired by task and run; 95% CI from task-cluster bootstrap. Positive = more unsupported conclusions with STRUCTURED.")

# Fig 5: UCR by failure category and condition
cats = list(T["ucr_by_category"].keys())
pretty = {c: c.split("_", 1)[1].replace("_", " ") for c in cats}
fig, ax = plt.subplots(figsize=(6.4, 4.2))
h = 0.26
for j, c in enumerate(CONDS):
    ys = [i + (j - 1) * h for i in range(len(cats))]
    ax.barh(ys, [T["ucr_by_category"][k][c] for k in cats], height=h, color=COL[c], label=c)
ax.set_yticks(range(len(cats)), [f"{k[0]}  {pretty[k]}" for k in cats])
ax.invert_yaxis()
ax.set_xlabel("UCR (%)")
ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0))
ax.set_title("Fig. 5  UCR by task family and condition (pooled over models)", loc="left", fontsize=9)
ax.text(0, -0.17, "K = affirmative controls. Category sizes 6–10 tasks; n per bar = tasks × 4 models × 3 runs.", transform=ax.transAxes, fontsize=7, color="#555")
save(fig, "fig5_ucr_by_category")

# Fig 6: EVE vs base
fig, ax = plt.subplots(figsize=(4.8, 3.2))
w = 0.36
for j, (lab, k, col) in enumerate((("Mistral Small 3.2 (base)", "base_ucr", "#999999"), ("EVE-Instruct", "eve_ucr", "#CC79A7"))):
    xs = [i + (j - 0.5) * w for i in range(3)]
    ys = [T["eve_vs_base"][c][k] for c in CONDS]
    ax.bar(xs, ys, width=w, color=col, label=lab)
    for x_, y_ in zip(xs, ys):
        ax.text(x_, y_ + 1.5, f"{y_:.1f}", ha="center", fontsize=7)
ax.set_xticks(range(3), CONDS)
ax.set_ylabel("UCR (%)")
ax.set_ylim(0, 95)
ax.legend(frameon=False)
ax.set_title("Fig. 6  EVE-Instruct vs its base model", loc="left", fontsize=9)
ax.text(0, -0.2, "Same prompts, serving stack and decoding; n = 246 paired responses per condition.", transform=ax.transAxes, fontsize=7, color="#555")
save(fig, "fig6_eve_vs_base")
print("6 figures written to", OUT.relative_to(ROOT))
