"""Tiempo real de Météo-France (DPObs): sin clave ≠ 0, clave en cabecera, unidades, día completo o nada."""
import io
import json
import sys
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import mf_rt  # noqa: E402

UTC = timezone.utc
NOW = datetime(2026, 11, 11, 17, 20, tzinfo=UTC)
SECRET = "TEST-KEY-NOT-REAL"


def row(sid, t, temp_k=275.15, rr=0.4, ff=5.0, fxi=12.0, u=80, pres=84000):
    return {"geo_id_insee": sid, "validity_time": t.strftime("%Y-%m-%dT%H:%M:%SZ"), "t": temp_k, "u": u,
            "ff": ff, "fxi": fxi, "rr1": rr, "pres": pres}


def day_rows(sid, last=datetime(2026, 11, 11, 17, tzinfo=UTC), skip=None):
    """Horas desde la medianoche UTC (tz=UTC en los tests) hasta `last`."""
    out, t = [], last.replace(hour=1)
    while t <= last:
        if t != skip:
            out.append(row(sid, t))
        t += timedelta(hours=1)
    return out


class Records(unittest.TestCase):
    def test_geojson_and_list(self):
        geo = {"type": "FeatureCollection", "features": [
            {"geometry": {"coordinates": [2.11, 42.61]}, "properties": {"geo_id_insee": "66082004", "t": 280}}]}
        r = mf_rt.records(json.dumps(geo).encode())
        self.assertEqual((r[0]["lat"], r[0]["lon"]), (42.61, 2.11))
        self.assertEqual(len(mf_rt.records([{"a": 1}, "x"])), 1)


class StationObs(unittest.TestCase):
    def test_units_and_full_day(self):
        o = mf_rt.station_obs("66082004", day_rows("66082004"), NOW, UTC)
        self.assertEqual(o["red"], "Météo-France")
        self.assertEqual(o["T"], 2.0)
        self.assertEqual((o["viento"], o["P"], o["HR"]), (18, 840.0, 80))
        self.assertEqual(o["edad_min"], 20)
        self.assertAlmostEqual(o["lluvia_dia"], 6.8)          # 17 horas × 0,4
        self.assertEqual(o["racha_dia"], 43)

    def test_missing_hour_gives_unknown_not_zero(self):
        o = mf_rt.station_obs("66082004", day_rows("66082004", skip=datetime(2026, 11, 11, 9, tzinfo=UTC)), NOW, UTC)
        self.assertIsNone(o["lluvia_dia"])
        self.assertIsNone(o["racha_dia"])
        self.assertEqual(o["T"], 2.0)                          # la última hora sigue siendo válida

    def test_missing_rain_value_is_unknown(self):
        rows = day_rows("66082004")
        rows[3]["rr1"] = None
        self.assertIsNone(mf_rt.station_obs("66082004", rows, NOW, UTC)["lluvia_dia"])

    def test_no_temperature_no_row(self):
        self.assertIsNone(mf_rt.station_obs("66082004", [row("66082004", NOW, temp_k=None)], NOW, UTC))


def http_error(code):
    return urllib.error.HTTPError("u", code, "x", {}, io.BytesIO(b""))


class Fetch(unittest.TestCase):
    def test_without_key_is_permission_error(self):
        with self.assertRaises(PermissionError):
            mf_rt.fetch(NOW, key="", get=lambda u, h: b"[]")

    def test_key_goes_in_header_never_in_url(self):
        seen = []
        def get(url, headers):
            seen.append((url, headers))
            dept = url.split("id-departement=")[1][:2]
            return json.dumps(day_rows("66082004") if dept == "66" else day_rows("09024004")).encode()
        obs = mf_rt.fetch(NOW, key=SECRET, get=get)
        self.assertEqual({o["id"] for o in obs}, {"66082004", "09024004"})
        self.assertTrue(all(h["apikey"] == SECRET and SECRET not in u for u, h in seen))
        self.assertEqual(len(seen), 2)                         # un paquete por departamento

    def test_rejected_key_is_reported_as_such(self):
        def get(url, headers):
            raise http_error(401)
        with self.assertRaises(mf_rt.KeyRejected) as cm:
            mf_rt.fetch(NOW, key=SECRET, get=get)
        self.assertNotIn(SECRET, str(cm.exception))
        self.assertEqual({m for m, _, _ in cm.exception.intentos}, {"apikey", "bearer"})

    def test_oauth_token_is_accepted_as_bearer(self):
        def get(url, headers):
            if headers.get("Authorization") != "Bearer " + SECRET:
                raise http_error(401)
            return json.dumps(day_rows("66082004") if "=66" in url else day_rows("09024004")).encode()
        obs = mf_rt.fetch(NOW, key=SECRET, get=get)
        self.assertEqual(len(obs), 2)
        self.assertEqual(mf_rt.fetch.last_auth, "bearer")

    def test_application_id_is_exchanged_for_a_token(self):
        import base64
        app_id = base64.b64encode(b"client:secret").decode()
        def get(url, headers):
            if headers.get("Authorization") != "Bearer TOKEN":
                raise http_error(401)
            return json.dumps(day_rows("66082004") if "=66" in url else day_rows("09024004")).encode()
        mf_rt.fetch(NOW, key=app_id, get=get, token=lambda a: "TOKEN")
        self.assertEqual(mf_rt.fetch.last_auth, "application_id")

    def test_package_403_tries_station_endpoint_before_blaming_the_key(self):
        def get(url, headers):
            if "paquet" in url:
                raise http_error(403)
            sid = url.split("id_station=")[1][:8]
            return json.dumps([row(sid, datetime(2026, 11, 11, 17, tzinfo=UTC))]).encode()
        obs = mf_rt.fetch(NOW, key=SECRET, get=get)
        self.assertEqual(len(obs), len(mf_rt.STATIONS))
        self.assertEqual(mf_rt.fetch.last_auth, "apikey")

    def test_package_failure_falls_back_to_station_endpoint(self):
        def get(url, headers):
            if "paquet" in url:
                raise http_error(500)
            sid = url.split("id_station=")[1][:8]
            return json.dumps([row(sid, datetime(2026, 11, 11, 17, tzinfo=UTC))]).encode()
        obs = mf_rt.fetch(NOW, key=SECRET, get=get)
        self.assertEqual(len(obs), len(mf_rt.STATIONS))
        self.assertTrue(all(o["lluvia_dia"] is None for o in obs))   # una hora suelta no es un día

    def test_nothing_usable_raises(self):
        with self.assertRaises(RuntimeError):
            mf_rt.fetch(NOW, key=SECRET, get=lambda u, h: b"[]")

    def test_foreign_stations_are_ignored(self):
        get = lambda u, h: json.dumps([row("75114001", datetime(2026, 11, 11, 17, tzinfo=UTC))]).encode()
        with self.assertRaises(RuntimeError):
            mf_rt.fetch(NOW, key=SECRET, get=get)


if __name__ == "__main__":
    unittest.main()
