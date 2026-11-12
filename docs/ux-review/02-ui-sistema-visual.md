# 02 · Auditoría UI: sistema visual (foco Pirineo)

Revisor: UI Designer + UI Finish-Gate Reviewer (NEXUS). Solo lectura: no se ha editado código.
Fecha: 2026-11-11. Versión auditada: motor 0.6.1, release 0.6.0.

Leyenda: **OBSERVADO** = medido o visto en navegador (Playwright/Chromium, dsf 1) o leído en el código. **SUPUESTO** = inferencia sin prueba directa.
Capturas en `docs/ux-review/img/ui-*.png`. Las capturas `ui-pir-*-390.png` se hicieron sobre una **copia parcheada** (con `<!doctype>` y `viewport`) en el directorio temporal de la sesión, nunca sobre el repo; las `ui-*-1440.png` y `ui-pirineo-390.png` son el código real. Datos: sitio ya construido (`build_site`) con `api/*.json` reales del 11/11.

## 0. Lente de producto

- **Usuario y trabajo:** persona que sale al Pirineo (esquí de travesía/ruta) o lo vigila desde casa. Quiere saber en 10 s "¿qué hay oficial, qué es modelo, qué decide mi salida?" y, si es técnica, inspeccionar perfiles, cortes y ensemble.
- **Objeto de primera lectura:** el aviso oficial vigente + la antigüedad del dato. Hoy es lo primero en Vigilancia, bien.
- **Frecuencia:** uso diario móvil (en refugio, coche, con guantes) frente a uso de escritorio puntual para análisis.
- **Hallazgo central:** el usuario dice "es un lío" y los datos lo confirman. Son **5 páginas con 4 lenguajes visuales distintos** y, sobre todo, **la consola Pirineo (la principal) y Portinatx no son utilizables en móvil**: no declaran `viewport` ni `doctype` (UI-01). Todo lo demás se mide encima de ese defecto.

Páginas auditadas: `pirineo_app.html` (72 KB, 12 pestañas), `pirineo_ruta.html`, `decision_app.html`, `nowcast_hub.html`, `portinatx_app.html` (170 KB, comparativa), más `pirineo_observatory.js`, `pirineo_atmos.js`, `decision_cards.js`.

## 1. Resumen de hallazgos

| ID | Sev. | Hallazgo | Esfuerzo |
|----|------|----------|----------|
| UI-01 | P0 | Consola Pirineo/Portinatx sin `doctype` ni `viewport`: móvil renderiza a 980 px y modo quirks | S |
| UI-02 | P0 | Al corregir UI-01 aparecen 5 pestañas con desbordamiento horizontal en 390 px | M |
| UI-03 | P0 | Fallo de carga de datos = "esperando datos…" eterno, sin error ni reintento | S |
| UI-04 | P1 | Cuatro sistemas de tokens para una misma marca (colores, radios, tipografías) | M |
| UI-05 | P1 | Gráficos SVG con etiquetas superpuestas/ilegibles (corte vertical, hodógrafa) | M |
| UI-06 | P1 | Objetivos táctiles: 100 % de los controles medidos de la consola < 44 px | M |
| UI-07 | P1 | Escala tipográfica sin sistema: 25 tamaños de fuente y piso de 10-11 px | M |
| UI-08 | P1 | Tres cabeceras y tres idiomas de navegación distintos entre páginas hermanas | M |
| UI-09 | P1 | Contraste: bordes 1,35:1 y color `--cu`/trazos de ruta bajo mínimo | S |
| UI-10 | P1 | Densidad: pestaña Atmósfera mide 5 456 px; Superficie 7 442 caracteres; 12 pestañas sin jerarquía | M |
| UI-11 | P1 | Etiquetas del mapa de relieve se solapan; canvas sin alternativa textual de datos | M |
| UI-12 | P2 | Estilos en línea masivos (101 en Portinatx, 29 en Pirineo) y `!important` | M |
| UI-13 | P2 | Solo modo oscuro fijo (`color-scheme:dark`); sin modo claro para sol | M |
| UI-14 | P2 | Fuentes de Google en Pirineo vs "sin terceros" en Ruta: incoherencia visual y de privacidad | S |
| UI-15 | P2 | `ruta` anclada a la izquierda con 1200 px máx. y hueco muerto a 1440 px | S |
| UI-16 | P2 | Datos crudos en inglés/ID mezclados (`UNKNOWN`, `multi-family`, `NOT_INTEGRATED`, `Moderate thunderstorm warning`) | S |

## 2. Hallazgos detallados

