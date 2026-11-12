# Pyrenees route planner (`/pirineo/ruta/`)

**Language / Idioma:** [Español](RUTAS-PIRINEO.md) · English

Overlays the forecast on the **estimated position** along a GPS track using departure time and pace. Status: **MVP, eastern Pyrenees only, tested only with synthetic data**.

## What it does

1. Upload a **GPX** (or use the synthetic demonstration route) and choose departure time and pace.
2. The track is resampled approximately every 200 m. Each point receives an **estimated time** (Tobler × factor + breaks, or recorded track times) and a **window** of ±15% of elapsed time.
3. The forecast grid is interpolated at each point and time (bilinear in space; linear in time; accumulation in three-hour blocks).
4. **Each hazard is assessed separately:** rain, wind (gust), snow and cold (wind chill). Results appear in a summary, terrain map, profile with hazard bands and segment table.

## Privacy (design requirement)

- The GPX is read and processed **in the browser**; it is not uploaded or stored (including in `localStorage`).
- The page uses no third-party fonts or tiles: the only requests are for the site's own public JSON (`core`, `dem`, `grid`).
- `tests/test_route_page_browser.py` checks this in real Chrome: zero external requests, no requests after uploading a track, no track in URL or request body, only `GET`.

## Project principles applied

- **Fail closed.** Outside the grid or 48-hour horizon, with missing data or an invalid grid, the result is *no data*, never “no risk”. The page says so and uses striped grey.
- **One indicator per hazard**, no overall score.
- **Time windows**, not exact times.
- **Context ≠ observation.** This tool does not issue warnings or change engine levels.
- **Thresholds without official provenance** are declared `UNVERIFIED` or `ORIENTATIVE` in `THRESHOLDS` (`src/route_engine.js`).

## Input data

Pyrenees `grid.json` (model `OM_MODELS[0]`, 0.05°, three-hour step, 48 h), expanded in this version with `dew_point_2m` and `wind_speed_10m`, plus `paso_h` and `acumulado` declaring accumulation semantics: the block timestamped `t_k` sums hours `k..k+2` and covers `(t_k − 1 h, t_k + 2 h]`. It also uses `dem.json` (~440 m terrain) and `core.avisos` (listed without geolocating them on the route).

## Physics (and parity with Python)

- **Temperature at track elevation:** a lapse rate is derived using cell altitude and model freezing level; if it is 3–9 K/km it is used, otherwise 6.5 K/km is used and the profile is marked uncertain (possible inversion).
- **Phase:** same rule as `pirineo.snow_frac` (ramp on wet-bulb temperature centred on 0.7 °C, width ±1 °C; uncalibrated HYPOTHESIS), using dew point at track elevation assuming constant dew-point depression. JS↔Python numerical parity tests in `tests/test_route_engine.py` (solid fraction, wet bulb and DEM).
- **Snow:** mm of water equivalent; no conversion to cm (snow-to-liquid ratio varies).
- **Gust:** maximum of the two adjacent model outputs. On ridges and passes (DEM, 1.5 km ring, ≥150 m above surroundings), users are warned actual gusts may exceed the model; no invented factor is applied.
- **Cold:** wind chill (JAG/TI, T ≤ 10 °C and wind > 4.8 km/h).

## Not assessed (declared on the page)

Thunderstorms and lightning, fog and visibility, **flooding and watercourse crossings**, avalanches and ground snow conditions. Sources (CAPE, hydrology) are missing and no indicators are invented.

## Known limitations

- One deterministic model, no probabilities; three-hour temporal resolution dilutes brief showers.
- Grid domain: lat 42.30–42.65, lon 1.45–2.20 (Cerdanya, Capcir, Andorra and surroundings). The central Pyrenees and Huesca Pyrenees are outside it and marked no data.
- Activity factors (1.0 / 0.75 / 1.7 / 0.6) are indicative and uncalibrated.
- Rain and snow level cutoffs are recalled from usual conventions and have not been checked against the official glossary.
- **The expanded grid (two additional variables) has not been run against Open-Meteo**, only simulated responses. Check Open-Meteo terms if the site receives intensive public use.
- GPX only in the MVP.

## Next phases

1. TCX/FIT and ensemble probabilities along the route; extend the grid to central and Huesca Pyrenees.
2. Hydrology: watercourses from DEM, track crossings and upstream accumulated-rain indicator (not a hydrological warning).
3. Accounts, saved routes and shareable links (the phase with the greatest privacy implications).

## Verification

`node tests/test_route_engine.cjs` (21 tests) · `python3 -m unittest tests.test_route_engine tests.test_route_grid_contract tests.test_route_page_browser`. The browser test is skipped without Node, Playwright and Chrome.
