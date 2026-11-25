# Pirineo Nowcast · relieve fino, cubeta fría y carreteras (EXPERIMENTAL)

**Idioma / Language:** Español · [English](PIRINEO-OROGRAFIA-CUBETA-CARRETERAS.en.md)

**Estado:** implementado; probado con datos sintéticos y con una ejecución manual real (25-11-2026). Revisión interna con agentes (código, física y verificación de afirmaciones), que no es una validación: lo aplicado de esa revisión y lo pendiente están en §2 y §6. **Ningún parámetro está calibrado con observaciones.** Nada de esto cambia avisos, niveles ni el diagnóstico 0–72 h existente: son tres bloques nuevos en `core` con estado propio. No sustituye a AEMET, Meteocat, el SMA, Météo-France ni a los servicios de tráfico.

## 1. Qué se añade

| Bloque de `core` | Módulo | Qué responde |
|---|---|---|
| `orografia` | `src/pirineo_orografia.py` | Cota de copo efectiva por punto (ahora y mínima en 24 h entre horas con precipitación): la del perfil menos el descenso por fusión con la precipitación local realzada por el relieve |
| `cubeta_fria` | `src/pirineo_orografia.py` | Mínima estimada en fondos de cuenca que los modelos de 2–9 km no resuelven (Das, Puigcerdà, Llívia, Bellver, Formiguères...) |
| `carreteras.oficial` | `src/pirineo_carreteras.py` | Incidencias oficiales de SCT y Bison Futé; Andorra e Inforoute 66 solo con enlace |
| `carreteras.exposicion` | `src/pirineo_carreteras.py` | Km de cada vía sobre la cota efectiva mínima en 24 h, tramos en cubeta y puertos |

Las tablas de relieve son estáticas: `src/pirineo_orografia.json` (≈137 kB, malla de 0,01° ≈ 1 km muestreada sobre un DEM de 90 m), generado por `scripts/build_orografia_pirineo.py` (numpy y scipy, fuera del núcleo). El núcleo solo usa la biblioteca estándar.

## 2. Física y parámetros (HIPÓTESIS)

**Forzamiento orográfico.** Modelo lineal de Smith y Barstad (2004) por FFT sobre el DEM Copernicus GLO-90 (malla de 0,01°, 42,15–43,05 N × 1,15–2,65 E: del Cadí y el Pedraforca a Foix, y del Pallars y el Montcalm al Canigó), para 16 rumbos con U = 14 m/s, N = 0,004 s⁻¹ y τ = 1000 s. Humedad por sector (Cw, Hw): N 0,0030/1800; NE 0,0035/2000; E 0,0060/2500; SE 0,0070/3000; S 0,0065/3000; SW 0,0060/3000; W 0,0040/2500; NW 0,0035/2000. Se guarda por punto la precipitación forzada (mm/h del modelo lineal, **relativa, no prevista**). En tiempo real se interpola por rumbo del viento a 700 hPa del perfil, se escala linealmente con su velocidad y se convierte en un **factor de realce sin unidades**: realce = min(2; 1 + 0,5 × forzamiento / 3 mm/h). La etiqueta de posición sale del mismo campo: «realce orográfico» (≥ 1 mm/h), «realce débil» o «sin realce (posible sombra)» (< 0,1 mm/h).

**Cota de copo efectiva.** Parte de `cota_copo_m` del perfil (Tw0 − 300 m, que ya incluye el enfriamiento por evaporación):

- Fusión: −min(400 m, 100·P^0,7), con P = precipitación horaria del perfil × realce, y nunca más que el espesor entre el suelo del perfil y Tw0. Solo si la precipitación del perfil es ≥ 0,1 mm/h: sin lluvia del perfil el relieve no funde nada. Sin precipitación conocida, la fusión es UNKNOWN y el estado `PARCIAL`; no se pone a 0.
- El föhn **no** se suma: el perfil de cada vertiente ya lo lleva y `core.foehn` lo diagnostica aparte. Una primera versión lo sumaba con el signo local de U·∇z; la revisión física mostró que contradecía al propio campo de Smith–Barstad (64 de 512 combinaciones punto-rumbo marcadas sotavento con forzamiento ≥ 1 mm/h) y que su magnitud no pasaba de ~70 m.
- La mínima de 24 h se toma **solo entre horas con precipitación** (una hora seca no da cota de nieve). Si no hay ninguna, `sin_precipitacion_24h` = true y `min24` = null, con estado OK (no es UNKNOWN). Solo las horas en `OK` cuentan; si alguna es `PARCIAL`, el punto queda `PARCIAL` y sus km de carretera cuentan como UNKNOWN.
- En la divisoria (Envalira, Puymorens) se usan los dos perfiles y se toma la cota más baja.

