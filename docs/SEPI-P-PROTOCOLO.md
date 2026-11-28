# SEPI-P: protocolo de validación de la predicción estacional (SEPI-EK-02a)

**Estado: BORRADOR, no congelado.** Lo congela el titular, con fecha, **antes de la primera descarga de hindcasts**. Desde entonces cualquier cambio va al registro de decisiones (§12), con fecha y motivo, y nunca se presenta como prerregistro.

**Ceguera parcial, declarada:** las series objetivo (S2M, F03 v2) ya se conocen; las predicciones de SEAS5 todavía no. El protocolo es ciego respecto a la habilidad del modelo, no respecto a los inviernos observados.

Relación con otros documentos:
- [`SEPI-PROTOCOLO.md`](SEPI-PROTOCOLO.md): diagnóstico histórico, F03 v2.
- [`SEPI-EARTHKIT.md`](SEPI-EARTHKIT.md): ingesta de los datos, EK-01.

## 1. Objeto y no-objeto
**Objeto.** Comprobar si los pronósticos de SEAS5 iniciados el 1 de noviembre tienen **habilidad fuera de muestra frente a la climatología** para:
- **(A)** la meteorología regional del Pirineo oriental de diciembre a enero, frente a ERA5;
- **(B)** la acumulación nival de la temporada, frente a S2M (F03 v2) y frente a las anclas.

Son dos validaciones distintas. Que SEAS5 acierte en (A) no implica que acierte en (B).

**No-objeto:**
- Ninguna probabilidad operativa ni aviso.
- Ninguna predicción para una estación de esquí concreta: la rejilla de 1° no resuelve Masella, Font-Romeu ni Les Angles.
- Ningún cambio en la F03 v1 ni en la v2.

## 2. Datos
| Fuente | Uso | Detalle fijado | Estado |
|---|---|---|---|
| SEAS5, CDS `seasonal-monthly-single-levels`, `monthly_mean` | Predictores | Inicio el 1 de noviembre. `leadtime_month` 2–3 (diciembre y enero); 2–6 (diciembre a abril) solo para el objetivo secundario T2 | System 51 frente a 5: UNKNOWN hasta comprobarlo en el catálogo (G0 de EK-01) |
| Hindcast de SEAS5 | Entrenamiento y validación | **1981–2016, 36 inviernos, 25 miembros** (Johnson et al. 2019; documentación de C3S) | OBSERVADO para SEAS5; SUPUESTO que System 51 comparte el periodo |
| Previsiones reales de SEAS5 | Prueba final | Inviernos 2017–18 a 2025–26 (9), **51 miembros** | No se abren hasta cerrar el modelo (§7) |
| ERA5 mensual | Referencia para (A) | Misma caja y mismas variables | Es reanálisis, no observación |
| S2M (F03 v2) | Objetivo para (B) | `season_metrics_v2.csv` y `rankings_v2.csv` | Es un modelo forzado por SAFRAN |
| Anclas (nivosas, QUOT) | Contraste de (B) | Clases de validación de F03 v2 | Independencia: UNKNOWN |

**Caja regional (propuesta):** 42,0–43,0° N y 0,5–3,0° E, que da unos 4×3 puntos a 1°. La caja se fija **antes** de descargar y no se ajusta después.

**Unidades:**
- `snow_depth` en SEAS5 y ERA5 está en **m de equivalente en agua**, no en cm de espesor.
- La precipitación mensual se da como tasa. Hay que comprobar su agregación con los metadatos (EK-01, G2).

