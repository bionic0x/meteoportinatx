"""SEPI fase 04: núcleo de cálculo de los objetivos bimestrales, en Python puro y probado en el CI.

Definiciones en docs/SEPI-P-PROTOCOLO.md (v0.4), §2–§3. Solo hay cálculo descriptivo y por periodo.
Las relaciones entre periodos (`transition_matrix`) se pueden probar con datos sintéticos, pero
`require_frozen_protocol` bloquea su ejecución sobre S2M mientras el protocolo no esté congelado (§9).
"""
import math
from datetime import date, timedelta

PERIODS = ("P1", "P2", "P3")
PERIOD_NAMES = {"P1": "nov–dic", "P2": "ene–feb", "P3": "mar–abr"}
PERCENTILES = (10, 25, 33, 50, 67, 75, 90)
FORMATION_HS_CM = 30.0
FORMATION_DAYS = 7
CENSORED = "censurado"


def period_dates(season, period):
    """Día anterior al periodo y días del periodo. `season` es el año de inicio (1968 = 1968–69)."""
    if period == "P1":
        first, last = date(season, 11, 1), date(season, 12, 31)
    elif period == "P2":
        first, last = date(season + 1, 1, 1), date(season + 1, 3, 1) - timedelta(days=1)
    elif period == "P3":
        first, last = date(season + 1, 3, 1), date(season + 1, 4, 30)
    else:
        raise ValueError(period)
    days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    return first - timedelta(days=1), days


def d100_applies(period, altitude, exposition, slope):
    """d100 excluido en P1; en P2 y P3 solo en el estrato 2.100 m llano (§3)."""
    return period != "P1" and altitude == 2100 and exposition == -1 and slope == 0


def _num(v):
    return v is not None and not (isinstance(v, float) and math.isnan(v))


def formation_date(days, hs):
    """Primer día de la primera secuencia de 7 días consecutivos, observados y dentro del periodo, con HS ≥ 30 cm.

    Un día ausente interrumpe la secuencia. Devuelve (fecha | None, censurado: bool). Si no se
    alcanza, queda censurado a la fecha del último día (31-dic), no a cero.
    """
    run = 0
    for i, d in enumerate(days):
        v = hs.get(d)
        if _num(v) and v >= FORMATION_HS_CM:
            run += 1
            if run == FORMATION_DAYS:
                return days[i - FORMATION_DAYS + 1], False
        else:
            run = 0
    return None, True


def period_metrics(season, period, hs, swe, altitude, exposition, slope):
    """Objetivos de un periodo. `hs` (cm) y `swe` (kg/m²) son {fecha: valor}; la ausencia es ausencia, no cero."""
    prev, days = period_dates(season, period)
    n = len(days)
    seq = [prev] + days
    swe_ok = all(_num(swe.get(d)) for d in seq)
    hs_ok = all(_num(hs.get(d)) for d in seq)
    hs_obs = sum(1 for d in days if _num(hs.get(d)))
    ends = _num(swe.get(prev)) and _num(swe.get(days[-1]))
    row = {
        "season": season, "period": period, "n_days": n, "n_hs_obs": hs_obs,
        "n_swe_obs": sum(1 for d in days if _num(swe.get(d))),
        "swe_extremes_ok": ends, "swe_sequence_complete": swe_ok, "hs_sequence_complete": hs_ok,
        "swe0": swe.get(prev) if ends else None, "swe_end": swe.get(days[-1]) if ends else None,
        "hs_end": hs.get(days[-1]) if _num(hs.get(days[-1])) else None,
        "dswe": swe[days[-1]] - swe[prev] if ends else None,
        "g_swe": None, "l_swe": None, "g_hs": None, "d30": None, "d100": None,
        "d_threshold_coverage_ok": hs_obs >= math.ceil(0.9 * n),
        "formation_date": None, "formation_censored": None,
    }
    if swe_ok:
        deltas = [swe[b] - swe[a] for a, b in zip(seq, seq[1:])]
        row["g_swe"] = sum(max(x, 0.0) for x in deltas)
        row["l_swe"] = sum(max(-x, 0.0) for x in deltas)
    if hs_ok:
        row["g_hs"] = sum(max(hs[b] - hs[a], 0.0) for a, b in zip(seq, seq[1:]))
    if row["d_threshold_coverage_ok"]:
        row["d30"] = sum(1 for d in days if _num(hs.get(d)) and hs[d] >= 30)
        if d100_applies(period, altitude, exposition, slope):
            row["d100"] = sum(1 for d in days if _num(hs.get(d)) and hs[d] >= 100)
    if period == "P1":
        f, cens = formation_date(days, hs)
        row["formation_date"] = f.isoformat() if f else CENSORED
        row["formation_censored"] = cens
    return row


def quantile_type7(values, q):
    """Cuantil lineal tipo 7 (el de numpy por defecto); `q` en [0, 1]."""
    xs = sorted(values)
    if not xs:
        return None
    h = (len(xs) - 1) * q
    lo = math.floor(h)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (h - lo) * (xs[hi] - xs[lo])


def quantile_censored(ranks, q, censored_rank):
    """Cuantil tipo 1 (rango más cercano por la izquierda, sin interpolar) con censura por la derecha.

    `ranks` son días desde el inicio del periodo (1 = 1-nov) y `censored_rank` marca los censurados.
    Si el cuantil cae en la censura, devuelve CENSORED.
    """
    xs = sorted(ranks)
    if not xs:
        return None
    k = max(math.ceil(q * len(xs)), 1) - 1
    return CENSORED if xs[k] >= censored_rank else xs[k]


def tercile_edges(train):
    return quantile_type7(train, 1 / 3), quantile_type7(train, 2 / 3)


def tercile(value, edges):
    lo, hi = edges
    return 0 if value <= lo else (2 if value > hi else 1)


def transition_matrix(pairs, edges_prev, edges_next):
    """Matriz 3×3 de recuentos (tercil del periodo anterior → tercil del siguiente).

    Los terciles se calculan fuera (`tercile_edges`) con el conjunto de entrenamiento.
    No debe ejecutarse sobre S2M hasta que el protocolo esté congelado (ver `require_frozen_protocol`).
    """
    m = [[0, 0, 0] for _ in range(3)]
    for a, b in pairs:
        if _num(a) and _num(b):
            m[tercile(a, edges_prev)][tercile(b, edges_next)] += 1
    return m


FROZEN_MARK = "**Estado: CONGELADO"


def protocol_frozen(protocol_text):
    """El protocolo está congelado si su línea de estado empieza por la marca de congelado."""
    return any(line.startswith(FROZEN_MARK) for line in protocol_text.splitlines()[:6])


def require_frozen_protocol(protocol_text):
    if not protocol_frozen(protocol_text):
        raise SystemExit(
            "Bloqueado: docs/SEPI-P-PROTOCOLO.md no está congelado (§9). Las matrices de transición sobre S2M "
            "solo se ejecutan después de la congelación; usa --sintetico para probar el código.")
