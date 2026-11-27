# 05 · Móvil y accesibilidad: auditoría y correcciones

**Base:** rama `main` en 107dfe5. **Criterio:** WCAG 2.2 AA. **Método de la auditoría:** Playwright con Chrome headless a 360×780 (`isMobile`), árbol de accesibilidad por CDP y contraste calculado con la fórmula WCAG 2.x. Páginas en **estado vacío** (sin red); las gráficas de Portinatx se probaron con datos **sintéticos**.

Marcas: **OBSERVADO** = medido en el navegador; **SUPUESTO** = inferencia no verificada; **UNKNOWN** = no se puede afirmar con lo medido.

## Resumen de la auditoría

Antes de las correcciones el resultado era **NO CONFORMA** (1.4.10, 1.1.1 y 1.4.1).

| ID | Sev. | Criterio | Hallazgo (OBSERVADO) | Estado |
|---|---|---|---|---|
| A-01 | P0 | 1.4.10 / 1.4.4 | Portinatx y Pirineo sin `meta viewport`, y Pirineo además en modo quirks. En móvil se maquetan a 980 px y el texto de 14 px se ve a unos 5 px. | Corregido |
| A-02 | P1 | 1.1.1 | Las gráficas SVG de Portinatx no tienen nombre accesible: `lineChart` emitía `role="img"` sin `aria-label`, y otros 10 `svg.ch` no tenían ni rol ni nombre. | Corregido |
| A-03 | P1 | 1.4.1 | El nivel se transmitía solo por el color. En la franja de historial iba en un `<title>` en inglés, visible solo al pasar el ratón. En el Gantt de avisos se quitaba «de nivel X» de la etiqueta. | Corregido |
| A-04 | P1 | 2.1.1 | El GPX de Rutas no se podía subir con teclado: el `input` estaba `hidden` y la etiqueta no era enfocable. | Corregido |
| A-05 | P2 | 1.1.1 | Los lienzos `#cmap` y `#cprof` de Rutas no tenían nombre. | Corregido |
| A-06 | P2 | 1.4.4 | El texto de las gráficas mide 10 unidades del `viewBox`; a 360 px queda en unos 4,7 px. | **Abierto** |
| A-07 | P2 | 2.5.8 | Varios controles medían menos de 24 px: selectores de idioma, `summary`, deslizadores, enlaces de cabecera y la casilla `#wake`. | Corregido |
| A-08 | P2 | 2.3.3 | El hub no respetaba `prefers-reduced-motion`. | Corregido |

**Contraste (OBSERVADO):** todos los textos de nivel dan al menos 4,5:1 (Portinatx 5,03–7,51; Rutas 5,70–9,56). Sigue fallando el borde `--line` de Portinatx, con 1,39:1; incumple 1.4.11 si ese borde delimita controles. No se ha tocado.

## Qué se corrigió

- **Viewport y doctype.**
  - Se añadió `<meta name="viewport" content="width=device-width, initial-scale=1">` en `src/portinatx_app.html` y `src/pirineo_app.html`.
  - Se añadió `<!doctype html>` en `src/pirineo_app.html`.
  - Antes se comprobó que `scripts/build_site.py` y `src/nowcast.py` sirven el archivo tal cual, sin envolverlo, así que no se duplican cabeceras.
  - En escritorio, el Pirineo en modo estándar se ve igual que antes en estado vacío. La única diferencia es la altura del deslizador (+4 px).
  - **La comparación entre modo quirks y modo estándar del Pirineo se hizo solo en estado vacío.** Con datos (mapas, cortes, tablas y gráficas) no se ha comparado: cómo queda la maquetación en ese caso es **UNKNOWN**.
- **Gráficas de Portinatx.**
  - `lineChart` acepta ahora `label` y emite `role="img" aria-label="…"`. Las 17 llamadas pasan un título con sus unidades.
  - Las otras 11 SVG informativas tienen `role="img"` y un nombre: Gantt, historial, trayectorias, perfil, hodógrafa, umbrales, distribución de 24 h, sensibilidad, barrido, θe y cizalladura.
  - Los dos mini-gráficos decorativos ya tenían `aria-hidden="true"`.
