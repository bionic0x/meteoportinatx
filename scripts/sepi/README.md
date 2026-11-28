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
python scripts/sepi/audit_nivo.py             # estaciones de la red nivo en el Pirineo oriental
python scripts/sepi/phase03.py                # F03 v1 exploratoria (inmutable; necesita out_catalogo.csv de phase01)
python scripts/sepi/phase03_v2.py             # F03 v2 según el protocolo congelado (necesita la salida de phase03.py)
```

Dependencias: `numpy`, `pandas`, `scipy`, `xarray` con `netCDF4`.

### Ingesta estacional (opcional, experimental)
`earthkit_ingest.py` prepara las peticiones de SEAS5 al CDS. Necesita un entorno aparte con [`requirements-earthkit.txt`](requirements-earthkit.txt) (unos 1,2 GB con eccodes) y la clave del CDS del titular en `~/.cdsapirc`, nunca en el repositorio. Por defecto solo muestra las peticiones; descarga únicamente con `--download`. Uso, puertas y licencias en [`docs/SEPI-EARTHKIT.md`](../../docs/SEPI-EARTHKIT.md); validación en [`docs/SEPI-P-PROTOCOLO.md`](../../docs/SEPI-P-PROTOCOLO.md), que todavía es un borrador.

```bash
python scripts/sepi/earthkit_ingest.py --system 51 --years 1993   # solo muestra las peticiones; sin red
```

| Script | Salidas en `SEPI_DATA` |
|---|---|
| `phase01.py` | `out_catalogo.csv`, `out_correlaciones.csv`, `out_h6.csv`, `out_xema_*.csv`, `out_mf_*.csv`, `out_indices.csv` |
| `phase02.py` | `out_fase02.csv`, `out_fase02_tests.csv` |
| `phase02b.py` | `out_fase02b.csv`, `out_fase02b_tests.csv` |
| `sens_trans.py` | `out_sens_transiciones.csv` |
| `fetch_hist.py` | `s2m/`, `s2m_ref_69_74.csv.gz`, `mfquot/`, `nivose/`, `meta/`, `descarga.json` |
| `audit_quot.py` | `out_cobertura_mf_nieve.csv` |
| `audit_nivo.py` | `nivose_pyr_or.csv.gz`, `out_nivo_estaciones.csv` |
| `phase03.py` | `out_f03_metricas.csv`, `out_f03_ranking.csv`, `out_f03_anclas.csv`, `out_f03_resumen.txt` |
| `phase03_v2.py` | `f03v2/*.csv` (copia en `docs/datos/sepi-f03-v2/`) |
| `earthkit_ingest.py --download` | `cds/seasonal/<sha256>.grib` y `<sha256>.json` (petición, SHA-256 y hora) |

Bootstrap con semillas fijas: dos ejecuciones sobre los mismos datos dan las mismas cifras. Los datos abiertos pueden revisarse con el tiempo; las cifras de `docs/SEPI.md` corresponden a la descarga del 26-11-2026.
