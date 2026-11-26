# Avisos oficiales: vigencia y ámbito

Correcciones de la auditoría de solo lectura sobre la vigencia y el ámbito de los avisos oficiales (hallazgos A-01 a A-11). Este proyecto es experimental: **no emite avisos**. Se limita a mostrar los avisos de AEMET y MeteoAlarm. Si un aviso falta o no se pudo consultar, el estado es **UNKNOWN**, y UNKNOWN no equivale a calma.

## Lo corregido

| ID | Problema | Corrección | Dónde |
|---|---|---|---|
| A-01 (P0) | El EMMA_ID de Ibiza (`ES113`) se aceptaba para cualquier zona pedida, así que un aviso de Ibiza podía aparecer como aviso de una zona del Pirineo. | `ES113` solo se acepta si la zona pedida es la de Portinatx (`CFG["aemet_zone"]`). | `src/portinatx_degen.py`, `parse_cap_documents` |
| A-02 (P0) | Si caía el feed de MeteoAlarm de Francia o de Andorra, la fuente se marcaba igualmente «ok» y la interfaz decía «sin avisos». | La cobertura se calcula por país (`avisos_cobertura` en el `core`). `fuentes.avisos` vale `ok` solo si respondieron todos los países, `parcial: no se pudo consultar …` si fallaron algunos y `error: …` si fallaron todos. La interfaz dice «sin avisos» solo para los países que respondieron y nombra los no verificados como UNKNOWN. | `src/pirineo.py` (`warn_coverage_status`, `run_all`), `src/pirineo_app.html` |
| A-03 (P1) | El filtro por subcadena «girona» o «lleida» dejaba entrar, por ejemplo, «Litoral sur de Girona». Además, la interfaz afirmaba cubrir el Prepirineo de Barcelona y el Pirineo oscense, que MeteoAlarm no consultaba. | Para España se usa una lista blanca formada por las cuatro zonas Meteoalerta de `AEMET_ZONES`, comparadas como palabras completas. «Pirineo de Girona» ya no casa con «Prepirineo de Girona». El texto de cobertura se genera a partir de lo consultado e indica que 66 y 09 son ámbitos departamentales. El motor de zonas también compara palabras completas. | `src/pirineo.py` (`WARN_AREAS`, `WARN_SCOPE`, `warn_area_match`), `src/zone_sources.py` |
| A-04 (P1) | En Portinatx se mostraba «Sin avisos en las próximas 36 h» aunque la consulta hubiera fallado. | Si `official.verificado` no es verdadero, se muestra «No verificado: no se pudo consultar la fuente oficial. No equivale a ausencia de avisos.» | `src/portinatx_app.html` |
| A-05 (P1) | Un aviso sin `expires` quedaba vigente indefinidamente (Portinatx y Pirineo) o se borraba sin avisar (motor de zonas). | El aviso se conserva con `vigencia = "SIN FIN DECLARADO"` y se muestra como «vigencia no indicada por el emisor: incierta». Se retira a las N horas (véase la sección «Decisiones»). La regla es la misma en los tres sitios. | `cap_window` en `portinatx_degen.py`, `pirineo.py`, `zone_sources.py`, `zone_report.py`, ambas interfaces |
| A-06 (P1) | La interfaz de Portinatx mantenía el estado «activo» calculado al emitir el ciclo. | `warnTiming` recalcula con la hora actual si el aviso está activo, próximo, finalizado (y entonces se oculta), con vigencia no indicada o con horario no verificable. Es la misma regla que `warningTiming` del Pirineo. | `src/portinatx_app.html`, `src/pirineo_observatory.js` |
| A-07 (P2) | Si faltaba `onset`, el aviso nunca se daba por activo. | Sin `onset` rige `effective` (CAP 1.2). | `cap_window` |
| A-08 (P2) | Una hora sin zona horaria se interpretaba como UTC sin avisar. | Se marca `tz = "ASUMIDA_UTC"` y `vigencia = "SIN HORARIO VERIFICABLE"`, y el aviso no se da por activo. Se sigue mostrando, como incertidumbre. El motor de zonas ya rechazaba estas horas. | `cap_window`, interfaces |
| A-10 (P2) | Portinatx no mostraba la hora de emisión, la edad ni la zona. | `official.all` incluye `emitido` (el campo `sent`), `area`, `vigencia` y `caduca_prudente`. La interfaz muestra la zona, la hora de emisión y la edad («hace N h»). En el Pirineo se muestra la hora de emisión. | `portinatx_degen.py`, `portinatx_app.html`, `pirineo_app.html` |

## Decisiones

