# 04 · Personas y accesibilidad (perfil PIRINEO)

**Revisor:** NEXUS · métodos de `design-persona-walkthrough` (Five-Second Test, LIFT, Fogg, dos voces) e `design-inclusive-visuals-specialist` (revisión de dignidad/claridad de lo visual: color, daltonismo, alternativas).
**Fecha de la prueba:** 2026-11-11, 23:40–00:10 UTC. Código en solo lectura.
**Entrada del usuario:** «es un lío».

## 0. Alcance, método y límites honestos

- **Producto real, no maqueta.** Se sirvió con `python3 -m http.server` una copia de `src/` (hub, `decidir/`, `pirineo/`, `pirineo/ruta/`) con los JSON reales descargados de la instantánea pública (`pirineo/api/*.json`, `portinatx/api/*.json`; mismos tamaños de archivo que el repositorio). Chromium vía Playwright: móvil 390 px (con y sin `isMobile`) y escritorio 1280 px. Foco, teclado, tamaño de objetivo y reflujo se midieron en el DOM renderizado.
- **axe-core 4.10.2** instalado por npm en el scratchpad (etiquetas wcag2a/2aa/21aa/22aa + best-practice), ejecutado en 6 vistas × 2 viewports y en las 11 pestañas del Pirineo. Ratios de contraste calculados con la fórmula WCAG 2.x; daltonismo con las matrices de Machado (ΔE76).
- **Esto es simulación cualitativa, no evidencia estadística.** Los monólogos de persona son hipótesis a validar con las sesiones de `docs/EVALUACION-USUARIOS-P1.md` (todavía no realizadas). Las cifras de tiempo son de mi navegación asistida (mínimos), no de usuarios.
- Marcas: **OBSERVADO** = medido o visto en el producto en esta prueba; **SUPUESTO** = inferencia razonable no verificada con usuarios reales ni en dispositivo físico.
- **Contexto temporal de los datos:** Pirineo con ciclo de 108 min (reciente, umbral 360); Portinatx con ciclo de 109 min (**caducado** para el umbral de 60 min). Eso condiciona qué ve cada persona.
- Capturas en `docs/ux-review/img/` (`a11y-*.png`, `px-*.png`).
- No se probó: lector de pantalla real (NVDA/VoiceOver/TalkBack; solo árbol de accesibilidad de Chromium), dispositivo físico, zoom del SO, modo alto contraste forzado.

---

## 1. Recorridos por persona

### Persona A · Jordi, esquiador de travesía (planifica ruta GPX)

```
Nombre: Jordi · 41 H · catalán, Puigcerdà
Situación: sale mañana de madrugada a la Tossa d'Alp desde La Molina; ya tiene el GPX en el móvil.
Google: «previsión viento nieve Tossa d'Alp ruta gpx»  · llega desde el hub
Dispositivo: móvil 390 px · Familiaridad: media-alta · Urgencia: horas
Miedos: viento en cresta, lluvia en vez de nieve, que la app me dé una falsa calma
Confía en: avisos de Meteocat/AEMET, boletín de aludes, números concretos
Decisión: rápido · Apego: evitativo (datos, sin florituras)
```

**Tarea:** saber si la ruta es viable a su hora de salida y qué dice lo oficial.

**Pasos reales (OBSERVADO):**
1. Hub → tarjeta «¿Qué necesitas saber ahora?» (la tarjeta solo muestra una flecha ↗, sin verbo de acción).
2. `/decidir/` → pulsa «Esquí y montaña». Carga 1,3 s.
3. Lee: titular «Estimación de AROME HD para Font-Romeu» (no da ningún número); la cota de copo y la nieve están en «Señales consultadas», **a 1860 px de scroll** (≈ 2,2 pantallas).
4. Busca «mi ruta»: **`/decidir/` no enlaza a la planificadora de rutas** (8 enlaces, ninguno a `ruta/`). Debe pulsar «Ver el observatorio completo» → `pirineo/#corte` (pestaña «Corte y cotas», 12 pestañas) → botón «Ruta y tiempo» arriba. 3 saltos y ~8 s con la página de 980 px (ver A11Y-01).
5. En `ruta/`: «Subir track GPX» → resultado. Tiempo total de la navegación asistida: ≈ 9,7 s hasta ver el resumen; un humano, ~45–90 s.
6. Resultado (GPX de prueba 5,7 km, +791 m): lluvia «moderada» en el km 0; viento «racha < 39 km/h», «Sin aviso de esta herramienta en todo el recorrido» pero 5,3 km «expuestos» a crestas; nieve «débil» solo en los últimos 100 m; «80 % del recorrido con perfil vertical incierto (posible inversión)».
7. La lista de avisos oficiales está en la posición 3072 px de 4050 y el aviso «no es un aviso oficial» es **lo último de la página** (pie, 3916 px).

