# Reality Checker preliminar — MeteoPortinatx / Agency Agents

**Estado: NEEDS WORK.** Evaluación de una primera ronda de análisis. No equivale a una certificación externa de la calidad científica ni a una revisión de seguridad de producción. El rol Reality Checker ha sido utilizado como procedimiento de revisión, no como ejecución independiente de otra instancia de IA.

## 1. Matriz de comprobación

| Afirmación | Evidencia | Decisión |
|---|---|---|
| Agencia upstream ofrece perfiles de especialistas | README y archivos de `msitarzewski/agency-agents` | PASS: catálogo real, no runner autónomo |
| MeteoPortinatx 0.5.1 dispone de dos dominios y fallback estático | `README.md`, `src/public_fetch.js`, CI existente | PASS de existencia en código; no prueba SLA/skill |
| Existe un nowcast fiable cada 5 min | Render Free duerme; no hay observaciones operacionales exhaustivas | REJECT como claim actual |
| Los niveles de Portinatx son probabilidad meteorológica calibrada | `fuse` es max+gates, sin pares históricos suficientes | REJECT |
| CNP tiene cuatro estaciones referenciadas | `src/pirineo.py:CNP_STATIONS` | PASS de mapeo; coordenadas aproximadas y contrato legal desconocido |
| Podemos automatizar el scraping del foro | acceso directo 403, política/licencia no verificada | BLOCKED |
| La comunidad puede corroborar un episodio | sí, como pista no verificada y mediante fuentes independientes | HYPOTHESIS; requiere piloto |
| `sea_model_check` realiza comparación apareada | compara máximo de horizonte vs boya reciente | REJECT; revisión P1 |
| Todas las cotas de nieve representan N/S | resumen usa perfil sur | REJECT; revisión P1 |
| El dataset forense sobre Render Free es permanente | filesystem efímero | REJECT |
| El prototipo de evidencia comunitaria no recoge PII ni activa avisos | lista blanca estricta y tests locales nuevos | PASS sintético; sin validación de operación real |
| Skill Brier/CSI/CRPS del sistema | no hay backtest publicado | NO EVIDENCE |
| AEMET/Météo-France tienen canales de datos abiertos | documentación de origen | PASS de existencia; cada producto necesita revisión de condiciones |

## 2. Hallazgos que bloquean *producción científica*

**P0 (integridad de claims).** No llamar probabilidad calibrada a fracción ensemble; distinguir evidencia/hipótesis, fecha de emisión y fuente. No convertir `UNKNOWN` a cero. No incorporar relatos de foros como observaciones confirmadas.

**P1 (espacial).** Oleaje no apareado, proximidad de estaciones y extrapolación del perfil sur requieren corrección con pruebas y revisión de representatividad. Radar basado en escalar de acercamiento necesita evaluación contra tracking 2D antes de reclamar ETA fiable.

**P1 (histórico).** Sin pronósticos preepisodio congelados y datos instrumentales reconstruibles no puede demostrarse ni aprenderse de errores. La cadena SHA dentro de SQLite efímero no es garantía forense externa.

**P1 (fuentes).** CNP/foro no debe autoextraerse ni redistribuirse mientras no se verifiquen permisos, condiciones y metadatos de estaciones. Un acceso web 403 no se puede «reparar» eludiendo controles.

**P2 (producto).** No existe evaluación de tareas en 10 segundos ni medición de valor de mercado. El MVP requiere demostraciones y entrevistas antes de apostar por funcionalidades de más coste.

## 3. Pruebas realizadas y lo que NO prueban

En esta rama, `tests/test_episode_evidence.py` cubre validaciones, formatos de fechas y unidades, bloqueo de campos privados, fuentes URL, valores imposibles, deduplicación e invariantes de solo lectura. **No ha habido recolección de posts de foros, usuarios reales, ni ingestión de datos al backend en vivo**. Este PR es `draft` y la integración es deliberadamente una biblioteca desconectada del core.

CI de GitHub debe demostrar integridad SHA, suite Python 3.10/3.11 y test de cambios. Si hay un error de CI, actualizar el branch y mantenerlo draft. Si CI pasa, la evaluación científica queda igualmente `NEEDS WORK` por ausencia de archivo/habilitación de fuentes.

## 4. Gates para reclasificar

- **Software (PASS):** 3.10/3.11 + tests JS + integrity + `episode_evidence` nuevos.
- **Fuentes (PASS):** respuesta de licencia/permiso y prueba reproducible de estaciones con metadata validada.
- **Verificación (PASS):** al menos baseline de episodios históricos/pronósticos congelados y pruebas out-of-sample; ningún caso fallido silenciado.
- **Producto (PASS):** test de tareas con métricas, documentación de roles de usuario, validación de que no se interpreta como alerta oficial.
- **Producción (PASS):** almacenamiento externo realmente duradero, budget revisado, permisos, monitorización y alertas de fallo (no falso «nowcast 5 min» en Free).

**Dictamen final de esta ronda:** la investigación y la normalización manual merecen revisión en PR; **no** aprobar como herramienta de predicción operacional ni fusionar cambios de modelo/foros sin nuevo protocolo y evidencia de fuentes.
