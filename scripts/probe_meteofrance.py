#!/usr/bin/env python3
"""Sonda de METEOFRANCE_API_KEY contra DPObs (src/meteo_france_obs.py).

Imprime solo el estado, el código HTTP del catálogo y recuentos por estación: nunca la clave.
Sale con 0 si hay lecturas o si no hay clave configurada; con 1 si la clave falla o no hay datos.
"""
from __future__ import annotations

import os
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import meteo_france_obs as mf  # noqa: E402


def main() -> int:
    if not os.environ.get("METEOFRANCE_API_KEY", "").strip():
        print("ESTADO: sin METEOFRANCE_API_KEY (la fuente queda «sin clave»)")
        return 0
    try:
        catalog = mf._request("/liste-stations", {"format": "csv"})
    except urllib.error.HTTPError as exc:
        hint = {401: "token no válido o caducado", 403: "sin suscripción a DPObs o credencial de otro tipo"}
        print(f"ESTADO: catálogo DPObs HTTP {exc.code} ({hint.get(exc.code, 'error del servicio')})")
        return 1
    except Exception as exc:
        print(f"ESTADO: catálogo DPObs falló: {type(exc).__name__}")
        return 1
    print(f"Catálogo DPObs: ok · {len(mf.station_catalog(catalog))} estaciones en el dominio")
    try:
        obs = mf.fetch_observations()
    except Exception as exc:
        print(f"ESTADO: sin lecturas: {type(exc).__name__}: {str(exc)[:160]}")
        return 1
    print(f"ESTADO: ok · {len(obs)} estaciones con lectura ≤{mf.MAX_AGE_MIN} min")
    for o in obs:
        print(f"  {o['id']} {o['nombre']} ({o['alt']} m): edad {o['edad_min']} min, T={o['T']}, HR={o['HR']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
