# 03 · Identidad visual y diseño gráfico del Pirineo

Auditoría de MeteoPortinatx, foco Pirineo (Cerdanya, Capcir, Andorra). Perfiles aplicados: Brand Guardian (coherencia de marca, sistema visual, guardia de consistencia) y Visual Storyteller (narrativa visual, visualización de datos, divulgación progresiva, accesibilidad).
Fecha de la revisión: 2026-11-11. Solo lectura: no se ha tocado código.

**Método.** Lectura de `src/pirineo_app.html`, `src/pirineo_ruta.html`, `src/pirineo_observatory.js`, `src/pirineo_atmos.js`, `README.md`, `docs/PIRINEO-OBSERVATORIO-061.md`, contraste con `src/portinatx_app.html` y el hub. Capturas con Playwright (Chromium) a 1440 y 390 px sobre datos reales del ciclo 11/11/2026 22:54 (servidor `python3 -m http.server`), en `docs/ux-review/img/gfx-*-1440.png` y `gfx-*-390.png`.
Etiquetas: **OBSERVADO** = visto en captura o en el código; **SUPUESTO** = inferencia mía sin comprobar con usuarios.

---

## 1. Veredicto

**El Pirineo tiene un núcleo gráfico propio y muy bueno (el mapa de relieve con curvas, el corte vertical y las cotas a 72 h), pero la identidad está a medias y la capa de gráficos mezcla significados.** Hay tres problemas de fondo, y explican el «es un lío» del usuario:

1. **Un mismo color significa cosas distintas** según el gráfico (el azul `--std` es precipitación, bulbo húmedo, cizalladura y la etiqueta «ESTÁNDAR»; el amarillo es aviso, UNKNOWN y «DIAGNÓSTICO»; el blanco es nieve, cima y 0 °C).
2. **La marca paraguas no llega al Pirineo de forma coherente**: el hub lo pinta de azul claro, la consola de verde azulado, la página de ruta usa otra tipografía, y «Vigilancia» (la primera pestaña) ha perdido los píldoras de color que sí tiene Portinatx.
3. **Observado / modelizado / UNKNOWN se distingue en el texto, no en el gráfico.** La honestidad epistémica es excelente en las notas; en la visualización casi no hay lenguaje visual que la haga visible de un vistazo.

Lo que funciona (conservar): consola oscura «cartográfica», tipografía Saira Condensed + Public Sans + IBM Plex Mono, curvas de nivel doradas, el patrón de líneas isocero / Tw0 / copo (naranja discontinua / azul hielo continua / blanca punteada), la sombra de relieve, el rechazo explícito a dibujar fronteras inventadas, y las leyendas que acompañan cada capa.

---

## 2. Identidad y coherencia con la marca paraguas («dos territorios, una mirada»)

Lo que dice la marca (README, hub): «Dos territorios. Un mismo motor de análisis.» y «Del Mediterráneo al Pirineo».

| Elemento | Portinatx | Pirineo (consola) | Hub / otras páginas | Lectura |
|---|---|---|---|---|
| Acento de dominio | coral `#ff7a4a` | verde azulado `#5fd0c4` (`--accent`) | hub: Portinatx coral, **Pirineo azul claro `#7cc6ff`** | Pirineo tiene dos colores de marca (OBSERVADO) |
| Tipografía | Saira Condensed / Public Sans / Plex Mono | igual | hub: grotesca tipo Inter, sin Saira; **ruta: `system-ui`** | La familia se pierde en 2 de 4 superficies (OBSERVADO) |
| Estructura de portada | 3 ejes con borde superior de color + píldoras (`.axis`, `.lv-*`) | 3 ejes como casillas `.kv` planas; avisos en texto | — | El «lenguaje de nivel» de Portinatx no existe en Vigilancia del Pirineo (OBSERVADO) |
| Fondo | `#0c171c` azul-petróleo | `#0d1417` casi negro verdoso | — | Dos negros distintos; el paso de uno a otro se nota (OBSERVADO, tokens) |
| Elemento propio | radar, mar | relieve, cotas, perfil | — | Cada territorio ya trae su «objeto gráfico firma» |

**Idea de dirección:** la marca paraguas = *estructura compartida* (tipografía, rejilla, sistema de nivel de riesgo, forma de marcar observado/modelizado/UNKNOWN); cada territorio = *acento + objeto firma*. Portinatx: coral + radar sobre costa. Pirineo: verde azulado glaciar + relieve con curvas y cota de nieve. Hoy lo compartido se rompe en Pirineo (ver GFX-04, GFX-05) y el acento está duplicado (GFX-03).

**Emojis e iconografía.** La consola casi no usa iconos: el único emoji en la interfaz es ❄ en el corte vertical y ⚠ en «capa cálida»; el chat usa 🟢🟡🟠🔴 en las reglas. El README usa 🌊 y 🏔️ para los dos territorios, pero no existen en la app. Positivo (tono sobrio, técnico). Negativo: no hay ningún símbolo de marca para el Pirineo (ni una «silueta de cresta», ni un glifo de cota); los marcadores del mapa (▲ cima, ● pueblo, ● collado) son lo único parecido a un sistema icónico, y se redibujan a mano en tres sitios (mapa, corte, leyendas). Un conjunto mínimo de 6 glifos SVG cubriría todo (GFX-13).

