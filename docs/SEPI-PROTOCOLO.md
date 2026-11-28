# SEPI — protocolo de investigación (congelado el 28-11-2026)

**Estado:** protocolo metodológico congelado. Se aplica a todo resultado SEPI posterior a esta fecha. No es un aviso ni un pronóstico. Diseño científico en [`SEPI.md`](SEPI.md) e inventario de fuentes en [`SEPI-INVENTARIO-FUENTES.md`](SEPI-INVENTARIO-FUENTES.md).

## 0. Línea base y exposición previa

- **Línea base exploratoria e inmutable:** **SEPI F03 v1**, fusionada en `main` con el PR #66 (commit de fusión `cc73bb1`, 27-11-2026). Sus resultados y su documentación (sección «Fase 03» de `SEPI.md`) no se modifican ni se sobrescriben. Si un resultado posterior los contradice, la divergencia se publica como resultado.
- **Este protocolo no es un preregistro original del ranking.** Los rankings de la v1 ya se conocían al redactarlo. Toda decisión fijada aquí se tomó **después** de conocerlos y figura en el registro de decisiones (§10).
- **Exposición previa de las hipótesis.** H1–H5 y H7 siguen siendo prospectivas en cuanto a sus pruebas estadísticas formales, que no se han ejecutado. No son independientes del conocimiento previo de los rankings v1 ni de las fases 01–02: H6 y el contraste E–O ya se exploraron. Se declara esta exposición.
- **Tres versiones diferenciadas:**
  - **SEPI F03 v1:** exploratoria, PR #66.
  - **SEPI F03 v2:** reanálisis metodológico con este protocolo, comparación de sensibilidad e incertidumbre.
  - **SEPI-P:** validación predictiva con hindcasts, evaluación temporal fuera de muestra y control de fuga de información.

## 1. Objetivo y estatuto de la evidencia

Reconstruir, explicar y evaluar la predictibilidad de los inviernos nivales excepcionales del Pirineo oriental entre 1968–69 y 2025–26 (58 temporadas). Se separan dos productos: SEPI-D (diagnóstico retrospectivo) y SEPI-P (predicción ex ante). Quedan fuera la nieve artificial, la explotación de estaciones de esquí y los rankings comerciales.

Toda afirmación lleva una de tres clases:
- **E, evidencia documental o científica.** S2M es una simulación nivometeorológica semidistribuida con una heterogeneidad del forzamiento alrededor de 2002. La literatura relaciona la circulación y la precipitación orográfica con la nieve, pero no acredita ningún predictor antecedente único con habilidad demostrada en toda la región.
- **H, hipótesis** (§6).
- **R, resultado SEPI demostrado.** Solo cuenta lo que procede de una ejecución reproducible y de una validación independiente. **Todavía no hay ninguno para el ranking ni para la predicción.** Los 1.073 aludes que el ICGC contó en 2025–26 son evidencia institucional de actividad, no la demostración de un primer puesto nival.

**Reproducibilidad no es validación científica.** Un verificador independiente acredita que el cálculo es correcto, no que S2M represente la realidad observada.

## 2. Estado del proyecto a 28-11-2026

| Componente | Estado | Referencia |
|---|---|---|
| S2M CSV 1958–2026 | **Completado** (descargado y versionado por fecha de descarga) | `scripts/sepi/fetch_hist.py` |
| AERIS S2M v2020.2 y comparación de versiones | Pendiente | — |
| QUOT 66/09 y red nivo (NIVOSE) | **Auditados** | `audit_quot.py`, `audit_nivo.py`, `SEPI-INVENTARIO-FUENTES.md` |
| XEMA 2009–2026 | **Incorporado** | fase 01 |
| Ranking F3 original (v1) | **Exploratorio** | PR #66 |
| Ranking F3 v2 | Pendiente | este protocolo, §4 |
| Independencia observacional de las anclas | **UNKNOWN** | se desconoce qué estaciones asimila SAFRAN |
| Ruptura de 2002 | Parcialmente evaluada (solo interna a S2M) | falta el contraste con CERRA-Land y con estaciones estables |
| H6 | Exploratoria | fases 02 y 02b |
| H1–H5 y H7 | Pendientes de contraste formal (con exposición previa declarada) | §6 |
| SEPI-P | Pendiente de validación predictiva | §7 |
| Ransol, Núria anterior a 1985, NIVOBS y ERHIN | Pendientes de petición institucional | `SEPI-INVENTARIO-FUENTES.md` |

