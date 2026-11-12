# User evaluation of the decision view (issue #11)

**Language / Idioma:** [Español](EVALUACION-USUARIOS-P1.md) · English

**Status:** protocol ready; sessions **not conducted**. None of this document's results exists yet. Do not invent adoption, satisfaction or forecasting skill.

## What is evaluated

The `/decidir/` view, with three levels: 01 Decide · 02 Follow data · 03 Investigate. Evaluate on a public snapshot or local server, never during a real hazardous episode. Question: can each profile find what it needs within 15 s without reading missing data as calm?

## Participants

- At least **5 people per segment**: home beside a torrent, boat, second home in the Pyrenees, skiing and mountains. The “investigate the episode” segment is optional.
- Real members of each segment, not the maintainer. Recruit voluntarily and without compensation that influences answers.

## Tasks (same order for everyone)

1. **Official status.** “Is an official warning currently in force and who issued it?” Success: correct level and agency, or “not verified” when shown.
2. **Data age.** “How old are these data?” Success: identifies cycle age and whether it is fresh or stale.
3. **Missing ≠ calm.** Show a prepared insufficient-rain-coverage case (test snapshot). “Is it calm?” Success: says it cannot be known. Critical failure: “yes, it is calm.”

For mountains, replace task 3 with: “Is your location above the snow level?” Success: reads the elevation for their mountain side, or “—” when unavailable, without assuming it is below.

## Measures

| Measure | Method | Indicative threshold |
|---|---|---|
| Success per task | Yes / no / partial, recorded by observer | ≥80% per segment |
| Time to answer | Stopwatch from question | Tasks 1–2: ≤15 s |
| Critical failures | Calm inferred from UNKNOWN, or own estimate mistaken for official warning | **0** |
| Mobile | Same session on a phone at 360 px | No blocked task |
| Accessibility | Level understandable without colour; keyboard navigation | No blocked task |

With 5 people per segment, percentages are **descriptive**, not statistical. Publish with their denominator (e.g. “4/5”).

## Privacy and recording

- No names, contacts, home locations or screen recordings containing personal data. Identify each session as `S-<segmento>-<n>`.
- Record template, one row per task: `sesion, segmento, dispositivo, tarea, exito, segundos, fallo_critico, observacion_breve`. Limit `observacion_breve` to observed behaviour; never copy verbatim quotations.
- Store records outside the repository. Publish only the aggregated summary in the repository.

## Afterwards

Open an issue for each critical failure, with a screenshot of the test snapshot (without personal data) and the affected task. Usability results do not change the warning level or fusion.
