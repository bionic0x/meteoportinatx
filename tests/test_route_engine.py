"""Motor de ruta (JS) frente al código Python de referencia: la física no puede divergir en silencio."""
import json
import random
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import knowledge_base as kb  # noqa: E402
import pirineo  # noqa: E402
import portinatx_degen as pd  # noqa: E402

ENGINE = ROOT / "src" / "route_engine.js"
HAVE_NODE = shutil.which("node") is not None


def node_eval(script: str, payload) -> object:
    code = f"const E=require({json.dumps(str(ENGINE))});const IN=JSON.parse(require('fs').readFileSync(0,'utf8'));{script}"
    r = subprocess.run(["node", "-e", code], input=json.dumps(payload), capture_output=True, text=True, timeout=60)
    if r.returncode:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


@unittest.skipUnless(HAVE_NODE, "Node requerido")
class RouteEngineContract(unittest.TestCase):
    def test_node_suite(self):
        r = subprocess.run(["node", str(ROOT / "tests" / "test_route_engine.cjs")], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertIn("pruebas OK", r.stdout)

    def test_snow_constants_match_knowledge_base(self):
        d = node_eval("console.log(JSON.stringify(E.DEFAULTS))", None)
        self.assertEqual(d["snowTw"], kb.PRIORS["wet_bulb_snow_threshold_c"]["value"])
        self.assertEqual(d["snowHalf"], kb.PRIORS["snow_ramp_half_width_c"]["value"])

    def test_solid_fraction_and_wet_bulb_parity_with_python(self):
        rng = random.Random(7)
        cases = []
        for _ in range(400):
            t = rng.uniform(-12, 12)
            td = t - rng.uniform(0, 12)
            z = rng.uniform(300, 3000)
            cases.append([t, td, z])
        cases += [[1.0, None, 1800], [0.7, 0.7, 0], [-5, -5, 2500], [None, 0, 1000]]
        js = node_eval("console.log(JSON.stringify(IN.map(([t,td,z])=>[E.solidFraction(t,td,z),"
                       "(t==null||td==null)?null:E.wetBulb(t,td,1013.25*Math.pow(1-2.25577e-5*z,5.25588))])))", cases)
        for (t, td, z), (frac, tw) in zip(cases, js):
            self.assertAlmostEqual(frac, pirineo.snow_frac(t, td, z), places=9, msg=str((t, td, z)))
            if tw is not None:
                p = 1013.25 * (1 - 2.25577e-5 * z) ** 5.25588
                self.assertAlmostEqual(tw, pd.wet_bulb(t, td, p), places=9)

    def test_dem_bilinear_parity_with_python(self):
        rng = random.Random(3)
        nlat, nlon, step = 40, 55, 0.004
        rows = [[rng.randint(600, 2900) for _ in range(nlon)] for _ in range(nlat)]
        dem = {"lat_n": 42.68, "lon_w": 1.40, "step": step, "nlat": nlat, "nlon": nlon, "rows": rows}
        packed = pirineo.pack_dem(dem)
        pts = [[42.68 - rng.uniform(-0.02, nlat * step), 1.40 + rng.uniform(-0.02, nlon * step)] for _ in range(300)]
        pts += [[42.68, 1.40], [42.68 - (nlat - 1) * step, 1.40 + (nlon - 1) * step], [43.0, 1.5]]
        js = node_eval("const D=E.makeDem(IN.dem);console.log(JSON.stringify(IN.pts.map(([a,b])=>D.at(a,b))))", {"dem": packed, "pts": pts})
        for (la, lo), v in zip(pts, js):
            ref = pirineo.dem_at(dem, la, lo)
            if ref is None:
                self.assertIsNone(v, (la, lo))
            else:
                self.assertAlmostEqual(v, ref, delta=0.06, msg=str((la, lo)))   # dem_at redondea a 0,1 m

    def test_every_threshold_declares_provenance(self):
        t = node_eval("console.log(JSON.stringify(E.THRESHOLDS))", None)
        self.assertEqual(set(t), {"lluvia", "viento", "nieve", "frio"})
        for name, spec in t.items():
            self.assertIn(spec["status"], {"UNVERIFIED", "ORIENTATIVE"}, name)
            self.assertTrue(spec["basis"] and spec["unit"], name)


if __name__ == "__main__":
    unittest.main()
