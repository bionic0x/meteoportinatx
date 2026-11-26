"""SEPI fase 02b — control del dominio oeste (hallazgo H4 de la verificación de la fase 02).

Precipitación diaria XEMA (variable 35) del oeste: Bonaigua Z1, Boí Z2, Certascan Z5, Sasseuva Z6,
Espot Z7, Salòria ZB, Lac Redon VS. Mismo control de calidad y escalado que phase02.py.
Pruebas:
  W_acum ~ P_total_W ; W_acum ~ P_NNW_W | P_total_W
  contraste_E_W ~ log(P_E / P_W)  (¿el contraste de nieve es un contraste de precipitación?)
  contraste_E_W ~ fracción E/SE (Puigmal) | log(P_E/P_W)
"""
import json, warnings
import numpy as np, pandas as pd
from scipy import stats
import os
os.chdir(os.environ.get("SEPI_DATA", "."))  # datos y salidas fuera del repo (ver scripts/sepi/README.md)

warnings.filterwarnings("ignore")
rng = np.random.default_rng(11)


def load_group(codes):
    P = {}
    for c in codes:
        d = pd.DataFrame(json.load(open(f"xema/P_{c}.json")))
        d["d"] = pd.to_datetime(d["d"])
        d = d.set_index("d")
        s = d["p"].astype(float)
        s[d["n"].astype(int) < 40] = np.nan
        s[s > 250] = np.nan
        P[c] = s
    P = pd.DataFrame(P)
    com = P.loc["2011-12-01":"2026-03-31"]
    com = com[com.index.month.isin([12, 1, 2, 3])]
    Pn = P / com.mean() * com.mean().mean()
    m = Pn.mean(axis=1, skipna=True)
    m[P.notna().sum(axis=1) < max(2, len(codes) // 2)] = np.nan
    return m, P


pW, PW = load_group(["Z1", "Z2", "Z5", "Z6", "Z7", "ZB", "VS"])
pE, _ = load_group(["Z3", "Z9", "DG", "ZC"])

# sector diario de Puigmal, reutilizando el de la fase 02
import xarray as xr, glob
parts = []
for f in sorted(glob.glob("mf/66067402_PUIGMAL-NIVOSE_MTO_1H_*.nc")):
    d = xr.open_dataset(f)
    if "wd" in d:
        parts.append(pd.DataFrame({"wd": d.wd.values, "ws": d.ws.values}, index=pd.to_datetime(d.time.values)))
w = pd.concat(parts).sort_index(); w = w[~w.index.duplicated()].dropna()
u = -w.ws * np.sin(np.radians(w.wd)); v = -w.ws * np.cos(np.radians(w.wd))
g = pd.DataFrame({"u": u, "v": v}).resample("D").mean(); n = w.ws.resample("D").count(); g[n < 16] = np.nan
dirn = (np.degrees(np.arctan2(-g.u, -g.v)) + 360) % 360
sec = pd.Series(np.select([dirn.isna(), (dirn >= 270) | (dirn < 45), dirn < 180], [None, "NW", "ESE"], "SW"), index=dirn.index)

rows = []
for y in range(2010, 2027):
    idx = pd.date_range(f"{y-1}-12-01", f"{y}-03-31")
    a, b, s = pW.reindex(idx), pE.reindex(idx), sec.reindex(idx)
    if a.notna().mean() < 0.9 or b.notna().mean() < 0.9:
        rows.append(dict(season=y)); continue
    wetW = a >= 2
    cob_sec = s[wetW].notna().mean()
    rows.append(dict(season=y, PW_total=a.sum(), PE_total=b.sum(), PW_NNW=a[wetW & (s == "NW")].sum(),
                     PW_ESE=a[wetW & (s == "ESE")].sum(), cobW=a.notna().mean(), cob_sec=cob_sec,
                     n_est_W=int(PW.reindex(idx).notna().any().sum())))
M = pd.DataFrame(rows).set_index("season")
M["logEW"] = np.log(M.PE_total / M.PW_total)
M["shareNNW_W"] = M.PW_NNW / M.PW_total
# V3: sin cobertura de sector >=90 % en días húmedos, las métricas por sector no son válidas
M.loc[M.cob_sec < 0.9, ["PW_NNW", "PW_ESE", "shareNNW_W"]] = np.nan
cat = pd.read_csv("out_catalogo.csv", index_col=0)
f2 = pd.read_csv("out_fase02.csv", index_col=0)
T = M.join(cat[["E_acum", "W_acum", "contraste_E_W"]]).join(f2[["frac_ESE", "P_ESE", "P_total"]])
T.to_csv("out_fase02b.csv")


def sb(a, b, nb=5000):
    j = T[[a, b]].dropna()
    r, p = stats.spearmanr(j[a], j[b])
    bs = [stats.spearmanr(*j.iloc[rng.integers(0, len(j), len(j))].T.values)[0] for _ in range(nb)]
    return len(j), r, np.nanpercentile(bs, 2.5), np.nanpercentile(bs, 97.5), p


def parcial(a, b, c, D=None):
    D = T if D is None else D
    r = D[[a, b, c]].dropna().rank()
    ra = r[a] - np.polyval(np.polyfit(r[c], r[a], 1), r[c]); rb = r[b] - np.polyval(np.polyfit(r[c], r[b], 1), r[c])
    return stats.pearsonr(ra, rb)


pd.set_option("display.width", 200)
print(T.round(2).to_string())
out = []
for a, b, c in [("W_acum", "PW_total", None), ("W_acum", "PW_NNW", "PW_total"), ("W_acum", "shareNNW_W", None),
                ("E_acum", "PE_total", None), ("contraste_E_W", "logEW", None),
                ("contraste_E_W", "frac_ESE", "logEW"), ("contraste_E_W", "P_ESE", "logEW")]:
    n_, r, lo, hi, p = sb(a, b)
    rp, pp = parcial(a, b, c) if c else (np.nan, np.nan)
    if c:   # V1: IC bootstrap de la parcial
        J = T[[a, b, c]].dropna()
        bs = [parcial(a, b, c, J.iloc[rng.integers(0, len(J), len(J))].reset_index(drop=True))[0] for _ in range(2000)]
        plo, phi = np.nanpercentile(bs, [2.5, 97.5])
    else:
        plo = phi = np.nan
    out.append((a, b, c or "", n_, r, lo, hi, p, rp, plo, phi, pp))
R = pd.DataFrame(out, columns=["objetivo", "metrica", "control", "n", "rho", "ic2.5", "ic97.5", "p", "rho_parcial", "parc_ic2.5", "parc_ic97.5", "p_parcial"])
o = np.argsort(R.p.values); m = len(R)
R.loc[o, "q_BH"] = np.minimum(np.minimum.accumulate((R.p.values[o] * m / np.arange(1, m + 1))[::-1])[::-1], 1)
print(R.round(3).to_string()); R.to_csv("out_fase02b_tests.csv", index=False)
