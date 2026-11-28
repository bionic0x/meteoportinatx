"""SEPI fase 03 v2 — ranking de 58 inviernos según el protocolo congelado (docs/SEPI-PROTOCOLO.md §4).

No modifica la v1 (phase03.py, PR #66). Decisiones congeladas:
- invierno identificado por año de inicio (1968 = dic 1968–abr 1969, etiqueta «1968–69»), 1968–2025;
- métricas HSmed, HSmax, d30, d100; índice I = mediana de los percentiles (percentil de rango medio
  frente a la referencia: (n_menores + 0,5·n_iguales)/n_ref);
- excepcional si I > P90 de I (cuantil lineal tipo 7 sobre la referencia); extremo I > P95; deficitario I < P10;
- métricas degeneradas (P90 = 0) conservadas; sensibilidad sin ellas;
- geometrías llano, N 20° y NO 20°, por separado; cotas 1.800 y 2.100 m; macizos 69–74;
- cobertura ≥90 % y ningún hueco > 7 días (series S2M y anclas);
- referencia principal 1968–2026 (58 inviernos), alternativa 1991–2020 (inviernos 1990–91…2019–20);
- sensibilidad sin tendencia lineal; bootstrap circular por bloques de 5 inviernos (incertidumbre muestral
  del umbral, no error físico de S2M);
- independencia de las anclas no presupuesta (UNKNOWN).

Entradas en SEPI_DATA: s2m_ref_v2_69_74.csv.gz (fetch_hist.py), mfquot/ (QUOT 66/09),
out_f03_ranking.csv (v1, para la comparativa).
Salidas en SEPI_DATA/f03v2/: season_metrics_v2.csv, rankings_v2.csv, ranking_delta.csv,
exceptional_winters_delta.csv, ranking_uncertainty.csv, sensitivity_analysis.csv,
validation_classes_v2.csv, coverage_v2.csv, resumen_v2.txt
"""
import glob
import os

import numpy as np
import pandas as pd

_REPO = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DATA = os.path.realpath(os.environ.get("SEPI_DATA", ""))
if not os.environ.get("SEPI_DATA") or os.path.commonpath([_REPO, _DATA]) == _REPO:
    raise SystemExit("Define SEPI_DATA con una carpeta fuera del repositorio (ver scripts/sepi/README.md).")
os.chdir(_DATA)
OUT = "f03v2"
os.makedirs(OUT, exist_ok=True)

SEASONS = list(range(1968, 2026))            # año de inicio
REF_ALT = list(range(1990, 2020))            # inviernos 1990–91 … 2019–20 («1991–2020»)
DOM = {69: "Couserans (control)", 70: "Haute-Ariège", 71: "Andorra", 72: "Orlu–St-Barthélemy",
       73: "Capcir–Puymorens", 74: "Cerdagne–Canigou"}
GEO = {(-1, 0): "llano", (0, 20): "N20", (315, 20): "NO20"}
ALTS = [1800, 2100]
MET = ["HSmed", "HSmax", "d30", "d100"]
B, BLOQUE = 2000, 5
rng = np.random.default_rng(20261128)


def etiqueta(y):
    return f"{y}–{str(y + 1)[-2:]}"


def season_of(t):
    """Año de inicio del invierno dic–abr; NaN fuera de dic–abr."""
    y = t.dt.year - (t.dt.month <= 4)
    return y.where(t.dt.month.isin([12, 1, 2, 3, 4]))


def dias_esperados(y):
    return len(pd.date_range(f"{y}-12-01", f"{y + 1}-04-30"))


def cobertura(fechas, y):
    """(fracción de días válidos, hueco máximo en días) de una serie diaria en el invierno y."""
    idx = pd.date_range(f"{y}-12-01", f"{y + 1}-04-30")
    ok = pd.Series(False, index=idx)
    ok[ok.index.isin(fechas)] = True
    hueco = cur = 0
    for v in ok.values:
        cur = 0 if v else cur + 1
        hueco = max(hueco, cur)
    return ok.mean(), hueco


def valida(frac, hueco):
    return (frac >= 0.9) and (hueco <= 7)


def cubierta_continua(x, umbral=5):
    best = cur = 0
    for v in x:
        cur = cur + 1 if v >= umbral else 0
        best = max(best, cur)
    return best


