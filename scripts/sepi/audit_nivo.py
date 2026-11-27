"""SEPI — lista de estaciones de la red nivo-météorologique en el Pirineo oriental (1996→hoy).

Filtra los ficheros nivo_AAAA.csv.gz por una caja (lat < 43,1; 0,8 < lon < 3,2) y lista cada estación
(id WIGOS, nombre, altitud) con su primer y último año y el número de espesores válidos.
Los ficheros de 2025 en adelante usan «;» como separador. Las estaciones antiguas pueden no tener id WIGOS.
Salidas en SEPI_DATA: nivose_pyr_or.csv.gz y out_nivo_estaciones.csv.
"""
import glob
import os

import pandas as pd

_REPO = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DATA = os.path.realpath(os.environ.get("SEPI_DATA", ""))
if not os.environ.get("SEPI_DATA") or os.path.commonpath([_REPO, _DATA]) == _REPO:
    raise SystemExit("Define SEPI_DATA con una carpeta fuera del repositorio (ver scripts/sepi/README.md).")
os.chdir(_DATA)

U = ["lat", "lon", "geo_id_wigos", "Altitude", "name", "validity_time", "ht_neige"]
rows = []
for f in sorted(glob.glob("nivose/nivo_*.csv.gz")):
    sep = "," if set(U) <= set(pd.read_csv(f, nrows=0).columns) else ";"
    d = pd.read_csv(f, usecols=U, sep=sep, dtype={"geo_id_wigos": str})
    d = d[(d.lat < 43.1) & (d.lon > 0.8) & (d.lon < 3.2)]
    d["anio"] = int(os.path.basename(f)[5:9])
    rows.append(d)
d = pd.concat(rows)
d.to_csv("nivose_pyr_or.csv.gz", index=False)
g = (d.fillna({"geo_id_wigos": "(sin id)"}).groupby(["geo_id_wigos", "name", "Altitude"])
     .agg(lat=("lat", "first"), lon=("lon", "first"), desde=("anio", "min"), hasta=("anio", "max"),
          registros=("ht_neige", "size"), espesores_validos=("ht_neige", lambda s: int(s.notna().sum())))
     .reset_index().sort_values(["desde", "name"]))
g.to_csv("out_nivo_estaciones.csv", index=False)
pd.set_option("display.width", 200)
print(g.to_string(index=False))
