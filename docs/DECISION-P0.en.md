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
| Weather | What is observed and what does the engine estimate? | Six observational channels, institutional diagnosis, without calling an ensemble fraction a “probability” | Portinatx · Forensics |

The interface is `/decidir/` and retains the current console in the observatories. Links from the portal and both consoles are additive; around 60 sections of the original engine are not rewritten.

## Data contract and guarantees

1. **One document per domain:** only `core.json` is consumed, using `meteoLoadPart(domain, 'core', staticPath)`. Therefore a panel never mixes `core` with `series` or `radar` from different generations. Full analyses take place in the previous console, which retains its atomic loading of parts.
2. **Visible source:** if `METEO_BACKEND_URL` is configured, the API is used *only* with `X-Meteo-Snapshot` and `X-Meteo-Freshness: fresh` accessible through CORS; otherwise it falls back to the **same** `core.json` in the Pages snapshot. This view does not enable the variable or modify Render.
3. **Operational freshness:** UTC/TZ `issued` is mandatory; 60 min for Portinatx and 360 min for the Pyrenees are **display thresholds**, not a guarantee that each station is current. A date more than five minutes in the future, without a time zone or unreadable = `UNKNOWN`. If the cycle is stale, its recommendations and values are suppressed completely to avoid a false impression of currency.
4. **Epistemic separation:** AEMET/warnings are marked as verified only with `official.verificado === true` (coast) or `fuentes.avisos` in state `ok` (mountains). The `quiet` level is **internal** and never means “safe”. `UNKNOWN` instruments are not converted to zero. Mountain data are labelled “model estimate”; they are not equivalent to accumulated snow or road conditions.
5. **Privacy:** `state.json`, private notes, local forensics, manual flood observations (`runoff`/`flooding`) and private address data are not loaded. The profile is not persisted in a cookie or localStorage. Displayed values are inserted as text, not provider HTML. There are no `POST` functions.
6. **Safety:** it does not order someone to move a car or sail, rate mountain safety, or replace civil protection / AEMET / Météo-France / SMA. It is never presented as permanent monitoring or a push alert on Pages/Render Free.

## Acceptance tests

- `node tests/test_decision_cards.cjs`: 13 cases covering the five profiles, actual channel schema, privacy, `UNKNOWN`, expiry, invalid timestamp and location selection without silently substituting another.
- `python -m unittest discover -s tests`: integration of `/decidir/`, `/decision_cards.js` and static output.
- `python scripts/build_site.py` after exporting *both* domains: produces `site/decidir/index.html` and `site/decision_cards.js`.
- `python scripts/integrity.py --check`: intact manifest.
- The `.pyz` must contain both resources; locally `/public_config.js` remains empty and does not use Render.

**Pending gates:** usability testing with at least five people per segment, task-time records (exploratory 10-second target, not an achieved result), real mobile testing and review with fresh data in both domains. Neither passing CI nor a compact design confirms that a user can resolve a decision in ten seconds. The next phase must add an episode timeline with evidence and Forecast Ledger prospective data.
