# A shared core, profiles by zone

**Language / Idioma:** [Español](ZONAS-MODULARES.md) · English

Direction established on 11 November 2026: Portinatx and the Pyrenees are two zones of the same product, with shared general capabilities and territory-specific modules. The Pyrenees is an inland zone and excludes marine data. New users must be able to select points and modules for their territory. Module availability depends on its sources; local warning thresholds are not transferred from one region to another.

## Implemented in this iteration

`src/zone_engine.py`, accessible through `nowcast.py zone`, uses one flow for both zones and custom profiles. It needs no external Python dependencies. The portable `.pyz` includes this engine.

| Module | Selected data | Application |
|---|---|---|
| `forecast` | Temperature, dew point, precipitation, snow, wind and gusts, 7 days | Same for any point; daily UTC diagnosis with coverage and approximate wet bulb |
| `ensemble` | Temperature, precipitation and snow by ECMWF/NCEP/DWD members, 7 days requested | Same connector in both zones; actual availability and horizon depend on provider |
| `terrain` | Point elevation | Same for any point; does not yet download a regional DEM |
| `marine` | Wave height, direction and period, 7 days | Coastal or mixed profiles only; excluded from Pyrenees and inland profiles |

Templates differ in points and default selection. The Pyrenees initially includes three representative points and does not select marine data; it is not a complete station inventory. Points can be edited or added up to 25 per package. The catalogue is common; selection respects the territory. `setting: inland` prevents enabling `marine`. Portinatx uses `coastal`. A new profile defaults to inland; `--setting coastal` or `mixed` can be declared where appropriate.

## Commands

From the repository root:

```bash
# Inspect available profiles and modules, offline.
python3 src/nowcast.py zone list

# Inspect initial requests and selected sources.
python3 src/nowcast.py zone plan portinatx
python3 src/nowcast.py zone plan pirineo

# Export an editable template. Does not overwrite existing files.
python3 src/nowcast.py zone template pirineo --output /tmp/mi-pirineo.json

# Create your own zone and choose only the modules needed.
python3 src/nowcast.py zone init --id mi_zona --name 'Mi zona' \
  --latitude 41.4 --longitude 2.1 --setting inland --modules forecast,ensemble,terrain \
  --output /tmp/mi-zona.json
python3 src/nowcast.py zone plan /tmp/mi-zona.json

# Real download, subject to network access, provider availability and terms.
python3 src/nowcast.py zone fetch /tmp/mi-zona.json --output /tmp/mi-zona.zip
```

`python3 dist/MeteoPortinatx.pyz zone …` also works. The build regenerates `dist/zones/portinatx.json` and `dist/zones/pirineo.json`; copy those templates outside `dist/` before customising. It does not run the legacy regional engines with changed coordinates: the new flow has its own profile and results remain in the selected package.

## Generated package

- `zone.json`: profile, points and selected modules.
- `manifest.json`: collection date, URL, status, available coverage and SHA-256 per file.
- `data/<point>/<module>.json`: structurally validated provider response; retains units, times and missing values.
- `diagnostics/<point>/ensemble.json`: member fractions for rain ≥10 mm and snow ≥5 cm by family; support and denominators per variable, complete days and verified units. These are not calibrated probabilities.
- `diagnostics/<point>/marine.json`: daily maximum wave height and period, circular mean direction; only when marine is selected.
- `diagnostics/<point>/daily.json`: daily rain/snow totals, maximum gust, minimum temperature and minimum wet bulb for `forecast`. A daily total exists only if all 24 UTC hours and all required values are present. Coverage is retained per variable.

The ZIP contains no keys or remote code. An existing package is never overwritten. A failed provider is `UNKNOWN`; the set is `PARTIAL` if only some modules respond. The command returns exit code 1 if not all selected responses were downloaded. `AVAILABLE` describes a downloaded response, not an absence of gaps, weather skill or calibration: check coverage and null values.

Point elevation is not a terrain model. Snow accumulations are not snowpack depth, passability or avalanche risk. Shared diagnostics do not adopt Portinatx or Pyrenees thresholds.

## Use packages offline

