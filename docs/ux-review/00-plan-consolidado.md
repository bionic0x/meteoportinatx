# Revisión integral UX/UI y diseño gráfico del Pirineo — plan consolidado

Método: cuatro revisores especialistas del catálogo `design/` de Ante-agency-agents, coordinados al estilo NEXUS (hallazgos con evidencia, marcados OBSERVADO o SUPUESTO, con severidad P0–P2). Esta consolidación es de lectura y no cambia código del producto.

| Informe | Hallazgos | P0 |
|---|---|---|
| [01 Arquitectura y flujos](01-arquitectura-y-flujos.md) | IA-01…16 | 3 |
| [02 UI y sistema visual](02-ui-sistema-visual.md) | UI-01…16 | 3 |
| [03 Identidad y gráfica](03-identidad-y-grafica.md) | GFX-01…20 | 2 |
| [04 Personas y accesibilidad](04-personas-y-accesibilidad.md) | PX-01…14, A11Y-01…13 | 3 |

Limitaciones comunes: solo había un ciclo de datos (noche de lluvia con avisos amarillos y uno naranja); no hay datos de usuarios reales (todo lo de comprensión es SUPUESTO); no se probó lector de pantalla real, dispositivo físico ni alto contraste forzado.

## Por qué «es un lío»

1. **La consola del Pirineo se rompe en móvil.** `src/pirineo_app.html` y `src/portinatx_app.html` no tienen `<!doctype>`, `<html lang>` ni `<meta name="viewport">` (verificado: las otras tres páginas sí). En un móvil se dibuja a 980 px, a escala del 40 %, en modo quirks, y las media queries no se activan. Lo señalan IA-01, UI-01 y A11Y-01.
2. **No hay una pantalla de respuesta.** La primera vista (Vigilancia) es un panel de metadatos con UNKNOWN. La vista orientada a decidir existe aparte (`/decidir/`) y no se enlaza con Rutas. Los avisos oficiales se repiten en cuatro sitios.
3. **Cuatro sistemas visuales distintos** y un color que significa cosas distintas (blanco = nieve, cima y 0 °C; amarillo = aviso y UNKNOWN; azul = lluvia y sello «ESTÁNDAR»).
4. **Estados de incertidumbre ilegibles:** observado, modelizado y UNKNOWN no se distinguen visualmente, y hay jerga cruda en inglés.

## Hallazgos P0 (por orden de ataque)

| Orden | ID | Hallazgo | Esfuerzo |
|---|---|---|---|
| 1 | IA-01 / UI-01 / A11Y-01 | Falta doctype, lang y viewport en las dos consolas | S |
| 2 | UI-02 | Con viewport corregido, 5 de 12 pestañas desbordan en horizontal a 390 px | M |
| 3 | UI-03 | Si falla la carga, «esperando datos…» eterno, sin error ni reintento | S |
| 4 | PX-03 | El estado «vigente» de los avisos queda fijado al emitir el ciclo: se muestra un aviso caducado y se omite uno ya iniciado (zona de Font-Romeu) | M |
| 5 | A11Y-02 | La subida de GPX no es accesible con teclado (input oculto, label no focalizable) | S |
| 6 | PX-02 | «Casa junto a torrente» alimenta datos de Portinatx (Ibiza); no hay perfil para un propietario pirenaico | M |
| 7 | IA-02 | Falta una pantalla de respuesta en la consola del Pirineo | L |
| 8 | IA-03 | Duplicación de avisos, puntos y modelo entre Decidir, Vigilancia y Ruta | M |
| 9 | GFX-01 | La capa «Relieve» pinta las cumbres blancas haya o no nieve | S |
| 10 | GFX-02 | El mapa de temperatura muestra celdas del modelo con aspecto de medición, sin aviso | S |

## Hallazgos P1 con más impacto

