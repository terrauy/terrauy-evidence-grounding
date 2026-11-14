"""Render copyright/attribution metadata from release_config.json (parametrizable copyright holder).

    python analysis/release_meta.py

Writes NOTICE and analysis/blocks/copyright.md (inserted into docs by analysis/docs_sync.py --render).
Changing the holder later (e.g. to a legal entity) only requires editing release_config.json and re-running.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    c = json.loads((ROOT / "release_config.json").read_text(encoding="utf-8"))
    holder = c["legal_entity"] or c["copyright_holder"]
    line = f"Copyright © {c['copyright_year']} {holder}"
    brand = c["brand"]
    block = (f"{line}. Project/brand: {brand}.\n\n"
             "| Component | License / terms |\n|---|---|\n"
             "| TEGB code (`harness/`, `evaluation/`, `analysis/`, `audit/`, `tests/`, `dataset/build_public_files.py`) | Apache License 2.0 (`LICENSE`) |\n"
             "| TEGB-authored tasks, answer keys, annotations, fact-sheet structure, documentation and figures | CC BY 4.0 (`LICENSES/CC-BY-4.0.md`) |\n"
             "| Third-party EO source values embedded in the evidence | Original source terms + attribution (`THIRD_PARTY_DATA.md`) |\n"
             "| Model outputs (agent responses and LLM-judge verdicts) | **Not** licensed under CC BY 4.0. See `MODEL_OUTPUTS_NOTICE.md` and `MODEL_OUTPUTS_RIGHTS_MATRIX.md` |")
    (ROOT / "analysis" / "blocks").mkdir(parents=True, exist_ok=True)
    (ROOT / "analysis" / "blocks" / "copyright.md").write_text(block + "\n", encoding="utf-8")
    notice = f"""TerraUY Evidence Grounding Benchmark (TEGB)
{line}
Project/brand: {brand}. Brand use does not imply that any legal entity holds the intellectual property.

This distribution contains material under different terms:

1. TEGB code - Apache License 2.0 (see LICENSE).
2. TEGB-authored benchmark tasks, answer keys, annotations, documentation and figures -
   Creative Commons Attribution 4.0 International (see LICENSES/CC-BY-4.0.md).
3. Values derived from third-party Earth-observation datasets - their original terms apply
   (see THIRD_PARTY_DATA.md):
   - Hansen/UMD/Google/USGS/NASA Global Forest Change (CC BY 4.0). Hansen et al. 2013, Science 342: 850-853.
   - European Commission Joint Research Centre, Global Forest Cover 2020 (free of charge, without restriction
     of use; acknowledgement required).
   - NASA Fire Information for Resource Management System (FIRMS). We acknowledge the use of data and/or
     imagery from NASA's FIRMS. Use does not imply endorsement by NASA.
   - Ministerio de Ganaderia, Agricultura y Pesca (MGAP), Uruguay - forest cartography 2021, under the
     Licencia de Datos Abiertos - Uruguay v0.1; values were derived per asset (modified).
4. Model outputs (agent responses and LLM-judge verdicts) are NOT licensed under CC BY 4.0 and are not
   TEGB-authored content. See MODEL_OUTPUTS_NOTICE.md:
   "Model outputs are provided for research, evaluation and benchmark reproducibility. Their inclusion does
   not grant rights beyond those permitted by the originating model provider's applicable terms."

No model provider, data provider or space agency sponsors, endorses or has reviewed TEGB.
"""
    (ROOT / "NOTICE").write_text(notice, encoding="utf-8")
    print("NOTICE and copyright block written:", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
