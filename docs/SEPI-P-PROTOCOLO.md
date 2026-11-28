# SEPI-P: protocolo de predicción y validación estacional (v0.4)

**Estado: BORRADOR, no congelado.**
- **Congelación:** la hace el titular, con fecha, **antes de ejecutar ningún cálculo de habilidad y antes de consultar las matrices de transición entre periodos** (§9). Desde entonces, todo cambio va al registro de decisiones (§13), con fecha y motivo, y no se presenta como prerregistro.
- **Versiones:**
  - v0.3, 28-11-2026: PR #72, solo con SEAS5.
  - v0.4: añade los periodos bimestrales, los objetivos medidos dentro de cada periodo, los modelos de referencia sin CDS y la separación entre modelos retrospectivos y operacionales.

Relación con otros documentos:
- [`SEPI-PROTOCOLO.md`](SEPI-PROTOCOLO.md): diagnóstico histórico, F03 v2.
- [`SEPI-EARTHKIT.md`](SEPI-EARTHKIT.md): ingesta de los datos.

## 0. Lo que ya se conoce antes de congelar (declarado)
El protocolo no es ciego del todo. Antes de congelarlo ya se conocía lo siguiente:
- **Los resultados de F03 v1 y v2**, con los rankings estacionales de diciembre a abril.
- **Los recuentos descriptivos de días ≥ 30 y ≥ 100 cm por periodo** (28-11-2026), que motivaron la regla de exclusión de §3. Resultado: d100 tiene P90 = 0 en 8 de 12 estratos de noviembre–diciembre, y la mediana de inviernos sin ningún día es del 95 %.

**No** se ha calculado ni consultado nada de lo siguiente:
- relaciones entre periodos (transiciones, correlaciones o regresiones del estado inicial sobre el balance);
- análogos;
- habilidad de ningún modelo;
- predicciones de SEAS5.

## 1. Objeto y no-objeto
**Objeto.** Comprobar, fuera de muestra y frente a la climatología, tres capacidades distintas que no se confunden:
- **(a)** anticipar **acumulación**, es decir, ganancia de nieve;
- **(b)** anticipar **pérdidas**;
- **(c)** anticipar el **estado final** del manto.

El balance neto de nieve de un periodo depende en parte, por pura aritmética, del estado inicial: un manto grande puede perder más. Por eso cada una de las tres capacidades se informa por separado.

**No-objeto:**
- Ninguna probabilidad operativa ni aviso.
- Ninguna predicción para una estación concreta: Masella, Font-Romeu, Les Angles, Formiguères y Porté-Puymorens necesitan una reducción de escala orográfica validada (EK-03b).
- Ningún cambio en la F03 v1 ni en la v2.

**Resultados negativos.** Si ningún modelo supera a la climatología, se publica ese resultado. Si solo hay habilidad en un periodo o en algunos dominios, el producto se limita a ellos.

## 2. Periodos, dominios y estratos
- **Periodos:**
  - **P1**, noviembre–diciembre: formación del manto.
  - **P2**, enero–febrero: acumulación.
  - **P3**, marzo–abril: persistencia y fusión.

  Inviernos de 1968–69 a 2025–26, 58 en total, con la etiqueta del año de inicio. Cada periodo tiene **su propia** climatología, sus umbrales y su distribución de referencia.
- **Dominios** (macizos S2M):
  - 74, Cerdagne–Canigou;
  - 73, Capcir–Puymorens;
  - 71, Andorra;
  - 70, Haute-Ariège;
  - 72, Orlu–Saint-Barthélemy;
  - 69, Couserans, como control occidental.
- **Estrato primario:** 2.100 m en llano.
- **Estratos secundarios:** 1.800 m en llano, 1.800 m en N 20° y 1.800 m en NO 20°.
- **Fuente:** S2M diario (`s2m_ref_v2_69_74.csv.gz`). `equivalent_eau` es el agua equivalente de la nieve (SWE) en kg/m², es decir, en mm; `neigetot` es el espesor (HS) en cm.

## 3. Objetivos por periodo

