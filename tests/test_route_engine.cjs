// Contrato del motor de ruta. Datos 100 % sintéticos: no hay red ni pronóstico real.
'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const E = require(path.join(__dirname, '../src/route_engine.js'));

let passed = 0;
function test(name, fn) {
  try { fn(); passed++; } catch (e) { console.error('FAIL', name); throw e; }
}
const close = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol, `${msg || ''} ${a} vs ${b} (±${tol})`);

// ── utilidades de fixtures ──
const LATS = [], LONS = [];
for (let i = 0; i < 8; i++) LATS.push(+(42.30 + 0.05 * i).toFixed(2));
for (let j = 0; j < 16; j++) LONS.push(+(1.45 + 0.05 * j).toFixed(2));
const TIMES = [];
for (let k = 0; k < 16; k++) TIMES.push(new Date(Date.UTC(2026, 10, 11, 3 * k)).toISOString().slice(0, 16));   // paso 3 h
const T0 = Date.UTC(2026, 10, 11, 0);
const HOUR = 3.6e6;

function makeGrid(fn) {    // fn(name, lat, lon, k) → valor; elev = 1500 en todas las celdas salvo que se indique
  const fields = {};
  for (const name of ['temperature_2m', 'dew_point_2m', 'precipitation', 'wind_gusts_10m', 'wind_speed_10m', 'freezing_level_height']) {
    fields[name] = TIMES.map((_, k) => { const row = []; for (const la of LATS) for (const lo of LONS) row.push(fn(name, la, lo, k)); return row; });
  }
  const elev = []; for (const la of LATS) for (const lo of LONS) elev.push(fn('elev', la, lo, 0));
  return { modelo: 'sintético', paso_h: 3, lats: LATS, lons: LONS, time: TIMES, fields, elev };
}
const calm = (name) => ({ temperature_2m: 8, dew_point_2m: 2, precipitation: 0, wind_gusts_10m: 15, wind_speed_10m: 8, freezing_level_height: 2600, elev: 1500 })[name];

function gpx(points, { ele = true, time = false, attrsSingle = false } = {}) {
  const q = attrsSingle ? "'" : '"';
  const pts = points.map((p, i) => `<trkpt lon=${q}${p[1]}${q} lat=${q}${p[0]}${q}>${ele && p[2] !== undefined ? `<ele>${p[2]}</ele>` : ''}${time ? `<time>${new Date(T0 + i * 60000).toISOString()}</time>` : ''}</trkpt>`);
  return `<?xml version="1.0"?><gpx version="1.1"><trk><name>Prueba</name><trkseg>${pts.join('')}</trkseg></trk></gpx>`;
}
// Línea recta hacia el norte desde (42.40, 1.60), con rampa de altitud
function line(n, dLat, z0, z1, lon = 1.60) {
  const out = [];
  for (let i = 0; i < n; i++) out.push([+(42.40 + dLat * i).toFixed(6), lon, +(z0 + (z1 - z0) * i / (n - 1)).toFixed(1)]);
  return out;
}

// ── GPX ──
test('parseGPX: orden de atributos, comillas simples y campos opcionales', () => {
  const r = E.parseGPX(gpx([[42.4, 1.6, 1500], [42.41, 1.6, 1510]], { attrsSingle: true }));
  assert.equal(r.points.length, 2); assert.equal(r.points[0].ele, 1500); assert.equal(r.points[0].t, null); assert.equal(r.name, 'Prueba');
  const r2 = E.parseGPX('<gpx><trk><trkseg><trkpt lat="42.4" lon="1.6"/><trkpt lat="42.41" lon="1.6"></trkpt></trkseg></trk></gpx>');
  assert.equal(r2.points.length, 2); assert.equal(r2.points[1].ele, null);
});
test('parseGPX: ruta planificada, descarte de coordenadas inválidas y rechazos', () => {
  const rte = E.parseGPX('<gpx><rte><rtept lat="42.4" lon="1.6"/><rtept lat="42.5" lon="1.6"/><rtept lat="95" lon="1.6"/></rte></gpx>');
  assert.equal(rte.kind, 'ruta'); assert.equal(rte.points.length, 2); assert.ok(rte.warnings.length >= 2);
  assert.throws(() => E.parseGPX('<!DOCTYPE x [<!ENTITY a "b">]><gpx></gpx>'), /DOCTYPE/);
  assert.throws(() => E.parseGPX(''), /vac/);
  assert.throws(() => E.parseGPX('<gpx><trk><trkseg><trkpt lat="42.4" lon="1.6"/></trkseg></trk></gpx>'), /al menos 2/);
  assert.throws(() => E.parseGPX('x'.repeat(E.LIMITS.maxChars + 1)), /grande/);
});
test('parseGPX: tiempos ISO y tiempo inválido → null', () => {
  const r = E.parseGPX('<gpx><trkpt lat="42.4" lon="1.6"><time>2026-11-11T08:00:00Z</time></trkpt><trkpt lat="42.41" lon="1.6"><time>basura</time></trkpt></gpx>');
  assert.equal(r.points[0].t, Date.UTC(2026, 10, 11, 8)); assert.equal(r.points[1].t, null);
});

