# Algorithm parity: scope and evidence

**Language / Idioma:** [Español](PARIDAD-ALGORITMOS.md) · English

Agency Agents review of 13 November 2026, based on `9ba40bf`.
Engineering Division: Backend Architect and Frontend Developer profiles from Ante/Agency Agents. Backend, Geospatial and Quality began the parallel review; they reached the account usage limit after delivering the diagnosis, initial core and tests. The coordinator completed the adapters, integration, review and verification; no final independent review by those agents is claimed.
References: profiles in `.codex/agents/` and the [coordination contract](agency-agents.en.md).

Parity requires running the same algorithm on equivalent inputs and preserving its validity conditions. Two tabs with the same name, or two connectors that respond, do not demonstrate physical parity. A regional adapter can supply different data without changing the algorithm; a missing value must remain unknown.

## Capability matrix

| Capability | Portinatx | Pyrenees | Zone profiles | Parity status |
|---|---|---|---|---|
| Daily accumulations and ensemble support by family | Territorial engine and packages | Territorial engine and packages | Shared `weather_core` and `zone_engine` | Shared in packages; territorial models, horizons and summaries still differ |
| Point atmospheric profile: thermodynamics, instability, wind and shear | `portinatx_degen.derive_profile` | `pirineo_atmos.derive` | Atmospheric module in this delivery | Shared: `atmospheric_core.derive` is used by both adapters and the `atmosphere` module; logic parity tested with synthetic inputs |
| Spatial wind gradients | Model stencil around Portinatx | No equivalent stencil in current acquisition | No neighbouring grid in a point profile | Regional acquisition pending; do not invent divergence or vorticity from one point |
| Radar: images, age and reference point | Territorial connector and package | Package and external viewers in console | `zone_sources.radar` | Common image acquisition; no parity in echo diagnostics |
| Radar: motion, ETA and window self-verification | `radar_motion` connected to the coastal channel | No equivalent connection in the territorial engine | Archived PNGs; no equivalent dBZ grid | Pending. Requires a mosaic, validated palette, coverage and traceable conversion |
| Warnings and observations | Local networks and rules | Local networks and rules | Configurable METAR/Meteoalarm | Shared package contract; instrumentation and coverage are not equivalent |
| Regional DEM and exposure | Coastal relief and separate bathymetry | Terrarium, elevations and Pyrenean transects | Point elevation | Extent, resolution, datum/nodata and regional download still need parameterisation |
| Snow, warm layer and freezing | No equivalent territorial diagnostic | `profile_diag`, `warm_layer`, `point_snow_levels` | No such diagnostics in the package | Extraction pending; heuristic levels are not observed snow cover or avalanche risk |
| Observed inversion and föhn | No equivalent regional pairs | `obs_inversion`, `foehn_diag` | No pair/slope configuration | Pending. Requires terrain, comparable stations and temporal alignment |
| Gust front and hydrological response | `gust_front`, `ch_runoff`, `irh_now` | No equivalent diagnostic | No basin configuration | Pending; do not transfer the cove's thresholds to mountain basins |
| Extended meta-analysis and review across cycles | Extended models and local superensemble | 15-day meta-analysis, revisions by family | Common ensemble with 7 days requested | Partial parity; geometry, support and horizons must be parameterised |
| Daily forensic evaluation and package archive | Available | Available | `zone_forensics`, `zone_packages` | Shared; synthetic tests do not establish calibration or remote durability |
| Displacement, timing offset and learning by regime | Territorial forensic diagnostics | Revisions between runs | No complete equivalent | Pending separation of observed evaluation, change between forecasts and learned adjustment |
| Sea, waves, currents and bathymetry | Coastal specialisation | Excluded | Coastal/mixed profiles only | Deliberate exclusion from the Pyrenees, not a lack of parity |

Implementation references: `src/portinatx_degen.py`, `src/pirineo.py`, `src/pirineo_meta.py`, `src/pirineo_atmos.py`, `src/weather_core.py`, `src/radar_motion.py`, `src/zone_engine.py`, `src/zone_sources.py` and `src/zone_forensics.py`.

## Counterexample motivating the atmospheric block

