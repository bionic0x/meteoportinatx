# MeteoPortinatx divisions

**Language / Idioma:** [Español](agency-agents.md) · English

Seven profiles for Codex sessions with subagents, adapted from [agency-agents](https://github.com/msitarzewski/agency-agents) at commit `8ae6164602c95ca78828b148b9052460ee426885`. The profiles are brief instructions adapted to the project; they do not incorporate the third-party executable or service. The MIT licence and copyright notice are retained in `docs/agency-agents-LICENSE.txt`.

| Division | Scope |
|---|---|
| datos | Sources, permissions, ingestion, quality |
| geoespacial | DEM, coordinates, elevations and mountain sides |
| backend | Contracts, engine, archive and time zones |
| operaciones | Actions, Pages, persistence, monitoring |
| calidad | Independent validation and evidence |
| interfaz | Console, accessibility and source states |
| seguridad | Credentials, permissions and dependencies |

## Usage

Open the repository in a Codex version compatible with subagents and trusted project configuration. For example, request: “Use datos and calidad to review DPObs and XEMA in parallel; operaciones checks deployment; integrate results with evidence.” The coordinator must assign independent tasks and avoid concurrent writes to the same files. Agent configuration does not schedule tasks, create persistent processes, enable notifications or itself prove a meteorological connection. Each agent's availability and permissions depend on the runtime environment. Do not copy credentials into instructions, files or logs.

Meteorological diagnosis follows project instructions: distinguish observation from hypothesis and model, and impact probability from conditional severity; state uncertainty and data time. Official warnings are identified as such. A source must not be declared validated merely because fixtures or mocks pass.

To validate syntax locally: `python3 -c 'import pathlib,tomllib; [tomllib.loads(p.read_text()) for p in pathlib.Path(".codex").rglob("*.toml")]'`. This validates TOML syntax only; profile recognition and delegation require testing in a compatible session.

## Coordination contract

Each division receives a bounded task, a base or commit and, if writing, a list of files it owns. Independent tasks may run in parallel; the coordinator integrates and resolves overlaps. Quality reviews the behaviour and evidence of the other divisions, but a CI result does not replace a real source test.

Each division returns: **result**, commit or source and time, tests run and their result, limitations and next step. Use `UNKNOWN` where evidence is missing; it does not mean calm weather or a passed check. Credentials never belong in agent messages or files.

| Division | Minimum specific deliverable |
|---|---|
| datos | Source, variable, station, measurement time, units, QC and permission. |
| geoespacial | Coordinates, elevations, resolution, spatial matching and its limits. |
| backend | Changed contract, compatibility, isolation and failure tests. |
| operaciones | Workflow, commit, actual publication, data date and real persistence. |
| calidad | Reproduction, expected and observed behaviour, PASS/FAIL/UNKNOWN results. |
| interfaz | Visible state and provenance, accessibility and checks at different sizes. |
| seguridad | Threat, evidence without secrets, fix and residual risk. |

Files define profiles, not seven permanent processes. The `max_threads = 6` limit applies to concurrency supported by the environment; it does not guarantee seven divisions can work simultaneously. Depending on tool availability, a task may run sequentially and this must be stated honestly. To verify actual activation, start a new Codex session with the project authorised, request an independent task from two profiles, and check that their names and responses appear in the session. Record that observation separately from the static TOML check.
