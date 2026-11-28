"""SEPI fase 04: matrices de transición entre periodos (terciles P1→P2 y P2→P3) de ΔSWE.

BLOQUEADO sobre S2M hasta que docs/SEPI-P-PROTOCOLO.md esté congelado (protocolo §9): las transiciones
revelan dependencia temporal y, por tanto, predictibilidad potencial. Con --sintetico se ejecuta sobre datos
generados para probar el código, sin leer S2M.

Uso:
  python scripts/sepi/phase04_transitions.py --sintetico
  SEPI_DATA=... python scripts/sepi/phase04_transitions.py      # solo con el protocolo congelado (PR 3)
"""
import argparse
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f04_core as fc  # noqa: E402

_REPO = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
PAIRS = (("P1", "P2"), ("P2", "P3"))


def synthetic(seed=20261128, n=58):
    rnd = random.Random(seed)
    p1 = [rnd.gauss(0, 1) for _ in range(n)]
    p2 = [0.5 * a + rnd.gauss(0, 1) for a in p1]
    return {"P1": p1, "P2": p2, "P3": [rnd.gauss(0, 1) for _ in range(n)]}


def show(name, m):
    print(f"{name}  (filas: tercil del periodo anterior; columnas: del siguiente)")
    for label, row in zip(("bajo", "medio", "alto"), m):
        print(f"  {label:>5}: {row}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sintetico", action="store_true", help="Probar el código con datos sintéticos (no lee S2M)")
    args = ap.parse_args()
    if args.sintetico:
        data = synthetic()
        for a, b in PAIRS:
            show(f"SINTÉTICO {a}→{b}", fc.transition_matrix(
                zip(data[a], data[b]), fc.tercile_edges(data[a]), fc.tercile_edges(data[b])))
        return
    with open(os.path.join(_REPO, "docs", "SEPI-P-PROTOCOLO.md"), encoding="utf-8") as f:
        fc.require_frozen_protocol(f.read())
    raise SystemExit("La ejecución sobre S2M se implementa en el PR 3, con los terciles calculados solo con el "
                     "entrenamiento de cada pliegue (protocolo §6).")


if __name__ == "__main__":
    main()
