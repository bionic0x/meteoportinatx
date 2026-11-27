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

## 5. Ninety-day prospective campaign

**Current status: the 90-day validation has NOT been started or finished, and it will not be declared complete early.** Its status is not declared in any document: `campaign-status` computes it from the journal and the records. What the code guarantees: `COMPLETADO` requires, all at once, 90 days with cycles that journal new records (no repeated ids, each captured within its interval), 2160 real hours, coverage by UTC hours, 20 distinct QC PASS observations matched and journaled, spread over at least 10 days, and a restore receipt from a copy on another filesystem. What it does **not** guarantee: that the data are authentic against whoever controls the disk (no external signature or timestamp), that `INSTRUMENT_QC_PASS` reflects a real check (the importer declares it), or that "another filesystem" is another physical disk (see the limits in §5.1–5.3). It is also **blocked by A1** (see §5.6): the current wiring yields no scorable pair.

### 5.1 Hash-chained cycle journal

`<METEO_LEDGER>/journal/cycles.jsonl` is an append-only journal. `scripts/forensic_cycle.py` appends an entry on **every** cycle (`OK`, `NO_DATA`, `DEGRADED`, `ERROR`), so gaps and failures leave a trace even though `cycle-health.json` is overwritten. Each entry carries `seq`, `timestamp` (UTC, host clock), `state`, `added_ids`, `added_sha256` (map id → SHA-256 of each added record file), `prev_hash` and `hash` (canonical SHA-256 of the entry without `hash`; the first links to 64 zeros).

`verify` recomputes the chain (sequence, `prev_hash`, hash, canonical form, non-decreasing time), requires every cited id to exist and its file to keep the recorded SHA-256, and checks that every restore receipt is intact and anchored to an existing entry. It returns a top-level `integridad`:

| `integridad` | When | `verify` exit code |
|---|---|---|
| `VERIFICADA` | Intact journal and every entry carries file hashes. | 0 |
| `ROTA` | Reason in `motivo`: `DIARIO_ID_AUSENTE`, `DIARIO_REGISTRO_ALTERADO` (edited value), `DIARIO_ID_DUPLICADO` (id already journaled in an earlier entry), `DIARIO_ID_FUERA_DE_INTERVALO` (`captured_at` outside the interval between the previous entry and its own), `DIARIO_HASH_ALTERADO`, `DIARIO_SECUENCIA_ROTA`, `DIARIO_COLA_INCOMPLETA`, `DIARIO_RECIBO_HUERFANO`, `DIARIO_RECIBO_ALTERADO`… | 1 |
| `UNKNOWN` | Old ledger without a journal (`SIN_DIARIO`, **not migrated**) or first-format entries without `added_sha256` (`parcial: ASIENTOS_SIN_HASH`): existence is checked, content is not. | 3 |

A record with an invalid format still exits with code 2, as before. The `ok` field is kept (`ok = integridad ≠ ROTA`). Selftest and CI only check these codes in synthetic tests (`tests/test_forecast_ledger.py`, `tests/test_ledger_campaign.py`); no CI step and not `forensic_cycle.py` depends on the `verify` exit code.