## 3. Dominio, unidad de análisis y fuentes

- **Unidad:** el invierno, del 1 de diciembre al 30 de abril, **identificado por su año de inicio** y con la etiqueta legible «1968–69». Sensibilidades: noviembre–mayo y DJF.
- **Dominios separados** (macizos S2M): Haute-Ariège 70, Andorre 71, Orlu 72, Capcir–Puymorens 73 y Cerdagne–Canigou 74, con Couserans 69 como control.
- **Vertiente sur** (Cerdanya catalana, Núria–Ripollès, Cadí–Moixeró): es un dominio observacional y modelado aparte, porque el S2M estándar no tiene macizos allí.
- **Cotas primarias** 1.800 y 2.100 m, en **llano, N 20° y NO 20°**, siempre por separado. Las demás cotas y orientaciones, como sensibilidad.
- No se asume equivalencia entre macizo, valle y punto observado.

| Fuente | Función | Restricción |
|---|---|---|
| S2M CSV operativo 1958–2026 | Columna vertebral de nieve | Versionar aparte de AERIS; verificar fechas efectivas y geometrías |
| AERIS S2M v2020.2 (1958–2021) | Forzamiento y nieve en NetCDF | Acceso completo pendiente; ruptura ERA-40/ARPEGE |
| Ransol-FEDA 99130004 (1.641 m) | Ancla observacional 1934–2002 | Solicitar datos originales; la automática desde 2003 no acredita espesor |
| QUOT 66/09 | Anclas francesas | Auditadas; la fecha de apertura no equivale a serie nival |
| Núria (1.970 m) | Espesor diario desde 01-02-1985, a las 08 h | Antes de 1985, no acreditado; serie no descargable |
| NIVOSE, NIVOBS, XEMA, ERHIN | Observaciones modernas | Inventario de puestos, asimilación y metadatos |
| CADTEP, CLIMPY v3, E-OBS, SIM | Control de temperatura y precipitación | No confundir T/P con espesor |
| CERRA-Land, ERA5-Land, Alonso-González | Sensibilidad entre modelos | CERRA desde 09-1984 |
| MODIS (Gascoin), Theia | Cobertura y línea de nieve | MODIS 2000–2015; no mide espesor |
| CPC, WeMO (UB), SSWC, ERA5, C3S | Explicación y predicción | WeMO, archivo pendiente; SSWC hasta 2023 |

## 4. Fases 0–3: adquisición, calidad y definición de invierno excepcional

**F0, congelación.** Este documento. Cualquier cambio posterior se registra en §10 con fecha y motivo.

**F1, adquisición.** S2M CSV y AERIS por separado, QUOT 66/09, catálogo nivo, peticiones institucionales, CERRA, ERA5-Land, SIM, CADTEP, CLIMPY, satélite e índices. Se construye una matriz estación × variable × año con días disponibles y procedencia.

**F2, ETL y control de calidad.**
- Se conservan el dato bruto inmutable y el linaje.
- Se separan:
  - HS: espesor, en cm.
  - HN: nieve nueva, en cm.
  - SWE: equivalente en agua, en mm.
  - Precipitación, en mm.
  - Temperatura, en °C.
  - Cubierta, como fracción.
- Se distingue entre cero real, traza y NA.
- No se eliminan extremos por un criterio estadístico aislado.
- No se usa S2M para rellenar observaciones que sirven para validarlo.
- **Cobertura por temporada:** al menos el 90 % de los días válidos **y ningún hueco de más de 7 días**. Se publican la cobertura y la sensibilidad con umbrales del 80 % y del 95 %.

**F3, invierno excepcional (decisiones congeladas).**

