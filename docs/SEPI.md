# SEPI — inviernos de nieve excepcional en el Pirineo oriental

**Estado:** línea de investigación experimental. Diseño v0.3 y resultados de las fases 01, 02, 02b (26-11-2026) y 03 (27-11-2026). Cada fase la ha revisado un agente verificador independiente y sus correcciones están aplicadas. **No es un aviso ni un pronóstico**, y no sustituye a Météo-France, AEMET, Meteocat ni al SMA. Ningún modelo SEPI está validado; no se emite ninguna probabilidad de invierno excepcional.

<<<<<<< HEAD
Scripts y reproducción: [`scripts/sepi/`](../scripts/sepi/README.md). Inventario de fuentes 1968–2026: [`SEPI-INVENTARIO-FUENTES.md`](SEPI-INVENTARIO-FUENTES.md). **Protocolo congelado el 28-11-2026:** [`SEPI-PROTOCOLO.md`](SEPI-PROTOCOLO.md); predicción estacional (borrador, sin congelar): [`SEPI-P-PROTOCOLO.md`](SEPI-P-PROTOCOLO.md), con su ingesta opcional en [`SEPI-EARTHKIT.md`](SEPI-EARTHKIT.md); la fase 03 de este documento es la v1 exploratoria e inmutable. Recálculo según el protocolo: [`SEPI-FASE03-V2.md`](SEPI-FASE03-V2.md) y comparativa v1↔v2 en [`SEPI-FASE03-COMPARATIVA.md`](SEPI-FASE03-COMPARATIVA.md). Climatologías bimestrales descriptivas (F04): [`SEPI-FASE04-CLIMATOLOGIA.md`](SEPI-FASE04-CLIMATOLOGIA.md).
=======
Scripts y reproducción: [`scripts/sepi/`](../scripts/sepi/README.md). Inventario de fuentes 1968–2026: [`SEPI-INVENTARIO-FUENTES.md`](SEPI-INVENTARIO-FUENTES.md). **Protocolo congelado el 28-11-2026:** [`SEPI-PROTOCOLO.md`](SEPI-PROTOCOLO.md); predicción estacional v0.4 (candidato a congelación): [`SEPI-P-PROTOCOLO.md`](SEPI-P-PROTOCOLO.md), con su ingesta opcional en [`SEPI-EARTHKIT.md`](SEPI-EARTHKIT.md); la fase 03 de este documento es la v1 exploratoria e inmutable. Recálculo según el protocolo: [`SEPI-FASE03-V2.md`](SEPI-FASE03-V2.md) y comparativa v1↔v2 en [`SEPI-FASE03-COMPARATIVA.md`](SEPI-FASE03-COMPARATIVA.md).
>>>>>>> origin/main

## Resumen
- Con datos abiertos (XEMA, Météo-France, NOAA CPC) se ha construido un catálogo objetivo de 17 inviernos (2009–10 a 2025–26). 2017–18 y 2025–26 son los excepcionales en el Pirineo catalán oriental; el contraste este–oeste separa inviernos de sesgo mediterráneo (2016–17, 2025–26, 2019–20) y atlántico (2013–14, 2012–13).
- Ningún índice de teleconexión estacional (NAO, EA, EA/WR, SCA, AO, ENSO) explica la nieve del este tras corregir por pruebas múltiples.
- La nieve de cada vertiente sigue a su precipitación total, y el contraste de nieve este–oeste sigue al reparto de precipitación entre ambas. Con 17 inviernos **no se detecta** aportación adicional de métricas de régimen o de persistencia (H6) medidas con el viento de una estación. Los intervalos son anchos: no se descarta un efecto moderado.
- La señal de transiciones NW↔E/SE es frágil (depende de los límites de sector). Decidirla exige regímenes ERA5 a 700 hPa.
- **Fase 03, 58 inviernos (1968–69 a 2025–26) con S2M y anclas observadas:**
  - No hay un único «mejor invierno» en los macizos franceses y Andorra: el orden depende del dominio y de la cota.
  - 2025–26 es el primero de 58 en Cerdagne–Canigou a las dos cotas. En Capcir empata con 1971–72 a 1.800 m, y en Haute-Ariège queda el 25.º.
  - 1971–72, 1980–81, 1995–96, 2004–05 y 2013–14 son los otros candidatos.
  - Las anclas que lo apoyan probablemente están asimiladas por SAFRAN: no son una validación independiente.
  - De 1969 a 1984, el orden depende casi solo del modelo.
- Hallazgos de datos reutilizables: el cambio de unidades de la variable 38 de la XEMA el 15-11-2021 y que la nivosa de Canigou no representa el flujo de cresta.

# Diseño v0.3

**Pregunta de fondo:** ¿existen estados antecedentes del sistema océano–atmósfera–estratosfera que aumenten la probabilidad de secuencias persistentes de regímenes favorables a la acumulación y conservación excepcional de nieve en el Pirineo oriental?

