"""SEPI fase 04 (PR 2): objetivos y climatologías bimestrales DESCRIPTIVAS, según docs/SEPI-P-PROTOCOLO.md v0.4.

Solo distribuciones marginales de cada periodo por separado: no calcula ninguna relación entre periodos
(transiciones, correlaciones ni regresiones) ni ninguna habilidad. Eso queda para el PR 3, tras la congelación.

Entrada: SEPI_DATA/s2m_ref_v2_69_74.csv.gz (fetch_hist.py). Inviernos 1968–69 … 2025–26 (año de inicio).
Estratos (§2): 2.100 m llano (primario); 1.800 m llano, N20 y NO20 (secundarios). Macizos 69–74.
Salidas en SEPI_DATA/f04/: bimonthly_metrics.csv, bimonthly_coverage.csv, bimonthly_climatology.csv,
bimonthly_percentiles.csv, degenerate_variables.csv y manifest.json.
"""
import hashlib
import json
import os
import subprocess
import sys
from datetime import date, datetime, timezone

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f04_core as fc  # noqa: E402

_REPO = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DATA = os.path.realpath(os.environ.get("SEPI_DATA", ""))
if not os.environ.get("SEPI_DATA") or os.path.commonpath([_REPO, _DATA]) == _REPO:
    raise SystemExit("Define SEPI_DATA con una carpeta fuera del repositorio (ver scripts/sepi/README.md).")

SRC = os.path.join(_DATA, "s2m_ref_v2_69_74.csv.gz")
OUT = os.path.join(_DATA, "f04")
SEASONS = list(range(1968, 2026))
DOM = {69: "Couserans (control)", 70: "Haute-Ariège", 71: "Andorra", 72: "Orlu–St-Barthélemy",
       73: "Capcir–Puymorens", 74: "Cerdagne–Canigou"}
STRATA = [(2100, -1, 0, "llano", "primario"), (1800, -1, 0, "llano", "secundario"),
          (1800, 0, 20, "N20", "secundario"), (1800, 315, 20, "NO20", "secundario")]
