"""Contrato entre la rejilla que publica Python y el motor de ruta (JS). Sin red: Open-Meteo simulado."""
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import pirineo  # noqa: E402

LATS = [round(42.30 + 0.05 * i, 2) for i in range(8)]
LONS = [round(1.45 + 0.05 * j, 2) for j in range(16)]
N_HOURS = 48


def fake_open_meteo(url, timeout=60):
    """Una respuesta por celda (lat-mayor, como la consulta), con campos analíticos para poder comprobar el resultado."""
    cells = []
    t = [f"2026-11-11T{h % 24:02d}:00" if h < 24 else f"2026-11-12T{h % 24:02d}:00" for h in range(N_HOURS)]
    for la in LATS:
        for lo in LONS:
            hourly = {"time": t}
            hourly["temperature_2m"] = [5 + 10 * (la - 42.30) + 0.1 * h for h in range(N_HOURS)]
            hourly["dew_point_2m"] = [x - 2 for x in hourly["temperature_2m"]]
            hourly["precipitation"] = [1.0 if 3 <= h < 6 else 0.0 for h in range(N_HOURS)]      # 3 mm en el bloque k=3
            hourly["snowfall"] = [0.0] * N_HOURS
            hourly["wind_speed_10m"] = [20.0] * N_HOURS
            hourly["wind_gusts_10m"] = [30.0 + h for h in range(N_HOURS)]
            hourly["freezing_level_height"] = [2400.0] * N_HOURS
            cells.append({"elevation": 1500.0 + 100 * (lo - 1.45), "hourly": hourly})
    return cells


class GridPublishing(unittest.TestCase):
    def grid(self):
        with patch.object(pirineo.pd, "get_json", side_effect=fake_open_meteo):
            return pirineo.src_grid_om()

    def test_shape_and_new_fields(self):
        g = self.grid()
        self.assertEqual(g["paso_h"], 3)
        self.assertEqual(len(g["time"]), 16)
        for v in ("temperature_2m", "dew_point_2m", "wind_speed_10m", "wind_gusts_10m", "precipitation", "freezing_level_height"):
            self.assertEqual(len(g["fields"][v]), 16, v)
            self.assertTrue(all(len(r) == 128 for r in g["fields"][v]), v)
        self.assertEqual(len(g["elev"]), 128)
        self.assertIn("(t_k-1 h, t_k+2 h]", g["acumulado"]["semantica"])
        json.dumps(g, allow_nan=False)

    def test_three_hour_sums_and_instants(self):
        g = self.grid()
        self.assertEqual(g["fields"]["precipitation"][1][0], 3.0)       # horas 3,4,5
        self.assertEqual(g["fields"]["precipitation"][0][0], 0.0)
        self.assertEqual(g["fields"]["wind_gusts_10m"][2][5], 36.0)     # instantáneo en h=6, sin suma

    def test_wrong_cell_count_fails_closed(self):
        with patch.object(pirineo.pd, "get_json", side_effect=lambda *a, **k: fake_open_meteo(*a)[:100]):
            with self.assertRaisesRegex(ValueError, "128"):
                pirineo.src_grid_om()

    @unittest.skipUnless(shutil.which("node"), "Node requerido")
    def test_published_grid_is_consumable_by_route_engine(self):
        g = self.grid()
        script = f"""
const E=require({json.dumps(str(ROOT / 'src' / 'route_engine.js'))});
const G=E.createGrid(JSON.parse(require('fs').readFileSync(0,'utf8')));
const T0=Date.UTC(2026,10,11,0), H=3.6e6;
const a=E.sampleGrid(G,42.40,1.60,T0+4*H);       // dentro del bloque de lluvia (02:00–05:00 UTC): 3 mm/3 h
const b=E.sampleGrid(G,42.40,1.60,T0+8*H);
console.log(JSON.stringify({{a,b,step:G.stepH}}));
"""
        r = subprocess.run(["node", "-e", script], input=json.dumps(g), capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out["step"], 3)
        self.assertEqual(out["a"]["estado"], "ok")
        self.assertAlmostEqual(out["a"]["pr"], 1.0, places=9)
        self.assertAlmostEqual(out["b"]["pr"], 0.0, places=9)
        self.assertAlmostEqual(out["a"]["wind"], 20.0, places=9)
        self.assertAlmostEqual(out["a"]["t2m"], 5 + 10 * (42.40 - 42.30) + 0.1 * 4, places=6)
        self.assertAlmostEqual(out["a"]["elev"], 1500 + 100 * (1.60 - 1.45), places=6)


if __name__ == "__main__":
    unittest.main()
