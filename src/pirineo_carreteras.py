"""Pirineo Nowcast · carreteras de la Cerdanya, el Capcir y Andorra oriental (EXPERIMENTAL).

Solo biblioteca estándar. Dos partes separadas, que nunca se mezclan:

  1. Estado oficial: incidencias de los servicios de tráfico con datos abiertos.
       - Servei Català de Trànsit (SCT), GML de incidencias de Cataluña.
       - Bison Futé / DIR Sud-Ouest, DATEX II de la red nacional francesa (RN20, RN22, RN320, RN116).
     Sin fuente abierta automática (solo enlace): Mobilitat Andorra y la red departamental de los
     Pirineos Orientales (Inforoute 66). Si una fuente falla, su estado es UNKNOWN: «sin incidencias» solo
     se afirma con la fuente leída.
  2. Exposición meteorológica (diagnóstico propio, no estado de la vía): km de calzada por encima de la cota
     de copo efectiva, tramos en cubeta fría (hielo probable con noche despejada) y puertos.

El trazado es aproximado (puntos de paso ±1–2 km, perfil ajustado al fondo de valle). No es información
oficial de tráfico ni sustituye a SCT, DGT, Bison Futé, Inforoute 66 o Mobilitat.
"""
from __future__ import annotations

import math
import re
from concurrent.futures import ThreadPoolExecutor
import xml.etree.ElementTree as ET

BBOX = (42.15, 42.80, 1.40, 2.30)          # Cerdanya, Capcir, Andorra oriental, Carol y accesos (sin Garrotxa)
SCT_URL = "https://www.gencat.cat/transit/opendata/incidenciesGML.xml"
BF_URL = "https://tipi.bison-fute.gouv.fr/bison-fute-ouvert/publicationsDIR/Evenementiel-DIR/grt/RRN/content.xml"
SIN_FEED = {"andorra": ("Mobilitat Andorra", "https://www.mobilitat.ad/totes-incidencies"),
            "pyrenees_orientales": ("Inforoute 66 (red departamental)", "https://www.inforoute66.fr")}
# Palabras completas (no subcadenas: «ice» no debe casar con «service» ni «neu» con «neutralisation»)
WEATHER_WORDS = ("neu", "neus", "nevada", "gel", "gelada", "glaç", "cadenes", "meteorològic", "meteorològica", "neige",
                 "verglas", "chaînes", "équipements spéciaux", "hivernal", "hivernals", "snow", "ice", "icy", "avalanche",
                 "allau", "allaus", "poorenvironmentconditions", "winterdrivingmanagement", "visibilitat", "boira", "brouillard")
_WEATHER_RE = re.compile(r"(?<![\w])(" + "|".join(re.escape(w) for w in WEATHER_WORDS) + r")(?![\w])", re.IGNORECASE)
CPI_REL_HIELO = 1.0             # tramo en cubeta: fondo de cuenca con índice ≥ el de Das (HIPÓTESIS)
MAX_ITEMS = 60


def _inside(lat: float, lon: float) -> bool:
    return BBOX[0] <= lat <= BBOX[1] and BBOX[2] <= lon <= BBOX[3]


def _local(tag: str) -> str:
    return tag.split("}")[-1]


def _is_meteo(txt: str) -> bool:
    return bool(_WEATHER_RE.search(txt or ""))


class FormatoDesconocido(ValueError):
    """El XML es válido pero no trae registros del tipo esperado: UNKNOWN, no «sin incidencias»."""


def parse_sct(raw: bytes) -> tuple[list[dict], dict]:
    root = ET.fromstring(raw)
    out, n, malos = [], 0, 0
    for fm in (e for e in root.iter() if _local(e.tag) == "featureMember"):
        n += 1
        d = {_local(e.tag): e.text.strip() for e in fm.iter() if e.text and e.text.strip()}
        try:
            lon, lat = map(float, d["coordinates"].split(",")[:2])
        except (KeyError, ValueError):
            malos += 1
            continue
        if not _inside(lat, lon):
            continue
        txt = " ".join(str(d.get(k, "")) for k in ("causa", "descripcio", "descripcio_tipus"))
        out.append({"fuente": "SCT", "carretera": d.get("carretera"), "pk": f"{d.get('pk_inici')}–{d.get('pk_fi')}",
                    "tipo": d.get("descripcio_tipus"), "causa": d.get("causa"), "texto": d.get("descripcio"),
                    "desde": d.get("data"), "lat": round(lat, 4), "lon": round(lon, 4), "meteo": _is_meteo(txt)})
    if n == 0:
        raise FormatoDesconocido("sin featureMember")
    return out, {"registros": n, "descartados_coordenadas": malos}