- **Nivel como texto.**
  - Gantt de avisos: cada fila muestra el evento y debajo «de nivel X». Las filas pasan de 20 a 28 unidades de alto, y a 38 cuando hay una tercera línea.
  - **V-01 (revisión independiente).** El nivel visible y el accesible salen del campo `nivel`, la misma fuente que el color de la barra. En la primera versión salían del texto del evento, así que texto y color podían contradecirse.
    - Si falta `nivel`, o no es verde, amarillo, naranja ni rojo, se muestra «de nivel sin verificar» y la barra sale gris.
    - Si el texto del aviso nombra otro nivel, se añade una línea «el texto dice X». En el nombre accesible se lee «(el texto del aviso dice X)».
    - El texto del aviso no se modifica.
  - **V-02.** El nombre accesible del Gantt incluye el nombre completo del evento (sin recortar) y su nivel.
  - **V-06.** La etiqueta visible se recorta a 22 caracteres con «…», para que no se salga del gráfico por la izquierda.
  - Historial: los `<title>` usan `LV_ES` (español). Debajo de la franja se ve el texto «Último ciclo: precaución X · 36 h Y», y el `aria-label` incluye el número de ciclos y ese resumen.
- **GPX con teclado (Rutas).**
  - El `input` de archivo deja de estar `hidden`. Pasa a estar oculto solo a la vista (clase `.vh`), se coloca antes de su `label` y el foco se ve en la etiqueta («Subir track GPX»).
  - Con Espacio se abre el selector de archivos: 15 de 15 intentos en Chrome headless (OBSERVADO). Con Enter, el mismo Chrome headless lo abrió solo en 6 de 15 intentos, y en 7 de 15 con un manejador `keydown` que llama a `click()`. Por eso no se añadió el manejador. En un dispositivo real, el comportamiento con Enter es **UNKNOWN**.
- **Lienzos de Rutas:** `role="img"` y `aria-label` en `#cmap` y `#cprof`.
- **Hub:** `@media (prefers-reduced-motion:reduce){.card{transition:none}}`.
- **V-04: estados en español en la interfaz.** El valor interno no cambia.
  - Fases del episodio en el historial: Activo, Cese, Transición, Cierre propuesto y Cerrado. El valor interno se guarda en `data-phase`.
  - UNKNOWN se muestra como «Desconocido (UNKNOWN)», para mantener el concepto «UNKNOWN no es cero». Afecta a las pastillas de peligro, la leyenda «Desconocido (UNKNOWN) = sin dato…», el filtro de afirmaciones y las etiquetas epistémicas de Portinatx (Evidencia, Hipótesis, Supuesto).
  - En Dispositivo, los estados de los sensores y de la tendencia se muestran como «Desconocido (UNKNOWN)», «Dato antiguo (STALE)» y «Medido».
  - La traducción parcial al inglés tiene sus equivalentes para la leyenda de Portinatx y para los estados de Dispositivo.
