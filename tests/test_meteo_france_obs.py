"""Official DPObs connector: local synthetic response, no live bearer token."""
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import meteo_france_obs as mf

UTC=timezone.utc
NOW=datetime(2026,11,11,16,0,tzinfo=UTC)
STA={"id":"66001001","nombre":"Les Angles test","lat":42.57,"lon":2.07,"alt":1640}

class MFranceObservations(unittest.TestCase):
    def test_catalog_preserves_leading_zero_and_limits_scope(self):
        csv_text=("Id_station;Nom_usuel;Latitude;Longitude;Altitude\n"
                  "66001001;LES ANGLES;42.57;2.07;1640\n"
                  "09002002;AX;42.72;1.84;680\n"
                  "75001001;PARIS;48.8;2.3;35\n"
                  "123;FAKE;42.5;2.0;1000\n")
        stations=mf.station_catalog(csv_text)
        self.assertEqual({s["id"] for s in stations},{"66001001","09002002"})
        self.assertEqual(stations[0]["lat"],42.57)

    def test_geojson_conversions_and_nulls(self):
        data=[{"type":"Feature","geometry":{"coordinates":[2.07,42.57]},
               "properties":{"geo_id_insee":"66001001","validity_time":"2026-11-11T15:00:00Z",
                             "t":270.15,"u":88,"ff":5,"fxi10":14,"rr1":0,
                             "sss":0.12,"pres":83500}}]
        x=mf.measurement(data,STA,NOW)
        self.assertEqual(x["red"],"Météo-France API")
        self.assertAlmostEqual(x["T"],-3)
        self.assertEqual(x["viento"],18)
        self.assertEqual(x["racha_inst"],50.4)
        self.assertIsNone(x["racha_dia"])
        self.assertIsNone(x["lluvia_dia"])
        self.assertEqual(x["prec_1h"],0)
        self.assertEqual(x["nieve_cm"],12)
        self.assertEqual(x["P"],835)
        self.assertEqual(x["instrument_qc"],"UNKNOWN")
        self.assertNotIn("token",str(x).lower())

    def test_stale_future_unzoned_and_mismatched_unknown(self):
        def row(t,id="66001001"):
            return [{"properties":{"geo_id_insee":id,"validity_time":t,"t":273.15}}]
        self.assertIsNone(mf.measurement(row("2026-11-11T13:00:00Z"),STA,NOW))
        self.assertIsNone(mf.measurement(row("2026-11-11T16:30:00Z"),STA,NOW))
        self.assertIsNone(mf.measurement(row("2026-11-11T15:00:00"),STA,NOW))
        self.assertIsNone(mf.measurement(row("2026-11-11T15:00:00Z","66001002"),STA,NOW))

    def test_missing_secret_fails_before_http(self):
        with mock.patch.dict("os.environ",{},clear=True):
            with mock.patch.object(mf.pd,"http_get") as request:
                with self.assertRaises(PermissionError):mf.fetch_observations(NOW)
                request.assert_not_called()

    def test_fail_closed_no_station_and_single_network_family(self):
        with mock.patch.dict("os.environ",{"METEOFRANCE_API_KEY":"TEST-ONLY"}):
            with mock.patch.object(mf,"_request",return_value="Id_station;nom;latitude;longitude\n") as request:
                with self.assertRaises(ValueError):mf.fetch_observations(NOW)
                self.assertEqual(request.call_count,1)

if __name__=="__main__":
    unittest.main()
