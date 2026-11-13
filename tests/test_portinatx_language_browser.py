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
  assert.equal(await page.locator('html').getAttribute('lang'),'es');
  await page.selectOption('#portinatx-language','en');
  assert.equal(await page.locator('[data-tab="vigilancia"]').textContent(),'Monitoring');
  assert.equal(await page.locator('#portinatx-language-note').isVisible(),true);
  assert.equal(await page.locator('nav.tabs').getAttribute('aria-label'),'Sections');
  await page.evaluate(() => {
   S.forense={modelos:[], pares_cols:[], pares:[], dias:[], puntuacion:{}, aprendizaje:{}};
   renderForense();
  });
  assert.match(await page.locator('#fz-sample').textContent(),/^Archive: 0 days/);
  await page.locator('#pre-exit').evaluate(e => { e.innerHTML = '<li>aviso oficial vigente ≤ watch</li><li>sin peligro local observado ≥ nivel actual en 3 ciclos seguidos</li>'; });
  await page.waitForFunction(() => document.querySelector('#pre-exit').textContent.includes('current official warning ≤ watch'));
  assert.match(await page.locator('#pre-exit').textContent(), /no observed local hazard/);
  await page.locator('#refresh-st').evaluate(e => { e.textContent = 'El ciclo falló: timeout'; });
  await page.waitForFunction(() => document.querySelector('#refresh-st').textContent === 'The cycle failed: timeout');
  // A running cycle can mutate an existing text node instead of replacing it.
  await page.locator('#refresh-st').evaluate(e => { e.firstChild.data = 'Actualizado · ciclo-7'; });
  await page.waitForFunction(() => document.querySelector('#refresh-st').textContent === 'Updated · ciclo-7');
  await page.selectOption('#portinatx-language','es');
  assert.equal(await page.locator('#refresh-st').textContent(),'Actualizado · ciclo-7');
  await page.selectOption('#portinatx-language','en');
  assert.equal(await page.locator('#refresh-st').textContent(),'Updated · ciclo-7');
  await page.evaluate(() => { CHAT.turns=[{role:'user',content:'Mar'},{role:'assistant',content:'Viento'}]; renderChatLog(); });
  await page.waitForTimeout(100);
  assert.equal(await page.locator('#chat-log .msg.u').textContent(),'Mar');
  assert.equal(await page.locator('#chat-log .msg.a').textContent(),'Viento');
  await page.evaluate(() => {
   S.core={sources:[{name:'Mar',status:'ok',data_time:null,detail:'Viento'}],channels:[{name:'Mar',available:true,level:0,kind:'test',confidence:'unknown',age_min:2,evidence:['Mar']}]};
   renderSources(); renderChannels();
  });
  await page.waitForTimeout(100);
  assert.equal(await page.locator('#t-src tbody tr td').first().textContent(),'Mar');
  assert.equal(await page.locator('#t-src tbody tr td').last().textContent(),'Viento');
  assert.equal(await page.locator('#channels li').textContent(),'Mar');
  assert.equal(await page.locator('#channels summary b').textContent(),'Mar');
  await page.evaluate(() => {document.querySelector('#chat-log').innerHTML='<div id="chat-live">Mar</div>';});
  await page.waitForTimeout(100);
  assert.equal(await page.locator('#chat-live').textContent(),'Mar');



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
