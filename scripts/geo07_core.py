"""GEO-07, fase 07-1: núcleo físico reducido de la interacción flujo–relieve (Python puro, probado en el CI).

Sigue docs/GEO-07-PROTOCOLO.md (§4; fusionado en #82, borrador sin congelar). Diagnóstico experimental: no es un
aviso ni una predicción validada. **Ningún umbral está calibrado** y no se ajustará con episodios reales hasta
congelar el protocolo.

Convenciones:
- Un perfil es una lista de niveles dict(z=m s.n.m., t=°C, rh=%, u=m/s, v=m/s, p=hPa). Los ausentes son None.
  Un valor PRESENTE pero no físico (NaN, ±inf, p ≤ 0, HR fuera de 0–100 %, T fuera de −100…+60 °C…) invalida
  el cálculo entero (UNKNOWN): no se descarta en silencio.
- Dirección del viento = PROCEDENCIA (grados, meteorológica). La barrera se describe por la **normal geométrica
  de su cresta** que apunta hacia barlovento (`normal_deg`, ver `crest_normal`), no por un sector de flujo.
- Estados: "OK", "PARCIAL", "UNKNOWN", "NO_APLICABLE_INESTABLE", "FLUJO_MAL_DEFINIDO", "FLUJO_NO_INCIDENTE".
  Nunca 0 por defecto.
"""
import math

G = 9.81
RD = 287.04
RV = 461.5
CP = 1004.0
LV = 2.501e6
EPS = RD / RV
DEFAULT_THRESHOLDS = (0.5, 1.5)        # HIPÓTESIS sin calibrar (protocolo §4)
MIN_LEVELS = 2
MIN_UPERP = 2.0                        # m/s
MAX_DIR_SPREAD = 45.0                  # grados (arco mínimo que contiene todas las direcciones)
MIN_COVERAGE = 0.5                     # fracción de la barrera cubierta por niveles válidos (sin calibrar)
SAT_RH = 90.0
RANGES = {"z": (-500.0, 12000.0), "t": (-100.0, 60.0), "rh": (0.0, 100.0), "u": (-150.0, 150.0),
          "v": (-150.0, 150.0), "p": (1e-3, 1100.0)}


# ---------------------------------------------------------------- validación

