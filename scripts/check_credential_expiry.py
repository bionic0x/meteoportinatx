#!/usr/bin/env python3
"""Aviso de caducidad de la clave de AEMET (las claves nuevas caducan a los tres meses).

Lee la fecha de caducidad de la variable de Actions `AEMET_KEY_EXPIRES` (AAAA-MM-DD, no secreta) y
solo la PRESENCIA de `AEMET_API_KEY`: el valor nunca se lee más allá de comprobar que no está vacío,
ni se imprime. Sale con 1 (el workflow falla y GitHub avisa al propietario) cuando:
- la clave está presente pero no hay fecha registrada o no es válida;
- faltan AEMET_WARN_DAYS días o menos (14 por defecto) o ya ha caducado.
Sin clave configurada no falla: esa ausencia ya se informa en la publicación (eje «solo MeteoAlarm»).

Clave de Météo-France (`METEOFRANCE_API_KEY`, API DPObs): su caducidad la elige el propietario al
generarla, así que la fecha `METEOFRANCE_KEY_EXPIRES` es opcional; si está registrada se vigila igual.
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone

DEFAULT_WARN_DAYS = 14


def parse_day(value: str) -> date | None:
    """AAAA-MM-DD o fecha y hora ISO (p. ej. «2027-02-02 16:52:02+00:00», en UTC)."""
    value = (value or "").strip()
    try:
        return date.fromisoformat(value)
    except ValueError:
        pass
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (dt.astimezone(timezone.utc) if dt.tzinfo else dt).date()


def evaluate(key_present: bool, expires: str | None, today: date, warn_days: int = DEFAULT_WARN_DAYS) -> tuple[bool, str]:
    expires = (expires or "").strip()
    if not key_present:
        if expires:
            return True, f"AEMET_API_KEY ausente; AEMET_KEY_EXPIRES={expires} no se usa (eje oficial solo MeteoAlarm)"
        return True, "AEMET_API_KEY ausente: nada que vigilar (eje oficial solo MeteoAlarm)"
    if not expires:
        return False, "AEMET_API_KEY presente sin fecha de caducidad: registra la variable AEMET_KEY_EXPIRES (AAAA-MM-DD)"
    end = parse_day(expires)
    if end is None:
        return False, f"AEMET_KEY_EXPIRES no es una fecha válida (AAAA-MM-DD o fecha y hora ISO): {expires!r}"
    left = (end - today).days
    if left < 0:
        return False, f"La clave de AEMET CADUCÓ el {end.isoformat()} (hace {-left} días): renuévala y actualiza AEMET_KEY_EXPIRES"
    if left <= warn_days:
        return False, f"La clave de AEMET caduca el {end.isoformat()} (quedan {left} días): renuévala y actualiza AEMET_KEY_EXPIRES"
    return True, f"Clave de AEMET vigente hasta el {end.isoformat()} (quedan {left} días)"


def evaluate_meteofrance(key_present: bool, expires: str | None, today: date,
                         warn_days: int = DEFAULT_WARN_DAYS) -> tuple[bool, str]:
    expires = (expires or "").strip()
    if not key_present:
        return True, "METEOFRANCE_API_KEY ausente: Météo-France en tiempo real queda «sin clave» (UNKNOWN)"
    if not expires:
        return True, ("METEOFRANCE_API_KEY presente sin fecha registrada: si la clave caduca, "
                      "anota METEOFRANCE_KEY_EXPIRES (AAAA-MM-DD) para recibir el aviso")
    end = parse_day(expires)
    if end is None:
        return False, f"METEOFRANCE_KEY_EXPIRES no es una fecha válida (AAAA-MM-DD o fecha y hora ISO): {expires!r}"
    left = (end - today).days
    if left < 0:
        return False, f"La clave de Météo-France CADUCÓ el {end.isoformat()} (hace {-left} días): genera otra en portail-api.meteofrance.fr"
    if left <= warn_days:
        return False, f"La clave de Météo-France caduca el {end.isoformat()} (quedan {left} días): genera otra y actualiza METEOFRANCE_KEY_EXPIRES"
    return True, f"Clave de Météo-France vigente hasta el {end.isoformat()} (quedan {left} días)"


def permission_checks(directory, today: date, warn_days: int = DEFAULT_WARN_DAYS) -> list[tuple[bool, str]]:
    """Permisos de fuentes (`permisos/*.json`, salvo ejemplos): avisa antes de que venzan."""
    import json
    from pathlib import Path
    out = []
    for f in sorted(Path(directory).glob("*.json")):
        if f.name.endswith(".example.json"):
            continue
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
            end = rec.get("valido_hasta")
            end = date.fromisoformat(end) if end else None
        except (OSError, ValueError, AttributeError):
            out.append((False, f"Permiso {f.name} ilegible o con fecha inválida: la fuente queda desactivada"))
            continue
        if end is None:
            out.append((True, f"Permiso {f.name}: sin fecha de fin"))
            continue
        left = (end - today).days
        if left < 0:
            out.append((True, f"Permiso {f.name} vencido el {end.isoformat()}: la fuente se desactivó sola"))
        elif left <= warn_days:
            out.append((False, f"Permiso {f.name} vence el {end.isoformat()} (quedan {left} días): renuévalo o la fuente se desactivará"))
        else:
            out.append((True, f"Permiso {f.name} vigente hasta el {end.isoformat()} (quedan {left} días)"))
    return out


def main() -> int:
    try:
        warn = int(os.environ.get("AEMET_WARN_DAYS") or DEFAULT_WARN_DAYS)
    except ValueError:
        warn = DEFAULT_WARN_DAYS
    today = datetime.now(timezone.utc).date()
    results = [evaluate(bool(os.environ.get("AEMET_API_KEY")), os.environ.get("AEMET_KEY_EXPIRES"), today, warn),
               evaluate_meteofrance(bool((os.environ.get("METEOFRANCE_API_KEY") or "").strip()),
                                    os.environ.get("METEOFRANCE_KEY_EXPIRES"), today, warn)]
    from pathlib import Path
    results += permission_checks(Path(__file__).resolve().parents[1] / "permisos", today, warn)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    for ok, msg in results:
        print(msg if ok else f"::error::{msg}")
        if summary:
            with open(summary, "a", encoding="utf-8") as f:
                f.write(("✅ " if ok else "❌ ") + msg + "\n")
    return 0 if all(ok for ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