- El invierno se estudia como **proceso** (secuencia de regímenes), no solo como media estacional.
- **SEPI-D** (diagnóstico y atribución histórica) y **SEPI-P** (predicción) son productos separados, con predictores distintos y sin mezclar resultados.
- Capas: L0 planetaria (ENSO, QBO, MJO, vórtice, calentamientos estratosféricos súbitos), L1 oceánica, L2 regímenes sinópticos (NAO, WeMO, EA/WR, jet, bloqueos, transporte de vapor), L3 persistencia, L4 mesoescala (motor orográfico, föhn, cubetas, viento a 700 hPa) y L5 manto (nieve nueva, equivalente en agua, fusión, lluvia sobre nieve).
- Un episodio extremo no equivale a un invierno extremo (Gloria 2020 se clasifica por separado como episodio y como temporada).
- Dos climatologías: móvil (excepcionalidad respecto al clima de cada época) y fija (para no ocultar tendencias).

## Hipótesis
- **H1 atlántica**, **H2 mediterránea**, **H3 híbrida**, **H4 conservación** y **H5 estratosférica** (como cadena de mediación).
- **H6 memoria y persistencia:** con iguales medias estacionales, la organización temporal de los regímenes decide el resultado. Métricas preregistradas (máximo tres): racha seca más larga; transiciones entre regímenes húmedos NW y E/SE; días de lluvia sobre nieve o recuperación del manto tras la fusión.

## Estado de las afirmaciones
| Hallazgo | Valoración | Decisión |
|---|---|---|
| Dualidad atlántica–mediterránea | Sólida; reproducida con datos propios (fase 01) | Núcleo |
| WeMO con signo distinto según la vertiente | Sólida como diagnóstico | Modelizar por macizo; usar días en las colas |
| H3 híbrida | La que mejor integra la evidencia; no demostrada | Prioritaria |
| Persistencia de regímenes (H6) | Sin señal detectable con n = 17 (fase 02) | Pendiente de ERA5 y S2M |
| ENSO como predictor directo | Evidencia insuficiente | Condicionante |
| Vórtice polar y calentamientos súbitos | Efecto indirecto documentado; ni necesario ni suficiente | Módulo subestacional |
| «Un calentamiento súbito garantiza un invierno nivoso» | Refutado (2022–23 y 2023–24) | — |
| Predictibilidad estacional local | No evaluada | Validación obligatoria |

## Tamaño muestral
- **SEPI-D:** unos 65 inviernos con S2M (1959–2026); hoy solo 17 con datos abiertos accesibles. Muestra efectiva menor por la dependencia entre macizos.
- **SEPI-P:** limitado por los hindcasts (periodo común C3S 1993–2016; SEAS5 1981–2016, por comprobar). Como mucho, habilidad en terciles.

## Experimento prospectivo 2026–27 (preregistrado el 26-11-2026)
- Estado inicial: El Niño muy fuerte (ONI ASO +2,46), QBO del oeste y un calentamiento estratosférico el 10-11-2026 (fuentes secundarias, **por verificar con ERA5**). Combinación sin análogos en la serie: es un experimento, no una señal.
- Variables objetivo: acumulación por encima de 2.000 m y persistencia a 1.500–1.800 m, por macizo y cota.
- Predicción: climatología más una nota cualitativa. No se emite probabilidad de excepcionalidad.

## Fases
01 dataset transfronterizo · 02 ranking por macizo y cota · 03 reconstrucción diaria de los inviernos extremos · 04 atlas de anomalías oceánicas y estratosféricas · 05 matrices de transición · 06 extremos frente a deficitarios · 07 validación retrospectiva · 08 experimento 2026–27 · 09 integración en MeteoPortinatx–Pirineos.

---

# Fase 01 — catálogo objetivo de inviernos con observaciones (26-11-2026)

**Estado:** análisis exploratorio. Lo ha verificado un agente independiente; sus correcciones están aplicadas. No es una validación de SEPI ni un aviso. 

