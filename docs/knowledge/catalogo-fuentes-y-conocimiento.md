# Catálogo de fuentes, datos históricos y conocimiento científico — MeteoPortinatx

**Fecha:** 2026-11-11 · **Alcance:** Portinatx (Pitiusas) y Pirineo (Cerdanya/Andorra) · **Complementa:** `claude/especificacion-motor-conectores.md` (contrato de conectores) y `claude/auditoria-ante-meteoportinatx.md`.
**Implementación asociada en el repo:** `src/knowledge_base.py` (catálogo, priors y contrato sidecar), conector `src_contexto` (kind `context`, no entra en la fusión), diagnóstico `tw07_m` en el perfil de Pirineo y `docs/CATALOGO-FUENTES.md`.

> Regla de lectura: cada fila lleva un estado de verificación. **VERIFICADO** = visto en documentación oficial durante la investigación. **NO VERIFICADO** = recordado o inferido; no usar como hecho hasta comprobarlo. Nada de esta tabla se ha ejecutado contra el servicio real desde el entorno de trabajo (red restringida): ningún conector nuevo está *probado en vivo*.

## 1. Principios de integración (no negociables)

1. **El núcleo sigue siendo stdlib-only.** Todo lo que necesite `xarray`, `cfgrib`, `satpy`, `cdsapi`, `scores`, etc. vive en un **sidecar** con sus propias dependencias (workflow aparte) que escribe JSON validado. El núcleo lee ese JSON; si falta, está caducado o es inválido → `UNKNOWN` (`available=False`). Ausencia de dato ≠ calma.
2. **Contexto no es observación ni aviso.** Climatología, reanálisis y priors sinópticos se publican como `kind="context"`; el motor de fusión (`fuse`) solo mira `institutional`, `obs`, `model`, `ensemble`, así que **no pueden subir ni bajar el nivel**. Si en el futuro se quiere que influyan, hace falta decisión explícita y calibración.
3. **Un modelo nunca es una observación.** ERA5-Land, CERRA, CMEMS-modelo y similares son reanálisis/modelo: sirven de *prior* y de *percentil de contexto*, no de confirmación.
4. **Umbrales sin procedencia no se inventan.** Los umbrales de Meteoalerta no están en el Plan principal sino en sus Anexos 1/2 (no obtenidos); las cifras de prensa son inconsistentes. `CFG["rain_1h"]`, `rain_12h`, etc. quedan marcados **UNVERIFIED** en `THRESHOLD_PROVENANCE` y hay un placeholder `meteoalerta_annex1 = None`.
5. **Calibrar solo con eventos suficientes.** Fracción de miembros ≠ probabilidad. Solo se calibra en umbrales con ≥30 eventos; verificación por Brier/BSS, CRPS, FSS, SEDI con bootstrap por episodio y origen rodante.

## 2. Catálogo de fuentes

### 2.1 Copernicus
| Producto | Para qué sirve aquí | Acceso | Licencia | Estado |
|---|---|---|---|---|
| ERA5-Land (CDS) | Climatología horaria 9 km de T, precipitación, nieve en suelo; percentiles de contexto para Portinatx y Pirineo | `cdsapi` (sidecar) | CC-BY 4.0 (CDS/ADS/EWDS desde 2-jul-2025) | Licencia VERIFICADA; cobertura/latencia concretas NO VERIFICADAS |
| CERRA / CERRA-Land | Reanálisis regional ~5,5 km (mejor orografía pirenaica que ERA5) | CDS (sidecar) | CC-BY 4.0 | Existencia VERIFICADA; periodo exacto NO VERIFICADO |
| E-OBS | Rejilla observacional diaria (referencia de extremos) | CDS | CC-BY 4.0 (algunos conjuntos EWDS con restricciones) | Comprobar licencia por conjunto |
| DEM GLO-30 | Relieve 30 m (cotas, exposición, barlovento/sotavento) | Copernicus Data Space | Revisar condiciones del DEM | NO VERIFICADO |
| CMEMS (SST, oleaje, nivel) | SST como combustible convectivo; contexto de mar | `copernicusmarine` (sidecar) | Términos CMEMS | NO VERIFICADO el producto exacto |
| HR-S&I (nieve) | Cobertura/extensión de nieve en Pirineo | Copernicus Land | CC-BY | NO VERIFICADO resolución/latencia |
| EFAS / GloFAS | Contexto hidrológico (Segre, caudales) | EWDS | Algunos conjuntos no comerciales | Comprobar |

