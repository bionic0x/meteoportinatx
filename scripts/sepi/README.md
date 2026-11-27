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
python scripts/sepi/fetch_hist.py             # ~700 MB de tráfico; S2M CSV 1958→, QUOT 66/09, red nivo; sin credenciales
python scripts/sepi/audit_quot.py             # auditoría de la nieve observada por estación e invierno
python scripts/sepi/phase03.py                # 58 inviernos por dominio con S2M, anclas y prueba de 2002 (necesita out_catalogo.csv de phase01)
```

Dependencias: `numpy`, `pandas`, `scipy`, `xarray` con `netCDF4`.

| Script | Salidas en `SEPI_DATA` |
|---|---|
| `phase01.py` | `out_catalogo.csv`, `out_correlaciones.csv`, `out_h6.csv`, `out_xema_*.csv`, `out_mf_*.csv`, `out_indices.csv` |
| `phase02.py` | `out_fase02.csv`, `out_fase02_tests.csv` |
| `phase02b.py` | `out_fase02b.csv`, `out_fase02b_tests.csv` |
| `sens_trans.py` | `out_sens_transiciones.csv` |
| `fetch_hist.py` | `s2m/`, `s2m_ref_69_74.csv.gz`, `mfquot/`, `nivose/`, `meta/`, `descarga.json` |
| `audit_quot.py` | `out_cobertura_mf_nieve.csv` |
| `phase03.py` | `out_f03_metricas.csv`, `out_f03_ranking.csv`, `out_f03_anclas.csv`, `out_f03_resumen.txt` |

Bootstrap con semillas fijas: dos ejecuciones sobre los mismos datos dan las mismas cifras. Los datos abiertos pueden revisarse con el tiempo; las cifras de `docs/SEPI.md` corresponden a la descarga del 26-11-2026.
