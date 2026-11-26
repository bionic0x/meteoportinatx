"""SEPI fase 01 — catálogo objetivo de inviernos con observaciones accesibles.

Fuentes: XEMA (espesor de nieve, variable 38, máximos diarios) y Météo-France
(precipitación y temperatura horarias, red MTO_1H vía AERIS/IPSL).
Temporada = noviembre (año t-1) a mayo (año t); se etiqueta con el año t.
"""
import glob, json, re, warnings
import numpy as np, pandas as pd, xarray as xr
from scipy import stats
import os
os.chdir(os.environ.get("SEPI_DATA", "."))  # datos y salidas fuera del repo (ver scripts/sepi/README.md)

warnings.filterwarnings("ignore")
rng = np.random.default_rng(42)

EAST = {"Z3": "Malniu 2229", "Z9": "Cadí Nord 2145", "DG": "Núria 1971", "ZC": "Ulldeter 2413"}
WEST = {"Z1": "Bonaigua 2262", "Z2": "Boí 2537", "Z5": "Certascan 2398", "Z6": "Sasseuva 2226",
        "Z7": "Espot 2519", "ZB": "Salòria 2451", "VS": "Lac Redon 2245"}


def season(ts):
    return ts.year + (ts.month >= 9)


def load_xema(code):
    d = pd.DataFrame(json.load(open(f"xema/{code}.json")))
    d["d"] = pd.to_datetime(d["d"])
    s = d.set_index("d")["hmax"].astype(float)
    smin = d.set_index("d")["hmin"].astype(float)
    n = d.set_index("d")["n"].astype(int)
    # Rampas espurias en el máximo diario: si max-min supera 30 cm (300 mm antes del cambio), usar el mínimo
    thr = pd.Series(30.0, index=s.index); thr[s.index < "2021-11-15"] = 300.0
    s = s.where((s - smin) <= thr, smin)
    # Cambio de unidades en los datos abiertos: mm hasta el verano de 2021, cm después.
    # Comprobado: Cadí Nord 2018 = 2338 (mm) -> 234 cm, máximo histórico citado por Meteocat;
    # Núria 26-01-2026 = 144 (cm), récord citado por Meteocat.
    s[s.index < "2021-11-15"] = s[s.index < "2021-11-15"] / 10.0
    s[(s < 0)] = 0.0
    s[(s > 600) | (n < 24)] = np.nan          # sensor fuera de rango o día incompleto (<12 h)
    # picos aislados: salto >80 cm que revierte al día siguiente
    up = s.diff(); dn = s.diff(-1)
    s[(up > 80) & (dn > 80)] = np.nan
    return s


def xema_metrics(s):
    rows = []
    for y in range(2010, 2027):
        w = s[(s.index >= f"{y-1}-11-01") & (s.index <= f"{y}-05-31")]
        dja = s[(s.index >= f"{y-1}-12-01") & (s.index <= f"{y}-04-30")]
        cover = w.notna().mean() if len(w) else 0
        if cover < 0.8:
            rows.append((y, np.nan, np.nan, np.nan, cover)); continue
        inc = w.diff().clip(lower=0)
        hn = inc[inc >= 2].sum()                     # acumulación: suma de aumentos ≥2 cm/día
        rows.append((y, w.max(), (dja >= 30).sum() / max(dja.notna().mean(), 1e-9), hn, cover))
    return pd.DataFrame(rows, columns=["season", "HSmax", "dias_ge30", "HNproxy", "cobertura"]).set_index("season")


def mf_solid(pattern, tmax_c=0.5):
    """Precipitación caída con T ≤ tmax_c (proxy de precipitación sólida), nov–abr."""
    out = {}
    for f in sorted(glob.glob(pattern)):
        d = xr.open_dataset(f)
        if "cumul_precip" not in d or "ta" not in d:
            continue
        df = pd.DataFrame({"p": d.cumul_precip.values, "t": d.ta.values - 273.15}, index=pd.to_datetime(d.time.values))
        out[f] = df
    df = pd.concat(out.values()).sort_index()
    df = df[~df.index.duplicated()]
    rows = []
    for y in range(1994, 2027):
        w = df[(df.index >= f"{y-1}-11-01") & (df.index < f"{y}-05-01")]
        valid = w.dropna()
        cov = len(valid) / (len(pd.date_range(f"{y-1}-11-01", f"{y}-04-30 23:00", freq="h")))
        if cov < 0.8:
            continue
        mon = w.p.notna().groupby(w.index.month).mean()
        if any(mon.get(m, 0) < 0.85 for m in (12, 1, 2, 3)):
            continue
        sol = valid.p[valid.t <= tmax_c].sum() / cov
        tot = valid.p.sum() / cov
        tmean = valid.t.mean()
        rows.append((y, sol, tot, tmean, cov))
    return pd.DataFrame(rows, columns=["season", "Psolida", "Ptotal", "Tmedia", "cobertura"]).set_index("season")


