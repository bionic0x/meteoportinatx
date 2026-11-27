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
    // Datos sintéticos para pintar todas las gráficas que no dependen del laboratorio (ver docs/ux-review/05).
    const runs=await page.evaluate(()=>{const now=Date.now(), L=['quiet','watch','alert','alarm','unknown'], iso=t=>new Date(t).toISOString(), isoZ=t=>iso(t).slice(0,16);
     const T=Array.from({length:48},(_,k)=>isoZ(now+(k-3)*3600e3)), seq=f=>T.map((_,k)=>f(k)), PR=[1000,925,850,700,500,300];
     const rows=Array.from({length:8},(_,k)=>({t:iso(now-(8-k)*3600e3),hm0:1+k/10,hmax:2+k/10,vv_md:5+k,vv_mx:7+k,dv_md:40}));
     const lvl=pr=>({T:seq(()=>15-(1000-pr)/30),Td:seq(()=>10-(1000-pr)/25),ws:seq(()=>5+(1000-pr)/50),wd:seq(()=>200+(1000-pr)/10)});
     S.core={history:Array.from({length:12},(_,i)=>({id:`ciclo-20261126T${String(i).padStart(2,'0')}00Z`,nowcast:L[i%5],level:L[(i+1)%5]})),
      official:{all:[{evento:'Aviso de lluvias de nivel amarillo',nivel:'amarillo',desde:iso(now-3600e3),hasta:iso(now+6*3600e3),activo:true},
                     {evento:'Aviso de lluvias de nivel amarillo',nivel:'naranja',desde:iso(now),hasta:iso(now+8*3600e3),activo:true},
                     {evento:'Aviso de fenómenos costeros de nivel naranja',tipo:'costero',desde:iso(now),hasta:iso(now+9*3600e3),activo:true}]},
      hazard:{radar:{estado:'UNKNOWN'}},
      governance:{episode:{id:'EP-1',phase:'ACTIVE',opened:iso(now-7200e3),closure_blockers:[]},claims:[{epistemic:'UNKNOWN',text:'x',source_root:'r',scope:'s',expires:iso(now)}],claims_count:{UNKNOWN:1},predictions:[],anomalies:[]}};
     S.series={portus:{'Boya Dragonera':{kind:'boya',rows},'Estación Ibiza':{kind:'viento',rows}},
      models:{arome_hd:{time:T,pr:seq(k=>k%7),pr_neigh_max:seq(k=>k%9)}},
      ensemble:{start:T[0],p50:seq(()=>1),max:seq(()=>4),p10:seq(()=>0),p90:seq(()=>2),n:51,total72:{p10:1,p50:2,p90:3,max:5},
       exceed:{'1':seq(k=>k%3/3),'5':seq(k=>k%5/10)},cum:[1,2,3].map(d=>seq(k=>k/d).slice(0,16)),hist24:[1,3,5,8,13,2,4],p24_point:.3,p24_neigh:.5},
      tracks:{arome_hd:[{init:iso(now-12*3600e3),max_dist_km:30,max12:20,centered:false},{init:iso(now-6*3600e3),max_dist_km:15,max12:25,centered:true}]},
      marine:{time:T,hs:seq(()=>1.2)},
      surface:{LEIB:Array.from({length:8},(_,k)=>({t:iso(now-(8-k)*3600e3),T:15+k/4,Td:10,P:1012+k/5,U:10+k,G:20+k}))}};
     S.atmos={model:'sintético',profile:{time:T,levels:Object.fromEntries(PR.map(p=>[p,lvl(p)])),wind10:{ws:seq(()=>4),wd:seq(()=>180)},indices:{},
      physics:{thetae:Object.fromEntries(PR.map(p=>[p,seq(()=>330-(1000-p)/40)])),shear_by_height:seq(()=>[[0,0],[1,4],[3,9],[6,15]])}}};
     S.mar={ocean:{time:T,sea_surface_temperature:seq(()=>20),ocean_current_velocity:seq(()=>1)},time:T,waves:{ecmwf_wam:{wave_height:seq(()=>1.1)}},boyas:{},
      surge:{serie:rows.map(r=>({t:r.t,obs:.1,mod:.05,res:.05})),res_ultimo:.05,res_max:.08,n:8}};
     S.modx={time:T,ventanas:{ecmwf_ifs:{}},series:{ecmwf_ifs:{pr:seq(k=>k%3)}},superens:{time:T,sistemas:{a:{nombre:'Sistema A',familia:'física',n:10,ventanas:{},mediana_h:seq(()=>.5)}}}};
     S.forense={modelos:['ecmwf_ifs'],pares_cols:[],pares:[],dias:[],puntuacion:{},aprendizaje:{},historial_aprendizaje:{'2026-11-20':{'ecmwf_ifs|D0':1.1},'2026-11-21':{'ecmwf_ifs|D0':1.2}}};
     const out={};
     // renderAtmos se corta en los índices compuestos tras pintar perfil y hodógrafa; el resto debe completarse.
     for(const f of ['renderHistory','renderCharts','renderSurface','renderEnsembleX','renderAtmos','renderPhysics','renderMar','renderModelsX','renderForense','renderGov','renderAxes']){
      try{eval(f+'()');out[f]='ok'}catch(e){out[f]=String(e)}}
     document.querySelector('main').insertAdjacentHTML('beforeend','<p id="a11y-pills">'+L.map(l=>pill(l)).join(' ')+'</p>');
     return out;});
    for(const f of ['renderHistory','renderCharts','renderSurface','renderEnsembleX','renderPhysics','renderMar','renderModelsX','renderForense','renderGov']) assert.equal(runs[f],'ok',f);
    const r=await page.evaluate(()=>{const g=id=>document.querySelector(`#${id} svg`), lines=e=>[...e.querySelectorAll('text')].map(t=>t.textContent);
     const warn=g('ch-warn'), wb=warn.getBoundingClientRect();
     return {sw:document.documentElement.scrollWidth, iw:innerWidth,
      drawn:[...document.querySelectorAll('[id^=ch-] > svg')].map(e=>e.parentElement.id),
      hs:g('ch-hs')?.getAttribute('aria-label'), warnLabel:warn.getAttribute('aria-label'), warnText:lines(warn),
      warnFill:[...warn.querySelectorAll('rect')].map(x=>x.getAttribute('fill')),
      warnLeft:Math.min(...[...warn.querySelectorAll('text')].map(t=>t.getBoundingClientRect().left))-wb.left,
      histRole:g('ch-hist').getAttribute('role'), histLabel:g('ch-hist').getAttribute('aria-label'),
      histTitles:[...g('ch-hist').querySelectorAll('title')].map(t=>t.textContent).join('|'),
      histSub:document.querySelector('#ch-hist .sub')?.textContent||'',
      phases:document.querySelector('#phases').textContent, phaseOn:document.querySelector('#phases .on')?.dataset.phase,
      states:['#haz-chips','#phases','#claim-filters','#t-claims'].map(q=>document.querySelector(q).textContent).join('|')};});
    assert.ok(r.sw<=r.iw,`Portinatx con datos: desbordamiento ${r.sw}>${r.iw}`);
    const REQUIRED=['ch-hs','ch-wind','ch-warn','ch-models','ch-ens','ch-tracks','ch-marine','ch-hist','ch-sfc-t','ch-sfc-p','ch-sfc-w',
     'ch-exceed','ch-spag','ch-hist24','ch-profile','ch-hodo','ch-thetae','ch-shear','ch-wav','ch-surge','ch-sst','ch-cur','ch-modx','ch-sens','ch-fz-learn'];
    assert.deepEqual(REQUIRED.filter(id=>!r.drawn.includes(id)),[],'gráficas sin pintar con los datos sintéticos');
    assert.match(r.hs||'',/oleaje.*en m$/,'lineChart con nombre y unidades');
    // Gantt: el nivel sale de `nivel` (la misma fuente que el color) y la discrepancia con el texto se señala.
    assert.deepEqual(r.warnText.slice(0,7),['lluvias','de nivel amarillo','lluvias','de nivel naranja','el texto dice amarillo','fenómenos costeros (c…','de nivel sin verificar']);
    assert.equal(r.warnText[7],'el texto dice naranja');
    assert.deepEqual(r.warnFill.slice(0,3),['var(--w)','var(--a)','var(--unk)']);
    assert.match(r.warnLabel,/Aviso de lluvias, de nivel amarillo; Aviso de lluvias, de nivel naranja \(el texto del aviso dice amarillo\); Aviso de fenómenos costeros \(costa\), de nivel sin verificar \(el texto del aviso dice naranja\)$/);
    assert.ok(r.warnLeft>=0,`etiqueta del Gantt fuera del gráfico por la izquierda (${r.warnLeft.toFixed(1)} px)`);
    assert.equal(r.histRole,'img');
    assert.match(r.histLabel,/12 ciclos; último ciclo: precaución Vigilancia · 36 h Alerta/);
    assert.match(r.histSub,/Último ciclo: precaución Vigilancia · 36 h Alerta/,'nivel visible sin hover');
    for(const s of [r.histLabel,r.histTitles,r.histSub]) assert.doesNotMatch(s,/\b(quiet|watch|alert|alarm|unknown)\b/,'nivel en español');
    // Fases y estados en español; el valor interno se conserva.
    assert.equal(r.phases,'ActivoCeseTransiciónCierre propuestoCerrado'); assert.equal(r.phaseOn,'ACTIVE');
    assert.match(r.states,/Desconocido \(UNKNOWN\)/);
    assert.doesNotMatch(r.states,/ACTIVE|CESSATION|TRANSITION|CLOSURE_PROPOSED|CLOSED|EVIDENCE|HYPOTHESIS|ASSUMPTION|(?<!\()UNKNOWN/,'estado en inglés visible');
    // Contraste de los textos de nivel: pastillas y textos del Gantt y del historial.
    const pairs=await page.evaluate(()=>{const bg=e=>{for(let a=e;a;a=a.parentElement){const c=getComputedStyle(a).backgroundColor;if(!/rgba\(.*, 0\)|transparent/.test(c))return c;}return 'rgb(0, 0, 0)'};
     const els=[...document.querySelectorAll('#a11y-pills .pill, #ch-warn svg text, #ch-hist .sub')];
     return els.map(e=>({t:e.textContent, fg:e instanceof SVGElement?getComputedStyle(e).fill:getComputedStyle(e).color, bg:bg(e)}));});
    assert.ok(pairs.length>=8,'textos de nivel encontrados');
    for(const p of pairs) assert.ok(ratio(p.fg,p.bg)>=4.5,`contraste ${ratio(p.fg,p.bg).toFixed(2)} < 4,5 en «${p.t}» (${p.fg} / ${p.bg})`);
   }
   if(file==='device_app.html'){
    const d=await page.evaluate(()=>{const w=document.getElementById('wake').getBoundingClientRect(), r=document.createRange(); r.selectNodeContents(document.getElementById('wake').parentElement);
     const t=[...r.getClientRects()].filter(x=>x.left>w.right-1)[0];
     return {text:document.getElementById('sensors').textContent+'|'+document.getElementById('trend').textContent, dy:t?Math.abs((w.top+w.bottom)/2-(t.top+t.bottom)/2):99};});
    assert.match(d.text,/Desconocido \(UNKNOWN\)/); assert.doesNotMatch(d.text,/(?<!\()UNKNOWN|STALE(?!\))|MEASURED/,'estado en inglés visible');
    assert.ok(d.dy<=4,`casilla #wake desalineada con su texto (${d.dy.toFixed(1)} px)`);
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
