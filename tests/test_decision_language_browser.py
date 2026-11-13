"""Language switching must retain evidence semantics and source texts."""
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
const [chrome,file] = process.argv.slice(1);
(async()=>{
 const browser=await chromium.launch({executablePath:chrome,headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage();
  const stub=`<script>
    window.MeteoDecision={profiles:{casa:{label:'Casa junto a torrente',domain:'portinatx'}},places:{font_romeu:'Font-Romeu'},project:()=>({question:'¿Qué ha cambiado cerca de casa?',heading:'No hay datos verificables',state:'unknown',source:'snapshot',available:false,official:{kind:'unknown',title:'Avisos sin verificar',detail:'Aviso de lluvias de nivel amarillo'},observed:[],operational:null,forecast:null,guidance:'No deducir calma ni tomar decisiones de seguridad con estos datos.'})};
    window.meteoLoadPart=async()=>({data:null,source:'snapshot'});
  </script>`;
  const html=fs.readFileSync(file,'utf8').replace(/<script src="\.\.\/public_config\.js"><\/script><script src="\.\.\/public_fetch\.js"><\/script><script src="\.\.\/decision_cards\.js"><\/script>/,stub);
  await page.route('**/*',r=>r.request().url()==='http://meteo.test/'?r.fulfill({contentType:'text/html',body:html}):r.abort());
  await page.goto('http://meteo.test/');
  await page.selectOption('#decision-language','en');
  await page.waitForFunction(()=>document.querySelector('#question').textContent==='What has changed near home?');
  assert.equal(await page.locator('#official-title').textContent(),'Warnings unverified');
  assert.equal(await page.locator('#official-detail').textContent(),'Aviso de lluvias de nivel amarillo');
  assert.equal(await page.locator('#official-detail').getAttribute('lang'),'und');
  assert.equal(await page.locator('html').getAttribute('lang'),'en');
  await page.reload();
  assert.equal(await page.locator('#decision-language').inputValue(),'en');
  await page.selectOption('#decision-language','es');
  assert.equal(await page.locator('#question').textContent(),'¿Qué ha cambiado cerca de casa?');
  assert.equal(await page.locator('html').getAttribute('lang'),'es');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
'''

class DecisionLanguageBrowser(unittest.TestCase):
    def test_switch_and_preserve_warning(self):
        chrome = require_browser(self)
        proc = subprocess.run([NODE, '-e', JS, chrome, str(ROOT / 'src/decision_app.html')],
                              cwd=ROOT, capture_output=True, text=True, timeout=40, env=os.environ.copy())
        self.assertEqual(proc.returncode, 0, proc.stderr)