# ---------------- métricas estacionales S2M ----------------
s = pd.read_csv("s2m_ref_v2_69_74.csv.gz")
s = s[s.altitude.isin(ALTS) & s.num_massif.between(69, 74)]
s["t"] = pd.to_datetime(s.dat.astype(str), format="%Y%m%d")
s["season"] = season_of(s.t)
s = s[s.season.isin(SEASONS)].copy()
s["season"] = s.season.astype(int)
s["geo"] = [GEO[(e, p)] for e, p in zip(s.exposition, s.pente)]
rows, cov = [], []
for (m, alt, geo, y), g in s.sort_values("t").groupby(["num_massif", "altitude", "geo", "season"]):
    frac, hueco = cobertura(g.t.values, y)
    cov.append(dict(fuente="S2M", serie=f"{m}-{alt}-{geo}", season=y, etiqueta=etiqueta(y), frac=frac,
                    hueco_max=hueco, valida=valida(frac, hueco)))
    hs = g.neigetot.values
    rows.append(dict(massif=m, dominio=DOM[m], alt=alt, geo=geo, season=y, etiqueta=etiqueta(y),
                     n_dias=len(g), cobertura=frac, valida=valida(frac, hueco), HSmed=hs.mean(), HSmax=hs.max(),
                     d30=int((hs >= 30).sum()), d100=int((hs >= 100).sum()), SWEmed=g.equivalent_eau.mean(),
                     SWEmax=g.equivalent_eau.max(), fecha_max=g.t.iloc[int(hs.argmax())].strftime("%m-%d"),
                     duracion_max_dias=cubierta_continua(hs)))
F = pd.DataFrame(rows)
assert F.groupby(["massif", "alt", "geo"]).season.nunique().eq(len(SEASONS)).all(), "faltan inviernos S2M"
assert F.valida.all(), "alguna serie S2M no cumple la cobertura"
F.to_csv(f"{OUT}/season_metrics_v2.csv", index=False)


# ---------------- índice y variantes ----------------
def pct_ref(x, ref):
    """Percentil de rango medio de cada valor de x frente a la distribución de referencia ref."""
    ref = np.sort(np.asarray(ref, float))
    lo = np.searchsorted(ref, x, side="left")
    hi = np.searchsorted(ref, x, side="right")
    return (lo + 0.5 * (hi - lo)) / len(ref)


def detrend(v, years):
    b = np.polyfit(years, v, 1)
    return v - np.polyval(b, years) + v.mean()


def evalua(g, ref_years=SEASONS, metricas=MET, regla="I>P90", sin_tendencia=False):
    """g: métricas de un estrato indexadas por season. Devuelve DataFrame por invierno."""
    X = g[MET].astype(float).copy()
    if sin_tendencia:
        for c in MET:
            X[c] = detrend(X[c].values, X.index.values)
    ref = X.loc[ref_years]
    p90m = {c: np.quantile(ref[c], 0.9) for c in MET}
    usadas = [c for c in metricas if c in MET]
    P = pd.DataFrame({c: pct_ref(X[c].values, ref[c].values) for c in usadas}, index=X.index)
    I = P.median(axis=1).round(9)  # evita desempates espurios por redondeo en coma flotante
    Iref = I.loc[ref_years]
    q90, q95, q10 = (np.quantile(Iref, q) for q in (0.9, 0.95, 0.1))
    if regla == "I>P90":
        exc = I > q90
    else:  # regla v1: todas las métricas usadas ≥ P90 de cada métrica
        exc = pd.concat([X[c] >= p90m[c] for c in usadas], axis=1).all(axis=1)
    return pd.DataFrame({"I": I, "rank": I.rank(ascending=False, method="min").astype(int),
                         "excepcional": exc, "extremo": I > q95, "deficitario": I < q10,
                         "P90_I": q90, "metricas": "+".join(usadas)})


def no_degeneradas(g, ref_years=SEASONS):
    return [c for c in MET if np.quantile(g.loc[ref_years, c], 0.9) > 0]


