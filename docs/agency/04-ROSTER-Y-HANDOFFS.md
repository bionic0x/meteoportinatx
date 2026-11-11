# Agency Agents para MeteoPortinatx — roster operativo y protocolo de handoffs

**Origen:** https://github.com/msitarzewski/agency-agents (licencia MIT). Estos son los nombres de roles realmente presentes en el repositorio, no agentes residentes desplegados. Cada archivo upstream contiene una personalidad especializada y un procedimiento. **No hay proceso ni credenciales de orquestación en GitHub por el hecho de referenciar estos archivos**. No copiar código de terceros ni activar proveedores de pago sin consentimiento.

## 1. Topología de revisión

```text
                    Coordinator / evidence ledger (read-only)
                                  |
                +-----------------+--------------------+
                |                 |                    |
        MODEL SCIENCE       EPISODE/GIS DATA         PRODUCT/MARKET
          Stat + QA          Spatial + Data          PM + UX + Trend
                |                 |                    |
                +---------- source-anchored handoffs--+
                                  |
                        Research Synthesist
                                  |
                         Reality Checker
                                  |
                        DRAFT PR / NO AUTOSHIP
```

## 2. Hojas de agente

| Rol upstream | Archivo | Input obligatorio | Output y criterio |
|---|---|---|---|
| Statistician | `academic/academic-statistician.md` | formulas y datasets del repo, baseline, conteos | diseño pre-registrado, estadísticas que sí/no están medidas |
| Model QA Specialist | `specialized/specialized-model-qa.md` | funciones `fuse`, `deescalation_decision`, `pirineo_meta`, fixtures | catálogo claims, calibración, sesgos/filtraciones, criterios de aceptación |
| Spatial Data Scientist | `gis/gis-spatial-data-scientist.md` | estaciones, DEM, boyas, radar, campos NWP | tabla de problemas espaciales con reproducción y test esperado |
| Spatial Data Engineer | `gis/gis-spatial-data-engineer.md` | endpoints, esquema, CNP, tiempo/cota | contratos ingesta, QC, licencias, retención, deduplicación |
| Product Manager | `product/product-manager.md` | pantallas existentes, personas, trabajo por hacer | PRD de <=10 segundos, métricas de resultado |
| UX Researcher | `design/design-ux-researcher.md` | prototipo, recorridos de usuario | guion de prueba, evidencia vs hipótesis, accesibilidad |
| Trend Researcher | `product/product-trend-researcher.md` | competidores, proyectos públicos, user needs | escenarios de nicho, no TAM inventado |
| Research Synthesist | `research/research-synthesist.md` | entregables de los siete roles y evidencia externa | contradicciones, trazabilidad, síntesis sin duplicar fuentes |
| Reality Checker | `testing/testing-reality-checker.md` | PR, tests, fuentes, capturas y logs | PASS/NEEDS WORK/REJECT por claim y bloqueos |
| Multi-Agent Systems Architect | `engineering/engineering-multi-agent-systems-architect.md` | handoff y scope, presupuesto | límites de permisos, aislamiento y recuperación de fallos |

Links upstream: `https://github.com/msitarzewski/agency-agents/blob/main/<archivo>`.

## 3. Instrucciones por especialista (prompts específicos)

### Scientist / Model QA

> Examina el código real de MeteoPortinatx, no el README como evidencia suficiente. Reconstruye `fuse`, histéresis, tasas de ausencia, familias ENS, uso de observaciones, y fecha de emisión. Identifica cada variable que parece una probabilidad sin calibración demostrada. Diseña baseline, dataset de pares congelados, métricas y test out-of-sample. Separa OBSERVED, INFERRED, ASSUMED y UNTESTED. No modifiques los umbrales sin estudio retrospectivo.

### GIS / Spatial

> Verifica con coordenadas y tiempos la etiqueta de proximidad, la equivalencia entre costa y boyas, la resolución de radar y el uso del perfil sur en cotas de nieve. Propón advección radar 0–2h con evaluación FSS/CSI, benchmarks de persistencia y fail-closed. Si faltan datos, declara `NO_COMPARABLE`. Nunca inventes distancias, altitudes o errores medidos.

### Episode / Data Engineer