- **V-05:** la casilla `#wake` queda alineada verticalmente con su texto.
- **Objetivos de 24 px:** `min-height:24px` en `select`, `summary` e `input[type=range]` según la página, y en los enlaces de cabecera de Dispositivo y Rutas. La casilla `#wake` mide 24×24.
- **Test** `tests/test_a11y_mobile_browser.py`. Entra en `python src/nowcast.py selftest` por `unittest discover`, que es lo que ejecuta el CI con `METEO_REQUIRE_BROWSER=1`, y no se salta. Las comprobaciones son:
  - Las seis páginas a 360 px: viewport, modo estándar, `lang` en español, sin desbordamiento horizontal, ningún `svg`/`canvas` informativo sin nombre, controles medidos de al menos 24 px y ningún error de página.
  - Portinatx con datos sintéticos de oleaje, viento, avisos, modelos, ensemble, trayectorias, METAR, perfil, física, mar, IA/superensemble y forense. Con esos datos se pintan **25 gráficas SVG** y los 8 lienzos, y el test exige las 25 por su identificador. Ninguna SVG ni ningún lienzo pintado puede quedar sin nombre: el test falla si se quita el nombre a la hodógrafa o a la gráfica de lluvia de modelos, que es la prueba del verificador repetida.
  - Gantt: tres casos. Un aviso coherente. Uno con `nivel` naranja cuyo texto dice amarillo, que debe mostrar «de nivel naranja», «el texto dice amarillo» y la barra naranja. Uno sin `nivel` cuyo texto dice naranja, que debe mostrar «de nivel sin verificar», «el texto dice naranja» y la barra gris. Además, el nombre accesible completo y ninguna etiqueta fuera del gráfico por la izquierda.
  - Historial con el nivel en español (sin `quiet`, `watch`, `alert`, `alarm` ni `unknown`), fases en español con el valor interno conservado, ningún estado en inglés sin traducir en peligros, fases y afirmaciones, y contraste de al menos 4,5:1 en las pastillas y en los textos de nivel.
  - **Gráficas que el test no pinta:** `ch-ci`, `ch-tornado` y `ch-sweep` (laboratorio). Necesitan la especificación de los indicadores compuestos y los umbrales del motor, que no se pueden sintetizar razonablemente. Su nombre está en el código, pero **el test no lo verifica**. `renderAtmos` también se corta en los índices compuestos después de pintar el perfil y la hodógrafa, así que la rejilla de índices no se recorre.
  - Dispositivo: estados en español y casilla `#wake` alineada con su texto (como mucho 4 px de diferencia entre centros).
  - Rutas: contraste de las pastillas `l0`–`l4`, `#file` alcanzable con el tabulador, foco visible en la etiqueta y selector abierto con Espacio (Enter no se comprueba: ver límites).
  - Hub con `reducedMotion:'reduce'`: duración de transición 0 s.
  - Se comprobó que el test **falla** con el código de `main` (primer fallo: selector de idioma del hub de 19 px).

## Límites de lo corregido

- **Datos.** Todo se probó en estado vacío o con datos sintéticos. Con datos reales, el desbordamiento de pestañas (UI-02 del plan) es **UNKNOWN**.
- **Gantt.** La etiqueta visible del evento se recorta a 22 caracteres con «…», por ejemplo «fenómenos costeros (c…». El nombre completo está en el nombre accesible.
- **Estados en inglés que quedan en Portinatx.** No se han traducido los resultados de las predicciones (HIT, MISS, PENDING…) ni otros estados de fuentes y canales que se muestran tal cual. Están fuera de V-04; conviene revisarlos en un cambio aparte.
- **Historial.** El resumen en texto da el nivel del **último** ciclo. Los ciclos anteriores siguen identificándose por color y por `<title>`, que ya está en español.
- **Idioma.** Los nombres accesibles nuevos están solo en español. Con la traducción parcial al inglés activada, siguen en español.
- **Enter en el GPX.** No se garantiza: en Chrome headless es intermitente (ver arriba). Falta comprobarlo en navegadores y dispositivos reales.
- **Pirineo.** `lang` sigue poniéndolo JS; no se añadió `<html lang>` estático.
- **Texto pequeño.** A-06 (texto de las gráficas a unos 4,7 px en móvil) queda abierto: requiere cambiar el `viewBox` o la fuente según el ancho, con esfuerzo M.

## No cubierto

- **Lector de pantalla real** (VoiceOver en iOS, TalkBack, NVDA). No se sabe cómo anuncian los `aria-label` de SVG y canvas, los cambios de pestaña ni las regiones `aria-live`. **UNKNOWN**.
- **Pruebas con usuarios.** No se sabe si se entienden los niveles ni si se leen en un móvil al sol. **UNKNOWN**.
- **Zoom al 200 % y al 400 %** (1.4.4 y 1.4.10 con zoom del navegador o del sistema).
- **Colores forzados** (`forced-colors` / alto contraste de Windows) y simulación de deuteranopía después de los cambios.
- **Otros:** dispositivo físico, rendimiento real, jerarquía de encabezados, axe-core (no instalado en esta pasada) y el borde `--line` a 1,39:1.