## 3. Correcciones a la propuesta del 28-11-2026
| Propuesta | Corrección | Motivo |
|---|---|---|
| Hindcasts 1993–2016, 24 inviernos | **1981–2016, 36 inviernos** para SEAS5. El periodo 1993–2016 se usa solo en la comparación multimodelo M6 | El hindcast de SEAS5 empieza en 1981. Con n = 36, la correlación crítica unilateral (p = 0,05) baja de 0,34 a 0,28 |
| «Previsión diciembre–enero» con el índice SEPI | El índice F03 v2 cubre diciembre a abril. **T1 = índice diciembre–enero** (nuevo, calculado con S2M diario) y **T2 = índice diciembre–abril** de F03 v2 | Sin esto, objetivo y predictores no cubrirían la misma ventana temporal |
| Hindcast y previsión real equivalentes | Hindcast con 25 miembros, previsión real con 51 | Las puntuaciones probabilísticas dependen del número de miembros: CRPS «fair» o submuestra de 25 |
| Objetivo S2M homogéneo | **La ruptura del forzamiento de 2002 cae dentro del hindcast** | Una habilidad aparente puede venir del salto. Se exige estabilidad entre 1981–2001 y 2002–2016 (§8) |
| 36 estratos como 36 pruebas | Los estratos no son independientes | Objetivo primario reducido a 6 series, con corrección de Holm (§4) |
| Eventos P90: 2–3 por estrato | Cifras reales en F03 v2: 1981–2016, mediana 3 (1–5); 2017–2025, mediana 1, y 16 estratos sin ninguno | El objetivo P90 solo puede ser exploratorio |

## 4. Objetivos (fijados de antemano)
- **T1, primario:** índice SEPI de diciembre a enero, continuo, en **2.100 m en llano**, para cada uno de los 6 dominios (69–74). Son 6 pruebas con corrección de Holm. La cota y la orientación son una propuesta y quedan pendientes de decisión del titular (§12).
- **T2, secundario:** índice I de diciembre a abril (F03 v2), en la misma cota y orientación, y terciles del índice.
- **T3, exploratorio:** probabilidad de que el índice supere el P90. Solo descriptivo y sin afirmaciones de habilidad: hay muy pocos eventos.
- **Validación A:** anomalías de T2m, precipitación total, nevada y presión a nivel del mar sobre la caja, frente a ERA5.

## 5. Predictores
**Tope de 3 predictores por modelo,** para no sobreajustar con 36 inviernos. La lista candidata se cierra antes de descargar:
1. Anomalía de T2m de la caja.
2. Anomalía de la precipitación total o de la nevada de la caja.
3. Índice de régimen a partir de la presión a nivel del mar: componente zonal del gradiente entre el Atlántico y el Mediterráneo occidental (el «oeste» o el «levante» de las hipótesis SEPI). La definición exacta se fija en §12.
4. Anomalía de `snow_depth` en m de equivalente en agua: candidata, compite con la 2.

La selección se hace dentro de cada pliegue de entrenamiento, nunca con todos los años.

## 6. Modelos (por orden; cada uno debe superar a los anteriores fuera de muestra)
| Modelo | Método |
|---|---|
| M0 | Climatología (referencia de todas las puntuaciones de habilidad) |
| M1 | Ensemble sin corregir, con anomalía respecto a su propia climatología |
| M2 | Corrección del sesgo medio |
| M3 | Anomalías estandarizadas |
| M4 | Quantile mapping (alto riesgo de sobreajustar las colas con n = 36) |
| M5 | Regresión regularizada (ridge) de T1 y T2 sobre los predictores, con λ elegido en validación cruzada anidada |
| M6 | Multimodelo de C3S, solo en 1993–2016, como comparación |

La corrección del sesgo se calcula **solo con los años de entrenamiento** de cada pliegue. Es una hipótesis que hay que contrastar, no una mejora que se da por hecha.

## 7. Diseño de validación
1. **Hindcast 1981–2016.** Validación cruzada dejando un año fuera, con exclusión de ±1 año alrededor del invierno de prueba, porque hay autocorrelación. Como sensibilidad, origen móvil con entrenamiento inicial 1981–2000.
2. **Prueba final 2017–2025** (9 inviernos). Se abre **una sola vez**, con el modelo ya congelado. No se usa para elegir nada. Con 9 casos solo puede refutar, no confirmar.
3. **Intervalos de confianza:** bootstrap circular por bloques (bloque de 5, B = 2.000), como en F03 v2.

## 8. Métricas y criterio de éxito
**Métricas deterministas, para T1 y T2:**
- Correlación de anomalías (ACC).
- Correlación de Spearman.
- RMSE y MAE.
- MBE (sesgo medio).
- MSSS frente a M0.

