# Evaluation of the model, its uses and potential

**Language / Idioma:** [Español](EVALUACION-MODELO-USOS-POTENCIAL.md) · English

Date: 11 November 2026. Analysis of `fded39b`; revalidated on `main` at `a035deb` (0.5.1), where `portinatx_degen.py`, `pirineo.py` and `pirineo_meta.py` had not changed, so line references remained valid.

**Relationship to merged work.** This complements the [`docs/agency/`](agency/00-MANDATO-Y-DIAGNOSTICO.md) investigation and the [`FORECAST-LEDGER-P0`](FORECAST-LEDGER-P0.en.md) ledger. Its new contribution is the quality audit with reproduced findings (section 1.4: H1–H3, M1–M7), absent from those documents, and the cross-check in section 5.

## Method

Six profiles from the public [agency-agents](https://github.com/msitarzewski/agency-agents) collection were activated. The same collection is the source of the coastal engine's “Ante Agency Agents / NEXUS” governance framework (`src/portinatx_degen.py:2153`). Each profile reviewed the repository independently without modifying it:

| Profile | Question |
|---|---|
| Statistician (`academic/`) | What does the model calculate and what evidence supports it? |
| Model QA Specialist (`specialized/`) | What logical, physical and testing risks exist? |
| Spatial Data Scientist (`gis/`) | How are space and terrain treated? |
| Product Manager (`product/`) | Who is it useful for, and for what is it unsuitable? |
| Trend Researcher (`product/`) | What niche does it occupy and what potential does it have? |
| Reality Checker (`testing/`) | Are the preceding conclusions supported? |

Conventions: **[V]** verified in code (with `file:line`), **[I]** inference not checked against data. Line numbers refer to `fded39b` and may shift. External links are cited as sources; unverified claims are marked accordingly.

Overall conclusion: **the project is a useful niche methodological reference with honest uncertainty discipline, but currently cannot demonstrate predictive skill**, because it does not retain the forecast–observation pairs needed to measure it.

---

## 1. The model

### 1.1 What it actually calculates

**Portinatx** is a rule-based system, not a probabilistic model:

- **Maximum fusion** [V] (`src/portinatx_degen.py:2078-2083`): level = max(institutional floor, observation, models capped at `alert`). `alarm` requires independent confirmation: another observation from a different group and source root, at least one local (`:2091-2103`), or two consecutive centred high-resolution runs plus a local signal (`:2106-2110`, `:1011-1035`).
- **Asymmetric hysteresis** [V] (`:2128-2149`): rises immediately; falls one step after three consecutive cycles and never with insufficient coverage or a manual hold. Falling from `alert` also requires a fresh nearby rain gauge (`:2331-2342`).
- **Thresholds** [V] manually set in `CFG` (`:240-309`); the engine itself calls them “initial, not calibrated” (`:2248`). Saturated-soil thresholds come from two observations (`:258-261`).
- **Ensembles** [V]: raw fraction of members exceeding 50 mm/24 h, 100 mm/12 h and 30 mm/1 h, converted to a level using fixed cuts (`:1847-1866`). The “ensemble” is the simple mean of fractions from five systems (`:3417-3458`).
- **Falsifiable predictions** [V] (`:2363-2429`): binary and deterministic (e.g. “≥2 mm in 60 min” if intensity is ≥5 mm/h), checked as HIT/MISS/UNVERIFIABLE within a −10/+20 min window. The summary is a count.
- **Forensics** [V]: station-day-model-lead pairs (`:3793-3816`), with a 10-day half-life over 14 days of memory (`:3586-3595`); MAE, RMSE, POD/FAR/CSI at 10 and 30 mm (`:3823-3849`); correction factor shrunk toward 1 (`:3936-3943`); model weights ∝ 1/(relative MAE + 0.2) (`:3948-3952`). Regime correction is blocked until three episodes and is never applied alone (`:4062-4082`).

**Pyrenees** uses deterministic physics with fixed constants:

- Snow levels = wet-bulb zero −300/−100/+200 m, Kuchera snow-to-water ratio and linear-ramp solid fraction [V] (`src/pirineo.py:269-275`, `:312-317`, `:345-347`).
- Only two ARPEGE profiles (north and south) with five pressure levels [V] (`:104-105`); inversion from one temperature–altitude regression across the domain [V] (`:405-418`); föhn using three fixed pairs and north flow only [V] (`:87-88`, `:396`).
- Days 3–15 meta-analysis [V] (`src/pirineo_meta.py:232-272`): member fractions by ECMWF/GEFS/ICON family with equal weights; these change to 1/(Brier+0.02) only with ≥30 valid days and a 0.65 cap. “Contrarian” triggers at Δ≥0.2 in two families (`:420-431`). Teleconnections never enter the calculation (`:376-385`).

### 1.2 Where claims exceed evidence

1. **“P(…)” values are not probabilities.** Portinatx evidence strings label uncalibrated member fractions `P(24h≥50)` [V] (`portinatx_degen.py:1855`, `:1867`). `pirineo_meta.py` is more explicit (“raw-member-fraction”, `:250`).
2. **False independence.** IFS/AIFS and GEFS/AIGEFS share a centre [V] (`:3359-3365`) and probably initial analysis [I]; equally averaging them exaggerates consensus. In forensics, 11 island stations on one day are nearly one observation: POD/FAR/CSI count station-days [V] (`:3834-3840`).
3. **“Best model” with in-sample multiple comparisons:** five models × three lead times across about three rainy days (`docs/FORENSE-PUBLICO.md`). The learned factor is never assessed out of sample [V].
4. **Unreachable regime gate:** requires three episodes, but the archive is pruned to 14 days [V] (`:3639`).
5. **Inactive Brier weighting:** no code writes `replay/cases.jsonl`; it is only read [V] (`pirineo.py:858`).
6. **Contrarian ignores noise:** with 30 members and p≈0.5, Δ≥0.2 between two runs occurs by chance in roughly 6% of point-days [I, binomial calculation], and approximately 90 are evaluated per cycle.
7. **Predictions lack a benchmark:** “rain continues” is persistence, and cessation predictions are issued only when the engine decides to step down [V] (`:2376`), introducing selection.
8. **Maximum fusion accumulates false alarms** as channels increase; no FAR is measured for the fused level.
9. **Hysteresis is counted in cycles, not minutes**, while free hosting does not guarantee cadence.

### 1.3 Spatial issues

- **Incorrect neighbourhood label** [V]: text says “±17 km” (`portinatx_degen.py:1795`, `:1855`), but two of seven points are 27–30 km away.
- **`sea_model_check` is not paired** [V] (`:2253-2267`): it compares the Portinatx model's 72 h maximum with current Hs at buoys 80–175 km away, and with a sector (330–100°) different from the bay's (290–60°, `:224-225`). This contradicts the README claim that wave comparisons are paired. Forensics does pair correctly (`:3760-3771`).
- **Rain-gauge network south of the site** [I, from spatial analysis; not reproduced]: stations would be at latitude ≤39.085 while the site is at 39.115 (`:202`), constraining centroid movement to the network footprint.
- **Radar–gauge bias** [V] (`:2433-2463`): uses the maximum 3×3 dBZ, compares instantaneous rate with 8–90 min totals and urban-centre coordinates.
- **Runoff from an out-of-catchment proxy** [V]: station B908X, limited by the code itself to `watch` (`:1609-1614`).
- **Scalar radar motion** [V] (`:1671-1675`): the distance slope to the nearest echo confuses growth with displacement.
- **Pyrenees**: map and table snow levels use only the southern profile [V] (`src/pirineo_app.html:334`, `:341`, `:457`); melting cooling is documented but not applied [V] (`pirineo.py:111`); inversion combines Cerdanya, Andorra and Capcir in one line [V]; orientation and slope are absent from the physics [V]. Possible double altitude correction, because Open-Meteo already adjusts temperature to requested elevation [I].
- **Scale mismatch** [I]: a 300–500 m cove or ski run versus models at 1.5–25 km.

### 1.4 Model quality audit

The self-test passes in full (106 + 13 engine-specific checks and the unittest suite). Findings derive from code review and synthetic probes; they test logic, not forecast accuracy.

**High severity**

- **H1. Coverage counts channels, not phenomena** [V, reproduced]. With observed rain, gauges, radar and lightning missing but wind and sea live, `fuse` returns `quiet` with `insufficient=False` (`portinatx_degen.py:2119-2120`). Two live observed channels of any kind suffice. This is exactly the situation the design seeks to avoid: missing rain data read as calm. `HAZARD_FAMILY` exists (`:2175`) but is unused for coverage.
- **H2. Old or empty data count as valid observations** [V, according to the audit]: a five-hour-old buoy remains available; radar with six-hour-old or all-duplicate frames gives `available=True` and level 0 (`:1664`); models or waves with all `None` become 0 (`:1780`, `:1885`); `ch_rain_obs` does not check AEMET or METAR age.
- **H3. No Portinatx cycle can be reproduced** [V]: the frozen snapshot removes source payloads (`:2804`), `state.json` and caches are overwritten, channels call `now_utc()` without clock injection, and no hash of `CFG` is saved. Only the backend retains raw Pyrenees data.

**Medium severity**

- **M1. One observation can produce `alarm`** [V]: independent confirmation is required only when the observed maximum is 2. One channel reaching 3 (≥50 lightning flashes, B908X ≥60 mm/h, a nearby gauge) produces `alarm` directly (`:2083`, `:2091`). `ch_lightning` has no test.
- **M2. Radar threshold depends on Z–R relation** [V]: the maximum of Marshall-Palmer and “tropical” is used (`:1692`); with tropical, 40 dBZ already yields about 21.6 mm/h, so `alert` triggers near 40 dBZ rather than the configured 45.
- **M3. Anomalies expire after 6 h without review** (`:2300`), contrary to the doctrine of not silently normalising them (`:2159`).
- **M4. Cycle-based hysteresis**: `alarm` to `quiet` in nine cycles (about 45 min at 300 s); the refresh button wakes the loop and accelerates de-escalation (`:4458`).
- **M5. Poorly paired modelled waves and buoy** in `sea_model_check` (see 1.3).
- **M6. Mountain physics** [V]: with a cold pool in the valley, `_zero_height` returns the crossing above the warm layer (−3 °C at 1100 m gives a 2000 m freezing level and no freezing-rain warning); `wet_bulb_c` uses the Stull approximation at 1013 hPa, deviating by up to about 0.45 °C at 1500–2400 m around Tw ≤ 0.5; wet-bulb fraction ≤0 does not depend on precipitation (a dry day gives 1.0); Kuchera takes Tmax only between 850 and 500 hPa.
- **M7. Föhn and inversion**: with no profile, `foehn_diag` returns zero hours instead of unknown; `obs_inversion` declares inversion at +1 °C/km between stations 100 m apart, without a noise threshold.

**Low severity:** no pressure means no gust-front detection; ICC with CAPE alone gives 1.0; documentation says n_eff/(n_eff+8) (`:2916`) while code uses 5 (`:3591`); lightning uses file time, not each flash time (`:1404`).

**Tests do not cover:** complete `cycle()`; lightning, sea, wind and runoff channels; `sea_model_check`, `corrected_outlook` and wave forensics; `foehn_diag` and Pyrenees blowing snow; stale or empty data outside radar and gauges; threshold sensitivity; any verification against observations.

**Governance** (`:2153-2590`) ensures traceability of each level, no reduction below the official warning, and a rain gauge before falling from `alert` or `alarm`. It does not guarantee calibration, real independence among channels sharing a phenomenon but not source root, or cryptographic integrity: prediction SHA detects rewriting by the code itself, not manipulation of `state.json`.

### 1.5 Proposed verification programme

**Storage.** Two append-only JSONL files, written by the existing Actions cron, in a data branch or separate repository:

- `forecasts-AAAA-MM.jsonl`: frozen on issue (sha, `issued_at`, run, lead, fraction or members).
- `obs-AAAA-MM.jsonl`: appended afterwards.

Join them only at evaluation. Historical data can be filled using Open-Meteo “previous runs” already queried by the engine (`portinatx_degen.py:3588`). Forensic memory should increase from 14 days to at least two years.

**Avoid leakage.** Freeze thresholds and the analysis plan before each season; use rolling-origin evaluation (trained through t−1, scored at t); resample by episode, not station; exclude the 18–19 October DANA from all tests because it was already used for tuning.

**Metrics.** Brier with decomposition and BSS against climatology for exceedances; CRPS and rank histograms for amounts; POD/FAR/CSI, frequency bias and SEDI for rare events; bootstrap day intervals; FSS for spatial verification.

**Baselines to beat.** Persistence (60 min prediction), monthly climatology (Brier), raw model and simple mean (factor and weights), equal family weights and the AEMET warning (precaution axis).

**Realistic sample sizes** [I, confirm with `cmd_climo`, `portinatx_degen.py:4566`]:

| Domain | Event | Estimated frequency |
|---|---|---|
| Ibiza | ≥10 mm/day | 12–15 days/year |
| Ibiza | ≥30 mm/day | 3–4 days/year |
| Ibiza | ≥100 mm/12 h | fewer than one per five years |
| Pyrenees, ~2000 m | ≥5 cm/day | 20–30 days/season |
| Pyrenees, ~2000 m | ≥30 cm/day | 2–4 days/season |

Low thresholds (1–10 mm, 5–10 cm) can be calibrated in one or two years. DANAs and major snowfalls cannot: treat and label them as case studies.

---

## 2. Uses

### 2.1 Who it serves today

Personas are hypotheses: no analytics or interviews exist, and the only evidenced user is the owner-operator.

| Persona | What they want to resolve | What is already useful |
|---|---|---|
| Homeowner beside a torrent (originating case) | Move belongings or the car, return earlier? | Three axes, radar, gauges, exit conditions; ntfy push locally only |
| Boat skipper or owner | Reinforce moorings? What sea enters the harbour mouth? | PORTUS buoys, seven-model waves, HF radar, bathymetry |
| Second home in the Pyrenees | Snow at the elevation of the house or road? | 72 h elevations, official warnings, road links, 15 days |
| Skier or mountaineer | At what height does it snow, is there föhn or inversion? | Terrain, cross-section, föhn, inversion, avalanche-bulletin links |
| Enthusiast | Understand the episode and which model is accurate | Sounding, hodograph, ensembles, falsifiable predictions, forensics |

The enthusiast and operator are overserved (about 60 Portinatx sections). Others need an answer in ten seconds and currently must search through charts.

### 2.2 Appropriate and excluded uses

**Appropriate:** context and anticipation hours or days ahead, non-urgent home preparation, mountain-trip planning, learning and auditing models, and a second opinion always subordinate to official warnings.

**Explicitly excluded:**

- Emergency decisions (evacuation, crossing a torrent): AEMET, Civil Protection and 112 take precedence.
- Avalanche risk: the engine does not calculate it; it only links bulletins.
- Navigation safety: the nearest buoy is tens of kilometres away.
- Any “all clear”, open slope or passable road: `UNKNOWN` is not calm.

Scope warnings already exist but are scattered and in small print. Proposed: a fixed strip with identical text on all three pages, large data age beside each axis, exclusions next to sea and mountain data, and precautionary rather than imperative language.

### 2.3 Gaps between calculations and action

- **Cadence:** the convective cycle is designed for about five minutes; the public website updates every six hours. For the torrent it is a situation report, not a nowcast.
- **Notifications:** ntfy exists in the coastal engine but only for a local server operator. Nothing equivalent exists on the public website or in the Pyrenees.
- **Synthesis:** there is no “what does this mean for me today?” screen.
- **Language:** Spanish only for a Balearic, Andorran and French audience (demand unverified).
- **Mobile and accessibility:** Portinatx HTML is about 170 KB with dozens of charts; levels appear colour-dependent; no contrast or screen-reader tests.
- **Trust:** the prediction ledger is the main differentiator, but does not persist in free mode.
- **Contradictory deployment documentation** (corrected in 0.5.1).

---

## 3. Potential

### 3.1 Landscape and gap

| Actor | What they do that the project does not | What remains open |
|---|---|---|
| AEMET, Meteocat, Météo-France, Andorran service | Legal authority, own networks, human forecasters | Warnings by area, not by cove or altitude |
| Open-Meteo | Normalised models and ensembles through an API | Does not interpret, fuse warnings or verify |
| Windy, Meteoblue, yr.no | Scale and polished apps | Do not separate official warnings from own judgement or audit local accuracy (unverified) |
| Radar nowcasting ([pysteps](https://pysteps.readthedocs.io/)) | Probabilistic 0–6 h extrapolation | Requires raw radar and heavy dependencies |
| Global AI models ([AIFS](https://www.ecmwf.int/en/forecasts/datasets/aifs-machine-learning-data), [GraphCast/GenCast](https://developers.google.com/weathernext/guides/osmodel)) | Open global forecasts | Do not resolve terrain-anchored convection |

The repository's own forensics illustrates the limit: in the 17–20 October DANA, IFS and AIFS predicted approximately 0.35 times measured rainfall and AROME 0.65 times (`docs/FORENSE-PUBLICO.md`; one episode).

**Niche:** an audited micro-domain interpretation layer stating what the authority says, what is observed, what precaution the system adds, and how accurate it was previously. No open equivalent was found, although absence is not established.

### 3.2 Enabling trends

- ECMWF opened its real-time catalogue under CC BY 4.0 at no cost from 1 October 2025 ([ECMWF](https://www.ecmwf.int/node/29328)).
- EU high-value meteorological datasets (Regulation 2023/138, applicable since June 2024) ([data.europa.eu](https://data.europa.eu/en/news-events/news/high-value-datasets-what-has-changed-and-what-will-come-next)).
- Météo-France public data free from 1 January 2024 ([French ministry](https://www.ecologie.gouv.fr/ouverture-des-donnees-publiques-du-ministere-au-1er-janvier-2024-toutes-donnees-publiques-meteo)).
- AEMET CAP warnings with free key ([datos.gob.es](https://datos.gob.es/es/blog/los-conjuntos-de-datos-meteorologicos-de-alto-valor)); MeteoAlarm terms unverified.
- Free compute suffices for snapshots, not monitoring. GitHub disables scheduled workflows after 60 days of inactivity in public repositories ([GitHub Docs](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows)).

### 3.3 Actual differentiation

It lies in the method, not the data: everything used can be replicated by others.

1. Three separate axes (official, observed, own precaution): the primary defence against appearing to be an alternative warning.
2. Verification ledger with SHA-256 chain and per-event scoring; currently a one-episode sample.
3. Honest `UNKNOWN`: missing data never become 0 mm.
4. Terrain context: DEM, snow levels, föhn, inversion, paired waves in forensics.
5. Zero dependencies and a portable `.pyz`: easy to replicate, but limits serious radar nowcasting.

### 3.4 Growth vectors, most to least realistic

| # | Vector | First low-cost experiment | Main risk |
|---|---|---|---|
| 1 | DANA verification collaboration | Publish a minimal reproducible October dataset and request academic review | Citizen-observation licence; n=1 |
| 2 | Educational use | Notebook with a snow-level case and self-test | Being read as an official forecast |
| 3 | Replication kit | Third test domain using configuration only, measuring calls per cycle | Open-Meteo non-commercial limit of <10,000 calls/day ([terms](https://open-meteo.com/en/terms)) |
| 4 | Visitor view | Translate labels and disclaimer only (EN/DE/FR/CA) | Legal responsibility: tourist reads “warning” |
| 5 | Home automation | Read-only sensor with freshness and axis, no actions | Automating on stale or `UNKNOWN` data |
| 6 | Citizen observations | Manual post-event form with five volunteers | GDPR, quality, maintainer workload |

**Transferability** [V]: PNG decoder, tiles, Terrarium DEM, channel architecture and profile physics are already generic. Hard-coded items include `LEIB` and `B908X`, `station_km`, sea sectors, coastline and site coordinates in JavaScript; Pyrenees `BOX`, `POIS`, `FOEHN_PAIRS` and `CORTE`. A third domain first requires a declarative “Domain” object.

### 3.5 Risks to the concept

- **Dependence on Open-Meteo:** single point of failure; free tier excludes commercial use.
- **Mixed licences:** AEMET planned a review; Meteocat XEMA is listed as Meteocat intellectual property ([record](https://datos.gob.es/es/catalogo/a09002970-datos-meteorologicos-de-la-xema)); Andorra unverified.
- **Liability:** Spanish legal framework for unofficial warnings is unverified; legal advice is appropriate before a visitor view.
- **Ephemeral state:** forensic ledger has no free durable store.
- **One maintainer** with tacit local knowledge.
- **Statistical validity:** until independent events accumulate, the ledger demonstrates discipline, not skill.

---

## 4. Integrated roadmap

Ordered by value versus effort. Each item includes the test that would demonstrate it works.

**Now (days)**

1. **Coverage by phenomenon and consistent freshness** (H1, H2): require at least one live source in the rain family and treat stale, empty or duplicate data as unavailable. This is the only finding contradicting the project's central rule. *Test:* with wind and sea alone, `insufficient=True` and rain `UNKNOWN`; per-channel cases (six-hour radar, five-hour buoy, empty model, old METAR).
2. **Persistent forecast–observation pair archive.** Format exists (`src/forecast_ledger.py`, P0); it still needs connection to the real cycle and durable storage outside the repository. Prerequisite for everything else. *Test:* after one week, every published cycle has a frozen, hash-verifiable line.
3. **Correct labels and comparisons:** “member fraction” instead of “P(…)”, actual neighbourhood in km, paired or relabelled `sea_model_check`, north/south profiles by Pyrenees zone. *Test:* fail if an evidence string contains “P(” without declared calibration.
4. **Shared scope banner and visible data age** on all three pages. *Test:* no view displays a level without its age.

**Next (weeks)**

5. **Baselines and intervals** in forensics and predictions (persistence, climatology, raw model), with n counted in days. *Test:* forensic panel shows BSS and its interval.
6. **Radar advection** by cross-correlation between already-saved frames: motion vector and arrival time. *Test:* replay archived episodes with arrival-time error measured against persistence.
7. **Rolling-origin forensic test:** show “learned consensus” only if it beats the raw mean out of sample. *Test:* synthetic series where the learned factor must lose.
8. **“10-second summary” card** across the three axes. *Test:* 3–5 people state official level and data age in under 15 s.

**Later (conditional on data or demand)**

9. Snow level by zone with observed anchoring and intensity correction.
10. Spatial verification by FSS to set radii using data.
11. Reproducible cycles (H3): save hashed raw inputs, inject clock and version `CFG`. *Test:* `replay(cycle_id)` produces byte-identical snapshot.
12. Always require independent confirmation for `alarm` (M1) and explicit Z–R for threshold (M2). *Test:* ≥50 lightning flashes without rain → `alert`; 42 dBZ → no `alert`.
13. Robust mountain physics (M6, M7): warm layer or cold pool, Tw at actual pressure, phase conditional on precipitation, inversion noise threshold.
14. D8 catchment with areal radar rainfall to replace B908X proxy.
15. Declarative “Domain” object before any third observatory.
16. Calibrate fractions only at thresholds with ≥30 events.

**Non-goals:** become a warning service; avalanche index, piste report or recommendation to go to sea; SLA or five-minute monitoring on the public website; user accounts or paid infrastructure; presenting values as calibrated probabilities; expanding territories with one maintainer.

---

## 5. Reality Checker cross-check

Following the profile's stance (default “NEEDS WORK”, evidence before approval), the highest-impact claims were checked directly in code:

| Claim | Result |
|---|---|
| H1: without rain channels, `fuse` returns `quiet` without insufficient coverage | **Confirmed** with synthetic channels: `quiet False 2/6` |
| Neighbourhood labelled “±17 km” reaches 27–30 km | **Confirmed**: up to 0.35° longitude displacement (`:218-219`) |
| Evidence strings label member fractions “P(24h≥50)” | **Confirmed** (`:1855`, `:1867`) |
| `sea_model_check` compares 72 h model maximum with last buoy reading, with another sector | **Confirmed** (`:2253-2267` versus `:224-225`) |
| Thresholds declared uncalibrated | **Confirmed** (`:2248`) |
| Forensic memory pruned to `FORENSIC["days"]` | **Confirmed** (`:3639`) |
| No code writes `replay/cases.jsonl` | **Confirmed**: read only (`pirineo.py:858`) |
| Cessation predictions issued only when the engine steps down | **Confirmed** (`:2376`) |
| Rain-gauge network south of site | **Not reproduced**; remains inference |
| Climatological sample sizes | **Cannot be checked** without data; remain inference |
| MeteoAlarm, Andorra and citizen-network licences | **Not verified** |

Verdict: **NEEDS WORK** as a predictive system, because of H1 and lack of verification; **acceptable** as a personal diagnostic tool and methodological reference, always subordinate to official warnings.