NONNEG = ["g_swe", "l_swe", "g_hs", "d30", "d100", "swe_end", "hs_end"]
VARS = ["dswe", "g_swe", "l_swe", "g_hs", "d30", "d100", "swe_end", "hs_end"]
COVERAGE = ["n_days", "n_hs_obs", "n_swe_obs", "swe_extremes_ok", "swe_sequence_complete",
            "hs_sequence_complete", "d_threshold_coverage_ok"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(OUT, exist_ok=True)
    s2m = pd.read_csv(SRC, parse_dates=["dat"])
    rows = []
    for (alt, expo, slope, geo, role) in STRATA:
        sub = s2m[(s2m.altitude == alt) & (s2m.exposition == expo) & (s2m.pente == slope)]
        for massif, g in sub.groupby("num_massif"):
            dates = [d.date() for d in g.dat]
            hs = dict(zip(dates, g.neigetot.astype(float)))
            swe = dict(zip(dates, g.equivalent_eau.astype(float)))
            for season in SEASONS:
                for period in fc.PERIODS:
                    r = fc.period_metrics(season, period, hs, swe, alt, expo, slope)
                    r.update(num_massif=int(massif), dominio=DOM[int(massif)], altitude=alt, geo=geo, estrato=role,
                             label=f"{season}–{str(season + 1)[-2:]}")
                    rows.append(r)
    m = pd.DataFrame(rows)
    keys = ["num_massif", "dominio", "altitude", "geo", "estrato", "season", "label", "period"]
    m[keys + ["swe0"] + VARS + ["formation_date", "formation_censored"]].to_csv(
        os.path.join(OUT, "bimonthly_metrics.csv"), index=False, float_format="%.3f")
    m[keys + COVERAGE].to_csv(os.path.join(OUT, "bimonthly_coverage.csv"), index=False)

    clim, pct, degen = [], [], []
    for (massif, alt, geo, period), g in m.groupby(["num_massif", "altitude", "geo", "period"]):
        base = dict(num_massif=massif, dominio=DOM[massif], altitude=alt, geo=geo, period=period,
                    periodo=fc.PERIOD_NAMES[period])
        for var in VARS:
            vals = [float(v) for v in g[var] if pd.notna(v)]
            if not vals:
                continue
            s = pd.Series(vals)
            clim.append({**base, "variable": var, "n": len(vals), "n_unknown": int(g[var].isna().sum()),
                         "media": s.mean(), "desv": s.std(ddof=1), "min": s.min(), "max": s.max(),
                         "frac_cero": float((s == 0).mean())})
            pct.append({**base, "variable": var, **{f"P{q}": fc.quantile_type7(vals, q / 100) for q in fc.PERCENTILES}})
            if var in NONNEG:      # la regla P90 = 0 solo tiene sentido en variables no negativas
                p90 = fc.quantile_type7(vals, 0.9)
                degen.append({**base, "variable": var, "P90": p90, "degenerada": p90 == 0})
        if period == "P1":
            ranks = []
            for v in g.formation_date:
                if v == fc.CENSORED:
                    ranks.append(62)
                elif isinstance(v, str):
                    ranks.append((date.fromisoformat(v) - date(int(v[:4]), 11, 1)).days + 1)
            pct.append({**base, "variable": "formation_day", **{
                f"P{q}": fc.quantile_censored(ranks, q / 100, 62) for q in fc.PERCENTILES}})
            clim.append({**base, "variable": "formation_day", "n": len(ranks), "n_unknown": 0,
                         "frac_censurado": sum(r == 62 for r in ranks) / len(ranks)})
    pd.DataFrame(clim).to_csv(os.path.join(OUT, "bimonthly_climatology.csv"), index=False, float_format="%.3f")
    pd.DataFrame(pct).to_csv(os.path.join(OUT, "bimonthly_percentiles.csv"), index=False, float_format="%.3f")
    pd.DataFrame(degen).to_csv(os.path.join(OUT, "degenerate_variables.csv"), index=False, float_format="%.3f")

    try:
        commit = subprocess.run(["git", "-C", _REPO, "rev-parse", "HEAD"], capture_output=True, text=True,
                                check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    proto = os.path.join(_REPO, "docs", "SEPI-P-PROTOCOLO.md")
    manifest = {
        "generado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "script": "scripts/sepi/phase04_climatology.py", "commit_repo": commit,
        "entrada": {"archivo": os.path.basename(SRC), "sha256": sha256(SRC), "filas": int(len(s2m)),
                    "ultima_fecha": str(s2m.dat.max().date())},
        "protocolo": {"archivo": "docs/SEPI-P-PROTOCOLO.md", "sha256": sha256(proto),
                      "congelado": fc.protocol_frozen(open(proto, encoding="utf-8").read())},
        "inviernos": [SEASONS[0], SEASONS[-1]], "periodos": fc.PERIOD_NAMES,
        "estratos": [{"altitude": a, "geo": g, "rol": r} for a, _, _, g, r in STRATA],
        "percentiles": list(fc.PERCENTILES),
        "degeneracion": "P90 = 0 en el conjunto completo, solo para variables no negativas; descriptivo (en el PR 3 se evalúa por pliegue)",
        "metodo_percentiles": "tipo 7 (lineal); fecha de formación: tipo 1 con censura a 31-dic (rango 62)",
        "unidades": {"swe": "kg/m² (= mm)", "hs": "cm", "formation_day": "días desde el 1-nov (1 = 1-nov)"},
        "alcance": "Descriptivo por periodo. Sin relaciones entre periodos ni habilidad (protocolo §9).",
        "salidas": sorted(f for f in os.listdir(OUT) if f.endswith(".csv")),
    }
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"{len(m)} filas de métricas; salidas en {OUT}")


if __name__ == "__main__":
    main()
