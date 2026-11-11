# Informe 1 · Modelo meteorológico y verificación

**Lentes:** Statistician, Model QA Specialist, Spatial Data Scientist. **Estado:** auditoría preliminar sustentada en código; no hay reconstrucción histórica ni scores reales calculados.

## A. Qué modelo existe realmente

El motor costero `fuse(channels, hr_gate)` extrae el máximo institucional `inst`, de observaciones `obs_max` y de modelos `mod_max` (este último limitado a nivel `alert`), y toma `max(inst, obs_max, mod_max)`. Una regla adicional puede alcanzar `alarm` por **dos observaciones independientes del mismo fenómeno, al menos una local**, o por dos ejecuciones HR consecutivas más señal observada local. La salida pasa por histéresis y reglas de precaución. Los umbrales numéricos residen en `CFG`. Es un **sistema de reglas experto**, no una estimación estadística directa de `P(lluvia > x | información)`.

La independencia declarada por nombre de canal no garantiza independencia física: estaciones vecinas comparten episodio; satélite/radar/pluviómetros pueden compartir precipitación; ensembles de una misma familia no son fuentes independientes. No contar `50 + 30 + 20` miembros como 100 modelos. En Pirineo, `pirineo_meta.py` ya agrupa familias `ecmwf`, `ncep`, `dwd`, y su docstring señala que la fracción de miembros no es probabilidad calibrada. La calidad probabilística no puede proclamarse sin pares medidos.

## B. Producto de verificación antes de modificar el algoritmo

### Registro congelado `forecast_issued`

Campos mínimos: `event_id`, `domain_id`, `site_id`, lat/lon, altitud, ventana válida UTC, `forecast_issued_at` UTC, `provider`, `provider_run_at` UTC, modelo y familia, `forecast_horizon_h`, `variable`, `threshold`, `value/probability_raw`, `unit`, `source_url/licence`, `code_commit`, `model_config_hash`, `dataset_hash`, `ingested_at`, `status`.

Regla: **ingestión antes de `valid_from`** para predicción estricta. Si se archiva después, el registro pasa a `HINDCAST` y se excluye de puntuaciones prospectivas. No permitir sustituir valores emitidos por actualizaciones posteriores. Guardar manifest e índice append-only fuera de Render Free; SQLite local es índice y caché, no única verdad.

### Registro `observation_verified`

Campos: `event_id`, `station_id`, red y licencia, lat/lon, altitud y exposición, `observed_at` UTC, `received_at`, fenómeno/variable, unidad, validez de calibración, calidad, `validated_by`, flags de hueco/demora/reinicio de acumulado, fuente primaria, versión de procesado. Para nieve añadir ladera/orientación y si es nieve natural vs nieve producida; para mar, coordenadas y periodo de agregación; para radar, resolución, píxeles, proyección y hora del barrido.

**Regla de pareo:** mismo fenómeno y unidad, ubicación compatible definida a priori, intervalo validado idéntico (o agregación documentada), horizonte definido, calidad no `UNKNOWN`. Guardar n de pares y n excluidos, con motivo. No imputar ausencia como 0.

## C. Métricas y baselines

| Producto | Métrica primaria | Secundarias | Baseline obligatorio |
|---|---|---|---|
| Avisos por umbral 1h / 6h / 12h | CSI, POD, FAR, matriz de confusión | Tasa de falsas alarmas por 100 días, lead time | AEMET CAP / persistencia / climatología, según variable |
| Probabilidades declaradas, si se habilitan | Brier Score y skill | Diagrama de fiabilidad, tamaño muestra por bin, ROC/PR cuando proceda | Frecuencia climatológica por estación/mes |
| Cantidades de precipitación | MAE, sesgo, distribución de errores | Error condicional >p95, FSS para campos | Persistencia y pronóstico base de proveedor |
| Nieve nueva/acumulada | MAE, sesgo por cota/aspecto | Error de cota, incertidumbre de ratio nieve/agua | Referencia oficial local disponible |
| Familia ensemble en horizonte 3–15d | CRPS o proper scoring por variable | Spread-skill, rank histograms | Climatología y ensemble sin ajustes |
| Radar 0–120min | Error vector/desplazamiento y llegada | CSI/FSS por lead 10/30/60/120min | Persistencia Lagrangiana y Euleriana |
| Alertas de episodio | Tiempo desde primera señal observable; falsas alarmas | Cobertura/frescura y degradación | Reglas actuales congeladas |