### UI-01 · P0 · Sin `doctype` ni `viewport` en la consola Pirineo y en Portinatx (OBSERVADO)
- **Evidencia:** `src/pirineo_app.html:1-3` y `src/portinatx_app.html:1-3` empiezan con `<meta charset>` y una meta inventada `claude:viewport-fit-sides`; no hay `<!doctype>`, `<html lang>` ni `<meta name="viewport">`. Medido: `document.compatMode = "BackCompat"` (quirks) y `lang=""` en ambas. A 390x844 con emulación móvil: `scrollWidth = clientWidth = 980`, es decir, el navegador móvil dibuja un lienzo de 980 px y lo reduce al 40 %. Texto de 14 px pasa a ~5,6 px efectivos. Captura: `ui-pirineo-390.png`, `ui-portinatx-390.png`. Páginas hermanas (`pirineo_ruta`, `decision_app`, `nowcast_hub`) sí llevan doctype, `lang="es"` y viewport.
- **Impacto:** en el dispositivo principal del producto la consola es ilegible y los controles no se pueden pulsar. Quirks mode además altera cajas, alturas de tabla y `line-height`, y sin `lang` los lectores de pantalla y el corrector no saben el idioma. Los `@media (max-width:600px)` y `(max-width:1000px)` existentes **nunca se activan en móvil** (el ancho de layout es 980).
- **Recomendación:** añadir `<!doctype html><html lang="es">` y `<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">`; envolver `<style>`/`<header>` en `<head>/<body>`; eliminar la meta `claude:viewport-fit-sides`. Las reglas `env(safe-area-inset-*)` ya existentes solo funcionan con `viewport-fit=cover`.
- **Esfuerzo:** S (2 líneas por archivo), pero **desencadena UI-02**; hacerlo junto.

### UI-02 · P0 · Desbordamiento horizontal en 390 px una vez corregido el viewport (OBSERVADO)
- **Evidencia:** sobre copia parcheada, `scrollWidth` vs `clientWidth` 390: Atmósfera 722, Puntos 1121, Modelos 803, Ensemble 938, Gobernanza 642; Superficie con `TABLE` de 705 px. Selectores culpables: `.card`/`.bar` con barras de controles `white-space:nowrap`, tablas con `th,td{white-space:nowrap}` (`pirineo_app.html:~58`) cuyo contenedor `.tbl` debería hacer scroll pero la `section.card` hija directa no tiene `min-width:0` en todos los casos. Capturas: `ui-pir-puntos-390.png`, `ui-pir-atmosfera-390.png`, `ui-pir-modelos-390.png`, `ui-pir-extendido-390.png`, `ui-pir-gobernanza-390.png`.
- **Impacto:** al arreglar UI-01 la página "se rompe" lateralmente: scroll horizontal de página completa, tarjetas cortadas (en la captura de Puntos la tabla ya queda truncada en "TW °C"). Esto explica por qué nadie lo detectó: el 40 % de escala oculta el problema.
- **Recomendación:** contrato responsive explícito: toda tabla dentro de `.tbl{overflow-x:auto}` con columna de primera celda sticky; `.bar` con `flex-wrap` y controles `min-width:0`; en <640 px las tablas de 5+ columnas pasan a lista de tarjetas (punto, valor principal, 2 secundarios). Añadir un test Playwright "sin scroll horizontal en 390 px" por pestaña.
- **Esfuerzo:** M.

### UI-03 · P0 · Estado de error de carga ausente (OBSERVADO)
- **Evidencia:** `pirineo_app.html:331` `catch (e) { /* Keep previous coherent domain on failure. */ }` sin UI. Prueba con `api/*.json` abortado: cabecera permanece `esperando datos…` (`#m-issued`), mapa con "Hora / —", sin mensaje, sin botón reintentar, sin spinner. Captura `ui-pir-error-api-1440.png`. Solo existen estados textuales sueltos (`.empty`, `.pov-unknown`).
- **Impacto:** en un producto cuyo valor es la honestidad sobre el estado del dato, el peor estado (no hay dato) es mudo y indistinguible de "cargando". Contradice el principio del propio producto ("una instantánea antigua nunca se interpreta como ausencia de peligro").
- **Recomendación:** banner de estado de datos persistente con 4 estados definidos: Cargando (skeleton), Actual, Caducado (naranja, con edad), Error (rojo, "No se pudo cargar. Reintentar · último dato: hh:mm"). Reutilizar `.pov-unknown` como componente `Callout`.
- **Esfuerzo:** S-M.

### UI-04 · P1 · Cuatro sistemas de tokens para una sola marca (OBSERVADO)
Inventario (conteo sobre el código fuente; "distintos" = valores únicos declarados):