Before unification, Quality ran both diagnostics on the same synthetic profile: terrain at 1600 m, surface pressure of 850 hPa and vertical velocity of −0.2 Pa/s. The source is derived from `MountainAtmosphere.source()` in `tests/test_pirineo_atmos.py`.

| Quantity | Previous coastal implementation | Previous Pyrenean implementation |
|---|---|---|
| Temperature at 850 hPa, level at 1500 m | 5 °C, even though below terrain | Unknown |
| K index | 23.9 | Unknown because the level is below ground |
| Vertical velocity at 700 hPa | +0.2 after reversing the sign of Pa/s | Unknown; verifiable geometric quantity missing |
| Surface wet-bulb temperature | 3.7 °C using reduced/default pressure | 3.55 °C using surface pressure |
| Shear height at 700 hPa | 3.0 km above sea level | 1.4 km above terrain |

These results are a synthetic reproduction of the disagreement, not meteorological observations. Reusing the coastal algorithm without correcting its assumptions would not resolve parity: it would propagate below-ground extrapolations and incompatible units.

## Verifiable criteria for the atmospheric core

1. **Equivalence:** the core and the two territorial adapters return the same common levels and indices for equivalent input, both at sea level and at elevation. Location labels may differ; physical values must not.
2. **Terrain:** only levels above the model terrain and with pressure lower than surface pressure are usable. Unknown terrain or pressure does not authorise extrapolation.
3. **Units:** documented conversions preserve the result; missing or incompatible units do not produce indices. Pa/s is not converted to m/s by reversing its sign.
4. **Height:** shear is referenced to the terrain, with its actual height visible. A 500 hPa level is not automatically an exact 0–6 km layer above every terrain.
5. **Coverage:** no missing, non-finite or invalid input is converted to zero. Composite indices require every component; missing components or an unverified vertical sign leave the composite unknown.
6. **Geography:** the point calculation does not depend on `SITE` or a global latitude. Spatial gradients are calculated only with explicit geometry and valid neighbours.
7. **Distribution:** the module can be selected in both templates and in a custom zone, travel in a verified ZIP and be shown in an offline report. The inland profile continues to reject `marine`.
8. **Compatibility:** public contracts retain their fields; missing-data tests and existing consumers continue to pass. New safeguards can reduce values previously shown without support: that change must be documented, not hidden.

Verification of this delivery is limited to the atmospheric block and its adapters. The matrix above must not be marked complete merely because that block has been unified. A passing CI also does not validate real sources, provider vertical semantics, local calibration, official warnings, a durable remote archive or continuous availability.

## Recommended order for the next blocks

- Shared radar grid and coverage before connecting motion/ETA to the Pyrenees.
- Downloadable regional geometry and station pairs before generalising föhn, inversion, snow levels and basin diagnostics.
- Common ensemble horizons and revisions, with support by variable and family.
- Prospective evaluation by episode before sharing learned corrections.

Each block must include input, output, coverage, units, geography and explicit counter-tests. The sea remains a coastal specialisation.

## Delivery and checks

- A single pure core without `SITE`, network access or imports from the coastal engine. The adapters retain the fields consumed by the consoles.
- The coastal connector retains elevation, surface pressure and metadata for each neighbour; gradients use returned cell spacing, with compatible geometry and time. Without verifiable neighbours they remain unknown.
- Froude obstacle height must be known above modelled terrain: the implicit coastal value of 400 m is removed.
- `atmosphere` is selected in both templates and can be downloaded on its own in a new profile. It requests 3 days, wind in m/s and surface pressure. It retains data, diagnostics and hash; on reading, it recalculates using the core.
- Missing/incompatible unit inputs no longer enable indices. The HTML laboratory retains that restriction, including the vertical sign and every component of the synthetic indices.
- Tests: `tests/test_atmospheric_core.py`, `tests/test_pirineo_atmos.py`, `tests/test_zone_atmosphere.py`, `tests/test_atmospheric_ui.py` and the integration suite. The laboratory test uses real Chromium; the test measurements and profiles are synthetic.

Remote sources and deployed consoles require separate checks. Parity of this block does not complete advective radar, snow, föhn, basins, meta-analysis or calibration; they remain in the matrix with their requirements.