**Tono visual.** Científico-cartográfico, sobrio, denso. Coherente con el tono verbal (UNKNOWN, «no es un aviso oficial»). Riesgo: demasiado denso para los usuarios «esquí y montaña» que el hub dice atender; la pestaña Atmósfera mide 5 500 px de alto a 1440 (OBSERVADO, `gfx-atmosfera-1440.png`).

---

## 3. Hallazgos

Severidad: **P0** engaña o puede llevar a una lectura errónea con consecuencias; **P1** confunde o rompe la coherencia de forma visible; **P2** pulido. Esfuerzo: S (horas), M (1–3 días), L (semana o más).

### GFX-01 · P0 · El blanco significa nieve, cima, 0 °C y roca alta a la vez
- **Evidencia (OBSERVADO).** `HYPSO` termina en `[232,232,228]` a 3000 m y `[196,196,192]` a 2800 m: los macizos de la capa «Relieve» salen blancos (`gfx-mapa-relieve-1440.png`) aunque **no haya nieve en el modelo** (cota de copo 2527 m: sí habría nieve en las cumbres, pero el mismo blanco se pinta aunque la cota fuera 3500 m). En la capa «Cota de nieve» la nieve se mezcla con el mismo gris-blanco (`col*(1-f)+242*f`) y el resultado apenas se distingue del relieve base (`gfx-mapa-cota-1440.png`: manchas blanco-grisáceas rodeadas de línea punteada). En «Temperatura», 0 °C se pinta blanco (`RAMP_T [0,[230,240,250]]`), y en «Precipitación» el blanco (`[245,248,250]`) = «nieve probable» (`gfx-mapa-prec-1440.png`). El triángulo de cima también es blanco.
- **Por qué importa.** Un lector que alterna capas ve «blanco» en cumbres en todas y concluye que hay nieve en todas. La capa Relieve afirma, sin querer, una nevada permanente.
- **Recomendación.** Reservar el blanco-azulado (`#eaf6ff`) **solo** para nieve modelizada. Terminar la rampa hipsométrica en roca cálida (`#b9ae9c` → `#d6cdbd`), sin blanco. Dibujar la nieve con una textura (puntos) o un borde azul hielo además del relleno, para que se lea sin depender del tono. Cima en marfil `#f3e9d2` con contorno oscuro.
- **Esfuerzo:** S–M. **OBSERVADO.**

### GFX-02 · P0 · Mapa de temperatura con celdas rectangulares visibles y sin aviso de que es un modelo suavizado
- **Evidencia (OBSERVADO).** `gfx-mapa-temp-1440.png`: parches rectangulares de color (la malla 0,05° de AROME HD) con una corrección de −6,5 °C/km encima. La nota lo explica («no ve las inversiones de fondo de valle»), pero la imagen parece medida: valle amarillo-naranja (9–10 °C) rodeado de verdes, sin marca de incertidumbre. Los fondos de valle de la Cerdanya en una noche de inversión están en realidad más fríos.
- **Por qué importa.** Es justo la capa donde el modelo es más débil (inversiones) y se presenta con la mayor apariencia de precisión.
- **Recomendación.** (a) Suavizar o difuminar el borde de celda para que no parezca estación; (b) trama diagonal tenue sobre fondos de valle (< 1 500 m) mientras la inversión observada no se haya verificado, con leyenda «el modelo no ve esta zona»; (c) superponer los puntos de estaciones **observadas** con relleno sólido del color de su lectura, de modo que la discrepancia modelo-observación salte a la vista (ahora los puntos llevan texto, no color).
- **Esfuerzo:** M. **OBSERVADO.**

### GFX-03 · P1 · Dos azules / dos verdes azulados: el acento del Pirineo no es único
- **Evidencia (OBSERVADO).** Consola: `--accent:#5fd0c4` (verde azulado). Hub: tarjeta «Pirineo Nowcast» en `#7cc6ff`-like (`gfx-hub-1440.png`). En la consola, `--ice:#7cc6ff` se usa también para el foco, los enlaces, el collado, Tw0 y el botón «Ruta y tiempo». El «azul Pirineo» del hub es, en realidad, el color de *enlace* de la consola.
- **Recomendación.** Fijar **un** color de dominio por territorio (propuesta: Pirineo `#5fd0c4`) y usarlo en el hub, cabeceras y marcadores de vista activa. Liberar el azul hielo para datos térmicos (Tw0) y no para enlaces.
- **Esfuerzo:** S. **OBSERVADO.**

### GFX-04 · P1 · Vigilancia (primera pestaña) rompe el lenguaje de nivel de riesgo
- **Evidencia (OBSERVADO).** `gfx-vigilancia-1440.png`: avisos como texto plano «amarillo · Aviso de lluvias…» sin píldora ni color, mientras Superficie (`p-amarillo`, `p-naranja`) y Portinatx sí tienen píldoras. Hay un aviso **naranja** (Pirineo oscense) que en Vigilancia se ve idéntico a los amarillos. Las tres «ejes» son casillas grises sin borde de color ni icono de estado. «FUENTE OFICIAL DISPONIBLE» en verde es el único color de la pantalla.
- **Causa.** `pirineo_observatory.js` genera HTML con `<b>` y no usa las clases `.pill p-*` de la app.
- **Recomendación.** Reutilizar `.pill p-{nivel}` y el patrón `.axis` de Portinatx (borde superior de 5 px con color de nivel). El naranja debe distinguirse a primera vista.
- **Esfuerzo:** S. **OBSERVADO.**

