"""Real Chromium CORS test. Optional when Node/Playwright/Chromium are unavailable."""
import json
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]
import nowcast_backend as backend
import test_backend
from browser_support import NODE, require_browser


class BrowserFetch(unittest.TestCase):
    def test_cross_origin_fresh_stale_and_unavailable(self):
        chrome = require_browser(self)
        fixture = test_backend.PersistentBackend()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.fixture('portinatx')
        fixture.store.publish('portinatx', fixture.app)
        class Page(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                body = b'{"snapshot":true}' if self.path == '/static/core.json' else b'<html></html>'
                self.send_response(200)
                self.send_header('Content-Type', 'application/json' if self.path.endswith('.json') else 'text/html')
                self.end_headers()
                self.wfile.write(body)
        frontend = ThreadingHTTPServer(('127.0.0.1', 0), Page)
        origin = f'http://127.0.0.1:{frontend.server_port}'
        service = backend.Service(fixture.store.root)
        api = ThreadingHTTPServer(('127.0.0.1', 0), backend.handler(service, {origin}))
        for server in [frontend, api]:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(lambda s=server,t=thread: (s.shutdown(),s.server_close(),t.join(1)))
        js = r'''
const {chromium} = require('playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:process.argv[1],headless:true,args:['--no-sandbox']});
 try {
 const page=await browser.newPage();
 await page.goto(process.argv[2]);
 await page.addScriptTag({path:process.argv[4]});
 await page.evaluate(base=>window.METEO_BACKEND_URL=base,process.argv[3]);
 const result=await page.evaluate(()=>window.meteoLoadPart('portinatx','core','/static/core.json'));
 if(result.source !== process.argv[5]) throw Error(JSON.stringify(result));
 console.log(result.source);
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
'''
        def check(expected):
            result = subprocess.run([NODE,'-e',js,chrome,origin,
                f'http://127.0.0.1:{api.server_port}',str(ROOT/'src/public_fetch.js'),expected],
                cwd=ROOT,text=True,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        check('backend')
        pointer = fixture.store.public / 'portinatx' / 'CURRENT.json'
        data = json.loads(pointer.read_text())
        data['issued'] = '2000-01-01T00:00:00+00:00'
        pointer.write_text(json.dumps(data))
        check('snapshot-fallback')
        pointer.unlink()
        check('snapshot-fallback')
