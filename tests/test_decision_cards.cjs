// Regression: no stale/future data presented as live, all five personas isolated.
const assert = require('node:assert/strict');
const M = require('../src/decision_cards.js');
const NOW = Date.parse('2026-11-11T10:00:00Z');
const issued = '2026-11-11T09:40:00Z';
const base = () => ({
  issued, source_secret: 'SECRET_OWNER_QUOTE',
  official: {verificado: true, level_now: 'alert', all: [{activo: true, evento: 'Lluvias intensas', nivel: 'naranja'}], private: 'SECRET_OWNER_QUOTE'},
  precaution: {level: 'watch', decision: {reason: 'SECRET_OWNER_QUOTE'}},
  hazard: {
    lluvia_pluviometros: {estado: 'OBSERVED', nivel: 'alert', local: true},
    lluvia_metar_aemet: {estado: 'OBSERVED', nivel: 'quiet'},
    radar: {estado: 'UNKNOWN', nivel: 'quiet'},
    rayos: {estado: 'OBSERVED', nivel: 'watch'},
    viento: {estado: 'OBSERVED', nivel: 'watch'},
    mar: {estado: 'OBSERVED', nivel: 'alert'},
    runoff: {estado: 'OBSERVED', nivel: 'alarm', private: 'SECRET_OWNER_QUOTE'}
  }
});
const mountain = () => ({
  issued, fuentes: {avisos: 'ok · MeteoAlarm'},
  avisos: [{vigente: true, evento: 'Nieve'},{vigente: false, evento: 'Otro'}],
  modelo_nombre: 'mejor',
  puntos: [
    {id:'font_romeu',modelos:{meteofrance_arome_france_hd:{nieve24_cm:6,racha24:52,T:-4,pr24:11}}},
    {id:'les_angles',modelos:{icon_eu:{nieve24_cm:9,racha24:37,T:-3,pr24:13}}}
  ]
});
let n = 0;function test(name,fn){fn();n++;console.log('PASS',name)}
test('five profiles configured, route domains explicit',()=>{
  assert.deepEqual(Object.keys(M.profiles),['casa','barca','residencia','esqui','meteo']);
  assert.equal(M.profiles.casa.domain,'portinatx');assert.equal(M.profiles.residencia.domain,'pirineo');
});
test('homeowner sees both actual rain hazard channels, no private text',()=>{
  const x = M.project('casa',base(),'snapshot','font_romeu',NOW);
  assert.equal(x.state,'recent');assert.equal(x.observed[0].key,'lluvia_pluviometros');
  assert.equal(x.observed[1].key,'lluvia_metar_aemet');
  assert.equal(x.observed[0].kind,'observed');assert.equal(x.observed[2].kind,'unknown');
  assert.match(x.official.title,/alert/);assert.match(x.operational.title,/watch/);
  assert.doesNotMatch(JSON.stringify(x),/SECRET_OWNER_QUOTE/);
});
test('boater sees only measured wind/sea/lightning with uncertainty',()=>{
  const x=M.project('barca',base(),'backend','font_romeu',NOW);
  assert.deepEqual(x.observed.map(e=>e.key),['viento','mar','rayos']);
  assert.equal(x.operational,null);
});
test('meteorologist sees measured axes and no invented calibrated probability',()=>{
  const x=M.project('meteo',base(),'snapshot','font_romeu',NOW);
  assert.equal(x.observed.length,6);assert.equal(x.forecast,null);
  assert.match(x.guidance,/no están calibradas/);
});
test('old and future coastal cycle suppress all operational results',()=>{
  for(const value of ['2026-11-11T07:10:00Z','2026-11-11T10:30:00Z']){
    const x=M.project('casa',{...base(),issued:value},'snapshot','font_romeu',NOW);
    assert.equal(x.available,false);assert.equal(x.observed.length,0);assert.equal(x.operational,null);
    assert.equal(x.official.kind,'unknown');assert.notEqual(x.heading,'Sin peligro');
  }
});
test('missing/invalid issue timestamp never becomes calm',()=>{
  const x=M.project('barca',{...base(),issued:'2026-11-11T09:59:59'},'backend','font_romeu',NOW);
  assert.equal(x.state,'unknown');assert.equal(x.available,false);
});
test('unverified coast institutional provider is UNKNOWN',()=>{
  const c=base();c.official.verificado=false;
  const x=M.project('casa',c,'backend','font_romeu',NOW);
  assert.equal(x.official.kind,'unknown');assert.match(x.official.title,/no verificado/i);
});
test('residence uses selected place/model, no fabricated measurement',()=>{
  const x=M.project('residencia',mountain(),'snapshot','font_romeu',NOW);
  assert.equal(x.available,true);assert.equal(x.forecast.snow24,6);
  assert.equal(x.forecast.place,'Font-Romeu');assert.match(x.heading,/Estimación/);
  assert.equal(x.official.kind,'official');
});
test('ski changes point and does not silently use another station',()=>{
  const x=M.project('esqui',mountain(),'snapshot','les_angles',NOW);
  assert.equal(x.forecast.snow24,9);assert.equal(x.forecast.place,'Les Angles');
  const missing=M.project('esqui',mountain(),'snapshot','masella',NOW);
  assert.equal(missing.forecast,null);assert.match(missing.heading,/no disponible/);
});
test('mountain warnings unknown when source is not verified',()=>{
  const x=mountain();x.fuentes.avisos='error: HTTPError';
  assert.equal(M.project('residencia',x,'snapshot','font_romeu',NOW).official.kind,'unknown');
});
test('old mountain snapshot suppresses numerical snow values',()=>{
  const x=M.project('esqui',{...mountain(),issued:'2026-11-10T23:00:00Z'},'snapshot','font_romeu',NOW);
  assert.equal(x.state,'stale');assert.equal(x.forecast,null);
});
test('missing point or NaN is not converted to zero',()=>{
  const x=mountain();x.puntos[0].modelos.meteofrance_arome_france_hd.nieve24_cm=null;
  assert.equal(M.project('residencia',x,'snapshot','font_romeu',NOW).forecast.snow24,null);
});
test('invalid profile cannot render arbitrary input',()=>{
  assert.throws(()=>M.project('__proto__',base(),'snapshot','font_romeu',NOW),TypeError);
});
test('H1: missing rain coverage cannot look like an operational quiet verdict',()=>{
  const x=base();x.precaution={level:'quiet',insufficient:true,rain_coverage:'0/3'};
  for (const k of ['lluvia_pluviometros','lluvia_metar_aemet','radar']) x.hazard[k]={estado:'UNKNOWN',nivel:'—'};
  const p=M.project('casa',x,'snapshot','font_romeu',NOW);
  assert.equal(p.operational,null);assert.match(p.heading,/lluvia insuficiente/i);
  assert.equal(p.official.kind,'official');
});
test('#18: official card says when AEMET CAP is missing',()=>{
  const x=base();x.official.fuente_oficial='SOLO_METEOALARM';
  assert.match(M.project('casa',x,'snapshot','font_romeu',NOW).official.detail,/solo MeteoAlarm/);
  const y=base();y.official.fuente_oficial='AEMET_CAP+METEOALARM';
  assert.doesNotMatch(M.project('casa',y,'snapshot','font_romeu',NOW).official.detail,/MeteoAlarm/);
});
test('#8: point reports its slope snow level and freezing-rain risk; unknown stays null',()=>{
  const x=mountain();
  x.puntos[0].cotas={estado:'OK',vertiente:'sur',cota_copo_m:1500,sobre_cota_copo:true,riesgo_engelante:true};
  const f=M.project('esqui',x,'snapshot','font_romeu',NOW).forecast;
  assert.equal(f.snowLevel,1500);assert.equal(f.side,'sur');assert.equal(f.aboveSnowLevel,true);assert.equal(f.freezingRain,true);
  x.puntos[0].cotas={estado:'UNKNOWN',vertiente:'sur',cota_copo_m:null,sobre_cota_copo:null};
  const g=M.project('esqui',x,'snapshot','font_romeu',NOW).forecast;
  assert.equal(g.snowLevel,null);assert.equal(g.aboveSnowLevel,null);assert.equal(g.freezingRain,false);
});
// ── «Investigar el episodio»: ficha de un ciclo, solo desde core.json ──
const episodeCore = () => ({...base(), cycle_id: 'NWC-20261111T094000Z', engine: '0.6.1', history: [{id: 'a'}],
  official: {verificado: true, level_now: 'watch', fuente_oficial: 'AEMET_CAP+METEOALARM', all: [
    {nivel: 'amarillo', tipo: 'terrestre', evento: 'Aviso de vientos', desde: '2026-11-11T08:00:00+01:00', hasta: '2026-11-11T20:00:00+01:00', activo: true, umbral: 'Rachas 70 km/h', private: 'SECRET_OWNER_QUOTE'},
    {nivel: 'amarillo', tipo: 'terrestre', evento: 'Aviso de vientos', desde: '2026-11-11T08:00:00+01:00', hasta: '2026-11-11T20:00:00+01:00', activo: true, umbral: 'Rachas 70 km/h'},
    {nivel: 'naranja', tipo: 'costero', evento: 'Aviso ya vencido', desde: '2026-11-11T00:00:00+01:00', hasta: '2026-11-11T09:00:00+01:00', activo: true},
    {nivel: 'verde', tipo: 'terrestre', evento: 'Futuro', desde: '2026-11-12T00:00:00+01:00', hasta: '2026-11-12T23:00:00+01:00', activo: false}]},
  channels: [
    {name: 'radar', level: 1, kind: 'obs', available: true, age_min: 7, evidence: ['eco más cercano 55 km', 'MOTION_UNKNOWN']},
    {name: 'rayos', level: 0, kind: 'obs', available: false, age_min: null, evidence: ['rayos no disponibles (sin_clave)']},
    {name: 'mar_boyas', level: 0, kind: 'obs', available: true, age_min: -1, evidence: ['Boya: Hs 1.88 m, Hmax nan m']},
    {name: 'lluvia_observada', level: 0, kind: 'obs', available: true, age_min: 7, evidence: ['METAR 2330Z METAR LEIB 102330Z AUTO CAVOK']},
    {name: 'modelo_icon_eu', level: 1, kind: 'model', available: true, age_min: -1, evidence: ['punto: máx 0.0 mm/1h · racha 66 km/h · CAPE 700 J/kg']},
    {name: 'modelo_ecmwf_ifs025', level: 1, kind: 'model', available: true, age_min: -1, evidence: ['1 horas sin valor', 'punto: máx 0.0 mm/1h · racha 62 km/h · CAPE 1130 J/kg']},
    {name: 'ensemble_ecmwf', level: 0, kind: 'ensemble', available: true, evidence: ['51 miembros · P(24h≥50)=0% · P(1h≥30)=0%']},
    {name: 'manual', level: 3, kind: 'obs', available: true, evidence: ['SECRET_OWNER_QUOTE']},
    {name: 'canal_futuro', level: 2, kind: 'obs', available: true, evidence: ['SECRET_OWNER_QUOTE']},
    {name: 'viento_estaciones', level: 0, kind: 'obs', available: true, age_min: 3, evidence: ['observación manual del propietario: SECRET_OWNER_QUOTE', 'Puerto: racha 50 km/h']}],
  nowcast: {level: 'watch', transition: 'ESCALADA quiet→watch', reasons: ['anegamiento observado (manual) → alarm', 'suelo institucional = watch', 'radar=watch', 'manual=alarm', 'texto libre SECRET_OWNER_QUOTE']},
  outlook: {level: 'watch', reasons: ['modelo_icon_eu=watch', 'radar=watch']},
  precaution: {level: 'watch', insufficient: false, rain_coverage: '3/3', hold: 'SECRET_OWNER_QUOTE', exit_conditions: ['SECRET_OWNER_QUOTE'], decision: {overridden: [{motivo: 'SECRET_OWNER_QUOTE'}]}},
  sources: [{name: 'radar', status: 'ok', detail: 'SECRET_OWNER_QUOTE'}, {name: 'rayos_mtg_li', status: 'sin_clave', detail: 'EUMETSAT_KEY'}, {name: 'radar_hf', status: 'error', detail: 'RuntimeError https://x'}, {name: '<b>x</b>', status: 'error'}],
  governance: {claims: [
    {id: 'C-OFF0', text: 'AEMET mantiene aviso', epistemic: 'EVIDENCE', source_root: 'aemet'},
    {id: 'C-OFF2', text: 'AEMET mantiene aviso', epistemic: 'EVIDENCE', source_root: 'aemet'},
    {id: 'C-man-1', text: 'SECRET_OWNER_QUOTE', epistemic: 'EVIDENCE', source_root: 'owner', label: 'OWNER'},
    {id: 'C-1', text: 'modelo', epistemic: 'HYPOTHESIS', source_root: 'nwp'}],
    dissent: ['SECRET_OWNER_QUOTE'], anomalies: ['SECRET_OWNER_QUOTE'], overrides: {x: 'SECRET_OWNER_QUOTE'},
    episode: {closure_record: 'SECRET_OWNER_QUOTE'}}
});
test('episode: only the meteo profile gets it, and the six hazard axes stay',()=>{
  const x=M.project('meteo',episodeCore(),'snapshot','font_romeu',NOW);
  assert.ok(x.episode);assert.equal(x.observed.length,6);
  for(const p of ['casa','barca'])assert.equal(M.project(p,episodeCore(),'snapshot','font_romeu',NOW).episode,null);
  assert.equal(M.project('esqui',mountain(),'snapshot','font_romeu',NOW).episode,undefined);
});
test('episode: owner text, manual channels and unknown channels never surface',()=>{
  const x=M.project('meteo',episodeCore(),'snapshot','font_romeu',NOW);
  assert.doesNotMatch(JSON.stringify(x),/SECRET_OWNER_QUOTE|EUMETSAT_KEY|RuntimeError|manual|propietario|<b>/);
  const all=[...x.episode.measured,...x.episode.models,...x.episode.ensemble].map(r=>r.name);
  assert.ok(!all.includes('manual')&&!all.includes('canal_futuro'));
  assert.deepEqual(x.episode.measured.find(r=>r.name==='viento_estaciones').evidence,['Puerto: racha 50 km/h']);
});
test('episode: unavailable channel is no data, never level 0',()=>{
  const e=M.project('meteo',episodeCore(),'snapshot','font_romeu',NOW).episode;
  const rayos=e.measured.find(r=>r.name==='rayos');
  assert.equal(rayos.status,'nodata');assert.equal(rayos.level,null);assert.match(rayos.levelLabel,/no equivale a calma/);
  assert.deepEqual(e.counts,{total:5,available:4,signal:1,nodata:1});
  assert.equal(e.measured[0].name,'radar');   // la señal primero, después lo que no se ve
});
test('episode: negative or model ages are not printed as minutes',()=>{
  const e=M.project('meteo',episodeCore(),'snapshot','font_romeu',NOW).episode;
  const buoy=e.measured.find(r=>r.name==='mar_boyas');
  assert.equal(buoy.ageMin,null);assert.equal(buoy.justMeasured,true);
  assert.equal(e.models[0].ageMin,null);assert.equal(e.models[0].justMeasured,false);
});
test('episode: warnings deduplicated, expired dropped, level literal, later counted',()=>{
  const w=M.project('meteo',episodeCore(),'snapshot','font_romeu',NOW).episode.warnings;
  assert.equal(w.verified,true);assert.equal(w.items.length,1);assert.equal(w.items[0].level,'amarillo');
  assert.equal(w.items[0].threshold,'Rachas 70 km/h');assert.equal(w.expired,1);assert.equal(w.later,1);
  const c=episodeCore();c.official.verificado=false;
  const u=M.project('meteo',c,'snapshot','font_romeu',NOW).episode.warnings;
  assert.equal(u.verified,false);assert.equal(u.items.length,0);
});
test('episode: a hand-entered floor is never listed as the authority\'s warning',()=>{
  const c=episodeCore();c.official.all.push({nivel:'naranja',tipo:'terrestre',evento:'aviso introducido a mano',desde:'',hasta:'',activo:true,umbral:'verificado por el usuario'});
  const w=M.project('meteo',c,'snapshot','font_romeu',NOW).episode.warnings;
  assert.equal(w.items.length,1);assert.equal(w.byHand,1);assert.doesNotMatch(JSON.stringify(w.items),/a mano|usuario|naranja/);
});
test('episode: incoherent or zoneless official data never reads as no warnings',()=>{
  const c=episodeCore();c.official.all='roto';
  assert.equal(M.project('meteo',c,'snapshot','font_romeu',NOW).episode.warnings.verified,false);
  const d=episodeCore();d.official.all=[];d.official.level_now='alert';
  assert.equal(M.project('meteo',d,'snapshot','font_romeu',NOW).episode.warnings.verified,false);
  const q=episodeCore();q.official.all=[];q.official.level_now='quiet';
  assert.equal(M.project('meteo',q,'snapshot','font_romeu',NOW).episode.warnings.verified,true);
  const z=episodeCore();z.official.all=[{nivel:'amarillo',tipo:'t',evento:'Sin zona',desde:'2026-11-11T08:00:00',hasta:'2026-11-11T20:00:00',activo:true}];
  assert.equal(M.project('meteo',z,'snapshot','font_romeu',NOW).episode.warnings.items[0].until,null);
  const m=episodeCore();m.official.fuente_oficial='SOLO_METEOALARM';
  assert.equal(M.project('meteo',m,'snapshot','font_romeu',NOW).episode.warnings.source,'MeteoAlarm');
});
test('episode: a channel is available only when the engine says so',()=>{
  for(const value of [undefined,null,0,'false','true']){
    const c=episodeCore();c.channels[0]={name:'radar',level:0,kind:'obs',available:value,age_min:-1,evidence:[]};
    const r=M.project('meteo',c,'snapshot','font_romeu',NOW).episode.measured.find(x=>x.name==='radar');
    assert.equal(r.status,'nodata');assert.equal(r.level,null);assert.equal(r.justMeasured,false);
  }
});
test('episode: a METAR across midnight is current, an old one is flagged',()=>{
  const c=episodeCore();
  c.channels[3].evidence=['METAR LEIB 110920Z AUTO','METAR LEIB 102350Z AUTO','METAR LEIB 110100Z AUTO'];
  const ev=M.project('meteo',c,'snapshot','font_romeu',NOW).episode.measured.find(r=>r.name==='lluvia_observada').evidence;
  assert.doesNotMatch(ev[0],/no es actual/);assert.match(ev[1],/no es actual/);assert.match(ev[2],/no es actual/);
  const n=episodeCore();n.issued='2026-11-11T00:20:00Z';n.channels[3].evidence=['METAR LEIB 102350Z AUTO'];
  assert.doesNotMatch(M.project('meteo',n,'snapshot','font_romeu',Date.parse('2026-11-11T00:30:00Z')).episode.measured.find(r=>r.name==='lluvia_observada').evidence[0],/no es actual/);
});
test('episode: ensemble fractions are never written as P(), engine artefacts are cleaned',()=>{
  const e=M.project('meteo',episodeCore(),'snapshot','font_romeu',NOW).episode;
  assert.doesNotMatch(JSON.stringify(e),/P\(|\bnan\b|MOTION_UNKNOWN/);
  assert.match(e.ensemble[0].evidence[0],/0 % de miembros ≥50 mm\/24 h/);
  assert.match(e.measured.find(r=>r.name==='lluvia_observada').evidence[0],/hace más de 6 h/);
});
test('episode: engine reasons are allow-listed and a cold start shows no transition',()=>{
  const g=M.project('meteo',episodeCore(),'snapshot','font_romeu',NOW).episode.engine;
  assert.deepEqual(g.now.reasons,[{kind:'floor',level:'seguimiento'},{kind:'channel',label:'Radar',level:'seguimiento'}]);
  assert.equal(g.now.hidden,3);assert.equal(g.comparable,false);assert.equal(g.change,null);
  const c=episodeCore();c.history=[{id:'a'},{id:'b'}];
  assert.deepEqual(M.project('meteo',c,'snapshot','font_romeu',NOW).episode.engine.change,{up:true,from:'sin señal destacada en este canal',to:'seguimiento'});
});
test('episode: model spread only when every model parses; no average',()=>{
  const e=M.project('meteo',episodeCore(),'snapshot','font_romeu',NOW).episode;
  assert.deepEqual(e.spread.gust,{min:62,minModel:'ECMWF',max:66,maxModel:'ICON'});assert.equal(e.spread.cape.max,1130);
  const c=episodeCore();c.channels[4].evidence=['punto: sin datos (¿fuera de dominio?)'];
  assert.equal(M.project('meteo',c,'snapshot','font_romeu',NOW).episode.spread,null);
});
test('episode: sources and claims are counted without free text',()=>{
  const e=M.project('meteo',episodeCore(),'snapshot','font_romeu',NOW).episode;
  assert.deepEqual(e.sources,{total:3,ok:1,failing:[{name:'rayos_mtg_li',state:'sin credencial configurada',error:false},{name:'radar_hf',state:'falló en esta actualización',error:true}]});
  assert.deepEqual(e.claims,{evidence:1,hypothesis:1,assumption:0,unknown:0,total:2,deduplicated:true});
});
test('episode: backend projection without evidence or reasons degrades, never invents',()=>{
  const c=episodeCore();c.channels=c.channels.map(x=>({...x,evidence:[]}));c.nowcast={level:'watch'};c.outlook={level:'watch',reasons:[]};
  c.governance={claims:[]};c.sources=[];
  const e=M.project('meteo',c,'backend','font_romeu',NOW).episode;
  assert.equal(e.measured[0].evidencePublished,false);assert.equal(e.spread,null);assert.equal(e.claims,null);
  assert.equal(e.engine.now.published,false);assert.equal(e.engine.now.levelLabel,'seguimiento');assert.equal(e.sources.total,0);
  const empty=M.project('meteo',base(),'snapshot','font_romeu',NOW).episode;
  assert.equal(empty.counts.total,0);assert.equal(empty.engine.now.level,null);
});
test('episode: stale or insufficient cycles expose no values or level',()=>{
  assert.equal(M.project('meteo',{...episodeCore(),issued:'2026-11-11T07:10:00Z'},'snapshot','font_romeu',NOW).episode,undefined);
  const c=episodeCore();c.precaution.insufficient=true;
  assert.equal(M.project('meteo',c,'snapshot','font_romeu',NOW).episode.engine.insufficient,true);
});
console.log(`PASS ${n} decision tests`);
