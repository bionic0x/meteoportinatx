"""GEO-07 07-1: núcleo físico (Froude, N, U⊥, θe, guardas y firma de föhn) con perfiles sintéticos."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import geo07_core as g  # noqa: E402


def profile(lapse_k_per_km, u, v, rh=50.0, z0=1000.0, top=4000.0, t0=10.0):
    """Atmósfera estándar en presión (escala de 8 km) con gradiente térmico y viento constantes."""
    out = []
    z = z0
    while z <= top:
        out.append({"z": z, "t": t0 - lapse_k_per_km * (z - z0) / 1000.0, "rh": rh, "u": u, "v": v,
                    "p": 1013.25 * math.exp(-z / 8000.0)})
        z += 500.0
    return out


class Thermo(unittest.TestCase):
    def test_theta_at_1000_hpa_equals_t(self):
        self.assertAlmostEqual(g.theta(15.0, 1000.0), 288.15)

    def test_theta_e_exceeds_theta_and_grows_with_humidity(self):
        dry, wet = g.theta_e(20.0, 1.0, 900.0), g.theta_e(20.0, 90.0, 900.0)
        self.assertGreater(wet, dry)
        self.assertAlmostEqual(dry, g.theta(20.0, 900.0), delta=1.0)   # r ≈ 0,15 g/kg → +0,6 K

    def test_wind_direction_convention(self):
        self.assertAlmostEqual(g.wind_from_uv(0.0, -10.0)[1], 0.0)      # sopla hacia el S → viene del N
        self.assertAlmostEqual(g.wind_from_uv(10.0, 0.0)[1], 270.0)     # hacia el E → viene del O

    def test_normal_component_sign(self):
        self.assertAlmostEqual(g.normal_component(0.0, -10.0, 0.0), 10.0)    # viento del N contra barrera N
        self.assertAlmostEqual(g.normal_component(0.0, 10.0, 0.0), -10.0)    # viento del S: se aleja
        self.assertAlmostEqual(g.normal_component(-10.0, 0.0, 90.0), 10.0)   # viento del E contra barrera E


class Froude(unittest.TestCase):
    def test_isothermal_stable_layer_gives_known_n(self):
        prof = profile(0.0, 0.0, -10.0)          # isoterma: N² = g²/(cp·T) aprox.
        r = g.froude(prof, 1000.0, 3000.0, 0.0)
        self.assertEqual(r["estado"], "OK")
        self.assertAlmostEqual(r["n"], 0.0195, delta=0.002)
        self.assertAlmostEqual(r["fr"], 10.0 / (r["n"] * 2000.0))

    def test_regimes_follow_wind_speed(self):
        self.assertEqual(g.froude(profile(4.0, 0.0, -3.0), 1000.0, 3000.0, 0.0)["regimen"], "bloqueo")
        # 4 K/km → N ≈ 0,014 s⁻¹; 25 m/s sobre 1 km → Fr ≈ 1,8
        self.assertEqual(g.froude(profile(4.0, 0.0, -25.0), 1000.0, 2000.0, 0.0)["regimen"], "paso_por_encima")
        self.assertEqual(g.froude(profile(4.0, 0.0, -15.0), 1000.0, 2000.0, 0.0)["regimen"], "transicion")

    def test_unstable_layer_is_not_applicable(self):
        r = g.froude(profile(11.0, 0.0, -10.0), 1000.0, 3000.0, 0.0)    # superadiabático
        self.assertEqual((r["estado"], r["fr"]), ("NO_APLICABLE_INESTABLE", None))

    def test_weak_or_parallel_flow_is_ill_defined(self):
        self.assertEqual(g.froude(profile(4.0, 0.0, -1.0), 1000.0, 3000.0, 0.0)["estado"], "FLUJO_MAL_DEFINIDO")
        self.assertEqual(g.froude(profile(4.0, 10.0, 0.0), 1000.0, 3000.0, 0.0)["estado"], "FLUJO_MAL_DEFINIDO")

    def test_levels_below_terrain_are_discarded(self):
        prof = profile(4.0, 0.0, -10.0, z0=1000.0, top=1500.0)
        r = g.froude(prof, 1400.0, 2800.0, 0.0)          # solo 1 nivel válido en la capa
        self.assertEqual(r["estado"], "UNKNOWN")
        self.assertIsNone(r["fr"])

    def test_missing_values_never_become_zero(self):
        prof = profile(4.0, 0.0, -10.0)
        for lv in prof:
            lv["t"] = None
        self.assertEqual(g.froude(prof, 1000.0, 3000.0, 0.0)["estado"], "UNKNOWN")

    def test_saturated_layer_uses_moist_stability(self):
        r = g.froude(profile(5.0, 0.0, -10.0, rh=95.0), 1000.0, 3000.0, 0.0)
        self.assertEqual(r["n_tipo"], "húmeda (θe)")
        dry = g.froude(profile(5.0, 0.0, -10.0, rh=50.0), 1000.0, 3000.0, 0.0)
        self.assertEqual(dry["n_tipo"], "seca (θ)")


class Foehn(unittest.TestCase):
    def test_signature(self):
        up = {"t": 2.0, "rh": 95.0, "p": 780.0}
        down = {"t": 16.0, "rh": 45.0, "p": 880.0}       # Δθ ≈ +4,5 K: calor latente liberado a barlovento
        ok, detail = g.foehn_signature(up, down)
        self.assertTrue(ok, detail)
        # descenso adiabático seco puro (θ conservada): sin firma aunque la HR caiga
        self.assertFalse(g.foehn_signature(up, {"t": 12.0, "rh": 45.0, "p": 880.0})[0])
        self.assertEqual(g.foehn_signature(up, {"t": None, "rh": 40.0, "p": 880.0})[0], None)
        self.assertFalse(g.foehn_signature(up, {"t": 3.0, "rh": 90.0, "p": 880.0})[0])


if __name__ == "__main__":
    unittest.main()
