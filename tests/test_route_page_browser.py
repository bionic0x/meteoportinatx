"""Página de rutas en un navegador real: privacidad (cero peticiones externas), cálculo, fallo cerrado y móvil.

Datos sintéticos servidos desde un servidor local temporal. Se omite si faltan Node, Playwright o Chrome (salvo METEO_REQUIRE_BROWSER=1).
"""
import json
import math
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
import pirineo  # noqa: E402
from browser_support import NODE, require_browser  # noqa: E402

LATS = [round(42.30 + 0.05 * i, 2) for i in range(8)]
LONS = [round(1.45 + 0.05 * j, 2) for j in range(16)]


def synthetic_dem():
    nlat, nlon, step = 101, 206, 0.004
    rows = []
    for i in range(nlat):
        la = 42.68 - i * step
        rows.append([int(1100 + 1400 * math.exp(-(((la - 42.50) ** 2) / 0.006 + ((1.40 + j * step - 1.75) ** 2) / 0.03)) + 150 * math.sin(j / 9)) for j in range(nlon)])
    return pirineo.pack_dem({"lat_n": 42.68, "lon_w": 1.40, "step": step, "nlat": nlat, "nlon": nlon, "rows": rows})


def synthetic_grid(start: datetime):
    times = [(start + timedelta(hours=3 * k)).strftime("%Y-%m-%dT%H:%M") for k in range(16)]
    def field(fn):
        return [[fn(la, lo, k) for la in LATS for lo in LONS] for k in range(16)]
    return {"modelo": "sintético", "lats": LATS, "lons": LONS, "time": times, "paso_h": 3,
            "elev": [1500.0 for _ in LATS for _ in LONS],
            "fields": {"temperature_2m": field(lambda la, lo, k: 4.0 - 0.1 * k), "dew_point_2m": field(lambda la, lo, k: 2.5 - 0.1 * k),
                       "precipitation": field(lambda la, lo, k: 4.5 if k in (1, 2) else 0.0), "snowfall": field(lambda *a: 0.0),
                       "wind_speed_10m": field(lambda *a: 25.0), "wind_gusts_10m": field(lambda la, lo, k: 35.0 + 6 * k),
                       "freezing_level_height": field(lambda *a: 2300.0)}}


def synthetic_core(now: datetime):
    return {"issued": now.isoformat(), "box": pirineo.BOX,
            "pois": [{"id": "valle", "name": "Valle", "lat": 42.40, "lon": 1.95, "alt_ref": 1150, "alt_dem": 1150},
                     {"id": "cima", "name": "Cima", "lat": 42.52, "lon": 1.75, "alt_ref": 2600, "alt_dem": 2600}],
            "avisos": [{"nivel": "amarillo", "evento": "Viento", "area": "Zona de prueba", "fuente": "MeteoAlarm", "vigente": True}]}