| Concepto | `pirineo_app` / `portinatx` / `ruta` | `decision_app` | `nowcast_hub` |
|---|---|---|---|
| Fondo | `#0d1417` | `#0b151b` | `#0d151b` |
| Panel | `#141e22` (+ `--panel2 #10181c`) | `#13232a` (+ `--surface2 #192e36`) | `#17232a` |
| Borde | `#26363b` | `#314854` | `#314450` |
| Texto | `#e4ebe9` | `#eaf2f3` | `#e5edf1` |
| Texto atenuado | `#8fa19f` | `#abc0c9` | `#9aacb5` |
| Acento primario | `--accent #5fd0c4` (turquesa) | `--sea #f49b7d` (coral) | `--sea #ff916a` (coral) |
| Azul "hielo" | `--ice #7cc6ff` | `--mount #88c9df` | `--snow #90cffe` |
| Naranja aviso | `--fz #ff9a4d` / `--a #ff9447` | `--amber #ffd49a` | n/d |
| Radio | 4 px (9 usos) y 6 px (2) | 8, 9, 12, 14, 18, 999 px | 15, 16, 999 px |
| Fuente | Saira Condensed + Public Sans + IBM Plex Mono (Google Fonts) | `system-ui` | `system-ui` |
| Peso | 500/600 | 700/750/800 | 700 |
| Tamaños de fuente distintos | 15 | 14 | 6 |

- Total: **5 fondos, 5 "paneles", 3 bordes, 3 textos y 3 "muteds" para lo que debería ser un único valor cada uno**. Ruta (`pirineo_ruta.html:10-15`) copia los tokens de Pirineo pero cambia la tipografía a `system-ui`, y añade grises propios (`#4d5b5d` x5, `#34403f` x5, `--cu #6b7a7c`) que no existen en la consola.
- `portinatx_app.html` declara 54 hex distintos (89 usos); en `pirineo_app` 24 distintos, 26 usos: la mayoría de la paleta se define una sola vez (bien) pero los 5 "semáforos" `--q/--w/--a/--x` + `--std/--diag/--exp` se redefinen con otros nombres en ruta (`--c0..--c4`) para el mismo significado.
- **Impacto:** el usuario percibe cuatro productos distintos (turquesa técnico / coral editorial). Cada ajuste de color cuesta 3-5 ediciones.
- **Recomendación:** extraer `tokens.css` único (ver sección 4) importado por las 5 páginas. Decidir **una** voz: el hub y "Decidir" (editorial, coral) y la consola (cartográfica, turquesa) pueden coexistir solo si el cambio es intencionado y marcado (p. ej. acento por dominio: coral=Ibiza/marino, turquesa=Pirineo), pero compartiendo superficies, bordes, texto, radios y escala.
- **Esfuerzo:** M.

### UI-05 · P1 · Gráficos con etiquetas superpuestas (OBSERVADO)
- **Evidencia:** `ui-pir-corte-1440.png`: las etiquetas rotadas ("Port d'Envalira 3º · lluvia", "Pas de la Casa 4º", "Grau Roig", "Canillo 11º · lluvia", "La Molina 8º", "Bourg-Madame", "Tossa d'Alp lluvia") se cruzan entre sí y con la línea de isocero/cota; "Tossa d'Alp 2º" se corta contra el borde. Generación en `pirineo_app.html:~516` (`<line … stem>` + texto rotado, sin algoritmo de colisión). Hodógrafa (`ui-pir-atmosfera-1440.png`): etiquetas de nivel "1000/850/500/700/300" superpuestas sobre las de velocidad "10/20/30/40" ("10850" ilegible). El perfil T/Td/Tw (3 curvas casi idénticas) no muestra leyenda visible en la captura; el color es el único canal.
- **Impacto:** el gráfico central de la pestaña "Corte y cotas" (la más relevante para decidir cota de lluvia/nieve) no se puede leer en escritorio; en móvil será peor. Daño directo a la tarea.
- **Recomendación:** (a) etiquetas de punto en horizontal, alternando 2 alturas y con descarte por colisión (prioridad: pasos/collados con diferencia de cota de lluvia); detalle completo en tabla bajo el gráfico; (b) hodógrafa: etiquetas de nivel solo en 3 puntos y velocidad en anillos con halo de fondo (`paint-order:stroke`); (c) leyenda siempre visible y marcadores diferenciados por forma, no solo color; (d) `svg.ch text{font:11px}` fijo (`:71`) más `viewBox` escalado produce 17 px en escritorio y 5 px en móvil: usar `font-size` en unidades del viewBox calculadas por ancho renderizado.
- **Esfuerzo:** M.

### UI-06 · P1 · Objetivos táctiles < 44 px (OBSERVADO)
- **Medido** (a:`a,button,select,input,summary` visibles): Pirineo 19-26 de 19-26 por debajo de 44 px en las 12 pestañas (100 %). Ejemplos: `Decidir` 66x26, `← Observatorios` 127x26, `.btn` (`padding:4px 10px`, línea 40) ≈ 26-28 px de alto, pestañas `nav.tabs a` (`padding:5px 12px`) ≈ 34 px, selectores. Ruta 8/8, Portinatx 20/20, Decidir 6-7 de 14, Hub 1-2 de 5.
- **Nota:** hoy el problema queda enmascarado porque la página se ve al 40 % (UI-01); tras corregirlo seguirán siendo 26 px reales.
- **Recomendación:** `--tap-min:44px` (pointer:coarse); `.btn`, `nav.tabs a`, `select`, enlaces de cabecera con `min-height:44px`; `input[type=range]` con `height:44px` de zona activa; separaciones ≥ 8 px. Se puede mantener la versión compacta de 32 px en `@media (pointer:fine)`.
- **Esfuerzo:** M (se resuelve con 3-4 reglas si primero se unifican los componentes, UI-08).

