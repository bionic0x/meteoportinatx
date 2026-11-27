"""SEPI — descarga de las series largas abiertas (1968–hoy) que usa phase03.py.

Uso:  SEPI_DATA=/ruta/fuera/del/repo python scripts/sepi/fetch_hist.py
Sin credenciales. Unos 700 MB de tráfico; en disco quedan ~60 MB tras filtrar.

Fuentes (Météo-France, Licence Ouverte 2.0), descargadas desde el espejo público de Météo-France
en OVH, que publica los mismos ficheros que enlazan las fichas de data.gouv.fr:
- S2M en CSV («Données de Modèle de Simulation Nivologique», REF_CC/NIVO), 1958→hoy. Se conservan
  los macizos 64–74 (Pirineo francés y Andorra = 71) y se extrae una tabla reducida para phase03:
  macizos 69–74, cotas 1200–2400 m, terreno llano y N 20°.
- Observación diaria por departamento (QUOT 66 y 09, RR-T-Vent y autres-parametres), con
  HNEIGEF y NEIGETOT06.
- Red nivo-météorologique (OBS/NIVOSE), 1996→hoy.
- Lista de estaciones (GeoJSON 66 y 09) y descriptivo de la climatología diaria.

El CSV S2M es un canal de publicación distinto de la versión científica AERIS v2020.2
(doi:10.25326/37): no se mezclan. La fecha de descarga queda en descarga.json.
"""
import datetime
import gzip
import json
import os
import shutil
import urllib.error
import urllib.request

import pandas as pd

MF = "https://meteofrance.s3.sbg.io.cloud.ovh.net"
BASE = os.environ.get("SEPI_DATA", "")
_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOY = datetime.date.today()


def get(url, dest, timeout=600):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return True
    tmp = dest + ".part"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
        os.replace(tmp, dest)
        return True
    except (urllib.error.URLError, OSError) as e:
        print("  error", e, url)
        if os.path.exists(tmp):
            os.remove(tmp)
        return False


def s2m_year(y):
    """Descarga un año S2M y conserva solo los macizos del Pirineo (64–74)."""
    dest = os.path.join(BASE, "s2m", f"s2m_pyr_{y}.csv.gz")
    if os.path.exists(dest) and y < HOY.year:
        return True
    raw = os.path.join(BASE, "s2m", f"_raw_{y}.csv.gz")
    if not get(f"{MF}/data/REF_CC/NIVO/donnees_nivologiques_{y}.csv.gz", raw):
        return False
    with gzip.open(raw, "rt") as fi, gzip.open(dest + ".part", "wt") as fo:
        head = fi.readline()
        fo.write(head)
        for line in fi:
            m = int(line.split(";", 1)[0])
            if 64 <= m <= 74:
                fo.write(line)
    os.replace(dest + ".part", dest)
    os.remove(raw)
    return True


def s2m_reducido(y0=1958):
    out = []
    for y in range(y0, HOY.year + 1):
        f = os.path.join(BASE, "s2m", f"s2m_pyr_{y}.csv.gz")
        if not os.path.exists(f):
            continue
        d = pd.read_csv(f, sep=";")
        sel = (d.num_massif.between(69, 74) & d.altitude.isin([1200, 1500, 1800, 2100, 2400])
               & (((d.exposition == -1) & (d.pente == 0)) | ((d.exposition == 0) & (d.pente == 20))))
        out.append(d.loc[sel, ["num_massif", "dat", "altitude", "exposition", "pente", "neigetot", "equivalent_eau"]])
    pd.concat(out).to_csv(os.path.join(BASE, "s2m_ref_69_74.csv.gz"), index=False)


def main():
    if not BASE or os.path.commonpath([_REPO, os.path.abspath(BASE)]) == _REPO:
        raise SystemExit("Define SEPI_DATA con una carpeta fuera del repositorio.")
    for sub in ("s2m", "mfquot", "nivose", "meta"):
        os.makedirs(os.path.join(BASE, sub), exist_ok=True)
    fallos = []
    for y in range(1958, HOY.year + 1):
        if not s2m_year(y):
            fallos.append(f"S2M {y}")
    s2m_reducido()
    for d in ("66", "09"):
        for per in ("previous-1950-2024", "latest-2025-2026", "avant-1949"):
            for fam in ("RR-T-Vent", "autres-parametres"):
                f = f"Q_{d}_{per}_{fam}.csv.gz"
                if not get(f"{MF}/data/synchro_ftp/BASE/QUOT/{f}", os.path.join(BASE, "mfquot", f)):
                    fallos.append(f)
        get(f"{MF}/data/stations/stations_{d}.geojson", os.path.join(BASE, "meta", f"stations_{d}.geojson"))
    for y in range(1996, HOY.year + 1):
        if not get(f"{MF}/data/synchro_ftp/OBS/NIVOSE/nivo_{y}.csv.gz", os.path.join(BASE, "nivose", f"nivo_{y}.csv.gz")):
            fallos.append(f"nivo {y}")
    get(f"{MF}/data/synchro_ftp/BASE/A_LIRE_Donnees_quotidiennes_journee_climatologique.csv",
        os.path.join(BASE, "meta", "A_LIRE_quot.csv"))
    json.dump({"fecha_descarga": HOY.isoformat(), "origen": MF, "s2m_canal": "CSV Météo-France (REF_CC/NIVO)",
               "fallos": fallos}, open(os.path.join(BASE, "descarga.json"), "w"), ensure_ascii=False, indent=1)
    print("Fallos:", fallos or "ninguno", "| listo en", os.path.abspath(BASE))
    print("Nota: los nombres de periodo de QUOT (previous-1950-2024, latest-2025-2026) cambian cada año.")


if __name__ == "__main__":
    main()