```bash
# Check integrity, inventory, profile and each source response.
python3 src/nowcast.py zone inspect /tmp/mi-zona.zip

# Save by zone and hash; does not mix data from different locations.
python3 src/nowcast.py zone install /tmp/mi-zona.zip --root /tmp/mis-observatorios
python3 src/nowcast.py zone history mi_zona --root /tmp/mis-observatorios

# Create a standalone HTML view, without libraries or external requests when opened.
python3 src/nowcast.py zone report --current mi_zona --root /tmp/mis-observatorios \
  --output /tmp/mi-zona.html
# A partial package can also be reviewed directly without activating it.
python3 src/nowcast.py zone report --pack /tmp/mi-zona.zip --output /tmp/revision.html

# Compare two queries for the same configuration on shared valid days.
python3 src/nowcast.py zone compare /tmp/consulta-anterior.zip /tmp/consulta-nueva.zip
```

The report shows points, sources, coverage by variable, family scenarios and marine data only for profiles that include it. Snapshot label and dates are visible: HTML does not become current information when opened. The point filter works offline. Diagnostics are recalculated using local code from verified data, without executing package content.

The verifier rejects duplicates, unexpected paths, incomplete inventories, invalid numerical values and mismatched hashes. It does not extract the ZIP or load package code. Limits: 128 MiB compressed/uncompressed, 25 MB per entry and 512 entries. Checksums detect corruption; they are neither authorship signatures nor meteorological validation.

The archive retains each ZIP by SHA-256. Only an `AVAILABLE` package can activate `CURRENT`, and an older snapshot does not replace a newer one. A partial or failed package is archived for review while the last complete package is retained. Missing fields still have incomplete coverage even in an `AVAILABLE` package. The archive is used by one installer at a time; it is not a multi-user service.

`compare` compares same-valid-day accumulations and extremes for the same point, profile and unit. It requires a later query; missing values or unverified units yield an unknown delta. This is a change between queries, not error against observations or proof of skill. Changed points or modules require separate analysis, not an apparently equivalent comparison.

## Parity still missing

The new flow shares acquisition, packaging and basic diagnosis. The two legacy interfaces and all their specialised algorithms **do not yet have complete parity**. The zone package does not automatically feed those interfaces.

| Capability to extract to the common core | Pending work |
|---|---|
| Satellite and exact geographic coverage | Radar, METAR and area warnings implemented; satellite, official polygons and other local networks pending |
| Regional DEM, vertical profiles and terrain diagnosis | Bounded regional download, cache, provenance and parameterisation of points, transects and exposures |
| Calibration and physical replay | Daily forensic archive and evaluation implemented; learned corrections, physical simulation and out-of-sample inference pending |
| Extended meta-analysis and marine diagnosis | Remove fixed stations/buoys/windows; retain per-variable support and temporal/spatial verification |
| Graphical configurator | Common report and web downloads implemented; visual profile editing pending |
| Pack installation/import | Verification, zone archive, history and report implemented; incremental provider caching and multi-user management pending |

This matrix supersedes the earlier priority of treating the Pyrenees solely as a later expansion: shared capabilities must be developed and tested over both zones.

## Related corrections

Daily snow coverage and per-metric support in meta-analysis, and 24/72-hour mountain window coverage, were corrected. On the website the count next to snow now refers to families contributing that metric.

The backend identifies the complete public package using a manifest; publishing different content with the same `issued` causes an explicit error. A correction requires a new cycle. Old pointers with a core hash remain readable; republishing them requires a new issuance. The new publication `sha256` represents the full manifest, not just `core.json`.

A failure writing CURRENT leaves the index recorded and the previous pointer; retrying exactly the same cycle repairs the pointer without duplicating the chain. The service retains the existing single-publisher-per-data-directory model. No multi-process coordination or automatic CURRENT recovery on startup was added.

## Verification and current limits

Offline tests cover both profiles, marine exclusion in the Pyrenees, custom profiles, hashes, installation, history, comparison and provider failures. Chromium checks the cross-origin backend and common report on mobile, including point filtering and missing values. In this managed browser the HTML is served over local HTTP because policy blocks `file://`; the view needs no external services or resources.

Real requests to `api.open-meteo.com` still receive `CONNECT 403` in this environment. Provider downloads are therefore not verified live. Network rules and published configuration were not changed. Before enabling real use, permit required domains, check responses and review quotas, attribution and terms.

## Shared radar, warnings and observations (0.6.0)

Both zone templates now select `radar`, `warnings` and `observations`. These public adapters need no keys; availability, quota, coverage and terms depend on the provider. Identical requests are reused within each download, including radar metadata and tiles.

