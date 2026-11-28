# ECMWF Earthkit en MeteoPortinatx (SEPI-EK-01)

**Estado:** integración mínima y opcional (28-11-2026). Earthkit **no** es dependencia del motor, ni de las consolas, ni del CI.

## Por qué opcional
- **Instalación pesada:** el meta-paquete `earthkit` 1.0.0 con eccodes 2.50 ocupa unos 1,2 GB de entorno.
- **El núcleo no lo necesita:** el motor y las consolas funcionan con la biblioteca estándar y pocas dependencias, y así deben seguir.
- **Dónde sí aporta:** en los scripts por lotes que leen GRIB/NetCDF del CDS (hindcasts de SEAS5, CERRA, ERA5) y calculan anomalías, percentiles de ensembles y regrids. Es decir, en SEPI-EK-02 y en la ingesta.

Instalación en un entorno aparte:

```bash
python -m venv ~/.venv-earthkit && . ~/.venv-earthkit/bin/activate
pip install -r scripts/requirements-earthkit.txt
```

Earthkit **no** elimina la autenticación del CDS. La clave la pone el titular en su entorno (`~/.cdsapirc`), nunca en el repositorio ni en prompts.

## Licencias (auditadas el 28-11-2026)

| Paquete | Versión | Licencia |
|---|---|---|
| earthkit, -data, -meteo, -transforms, -geo, -plots, -hydro, -utils | 1.0.0 / 1.3.1 / 1.3.0 / 1.0.0 / 1.2.0 / 1.0.4 / 1.4.0 / 1.0.4 | Apache-2.0 |
| earthkit-time | 0.1.8 (anterior a la 1.0) | Apache-2.0 |
| eccodes | 2.50.1 | Apache-2.0 |

- **Uso como dependencia:** compatible.
- **Código de ECMWF:** no se copia al repositorio. Si alguna vez se redistribuye, hay que conservar el NOTICE de Apache-2.0.
- **Datos de ECMWF y Copernicus:** se citan con su atribución (CC BY 4.0 o licencia de Copernicus, según el producto).

## Primer uso: el bulbo húmedo en montaña
La comparación con `earthkit.meteo.thermo.wet_bulb_temperature_from_dewpoint` (bisección IFS) a 1.700 y 2.100 m, con temperaturas entre −6 y +6 °C, da estas diferencias (OBSERVADO):

| HR | Stull (`wet_bulb_c`) frente a earthkit | Psicrométrica (`wet_bulb_psychro`) frente a earthkit |
|---|---|---|
| 40 % | ≤ 0,19 °C | ≤ 0,29 °C |
| 70 % | sesgo medio −0,5 °C (máx. 0,7) | ≤ 0,23 °C |
| 95 % | sesgo medio −0,26 °C | ≤ 0,17 °C |

**Conclusión:** Stull supone 1013 hPa y en montaña da un bulbo húmedo demasiado frío. El módulo Pirineo (`pirineo_meta.py`) ya usaba la ecuación psicrométrica. Este PR la aplica también en el diagnóstico diario por zonas (`zone_engine.daily_diagnostics`): cuando el proveedor da la cota del punto, se usa la presión estándar de esa cota; sin cota, se mantiene Stull. El campo `wet_bulb_method` indica cuál se usó.

**Efecto en la previsión de producción de nieve del 28-11-2026** (Masella y Font-Romeu, GEFS con 31 miembros, 28-nov a 12-dic): con la ecuación psicrométrica salen entre un 2 y un 5 % menos de horas-miembro con Tw ≤ −2 °C y Tw ≤ −4 °C. Es una diferencia pequeña, porque las noches del anticiclón eran secas y el sesgo de Stull crece con humedades intermedias. La conclusión de aquella previsión no cambia.

`tests/test_wet_bulb_reference.py` guarda valores de earthkit congelados como referencia externa. Así el CI comprueba la física sin instalar earthkit.

## Qué no hace este PR
- **Hindcasts y predictores** (SEPI-EK-02): necesitan la clave del CDS y un protocolo de validación fijado antes de mirar resultados.
- **Agentes de ECMWF** (`ecmwf/ecmwf-weather-skills`, SEPI-EK-03): no se instalan. El repositorio es Apache-2.0, con madurez «Emerging», y su README advierte de que no es apto para uso operativo. Su servidor MCP remoto (`mcp.ecmwf.int`) es un servicio externo y activarlo es decisión del titular.
- **F03 v2:** sin cambios.
