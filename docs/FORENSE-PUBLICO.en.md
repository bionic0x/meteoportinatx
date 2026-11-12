# Public technical lessons from the 17–20 October 2026 DANA

**Language / Idioma:** [Español](FORENSE-PUBLICO.md) · English

**Scope:** retrospective study of one episode in Ibiza, with three days of rainfall, 11 Meteoclimatic stations and Open-Meteo Previous Runs products D0–D2. The comparisons come from the technical reports in the October 2026 release. They are not a climatology or calibrated coefficients.

## Model/observation rainfall: D0 (0–24 h)

| Family/model | Forecast / measured rainfall | Mean error |
|---|---:|---:|
| AROME HD | 0.65× | 22.8 mm |
| ICON-EU | 0.41× | 23.1 mm |
| ECMWF IFS 0.25° | 0.36× | 25.1 mm |
| ECMWF AIFS | 0.35× | 25.6 mm |
| NOAA AIGFS | 0.25× | 29.4 mm |

There are amplitude and location errors in anchored convective rainfall; sources must not be weighted for snow, Atlantic fronts or sea forecasts based on their performance in a single case. A model grid cell's representativeness error is not instrument bias. Validation must freeze the original run and compare observations within the same time window and area.

## Waves: correction needed

A preliminary comparison suggested a 2–2.5× difference, but compared a model point off a bay with distant buoys. Subsequent comparison at **spatially coincident points** produced model/buoy ratios between **0.87 and 0.99** and RMSE between 0.24 and 0.46 m for the models reviewed. Do not introduce a universal ×2 wave multiplier; each sector's orientation and bathymetry require a separate diagnosis.

## Derived rules

- Official warnings retain their authority and are not derived from NWP consensus.
- A model, an unverified radar and a remote station do not by themselves constitute independent local confirmation.
- Do not recalibrate a radar–rainfall Z–R relationship using a single significant pair; compare radar and rain gauge at the same place and time.
- Revisions of the same episode must not be counted as *n* independent observations; score by date/event.
- Learned correction belongs to the *experimental forensic* domain; it never independently alters warnings or operational thresholds.
- Missing data and sources are reported as `UNKNOWN`, not as a forecast of calm conditions.

The full reports and original tracking notebook are kept **outside the public repository** in the local integration-release package, because they contain private contextual information about a property.
