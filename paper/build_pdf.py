"""Render paper/TECHNICAL_REPORT.md to HTML and PDF (headless Chrome or Edge).

    python paper/build_pdf.py            # needs the `markdown` package and a local Chrome/Edge

Writes paper/TEGB_v0.1_Technical_Report.pdf (the intermediate HTML goes to a temporary directory).
The Markdown file stays the source of truth; numbers come from the generated blocks (analysis/docs_sync.py).
"""
from __future__ import annotations

import argparse
import base64
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "paper" / "TECHNICAL_REPORT.md"
PDF = ROOT / "paper" / "TEGB_v0.1_Technical_Report.pdf"

CSS = """
@page { size: A4; margin: 25.4mm; }
body { font-family: Georgia, 'Times New Roman', serif; font-size: 10.5pt; line-height: 1.45; color: #111; }
h1 { font-size: 19pt; line-height: 1.2; margin: 0 0 6pt; }
h2 { font-size: 13.5pt; margin: 18pt 0 6pt; border-bottom: 0.5pt solid #999; padding-bottom: 2pt; }
h3 { font-size: 11.5pt; margin: 12pt 0 4pt; }
p, li { text-align: left; }
code { font-family: Consolas, 'Courier New', monospace; font-size: 9pt; background: #f3f3f3; padding: 0 2pt; }
pre { background: #f6f6f6; padding: 6pt; font-size: 8.5pt; white-space: pre-wrap; }
table { border-collapse: collapse; margin: 8pt 0; font-size: 9pt; width: 100%; page-break-inside: avoid; }
th, td { border-top: 0.4pt solid #bbb; border-bottom: 0.4pt solid #bbb; padding: 2.5pt 4pt; vertical-align: top; }
th { background: #eee; text-align: left; }
img { max-width: 100%; display: block; margin: 8pt auto 2pt; page-break-inside: avoid; }
blockquote { border-left: 2pt solid #777; margin: 8pt 0; padding: 2pt 8pt; background: #f7f7f7; }
"""


def find_browser() -> str:
    for c in (os.environ.get("TEGB_BROWSER"), shutil.which("chrome"), shutil.which("msedge"),
              r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              shutil.which("google-chrome"), shutil.which("chromium")):
        if c and Path(c).exists():
            return c
    raise SystemExit("no Chrome/Edge found; set TEGB_BROWSER")


ITEM = re.compile(r"^(\s*)([-*]|\d+\.)\s+")


def normalize_lists(md: str) -> str:
    """GitHub renders a list that directly follows a paragraph, and nested items indented by 2-3 spaces.
    python-markdown needs a blank line before the list and 4-space nesting, so adapt the source here."""
    out, in_code = [], False
    for line in md.split("\n"):
        if line.lstrip().startswith("```"):
            in_code = not in_code
        m = None if in_code else ITEM.match(line)
        if m:
            indent = len(m.group(1))
            if 2 <= indent <= 3:
                line = "    " + line.lstrip()
            prev = out[-1] if out else ""
            if indent == 0 and prev.strip() and not ITEM.match(prev) and not prev.startswith((" ", "|", "#")):
                out.append("")
        out.append(line)
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(SRC), help="Markdown source (figure paths are resolved from paper/)")
    ap.add_argument("--out", default=str(PDF))
    args = ap.parse_args()
    out = Path(args.out).resolve()
    md = Path(args.src).read_text(encoding="utf-8")
    md = re.sub(r"<!-- /?TEGB:[a-z_]+ -->\n?", "", md)
    md = normalize_lists(md)
    body = markdown.markdown(md, extensions=["tables", "fenced_code", "sane_lists"])

    def inline(m: re.Match) -> str:
        path = (SRC.parent / m.group(1)).resolve()
        data = base64.b64encode(path.read_bytes()).decode()
        return f'src="data:image/png;base64,{data}"'
    body = re.sub(r'src="([^"]+\.png)"', inline, body)
    html = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>TEGB v0.1 Technical Report</title>'
            f"<style>{CSS}</style></head><body>{body}</body></html>")
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "report.html"
        page.write_text(html, encoding="utf-8")
        subprocess.run([find_browser(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={out}", page.as_uri()], check=True, timeout=120,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("written", out, out.stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
