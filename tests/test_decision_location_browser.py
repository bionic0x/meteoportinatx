"""Check that the mountain selector is visible only for mountain profiles."""
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
  await page.route('**/*', route => route.abort());
  let html = fs.readFileSync(file,'utf8');
  const stub = `<script>
   window.MeteoDecision = {
     profiles: {casa:{label:'Casa',domain:'portinatx'},barca:{label:'Barca',domain:'portinatx'},residencia:{label:'Segunda',domain:'pirineo'},meteo:{label:'Meteo',domain:'portinatx'},esqui:{label:'Esquí',domain:'pirineo'}},
     places:{font_romeu:'Font-Romeu'},
     project: () => ({question:'Consulta',heading:'Resumen',state:'recent',issued:null,source:'snapshot',available:true,ageMin:0,official:{kind:'unknown',title:'-',detail:'-'},observed:[],operational:null,forecast:null,guidance:'-'})
   };
   window.meteoLoadPart = async () => ({data:{},source:'snapshot'});
  </script>`;
  html = html.replace(/<script src="\.\.\/public_config\.js"><\/script><script src="\.\.\/public_fetch\.js"><\/script><script src="\.\.\/decision_cards\.js"><\/script>/, stub);
  await page.setContent(html);
  for (const profile of ['casa','barca','meteo']) {
   await page.locator(`[data-profile="${profile}"]`).click();
   await page.waitForFunction(p=>document.querySelector(`[data-profile="${p}"]`).getAttribute('aria-pressed')==='true',profile);
   assert.equal(await page.locator('#place-controls').isVisible(),false,profile);
  }
  for (const profile of ['residencia','esqui']) {
   await page.locator(`[data-profile="${profile}"]`).click();
   await page.waitForFunction(p=>document.querySelector(`[data-profile="${p}"]`).getAttribute('aria-pressed')==='true',profile);
   assert.equal(await page.locator('#place-controls').isVisible(),true,profile);
  }
 } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exit(1)});
'''

class DecisionLocationBrowser(unittest.TestCase):
    def test_selector_visibility_tracks_domain(self):
        chrome = require_browser(self)
        proc = subprocess.run([NODE, '-e', JS, chrome, str(ROOT / 'src/decision_app.html')],
                              cwd=ROOT, capture_output=True, text=True, timeout=40, env=os.environ.copy())
        self.assertEqual(proc.returncode, 0, proc.stderr)
