"""GEO-07, fase 07-1: núcleo físico reducido de la interacción flujo–relieve (Python puro, probado en el CI).

Sigue docs/GEO-07-PROTOCOLO.md v0.1, §4 (BORRADOR; PR #82). Diagnóstico experimental: no es un aviso ni una
predicción validada. **Ningún umbral está calibrado**: los valores por defecto de `regime` son las hipótesis
del protocolo y solo se ajustarán con episodios de entrenamiento (fase 07-3).

Convenciones:
- Un perfil es una lista de niveles dict(z=m s.n.m., t=°C, rh=%, u=m/s, v=m/s, p=hPa). Los ausentes son None.
- La dirección del viento es la de PROCEDENCIA (meteorológica, en grados). `barrier_from` es el sector de
  procedencia del flujo que la barrera intercepta (GEO-01 `sector_procedencia`).
- Las guardas devuelven un estado, nunca 0: "OK", "UNKNOWN", "NO_APLICABLE_INESTABLE", "FLUJO_MAL_DEFINIDO".
"""
import math

G = 9.81
RD = 287.04
CP = 1004.0
LV = 2.501e6
EPS = 0.622
DEFAULT_THRESHOLDS = (0.5, 1.5)        # HIPÓTESIS sin calibrar (protocolo §4)
MIN_LEVELS = 2
MIN_UPERP = 2.0                        # m/s
MAX_DIR_SPREAD = 45.0                  # grados
SAT_RH = 90.0


def _ok(v):
    return v is not None and not (isinstance(v, float) and math.isnan(v))


def theta(t_c, p_hpa):
    """Temperatura potencial (K)."""
    return (t_c + 273.15) * (1000.0 / p_hpa) ** (RD / CP)


def sat_vapor_pressure(t_c):
    """Presión de vapor de saturación (hPa), Bolton (1980)."""
    return 6.112 * math.exp(17.67 * t_c / (t_c + 243.5))


def mixing_ratio(t_c, rh, p_hpa):
    e = rh / 100.0 * sat_vapor_pressure(t_c)
    return EPS * e / (p_hpa - e)


def theta_e(t_c, rh, p_hpa):
    """Temperatura potencial equivalente (K), Bolton (1980), ec. 43, con la T del LCL por la ec. 22."""
    tk = t_c + 273.15
    r = mixing_ratio(t_c, rh, p_hpa)
    e = rh / 100.0 * sat_vapor_pressure(t_c)
    tl = 2840.0 / (3.5 * math.log(tk) - math.log(max(e, 1e-6)) - 4.805) + 55.0
    return tk * (1000.0 / p_hpa) ** (0.2854 * (1 - 0.28 * r)) * math.exp((3.376 / tl - 0.00254) * r * 1000 * (1 + 0.81 * r))


def wind_from_uv(u, v):
    """(velocidad, dirección de procedencia en grados) a partir de u (hacia el E) y v (hacia el N)."""
    return math.hypot(u, v), (math.degrees(math.atan2(-u, -v)) % 360)


def normal_component(u, v, barrier_from):
    """Componente del viento que SOPLA DESDE `barrier_from` hacia la barrera (positiva = incide en la barrera)."""
    a = math.radians(barrier_from)
    # vector unitario que apunta DESDE la procedencia hacia el punto: (−sin a, −cos a)
    return -(u * math.sin(a) + v * math.cos(a))


def layer(profile, z_bottom, z_top):
    """Niveles válidos dentro de [z_bottom, z_top]; descarta los que están bajo el terreno (z < z_bottom)."""
    keys = ("z", "t", "p", "u", "v")
    return sorted((lv for lv in profile if all(_ok(lv.get(k)) for k in keys) and z_bottom <= lv["z"] <= z_top),
                  key=lambda lv: lv["z"])