def zgroup(tab, cols):
    z = (tab - tab.mean()) / tab.std(ddof=1)
    return z[cols].mean(axis=1, skipna=True), z[cols].notna().sum(axis=1)


# ---------- XEMA ----------
met = {c: xema_metrics(load_xema(c)) for c in list(EAST) + list(WEST)}
idx = {}
for m in ["HSmax", "dias_ge30", "HNproxy"]:
    tab = pd.DataFrame({c: met[c][m] for c in met})
    e, ne = zgroup(tab, list(EAST)); w, nw = zgroup(tab, list(WEST))
    idx[f"E_{m}"] = e; idx[f"W_{m}"] = w; idx[f"nE_{m}"] = ne
    tab.to_csv(f"out_xema_{m}.csv")
X = pd.DataFrame(idx)
X["E_acum"] = X[["E_HSmax", "E_HNproxy"]].mean(axis=1)
X["W_acum"] = X[["W_HSmax", "W_HNproxy"]].mean(axis=1)
X["E_pers"] = X["E_dias_ge30"]
X["contraste_E_W"] = X["E_acum"] - X["W_acum"]

# ---------- Météo-France ----------
ast = mf_solid("mf/09024004_ASTON_MTO_1H_*.nc")
frm = mf_solid("mf/66082004_FORMIGUERES_MTO_1H_*.nc")
blc = mf_solid("mf/11028001_BELCAIRE_MTO_1H_*.nc")
ast.to_csv("out_mf_aston.csv"); frm.to_csv("out_mf_formigueres.csv"); blc.to_csv("out_mf_belcaire.csv")

# ---------- índices ----------
_rows = []
for _l in open("idx/tele.txt"):
    if re.match(r"^\d{4}\s+\d{1,2}\s", _l):
        v = [float(x) for x in re.findall(r"-?\d+\.\d+", _l[7:])]
        _rows.append([int(_l[:4]), int(_l[4:7])] + v[:7])
tele = pd.DataFrame(_rows, columns=["y", "m", "NAO", "EA", "WP", "EPNP", "PNA", "EAWR", "SCA"]).replace(-99.9, np.nan)
tele["season"] = tele.y + (tele.m >= 9)
djfm = tele[tele.m.isin([12, 1, 2, 3])].groupby("season")[["NAO", "EA", "EAWR", "SCA"]].mean()
oni = pd.read_csv("idx/oni.txt", sep=r"\s+")
oni = oni[oni.SEAS == "DJF"].set_index("YR")["ANOM"].rename("ONI_DJF")
ao = pd.read_csv("idx/ao_daily.csv"); ao["date"] = pd.to_datetime(ao[["year", "month", "day"]])
ao["season"] = ao.date.dt.year + (ao.date.dt.month >= 9)
aoS = ao[ao.date.dt.month.isin([12, 1, 2, 3])].groupby("season")["ao_index_cdas"].mean().rename("AO_DJFM")
nao = pd.read_csv("idx/nao_daily.csv"); nao["date"] = pd.to_datetime(nao[["year", "month", "day"]])
nao["season"] = nao.date.dt.year + (nao.date.dt.month >= 9)
d4 = nao[nao.date.dt.month.isin([12, 1, 2, 3])]
naoT = d4.groupby("season")["nao_index_cdas"].agg(
    NAOd_media="mean",
    NAOd_neg_dias=lambda s: (s <= -1).sum(),
    NAOd_pos_dias=lambda s: (s >= 1).sum())
I = djfm.join([oni, aoS, naoT], how="outer")
I.to_csv("out_indices.csv")


def spearman_boot(a, b, n=5000):
    j = pd.concat([a, b], axis=1).dropna()
    if len(j) < 8:
        return len(j), np.nan, (np.nan, np.nan), np.nan
    r, p = stats.spearmanr(j.iloc[:, 0], j.iloc[:, 1])
    bs = []
    for _ in range(n):
        k = rng.integers(0, len(j), len(j))
        bs.append(stats.spearmanr(j.iloc[k, 0], j.iloc[k, 1])[0])
    return len(j), r, tuple(np.nanpercentile(bs, [2.5, 97.5])), p