| Variable | P1 nov–dic | P2 ene–feb | P3 mar–abr |
|---|---|---|---|
| Balance neto de SWE, ΔSWE | **Primaria** | **Primaria** | **Primaria** |
| Ganancias diarias de SWE, G_SWE | Secundaria | Secundaria | Secundaria |
| Pérdidas diarias de SWE, L_SWE | Secundaria | Secundaria | Secundaria |
| Ganancias diarias de HS, G_HS | Secundaria | Secundaria | Secundaria |
| Días con HS ≥ 30 cm | Secundaria | Secundaria | Secundaria |
| Días con HS ≥ 100 cm | **Excluida** | Solo 2.100 m | Solo 2.100 m |
| Fecha de formación del manto | Secundaria | — | — |
| Espesor y SWE al cierre | Diagnóstico (capacidad c) | Diagnóstico | Diagnóstico |
| Nieve nueva real | UNKNOWN | UNKNOWN | UNKNOWN |
| Lluvia sobre nieve | UNKNOWN | UNKNOWN | UNKNOWN |

**Definiciones.** Para un periodo con días t = 1…n, y con SWE₀ el valor del día anterior al primero:

- ΔSWE = SWE_final − SWE_inicial
- G_SWE = Σ max(ΔSWE_t, 0)
- L_SWE = Σ max(−ΔSWE_t, 0)

Se cumple ΔSWE = G_SWE − L_SWE.

**Lo que G y L no son:**
- **G y L no son nevada ni fusión.** Son aproximaciones derivadas del balance diario del manto. En un mismo día, la nevada y la fusión se compensan: G infravalora la nevada y L infravalora la fusión.
- **La nieve nueva real y la lluvia sobre nieve** necesitan el forzamiento de SAFRAN o ERA5, que no está en los CSV de S2M. Siguen en UNKNOWN hasta que haya datos.

**Fecha de formación del manto:** primer día, contando desde el 1 de noviembre, a partir del cual HS ≥ 30 cm se mantiene durante 7 días seguidos. Si no ocurre en P1 se codifica como «> 31 dic», censurado, no como cero.

**Regla de degeneración:** una variable cuyo P90 en el entrenamiento sea 0 en un estrato se excluye de ese estrato en ese pliegue, y se informa.

## 4. Inicializaciones

| Inicio | P1 nov–dic | P2 ene–feb | P3 mar–abr |
|---|---|---|---|
| 1 nov | lead 1–2 | lead 3–4 | lead 5–6 |
| 1 dic | nov observado + dic previsto | lead 2–3 | lead 4–5 |
| 1 ene | observado | lead 1–2 | lead 3–4 |
| 1 feb | observado | ene observado + feb previsto | lead 2–3 |
| 1 mar | observado | observado | lead 1–2 |

- **Hipótesis primarias:** cada periodo se evalúa con la **inicialización inmediatamente anterior a su inicio**: P1 con la del 1 de noviembre, P2 con la del 1 de enero y P3 con la del 1 de marzo.
- **Expectativa declarada para H-P1:** el 1 de noviembre suele no haber manto, así que M0c tendrá muy poca información. La hipótesis se mantiene igualmente, sin modificarla según el resultado.
- **Archivo de emisiones:** cada emisión, en backtesting o real, se guarda como una instantánea inmutable con su manifiesto y su SHA-256. El diseño es el mismo que el archivo prospectivo del PR #64.

## 5. Modelos

| Modelo | Entrada | Naturaleza | ¿Requiere CDS? |
|---|---|---|---|
| M0 | Distribución climatológica empírica de los inviernos de entrenamiento | Referencia | No |
| M0b | M0 con tendencia lineal ajustada en el entrenamiento | Referencia | No |
| M0c-R | Estado inicial S2M retrospectivo; regresión lineal del objetivo sobre SWE₀, con distribución empírica de residuos | Experimental | No |
| M0c-O | Estado inicial **disponible en la fecha de emisión** | Operacional | No |
| M0d-R | Análogos con S2M retrospectivo | Experimental | No |
| M0d-O | Análogos con datos disponibles en tiempo real | Operacional | No |
| M1–M4 | SEAS5 sin corregir, con sesgo medio corregido, con anomalías estandarizadas y con *quantile mapping* (v0.3) | Experimental | Sí |
| M5 | Estado inicial + SEAS5, regresión regularizada | Experimental hasta validar | Sí |
| M6 | Multimodelo C3S, solo 1993–2016 | Comparación | Sí |

**Los modelos R y O se separan obligatoriamente.**
- **R** mide la predictibilidad potencial.
- **O** mide la que se puede aprovechar al emitir.
- Si no existe una fuente histórica archivada con la disponibilidad real en cada fecha, **los modelos O quedan en UNKNOWN**. Candidatos, sin verificar: nivosas de Météo-France, XEMA y ERA5-Land con su retraso de publicación. Que S2M tenga una versión abierta en tiempo real es UNKNOWN.

