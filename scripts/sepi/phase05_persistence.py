"""SEPI F05 (PR 3): persistencia, análogos y predictibilidad. Protocolo congelado en 1ae92c1; concreciones C1–C19.

Necesita el protocolo congelado (puerta de f04_core). Entradas en SEPI_DATA:
  s2m_ref_v2_69_74.csv.gz (estado inicial) y f04/bimonthly_metrics.csv (objetivos).
Salidas en SEPI_DATA/f05/:
  predictions.csv         predicciones individuales fuera de muestra (media, P10, P50, P90, CRPS, RPS y truncado)
  skill.csv               habilidad por modelo, dominio, estrato, periodo y objetivo, frente a M0
  primary_hypotheses.csv  H-P1 a H-P3 (M0c-R frente a M0, ΔSWE, 2.100 m llano), con Holm y estado
  transition_matrix.csv   terciles de ΔSWE P1→P2 y P2→P3 con límites por origen móvil
  log.csv                 exclusiones, degeneraciones, configuraciones de los análogos y truncados
  emisiones/*.json        instantáneas inmutables por inicialización e invierno, con manifest.json (SHA-256)
"""
import csv
import hashlib
import json
import math
import os
import sys
from collections import defaultdict
from datetime import date, timedelta

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f04_core as f4  # noqa: E402
import f05_core as fc  # noqa: E402

_REPO = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DATA = os.path.realpath(os.environ.get("SEPI_DATA", ""))
if not os.environ.get("SEPI_DATA") or os.path.commonpath([_REPO, _DATA]) == _REPO:
    raise SystemExit("Define SEPI_DATA con una carpeta fuera del repositorio (ver scripts/sepi/README.md).")
with open(os.path.join(_REPO, "docs", "SEPI-P-PROTOCOLO.md"), encoding="utf-8") as _f:
    f4.require_frozen_protocol(_f.read())

OUT = os.path.join(_DATA, "f05")
SEASONS = list(range(1968, 2026))
TEST = [s for s in SEASONS if s >= 1991]
PRE2002 = range(1991, 2002)
DOM = {69: "Couserans (control)", 70: "Haute-Ariège", 71: "Andorra", 72: "Orlu–St-Barthélemy",
       73: "Capcir–Puymorens", 74: "Cerdagne–Canigou"}
STRATA = [(2100, -1, 0, "llano"), (1800, -1, 0, "llano"), (1800, 0, 20, "N20"), (1800, 315, 20, "NO20")]
NONNEG = {"g_swe", "l_swe", "g_hs", "d30", "d100", "formation_day"}
MODELS = ["M0", "M0b", "M0c-R", "M0d-R", "M0d-R+"]
INIT_DAY = {"P1": lambda s: date(s, 10, 31), "P2": lambda s: date(s, 12, 31),
            "P3": lambda s: date(s + 1, 3, 1) - timedelta(days=1)}


def targets_for(period, alt, geo):
    t = ["dswe", "g_swe", "l_swe", "g_hs", "d30"]
    if period != "P1" and alt == 2100 and geo == "llano":
        t.append("d100")
    if period == "P1":
        t.append("formation_day")
    return t


def formation_ordinal(v):
    if not isinstance(v, str):
        return None
    if v == f4.CENSORED:
        return 62.0
    d = date.fromisoformat(v)
    return float((d - date(d.year if d.month >= 11 else d.year - 1, 11, 1)).days + 1)


def bounds(target, period, swe0, season):
    if target == "dswe":
        return -swe0, None
    if target in ("d30", "d100"):
        return 0.0, float(len(f4.period_dates(season, period)[1]))
    if target == "formation_day":
        return 1.0, 62.0
    return (0.0, None) if target in NONNEG else (None, None)


