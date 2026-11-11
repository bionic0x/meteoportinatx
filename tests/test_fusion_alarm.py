"""#17 — 'alarm' siempre con confirmación independiente y una sola Z–R para el umbral de radar."""
import sys
import unittest
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import portinatx_degen as d  # noqa: E402

C, SR = d.Channel, d.SourceResult
INST0 = C("aviso_aemet_activo", 0, "institutional")


def lightning(flashes, minutes_ago=5):
    """flashes: lista de (minutos atrás, distancia km)."""
    now = d.now_utc()
    return SR("rayos_mtg_li", "ok", data_time=now.isoformat(),
              payload={"flashes": [((now - timedelta(minutes=m)).isoformat(), km) for m, km in flashes]})


def radar_frames(dbz):
    mp = d.zr_rate(dbz, *d.CFG["zr"]["marshall_palmer"])
    tr = d.zr_rate(dbz, *d.CFG["zr"]["tropical"])
    return SR("radar", "ok", payload={"frames": [
        {"time": f"2026-10-18T06:{10 * i:02d}:00+00:00", "dup": False, "cover": {10: 0.2, 30: 0.3, 60: 0.4},
         "nearest_km": 5.0, "nearest_strong_km": None, "max_dbz_30km": dbz, "max_dbz_15km": dbz,
         "site_max_dbz": dbz, "qpe_site_mmh": {"marshall_palmer": mp, "tropical": tr}} for i in range(3)]})


class IsolatedObservationCap(unittest.TestCase):
    def test_lightning_burst_alone_is_alert_not_alarm(self):
        light = d.ch_lightning(lightning([(5, 10.0)] * 60))
        self.assertEqual(light.level, 3)  # el canal sigue informando su propia intensidad
        f = d.fuse([INST0, light, C("pluviometros", 0, "obs", group="pluviometros"),
                    C("viento_estaciones", 0, "obs", group="viento")])
        self.assertEqual(f["proposed"], "alert")
        self.assertTrue(any("techo alert" in r for r in f["reasons"]))

    def test_any_single_channel_at_three_is_capped(self):
        for name, group in (("pluviometros", "pluviometros"), ("escorrentia_torrentes", "lluvia_observada"),
                            ("lluvia_observada", "lluvia_observada")):
            with self.subTest(channel=name):
                f = d.fuse([INST0, C(name, 3, "obs", group=group, local=True), C("radar", 0, "obs")])
                self.assertEqual(f["proposed"], "alert")

    def test_independent_local_confirmation_still_reaches_alarm(self):
        f = d.fuse([INST0, C("radar", 3, "obs", local=True),
                    C("pluviometros", 2, "obs", group="pluviometros", local=True)])
        self.assertEqual(f["proposed"], "alarm")

    def test_lightning_and_rain_are_different_hazards_and_do_not_confirm_each_other(self):
        for lead, support in ((C("rayos", 3, "obs", local=True),
                               C("pluviometros", 2, "obs", group="pluviometros", local=True)),
                              (C("pluviometros", 3, "obs", group="pluviometros", local=True),
                               C("rayos", 2, "obs", local=True))):
            with self.subTest(lead=lead.name):
                f = d.fuse([INST0, lead, support, C("radar", 0, "obs")])
                self.assertEqual(f["proposed"], "alert")

    def test_electrical_hazard_is_not_hidden(self):
        light = d.ch_lightning(lightning([(5, 10.0)] * 60))
        self.assertEqual(light.level, 3)
        hz = d.local_hazard_state({"rayos": light}, {})
        self.assertEqual(hz["rayos"]["nivel"], "alarm")

    def test_manual_es_alert_and_flooding_holds_are_preserved(self):
        self.assertIn("ES-Alert", d.precaution_hold({"es_alert": {"value": "active", "edad_h": 0.5}}))
        self.assertIn("flooding", d.precaution_hold({"flooding": {"value": "observed", "edad_h": 0.2}}))

    def test_same_family_but_same_root_does_not_confirm(self):
        f = d.fuse([INST0, C("lluvia_observada", 3, "obs", local=True),
                    C("escorrentia_torrentes", 2, "obs", group="lluvia_observada", local=True)])
        self.assertEqual(f["proposed"], "alert")

    def test_official_red_floor_is_unchanged(self):
        f = d.fuse([C("aviso_aemet_activo", 3, "institutional"), C("radar", 0, "obs"),
                    C("pluviometros", 0, "obs", group="pluviometros")])
        self.assertEqual(f["proposed"], "alarm")


class LightningChannel(unittest.TestCase):
    def test_levels_by_count_within_30_km(self):
        cases = {0: 0, 1: 1, 10: 2, 50: 3}
        for n, lvl in cases.items():
            with self.subTest(flashes=n):
                self.assertEqual(d.ch_lightning(lightning([(30, 25.0)] * n)).level, lvl)

    def test_flashes_beyond_30_km_only_watch(self):
        self.assertEqual(d.ch_lightning(lightning([(30, 45.0)] * 80)).level, 1)

    def test_locality_needs_three_flashes_within_local_radius(self):
        near = d.CFG["local_obs_km"] - 1
        self.assertFalse(d.ch_lightning(lightning([(5, near)] * 2)).local)
        self.assertTrue(d.ch_lightning(lightning([(5, near)] * 3)).local)

    def test_activity_jump_raises_to_alert(self):
        ch = d.ch_lightning(lightning([(3, 50.0)] * 4))   # 4 recientes, 0 previos, todos a >30 km
        self.assertEqual(ch.level, 2)
        self.assertTrue(any("SALTO DE RAYOS" in e for e in ch.evidence))

    def test_unavailable_source_is_unknown(self):
        self.assertFalse(d.ch_lightning(None).available)


class RadarZR(unittest.TestCase):
    def test_threshold_uses_one_declared_relation(self):
        self.assertIn(d.CFG["radar_threshold_zr"], d.CFG["zr"])

    def test_dbz_ladder_with_one_and_two_strong_frames(self):
        def frames(dbz, n_strong):
            src = radar_frames(dbz)
            for i, f in enumerate(src.payload["frames"]):
                if i < 3 - n_strong:                       # frames débiles al principio de la ventana
                    f.update(max_dbz_15km=20, max_dbz_30km=20, site_max_dbz=20,
                             qpe_site_mmh={"marshall_palmer": 0.6, "tropical": 0.9})
            return src
        for dbz in (39, 40, 42, 45):
            for n in (1, 2):
                with self.subTest(dbz=dbz, strong_frames=n):
                    expected = 2 if (dbz >= 45 and n >= 2) else 1
                    self.assertEqual(d.ch_radar(frames(dbz, n)).level, expected)

    def test_42_dbz_persistent_is_not_alert(self):
        ch = d.ch_radar(radar_frames(42))
        self.assertGreater(d.zr_rate(42, *d.CFG["zr"]["tropical"]), d.CFG["radar_alert_qpe"])
        self.assertEqual(ch.level, 1)

    def test_45_dbz_persistent_is_alert(self):
        self.assertEqual(d.ch_radar(radar_frames(45)).level, 2)

    def test_both_relations_still_reported_as_diagnostic(self):
        ev = " ".join(d.ch_radar(radar_frames(42)).evidence)
        self.assertIn("marshall_palmer", ev)
        self.assertIn("tropical", ev)


if __name__ == "__main__":
    unittest.main()