**Monólogo de Jordi (voz persona):**
> «Vale, abro "Esquí y montaña"... me pone AROME no-sé-qué y Font-Romeu. Yo no voy a Font-Romeu. Scrolleo... "Nieve: UNKNOWN". ¿Unknown? ¿Que no hay nieve o que no lo saben? Mi ruta no está. ¿Dónde subo el track? ... Ah, "Ver el observatorio completo". Uf, doce pestañas. "Ruta y tiempo", ahí. Subo el GPX. Me dice "lluvia moderada" a la salida y "sin aviso de esta herramienta" en el viento. ¿Qué herramienta? ¿Y el aviso de verdad? Está abajo del todo, como siete pantallas más allá. Y dice "perfil incierto, posible inversión" en el 80 % — pues ¿me fío o no?»

**Analista — Five-Second Test (decidir):** Qué es: sí (título «La información relevante...» es marketing, no nombre del servicio). Para mí: sí, por los perfiles. Qué hago: **parcial**, el CTA es elegir perfil; el resultado queda bajo el pliegue.

| Fold | Estado | LIFT | Fogg | Notas |
|---|---|---|---|---|
| decidir fold 1 (0–844 px) | confuso | Clarity ↓ (hero de 300 px sin dato) | M alta, A baja, prompt visible sí | respuesta a 1860 px |
| decidir 2–3 | frustrado | Relevance ↓ (Font-Romeu por defecto) | A baja | «Nieve UNKNOWN» |
| ruta fold 1 | aliviado | Value ↑ (banner de privacidad) | A media | falta explicar el GPX |
| ruta resultado | alerta | Anxiety ↑ | A media | pastillas «verdes» + ventanas de aviso en el pie |

**Veredicto de Jordi:** Confianza 5/10 · Claridad 4/10 · Relevancia 6/10 (la ruta es útil; el resto, no). **¿Lo usaría?** Quizá, solo la ruta. **Casi me voy:** al no encontrar el enlace a la ruta. **Más enganchado:** al ver mis km y horas por peligro.

**Riesgo de malinterpretar (seguridad):**
- «Sin aviso de esta herramienta» usa la palabra **aviso** para una salida del propio motor; la misma palabra designa los avisos oficiales (PX-04).
- Con un track fuera de la rejilla (83 % sin datos) las pastillas siguen mostrando «sin nieve» / «racha < 39 km/h» y el texto «Sin datos en el 83 %» está en la frase, no en la pastilla (PX-05).
- El desglose «No evaluado: aludes…» es **excelente** (fortaleza).

### Persona B · Marta, propietaria de segunda residencia junto a un torrente

```
Nombre: Marta · 58 M · Barcelona, casa en Cerdanya junto a un torrente
Situación: lluvia fuerte en la previsión; quiere saber si el torrente puede crecer.
Google: «torrent casa Cerdanya aviso lluvia crecida» · Móvil 390 px · Familiaridad: baja
Miedos: inundación, que me digan «tranquila» y no lo esté
Confía en: avisos oficiales (Protección Civil), el pueblo, números claros · Apego: ansioso
```

**Pasos (OBSERVADO):**
1. `/decidir/`: la primera pastilla seleccionada es **«Casa junto a torrente»** (es su situación literal).
2. Muestra **«Datos antiguos · sin diagnóstico actual»**, ciclo de Portinatx (Ibiza). La ubicación «Portinatx · Ibiza» está a **995 px** de scroll. Con datos recientes, mostraría los 4 canales de **Ibiza**, no del Pirineo.
3. Prueba «Segunda residencia» → Pirineo: nieve/temperatura de un modelo para Font-Romeu (otro país), punto elegible entre 9 estaciones; **no hay su valle, ni torrente, ni lluvia observada** («Sin observación instrumental detallada», aunque `core.json` trae 34 observaciones y 5 AEMET + 8 XEMA + 7 Météo-France `ok`).
4. Tarjeta de avisos: «Avisos oficiales: 2 vigente(s) — Aviso de lluvias de nivel amarillo · Aviso de lluvias de nivel amarillo». No dice **zona, organismo ni hora**; el mismo texto para los 9 puntos.

**Monólogo de Marta:**
> «"Casa junto a torrente", ese soy yo. Pone "datos antiguos". ¿Antiguos de cuándo? Aviso oficial: "sin verificar". Vale, ¿entonces qué hago? Bajo y veo "Portinatx"... eso es Ibiza, ¿no? ¡Si mi casa está en Puigcerdà! Pruebo "Segunda residencia": "estimación de AROME HD para Font-Romeu". ¿Y mi torrente? "2 vigentes: lluvias amarillo". ¿De dónde? No me dice si es mi zona. Me están diciendo que no saben nada o que sí. Me da más miedo.»

**Analista:** Emoción: ansiosa. LIFT: Relevance ↓↓ (nombre del perfil promete torrente; datos son de otro territorio), Anxiety ↑. Cialdini:Authority débil (no nombra el organismo en la tarjeta). Fogg: M alta, A baja. CTA: sí, pero el CTA oficial («Consultar avisos oficiales») apunta a `meteofrance.com/meteo-montagne` aunque la residencia esté en España.
**Veredicto:** Confianza 3/10 · Claridad 3/10 · Relevancia 2/10. **¿Contactaría/usaría?** No. **Casi me voy:** al ver «Portinatx». **Más enganchada:** nunca.

