# Source catalogue, climate context and provenance-labelled knowledge

**Language / Idioma:** [Español](CATALOGO-FUENTES.md) · English

**Status:** contract and reading implemented and tested with synthetic data. **No real sidecar exists yet** and **no new source has been tested against its actual service**. None of this alters warning levels. Companion document in the Claude project: `claude/catalogo-fuentes-y-conocimiento.md`.

## 1. What was added

| Piece | Location | Effect |
|---|---|---|
| Source catalogue with licence and verification status | `src/knowledge_base.py` (`SOURCE_CATALOG`) | Executable documentation; consistency test |
| Provenance-labelled priors (`HYPOTHESIS`) | `knowledge_base.PRIORS`, `SYNOPTIC_PRIORS` | Only the wet-bulb threshold is used; synoptic priors have `used_in_fusion=False` |
| Threshold provenance | `knowledge_base.THRESHOLD_PROVENANCE`, `METEOALERTA_ANNEX1 = None` | States which `CFG` thresholds are unverified; drift test |
| Validated sidecar reading | `knowledge_base.read_sidecar`, `context_bundle` | `ok / sin_datos / caducado / invalido`; never throws |
| `contexto` source | `portinatx_degen.src_contexto` (`kind="context"`) | `deshabilitado` without a valid sidecar (UNKNOWN). Does not enter `fuse` |
| Rain context note | `portinatx_degen.context_notes`, snapshot `context` key | Places observed mm/1 h in the climatological band; informative |
| Pyrenees `contexto` block | `pirineo.py` (core) | Status and provenance of Pyrenees sidecars, without values |
| Phase at 0.7 °C wet bulb | `pirineo.snow_frac`, `profile_diag.tw07_m` | Ramp centred on 0.7 °C (previously 0.5 °C without provenance); `tw07_m` is an additional diagnostic. Existing elevation offsets unchanged |
| Backend does not count `context` as a usable source | `nowcast_backend.py` | A context source cannot support publication if all real sources fail |

## 2. Principles

1. **Dependency-free core.** `xarray`, `cdsapi`, `copernicusmarine`, `satpy`, `scores`… belong in a separate sidecar that writes JSON. If it is absent, the core does not break.
2. **Context ≠ observation ≠ warning ≠ model.** Reanalysis is a prior or context percentile, never confirmation.
3. **Missing data is not calm.** Any status ≠ `ok` ⇒ UNKNOWN.
4. **No invented thresholds.** Meteoalerta thresholds are in Annexes 1/2 of the plan (not obtained). `METEOALERTA_ANNEX1` remains `None` until loaded with provenance.
5. **Calibrate with a sufficient sample.** Phase threshold and percentiles are hypotheses until ≥30 local events are available.

## 3. Sidecar contract

File `<dir>/<name>.json`; `<dir>` = `$METEO_SIDECAR_DIR` or `<HOME>/sidecar`. Known names and maximum ages:

| Name | Domain | Expiry |
|---|---|---|
| `climatologia_era5land` | portinatx | 45 d |
| `climatologia_cerra` | pirineo | 45 d |
| `sst_cmems` | portinatx | 48 h |
| `nieve_hrsi` | pirineo | 7 d |
| `verificacion_scores` | portinatx | 10 d |

```json
{
  "schema": 1,
  "name": "climatologia_era5land",
  "generated_at": "2026-11-11T06:00:00+00:00",
  "source": "ERA5-Land, celda más próxima a Portinatx, 1991-2020",
  "licence": "CC-BY 4.0",
  "domain": "portinatx",
  "kind": "context",
  "values": {"precip_1h_mm": {"p50": 0.2, "p90": 4.0, "p95": 8.0, "p99": 20.0, "max": 55.0}}
}
```

Rejected (`invalido`) if: a key is missing, there are unexpected keys, `schema` ≠ 1, `name/kind/domain` are inconsistent, `generated_at` lacks a time zone or is in the future, `values` is not a finite and bounded object (NaN/Infinity), or the name does not match `^[a-z0-9_]{1,40}$`. Currently interpreted `values` schema: only `precip_1h_mm` (monotonic percentile table). Other sidecars are read and publish their status, but no code interprets their values yet.

## 4. What is NOT done

- No real sidecar (ERA5-Land/CERRA/CMEMS/HR-S&I download, percentile calculation) or workflow exists.
- Meteoalerta thresholds have not been loaded.
- 0.7 °C is literature from Catalonia applied to Cerdanya/Andorra without calibration; the ramp and `tw07_m` are hypotheses.
- Licences marked `UNVERIFIED` in the catalogue must be checked before derived data are redistributed (especially Meteocat).
- The AEMET hourly archive (B954/LEIB) needs to start being archived now: there is no backfill. Related: `docs/FORECAST-LEDGER-P0.md`.

## Additional sidecar: ERA5-Land Pyrenees (manual and experimental)

`scripts/sidecar_era5land_pirineo.py` calculates monthly daily-rainfall tables for wet days at Pyrenean points from ERA5-Land time series. Its accumulation convention and CSV structure are synthetically validated; **no real CDS request has been made**. Before operational use, run `--probe` and verify coverage, periods, metadata, licence terms and attribution.

Reference commands: `python scripts/sidecar_era5land_pirineo.py --probe` and `python scripts/sidecar_era5land_pirineo.py --from-dir DIR --out data/sidecar`. Workflow `.github/workflows/sidecar-era5land.yml` is exclusively manual and generates an artifact for review; it does not modify the site or Render.

The optional output `climatologia_era5land_pirineo.json` is a scientific prior. `pirineo.core.contexto.notas_lluvia_24h` only displays forecast comparisons against percentiles; it does not modify warnings, snow calculation or alarm levels. Missing, invalid or expired file => `UNKNOWN`.
