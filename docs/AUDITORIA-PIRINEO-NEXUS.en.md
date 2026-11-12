# Pyrenees: product, experience and design review

**Language / Idioma:** [Español](AUDITORIA-PIRINEO-NEXUS.md) · English

Review of the observatory published on 11 November 2026. All twelve sections were traversed on desktop, with screenshots. Findings describe what was observed in that cycle; sources and their data may change. An accessibility audit, instrumented contrast assessment, screen-reader test and real-phone usability test have not been completed.

## What makes the experience difficult

| View reviewed | Finding | Priority |
|---|---|---|
| Monitoring | Warnings refer to different areas and periods; source status does not prove that the selected point is free from danger. Some cards place labels and values too close together. | High |
| Atmosphere | Charts take up much of the screen; two time controls relate to different sources without sufficient explanation. | High |
| Terrain and cross-section | Place names and elevations overlap on the map, especially in nearby locations. Model selectors can be mistaken for checkboxes. | High |
| Points | The long table has no search, and some abbreviated headers require interpretation. | Medium |
| Models | The control point was selected in another view and not clearly shown alongside the comparison. | High |
| 15-day ensemble | The initial point can differ from Monitoring. Ensemble fractions are not calibrated impact probabilities. | High |
| Satellite and radar | External viewers are provided without in-house ingestion; this must remain clearly stated. | Medium |
| Surface | Technical information competes for attention with the other general controls. | Medium |
| Forensics | The summary has blocks of text and values that are hard to scan; forecast skill has not been demonstrated without prospective validation. | Medium |
| Governance | An UNKNOWN status can coexist with an “ok” reason when verifiable age is missing; distinguish the source result from its freshness. | High |
| Laboratory | Results and their limits need a visual hierarchy so simulations are not confused with warnings. | Medium |

## First intervention

- Group the twelve sections by task, preserving existing links and showing the active section.
- Identify map and model time separately from atmospheric-profile time; limit chart size.
- Add point selection in Models and synchronise it with the observatory control point.
- Identify current, upcoming, expired and unverifiable-time warnings according to the device clock, without automatically assigning them to the chosen point. Official information remains authoritative.
- Visually separate labels and values in Monitoring, Forensics, Governance and Laboratory.

## Next work

1. Resolve the geographical match between official warnings and locations using verified geometries and coverage; display scope and freshness.
2. Design a shared point state across all views, including the ensemble, without silently changing existing selections.
3. Resolve label collisions on the map and profiles, and add search and clear headers to the points table.
4. Review Governance to distinguish query reason, age and derived status.
5. Validate on a real phone, with keyboard, screen reader and contrast checks; test comprehension with people using the tool.

Interface changes do not turn models into observations or introduce official alerts or real-time data. An unknown status does not mean there is no danger.
