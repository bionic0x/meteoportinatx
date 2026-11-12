# GitHub Pages publication — MeteoPortinatx Unified v0.5.1

**Language / Idioma:** [Español](DESPLIEGUE-WEB.md) · English

## Read-only hosting: GitHub Pages

- Public URL, with publication confirmed by the workflow: `https://bionic0x.github.io/meteoportinatx/`.
- Configuration already applied: repository → Settings → Pages → Build and deployment → Source: **GitHub Actions**.
- Then: Actions → **Publish unified meteorological website** → Run workflow. Automatic deployment is triggered when `main` changes and every six hours (`23 */6 * * *`, UTC). GitHub Actions can delay scheduled jobs.
- If data are missing, stale, or an export fails, publication **stops** and does not fabricate weather data. The site already published can become stale; check `core.issued` and the run logs.

## Guarantees and limitations

The automation runs a single `src/nowcast.py export` for both domains, validates the package before upload with `scripts/build_site.py`, and publishes through `actions/upload-pages-artifact` and `actions/deploy-pages`. The site includes `/portinatx/` and `/pirineo/`.

This is **NOT a five-minute monitoring service**: the nominal interval is six hours and the files are static. It offers no push notifications, active monitoring, or persistent forensic archive between runner executions. Render Free currently offers an experimental read-only backend, but sleeps after inactivity and does not retain SQLite or `state.json`; it therefore does not enable continuous monitoring or a durable forensic archive. Independent external storage and guaranteed regular execution are needed for these capabilities.

Only `dem.json` (non-sensitive terrain) is cached. State, personal forensic records and `config.env` are never cached or included in the Pages artifact. `AEMET_API_KEY` is an optional GitHub Secret and must not appear in code, logs or JSON. A failed provider connection is identified as `UNKNOWN` or an error.

Results are diagnostic estimates, not official alerts; AEMET, Civil Protection, SMA, Météo-France and mountain bulletins remain authoritative. Use of Open-Meteo is subject to its terms of use and CC BY 4.0 attribution.

## Data bridge v0.5.1

The backend exposes `X-Meteo-Snapshot` and `X-Meteo-Freshness` via CORS. The browser loads each domain as an atomic set: if parts have different generations, are missing or expire, the **entire set** from GitHub Pages is used. The URL is optionally configured using the public Actions variable `METEO_BACKEND_URL`. **Do not enable it until the fix is deployed to Render and its actual headers have been validated.** Keys and private state must never be sent to the browser.