// ── preparación del track ──
test('prepareTrack: longitud, remuestreo, extremos y desnivel (el ruido GPS no suma)', () => {
  const pts = line(31, 0.001, 1000, 1300);                 // 3,336 km, +300 m
  pts.forEach((p, i) => { p[2] += (i % 2 ? 1.5 : -1.5); }); // ruido ±1,5 m
  const prep = E.prepareTrack(E.parseGPX(gpx(pts)));
  close(prep.totalM, 30 * 111.19, 2, 'longitud');
  assert.equal(prep.samples[0].d, 0); close(prep.samples[prep.samples.length - 1].d, prep.totalM, 1e-6);
  assert.equal(prep.eleSource, 'track');
  close(prep.ascentM, 300, 12, 'ascenso'); assert.ok(prep.descentM < 10);
  assert.ok(prep.samples.length >= Math.floor(prep.totalM / 200));
});
test('prepareTrack: sin altitud usa el DEM; sin DEM queda sin altitud; muy corto se rechaza', () => {
  const dem = { at: (la) => 1000 + (la - 42.4) * 10000 };
  const noEle = E.parseGPX(gpx(line(11, 0.001, 0, 0), { ele: false }));
  const p1 = E.prepareTrack(noEle, { dem }); assert.equal(p1.eleSource, 'dem'); assert.ok(p1.ascentM > 80);
  const p2 = E.prepareTrack(noEle); assert.equal(p2.eleSource, 'ninguna'); assert.equal(p2.samples[0].ele, null);
  assert.throws(() => E.prepareTrack(E.parseGPX(gpx([[42.4, 1.6], [42.4003, 1.6]]))), /100 m/);
  assert.throws(() => E.prepareTrack(E.parseGPX(gpx([[42.4, 1.6], [42.4, 1.6]]))), /movimiento/);
});

// ── ritmo ──
test('Tobler: llano ≈ 5,04 km/h, máximo en ligera bajada, y el factor escala el tiempo', () => {
  close(E.toblerKmh(0), 6 * Math.exp(-0.175), 1e-9);
  assert.ok(E.toblerKmh(-0.05) > E.toblerKmh(0) && E.toblerKmh(-0.05) > E.toblerKmh(-0.3));
  assert.ok(E.toblerKmh(0.3) < E.toblerKmh(0));
  const prep = E.prepareTrack(E.parseGPX(gpx(line(46, 0.001, 1500, 1500))));      // 5,0 km llanos
  const a = E.elapsedSeconds(prep, { factor: 1 }).tau, b = E.elapsedSeconds(prep, { factor: 0.5 }).tau;
  const dist = prep.totalM / 1000;
  close(a[a.length - 1], dist / (6 * Math.exp(-0.175)) * 3600, 5);
  close(b[b.length - 1] / a[a.length - 1], 2, 1e-9);
  const c = E.elapsedSeconds(prep, { factor: 1, breakMinPerHour: 6 }).tau;
  close(c[c.length - 1] / a[a.length - 1], 1.1, 1e-9);
  assert.ok(a.every((x, i) => i === 0 || x > a[i - 1]));
});
test('ritmo del track: reproduce los tiempos grabados; sin tiempos cae a Tobler', () => {
  const withT = E.prepareTrack(E.parseGPX(gpx(line(31, 0.001, 1500, 1500), { time: true })));
  assert.equal(withT.hasTimes, true);
  const r = E.elapsedSeconds(withT, { pace: 'track' });
  assert.equal(r.method, 'track'); close(r.tau[r.tau.length - 1], 30 * 60, 1.5);
  const noT = E.prepareTrack(E.parseGPX(gpx(line(31, 0.001, 1500, 1500))));
  assert.equal(E.elapsedSeconds(noT, { pace: 'track' }).method, 'tobler');
});

