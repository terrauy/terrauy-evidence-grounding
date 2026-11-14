"""Privacy + security scan of every file in the TEGB release candidate (excluding audit/ itself).

    python audit/scan.py            -> audit/privacy_scan.json, audit/security_scan.json; exit 1 if a blocking hit is found

Privacy patterns: identifiers (UUIDs, emails), geometry/coordinates, cadastral references, tenant/organization fields,
internal hostnames/URLs, personal names of project staff, local filesystem paths.
Security patterns: API keys/tokens (Anthropic, OpenAI, Hugging Face, GitHub, AWS, Google, Supabase JWT, Stripe), private keys,
.env files, credentials in URLs, bearer tokens, password assignments.
URLs are checked against an allow-list of public documentation/data domains; anything else is reported.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {"audit", "__pycache__", ".git"}
TEXT_EXT = {".json", ".jsonl", ".md", ".py", ".csv", ".txt", ".cff", ".svg", ".html", ".yaml", ".yml", ".toml", ""}

PRIVACY = {
    "uuid": r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "coordinate_pair_uy": r"-3[0-5]\.\d{3,}\s*,\s*-5[3-8]\.\d{3,}|-5[3-8]\.\d{3,}\s*,\s*-3[0-5]\.\d{3,}",
    "geojson_or_wkt": r"(?i)\"coordinates\"\s*:|\bMULTIPOLYGON\s*\(|\bPOLYGON\s*\(|\"bbox\"\s*:",
    "cadastral_ref": r"(?i)\bpadr[oó]n\s*(n[º°o.]*\s*)?\d{2,}",
    "tenant_fields": r"(?i)\b(organization_id|org_id|tenant_id|asset_id|user_id)\b\s*[\"']?\s*[:=]",
    "internal_hosts": r"(?i)(supabase\.co|railway\.app|up\.railway|vercel\.app|endpoints\.huggingface\.cloud|\.internal\b|localhost:\d+)",
    "local_paths": r"(?i)([A-Z]:\\\\?Users\\\\?|/Users/[a-z]|/home/[a-z]|Desktop[\\\\/]TerraUY)",
    "staff_names": r"(?i)\b(jairo|rifran|jairorifran)\b",
}
SECURITY = {
    "anthropic_key": r"sk-ant-[A-Za-z0-9_\-]{10,}",
    "openai_key": r"\bsk-(proj-|svcacct-)?[A-Za-z0-9_\-]{20,}",
    "hf_token": r"\bhf_[A-Za-z0-9]{20,}",
    "github_token": r"\bgh[pousr]_[A-Za-z0-9]{20,}",
    "aws_key": r"\bAKIA[0-9A-Z]{16}\b",
    "google_key": r"\bAIza[0-9A-Za-z_\-]{30,}",
    "jwt": r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}",
    "stripe_key": r"\b(sk|rk)_(live|test)_[A-Za-z0-9]{10,}",
    "private_key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "credential_url": r"[a-z]+://[^\s/:@]+:[^\s/@]+@",
    "bearer": r"(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}",
    "password_assignment": r"(?i)(password|passwd|secret|api_key)\s*[:=]\s*[\"'][^\"'\s]{6,}[\"']",
}
URL = re.compile(r"https?://[^\s\"'<>)\]]+")
ALLOWED_URL_DOMAINS = ("huggingface.co/eve-esa", "huggingface.co/mistralai", "huggingface.co/datasets", "creativecommons.org", "apache.org",
                       "doi.org", "arxiv.org", "aclanthology.org", "philab.esa.int", "esa.int", "eovc.cs-soprasteria.com", "cs-soprasteria.com",
                       "storage.googleapis.com/earthenginepartners-hansen", "glad.umd.edu", "forobs.jrc.ec.europa.eu", "earthdata.nasa.gov",
                       "firms.modaps.eosdis.nasa.gov", "catalogodatos.gub.uy", "gub.uy", "iclr.cc", "papers.neurips.cc", "proceedings.iclr.cc",
                       "developers.google.com/earth-engine", "json-schema.org", "citation-file-format.github.io", "terrauy.com", "www.terrauy.com",
                       "www.w3.org", "purl.org/dc", "matplotlib.org",
                       "openai.com/policies", "www.anthropic.com/legal", "legal.mistral.ai/terms", "huggingface.co/terms-of-service",
                       "img.shields.io/badge", "zenodo.org/badge", "github.com/terrauy", "zenodo.org", "huggingface.co/TerraUY",
                       "//localhost:", "//127.0.0.1:", "//HOST", "api.openai.com/v1", "docs.github.com", "info.arxiv.org", "orcid.org")


def files():
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT).parts
        if rel[0] == "submissions" and len(rel) >= 3:
            continue  # community submissions: third-party model outputs, checked by `tegb validate`
        if p.is_file() and not (set(rel[:-1]) & SKIP_DIRS) and p.suffix.lower() in TEXT_EXT:
            yield p


NAME_ALLOWED = {"NOTICE", "LICENSING.md", "release_config.json", "PRIVACY_AUDIT.md", "copyright.md",
                "BENCHMARK_CARD.md", "TECHNICAL_REPORT.md", "CITATION.cff", "README.md", ".zenodo.json"}  # copyright holder / author line only (owner decisions 2026-11-13)


LOCALHOST_ALLOWED = {"RUN_YOUR_MODEL.md", "adapters.py", "README.md"}
EMAIL_ALLOWED = {"contacto@terrauy.com"}


def scan(patterns):
    hits = {k: [] for k in patterns}
    comp = {k: re.compile(v) for k, v in patterns.items()}
    n = 0
    for p in files():
        n += 1
        t = p.read_text(encoding="utf-8", errors="ignore")
        for k, rx in comp.items():
            if k == "staff_names" and p.name in NAME_ALLOWED:
                continue
            for m in rx.finditer(t):
                if k == "internal_hosts" and p.name in LOCALHOST_ALLOWED and m.group(0).lower().startswith("localhost:"):
                    continue  # documented defaults of local model servers (Ollama, vLLM), not internal infrastructure
                if k == "email" and m.group(0).lower() in EMAIL_ALLOWED:
                    continue  # public research contact, as published on terrauy.com
                hits[k].append({"file": p.relative_to(ROOT).as_posix(), "match": m.group(0)[:60]})
    return n, hits


def main() -> int:
    n, priv = scan(PRIVACY)
    urls = []
    for p in files():
        for m in URL.finditer(p.read_text(encoding="utf-8", errors="ignore")):
            u = m.group(0)
            if not any(d in u for d in ALLOWED_URL_DOMAINS):
                urls.append({"file": p.relative_to(ROOT).as_posix(), "url": u[:100]})
    priv["urls_outside_allowlist"] = urls
    # quasi-identifiers (reported, not blocking): exact asset areas in the evidence
    tasks = [json.loads(x) for x in (ROOT / "dataset" / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    areas = sorted({u["asset_reference"].get("area_ha") for t in tasks for u in t["units"] if u["asset_reference"].get("area_ha")})
    _, sec = scan(SECURITY)
    env_files = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob(".env*")]
    sec["dotenv_files"] = [{"file": f} for f in env_files]
    blocking_priv = {k: v for k, v in priv.items() if v}
    blocking_sec = {k: v for k, v in sec.items() if v}
    pr = {"files_scanned": n, "result": "PASS" if not blocking_priv else "FAIL", "hits": {k: v[:25] for k, v in priv.items()},
          "hit_counts": {k: len(v) for k, v in priv.items()},
          "quasi_identifiers": {"distinct_exact_asset_areas_ha": len(areas), "note": "area values >= 2 ha in the 66 substituted tasks are synthetic; see PRIVACY_AUDIT.md"}}
    sr = {"files_scanned": n, "result": "PASS" if not blocking_sec else "FAIL", "hits": {k: v[:25] for k, v in sec.items()},
          "hit_counts": {k: len(v) for k, v in sec.items()}}
    (ROOT / "audit" / "privacy_scan.json").write_text(json.dumps(pr, indent=1, ensure_ascii=False), encoding="utf-8")
    (ROOT / "audit" / "security_scan.json").write_text(json.dumps(sr, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"privacy": {"result": pr["result"], "hit_counts": pr["hit_counts"]}, "security": {"result": sr["result"], "hit_counts": sr["hit_counts"]}}, indent=1))
    return 0 if pr["result"] == sr["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