**Riesgo de malinterpretar (seguridad, OBSERVADO):**
- Un propietario pirenaico junto a un torrente **no tiene perfil**: «Casa junto a torrente» se alimenta de Ibiza (PX-02, P0).
- El estado «vigente» de los avisos no se recalcula con la hora actual (PX-03, P0).

### Persona C · Anaïs, analista meteorológica

```
Nombre: Anaïs · 33 M · predictora en un servicio autonómico · escritorio 1280 px, 2 monitores
Google: «ensemble 15 días nieve Pirineo ECMWF ENS GEFS» · Familiaridad: alta · Urgencia: días
Miedos: que la herramienta tome una fracción de ensemble por probabilidad, números sin procedencia
Confía en: trazabilidad, edades de fuente, parámetros del modelo · Apego: evitativo, necesita densidad
```

**Pasos (OBSERVADO):** hub → Pirineo → Atmósfera (perfil por vertientes, 23 `UNKNOWN`), Modelos (3 modelos comparables), Ensemble · 15 días (familias ECMWF/ENS, GEFS, ICON-EPS; «fracciones de miembros, no probabilidades locales calibradas»), Forense («Skill fuera de muestra NO VERIFICADA», «Archivo prospectivo NO PUBLICADO»), Gobernanza (tabla de 16 fuentes con edad y motivo).

**Monólogo de Anaïs:**
> «Esto está bastante bien. Dice cuándo algo es modelo y no observación, y las fracciones no las llama probabilidad. En Modelos: AROME 13,8 mm, ICON 22,1, ECMWF 18,6: ya está el spread. Pero... en la pestaña Vigilancia me da "Cota copo 2619 m" y justo debajo, en el panel de modelos, "Cota de copo 2527 m". ¿Cuál? Y en Atmósfera, los niveles 1000 y 925 hPa son todo UNKNOWN: ya lo sé, están bajo el terreno, no es "desconocido", es "no aplica". Y no veo cómo descargar la serie.»

**Analista:** el perfil mejor servido. Fortalezas: separación epistémica explícita, edades por fuente, `UNKNOWN` no se convierte en 0. Debilidades: PX-06 (dos cotas), PX-07 (`UNKNOWN` por «bajo terreno»), PX-08 (doce pestañas sin jerarquía; la cinta de modelo se repite en todas las pestañas).
**Veredicto:** Confianza 8/10 · Claridad 6/10 · Relevancia 9/10. **¿Lo usaría?** Sí, como segunda pantalla. **Casi me voy:** Superficie, 1430 palabras en una pestaña. **Más enganchada:** Gobernanza.
**Riesgo de malinterpretar:** bajo; es la persona con menos riesgo (conoce la diferencia entre estimación y aviso).

### Persona D · Lucía, visitante nueva (no sabe qué es un «ensemble» ni «UNKNOWN»)

```
Nombre: Lucía · 27 M · turista, va a esquiar un fin de semana · móvil 390 px · Familiaridad: baja
Google: «tiempo Cerdanya fin de semana nieve» · Miedos: perderme algo importante o que me engañen
Apego: ansioso
```

**Pasos (OBSERVADO):** hub (jerga en el titular: «motor de análisis», «aprendizaje forense») → `decidir/` (eyebrow «Fase P0», «Interfaz de decisión», «instantánea», «ciclo»; titular «Sin buscarla entre 60 gráficos»).
Palabras que no entenderá, contadas en `decidir` y las consolas: `UNKNOWN` (inglés, 2 en decidir por vista; **23** en Atmósfera, 7 en Gobernanza), «ensemble», «nowcast», «forense», «cota de copo», «vertiente», «ciclo», «instantánea», «Render Free», «GitHub Pages» (este último, dentro del aviso de seguridad).

**Monólogo de Lucía:**
> «"La información relevante sin buscarla entre 60 gráficos"... ¿de qué? Elijo "Esquí y montaña" porque esquío. "Estimación de AROME HD". ¿AROME qué? "Nieve 24 h: UNKNOWN". Eso es inglés, ¿no? ¿Quiere decir que no hay nieve? "El punto está por debajo". ¿Por debajo de qué? ¿Puedo esquiar o no? Me aparece "Cota de copo 2619 m", ¿y eso qué es? Y abajo, letras pequeñas con "Render Free puede suspenderse". No sé qué es Render. Esto no es para mí.»

**Analista:** LIFT: Clarity ↓↓, Anxiety ↑ (la tarjeta amarilla y el recuadro «Límites» no explican qué hacer). Five-Second Test: Qué es **parcial**, para mí **sí**, qué hago **parcial**. Tiempo-a-respuesta útil: no alcanzable sin jerga.
**Veredicto:** Confianza 4/10 · Claridad 2/10 · Relevancia 5/10.
**Riesgo de malinterpretar:** (a) «Ciclo reciente» + verde puede leerse como «el tiempo es bueno/recomendable» y no como «el dato es reciente» (la etiqueta verde es de frescura, no de seguridad: la misma pastilla verde se reutiliza con otro significado en la ruta) (PX-09); (b) «UNKNOWN» se lee como «no hay nieve» o «no hay peligro» (PX-01); (c) «Avisos oficiales: 2 vigente(s)» sin zona puede leerse como «hay un aviso aquí» o, al revés, ignorarse.

