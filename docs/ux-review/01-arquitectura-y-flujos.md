# Revisión UX 01 · Arquitectura de información, navegación y flujos (perfil Pirineo)

Método: UX Architect (estructura, jerarquía, contratos de navegación) + UX Researcher (hallazgos con evidencia, sin inventar datos de usuarios).
Fecha de la revisión: 2026-11-11. Solo lectura; no se ha editado código.

**Convención.** OBSERVADO = visto en el código o en una captura propia. SUPUESTO = inferencia que requiere validar con usuarios o en un dispositivo real. **No existe ningún dato de usuarios**: `docs/EVALUACION-USUARIOS-P1.md` declara «sesiones no realizadas» (OBSERVADO, línea 3). Toda afirmación sobre comportamiento de personas es SUPUESTO.

**Cómo se observó.** Se sirvió una copia de la web (con la estructura de `scripts/build_site.py`) con `python3 -m http.server` y se capturó con Playwright a 390 px y 1440 px. Los datos eran los de la instantánea pública del momento (ciclo del 11/11, 106 min de edad). Capturas, en `/tmp/claude-0/-home-user-meteoportinatx/4d9d0d8f-4519-5d3b-ad75-a74e12f7d7f3/scratchpad/`: `pir-390.png`, `pir-1440.png`, `decidir-esqui-390-full.png`, `hub-390.png`, `ruta-390.png`.

---

## 1. Diagnóstico en una frase

«Es un lío» porque el Pirineo tiene **cuatro puertas de entrada que responden a la misma pregunta con jerarquías distintas** (portal, Decidir, consola de 12 pestañas, Ruta), sin un orden claro entre ellas, y porque la consola mezcla en una misma barra tareas del usuario («Corte y cotas», «Puntos») con jerga de laboratorio («Gobernanza», «Laboratorio», «Forense»).

## 2. Inventario de lo que existe (OBSERVADO)

| Superficie | Ruta publicada | Qué hace | Tamaño |
|---|---|---|---|
| Portal | `/` (`src/nowcast_hub.html`) | CTA «¿Qué necesitas saber ahora?» + tarjetas Portinatx y Pirineo + enlace a «Sensores y vibración» + informes de zona + descargas | 41 líneas |
| Decidir | `/decidir/` (`src/decision_app.html`) | 5 perfiles, 3 ejes (aviso, observación, estimación), 1 punto del Pirineo | 119 líneas |
| Consola Pirineo | `/pirineo/` (`src/pirineo_app.html`) | 12 pestañas, ~30 tarjetas solo en «Atmósfera» | 679 líneas |
| Ruta | `/pirineo/ruta/` (`src/pirineo_ruta.html`) | GPX en navegador, 6 pasos numerados | 495 líneas |
| Dispositivo | `/dispositivo/` (`src/device_app.html`) | Vibración y sensores del móvil, experimental | 19 líneas |
| Informes de zona | `/zones/pirineo/`, `/downloads/` | Generados por `scripts/build_zones.py`, fuera del alcance visual | n/a |

## 3. Qué ve primero el usuario (recorrido de primera visita)

1. **Portal.** En 390 px, antes de llegar a las tarjetas hay: eyebrow, titular, párrafo, CTA de Decidir y un enlace suelto a «Sensores y vibración · experimental». La tarjeta del Pirineo queda **bajo el pliegue** (`hub-390.png`, OBSERVADO). El CTA de Decidir lista «Casa · Barca · Segunda residencia · Esquí · Análisis meteorológico»: cinco etiquetas de las que tres son costeras (OBSERVADO, `nowcast_hub.html`).
2. **Consola Pirineo.** Aterriza en **Vigilancia** (`pirineo_app.html:677`, por defecto o lo último guardado en `localStorage`). Lo primero es una tarjeta «Tres ejes» con seis casillas: «AVISOS: Fuentes AEMET», «OBSERVACIÓN ≤90 MIN: UNKNOWN», «DIAGNÓSTICO MODELO: 11/11, 22:00», «ANTIGÜEDAD CICLO 106 min», «CICLO FRESCO ≤6 H: SÍ (no es vigilancia continua)», «PUNTO: La Molina» (`pir-390.png`). No hay respuesta a «¿qué va a pasar en mi sitio?».
3. La pestaña **Territorio** (mapa de relieve), que el código marca como pieza central (`pirineo_app.html:7`, comentario «mapa de relieve como pieza central») y que no tiene `hidden` en el HTML (línea 160), **no es la que se ve**: queda tercera en la barra y el JS la oculta. Hay una contradicción entre la intención de diseño y el estado real (OBSERVADO).