### UI-07 · P1 · Jerarquía tipográfica sin escala (OBSERVADO)
- **Evidencia:** unión de tamaños en las 4 páginas con CSS propio: **25 valores** (`.68, .7, .72, .75, .76, .78, .8, .81, .82, .84, .86, .88, .9, .93, 1, 1.04, 1.05, 1.1, 1.14, 1.2, 1.22, 1.5, 1.6, 1.7, 2 rem`). Pares casi iguales: .75/.76/.78/.8/.81/.82/.84 (7 variantes de "texto pequeño" entre 12 y 13,4 px). Portinatx: 18 tamaños, `.75rem` x36 y un `10px` literal (`:101`) y `.62rem` (≈10 px). Mínimos medidos: 11,2 px (Pirineo, texto), 10,88 px (Corte, Superficie, Puntos), 10 px (Portinatx), 11,5 px (Decidir). SVG: `font:11px`.
- El texto auxiliar `.src`, `.ev`, `.kv span`, `.st` (11-12 px), `footer` es lo que sustenta el rigor del producto (qué es modelo, qué no), y es lo más pequeño.
- Jerarquía de cabeceras: `h2` = 1,1 rem **mayúsculas, atenuado, tracking .08em** (`pirineo_app.html:25`), idéntico en peso visual a los rótulos de `th` y `.kv span`. Todo el interfaz es "etiqueta en mayúsculas": no hay un nivel de título que guíe. Los valores clave (`.kv b` 1 rem mono) no son mayores que el texto corriente.
- **Recomendación:** escala de 7 pasos (tabla en sección 4), mínimo 12 px (13 para texto de aviso/fuente), valores clave `--fs-xl` 1,5 rem; reservar mayúsculas+tracking para eyebrows/`th`, usar el título de sección en versalitas no atenuado (`--ink`). Para el dato más importante de cada pestaña usar un "KPI" de 1,5-2 rem.
- **Esfuerzo:** M.

### UI-08 · P1 · Componentes repetidos con variantes divergentes (OBSERVADO)

| Componente | Variantes encontradas |
|---|---|
| Botón `.btn` | Pirineo `padding:4px 10px; radius 4`; Ruta `padding:6px 12px; radius 4`; Decidir pastillas `radius 999` con `padding 9px`; Hub tarjeta `radius 16`. Estado activo: Pirineo `aria-pressed` fondo `--ink`; Decidir fondo claro; Ruta `aria-pressed` igual que Pirineo. |
| Enlaces de cabecera | Pirineo: 2 enlaces con `style="…border-radius:4px;padding:2px 9px"` **en línea** (`pirineo_app.html:97-98`) + 1 `.btn.act`; Ruta: texto subrayado `← Panel del Pirineo`; Decidir: 3 enlaces subrayados; Hub: sin cabecera. |
| Tarjeta `.card` | Pirineo radius 6 pad 14; Ruta idem; Decidir radius 14-18 pad 20-28; Hub radius 16 pad 28 `min-height:290px`. |
| Chip de estado | `.st` (mono 11 px, borde, radius 3), `.pill` (999 px, fondo coloreado), Ruta `.pill` (radius 3, fondo sólido `#0d1417`), Decidir "Datos antiguos" (radio 999, borde ámbar). Cuatro componentes para "estado + color". |
| KV / KPI | `.kv div` (borde, radio 4) en Pirineo y Ruta (mínimo 140 vs 150 px); Decidir usa tarjetas grandes con titular; Hub sin KPI. |
| Slider hora | Pirineo `.hour`; Ruta `label.f`/`.big output`; sin estilo propio del `range` (control nativo azul `#7cc6ff` por defecto en Chromium). |
| Navegación | 12 pestañas con scroll horizontal oculto (`scrollbar-width:none` luego `thin`, `:32` y última línea): no hay indicador de que hay más pestañas a la derecha. |

- **Impacto:** cada pantalla "habla un dialecto"; el usuario no aprende un patrón una vez.
- **Recomendación:** biblioteca de 8 componentes (Button, Tab, Card, Chip/Status, KPI, Callout, DataTable, TimeSlider) en `components.css`; cabecera común `app-header` con migas (Observatorios > Pirineo > Ruta).
- **Esfuerzo:** M-L.

