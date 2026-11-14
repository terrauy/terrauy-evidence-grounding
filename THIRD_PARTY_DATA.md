# Third-party data in TEGB

The **TEGB license** and the **source dataset terms** are two different things:
- **TEGB license.** Applies to what TEGB authors created. Code is under Apache-2.0; tasks, annotations, documentation and figures are under CC BY 4.0. See `LICENSING.md`.
- **Source dataset terms.** Apply to the Earth-observation values that TEGB evidence records quote or derive from these sources. They remain under each source's own terms, listed below.

TEGB contains **derived per-asset values** (areas, years, statuses, detection counts), not raster data.

| Source as it appears in the evidence | Provider | Version(s) in TEGB | Terms (verified 2026-11-13T23:35Z) | Required attribution / notes |
|---|---|---|---|---|
| Global Forest Change | University of Maryland (Hansen/UMD), Google, USGS, NASA | GFC-2025-v1.13 (main); GFC-2024-v1.12, GFC-2023-v1.11, GFC-2021-v1.9, GFC-2019-v1.7 (versioning tasks only) | **CC BY 4.0** | "Source: Hansen/UMD/Google/USGS/NASA". Cite Hansen, M. C. et al. (2013) *High-Resolution Global Maps of 21st-Century Forest Cover Change*, Science 342: 850–853. Indicate that the values are derived. |
| Global Forest Cover 2020 (GFC2020) | European Commission Joint Research Centre (JRC) | V4 | **Free of charge, without restriction of use**, under the Copernicus Regulation. **Acknowledgement required.** This is **not** labelled CC BY 4.0. | Acknowledge the JRC GFC2020 dataset and cite it as indicated by the JRC (V4 data citation, doi:10.2905/JRC.3KATEH8, Bourgoin et al. 2026). |
| Active fire / thermal anomaly detections (FIRMS) | NASA | VIIRS S-NPP, VIIRS NOAA-20, VIIRS NOAA-21, MODIS (near real time) | Unmarked data from NASA-led missions are licensed as **Creative Commons Zero (CC0)** (NASA Earthdata data-use guidance). Citation requested. No implied endorsement. No separate terms for the NOAA-platform VIIRS products were found. | "We acknowledge the use of data and/or imagery from NASA's Fire Information for Resource Management System (FIRMS)." Use does not imply NASA endorsement. |
| National forest cartography (native vs planted forest) | Ministerio de Ganadería, Agricultura y Pesca (MGAP), Uruguay | 2021 | **Licencia de Datos Abiertos – Uruguay, v0.1**. Reuse, adaptation and merging are permitted. | A source note naming MGAP, the license and the dataset, **stating that values were derived/modified** (per-asset planted/native areas). |

**Mentioned but not used as evidence:**
- Sentinel-2 appears only as a distractor in one source-attribution question (F05). No Sentinel-2 data is included.
- No CDSE, CHIRPS or other datasets are used.

The sources are in `paper/RELATED_WORK_SOURCES.md`. This is a factual summary, not legal advice.
