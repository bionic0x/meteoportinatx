# Tablas de SEPI-GEO-01

Generadas por `scripts/build_terrain_derivatives.py`, `compare_orografia.py` y `verify_terrain.py` a partir de **Copernicus DEM GLO-30 y GLO-90** (© DLR e.V. 2010-2014 y © Airbus Defence and Space GmbH 2014-2018, proporcionado en el marco de COPERNICUS por la Unión Europea y la ESA). Son de diagnóstico: no se usan en el motor. Método y resultados en [`../../SEPI-GEO-01.md`](../../SEPI-GEO-01.md).

| Fichero | Contenido |
|---|---|
| `points_comparison.csv` | Por punto, variable y variante (V0, V0r, V1k, V3k, V1, V2, V3): altitud, CPI, TPI de la caja del motor, TPI a 250 m–5 km, pendiente, orientación y factor de vista del cielo |
| `terrain_statistics.csv` | Sesgo, MAE, RMSE, mediana, P95, máximo de \|Δ\| y Spearman por variable y comparación; para todos los puntos, cimas, pueblos y estaciones |
| `summit_validation.csv` | 44 cimas × 2 DEM × 4 métodos (píxel próximo, bilineal, máximo en 90 m y en 250 m) frente a la cota de referencia |
| `exposure_by_sector.csv` | Por punto, variante (V1, V3) y sector de procedencia (16): altura y distancia de la barrera, ángulo de abrigo y pendiente de barlovento |
| `manifest.json` | SHA-256 de las entradas, proyección, dominio, parámetros y estado de NODATA |
| `verify_report.json` | Resultado de las comprobaciones de coherencia (no es la verificación independiente) |

Unidades: metros, grados y el factor de vista del cielo sin unidades (1 = cielo libre). NODATA vacío = desconocido, nunca cero.