### UI-09 · P1 · Contraste y límites de componentes (OBSERVADO, calculado WCAG)
| Par | Ratio | Veredicto |
|---|---|---|
| `--muted #8fa19f` sobre `--panel #141e22` | 6,27:1 | AA ok |
| `--muted` sobre `--bg` | 6,88:1 | AA ok |
| `--line #26363b` sobre `--panel` (bordes de input/botón) | **1,35:1** | Falla 3:1 para límites de control (WCAG 1.4.11) |
| `--line` Decidir `#314854` sobre `#13232a` | **1,68:1** | Falla 3:1 |
| `--cu #6b7a7c` (ruta, "cielo/sin dato") sobre panel | **3,79:1** | Falla 4,5:1 si es texto |
| Ruta `#4d5b5d`/`#34403f` sobre bg (x5 cada uno) | **2,63 / 1,73:1** | Falla si portan información |
| `.p-rojo #ff5f5f` sobre `#431a1a` | 5,03:1 | ok |
| `--exp #c58cff` sobre panel | 6,92:1 | ok |
- Los botones `.btn` (borde `--line` + fondo `--panel2` casi igual al panel) son prácticamente "texto flotante": sin relieve ni borde perceptible. `.btn[aria-pressed=true]` es el único estado claro.
- Semáforo `amarillo/naranja/rojo` se da por color + texto ("amarillo · …") en `pov-official`: **bien** (no solo color).
- **Recomendación:** `--line` de control ≥ 3:1 (≈`#5b7076` sobre panel; mantener `--line-soft` para separadores decorativos); `--cu` solo como relleno, nunca texto. Verificar el modo `forced-colors`/alto contraste (SUPUESTO: no se ha probado).
- **Esfuerzo:** S.

### UI-10 · P1 · Densidad, orden y longitud de pestañas (OBSERVADO)
- 12 pestañas planas (`pirineo_app.html:100-112`): Vigilancia, Satélite/radar, Atmósfera, Territorio, Corte y cotas, Superficie, Puntos, Modelos, Ensemble 15 días, Forense, Gobernanza, Laboratorio. Mezclan **tareas de decisión** (Vigilancia, Territorio, Corte), **analítica** (Atmósfera, Superficie, Modelos, Ensemble) y **meta/auditoría** (Forense, Gobernanza, Laboratorio) con el mismo peso. En 1440 px caben apenas; en 390 px solo se ven 3 (la barra se desplaza sin indicio).
- Altura de página a 1440: Atmósfera **5 456 px** (≈6 pantallas), Superficie 2 932 px con 7 442 caracteres, Puntos 1 617, Corte 1 581. Vigilancia: 1 034 px, bien.
- Pestaña **"Satélite/radar"** es solo una explicación de que **no está integrado** (`NOT_INTEGRATED EN ESTA CONSOLA`) con 3 enlaces: ocupa un nivel de primera navegación para un "no".
- Selector de modelo/hora (AROME/ICON/ECMWF + slider + 7 KPI) se repite en Territorio, Corte, Ensemble y otras (visible en `ui-pir-mapa-1440`, `-corte-`, `-extendido-`) y ocupa ~140 px verticales antes del contenido; en Ensemble los KPI del modelo son irrelevantes para la tabla de 15 días (que no depende de la hora).
- Ensemble: tabla de 15 filas con números "0 %" repetidos y una columna "multi-family" textual idéntica en todas las filas (ruido); la fila relevante (cuándo cambia) no se destaca. Columnas centradas a la derecha con 270 px de hueco entre cabecera y valor.
- **Recomendación:** 3 grupos: **Ahora** (Vigilancia, Territorio, Corte), **Analizar** (Atmósfera, Superficie, Puntos, Modelos, Ensemble), **Auditar** (Forense, Gobernanza, Laboratorio; colapsado, "Para técnicos"). Eliminar Satélite/radar como pestaña (pasa a pie de Vigilancia). El control compartido modelo+hora se vuelve barra sticky compacta única. En Ensemble: mini-gráfico (sparkline/barras) de fracción de nieve/TW≤0 por día en lugar de la tabla de 15 filas; tabla bajo "ver datos".
- **Esfuerzo:** M.

### UI-11 · P1 · Mapa de relieve: etiquetas solapadas y sin alternativa (OBSERVADO)
- **Evidencia:** `ui-pir-mapa-1440.png`: "Andorra la Vella"/"Escaldes-Engordany" y "Port d'Envalira"/"Pas de la Casa" se montan; "Font-Romeu 1773"/"Bolquère 1615"; el relieve sombreado marrón/verde con curvas naranja compite con las etiquetas (sin halo). `canvas#map` solo tiene `aria-label` (`:172`); las cinco capas (Relieve, Cota de nieve, Temperatura, Precipitación, Racha) no tienen leyenda visible en la primera pantalla; la leyenda existe más abajo (`.legend`, `.75rem`).
- **Bien:** mapa grande y central (aspect-ratio 1,512), selector de capas simple, curvas con valor, offline y sin teselas de terceros. Es el elemento más "propio del producto".
- **Recomendación:** halo oscuro en etiquetas (`strokeText` + `fillText`), desplazamiento anti-colisión, nivel de detalle según zoom/tamaño (en 390 px solo ~8 etiquetas prioritarias), leyenda de la capa pegada al mapa con unidades, y tabla de puntos accesible (ya existe en Puntos) enlazada desde el mapa.
- **Esfuerzo:** M.

