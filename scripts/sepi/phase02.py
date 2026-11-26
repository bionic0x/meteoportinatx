"""SEPI fase 02 — H6 y H1/H2 sin circularidad.

Días húmedos: precipitación diaria XEMA (variable 35) en las estaciones altas del este
(Malniu Z3, Cadí Nord Z9, Núria DG, Ulldeter ZC), independiente del sensor de espesor.
Dirección del flujo en cresta: viento horario de las nivosas de Météo-France
(Puigmal 2.465 m desde 2009; Canigou 2.150 m desde 1996), media vectorial diaria.
Variable objetivo: E_acum, E_pers y contraste E–O de la fase 01 (out_catalogo.csv).
"""
import glob, json, warnings
import numpy as np, pandas as pd, xarray as xr
from scipy import stats
import os
_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DATA = os.path.abspath(os.environ.get("SEPI_DATA", ""))
if not os.environ.get("SEPI_DATA") or os.path.commonpath([_REPO, _DATA]) == _REPO:
    raise SystemExit("Define SEPI_DATA con una carpeta fuera del repositorio (ver scripts/sepi/README.md).")
os.chdir(_DATA)  # datos y salidas fuera del repo

warnings.filterwarnings("ignore")
rng = np.random.default_rng(7)

# ---------- precipitación diaria del este ----------
P = {}
for c in ["Z3", "Z9", "DG", "ZC"]:
    d = pd.DataFrame(json.load(open(f"xema/P_{c}.json")))
    d["d"] = pd.to_datetime(d["d"])
    s = d.set_index("d")["p"].astype(float)
    s[d.set_index("d")["n"].astype(int) < 40] = np.nan      # día con <20 h de datos
    s[s > 250] = np.nan
    P[c] = s
P = pd.DataFrame(P)
# H5: cada estación se escala por su media dic–mar del periodo común, para que la
# entrada de ZC (sept. 2011) no cambie el nivel de la media
com = P.loc["2011-12-01":"2026-03-31"]; com = com[com.index.month.isin([12,1,2,3])]
Pn = P / com.mean() * com.mean().mean()
pE = Pn.mean(axis=1, skipna=True)
pE[P.notna().sum(axis=1) < 2] = np.nan


# ---------- viento en cresta ----------
def nivose_wind(pattern):
    parts = []
    for f in sorted(glob.glob(pattern)):
        d = xr.open_dataset(f)
        if "wd" not in d:
            continue
        parts.append(pd.DataFrame({"wd": d.wd.values, "ws": d.ws.values}, index=pd.to_datetime(d.time.values)))
    df = pd.concat(parts).sort_index()
    df = df[~df.index.duplicated()].dropna()
    u = -df.ws * np.sin(np.radians(df.wd)); v = -df.ws * np.cos(np.radians(df.wd))
    g = pd.DataFrame({"u": u, "v": v, "ws": df.ws}).resample("D").agg({"u": "mean", "v": "mean", "ws": "mean"})
    n = df.ws.resample("D").count()
    g.loc[n < 16, :] = np.nan
    g["dir"] = (np.degrees(np.arctan2(-g.u, -g.v)) + 360) % 360
    g["consist"] = np.hypot(g.u, g.v) / g.ws        # 1 = dirección constante
    return g


pm = nivose_wind("mf/66067402_PUIGMAL-NIVOSE_MTO_1H_*.nc")
cg = nivose_wind("mf/66204400_CANIGOU-NIVOSE_MTO_1H_*.nc")
j = pd.concat([pm.dir.rename("pm"), cg.dir.rename("cg")], axis=1).dropna()
dd = ((j.pm - j.cg + 180) % 360) - 180


def sector(a):
    if np.isnan(a):
        return np.nan
    if a >= 270 or a < 45:
        return "W-NW-N-NE"
    if a < 180:
        return "ENE-E-SE-S"
    return "SSW-SW-WSW"


secpm = pm.dir.apply(sector); seccg = cg.dir.apply(sector)
both = pd.concat([secpm.rename("pm"), seccg.rename("cg")], axis=1).dropna()
print(f"\r Puigmal vs Canigou: n={len(both)} días; diferencia angular mediana {dd.abs().median():.0f}°; "
      f"misma clase en el {100*(both.pm == both.cg).mean():.0f} % de los días")
flow = pm.dir   # H1: Canigou no representa el flujo de cresta (v anticorrelacionada con las demás); no se usa de relleno
sec = flow.apply(sector)

