"""SEPI fase 03 — ranking de 58 inviernos (dic–abr 1968-69 a 2025-26) por dominio con S2M,
anclas observadas de Météo-France (QUOT 66/09) y prueba de sensibilidad a la ruptura de 2002.

Entradas en SEPI_DATA (ver fetch_hist.py):
  s2m_ref_69_74.csv.gz  S2M (CSV abierto Météo-France), macizos 69–74, plano y N 20°, 1200–2400 m
  mfquot/Q_{66,09}_*_autres-parametres.csv.gz  observación diaria (NEIGETOT06)
  out_catalogo.csv      fase 01 (XEMA, vertiente catalana 2010–2026)
Salidas: out_f03_metricas.csv, out_f03_ranking.csv, out_f03_anclas.csv, out_f03_resumen.txt
"""
import glob
import os
import numpy as np
import pandas as pd
from scipy import stats

_REPO = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DATA = os.path.realpath(os.environ.get("SEPI_DATA", ""))
if not os.environ.get("SEPI_DATA") or os.path.commonpath([_REPO, _DATA]) == _REPO:
    raise SystemExit("Define SEPI_DATA con una carpeta fuera del repositorio (ver scripts/sepi/README.md).")
os.chdir(_DATA)

rng = np.random.default_rng(2026)
INV = list(range(1969, 2027))  # invierno etiquetado por año final; 1969 = dic 1968–abr 1969
DOM = {69: "Couserans (contraste)", 70: "Haute-Ariège", 71: "Andorra", 72: "Orlu–St-Barthélemy",
       73: "Capcir–Puymorens", 74: "Cerdagne–Canigou"}
GEO = {(-1, 0): "plano", (0, 20): "N20"}
MET = ["HSmed", "HSmax", "d30", "d100"]

# ---------- S2M: métricas estacionales ----------
s = pd.read_csv("s2m_ref_69_74.csv.gz")
s["t"] = pd.to_datetime(s.dat.astype(str), format="%Y%m%d")
s = s[s.t.dt.month.isin([12, 1, 2, 3, 4])]
s["inv"] = s.t.dt.year + (s.t.dt.month == 12)
s = s[s.inv.isin(INV)]
s["geo"] = [GEO[(e, p)] for e, p in zip(s.exposition, s.pente)]


def cubierta_continua(x, umbral=5):
    best = cur = 0
    for v in x:
        cur = cur + 1 if v >= umbral else 0
        best = max(best, cur)
    return best


rows = []
for (m, alt, geo, y), g in s.sort_values("t").groupby(["num_massif", "altitude", "geo", "inv"]):
    hs = g.neigetot.values
    rows.append(dict(massif=m, dominio=DOM[m], alt=alt, geo=geo, inv=y, n=len(g), HSmed=hs.mean(), HSmax=hs.max(),
                     d30=int((hs >= 30).sum()), d100=int((hs >= 100).sum()), SWEmed=g.equivalent_eau.mean(),
                     SWEmax=g.equivalent_eau.max(), fecha_max=g.t.iloc[int(hs.argmax())].strftime("%m-%d"),
                     cubierta_max_dias=cubierta_continua(hs)))
F = pd.DataFrame(rows)
assert F.groupby(["massif", "alt", "geo"]).inv.nunique().eq(len(INV)).all(), "faltan inviernos en S2M"
assert (F.n >= 151).all(), "invierno S2M incompleto"
F.to_csv("out_f03_metricas.csv", index=False)

# ---------- índice de rangos y P90 sobre los 58 valores estacionales ----------
def indice(df, met):
    pct = df[met].rank(pct=True)
    return pct.median(axis=1)


R = []
for (m, alt, geo), g in F.groupby(["massif", "alt", "geo"]):
    g = g.set_index("inv")
    p90 = {c: g[c].quantile(0.9) for c in MET}
    # Una métrica con P90 = 0 (p. ej. días ≥100 cm casi siempre 0 a 1.800 m) es degenerada:
    # con «≥» todos los inviernos la cumplirían. Se excluye del índice y de «excepcional».
    met = [c for c in MET if p90[c] > 0]
    idx = indice(g, met)
    exc = pd.DataFrame({c: g[c] >= p90[c] for c in met})
    # prueba de ruptura 2002: percentiles calculados por subperiodo (S2M forzado por ERA-40 hasta 2002, ARPEGE después)
    sub = pd.concat([indice(g.loc[:2002], met), indice(g.loc[2003:], met)])
    dec_glob = np.ceil(idx.rank(pct=True) * 10)
    dec_sub = np.ceil(sub.rank(pct=True) * 10)
    R.append(pd.DataFrame({"massif": m, "dominio": DOM[m], "alt": alt, "geo": geo, "indice": idx,
                           "rank": idx.rank(ascending=False, method="min").astype(int),
                           "metricas": "+".join(met), "n_metricas_p90": exc.sum(axis=1),
                           "excepcional_todas": exc.all(axis=1),
                           "decil": dec_glob, "decil_subperiodo": dec_sub,
                           "sensible_2002": (dec_glob - dec_sub).abs() >= 2}).reset_index())