> Inspecciona las cuatro rutas CNP existentes. Construye un mapa de datos permitidos: endpoint, owner, condiciones de acceso, horario, TTL, licencia, privacidad, retención, revisión. Foros son evidencia no confiable; primero permiso y acceso. No saltar HTTP 403/robots. Diseña un episodio JSONL por productor, pronóstico pre-emisión congelado, observación verificada y anotación comunitaria manual. Evita PII e instrucciones embebidas en texto de origen.

### Product / UX / Market

> Compara tareas concretas de residente Portinatx, esquiador Cerdanya, forero experto, investigador y gestor local. Diseña una respuesta en <=10s que distinga oficial, observado, previsto, actualización y confianza. Informa qué hipótesis requieren entrevistas; mide success y error, no número de tarjetas. Mercado de nicho sin ingresos ni precisión inventados. Prioriza features por evidencia y coste real, incluido Render Free.

### Research Synthesist

> Recibe hallazgos marcados con `claim_id`, fuente y fecha. Fusiona sólo resultados no contradictorios; señala dónde distintas fuentes derivan del mismo origen; cita método, versión de código y URL externas. Produce un registro único de discrepancias abierto.

### Reality Checker

> Parte de NEEDS WORK. Comprueba cada afirmación contra código, pruebas o fuente primaria. Un test sintético no valida skill meteorológica. Rechaza piloto de foros sin política de permisos; rechaza «nowcast en vivo» si el backend Free duerme, o «forense persistente» en filesystem efímero. Las funciones científicas con P0 deben tener test reproducible antes de merge. Haz revisión de tres clases: integridad del software, validez científica y permisos/uso.

## 4. Contrato de salida entre roles

Cada hallazgo deberá registrar:

```json
{
  "id": "MTP-AUD-001",
  "claim": "descripción verificable y delimitada",
  "status": "OBSERVED_IN_CODE",
  "evidence": [{"source": "src/portinatx_degen.py", "symbol": "fuse"}],
  "severity": "P1",
  "uncertainty": "sin archivo histórico de verificación",
  "counterevidence": [],
  "owner_role": "model-qa",
  "proposed_test": "test de regresión concreto",
  "external_access": "NOT_REQUIRED",
  "next_decision": "mantener regla actual mientras se compara en sombra"
}
```

Enum `status`: `OBSERVED_IN_CODE`, `PRIMARY_SOURCE`, `SECONDARY_SOURCE`, `HYPOTHESIS`, `UNVERIFIED`, `BLOCKED`. No transformar `HYPOTHESIS` en `PRIMARY_SOURCE` al sintetizar. Un rol no puede aprobar sus propios resultados.

## 5. Gates y presupuesto

**G0:** fuente y permiso (no claves externas ni scraping no autorizado). **G1:** tests y SHA. **G2:** evaluación espacial/física (no 72h vs observación ahora). **G3:** privacidad/PII/copyright. **G4:** Reality Checker con evidencia independiente. **G5:** merge y despliegue manual autorizado por usuario. No se abren recursos Render nuevos ni se contratan APIs. El uso de la aplicación Agency Agents no forma parte del backend MeteoPortinatx.

## 6. Ejecución externa reproducible, si se conecta una herramienta de agentes

El repo upstream documenta instalación por herramienta. En un ordenador que tenga instalada la plataforma correspondiente y acceso GitHub:

```bash
# Ejemplo documental, NO ejecutado aquí:
git clone https://github.com/msitarzewski/agency-agents.git
cd agency-agents
./scripts/install.sh --tool codex --agent academic-statistician,specialized-model-qa,gis-spatial-data-scientist,gis-spatial-data-engineer,product-manager,design-ux-researcher,product-trend-researcher,research-synthesist,testing-reality-checker
```

Consultar primero `./scripts/install.sh --list agents` para resolver los *slugs reales* en la versión instalada; la lista anterior es orientativa. La instalación crea perfiles para la herramienta elegida: **no lanza tareas automáticamente**, no abre PR y no concede autorización para fusionar/deploy. La ejecución concreta requiere un orquestador compatible y su consentimiento/cuenta. Esta rama deja preparados prompts y contratos, no afirma haber lanzado diez instancias LLM simultáneas.