**Cubeta fría.** Índice CPI = (percentil 75 del relieve en ~13 km − z)/100 × log10(área que drena aire frío, D8, km²). ΔTmax = 20 °C × CPI/CPI(Das), con tope en 20 °C. Mínima estimada = mínima del modelo en 24 h − 0,6 × ΔTmax × (1 − nubosidad media de las 6 h previas y la hora de la mínima) × calma, con calma = 1 si el viento a 700 hPa ≤ 6 m/s y 0 si ≥ 14 m/s. Por modelo; un modelo sin nubosidad (AROME HD) queda UNKNOWN. Puntos con CPI < 1 (p. ej. Bolquère) no se tratan como cubeta (`NO_APLICA`). Con el tope, 7 de los 10 puntos de fondo de cuenca quedan con el mismo ΔTmax que Das: dentro de la cuenca el índice es casi binario.

**Límite conocido del índice.** El CPI crece con la profundidad del valle. En los valles estrechos de Andorra (Escaldes 9,4; Andorra la Vella 6,0) sale muy por encima de Das (2,9), lo que contradice la climatología. Por eso la cubeta solo se aplica en fondos de cuenca de la Cerdanya, la Cerdagne y el Capcir (`cubeta_calibrable`), y fuera de ellos el punto se publica con estado `NO_CALIBRADO`. Dentro de la cuenca, a 1 km de resolución, el índice **no distingue a Das de sus vecinos** (Puigcerdà 2,9; Llívia 4,8; Bellver 4,7). Que Das tenga la media más baja de España no está verificado en este trabajo.

## 2 bis. Modelo integrado: puntos de control, cimas y estaciones de esquí

Además de los 32 puntos de `pirineo.POIS` (que piden previsión por punto), la tabla incluye **97 puntos adicionales** que no piden previsión: usan el perfil de su vertiente (`norte` = al norte de la cresta axial, con el perfil del Ariège alto: Ariège, Donezan y Capcir, aunque el Capcir y el Donezan vierten al Aude; `sur` = perfil de la Cerdanya; `divisoria` = en cada hora el lado con precipitación y la cota más baja) y su forzamiento orográfico. Coordenadas y altitudes del geocodificador de Open-Meteo (GeoNames).

- **Ariège y Donezan (norte):** Tarascon, Les Cabannes, Luzenac, Ax, Orlu, Ascou, Mérens, L'Hospitalet, Camurac, Mijanès, Quérigut, Col de Pailhères; cimas Saint-Barthélemy, Soularac, Mont Fourcat, Tarbésou, Rulhe, Thoumasset, Baxouillade, Nérassol; Montcalm y Pica d'Estats (divisoria, barrera del NW).
- **Divisoria Ariège–Andorra–Carol–Capcir:** Cabaneta, Fontargente, Escobes, Serrera, Font Blanca, Tristaina, Medécourbe, Puig Pedrós (Lanós), Puig de Coma d'Or, Pic de la Mina, Puig Peric, Pic d'Envalira (nombre y cota de GeoNames por verificar); Mont-Louis y La Llagonne (Haut-Conflent, collado Têt–Segre–Capcir).
- **Andorra:** Coma Pedrosa, Casamanya, Estanyó, Pessons; El Tarter, Arinsal, La Cortinada.
- **Cerdanya, Cerdagne, Puigmal y Cadí (sur):** Puigpedrós, Tossa Plana de Lles, Calm Colomer, Roc Colom, Noufonts, Infern, Gra de Fajol, Puig Redon, Pic de l'Orri, Comabona, Pedraforca (Berguedà); Martinet, Prullans, Lles, Urús, Bolvir, Guils, Porta y Latour-de-Carol (Carol), Enveitg, Ur, Estavar, Targasonne, Odeillo, Err, Llo, Eyne, Saint-Pierre-dels-Forcats; Toses, Planoles, Ribes y Vall de Núria (Ripollès, con el perfil de la Cerdanya).
- **Capcir (norte):** Réal, Puyvalador, Pic de Madres, Puig de la Tossa. **Conflent:** Canigó (contexto de levante; usa el perfil de la Cerdanya, sin perfil propio).
- **17 estaciones de esquí** (`core.orografia.estaciones_esqui`): Ax 3 Domaines, Ascou-Pailhères y Mijanès-Donezan (punto de referencia en la carretera a la altitud de la base, aproximado), Camurac, Les Angles, Formiguères, Puyvalador (cerrada), Font-Romeu, Pyrénées 2000, Cambre d'Aze, Porté-Puymorens (divisoria), La Molina, Masella, Grandvalira en dos sectores (Pas de la Casa–Grau Roig, divisoria; Soldeu–El Tarter, sur), Ordino Arcalís (divisoria: el techo toca la cresta y recibe el desbordamiento del norte) y Pal Arinsal (sur). Cada una con punto de referencia, rango esquiable publicado (base–techo, con su fuente; La Molina y Masella sin verificar; en Camurac y Formiguères la base es la altitud del pueblo, aproximada) y la **fracción del desnivel esquiable por encima de la cota efectiva mínima de 24 h** («nieve en toda la estación», «solo en la parte alta», «lluvia hasta el techo»). No es el estado de las pistas ni su espesor.

