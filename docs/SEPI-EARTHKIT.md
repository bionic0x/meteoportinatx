# SEPI-EK-01: ECMWF Earthkit en MeteoPortinatx

**Estado:** andamiaje experimental, no es una previsión. La F03 v1 y la v2 no cambian. Earthkit **no** es dependencia del motor, de las consolas ni del CI.

- **Protocolo de validación estacional:** [`SEPI-P-PROTOCOLO.md`](SEPI-P-PROTOCOLO.md) (borrador).
- **Entorno opcional:** [`scripts/sepi/requirements-earthkit.txt`](../scripts/sepi/requirements-earthkit.txt).

## Por qué opcional
- **La instalación pesa** unos 1,2 GB con eccodes, en la combinación probada el 28-11-2026 (detalle en el archivo de dependencias).
- **El núcleo no lo necesita:** el motor y las consolas funcionan con la biblioteca estándar y pocas dependencias, y así deben seguir.
- **Dónde aporta:** en los scripts por lotes que leen GRIB o NetCDF del CDS (hindcasts de SEAS5, ERA5, CERRA) y calculan anomalías, percentiles de ensembles y regrids.

## Adquisición
Instálalo en un entorno aparte con Python ≥ 3.11. Configura el CDS en local (`~/.cdsapirc`) y acepta las condiciones del conjunto de datos. **No subas nunca credenciales al repositorio ni las pongas en prompts.**

Antes de ejecutar, comprueba en el formulario de descarga del CDS el sistema de ECMWF, los años disponibles y los campos de la petición. System 51 es un candidato: no está confirmado que esté disponible en noviembre de 2026.

```sh
python -m venv ~/.venv-earthkit && . ~/.venv-earthkit/bin/activate
python -m pip install -r scripts/sepi/requirements-earthkit.txt
export SEPI_DATA=$HOME/sepi-data       # fuera del repositorio
python scripts/sepi/earthkit_ingest.py --system 51 --years 1993 1994 2016 2026            # solo muestra las peticiones
python scripts/sepi/earthkit_ingest.py --system 51 --years 1993 --download                 # tras comprobar el catálogo
python scripts/sepi/earthkit_ingest.py --system 51 --years 1993 --inspect <ruta>.grib
```

**Cómo funciona el script:**
- **Por defecto es una ejecución en seco**, sin descargar nada.
- **Cada petición pide una sola variable y un solo año,** sobre la rejilla completa para no depender de recortes que el CDS quizá no admita. Antes de ampliar, hay que estimar la cuota.
- **Cada artefacto bruto queda fuera del repositorio** con su SHA-256, la petición exacta y la hora de adquisición. Si una petición falla, no se fabrica ninguna previsión.

**Antes de convertir el GRIB:**
- Comprobar que el miembro, el inicio, el plazo, la rejilla y las unidades se conservan. Earthkit lo lee con su adaptador a xarray.
- Mantener separados, en todo lo que venga después, el sistema, el inicio, el miembro y el plazo.
- Verificar con los metadatos de la fuente las unidades y la agregación de la precipitación mensual.
- Recordar que `snow_depth` va en m de equivalente en agua.

## Licencias (auditadas el 28-11-2026)

| Paquete | Licencia |
|---|---|
| earthkit, -data, -meteo, -transforms, -geo, -plots, -hydro, -utils | Apache-2.0 |
| earthkit-time (0.1.8, anterior a la 1.0; no se usa) | Apache-2.0 |
| eccodes | Apache-2.0 |
| cdsapi | Apache-2.0 (SUPUESTO; verificar en G3) |

- **Uso como dependencia:** compatible.
- **Código de ECMWF:** no se copia al repositorio. Si alguna vez se redistribuye, hay que conservar el NOTICE.
- **Datos de Copernicus:** se citan con la atribución de su licencia.

## Bulbo húmedo en montaña (referencia externa)
La comparación con `earthkit.meteo.thermo.wet_bulb_temperature_from_dewpoint` (bisección de la IFS) a 1.700 y 2.100 m, con temperaturas entre −6 y +6 °C, da estas diferencias (OBSERVADO):

| HR | Stull (`wet_bulb_c`) frente a earthkit | Psicrométrica (`wet_bulb_psychro`) frente a earthkit |
|---|---|---|
| 40 % | ≤ 0,19 °C | ≤ 0,29 °C |
| 70 % | sesgo medio −0,5 °C (máx. 0,7) | ≤ 0,23 °C |
| 95 % | sesgo medio −0,26 °C | ≤ 0,17 °C |

- **Por qué hay sesgo:** Stull supone 1013 hPa y en montaña da un bulbo húmedo demasiado frío.
- **Qué usa ahora el motor:** el módulo Pirineo (`pirineo_meta.py`) ya usaba la ecuación psicrométrica. Desde el PR #71, `zone_engine.daily_diagnostics` también la usa a la presión estándar de la cota del punto. Sin cota, se mantiene Stull, y el campo `wet_bulb_method` indica qué método se usó.
- **Efecto en la previsión de producción de nieve del 28-11-2026** (Masella y Font-Romeu, GEFS con 31 miembros): entre un 2 y un 5 % menos de horas-miembro con Tw ≤ −2 y Tw ≤ −4 °C. La conclusión no cambia.
- **Test:** `tests/test_wet_bulb_reference.py` congela valores de earthkit-meteo 1.3.0. Así el CI comprueba la física sin instalar earthkit.
- **Límite:** la referencia también es un cálculo modelizado, no una medición, y la presión usada es la estándar de la cota, no la real.

## Hoja de ruta
- **EK-02:** validación de SEAS5 según [`SEPI-P-PROTOCOLO.md`](SEPI-P-PROTOCOLO.md). Hindcasts de 1981–2016, objetivos de diciembre–enero y de diciembre–abril, y preprocesado siempre dentro de cada pliegue de entrenamiento. No se afirma ninguna capacidad de predicción sin habilidad frente a la climatología.
- **EK-03:** evaluar `ecmwf/ecmwf-weather-skills`. Es Apache-2.0, con madurez «Emerging», y no es apto para uso operativo. Hay que revisar su licencia y los permisos de sus herramientas antes de importar nada. Su servidor MCP remoto (`mcp.ecmwf.int`) es un servicio externo y activarlo es decisión del titular. La reducción de escala orográfica, el bulbo húmedo y los productos van por separado. Interpolar no aumenta la resolución.
- **Discontinuidad de 2002 con CERRA-Land:** línea de trabajo aparte.

## Puertas
| Puerta | Condición |
|---|---|
| G0 | Peticiones en seco revisadas |
| G1 | Primer GRIB descargado con autenticación y manifiesto verificado |
| G2 | El decodificado de earthkit conserva las coordenadas de ensemble y tiempo y las unidades |
| G3 | Dependencias fijadas y CI en verde |
| G4 | Habilidad y calibración del hindcast demostradas antes de emitir probabilidades |

Ninguna de las cinco puertas se ha ejecutado todavía.

Documentación: https://earthkit-data.readthedocs.io/en/latest/tutorials/source/cds.html y https://cds.climate.copernicus.eu/datasets/seasonal-monthly-single-levels?tab=download