- `radar`: up to three recent RainViewer images, 256 px tiles at zoom 7 around each point. Image, hash, date and point position are saved for offline viewing. Each frame timestamp is the composite time, not necessarily that of each radar observation included; frames older than two hours are rejected and marked old from 20 minutes, without inferring local measurement freshness. Coverage is unverified, with no conversion to local rain or warning. Not a continuous animation; a transparent image does not prove dry weather. Attribution: [RainViewer](https://www.rainviewer.com/); review terms before redistribution or increased use.
- `warnings`: official Atom bulletins distributed by [Meteoalarm](https://meteoalarm.org/), filtered by configured area names, start and expiry. Bulletin freshness and failed countries are shown. There is no polygon-based geographical resolution or guarantee of completeness. A bulletin with no matches does not establish absence of warnings. Retain attribution to Meteoalarm and the issuing agency and review national terms.
- `observations`: [Aviation Weather Center](https://aviationweather.gov/) METAR from selected stations, up to 100 km, last 24 hours, marked old after two hours. Wind converts knots to km/h; missing fields remain null. Distance and altitude may prevent local representativeness. They are not automatically used as daily truth to train or verify snow/rain.

Forecast/elevation/ensemble/marine data come from [Open-Meteo](https://open-meteo.com/), with CC BY 4.0 attribution and API terms. ZIPs contain normalised responses for the three new adapters; model responses retain their structure and units.

In a custom profile, besides adding desired modules, configure for example:

```json
"sources": {
  "metar": ["LESU", "LFMP"],
  "warning_feeds": [
    {"country": "spain", "areas": ["pirineo de girona", "pirineo de lleida"]},
    {"country": "france", "areas": ["pyrénées-orientales", "ariège"]},
    {"country": "andorra", "areas": ["andorra"]}
  ]
}
```

Check the provider's actual area names for each territory. Reports show configured scope and failures. Template stations are nearby references, not instruments on every slope. `plan` lists initial requests; radar adds tiles from metadata and warnings query every configured country.

## Forensics: from archive to evaluation

1. Download and archive packages **before** the episode. Keep them with `zone install`; the hash identifies content but does not certify time or authorship against manipulation.
2. Independently review measurements and prepare an observations JSON like the example below. `VERIFIED` is declared under the reviewer's responsibility; community leads in `episode_evidence` remain unverified and do not automatically enter this flow.
3. Run the evaluation and review pairs, exclusions, support, distances, times and sources. The latest eligible snapshot before the day is chosen; a later snapshot or one with a module collected after the start is excluded. The best-fitting forecast is not retrospectively selected.
4. Keep JSON, HTML, original measurements and packages. The package report allows review of radar, warnings and observations available in the snapshot. This replay reconstructs archived evidence; it is neither a physical simulation nor recovery of unarchived data.

```bash
python3 MeteoPortinatx.pyz zone forensic \
  --forecasts archivo-antes-1.zip archivo-antes-2.zip \
  --observations medidas-revisadas.json \
  --output evaluacion.json --html evaluacion.html --max-distance-km 1
```

**Fictional** format example, not an actual observation:

```json
[
  {
    "event": "episodio_ejemplo", "point": "masella",
    "variable": "precipitation", "value": 20, "unit": "mm", "aggregation": "sum",
    "start": "2026-11-11T00:00:00Z", "end": "2026-11-12T00:00:00Z",
    "observed_at": "2026-11-12T01:00:00Z",
    "latitude": 42.35, "longitude": 1.9,
    "source_url": "https://example.org/medida-revisada", "source_id": "instrumento_ejemplo",
    "review_status": "VERIFIED", "baseline": 30
  }
]
```

An exact complete UTC day and a measurement after closing are required. Variables: `precipitation` mm/sum, `snowfall` cm/sum, `temperature_2m` °C/min, `wind_gusts_10m` km/h/max; only for marine profiles, `wave_height` m/max, `wave_period` s/max and `wave_direction` °/circular_mean. Missing values or unverified units do not score. Coordinates within 1 km by default (configurable up to 20); this does not verify elevation, exposure or instrumental quality. `collection_lead_hours` refers to the snapshot, not an authenticated model initialisation.

Results: bias, MAE, RMSE, MAE difference from optional `baseline` over common pairs, Brier for rain ≥10 mm and snow ≥5 cm when valid ensembles exist. Direction errors are circular. Each episode has equal weight, with pair and episode counts visible; the user must verify label independence. Identical duplicates are deduplicated and contradictory ones rejected. No confidence intervals, learned calibration or proof of generalisation: those steps require more independent episodes and temporal train/test separation.

Forensic files **are not published automatically**. Pages only collects predefined profiles and public data obtained during its run. It does not import local state or private observations.

## Publication and network

The Pages workflow builds the program, validates both domains, collects regional modules and publishes `/zones/portinatx/`, `/zones/pirineo/` and `/downloads/`. It requires at least one complete temperature day per point. Supplementary failures do not block the forecast: they remain visible as unavailable. A new run fails before uploading the site if the basic forecast is missing; the previously deployed version remains. The schedule is every six hours: radar, METAR and warnings can become old well before the next update. Consult original sources for current conditions.

Additional domains needed for verification from a restricted environment: `api.open-meteo.com`, `ensemble-api.open-meteo.com`, `marine-api.open-meteo.com`, `api.rainviewer.com`, `tilecache.rainviewer.com`, `feeds.meteoalarm.org`, `aviationweather.gov`. Deployment checks require `api.github.com`, `bionic0x.github.io` and, for Render, its service domain and relevant API. Published environment configuration was not changed.

## Compatibility with additions to main

`nowcast.py evidence PROFILE evidence.json --as-of DATE` remains: it normalises offline `schema:1, items:[]` metadata with radar/warning/station/forensic classes. Spatial and temporal presence remains `PRESENT_UNVERIFIED`; it does not authenticate the source or authorise warnings. Stations and forensic evidence require `qc=PASS` and `source_type=instrument` declarations; the contract remains separate from public adapters and evaluator-reviewed measurements.

The portable package also includes [Forecast Ledger P0](FORECAST-LEDGER-P0.en.md), accessible as `python3 MeteoPortinatx.pyz ledger --root /private/path ...`. It retains prospective capture, uncertified external imports, integrity, matching and threshold metrics. Its schema requires issuance, provider initialisation, provenance and explicit licence: those fields are not invented from a ZIP. `zone forensic` provides daily evaluation and archived context for custom zones; the ledger provides prospective recording under its P0 contract. They are not automatically crossed or converted. Both avoid training or changing warnings using unverified community evidence.

The `/decidir/` views and five use profiles are retained. Regional downloads and reports extend the website without replacing its sources or rules.

### Pyrenean images: scope and limitations

The public console provides external official viewers and does not ingest radar or satellite rasters. `zone fetch pirineo` obtains RainViewer tiles on demand for profile points and `zone report` displays them offline with attribution and a marker. This is separate from the console and does not certify coverage or instrumental quality in each valley. [RainViewer documents](https://www.rainviewer.com/api/weather-maps-api.html) that the composite time is not necessarily the time of its contributing radar data. The displayed age is the frame's and cannot establish that an individual measurement is fresh. Review terms and coverage before increasing distribution; the free API is described for personal or educational use.

Satellite remains an external EUMETView viewer: integration, acquisition date and coverage are not simulated. Before incorporating it into the engine, product selection and licence documentation, verifiable acquisition metadata, projection and coverage, expiry management and real-data tests are needed. [EUMETSAT states](https://www.eumetsat.int/about-us/terms-use) that its satellite products are subject to its data policy, not automatically to Creative Commons.


## Shared atmospheric engine — 13 November 2026

The coastal console, mountain console and downloadable `atmosphere` module now use `atmospheric_core.derive`. Both templates include this module; custom profiles can select it alone. It requests three days of model profiles with explicit units, surface pressure and model-cell elevation. Terrain masking, K/TT, lapse rate, wet bulb and pressure-level wind shear use identical calculations. Missing units/inputs remain unknown; pressure velocity is not relabelled as geometric velocity. Composite indices require all inputs and a verified vertical convention where applicable. Radar advection, regional DEM, snow, föhn and calibration are still separate work; see [the evidence matrix](PARIDAD-ALGORITMOS.md).

The pack inventory limit is 512 entries for 25 fully selected points, with unchanged byte limits. Old packs remain readable; older readers may reject new packs exceeding 256 entries. Numerical regression fixtures do not establish live provider availability or calibrated skill.
