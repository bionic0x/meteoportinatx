#!/usr/bin/env python3
"""MeteoPortinatx Unified — two domains, one CLI and one localhost server.

The weather engines remain separate: no Mediterranean flood threshold can
become a mountain snow alert. Only the meteorological utilities are reused.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import portinatx_degen as coastal
import pirineo as mountain

VERSION = "0.5.1"
DOMAINS = ("portinatx", "pirineo")
PARTS = {
    "portinatx": frozenset(("core", "radar", "series", "atmos", "sat", "mar", "modx", "forense")),
    "pirineo": frozenset(("core", "dem", "grid", "series", "extended")),
}
PAGES = {"/": "nowcast_hub.html", "/index.html": "nowcast_hub.html",
         "/portinatx/": "portinatx_app.html", "/portinatx/index.html": "portinatx_app.html",
         "/pirineo/": "pirineo_app.html", "/pirineo/index.html": "pirineo_app.html",
         "/decidir/": "decision_app.html", "/decidir/index.html": "decision_app.html"}


def home(domain: str) -> Path:
    return coastal.HOME if domain == "portinatx" else mountain.HOME


def load_mountain_config() -> None:
    """Same opt-in config semantics as pirineo.main; existing keys not overridden."""
    for f in (mountain.HOME / "config.env", coastal.HOME / "config.env"):
        if f.is_file():
            for line in f.read_text(encoding="utf-8").splitlines():
                k, eq, v = line.strip().partition("=")
                if eq and k and not k.startswith("#") and v.strip() and k not in os.environ:
                    os.environ[k] = v.strip()


def export(domain: str) -> dict:
    """Runs the existing engine once. No manufactured fair-weather values on failure."""
    if domain == "portinatx":
        coastal.load_config_env()
        state = coastal.load_state()
        snapshot = coastal.cycle(state)
        coastal.persist(snapshot, state)  # append-only evidence, unchanged safety gates
        output = coastal.write_app(coastal.build_app(snapshot, state))
        issued = snapshot.get("issued_utc")
    elif domain == "pirineo":
        load_mountain_config()
        parts = mountain.build()
        output = mountain.write(parts)
        issued = parts.get("core", {}).get("issued")
    else:
        raise ValueError(f"Unknown domain: {domain}")
    return {"domain": domain, "issued": issued, "dir": str(output)}


def read_data(domain: str, part: str) -> bytes:
    """Closed allowlist: no traversal, no credential or state-file access."""
    if domain not in PARTS or part not in PARTS[domain]:
        raise KeyError("Unknown domain or part")
    return (home(domain) / "app" / f"{part}.json").read_bytes()


def status(domain: str) -> dict:
    d = home(domain) / "app"
    parts = {p: (d / f"{p}.json").is_file() for p in sorted(PARTS[domain])}
    issued = None
    try:
        v = json.loads((d / "core.json").read_text(encoding="utf-8"))
        issued = v.get("issued")
    except (OSError, ValueError, TypeError):
        pass
    return {"domain": domain, "issued": issued, "parts": parts,
            "ready": all(parts.values()), "data_state": "AVAILABLE" if all(parts.values()) else "INCOMPLETE"}


def page_for(path: str) -> bytes:
    try:
        return coastal.resource_bytes(PAGES[path])
    except KeyError:
        raise KeyError("Unknown page") from None


class Collector:
    def __init__(self, domain: str, interval_s: int):
        self.domain = domain
        self.interval_s = interval_s
        self.wake = threading.Event()
        self.lock = threading.Lock()
        self.state = {"running": False, "last_end": None, "last_error": None,
                      "last_cycle": None, "next_at": None, "interval_s": interval_s}

    def snapshot(self) -> dict:
        with self.lock:
            return {"mode": "local", **self.state}

    def run_once(self):
        with self.lock:
            self.state["running"] = True
        try:
            result = export(self.domain)
            with self.lock:
                self.state["last_error"] = None
                self.state["last_cycle"] = result["issued"]
        except Exception as exc:
            with self.lock:
                self.state["last_error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
        finally:
            end = datetime.now(timezone.utc)
            with self.lock:
                self.state.update(running=False, last_end=end.isoformat(),
                                  next_at=datetime.fromtimestamp(end.timestamp() + self.interval_s, timezone.utc).isoformat())

    def run(self):
        while True:
            self.run_once()
            self.wake.wait(self.interval_s)
            self.wake.clear()


def server_handler(workers: dict[str, Collector]):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            print(f"[{self.log_date_time_string()}] {fmt % args}", file=sys.stderr)

        def send_bytes(self, code, data: bytes, mime: str):
            self.send_response(code)
            self.send_header("Content-Type", mime)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def json_reply(self, code, obj):
            return self.send_bytes(code, json.dumps(obj).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self):
            path = urlsplit(self.path).path
            if path in PAGES:
                try:
                    return self.send_bytes(200, page_for(path), "text/html; charset=utf-8")
                except (OSError, KeyError):
                    return self.send_error(404)
            if path == "/decision_cards.js":
                return self.send_bytes(200, coastal.resource_bytes("decision_cards.js"),
                                       "text/javascript; charset=utf-8")
            if path == "/public_fetch.js":
                return self.send_bytes(200, coastal.resource_bytes("public_fetch.js"),
                                       "text/javascript; charset=utf-8")
            if path == "/public_config.js":
                # Loopback is a local server, not a remote production backend.
                return self.send_bytes(200, b"window.METEO_BACKEND_URL=\"\";\n",
                                       "text/javascript; charset=utf-8")
            segments = path.strip("/").split("/")
            if len(segments) == 3 and segments[0] in DOMAINS and segments[1] == "api":
                domain = segments[0]
                if segments[2] == "status":
                    return self.json_reply(200, workers[domain].snapshot())
                if segments[2].endswith(".json"):
                    try:
                        return self.send_bytes(200, read_data(domain, segments[2][:-5]), "application/json; charset=utf-8")
                    except (OSError, KeyError):
                        return self.send_error(503 if segments[2][:-5] in PARTS[domain] else 404)
            return self.send_error(404)

        def do_POST(self):
            path = urlsplit(self.path).path
            segments = path.strip("/").split("/")
            if len(segments) != 3 or segments[0] not in DOMAINS or segments[1:] != ["api", "refresh"]:
                return self.send_error(404)
            # Browser-driven loopback only, no cross-origin refresh trigger.
            origin = self.headers.get("Origin")
            host = self.headers.get("Host", "")
            host_port = host.split(":")[-1] if ":" in host else ""
            if not host_port.isdigit() or host.split(":")[0] not in ("localhost", "127.0.0.1"):
                return self.send_error(403)
            if origin not in (None, f"http://localhost:{host_port}", f"http://127.0.0.1:{host_port}"):
                return self.send_error(403)
            worker = workers[segments[0]]
            worker.wake.set()
            return self.json_reply(202, {"accepted": True, **worker.snapshot()})

    return Handler


def serve(port: int, interval_portinatx: int, interval_pirineo: int, open_browser=False):
    import webbrowser
    workers = {"portinatx": Collector("portinatx", interval_portinatx),
               "pirineo": Collector("pirineo", interval_pirineo)}
    srv = ThreadingHTTPServer(("127.0.0.1", port), server_handler(workers))
    for worker in workers.values():
        threading.Thread(target=worker.run, daemon=True, name=f"collector-{worker.domain}").start()
    url = f"http://localhost:{srv.server_port}/"
    print(f"MeteoPortinatx Unified {VERSION}: {url}", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        srv.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


def regression(root: Path) -> int:
    # A self-contained .pyz has no extracted tests/ tree. Built-in domain selftests
    # still run; CI executes the complete filesystem suite before packaging.
    if not (root / "src" / "portinatx_degen.py").is_file():
        import pirineo_meta
        failures = [coastal.selftest(), mountain.selftest(), pirineo_meta.selftest()]
        return int(any(failures))
    commands = [
        [sys.executable, str(root / "src" / "portinatx_degen.py"), "selftest"],
        [sys.executable, str(root / "src" / "pirineo.py"), "selftest"],
        [sys.executable, str(root / "src" / "pirineo_meta.py"), "selftest"],
        [sys.executable, "-m", "unittest", "discover", "-s", str(root / "tests"), "-v"],
    ]
    for command in commands:
        print("TEST", " ".join(command), flush=True)
        if subprocess.call(command, cwd=root) != 0:
            return 1
    return 0


def main(argv=None):
    cli = argparse.ArgumentParser(description="MeteoPortinatx Unified · Portinatx + Pirineo")
    sub = cli.add_subparsers(dest="command", required=False)
    x = sub.add_parser("export", help="actualiza uno o ambos dominios")
    x.add_argument("--domain", choices=(*DOMAINS, "all"), default="all")
    sub.add_parser("selftest")
    sub.add_parser("status")
    s = sub.add_parser("serve", help="servidor local con dos colectores independientes")
    s.add_argument("--port", type=int, default=8787)
    s.add_argument("--portinatx-interval", type=int, default=300)
    s.add_argument("--pirineo-interval", type=int, default=10800)
    s.add_argument("--open", action="store_true")
    args = cli.parse_args(argv)
    if args.command in (None, "serve"):
        if args.command == "serve":
            interval_p, interval_m, port, op = args.portinatx_interval, args.pirineo_interval, args.port, args.open
        else:
            interval_p, interval_m, port, op = 300, 10800, 8787, True
        if not (60 <= interval_p <= 86400 and 60 <= interval_m <= 86400):
            cli.error("intervalos permitidos: 60–86400 segundos")
        serve(port, interval_p, interval_m, op)
    elif args.command == "export":
        targets = DOMAINS if args.domain == "all" else (args.domain,)
        failures = []
        for domain in targets:
            try:
                print(json.dumps(export(domain), ensure_ascii=False))
            except Exception as exc:
                failures.append(domain)
                print(f"ERROR {domain}: {type(exc).__name__}: {exc}", file=sys.stderr)
        if failures:
            raise SystemExit(1)
    elif args.command == "status":
        print(json.dumps({d: status(d) for d in DOMAINS}, ensure_ascii=False, indent=2))
    else:
        return regression(Path(__file__).resolve().parent.parent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
