# Reproduced real case — spatial wave diagnosis (#8)

**Language / Idioma:** [Español](REPRODUCCION-ESPACIAL-20261111.md) · English

**Observed snapshot**, not synthetic: GitHub Pages workflow [#43051163150](https://github.com/bionic0x/meteoportinatx/actions/runs/43051163150), commit `535c1e4e8abdf3b33fdc8b9111d7055dbe1a6c35`, `github-pages` artifact id `13869591734` (published ZIP SHA-256: `2a3db47d765ff7615de78de4dc1147c2c80541a382efdab78ed74a05b8e9bc42`). Public `portinatx/api/core.json` issued at **2026-11-11T15:43:48Z**. Instrument data are from PORTUS/Puertos del Estado; the Open-Meteo Marine model is served in the same snapshot. Values were selectively copied into `tests/fixtures/spatial_20261111.json`; this is not independent certification of measurement quality.

| Field | Dragonera buoy | Model in Portinatx bay |
|---|---:|---:|
| Coordinates | 39.563, 2.097 | 39.145, 1.525 |
| UTC time | 11 Nov 2026, 15:00 | 11 Nov 2026, 15:00 |
| Hs | **0.82 m** | **0.50 m** |
| Hmax | 1.47 m | not comparable |
| Distance between points | — | **67.7 km (Haversine)** |

**Reproduce:** `python -m unittest tests.test_spatial_real_20261111 -v`. The test uses these archived real values and engine code: `sea_model_check` returns `NO_COMPARABLE` when the only available model is for the bay, even if times match. It is incorrect to claim that the model underestimated by 0.32 m or compute an error: the difference between locations is not a temporal residual.

The current `src_marine` adapter already requests additional forecasts at buoy positions and `sea_model_check` pairs observations and model within **±30 minutes**; however, the public `mar.json` and `series.json` snapshot **exposes only the bay series**, not `_buoys` series. Thus this case verifies the **fail-closed external comparison**, but does not yet establish a real `PAIRED` pair from the internal adapter or forecast skill.

**Remaining to close #8:** capture a controlled dossier with the model actually extracted at Dragonera or Valencia coordinates, its `provider_run_at`, and the PORTUS observation with verifiable QC flag. Freeze the pair, reproduce it deterministically, and check orientation and regional representativeness. Do not publish proprietary data or turn offshore waves into a hazard inside the cove.
