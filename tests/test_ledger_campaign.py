"""Diario encadenado, campaña de 90 días y simulacro de restauración con reloj sintético.

Incluye las reproducciones del verificador independiente (90 asientos vacíos, 0 pares, recibo local,
edición de valor, timestamp futuro, diario truncado, cola incompleta y códigos de salida).
"""
from __future__ import annotations

import importlib.util
import inspect
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import forecast_ledger as fl  # noqa: E402
import ledger_campaign as lc  # noqa: E402

spec = importlib.util.spec_from_file_location("ledger_restore_drill", ROOT / "scripts/ledger_restore_drill.py")
drill = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drill)
spec = importlib.util.spec_from_file_location("forensic_cycle", ROOT / "scripts/forensic_cycle.py")
fc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fc)

UTC = timezone.utc
START = datetime(2026, 1, 1, 12, tzinfo=UTC)
SITE = {"domain": "portinatx", "site_id": "portinatx", "lat": 39.1, "lon": 1.5,
        "variable": "precipitation_mm", "unit": "mm", "source_license": "SYNTHETIC"}


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.now = START
        self.ledger = fl.Ledger(self.tmp / "private", clock=lambda: self.now)
        self.pending = []

    def forecast(self, begin, model="m", baseline=False):
        return self.ledger.add("forecast", {
            **SITE, "event_id": f"e{begin:%Y%m%d%H}", "valid_from": begin.isoformat(),
            "valid_to": (begin + timedelta(hours=1)).isoformat(), "issued_at": self.now.isoformat(),
            "provider_run_at": self.now.isoformat(), "provider": "test", "model": model, "family": "f",
            "mode": "amount", "prediction": 1.0, "source_id": "synthetic", "baseline": baseline})["id"]

    def observation(self, begin):
        return self.ledger.add("observation", {
            **SITE, "event_id": f"e{begin:%Y%m%d%H}", "observed_from": begin.isoformat(),
            "observed_to": (begin + timedelta(hours=1)).isoformat(), "station_id": "rain-gauge",
            "value": 1.5, "qc": "INSTRUMENT_QC_PASS", "source_type": "instrument", "source_id": "synthetic"})["id"]

    def cycle(self, when, *, pairs=False, state="OK"):
        """One journaled cycle that freezes a forecast (+1 h) and, optionally, observes the latest closed window."""
        self.now = when
        ids = [self.forecast(when + timedelta(hours=1))]
        if pairs:
            closed = [b for b in self.pending if b + timedelta(hours=1) <= when]
            ids += [self.observation(b) for b in closed[-1:]]
            self.pending = [b for b in self.pending if b not in closed]
        self.pending.append(when + timedelta(hours=1))
        return self.ledger.append_journal(state, ids)

    def run_cycles(self, n, *, step=timedelta(days=1), pairs=0):
        for k in range(n):
            self.cycle(START + step * k, pairs=k <= pairs)

    def status(self, **kw):
        return lc.campaign_status(self.ledger, **kw)

    def complete_drill(self, *, other_device=True):
        """Drill from an external copy; the test tree is on one filesystem (possibly tmpfs), so another
        device with a durable filesystem is simulated."""
        with patch.object(drill, "_same_device", return_value=not other_device), \
                patch.object(drill, "_fs_type", return_value="ext4"):
            return drill.drill(self.ledger.root, source=self.external_copy(), clock=lambda: self.now)

    def complete_drill_from(self, src):
        with patch.object(drill, "_same_device", return_value=False), \
                patch.object(drill, "_fs_type", return_value="ext4"):
            return drill.drill(self.ledger.root, source=src, clock=lambda: self.now)

    def external_copy(self):
        copy = self.tmp / "external"
        shutil.rmtree(copy, ignore_errors=True)
        shutil.copytree(self.ledger.root, copy, ignore=shutil.ignore_patterns("restore-receipts"))
        return copy


