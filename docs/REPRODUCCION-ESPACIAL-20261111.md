# Caso real reproducido — diagnóstico espacial de oleaje (#8)

**Instantánea observada**, no sintética: GitHub Pages workflow [#43051163150](https://github.com/bionic0x/meteoportinatx/actions/runs/43051163150), commit `535c1e4e8abdf3b33fdc8b9111d7055dbe1a6c35`, artefacto `github-pages` id `13869591734` (SHA-256 del ZIP publicado: `2a3db47d765ff7615de78de4dc1147c2c80541a382efdab78ed74a05b8e9bc42`). Capa pública `portinatx/api/core.json` emitida a las **2026-11-11T15:43:48Z**. Los datos instrumentales proceden de PORTUS/Puertos del Estado; el modelo de Open-Meteo Marine, servido en el mismo snapshot. Valores copiados selectivamente a `tests/fixtures/spatial_20261111.json`; no es certificación independiente de la calidad de la medida.

| Campo | Boya Dragonera | Modelo en bahía de Portinatx |
|---|---:|---:|
| Coordenadas | 39.563, 2.097 | 39.145, 1.525 |
| Hora UTC | 11 nov 2026, 15:00 | 11 nov 2026, 15:00 |
| Hs | **0,82 m** | **0,50 m** |
| Hmax | 1,47 m | no comparable |
| Distancia entre puntos | \- | **67,7 km (Haversine)** |

**Reproducción:** `python -m unittest tests.test_spatial_real_20261111 -v`. El test usa estos valores reales archivados y aplica el código del motor: `sea_model_check` devuelve `NO_COMPARABLE` cuando el único modelo disponible es de la bahía, aunque las horas coincidan. Es incorrecto afirmar que el modelo infraestimó 0,32 m o computar error: la diferencia entre ubicaciones no es un residual temporal.

El adaptador actual `src_marine` ya solicita predicciones adicionales en la posición de las boyas y la función `sea_model_check` empareja observación y modelo con tolerancia **±30 minutos**; sin embargo, el snapshot público de `mar.json` y `series.json` **solo expone la serie en la bahía**, no las series `_buoys`. Por eso este caso verifica el **fallo cerrado de la comparación externa**, no demuestra todavía un par `PAIRED` real del adaptador interno ni habilidad predictiva.

**Pendente para cerrar #8:** capturar un dossier controlado con el modelo realmente extraído en la coordenada de Dragonera o Valencia, su `provider_run_at` y la observación PORTUS con bandera QC verificable. Congelar el par, reproducirlo de forma determinista y contrastar orientación/representatividad regional. No publicar datos propietarios ni convertir oleaje mar abierto en peligro dentro de la cala.
