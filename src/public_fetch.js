/* Read-only live API preference with explicit static-snapshot fallback.
   public_config.js is generated at site build time; do not put secrets there. */
window.meteoLoadPart = async function(domain, part, staticPath) {
  const base = (window.METEO_BACKEND_URL || '').replace(/\/$/, '');
  if (base) {
    try {
      const url = base + '/v1/' + encodeURIComponent(domain) + '/api/' + encodeURIComponent(part) + '.json';
      const response = await fetch(url, {cache:'no-store', mode:'cors'});
      if (!response.ok) throw new Error('HTTP ' + response.status);
      if (response.headers.get('X-Meteo-Freshness') !== 'fresh') throw new Error('stale remote');
      const data = await response.json();
      return {data, source:'backend'};
    } catch(e) { /* fallback permitted; caller labels provenance */ }
  }
  const r = await fetch(staticPath, {cache:'no-store'});
  if (!r.ok) throw new Error('snapshot HTTP ' + r.status);
  return {data:await r.json(), source:base?'snapshot-fallback':'snapshot'};
};