| Criterio | Decisión |
|---|---|
| Identificador | Año de inicio; etiqueta 1968–69 |
| Métricas | HS medio dic–abr, HS máximo, días con HS ≥30 cm y ≥100 cm (más SWE, fecha del máximo y duración como diagnósticos) |
| Índice | I = mediana de los percentiles de las cuatro métricas, con los empates promediados |
| Percentiles | Sobre los valores estacionales, nunca diarios; cuantiles lineales de tipo 7 |
| Excepcionalidad | **I > P90 de I**. Extremo: I > P95 (exploratorio). Deficitario: I < P10. Además, la excepcionalidad de cada métrica por separado |
| Métricas degeneradas (P90 = 0) | **Se conservan** en el índice principal. Como sensibilidad, se recalcula sin ellas. Los empates se documentan |
| Geometrías | Llano, N 20° y NO 20°, por separado |
| Referencia principal | Los 58 inviernos de 1968–69 a 2025–26 |
| Referencia alternativa | 1991–2020, como sensibilidad |
| Tendencia | Sensibilidad con anomalías sin tendencia lineal |
| Incertidumbre | Bootstrap por bloques de inviernos (ver abajo) |
| Agregado regional | No se calcula hasta comprobar la coherencia entre dominios |
| Independencia de las anclas | No se presupone |

**Dos incertidumbres distintas que no deben confundirse:**
- **Incertidumbre muestral del umbral climatológico:** cuánto cambia la clasificación de un invierno si la distribución de referencia se estima con otros inviernos. Se mide con un bootstrap por bloques de inviernos.
- **Estabilidad frente a las decisiones metodológicas:** cuánto cambia la clasificación al variar la definición, el tratamiento de las métricas degeneradas, la referencia, la tendencia o la geometría. Se mide con la tabla de sensibilidad.

**Ninguna de las dos cuantifica el error físico de S2M.**

**Candidatos históricos que se contrastan sin orden previo:** 1971–72, 1985–86, 1995–96, 2003–04, 2012–13, 2013–14, 2017–18 y 2025–26. Se aplica el mismo algoritmo a las 58 temporadas y se examinan también los inviernos deficitarios y los falsos positivos.

**Puertas G1 y G2.**
- **G1:** manifiesto de datos, pruebas de unidades y de calidad, matriz de cobertura y registro de rupturas.
- **G2:** ranking reproducible por estrato, con bandas de incertidumbre y sin ninguna afirmación ordinal que los datos no respalden.

## 5. Fase 4: validación de S2M

- **Tres niveles de contraste:**
  - espesor o SWE observados directamente;
  - cobertura y línea de nieve por satélite;
  - plausibilidad meteorológica independiente de temperatura y precipitación.
- **Emparejamiento estación–modelo:** cada estación se empareja con el macizo, la cota y la geometría que le corresponden. Se compara solo en periodos comunes.
- **Dependencia de la asimilación:** cada fuente se clasifica como **independiente confirmada**, **parcialmente dependiente** o **desconocida**. Nunca se le atribuye independencia por defecto.
- **Métricas:**
  - sesgo de HS, MAE, RMSE y Spearman estacional;
  - error en días ≥30 y ≥100 cm y en la fecha del máximo;
  - concordancia de decil;
  - POD, FAR y CSI.

  Intervalos por bootstrap agrupado por invierno o estación.
- **Ruptura de 2002:**
  - Contrastar los residuos S2M–estación estable y S2M–CERRA antes y después de 2002 (1984–2001 frente a 2002–2020), sin atribuirles causa de forma automática.
  - Repetir los rankings normalizados por subperiodo.
  - Comparar el CSV operativo con AERIS en el periodo común.
  - **Si CERRA o las estaciones necesarias no están disponibles, esta prueba queda explícitamente pendiente, sin bloquear el recálculo.**
- **Criterios G3 (propuestos, no son estándares publicados).** En los estratos con ≥15 inviernos de solape:
  - Spearman ≥0,7;
  - error menor que la climatología en las métricas primarias.
- **Clases de validación:**

| Clase | Criterio |
|---|---|
| A | Modelo y dos controles independientes concordantes, al menos uno directo |
| B | Una ancla directa concordante, o independencia incompleta o desconocida |
| C | Esencialmente modelo, sobre todo en la vertiente sur de 1968 a 1984 |
| UNKNOWN | Sin comparabilidad |

  Un estrato que no supera G3 no puede sostener una afirmación observacional fuerte.