### UI-12 · P2 · Estilos en línea y `!important` (OBSERVADO)
- Conteo `style="`: Portinatx 101 (116 con plantillas JS), Pirineo 29, Ruta 13, Hub 4, Decidir 0. `!important`: 2-3 por archivo (`[hidden]`, `prefers-reduced-motion`; aceptables). Los enlaces de cabecera en línea (`:97-98`) impiden aplicar UI-06 con una sola regla.
- **Recomendación:** mover a clases (`.chip-link`), tras UI-08.
- **Esfuerzo:** M.

### UI-13 · P2 · Modo oscuro único (OBSERVADO)
- Las 5 páginas fijan `color-scheme:dark`; no hay `prefers-color-scheme` (0 coincidencias). Prueba con `colorScheme:'light'`: fondo `rgb(11,21,27)` siempre. Para consola de montaña de noche es razonable.
- **Riesgo (SUPUESTO):** a pleno sol sobre nieve el texto atenuado (`#8fa19f`) y bordes de 1,35:1 son difíciles de leer; no hay modo "alto contraste/sol". Mantener oscuro por defecto pero ofrecer `data-theme="sun"` (fondo claro, texto `#10181c`) como opción, una vez existan tokens (UI-04).
- **Esfuerzo:** M (barato si los tokens son semánticos).

### UI-14 · P2 · Fuentes y privacidad visual (OBSERVADO)
- `pirineo_app.html:4-5`: `preconnect` + hoja de `fonts.googleapis.com` (3 familias). `pirineo_ruta.html:11` declara "Sin fuentes ni mapas de terceros" y usa `system-ui`: es **la única página consciente de la privacidad** y por eso cambia de tipografía, de modo que "Ruta y tiempo" parece de otra app que su página madre. También aumenta el FOUT (cambio de fuente al cargar) y el peso de red.
- **Recomendación:** autohospedar las 3 fuentes (subset latin + latin-ext, `font-display:swap`, ~60-90 KB en woff2) y usarlas también en Ruta; elimina la petición a Google y unifica.
- **Esfuerzo:** S.

### UI-15 · P2 · Ruta: hueco muerto y alineación (OBSERVADO)
- `pirineo_ruta.html:24` `main{max-width:1200px}` sin `margin:auto` mientras `body` ocupa 1440: en `ui-ruta-1440.png` la columna queda pegada a la izquierda con 224 px de vacío a la derecha, y la cabecera sí ocupa todo el ancho (línea separadora a 1424 px). La fila de controles (Actividad / Factor de ritmo / Pausas / Origen) tiene bases desalineadas (etiquetas a distinta altura: "Actividad" y "Origen del ritmo" más bajas que "Factor de ritmo"/"Pausas").
- **Recomendación:** `margin-inline:auto`, o mejor un layout de 2 columnas a >1100 px (parámetros a la izquierda, resultado/gráfico a la derecha fijo); alinear `label.f` con `align-items:end` o rejilla de 4 columnas.
- **Esfuerzo:** S.

### UI-16 · P2 · Texto técnico sin traducir ni jerarquizar (OBSERVADO)
- Valores mostrados tal cual del motor: `UNKNOWN` (Vigilancia: "Observación ≤90 min UNKNOWN", "Nieve modelo (3 h) UNKNOWN"), `multi-family` (Ensemble, 15 filas), `NOT_INTEGRATED EN ESTA CONSOLA`, `Moderate thunderstorm warning` (aviso francés sin traducir), `Ensemble member fractions, NOT locally calibrated…` (pie en inglés), `AROME HD 1,5 km`, identificadores `best_match`. En Vigilancia las líneas "Racha prevista27 km/h", "Precipitación (bloque 3 h)2,8 mm" salen **sin separación entre etiqueta y valor** (`ui-pirineo-1440.png`, bloque central), un fallo de maquetación: falta espacio/`justify-between`.
- **Recomendación:** diccionario de estados (`UNKNOWN`→"Sin dato", con icono gris y tooltip del motivo); alinear pares etiqueta/valor con `dl` en rejilla.
- **Esfuerzo:** S.

## 3. Gráficos, tablas, mapas: resumen de legibilidad

