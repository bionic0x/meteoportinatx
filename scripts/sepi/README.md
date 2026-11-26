# SEPI — scripts de análisis

Línea de investigación experimental sobre los inviernos de nieve excepcional en el Pirineo oriental. Diseño y resultados en [`docs/SEPI.md`](../../docs/SEPI.md). No produce avisos ni pronósticos operativos.

Los datos y las salidas viven **fuera del repositorio**, en la carpeta que indique `SEPI_DATA`.

```bash
export SEPI_DATA=$HOME/sepi-data              # fuera del repo
python scripts/sepi/fetch_data.py             # ~190 MB; XEMA, Météo-France MTO_1H y NOAA CPC; sin credenciales
python scripts/sepi/phase01.py                # catálogo de inviernos, teleconexiones, H6 descriptiva
python scripts/sepi/phase02.py                # H6 y H1/H2 con precipitación independiente
python scripts/sepi/phase02b.py               # control del dominio oeste
python scripts/sepi/sens_trans.py             # sensibilidad de la señal de transiciones
```

Dependencias: `numpy`, `pandas`, `scipy`, `xarray` con `netCDF4`.

| Script | Salidas en `SEPI_DATA` |
|---|---|
| `phase01.py` | `out_catalogo.csv`, `out_correlaciones.csv`, `out_h6.csv`, `out_xema_*.csv`, `out_mf_*.csv`, `out_indices.csv` |
| `phase02.py` | `out_fase02.csv`, `out_fase02_tests.csv` |
| `phase02b.py` | `out_fase02b.csv`, `out_fase02b_tests.csv` |
| `sens_trans.py` | `out_sens_transiciones.csv` |

Bootstrap con semillas fijas: dos ejecuciones sobre los mismos datos dan las mismas cifras. Los datos abiertos pueden revisarse con el tiempo; las cifras de `docs/SEPI.md` corresponden a la descarga del 26-11-2026.