## 6. Fase 5: hipótesis falsables (SEPI-D)

| ID | Hipótesis | Prueba o falsación |
|---|---|---|
| H1 | NAO, EA, EA/WR, SCAND y WeMO modulan la nieve de forma distinta según la vertiente | Modelos por dominio con interacción índice × vertiente; signo y estabilidad fuera de muestra |
| H2 | Los regímenes NW atlánticos y E/SE mediterráneos aportan nieve por rutas distintas | Clasificación objetiva con Z700, SLP, viento e IVT de ERA5; composiciones por evento con control de la temperatura |
| H3 | El frío y el nivel de congelación condicionan la conversión de precipitación en nieve, sobre todo entre 1.800 y 2.000 m | Interacción P × T y cota 0 °C; acumulación, fusión y lluvia sobre nieve por altitud |
| H4 | La SST mediterránea y atlántica modula la humedad disponible, condicionada por la circulación | Anomalías de SST, IVT y flujo de humedad, con control de estación y de régimen |
| H5 | ENSO, QBO, vórtice polar, SSW y bloqueo actúan como moduladores remotos, ni necesarios ni suficientes | Composites, rezagos predefinidos y modelos condicionales; eventos con y sin SSW |
| H6 | La persistencia y la alternancia de regímenes húmedos explican los extremos mejor que un único temporal o un índice medio | Rachas, matrices de transición y valor incremental por ablación (**exploratoria en las fases 02 y 02b**) |
| H7 | Inviernos con cinemática similar pueden divergir termodinámicamente (1995–96 frente a 2025–26) | Anomalías estandarizadas de T, SST, IVT, fase de la precipitación, SWE/HS y lluvia sobre nieve |

- **Cadena causal de trabajo:** estado planetario → océano y estratosfera → circulación sinóptica → persistencia y transiciones → orografía y mesoescala → balance del manto.
- **Estadística:** se estiman magnitudes con intervalos, no solo p-valores. FDR de Benjamini–Hochberg por familias predefinidas. Bootstrap o permutación temporal por bloques.
- **Índices del mismo invierno:** sirven para el diagnóstico, nunca para la predicción.
- **G4:** resultados reproducibles, n efectivo y publicación de las hipótesis rechazadas o inconclusas. No se afirma causalidad sin identificación.

## 7. Fase 6: evaluación predictiva (SEPI-P)

- **Objetivo:** probabilidad de invierno P90 por dominio y cota.
- **Fechas de emisión:** 1 de septiembre, 1 de octubre, 1 de noviembre y 1 de diciembre. Cada una es un experimento separado.
- **Datos admitidos:** solo lo disponible en la fecha de emisión, con los retrasos de publicación incluidos, y hindcasts con versión y periodo común verificados.
- **Fuga de información, prohibido como predictor:** las medias NAO o WeMO de DJF observadas después de la emisión, los SSW futuros y los reanálisis del invierno completo.
- **Baselines:** climatología fija entrenada en el pasado, climatología móvil o con tendencia y persistencia del invierno anterior.
- **Modelos:** regresión logística penalizada con pocas variables preespecificadas o probabilidades de ensemble calibradas. Los miembros y los estratos correlacionados no cuentan como inviernos independientes.
- **Validación:**
  - rolling-origin con entrenamiento estrictamente anterior;
  - umbral P90 y escalado estimados solo con el entrenamiento;
  - un test final temporal reservado;
  - LOYO solo como sensibilidad.
- **Métricas:** BSS frente a la climatología entrenada, log loss, calibración, ROC-AUC, PR-AUC (referencia: la prevalencia) y POD, FAR y CSI con umbrales fijados de antemano. Bootstrap por bloques y una simulación de potencia con prevalencia ~0,1.
- **G5:** solo se considera habilidad demostrada si el BSS es >0 fuera de muestra, con un intervalo favorable, sin degradar la calibración y de forma estable entre bloques. Si el intervalo incluye 0, la evidencia es inconclusa; si no mejora, se rechaza.

## 8. Backlog