Límites del modelo integrado: el perfil vertical sigue saliendo de dos puntos (Ariège alto y Cerdanya), así que la precipitación de cada hora de los puntos adicionales es la de su perfil, no la local; por eso Arcalís se trata como `divisoria`. En el motor, los puntos de `pirineo.POIS` conservan la vertiente de su mapa de zonas (`arcalis` sur, `porte` norte; la revisión geográfica propone `porte` como divisoria, pendiente porque cambia las cotas y el par de föhn del motor). Los perfiles de carretera usan puntos de paso: no recorren las curvas, así que las pendientes de los puertos (Puymorens, Pailhères, Font-Romeu) y los km no son los reales; el emboquille norte del túnel del Cadí es aproximado. Faltan, como siguiente paso, los collados de la Quillane y del Chioula, Campcardós, las cimas altas del Cadí, Vallter y Plateau de Beille, y la CG-1/N-145 La Seu–Andorra. Las cimas salen rebajadas en el DEM de ~1 km. En la divisoria, si un lado no tiene dato a una hora (o falta un perfil entero), esa hora queda `PARCIAL`. Las carreteras toman la cota solo de pueblos, collados y bases de estación (`pueblo`, `collado`, `estacion`), nunca de cimas ni de los puntos de referencia de estaciones de esquí. El estado global es OK solo si todos los puntos lo son; si hay alguno UNKNOWN o PARCIAL, es PARCIAL.

## 3. Carreteras

- **Oficial.** SCT: `https://www.gencat.cat/transit/opendata/incidenciesGML.xml`. Bison Futé / DIR Sud-Ouest (DATEX II, red nacional): `.../Evenementiel-DIR/grt/RRN/content.xml`. Filtro por caja 42,15–42,90 N × 1,40–2,30 E. Se marca `meteo` por palabras clave (nieve, hielo, cadenas, WinterDriving...). Las dos fuentes se piden en paralelo (15 s, sin reintentos). Un XML válido sin registros reconocibles es UNKNOWN («formato no reconocido»), no «sin incidencias»; un registro con coordenadas ilegibles se descarta y se cuenta. Caché de 15 min con su edad en `carreteras.oficial.edad_min`; si las dos fuentes fallan se sirve la última buena de ≤60 min y, si no, UNKNOWN. **UNKNOWN o SIN_FEED no significa vía libre.**
- **Sin fuente abierta:** Mobilitat Andorra (`/totes-incidencies`, fases groga, taronja, vermella y negra) e Inforoute 66 (red departamental: D618, D118...). Solo enlace.
- **Exposición.** 14 vías: CG-2, CG-3, RN22, RN20 Tarascon–Ax–L'Hospitalet, RN20 L'Hospitalet–Puymorens–Porté–Latour–Bourg-Madame, RN116, D618 Ur–Font-Romeu–Perche, D118 Capcir hasta Puyvalador, D613/D25 Ax–Col de Pailhères–Mijanès (cerrada en invierno), N-260 Toses, N-260 Seu, C-16, accesos a Masella y N-154. Puntos de paso (±1–2 km; los tramos de valle del Ariège, del Puymorens, del Carol y de Pailhères, por camino de menor coste en malla de 0,0025°), muestreadas cada ~0,5 km con el perfil ajustado al fondo de valle y las cotas de puerto forzadas (Envalira 2408, Pas de la Casa 2085, Puymorens 1915 en 42,560 N 1,8075 E, Toses 1800, Perche 1581, Pailhères 2001). Cada muestra toma la cota efectiva mínima en 24 h del punto de control más cercano (≤15 km); si allí no hay precipitación en 24 h, cuenta en `km_sin_precipitacion`; si no hay dato, en `km_unknown`. `km_sobre_cota` solo mide nieve que cae: **no cubre hielo, rehielo, ventisca ni nieve ya en el suelo**. Tramos en cubeta: muestras consecutivas de fondo de cuenca con CPI ≥ CPI(Das).

