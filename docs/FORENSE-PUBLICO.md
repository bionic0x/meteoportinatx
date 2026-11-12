# Lecciones técnicas públicas de la DANA 17–20/10/2026

**Idioma / Language:** Español · [English](FORENSE-PUBLICO.en.md)

**Alcance:** estudio retrospectivo de un único episodio en Ibiza, con 3 días de lluvia, 11 estaciones de Meteoclimatic y productos Open-Meteo Previous Runs D0–D2. Las comparaciones derivan de los informes técnicos de la release de octubre de 2026. No son una climatología ni coeficientes calibrados.

## Modelo/observación de lluvia: D0 (0–24 h)

| Familia/modelo | Lluvia prevista / medida | Error medio |
|---|---:|---:|
| AROME HD | 0,65× | 22,8 mm |
| ICON-EU | 0,41× | 23,1 mm |
| ECMWF IFS 0,25° | 0,36× | 25,1 mm |
| ECMWF AIFS | 0,35× | 25,6 mm |
| NOAA AIGFS | 0,25× | 29,4 mm |

Hay desviación de amplitud y localización en lluvia convectiva anclada; las fuentes no deben ponderarse por sus éxitos en un único caso para pronósticos de nieve, frentes atlánticos o mar. El error de representatividad de una celda de modelo no equivale a sesgo instrumental. La validación debe congelar el *run* original y comparar observaciones dentro de la misma ventana horaria y la misma zona.

## Oleaje: corrección necesaria

Una comparación preliminar indicó diferencia de 2–2,5×, pero contrastaba el punto modelo frente a una bahía con boyas distantes. El contraste posterior en **puntos espacialmente coincidentes** dio cocientes modelo/boya entre **0,87 y 0,99** y RMSE entre 0,24 y 0,46 m para los modelos revisados. No se debe introducir un multiplicador universal ×2 para el oleaje; la orientación y la batimetría de cada sector requieren diagnóstico propio.

## Reglas derivadas

- El aviso oficial mantiene su autoridad y no se deriva del consenso de NWP.
- Un modelo, un radar sin verificación y una estación remota no constituyen por sí solos confirmación local independiente.
- No se recalibra una relación radar–lluvia Z–R con un único par significativo; comparar radar y pluviómetro en el mismo punto y hora.
- Las revisiones de un mismo episodio no deben contarse como *n* observaciones independientes; se puntúa por fecha/evento.
- La corrección aprendida aparece en el ámbito *forense experimental*; nunca altera por sí sola los avisos ni los umbrales operativos.
- Los datos y fuentes ausentes se informan como `UNKNOWN`, no como pronóstico de calma.

Los informes completos y el cuaderno de seguimiento original se conservan **fuera del repositorio público**, en el paquete local de la release de integración, porque contienen información contextual privada de un inmueble.
