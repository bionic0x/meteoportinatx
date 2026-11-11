# Planificador de rutas del Pirineo (`/pirineo/ruta/`)

Superpone el pronóstico sobre la **posición estimada** de un track GPS según la hora de salida y el ritmo. Estado: **MVP, solo Pirineo oriental, probado únicamente con datos sintéticos**.

## Qué hace

1. El usuario sube un **GPX** (o usa la ruta de demostración sintética) y elige la hora de salida y el ritmo.
2. El track se remuestrea cada ~200 m. Cada punto recibe una **hora estimada** (Tobler × factor + pausas, o los tiempos grabados del track) y una **ventana** ±15 % del tiempo transcurrido.
3. En cada punto y hora se interpola la rejilla de pronóstico (espacio: bilineal; tiempo: lineal; acumulados por bloques de 3 h).
4. Se evalúa **cada peligro por separado**: lluvia, viento (racha), nieve y frío (sensación térmica). El resultado se muestra en un resumen, un mapa con relieve, un perfil con franjas por peligro y una tabla de tramos.

## Privacidad (requisito de diseño)

- El GPX se lee y se calcula **en el navegador**; no se sube ni se guarda (ni `localStorage`).
- La página no usa fuentes ni teselas de terceros: las únicas peticiones son los JSON públicos del propio sitio (`core`, `dem`, `grid`).
- `tests/test_route_page_browser.py` lo comprueba en Chrome real: cero peticiones externas, ninguna petición tras subir un track, nada del track en URL o cuerpo, solo `GET`.

## Principios del proyecto aplicados

- **Fallo cerrado.** Fuera de la rejilla, fuera del horizonte (48 h), con datos faltantes o con rejilla inválida el resultado es *sin datos*, nunca «sin riesgo». La página lo dice y el color es gris rayado.
- **Un indicador por peligro**, sin nota global.
- **Ventanas horarias**, no horas exactas.
- **Contexto ≠ observación.** Esta herramienta no emite avisos ni modifica niveles del motor.
- **Umbrales sin procedencia oficial** declarados como `UNVERIFIED` u `ORIENTATIVE` en `THRESHOLDS` (`src/route_engine.js`).

## Datos que consume

`grid.json` del Pirineo (modelo `OM_MODELS[0]`, 0,05°, paso 3 h, 48 h), ampliado en esta versión con `dew_point_2m` y `wind_speed_10m`, y con `paso_h` y `acumulado` que declaran la semántica de los acumulados: el bloque con marca `t_k` suma las horas `k..k+2` y cubre `(t_k − 1 h, t_k + 2 h]`. También `dem.json` (relieve de ~440 m) y `core.avisos` (se listan sin geolocalizar sobre la ruta).

## Física (y su paridad con Python)

- **Temperatura a la cota del track:** con la altitud de la celda y la isocero del modelo se obtiene un gradiente; si cae en 3–9 K/km se usa, si no 6,5 K/km y se marca el perfil como incierto (posible inversión).
- **Fase:** misma regla que `pirineo.snow_frac` (rampa sobre el bulbo húmedo centrada en 0,7 °C, ancho ±1 °C; HIPÓTESIS sin calibrar), con el punto de rocío a la cota del track suponiendo depresión constante. Tests de paridad numérica JS↔Python en `tests/test_route_engine.py` (solid fraction, bulbo húmedo y DEM).
- **Nieve:** en mm de agua equivalente; no se convierte a cm (la relación nieve/agua es variable).
- **Racha:** máximo de las dos salidas contiguas. En crestas y collados (DEM, anillo de 1,5 km, ≥150 m sobre el entorno) se avisa de que la racha real puede superar la del modelo; no se aplica ningún factor inventado.
- **Frío:** sensación térmica por viento (JAG/TI, T ≤ 10 °C y viento > 4,8 km/h).

## No evaluado (se declara en la propia página)

Tormentas y rayos, niebla y visibilidad, **crecidas y cruces de cauces**, aludes y estado de la nieve en suelo. Faltan fuentes (CAPE, hidrología) y no se inventan indicadores.

## Límites conocidos

- Un solo modelo determinista, sin probabilidades; 3 h de resolución temporal: los chubascos breves se diluyen.
- Dominio de la rejilla: lat 42,30–42,65, lon 1,45–2,20 (Cerdanya, Capcir, Andorra y alrededores). El Pirineo central y oscense quedan fuera: se marcan como sin datos.
- Los factores de actividad (1,0 / 0,75 / 1,7 / 0,6) son orientativos, sin calibrar.
- Los cortes de nivel de lluvia y nieve se recuerdan de convenciones usuales, no se han contrastado con el glosario oficial.
- **La ampliación de la rejilla (2 variables más) no se ha ejecutado contra Open-Meteo**; solo con respuestas simuladas. Comprobar condiciones de uso de Open-Meteo si el sitio pasa a uso público intensivo.
- Solo GPX en el MVP.

## Siguientes fases

1. TCX/FIT y probabilidades por ensemble a lo largo de la ruta; ampliar la rejilla al Pirineo central/oscense.
2. Hidrología: cauces desde el DEM, cruces de cauces del track e indicador de lluvia acumulada aguas arriba (no es un aviso hidrológico).
3. Cuentas, rutas guardadas y enlaces compartidos (la fase con más implicaciones de privacidad).

## Verificación

`node tests/test_route_engine.cjs` (21 pruebas) · `python3 -m unittest tests.test_route_engine tests.test_route_grid_contract tests.test_route_page_browser`. El de navegador se omite sin Node, Playwright y Chrome.
