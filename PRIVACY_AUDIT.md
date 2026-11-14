# Privacy audit: TEGB v0.1 (public baseline)

| | |
|---|---|
| **Date** | 2026-11-13 (after the targeted public re-baseline; re-run before publication) |
| **Scope** | Every file in the v0.1 release |
| **Tools** | `audit/scan.py` (output in `audit/privacy_scan.json`), plus an internal leak scan against the private original values. The internal scan prints no values. |
| **Result** | **PASS** |

## Checks performed

| Check | Method | Result |
|---|---|---|
| Organization, tenant, user and asset identifiers | Regex scan for UUIDs and `organization_id` / `org_id` / `tenant_id` / `asset_id` / `user_id` fields | 0 hits |
| Emails | Regex | 0 hits |
| Geometry, coordinates, bbox | Regex for coordinate pairs in Uruguay's range, GeoJSON `coordinates` / `bbox`, and WKT polygons | 0 hits |
| Cadastral references (padrón) | Regex | 0 hits |
| Place names | Manual scan for all 19 Uruguayan departments | 0 hits |
| Internal hostnames and URLs | Regex for Supabase, Railway, Vercel, private inference-endpoint hosts and `localhost`; every URL checked against a public allow-list | 0 hits outside the allow-list |
| Local filesystem paths | Regex | 0 hits |
| Personal names | Regex | Only the copyright line in `NOTICE` / `LICENSING.md` / `release_config.json`, by owner decision |
| Customer data | Read-only aggregate query on the production database (counts only, no identifiers) | All assets behind the tasks belong to TerraUY's own organization. Two fire contexts of another organization were never used and are not distributed. |
| **Quasi-identifiers: real area values** | Internal leak scan of every public file against all original area values ≥ 2 ha and all original shares of an asset ≥ 0.10 %. Data files and model-output text are checked strictly, on every numeric token; code and docs are checked on numbers used as areas or shares. | **0 original values** in tasks, fact sheets, prompts, model responses, judge verdicts, labels, analyses, figures, docs and code |
| Model outputs repeating real values | The development-run outputs of the 66 substituted tasks quoted real areas (624 responses, 45 judge rationales) | Removed from the release. The public baseline contains only responses to the public prompts. |
| Development run and its blind review | Contain real values | **Not distributed.** Only aggregate statistics are included, in `results/baseline/development_run/`. |

## Synthetic area values (owner decision 2026-11-13)

Exact asset areas, event areas and percentages could have allowed re-identification of real parcels against the public cadastre and per-parcel Hansen statistics. To remove that path:
- in 66 tasks, every area value ≥ 2 ha received an independent synthetic factor, with method thresholds preserved and derived fields recomputed;
- the real-to-synthetic mapping and its seed are not published;
- values below 2 ha (not identifying), years, statuses, fractions and dataset versions are unchanged.

**Residual information:** loss years and forest-type context, such as plantation species. These are weak identifiers on their own.

**Coincidental numeric matches.** The strict token scan (re-run on 2026-11-13 before publication) finds 8 distinct numbers in public-run model outputs, judge rationales and metric files that happen to equal an original value. None is used as an area in hectares. They are shares of an asset that models computed from the synthetic inputs (for example a loss area divided by the asset area), statistics such as a UCR, and one cost figure.
- These are not disclosures: every model input of the public run (tasks, fact sheets, prompts) contains no original value, which the strict scan verifies.
- The numbers are not linked to any real asset.

**Copyright line.** By owner decision, the copyright holder's name appears in `NOTICE`, `LICENSING.md` and `release_config.json`. The scanner allows it only there.
