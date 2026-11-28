// GEO-06: funciones puras del explorador de relieve (lab/terrain/terrain_core.js), con datos sintéticos.
'use strict';
const assert = require('assert');
const path = require('path');
const T = require(path.join(__dirname, '..', 'lab', 'terrain', 'terrain_core.js'));

let n = 0;
function test(name, fn) { fn(); n++; }

test('Terrarium: 0 m y transparencia = NODATA, no cero', () => {
  assert.strictEqual(T.decodeTerrarium(128, 0, 0, 255), 0);
  assert.strictEqual(T.decodeTerrarium(128, 0, 0, 0), null);
  // 2913.5 m → v = 35681.5 → R 139, G 97, B 128
  assert.ok(Math.abs(T.decodeTerrarium(139, 97, 128, 255) - 2913.5) < 1e-9);
});

test('Tesela y píxel: Puigmal en z10', () => {
  const t = T.lonLatToTilePixel(2.1167, 42.3833, 10);
  assert.strictEqual(t.x, 518);
  assert.strictEqual(t.y, 378);
  assert.ok(t.px >= 0 && t.px < 256 && t.py >= 0 && t.py < 256);
});

test('Metros por píxel a 42,5° en z10 ≈ 112 m', () => {
  const m = T.metersPerPixel(42.5, 10);
  assert.ok(m > 110 && m < 114, m);
});

test('Horn: llano, pendiente al este y NODATA', () => {
  assert.deepStrictEqual(T.horn([[5, 5, 5], [5, 5, 5], [5, 5, 5]], 30), { slope: 0, aspect: null });
  const r = T.horn([[30, 15, 0], [30, 15, 0], [30, 15, 0]], 30);   // baja hacia el este
  assert.ok(Math.abs(r.slope - Math.atan(0.5) * 180 / Math.PI) < 1e-9);
  assert.ok(Math.abs(r.aspect - 90) < 1e-9);
  assert.strictEqual(T.aspectName(r.aspect), 'E');
  assert.deepStrictEqual(T.horn([[1, 1, 1], [1, null, 1], [1, 1, 1]], 30), { slope: null, aspect: null });
});

test('Perfil: distancia, extremos y NODATA', () => {
  const s = T.samplePath([1.9, 42.4], [2.0, 42.4], 11);
  assert.strictEqual(s.length, 11);
  assert.ok(Math.abs(s[10].dist - T.haversine([1.9, 42.4], [2.0, 42.4])) < 1e-6);
  const st = T.profileStats([{ z: 1000 }, { z: 1200 }, { z: null }, { z: 1100 }, { z: 1300 }]);
  assert.deepStrictEqual([st.min, st.max, st.ascent], [1000, 1300, 400]);
  assert.ok(Math.abs(st.unknown - 0.2) < 1e-12);
  assert.strictEqual(T.profileStats([{ z: null }]).unknown, 1);
});

test('Bilineal y borde', () => {
  assert.strictEqual(T.bilinear([[0, 10], [20, 30]], 0.5, 0.5), 15);
  assert.strictEqual(T.bilinear([[0, null], [20, 30]], 0.5, 0.5), null);
  assert.strictEqual(T.bilinear([[0, 10], [20, 30]], 1.5, 0.5), null);
});

console.log(`terrain_core: ${n} pruebas OK`);
