"""Observación en tiempo real de Météo-France para el Pirineo (API DPObs, clave del propietario).

Fuente: portail-api.meteofrance.fr, «Données d'observation» (DPObs v1), datos públicos bajo Licence
Ouverte (Etalab). Requiere una clave gratuita en la variable de entorno `METEOFRANCE_API_KEY`; se envía en la
cabecera `apikey` y nunca se imprime. Sin clave la fuente queda «sin clave» (UNKNOWN), nunca a 0.

Sustituye a la lectura de tablas de meteociel.fr para las estaciones de Météo-France: mismo dato,
de su productor, con licencia explícita.

Endpoints (v1):
- `paquet/horaire?id-departement=DD&format=json`: horario de todas las estaciones del departamento,
  últimas 24 h. Se usa primero (2 peticiones por ciclo).
- `station/horaire?id_station=NNNNNNNN&format=json`: última hora de una estación. Respaldo si el paquete
  falla por algo que no sea la clave.
Unidades del productor: t y td en K, ff y fxi en m/s, pres en Pa, rr1 en mm, u en %.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

UTC = timezone.utc
API = "https://public-api.meteofrance.fr/public/DPObs/v1"
TOKEN_URL = "https://portail-api.meteofrance.fr/token"
KEY_ENV = "METEOFRANCE_API_KEY"
ATTRIBUTION = "Météo-France, données d'observation en temps réel (API DPObs, Licence Ouverte Etalab)"
# Estaciones del dominio según el archivo horario oficial (NUM_POSTE, coordenadas y altitud de Météo-France).
STATIONS = {
    "66067402": ("Puigmal nivôse (MF)", 42.380667, 2.095333, 2461),
    "66082004": ("Formiguères (MF)", 42.616, 2.111333, 1495),
    "66157001": ("Railleu (MF)", 42.586667, 2.181, 1366),
    "66202001": ("Targasonne (MF)", 42.504, 1.973333, 1600),
    "09023002": ("Ascou Lavail (MF)", 42.725333, 1.8885, 1090),
    "09024004": ("Aston (MF)", 42.724167, 1.691, 1781),
}


class KeyRejected(PermissionError):
    """La API rechazó la credencial (401/403) de todas las formas probadas: caducada, revocada o sin
    suscripción a DPObs. `intentos` dice qué forma y endpoint dieron qué código (nunca la credencial)."""

    def __init__(self, msg, intentos=()):
        super().__init__(msg)
        self.intentos = list(intentos)


def _looks_like_application_id(key: str) -> bool:
    """El «application ID» del portal es base64 de «client_id:client_secret»."""
    try:
        return b":" in base64.b64decode(key, validate=True)
    except (ValueError, TypeError):
        return False


def _default_token(app_id: str) -> str:
    req = urllib.request.Request(TOKEN_URL, data=b"grant_type=client_credentials",
                                 headers={"Authorization": "Basic " + app_id,
                                          "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["access_token"]


def auth_modes(key: str, token=None):
    """Formas de presentar la credencial, por orden: clave API, token OAuth2 y application ID → token."""
    yield "apikey", {"apikey": key}
    yield "bearer", {"Authorization": "Bearer " + key}
    if _looks_like_application_id(key):
        try:
            yield "application_id", {"Authorization": "Bearer " + (token or _default_token)(key)}
        except Exception:
            return


def _num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def _time(s) -> datetime | None:
    if not isinstance(s, str) or not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)


def _celsius(k):
    v = _num(k)
    if v is None:
        return None
    return round(v - 273.15, 1) if v > 150 else round(v, 1)     # el productor da K; tolera °C


def records(payload) -> list[dict]:
    """Normaliza la respuesta (lista JSON, GeoJSON o un único objeto) a filas planas con `geo_id_insee`."""
    if isinstance(payload, (bytes, str)):
        payload = json.loads(payload or "[]")
    if isinstance(payload, dict) and "features" in payload:
        rows = []
        for f in payload.get("features") or []:
            p = dict(f.get("properties") or {})
            c = (f.get("geometry") or {}).get("coordinates") or []
            if len(c) >= 2:
                p.setdefault("lon", c[0])
                p.setdefault("lat", c[1])
            rows.append(p)
        return rows
    if isinstance(payload, dict):
        return [payload]
    return [r for r in payload or [] if isinstance(r, dict)]


def station_obs(sid: str, rows: list[dict], now: datetime, tz) -> dict | None:
    """Fila del formato común de observaciones del Pirineo para una estación (última hora con T)."""
    series = sorted(((t, r) for r in rows if (t := _time(r.get("validity_time"))) is not None), key=lambda x: x[0])
    with_t = [(t, r) for t, r in series if _num(r.get("t")) is not None]
    if not with_t:
        return None
    t_last, last = with_t[-1]
    name, lat, lon, alt = STATIONS.get(sid, (f"{sid} (MF)", _num(last.get("lat")), _num(last.get("lon")), None))
    # Día local completo (todas las horas desde la medianoche) o nada: ausencia ≠ 0.
    local_day = t_last.astimezone(tz).date()
    start = datetime.combine(local_day, datetime.min.time(), tz).astimezone(UTC)
    day = {t: r for t, r in series if start < t <= t_last}
    expected = int((t_last - start).total_seconds() // 3600)
    rain = [_num(r.get("rr1")) for r in day.values()]
    gust = [_num(r.get("fxi")) for r in day.values()]
    complete = expected > 0 and len(day) == expected
    ff, pres = _num(last.get("ff")), _num(last.get("pres"))
    return {"id": sid, "red": "Météo-France", "nombre": name, "lat": lat, "lon": lon, "alt": alt,
            "t": t_last.isoformat(), "edad_min": round((now - t_last).total_seconds() / 60),
            "T": _celsius(last.get("t")), "HR": _num(last.get("u")),
            "P": round(pres / 100, 1) if pres is not None and pres > 2000 else pres,
            "viento": round(ff * 3.6) if ff is not None else None,
            "racha_dia": round(max(gust) * 3.6) if complete and all(g is not None for g in gust) else None,
            "lluvia_dia": round(sum(rain), 1) if complete and all(x is not None for x in rain) else None}


class _EndpointDenied(Exception):
    """403 en el paquete con la clave API: puede ser el endpoint, no la clave; se prueba el de estación."""


def _default_get(url: str, headers: dict) -> bytes:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def fetch(now: datetime | None = None, tz=UTC, key: str | None = None, get=None, token=None) -> list[dict]:
    """Observaciones del dominio. `get(url, headers) -> bytes` inyectable para tests.
    Sin clave → PermissionError; clave rechazada → KeyRejected; nunca devuelve ceros inventados."""
    key = key if key is not None else os.environ.get(KEY_ENV, "")
    if not key.strip():
        raise PermissionError(f"sin {KEY_ENV}")
    now = now or datetime.now(UTC)
    get = get or _default_get
    base = {"accept": "application/json", "User-Agent": "meteoportinatx-pirineo (observación horaria)"}
    modes = auth_modes(key.strip(), token)
    state = {"mode": None, "headers": None}
    intentos = []

    def call(url):
        """GET autenticado. Prueba las formas de credencial hasta que una no dé 401/403 y se queda con ella."""
        endpoint = url.split("/v1/")[1].split("?")[0]
        while True:
            if state["headers"] is None:
                nxt = next(modes, None)
                if nxt is None:
                    raise KeyRejected("Météo-France rechazó la credencial: " +
                                      ", ".join(f"{m} {e} HTTP {c}" for m, e, c in intentos), intentos)
                state["mode"], h = nxt
                state["headers"] = {**base, **h}
            try:
                return get(url, state["headers"])
            except urllib.error.HTTPError as exc:
                if exc.code not in (401, 403):
                    raise
                intentos.append((state["mode"], endpoint, exc.code))
                if exc.code == 403 and endpoint.startswith("paquet"):
                    raise _EndpointDenied() from None       # puede ser el endpoint: se prueba el de estación
                state["headers"] = None                     # 401/403 en estación: siguiente forma de credencial

    by_station: dict[str, list[dict]] = {}
    errors = []
    for dept in sorted({sid[:2] for sid in STATIONS}):
        try:
            rows = records(call(f"{API}/paquet/horaire?id-departement={dept}&format=json"))
        except KeyRejected:
            raise
        except _EndpointDenied:
            errors.append(f"paquet {dept}: HTTP 403")
            rows = None
        except Exception as exc:
            errors.append(f"paquet {dept}: {type(exc).__name__}")
            rows = None
        if rows:
            for r in rows:
                sid = str(r.get("geo_id_insee") or "").zfill(8)
                if sid in STATIONS:
                    by_station.setdefault(sid, []).append(r)
            continue
        for sid in (s for s in STATIONS if s[:2] == dept):          # respaldo: última hora por estación
            try:
                by_station.setdefault(sid, []).extend(records(call(f"{API}/station/horaire?id_station={sid}&format=json")))
            except KeyRejected:
                raise
            except Exception as exc:
                errors.append(f"{sid}: {type(exc).__name__}")
    fetch.last_auth = state["mode"]                 # forma de credencial que funcionó (para la sonda)
    out = [o for sid, rows in by_station.items() if (o := station_obs(sid, rows, now, tz))]
    if not out:
        raise RuntimeError("sin observaciones de Météo-France: " + (", ".join(errors) or "respuesta vacía"))
    return sorted(out, key=lambda o: -(o["alt"] or 0))


if __name__ == "__main__":                       # sonda: solo estado y recuentos, nunca la clave
    import sys
    try:
        obs = fetch()
    except PermissionError as exc:
        print(f"ESTADO: {type(exc).__name__}: {exc}")
        if os.environ.get(KEY_ENV) and _looks_like_application_id(os.environ[KEY_ENV].strip()):
            print("  (el valor tiene forma de application ID; se probó también el canje por token)")
        sys.exit(0 if not os.environ.get(KEY_ENV) else 1)
    except Exception as exc:
        print(f"ESTADO: error {type(exc).__name__}: {str(exc)[:200]}")
        sys.exit(1)
    print(f"ESTADO: ok · {len(obs)} estaciones · credencial aceptada como «{fetch.last_auth}»")
    for o in obs:
        print(f"  {o['id']} {o['nombre']}: edad {o['edad_min']} min, T={o['T']}, HR={o['HR']}, "
              f"viento={o['viento']}, lluvia_dia={o['lluvia_dia']}")