| Elemento | Escritorio 1440 | Móvil 390 | Nota |
|---|---|---|---|
| Mapa relieve (canvas) | Legible, etiquetas con solapes | SUPUESTO ilegible (etiquetas fijas) | UI-11 |
| Corte vertical (SVG) | Etiquetas rotadas se solapan | Peor (UI-05) | UI-05 |
| Perfil T/Td/Tw | Correcto, sin leyenda visible | Texto SVG 5-8 px | UI-05 |
| Hodógrafa | Rótulos de nivel y velocidad superpuestos | idem | UI-05 |
| Tabla Puntos | Buena (zonas separadas, números mono a derecha) | Ancho 1121 px: desborda | UI-02 |
| Tabla Ensemble | Legible, repetitiva | 938 px: desborda | UI-02/10 |
| Ruta (gráficos GPX) | No medidos en detalle; colores `c0..c4` con grises de bajo contraste | n/d | UI-09 (SUPUESTO para el gráfico) |

Tipografía mono con `tabular-nums` para cifras: **acierto** (se mantiene).

## 4. Propuesta de tokens unificados

Basada en la consola Pirineo (la más coherente) y ajustada para contraste. Prefijo `--mp-` para no colisionar.

| Grupo | Token | Valor propuesto | Sustituye |
|---|---|---|---|
| Superficie | `--mp-bg` | `#0d1417` | `#0b151b`, `#0d151b`, `#0d1417` |
| | `--mp-surface` | `#141e22` | `--panel`, `--surface`, `#17232a` |
| | `--mp-surface-2` | `#10181c` | `--panel2` |
| | `--mp-surface-raised` | `#1a2a30` | `--surface2 #192e36`, `.msg.u #16303a` |
| Borde | `--mp-line` (decorativo) | `#26363b` | `--line` actual |
| | `--mp-line-control` (≥3:1) | `#5b7076` | nuevo (UI-09) |
| Texto | `--mp-ink` | `#e4ebe9` | `#eaf2f3`, `#e5edf1` |
| | `--mp-muted` | `#9db0ae` | `#8fa19f`, `#abc0c9`, `#9aacb5` (>=7:1) |
| Marca | `--mp-accent` (Pirineo) | `#5fd0c4` | `--accent` |
| | `--mp-accent-sea` (Ibiza/Decidir) | `#f49b7d` | `--sea` x2 |
| | `--mp-link` | `#7cc6ff` | `--ice`, `--mount`, `--snow` |
| Semáforo | `--mp-ok` / `warn` / `alert` / `crit` | `#4cc184` / `#e8be33` / `#ff9447` / `#ff5f5f` | `--q,--w,--a,--x`, `--c0..--c3` |
| Estado de dato | `--mp-std` / `diag` / `exp` / `unk` | `#62b0ff` / `#e8be33` / `#c58cff` / `#8fa19f` | `--std,--diag,--exp`, `--cu` |
| Fondos de chip | `--mp-warn-bg` / `alert-bg` / `crit-bg` | `#372f12` / `#3d240f` / `#431a1a` | `.p-amarillo/naranja/rojo` |
| Tipografía | `--mp-font-display` | "Saira Condensed", "Arial Narrow", system-ui | `--f-disp` |
| | `--mp-font-body` | "Public Sans", system-ui, sans-serif | `--f-body` (y `system-ui` de Ruta/Decidir/Hub) |
| | `--mp-font-mono` | "IBM Plex Mono", ui-monospace, monospace | `--f-mono` |
| Escala | `--fs-xs` 12 / `sm` 13 / `base` 14 (15 en móvil) / `md` 16 / `lg` 20 / `xl` 24 / `2xl` 32 px | 7 pasos | 25 valores actuales |
| Peso | `--fw-regular` 400 / `medium` 500 / `semibold` 600 | 3 | 500/600/700/750/800 |
| Espaciado (4 px) | `--sp-1..8` | 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 | 36+ combinaciones |
| Radio | `--r-sm` 4 / `--r-md` 8 / `--r-pill` 999 | 3 | 2,3,4,5,6,8,9,12,14,15,16,18,50 %,999 |
| Sombra | `--sh-overlay` | `0 8px 28px rgba(0,0,0,.4)` | única sombra actual `-10px 0 28px` (chat) |
| Táctil | `--tap-min` | 44px (`pointer:coarse`), 32px (`pointer:fine`) | 26-34 px actuales |
| Ancho | `--w-content` | 1200px, `margin-inline:auto` | `max-width` varios |

## 5. Lo que ya funciona (Keep)

- Vigilancia pone el aviso oficial y la antigüedad del ciclo como primer objeto de lectura, con separación explícita "oficial / observación / diagnóstico". Rasgo propio del producto, no genérico.
- Semáforos con texto + color, no solo color.
- Mono tabular para cifras; tablas de Puntos con grupos por zona.
- Mapa de relieve propio, offline, grande y central; Ruta con aviso de privacidad visible y primero.
- Focus visible (`:focus-visible` 2 px `--ice`), `prefers-reduced-motion`, `safe-area-inset-*` presente (aunque inactivo por UI-01).
- Pestañas con `aria-current`, `h1`/`h2` presentes.

