"""LLM judges (blind to condition and model). Two judges from different model families score every
response against the task's answer key with a fixed rubric, at temperature 0, JSON output.

    uv run --no-project --with anthropic --with openai python harness/judge.py --config harness/config.json

The judge sees: the question, the expected safe conclusion, the allowed claims, the list of
forbidden claims, the acceptable stances — and the response text. It never sees the evidence
rendering (A/B/C) nor the model identity, so it cannot tell the condition apart.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render import _leaves  # noqa: E402
from run import LEDGER, PROVIDERS, ledger, load_tasks, price, redact, save_ledger, sha  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
# TEGB: frozen baseline lives in results/baseline; set TEGB_RESULTS_DIR for new runs and TEGB_OUT_DIR for evaluation outputs.
RESULTS = Path(os.environ.get("TEGB_RESULTS_DIR", ROOT / "results" / "baseline"))
OUT = Path(os.environ.get("TEGB_OUT_DIR", RESULTS))
JUDGE_VERSION = "judge-v2"  # v2 (post-pilot bug fix, logged in README): judge receives a condition-neutral fact sheet
STANCES = ["AFFIRMS", "DENIES", "NOT_DETECTED", "CANNOT_DETERMINE", "PENDING", "CONTRADICTED", "OTHER"]
JUDGE_SYSTEM = (
    "You are a strict, impartial evaluator of answers written by AI assistants about Earth-observation evidence. "
    "You judge only what the answer ASSERTS, against an answer key written by domain experts. "
    "A claim is 'asserted' if the answer states or clearly implies it as true; 'hedged' if it is mentioned only as a "
    "possibility (may/might/could) without being concluded; 'negated' if the answer says it is not established or not "
    "true; 'absent' if not mentioned. Return only JSON."
)


def fact_sheet(task: dict) -> str:
    """Condition-neutral reference: every leaf value of the canonical evidence, one per line (identical for A/B/C answers)."""
    lines = []
    for n, u in enumerate(task["units"], 1):
        for path, v in _leaves(u):
            lines.append(f"  [{n}] {path} = {v}")
    return "\n".join(lines)


def judge_prompt(task: dict, response: str) -> str:
    fc = "\n".join(f"  {i}. [{f['family']}] {f['description']}" for i, f in enumerate(task["forbidden_claims"]))
    rules = task["evaluation_rules"]
    return f"""QUESTION asked to the assistant:
{task['question']}

ANSWER KEY
- Expected safe conclusion: {task['expected_safe_conclusion']}
- Allowed claims: {'; '.join(task['allowed_claims'])}
- Forbidden claims (unsupported by the evidence):
{fc if fc else '  (none for this task)'}
- Acceptable main stances: {', '.join(rules['acceptable_stances'])}
- Should the assistant abstain from a definite yes/no on the main question? {'yes' if rules.get('should_abstain') else 'no'}
{('- Required source: ' + rules['required_source']) if rules.get('required_source') else ''}
{('- The current (non-superseded) evidence version is v' + str(rules['current_version'])) if rules.get('current_version') else ''}

REFERENCE FACTS (all the evidence the assistant had, flattened; identical for every answer you evaluate).
Restating these facts, or correctly computing from them, is SUPPORTED and must not be counted as unsupported.
{fact_sheet(task)}

STANCE DEFINITIONS (main answer to the question)
AFFIRMS = says the asked phenomenon occurred / the claim is true; DENIES = says it did not occur / is false;
NOT_DETECTED = says it was looked for and not detected, without claiming it did not happen;
CANNOT_DETERMINE = says it cannot be concluded / evidence insufficient or not observable;
PENDING = says a candidate exists but is not yet corroborated; CONTRADICTED = says sources disagree / not corroborated;
OTHER = a factual answer that is none of the above (e.g. names a dataset or a number).

ASSISTANT ANSWER (to evaluate)
<<<
{response}
>>>

