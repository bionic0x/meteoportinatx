#!/usr/bin/env python3
"""Persistent, read-only public API + two meteorological collectors.

One process, one durable volume, stdlib only. The legacy engines and their
private forensic histories remain untouched; only explicitly projected JSON
is ever served. No public refresh endpoint exists.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import gzip
import hashlib
import json
import os
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import nowcast

VERSION = "0.5.0"
DOMAINS = nowcast.DOMAINS
PARTS = nowcast.PARTS
DEFAULT_INTERVALS = {"portinatx": 300, "pirineo": 10800}
AGE_HOURS = {"portinatx": 1, "pirineo": 6}
UTC = timezone.utc
CORS_ORIGINS = frozenset(("https://bionic0x.github.io", "http://localhost:8789", "http://127.0.0.1:8789"))
SAFE_DOMAIN = re.compile(r"^(portinatx|pirineo)$")
SAFE_PART = re.compile(r"^[a-z][a-z0-9_]{0,35}$")


def iso_utc(dt=None):
    return (dt or datetime.now(UTC)).astimezone(UTC).isoformat()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_atomic(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".part-", delete=False) as f:
        tmp = Path(f.name)
        try:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
    try:
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def _utc_issue(stamp):
    if not isinstance(stamp, str):
        raise ValueError("issued timestamp missing")
    dt = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("issued timestamp is timezone-naive")
    dt = dt.astimezone(UTC)
    if not (-300 <= (datetime.now(UTC) - dt).total_seconds() <= 3600):
        raise ValueError("issued timestamp outside a valid collection window")
    return dt


def _public_view(domain: str, part: str, original: dict) -> dict:
    """Drop owner-authored governance and local private evidence, by design.

    This is a projection, NOT a raw file server and NOT an approval of the
    original diagnostic output as an official warning.
    """
    if domain == "portinatx" and part == "core":
        result = dict(original)
        gov = result.get("governance") or {}
        result["governance"] = {
            "claims": [], "claims_count": {}, "predictions": [],
            "predictions_summary": {}, "anomalies": [], "dissent": [], "overrides": {},
            "bias": gov.get("bias"),
            "episode": {"phase": (gov.get("episode") or {}).get("phase", "UNKNOWN")},
        }
        # Preserve dashboard schema but remove owner-written narratives from
        # decisions, channel evidence, and forecasts. Public warnings remain
        # institutional; no owner testimony is included in the public API.
        precaution = original.get("precaution") or {}
        result["precaution"] = {
            "level": precaution.get("level", "unknown"),
            "transition": precaution.get("transition", ""),
            "decision": {}, "exit_conditions": [],
        }
        nowcast = original.get("nowcast") or {}
        result["nowcast"] = {k: nowcast.get(k) for k in ("level", "proposed", "transition")}
        result["outlook"] = {k: (original.get("outlook") or {}).get(k) for k in ("level", "proposed", "transition")}
        result["outlook"]["reasons"] = []
        hazard = original.get("hazard") or {}
        result["hazard"] = {k: {"estado": "UNKNOWN", "nivel": "unknown"}
                            if k in ("runoff", "flooding") else
                            {q: v.get(q) for q in ("estado", "nivel", "local")}
                            for k, v in hazard.items() if isinstance(v, dict)}
        result["channels"] = [
            {**{k: c.get(k) for k in ("name", "level", "kind", "confidence", "available", "local")},
             "evidence": []}
            for c in (original.get("channels") or []) if isinstance(c, dict)]
        result["history"] = [
            {k: v.get(k) for k in ("id", "level", "nowcast")}
            for v in (original.get("history") or []) if isinstance(v, dict)]
        result["sources"] = [
            {"name": s.get("name"), "status": s.get("status"), "data_time": s.get("data_time"), "detail": ""}
            for s in (original.get("sources") or []) if isinstance(s, dict)]
        return result
    if domain == "portinatx" and part == "forense":
        # Published forensic aggregates only, never source rows or user notes.
        return {k: v for k, v in original.items() if k in ("status", "corregido", "modelos", "info", "aprendizaje", "puntuacion", "lecciones", "dias", "nucleo", "desfase", "oleaje", "historial_aprendizaje", "pares_cols", "resumen", "n_dias")}
    return original


class Store:
    """SQLite audit/chain plus immutable, atomic public projection snapshots."""
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.public = self.root / "public"
        self.public.mkdir(exist_ok=True)
        self.db = self.root / "forensics.sqlite3"
        self._write_lock = threading.RLock()
        self._init_db()

    def _connect(self):
        c = sqlite3.connect(self.db, timeout=30)
        c.execute("PRAGMA busy_timeout=30000")
        return c

    @contextmanager
    def _db(self):
        db = self._connect()
        try:
            with db:
                yield db
        finally:
            db.close()

    def _init_db(self):
        with self._db() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
            CREATE TABLE IF NOT EXISTS cycles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL CHECK(domain IN ('portinatx','pirineo')),
                issued TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                previous_chain TEXT NOT NULL,
                chain_sha256 TEXT NOT NULL,
                source_count INTEGER NOT NULL,
                status TEXT NOT NULL,
                UNIQUE(domain, issued)
            );
            CREATE TABLE IF NOT EXISTS failures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                reason TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS cycles_domain_time ON cycles(domain,id DESC);
            """)

    def failure(self, domain, reason):
        with self._db() as db:
            db.execute("INSERT INTO failures(domain,recorded_at,reason) VALUES(?,?,?)",
                       (domain, iso_utc(), str(reason)[:120]))

    def publish(self, domain: str, app_path: Path):
        if domain not in DOMAINS:
            raise ValueError("unknown domain")
        app_path = Path(app_path)
        parsed = {}
        for part in PARTS[domain]:
            file = app_path / f"{part}.json"
            payload = json.loads(file.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError(f"invalid JSON object: {part}")
            parsed[part] = payload
        issued = parsed["core"].get("issued")
        _utc_issue(issued)
        if domain == "portinatx":
            usable = sum(x.get("status") == "ok" for x in parsed["core"].get("sources", []) if isinstance(x, dict))
            if not usable:
                raise ValueError("no fresh, usable coastal source")
        else:
            usable = len(parsed["core"].get("puntos", []))
            if not usable:
                raise ValueError("no valid mountain point forecasts")
        projected = {part: json.dumps(_public_view(domain, part, parsed[part]), ensure_ascii=False,
                                      separators=(",", ":"), allow_nan=False).encode("utf-8")
                     for part in PARTS[domain]}
        core_hash = _sha(projected["core"])
        # Keep complete private mountain forecasts immutable for honest replay;
        # coastline already persists its full frozen cycles independently.
        if domain == "pirineo":
            payload = {p: parsed[p] for p in ("core", "series", "extended")}
            raw = gzip.compress(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
                                mtime=0)
            stamp = _utc_issue(issued).strftime("%Y%m%dT%H%M%SZ")
            _write_atomic(self.root / "private_history" / "pirineo" / (stamp + "-" + _sha(raw)[:12] + ".json.gz"), raw)
        with self._write_lock:
            # Unique numbered immutable generations; readers use CURRENT pointer.
            # No transient half-written JSON can leak through the public API.
            domain_root = self.public / domain
            domain_root.mkdir(exist_ok=True)
            version = _utc_issue(issued).strftime("%Y%m%dT%H%M%SZ") + "-" + core_hash[:12]
            tmp = Path(tempfile.mkdtemp(prefix=".staging-", dir=domain_root))
            destination = domain_root / version
            try:
                for name, payload in projected.items():
                    (tmp / f"{name}.json").write_bytes(payload)
                if not destination.exists():
                    tmp.replace(destination)
                else:
                    shutil.rmtree(tmp)
            finally:
                if tmp.exists():
                    shutil.rmtree(tmp)
            with self._db() as db:
                db.execute("BEGIN IMMEDIATE")
                prev = db.execute("SELECT chain_sha256 FROM cycles WHERE domain=? ORDER BY id DESC LIMIT 1", (domain,)).fetchone()
                chain_prev = prev[0] if prev else "0" * 64
                chain = _sha((chain_prev + "\n" + domain + "\n" + issued + "\n" + core_hash).encode())
                db.execute("INSERT OR IGNORE INTO cycles(domain,issued,recorded_at,sha256,previous_chain,chain_sha256,source_count,status) "
                           "VALUES(?,?,?,?,?,?,?,?)", (domain,issued,iso_utc(),core_hash,chain_prev,chain,usable,"PUBLISHED"))
            _write_atomic(domain_root / "CURRENT.json", json.dumps({"version":version,"issued":issued,"sha256":core_hash},separators=(",", ":")).encode())
            versions = sorted((p for p in domain_root.iterdir() if p.is_dir() and not p.name.startswith(".")),reverse=True)
            for stale in versions[12:]:
                shutil.rmtree(stale)
        return {"domain": domain, "issued": issued, "sha256": core_hash, "source_count": usable}

    def read_public(self, domain: str, part: str):
        if domain not in DOMAINS or part not in PARTS[domain] or not SAFE_PART.fullmatch(part):
            raise KeyError("invalid domain or part")
        pointer = json.loads((self.public / domain / "CURRENT.json").read_text())
        version = pointer["version"]
        if not re.fullmatch(r"\d{8}T\d{6}Z-[a-f0-9]{12}", version):
            raise ValueError("invalid snapshot reference")
        raw = (self.public / domain / version / (part + ".json")).read_bytes()
        age = (datetime.now(UTC) - datetime.fromisoformat(pointer["issued"].replace("Z", "+00:00"))).total_seconds() / 3600
        return raw, ("fresh" if -0.1 <= age <= AGE_HOURS[domain] else "stale"), pointer

    def summary(self, domain: str | None = None):
        with self._db() as db:
            if domain:
                rows = db.execute("SELECT domain,issued,sha256,chain_sha256,source_count FROM cycles WHERE domain=? ORDER BY id DESC LIMIT 24", (domain,)).fetchall()
                counts = db.execute("SELECT COUNT(*) FROM failures WHERE domain=?",(domain,)).fetchone()[0]
            else:
                rows = db.execute("SELECT domain,issued,sha256,chain_sha256,source_count FROM cycles ORDER BY id DESC LIMIT 24").fetchall()
                counts = db.execute("SELECT COUNT(*) FROM failures").fetchone()[0]
        return {"schema":1,"cycle_count_in_window":len(rows),"failures_total":counts,
                "cycles":[{"domain":x[0],"issued":x[1],"sha256":x[2],"chain_sha256":x[3],"source_count":x[4]} for x in rows],
                "note":"Metadata only; no archived measurements, manual interventions or private evidence are exposed"}


class Service:
    def __init__(self, root: Path, *, runner=None, intervals=None):
        self.store = Store(root)
        self.runner = runner or self._runner
        self.intervals = {**DEFAULT_INTERVALS, **(intervals or {})}
        self.state = {d:{"running":False,"last_error":None,"last_success":None,"last_attempt":None} for d in DOMAINS}
        self.lock = threading.RLock()
        self.stop = threading.Event()

    def _runner(self, domain):
        cmd = [sys.executable,"-u",str(Path(__file__).with_name("nowcast.py")),"export","--domain",domain]
        timeout = 245 if domain == "portinatx" else 1800
        result = subprocess.run(cmd,capture_output=True,text=True,timeout=timeout,check=False)
        if result.returncode != 0:
            raise RuntimeError(f"collector_exit_{result.returncode}")
        return Path(os.environ["PORTINATX_HOME"] if domain=="portinatx" else os.environ["PIRINEO_HOME"]) / "app"

    def collect_once(self, domain):
        if domain not in DOMAINS:
            raise ValueError("unknown domain")
        with self.lock:
            if self.state[domain]["running"]:
                raise RuntimeError("collection already running")
            self.state[domain]["running"] = True
            self.state[domain]["last_attempt"] = iso_utc()
        try:
            app = self.runner(domain)
            published = self.store.publish(domain, app)
            with self.lock:
                self.state[domain]["last_success"] = published["issued"]
                self.state[domain]["last_error"] = None
            return published
        except Exception as exc:
            # API exposes only class, never exception text (URLs may carry keys).
            kind = type(exc).__name__
            self.store.failure(domain,kind)
            with self.lock:
                self.state[domain]["last_error"] = kind
            raise
        finally:
            with self.lock:
                self.state[domain]["running"] = False

    def loop(self, domain):
        while not self.stop.is_set():
            began = time.monotonic()
            try:
                self.collect_once(domain)
            except Exception as exc:
                print(f"collector {domain}: {type(exc).__name__}",file=sys.stderr,flush=True)
            # Start-to-start cadence, without overlap; long cycles catch up
            # only after a short backoff to prevent provider hammering.
            self.stop.wait(max(10, self.intervals[domain] - (time.monotonic() - began)))

    def start(self):
        for d in DOMAINS:
            threading.Thread(target=self.loop,args=(d,),daemon=True,name="collector-"+d).start()

    def status(self):
        with self.lock:
            states = json.loads(json.dumps(self.state))
        for d in DOMAINS:
            try:
                _, freshness, ptr = self.store.read_public(d, "core")
                states[d].update({"data_state":freshness.upper(),"issued":ptr["issued"],"sha256":ptr["sha256"],
                                  "interval_seconds":self.intervals[d]})
            except (OSError,ValueError,KeyError):
                states[d].update({"data_state":"UNKNOWN","issued":None,
                                  "interval_seconds":self.intervals[d]})
        return {"version":VERSION,"mode":"persistent-backend","domains":states}


def handler(service: Service, allowed_origins=CORS_ORIGINS):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            # Do not log raw request query strings or user IPs.
            pass

        def _send(self, code, data, mime="application/json; charset=utf-8", freshness=None):
            self.send_response(code)
            self.send_header("Content-Type",mime)
            self.send_header("Content-Length",str(len(data)))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("X-Frame-Options","DENY")
            self.send_header("Referrer-Policy","no-referrer")
            origin = self.headers.get("Origin")
            if origin in allowed_origins:
                self.send_header("Access-Control-Allow-Origin",origin)
                self.send_header("Vary","Origin")
            if freshness:
                self.send_header("X-Meteo-Freshness",freshness)
            self.end_headers()
            self.wfile.write(data)

        def _json(self, code, obj, **kwargs):
            self._send(code,json.dumps(obj,ensure_ascii=False,separators=(",", ":")).encode(),**kwargs)

        def do_GET(self):
            path=urlsplit(self.path).path
            if path=="/healthz":
                return self._json(200,{"status":"ok","version":VERSION})
            if path=="/v1/status":
                return self._json(200,service.status())
            if path=="/v1/forensics/summary":
                return self._json(200,service.store.summary())
            m=re.fullmatch(r"/v1/(portinatx|pirineo)/api/([a-z][a-z0-9_]{0,35})\.json",path)
            if m:
                domain,part=m.groups()
                if part not in PARTS[domain]:
                    return self._json(404,{"error":"not_found"})
                try:
                    data,fresh,_=service.store.read_public(domain,part)
                    return self._send(200,data,freshness=fresh)
                except (OSError,KeyError,ValueError):
                    return self._json(503,{"state":"UNKNOWN","reason":"snapshot not available"})
            return self._json(404,{"error":"not_found"})

        def do_POST(self):
            return self._json(405,{"error":"public API is read-only"})

        def do_OPTIONS(self):
            # Cross-origin reads only; browsers never gain write authority.
            self.send_response(204)
            origin=self.headers.get("Origin")
            if origin in allowed_origins:
                self.send_header("Access-Control-Allow-Origin",origin)
                self.send_header("Access-Control-Allow-Methods","GET, OPTIONS")
                self.send_header("Access-Control-Allow-Headers","Accept, Content-Type")
                self.send_header("Vary","Origin")
            self.send_header("Content-Length","0")
            self.end_headers()
    return Handler


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("command",choices=("serve","once","status"),nargs="?",default="serve")
    parser.add_argument("--domain",choices=(*DOMAINS,"all"),default="all")
    parser.add_argument("--port",type=int,default=int(os.environ.get("PORT","10000")))
    parser.add_argument("--root",type=Path,default=Path(os.environ.get("NOWCAST_DATA_ROOT","./backend_state")))
    parser.add_argument("--no-workers",action="store_true")
    args=parser.parse_args(argv)
    root=args.root.resolve()
    os.environ.setdefault("PORTINATX_HOME",str(root/"portinatx"))
    os.environ.setdefault("PIRINEO_HOME",str(root/"portinatx"/"pirineo"))
    os.environ.setdefault("PIRINEO_EXTENDED","1")
    if os.environ.get("NOWCAST_REQUIRE_DISK")=="1" and not root.is_mount():
        raise SystemExit("persistent disk required: NOWCAST_DATA_ROOT is not a mount")
    service=Service(root,intervals={"portinatx":int(os.environ.get("PORTINATX_INTERVAL","300")),
                                    "pirineo":int(os.environ.get("PIRINEO_INTERVAL","10800"))})
    if args.command=="status":
        print(json.dumps(service.status(),indent=2));return 0
    if args.command=="once":
        targets=DOMAINS if args.domain=="all" else (args.domain,)
        failures=0
        for d in targets:
            try:
                print(json.dumps(service.collect_once(d)))
            except Exception as exc:
                failures+=1;print(f"FAILED {d}: {type(exc).__name__}",file=sys.stderr)
        return int(bool(failures))
    server=ThreadingHTTPServer(("0.0.0.0",args.port),handler(service))
    def shutdown(*_):
        service.stop.set()
        threading.Thread(target=server.shutdown,daemon=True).start()
    signal.signal(signal.SIGTERM,shutdown)
    signal.signal(signal.SIGINT,shutdown)
    if not args.no_workers:
        service.start()
    print(f"Meteo backend {VERSION} started on port {server.server_port}",flush=True)
    try:
        server.serve_forever(poll_interval=.5)
    finally:
        service.stop.set();server.server_close()
    return 0


if __name__=="__main__":
    raise SystemExit(main())
