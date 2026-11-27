"""Pirineo: «sin avisos» solo si respondieron todas las fuentes; las caídas se nombran como UNKNOWN."""
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
const path = require('node:path');
const assert = require('node:assert/strict');
const [chrome, dir] = process.argv.slice(1);
(async () => {
 const browser=await chromium.launch({executablePath:chrome,headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage();
  await page.route('**/*', route=>{
   const u=new URL(route.request().url());
   if(u.host!=='meteo.test') return route.abort();
   const name=u.pathname==='/'?'pirineo_app.html':path.basename(u.pathname);
   const f=path.join(dir,name);
   if(!fs.existsSync(f)) return route.fulfill({status:404,body:''});
   route.fulfill({contentType:name.endsWith('.js')?'text/javascript':'text/html',body:fs.readFileSync(f,'utf8')});
  });
  await page.goto('http://meteo.test/');
  const render = (cob, avisos, fuentes) => page.evaluate(([cob,avisos,fuentes]) => {
   const issued=new Date().toISOString();
   D.core={issued, fuentes, fuentes_edad_min:{avisos:0,aemet_cap:0}, avisos, avisos_cobertura:cob, obs:[], metar:[], perfil:{}};
   $("tab-diagnostico").hidden=false; renderDiag();
   return document.querySelector('#warns').textContent;
  }, [cob, avisos, fuentes]);
  const es={pais:'spain',nombre:'España',ambito:'Pirineo de Girona',estado:'ok',fuente:'MeteoAlarm'};
  const fr={pais:'france',nombre:'Francia',ambito:'departamentos 66 y 09',estado:'error',fuente:'MeteoAlarm'};
  const ad={pais:'andorra',nombre:'Andorra',ambito:'todo el país',estado:'ok',fuente:'MeteoAlarm'};
  // Francia caída, sin AEMET: no se certifica «sin avisos».
  let txt=await render([es,fr,ad],[{pais:'france',error:'OSError'}],{avisos:'parcial: no se pudo consultar Francia',aemet_cap:'sin clave AEMET_API_KEY'});
  assert.doesNotMatch(txt,/Sin avisos/); assert.match(txt,/UNKNOWN/);
  // AEMET CAP responde (España), Francia sigue caída: «sin avisos» solo para lo consultado y Francia nombrada.
  txt=await render([es,fr,ad],[{pais:'france',error:'OSError'}],{avisos:'parcial: no se pudo consultar Francia · España: AEMET CAP',aemet_cap:'ok'});
  assert.match(txt,/Sin avisos amarillos o superiores en: España.*Andorra/);
  assert.doesNotMatch(txt,/Sin avisos[^.]*Francia/);
  assert.match(txt,/no se pudo consultar: Francia/);
  // Todas responden.
  txt=await render([es,{...fr,estado:'ok'},ad],[],{avisos:'ok',aemet_cap:'sin clave AEMET_API_KEY'});
  assert.match(txt,/Sin avisos amarillos o superiores en: España.*Francia.*Andorra/); assert.doesNotMatch(txt,/UNKNOWN/);
  // Aviso con fuente parcial: se lista y la fuente caída sigue nombrada.
  const h=n=>new Date(Date.now()+n*3600000).toISOString();
  txt=await render([es,fr,ad],[{pais:'spain',area:'Pirineo de Lleida',nivel:'amarillo',evento:'Nieve',desde:h(-1),hasta:'',vigencia:'SIN FIN DECLARADO',caduca_prudente:h(10),vigente:true}],{avisos:'parcial: no se pudo consultar Francia',aemet_cap:'sin clave'});
  assert.match(txt,/Nieve/); assert.match(txt,/vigencia no indicada[^·]*· según el ciclo de hace/); assert.match(txt,/no se pudo consultar: Francia/);
  // Aviso rojo con hora sin zona horaria: visible como posible aviso, nunca «sin avisos».
  txt=await render([es,{...fr,estado:'ok'},ad],[{pais:'spain',area:'Pirineo de Lleida',nivel:'rojo',evento:'Nieve',desde:h(-2).slice(0,19),hasta:h(5).slice(0,19),vigencia:'SIN HORARIO VERIFICABLE',vigente:true}],{avisos:'ok',aemet_cap:'sin clave'});
  assert.match(txt,/posible aviso · horario no verificable · según el ciclo de hace/); assert.doesNotMatch(txt,/Sin avisos/);
 } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exit(1)});
'''


class AvisosPirineoBrowser(unittest.TestCase):
    def test_cobertura_por_fuente(self):
        chrome = require_browser(self)
        proc = subprocess.run([NODE, '-e', JS, chrome, str(ROOT / 'src')],
                              cwd=ROOT, capture_output=True, text=True, timeout=60, env=os.environ.copy())
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == '__main__':
    unittest.main()