## 4. Regenerar las tablas

```bash
python3 scripts/build_orografia_pirineo.py                       # descarga el DEM (API de elevación de Open-Meteo, con esperas)
python3 scripts/build_orografia_pirineo.py --dem-npz dem.npz --roads-cache roads_cache.json   # con cachés locales
python scripts/integrity.py --write
```

Si cambian los puntos de `pirineo.POIS`, hay que regenerar el JSON: los puntos sin tabla no reciben diagnóstico.

## 5. Primera comprobación real (25-11-2026, flujo NW)

Ejecución manual sin registro en el repositorio (UNKNOWN para terceros). Con ARPEGE en el perfil y flujo NW, todo el fondo de la Cerdanya queda «sin realce»: Das, Puigcerdà, Bellver, Masella y La Molina, cota del perfil 1279 m → 1259 m en la única hora con precipitación (los 20 m son fusión con ~0,1 mm/h del perfil). Formiguères (perfil norte): 1982 m, 17 h con precipitación. Una versión anterior daba 1051 m en Masella tomando una hora **seca**: era el fallo que corrige la regla de «solo horas con precipitación». Cubeta con ICON-EU y nubosidad ~60 %: Das −1,1 → −4,4 °C, Puigcerdà −2,4 → −6,7 °C; Escaldes, Soldeu, Pas de la Casa, Porté y La Molina salen `NO_CALIBRADO`. SCT (209 registros, 14 en la caja) y Bison Futé (524, 16 en la caja) sin incidencias meteorológicas. Son estimaciones, no verificaciones.

## 6. Qué falta

- Calibrar fusión y cubeta con XEMA (Das, Bellver, Puigcerdà), Météo-France (Mont-Louis, Formiguères) y el SMA. Hasta entonces, HIPÓTESIS.
- Fusión por balance de energía acumulado (precipitación acumulada × calor latente frente al calor de la capa cálida), en lugar de la fórmula horaria: la actual subestima la lluvia moderada y continua con aire estancado y sobrestima los chubascos cortos.
- Cubeta con mejores predictores: estabilidad de la capa (T a 700–750 hPa − T2m) además del viento, nieve en el suelo, punto de rocío, nubosidad baja o niebla, duración de la noche y persistencia. Comprobar si la corrección de altitud de Open-Meteo calienta el fondo de valle con inversión.
- Índice de cubeta con el DEM nativo de 90 m: altura de la barrera de drenaje (relleno de depresiones), fracción de fondo llano, factor de vista del cielo, TPI multiescala. El índice actual (log del área drenada) premia los puntos aguas abajo.
- Revisar en la tabla: Envalira, Pas de la Casa y Grau Roig dan forzamiento 0 entre 67,5° y 90°; la deriva del modelo lineal (~28 km a 14 m/s) lleva precipitación a Das y Alp con viento del S.
- Vista en la consola: los bloques están en `core` pero aún no se pintan.
- Trazado real de las vías (OSM bloqueado en esta sesión) y fuente automática de Andorra.
- Föhn del sur y cubetas de Andorra y del Carol.
