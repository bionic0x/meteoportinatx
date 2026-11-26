"""Móvil y accesibilidad en Chrome real a 360 px: viewport, reflujo, nombres de gráficas, nivel como texto,
contraste de los textos de nivel, objetivos de 24 px y GPX con teclado.

Páginas servidas desde src/ sin red (estado vacío); Portinatx recibe además datos sintéticos inyectados.
Se omite si faltan Node, Playwright o Chrome, salvo con METEO_REQUIRE_BROWSER=1 (CI), donde falla.
"""
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_support import NODE, ROOT, require_browser  # noqa: E402

JS = r'''
const {chromium}=require('playwright');
const fs=require('node:fs'), path=require('node:path');
const assert=require('node:assert/strict');
const [chrome, src]=process.argv.slice(1);
const PAGES={'nowcast_hub.html':['select'],
 'portinatx_app.html':['select','details summary','input[type=range]'],
 'pirineo_app.html':['select','input[type=range]'],
 'decision_app.html':[],
 'device_app.html':['.top a','select','#wake'],
 'pirineo_ruta.html':['header a','select','input[type=range]']};
// Luminancia relativa WCAG 2.x de un color CSS rgb()/rgba() opaco.
const lum=c=>{const v=c.match(/[\d.]+/g).slice(0,3).map(x=>{x/=255;return x<=0.04045?x/12.92:((x+0.055)/1.055)**2.4});return 0.2126*v[0]+0.7152*v[1]+0.0722*v[2]};
const ratio=(a,b)=>{const [x,y]=[lum(a),lum(b)].sort((p,q)=>q-p);return (x+0.05)/(y+0.05)};
(async()=>{
 const browser=await chromium.launch({executablePath:chrome,headless:true,args:['--no-sandbox']});
 try{
  for(const [file,targets] of Object.entries(PAGES)){
   const ctx=await browser.newContext({viewport:{width:360,height:780},isMobile:true,hasTouch:true});
   const page=await ctx.newPage(); const errors=[];
   page.on('pageerror',e=>errors.push(e.message));
   await page.route('**/*',r=>{const u=new URL(r.request().url()), f=path.join(src,path.basename(u.pathname));
    if(u.host!=='meteo.test'||!fs.existsSync(f)) return r.abort();
    return r.fulfill({contentType:f.endsWith('.js')?'application/javascript':'text/html',body:fs.readFileSync(f)});});
   await page.goto('http://meteo.test/x/'+file); await page.waitForTimeout(400);
   const base=await page.evaluate(()=>({compat:document.compatMode, vp:document.querySelector('meta[name=viewport]')?.content||'',
    lang:document.documentElement.lang, iw:innerWidth, sw:document.documentElement.scrollWidth}));
   assert.equal(base.compat,'CSS1Compat',file+': modo estándar (doctype)');
   assert.match(base.vp,/width=device-width/,file+': meta viewport');
   assert.match(base.lang,/^es/,file+': lang es');
   assert.ok(base.sw<=base.iw,`${file}: desbordamiento horizontal ${base.sw}>${base.iw}`);
   if(file==='portinatx_app.html'){
    await page.evaluate(()=>{const now=Date.now(), L=['quiet','watch','alert','alarm','unknown'], iso=t=>new Date(t).toISOString();
     S.core={history:Array.from({length:12},(_,i)=>({id:`ciclo-20261126T${String(i).padStart(2,'0')}00Z`,nowcast:L[i%5],level:L[(i+1)%5]})),
      official:{all:[{evento:'Aviso de lluvias de nivel amarillo',nivel:'amarillo',desde:iso(now-3600e3),hasta:iso(now+6*3600e3),activo:true},
                     {evento:'Aviso de fenómenos costeros de nivel naranja',nivel:'naranja',tipo:'costero',desde:iso(now),hasta:iso(now+9*3600e3),activo:true}]},governance:{}};
     const rows=Array.from({length:8},(_,k)=>({t:iso(now-(8-k)*3600e3),hm0:1+k/10,hmax:2+k/10,vv_md:5+k}));
     S.series={portus:{'Boya Dragonera':{kind:'boya',rows},'Estación Ibiza':{kind:'viento',rows}}};
     renderHistory(); renderCharts();
     document.querySelector('main').insertAdjacentHTML('beforeend','<p id="a11y-pills">'+L.map(l=>pill(l)).join(' ')+'</p>');});
    const r=await page.evaluate(()=>{const g=id=>document.querySelector(`#${id} svg`), txt=e=>[...e.querySelectorAll('text')].map(t=>t.textContent).join('|');
     return {sw:document.documentElement.scrollWidth, iw:innerWidth,
      hs:g('ch-hs')?.getAttribute('aria-label'), warnLabel:g('ch-warn').getAttribute('aria-label'), warnText:txt(g('ch-warn')),
      histRole:g('ch-hist').getAttribute('role'), histLabel:g('ch-hist').getAttribute('aria-label'),
      histTitles:[...g('ch-hist').querySelectorAll('title')].map(t=>t.textContent).join('|'),
      histSub:document.querySelector('#ch-hist .sub')?.textContent||''};});
    assert.ok(r.sw<=r.iw,`Portinatx con datos: desbordamiento ${r.sw}>${r.iw}`);
    assert.match(r.hs||'',/oleaje.*en m$/,'lineChart con nombre y unidades');
    for(const s of [r.warnText,r.warnLabel]){assert.match(s,/de nivel amarillo/);assert.match(s,/de nivel naranja/);}
    assert.equal(r.histRole,'img');
    assert.match(r.histLabel,/12 ciclos; último ciclo: precaución Vigilancia · 36 h Alerta/);
    assert.match(r.histSub,/Último ciclo: precaución Vigilancia · 36 h Alerta/,'nivel visible sin hover');
    for(const s of [r.histLabel,r.histTitles,r.histSub]) assert.doesNotMatch(s,/\b(quiet|watch|alert|alarm|unknown)\b/,'nivel en español');
    // Contraste de los textos de nivel: pastillas y textos del Gantt y del historial.
    const pairs=await page.evaluate(()=>{const bg=e=>{for(let a=e;a;a=a.parentElement){const c=getComputedStyle(a).backgroundColor;if(!/rgba\(.*, 0\)|transparent/.test(c))return c;}return 'rgb(0, 0, 0)'};
     const els=[...document.querySelectorAll('#a11y-pills .pill, #ch-warn svg text, #ch-hist .sub')];
     return els.map(e=>({t:e.textContent, fg:e instanceof SVGElement?getComputedStyle(e).fill:getComputedStyle(e).color, bg:bg(e)}));});
    assert.ok(pairs.length>=8,'textos de nivel encontrados');
    for(const p of pairs) assert.ok(ratio(p.fg,p.bg)>=4.5,`contraste ${ratio(p.fg,p.bg).toFixed(2)} < 4,5 en «${p.t}» (${p.fg} / ${p.bg})`);
   }
   if(file==='pirineo_ruta.html'){
    await page.evaluate(()=>document.querySelector('main').insertAdjacentHTML('beforeend','<p id="a11y-pills">'+['l0','l1','l2','l3','l4'].map(c=>`<span class="pill ${c}">nivel</span>`).join(' ')+'</p>'));
    const pairs=await page.evaluate(()=>[...document.querySelectorAll('#a11y-pills .pill')].map(e=>({fg:getComputedStyle(e).color,bg:getComputedStyle(e).backgroundColor})));
    for(const p of pairs) assert.ok(ratio(p.fg,p.bg)>=4.5,`Rutas: contraste ${ratio(p.fg,p.bg).toFixed(2)} < 4,5`);
    // GPX con teclado: se alcanza con el tabulador, muestra el foco en su etiqueta y abre el selector con Espacio.
    // Enter no se comprueba: en Chrome headless abre el selector de forma intermitente (medido), sin relación con esta página.
    let reached=false;
    for(let i=0;i<30&&!reached;i++){await page.keyboard.press('Tab'); reached=await page.evaluate(()=>document.activeElement?.id==='file');}
    assert.ok(reached,'el selector de GPX se alcanza con el tabulador');
    const lab=await page.evaluate(()=>{const e=document.activeElement, l=e.labels[0], r=e.getBoundingClientRect();
     return {name:l.textContent.trim(), outline:getComputedStyle(l).outlineStyle, hidden:e.hidden}});
    assert.equal(lab.name,'Subir track GPX'); assert.notEqual(lab.outline,'none','foco visible en la etiqueta'); assert.equal(lab.hidden,false);
    const [chooser]=await Promise.all([page.waitForEvent('filechooser',{timeout:10000}),page.keyboard.press('Space')]);
    assert.ok(chooser,'selector de archivo con Espacio');
   }
   // Gráficas con nombre: ningún svg/canvas visible sin nombre ni aria-hidden.
   const unnamed=await page.evaluate(()=>[...document.querySelectorAll('svg, canvas')].filter(e=>{
     if(e.closest('[aria-hidden=true]')||e.parentElement.closest('svg')) return false;
     if(e.tagName==='svg'&&!e.getAttribute('role')&&!e.classList.contains('ch')) return false;
     return !(e.getAttribute('aria-label')||e.getAttribute('aria-labelledby')||e.querySelector(':scope > title'));
    }).map(e=>(e.id||e.parentElement.id||e.tagName)));
   assert.deepEqual(unnamed,[],file+': gráficas sin nombre');
   // Objetivos táctiles medidos por debajo de 24 px en la auditoría.
   const small=await page.evaluate(sel=>sel.flatMap(s=>[...document.querySelectorAll(s)]).filter(e=>{const r=e.getBoundingClientRect();
     return r.width>0&&r.height>0&&(r.width<24||r.height<24)}).map(e=>`${e.tagName}#${e.id} ${Math.round(e.getBoundingClientRect().width)}x${Math.round(e.getBoundingClientRect().height)}`),targets);
   assert.deepEqual(small,[],file+': objetivos < 24 px');
   assert.deepEqual(errors,[],file+': errores de página');
   await ctx.close();
  }
  // Hub: movimiento reducido.
  const ctx=await browser.newContext({viewport:{width:360,height:780},reducedMotion:'reduce'});
  const page=await ctx.newPage();
  await page.route('**/*',r=>r.request().url().endsWith('/nowcast_hub.html')?r.fulfill({contentType:'text/html',body:fs.readFileSync(path.join(src,'nowcast_hub.html'))}):r.abort());
  await page.goto('http://meteo.test/nowcast_hub.html');
  const tr=await page.evaluate(()=>[...document.querySelectorAll('.card')].map(e=>getComputedStyle(e).transitionDuration));
  assert.ok(tr.length&&tr.every(d=>d==='0s'),'hub sin transiciones con prefers-reduced-motion: '+tr);
  await ctx.close();
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
'''


class A11yMobileBrowser(unittest.TestCase):
    def test_mobile_accessibility_at_360(self):
        chrome = require_browser(self)
        proc = subprocess.run([NODE, '-e', JS, chrome, str(ROOT / 'src')],
                              cwd=ROOT, capture_output=True, text=True, timeout=120, env=os.environ.copy())
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == '__main__':
    unittest.main()