# ---------- métricas por invierno (dic–mar) ----------
WET = 2.0
rows = []
for y in range(2010, 2027):
    idx = pd.date_range(f"{y-1}-12-01", f"{y}-03-31", freq="D")
    p = pE.reindex(idx); s = sec.reindex(idx)
    cov_p = p.notna().mean(); cov_s = s[p >= WET].notna().mean() if (p >= WET).any() else np.nan  # informativa
    if cov_p < 0.9:
        rows.append(dict(season=y)); continue
    wet = (p >= WET)
    # racha seca más larga: días válidos no húmedos consecutivos (un día sin dato corta la racha)
    best = cur = 0
    for v, ok in zip(wet.values, p.notna().values):
        if ok and not v:
            cur += 1; best = max(best, cur)
        else:
            cur = 0
    # episodios: rachas de días húmedos
    ep = int((wet & ~wet.shift(1, fill_value=False)).sum())
    ws = s[wet].dropna()
    # sector dominante de cada episodio y transiciones entre episodios consecutivos
    epi_sec = []
    for k, grp in wet.groupby((wet != wet.shift()).cumsum()):
        if grp.iloc[0]:
            ss = s.loc[grp.index].dropna()
            if len(ss):
                epi_sec.append(ss.mode().iloc[0])
    trans = sum(1 for a, b in zip(epi_sec, epi_sec[1:]) if {a, b} == {"W-NW-N-NE", "ENE-E-SE-S"})
    rows.append(dict(season=y, P_total=p.sum(), dias_humedos=int(wet.sum()), episodios=ep, racha_seca_max=best,
                     frac_NNW=(ws == "W-NW-N-NE").mean(), frac_ESE=(ws == "ENE-E-SE-S").mean(), frac_SSW=(ws == "SSW-SW-WSW").mean(),
                     P_ESE=p[wet & (s == "ENE-E-SE-S")].sum(), P_NNW=p[wet & (s == "W-NW-N-NE")].sum(),
                     transiciones_NW_ESE=trans, cobertura_viento=cov_s))
M = pd.DataFrame(rows).set_index("season")
cat = pd.read_csv("out_catalogo.csv", index_col=0)
T = M.join(cat[["E_acum", "E_pers", "W_acum", "contraste_E_W"]])
T.to_csv("out_fase02.csv")


def sb(a, b, n=5000):
    jj = pd.concat([a, b], axis=1).dropna()
    r, p = stats.spearmanr(jj.iloc[:, 0], jj.iloc[:, 1])
    bs = [stats.spearmanr(*jj.iloc[rng.integers(0, len(jj), len(jj))].T.values)[0] for _ in range(n)]
    return len(jj), r, np.nanpercentile(bs, 2.5), np.nanpercentile(bs, 97.5), p


pd.set_option("display.width", 220)
print(T.round(2).to_string())
print("\nPruebas preregistradas (v0.3): racha seca, transiciones; más reparto por sector para H1/H2")
tests = [("E_acum", "racha_seca_max"), ("E_acum", "episodios"), ("E_acum", "transiciones_NW_ESE"),
         ("E_pers", "racha_seca_max"), ("E_acum", "P_total"),
         ("contraste_E_W", "frac_ESE"), ("contraste_E_W", "P_ESE"), ("W_acum", "P_NNW")]
out = []
for a, b in tests:
    n, r, lo, hi, p = sb(T[a], T[b])
    out.append((a, b, n, r, lo, hi, p))
    print(f"{a:>14} vs {b:<20} n={n} rho={r:+.2f} IC95 [{lo:+.2f},{hi:+.2f}] p={p:.3f}")


# H2/H3: parciales de rangos controlando P_total para las ocho pruebas y corrección BH
def parcial(a, b, c="P_total"):
    r = T[[a, b, c]].dropna().rank()
    ra = r[a] - np.polyval(np.polyfit(r[c], r[a], 1), r[c]); rb = r[b] - np.polyval(np.polyfit(r[c], r[b], 1), r[c])
    return stats.pearsonr(ra, rb)
R = pd.DataFrame(out, columns=["objetivo", "metrica", "n", "rho", "ic2.5", "ic97.5", "p"])
R[["rho_parcial_Ptot", "p_parcial"]] = [(np.nan, np.nan) if b == "P_total" else tuple(parcial(a, b)) for a, b in tests]
def bh(p):
    p = np.asarray(p, float); m = (~np.isnan(p)).sum(); o = np.argsort(p); q = np.full(len(p), np.nan)
    qq = np.minimum.accumulate((p[o][:m] * m / np.arange(1, m + 1))[::-1])[::-1]; q[o[:m]] = np.minimum(qq, 1); return q
R["q_BH"] = bh(R.p); R["q_BH_parcial"] = bh(R.p_parcial)
T["shareNNW"] = T.P_NNW / T.P_total; T["shareESE"] = T.P_ESE / T.P_total
for a, b in [("W_acum", "shareNNW"), ("contraste_E_W", "shareESE")]:
    print("fracción", a, b, "rho=%+.2f p=%.3f" % stats.spearmanr(T[a], T[b], nan_policy="omit"))
print(R.round(3).to_string()); R.to_csv("out_fase02_tests.csv", index=False)
