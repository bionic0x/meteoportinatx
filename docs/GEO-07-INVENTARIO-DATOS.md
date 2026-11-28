# GEO-07 · Fase 07-0 — Inventario de datos para verificar la interacción frente/tormenta–relieve

**Estado:** borrador, 28-11-2026. Depende del protocolo `docs/GEO-07-PROTOCOLO.md` v0.1 (PR #82, sin fusionar).
**Alcance:** qué observaciones existen para verificar los submódulos 07a–h, con qué profundidad de archivo,
licencia y coste. No descarga nada, no activa proveedores y no toca el motor operativo.
**Sin verificación independiente:** los agentes revisores (Ante/NEXUS) no están disponibles hasta el 2-12-2026.

Etiquetas: **OBSERVADO** = comprobado en el código del repositorio o en la documentación oficial consultada hoy;
**SUPUESTO** = deducido, sin comprobar de forma directa; **UNKNOWN** = sin información suficiente.

## 1. Conclusión

1. **Hay datos suficientes para verificar el föhn (07e) y el bloqueo y desvío del flujo (07b/07c) con estaciones.**
   El motor ya lee las estaciones XEMA y las de Météo-France, y los pares barlovento/sotavento ya están definidos.
2. **No hay archivo de radar en reflectividad.** El radar de Météo-France y RainViewer solo sirven en tiempo
   real. Para un archivo de precipitación en Francia, la vía es **Coméphore** (reanálisis radar + pluviómetros,
   horario, ~1 km). En el lado español y en Andorra, el archivo de radar es UNKNOWN.
3. **Rayos: archivo continuo de MTG-LI solo desde julio de 2024.** Eso limita la verificación convectiva (07f/07g)
   a unas dos temporadas cálidas. El repositorio ya tiene el conector (`EUMETSAT_KEY`/`EUMETSAT_SECRET`), pero
   solo para tiempo real.
4. **El archivo del propio motor es el cuello de botella para R1** (la referencia «diagnóstico actual»). Sin un
   almacenamiento persistente de las salidas (decisión pendiente del usuario), R1 solo puede reconstruirse para
   episodios con perfiles de modelo recuperables.

## 2. Inventario

| ID | Fuente | Variables | Cobertura | Archivo | Acceso, clave y licencia | Estado | Uso en GEO-07 |
|---|---|---|---|---|---|---|---|
| D1 | **XEMA (Meteocat)**, Socrata `nzvn-apee` | T, HR, viento, racha, p, precipitación (semihorario) | Cataluña: Cerdanya, Alt Urgell, Ripollès | Plurianual en el portal abierto (profundidad por estación UNKNOWN) | Sin clave; datos abiertos de la Generalitat (licencia a confirmar por estación) | OBSERVADO: conector en `src/pirineo.py` | Föhn del sur y del norte en el lado catalán; frentes de racha (07f) |
| D2 | **Météo-France HOR**, `src/mf_obs.py` (`H_{dept}_latest`) | T, HR, viento, p, precipitación horaria | Ariège (09) y Pyrénées-Orientales (66): Porté, Font-Romeu, Les Angles… | Los ficheros `latest` cubren el año en curso y el anterior; los históricos completos, en ficheros por década del mismo servicio (SUPUESTO por la convención de nombres) | Licence Ouverte 2.0 (Etalab) | OBSERVADO: conector; histórico SUPUESTO | Pares de föhn `porte→puigcerda` y `les_angles→font_romeu` |
| D3 | **Estaciones de Andorra** (SMA / Andorra Recerca + Innovació) | T, HR, viento | Pas de la Casa, Encamp… | UNKNOWN | UNKNOWN: sin acuerdo de acceso documentado en el repositorio | UNKNOWN | Par `pas_casa→encamp` (FOEHN_PAIRS); sin datos, el par queda UNKNOWN |
| D4 | **Radar Météo-France** (API pública) | Reflectividad, lámina | Francia | **Sin archivo: retención de ~20 h** | Clave gratuita de portail-api | OBSERVADO (documentación oficial) | Solo nowcast; no sirve para verificar episodios pasados |
| D5 | **Coméphore** (Météo-France) | Lámina horaria radar+pluviómetros, ~1 km | Francia metropolitana, márgenes incluidos | Plurianual (año de inicio y fecha de corte UNKNOWN hasta abrir la ficha completa) | data.gouv.fr, Licence Ouverte 2.0 | OBSERVADO: ficha publicada; contenido no descargado | **Referencia de precipitación** para el realce orográfico (07d) en la vertiente norte y en la Cerdagne |
| D6 | **Radar AEMET / Meteocat** | Reflectividad compuesta | España | UNKNOWN para archivo descargable sin petición formal | UNKNOWN | UNKNOWN | Sin él, el realce y la sombra en la vertiente sur se verifican solo con pluviómetros (D1) |
| D7 | **RainViewer** (teselas) | Reflectividad renderizada (no dBZ) | Global | Solo las últimas horas | Gratuito; condiciones de uso propias | OBSERVADO: `portinatx_degen.py`, `src/radar_motion.py` | Solo seguimiento de ecos en tiempo real (07g); no cuantitativo |
| D8 | **MTG-LI** (EUMETSAT) | Grupos y flashes de rayo | Disco completo | **Continuo desde jul-2024** | EUMETSAT Data Store, clave gratuita; licencia EUMETSAT | OBSERVADO: conector `src_lightning`; archivo según el Data Store | Verificación convectiva (07f/07g) en 2024–2026 |
| D9 | **Perfiles de modelo** (Open-Meteo: ECMWF, ICON, AROME) | T, HR, u, v por niveles de presión | Malla del modelo | El archivo de pronósticos históricos depende del modelo; profundidad UNKNOWN | Open-Meteo sin clave (uso no comercial) | OBSERVADO: perfiles en `src/pirineo.py`; archivo UNKNOWN | Entradas de Fr, N y U⊥ (07a–c); referencia R2 |
| D10 | **ERA5 / CERRA** (Copernicus CDS) | Perfiles de reanálisis | ERA5 a 0,25°, CERRA a 5,5 km | 1940– / 1984– | Clave CDS (pendiente del usuario); licencia Copernicus | SUPUESTO hasta tener la clave | Reconstrucción de N y Fr en episodios antiguos |
| D11 | **Archivo del motor** (salidas JSON) | Diagnósticos de föhn, orografía, cota | Puntos del motor | **Sin almacenamiento persistente** | Propio | OBSERVADO: no hay histórico en el repositorio | Referencia R1; requiere decidir el almacenamiento |
| D12 | **DEM GLO-30 y derivados GEO-01** | Altitud, barrera, exposición | Pirineo oriental | Estático | Copernicus DEM, licencia gratuita con atribución | OBSERVADO (`docs/datos/sepi-geo01/`) | h_eff (barrera) y orientación de cada transecto |

## 3. Huecos que bloquean fases

| Hueco | Bloquea | Opciones (decide el usuario) |
|---|---|---|
| Sin estaciones de Andorra (D3) | Par `pas_casa→encamp` | Pedir acceso a SMA/AR+I, o declarar el par UNKNOWN de forma permanente |
| Sin radar descargable en la vertiente sur (D6) | Realce y sombra pluviométrica al sur (07d) | Pluviómetros XEMA; solicitar archivo a Meteocat |
| Archivo de rayos corto (D8) | Estadística convectiva (07f/07g) | Aceptar n pequeño y declararlo; no extrapolar |
| Sin archivo del motor (D11) | Referencia R1 | Almacenamiento persistente (pendiente desde F05) |
| Sin clave CDS (D10) | Episodios anteriores a los perfiles disponibles | El usuario define la clave en el entorno, nunca en el repositorio |

## 4. Próximo paso propuesto (07-2)

Seleccionar episodios según el §6 del protocolo **antes** de mirar las salidas del núcleo. Empezar por el föhn
del norte en `porte→puigcerda` (D2 + D1, ambos con conector) y el realce en la vertiente norte con Coméphore (D5).
Fijar la lista y registrarla en el §13 antes de ejecutar.
