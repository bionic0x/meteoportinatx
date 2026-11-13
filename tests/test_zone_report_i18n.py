"""Offline regional report keeps warnings intact when switching language."""
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'src'), str(Path(__file__).resolve().parent)]
import zone_engine
import zone_report
from browser_support import NODE, ROOT, require_browser
from zone_fixtures import provider


class ZoneReportLanguage(unittest.TestCase):
    def test_offline_language_switch_and_original_warning(self):
        chrome = require_browser(self)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            profile = zone_engine.load_profile('pirineo')
            zone_engine.collect(profile, root / 'pack.zip', getter=lambda url: provider(url, partial_snow=True))
            html = zone_report.render_report(root / 'pack.zip').encode()

            class Handler(BaseHTTPRequestHandler):
                def log_message(self, *args): pass
                def do_GET(self):
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(html)

            server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(lambda: (server.shutdown(), server.server_close(), thread.join(1)))
            code = r'''
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:process.argv[1],headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage(); const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(process.argv[2]);
  const source=await page.locator('[data-source-text]').allTextContents();
  assert(source.includes('Test'));
  await page.selectOption('#report-language','en');
  assert.equal(await page.locator('html').getAttribute('lang'),'en');
  assert.equal(await page.locator('h3').filter({hasText:'Daily forecast · UTC'}).count(),3);
  assert((await page.locator('header .notice').innerText()).includes('Offline snapshot'));
  assert((await page.locator('figcaption').first().innerText()).includes('Frame:'));
  assert((await page.locator('small').first().innerText()).includes('/24 hours'));
  assert.deepEqual(await page.locator('[data-source-text]').allTextContents(),source);
  assert.equal(await page.locator('[data-source-text]').first().getAttribute('lang'),'und');
  await page.reload();assert.equal(await page.locator('#report-language').inputValue(),'en');
  await page.selectOption('#point-filter','masella');
  assert.equal(await page.locator('section.point:visible').count(),1);
  await page.selectOption('#report-language','es');
  assert.equal(await page.locator('html').getAttribute('lang'),'es');
  assert.equal(await page.locator('h3').filter({hasText:'Previsión diaria · UTC'}).count(),3);
  assert.deepEqual(await page.locator('[data-source-text]').allTextContents(),source);
  assert.deepEqual(errors,[]);
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
'''
            result = subprocess.run([NODE, '-e', code, chrome, f'http://127.0.0.1:{server.server_port}/'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
