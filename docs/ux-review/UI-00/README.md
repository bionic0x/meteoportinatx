# UI-00 · Material de partida para el rediseño (gate G0 del #77)

**Fecha:** 28-11-2026. **Alcance:** estado actual de la interfaz pública, contratos de datos, matriz de funcionalidades,
escenarios de prueba y encargo para los equipos NEXUS. **No cambia código del producto.**
**Sin verificación independiente:** la cuota de agentes Ante/NEXUS está agotada hasta el 2-12-2026. Este paquete lo
ha preparado una sola persona (Claude) y debe revisarlo `testing-evidence-collector` antes de cerrar G0.

| Archivo | Contenido |
|---|---|
| [`capturas/`](capturas/) | 58 capturas del sitio publicado (8 páginas, todas las pestañas, 1440 y 390 px) y `capturas.json` con URL, pestaña, desbordamiento y errores |
| [`contratos/`](contratos/) | Forma de las 13 partes JSON (Portinatx 8, Pirineo 5), extraída de la generación publicada |
| [`MATRIZ.md`](MATRIZ.md) | Funcionalidades × páginas × contratos |
| [`fixtures/escenarios.json`](fixtures/escenarios.json) | 8 escenarios meteorológicos **sintéticos** para diseñar y probar estados límite |
| [`BRIEF-NEXUS.md`](BRIEF-NEXUS.md) | Encargo acotado por equipo (A–G del #77) y agenda del 2-12 |
| [`../vNext/CONTRATO-ESTADO-VISUAL.md`](../vNext/CONTRATO-ESTADO-VISUAL.md) | Contrato de estado común 2D/3D/animación (requisito de G1) |

## 1. Cómo se obtuvo

- **Capturas:** se tomaron con Chrome sin interfaz y Playwright contra `https://bionic0x.github.io/meteoportinatx/`
  el 28-11-2026 a las 18:31 UTC, con locale es-ES y zona Europe/Madrid. En el Pirineo hubo que abrir antes
  `<details id="other-sections">`. El HTML publicado del Pirineo es idéntico byte a byte al de `main` (OBSERVADO,
  SHA-256).
- **Contratos:** se descargaron las 13 partes `api/*.json` publicadas (core emitido a las 13:08–13:10 UTC) y se
  extrajo su forma: claves, tipos, longitudes y un ejemplo truncado. **No se versionan los datos brutos**, que
  incluyen datos de terceros con atribución; solo su forma.
- **Uso por página:** búsqueda léxica de cada clave de primer nivel en `src/*.html` y `src/*.js`. Es una
  **heurística**: da falsos negativos en accesos dinámicos (p. ej. `D.series[pid]`). Las ausencias citadas abajo
  se comprobaron además con `grep` sobre el nombre literal.

## 2. Inventario de páginas y carga de datos

| Página (ruta publicada) | Archivo | Datos | Vistas |
|---|---|---|---|
| Portal `/` | `src/nowcast_hub.html` | `core` de cada dominio | — |
| Portinatx `/portinatx/` | `src/portinatx_app.html` (230 KB) | 8 partes: core, radar, series, atmos, sat, mar, modx, forense | 11 pestañas |
| Pirineo `/pirineo/` | `src/pirineo_app.html` (119 KB) + `pirineo_atmos.js`, `pirineo_observatory.js` | 5 partes: core, dem, grid, series, extended | 5 pestañas visibles + 7 en «Más herramientas» |
| Ruta `/pirineo/ruta/` | `src/pirineo_ruta.html` + `route_engine.js` | dem, grid, core; GPX local | — |
| Decidir `/decidir/` | `src/decision_app.html` + `decision_cards.js` | `core` de ambos dominios | Tarjetas por perfil |
| Dispositivo `/dispositivo/` | `src/device_app.html` + `device_sensors.js` | Sensores del teléfono | — |
| Zonas `/zones/{pirineo,portinatx}/` | Generadas por `scripts/build_site.py` | Paquetes de zona | — |

**Capa de carga (`src/public_fetch.js`):** todo el dominio procede de **una sola generación**: o del backend
(cabeceras `X-Meteo-Snapshot` y `X-Meteo-Freshness` coherentes) o de la instantánea de Pages, nunca mezcladas.
Cualquier rediseño debe conservar este contrato (equipo F).

## 3. Hallazgos G0 (OBSERVADO salvo indicación)

| ID | Sev. | Hallazgo | Evidencia |
|---|---|---|---|
| G0-01 | P1 | **El motor genera diagnósticos que ninguna página muestra:** `core.orografia` (cota de copo efectiva por punto, 129 puntos) y `core.cubeta_fria` (mínima en cubetas). `core.carreteras` solo aparece como enlaces externos, no como dato. | `grep` sin coincidencias en `src/*.html`/`*.js`; claves en `contratos/pirineo_core.schema.json` |
| G0-02 | P1 | **7 de las 12 pestañas del Pirineo están ocultas** en «Más herramientas» (Corte y cotas, Superficie, Modelos, Satélite/radar, Forense, Fuentes y estado, Laboratorio). | `capturas/pirineo-*-1440.png`; `capturas.json` (primer pase: 14 clics fallidos) |
| G0-03 | P1 | **«UNKNOWN» crudo y jerga en la Situación del Pirineo** («sin datos: cnp, relieve_fino», «ESTÁNDAR»), mientras Portinatx ya usa «Desconocido (UNKNOWN)». Contradice la regla de idioma del proyecto. | `capturas/pirineo-vigilancia-1440.png` |
| G0-04 | P1 | **Ciclo caducado en ambas consolas en el momento de capturar** (~320 min). Portinatx lo señala en rojo; en el Pirineo solo figura como «Antigüedad ciclo 321 min» en una tarjeta. | `capturas/portinatx-vigilancia-390.png`, `pirineo-vigilancia-1440.png` |
| G0-05 | P2 | A 390 px las pestañas de Portinatx se recortan («TERR…») sin indicio de desplazamiento. | `capturas/portinatx-vigilancia-390.png` |
| G0-06 | P2 | Ninguna página desborda en horizontal a 390 px **a nivel de documento**. No se midieron contenedores internos desplazables (UI-02 del plan anterior sigue sin verificar con datos reales). | `capturas.json`, `overflow_px` = 0 en 56 de 56 entradas medidas |
| G0-07 | P2 | Claves publicadas sin consumidor aparente: `radar.motion`, `radar.window_skill`, `radar.metrics_radius_km`, `mar.mareografo`, `extended.family_daily`, `extended.deterministic`, `extended.limitations`, `core.horizontes`. **SUPUESTO**: pueden ser intencionadas (auditoría) o huecos de interfaz. | Heurística léxica, §1 |
| G0-08 | — | Las demás observaciones de 00-plan-consolidado (cuatro sistemas visuales, ausencia de pantalla de respuesta en el Pirineo, avisos repetidos) **no se han vuelto a auditar** aquí. | — |

## 4. Límites

- Una sola generación de datos: noche sin avisos activos en el Pirineo y avisos verdes en Ibiza. Los estados
  de aviso, tormenta y nieve solo se cubren con los fixtures sintéticos (F4–F6).
- Las capturas recogen solo la ventana visible (no la página completa) para mantener el tamaño (9 MB).
- Sin lector de pantalla, dispositivo físico, rendimiento medido ni modo de alto contraste.
- Sin datos de usuarios reales: todo juicio sobre comprensión es SUPUESTO.