Nunca comunicar skill numérico ni «P(...)» calibrada antes de disponer de dataset. Los intervalos de confianza deben agrupar por episodio (bloques temporales/espaciales), no por pixel ni por frame como si fueran independientes.

## D. Diseño experimental

1. **Fase 0, instrumentación:** 90 días de pronósticos congelados prospectivos; si se incorpora un histórico, marcarlo `HINDCAST` y validar sesgo de selección. Un año o más es deseable para estacionalidad; 90 días solo prueba la tubería.
2. **Fase 1, baseline:** calcular un informe mensual por variable y horizonte, separado por régimen DANA/frente/convectivo estable/nevadas y por zona, sin ajustar parámetros con la ventana de prueba.
3. **Fase 2, calibración:** únicamente donde el nº de episodios independientes permita estimación estable, ajustar `isotonic`/logistic o parámetros simples, con validación walk-forward y test sellado. No usar la fracción de miembros como probabilidad de alerta oficial.
4. **Fase 3, shadow mode:** competir modelo candidato vs modelo de reglas actual durante >=30 días/episodios representativos; comparar métrica pre-registrada y alerta adversa. No cambiar el eje institucional.
5. **Fase 4, control de cambios:** nueva política solo con reducción documentada de error y sin deterioro inaceptable de falsa tranquilidad, incluidas condiciones de fuentes `UNKNOWN`.

**Control estadístico:** antes de declarar ganancia, informar denominador: n pronósticos, n días, n episodios independientes, n estaciones y n de alertas extremas. El CI unitario no es validación meteorológica.

## E. Auditoría geoespacial específica (P0/P1)

- `sea_model_check`: actualmente obtiene `max(wave_height)` modelado y lo contrasta con lectura reciente máxima de boyas NE, no apareada a misma coordenada y instante. Rehacer como `(model_gridpoint_near_buoy, valid_time, depth/exposure, obs_hs)` y comparar solo `Hs(t)` con tolerancia definida; sin pareo, `UNKNOWN/NO_COMPARABLE`.
- Vecindad `±17 km` en la vista: verificar cálculo geodésico efectivo por pares/estaciones y cambiar etiqueta basada en radios del algoritmo, no en texto hardcoded.
- Cota Pirineo: `summarize_points(points, pois, prof.get('sur', []))` ancla el resumen a perfil sur. Separar ladera N/S y orientación, altitud exacta del sitio, exposición viento, inversión, nieve natural y nieblas. Evitar extrapolación del perfil sur a ladera norte.
- Radar: capturar al menos 2–3 frames georreferenciados de calidad controlada, estimar campo de movimiento por correlación cruzada/óptical flow con máscara de clutter y cambios radiométricos; entregar vector m/s y ETA con intervalos, no solo `distancia_acercándose`. Distinguir **advectiva** de **crecimiento/decadencia** de celdas.
- Capacidad: testar primero con pares sintéticos (traslación conocida ±error y crecimiento in situ), luego 10 episodios independientes. Si no hay dos frames utilizables, salida `MOTION_UNKNOWN`.

## F. Criterios de aceptación

- Los pares pronóstico-observación son reproducibles a partir de manifiestos, no solo del estado SQLite.
- Se pueden reconstruir 20 ejemplos y justificar por qué entraron o no al benchmark; ninguna observación comunitaria no verificada se etiqueta como verdad.
- Módulos de oleaje/nieve/radar fallan cerrado a ausencia/calidad mala y evitan falsa precisión.
- Toda mejora reporta métricas vs baseline, incertidumbre y trade-off de falsas alarmas.

**Resultado ahora:** `MODEL SKILL = NOT MEASURED`. Ningún algoritmo nuevo pasa a la web en esta entrega.