## Datos usados y bloqueos
- **Usados:**
  - XEMA (Meteocat), espesor de nieve diario (variable 38, máximo diario corregido), 2009–2026. Este: Malniu Z3, Cadí Nord Z9, Núria DG, Ulldeter ZC. Centro y oeste: Bonaigua Z1, Boí Z2, Certascan Z5, Sasseuva Z6, Espot Z7, Salòria ZB, Lac Redon VS.
  - XEMA, precipitación diaria (variable 35) de las once estaciones (fases 02 y 02b).
  - Météo-France, red horaria MTO_1H (THREDDS de AERIS/IPSL): precipitación y temperatura de Aston, Formiguères y Belcaire. Viento horario de las nivosas. Las nivosas (Canigou, Puigmal, Port d'Aula) no traen ni precipitación ni espesor de nieve en este producto.
  - NOAA CPC: NAO, EA, EA/WR, SCA (mensuales), NAO y AO diarias, ONI y QBO.
- **Bloqueados desde el entorno de trabajo:**
  - S2M (AERIS no publica una ruta de descarga accesible; probablemente exige registro).
  - data.gouv / Météo-France quotidiennes (el proxy corta la conexión).
  - NCEP en NOAA PSL (403).
  - ERA5 vía Open-Meteo (cupo diario agotado).
  - WeMO de la UB (error 500).
  - Pendientes por ello: la prueba de ruptura de S2M en 2002, la WeMO y los regímenes a 700 hPa.

## Hallazgo de datos importante
Los datos abiertos de la XEMA para la variable 38 están en **mm hasta el 14-11-2021** y en **cm desde el 15-11-2021**. El cambio ocurre el mismo día en las 11 estaciones. Comprobado con dos anclas: Cadí Nord 2.338 mm el 11-04-2018 equivale a 234 cm, el máximo histórico citado por Meteocat; Núria 144 cm el 26-01-2026, récord citado por Meteocat. Cualquier uso de esta variable debe aplicar la corrección.

## Método (resumen)
- Temporada de noviembre a mayo, con el nombre del año final.
- Por estación: HSmax (espesor máximo), días con ≥30 cm entre diciembre y abril (corregidos por cobertura) y HNproxy (suma de subidas diarias ≥2 cm).
- Control de calidad: día con al menos 12 h de datos; valores >600 cm descartados; picos de un día descartados; si máximo − mínimo diario >30 cm, se usa el mínimo; temporada válida con ≥80 % de días.
- Índice de grupo: media de los valores estandarizados por estación. E_acum = media de HSmax y HNproxy del este; E_pers = días ≥30 cm del este; contraste E–O = E_acum − W_acum.
- Météo-France: precipitación horaria caída con T ≤ 0,5 °C entre noviembre y abril. Se exige ≥85 % de cobertura en cada mes de diciembre a marzo.

## Ranking del Pirineo catalán oriental (2009–10 a 2025–26)
| Invierno | E_acum | E_pers | W_acum | Contraste E–O |
|---|---|---|---|---|
| 2017–18 | 1,60 | 0,92 | 1,67 | −0,06 |
| 2025–26 | 1,25 | 1,16 | 0,55 | 0,70 |
| 2012–13 | 0,72 | 0,14 | 1,34 | −0,61 |
| 2016–17 | 0,63 | 0,70 | −0,32 | 0,95 |
| 2019–20 | 0,59 | 0,58 | 0,18 | 0,42 |
| 2013–14 | 0,50 | 0,86 | 1,30 | −0,81 |
| 2009–10 | 0,41 | 0,26 | 0,10 | 0,31 |
| 2024–25 | −0,14 | −0,44 | −0,38 | 0,24 |
| 2021–22 | −0,17 | 0,29 | −0,23 | 0,06 |
| 2010–11 | −0,20 | −0,17 | −0,38 | 0,18 |
| 2011–12 | −0,29 | −0,57 | −0,39 | 0,10 |
| 2014–15 | −0,32 | −0,04 | 0,06 | −0,38 |
| 2018–19 | −0,68 | −0,37 | −0,48 | −0,19 |
| 2023–24 | −0,70 | −1,23 | −0,30 | −0,41 |
| 2020–21 | −0,87 | −0,21 | −0,84 | −0,03 |
| 2015–16 | −0,95 | −1,12 | −0,49 | −0,46 |
| 2022–23 | −1,37 | −0,86 | −1,39 | 0,02 |

**Lectura:**
- **Excepcionales en el este:** 2017–18 y 2025–26. En el ranking de persistencia, 2025–26 queda primero.
- **Deficitarios:** 2022–23, 2015–16, 2020–21 y 2023–24.
- **El contraste E–O separa los tipos de invierno:**
  - Inviernos con sesgo oriental (mediterráneo): 2016–17, 2025–26 y 2019–20 (Gloria).
  - Inviernos con sesgo occidental (atlántico): 2013–14 y 2012–13. Coincide con la literatura, que sitúa 2013 como récord en el oeste y la Haute-Ariège, no en los Pirineos Orientales.
  - Es una separación descriptiva entre H1 y H2 con datos propios.
- Con solo 17 inviernos, los percentiles 90 y 95 equivalen a uno o dos casos. El ranking es ordinal, no una probabilidad.

## Índices de teleconexión (exploratorio)
- 42 correlaciones de Spearman (NAO, EA, EA/WR, SCA, ONI de diciembre a febrero, AO, días con NAO ≤ −1) contra seis variables objetivo, con intervalos bootstrap.
- **Ninguna supera la corrección por pruebas múltiples.** Solo una tiene p < 0,05 (EA/WR contra la precipitación sólida de Formiguères: ρ = −0,47, n = 19). Por azar se esperarían unas dos.
- Conclusión coherente con la literatura: **ningún índice estacional por sí solo explica la nieve del Pirineo oriental** en este periodo.
- ENSO, solo como anécdota (n = 3, no significativo): los tres inviernos con ONI ≥ 1,4 (2009–10, 2015–16 y 2023–24) quedan en los puestos 7, 16 y 14. No permite ninguna inferencia para el El Niño muy fuerte de 2026–27.

## H6 — estructura temporal (diciembre a marzo, estaciones del este)
- Racha seca máxima (días sin subida ≥2 cm) frente a E_acum: ρ = −0,51 [−0,78; −0,05].
- Número de episodios de nevada frente a E_acum: ρ = 0,61 [0,19; 0,84]. Es parcialmente circular, porque ambos salen de la misma serie. Frente a HSmax solo: ρ = 0,55 [0,08; 0,80].
- 2025–26 tuvo la racha seca más corta (17 días) y la mayor cantidad de episodios (13,2); 2017–18, 18,5 días y 12,5 episodios.
- Resultado descriptivo compatible con H6. La fase 02 lo contrasta con una fuente independiente (abajo).

## Coherencia entre redes
- E_acum frente a la precipitación sólida de Formiguères: ρ = 0,65 (n = 16).
- Acumulación oeste (W_acum) frente a Aston: ρ = 0,63 (n = 14).
- Formiguères frente a Aston: ρ = 0,76 (n = 13).
- Los pluviómetros calefactados de Météo-France captan mal la nieve. En Formiguères, en diciembre de 2017 y febrero de 2018, los huecos de datos coinciden con la precipitación, y esa temporada queda excluida. Las cifras de precipitación sólida son índices relativos, no la nieve caída.

## Hallazgos de la verificación independiente (aplicados)
- V1, P0: el corte de unidades es el 15-11-2021, no el 01-08-2021. Corregido.
- V2: había picos en rampa en el máximo diario. Ahora se usa el mínimo si la diferencia supera 30 cm.
- V3: Formiguères 2017–18 no es válido. Excluido por exigencia de cobertura mensual.
- V4: la señal EA/WR no supera la corrección por pruebas múltiples. Se presenta como exploratoria.
- V5: H6 es parcialmente circular. Se añade el contraste con HSmax.
- V6: los días sin dato alargaban las rachas en H6. Ahora se exige ≥95 % de cobertura. Los días ≥30 cm se corrigen por cobertura.

---

# Fase 02 — H6 y H1/H2 con una fuente independiente (26-11-2026)

**Estado:** exploratorio, verificado por un agente independiente; correcciones aplicadas. n = 17 inviernos (dic–mar 2009–10 a 2025–26).

## Método
- **Días húmedos** a partir de la precipitación diaria XEMA (variable 35) de Malniu, Cadí Nord, Núria y Ulldeter, no del espesor de nieve. Umbral: ≥2 mm/día en la media de estaciones. Cada estación se escala por su media dic–mar del periodo común, para que la entrada de Ulldeter (sept. 2011) no cambie el nivel. Día válido con ≥20 h de datos y ≥2 estaciones. Cobertura ≥96,7 % en todas las temporadas.
- **Sector del flujo** por la dirección vectorial media diaria del viento en la nivosa de Puigmal (2.465 m; Météo-France MTO_1H): W-NW-N-NE (270–45°), ENE-E-SE-S (45–180°), SSW-SW-WSW (180–270°). Los sectores son desiguales (135°, 135°, 90°).
- Métricas por invierno: precipitación total, días húmedos, episodios, racha seca máxima, fracción y precipitación por sector, transiciones entre episodios W-NW-N-NE ↔ ENE-E-SE-S.
- Spearman con IC bootstrap; parcial de rangos controlando por la precipitación total; corrección de Benjamini–Hochberg sobre las ocho pruebas.

## Resultados
| Objetivo | Métrica | ρ | IC 95 % | q BH | ρ parcial (P total) | q BH parcial |
|---|---|---|---|---|---|---|
| E_acum | racha seca máxima | −0,29 | [−0,75; +0,29] | 0,30 | +0,18 | 0,64 |
| E_acum | episodios | +0,53 | [+0,04; +0,82] | 0,08 | +0,16 | 0,64 |
| E_acum | transiciones NW↔E/SE | −0,05 | [−0,50; +0,42] | 0,84 | −0,65 | 0,03 |
| E_pers | racha seca máxima | −0,36 | [−0,73; +0,19] | 0,24 | −0,06 | 0,83 |
| E_acum | precipitación total | +0,71 | [+0,32; +0,89] | 0,01 | — | — |
| Contraste E–O | fracción días E/SE | +0,34 | [−0,25; +0,87] | 0,24 | +0,27 | 0,53 |
| Contraste E–O | precipitación E/SE | +0,44 | [−0,12; +0,87] | 0,15 | +0,28 | 0,53 |
| W_acum | precipitación NW (este) | +0,64 | [+0,21; +0,89] | 0,02 | +0,38 | 0,45 |

## Lectura
- **La señal dominante es la cantidad total de precipitación** (ρ = 0,71 con E_acum). Con n = 17 no se detecta ningún efecto directo adicional de las métricas de régimen o de estructura temporal. Redacción correcta: «no se detecta», no «no hay». La precipitación total puede ser mediadora del régimen, y la potencia para una parcial de 0,5 es de ≈0,5.
- **La racha seca de la fase 01 no se reproduce** con días húmedos por precipitación (−0,29 frente a −0,51). La diferencia cabe en el ruido de muestreo y las definiciones cambian, así que no está demostrado que la fase 01 estuviera inflada por circularidad.
- **Transiciones NW↔E/SE:** nulas en bruto; parcial −0,65 (q = 0,03), contraria a H6. **No se sostiene:** el análisis de sensibilidad (abajo) muestra que depende de dónde se tracen los límites de sector.
- **H1/H2:** la orientación de la precipitación va en la dirección esperada respecto al contraste E–O, pero no es significativa con esta clasificación.

## Sensibilidad de la señal de transiciones
24 variantes: umbral húmedo 1/2/3/5 mm, límites de sector girados −22,5°/0°/+22,5°, con y sin filtro de consistencia del viento ≥0,5. Dos definiciones de transición: entre episodios consecutivos, o ignorando los episodios SW.
- Parcial mediana −0,35, rango [−0,79; +0,11]. p < 0,05 en solo 9 de 24 variantes (7 de 24 en la segunda definición).
- Casi todas las significativas usan los límites originales; con giro de ±22,5° la señal se debilita mucho.
- **Conclusión:** el signo tiende a ser negativo, pero la señal es frágil y depende de dónde se trace la frontera entre sectores. No se puede sostener con el viento de una estación; contrastar con regímenes ERA5 a 700 hPa. Salida: `out_sens_transiciones.csv` (`scripts/sepi/sens_trans.py`).

## Hallazgos de la verificación independiente (aplicados o declarados)
- H1, P0: **Canigou no representa el flujo de cresta.** Su componente v diaria se correlaciona negativamente con Puigmal (−0,60), Port d'Aula, Formiguères y Targasonne. El 86 % de sus días caen en S-SW y entre un 33 y un 42 % de sus horas están en calma. Se descarta un error de código: convención, unidades, desfase horario y giro de 180° comprobados. Causa (canalización local o sensor): desconocida. **Retirado como relleno**; no usar Canigou como proxy de cresta. (Comprobación hecha por el verificador con scripts propios; `fetch_data.py` descarga Port d'Aula y Targasonne para repetirla, pero aún no hay script en el repo.)
- H2, P1: posible sobrecontrol, porque la precipitación total puede ser mediadora. La redacción se ajusta en consecuencia.
- H3, P1: el control parcial se había aplicado solo a lo significativo. Ahora se calcula para las ocho pruebas, con BH, dentro de `phase02.py`.
- H4, P1: W_acum se controlaba con precipitación del este. Tratado en la fase 02b.
- H5, P2: en 2010 y 2011 solo hay tres estaciones. Corregido con el escalado por estación.
- H6, P2: las etiquetas de sector eran engañosas. Renombradas con su anchura real.
- H7, P2: restos de código eliminados.