| Tarea | Prioridad | Estado |
|---|---|---|
| T01 Congelar el protocolo y los dominios | P0 | **Hecho** (este documento) |
| T02 Descargar y versionar S2M CSV y AERIS | P0 | CSV hecho; AERIS pendiente |
| T03 Auditar QUOT 66/09 y NIVOSE | P0 | **Hecho** |
| T04 Solicitar Ransol, FEDA y AR+I | P0 | Pendiente (lo hace el titular) |
| T05 AEMET, ICGC y ERHIN | P0 | Pendiente (lo hace el titular) |
| T06 ETL, control de calidad y homogeneización | P0 | Parcial (S2M y QUOT) |
| T07 Rankings de los 58 inviernos | P0 | v1 exploratoria; v2 en curso |
| T08 Validación y ruptura de 2002 | P0 | Parcial; CERRA pendiente |
| T09 Controles de satélite y de T/P | P1 | Pendiente |
| T10 Índices WeMO, SSW y ERA5 | P1 | Pendiente |
| T11 Diagnóstico H1–H7 | P1 | H6 exploratoria; resto pendiente |
| T12 Hindcasts C3S y auditoría antifuga | P1 | Pendiente |
| T13 Benchmark de SEPI-P | P1 | Pendiente |
| T14 Archivos de EDF, SHF y otros | P2 | Pendiente (primero el inventario) |
| T15 Informe y paquete reproducible | P1 | Depende de G1–G5 |

## 9. Gobernanza epistemológica

- **Ficha de cada afirmación:** ID, clase E/H/R, fuente y versión, método, tamaño muestral, incertidumbre, fecha y estado PASS, REJECT o UNKNOWN.
- **Alcance de PASS:** solo la hipótesis y el dominio que se han evaluado realmente.
- **Conclusiones negativas:** forman parte del producto científico.
- **Resultados anteriores:** no se eliminan aunque los nuevos los contradigan.

## 10. Registro de decisiones y desviaciones

| Fecha | Decisión o desviación | Motivo | Conocía los rankings v1 |
|---|---|---|---|
| 26/27-11-2026 | Fase 03 v1: invierno etiquetado por año final; «excepcional» = todas las métricas no degeneradas ≥ P90; d100 excluido si P90 = 0; llano y N 20°; clases por coincidencia de tercil | Exploración inicial | — |
| 28-11-2026 | Etiqueta por año de inicio | Protocolo | Sí |
| 28-11-2026 | Excepcional = I > P90 de I (no confundir con I ≥ 0,9) | Protocolo | Sí |
| 28-11-2026 | Conservar las métricas degeneradas en el índice principal y dar la sensibilidad sin ellas (revierte la exclusión de la v1) | Evitar redefinir el objetivo a posteriori | Sí |
| 28-11-2026 | Se añade la geometría NO 20° | Protocolo | Sí |
| 28-11-2026 | Cobertura ≥90 % y ningún hueco de más de 7 días | Protocolo | Sí |
| 28-11-2026 | Referencia alternativa 1991–2020 y sensibilidad sin tendencia | Protocolo | Sí |
| 28-11-2026 | Independencia de las anclas UNKNOWN mientras no se documente la asimilación por SAFRAN; por tanto, ninguna clase A es posible hoy | Protocolo | Sí |
| 28-11-2026 | Umbrales G3 y G5 y particiones temporales como propuestas, no estándares | Protocolo | Sí |

## 11. Referencias nucleares

- Vernay et al. (2022), ESSD 14, 1707–1733 (S2M) y AERIS v2020.2 (doi:10.25326/37).
- Météo-France: S2M CSV, QUOT, red nivo y SIM (Licence Ouverte 2.0).
- Ransol-FEDA, histórico de FEDA, Núria (ICGC), CADTEP (Meteocat), CLIMPY v3, Alonso-González et al. (2018), MODIS (Gascoin), SSWC (NOAA) y E-OBS.
- La literatura conceptual de la v0.2 (Lemus-Canovas, Bonsoms, Esteban, López-Moreno, Gascoin, Pagès, Martínez-Villagrasa, Monnin, Dai) **está pendiente de reconciliar con el DOI y el texto original**. No se presenta como cita verificada de hipótesis individuales.
