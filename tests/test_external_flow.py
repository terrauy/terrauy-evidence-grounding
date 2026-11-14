"""Simulates an external submitter end to end, offline and at zero cost.

    python tests/test_external_flow.py          # or through tests/run_tests.py / pytest

Covers: every adapter type (mock, local program, Python function, OpenAI-compatible HTTP against a local fake
server), run -> score -> submit -> validate -> leaderboard, tamper detection, and the reference path using the
frozen judged baseline. Nothing is written inside the repository and no fake model reaches the leaderboard.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SUBMIT_META = ["--model-name", "Fake Model", "--model-version", "0.0-test", "--provider", "local test", "--submitter", "tegb-tests",
               "--contamination", "unknown", "--i-can-share-outputs"]


def tegb(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "tegb", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                          env={**os.environ, "PYTHONIOENCODING": "utf-8", **(env or {})})


def _rewrite(folder: Path, mutate) -> None:
    """Apply `mutate(submission_dict, responses_list)` and write both files back, keeping hashes consistent."""
    from tegb import core

    sub = json.loads((folder / "submission.json").read_text(encoding="utf-8"))
    rows = core.read_jsonl(folder / "responses.jsonl")
    mutate(sub, rows)
    core.write_jsonl(rows, folder / "responses.jsonl")
    sub["hashes"]["responses_sha256"] = core.sha256_bytes((folder / "responses.jsonl").read_bytes())
    (folder / "submission.json").write_text(json.dumps(sub, indent=1), encoding="utf-8")


def test_scorer_reproduces_official_baseline():
    """`tegb score` on the frozen responses must give exactly the published reference numbers."""
    from tegb import core

    S = json.loads((ROOT / "results" / "baseline" / "summary_main.json").read_text(encoding="utf-8"))
    tasks = core.load_tasks()
    for key in S["models"]:
        responses, judgments, why = core.read_results(core.FROZEN, key)
        assert judgments is not None, why
        ref = core.score(responses, judgments, tasks)["reference"]["by_condition"]
        for c, name in core.CONDITIONS.items():
            pub = S["rates"][key][c]
            for mine, theirs in ((ref[name]["ucr"], pub["uc"]), (ref[name]["constraint_violations"], pub["cv"]),
                                 (ref[name]["observability_errors"], pub["ocr"]), (ref[name]["factual_accuracy"], pub["factual_ok"]),
                                 (ref[name]["scope_errors"], 1 - pub["scope_ok"])):
                assert abs(mine - theirs) < 1e-5, (key, name, mine, theirs)


def test_task_hashes_file_is_current():
    r = tegb("hashes", "--check")
    assert r.returncode == 0, r.stdout + r.stderr


def test_leaderboard_blocks_are_current():
    r = tegb("leaderboard", "--check")
    assert r.returncode == 0, r.stdout + r.stderr


def test_external_submitter_core_flow_and_tamper_detection():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        res, subs = tmp / "results", tmp / "submissions" / "v0.1"
        r = tegb("run", "--adapter", "mock", "--model", "cond_sensitive", "--output", str(res), "--workers", "8")
        assert r.returncode == 0, r.stdout + r.stderr
        assert len(list((res / "raw" / "cond_sensitive").glob("*.json"))) == 738
        r = tegb("score", str(res))
        assert r.returncode == 0 and "CORE detector score" in r.stdout and "not available" in r.stdout, r.stdout + r.stderr
        sc = json.loads((res / "scores" / "score_cond_sensitive.json").read_text(encoding="utf-8"))
        assert sc["complete"] and sc["reference"] is None
        # the fake model overclaims in RAW and TEXT and is careful in STRUCTURED: the detector must see that
        ucr = {c: v["ucr"] for c, v in sc["core"]["by_condition"].items()}
        assert ucr["RAW"] > 0.3 and ucr["TEXT"] > 0.3 and ucr["STRUCTURED"] == 0.0, ucr
        r = tegb("submit", str(res), *SUBMIT_META, "--out", str(subs), "--allow-mock")
        folder = subs / "fake-model"
        assert r.returncode == 0 and (folder / "submission.json").is_file(), r.stdout + r.stderr
        assert tegb("validate", str(folder), "--allow-mock").returncode == 0
        r = tegb("validate", str(folder))  # a mock model must never be accepted
        assert r.returncode == 1 and "mock adapter" in r.stdout
        text = (folder / "submission.json").read_text(encoding="utf-8") + (folder / "responses.jsonl").read_text(encoding="utf-8")
        assert "api_key" not in text.lower() and "authorization" not in text.lower()

        def check_fails(name: str, mutate, needle: str, fix_hash: bool = True) -> None:
            bad = tmp / "tamper" / "v0.1" / "fake-model"
            if bad.parent.exists():
                shutil.rmtree(bad.parent)
            shutil.copytree(folder, bad)
            if fix_hash:
                _rewrite(bad, mutate)
            else:
                mutate(bad)
            rr = tegb("validate", str(bad), "--allow-mock")
            assert rr.returncode == 1 and needle in rr.stdout, (name, rr.stdout[-600:])

        check_fails("edited answer without hash", lambda f: (f / "responses.jsonl").write_text(
            (f / "responses.jsonl").read_text(encoding="utf-8").replace("deforestation", "tree-cover loss"), encoding="utf-8"),
            "responses_sha256", fix_hash=False)
        check_fails("edited answer with hash fixed", lambda s, rows: [r.update(text="The evidence does not establish that.") for r in rows[:300]],
                    "recomputed")
        check_fails("missing output", lambda s, rows: rows.pop(), "missing")
        check_fails("foreign prompt", lambda s, rows: rows[0].update(user_sha256="0" * 64), "prompt hash mismatch")
        check_fails("impossible metric", lambda s, rows: s["metrics"]["core"]["by_condition"]["RAW"].update(ucr=1.7), "not a rate")
        check_fails("better-looking metric", lambda s, rows: s["metrics"]["core"]["by_condition"]["RAW"].update(ucr=0.0), "recomputed")
        check_fails("wrong benchmark version", lambda s, rows: s.update(benchmark_version="v0.2"), "benchmark_version")
        check_fails("other task file", lambda s, rows: s["hashes"].update(tasks_file_sha256="0" * 64), "tasks_file_sha256")
        check_fails("missing metadata", lambda s, rows: s["model"].update(version=""), "model.version")
        check_fails("leaked credential", lambda s, rows: s.update(notes="key sk-" + "a1B2c3D4" * 4), "credential")
        # the maintainers' leaderboard step runs on a private copy and lists the entry there only
        priv = tmp / "private" / "v0.1"
        shutil.copytree(folder, priv / "fake-model")
        sub = json.loads((priv / "fake-model" / "submission.json").read_text(encoding="utf-8"))
        sub["run"]["adapter"] = "command"  # pretend it was a real local model so the leaderboard code path can be exercised
        (priv / "fake-model" / "submission.json").write_text(json.dumps(sub, indent=1), encoding="utf-8")
        r = tegb("leaderboard", "--submissions", str(priv), "--blocks-dir", str(tmp / "blocks"))
        assert r.returncode == 0, r.stdout + r.stderr
        assert "Fake Model" in (tmp / "blocks" / "community_core.md").read_text(encoding="utf-8")
        assert "No external submissions yet." in (tmp / "blocks" / "community_reference.md").read_text(encoding="utf-8")
    assert "No external submissions yet." in (ROOT / "LEADERBOARD.md").read_text(encoding="utf-8")
    assert "Fake Model" not in (ROOT / "LEADERBOARD.md").read_text(encoding="utf-8")


def test_reference_path_with_frozen_judgments():
    """Copy one baseline model with its real judge verdicts, package it and validate the reference metrics."""
    key = "gpt-6.1-terra"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        res = tmp / "results"
        shutil.copytree(ROOT / "results" / "baseline" / "raw" / key, res / "raw" / key)
        for j in ("judge-claude-sonnet-5-5", "judge-gpt-6.1-terra"):
            (res / "judged" / j).mkdir(parents=True)
            for p in (ROOT / "results" / "baseline" / "judged" / j).glob(f"{key}__*.json"):
                shutil.copy(p, res / "judged" / j / p.name)
        r = tegb("submit", str(res), *SUBMIT_META, "--out", str(tmp / "submissions" / "v0.1"))
        folder = tmp / "submissions" / "v0.1" / "fake-model"
        assert r.returncode == 0 and (folder / "judgments.jsonl").is_file(), r.stdout + r.stderr
        sub = json.loads((folder / "submission.json").read_text(encoding="utf-8"))
        S = json.loads((ROOT / "results" / "baseline" / "summary_main.json").read_text(encoding="utf-8"))
        assert abs(sub["metrics"]["reference"]["by_condition"]["RAW"]["ucr"] - S["rates"][key]["A"]["uc"]) < 1e-5
        r = tegb("leaderboard", "--submissions", str(folder.parent), "--blocks-dir", str(tmp / "blocks"))
        assert r.returncode == 0 and "Fake Model" in (tmp / "blocks" / "community_reference.md").read_text(encoding="utf-8"), r.stdout + r.stderr
        # a verdict changed after the fact is caught
        from tegb import core

        rows = core.read_jsonl(folder / "judgments.jsonl")
        rows[0]["parsed"]["stance"] = "AFFIRMS"
        core.write_jsonl(rows, folder / "judgments.jsonl")
        r = tegb("validate", str(folder))
        assert r.returncode == 1 and "judgments_sha256" in r.stdout
        # a judgment that belongs to another answer is caught even if the file hash is fixed
        rows[1]["prompt_sha256"] = "0" * 64
        core.write_jsonl(rows, folder / "judgments.jsonl")
        sub["hashes"]["judgments_sha256"] = core.sha256_bytes((folder / "judgments.jsonl").read_bytes())
        (folder / "submission.json").write_text(json.dumps(sub, indent=1), encoding="utf-8")
        r = tegb("validate", str(folder))
        assert r.returncode == 1 and "judge prompt hash mismatch" in r.stdout


def test_maintainer_adds_reference_evaluation_to_core_only_submission():
    """Early Evaluation Program path: a third party sends the core score only; the maintainers unpack the answers,
    run the reference judges (here the frozen verdicts stand in for the paid calls) and attach the result."""
    key = "gpt-6.1-terra"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        res = tmp / "theirs"
        shutil.copytree(ROOT / "results" / "baseline" / "raw" / key, res / "raw" / key)
        r = tegb("submit", str(res), *SUBMIT_META, "--out", str(tmp / "submissions" / "v0.1"))
        folder = tmp / "submissions" / "v0.1" / "fake-model"
        assert r.returncode == 0 and not (folder / "judgments.jsonl").exists(), r.stdout + r.stderr
        assert json.loads((folder / "submission.json").read_text(encoding="utf-8"))["metrics"]["reference"] is None
        ours = tmp / "ours"
        r = tegb("unpack", str(folder), "--output", str(ours))
        assert r.returncode == 0 and len(list((ours / "raw" / "fake-model").glob("*.json"))) == 738, r.stdout + r.stderr
        r = tegb("attach-reference", str(folder), "--results", str(ours))
        assert r.returncode != 0 and "not complete" in (r.stdout + r.stderr)  # the judges have not run yet
        for j in ("judge-claude-sonnet-5-5", "judge-gpt-6.1-terra"):
            (ours / "judged" / j).mkdir(parents=True)
            for p in (ROOT / "results" / "baseline" / "judged" / j).glob(f"{key}__*.json"):
                shutil.copy(p, ours / "judged" / j / p.name.replace(f"{key}__", "fake-model__"))
        r = tegb("attach-reference", str(folder), "--results", str(ours))
        assert r.returncode == 0, r.stdout + r.stderr
        assert tegb("validate", str(folder)).returncode == 0
        sub = json.loads((folder / "submission.json").read_text(encoding="utf-8"))
        S = json.loads((ROOT / "results" / "baseline" / "summary_main.json").read_text(encoding="utf-8"))
        assert abs(sub["metrics"]["reference"]["by_condition"]["RAW"]["ucr"] - S["rates"][key]["A"]["uc"]) < 1e-5
        assert sub["reference_evaluation"]["evaluated_by"] == "TerraUY (TEGB Early Evaluation Program)"
        r = tegb("leaderboard", "--submissions", str(folder.parent), "--blocks-dir", str(tmp / "blocks"))
        block = (tmp / "blocks" / "community_reference.md").read_text(encoding="utf-8")
        assert r.returncode == 0 and "Early Evaluation Program" in block and "Judges run by" in block, r.stdout + r.stderr


LOCAL_MODEL = '''import json, sys
req = json.load(sys.stdin)
assert "Analyst question" in req["user"] and req["max_tokens"] == 600
print("Local model: the evidence supports tree-cover loss; it does not establish deforestation.")
'''
PY_ADAPTER_1 = 'def generate(prompt):\n    assert "Analyst question" in prompt\n    return "One-argument adapter answer."\n'
PY_ADAPTER_2 = ('def generate(system, user, max_tokens=None, temperature=None):\n    assert max_tokens == 600\n'
                '    return {"text": "Two-argument adapter answer.", "model_returned": "my-model-rev-1"}\n')


class _FakeOpenAI(BaseHTTPRequestHandler):
    seen: list = []

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).seen.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
        if "temperature" in body:  # like providers that only accept their default sampling
            out, code = {"error": {"message": "Unsupported parameter: temperature"}}, 400
        else:
            out, code = {"model": "fake-served-model", "choices": [{"message": {"content": "HTTP adapter answer."}, "finish_reason": "stop"}],
                         "usage": {"prompt_tokens": 11, "completion_tokens": 4}}, 200
        data = json.dumps(out).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def test_adapters_local_program_python_function_and_http():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "local_model.py").write_text(LOCAL_MODEL, encoding="utf-8")
        (tmp / "a1.py").write_text(PY_ADAPTER_1, encoding="utf-8")
        (tmp / "a2.py").write_text(PY_ADAPTER_2, encoding="utf-8")
        few = ["--task-ids", "A01,D01", "--workers", "2"]

        def texts(out: Path) -> list[dict]:
            return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((out / "raw").glob("*/*.json"))]

        r = tegb("run", "--adapter", "command", "--model", "local-llm", "--command", f'"{sys.executable}" "{tmp / "local_model.py"}"',
                 "--output", str(tmp / "cmd"), *few)
        assert r.returncode == 0, r.stdout + r.stderr
        got = texts(tmp / "cmd")
        assert len(got) == 18 and all(g["text"].startswith("Local model:") for g in got)
        r = tegb("run", "--adapter", "python", "--model", "m1", "--adapter-path", str(tmp / "a1.py"), "--output", str(tmp / "py1"), *few)
        assert r.returncode == 0 and all(g["text"] == "One-argument adapter answer." for g in texts(tmp / "py1")), r.stdout + r.stderr
        r = tegb("run", "--adapter", "python", "--model", "m2", "--adapter-path", str(tmp / "a2.py"), "--output", str(tmp / "py2"), *few)
        assert r.returncode == 0 and {g["model_returned"] for g in texts(tmp / "py2")} == {"my-model-rev-1"}, r.stdout + r.stderr

        _FakeOpenAI.seen = []
        srv = HTTPServer(("127.0.0.1", 0), _FakeOpenAI)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            url = f"http://127.0.0.1:{srv.server_port}/v1"
            r = tegb("run", "--adapter", "openai-compatible", "--model", "served", "--base-url", url, "--api-key-env", "TEGB_TEST_KEY",
                     "--output", str(tmp / "http"), *few, env={"TEGB_TEST_KEY": "dummy-test-key"})
            assert r.returncode == 0, r.stdout + r.stderr
        finally:
            srv.shutdown()
        got = texts(tmp / "http")
        assert len(got) == 18 and all(g["text"] == "HTTP adapter answer." and g["model_returned"] == "fake-served-model" for g in got)
        assert all(g["temperature"] is None for g in got), "temperature rejected by the server must be recorded as provider default"
        assert all(s["path"] == "/v1/chat/completions" and s["auth"] == "Bearer dummy-test-key" for s in _FakeOpenAI.seen)
        assert all(s["body"]["max_tokens"] == 600 and s["body"]["messages"][0]["role"] == "system" for s in _FakeOpenAI.seen)
        blob = "".join(p.read_text(encoding="utf-8") for p in (tmp / "http").rglob("*.json"))
        assert "dummy-test-key" not in blob, "the key value must never be written to disk"
        # an incomplete run cannot be packaged
        r = tegb("submit", str(tmp / "http"), *SUBMIT_META, "--out", str(tmp / "subs"))
        assert r.returncode != 0 and "incomplete run" in (r.stdout + r.stderr)
        # the frozen baseline can never be overwritten
        r = tegb("run", "--adapter", "mock", "--model", "naive", "--output", str(ROOT / "results" / "baseline"), *few)
        assert r.returncode != 0 and "frozen" in (r.stdout + r.stderr)


def main() -> int:
    failed = 0
    for name, fn in [(k, v) for k, v in globals().items() if k.startswith("test_")]:
        try:
            fn()
            print("PASS", name)
        except Exception as e:  # noqa: BLE001
            failed += 1
            print("FAIL", name, str(e)[:800])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
