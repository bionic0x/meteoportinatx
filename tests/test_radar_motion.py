"""#10 — advección de ecos de radar: desplazamiento conocido, crecimiento, clutter, radar viejo y ETA."""
import base64
import math
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import radar_motion as rm  # noqa: E402

UTC = timezone.utc
GEOM = {"lat_n": 40.0, "lon_w": 0.0, "step": 0.025, "nlat": 81, "nlon": 81}
SITE = (40.0 - 40 * 0.025, 40 * 0.025)        # centro de la rejilla
T0 = datetime(2026, 10, 18, 6, 0, tzinfo=UTC)


def blob(ci, cj, r=4, dbz=40, extra=()):
    f = [0] * (GEOM["nlat"] * GEOM["nlon"])
    for i in range(GEOM["nlat"]):
        for j in range(GEOM["nlon"]):
            if (i - ci) ** 2 + (j - cj) ** 2 <= r * r:
                f[i * GEOM["nlon"] + j] = dbz
    for k, v in extra:
        f[k] = v
    return f


def frames(fields, step_min=10, start=T0):
    return [{"time": (start + timedelta(minutes=step_min * n)).isoformat(), "dup": False,
             "grid": base64.b64encode(bytes(f)).decode()} for n, f in enumerate(fields)]


def moving(n=4, di=0, dj=2, ci=40, cj=10, **kw):
    return [blob(ci + di * k, cj + dj * k, **kw) for k in range(n)]


class Motion(unittest.TestCase):
    def test_known_eastward_displacement(self):
        m = rm.estimate_motion(frames(moving(dj=2)), GEOM)
        dlat, dlon = rm.cell_km(GEOM)
        expected = 2 * dlon * 6                               # 2 celdas por 10 min → km/h
        self.assertEqual(m["estado"], "OK")
        self.assertAlmostEqual(m["u_kmh"], expected, delta=0.5)
        self.assertAlmostEqual(m["v_kmh"], 0.0, delta=0.5)
        self.assertEqual(m["hacia_deg"], 90)

    def test_known_southward_displacement(self):
        m = rm.estimate_motion(frames(moving(di=2, dj=0, ci=10, cj=40)), GEOM)
        self.assertLess(m["v_kmh"], -20)
        self.assertEqual(m["hacia_deg"], 180)

    def test_growth_without_movement_is_not_motion(self):
        fields = [blob(40, 40, r=r) for r in (3, 4, 5, 6)]
        m = rm.estimate_motion(frames(fields), GEOM)
        self.assertEqual(m["estado"], "OK")
        self.assertLess(m["velocidad_kmh"], m["incertidumbre_kmh"] + 1)

    def test_static_clutter_does_not_freeze_a_moving_storm(self):
        clutter = [(k, 35) for k in range(70 * 81 + 60, 70 * 81 + 80)]    # 20 celdas fijas
        fields = [blob(40, 10 + 2 * k, extra=clutter) for k in range(4)]
        m = rm.estimate_motion(frames(fields), GEOM)
        self.assertEqual(m["estado"], "OK")
        self.assertGreater(m["u_kmh"], 20)
        self.assertGreaterEqual(m["clutter_celdas"], 20)

    def test_stale_radar_is_motion_unknown(self):
        m = rm.estimate_motion(frames(moving()), GEOM, now=T0 + timedelta(hours=2))
        self.assertEqual(m["estado"], "MOTION_UNKNOWN")

    def test_no_echoes_is_motion_unknown(self):
        empty = [[0] * (81 * 81)] * 4
        self.assertEqual(rm.estimate_motion(frames(empty), GEOM)["estado"], "MOTION_UNKNOWN")

    def test_single_frame_is_motion_unknown(self):
        self.assertEqual(rm.estimate_motion(frames(moving(n=1)), GEOM)["estado"], "MOTION_UNKNOWN")

    def test_incoherent_pairs_are_motion_unknown(self):
        fields = [blob(40, 20), blob(40, 26), blob(40, 20), blob(40, 26)]   # va y vuelve
        self.assertEqual(rm.estimate_motion(frames(fields), GEOM)["estado"], "MOTION_UNKNOWN")

    def test_corrupt_or_duplicate_frames_are_ignored(self):
        fr = frames(moving())
        fr.insert(1, {"time": (T0 + timedelta(minutes=5)).isoformat(), "dup": False, "grid": "!!no-base64"})
        fr[-1]["dup"] = True
        self.assertEqual(rm.estimate_motion(fr, GEOM)["estado"], "OK")