### GFX-05 · P1 · Los píldoras de nivel de aviso y el color de «UNKNOWN» chocan
- **Evidencia (OBSERVADO).** Pirineo define UNKNOWN con el **amarillo** `--w` (`.pov-unknown{border-left:3px solid var(--w)}`, `.pov-unk{color:var(--w)}`). Portinatx tiene un token propio `--unk:#8a9aa1` (gris) con `.lv-unknown`. En el Pirineo, «sin datos» y «aviso amarillo oficial» comparten color: la jerarquía de la marca («un dato ausente no es calma», pero tampoco es un aviso) se pierde. En la pestaña Satélite/radar, el bloque «NOT_INTEGRATED» también va en amarillo.
- **Recomendación.** Importar a Pirineo `--unk`, `--q-bg…--unk-bg` y las clases `.lv-*`. UNKNOWN = gris frío con **trama diagonal** (ya existe en la ruta: `.lu` `repeating-linear-gradient(45deg,#4d5b5d,#34403f)`), nunca amarillo.
- **Esfuerzo:** S. **OBSERVADO.**

### GFX-06 · P1 · El azul `--std` y el amarillo `--diag` cargan dos significados cada uno
- **Evidencia (OBSERVADO).** `--std:#62b0ff` = chip «ESTÁNDAR», barras de precipitación del gráfico de cotas, línea Tw del perfil T/Td/Tw, cizalladura. `--diag:#e8be33` = chip «DIAGNÓSTICO» y amarillo de aviso. `--exp:#c58cff` = chip «EXPERIMENTAL» y tope de la rampa de rachas (`RAMP_G` 100–130 km/h) y nivel 4 de la ruta (`--c4`). `--fz:#ff9a4d` = isocero y θe y capa cálida y «hace calor»; `--x` rojo = temperatura en el perfil T/Td/Tw **y** aviso rojo.
- **Por qué importa.** El rojo de la línea de temperatura (T) en el perfil atmosférico se lee como alarma; el rojo debe quedar reservado a aviso oficial rojo.
- **Recomendación.** Tabla de roles de color (§5). Los sellos de validación (ESTÁNDAR / DIAGNÓSTICO / EXPERIMENTAL) deben ser **neutros con forma** (borde sólido / punteado / doble) y no consumir tonos de datos.
- **Esfuerzo:** M. **OBSERVADO.**

### GFX-07 · P1 · Corte vertical: etiquetas rotadas que se pisan y ejes que desperdician el 40 % del lienzo
- **Evidencia (OBSERVADO).** `gfx-corte-1440.png`: nombres rotados −28° con temperatura y «lluvia» se solapan (Canillo / Encamp / Soldeu / Pas de la Casa / Port d'Envalira / Grau Roig; «… · lluviaTossa d'Alp» pegados). El eje Y llega a 4 000 m (`zmax=4000`) cuando el relieve no pasa de 2 900 m: el tercio superior está vacío salvo las líneas de cota. A 390 px el SVG (viewBox 900) se escala a ×0,43: **texto de ≈ 4,7 px**, ilegible (`gfx-corte-390.png`).
- **Además.** «lluvia» en todos los puntos con T 2–11 °C y cota de copo a 2 527 m es correcto, pero la repetición de la misma palabra 13 veces es ruido: mejor un icono o un tono en el punto.
- **Recomendación.** Reducir `zmax` a `max(DEM)+300`; etiquetas horizontales con algoritmo anti-solape (o solo cimas/collados nombrados + tooltip); en móvil, SVG con `viewBox` propio de 360×300 y fuente ≥ 11 px efectivos, o gráfico a ancho 2× con desplazamiento horizontal.
- **Esfuerzo:** M. **OBSERVADO.**

### GFX-08 · P1 · Gráfico «Cotas 72 h»: etiquetas de eje ambiguas y precipitación sin escala
- **Evidencia (OBSERVADO).** El eje X dice «jue, 01 · jue, 13 · vie, 01 …» (día de la semana + hora, `fmtT(...{weekday,hour})`): se lee «jueves 1, jueves 13», no «jueves a la 01:00». Las barras de precipitación (`pm=max…·40 px`) están normalizadas al máximo de la serie y se dibujan **sobre el eje de altitud** (las barras se solapan con los 1 000 m), sin escala ni unidad. La línea vertical de la hora elegida (verde azulado, 1,2 px) cae pegada al borde del eje y casi no se ve. Las etiquetas de la derecha («Puigmal 2892 … La Molina 1682») se separan a mano (`lastY-ly<12`) y quedan desalineadas con su línea punteada.
- **Recomendación.** Eje: «jue 00h · jue 12h»; panel de precipitación **debajo**, con su propio eje en mm/h; marcar la hora elegida con triángulo en el eje; leyenda con la franja «copo → acumulación fiable» (ya existe pero en gris casi invisible).
- **Esfuerzo:** S–M. **OBSERVADO.**

