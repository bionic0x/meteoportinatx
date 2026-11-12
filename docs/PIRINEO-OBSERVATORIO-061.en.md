# Pyrenees 0.6.1 — expanded observatory

**Language / Idioma:** [Español](PIRINEO-OBSERVATORIO-061.md) · English

**Scope:** Andorra, Puymorens, Cerdanya/Cerdagne, Capcir. Parity of **navigation, presentation and traceability** with Portinatx, NOT instrumentation. Marine data and thresholds are not inherited.

| View | Effective contract |
|---|---|
| Monitoring | Three separate axes: AEMET CAP / MeteoAlarm institutional warning, observation ≤90 min, model-based weather diagnosis; source failure → UNKNOWN |
| Satellite/radar | Links to official EUMETSAT, AEMET and Meteocat viewers; Pyrenees raster and lightning remain **NOT_INTEGRATED**; no simulated coverage |
| Atmosphere | T, Td, RH, cloud cover, wind, gust and two ARPEGE profiles, 700 hPa, Froude, freezing level and Tw0 |
| Terrain/cross-section | Terrarium DEM, temperature and precipitation maps, snow by mountain side and Andorra–Puymorens–Cerdanya cross-section |
| Surface | AEMET, Meteoclimatic, METAR, Meteociel (secondary network), optional Météo-France DPObs (official network); inversion/föhn and provenance |
| Locations | Forecast at DEM altitude and 24–72 h metrics for passes and resorts |
| Models | AROME HD, ICON-EU, ECMWF IFS by location; three-hour blocks of T, Td, RH, wind, clouds, rain and snow |
| Ensemble | Existing independent ECMWF/ENS, GEFS, ICON-EPS 15-day meta-analysis; no calibrated probabilities |
| Forensics | Revisions between runs and ERA5-Land context when available; do not confuse forecast changes with observed skill |
| Governance | Cache status and age by source, absent key or CNP permission, traceability of terms |
| Laboratory | Hypothetical gust threshold in the browser only; no changes to the engine, warnings or ledger |

## Safety, quantities and missing data

- The frontend reads published **Pyrenees-domain** data, not Portinatx endpoints. Updates depend on the local collector and Pages workflow; this does not amount to continuous monitoring.
- Rain and snow aggregation requires **all three hours** with finite non-negative measurements. If any datum in the block is missing, the value is null, never zero.
- AEMET and Météo-France stations are labelled official; Meteociel is secondary and does not have the same traceability as the original measurement.
- Météo-France observations are **raw real-time data** (24-hour retention, not a QC climatological archive). Station count is limited, the eight-digit ID is preserved, explicit UTC time is used, K / m/s / Pa units are validated and data older than 120 minutes are rejected. Hourly rain and instantaneous gusts are not labelled as daily totals.
- The connector is enabled only with the Actions secret `METEOFRANCE_API_KEY`, sent in the `apikey` header (the portal's API Key type; different from an OAuth2 Bearer token); it is not logged, published or sent to third parties. If absent, the source is marked as lacking a key. Real access from GitHub Actions had not yet been verified at the time of this record.
- Names and identifiers are obtained from the official catalogue; Météo-France changed identifiers on 2026-04-16, so historical codes are not hard-coded.
- The catalogue is not guaranteed for all areas: without a station or with stale data, UNKNOWN.
- Avalanches, lightning, the inversion layer and radar blocked by mountain ranges require independent sources and verification, especially for skiing and mountain activities. The hierarchy of official warnings is maintained.

### References

- https://www.data.gouv.fr/dataservices/api-donnees-dobservation
- https://confluence-meteofrance.atlassian.net/wiki/spaces/OpenDataMeteoFrance/pages/853639294/
- https://confluence-meteofrance.atlassian.net/wiki/spaces/OpenDataMeteoFrance/pages/1603796993/

### Live authentication verification

Pages deployment #43069942357 published the twelve tabs and engine 0.6.1, but the DPObs v2 `/liste-stations` request received HTTP 401 with `Authorization: Bearer`. The installed credential has the portal API Key format, not the OAuth2 access format; the client now sends `apikey`. A later publication must confirm HTTP 200 and fresh stations before declaring this source active. Probe #43069851447 tested the DPObs v1 route (not covered by the v2 subscription) and returned 403: that does not demonstrate that the v2 API is inactive. No key was included in files or logs.