- **Seguridad de lectura (priorizar):** PX-04/PX-09, la tarjeta oficial no da organismo, zona ni nivel, y la nota «no es aviso oficial» queda al pie con jerga. IA-08, los avisos no se filtran por zona (avisos de Huesca para la Cerdanya).
- **Datos:** PX-01, «Nieve 24 h: UNKNOWN» en los 9 puntos porque no cae al siguiente modelo cuando uno devuelve null. PX-10, 3 de 5 perfiles muestran «Datos antiguos» (umbral de 60 min con publicación cada 6 h). PX-12, Decidir descarta observaciones de estaciones aunque `fuentes` las marca ok. GFX: «Inversión observada» sale vacía con 36 estaciones por un umbral de ≤90 min.
- **Navegación:** 12 pestañas planas (IA-04/05/10); «Satélite/radar» solo dice NOT_INTEGRATED; Atmósfera mide 5456 px. PX-11, Decidir no enlaza a Rutas.
- **Sistema visual:** 25 tamaños de fuente, radios de 2 a 18 px, 5 fondos distintos (UI-04); controles de la consola de menos de 44 px (UI-06); bordes de control a 1,35:1 de contraste (UI-09).
- **Marca:** el Pirineo es azul claro en el hub y verde azulado en la consola; Rutas usa `system-ui`; en Vigilancia un aviso naranja se ve igual que los amarillos.
- **Gráficos:** etiquetas solapadas en el corte vertical, la hodógrafa y el mapa de relieve; el eje X de «Cotas 72 h» se lee como día en vez de hora; 25 mini-gráficos con escalas propias.
- **Accesibilidad:** amarillo y naranja casi no se distinguen en deuteranopía (ΔE 11,5); lienzos de Rutas sin nombre ni teclado; objetivos táctiles de menos de 24 px; desbordamiento a 320 px en Decidir y Rutas; el hub no respeta `prefers-reduced-motion`.

## Contradicciones y huecos entre informes

- No hay contradicciones sustanciales. Los cuatro coinciden en las causas de fondo (viewport, duplicación, color sin semántica).
- **Dos matices que conviene decidir:** (a) los informes de UI y de gráfica proponen sistemas de tokens distintos (`--mp-*` frente a «Cresta y cota»); hay que unificarlos antes de implementar. (b) El informe de personas indica que el contraste de texto en general es correcto (≥ 6,3:1), mientras el de UI señala contrastes bajos en bordes y en los grises de Rutas: no se contradicen, afectan a elementos distintos.
- **No cubierto:** `forced-colors`, lectores de pantalla reales, gráficos de Rutas en detalle, estados de carga lenta, capas con nevada o inversión fuerte, y cualquier dato de usuarios reales.

## Orden de trabajo propuesto

1. **Semana 1 — Arreglos pequeños y de alto efecto (S):** doctype, lang y viewport; error de carga con reintento; teclado en la subida de GPX; capa «Relieve» sin cumbres blancas; aviso de modelo en el mapa de temperatura. Después, desbordes de las 5 pestañas (M).
2. **Semana 1–2 — Fiabilidad de lo que se muestra (M):** recalcular «vigente» en el cliente; filtrar avisos por zona; organismo, zona y nivel en la tarjeta oficial; caída al siguiente modelo para la nieve; perfil de propietario pirenaico; enlace de Decidir a Rutas.
3. **Semana 2 — Sistema:** `tokens.css` único (unificando las dos propuestas), cabecera común, 8 componentes, reglas de color (una semántica por color), cuatro «voces» gráficas para observado, modelizado, UNKNOWN y oficial.
4. **Después (L):** pantalla de respuesta «Hoy» por territorio, reducción de 12 pestañas, traducción ES/CA y glosario, rediseño de gráficos (corte, hodógrafa, Cotas 72 h, índices).

## Qué conservar

La separación en tres ejes (oficial, observado, estimado), la tarjeta de portal, semáforos con texto además de color, cifras mono tabulares, el mapa propio offline, la nota de privacidad de Rutas, y Decidir a 390 px sin desbordamiento.

## Siguiente paso

Cada fase se puede aplicar en un PR aparte. Se recomienda empezar por el punto 1, que es de bajo riesgo y resuelve el mayor «lío» en móvil.