---

# Fase 02b — dominio oeste con su propia precipitación (26-11-2026)

**Estado:** exploratorio, verificado por un agente independiente; correcciones aplicadas.

## Método
- Precipitación diaria XEMA (variable 35) de Bonaigua, Boí, Certascan, Sasseuva, Espot, Salòria y Lac Redon, con el mismo control de calidad y escalado que la fase 02. Cobertura ≥97 % en todas las temporadas; sin días duplicados ni desplazados.
- Sector de Puigmal en días húmedos del oeste; las métricas por sector exigen ≥90 % de días húmedos con sector válido (quedan fuera 2013, 2014 y 2023).
- Parciales con IC bootstrap (2.000 remuestreos).

## Resultados
| Objetivo | Métrica | Control | n | ρ | IC 95 % | ρ parcial [IC 95 %] |
|---|---|---|---|---|---|---|
| W_acum | precipitación total oeste | — | 17 | +0,80 | [+0,48; +0,96] | — |
| W_acum | precipitación NW oeste | P total oeste | 14 | +0,53 | [−0,07; +0,90] | +0,04 [−0,54; +0,79] |
| W_acum | fracción NW oeste | — | 14 | −0,16 | [−0,66; +0,49] | — |
| E_acum | precipitación total este | — | 17 | +0,71 | [+0,31; +0,88] | — |
| Contraste E–O | log(P este / P oeste) | — | 17 | +0,76 | [+0,37; +0,93] | — |
| Contraste E–O | fracción días E/SE | log(PE/PW) | 17 | +0,34 | [−0,24; +0,88] | +0,06 [−0,45; +0,70] |
| Contraste E–O | precipitación E/SE | log(PE/PW) | 17 | +0,44 | [−0,16; +0,89] | +0,15 [−0,43; +0,80] |