def brunt_vaisala_sq(levels, moist=False):
    """N² (s⁻²) de la capa entre el nivel más bajo y el más alto.

    Seco: N² = (g/θ̄)·Δθ/Δz. Húmedo, si `moist`: se sustituye θ por θe (aproximación de primer orden de la
    estabilidad húmeda saturada, que hay que declarar). None si no hay espesor.
    """
    lo, hi = levels[0], levels[-1]
    dz = hi["z"] - lo["z"]
    if dz <= 0:
        return None
    if moist:
        if not (_ok(lo.get("rh")) and _ok(hi.get("rh"))):
            return None
        a, b = theta_e(lo["t"], lo["rh"], lo["p"]), theta_e(hi["t"], hi["rh"], hi["p"])
    else:
        a, b = theta(lo["t"], lo["p"]), theta(hi["t"], hi["p"])
    return G / ((a + b) / 2) * (b - a) / dz


def froude(profile, base_z, crest_z, barrier_from, thresholds=DEFAULT_THRESHOLDS):
    """Fr = U⊥ / (N · h_eff) en la capa entre la base de barlovento y la cresta, con guardas (protocolo §4).

    Devuelve un dict con: estado, fr, regimen, u_perp, n, n_tipo, h_eff, n_niveles y motivo.
    """
    h = crest_z - base_z
    out = {"estado": "UNKNOWN", "fr": None, "regimen": None, "u_perp": None, "n": None, "n_tipo": None,
           "h_eff": h if h > 0 else None, "n_niveles": 0, "motivo": ""}
    if h <= 0:
        out["motivo"] = "barrera no positiva"
        return out
    lv = layer(profile, base_z, crest_z)
    out["n_niveles"] = len(lv)
    if len(lv) < MIN_LEVELS:
        out["motivo"] = "menos de 2 niveles válidos en la capa (niveles bajo el terreno descartados)"
        return out
    dirs = [wind_from_uv(x["u"], x["v"])[1] for x in lv]
    spread = max(abs((d - dirs[0] + 180) % 360 - 180) for d in dirs)
    up = sum(normal_component(x["u"], x["v"], barrier_from) for x in lv) / len(lv)
    out["u_perp"] = up
    if up < MIN_UPERP or spread > MAX_DIR_SPREAD:
        out["estado"] = "FLUJO_MAL_DEFINIDO"
        out["motivo"] = f"U⊥ = {up:.1f} m/s, dispersión de dirección = {spread:.0f}°"
        return out
    saturated = all(_ok(x.get("rh")) and x["rh"] >= SAT_RH for x in (lv[0], lv[-1]))
    n2 = brunt_vaisala_sq(lv, moist=saturated)
    out["n_tipo"] = "húmeda (θe)" if saturated else "seca (θ)"
    if n2 is None:
        out["motivo"] = "estabilidad no calculable"
        return out
    if n2 <= 0:
        out["estado"] = "NO_APLICABLE_INESTABLE"
        out["motivo"] = f"N² = {n2:.2e} s⁻² ≤ 0"
        return out
    n = math.sqrt(n2)
    fr = up / (n * h)
    lo, hi = thresholds
    out.update(estado="OK", fr=fr, n=n,
               regimen="bloqueo" if fr < lo else ("transicion" if fr < hi else "paso_por_encima"))
    return out


def foehn_signature(upwind, downwind, dtheta_min=2.0, drh_min=20.0):
    """Firma observable de föhn en un par barlovento/sotavento (protocolo §2, 07e).

    `upwind` y `downwind` son dict(t, rh, p). Devuelve (True/False/None, detalle). Con datos ausentes, None (UNKNOWN).
    Umbrales por defecto = regla actual del motor (pirineo.py), usados aquí solo como referencia R1.
    """
    keys = ("t", "rh", "p")
    if not all(_ok(upwind.get(k)) and _ok(downwind.get(k)) for k in keys):
        return None, "UNKNOWN: falta T, HR o p"
    dth = theta(downwind["t"], downwind["p"]) - theta(upwind["t"], upwind["p"])
    drh = upwind["rh"] - downwind["rh"]
    return (dth >= dtheta_min and drh >= drh_min), f"Δθ = {dth:+.1f} K, ΔHR = {drh:+.0f} puntos"
