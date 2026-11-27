# Avisos oficiales: vigencia y ámbito

Correcciones de la auditoría de solo lectura sobre la vigencia y el ámbito de los avisos oficiales (hallazgos A-01 a A-11). Este proyecto es experimental: **no emite avisos**. Se limita a mostrar los avisos de AEMET y MeteoAlarm. Si un aviso falta o no se pudo consultar, el estado es **UNKNOWN**, y UNKNOWN no equivale a calma.

**Principio rector:** un aviso oficial real nunca desaparece ni se rebaja por falta de metadatos (fin, inicio o zona horaria). Ante la duda, se muestra como incertidumbre.

## Lo corregido

| ID | Problema | Corrección | Dónde |
|---|---|---|---|
| A-01 (P0) | El EMMA_ID de Ibiza (`ES113`) se aceptaba para cualquier zona pedida, así que un aviso de Ibiza podía aparecer como aviso de una zona del Pirineo. | `ES113` solo se acepta si la zona pedida es la de Portinatx (`CFG["aemet_zone"]`). | `src/portinatx_degen.py`, `parse_cap_documents` |
| A-02 (P0) | Si caía el feed de MeteoAlarm de Francia o de Andorra, la fuente se marcaba igualmente «ok» y la interfaz decía «sin avisos». | La cobertura se calcula por país (`avisos_cobertura` en el `core`). `fuentes.avisos` vale `ok` solo si respondieron todos los países, `parcial: no se pudo consultar …` si fallaron algunos y `error: …` si fallaron todos. La interfaz dice «sin avisos» solo para los países que respondieron y nombra los no verificados como UNKNOWN. | `src/pirineo.py` (`warn_coverage_status`, `build`), `src/pirineo_app.html` |
| A-03 (P1) | El filtro por subcadena «girona» o «lleida» dejaba entrar, por ejemplo, «Litoral sur de Girona». Además, la interfaz afirmaba cubrir el Prepirineo de Barcelona y el Pirineo oscense, que MeteoAlarm no consultaba. | Para España se usa una lista blanca formada por las cuatro zonas Meteoalerta de `AEMET_ZONES` (más la variante «Pirineo de Gerona»), comparadas como palabras completas tras normalizar: NFKD sin diacríticos, minúsculas, y guiones y espacios unificados («Pyrénées Orientales» = «Pyrénées-Orientales»). «Pirineo de Girona» ya no casa con «Prepirineo de Girona». El texto de cobertura se genera a partir de lo consultado e indica que 66 y 09 son ámbitos departamentales. El motor de zonas usa la misma función (`zone_sources.area_matches`). | `src/pirineo.py` (`WARN_AREAS`, `WARN_SCOPE`, `warn_area_match`), `src/zone_sources.py` (`_normal`, `area_matches`) |
| A-04 (P1) | En Portinatx se mostraba «Sin avisos en las próximas 36 h» aunque la consulta hubiera fallado. | Si `official.verificado` no es verdadero, se muestra «No verificado: no se pudo consultar la fuente oficial. No equivale a ausencia de avisos.» | `src/portinatx_app.html` |
| A-05 (P1) | Un aviso sin `expires` quedaba vigente indefinidamente (Portinatx y Pirineo) o se borraba sin avisar (motor de zonas). | El aviso se conserva con `vigencia = "SIN FIN DECLARADO"` (en el motor de zonas, `validity = "end-not-declared"`) y se muestra como «vigencia no indicada por el emisor: incierta» **mientras el feed lo publique**. La retirada prudente cuenta desde la consulta (véase la sección «Decisiones»). La regla es la misma en los tres sitios. | `cap_window` en `portinatx_degen.py`, `pirineo.py`, `zone_sources.py`, `zone_report.py`, ambas interfaces |
| A-06 (P1) | La interfaz de Portinatx mantenía el estado «activo» calculado al emitir el ciclo. | `warnTiming` recalcula con la hora actual si el aviso está activo, próximo, finalizado (y entonces se oculta), con vigencia no indicada o con horario no verificable. Es la misma regla que `warningTiming` del Pirineo. | `src/portinatx_app.html`, `src/pirineo_observatory.js` |
| A-07 (P2) | Si faltaba `onset`, el aviso nunca se daba por activo. | Sin `onset` rige `effective` (CAP 1.2). | `cap_window` |
| A-08 (P2) | Una hora sin zona horaria se interpretaba como UTC sin avisar. El motor de zonas, además, descartaba sin avisar esos avisos y los que no tenían inicio. | Se marca `tz = "ASUMIDA_UTC"` y `vigencia = "SIN HORARIO VERIFICABLE"`. En el motor de zonas: `validity = "time-not-verifiable"`, `state = "possibly-active"` y, en el informe, el recuento «Avisos con horario no verificable: N». La ventana se ensancha 3 h por cada lado. Dentro de ella, el aviso es un **posible aviso** (`posible_ahora` / `posible`). Ese estado propio cumple lo siguiente:
- **Visible:** la cabecera de Portinatx muestra «posible aviso [nivel] · horario no verificable», nunca «Sin aviso vigente». Las tarjetas de decisión lo muestran como incierto y la señal del dispositivo como `unknown`.
- **Nunca es un hecho oficial:** no entra en `level_now`, ni en `vigente`/`vigentes`, ni en el suelo institucional. Por tanto, `fuse` no sube la precaución por esa vía y no puede forzar ALARM. El canal institucional solo lleva la marca «⚠ posible aviso … · horario no verificable: no cuenta como nivel oficial ni como suelo».
- **En `build_claims`:** se registra como afirmación `UNKNOWN` con la etiqueta `HORARIO_NO_VERIFICABLE`, nunca como «AEMET mantiene aviso».