## Lectura
- La nieve de cada lado sigue a su precipitación total (oeste 0,80; este 0,71), y **el contraste de nieve E–O sigue al reparto de precipitación entre los dos lados** (0,76).
- Una vez controlado ese reparto, **no se detecta con n = 17** aportación adicional de la clasificación de régimen por el viento de Puigmal. Los IC de las parciales son muy anchos (hasta ±0,6), así que no se puede descartar un efecto moderado.
- **Hipótesis, no resultado:** el régimen podría actuar a través del reparto de precipitación. La relación entre la fracción E/SE y log(PE/PW) es ρ = 0,40 (p = 0,11), no significativa, y el régimen se mide con una sola estación del este.
- **Límite de interpretación:** W_acum y la precipitación del oeste salen de las mismas siete estaciones (espesor y pluviómetro). Su correlación de 0,80 mide en buena parte coherencia entre los dos sensores de cada estación, no una causa independiente. Se desconoce el tipo de pluviómetro y cómo capta la nieve.

## Hallazgos de la verificación independiente (aplicados)
- V1, P1: «queda cerrado» y «no añade nada» presentaban la falta de evidencia como evidencia de ausencia. Reescrito como «no se detecta con n = 17», con IC.
- V2, P1: la mediación pasa a ser hipótesis.
- V3, P2: sin cobertura mínima de sector, PW_NNW quedaba infravalorado (2013 tenía un 60–73 % de días). Ahora se exige ≥90 %.
- V4, P2: comparten estaciones. Declarado como límite.
- V5–V7: sin desplazamiento de día, sin duplicados, sin valores anómalos (máximo diario 146 mm en Espot).
- V8, P2: retirada una comprobación trivial (dos columnas idénticas).

