"""Portinatx: lista de avisos con la hora actual, «No verificado» con fuente caída y vigencia no indicada."""
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
  const render = official => page.evaluate(o => { S.core={official:o, precaution:{level:'quiet', transition:''}}; renderAxes(); return document.querySelector('#off-list').textContent; }, official);
  // Fuente caída: nunca «Sin avisos».
  let txt = await render({level_now:'unknown', verificado:false, all:[]});
  assert.match(txt, /No verificado/); assert.doesNotMatch(txt, /Sin avisos/);
  txt = await render({level_now:'quiet', verificado:true, all:[]});
  assert.match(txt, /Sin avisos en las próximas 36 h/);
  // Vigencia recalculada con la hora actual (el ciclo decía «activo» para todos).
  txt = await page.evaluate(() => {
   const h = n => new Date(Date.now()+n*3600000).toISOString();
   S.core={issued:h(-2), precaution:{level:'quiet', transition:''}, official:{level_now:'alert', verificado:true, all:[
    {nivel:'naranja', evento:'Aviso de lluvias', desde:h(-5), hasta:h(-1), activo:true, area:'Ibiza y Formentera', emitido:h(-6)},
    {nivel:'amarillo', evento:'Aviso de viento', desde:h(-1), hasta:h(3), activo:true, area:'Ibiza y Formentera', emitido:h(-2)},
    {nivel:'amarillo', evento:'Aviso de tormentas', desde:h(2), hasta:h(8), activo:true, area:'Ibiza y Formentera', emitido:h(-2)},
    {nivel:'amarillo', evento:'Aviso de costeros', desde:h(-1), hasta:'', vigencia:'SIN FIN DECLARADO', caduca_prudente:h(20), emitido:h(-4)},
    {nivel:'amarillo', evento:'Aviso de nieblas', desde:h(-1), hasta:h(5), vigencia:'SIN HORARIO VERIFICABLE'}]}};
   renderAxes(); return [...document.querySelectorAll('#off-list li')].map(li=>li.textContent);
  });
  assert.equal(txt.length, 4, 'the expired warning disappears at viewing time');
  assert.ok(!txt.some(t=>/lluvias/.test(t)));
  assert.match(txt[0], /viento · activo.*Ibiza y Formentera/); assert.match(txt[0], /emitido .*hace 2 h/);
  assert.match(txt[1], /tormentas · próximo/);
  assert.match(txt[2], /vigencia no indicada.*según el ciclo de hace 2 h.*fin no indicado/);
  assert.doesNotMatch(txt[0], /según el ciclo/);
  assert.match(txt[3], /horario no verificable/);
  // V-02: aviso rojo en curso con hora sin zona horaria → la cabecera nunca dice «Sin aviso vigente».
  const head = await page.evaluate(() => {
   const h = n => new Date(Date.now()+n*3600000).toISOString().slice(0,19);
   S.core={precaution:{level:'quiet', transition:''}, official:{level_now:'quiet', level_36h:'alarm', verificado:true, all:[
    {nivel:'rojo', rank:3, evento:'Aviso de lluvias', desde:h(-2), hasta:h(10), activo:false, vigencia:'SIN HORARIO VERIFICABLE'}]}};
   renderAxes(); return document.querySelector('#off-level').textContent;
  });
  assert.doesNotMatch(head, /Sin aviso vigente/); assert.match(head, /posible aviso rojo · horario no verificable/);
  assert.doesNotMatch(head, /^Rojo/, 'a doubtful time is not an official fact');
 } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exit(1)});
'''


class AvisosPortinatxBrowser(unittest.TestCase):
    def test_vigencia_y_no_verificado(self):
        chrome = require_browser(self)
        proc = subprocess.run([NODE, '-e', JS, chrome, str(ROOT / 'src/portinatx_app.html')],
                              cwd=ROOT, capture_output=True, text=True, timeout=40, env=os.environ.copy())
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == '__main__':
    unittest.main()