class Eta(unittest.TestCase):
    def test_approaching_echo_has_eta_and_range(self):
        fields = moving(dj=2, cj=10)
        m = rm.estimate_motion(frames(fields), GEOM)
        e = rm.eta_to_site(fields[-1], GEOM, SITE, m)
        self.assertEqual(e["estado"], "OK")
        self.assertTrue(0 < e["eta_min"] <= rm.HORIZON_MIN)
        lo, hi = e["eta_rango_min"]
        self.assertLessEqual(lo, e["eta_min"])
        self.assertGreaterEqual(hi, e["eta_min"])

    def test_receding_echo_has_no_eta(self):
        fields = moving(dj=-2, cj=30)
        m = rm.estimate_motion(frames(fields), GEOM)
        self.assertEqual(rm.eta_to_site(fields[-1], GEOM, SITE, m)["estado"], "SIN_ECO_EN_TRAYECTORIA")

    def test_echo_over_site_is_in_progress(self):
        fields = [blob(40, 40)] * 1 + [blob(40, 40)]
        m = {"estado": "OK", "u_kmh": 10.0, "v_kmh": 0.0, "velocidad_kmh": 10.0, "incertidumbre_kmh": 5.0}
        self.assertEqual(rm.eta_to_site(fields[-1], GEOM, SITE, m)["estado"], "EN_CURSO")

    def test_unknown_motion_gives_unknown_eta(self):
        self.assertEqual(rm.eta_to_site(blob(40, 10), GEOM, SITE, {"estado": "MOTION_UNKNOWN"})["estado"],
                         "MOTION_UNKNOWN")


class WindowSkill(unittest.TestCase):
    def test_advection_beats_eulerian_persistence_for_a_moving_blob(self):
        s = rm.window_skill(frames(moving(n=5, dj=3)), GEOM)
        self.assertEqual(s["estado"], "OK")
        self.assertGreater(s["csi_lagrangiana"], s["csi_euleriana"])

    def test_too_few_frames(self):
        self.assertEqual(rm.window_skill(frames(moving(n=2)), GEOM)["estado"], "INSUFICIENTE")


class EngineIntegration(unittest.TestCase):
    def test_radar_channel_reports_motion_instead_of_closing_speed(self):
        import portinatx_degen as d
        g = d.radar_geom()
        fr = []
        for k in range(4):
            f = [0] * (g["nlat"] * g["nlon"])
            ci, cj = g["nlat"] // 2, 20 + 3 * k
            for i in range(ci - 4, ci + 5):
                for j in range(cj - 4, cj + 5):
                    f[i * g["nlon"] + j] = 40
            fr.append({"time": (d.now_utc() - timedelta(minutes=30 - 10 * k)).isoformat(), "dup": False,
                       "grid": base64.b64encode(bytes(f)).decode(), "cover": {10: 0.0, 30: 0.0, 60: 0.2},
                       "nearest_km": 50.0, "nearest_strong_km": None, "max_dbz_30km": 0, "max_dbz_15km": 0,
                       "site_max_dbz": 0, "qpe_site_mmh": {"marshall_palmer": 0.0, "tropical": 0.0}})
        ch = d.ch_radar(d.SourceResult("radar", "ok", data_time=fr[-1]["time"], payload={"frames": fr}))
        self.assertEqual(ch.metrics["motion"]["estado"], "OK")
        self.assertTrue(any("movimiento de ecos" in e for e in ch.evidence))
        self.assertFalse(any("velocidad de acercamiento" in e for e in ch.evidence))


if __name__ == "__main__":
    unittest.main()