---

# Fase 03 — 58 inviernos con S2M y anclas observadas (27-11-2026)

**Estado:** exploratorio, verificado por un agente independiente; correcciones aplicadas. Ranking por dominio, no regional. S2M es un modelo, no observación ni aviso. Inventario de fuentes y auditoría de datos brutos en [`SEPI-INVENTARIO-FUENTES.md`](SEPI-INVENTARIO-FUENTES.md).

## Datos
- **S2M CSV abierto** (Météo-France, Licence Ouverte 2.0), descargado el 27-11-2026; el último día disponible es el 26-11-2026.
  - Macizos: 70 Haute-Ariège, 71 Andorra, 72 Orlu–St-Barthélemy, 73 Capcir–Puymorens, 74 Cerdagne–Canigou y, como contraste, 69 Couserans.
  - Geometrías: llano y N 20° a 1.800 y 2.100 m; para las anclas, también 1.200–2.400 m.
  - **No hay macizos de la vertiente catalana.**
- **Anclas: observación diaria de Météo-France** (QUOT 66/09, NEIGETOT06), auditada estación a estación.
  - Mont-Louis solo tiene 9 inviernos completos (2005–2013).
  - Porté-Puymorens empieza en 1981.
  - Las anclas largas son Ascou-Lavail (44 inviernos, 1972–2023) y L'Hospitalet (33, 1969–2005).

## Método
- **Invierno:** del 1 de diciembre al 30 de abril. Son 58 inviernos y 8.772 días por serie, sin huecos en S2M.
- **Métricas:** espesor medio (HSmed), máximo (HSmax), días ≥30 cm y días ≥100 cm. Se guardan también el SWE, la fecha del máximo y la racha más larga con ≥5 cm.
- **Métricas degeneradas:** se excluye la que tiene P90 = 0 en un dominio y cota. Es el caso de los días ≥100 cm a 1.800 m en Andorra, Capcir y Cerdagne, casi siempre 0; con «≥» todos los inviernos la cumplirían. Allí el índice y la etiqueta «excepcional» usan HSmed, HSmax y d30.
- **Índice:** mediana del percentil de las métricas usadas. **P90 sobre los 58 valores estacionales.** «Excepcional» significa que todas las métricas usadas están ≥ P90.
- **Ruptura de 2002** (ERA-40 → ARPEGE): percentiles recalculados por subperiodo, 1969–2002 y 2003–2026. Un invierno es «sensible» si cambia ≥2 deciles. La prueba es interna a S2M: no distingue un artefacto de forzamiento de un cambio climático real.
- **Clase por invierno y dominio.** Cada ancla se compara con S2M en su propia cota y se le adjudica el tercil:
  - **A:** ≥2 anclas coinciden en tercil con S2M.
  - **B:** coincide 1.
  - **C:** hay anclas y ninguna coincide (discrepan).
  - **SA:** sin ancla; el orden depende solo del modelo.

  **La clase mide cuántas anclas hay y si coinciden; no es una confianza calibrada.** La clase A solo es posible en Capcir y Cerdagne, y Andorra es siempre SA.

## Resultados

