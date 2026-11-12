"""Exercise the partial language selector and preservation of source warnings."""
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_support import NODE, ROOT, require_browser  # noqa: E402

JS = r'''
const {chromium} = require('playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const [chrome, file] = process.argv.slice(1);
(async () => {
 const browser=await chromium.launch({executablePath:chrome,headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage();
  const html=fs.readFileSync(file,'utf8');
  await page.route('**/*', route=>route.request().url()==='http://meteo.test/' ? route.fulfill({contentType:'text/html',body:html}) : route.abort());
  await page.goto('http://meteo.test/');
  await page.selectOption('#portinatx-language','en');
  assert.equal(await page.locator('[data-tab="vigilancia"]').textContent(),'Monitoring');
  assert.equal(await page.locator('#portinatx-language-note').isVisible(),true);
  assert.equal(await page.locator('nav.tabs').getAttribute('aria-label'),'Sections');
  await page.locator('#off-list').evaluate(e=>{e.innerHTML='<li>Aviso oficial original</li>';});
  await page.waitForTimeout(100);
  assert.equal(await page.locator('#off-list').textContent(),'Aviso oficial original');
  await page.reload();
  assert.equal(await page.locator('#portinatx-language').inputValue(),'en');
  await page.selectOption('#portinatx-language','es');
  assert.equal(await page.locator('[data-tab="vigilancia"]').textContent(),'Vigilancia');
  assert.equal(await page.locator('#portinatx-language-note').isVisible(),false);
  assert.equal(await page.locator('nav.tabs').getAttribute('aria-label'),'Secciones');
 } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exit(1)});
'''

class PortinatxLanguageBrowser(unittest.TestCase):
    def test_switch_and_source_warnings(self):
        chrome = require_browser(self)
        proc = subprocess.run([NODE, '-e', JS, chrome, str(ROOT / 'src/portinatx_app.html')],
                              cwd=ROOT, capture_output=True, text=True, timeout=40, env=os.environ.copy())
        self.assertEqual(proc.returncode, 0, proc.stderr)
