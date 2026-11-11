/* Motor de ruta del Pirineo: pronóstico sobre la posición estimada de un track GPS.
 *
 * Módulo puro (sin DOM, sin red, sin almacenamiento). El track vive solo en memoria del navegador.
 * Cada punto recibe (lat, lon, altitud, hora estimada) y se consulta la rejilla de pronóstico en ese
 * punto del espacio y del tiempo. Principios del proyecto aplicados:
 *   - Un indicador por peligro; nunca una nota global de «mal tiempo».
 *   - Fallo cerrado: lo que no se puede evaluar es DESCONOCIDO (-1), nunca «sin riesgo».
 *   - Ventanas horarias (incertidumbre de ritmo), no horas exactas.
 *   - Los umbrales son orientativos de la herramienta; no son umbrales de aviso oficial.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.RouteEngine = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const UNKNOWN = -1;
  const R_EARTH = 6371008.8;
  const LIMITS = { maxChars: 30e6, maxRawPoints: 400000, maxSamples: 4000 };

  // Constantes de fase: deben coincidir con knowledge_base.PRIORS (lo comprueba tests/test_route_engine.py).
  const DEFAULTS = { snowTw: 0.7, snowHalf: 1.0, stepM: 200, windowFrac: 0.15, exposedDz: 150, exposedRingM: 1500 };

  // Umbrales ORIENTATIVOS de la herramienta. Ninguno es umbral de aviso oficial ni está calibrado localmente.
  const THRESHOLDS = {
    lluvia: { unit: 'mm/h', status: 'UNVERIFIED', basis: 'Clases de intensidad usuales (débil ≤2, moderada ≤15, fuerte ≤30, muy fuerte >30); recordadas, no contrastadas con el glosario oficial.', edges: [0.1, 2, 15, 30] },
    viento: { unit: 'km/h', status: 'ORIENTATIVE', basis: 'Escala de Beaufort aplicada a la racha: 39 (Bf6), 62 (Bf8), 89 (Bf10), 118 (Bf12).', edges: [39, 62, 89, 118] },
    nieve: { unit: 'mm agua eq./h', status: 'UNVERIFIED', basis: 'Intensidad de precipitación sólida; cortes propios sin calibrar. No se convierte a cm (la relación nieve/agua es variable).', edges: [0.1, 1, 2.5] },
    frio: { unit: '°C', status: 'ORIENTATIVE', basis: 'Sensación térmica por viento (índice JAG/TI, T ≤ 10 °C y viento > 4,8 km/h) con los cortes de riesgo de congelación habituales: -10, -28, -40.', edges: [-10, -28, -40] },
  };
  const HAZARDS = ['lluvia', 'viento', 'nieve', 'frio'];
  const NOT_EVALUATED = ['tormenta y rayos', 'niebla y visibilidad', 'crecidas y cruces de cauces', 'aludes y estado de la nieve en suelo'];

  const rad = (d) => d * Math.PI / 180;
  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
  const isNum = (x) => typeof x === 'number' && Number.isFinite(x);

  function haversine(lat1, lon1, lat2, lon2) {
    const dLat = rad(lat2 - lat1), dLon = rad(lon2 - lon1);
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(dLon / 2) ** 2;
    return 2 * R_EARTH * Math.asin(Math.min(1, Math.sqrt(a)));
  }

  // ───────────────────────────── lectura de GPX ─────────────────────────────
  function attr(s, name) {
    const m = new RegExp('\\b' + name + '\\s*=\\s*(?:"([^"]*)"|\'([^\']*)\')', 'i').exec(s);
    return m ? Number(m[1] !== undefined ? m[1] : m[2]) : NaN;
  }

  function parseGPX(text) {
    if (typeof text !== 'string' || !text.length) throw new Error('Fichero vacío');
    if (text.length > LIMITS.maxChars) throw new Error('Fichero demasiado grande');
    if (/<!(DOCTYPE|ENTITY)/i.test(text)) throw new Error('GPX con DOCTYPE/ENTITY: rechazado');
    const warnings = [];
    let re = /<trkpt\b([^>]*?)(?:\/>|>([\s\S]*?)<\/trkpt>)/gi;
    let kind = 'track';
    if (!/<trkpt\b/i.test(text)) { re = /<rtept\b([^>]*?)(?:\/>|>([\s\S]*?)<\/rtept>)/gi; kind = 'ruta'; }
    const points = [];
    let bad = 0, m;
    while ((m = re.exec(text)) !== null) {
      if (points.length + bad >= LIMITS.maxRawPoints) throw new Error('Demasiados puntos');
      const lat = attr(m[1], 'lat'), lon = attr(m[1], 'lon');
      if (!(Math.abs(lat) <= 90) || !(Math.abs(lon) <= 180)) { bad++; continue; }
      const body = m[2] || '';
      const e = /<ele>\s*([^<\s]+)\s*<\/ele>/i.exec(body);
      const tm = /<time>\s*([^<\s]+)\s*<\/time>/i.exec(body);
      const ele = e ? Number(e[1]) : NaN;
      const t = tm ? Date.parse(tm[1]) : NaN;
      points.push({ lat, lon, ele: isNum(ele) ? ele : null, t: isNum(t) ? t : null });
    }
    if (bad) warnings.push(bad + ' puntos con coordenadas inválidas descartados');
    if (points.length < 2) throw new Error('El fichero no contiene un track con al menos 2 puntos');
    if (kind === 'ruta') warnings.push('El fichero es una ruta planificada, no un track grabado: puede ser poco densa y sin tiempos');
    const nm = /<name>\s*([^<]{1,120}?)\s*<\/name>/i.exec(text);
    return { points, name: nm ? nm[1] : null, kind, warnings };
  }

  // ───────────────────────────── DEM (dem.json empaquetado) ─────────────────────────────
  function makeDem(dem) {
    if (!dem || dem.enc !== 'uint16le_base64' || !dem.data) return null;
    const bin = typeof atob === 'function' ? atob(dem.data) : Buffer.from(dem.data, 'base64').toString('binary');
    const u = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
    if (u.length !== dem.nlat * dem.nlon * 2) throw new Error('DEM con tamaño inconsistente');
    const Z = new Uint16Array(u.buffer);
    const at = (lat, lon) => {            // misma interpolación bilineal que pirineo.dem_at
      const i = (dem.lat_n - lat) / dem.step, j = (lon - dem.lon_w) / dem.step;
      if (!(i >= 0 && i <= dem.nlat - 1 && j >= 0 && j <= dem.nlon - 1)) return null;
      const i0 = Math.floor(i), j0 = Math.floor(j);
      const i1 = Math.min(i0 + 1, dem.nlat - 1), j1 = Math.min(j0 + 1, dem.nlon - 1);
      const a = i - i0, b = j - j0, n = dem.nlon;
      return Z[i0 * n + j0] * (1 - a) * (1 - b) + Z[i0 * n + j1] * (1 - a) * b + Z[i1 * n + j0] * a * (1 - b) + Z[i1 * n + j1] * a * b;
    };
    return { at, meta: dem, Z };
  }

  // ───────────────────────────── preparación del track ─────────────────────────────
  function smoothByDistance(d, v, halfM) {
    const n = d.length, pre = new Float64Array(n + 1);
    for (let i = 0; i < n; i++) pre[i + 1] = pre[i] + v[i];
    const out = new Array(n);
    let lo = 0, hi = 0;
    for (let i = 0; i < n; i++) {
      while (d[i] - d[lo] > halfM) lo++;
      while (hi + 1 < n && d[hi + 1] - d[i] <= halfM) hi++;
      out[i] = (pre[hi + 1] - pre[lo]) / (hi - lo + 1);
    }
    return out;
  }

  function ascentDescent(ele, thr) {
    let ref = ele[0], up = 0, down = 0;
    for (let i = 1; i < ele.length; i++) {
      const dz = ele[i] - ref;
      if (dz >= thr) { up += dz; ref = ele[i]; } else if (dz <= -thr) { down -= dz; ref = ele[i]; }
    }
    return { up, down };
  }

  function prepareTrack(parsed, opts) {
    opts = opts || {};
    const stepM = opts.stepM || DEFAULTS.stepM;
    const demAt = opts.dem ? opts.dem.at : null;
    const raw = [];
    for (const p of parsed.points) {            // elimina duplicados exactos consecutivos
      const q = raw[raw.length - 1];
      if (!q || p.lat !== q.lat || p.lon !== q.lon) raw.push(p);
    }
    if (raw.length < 2) throw new Error('El track no tiene movimiento');
    const d = new Float64Array(raw.length);
    for (let i = 1; i < raw.length; i++) d[i] = d[i - 1] + haversine(raw[i - 1].lat, raw[i - 1].lon, raw[i].lat, raw[i].lon);
    const total = d[raw.length - 1];
    if (!(total >= 100)) throw new Error('El track mide menos de 100 m');

    // Altitud: la del track si cubre ≥ 90 % de los puntos; si no, el DEM de ~440 m; si no, sin altitud.
    const nEle = raw.filter((p) => p.ele !== null).length;
    let eleSource = 'ninguna', ele = null;
    if (nEle >= 0.9 * raw.length) {
      eleSource = 'track'; ele = raw.map((p) => p.ele);
      let last = null; for (let i = 0; i < ele.length; i++) { if (ele[i] === null) ele[i] = last; else last = ele[i]; }
      let nxt = null; for (let i = ele.length - 1; i >= 0; i--) { if (ele[i] === null) ele[i] = nxt; else nxt = ele[i]; }
    } else if (demAt) {
      const e = raw.map((p) => demAt(p.lat, p.lon));
      if (e.every((x) => x !== null)) { eleSource = 'dem'; ele = e; }
    }
    let eleS = null, asc = null;
    if (ele) {
      eleS = smoothByDistance(Array.from(d), ele, 75);
      asc = ascentDescent(eleS, 3);
    }

    // Tiempos grabados (solo si cubren casi todo el track y son monótonos).
    const tOk = raw.every((p) => p.t !== null) && raw.every((p, i) => i === 0 || p.t >= raw[i - 1].t) && raw[raw.length - 1].t > raw[0].t;

    // Remuestreo uniforme.
    const step = Math.max(stepM, total / LIMITS.maxSamples);
    const pos = [];
    for (let s = 0; s < total; s += step) pos.push(s);
    pos.push(total);
    const samples = [];
    let k = 0;
    for (const s of pos) {
      while (k < raw.length - 2 && d[k + 1] < s) k++;
      const span = d[k + 1] - d[k], f = span > 0 ? clamp((s - d[k]) / span, 0, 1) : 0;
      const lerp = (a, b) => a + (b - a) * f;
      samples.push({
        d: s, lat: lerp(raw[k].lat, raw[k + 1].lat), lon: lerp(raw[k].lon, raw[k + 1].lon),
        ele: eleS ? lerp(eleS[k], eleS[k + 1]) : null,
        tRec: tOk ? lerp(raw[k].t, raw[k + 1].t) : null,
      });
    }
    return {
      name: parsed.name, kind: parsed.kind, samples, totalM: total, ascentM: asc ? asc.up : null, descentM: asc ? asc.down : null,
      eleSource, hasTimes: tOk, rawPoints: raw.length, stepM: step, warnings: parsed.warnings.slice(),
    };
  }

  // ───────────────────────────── ritmo y horas ─────────────────────────────
  function toblerKmh(slope) {
    return 6 * Math.exp(-3.5 * Math.abs(clamp(slope, -0.8, 0.8) + 0.05));
  }

  // Segundos transcurridos desde la salida en cada muestra (valor central).
  function elapsedSeconds(prep, opts) {
    opts = opts || {};
    const S = prep.samples, tau = new Array(S.length).fill(0);
    if (opts.pace === 'track' && prep.hasTimes) {
      for (let i = 0; i < S.length; i++) tau[i] = (S[i].tRec - S[0].tRec) / 1000;
      return { tau, method: 'track' };
    }
    const factor = opts.factor > 0 ? opts.factor : 1;
    const pauseFactor = 1 + Math.max(0, opts.breakMinPerHour || 0) / 60;
    for (let i = 1; i < S.length; i++) {
      const ds = S[i].d - S[i - 1].d;
      const slope = (S[i].ele !== null && S[i - 1].ele !== null && ds > 0) ? (S[i].ele - S[i - 1].ele) / ds : 0;
      const v = Math.max(0.5, toblerKmh(slope) * factor) / 3.6;
      tau[i] = tau[i - 1] + (ds / v) * pauseFactor;
    }
    return { tau, method: 'tobler' };
  }

  // ───────────────────────────── rejilla de pronóstico ─────────────────────────────
  function createGrid(g) {
    if (!g || !Array.isArray(g.lats) || !Array.isArray(g.lons) || !Array.isArray(g.time) || !g.fields) throw new Error('Rejilla inválida');
    const nlat = g.lats.length, nlon = g.lons.length, cells = nlat * nlon;
    if (nlat < 2 || nlon < 2 || g.time.length < 2) throw new Error('Rejilla demasiado pequeña');
    for (const arr of [g.lats, g.lons]) for (let i = 1; i < arr.length; i++) if (!(arr[i] > arr[i - 1])) throw new Error('Ejes de rejilla no crecientes');
    const times = g.time.map((s) => Date.parse(/Z$|[+-]\d\d:\d\d$/.test(s) ? s : s + 'Z'));
    if (times.some((t) => !isNum(t))) throw new Error('Tiempos de rejilla inválidos');
    for (let i = 1; i < times.length; i++) if (!(times[i] > times[i - 1])) throw new Error('Tiempos de rejilla no crecientes');
    const need = ['temperature_2m', 'precipitation', 'wind_gusts_10m'];
    for (const v of need) if (!g.fields[v]) throw new Error('Falta el campo ' + v);
    for (const v of Object.keys(g.fields)) {
      const F = g.fields[v];
      if (!Array.isArray(F) || F.length !== times.length || F.some((r) => !Array.isArray(r) || r.length !== cells)) throw new Error('Campo ' + v + ' con forma inconsistente');
    }
    if (!Array.isArray(g.elev) || g.elev.length !== cells) throw new Error('Altitudes de celda inconsistentes');
    const stepH = g.paso_h > 0 ? g.paso_h : (times[1] - times[0]) / 3.6e6;
    return { lats: g.lats, lons: g.lons, times, fields: g.fields, elev: g.elev, nlat, nlon, stepH, modelo: g.modelo || null };
  }

  function axisPos(axis, x) {
    const n = axis.length;
    if (!(x >= axis[0] && x <= axis[n - 1])) return null;
    let i = 0;
    while (i < n - 2 && axis[i + 1] < x) i++;
    return [i, (x - axis[i]) / (axis[i + 1] - axis[i])];
  }

  function bilinear(grid, row, p, q) {       // p, q = [índice, fracción] de lat y lon; null si falta alguna esquina
    const [ia, fa] = p, [ib, fb] = q, n = grid.nlon;
    const c = [row[ia * n + ib], row[ia * n + ib + 1], row[(ia + 1) * n + ib], row[(ia + 1) * n + ib + 1]];
    if (c.some((x) => !isNum(x))) return null;
    return c[0] * (1 - fa) * (1 - fb) + c[1] * (1 - fa) * fb + c[2] * fa * (1 - fb) + c[3] * fa * fb;
  }

  // Estado de la rejilla en (lat, lon, t). Devuelve {estado} si no se puede evaluar.
  function sampleGrid(grid, lat, lon, tMs) {
    const p = axisPos(grid.lats, lat), q = axisPos(grid.lons, lon);
    if (!p || !q) return { estado: 'fuera_dominio' };
    const T = grid.times, n = T.length;
    // Instantáneas: el dato de 3 h se interpola linealmente en el tiempo.
    if (!(tMs >= T[0] && tMs <= T[n - 1])) return { estado: 'fuera_horizonte' };
    let k = 0;
    while (k < n - 2 && T[k + 1] < tMs) k++;
    const w = (tMs - T[k]) / (T[k + 1] - T[k]);
    const inst = (name, useMax) => {
      const F = grid.fields[name];
      if (!F) return null;
      const a = bilinear(grid, F[k], p, q), b = bilinear(grid, F[k + 1], p, q);
      if (a === null || b === null) return null;
      return useMax ? Math.max(a, b) : a * (1 - w) + b * w;   // racha: máximo de las dos salidas contiguas (conservador)
    };
    // Acumulados: bloque de stepH horas con marca tk que cubre (tk − 1 h, tk + stepH − 1 h].
    let pr = null;
    const H = 3.6e6;
    for (let j = 0; j < n; j++) {
      if (tMs > T[j] - H && tMs <= T[j] + (grid.stepH - 1) * H) {
        const v = bilinear(grid, grid.fields.precipitation[j], p, q);
        pr = v === null ? null : v / grid.stepH;
        break;
      }
    }
    const el = bilinear(grid, grid.elev, p, q);
    return {
      estado: 'ok', t2m: inst('temperature_2m'), td: inst('dew_point_2m'), gust: inst('wind_gusts_10m', true),
      wind: inst('wind_speed_10m'), fl: inst('freezing_level_height'), pr, elev: el,
    };
  }

  // ───────────────────────────── física ─────────────────────────────
  function wetBulb(t, td, p) {                // psicrométrica por bisección; idéntica a portinatx_degen.wet_bulb
    if (!isNum(t) || !isNum(td)) return null;
    const e = 6.112 * Math.exp(17.67 * td / (td + 243.5));
    let lo = td, hi = t;
    for (let i = 0; i < 40; i++) {
      const tw = (lo + hi) / 2;
      const es = 6.112 * Math.exp(17.67 * tw / (tw + 243.5));
      const f = es - 0.00066 * (1 + 0.00115 * tw) * p * (t - tw) - e;
      if (f > 0) hi = tw; else lo = tw;
    }
    return (lo + hi) / 2;
  }

  // Misma regla que pirineo.snow_frac: rampa lineal centrada en snowTw sobre el bulbo húmedo.
  function solidFraction(t, td, z, cfg) {
    cfg = cfg || DEFAULTS;
    if (!isNum(t)) return 0;
    const p = 1013.25 * Math.pow(1 - 2.25577e-5 * z, 5.25588);
    const tw = isNum(td) ? wetBulb(t, td, p) : t;
    return clamp((cfg.snowTw + cfg.snowHalf - tw) / (2 * cfg.snowHalf), 0, 1);
  }

  // Temperatura a la altitud del track. Si la cota de 0 °C del modelo da un gradiente creíble (3–9 K/km) se usa;
  // si no (inversión, aire muy seco), 6,5 K/km y se marca el perfil como incierto.
  function tempAtAltitude(t2m, zCell, fl, z) {
    if (!isNum(t2m)) return null;
    if (!isNum(z) || !isNum(zCell) || Math.abs(z - zCell) < 1) return { t: t2m, lapse: null, method: 'celda', uncertain: false };
    let lapse = null, method = 'estandar';
    if (isNum(fl) && Math.abs(fl - zCell) > 100) {
      const g = t2m / (fl - zCell) * 1000;
      if (g >= 3 && g <= 9) { lapse = g; method = 'isocero'; }
    }
    if (lapse === null) lapse = 6.5;
    return { t: t2m - lapse * (z - zCell) / 1000, lapse, method, uncertain: method === 'estandar' && Math.abs(z - zCell) > 300 };
  }

  function windChill(t, vKmh) {
    if (!isNum(t)) return null;
    if (!isNum(vKmh)) return null;
    if (t > 10 || vKmh <= 4.8) return t;
    const v = Math.pow(vKmh, 0.16);
    return 13.12 + 0.6215 * t - 11.37 * v + 0.3965 * t * v;
  }

  function classify(hazard, value) {
    if (!isNum(value)) return UNKNOWN;
    const E = THRESHOLDS[hazard].edges;
    if (hazard === 'frio') { let c = 0; for (const e of E) if (value < e) c++; return c; }   // más frío → más clase
    let c = 0; for (const e of E) if (value >= e) c++;
    return c;
  }

  function derive(env, z, cfg) {
    if (!env || env.estado !== 'ok') return null;
    const zRef = isNum(z) ? z : env.elev;
    const ta = tempAtAltitude(env.t2m, env.elev, env.fl, isNum(z) ? z : env.elev);
    const tAlt = ta ? ta.t : null;
    const tdAlt = (ta && isNum(env.td)) ? tAlt - Math.max(0, env.t2m - env.td) : null;
    const frac = ta && isNum(zRef) ? solidFraction(tAlt, tdAlt, zRef, cfg) : null;
    const rain = (env.pr !== null && frac !== null) ? env.pr * (1 - frac) : null;
    const snow = (env.pr !== null && frac !== null) ? env.pr * frac : null;
    const wc = windChill(tAlt, env.wind);
    return {
      t: tAlt, td: tdAlt, frac, pr: env.pr, rain, snow, gust: env.gust, wind: env.wind, wc, fl: env.fl,
      aboveFl: (isNum(env.fl) && isNum(zRef)) ? zRef > env.fl : null, tMethod: ta ? ta.method : null, uncertainProfile: ta ? ta.uncertain : false,
      cls: { lluvia: classify('lluvia', rain), viento: classify('viento', env.gust), nieve: classify('nieve', snow), frio: classify('frio', wc) },
    };
  }

  // ───────────────────────────── evaluación de la ruta ─────────────────────────────
  function exposure(dem, lat, lon, ele, cfg) {
    if (!dem || !isNum(ele)) return null;
    const dLat = cfg.exposedRingM / 111320, dLon = cfg.exposedRingM / (111320 * Math.cos(rad(lat)));
    let sum = 0, n = 0;
    for (let b = 0; b < 8; b++) {
      const a = b * Math.PI / 4, z = dem.at(lat + dLat * Math.cos(a), lon + dLon * Math.sin(a));
      if (z !== null) { sum += z; n++; }
    }
    if (n < 6) return null;
    return ele - sum / n >= cfg.exposedDz;
  }

  function evaluateRoute(prep, grid, opts) {
    opts = opts || {};
    const cfg = Object.assign({}, DEFAULTS, opts.cfg || {});
    if (!isNum(opts.departMs)) throw new Error('Falta la hora de salida');
    const { tau, method } = elapsedSeconds(prep, opts);
    const w = cfg.windowFrac, fs = [1 - w, 1, 1 + w];
    const out = [];
    for (let i = 0; i < prep.samples.length; i++) {
      const s = prep.samples[i];
      const evals = fs.map((f) => {
        const t = opts.departMs + tau[i] * f * 1000;
        const env = sampleGrid(grid, s.lat, s.lon, t);
        return { t, env, dv: derive(env, s.ele, cfg) };
      });
      const c = evals[1];
      const states = evals.map((e) => e.env.estado);
      const estado = states.every((x) => x === 'ok') ? 'ok' : (c.env.estado !== 'ok' ? c.env.estado : 'ventana_incompleta');
      const cls = {}, worst = {};
      for (const h of HAZARDS) {
        const vals = evals.map((e) => (e.dv ? e.dv.cls[h] : UNKNOWN));
        cls[h] = vals[1];
        worst[h] = vals.some((v) => v === UNKNOWN) ? UNKNOWN : Math.max(...vals);
      }
      out.push({
        i, d: s.d, lat: s.lat, lon: s.lon, ele: s.ele, tau: tau[i], tMs: c.t, tWin: [evals[0].t, evals[2].t], estado,
        v: c.dv, cls, worst, exposed: exposure(opts.dem, s.lat, s.lon, s.ele, cfg),
      });
    }
    return { samples: out, paceMethod: method, departMs: opts.departMs, durationS: tau[tau.length - 1], windowFrac: w };
  }

  function summarize(prep, ev) {
    const S = ev.samples, n = S.length;
    const byHazard = {};
    for (const h of HAZARDS) {
      let worst = UNKNOWN, at = null, unknown = 0, runs = [], run = null, wmax = 0;
      for (const s of S) {
        const c = s.cls[h];
        if (c === UNKNOWN) unknown++;
        if (c > worst) { worst = c; at = s; }
        if (s.worst[h] > wmax) wmax = s.worst[h];
        if (c >= 1) {
          if (!run) { run = { d0: s.d, d1: s.d, t0: s.tWin[0], t1: s.tWin[1], max: c, tMs0: s.tMs }; runs.push(run); }
          run.d1 = s.d; run.t1 = Math.max(run.t1, s.tWin[1]); run.t0 = Math.min(run.t0, s.tWin[0]); run.max = Math.max(run.max, c);
        } else run = null;
      }
      byHazard[h] = { worst, atKm: at ? at.d / 1000 : null, atWindow: at ? at.tWin : null, atEle: at ? at.ele : null, worstWindow: wmax, unknownFraction: unknown / n, runs };
    }
    // Precipitación que caería sobre el recorrido (mm de agua), integrando por tiempo de paso.
    let liquid = 0, solid = 0, nPr = 0;
    for (let i = 0; i < n; i++) {
      const dt = ((i < n - 1 ? S[i + 1].tau : S[i].tau) - (i > 0 ? S[i - 1].tau : S[i].tau)) / 2 / 3600;
      const v = S[i].v;
      if (v && v.rain !== null) { liquid += v.rain * dt; solid += v.snow * dt; nPr++; }
    }
    const count = (e) => S.filter((s) => s.estado === e).length;
    return {
      distanceKm: prep.totalM / 1000, ascentM: prep.ascentM, descentM: prep.descentM, durationS: ev.durationS,
      arrivalMs: ev.departMs + ev.durationS * 1000, arrivalWindow: [ev.departMs + ev.durationS * 1000 * (1 - ev.windowFrac), ev.departMs + ev.durationS * 1000 * (1 + ev.windowFrac)],
      coverage: { ok: count('ok') / n, fueraDominio: count('fuera_dominio') / n, fueraHorizonte: count('fuera_horizonte') / n, parcial: count('ventana_incompleta') / n },
      precip: { liquidMm: nPr ? liquid : null, solidMm: nPr ? solid : null, samplesWithData: nPr / n },
      exposedKm: S.reduce((a, s, i) => a + (s.exposed ? ((i < n - 1 ? S[i + 1].d : s.d) - s.d) : 0), 0) / 1000,
      uncertainProfileFraction: S.filter((s) => s.v && s.v.uncertainProfile).length / n,
      hazards: byHazard, notEvaluated: NOT_EVALUATED.slice(),
    };
  }

  return {
    UNKNOWN, DEFAULTS, THRESHOLDS, HAZARDS, NOT_EVALUATED, LIMITS,
    haversine, parseGPX, makeDem, prepareTrack, toblerKmh, elapsedSeconds, createGrid, sampleGrid,
    wetBulb, solidFraction, tempAtAltitude, windChill, classify, derive, evaluateRoute, summarize,
  };
});