### Matriz de contradicciones entre personas (trade-offs)

| Necesidad | Jordi (ruta) | Marta (torrente) | Anaïs (analista) | Lucía (visitante) |
|---|---|---|---|---|
| Primera pantalla | su ruta y avisos de su zona | qué pasa en mi valle | densidad, fuentes, edad | un veredicto en lenguaje llano |
| `UNKNOWN` | quiere «sin dato» | quiere saber qué hacer | lo valora (honesto) | no lo entiende |
| Aviso de seguridad | arriba, cerca del resultado | arriba | no lo necesita | en lenguaje humano |
| Pestañas | pocas | pocas | todas | ninguna |

Conclusión: `/decidir/` intenta servir a Lucía y Marta pero hereda la jerga de Anaïs; la consola de 12 pestañas sirve a Anaïs; **nadie sirve a Jordi de punta a punta** (le falta el puente decidir → ruta).

---

## 2. Hallazgos de personas (PX)

| ID | Sev. | Hallazgo | Evidencia | Recomendación | Esf. | Estado |
|---|---|---|---|---|---|---|
| **PX-01** | P1 | `UNKNOWN` (inglés, sin explicación) aparece como valor clave: «Nieve 24 h (modelo): UNKNOWN» en **los 9 puntos**. Además AROME HD devuelve `nieve24_cm: null` mientras ICON-EU y ECMWF dan `0.0`; `decision_cards.js` elige un único modelo y no cae al siguiente por campo. | Capturas `px-esqui-decidir-m-full.png`; `core.json` punto `font_romeu`: AROME `None`, ICON `0.0`, ECMWF `0.0` | Sustituir por «Sin dato de nieve de este modelo» y, si otro modelo tiene valor, mostrarlo con su nombre; glosario de una línea para `UNKNOWN` | S | OBSERVADO |
| **PX-02** | **P0** | **El perfil «Casa junto a torrente» (el que una propietaria pirenaica elige por nombre) proyecta Portinatx/Ibiza.** El dominio solo aparece en «Zona o punto» a 995 px. Y «Segunda residencia» (Pirineo) no tiene canales de lluvia observada ni torrente. Riesgo: un usuario del Pirineo lee datos de Ibiza como los suyos. | `px-casa-default-m.png`, `profiles.casa.domain='portinatx'` en `decision_cards.js` | Renombrar a «Casa junto a torrente · Ibiza (Portinatx)» o añadir selector de territorio previo; y crear caso Pirineo (lluvia/estaciones observadas ya existentes) o decir explícitamente «aún no disponible en el Pirineo» | M | OBSERVADO |
| **PX-03** | **P0** | **«Vigente» no se recalcula con la hora actual.** `mountainOfficial()` cuenta `w.vigente === true` del JSON (congelado en la emisión). A las ≈23:55 UTC (ciclo de 21:54): se mostraba «2 vigente(s)» incluyendo el aviso amarillo del Pirineo oscense **caducado a las 23:59 CET (22:59 UTC)**, y **no** se contaban el aviso de tormentas de Pyrénées-Orientales (desde 23:00 UTC; Font-Romeu está ahí), ni los de lluvias de Girona, Barcelona y el naranja de Huesca (desde las 00:00 CET). Con 6 h de margen de frescura, el desfase puede ser grande, y el texto «No constan avisos vigentes en este ciclo» (rama vacía) es literalmente cierto pero engañoso. | `core.json` `avisos[].vigente/desde/hasta`; `px-esqui-decidir-m-full.png`; `decision_cards.js` líneas de `mountainOfficial` | Recalcular `vigente` en cliente con `desde/hasta` y la hora actual; mostrar «próximos» (≤12 h) y «caducados» por separado; etiqueta «estado a las HH:MM» | S | OBSERVADO (código y datos) |
| **PX-04** | P1 | La tarjeta oficial no dice **organismo, zona ni nivel**: «Avisos oficiales: 2 vigente(s) · Aviso de lluvias de nivel amarillo · Aviso de lluvias de nivel amarillo» (duplicado, sin zona; mezcla Lleida y **Huesca**, a >100 km de la Cerdanya) y es idéntica para los 9 puntos. La tarea 1 del protocolo P1 («¿quién lo emite?») no es contestable. Además la ruta usa «Sin **aviso** de esta herramienta» con la misma palabra. | `px-esqui-decidir-m-full.png`; `pirineo/ruta` fila viento | Mostrar «AEMET · Pirineo de Lleida · amarillo · hasta 06:59»; filtrar por zona del punto; reservar «aviso» para lo oficial y llamar a lo propio «indicador de esta herramienta» | M | OBSERVADO |
| **PX-05** | P1 | En `ruta/`, con un track fuera del dominio (83 % sin datos) las pastillas siguen en la clase verde-baja («sin nieve», «racha < 39 km/h», «sin lluvia») y el «Sin datos en el 83 %» solo va en el texto adyacente. Con track dentro del dominio la pastilla de viento verde y «5,3 km de crestas» conviven. | `px-esqui-ruta-fuera-m.png`; texto de `hz` | Si `unknownFraction > 0`, pastilla «sin datos ≥ X %» en estilo rayado y sin color verde; no mostrar nivel máximo como «nada relevante» cuando falta datos | S | OBSERVADO |
| **PX-06** | P1 | Dos valores para «cota de copo» en la misma pantalla: 2619 m (bloque «Tres ejes», `cotas.cota_copo_m`) y 2527 m (cinta del modelo, hora 22:00). No se explica la diferencia (tiempo/modelo/vertiente). En `decidir` es 2619 m para todos los puntos de la vertiente (valor regional, no por punto) pero la etiqueta dice «el punto está por debajo». | `a11y-pirineo-movil-sin-viewport.png`; JSON `cotas` | Una sola cifra con su hora, modelo y alcance («regional, vertiente sur»); y decir la consecuencia («lluvia, no nieve, en este punto») | M | OBSERVADO |
| **PX-07** | P2 | `UNKNOWN` para niveles bajo terreno (1000/925 hPa en Atmósfera) mezcla «no aplica» con «dato ausente»; devalúa el significado de `UNKNOWN`. | Pestaña Atmósfera, 23 `UNKNOWN` | Usar «bajo terreno» / «n. a.» en esos niveles | S | OBSERVADO |
| **PX-08** | P2 | Doce pestañas sin jerarquía ni «modo básico/experto»; Superficie tiene 1430 palabras; la cinta de modelo/hora se repite en las 11 pestañas. Las etiquetas del hash no coinciden con las del enlace (`#diagnostico` = «Superficie», enlazada como «03 · Investigar»). | `p3.js`: palabras por pestaña | Agrupar en «Hoy / Ruta / Análisis»; cinta de modelo solo donde pinta algo | M | OBSERVADO |
| **PX-09** | P1 | **Estimación vs. oficial**: la pastilla verde «Ciclo reciente» (frescura) usa la misma semántica de color que «verde = bien» y se ve primero; el titular es «Estimación de AROME HD…» (nombre de modelo, no conclusión). La advertencia clave («esto no es un aviso oficial, no sabe de tu casa/ruta») está en 12,6 px al pie (2500 px de 2830), con jerga de infraestructura («Render Free», «GitHub Pages»). En `ruta/` aparece solo en el **último** elemento de la página (3916/4050 px). | `px-esqui-decidir-m-full.png`, `px-esqui-ruta-m-full.png` | Mover una línea «Estimación de un modelo, no aviso oficial. Compruebe AEMET/Météo-France» justo bajo el titular y bajo el resumen de ruta; quitar Render/GitHub del aviso de seguridad (dejar «actualización cada ~6 h, sin alertas»); pastilla de frescura en azul/gris neutro | S | OBSERVADO |
| **PX-10** | P1 | **Estado por defecto casi siempre «Datos antiguos» en 3 de 5 perfiles.** Portinatx exige ≤60 min; el hub dice «actualización automática cada 6 h». Con ciclo de 109 min hoy, «Casa», «Barca» e «Investigar» solo muestran «No hay datos verificables». Es seguro y honesto, pero inútil, y es el perfil seleccionado al abrir. | `px-casa-default-m.png`; hub «DATOS ANTIGUOS» | Cambiar el perfil por defecto según territorio/frescura; mostrar el último ciclo con rótulo «de hace 1 h 49 min, no vigente» para quien quiera ver lo que hubo; o alinear umbral y cadencia | M | OBSERVADO (hoy) / SUPUESTO (proporción del tiempo) |
| **PX-11** | P1 | **Sin puente decidir → ruta.** `decidir/` no enlaza a `pirineo/ruta/`; la persona de esquí/montaña da 3 saltos. | lista de enlaces de `decidir/` | Botón «Planificar una ruta con GPX» en las vistas Esquí y Segunda residencia | S | OBSERVADO |
| **PX-12** | P1 | La vista de montaña descarta observaciones disponibles: el eje «02 · Observación en montaña» es siempre «Sin observación instrumental detallada» (clase `unknown`) aunque `fuentes` marca AEMET 5, XEMA 8, MF 7 estaciones `ok`. El usuario lee «no hay mediciones». | `decision_app.html` rama `else axis('observed','unknown',…)`; JSON | Mostrar 2–3 estaciones cercanas con hora y edad | M | OBSERVADO |
| **PX-13** | P2 | El enlace «Consultar avisos oficiales» del Pirineo va siempre a Météo-France (`meteofrance.com/meteo-montagne`) aunque el punto esté en España/Andorra; para una persona de Puigcerdà o La Molina la fuente primaria es Meteocat/AEMET/SMA. | `official.pirineo` en `decision_app.html` | Enlace según país del punto | S | OBSERVADO |
| **PX-14** | P2 | Ruta: lenguaje de ventanas («hacia las 01:00–01:00», ventana de ancho 0), «80 % con perfil vertical incierto (posible inversión)» sin consecuencia práctica, hora de salida por defecto a la próxima cuarto de hora (madrugada si se abre de noche). | `ruta/` resumen | Texto «a las 01:00 ±15 min»; añadir «qué significa: la temperatura a tu cota puede errar varios °C» | S | OBSERVADO |