---

## 4. Hallazgos

### IA-01 · P0 · La consola del Pirineo no declara viewport ni doctype
- **Evidencia (OBSERVADO):** `src/pirineo_app.html:1-3` empieza con `<meta charset>` sin `<!doctype html>`, sin `<html lang>` y sin `<meta name="viewport">` (`grep -c 'name="viewport"'` = 0; en `pirineo_ruta.html` = 1). Con emulación móvil de Playwright (`isMobile:true`, 390 px) la página mide 980 px y `document.compatMode` es `BackCompat` (quirks mode). Lo mismo ocurre con `portinatx_app.html`.
- **Por qué importa:** las capturas a 390 px «sin emulación» parecen correctas, pero en un móvil real la consola se renderiza a escritorio reducido y en modo quirks. Todas las reglas `@media (max-width:600px)` (p. ej. `pirineo_app.html:84`, el panel de chat) y `max-width:1000px` (línea 37) **no se activan**. Es probable que sea la causa principal de «es un lío» en el móvil (SUPUESTO sobre percepción; el hecho técnico es OBSERVADO).
- **Recomendación:** añadir `<!doctype html><html lang="es">` y `<meta name="viewport" content="width=device-width,initial-scale=1">` en `pirineo_app.html` y `portinatx_app.html`; revisar después regresiones en tablas y canvas.
- **Esfuerzo:** S.

### IA-02 · P0 · Pirineo no tiene una «pantalla de respuesta»: la primera vista es un panel de metadatos
- **Evidencia (OBSERVADO):** `pir-390.png` y `pir-1440.png`; `pirineo_app.html:119-125`. La tarjeta inicial presenta «OBSERVACIÓN ≤90 MIN: UNKNOWN» y «Nieve modelo (3 h): UNKNOWN» y cuatro metadatos de frescura (edad, ciclo fresco, diagnóstico, punto) con el mismo peso visual que los avisos. Los avisos (que sí son accionables) están en la segunda tarjeta, 7 líneas sin agrupar por zona.
- **Por qué importa:** el patrón correcto de DECISION-P0 («primero la pregunta, luego la evidencia») queda solo en `/decidir/`; quien entra por la consola recibe «tres ejes» antes que una conclusión. Un usuario esporádico ve dos UNKNOWN sin saber si es un fallo o lo normal (SUPUESTO).
- **Recomendación:** convertir Vigilancia en «Hoy en mi punto»: (1) selector de punto persistente, (2) una línea de conclusión («Aviso naranja vigente en Pirineo oscense; en La Molina: cota 2619 m, 2,8 mm/3 h»), (3) tres chips fuente/edad. Colapsar edad/ciclo/«no es vigilancia continua» en una sola línea de estado.
- **Esfuerzo:** M.

### IA-03 · P0 · Duplicación estructural Decidir ↔ Vigilancia ↔ Ruta (tres pantallas de «avisos», dos «puntos», dos «modelo»)
- **Evidencia (OBSERVADO):**
  - Avisos oficiales aparecen en Decidir (eje 01), en Vigilancia (`pirineo_app.html:123`), en Superficie (`:219`, «Avisos oficiales») y en Ruta (`pirineo_ruta.html:139`, «Avisos oficiales vigentes en el Pirineo»): **cuatro** lugares, con formatos distintos.
  - Selector de punto: Decidir (`#place`, 9 localidades, `decision_cards.js:places`), consola (Vigilancia «PUNTO», Puntos, Modelos), Ruta (otro concepto: tramo). No se comparte la elección entre páginas: Decidir no persiste perfil (decisión deliberada de privacidad, DECISION-P0 §5) pero la consola sí guarda pestaña en `localStorage` (`:677`), de modo que el comportamiento de memoria es inconsistente.
  - Los mismos datos (nieve 24 h, racha 24 h, cota de copo) están en Decidir y en Puntos/Corte.
