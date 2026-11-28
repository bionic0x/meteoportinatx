/* GEO-06: funciones puras del explorador de relieve (sin DOM). Probadas en tests/test_terrain_core.cjs.
   La elevación que devuelven es la REAL del DEM; la exageración vertical del mapa 3D es solo visual. */
(function (root) {
  'use strict';
  const R_EARTH = 6378137;

  /** Terrarium → metros. Un píxel transparente es NODATA: devuelve null, nunca 0. */
  function decodeTerrarium(r, g, b, a) {
    if (a === 0) return null;
    return r * 256 + g + b / 256 - 32768;
  }

  /** Tesela y píxel (fraccionario) de una coordenada en la malla Web Mercator de `size` píxeles. */
  function lonLatToTilePixel(lon, lat, z, size) {
    size = size || 256;
    const n = Math.pow(2, z);
    const xf = (lon + 180) / 360 * n;
    const r = lat * Math.PI / 180;
    const yf = (1 - Math.asinh(Math.tan(r)) / Math.PI) / 2 * n;
    const x = Math.floor(xf), y = Math.floor(yf);
    return { x: x, y: y, px: (xf - x) * size, py: (yf - y) * size };
  }

  /** Metros reales por píxel en una latitud y zoom dados. */
  function metersPerPixel(lat, z, size) {
    size = size || 256;
    return 2 * Math.PI * R_EARTH * Math.cos(lat * Math.PI / 180) / (size * Math.pow(2, z));
  }

  /** Pendiente (grados) y orientación (azimut hacia el que baja la ladera) por Horn, ventana 3×3 [fila][col], fila 0 al norte. */
  function horn(w, res) {
    for (const row of w) for (const v of row) if (v === null || !isFinite(v)) return { slope: null, aspect: null };
    const dzdx = ((w[0][2] + 2 * w[1][2] + w[2][2]) - (w[0][0] + 2 * w[1][0] + w[2][0])) / (8 * res);
    const dzdy = ((w[0][0] + 2 * w[0][1] + w[0][2]) - (w[2][0] + 2 * w[2][1] + w[2][2])) / (8 * res);
    const slope = Math.atan(Math.hypot(dzdx, dzdy)) * 180 / Math.PI;
    if (dzdx === 0 && dzdy === 0) return { slope: slope, aspect: null };
    let aspect = Math.atan2(-dzdx, -dzdy) * 180 / Math.PI;
    if (aspect < 0) aspect += 360;
    return { slope: slope, aspect: aspect };
  }

  const ASPECT_NAMES = ['N', 'NE', 'E', 'SE', 'S', 'SO', 'O', 'NO'];
  function aspectName(a) {
    return a === null ? 'llano' : ASPECT_NAMES[Math.round(a / 45) % 8];
  }

  /** Distancia ortodrómica en metros. */
  function haversine(a, b) {
    const t = Math.PI / 180;
    const dlat = (b[1] - a[1]) * t, dlon = (b[0] - a[0]) * t;
    const h = Math.sin(dlat / 2) ** 2 + Math.cos(a[1] * t) * Math.cos(b[1] * t) * Math.sin(dlon / 2) ** 2;
    return 2 * R_EARTH * Math.asin(Math.sqrt(h));
  }

  /** n puntos equiespaciados entre a y b ([lon, lat]), con la distancia acumulada en metros. */
  function samplePath(a, b, n) {
    const total = haversine(a, b);
    const out = [];
    for (let i = 0; i < n; i++) {
      const f = n === 1 ? 0 : i / (n - 1);
      out.push({ lon: a[0] + (b[0] - a[0]) * f, lat: a[1] + (b[1] - a[1]) * f, dist: total * f });
    }
    return out;
  }

  /** Bilineal sobre una rejilla de elevaciones (null = NODATA → null). */
  function bilinear(grid, fx, fy) {
    const x = Math.floor(fx), y = Math.floor(fy);
    if (y < 0 || x < 0 || y + 1 >= grid.length || x + 1 >= grid[0].length) return null;
    const c = [grid[y][x], grid[y][x + 1], grid[y + 1][x], grid[y + 1][x + 1]];
    if (c.some(v => v === null)) return null;
    const tx = fx - x, ty = fy - y;
    return (1 - ty) * ((1 - tx) * c[0] + tx * c[1]) + ty * ((1 - tx) * c[2] + tx * c[3]);
  }

  /** Resumen de un perfil: mínimo, máximo, desnivel acumulado positivo y fracción sin dato. */
  function profileStats(samples) {
    const z = samples.map(s => s.z);
    const ok = z.filter(v => v !== null);
    if (!ok.length) return { min: null, max: null, ascent: null, unknown: 1 };
    let ascent = 0, prev = null;
    for (const v of z) {
      if (v !== null && prev !== null && v > prev) ascent += v - prev;
      if (v !== null) prev = v;
    }
    return { min: Math.min(...ok), max: Math.max(...ok), ascent: ascent, unknown: 1 - ok.length / z.length };
  }

  const api = { decodeTerrarium, lonLatToTilePixel, metersPerPixel, horn, aspectName, haversine, samplePath, bilinear, profileStats };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.TerrainCore = api;
})(typeof window !== 'undefined' ? window : globalThis);
