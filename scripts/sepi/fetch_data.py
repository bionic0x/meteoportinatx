"""SEPI — descarga de los datos abiertos que usan phase01/02/02b y sens_trans.

Uso:  SEPI_DATA=/ruta/fuera/del/repo python scripts/sepi/fetch_data.py
Crea xema/, mf/ e idx/ dentro de SEPI_DATA. No necesita credenciales.
Unos 190 MB. Los datos no se commitean.

Fuentes:
- XEMA (Meteocat, datos abiertos Socrata, dataset nzvn-apee): variable 38 (espesor de nieve)
  y variable 35 (precipitación), agregadas por día. Atención: la variable 38 está en mm hasta
  el 14-11-2021 y en cm desde el 15-11-2021; phase01.py lo corrige.
- Météo-France MTO_1H horario, servido por AERIS/IPSL en THREDDS.
- NOAA CPC: NAO y AO diarias, teleconexiones mensuales, ONI, QBO.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("SEPI_DATA", ".")
SOCRATA = "https://analisi.transparenciacatalunya.cat/resource/nzvn-apee.json"
THREDDS = ("https://thredds-su.ipsl.fr/thredds/fileServer/aeris_thredds/actrisfr_data/"
           "665029c8-82b8-4754-9ff4-d558e640b0ba/{y}/{code}_{name}_MTO_1H_{y}.nc")
XEMA = ["Z3", "Z9", "DG", "ZC", "Z1", "Z2", "Z5", "Z6", "Z7", "ZB", "VS"]
MF = {  # código: (nombre en el fichero, primer año)
    "66067402": ("PUIGMAL-NIVOSE", 2009), "66204400": ("CANIGOU-NIVOSE", 1996),
    "09285400": ("PORT_D_AULA-NIVOSE", 1995), "66082004": ("FORMIGUERES", 2000),
    "66202001": ("TARGASONNE", 2017), "09024004": ("ASTON", 2002),
    "09023002": ("ASCOU_LAVAIL", 1971), "11028001": ("BELCAIRE", 1971),
}
CPC = {
    "nao_daily.csv": "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.nao.cdas.z500.19500101_current.csv",
    "ao_daily.csv": "https://ftp.cpc.ncep.noaa.gov/cwlinks/norm.daily.ao.cdas.z1000.19500101_current.csv",
    "tele.txt": "https://ftp.cpc.ncep.noaa.gov/wd52dg/data/indices/tele_index.nh",
    "oni.txt": "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt",
    "qbo30.txt": "https://www.cpc.ncep.noaa.gov/data/indices/qbo.u30.index",
}


def get(url, dest, timeout=300):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return True
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r, open(dest, "wb") as f:
            f.write(r.read())
        return True
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print("  error", e.code, url)
        return False


def socrata(code, var, select):
    q = {"$select": f"date_trunc_ymd(data_lectura) as d, {select}",
         "$where": f"codi_estacio='{code}' AND codi_variable='{var}'",
         "$group": "d", "$order": "d", "$limit": "50000"}
    return SOCRATA + "?" + urllib.parse.urlencode(q)


def main():
    for sub in ("xema", "mf", "idx"):
        os.makedirs(os.path.join(BASE, sub), exist_ok=True)
    for c in XEMA:  # una estación por consulta: la consulta múltiple agota el tiempo
        get(socrata(c, "38", "max(valor_lectura) as hmax, min(valor_lectura) as hmin, count(*) as n"),
            os.path.join(BASE, "xema", f"{c}.json"))
        get(socrata(c, "35", "sum(valor_lectura) as p, count(*) as n"), os.path.join(BASE, "xema", f"P_{c}.json"))
        n = len(json.load(open(os.path.join(BASE, "xema", f"P_{c}.json"))))
        print(f"XEMA {c}: {n} días de precipitación")
    for code, (name, y0) in MF.items():
        ok = sum(get(THREDDS.format(y=y, code=code, name=name),
                     os.path.join(BASE, "mf", f"{code}_{name}_MTO_1H_{y}.nc")) for y in range(y0, 2027))
        print(f"Météo-France {name}: {ok} años")
    for fn, url in CPC.items():
        get(url, os.path.join(BASE, "idx", fn))
    print("Listo en", os.path.abspath(BASE))


if __name__ == "__main__":
    main()
