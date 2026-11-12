# H1 — Critical rain coverage and freshness (conservative patch)

**Language / Idioma:** [Español](H1-RAIN-COVERAGE.md) · English

**Objective:** prevent two wind/sea observations from creating a false impression of calm when the rain family is unavailable. Fusion retains the three axes and the official minimum level.

## Implemented contract

- `fuse()` requires **both** at least two live observations and at least one rain observation from `lluvia_observada` (METAR/AEMET/PWS), `pluviometros` (Meteoclimatic) or `radar` (RainViewer).
- Lightning, wind, sea, runoff estimates and models cannot substitute for a precipitation observation. Availability is calculated after QC and timestamp validation.
- If the rain family is missing: `insufficient=true`, reason `COBERTURA INSUFICIENTE DE LLUVIA`, `rain_coverage=0/3`, de-escalation decision `HOLD`, and no reduction of existing levels. `quiet` remains an internal rank but **does not certify calm**.
- Ages refer to **observations**, not downloads: radar maximum 30 min; AEMET/METAR maximum 90 min; PWS 30 min (existing QC); Meteoclimatic 45 min (existing station age). Future timestamps tolerate up to 10 min clock skew; after that, `UNKNOWN`.
- Public API: allowlist extended only for boolean `insufficient` and `rain_coverage`; no private notes. In the homeowner view, a failed H1 check does not present a `quiet` precaution as an available diagnosis.
- The official level retains its priority; escalation rules M1/M2 are unchanged and require independent investigation.

## Tests and limits

New tests cover live wind+sea with rain unavailable, five blocked de-escalation cycles, restoration of rain coverage via radar, lightning being insufficient, institutional warnings, stale AEMET/METAR and radar, fresh observations, future and missing timestamps. Self-test radar fixtures use relative times to test actual freshness.

**Not included:** calibration, remote ledger persistence, private AEMET credentials, Render reconfiguration, forum connections, H2 investigation (HF radar), or M1/M2 resolution. Passing tests does not establish meteorological skill.

## Integration with #24

This patch retains the `Channel.data_time` freshness scheme introduced in #24 and corrects an H1 detail: `rayos` and `escorrentia_torrentes` belong to the rain hazard family but do not establish **rainfall observation coverage**. It retains `families` and adds `rain_coverage` for the decision view; older tests are adapted to `apply_freshness()`.