Lo mismo vale para un aviso sin `onset` ni `effective` o con una hora ilegible. | `cap_window`, `ch_institutional`, `build_claims`, `zone_sources.warnings`, `zone_report.py`, `nowcast_backend.py` (proyección pública), `decision_cards.js`, `device_sensors.js`, interfaces |
| A-10 (P2) | Portinatx no mostraba la hora de emisión, la edad ni la zona. | `official.all` incluye `emitido` (el campo `sent`), `area`, `vigencia` y `caduca_prudente`. La interfaz muestra la zona, la hora de emisión y la edad («hace N h»). En el Pirineo se muestra la hora de emisión. | `portinatx_degen.py`, `portinatx_app.html`, `pirineo_app.html` |

## Decisiones

- **Aviso sin `expires`: N = 24 h desde la consulta.** Las constantes son `CAP_SIN_FIN_H` en `portinatx_degen.py` y `NO_EXPIRES_MAX_H` en `zone_sources.py`; un test comprueba que coinciden.
  - Mientras el feed lo publique, el aviso sigue visible en cada ciclo, sea cual sea la antigüedad de su `sent` o de su inicio.
  - `caduca_prudente` vale la hora del ciclo + 24 h. Solo sirve para que la interfaz lo retire de una instantánea vieja, es decir, de un ciclo que ya no se ha vuelto a consultar.
  - Por qué 24 h: AEMET reelabora los avisos varias veces al día, y el feed de MeteoAlarm cubre solo el día actual y el siguiente.
- **Hora dudosa: holgura de 3 h.** Las constantes son `CAP_TZ_HOLGURA_H` y `TZ_SLACK_H`; un test comprueba también que coinciden.
  - Los feeds consultados son de España, Francia y Andorra, cuya hora oficial difiere de UTC entre 0 y 2 h (UTC+0 en Canarias; UTC+1 o UTC+2 en la península, Baleares, Francia y Andorra). Las 3 h cubren ese desfase con 1 h de margen.
  - El aviso se descarta si su fin, leído como UTC, quedó más de 3 h atrás. Un aviso que terminó hace 13 h ya no cuenta.
  - Es «posible» desde 3 h antes de su inicio. Uno que empieza dentro de 12 h aparece como próximo, no como posible.
  - Siempre lleva la marca «horario no verificable» y nunca se presenta como hecho oficial ni fuerza ALARM.
- **Sin inicio (ni `onset` ni `effective`): posible aviso** hasta su `expires`, si lo hay. Nunca se descarta por esa falta.
- **Edad del dato:** junto a los avisos «vigencia no indicada» y «posible aviso», las dos interfaces muestran «según el ciclo de hace X h».
- **El inicio es `onset` y, si falta, `effective`.** No se usa `sent` como inicio.
- **«Sin avisos» exige cobertura completa.** Se afirma solo para las fuentes que respondieron. Los países que no respondieron aparecen como UNKNOWN con su nombre. `decision_cards.js` y `device_sensors.js` solo aceptan `fuentes.avisos` cuando empieza por `ok`, así que un estado `parcial` queda como no verificado (`docs/DECISION-P0.md`, punto 4).
- **Ámbito español del Pirineo: las cuatro zonas de `AEMET_ZONES`, más la variante «Pirineo de Gerona».** Así MeteoAlarm y el CAP de AEMET cubren lo mismo. «Prepirineo de Girona» y «Prepirineo de Lleida», que antes entraban por la subcadena, quedan fuera porque nunca se declararon como cobertura. Los nombres «Pirineo de Lleida» y «Pirineo oscense» se vieron en el feed real el 26/11/2026. «Pirineo de Girona» y «Prepirineo de Barcelona» siguen el mismo formato, pero ese día no tenían aviso y son SUPUESTO.
- **Francia (66 y 09) y Andorra** conservan sus claves. La interfaz indica que 66 y 09 son ámbitos departamentales, que también incluyen el litoral del Rosellón y la llanura.
- **La plantilla del motor de zonas solo incluye áreas que contienen alguno de sus puntos.**
  - La plantilla `pirineo` de `zone_engine.py` tiene tres puntos: Masella (Alp, en el Pirineo de Girona), Font-Romeu (Pyrénées-Orientales, 66) y Andorra la Vella (Andorra). Por eso su ámbito es `pirineo de girona`, `pyrénées-orientales` y `andorra`; el criterio está comentado junto a la plantilla.
  - Se han quitado `pirineo de lleida` y `ariège` (09), que no contienen ninguno de esos puntos.
  - `pirineo.py`, en cambio, cubre los puntos de todo el observatorio y la vía CAP de AEMET (`AEMET_ZONES`), con cuatro zonas españolas y 66 y 09.
  - Ambos motores comparten la normalización de los nombres y la regla temporal.

