/* MeteoPortinatx Decision P0 — read-only profile projection, NO new forecasts.
   Pure functions so unfamiliar schema/old data cannot become a 'safe' verdict.
   Used from both static GitHub Pages and the localhost app. */
(function (global, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (global) global.MeteoDecision = api;
})(typeof window !== 'undefined' ? window : undefined, function () {
  'use strict';
  const profiles = Object.freeze({
    casa: {label: 'Casa junto a torrente', domain: 'portinatx', question: '¿Qué ha cambiado cerca de casa?', path: '../portinatx/', detail: 'Radar, pluviómetros y precaución'},
    barca: {label: 'Barca y amarre', domain: 'portinatx', question: '¿Qué viento y mar se están observando?', path: '../portinatx/', detail: 'Mar, viento y avisos costeros'},
    residencia: {label: 'Segunda residencia', domain: 'pirineo', question: '¿Qué se prevé para la zona de mi casa?', path: '../pirineo/', detail: 'Cotas, carreteras y avisos'},
    esqui: {label: 'Esquí y montaña', domain: 'pirineo', question: '¿Qué se prevé en la estación y a qué altitud?', path: '../pirineo/', detail: 'Relieve, viento y nieve'},
    meteo: {label: 'Investigar el episodio', domain: 'portinatx', question: '¿Qué se observa y qué está estimando el motor?', path: '../portinatx/', detail: 'Modelos, radar y verificación'}
  });
  const places = Object.freeze({
    font_romeu: 'Font-Romeu', les_angles: 'Les Angles', formigueres: 'Formiguères',
    porte: 'Porté-Puymorens', puigcerda: 'Puigcerdà', masella: 'Masella',
    la_molina: 'La Molina', arcalis: 'Ordino-Arcalís', pas_casa: 'Pas de la Casa'
  });
  const LEVELS = Object.freeze({quiet: 'sin señal destacada en este canal', watch: 'seguimiento', alert: 'señal elevada', alarm: 'señal intensa'});
  const HAZARD_KEYS = Object.freeze({
    lluvia_pluviometros: 'Lluvia en pluviómetros', lluvia_metar_aemet: 'Lluvia METAR / AEMET',
    radar: 'Radar', rayos: 'Rayos', viento: 'Viento', mar: 'Mar',
    runoff: 'Escorrentía manual', flooding: 'Anegamiento manual'
  });
  function finite(v) { return typeof v === 'number' && Number.isFinite(v); }
  function freshness(core, domain, nowMs) {
    const iso = core && typeof core.issued === 'string' ? core.issued : null;
    const t = iso && /(?:Z|[+-]\d{2}:\d{2})$/.test(iso) ? Date.parse(iso) : NaN;
    if (!Number.isFinite(t) || !Number.isFinite(nowMs)) return {state: 'unknown', ageMin: null, issued: null};
    const age = (nowMs - t) / 60000;
    if (age < -5) return {state: 'unknown', ageMin: null, issued: iso};
    return {state: age <= (domain === 'portinatx' ? 60 : 360) ? 'recent' : 'stale',
            ageMin: Math.round(Math.max(0, age)), issued: iso};
  }
  function officialCoast(core) {
    const v = core && core.official;
    if (!v || v.verificado !== true || !(v.level_now in LEVELS)) {
      return {kind: 'unknown', title: 'Aviso oficial: no verificado', detail: 'Consultar AEMET directamente.'};
    }
    const active = Array.isArray(v.all) ? v.all.filter(w => w && w.activo === true) : [];
    const names = active.map(w => typeof w.evento === 'string' ? w.evento.trim() : '').filter(Boolean).slice(0, 2);
    // #18: si el eje oficial no se apoya en AEMET CAP, decirlo en la propia tarjeta
    const SOURCE_NOTE = {SOLO_METEOALARM: 'Fuente: solo MeteoAlarm (sin CAP directo de AEMET).',
                         NINGUNA: 'Sin fuente oficial disponible en este ciclo.'};
    const note = SOURCE_NOTE[v.fuente_oficial] || '';
    const detail = names.length ? names.join(' · ') : 'Situación del último ciclo verificado; comprobar AEMET.';
    return {kind: v.level_now === 'quiet' ? 'neutral' : 'official',
            title: `Aviso oficial interpretado: ${v.level_now}`,
            detail: note ? `${note} ${detail}` : detail};
  }
  function mountainOfficial(core) {
    const provider = core && core.fuentes && core.fuentes.avisos;
    const verified = typeof provider === 'string' && /^ok\b/i.test(provider);
    if (!verified) return {kind: 'unknown', title: 'Avisos: fuente sin verificar', detail: 'Comprobar AEMET, SMA y Météo-France.'};
    const active = Array.isArray(core.avisos) ? core.avisos.filter(w => w && w.vigente === true) : [];
    const events = active.map(w => String(w.evento || '').slice(0, 100)).filter(Boolean).slice(0, 2);
    return {kind: active.length ? 'official' : 'neutral',
            title: active.length ? `Avisos oficiales: ${active.length} vigente(s)` : 'No constan avisos vigentes en este ciclo',
            detail: events.length ? events.join(' · ') : 'No equivale a ausencia de peligro; verificar los organismos oficiales.'};
  }
  function hazard(core, keys) {
    const source = core && core.hazard && typeof core.hazard === 'object' ? core.hazard : {};
    return keys.map(key => {
      const h = source[key];
      const valid = h && h.estado === 'OBSERVED' && Object.prototype.hasOwnProperty.call(LEVELS, h.nivel);
      return {key, label: HAZARD_KEYS[key], kind: valid ? (h.nivel === 'quiet' ? 'neutral' : 'observed') : 'unknown',
              value: valid ? LEVELS[h.nivel] : 'UNKNOWN · sin observación utilizable',
              local: valid && h.local === true};
    });
  }
  function mountainPoint(core, id) {
    const rows = Array.isArray(core && core.puntos) ? core.puntos : [];
    const item = rows.find(row => row && row.id === id);
    if (!item || !item.modelos || typeof item.modelos !== 'object') return null;
    const preference = ['meteofrance_arome_france_hd', 'icon_eu', 'ecmwf_ifs'];
    const modelId = preference.find(k => item.modelos[k] && typeof item.modelos[k] === 'object') ||
                    Object.keys(item.modelos).find(k => item.modelos[k] && typeof item.modelos[k] === 'object');
    if (!modelId) return null;
    const m = item.modelos[modelId];
    const readable = {meteofrance_arome_france_hd: 'AROME HD', icon_eu: 'ICON-EU', ecmwf_ifs: 'ECMWF IFS', metno: 'MET Norway'};
    const label = readable[modelId] || (core.modelo_nombre && typeof core.modelo_nombre === 'object' && core.modelo_nombre[modelId]) || modelId;
    // #8 / Pirineo 0.6.1: cota de la vertiente del punto y riesgo de engelante; sin dato, null (no «debajo»)
    const c = item.cotas && typeof item.cotas === 'object' ? item.cotas : {};
    const above = c.estado === 'OK' && typeof c.sobre_cota_copo === 'boolean' ? c.sobre_cota_copo : null;
    return {id, place: places[id] || id, model: String(label).slice(0, 65),
            snowLevel: finite(c.cota_copo_m) && c.estado === 'OK' ? c.cota_copo_m : null,
            side: c.vertiente === 'norte' || c.vertiente === 'sur' || c.vertiente === 'divisoria' ? c.vertiente : null,
            aboveSnowLevel: above, freezingRain: c.riesgo_engelante === true,
            snow24: finite(m.nieve24_cm) && m.nieve24_cm >= 0 ? m.nieve24_cm : null,
            gust24: finite(m.racha24) && m.racha24 >= 0 ? m.racha24 : null,
            temp: finite(m.T) ? m.T : null,
            pr24: finite(m.pr24) && m.pr24 >= 0 ? m.pr24 : null};
  }
  /* ── «Investigar el episodio»: ficha de auditoría de UN ciclo, solo desde core.json ──
     Lista de permitidos: un canal o campo que no esté aquí no enseña su texto. El snapshot
     de Pages no pasa por la proyección pública del backend, así que el filtro va también aquí. */
  const LEVEL_NAMES = Object.freeze(['quiet', 'watch', 'alert', 'alarm']);
  const CHANNELS = Object.freeze({
    lluvia_observada: {group: 'measured', label: 'Lluvia en estaciones AEMET y METAR'},
    pluviometros: {group: 'measured', label: 'Pluviómetros vecinos'},
    radar: {group: 'measured', label: 'Radar'},
    rayos: {group: 'measured', label: 'Rayos'},
    frente_racha: {group: 'measured', label: 'Frente de racha en estaciones'},
    viento_estaciones: {group: 'measured', label: 'Viento en estaciones'},
    mar_boyas: {group: 'measured', label: 'Oleaje en boyas'},
    escorrentia_torrentes: {group: 'measured', label: 'Escorrentía: indicio por pluviómetro, no medida'},
    modelo_meteofrance_arome_france_hd: {group: 'model', label: 'Modelo AROME HD', short: 'AROME'},
    modelo_ecmwf_ifs025: {group: 'model', label: 'Modelo ECMWF IFS', short: 'ECMWF'},
    modelo_icon_eu: {group: 'model', label: 'Modelo ICON-EU', short: 'ICON'},
    trayectoria_nucleo: {group: 'model', label: 'Trayectoria del núcleo de lluvia en modelos'},
    mar_bahia: {group: 'model', label: 'Oleaje modelado en la bahía'},
    ensemble_ecmwf: {group: 'ensemble', label: 'Conjunto ECMWF de simulaciones'}
  });
  const SOURCE_STATES = Object.freeze({error: 'falló en esta actualización', sin_clave: 'sin credencial configurada', deshabilitado: 'desactivada'});
  const WARNING_LEVELS = Object.freeze(['verde', 'amarillo', 'naranja', 'rojo']);
  const OWNER_TEXT = /manual|propietari|owner/i;
  function text(v, max) { return typeof v === 'string' ? v.trim().slice(0, max) : ''; }
  // Saneado mínimo y determinista del texto del motor; el resto se muestra literal.
  function cleanEvidence(line) {
    return line.replace(/\bnan\b/g, 'sin dato')
      .replace(/STALE → UNKNOWN/g, 'dato caducado → no se usa')
      .replace(/MOTION_UNKNOWN/g, 'movimiento no determinable')
      // límite del contrato: una fracción de miembros nunca se escribe como probabilidad
      .replace(/P\((\d+) ?h≥(\d+)\)=(\d+) ?%/g, '$3 % de miembros ≥$2 mm/$1 h');
  }
  function channelRow(c, issuedMs) {
    const known = Object.prototype.hasOwnProperty.call(CHANNELS, c.name) ? CHANNELS[c.name] : null;
    if (!known) return null;
    const level = c.available !== false && Number.isInteger(c.level) && c.level >= 0 && c.level <= 3 ? c.level : null;
    const raw = Array.isArray(c.evidence) ? c.evidence : [];
    const evidence = raw.map(e => text(e, 320)).filter(e => e && !OWNER_TEXT.test(e)).slice(0, 14).map(e => {
      // un parte METAR fechado otro día no describe el ciclo actual
      const m = e.match(/\b[A-Z]{4} (\d{2})\d{4}Z\b/);
      const day = Number.isFinite(issuedMs) ? new Date(issuedMs).getUTCDate() : null;
      return cleanEvidence(e) + (m && day !== null && Number(m[1]) !== day ? ' · parte fechado otro día: no es actual' : '');
    });
    return {name: c.name, group: known.group, label: known.label, short: known.short || null,
            status: level === null ? 'nodata' : level >= 1 ? 'signal' : 'none', level,
            levelLabel: level === null ? 'sin dato · no equivale a calma' : LEVELS[LEVEL_NAMES[level]],
            // la edad publicada es la del dato MÁS reciente del canal; en modelos es la hora de descarga
            ageMin: known.group === 'measured' && finite(c.age_min) && c.age_min >= 0 ? Math.round(c.age_min) : null,
            justMeasured: known.group === 'measured' && finite(c.age_min) && c.age_min < 0 && c.available !== false,
            local: c.local === true, evidence, evidencePublished: raw.length > 0};
  }
  function activeWarnings(core, nowMs) {
    const v = core && core.official;
    if (!v || v.verificado !== true) return {verified: false, items: [], later: 0, expired: 0, note: ''};
    const seen = new Set(); const items = []; let later = 0, expired = 0;
    for (const w of Array.isArray(v.all) ? v.all : []) {
      if (!w || typeof w !== 'object') continue;
      const until = typeof w.hasta === 'string' ? Date.parse(w.hasta) : NaN;
      if (w.activo !== true) { later++; continue; }
      // «activo» se fija al emitir el ciclo: un aviso ya vencido al consultar no cuenta como vigente
      if (Number.isFinite(until) && until < nowMs) { expired++; continue; }
      const key = [w.nivel, w.tipo, w.evento, w.desde, w.hasta].join('|');
      if (seen.has(key)) continue;
      seen.add(key);
      items.push({level: WARNING_LEVELS.includes(w.nivel) ? w.nivel : null, type: text(w.tipo, 30),
                  event: text(w.evento, 140), until: Number.isFinite(until) ? w.hasta : null,
                  threshold: text(w.umbral, 260)});
    }
    const note = {SOLO_METEOALARM: 'Fuente: solo MeteoAlarm (sin CAP directo de AEMET).', NINGUNA: 'Sin fuente oficial disponible en este ciclo.'}[v.fuente_oficial] || '';
    return {verified: true, items, later, expired, note};
  }
  function engineReason(r) {
    let m;
    if (typeof r !== 'string' || OWNER_TEXT.test(r)) return null;
    if ((m = r.match(/^suelo institucional = (quiet|watch|alert|alarm)$/))) return {kind: 'floor', level: LEVELS[m[1]]};
    if ((m = r.match(/^([a-z0-9_]{1,48})=(quiet|watch|alert|alarm)$/))) {
      if (m[1] === 'aviso_aemet' || m[1] === 'aviso_aemet_activo') return {kind: 'official', level: LEVELS[m[2]]};
      if (Object.prototype.hasOwnProperty.call(CHANNELS, m[1])) return {kind: 'channel', label: CHANNELS[m[1]].label, level: LEVELS[m[2]]};
    }
    return null;   // texto libre del motor (puede citar observaciones manuales): no se muestra
  }
  function engineView(core) {
    const stage = (o) => {
      const lvl = o && typeof o === 'object' && Object.prototype.hasOwnProperty.call(LEVELS, o.level) ? o.level : null;
      const raw = o && Array.isArray(o.reasons) ? o.reasons : [];
      const seen = new Set();
      const reasons = raw.map(engineReason).filter(r => r && !seen.has(JSON.stringify(r)) && seen.add(JSON.stringify(r)));
      return {level: lvl === null ? null : LEVEL_NAMES.indexOf(lvl), levelLabel: lvl === null ? null : LEVELS[lvl],
              reasons, hidden: raw.length - reasons.length, published: raw.length > 0};
    };
    const p = core && core.precaution && typeof core.precaution === 'object' ? core.precaution : {};
    const insufficient = p.insufficient === true || (core && core.nowcast && core.nowcast.insufficient === true);
    // En Pages cada ciclo arranca sin estado previo: «ESCALADA quiet→…» sería un artefacto, no un cambio real.
    const history = Array.isArray(core && core.history) ? core.history.length : 0;
    let change = null;
    const m = history > 1 && typeof (core.nowcast || {}).transition === 'string' &&
              core.nowcast.transition.match(/^(ESCALADA|DESCENSO) (quiet|watch|alert|alarm)→(quiet|watch|alert|alarm)$/);
    if (m) change = {up: m[1] === 'ESCALADA', from: LEVELS[m[2]], to: LEVELS[m[3]]};
    return {now: stage(core && core.nowcast), next: stage(core && core.outlook), insufficient,
            rainCoverage: /^\d\/\d$/.test(p.rain_coverage || '') ? p.rain_coverage : null,
            comparable: history > 1, change};
  }
  function modelSpread(rows) {
    const models = rows.filter(r => /^modelo_/.test(r.name) && r.status !== 'nodata');
    if (models.length < 2) return null;
    const parsed = [];
    for (const r of models) {
      // extracción estricta del texto del motor; si un modelo no casa, no se compara ninguno
      const hit = r.evidence.map(e => e.match(/· racha (\d+) km\/h · CAPE (\d+) J\/kg$/)).find(Boolean);
      if (!hit) return null;
      parsed.push({short: r.short || r.label, gust: Number(hit[1]), cape: Number(hit[2])});
    }
    const range = k => { const s = [...parsed].sort((a, b) => a[k] - b[k]); return {min: s[0][k], minModel: s[0].short, max: s[s.length - 1][k], maxModel: s[s.length - 1].short}; };
    return {gust: range('gust'), cape: range('cape'), n: parsed.length};
  }
  function sourceHealth(core) {
    const rows = (Array.isArray(core && core.sources) ? core.sources : []).filter(s => s && /^[a-z0-9_]{1,40}$/.test(s.name || ''));
    const failing = rows.filter(s => s.status !== 'ok').map(s => ({name: s.name, state: SOURCE_STATES[s.status] || 'estado no reconocido', error: s.status === 'error'}));
    return {total: rows.length, ok: rows.length - failing.length, failing};
  }
  function claimCounts(core) {
    const list = core && core.governance && Array.isArray(core.governance.claims) ? core.governance.claims : [];
    const kinds = {EVIDENCE: 0, HYPOTHESIS: 0, ASSUMPTION: 0, UNKNOWN: 0}; const seen = new Set(); let n = 0;
    for (const c of list) {
      if (!c || typeof c !== 'object' || c.source_root === 'owner' || c.label === 'OWNER' || /^C-(man|es-alert)/.test(c.id || '')) continue;
      if (!Object.prototype.hasOwnProperty.call(kinds, c.epistemic) || seen.has(c.text)) continue;   // los avisos llegan duplicados (CAP + MeteoAlarm)
      seen.add(c.text); kinds[c.epistemic]++; n++;
    }
    return n ? {evidence: kinds.EVIDENCE, hypothesis: kinds.HYPOTHESIS, assumption: kinds.ASSUMPTION, unknown: kinds.UNKNOWN, total: n} : null;
  }
  function investigation(core, nowMs = Date.now()) {
    const issuedMs = core && typeof core.issued === 'string' ? Date.parse(core.issued) : NaN;
    const rows = (Array.isArray(core && core.channels) ? core.channels : [])
      .filter(c => c && typeof c === 'object' && typeof c.name === 'string').map(c => channelRow(c, issuedMs)).filter(Boolean);
    const order = r => (r.status === 'signal' ? 0 : r.status === 'nodata' ? 1 : 2);
    const pick = g => rows.filter(r => r.group === g).sort((a, b) => order(a) - order(b));
    const measured = pick('measured');
    return {cycle: {engine: /^[\w.-]{1,20}$/.test((core && core.engine) || '') ? core.engine : null,
                    id: /^[\w-]{1,40}$/.test((core && core.cycle_id) || '') ? core.cycle_id : null},
            warnings: activeWarnings(core, nowMs), measured, models: pick('model'), ensemble: pick('ensemble'),
            counts: {total: measured.length, available: measured.filter(r => r.status !== 'nodata').length,
                     signal: measured.filter(r => r.status === 'signal').length, nodata: measured.filter(r => r.status === 'nodata').length},
            spread: modelSpread(rows), engine: engineView(core), sources: sourceHealth(core), claims: claimCounts(core)};
  }
  function unknownFor(profile, f, source) {
    return {id: profile, ...profiles[profile], state: f.state, issued: f.issued, ageMin: f.ageMin,
            source: source || 'desconocido', heading: f.state === 'stale' ? 'Datos antiguos · sin diagnóstico actual' : 'No hay datos verificables',
            official: {kind:'unknown', title:'Avisos sin verificar', detail:'Consultar fuentes oficiales.'},
            observed: [], operational: null, forecast: null,
            guidance: 'No deducir calma ni tomar decisiones de seguridad con estos datos.', available: false};
  }
  function project(profile, core, source = 'snapshot', place = 'font_romeu', nowMs = Date.now()) {
    if (!Object.prototype.hasOwnProperty.call(profiles, profile)) throw new TypeError('Perfil desconocido');
    const p = profiles[profile];
    const f = freshness(core, p.domain, nowMs);
    if (f.state !== 'recent') return unknownFor(profile, f, source);
    const common = {id: profile, ...p, state:f.state, issued:f.issued, ageMin:f.ageMin,
                    source, available:true, forecast:null, operational:null, observed: []};
    if (p.domain === 'portinatx') {
      const keys = profile === 'barca' ? ['viento','mar','rayos'] :
                   profile === 'meteo' ? ['lluvia_pluviometros','lluvia_metar_aemet','radar','rayos','viento','mar'] :
                   ['lluvia_pluviometros','lluvia_metar_aemet','radar','rayos'];
      const items = hazard(core, keys);
      const usable = items.filter(h => h.kind !== 'unknown');
      const precaution = core && core.precaution && core.precaution.level;
      const insufficient = core && core.precaution && core.precaution.insufficient === true;
      return {...common, official:officialCoast(core), observed:items,
        episode: profile === 'meteo' ? investigation(core, nowMs) : null,
        operational: profile === 'casa' && !insufficient && Object.prototype.hasOwnProperty.call(LEVELS, precaution) ?
                    {title:`Precaución calculada: ${precaution}`, detail:'Estimación operativa, no instrucción individual ni aviso oficial.'} : null,
        heading: insufficient ? 'Cobertura de lluvia insuficiente · situación no verificable' :
        usable.length ? `${usable.length} de ${items.length} canales observados disponibles` : 'Observación local insuficiente',
        guidance: profile === 'casa' ? 'Revisar el protocolo propio y las indicaciones oficiales de emergencias; la web no conoce el estado de la vivienda.' :
                  profile === 'barca' ? 'Contrastar con capitanía, AEMET y condiciones en la bocana antes de maniobras náuticas.' :
                  'Inspeccionar datos de origen, ejecuciones del modelo y evidencias falsables; las fracciones ensemble no están calibradas.'};
    }
    const pointId = Object.prototype.hasOwnProperty.call(places,place) ? place : 'font_romeu';
    const forecast = mountainPoint(core,pointId);
    return {...common, official:mountainOfficial(core), observed:[], forecast,
      heading: forecast ? `Estimación de ${forecast.model} para ${forecast.place}` : 'Pronóstico puntual no disponible',
      guidance: profile === 'residencia' ? 'La previsión por punto no confirma el estado de carreteras ni la cota de acceso; consultar tráfico y avisos oficiales.' :
                'Consultar el boletín de aludes, el viento en collados y las condiciones de terreno: no hay evaluación automática de seguridad.'};
  }
  return Object.freeze({profiles, places, freshness, officialCoast, mountainOfficial, hazard, mountainPoint, investigation, project});
});