### 2.2 Archivos históricos (para verificación y climatología local)
| Fuente | Uso | Observaciones | Estado |
|---|---|---|---|
| OPERA / EURADCLIM | Radar compuesto europeo histórico → sesgo radar–pluviómetro, climatología de lluvia | Cobertura mediterránea/Baleares NO verificada | NO VERIFICADO |
| AEMET OpenData | Observación horaria y diaria | **No hay backfill horario**: hay que archivar B954/LEIB desde ya (de ahí la prioridad del ledger #7) | VERIFICADO el hecho del backfill |
| Meteocat XEMA | Estaciones catalanas (Cerdanya) | Licencia ambigua → tratar como no redistribuible hasta aclararla | Licencia NO VERIFICADA |
| Météo-France (AROME, vigilance, datos públicos) | Vertiente francesa, vigilancia | Etalab 2.0 | VERIFICADA |
| S2M (reanálisis de nieve de montaña) | Perfil de nieve por macizo | Cobertura Pirineos-Orientales a confirmar | NO VERIFICADO |
| MeteoNet | Dataset de ML con radar+estaciones (NW/SE Francia) | Útil para pruebas, no para el dominio | NO VERIFICADO |
| Open-Meteo Previous Runs / Single Runs / Historical Forecast | Backfill de pronósticos pasados para evaluar sesgo de modelos | Solo como **HINDCAST**, nunca PROSPECTIVE | VERIFICADO el concepto; cuotas a vigilar |

### 2.3 Tiempo real adicional (candidatas)
- `ecmwf-opendata` (IFS/AIFS abiertos) y MTG-LI vía `eumdac`/`satpy` (rayos): requieren sidecar; el repo ya consume MTG-LI por otra vía (`src_lightning`).
- AEMET OpenData CAP y Météo-France vigilance: ya cubiertos por CAP/MeteoAlarm; no duplicar raíz (`CHANNEL_ROOT`).

## 3. Conocimiento científico incorporado

1. **Fase de precipitación por bulbo húmedo.** En Cataluña (Casellas et al.) el umbral de bulbo húmedo en superficie para nieve vs no nieve ronda **0,7 °C** (Pierce, comparable, ≈0,77). La regla operativa del SMC combina la **isocero de bulbo húmedo** con la **tasa de precipitación**. Implementado como: constante `PRIORS["wet_bulb_snow_threshold_c"] = 0.7` (HIPÓTESIS hasta calibrar con observaciones locales), la rampa de `snow_frac` centrada en ese valor, y el diagnóstico `tw07_m` (altura donde el Tw del perfil cruza 0,7 °C). Los offsets de cota de copo/cuajado/acumulación existentes **no se modifican**.
2. **Lluvia intensa balear.** Prior cualitativo: episodios asociados a depresión aislada/vaguada con flujo bajo de componente E–SE sobre mar cálido, convergencia y transporte persistente de humedad. Se registra en `SYNOPTIC_PRIORS` como **hipótesis** con `used_in_fusion=False`.
3. **Aviso oficial = suelo, no confirmación** (ya en el motor). El prior climatológico nunca sustituye al aviso.

## 4. Mapa de huecos (investigación → componente)

| Hueco | Respuesta propuesta | Estado en el repo |
|---|---|---|
| Sin climatología local para decir «esto es p99» | Sidecar ERA5-Land/CERRA → tabla de percentiles → `percentile_rank` | Contrato y función implementados; sidecar real **pendiente** |
| Fase lluvia/nieve con Stull a 1013 hPa | Umbral 0,7 °C + diagnóstico `tw07_m` | Implementado (HIPÓTESIS) |
| Sin verificación de habilidad | Ledger #7 + archivo AEMET horario + scores | Ledger existe; sidecar de scores **pendiente** |
| Umbrales Meteoalerta sin procedencia | `THRESHOLD_PROVENANCE` + placeholder Anexo 1 | Implementado; **valores pendientes** de obtener los Anexos |
| SST/mar como combustible convectivo | Sidecar CMEMS → contexto | Contrato implementado; sidecar pendiente |
| Nieve en suelo/placas Pas de la Casa | HR-S&I/S2M → contexto | Contrato implementado; sidecar pendiente |

## 5. Contrato del sidecar (resumen)

Fichero `<dir>/<nombre>.json` con `schema=1`, `name`, `generated_at` (ISO con zona), `source`, `licence`, `domain` (`portinatx`/`pirineo`), `kind="context"` y `values`. Directorio por defecto `HOME/sidecar`, sobrescribible con `METEO_SIDECAR_DIR`. Estados de lectura: `ok`, `sin_datos`, `caducado`, `invalido`. Cualquiera distinto de `ok` → `UNKNOWN`. Valores no finitos, claves desconocidas de primer nivel o `generated_at` sin zona → `invalido`.

## 6. Pendiente (decisiones y trabajo)

1. Obtener Anexos 1/2 de Meteoalerta y cargar umbrales con procedencia.
2. Aclarar licencia Meteocat antes de redistribuir nada derivado.
3. Escribir el sidecar real (ERA5-Land/CERRA percentiles) y su workflow; probar con datos reales.
4. Calibrar 0,7 °C con observaciones de Cerdanya/Andorra (≥30 eventos).
5. Persistencia del ledger fuera de Render Free.
6. Abrir en GitHub los tres issues redactados (requiere acceso de escritura).

## 7. Qué no está verificado (lista corta)
Cobertura de OPERA/EURADCLIM en Baleares; periodos y latencias exactas de CERRA/ERA5-Land/HR-S&I; productos CMEMS concretos; licencia del DEM GLO-30 y de Meteocat; todos los conectores contra servicio real.