**SEAS5 no es predictor por defecto.** Entra solo si demuestra valor añadido frente al mejor de los modelos M0.

### Análogos (M0d)

| Predictor | Prioridad |
|---|---|
| SWE inicial | Primaria |
| HS inicial | Primaria |
| Balance de SWE en los 30 días anteriores | Secundaria |
| Temperatura y precipitación antecedentes | Futura (requieren otra fuente) |
| NAO / WeMO antecedentes | Exploratoria |

- **Dentro de cada pliegue de entrenamiento:** el número de vecinos (k ∈ {3, 5, 7}), la normalización (z con la media y la desviación del entrenamiento) y la ponderación (uniforme o por inverso de la distancia) se eligen ahí y nada más que ahí.
- **Predicción:** la distribución empírica de los objetivos de los k vecinos.
- **Exclusión:** se excluye el invierno inmediatamente anterior al evaluado. El posterior ya queda fuera por el diseño de origen móvil.

## 6. Validación
- **Origen móvil (principal):** entrenamiento inicial de 1968–69 a 1990–91 (23 inviernos). Se prueba un invierno cada vez, de 1991–92 a 2025–26 (35 inviernos potenciales), y se reentrena incluyendo los anteriores. El tamaño efectivo depende de la cobertura (§2 de `SEPI-PROTOCOLO.md`) y de las exclusiones, y se informa.
- **Control de 2002:** la habilidad debe tener el mismo signo en 1991–2001 y en 2002–2025. La ruptura del forzamiento de SAFRAN afecta también a la persistencia.
- **Intervalos de confianza:** bootstrap circular por bloques sobre los inviernos de prueba (bloque de 5, B = 2.000, semilla fijada al congelar).
- **SEAS5** (Parte B, §11): validación cruzada dejando un año fuera de 1981–2016, con exclusión de ±1 año, y prueba final 2017–2025 que se abre una sola vez (v0.3).

## 7. Métricas y criterio de aceptación
**Métrica primaria:** CRPSS de ΔSWE frente a M0. Es la mejora del CRPS sobre la climatología; el CRPS mide el error de toda la distribución prevista, no solo de un valor.

**Métricas secundarias:**
- MSSS, la mejora del error cuadrático frente a M0;
- correlación de Spearman;
- RPSS por terciles;
- MAE;
- sesgo;
- histograma de rangos y diagrama de fiabilidad, cuando haya suficientes casos.

**Hipótesis primarias:** H-P1, H-P2 y H-P3. En cada una, M0c-R supera a M0 en ΔSWE a 2.100 m en llano. Hay 6 dominios por familia.

**Criterio, para cada dominio y periodo; deben cumplirse las tres condiciones:**
1. CRPSS > 0, con la cota inferior unilateral del bootstrap al 95 % por encima de 0, tras corregir por Holm dentro de cada familia de 6 dominios.
2. Mismo signo en 1991–2001 y en 2002–2025.
3. Habilidad positiva también en los G_SWE o L_SWE del mismo periodo. Si solo hay habilidad en ΔSWE y no en G ni en L, se informa como «habilidad por el estado inicial (capacidad c)», no como habilidad para anticipar acumulación o pérdidas.

**Afirmaciones sobre la temporada completa:** controlan además la multiplicidad entre los 3 periodos, con Holm sobre las 18 pruebas.

**Análisis secundarios, descriptivos y sin afirmaciones de habilidad confirmada:** M0b, M0d, M0c-O, el resto de estratos, variables e inicializaciones, y las capacidades a, b y c por separado.

## 8. Factores de confusión declarados
- **S2M es un modelo,** con la ruptura de su forzamiento en 2002.
- **Las anclas tienen independencia UNKNOWN,** y sin independencia confirmada no hay clase A.
- **La dependencia aritmética entre el estado inicial y las pérdidas** (§1) puede inflar la habilidad de M0c en P3. Por eso existe la condición 3 de §7.
- **Tendencia:** con calentamiento, la climatología M0 favorece a los inviernos recientes. M0b sirve de control.
- **El Niño:** análisis exploratorio E1 (v0.3). No entra en el criterio.