### GFX-09 · P1 · Perfil T / Td / Tw: tres líneas superpuestas que parecen una, sin skew-T ni diferenciación de saturación
- **Evidencia (OBSERVADO).** `gfx-atmosfera-1440.png` (zona superior): con humedad ≈ 100 % las tres curvas coinciden y se ve una única diagonal con puntos de tres colores apilados. Los niveles 1000 y 925 hPa están bajo el terreno (UNKNOWN) y la parte baja del gráfico queda vacía sin explicar visualmente por qué. El eje X pasa de −40 a +20 °C con rejilla de 10 °C.
- **Qué falta.** Rotación skew-T (que haría legible la estabilidad), línea de 0 °C marcada, sombreado de la capa por debajo del terreno, y la altitud real (m) además de hPa.
- **Recomendación.** Marcar la isoterma 0 °C como línea vertical azul hielo, sombrear «bajo el terreno» con la textura de UNKNOWN, escalonar los puntos si Td≈T (ahorra confusión), y añadir eje derecho con altitud estándar. Skew-T solo si el público lo pide (SUPUESTO).
- **Esfuerzo:** M. **OBSERVADO.**

### GFX-10 · P1 · Hodógrafa sin norte, sin graduación de altura y con etiquetas que se solapan en el origen
- **Evidencia (OBSERVADO).** `pirineo_atmos.js` `hodo()`: línea y puntos de un solo color (`--accent`), etiquetas «10 m», «1000», «925»… colapsadas en el centro (en la captura «1000», «925» y «850» se montan). No hay anillos con la unidad en el borde (solo números «10 20 30 40» pegados al eje), ni marca N/S/E/O, ni gradiente de color por altitud. La nota «vector hacia donde sopla» es correcta, pero el convenio meteorológico habitual de dirección es «desde donde sopla», y los dos convenios conviven (tabla: «dirección desde °»; gráfico: «hacia donde sopla»).
- **Recomendación.** Color por altura (rampa secuencial de 6 pasos), ocultar etiquetas de niveles bajo terreno, marcas N-E-S-O en los anillos, y una única convención con la palabra «desde» en ambos.
- **Esfuerzo:** S–M. **OBSERVADO.**

### GFX-11 · P1 · 25 mini-gráficos de índices con escala propia: el ruido parece señal
- **Evidencia (OBSERVADO).** `evolution()`: cada tarjeta normaliza la serie a su mínimo/máximo (`y=30-(v-lo)/(hi-lo)*26`). CAPE «0,0 J/kg» muestra una montaña de picos grandes porque el máximo de la serie es unos pocos J/kg; «Velocidad vertical 700 −0,1 m/s» sube y baja a pantalla completa. Sin eje, sin unidad en la serie, sin referencia a un umbral. Resultado: una pared de 25 gráficos de aspecto igual y peso visual igual, de los que ≥ 6 son «UNKNOWN».
- **Por qué importa.** Un CAPE de 0 J/kg con la misma amplitud visual que un CAPE de 1 500 es engañoso (y es justo la clase de ilusión que el proyecto dice evitar).
- **Recomendación.** Escala mínima común por tipo de índice (p. ej. CAPE 0–1 000 fijo) o, si la serie es casi plana, línea recta gris con la etiqueta «sin variación»; plegar por defecto en un `<details>` con los 5–6 índices relevantes arriba (CAPE, CIN, Froude, Tw0, shear 0–6, agua precipitable). Las tarjetas UNKNOWN deben ser una sola fila compacta.
- **Esfuerzo:** M. **OBSERVADO.**

### GFX-12 · P1 · Inversión observada: el gráfico firma del Pirineo está vacío justo cuando hay 36 estaciones
- **Evidencia (OBSERVADO).** `gfx-diagnostico-1440.png`: el recuadro «Inversión observada» dice «Menos de dos estaciones frescas» y deja una columna entera en blanco, junto a una tabla con 36 filas de observaciones. El filtro es `liveAge ≤ 90 min` y el ciclo ya tenía 109 min. Es el gráfico que distingue el Pirineo (inversión de fondo de valle en la Cerdanya) y aparece **vacío por un umbral de frescura**, sin mostrar las estaciones «viejas» atenuadas.
- **Recomendación.** Dibujar siempre las estaciones disponibles; las de > 90 min en gris con trama («antigua»), las frescas en color sólido. Añadir la línea de referencia −6,5 °C/km (en el código existe pero con `opacity="0"`: está oculta). Reducir el hueco vertical cuando falta (estado vacío compacto).
- **Esfuerzo:** S–M. **OBSERVADO.**

### GFX-13 · P2 · Los marcadores y la simbología se dibujan por tres caminos distintos
- **Evidencia (OBSERVADO).** Mapa: ▲ blanco, ● verde azulado, ● azul (canvas). Corte: círculo blanco + vástago + texto rotado (SVG). Leyenda: caracteres Unicode «▲ ●» + `<span style="color:var(--ice)">●</span>`. Observación en tabla: sin icono, solo la columna «Red».
- **Recomendación.** Sprite SVG de 6 glifos (cima, collado, pueblo/estación, estación observada oficial, estación no oficial, punto de control) con la misma forma en mapa, corte, leyenda y tabla. La **forma** debe distinguir oficial / no oficial (hoy solo texto).
- **Esfuerzo:** M. **OBSERVADO.**