def _finite(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def check_level(lv, keys=("z", "t", "p", "u", "v", "rh")):
    """'ok' si todos los valores presentes son físicos; 'ausente' si falta alguno de z,t,p,u,v; 'invalido' si hay
    un valor presente no finito o fuera de rango. La HR ausente no hace el nivel ausente (se trata aparte)."""
    for k in keys:
        v = lv.get(k)
        if v is None:
            continue
        lo, hi = RANGES[k]
        if not _finite(v) or not lo <= v <= hi:
            return "invalido"
    if any(lv.get(k) is None for k in keys if k != "rh"):
        return "ausente"
    return "ok"


# ---------------------------------------------------------------- termodinámica

def theta(t_c, p_hpa):
    """Temperatura potencial (K)."""
    return (t_c + 273.15) * (1000.0 / p_hpa) ** (RD / CP)


def sat_vapor_pressure(t_c):
    """Presión de vapor de saturación (hPa) sobre agua, Bolton (1980)."""
    return 6.112 * math.exp(17.67 * t_c / (t_c + 243.5))


def sat_mixing_ratio(t_c, p_hpa):
    es = sat_vapor_pressure(t_c)
    return EPS * es / (p_hpa - es)


def mixing_ratio(t_c, rh, p_hpa):
    e = rh / 100.0 * sat_vapor_pressure(t_c)
    return EPS * e / (p_hpa - e)


def theta_e(t_c, rh, p_hpa):
    """Temperatura potencial equivalente (K), Bolton (1980), ec. 43 con T del LCL por la ec. 22. Diagnóstico de masa
    de aire; ya NO se usa para la estabilidad (ver `moist_n2`)."""
    tk = t_c + 273.15
    r = mixing_ratio(t_c, rh, p_hpa)
    e = rh / 100.0 * sat_vapor_pressure(t_c)
    tl = 2840.0 / (3.5 * math.log(tk) - math.log(max(e, 1e-6)) - 4.805) + 55.0
    return tk * (1000.0 / p_hpa) ** (0.2854 * (1 - 0.28 * r)) * math.exp((3.376 / tl - 0.00254) * r * 1000 * (1 + 0.81 * r))


def moist_lapse_rate(t_c, p_hpa):
    """Gradiente adiabático saturado Γm (K/m)."""
    tk = t_c + 273.15
    qs = sat_mixing_ratio(t_c, p_hpa)
    return G * (1 + LV * qs / (RD * tk)) / (CP + LV ** 2 * qs * EPS / (RD * tk ** 2))


def dry_n2(lo, hi):
    """N² seco (s⁻²) entre dos niveles: (g/θ̄)·Δθ/Δz."""
    dz = hi["z"] - lo["z"]
    a, b = theta(lo["t"], lo["p"]), theta(hi["t"], hi["p"])
    return G / ((a + b) / 2) * (b - a) / dz


def moist_n2(lo, hi):
    """N² saturado (s⁻²) de Durran y Klemp (1982, ec. 36) entre dos niveles:
        N_m² = (g/T)(dT/dz + Γm)(1 + L·qs/(Rd·T)) − g/(1 + qw) · dqw/dz
    HIPÓTESIS declarada: agua total qw = qs (sin condensado conocido). Solo válido si la capa está saturada."""
    dz = hi["z"] - lo["z"]
    tm = (lo["t"] + hi["t"]) / 2
    pm = (lo["p"] + hi["p"]) / 2
    tk = tm + 273.15
    qs = sat_mixing_ratio(tm, pm)
    dtdz = (hi["t"] - lo["t"]) / dz
    dqdz = (sat_mixing_ratio(hi["t"], hi["p"]) - sat_mixing_ratio(lo["t"], lo["p"])) / dz
    return G / tk * (dtdz + moist_lapse_rate(tm, pm)) * (1 + LV * qs / (RD * tk)) - G / (1 + qs) * dqdz


# ---------------------------------------------------------------- viento y geometría

def wind_from_uv(u, v):
    """(velocidad, dirección de procedencia en grados) a partir de u (hacia el E) y v (hacia el N)."""
    return math.hypot(u, v), (math.degrees(math.atan2(-u, -v)) % 360)


def incident_component(u, v, normal_deg):
    """U⊥ = U·n̂, con n̂ el vector unitario que entra en la barrera desde barlovento. `normal_deg` es el azimut de la
    normal de la cresta que apunta HACIA barlovento; n̂ = −(sin a, cos a). Positivo = el flujo incide en la barrera."""
    a = math.radians(normal_deg)
    return -(u * math.sin(a) + v * math.cos(a))


def angular_spread(dirs):
    """Arco mínimo (grados) que contiene todas las direcciones: 360° − mayor hueco entre direcciones ordenadas."""
    if len(dirs) < 2:
        return 0.0
    s = sorted(d % 360 for d in dirs)
    gaps = [b - a for a, b in zip(s, s[1:])] + [s[0] + 360 - s[-1]]
    return 360.0 - max(gaps)


def crest_normal(lon1, lat1, lon2, lat2, windward_lon, windward_lat):
    """Azimut (°) de la normal a la cresta (segmento 1→2) que apunta hacia el punto de barlovento dado.
    Proyección equirectangular local; válido para segmentos de decenas de km. None si la geometría es degenerada."""
    k = math.cos(math.radians((lat1 + lat2) / 2))
    ex, ny = (lon2 - lon1) * k, (lat2 - lat1)
    if math.hypot(ex, ny) == 0:
        return None
    nx, nny = -ny, ex                                  # una de las dos normales
    mx, my = (windward_lon - (lon1 + lon2) / 2) * k, windward_lat - (lat1 + lat2) / 2
    dot = nx * mx + nny * my
    if dot == 0:
        return None
    if dot < 0:
        nx, nny = -nx, -nny
    return math.degrees(math.atan2(nx, nny)) % 360


def thickness_weighted_mean(zs, vals):
    """(1/(z_n − z_1)) ∫ f dz por trapecios sobre niveles con separación irregular."""
    integral = sum((vals[i] + vals[i + 1]) / 2 * (zs[i + 1] - zs[i]) for i in range(len(zs) - 1))
    return integral / (zs[-1] - zs[0])


# ---------------------------------------------------------------- diagnóstico

def froude(profile, base_z, crest_z, normal_deg, thresholds=DEFAULT_THRESHOLDS):
    """Fr = Ū⊥ / (N · h) en la capa [base_z, crest_z] con guardas (protocolo §4).

    Ū⊥ se promedia por espesor; N se calcula entre los extremos (principal) y por subcapas (sensibilidad).
    Devuelve un dict: estado, motivo, fr, fr_seco, fr_humedo, regimen, u_perp, n_seco, n_humedo, saturacion,
    subcapas_inestables, sensibilidad, h, n_niveles, cobertura.
    """
    out = {"estado": "UNKNOWN", "motivo": "", "fr": None, "fr_seco": None, "fr_humedo": None, "regimen": None,
           "u_perp": None, "n_seco": None, "n_humedo": None, "saturacion": "UNKNOWN", "subcapas_inestables": [],
           "sensibilidad": {}, "h": None, "n_niveles": 0, "cobertura": None}
    if not (_finite(base_z) and _finite(crest_z) and _finite(normal_deg)) or crest_z - base_z <= 0:
        out["motivo"] = "barrera no definida (cota o normal ausente o no física)"
        return out
    h = crest_z - base_z
    out["h"] = h
    lv = []
    for x in profile:
        state = check_level(x)
        if state == "invalido":
            out["motivo"] = f"valor no físico en el nivel z = {x.get('z')}"
            return out
        if state == "ok" and base_z <= x["z"] <= crest_z:
            lv.append(x)
    lv.sort(key=lambda x: x["z"])
    out["n_niveles"] = len(lv)
    if len(lv) < MIN_LEVELS:
        out["motivo"] = "menos de 2 niveles válidos en la capa (niveles bajo el terreno descartados)"
        return out
    zs = [x["z"] for x in lv]
    out["cobertura"] = (zs[-1] - zs[0]) / h
    if out["cobertura"] < MIN_COVERAGE:
        out["motivo"] = f"los niveles cubren el {100 * out['cobertura']:.0f} % de la barrera"
        return out

    # Viento: dispersión entre TODOS los niveles y componente incidente promediada por espesor.
    spread = angular_spread([wind_from_uv(x["u"], x["v"])[1] for x in lv])
    up = thickness_weighted_mean(zs, [incident_component(x["u"], x["v"], normal_deg) for x in lv])
    out["u_perp"] = up
    out["sensibilidad"]["dispersion_dir"] = spread
    if spread > MAX_DIR_SPREAD:
        out["estado"], out["motivo"] = "FLUJO_MAL_DEFINIDO", f"dispersión de dirección = {spread:.0f}°"
        return out
    if up < MIN_UPERP:
        out["estado"] = "FLUJO_NO_INCIDENTE"
        out["motivo"] = (f"Ū⊥ = {up:.1f} m/s: flujo paralelo o desde sotavento" if up < 0.5
                         else f"Ū⊥ = {up:.1f} m/s < {MIN_UPERP} m/s")
        return out

    # Estabilidad: extremos (principal) y subcapas (sensibilidad).
    lo, hi = lv[0], lv[-1]
    n2d = dry_n2(lo, hi)
    pairs = list(zip(lv, lv[1:]))
    sub_d = [dry_n2(a, b) for a, b in pairs]
    rh = [x.get("rh") for x in lv]
    if any(r is None for r in rh):
        sat = "UNKNOWN"
    elif all(r >= SAT_RH for r in rh):
        sat = "saturada"
    elif all(r < SAT_RH for r in rh):
        sat = "no_saturada"
    else:
        sat = "parcial"
    out["saturacion"] = sat
    n2m = moist_n2(lo, hi) if sat in ("saturada", "parcial") else None
    sub_m = [moist_n2(a, b) for a, b in pairs] if sat == "saturada" else None
    main_sub = sub_m if sub_m is not None else sub_d
    out["subcapas_inestables"] = [(a["z"], b["z"]) for (a, b), n2 in zip(pairs, main_sub) if n2 <= 0]
    out["sensibilidad"].update(n2_seco_extremos=n2d, n2_seco_subcapas=sub_d, n2_humedo_extremos=n2m,
                               n2_humedo_subcapas=sub_m)

    def fr_of(n2):
        return up / (math.sqrt(n2) * h) if n2 is not None and n2 > 0 else None

    out["n_seco"] = math.sqrt(n2d) if n2d > 0 else None
    out["n_humedo"] = math.sqrt(n2m) if n2m is not None and n2m > 0 else None
    out["fr_seco"], out["fr_humedo"] = fr_of(n2d), fr_of(n2m)

    principal_n2 = n2m if sat == "saturada" else n2d
    if principal_n2 <= 0:
        out["estado"] = "NO_APLICABLE_INESTABLE"
        out["motivo"] = f"N² ({'húmeda' if sat == 'saturada' else 'seca'}) = {principal_n2:.2e} s⁻² ≤ 0"
        return out
    if sat == "UNKNOWN":
        out["estado"] = "PARCIAL"
        out["motivo"] = "humedad ausente: saturación desconocida; solo Fr seco, sin régimen"
        return out
    fr = out["fr_humedo"] if sat == "saturada" else out["fr_seco"]
    lo_t, hi_t = thresholds
    out["fr"] = fr
    out["regimen"] = "bloqueo" if fr < lo_t else ("transicion" if fr < hi_t else "paso_por_encima")
    out["estado"] = "OK"
    notes = []
    if sat == "parcial":
        notes.append("capa parcialmente saturada: Fr principal seco; ver fr_humedo como cota")
    if out["subcapas_inestables"]:
        notes.append(f"{len(out['subcapas_inestables'])} subcapa(s) con N² ≤ 0 dentro de una capa estable en bloque")
    out["motivo"] = "; ".join(notes)
    return out


def foehn_signature(upwind, downwind, dtheta_min=2.0, drh_min=20.0):
    """Firma observable de föhn en un par barlovento/sotavento (protocolo §2, 07e).

    Replica la regla del motor actual (pirineo.py: Δθ ≥ 2 K y ΔHR ≥ 20 puntos) como referencia R1. **No es una
    validación observacional independiente**: es la misma regla que se pretende evaluar. Devuelve (True/False/None,
    detalle); con datos ausentes o no físicos, None (UNKNOWN).
    """
    keys = ("t", "rh", "p")
    for side in (upwind, downwind):
        if any(side.get(k) is None for k in keys):
            return None, "UNKNOWN: falta T, HR o p"
        if check_level(side, keys) != "ok":
            return None, "UNKNOWN: valor no físico"
    dth = theta(downwind["t"], downwind["p"]) - theta(upwind["t"], upwind["p"])
    drh = upwind["rh"] - downwind["rh"]
    return (dth >= dtheta_min and drh >= drh_min), f"Δθ = {dth:+.1f} K, ΔHR = {drh:+.0f} puntos"