// ── rejilla ──
test('createGrid: valida forma, ejes y campos obligatorios', () => {
  const g = makeGrid(calm);
  assert.doesNotThrow(() => E.createGrid(g));
  const bad = (m) => { const x = JSON.parse(JSON.stringify(g)); m(x); return x; };
  assert.throws(() => E.createGrid(bad((x) => { delete x.fields.precipitation; })), /precipitation/);
  assert.throws(() => E.createGrid(bad((x) => { x.fields.temperature_2m[0].pop(); })), /inconsistente/);
  assert.throws(() => E.createGrid(bad((x) => { x.lats.reverse(); })), /crecientes/);
  assert.throws(() => E.createGrid(bad((x) => { x.time[3] = x.time[2]; })), /crecientes/);
  assert.throws(() => E.createGrid(bad((x) => { x.elev.pop(); })), /Altitudes/);
  assert.throws(() => E.createGrid(null), /inválida/);
});
test('sampleGrid: interpolación bilineal en espacio y lineal en tiempo exacta para campos lineales', () => {
  const lin = (n, la, lo, k) => n === 'temperature_2m' ? 5 + 10 * (la - 42.30) + 2 * (lo - 1.45) + 0.4 * k : calm(n);
  const G = E.createGrid(makeGrid(lin));
  const s = E.sampleGrid(G, 42.4137, 1.7311, T0 + 4.2 * HOUR);
  assert.equal(s.estado, 'ok');
  close(s.t2m, 5 + 10 * (42.4137 - 42.30) + 2 * (1.7311 - 1.45) + 0.4 * (4.2 / 3), 1e-9);
  assert.equal(E.sampleGrid(G, 42.20, 1.6, T0).estado, 'fuera_dominio');
  assert.equal(E.sampleGrid(G, 42.4, 2.5, T0).estado, 'fuera_dominio');
  assert.equal(E.sampleGrid(G, 42.4, 1.6, T0 - HOUR).estado, 'fuera_horizonte');
  assert.equal(E.sampleGrid(G, 42.4, 1.6, T0 + 46 * HOUR).estado, 'fuera_horizonte');
  assert.equal(E.sampleGrid(G, 42.65, 2.20, T0 + 9 * HOUR).estado, 'ok', 'esquina del dominio incluida');
});
test('sampleGrid: la precipitación de 3 h cubre (tk−1 h, tk+2 h] y se reparte en mm/h', () => {
  const G = E.createGrid(makeGrid((n, la, lo, k) => n === 'precipitation' ? (k === 0 ? 3 : k === 1 ? 6 : 0) : calm(n)));
  close(E.sampleGrid(G, 42.4, 1.6, T0 + 0.5 * HOUR).pr, 1, 1e-12);
  close(E.sampleGrid(G, 42.4, 1.6, T0 + 2 * HOUR).pr, 1, 1e-12, 'límite superior incluido');
  close(E.sampleGrid(G, 42.4, 1.6, T0 + 2.01 * HOUR).pr, 2, 1e-12, 'siguiente bloque');
  close(E.sampleGrid(G, 42.4, 1.6, T0 + 8 * HOUR).pr, 0, 1e-12);
});
test('sampleGrid: esquina sin dato → variable nula (no se rellena con ceros) y racha = máximo contiguo', () => {
  const raw = makeGrid((n, la, lo, k) => n === 'wind_gusts_10m' ? (k === 0 ? 20 : 70) : calm(n));
  raw.fields.temperature_2m[0][0] = null;                    // celda (42.30, 1.45)
  const G = E.createGrid(raw);
  assert.equal(E.sampleGrid(G, 42.31, 1.46, T0 + HOUR).t2m, null);
  assert.notEqual(E.sampleGrid(G, 42.55, 1.9, T0 + HOUR).t2m, null);
  assert.equal(E.sampleGrid(G, 42.5, 1.9, T0 + HOUR).gust, 70);
});