### GFX-14 · P1 · Observado vs modelizado: se explica en notas, no se ve
- **Evidencia (OBSERVADO).** Las notas lo dicen bien («Modelo, no observación», «Perfil ARPEGE… no es un sondeo observado»). Pero visualmente: (a) en el mapa los puntos de pueblos y estaciones usan el mismo marcador sea cual sea la red (AEMET oficial, Meteociel secundaria, Meteoclimatic aficionada); (b) la tabla «Observación» mezcla 36 filas con la red solo en una columna gris minúscula `.ev` (`.75rem`); (c) en el corte, la «T» de cada punto sale del modelo pero se pinta como la etiqueta de una estación; (d) los sellos ESTÁNDAR/DIAGNÓSTICO/EXPERIMENTAL aparecen en 4 de 12 pestañas.
- **Recomendación — gramática de procedencia (cuatro estados, uniforme en todos los gráficos):**
  1. **Observado oficial**: marcador relleno, trazo continuo, color pleno.
  2. **Observado no oficial**: marcador relleno con anillo discontinuo, mismo color con 70 % de opacidad.
  3. **Modelizado**: línea discontinua fina o área con trama ligera; marcador hueco.
  4. **UNKNOWN**: trama diagonal gris, nunca 0 ni hueco en blanco.
  Poner la misma mini-leyenda de 4 símbolos en la cabecera de la consola.
- **Esfuerzo:** M–L. **OBSERVADO** el problema; la gramática es **SUPUESTO** (hay que probarla con usuarios).

### GFX-15 · P1 · Ensemble 15 días es una tabla de porcentajes sin forma gráfica; el 0 % y el «sin datos» se parecen
- **Evidencia (OBSERVADO).** `gfx-extendido-1440.png`: 15 filas de «0 %» para nieve ≥5 cm en Masella, con una única columna que varía (Tw ≤ 0 °C 0 % → 68 %). No hay barra, calor ni sparkline. «0 %» es una fracción de miembros (correcto) y el texto avisa de que **no es probabilidad calibrada**, pero visualmente un 0 % de una fracción de 3 familias y «UNKNOWN» no se distinguen. Mezcla de idiomas: «Ensemble member fractions, NOT locally calibrated probabilities…», «multi-family», «UNCONFIRMED». «Pesos por familias institucionales» vuelca JSON crudo con 16 decimales (`{"dwd":0.3333333333333333,…}`).
- **Recomendación.** Rejilla de 15 días × 3 métricas con celdas de color secuencial (fracción), borde punteado si `n_families < 3` y trama si UNKNOWN; mostrar «3 de 3 familias» como puntos (●●●). Traducir las etiquetas y formatear los pesos (33 % / 33 % / 33 %).
- **Esfuerzo:** M. **OBSERVADO.**

### GFX-16 · P1 · Mapa de precipitación: saturación total y fusión con nieve
- **Evidencia (OBSERVADO).** `gfx-mapa-prec-1440.png`: toda la ventana es azul intenso (0,2–3 mm/3 h) salvo un parche sin datos marrón arriba a la derecha (borde circular visible = fin de la malla, sin leyenda de «sin cobertura») y manchas amarillas de 6 mm en esquinas. La rampa va azul → **amarillo → naranja → rojo** (colores de aviso para cantidades de lluvia). Los 0,2 mm/3 h y los 3 mm/3 h son dos azules apenas distintos. La nieve probable (blanco) se ve como roca nevada, no como precipitación nevando.
- **Recomendación.** Rampa de un solo tono (azul claro → azul profundo → violeta), sin amarillos/rojos (reservados a avisos). Umbral visible: por debajo de 0,5 mm/3 h, transparente. Nieve en cian-hielo con trama. Rotular el parche sin datos como UNKNOWN (trama), no como relieve base.
- **Esfuerzo:** S–M. **OBSERVADO.**

### GFX-17 · P1 · Móvil: los gráficos SVG se encogen y quedan ilegibles
- **Evidencia (OBSERVADO).** A 390 px, corte y cotas se muestran enteros pero con texto ≈ 4–5 px (`gfx-corte-390.png`); las capas del mapa y el slider de hora funcionan, pero el mapa usa la misma relación 1,512:1 (horizontal) en una pantalla vertical, sin zoom táctil (`touch-action:manipulation`). La barra de pestañas se desplaza horizontalmente, y en «Corte» se ven tres pestañas de doce (OBSERVADO en la captura).
- **Recomendación.** Para móvil: SVG con `viewBox` adaptado, fuente mínima 11 px efectivos; mapa con pellizco/zoom o formato vertical; un «resumen de la cota» en tarjeta (isocero, Tw0, copo + una frase) por encima del gráfico, y el gráfico como detalle.
- **Esfuerzo:** M. **OBSERVADO.**

### GFX-18 · P2 · La página de ruta parece de otra marca
- **Evidencia (OBSERVADO).** `gfx-ruta-1440.png`: tipografía `system-ui` (sin Saira), avisos en lista de viñetas sin píldoras («amarillo · Moderate thunderstorm warning · MeteoAlarm» en inglés dentro de una UI en español), pills `.l0–.l4` con texto oscuro sobre color pleno y trama `lu` para «sin datos» (buen patrón, pero solo aquí). Sin mapa hasta subir un GPX: el estado vacío es un formulario, no una invitación gráfica. El comentario del código justifica la ausencia de fuentes y mapas externos (privacidad), decisión correcta, pero no obliga a abandonar la identidad: se pueden usar fuentes del sistema que se acerquen a Saira y el mismo conjunto de tokens.
- **Recomendación.** Extraer los tokens a un solo `pirineo.css` compartido (sin red externa: servirlo local) y reutilizar `.pill`, `.axis`, la trama UNKNOWN; estado vacío con la silueta del relieve (DEM ya cargado) y una ruta de demostración dibujada.
- **Esfuerzo:** M. **OBSERVADO.**

