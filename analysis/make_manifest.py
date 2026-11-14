"""Write MANIFEST.sha256: SHA-256 of every file in the release except the manifest itself and .git/.

    python analysis/make_manifest.py          # write
    python analysis/make_manifest.py --check  # verify; exit 1 on any mismatch
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "MANIFEST.sha256"
SKIP = {".git", "__pycache__"}


def lines() -> list[str]:
    out = []
    for p in sorted(ROOT.rglob("*"), key=lambda q: q.relative_to(ROOT).as_posix()):
        rel = p.relative_to(ROOT)
        if p.is_file() and p != OUT and not set(rel.parts) & SKIP:
            out.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {rel.as_posix()}")
    return out


if __name__ == "__main__":
    cur = lines()
    if "--check" in sys.argv:
        ok = OUT.read_text(encoding="utf-8").splitlines() == cur
        print("MANIFEST", "PASS" if ok else "FAIL", len(cur), "files")
        sys.exit(0 if ok else 1)
    OUT.write_text("\n".join(cur) + "\n", encoding="utf-8", newline="\n")
    print("MANIFEST written:", len(cur), "files")