def main():
    os.makedirs(os.path.join(OUT, "emisiones"), exist_ok=True)
    s2m = pd.read_csv(os.path.join(_DATA, "s2m_ref_v2_69_74.csv.gz"), parse_dates=["dat"])
    met = pd.read_csv(os.path.join(_DATA, "f04", "bimonthly_metrics.csv"))
    met["formation_day"] = met.formation_date.map(formation_ordinal)
    boot = {}
    preds, logs, emis = [], [], defaultdict(list)
    folds = defaultdict(list)    # (model, massif, alt, geo, period, target) -> [(season, crps, rps, mean, y)]
    for alt, expo, slope, geo in STRATA:
        sub = s2m[(s2m.altitude == alt) & (s2m.exposition == expo) & (s2m.pente == slope)]
        for massif, g in sub.groupby("num_massif"):
            day = {d.date(): (h, w) for d, h, w in zip(g.dat, g.neigetot.astype(float), g.equivalent_eau.astype(float))}
            m = met[(met.num_massif == massif) & (met.altitude == alt) & (met.geo == geo)]
            for period in f4.PERIODS:
                mp = m[m.period == period].set_index("season")
                state = {}
                for s in SEASONS:
                    d0 = INIT_DAY[period](s)
                    a, b = day.get(d0), day.get(d0 - timedelta(days=30))
                    state[s] = None if a is None or b is None else (a[1], a[0], a[1] - b[1])   # SWE₀, HS₀, balance 30 d
                for target in targets_for(period, alt, geo):
                    ys = {s: (None if pd.isna(mp.at[s, target]) else float(mp.at[s, target])) for s in SEASONS}
                    for t in TEST:
                        if ys[t] is None or state[t] is None:
                            logs.append(dict(tipo="exclusion", massif=massif, altitude=alt, geo=geo, period=period,
                                             target=target, season=t, detalle="objetivo o estado UNKNOWN"))
                            continue
                        tr = [s for s in SEASONS if s < t and ys[s] is not None and state[s] is not None]
                        ty = [ys[s] for s in tr]
                        if target in NONNEG and fc.quantile7(ty, 0.9) == 0:
                            logs.append(dict(tipo="degeneracion", massif=massif, altitude=alt, geo=geo, period=period,
                                             target=target, season=t, detalle="P90 = 0 en el entrenamiento"))
                            continue
                        swe0 = state[t][0]
                        dists = {"M0": (fc.m0(ty), "")}
                        dists["M0b"] = (fc.regression_model([float(s) for s in tr], ty, float(t)) or fc.m0(ty), "")
                        r = fc.regression_model([state[s][0] for s in tr], ty, swe0)
                        dists["M0c-R"] = (r, "") if r is not None else (fc.m0(ty), "M0 (SWE₀ sin varianza)")
                        dists["M0d-R"] = fc.analog_predict(tr, [list(state[s][:2]) for s in tr], ty, t, list(state[t][:2]))
                        dists["M0d-R+"] = fc.analog_predict(tr, [list(state[s]) for s in tr], ty, t, list(state[t]))
                        edges = f4.tercile_edges(ty)
                        lo, hi = bounds(target, period, swe0, t)
                        for model in MODELS:
                            dist, cfg = dists[model]
                            if dist is None:
                                logs.append(dict(tipo="config_no_valida", massif=massif, altitude=alt, geo=geo,
                                                 period=period, target=target, season=t, detalle=f"{model}: {cfg}"))
                                continue
                            dist, cut = fc.truncate(dist, lo, hi)
                            vals = [v for v, _ in dist]
                            c = fc.crps(dist, ys[t])
                            rp = fc.rps(fc.tercile_probs(dist, edges), ys[t], edges)
                            mu = fc.mean(dist)
                            folds[(model, massif, alt, geo, period, target)].append((t, c, rp, mu, ys[t]))
                            row = dict(model=model, num_massif=massif, dominio=DOM[massif], altitude=alt, geo=geo,
                                       period=period, target=target, season=t, observado=ys[t], swe0=swe0,
                                       media=mu, p10=fc.quantile7(vals, 0.1), p50=fc.quantile7(vals, 0.5),
                                       p90=fc.quantile7(vals, 0.9), n_miembros=len(dist), crps=c, rps=rp,
                                       frac_truncada=cut, config=cfg)
                            preds.append(row)
                            emis[(period, t)].append({**row, "miembros": [[round(v, 4), round(w, 6)] for v, w in dist]})
                            if model.startswith("M0d"):
                                logs.append(dict(tipo="config_analogos", massif=massif, altitude=alt, geo=geo,
                                                 period=period, target=target, season=t, detalle=f"{model}: {cfg}"))
                            if cut > 0:
                                logs.append(dict(tipo="truncado", massif=massif, altitude=alt, geo=geo, period=period,
                                                 target=target, season=t, detalle=f"{model}: {cut:.3f}"))

    # Habilidad frente a M0
    skill = []
    for (model, massif, alt, geo, period, target), rows in folds.items():
        if model == "M0":
            continue
        ref = {s: (c, rp, mu, y) for s, c, rp, mu, y in folds[("M0", massif, alt, geo, period, target)]}
        common = [r for r in rows if r[0] in ref]
        if len(common) < 10:
            continue
        n = len(common)
        if n not in boot:
            boot[n] = fc.block_indices(n)
        c_ref = [ref[r[0]][0] for r in common]
        c_mod = [r[1] for r in common]
        test = fc.paired_test(c_ref, c_mod, boot[n])
        y = [r[4] for r in common]
        se_mod = sum((r[3] - r[4]) ** 2 for r in common)
        se_ref = sum((ref[r[0]][2] - r[4]) ** 2 for r in common)
        rps_ref = sum(ref[r[0]][1] for r in common)
        pre = [ref[r[0]][0] - r[1] for r in common if r[0] in PRE2002]
        post = [ref[r[0]][0] - r[1] for r in common if r[0] not in PRE2002]
        d_pre = sum(pre) / len(pre) if pre else None
        d_post = sum(post) / len(post) if post else None
        skill.append(dict(model=model, num_massif=massif, dominio=DOM[massif], altitude=alt, geo=geo, period=period,
                          target=target, **test, msss=(1 - se_mod / se_ref) if se_ref > 0 else None,
                          rpss=(1 - sum(r[2] for r in common) / rps_ref) if rps_ref > 0 else None,
                          mae=sum(abs(r[3] - r[4]) for r in common) / n, sesgo=sum(r[3] - r[4] for r in common) / n,
                          spearman=fc.spearman([r[3] for r in common], y),
                          d_media_1991_2001=d_pre, d_media_2002_2025=d_post,
                          estable=(d_pre is not None and d_post is not None and (d_pre > 0) == (d_post > 0))))

    # Hipótesis primarias
    sk = {(r["model"], r["num_massif"], r["altitude"], r["geo"], r["period"], r["target"]): r for r in skill}
    prim = []
    for period in f4.PERIODS:
        fam = [sk.get(("M0c-R", m, 2100, "llano", period, "dswe")) for m in DOM]
        ps = [r["p"] if r else 1.0 for r in fam]
        adj = fc.holm(ps)
        for m, r, pa in zip(DOM, fam, adj):
            comp = any((x := sk.get(("M0c-R", m, 2100, "llano", period, t))) and x["p"] < 0.05 and x["crpss"]
                       and x["crpss"] > 0 for t in ("g_swe", "l_swe"))
            state, why = fc.classify(pa if r else None, r["crpss"] if r else None, r["ic90_sup"] if r else None,
                                     r["estable"] if r else False, comp)
            prim.append(dict(hipotesis=f"H-{period}", num_massif=m, dominio=DOM[m], n=r["n"] if r else 0,
                             crpss=r["crpss"] if r else None, ic90_inf=r["ic90_inf"] if r else None,
                             ic90_sup=r["ic90_sup"] if r else None, p=r["p"] if r else None, p_holm_periodo=pa,
                             estable_2002=r["estable"] if r else None, componentes_g_o_l=comp, estado=state, motivo=why))
    adj18 = fc.holm([r["p"] if r["p"] is not None else 1.0 for r in prim])
    for r, a in zip(prim, adj18):
        r["p_holm_18"] = a

    # Matrices de transición (C16)
    trans = []
    dsw = met.set_index(["num_massif", "altitude", "geo", "period", "season"]).dswe
    for alt, _, _, geo in STRATA:
        for massif in DOM:
            for a, b in (("P1", "P2"), ("P2", "P3")):
                mat = [[0, 0, 0] for _ in range(3)]
                for t in TEST:
                    prev = [s for s in SEASONS if s < t]
                    ea = f4.tercile_edges([dsw[(massif, alt, geo, a, s)] for s in prev])
                    eb = f4.tercile_edges([dsw[(massif, alt, geo, b, s)] for s in prev])
                    mat[f4.tercile(dsw[(massif, alt, geo, a, t)], ea)][f4.tercile(dsw[(massif, alt, geo, b, t)], eb)] += 1
                for i, li in enumerate(("bajo", "medio", "alto")):
                    trans.append(dict(num_massif=massif, dominio=DOM[massif], altitude=alt, geo=geo, de=a, a=b,
                                      tercil_origen=li, bajo=mat[i][0], medio=mat[i][1], alto=mat[i][2]))

    def write(name, rows):
        with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            for r in rows:
                w.writerow({k: (round(v, 5) if isinstance(v, float) and not math.isnan(v) else v) for k, v in r.items()})
    write("predictions.csv", preds)
    write("skill.csv", skill)
    write("primary_hypotheses.csv", prim)
    write("transition_matrix.csv", trans)
    write("log.csv", logs)
    man = []
    for (period, t), rows in sorted(emis.items()):
        path = os.path.join(OUT, "emisiones", f"{period}_{t}.json")
        body = json.dumps({"inicializacion": str(INIT_DAY[period](t) + timedelta(days=1)), "periodo": period,
                           "invierno": t, "protocolo": "1ae92c1", "predicciones": rows}, ensure_ascii=False, sort_keys=True)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(body)
        with open(path, "rb") as f:
            man.append({"archivo": os.path.basename(path), "sha256": hashlib.sha256(f.read()).hexdigest()})
    with open(os.path.join(OUT, "emisiones", "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"protocolo": "1ae92c1", "concreciones": "docs/SEPI-F05-CONCRECIONES.md", "emisiones": man}, f, indent=1)
    print(f"{len(preds)} predicciones; {len(skill)} filas de habilidad; salidas en {OUT}")


if __name__ == "__main__":
    main()