- **Por qué importa:** el usuario no sabe cuál es «la buena»; si dos pantallas muestran un dato con distinta presentación o filtro, pierde confianza (SUPUESTO). Además cuatro implementaciones del mismo contenido multiplican el mantenimiento (OBSERVADO: el truncado «2 vigentes» de Decidir vs 7 filas en Vigilancia, ver IA-09).
- **Recomendación:** una única fuente de verdad de «Avisos» (un componente reutilizado) y un único selector de punto compartido por query string (`?p=la_molina`), no por almacenamiento. Decidir y consola deben leer del mismo contrato (`core.json`) con el mismo componente.
- **Esfuerzo:** M.

### IA-04 · P1 · Doce pestañas en una barra plana, con 1719 px de contenido en un viewport de 358 px
- **Evidencia (OBSERVADO):** `pirineo_app.html:102-115`; medición de Playwright `nav scrollWidth=1719, clientWidth=358` (390 px) y `1719/1408` en 1440 px: **también a 1440 px hay que desplazar la barra** y «Gobernanza»/«Laboratorio» quedan ocultas (`pir-1440.png` termina en «FORENSE»). Barra con `scrollbar-width:none` (línea 31): sin indicador de que hay más.
- **Por qué importa:** la ordenación mezcla niveles: Vigilancia (decisión), Satélite/radar (que es solo enlaces externos), Atmósfera (30 tarjetas), Territorio, Corte, Superficie, Puntos, Modelos, Ensemble, Forense, Gobernanza, Laboratorio. Cinco de las doce son de auditoría o ciencia (Modelos, Ensemble, Forense, Gobernanza, Laboratorio) y comparten rango con «Puntos» (SUPUESTO: un usuario no técnico no distingue «Modelos» de «Ensemble» de «Atmósfera»).
- **Recomendación:** agrupar en 4 secciones por tarea (ver §8): Hoy · Mapa · Detalle · Datos y método. Mantener las 12 vistas como sub-pestañas solo en el grupo «Detalle» y «Datos y método». Añadir degradado/flecha de desbordamiento.
- **Esfuerzo:** M.

### IA-05 · P1 · «Satélite / radar» es una pestaña de primer nivel que dice «NOT_INTEGRATED»
- **Evidencia (OBSERVADO):** `pirineo_app.html:126-135`: una caja `pov-unknown` con «NOT_INTEGRATED EN ESTA CONSOLA… `python3 src/nowcast.py zone fetch pirineo …`» y tres enlaces externos.
- **Por qué importa:** ocupa el puesto 2 de 12 y promete contenido que no existe; el aviso incluye una línea de comandos de terminal dentro de una pantalla de producto. Es honesto (valor del proyecto) pero el sitio equivocado para la honestidad: debería ser un enlace, no una pestaña (SUPUESTO sobre expectativa).
- **Recomendación:** mover los tres enlaces a un bloque «Radar y satélite oficiales (externos)» dentro de Hoy o Mapa, con la nota «no está integrado». Retirar el comando de terminal a la documentación.
- **Esfuerzo:** S.

