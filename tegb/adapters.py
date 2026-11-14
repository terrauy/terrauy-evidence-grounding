"""Model adapters. An adapter turns one TEGB prompt (system + user) into one answer.

Every adapter exposes:

    generate(system: str, user: str, *, max_tokens: int, temperature: float | None) -> dict

and returns {"text", "model_returned", "input_tokens", "output_tokens", "stop_reason", "temperature_used"}.
Only "text" is required from custom code; the rest is filled with None when unknown.

Built-in adapters:
    openai-compatible  any server that speaks POST {base_url}/chat/completions (OpenAI, vLLM, Ollama,
                       llama.cpp, LM Studio, TGI, Hugging Face Inference Endpoints, most hosted APIs)
    ollama             openai-compatible preset for a local Ollama server
    anthropic          Anthropic Messages API through the official `anthropic` SDK (pip install anthropic)
    command            any local program: prompt as JSON on stdin, answer on stdout
    python             your own file with a `generate` function
    mock               deterministic fake models for pipeline tests (never accepted on the leaderboard)

API keys are read from environment variables at call time and are never written to disk.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import os
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLLAMA_URL = "http://localhost:11434/v1"  # default local Ollama endpoint


class AdapterError(RuntimeError):
    pass


def _result(text, model_returned=None, input_tokens=None, output_tokens=None, stop_reason=None, temperature_used=None) -> dict:
    return {"text": text if isinstance(text, str) else "", "model_returned": model_returned, "input_tokens": input_tokens,
            "output_tokens": output_tokens, "stop_reason": stop_reason, "temperature_used": temperature_used}


class OpenAICompatible:
    """POST {base_url}/chat/completions with the standard chat schema. No SDK needed."""

    name = "openai-compatible"

    def __init__(self, model: str, base_url: str, api_key_env: str | None = None, max_tokens_param: str | None = None,
                 timeout: int = 300, extra_body: dict | None = None):
        if not base_url:
            raise AdapterError("openai-compatible needs --base-url (for example the /v1 URL of your server)")
        self.model, self.base_url, self.api_key_env, self.timeout = model, base_url.rstrip("/"), api_key_env, timeout
        self.max_tokens_param = max_tokens_param or ("max_completion_tokens" if "api.openai.com" in base_url else "max_tokens")
        self.extra_body = extra_body or {}
        self.send_temperature = True

    def _post(self, body: dict) -> dict:
        headers = {"Content-Type": "application/json"}
        key = os.environ.get(self.api_key_env, "") if self.api_key_env else ""
        if self.api_key_env and not key:
            raise AdapterError(f"environment variable {self.api_key_env} is not set")
        if key:
            headers["Authorization"] = "Bearer " + key
        req = urllib.request.Request(self.base_url + "/chat/completions", data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:  # noqa: S310 - URL chosen by the operator
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:300]
            raise AdapterError(f"HTTP {e.code}: {detail}") from None
        except urllib.error.URLError as e:
            raise AdapterError(f"connection error: {e.reason}") from None

    def generate(self, system: str, user: str, *, max_tokens: int, temperature: float | None) -> dict:
        for _ in range(3):  # at most two automatic parameter fallbacks
            body = {"model": self.model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    self.max_tokens_param: max_tokens, **self.extra_body}
            use_temp = temperature if self.send_temperature else None
            if use_temp is not None:
                body["temperature"] = use_temp
            try:
                r = self._post(body)
            except AdapterError as e:
                msg = str(e).lower()
                if msg.startswith("http 400") and "temperature" in msg and self.send_temperature:
                    self.send_temperature = False  # provider rejects temperature: use its default sampling
                    continue
                if msg.startswith("http 400") and "max_tokens" in msg and self.max_tokens_param == "max_tokens":
                    self.max_tokens_param = "max_completion_tokens"
                    continue
                if msg.startswith("http 400") and "max_completion_tokens" in msg and self.max_tokens_param == "max_completion_tokens":
                    self.max_tokens_param = "max_tokens"
                    continue
                raise
            choice = (r.get("choices") or [{}])[0]
            usage = r.get("usage") or {}
            return _result((choice.get("message") or {}).get("content") or "", r.get("model"), usage.get("prompt_tokens"),
                           usage.get("completion_tokens"), choice.get("finish_reason"), use_temp)
        raise AdapterError("request kept failing after parameter fallbacks")


class Anthropic:
    """Anthropic Messages API via the official SDK (the same call the v0.1 baseline used)."""

    name = "anthropic"

    def __init__(self, model: str, api_key_env: str | None = None):
        self.cfg = {"model": model, "key_env": api_key_env or "ANTHROPIC_API_KEY"}
        if not os.environ.get(self.cfg["key_env"]):
            raise AdapterError(f"environment variable {self.cfg['key_env']} is not set")
        try:
            import anthropic  # noqa: F401
        except ImportError:
            raise AdapterError("the anthropic adapter needs the official SDK: pip install anthropic") from None

    def generate(self, system: str, user: str, *, max_tokens: int, temperature: float | None) -> dict:
        sys.path.insert(0, str(ROOT / "harness"))
        from run import call_anthropic

        m = {**self.cfg, "max_tokens": max_tokens}
        try:
            r = call_anthropic(m, system, user, temperature)
            used = None if m.get("no_temperature") else temperature
        except Exception as e:  # noqa: BLE001
            if "temperature" not in str(e).lower():
                raise AdapterError(f"{type(e).__name__}: {str(e)[:200]}") from None
            self.cfg["no_temperature"] = True  # some models only accept their default sampling
            r = call_anthropic({**self.cfg, "max_tokens": max_tokens}, system, user, None)
            used = None
        if self.cfg.get("no_temperature"):
            used = None
        return _result(r["text"], r.get("model_returned"), r.get("input_tokens"), r.get("output_tokens"), r.get("stop_reason"), used)


class Command:
    """Run a local program once per prompt. It receives {"system","user","max_tokens","temperature"} as JSON on
    stdin and must print the answer (plain text) on stdout."""

    name = "command"

    def __init__(self, model: str, command: str, timeout: int = 600):
        if not command:
            raise AdapterError("command adapter needs --command")
        argv = shlex.split(command, posix=os.name != "nt")
        if os.name == "nt":  # non-POSIX splitting keeps the quotes around each argument
            argv = [x[1:-1] if len(x) > 1 and x[0] == x[-1] and x[0] in "\"'" else x for x in argv]
        self.model, self.argv, self.timeout = model, argv, timeout

    def generate(self, system: str, user: str, *, max_tokens: int, temperature: float | None) -> dict:
        payload = json.dumps({"system": system, "user": user, "max_tokens": max_tokens, "temperature": temperature})
        p = subprocess.run(self.argv, input=payload, capture_output=True, text=True, encoding="utf-8", timeout=self.timeout)  # noqa: S603
        if p.returncode != 0:
            raise AdapterError(f"command exited with {p.returncode}: {p.stderr[-300:]}")
        return _result(p.stdout.strip(), self.model, None, None, None, temperature)


class PythonFunction:
    """Load `generate` from a Python file. Accepted signatures:

        generate(prompt: str) -> str                       # system and user joined by a blank line
        generate(system: str, user: str) -> str
        generate(system, user, max_tokens=..., temperature=...) -> str | dict
    """

    name = "python"

    def __init__(self, model: str, path: str):
        if not path or not Path(path).is_file():
            raise AdapterError("python adapter needs --adapter-path pointing to a .py file")
        spec = importlib.util.spec_from_file_location("tegb_user_adapter", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if not hasattr(mod, "generate"):
            raise AdapterError(f"{path} does not define generate()")
        self.fn, self.model = mod.generate, model
        params = inspect.signature(self.fn).parameters
        self.positional = [p for p in params.values() if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) and p.default is p.empty]
        self.kw = {k for k in ("max_tokens", "temperature") if k in params}

    def generate(self, system: str, user: str, *, max_tokens: int, temperature: float | None) -> dict:
        extra = {k: v for k, v in (("max_tokens", max_tokens), ("temperature", temperature)) if k in self.kw}
        out = self.fn(f"{system}\n\n{user}", **extra) if len(self.positional) <= 1 else self.fn(system, user, **extra)
        if isinstance(out, dict):
            return _result(out.get("text", ""), out.get("model_returned", self.model), out.get("input_tokens"),
                           out.get("output_tokens"), out.get("stop_reason"), temperature if "temperature" in self.kw else None)
        return _result(out, self.model, None, None, None, temperature if "temperature" in self.kw else None)


class Mock:
    """Deterministic fake models (naive | careful | cond_sensitive) to test the pipeline at zero cost."""

    name = "mock"

    def __init__(self, model: str):
        if model not in ("naive", "careful", "cond_sensitive"):
            raise AdapterError("mock adapter models: naive, careful, cond_sensitive")
        self.model = model

    def generate(self, system: str, user: str, *, max_tokens: int, temperature: float | None) -> dict:
        sys.path.insert(0, str(ROOT / "harness"))
        from run import call_stub

        r = call_stub({"model": self.model}, system, user, temperature)
        return _result(r["text"], r["model_returned"], r["input_tokens"], r["output_tokens"], r["stop_reason"], temperature)


ADAPTERS = ("openai-compatible", "ollama", "anthropic", "command", "python", "mock")


def build(name: str, model: str, *, base_url: str | None = None, api_key_env: str | None = None, command: str | None = None,
          adapter_path: str | None = None, max_tokens_param: str | None = None):
    if name == "openai-compatible":
        return OpenAICompatible(model, base_url or os.environ.get("TEGB_BASE_URL", ""), api_key_env, max_tokens_param)
    if name == "ollama":
        a = OpenAICompatible(model, base_url or OLLAMA_URL, api_key_env, max_tokens_param)
        a.name = "ollama"
        return a
    if name == "anthropic":
        return Anthropic(model, api_key_env)
    if name == "command":
        return Command(model, command or "")
    if name == "python":
        return PythonFunction(model, adapter_path or "")
    if name == "mock":
        return Mock(model)
    raise AdapterError(f"unknown adapter '{name}'; choose one of: {', '.join(ADAPTERS)}")
