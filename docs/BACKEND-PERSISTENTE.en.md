# Backend 0.5.1: Render Free and real persistence

**Language / Idioma:** [Español](BACKEND-PERSISTENTE.md) · English

## Deployed status

The public `meteoportinatx-backend-free` service uses Python's standard library on **Render Free** (Frankfurt), without a paid disk or database. Its HTTP API listens on the port assigned by Render and exposes `/healthz`, `/v1/status`, `/v1/{domain}/api/{part}.json` and `/v1/forensics/summary` as read routes. `POST` returns 405.

**It is neither persistent nor continuous.** Render Free can sleep, restart or discard local storage. Consequently, `state.json`, original cycles, SQLite and the SHA-256 chain are **temporary**. The configured Portinatx (300 seconds) and Pyrenees (10,800 seconds) intervals are *best-effort intentions* only while the process is active, not an SLA or warning system.

## Safe integration

The server declares `X-Meteo-Freshness` and `X-Meteo-Snapshot` and exposes both headers by CORS exclusively to the GitHub Pages origin (and two local development origins). The website downloads **all** parts of each domain from the same snapshot; if any part is missing, stale, has a different identifier or connection fails, it loads **all** parts from GitHub Pages. Generations and sources are not mixed.

The public `portinatx/core` projection uses an explicit allowlist, including subfields for institutional warnings, sources, channels and governance. Owner-written evidence is not exported; new schema changes are denied by default. Observations and forecasts are labelled as the project's own estimates and never as official warnings.

## Forensics and verification

Full weather data remain in the engine's private paths. SQLite stores metadata and links `core` hashes by domain; the `verify` command checks chain consistency and the latest public `core` if present. **This is neither an external signature nor a tamper-proof log**: anyone who can alter the database can also recalculate the chain. On Render Free it does not survive suspensions either. Accumulated forensic learning needs external storage and backups, which are not configured.

## Operation

```bash
python src/nowcast_backend.py serve --port 10000
python src/nowcast_backend.py status
python src/nowcast_backend.py verify
```

Check `/healthz`, `/v1/status` and exposure of CORS headers. In GitHub Actions, configure `METEO_BACKEND_URL` only with the public HTTPS Render origin and run Pages publication; the interface retains the static fallback.

## Limitations

- No persistence, strong freshness guarantees or uninterrupted cron.
- Historical DANA data are not automatically recovered on Render Free.
- Synthetic tests do not replace validation with live weather sources.
- AI models and their products require checks of freshness, availability and provenance.
- Always consult AEMET / Civil Protection and official mountain services for safety decisions.