- **N = 24 h** (`CAP_SIN_FIN_H` en `portinatx_degen.py` y `NO_EXPIRES_MAX_H` en `zone_sources.py`; un test comprueba que coinciden). Un aviso sin `expires` se retira 24 h después de su emisión (`sent`). Si falta `sent`, se cuenta desde el inicio (`onset` o `effective`). Motivos:
  - AEMET reelabora los avisos varias veces al día.
  - El feed de MeteoAlarm cubre solo el día actual y el siguiente.

  Un aviso sin fin que siga en el feed vuelve a entrar en el siguiente ciclo, de modo que la retirada no lo hace desaparecer en silencio mientras el emisor lo mantenga. Si no hay ninguna referencia temporal, el aviso se muestra como «horario no verificable» mientras el feed lo publique.
- **El inicio es `onset` y, si falta, `effective`.** No se usa `sent` como inicio.
- **«Sin avisos» exige cobertura completa.** Se afirma solo para las fuentes que respondieron. Los países que no respondieron aparecen como UNKNOWN con su nombre. `decision_cards.js` y `device_sensors.js` solo aceptan `fuentes.avisos` cuando empieza por `ok`, así que un estado `parcial` queda como no verificado (`docs/DECISION-P0.md`, punto 4).
- **Ámbito español del Pirineo: las cuatro zonas de `AEMET_ZONES`.** Así MeteoAlarm y el CAP de AEMET cubren lo mismo. «Prepirineo de Girona» y «Prepirineo de Lleida», que antes entraban por la subcadena, quedan fuera porque nunca se declararon como cobertura. Los nombres «Pirineo de Lleida» y «Pirineo oscense» se vieron en el feed real el 26/11/2026. «Pirineo de Girona» y «Prepirineo de Barcelona» siguen el mismo formato, pero ese día no tenían aviso y son SUPUESTO.
- **Francia (66 y 09) y Andorra** conservan sus claves. La interfaz indica que 66 y 09 son ámbitos departamentales, que también incluyen el litoral del Rosellón y la llanura.

## Tests

- `tests/test_avisos_vigencia_ambito.py` (casos parametrizados):
  - aviso caducado, futuro o en vigor;
  - sin `expires`, y sin `expires` ya retirado;
  - sin `onset` pero con `effective`;
  - hora sin zona horaria;
  - zona ajena;
  - aviso de Ibiza pedido para la zona 691701, con geocode y solo con EMMA_ID;
  - feed de Francia caído y filtro de ámbito («Litoral sur de Girona», «Prepirineo de Girona»);
  - estado de cobertura;
  - motor de zonas.
- `tests/test_avisos_portinatx_browser.py` y `tests/test_avisos_pirineo_browser.py`: pruebas en navegador real. Comprueban el «No verificado», la vigencia calculada con la hora actual, la cobertura por país y la vigencia no indicada.
- `tests/test_pirineo_observatory.cjs`: casos nuevos de `warningTiming` (sin fin declarado y sin zona horaria).

Los tests de Python se descubren con `python src/nowcast.py selftest` (`unittest discover -s tests`), y el archivo `.cjs` ya estaba en `.github/workflows/ci.yml`.

## No cubierto

- **Conectores de Meteocat (avisos SMP), de la vigilance de Météo-France y del SMA de Andorra.** No existen. Francia y Andorra solo llegan a través de MeteoAlarm.
- **Nombres reales de MeteoAlarm.** Solo se verificaron los que tenían aviso el 26/11/2026 (véase la sección «Decisiones»). Hay que confirmar «Pirineo de Girona», «Prepirineo de Barcelona», «Pyrénées-Orientales», «Ariège» y los nombres de Andorra (el feed de Andorra estaba vacío). Una alternativa más robusta sería comparar el EMMA_ID o el código de zona del identificador. Por ejemplo, el aviso «Valle de Arán» del 26/11/2026 llevaba `ES186` y la zona `692501` en `cap:identifier`.
- **Geocodes reales del tar de AEMET (EMMA_ID por zona del Pirineo).** Verificarlos requiere `AEMET_API_KEY`, que nunca va en el repositorio ni en los tests. Por eso el Pirineo no tiene EMMA_ID propios.
- **Polígonos CAP (A-09).** Se ignoran. La comprobación de que el punto cae dentro del polígono queda pendiente.
- **Update y Cancel con `<references>` (A-11).** Todavía no se resuelve qué aviso sustituye a cuál, y un Alert y su Update pueden aparecer juntos.
- **Nivel del eje oficial en Portinatx (`level_now`).** Sigue siendo el del ciclo; solo la lista se recalcula con la hora actual.
- **Caché `_cached` (180 min) frente a `expires`.** No se ha revisado.
