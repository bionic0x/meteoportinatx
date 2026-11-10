/* Atomic per-domain loader: the whole view comes from ONE backend generation
   or from ONE GitHub Pages build. Never mix API and static JSON in one view. */
(function () {
  'use strict';
  const ALLOWED = {
    portinatx: ['core','radar','series','atmos','sat','mar','modx','forense'],
    pirineo: ['core','dem','grid','series','extended']
  };
  function partsOk(domain, parts) {
    if (!ALLOWED[domain] || !Array.isArray(parts) || !parts.length ||
        new Set(parts).size !== parts.length || parts.some(p => !ALLOWED[domain].includes(p))) {
      throw new Error('invalid domain or parts');
    }
  }
  async function loadAll(parts, urlFor, needsSnapshot) {
    const fetched = await Promise.all(parts.map(async part => {
      const response = await fetch(urlFor(part), {cache:'no-store',mode:'cors'});
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const freshness = needsSnapshot && response.headers.get('X-Meteo-Freshness');
      const snapshot = needsSnapshot && response.headers.get('X-Meteo-Snapshot');
      if (needsSnapshot && (freshness !== 'fresh' || !/^\d{8}T\d{6}Z-[a-f0-9]{12}$/.test(snapshot || ''))) {
        throw new Error('backend stale or snapshot header not exposed');
      }
      return {part, data:await response.json(), snapshot};
    }));
    if (needsSnapshot && fetched.some(x => x.snapshot !== fetched[0].snapshot)) {
      throw new Error('mixed backend generations');
    }
    return Object.fromEntries(fetched.map(({part,data}) => [part,data]));
  }
  window.meteoLoadDomain = async function (domain, parts, staticPrefix='api/') {
    partsOk(domain, parts);
    const backend = (window.METEO_BACKEND_URL || '').replace(/\/$/, '');
    if (backend) {
      try {
        const values = await loadAll(parts,
          part => backend + '/v1/' + domain + '/api/' + part + '.json', true);
        return {parts: values, source: 'backend'};
      } catch (_) { /* Entire domain falls back; never individual parts. */ }
    }
    const values = await loadAll(parts, part => staticPrefix + part + '.json', false);
    return {parts: values, source: backend ? 'snapshot-fallback' : 'snapshot'};
  };
  // The portal only needs the single `core` document.
  window.meteoLoadPart = async function (domain, part, staticPath) {
    partsOk(domain, [part]);
    const prefix = staticPath.slice(0, -part.length - '.json'.length);
    const packet = await window.meteoLoadDomain(domain, [part], prefix);
    return {data: packet.parts[part], source: packet.source};
  };
})();
