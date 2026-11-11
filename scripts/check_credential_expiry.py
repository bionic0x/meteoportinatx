#!/usr/bin/env python3
"""Aviso de caducidad de la clave de AEMET (las claves nuevas caducan a los tres meses).

Lee la fecha de caducidad de la variable de Actions `AEMET_KEY_EXPIRES` (AAAA-MM-DD, no secreta) y
solo la PRESENCIA de `AEMET_API_KEY`: el valor nunca se lee más allá de comprobar que no está vacío,
ni se imprime. Sale con 1 (el workflow falla y GitHub avisa al propietario) cuando:
- la clave está presente pero no hay fecha registrada o no es válida;
- faltan AEMET_WARN_DAYS días o menos (14 por defecto) o ya ha caducado.
Sin clave configurada no falla: esa ausencia ya se informa en la publicación (eje «solo MeteoAlarm»).
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone

DEFAULT_WARN_DAYS = 14


def evaluate(key_present: bool, expires: str | None, today: date, warn_days: int = DEFAULT_WARN_DAYS) -> tuple[bool, str]:
    expires = (expires or "").strip()
    if not key_present:
        if expires:
            return True, f"AEMET_API_KEY ausente; AEMET_KEY_EXPIRES={expires} no se usa (eje oficial solo MeteoAlarm)"
        return True, "AEMET_API_KEY ausente: nada que vigilar (eje oficial solo MeteoAlarm)"
    if not expires:
        return False, "AEMET_API_KEY presente sin fecha de caducidad: registra la variable AEMET_KEY_EXPIRES (AAAA-MM-DD)"
    try:
        end = date.fromisoformat(expires)
    except ValueError:
        return False, f"AEMET_KEY_EXPIRES no es una fecha AAAA-MM-DD válida: {expires!r}"
    left = (end - today).days
    if left < 0:
        return False, f"La clave de AEMET CADUCÓ el {end.isoformat()} (hace {-left} días): renuévala y actualiza AEMET_KEY_EXPIRES"
    if left <= warn_days:
        return False, f"La clave de AEMET caduca el {end.isoformat()} (quedan {left} días): renuévala y actualiza AEMET_KEY_EXPIRES"
    return True, f"Clave de AEMET vigente hasta el {end.isoformat()} (quedan {left} días)"


def main() -> int:
    try:
        warn = int(os.environ.get("AEMET_WARN_DAYS") or DEFAULT_WARN_DAYS)
    except ValueError:
        warn = DEFAULT_WARN_DAYS
    ok, msg = evaluate(bool(os.environ.get("AEMET_API_KEY")), os.environ.get("AEMET_KEY_EXPIRES"),
                       datetime.now(timezone.utc).date(), warn)
    print(msg if ok else f"::error::{msg}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(("✅ " if ok else "❌ ") + msg + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