res = []
targets = {"E_acum": X.E_acum, "E_pers": X.E_pers, "W_acum": X.W_acum, "contraste_E_W": X.contraste_E_W,
           "Aston_Psolida": ast.Psolida, "Formigueres_Psolida": frm.Psolida}
for tn, t in targets.items():
    for pn in ["NAO", "EA", "EAWR", "SCA", "ONI_DJF", "AO_DJFM", "NAOd_neg_dias"]:
        n, r, ci, p = spearman_boot(t, I[pn])
        res.append((tn, pn, n, r, ci[0], ci[1], p))
R = pd.DataFrame(res, columns=["objetivo", "indice", "n", "rho", "ic2.5", "ic97.5", "p"])
R.to_csv("out_correlaciones.csv", index=False)

# ---------- catálogo ----------
cat = X[["E_acum", "E_pers", "W_acum", "contraste_E_W", "nE_HSmax"]].join(
    frm[["Psolida", "Tmedia"]].rename(columns=lambda c: "FRM_" + c)).join(
    ast[["Psolida", "Tmedia"]].rename(columns=lambda c: "AST_" + c)).join(I[["NAO", "EAWR", "ONI_DJF", "AO_DJFM"]])
cat["pct_E_acum"] = cat.E_acum.rank(pct=True)
cat["pct_E_pers"] = cat.E_pers.rank(pct=True)
cat.to_csv("out_catalogo.csv")
pd.set_option("display.width", 220); pd.set_option("display.max_columns", 30)
print(cat.round(2).loc[2010:2026])
print()
print(ast.round(1)); print(frm.round(1))
print()
print(R[R.n >= 8].round(2).to_string(index=False))

# ---------- H6: estructura temporal (descriptiva) ----------
def h6(s, y):
    w = s[(s.index >= f"{y-1}-12-01") & (s.index <= f"{y}-03-31")]
    if len(w) == 0 or w.notna().mean() < 0.95:
        return np.nan, np.nan
    snow = (w.diff() >= 2)
    runs, cur = [], 0
    for v in snow.values:
        cur = 0 if v else cur + 1
        runs.append(cur)
    # episodios: días de aumento separados por ≥2 días sin aumento
    ev = (snow & ~snow.shift(1, fill_value=False) & ~snow.shift(2, fill_value=False)).sum()
    return max(runs), ev

h = {}
for c in EAST:
    s = load_xema(c)
    h[c] = pd.DataFrame([h6(s, y) for y in range(2010, 2027)], index=range(2010, 2027), columns=["racha", "episodios"])
racha = pd.DataFrame({c: h[c].racha for c in h}).mean(axis=1)
epis = pd.DataFrame({c: h[c].episodios for c in h}).mean(axis=1)
H6 = pd.DataFrame({"E_racha_seca_max": racha, "E_episodios": epis, "E_acum": X.E_acum})
H6.to_csv("out_h6.csv")
print("\nH6 (dic–mar, media de estaciones del este):")
print(H6.round(1).to_string())
HSm = pd.DataFrame({c: met[c]["HSmax"] for c in EAST})
H6["E_HSmax_z"] = ((HSm - HSm.mean()) / HSm.std(ddof=1)).mean(axis=1)
for tgt, col in [("E_acum", "E_racha_seca_max"), ("E_acum", "E_episodios"), ("E_HSmax_z", "E_episodios"), ("E_HSmax_z", "E_racha_seca_max")]:
    n, r, ci, p = spearman_boot(H6[tgt], H6[col])
    print(f"{tgt} vs {col}: n={n} rho={r:.2f} IC95 [{ci[0]:.2f},{ci[1]:.2f}]")
for _ in []:
    print(f"E_acum vs {col}: n={n} rho={r:.2f} IC95 [{ci[0]:.2f},{ci[1]:.2f}]")
print("\nConsistencia entre redes (Spearman):")
for a, b in [("E_acum", "FRM_Psolida"), ("E_acum", "AST_Psolida"), ("W_acum", "AST_Psolida"), ("FRM_Psolida", "AST_Psolida")]:
    n, r, ci, p = spearman_boot(cat[a], cat[b])
    print(f"{a} vs {b}: n={n} rho={r:.2f} IC95 [{ci[0]:.2f},{ci[1]:.2f}]")