// ── física ──
test('tempAtAltitude: usa la cota de 0 °C si el gradiente es creíble; si no, 6,5 K/km y perfil incierto', () => {
  const a = E.tempAtAltitude(5, 1500, 2500, 2000);
  assert.equal(a.method, 'isocero'); close(a.lapse, 5, 1e-9); close(a.t, 2.5, 1e-9);
  const b = E.tempAtAltitude(-3, 1500, 2000, 2000);          // inversión: gradiente negativo → descartado
  assert.equal(b.method, 'estandar'); close(b.t, -3 - 6.5 * 0.5, 1e-9); assert.equal(b.uncertain, true);
  const c = E.tempAtAltitude(5, 1500, 3500, 2000);           // 2,5 K/km: fuera de 3–9
  assert.equal(c.method, 'estandar');
  assert.equal(E.tempAtAltitude(5, 1500, 2500, 1500).method, 'celda');
  assert.equal(E.tempAtAltitude(null, 1500, 2500, 2000), null);
  const d = E.tempAtAltitude(-2, 2000, 1500, 2500);          // celda por encima de la isocero
  assert.equal(d.method, 'isocero'); close(d.lapse, 4, 1e-9);
});
test('solidFraction: rampa centrada en 0,7 °C de bulbo húmedo, monótona y acotada', () => {
  close(E.solidFraction(0.7, 0.7, 0), 0.5, 1e-6);            // saturado: Tw = T
  assert.equal(E.solidFraction(-3, -4, 1800), 1); assert.equal(E.solidFraction(6, 4, 1800), 0);
  let prev = 1; for (let t = -4; t <= 6; t += 0.5) { const f = E.solidFraction(t, t - 1, 1800); assert.ok(f <= prev + 1e-12); prev = f; }
  assert.equal(E.solidFraction(null, 0, 1800), 0);
  assert.ok(E.solidFraction(1.5, -4, 1800) > E.solidFraction(1.5, 1.4, 1800), 'aire seco: más nieve a igual T');
});
test('sensación térmica y clases', () => {
  const wc = E.windChill(-10, 30); assert.ok(wc < -18 && wc > -21);
  assert.equal(E.windChill(12, 50), 12); assert.equal(E.windChill(-5, 3), -5); assert.equal(E.windChill(-5, null), null);
  assert.equal(E.classify('viento', 38.9), 0); assert.equal(E.classify('viento', 39), 1); assert.equal(E.classify('viento', 62), 2);
  assert.equal(E.classify('viento', 89), 3); assert.equal(E.classify('viento', 200), 4);
  assert.equal(E.classify('lluvia', 0.05), 0); assert.equal(E.classify('lluvia', 1), 1); assert.equal(E.classify('lluvia', 2), 2); assert.equal(E.classify('lluvia', 31), 4);
  assert.equal(E.classify('frio', -9), 0); assert.equal(E.classify('frio', -12), 1); assert.equal(E.classify('frio', -30), 2); assert.equal(E.classify('frio', -45), 3);
  assert.equal(E.classify('nieve', 0.5), 1); assert.equal(E.classify('nieve', 3), 3);
  assert.equal(E.classify('viento', null), E.UNKNOWN); assert.equal(E.classify('lluvia', NaN), E.UNKNOWN);
  for (const h of E.HAZARDS) assert.ok(E.THRESHOLDS[h].status && E.THRESHOLDS[h].basis, 'cada umbral declara su procedencia');
});

// ── evaluación de la ruta ──
function routeNorth(n, dLat, z0, z1) { return E.prepareTrack(E.parseGPX(gpx(line(n, dLat, z0, z1)))); }