R = pd.concat(R)

# ---------- anclas observadas (NEIGETOT06, Météo-France) ----------
ANC = [("09023002", "Ascou-Lavail", 1090, 70, 1200), ("09139001", "L'Hospitalet", 1425, 72, 1500),
       ("66147001", "Porté-Puymorens", 1620, 73, 1500), ("66082001", "Formiguères (antigua)", 1530, 73, 1500),
       ("66082004", "Formiguères", 1495, 73, 1500), ("66124004", "Font-Romeu", 1964, 74, 2100),
       ("66181001", "Ste-Léocadie", 1320, 74, 1200), ("66117001", "Mont-Louis", 1600, 74, 1500),
       ("66204400", "Canigou nivose", 2160, 74, 2100),
       ("66067402", "Puigmal nivose", 2461, 74, 2400), ("09285400", "Port d'Aula nivose", 2140, 69, 2100)]
cols = ["NUM_POSTE", "AAAAMMJJ", "NEIGETOT06"]
o = pd.concat([pd.read_csv(f, sep=";", usecols=cols, dtype={"NUM_POSTE": str})
               for f in glob.glob("mfquot/Q_*_autres-parametres.csv.gz")]).drop_duplicates(["NUM_POSTE", "AAAAMMJJ"])
o["t"] = pd.to_datetime(o.AAAAMMJJ.astype(str), format="%Y%m%d")
o = o[o.t.dt.month.isin([12, 1, 2, 3, 4])]
o["inv"] = o.t.dt.year + (o.t.dt.month == 12)
o = o[o.inv.isin(INV)]
dias = {y: len(pd.date_range(f"{y-1}-12-01", f"{y}-04-30")) for y in INV}


def boot(a, b, n=3000):
    r = stats.spearmanr(a, b)[0]
    bs = [stats.spearmanr(*np.c_[a, b][rng.integers(0, len(a), len(a))].T)[0] for _ in range(n)]
    return r, np.nanpercentile(bs, 2.5), np.nanpercentile(bs, 97.5)


A, acuerdo = [], []
for p, nom, alt, m, band in ANC:
    g = o[(o.NUM_POSTE == p)].dropna(subset=["NEIGETOT06"])
    c = g.groupby("inv").NEIGETOT06
    ok = [y for y, n in c.size().items() if n >= 0.9 * dias[y]]
    fila = dict(estacion=nom, poste=p, alt=alt, macizo=m, banda=band, n_inviernos=len(ok),
                periodo=f"{min(ok)}–{max(ok)}" if ok else "—")
    if len(ok) >= 8:
        obs = c.mean().loc[ok]
        mod = F[(F.massif == m) & (F.alt == band) & (F.geo == "plano")].set_index("inv").loc[ok]
        r, lo, hi = boot(obs.values, mod.HSmed.values)
        fila.update(rho_HSmed=round(r, 2), ic95=f"[{lo:.2f}, {hi:.2f}]",
                    sesgo_cm=round(float((mod.HSmed - obs).mean()), 1))
        # sensibilidad de la asignación ancla→macizo (sin contornos oficiales de macizo: UNKNOWN)
        alt_r = {mm: stats.spearmanr(obs.values, F[(F.massif == mm) & (F.alt == band) & (F.geo == "plano")]
                                     .set_index("inv").loc[ok].HSmed.values)[0] for mm in DOM}
        mejor = max(alt_r, key=alt_r.get)
        fila.update(macizo_rho_max=mejor, rho_max=round(alt_r[mejor], 2))
        ter_o = np.ceil(obs.rank(pct=True) * 3)
        ter_m = np.ceil(mod.HSmed.rank(pct=True) * 3)
        for y in ok:
            acuerdo.append(dict(inv=y, massif=m, ancla=nom, coincide=bool(ter_o[y] == ter_m[y])))
    A.append(fila)
A = pd.DataFrame(A)
A.to_csv("out_f03_anclas.csv", index=False)
AC = pd.DataFrame(acuerdo)

