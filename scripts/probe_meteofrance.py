#!/usr/bin/env python3
"""Sonda de METEOFRANCE_API_KEY contra DPObs (src/meteo_france_obs.py).

Imprime solo el estado, el código HTTP del catálogo y recuentos por estación: nunca la clave.
Sale con 0 si hay lecturas o si no hay clave configurada; con 1 si la clave falla o no hay datos.
"""
from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import meteo_france_obs as mf  # noqa: E402


def main() -> int:
    if not os.environ.get("METEOFRANCE_API_KEY", "").strip():
        print("ESTADO: sin METEOFRANCE_API_KEY (la fuente queda «sin clave»)")
        return 0
    key = os.environ["METEOFRANCE_API_KEY"].strip()
    url = mf.BASE + "/liste-stations?format=csv"
    catalog, codes = None, {}
    # Diagnóstico: mismo endpoint con las dos formas que emite el portal (token OAuth2 y clave API).
    for label, header in (("Bearer", {"Authorization": "Bearer " + key}), ("apikey", {"apikey": key})):
        req = urllib.request.Request(url, headers={**header, "Accept": "*/*", "User-Agent": "meteoportinatx-probe"})
        try:
            with urllib.request.urlopen(req, timeout=35) as r:
                codes[label] = r.status
                catalog = catalog or r.read().decode("utf-8-sig", "replace")
        except urllib.error.HTTPError as exc:
            codes[label] = exc.code
        except Exception as exc:
            codes[label] = type(exc).__name__
    print("Catálogo DPObs v2: " + ", ".join(f"{k} → HTTP {v}" for k, v in codes.items()))
    if catalog is None:
        hint = {401: "token no válido o caducado (los tokens del portal duran 1 h; hace falta una clave API)",
                403: "aplicación sin suscripción a «Données d'observation» o credencial de otro tipo"}
        print("ESTADO: credencial rechazada · " + hint.get(codes.get("Bearer"), "revisar en portail-api.meteofrance.fr"))
        return 1
    print("Tipo de credencial: " + ("clave API (cabecera apikey)" if codes.get("apikey") == 200 else "token OAuth2 (Bearer)"))
    print(f"Catálogo DPObs: ok · {len(mf.station_catalog(catalog))} estaciones en el dominio")
    try:
        obs = mf.fetch_observations()
    except Exception as exc:
        print(f"ESTADO: sin lecturas: {type(exc).__name__}: {str(exc)[:200]}")
        return 1
    print(f"ESTADO: ok · {len(obs)} estaciones con lectura ≤{mf.MAX_AGE_MIN} min")
    for o in obs:
        print(f"  {o['id']} {o['nombre']} ({o['alt']} m): edad {o['edad_min']} min, T={o['T']}, HR={o['HR']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