test('evaluateRoute: la hora de salida mueve el episodio a lo largo de la ruta', () => {
  // Lluvia moderada (6 mm/3 h = 2 mm/h) solo en el bloque k=1 (hora 3 → cubre 02:00–05:00).
  const G = E.createGrid(makeGrid((n, la, lo, k) => n === 'precipitation' ? (k === 1 ? 6 : 0) : calm(n)));
  const prep = routeNorth(61, 0.001, 1500, 1500);                    // ~6,7 km hacia el norte
  const early = E.evaluateRoute(prep, G, { departMs: T0 + 0 * HOUR, factor: 1 });   // marcha de ~1,3 h, termina antes de las 02:00
  const mid = E.evaluateRoute(prep, G, { departMs: T0 + 3 * HOUR, factor: 1 });
  const late = E.evaluateRoute(prep, G, { departMs: T0 + 8 * HOUR, factor: 1 });
  const sm = (ev) => E.summarize(prep, ev);
  assert.equal(sm(early).hazards.lluvia.worst, 0); assert.equal(sm(late).hazards.lluvia.worst, 0);
  assert.ok(sm(mid).hazards.lluvia.worst >= 2, 'moderada a partir de 2 mm/h');
  assert.ok(sm(mid).precip.liquidMm > 1 && sm(early).precip.liquidMm === 0);
  assert.equal(sm(mid).precip.solidMm, 0);
  const runs = sm(mid).hazards.lluvia.runs; assert.ok(runs.length === 1 && runs[0].t0 < runs[0].t1);
});
test('evaluateRoute: fallo cerrado fuera del dominio y fuera del horizonte', () => {
  const G = E.createGrid(makeGrid((n, la, lo, k) => n === 'wind_gusts_10m' ? 70 : calm(n)));
  const prep = routeNorth(61, 0.001, 1500, 1500);
  const prep2 = E.prepareTrack(E.parseGPX(gpx(line(101, 0.004, 1500, 1500))));   // llega a 42.80: fuera
  const ev = E.evaluateRoute(prep2, G, { departMs: T0, factor: 1 }), sm = E.summarize(prep2, ev);
  assert.ok(sm.coverage.fueraDominio > 0.3 && sm.coverage.ok < 0.7);
  const out = ev.samples.find((s) => s.estado === 'fuera_dominio');
  for (const h of E.HAZARDS) assert.equal(out.cls[h], E.UNKNOWN);
  assert.ok(sm.hazards.viento.unknownFraction > 0.3);
  assert.equal(sm.hazards.viento.worst, 2, 'lo evaluable sigue informando (70 km/h = clase 2)');
  const far = E.summarize(prep, E.evaluateRoute(prep, G, { departMs: T0 + 47 * HOUR, factor: 1 }));
  assert.ok(far.coverage.fueraHorizonte > 0.9); assert.equal(far.hazards.viento.worst, E.UNKNOWN);
  assert.ok(sm.notEvaluated.length >= 4);
});
test('evaluateRoute: temperatura a la altitud del track, fase y frío con viento', () => {
  // Celda a 1500 m, T2m = 2 °C, isocero a 1900 m → 5 K/km. Tramo que sube a 2700 m con 40 km/h y precipitación.
  const G = E.createGrid(makeGrid((n) => ({ temperature_2m: 2, dew_point_2m: 1.5, precipitation: 6, wind_gusts_10m: 65, wind_speed_10m: 40, freezing_level_height: 1900, elev: 1500 })[n]));
  const prep = routeNorth(31, 0.001, 1500, 2700);
  const ev = E.evaluateRoute(prep, G, { departMs: T0, factor: 1 });
  const lo = ev.samples[0], hi = ev.samples[ev.samples.length - 1];
  close(lo.v.t, 2, 0.2); close(hi.v.t, 2 - 5 * 1.2, 0.2, 'T a 2700 m');
  assert.ok(lo.v.frac < 0.5 && hi.v.frac > 0.95, 'abajo lluvia/mixta, arriba nieve');
  assert.ok(hi.v.snow > hi.v.rain && lo.v.rain > lo.v.snow);
  assert.equal(hi.v.aboveFl, true); assert.equal(lo.v.aboveFl, false);
  assert.ok(hi.cls.frio >= 1 && hi.cls.nieve >= 1 && hi.cls.viento === 2);
  assert.equal(hi.v.tMethod, 'isocero');
});
test('evaluateRoute: la ventana de ritmo toma el peor caso; sin altitud de track no se ajusta la temperatura', () => {
  // Racha de 100 km/h solo a partir de las 09:00 (bloque k=4). El final del recorrido cae justo antes de las 09:00:
  // el valor central es 0 pero la ventana (+15 % de tiempo) lo rebasa → peor caso = clase 3.
  const G = E.createGrid(makeGrid((n, la, lo, k) => n === 'wind_gusts_10m' ? (k >= 4 ? 100 : 10) : calm(n)));
  const prep = routeNorth(61, 0.001, 1500, 1500);
  const D = E.elapsedSeconds(prep, { factor: 1 }).tau.slice(-1)[0];
  const ev = E.evaluateRoute(prep, G, { departMs: T0 + 8.9 * HOUR - D * 1000, factor: 1 });
  const last = ev.samples[ev.samples.length - 1], first = ev.samples[0];
  assert.equal(last.cls.viento, 0); assert.equal(last.worst.viento, 3);
  assert.equal(first.cls.viento, 0); assert.equal(first.worst.viento, 0, 'sin ventana al inicio');
  const sm = E.summarize(prep, ev);
  assert.equal(sm.hazards.viento.worst, 0); assert.equal(sm.hazards.viento.worstWindow, 3);
  const noEle = E.prepareTrack(E.parseGPX(gpx(line(31, 0.001, 0, 0), { ele: false })));
  const e2 = E.evaluateRoute(noEle, G, { departMs: T0, factor: 1 });
  assert.equal(e2.samples[0].v.tMethod, 'celda');
  assert.throws(() => E.evaluateRoute(prep, G, {}), /salida/);
});
test('summarize: distancia, desnivel, llegada con ventana, cobertura y precipitación', () => {
  const G = E.createGrid(makeGrid(calm));
  const prep = routeNorth(61, 0.001, 1500, 1800);
  const ev = E.evaluateRoute(prep, G, { departMs: T0 + HOUR, factor: 1 }), sm = E.summarize(prep, ev);
  close(sm.distanceKm, 60 * 0.11119, 0.05); close(sm.ascentM, 300, 12);
  assert.ok(sm.arrivalWindow[0] < sm.arrivalMs && sm.arrivalMs < sm.arrivalWindow[1]);
  close(sm.arrivalMs, T0 + HOUR + sm.durationS * 1000, 1);
  close(sm.coverage.ok, 1, 1e-12); assert.equal(sm.precip.liquidMm, 0);
  for (const h of E.HAZARDS) assert.equal(sm.hazards[h].worst, 0, h);
});
test('exposición: marca puntos sobre su entorno según el DEM', () => {
  const G = E.createGrid(makeGrid(calm));
  const prep = routeNorth(31, 0.001, 2000, 2000);
  const ev = E.evaluateRoute(prep, G, { departMs: T0, factor: 1, dem: { at: () => 1950 } });
  assert.ok(ev.samples.every((s) => s.exposed === false));
  const ev2 = E.evaluateRoute(prep, G, { departMs: T0, factor: 1, dem: { at: () => 1500 } });
  assert.ok(ev2.samples.every((s) => s.exposed === true));
  const ev3 = E.evaluateRoute(prep, G, { departMs: T0, factor: 1, dem: { at: () => null } });
  assert.ok(ev3.samples.every((s) => s.exposed === null));
});
test('makeDem: decodifica uint16 y reproduce una interpolación bilineal conocida', () => {
  const nlat = 6, nlon = 5, step = 0.004, Z = new Uint16Array(nlat * nlon);
  for (let i = 0; i < nlat; i++) for (let j = 0; j < nlon; j++) Z[i * nlon + j] = 1000 + 10 * i + 100 * j;
  const dem = E.makeDem({ lat_n: 42.5, lon_w: 1.5, step, nlat, nlon, enc: 'uint16le_base64', data: Buffer.from(Z.buffer).toString('base64') });
  close(dem.at(42.5, 1.5), 1000, 1e-9); close(dem.at(42.5 - 2.5 * step, 1.5 + 1.5 * step), 1000 + 25 + 150, 1e-9);
  assert.equal(dem.at(42.6, 1.5), null); assert.equal(dem.at(42.5, 9), null);
  assert.equal(E.makeDem({ enc: 'otra' }), null);
  assert.throws(() => E.makeDem({ lat_n: 42.5, lon_w: 1.5, step, nlat, nlon, enc: 'uint16le_base64', data: 'AAAA' }), /tamaño/);
});

console.log(`route_engine: ${passed} pruebas OK`);
