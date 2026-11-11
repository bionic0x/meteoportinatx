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
console.log(`PASS ${n} decision tests`);