### GFX-19 · P2 · «Vigilancia»: los pares etiqueta-valor se pegan («Racha prevista27 km/h»)
- **Evidencia (OBSERVADO).** `gfx-vigilancia-1440.png`: el bloque `.pov-mini` no tiene `.kv`, de modo que `span` y `b` se escriben seguidos («Cota copo2619 m», «Nieve modelo (3 h)UNKNOWN»). Es un fallo de CSS (`.pov-mini .kv{margin-top:0}` presupone un `.kv` que `grid()` no añade en esa llamada).
- **Esfuerzo:** S. **OBSERVADO.**

### GFX-20 · P2 · Accesibilidad de los gráficos
- **Evidencia (OBSERVADO).** Los SVG llevan `role="img"` y `aria-label` y las tablas dan los valores (bien); el canvas del mapa tiene `aria-label` pero la información de capa no está en texto. El mapa y la hodógrafa dependen de matiz (verde/rojo, azul/naranja) para separar series; el campo «Hora» no anuncia unidades. Las curvas de nivel doradas de 0,6 px a 45 % de opacidad quedan por debajo del contraste útil sobre tintas oliva. La rampa de temperatura (azul → blanco → verde → amarillo → naranja → rojo) no es segura para daltonismo rojo-verde (verde 5 °C vs amarillo 12 °C vs naranja 20 °C).
- **Recomendación.** Rampa divergente apta para daltonismo (§5), resumen textual de la capa («Isocero 2 876 m; el 18 % del área por encima de la cota de copo»), y un patrón además del color para las capas de riesgo.
- **Esfuerzo:** M. **OBSERVADO.**

---

## 4. Narrativa visual de las pistas de incertidumbre

El texto del Pirineo es excepcional (UNKNOWN en lugar de 0, «no es un aviso oficial», «fracciones de miembros, no probabilidades»). La narrativa visual no lo es:

- **Arco narrativo ausente.** Se entra por «Vigilancia» (tres casillas grises y una lista), se salta a doce pestañas con igual peso. No hay un «titular gráfico» del tipo «hoy la cota de nieve está a 2 530 m y baja a 2 100 m el viernes» con un mini corte que lo ilustre. El gráfico de más valor (Corte y cotas) está en la 5.ª pestaña.
- **La incertidumbre no tiene forma.** Un único carril de color para «lo que sé», y texto para «lo que no sé». Propuesta: tres «voces» visibles en todas las vistas (observado = sólido, modelo = discontinuo, UNKNOWN = trama) y un marcador de **edad** (anillo que se vacía con los minutos) en cada estación y cada ciclo.
- **La cota tiene una banda, pero no un rango.** El corte dibuja «entre copo y acumulación fiable» como una banda gris; la nota del mapa dice «con precipitación intensa puede bajar 200–400 m más». Esa franja de 200–400 m es incertidumbre real y debería dibujarse como degradado hacia abajo, no como texto.
- **Pistas de UNKNOWN invisibles.** En Atmósfera, niveles 1000/925 UNKNOWN se resuelven con la palabra «UNKNOWN» en celdas de tabla; en el gráfico simplemente faltan. Con una zona sombreada «bajo el terreno» y otra «sin dato» se cuenta la historia.
- **Resumen para el usuario «esquí y montaña».** (SUPUESTO) Su pregunta real es «¿dónde está la nieve y qué viento hay en el collado?»: hoy se responde con 4 pestañas y 7 gráficos; podría ser un único gráfico de cota + viento en collados con ventana de 72 h.

---

## 5. Propuesta de dirección visual del Pirineo

**Idea:** *«Cresta y cota»* — el Pirineo se dibuja con líneas de nivel y una cota que sube y baja; el color es glaciar (verde azulado), la roca es cálida, el riesgo y la incertidumbre nunca compiten con el dato. Comparte con Portinatx la estructura y el lenguaje de nivel; difiere en acento y objeto firma.

### 5.1 Paleta (hex)

