# Contrato de estado visual común: mapa 2D, relieve 3D, atmósfera y línea de tiempo (v0.1)

**Estado:** borrador, 28-11-2026. Lo exige el titular para el **gate G1** del rediseño (#77).
**Objetivo:** que el mapa 2D, el relieve 3D, el perfil atmosférico y la animación sean **vistas del mismo estado**
y no tres productos independientes (el problema de arquitectura que señala UI-00). Seleccionar Font-Romeu, las
18:00 y 700 hPa en el mapa debe conservar esa selección al pasar al relieve 3D o al perfil.
**No es implementación:** el equipo F implementa el almacén de estado tras G1. Los equipos C (2D), D (3D) y
E (movimiento) trabajan contra este contrato **desde el primer día**. Las aclaraciones van por PR y suben la versión.

## 1. Estado compartido

Hay una sola fuente de verdad, `EstadoVisual`. Cada vista lo lee y emite cambios; ninguna vista tiene una copia
propia de territorio, foco, hora, modelo, nivel o capas.

| Campo | Tipo | Significado | Reglas |
|---|---|---|---|
| `version` | texto | Versión del contrato (`0.1`) | Se rechaza un estado de otra versión mayor |
| `territorio` | `portinatx` \| `pirineo` | Dominio de datos | Cambiar de territorio reinicia foco, capas y corte; conserva la hora válida si existe en el nuevo dominio |
| `foco` | `{lon, lat, id?, nombre?, origen}` | Punto inspeccionado | `origen`: `punto_control` \| `clic` \| `busqueda`. Coordenadas WGS84. `id` solo si coincide con un punto del contrato (`core.pois`) |
| `corte` | `{a:{lon,lat}, b:{lon,lat}}` \| null | Transecto para el corte vertical | Compartido entre el corte 2D y el plano de corte 3D |
| `tiempo.valido_utc` | ISO 8601 UTC | **Hora válida** representada | Se muestra en la hora local del territorio, indicando la zona horaria |
| `tiempo.naturaleza` | ver §2 | Qué es lo que se ve a esa hora | Obligatoria; nunca se deduce del color |
| `modelo` | `{id, ejecucion_utc}` \| null | Modelo de los campos previstos | null en modo observado. La ejecución es visible siempre |
| `nivel` | `{tipo: superficie\|presion\|altura, valor, unidad}` | Nivel vertical | Ejemplo: `{presion, 700, hPa}`. El perfil marca ese nivel y el 3D muestra la superficie isobárica si la capa lo admite |
| `capas` | lista de `{id, visible, opacidad}` | Capas activas | Cada capa declara su naturaleza y su eje temporal (§3) |
| `generacion` | `{fuente: backend\|instantanea, snapshot}` | Generación de datos | Una sola generación por vista, según `src/public_fetch.js`; nunca se mezclan |
| `camara2d` | `{zoom, rumbo}` | Encuadre del mapa | Propio de la vista 2D; no altera el foco |
| `camara3d` | `{inclinacion, rumbo, exageracion}` | Encuadre 3D | La `exageracion` es **solo visual**: las cotas mostradas son siempre las reales (como en GEO-06) |
| `reproduccion` | `{estado: pausa\|reproduciendo, velocidad, bucle}` | Controlador de tiempo | Con movimiento reducido, arranca en pausa y no reproduce sola |
| `idioma` | `es` \| `en` | Idioma | — |
| `movimiento_reducido` | booleano | Preferencia del sistema o del usuario | Respeta `prefers-reduced-motion` |

**El estado no guarda la ruta GPX ni datos personales.** Si se serializa en la URL para enlazar, solo lleva
territorio, foco, corte, hora, modelo, nivel y capas. El GPX sigue siendo local y privado.

## 2. Naturaleza de lo que se ve (taxonomía obligatoria)

| Naturaleza | Origen | Ejemplo | Regla de presentación |
|---|---|---|---|
| `aviso_oficial` | AEMET, Meteocat, Météo-France, SMA | Aviso naranja de tormentas | Bloque separado; nunca se mezcla con el diagnóstico propio |
| `observado` | Estación, radar, satélite, rayos | `radar.frames`, `core.obs` | Hora de la observación y antigüedad visibles |
| `pronostico` | Salida de modelo a una hora válida | `grid.fields`, `series` | Modelo y ejecución visibles |
| `interpolado` | Fotogramas intermedios generados para el render | Transición entre dos horas de `grid.time` | Marcado como interpolación; **nunca entre observado y pronóstico** |
| `diagnostico` | Cálculo propio sobre pronóstico u observación | Cota efectiva, cubeta fría, föhn | Etiqueta «diagnóstico experimental» |
| `escenario` | Caso esquemático o sintético (GEO-07, fixtures) | Bloqueo frente a paso por encima | Etiqueta «escenario esquemático, no es previsión»; sin hora real |
| `desconocido` | Falta el dato o está caducado | Par de föhn sin estación | «Desconocido (UNKNOWN)»; **nunca se pinta como calma ni como cielo despejado** |

La naturaleza se distingue **por algo más que el color**: texto, trama o forma, sello o leyenda. El equipo B decide
la codificación, pero el contrato exige que sea legible en escala de grises y con lector de pantalla.

## 3. Capas y ejes temporales

Cada capa declara:
- `naturaleza` (§2);
- `eje` con las horas disponibles (`radar.frames[].t`, `grid.time`, `series.time`…);
- `paso` nominal;
- `fuente` y `edad`.

Reglas:
1. **Si la capa no tiene dato a la hora válida**, no salta en silencio a la hora más cercana. Muestra «sin dato a
   esta hora», la hora disponible más próxima y su distancia en minutos.
2. **La reproducción observada** solo recorre horas observadas. Un fotograma ausente se ve como hueco, no se
   rellena.
3. **La reproducción de pronóstico** recorre las horas válidas de una sola ejecución. Si cambia la ejecución, se
   avisa y no se empalma.
4. **La interpolación es solo de render**, entre dos horas del mismo modelo y la misma ejecución, y se marca
   `interpolado`.
5. **La transición observado → pronóstico** es un corte visible en la línea de tiempo (la hora de la última
   observación), no un fundido.
6. **La advección de ecos** (`src/radar_motion.py`) es una extrapolación diagnóstica: se etiqueta `diagnostico`, no
   `pronostico`.

## 4. Línea de tiempo y controlador

Un único control para todas las vistas, con:
- tramo observado y tramo de pronóstico diferenciados;
- marca de «ahora» y de la emisión del ciclo;
- huecos de datos visibles;
- reproducir/pausa, paso a paso, velocidad y bucle;
- teclado (← → por paso, espacio para pausa) y nombre accesible con la hora y la naturaleza.

Con movimiento reducido no hay reproducción automática ni transiciones animadas: los cambios son instantáneos.

## 5. Ejemplo (el del titular)

```json
{
  "version": "0.1",
  "territorio": "pirineo",
  "foco": {"lon": 2.0392, "lat": 42.5047, "id": "font_romeu", "nombre": "Font-Romeu", "origen": "punto_control"},
  "corte": null,
  "tiempo": {"valido_utc": "2026-11-29T17:00:00Z", "naturaleza": "pronostico"},
  "modelo": {"id": "meteofrance_arome_france_hd", "ejecucion_utc": "2026-11-29T06:00:00Z"},
  "nivel": {"tipo": "presion", "valor": 700, "unidad": "hPa"},
  "capas": [{"id": "viento_nivel", "visible": true, "opacidad": 0.8}, {"id": "relieve", "visible": true, "opacidad": 1}],
  "generacion": {"fuente": "instantanea", "snapshot": null},
  "camara2d": {"zoom": 10, "rumbo": 0},
  "camara3d": {"inclinacion": 60, "rumbo": 200, "exageracion": 1.5},
  "reproduccion": {"estado": "pausa", "velocidad": 1, "bucle": false},
  "idioma": "es",
  "movimiento_reducido": false
}
```

Las 18:00 locales de Font-Romeu en noviembre (CET, UTC+1) son las 17:00 UTC. Coordenadas y modelo
tomados de `core.pois` y `core.modelos` de la generación publicada del 28-11-2026.

## 6. Pruebas de aceptación para G1–G2

| ID | Prueba | Resultado esperado |
|---|---|---|
| CE-01 | Seleccionar Font-Romeu, 18:00 y 700 hPa en 2D y cambiar a 3D y a perfil | Mismo foco, hora válida y nivel en las tres vistas |
| CE-02 | Hora válida sin dato en una capa | «Sin dato a esta hora» con la hora más próxima; no hay salto silencioso |
| CE-03 | Reproducir radar con un fotograma ausente | Hueco visible; no se interpola |
| CE-04 | Pasar del tramo observado al de pronóstico | Corte visible; la etiqueta cambia de naturaleza |
| CE-05 | Cambiar de ejecución del modelo durante la reproducción | Aviso; no se empalman ejecuciones |
| CE-06 | Movimiento reducido activado | Sin reproducción automática ni animaciones |
| CE-07 | Exageración vertical 3D al 2× | Las cotas mostradas siguen siendo reales |
| CE-08 | Serializar el estado en un enlace | El enlace no contiene GPX ni datos personales |
| CE-09 | Fixture F2 (todo UNKNOWN) | Ninguna vista pinta calma; todas dicen «Desconocido (UNKNOWN)» |
| CE-10 | Fixture F7 (generaciones mezcladas) | La vista usa una sola generación e indica cuál |
| CE-11 | Escenario GEO-07 | Etiqueta «escenario esquemático, no es previsión», sin hora real |
| CE-12 | Lector de pantalla en la línea de tiempo | Anuncia hora, zona horaria y naturaleza |

## 7. Responsables

- **C (2D), D (3D) y E (movimiento):** consumen y emiten cambios del estado; ninguno define campos propios fuera
  de `camara2d` y `camara3d`.
- **F:** implementa el almacén y la serialización.
- **G:** verifica CE-01 a CE-12.
- Un cambio de campo o de regla es un PR a este documento; nunca un acuerdo bilateral entre dos equipos.
