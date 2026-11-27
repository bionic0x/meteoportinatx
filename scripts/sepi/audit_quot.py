"""SEPI — auditoría de la nieve observada en QUOT 66/09 (HNEIGEF, NEIGETOT06).

Para cada estación y variable: primer y último invierno con datos, días válidos e inviernos dic–abr
con ≥90 % y ≥50 % de días. Distingue «fecha de apertura de la estación» de «serie nival».
Salida: out_cobertura_mf_nieve.csv en SEPI_DATA.
"""
import glob

import pandas as pd

import os
_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DATA = os.path.abspath(os.environ.get("SEPI_DATA", ""))
if not os.environ.get("SEPI_DATA") or os.path.commonpath([_REPO, _DATA]) == _REPO:
    raise SystemExit("Define SEPI_DATA con una carpeta fuera del repositorio (ver scripts/sepi/README.md).")
os.chdir(_DATA)
cols = ["NUM_POSTE", "NOM_USUEL", "ALTI", "AAAAMMJJ", "HNEIGEF", "QHNEIGEF", "NEIGETOT06", "QNEIGETOT06", "NEIGETOTX", "SOLNEIGE"]
fr = []
for f in sorted(glob.glob("mfquot/Q_*_autres-parametres.csv.gz")):
    fr.append(pd.read_csv(f, sep=";", usecols=cols, dtype={"NUM_POSTE": str}))
d = pd.concat(fr).drop_duplicates(["NUM_POSTE", "AAAAMMJJ"])
d["t"] = pd.to_datetime(d.AAAAMMJJ.astype(str), format="%Y%m%d")
d = d[(d.t >= "1968-12-01") & d.t.dt.month.isin([12, 1, 2, 3, 4])]
d["inv"] = d.t.dt.year + (d.t.dt.month == 12)  # invierno etiquetado por año final
d = d[d.inv <= 2026]
dias = {y: len(pd.date_range(f"{y-1}-12-01", f"{y}-04-30")) for y in range(1969, 2027)}
print("días esperados dic–abr 1969–2026:", sum(dias.values()), "en", len(dias), "inviernos")
out = []
for (p, n, a), g in d.groupby(["NUM_POSTE", "NOM_USUEL", "ALTI"]):
    for var in ["NEIGETOT06", "HNEIGEF"]:
        c = g.dropna(subset=[var]).groupby("inv").size()
        if c.sum() == 0:
            continue
        frac = pd.Series({y: c.get(y, 0) / dias[y] for y in dias})
        out.append(dict(poste=p, nombre=n, alt=a, var=var, primer=int(c.index.min()), ultimo=int(c.index.max()),
                        dias_validos=int(c.sum()), inv_cob90=int((frac >= .9).sum()), inv_cob50=int((frac >= .5).sum())))
R = pd.DataFrame(out).sort_values(["var", "inv_cob90"], ascending=[True, False])
R.to_csv("out_cobertura_mf_nieve.csv", index=False)
pd.set_option("display.width", 200)
print(R[R.inv_cob50 >= 5].to_string(index=False))
