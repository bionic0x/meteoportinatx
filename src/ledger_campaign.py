"""Estado de la campaña prospectiva de 90 días, calculado SOLO desde el diario y los registros.

No acepta fechas declaradas de inicio ni de fin. Un "ciclo con datos" es un asiento OK que añadió
al menos un registro; un día con datos es un día UTC con al menos un ciclo con datos. Al alcanzar el
criterio (90 días con datos y 90×24 h reales desde el primer ciclo con datos) la ventana de
evaluación se congela en ese asiento de anclaje: lo posterior solo se informa como
`vigilancia_posterior`. El estado no es una validación meteorológica ni una puntuación de habilidad.

Límites declarados: los "episodios" se cuentan como días (`event_id` = día de la ventana); días
consecutivos de un mismo temporal no son episodios independientes. Diario y recibos no están
firmados ni sellados externamente: quien controla el disco puede rehacerlos de forma coherente.
"""
from __future__ import annotations

from datetime import timedelta

import forecast_ledger as fl

TARGET_DAYS = 90
TARGET_SPAN = timedelta(days=TARGET_DAYS)
CADENCE_HOURS = 1.0            # cadencia declarada del ciclo supervisado (systemd, cada hora)
DEFAULT_MAX_GAP_HOURS = 48.0   # decisión del titular; propuesta de la auditoría, no calibrada
DEFAULT_MIN_COVERAGE = 0.8     # decisión del titular: ciclos con datos / ciclos esperados en la ventana
MIN_PAIRS = 20                 # mínimo de D-021: observaciones QC PASS distintas emparejadas (sin baseline)
DEFAULT_MIN_PAIR_DAYS = 10     # decisión del titular: días UTC distintos entre esas observaciones
FUTURE_TOLERANCE = timedelta(minutes=10)
RECEIPTS_DIR = fl.RECEIPTS_DIR
receipt_digest = fl.receipt_digest


def _gaps(times):
    return [b - a for a, b in zip(times, times[1:])]


def independent_observations(ledger, pairs):
    """Observaciones QC PASS emparejadas (sin baseline) que cuentan como unidades independientes.

    Por sitio y variable, las ventanas solapadas cuentan una sola vez: se eligen ventanas sin solape
    por orden de fin (máximo conjunto disjunto). Veinte ventanas de 1–20 h que empiezan a la misma
    hora son un único periodo físico. Devuelve {id: (inicio, fin)} de las observaciones contadas."""
    obs_by_id = {r["id"]: r for _, r in ledger.records("observation", include_imported=False)}
    groups = {}
    for oid in {p["observation_id"] for p in pairs if not p["baseline"]}:
        d = obs_by_id[oid]["data"]
        window = (fl._date(d["observed_from"], "observed_from"), fl._date(d["observed_to"], "observed_to"))
        groups.setdefault((d["site_id"], d["variable"]), []).append((window[1], window[0], oid))
    counted = {}
    for items in groups.values():
        last_end = None
        for end, start, oid in sorted(items):
            if last_end is None or start >= last_end:
                counted[oid] = (start, end)
                last_end = end
    return counted


def _hour(t):
    return t.replace(minute=0, second=0, microsecond=0)


