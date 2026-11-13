# Decision P0 — five quick views of the existing engines

**Language / Idioma:** [Español](DECISION-P0.md) · English

**Status:** product view under review; not a new weather model, safety certification, warning service or additional API. Preparation for the MeteoPortinatx 0.6 line; integration version 0.5.1 remains in force until a release decision.

## Product contract

| Profile | Primary question | P0 display | Further detail |
|---|---|---|---|
| Home beside a torrent | What has changed and what should I check? | Verified warning, four observed channels (rain gauges, METAR, radar, lightning), **calculated** caution | Portinatx · Monitoring |
| Boat / mooring | Are there signs of wind or sea conditions and warnings? | Verified warning, wind, sea, lightning; does **not** compare buoys and model without matching | Portinatx · Sea |
| Second home | What is forecast for the home's area? | Selection among published points, institutional warning, snow/temperature/gust forecast by **one** model | Pyrenees · Points and elevations |
| Ski / mountains | What does a model forecast for a resort? | Selectable point, 24 h snow and gust; does not certify slopes, roads or avalanches | Pyrenees · Cross-section and diagnosis |
| Weather | What is observed and what does the engine estimate? | **Cycle audit sheet**: verbatim warnings, measurements with age and evidence, models with their spread, engine reasoning and failing sources; without calling an ensemble fraction a “probability” | Portinatx · Forensics, with per-block links |

The interface is `/decidir/` and retains the current console in the observatories. Links from the portal and both consoles are additive; around 60 sections of the original engine are not rewritten.

## Data contract and guarantees

1. **One document per domain:** only `core.json` is consumed, using `meteoLoadPart(domain, 'core', staticPath)`. Therefore a panel never mixes `core` with `series` or `radar` from different generations. Full analyses take place in the previous console, which retains its atomic loading of parts.
2. **Visible source:** if `METEO_BACKEND_URL` is configured, the API is used *only* with `X-Meteo-Snapshot` and `X-Meteo-Freshness: fresh` accessible through CORS; otherwise it falls back to the **same** `core.json` in the Pages snapshot. This view does not enable the variable or modify Render.
3. **Operational freshness:** UTC/TZ `issued` is mandatory; 60 min for Portinatx and 360 min for the Pyrenees are **display thresholds**, not a guarantee that each station is current. A date more than five minutes in the future, without a time zone or unreadable = `UNKNOWN`. If the cycle is stale, its recommendations and values are suppressed completely to avoid a false impression of currency.
4. **Epistemic separation:** AEMET/warnings are marked as verified only with `official.verificado === true` (coast) or `fuentes.avisos` in state `ok` (mountains). The `quiet` level is **internal** and never means “safe”. `UNKNOWN` instruments are not converted to zero. Mountain data are labelled “model estimate”; they are not equivalent to accumulated snow or road conditions.
5. **Privacy:** `state.json`, private notes, local forensics, manual flood observations (`runoff`/`flooding`) and private address data are not loaded. The profile is not persisted in a cookie or localStorage. Displayed values are inserted as text, not provider HTML. There are no `POST` functions.
6. **Safety:** it does not order someone to move a car or sail, rate mountain safety, or replace civil protection / AEMET / Météo-France / SMA. It is never presented as permanent monitoring or a push alert on Pages/Render Free.

## Weather profile sheet (“Investigate the event”)

The sheet audits **one** engine cycle on one screen. It is not another console, adds no forecasts or indices and gives no safety answer. It comes from the same `core.json` (the `episode` field of `project('meteo', …)`), with no new requests.

1. **Fixed order:** official warning, measured, model and ensemble, own analysis, sources. Provenance is distinguished by border, sign and word, not colour alone. The internal level (0–3) uses monochrome steps; institutional colour appears only in the official warning chip.
2. **Warnings:** read from `official.all` with `activo: true`, deduplicated (CAP and MeteoAlarm repeat the same warning), dropping any that have already expired when consulted and any floor entered by hand in the engine, which is not the authority's text. The level shown is the authority's own, not `level_now`.
3. **No data is not zero:** a channel whose `available` is not exactly `true` is shown as “no data · does not mean calm”, even if it carries `level: 0`. The published age is that of the channel's most recent datum; for models it is the download time and is not shown.
4. **Allow-list:** only known channels show their evidence; of the engine reasons, only those shaped `channel=level` and `suelo institucional = level`. Manual observations, `precaution.hold/decision/exit_conditions`, owner claims, dissent, anomalies, `sources[].detail` and free text are not shown. The Pages snapshot does not go through the backend public projection, so the filter is also applied in the client.
5. **Engine text:** shown verbatim, with four deterministic substitutions: `nan`, `STALE → UNKNOWN`, `MOTION_UNKNOWN`, and `P(24h≥50)=0%` rewritten as a fraction of members. A METAR report more than 6 h older than the cycle is marked as not current.
6. **Models:** the gust and CAPE range is shown only if strict extraction matches every available model; they are 48 h maxima at the point, with no time. No mean or consensus is computed.
7. **Trimmed source:** with the API (no evidence, reasons or claims) the sheet says so and invents nothing. On a cold start (a single cycle in `history`) no transition is shown.
8. **Scope:** Portinatx only. The Pyrenees `core.json` publishes neither channels nor engine reasoning.

## Acceptance tests

- `node tests/test_decision_cards.cjs`: 31 cases: the five profiles, actual channel schema, privacy, `UNKNOWN`, expiry, invalid timestamp, location selection without silently substituting another, and the Weather profile sheet (allow-list, “no data” that is not level 0, expired warnings, trimmed source).
- `python -m unittest discover -s tests`: integration of `/decidir/`, `/decision_cards.js` and static output.
- `python scripts/build_site.py` after exporting *both* domains: produces `site/decidir/index.html` and `site/decision_cards.js`.
- `python scripts/integrity.py --check`: intact manifest.
- The `.pyz` must contain both resources; locally `/public_config.js` remains empty and does not use Render.

**Pending gates:** usability testing with at least five people per segment, task-time records (exploratory 10-second target, not an achieved result), real mobile testing and review with fresh data in both domains. Neither passing CI nor a compact design confirms that a user can resolve a decision in ten seconds. The next phase must add an episode timeline with evidence and Forecast Ledger prospective data.