VARIANTES = {
    # nombre: (regla, métricas, referencia, sin_tendencia)
    "V0_replica_v1": ("todas≥P90", "nodeg", SEASONS, False),
    "V1_solo_regla": ("I>P90", "nodeg", SEASONS, False),
    "V2_solo_degeneradas": ("todas≥P90", "todas", SEASONS, False),
    "V3_principal": ("I>P90", "todas", SEASONS, False),
    "S_sin_degeneradas": ("I>P90", "nodeg", SEASONS, False),
    "S_ref_1991_2020": ("I>P90", "todas", REF_ALT, False),
    "S_sin_tendencia": ("I>P90", "todas", SEASONS, True),
}
sens, main = [], []
for (m, alt, geo), g in F.groupby(["massif", "alt", "geo"]):
    g = g.set_index("season")
    for nombre, (regla, met, ref, det) in VARIANTES.items():
        mets = no_degeneradas(g, ref) if met == "nodeg" else MET
        r = evalua(g, ref, mets, regla, det).reset_index()
        r.insert(0, "variante", nombre)
        r.insert(1, "massif", m)
        r.insert(2, "dominio", DOM[m])
        r.insert(3, "alt", alt)
        r.insert(4, "geo", geo)
        sens.append(r)
S = pd.concat(sens)
S["etiqueta"] = S.season.map(etiqueta)
S.to_csv(f"{OUT}/sensitivity_analysis.csv", index=False)
R = S[S.variante == "V3_principal"].drop(columns="variante").copy()

# ---------------- bootstrap por bloques (incertidumbre muestral del umbral) ----------------
def boot_idx(n, L):
    k = int(np.ceil(n / L))
    starts = rng.integers(0, n, k)
    return np.concatenate([(st + np.arange(L)) % n for st in starts])[:n]


unc = []
for (m, alt, geo), g in F.groupby(["massif", "alt", "geo"]):
    g = g.set_index("season")
    X = g[MET].astype(float)
    n = len(X)
    Ib, exb = np.empty((B, n)), np.empty((B, n), bool)
    for b in range(B):
        refb = X.iloc[boot_idx(n, BLOQUE)]
        P = np.column_stack([pct_ref(X[c].values, refb[c].values) for c in MET])
        I = np.median(P, axis=1)
        Pr = np.column_stack([pct_ref(refb[c].values, refb[c].values) for c in MET])
        Ib[b], exb[b] = I, I > np.quantile(np.median(Pr, axis=1), 0.9)
    for j, y in enumerate(X.index):
        unc.append(dict(massif=m, dominio=DOM[m], alt=alt, geo=geo, season=y, etiqueta=etiqueta(y),
                        I_p05=np.quantile(Ib[:, j], 0.05), I_p50=np.quantile(Ib[:, j], 0.5),
                        I_p95=np.quantile(Ib[:, j], 0.95), prob_excepcional=exb[:, j].mean()))
U = pd.DataFrame(unc)
R = R.merge(U[["massif", "alt", "geo", "season", "prob_excepcional"]], on=["massif", "alt", "geo", "season"])
U.to_csv(f"{OUT}/ranking_uncertainty.csv", index=False)

# estabilidad metodológica: en cuántas variantes v2 (principal + sensibilidades) es excepcional
v2set = ["V3_principal", "S_sin_degeneradas", "S_ref_1991_2020", "S_sin_tendencia"]
stab = (S[S.variante.isin(v2set)].groupby(["massif", "alt", "geo", "season"]).excepcional.sum()
        .rename("n_variantes_excepcional").reset_index())
R = R.merge(stab, on=["massif", "alt", "geo", "season"])
R.to_csv(f"{OUT}/rankings_v2.csv", index=False)

# ---------------- comparativa con la v1 ----------------
v1 = pd.read_csv("out_f03_ranking.csv")
v1 = v1.rename(columns={"inv": "inv_v1", "rank": "rank_v1", "excepcional_todas": "exc_v1", "geo": "geo_v1"})
v1["season"] = v1.inv_v1 - 1
v1["geo"] = v1.geo_v1.map({"plano": "llano", "N20": "N20"})
v1 = v1[v1.alt.isin(ALTS)][["massif", "alt", "geo", "season", "rank_v1", "exc_v1", "metricas"]].rename(
    columns={"metricas": "metricas_v1"})
piv = S.pivot_table(index=["massif", "alt", "geo", "season"], columns="variante",
                    values=["rank", "excepcional"], aggfunc="first")