| Rol | Token | Hex | Uso y regla |
|---|---|---|---|
| Fondo | `--bg` | `#0d1417` | Lo mantiene. Unificar con Portinatx en `#0c171c` o viceversa (decisión de marca; ver GFX-03) |
| Panel | `--panel` / `--panel2` | `#141e22` / `#10181c` | Igual |
| Tinta / apagado / línea | `--ink` `--muted` `--line` | `#e4ebe9` / `#8fa19f` / `#26363b` | Igual (contraste ≥ 6:1 sobre panel, OBSERVADO por cálculo) |
| **Acento Pirineo** | `--accent` | `#5fd0c4` | Cabeceras, pestaña activa, hodógrafa, marca. **Único color de marca** del dominio |
| Curvas de nivel | `--contour` / `--contour-i` | `#b08a5c` / `#d9b07a` | Solo relieve y altitud de referencia |
| Roca / relieve alto | `--rock` | `#b9ae9c` → `#d6cdbd` | Final de la rampa hipsométrica; **nunca blanco** |
| **Nieve** | `--snow` | `#eaf6ff` + borde `#7cc6ff` | Solo nieve modelizada o nieve en suelo. Con trama de puntos |
| **Lluvia** | `--rain` | `#4f8cff` (claro `#9cc0ff`, profundo `#2a56c8`) | Precipitación líquida. Rampa de un solo tono |
| **Cero térmico** | `--fz` | `#ff9a4d` | Isocero (línea discontinua larga) |
| Bulbo húmedo 0 °C | `--wb` | `#7cc6ff` | Tw 0 °C (línea continua) |
| **Viento / racha** | `--wind` | `#8f9bff` → `#c58cff` | Rampa secuencial índigo → magenta; sin amarillos |
| Frío ↔ calor (divergente) | `--cold` `--mid` `--warm` | `#5b7cff` / `#dfe7ea` / `#ff9a4d` | Rampa de temperatura: sin verde en medio; 0 °C = gris perla, no blanco |
| Riesgo oficial | `--q` `--w` `--a` `--x` | `#4cc184` / `#e8be33` / `#ff9447` / `#ff5f5f` | **Solo** niveles de aviso/alerta. Prohibido para datos |
| **UNKNOWN** | `--unk` | `#8a9aa1` + trama 45° `#4d5b5d / #34403f` | Siempre trama, nunca 0, nunca amarillo |
| Sello de validación | — | neutro (`--muted`) con borde distinto | ESTÁNDAR sólido · DIAGNÓSTICO punteado · EXPERIMENTAL doble; sin color de dato |

### 5.2 Tipografía

| Uso | Familia | Peso / tamaño | Nota |
|---|---|---|---|
| Marca, títulos, pestañas, etiquetas de eje en mayúsculas | Saira Condensed | 600 · 1,7 rem (h1), 1,1 rem (h2), `letter-spacing .06–.08em` | Ya en uso; extender a hub y ruta |
| Cuerpo y notas | Public Sans | 400–600 · 14 px / 1,45 | Igual |
| Números, ejes, sondeos, sondas del mapa | IBM Plex Mono | 400–500 · `tabular-nums` | Igual; mínimo 11 px efectivos en móvil |
| Fallback sin red (ruta) | `"Arial Narrow", system-ui` | — | Mantiene el aire condensado sin pedir fuentes externas |

### 5.3 Reglas de gráficos (resumen ejecutable)

1. **Un color = un significado** en todo el Pirineo (tabla 5.4). Riesgo oficial nunca se usa para datos.
2. **Cuatro voces de procedencia**: observado oficial (sólido) · observado no oficial (sólido, anillo discontinuo) · modelizado (discontinuo, marcador hueco) · UNKNOWN (trama). Misma mini-leyenda de 4 símbolos en la cabecera.
3. **Ejes**: altitud siempre en metros a la izquierda (también en perfiles de presión, con hPa como segundo eje); tiempo «jue 00 h»; unidades en el eje, no solo en la nota. Rango de ejes ajustado a los datos (no 4 000 m si el relieve llega a 2 900).
4. **Escala común** para series comparables; nunca autoescalar un índice a pantalla completa sin eje (GFX-11).
5. **Nieve** siempre con relleno claro + trama + borde; **no** blanco puro.
6. **Cota**: tres líneas fijas (isocero naranja largo-corto, Tw0 azul hielo continua, copo blanco punteada) + banda difusa «puede bajar 200–400 m» en degradado. Siempre con halo oscuro (1 px) para legibilidad.
7. **Mapas**: sin frontera inventada (se mantiene); curvas cada 100 m, gruesa cada 500 m (se mantiene); zonas sin datos en trama; estaciones observadas con color de lectura.
8. **Rampas**: temperatura divergente apta para daltonismo; lluvia mono-tono; viento índigo→magenta; sin rojo ni amarillo.
9. **Etiquetas**: sin rotación; solape resuelto; cada texto ≥ 11 px efectivos a 390 px.
10. **Texto alternativo**: cada gráfico acompaña con una línea resumen en lenguaje llano.
11. **Idioma**: todas las etiquetas visibles en español (sin «multi-family», «UNCONFIRMED» ni «Moderate thunderstorm warning» sin traducir o sin marcar como cita).

### 5.4 Hoja de estilo (tabla única)