def campaign_status(ledger, *, max_gap_hours=DEFAULT_MAX_GAP_HOURS, min_coverage=DEFAULT_MIN_COVERAGE,
                    min_pair_days=DEFAULT_MIN_PAIR_DAYS):
    """Estado y contadores de la campaña. Sin parámetros de fecha: todo sale del diario y del reloj."""
    max_gap = timedelta(hours=fl._number(max_gap_hours, "max_gap_hours", lower=1))
    min_coverage = fl._number(min_coverage, "min_coverage", lower=0, upper=1)
    min_pair_days = int(fl._number(min_pair_days, "min_pair_days", lower=1, upper=TARGET_DAYS))
    base = {"objetivo_dias": TARGET_DAYS, "umbral_hueco_horas": float(max_gap_hours),
            "umbral_cobertura": min_coverage, "minimo_observaciones_emparejadas": MIN_PAIRS,
            "minimo_dias_con_pares": min_pair_days, "cadencia_horas": CADENCE_HOURS,
            "limite_episodios": "los episodios se cuentan como días UTC; no son independientes",
            "validacion_meteorologica": False}
    try:
        verified = ledger.verify()
    except fl.ValidationError as exc:
        return _out(base, "INVALIDO:REGISTRO_CORRUPTO", {"detalle": str(exc)})
    if not verified["ok"]:
        return _out(base, "INVALIDO:" + verified["motivo"], {"diario": verified["journal"]})
    entries, _ = ledger.journal()
    if not entries:
        return _out(base, "SIN_INICIAR", {"diario": verified["journal"]})

    now = ledger._now()
    times = [fl._date(e["timestamp"], "timestamp") for e in entries]
    if times[-1] > now + FUTURE_TOLERANCE:
        return _out(base, "INVALIDO:TIMESTAMP_FUTURO", {"diario": verified["journal"]})

    # Ventana de evaluación: desde el primer ciclo con datos hasta el asiento de anclaje (si existe).
    data = [(t, e) for t, e in zip(times, entries) if e["state"] == "OK" and e["added_ids"]]
    anchor, days = None, set()
    for t, e in data:
        days.add(t.date())
        if len(days) >= TARGET_DAYS and t - data[0][0] >= TARGET_SPAN:
            anchor = (t, e)
            break
    end_seq = anchor[1]["seq"] if anchor else entries[-1]["seq"]
    window = [(t, e) for t, e in zip(times, entries) if e["seq"] <= end_seq]
    data_w = [t for t, e in data if e["seq"] <= end_seq]
    start = data_w[0] if data_w else times[0]
    end = anchor[0] if anchor else times[-1]
    # Cobertura por horas UTC distintas con datos, no por asientos (varios ciclos en una hora cuentan una vez).
    expected = int((_hour(end) - _hour(start)).total_seconds() // 3600) + 1
    data_hours = {_hour(t) for t in data_w}
    window_ids = {i for _, e in window for i in e["added_ids"]}
    pairs, excluded = ledger.pairs()
    # Un par cuenta solo si pronóstico Y observación figuran en el diario dentro de la ventana.
    pairs_w = [p for p in pairs if p["forecast_id"] in window_ids and p["observation_id"] in window_ids]
    scored = independent_observations(ledger, pairs_w)
    pair_days = {start.date() for start, _ in scored.values()}
    obs = [r for _, r in ledger.records("observation", include_imported=False) if r["id"] in window_ids]
    gaps = _gaps(data_w)
    days_w = {t.date() for t in data_w}
    counters = {
        "dias_con_datos": len(days_w),
        "dia": f"día {min(len(days_w), TARGET_DAYS)}/{TARGET_DAYS}",
        "horas_reales_ventana": round((end - start).total_seconds() / 3600, 2) if data_w else 0.0,
        "ventana_congelada": anchor is not None,
        "asiento_anclaje_seq": end_seq if anchor else None,
        "ciclos_esperados": expected,
        "ciclos_registrados": len(window),
        "ciclos_ok": sum(e["state"] == "OK" for _, e in window),
        "ciclos_con_datos": len(data_w),
        "horas_con_datos": len(data_hours),
        "cobertura": round(len(data_hours) / expected, 4),
        "ciclos_por_estado": {s: sum(e["state"] == s for _, e in window) for s in sorted(fl.JOURNAL_STATES)},
        "huecos": sum(g > timedelta(hours=1.5 * CADENCE_HOURS) for g in gaps),
        "hueco_max_horas": round(max(gaps, default=timedelta(0)).total_seconds() / 3600, 2),
        "fraccion_obs_unknown": (round(sum(o["data"]["qc"] == "UNKNOWN" for o in obs) / len(obs), 4)
                                 if obs else None),
        "pares_brutos": len(pairs_w),
        "observaciones_emparejadas": len(scored),
        "dias_con_pares": len(pair_days),
        "episodios_como_dias": len({p["event_id"] for p in pairs_w}),
        "excluidos_por_motivo_todo_el_archivo": excluded,
        "diario": verified["journal"],
    }
    if any(g > max_gap for g in gaps):
        return _out(base, "INVALIDO:HUECO_MAYOR_QUE_UMBRAL", counters)
    if anchor is None:
        open_gap = now - (data_w[-1] if data_w else times[0])
        counters["hueco_abierto_horas"] = round(open_gap.total_seconds() / 3600, 2)
        if open_gap > max_gap:
            return _out(base, "INVALIDO:HUECO_ABIERTO_MAYOR_QUE_UMBRAL", counters)
        return _out(base, "EN_CURSO", counters)

    after = [anchor[0]] + [t for t, e in data if e["seq"] > end_seq]
    worst = max(_gaps(after) + [now - after[-1]])
    counters["vigilancia_posterior"] = {
        "estado": "HUECO_POSTERIOR" if worst > max_gap else "SIN_HUECO_MAYOR_QUE_UMBRAL",
        "hueco_max_horas": round(worst.total_seconds() / 3600, 2),
        "nota": "no altera el estado de la ventana congelada"}
    if counters["cobertura"] < min_coverage:
        return _out(base, "DATOS_COMPLETOS_COBERTURA_INSUFICIENTE", counters)
    if len(scored) < MIN_PAIRS or len(pair_days) < min_pair_days:
        return _out(base, "DATOS_COMPLETOS_PARES_INSUFICIENTES", counters)
    candidates = [r for r, problem in ledger.receipts()
                  if not problem and r.get("ok") is True and r.get("origen") == "copia_externa"
                  and isinstance(r.get("n_observaciones_emparejadas"), int)
                  and r["n_observaciones_emparejadas"] >= MIN_PAIRS
                  and isinstance(r.get("journal_seq"), int) and r["journal_seq"] >= end_seq]
    valid = [r["sha256"] for r in candidates if r.get("mismo_dispositivo") is False]
    counters["recibos_otro_dispositivo_validos"] = valid
    if not valid:
        counters["motivo_restauracion"] = ("copia en el mismo dispositivo" if candidates else
                                           "sin recibo de una copia en otro dispositivo con al menos "
                                           "20 observaciones emparejadas")
        return _out(base, "DATOS_COMPLETOS_RESTAURACION_NO_PROBADA", counters)
    return _out(base, "COMPLETADO", counters)


SUMMARIES = {
    "SIN_INICIAR": "Campaña sin iniciar: el diario no tiene ciclos.",
    "EN_CURSO": ("Campaña en curso ({dia}; hacen falta 90 días con datos y 2160 h reales). "
                 "La validación de 90 días no ha terminado."),
    "INVALIDO": ("Campaña inválida ({motivo}). No se repara el diario: se conserva tal cual y se inicia "
                 "una campaña nueva en un directorio nuevo (docs/FORECAST-LEDGER-P0.md §5)."),
    "DATOS_COMPLETOS_COBERTURA_INSUFICIENTE": ("Ventana de 90 días cerrada con cobertura inferior al umbral: "
                                               "la validación no ha terminado ni puede terminar en esta campaña."),
    "DATOS_COMPLETOS_PARES_INSUFICIENTES": ("Ventana de 90 días cerrada con menos de 20 observaciones QC PASS "
                                            "emparejadas o repartidas en pocos días: la validación no ha "
                                            "terminado ni puede terminar en esta campaña."),
    "DATOS_COMPLETOS_RESTAURACION_NO_PROBADA": ("Ventana de 90 días cerrada, pero la restauración no está probada "
                                                "({motivo_restauracion}): la validación no ha terminado."),
    "COMPLETADO": ("Estado COMPLETADO: 90 días con datos, cobertura horaria y observaciones emparejadas "
                   "suficientes, diario íntegro y recibo de restauración desde una copia externa en otro "
                   "dispositivo. Diario y recibo no tienen firma externa. No implica habilidad meteorológica."),
}


def _out(base, state, counters):
    key, _, motivo = state.partition(":")
    out = {**base, "estado": state, **counters}
    out["resumen"] = SUMMARIES[key].format(dia=counters.get("dia"), motivo=motivo,
                                           motivo_restauracion=counters.get("motivo_restauracion"))
    return out