**Fortalezas observadas:** separación 01 Avisos / 02 Observado / 03 Estimación con borde discontinuo para `unknown`; «No evaluado: aludes, crecidas…» en la ruta; privacidad del GPX explicada; `Lo no evaluado NO es «sin riesgo»`; las tarjetas suprimen todo el ciclo cuando está caducado.

---

## 3. Accesibilidad WCAG 2.2 AA

### 3.1 Resultado axe-core (6 vistas × 2 viewports + 11 pestañas)

| Vista | Violaciones axe | Notas |
|---|---|---|
| Hub | 0 | |
| Decidir (todos los perfiles probados: casa, esquí) | 0 | |
| Ruta (con GPX) | `color-contrast` ×2 (serious): `#act`, `#pace` | ver A11Y-08 |
| Pirineo (todas las pestañas) | **`html-has-lang` (serious)** en las 12; `color-contrast` ×2 en Ensemble; `scrollable-region-focusable` ×1 en Superficie (solo escritorio) | |

axe **no** cubre: viewport ausente, modo quirks, tamaño de objetivo (WCAG 2.5.8 se midió a mano), comprensión del lenguaje, teclado en subir ficheros.

### 3.2 Contraste medido (ratio, texto ≥ 4,5:1; no textual/UI ≥ 3:1)