## 6. Finish-gate

**Decisión: FAIL (HOLD).** Motivos que bloquean:

1. **UI-01**: la pantalla principal no se puede usar en móvil (quirks + sin viewport; 980 px a escala 40 %). Verificar con: 390x844 `scrollWidth==390`, `compatMode=="CSS1Compat"`, texto base >= 14 px efectivos.
2. **UI-02**: tras arreglarlo, 5 pestañas desbordan en horizontal. Verificar con: test Playwright "scrollWidth<=clientWidth" en las 12 pestañas a 390 y 768.
3. **UI-03**: sin estado de error/cargando. Verificar con: bloqueo de `api/*.json` muestra banner de error con reintento.
4. **UI-05**: el gráfico clave (corte vertical) y la hodógrafa tienen etiquetas ilegibles. Verificar con: captura 1440 y 390 sin solapes.
5. **UI-06**: 100 % de controles < 44 px en pantalla táctil. Verificar con: medida de `getBoundingClientRect` >= 44 en `pointer:coarse`.

**Criterios de PASS:** los 5 anteriores + sistema de tokens único importado por las 5 páginas (UI-04) + cabecera común (UI-08). P2 puede ir en la iteración siguiente.

**Forbidden defaults para este producto:** tarjeta-galería genérica de meteo (icono de sol + grados), degradados decorativos, glassmorphism, hero marketing dentro de la consola (el hub actual de "Dos territorios. Un mismo motor de análisis." es marketing ajeno al trabajo del usuario en cuanto entra a Pirineo), emojis/iconos de nubes que sustituyan el estado oficial/modelo/dato.

**Contrato de diseño abreviado (Vigilancia / Pirineo móvil):**
- Usuario y trabajo: decidir salida o seguir una situación en el Pirineo, con guantes, a pie de coche o en refugio.
- Primer objeto de lectura: aviso oficial vigente + antigüedad del dato.
- Acción primaria: abrir Ruta y tiempo / ver cota en el corte.
- Densidad: compacta en escritorio, moderada en móvil (no compactar el área táctil).
- Prioridad responsive: se fijan estado del dato y tabs agrupadas; colapsan tablas en tarjetas; el mapa pasa a pantalla completa con etiquetas priorizadas.
- Evidencia de cierre: capturas 390/768/1440 de las 12 pestañas, estados cargando/error/caducado, test de overflow y de objetivos táctiles.

## 7. Orden de trabajo sugerido

1. UI-01 + UI-02 + UI-06 (día 1-2): viewport, doctype, overflow y tap-targets; test de regresión.
2. UI-03 (día 2): banner de estado de datos.
3. UI-04 + UI-07 + UI-08 (semana 1): `tokens.css` + `components.css`, cabecera común.
4. UI-05 + UI-11 (semana 1-2): etiquetado SVG/canvas con anti-colisión.
5. UI-10 (semana 2): reagrupar pestañas, sparkline en Ensemble.
6. UI-09, UI-12..16 al paso (S).

## 8. Resumen final (10 líneas)

1. Veredicto finish-gate: **FAIL/HOLD**; "es un lío" se explica por defectos estructurales, no de gusto.
2. P0: `pirineo_app.html` y `portinatx_app.html` no tienen `doctype` ni `viewport`: en móvil se dibuja a 980 px (escala 40 %), modo quirks, sin `lang`.
3. P0: al corregirlo, 5 de 12 pestañas Pirineo desbordan en horizontal a 390 px (hasta 1121 px de ancho).
4. P0: si falla la carga de `api/*.json`, la cabecera dice "esperando datos…" para siempre; no hay error ni reintento.
5. Cuatro sistemas de tokens para una marca: 5 fondos, 3 bordes, 3 textos, radios de 2 a 18 px, 25 tamaños de fuente, acento turquesa vs coral.
6. 100 % de los controles de la consola miden < 44 px (26-34 px); bordes de control a 1,35:1 de contraste.
7. Gráfico de corte vertical y hodógrafa con etiquetas superpuestas; mapa con rótulos solapados.
8. 12 pestañas planas mezclan decisión, análisis y auditoría; Atmósfera mide 5 456 px; Satélite/radar solo dice "no integrado".
9. Aciertos a conservar: Vigilancia (oficial/observación/diagnóstico), semáforos con texto, mono tabular, mapa propio offline, aviso de privacidad de Ruta.
10. Propuesta: `tokens.css` único (sección 4), 8 componentes, cabecera común, orden de trabajo de 2 semanas (sección 7); evidencias en `docs/ux-review/img/ui-*.png`.
