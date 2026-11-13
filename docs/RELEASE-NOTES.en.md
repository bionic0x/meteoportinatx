# Unreleased — phone sensors and haptics

**Language / Idioma:** [Español](RELEASE-NOTES.md) · English

- Experimental `/dispositivo/` view, optional sensors and vibration on cycle transitions. It does not replace official warnings or operate as a background alert. See `docs/DISPOSITIVO-SENSORES.en.md`.

# Unreleased — Météo-France key monitoring

- `credential-expiry.yml` also monitors `METEOFRANCE_KEY_EXPIRES` if registered (optional; portal tokens expire according to the duration chosen when they are generated).
- `meteofrance-probe.yml` and `scripts/probe_meteofrance.py` test `METEOFRANCE_API_KEY` against DPObs with the `src/meteo_france_obs.py` connector (#38): catalogue HTTP code and station counts, never the key.
- Météo-France attribution with time of the latest data when its observations are used.

# Unreleased — issues #7 #8 #9 #10 #11 #18 #20 #21 #23

- **#20/#21** Lightning in its own electrical family: it neither confirms nor is confirmed by rain for `alarm`; its level remains visible. 39/40/42/45 dBZ scale with 1 and 2 strong frames.
- **#8** Actual model-neighbourhood radius (30.2 km, not “±17 km”). Model/buoy waves matched only by buoy and time (±30 min), otherwise `NO_COMPARABLE`. Pyrenean elevations by each point's north/south side.
- **#18/#23** `scripts/check_backend_parity.py` and `backend-parity.yml` workflow (fails if Render does not serve the version in `RELEASE_STATUS.json`). Presence of `AEMET_API_KEY` reported without revealing its value. Official-axis source (`AEMET_CAP+METEOALARM`, `SOLO_METEOALARM`, `NINGUNA`) in `core`, API and views.
- **#10** `src/radar_motion.py`: echo-motion vector, ETA 0–120 min with range and `MOTION_UNKNOWN`. Replaces “approach speed”.
- **#7** `src/ledger_shadow.py`: optional shadow record (`METEO_LEDGER`) of forecasts frozen before their window. PORTUS observations have `qc=UNKNOWN`, so they are not yet scored.
- **#9** No automated access to ClimayNievePirineos unless `CNP_PERMISSION_VERIFIED=1`.
- **#11** Decision view displays the official source and the mountain-side elevation. User evaluation protocol in `docs/EVALUACION-USUARIOS-P1.md` (no sessions conducted).

## Pyrenees — ERA5-Land climate sidecar (experimental)

A manual generator with synthetic tests and informative 24-hour rainfall notes is included. No actual downloads, provisioned credentials, or impact on warnings or Render Free. CDS format and redistribution terms remain to be validated.

# Unreleased — Pyrenees engine 0.6.1 (coastal parity and mountain physics)

`src/pirineo.py` and `src/pirineo_meta.py` move from 0.3.0 to 0.6.1. The number aligns the mountain engine with coastal core 0.6.1 guarantees; it does not indicate calibration.

**Missing data = UNKNOWN, never 0**

- Foehn without a profile, a forecast for the pair or common hours → `estado: UNKNOWN` and `horas: null` (previously “0 h”, read as “no foehn”). Hours are paired by UTC instant (Open-Meteo and MET Norway), and the signal from any model counts, not just the first (`por_modelo`).
- Point “now” values (T, Td, Tw, wind) → `null` if the series does not cover the current hour within ±90 min, instead of using another hour's value.
- Grid: a 3-hour accumulation with any gap → `null`, not a sum treating gaps as zero.
- `core.fuentes_edad_min`: age of data served by each cached source.

**Mountain physics**

- Profile with model surface: pressure levels below ground are removed (e.g. 925 hPa below Cerdanya), and the 2 m level is added at surface pressure.
- Warm layer over subzero air at the bottom (cold pool): `capa_calida` (base, top, maximum T, valley-floor T) and `riesgo_engelante` if precipitation occurs. In that case no snow levels are given; previously the upper-layer freezing level hid subzero valley air.
- Meta-analysis: psychrometric wet bulb at each station's pressure (previously Stull at 1013 hPa, with deviations of tenths exactly at the phase threshold). The `wet_bulb_le0` fraction counts only precipitating members: a cold dry day no longer produces 1.0. The solid-phase threshold uses the same 0.7 °C as the 0–72 h engine.
- Observed inversion: asserted only with ≥300 m elevation difference and slope greater than twice its standard error; otherwise `concluyente: false` and the view does not draw the line.

**Unchanged:** the phase threshold remains an uncalibrated hypothesis; melting cooling is not modelled; inversion still mixes basins; southern foehn is not evaluated; the regional engine (`zone_engine.py`) still uses Stull.

# Unreleased — independent confirmation for alarm and explicit Z–R (#17)

- No isolated observation yields `alarm`: each observed channel contributes at most `alert` to fusion. Red is reached only by independent confirmation (different group, root and family, with a local observation), by the high-resolution gate or the official-warning floor, which does not change. Reasons state when the ceiling applies.
- The radar QPE threshold is evaluated only with `CFG["radar_threshold_zr"]` (Marshall–Palmer, consistent with 45 dBZ). The “tropical” relation triggered `alert` near 40 dBZ; it is now shown only as a diagnostic.
- Lightning-channel tests: levels by count, distance, locality and activity jump.

# Unreleased — family coverage and uniform freshness (#16)

- `fuse()` requires at least one live observed rain-family channel: if only wind and sea are live it declares insufficient coverage, marks rain `UNKNOWN` and does not downgrade.
- Every channel records its newest data time (`data_time`). Without a time, older than `CFG["channel_max_age_min"]`, or dated in the future, it becomes `UNKNOWN` before fusion. The official axis does not change.
- Radar with the same echo-bearing image in every frame → frozen, `UNKNOWN`. Identical empty frames (clear sky) remain valid.
- Models and waves with all values `None` → `UNKNOWN`; gaps no longer count as 0 mm.
- `core.json`, the public API and Portinatx view show each channel's data age.
- Initial age limits are uncalibrated; review with the forecast archive (#7).

# Unreleased — source catalogue and provenance-labelled knowledge

- New `src/knowledge_base.py` (stdlib): source catalogue with licence/verification, priors marked HYPOTHESIS, threshold provenance (`THRESHOLD_PROVENANCE`; Meteoalerta Annex 1 = `None`, no invented values), and validated JSON sidecar reading.
- New `contexto` source (`kind="context"`): UNKNOWN without a valid sidecar; it does not enter fusion or change levels. The backend does not count it as a usable coastal source.
- Pyrenees: `snow_frac` phase ramp changes from 0.5 °C to 0.7 °C wet bulb (Catalan literature, not locally calibrated), and `profile_diag` adds `tw07_m`. Heuristic snowflake/settling/accumulation levels do not change.
- `docs/CATALOGO-FUENTES.en.md`. No real sidecar, no connectors tested live. No version was changed.

# Release 0.5.1 — integration and security corrections

- Fixed reading of `X-Meteo-Freshness` using `Access-Control-Expose-Headers`.
- Added `X-Meteo-Snapshot` and verification that each screen uses one data generation, with complete static fallback.
- Replaced indiscriminate public `core` copying with an explicit projection of allowed fields.
- Fixed local server JS assets and `.pyz` packaging.
- Unified version across integration engines, portal, manifest, release and documentation.
- Regenerated SHA-256 table with mandatory CI verification.
- Render Free deployed as an experimental service without disk: forensic history is temporary, not durable.
- Validation extended to Python 3.10/3.11 and bridge Node tests. Weather providers still need field verification.

## Historical — Release 0.4.0

The following section describes **the historical state of the 0.4.0 merger**, before GitHub Pages and Render Free backend deployment. It does not describe current operational status.

---

# Release 0.4.0 — Portinatx + Pyrenees merger

Date: 10 November 2026.

## Integration completed

- Preserved coastal engine **0.6.1** over the older 0.6.0 attachment: it contains CET/CEST fixes and warning rules.
- Retained Pyrenees engine **0.3.0** with DEM, 0–72 h physical model and 15-day module.
- Added the **Portinatx interface** absent from repository release 0.3.0.
- New `src/nowcast.py` with common export and server: `/`, `/portinatx/`, `/pirineo/`.
- Statuses, alerts, caches and cadences isolated between domains. The risk of mixing Ibiza convective rain and mountain snow is not accepted.
- New `scripts/build_site.py` with strict validation of both domains and data age before changing `site/`.
- Unified launchers and `.pyz` application; tools in `src/portinatx_degen.py` and `src/pirineo.py` retained for advanced access.
- The DANA sequence is preserved as history in the local delivery package; the public repository contains only a summary without private household details. The later forensic report takes priority when interpreting wave bias.
- Added integration, route security, offline output, freshness and packaging tests in CI. No hosting connection or deployment workflow at that historical point.

## Not promised

- A passing synthetic test is not live meteorological validation.
- This release does not contain multi-winter seasonal snow calibration.
- The system does not guarantee availability of AROME/ICON/ECMWF or any provider at query time.
- The version is ready to deploy **after** connecting a hosting provider and persistent collection process.

See [Unified architecture](ARQUITECTURA-UNIFICADA.en.md) for decisions and limitations.

## 0.6.0 — Shared regional core (11 November 2026)

- Portinatx and the Pyrenees share configurable packages, forecasts, ensembles, RainViewer radar, Meteoalarm area warnings and nearby METAR observations. The Pyrenees exclude marine data.
- Offline HTML report, hash archive, query comparison and application/profile/package downloads from Pages. Specialised territorial interfaces remain available.
- Local forensic verification of frozen forecasts against reviewed measurements: time and space gates, compatible units and windows, duplicates, episode errors, common baseline and Brier. Traceable JSON and HTML with exclusions; no automatic recalibration.
- Full coverage required for daily accumulations and per-metric support; public backend packages identified by full manifest while retaining privacy projection and same-snapshot web loading.
- Deployment requires a useful forecast at each point; failed supplementary sources are shown as unknown. No test data or private forensic observations are published.
- Local validation with test responses and real browser. Live providers were not verified from the development environment due to network restrictions. Actions execution and Pages deployment are verified separately; Render requires its own deployment.

## 13 November 2026 — Shared atmospheric diagnostics

Coastal, mountain and downloadable regional profiles now execute the same pure atmospheric core. Terrain, explicit units, actual surface pressure and verified vertical conventions gate the results. Missing components remain unknown in both the engine and browser laboratory. Both templates include the optional-per-user `atmosphere` module; marine remains excluded from inland profiles. Local validation: 357 integration tests with required browser execution, domain selftests, Node suites, Ruff and checksums. These are synthetic regressions, not calibrated meteorological skill. See `PARIDAD-ALGORITMOS.md` for remaining specialized algorithms and the scope of Agency Agents engineering work.