| Elemento | Ratio | Veredicto |
|---|---|---|
| Decidir · tinta/fondo | 16,3 | OK |
| Decidir · muted `#abc0c9` / fondo / panel | 9,8 / 8,5 | OK |
| Decidir · pastillas «reciente»/«antiguo» (verde `#b4e0c0`, ámbar `#ffd49a`) | 11,0 / 11,6 | OK |
| Decidir · anillo de foco `#88c9df` / panel | 8,8 | OK |
| Decidir · borde de controles `#314854` / panel | **1,68** | **Falla 1.4.11** para `select`/botones sin relleno distinto |
| Decidir · borde de la pastilla `#34624d` | 2,31 | decorativo (hay texto) |
| Pirineo/Ruta · muted `#8fa19f` / panel | 6,3 | OK |
| Pirineo · bordes `#26363b` / panel | **1,35** | falla 1.4.11 para campos/selects |
| Ruta · `select` (texto `#8fa19f` sobre campo nativo `#3b3b3b`) | **4,14** | **falla 1.4.3** (12,5 px, no es «texto grande»); axe lo mide como 1,97 sobre `#6b6b6b` (valor computado distinto al píxel real; se toma el píxel) |
| Pirineo · Ensemble `select` tinta `#e4ebe9` / `#6b6b6b` (axe) | 4,41 | borde-línea; el píxel real es ≈ 9,3; **dudoso/posible falso positivo** |
| Ruta · pastillas de nivel (`#0d1417` sobre c0–c4) | 6,3–10,5 | OK |
| Ruta · colores c0–c4 sobre `#10181c` (lienzo) | 6,0–10,1 | OK (≥ 3:1) |
| Ruta · «sin datos» `#6b7a7c` / lienzo | 4,02 | OK |
| Hub · muted / panel | 6,8–7,8 | OK |
| Hub · borde de tarjeta `#314450` | 1,58 | decorativo (tarjeta es enlace con texto) |

### 3.3 Daltonismo (ΔE76 entre niveles consecutivos; < 20 ≈ difícil)

| Par | Normal | Protan | **Deutan** | Tritan |
|---|---|---|---|---|
| c1 amarillo / c2 naranja | 36 | 25 | **11,5** | 25 |
| c2 naranja / c3 rojo | 37 | 35 | **21** | 26 |
| c0 verde / c3 rojo | 109 | **21** | **22** | 120 |

Niveles 1–3 del mapa y de las franjas del perfil de la ruta se distinguen casi solo por tono; con deuteranopía amarillo y naranja son casi indistinguibles. Las **pastillas** de la sección «Qué te vas a encontrar» y la tabla «Tramos afectados» llevan texto («débil», «fuerte»): mitigan. El **mapa** y las **franjas** (lienzo) **no**.

### 3.4 Hallazgos de accesibilidad (A11Y)

