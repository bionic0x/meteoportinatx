# SEPI-EK-01 — Earthkit pilot

Status: experimental scaffold, not a forecast. F03 v1/v2 untouched. No mandatory dependency changes.

## Acquisition
Install the optional requirements in an isolated Python environment (Python >=3.11). Configure CDS locally, accept dataset terms; never commit credentials. Use the CDS download form to verify the ECMWF system, available years and request fields before executing. System 51 is a candidate, not asserted available in November 2026.

```sh
python -m pip install -r scripts/sepi/requirements-earthkit.txt
export SEPI_DATA=$HOME/sepi-data
python scripts/sepi/earthkit_ingest.py --system 51 --years 1993 1994 2016 2026
# After confirming the request against the catalogue:
python scripts/sepi/earthkit_ingest.py --system 51 --years 1993 --download
```

Default is dry run. One variable/year per request. Full grid initially to avoid unsupported subsetting; estimate quota before scaling. Separate system/initialization/member/lead in all downstream datasets. Raw artifacts live outside repo, with SHA256, exact request and acquisition timestamp. No fabricated forecasts on failed requests. Earthkit reads the GRIB with its xarray adapter; inspect member, initialization, lead, grid and units before conversion. Monthly precipitation units/aggregation must be verified against source metadata.

## Roadmap
EK-02: December–January targets from daily S2M; seasonal ensemble features with verified grid and lead; baseline and rolling-origin logistic model, all preprocessing within training folds. Hindcast and operational forecast versions must match or be separately evaluated. Few exceptional winters imply wide uncertainty. No predictive claim without skill against climatology.
EK-03: evaluate official ECMWF weather skills, license and tool permissions before importing. Separate orographic downscaling, wet-bulb and operational products; no resolution gain claimed from interpolation. Validate independent observations and keep model/observation provenance.
CERRA-Land 2002 discontinuity remains a separate workstream.

## Gates
G0 dry-run requests reviewed; G1 authenticated pilot GRIB downloaded and manifest verified; G2 Earthkit decoding preserves ensemble/time coordinates and units; G3 lock dependencies and pass CI; G4 hindcast skill and calibration before issuing probabilities. G1–G4 not executed in this PR. Documentation: https://earthkit-data.readthedocs.io/en/latest/tutorials/source/cds.html and https://cds.climate.copernicus.eu/datasets/seasonal-monthly-single-levels?tab=download.
