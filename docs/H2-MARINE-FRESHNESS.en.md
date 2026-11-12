# H2 — PORTUS and HF radar measurement freshness (11 November 2026)

**Language / Idioma:** [Español](H2-MARINE-FRESHNESS.md) · English

## Risk addressed

A valid network cache is not a recent observation. `cached_source` can return `status="ok"` for a measurement with an old `data_time`. A textual `STALE` warning for a buoy did not stop its wave height from contributing to the observed level.

## Implemented contract

- `status` describes the connector result; it is **not** synonymous with live data.
- `freshness = FRESH | STALE | UNKNOWN` is calculated from the explicitly UTC-zoned measurement time, **never** `fetched_at` or cache age.
- `FRESH`: age between −10 minutes and the family limit. `STALE`: older or more than 10 minutes in the future. `UNKNOWN`: missing/invalid time or time zone, or failed source.
- Provisional conservative limits, **not provider SLAs**: **generic PORTUS 120 min; PORTUS waves 120 min; wind 60 min; sea level 120 min; SOCIB HF radar 90 min**. Calibrate against each product's observed cadence.
- One PORTUS response can have **STALE waves**, **FRESH wind** and **FRESH sea level**. A provider-wide date is insufficient.
- `mar_boyas` and `viento_estaciones` use only samples whose timestamp is FRESH for their respective quantity. Stale data do not add to a level, validate coverage or imply calm.
- `sea_model_check` omits stale wave samples even if PORTUS remains available for other variables. Its model/observation comparison **still requires** spatial and temporal pairing (#8).
- Public `core` retains only `name/status/data_time`, freshness label, age, limit and the three allowed family states; it never exports payloads or private source details.

## Synthetic tests

`tests/test_marine_freshness.py` covers an HF cache valid at download time but stale at measurement time, summer/winter with the repeated local hour on 25 October, timezone-free and future timestamps, provider failure, stale extreme vs fresh modest waves, absent wind with a fresh tide gauge, and safe public projection.

## Limitations and next iteration

This patch does not audit PORTUS cadence live, determine storm probability or change institutional warnings, official thresholds, Render or the production backend. `radar_hf` measures regional Ibiza Channel currents: it is not itself a measurement at Portinatx and does not enter alarm fusion.

Issue #22 still requires checking limits against real data, historical monitoring of cadence changes, and per-station status. The buoy/model comparison must be corrected separately under #8.