JS = r"""
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const [chrome, base, gpxPath]=process.argv.slice(1);
(async()=>{
 const browser=await chromium.launch({executablePath:chrome,headless:true,args:['--no-sandbox']});
 try{
  const ctx=await browser.newContext({viewport:{width:1100,height:900}});
  const page=await ctx.newPage();
  const reqs=[], errors=[];
  page.on('request',r=>reqs.push({url:r.url(),method:r.method(),body:r.postData()}));
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'/pirineo/ruta/');
  await page.waitForFunction(()=>!document.getElementById('demo').disabled,null,{timeout:15000});
  assert.ok((await page.textContent('#official')).includes('Viento'), 'avisos oficiales visibles');
  // Demostración: resultado, lienzos con contenido y peligros por separado.
  await page.click('#demo');
  await page.waitForSelector('#result:not([hidden])');
  const hz=await page.textContent('#hz');
  for (const t of ['Lluvia','Viento','Nieve','Frío','No evaluado']) assert.ok(hz.includes(t), 'falta '+t);
  assert.ok((await page.textContent('#hz')).includes('tormenta'), 'lo no evaluado se declara');
  const painted=await page.evaluate(()=>['cmap','cprof'].map(id=>{const c=document.getElementById(id),d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;const s=new Set();for(let i=0;i<d.length;i+=4*97)s.add(d[i]+','+d[i+1]+','+d[i+2]);return s.size;}));
  assert.ok(painted[0]>20&&painted[1]>5, 'lienzos con contenido: '+painted);
  const arrive1=await page.evaluate(()=>[...document.querySelectorAll('#kv div')].find(d=>d.textContent.includes('Llegada')).textContent);
  // Cambiar la hora de salida desplaza la llegada.
  await page.evaluate(()=>{const r=document.getElementById('dep');r.value=String(Math.min(+r.max,24));r.dispatchEvent(new Event('input'));});
  const arrive2=await page.evaluate(()=>[...document.querySelectorAll('#kv div')].find(d=>d.textContent.includes('Llegada')).textContent);
  assert.notEqual(arrive1,arrive2,'la llegada debe depender de la salida');
  // El factor de ritmo cambia la duración.
  const dur=()=>page.evaluate(()=>[...document.querySelectorAll('#kv div')].find(d=>d.textContent.includes('Duración')).textContent);
  const d1=await dur(); await page.selectOption('#act','0.6'); const d2=await dur(); assert.notEqual(d1,d2);
  // Subida de un GPX propio.
  const before=reqs.length;
  await page.setInputFiles('#file',gpxPath);
  await page.waitForFunction(()=>document.getElementById('warns').textContent.includes('PRIVADO-XYZ'),null,{timeout:10000});
  await page.hover('#cmap',{position:{x:300,y:200}});
  // Privacidad: ninguna petición externa, ninguna petición posterior a la subida, nada con el nombre ni con coordenadas.
  const origin=new URL(base).origin;
  assert.ok(reqs.every(r=>r.url.startsWith(origin)||r.url.startsWith('data:')), 'peticiones externas: '+reqs.filter(r=>!r.url.startsWith(origin)).map(r=>r.url));
  assert.equal(reqs.length,before,'subir un track no debe generar ninguna petición');
  assert.ok(!reqs.some(r=>/PRIVADO|42\.4|1\.9/.test(r.url+(r.body||''))), 'el track no viaja en ninguna petición');
  assert.ok(reqs.every(r=>r.method==='GET'), 'solo GET');
  assert.ok(!(await page.evaluate(()=>JSON.stringify(Object.assign({},localStorage,sessionStorage)))).includes('PRIVADO'), 'no se guarda');
  // Fichero inválido: error visible, sin resultado.
  await page.setInputFiles('#file',{name:'x.gpx',mimeType:'text/xml',buffer:Buffer.from('<gpx><trk/></gpx>')});
  await page.waitForSelector('#err:not([hidden])');
  assert.ok((await page.textContent('#err')).includes('No se pudo leer'));
  assert.ok(await page.locator('#result').isHidden());
  // Móvil: sin desbordamiento horizontal.
  await page.setViewportSize({width:390,height:844});
  await page.click('#demo'); await page.waitForSelector('#result:not([hidden])');
  assert.ok(!(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)),'desborda en móvil');
  // Fallo cerrado: rejilla inválida → no hay botón de demostración ni resultados, y el mensaje lo dice.
  const p2=await ctx.newPage();
  await p2.route('**/pirineo/api/grid.json',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify({status:'error: sin datos'})}));
  await p2.goto(base+'/pirineo/ruta/');
  await p2.waitForSelector('#err:not([hidden])',{timeout:15000});
  assert.ok((await p2.textContent('#err')).includes('nada se da por'));
  assert.ok(await p2.locator('#demo').isDisabled());
  assert.deepEqual(errors,[], 'errores de página: '+JSON.stringify(errors));
  console.log('route page: privacidad, cálculo, salida/ritmo, GPX, fallo cerrado y móvil PASS');
 } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exit(1)});
"""


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


class RoutePageBrowser(unittest.TestCase):
    def test_page_end_to_end(self):
        chrome = require_browser(self)
        now = datetime.now(timezone.utc)
        start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        with tempfile.TemporaryDirectory() as td:
            site = Path(td) / "site"
            (site / "pirineo" / "ruta").mkdir(parents=True)
            (site / "pirineo" / "api").mkdir()
            shutil.copy2(ROOT / "src" / "pirineo_ruta.html", site / "pirineo" / "ruta" / "index.html")
            shutil.copy2(ROOT / "src" / "route_engine.js", site / "pirineo" / "ruta" / "route_engine.js")
            shutil.copy2(ROOT / "src" / "public_fetch.js", site / "public_fetch.js")
            (site / "public_config.js").write_text('window.METEO_BACKEND_URL="";\n')
            for name, obj in (("core", synthetic_core(now)), ("dem", synthetic_dem()), ("grid", synthetic_grid(start))):
                (site / "pirineo" / "api" / f"{name}.json").write_text(json.dumps(obj))
            pts = "".join(f'<trkpt lat="{42.42 + 0.002 * i:.5f}" lon="{1.92 - 0.001 * i:.5f}"><ele>{1200 + 6 * i}</ele></trkpt>' for i in range(60))
            gpx = Path(td) / "mio.gpx"
            gpx.write_text(f'<gpx><trk><name>PRIVADO-XYZ</name><trkseg>{pts}</trkseg></trk></gpx>')
            server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(site)))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                r = subprocess.run([NODE, "-e", JS, chrome, f"http://127.0.0.1:{server.server_port}", str(gpx)],
                                   capture_output=True, text=True, timeout=120, cwd=str(ROOT))
            finally:
                server.shutdown()
                server.server_close()
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("PASS", r.stdout)


if __name__ == "__main__":
    unittest.main()
