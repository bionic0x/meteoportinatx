# P0 — Forecast Ledger / prospective verification archive

**Language / Idioma:** [Español](FORECAST-LEDGER-P0.md) · English

**Status:** isolated local prototype (not deployed or integrated into alerts). Implementation of priority [#7](https://github.com/bionic0x/meteoportinatx/issues/7), based on [Agency Agents research #6](https://github.com/bionic0x/meteoportinatx/pull/6). **This does not mean that MeteoPortinatx has demonstrated forecast skill.**

## 1. Purpose and scope

Freeze a forecast **before** its validity window begins, save the observation afterwards, and document exactly which pairs can be compared. This avoids the illusion of a backtest generated with later data. Institutional rules, the alert engine, public data and CNP connectors are **not modified**.

`src/forecast_ledger.py` uses Python 3.10+ without external packages or Internet access. It operates on a **private user-managed** directory; do not use Render Free for archiving. Records are created by temporary write, `fsync` and atomic hard link, which never replaces an earlier record. The identifier derives from a canonical key (model, site, issue time and window). If the same identity attempts to enter a changed forecast, it is **rejected**. This is not a secure clock or notarisation system: whoever controls the disk can delete or replace all the evidence.

## 2. Data schema and limits

**Forecast:** `event_id`, `domain` (`portinatx`/`pirineo`), `site_id`, lat/lon, `issued_at`, `provider_run_at`, `valid_from`, `valid_to`, `provider`, `model`, `family`, `variable`, `unit`, `mode` (`amount` or `threshold`), `prediction`, `source_id`, `source_license`. Optional: `threshold`, `probability_raw` (thresholds only), `baseline`, and SHA-256 hashes of configuration, data or commit.

Actual local capture time is `captured_at`. **PROSPECTIVE** requires `issued_at` before validity and `captured_at < valid_from`. Any later upload is labelled **HINDCAST**, even if the file claims the forecast was issued earlier. There is no option to force `PROSPECTIVE`.

**Observation:** `observed_from`, `observed_to` window, station identifier, coordinates, value in canonical units, `source_type` (`instrument` or `community`), `qc` (`INSTRUMENT_QC_PASS`, `UNKNOWN`, `REJECTED`), source and licence. The value is the importer's assertion, **not independent validation**. A `community` report cannot be declared `INSTRUMENT_QC_PASS`. Unexpected fields, personal names, comments and links containing credentials are not accepted. Only technical identifiers are retained.

Initial variables: precipitation (`mm`), snow (`cm`), temperature (`C`), gust (`m/s`) and significant wave height (`m`). **Artificial snow is not converted into natural snow**, accumulation periods are not mixed, and a remote station is not extrapolated to a nearby point without geographical control.

## 3. Conservative pairing and scoring

All of the following are required: same episode, domain, site, variable and unit; an **exact** match between forecast and observation windows; geodesic distance no greater than the declared radius (default `3 km`); exactly one instrument observation marked QC PASS. If more than one QC PASS measurement exists, the pair is excluded as ambiguous until an explicit rule is defined; the maximum is never chosen arbitrarily.

Other reasons are reported: HINDCAST/late forecast, future window, missing observation, observation outside the radius or with unknown QC, no identical window, and multiple candidate stations. **Missing ≠ 0.** External imports are reconstructed, but are not scored as prospective without external attestation.

- `amount`: `MAE`, signed bias (`forecast - observed`), `n_pairs`, independent episodes.
- `threshold`: `TP/FP/FN/TN` matrix, `CSI`, `POD`, `FAR`; `None` if a denominator does not exist. If an original probability exists, Brier is explicitly **raw/uncalibrated**, not calibrated `P(alerta)` (alert probability).
- Comparison: only against a `baseline=true` forecast paired with **the same** observation and threshold. `mean_loss_reduction` is descriptive, not inference or a scientific victory.
- Every output declares `verification_status=EXPLORATORY_UNCALIBRATED` and `meteorological_skill_verified=false`.

## 4. Local execution

```bash
# Private directory **outside the repository**; do not use /tmp or Render Free.
export METEO_LEDGER="$HOME/meteoportinatx-private/forecast-ledger"
python3 src/forecast_ledger.py --root "$METEO_LEDGER" add-forecast --json /ruta/forecast.json
# Once the window has ended and an instrument with known QC is available:
python3 src/forecast_ledger.py --root "$METEO_LEDGER" add-observation --json /ruta/instrument-observation.json
python3 src/forecast_ledger.py --root "$METEO_LEDGER" verify
python3 src/forecast_ledger.py --root "$METEO_LEDGER" score --max-distance-km 3
python3 src/forecast_ledger.py --root "$METEO_LEDGER" export --out "$HOME/meteoportinatx-private/backup-20261111.json"

# On another machine: verify the archive but do **not** automatically promote
# imported forecasts to evidence of prospective prediction.
python3 src/forecast_ledger.py --root "$HOME/meteoportinatx-restore" import --bundle "$HOME/meteoportinatx-private/backup-20261111.json"
```

The JSON files must contain exactly the listed fields. For example, a precipitation forecast for a future UTC hour:

```json
{
  "event_id": "episode-20261111-demo", "domain": "portinatx", "site_id": "portinatx",
  "lat": 39.1136, "lon": 1.5180, "valid_from": "2026-11-12T11:00:00Z",
  "valid_to": "2026-11-12T12:00:00Z", "issued_at": "2026-11-11T08:00:00Z",
  "provider_run_at": "2026-11-11T06:00:00Z", "provider": "example",
  "model": "synthetic-v0", "family": "synthetic", "variable": "precipitation_mm",
  "unit": "mm", "mode": "amount", "prediction": 5.0, "source_id": "example-demo",
  "source_license": "SYNTHETIC", "baseline": false
}
```

This example is **synthetic**, not a real weather forecast. To retain prospective status, capture must occur before `valid_from`, and the issuer/model must be documented. Values may fail if run outside the illustrative window.

## 5. Ninety days of research and connector-integration criteria

1. **Weeks 1–2:** verify source contract, unit, period, coordinates, licence and capture before the start. Do not copy personal data or forum content to the ledger.
2. **Weeks 2–12:** a supervised connector automatically freezes each forecast issued *before* the event; previously verified zero-cost external storage, with exports and restore tests. **The connector does not yet exist:** current operation is manual.
3. **After 90 days:** stratify by family/station/horizon/regime; calculate denominators, `UNKNOWN` fraction and excluded cases; compare baselines and estimate episode-blocked intervals if the independent sample allows it. Do not claim improvement from 20 synthetic pairs.
4. **Gates:** verified provenance and licences; active instrumentation; disconnect checks; persistent data with validated restore; out-of-sample skill; reporting of false alarms and critical misses.

**Deliberately out of scope:** scraping ClimayNievePirineos/forums without permission, automatic weight training, official forecasts, public publication of the measurement archive, user ingestion and alert execution. If a model description conflicts with a non-comparable measurement, output `UNKNOWN/NO_COMPARABLE`.

## 6. Reality Checker — assessment of this delivery

- **Software:** tests of state, timing, spatial/temporal parity, schema privacy, integrity failures, export/import and baseline; CI matrix to be checked in this PR.
- **Real persistence:** **NEEDS WORK**; no durable external store or automated backup exists. JSON export requires an independent copy and recovery verification.
- **Forensic integrity:** **NOT ATTESTED**; hashes without an external signature do not detect deletion/replacement of the entire archive.
- **Meteorological accuracy:** **NOT MEASURED**; all tests use synthetic data.
- **Operational status:** **EXPERIMENTAL / NO DEPLOY**.

## 7. Shadow logging from the cycle (#7, optional)

`src/ledger_shadow.py` connects the Portinatx cycle to this ledger **only if** `METEO_LEDGER` points to a private directory outside the repository (paths inside the repository are rejected). It does not alter levels, warnings or public data; failures are ignored and reported in the `export` result (`ledger_sombra`).

- **Forecasts frozen before their window**, once per UTC hour (five-minute cycles do not multiply records):
  - hourly precipitation (mm) from each deterministic model at the Portinatx point for the next 1–6 h;
  - wave-model Hs (m) **at each PORTUS buoy position** (#8), next 1–6 h, and its persistence reference (`baseline=true`, latest measured Hs).
- Buoy **observations** for hours already closed (first sample in the hour). Missing values are never frozen as 0.
- `event_id` uses the window's day so forecast and observation share an identity.

**Limits (#7 gate remains open):**

- PORTUS provides no quality control here, so observations enter with `qc=UNKNOWN` and the ledger excludes them (`NO_QC_PASS_INSTRUMENT_WITHIN_RADIUS`) until the owner defines a verified QC criterion.
- Site precipitation has no instrument rain gauge within ≤3 km, so it is frozen without a possible pair.
- `provider_run_at` is the download instant (upper bound), not the actual run time.
- Durable storage, copies and the restore test remain the operator's responsibility.

```bash
export METEO_LEDGER="$HOME/meteoportinatx-private/forecast-ledger"
python3 src/nowcast.py export --domain portinatx
python3 src/forecast_ledger.py --root "$METEO_LEDGER" verify
```

## 8. Supervised cycle on persistent equipment (Linux, optional)

`scripts/forensic_cycle.py` captures Portinatx and verifies the private ledger. A lock prevents two simultaneous runs of this command; it does not stop another process using `nowcast.py` directly. The process requires `METEO_LEDGER` to be an absolute path outside the repository, creates the private directory with mode 700 or rejects an existing one accessible by group or others, and atomically writes `cycle-health.json` with counts, date and status `OK`, `NO_DATA`, `DEGRADED` or `ERROR`. It does not save provider output or error messages, which could contain credentials. `OK` only certifies that the cycle and local check finished; it does **not** certify a good forecast, QC for observations or functioning backups. A run with no new records (including repeated cycles in the same hour) is marked `NO_DATA` and is not considered a success. The execution limit is 20 minutes; an active lock returns code 75.

On an always-on Linux computer you own, with the repository already installed and private engine data/configuration in place, first run manually:

```bash
export METEO_LEDGER="$HOME/meteoportinatx-private/forecast-ledger"
python3 /RUTA/ABSOLUTA/meteoportinatx/scripts/forensic_cycle.py
cat "$METEO_LEDGER/cycle-health.json"
```

Scheduling templates `scripts/systemd/meteo-forensic.service` and `.timer` are provided: copy both to `~/.config/systemd/user/`, replace `/PATH/TO` with actual absolute paths in the service, then run `systemctl --user daemon-reload`, `systemctl --user enable --now meteo-forensic.timer` and `systemctl --user list-timers meteo-forensic.timer`. Inspect `systemctl --user status meteo-forensic.service` and `journalctl --user -u meteo-forensic.service`. The service runs at startup and hourly while the computer and user service are active. The timer may catch up a missed run when it returns; it **does not retrospectively recreate forecasts or observations for hours without service**. Check the system's user-service configuration: it may stop at logout. Do not put keys in these files; the engine loads its private local configuration.

This mechanism **has not been installed on any machine** and does not create durable hosting. Render Free has ephemeral storage and is unsuitable for this archive; GitHub Pages/Actions are not a persistent private ledger. An independent backup and tested restore remain essential. A computer failure or absence produces no captures; monitor the age of `cycle-health.json` and the timer externally. Data availability and QC remain subject to the limitations in section 7.
