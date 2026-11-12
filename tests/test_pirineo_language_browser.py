"""Partial translation must preserve source warnings, preference and switching."""
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
 const browser = await chromium.launch({executablePath:chrome, headless:true, args:['--no-sandbox']});
 try {
  const page = await browser.newPage();
  const html = fs.readFileSync(file,'utf8');
  await page.route('**/*', route => route.request().url()==='http://meteo.test/' ? route.fulfill({contentType:'text/html',body:html}) : route.abort());
  await page.goto('http://meteo.test/');
  await page.selectOption('#pir-language','en');
  assert.equal(await page.locator('[data-tab="atmosfera"]').textContent(),'Atmosphere');
  assert.equal(await page.locator('#language-note').isVisible(),true);
  assert.equal(await page.evaluate(() => chatEnglish()),true);
  assert.equal(await page.evaluate(() => window.meteoLocale()),'en-GB');
  assert.equal(await page.locator('nav.tabs').getAttribute('aria-label'),'Observatory sections');
  await page.locator('#pa-content').evaluate(e=>{e.innerHTML='<h3>Temperatura, rocío y bulbo húmedo</h3><p class="src">Se descartan los niveles bajo terreno; la cizalladura hasta niveles de presión no equivale a capas exactas de 1, 3 o 6 km.</p>';});
  await page.waitForFunction(()=>document.querySelector('#pa-content h3')?.textContent==='Temperature, dew point and wet bulb');
  assert.match(await page.locator('#pa-content p').textContent(),/not equivalent to exact 1, 3 or 6 km layers/);
  await page.locator('#now-kv').evaluate(e=>{e.innerHTML='<div><span>Fase en el fondo</span><b>⚠ capa cálida 1000–1600 m sobre aire bajo cero: riesgo de lluvia engelante o hielo</b></div>';});
  await page.waitForFunction(()=>document.querySelector('#now-kv b')?.textContent.includes('risk of freezing rain or ice'));
  assert.match(await page.locator('#now-kv b').textContent(),/1000–1600 m/);
  await page.locator('#pa-content h3').evaluate(e=>{e.firstChild.nodeValue='Hodógrafa';});
  await page.waitForFunction(()=>document.querySelector('#pa-content h3')?.textContent==='Hodograph');


  await page.locator('#pov-official').evaluate(e=>{e.innerHTML='<ul><li><span>VIGENTE</span> · <span data-source-text>rojo</span></li></ul>';});
  await page.waitForFunction(()=>document.querySelector('#pov-official li span')?.textContent==='ACTIVE');
  assert.equal(await page.locator('#pov-official [data-source-text]').textContent(),'rojo');
  await page.reload();
  assert.equal(await page.locator('#pir-language').inputValue(),'en');
  await page.selectOption('#pir-language','es');
  assert.equal(await page.locator('[data-tab="atmosfera"]').textContent(),'Atmósfera');
  assert.equal(await page.locator('#language-note').isVisible(),false);
  assert.equal(await page.evaluate(() => chatEnglish()),false);
  assert.equal(await page.evaluate(() => window.meteoLocale()),'es-ES');
  assert.equal(await page.locator('nav.tabs').getAttribute('aria-label'),'Secciones del observatorio');
 } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exit(1)});
'''

class PirineoLanguageBrowser(unittest.TestCase):
    def test_switch_and_persistence(self):
        chrome = require_browser(self)
        proc = subprocess.run([NODE, '-e', JS, chrome, str(ROOT / 'src/pirineo_app.html')],
                              cwd=ROOT, capture_output=True, text=True, timeout=40, env=os.environ.copy())
        self.assertEqual(proc.returncode, 0, proc.stderr)
