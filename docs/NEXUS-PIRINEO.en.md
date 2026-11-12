# NEXUS · Pyrenees product and design review

**Language / Idioma:** [Español](NEXUS-PIRINEO.md) · English

## Mandate and limits

Initiative: make the Pyrenees console understandable and usable on mobile and desktop without misrepresenting weather evidence. Javier Peiró is product owner and decision-maker. The review and reversible implementation follow his instruction; the existence of a profile grants no additional permissions or authority.

Adapted from the **Startup MVP** runbook of [Ante — NEXUS](https://github.com/bionic0x/Ante-agency-agents/tree/9c54ba227875633068e4eee919770b324b745d9c), pinned to commit `9c54ba227875633068e4eee919770b324b745d9c`. Scope: Pyrenees product, interface, experience, graphic identity, accessibility and data clarity. No duration or numeric validation target is set without data. Redesign alone does not change sources, warnings, thresholds, models or publication availability.

**Objective:** help a person find place, time, official warning, observed conditions and forecast with their sources and limitations. **Non-objective:** maximise sections, visual novelty or an appearance of precision. **Minimum outcome:** problems prioritised from screenshots, a coherent proposal, verifiable changes and independent regression and limitations review; tests with real users remain pending until performed.

**Hypothesis:** a hierarchy by task and time will make information easier to find. This is a hypothesis, not a measured result. **Falsification:** if users cannot find priority information or confuse warnings, measurements and estimates, revisit the solution. **Alternative:** difficulty may stem from absent or stale data and not be solved by design. Keep what already works and keep `UNKNOWN` visible.

## Coordination and deliverables

| Codex role | Function | Deliverable |
|---|---|---|
| `nexus_assurance` | Objective, limits and coherence | Decision log and stop conditions |
| `nexus_coordinacion` | Scope, dependencies and files | Plan and synthesis without concurrent writes |
| `nexus_arquitectura_ux` | Information architecture | Flows and task-based navigation |
| `nexus_investigacion_ux` | Evidence-based review | Findings with screenshot, location and severity |
| `nexus_diseno_ui` | Interface and states | Hierarchy, components and mobile response |
| `nexus_marca` / `nexus_grafico` | Identity, typography and tone | Territorial visual-language proposal |
| `nexus_frontend` | Bounded implementation | Code and regression tests |
| `nexus_verificacion` | Independent challenge | Evidence, limitations and verification review |

Roles work under the lead agent's coordination, with host-defined maximum concurrency; they may be grouped into one task if the environment does not support more agents. The audit must start with actual screenshots and distinguish evidence, hypotheses and pending tests. The verification agent must not treat unmeasured claims as validated or review only changes it produced. The associated log is [`NEXUS-PIRINEO-CLAIMS.json`](NEXUS-PIRINEO-CLAIMS.json).

**Pause criterion:** if source or time traceability is lost, modelled data are confused with an observation or official warning, risk semantics change, or a check fails, correct or isolate the change before publishing. Accessibility, contrast and actual mobile behaviour require validation; installing profiles does not prove them. The owner retains material decisions and risk acceptance.

## Installation and provenance

The original converter and installer were run with `--tool codex` and an explicit selection of nine profiles. Files installed in `.codex/nexus/` retain the generated instructions with additional MeteoPortinatx context; names and descriptions are declared in `.codex/config.toml`. The previous seven profiles are retained. Licences and attribution: [AgentLand MIT](nexus-LICENSE.txt) and [third-party notices, including OpenClaw Community](nexus-THIRD-PARTY-NOTICES.md). The source of `brand-designer` is `design/openclaw-brand-designer.md`; the rest use the `design-*`, `engineering-frontend-developer`, `testing-reality-checker`, `agents-orchestrator` and `specialized-strategic-assurance-lead` profiles from the pinned commit.

This configures profiles for **compatible Codex sessions and trusted projects**. Neither the installer nor the files summon agents, run NEXUS Relay, test compatibility on every host or create persistent processes. Relay has not been deployed: its documentation describes it as a local pilot with its own limits and requirements. Profile use during a session depends on the host and available authorisations.
