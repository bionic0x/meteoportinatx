# UI-00 · Encargo para los equipos NEXUS (issue #77)

Para lanzar **a partir del 2-12-2026**, cuando vuelva la cuota de agentes. Es un paquete de tareas, no una prueba
de que se hayan ejecutado. El usuario decide en cada gate y **ningún agente tiene autoridad para publicar,
desplegar ni fusionar**.

## Reglas comunes (para pegar en cada encargo)

- Entradas: `docs/ux-review/UI-00/` (capturas, contratos, matriz, fixtures), `docs/ux-review/00-plan-consolidado.md`
  y el issue #77.
- Solo lectura, salvo el equipo F tras G1, y solo en una ruta de vista previa aislada.
- Hallazgos con ID, severidad P0/P1/P2, evidencia (`archivo:línea` o captura), recomendación, esfuerzo S/M/L y
  la etiqueta OBSERVADO, SUPUESTO o UNKNOWN. No inventar usuarios, cifras ni citas.
- Reglas de dominio:
  - aviso oficial ≠ observación ≠ modelo ≠ experimental, y deben distinguirse a simple vista;
  - UNKNOWN no es cero;
  - un dato viejo se ve como incertidumbre;
  - no presentar ningún diagnóstico como aviso;
  - sin estados en inglés en la interfaz.
- Los fixtures son **sintéticos** y toda pantalla que los use lleva la etiqueta «Datos de ejemplo».
- No escribir en archivos compartidos en paralelo. Cada equipo trabaja en `docs/ux-review/vNext/<equipo>/`.

## Equipos, perfiles y entregables

| Equipo | Perfiles (`/tmp/ante/<división>/<slug>.md`) | Entregable | Gate |
|---|---|---|---|
| A · Investigación y arquitectura | `design-ux-researcher`, `design-ux-architect`, `design-persona-walkthrough` | Flujos de tarea por perfil (casa, barca, esquí, analista); arquitectura de información unificada de mapa primero; tratamiento de G0-01 a G0-05 | G1 |
| B · Diseño | `design-ui-designer`, `design-brand-guardian`, `design-visual-storyteller` | Tokens ES/EN, **3 direcciones visuales distintas** sobre F1, F2, F4 y F6; semántica de color única (resuelve «un color, varios significados») | G1: elige el usuario |
| C · 2D | `gis-web-gis-developer`, `engineering-data-visualization-engineer` | MapLibre frente a la pila actual; línea de tiempo sincronizada; leyenda con fuente, hora y unidades | G2 |
| D · 3D | `gis-3d-scene-developer`, `academic-geographer` | Partir de GEO-06 (`lab/terrain/`, MapLibre 5.24.1, Terrarium); cortes verticales y capas de nieve; no cargar el DEM bruto | G3 |
| E · Movimiento | `technical-artist` (`game-development/`) + C + D | Distinguir reproducción observada (`radar.frames`), fotogramas de modelo (`grid.time`), interpolación de render y escenarios esquemáticos GEO-07. Pausa, movimiento reducido y fotogramas ausentes visibles | G3 |
| **C · D · E: contrato común** | — | Los tres trabajan desde el primer día contra [`../vNext/CONTRATO-ESTADO-VISUAL.md`](../vNext/CONTRATO-ESTADO-VISUAL.md): un único estado de territorio, foco, hora válida, modelo, nivel, capas y generación. Prohibido crear un mapa, un explorador 3D y un simulador de frentes independientes | **G1** (CE-01 a CE-12) |
| F · Ingeniería | `engineering-frontend-developer`, `engineering-software-architect` | Adaptadores sobre `public_fetch.js` (una sola generación), interruptor de vista previa, sin credenciales, sin dependencia obligatoria de Earthkit | G2–G4 |
| G · QA independiente | `design-ui-finish-gate-reviewer`, `testing-evidence-collector`, `testing-performance-benchmarker`, `testing-reality-checker`, `gis-qa-engineer`, `engineering-section-508-specialist` | WCAG 2.2 AA, móvil, rendimiento medido, semántica física y geoespacial, los 8 escenarios de fallo. **Nunca el mismo agente que construyó** | G5 |
| Transversal | `specialized-strategic-assurance-lead` | Registro de decisiones y de afirmaciones; alcance y fuera de alcance | todos |

## Agenda del 2-12-2026 (definida por el titular el 28-11-2026)

| Perfil | Primera misión |
|---|---|
| `academic-statistician` | Inferencia y multiplicidad de SEPI F03 v2 y F05 |
| `testing-reality-checker` | Reproducción independiente (F03 v2 y F04) |
| `academic-geographer` | GEO-01 y GEO-06 |
| `engineering-code-reviewer` | Núcleo físico GEO-07 (#83) y fugas temporales de SEPI-P |
| `testing-evidence-collector` | Aceptación o rechazo del paquete UI-00 como evidencia G0 |
| `design-ux-architect` | Arquitectura de información unificada, de mapa primero |
| `design-ui-designer` | Tres direcciones visuales |
| `gis-3d-scene-developer` | Revisión y ampliación del contrato de estado visual |
| `technical-artist` (`game-development/`) | Sistema de animación atmosférica sobre el mismo contrato |

Los verificadores parten del protocolo congelado y de los datos originales; quien construye no verifica. Hasta
G1 (dirección visual y arquitectura de información elegidas por el titular, con el contrato de estado incluido)
no se escribe código de la nueva interfaz.

## Fuera de alcance

Motor meteorológico, protocolo SEPI-P, avisos oficiales, rutas de producción y despliegue. GEO-07 sigue con su
propio protocolo (#82) y su núcleo (#83). En el rediseño, las animaciones de GEO-07 se etiquetan siempre como esquemáticas.