### IA-06 · P1 · Terminología: jerga de laboratorio, estados en inglés técnico y mezcla de idiomas
- **Evidencia (OBSERVADO):**
  - Pestañas y títulos: «Gobernanza» (`:113`), «Laboratorio» (`:114`), «Forense» (`:112`, `:258`), «Señales contrarian» (`:244`), «Metaanálisis», «föhn», «Froude», «Tw0», «isocero», «700 hPa» en tarjetas visibles (`pir-1440.png`: «ISOCERO», «TW 0 °C», «FLUJO 700 HPA»).
  - Estados en inglés crudo y mayúsculas: `UNKNOWN`, `NOT_INTEGRATED` (`:128`, `:141`), `ESTÁNDAR/DIAGNÓSTICO/EXPERIMENTAL` en CSS (`:65`).
  - Avisos de MeteoAlarm sin traducir: «amarillo · Moderate thunderstorm warning · france» junto a «Aviso de lluvias de nivel amarillo · AEMET» (`pir-1440.png`).
  - Catalán/occitano/francés: topónimos (Puigcerdà, Formiguères, Pas de la Casa, Tossa d'Alp, Porté-Puymorens, Ordino-Arcalís) correctos; **no hay opción de idioma**: toda la interfaz es ES. SUPUESTO: la audiencia real del Pirineo oriental incluye personas catalanoparlantes/francófonas; nada en el repo mide su preferencia.
  - Dos nombres para el mismo concepto: «Investigar el episodio» (Decidir), «Análisis meteorológico» (portal), «Meteo» (DECISION-P0), «03 · Investigar» (nivel).
  - Etiquetas incoherentes: «Punto de referencia» (Decidir) / «Punto» (consola) / «Puntos de control» (`:193`) / «Puntos» (pestaña).
- **Por qué importa:** `UNKNOWN` en mayúsculas e inglés es la forma más repetida del estado vacío (aparece 23 veces solo en la pestaña Atmósfera según el recuento de texto de Playwright, orientativo porque la pestaña estaba oculta); para un usuario general suena a error del sistema, no a «sin dato» (SUPUESTO).
- **Recomendación:** glosario único: `UNKNOWN` → «Sin dato fiable» (con la razón en una línea y el icono «?»); `NOT_INTEGRATED` → «No disponible en esta web»; Gobernanza → «Fuentes y edad de los datos»; Laboratorio → «Simulador de rachas (solo tú)»; Forense → «Revisión de pronósticos»; mantener «föhn» con una explicación corta en tooltip y «Froude» solo en el nivel experto. Traducir (o al menos rotular «MeteoAlarm, en inglés») los eventos. Plantear ES/CA como segunda fase tras validar necesidad.
- **Esfuerzo:** M (glosario S; i18n L).

### IA-07 · P1 · Decidir: orden y estado vacío contradictorios en Pirineo
- **Evidencia (OBSERVADO):** `decidir-esqui-390-full.png`, `decision_app.html:76-93`.
  - El eje 02 «Observación en montaña» está **fijo en «Sin observación instrumental detallada»** para el Pirineo (`:82`: rama `else axis('observed','unknown',…)` siempre). Una de las tres cartas es un estado vacío estructural: no puede nunca contener dato aunque las estaciones AEMET/Météo-France existan en la consola (Superficie).
  - Eje 03 titula «Nieve: dato no disponible» mientras la lista de señales indica «Cota de copo 2619 m · el punto está por debajo» y «Precipitación 24 h 7,8 mm» (OBSERVADO): el titular destaca lo ausente y entierra lo útil.
  - La etiqueta verde «Ciclo reciente» encabeza una pantalla cuyos ejes 02 y 03 son UNKNOWN: el color positivo se refiere a la edad del ciclo, no a la calidad de los datos (SUPUESTO: puede leerse como «todo está bien»; fallo que `EVALUACION-USUARIOS-P1.md` tarea 3 pretende medir pero no ha medido).
  - El eje 01 muestra «2 vigente(s)» y repite el texto: «Aviso de lluvias de nivel amarillo · Aviso de lluvias de nivel amarillo» (`:81-83`, `mountainOfficial` corta a 2 eventos y no deduplica), omitiendo el aviso naranja visible en la consola.
- **Recomendación:** (a) eliminar el eje 02 vacío en Pirineo o rellenarlo con la estación más cercana del contrato `core.json` si existe; (b) titular del eje 03 con el dato disponible y marcar el no disponible como línea secundaria; (c) separar «Ciclo reciente» (edad) de la calidad del dato con un icono distinto; (d) deduplicar y ordenar avisos por nivel, mostrando «1 naranja, 6 amarillos»; (e) filtrar por zona del punto elegido (ver IA-09).
- **Esfuerzo:** M.

### IA-08 · P1 · Flujo de Decidir → profundización con enlaces que no cumplen el contrato documentado
- **Evidencia (OBSERVADO):**
  - `decision_app.html:96`: el destino «Ver el observatorio completo» solo añade ancla para `barca` (`#mar`), `meteo` (`#forense`) y `esqui` (`#corte`). **`residencia` y `casa` van sin ancla** (la consola abrirá la última pestaña guardada o Vigilancia). DECISION-P0 promete «Pirineo · Puntos y cotas» para segunda residencia (tabla, línea del perfil «Segunda residencia»).
  - Los pasos «02 · Seguir datos» y «03 · Investigar» (`:98-99`) llevan a `#puntos` y `#diagnostico` en Pirineo, pero DECISION-P0 asocia «Investigar» a Forense. El orden «01 Decidir → 02 Seguir → 03 Investigar» presenta como «niveles de profundidad» lo que en Pirineo son pestañas laterales sin jerarquía real.
  - Dentro de Decidir no hay ningún enlace a **Ruta**; el portal tampoco (`grep -n "ruta" nowcast_hub.html decision_app.html` = 0). La única puerta a Ruta es el botón «Ruta y tiempo» en la cabecera de la consola (`pirineo_app.html:101`).
  - El enlace «Decidir» de la consola está fijo a `#esqui` (`:97`), de modo que «Decidir» desde Pirineo siempre abre el perfil Esquí, también para quien entró como «residencia» (SUPUESTO sobre intención).
  - El perfil por defecto de Decidir es `casa` (Ibiza) (`:116`): un visitante del portal que pulsa el CTA principal cae en Portinatx aunque venga por el Pirineo; solo 2 de 5 perfiles son pirenaicos (`decision_cards.js` profiles).
- **Recomendación:** mapa de destinos explícito por perfil (residencia → `#puntos`, esquí → `#corte`, ruta → `/pirineo/ruta/`); añadir un sexto perfil «Salir a la montaña (ruta)» que enlace a Ruta; el CTA del portal debe preguntar primero el territorio (dos botones) o recordar el último perfil usado vía `?` en la URL, no por cookie.
- **Esfuerzo:** S–M.

### IA-09 · P1 · Los avisos oficiales no se filtran por la zona del usuario
- **Evidencia (OBSERVADO):** `pir-1440.png` lista siete avisos incluyendo «Pirineo oscense» (Huesca), «Prepirineo de Barcelona» y «Pyrénées-Orientales»; la nota de Ruta lo asume: «se muestran por zona, sin geolocalizarlos sobre tu ruta» (`pirineo_ruta.html:140`). Decidir cuenta los avisos vigentes de todo el Pirineo, no del punto elegido (`decision_cards.js:mountainOfficial` no usa `place`).
- **Por qué importa:** quien mira La Molina/Cerdanya ve un naranja que corresponde a Huesca: puede alarmarse o, tras varios falsos positivos, aprender a ignorar la sección (SUPUESTO).
- **Recomendación:** asociar cada punto a su zona de aviso (Pirineo de Girona/Lleida, Pyrénées-Orientales, Andorra) y mostrar primero «En tu zona» y luego «Resto del Pirineo» plegado.
- **Esfuerzo:** M (requiere mapeo punto→zona en datos).

### IA-10 · P1 · Atmósfera concentra ~30 tarjetas y 3 000+ caracteres de texto
- **Evidencia (OBSERVADO):** conteo de Playwright (indicativo, tabla oculta al medir): `atmosfera` = 30 `.card`, 3 673 caracteres; `extendido` 3 tarjetas, 1 905; `gobernanza` 7 coincidencias de estados vacíos; frente a `mapa` 1 tarjeta, 212 caracteres. `pirineo_app.html:136-158`: tres secciones («Perfil atmosférico detallado», «Termodinámica y viento», «Perfil a 700 hPa y cotas por vertiente») con selector de vertiente y control de hora propio (`pa-side`, `pa-hour`) que **no es el mismo control de hora** que el del mapa o los modelos.
- **Por qué importa:** densidad máxima en la pestaña más técnica, hora y punto reiniciados entre pestañas (SUPUESTO: se pierde contexto al cambiar de pestaña; verificar si el estado `S` lo conserva).
- **Recomendación:** una única barra fija «Punto · Hora · Vertiente» común a Mapa/Corte/Atmósfera/Modelos; el contenido de Atmósfera en acordeones (cerrados salvo «Cota de nieve y isocero»).
- **Esfuerzo:** M–L.

### IA-11 · P1 · Estados de dato viejo, ausente y desconocido: tres tratamientos distintos
- **Evidencia (OBSERVADO):**
  - Portal: «Último ciclo: … · DATOS ANTIGUOS» solo en texto, umbral 6 h para Pirineo (`nowcast_hub.html`, script).
  - Decidir: el umbral de 360 min suprime todo el contenido del ciclo y pinta «Datos antiguos · sin diagnóstico actual» (`decision_cards.js:unknownFor`), eliminando lo que sí es válido (p. ej. cota de copo).
  - Consola: muestra «CICLO FRESCO ≤6 H: SÍ» como una casilla más y mantiene todos los datos visibles aunque el ciclo sea viejo (SUPUESTO sobre el caso viejo: no se pudo reproducir con datos viejos en esta revisión; ver código, no capturas).
  - Formato de hora: Decidir «11/11/26, 21:54» (zona del navegador, `toLocaleString` sin `timeZone`, `decision_app.html:69`) frente a consola «mié 11, 22:54» (hora de Madrid). **Dos horas distintas para el mismo ciclo** en la misma sesión (OBSERVADO en las capturas; en esta revisión la diferencia procede de que el navegador de prueba está en UTC; para un usuario en Madrid no se vería, pero sí para quien viaje o abra el enlace desde otra zona).
  - El umbral de «reciente» es 6 h para Pirineo y 1 h para costa, y en la misma frase se avisa de que «publicación periódica ≈6 h» (DECISION-P0 §3 y notice de Decidir): con la cadencia de publicación igual al umbral, el estado «Datos antiguos» es el estado normal justo antes de cada publicación (SUPUESTO; no hay datos de uptime en el repo).
- **Recomendación:** una semántica única con tres niveles visibles en todas las pantallas: fresco (verde), viejo con datos visibles pero en gris y rotulado con la edad en cada tarjeta (ámbar), sin dato (guion + razón). Hora siempre en `Europe/Madrid` con el huso explícito («22:54 CET»). Mantener visible lo que no depende del ciclo (cota, mapa) con la etiqueta de edad.
- **Esfuerzo:** M.

### IA-12 · P2 · Navegación entre páginas inconsistente (migas, retorno y cabeceras distintas)
- **Evidencia (OBSERVADO):**
  - Decidir y Dispositivo usan cabecera «METEOPORTINATX · Observatorios · Ibiza · Pirineo» (`decision_app.html:31`); la consola usa botones «Decidir» y «← Observatorios» (`pirineo_app.html:97-98`) sin marca ni enlace a Ibiza; Ruta usa solo «← Panel del Pirineo» (`pirineo_ruta.html:72`) y desde Ruta no hay enlace a Decidir ni al portal.
  - Tres diseños visuales: Decidir/portal/dispositivo (Inter-like system-ui, 15-16 px, tarjetas redondeadas 14-18 px), consola (Saira Condensed + Public Sans + IBM Plex Mono, radios de 4-6 px, cargadas desde Google Fonts, `pirineo_app.html:5`), Ruta (variante de la consola). Decidir y consola tienen **sistemas de color distintos** para la misma señal (ámbar `--amber:#ffd49a` vs `--w:#e8be33`).
  - El botón «Decidir» de la consola lleva a `#esqui` fijo; el botón «Ruta y tiempo» es el único acceso a Ruta. En 390 px ambos botones se apilan antes del título (`pir-390.png`): «Decidir» y «← Observatorios» pequeños sobre «Pirineo Nowcast».
- **Por qué importa:** cambiar de página se siente como cambiar de producto (SUPUESTO); es una causa visual directa de «desordenado».
- **Recomendación:** una barra superior común de 3 elementos (Hoy · Mapa y datos · Ruta) + territorio (Ibiza/Pirineo) en todas las páginas; compartir tokens de color y tipografía (`tokens.css`).
- **Esfuerzo:** M.

### IA-13 · P2 · Ruta: flujo largo y numeración visible pero sin atajo al resultado
- **Evidencia (OBSERVADO):** `pirineo_ruta.html:81-136`: pasos 1-6 más «Avisos», «Límites». En 390 px (`ruta-390.png`) el primer pliegue contiene solo carga de GPX y 4 controles (hora, actividad, factor de ritmo, pausas, origen del ritmo) antes de ver ningún resultado. El botón «Ruta de demostración (sintética)» es secundario pero es la forma más rápida de comprender la herramienta. Lo más valioso (paso 3 «Qué te vas a encontrar, por peligro») está tras la entrada y los controles. La nota de privacidad ocupa el primer lugar visual; el titular de la cabecera repite el nombre del modelo en crudo («meteofrance_arome_france_hd», OBSERVADO en `ruta-390.png`).
- **Recomendación:** colapsar «Actividad/Factor/Pausas/Origen» en «Ajustes avanzados»; mostrar el resumen (paso 3) en cuanto haya track; reemplazar el identificador de modelo por «AROME HD»; privacidad en una línea con icono, no en una tarjeta destacada.
- **Esfuerzo:** S–M.

### IA-14 · P2 · Coherencia Portinatx ↔ Pirineo: misma estructura prometida, estructuras distintas
- **Evidencia (OBSERVADO):** README: «Ambos perfiles comparten adquisición modular, diagnósticos, cobertura e informes. La paridad completa sigue en desarrollo»; PIRINEO-OBSERVATORIO-061: «Paridad de navegación, presentación y trazabilidad con Portinatx». Hub: dos tarjetas con la misma forma (`data-area="sea"/"snow"`), buen patrón. Decidir: dos territorios mezclados en el mismo selector de 5 perfiles. Anclas compartidas: Decidir hace `pages[domain]+#vigilancia` para Portinatx y `#puntos` para Pirineo como «Seguir datos»: **el mismo nombre de nivel apunta a vistas con distinta función** (Vigilancia en costa, Puntos en montaña).
- **Por qué importa:** quien aprende la navegación en uno de los territorios no puede transferirla (SUPUESTO).
- **Recomendación:** definir un esqueleto de pestañas comunes con los mismos nombres y orden (Hoy · Mapa · Detalle · Fuentes) y que cada territorio cambie solo el contenido; Pirineo excluye el mar sin cambiar la estructura. Eliminar «Pirineo» y «Ibiza» de la lista de perfiles de Decidir y tratarlos como filtro (territorio → situación).
- **Esfuerzo:** L.

### IA-15 · P2 · Acciones de operador visibles en la interfaz pública
- **Evidencia (OBSERVADO):** `pirineo_app.html:101`: botones «Actualizar y publicar» y «Preguntar a Claude» (ambos `hidden` por defecto, visibles solo si el backend local los habilita) junto a «Ruta y tiempo» en el mismo grupo `.actions`, con el mismo estilo `.btn.act`. Decidir añade «Volver a consultar» al mismo nivel que los enlaces de navegación (`decision_app.html:47`).
- **Por qué importa:** en la instalación local el operador y el lector comparten barra; botones de «publicar» al lado de navegación de lectura pueden pulsarse sin querer (SUPUESTO).
- **Recomendación:** mover acciones de operador a un menú «Herramientas» separado; dejar «Actualizar» como icono con la edad del dato.
- **Esfuerzo:** S.

### IA-16 · P2 · Mensajes de límites y legales repetidos en cada pantalla
- **Evidencia (OBSERVADO):** «no es vigilancia continua» / «no sustituye avisos oficiales» aparecen en: portal (`footer` + hero), Decidir (lede + `.notice` de 6 frases), Vigilancia (cuatro veces: casilla «ciclo fresco», `src`, `src`, aviso de avisos), Ruta (nota de avisos + footer). Es correcto como política, pero repetido más de quince veces sobre el mismo mensaje.
- **Por qué importa:** la repetición acostumbra a no leerlo (SUPUESTO); el mensaje crítico («un dato ausente no es calma») pierde peso frente al texto de relleno.
- **Recomendación:** un único bloque estándar «Cómo leer esto» (3 viñetas) enlazado desde un icono «i» en cada tarjeta, y dejar en pantalla solo el aviso específico de esa vista.
- **Esfuerzo:** S.

---

## 5. Lo que ya funciona (no tocar)

- La separación epistémica de tres ejes (oficial / observado / estimado) y su vocabulario («NO es observación», «el punto está por encima/por debajo») está bien pensada y coherente con DECISION-P0 (OBSERVADO).
- El portal usa el mismo patrón de tarjeta para ambos territorios y avisa de la edad del ciclo con texto (OBSERVADO, `nowcast_hub.html`).
- Decidir en 390 px es una sola columna legible, con objetivos táctiles amplios y sin desbordamiento horizontal (`decidir-esqui-390-full.png`; `scrollWidth=390`, OBSERVADO).
- Ruta: privacidad explícita («tu track no sale de este navegador») y numeración de pasos son buenos patrones (OBSERVADO).
- Ninguna de las páginas lanzó errores de JavaScript en el arranque (OBSERVADO, `pageerror` vacío en las 12 capturas).

## 6. Lo que NO se pudo evaluar

- No hay datos de uso ni sesiones con usuarios (SUPUESTO todo lo relativo a comprensión). El protocolo de P1 está redactado pero sin ejecutar: se recomienda ejecutarlo **antes** de rediseñar, añadiendo dos tareas pirenaicas: «¿Cuál es la cota de nieve para tu pueblo?» y «¿Hay algún aviso para tu zona?».
- No se ha comprobado el comportamiento con datos viejos o ausentes de extremo a extremo, solo por lectura de `decision_cards.js` (`unknownFor`) y por la propia ausencia de `metar` y `cnp` en el estado actual («Puntos: Open-Meteo · sin datos: metar, cnp», `pir-1440.png`).
- Contraste y teclado: no se midieron en esta revisión (cubierto, en su caso, por la revisión de accesibilidad).

## 7. Prioridad propuesta

| Orden | ID | Sev. | Esfuerzo | Acción |
|---|---|---|---|---|
| 1 | IA-01 | P0 | S | viewport + doctype en consola |
| 2 | IA-08 | P1 | S | anclas y enlace a Ruta desde Decidir/portal |
| 3 | IA-05, IA-15, IA-16 | P1/P2 | S | sacar «satélite» de pestañas; separar operador; un solo aviso legal |
| 4 | IA-06 | P1 | S–M | glosario ES (UNKNOWN → «Sin dato fiable») |
| 5 | IA-07, IA-11 | P1 | M | semántica única de frescura; arreglar Decidir/Pirineo |
| 6 | IA-02, IA-03 | P0 | M | «Hoy en mi punto» + componente de avisos único |
| 7 | IA-04, IA-10, IA-12 | P1/P2 | M | reagrupar pestañas, barra común, tokens |
| 8 | IA-09 | P1 | M | avisos por zona |
| 9 | IA-14 | P2 | L | esqueleto común Ibiza/Pirineo; i18n CA |

## 8. Mapa de navegación propuesto (simplificado)

Principio: **una pregunta por pantalla, de lo accionable a lo técnico**, misma estructura para Ibiza y Pirineo, un selector de punto global que viaja en la URL (`?p=la_molina`).

```
MeteoPortinatx
├── Inicio  (/)
│     ¿Dónde? [ Ibiza ]  [ Pirineo ]   (recuerda el último en la URL, sin cookie)
│
├── PIRINEO  (/pirineo/)            barra común:  Hoy · Mapa · Ruta · Detalle · Fuentes
│   ├── Hoy  (antes Vigilancia + Decidir)
│   │     Punto ▾ (9 localidades)  ·  Situación: [Casa] [Esquí/montaña] [Salir de ruta]
│   │     1 línea de conclusión + cota, nieve, viento, lluvia del punto
│   │     Avisos en tu zona (nivel, organismo, vigencia) · resto del Pirineo (plegado)
│   │     Estado: edad del dato · fuente · «Sin dato fiable» con motivo
│   ├── Mapa  (antes Territorio + Corte y cotas)  capas: relieve · cota · temp · precip · racha
│   ├── Ruta  (/pirineo/ruta/)  Subir GPX o demo → resumen por peligro → perfil → tramos
│   ├── Detalle (sub-pestañas)
│   │     Atmósfera · Modelos · Ensemble 15 días · Superficie (estaciones, inversión, föhn)
│   └── Fuentes y método  (antes Gobernanza + Forense + Laboratorio + Satélite/radar enlaces)
│         Edad y estado por fuente · Revisión de pronósticos · Simulador de rachas · Radares oficiales (externos)
│
├── IBIZA  (/portinatx/)            misma barra: Hoy · Mapa · Ruta (n/a) · Detalle · Fuentes
│
└── Herramientas (pie de página, no en la barra principal)
      Informes de zona · Descargas · Sensores del móvil (experimental)
```

Reglas de contrato:
1. «Decidir» deja de ser una página aparte y pasa a ser la vista **Hoy** de cada territorio (los 5 perfiles se convierten en un filtro de situación, no en una página con territorio mezclado).
2. Máximo 5 elementos en la barra principal; ninguna pestaña con texto de estado como `NOT_INTEGRATED`.
3. Un solo componente de avisos, un solo selector de punto, una sola semántica de frescura (fresco / viejo / sin dato) y una sola hora (Madrid, con huso).
4. Aviso legal en un único lugar enlazado («Cómo leer esto»); en pantalla solo lo específico.
5. Todos los destinos del portal y de «Decidir» son rutas con ancla verificable por test (extender `tests/test_decision_location_browser.py` para comprobar que cada perfil abre la pestaña prometida).