piv.columns = [f"{a}_{b}" for a, b in piv.columns]
D = v1.merge(piv.reset_index(), on=["massif", "alt", "geo", "season"], how="left")
D["dominio"] = D.massif.map(DOM)
D["etiqueta"] = D.season.map(etiqueta)
D["delta_rank"] = D["rank_V3_principal"] - D.rank_v1
D["replica_ok"] = (D.rank_v1 == D["rank_V0_replica_v1"]) & (D.exc_v1 == D["excepcional_V0_replica_v1"])
# La v1 desempataba empates exactos de I por redondeo en coma flotante; la v2 los trata como empates.
I0 = S[S.variante == "V0_replica_v1"].set_index(["massif", "alt", "geo", "season"]).I
n_emp = I0.groupby(level=[0, 1, 2]).transform(lambda x: x.map(x.value_counts()))
D["empate_v0"] = D.set_index(["massif", "alt", "geo", "season"]).index.map(n_emp).values > 1
D["replica_ok_salvo_empates"] = D.replica_ok | (D.empate_v0 & (D.exc_v1 == D["excepcional_V0_replica_v1"]))


def causa_rank(r):
    if r.delta_rank == 0:
        return "sin cambio"
    if r["rank_V2_solo_degeneradas"] != r["rank_V0_replica_v1"]:
        return "conservar métrica degenerada (d100) en el índice"
    if r["rank_V0_replica_v1"] != r.rank_v1 and r.empate_v0:
        return "empate exacto (la v1 lo desempataba por redondeo)"
    if r["rank_V0_replica_v1"] != r.rank_v1:
        return "réplica v1 no exacta (revisar)"
    if r["rank_V2_solo_degeneradas"] != r.rank_v1:
        return "conservar métrica degenerada (d100) en el índice"
    return "otra"


D["causa_rank"] = D.apply(causa_rank, axis=1)
D.to_csv(f"{OUT}/ranking_delta.csv", index=False)


def causa_exc(r):
    a, b = bool(r.exc_v1), bool(r["excepcional_V3_principal"])
    if a == b:
        return "sin cambio"
    sr, sd = bool(r["excepcional_V1_solo_regla"]), bool(r["excepcional_V2_solo_degeneradas"])
    partes = []
    if sr != a:
        partes.append("regla I>P90 de I (frente a todas las métricas ≥ P90)")
    if sd != a:
        partes.append("conservar métrica degenerada")
    if not partes:
        partes.append("efecto conjunto de regla y métrica degenerada")
    return ("SALE de excepcional: " if a else "ENTRA en excepcional: ") + "; ".join(partes)


E = D[D.exc_v1 | D["excepcional_V3_principal"].astype(bool)].copy()
E["cambio"] = E.apply(causa_exc, axis=1)
E[["dominio", "massif", "alt", "geo", "season", "etiqueta", "exc_v1", "excepcional_V1_solo_regla",
   "excepcional_V2_solo_degeneradas", "excepcional_V3_principal", "rank_v1", "rank_V3_principal", "cambio"]].to_csv(
    f"{OUT}/exceptional_winters_delta.csv", index=False)

# ---------------- clases de validación v2 ----------------
ANC = [("09023002", "Ascou-Lavail", 1090, 70, 1200), ("09139001", "L'Hospitalet", 1425, 72, 1500),
       ("66147001", "Porté-Puymorens", 1620, 73, 1500), ("66082001", "Formiguères (antigua)", 1530, 73, 1500),
       ("66082004", "Formiguères", 1495, 73, 1500), ("66124004", "Font-Romeu", 1964, 74, 2100),
       ("66181001", "Ste-Léocadie", 1320, 74, 1200), ("66117001", "Mont-Louis", 1600, 74, 1500),
       ("66204400", "Canigou nivose", 2160, 74, 2100), ("66067402", "Puigmal nivose", 2461, 74, 2400),
       ("09285400", "Port d'Aula nivose", 2140, 69, 2100)]
s_all = pd.read_csv("s2m_ref_v2_69_74.csv.gz")
s_all = s_all[(s_all.exposition == -1) & (s_all.pente == 0)]
s_all["t"] = pd.to_datetime(s_all.dat.astype(str), format="%Y%m%d")
s_all["season"] = season_of(s_all.t)
s_all = s_all[s_all.season.isin(SEASONS)]
mod_hs = s_all.groupby(["num_massif", "altitude", "season"]).neigetot.mean()
o = pd.concat([pd.read_csv(f, sep=";", usecols=["NUM_POSTE", "AAAAMMJJ", "NEIGETOT06"], dtype={"NUM_POSTE": str})
               for f in glob.glob("mfquot/Q_*_autres-parametres.csv.gz")]).drop_duplicates(["NUM_POSTE", "AAAAMMJJ"])