| Elemento | Forma | Color | Línea / relleno | Texto | Cuándo / no usar |
|---|---|---|---|---|---|
| Isocero | línea | `#ff9a4d` | 2 px, guiones 6-4 | «isocero 2 876 m» | Perfil modelizado; no sobre fondo naranja |
| Tw 0 °C | línea | `#7cc6ff` | 2 px continua | «Tw 0 °C» | Modelizado |
| Cota de copo | línea | `#eaf6ff` | 2 px punteada 2-3 + halo | «copo 2 527 m» | Modelizado |
| Banda copo→acumulación | área | `#eaf6ff` 12 % | trama de puntos | leyenda | Incertidumbre explícita |
| Cota «puede bajar 200–400 m» | degradado | `#eaf6ff` 0–10 % | bajo la línea de copo | nota breve | Cuando hay precipitación intensa |
| Relieve hipsométrico | tinte | verde oscuro → oliva → ocre → `#d6cdbd` | sombreado 315°/45° | leyenda en m | Capa «Relieve»; nunca blanco |
| Curvas de nivel | línea | `#b08a5c` / `#d9b07a` | 0,6 / 1,1 px | cifra cada 500 m | Conmutables |
| Precipitación 3 h | área | `#9cc0ff` → `#4f8cff` → `#2a56c8` | transparente < 0,5 mm | «mm/3 h» | No amarillo/rojo |
| Nieve probable | área | `#eaf6ff` | trama de puntos + borde `#7cc6ff` | «nieve probable» | Sobre cota de copo |
| Viento / racha | área | `#8f9bff` → `#c58cff` | — | «km/h» | Sin rojos |
| Temperatura | área | `#5b7cff` → `#dfe7ea` → `#ff9a4d` | 0 °C neutro | «°C» | Capa modelizada con trama en valle |
| Estación oficial observada | marcador | color de lectura | círculo relleno, borde `#0d1417` | nombre + valor | Edad ≤ 90 min |
| Estación no oficial | marcador | color de lectura 70 % | círculo + anillo punteado | nombre + «(no oficial)» | Meteoclimatic, CNP |
| Estación antigua | marcador | `#8a9aa1` | relleno trama | «hace 3 h» | Edad > 90 min |
| UNKNOWN | área / celda | `#8a9aa1` | trama 45° `#4d5b5d/#34403f` | «UNKNOWN» | Nunca 0 ni vacío |
| Aviso amarillo / naranja / rojo | píldora | `#e8be33` / `#ff9447` / `#ff5f5f` sobre fondo 14 % | sin borde | nivel + evento | Solo oficial |
| Sello de validación | etiqueta | `--muted` | borde sólido / punteado / doble | ESTÁNDAR / DIAGNÓSTICO / EXPERIMENTAL | No usar colores de dato |
| Hora elegida | marca | `#5fd0c4` | línea vertical 1,5 px + triángulo en eje | «jue 12 h» | En todos los gráficos temporales |

---

## 6. Prioridad recomendada

| Orden | Hallazgos | Esfuerzo | Efecto |
|---|---|---|---|
| 1 | GFX-01, 05, 06, 16 (reglas de color + rampas) | S–M | Quita el «lío» semántico; mejora todo a la vez |
| 2 | GFX-04, 19, 03 (Vigilancia, acento, CSS) | S | Coherencia con la marca paraguas en la primera pantalla |
| 3 | GFX-12, 14 (inversión + gramática observado/modelo/UNKNOWN) | M | El gráfico firma deja de aparecer vacío; la honestidad se ve |
| 4 | GFX-07, 08, 17 (corte, cotas, móvil) | M | Lo mejor del Pirineo, legible en el teléfono |
| 5 | GFX-09, 10, 11 (atmósfera) | M | Menos ruido, escalas honestas |
| 6 | GFX-02, 15, 13, 18, 20 | M | Pulido y accesibilidad |

**Pruebas sugeridas (SUPUESTO):** test de 5 segundos del mapa de «Cota de nieve» con 5 usuarios de esquí/montaña («¿dónde hay nieve?»), antes y después de la regla del blanco; y prueba de daltonismo con simulador sobre las rampas de temperatura.

---

## 7. Limitaciones de esta auditoría

- Datos reales de un solo ciclo (11/11/2026 22:54, noche de lluvia con avisos amarillos y uno naranja); no se han visto capas con nevada, tormenta ni inversión fuerte.
- No se han probado lectores de pantalla ni simuladores de daltonismo; las afirmaciones de accesibilidad son por inspección de código y captura (OBSERVADO) y por teoría del color (SUPUESTO).
- Ninguna observación sobre usuarios reales: lo que el usuario «esquí y montaña» necesita es SUPUESTO.
- La comparación con Portinatx se limita a su consola y al hub; no se ha revisado «Decidir» ni «Dispositivo» en profundidad.

---

## 8. Resumen final (10 líneas)

1. El Pirineo tiene un núcleo gráfico propio y sólido (relieve con curvas, corte vertical, cotas), pero la identidad está a medias.
2. El mayor fallo es semántico: el mismo color significa cosas distintas (blanco = nieve/cima/0 °C; azul = lluvia/Tw/estándar; amarillo = aviso/UNKNOWN).
3. La capa «Relieve» pinta cumbres blancas haya o no nieve: engaña (GFX-01, P0).
4. El mapa de temperatura muestra celdas del modelo con aire de medición y no marca el valle, donde el modelo no ve la inversión (GFX-02, P0).
5. La marca paraguas se rompe: dos colores de Pirineo (azul en el hub, verde azulado en la consola), la ruta con otra tipografía, y Vigilancia sin píldoras de nivel.
6. Observado / modelizado / UNKNOWN se dice en notas pero no se ve; propongo cuatro «voces» gráficas (sólido, anillo, discontinuo, trama).
7. Gráficos concretos: corte con etiquetas solapadas e ilegible en móvil, índices con escala propia que convierten el ruido en señal, hodógrafa y perfil T/Td/Tw poco informativos, ensemble en tabla de «0 %».
8. La inversión observada, el gráfico firma, aparece vacío por un umbral de frescura con 36 estaciones disponibles.
9. Dirección propuesta «Cresta y cota»: acento verde azulado único, roca cálida, nieve = blanco-hielo con trama, riesgo oficial reservado, UNKNOWN en trama; hoja de estilo en §5.4.
10. Orden sugerido: reglas de color y rampas, coherencia de marca (Vigilancia, hub, ruta), gramática de procedencia, y luego legibilidad móvil y atmósfera; 20 hallazgos (2 P0, 14 P1, 4 P2).