Puesto (de 58) por dominio, en terreno llano. 70 Haute-Ariège · 71 Andorra · 72 Orlu · 73 Capcir · 74 Cerdagne.

| Invierno | 1.800 m: 70 / 71 / 72 / 73 / 74 | Mediana | 2.100 m: 70 / 71 / 72 / 73 / 74 | Mediana |
|---|---|---|---|---|
| 1980–81 | **1** / 6 / 3 / 3 / 15 | 3 | 5 / 18 / 4 / 14 / 34 | 14 |
| 2025–26 | 25 / 9 / 4 / **1**= / **1** | 4 | 27 / 9 / 8 / 3 / **1** | 8 |
| 1971–72 | 9 / 6 / **1** / **1**= / 4 | 4 | 13 / **1** / **1** / **1** / 3 | 1 |
| 2013–14 | 3 / 2 / 7 / 19 / 31 | 7 | 2 / 4 / 5 / 5 / 17 | 5 |
| 2004–05 | 2 / 13 / 2 / 7 / 25 | 7 | **1** / 25 / 2 / 7 / 18 | 7 |
| 1995–96 | 19 / **1** / 15 / 9 / 4 | 9 | 11 / 2 / 15 / 2 / 4 | 4 |
| 2012–13 | 4 / 12 / 6 / 12 / 39 | 12 | 6 / 10 / 6 / 6 / 22 | 6 |
| 2017–18 | 16 / 4 / 19 / 24 / 6 | 16 | 9 / 5 / 16 / 18 / 9 | 9 |

«=» indica empate. En Capcir a 1.800 m, 2025–26 y 1971–72 comparten el puesto 1. Por espesor medio, 1971–72 es primero (38,3 frente a 38,0 cm). Por espesor máximo y por días ≥30 cm, lo es 2025–26.

- **Excepcionales** (todas las métricas usadas ≥ P90; llano, 1.800 m):

| Invierno | Dominio (clase) |
|---|---|
| 2025–26 | Capcir (B), Cerdagne (A) |
| 1985–86 | Capcir (A) |
| 1980–81 | Haute-Ariège (B), Capcir (SA), Orlu (SA) |
| 1971–72 | Orlu (B) |
| 1995–96 | Andorra (SA), Cerdagne (B) |
| 2004–05 | Haute-Ariège (B), Orlu (B) |
| 1991–92 | Cerdagne (B) |
| 2013–14 | Andorra (SA) |

- **Inviernos más pobres** (mediana de puesto ≥ 50 de 58):
  - A 1.800 m: 1989–90, 2010–11, 2007–08 y 1997–98.
  - A 2.100 m: además 1992–93, 2006–07, 1988–89, 2023–24 y 2022–23.
- **Sensibilidad a 2002:** a 1.800 m solo tres inviernos cambian ≥2 deciles (Andorra 1998–99, Orlu 2003–04 y Couserans 2015–16).
- **Clases** (dominios 70–74, llano, 1.800 m):

| Tramo | A | B | C | SA |
|---|---|---|---|---|
| 1969–1984 | 0 | 18 | 12 | 50 |
| 1985–2002 | 7 | 44 | 18 | 21 |
| 2003–2026 | 16 | 38 | 7 | 59 |

- **Anclas** (Spearman del espesor medio dic–abr observado frente a S2M en el macizo asignado; IC del 95 % por bootstrap):
  - Ascou-Lavail → 70: 0,87 [0,73; 0,94].
  - L'Hospitalet → 72: 0,77 [0,51; 0,92].
  - Formiguères → 73: 0,93 y 0,96 (dos estaciones).
  - Ste-Léocadie → 74: 0,77.
  - Canigou, Puigmal y Port d'Aula (nivosas de cresta): 0,74–0,86, con S2M **30–37 cm por debajo**.
  - Mont-Louis → 74: 0,65 [−0,08; 0,93], solo 9 inviernos.
  - Porté-Puymorens → 73: 0,49.
  - Font-Romeu → 74: 0,61.
- **Asignación ancla → macizo:** con otro macizo, algunas anclas correlacionan mejor. Font-Romeu da 0,96 con Andorra, Porté-Puymorens 0,64 con Haute-Ariège y L'Hospitalet 0,85 con Couserans. Sin los contornos oficiales de los macizos, la asignación geográfica es **UNKNOWN**, y las clases de Capcir y Cerdagne dependen de ella.
- **Vertiente catalana:** el E_acum de la XEMA (fase 01, 2010–2026) frente a S2M a 2.100 m da ρ = 0,79 [0,52; 0,91] con Cerdagne–Canigou y 0,68 [0,34; 0,88] con Andorra.

