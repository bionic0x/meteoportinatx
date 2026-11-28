"""GEO-07 07-1: núcleo físico (Froude, N seca y saturada, U⊥, guardas y firma de föhn) con perfiles sintéticos."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import geo07_core as g  # noqa: E402

NORTH = 0.0     # normal de la cresta hacia barlovento norte: incide el viento del N (v < 0)


def profile(lapse_k_per_km, u, v, rh=50.0, z0=1000.0, top=4000.0, t0=10.0, step=500.0):
    """Atmósfera con presión de escala 8 km, gradiente térmico y viento constantes."""
    out = []
    z = z0
    while z <= top:
        out.append({"z": z, "t": t0 - lapse_k_per_km * (z - z0) / 1000.0, "rh": rh, "u": u, "v": v,
                    "p": 1013.25 * math.exp(-z / 8000.0)})
        z += step
    return out


def moist_adiabat(z0=1000.0, top=3000.0, t0=8.0):
    out, t, z = [], t0, z0
    while z <= top + 1e-6:
        p = 1013.25 * math.exp(-z / 8000.0)
        if abs((z - z0) % 500.0) < 1e-6:
            out.append({"z": z, "t": t, "rh": 100.0, "u": 0.0, "v": -15.0, "p": p})
        t -= g.moist_lapse_rate(t, p) * 10.0
        z += 10.0
    return out


class Thermo(unittest.TestCase):
    def test_theta_at_1000_hpa_equals_t(self):
        self.assertAlmostEqual(g.theta(15.0, 1000.0), 288.15)

    def test_theta_e_exceeds_theta_and_grows_with_humidity(self):
        dry, wet = g.theta_e(20.0, 1.0, 900.0), g.theta_e(20.0, 90.0, 900.0)
        self.assertGreater(wet, dry)
        self.assertAlmostEqual(dry, g.theta(20.0, 900.0), delta=1.0)   # r ≈ 0,15 g/kg → +0,6 K

    def test_moist_lapse_rate_between_limits(self):
        self.assertAlmostEqual(g.moist_lapse_rate(-40.0, 500.0), g.G / g.CP, delta=0.0007)   # frío: casi seco
        self.assertLess(g.moist_lapse_rate(20.0, 1000.0), 0.0045)                            # cálido: ~4 K/km

    def test_moist_adiabat_is_near_neutral_for_saturated_n2(self):
        lv = moist_adiabat()
        self.assertLess(abs(g.moist_n2(lv[0], lv[-1])), 3e-5)
        self.assertGreater(g.dry_n2(lv[0], lv[-1]), 1e-4)


class Geometry(unittest.TestCase):
    def test_wind_direction_convention(self):
        self.assertAlmostEqual(g.wind_from_uv(0.0, -10.0)[1], 0.0)
        self.assertAlmostEqual(g.wind_from_uv(10.0, 0.0)[1], 270.0)

    def test_incident_component_sign(self):
        self.assertAlmostEqual(g.incident_component(0.0, -10.0, 0.0), 10.0)     # del N contra cresta con normal N
        self.assertAlmostEqual(g.incident_component(0.0, 10.0, 0.0), -10.0)     # del S: desde sotavento
        self.assertAlmostEqual(g.incident_component(10.0, 0.0, 0.0), 0.0)       # paralelo
        self.assertAlmostEqual(g.incident_component(-10.0, 0.0, 90.0), 10.0)

    def test_angular_spread_wraps(self):
        self.assertAlmostEqual(g.angular_spread([359.0, 1.0]), 2.0)
        self.assertAlmostEqual(g.angular_spread([0.0, 40.0, 320.0]), 80.0)
        self.assertAlmostEqual(g.angular_spread([10.0]), 0.0)

    def test_crest_normal_points_to_windward(self):
        self.assertAlmostEqual(g.crest_normal(1.5, 42.5, 2.0, 42.5, 1.75, 42.7), 0.0, delta=1e-6)
        self.assertAlmostEqual(g.crest_normal(1.5, 42.5, 2.0, 42.5, 1.75, 42.3), 180.0, delta=1e-6)
        self.assertIsNone(g.crest_normal(1.5, 42.5, 1.5, 42.5, 1.75, 42.7))

    def test_thickness_weighted_mean_irregular_levels(self):
        self.assertAlmostEqual(g.thickness_weighted_mean([0.0, 100.0, 1000.0], [10.0, 10.0, 0.0]), 5.5)


class Validation(unittest.TestCase):
    def assertUnknown(self, prof, **kw):
        r = g.froude(prof, 1000.0, 3000.0, NORTH, **kw)
        self.assertEqual(r["estado"], "UNKNOWN", r["motivo"])
        self.assertIsNone(r["fr"])
        return r

    def mutate(self, key, value, idx=1):
        prof = profile(4.0, 0.0, -10.0)
        prof[idx][key] = value
        return prof

    def test_non_physical_values_are_unknown(self):
        for key, value in [("p", 0.0), ("p", -5.0), ("t", 200.0), ("t", -150.0), ("rh", 120.0), ("rh", -5.0),
                           ("t", float("nan")), ("u", float("inf")), ("v", float("-inf")), ("z", float("nan"))]:
            with self.subTest(key=key, value=value):
                self.assertUnknown(self.mutate(key, value))

    def test_missing_values_never_become_zero(self):
        prof = profile(4.0, 0.0, -10.0)
        for lv in prof:
            lv["t"] = None
        self.assertUnknown(prof)

    def test_levels_below_terrain_are_discarded(self):
        r = g.froude(profile(4.0, 0.0, -10.0, top=1500.0), 1400.0, 2800.0, NORTH)
        self.assertEqual(r["estado"], "UNKNOWN")

    def test_insufficient_vertical_coverage(self):
        r = self.assertUnknown(profile(4.0, 0.0, -10.0, top=1500.0))     # cubre 500 de 2000 m
        self.assertIn("cubren", r["motivo"])

    def test_undefined_barrier(self):
        for args in [(3000.0, 1000.0, NORTH), (1000.0, 3000.0, None), (1000.0, 3000.0, float("nan"))]:
            with self.subTest(args=args):
                self.assertEqual(g.froude(profile(4.0, 0.0, -10.0), *args)["estado"], "UNKNOWN")


class Froude(unittest.TestCase):
    def test_isothermal_stable_layer_gives_known_n(self):
        r = g.froude(profile(0.0, 0.0, -10.0), 1000.0, 3000.0, NORTH)
        self.assertEqual((r["estado"], r["saturacion"]), ("OK", "no_saturada"))
        self.assertAlmostEqual(r["n_seco"], 0.0195, delta=0.002)
        self.assertAlmostEqual(r["fr"], 10.0 / (r["n_seco"] * 2000.0))

    def test_regimes_follow_wind_speed(self):
        self.assertEqual(g.froude(profile(4.0, 0.0, -3.0), 1000.0, 3000.0, NORTH)["regimen"], "bloqueo")
        # 4 K/km → N ≈ 0,014 s⁻¹; sobre 1 km: 25 m/s → Fr ≈ 1,8; 15 m/s → Fr ≈ 1,1
        self.assertEqual(g.froude(profile(4.0, 0.0, -25.0), 1000.0, 2000.0, NORTH)["regimen"], "paso_por_encima")
        self.assertEqual(g.froude(profile(4.0, 0.0, -15.0), 1000.0, 2000.0, NORTH)["regimen"], "transicion")

    def test_unstable_layer_is_not_applicable(self):
        r = g.froude(profile(11.0, 0.0, -10.0), 1000.0, 3000.0, NORTH)
        self.assertEqual((r["estado"], r["fr"]), ("NO_APLICABLE_INESTABLE", None))

    def test_intermediate_unstable_sublayer_is_reported(self):
        prof = profile(2.0, 0.0, -10.0)              # estable en bloque
        prof[2]["t"] = prof[1]["t"] - 6.0            # 1500→2000 m: −12 K/km, superadiabático
        r = g.froude(prof, 1000.0, 3000.0, NORTH)
        self.assertEqual(r["estado"], "OK")
        self.assertIn((1500.0, 2000.0), r["subcapas_inestables"])
        self.assertIn("subcapa", r["motivo"])
        self.assertLess(min(r["sensibilidad"]["n2_seco_subcapas"]), 0)

    def test_parallel_and_contrary_flow_are_not_incident(self):
        par = g.froude(profile(4.0, 10.0, 0.0), 1000.0, 3000.0, NORTH)
        self.assertEqual(par["estado"], "FLUJO_NO_INCIDENTE")
        contra = g.froude(profile(4.0, 0.0, 15.0), 1000.0, 3000.0, NORTH)    # viento del S, barlovento al N
        self.assertEqual(contra["estado"], "FLUJO_NO_INCIDENTE")
        self.assertLess(contra["u_perp"], 0)
        self.assertIsNone(contra["fr"])

    def test_direction_spread_uses_all_levels(self):
        prof = profile(4.0, 0.0, -10.0)              # todos del N
        for lv, d in zip(prof, [0.0, 40.0, 320.0, 0.0, 0.0, 0.0, 0.0]):
            a = math.radians(d)
            lv["u"], lv["v"] = -10.0 * math.sin(a), -10.0 * math.cos(a)
        r = g.froude(prof, 1000.0, 4000.0, NORTH)
        self.assertEqual(r["estado"], "FLUJO_MAL_DEFINIDO")
        self.assertAlmostEqual(r["sensibilidad"]["dispersion_dir"], 80.0)

    def test_weighted_mean_with_irregular_levels(self):
        prof = profile(4.0, 0.0, -10.0, top=3000.0)
        prof = [lv for lv in prof if lv["z"] in (1000.0, 1500.0, 3000.0)]
        prof[0]["v"] = prof[1]["v"] = -10.0
        prof[2]["v"] = -2.0
        r = g.froude(prof, 1000.0, 3000.0, NORTH)
        self.assertAlmostEqual(r["u_perp"], (10.0 * 500 + 6.0 * 1500) / 2000.0)   # 7,0 (media aritmética 7,33)

    def test_missing_humidity_makes_moist_unknown(self):
        r = g.froude(profile(4.0, 0.0, -10.0, rh=None), 1000.0, 3000.0, NORTH)
        self.assertEqual((r["estado"], r["saturacion"]), ("PARCIAL", "UNKNOWN"))
        self.assertIsNone(r["fr"])
        self.assertIsNone(r["regimen"])
        self.assertIsNone(r["n_humedo"])
        self.assertIsNotNone(r["fr_seco"])

    def test_saturated_layer_uses_durran_klemp(self):
        r = g.froude(profile(5.0, 0.0, -10.0, rh=95.0), 1000.0, 3000.0, NORTH)
        self.assertEqual(r["saturacion"], "saturada")
        self.assertEqual(r["fr"], r["fr_humedo"])
        self.assertGreater(r["fr_humedo"], r["fr_seco"])     # N_m < N: la saturación reduce la estabilidad
        self.assertEqual(g.froude(profile(5.0, 0.0, -10.0, rh=50.0), 1000.0, 3000.0, NORTH)["fr"],
                         g.froude(profile(5.0, 0.0, -10.0, rh=50.0), 1000.0, 3000.0, NORTH)["fr_seco"])

    def test_moist_adiabatic_saturated_layer_is_near_neutral(self):
        # Sobre una adiabática saturada solo queda el término −g/(1+qw)·dqw/dz de Durran y Klemp: N_m ≪ N seco.
        r = g.froude(moist_adiabat(), 1000.0, 3000.0, NORTH)
        self.assertIn(r["estado"], ("NO_APLICABLE_INESTABLE", "OK"))
        if r["estado"] == "OK":
            self.assertGreater(r["fr"], 2 * r["fr_seco"])


class Foehn(unittest.TestCase):
    up = {"t": 2.0, "rh": 95.0, "p": 780.0}

    def test_signature(self):
        ok, detail = g.foehn_signature(self.up, {"t": 16.0, "rh": 45.0, "p": 880.0})   # Δθ ≈ +4,5 K
        self.assertTrue(ok, detail)
        # descenso adiabático seco puro (θ conservada): sin firma aunque la HR caiga
        self.assertFalse(g.foehn_signature(self.up, {"t": 12.0, "rh": 45.0, "p": 880.0})[0])
        self.assertFalse(g.foehn_signature(self.up, {"t": 3.0, "rh": 90.0, "p": 880.0})[0])

    def test_missing_or_invalid_is_unknown(self):
        self.assertIsNone(g.foehn_signature(self.up, {"t": None, "rh": 40.0, "p": 880.0})[0])
        self.assertIsNone(g.foehn_signature(self.up, {"t": 12.0, "rh": 140.0, "p": 880.0})[0])
        self.assertIsNone(g.foehn_signature(self.up, {"t": float("nan"), "rh": 40.0, "p": 880.0})[0])
        self.assertIsNone(g.foehn_signature({"t": 2.0, "rh": 95.0, "p": 0.0}, {"t": 12.0, "rh": 40.0, "p": 880.0})[0])


if __name__ == "__main__":
    unittest.main()
