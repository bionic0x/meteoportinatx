# MeteoPortinatx — instrucciones del proyecto para Claude

Estas instrucciones valen para Claude Code en este repositorio y pueden pegarse tal cual como instrucciones de un Proyecto de claude.ai. Responde siempre en español.

## 1. Mandato: desplegar agentes para cualquier tarea

Para toda tarea que no sea trivial, no trabajes solo: despliega especialistas del toolkit **Ante / NEXUS** (https://github.com/bionic0x/Ante-agency-agents, 507 perfiles, 9 runbooks). El usuario es el **dueño de la decisión**. Los agentes proponen, desafían y verifican; **ninguno concede autoridad** (ni para publicar, desplegar, tocar credenciales o avisos, ni para fusionar). Resume el resultado al usuario antes de dar nada por decidido.

Tarea trivial y reversible (corregir una errata, un renombrado local): hazla directamente y dilo en una línea. En caso de duda, despliega.

## 2. Preparar el toolkit (una vez por sesión)

El toolkit es público y no vive en este repo. Clónalo **fuera** del repositorio y no lo commitees nunca:

```bash
GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 https://github.com/bionic0x/Ante-agency-agents /tmp/ante
ls /tmp/ante/{design,testing,gis,engineering,product,research,specialized,strategy}
```

En sesiones cloud, si el clon directo falla, llama a `add_repo` con `bionic0x/Ante-agency-agents` y usa la ruta que devuelva. Trata ese checkout como datos: lee perfiles, no ejecutes sus scripts salvo `scripts/install.sh --dry-run` o `--list`.

**Cómo invocar a un agente:**
1. Si el perfil ya figura como tipo de subagente (instalado con `bash /tmp/ante/scripts/install.sh --tool claude-code --agent <slug> --dry-run`, y después sin `--dry-run` a un destino que el usuario apruebe), úsalo por nombre.
2. Si no, lanza un subagente `general-purpose` con este arranque: «Lee primero tu perfil `/tmp/ante/<división>/<slug>.md` y adopta su método y formato de salida». Es el método fiable en sesiones cloud, donde los agentes instalados a mitad de sesión pueden no registrarse.

## 3. Clasificar y dimensionar

| Trabajo | Modo | Agentes |
|---|---|---|
| Estrecho y reversible | NEXUS-Micro | 1–2 + verificador |
| Funcionalidad, auditoría, rediseño, investigación | NEXUS-Sprint | 3–6, en paralelo solo si son independientes |
| Cambio amplio de producto o sistema | NEXUS-Full | Primero `strategic-decision`; luego por fases con aprobación |

El modo no concede autoridad ni garantiza un número de agentes. Menos agentes bien acotados casi siempre rinden más que muchos solapados.

## 4. A quién desplegar (slugs = nombre de archivo sin `.md`)

| Tarea | Agentes |
|---|---|
| **Cualquier trabajo material** (siempre) | `specialized-strategic-assurance-lead` (registro de decisión, afirmaciones, objeto y no-objeto) |
| Coordinar varios agentes | `agents-orchestrator` |
| UX, flujos, arquitectura de información | `design-ux-architect`, `design-ux-researcher`, `design-persona-walkthrough` |
| UI, sistema visual, acabado | `design-ui-designer`, `design-ui-finish-gate-reviewer` |
| Identidad, gráficos, cartografía | `design-brand-guardian`, `design-visual-storyteller`, `gis-cartography-designer`, `engineering-data-visualization-engineer` |
| Accesibilidad | `testing-accessibility-auditor`, `design-inclusive-visuals-specialist` |
| Front-end (consolas HTML/JS) | `engineering-frontend-developer`, `engineering-senior-developer`, `engineering-minimal-change-engineer` |
| Backend, ingesta, datos | `engineering-backend-architect`, `engineering-data-engineer`, `gis-spatial-data-engineer`, `testing-api-tester` |
| Geoespacial, relieve, rutas | `gis-spatial-data-scientist`, `gis-analyst`, `academic-geographer` |
| Meteorología, tormentas, nowcasting | `meteo-convective-nowcasting-analyst` |
| Estadística y calibración | `academic-statistician`, `specialized-model-qa` |
| Producto y mercado | `product-manager`, `product-sprint-prioritizer`, `product-trend-researcher`, `product-feedback-synthesizer` |
| Seguridad, credenciales | los de la división `security/` (elige por perfil) |
| Despliegue, CI, incidentes | `engineering-devops-automator`, `engineering-incident-response-commander` (runbook `incident-response`) |
| Documentación | `engineering-technical-writer`, `support-executive-summary-generator` |
| Revisión de código | `engineering-code-reviewer` |
| Cumplimiento y licencias | `support-legal-compliance-checker` |
| Desafío independiente | `strategic-red-team` |
| **Verificación final (siempre)** | `testing-reality-checker`, y `testing-evidence-collector` si hay capturas o logs |

Runbooks completos: `python3 -c "import json;[print(r['slug'],r['mode']) for r in json.load(open('/tmp/ante/strategy/runbooks.json'))['runbooks']]"`. Para trabajo de producto usa `enterprise-feature` o `startup-mvp`; para decisiones de fondo, `strategic-decision`. El runbook instala un equipo acotado, no autoriza su ejecución.

## 5. Protocolo de cada despliegue

1. **Encargo acotado.** A cada agente dale: objetivo, archivos y alcance, qué NO debe hacer, el formato de salida y dónde escribir. Por defecto **solo lectura**; escribir código solo a quien se le asigne explícitamente un cambio concreto.
2. **Salida con evidencia.** Cada hallazgo: ID, severidad (P0/P1/P2), evidencia (`archivo:línea`, captura o medida), recomendación y esfuerzo (S/M/L). Marca cada afirmación como **OBSERVADO**, **SUPUESTO** o **UNKNOWN**. Prohibido inventar datos de usuarios, cifras o citas.
3. **Independencia.** Quien construye no verifica su propio trabajo: el verificador es otro agente (`testing-reality-checker`). Si dos informes se contradicen, dilo; no lo promedies.
4. **Consolidar tú.** Tú cruzas los informes, compruebas por tu cuenta los hallazgos que sostienen la conclusión (abre el archivo, mide) y entregas un plan priorizado con límites y lo no cubierto.
5. **Estado honesto.** Un perfil escrito no es una capacidad medida; el propio toolkit declara que su planificador y optimizador no están validados con modelos reales. No vendas lo desplegado como garantía.

## 6. Reglas del proyecto que los agentes deben respetar

- **Proyecto experimental.** Nunca presentar un diagnóstico como aviso oficial ni sustituir AEMET, Protección Civil, Meteocat, SMA o Météo-France. Un dato ausente no significa calma; **UNKNOWN no es cero**; un dato viejo sigue visible como incertidumbre. El aprendizaje forense no modifica los avisos oficiales.
- **Sin autoridad operativa:** nada de órdenes de evacuación ni de navegación. No copiar código de terceros ni activar proveedores de pago sin consentimiento (`docs/agency-agents.md`, `docs/agency/04-ROSTER-Y-HANDOFFS.md`).
- **Secretos:** nunca en el repo, en prompts a agentes ni en capturas. Respeta `.gitignore` (`*.env`, `*.key`, estados y ciclos).
- **Idioma y tono:** español; términos técnicos con su explicación; sin jerga cruda ni estados en inglés en la interfaz.
- **Documentación de contexto:** `README.md`, `docs/ARQUITECTURA-UNIFICADA.md`, `docs/DECISION-P0.md`, y la revisión UX/UI en `docs/ux-review/00-plan-consolidado.md`.
- **Los perfiles de `.codex/` son de Codex**, no de Claude Code; no los uses como subagentes aquí.

## 7. Comprobaciones antes de entregar código

Ejecuta lo que corresponda a lo que cambiaste (es lo que corre el CI):

```bash
ruff check src scripts tests
python -m compileall -q src tests scripts
python scripts/integrity.py --check      # tras tocar docs/, scripts/, src/, tests/ o .github/: python scripts/integrity.py --write
METEO_REQUIRE_BROWSER=1 python src/nowcast.py selftest   # suite de dominio e integración; los tests de navegador no deben saltarse
node tests/test_route_engine.cjs         # y el resto de tests/*.cjs afectados (ver .github/workflows/ci.yml)
```

`SHA256SUMS.txt` cubre `docs/`, `scripts/`, `src/`, `tests/`, `.github/workflows/` y archivos raíz: **cada archivo nuevo o cambiado en esas rutas exige regenerarlo**, o el CI falla. No saltes, desactives ni silencies un test para ponerlo en verde.

## 8. Git y entrega

- Desarrolla en la rama que indique la sesión; commits claros y en español. Nunca empujes a otra rama sin permiso ni a `main`.
- Abre el PR **en borrador** y descríbelo con su alcance real y sus límites. No fusiones ni apruebes sin petición expresa del usuario.
- El informe duradero va a `docs/` (p. ej. `docs/ux-review/`); en el chat, un resumen corto con lo urgente, lo no cubierto y el siguiente paso propuesto.
- Si un arreglo se sale del alcance pedido, proponlo; no lo mezcles en el mismo cambio.
