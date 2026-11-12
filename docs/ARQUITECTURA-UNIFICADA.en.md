# MeteoPortinatx Unified 0.5.1 — architecture and decisions

**Language / Idioma:** [Español](ARQUITECTURA-UNIFICADA.md) · English

**Date:** 2026-11-10. **Scope:** one project, two meteorological domains, one release cycle.

## Safety and observation contracts

- `src/portinatx_degen.py` 0.6.1 is the coastal core and shared library. It is not replaced by the attached 0.6.0 file, because that would lose CET/CEST fallback, 23/25-hour forensic windows and CAP changes. It retains the three axes **official warning / observed hazard / own caution**. A model does not become an observation; a source failure does not mean calm weather.
- `src/pirineo.py` 0.6.1 uses core utilities for the Pyrenean domain. Terrarium DEM, wet-bulb level, snowflake/settling/accumulation elevations, Kuchera SLR, foehn, inversion and mountain warnings. It retains its own data directory, cadence and diagnostic label.
- `src/pirineo_meta.py` 0.6.1 creates the 15-day perspective by ECMWF/GEFS/ICON family (it does not multiply independence by the number of members); it differs from deterministic GFS/IFS/ICON/AROME/AIFS. This layer is isolated from the 0–72 h physical diagnosis and safety hierarchy. ENSO, NAO/AO, stratosphere and ocean indices are **dated context, not probability multipliers**. Without ≥30 verified dates, weights are not adjusted by skill.
- `src/nowcast.py` 0.5.1 acts as orchestrator; it does not apply Ibiza thresholds to the mountains or snow thresholds to the coast. `PORTINATX_HOME` and `PIRINEO_HOME` remain independent; neither `state.json` nor the cycle archive is versioned.
- Observatories are served at `/portinatx/` and `/pirineo/`. Their APIs are `/portinatx/api/{core,radar,series,atmos,sat,mar,modx,forense}.json` and `/pirineo/api/{core,dem,grid,series,extended}.json`; read routes are enumerated and arbitrary disk files are not served.
- Locally, the server listens **only** on 127.0.0.1. It accepts POST only for `/[domain]/api/refresh`, with Host and Origin checks; it does not expose credentials. On static hosting **there is no server-side execution or button-triggered refresh**; a scheduled collector with persistence and later publication is needed.

## Interpretation of the October 2026 sources

1. Historical report `seguimiento-dana-17-20-oct-2026.md` (not published) records real-time evolution and its hypotheses. Earlier judgments are NOT retrospectively rewritten.
2. Historical report `calibracion-portinatx-dana-adam.md` (not published) contains tentative calibration based on one episode (n=2 intense days). Its factors are **hypotheses**, not general production parameters.
3. Historical report `forense-dana-17-20-oct-2026.md` (not published) uses actually issued Previous Runs, D0/D1/D2 and observations in local time. Its spatially matched comparison of marine models against buoys (model/observation ~0.87–0.99) **corrects** the initial hypothesis of 2–2.5× underestimation, which compared the cove entrance with distant buoys. Do not introduce a ×2 wave factor.
4. Convective DANA rainfall was underforecast at one point; the *easterly DANA* regime must not be inherited as universal calibration for mountain snow, summer storms or the sea. The engine shows the correction only in Forensics as experimental and avoids changing caution/warnings.
5. Historical specification `ESPECIFICACION-MOTOR-CONECTORES_v0.6.0.md` (not published) includes literal code excerpts from **0.6.0** and is a historical snapshot, not the current source of truth. The current executable source is `src/portinatx_degen.py` 0.6.1.

The full original reports are retained in the delivery package and are not uploaded to the public repository. See the [public forensic summary](FORENSE-PUBLICO.en.md).

## Structure

`src/nowcast.py` provides the CLI, localhost server and shared contracts. The Portinatx 0.6.1 engine supplies observation, radar/satellite, marine weather, NWP/AI, three safety axes, CAP and event forensics; its `HOME/app/` exports `core`, `radar`, `series`, `atmos`, `sat`, `mar`, `modx` and `forense` JSON. The Pirineo 0.6.1 engine supplies DEM, profiles, mountain observations, warnings, 15-day meta-ensemble, contrarian signals, teleconnections and Brier; its `HOME/app/` exports `core`, `dem`, `grid`, `series` and `extended` JSON.

Independent `/portinatx/` and `/pirineo/` homepages are linked from the common `/` portal. `scripts/build_site.py` validates both outputs and their age, copies them to staging and replaces `site/` only when all files are valid.

## Tests and tasks pending before connecting hosting

- Existing synthetic coastal core, Pyrenees and meta-analysis tests must stay green. Tests do not demonstrate meteorological reliability or successful live connections.
- `tests/test_unified.py`: routes, keys, state separation, rejection of missing/malformed/stale JSON, same-origin-only refresh, packaging and integrated output.
- CI checks Python 3.10 and 3.11, bridge JS tests, SHA-256 integrity and packaging. GitHub Pages already has scheduled publication and a Render Free backend is available experimentally.
- The forensic archive **is not durable** on Render Free: separate external storage is required to retain history and learning across restarts. Warnings are official; sources and weather data have independent freshness states. Never upload `state.json`, `config.env` or sensitive data.
- The static website supports *only* already issued cycles; by design it does not fabricate data when connectors fail.