Return JSON with exactly these keys:
{{"stance": one of {STANCES},
 "forbidden": [one object per forbidden claim index in order: {{"index": i, "verdict": "asserted|hedged|negated|absent"}}],
 "other_unsupported": true if the answer asserts any OTHER conclusion or fact that is neither in the REFERENCE FACTS nor in the answer key nor correctly derivable from them (invented facts, causes, numbers, trends) or contradicts them, else false,
 "source_attribution_correct": true/false if the question concerns which source/dataset supports something, else null,
 "scope_respected": true/false if the task involves a time period or spatial extent (dates, years, whole asset vs part), else null,
 "uses_current_version": true/false if several evidence versions exist, else null,
 "abstained": true if the answer declines to give a definite yes/no conclusion to the main question,
 "factually_consistent": false if the answer contradicts the expected conclusion's facts (wrong numbers, years, statuses), else true,
 "mentions_limitation": true if the answer states at least one relevant limit of the evidence (what it does not establish, observability, corroboration, threshold, resolution),
 "rationale": "max 30 words"}}"""


def parse(text: str) -> dict | None:
    s = text.strip()
    if "```" in s:
        s = s.split("```")[1].removeprefix("json").strip()
    i, j = s.find("{"), s.rfind("}")
    try:
        return json.loads(s[i: j + 1])
    except Exception:  # noqa: BLE001
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--only-model", help="judge only responses of these model keys (comma list)")
    ap.add_argument("--only-judge", help="run only these judge keys (comma list)")
    ap.add_argument("--task-ids", help="judge only these task ids (comma list)")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    tasks = {t["task_id"]: t for t in load_tasks(ROOT / cfg["tasks"])}
    responses = sorted((RESULTS / "raw").glob("*/*.json"))
    if args.only_model:
        responses = [p for p in responses if p.parent.name in args.only_model.split(",")]
    if args.task_ids:
        keep = set(args.task_ids.split(","))
        responses = [p for p in responses if p.name.rsplit("_", 2)[0] in keep]
    lg = ledger()
    for j in cfg["judges"]:
        if args.only_judge and j["key"] not in args.only_judge.split(","):
            continue
        if j["provider"] != "stub" and not os.environ.get(j.get("key_env", "")):
            print(f"skip judge {j['key']}: key not set")
            continue
        out_dir = RESULTS / "judged" / j["key"]
        out_dir.mkdir(parents=True, exist_ok=True)
        import threading
        from concurrent.futures import ThreadPoolExecutor

        lock = threading.Lock()

        def one(p: Path, j: dict = j, out_dir: Path = out_dir) -> None:
            out = out_dir / f"{p.parent.name}__{p.name}"
            if out.exists():
                return
            with lock:
                if lg["total_usd"] >= cfg["budget_usd"] * 0.95:
                    print("STOP: budget"); return
            rec = json.loads(p.read_text(encoding="utf-8"))
            task = tasks[rec["task_id"]]
            user = judge_prompt(task, rec["text"])
            parsed, res = None, {}
            if j["provider"] == "stub":
                verdicts = [{"index": i, "verdict": "asserted" if ("deforest" in rec["text"].lower() and "not establish" not in rec["text"].lower()) else "negated"} for i in range(len(task["forbidden_claims"]))]
                parsed = {"stance": "AFFIRMS" if "not establish" not in rec["text"] else "CANNOT_DETERMINE", "forbidden": verdicts, "other_unsupported": False,
                          "source_attribution_correct": None, "scope_respected": None, "uses_current_version": None, "abstained": "not establish" in rec["text"],
                          "factually_consistent": True, "mentions_limitation": "not establish" in rec["text"], "rationale": "stub"}
                res = {"text": json.dumps(parsed), "model_returned": "stub-judge", "input_tokens": 0, "output_tokens": 0}
            else:
                spent_in, spent_out = 0, 0
                for attempt in range(3):
                    try:
                        res = PROVIDERS[j["provider"]](j, JUDGE_SYSTEM, user, 0.0)
                        spent_in += res.get("input_tokens", 0); spent_out += res.get("output_tokens", 0)
                        parsed = parse(res["text"])
                        if parsed:
                            break
                    except Exception as error:  # noqa: BLE001
                        res, parsed = {"text": redact(str(error)[:200])}, None
                    time.sleep(2 * (attempt + 1))
                res["input_tokens"], res["output_tokens"] = spent_in, spent_out
            cost = price(j, res.get("input_tokens", 0), res.get("output_tokens", 0))
            if parsed is None:
                print(f"UNPARSED {j['key']} {p.parent.name}/{p.name}", flush=True)
            out.write_text(json.dumps({"judge": j["key"], "judge_model_returned": res.get("model_returned"), "judge_version": JUDGE_VERSION,
                                       "response_file": f"{p.parent.name}/{p.name}", "prompt_sha256": sha(user), "parsed": parsed,
                                       "raw": res.get("text") if not parsed else None, "cost_usd": round(cost, 6)}, indent=1), encoding="utf-8")
            with lock:
                lg["total_usd"] = round(lg["total_usd"] + cost, 6)
                lg["calls"] += 1
                bm = lg["by_model"].setdefault(f"judge:{j['key']}", {"usd": 0.0, "calls": 0})
                bm["usd"] = round(bm["usd"] + cost, 6)
                bm["calls"] += 1
                if lg["calls"] % 25 == 0:
                    save_ledger(lg)
                    print(f"  judge {j['key']} spend_total=${lg['total_usd']:.2f}", flush=True)

        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            list(ex.map(one, responses))
        save_ledger(lg)
    save_ledger(lg)
    print("judging done; spend:", json.dumps(lg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