class Campaign(Base):
    def test_old_ledger_without_journal_is_unknown_not_broken(self):
        self.forecast(START + timedelta(hours=2))
        v = self.ledger.verify()
        self.assertTrue(v["ok"])
        self.assertEqual(v["integridad"], "UNKNOWN")
        self.assertEqual(v["journal"], {"estado": "SIN_DIARIO", "integridad": "UNKNOWN"})
        self.assertEqual(self.status()["estado"], "SIN_INICIAR")

    def test_89_days_is_in_progress_day_89(self):
        self.run_cycles(89)
        out = self.status()
        self.assertEqual((out["estado"], out["dia"], out["dias_con_datos"]), ("EN_CURSO", "día 89/90", 89))

    def test_empty_ok_entries_are_not_days_with_data(self):
        for k in range(95):
            self.now = START + timedelta(days=k)
            self.ledger.append_journal("OK", [])
        out = self.status()
        self.assertEqual(out["dias_con_datos"], 0)
        self.assertTrue(out["estado"].startswith("INVALIDO:HUECO_ABIERTO"))

    def test_90_utc_days_in_88_real_days_is_not_a_full_window(self):
        # Reproducción A del verificador: 23:59 del día 1 → 00:01 del día 90.
        first = datetime(2026, 1, 1, 23, 59, tzinfo=UTC)
        self.cycle(first)
        for k in range(1, 89):
            self.cycle(first + timedelta(days=k))
        self.cycle(datetime(2026, 3, 31, 0, 1, tzinfo=UTC))
        out = self.status()
        self.assertEqual(out["dias_con_datos"], 90)
        self.assertLess(out["horas_reales_ventana"], 90 * 24)
        self.assertEqual(out["estado"], "EN_CURSO")
        self.complete_drill()
        self.assertEqual(self.status(min_coverage=0)["estado"], "EN_CURSO")

    def test_full_window_with_zero_pairs_never_completed(self):
        self.run_cycles(91)
        self.assertEqual(self.status(min_coverage=0)["estado"], "DATOS_COMPLETOS_PARES_INSUFICIENTES")
        receipt = self.complete_drill()
        self.assertTrue(receipt["ok"])
        out = self.status(min_coverage=0)
        self.assertEqual(out["estado"], "DATOS_COMPLETOS_PARES_INSUFICIENTES")
        self.assertNotIn("completado", out["resumen"].lower())

    def test_daily_cycles_have_insufficient_coverage(self):
        self.run_cycles(91, pairs=25)
        out = self.status()
        self.assertEqual(out["estado"], "DATOS_COMPLETOS_COBERTURA_INSUFICIENTE")
        self.assertLess(out["cobertura"], 0.8)

    def test_local_receipt_is_not_restore_proof(self):
        self.run_cycles(91, pairs=25)
        self.assertEqual(self.status(min_coverage=0)["estado"], "DATOS_COMPLETOS_RESTAURACION_NO_PROBADA")
        receipt = drill.drill(self.ledger.root, clock=lambda: self.now)
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["origen"], "copia_local")
        out = self.status(min_coverage=0)
        self.assertEqual(out["estado"], "DATOS_COMPLETOS_RESTAURACION_NO_PROBADA")
        self.assertNotIn("restauración probada", out["resumen"])

    def test_external_receipt_completes_and_window_is_frozen(self):
        self.run_cycles(91, pairs=25)
        receipt = self.complete_drill()
        self.assertEqual((receipt["ok"], receipt["origen"], receipt["n_observaciones_emparejadas"],
                          receipt["mismo_dispositivo"]), (True, "copia_externa", 25, False))
        out = self.status(min_coverage=0)
        self.assertEqual(out["estado"], "COMPLETADO")
        self.assertTrue(out["ventana_congelada"])
        self.assertIn("completado", out["resumen"].lower())
        # Un hueco posterior no invalida la ventana ya congelada; se informa aparte.
        self.now += timedelta(days=5)
        out = self.status(min_coverage=0)
        self.assertEqual(out["estado"], "COMPLETADO")
        self.assertEqual(out["vigilancia_posterior"]["estado"], "HUECO_POSTERIOR")

    def test_external_receipt_with_mismatching_copy_fails(self):
        self.run_cycles(91, pairs=25)
        copy = self.external_copy()
        self.cycle(self.now + timedelta(hours=1))           # el ledger avanza; la copia queda vieja
        receipt = self.complete_drill_from(copy)
        self.assertFalse(receipt["ok"])
        self.assertNotIn("motivo", receipt)                 # falla la comparación, no el origen
        self.assertEqual(self.status(min_coverage=0)["estado"], "DATOS_COMPLETOS_RESTAURACION_NO_PROBADA")

    def test_same_device_receipt_is_not_restore_proof(self):
        self.run_cycles(91, pairs=25)
        receipt = self.complete_drill(other_device=False)
        self.assertEqual((receipt["ok"], receipt["mismo_dispositivo"]), (True, True))
        out = self.status(min_coverage=0)
        self.assertEqual(out["estado"], "DATOS_COMPLETOS_RESTAURACION_NO_PROBADA")
        self.assertEqual(out["motivo_restauracion"], "copia en el mismo dispositivo")
        self.assertNotIn("copia externa", out["resumen"])

    # --- Ataques de la segunda verificación (probe2) ---

    def test_n1_repeated_id_is_rejected(self):
        self.now = START
        rid = self.forecast(START + timedelta(hours=2))
        self.ledger.append_journal("OK", [rid])
        self.now += timedelta(hours=1)
        self.ledger.append_journal("OK", [rid])
        v = self.ledger.verify()
        self.assertEqual((v["integridad"], v["motivo"]), ("ROTA", "DIARIO_ID_DUPLICADO seq=1"))
        self.assertTrue(self.status()["estado"].startswith("INVALIDO:DIARIO_ID_DUPLICADO"))

    def test_n1_many_forecasts_one_observation_is_one_observation(self):
        self.now = START
        window = START + timedelta(hours=1)
        self.ledger.append_journal("OK", [self.forecast(window, model=f"m{i}") for i in range(20)])
        self.now = START + timedelta(hours=2)
        self.ledger.append_journal("OK", [self.observation(window)])
        out = self.status()
        self.assertEqual((out["pares_brutos"], out["observaciones_emparejadas"], out["dias_con_pares"]), (20, 1, 1))

    def test_baseline_is_not_counted(self):
        self.now = START
        window = START + timedelta(hours=1)
        self.ledger.append_journal("OK", [self.forecast(window, model="persistence", baseline=True)])
        self.now = START + timedelta(hours=2)
        self.ledger.append_journal("OK", [self.observation(window)])
        out = self.status()
        self.assertEqual((out["pares_brutos"], out["observaciones_emparejadas"]), (1, 0))

    def test_pairs_concentrated_in_few_days_are_insufficient(self):
        # 25 observaciones en el primer día: suficientes en número, no en días distintos.
        for k in range(26):
            self.cycle(START + timedelta(hours=k), pairs=True)
        for d in range(2, 92):
            self.cycle(START + timedelta(days=d - 1, hours=2))
        out = self.status(min_coverage=0)
        self.assertGreaterEqual(out["observaciones_emparejadas"], 20)
        self.assertLess(out["dias_con_pares"], 10)
        self.assertEqual(out["estado"], "DATOS_COMPLETOS_PARES_INSUFICIENTES")
        self.assertEqual(self.status(min_coverage=0, min_pair_days=1)["estado"],
                         "DATOS_COMPLETOS_RESTAURACION_NO_PROBADA")

    def test_record_captured_outside_its_entry_interval(self):
        self.now = START
        early = self.forecast(START + timedelta(hours=5))
        self.now += timedelta(minutes=30)
        self.ledger.append_journal("NO_DATA", [])
        self.now += timedelta(hours=1)
        self.ledger.append_journal("OK", [early])   # capturado antes del asiento anterior
        self.assertTrue(self.ledger.verify()["motivo"].startswith("DIARIO_ID_FUERA_DE_INTERVALO"))

    def test_n2_half_hour_cycles_do_not_inflate_coverage(self):
        # Dos ciclos por hora durante 12 h y 12 h vacías: 72 asientos en 60 h esperadas (>1 por asientos),
        # pero solo 36 horas UTC con datos.
        for day in range(3):
            for j in range(24):
                self.cycle(START + timedelta(days=day, minutes=30 * j))
        out = self.status()
        self.assertEqual((out["ciclos_con_datos"], out["ciclos_esperados"], out["horas_con_datos"]), (72, 60, 36))
        self.assertEqual(out["cobertura"], 0.6)

    def test_n4_observation_outside_journal_is_not_a_pair(self):
        self.now = START
        window = START + timedelta(hours=1)
        self.ledger.append_journal("OK", [self.forecast(window)])
        self.now = START + timedelta(hours=3)
        self.observation(window)                   # nunca anotada en el diario
        self.ledger.append_journal("NO_DATA", [])
        out = self.status()
        self.assertEqual((out["pares_brutos"], out["observaciones_emparejadas"]), (0, 0))

    # --- Tercera verificación (probe3) ---

    def test_symlinked_source_is_rejected(self):
        self.run_cycles(91, pairs=25)
        src = self.tmp / "fake-external"
        src.mkdir()
        (src / "local").symlink_to(self.ledger.root / "local")
        (src / "journal").symlink_to(self.ledger.root / "journal")
        receipt = self.complete_drill_from(src)
        self.assertEqual((receipt["ok"], receipt["motivo"]), (False, "ORIGEN_CON_ENLACES"))
        self.assertEqual(self.status(min_coverage=0)["estado"], "DATOS_COMPLETOS_RESTAURACION_NO_PROBADA")

    def test_nested_symlink_in_source_is_rejected(self):
        self.run_cycles(3)
        src = self.external_copy()
        victim = next((src / "local" / "forecast").glob("*.json"))
        victim.unlink()
        victim.symlink_to(self.ledger.root / "local" / "forecast" / victim.name)
        self.assertEqual(self.complete_drill_from(src)["motivo"], "ORIGEN_CON_ENLACES")

    def test_hardlinked_source_is_the_ledger(self):
        self.run_cycles(91, pairs=25)
        src = self.tmp / "hardlinked"
        shutil.copytree(self.ledger.root, src, copy_function=lambda a, b: Path(b).hardlink_to(a),
                        ignore=shutil.ignore_patterns("restore-receipts"))
        receipt = self.complete_drill_from(src)
        self.assertEqual((receipt["ok"], receipt["motivo"]), (False, "ORIGEN_ES_EL_LEDGER"))
        self.assertEqual(self.status(min_coverage=0)["estado"], "DATOS_COMPLETOS_RESTAURACION_NO_PROBADA")

    def test_overlapping_windows_count_once(self):
        # 20 ventanas de 1–20 h que empiezan a la misma hora: un único periodo físico.
        self.now = START
        begin = START + timedelta(hours=1)
        ids = []
        for h in range(1, 21):
            ids.append(self.ledger.add("forecast", {
                **SITE, "event_id": "solape", "valid_from": begin.isoformat(),
                "valid_to": (begin + timedelta(hours=h)).isoformat(), "issued_at": START.isoformat(),
                "provider_run_at": START.isoformat(), "provider": "test", "model": f"m{h}", "family": "f",
                "mode": "amount", "prediction": 1.0, "source_id": "synthetic"})["id"])
        self.ledger.append_journal("OK", ids)
        self.now = START + timedelta(hours=22)
        obs = [self.ledger.add("observation", {
            **SITE, "event_id": "solape", "observed_from": begin.isoformat(),
            "observed_to": (begin + timedelta(hours=h)).isoformat(), "station_id": "rain-gauge",
            "value": 1.5, "qc": "INSTRUMENT_QC_PASS", "source_type": "instrument",
            "source_id": "synthetic"})["id"] for h in range(1, 21)]
        self.ledger.append_journal("OK", obs)
        out = self.status()
        self.assertEqual((out["pares_brutos"], out["observaciones_emparejadas"]), (20, 1))

    # --- Cuarta verificación ---

    def mountinfo(self, fstype):
        info = self.tmp / "mountinfo"
        info.write_text("22 27 0:21 / / rw,relatime - ext4 /dev/sda1 rw\n"
                        f"90 22 0:99 / {self.tmp / 'external'} rw,relatime - {fstype} {fstype} rw\n")
        return info

    def test_overlay_source_is_rejected_by_mountinfo(self):
        self.run_cycles(91, pairs=25)
        src = self.external_copy()
        for fstype in ("overlay", "tmpfs", "fuse.sshfs"):
            with patch.object(drill, "MOUNTINFO", self.mountinfo(fstype)), \
                    patch.object(drill, "_same_device", return_value=False):
                receipt = drill.drill(self.ledger.root, source=src, clock=lambda: self.now)
            self.assertEqual((receipt["ok"], receipt["motivo"], receipt["fs_origen"]),
                             (False, "ORIGEN_FS_NO_DURADERO", fstype))
        self.assertEqual(self.status(min_coverage=0)["estado"], "DATOS_COMPLETOS_RESTAURACION_NO_PROBADA")

    def test_durable_fs_from_mountinfo_is_accepted(self):
        self.run_cycles(91, pairs=25)
        src = self.external_copy()
        with patch.object(drill, "MOUNTINFO", self.mountinfo("ext4")), \
                patch.object(drill, "_same_device", return_value=False):
            receipt = drill.drill(self.ledger.root, source=src, clock=lambda: self.now)
        self.assertEqual((receipt["ok"], receipt["fs_origen"]), (True, "ext4"))
        self.assertEqual(self.status(min_coverage=0)["estado"], "COMPLETADO")

    def test_unreadable_mountinfo_is_unknown_not_blocking(self):
        self.run_cycles(3)
        with patch.object(drill, "MOUNTINFO", self.tmp / "missing-mountinfo"), \
                patch.object(drill, "_same_device", return_value=False):
            receipt = drill.drill(self.ledger.root, source=self.external_copy(), clock=lambda: self.now)
        self.assertEqual((receipt["ok"], receipt["fs_origen"]), (True, "UNKNOWN"))

    def test_short_windows_in_one_hour_count_once(self):
        # 20 ventanas de 3 min dentro de la misma hora: una sola observación.
        self.now = START
        begin = START + timedelta(hours=1)
        ids, obs = [], []
        for j in range(20):
            b = begin + timedelta(minutes=3 * j)
            ids.append(self.ledger.add("forecast", {
                **SITE, "event_id": "corto", "valid_from": b.isoformat(),
                "valid_to": (b + timedelta(minutes=3)).isoformat(), "issued_at": START.isoformat(),
                "provider_run_at": START.isoformat(), "provider": "test", "model": "m", "family": "f",
                "mode": "amount", "prediction": 1.0, "source_id": "synthetic"})["id"])
        self.ledger.append_journal("OK", ids)
        self.now = START + timedelta(hours=3)
        for j in range(20):
            b = begin + timedelta(minutes=3 * j)
            obs.append(self.ledger.add("observation", {
                **SITE, "event_id": "corto", "observed_from": b.isoformat(),
                "observed_to": (b + timedelta(minutes=3)).isoformat(), "station_id": "rain-gauge",
                "value": 1.5, "qc": "INSTRUMENT_QC_PASS", "source_type": "instrument",
                "source_id": "synthetic"})["id"])
        self.ledger.append_journal("OK", obs)
        out = self.status()
        self.assertEqual((out["pares_brutos"], out["observaciones_emparejadas"]), (20, 1))

    def test_source_must_be_outside_ledger(self):
        self.run_cycles(1)
        with self.assertRaises(ValueError):
            drill.drill(self.ledger.root, source=self.ledger.root / "local", clock=lambda: self.now)

    def test_hourly_campaign_at_default_thresholds_completes(self):
        start = START
        for k in range(90 * 24 + 1):
            if k % 10 == 7:                                  # 10 % de ciclos perdidos: cobertura 0,9
                continue
            self.cycle(start + timedelta(hours=k), pairs=k % 96 == 2)
        self.assertEqual(self.status()["estado"], "DATOS_COMPLETOS_RESTAURACION_NO_PROBADA")
        self.complete_drill()
        out = self.status()
        self.assertEqual(out["estado"], "COMPLETADO", out)
        self.assertGreaterEqual(out["cobertura"], 0.8)
        self.assertGreaterEqual(out["observaciones_emparejadas"], 20)
        self.assertGreaterEqual(out["dias_con_pares"], 10)

    def test_deleted_record_is_invalid(self):
        self.run_cycles(3)
        first = json.loads(self.ledger.journal_path.read_text().splitlines()[0])["added_ids"][0]
        (self.ledger.root / "local" / "forecast" / (first + ".json")).unlink()
        self.assertFalse(self.ledger.verify()["ok"])
        self.assertTrue(self.status()["estado"].startswith("INVALIDO:DIARIO_ID_AUSENTE"))

    def test_edited_record_value_is_detected(self):
        # Reproducción H del verificador: cambiar el valor sin cambiar la identidad.
        self.run_cycles(2)
        first = json.loads(self.ledger.journal_path.read_text().splitlines()[0])["added_ids"][0]
        path = self.ledger.root / "local" / "forecast" / (first + ".json")
        record = json.loads(path.read_bytes())
        record["data"]["prediction"] = 42.0
        path.write_bytes(fl._canonical(record))
        v = self.ledger.verify()
        self.assertEqual(v["integridad"], "ROTA")
        self.assertTrue(v["motivo"].startswith("DIARIO_REGISTRO_ALTERADO"))
        self.assertTrue(self.status()["estado"].startswith("INVALIDO:DIARIO_REGISTRO_ALTERADO"))

    def test_legacy_entries_without_hash_are_partial_unknown(self):
        rid = self.forecast(START + timedelta(hours=2))
        entry = {"seq": 0, "timestamp": fl._iso(START), "state": "OK", "added_ids": [rid], "prev_hash": fl.GENESIS}
        entry["hash"] = fl._hash(fl._canonical(entry))
        self.ledger.journal_path.parent.mkdir(parents=True)
        self.ledger.journal_path.write_bytes(fl._canonical(entry))
        self.ledger.append_journal("NO_DATA", [])
        v = self.ledger.verify()
        self.assertEqual((v["ok"], v["integridad"]), (True, "UNKNOWN"))
        self.assertEqual(v["journal"]["parcial"], "ASIENTOS_SIN_HASH n=1")

    def test_future_timestamp_is_invalid(self):
        self.run_cycles(3)
        self.now = START + timedelta(days=1)
        self.assertEqual(self.status()["estado"], "INVALIDO:TIMESTAMP_FUTURO")
        self.now = START + timedelta(days=2, minutes=-9)
        self.assertNotEqual(self.status()["estado"], "INVALIDO:TIMESTAMP_FUTURO")

    def test_truncated_tail_with_receipt_is_orphan(self):
        self.run_cycles(5)
        drill.drill(self.ledger.root, clock=lambda: self.now)
        lines = self.ledger.journal_path.read_bytes().splitlines(keepends=True)
        self.ledger.journal_path.write_bytes(b"".join(lines[:3]))
        v = self.ledger.verify()
        self.assertEqual((v["integridad"], v["motivo"]), ("ROTA", "DIARIO_RECIBO_HUERFANO"))
        self.assertEqual(self.status()["estado"], "INVALIDO:DIARIO_RECIBO_HUERFANO")

    def test_tampered_receipt_breaks_integrity(self):
        self.run_cycles(2)
        receipt = drill.drill(self.ledger.root, clock=lambda: self.now)
        path = self.ledger.root / "journal" / lc.RECEIPTS_DIR / (receipt["sha256"] + ".json")
        text = path.read_text()
        self.assertIn('"origen":"copia_local"', text)
        path.write_text(text.replace('"origen":"copia_local"', '"origen":"copia_externa"'))
        self.assertEqual(self.ledger.verify()["motivo"], "DIARIO_RECIBO_ALTERADO")

    def test_incomplete_tail_is_kept_and_blocks_campaign(self):
        self.run_cycles(2)
        self.ledger.journal_path.write_bytes(self.ledger.journal_path.read_bytes() + b'{"se')
        before = self.ledger.journal_path.read_bytes()
        self.assertEqual(self.ledger.append_journal("OK", []), {"estado": "DIARIO_COLA_INCOMPLETA"})
        self.assertEqual(self.ledger.journal_path.read_bytes(), before)
        self.assertEqual(self.ledger.verify()["motivo"], "DIARIO_COLA_INCOMPLETA")
        out = self.status()
        self.assertEqual(out["estado"], "INVALIDO:DIARIO_COLA_INCOMPLETA")
        self.assertIn("campaña nueva en un directorio nuevo", out["resumen"])

    def test_gap_over_48h_is_invalid(self):
        self.run_cycles(3)
        self.cycle(self.now + timedelta(hours=49))
        self.assertEqual(self.status()["estado"], "INVALIDO:HUECO_MAYOR_QUE_UMBRAL")
        self.assertEqual(self.status(max_gap_hours=72)["estado"], "EN_CURSO")

    def test_error_cycles_do_not_close_a_gap(self):
        self.run_cycles(2)
        for h in range(1, 50):
            self.now = START + timedelta(days=1, hours=h)
            self.ledger.append_journal("ERROR", [])
        self.assertEqual(self.status()["estado"], "INVALIDO:HUECO_ABIERTO_MAYOR_QUE_UMBRAL")

    def test_signature_has_no_declared_dates(self):
        params = inspect.signature(lc.campaign_status).parameters
        self.assertEqual(list(params), ["ledger", "max_gap_hours", "min_coverage", "min_pair_days"])
        with self.assertRaises(TypeError):
            lc.campaign_status(self.ledger, start=START)

    def test_summary_wording(self):
        for key, text in lc.SUMMARIES.items():
            self.assertEqual("completado" in text.lower(), key == "COMPLETADO", key)
            self.assertNotIn("restauración probada", text.lower())

    def test_verify_detects_altered_journal(self):
        self.run_cycles(3)
        lines = self.ledger.journal_path.read_text().splitlines(True)
        lines[1] = lines[1].replace('"state":"OK"', '"state":"NO_DATA"')
        self.ledger.journal_path.write_text("".join(lines))
        self.assertTrue(self.ledger.verify()["motivo"].startswith("DIARIO_HASH_ALTERADO"))

    def test_verify_detects_removed_journal_entry(self):
        self.run_cycles(3)
        lines = self.ledger.journal_path.read_text().splitlines(True)
        self.ledger.journal_path.write_text(lines[0] + lines[2])
        self.assertTrue(self.ledger.verify()["motivo"].startswith("DIARIO_SECUENCIA_ROTA"))

    def test_counters(self):
        self.run_cycles(3, step=timedelta(hours=1), pairs=3)
        self.ledger.append_journal("NO_DATA", [])
        out = self.status()
        self.assertEqual((out["ciclos_registrados"], out["ciclos_ok"], out["ciclos_con_datos"]), (4, 3, 3))
        self.assertEqual(out["ciclos_por_estado"]["NO_DATA"], 1)
        self.assertEqual((out["pares_brutos"], out["observaciones_emparejadas"], out["horas_con_datos"]), (1, 1, 3))
        self.assertEqual(out["fraccion_obs_unknown"], 0.0)

    def test_cli_exit_codes(self):
        cmd = [sys.executable, str(ROOT / "src/nowcast.py"), "ledger", "--root", str(self.ledger.root)]
        self.forecast(START + timedelta(hours=2))
        result = subprocess.run(cmd + ["verify"], capture_output=True, text=True)
        self.assertEqual((result.returncode, json.loads(result.stdout)["integridad"]), (3, "UNKNOWN"))
        self.ledger.append_journal("NO_DATA", [])
        self.assertEqual(subprocess.run(cmd + ["verify"], capture_output=True).returncode, 0)
        out = subprocess.run(cmd + ["campaign-status"], capture_output=True, text=True, check=True)
        self.assertIn("estado", json.loads(out.stdout))
        self.ledger.journal_path.write_text(self.ledger.journal_path.read_text().replace('"seq":0', '"seq":1'))
        self.assertEqual(subprocess.run(cmd + ["verify"], capture_output=True).returncode, 1)


