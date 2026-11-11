"""Regression of the unified routing, export contract and deployment staging."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import http.client
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
import nowcast
import portinatx_degen as coastal
import pirineo as mountain

spec = importlib.util.spec_from_file_location("site_builder", ROOT / "scripts" / "build_site.py")
site_builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(site_builder)


class Integration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.p_home, self.m_home = self.root / "portinatx", self.root / "pirineo"
        self.p_home.mkdir(); self.m_home.mkdir()
        self.patch_coast = patch.object(coastal, "HOME", self.p_home)
        self.patch_mtn = patch.object(mountain, "HOME", self.m_home)
        self.patch_coast.start(); self.patch_mtn.start()
        self.addCleanup(self.patch_coast.stop); self.addCleanup(self.patch_mtn.stop)

    def seed(self, issue=None):
        t = issue or datetime.now(timezone.utc).isoformat()
        for domain, home, names in (("portinatx", self.p_home, site_builder.PORT),
                                    ("pirineo", self.m_home, site_builder.PIR)):
            d = home / "app"; d.mkdir(parents=True, exist_ok=True)
            for name in names:
                (d / f"{name}.json").write_text(json.dumps({"issued": t, "domain": domain, "part": name}))

    def test_domain_paths_are_isolated(self):
        self.seed()
        self.assertEqual(json.loads(nowcast.read_data("portinatx", "core"))["domain"], "portinatx")
        self.assertEqual(json.loads(nowcast.read_data("pirineo", "core"))["domain"], "pirineo")
        with self.assertRaises(KeyError): nowcast.read_data("portinatx", "extended")
        with self.assertRaises(KeyError): nowcast.read_data("pirineo", "mar")
        for forbidden in ("../../config.env", "../state", "core.json/../../state", "state"):
            with self.assertRaises(KeyError): nowcast.read_data("portinatx", forbidden)

    def test_status_does_not_invent_missing_data(self):
        self.assertFalse(nowcast.status("portinatx")["ready"])
        self.assertEqual(nowcast.status("pirineo")["data_state"], "INCOMPLETE")
        self.seed()
        self.assertTrue(nowcast.status("pirineo")["ready"])

    def test_site_has_two_domains_and_manifest(self):
        self.seed()
        target = self.root / "site"
        report = site_builder.build_site(self.p_home, self.m_home, target)
        self.assertEqual(set(report), {"portinatx", "pirineo"})
        self.assertTrue((target / "portinatx" / "api" / "mar.json").exists())
        self.assertTrue((target / "pirineo" / "api" / "extended.json").exists())
        self.assertTrue((target / "pirineo" / "ruta" / "index.html").is_file())
        self.assertTrue((target / "pirineo" / "ruta" / "route_engine.js").is_file())
        self.assertTrue((target / "pirineo" / "pirineo_observatory.js").is_file())
        self.assertFalse((target / "portinatx" / "ruta").exists())
        self.assertTrue((target / "index.html").is_file())
        self.assertTrue((target / "decidir" / "index.html").is_file())
        self.assertTrue((target / "decision_cards.js").is_file())
        self.assertTrue((target / "device_sensors.js").is_file())
        self.assertTrue((target / "dispositivo" / "index.html").is_file())
        self.assertEqual(json.loads((target / "manifest.json").read_text())["release"], "0.6.0")
        self.assertFalse((target / "portinatx" / "api" / "extended.json").exists())
        self.assertFalse((target / "pirineo" / "api" / "mar.json").exists())
        self.assertNotIn("SECRET", "".join(str(p) for p in target.rglob("*")))

    def test_pages_backend_configuration_is_public_and_validated(self):
        self.seed()
        with patch.dict("os.environ", {"METEO_BACKEND_URL": "https://meteo-backend.example"}):
            target = self.root / "site-live"
            site_builder.build_site(self.p_home, self.m_home, target)
        self.assertIn("https://meteo-backend.example", (target / "public_config.js").read_text())
        self.assertTrue((target / "public_fetch.js").is_file())
        self.assertIn("public_fetch.js", (target / "pirineo" / "index.html").read_text())
        self.assertIn("public_fetch.js", (target / "portinatx" / "index.html").read_text())
        with patch.dict("os.environ", {"METEO_BACKEND_URL": "https://x.example;alert(1)"}):
            with self.assertRaisesRegex(ValueError, "HTTPS origin"):
                site_builder.build_site(self.p_home, self.m_home, self.root / "site-bad")

    def test_no_partial_publish_if_second_domain_invalid(self):
        self.seed()
        target = self.root / "site"
        target.mkdir()
        (target / "sentinel").write_text("original")
        (self.m_home / "app" / "dem.json").unlink()
        with self.assertRaisesRegex(ValueError, "Falta"):
            site_builder.build_site(self.p_home, self.m_home, target)
        self.assertEqual((target / "sentinel").read_text(), "original")

    def test_reject_stale_core(self):
        self.seed((datetime.now(timezone.utc) - timedelta(hours=36)).isoformat())
        with self.assertRaisesRegex(ValueError, "caducados"):
            site_builder.build_site(self.p_home, self.m_home, self.root / "site")

    def test_reject_future_time_and_malformed_json(self):
        self.seed((datetime.now(timezone.utc) + timedelta(hours=2)).isoformat())
        with self.assertRaisesRegex(ValueError, "futuros"):
            site_builder.build_site(self.p_home, self.m_home, self.root / "site")
        self.seed()
        (self.p_home / "app" / "mar.json").write_text("not-json")
        with self.assertRaises(json.JSONDecodeError):
            site_builder.build_site(self.p_home, self.m_home, self.root / "site")

    def test_export_dispatch_and_fault_isolation(self):
        with patch.object(coastal, "load_config_env"), patch.object(coastal, "load_state", return_value={}), \
             patch.object(coastal, "cycle", return_value={"issued_utc": "2026-11-10T00:00:00+00:00"}), \
             patch.object(coastal, "persist"), patch.object(coastal, "build_app", return_value={"core":{}}), \
             patch.object(coastal, "write_app", return_value=self.p_home / "app"):
            ret = nowcast.export("portinatx")
        self.assertEqual(ret["domain"], "portinatx")
        with patch.object(mountain, "build", side_effect=TimeoutError("no API")):
            with self.assertRaises(TimeoutError): nowcast.export("pirineo")
        with self.assertRaises(ValueError): nowcast.export("other")

    def test_pirineo_config_env_does_not_override_real_environment(self):
        f = self.m_home / "config.env"
        f.write_text("NOWCAST_TEST_KEY=fromfile\n# ALLOWED=bad\n")
        with patch.dict("os.environ", {"NOWCAST_TEST_KEY": "real"}):
            nowcast.load_mountain_config()
            self.assertEqual(__import__("os").environ["NOWCAST_TEST_KEY"], "real")

    def test_local_routes_and_refresh_security(self):
        self.seed()
        workers = {d: nowcast.Collector(d, 3600) for d in nowcast.DOMAINS}
        from http.server import ThreadingHTTPServer
        srv = ThreadingHTTPServer(("127.0.0.1", 0), nowcast.server_handler(workers))
        port = srv.server_port
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        conn = http.client.HTTPConnection("localhost", port, timeout=4)
        self.addCleanup(conn.close)
        conn.request("GET", "/dispositivo/")
        r = conn.getresponse()
        self.assertEqual(r.status, 200)
        self.assertIn(b"device_sensors.js", r.read())
        conn.request("GET", "/device_sensors.js")
        r = conn.getresponse()
        self.assertEqual(r.status, 200)
        r.read()
        conn.request("GET", "/decidir/")
        r = conn.getresponse(); self.assertEqual(r.status, 200)
        self.assertIn(b"decision_cards.js", r.read())
        conn.request("GET", "/decision_cards.js")
        r = conn.getresponse(); self.assertEqual(r.status, 200)
        self.assertIn(b"MeteoDecision", r.read())
        conn.request("GET", "/public_fetch.js")
        r = conn.getresponse(); self.assertEqual(r.status, 200)
        self.assertIn(b"meteoLoadDomain", r.read())
        conn.request("GET", "/public_config.js")
        r = conn.getresponse(); self.assertEqual(r.status, 200)
        self.assertIn(b"METEO_BACKEND_URL", r.read())
        conn.request("GET", "/portinatx/api/core.json")
        r = conn.getresponse()
        self.assertEqual(r.status, 200)
        self.assertEqual(json.loads(r.read())["domain"], "portinatx")
        conn.request("GET", "/pirineo/ruta/")
        r = conn.getresponse(); self.assertEqual(r.status, 200); self.assertIn(b"Ruta y tiempo", r.read())
        conn.request("GET", "/pirineo/ruta/route_engine.js")
        r = conn.getresponse(); self.assertEqual(r.status, 200); self.assertIn(b"RouteEngine", r.read())
        conn.request("GET", "/pirineo/api/status")
        r = conn.getresponse(); self.assertEqual(r.status, 200); r.read()
        conn.request("GET", "/portinatx/api/config.env")
        r = conn.getresponse(); self.assertEqual(r.status, 404); r.read()
        conn.request("POST", "/portinatx/api/refresh", headers={"Host":f"localhost:{port}","Origin":"https://evil.example"})
        r = conn.getresponse(); self.assertEqual(r.status, 403); r.read()
        conn.request("POST", "/pirineo/api/refresh", headers={"Host":f"localhost:{port}","Origin":f"http://localhost:{port}"})
        r = conn.getresponse(); self.assertEqual(r.status, 202); r.read()
        self.assertTrue(workers["pirineo"].wake.is_set())
        self.assertFalse(workers["portinatx"].wake.is_set())

    def test_html_navigation_and_both_reports(self):
        for name in ("nowcast_hub.html", "portinatx_app.html", "pirineo_app.html"):
            self.assertGreater(len(nowcast.page_for("/" if name=="nowcast_hub.html" else "/"+name.split("_")[0]+"/")), 200)
        self.assertIn('href="../"', (SRC / "pirineo_app.html").read_text())
        self.assertIn('href="../"', (SRC / "portinatx_app.html").read_text())
        self.assertIn("api/refresh", (SRC / "pirineo_app.html").read_text())
        self.assertIn("decidir/", (SRC / "nowcast_hub.html").read_text())


if __name__ == "__main__":
    unittest.main()
