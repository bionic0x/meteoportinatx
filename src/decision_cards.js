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
  return Object.freeze({profiles, places, freshness, officialCoast, mountainOfficial, hazard, mountainPoint, project});
});