## Tests

- `tests/test_avisos_vigencia_ambito.py` (casos parametrizados):
  - aviso caducado, futuro o en vigor;
  - sin `expires`: con `sent` de hace 25 h, y sin `sent` con inicio de hace 30 h (ambos siguen visibles);
  - sin `onset` pero con `effective`, y sin `onset` ni `effective` (posiblemente activo);
  - hora sin zona horaria: en curso, con `expires` pasado hace menos de 3 h leído como UTC (se conserva) y terminado hace 13 h (se retira); uno que empieza dentro de 12 h no es posible ni activo;
  - posible aviso: visible, sin nivel oficial ni suelo, `fuse` no propone ALARM y la afirmación es `UNKNOWN` con la etiqueta `HORARIO_NO_VERIFICABLE`;
  - zona ajena;
  - aviso de Ibiza pedido para la zona 691701, con geocode y solo con EMMA_ID;
  - feed de Francia caído y filtro de ámbito: «Litoral sur de Girona», «Prepirineo de Girona», «Pirineo de Gerona», mayúsculas, tildes en NFD y «Pyrénées Orientales» con espacio;
  - estado de cobertura;
  - motor de zonas: sin `expires`, sin zona horaria, sin inicio, NFD y «Gerona».
- `tests/test_avisos_portinatx_browser.py` y `tests/test_avisos_pirineo_browser.py`: pruebas en navegador real. Comprueban:
  - el «No verificado»;
  - la vigencia calculada con la hora actual;
  - la cobertura por país;
  - la vigencia no indicada;
  - que un aviso rojo con hora sin zona horaria aparece como «posible aviso rojo · horario no verificable» y no deja la cabecera en «Sin aviso vigente» (Portinatx) ni el listado en «sin avisos» (Pirineo);
  - el texto «según el ciclo de hace X h».
- `tests/test_pirineo_observatory.cjs`: casos nuevos de `warningTiming` (sin fin declarado, sin zona horaria y su holgura de 3 h).
- `tests/test_decision_cards.cjs` y `tests/test_device_sensors.cjs`: un posible aviso aparece como incierto y nunca como calma.

Los tests de Python se descubren con `python src/nowcast.py selftest` (`unittest discover -s tests`), y el archivo `.cjs` ya estaba en `.github/workflows/ci.yml`.

## No cubierto

- **Conectores de Meteocat (avisos SMP), de la vigilance de Météo-France y del SMA de Andorra.** No existen. Francia y Andorra solo llegan a través de MeteoAlarm.
- **Nombres reales de MeteoAlarm.** Solo se verificaron los que tenían aviso el 26/11/2026 (véase la sección «Decisiones»). Hay que confirmar «Pirineo de Girona», «Prepirineo de Barcelona», «Pyrénées-Orientales», «Ariège» y los nombres de Andorra (el feed de Andorra estaba vacío). Una alternativa más robusta sería comparar el EMMA_ID o el código de zona del identificador. Por ejemplo, el aviso «Valle de Arán» del 26/11/2026 llevaba `ES186` y la zona `692501` en `cap:identifier`.
- **Geocodes reales del tar de AEMET (EMMA_ID por zona del Pirineo).** Verificarlos requiere `AEMET_API_KEY`, que nunca va en el repositorio ni en los tests. Por eso el Pirineo no tiene EMMA_ID propios.
- **Polígonos CAP (A-09).** Se ignoran. La comprobación de que el punto cae dentro del polígono queda pendiente.
- **Update y Cancel con `<references>` (A-11).** Todavía no se resuelve qué aviso sustituye a cuál, y un Alert y su Update pueden aparecer juntos.
- **Nivel del eje oficial en Portinatx.**
  - La cabecera muestra el mayor de dos niveles: el `level_now` del ciclo y el de los avisos en vigor a la hora actual (con fin declarado o sin él).
  - Nunca baja de `level_now`, aunque un aviso haya caducado desde el ciclo.
  - Los posibles avisos solo añaden la marca de incertidumbre.
  - La precaución sigue siendo la del ciclo.
- **Notificación de aviso nuevo (`detect_warning_changes`).** Un posible aviso nuevo se notifica igual que cualquier aviso nuevo del feed, sin la marca «horario no verificable» en el texto de la notificación.
- **Caché `_cached` (180 min) frente a `expires`.** No se ha revisado.