o = o.dropna(subset=["NEIGETOT06"])
o["t"] = pd.to_datetime(o.AAAAMMJJ.astype(str), format="%Y%m%d")
o["season"] = season_of(o.t)
o = o[o.season.isin(SEASONS)]
ac = []
for p, nom, altp, m, band in ANC:
    g = o[o.NUM_POSTE == p]
    validos = []
    for y, gg in g.groupby("season"):
        y = int(y)
        frac, hueco = cobertura(gg.t.values, y)
        cov.append(dict(fuente="QUOT", serie=f"{p} {nom}", season=y, etiqueta=etiqueta(y), frac=frac,
                        hueco_max=hueco, valida=valida(frac, hueco)))
        if valida(frac, hueco):
            validos.append(y)
    if len(validos) < 8:
        continue
    obs = g[g.season.isin(validos)].groupby("season").NEIGETOT06.mean()
    mod = mod_hs.loc[(m, band)].loc[validos]
    to = np.ceil(pd.Series(pct_ref(obs.values, obs.values), index=validos) * 3).clip(1, 3)
    tm = np.ceil(pd.Series(pct_ref(mod.values, mod.values), index=validos) * 3).clip(1, 3)
    for y in validos:
        ac.append(dict(massif=m, season=y, ancla=nom, poste=p, concordante=bool(to[y] == tm[y]),
                       independencia="desconocida (posible asimilación SAFRAN)"))
AC = pd.DataFrame(ac)
pd.DataFrame(cov).to_csv(f"{OUT}/coverage_v2.csv", index=False)
V = []
for m in DOM:
    for y in SEASONS:
        a = AC[(AC.massif == m) & (AC.season == y)] if len(AC) else AC
        n_c, n_d = int(a.concordante.sum()) if len(a) else 0, int((~a.concordante).sum()) if len(a) else 0
        ind_conf = 0  # ninguna ancla tiene independencia confirmada (protocolo §5)
        if ind_conf >= 2:
            clase = "A"
        elif n_c >= 1:
            clase = "B"
        else:
            clase = "C"
        V.append(dict(massif=m, dominio=DOM[m], season=y, etiqueta=etiqueta(y), anclas_concordantes=n_c,
                      anclas_discordantes=n_d, anclas_independientes_confirmadas=ind_conf, clase=clase,
                      discrepancia=(n_c == 0 and n_d > 0),
                      nota="B por independencia desconocida; A no alcanzable mientras no se documente la asimilación"))
VC = pd.DataFrame(V)
VC.to_csv(f"{OUT}/validation_classes_v2.csv", index=False)

# ---------------- resumen ----------------
L = []
P = lambda *a: L.append(" ".join(str(x) for x in a))  # noqa: E731
P("Inviernos:", len(SEASONS), f"({etiqueta(SEASONS[0])} a {etiqueta(SEASONS[-1])}); días por serie:",
  sum(dias_esperados(y) for y in SEASONS), "| último día S2M:", s.t.max().date())
P("Réplica de la v1 (V0) exacta en rank y excepcional:", f"{D.replica_ok.mean():.1%} de", len(D),
  "filas comparables; salvo empates exactos de I:", f"{D.replica_ok_salvo_empates.mean():.1%}",
  "| excepcional idéntico:", f"{(D.exc_v1 == D['excepcional_V0_replica_v1']).mean():.1%}")
for geo in ["llano", "N20", "NO20"]:
    for alt in ALTS:
        x = R[(R.geo == geo) & (R.alt == alt) & R.excepcional]
        P(f"\nExcepcionales v2 (I > P90), {geo} {alt} m:")
        P(x[["dominio", "etiqueta", "rank", "I", "prob_excepcional", "n_variantes_excepcional"]]
          .sort_values(["dominio", "rank"]).round(2).to_string(index=False))
P("\nCambios de categoría excepcional v1 → v2 (llano y N20):")
P(E[E.cambio != "sin cambio"][["dominio", "alt", "geo", "etiqueta", "cambio"]].to_string(index=False))
P("\nCausas de cambio de puesto:", D.causa_rank.value_counts().to_dict())
P("\nClases v2 por tramo (macizos 70–74):")
VC["tramo"] = pd.cut(VC.season, [1967, 1983, 2001, 2025], labels=["1968–84", "1985–2002", "2003–2026"])
P(VC[VC.massif.between(70, 74)].groupby(["tramo", "clase"], observed=False).size().unstack(fill_value=0).to_string())
open(f"{OUT}/resumen_v2.txt", "w").write("\n".join(L) + "\n")
print("\n".join(L))