def parse_datex(raw: bytes) -> tuple[list[dict], dict]:
    root = ET.fromstring(raw)
    out, n, malos = [], 0, 0
    for rec in (e for e in root.iter() if _local(e.tag) == "situationRecord"):
        n += 1
        try:
            lats = [float(e.text) for e in rec.iter() if _local(e.tag) == "latitude" and e.text]
            lons = [float(e.text) for e in rec.iter() if _local(e.tag) == "longitude" and e.text]
        except ValueError:                      # un registro ilegible no tumba el feed
            malos += 1
            continue
        if not lats or len(lats) != len(lons):
            malos += 1
            continue
        pts = [(a, b) for a, b in zip(lats, lons) if _inside(a, b)]
        if not pts:
            continue
        vals = [e.text.strip() for e in rec.iter() if _local(e.tag) in ("value", "roadNumber") and e.text and e.text.strip()]
        kind = rec.get("{http://www.w3.org/2001/XMLSchema-instance}type", "")
        start = next((e.text for e in rec.iter() if _local(e.tag) == "overallStartTime"), None)
        road = next((e.text.strip() for e in rec.iter() if _local(e.tag) == "roadNumber" and e.text), None)
        out.append({"fuente": "Bison Futé / DIR Sud-Ouest", "carretera": road, "tipo": kind.split(":")[-1], "desde": start,
                    "texto": " | ".join(vals)[:300], "lat": round(pts[0][0], 4), "lon": round(pts[0][1], 4),
                    "meteo": _is_meteo(kind + " " + " ".join(vals))})
    if n == 0:
        raise FormatoDesconocido("sin situationRecord")
    return out, {"registros": n, "descartados_coordenadas": malos}


def estado_oficial(fetch) -> dict:
    """fetch(url) -> bytes. Cada fuente falla cerrada: error = UNKNOWN, nunca «sin incidencias»."""
    fuentes = {}
    feeds = (("sct", SCT_URL, parse_sct, "Servei Català de Trànsit"),
             ("bison_fute", BF_URL, parse_datex, "Bison Futé / DIR Sud-Ouest (RRN)"))

    def one(feed):
        key, url, parser, nombre = feed
        try:
            items, meta = parser(fetch(url))
        except Exception as exc:          # red caída, XML corrupto o formato nuevo: se informa, no se inventa
            return key, {"nombre": nombre, "estado": "UNKNOWN", "motivo": f"{type(exc).__name__}", "incidencias": None}
        items.sort(key=lambda i: (not i["meteo"], i.get("carretera") or ""))
        return key, {"nombre": nombre, "estado": "OK", "incidencias": items[:MAX_ITEMS], "total": len(items),
                     "meteo": sum(1 for i in items if i["meteo"]), **meta}
    with ThreadPoolExecutor(max_workers=len(feeds)) as ex:          # en paralelo: el peor caso es un timeout, no dos
        fuentes.update(dict(ex.map(one, feeds)))
    for key, (nombre, url) in SIN_FEED.items():
        fuentes[key] = {"nombre": nombre, "estado": "SIN_FEED", "enlace": url, "incidencias": None,
                        "motivo": "sin fuente abierta automática: consulta manual"}
    return {"nota": "estado oficial de las vías según cada servicio; UNKNOWN o SIN_FEED no significa vía libre",
            "fuentes": fuentes}


SECO = "sin_precipitacion"


def _cota_muestra(m: dict, cotas: dict):
    """Cota efectiva del punto de control más cercano (≤15 km), SECO si allí no hay precipitación en 24 h, o None."""
    best = None
    for c in cotas.values():
        if c.get("cota") is None and not c.get("sin_precipitacion"):
            continue
        d = math.hypot((m["lat"] - c["lat"]) * 111.3, (m["lon"] - c["lon"]) * 82.0)
        if best is None or d < best[0]:
            best = (d, c["cota"] if c.get("cota") is not None else SECO)
    return None if best is None or best[0] > 15 else best[1]