**Métricas probabilísticas:**
- CRPS «fair» y CRPSS.
- RPS y RPSS por terciles.
- ROC-AUC.
- Diagrama de fiabilidad.
- Histograma de rangos.
- Brier, BSS y PR-AUC solo para T3, exploratorio.

**Criterio de habilidad para T1, fijado de antemano.** Un dominio tiene habilidad solo si se cumplen **las cuatro** condiciones:
1. **CRPSS > 0,** con el IC al 90 % del bootstrap sin incluir el 0.
2. **Spearman significativo** tras Holm (unilateral, α = 0,05, n = 36; correlación crítica sin corregir ≈ 0,28).
3. **Mismo signo de habilidad** en 1981–2001 y en 2002–2016, como control de la ruptura de 2002.
4. **En la prueba final 2017–2025,** que no haya habilidad negativa clara, es decir, que el IC del CRPSS no esté entero por debajo de 0.

Si no se cumple, el resultado es «sin habilidad demostrada», no «predicción posible». Es un resultado válido y se publica.

## 9. Factores de confusión declarados
- **S2M es un modelo** y su forzamiento cambia en 2002.
- **Validación B:** frente a las anclas hereda las clases de F03 v2. Sin independencia confirmada no puede haber clase A.
- **El Niño:** solo hay 8 inviernos con El Niño moderado o fuerte desde 1968. La comparación con inviernos de El Niño (la lista del 28-11) queda registrada como **análisis exploratorio E1**. La lista oficial del CPC se fija antes de mirar resultados, y E1 no entra en el criterio de §8.
- **La rejilla de 1°** no representa la sombra pluviométrica de Cerdanya ni de Capcir. Los predictores son regionales.

## 10. Herramientas externas (auditar antes de usar)
| Herramienta | Uso | Licencia |
|---|---|---|
| Tutorial de verificación estacional de C3S | Referencia metodológica (anomalías, terciles, ROC, RPS) | Documentación |
| earthkit-data / -transforms | Ingesta y anomalías | Apache-2.0 (auditada en EK-01) |
| xskillscore | Métricas | UNKNOWN: verificar antes de añadirlo |
| ibicus | Corrección de sesgo (M4) | UNKNOWN: verificar antes de añadirlo |

No se copia código de terceros: se usan como dependencias opcionales en el entorno de `scripts/sepi/requirements-earthkit.txt`, con versiones fijadas tras la puerta G3 de EK-01.

## 11. Scripts previstos (`scripts/sepi/`, todos opcionales y fuera del CI)
| Script | Función |
|---|---|
| `earthkit_ingest.py` | Ya existe (EK-01, PR #70). Hay que ampliar `leadtime_month` a 2–6 para T2 |
| `fetch_era5_reference.py` | ERA5 mensual sobre la caja (requiere la clave del CDS) |
| `align_hindcasts.py` | Separar sistema, inicio, miembro y plazo, y recortar la caja |
| `phase04_targets.py` | T1 (diciembre–enero) a partir de S2M diario; T2 y T3 a partir de F03 v2 |
| `verify_meteorology.py` | Validación A |
| `bias_adjustment.py` | Modelos M2 a M4, dentro de cada pliegue |
| `phase05_backtest.py` | Validación cruzada, bootstrap y criterio de §8 |
| `verify_sepi_p.py` | Verificador independiente, escrito por otra persona o agente desde este documento |
| `phase06_forecast.py` | **Solo si §8 se cumple** para algún dominio |

## 12. Decisiones pendientes del titular (antes de congelar)
1. Estrato del objetivo primario: 2.100 m en llano (propuesta) u otro.
2. La caja regional (§2).
3. Definición exacta del índice de régimen a partir de la presión a nivel del mar.
4. System 51 o 5, una vez comprobado en el catálogo.
5. Si se incluye M6 (multimodelo) o se deja para más adelante.
6. Fecha de congelación.

### Registro de decisiones
| Fecha | Decisión | Tipo |
|---|---|---|
| 28-11-2026 | Redacción del borrador a partir de la propuesta del titular, con las correcciones de §3 | Borrador |
