/* Pirineo Nowcast 0.6.1 — evidence-first observatory views.
 * Reads the existing mountain-domain export only. No cross-domain thresholds.
 * No network calls, external assets, or new claims of continuous surveillance.
 */
(function (root) {
  'use strict';
  const valid = n => typeof n === 'number' && Number.isFinite(n);
  const number = (n, digits=1) => valid(n) ? n.toFixed(digits) : '—';
  const escape = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const utc = s => {
    if (typeof s !== 'string' || !s) return null;
    const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(s) ? s : s+'Z');
    return Number.isFinite(+d) ? d : null;
  };
  const stamp = s => {
    const d=utc(s);
    return d ? new Intl.DateTimeFormat('es-ES',{timeZone:'Europe/Madrid',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}).format(d) : '—';
  };
  const label = o => escape(o?.nombre || o?.id || '—');
  const present = (v, maxAge=180, age=null) => {
    if (typeof v !== 'string') return false;
    return (/^ok\b/i.test(v) || /^cach[eé]/i.test(v)) && (!valid(age) || age<=maxAge);
  };
  const source = (v, age) => {
    if (v==null) return 'UNKNOWN';
    if (/PERMISSION_UNKNOWN|sin clave|sin_clave|desactivado|^error/i.test(String(v))) return 'UNKNOWN';
    if (/API falló/i.test(String(v))) return 'DEGRADED';
    if (/^cach[eé]/i.test(String(v))) return valid(age) && age>180 ? 'STALE' : 'CACHED';
    if (/^ok\b/i.test(String(v))) return valid(age) && age>180 ? 'STALE' : 'OK';
    return 'UNKNOWN';
  };
  const point = (c,id) => (c?.puntos||[]).find(x=>x.id===id);
  const getPoint = (c,id) => (c?.pois||[]).find(x=>x.id===id);
  const at = (v,i) => Array.isArray(v) && i>=0 && i<v.length && valid(v[i]) ? v[i] : null;
  const modelRow = (c,id,m) => point(c,id)?.modelos?.[m] || {};
  const forecast = (series,id,m,k) => {
    const P=series?.[id],v=P?.m?.[m]||{},t=P?.time?.[k]||null;
    return {time:t, temperature:at(v.temperature_2m,k), dewpoint:at(v.dew_point_2m,k),
      humidity:at(v.relative_humidity_2m,k), cloud:at(v.cloud_cover,k),
      rain:at(v.precipitation,k), snow:at(v.snowfall,k),
      gust:at(v.wind_gusts_10m,k), wind:at(v.wind_speed_10m,k),
      direction:at(v.wind_direction_10m,k), freezing:at(v.freezing_level_height,k)};
  };
  const nearest = (list,time,toleranceHours=2) => {
    const goal=utc(time);
    if(!goal || !Array.isArray(list)) return null;
    let best=null,delta=Infinity;
    for(const item of list) {
      const d=utc(item?.t);
      if(d && Math.abs(d-goal)<delta){best=item; delta=Math.abs(d-goal);}
    }
    return delta<=toleranceHours*3600000 ? best : null;
  };
  function derive(c,series,extended,opts={}) {
    if(!c) return {status:'UNKNOWN'};
    const ids=(c.pois||[]).map(p=>p.id);
    const id=ids.includes(opts.pointId)?opts.pointId:ids.includes('la_molina')?'la_molina':ids[0];
    const models=(c.modelos||[]);
    const model=models.includes(opts.model)?opts.model:models[0];
    const P=series?.[id];
    const k=valid(opts.k)?Math.min(Math.max(0,opts.k),Math.max(0,(P?.time||[]).length-1)):0;
    const current=forecast(series,id,model,k);
    const summary=modelRow(c,id,model);
    const ages=c.fuentes_edad_min||{};
    const aemetState=source(c.fuentes?.aemet_cap,ages.aemet_cap);
    const meteolarmState=source(c.fuentes?.avisos,ages.avisos);
    const officialOk=['OK','CACHED'].includes(aemetState) || ['OK','CACHED'].includes(meteolarmState);
    const warn=(c.avisos||[]).filter(x=>!x.error && x.nivel);
    const freshObs=[...(c.obs||[]),...(c.metar||[])].filter(o=>valid(o.edad_min)&&o.edad_min>=-10&&o.edad_min<=90);
    const profiles={sur:nearest(c.perfil?.sur,current.time), norte:nearest(c.perfil?.norte,current.time)};
    const revisions=Array.isArray(extended?.run_revisions)?extended.run_revisions:[];
    const sidecars=c.contexto?.sidecars||{};
    return {status:'OK',id,model,k,current,summary,profile:profiles,officialOk,officialState:officialOk?(aemetState==='OK'?'AEMET CAP disponible':'Avisos disponibles con cobertura condicionada'):'UNKNOWN · avisos no verificados',
      warnings:warn,observations:freshObs,ages,sources:c.fuentes||{},revisions,sidecars,
      snowAtPoint:point(c,id)?.cotas,station:getPoint(c,id),
      forecastValidated:false, satelliteIntegrated:false, avalancheIntegrated:false};
  }
  const tbody = (el,rows,emptyCols) => { if(el)el.innerHTML=rows || `<tr><td colspan="${emptyCols}" class="empty">UNKNOWN · faltan datos comparables.</td></tr>`; };
  const grid = data => data.map(([a,b])=>`<div><span>${escape(a)}</span><b>${escape(b)}</b></div>`).join('');
  const S = {point:'la_molina',threshold:60};
  function render(ctx) {
    if(typeof document==='undefined'||!ctx?.core) return;
    const c=ctx.core, e=derive(c,ctx.series,ctx.extended,{pointId:S.point,model:ctx.model,k:ctx.k});
    S.point=e.id;
    const el=id=>document.getElementById(id);
    const set=(id,html)=>{const n=el(id);if(n)n.innerHTML=html;};
    const po=el('pov-point');
    if(po) {
      const ids=(c.pois||[]).map(p=>p.id).join('|');
      if(po.dataset.ids!==ids) {
        po.innerHTML=(c.pois||[]).map(p=>`<option value="${escape(p.id)}">${label(p)} · ${escape(p.zona)}</option>`).join('');
        po.dataset.ids=ids;
      }
      po.value=e.id||'';
      if(!po.onchange) po.onchange=()=>{S.point=po.value;render(ctx);};
    }
    const off= e.officialOk ? '<strong class="pov-good">FUENTE OFICIAL DISPONIBLE</strong>' : '<strong class="pov-unk">UNKNOWN · sin comprobación oficial suficiente</strong>';
    const w=e.warnings.length?e.warnings.slice(0,15).map(x=>`<li><b>${escape(x.nivel)} · ${escape(x.evento)}</b> · ${escape(x.fuente||x.pais||'autoridad')} · ${escape(x.area||x.zona||'zona no indicada')} · ${stamp(x.desde)}–${stamp(x.hasta)}</li>`).join('')
      :(e.officialOk?'<li>Sin mensajes de nivel amarillo o superior en las zonas procesadas del ciclo; comprobar cobertura de fuentes.</li>':'<li>UNKNOWN: no interpretar la ausencia de mensajes como calma.</li>');
    set('pov-official',off+'<ul class="plain">'+w+'</ul>');
    const obs=e.observations;
    const ageCycle=utc(c.issued)?Math.round((Date.now()-utc(c.issued).getTime())/60000):null;
    const oldCycle=ageCycle==null||ageCycle>360||ageCycle< -10;
    set('pov-axes',grid([
      ['Avisos', e.officialOk?'Fuentes '+(source(c.fuentes?.aemet_cap,e.ages.aemet_cap)==='OK'?'AEMET':'disponibles'):'UNKNOWN'],
      ['Observación ≤90 min', obs.length?obs.length+' estaciones':'UNKNOWN'],
      ['Diagnóstico modelo',e.current.time?stamp(e.current.time):'UNKNOWN'],
      ['Antigüedad ciclo',ageCycle!=null&&ageCycle>=0?ageCycle+' min':'UNKNOWN'],
      ['Ciclo fresco ≤6 h',oldCycle?'NO · no concluir calma':'SÍ (no es vigilancia continua)'],
      ['Punto',e.station?.nombre||'UNKNOWN']
    ]));
    set('pov-evidence',`<p class="src">Las estaciones son observaciones; temperatura, precipitación, nieve y viento previstos son modelos. No se sustituye un aviso oficial por umbrales propios. En Pages la publicación es periódica, no vigilancia continua.</p>
    <div class="pov-mini">${grid([['Racha prevista',e.current.gust==null?'UNKNOWN':number(e.current.gust,0)+' km/h'],['Precipitación (bloque 3 h)',e.current.rain==null?'UNKNOWN':number(e.current.rain)+' mm'],['Nieve modelo (3 h)',e.current.snow==null?'UNKNOWN':number(e.current.snow)+' cm'],['Cota copo',e.snowAtPoint?.cota_copo_m==null?'UNKNOWN':number(e.snowAtPoint.cota_copo_m,0)+' m']])}</div>`);

    const atmos=Object.entries(e.profile).map(([side,p])=>`<tr><td>${side==='norte'?'Norte (Ariège/Capcir)':'Sur (Cerdanya)'}</td><td class="num">${number(p?.isocero_m,0)}</td><td class="num">${number(p?.tw0_m,0)}</td><td class="num">${number(p?.cota_copo_m,0)}</td><td class="num">${number(p?.viento700_kmh,0)}</td><td class="num">${escape(p?.flujo||'UNKNOWN')}</td><td class="num">${number(p?.froude,2)}</td></tr>`).join('');
    tbody(el('pov-atmos-rows'),atmos,7);
    set('pov-atmos-cards',grid([
      ['T / rocío', number(e.current.temperature)+' / '+number(e.current.dewpoint)+' °C'],
      ['Humedad',e.current.humidity==null?'UNKNOWN':number(e.current.humidity,0)+' %'],
      ['Nubosidad',e.current.cloud==null?'UNKNOWN':number(e.current.cloud,0)+' %'],
      ['Racha 10 m',e.current.gust==null?'UNKNOWN':number(e.current.gust,0)+' km/h'],
      ['Viento / dirección',e.current.wind==null?'UNKNOWN':number(e.current.wind,0)+' km/h'+(e.current.direction==null?' · dir UNKNOWN':' · '+number(e.current.direction,0)+'°')],
      ['Isocero en punto (modelo)',e.current.freezing==null?'UNKNOWN':number(e.current.freezing,0)+' m']
    ]));
    set('pov-atmos-note','Hora del modelo: '+stamp(e.current.time)+' · '+escape(c.modelo_nombre?.[e.model]||e.model||'UNKNOWN')+'. Perfil ARPEGE distinto de modelo del punto. La inversión y föhn están en Superficie.');
    const rs=(c.modelos||[]).map(m=>{const a=modelRow(c,e.id,m),cov=a.coverage||{};
      const check=(v,key)=>v==null?'UNKNOWN':(cov[key] && cov[key].complete===false ? 'UNKNOWN':number(v));
      return `<tr><td>${escape(c.modelo_nombre?.[m]||m)}</td><td class="num">${number(a.T)}</td><td class="num">${check(a.pr24,'precipitation:0-24h')}</td><td class="num">${check(a.nieve24_cm,'snowfall:0-24h')}</td><td class="num">${number(a.racha24,0)}</td><td>${escape(c.modelo_puntos||'UNKNOWN')}</td></tr>`;
    }).join('');
    tbody(el('pov-model-rows'),rs,6);
    const pt=ctx.series?.[e.id],rows=[];
    if(pt&&pt.time) for(let i=0;i<Math.min(12,pt.time.length);i++){
      const x=forecast(ctx.series,e.id,e.model,i);
      rows.push(`<tr><td>${stamp(x.time)}</td><td class="num">${number(x.temperature)}</td><td class="num">${number(x.rain)}</td><td class="num">${number(x.snow)}</td><td class="num">${number(x.gust,0)}</td><td class="num">${number(x.humidity,0)}</td><td class="num">${number(x.cloud,0)}</td></tr>`);
    }
    tbody(el('pov-model-timeline'),rows.join(''),7);
    set('pov-model-note','Modelo seleccionado: '+escape(c.modelo_nombre?.[e.model]||e.model||'UNKNOWN')+' · muestreo cada 3 h. Precipitación y nieve: suma de tres horas completas; si falta un elemento: UNKNOWN. Ninguna cifra equivale a probabilidad de impacto local.');
    const rev= e.revisions.length?e.revisions.length+' revisiones entre salidas, NO habilidad verificada':'UNKNOWN · sin comparativa de salidas';
    const sc=Object.entries(e.sidecars).map(([key,value])=>`<li>${escape(key)} · ${escape(value?.state||value?.status||'UNKNOWN')} · contexto informativo, no alerta</li>`).join('')||'<li>Sin contexto lateral validado</li>';
    const notes=(c.contexto?.notas_lluvia_24h||[]).slice(0,8).map(x=>'<li>'+escape(typeof x==='string'?x:JSON.stringify(x))+'</li>').join('');
    set('pov-forensic',`<div class="pov-mini">${grid([['Revisiones 15 d',rev],['Skill fuera de muestra','NO VERIFICADA'],['Archivo prospectivo','NO PUBLICADO (ledger privado)'],['Datos ausentes','UNKNOWN, nunca 0']])}</div><h3>Contexto y fuentes suplementarias</h3><ul class="plain">${sc}${notes}</ul><p class="src">Los cambios de una salida a otra no son errores contra observación. No hay CSI, POD, FAR, MAE o Brier válidos sin emparejamiento temporal y espacial, QC instrumental y pronóstico congelado.</p>`);
    const srcrows=Object.entries(e.sources).map(([name,value])=>`<tr><td>${escape(name)}</td><td>${escape(source(value,e.ages[name]))}</td><td class="num">${valid(e.ages[name])?number(e.ages[name],0)+' min':'—'}</td><td style="white-space:normal">${escape(String(value).slice(0,220))}</td></tr>`).join('');
    tbody(el('pov-source-rows'),srcrows,4);
    set('pov-governance',`<div class="pov-mini">${grid([['Ciclo UTC',c.issued||'UNKNOWN'],['Motorización',c.engine||'UNKNOWN'],['Permiso CNP',/PERMISSION_UNKNOWN/.test(e.sources.cnp||'')?'NO VERIFICADO':'Comprobar condiciones'],['Modelo ≠ aviso','Separación obligatoria'],['Alertas marinas','FUERA DE DOMINIO']])}</div><p class="src">Estado de cada conector por ciclo. «CACHED» indica respuesta almacenada, no observación recién medida; «UNKNOWN» no es ausencia de peligro. Los enlaces a boletines de aludes son referencias externas, no boletines integrados.</p>`);
    const slider=el('pov-wind-threshold');
    if(slider){
      slider.value=String(S.threshold);
      if(!slider.oninput) slider.oninput=()=>{S.threshold=Number(slider.value);render(ctx);};
    }
    const v=pt?.m?.[e.model]?.wind_gusts_10m, count=Math.min(8,pt?.time?.length||0);
    const wind=Array.isArray(v)?v.slice(0,8):[], all24=wind.length===8&&wind.every(valid);
    const exceed=all24?wind.filter(x=>x>=S.threshold).length:null;
    set('pov-lab-value',String(S.threshold)+' km/h');
    set('pov-lab-result',`<div class="pov-mini">${grid([['Umbral hipotético',S.threshold+' km/h'],['Bloques 3 h sobre umbral',all24?exceed+' de 8':'UNKNOWN · faltan intervalos'],['Duración de la señal',all24?(exceed*3)+' h muestreadas (no continuas)':'UNKNOWN'],['Modelo',c.modelo_nombre?.[e.model]||e.model||'UNKNOWN']])}</div><p class="src">Solo navegador. La racha disponible es una muestra del bloque de 3 h, no una vigilancia continua. Ningún ajuste cambia reglas, avisos, archivo forense o pronósticos publicados.</p>`);
  }
  const api={source,derive,forecast,nearest,render};
  if(typeof module==='object' && module.exports) module.exports=api;
  if(root) root.PirineoObservatory=api;
})(typeof window!=='undefined'?window:null);