| ID | Sev. | Hallazgo | WCAG | Evidencia | Recomendación | Esf. | Estado |
|---|---|---|---|---|---|---|---|
| **A11Y-01** | **P0** | **`pirineo/` y `portinatx/` no tienen `<meta name="viewport">` ni `<!doctype html>` ni `lang`.** Solo existe `<meta name="claude:viewport-fit-sides">` (no estándar, no es viewport). En móvil, Chromium con `isMobile` hace layout de **980 px a escala 0,40** (`visualViewport.scale = 0.398`): el texto de 14 px queda en ≈ 5,6 px efectivos. Modo quirks (`BackCompat`). Decidir, hub, ruta sí lo tienen (`CSS1Compat`, 390 px). La consola del Pirineo es la que llega la persona de montaña desde el móvil (y el enlace «Ver el observatorio completo»). | 1.4.4, 1.4.10, 3.1.1 | `a11y-pirineo-movil-sin-viewport.png`; `p4.js`; `head` de `src/pirineo_app.html` | Añadir `<!doctype html><html lang="es">` y `<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">` en ambas consolas; revisar que el CSS responsive (ya hay `@media (max-width:600px)`) se activa | S | OBSERVADO (emulación Chromium; **SUPUESTO** que un teléfono real se comporta igual, es el comportamiento estándar) |
| **A11Y-02** | **P0** | **El selector de archivo GPX no es alcanzable con teclado.** El `<input type=file hidden>` queda fuera del orden de tabulación y el `<label for=file>` no es focalizable (`tabIndex = -1`); la secuencia Tab pasa de «← Panel» a «Ruta de demostración (sintética)». Un usuario de teclado o de lector de pantalla/switch no puede subir su ruta. | 2.1.1 | `kb.js`: «file input reachable by Tab? false» | Reemplazar por `<button>` que dispare `input.click()` y mantener el `input` visualmente oculto pero focalizable | S | OBSERVADO |
| **A11Y-03** | P1 | **Mapa y perfil de la ruta** (2 `<canvas>`) no tienen nombre ni alternativa; el tooltip con km, hora, altitud y nivel solo se abre con `pointermove` (ratón/táctil), no con teclado ni lector. La información equivalente existe en tabla, pero el mapa/perfil quedan sin acceso. | 1.1.1, 2.1.1, 1.4.13 | `canvas sin nombre 2`; sin `keydown` en `pirineo_ruta.html` | `role="img"` + `aria-label` con resumen; botones «anterior/siguiente punto» y `aria-live` con km/hora/nivel; la tabla «Tramos afectados» como alternativa declarada | M | OBSERVADO |
| **A11Y-04** | P1 | **Color como único canal en el lienzo** (niveles 1–3 con ΔE 11–25 bajo deuteranopía/protanopía). Las pastillas de texto mitigan solo en la sección 3. | 1.4.1 | tabla 3.3 | Añadir trazos distintos (discontinuo/grosor) o marcadores y letras/números sobre las franjas; paleta con diferencia de luminosidad (p. ej., amarillo claro vs naranja oscuro) | M | OBSERVADO (cálculo) |
| **A11Y-05** | P1 | **Región `aria-live="polite" aria-atomic="true"` es todo el panel** de Decidir (≈ 1370 caracteres, incluye el `select`, los enlaces y los botones). Cada cambio de perfil o de punto relee todo; `aria-labelledby="question"` además da nombre de región a un contenedor que cambia. | 4.1.3 | `sr.js`: «live region chars: 1367» | Limitar la región a un `role=status` con el titular + estado de datos; el resto como contenido navegable; mover el foco o anunciar «Perfil: Esquí y montaña, datos de hace 1 h 49 min» | S | OBSERVADO (código) / SUPUESTO (comportamiento de NVDA/VoiceOver) |
| **A11Y-06** | P1 | **Tamaño de objetivo < 24 × 24 px** (2.5.8): ruta: `range` 16 px de alto ×3, `select` 19 px ×2, enlace «← Panel» 20 px; Pirineo: `range` «Hora» 16 px; Decidir: enlaces de cabecera 20 px de alto (4); hub: «Open-Meteo» 16 px. Los botones principales miden 31–34 px (OK). | 2.5.8 | `a11y.js` | `min-height: 24px` (mejor 44) con relleno; ranges con `height:24px` | S | OBSERVADO |
| **A11Y-07** | P2 | **Reflujo a 320 px** (equivale a zoom 400 % en 1280): `decidir/` desborda 357 px (nav `.toplinks`); `ruta/` desborda 357 px (el bloque de carga/controles). Pirineo y hub no desbordan. | 1.4.10 | `a11y.js` «reflow 320» | `flex-wrap` en `.toplinks`; `min-width:0` y `min-width: min(150px,100%)` en `label.f`/`.big` | S | OBSERVADO |
| **A11Y-08** | P2 | **Contraste de `select` en Ruta** (4,14:1 sobre campo `#3b3b3b`) y bordes de controles 1,35–1,9:1 (Pirineo/Decidir). | 1.4.3, 1.4.11 | tabla 3.2 | Estilar `select`/input con fondo y borde propios (`border:1px solid #8fa19f`, ≥ 3:1) | S | OBSERVADO |
| **A11Y-09** | P2 | **Texto pequeño y tipografía fija en px**: 8 % del texto de Pirineo < 12 px (mínimo 11 px), 4 % en ruta; cuerpo fijo en `px` (14–15 px) en lugar de `rem`: respeta la preferencia de tamaño del navegador solo en parte (`rem` en decidir sí). | 1.4.4 | `a11y.js` histograma | `font-size: 1rem` base; mínimos 12 px; probar con tamaño de fuente de sistema al 200 % | S | OBSERVADO (medición) / SUPUESTO (zoom de fuente del SO) |
| **A11Y-10** | P2 | **Pirineo**: 15 paradas de tabulación antes del contenido (3 enlaces de cabecera + 12 pestañas), sin enlace «saltar al contenido»; pestañas como enlaces con `aria-current` (válido), pero **`hashchange` no se escucha**: botón Atrás/Adelante no cambia de pestaña, y el hash externo solo funciona en la carga. Contenedor con desplazamiento sin foco en Superficie (`.tbl`, axe `scrollable-region-focusable`). | 2.4.1, 2.1.1 | `kb.js`; `axe-out.json`; `grep hashchange` | `<a class="skip">`; listener `hashchange`; `tabindex="0"` + `role="region"` con nombre en tablas desplazables | S | OBSERVADO |
| **A11Y-11** | P2 | **Idioma mezclado sin marcar**: «Moderate thunderstorm warning» (aviso francés en inglés), `UNKNOWN`, `france` en minúsculas, nombres de modelo; ningún `lang` en el fragmento. | 3.1.2 | `a11y-pirineo-movil-sin-viewport.png` | Traducir los eventos conocidos o `lang="en"`; sustituir `UNKNOWN` por texto en español | S | OBSERVADO |
| **A11Y-12** | P2 | **Movimiento**: `prefers-reduced-motion` está respetado en Decidir y Pirineo (`transition:none!important`); **no** en el hub (`transition: transform .15s`, `translateY(-3px)` en hover/foco) ni en la ruta (no hay animación). | 2.3.3 (AAA)/buena práctica | `grep` de las 4 páginas | Añadir la misma regla al hub | S | OBSERVADO |
| **A11Y-13** | P2 | **Gráficos del Pirineo (SVG)**: 23 `svg`, todos con nombre o `aria-hidden` (axe sin errores); 3 con `role="img"`; la tabla «Hodógrafa/Perfil» tiene alternativa en tabla de niveles (con `UNKNOWN` por nivel). Aceptable; falta descripción larga del perfil térmico. | 1.1.1 | axe + `a11y.js` | Añadir `<desc>` o párrafo «T 9,3 °C a 850 hPa, 1,5 °C a 700 hPa…» | S | OBSERVADO |

