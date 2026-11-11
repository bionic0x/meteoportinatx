#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []          # solo biblioteca estándar; netCDF4 opcional (rayos MTG-LI)
# ///
"""
PORTINATX DEGEN — vigilancia multifuente para Portinatx (39.1153 N, 1.5214 E)

Cada ciclo
  1. Recoge datos en vivo de todas las fuentes configuradas. Cada conector falla
     solo y declara su estado (ok / sin_clave / error / deshabilitado).
  2. Cada familia de datos pasa por un detector físico que devuelve nivel 0..3
     (quiet/watch/alert/alarm), confianza y evidencia literal.
  3. Tres estados separados en la salida:
       AVISO OFICIAL        nivel y vigencia exacta del aviso de AEMET (nunca lo
                            prolonga la histéresis)
       PELIGRO LOCAL        lluvia medida, radar (QPE con varias Z–R), rayos,
                            viento en estaciones, mar en boyas, escorrentía
                            observada; cada variable con estado OBSERVED / STALE
                            / UNKNOWN y distancia al punto
       PRECAUCIÓN OPERATIVA nivel recomendado, con histéresis y condiciones de
                            salida explícitas (no baja con escorrentía observada)
     Y la perspectiva PRÓXIMAS 36 h (avisos previstos + observación + modelos).
  4. Histéresis asimétrica: sube al instante; baja un escalón tras 3 ciclos.
     Con <2 canales observados vivos se declara COBERTURA INSUFICIENTE y no baja.
  5. Congela el ciclo (anti-hindsight) en cycles/NWC-<UTC>-<sha256>.json,
     nunca se sobrescribe, y lo añade a log.jsonl.

Reglas de fusión
  · El aviso de AEMET es SUELO: nunca se rebaja por debajo de él.
  · Un modelo determinista llega como mucho a 'alert'.
  · 'alarm' exige: aviso rojo; u observación en 'alarm'; u observación en
    'alert' confirmada por OTRA observación de grupo distinto (un modelo no
    confirma); o gate de alta resolución: ≥2 runs CONSECUTIVOS verificados de
    AROME HD / ICON-EU (sin runs intermedios sin ver) con ≥100 mm/12 h o
    ≥60 mm/6 h a ≤20 km, más una señal observada LOCAL: eco persistente a
    ≤25 km con cobertura ≥10 % a ≤30 km en 2 de 3 frames, rayos a ≤25 km o
    lluvia medida. Un eco lejano (≤60 km) solo da 'watch' y no abre el gate.

Tres ejes de alarma (cada snapshot los lleva por separado)
  · AVISO OFICIAL: lo que AEMET tiene vigente, tal cual, caduca con el CAP. Todos los
    vigentes se listan (terrestres y costeros). Un cambio de aviso produce banner,
    línea en alerts.jsonl y push opcional (NTFY_URL).
  · PELIGRO LOCAL OBSERVADO: por canal, OBSERVED/UNKNOWN; nunca 'quiet' sin dato.
  · PRECAUCIÓN OPERATIVA: propia; no prolonga el aviso oficial ni baja de él.

Gobernanza (marco Ante Agency Agents)
  · Afirmaciones tipadas EVIDENCE / HYPOTHESIS / ASSUMPTION / UNKNOWN con raíz de
    fuente, alcance y caducidad. Un modelo o una estimación nunca es EVIDENCE.
  · Dos canales con la misma raíz no se confirman (METAR LEIB y lluvia AEMET).
    'alarm' por confirmación exige además que una de las dos señales sea local.
  · Estaciones a >25 km (LEIB, puertos): precursoras, techo 'alert'.
  · Bajar la precaución es una DECISIÓN: PROCEED o HOLD con condiciones nombradas
    (suelo oficial = FATAL_DEFECT, sin override). Desde alert/alarm el retador veta
    la bajada sin pluviómetro vecino fresco que la confirme: dBZ bajo ≠ lluvia baja.
  · Radar mudo a ≤30 km con lluvia medida cerca → hueco de cobertura, radar UNKNOWN.
  · Disenso (--dissent/--respond): el abierto impide bajar a quiet y cerrar.
  · Predicciones falsables congeladas (sha); una bajada refutada abre anomalía que
    retiene hasta --review-anomaly. Sesgo radar–pluviómetro: se mide y se avisa,
    la relación Z–R no cambia sola.
  · Episodio: ACTIVE → CESSATION / TRANSITION → CLOSURE_PROPOSED → CLOSED solo con
    --close-episode del propietario (el motor no se auto-acepta).

Detectores
  · Lluvia observada 1/3/12 h. El significado de 'prec' de AEMET (hora previa
    o acumulado) se lee de los metadatos de la respuesta; acumulado → diferencias;
    sin confirmar → techo 'watch'; cadencia exigida 45–90 min.
  · Frente de racha: racha con racha, medio con medio; puerta dura de presión
    (calibración de 51 días de v1.2.1) y caída de Td como discriminante.
  · Radar: teselas RainViewer decodificadas a dBZ con la tabla oficial Universal
    Blue. QPE en el punto con Marshall–Palmer y con la relación tropical, ambas
    con su rango: ninguna se impone. El radar solo llega a 'alert' (≥45 dBZ a
    ≤15 km o QPE ≥20 mm/h en 2 de 3 frames); el rojo exige otra observación.
  · Pluviómetros: red Meteoclimatic (feed XML documentado) con coordenadas de
    núcleo, distancia, frescura e intensidad por diferencia entre ciclos. Una
    estación lejana nunca se atribuye a Portinatx; un dato viejo es STALE, no 0.
  · Mar y viento: boyas y estaciones de Puertos del Estado (PORTUS, sin clave).
  · Escorrentía/anegamiento observados a mano (--obs runoff=observed): validez
    6 h; mientras duren, la precaución operativa no desescala.
  · Ensemble: control + miembros identificados por nombre, ventanas completas,
    en el punto y en la vecindad (±17 km) por separado; <10 miembros → no opina.
  · Núcleo convectivo: rejilla 0,15° por run (hora de inicio vía meta.json),
    distancia a Portinatx, desplazamiento entre runs y runs centrados seguidos.
  · Escorrentía: B908X es un proxy fuera de la cuenca; techo 'watch' salvo
    CATCHMENT_VERIFIED=1. Mar: Hs del sector abierto de la bahía (provisional).
  · Estación casera: QC de retraso, valores imposibles y valores congelados.

Fuentes y estado: `python3 portinatx_degen.py catalog`.

Uso
  python3 portinatx_degen.py run                      # un ciclo
  python3 portinatx_degen.py watch --interval 300     # vigilancia
  python3 portinatx_degen.py --floor naranja run      # aviso verificado a mano (sin clave)
  python3 portinatx_degen.py inspect-cap avisos.xml --at 2026-10-18T07:00:00Z
  python3 portinatx_degen.py radar-colors | static | climo | catalog | selftest
  python3 portinatx_degen.py --obs runoff=observed run           # observación del propietario
  python3 portinatx_degen.py --dissent "sigue lloviendo en la cala" run
  python3 portinatx_degen.py --respond D1=REFUTED:"medido 0 mm" run
  python3 portinatx_degen.py --override CHALLENGER_VETO="pluviómetro propio 0 mm" run
  python3 portinatx_degen.py --review-anomaly A1="revisado: célula local" run
  python3 portinatx_degen.py --close-episode run

Entorno: NTFY_URL (push en cambio de aviso), AEMET_API_KEY, WU_API_KEY, SOCIB_BUOY_URL, EUMETSAT_KEY,
EUMETSAT_SECRET, CATCHMENT_VERIFIED, PORTINATX_HOME (directorio de estado).

Presupuesto Open-Meteo (10 000 llamadas/día; cada punto cuenta): punto y
vecindad cada 15 min, ensemble y oleaje cada 60 min, rejilla solo con run
nuevo; ante 429 se sirve la última respuesta buena, marcada.

Limitaciones
  · Umbrales de partida, NO calibrados ni equivalentes a Meteoalerta. Recalibrar
    el detector de frente de racha con la serie de 51 días antes de fiarse.
  · RainViewer no da dBZ. El ensemble a 0,25° es una cota inferior en convección.
  · Oleaje modelizado offshore; no representa la rompiente de la cala.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import os
import struct
import sys
import tarfile
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import re
import xml.etree.ElementTree as ET
import zlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any, Callable

VERSION = "0.6.1"
UTC = timezone.utc


class EuropeanMadrid(tzinfo):
    """Respaldo CET/CEST para fechas modernas (regla UE vigente desde 1996).

    Cambio a las 01 UTC del último domingo de marzo/octubre. Respeta fold
    durante la hora repetida; no pretende reproducir la historia anterior a 1996.
    """
    @staticmethod
    def _last_sunday(year: int, month: int) -> datetime:
        d = datetime(year, month, 31)
        return d - timedelta(days=(d.weekday() + 1) % 7)

    def dst(self, dt):
        if dt is None:
            return timedelta(0)
        wall = dt.replace(tzinfo=None)
        start = self._last_sunday(dt.year, 3).replace(hour=2)
        end = self._last_sunday(dt.year, 10).replace(hour=2)
        if start <= wall < start + timedelta(hours=1):
            summer = bool(dt.fold)                 # hora inexistente: semántica PEP 495
        elif end <= wall < end + timedelta(hours=1):
            summer = not dt.fold                   # primera/segunda aparición de las 02
        else:
            summer = start + timedelta(hours=1) <= wall < end
        return timedelta(hours=int(summer))

    def utcoffset(self, dt):
        return timedelta(hours=1) + self.dst(dt)

    def tzname(self, dt):
        return "CEST" if self.dst(dt) else "CET"

    def fromutc(self, dt):
        if dt.tzinfo is not self:
            raise ValueError("fromutc exige este huso")
        u = dt.replace(tzinfo=None)
        start = self._last_sunday(dt.year, 3).replace(hour=1)
        end = self._last_sunday(dt.year, 10).replace(hour=1)
        summer = start <= u < end
        fold = end <= u < end + timedelta(hours=1)
        return (u + timedelta(hours=2 if summer else 1)).replace(tzinfo=self, fold=int(fold))


try:
    from zoneinfo import ZoneInfo
    MADRID = ZoneInfo("Europe/Madrid")
except (ImportError, KeyError):                        # Windows sin tzdata
    MADRID = EuropeanMadrid()


def before_utc_daily_reset(t: datetime) -> bool:
    """Entre medianoche local y 00 UTC (01 CET / 02 CEST), incluso el día de cambio."""
    return t.astimezone(UTC).date() < t.astimezone(MADRID).date()

# ════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ════════════════════════════════════════════════════════════════════════
SITE = {"name": "Portinatx", "lat": 39.1153, "lon": 1.5214}

CFG: dict[str, Any] = {
    "metar_ids": ["LEIB", "LEPA", "LEVC", "LEAL", "LEMH", "LECH"],
    "dem_box": (38.62, 39.16, 1.15, 1.66), "dem_res": 0.005,          # relieve de Ibiza (IGN, ~500 m)
    "bathy_box": (39.06, 39.22, 1.42, 1.64), "bathy_res": 0.002,      # norte de Ibiza (EMODnet, ~200 m)
    "stencil_deg": 0.25,                                               # malla para divergencia y vorticidad
    "aemet_stations": {"B908X": "Sant Joan de Labritja", "B954": "Ibiza Aeropuerto"},
    # Área CAP de AEMET. 'esp' = toda España (seguro, más pesado). ⚠ El código
    # autonómico de Baleares no está verificado; cámbialo si lo confirmas.
    "aemet_cap_area": "esp",
    "aemet_zone": "645301",
    "emma_id": "ES113",                     # misma zona en MeteoAlarm (verificado 17/10/2026)
    "wu_station": "ISANTJ159",
    # Vecindad para modelos: punto + 4 desplazamientos (~15–17 km). El error de
    # posición de la convección a +24/48 h es de ese orden: se mira el máximo.
    "neighborhood": [(0.0, 0.0), (0.15, 0.0), (-0.15, 0.0), (0.0, 0.2), (0.0, -0.2),
                     (0.0, 0.35), (-0.15, 0.25)],      # +2 al E/SE: la DANA descargó al E del máximo modelizado
    "det_models": ["meteofrance_arome_france_hd", "ecmwf_ifs025", "icon_eu"],
    "ai_models": ["ecmwf_aifs025_single", "ncep_aigfs025"],    # IA: verificación y comparación; no abren la precaución
    "tide_gauge": "Mareógrafo Ibiza 2",
    "ens_model": "ecmwf_ifs025",
    "marine_point": (39.145, 1.525),          # frente a la bocana, mar abierto al N
    "bay_open_sector": (290.0, 60.0),         # de dónde viene el mar que entra (grados)
    "radar_zoom": 7,
    "radar_radius_km": 80.0,
    "radar_frames": 7,                         # ~1 h a 10 min
    # Tabla oficial RainViewer «Universal Blue» (rainviewer_api_colors_table.csv), lluvia 5–65 dBZ.
    "radar_dbz_table": {5: "928871", 6: "9e9375", 7: "aa9e79", 8: "b6a97e", 9: "c2b482", 10: "cec087",
        11: "d2c48b", 12: "d6c88f", 13: "dacc93", 14: "ded097", 15: "88ddee", 16: "6cd1eb", 17: "51c5e8",
        18: "36bae5", 19: "1baee2", 20: "00a3e0", 21: "009ad5", 22: "0091ca", 23: "0088bf", 24: "007fb4",
        25: "0077aa", 26: "0070a3", 27: "00699c", 28: "006295", 29: "005b8e", 30: "005588", 31: "005180",
        32: "004e78", 33: "004a70", 34: "004768", 35: "ffee00", 36: "ffe000", 37: "ffd200", 38: "ffc500",
        39: "ffb700", 40: "ffaa00", 41: "ff9f00", 42: "ff9500", 43: "ff8b00", 44: "ff8100", 45: "ff4400",
        46: "f23600", 47: "e62800", 48: "d91b00", 49: "cd0d00", 50: "c10000", 51: "a80000", 52: "8f0000",
        53: "760000", 54: "5d0000", 55: "ffaaff", 56: "ff9fff", 57: "ff95ff", 58: "ff8bff", 59: "ff81ff",
        60: "ff77ff", 61: "ff6cff", 62: "ff62ff", 63: "ff58ff", 64: "ff4eff", 65: "ffffff"},
    # Relaciones Z = a·R^b. Se calculan TODAS; ninguna es la «verdadera» sin validar con pluviómetro.
    "zr": {"marshall_palmer": (200.0, 1.6), "tropical": (250.0, 1.2)},
    "qpe_radius_km": 3.0,
    "radar_alert_dbz": 45.0, "radar_alert_km": 15.0, "radar_alert_qpe": 20.0,
    # #17: UNA relación Z–R decide el umbral de QPE; la otra solo se muestra como diagnóstico.
    # Marshall–Palmer es la coherente con 45 dBZ ≈ 24 mm/h ≥ radar_alert_qpe; con la «tropical»
    # el umbral saltaba ya hacia 40 dBZ.
    "radar_threshold_zr": "marshall_palmer",
    # Meteoclimatic (feed XML regional). Coordenadas de núcleo urbano (aprox.), no de la estación.
    "mc_feed": "https://www.meteoclimatic.net/feed/xml/ESIBA",
    "mc_stations": {
        "ESIBA0700000207815B": ("Sant Miquel de Balansat", 39.085, 1.443),
        "ESIBA0700000207812A": ("Sant Llorenç de Balafia", 39.044, 1.487),
        "ESIBA0700000207840A": ("Santa Eulària des Riu", 38.985, 1.535),
        "ESIBA0700000207816A": ("Sant Mateu d'Albarca", 39.045, 1.370),
        "ESIBA0700000207816B": ("Sant Rafel de sa Creu", 38.966, 1.386),
        "ESIBA0700000207800A": ("Eivissa", 38.910, 1.430),
        "ESIBA0700000207820A": ("Sant Antoni de Portmany", 38.980, 1.303),
        "ESIBA0700000207817A": ("Sant Jordi de ses Salines", 38.880, 1.410),
        "ESIBA0700000207829B": ("Sant Agustí des Vedrà", 38.925, 1.300),
        "ESIBA0700000207829A": ("Cala de Bou", 38.960, 1.270),
        "ESIBA0700000207839A": ("Cala Jondal", 38.865, 1.330)},
    "gauge_near_km": 12.0,
    # Suelo saturado (antecedente de ayer + hoy ≥ sat_mm en la estación): umbrales de intensidad y de
    # acumulado más bajos. Calibrado con 2 observaciones del propietario en Portinatx (18 y 19/10:
    # escorrentía con ~20–30 mm/h y 40–80 mm en el día): HIPÓTESIS de n=2, revisar.
    "sat_mm": 60.0, "rain_1h_wet": (10.0, 20.0, 40.0), "rain_day_wet": (30.0, 45.0, 120.0),                     # «vecina»: indicio para Portinatx, nunca medida en Portinatx
    "gauge_stale_min": 45,
    # PORTUS (Puertos del Estado): boyas de mar abierto y estaciones de puerto/mareógrafo.
    "portus_base": "https://portus.puertos.es/portussvr/api",
    "portus_buoys": {2720: "Boya Tarragona", 2630: "Boya Valencia", 2820: "Boya Dragonera"},
    "portus_wind": {4815: "Puerto de Ibiza", 4814: "Puerto de Formentera", 3856: "Mareógrafo Ibiza 2",
                    4802: "Boya canal de Ibiza (meteo)"},
    "sea_hs": (1.5, 2.5, 4.0),                 # Hs (m) en boyas con mar del sector N–E
    "manual_obs_ttl_h": 6,
    "socib_buoy_url": os.environ.get("SOCIB_BUOY_URL", ""),   # ⚠ pega la de v1.2.1
    # Umbrales de lluvia (mm) ≈ escalones Meteoalerta Pitiusas. ⚠ verificar plan vigente: los valores oficiales están
    # en los Anexos 1/2 del plan (no obtenidos). Procedencia de cada umbral: knowledge_base.THRESHOLD_PROVENANCE.
    "rain_1h": (20.0, 40.0, 60.0),
    "rain_12h": (60.0, 100.0, 180.0),
    "runoff_antecedent_mm": 40.0,
    # Detector de frente de racha (ventana 30–90 min; hourly = 2 h)
    "gf": {"dT_watch": -2.0, "dT_strong": -4.0, "dP_watch": 0.8, "dP_strong": 1.5,
           "dU_watch": 15.0, "dU_strong": 30.0, "dTd_watch": -1.0, "dTd_strong": -2.0,
           "gust_watch": 60.0, "gust_strong": 80.0},
    "ens_thresholds": {"p24_50": (0.2, 0.4), "p12_100": (0.1, 0.25), "p1_30": (0.15, 0.3)},
    "wave_hs": (1.5, 2.5, 3.5),               # m, solo cuenta si entra por el sector abierto
    "gust_model": (60.0, 80.0, 100.0),        # km/h racha modelizada
    "deescalate_cycles": 3,
    "lookahead_h": 36,
    "cap_lookahead_h": 72,                  # listado CAP; la decisión operativa mantiene 36 h
    # Rejilla 0,1° para seguir el núcleo convectivo run a run.
    # 13×19 = 247 celdas a 0,15°. Presupuesto: ~16 runs/día × 247 ≈ 4000 llamadas;
    # el cupo gratuito de Open-Meteo es 10 000/día y cuenta CADA punto (429 si se pasa).
    "grid_lat": (38.4, 40.2), "grid_lon": (0.0, 2.7), "grid_step": 0.15,
    "grid_models": ["meteofrance_arome_france_hd", "icon_eu"],
    "grid_ttl_min": 60,
    "gate_models": ["meteofrance_arome_france_hd", "icon_eu"],   # alta resolución para el gate rojo
    "meta_name": {"icon_eu": "dwd_icon_eu"},                     # nombre en /data/<m>/static/meta.json
    "centered_radius_km": 20.0,
    "centered_12h": 100.0, "centered_6h": 60.0,
    "run_interval_h": {"meteofrance_arome_france_hd": 3, "icon_eu": 3},   # cadencia de runs
    "local_obs_km": 25.0, "local_cover_30km": 0.10,   # señal observada local para el gate rojo
    "rain_3h": (30.0, 50.0, 80.0),
    "pws_stale_min": 30,
    "min_obs_channels": 2,
    # Frescura (#16): edad máxima del dato más reciente de cada canal, en minutos (de partida, sin
    # calibrar). Sin hora de dato, o más viejo que el límite → UNKNOWN (available=False), nunca 0.
    # El eje oficial (aviso_aemet*) no pasa por aquí: se consulta cada ciclo y caduca con el CAP.
    "channel_max_age_min": {"lluvia_observada": 90, "pluviometros": 45, "escorrentia_torrentes": 120,
                            "frente_racha": 150, "radar": 30, "rayos": 20, "viento_estaciones": 60,
                            "mar_boyas": 120, "modelo": 360, "ensemble_ecmwf": 720, "mar_bahia": 360,
                            "trayectoria_nucleo": 720},
    # Familias de fenómeno que deben tener ≥1 canal observado vivo para declarar cobertura suficiente.
    "required_families": ("lluvia",),
    # Distancia (km) de estaciones puntuales a Portinatx: más allá de local_obs_km son precursoras,
    # no medida local (DANA 18/10: el frente de racha de LEIB/puerto se debilitó hacia el norte).
    "station_km": {"B908X": 4.5, "B954": 29.0, "LEIB": 29.0, "ISANTJ159": 6.0},
    "far_obs_cap": 2,                          # techo de una observación puntual no local
    # Gobernanza (marco Ante): caducidades, predicciones falsables, sesgo radar–pluviómetro
    "override_ttl_h": 3,
    "pred_window_min": 60, "pred_rise_rate": 5.0, "pred_rise_mm": 2.0, "pred_cease_mm": 1.0,
    "pred_grace_min": 60,
    "pred_tol_min": 20,                        # lectura válida: ±20 min del cierre de la ventana (−10/+20)
    "bias_min_n": 4, "bias_hi": 2.0, "bias_lo": 0.5,
    "coverage_gap_rate": 1.0,                  # mm/h medidos con radar mudo a ≤30 km → hueco
    "anomaly_hold_h": 6,
    # Aplicación en tiempo real (serve / export-app)
    "radar_grid": {"dlat": 1.45, "dlon": 1.95, "step": 0.025, "frames": 6},
    "portus_coords": {"Boya Tarragona": (40.69, 1.47), "Boya Valencia": (39.51, 0.20),
                      "Boya Dragonera": (39.563, 2.097), "Puerto de Ibiza": (38.904, 1.447),
                      "Puerto de Formentera": (38.735, 1.419), "Mareógrafo Ibiza 2": (38.911, 1.450),
                      "Boya canal de Ibiza (meteo)": (38.824, 0.784)},
    "app_port": 8787, "app_history": 288,
}

APP_MODE = bool(getattr(sys, "frozen", False)) or sys.argv[0].endswith(".pyz")   # ejecutable empaquetado
HOME = Path(os.environ.get("PORTINATX_HOME") or
            (Path.home() / "PortinatxNowcast" if APP_MODE else Path.cwd() / "portinatx_state"))


def resource_bytes(name: str) -> bytes:
    """Recurso empaquetado: junto al script, dentro del ejecutable (PyInstaller) o dentro del .pyz."""
    for base in (Path(__file__).parent, Path(getattr(sys, "_MEIPASS", "") or "/nonexistent")):
        f = base / name
        if f.exists():
            return f.read_bytes()
    import pkgutil
    data = pkgutil.get_data(__name__ if __name__ != "__main__" else "portinatx_degen", name)
    if data is None:
        raise FileNotFoundError(name)
    return data
LEVELS = ("quiet", "watch", "alert", "alarm")
EMOJI = {"quiet": "🟢", "watch": "🟡", "alert": "🟠", "alarm": "🔴"}
WARN_RANK = {"verde": 0, "green": 0, "amarillo": 1, "yellow": 1, "naranja": 2,
             "orange": 2, "rojo": 3, "red": 3}
UA = f"portinatx-degen/{VERSION} (personal research nowcast)"


# ════════════════════════════════════════════════════════════════════════
# UTILIDADES
# ════════════════════════════════════════════════════════════════════════
def now_utc() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def http_get(url: str, *, timeout: float = 25.0, headers: dict | None = None,
             data: bytes | None = None, retries: int = 2) -> bytes:
    h = {"User-Agent": UA, "Accept-Encoding": "gzip"}
    if headers:
        h.update(headers)
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=h, data=data)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
                    try:
                        raw = gzip.decompress(raw)
                    except OSError:
                        pass
                return raw
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last = exc
            if attempt < retries:
                time.sleep(3.0 * (attempt + 1))
    raise RuntimeError(f"GET falló ({url.split('?')[0]}): {last}")


def get_json(url: str, **kw) -> Any:
    raw = http_get(url, **kw)
    for enc in ("utf-8", "latin-1"):
        try:
            return json.loads(raw.decode(enc))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise RuntimeError("respuesta no JSON")


def parse_time(s: str | int | float | None) -> datetime | None:
    if s is None or s == "":
        return None
    if isinstance(s, (int, float)):
        return datetime.fromtimestamp(float(s), UTC)
    s = str(s).strip().replace("Z", "+00:00")
    if len(s) >= 5 and (s[-5] in "+-") and s[-3] != ":":   # +0000 → +00:00
        s = s[:-2] + ":" + s[-2:]
    for fmt in (None, "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.fromisoformat(s) if fmt is None else datetime.strptime(s, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def fnum(x: Any) -> float | None:
    try:
        v = float(x)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


def in_sector(deg: float, sector: tuple[float, float]) -> bool:
    a, b = sector
    deg %= 360
    return a <= deg <= b if a <= b else (deg >= a or deg <= b)


def level_from(value: float | None, thr: tuple[float, ...], *, reverse: bool = False) -> int:
    """thr = (watch, alert, alarm) — devuelve 0..3."""
    if value is None:
        return 0
    lvl = 0
    for i, t in enumerate(thr, start=1):
        if (value <= t) if reverse else (value >= t):
            lvl = i
    return lvl


# ════════════════════════════════════════════════════════════════════════
# MODELO DE DATOS
# ════════════════════════════════════════════════════════════════════════
@dataclass
class SourceResult:
    name: str
    status: str = "pending"            # ok | sin_clave | error | deshabilitado
    kind: str = "obs"                  # obs | model | ensemble | institutional
    fetched_at: str = ""
    data_time: str = ""                # hora del dato más reciente
    detail: str = ""
    payload: Any = None


@dataclass
class Channel:
    name: str
    level: int = 0
    kind: str = "obs"                  # obs | model | ensemble | institutional
    confidence: str = "baja"
    evidence: list[str] = field(default_factory=list)
    available: bool = True
    group: str = ""                    # canales del mismo grupo NO se confirman entre sí
    local: bool = False                # señal observada cerca del punto (abre el gate rojo de modelo)
    metrics: dict = field(default_factory=dict)   # cifras para gobernanza (sin texto)
    data_time: str | None = None       # hora (ISO) del dato más reciente usado; None = no verificable

    def __post_init__(self):
        self.group = self.group or self.name


@dataclass
class Point:                          # muestra de estación para detectores
    t: datetime
    T: float | None = None
    Td: float | None = None
    P: float | None = None
    U: float | None = None             # viento medio km/h
    G: float | None = None             # racha km/h
    D: float | None = None             # dirección
    R1: float | None = None            # lluvia en la última hora (mm)
    RR: float | None = None            # intensidad instantánea (mm/h)


def run_source(name: str, kind: str, fn: Callable[[], SourceResult]) -> SourceResult:
    try:
        res = fn()
    except Exception as exc:                       # cada conector cae solo
        res = SourceResult(name=name, kind=kind, status="error",
                           detail=f"{type(exc).__name__}: {exc}"[:300])
    res.name, res.kind = name, kind
    res.fetched_at = now_utc().isoformat()
    return res


# ════════════════════════════════════════════════════════════════════════
# CONECTORES
# ════════════════════════════════════════════════════════════════════════
def src_metar() -> SourceResult:
    ids = ",".join(CFG["metar_ids"])
    data = get_json(f"https://aviationweather.gov/api/data/metar?ids={ids}&format=json&hours=24")
    series: dict[str, list[Point]] = {}
    wx: dict[str, list[str]] = {}
    meta: dict[str, dict] = {}
    for ob in data or []:
        icao = ob.get("icaoId")
        t = parse_time(ob.get("reportTime") or ob.get("obsTime"))
        if not icao or not t:
            continue
        kt = 1.852
        series.setdefault(icao, []).append(Point(
            t=t, T=fnum(ob.get("temp")), Td=fnum(ob.get("dewp")), P=fnum(ob.get("altim")),
            U=(fnum(ob.get("wspd")) or 0) * kt if fnum(ob.get("wspd")) is not None else None,
            G=(fnum(ob.get("wgst")) * kt) if fnum(ob.get("wgst")) is not None else None,
            D=fnum(ob.get("wdir"))))
        wx.setdefault(icao, []).append(f"{t:%H%MZ} {ob.get('rawOb', '')}")
        if parse_time((meta.get(icao) or {}).get("last")) and parse_time(meta[icao]["last"]) >= t:
            continue                                   # se queda el parte más reciente
        meta.setdefault(icao, {}).update({"lat": fnum(ob.get("lat")), "lon": fnum(ob.get("lon")),
                                          "name": ob.get("name", ""), "elev": fnum(ob.get("elev")),
                                          "last": t.isoformat(), "raw": ob.get("rawOb", ""),
                                          "visib": ob.get("visib"), "cover": ob.get("cover", "")})
    for v in series.values():
        v.sort(key=lambda p: p.t)
    for v in wx.values():
        v.sort()                                   # "HHMMZ ..." → orden cronológico
    latest = max((p.t for v in series.values() for p in v), default=None)
    return SourceResult(name="metar", status="ok" if series else "error",
                        data_time=latest.isoformat() if latest else "",
                        detail=f"{sum(len(v) for v in series.values())} partes",
                        payload={"series": series, "raw": wx, "meta": meta})


def _aemet(path: str, *, with_meta: bool = False) -> Any:
    key = os.environ.get("AEMET_API_KEY")
    if not key:
        raise PermissionError("sin AEMET_API_KEY")
    meta = get_json("https://opendata.aemet.es/opendata" + urllib.parse.quote(path, safe="/"),
                    headers={"api_key": key, "Accept": "application/json"})
    if int(meta.get("estado", 0)) != 200 or not meta.get("datos"):
        raise RuntimeError(f"AEMET estado={meta.get('estado')} {meta.get('descripcion')}")
    data = http_get(meta["datos"], headers={"api_key": key})
    return (data, meta.get("metadatos", "")) if with_meta else data


def _decode(raw: bytes) -> Any:
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return json.loads(raw.decode(enc))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise RuntimeError("JSON AEMET ilegible")


def aemet_prec_mode(meta_url: str) -> tuple[str, str]:
    """Lee la definición oficial del campo 'prec' en los metadatos de la propia respuesta.
    hourly = lluvia de la hora previa; cumulative = acumulado desde una hora fija; unknown."""
    forced = os.environ.get("AEMET_PREC_MODE", "").lower()
    if forced in ("hourly", "cumulative"):
        return forced, "forzado por AEMET_PREC_MODE"
    if not meta_url:
        return "unknown", "sin URL de metadatos"
    try:
        m = _decode(http_get(meta_url, headers={"api_key": os.environ.get("AEMET_API_KEY", "")}))
        campos = m.get("campos", []) if isinstance(m, dict) else []
        desc = next((c.get("descripcion", "") for c in campos if c.get("id") == "prec"), "")
    except Exception as exc:
        return "unknown", f"metadatos ilegibles: {exc}"
    d = desc.lower()
    if "60 minutos" in d or "hora anterior" in d or "última hora" in d or "ultima hora" in d:
        return "hourly", f"metadatos AEMET: «{desc[:90]}»"
    if "desde las" in d or "del día" in d or "del dia" in d:
        return "cumulative", f"metadatos AEMET: «{desc[:90]}»"
    return "unknown", f"definición no reconocida: «{desc[:90]}»"


def aemet_rows_to_points(rows: list[dict], mode: str) -> list[Point]:
    """R1 = lluvia de la hora previa, SOLO si se puede derivar con garantías:
    hourly → valor tal cual con cadencia 45–90 min; cumulative → diferencia dentro del
    mismo día; unknown → valor tal cual pero el canal lo marca y limita."""
    rows = sorted((r for r in rows if parse_time(r.get("fint"))), key=lambda r: parse_time(r["fint"]))
    out, prev = [], None
    for r in rows:
        t = parse_time(r["fint"])
        prec = fnum(r.get("prec"))
        rain = None
        if prec is not None and prec >= 0:
            if mode == "cumulative":
                if prev and prev[0].date() == t.date() and prev[1] is not None and prec >= prev[1] \
                        and (t - prev[0]) <= timedelta(minutes=90):
                    rain = prec - prev[1]
            elif prev is None or timedelta(minutes=45) <= (t - prev[0]) <= timedelta(minutes=90):
                rain = prec
        prev = (t, prec)
        vv, vmax = fnum(r.get("vv")), fnum(r.get("vmax"))
        out.append(Point(t=t, T=fnum(r.get("ta")), Td=fnum(r.get("tpr")), P=fnum(r.get("pres")),
                         U=vv * 3.6 if vv is not None else None,
                         G=vmax * 3.6 if vmax is not None else None,
                         D=fnum(r.get("dv")), R1=rain))
    return out


def src_aemet_obs() -> SourceResult:
    if not os.environ.get("AEMET_API_KEY"):
        return SourceResult(name="aemet_obs", status="sin_clave",
                            detail="exporta AEMET_API_KEY (gratuita en opendata.aemet.es)")
    out: dict[str, list[Point]] = {}
    errors, mode, why = [], "unknown", ""
    for idema in CFG["aemet_stations"]:
        try:
            raw, meta_url = _aemet(f"/api/observacion/convencional/datos/estacion/{idema}", with_meta=True)
            if mode == "unknown":
                mode, why = aemet_prec_mode(meta_url)
            out[idema] = aemet_rows_to_points(_decode(raw), mode)
        except Exception as exc:
            errors.append(f"{idema}: {exc}")
    latest = max((p.t for v in out.values() for p in v), default=None)
    return SourceResult(name="aemet_obs", status="ok" if out else "error",
                        data_time=latest.isoformat() if latest else "",
                        detail=f"prec={mode} ({why}); " + ("; ".join(errors) or f"{len(out)} estaciones"),
                        payload={"series": out, "prec_mode": mode})


def parse_cap_documents(blobs: list[bytes], zone: str, now: datetime,
                        lookahead_h: int) -> list[dict]:
    """Extrae los avisos CAP de la zona. Devuelve lista de {nivel, rank, onset, expires, ...}."""
    ns = {"c": "urn:oasis:names:tc:emergency:cap:1.2"}
    found = []
    horizon = now + timedelta(hours=lookahead_h)
    for blob in blobs:
        try:
            root = ET.fromstring(blob)
        except ET.ParseError:
            continue
        if (root.findtext("c:status", "Actual", ns) or "Actual") != "Actual":
            continue                                   # ejercicios y pruebas fuera
        if root.findtext("c:msgType", "", ns) == "Cancel":
            continue
        ident = root.findtext("c:identifier", "", ns) or ""
        sent = root.findtext("c:sent", "", ns) or ""
        mtype = root.findtext("c:msgType", "", ns) or ""
        for info in root.findall("c:info", ns):
            lang = (info.findtext("c:language", "", ns) or "").lower()
            if lang and not lang.startswith("es"):
                continue
            params = {p.findtext("c:valueName", "", ns): p.findtext("c:value", "", ns)
                      for p in info.findall("c:parameter", ns)}
            nivel = (params.get("AEMET-Meteoalerta nivel") or "").lower()
            if not nivel:
                # Formato MeteoAlarm (reemisión del CAP de AEMET, verificado 17/10/2026):
                # awareness_level = "3; orange; Severe", zona como EMMA_ID ES113.
                aw = (params.get("awareness_level") or "").split(";")
                nivel = {"yellow": "amarillo", "orange": "naranja", "red": "rojo",
                         "green": "verde"}.get(aw[1].strip().lower() if len(aw) > 1 else "", "")
            onset = parse_time(info.findtext("c:onset", None, ns))
            expires = parse_time(info.findtext("c:expires", None, ns))
            for area in info.findall("c:area", ns):
                codes = [g.findtext("c:value", "", ns) for g in area.findall("c:geocode", ns)]
                if not (zone in codes or CFG["emma_id"] in codes or f".{zone}" in ident):
                    continue
                if expires and expires < now:
                    continue
                if onset and onset > horizon:
                    continue
                adesc = area.findtext("c:areaDesc", "", ns) or ""
                coastal = "COCO" in ident or adesc.lower().startswith("costa") or \
                    "costero" in (info.findtext("c:event", "", ns) or "").lower()
                found.append({
                    "id": ident, "sent": sent, "msg_type": mtype,
                    "tipo": "costero" if coastal else "terrestre", "area": adesc,
                    "nivel": nivel, "rank": WARN_RANK.get(nivel, 0),
                    "evento": info.findtext("c:event", "", ns),
                    "onset": onset.isoformat() if onset else "",
                    "expires": expires.isoformat() if expires else "",
                    "activo_ahora": bool(onset and onset <= now and (not expires or expires >= now)),
                    "parametro": params.get("AEMET-Meteoalerta parametro", ""),
                    "probabilidad": params.get("AEMET-Meteoalerta probabilidad", ""),
                    "descripcion": (info.findtext("c:description", "", ns) or "")[:240],
                })
    return found


def src_aemet_cap() -> SourceResult:
    if not os.environ.get("AEMET_API_KEY"):
        return SourceResult(name="aemet_cap", status="sin_clave",
                            detail="exporta AEMET_API_KEY")
    raw = _aemet(f"/api/avisos_cap/ultimoelaborado/area/{CFG['aemet_cap_area']}")
    blobs: list[bytes] = []
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as tf:
            for m in tf.getmembers():
                if m.isfile() and m.name.lower().endswith(".xml"):
                    f = tf.extractfile(m)
                    if f:
                        blobs.append(f.read())
    except tarfile.TarError:
        blobs = [raw]                              # a veces llega un único XML
    warns = parse_cap_documents(blobs, CFG["aemet_zone"], now_utc(), CFG["cap_lookahead_h"])
    return SourceResult(name="aemet_cap", status="ok", data_time=now_utc().isoformat(),
                        detail=f"{len(blobs)} CAP leídos, {len(warns)} en zona {CFG['aemet_zone']}",
                        payload={"warnings": warns})


def src_meteoalarm() -> SourceResult:
    """Respaldo SIN CLAVE de los avisos (MeteoAlarm reemite los CAP de AEMET).
    Verificado 16/10/2026: el feed solo cubre hoy y mañana (no D+2)."""
    txt = http_get("https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-spain").decode("utf-8", "replace")
    now = now_utc()
    horizon = now + timedelta(hours=CFG["lookahead_h"])
    color = {"yellow": "amarillo", "orange": "naranja", "red": "rojo"}
    warns = []
    for e in txt.split("<entry>")[1:]:
        area = _tag(e, "cap:areaDesc")
        if not any(k in area.lower() for k in ("ibiza", "eivissa", "formentera")):
            continue
        title = _tag(e, "title")
        lv = next((v for k, v in color.items() if title.lower().startswith(k)), "")
        onset, exp = parse_time(_tag(e, "cap:onset")), parse_time(_tag(e, "cap:expires"))
        if (exp and exp < now) or (onset and onset > horizon):
            continue
        # El CAP completo trae el umbral ("Precipitación acumulada en una hora: 50 mm").
        cap_url = ""
        marker = 'type="application/cap+xml" href="'
        k = e.find(marker)
        if k >= 0:
            cap_url = e[k + len(marker):e.find('"', k + len(marker))]
        full = []
        if cap_url:
            try:
                full = parse_cap_documents([http_get(cap_url)], CFG["aemet_zone"], now, CFG["lookahead_h"])
            except Exception:
                full = []
        if full:
            warns.extend(full)
            continue
        warns.append({"nivel": lv, "rank": WARN_RANK.get(lv, 0), "evento": _tag(e, "cap:event"),
                      "onset": onset.isoformat() if onset else "", "expires": exp.isoformat() if exp else "",
                      "activo_ahora": bool(onset and onset <= now and (not exp or exp >= now)),
                      "parametro": area, "probabilidad": _tag(e, "cap:certainty"), "descripcion": title})
    return SourceResult(name="meteoalarm", status="ok", kind="institutional",
                        data_time=now.isoformat(), detail=f"{len(warns)} avisos Pitiusas (cubre D y D+1)",
                        payload={"warnings": warns})


def _tag(s: str, tag: str) -> str:
    a = s.find(f"<{tag}>")
    if a < 0:
        return ""
    b = s.find(f"</{tag}>", a)
    return s[a + len(tag) + 2:b].strip()


def src_wu() -> SourceResult:
    key = os.environ.get("WU_API_KEY")
    if not key:
        return SourceResult(name="wu_pws", status="sin_clave",
                            detail="WU solo da clave a quien sube datos de una PWS propia")
    st = CFG["wu_station"]
    base = "https://api.weather.com/v2/pws/observations"
    data = get_json(f"{base}/all/1day?stationId={st}&format=json&units=m&numericPrecision=decimal&apiKey={key}")
    pts = []
    for ob in data.get("observations", []):
        m = ob.get("metric", {})
        pts.append(Point(t=parse_time(ob.get("obsTimeUtc")),
                         T=fnum(m.get("tempAvg")), Td=fnum(m.get("dewptAvg")),
                         P=fnum(m.get("pressureMax")), U=fnum(m.get("windspeedAvg")),
                         G=fnum(m.get("windgustHigh")), D=fnum(ob.get("winddirAvg")),
                         RR=fnum(m.get("precipRate"))))
    pts = [p for p in pts if p.t]
    cur = get_json(f"{base}/current?stationId={st}&format=json&units=m&numericPrecision=decimal&apiKey={key}")
    c = (cur.get("observations") or [{}])[0]
    cm = c.get("metric", {})
    pts.append(Point(t=parse_time(c.get("obsTimeUtc")) or now_utc(), T=fnum(cm.get("temp")),
                     Td=fnum(cm.get("dewpt")), P=fnum(cm.get("pressure")),
                     U=fnum(cm.get("windSpeed")), G=fnum(cm.get("windGust")),
                     D=fnum(c.get("winddir")), RR=fnum(cm.get("precipRate"))))
    pts.sort(key=lambda p: p.t)
    return SourceResult(name="wu_pws", status="ok", data_time=pts[-1].t.isoformat(),
                        detail=f"{st}: {len(pts)} muestras, total hoy {cm.get('precipTotal')} mm",
                        payload={"series": {st: pts}, "precip_total": fnum(cm.get("precipTotal"))})


def src_socib() -> SourceResult:
    url = CFG["socib_buoy_url"]
    if not url:
        return SourceResult(name="socib_boya", status="deshabilitado",
                            detail="define SOCIB_BUOY_URL (URL OPeNDAP .ascii de v1.2.1)")
    txt = http_get(url).decode("utf-8", "replace")
    # Lector genérico de OPeNDAP ASCII: bloques "VAR[n]" seguidos de valores.
    blocks: dict[str, list[float]] = {}
    cur = None
    for line in txt.splitlines():
        line = line.strip()
        if not line:
            continue
        head = line.split(",")[0]
        if "[" in head and not head[0].isdigit() and not head.startswith("["):
            cur = head.split("[")[0].split(".")[-1]
            blocks[cur] = []
            rest = line.split(",")[1:]
        else:
            rest = line.split(",")
            if rest and rest[0].startswith("["):
                rest = rest[1:]
        if cur:
            blocks[cur].extend(v for v in (fnum(x) for x in rest) if v is not None)
    tkey = next((k for k in blocks if k.lower() == "time"), None)
    if not tkey:
        raise RuntimeError("OPeNDAP sin variable time")
    def col(*names):
        for n in names:
            if n in blocks:
                return blocks[n]
        return []
    T, Td, P = col("AIR_TEM"), col("DEW_POI"), col("AIR_PRE")
    U, G, D = col("WIN_SPE"), col("WIN_GUS", "WIN_SPE_MAX"), col("WIN_DIR")
    pts = []
    for i, ts in enumerate(blocks[tkey]):
        g = lambda arr, k=1.0: (arr[i] * k) if i < len(arr) else None
        pts.append(Point(t=datetime.fromtimestamp(ts, UTC), T=g(T), Td=g(Td), P=g(P),
                         U=g(U, 3.6), G=g(G, 3.6), D=g(D)))
    pts.sort(key=lambda p: p.t)
    return SourceResult(name="socib_boya", status="ok", data_time=pts[-1].t.isoformat(),
                        detail=f"{len(pts)} muestras", payload={"series": {"boya_canal": pts[-60:]}})


def _om_multi(base: str, params: dict, points: list[tuple[float, float]]) -> list[dict]:
    q = dict(params)
    q["latitude"] = ",".join(f"{p[0]:.4f}" for p in points)
    q["longitude"] = ",".join(f"{p[1]:.4f}" for p in points)
    q["timezone"] = "UTC"
    data = get_json(f"{base}?{urllib.parse.urlencode(q)}")
    return data if isinstance(data, list) else [data]


def src_openmeteo_det() -> SourceResult:
    pts = [(SITE["lat"] + a, SITE["lon"] + b) for a, b in CFG["neighborhood"]]
    res = _om_multi("https://api.open-meteo.com/v1/forecast", {
        "hourly": "precipitation,wind_gusts_10m,wind_direction_10m,cape,pressure_msl",
        "models": ",".join(CFG["det_models"]), "forecast_hours": 48}, pts)
    out: dict[str, dict] = {}
    for m in CFG["det_models"]:
        per_pt = []
        for loc in res:
            h = loc.get("hourly", {})
            def series(var):
                return h.get(f"{var}_{m}") or (h.get(var) if len(CFG["det_models"]) == 1 else None) or []
            per_pt.append({"time": h.get("time", []), "pr": series("precipitation"),
                           "gust": series("wind_gusts_10m"), "dir": series("wind_direction_10m"),
                           "cape": series("cape")})
        out[m] = per_pt
    return SourceResult(name="openmeteo_det", status="ok", kind="model",
                        data_time=now_utc().isoformat(), detail=f"{len(pts)} puntos × {len(out)} modelos",
                        payload=out)


def src_openmeteo_ens() -> SourceResult:
    """Miembros en el punto Y en la vecindad: separa 'llueve en algún sitio cerca'
    de 'llueve en Portinatx' (un miembro con 100 mm a 17 km no es un acierto en el punto)."""
    pts = [(SITE["lat"] + a, SITE["lon"] + b) for a, b in CFG["neighborhood"]]
    res = _om_multi("https://ensemble-api.open-meteo.com/v1/ensemble", {
        "hourly": "precipitation", "models": CFG["ens_model"], "forecast_hours": 72}, pts)
    per_pt = []
    import re
    pat = re.compile(r"precipitation(_member\d+)?")           # control + miembros, nada más
    for loc in res:
        h = loc.get("hourly", {})
        nt = len(h.get("time", []))
        keys = sorted(k for k in h if pat.fullmatch(k) and isinstance(h[k], list) and len(h[k]) == nt)
        per_pt.append([h[k] for k in keys])
    n = len(per_pt[0]) if per_pt else 0
    return SourceResult(name="openmeteo_ens", status="ok" if n else "error", kind="ensemble",
                        data_time=now_utc().isoformat(), detail=f"{n} miembros × {len(per_pt)} puntos",
                        payload={"members": per_pt[0] if per_pt else [], "per_point": per_pt})


def model_run_init(model: str) -> str:
    name = CFG["meta_name"].get(model, model)
    try:
        meta = get_json(f"https://api.open-meteo.com/data/{name}/static/meta.json", timeout=15)
        return datetime.fromtimestamp(meta["last_run_initialisation_time"], UTC).isoformat()
    except Exception:
        return ""


def src_model_grid() -> SourceResult:
    """Rejilla regional: dónde está el núcleo de cada modelo y a qué distancia de Portinatx."""
    la0, la1 = CFG["grid_lat"]; lo0, lo1 = CFG["grid_lon"]; st = CFG["grid_step"]
    lats = [round(la0 + st * i, 3) for i in range(int(round((la1 - la0) / st)) + 1)]
    lons = [round(lo0 + st * j, 3) for j in range(int(round((lo1 - lo0) / st)) + 1)]
    cells = [(a, b) for a in lats for b in lons]
    out, errs, reused = {}, [], []
    cache = _cache_load("grid")
    for m in CFG["grid_models"]:
        init = model_run_init(m)
        hit = cache.get(m)
        # Solo se pide la rejilla si hay run nuevo (o, sin metadatos, cada grid_ttl_min).
        if hit and ((init and hit.get("init") == init) or
                    (not init and _age_min(hit.get("fetched")) < CFG["grid_ttl_min"])):
            out[m] = hit
            reused.append(m)
            continue
        try:
            res = []                                   # lotes de 200: la URL tiene límite (HTTP 414)
            for i in range(0, len(cells), 200):
                res += _om_multi("https://api.open-meteo.com/v1/forecast",
                                 {"hourly": "precipitation", "models": m, "forecast_hours": 48},
                                 cells[i:i + 200])
            ser = [r.get("hourly", {}).get("precipitation") or [] for r in res]
            out[m] = summarize_grid(cells, ser)
            out[m]["cells"] = cells                     # campo explícito por ventanas para el mapa
            out[m]["win"] = {w: [round(sum((x or 0) for x in pr[a:b]), 1) for pr in ser]
                             for w, (a, b) in {"0-6": (0, 6), "6-12": (6, 12), "12-24": (12, 24), "24-48": (24, 48)}.items()}
            out[m]["init"] = init
            out[m]["fetched"] = now_utc().isoformat()
            cache[m] = out[m]
        except Exception as exc:
            errs.append(f"{m}: {exc}")
            if hit:                                    # mejor un run viejo marcado que nada
                out[m] = {**hit, "stale": True}
    _cache_save("grid", cache)
    det = f"{len(cells)} celdas × {len(out)} modelos" + (f" (reutilizados sin run nuevo: {', '.join(reused)})" if reused else "")
    return SourceResult(name="model_grid", status="ok" if out else "error", kind="model",
                        data_time=now_utc().isoformat(),
                        detail="; ".join(errs + [det]), payload=out)


# ── caché en disco: el cupo gratuito de Open-Meteo cuenta cada punto como una llamada ──
def _cache_path(name: str) -> Path:
    return HOME / "cache" / f"{name}.json"


def _cache_load(name: str) -> dict:
    try:
        return json.loads(_cache_path(name).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _cache_save(name: str, obj: dict) -> None:
    p = _cache_path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, default=str))
    tmp.replace(p)


def _age_min(iso: str | None) -> float:
    t = parse_time(iso) if iso else None
    return (now_utc() - t).total_seconds() / 60 if t else 1e9


# Freshness of *measurements*, not cache requests. These provisional ceilings follow
# the existing channel limits; they are NOT calibrated provider SLAs.
OBS_SOURCE_MAX_AGE_MIN = {"portus": 120, "radar_hf": 90}
PORTUS_METRIC_MAX_AGE_MIN = {"wave": 120, "wind": 60, "sea_level": 120}
PORTUS_METRIC_FIELDS = {
    "wave": ("hm0", "hmax"),
    "wind": ("vv_mx", "vv_md"),
    "sea_level": ("nivel", "nivelMedio"),
}


def observation_recency(timestamp: str | None, limit_min: float,
                        now: datetime | None = None) -> dict:
    """Judge an actual measurement UTC instant, never fetched_at or cache TTL.

    Unzoned timestamps are ambiguous across DST and must stay UNKNOWN.
    A future measurement beyond 10 min is STALE, not a fresh observation.
    """
    if not isinstance(timestamp, str) or not timestamp:
        return {"freshness": "UNKNOWN", "age_min": None}
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return {"freshness": "UNKNOWN", "age_min": None}
    if dt.tzinfo is None:
        return {"freshness": "UNKNOWN", "age_min": None}
    age = ((now or now_utc()).astimezone(UTC) - dt.astimezone(UTC)).total_seconds() / 60
    return {"freshness": "FRESH" if -10 <= age <= limit_min else "STALE",
            "age_min": round(age, 1)}


def marine_source_recency(src: SourceResult, now: datetime | None = None) -> dict:
    """Public-safe freshness labels for HF current and PORTUS variable families."""
    limit = OBS_SOURCE_MAX_AGE_MIN.get(src.name)
    if limit is None:
        return {}
    summary = (observation_recency(src.data_time, limit, now) if src.status == "ok"
               else {"freshness": "UNKNOWN", "age_min": None})
    summary["limit_min"] = limit
    if src.name == "portus":
        station_series = ((src.payload or {}).get("stations", {})
                          if src.status == "ok" and isinstance(src.payload, dict) else {})
        metrics = {}
        for metric, cols in PORTUS_METRIC_FIELDS.items():
            statuses = []
            for rows in station_series.values():
                if not isinstance(rows, list):
                    continue
                for row in rows:
                    if isinstance(row, dict) and any(
                        isinstance(row.get(col), (int, float)) and not isinstance(row.get(col), bool)
                        and math.isfinite(row[col]) for col in cols
                    ):
                        statuses.append(observation_recency(
                            row.get("t"), PORTUS_METRIC_MAX_AGE_MIN[metric], now)["freshness"])
            metrics[metric] = ("FRESH" if "FRESH" in statuses else
                               "STALE" if "STALE" in statuses else "UNKNOWN")
        summary["metrics_freshness"] = metrics
    return summary


def cached_source(name: str, ttl_min: float, fn: Callable[[], SourceResult]) -> Callable[[], SourceResult]:
    """Envuelve un conector de modelo: reutiliza la última respuesta mientras sea fresca;
    si la API falla (p. ej. 429), sirve la última buena marcada como 'caché'."""
    def wrapped() -> SourceResult:
        c = _cache_load(name)
        if c and _age_min(c.get("fetched")) < ttl_min:
            return SourceResult(name=name, status="ok", kind=c["kind"], data_time=c["data_time"],
                                detail=c["detail"] + f" (caché {_age_min(c['fetched']):.0f} min)",
                                payload=c["payload"])
        try:
            r = fn()
            if r.status == "ok":
                _cache_save(name, {"fetched": now_utc().isoformat(), "kind": r.kind,
                                   "data_time": r.data_time, "detail": r.detail, "payload": r.payload})
            return r
        except Exception as exc:
            if c and _age_min(c.get("fetched")) > max(6 * ttl_min, 180):
                raise RuntimeError(f"API falló ({type(exc).__name__}) y la caché tiene {_age_min(c['fetched']):.0f} min: "
                                   "demasiado vieja para presentarla como actual") from exc
            if c:
                return SourceResult(name=name, status="ok", kind=c["kind"], data_time=c["data_time"],
                                    detail=f"API falló ({type(exc).__name__}); se usa caché de "
                                           f"{_age_min(c['fetched']):.0f} min", payload=c["payload"])
            raise
    return wrapped


def summarize_grid(cells: list[tuple[float, float]], series: list[list[float]]) -> dict:
    R = CFG["centered_radius_km"]
    best = (-1.0, None)
    loc12 = loc6 = loc1 = 0.0
    n100 = 0
    for (la, lo), pr in zip(cells, series):
        if not pr:
            continue
        r12, r6, r1 = _rolling_max(pr, 12), _rolling_max(pr, 6), max((x or 0) for x in pr)
        if r12 > best[0]:
            best = (r12, (la, lo))
        n100 += r12 >= 100
        if haversine_km(SITE["lat"], SITE["lon"], la, lo) <= R:
            loc12, loc6, loc1 = max(loc12, r12), max(loc6, r6), max(loc1, r1)
    mx, (bla, blo) = best[0], best[1] or (None, None)
    return {"max12": mx, "max_lat": bla, "max_lon": blo,
            "max_dist_km": haversine_km(SITE["lat"], SITE["lon"], bla, blo) if bla is not None else None,
            "local12": loc12, "local6": loc6, "local1": loc1, "cells_ge100_12h": n100}


def update_run_tracks(state: dict, grid: dict) -> dict:
    """Historial por run (no por ciclo): desplazamiento del núcleo y runs consecutivos centrados."""
    tracks = state.setdefault("runs", {})
    out = {}
    for m, g in grid.items():
        hist = tracks.setdefault(m, [])
        key = g.get("init")
        rec = {k: g[k] for k in ("max12", "max_lat", "max_lon", "max_dist_km", "local12", "local6",
                                 "local1", "cells_ge100_12h")}
        if not key:
            # Sin hora de inicio verificable (meta.json caído) el run NO se registra: inventar una
            # clave por hora fabricaba «runs» que podían encadenarse en el gate rojo.
            rec["centered"] = bool(g["local12"] >= CFG["centered_12h"] or g["local6"] >= CFG["centered_6h"])
            out[m] = {**rec, "init": None, "unverified_run": True, "displacement_km": None,
                      "centered_consecutive": 0, "prev_dist_km": hist[-1]["max_dist_km"] if hist else None}
            continue
        rec["init"] = key
        rec["centered"] = bool(g["local12"] >= CFG["centered_12h"] or g["local6"] >= CFG["centered_6h"])
        if hist and hist[-1]["init"] == key:
            hist[-1] = rec                    # mismo run: se refresca, no cuenta doble
        else:
            hist.append(rec)
        del hist[:-8]
        disp = None
        if len(hist) >= 2 and hist[-2]["max_lat"] is not None and rec["max_lat"] is not None:
            disp = haversine_km(hist[-2]["max_lat"], hist[-2]["max_lon"], rec["max_lat"], rec["max_lon"])
        # Solo cuentan runs CONSECUTIVOS verificados: si entre dos runs vistos falta
        # uno intermedio (no consultado), la cadena se corta: no se sabe qué decía.
        step = CFG["run_interval_h"].get(m)
        consec, newer = 0, None
        for h in reversed(hist):
            if not h["centered"]:
                break
            if newer is not None and step:
                try:
                    gap = (datetime.fromisoformat(newer["init"]) - datetime.fromisoformat(h["init"])).total_seconds() / 3600
                except ValueError:
                    break
                if gap > step + 0.1:
                    break
            consec += 1
            newer = h
        out[m] = {**rec, "displacement_km": disp, "centered_consecutive": consec,
                  "prev_dist_km": hist[-2]["max_dist_km"] if len(hist) >= 2 else None}
    return out


def src_marine() -> SourceResult:
    lat, lon = CFG["marine_point"]
    res = _om_multi("https://marine-api.open-meteo.com/v1/marine", {
        "hourly": "wave_height,wave_direction,wave_period", "forecast_hours": 72}, [(lat, lon)])
    h = res[0].get("hourly", {})
    return SourceResult(name="marine", status="ok", kind="model", data_time=now_utc().isoformat(),
                        detail="oleaje Open-Meteo Marine", payload=h)


# ── Meteoclimatic (pluviómetros, feed XML regional) ───────────────────
def parse_meteoclimatic(xml: str, now: datetime) -> list[dict]:
    """Estaciones conocidas del feed → {id, nombre, lat, lon, dist_km, t, edad_min, lluvia_dia, T, viento}."""
    from email.utils import parsedate_to_datetime
    out = []
    for blk in re.findall(r"<station>(.*?)</station>", xml, re.S):
        sid = (re.search(r"<id>(.*?)</id>", blk) or [None, ""])[1]
        if sid not in CFG["mc_stations"]:
            continue
        name, lat, lon = CFG["mc_stations"][sid]
        try:
            t = parsedate_to_datetime(re.search(r"<pubDate>(.*?)</pubDate>", blk).group(1)).astimezone(UTC)
        except Exception:
            continue
        def sub(block, key):
            b = re.search(rf"<{block}>(.*?)</{block}>", blk, re.S)
            m = re.search(rf"<{key}>(.*?)</{key}>", b.group(1)) if b else None
            return fnum(m.group(1)) if m else None
        out.append({"id": sid, "nombre": name, "lat": lat, "lon": lon,
                    "dist_km": haversine_km(SITE["lat"], SITE["lon"], lat, lon),
                    "t": t.isoformat(), "edad_min": (now - t).total_seconds() / 60,
                    "lluvia_dia": sub("rain", "total"), "T": sub("temperature", "now"),
                    "viento": sub("wind", "now"), "racha_dia": sub("wind", "max")})
    return out


def src_meteoclimatic() -> SourceResult:
    xml = http_get(CFG["mc_feed"], headers={"User-Agent": "Mozilla/5.0"}).decode("iso-8859-15", "replace")
    st = parse_meteoclimatic(xml, now_utc())
    if not st:
        raise RuntimeError("feed sin estaciones conocidas de Ibiza")
    newest = max(s["t"] for s in st)
    return SourceResult(name="meteoclimatic", status="ok", data_time=newest,
                        detail=f"{len(st)} estaciones de Ibiza (lluvia diaria desde 00 h local)",
                        payload={"stations": st})


# ── PORTUS · Puertos del Estado (boyas y estaciones costeras, sin clave) ─
def _portus_post(path: str, body: list) -> Any:
    raw = http_get(CFG["portus_base"] + path, data=json.dumps(body).encode(), timeout=40, retries=1,
                   headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json",
                            "Origin": "https://portus.puertos.es", "Referer": "https://portus.puertos.es/"})
    return json.loads(raw) if raw else None


def _portus_series(sid: int, vtypes: list[str]) -> list[dict]:
    ids = []
    for v in vtypes:
        try:
            d = _portus_post(f"/lastData/station/{sid}?locale=es", [v])
        except Exception:
            continue                                   # la estación no mide ese tipo de variable
        for prm in (d or {}).get("datos", []):
            if prm.get("nombreColumna") not in ("lat", "lon"):
                ids.append(prm["id"])
    if not ids:
        return []
    rows = {}
    for rec in _portus_post(f"/RTData/station/{sid}?locale=es", sorted(set(ids))) or []:
        t = parse_time(rec["fecha"][:19].replace(" ", "T") + "+00:00")       # PORTUS da UTC
        r = rows.setdefault(t, {"t": t.isoformat()})
        for prm in rec["datos"]:
            try:
                val = float(prm["valor"]) / float(prm["factor"] or 1)
            except (TypeError, ValueError):
                continue
            col = prm["nombreColumna"]
            r[col] = max(r.get(col, val), val) if col in ("vv_mx", "hmax", "vv_md") else val   # 2 anemómetros → máx
    return [rows[k] for k in sorted(rows)]


def src_portus() -> SourceResult:
    out, errs, refs = {}, [], {}
    ref_cols = ("nivelMedio", "nivelCeroHidrog", "cotaElipsoidal", "ceroGeoNacional")
    for sid, name in {**CFG["portus_buoys"], **CFG["portus_wind"]}.items():
        try:
            tide = name == CFG["tide_gauge"]
            vt = (["WAVE", "WIND", "WATER_TEMP", "CURRENTS"] if sid in CFG["portus_buoys"]
                  else ["WIND", "SEA_LEVEL"] if tide else ["WIND"])
            if tide:                                   # PORTUS no mezcla viento y nivel en una consulta
                merged: dict[str, dict] = {}
                for v in vt:
                    for r in _portus_series(sid, [v]):
                        merged.setdefault(r["t"], {}).update(r)
                ser = [merged[k] for k in sorted(merged)]
            else:
                ser = _portus_series(sid, vt)
            if tide and ser:
                last_lvl = next((r for r in reversed(ser) if r.get("nivelMedio") is not None), {})
                refs[name] = {k: last_lvl[k] for k in ref_cols if last_lvl.get(k) is not None}
                ser = [{k: v for k, v in r.items() if k not in ref_cols} for r in thin_rows(ser, 10)]
            if ser:
                out[name] = ser[-36:] if sid in CFG["portus_buoys"] else ser[-150:] if tide else ser[-90:]
        except Exception as exc:
            errs.append(f"{name}: {type(exc).__name__}")
    if not out:
        raise RuntimeError("PORTUS sin datos: " + "; ".join(errs))
    newest = max(v[-1]["t"] for v in out.values())
    return SourceResult(name="portus", status="ok", data_time=newest,
                        detail=f"{len(out)} estaciones" + (f" · fallos: {', '.join(errs)}" if errs else ""),
                        payload={"stations": out, "refs": refs})


# ── RainViewer + decodificador PNG (stdlib) ────────────────────────────
_PNG_MEMO: dict[str, tuple] = {}


def png_decode(blob: bytes) -> tuple[int, int, list[tuple[int, int, int, int]]]:
    key = hashlib.sha1(blob).hexdigest()
    hit = _PNG_MEMO.get(key)
    if hit is None:
        hit = _png_decode(blob)
        if len(_PNG_MEMO) > 200:
            _PNG_MEMO.clear()
        _PNG_MEMO[key] = hit
    return hit


def _png_decode(blob: bytes) -> tuple[int, int, list[tuple[int, int, int, int]]]:
    if blob[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("no es PNG")
    pos, idat, plte, trns = 8, b"", None, None
    w = h = depth = ctype = interlace = 0
    while pos < len(blob):
        ln = struct.unpack(">I", blob[pos:pos + 4])[0]
        typ = blob[pos + 4:pos + 8]
        chunk = blob[pos + 8:pos + 8 + ln]
        pos += 12 + ln
        if typ == b"IHDR":
            w, h, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", chunk)
        elif typ == b"PLTE":
            plte = [tuple(chunk[i:i + 3]) for i in range(0, len(chunk), 3)]
        elif typ == b"tRNS":
            trns = list(chunk)
        elif typ == b"IDAT":
            idat += chunk
        elif typ == b"IEND":
            break
    if depth != 8 or interlace:
        raise ValueError(f"PNG no soportado (depth={depth}, interlace={interlace})")
    bpp = {6: 4, 2: 3, 3: 1, 0: 1, 4: 2}[ctype]
    raw = zlib.decompress(idat)
    stride = w * bpp
    prev = bytearray(stride)
    pixels: list[tuple[int, int, int, int]] = []
    i = 0
    for _ in range(h):
        f = raw[i]; i += 1
        line = bytearray(raw[i:i + stride]); i += stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + ((a + b) >> 1)) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        for x in range(w):
            px = line[x * bpp:(x + 1) * bpp]
            if ctype == 6:
                pixels.append((px[0], px[1], px[2], px[3]))
            elif ctype == 2:
                pixels.append((px[0], px[1], px[2], 255))
            elif ctype == 3:
                r, g, b_ = plte[px[0]] if plte else (0, 0, 0)
                alpha = trns[px[0]] if trns and px[0] < len(trns) else 255
                pixels.append((r, g, b_, alpha))
            elif ctype == 0:
                pixels.append((px[0], px[0], px[0], 255))
            else:
                pixels.append((px[0], px[0], px[0], px[1]))
        prev = line
    return w, h, pixels


def _tile_xy(lat: float, lon: float, z: int) -> tuple[float, float]:
    n = 2 ** z
    x = (lon + 180.0) / 360.0 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def _xy_latlon(x: float, y: float, z: int) -> tuple[float, float]:
    n = 2 ** z
    lon = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lat, lon


_DBZ_RGB = None
_DBZ_CACHE: dict[tuple[int, int, int], float | None] = {}


def color_to_dbz(r: int, g: int, b: int) -> float | None:
    """Color Universal Blue → dBZ (vecino más próximo en RGB; None si no es de la escala)."""
    global _DBZ_RGB
    if _DBZ_RGB is None:
        _DBZ_RGB = [(dbz, tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)))
                    for dbz, h in CFG["radar_dbz_table"].items()]
    key = (r, g, b)
    if key not in _DBZ_CACHE:
        best = min(_DBZ_RGB, key=lambda e: (e[1][0] - r) ** 2 + (e[1][1] - g) ** 2 + (e[1][2] - b) ** 2)
        dist = sum((best[1][i] - key[i]) ** 2 for i in range(3))
        _DBZ_CACHE[key] = float(best[0]) if dist <= 300 else None
    return _DBZ_CACHE[key]


def zr_rate(dbz: float | None, a: float, b: float) -> float:
    """Z = a·R^b → R (mm/h). Por debajo de 15 dBZ se toma 0; se capa en 55 dBZ (posible granizo)."""
    if dbz is None or dbz < 15:
        return 0.0
    z = 10 ** (min(dbz, 55.0) / 10)
    return (z / a) ** (1 / b)


def radar_frame_metrics(tiles: dict[tuple[int, int], bytes], z: int, palette: dict | None = None) -> dict:
    lat0, lon0 = SITE["lat"], SITE["lon"]
    R = CFG["radar_radius_km"]
    rings = {10: [0, 0], 30: [0, 0], 60: [0, 0]}
    nearest, nearest_strong = None, None
    colors: dict[str, int] = {}
    max30 = max15 = 0.0
    qpe = {k: 0.0 for k in CFG["zr"]}
    nsite = 0
    site_max = 0.0
    for (tx, ty), blob in tiles.items():
        w, h, px = png_decode(blob)
        for idx, (r, g, b, a) in enumerate(px):
            yy, xx = divmod(idx, w)
            lat, lon = _xy_latlon(tx + (xx + 0.5) / w, ty + (yy + 0.5) / h, z)
            d = haversine_km(lat0, lon0, lat, lon)
            if d > R:
                continue
            echo = a > 0
            for k in rings:
                if d <= k:
                    rings[k][1] += 1
                    rings[k][0] += int(echo)
            dbz = color_to_dbz(r, g, b) if echo else None
            if d <= CFG["qpe_radius_km"]:
                nsite += 1
                site_max = max(site_max, dbz or 0.0)
                for k, (za, zb) in CFG["zr"].items():
                    qpe[k] += zr_rate(dbz, za, zb)
            if not echo:
                continue
            hexc = f"#{r:02x}{g:02x}{b:02x}"
            colors[hexc] = colors.get(hexc, 0) + 1
            nearest = d if nearest is None else min(nearest, d)
            if dbz is not None:
                if d <= 30:
                    max30 = max(max30, dbz)
                if d <= CFG["radar_alert_km"]:
                    max15 = max(max15, dbz)
                if dbz >= CFG["radar_alert_dbz"]:
                    nearest_strong = d if nearest_strong is None else min(nearest_strong, d)
    cls = 5 if max30 >= 50 else 4 if max30 >= 45 else 3 if max30 >= 35 else 2 if max30 >= 25 else 1 if max30 else 0
    return {"cover": {k: (v[0] / v[1] if v[1] else 0.0) for k, v in rings.items()},
            "nearest_km": nearest, "nearest_strong_km": nearest_strong,
            "max_dbz_30km": max30, "max_dbz_15km": max15, "site_max_dbz": site_max,
            "qpe_site_mmh": {k: (v / nsite if nsite else 0.0) for k, v in qpe.items()},
            "max_class_30km": cls, "colors": colors}


def radar_grid(tiles: dict[tuple[int, int], bytes], z: int) -> str:
    """Rejilla lat/lon de dBZ alrededor de Portinatx (fila 0 = norte), 1 byte por celda:
    0 sin eco · 1 eco de color no tabulado · 5–65 dBZ. Codificada en base64."""
    import base64
    rg = CFG["radar_grid"]
    st = rg["step"]
    nlat = int(round(2 * rg["dlat"] / st)) + 1
    nlon = int(round(2 * rg["dlon"] / st)) + 1
    dec = {k: png_decode(v) for k, v in tiles.items()}
    out = bytearray(nlat * nlon)
    for i in range(nlat):
        lat = SITE["lat"] + rg["dlat"] - i * st
        for j in range(nlon):
            lon = SITE["lon"] - rg["dlon"] + j * st
            x, y = _tile_xy(lat, lon, z)
            t = dec.get((int(x), int(y)))
            if not t:
                continue
            w, h, px = t
            r, g, b, a = px[min(h - 1, int((y % 1) * h)) * w + min(w - 1, int((x % 1) * w))]
            if a:
                d = color_to_dbz(r, g, b)
                out[i * nlon + j] = 1 if d is None else max(2, min(255, int(round(d))))
    return base64.b64encode(bytes(out)).decode()


def src_radar() -> SourceResult:
    maps = get_json("https://api.rainviewer.com/public/weather-maps.json")
    host = maps.get("host", "https://tilecache.rainviewer.com")
    frames = (maps.get("radar", {}).get("past") or [])[-CFG["radar_frames"]:]
    z = CFG["radar_zoom"]
    # teselas que cubren el radio de vigilancia
    rg = CFG["radar_grid"]
    dlat, dlon = rg["dlat"], rg["dlon"]               # teselas que cubren la rejilla de la app (⊃ radio de métricas)
    xs, ys = set(), set()
    for la in (SITE["lat"] - dlat, SITE["lat"] + dlat):
        for lo in (SITE["lon"] - dlon, SITE["lon"] + dlon):
            x, y = _tile_xy(la, lo, z)
            xs.add(int(x)); ys.add(int(y))
    tiles_xy = [(x, y) for x in range(min(xs), max(xs) + 1) for y in range(min(ys), max(ys) + 1)]
    out = []
    seen_hash = set()
    for fr in frames:
        tiles = {}
        for (x, y) in tiles_xy:
            url = f"{host}{fr['path']}/256/{z}/{x}/{y}/2/0_0.png"
            tiles[(x, y)] = http_get(url)
        hsh = hashlib.sha1(b"".join(tiles[k] for k in sorted(tiles))).hexdigest()
        m = radar_frame_metrics(tiles, z)
        m["grid"] = radar_grid(tiles, z)
        m["time"] = datetime.fromtimestamp(fr["time"], UTC).isoformat()
        m["dup"] = hsh in seen_hash
        seen_hash.add(hsh)
        out.append(m)
    if not out:
        raise RuntimeError("sin frames de radar")
    return SourceResult(name="radar", status="ok", data_time=out[-1]["time"],
                        detail=f"{len(out)} frames, {len(tiles_xy)} teselas z{z} · dBZ decodificados (Universal Blue)",
                        payload={"frames": out})


def src_lightning() -> SourceResult:
    key, sec = os.environ.get("EUMETSAT_KEY"), os.environ.get("EUMETSAT_SECRET")
    if not (key and sec):
        return SourceResult(name="rayos_mtg_li", status="sin_clave",
                            detail="EUMETSAT_KEY/SECRET (cuenta gratuita, Data Store) — experimental")
    try:
        import netCDF4  # noqa: F401
    except ImportError:
        return SourceResult(name="rayos_mtg_li", status="deshabilitado",
                            detail="pip install netCDF4 para leer MTG-LI")
    import base64, zipfile, tempfile, netCDF4
    tok = json.loads(http_get("https://api.eumetsat.int/token", data=b"grant_type=client_credentials",
                              headers={"Authorization": "Basic " + base64.b64encode(f"{key}:{sec}".encode()).decode()}))
    auth = {"Authorization": f"Bearer {tok['access_token']}"}
    end = now_utc(); start = end - timedelta(minutes=40)
    q = urllib.parse.urlencode({"format": "json", "pi": "EO:EUM:DAT:0691", "si": 0, "c": 6,
                                "dtstart": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "dtend": end.strftime("%Y-%m-%dT%H:%M:%SZ")})
    found = get_json(f"https://api.eumetsat.int/data/search-products/1.0.0/os?{q}", headers=auth)
    flashes: list[tuple[datetime, float]] = []
    for feat in found.get("features", []):
        try:
            href = feat["properties"]["links"]["data"][0]["href"]
            t0 = parse_time(feat["properties"]["date"].split("/")[0])
            blob = http_get(href, headers=auth, timeout=60)
            with zipfile.ZipFile(io.BytesIO(blob)) as zf, tempfile.TemporaryDirectory() as td:
                for nm in zf.namelist():
                    if not nm.endswith(".nc"):
                        continue
                    p = zf.extract(nm, td)
                    with netCDF4.Dataset(p) as ds:
                        la, lo = ds.variables["latitude"][:], ds.variables["longitude"][:]
                        for a, b in zip(la, lo):
                            flashes.append((t0, haversine_km(SITE["lat"], SITE["lon"], float(a), float(b))))
        except Exception:
            continue
    return SourceResult(name="rayos_mtg_li", status="ok", data_time=end.isoformat(),
                        detail=f"{len(flashes)} flashes en 40 min (dominio completo)",
                        payload={"flashes": [(t.isoformat(), d) for t, d in flashes if d <= 100]})


# ════════════════════════════════════════════════════════════════════════
# DETECTORES
# ════════════════════════════════════════════════════════════════════════
def gust_front(series: list[Point], *, window_min: int = 60) -> dict:
    """Firma de corriente de densidad en la última muestra.
    Puerta dura: sin subida de presión no hay frente de racha (calibración 51 días)."""
    g = CFG["gf"]
    if len(series) < 3:
        return {"level": "none", "detected": False, "note": "serie corta"}
    now = series[-1]
    win = [p for p in series[:-1] if 0 < (now.t - p.t).total_seconds() <= window_min * 60]
    if not win:
        win = series[-3:-1]
    def best(vals, fn):
        vals = [v for v in vals if v is not None]
        return fn(vals) if vals else None
    dT = (now.T - best([p.T for p in win], max)) if now.T is not None and best([p.T for p in win], max) is not None else None
    dP = (now.P - best([p.P for p in win], min)) if now.P is not None and best([p.P for p in win], min) is not None else None
    dTd = (now.Td - best([p.Td for p in win], max)) if now.Td is not None and best([p.Td for p in win], max) is not None else None
    # viento: SIEMPRE magnitudes homogéneas (racha con racha, medio con medio).
    g_ref = best([p.G for p in win], lambda v: sum(v) / len(v))
    u_ref = best([p.U for p in win], lambda v: sum(v) / len(v))
    if now.G is not None and g_ref is not None:
        dU = now.G - g_ref
    elif now.U is not None and u_ref is not None:
        dU = now.U - u_ref
    else:
        dU = None
    lT = 2 if dT is not None and dT <= g["dT_strong"] else 1 if dT is not None and dT <= g["dT_watch"] else 0
    lP = 2 if dP is not None and dP >= g["dP_strong"] else 1 if dP is not None and dP >= g["dP_watch"] else 0
    lU = 2 if dU is not None and dU >= g["dU_strong"] else 1 if dU is not None and dU >= g["dU_watch"] else 0
    lTd = 2 if dTd is not None and dTd <= g["dTd_strong"] else 1 if dTd is not None and dTd <= g["dTd_watch"] else 0
    lG = 2 if now.G is not None and now.G >= g["gust_strong"] else 1 if now.G is not None and now.G >= g["gust_watch"] else 0
    if lP < 1:                                              # PUERTA DURA
        level = "watch" if (lT >= 2 and lU >= 1) else "none"
        detected = False
    elif lT >= 2 and lU >= 1 and lTd >= 1:
        level, detected = "confirmed", True
    elif lT >= 1 and lU >= 1 and (lTd >= 1 or lG >= 1):
        level, detected = "probable", True
    elif lT >= 1 or lU >= 1:
        level, detected = "watch", False
    else:
        level, detected = "none", False
    return {"level": level, "detected": detected, "t": now.t.isoformat(),
            "dT": dT, "dP": dP, "dU": dU, "dTd": dTd, "gust": now.G,
            "note": "sin subida de presión: no es corriente de densidad" if lP < 1 and (lT or lU) else ""}


MANUAL_FLOOR: dict = {}                              # --floor naranja (verificado a mano)


def ch_institutional(src: SourceResult, alt: SourceResult | None = None, *,
                     active_only: bool = False) -> Channel:
    ch = Channel("aviso_aemet_activo" if active_only else "aviso_aemet", kind="institutional",
                 confidence="alta")
    warns, used = [], []
    for s in (src, alt):
        if s and s.status == "ok":
            warns += s.payload["warnings"]
            used.append(s.name)
    if MANUAL_FLOOR:
        warns.append(MANUAL_FLOOR)
        used.append("manual")
    if not used:
        ch.available = False
        ch.evidence.append(f"⚠ SUELO INSTITUCIONAL NO VERIFICADO — CAP: {src.detail}; "
                           f"MeteoAlarm: {alt.detail if alt else '—'}. Usa --floor <nivel> si lo ves en aemet.es")
        return ch
    ch.evidence.append(f"fuentes de aviso: {', '.join(used)}")
    if active_only:
        warns = [w for w in warns if w.get("activo_ahora")]
    else:
        horizon = now_utc() + timedelta(hours=CFG["lookahead_h"])
        warns = [w for w in warns if not parse_time(w.get("onset")) or parse_time(w["onset"]) <= horizon]
    if not warns:
        ch.evidence.append(f"sin avisos {'activos ahora' if active_only else 'en las próximas %d h' % CFG['lookahead_h']} "
                           f"en zona {CFG['aemet_zone']}")
        return ch
    top = max(warns, key=lambda w: w["rank"])
    ch.level = top["rank"]
    seen = set()                                       # CAP de AEMET y MeteoAlarm traen el mismo aviso
    for w in sorted(warns, key=lambda w: (-w["rank"], w["onset"])):
        on, ex = parse_time(w["onset"]), parse_time(w["expires"])
        key = (w["nivel"], w["evento"].lower(), on, ex, w.get("descripcion", ""))
        if key in seen:
            continue
        seen.add(key)
        span = (f"{on.astimezone(MADRID):%a %d %H:%M}→{ex.astimezone(MADRID):%a %d %H:%M} local"
                if on and ex else "")
        ch.evidence.append(f"{w['nivel'].upper()} {w['evento']} {span}{' (ACTIVO)' if w['activo_ahora'] else ''}"
                           f" · {w.get('descripcion') or w['parametro']}".rstrip(" ·"))
    return ch


def ch_rain_obs(sources: dict[str, SourceResult]) -> Channel:
    ch = Channel("lluvia_observada", kind="obs", confidence="media")
    got = False
    a = sources.get("aemet_obs")
    if a and a.status == "ok":
        for idema, pts in a.payload["series"].items():
            rec = [p for p in pts if p.R1 is not None]
            if not rec:
                continue
            got = True
            _mark_time(ch, rec[-1].t)
            last1 = rec[-1].R1
            acc3 = sum(p.R1 for p in rec if p.t > rec[-1].t - timedelta(hours=3))
            acc12 = sum(p.R1 for p in rec if p.t > rec[-1].t - timedelta(hours=12))
            lvl = max(level_from(last1, CFG["rain_1h"]), level_from(acc3, CFG["rain_3h"]),
                      level_from(acc12, CFG["rain_12h"]))
            if a.payload.get("prec_mode", "unknown") == "unknown" and lvl > 1:
                ch.evidence.append(f"{idema}: semántica de 'prec' no confirmada → limitado a watch")
                lvl = 1
            ch.level = max(ch.level, lvl)
            ch.metrics[f"{idema}_r1"] = last1
            if last1 > 0 and CFG["station_km"].get(idema, 99) <= CFG["local_obs_km"]:
                ch.local = True
            ch.evidence.append(f"{idema} {CFG['aemet_stations'][idema]}: {last1:.1f} mm/1h, "
                               f"{acc3:.1f} mm/3h, {acc12:.1f} mm/12h ({rec[-1].t:%H:%MZ})")
    w = sources.get("wu_pws")
    if w and w.status == "ok":
        pts = list(w.payload["series"].values())[0]
        rr = pts[-1].RR
        qc = pws_qc(pts)
        if qc:
            ch.evidence.append(f"{CFG['wu_station']} descartada por QC: {qc}")
            rr = None
        if rr is not None:
            got = True
            _mark_time(ch, pts[-1].t)
            ch.level = max(ch.level, level_from(rr, CFG["rain_1h"]))
            ch.evidence.append(f"{CFG['wu_station']}: {rr:.1f} mm/h instantáneo, "
                               f"hoy {w.payload.get('precip_total')} mm")
    m = sources.get("metar")
    if m and m.status == "ok":
        for icao in ("LEIB",):
            raw = (m.payload["raw"].get(icao) or [])[-1:]
            ser = (m.payload.get("series") or {}).get(icao) or []
            for line in raw:
                got = True
                if ser:
                    _mark_time(ch, ser[-1].t)
                if "+TSRA" in line or "+RA" in line:
                    ch.level = max(ch.level, 2)
                elif "TS" in line.split(" ", 1)[-1] or "RA" in line.split(" ", 1)[-1]:
                    ch.level = max(ch.level, 1)
                ch.evidence.append(f"METAR {line}")
    ch.available = got
    if not got:
        ch.evidence.append("ninguna fuente de lluvia observada disponible")
    return ch


def pws_qc(pts: list[Point]) -> str:
    """QC mínimo de una estación casera: retraso, valores imposibles, contador congelado."""
    if not pts:
        return "sin muestras"
    last = pts[-1]
    age = (now_utc() - last.t).total_seconds() / 60
    if age > CFG["pws_stale_min"]:
        return f"dato con {age:.0f} min de retraso"
    if last.RR is not None and not (0 <= last.RR <= 250):
        return f"intensidad imposible {last.RR}"
    if last.T is not None and not (-5 <= last.T <= 45):
        return f"temperatura imposible {last.T}"
    if last.P is not None and not (960 <= last.P <= 1050):
        return f"presión imposible {last.P}"
    recent = [p for p in pts if (last.t - p.t) <= timedelta(hours=2)]
    if len(recent) >= 8 and len({(p.T, p.P, p.U) for p in recent}) == 1:
        return "valores congelados 2 h"
    return ""


def ch_runoff(sources: dict[str, SourceResult], rain: Channel) -> Channel:
    """Torrentes de Es Amunts: intensidad sobre suelo ya mojado. Heurística, sin calibrar."""
    ch = Channel("escorrentia_torrentes", kind="obs", confidence="baja", group="lluvia_observada")
    a = sources.get("aemet_obs")
    if not (a and a.status == "ok" and "B908X" in a.payload["series"]):
        ch.available = False
        ch.evidence.append("sin B908X: no se evalúa escorrentía")
        return ch
    pts = [p for p in a.payload["series"]["B908X"] if p.R1 is not None]
    if not pts:
        ch.available = False
        return ch
    acc = sum(p.R1 for p in pts)
    i1 = pts[-1].R1
    _mark_time(ch, pts[-1].t)
    wet = acc >= CFG["runoff_antecedent_mm"]
    lvl = level_from(i1, (15.0, 30.0, 50.0))
    if wet:
        lvl = min(3, lvl + 1) if lvl else (1 if i1 >= 5 else 0)
    # B908X está en Sant Joan, no en la cuenca que drena a Portinatx: es un PROXY.
    # Sin cuenca validada (CATCHMENT_VERIFIED=1) el canal no pasa de 'watch'.
    if os.environ.get("CATCHMENT_VERIFIED") != "1":
        if lvl > 1:
            ch.evidence.append(f"nivel {LEVELS[lvl]} limitado a watch: pluviómetro fuera de la cuenca de Portinatx")
        lvl = min(lvl, 1)
    ch.level = lvl
    ch.evidence.append(f"B908X (proxy): {acc:.1f} mm en {len(pts)} h previas ({'suelo saturado' if wet else 'suelo no saturado'}), "
                       f"intensidad {i1:.1f} mm/h")
    return ch


def ch_gustfront(sources: dict[str, SourceResult]) -> Channel:
    ch = Channel("frente_racha", kind="obs", confidence="media")
    rank = {"none": 0, "watch": 1, "probable": 2, "confirmed": 3}
    got = False
    for sname, window in (("socib_boya", 60), ("wu_pws", 60), ("aemet_obs", 120), ("metar", 120)):
        s = sources.get(sname)
        if not (s and s.status == "ok"):
            continue
        for st, pts in s.payload["series"].items():
            if sname == "metar" and st not in ("LEIB",):
                continue
            got = True
            if pts:
                _mark_time(ch, pts[-1].t)
            v = gust_front(pts, window_min=window)
            lvl = rank[v["level"]]
            dkm = CFG["station_km"].get(st)
            far = dkm is None or dkm > CFG["local_obs_km"]
            if far and lvl > CFG["far_obs_cap"]:
                lvl = CFG["far_obs_cap"]
            if not far and lvl >= 1:
                ch.local = True
            ch.level = max(ch.level, lvl)
            if v["level"] != "none":
                ch.evidence.append(f"{st}: {v['level']} ΔT={_f(v['dT'])} ΔP={_f(v['dP'])} "
                                   f"ΔU={_f(v['dU'])} ΔTd={_f(v['dTd'])} racha={_f(v['gust'])} {v['note']}"
                                   + (f" — estación a {'?' if dkm is None else f'{dkm:.0f}'} km: PRECURSOR, la "
                                      f"propagación a Portinatx no está demostrada (techo {LEVELS[CFG['far_obs_cap']]})"
                                      if far else ""))
    ch.available = got
    if got and not ch.evidence:
        ch.evidence.append("sin firma de corriente de densidad en ninguna estación")
    return ch


def _f(x):
    return "—" if x is None else f"{x:+.1f}"


def ch_radar(src: SourceResult | None) -> Channel:
    ch = Channel("radar", kind="obs", confidence="media")
    if not (src and src.status == "ok"):
        ch.available = False
        ch.evidence.append(f"radar no disponible ({src.status if src else '—'})")
        return ch
    frames = src.payload["frames"]
    fr = [f for f in frames if not f["dup"]] or frames
    # Imágenes idénticas en todos los frames: con cielo despejado es normal (teselas vacías);
    # con ecos presentes, el mismo campo durante toda la ventana indica radar congelado.
    if len(frames) >= 2 and all(f["dup"] for f in frames[1:]) and frames[-1]["cover"].get(60, 0) > 0:
        ch.available = False
        ch.evidence.append(f"radar congelado: {len(frames)} frames con la misma imagen con ecos → UNKNOWN")
        return ch
    last = fr[-1]
    _mark_time(ch, last.get("time"))
    cov = last["cover"]
    near = last["nearest_km"]
    ch.evidence.append(f"cobertura de ecos: {cov[10]:.0%} ≤10 km · {cov[30]:.0%} ≤30 km · {cov[60]:.0%} ≤60 km; "
                       f"eco más cercano {('—' if near is None else f'{near:.0f} km')}")
    # acercamiento: pendiente de la distancia mínima
    ds = [(parse_time(f["time"]), f["nearest_km"]) for f in fr if f["nearest_km"] is not None]
    closing = None
    if len(ds) >= 2 and (ds[-1][0] - ds[0][0]).total_seconds() > 0:
        closing = (ds[0][1] - ds[-1][1]) / ((ds[-1][0] - ds[0][0]).total_seconds() / 3600)
        ch.evidence.append(f"velocidad de acercamiento del eco más cercano: {closing:+.0f} km/h")
    # Cobertura/proximidad solo da 'watch'. 'alert'/'alarm' exigen paleta calibrada Y
    # persistencia: ecos fuertes en ≥2 de los 3 últimos frames (un frame aislado no basta).
    lvl = 1 if (cov[60] > 0.05 or (near is not None and near <= 60)) else 0
    # Señal LOCAL (abre el gate rojo): eco a ≤25 km con ≥10 % de cobertura a ≤30 km,
    # persistente en ≥2 de los 3 últimos frames. Un eco suelto o lejano no cuenta.
    def _is_local(f):
        nk = f.get("nearest_km")
        return nk is not None and nk <= CFG["local_obs_km"] and f["cover"][30] >= CFG["local_cover_30km"]
    n_loc = sum(1 for f in fr[-3:] if _is_local(f))
    ch.local = n_loc >= 2
    ch.evidence.append(f"eco local (≤{CFG['local_obs_km']:.0f} km y ≥{CFG['local_cover_30km']:.0%} a ≤30 km): "
                       f"{n_loc}/3 frames → {'SÍ' if ch.local else 'no'}")
    # Intensidad: dBZ decodificados. El radar SOLO llega a 'alert' (≥45 dBZ a ≤15 km o QPE ≥20 mm/h
    # en ≥2 de 3 frames). Para 'alarm' hace falta otra observación de grupo distinto (fusión).
    last3 = fr[-3:]
    n_strong = sum(1 for f in last3 if f.get("max_dbz_15km", 0) >= CFG["radar_alert_dbz"])
    def _qhi(f):
        return (f.get("qpe_site_mmh") or {}).get(CFG["radar_threshold_zr"], 0.0)
    n_qpe = sum(1 for f in last3 if _qhi(f) >= CFG["radar_alert_qpe"])
    if n_strong >= 2 or n_qpe >= 2:
        lvl = max(lvl, 2)
    ch.evidence.append(f"dBZ máx ≤30 km {last.get('max_dbz_30km', 0):.0f} · ≤15 km {last.get('max_dbz_15km', 0):.0f} · "
                       f"en el punto (≤{CFG['qpe_radius_km']:.0f} km) {last.get('site_max_dbz', 0):.0f}; "
                       f"≥{CFG['radar_alert_dbz']:.0f} dBZ a ≤{CFG['radar_alert_km']:.0f} km en {n_strong}/3 frames")
    if last.get("nearest_strong_km") is not None:
        ch.evidence.append(f"eco ≥{CFG['radar_alert_dbz']:.0f} dBZ más cercano: {last['nearest_strong_km']:.0f} km")
    # QPE: intensidad actual y acumulado de la ventana con cada relación Z–R (rango, no valor único)
    acc = {k: 0.0 for k in CFG["zr"]}
    for i, f in enumerate(fr):
        if i == 0:
            continue
        dt_h = max(0.0, (parse_time(f["time"]) - parse_time(fr[i - 1]["time"])).total_seconds() / 3600)
        for k in acc:
            acc[k] += (f.get("qpe_site_mmh") or {}).get(k, 0.0) * dt_h
    now_q = last.get("qpe_site_mmh") or {}
    if now_q:
        span = (parse_time(fr[-1]["time"]) - parse_time(fr[0]["time"])).total_seconds() / 60
        ch.evidence.append("QPE radar en el punto (estimación, no medida): " + " · ".join(
            f"{k} {now_q.get(k, 0):.1f} mm/h, {acc[k]:.0f} mm/{span:.0f} min" for k in CFG["zr"])
            + f" — umbral de alerta evaluado solo con {CFG['radar_threshold_zr']}; las demás son diagnóstico "
              "(el radar compuesto puede infraestimar lluvia cálida)")
    ch.level = lvl
    ch.metrics.update({"nearest_km": near, "cover30": cov[30], "site_dbz": last.get("site_max_dbz", 0),
                       "qpe_now": dict(now_q), "qpe_acc": {k: round(v, 1) for k, v in acc.items()},
                       "max_dbz_15km": last.get("max_dbz_15km", 0)})
    return ch


def ch_lightning(src: SourceResult | None) -> Channel:
    ch = Channel("rayos", kind="obs", confidence="media")
    if not (src and src.status == "ok"):
        ch.available = False
        ch.evidence.append(f"rayos no disponibles ({src.status if src else '—'})")
        return ch
    _mark_time(ch, src.data_time)
    fl = [(parse_time(t), d) for t, d in src.payload["flashes"]]
    n30 = sum(1 for _, d in fl if d <= 30)
    n60 = sum(1 for _, d in fl if d <= 60)
    t_end = now_utc()
    recent = sum(1 for t, d in fl if d <= 60 and t and (t_end - t) <= timedelta(minutes=10))
    older = sum(1 for t, d in fl if d <= 60 and t and timedelta(minutes=10) < (t_end - t) <= timedelta(minutes=40))
    jump = recent > 0 and recent >= 2 * max(1, older / 3)
    ch.level = 3 if n30 >= 50 else 2 if (n30 >= 10 or jump) else 1 if n60 >= 1 else 0
    n_loc = sum(1 for _, d in fl if d <= CFG["local_obs_km"])
    ch.local = n_loc >= 3
    ch.evidence.append(f"flashes 40 min: {n30} ≤30 km, {n60} ≤60 km; últimos 10 min {recent}"
                       f"{' · SALTO DE RAYOS' if jump else ''}")
    return ch


def _window_max(vals: list, n: int) -> float | None:
    """Máximo de sumas móviles SOLO sobre ventanas completas (sin huecos ni negativos)."""
    best = None
    for i in range(len(vals) - n + 1):
        blk = vals[i:i + n]
        if all(isinstance(x, (int, float)) and x >= 0 and not math.isnan(x) for x in blk):
            s = sum(blk)
            best = s if best is None else max(best, s)
    return best


def _rolling_max(vals: list[float], n: int) -> float:
    v = [x or 0.0 for x in vals]
    if len(v) < n:
        return sum(v)
    s = sum(v[:n]); best = s
    for i in range(n, len(v)):
        s += v[i] - v[i - n]
        best = max(best, s)
    return best


def ch_models(src: SourceResult | None) -> list[Channel]:
    chans = []
    if not (src and src.status == "ok"):
        c = Channel("modelos", kind="model", available=False)
        c.evidence.append(f"Open-Meteo no disponible ({src.status if src else '—'}): {src.detail if src else ''}")
        return [c]
    for m, per_pt in src.payload.items():
        c = Channel(f"modelo_{m}", kind="model", confidence="baja")
        if not per_pt or not per_pt[0]["pr"]:
            c.available = False
            c.evidence.append("sin datos (¿fuera de dominio?)")
            chans.append(c)
            continue
        pt0 = per_pt[0]
        if all(x is None for x in pt0["pr"]):
            c.available = False
            c.evidence.append("precipitación sin valores (todo None): UNKNOWN, no 0 mm")
            chans.append(c)
            continue
        _mark_time(c, src.data_time)
        p1_pt = _vmax(pt0["pr"])
        p12_pt = _window_max(pt0["pr"], 12)
        nb = [p["pr"] for p in per_pt if p["pr"] and any(x is not None for x in p["pr"])]
        p1_nb = max(_vmax(v) for v in nb)
        w12 = [w for w in (_window_max(v, 12) for v in nb) if w is not None]
        p12_nb = max(w12) if w12 else None
        gust = _vmax(pt0["gust"] or [])
        cape = _vmax(pt0["cape"] or [])
        n_gap = sum(x is None for x in pt0["pr"])
        if n_gap:
            c.evidence.append(f"{n_gap} horas sin valor: no se cuentan como 0 mm; acumulados solo en ventanas completas")
        i_peak = max(range(len(pt0["pr"])), key=lambda i: pt0["pr"][i] if pt0["pr"][i] is not None else -1)
        t_peak = pt0["time"][i_peak] if pt0["time"] else "?"
        # nivel: punto pesa entero; vecindad un escalón menos (error de posición)
        lvl = max(level_from(p1_pt, CFG["rain_1h"]),
                  level_from(p12_pt, CFG["rain_12h"]) if p12_pt is not None else 0,
                  max(0, max(level_from(p1_nb, CFG["rain_1h"]),
                             level_from(p12_nb, CFG["rain_12h"]) if p12_nb is not None else 0) - 1),
                  level_from(gust, CFG["gust_model"]))
        c.level = min(lvl, 2)                       # un determinista nunca da 'alarm'
        c.group = "nwp_hr" if m in CFG["gate_models"] else "nwp_global"
        c.evidence.append(f"punto: máx {p1_pt:.1f} mm/1h, {_n(p12_pt)} mm/12h (pico {t_peak}Z) · "
                          f"vecindad ±17 km: {p1_nb:.1f} mm/1h, {_n(p12_nb)} mm/12h · "
                          f"racha {_n(gust)} km/h · CAPE {_n(cape)} J/kg")
        chans.append(c)
    return chans


def _n(x):
    return "—" if x is None else f"{x:.0f}"


def _vmax(vals: list) -> float | None:
    """Máximo de los valores presentes; None si no hay ninguno (un hueco no es 0)."""
    v = [x for x in vals if isinstance(x, (int, float)) and not math.isnan(x)]
    return max(v) if v else None


def ch_trajectory(tracks: dict | None, data_time: str | None = None) -> tuple[Channel, bool]:
    c = Channel("trayectoria_nucleo", kind="model", confidence="media", group="nwp_hr")
    if not tracks:
        c.available = False
        c.evidence.append("rejilla de modelos no disponible")
        return c, False
    _mark_time(c, data_time)
    gate = False
    for m, t in tracks.items():
        if t["max_lat"] is None:
            continue
        hr = m in CFG["gate_models"]
        lvl = 2 if t["centered"] else 1 if t["local12"] >= 60 or t["local6"] >= 40 else 0
        c.level = max(c.level, lvl if hr else min(lvl, 1))
        gate |= hr and t["centered_consecutive"] >= 2
        disp = "" if t["displacement_km"] is None else (
            f" · núcleo movido {t['displacement_km']:.0f} km vs run previo "
            f"(distancia a Portinatx {t['prev_dist_km']:.0f}→{t['max_dist_km']:.0f} km)")
        c.evidence.append(f"{m} run {t['init'][:16]}: núcleo {t['max12']:.0f} mm/12h en "
                          f"{t['max_lat']:.1f}N {t['max_lon']:.1f}E a {t['max_dist_km']:.0f} km · "
                          f"≤20 km: {t['local12']:.0f} mm/12h, {t['local6']:.0f} mm/6h, {t['local1']:.0f} mm/1h · "
                          f"celdas ≥100 mm/12h: {t['cells_ge100_12h']} · runs centrados seguidos: "
                          f"{t['centered_consecutive']}{disp}")
    return c, gate


def ch_ensemble(src: SourceResult | None) -> Channel:
    c = Channel("ensemble_ecmwf", kind="ensemble", confidence="media")
    if not (src and src.status == "ok"):
        c.available = False
        c.evidence.append(f"ensemble no disponible ({src.status if src else '—'})")
        return c
    _mark_time(c, src.data_time)
    mem = src.payload["members"]
    # solo miembros con ventanas completas; si quedan <10, el canal no opina
    w24 = [_window_max(m, 24) for m in mem]
    w12 = [_window_max(m, 12) for m in mem]
    w1 = [_window_max(m, 1) for m in mem]
    ok = [i for i in range(len(mem)) if w24[i] is not None and w12[i] is not None]
    if len(ok) < 10:
        c.available = False
        c.evidence.append(f"solo {len(ok)} miembros con ventanas completas: insuficiente")
        return c
    n = len(ok)
    p24 = sum(w24[i] >= 50 for i in ok) / n
    p12 = sum(w12[i] >= 100 for i in ok) / n
    p1 = sum((w1[i] or 0) >= 30 for i in ok) / n
    pp = src.payload.get("per_point") or [mem]
    nn = min(len(x) for x in pp)
    p24_any = sum(any((_window_max(pt[i], 24) or 0) >= 50 for pt in pp) for i in range(nn)) / nn
    p12_any = sum(any((_window_max(pt[i], 12) or 0) >= 100 for pt in pp) for i in range(nn)) / nn
    mem = [mem[i] for i in ok]
    c.evidence.append(f"vecindad ±17 km (algún punto): P(24h≥50)={p24_any:.0%} · P(12h≥100)={p12_any:.0%} "
                      f"— no equivale a probabilidad en Portinatx")
    tot = sorted(sum(x or 0 for x in m) for m in mem)
    med, p90 = tot[n // 2], tot[min(n - 1, int(0.9 * n))]
    th = CFG["ens_thresholds"]
    lvl = 0
    for p, key in ((p24, "p24_50"), (p12, "p12_100"), (p1, "p1_30")):
        if p >= th[key][1]:
            lvl = max(lvl, 2)
        elif p >= th[key][0]:
            lvl = max(lvl, 1)
    c.level = lvl
    c.evidence.append(f"{n} miembros · P(24h≥50)={p24:.0%} · P(12h≥100)={p12:.0%} · P(1h≥30)={p1:.0%} · "
                      f"total 72 h mediana {med:.0f} / p90 {p90:.0f} mm (0,25°: cota inferior en convección)")
    return c


def ch_sea(src: SourceResult | None) -> Channel:
    c = Channel("mar_bahia", kind="model", confidence="media")
    if not (src and src.status == "ok"):
        c.available = False
        c.evidence.append(f"oleaje no disponible ({src.status if src else '—'})")
        return c
    h = src.payload
    if not any(x is not None for x in h.get("wave_height") or []):
        c.available = False
        c.evidence.append("oleaje sin valores (todo None): UNKNOWN, no 0 m")
        return c
    _mark_time(c, src.data_time)
    best, best_t, best_dir = 0.0, "", None
    for t, hs, d in zip(h.get("time", []), h.get("wave_height", []), h.get("wave_direction", [])):
        if hs is None or d is None:
            continue
        if in_sector(d, CFG["bay_open_sector"]) and hs > best:
            best, best_t, best_dir = hs, t, d
    allmax = _vmax(h.get("wave_height") or [])
    c.level = min(2, level_from(best, CFG["wave_hs"]))
    c.evidence.append(f"Hs máx entrando por el sector abierto {CFG['bay_open_sector']}: {best:.1f} m "
                      f"({best_t}Z, {_n(best_dir)}°) · Hs máx cualquier dirección {allmax:.1f} m")
    return c


def ch_gauges(src: SourceResult | None, state: dict) -> Channel:
    """Pluviómetros Meteoclimatic. Intensidad = Δ(lluvia diaria)/Δt entre ciclos (mismo día local).
    Vecina (≤gauge_near_km) = indicio para Portinatx, NUNCA medida en Portinatx. Dato viejo = STALE."""
    ch = Channel("pluviometros", kind="obs", confidence="media", group="pluviometros")
    if not (src and src.status == "ok"):
        ch.available = False
        ch.evidence.append(f"Meteoclimatic no disponible ({src.status if src else '—'}): lluvia UNKNOWN, no 0")
        return ch
    prev = state.setdefault("gauge_prev", {})
    daily = state.setdefault("gauge_daily", {})
    fresh = 0
    ch.metrics.update({"near_fresh": 0, "near_rate_max": None, "near_total_max": None, "stations": []})
    for g in sorted(src.payload["stations"], key=lambda g: g["dist_km"]):
        near = g["dist_km"] <= CFG["gauge_near_km"]
        tag = f"{g['nombre']} (a {g['dist_km']:.0f} km{', vecina' if near else ''})"
        if g["edad_min"] > CFG["gauge_stale_min"] or g["lluvia_dia"] is None:
            ch.evidence.append(f"{tag}: STALE (dato de hace {g['edad_min']:.0f} min) — no se infiere 0")
            continue
        t = parse_time(g["t"])
        day = t.astimezone(MADRID).date().isoformat()
        yday = (t.astimezone(MADRID).date() - timedelta(days=1)).isoformat()
        # F14: posible arrastre hasta 00 UTC, según el desfase vigente en ESTE instante.
        last_y = (daily.get(g["id"]) or {}).get(yday)
        if before_utc_daily_reset(t) and last_y and g["lluvia_dia"] and abs(g["lluvia_dia"] - last_y) < 0.05:
            ch.evidence.append(f"{tag}: total {g['lluvia_dia']:.1f} mm = el de ayer (reinicio a 00 UTC) — "
                               "no se usa como lluvia de hoy")
            continue
        fresh += 1
        _mark_time(ch, t)
        daily.setdefault(g["id"], {})[day] = g["lluvia_dia"]
        for k in list(daily[g["id"]]):
            if k < (t.astimezone(MADRID).date() - timedelta(days=3)).isoformat():
                del daily[g["id"]][k]
        ante = (daily[g["id"]].get(yday) or 0.0) + g["lluvia_dia"]
        wet = ante >= CFG["sat_mm"]
        rate = None
        p = prev.get(g["id"])
        if p and p.get("day") == day:
            dt_h = (t - parse_time(p["t"])).total_seconds() / 3600
            if 8 / 60 <= dt_h <= 1.5:
                rate = max(0.0, (g["lluvia_dia"] - p["total"]) / dt_h)
            elif dt_h < 8 / 60 and "rate" in p:
                rate = p["rate"]
        hist = state.setdefault("gauge_hist", {}).setdefault(g["id"], [])
        if not hist or hist[-1]["t"] != g["t"]:
            hist.append({"t": g["t"], "total": g["lluvia_dia"]})     # para verificar predicciones en su ventana
            del hist[:-24]
        if not p or parse_time(g["t"]) > parse_time(p["t"]):
            prev[g["id"]] = {"t": g["t"], "total": g["lluvia_dia"], "day": day,
                             **({"rate": rate} if rate is not None else {})}
        lvl = max(level_from(rate, CFG["rain_1h_wet" if wet else "rain_1h"]) if rate is not None else 0,
                  level_from(g["lluvia_dia"], CFG["rain_day_wet"] if wet else CFG["rain_12h"]))
        if not near:
            lvl = min(lvl, 1)                                      # lejana: contexto regional, techo 'watch'
        ch.level = max(ch.level, lvl)
        if near and (g["lluvia_dia"] > 0 or (rate or 0) > 0):
            ch.local = True
        ch.metrics["stations"].append({"id": g["id"], "nombre": g["nombre"], "dist_km": g["dist_km"], "near": near,
                                       "total": g["lluvia_dia"], "rate": rate, "t": g["t"],
                                       "lat": g.get("lat"), "lon": g.get("lon"), "ante_mm": round(ante, 1),
                                       "wet": wet})
        if near:
            ch.metrics["near_fresh"] += 1
            if rate is not None:
                ch.metrics["near_rate_max"] = max(rate, ch.metrics["near_rate_max"] or 0.0)
            ch.metrics["near_total_max"] = max(g["lluvia_dia"], ch.metrics["near_total_max"] or 0.0)
        ch.evidence.append(f"{tag}: {g['lluvia_dia']:.1f} mm hoy"
                           + (f", {rate:.1f} mm/h (Δ entre ciclos)" if rate is not None else ", intensidad pendiente del próximo ciclo")
                           + (f", {g['T']:.1f} °C" if g["T"] is not None else "")
                           + (f" · SUELO SATURADO (ayer+hoy {ante:.0f} mm): umbrales rebajados" if wet else ""))
    ch.available = fresh > 0
    if not fresh:
        ch.evidence.append("ninguna estación fresca: lluvia UNKNOWN")
    ch.evidence.append("estaciones vecinas = indicio, no lluvia medida en Portinatx")
    return ch


def ch_sea_obs(src: SourceResult | None) -> Channel:
    """Boyas de mar abierto (PORTUS): Hs con mar del sector N–E, que es el que entra en la bahía."""
    ch = Channel("mar_boyas", kind="obs", confidence="media", group="mar")
    if not (src and src.status == "ok"):
        ch.available = False
        ch.evidence.append(f"PORTUS no disponible ({src.status if src else '—'})")
        return ch
    got = False
    now = now_utc()
    for name in CFG["portus_buoys"].values():
        all_rows = [r for r in src.payload["stations"].get(name, []) if r.get("hm0") is not None]
        ser = [r for r in all_rows if observation_recency(
            r.get("t"), CFG["channel_max_age_min"]["mar_boyas"], now)["freshness"] == "FRESH"]
        if not ser:
            if all_rows:
                ch.evidence.append(f"{name}: oleaje STALE → UNKNOWN (sin Hs reciente)")
            continue
        got = True
        last = ser[-1]
        _mark_time(ch, last["t"])
        age = (now - parse_time(last["t"])).total_seconds() / 60
        trend = last["hm0"] - ser[-4]["hm0"] if len(ser) >= 4 else None
        d = last.get("dmd")
        ne = d is not None and in_sector(d, (330.0, 100.0))
        lvl = level_from(last["hm0"], CFG["sea_hs"]) if ne else 0
        ch.level = max(ch.level, min(lvl, 2))                     # el mar abierto no decide el rojo
        ch.evidence.append(f"{name}: Hs {last['hm0']:.2f} m, Hmax {last.get('hmax', float('nan')):.1f} m, "
                           f"Tp {last.get('tp', float('nan')):.1f} s, de {d if d is not None else '—'}°"
                           + (f", {trend:+.2f} m en 3 h" if trend is not None else "")
                           + f" ({parse_time(last['t']).astimezone(MADRID):%H:%M} local"
                           + (", STALE" if age > 120 else "") + ")")
    ch.available = got
    if not got:
        ch.evidence.append("oleaje PORTUS UNKNOWN: ninguna boya con Hs reciente")
    ch.evidence.append("boyas lejanas: describen el mar regional, no la altura de ola dentro de la cala")
    return ch


def ch_wind_obs(src: SourceResult | None) -> Channel:
    ch = Channel("viento_estaciones", kind="obs", confidence="media", group="viento")
    if not (src and src.status == "ok"):
        ch.available = False
        ch.evidence.append(f"PORTUS no disponible ({src.status if src else '—'})")
        return ch
    got = False
    now = now_utc()
    for name in CFG["portus_wind"].values():
        ser = src.payload["stations"].get(name, [])
        recent = [r for r in ser if (r.get("vv_mx") is not None or r.get("vv_md") is not None)
                  and observation_recency(r.get("t"), CFG["channel_max_age_min"]["viento_estaciones"],
                                          now)["freshness"] == "FRESH"]
        if not recent:
            continue
        got = True
        gmax = max((r.get("vv_mx") or r.get("vv_md") or 0) for r in recent) * 3.6
        last = recent[-1]
        _mark_time(ch, last["t"])
        # Puertos de Ibiza/Formentera y la boya del canal están a ≥25 km: precursores, no Portinatx.
        ch.level = max(ch.level, min(level_from(gmax, CFG["gust_model"]), CFG["far_obs_cap"]))
        ch.evidence.append(f"{name}: racha máx 1 h {gmax:.0f} km/h; último {(last.get('vv_md') or 0) * 3.6:.0f} km/h "
                           f"de {last.get('dv_md', float('nan')):.0f}° ({parse_time(last['t']).astimezone(MADRID):%H:%M})")
    ch.available = got
    if got:
        ch.evidence.append(f"estaciones a ≥25 km: viento regional, techo {LEVELS[CFG['far_obs_cap']]} para Portinatx")
    return ch


def manual_obs(state: dict, now: datetime) -> dict:
    """Observaciones introducidas a mano (escorrentía, anegamiento). Caducan a las manual_obs_ttl_h."""
    out = {}
    for k, v in (state.get("manual_obs") or {}).items():
        t = parse_time(v.get("t"))
        if t and (now - t) <= timedelta(hours=CFG["manual_obs_ttl_h"]):
            out[k] = {**v, "edad_h": round((now - t).total_seconds() / 3600, 1)}
    return out


def official_state(inst_now: Channel, inst_all: Channel, warnings: list[dict]) -> dict:
    act = [w for w in warnings if w.get("activo_ahora")]
    top = max(act, key=lambda w: w["rank"]) if act else None
    return {"level_now": LEVELS[inst_now.level] if inst_now.available else "unknown",
            "level_36h": LEVELS[inst_all.level] if inst_all.available else "unknown",
            "vigente": ({"nivel": top["nivel"], "evento": top["evento"], "desde": top["onset"],
                         "hasta": top["expires"], "umbral": top.get("descripcion") or top.get("parametro", "")}
                        if top else None),
            "vigentes": [{"nivel": w["nivel"], "tipo": w.get("tipo", ""), "evento": w["evento"],
                          "desde": w["onset"], "hasta": w["expires"],
                          "umbral": w.get("descripcion") or w.get("parametro", "")}
                         for w in sorted(act, key=lambda w: -w["rank"])],
            "verificado": inst_now.available}


def local_hazard_state(chs: dict[str, Channel], manual: dict) -> dict:
    def st(c: Channel | None):
        if c is None or not c.available:
            return {"estado": "UNKNOWN", "nivel": "—"}
        return {"estado": "OBSERVED", "nivel": LEVELS[c.level], "local": c.local}
    out = {k: st(c) for k, c in chs.items()}
    for k in ("runoff", "flooding"):
        v = manual.get(k)
        out[k] = ({"estado": "OBSERVED" if v["value"] == "observed" else "NONE",
                   "nivel": "alert" if v["value"] == "observed" and k == "runoff" else
                            "alarm" if v["value"] == "observed" else "quiet",
                   "fuente": "observación manual", "edad_h": v["edad_h"]} if v else {"estado": "UNKNOWN", "nivel": "—"})
    return out


def precaution_hold(manual: dict) -> str | None:
    v = manual.get("es_alert")
    if v and v["value"] == "active":
        return f"ES-Alert de Protección Civil vigente (registrada hace {v['edad_h']} h)"
    for k in ("flooding", "runoff"):
        v = manual.get(k)
        if v and v["value"] == "observed":
            return f"{k} observado hace {v['edad_h']} h"
    return None


# ════════════════════════════════════════════════════════════════════════
# FRESCURA (#16): un dato viejo, vacío o sin hora no es una observación
# ════════════════════════════════════════════════════════════════════════
def channel_age_limit(name: str) -> float | None:
    lim = CFG["channel_max_age_min"]
    if name in lim:
        return lim[name]
    return lim["modelo"] if name.startswith("modelo") else None


def _mark_time(ch: Channel, t) -> None:
    """Registra en el canal la hora del dato más reciente realmente usado."""
    tt = parse_time(t) if isinstance(t, str) else t
    if tt is None:
        return
    cur = parse_time(ch.data_time) if ch.data_time else None
    if cur is None or tt > cur:
        ch.data_time = tt.isoformat()


def apply_freshness(channels: list[Channel], now: datetime | None = None) -> None:
    """Pasa a UNKNOWN (available=False, nivel 0, sin señal local) todo canal vivo cuyo dato más
    reciente no tiene hora, supera su edad máxima o viene del futuro. Ausencia de dato ≠ calma."""
    now = now or now_utc()
    for c in channels:
        if c.kind == "institutional" or not c.available:
            continue
        lim = channel_age_limit(c.name)
        t = parse_time(c.data_time) if c.data_time else None
        why = None
        if lim is None:
            why = "canal sin edad máxima declarada en CFG"
        elif t is None:
            why = "sin hora de dato verificable"
        else:
            age = (now - t).total_seconds() / 60
            c.metrics["age_min"] = round(age)
            if age > lim:
                why = f"dato de hace {age:.0f} min > límite {lim:.0f} min"
            elif age < -10:
                why = f"dato fechado {-age:.0f} min en el futuro"
        if why:
            c.available, c.level, c.local = False, 0, False
            c.evidence.insert(0, f"STALE → UNKNOWN: {why}; no se usa como observación")


# ════════════════════════════════════════════════════════════════════════
# FUSIÓN + HISTÉRESIS
# ════════════════════════════════════════════════════════════════════════
def fuse(channels: list[Channel], hr_gate: bool = False) -> dict:
    inst = max((c.level for c in channels if c.kind == "institutional" and c.available), default=0)
    obs = [c for c in channels if c.kind == "obs" and c.available]
    oth = [c for c in channels if c.kind in ("model", "ensemble") and c.available]
    obs_max = max((c.level for c in obs), default=0)
    mod_max = min(2, max((c.level for c in oth), default=0))
    # #17: ninguna observación aislada da 'alarm' por sí sola; techo 'alert'. El rojo solo llega
    # por confirmación independiente (abajo), por el gate HR o por el suelo del aviso oficial.
    obs_cap = min(2, obs_max)
    level = max(inst, obs_cap, mod_max)
    reasons = []
    if inst:
        reasons.append(f"suelo institucional = {LEVELS[inst]}")
    if obs_max > obs_cap and level < 3:
        solo = max(obs, key=lambda c: c.level)
        reasons.append(f"{solo.name} llega a alarm por sí solo: techo alert sin confirmación independiente")
    # 'alarm' por confirmación: observación en alert + otro canal independiente en alert
    # (el aviso es suelo, no confirmación; tampoco se confirman canales del mismo grupo)
    # La confirmación debe ser OBSERVACIONAL: un modelo no confirma una observación
    # (la vía de modelo al rojo es solo el gate de 2 runs HR + nowcast, más abajo).
    if level < 3 and obs_max >= 2:
        lead = max(obs, key=lambda c: c.level)
        # Independencia (Ante): grupo distinto Y raíz de fuente distinta; y al menos una de las dos
        # observaciones debe ser LOCAL (dos estaciones a 25–30 km no confirman el punto).
        # …y del MISMO fenómeno: lluvia en un pluviómetro y mar en una boya no se confirman entre sí.
        support = [c for c in obs if c.level >= 2 and c.group != lead.group
                   and channel_root(c.name) != channel_root(lead.name) and (c.local or lead.local)
                   and HAZARD_FAMILY.get(c.name, c.name) == HAZARD_FAMILY.get(lead.name, lead.name)]
        if not support and any(c.level >= 2 and c.group != lead.group for c in obs if c is not lead):
            reasons.append("dos observaciones en alert sin independencia o sin señal local: no confirman alarm")
        if support:
            level = 3
            reasons.append(f"observación confirmada por otra independiente: {lead.name} + {support[0].name} → alarm")
    # gate rojo interno de modelo: ≥2 runs de alta resolución seguidos centrando ≥100 mm/12 h
    # (o ≥60/6 h) a ≤20 km, Y el nowcast ya ve algo (alguna observación ≥ watch).
    local = [c for c in obs if c.local and c.level >= 1]
    if level < 3 and hr_gate and local:
        level = 3
        reasons.append("gate interno: 2 runs AROME/ICON-EU consecutivos centrados sobre Portinatx + señal "
                       f"observada local ({', '.join(c.name for c in local)})")
    elif hr_gate:
        reasons.append("2 runs de alta resolución consecutivos centrados, pero sin señal observada LOCAL "
                       "(≤25 km persistente, rayos o lluvia medida): no sube a alarm")
    top = sorted([c for c in channels if c.available], key=lambda c: -c.level)[:3]
    reasons += [f"{c.name}={LEVELS[c.level]}" for c in top if c.level]
    missing = [c.name for c in channels if not c.available]
    # Ausencia de datos ≠ tranquilidad: con <2 canales observados vivos, o con una familia de
    # fenómeno obligatoria (lluvia) sin ningún canal observado vivo, se declara cobertura
    # insuficiente y la histéresis no desescala. Viento y mar vivos no dicen nada de la lluvia.
    n_obs_total = sum(1 for c in channels if c.kind == "obs")
    # H1: rayos y proxy de escorrentía están en la familia de *peligro* lluvia,
    # pero NO son medidas de precipitación que certifiquen cobertura seca.
    COVERAGE_RAIN = frozenset(("lluvia_observada", "pluviometros", "radar"))
    rain_all = [c for c in channels if c.kind == "obs" and c.name in COVERAGE_RAIN]
    rain_live = [c for c in rain_all if c.available]
    families = {f: ("OK" if (bool(rain_live) if f == "lluvia" else
                         any(HAZARD_FAMILY.get(c.name) == f for c in obs)) else "UNKNOWN")
                for f in CFG["required_families"]}
    blind = [f for f, st in families.items() if st == "UNKNOWN"]
    insufficient = len(obs) < CFG["min_obs_channels"] or bool(blind)
    if len(obs) < CFG["min_obs_channels"]:
        reasons.append(f"⚠ COBERTURA INSUFICIENTE: {len(obs)}/{n_obs_total} canales observados — "
                       f"un 'quiet' aquí no significa calma")
    for f in blind:
        reasons.append(f"⚠ COBERTURA INSUFICIENTE DE {f.upper()}: familia sin medida reciente "
                       f"directa de precipitación — {f} UNKNOWN, un 'quiet' no significa calma")
    cov = f"{len(obs)}/{n_obs_total} canales observados activos"
    if blind:
        cov += " · sin dato: " + ", ".join(blind)
    return {"proposed": LEVELS[level], "reasons": reasons, "missing": missing, "insufficient": insufficient,
            "families": families, "rain_coverage": f"{len(rain_live)}/{len(rain_all)}",
            "obs_coverage": cov}


def apply_hysteresis(proposed: str, state: dict, key: str = "level", *,
                     insufficient: bool = False, hold: str | None = None) -> tuple[str, str]:
    cur = state.get(key, "quiet")
    dkey = f"{key}_pending_down" if key != "level" else "pending_down"
    rp, rc = LEVELS.index(proposed), LEVELS.index(cur)
    if rp > rc:
        state.update({key: proposed, dkey: 0})
        return proposed, f"ESCALADA {cur}→{proposed}"
    if rp == rc:
        state[dkey] = 0
        return cur, "estable"
    if insufficient:
        return cur, f"retenido en {cur}: cobertura insuficiente, no se desescala"
    if hold:
        state[dkey] = 0
        return cur, f"retenido en {cur}: {hold} (no se desescala mientras dure)"
    state[dkey] = state.get(dkey, 0) + 1
    if state[dkey] >= CFG["deescalate_cycles"]:
        new = LEVELS[rc - 1]
        state.update({key: new, dkey: 0})
        return new, f"desescalada {cur}→{new} tras {CFG['deescalate_cycles']} ciclos"
    return cur, f"retenido en {cur} ({state[dkey]}/{CFG['deescalate_cycles']} ciclos hacia {proposed})"


# ════════════════════════════════════════════════════════════════════════
# GOBERNANZA — marco Ante Agency Agents (doctrina + contrato NEXUS)
#   · Estados epistémicos tipados por afirmación, con raíz de fuente, alcance y caducidad.
#   · La desescalada es una DECISIÓN (PROCEED / HOLD) con condiciones abiertas nombradas.
#   · Retador (challenger) con veto: dBZ bajo no autoriza bajar sin pluviómetro de otra raíz.
#   · Disenso registrado; el abierto bloquea bajar a quiet y cerrar el episodio.
#   · Predicciones falsables congeladas; el resultado se anota aparte y nunca reescribe la predicción.
#   · Anomalías: no se normalizan en silencio; retienen hasta revisión explícita.
#   · Sin auto-aceptación: el motor PROPONE el cierre; lo acepta el propietario.
# ════════════════════════════════════════════════════════════════════════
EPISTEMIC = ("EVIDENCE", "HYPOTHESIS", "ASSUMPTION", "UNKNOWN")
DECISIONS = ("PROCEED", "PROCEED_WITH_CONDITIONS", "HOLD", "REDESIGN", "REJECT")
PHASES = ("ACTIVE", "CESSATION", "TRANSITION", "CLOSURE_PROPOSED", "CLOSED")
# Raíz de fuente: dos canales con la misma raíz NO son independientes (METAR LEIB y la estación
# B954 son el mismo observatorio de AEMET; MeteoAlarm reemite el CAP de AEMET).
CHANNEL_ROOT = {
    "aviso_aemet": "aemet", "aviso_aemet_activo": "aemet", "lluvia_observada": "aemet",
    "escorrentia_torrentes": "aemet", "frente_racha": "aemet", "radar": "rainviewer",
    "rayos": "eumetsat", "pluviometros": "meteoclimatic", "mar_boyas": "puertos_estado",
    "viento_estaciones": "puertos_estado", "trayectoria_nucleo": "nwp", "ensemble_ecmwf": "nwp",
    "mar_bahia": "nwp", "manual": "owner"}


HAZARD_FAMILY = {"lluvia_observada": "lluvia", "pluviometros": "lluvia", "radar": "lluvia",
                 "escorrentia_torrentes": "lluvia", "rayos": "lluvia", "frente_racha": "viento",
                 "viento_estaciones": "viento", "mar_boyas": "mar"}


def channel_root(name: str) -> str:
    return CHANNEL_ROOT.get(name) or ("nwp" if name.startswith("modelo") else name)


@dataclass
class Claim:
    id: str
    text: str
    epistemic: str                      # EVIDENCE | HYPOTHESIS | ASSUMPTION | UNKNOWN
    source_root: str
    scope: str                          # dónde y cuándo vale
    expires: str                        # ISO UTC
    label: str = ""                     # OFFICIAL | PROXY | RADAR_ESTIMATE | MODEL_ESTIMATE | OWNER

    def __post_init__(self):
        if self.epistemic not in EPISTEMIC:
            raise ValueError(f"estado epistémico inválido: {self.epistemic}")
        # Un modelo (o una estimación derivada) nunca es observación.
        if self.epistemic == "EVIDENCE" and (self.source_root == "nwp" or
                                             self.label in ("MODEL_ESTIMATE", "RADAR_ESTIMATE", "PROXY")):
            raise ValueError(f"{self.id}: {self.label or self.source_root} no puede ser EVIDENCE")


def build_claims(issued: datetime, channels: list[Channel], warnings: list[dict], manual: dict,
                 official_verified: bool) -> list[Claim]:
    out: list[Claim] = []
    exp_obs = (issued + timedelta(minutes=20)).isoformat()
    # 1. Aviso oficial: EVIDENCIA de que el aviso existe (no del fenómeno), vale hasta su 'expires'.
    if not official_verified:
        out.append(Claim("C-OFF", "estado del aviso oficial para la zona 645301", "UNKNOWN", "aemet",
                         "Ibiza y Formentera", exp_obs))
    for i, w in enumerate(w for w in warnings if w.get("activo_ahora")):
        out.append(Claim(f"C-OFF{i}", f"AEMET mantiene aviso {w['nivel']} ({w.get('tipo', '?')}): {w['evento']} — "
                                      f"{w.get('descripcion') or w.get('parametro', '')}"[:200],
                         "EVIDENCE", "aemet", w.get("area") or "zona 645301", w.get("expires") or exp_obs, "OFFICIAL"))
    # 2. Canales
    for c in channels:
        root = channel_root(c.name)
        if c.kind == "institutional":
            continue
        if not c.available:
            out.append(Claim(f"C-{c.name}", f"{c.name}: sin dato (ausencia ≠ calma)", "UNKNOWN", root,
                             "Portinatx", exp_obs))
            continue
        head = c.evidence[0] if c.evidence else ""
        if c.kind in ("model", "ensemble"):
            out.append(Claim(f"C-{c.name}", f"{c.name} → {LEVELS[c.level]}: {head}"[:200], "HYPOTHESIS", root,
                             "Portinatx ±20–100 km y ±3 h (error de posición/hora convectivo)",
                             (issued + timedelta(hours=3)).isoformat(), "MODEL_ESTIMATE"))
            continue
        out.append(Claim(f"C-{c.name}", f"{c.name} observa {LEVELS[c.level]}: {head}"[:200], "EVIDENCE", root,
                         "donde está el sensor (ver evidencia)", exp_obs))
        if c.level and not c.local:
            out.append(Claim(f"C-{c.name}-attr", f"lo observado por {c.name} afecta igual a Portinatx",
                             "HYPOTHESIS", root, "Portinatx", exp_obs, "PROXY"))
        if c.name == "radar" and c.metrics.get("qpe_now"):
            q = c.metrics["qpe_now"]
            out.append(Claim("C-radar-qpe", "QPE radar en el punto: " + " · ".join(f"{k} {v:.1f} mm/h" for k, v in q.items()),
                             "HYPOTHESIS", root, f"≤{CFG['qpe_radius_km']:.0f} km de Portinatx", exp_obs, "RADAR_ESTIMATE"))
    for k, v in manual.items():
        if k == "es_alert":
            out.append(Claim("C-es-alert", f"Protección Civil (112) mantiene ES-Alert: {v['value']} (registrada hace {v['edad_h']} h)",
                             "EVIDENCE", "proteccion_civil", "isla de Ibiza",
                             (parse_time(v["t"]) + timedelta(hours=CFG["manual_obs_ttl_h"])).isoformat(), "OFFICIAL"))
            continue
        out.append(Claim(f"C-man-{k}", f"propietario: {k}={v['value']} (hace {v['edad_h']} h)", "EVIDENCE", "owner",
                         "Cala de Portinatx", (parse_time(v["t"]) + timedelta(hours=CFG["manual_obs_ttl_h"])).isoformat(),
                         "OWNER"))
    out.append(Claim("C-ass-thr", "los umbrales del motor (mm/h, dBZ, Hs, rachas) son de partida, no calibrados",
                     "ASSUMPTION", "engine", "todo el motor", (issued + timedelta(days=365)).isoformat()))
    return out


def sea_model_check(sea_obs: Channel, marine: SourceResult | None, portus: SourceResult | None) -> None:
    """DANA 18–19/10: el oleaje modelizado (1,7 m) quedó muy por debajo de las boyas (3,5–4,1 m).
    Si la boya NE más alta supera 1,5× el máximo del modelo, se marca: manda la observación."""
    if not (sea_obs.available and marine and marine.status == "ok"
            and portus and portus.status == "ok"):
        return
    mod = max((x or 0) for x in marine.payload.get("wave_height") or [0])
    obs = 0.0
    for name in CFG["portus_buoys"].values():
        ser = [r for r in portus.payload["stations"].get(name, [])
               if r.get("hm0") is not None
               and observation_recency(r.get("t"), CFG["channel_max_age_min"]["mar_boyas"]
                                       )["freshness"] == "FRESH"]
        if ser and ser[-1].get("dmd") is not None and in_sector(ser[-1]["dmd"], (330.0, 100.0)):
            obs = max(obs, ser[-1]["hm0"])
    sea_obs.metrics.update({"buoy_hs_ne": obs, "model_hs_max": mod})
    if mod and obs > 1.5 * mod:
        sea_obs.evidence.insert(0, f"⚠ el oleaje modelizado (máx {mod:.1f} m) infraestima: boyas del NE con {obs:.1f} m "
                                   "— manda la observación y el aviso costero")


def radar_coverage_check(radar: Channel, gauges: Channel, rain: Channel) -> None:
    """Radar mudo cerca mientras un pluviómetro cercano mide lluvia → hueco de cobertura, no 'sin lluvia'."""
    if not radar.available:
        return
    near = radar.metrics.get("nearest_km")
    mute = near is None or near > 30
    g_rate = gauges.metrics.get("near_rate_max") if gauges.available else None
    b_r1 = rain.metrics.get("B908X_r1") if rain.available else None
    wet = [f"{n} {v:.1f} mm/h" for n, v in (("pluviómetro vecino", g_rate), ("B908X", b_r1))
           if v is not None and v >= CFG["coverage_gap_rate"]]
    if mute and wet:
        radar.available = False
        radar.metrics["coverage_gap"] = True
        radar.evidence.insert(0, f"⚠ HUECO DE COBERTURA: radar sin eco a ≤30 km mientras mide lluvia "
                                 f"({', '.join(wet)}) → radar UNKNOWN, no 'sin lluvia'")


def active_overrides(state: dict, now: datetime) -> dict:
    out = {}
    for code, v in (state.get("overrides") or {}).items():
        t = parse_time(v.get("t"))
        if t and now - t <= timedelta(hours=CFG["override_ttl_h"]):
            out[code] = v
    return out


def open_dissent(state: dict) -> list[dict]:
    return [d for d in state.get("dissent", []) if d.get("status") == "OPEN"]


def open_anomalies(state: dict, now: datetime) -> list[dict]:
    return [a for a in state.get("anomalies", []) if not a.get("reviewed")
            and now - parse_time(a["t"]) <= timedelta(hours=CFG["anomaly_hold_h"])]


def deescalation_decision(current: str, proposed: str, *, gauges: Channel | None, radar: Channel | None,
                          official: dict, manual_hold: str | None, insufficient: bool,
                          dissent: list[dict], anomalies: list[dict], overrides: dict) -> dict:
    """Bajar la precaución es una decisión con condiciones, no un efecto colateral del radar."""
    cur, pro = LEVELS.index(current), LEVELS.index(proposed)
    res = {"from": current, "to": proposed, "decision": "PROCEED", "open_conditions": [],
           "challenger": None, "overridden": []}
    if pro >= cur:
        return res
    conds = []
    off = official.get("level_now", "unknown")
    if off == "unknown":
        conds.append(("OFFICIAL_UNVERIFIED", "PENDING_EVIDENCE", "estado del aviso oficial no verificado"))
    elif LEVELS.index(off) > pro:
        conds.append(("OFFICIAL_FLOOR", "FATAL_DEFECT", f"{proposed} quedaría por debajo del aviso oficial vigente ({off})"))
    if manual_hold:
        conds.append(("LOCAL_HAZARD_OBSERVED", "PENDING_EVIDENCE", manual_hold))
    if insufficient:
        conds.append(("COVERAGE", "PENDING_EVIDENCE",
                      "cobertura insuficiente: menos de 2 canales observados vivos o familia lluvia sin dato"))
    if radar is not None and radar.metrics.get("coverage_gap"):
        conds.append(("RADAR_COVERAGE_GAP", "PENDING_EVIDENCE", "radar mudo con lluvia medida cerca"))
    if dissent and pro == 0:
        conds.append(("OPEN_DISSENT", "PENDING_EVIDENCE", f"disenso abierto: {', '.join(d['id'] for d in dissent)}"))
    if anomalies:
        conds.append(("ANOMALY_UNREVIEWED", "PENDING_EVIDENCE",
                      "anomalía sin revisar: " + "; ".join(f"{a['id']} {a['text']}" for a in anomalies)[:200]))
    if cur >= 2:
        # Retador: la bajada desde alert/alarm exige pluviómetro VECINO y FRESCO, de raíz distinta
        # del radar y de los modelos, que no contradiga la bajada. dBZ bajo ≠ lluvia baja (F2, 10:25).
        g_ok = bool(gauges and gauges.available and gauges.metrics.get("near_fresh", 0) > 0
                    and gauges.metrics.get("near_rate_max") is not None and gauges.level <= pro)
        res["challenger"] = {
            "role": "challenger (assurance)", "verdict": "NO_OBJECTION" if g_ok else "VETO",
            "reason": ("pluviómetro vecino fresco con intensidad medida compatible con la bajada" if g_ok else
                       "bajada sin confirmación pluviométrica vecina fresca (intensidad medida entre ciclos): "
                       "el radar o el modelo no bastan — sustitución de métrica")}
        if not g_ok:
            conds.append(("CHALLENGER_VETO", "PENDING_EVIDENCE", res["challenger"]["reason"]))
    kept = []
    for code, kind, text in conds:
        if kind != "FATAL_DEFECT" and code in overrides:       # el suelo oficial no admite override
            res["overridden"].append({"code": code, **overrides[code]})
        else:
            kept.append({"code": code, "kind": kind, "text": text})
    res["open_conditions"] = kept
    if kept:
        res["decision"] = "HOLD"
    elif res["overridden"]:
        res["decision"] = "PROCEED_WITH_CONDITIONS"
    return res


# ── predicciones falsables ──
def _pred_sha(p: dict) -> str:
    body = {k: p[k] for k in ("id", "made", "window_end", "claim", "criterion")}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:12]


def make_predictions(state: dict, issued: datetime, gauges: Channel, decision: dict) -> list[dict]:
    preds = state.setdefault("predictions", [])
    pending = {p["criterion"]["station"] for p in preds if p["outcome"] is None}   # una abierta por estación
    new = []
    if not gauges.available:
        return new
    near = [s for s in gauges.metrics.get("stations", []) if s["near"]]
    wet_near = any((s["rate"] or 0) >= CFG["pred_rise_rate"] for s in near)
    for s in near:
        kind = None
        if (s["rate"] or 0) >= CFG["pred_rise_rate"]:
            kind, crit = "rise", {"min_delta": CFG["pred_rise_mm"]}
            txt = f"{s['nombre']} sumará ≥{CFG['pred_rise_mm']:.0f} mm en {CFG['pred_window_min']} min (la lluvia sigue)"
        elif not wet_near and decision.get("to") and LEVELS.index(decision["to"]) < LEVELS.index(decision["from"]):
            kind, crit = "cease", {"max_delta": CFG["pred_cease_mm"]}
            txt = f"{s['nombre']} sumará <{CFG['pred_cease_mm']:.0f} mm en {CFG['pred_window_min']} min (la bajada es correcta)"
        if not kind or s["id"] in pending:
            continue
        p = {"id": f"P{len(preds) + 1}", "made": issued.isoformat(), "kind": kind,
             "window_end": (issued + timedelta(minutes=CFG["pred_window_min"])).isoformat(), "claim": txt,
             "criterion": {"station": s["id"], "base_total": s["total"], "base_t": s["t"], **crit}, "outcome": None}
        p["sha"] = _pred_sha(p)
        preds.append(p)
        new.append(p)
    del preds[:-200]
    return new


def verify_predictions(state: dict, now: datetime) -> list[dict]:
    """Verifica contra el último total diario visto; anota el resultado en 'outcome' (la predicción no se toca)."""
    done = []
    gh = state.get("gauge_hist", {})
    for p in state.get("predictions", []):
        if p["outcome"] is not None:
            continue
        end = parse_time(p["window_end"])
        if now < end:
            continue
        cr = p["criterion"]
        base_day = parse_time(cr["base_t"]).astimezone(MADRID).date()
        # Solo vale una lectura en la banda [cierre −10, cierre +tol] del mismo día: una lectura posterior
        # acumula lluvia de fuera de la ventana y no puede ni confirmar ni refutar.
        band = [r for r in gh.get(cr["station"], [])
                if end - timedelta(minutes=10) <= parse_time(r["t"]) <= end + timedelta(minutes=CFG["pred_tol_min"])
                and parse_time(r["t"]).astimezone(MADRID).date() == base_day]
        g = min(band, key=lambda r: abs((parse_time(r["t"]) - end).total_seconds())) if band else None
        if g:
            delta = g["total"] - cr["base_total"]
            hit = delta >= cr["min_delta"] if "min_delta" in cr else delta < cr["max_delta"]
            p["outcome"] = {"status": "HIT" if hit else "MISS", "delta_mm": round(delta, 1), "at": g["t"]}
            done.append(p)
            if not hit and p["kind"] == "cease":
                state.setdefault("anomalies", []).append(
                    {"id": f"A{len(state.get('anomalies', [])) + 1}", "t": now.isoformat(), "reviewed": False,
                     "text": f"{p['id']} refutada: la bajada se contradijo con +{delta:.1f} mm en la ventana"})
        elif now >= end + timedelta(minutes=CFG["pred_tol_min"]):
            p["outcome"] = {"status": "UNVERIFIABLE",
                            "reason": "sin lectura del mismo día en la banda de cierre de la ventana (motor no ciclando)"}
            done.append(p)
    return done


def prediction_summary(state: dict) -> dict:
    cnt = {"PENDING": 0, "HIT": 0, "MISS": 0, "UNVERIFIABLE": 0, "WITHDRAWN": 0}
    for p in state.get("predictions", []):
        cnt[p["outcome"]["status"] if p["outcome"] else "PENDING"] += 1
    return cnt


# ── sesgo radar–pluviómetro: se mide y se avisa; NUNCA cambia la relación Z–R sola ──
def grid_dbz_at(grid_b64: str, lat: float, lon: float, r: int = 1) -> float | None:
    """dBZ máximo de la rejilla de la app en una ventana (2r+1)² alrededor de lat/lon (≈±2,5 km con r=1)."""
    import base64
    rg = CFG["radar_grid"]
    nlat = int(round(2 * rg["dlat"] / rg["step"])) + 1
    nlon = int(round(2 * rg["dlon"] / rg["step"])) + 1
    i = int(round((SITE["lat"] + rg["dlat"] - lat) / rg["step"]))
    j = int(round((lon - (SITE["lon"] - rg["dlon"])) / rg["step"]))
    if not (0 <= i < nlat and 0 <= j < nlon):
        return None
    g = base64.b64decode(grid_b64)
    vals = [g[a * nlon + b] for a in range(max(0, i - r), min(nlat, i + r + 1))
            for b in range(max(0, j - r), min(nlon, j + r + 1))]
    vals = [v for v in vals if v >= 2]
    return float(max(vals)) if vals else 0.0


def annotate_gauges_radar(gauges: Channel, src: SourceResult | None) -> None:
    """Radar en el sitio de cada pluviómetro (no en Portinatx): elimina el desajuste espacial de 8 km."""
    if not (src and src.status == "ok" and gauges.available):
        return
    fr = [f for f in src.payload["frames"] if f.get("grid")]
    if not fr:
        return
    for s in gauges.metrics.get("stations", []):
        if s.get("lat") is None:
            continue
        d = grid_dbz_at(fr[-1]["grid"], s["lat"], s["lon"])
        if d is not None:
            s["radar_dbz"] = d
            s["radar_qpe"] = {k: zr_rate(d, a, b) for k, (a, b) in CFG["zr"].items()}


def update_bias(state: dict, issued: datetime, radar: Channel, gauges: Channel) -> dict:
    pairs = state.setdefault("bias_pairs", [])
    q0 = radar.metrics.get("qpe_now") if radar.available else None
    near = [s for s in (gauges.metrics.get("stations", []) if gauges.available else [])
            if s["near"] and s["rate"] is not None]
    seen = {(p.get("station"), p.get("reading")) for p in pairs}
    for s in near:
        q = s.get("radar_qpe") or q0           # radar en el pluviómetro si existe; si no, en el punto
        if (s["nombre"], s["t"]) in seen:      # la misma lectura no se cuenta dos veces
            continue
        if q and max(s["rate"], *q.values()) >= 0.5:
            pairs.append({"t": issued.isoformat(), "reading": s["t"], "gauge": round(s["rate"], 1), "station": s["nombre"],
                          "dist_km": round(s["dist_km"], 1), "at": "pluviometro" if s.get("radar_qpe") else "punto",
                          **{k: round(v, 1) for k, v in q.items()}})
    del pairs[:-100]
    out = {"n": len(pairs), "note": "radar muestreado en cada pluviómetro vecino (±2,5 km): indicativo, no calibración"}
    # Razón solo con lluvia en ambos (≥1 mm/h) y radar muestreado en el pluviómetro; los desacuerdos de
    # detección (uno llueve, el otro no) se cuentan aparte: son error de posición, no de Z–R.
    good = [p for p in pairs if p.get("at") == "pluviometro"]
    out["n_detect_mismatch"] = sum(1 for p in good if (p["gauge"] >= 1) != (max(p.get(k, 0) for k in CFG["zr"]) >= 1))
    for k in CFG["zr"]:
        r = sorted(p["gauge"] / p[k] for p in good if p.get(k, 0) >= 1 and p["gauge"] >= 1)
        if r:
            out[f"ratio_{k}"] = round(r[len(r) // 2], 2)
            out[f"n_{k}"] = len(r)
    mp = out.get("ratio_marshall_palmer")
    if mp is not None and out.get("n_marshall_palmer", 0) >= CFG["bias_min_n"] and \
            (mp > CFG["bias_hi"] or mp < CFG["bias_lo"]):
        out["flag"] = (f"REVISAR Z–R: pluviómetro/Marshall–Palmer mediana {mp}× en n={out['n_marshall_palmer']} — "
                       "revisión humana; el motor no cambia de relación por sí mismo")
    return out


# ── cambios de aviso oficial ──
def detect_warning_changes(state: dict, warnings: list[dict], now: datetime) -> list[dict]:
    seen = state.setdefault("warn_seen", {})
    changes = []
    for w in warnings:
        if not w.get("onset"):
            continue
        sig = f"{w['nivel']}|{w.get('tipo', '')}|{w['onset']}|{w['expires']}"
        if sig not in seen:
            seen[sig] = now.isoformat()
            changes.append({"kind": "NUEVO", "nivel": w["nivel"], "tipo": w.get("tipo", ""), "evento": w["evento"],
                            "onset": w["onset"], "expires": w["expires"], "id": w.get("id", "")})
    act = max((w["rank"] for w in warnings if w.get("activo_ahora")), default=0)
    first = "official_rank_now" not in state
    prev = state.get("official_rank_now", 0)
    if first:
        changes.insert(0, {"kind": "INICIAL", "de": "—", "a": LEVELS[act]})
    elif act > prev:
        changes.insert(0, {"kind": "ESCALADA", "de": LEVELS[prev], "a": LEVELS[act]})
    elif act < prev:
        changes.insert(0, {"kind": "DESCENSO", "de": LEVELS[prev], "a": LEVELS[act]})
    state["official_rank_now"] = act
    for sig in list(seen):
        exp = parse_time(sig.split("|")[3])
        if exp and exp < now - timedelta(days=1):
            del seen[sig]
    return changes


def notify(changes: list[dict], cid: str) -> str:
    """Registra en alerts.jsonl y, si NTFY_URL está definido, envía un push. Nunca bloquea el ciclo."""
    if not changes:
        return ""
    HOME.mkdir(parents=True, exist_ok=True)
    with open(HOME / "alerts.jsonl", "a") as fh:
        fh.write(json.dumps({"cycle": cid, "changes": changes}, ensure_ascii=False) + "\n")
    url = os.environ.get("NTFY_URL", "")
    if not url:
        return "registrado (sin NTFY_URL)"
    txt = "; ".join(f"{c['kind']} {c.get('nivel') or c.get('a')} {c.get('evento', '')}" for c in changes)[:900]
    try:
        req = urllib.request.Request(url, data=txt.encode(), headers={"Title": "Portinatx: cambio de aviso",
                                                                      "Priority": "high"})
        urllib.request.urlopen(req, timeout=10)
        return "notificado"
    except Exception as exc:
        return f"push falló: {exc}"


# ── fases del episodio ──
def episode_update(state: dict, now: datetime, official: dict, precaution: str, hazard: dict,
                   blockers: list[str], conservation: dict) -> dict:
    ep = state.get("episode")
    rk = lambda lv: -1 if lv == "unknown" else LEVELS.index(lv)
    off_now, off_36 = rk(official["level_now"]), rk(official["level_36h"])
    haz = any(v.get("estado") == "OBSERVED" and v.get("nivel") in ("alert", "alarm") for v in hazard.values())
    prec = LEVELS.index(precaution)
    if ep is None or ep["phase"] == "CLOSED":
        if off_36 >= 1 or prec >= 1 or haz:
            ep = {"id": f"EP-{now:%Y%m%dT%H%MZ}", "opened": now.isoformat(), "phase": "ACTIVE", "history": []}
            if state.get("episode"):
                ep["previous"] = state["episode"]["id"]
        else:
            return ep or {}
    if off_now == -1 or off_36 == -1:
        phase = ep["phase"] if ep["phase"] != "CLOSURE_PROPOSED" else "CESSATION"   # sin aviso verificado no se cierra
    elif haz or prec >= 2 or off_now >= 1:
        phase = "ACTIVE"
    elif off_36 >= 1:
        phase = "TRANSITION"                       # sin aviso ahora, pero hay otro en las próximas 36 h
    elif prec >= 1 or blockers:
        phase = "CESSATION"
    else:
        phase = "CLOSURE_PROPOSED"                 # sin auto-aceptación: lo acepta el propietario
    if ep.get("accepted") and phase == "CLOSURE_PROPOSED":
        phase = "CLOSED"
    if phase != ep["phase"]:
        ep["history"].append({"t": now.isoformat(), "from": ep["phase"], "to": phase})
        del ep["history"][:-30]
    ep["phase"] = phase
    ep["closure_blockers"] = blockers
    if phase in ("CLOSURE_PROPOSED", "CLOSED"):
        ep["closure_record"] = {
            "achieved": "sin aviso oficial en 36 h, precaución en quiet, sin peligro local observado",
            "outstanding": blockers,
            "accountable": "propietario (Javier): acepta el cierre con --close-episode; el motor no se auto-acepta",
            "on_breach": "nuevo aviso o peligro observado → episodio nuevo enlazado a este",
            "conservation": conservation}
    if phase not in ("CLOSURE_PROPOSED", "CLOSED"):
        ep.pop("accepted", None)                   # una aceptación vieja no cierra un episodio reactivado
    state["episode"] = ep
    return ep


# ════════════════════════════════════════════════════════════════════════
# CICLO
# ════════════════════════════════════════════════════════════════════════
SOURCES = [
    ("metar", "obs", src_metar), ("aemet_obs", "obs", src_aemet_obs),
    ("aemet_cap", "institutional", src_aemet_cap), ("meteoalarm", "institutional", src_meteoalarm),
    ("wu_pws", "obs", src_wu),
    ("socib_boya", "obs", src_socib), ("radar", "obs", src_radar),
    ("rayos_mtg_li", "obs", src_lightning),
    ("meteoclimatic", "obs", src_meteoclimatic),
    ("portus", "obs", cached_source("portus", 20, src_portus)),
    ("openmeteo_det", "model", cached_source("openmeteo_det", 15, src_openmeteo_det)),
    ("openmeteo_ens", "ensemble", cached_source("openmeteo_ens", 60, src_openmeteo_ens)),
    ("marine", "model", cached_source("marine", 60, src_marine)),
    ("model_grid", "model", src_model_grid),         # caché propia: solo con run nuevo
    ("perfil", "model", cached_source("perfil", 60, lambda: src_profile())),
    ("satelite", "obs", cached_source("satelite", 10, lambda: src_satellite())),
    ("modelos_pluvio", "model", cached_source("modelos_pluvio", 60, lambda: src_gauge_models())),
    ("relieve", "obs", cached_source("relieve", 60 * 24 * 30, lambda: src_terrain())),
    ("batimetria", "obs", cached_source("batimetria", 60 * 24 * 30, lambda: src_bathy())),
    ("modelos_x", "model", cached_source("modelos_x", 60, lambda: src_models_x())),
    ("superensemble", "ensemble", cached_source("superensemble", 120, lambda: src_superens())),
    ("mar_modelos", "model", cached_source("mar_modelos", 60, lambda: src_marine_x())),
    ("radar_hf", "obs", cached_source("radar_hf", 30, lambda: src_hfradar())),
    ("forense_modelos", "model", cached_source("forense_modelos", 180, lambda: src_forensic_models())),
    ("forense_mar", "model", cached_source("forense_mar", 180, lambda: src_forensic_marine())),
    ("forense_malla", "model", cached_source("forense_malla", 180, lambda: src_forensic_grid())),
    # Contexto de un sidecar opcional (climatología, SST, nieve, scores). kind='context': NO entra en la fusión.
    ("contexto", "context", lambda: src_contexto()),
]


def cycle(state: dict) -> dict:
    issued = now_utc()
    srcs = {n: run_source(n, k, f) for n, k, f in SOURCES}
    rain = ch_rain_obs(srcs)
    g = srcs.get("model_grid")
    tracks = update_run_tracks(state, g.payload) if g and g.status == "ok" else None
    traj, hr_gate = ch_trajectory(tracks, g.data_time if g else None)
    gauges = ch_gauges(srcs.get("meteoclimatic"), state)
    archived = update_ledgers(state, srcs)                       # archivo propio de observaciones (forense)
    radar = ch_radar(srcs.get("radar"))
    light = ch_lightning(srcs.get("rayos_mtg_li"))
    wind = ch_wind_obs(srcs.get("portus"))
    sea_obs = ch_sea_obs(srcs.get("portus"))
    runoff, gustfront = ch_runoff(srcs, rain), ch_gustfront(srcs)
    forecast = [traj, *ch_models(srcs.get("openmeteo_det")), ch_ensemble(srcs.get("openmeteo_ens")),
                ch_sea(srcs.get("marine"))]
    # #16: lo caducado o sin hora pasa a UNKNOWN antes de cualquier comprobación o fusión
    apply_freshness([rain, gauges, runoff, gustfront, radar, light, wind, sea_obs, *forecast], issued)
    radar_coverage_check(radar, gauges, rain)
    sea_model_check(sea_obs, srcs.get("marine"), srcs.get("portus"))                     # F7: radar mudo con lluvia medida
    observed = [rain, gauges, runoff, gustfront, radar, light, wind, sea_obs]
    manual = manual_obs(state, issued)
    inst_all = ch_institutional(srcs["aemet_cap"], srcs.get("meteoalarm"))
    inst_now = ch_institutional(srcs["aemet_cap"], srcs.get("meteoalarm"), active_only=True)
    cid = f"NWC-{issued:%Y%m%dT%H%M%SZ}"
    # ── EJE 1: AVISO OFICIAL (se informa tal cual; sin histéresis, caduca con el CAP) ──
    warns = []
    for nm in ("aemet_cap", "meteoalarm"):
        sr = srcs.get(nm)
        if sr and sr.status == "ok":
            warns += sr.payload["warnings"]
    if MANUAL_FLOOR:
        warns.append(MANUAL_FLOOR)
    official = official_state(inst_now, inst_all, warns)
    changes = detect_warning_changes(state, warns, issued)          # F1: un cambio de aviso no puede pasar callado
    notified = notify(changes, cid)
    # ── EJE 2: PELIGRO LOCAL OBSERVADO ──
    hazard = local_hazard_state({"lluvia_pluviometros": gauges, "lluvia_metar_aemet": rain, "radar": radar,
                                 "rayos": light, "viento": wind, "mar": sea_obs}, manual)
    # ── EJE 3: PRECAUCIÓN OPERATIVA (nowcast + decisión de desescalada gobernada) ──
    fz_now = fuse([inst_now, *observed])
    fz_out = fuse([inst_all, *observed, *forecast], hr_gate)
    hold = precaution_hold(manual)
    if manual.get("flooding", {}).get("value") == "observed":
        fz_now["proposed"] = "alarm"
        fz_now["reasons"].insert(0, "anegamiento observado (manual) → alarm")
    elif manual.get("es_alert", {}).get("value") == "active":
        # ES-Alert de Protección Civil (112): autoridad de emergencias, raíz distinta de AEMET.
        fz_now["proposed"] = "alarm"
        fz_now["reasons"].insert(0, "ES-Alert de Protección Civil (112) vigente, registrada por el propietario → alarm")
    elif manual.get("runoff", {}).get("value") == "observed" and LEVELS.index(fz_now["proposed"]) < 2:
        fz_now["proposed"] = "alert"
        fz_now["reasons"].insert(0, "escorrentía observada (manual) → al menos alert")
    verified = verify_predictions(state, issued)
    overrides = active_overrides(state, issued)
    dissent = open_dissent(state)
    anomalies = open_anomalies(state, issued)
    decision = deescalation_decision(state.get("nowcast_level", "quiet"), fz_now["proposed"], gauges=gauges,
                                     radar=radar, official=official, manual_hold=hold,
                                     insufficient=fz_now["insufficient"], dissent=dissent,
                                     anomalies=anomalies, overrides=overrides)
    hold_txt = "; ".join(f"{c['code']}" for c in decision["open_conditions"]) or None
    now_lvl, now_tr = apply_hysteresis(fz_now["proposed"], state, "nowcast_level", hold=hold_txt)
    new_preds = make_predictions(state, issued, gauges, decision)
    annotate_gauges_radar(gauges, srcs.get("radar"))
    bias = update_bias(state, issued, radar, gauges)
    exit_cond = [f"aviso oficial vigente ≤ {LEVELS[max(0, LEVELS.index(now_lvl) - 1)]}",
                 "sin peligro local observado ≥ nivel actual en 3 ciclos seguidos",
                 f"≥{CFG['min_obs_channels']} canales observados vivos y ≥1 por familia "
                 f"{'/'.join(CFG['required_families'])} (ahora {fz_now['obs_coverage']})",
                 f"sin escorrentía/anegamiento observados en las últimas {CFG['manual_obs_ttl_h']} h",
                 "pluviómetro vecino fresco que no contradiga la bajada desde alert/alarm (retador)",
                 "sin disenso abierto (para bajar a quiet) ni anomalías sin revisar"]
    final, transition = apply_hysteresis(fz_out["proposed"], state, insufficient=fz_out["insufficient"])
    claims = build_claims(issued, [*observed, *forecast], warns, manual, official["verificado"])
    psum = prediction_summary(state)
    blockers = ([f"disenso {d['id']}" for d in dissent] + [f"anomalía {a['id']}" for a in anomalies]
                + ([f"{psum['PENDING']} predicciones pendientes"] if psum["PENDING"] else [])
                + ([hold] if hold else []))
    episode = episode_update(state, issued, official, now_lvl, hazard, blockers,
                             {"bias": bias, "anomalies": state.get("anomalies", [])[-10:],
                              "overrides": overrides, "predictions": psum})
    state["last_issued"] = issued.isoformat()
    ecount = {e: sum(1 for c in claims if c.epistemic == e) for e in EPISTEMIC}
    return {"cycle_id": cid, "issued_utc": issued.isoformat(), "engine": VERSION, "site": SITE,
            "level": final, "proposed": fz_out["proposed"], "transition": transition,
            "reasons": fz_out["reasons"], "missing": fz_out["missing"], "coverage": fz_out["obs_coverage"],
            "nowcast": {"level": now_lvl, "proposed": fz_now["proposed"], "transition": now_tr,
                        "insufficient": fz_now["insufficient"], "rain_coverage": fz_now["rain_coverage"],
                        "reasons": fz_now["reasons"]},
            "warning_changes": changes, "notify": notified,
            "official_warning": official, "observed_local_hazard": hazard,
            "operational_precaution": {"level": now_lvl, "transition": now_tr, "hold": hold,
                                       "insufficient": fz_now["insufficient"], "rain_coverage": fz_now["rain_coverage"],
                                       "decision": decision, "exit_conditions": exit_cond,
                                       "note": "precaución propia; NO prolonga la vigencia del aviso oficial"},
            "governance": {"framework": "Ante Agency Agents (doctrina + contrato NEXUS)",
                           "claims_count": ecount, "claims": [asdict(c) for c in claims],
                           "dissent_open": dissent, "anomalies_open": anomalies, "overrides": overrides,
                           "predictions": {"summary": psum, "new": new_preds, "verified": verified},
                           "bias_radar_gauge": bias, "episode": episode},
            "channels": [asdict(c) for c in [inst_all, inst_now, *observed, *forecast]],
            "context": context_notes(srcs.get("contexto"), rain),
            "sources": [{**{k: v for k, v in asdict(s).items() if k != "payload"},
                         **marine_source_recency(s, issued)} for s in srcs.values()],
            "_srcs": srcs, "_forense": {**forensic_bundle(state, srcs, None), "archivado_ciclo": archived}}


def render(snap: dict) -> str:
    L = []
    L.append(f"━━ {snap['cycle_id']} · PORTINATX DEGEN {snap['engine']} ━━")
    for c in snap.get("warning_changes") or []:
        if c["kind"] == "INICIAL":
            L.append(f"ℹ  primer ciclo con registro de avisos: nivel oficial vigente {c['a']} (no es un cambio)")
        elif c["kind"] in ("ESCALADA", "DESCENSO"):
            L.append(f"⚠⚠ CAMBIO DE AVISO OFICIAL: {c['kind']} {c['de']}→{c['a']}  [{snap.get('notify', '')}]")
        else:
            L.append(f"⚠  aviso nuevo en el feed: {c['nivel'].upper()} {c['tipo']} · {c['evento']} · "
                     f"{c['onset'][:16]}→{c['expires'][:16]}")
    ow = snap.get("official_warning")
    if ow:
        v = ow["vigente"]
        em = EMOJI.get(ow["level_now"], "✖")
        if v:
            for w in ow.get("vigentes") or [v]:
                on, ex = parse_time(w["desde"]), parse_time(w["hasta"])
                span = f"{on.astimezone(MADRID):%d %H:%M}→{ex.astimezone(MADRID):%d %H:%M}" if on and ex else "manual"
                L.append(f"{em}  AVISO OFICIAL        {w['nivel'].upper()} {w.get('tipo', '')} · {w['evento']} · "
                         f"{span} local · {w['umbral'][:90]}")
        else:
            L.append(f"{em}  AVISO OFICIAL        {'ninguno vigente' if ow['verificado'] else 'NO VERIFICADO'} "
                     f"(próximas 36 h: {ow['level_36h']})")
        hz = snap["observed_local_hazard"]
        L.append("    PELIGRO LOCAL       " + " · ".join(
            f"{k}={v['estado'] if v['estado'] != 'OBSERVED' else v['nivel']}" for k, v in hz.items()))
        op = snap["operational_precaution"]
        L.append(f"{EMOJI[op['level']]}  PRECAUCIÓN OPERATIVA {op['level'].upper()} ({op['transition']}) — {op['note']}")
        d = op.get("decision") or {}
        if d.get("to") and LEVELS.index(d["to"]) < LEVELS.index(d["from"]):
            L.append(f"    decisión de bajar {d['from']}→{d['to']}: {d['decision']}"
                     + (f" · retador {d['challenger']['verdict']}" if d.get("challenger") else ""))
            for c in d["open_conditions"]:
                L.append(f"      ✋ {c['code']} [{c['kind']}] {c['text']}")
            for c in d.get("overridden", []):
                L.append(f"      ↷ {c['code']} levantado por el propietario: {c.get('motivo', '')}")
        L.append("    salida si: " + "; ".join(op["exit_conditions"]))
        gv = snap.get("governance")
        if gv:
            ep = gv["episode"] or {}
            ps = gv["predictions"]["summary"]
            L.append(f"    GOBERNANZA          afirmaciones {gv['claims_count']} · episodio {ep.get('id', '—')} "
                     f"fase {ep.get('phase', '—')} · predicciones {ps}")
            for x in gv["dissent_open"]:
                L.append(f"      ⚑ disenso {x['id']} abierto: {x['text'][:120]}")
            for x in gv["anomalies_open"]:
                L.append(f"      ⚑ anomalía {x['id']} sin revisar: {x['text'][:120]}")
            for p in gv["predictions"]["new"]:
                L.append(f"      ⧗ {p['id']} hasta {parse_time(p['window_end']).astimezone(MADRID):%H:%M}: {p['claim']}")
            for p in gv["predictions"]["verified"]:
                L.append(f"      ✓ {p['id']} {p['outcome']['status']}: {p['claim']} ({p['outcome'].get('delta_mm', '—')} mm)")
            b = gv["bias_radar_gauge"]
            if b.get("n"):
                L.append(f"      sesgo radar–pluviómetro: n={b['n']} " + " ".join(
                    f"{k}={v}" for k, v in b.items() if k.startswith("ratio_")) + (f" · {b['flag']}" if b.get("flag") else ""))
            if ep.get("closure_blockers"):
                L.append(f"      cierre bloqueado por: {', '.join(ep['closure_blockers'])}")
            if ep.get("phase") == "CLOSURE_PROPOSED":
                L.append("      cierre PROPUESTO: acéptalo con --close-episode (el motor no se auto-acepta)")
    nc = snap["nowcast"]
    L.append(f"{EMOJI[nc['level']]}  AHORA (nowcast)      {nc['level'].upper():<6} (propuesto {nc['proposed']} · {nc['transition']})")
    for r in nc["reasons"]:
        L.append(f"   · {r}")
    L.append(f"{EMOJI[snap['level']]}  PRÓXIMAS 36 h      {snap['level'].upper():<6} (propuesto {snap['proposed']} · {snap['transition']})")
    for r in snap["reasons"]:
        L.append(f"   · {r}")
    L.append(f"   cobertura: {snap['coverage']}")
    L.append("── canales ──")
    for c in snap["channels"]:
        tag = "✖" if not c["available"] else EMOJI[LEVELS[c["level"]]]
        L.append(f"{tag} {c['name']:<34} [{c['kind']}, conf. {c['confidence']}]")
        for e in c["evidence"]:
            L.append(f"      {e}")
    ctx = snap.get("context")
    if ctx and ctx.get("notas"):
        L.append("── contexto climatológico (no altera niveles) ──")
        for n in ctx["notas"]:
            L.append(f"   {n['estacion']}: {n['mm_1h']:.1f} mm/1 h en la banda {n['banda']} de la climatología local")
    L.append("── fuentes ──")
    for s in snap["sources"]:
        L.append(f"   {s['name']:<14} {s['status']:<13} {s['data_time'][:16]:<16} {s['detail'][:110]}")
    L.append("Umbrales sin calibrar · estimación diagnóstica, no aviso oficial. Manda AEMET.")
    return "\n".join(L)


def persist(snap: dict, state: dict) -> Path:
    HOME.mkdir(parents=True, exist_ok=True)
    (HOME / "cycles").mkdir(exist_ok=True)
    clean = {k: v for k, v in snap.items() if not k.startswith("_")}
    body = json.dumps(clean, ensure_ascii=False, indent=1, default=str)
    digest = hashlib.sha256(body.encode()).hexdigest()[:10]
    p = HOME / "cycles" / f"{snap['cycle_id']}-{digest}.json"
    if not p.exists():                                 # ciclo congelado: nunca se reescribe
        tmp = p.with_suffix(".tmp")
        tmp.write_text(body)
        tmp.replace(p)
        with open(HOME / "log.jsonl", "a") as fh:
            fh.write(json.dumps({"id": snap["cycle_id"], "sha": digest, "level": snap["level"],
                                 "nowcast": snap["nowcast"]["level"], "proposed": snap["proposed"],
                                 "reasons": snap["reasons"]}, ensure_ascii=False) + "\n")
    st = HOME / "state.json"
    st.with_suffix(".tmp").write_text(json.dumps(state))
    st.with_suffix(".tmp").replace(st)
    return p


def persist_state_only(state: dict) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    st = HOME / "state.json"
    st.with_suffix(".tmp").write_text(json.dumps(state))
    st.with_suffix(".tmp").replace(st)


def pack_state(out: Path) -> Path:
    """Estado mínimo para continuar el seguimiento en otra máquina: state.json + cola de log y alertas."""
    def tail(name: str, n: int) -> list[str]:
        try:
            return (HOME / name).read_text().splitlines()[-n:]
        except FileNotFoundError:
            return []
    body = {"engine": VERSION, "packed_utc": now_utc().isoformat(), "state": load_state(),
            "log": tail("log.jsonl", CFG["app_history"]), "alerts": tail("alerts.jsonl", 200)}
    out.write_text(json.dumps(body, ensure_ascii=False, separators=(",", ":"), default=str))
    return out


def unpack_state(src: Path) -> dict:
    body = json.loads(src.read_text())
    if not isinstance(body.get("state"), dict):
        raise ValueError("paquete de estado sin 'state'")
    HOME.mkdir(parents=True, exist_ok=True)
    persist_state_only(body["state"])
    for name in ("log", "alerts"):
        lines = [ln for ln in body.get(name, []) if isinstance(ln, str) and ln.strip()]
        (HOME / f"{name if name == 'log' else 'alerts'}.jsonl").write_text("\n".join(lines) + ("\n" if lines else ""))
    return body["state"]


def load_state() -> dict:
    try:
        return json.loads((HOME / "state.json").read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"level": "quiet", "pending_down": 0}


# ════════════════════════════════════════════════════════════════════════
# ATMÓSFERA — perfil por niveles en Portinatx, índices derivados e indicadores sintéticos
#   Cada índice lleva su estado de validación:
#     ESTÁNDAR      índice operacional establecido (fórmula publicada); umbrales NO calibrados en Ibiza
#     DIAGNÓSTICO   regla local calibrada con observaciones de Portinatx (n pequeño, declarado)
#     EXPERIMENTAL  construcción propia sin validar: orienta, no decide
# ════════════════════════════════════════════════════════════════════════
INDEX_STATUS = {
    "cape": ("ESTÁNDAR", "CAPE del modelo (J/kg). Energía disponible, no probabilidad de tormenta."),
    "cin": ("ESTÁNDAR", "Inhibición convectiva del modelo (J/kg). Tapadera que el disparo debe vencer."),
    "li": ("ESTÁNDAR", "Lifted Index del modelo (°C). Negativo = inestable."),
    "ki": ("ESTÁNDAR", "K-Index (George 1960): (T850−T500)+Td850−(T700−Td700). Humedad + inestabilidad en niveles medios."),
    "tt": ("ESTÁNDAR", "Total Totals (Miller 1972): T850+Td850−2·T500."),
    "lr75": ("ESTÁNDAR", "Gradiente térmico 700–500 hPa (°C/km) con alturas geopotenciales del modelo."),
    "thetae850": ("ESTÁNDAR", "Temperatura potencial equivalente a 850 hPa (K, Bolton 1980). Masa de aire cálida y húmeda."),
    "tcwv": ("ESTÁNDAR", "Agua precipitable (columna total de vapor, mm) del modelo."),
    "fzl": ("ESTÁNDAR", "Altura de la isoterma 0 °C del modelo (m)."),
    "shr06": ("ESTÁNDAR", "Cizalladura 0–6 km aproximada: |V500 − V10m| (m/s). Aproximación por niveles, no capa integrada."),
    "shr01": ("ESTÁNDAR", "Cizalladura 0–1 km aproximada: |V925 − V10m| (m/s)."),
    "w700": ("ESTÁNDAR", "Velocidad vertical a 700 hPa del modelo (positivo = ascenso)."),
    "tw2m": ("ESTÁNDAR", "Temperatura de bulbo húmedo en superficie (°C), ecuación psicrométrica."),
    "wbz": ("ESTÁNDAR", "Altura del cero de bulbo húmedo (m) interpolada en el perfil."),
    "w850": ("ESTÁNDAR", "Velocidad vertical a 850 hPa del modelo (positivo = ascenso)."),
    "w500": ("ESTÁNDAR", "Velocidad vertical a 500 hPa del modelo (positivo = ascenso)."),
    "shr03": ("ESTÁNDAR", "Cizalladura 0–3 km aproximada: |V700 − V10m| (m/s)."),
    "div925": ("ESTÁNDAR", "Divergencia a 925 hPa (10⁻⁵ s⁻¹) por diferencias finitas en una malla de ±0,25°: negativa = convergencia. Escala de ~50 km."),
    "div850": ("ESTÁNDAR", "Divergencia a 850 hPa (10⁻⁵ s⁻¹), malla ±0,25°."),
    "vort850": ("ESTÁNDAR", "Vorticidad relativa a 850 hPa (10⁻⁵ s⁻¹), malla ±0,25°: positiva = ciclónica."),
    "vort500": ("ESTÁNDAR", "Vorticidad relativa a 500 hPa (10⁻⁵ s⁻¹), malla ±0,25°."),
    "froude": ("EXPERIMENTAL", "Froude U925/(N·h) con N seco de 1000–850 hPa y h = cota máxima de Ibiza: <1 el aire rodea el relieve, >1 lo remonta. Fórmula estándar; aplicación local sin validar."),
    "u925": ("ESTÁNDAR", "Viento a 925 hPa (m/s): el que choca con el relieve de la isla."),
    "orografia": ("EXPERIMENTAL", "Ascenso forzado por el relieve w = V925·∇h (m/s) sobre el MDT del IGN. Solo la componente forzada lineal; ignora bloqueo y efectos no lineales."),
    "oleaje_costa": ("ESTÁNDAR", "Asomeramiento lineal (Ks = √(cg0/cg)) y rotura H ≥ 0,78·d. Sin refracción ni difracción: es una cota, no la ola en la cala."),
    "mw": ("EXPERIMENTAL", "Viento medio 850–300 hPa (m/s), media simple de niveles: proxy del desplazamiento de las células."),
    "flux850": ("EXPERIMENTAL", "Flujo de humedad a 850 hPa q·|V| (g·kg⁻¹·m·s⁻¹): alimentación de vapor."),
    "icc": ("EXPERIMENTAL", "Ingredientes convectivos: inestabilidad, humedad, ascenso y organización, penalizado por CIN. Sin validar."),
    "ipp": ("EXPERIMENTAL", "Precipitación persistente (training): humedad, flujo a 850, lentitud de las células e inestabilidad. Sin validar."),
    "irh": ("DIAGNÓSTICO", "Respuesta hidrológica de la cala: antecedente, intensidad medida y lluvia prevista a 3 h. "
                           "Pesos fijados con 2 observaciones del propietario (18 y 19/10): n=2."),
    "modelos_ia": ("DIAGNÓSTICO", "Deterministas de IA (ECMWF AIFS, NOAA AIGFS) a 25 km y paso de 6 h: la lluvia horaria es el total de 6 h repartido. "
                                  "Útiles para la escala sinóptica; no resuelven la convección. Se verifican junto a los físicos."),
    "superens": ("EXPERIMENTAL", "Superensemble de 5 sistemas (IFS ENS, GEFS, AIFS ENS, AIGEFS, WeatherNext 2): fracción de miembros que superan el umbral en el punto, "
                                 "con el mismo peso por sistema. No es una probabilidad calibrada: sin corrección de sesgo ni vecindad."),
    "oleaje_multi": ("DIAGNÓSTICO", "Hs de 7 modelos de oleaje en el mismo punto frente a la bocana. La dispersión entre modelos es incertidumbre, no ruido; "
                                    "en este episodio los modelos han infraestimado las boyas."),
    "surge": ("DIAGNÓSTICO", "Nivel del mar observado (mareógrafo del puerto de Ibiza) y modelizado (marea + barómetro inverso) como anomalía respecto a su media común; "
                             "residuo = obs − modelo. Los ceros de referencia no coinciden: solo se comparan variaciones."),
    "radar_hf": ("ESTÁNDAR", "Corriente superficial medida por el radar HF de SOCIB en el canal de Ibiza (celdas con QC = 1). Cubre el canal SW, no la costa norte."),
    "forense": ("DIAGNÓSTICO", "Verificación de lo que cada modelo previó TAL COMO SE EMITIÓ (Open-Meteo Previous Runs: D0 = run del día, D1 = de la víspera, "
                               "D2 = de dos días antes) frente a las lecturas archivadas de los pluviómetros, con la ventana exacta 00 h local → hora de la lectura. "
                               "Pocas estaciones de red aficionada y pocos episodios: las cifras describen este periodo, no el clima del modelo."),
    "aprendizaje": ("EXPERIMENTAL", "Factor de corrección por modelo y antelación = (lluvia medida / prevista) contraído hacia 1 según el tamaño de muestra "
                                    "(n_eff/(n_eff+8)) y con olvido exponencial (vida media 10 días); pesos por error relativo. No modifica el aviso ni la precaución."),
    "gauge_wet": ("DIAGNÓSTICO", "Umbrales de pluviómetro rebajados con suelo saturado (≥60 mm ayer+hoy): 10/20/40 mm/h. n=2."),
}
# Normalización de componentes (lineal y recortada a [0,1]) y pesos. Todo editable en el modo laboratorio.
COMPOSITES = {
    "icc": {"weights": {"inestabilidad": 0.30, "humedad": 0.30, "ascenso": 0.20, "organizacion": 0.20},
            "ranges": {"inestabilidad": ("cape", 0, 2000), "humedad": ("tcwv", 20, 40),
                       "ascenso": ("w700", 0, 0.3), "organizacion": ("shr06", 5, 25)},
            "penalty": ("cin", 0, 200, 0.5)},
    "ipp": {"weights": {"humedad": 0.30, "alimentacion": 0.30, "lentitud": 0.25, "inestabilidad": 0.15},
            "ranges": {"humedad": ("tcwv", 20, 40), "alimentacion": ("flux850", 50, 250),
                       "lentitud": ("mw", 20, 5), "inestabilidad": ("cape", 0, 1500)},
            "penalty": None},
}
PROFILE_LEVELS = (1000, 925, 850, 700, 500, 300)


def src_profile() -> SourceResult:
    lv = PROFILE_LEVELS
    vars_ = [f"{v}_{p}hPa" for p in lv for v in ("temperature", "relative_humidity", "wind_speed",
                                                  "wind_direction", "geopotential_height")]
    vars_ += ["vertical_velocity_700hPa", "vertical_velocity_850hPa", "cape", "convective_inhibition",
              "lifted_index", "freezing_level_height", "total_column_integrated_water_vapour",
              "boundary_layer_height", "temperature_2m", "dew_point_2m", "pressure_msl",
              "wind_speed_10m", "wind_direction_10m", "precipitation"]
    vars_ += ["vertical_velocity_500hPa"]
    dd = CFG["stencil_deg"]
    pts = [(SITE["lat"], SITE["lon"]), (SITE["lat"] + dd, SITE["lon"]), (SITE["lat"] - dd, SITE["lon"]),
           (SITE["lat"], SITE["lon"] + dd), (SITE["lat"], SITE["lon"] - dd)]
    q = {"forecast_hours": 48, "past_hours": 12, "hourly": ",".join(vars_), "wind_speed_unit": "ms",
         "models": CFG.get("profile_model", "best_match")}
    res = _om_multi("https://api.open-meteo.com/v1/forecast", q, pts)
    d = res[0]
    if "hourly" not in d:
        raise RuntimeError(str(d.get("reason", d))[:120])
    keep = [f"wind_{v}_{p}hPa" for p in (925, 850, 500) for v in ("speed", "direction")]
    sten = {k: {v: r.get("hourly", {}).get(v) for v in keep} for k, r in zip(("N", "S", "E", "W"), res[1:])}
    return SourceResult(name="perfil", status="ok", kind="model", data_time=now_utc().isoformat(),
                        detail=f"perfil {CFG.get('profile_model', 'best_match')} · {len(lv)} niveles · 60 h · malla ±{dd}°",
                        payload={"hourly": d["hourly"], "units": d.get("hourly_units", {}), "stencil": sten})


def _dewpoint(t: float | None, rh: float | None) -> float | None:
    if t is None or rh is None or rh <= 0:
        return None
    a, b = 17.625, 243.04                                   # Magnus–Alduchov
    g = math.log(rh / 100.0) + a * t / (b + t)
    return b * g / (a - g)


def _thetae(t: float | None, td: float | None, p: float) -> float | None:
    """Bolton (1980), ec. 38–43."""
    if t is None or td is None:
        return None
    tk, tdk = t + 273.15, td + 273.15
    e = 6.112 * math.exp(17.67 * td / (td + 243.5))
    r = 622.0 * e / (p - e)                                # g/kg
    tl = 1.0 / (1.0 / (tdk - 56.0) + math.log(tk / tdk) / 800.0) + 56.0
    th = tk * (1000.0 / p) ** (0.2854 * (1 - 0.00028 * r))
    return th * math.exp((3.376 / tl - 0.00254) * r * (1 + 0.00081 * r))


def _q(t: float | None, td: float | None, p: float) -> float | None:
    if td is None:
        return None
    e = 6.112 * math.exp(17.67 * td / (td + 243.5))
    return 622.0 * e / (p - 0.378 * e)                     # g/kg


def _uv(ws: float | None, wd: float | None) -> tuple[float, float] | None:
    if ws is None or wd is None:
        return None
    a = math.radians(wd)
    return -ws * math.sin(a), -ws * math.cos(a)


def _norm(v: float | None, lo: float, hi: float) -> float | None:
    if v is None:
        return None
    x = (v - lo) / (hi - lo) if hi != lo else 0.0
    return max(0.0, min(1.0, x))


def composite(name: str, idx: dict[str, float | None], weights: dict | None = None) -> dict:
    spec = COMPOSITES[name]
    w = weights or spec["weights"]
    comps, val, wsum = {}, 0.0, 0.0
    for k, (var, lo, hi) in spec["ranges"].items():
        n = _norm(idx.get(var), lo, hi)
        comps[k] = n
        if n is not None:
            val += w[k] * n
            wsum += w[k]
    if not wsum:
        return {"value": None, "components": comps}
    val /= wsum                                              # renormaliza si falta un componente
    pen = None
    if spec.get("penalty"):
        var, lo, hi, f = spec["penalty"]
        pn = _norm(idx.get(var), lo, hi)
        if pn is not None:
            pen = pn
            val *= (1 - f * pn)
    return {"value": round(val, 3), "components": {k: (None if v is None else round(v, 3)) for k, v in comps.items()},
            "penalty": None if pen is None else round(pen, 3), "missing": [k for k, v in comps.items() if v is None]}


def derive_profile(h: dict, units: dict, stencil: dict | None = None, terrain_top: float = 400.0) -> dict:
    """Índices por hora a partir del perfil del modelo."""
    times = h.get("time", [])
    get = lambda k, i: (h.get(k) or [None] * len(times))[i] if i < len(h.get(k) or []) else None
    w_sign = -1.0 if "Pa" in (units.get("vertical_velocity_700hPa") or "") else 1.0   # Pa/s: negativo = ascenso
    out = {k: [] for k in ("cape", "cin", "li", "ki", "tt", "lr75", "thetae850", "tcwv", "fzl", "shr06",
                           "shr01", "w700", "mw", "flux850", "blh", "t2m", "td2m", "pmsl", "pr",
                           "tw2m", "wbz", "w850", "w500", "shr03", "div925", "div850", "vort850", "vort500",
                           "froude", "u925")}
    phys = {"thetae": {str(p): [] for p in PROFILE_LEVELS}, "tw": {str(p): [] for p in PROFILE_LEVELS},
            "shear_by_height": []}
    comp = {"icc": [], "ipp": []}
    levels = {p: {"T": [], "Td": [], "ws": [], "wd": [], "z": []} for p in PROFILE_LEVELS}
    for i in range(len(times)):
        L = {}
        for p in PROFILE_LEVELS:
            t, rh = get(f"temperature_{p}hPa", i), get(f"relative_humidity_{p}hPa", i)
            td = _dewpoint(t, rh)
            L[p] = {"T": t, "Td": td, "ws": get(f"wind_speed_{p}hPa", i), "wd": get(f"wind_direction_{p}hPa", i),
                    "z": get(f"geopotential_height_{p}hPa", i)}
            for k in levels[p]:
                v = L[p][k]
                levels[p][k].append(None if v is None else round(v, 1))
        T = lambda p: L[p]["T"]; TD = lambda p: L[p]["Td"]
        ki = tt = lr = None
        if None not in (T(850), T(700), T(500), TD(850), TD(700)):
            ki = (T(850) - T(500)) + TD(850) - (T(700) - TD(700))
            tt = T(850) + TD(850) - 2 * T(500)
        if None not in (T(700), T(500), L[700]["z"], L[500]["z"]) and L[500]["z"] > L[700]["z"]:
            lr = (T(700) - T(500)) / ((L[500]["z"] - L[700]["z"]) / 1000.0)
        v10 = _uv(get("wind_speed_10m", i), get("wind_direction_10m", i))
        v500, v925 = _uv(L[500]["ws"], L[500]["wd"]), _uv(L[925]["ws"], L[925]["wd"])
        shr = lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1]) if a and b else None
        uvs = [_uv(L[p]["ws"], L[p]["wd"]) for p in (850, 700, 500, 300)]
        mw = (math.hypot(sum(u[0] for u in uvs) / 4, sum(u[1] for u in uvs) / 4) if all(uvs) else None)
        q850 = _q(T(850), TD(850), 850.0)
        w700 = get("vertical_velocity_700hPa", i)
        row = {"cape": get("cape", i), "cin": get("convective_inhibition", i), "li": get("lifted_index", i),
               "ki": ki, "tt": tt, "lr75": lr, "thetae850": _thetae(T(850), TD(850), 850.0),
               "tcwv": get("total_column_integrated_water_vapour", i), "fzl": get("freezing_level_height", i),
               "shr06": shr(v500, v10), "shr01": shr(v925, v10), "w700": None if w700 is None else w_sign * w700,
               "mw": mw, "flux850": (q850 * L[850]["ws"]) if (q850 is not None and L[850]["ws"] is not None) else None,
               "blh": get("boundary_layer_height", i), "t2m": get("temperature_2m", i), "td2m": get("dew_point_2m", i),
               "pmsl": get("pressure_msl", i), "pr": get("precipitation", i)}
        if row["cin"] is not None:
            row["cin"] = abs(row["cin"])
        # física: θe y bulbo húmedo por nivel, cero de bulbo húmedo, cizalladura por altura, divergencia, vorticidad
        tw_lv = {}
        for p in PROFILE_LEVELS:
            te_p = _thetae(T(p), TD(p), float(p))
            tw_p = wet_bulb(T(p), TD(p), float(p))
            tw_lv[p] = tw_p
            phys["thetae"][str(p)].append(None if te_p is None else round(te_p, 1))
            phys["tw"][str(p)].append(None if tw_p is None else round(tw_p, 1))
        tw2 = wet_bulb(row["t2m"], row["td2m"], row["pmsl"] or 1013.0)
        prof = [(0.0, tw2)] + [(L[p]["z"], tw_lv[p]) for p in PROFILE_LEVELS if L[p]["z"] is not None]
        wbz = None
        for (z1, a1), (z2, a2) in zip(prof, prof[1:]):
            if None not in (a1, a2) and a1 > 0 >= a2 and z2 > z1:
                wbz = z1 + (z2 - z1) * a1 / (a1 - a2)
                break
        v700 = _uv(L[700]["ws"], L[700]["wd"])
        sbh = []
        for p in (925, 850, 700, 500, 300):
            vp = _uv(L[p]["ws"], L[p]["wd"])
            if vp and v10 and L[p]["z"] is not None:
                sbh.append([round(L[p]["z"] / 1000, 2), round(math.hypot(vp[0] - v10[0], vp[1] - v10[1]), 1)])
        phys["shear_by_height"].append(sbh)
        dv = {}
        if stencil:
            dd = CFG["stencil_deg"]
            dx = 2 * dd * 111000 * math.cos(math.radians(SITE["lat"]))
            dy = 2 * dd * 111000

            def g_(k, p):
                st_ = stencil.get(k) or {}
                sp, di = st_.get(f"wind_speed_{p}hPa") or [], st_.get(f"wind_direction_{p}hPa") or []
                return _uv(sp[i] if i < len(sp) else None, di[i] if i < len(di) else None)
            for p in (925, 850, 500):
                n_, s_, e_, w_ = g_("N", p), g_("S", p), g_("E", p), g_("W", p)
                if all((n_, s_, e_, w_)):
                    dv[f"div{p}"] = ((e_[0] - w_[0]) / dx + (n_[1] - s_[1]) / dy) * 1e5
                    dv[f"vort{p}"] = ((e_[1] - w_[1]) / dx - (n_[0] - s_[0]) / dy) * 1e5
        th1000 = (T(1000) + 273.15) if T(1000) is not None else None
        th850 = (T(850) + 273.15) * (1000 / 850) ** 0.2854 if T(850) is not None else None
        dz = (L[850]["z"] - L[1000]["z"]) if None not in (L[850]["z"], L[1000]["z"]) else None
        u925 = L[925]["ws"]
        row.update({"tw2m": tw2, "wbz": wbz, "w850": get("vertical_velocity_850hPa", i), "w500": get("vertical_velocity_500hPa", i),
                    "shr03": (math.hypot(v700[0] - v10[0], v700[1] - v10[1]) if v700 and v10 else None),
                    "div925": dv.get("div925"), "div850": dv.get("div850"), "vort850": dv.get("vort850"),
                    "vort500": dv.get("vort500"), "froude": froude(u925, th1000, th850, dz, terrain_top), "u925": u925})
        for kk in ("w850", "w500"):
            if row[kk] is not None:
                row[kk] = w_sign * row[kk]
        for k, v in row.items():
            out[k].append(None if v is None else round(v, 3 if k in ("w700", "w850", "w500") else 2 if k in ("froude", "div925", "div850", "vort850", "vort500") else 1))
        for c in comp:
            comp[c].append(composite(c, row))
    return {"time": times, "indices": out, "levels": {str(p): v for p, v in levels.items()},
            "composites": comp, "wind10": {"ws": h.get("wind_speed_10m", []), "wd": h.get("wind_direction_10m", [])},
            "physics": phys}


def irh_now(gauges: Channel, models: dict | None) -> dict:
    """Respuesta hidrológica de la cala (DIAGNÓSTICO, n=2). Componentes visibles."""
    st = [s for s in gauges.metrics.get("stations", []) if s.get("near")] if gauges.available else []
    ante = max((s.get("ante_mm") or 0 for s in st), default=None)
    rate = max((s.get("rate") or 0 for s in st if s.get("rate") is not None), default=None)
    fc3 = None
    if models:
        now = now_utc()
        vals = []
        for m, v in models.items():
            for t, x in zip(v.get("time", []), v.get("pr_neigh_max") or v.get("pr") or []):
                tt = parse_time(t + "Z" if t and not t.endswith("Z") else t)
                if tt and now <= tt < now + timedelta(hours=3) and x is not None:
                    vals.append((m, t, x))
        if vals:
            per = {}
            for m, t, x in vals:
                per[m] = per.get(m, 0) + x
            fc3 = max(per.values())
    w = {"antecedente": 0.35, "intensidad": 0.45, "prevista_3h": 0.20}
    c = {"antecedente": _norm(ante, 0, 100), "intensidad": _norm(rate, 0, 30), "prevista_3h": _norm(fc3, 0, 30)}
    ws = sum(w[k] for k in c if c[k] is not None)
    val = sum(w[k] * c[k] for k in c if c[k] is not None) / ws if ws else None
    return {"value": None if val is None else round(val, 3), "components": {k: (None if v is None else round(v, 3)) for k, v in c.items()},
            "raw": {"antecedente_mm": ante, "intensidad_mmh": rate, "prevista_3h_mm": None if fc3 is None else round(fc3, 1)},
            "weights": w, "ranges": {"antecedente": (0, 100), "intensidad": (0, 30), "prevista_3h": (0, 30)},
            "reference": "18/10: escorrentía con ~20–30 mm/h y >60 mm de antecedente · 19/10 10:16: agua en la puerta "
                         "con 20,8 mm/h y 145 mm de antecedente (IRH ≈ 0,66 sin lluvia prevista; ≈ 0,83 sin el componente previsto)"}


# ════════════════════════════════════════════════════════════════════════
# TERRITORIO, SATÉLITE Y VERIFICACIÓN DE MODELOS
#   Relieve IGN (WCS, ArcGrid) · batimetría EMODnet (WCS, GeoTIFF float32) · EUMETView (WMS: IR, WV, RGB)
#   Modelos en cada pluviómetro (AROME HD, ICON-EU, ECMWF) para comparar con la lluvia medida.
# ════════════════════════════════════════════════════════════════════════
def parse_arcgrid(txt: str) -> dict:
    lines = txt.strip().splitlines()
    hdr, k = {}, 0
    while k < len(lines) and re.match(r"^[A-Za-z_]+\s", lines[k]):
        a, b = lines[k].split(None, 1)
        hdr[a.lower()] = float(b)
        k += 1
    vals = [float(x) for ln in lines[k:] for x in ln.split()]
    nc, nr = int(hdr["ncols"]), int(hdr["nrows"])
    nod = hdr.get("nodata_value", -9999.0)
    rows = [[None if v == nod else v for v in vals[i * nc:(i + 1) * nc]] for i in range(nr)]
    return {"ncols": nc, "nrows": nr, "lon_w": hdr["xllcorner"], "lat_s": hdr["yllcorner"],
            "cell": hdr["cellsize"], "lat_n": hdr["yllcorner"] + nr * hdr["cellsize"], "rows": rows}


def parse_tiff_f32(blob: bytes) -> tuple[int, int, list[float]]:
    """TIFF sin comprimir, float32 de una banda, en teselas o tiras (lo que sirve EMODnet)."""
    bo = "<" if blob[:2] == b"II" else ">"
    off = struct.unpack(bo + "I", blob[4:8])[0]
    n = struct.unpack(bo + "H", blob[off:off + 2])[0]
    tags = {}
    for i in range(n):
        e = blob[off + 2 + 12 * i: off + 14 + 12 * i]
        tag, typ, cnt = struct.unpack(bo + "HHI", e[:8])
        size = {3: 2, 4: 4}.get(typ, 1) * cnt
        if typ in (3, 4) and size <= 4:
            vals = list(struct.unpack(bo + ("H" if typ == 3 else "I") * cnt, e[8:8 + size]))
        elif typ in (3, 4):
            p = struct.unpack(bo + "I", e[8:12])[0]
            vals = list(struct.unpack(bo + ("H" if typ == 3 else "I") * cnt, blob[p:p + size]))
        else:
            vals = [struct.unpack(bo + "I", e[8:12])[0]]
        tags[tag] = vals
    w, h = tags[256][0], tags[257][0]
    if tags.get(259, [1])[0] != 1 or tags.get(258, [32])[0] != 32:
        raise ValueError("TIFF comprimido o no float32")
    out = [0.0] * (w * h)
    if 322 in tags:                                      # teselas
        tw, th = tags[322][0], tags[323][0]
        across = (w + tw - 1) // tw
        for k, (o, c) in enumerate(zip(tags[324], tags[325])):
            ty, tx = divmod(k, across)
            data = struct.unpack(bo + "f" * (c // 4), blob[o:o + c])
            for r in range(th):
                y = ty * th + r
                if y >= h:
                    break
                for q in range(tw):
                    x = tx * tw + q
                    if x < w:
                        out[y * w + x] = data[r * tw + q]
    else:                                                # tiras
        pos = 0
        for o, c in zip(tags[273], tags[279]):
            data = struct.unpack(bo + "f" * (c // 4), blob[o:o + c])
            out[pos:pos + len(data)] = data
            pos += len(data)
    return w, h, out


def src_terrain() -> SourceResult:
    la0, la1, lo0, lo1 = CFG["dem_box"]
    r = CFG["dem_res"]
    url = ("https://servicios.idee.es/wcs-inspire/mdt?SERVICE=WCS&VERSION=1.0.0&REQUEST=GetCoverage"
           f"&COVERAGE=Elevacion4258_200&CRS=EPSG:4258&BBOX={lo0},{la0},{lo1},{la1}&RESX={r}&RESY={r}&FORMAT=ArcGrid")
    g = parse_arcgrid(http_get(url, timeout=90).decode("ascii", "replace"))
    g["rows"] = [[None if v is None else round(v) for v in row] for row in g["rows"]]
    top = max(v for row in g["rows"] for v in row if v is not None)
    return SourceResult(name="relieve", status="ok", kind="obs", data_time=now_utc().isoformat(),
                        detail=f"IGN MDT {g['ncols']}×{g['nrows']} a {r}° · cota máx {top} m", payload=g)


def src_bathy() -> SourceResult:
    la0, la1, lo0, lo1 = CFG["bathy_box"]
    r = CFG["bathy_res"]
    url = ("https://ows.emodnet-bathymetry.eu/wcs?service=WCS&version=1.0.0&request=GetCoverage&coverage=emodnet:mean"
           f"&crs=EPSG:4326&bbox={lo0},{la0},{lo1},{la1}&format=image/tiff&resx={r}&resy={r}")
    w, h, v = parse_tiff_f32(http_get(url, timeout=90))
    rows = [[None if (abs(x) > 1e5 or x != x or x >= 0) else round(-x, 1) for x in v[i * w:(i + 1) * w]] for i in range(h)]
    deep = max((x for row in rows for x in row if x is not None), default=0)
    return SourceResult(name="batimetria", status="ok", kind="obs", data_time=now_utc().isoformat(),
                        detail=f"EMODnet DTM {w}×{h} a {r}° · prof. máx {deep:.0f} m",
                        payload={"ncols": w, "nrows": h, "lon_w": lo0, "lat_n": la1, "cell_x": (lo1 - lo0) / w,
                                 "cell_y": (la1 - la0) / h, "rows": rows})


SAT_LAYERS = {"ir": ("mtg_fd:ir105_hrfi", "IR 10,5 µm (MTG-FCI)"), "wv": ("msg_fes:wv062", "Vapor de agua 6,2 µm (MSG)"),
              "airmass": ("msg_fes:rgb_airmass", "RGB Airmass (MSG)"), "conv": ("msg_fes:rgb_convection", "RGB Convección (MSG, solo de día)")}


def src_satellite() -> SourceResult:
    import base64
    base = "https://view.eumetsat.int/geoserver/ows"
    caps = http_get(f"{base}?service=WMS&request=GetCapabilities&version=1.3.0", timeout=60).decode("utf-8", "replace")
    rg = CFG["radar_grid"]
    la_s, la_n = SITE["lat"] - rg["dlat"], SITE["lat"] + rg["dlat"]
    lo_w, lo_e = SITE["lon"] - rg["dlon"], SITE["lon"] + rg["dlon"]
    out, errs = {}, []
    for k, (layer, title) in SAT_LAYERS.items():
        try:
            i = caps.find(f"<Name>{layer}</Name>")
            m = re.search(r'<Dimension name="time"[^>]*default="([^"]+)"', caps[i:i + 6000]) if i >= 0 else None
            q = urllib.parse.urlencode({"service": "WMS", "version": "1.3.0", "request": "GetMap", "layers": layer,
                                        "styles": "", "crs": "EPSG:4326", "bbox": f"{la_s},{lo_w},{la_n},{lo_e}",
                                        "width": 628, "height": 468, "format": "image/jpeg"})
            img = http_get(f"{base}?{q}", timeout=60)
            out[k] = {"title": title, "layer": layer, "time": m.group(1) if m else "",
                      "data": "data:image/jpeg;base64," + base64.b64encode(img).decode()}
        except Exception as exc:
            errs.append(f"{k}: {type(exc).__name__}")
    if not out:
        raise RuntimeError("EUMETView sin imágenes: " + "; ".join(errs))
    newest = max((v["time"] for v in out.values() if v["time"]), default=now_utc().isoformat())
    return SourceResult(name="satelite", status="ok", kind="obs", data_time=newest,
                        detail=f"EUMETView {', '.join(out)}" + (f" · fallos: {', '.join(errs)}" if errs else ""),
                        payload={"bbox": {"lat_s": la_s, "lat_n": la_n, "lon_w": lo_w, "lon_e": lo_e}, "layers": out})


def src_gauge_models() -> SourceResult:
    """Lluvia de cada modelo en cada pluviómetro (y en Portinatx): 24 h pasadas + 24 h futuras."""
    pts = [(SITE["lat"], SITE["lon"], "Portinatx")] + [(la, lo, nm) for nm, la, lo in CFG["mc_stations"].values()]
    res = _om_multi("https://api.open-meteo.com/v1/forecast",
                    {"hourly": "precipitation", "models": ",".join(CFG["det_models"] + CFG["ai_models"]), "past_hours": 24,
                     "forecast_hours": 24}, [(a, b) for a, b, _ in pts])
    out = []
    for (la, lo, nm), r in zip(pts, res):
        h = r.get("hourly", {})
        out.append({"nombre": nm, "lat": la, "lon": lo, "time": h.get("time", []),
                    "models": {m: h.get(f"precipitation_{m}") or [] for m in CFG["det_models"] + CFG["ai_models"]}})
    return SourceResult(name="modelos_pluvio", status="ok", kind="model", data_time=now_utc().isoformat(),
                        detail=f"{len(out)} puntos × {len(CFG['det_models']) + len(CFG['ai_models'])} modelos (física + IA) · ±24 h", payload={"points": out})


def wet_bulb(t: float | None, td: float | None, p: float) -> float | None:
    """Temperatura de bulbo húmedo por la ecuación psicrométrica (bisección). °C."""
    if t is None or td is None:
        return None
    e = 6.112 * math.exp(17.67 * td / (td + 243.5))
    lo, hi = td, t
    for _ in range(40):
        tw = (lo + hi) / 2
        es = 6.112 * math.exp(17.67 * tw / (tw + 243.5))
        f = es - 0.00066 * (1 + 0.00115 * tw) * p * (t - tw) - e
        if f > 0:
            hi = tw
        else:
            lo = tw
    return (lo + hi) / 2


def froude(u: float | None, theta_lo: float | None, theta_hi: float | None, dz: float | None, h: float) -> float | None:
    """Número de Froude U/(N·h) con N² = g/θ̄ · Δθ/Δz (aire seco; la humedad lo reduce)."""
    if None in (u, theta_lo, theta_hi, dz) or dz <= 0:
        return None
    n2 = 9.81 / ((theta_lo + theta_hi) / 2) * (theta_hi - theta_lo) / dz
    if n2 <= 0:
        return 99.0                                   # inestable: sin bloqueo
    return u / (math.sqrt(n2) * h)


def wave_shoaling(h0: float | None, tp: float | None, depths: list[float]) -> list[dict]:
    """Asomeramiento lineal (sin refracción) desde aguas profundas: Ks = √(cg0/cg); rotura si H ≥ 0,78·d."""
    if not h0 or not tp:
        return []
    g = 9.81
    L0 = g * tp ** 2 / (2 * math.pi)
    cg0 = 0.5 * g * tp / (2 * math.pi)
    out = []
    for d in depths:
        y = (2 * math.pi / tp) ** 2 * d / g             # dispersión: aproximación de Hunt (1979), error <0,1 %
        kd = math.sqrt(y * y + y / (1 + 0.6522 * y + 0.4622 * y ** 2 + 0.0864 * y ** 4 + 0.0675 * y ** 5))
        k = kd / d
        L = 2 * math.pi / k
        n = 0.5 * (1 + 2 * k * d / math.sinh(2 * k * d))
        cg = n * L / tp
        ks = math.sqrt(cg0 / cg)
        hh = h0 * ks
        out.append({"d": d, "L": round(L, 1), "Ks": round(ks, 3), "H": round(hh, 2), "rompe": hh >= 0.78 * d})
    return out


# ════════════════════════════════════════════════════════════════════════
# MODELOS DE IA, SUPERENSEMBLE Y ESTADO DEL MAR
#   Deterministas físicos e IA en Portinatx (Open-Meteo) · superensemble de 5 sistemas (2 físicos, 3 IA) ·
#   oleaje de 7 modelos con partición mar de viento / mar de fondo · corrientes, SST y nivel del mar ·
#   radar HF de corrientes del canal de Ibiza (SOCIB, OPeNDAP).
#   Ningún producto de este bloque abre por sí solo la precaución: son DIAGNÓSTICO o EXPERIMENTAL.
# ════════════════════════════════════════════════════════════════════════
MODEL_INFO = {
    "meteofrance_arome_france_hd": ("AROME HD", "física", "1,5 km · convectivo"),
    "icon_eu": ("ICON-EU", "física", "7 km"),
    "ecmwf_ifs": ("ECMWF IFS HRES", "física", "9 km"),
    "ecmwf_ifs025": ("ECMWF IFS 0,25°", "física", "25 km"),
    "meteofrance_arpege_europe": ("ARPEGE Europa", "física", "10 km"),
    "ukmo_global_deterministic_10km": ("UKMO Global", "física", "10 km"),
    "ecmwf_aifs025_single": ("ECMWF AIFS", "IA", "25 km · 6-horario"),
    "ncep_aigfs025": ("NOAA AIGFS", "IA", "25 km · 6-horario"),
}
SUPER_ENS = {
    "ecmwf_ifs025": ("ECMWF IFS ENS", "física"),
    "ncep_gefs025": ("NOAA GEFS", "física"),
    "ecmwf_aifs025_ensemble": ("ECMWF AIFS ENS", "IA"),
    "ncep_aigefs025": ("NOAA AIGEFS", "IA"),
    "google_weathernext2_ensemble": ("Google WeatherNext 2", "IA"),
}
WAVE_MODELS = {
    "meteofrance_wave": "MFWAM 8 km", "dwd_ewam": "DWD EWAM 5 km", "ecmwf_wam": "ECMWF WAM 9 km",
    "ncep_gfswave016": "GFS-Wave 16 km", "dwd_gwam": "DWD GWAM 25 km", "ecmwf_wam025": "ECMWF WAM 25 km",
    "ncep_gfswave025": "GFS-Wave 25 km",
}
WAVE_VARS = ("wave_height", "wave_period", "wave_direction", "wave_peak_period", "swell_wave_height",
             "swell_wave_period", "swell_wave_direction", "wind_wave_height", "secondary_swell_wave_height")
HF_RADAR_URL = ("https://thredds.socib.es/thredds/dodsC/hf_radar/hf_radar_ibiza-scb_codarssproc001/L1/"
                "dep0001_hf-radar-ibiza_scb-codarssproc001_L1_latest.nc")
WINDOWS_H = {"0-6": (0, 6), "6-12": (6, 12), "12-24": (12, 24), "24-48": (24, 48), "48-72": (48, 72)}


def _by_model(h: dict, var: str, m: str, single: bool) -> list:
    return h.get(f"{var}_{m}") or (h.get(var) if single else None) or []


def src_models_x() -> SourceResult:
    """Deterministas físicos e IA en el punto: lluvia, racha, CAPE, viento y presión, −24/+72 h."""
    models = list(MODEL_INFO)
    hv = "precipitation,wind_gusts_10m,cape,wind_speed_10m,wind_direction_10m,pressure_msl"
    h = _om_multi("https://api.open-meteo.com/v1/forecast",
                  {"hourly": hv, "models": ",".join(models), "past_hours": 24, "forecast_hours": 72},
                  [(SITE["lat"], SITE["lon"])])[0].get("hourly", {})
    out = {m: {v: _by_model(h, v, m, False) for v in hv.split(",")} for m in models}
    alive = [m for m, d in out.items() if any(x is not None for x in d["precipitation"])]
    if not alive:
        raise RuntimeError("ningún modelo devolvió lluvia")
    return SourceResult(name="modelos_x", status="ok", kind="model", data_time=now_utc().isoformat(),
                        detail=f"{len(alive)}/{len(models)} modelos ({sum(MODEL_INFO[m][1] == 'IA' for m in alive)} de IA)",
                        payload={"time": h.get("time", []), "models": {m: out[m] for m in alive}})


def ens_members(h: dict, var: str, m: str) -> list[list]:
    """Control + miembros de un modelo en una respuesta multi-modelo del API de ensembles.
    El sufijo de las claves es el id del modelo o el id + «_ensemble» (p. ej. ecmwf_ifs025 → _ecmwf_ifs025_ensemble)."""
    out = []
    for sfx in (f"{m}_ensemble", m):
        keys = [k for k in h if k.startswith(f"{var}_") and k.endswith(f"_{sfx}")
                and (k == f"{var}_{sfx}" or k[len(var) + 1:].startswith("member"))]
        if keys:
            out = [h[k] for k in sorted(keys) if any(x is not None for x in h[k])]
            break
    return out


def window_sums(times: list[str], vals: list, now: datetime, windows: dict = WINDOWS_H) -> dict:
    tt = [parse_time(t + "Z") for t in times]
    return {w: sum((x or 0) for t, x in zip(tt, vals) if t and now + timedelta(hours=a) <= t < now + timedelta(hours=b))
            for w, (a, b) in windows.items()}


def ens_stats(members: list[list], times: list[str], now: datetime, thresholds=(1, 5, 10, 30, 50)) -> dict:
    """Totales por ventana de cada miembro → percentiles y probabilidad de superar umbrales (fracción de miembros)."""
    if not members:
        return {}
    tots = [window_sums(times, m, now, {"0-24": (0, 24), "24-48": (24, 48), "48-72": (48, 72)}) for m in members]
    out = {"n": len(members), "ventanas": {}}
    for w in ("0-24", "24-48", "48-72"):
        v = sorted(t[w] for t in tots)
        out["ventanas"][w] = {"p10": _r(_pct(v, 0.1), 1), "p50": _r(_pct(v, 0.5), 1), "p90": _r(_pct(v, 0.9), 1),
                              "max": _r(v[-1], 1),
                              "prob": {str(th): round(sum(1 for x in v if x >= th) / len(v), 3) for th in thresholds}}
    return out


def src_superens() -> SourceResult:
    models = list(SUPER_ENS)
    h = _om_multi("https://ensemble-api.open-meteo.com/v1/ensemble",
                  {"hourly": "precipitation,wind_gusts_10m", "models": ",".join(models), "forecast_hours": 72},
                  [(SITE["lat"], SITE["lon"])])[0].get("hourly", {})
    times, now = h.get("time", []), now_utc()
    systems = {}
    for m in models:
        pr = ens_members(h, "precipitation", m)
        if not pr:
            continue
        st = ens_stats(pr, times, now)
        gu = ens_members(h, "wind_gusts_10m", m)
        if gu:
            mx = sorted(max((x or 0) for x in g[:24]) for g in gu)
            st["racha24"] = {"p50": _r(_pct(mx, 0.5), 0), "p90": _r(_pct(mx, 0.9), 0),
                             "prob": {str(th): round(sum(1 for x in mx if x >= th) / len(mx), 3) for th in (60, 80)}}
        hourly = list(zip(*[[x or 0 for x in s] for s in pr]))
        st["mediana_h"] = [_r(_pct(sorted(c), 0.5), 2) for c in hourly]
        st["p90_h"] = [_r(_pct(sorted(c), 0.9), 2) for c in hourly]
        systems[m] = {"nombre": SUPER_ENS[m][0], "familia": SUPER_ENS[m][1], **st}
    if not systems:
        raise RuntimeError("ensembles sin miembros")
    ths = list(next(iter(systems.values()))["ventanas"]["0-24"]["prob"])
    pooled = {}
    for w in ("0-24", "24-48", "48-72"):                 # mismo peso por SISTEMA, no por miembro
        pooled[w] = {th: round(sum(s["ventanas"][w]["prob"][th] for s in systems.values()) / len(systems), 3)
                     for th in ths}
    fam = {f: [s for s in systems.values() if s["familia"] == f] for f in ("física", "IA")}
    by_family = {f: {w: {th: round(sum(s["ventanas"][w]["prob"][th] for s in ss) / len(ss), 3) for th in ths}
                     for w in ("0-24", "24-48", "48-72")} for f, ss in fam.items() if ss}
    n = sum(s["n"] for s in systems.values())
    return SourceResult(name="superensemble", status="ok", kind="ensemble", data_time=now_utc().isoformat(),
                        detail=f"{len(systems)} sistemas · {n} miembros", payload={
                            "time": times, "sistemas": systems, "conjunto": pooled, "por_familia": by_family})


def src_marine_x() -> SourceResult:
    lat, lon = CFG["marine_point"]
    base = "https://marine-api.open-meteo.com/v1/marine"
    models = list(WAVE_MODELS)
    hw = _om_multi(base, {"hourly": ",".join(WAVE_VARS), "models": ",".join(models), "past_hours": 24,
                          "forecast_hours": 72}, [(lat, lon)])[0].get("hourly", {})
    waves = {}
    for m in models:
        d = {v: _by_model(hw, v, m, False) for v in WAVE_VARS}
        if any(x is not None for x in d["wave_height"]):
            waves[m] = {k: v for k, v in d.items() if any(x is not None for x in v)}
    oc = _om_multi(base, {"hourly": "ocean_current_velocity,ocean_current_direction,sea_surface_temperature,"
                                    "sea_level_height_msl,invert_barometer_height", "past_hours": 24,
                          "forecast_hours": 72}, [(lat, lon)])[0].get("hourly", {})
    if not waves:
        raise RuntimeError("ningún modelo de oleaje con datos")
    return SourceResult(name="mar_modelos", status="ok", kind="model", data_time=now_utc().isoformat(),
                        detail=f"{len(waves)}/{len(models)} modelos de oleaje + corrientes, SST y nivel del mar",
                        payload={"time": hw.get("time", []), "waves": waves, "ocean": oc})


def parse_opendap_ascii(txt: str) -> dict[str, list]:
    """Respuesta .ascii de OPeNDAP → {variable: valores aplanados}. Acepta vectores y matrices."""
    body = txt.split("---------------------------------------------", 1)[-1]
    out, cur = {}, None
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^([A-Za-z_][\w.]*)\[\d+\]", line)
        if m and not line.startswith("["):
            cur = m.group(1).split(".")[-1]
            out.setdefault(cur, [])
            continue
        if cur is None:
            continue
        vals = line.split(",")
        if line.startswith("["):
            vals = vals[1:]
        for v in vals:
            v = v.strip()
            if v:
                out[cur].append(None if v.lower() == "nan" else float(v))
    return out


def src_hfradar() -> SourceResult:
    """Corriente superficial del radar HF del canal de Ibiza (SOCIB): último corte con cobertura útil."""
    dds = http_get(HF_RADAR_URL + ".dds", timeout=40).decode("utf-8", "replace")
    nt = int(re.search(r"time\[time = (\d+)\]", dds).group(1))
    a = max(0, nt - 6)
    sl = f"[{a}:{nt - 1}][0:29][0:26]"
    q = ",".join(f"{v}{sl}" for v in ("U", "V", "QC_U", "QC_V"))
    data = parse_opendap_ascii(http_get(HF_RADAR_URL + ".ascii?" + urllib.parse.quote(f"time[{a}:{nt - 1}],LAT,LON," + q, safe=",:"),
                                        timeout=60).decode("utf-8", "replace"))
    lat, lon, times = data["LAT"], data["LON"], data["time"]
    ncell = len(lat) * len(lon)
    best = None
    for k in range(len(times) - 1, -1, -1):
        cells = []
        for i, la in enumerate(lat):
            for j, lo in enumerate(lon):
                idx = k * ncell + i * len(lon) + j
                u, v = data["U"][idx], data["V"][idx]
                if u is None or v is None or data["QC_U"][idx] != 1 or data["QC_V"][idx] != 1:
                    continue
                cells.append([round(la, 4), round(lo, 4), round(u, 3), round(v, 3)])
        if len(cells) >= 20:
            best = (k, cells)
            break
    if not best:
        raise RuntimeError("radar HF sin corte con cobertura suficiente en las últimas 6 h")
    k, cells = best
    sp = [math.hypot(c[2], c[3]) for c in cells]
    mu, mv = sum(c[2] for c in cells) / len(cells), sum(c[3] for c in cells) / len(cells)
    t = datetime.fromtimestamp(times[k], UTC)
    return SourceResult(name="radar_hf", status="ok", data_time=t.isoformat(),
                        detail=f"SOCIB radar HF canal de Ibiza · {len(cells)} celdas válidas",
                        payload={"t": t.isoformat(), "cells": cells, "bbox": [min(lat), max(lat), min(lon), max(lon)],
                                 "media": {"vel_ms": round(math.hypot(mu, mv), 3),
                                           "hacia_deg": round(math.degrees(math.atan2(mu, mv)) % 360),
                                           "max_ms": round(max(sp), 3), "p50_ms": round(_pct(sorted(sp), 0.5), 3)}})


def thin_rows(rows: list[dict], step_min: int = 10) -> list[dict]:
    """Series de 1 min (mareógrafo) → una muestra cada step_min minutos."""
    return [r for r in rows if parse_time(r["t"]).minute % step_min == 0]


def surge_residual(obs_rows: list[dict], model_t: list[str], model_lvl: list) -> dict:
    """Nivel observado y modelizado como ANOMALÍA respecto a su media en la ventana común (los ceros
    de referencia del mareógrafo y del modelo no coinciden). Residuo = obs − modelo."""
    mod = {parse_time(t + "Z"): v for t, v in zip(model_t, model_lvl) if v is not None}
    pairs = []
    for r in obs_rows:
        t = parse_time(r["t"])
        if r.get("nivel") is None or t.minute != 0 or t not in mod:
            continue
        pairs.append((t, r["nivel"], mod[t]))
    if len(pairs) < 6:
        return {}
    mo = sum(p[1] for p in pairs) / len(pairs)
    mm = sum(p[2] for p in pairs) / len(pairs)
    ser = [{"t": t.isoformat(), "obs": round(o - mo, 3), "mod": round(m - mm, 3), "res": round((o - mo) - (m - mm), 3)}
           for t, o, m in pairs]
    return {"n": len(ser), "serie": ser, "res_ultimo": ser[-1]["res"], "res_max": max(abs(s["res"]) for s in ser)}


# ════════════════════════════════════════════════════════════════════════
# FORENSE Y APRENDIZAJE
#   1. Archivo de observaciones propio: lecturas de pluviómetro con hora (14 días) y Hs horaria de boyas.
#   2. Previsiones TAL COMO SE EMITIERON (Open-Meteo Previous Runs): para cada hora válida, el valor del
#      run de ese día (D0, 0–24 h), del de la víspera (D1, 24–48 h) y del de dos días antes (D2, 48–72 h).
#   3. Forense: cada lectura se compara con la lluvia que cada modelo acumuló desde las 00 h local hasta
#      la hora de esa lectura → sesgo, error, aciertos/fallos, desfase temporal y desplazamiento del núcleo.
#   4. Aprendizaje: factor de corrección por modelo y antelación (con contracción hacia 1 y olvido
#      exponencial) y pesos por desempeño. Producto EXPERIMENTAL: nunca toca el aviso ni la precaución.
# ════════════════════════════════════════════════════════════════════════
FORENSIC = {
    "models": ["meteofrance_arome_france_hd", "icon_eu", "ecmwf_ifs025", "ecmwf_aifs025_single", "ncep_aigfs025"],
    "leads": {"D0": "precipitation", "D1": "precipitation_previous_day1", "D2": "precipitation_previous_day2"},
    "days": 14,                 # memoria del archivo y de la forense
    "half_life_d": 10.0,        # olvido exponencial: un par de hace 10 días pesa la mitad
    "n0": 5.0,                  # días de lluvia independientes para fiarse a medias del factor aprendido
    "n0_wave": 24.0,            # horas de boya equivalentes para el oleaje
    "min_window_h": 6.0,        # ventana mínima desde las 00 h local para comparar una lectura
    "thr": (10.0, 30.0),        # umbrales de contingencia (mm en la ventana)
    "clamp": (0.2, 5.0),
}
LEAD_OF_WINDOW = {"0-6": "D0", "6-12": "D0", "12-24": "D0", "24-48": "D1", "48-72": "D2"}


def _midnight_local(day: str) -> datetime:
    d = datetime.fromisoformat(day)
    return datetime(d.year, d.month, d.day, tzinfo=MADRID).astimezone(UTC)


def _ledger_end_utc(day: str, mins: int) -> datetime:
    """Minutos de reloj local; un día de cambio puede durar 23 o 25 horas."""
    d = datetime.fromisoformat(day)
    if mins == 1439:                                  # cierre completo del día
        return _midnight_local((d + timedelta(days=1)).date().isoformat())
    return (d + timedelta(minutes=mins)).replace(tzinfo=MADRID).astimezone(UTC)


def ledger_add(state: dict, sid: str, t_iso: str, total: float | None) -> str:
    """Añade una lectura (hora, total del día) al archivo. Devuelve qué hizo: ok | arrastre | descartada.
    Las estaciones que reinician a 00 UTC pueden mostrar antes del reinicio el total de AYER: ese valor es el
    total completo del día anterior y se archiva como tal (minuto 1439)."""
    if total is None:
        return "descartada"
    t = parse_time(t_iso)
    if t is None:
        return "descartada"
    lt = t.astimezone(MADRID)
    L = state.setdefault("obs_ledger", {}).setdefault(sid, {})
    day, mins, v = lt.date().isoformat(), lt.hour * 60 + lt.minute, int(round(total * 10))
    yday = (lt.date() - timedelta(days=1)).isoformat()
    prev = L.get(yday)
    if before_utc_daily_reset(t) and v > 0 and (prev is None or v >= prev[-1][1]):
        row = L.setdefault(yday, [])
        row[:] = [r for r in row if r[0] < 1439] + [[1439, v]]
        return "arrastre"
    if prev and lt.hour < 12 and v > 0 and v == prev[-1][1] and prev[-1][0] >= 1380:
        return "descartada"                             # copia exacta del total de ayer después del reinicio
    row = L.setdefault(day, [])
    earlier = [r[1] for r in row if r[0] < mins]
    if earlier and v + 5 < max(earlier):
        return "descartada"                             # el total del día no puede bajar (salvo redondeo)
    row[:] = [r for r in row if abs(r[0] - mins) >= 10] + [[mins, v]]
    row.sort()
    for d in [k for k in L if k < (lt.date() - timedelta(days=FORENSIC["days"])).isoformat()]:
        del L[d]
    return "ok"


def buoy_ledger_add(state: dict, name: str, rows: list[dict]) -> None:
    B = state.setdefault("buoy_ledger", {}).setdefault(name, {})
    for r in rows:
        if r.get("hm0") is None:
            continue
        t = parse_time(r["t"])
        if t and t.minute == 0:
            B[t.strftime("%Y-%m-%dT%H")] = int(round(r["hm0"] * 100))
    cut = (now_utc() - timedelta(days=FORENSIC["days"])).strftime("%Y-%m-%dT%H")    # 14 días hacia atrás
    for k in [k for k in B if k < cut]:
        del B[k]


def update_ledgers(state: dict, srcs: dict) -> dict:
    out = {"ok": 0, "arrastre": 0, "descartada": 0}
    mc = srcs.get("meteoclimatic")
    if mc and mc.status == "ok":
        for g in mc.payload["stations"]:
            if g.get("edad_min", 0) <= CFG["gauge_stale_min"]:
                out[ledger_add(state, g["id"], g["t"], g.get("lluvia_dia"))] += 1
    po = srcs.get("portus")
    if po and po.status == "ok":
        for name in CFG["portus_buoys"].values():
            buoy_ledger_add(state, name, po.payload["stations"].get(name, []))
    return out


def sidecar_dir() -> Path:
    """Directorio de los JSON del sidecar. Sobrescribible con METEO_SIDECAR_DIR."""
    return Path(os.environ.get("METEO_SIDECAR_DIR") or (HOME / "sidecar"))


def src_contexto() -> SourceResult:
    """Contexto escrito por un proceso aparte con dependencias propias (ver knowledge_base.py y CATALOGO-FUENTES.md).

    Es CONTEXTO: ni observación ni aviso ni modelo. kind='context' no participa en `fuse`. Sin ficheros válidos devuelve
    'deshabilitado' (UNKNOWN, no «sin riesgo»).
    """
    import knowledge_base as kb
    bundle = kb.context_bundle(sidecar_dir(), "portinatx", now_utc())
    detail = "; ".join(f"{n}={b['state']}" for n, b in bundle.items())
    ok = {n: b for n, b in bundle.items() if b["state"] == "ok"}
    if not ok:
        return SourceResult(name="contexto", status="deshabilitado",
                            detail="sin sidecar válido → contexto UNKNOWN (no calma): " + detail,
                            payload={"sidecars": bundle})
    newest = max(b["generated_at"] for b in ok.values())
    return SourceResult(name="contexto", status="ok", data_time=newest, detail=detail, payload={"sidecars": bundle})


def context_notes(ctx: SourceResult | None, rain: Channel) -> dict:
    """Sitúa la lluvia observada respecto a la climatología local del sidecar. SOLO informativo: no cambia niveles.

    Tabla esperada: values.precip_1h_mm = {p50,p90,p95,p99,max} (celda de reanálisis ~9 km, no punto de estación).
    """
    if ctx is None or ctx.status != "ok":
        return {"estado": "UNKNOWN", "notas": [], "detalle": ctx.detail if ctx else "fuente ausente",
                "aviso": "contexto no disponible: UNKNOWN, no «normal»"}
    import knowledge_base as kb
    clim = ((ctx.payload or {}).get("sidecars") or {}).get("climatologia_era5land") or {}
    table = (clim.get("data") or {}).get("precip_1h_mm") if clim.get("state") == "ok" else None
    notes = []
    for key, val in rain.metrics.items():
        if not key.endswith("_r1") or not isinstance(val, (int, float)) or isinstance(val, bool) or val <= 0:
            continue
        pr = kb.percentile_rank(val, table)
        if pr["band"] in ("UNKNOWN", "<p50"):
            continue
        notes.append({"estacion": key[:-3], "mm_1h": val, "banda": pr["band"], "rank": pr["rank"]})
    return {"estado": "ok", "notas": notes, "detalle": ctx.detail,
            "aviso": "contexto climatológico de celda ~9 km frente a un punto: indicio, no medida ni aviso"}


def forensic_points() -> list[tuple[str, str, float, float]]:
    return [("portinatx", "Portinatx", SITE["lat"], SITE["lon"])] + [(sid, nm, la, lo) for sid, (nm, la, lo) in CFG["mc_stations"].items()]


def src_forensic_models() -> SourceResult:
    """Previsiones archivadas tal como se emitieron, en los pluviómetros, para los últimos días."""
    pts = forensic_points()
    hv = ",".join(FORENSIC["leads"].values())
    today = now_utc().date()
    q = {"hourly": hv, "models": ",".join(FORENSIC["models"]), "timezone": "UTC",
         "start_date": (today - timedelta(days=FORENSIC["days"])).isoformat(), "end_date": today.isoformat()}
    res = _om_multi("https://previous-runs-api.open-meteo.com/v1/forecast", q, [(p[2], p[3]) for p in pts])
    out = {}
    for (sid, nm, la, lo), r in zip(pts, res):
        h = r.get("hourly", {})
        out[sid] = {"nombre": nm, "lat": la, "lon": lo, "time": h.get("time", []),
                    "m": {m: {L: h.get(f"{var}_{m}") or [] for L, var in FORENSIC["leads"].items()} for m in FORENSIC["models"]}}
    return SourceResult(name="forense_modelos", status="ok", kind="model", data_time=now_utc().isoformat(),
                        detail=f"{len(out)} puntos × {len(FORENSIC['models'])} modelos × D0/D1/D2 · {FORENSIC['days']} días",
                        payload={"points": out})


FORENSIC_GRID = {"lat": (38.50, 39.75), "lon": (0.75, 2.25), "step": 0.25, "leads": ("D0", "D1")}


def forensic_grid_points() -> list[tuple[float, float]]:
    g = dict(FORENSIC_GRID)
    if os.environ.get("PORTINATX_WIDE_GRID") == "1":
        g.update(lat=(38.25, 40.0), lon=(0.50, 2.75))  # 80 puntos; se lee después de config.env
    la = [round(g["lat"][0] + i * g["step"], 2) for i in range(int(round((g["lat"][1] - g["lat"][0]) / g["step"])) + 1)]
    lo = [round(g["lon"][0] + j * g["step"], 2) for j in range(int(round((g["lon"][1] - g["lon"][0]) / g["step"])) + 1)]
    return [(a, b) for a in la for b in lo]


def src_forensic_grid() -> SourceResult:
    """Lluvia diaria (día local) emitida por cada modelo en una malla regional de 0,25° alrededor de Ibiza."""
    pts = forensic_grid_points()
    today = now_utc().date()
    hv = ",".join(FORENSIC["leads"][L] for L in FORENSIC_GRID["leads"])
    q = {"hourly": hv, "models": ",".join(FORENSIC["models"]), "timezone": "UTC",
         "start_date": (today - timedelta(days=FORENSIC["days"])).isoformat(), "end_date": today.isoformat()}
    res = _om_multi("https://previous-runs-api.open-meteo.com/v1/forecast", q, pts)
    daily: dict = {}
    for k, r in enumerate(res):
        h = r.get("hourly", {})
        tt = h.get("time", [])
        for m in FORENSIC["models"]:
            for L in FORENSIC_GRID["leads"]:
                arr = h.get(f"{FORENSIC['leads'][L]}_{m}") or []
                acc: dict = {}
                for t, x in zip(tt, arr):
                    if x is None:
                        continue
                    t0 = (parse_time(t + "Z") - timedelta(hours=1)).astimezone(MADRID)        # la lluvia de T es la de la hora previa
                    acc[t0.date().isoformat()] = acc.get(t0.date().isoformat(), 0.0) + x
                for d, v in acc.items():
                    daily.setdefault(f"{m}|{L}", {}).setdefault(d, [None] * len(pts))[k] = round(v, 1)
    return SourceResult(name="forense_malla", status="ok", kind="model", data_time=now_utc().isoformat(),
                        detail=f"malla {len(pts)} puntos × {len(FORENSIC['models'])} modelos × D0/D1", payload={"pts": pts, "daily": daily})


def forensic_core_shift(state: dict, grid: dict) -> list[dict]:
    """Por día de lluvia: distancia y rumbo desde el centroide de la lluvia observada en Ibiza hasta el
    máximo diario del modelo en la malla regional, y qué fracción de su máximo puso sobre la red."""
    pts, out = grid["pts"], []
    led = state.get("obs_ledger") or {}
    coords = {sid: (la, lo) for sid, (nm, la, lo) in CFG["mc_stations"].items()}
    for key, days in grid["daily"].items():
        m, L = key.split("|")
        for d, vals in days.items():
            obs = [(coords[sid], rows[d][-1][1] / 10) for sid, rows in led.items() if sid in coords and d in rows and rows[d][-1][0] >= 600]
            so = sum(v for _, v in obs)
            if len(obs) < 5 or so < 40:
                continue
            co = (sum(c[0] * v for c, v in obs) / so, sum(c[1] * v for c, v in obs) / so)
            ok = [(pts[i], v) for i, v in enumerate(vals) if v is not None]
            if not ok:
                continue
            (pla, plo), vmax = max(ok, key=lambda x: x[1])
            near = [v for (a, b), v in ok if haversine_km(co[0], co[1], a, b) <= 20]
            dy, dx = (pla - co[0]) * 111.2, (plo - co[1]) * 111.2 * math.cos(math.radians(co[0]))
            out.append({"dia": d, "m": m, "L": L, "obs_media_mm": _r(so / len(obs), 1), "max_modelo_mm": _r(vmax, 1),
                        "max_lat": pla, "max_lon": plo, "dist_km": _r(math.hypot(dx, dy), 0), "rumbo_deg": round(math.degrees(math.atan2(dx, dy)) % 360),
                        "borde": pla in FORENSIC_GRID["lat"] or plo in FORENSIC_GRID["lon"],     # máximo en el borde: distancia mínima
                        "modelo_sobre_red_mm": _r(max(near), 1) if near else None,
                        "fraccion_en_red": _r(max(near) / vmax, 2) if near and vmax > 0 else None})
    return sorted(out, key=lambda r: (r["dia"], r["m"], r["L"]))


def src_forensic_marine() -> SourceResult:
    """Oleaje modelizado en la posición de cada boya (últimos días) para comparar con lo medido."""
    names = list(CFG["portus_buoys"].values())
    pts = [CFG["portus_coords"][n] for n in names]
    res = _om_multi("https://marine-api.open-meteo.com/v1/marine",
                    {"hourly": "wave_height", "models": ",".join(WAVE_MODELS), "past_days": 7, "forecast_days": 1}, pts)
    out = {}
    for n, r in zip(names, res):
        h = r.get("hourly", {})
        out[n] = {"time": h.get("time", []), "m": {m: h.get(f"wave_height_{m}") or [] for m in WAVE_MODELS}}
    return SourceResult(name="forense_mar", status="ok", kind="model", data_time=now_utc().isoformat(),
                        detail=f"{len(out)} boyas × {len(WAVE_MODELS)} modelos · 7 días", payload={"buoys": out})


def _cum_fc(times: list[datetime], vals: list, t0: datetime, t1: datetime) -> float | None:
    """Lluvia del modelo en (t0, t1]. La precipitación horaria de Open-Meteo en T es la de la hora previa;
    la hora parcial final se prorratea."""
    tot, need, got = 0.0, 0, 0
    for T, x in zip(times, vals):
        if t0 < T <= t1 + timedelta(minutes=59):
            frac = 1.0 if T <= t1 else max(0.0, 1 - (T - t1).total_seconds() / 3600)
            if frac <= 0:
                continue
            need += 1
            if x is None:
                continue
            got += 1
            tot += x * frac
    if need == 0 or got < need:
        return None
    return tot


def forensic_pairs(state: dict, fpay: dict, now: datetime) -> list[dict]:
    """Un par por (estación, día, modelo, antelación): última lectura del día frente al acumulado del modelo."""
    pairs = []
    for sid, days in (state.get("obs_ledger") or {}).items():
        P = fpay.get(sid)
        if not P:
            continue
        tt = [parse_time(t + "Z") for t in P["time"]]
        for day, rows in days.items():
            mins, v = rows[-1]
            if mins < FORENSIC["min_window_h"] * 60:
                continue
            t0 = _midnight_local(day)
            t1 = _ledger_end_utc(day, mins)
            age = (now - t1).total_seconds() / 86400
            for m, leads in P["m"].items():
                for L, arr in leads.items():
                    fc = _cum_fc(tt, arr, t0, t1)
                    if fc is None:
                        continue
                    pairs.append({"sid": sid, "est": P["nombre"], "dia": day, "h": round(mins / 60, 3), "m": m, "L": L,
                                  "obs": round(v / 10, 1), "fc": round(fc, 1), "edad_d": round(age, 2),
                                  "completo": mins >= 22 * 60})
    return pairs


def _w(age_d: float) -> float:
    return 0.5 ** (max(0.0, age_d) / FORENSIC["half_life_d"])


def forensic_scores(pairs: list[dict]) -> dict:
    out = {}
    for key in sorted({(p["m"], p["L"]) for p in pairs}):
        P = [p for p in pairs if (p["m"], p["L"]) == key]
        W = [_w(p["edad_d"]) for p in P]
        so, sf = sum(w * p["obs"] for w, p in zip(W, P)), sum(w * p["fc"] for w, p in zip(W, P))
        sw = sum(W)
        mae = sum(w * abs(p["fc"] - p["obs"]) for w, p in zip(W, P)) / sw
        rmse = math.sqrt(sum(w * (p["fc"] - p["obs"]) ** 2 for w, p in zip(W, P)) / sw)
        cont = {}
        for th in FORENSIC["thr"]:
            Q = [p for p in P if p["h"] >= 12]
            a = sum(1 for p in Q if p["obs"] >= th and p["fc"] >= th)
            b = sum(1 for p in Q if p["obs"] < th and p["fc"] >= th)
            c = sum(1 for p in Q if p["obs"] >= th and p["fc"] < th)
            cont[str(int(th))] = {"aciertos": a, "falsas": b, "fallos": c,
                                  "pod": _r(a / (a + c), 2) if a + c else None, "far": _r(b / (a + b), 2) if a + b else None,
                                  "csi": _r(a / (a + b + c), 2) if a + b + c else None}
        days_w = {}
        for w, p in zip(W, P):
            if p["obs"] >= 1 or p["fc"] >= 1:
                days_w[p["dia"]] = max(days_w.get(p["dia"], 0.0), w)
        out[f"{key[0]}|{key[1]}"] = {"m": key[0], "L": key[1], "n": len(P), "n_dias": len(days_w), "n_eff": _r(sum(days_w.values()), 2),
                                     "obs_mm": _r(so, 1),
                                     "fc_mm": _r(sf, 1), "ratio": _r(sf / so, 2) if so > 0 else None,
                                     "mae": _r(mae, 1), "rmse": _r(rmse, 1), "mae_rel": _r(mae / (so / sw), 2) if so > 0 else None,
                                     "contingencia": cont}
    return out


def forensic_displacement(pairs: list[dict]) -> list[dict]:
    """Por día, modelo y antelación: centroide de la lluvia observada frente al del modelo en las mismas
    estaciones (km y rumbo) y correlación espacial del patrón. Solo días con ≥5 estaciones y ≥40 mm sumados."""
    coords = {sid: (la, lo) for sid, (nm, la, lo) in CFG["mc_stations"].items()}
    out = []
    for key in sorted({(p["dia"], p["m"], p["L"]) for p in pairs}):
        P = [p for p in pairs if (p["dia"], p["m"], p["L"]) == key and p["sid"] in coords and p["h"] >= 12]
        so, sf = sum(p["obs"] for p in P), sum(p["fc"] for p in P)
        if len(P) < 5 or so < 40 or sf <= 0:
            continue
        co = (sum(p["obs"] * coords[p["sid"]][0] for p in P) / so, sum(p["obs"] * coords[p["sid"]][1] for p in P) / so)
        cf = (sum(p["fc"] * coords[p["sid"]][0] for p in P) / sf, sum(p["fc"] * coords[p["sid"]][1] for p in P) / sf)
        dy = (cf[0] - co[0]) * 111.2
        dx = (cf[1] - co[1]) * 111.2 * math.cos(math.radians(co[0]))
        xo, xf = [p["obs"] for p in P], [p["fc"] for p in P]
        mo, mf = sum(xo) / len(xo), sum(xf) / len(xf)
        cov = sum((a - mo) * (b - mf) for a, b in zip(xo, xf))
        den = math.sqrt(sum((a - mo) ** 2 for a in xo) * sum((b - mf) ** 2 for b in xf))
        out.append({"dia": key[0], "m": key[1], "L": key[2], "n": len(P), "obs_mm": _r(so, 1), "fc_mm": _r(sf, 1),
                    "desplaz_km": _r(math.hypot(dx, dy), 1), "rumbo_deg": round(math.degrees(math.atan2(dx, dy)) % 360),
                    "r_espacial": _r(cov / den, 2) if den > 0 else None})
    return out


def forensic_lag(state: dict, fpay: dict) -> dict:
    """Desfase temporal: desplaza la curva acumulada del modelo ±6 h y busca el ajuste a las lecturas del día
    (solo estación-días con ≥4 lecturas que cubren ≥6 h y ≥10 mm). Positivo = el modelo llega tarde."""
    res: dict[str, list[int]] = {}
    for sid, days in (state.get("obs_ledger") or {}).items():
        P = fpay.get(sid)
        if not P:
            continue
        tt = [parse_time(t + "Z") for t in P["time"]]
        for day, rows in days.items():
            rows = [r for r in rows if r[0] < 1439]
            if len(rows) < 4 or rows[-1][0] - rows[0][0] < 360 or rows[-1][1] < 100:
                continue
            t0 = _midnight_local(day)
            for m, leads in P["m"].items():
                arr = leads.get("D0") or []
                best = None
                for k in range(-6, 7):
                    err, ok = 0.0, True
                    for mins, v in rows:
                        fc = _cum_fc(tt, arr, t0 + timedelta(hours=k), t0 + timedelta(minutes=mins, hours=k))
                        if fc is None:
                            ok = False
                            break
                        err += abs(fc / max(1e-6, (_cum_fc(tt, arr, t0, t0 + timedelta(days=1)) or 1e-6)) - v / rows[-1][1])
                    if ok and (best is None or err < best[0]):
                        best = (err, k)
                if best:
                    res.setdefault(m, []).append(best[1])
    return {m: {"mediana_h": sorted(v)[len(v) // 2], "n": len(v)} for m, v in res.items()}


def forensic_waves(state: dict, mpay: dict) -> dict:
    out = {}
    led = state.get("buoy_ledger") or {}
    for name, P in mpay.items():
        obs = led.get(name, {})
        tt = [t[:13] for t in P["time"]]
        for m, arr in P["m"].items():
            pr = [(obs[t] / 100, x) for t, x in zip(tt, arr) if t in obs and x is not None]
            if len(pr) < 6:
                continue
            d = out.setdefault(m, {"n": 0, "so": 0.0, "sm": 0.0, "se2": 0.0, "pico_obs": 0.0, "pico_mod": 0.0})
            d["n"] += len(pr)
            d["so"] += sum(o for o, _ in pr)
            d["sm"] += sum(x for _, x in pr)
            d["se2"] += sum((x - o) ** 2 for o, x in pr)
            d["pico_obs"] = max(d["pico_obs"], max(o for o, _ in pr))
            d["pico_mod"] = max(d["pico_mod"], max(x for _, x in pr))
    for m, d in out.items():
        d.update({"ratio": _r(d["sm"] / d["so"], 2) if d["so"] else None, "sesgo_m": _r((d["sm"] - d["so"]) / d["n"], 2),
                  "rmse_m": _r(math.sqrt(d["se2"] / d["n"]), 2), "pico_obs": _r(d["pico_obs"], 2), "pico_mod": _r(d["pico_mod"], 2)})
        for k in ("so", "sm", "se2"):
            del d[k]
    return out


def learn(scores: dict, waves: dict) -> dict:
    """Factores de corrección con contracción hacia 1 (log-espacio) y pesos por desempeño."""
    lo, hi = FORENSIC["clamp"]
    fac, wts = {}, {}
    for k, s in scores.items():
        if not s["obs_mm"] or not s["fc_mm"] or s["fc_mm"] < 1:
            continue
        a = s["n_eff"] / (s["n_eff"] + FORENSIC["n0"])
        raw = min(hi, max(lo, s["obs_mm"] / s["fc_mm"]))
        fac[k] = {"factor": _r(math.exp(a * math.log(raw)), 2), "bruto": _r(raw, 2), "confianza": _r(a, 2), "n": s["n"], "n_dias": s["n_dias"]}
    for L in ("D0", "D1", "D2"):
        S = {k: s for k, s in scores.items() if s["L"] == L and s.get("mae_rel") is not None}
        if not S:
            continue
        sk = {s["m"]: 1 / (s["mae_rel"] + 0.2) for s in S.values()}
        tot = sum(sk.values())
        for s in S.values():
            a = s["n_eff"] / (s["n_eff"] + FORENSIC["n0"])
            wts[f"{s['m']}|{L}"] = _r((1 - a) / len(S) + a * sk[s["m"]] / tot, 3)
    wf = {}
    for m, d in waves.items():
        if d.get("ratio"):
            a = d["n"] / (d["n"] + FORENSIC["n0_wave"])
            wf[m] = {"factor": _r(math.exp(a * math.log(min(hi, max(lo, 1 / d["ratio"])))), 2), "n": d["n"], "confianza": _r(a, 2)}
    return {"factor_lluvia": fac, "peso": wts, "factor_oleaje": wf}


def corrected_outlook(modx_windows: dict, L: dict) -> dict:
    """Ventanas de Portinatx: bruto, corregido por modelo y consenso ponderado aprendido."""
    out = {}
    for w, lead in LEAD_OF_WINDOW.items():
        rows, num, den, raw = {}, 0.0, 0.0, []
        for m in FORENSIC["models"]:
            v = (modx_windows.get(m) or {}).get("lluvia", {}).get(w)
            if v is None:
                continue
            f = (L["factor_lluvia"].get(f"{m}|{lead}") or {}).get("factor")
            wt = L["peso"].get(f"{m}|{lead}")
            c = v * f if f else None
            rows[m] = {"bruto": v, "factor": f, "corregido": _r(c, 1) if c is not None else None, "peso": wt}
            raw.append(v)
            if c is not None and wt:
                num += wt * c
                den += wt
        out[w] = {"antelacion": lead, "modelos": rows, "media_bruta": _r(sum(raw) / len(raw), 1) if raw else None,
                  "consenso_aprendido": _r(num / den, 1) if den else None}
    return out


def lessons(scores: dict, disp: list[dict], lag: dict, waves: dict) -> list[str]:
    """disp = desplazamiento del núcleo en la malla regional (forensic_core_shift)."""
    name = lambda m: MODEL_INFO.get(m, (m,))[0]
    L = []
    d0 = sorted([s for s in scores.values() if s["L"] == "D0" and s["ratio"] is not None], key=lambda s: s["mae_rel"] or 9)
    if d0:
        b = d0[0]
        L.append(f"Mejor modelo a 0–24 h: {name(b['m'])} (error medio {b['mae']} mm, {b['ratio']}× lo medido; {b['n_dias']} días de lluvia, {b['n']} lecturas).")
        for s in sorted(d0, key=lambda s: abs(math.log(max(s['ratio'], 0.01)))):
            if s["ratio"] < 0.6:
                L.append(f"{name(s['m'])} a 0–24 h se queda corto: prevé {s['ratio']}× lo medido ({s['n_dias']} días).")
            elif s["ratio"] > 1.6:
                L.append(f"{name(s['m'])} a 0–24 h se pasa: prevé {s['ratio']}× lo medido ({s['n_dias']} días).")
    for L2 in ("D1", "D2"):
        S = [s for s in scores.values() if s["L"] == L2 and s["ratio"] is not None]
        if S:
            b = min(S, key=lambda s: s["mae_rel"] or 9)
            L.append(f"Con {L2[1]} {'día' if L2 == 'D1' else 'días'} de antelación el más útil fue {name(b['m'])} ({b['ratio']}× lo medido, {b['n_dias']} días).")
    big = [d for d in disp if d["L"] == "D0"]
    for m in sorted({d["m"] for d in big}):
        dd = [d for d in big if d["m"] == m]
        km = sorted(d["dist_km"] for d in dd)[len(dd) // 2]
        if km >= 25:
            rb = sorted(d["rumbo_deg"] for d in dd)[len(dd) // 2]
            fr = sorted(d["fraccion_en_red"] or 0 for d in dd)[len(dd) // 2]
            edge = sum(1 for d in dd if d.get("borde")) > len(dd) / 2
            L.append(f"{name(m)} puso el máximo diario a {'≥' if edge else ''}{int(km)} km al {_rumbo(rb)} de donde llovió (mediana de {len(dd)} días"
                     f"{'; máximo en el borde de la malla' if edge else ''}); sobre la red dejó {int(fr * 100)} % de ese máximo.")
    for m, v in lag.items():
        if v["n"] >= 3 and v["mediana_h"]:
            L.append(f"{name(m)} llega {abs(v['mediana_h'])} h {'tarde' if v['mediana_h'] > 0 else 'pronto'} (mediana de {v['n']} estación-días).")
    for m, d in waves.items():
        if d.get("ratio") and d["ratio"] < 0.8:
            L.append(f"Oleaje: {WAVE_MODELS.get(m, m)} se queda en {d['ratio']}× lo medido en las boyas (pico {d['pico_mod']} m frente a {d['pico_obs']} m).")
    return L


def _rumbo(deg: float) -> str:
    return ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][int((deg + 22.5) // 45) % 8]


def forensic_bundle(state: dict, srcs: dict, modx_windows: dict | None) -> dict:
    fm, fw = srcs.get("forense_modelos"), srcs.get("forense_mar")
    now = now_utc()
    pairs = forensic_pairs(state, fm.payload["points"], now) if fm and fm.status == "ok" else []
    scores = forensic_scores(pairs)
    disp = forensic_displacement(pairs)
    fg = srcs.get("forense_malla")
    core = forensic_core_shift(state, fg.payload) if fg and fg.status == "ok" else []
    lag = forensic_lag(state, fm.payload["points"]) if fm and fm.status == "ok" else {}
    waves = forensic_waves(state, fw.payload["buoys"]) if fw and fw.status == "ok" else {}
    L = learn(scores, waves)
    day = now.astimezone(MADRID).date().isoformat()
    hist = state.setdefault("learn_hist", {})
    hist[day] = {k: v["factor"] for k, v in L["factor_lluvia"].items()}
    for d in sorted(hist)[:-60]:
        del hist[d]
    return {"pares": pairs, "puntuacion": scores, "desplazamiento": disp, "nucleo": core, "malla": fg.payload if fg and fg.status == "ok" else None,
            "desfase": lag, "oleaje": waves,
            "aprendizaje": L, "aprendizaje_regimen": regime_learning(state, pairs),
            "corregido": corrected_outlook(modx_windows or {}, L), "lecciones": lessons(scores, core, lag, waves),
            "historial_aprendizaje": hist, "dias": sorted({p["dia"] for p in pairs}),
            "archivo": {sid: {d: len(r) for d, r in days.items()} for sid, days in (state.get("obs_ledger") or {}).items()},
            "config": {k: FORENSIC[k] for k in ("days", "half_life_d", "n0", "thr", "clamp")}}


REGIMES = ("dana_levante", "conveccion_estival", "frente_atlantico")


def label_episode(state: dict, episode: str, start: str, end: str, regime: str) -> None:
    """Etiquetas explícitas con trazabilidad; no deduce el régimen de la lluvia posterior."""
    first, last = datetime.fromisoformat(start).date(), datetime.fromisoformat(end).date()
    if regime not in REGIMES or not episode.strip() or not 0 <= (last - first).days <= 31:
        raise ValueError("episodio vacío, régimen desconocido o fechas inválidas (máximo 32 días)")
    labels = state.setdefault("regime_calendar", {})
    for i in range((last - first).days + 1):
        labels[(first + timedelta(days=i)).isoformat()] = {"episode": episode, "regime": regime}


def regime_learning(state: dict, pairs: list[dict]) -> dict:
    """Factores descriptivos por régimen; bloqueados hasta tres episodios independientes.

    Aun superado ese mínimo, nunca se aplican automáticamente al diagnóstico.
    """
    labels = state.get("regime_calendar", {})
    out = {}
    for regime in REGIMES:
        selected = [p for p in pairs if labels.get(p["dia"], {}).get("regime") == regime]
        scores = forensic_scores(selected)
        eligible = {}
        for key, score in scores.items():
            episodes = {labels[p["dia"]]["episode"] for p in selected
                        if f"{p['m']}|{p['L']}" == key and max(p["obs"], p["fc"]) >= 1}
            score["n_episodios"] = len(episodes)
            if len(episodes) >= 3:
                eligible[key] = score
        out[regime] = {"puntuacion": scores, "aprendizaje": learn(eligible, {}),
                       "min_episodios": 3, "aplicacion_automatica": False,
                       "estado": "experimental" if eligible else "muestra_insuficiente"}
    return out


def forensic_backfill(state: dict, dirs: list[str]) -> dict:
    """Rellena el archivo de observaciones con instantáneas congeladas (cycles/*.json) y con gauge_hist de
    estados guardados. Cada lectura pasa por los mismos filtros que en vivo."""
    seen, cnt = set(), {"ok": 0, "arrastre": 0, "descartada": 0}
    reads, buoys = [], []
    for d in dirs:
        p = Path(d)
        files = list(p.glob("cycles/*.json")) + list(p.glob("*.json"))
        for f in files:
            try:
                s = json.loads(f.read_text())
            except Exception:
                continue
            st = s.get("state", s)
            for sid, hist in (st.get("gauge_hist") or {}).items():
                reads += [(r["t"], sid, r["total"]) for r in hist]
            for ch in s.get("channels", []) or []:
                if ch.get("name") == "pluviometros":
                    reads += [(g["t"], g["id"], g["total"]) for g in (ch.get("metrics") or {}).get("stations", []) or []]
                if ch.get("name") == "mar_boyas" and s.get("issued_utc"):
                    for e in ch.get("evidence", []):
                        mm = re.match(r"^(Boya [^:]+): Hs ([\d.]+) m.*\((\d\d):(\d\d) local", e)
                        if not mm:
                            continue
                        iss = parse_time(s["issued_utc"]).astimezone(MADRID)
                        t = iss.replace(hour=int(mm.group(3)), minute=int(mm.group(4)), second=0)
                        if t > iss:
                            t -= timedelta(days=1)
                        buoys.append((mm.group(1), t.astimezone(UTC).isoformat(), float(mm.group(2))))
    for t, sid, tot in sorted(reads):
        if (t, sid) in seen:
            continue
        seen.add((t, sid))
        cnt[ledger_add(state, sid, t, tot)] += 1
    for name in {b[0] for b in buoys}:
        buoy_ledger_add(state, name, [{"t": t, "hm0": h} for n, t, h in buoys if n == name])
    cnt["boyas_h"] = sum(len(v) for v in (state.get("buoy_ledger") or {}).values())
    return cnt


# ════════════════════════════════════════════════════════════════════════
# APLICACIÓN EN TIEMPO REAL — carga útil estructurada para visualizar el motor
#   core   : ejes de alarma, avisos, decisión, gobernanza, canales, fuentes, historial
#   radar  : rejillas de dBZ por frame + métricas
#   series : boyas/viento PORTUS, pluviómetros, modelos (punto, ensemble, oleaje), trayectorias de núcleo
# Cada parte cabe en un documento de 256 KiB (base de datos del artifact).
# ════════════════════════════════════════════════════════════════════════
def _r(x, n=2):
    return None if x is None else round(x, n)


def _pct(vals: list[float], q: float) -> float | None:
    v = sorted(x for x in vals if x is not None)
    if not v:
        return None
    k = (len(v) - 1) * q
    f = int(k)
    return v[f] + (v[min(f + 1, len(v) - 1)] - v[f]) * (k - f)


def build_app(snap: dict, state: dict) -> dict[str, dict]:
    srcs: dict[str, SourceResult] = snap.get("_srcs", {})
    ok = lambda n: srcs.get(n) is not None and srcs[n].status == "ok"
    # ── núcleo ──
    warnings = []
    for nm in ("aemet_cap", "meteoalarm"):
        if ok(nm):
            warnings += srcs[nm].payload["warnings"]
    seen, wl = set(), []
    for w in sorted(warnings, key=lambda w: (w.get("onset") or "", -w["rank"])):
        k = (w["nivel"], w.get("tipo"), w["evento"].lower(), w.get("onset"), w.get("expires"))
        if k in seen:
            continue
        seen.add(k)
        wl.append({"nivel": w["nivel"], "rank": w["rank"], "tipo": w.get("tipo", ""), "evento": w["evento"],
                   "desde": w.get("onset"), "hasta": w.get("expires"), "activo": bool(w.get("activo_ahora")),
                   "umbral": w.get("descripcion") or w.get("parametro", "")})
    hist = []
    try:
        with open(HOME / "log.jsonl") as fh:
            for line in fh.readlines()[-CFG["app_history"]:]:
                r = json.loads(line)
                hist.append({"id": r["id"], "level": r["level"], "nowcast": r["nowcast"]})
    except FileNotFoundError:
        pass
    gv = snap["governance"]
    core = {
        "cycle_id": snap["cycle_id"], "issued": snap["issued_utc"], "engine": snap["engine"], "site": SITE,
        "official": {**{k: v for k, v in snap["official_warning"].items() if k != "vigente"}, "all": wl},
        "warning_changes": snap.get("warning_changes", []),
        "hazard": snap["observed_local_hazard"],
        "precaution": {k: v for k, v in snap["operational_precaution"].items()},
        "nowcast": snap["nowcast"],
        "outlook": {"level": snap["level"], "proposed": snap["proposed"], "transition": snap["transition"],
                    "reasons": snap["reasons"]},
        "coverage": snap["coverage"],
        "governance": {"claims": gv["claims"], "claims_count": gv["claims_count"],
                       "dissent": state.get("dissent", [])[-20:], "anomalies": state.get("anomalies", [])[-20:],
                       "overrides": gv["overrides"], "predictions": state.get("predictions", [])[-30:],
                       "predictions_summary": gv["predictions"]["summary"], "bias": gv["bias_radar_gauge"],
                       "episode": gv["episode"]},
        "channels": [{**{k: c[k] for k in ("name", "level", "kind", "confidence", "evidence", "available", "local")},
                      "data_time": c.get("data_time"), "age_min": (c.get("metrics") or {}).get("age_min")}
                     for c in snap["channels"]],
        "sources": snap["sources"],
        "history": hist,
    }
    # ── radar ──
    rg = CFG["radar_grid"]
    radar = {"geometry": {"lat_n": SITE["lat"] + rg["dlat"], "lon_w": SITE["lon"] - rg["dlon"], "step": rg["step"],
                          "nlat": int(round(2 * rg["dlat"] / rg["step"])) + 1,
                          "nlon": int(round(2 * rg["dlon"] / rg["step"])) + 1,
                          "encoding": "base64 uint8: 0 sin eco, 1 eco sin tabular, ≥2 dBZ"},
             "metrics_radius_km": CFG["radar_radius_km"], "frames": [], "status": srcs["radar"].status if "radar" in srcs else "—"}
    if ok("radar"):
        for f in srcs["radar"].payload["frames"][-rg["frames"]:]:
            radar["frames"].append({"time": f["time"], "dup": f["dup"], "grid": f.get("grid"),
                                    "cover": f["cover"], "nearest_km": _r(f["nearest_km"], 1),
                                    "nearest_strong_km": _r(f["nearest_strong_km"], 1),
                                    "max_dbz_30km": f["max_dbz_30km"], "max_dbz_15km": f["max_dbz_15km"],
                                    "site_max_dbz": f["site_max_dbz"],
                                    "qpe": {k: _r(v, 1) for k, v in f["qpe_site_mmh"].items()}})
    # ── series ──
    series: dict[str, Any] = {"portus": {}, "gauges": [], "models": {}, "ensemble": None, "marine": None, "tracks": {}}
    if ok("portus"):
        for name, rows in srcs["portus"].payload["stations"].items():
            keep = ("t", "hm0", "hmax", "tp", "dmd", "vv_md", "vv_mx", "dv_md")
            series["portus"][name] = {"coords": CFG["portus_coords"].get(name),
                                      "kind": "boya" if name in CFG["portus_buoys"].values() else "viento",
                                      "rows": [x for x in ({k: (_r(r[k]) if k != "t" else r[k]) for k in keep if k in r}
                                                           for r in rows) if len(x) > 1][-60:]}   # ≤10 h: límite de 256 KiB por documento
    if ok("meteoclimatic"):
        gh = state.get("gauge_hist", {})
        for g in srcs["meteoclimatic"].payload["stations"]:
            series["gauges"].append({"id": g["id"], "nombre": g["nombre"], "lat": g["lat"], "lon": g["lon"],
                                     "dist_km": _r(g["dist_km"], 1), "t": g["t"], "edad_min": _r(g["edad_min"], 0),
                                     "total": g["lluvia_dia"], "T": g["T"], "viento": g["viento"],
                                     "near": g["dist_km"] <= CFG["gauge_near_km"],
                                     "hist": gh.get(g["id"], [])[-24:]})
    if ok("openmeteo_det"):
        for m, pts in srcs["openmeteo_det"].payload.items():
            p0 = pts[0] if pts else {}
            nb = [max((x for x in v if x is not None), default=None)
                  for v in zip(*[p["pr"] for p in pts if p.get("pr")])] if pts else []
            series["models"][m] = {"time": p0.get("time", []), "pr": p0.get("pr", []), "gust": p0.get("gust", []),
                                   "cape": p0.get("cape", []), "pr_neigh_max": nb}
    if ok("openmeteo_ens"):
        mem = srcs["openmeteo_ens"].payload["members"]
        if mem:
            n = len(mem[0])
            cols = [[m[i] for m in mem] for i in range(n)]
            acc = [sum(x or 0 for x in m) for m in mem]
            base_t = srcs["openmeteo_det"].payload[next(iter(srcs["openmeteo_det"].payload))][0]["time"][0] \
                if ok("openmeteo_det") else None
            series["ensemble"] = {"n": len(mem), "start": base_t,
                                  "p10": [_r(_pct(c, .1)) for c in cols], "p50": [_r(_pct(c, .5)) for c in cols],
                                  "p90": [_r(_pct(c, .9)) for c in cols], "max": [_r(max(x or 0 for x in c)) for c in cols],
                                  "total72": {"p10": _r(_pct(acc, .1), 1), "p50": _r(_pct(acc, .5), 1),
                                              "p90": _r(_pct(acc, .9), 1), "max": _r(max(acc), 1)}}
    if ok("marine"):
        h = srcs["marine"].payload
        series["marine"] = {"time": h.get("time", []), "hs": h.get("wave_height", []),
                            "dir": h.get("wave_direction", []), "tp": h.get("wave_period", [])}
    for m, runs in (state.get("runs") or {}).items():
        series["tracks"][m] = [{k: r.get(k) for k in ("init", "max12", "max_lat", "max_lon", "max_dist_km",
                                                      "local12", "local6", "local1", "centered")}
                               for r in runs if parse_time(r.get("init"))]     # fuera claves de runs sin hora verificada
    # superficie: METAR (24 h) por aeródromo
    series["surface"] = {}
    if ok("metar"):
        for icao, pts in srcs["metar"].payload["series"].items():
            series["surface"][icao] = [{"t": p.t.isoformat(), "T": p.T, "Td": p.Td, "P": p.P,
                                        "U": _r(p.U, 0), "G": _r(p.G, 0), "D": p.D} for p in pts]
    # ensemble: probabilidad de superación por hora y trazas acumuladas (punto y vecindad)
    if ok("openmeteo_ens") and series.get("ensemble"):
        pp = srcs["openmeteo_ens"].payload["per_point"]
        mem = pp[0] if pp else []
        n = len(mem[0]) if mem else 0
        thr = (1, 5, 10, 20)
        series["ensemble"]["exceed"] = {str(t): [round(sum(1 for m in mem if (m[i] or 0) >= t) / len(mem), 3)
                                                 for i in range(n)] for t in thr}
        def cum(v):
            acc, out = 0.0, []
            for x in v:
                acc += x or 0
                out.append(round(acc, 1))
            return out
        series["ensemble"]["cum"] = [cum(m)[::3] for m in mem]          # cada 3 h
        tot24 = lambda m: sum((x or 0) for x in m[:24])
        series["ensemble"]["p24_point"] = {str(t): round(sum(1 for m in mem if tot24(m) >= t) / len(mem), 3)
                                           for t in (10, 30, 50, 100)}
        # vecindad: algún punto de la vecindad supera (máximo por miembro entre puntos)
        if len(pp) > 1:
            nm = min(len(x) for x in pp)
            series["ensemble"]["p24_neigh"] = {str(t): round(sum(1 for j in range(nm)
                                               if max(tot24(pp[k][j]) for k in range(len(pp))) >= t) / nm, 3)
                                               for t in (10, 30, 50, 100)}
        series["ensemble"]["hist24"] = sorted(round(tot24(m), 1) for m in mem)
    # atmósfera
    atmos = {"status": {k: {"estado": v[0], "nota": v[1]} for k, v in INDEX_STATUS.items()},
             "composites_spec": COMPOSITES, "profile": None}
    top = 400.0
    if ok("relieve"):
        rel = srcs["relieve"].payload
        top = float(max(v for row in rel["rows"] for v in row if v is not None))
        atmos["terrain"] = rel
    if ok("batimetria"):
        atmos["bathy"] = srcs["batimetria"].payload
    if ok("perfil"):
        atmos["profile"] = derive_profile(srcs["perfil"].payload["hourly"], srcs["perfil"].payload["units"],
                                          srcs["perfil"].payload.get("stencil"), top)
        atmos["units"] = srcs["perfil"].payload["units"]
        atmos["model"] = CFG.get("profile_model", "best_match")
    gch = next((c for c in snap["channels"] if c["name"] == "pluviometros"), None)
    if gch:
        atmos["irh"] = irh_now(Channel(**gch), series.get("models"))
        atmos["gauges_now"] = gch.get("metrics", {}).get("stations", [])
    atmos["thresholds"] = {"rain_1h": CFG["rain_1h"], "rain_1h_wet": CFG["rain_1h_wet"], "rain_12h": CFG["rain_12h"],
                           "rain_day_wet": CFG["rain_day_wet"], "sat_mm": CFG["sat_mm"], "zr": CFG["zr"],
                           "radar_alert_dbz": CFG["radar_alert_dbz"], "gauge_near_km": CFG["gauge_near_km"]}
    # METAR: estación, distancia y antigüedad
    if ok("metar"):
        series["metar_meta"] = []
        for icao, m in srcs["metar"].payload.get("meta", {}).items():
            if m.get("lat") is None:
                continue
            series["metar_meta"].append({"icao": icao, **m, "dist_km": round(haversine_km(SITE["lat"], SITE["lon"], m["lat"], m["lon"]), 0),
                                         "edad_min": round((now_utc() - parse_time(m["last"])).total_seconds() / 60)})
    # modelos frente a pluviómetros: lluvia desde las 00 local y ventanas futuras
    if ok("modelos_pluvio"):
        today0 = now_utc().astimezone(MADRID).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
        obs = {g["nombre"]: g for g in (srcs["meteoclimatic"].payload["stations"] if ok("meteoclimatic") else [])}
        rows = []
        for p in srcs["modelos_pluvio"].payload["points"]:
            tt = [parse_time(t + "Z") for t in p["time"]]
            r = {"nombre": p["nombre"], "obs_hoy": (obs.get(p["nombre"]) or {}).get("lluvia_dia"), "modelos": {}}
            for m, v in p["models"].items():
                past = sum((x or 0) for t, x in zip(tt, v) if t and today0 <= t <= now_utc())
                fut = {w: round(sum((x or 0) for t, x in zip(tt, v) if t and now_utc() + timedelta(hours=a) <= t < now_utc() + timedelta(hours=b)), 1)
                       for w, (a, b) in {"0-3": (0, 3), "3-6": (3, 6), "6-12": (6, 12), "12-24": (12, 24)}.items()}
                r["modelos"][m] = {"hoy": round(past, 1), "ventanas": fut}
            rows.append(r)
        series["verif"] = {"desde": today0.isoformat(), "filas": rows}
    # campo explícito por ventanas (rejilla AROME HD / ICON-EU)
    if ok("model_grid"):
        series["fields"] = {m: {"cells": g.get("cells"), "win": g.get("win"), "init": g.get("init")}
                            for m, g in srcs["model_grid"].payload.items() if g.get("win")}
    sat = {"layers": {}, "bbox": None, "status": srcs["satelite"].status if "satelite" in srcs else "—"}
    if ok("satelite"):
        sat = {**srcs["satelite"].payload, "status": "ok"}
    return {"core": core, "radar": radar, "series": series, "atmos": atmos, "sat": sat,
            "mar": build_mar(srcs, ok), "modx": (modx := build_modx(srcs, ok)), "forense": build_forense(snap, modx)}


def build_forense(snap: dict, modx: dict) -> dict:
    fb = snap.get("_forense")
    if not fb:
        return {"status": "sin datos"}
    models = FORENSIC["models"]
    out = {k: v for k, v in fb.items() if k != "pares"}
    out["corregido"] = corrected_outlook(modx.get("ventanas") or {}, fb["aprendizaje"])
    out["modelos"] = models
    out["info"] = {m: MODEL_INFO.get(m, (m, "", ""))[0] for m in models}
    out["estaciones"] = {sid: {"nombre": nm, "lat": la, "lon": lo} for sid, (nm, la, lo) in CFG["mc_stations"].items()}
    out["pares_cols"] = ["sid", "dia", "h", "modelo", "L", "obs", "fc", "completo"]
    out["pares"] = [[q["sid"], q["dia"], q["h"], models.index(q["m"]), q["L"], q["obs"], q["fc"], int(q["completo"])]
                    for q in fb["pares"] if q["m"] in models]
    out["status"] = {k: INDEX_STATUS[k][0] for k in ("forense", "aprendizaje")}
    return out


def build_modx(srcs: dict, ok: Callable[[str], bool]) -> dict:
    """Deterministas físicos e IA por ventanas en Portinatx + superensemble."""
    out = {"info": {m: {"nombre": a, "familia": b, "res": c} for m, (a, b, c) in MODEL_INFO.items()},
           "status": {k: INDEX_STATUS[k][0] for k in ("modelos_ia", "superens")}}
    now = now_utc()
    if ok("modelos_x"):
        P = srcs["modelos_x"].payload
        tt = P["time"]
        rows = {}
        for m, d in P["models"].items():
            tq = [parse_time(t + "Z") for t in tt]
            fut = lambda var, a, b: [x for t, x in zip(tq, d.get(var, [])) if t and x is not None
                                     and now + timedelta(hours=a) <= t < now + timedelta(hours=b)]
            rows[m] = {"lluvia": {w: _r(v, 1) for w, v in window_sums(tt, d.get("precipitation", []), now).items()},
                       "racha_max": {w: _r(max(fut("wind_gusts_10m", a, b), default=None), 0)
                                     for w, (a, b) in {"0-24": (0, 24), "24-48": (24, 48)}.items()},
                       "cape_max": {w: _r(max(fut("cape", a, b), default=None), 0)
                                    for w, (a, b) in {"0-24": (0, 24), "24-48": (24, 48)}.items()}}
        out.update({"time": tt, "series": {m: {"pr": d.get("precipitation"), "gust": d.get("wind_gusts_10m"),
                                               "mslp": d.get("pressure_msl")} for m, d in P["models"].items()},
                    "ventanas": rows, "fuente": srcs["modelos_x"].detail})
    if ok("superensemble"):
        out["superens"] = srcs["superensemble"].payload
        out["superens_fuente"] = srcs["superensemble"].detail
    return out


def build_mar(srcs: dict, ok: Callable[[str], bool]) -> dict:
    """Mar: oleaje multi-modelo frente a boyas, partición, corrientes, SST, nivel del mar y radar HF."""
    out = {"punto": CFG["marine_point"], "modelos_info": WAVE_MODELS,
           "status": {k: INDEX_STATUS[k][0] for k in ("oleaje_multi", "surge", "radar_hf")}}
    now = now_utc()
    if ok("mar_modelos"):
        P = srcs["mar_modelos"].payload
        out.update({"time": P["time"], "waves": P["waves"], "ocean": P["ocean"]})
        tq = [parse_time(t + "Z") for t in P["time"]]
        k_now = min(range(len(tq)), key=lambda i: abs((tq[i] - now).total_seconds())) if tq else None
        cons = {}
        for m, d in P["waves"].items():
            hs = d.get("wave_height", [])
            nxt = [x for t, x in zip(tq, hs) if x is not None and now <= t < now + timedelta(hours=24)]
            cons[m] = {"hs_ahora": hs[k_now] if k_now is not None and k_now < len(hs) else None,
                       "hs_max24": max(nxt, default=None),
                       "fondo_ahora": (d.get("swell_wave_height") or [None] * (k_now + 1))[k_now] if k_now is not None else None,
                       "viento_ahora": (d.get("wind_wave_height") or [None] * (k_now + 1))[k_now] if k_now is not None else None,
                       "dir_ahora": (d.get("wave_direction") or [None] * (k_now + 1))[k_now] if k_now is not None else None,
                       "tp_ahora": ((d.get("wave_peak_period") or d.get("wave_period") or [None] * (k_now + 1))[k_now]
                                    if k_now is not None else None)}
        vals = sorted(c["hs_max24"] for c in cons.values() if c["hs_max24"] is not None)
        out["consenso"] = {"modelos": cons, "hs_max24_min": vals[0] if vals else None,
                           "hs_max24_max": vals[-1] if vals else None, "hs_max24_med": _r(_pct(vals, 0.5), 2) if vals else None}
    if ok("portus"):
        st = srcs["portus"].payload["stations"]
        out["boyas"] = {n: [{k: r.get(k) for k in ("t", "hm0", "hmax", "tp", "dmd", "ts2", "vc_md", "dc_md")} for r in st[n]]
                        for n in CFG["portus_buoys"].values() if n in st}
        tg = st.get(CFG["tide_gauge"], [])
        out["mareografo"] = {"nombre": CFG["tide_gauge"], "serie": [{"t": r["t"], "nivel": r.get("nivel")} for r in tg if r.get("nivel") is not None],
                             "refs": srcs["portus"].payload.get("refs", {}).get(CFG["tide_gauge"], {})}
        if ok("mar_modelos"):
            oc = srcs["mar_modelos"].payload["ocean"]
            out["surge"] = surge_residual(tg, oc.get("time", []), oc.get("sea_level_height_msl", []))
    if ok("radar_hf"):
        out["hf"] = srcs["radar_hf"].payload
    return out


def write_app(parts: dict[str, dict]) -> Path:
    d = HOME / "app"
    d.mkdir(parents=True, exist_ok=True)
    for k, v in parts.items():
        tmp = d / f"{k}.json.tmp"
        tmp.write_text(json.dumps(v, ensure_ascii=False, separators=(",", ":"), default=str))
        tmp.replace(d / f"{k}.json")
    return d


def cmd_serve(interval: int, port: int, open_browser: bool = False) -> None:
    """Aplicación local en tiempo real: un hilo ejecuta el ciclo; el navegador lee /api/<parte>.json."""
    import threading
    import http.server
    import socket
    page_bytes = resource_bytes("portinatx_app.html")
    lock = threading.Lock()

    wake = threading.Event()
    status = {"running": False, "last_cycle": "", "last_end": "", "last_error": "", "next_at": "", "interval_s": interval}

    def loop():
        state = load_state()
        while True:
            status["running"] = True
            try:
                with lock:
                    snap = cycle(state)
                    persist(snap, state)
                    write_app(build_app(snap, state))
                status.update(last_cycle=snap["cycle_id"], last_error="")
                print(f"[{now_utc():%H:%M:%SZ}] {snap['cycle_id']} precaución={snap['nowcast']['level']}", flush=True)
            except Exception as exc:
                status["last_error"] = f"{type(exc).__name__}: {exc}"[:300]
                traceback.print_exc()
            status.update(running=False, last_end=now_utc().isoformat(),
                          next_at=(now_utc() + timedelta(seconds=interval)).isoformat())
            wake.wait(interval)                        # el botón «Actualizar» despierta el bucle antes de tiempo
            wake.clear()

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, code: int, obj: dict):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if self.path.split("?")[0] != "/api/refresh":
                self.send_error(404)
                return
            if self.headers.get("Origin") not in (None, f"http://localhost:{port}", f"http://127.0.0.1:{port}"):
                self.send_error(403)                   # solo la propia página puede pedir un ciclo
                return
            already = status["running"]
            wake.set()
            self._json(202, {"ok": True, "already_running": already, **status})

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/api/status":
                return self._json(200, {"mode": "local", **status})
            if path in ("/", "/index.html"):
                body, ctype = page_bytes, "text/html; charset=utf-8"
            elif path.startswith("/api/") and path.endswith(".json") and path[5:-5] in ("core", "radar", "series", "atmos", "sat", "mar", "modx", "forense"):
                f = HOME / "app" / path[5:]
                if not f.exists():
                    self.send_error(503, "primer ciclo en curso")
                    return
                body, ctype = f.read_bytes(), "application/json"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    srv = None
    for p in range(port, port + 20):                   # puerto ocupado → el siguiente libre
        try:
            srv = http.server.ThreadingHTTPServer(("127.0.0.1", p), H)
            port = p
            break
        except OSError:
            continue
    if srv is None:
        raise SystemExit(f"no hay puerto libre entre {port} y {port + 19}")
    threading.Thread(target=loop, daemon=True).start()
    url = f"http://localhost:{port}"
    print(f"Portinatx Nowcast {VERSION} → {url}  (ciclo cada {interval} s · datos en {HOME})", flush=True)
    print("Cierra esta ventana o pulsa Ctrl+C para detenerlo.", flush=True)
    if open_browser:
        import webbrowser
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("detenido", flush=True)


# ════════════════════════════════════════════════════════════════════════
# COMANDOS ESTÁTICOS
# ════════════════════════════════════════════════════════════════════════
def cmd_static() -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    bbox = (1.30, 38.98, 1.62, 39.135)               # Es Amunts + costa N (lon/lat)
    base = "https://ideib.caib.es/pregeoserveis/rest/services/public/2021btib5000/MapServer/25/query"
    feats, off, page_n = [], 0, 500
    try:
        while True:
            q = urllib.parse.urlencode({"where": "1=1", "geometry": ",".join(map(str, bbox)),
                                        "geometryType": "esriGeometryEnvelope", "inSR": 4326, "outSR": 4326,
                                        "spatialRel": "esriSpatialRelIntersects", "outFields": "*",
                                        "f": "geojson", "resultOffset": off, "resultRecordCount": page_n})
            page = get_json(f"{base}?{q}", timeout=120, retries=2)
            fs = page.get("features", [])
            feats += fs
            print(f"   curvas: {len(feats)}…", end="\r")
            if len(fs) < page_n:
                break
            off += page_n
    except Exception as exc:
        print(f"curvas BTIB interrumpidas en {len(feats)} entidades: {exc} "
              "(el servicio de consultas de IDEIB falló el 16/10/2026; reintenta más tarde)")
    if feats:
        out = HOME / "es_amunts_curvas_btib5000.geojson"
        out.write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
        print(f"curvas BTIB 1:5000 (5 m, maestras 25 m): {len(feats)} entidades → {out}")
    # perfil batimétrico EMODnet al N de la bocana (✔ verificado 16/10/2026; fuente GEBCO/EMODnet, grano grueso)
    try:
        line = "LINESTRING(1.5214 39.118, 1.5214 39.30)"
        prof = get_json(f"https://rest.emodnet-bathymetry.eu/depth_profile?geom={urllib.parse.quote(line)}")
        (HOME / "batimetria_perfil_N_portinatx.json").write_text(json.dumps(prof))
        print("perfil batimétrico N de Portinatx guardado")
    except Exception as exc:
        print(f"batimetría EMODnet no disponible: {exc}")


def cmd_climo() -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    for path, name in (("/api/valores/climatologicos/normales/estacion/B954", "normales_B954.json"),
                       ("/api/valores/climatologicos/valoresextremos/parametro/P/estacion/B954",
                        "extremos_precip_B954.json")):
        try:
            raw = _aemet(path)
            (HOME / name).write_bytes(raw)
            print(f"guardado {name}")
            if "normales" in name:
                for row in json.loads(raw.decode("latin-1")):
                    if str(row.get("mes")) == "10":
                        print(f"   octubre normal B954: p_mes={row.get('p_mes_md')} mm, "
                              f"días tormenta={row.get('n_tor_md')}")
        except Exception as exc:
            print(f"{name}: {exc}")


CATALOG = [   # (fuente, acceso, estado de validación)
    ("METAR/SPECI aviationweather.gov LEIB LEPA LEVC LEAL LEMH", "sin clave", "probado en vivo"),
    ("MeteoAlarm feed España + CAP por aviso (ES113 = 645301)", "sin clave", "probado en vivo; cubre D y D+1"),
    ("AEMET OpenData observación B908X / B954", "AEMET_API_KEY", "documentado; semántica de 'prec' leída de metadatos"),
    ("AEMET OpenData CAP área esp, zona 645301", "AEMET_API_KEY", "documentado; parser probado con CAP reales vía MeteoAlarm"),
    ("Open-Meteo AROME HD / ECMWF / ICON-EU, punto + vecindad", "sin clave (10 000 llamadas/día)", "probado en vivo"),
    ("Open-Meteo rejilla 0,15° + meta.json de runs", "sin clave", "probado en vivo; caché por run"),
    ("Open-Meteo ensemble ECMWF IFS 0,25", "sin clave", "probado en vivo"),
    ("Open-Meteo Marine (oleaje modelizado, no rompiente)", "sin clave", "probado en vivo"),
    ("RainViewer z7 Universal Blue → dBZ (tabla oficial) + QPE Marshall–Palmer y tropical", "sin clave (100 pet./min)", "probado en vivo 18/10"),
    ("Meteoclimatic feed XML ESIBA (lluvia diaria, T, viento)", "sin clave (condiciones de uso del feed)", "probado en vivo 18/10"),
    ("PORTUS Puertos del Estado: boyas 2720/2630/2820, puertos 4815/4814, 3856, 4802", "sin clave", "probado en vivo 18/10"),
    ("WU PWS ISANTJ159 (API oficial)", "WU_API_KEY (solo con PWS propia)", "documentado; no se lee la web pública"),
    ("SOCIB boya Canal de Ibiza (OPeNDAP ascii)", "SOCIB_BUOY_URL", "pendiente de URL de v1.2.1"),
    ("EUMETSAT MTG-LI EO:EUM:DAT:0691", "EUMETSAT_KEY/SECRET + netCDF4", "experimental, sin probar"),
    ("EMODnet batimetría (static)", "sin clave", "probado en vivo"),
    ("IDEIB BTIB curvas 5 m (static)", "sin clave", "metadatos OK; consultas caídas el 16/10"),
    ("Nivel del mar de mareógrafos PORTUS", "—", "el tipo WATER devuelve 500: pendiente"),
]


def cmd_catalog() -> None:
    for src, acc, st in CATALOG:
        print(f"· {src}\n    acceso: {acc} · estado: {st}")


def cmd_inspect_cap(path: str, at: str) -> None:
    now = parse_time(at) if at else now_utc()
    raw = Path(path).read_bytes()
    blobs = [raw]
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as tf:
            blobs = [tf.extractfile(m).read() for m in tf.getmembers()
                     if m.isfile() and m.name.lower().endswith(".xml")]
    except tarfile.TarError:
        pass
    warns = parse_cap_documents(blobs, CFG["aemet_zone"], now, 72)
    print(json.dumps({"evaluado_a": now.isoformat(), "documentos": len(blobs), "avisos_zona": warns},
                     ensure_ascii=False, indent=1))


def cmd_radar_colors() -> None:
    r = run_source("radar", "obs", src_radar)
    if r.status != "ok":
        print(r.status, r.detail); return
    last = r.payload["frames"][-1]["colors"]
    print("color      píxeles  dBZ (tabla oficial Universal Blue)")
    for c, n in sorted(last.items(), key=lambda kv: -kv[1])[:40]:
        d = color_to_dbz(int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16))
        print(f"{c}  {n:>7}  {'—' if d is None else f'{d:.0f}'}")


# ════════════════════════════════════════════════════════════════════════
# SELFTEST — pruebas de LÓGICA, no de calibración
# ════════════════════════════════════════════════════════════════════════
def _mk_png(w, h, rgba_fn) -> bytes:
    raw = b"".join(b"\x00" + bytes(v for x in range(w) for v in rgba_fn(x, y)) for y in range(h))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def selftest() -> int:
    ok = 0; fail = 0
    def check(name, cond):
        nonlocal ok, fail
        print(("  ✔ " if cond else "  ✘ ") + name)
        ok += cond; fail += (not cond)
    t0 = datetime(2026, 10, 18, 6, 0, tzinfo=UTC)
    def ser(vals):
        return [Point(t=t0 + timedelta(minutes=10 * i), T=a, Td=b, P=c, U=d, G=e) for i, (a, b, c, d, e) in enumerate(vals)]
    calm = ser([(24, 20, 1012.0, 15, 20)] * 6 + [(24, 20, 1012.0, 15, 22)])
    check("calma → none", gust_front(calm)["level"] == "none")
    gf = ser([(24, 20, 1012.0, 15, 20)] * 6 + [(19, 17, 1014.0, 50, 75)])
    check("ΔT−5 ΔP+2 ΔU+60 ΔTd−3 → confirmed", gust_front(gf)["level"] == "confirmed")
    surge = ser([(24, 20, 1012.0, 15, 20)] * 6 + [(21, 20, 1011.8, 45, 60)])
    v = gust_front(surge)
    check("enfriamiento+viento SIN subida de presión → no detectado (puerta dura)", not v["detected"])
    # CAP
    cap = f"""<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2"><info><language>es-ES</language>
      <event>Aviso de lluvias de nivel naranja</event><onset>2026-10-18T00:00:00+02:00</onset>
      <expires>2026-10-18T23:59:59+02:00</expires>
      <parameter><valueName>AEMET-Meteoalerta nivel</valueName><value>naranja</value></parameter>
      <parameter><valueName>AEMET-Meteoalerta parametro</valueName><value>PR; 100 mm en 12 h</value></parameter>
      <area><areaDesc>Ibiza y Formentera</areaDesc><geocode><valueName>AEMET-Meteoalerta zona</valueName>
      <value>645301</value></geocode></area></info></alert>""".encode()
    w = parse_cap_documents([cap], "645301", datetime(2026, 10, 16, 12, tzinfo=UTC), 36)
    check("CAP naranja 645301 dentro de 36 h → rank 2", len(w) == 1 and w[0]["rank"] == 2 and not w[0]["activo_ahora"])
    w2 = parse_cap_documents([cap], "645301", datetime(2026, 10, 15, 0, tzinfo=UTC), 36)
    check("CAP fuera del horizonte → ignorado", w2 == [])
    # fusión
    inst = Channel("aviso_aemet", 2, "institutional", available=True)
    model3 = Channel("modelo_x", 3, "model")
    f = fuse([inst, model3, Channel("lluvia_observada", 0, "obs")])
    check("aviso naranja + modelo extremo → alert (modelo no da alarm)", f["proposed"] == "alert")
    f = fuse([inst, Channel("lluvia_observada", 2, "obs", local=True), Channel("radar", 2, "obs")])
    check("obs alert LOCAL + radar alert (otra raíz) → alarm por confirmación", f["proposed"] == "alarm")
    f = fuse([Channel("aviso_aemet", 0, "institutional"), Channel("lluvia_observada", 2, "obs")])
    check("una sola obs en alert sin apoyo → alert", f["proposed"] == "alert")
    f = fuse([inst, Channel("lluvia_observada", 2, "obs"),
              Channel("escorrentia_torrentes", 2, "obs", group="lluvia_observada")])
    check("lluvia + escorrentía (misma fuente) no se confirman entre sí → alert", f["proposed"] == "alert")
    # histéresis
    st = {"level": "alert", "pending_down": 0}
    seq = [apply_hysteresis("quiet", st)[0] for _ in range(3)]
    check("desescalada: 2 ciclos retiene, al 3.º baja un escalón", seq == ["alert", "alert", "watch"])
    st = {"level": "watch", "pending_down": 2}
    check("escalada inmediata", apply_hysteresis("alarm", st)[0] == "alarm")
    # PNG + radar
    blob = _mk_png(4, 3, lambda x, y: (10 * x, 20 * y, 200, 255 if x == 2 else 0))
    wpx, hpx, px = png_decode(blob)
    check("decodificador PNG RGBA", (wpx, hpx) == (4, 3) and px[2] == (20, 0, 200, 255) and px[0][3] == 0)
    z = 7
    tx, ty = _tile_xy(SITE["lat"], SITE["lon"], z)
    tile = _mk_png(256, 256, lambda x, y: (0, 80, 255, 255))
    m = radar_frame_metrics({(int(tx), int(ty)): tile}, z, {})
    check("radar: tesela llena → cobertura 100 % a ≤10 km, eco a <1 km",
          m["cover"][10] == 1.0 and m["nearest_km"] is not None and m["nearest_km"] < 1.5)
    check("sector abierto N (290–60°) contiene 0° y 330°, no 90°",
          in_sector(0, (290, 60)) and in_sector(330, (290, 60)) and not in_sector(90, (290, 60)))
    check("rolling 12 h", _rolling_max([0] * 5 + [10] * 12 + [0] * 5, 12) == 120)
    # rejilla + seguimiento por run
    cells = [(SITE["lat"], SITE["lon"]), (39.0, 0.8)]
    gsum = summarize_grid(cells, [[12.0] * 10, [30.0] * 10])
    check("rejilla: núcleo lejano detectado y 'local' ≤20 km separado",
          gsum["max12"] == 300 and gsum["max_dist_km"] > 50 and gsum["local12"] == 120)
    st = {}
    m = "meteofrance_arome_france_hd"
    base = {"max12": 150.0, "max_lat": 39.1, "max_lon": 1.5, "max_dist_km": 2.0, "local12": 150.0,
            "local6": 90.0, "local1": 40.0, "cells_ge100_12h": 3}
    t1 = update_run_tracks(st, {m: {**base, "init": "2026-10-17T00:00"}})
    t1b = update_run_tracks(st, {m: {**base, "init": "2026-10-17T00:00"}})
    t2 = update_run_tracks(st, {m: {**base, "max_lon": 1.3, "init": "2026-10-17T03:00"}})
    check("mismo run no cuenta doble; 2 runs distintos centrados → consecutivos=2",
          t1[m]["centered_consecutive"] == 1 and t1b[m]["centered_consecutive"] == 1
          and t2[m]["centered_consecutive"] == 2 and t2[m]["displacement_km"] > 15)
    _, gate = ch_trajectory(t2)
    f1 = fuse([inst, Channel("radar", 1, "obs", local=True)], hr_gate=gate)
    f0 = fuse([inst, Channel("radar", 0, "obs")], hr_gate=gate)
    ffar = fuse([inst, Channel("radar", 1, "obs", local=False)], hr_gate=gate)
    check("gate interno: 2 runs + eco local → alarm; eco lejano (≤60 km) o sin eco → alert",
          f1["proposed"] == "alarm" and f0["proposed"] == "alert" and ffar["proposed"] == "alert")
    st_gap = {}
    update_run_tracks(st_gap, {m: {**base, "init": "2026-10-17T03:00"}})
    tg = update_run_tracks(st_gap, {m: {**base, "init": "2026-10-17T15:00"}})
    check("runs centrados con intermedios sin ver (03Z→15Z) no cuentan como seguidos",
          tg[m]["centered_consecutive"] == 1)
    old = [Point(t=now_utc() - timedelta(minutes=90), T=20, P=1010, RR=5.0)]
    check("QC estación casera: dato de hace 90 min descartado", "retraso" in pws_qc(old))
    zero, wet = [[0.0] * 30 for _ in range(10)], [[5.0] * 30] * 5 + [[0.0] * 30] * 5
    ens = SourceResult("openmeteo_ens", "ok", "ensemble", payload={"members": zero, "per_point": [zero, wet]})
    ce = ch_ensemble(ens)
    check("ensemble: 50 % en la vecindad no se confunde con 0 % en el punto",
          "P(24h≥50)=0%" in ce.evidence[-1] and "P(24h≥50)=50%" in ce.evidence[0])
    holes = [[1.0] * 10 + [None] * 20 for _ in range(12)]
    ce2 = ch_ensemble(SourceResult("openmeteo_ens", "ok", "ensemble", payload={"members": holes}))
    check("ensemble: miembros sin ventana de 24 h completa → canal no opina", not ce2.available)
    # ── semántica de prec, ensemble, radar, cobertura y confirmación ──
    rows = [{"fint": f"2026-10-18T0{h}:00:00", "prec": v} for h, v in ((5, 2.0), (6, 5.0), (7, 9.0))]
    cum = aemet_rows_to_points(rows, "cumulative")
    hr = aemet_rows_to_points(rows, "hourly")
    check("AEMET prec acumulado: incrementos 3,0 y 4,0 (no 5 y 9)", [p.R1 for p in cum] == [None, 3.0, 4.0])
    check("AEMET prec horario: valor tal cual", [p.R1 for p in hr] == [2.0, 5.0, 9.0])
    gap = aemet_rows_to_points([{"fint": "2026-10-18T05:00:00", "prec": 1.0},
                                {"fint": "2026-10-18T08:00:00", "prec": 7.0}], "hourly")
    check("AEMET horario con hueco de 3 h: no se asume que es lluvia de 1 h", gap[1].R1 is None)
    gusty = ser([(24, 20, 1012.0, 20, 55)] * 6 + [(24, 20, 1012.0, 20, 60)])
    check("frente de racha: racha 60 vs rachas previas 55 (no vs viento medio 20) → none",
          gust_front(gusty)["level"] == "none" and abs(gust_front(gusty)["dU"] - 5) < 1e-6)
    rain_alert = Channel("lluvia_observada", 2, "obs")
    f = fuse([inst, rain_alert, Channel("modelo_x", 2, "model", group="nwp_hr")])
    check("un modelo NO confirma una observación → alert, no alarm", f["proposed"] == "alert")
    f = fuse([inst, Channel("radar", 0, "obs")])
    check("1 canal observado → cobertura insuficiente declarada", f["insufficient"])
    st = {"level": "alert"}
    check("con cobertura insuficiente no se desescala",
          all(apply_hysteresis("quiet", st, insufficient=True)[0] == "alert" for _ in range(4)))
    def frames(dbzs):
        return SourceResult("radar", "ok", payload={"frames": [
            {"time": f"2026-10-18T06:{10 * i:02d}:00+00:00", "dup": False, "cover": {10: 0, 30: 0.2, 60: 0.3},
             "nearest_km": 12.0, "nearest_strong_km": 12.0, "max_dbz_30km": d, "max_dbz_15km": d,
             "site_max_dbz": 30, "qpe_site_mmh": {"marshall_palmer": 3.0, "tropical": 4.0}}
            for i, d in enumerate(dbzs)]})
    one, two = ch_radar(frames([20, 20, 55])), ch_radar(frames([20, 55, 55]))
    def far_frames(nk, c30):
        return SourceResult("radar", "ok", payload={"frames": [
            {"time": f"2026-10-18T06:{10 * i:02d}:00+00:00", "dup": False, "cover": {10: 0, 30: c30, 60: 0.3},
             "nearest_km": nk, "nearest_strong_km": None, "max_class_30km": 0} for i in range(3)]})
    check("radar: eco a 50 km no es local; eco a 15 km con 20 % a ≤30 km sí",
          not ch_radar(far_frames(50.0, 0.0)).local and ch_radar(far_frames(15.0, 0.2)).local)
    check("radar: 1 frame fuerte aislado no pasa de watch; 2 de 3 → alert (el radar solo nunca da alarm)",
          one.level == 1 and two.level == 2)
    # ── pruebas de aceptación v0.5 (auditoría 18/10) ──
    check("dBZ: color oficial ff9500 → 42 dBZ; color ajeno a la escala → None",
          color_to_dbz(0xff, 0x95, 0x00) == 42.0 and color_to_dbz(0x12, 0x34, 0x56) is None)
    mp, tr = zr_rate(42, *CFG["zr"]["marshall_palmer"]), zr_rate(42, *CFG["zr"]["tropical"])
    rq = ch_radar(frames([42, 42, 42]))
    check("QPE: a 42 dBZ tropical ≈ 2× Marshall–Palmer y AMBAS figuran en la evidencia",
          14 < mp < 17 and 30 < tr < 34 and any("marshall_palmer" in e and "tropical" in e for e in rq.evidence))
    nowt = datetime(2026, 10, 18, 10, 30, tzinfo=UTC)
    feed = ("<stations>" + "".join(
        f"<station><id>{sid}</id><pubDate>{pub}</pubDate><stationdata><temperature><now>17</now></temperature>"
        f"<wind><now>3</now><max>20</max></wind><rain><unit>mm</unit><total>{tot}</total></rain></stationdata></station>"
        for sid, pub, tot in [("ESIBA0700000207817A", "Sun, 18 Oct 2026 10:25:00 +0000", 80.0),
                              ("ESIBA0700000207815B", "Sun, 18 Oct 2026 08:00:00 +0000", 40.0)]) + "</stations>")
    stns = parse_meteoclimatic(feed, nowt)
    gch = ch_gauges(SourceResult("meteoclimatic", "ok", payload={"stations": stns}), {})
    far = [e for e in gch.evidence if "Sant Jordi" in e][0]
    check("pluviómetro lejano con 80 mm → no se atribuye a Portinatx (techo watch, no local, distancia explícita)",
          gch.level <= 1 and not gch.local and "a 2" in far and "vecina" not in far)
    check("pluviómetro con dato viejo → STALE, sin inferir 0",
          any("Sant Miquel" in e and "STALE" in e for e in gch.evidence))
    allstale = ch_gauges(SourceResult("meteoclimatic", "ok", payload={"stations": [stns[1]]}), {})
    check("todas las estaciones STALE → canal no disponible (UNKNOWN), no 'quiet'", not allstale.available)
    st2 = {}
    near = {**stns[1], "edad_min": 5, "t": "2026-10-18T10:10:00+00:00", "lluvia_dia": 40.0}
    ch_gauges(SourceResult("m", "ok", payload={"stations": [near]}), st2)
    near2 = {**near, "t": "2026-10-18T10:25:00+00:00", "lluvia_dia": 52.0}
    g2 = ch_gauges(SourceResult("m", "ok", payload={"stations": [near2]}), st2)
    check("vecina: 12 mm en 15 min → 48 mm/h por diferencia entre ciclos → alert y señal local",
          g2.level == 2 and g2.local and any("48.0 mm/h" in e for e in g2.evidence))
    red = {"nivel": "rojo", "rank": 3, "evento": "Aviso de lluvias de nivel rojo", "onset": "2026-10-18T08:00:00+00:00",
           "expires": "2026-10-18T11:59:59+00:00", "activo_ahora": True, "descripcion": "90 mm en 1 h", "parametro": ""}
    orange = {**red, "nivel": "naranja", "rank": 2, "evento": "Aviso de lluvias de nivel naranja",
              "onset": "2026-10-18T12:00:00+00:00", "expires": "2026-10-18T15:59:59+00:00"}
    sp = {}
    ofr = official_state(Channel("aviso_aemet_activo", 3, "institutional"), Channel("aviso_aemet", 3, "institutional"), [red])
    lv, _ = apply_hysteresis("alarm", sp, "nowcast_level")
    check("rojo válido → aviso oficial rojo y precaución ALARM inmediata", ofr["level_now"] == "alarm" and lv == "alarm")
    ofo = official_state(Channel("aviso_aemet_activo", 2, "institutional"), Channel("aviso_aemet", 2, "institutional"),
                         [{**red, "activo_ahora": False}, orange])
    lv2, _ = apply_hysteresis("alert", sp, "nowcast_level")
    check("rojo expira y entra naranja → aviso oficial NARANJA (no rojo congelado); la precaución puede seguir en alarm",
          ofo["vigente"]["nivel"] == "naranja" and ofo["level_now"] == "alert" and lv2 == "alarm")
    man = manual_obs({"manual_obs": {"runoff": {"value": "observed", "t": (now_utc() - timedelta(hours=1)).isoformat()}}}, now_utc())
    held = all(apply_hysteresis("watch", sp, "nowcast_level", hold=precaution_hold(man))[0] == "alarm" for _ in range(5))
    check("escorrentía observada + aviso degradado → la precaución no desescala", held)
    old = manual_obs({"manual_obs": {"runoff": {"value": "observed", "t": (now_utc() - timedelta(hours=9)).isoformat()}}}, now_utc())
    check("escorrentía manual caduca a las 6 h (deja de retener)", precaution_hold(old) is None)
    hz = local_hazard_state({"radar": Channel("radar", available=False)}, {})
    check("radar sin datos → UNKNOWN en peligro local, nunca 'quiet'", hz["radar"]["estado"] == "UNKNOWN")
    global HOME
    import tempfile
    saved = HOME
    with tempfile.TemporaryDirectory() as td:
        HOME = Path(td)
        calls = {"n": 0}
        def good():
            calls["n"] += 1
            return SourceResult("x", "ok", "model", data_time="t", detail="d", payload={"v": 1})
        def bad():
            raise RuntimeError("HTTP Error 429")
        r1 = cached_source("x", 15, good)(); r2 = cached_source("x", 15, good)()
        _cache_save("x", {**_cache_load("x"), "fetched": (now_utc() - timedelta(hours=2)).isoformat()})
        r3 = cached_source("x", 15, bad)()
        check("caché: 2.ª llamada no toca la API; con 429 sirve la última buena marcada",
              calls["n"] == 1 and "caché" in r2.detail and r3.status == "ok" and "API falló" in r3.detail
              and r3.payload == {"v": 1})
        _cache_save("x", {**_cache_load("x"), "fetched": (now_utc() - timedelta(hours=7)).isoformat()})
        try:
            cached_source("x", 15, bad)()
            too_old = False
        except RuntimeError as exc:
            too_old = "demasiado vieja" in str(exc)
        check("caché: con la API caída, una copia de 7 h no se sirve como actual (fuente sin dato)", too_old)
        st0 = {"level": "watch", "pending_down": 1, "bias": {"Sant Llorenç": 3.2}}
        persist_state_only(st0)
        (HOME / "log.jsonl").write_text("".join(json.dumps({"id": f"C{i}", "level": "watch", "nowcast": "alarm"}) + "\n" for i in range(300)))
        pk = pack_state(Path(td) / "pk.json")
        (HOME / "state.json").unlink(); (HOME / "log.jsonl").unlink()
        st1 = unpack_state(pk)
        lg = (HOME / "log.jsonl").read_text().splitlines()
        check("estado portátil: ida y vuelta conserva calibración y cola del historial",
              st1 == st0 and load_state() == st0 and len(lg) == CFG["app_history"] and json.loads(lg[-1])["id"] == "C299")
    HOME = saved
    # CAP real de AEMET reemitido por MeteoAlarm (17/10/2026), recortado
    ma = b"""<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
      <identifier>2.49.0.0.724.0.ES.261017091609.645301PRP1181328569</identifier>
      <sent>2026-10-17T09:16:09+00:00</sent><status>Actual</status><msgType>Alert</msgType>
      <info><language>es-ES</language><event>Aviso de lluvias de nivel naranja</event>
      <onset>2026-10-18T09:00:00+02:00</onset><expires>2026-10-18T14:59:59+02:00</expires>
      <description>Precipitaci\xc3\xb3n acumulada en una hora: 50 mm.</description>
      <parameter><valueName>awareness_level</valueName><value>3; orange; Severe</value></parameter>
      <area><areaDesc>Ibiza y Formentera</areaDesc><geocode><valueName>EMMA_ID</valueName>
      <value>ES113</value></geocode></area></info></alert>"""
    w = parse_cap_documents([ma], "645301", datetime(2026, 10, 17, 12, tzinfo=UTC), 36)
    check("CAP formato MeteoAlarm (awareness_level + ES113) → naranja con umbral",
          len(w) == 1 and w[0]["rank"] == 2 and "50 mm" in w[0]["descripcion"])
    ex = ma.replace(b"<status>Actual</status>", b"<status>Exercise</status>")
    check("CAP de ejercicio ignorado", parse_cap_documents([ex], "645301", datetime(2026, 10, 17, 12, tzinfo=UTC), 36) == [])
    mallorca = ma.replace(b"645301PRP", b"645203COCO").replace(b"<value>ES113</value>", b"<value>ES872</value>") \
                 .replace(b"Ibiza y Formentera", b"Costa - Norte y nordeste de Mallorca")
    check("CAP costero de Mallorca → no se aplica a Portinatx",
          parse_cap_documents([mallorca], "645301", datetime(2026, 10, 17, 12, tzinfo=UTC), 36) == [])
    # ════ REGRESIÓN DANA 17–20/10/2026 (F1–F13) + GOBERNANZA Ante ════
    print("── regresión DANA (F1–F13) y gobernanza ──")
    T = datetime(2026, 10, 18, 9, 30, tzinfo=UTC)
    def gch(rate, total=40.0, near=True, lvl=None, fresh=True):
        c = Channel("pluviometros", kind="obs", group="pluviometros", available=fresh)
        c.metrics = {"near_fresh": 1 if (near and fresh) else 0, "near_rate_max": rate if near else None,
                     "stations": [{"id": "S1", "nombre": "Sant Miquel", "dist_km": 7.0 if near else 30.0,
                                   "near": near, "total": total, "rate": rate, "t": T.isoformat()}]}
        c.level = lvl if lvl is not None else (level_from(rate, CFG["rain_1h"]) if rate is not None else 0)
        return c
    OFF = lambda now, d36=None: {"level_now": now, "level_36h": d36 or now, "verificado": True}
    D = lambda cur, pro, **kw: deescalation_decision(cur, pro, **{**dict(gauges=None, radar=None, official=OFF("quiet"),
                                 manual_hold=None, insufficient=False, dissent=[], anomalies=[], overrides={}), **kw})
    # F1 — aviso rojo no detectado ~90 min
    with tempfile.TemporaryDirectory() as td:
        HOME = Path(td)
        os.environ.pop("NTFY_URL", None)
        stw = {}
        detect_warning_changes(stw, [orange], T)
        ch1 = detect_warning_changes(stw, [orange, red], T)
        ch2 = detect_warning_changes(stw, [orange, red], T + timedelta(minutes=5))
        res = notify(ch1, "NWC-test")
        check("F1 aviso rojo nuevo → ESCALADA + NUEVO, registrado en alerts.jsonl; repetido no vuelve a sonar",
              ch1 and ch1[0]["kind"] == "ESCALADA" and ch1[0]["a"] == "alarm" and any(c["kind"] == "NUEVO" for c in ch1)
              and ch2 == [] and (HOME / "alerts.jsonl").exists() and res.startswith("registrado"))
    HOME = saved
    # F2 — desescalada por dBZ máximo (10:25): sustitución de métrica
    rad_low = Channel("radar", 0, "obs"); rad_low.metrics = {"nearest_km": 12.0, "qpe_now": {"marshall_palmer": 1.0}}
    d2 = D("alarm", "watch", gauges=Channel("pluviometros", available=False), radar=rad_low, official=OFF("watch"))
    check("F2 alarm→watch con radar flojo y SIN pluviómetro → HOLD, veto del retador",
          d2["decision"] == "HOLD" and d2["challenger"]["verdict"] == "VETO"
          and any(c["code"] == "CHALLENGER_VETO" for c in d2["open_conditions"]))
    d2b = D("alarm", "watch", gauges=gch(48.0), radar=rad_low, official=OFF("watch"))
    check("F2 pluviómetro vecino a 48 mm/h contradice la bajada → VETO", d2b["challenger"]["verdict"] == "VETO")
    d2c = D("alarm", "watch", gauges=gch(0.4), radar=rad_low, official=OFF("watch"))
    check("F2 pluviómetro vecino fresco a 0,4 mm/h → retador sin objeción, PROCEED",
          d2c["decision"] == "PROCEED" and d2c["challenger"]["verdict"] == "NO_OBJECTION")
    sh = {"nowcast_level": "alarm"}
    held2 = all(apply_hysteresis("watch", sh, "nowcast_level", hold="CHALLENGER_VETO")[0] == "alarm" for _ in range(6))
    check("F2 con HOLD la precaución no baja aunque pasen 6 ciclos", held2)
    # F3 — Marshall–Palmer infraestima lluvia cálida: se mide, se avisa, no se cambia sola
    zr0 = json.dumps(CFG["zr"])
    sb = {}
    r3 = Channel("radar", 1, "obs"); r3.metrics = {"qpe_now": {"marshall_palmer": 8.0, "tropical": 18.0}}
    for k5 in range(5):
        g3 = gch(30.0); g3.metrics["stations"][0].update({"radar_qpe": {"marshall_palmer": 8.0, "tropical": 18.0},
                                                         "t": (T + timedelta(minutes=10 * k5)).isoformat()})
        b3 = update_bias(sb, T, r3, g3)
    check("F3 pluviómetro 30 vs MP 8 mm/h (n=5) → aviso REVISAR Z–R; la relación no cambia; nivel radar intacto",
          "flag" in b3 and b3["ratio_marshall_palmer"] == 3.75 and json.dumps(CFG["zr"]) == zr0 and r3.level == 1)
    # F4 — histéresis congelando el aviso oficial (ver pruebas de rojo→naranja) + suelo como defecto fatal
    d4 = D("alert", "watch", official=OFF("alert"), overrides={"OFFICIAL_FLOOR": {"motivo": "x"}})
    check("F4 bajar por debajo del aviso oficial → FATAL_DEFECT que no admite override",
          d4["decision"] == "HOLD" and any(c["code"] == "OFFICIAL_FLOOR" and c["kind"] == "FATAL_DEFECT"
                                           for c in d4["open_conditions"]))
    class _A:  # argumentos CLI simulados
        dissent = respond = review_anomaly = None; close_episode = False; override = ["OFFICIAL_FLOOR=quiero"]
    try:
        governance_cli({}, _A()); f4cli = False
    except ValueError:
        f4cli = True
    check("F4 CLI rechaza override del suelo oficial", f4cli)
    # F5 — runs no consecutivos: prueba previa (hueco 03→15 Z corta la cadena). Aquí 00→06 con paso 3 h.
    st5 = {}
    update_run_tracks(st5, {m: {**base, "init": "2026-10-18T00:00"}})
    t5 = update_run_tracks(st5, {m: {**base, "init": "2026-10-18T06:00"}})
    check("F5 AROME 00Z y 06Z sin ver 03Z → no son 2 consecutivos", t5[m]["centered_consecutive"] == 1)
    # F6 — estaciones lejanas o viejas: pruebas previas (80 mm lejana no se atribuye; STALE ≠ 0)
    # F7 — hueco de cobertura leído como «no llueve»
    r7 = Channel("radar", 0, "obs"); r7.metrics = {"nearest_km": None, "qpe_now": {}}
    radar_coverage_check(r7, gch(12.0), Channel("lluvia_observada", available=False))
    cl7 = build_claims(T, [r7], [], {}, True)
    check("F7 radar sin eco a ≤30 km con pluviómetro vecino a 12 mm/h → radar UNKNOWN (hueco), no 'sin lluvia'",
          not r7.available and r7.metrics.get("coverage_gap") and any(c.id == "C-radar" and c.epistemic == "UNKNOWN" for c in cl7))
    d7 = D("alert", "watch", gauges=gch(0.2), radar=r7, official=OFF("watch"))
    check("F7 hueco de radar retiene la bajada", any(c["code"] == "RADAR_COVERAGE_GAP" for c in d7["open_conditions"]))
    # F8 — campo de modelo leído como radar
    try:
        Claim("x", "precipitación simulada", "EVIDENCE", "nwp", "Portinatx", T.isoformat()); f8 = False
    except ValueError:
        f8 = True
    m8 = Channel("modelo_arome", 2, "model"); m8.evidence = ["AROME 60 mm/1h"]
    c8 = build_claims(T, [m8], [], {}, True)
    check("F8 un campo de modelo no puede ser EVIDENCE; entra como HYPOTHESIS/MODEL_ESTIMATE",
          f8 and c8[0].epistemic == "HYPOTHESIS" and c8[0].label == "MODEL_ESTIMATE")
    # F9 — frente de racha fuerte en LEIB/puerto que se debilitó hacia el norte
    srcF9 = {"metar": SourceResult("metar", "ok", payload={"series": {"LEIB": gf}})}
    c9 = ch_gustfront(srcF9)
    check("F9 frente de racha CONFIRMED en LEIB (29 km) → techo alert, no local, marcado PRECURSOR",
          c9.level == 2 and not c9.local and any("PRECURSOR" in e for e in c9.evidence))
    w9 = Channel("viento_estaciones", 2, "obs", group="viento")
    f9 = fuse([Channel("aviso_aemet_activo", 0, "institutional"), c9, w9])
    check("F9 frente de racha lejano + viento de puerto lejano (ambos alert) → NO alarm", f9["proposed"] == "alert")
    fx = fuse([Channel("aviso_aemet_activo", 2, "institutional"), Channel("pluviometros", 2, "obs", group="pluviometros", local=True),
               Channel("mar_boyas", 2, "obs", group="mar")])
    fy = fuse([Channel("aviso_aemet_activo", 2, "institutional"), Channel("pluviometros", 2, "obs", group="pluviometros", local=True),
               Channel("radar", 2, "obs")])
    # Modelos de IA, superensemble y mar
    od = parse_opendap_ascii("Dataset {\n} x;\n---------------------------------------------\ntime[2]\n1.7924832E9, 1.7924868E9\n\n"
                             "LAT[2]\n38.9, 39.0\n\nU[2][2][1]\n[0][0], 0.1\n[0][1], NaN\n[1][0], 0.3\n[1][1], -0.2\n")
    check("OPeNDAP ASCII: vectores y matrices aplanadas, NaN → None",
          od["time"] == [1.7924832e9, 1.7924868e9] and od["LAT"] == [38.9, 39.0] and od["U"] == [0.1, None, 0.3, -0.2])
    hh = {"precipitation_ecmwf_ifs025_ensemble": [1, 1], "precipitation_member01_ecmwf_ifs025_ensemble": [2, 2],
          "precipitation_member01_ecmwf_aifs025_ensemble": [9, 9], "precipitation_google_weathernext2_ensemble": [3, 3],
          "precipitation_member01_google_weathernext2_ensemble": [None, None]}
    check("ensembles: sufijo «_ensemble» resuelto y sin mezclar IFS con AIFS; miembros vacíos fuera",
          ens_members(hh, "precipitation", "ecmwf_ifs025") == [[1, 1], [2, 2]]
          and ens_members(hh, "precipitation", "google_weathernext2_ensemble") == [[3, 3]])
    t0 = now_utc().replace(minute=0, second=0)
    tl = [(t0 + timedelta(hours=k)).strftime("%Y-%m-%dT%H:%M") for k in range(72)]
    mem = [[1.0] * 72, [0.0] * 72, [2.0] * 72, [0.5] * 72]           # 24 / 0 / 48 / 12 mm en 24 h
    es = ens_stats(mem, tl, t0)
    check("superensemble: fracción de miembros ≥ umbral y percentiles por ventana",
          es["n"] == 4 and es["ventanas"]["0-24"]["prob"]["10"] == 0.75 and es["ventanas"]["0-24"]["prob"]["30"] == 0.25
          and es["ventanas"]["0-24"]["max"] == 48.0 and window_sums(tl, [1.0] * 72, t0)["6-12"] == 6.0)
    rows = [{"t": (t0 - timedelta(minutes=m)).isoformat(), "nivel": 0.5 + (0.1 if m % 120 == 0 else 0.0)} for m in range(0, 600)]
    check("mareógrafo: 1 min → cada 10 min", len(thin_rows(rows, 10)) == 60)
    mt = [(t0 - timedelta(hours=k)).strftime("%Y-%m-%dT%H:%M") for k in range(10)]
    obs = [{"t": (t0 - timedelta(hours=k)).isoformat(), "nivel": 0.60 + 0.02 * k} for k in range(10)]
    sr = surge_residual(obs, mt, [-0.30 + 0.01 * k for k in range(10)])
    check("marea meteorológica: anomalías con ceros distintos → residuo = diferencia de variaciones",
          sr["n"] == 10 and abs(sr["serie"][0]["obs"] + 0.09) < 1e-6 and abs(sr["res_max"] - 0.045) < 1e-6)
    # Forense y aprendizaje
    stF: dict = {}
    r1 = ledger_add(stF, "S1", "2026-10-18T20:15:00+00:00", 81.6)            # 22:15 local
    r2 = ledger_add(stF, "S1", "2026-10-18T23:16:00+00:00", 83.2)            # 01:16 local del 19: arrastre de ayer
    r3 = ledger_add(stF, "S1", "2026-10-19T07:45:00+00:00", 68.2)
    r4 = ledger_add(stF, "S1", "2026-10-19T08:00:00+00:00", 60.0)            # baja: imposible en un total diario
    Lg = stF["obs_ledger"]["S1"]
    check("archivo: el total que una estación arrastra hasta las 02 h es el total COMPLETO de ayer; un total que baja se descarta",
          (r1, r2, r3, r4) == ("ok", "arrastre", "ok", "descartada") and Lg["2026-10-18"][-1] == [1439, 832] and Lg["2026-10-19"] == [[585, 682]])
    fz_t0 = datetime(2026, 10, 18, 22, 0, tzinfo=UTC)
    fz_tt = [fz_t0 + timedelta(hours=k) for k in range(1, 49)]
    check("lluvia del modelo en la ventana exacta: horas completas + hora final prorrateada; hueco → sin dato",
          _cum_fc(fz_tt, [1.0] * 48, fz_t0, fz_t0 + timedelta(hours=5, minutes=30)) == 5.5
          and _cum_fc(fz_tt, [1.0] * 10 + [None] * 38, fz_t0, fz_t0 + timedelta(hours=20)) is None)
    prs = [{"sid": f"S{i}", "est": "x", "dia": d, "h": 23.98, "m": "icon_eu", "L": "D0", "obs": 30.0, "fc": 10.0, "edad_d": 0.0,
            "completo": True} for i in range(4) for d in ("2026-10-18", "2026-10-19", "2026-10-20")]
    sc = forensic_scores(prs)["icon_eu|D0"]
    lr = learn({"icon_eu|D0": sc}, {})["factor_lluvia"]["icon_eu|D0"]
    check("aprendizaje: 12 pares pero 3 días independientes → confianza 3/(3+5); factor = 3^0,375 ≈ 1,51, no 3",
          sc["n"] == 12 and sc["n_dias"] == 3 and sc["ratio"] == 0.33 and lr["confianza"] == 0.38 and lr["factor"] == 1.51
          and sc["contingencia"]["30"]["fallos"] == 12)
    stL = {"obs_ledger": {"S1": {"2026-10-18": [[360, 0], [600, 100], [840, 300], [1080, 400]]}}}
    fz_base = datetime(2026, 10, 18, 0, 0, tzinfo=MADRID).astimezone(UTC)
    fz_tim = [fz_base + timedelta(hours=k) for k in range(1, 25)]
    fz_obs = [0] * 6 + [2.5] * 4 + [5.0] * 4 + [2.5] * 4 + [0] * 6                  # lluvia observada por hora
    fz_late = [0.0, 0.0] + fz_obs[:-2]                                                   # el modelo la trae 2 h tarde
    fpL = {"S1": {"nombre": "x", "time": [t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M") for t in fz_tim], "m": {"icon_eu": {"D0": fz_late}}}}
    check("desfase: un modelo que trae la lluvia 2 h tarde da +2 h", forensic_lag(stL, fpL).get("icon_eu", {}).get("mediana_h") == 2)
    stC = {"obs_ledger": {sid: {"2026-10-18": [[1439, 700]]} for sid in CFG["mc_stations"]}}
    grid = {"pts": [(39.0, 1.4), (39.75, 0.75)], "daily": {"icon_eu|D0": {"2026-10-18": [20.0, 130.0]}}}
    cs = forensic_core_shift(stC, grid)
    check("núcleo: máximo del modelo a ~100 km al NW, en el borde de la malla; sobre la red deja una fracción",
          len(cs) == 1 and 90 <= cs[0]["dist_km"] <= 110 and _rumbo(cs[0]["rumbo_deg"]) == "NW" and cs[0]["borde"]
          and cs[0]["fraccion_en_red"] == 0.15)
    # PORTUS: contrato del conector con respuestas sintéticas (lastData → ids; RTData → valor/factor)
    _pp = globals()["_portus_post"]
    def fake_post(path, body):
        if path.startswith("/lastData"):
            return {"datos": [{"id": 1, "nombreColumna": "hm0"}, {"id": 2, "nombreColumna": "dmd"},
                              {"id": 3, "nombreColumna": "vv_mx"}, {"id": 9, "nombreColumna": "lat"}]}
        return [{"fecha": "2026-10-19 07:00:00.0", "datos": [
                    {"nombreColumna": "hm0", "valor": "412", "factor": "100"},
                    {"nombreColumna": "dmd", "valor": "35", "factor": "1"},
                    {"nombreColumna": "vv_mx", "valor": "141", "factor": "10"},
                    {"nombreColumna": "vv_mx", "valor": "152", "factor": "10"}]}]
    globals()["_portus_post"] = fake_post
    try:
        ser = _portus_series(2820, ["WAVE"])
    finally:
        globals()["_portus_post"] = _pp
    check("PORTUS: valor/factor, hora UTC y 2 anemómetros → máximo",
          len(ser) == 1 and ser[0]["hm0"] == 4.12 and ser[0]["vv_mx"] == 15.2 and ser[0]["t"] == "2026-10-19T07:00:00+00:00")
    tnow = now_utc().replace(second=0)
    mk = lambda d: SourceResult("portus", "ok", payload={"stations": {"Boya Dragonera":
            [{"t": (tnow - timedelta(minutes=60 * k)).isoformat(), "hm0": 4.1 - 0.2 * k, "dmd": d, "tp": 9.0} for k in (3, 2, 1, 0)]}})
    ne, sw = ch_sea_obs(mk(35.0)), ch_sea_obs(mk(220.0))
    check("PORTUS boya: Hs 4,1 m del NE → alert (techo del mar abierto); mismo Hs del SW no cuenta",
          ne.level == 2 and sw.level == 0 and ne.available and "+0.60 m en 3 h" in " ".join(ne.evidence))
    check("R5 lluvia local + mar en boyas NO se confirman (fenómenos distintos); lluvia + radar sí",
          fx["proposed"] == "alert" and fy["proposed"] == "alarm")
    # F10 — aviso costero descartado
    coast = ma.replace(b"645301PRP1181328569", b"645301COCO190108009") \
              .replace(b"Aviso de lluvias de nivel naranja", b"Aviso de fen\xc3\xb3menos costeros de nivel amarillo") \
              .replace(b"3; orange; Severe", b"2; yellow; Moderate").replace(b"<value>ES113</value>", b"<value>ES873</value>") \
              .replace(b"Ibiza y Formentera", b"Costa - Ibiza y Formentera")
    w10 = parse_cap_documents([coast], "645301", datetime(2026, 10, 18, 8, tzinfo=UTC), 36)
    of10 = official_state(Channel("a", 3, "institutional"), Channel("b", 3, "institutional"),
                          [red, {**w10[0], "activo_ahora": True}] if w10 else [red])
    check("F10 CAP costero de Ibiza (COCO, ES873) → se aplica, tipo costero, y se lista junto al rojo terrestre",
          len(w10) == 1 and w10[0]["tipo"] == "costero" and len(of10["vigentes"]) == 2
          and {v["nivel"] for v in of10["vigentes"]} == {"rojo", "amarillo"})
    # F11 — error de horario de AROME (~2–3 h): toda afirmación de modelo lleva ventana ±3 h
    check("F11 afirmación de modelo con alcance ±3 h y ±20–100 km", "±3 h" in c8[0].scope and "20–100 km" in c8[0].scope)
    # F12 — profundidades simuladas tomadas como observadas
    try:
        Claim("depth", "s'Arenal Gros 55–65 cm", "EVIDENCE", "flood_sim", "cala", T.isoformat(), "MODEL_ESTIMATE"); f12 = False
    except ValueError:
        f12 = True
    check("F12 profundidad simulada (MODEL_ESTIMATE) no puede declararse EVIDENCE", f12)
    # F13 — «sin-meta»: run inventado por fallo de meta.json
    st13 = {}
    update_run_tracks(st13, {m: {**base, "init": "2026-10-18T00:00"}})
    t13 = update_run_tracks(st13, {m: {**base, "init": ""}})
    t13b = update_run_tracks(st13, {m: {**base, "init": ""}})
    check("F13 run sin hora de inicio → no se registra ni encadena (consecutivos 0, historial intacto)",
          t13[m]["unverified_run"] and t13b[m]["centered_consecutive"] == 0 and len(st13["runs"][m]) == 1)
    # ── Gobernanza ──
    dis = [{"id": "D1", "text": "creo que sigue lloviendo en la cala", "status": "OPEN"}]
    g1 = D("watch", "quiet", dissent=dis)
    g1b = D("alarm", "alert", dissent=dis, gauges=gch(0.1), official=OFF("alert"))
    check("G1 disenso abierto bloquea bajar a quiet, no las bajadas intermedias",
          g1["decision"] == "HOLD" and any(c["code"] == "OPEN_DISSENT" for c in g1["open_conditions"])
          and g1b["decision"] == "PROCEED")
    sp2 = {"gauge_prev": {}}
    g2c = gch(0.3, total=60.0)
    make_predictions(sp2, T, g2c, {"from": "alarm", "to": "alert"})
    pr = sp2["predictions"][0]
    sha0 = pr["sha"]
    sp2["gauge_hist"] = {"S1": [{"t": (T + timedelta(minutes=62)).isoformat(), "total": 66.5}]}
    ver = verify_predictions(sp2, T + timedelta(minutes=65))
    an2 = open_anomalies(sp2, T + timedelta(minutes=65))
    check("G2 predicción de cese refutada (+6,5 mm) → MISS y anomalía abierta",
          pr["kind"] == "cease" and ver and pr["outcome"]["status"] == "MISS" and len(an2) == 1)
    check("G2 el resultado no reescribe la predicción (sha intacto)", _pred_sha(pr) == sha0)
    g2d = D("alert", "watch", gauges=gch(0.1), official=OFF("watch"), anomalies=an2)
    check("G2 anomalía sin revisar retiene la bajada", any(c["code"] == "ANOMALY_UNREVIEWED" for c in g2d["open_conditions"]))
    sp3 = {"predictions": [{**pr, "id": "P9", "outcome": None, "window_end": T.isoformat()}], "gauge_prev": {}}
    verify_predictions(sp3, T + timedelta(minutes=CFG["pred_grace_min"] + 1))
    check("G2 sin dato en la ventana → UNVERIFIABLE (no HIT)", sp3["predictions"][0]["outcome"]["status"] == "UNVERIFIABLE")
    sp4 = {"predictions": [{**pr, "id": "P8", "outcome": None}],
           "gauge_hist": {"S1": [{"t": (T + timedelta(hours=4)).isoformat(), "total": 70.0}]}}
    verify_predictions(sp4, T + timedelta(hours=4))
    check("G2 lectura 4 h después del cierre (motor parado) → UNVERIFIABLE, no MISS ni anomalía",
          sp4["predictions"][0]["outcome"]["status"] == "UNVERIFIABLE" and not sp4.get("anomalies"))
    g4 = D("alarm", "alert", gauges=Channel("pluviometros", available=False), official=OFF("alert"),
           overrides={"CHALLENGER_VETO": {"motivo": "pluviómetro propio a 0 mm, visto en persona"}})
    check("G3 override del propietario sobre el veto → PROCEED_WITH_CONDITIONS, registrado",
          g4["decision"] == "PROCEED_WITH_CONDITIONS" and g4["overridden"][0]["code"] == "CHALLENGER_VETO")
    se = {}
    hz0 = {"radar": {"estado": "OBSERVED", "nivel": "quiet"}}
    episode_update(se, T, OFF("alarm"), "alarm", hz0, [], {})
    e1 = episode_update(se, T, OFF("quiet", "alert"), "watch", hz0, [], {})
    check("G4 sin aviso ahora pero naranja en 36 h → TRANSITION", e1["phase"] == "TRANSITION")
    e2 = episode_update(se, T, OFF("quiet"), "quiet", hz0, ["disenso D1"], {})
    check("G4 bloqueos de cierre → CESSATION, no cierre", e2["phase"] == "CESSATION")
    e3 = episode_update(se, T, OFF("quiet"), "quiet", hz0, [], {"bias": {}})
    e3b = episode_update(se, T, OFF("quiet"), "quiet", hz0, [], {"bias": {}})
    check("G4 sin auto-aceptación: el motor solo PROPONE el cierre", e3["phase"] == e3b["phase"] == "CLOSURE_PROPOSED"
          and "closure_record" in e3)
    se["episode"]["accepted"] = {"t": T.isoformat(), "by": "propietario"}
    e4 = episode_update(se, T, OFF("quiet"), "quiet", hz0, [], {})
    e5 = episode_update(se, T, OFF("unknown"), "quiet", hz0, [], {})
    check("G4 aceptado por el propietario → CLOSED; aviso no verificado no abre ni cierra", e4["phase"] == "CLOSED"
          and e5["phase"] == "CLOSED")
    cl = build_claims(T, [Channel("rayos", 1, "obs")], [], {"runoff": {"value": "observed", "t": T.isoformat(), "edad_h": 0}}, False)
    check("G5 registro tipado: aviso no verificado = UNKNOWN; rayo lejano = EVIDENCE + atribución HYPOTHESIS/PROXY; "
          "observación del propietario = EVIDENCE",
          any(c.id == "C-OFF" and c.epistemic == "UNKNOWN" for c in cl)
          and any(c.id == "C-rayos-attr" and c.label == "PROXY" for c in cl)
          and any(c.id == "C-man-runoff" and c.epistemic == "EVIDENCE" for c in cl))
    mES = manual_obs({"manual_obs": {"es_alert": {"value": "active", "t": (now_utc() - timedelta(minutes=10)).isoformat()}}}, now_utc())
    cES = build_claims(now_utc(), [], [], mES, True)
    check("F15 ES-Alert de Protección Civil → retiene la precaución y es EVIDENCE OFFICIAL de raíz propia (no AEMET)",
          precaution_hold(mES) and any(c.id == "C-es-alert" and c.source_root == "proteccion_civil" for c in cES))
    # R1: suelo saturado (calibración Portinatx 18–19/10, n=2)
    sw = {"gauge_daily": {"S9": {"2026-10-18": 98.8}},
          "gauge_prev": {"S9": {"t": "2026-10-19T07:45:00+00:00", "total": 41.4, "day": "2026-10-19"}}}
    srcW = SourceResult("meteoclimatic", "ok", payload={"stations": [{"id": "S9", "nombre": "Sant Llorenç", "dist_km": 8.0,
           "lat": 39.044, "lon": 1.487, "t": "2026-10-19T08:15:00+00:00", "edad_min": 5, "lluvia_dia": 51.8, "T": 17.0}]})
    cw = ch_gauges(srcW, sw)
    check("R1 suelo saturado (ayer 99 + hoy 52): 20,8 mm/h → alert (antes watch) y marcado SUELO SATURADO",
          cw.level == 2 and any("SUELO SATURADO" in e for e in cw.evidence))
    sd = {"gauge_prev": {}}
    srcD = SourceResult("meteoclimatic", "ok", payload={"stations": [{**srcW.payload["stations"][0], "lluvia_dia": 5.0}]})
    check("R1 suelo seco: 5 mm hoy sin antecedente → no alerta", ch_gauges(srcD, sd).level == 0)
    # F14: reinicio a 00 UTC
    su = {"gauge_daily": {"S9": {"2026-10-18": 83.2}}, "gauge_prev": {}}
    srcU = SourceResult("meteoclimatic", "ok", payload={"stations": [{**srcW.payload["stations"][0],
           "t": "2026-10-18T23:40:00+00:00", "lluvia_dia": 83.2}]})
    cu = ch_gauges(srcU, su)
    check("F14 a las 01:40 local el total de ayer (83,2) no cuenta como lluvia de hoy", not cu.available
          and any("reinicio a 00 UTC" in e for e in cu.evidence))
    # R3: radar en el pluviómetro
    import base64 as _b64
    rgc = CFG["radar_grid"]; nl = int(round(2 * rgc["dlat"] / rgc["step"])) + 1; nn = int(round(2 * rgc["dlon"] / rgc["step"])) + 1
    gb = bytearray(nl * nn)
    ii = int(round((SITE["lat"] + rgc["dlat"] - 39.044) / rgc["step"])); jj = int(round((1.487 - (SITE["lon"] - rgc["dlon"])) / rgc["step"]))
    gb[ii * nn + jj] = 40
    check("R3 rejilla radar muestreada en el pluviómetro (40 dBZ allí, 0 en Portinatx)",
          grid_dbz_at(_b64.b64encode(bytes(gb)).decode(), 39.044, 1.487) == 40.0
          and grid_dbz_at(_b64.b64encode(bytes(gb)).decode(), SITE["lat"], SITE["lon"]) == 0.0)
    # Índices atmosféricos: valores de referencia
    te = _thetae(20.0, 16.0, 850.0)
    check("θe850 Bolton con T=20, Td=16 °C a 850 hPa → ~348 K (r≈13,6 g/kg)", te is not None and 344 < te < 352)
    hh = {"time": ["2026-10-19T08:00"]}
    for p_, t_, rh_, z_ in ((1000, 20, 90, 100), (925, 16, 90, 800), (850, 12, 85, 1500), (700, 2, 70, 3100),
                            (500, -15, 50, 5700), (300, -40, 30, 9300)):
        hh.update({f"temperature_{p_}hPa": [t_], f"relative_humidity_{p_}hPa": [rh_], f"geopotential_height_{p_}hPa": [z_],
                   f"wind_speed_{p_}hPa": [5 + p_ / 100], f"wind_direction_{p_}hPa": [200]})
    hh.update({"wind_speed_10m": [3], "wind_direction_10m": [90], "cape": [1200], "convective_inhibition": [-30],
               "total_column_integrated_water_vapour": [34], "vertical_velocity_700hPa": [0.1]})
    dp = derive_profile(hh, {"vertical_velocity_700hPa": "m/s"})
    ix = {k: v[0] for k, v in dp["indices"].items()}
    check("perfil: LR75 = 17 °C / 2,6 km ≈ 6,5 °C/km; TT y KI calculados; CIN en valor absoluto",
          abs(ix["lr75"] - 6.5) < 0.1 and ix["tt"] is not None and ix["ki"] is not None and ix["cin"] == 30)
    cc = dp["composites"]["icc"][0]
    check("indicador ICC expone componentes, penalización por CIN y valor en [0,1]",
          0 <= cc["value"] <= 1 and set(cc["components"]) == {"inestabilidad", "humedad", "ascenso", "organizacion"}
          and cc["penalty"] == 0.15)
    check("bulbo húmedo: T=20, Td=12 °C a 1013 hPa → Tw ≈ 15,4 °C", abs(wet_bulb(20.0, 12.0, 1013.0) - 15.4) < 0.4)
    ws_ = wave_shoaling(3.5, 9.0, [50.0, 30.0, 10.0, 4.0])
    check("asomeramiento lineal (T=9 s): Ks 0,97 a 50 m, mínimo ~0,93 a 30 m, 0,96 a 10 m; Hs 3,5 rompe a 4 m",
          abs(ws_[0]["Ks"] - 0.975) < 0.01 and abs(ws_[1]["Ks"] - 0.928) < 0.01 and abs(ws_[2]["Ks"] - 0.956) < 0.01
          and ws_[3]["rompe"] and not ws_[2]["rompe"])
    check("Froude: U=10 m/s, Δθ=6 K en 1300 m, h=400 m → ≈1,8 (remonta)", 1.5 < froude(10.0, 290.0, 296.0, 1300.0, 400.0) < 2.1)
    agrid = parse_arcgrid("ncols 2\nnrows 2\nxllcorner 1.0\nyllcorner 39.0\ncellsize 0.5\nNODATA_value -9999\n1 2\n3 -9999\n")
    check("ArcGrid del IGN: cabecera, filas de norte a sur y nodata → None", agrid["rows"] == [[1, 2], [3, None]] and agrid["lat_n"] == 40.0)
    tif = b"II*\x00" + struct.pack("<I", 8) + struct.pack("<H", 8)
    ents = [(256, 3, 1, 2), (257, 3, 1, 1), (258, 3, 1, 32), (259, 3, 1, 1), (273, 4, 1, 8 + 2 + 8 * 12 + 4), (277, 3, 1, 1),
            (279, 4, 1, 8), (339, 3, 1, 3)]
    tif += b"".join(struct.pack("<HHI", t_, ty_, c_) + (struct.pack("<HH", v_, 0) if ty_ == 3 else struct.pack("<I", v_)) for t_, ty_, c_, v_ in ents)
    tif += b"\x00\x00\x00\x00" + struct.pack("<ff", -12.5, 3.0)
    check("GeoTIFF float32 de EMODnet (tiras sin comprimir) decodificado", parse_tiff_f32(tif) == (2, 1, [-12.5, 3.0]))
    check("todo índice publicado tiene estado de validación", all(INDEX_STATUS[k][0] in ("ESTÁNDAR", "DIAGNÓSTICO", "EXPERIMENTAL")
          for k in INDEX_STATUS) and all(k in INDEX_STATUS for k in ("icc", "ipp", "irh")))
    check("G5 MeteoAlarm y CAP de AEMET comparten raíz; LEIB y lluvia observada también (no se confirman entre sí)",
          channel_root("aviso_aemet") == channel_root("aviso_aemet_activo") == channel_root("frente_racha")
          == channel_root("lluvia_observada"))
    import knowledge_base as kb_
    check("contexto: kind='context' no cuenta como canal en la fusión (fuse solo mira institutional/obs/model/ensemble)",
          not any(n == "contexto" and k in ("institutional", "obs", "model", "ensemble") for n, k, _ in SOURCES)
          and any(n == "contexto" and k == "context" for n, k, _ in SOURCES))
    check("contexto: sin sidecar → fuente deshabilitada (UNKNOWN) y notas vacías, nunca «normal»",
          (lambda r: r.status == "deshabilitado" and context_notes(r, Channel("x"))["estado"] == "UNKNOWN")(
              run_source("contexto", "context", lambda: SourceResult(name="contexto", status="deshabilitado", detail="sin sidecar"))))
    check("percentil de contexto: 25 mm/h con p95=20 y p99=35 → banda p95–p99; sin tabla → UNKNOWN",
          kb_.percentile_rank(25.0, {"p50": 1, "p90": 8, "p95": 20, "p99": 35, "max": 60})["band"] == "p95–p99"
          and kb_.percentile_rank(25.0, None)["band"] == "UNKNOWN")
    check("umbrales: todo umbral con procedencia declarada existe en CFG y Meteoalerta Anexo 1 sigue sin cargar (None)",
          all(k in CFG for k in kb_.THRESHOLD_PROVENANCE) and kb_.METEOALERTA_ANNEX1 is None)
    print(f"\n{ok} OK, {fail} fallos — pruebas de LÓGICA con datos sintéticos; no validan umbrales ni endpoints.")
    return 1 if fail else 0


# ════════════════════════════════════════════════════════════════════════
def governance_cli(state: dict, a: Any) -> None:
    t = now_utc().isoformat()
    if a.dissent:
        ds = state.setdefault("dissent", [])
        ds.append({"id": f"D{len(ds) + 1}", "t": t, "text": a.dissent, "status": "OPEN",
                   "against": {"nowcast": state.get("nowcast_level"), "outlook": state.get("level")}})
    if a.respond:
        did, _, rest = a.respond.partition("=")
        st, _, txt = rest.partition(":")
        if st not in ("UPHELD", "RISK_ACCEPTED", "REFUTED"):
            raise ValueError("--respond: estado UPHELD | RISK_ACCEPTED | REFUTED")
        d = next((d for d in state.get("dissent", []) if d["id"] == did), None)
        if not d:
            raise ValueError(f"--respond: no existe el disenso {did}")
        d.update({"status": st, "response": txt, "responded": t})
    for kv in a.override:
        code, _, why = kv.partition("=")
        if code == "OFFICIAL_FLOOR":
            raise ValueError("el suelo del aviso oficial no admite override")
        if not why:
            raise ValueError("--override exige motivo: CÓDIGO=motivo")
        state.setdefault("overrides", {})[code] = {"t": t, "motivo": why, "by": "propietario"}
    if a.review_anomaly:
        aid, _, txt = a.review_anomaly.partition("=")
        an = next((x for x in state.get("anomalies", []) if x["id"] == aid), None)
        if not an:
            raise ValueError(f"--review-anomaly: no existe {aid}")
        an.update({"reviewed": True, "review": txt, "reviewed_t": t})
    if a.close_episode:
        ep = state.get("episode") or {}
        if ep.get("phase") != "CLOSURE_PROPOSED":
            raise ValueError(f"no hay cierre propuesto (fase {ep.get('phase', '—')})")
        ep["accepted"] = {"t": t, "by": "propietario"}


def load_config_env() -> None:
    """Claves opcionales para la app sin terminal: <datos>/config.env con líneas CLAVE=valor
    (AEMET_API_KEY, NTFY_URL, EUMETSAT_KEY, EUMETSAT_SECRET…). El entorno real tiene prioridad."""
    f = HOME / "config.env"
    if not f.exists():
        HOME.mkdir(parents=True, exist_ok=True)
        f.write_text("# Claves opcionales (quita el # y rellena):\n# AEMET_API_KEY=\n# NTFY_URL=https://ntfy.sh/<tema-privado>\n"
                     "# EUMETSAT_KEY=\n# EUMETSAT_SECRET=\n")
        return
    for line in f.read_text().splitlines():
        k, sep, v = line.strip().partition("=")
        if sep and k and not k.startswith("#") and v.strip() and k.strip() not in os.environ:
            os.environ[k.strip()] = v.strip()


def main() -> None:
    load_config_env()
    ap = argparse.ArgumentParser(description="Portinatx degen nowcast")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("run")
    wp = sub.add_parser("watch"); wp.add_argument("--interval", type=int, default=300)
    sub.add_parser("static"); sub.add_parser("climo"); sub.add_parser("radar-colors")
    sub.add_parser("selftest"); sub.add_parser("catalog")
    sv = sub.add_parser("serve"); sv.add_argument("--interval", type=int, default=300)
    sv.add_argument("--port", type=int, default=CFG["app_port"])
    sv.add_argument("--open", action="store_true", help="abre el navegador al arrancar")
    sub.add_parser("export-app")
    ps = sub.add_parser("pack-state"); ps.add_argument("out")
    fbk = sub.add_parser("forense-backfill"); fbk.add_argument("dirs", nargs="+")
    sub.add_parser("forense-informe")
    le = sub.add_parser("label-episode")
    le.add_argument("episode"); le.add_argument("start"); le.add_argument("end")
    le.add_argument("regime", choices=REGIMES)
    sub.add_parser("pirineo-export")
    us = sub.add_parser("unpack-state"); us.add_argument("src")
    ic = sub.add_parser("inspect-cap"); ic.add_argument("file"); ic.add_argument("--at", default="")
    ap.add_argument("--json", action="store_true", help="imprime el snapshot JSON")
    ap.add_argument("--floor", choices=["amarillo", "naranja", "rojo"],
                    help="aviso AEMET verificado a mano (sin clave): actúa como suelo")
    ap.add_argument("--floor-active", action="store_true",
                    help="el aviso de --floor está VIGENTE ahora (cuenta también para el nowcast)")
    ap.add_argument("--obs", action="append", default=[], metavar="CLAVE=VALOR",
                    help="observación local manual: runoff=observed|none, flooding=observed|none, "
                         "es_alert=active|none (ES-Alert de Protección Civil) "
                         f"(caduca a las {CFG['manual_obs_ttl_h']} h)")
    ap.add_argument("--dissent", metavar="TEXTO", help="registra un disenso contra el diagnóstico actual")
    ap.add_argument("--respond", metavar="ID=ESTADO:TEXTO",
                    help="responde un disenso: UPHELD | RISK_ACCEPTED | REFUTED")
    ap.add_argument("--override", action="append", default=[], metavar="CÓDIGO=MOTIVO",
                    help=f"levanta una condición de retención (no el suelo oficial) durante {CFG['override_ttl_h']} h")
    ap.add_argument("--review-anomaly", metavar="ID=TEXTO", help="marca una anomalía como revisada")
    ap.add_argument("--close-episode", action="store_true", help="acepta el cierre propuesto del episodio")
    a = ap.parse_args()
    if a.cmd is None:                                  # doble clic / sin argumentos → aplicación
        a.cmd, a.interval, a.port, a.open = "serve", 300, CFG["app_port"], True
    if a.floor:
        MANUAL_FLOOR.update({"nivel": a.floor, "rank": WARN_RANK[a.floor], "evento": "aviso introducido a mano",
                             "onset": "", "expires": "", "activo_ahora": bool(a.floor_active), "parametro": "",
                             "probabilidad": "", "descripcion": "verificado por el usuario"})
    if a.cmd == "selftest":
        sys.exit(selftest())
    if a.cmd == "pirineo-export":
        sys.modules.setdefault("portinatx_degen", sys.modules[__name__])
        import pirineo
        sys.argv = [sys.argv[0], "export"]
        return pirineo.main()
    if a.cmd == "label-episode":
        st = load_state()
        label_episode(st, a.episode, a.start, a.end, a.regime)
        persist_state_only(st)
        print("Episodio etiquetado; no modifica avisos ni precaución.")
        return
    if a.cmd == "static":
        return cmd_static()
    if a.cmd == "climo":
        return cmd_climo()
    if a.cmd == "radar-colors":
        return cmd_radar_colors()
    if a.cmd == "catalog":
        return cmd_catalog()
    if a.cmd == "inspect-cap":
        return cmd_inspect_cap(a.file, a.at)
    if a.cmd == "forense-backfill":
        st = load_state()
        print(forensic_backfill(st, a.dirs))
        persist_state_only(st)
        return
    if a.cmd == "forense-informe":
        st = load_state()
        srcs = {n: run_source(n, k, f) for n, k, f in SOURCES if n in ("forense_modelos", "forense_mar", "forense_malla")}
        print(json.dumps(forensic_bundle(st, srcs, None), ensure_ascii=False, indent=1, default=str))
        persist_state_only(st)
        return
    if a.cmd == "pack-state":
        print(pack_state(Path(a.out)))
        return
    if a.cmd == "unpack-state":
        st = unpack_state(Path(a.src))
        print(f"estado restaurado en {HOME} · nivel {st.get('level')}")
        return
    state = load_state()
    for kv in a.obs:
        k, _, v = kv.partition("=")
        if (k in ("runoff", "flooding") and v in ("observed", "none")) or (k == "es_alert" and v in ("active", "none")):
            state.setdefault("manual_obs", {})[k] = {"value": v, "t": now_utc().isoformat()}
        else:
            sys.exit(f"--obs no válido: {kv} (usa runoff=observed|none, flooding=observed|none)")
    try:
        governance_cli(state, a)
    except ValueError as exc:
        sys.exit(str(exc))
    if a.cmd == "serve":
        persist_state_only(state)
        return cmd_serve(a.interval, a.port, getattr(a, "open", False))
    while True:
        try:
            snap = cycle(state)
            path = persist(snap, state)
            if a.cmd in ("export-app", "run", "watch"):
                write_app(build_app(snap, state))
            if a.json:
                print(json.dumps({k: v for k, v in snap.items() if not k.startswith("_")},
                                 ensure_ascii=False, indent=1, default=str))
            else:
                print(render(snap))
                print(f"   snapshot congelado: {path}")
        except Exception:
            traceback.print_exc()
            if a.cmd in ("run", "export-app"):
                raise                                  # la nube debe detectar un ciclo fallido
        if a.cmd in ("run", "export-app"):
            break
        time.sleep(a.interval)


if __name__ == "__main__":
    main()
