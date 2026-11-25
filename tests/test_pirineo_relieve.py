"""Pirineo · relieve fino (cota efectiva, cubeta fría) y carreteras: contratos y ausencia de dato = UNKNOWN."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pirineo  # noqa: E402
import pirineo_carreteras as roads  # noqa: E402
import pirineo_orografia as oro  # noqa: E402

NOW = datetime(2026, 11, 26, 3, 0, tzinfo=timezone.utc)


def doc_stub(cpi=3.0, p=2.0, w=1.0):
    pt = {"nombre": "X", "p_oro_mmh": [p] * 16, "ascenso_ms": [w] * 16, "cpi": cpi, "tpi_m": -100, "cubeta_calibrable": True}
    return {"schema": 1, "generado": "2026-11-25T00:00:00Z", "fuente_dem": "stub",
            "modelo": {"nombre": "stub", "U_ref_ms": 14.0, "direcciones": [i * 22.5 for i in range(16)]},
            "cubeta": {"cpi_ref_das": 3.0, "dtmax_ref_c": 20.0},
            "puntos": {"das": dict(pt), "masella": {**pt, "cpi": 0.5}},
            "carreteras": {"c16": {"nombre": "C-16", "pais": "CAT", "etiquetas": [[0, "Das"], [1, "Puigcerdà"]],
                                   "muestras": [{"lat": 42.38, "lon": 1.866, "km": 0, "z": 1100, "cpi": 3.0, "cuenca": True},
                                                {"lat": 42.43, "lon": 1.928, "km": 7, "z": 1150, "cpi": 3.0, "cuenca": True}]}},
            "puertos": {}}


def profile(hours=24, pr=2.0, cota=1500, wind=50.0, d=135.0):
    return [{"t": (NOW + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M"), "cota_copo_m": cota, "pr_mm": pr,
             "viento700_kmh": wind, "dir700": d, "flujo": "SE"} for h in range(hours)]


def series(tmin=-4.0, cloud=0.0):
    tt = [(NOW + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(-2, 26)]
    T = [tmin + abs(h - 3) * 0.5 for h in range(len(tt))]
    return {"time": tt, "m": {"ecmwf_ifs": {"temperature_2m": T, "cloud_cover": [cloud] * len(tt)}}}


POIS = [{"id": "das", "lat": 42.38, "lon": 1.866, "zona": "Cerdanya"},
        {"id": "masella", "lat": 42.356, "lon": 1.908, "zona": "Cerdanya"}]


class Orografia(unittest.TestCase):
    def test_precipitacion_baja_la_cota_y_sin_lluvia_no(self):
        f = oro.forzamiento(doc_stub()["puntos"]["das"], doc_stub(), 135, 14.0)   # p_oro 2 → realce 1,33
        self.assertEqual(oro.cota_efectiva(1500, 3.0, f)["fusion_m"], round(100 * (3.0 * 1.33) ** 0.7))
        self.assertEqual(oro.cota_efectiva(1500, 0.0, f)["cota_copo_efectiva_m"], 1500)

    def test_precipitacion_desconocida_es_parcial_no_cero(self):
        f = oro.forzamiento(doc_stub()["puntos"]["das"], doc_stub(), 135, 14.0)
        c = oro.cota_efectiva(1500, None, f)
        self.assertEqual(c["estado"], "PARCIAL")
        self.assertIsNone(c["fusion_m"])

    def test_realce_es_factor_sin_unidades(self):
        d = doc_stub(p=6.0)
        f = oro.forzamiento(d["puntos"]["das"], d, 135, 14.0)
        self.assertEqual(f["realce"], 2.0)                       # tope
        self.assertEqual(oro.cota_efectiva(1500, 0.0, f)["fusion_m"], 0)   # sin lluvia del perfil, el relieve no funde

    def test_fusion_no_baja_del_suelo(self):
        f = oro.forzamiento(doc_stub()["puntos"]["das"], doc_stub(), 135, 14.0)
        self.assertEqual(oro.cota_efectiva(1500, 5.0, f, capa_m=120)["fusion_m"], 120)

    def test_sin_precipitacion_en_24h_no_es_unknown(self):
        with patch.object(oro, "load", return_value=doc_stub()):
            r = pirineo.relieve_diag(POIS, {"sur": profile(pr=0.0)}, None, now=NOW)
        das = r["orografia"]["puntos"]["das"]
        self.assertEqual(das["estado"], "OK")
        self.assertTrue(das["sin_precipitacion_24h"])
        c16 = r["exposicion"]["carreteras"]["c16"]
        self.assertEqual((c16["km_sin_precipitacion"], c16["km_unknown"], c16["km_sobre_cota"]), (7.0, 0.0, 0.0))

    def test_relieve_diag_minimo_24h_y_unknown_sin_perfil(self):
        with patch.object(oro, "load", return_value=doc_stub()):
            r = pirineo.relieve_diag(POIS, {"sur": profile()}, None, now=NOW)
            das = r["orografia"]["puntos"]["das"]
            self.assertEqual(das["estado"], "OK")
            self.assertLess(das["min24"]["cota_copo_efectiva_m"], 1500)
            r = pirineo.relieve_diag(POIS, {}, None, now=NOW)
            self.assertEqual(r["orografia"]["puntos"]["das"]["estado"], "UNKNOWN")
            self.assertIsNone(r["exposicion"]["carreteras"]["c16"]["km_sobre_cota"])

    def test_precipitacion_desconocida_no_da_exposicion_cero(self):
        with patch.object(oro, "load", return_value=doc_stub()):
            r = pirineo.relieve_diag(POIS, {"sur": profile(pr=None)}, None, now=NOW)
        self.assertEqual(r["orografia"]["puntos"]["das"]["estado"], "PARCIAL")
        self.assertIsNone(r["orografia"]["puntos"]["das"]["min24"])
        c16 = r["exposicion"]["carreteras"]["c16"]
        self.assertIsNone(c16["km_sobre_cota"])
        self.assertEqual(c16["km_unknown"], 7.0)

    def test_estado_global_no_es_ok_si_todo_es_unknown(self):
        with patch.object(oro, "load", return_value=doc_stub()):
            r = pirineo.relieve_diag(POIS, {}, None, now=NOW)
        self.assertEqual(r["orografia"]["estado"], "UNKNOWN")

    def test_divisoria_toma_la_cota_mas_baja(self):
        d = doc_stub(p=0.0, w=0.0)
        prof = {"norte": profile(pr=0.5, cota=1400), "sur": profile(pr=0.5, cota=1700)}
        r = oro.diag_punto(d["puntos"]["das"], d, prof, ["norte", "sur"], NOW)
        self.assertEqual(r["min24"]["cota_copo_efectiva_m"], 1400 - round(100 * 0.5 ** 0.7))
        self.assertEqual(r["min24"]["perfil"], "norte")

    def test_tabla_incompleta_no_carga(self):
        import json
        import tempfile
        d = doc_stub()
        d["puntos"]["das"]["p_oro_mmh"] = [1.0] * 15
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(d, f)
        self.assertIsNone(oro.load(Path(f.name)))
        Path(f.name).unlink()

    def test_puntos_del_json_coinciden_con_pois(self):
        self.assertEqual(set(oro.load()["puntos"]), {p[0] for p in pirineo.POIS})

    def test_sin_tablas_todo_unknown(self):
        with patch.object(oro, "load", return_value=None):
            r = pirineo.relieve_diag(POIS, {"sur": profile()}, None, now=NOW)
        self.assertTrue(all(v["estado"] == "UNKNOWN" for v in r.values()))


class Cubeta(unittest.TestCase):
    def test_noche_despejada_y_calma_enfria_la_cubeta(self):
        d = doc_stub()
        c = oro.cubeta_punto(d["puntos"]["das"], d, series(-4.0, 0.0), profile(wind=10.0), NOW)
        m = c["modelos"]["ecmwf_ifs"]
        self.assertEqual(m["estado"], "OK")
        self.assertAlmostEqual(m["tmin_est"], -4.0 - 0.6 * 20.0, places=1)

    def test_cielo_cubierto_no_cambia_la_minima(self):
        d = doc_stub()
        m = oro.cubeta_punto(d["puntos"]["das"], d, series(-4.0, 100.0), profile(wind=10.0), NOW)["modelos"]["ecmwf_ifs"]
        self.assertEqual(m["tmin_est"], -4.0)

    def test_sin_viento_de_700_es_unknown(self):
        d = doc_stub()
        m = oro.cubeta_punto(d["puntos"]["das"], d, series(), [], NOW)["modelos"]["ecmwf_ifs"]
        self.assertEqual(m["estado"], "UNKNOWN")

    def test_punto_que_no_es_cubeta(self):
        d = doc_stub()
        self.assertEqual(oro.cubeta_punto(d["puntos"]["masella"], d, series(), profile(), NOW)["estado"], "NO_APLICA")

    def test_valle_estrecho_no_calibrado(self):
        d = doc_stub()
        pt = {**d["puntos"]["das"], "cubeta_calibrable": False}
        self.assertEqual(oro.cubeta_punto(pt, d, series(), profile(), NOW)["estado"], "NO_CALIBRADO")

    def test_rampa_de_calma(self):
        self.assertAlmostEqual(oro.factor_noche(0, 10.0), 0.5)
        self.assertEqual(oro.factor_noche(50, 6.0), 0.5)

    def test_andorra_se_publica_como_no_calibrado(self):
        d = doc_stub()
        d["puntos"]["escaldes"] = {**d["puntos"]["das"], "cubeta_calibrable": False}
        pois = POIS + [{"id": "escaldes", "lat": 42.509, "lon": 1.539, "zona": "Andorra"}]
        with patch.object(oro, "load", return_value=d):
            r = pirineo.relieve_diag(pois, {"sur": profile()}, {"escaldes": series(), "das": series()}, now=NOW)
        self.assertEqual(r["cubeta_fria"]["puntos"]["escaldes"]["estado"], "NO_CALIBRADO")

    def test_tablas_cargan_dentro_de_un_zipapp(self):
        import subprocess
        import tempfile
        import zipfile
        src = Path(__file__).resolve().parents[1] / "src"
        with tempfile.TemporaryDirectory() as td:
            pyz = Path(td) / "t.pyz"
            with zipfile.ZipFile(pyz, "w") as z:
                for n in ("pirineo_orografia.py", "pirineo_orografia.json"):
                    z.write(src / n, n)
                z.writestr("__main__.py", "import pirineo_orografia as o\nd = o.load()\nprint(d['puntos']['das']['cpi'] if d else 'NONE')\n")
            out = subprocess.run([sys.executable, "-I", str(pyz)], capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertNotEqual(out.stdout.strip(), "NONE")

    def test_tablas_reales_das_es_cubeta_y_masella_menos(self):
        real = oro.load()
        self.assertIsNotNone(real)
        self.assertGreater(real["puntos"]["das"]["cpi"], 2 * real["puntos"]["masella"]["cpi"])
        self.assertEqual(len(real["carreteras"]), 11)


class Carreteras(unittest.TestCase):
    def test_fallo_de_red_es_unknown_no_via_libre(self):
        def boom(url):
            raise TimeoutError
        st = roads.estado_oficial(boom)
        for k in ("sct", "bison_fute"):
            self.assertEqual(st["fuentes"][k]["estado"], "UNKNOWN")
            self.assertIsNone(st["fuentes"][k]["incidencias"])

    def test_xml_corrupto_es_unknown(self):
        st = roads.estado_oficial(lambda url: b"<no-cierra")
        self.assertEqual(st["fuentes"]["sct"]["estado"], "UNKNOWN")
        self.assertEqual(st["fuentes"]["bison_fute"]["estado"], "UNKNOWN")

    def test_xml_valido_sin_registros_es_unknown(self):
        st = roads.estado_oficial(lambda url: b"<root><nuevoFormato/></root>")
        self.assertEqual(st["fuentes"]["sct"]["estado"], "UNKNOWN")
        self.assertEqual(st["fuentes"]["bison_fute"]["estado"], "UNKNOWN")

    def test_registro_datex_ilegible_no_tumba_el_feed(self):
        dx = (b'<d><situationRecord><latitude>42,56</latitude><longitude>1.82</longitude></situationRecord>'
              b'<situationRecord><latitude>42.56</latitude><longitude>1.82</longitude><roadNumber>N20</roadNumber>'
              b'</situationRecord></d>')
        items, meta = roads.parse_datex(dx)
        self.assertEqual((len(items), meta["descartados_coordenadas"]), (1, 1))

    def test_palabras_completas(self):
        self.assertFalse(roads._is_meteo("Neutralisation de voie · service de police"))
        self.assertTrue(roads._is_meteo("Cadenes obligatòries per neu"))

    def test_fuera_de_la_zona_se_descarta(self):
        gml = (b'<r xmlns:gml="http://www.opengis.net/gml"><gml:featureMember><i><carretera>AP-7</carretera>'
               b'<gml:coordinates>2.9,41.5</gml:coordinates></i></gml:featureMember></r>')
        self.assertEqual(roads.parse_sct(gml)[0], [])

    def test_exposicion_cuenta_km_sobre_la_cota(self):
        d = doc_stub()
        e = roads.exposicion(d["carreteras"], {"das": {"lat": 42.38, "lon": 1.866, "cota": 1000}}, cpi_ref=3.0)
        self.assertEqual(e["carreteras"]["c16"]["km_sobre_cota"], 7.0)
        self.assertEqual(e["carreteras"]["c16"]["tramos_cubeta_km"], [[0.0, 7.0]])


if __name__ == "__main__":
    unittest.main()