def exposicion(roads: dict, cotas: dict, puertos: dict | None = None, cpi_ref: float | None = None) -> dict:
    """Por carretera: km sobre la cota de copo efectiva mínima en 24 h, tramos en cubeta y puertos.

    cotas: {poi_id: {"lat", "lon", "cota"}} con la cota efectiva mínima en 24 h de cada punto de control
    (None = UNKNOWN). Una muestra sin punto de control a ≤15 km con cota conocida queda UNKNOWN.
    """
    out = {}
    for rid, r in roads.items():
        mm = r.get("muestras") or []
        if len(mm) < 2:
            continue
        seg = [max(0.0, b["km"] - a["km"]) for a, b in zip(mm, mm[1:])]
        km_total = sum(seg)
        km_nieve = km_unk = km_seco = 0.0
        for a, b, s in zip(mm, mm[1:], seg):
            c = _cota_muestra(a, cotas)
            if c is None:
                km_unk += s
            elif c == SECO:
                km_seco += s
            elif max(a["z"], b["z"]) >= c:
                km_nieve += s
        tramos, cur = [], None                      # muestras consecutivas en cubeta forman un tramo
        umbral = None if cpi_ref is None else CPI_REL_HIELO * cpi_ref
        for m in mm:
            if umbral is not None and m.get("cuenca") and (m.get("cpi") or 0) >= umbral:
                if cur:
                    cur[1] = m["km"]
                else:
                    cur = [m["km"], m["km"]]
                    tramos.append(cur)
            else:
                cur = None
        zmax = max(mm, key=lambda m: m["z"])
        out[rid] = {"nombre": r["nombre"], "pais": r["pais"], "km": round(km_total, 1),
                    "km_sobre_cota": None if km_unk >= km_total else round(km_nieve, 1),
                    "km_unknown": round(km_unk, 1), "km_sin_precipitacion": round(km_seco, 1), "z_max": zmax["z"],
                    "punto_alto": next((n for i, n in r.get("etiquetas", []) if abs(mm[i]["km"] - zmax["km"]) < 1.0), None),
                    "tramos_cubeta_km": None if umbral is None else [[round(a, 1), round(b, 1)] for a, b in tramos],
                    "km_fuera_de_cuenca": round(sum(s for a, s in zip(mm, seg) if not a.get("cuenca")), 1)}
    return {"nota": "exposición meteorológica estimada sobre un trazado aproximado; no es el estado de la vía ni un aviso. "
                    "km_sobre_cota solo mide nieve que cae: no cubre hielo, rehielo, ventisca ni nieve ya en el suelo. "
                    "Tramos en cubeta solo se evalúan en los fondos de cuenca (Cerdanya, Cerdagne, Capcir)",
            "carreteras": out, "puertos": puertos or {}}


def selftest() -> None:
    gml = (b'<?xml version="1.0"?><r xmlns:gml="http://www.opengis.net/gml"><gml:featureMember><i>'
           b'<carretera>N-260</carretera><causa>Neu</causa><descripcio>Cadenes obligat\xc3\xb2ries</descripcio>'
           b'<gml:coordinates>1.95,42.33</gml:coordinates></i></gml:featureMember><gml:featureMember><i>'
           b'<carretera>AP-7</carretera><gml:coordinates>2.9,41.5</gml:coordinates></i></gml:featureMember></r>')
    it, meta = parse_sct(gml)
    assert meta["registros"] == 2 and len(it) == 1 and it[0]["meteo"] and it[0]["carretera"] == "N-260"
    dx = (b'<d xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><situationRecord xsi:type="WinterDrivingManagement">'
          b'<latitude>42.56</latitude><longitude>1.82</longitude><roadNumber>N20</roadNumber></situationRecord></d>')
    assert not _is_meteo("Neutralisation de voie, service de police") and _is_meteo("Calçada amb gel")
    it, _ = parse_datex(dx)
    assert len(it) == 1 and it[0]["meteo"] and it[0]["carretera"] == "N20"

    def boom(url):
        raise OSError("red")
    st = estado_oficial(boom)
    assert st["fuentes"]["sct"]["estado"] == "UNKNOWN" and st["fuentes"]["sct"]["incidencias"] is None
    assert st["fuentes"]["andorra"]["estado"] == "SIN_FEED"
    st = estado_oficial(lambda url: b"<raiz><formatoNuevo/></raiz>")      # XML válido sin registros: UNKNOWN
    assert st["fuentes"]["sct"]["estado"] == "UNKNOWN" and st["fuentes"]["bison_fute"]["estado"] == "UNKNOWN"
    roads = {"x": {"nombre": "X", "pais": "CAT", "etiquetas": [[0, "A"], [2, "Puerto"]],
                   "muestras": [{"lat": 42.3, "lon": 1.9, "km": 0, "z": 1200, "cpi": 2.0, "cuenca": True},
                                {"lat": 42.3, "lon": 1.91, "km": 1, "z": 1600, "cpi": 0.2, "cuenca": True},
                                {"lat": 42.3, "lon": 1.92, "km": 2, "z": 1800, "cpi": 0.1, "cuenca": False}]}}
    e = exposicion(roads, {"p": {"lat": 42.3, "lon": 1.9, "cota": 1500}}, cpi_ref=2.0)["carreteras"]["x"]
    assert e["km_sobre_cota"] == 2.0 and e["tramos_cubeta_km"] == [[0.0, 0.0]] and e["punto_alto"] == "Puerto"   # tramo de una sola muestra
    e = exposicion(roads, {"p": {"lat": 42.3, "lon": 1.9, "cota": None}})["carreteras"]["x"]
    assert e["km_sobre_cota"] is None and e["km_unknown"] == 2.0 and e["tramos_cubeta_km"] is None