**Qué funciona bien (OBSERVADO):** foco visible en todas las páginas (outline 2–3 px, ratios 8,8–10:1); orden de tabulación lógico en decidir; botones de perfil con `aria-pressed`; `lang="es"` en hub, decidir y ruta; `alert` en errores del GPX; tablas con encabezados; sin imágenes sin `alt`; contraste de texto general alto (≥ 6,3:1).

### 3.5 Lo que no se pudo verificar
- Comportamiento real de NVDA/JAWS/VoiceOver/TalkBack (solo árbol de accesibilidad de Chromium).
- Zoom del SO/tamaño de fuente de Android/iOS; modo de alto contraste de Windows (`forced-colors`): no hay reglas `forced-colors` en ninguna de las 4 páginas (**SUPUESTO**: los lienzos y las pastillas perderían significado).
- Dispositivo físico (A11Y-01 se basa en la emulación estándar de Chromium).
- Sesiones con personas (ver `EVALUACION-USUARIOS-P1.md`).

---

## 4. Prioridades sugeridas

1. **P0 (antes de recomendar a nadie):** A11Y-01 (viewport/doctype/lang), A11Y-02 (GPX por teclado), PX-02 (perfil «casa junto a torrente» ≠ Pirineo), PX-03 (`vigente` congelado).
2. **P1 (siguiente iteración):** PX-04/PX-09 (organismo, zona y aviso «no oficial» arriba), PX-05, PX-10/11/12, A11Y-03/04/05/06.
3. **P2:** el resto.

> Este documento no sustituye las sesiones con usuarios del protocolo P1; los hallazgos PX son hipótesis informadas por el producto real y los datos de las 23:40 UTC del 11-11-2026.

### Archivos de evidencia

`img/a11y-pirineo-movil-sin-viewport.png`, `a11y-decidir-foco-teclado.png`, `a11y-pirineo-foco-teclado.png`, `a11y-ruta-foco-teclado.png`, `a11y-ruta-demo-desktop.png`, `a11y-decidir-320-text-spacing.png`, `a11y-pirineo-320-text-spacing.png`, `a11y-ruta-320-text-spacing.png`; `px-esqui-*`, `px-casa-default-m*.png`, `px-barca-m-full.png`, `px-residencia-m-full.png`, `px-meteo-m-full.png`, `px-analista-*-d.png`, `px-visitante-*.png`.
