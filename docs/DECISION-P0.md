# Decision P0 — cinco vistas rápidas sobre los motores actuales

**Idioma / Language:** Español · [English](DECISION-P0.en.md)

**Estado:** vista de producto en revisión; no modelo meteorológico nuevo, no acreditación de seguridad, no servicio de avisos ni API adicional. Preparación de la línea MeteoPortinatx 0.6; la versión de integración 0.5.1 sigue vigente hasta decidir release.

## Contrato de producto

| Perfil | Pregunta prioritaria | Presentación P0 | Profundización |
|---|---|---|---|
| Casa junto a torrente | ¿Qué ha cambiado y qué debo comprobar? | Aviso verificado, cuatro canales observados (pluviómetros, METAR, radar, rayos), precaución **calculada** | Portinatx · Vigilancia |
| Barca / amarre | ¿Hay señales de viento o mar y avisos? | Aviso verificado, viento, mar, rayos; **no** compara boyas/modelo sin pareo | Portinatx · Mar |
| Segunda residencia | ¿Qué se prevé para la zona de casa? | Selección entre puntos publicados, aviso institucional, nieve/temperatura/racha previstas por **un** modelo | Pirineo · Puntos y cotas |
| Esquí / montaña | ¿Qué prevé un modelo para una estación? | Punto seleccionable, nieve 24 h, racha 24 h; sin certificar pistas, carreteras o aludes | Pirineo · Corte y diagnóstico |
| Meteo | ¿Qué se observa y qué estima el motor? | **Ficha de auditoría del ciclo**: avisos literales, mediciones con antigüedad y evidencia, modelos con su rango de discrepancia, razonamiento del motor y fuentes que fallan; sin llamar «probabilidad» a una fracción ensemble | Portinatx · Forense, con enlaces por bloque |

La interfaz es `/decidir/` y mantiene la consola actual en los observatorios. Los enlaces desde el portal y las dos consolas son aditivos; no se reescriben unas 60 secciones del motor original.

## Contrato de datos y garantías

1. **Único documento por dominio:** se consume solo `core.json`, mediante `meteoLoadPart(domain, 'core', staticPath)`. Por tanto, un panel nunca mezcla `core` con `series` o `radar` de generaciones distintas. Los análisis completos se hacen en la consola anterior, que mantiene su carga atómica de partes.
2. **Origen visible:** si `METEO_BACKEND_URL` está configurada, se utiliza API *solo* con `X-Meteo-Snapshot` y `X-Meteo-Freshness: fresh` accesibles por CORS; si falla, cae al **mismo** `core.json` del snapshot de Pages. La vista no activa la variable ni modifica Render.
3. **Frescura operativa:** `issued` UTC/TZ obligatorio; 60 min para Portinatx y 360 min para Pirineo son **umbrales de presentación** y no garantía de vigencia de cada estación. Fecha futura >5 min, sin zona horaria o ilegible = `UNKNOWN`. Si el ciclo está caducado, se suprimen por completo recomendaciones/valores del ciclo para evitar falsa sensación de actualidad.
4. **Separación epistémica:** AEMET/avisos solo se marcan como verificados con `official.verificado === true` (costa) o `fuentes.avisos` con estado `ok` (montaña). El nivel `quiet` es un **nivel interno** y nunca implica «seguro». Instrumentos `UNKNOWN` no se convierten en 0. Los datos de montaña se etiquetan como «estimación de modelo»; no equivalen a nieve acumulada o estado de carretera.
5. **Privacidad:** no se cargan `state.json`, notas privadas, forense local, observaciones manuales de inundación (`runoff`/`flooding`) ni datos de dirección particular. No se persiste un perfil en cookie o localStorage. Los valores mostrados se insertan como texto, no HTML de proveedores. No hay funciones `POST`.
6. **Seguridad:** no ordena mover un coche o salir a navegar, no califica seguridad en montaña, no sustituye protección civil / AEMET / Météo-France / SMA. Nunca se presenta como monitorización permanente ni como alerta push en Pages/Render Free.

