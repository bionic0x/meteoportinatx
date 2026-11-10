"""Offline regression: persistent, read-only API, privacy, atomic published snapshots."""
import gzip
import http.client
import json
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import nowcast_backend as backend


class PersistentBackend(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = backend.Store(self.root / "durable")
        self.app = self.root / "app"
        self.app.mkdir()

    def fixture(self, domain, issued=None, owner="private observation next to my home"):
        issued = issued or backend.iso_utc()
        core = {"issued": issued, "sources": [{"name":"radar","status":"ok","data_time": issued,"detail":"SECRET_API_KEY=private"}],
                "official":{"verificado":False,"level_now":"unknown","all":[]},
                "hazard":{"runoff":{"estado":"OBSERVED","nivel":"alert","evidence":owner}},
                "precaution":{"level":"watch","transition":"UP","decision":{"overridden":[{"motivo":owner}]},"exit_conditions":[owner]},
                "nowcast":{"level":"watch","reasons":[owner]},
                "outlook":{"level":"watch","reasons":[owner]},
                "channels":[{"name":"manual","kind":"obs","level":2,"available":True,"local":True,"evidence":[owner]}],
                "history":[{"id":"NWC-20261018T120000Z","level":"watch","nowcast":"watch","evidence":owner}],
                "governance":{"dissent":[{"text":owner}],"overrides":{"D1":{"motivo":owner}},
                              "anomalies":[{"text":owner}],"predictions":[{"claim":owner}],
                              "claims":[{"source_root":"owner","text":owner}],"claims_count":{},"bias":{},
                              "episode":{"phase":"ACTIVE","private_notes":owner}}}
        if domain=="pirineo":
            core.update({"puntos":[{"id":"font_romeu","alt":1800}],"sources":[],"series":{}})
        for part in backend.PARTS[domain]:
            value = core if part=="core" else ({"secret":""} if part!="extended" else {"status":"UNKNOWN"})
            (self.app / (part + ".json")).write_text(json.dumps(value,ensure_ascii=False))
        return core

    def test_portinatx_public_projection_drops_owner_data_but_renders(self):
        self.fixture("portinatx")
        self.store.publish("portinatx",self.app)
        data, freshness, pointer=self.store.read_public("portinatx","core")
        public=json.loads(data)
        self.assertEqual(freshness,"fresh")
        self.assertEqual(public["governance"]["claims"],[])
        self.assertEqual(public["governance"]["dissent"],[])
        self.assertIn("channels",public)
        self.assertIn("hazard",public)
        self.assertIn("precaution",public)
        self.assertIn("history",public)
        self.assertNotIn("private observation",data.decode())
        self.assertNotIn("SECRET_API_KEY",data.decode())
        self.assertEqual(public["hazard"]["runoff"]["estado"],"UNKNOWN")
        self.assertEqual(public["precaution"]["level"],"watch")
        self.assertEqual(pointer["sha256"],backend._sha(data))

    def test_fail_closed_missing_part_keeps_previous_snapshot(self):
        self.fixture("pirineo")
        old=self.store.publish("pirineo",self.app)
        (self.app/"grid.json").unlink()
        with self.assertRaises(FileNotFoundError):
            self.store.publish("pirineo",self.app)
        _,_,ptr=self.store.read_public("pirineo","core")
        self.assertEqual(ptr["sha256"],old["sha256"])

    def test_bad_sourcedata_never_becomes_fake_calm(self):
        core=self.fixture("portinatx")
        core["sources"]=[]
        (self.app/"core.json").write_text(json.dumps(core))
        with self.assertRaisesRegex(ValueError,"no fresh"):
            self.store.publish("portinatx",self.app)
        with self.assertRaises(FileNotFoundError):
            self.store.read_public("portinatx","core")

    def test_timezone_naive_disallowed(self):
        self.fixture("pirineo",issued="2026-11-10T12:00:00")
        with self.assertRaisesRegex(ValueError,"timezone-naive"):
            self.store.publish("pirineo",self.app)

    def test_persistent_sqlite_and_hash_chain_on_restart(self):
        self.fixture("pirineo")
        a=self.store.publish("pirineo",self.app)
        v=json.loads((self.app/"core.json").read_text())
        v["issued"] = backend.iso_utc(datetime.now(timezone.utc))
        v["issued"] = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        (self.app/"core.json").write_text(json.dumps(v))
        b=self.store.publish("pirineo",self.app)
        reopened=backend.Store(self.root/"durable")
        history=reopened.summary("pirineo")
        self.assertEqual(history["cycle_count_in_window"],2)
        self.assertEqual(history["cycles"][0]["sha256"],b["sha256"])
        self.assertEqual(history["cycles"][1]["sha256"],a["sha256"])
        self.assertEqual(history["cycles"][0]["chain_sha256"], backend._sha((history["cycles"][1]["chain_sha256"]+"\npirineo\n"+b["issued"]+"\n"+b["sha256"]).encode()))
        hist=list((self.store.root/"private_history"/"pirineo").glob("*.gz"))
        self.assertEqual(len(hist),2)
        self.assertIn("extended",json.loads(gzip.decompress(hist[-1].read_bytes())))

    def test_no_public_archive_or_path_traversal(self):
        self.fixture("portinatx")
        self.store.publish("portinatx",self.app)
        with self.assertRaises(KeyError):
            self.store.read_public("portinatx","../config.env")
        with self.assertRaises(KeyError):
            self.store.read_public("unknown","core")
        self.assertFalse((self.store.public/"portinatx"/"private_history").exists())

    def test_http_read_only_cors_and_unavailable(self):
        self.fixture("portinatx")
        self.store.publish("portinatx",self.app)
        service=backend.Service(self.store.root,runner=lambda domain:self.app)
        server=ThreadingHTTPServer(("127.0.0.1",0),backend.handler(service))
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        self.addCleanup(lambda:(server.shutdown(),server.server_close(),thread.join(1)))
        def call(method,path,origin=None):
            conn=http.client.HTTPConnection("127.0.0.1",server.server_port,timeout=3)
            conn.request(method,path,headers={"Origin":origin} if origin else {})
            response=conn.getresponse()
            result=(response.status,dict(response.getheaders()),response.read())
            conn.close()
            return result
        status,headers,data=call("GET","/v1/portinatx/api/core.json","https://bionic0x.github.io")
        self.assertEqual(status,200)
        self.assertEqual(headers["Access-Control-Allow-Origin"],"https://bionic0x.github.io")
        self.assertEqual(headers["X-Meteo-Freshness"],"fresh")
        self.assertNotIn(b"private observation",data)
        status,headers,_=call("POST","/v1/portinatx/api/refresh","https://bionic0x.github.io")
        self.assertEqual(status,405)
        status,headers,_=call("GET","/v1/portinatx/api/core.json","https://untrusted.invalid")
        self.assertEqual(status,200)
        self.assertNotIn("Access-Control-Allow-Origin",headers)
        status,_,_=call("GET","/v1/portinatx/api/state.json")
        self.assertEqual(status,404)
        status,_,_=call("GET","/v1/pirineo/api/core.json")
        self.assertEqual(status,503)
        status,_,_=call("GET","/v1/forensics/summary")
        self.assertEqual(status,200)

    def test_failure_tracking_redacts_exception_strings(self):
        service=backend.Service(self.store.root,runner=lambda d:(_ for _ in ()).throw(RuntimeError("secret token")))
        with self.assertRaises(RuntimeError):
            service.collect_once("portinatx")
        self.assertEqual(service.status()["domains"]["portinatx"]["last_error"],"RuntimeError")
        self.assertEqual(service.store.summary("portinatx")["failures_total"],1)


if __name__=="__main__":
    unittest.main()