## Lectura
- **2025–26 en Cerdagne–Canigou es el resultado más sólido de la fase:** primero de 58 con cualquier índice y a las dos cotas. A 1.800 m tuvo 44 días con ≥100 cm, cuando el siguiente invierno no pasa de 16. En Capcir empata con 1971–72 a 1.800 m y es tercero a 2.100 m. En Haute-Ariège queda vigésimo quinto. Encaja con el sesgo mediterráneo que mostró la fase 01 y con los 1.073 aludes que contó el ICGC. **Las anclas que lo apoyan en Cerdagne son nivosas de cresta que probablemente asimila SAFRAN, así que no son una confirmación independiente.**
- **No hay base para un número 1 regional.** 1971–72 destaca en Orlu, Capcir y Andorra a 2.100 m. 1995–96 destaca en Andorra. 1980–81 y 2004–05 son inviernos del Ariège. 2013–14 es del oeste y de Andorra. Todo esto vale solo para los macizos franceses y Andorra, sin la vertiente catalana.
- **2017–18,** el primero en la XEMA catalana de 2010–2026, queda en los puestos 4–24 en los macizos franceses y Andorra: es la misma diferencia entre vertientes que ya mostró la XEMA.
- **De 1969 a 1984 el orden es casi solo del modelo** (50 de 80 combinaciones sin ancla). Ransol 1934–2002, que habría que pedir al SMN, es la adquisición de más valor.

## Hallazgos de la verificación independiente (aplicados o declarados)
- **F1, P1.** El P90 con «≥» y d100 casi siempre en 0 hacían trivial esa métrica. Ahora se excluyen las métricas con P90 = 0.
- **F2, P1.** «2025–26 excepcional en el este» iba más allá de los datos. Se ha matizado: Cerdagne es sólido, Capcir empata. La posible asimilación de las anclas pasa a la Lectura y al resumen.
- **F3, P1.** La clase C mezclaba «sin ancla» con «discrepa». Ahora se separan (C/SA), se ha añadido Mont-Louis y se declara que la clase depende del número de anclas.
- **F4, P1.** El emparejamiento de las anclas con los macizos queda como UNKNOWN. El script calcula la ρ con todos los macizos y la tabla de anclas la muestra.
- **F5, P2.** El alcance de la prueba de 2002 se ha declarado en el Método.
- **F6, P2.** Erratas corregidas: lista de inviernos pobres por cota (incluye 1989–90) y puestos de 2017–18.
- **F7, P2.** La lista de la red nivo omitía las estaciones sin id WIGOS: Porte Puymorens a 2.085 m (1996–2009) y Ax-Bonascre. Ahora la genera `audit_nivo.py`.
- **F8, P2.** En `fetch_hist.py`:
  - los nombres de periodo de QUOT se descubren listando el espejo;
  - los ficheros «latest» y los del año en curso se vuelven a descargar siempre;
  - la guarda usa `realpath`;
  - `phase03.py` avisa si la observación no llega al último invierno.

## Límites
- **Independencia de las anclas.** SAFRAN asimila observaciones de la red de Météo-France y de la red nivo, y por NIVOMET también españolas y andorranas. Las correlaciones con las anclas francesas **sobrestiman la validación**. Qué estaciones entran cada año es UNKNOWN; hay que pedirlo al CNRM-CEN.
- **Clases A/B/C/SA:** recuentos de coincidencia de tercil, no probabilidades. Dependen de cuántas anclas hay y de la asignación al macizo.
- **Prueba de 2002:** solo es interna a S2M. El contraste con CERRA-Land, desde 1984, requiere la cuenta del CDS del titular.
- **Geometría:** solo llano y N 20°. La convención de que exposición 0 es el norte es SUPUESTO, pendiente del descriptivo oficial. Tampoco se han confirmado las unidades del CSV (cm y mm, inferidas de los valores).
- **Versiones:** el CSV abierto no se mezcla con S2M AERIS v2020.2.

## Siguientes pasos
1. **Peticiones de datos** (el titular): Ransol 1934–2002 (SMN/FEDA), Núria antes de 1985 (AEMET), el inventario NIVOBS (ICGC) y la lista de estaciones asimiladas en SAFRAN (CNRM-CEN).
2. **Con la clave del CDS:**
   - CERRA-Land para la prueba de 2002;
   - regímenes ERA5 a 700 hPa para la señal de transiciones (fase 02);
   - verificar el calentamiento estratosférico del 10-11-2026.
3. **Teleconexiones sobre el ranking de 58 inviernos.** Se analizan después del ranking, sin usarlas para construirlo:
   - NAO, EA y EA/WR de CPC;
   - WeMO de la UB, cuando su servidor responda;
   - el catálogo SSWC de NOAA (hasta 2023).

   Corregir por multiplicidad.
4. Añadir Sorteny (SMA) y Núria manual (AEMET) para alargar la serie del este.

Scripts en `scripts/sepi/`. Salidas (en `SEPI_DATA`): `out_catalogo.csv`, `out_correlaciones.csv`, `out_h6.csv`, `out_xema_*.csv`, `out_fase02*.csv`, `out_sens_transiciones.csv`, `out_cobertura_mf_nieve.csv` y `out_f03_*.csv`.