## Ficha del perfil Meteo («Investigar el episodio»)

La ficha audita **un** ciclo del motor en una pantalla. No es otra consola, no añade pronósticos ni índices y no da una respuesta de seguridad. Sale del mismo `core.json` (campo `episode` de `project('meteo', …)`), sin peticiones nuevas.

1. **Orden fijo:** aviso oficial, medido, modelo y conjunto, análisis propio, fuentes. La procedencia se distingue por borde, signo y palabra, no solo por color. El nivel interno (0–3) usa escalones monocromos; el color institucional solo aparece en el chip del aviso oficial.
2. **Avisos:** se leen de `official.all` con `activo: true`, se deduplican (CAP y MeteoAlarm repiten el mismo aviso) y se descartan los que ya han vencido al consultar y los suelos introducidos a mano en el motor, que no son texto del organismo. El nivel mostrado es el literal del organismo, no `level_now`.
3. **Sin dato no es cero:** un canal cuyo `available` no es exactamente `true` se muestra como «sin dato · no equivale a calma», aunque traiga `level: 0`. La edad publicada es la del dato más reciente del canal; en modelos es la hora de descarga y no se muestra.
4. **Lista de permitidos:** solo los canales conocidos enseñan su evidencia; de las razones del motor solo las de forma `canal=nivel` y `suelo institucional = nivel`. No se muestran observaciones manuales, `precaution.hold/decision/exit_conditions`, afirmaciones del propietario, disenso, anomalías, `sources[].detail` ni texto libre. La instantánea de Pages no pasa por la proyección pública del backend, por eso el filtro se aplica también en el cliente.
5. **Texto del motor:** se muestra literal, con cuatro sustituciones deterministas: `nan` → «sin dato», `STALE → UNKNOWN` → «dato caducado → no se usa», `MOTION_UNKNOWN` → «movimiento no determinable» y `P(24h≥50)=0%` → «0 % de miembros ≥50 mm/24 h». Un parte METAR de más de 6 h respecto al ciclo se marca como no actual.
6. **Modelos:** el rango de racha y CAPE solo se muestra si la extracción estricta casa en todos los modelos disponibles; son máximos a 48 h en el punto, sin hora. No se calcula media ni consenso.
7. **Origen recortado:** con la API (sin evidencia, razones ni afirmaciones) la ficha lo dice («no publicado por este origen») y no inventa nada. Con arranque en frío (un solo ciclo en `history`) no se muestra transición.
8. **Alcance:** solo Portinatx. El `core.json` del Pirineo no publica canales ni razonamiento del motor.

## Pruebas de aceptación

- `node tests/test_decision_cards.cjs`: 31 casos: los cinco perfiles, esquema real de canales, privacidad, `UNKNOWN`, caducidad, timestamp inválido, elección de localidad sin sustituirla por otra, y la ficha del perfil Meteo (lista de permitidos, «sin dato» que no es nivel 0, avisos vencidos, origen recortado).
- `python -m unittest discover -s tests`: integración de rutas `/decidir/`, `/decision_cards.js` y salida estática.
- `python scripts/build_site.py` después de exportar *ambos* dominios: produce `site/decidir/index.html` y `site/decision_cards.js`.
- `python scripts/integrity.py --check`: manifiesto íntegro.
- El `.pyz` debe contener ambos recursos; en local `/public_config.js` se mantiene vacío y no utiliza Render.

**Gates pendientes:** prueba de usabilidad con al menos cinco personas por segmento, registros de tiempo por tarea (objetivo exploratorio de 10 s, no resultado logrado), prueba real en móvil y revisión con data fresca en los dos dominios. Ni el paso de CI ni un diseño compacto confirman que un usuario resuelva una decisión en diez segundos. La siguiente fase debe añadir una línea temporal del episodio con evidencias y prospectiva del Forecast Ledger.
