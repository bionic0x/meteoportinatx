#!/usr/bin/env python3
"""SEPI-GEO-01: estadísticas de cambio entre variantes en los 129 puntos (solo Python estándar).

Lee SEPI_DATA/terrain/geo01/points_comparison.csv y escribe terrain_statistics.csv con sesgo, MAE, RMSE,
mediana y P95 de |Δ|, máximo y correlación de rangos de Spearman.

Comparaciones, cada una aísla un efecto:
  V0 → V0r   réplica: ¿reproduce el código local el motor actual?
  V0r → V1k  mismo DEM y escala: muestrear un nodo frente a promediar la celda de 0,01°
  V1k → V3k  misma escala (0,01°): cambio de DEM, de GLO-90 a GLO-30
  V0 → V1    motor actual frente a GLO-90 nativo (incluye el cambio de definición a escala nativa)
  V1 → V2    misma resolución (90 m): cambio de DEM
  V2 → V3    mismo DEM (GLO-30): de 90 a 30 m
  V1 → V3    efecto total
  referencia → Vx  solo en altitud: frente a la cota de referencia del motor (GeoNames)
La orientación es circular: se usa la diferencia angular mínima.
"""
import csv
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import geo_terrain_core as gt  # noqa: E402

PAIRS = [("V0", "V0r"), ("V0r", "V1k"), ("V1k", "V3k"), ("V0", "V1"), ("V1", "V2"), ("V2", "V3"), ("V1", "V3")]
REF_PAIRS = [("referencia", v) for v in ("V0r", "V1k", "V3k", "V1", "V2", "V3")]


def main():
    raw = os.environ.get("SEPI_DATA")
    if not raw:
        raise SystemExit("Define SEPI_DATA.")
    d = Path(raw) / "terrain" / "geo01"
    vals = defaultdict(dict)
    meta = {}
    with open(d / "points_comparison.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            vals[(r["variable"], r["variante"])][r["punto"]] = float(r["valor"]) if r["valor"] not in ("", "None") else None
            meta[r["punto"]] = r["tipo"]
    out = []
    for var in sorted({v for v, _ in vals}):
        pairs = REF_PAIRS if var == "altitud" else PAIRS
        for a, b in pairs:
            if (var, a) not in vals or (var, b) not in vals:
                continue
            for subset in ("todos", "cima", "pueblo", "estacion_esqui"):
                keys = [k for k in vals[(var, a)] if subset == "todos" or meta[k] == subset]
                ra = [vals[(var, a)].get(k) for k in keys]
                rb = [vals[(var, b)].get(k) for k in keys]
                if var == "orientacion":       # diferencia circular: se compara el giro con respecto a ra
                    rb = [None if x is None or y is None else x + ((y - x + 180) % 360 - 180) for x, y in zip(ra, rb)]
                s = gt.change_stats(ra, rb)
                if s.get("n", 0) == 0:
                    continue
                out.append({"variable": var, "de": a, "a": b, "subconjunto": subset,
                            **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in s.items()}})
    with open(d / "terrain_statistics.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["variable", "de", "a", "subconjunto", "n", "sesgo", "mae", "rmse",
                                          "mediana_abs", "p95_abs", "max_abs", "spearman"])
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)} filas en {d / 'terrain_statistics.csv'}")


if __name__ == "__main__":
    main()
