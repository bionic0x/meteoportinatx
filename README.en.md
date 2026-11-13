# MeteoPortinatx

[Español](README.md) · **English**

### From the Mediterranean to the Pyrenees. A closer look at the weather.

A thunderstorm can pass a few kilometres from Portinatx and change sea conditions without bringing rain ashore. In Cerdanya, a temperature inversion or a few hundred metres of elevation can mean the difference between rain and snow. **MeteoPortinatx was created to understand those local differences**, bring together the available evidence, and make visible what we still do not know.

[**Explore MeteoPortinatx**](https://bionic0x.github.io/meteoportinatx/) · [Portinatx](https://bionic0x.github.io/meteoportinatx/portinatx/) · [Pyrenees](https://bionic0x.github.io/meteoportinatx/pirineo/) · [Decision views](https://bionic0x.github.io/meteoportinatx/decidir/) · [Documentation](docs/ARQUITECTURA-UNIFICADA.en.md)

> **Experimental project.** Diagnostics do not replace official warnings from AEMET, Civil Protection, Meteocat, SMA or Météo-France. Missing data does not mean calm conditions. Forensic learning does not modify official warnings.

## Two territories, one shared perspective

| 🌊 Portinatx and Ibiza | 🏔️ Eastern Pyrenees |
|---|---|
| Radar, rainfall, thunderstorms, wind, warnings and marine conditions for Ibiza's north coast. | Cerdanya, Capcir and Andorra: terrain, elevations, snow, stations, models and ensembles. |
| The geography of a cove matters: a nearby cell or a gust front can have different impacts just a few kilometres apart. | Valley floors, slopes and watersheds do not experience the same weather. The Pyrenees profile excludes the marine module. |

Both profiles share modular acquisition, diagnostics, coverage indicators and reports. Each territory retains specialised algorithms; complete parity is still in development. The app and website are at **0.6.0**; the coastal and Pyrenean engines are at **0.6.1**. [Profiles and zones](docs/ZONAS-MODULARES.en.md).

## From evidence to decisions

**Observe.** Consult measurements, radar, METAR and warnings, with their source and age. Old or inaccessible data must remain visible as uncertainty, not as a new measurement.

**Interpret.** Compare models and ensembles with local geography. Terrain, exposure and distance matter as much as a value on a map.

**Decide.** The [“Decide” view](https://bionic0x.github.io/meteoportinatx/decidir/) organises information for five situations: a home beside a torrent, a boat or mooring, a second home, skiing and mountain activities, and meteorological analysis. It separates warnings, observations and estimates and links to the full consoles. It is a reading aid: it does not issue evacuation or navigation orders. [How it works](docs/DECISION-P0.en.md).

**Learn.** The experimental prospective archive freezes forecasts before an event so that they can later be checked against comparable, quality-assured observations. It also records exclusions and uncertainty. It does not yet demonstrate that probabilities are calibrated or that the archive persists on its own. [Forensic protocol](docs/FORECAST-LEDGER-P0.en.md).

## Explore the tools

- **Regional consoles:** a scientific view of [Portinatx](https://bionic0x.github.io/meteoportinatx/portinatx/) and the [Pyrenees](https://bionic0x.github.io/meteoportinatx/pirineo/), built on the same shared core.
- **Route planner:** load a GPX in the browser and explore conditions by segment and time. The route remains in the browser. Its limits and variables are documented in [Pyrenees routes](docs/RUTAS-PIRINEO.en.md).
- **Zone packages:** prepare, verify and install snapshots containing data, diagnostics, coverage and hashes; you can also generate offline HTML reports. [Zone guide](docs/ZONAS-MODULARES.en.md).
- **Climate context:** the project includes provenance-labelled knowledge and experimental sidecar tools, without confusing context with an observation or warning. [Source catalogue](docs/CATALOGO-FUENTES.en.md).

In **Atmosphere · Pyrenees**, the detailed profile compares representative points on the northern and southern sides: thermal profiles, hodograph, wind shear and hourly indicators. These are model fields; below-ground levels are excluded and unavailable fields are shown as `UNKNOWN`. Experimental indices have not been calibrated for the Pyrenees.

## Sources and confidence

The Pyrenean console integrates AEMET, Meteocat XEMA and Météo-France DPObs. A publication on 11 November 2026 included observations from all three networks and the French hourly archive; subsequent availability depends on providers, credentials and the freshness of each measurement. Pyrenean radar and satellite viewers are external: check their coverage and age. In RainViewer, the mosaic timestamp does not guarantee the timestamp of each radar.

[**ClimayNievePirineos**](https://www.climaynievepirineos.com/estaciones/UsoYCaracteristicasCYNP.htm) is a private, unofficial network whose author permits data sharing with source attribution or a link to the station. The article does not establish a maximum frequency for automated requests. The connector currently retains a project-specific activation control: `permisos/cnp.json` or, only in a private local environment, `CNP_PERMISSION_VERIFIED=1`; this is not a prohibition stated in the article. [Conditions record](docs/CNP-PERMISO-20261111.en.md).

The manual describes the general table's intensity as the **daily maximum**, not the current intensity. The individual-page parser retains the field `intensidad_mmh`, whose meaning needs verification before it is treated as instantaneous. The 2014 manual also describes potential underestimation of rainfall and wind; these are indicative, station-dependent warnings, not universal correction factors.

## Phone sensors and haptics (experimental)

The `/dispositivo/` route offers optional vibration when the cycle signal rises or a diagnosis is lost, and displays browser-compatible sensors. A barometer, thermometer and hygrometer require an external native bridge that is not included. Measurements remain on the device and expire; enabling altitude requires geolocation permission. It works only while the page is open and visible: **it is not a push alert or continuous monitoring**. No vibration does not mean no danger. [Contract and limits](docs/DISPOSITIVO-SENSORES.en.md).

## Run locally

Requires Python 3.10 or later and its standard library. Some sources need optional credentials, which must be kept out of Git.

```bash
python3 src/nowcast.py selftest
python3 src/nowcast.py serve --port 8787 --portinatx-interval 300 --pirineo-interval 10800
```

Open [localhost:8787](http://localhost:8787/) and navigate to `/portinatx/`, `/pirineo/` or `/decidir/`. The local server restricts refreshes to the same origin; the public API is read-only.

To work with zones and build the application:

```bash
python3 src/nowcast.py zone list
python3 src/nowcast.py zone plan portinatx
python3 src/nowcast.py zone plan pirineo
python3 src/nowcast.py zone fetch pirineo --output captura.zip
python3 src/nowcast.py zone inspect captura.zip
python3 src/nowcast.py zone report --pack captura.zip --output informe.html
python3 src/nowcast.py export
python3 scripts/build_site.py
python3 scripts/build.py
python3 scripts/integrity.py --check
```

You can also create profile templates, install packages and inspect evidence with `zone template`, `zone install` and `evidence`. [Commands and contracts](docs/ZONAS-MODULARES.en.md).

## Publication, persistence and limits

[GitHub Pages](https://bionic0x.github.io/meteoportinatx/) publishes snapshots generated by Actions every six hours and when sources change. That cadence **does not amount to continuous monitoring**. Deployment requires recent data for both domains and fails if they are missing.

The [Render Free backend](https://meteoportinatx-backend-free.onrender.com/) is a read-only preview: it may sleep and its local storage is volatile. No persistent disk is configured. The web bridge can use the backend through the public `METEO_BACKEND_URL` variable and falls back to the complete Pages file set if it fails or mixes generations. Never put secrets in that variable. [Backend guide](docs/BACKEND-PERSISTENTE.en.md).

The supervised cycle for the Portinatx prospective archive includes systemd templates, but requires installation on a Linux machine with persistent storage and independent backups. The presence of templates **does not mean it is scheduled or active**. [Installation and limits](docs/FORECAST-LEDGER-P0.en.md).

## Under the hood

| Component | Purpose |
|---|---|
| `src/portinatx_degen.py` | Coastal engine: radar, observations, warnings, marine data, models and private forensics. |
| `src/pirineo.py` and `src/pirineo_meta.py` | Mountain engine: terrain, profiles, snow and ensembles. |
| `src/atmospheric_core.py` | Shared atmospheric core; parity covers only the block tested with synthetic inputs. |
| `src/nowcast.py` and `src/nowcast_backend.py` | Orchestration, local server and read-only backend. |
| `src/public_fetch.js` | Consistent domain loading and static fallback. |
| `src/route_engine.js` and `src/pirineo_ruta.html` | Private in-browser GPX route planner. |
| `scripts/build_site.py`, `scripts/build.py` and `scripts/integrity.py` | Website, portable application and SHA-256 integrity. |
| `tests/` | Synthetic engine, interface and contract regressions. |

CI checks Python 3.10 and 3.11, JavaScript tests, integrity and the portable application build. Synthetic tests do not calibrate a forecast or guarantee external source availability.

The repository also configures seven [Codex agent divisions](docs/agency-agents.en.md): data, geospatial, backend, operations, quality, interface and security. These are profiles for compatible sessions; they do not create persistent agents or schedule work by themselves.

[Architecture](docs/ARQUITECTURA-UNIFICADA.en.md) · [Release notes](docs/RELEASE-NOTES.en.md) · [Assessment and roadmap](docs/EVALUACION-MODELO-USOS-POTENCIAL.en.md) · [Modular zones](docs/ZONAS-MODULARES.en.md) · [Algorithm parity](docs/PARIDAD-ALGORITMOS.en.md)