**Incomplete tail (a half-written line after a crash).** `append_journal` neither deletes nor repairs it: it writes nothing and returns `DIARIO_COLA_INCOMPLETA`; the cycle keeps capturing and ends `DEGRADED` with that reason in `cycle-health.json`, and the campaign becomes `INVALIDO:DIARIO_COLA_INCOMPLETA`. Manual recovery (owner's decision): (1) copy the whole root to a read-only archive as evidence; (2) **do not rewrite** the old journal; (3) start a new campaign with `METEO_LEDGER` pointing to a new, empty directory. The same procedure applies to any `INVALIDO`.

**Remaining limits:** whoever controls the disk can rewrite the whole chain, records and receipts consistently (no external signature or timestamp). Truncating the end of the journal is **not** detectable when no later receipt exists. The interval check uses the host clock: a clock without NTP can produce false `DIARIO_ID_FUERA_DE_INTERVALO` or hide late captures. Records added outside `forensic_cycle.py` (e.g. a direct `nowcast.py export`) are not in the journal.

### 5.2 States and counters (`campaign-status`)

```bash
python3 src/forecast_ledger.py --root "$METEO_LEDGER" campaign-status [--max-gap-hours 48] [--min-coverage 0.8] [--min-pair-days 10]
```

`ledger_campaign.campaign_status(ledger, *, max_gap_hours, min_coverage, min_pair_days)` **accepts no start or end date**. A *data cycle* is an `OK` entry with non-empty `added_ids`; a *data day* is a UTC day with at least one. An `OK` without new records does not count.

**Frozen window.** The window starts at the first data cycle and is frozen at the *anchor entry*: the first data cycle at which 90 data days and at least 90 × 24 real hours since the start both hold. Coverage, pairs and gaps are computed over that window. Later events do not change the state: they are reported in `vigilancia_posterior` (`HUECO_POSTERIOR` if a gap exceeds the threshold).

| State | Condition |
|---|---|
| `SIN_INICIAR` | Journal absent or empty. |
| `EN_CURSO` (`día N/90`) | Intact chain, no gap above the threshold and window still open. |
| `INVALIDO:<motivo>` | Integrity `ROTA` (`DIARIO_…`), corrupt record, an entry `timestamp` later than now + 10 min (`TIMESTAMP_FUTURO`), a gap between data cycles above the threshold inside the window (`HUECO_MAYOR_QUE_UMBRAL`) or, with the window open, time since the last data cycle above the threshold (`HUECO_ABIERTO_MAYOR_QUE_UMBRAL`). |
| `DATOS_COMPLETOS_COBERTURA_INSUFICIENTE` | Window closed with `horas_con_datos / ciclos_esperados` below the threshold: distinct UTC hours with at least one data cycle versus UTC hours in the window. Several cycles in the same hour count once. |
| `DATOS_COMPLETOS_PARES_INSUFICIENTES` | Window closed with fewer than **20 distinct QC PASS observations** matched (D-021 minimum) or spread over fewer than **N UTC days** (`--min-pair-days`, 10 by default). Only pairs whose forecast and observation are both journaled inside the window count; the baseline does not count; 20 models against one observation count as 1. |
| `DATOS_COMPLETOS_RESTAURACION_NO_PROBADA` | All of the above holds, but there is no valid receipt with `origen: copia_externa`, `mismo_dispositivo: false`, `n_observaciones_emparejadas ≥ 20` and anchored at or after the anchor entry. A `copia_local` or same-device receipt is never enough (reason in `motivo_restauracion`). |
| `COMPLETADO` | All at once: 90 data days, ≥ 2160 real hours, hourly coverage ≥ threshold, ≥ 20 matched observations over ≥ N days, intact chain and a valid receipt from a copy on another device. |

**Thresholds, the owner's decision** (proposed by the audit, not calibrated): maximum gap 48 h; minimum hourly coverage 0.8; matched observations spread over at least 10 UTC days. `ERROR`/`NO_DATA` cycles do not close a gap. The intermediate `DATOS_COMPLETOS_*` states cannot become `COMPLETADO` within the same campaign, except the restore one (a valid external receipt is enough). The text summary only says "completado" when the state is `COMPLETADO` and never says "restauración probada".

Counters: data days, real hours in the window, expected / recorded / `OK` / data cycles, coverage, cycles per state, gaps (> 1.5 h between data cycles) and maximum gap, open gap, fraction of `UNKNOWN` observations in the window, hours with data, raw pairs, matched observations (no baseline) and days with pairs in the window, and exclusions by reason (whole archive). **Limit:** episodes are counted as days (`event_id` = window day); consecutive days of the same storm are not independent.

### 5.3 Restore drill

```bash
# Only checks that this disk is readable (origen: copia_local; never enough for COMPLETADO):
METEO_LEDGER="$HOME/meteoportinatx-private/forecast-ledger" python3 scripts/ledger_restore_drill.py
# Restores FROM an existing external copy (another disk, private-repository clone):
METEO_LEDGER="$HOME/meteoportinatx-private/forecast-ledger" python3 scripts/ledger_restore_drill.py --source /media/backup/forecast-ledger
```

Takes the same lock as the cycle, copies `local/` and `journal/cycles.jsonl` from the source into a clean temporary directory and, with the same clock, compares against the original ledger `verify`, the journal, `score` (with its exclusions) and the bundle SHA-256. `--source` must be an existing absolute directory outside the ledger; the copy must be in sync with the ledger, otherwise the receipt is `ok: false`. It writes a hashed receipt to `journal/restore-receipts/<sha256>.json` with `origen`, `journal_seq`, journal head, restored raw `n_pares` and `n_observaciones_emparejadas`, and `mismo_dispositivo` (same `st_dev` as the ledger). `COMPLETADO` requires `mismo_dispositivo: false`, but another filesystem does not prove another physical disk (it may be another partition of the same disk). **`import` is not suitable for this:** it leaves every record `IMPORTED_UNATTESTED`, excluded from scoring. **Limit:** the receipt is neither signed nor timestamped; whoever controls the disk can forge it.

### 5.4 Metrics (after the campaign)

- **Strata:** domain / site / variable / model / lead (1–2, 3–4, 5–6 h) / month / regime; denominators, `UNKNOWN` fraction and exclusions per stratum.
- **Baselines:** Hs persistence (exists; since this change it is not frozen if the latest Hs is older than 120 min, D-021) and **monthly precipitation climatology: does not exist yet**.
- **Intervals:** episode-block bootstrap, only with ≥ 10 blocks; otherwise `INSUFICIENTE`. Do not claim improvement from synthetic pairs.
- **Drift:** monthly MAE and bias against persistence; shifts in the `UNKNOWN` fraction and rejections; model name changes; `captured_at − issued_at` latency.

### 5.5 Activation: what the owner needs to provide

None of this can be done by code or by an agent:

1. **Private repository** for the durable ledger copy. **An orphan branch in the public repository is rejected**: it would publish the measurements (out of scope, see below) and raises PORTUS licence questions.
2. **Fine-grained PAT or deploy key with minimal scope** (contents write on that private repository only). **Never in the repository or in prompts**; monitor its expiry.
3. **Branch protection** on the private repository (no force-push or deletion). Git is not WORM.
4. **Always-on Linux machine** with the systemd timer installed, `loginctl enable-linger <user>` (without linger the user service stops at logout), NTP-synchronised clock and an **encrypted disk**.
5. **Invalidity thresholds** (maximum gap, 48 h by default; minimum hourly coverage, 0.8 by default; minimum days with pairs, 10 by default) and the **PORTUS QC criterion** (QC gate 1 of D-021).
6. An **external copy on another disk** of the ledger kept in sync, and a `--source` drill on it when the window closes.

### 5.6 Blocker A1: 0 scorable pairs with the current wiring

At Portinatx precipitation has no rain gauge within ≤ 3 km and PORTUS Hs enters as `UNKNOWN`; in the Pyrenees there are Météo-France observations with `INSTRUMENT_QC_PASS` but no forecast frozen at those coordinates. Result: **0 scorable pairs**. Starting the 90 days like this would end at best in `DATOS_COMPLETOS_PARES_INSUFICIENTES`. Proposal (separate change, **not implemented here**): freeze forecasts at the coordinates of the Pyrenean Météo-France stations with QC PASS; for PORTUS, the owner closes the QC criterion (which flags or checks turn an Hs into `INSTRUMENT_QC_PASS`).

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
  - wave-model Hs (m) **at each PORTUS buoy position** (#8), next 1–6 h, and its persistence reference (`baseline=true`, latest measured Hs; not frozen if older than 120 min, D-021).
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

`scripts/forensic_cycle.py` captures Portinatx and verifies the private ledger. A lock prevents two simultaneous runs of this command; it does not stop another process using `nowcast.py` directly. The process requires `METEO_LEDGER` to be an absolute path outside the repository, creates the private directory with mode 700 or rejects an existing one accessible by group or others, and atomically writes `cycle-health.json` with counts, date and status `OK`, `NO_DATA`, `DEGRADED` or `ERROR`. It does not save provider output or error messages, which could contain credentials. `OK` only certifies that the cycle and local check finished; it does **not** certify a good forecast, QC for observations or functioning backups. A run with no new records (including repeated cycles in the same hour) is marked `NO_DATA` and is not considered a success. The execution limit is 20 minutes; an active lock returns code 75. Every cycle, whatever its state, also appends an entry to the hash-chained journal (§5.1); if it cannot, the cycle ends as `ERROR`, and if the journal has an incomplete tail, as `DEGRADED` without writing or repairing anything.

On an always-on Linux computer you own, with the repository already installed and private engine data/configuration in place, first run manually:

```bash
export METEO_LEDGER="$HOME/meteoportinatx-private/forecast-ledger"
python3 /RUTA/ABSOLUTA/meteoportinatx/scripts/forensic_cycle.py
cat "$METEO_LEDGER/cycle-health.json"
```

Scheduling templates `scripts/systemd/meteo-forensic.service` and `.timer` are provided: copy both to `~/.config/systemd/user/`, replace `/PATH/TO` with actual absolute paths in the service, then run `systemctl --user daemon-reload`, `systemctl --user enable --now meteo-forensic.timer` and `systemctl --user list-timers meteo-forensic.timer`. Inspect `systemctl --user status meteo-forensic.service` and `journalctl --user -u meteo-forensic.service`. The service runs at startup and hourly while the computer and user service are active. The timer may catch up a missed run when it returns; it **does not retrospectively recreate forecasts or observations for hours without service**. The user service stops at logout unless you enable `loginctl enable-linger <user>`. Do not put keys in these files; the engine loads its private local configuration.

This mechanism **has not been installed on any machine** and does not create durable hosting. Render Free has ephemeral storage and is unsuitable for this archive; GitHub Pages/Actions are not a persistent private ledger. An independent backup and tested restore remain essential. A computer failure or absence produces no captures; monitor the age of `cycle-health.json` and the timer externally. Data availability and QC remain subject to the limitations in section 7.
