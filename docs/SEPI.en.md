# SEPI — exceptional snow winters in the eastern Pyrenees

**Status:** experimental research line. Design v0.3 and results of phases 01, 02 and 02b (26-11-2026). Each phase was reviewed by an independent verifier agent and its corrections are applied. **This is not a warning or a forecast**, and it does not replace Météo-France, AEMET, Meteocat or the SMA. No SEPI model is validated; no probability of an exceptional winter is issued.

Scripts and reproduction: [`scripts/sepi/`](../scripts/sepi/README.md). The Spanish version, [`SEPI.md`](SEPI.md), is the reference.

## Summary
- Using open data (XEMA, Météo-France, NOAA CPC), an objective catalogue of 17 winters (2009–10 to 2025–26) has been built. 2017–18 and 2025–26 are the exceptional ones in the eastern Catalan Pyrenees; the east–west contrast separates Mediterranean-biased winters (2016–17, 2025–26, 2019–20) from Atlantic-biased ones (2013–14, 2012–13).
- No seasonal teleconnection index (NAO, EA, EA/WR, SCA, AO, ENSO) explains eastern snow after correcting for multiple testing.
- Snow on each side follows that side's total precipitation, and the east–west snow contrast follows how precipitation is split between the two sides. With 17 winters, **no additional contribution is detected** from regime or persistence metrics (H6) measured with a single station's wind. Intervals are wide: a moderate effect cannot be ruled out.
- The NW↔E/SE transition signal is fragile (it depends on the sector boundaries). Settling it needs ERA5 regimes at 700 hPa.
- Reusable data findings: XEMA variable 38 changes units on 15-11-2021, and the Canigou nivose station does not represent crest-level flow.

# Design v0.3

**Core question:** are there antecedent states of the ocean–atmosphere–stratosphere system that raise the probability of persistent sequences of regimes favourable to exceptional snow accumulation and retention in the eastern Pyrenees?

