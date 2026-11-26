"""Estado de la campaña prospectiva de 90 días, calculado SOLO desde el diario y los registros.

No acepta fechas declaradas de inicio ni de fin: el día N es el número de días UTC con al menos un
ciclo OK en el diario encadenado. Un ledger sin diario no tiene campaña medible (SIN_INICIAR, diario
UNKNOWN). El estado no es una validación meteorológica ni una puntuación de habilidad.

Límite declarado: los "episodios" se cuentan como días (`event_id` = día de la ventana); días
consecutivos de un mismo temporal no son episodios independientes.
"""
from __future__ import annotations

import json
from datetime import timedelta

import forecast_ledger as fl

TARGET_DAYS = 90
CADENCE_HOURS = 1.0           # cadencia declarada del ciclo supervisado (systemd, cada hora)
DEFAULT_MAX_GAP_HOURS = 48.0  # decisión del titular; propuesta de la auditoría, no calibrada
RECEIPTS_DIR = "restore-receipts"


def receipt_digest(receipt):
    """SHA-256 canónico de un recibo, excluido su propio campo `sha256`."""
    return fl._hash(fl._canonical({k: v for k, v in receipt.items() if k != "sha256"}))


def _valid_receipts(ledger, entries, min_seq):
    """Recibos de restauración íntegros, satisfactorios y anclados en el diario en seq >= min_seq."""
    heads = {e["hash"]: e["seq"] for e in entries}
    found = []
    for path in sorted((ledger.root / "journal" / RECEIPTS_DIR).glob("*.json")):
        try:
            receipt = json.loads(path.read_bytes())
        except (OSError, ValueError):
            continue
        if (isinstance(receipt, dict) and receipt.get("kind") == "restore-drill"
                and receipt.get("sha256") == receipt_digest(receipt)
                and path.name == receipt["sha256"] + ".json"
                and receipt.get("ok") is True
                and heads.get(receipt.get("journal_head_sha256"), -1) >= min_seq):
            found.append(receipt["sha256"])
    return found


def campaign_status(ledger, *, max_gap_hours=DEFAULT_MAX_GAP_HOURS):
    """Estado y contadores de la campaña. Sin parámetros de fecha: todo sale del diario y del reloj."""
    max_gap = timedelta(hours=fl._number(max_gap_hours, "max_gap_hours", lower=1))
    base = {"objetivo_dias": TARGET_DAYS, "umbral_hueco_horas": float(max_gap_hours),
            "cadencia_horas": CADENCE_HOURS,
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
    ok_times = [t for t, e in zip(times, entries) if e["state"] == "OK"]
    days = sorted({t.date() for t in ok_times})
    gaps = [b - a for a, b in zip(ok_times, ok_times[1:])]
    open_gap = now - (ok_times[-1] if ok_times else times[0])
    span_h = (times[-1] - times[0]).total_seconds() / 3600
    pairs, excluded = ledger.pairs()
    obs = [r for _, r in ledger.records("observation", include_imported=False)]
    counters = {
        "dias_con_datos": len(days),
        "ciclos_esperados": int(span_h // CADENCE_HOURS) + 1,
        "ciclos_registrados": len(entries),
        "ciclos_ok": len(ok_times),
        "ciclos_por_estado": {s: sum(e["state"] == s for e in entries) for s in sorted(fl.JOURNAL_STATES)},
        "huecos": sum(g > timedelta(hours=1.5 * CADENCE_HOURS) for g in gaps),
        "hueco_max_horas": round(max(gaps + [open_gap]).total_seconds() / 3600, 2),
        "hueco_abierto_horas": round(open_gap.total_seconds() / 3600, 2),
        "fraccion_obs_unknown": (round(sum(o["data"]["qc"] == "UNKNOWN" for o in obs) / len(obs), 4)
                                 if obs else None),
        "pares_emparejados": len(pairs),
        "episodios_como_dias": len({p["event_id"] for p in pairs}),
        "excluidos_por_motivo": excluded,
        "diario": verified["journal"],
    }
    if any(g > max_gap for g in gaps):
        return _out(base, "INVALIDO:HUECO_MAYOR_QUE_UMBRAL", counters)
    if open_gap > max_gap:
        return _out(base, "INVALIDO:HUECO_ABIERTO_MAYOR_QUE_UMBRAL", counters)
    if len(days) < TARGET_DAYS:
        return _out(base, "EN_CURSO", counters, dia=f"día {len(days)}/{TARGET_DAYS}")
    day_target = days[TARGET_DAYS - 1]
    min_seq = next(e["seq"] for t, e in zip(times, entries) if e["state"] == "OK" and t.date() == day_target)
    receipts = _valid_receipts(ledger, entries, min_seq)
    counters["recibos_restauracion_validos"] = receipts
    if not receipts:
        return _out(base, "DATOS_COMPLETOS_RESTAURACION_NO_PROBADA", counters)
    return _out(base, "COMPLETADO", counters)


SUMMARIES = {
    "SIN_INICIAR": "Campaña sin iniciar: el diario no tiene ciclos.",
    "EN_CURSO": "Campaña en curso ({dia}). La validación de 90 días no ha terminado.",
    "INVALIDO": "Campaña inválida ({motivo}). Debe reiniciarse; los datos no cuentan como campaña.",
    "DATOS_COMPLETOS_RESTAURACION_NO_PROBADA": ("90 días de datos reunidos, pero sin recibo de restauración "
                                                "válido: la validación no ha terminado."),
    "COMPLETADO": "Estado COMPLETADO: 90 días, diario íntegro y restauración probada. No implica habilidad.",
}


def _out(base, state, counters, dia=None):
    key, _, motivo = state.partition(":")
    out = {**base, "estado": state, **counters}
    if dia:
        out["dia"] = dia
    out["resumen"] = SUMMARIES[key].format(dia=dia, motivo=motivo)
    return out