class CycleJournal(unittest.TestCase):
    def test_every_cycle_state_is_journaled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "private"
            ok = {"domain": "portinatx", "ledger_sombra": {"estado": "OK", "pronosticos": 1}}
            empty = {"domain": "portinatx", "ledger_sombra": {"estado": "OK"}}
            for out in (ok, empty):
                proc = subprocess.CompletedProcess([], 0, json.dumps(out), "")
                with patch.object(fc.subprocess, "run", return_value=proc):
                    fc.run(root)
            with patch.object(fc.subprocess, "run", side_effect=RuntimeError("secret")):
                fc.run(root)
            entries, reason = fl.Ledger(root).journal()
            self.assertIsNone(reason)
            self.assertEqual([e["state"] for e in entries], ["OK", "NO_DATA", "ERROR"])
            self.assertNotIn("secret", fl.Ledger(root).journal_path.read_text())

    def test_incomplete_tail_degrades_cycle_without_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "private"
            root.mkdir(mode=0o700)
            journal = root / "journal" / "cycles.jsonl"
            journal.parent.mkdir()
            journal.write_bytes(b'{"se')
            proc = subprocess.CompletedProcess([], 0, json.dumps(
                {"domain": "portinatx", "ledger_sombra": {"estado": "OK", "pronosticos": 1}}), "")
            with patch.object(fc.subprocess, "run", return_value=proc):
                self.assertEqual(fc.run(root), 1)
            health = json.loads((root / "cycle-health.json").read_text())
            self.assertEqual((health["state"], health["journal"]), ("DEGRADED", "DIARIO_COLA_INCOMPLETA"))
            self.assertEqual(journal.read_bytes(), b'{"se')


if __name__ == "__main__":
    unittest.main()