- The winter is studied as a **process** (a sequence of regimes), not only as a seasonal mean.
- **SEPI-D** (diagnosis and historical attribution) and **SEPI-P** (prediction) are separate products, with different predictors and no mixing of results.
- Layers: L0 planetary (ENSO, QBO, MJO, polar vortex, sudden stratospheric warmings), L1 ocean, L2 synoptic regimes (NAO, WeMO, EA/WR, jet, blocking, moisture transport), L3 persistence, L4 mesoscale (orographic engine, föhn, cold pools, 700 hPa wind) and L5 snowpack (new snow, snow water equivalent, melt, rain on snow).
- An extreme episode is not an extreme winter (Gloria 2020 is classified separately as an episode and as a season).
- Two climatologies: moving (exceptionality relative to each era's climate) and fixed (so trends are not hidden).

## Hypotheses
- **H1 Atlantic**, **H2 Mediterranean**, **H3 hybrid**, **H4 retention** and **H5 stratospheric** (as a mediation chain).
- **H6 memory and persistence:** with equal seasonal means, the temporal organisation of regimes decides the outcome. Pre-registered metrics (three at most): longest dry spell; transitions between wet NW and E/SE regimes; rain-on-snow days or snowpack recovery after melt.

## Status of the claims
| Finding | Assessment | Decision |
|---|---|---|
| Atlantic–Mediterranean duality | Robust; reproduced with our own data (phase 01) | Core |
| WeMO with opposite sign on each side | Robust as a diagnosis | Model per massif; use tail days |
| H3 hybrid | Best integrates the evidence; not demonstrated | Priority |
| Regime persistence (H6) | No detectable signal with n = 17 (phase 02) | Pending ERA5 and S2M |
| ENSO as a direct predictor | Insufficient evidence | Conditioning factor |
| Polar vortex and sudden warmings | Documented indirect effect; neither necessary nor sufficient | Sub-seasonal module |
| "A sudden warming guarantees a snowy winter" | Refuted (2022–23 and 2023–24) | — |
| Local seasonal predictability | Not evaluated | Validation mandatory |

## Sample size
- **SEPI-D:** about 65 winters with S2M (1959–2026); today only 17 with accessible open data. The effective sample is smaller because massifs are not independent.
- **SEPI-P:** limited by hindcasts (C3S common period 1993–2016; SEAS5 1981–2016, to be checked). At best, skill in terciles.

## Prospective 2026–27 experiment (pre-registered on 26-11-2026)
- Initial state: very strong El Niño (ONI ASO +2.46), westerly QBO and a stratospheric warming on 10-11-2026 (secondary sources, **to be verified with ERA5**). A combination with no analogue in the record: it is an experiment, not a signal.
- Target variables: accumulation above 2,000 m and persistence at 1,500–1,800 m, per massif and elevation.
- Prediction: climatology plus a qualitative note. No probability of exceptionality is issued.

## Phases
01 cross-border dataset · 02 ranking per massif and elevation · 03 daily reconstruction of extreme winters · 04 atlas of ocean and stratospheric anomalies · 05 transition matrices · 06 extreme vs deficit winters · 07 retrospective validation · 08 2026–27 experiment · 09 integration into MeteoPortinatx–Pyrenees.

---

# Phase 01 — objective catalogue of winters from observations (26-11-2026)

**Status:** exploratory analysis, verified by an independent agent; corrections applied. Not a validation of SEPI.

## Data used and blocked sources
- **Used:**
  - XEMA (Meteocat), daily snow depth (variable 38, corrected daily maximum), 2009–2026. East: Malniu Z3, Cadí Nord Z9, Núria DG, Ulldeter ZC. Centre and west: Bonaigua Z1, Boí Z2, Certascan Z5, Sasseuva Z6, Espot Z7, Salòria ZB, Lac Redon VS.
  - XEMA daily precipitation (variable 35) at all eleven stations (phases 02 and 02b).
  - Météo-France hourly MTO_1H network (AERIS/IPSL THREDDS): precipitation and temperature at Aston, Formiguères and Belcaire; hourly wind at the nivose stations. The nivose stations (Canigou, Puigmal, Port d'Aula) carry neither precipitation nor snow depth in this product.
  - NOAA CPC: NAO, EA, EA/WR, SCA (monthly), daily NAO and AO, ONI and QBO.
- **Blocked from the working environment:** S2M (AERIS offers no accessible download path; registration likely required), data.gouv / Météo-France daily data (proxy drops the connection), NCEP at NOAA PSL (403), ERA5 via Open-Meteo (daily quota exhausted), UB WeMO (error 500). Pending for that reason: the S2M 2002 break test, the WeMO and the 700 hPa regimes.

## Important data finding
XEMA open data for variable 38 are in **mm until 14-11-2021** and in **cm from 15-11-2021**. The change happens on the same day at all 11 stations. Checked against two anchors: Cadí Nord 2,338 mm on 11-04-2018 = 234 cm, the record cited by Meteocat; Núria 144 cm on 26-01-2026, record cited by Meteocat. Any use of this variable must apply the correction.

## Method (summary)
- Season from November to May, named after the ending year.
- Per station: HSmax (maximum depth), days with ≥30 cm from December to April (coverage-corrected) and HNproxy (sum of daily increases ≥2 cm).
- Quality control: a day needs ≥12 h of data; values >600 cm discarded; one-day spikes discarded; if daily max − min >30 cm, the minimum is used; season valid with ≥80 % of days.
- Group index: mean of standardised station values. E_acum = mean of eastern HSmax and HNproxy; E_pers = eastern days ≥30 cm; E–W contrast = E_acum − W_acum.
- Météo-France: hourly precipitation with T ≤ 0.5 °C from November to April; ≥85 % coverage required in each month from December to March.

## Ranking for the eastern Catalan Pyrenees (2009–10 to 2025–26)
| Winter | E_acum | E_pers | W_acum | E–W contrast |
|---|---|---|---|---|
| 2017–18 | 1.60 | 0.92 | 1.67 | −0.06 |
| 2025–26 | 1.25 | 1.16 | 0.55 | 0.70 |
| 2012–13 | 0.72 | 0.14 | 1.34 | −0.61 |
| 2016–17 | 0.63 | 0.70 | −0.32 | 0.95 |
| 2019–20 | 0.59 | 0.58 | 0.18 | 0.42 |
| 2013–14 | 0.50 | 0.86 | 1.30 | −0.81 |
| 2009–10 | 0.41 | 0.26 | 0.10 | 0.31 |
| 2024–25 | −0.14 | −0.44 | −0.38 | 0.24 |
| 2021–22 | −0.17 | 0.29 | −0.23 | 0.06 |
| 2010–11 | −0.20 | −0.17 | −0.38 | 0.18 |
| 2011–12 | −0.29 | −0.57 | −0.39 | 0.10 |
| 2014–15 | −0.32 | −0.04 | 0.06 | −0.38 |
| 2018–19 | −0.68 | −0.37 | −0.48 | −0.19 |
| 2023–24 | −0.70 | −1.23 | −0.30 | −0.41 |
| 2020–21 | −0.87 | −0.21 | −0.84 | −0.03 |
| 2015–16 | −0.95 | −1.12 | −0.49 | −0.46 |
| 2022–23 | −1.37 | −0.86 | −1.39 | 0.02 |

**Reading:**
- **Exceptional in the east:** 2017–18 and 2025–26; 2025–26 ranks first for persistence.
- **Deficit winters:** 2022–23, 2015–16, 2020–21 and 2023–24.
- **The E–W contrast separates winter types:** Mediterranean-biased 2016–17, 2025–26 and 2019–20 (Gloria); Atlantic-biased 2013–14 and 2012–13, consistent with the literature placing 2013 as a record in the west and the Haute-Ariège, not in the Pyrénées-Orientales. A descriptive H1/H2 separation with our own data.
- With only 17 winters, the 90th and 95th percentiles are one or two cases. The ranking is ordinal, not a probability.

## Teleconnection indices (exploratory)
- 42 Spearman correlations (NAO, EA, EA/WR, SCA, DJF ONI, AO, days with NAO ≤ −1) against six target variables, with bootstrap intervals.
- **None survives correction for multiple testing.** Only one has p < 0.05 (EA/WR vs Formiguères solid precipitation: ρ = −0.47, n = 19); about two are expected by chance.
- Consistent with the literature: **no single seasonal index explains eastern Pyrenean snow** in this period.
- ENSO, anecdotal only (n = 3, not significant): the three winters with ONI ≥ 1.4 (2009–10, 2015–16 and 2023–24) rank 7, 16 and 14. No inference is possible for the very strong El Niño of 2026–27.

## H6 — temporal structure (December to March, eastern stations)
- Longest dry spell (days without a ≥2 cm increase) vs E_acum: ρ = −0.51 [−0.78; −0.05].
- Number of snowfall episodes vs E_acum: ρ = 0.61 [0.19; 0.84]. Partly circular, as both come from the same series. Against HSmax alone: ρ = 0.55 [0.08; 0.80].
- 2025–26 had the shortest dry spell (17 days) and the most episodes (13.2); 2017–18, 18.5 days and 12.5 episodes.
- Descriptive result compatible with H6. Phase 02 tests it with an independent source.

## Cross-network consistency
- E_acum vs Formiguères solid precipitation: ρ = 0.65 (n = 16). Western accumulation (W_acum) vs Aston: ρ = 0.63 (n = 14). Formiguères vs Aston: ρ = 0.76 (n = 13).
- Météo-France heated gauges undercatch snow. At Formiguères, in December 2017 and February 2018, data gaps coincide with precipitation and that season is excluded. Solid-precipitation figures are relative indices, not snowfall.

## Independent verification findings (applied)
- V1, P0: the unit change is on 15-11-2021, not 01-08-2021. Fixed.
- V2: ramp spikes in the daily maximum; the minimum is now used if the difference exceeds 30 cm.
- V3: Formiguères 2017–18 invalid; excluded by the monthly coverage rule.
- V4: the EA/WR signal does not survive multiple-testing correction; presented as exploratory.
- V5: H6 partly circular; HSmax comparison added.
- V6: missing days lengthened H6 spells; ≥95 % coverage now required. Days ≥30 cm are coverage-corrected.

---

# Phase 02 — H6 and H1/H2 with an independent source (26-11-2026)

**Status:** exploratory, independently verified; corrections applied. n = 17 winters (DJFM 2009–10 to 2025–26).

## Method
- **Wet days** from XEMA daily precipitation (variable 35) at Malniu, Cadí Nord, Núria and Ulldeter, not from snow depth. Threshold ≥2 mm/day in the station mean. Each station is scaled by its common-period DJFM mean so Ulldeter's start (Sept. 2011) does not shift the level. Valid day with ≥20 h of data and ≥2 stations. Coverage ≥96.7 % in every season.
- **Flow sector** from the daily vector-mean wind direction at the Puigmal nivose station (2,465 m; Météo-France MTO_1H): W-NW-N-NE (270–45°), ENE-E-SE-S (45–180°), SSW-SW-WSW (180–270°). Sectors are unequal (135°, 135°, 90°).
- Per-winter metrics: total precipitation, wet days, episodes, longest dry spell, fraction and precipitation per sector, transitions between W-NW-N-NE ↔ ENE-E-SE-S episodes.
- Spearman with bootstrap CI; rank partial correlation controlling for total precipitation; Benjamini–Hochberg over the eight tests.

## Results
| Target | Metric | ρ | 95 % CI | BH q | Partial ρ (total P) | Partial BH q |
|---|---|---|---|---|---|---|
| E_acum | longest dry spell | −0.29 | [−0.75; +0.29] | 0.30 | +0.18 | 0.64 |
| E_acum | episodes | +0.53 | [+0.04; +0.82] | 0.08 | +0.16 | 0.64 |
| E_acum | NW↔E/SE transitions | −0.05 | [−0.50; +0.42] | 0.84 | −0.65 | 0.03 |
| E_pers | longest dry spell | −0.36 | [−0.73; +0.19] | 0.24 | −0.06 | 0.83 |
| E_acum | total precipitation | +0.71 | [+0.32; +0.89] | 0.01 | — | — |
| E–W contrast | fraction of E/SE days | +0.34 | [−0.25; +0.87] | 0.24 | +0.27 | 0.53 |
| E–W contrast | E/SE precipitation | +0.44 | [−0.12; +0.87] | 0.15 | +0.28 | 0.53 |
| W_acum | NW precipitation (east) | +0.64 | [+0.21; +0.89] | 0.02 | +0.38 | 0.45 |

## Reading
- **The dominant signal is total precipitation** (ρ = 0.71 with E_acum). With n = 17, no additional direct effect of regime or temporal-structure metrics is detected. Correct wording: "not detected", not "absent". Total precipitation may mediate the regime, and power for a partial of 0.5 is ≈0.5.
- **The phase 01 dry-spell result is not reproduced** with precipitation-based wet days (−0.29 vs −0.51). The difference is within sampling noise and the definitions differ, so it is not shown that phase 01 was inflated by circularity.
- **NW↔E/SE transitions:** null raw; partial −0.65 (q = 0.03), contrary to H6. **Not sustained:** the sensitivity analysis below shows it depends on where the sector boundaries are drawn.
- **H1/H2:** precipitation orientation goes in the expected direction relative to the E–W contrast, but is not significant with this classification.

## Sensitivity of the transition signal
24 variants: wet threshold 1/2/3/5 mm, sector boundaries rotated −22.5°/0°/+22.5°, with and without a wind-consistency filter ≥0.5. Two transition definitions: between consecutive episodes, or ignoring SW episodes.
- Median partial −0.35, range [−0.79; +0.11]. p < 0.05 in only 9 of 24 variants (7 of 24 for the second definition).
- Almost all significant variants use the original boundaries; with ±22.5° rotation the signal weakens markedly.
- **Conclusion:** the sign tends to be negative, but the signal is fragile and depends on the sector boundaries. It cannot be sustained with one station's wind; test with ERA5 700 hPa regimes. Output: `out_sens_transiciones.csv` (`scripts/sepi/sens_trans.py`).

## Independent verification findings (applied or declared)
- H1, P0: **Canigou does not represent crest-level flow.** Its daily v component correlates negatively with Puigmal (−0.60), Port d'Aula, Formiguères and Targasonne; 86 % of its days fall in S-SW and 33–42 % of its hours are calm. A code error was ruled out (convention, units, time offset and 180° flip checked). Cause (local channelling or sensor) unknown. **Removed as gap filler**; do not use Canigou as a crest proxy. (Check run by the verifier with its own scripts; `fetch_data.py` downloads Port d'Aula and Targasonne to repeat it, but there is no script in the repo yet.)
- H2, P1: possible over-control, since total precipitation may be a mediator. Wording adjusted.
- H3, P1: the partial control had only been applied to significant results. Now computed for all eight tests, with BH, inside `phase02.py`.
- H4, P1: W_acum was controlled with eastern precipitation. Addressed in phase 02b.
- H5, P2: only three stations in 2010 and 2011. Fixed by per-station scaling.
- H6, P2: misleading sector labels. Renamed with their real width.
- H7, P2: dead code removed.

---

# Phase 02b — western domain with its own precipitation (26-11-2026)

**Status:** exploratory, independently verified; corrections applied.

## Method
- XEMA daily precipitation (variable 35) at Bonaigua, Boí, Certascan, Sasseuva, Espot, Salòria and Lac Redon, with the same quality control and scaling as phase 02. Coverage ≥97 % in every season; no duplicated or shifted days.
- Puigmal sector on western wet days; per-sector metrics require ≥90 % of wet days with a valid sector (2013, 2014 and 2023 drop out).
- Partials with bootstrap CI (2,000 resamples).

## Results
| Target | Metric | Control | n | ρ | 95 % CI | Partial ρ [95 % CI] |
|---|---|---|---|---|---|---|
| W_acum | western total precipitation | — | 17 | +0.80 | [+0.48; +0.96] | — |
| W_acum | western NW precipitation | western total P | 14 | +0.53 | [−0.07; +0.90] | +0.04 [−0.54; +0.79] |
| W_acum | western NW fraction | — | 14 | −0.16 | [−0.66; +0.49] | — |
| E_acum | eastern total precipitation | — | 17 | +0.71 | [+0.31; +0.88] | — |
| E–W contrast | log(east P / west P) | — | 17 | +0.76 | [+0.37; +0.93] | — |
| E–W contrast | fraction of E/SE days | log(PE/PW) | 17 | +0.34 | [−0.24; +0.88] | +0.06 [−0.45; +0.70] |
| E–W contrast | E/SE precipitation | log(PE/PW) | 17 | +0.44 | [−0.16; +0.89] | +0.15 [−0.43; +0.80] |

## Reading
- Snow on each side follows its total precipitation (west 0.80; east 0.71), and **the E–W snow contrast follows how precipitation is split between the two sides** (0.76).
- Once that split is controlled, **no additional contribution is detected with n = 17** from the regime classification based on Puigmal's wind. Partial CIs are very wide (up to ±0.6), so a moderate effect cannot be ruled out.
- **Hypothesis, not result:** the regime may act through the precipitation split. The relation between the E/SE fraction and log(PE/PW) is ρ = 0.40 (p = 0.11), not significant, and the regime is measured with a single eastern station.
- **Interpretation limit:** W_acum and western precipitation come from the same seven stations (depth sensor and gauge). Their 0.80 correlation partly measures agreement between each station's two sensors, not an independent cause. Gauge type and snow catch are unknown.

## Independent verification findings (applied)
- V1, P1: "closed" and "adds nothing" presented absence of evidence as evidence of absence. Rewritten as "not detected with n = 17", with CIs.
- V2, P1: mediation becomes a hypothesis.
- V3, P2: without a minimum sector coverage, PW_NNW was underestimated (2013 had 60–73 % of days). ≥90 % now required.
- V4, P2: shared stations. Declared as a limit.
- V5–V7: no shifted days, no duplicates, no anomalous values (maximum daily 146 mm at Espot).
- V8, P2: a trivial check (two identical columns) removed.

## Next steps
1. **Priority** once a CDS key is available: ERA5 700 hPa regimes to replace the single-station sector and settle the transition signal; also verify the 10-11-2026 stratospheric warming.
2. Obtain S2M (AERIS registration or user download) to extend to 1958–2026, gain statistical power and run the 2002 test.
3. Download the UB WeMO when the server responds; another route to regime classification.
4. Add Ransol and Sorteny (SMA) and manual Núria (AEMET) to lengthen the eastern series.

Scripts in `scripts/sepi/`. Outputs (in `SEPI_DATA`): `out_catalogo.csv`, `out_correlaciones.csv`, `out_h6.csv`, `out_xema_*.csv`, `out_fase02*.csv` and `out_sens_transiciones.csv`.