# clase por invierno y dominio (se adjunta a la fila plano 1800 m; cada ancla se compara con S2M en su propia banda):
# A = ≥2 anclas coinciden en tercil con S2M; B = 1 coincide; C = hay anclas y ninguna coincide (discrepa);
# SA = sin ancla observada (el orden depende solo del modelo). No es una probabilidad calibrada.
base = R[(R.geo == "plano") & (R.alt == 1800)].copy()
cnt = AC[AC.coincide].groupby(["inv", "massif"]).size().rename("anclas_coinciden")
dis = AC[~AC.coincide].groupby(["inv", "massif"]).size().rename("anclas_discrepan")
base = base.join(cnt, on=["inv", "massif"]).join(dis, on=["inv", "massif"]).fillna({"anclas_coinciden": 0, "anclas_discrepan": 0})
base["clase"] = np.select([base.anclas_coinciden >= 2, base.anclas_coinciden == 1, base.anclas_discrepan >= 1],
                          ["A", "B", "C"], "SA")
R = R.merge(base[["inv", "massif", "anclas_coinciden", "anclas_discrepan", "clase"]], on=["inv", "massif"], how="left")
R.to_csv("out_f03_ranking.csv", index=False)

# ---------- resumen ----------
L = []
P = lambda *a: L.append(" ".join(str(x) for x in a))  # noqa: E731
P("Último día S2M usado:", s.t.max().date(), "| inviernos:", len(INV), "| días dic–abr esperados por serie:", sum(dias.values()))
ult_obs = o.dropna(subset=["NEIGETOT06"]).t.max()
P("Último día de observación QUOT con espesor:", ult_obs.date())
if ult_obs < pd.Timestamp(f"{max(INV)}-04-30"):
    P("AVISO: la observación QUOT no cubre el último invierno; ¿falta el fichero «latest»? Ejecuta fetch_hist.py.")
for geo in ["plano", "N20"]:
    for alt in [1800, 2100]:
        T = R[(R.geo == geo) & (R.alt == alt) & R.massif.between(70, 74)].pivot(index="inv", columns="massif", values="rank")
        T["mediana_rank_70_74"] = T.median(axis=1)
        top = T.sort_values("mediana_rank_70_74").head(8)
        P(f"\n{geo} {alt} m — 8 inviernos con mejor mediana de puesto en los dominios 70–74 (puesto por dominio):")
        P(top.to_string())
ex = R[(R.geo == "plano") & (R.alt == 1800) & R.excepcional_todas]
P("\nExcepcionales (todas las métricas no degeneradas ≥ P90 de 58 inviernos), plano 1800 m:")
P(ex[["inv", "dominio", "rank", "sensible_2002", "clase"]].sort_values(["inv", "dominio"]).to_string(index=False))
P("\nInviernos con ranking sensible a la ruptura de 2002 (decil cambia ≥2), plano 1800 m, por dominio:")
P(R[(R.geo == "plano") & (R.alt == 1800) & R.sensible_2002].groupby("dominio").inv.apply(list).to_string())
P("\nClases de confianza, plano 1800 m (dominios 70–74), por tramo:")
b = R[(R.geo == "plano") & (R.alt == 1800) & R.massif.between(70, 74)].copy()
b["tramo"] = pd.cut(b.inv, [1968, 1984, 2002, 2026], labels=["1969–1984", "1985–2002", "2003–2026"])
P(b.groupby(["tramo", "clase"], observed=False).size().unstack(fill_value=0).to_string())
P("\nMétricas usadas por dominio (plano 1800 m; se excluye la de P90 = 0):")
P(R[(R.geo == "plano") & (R.alt == 1800)].groupby("dominio").metricas.first().to_string())
P("\nAnclas observadas frente a S2M (plano, HS medio dic–abr):")
P(A.to_string(index=False))
# vertiente catalana: XEMA 2010–2026 frente a S2M Cerdagne–Canigou 2100 m plano
if os.path.exists("out_catalogo.csv"):
    X = pd.read_csv("out_catalogo.csv", index_col=0)
    for m in [74, 71]:
        S = R[(R.massif == m) & (R.alt == 2100) & (R.geo == "plano")].set_index("inv").indice
        j = pd.concat([S, X.E_acum], axis=1).dropna()
        r, lo, hi = boot(j.iloc[:, 0].values, j.iloc[:, 1].values)
        P(f"XEMA E_acum (vertiente catalana) vs S2M {DOM[m]} 2100 m: n={len(j)} rho={r:.2f} IC95 [{lo:.2f}, {hi:.2f}]")
open("out_f03_resumen.txt", "w").write("\n".join(L) + "\n")
print("\n".join(L))