## 9. Orden de ejecución y puertas
| PR | Contenido | Condición |
|---|---|---|
| 1 (este) | Protocolo v0.4 | Borrador hasta la congelación |
| 2 | Climatologías bimestrales: código, auditoría de cobertura y distribuciones marginales y umbrales descriptivos de cada periodo | Puede hacerse antes de congelar. **El código de las matrices de transición se escribe y se prueba con datos sintéticos, pero no se ejecuta sobre S2M ni se consultan sus resultados hasta la congelación** |
| 3 | Persistencia y análogos: backtesting, habilidad, incertidumbre y estabilidad | **Solo después de congelar** |
| 4 | Hindcasts de SEAS5 (Parte B) | Clave del CDS, sistema confirmado y protocolo congelado |

Verificación independiente: pendiente de que haya agentes disponibles (a partir del 2-12-2026). Ningún resultado de habilidad se da por bueno sin ella.

## 10. Scripts previstos (`scripts/sepi/`, opcionales y fuera del CI)
| Script | PR | Función |
|---|---|---|
| `phase04_targets_bimonthly.py` | 2 | ΔSWE, G, L, G_HS, días con umbral y fecha de formación por periodo, dominio y estrato |
| `phase04_climatology.py` | 2 | Distribuciones marginales y umbrales por periodo; solo descriptivo |
| `phase04_transitions.py` | 2 (código) / 3 (ejecución) | Matriz de transiciones entre periodos; bloqueado hasta la congelación |
| `phase04_persistence.py` | 3 | M0, M0b y M0c-R con origen móvil |
| `phase04_analogues.py` | 3 | M0d-R |
| `verify_phase04.py` | 3 | Verificador independiente, escrito por otro agente a partir de este documento |
| `earthkit_ingest.py`, `align_hindcasts.py`, `verify_meteorology.py`, `bias_adjustment.py`, `phase05_backtest.py` | 4 | Parte B (v0.3, §11) |

Salidas: `SEPI_DATA/f04/`, con copia de las tablas en `docs/datos/sepi-f04/`.

## 11. Parte B: SEAS5 (se mantiene de v0.3, adaptada a los periodos)
- **Datos:**
  - **SEAS5** `seasonal-monthly-single-levels`, con las inicializaciones de §4.
  - **Hindcast:** 1981–2016, 36 inviernos y 25 miembros.
  - **Previsiones reales:** 2017–2025, 51 miembros.
  - **ERA5:** referencia meteorológica (validación A).
- **Caja regional propuesta:** 42–43° N y 0,5–3° E. **Unidades:** `snow_depth` en m de equivalente en agua.
- **Predictores:** tope de 3 por modelo. Candidatos: anomalías de T2m, de precipitación o nevada, de `snow_depth`, y un índice de régimen basado en la presión a nivel del mar.
- **Corrección del sesgo:** solo dentro de cada pliegue; es una hipótesis, no una mejora presupuesta.
- **Criterio:** SEAS5 tiene que añadir habilidad frente al mejor M0 (CRPSS de M5 frente a M0c > 0) con el mismo criterio de §7. Hindcast y previsión real tienen distinto número de miembros, así que se usan puntuaciones «fair».
- **Herramientas por auditar** (licencia UNKNOWN): xskillscore e ibicus.

## 12. Decisiones pendientes del titular (antes de congelar)
1. Confirmar el umbral y la persistencia de la fecha de formación del manto (propuesta: HS ≥ 30 cm durante 7 días).
2. Confirmar el conjunto de k y de ponderaciones de los análogos (§5).
3. Fuente candidata para los modelos O, o aceptar que queden en UNKNOWN.
4. Parte B: caja, índice de régimen y System 51 o 5.
5. Fecha de congelación y semilla del bootstrap.

## 13. Registro de decisiones
| Fecha | Decisión | Tipo |
|---|---|---|
| 28-11-2026 | v0.3: borrador solo con SEAS5 (PR #72) | Borrador |
| 28-11-2026 | v0.4: tres periodos; ΔSWE como objetivo primario y G/L como secundarios; d100 excluido en P1 y limitado a 2.100 m en P2 y P3; nieve nueva y lluvia sobre nieve en UNKNOWN; separación de modelos R y O; hipótesis H-P1 a H-P3 con Holm; origen móvil 1968–1990 / 1991–2025; matrices de transición bloqueadas hasta la congelación. Aprobado metodológicamente por el titular; pendiente de congelación | Borrador |
