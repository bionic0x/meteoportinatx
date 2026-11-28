# UI-00 · Matriz de funcionalidades, páginas y contratos

Leyenda: ● vista dedicada · ◐ parcial o tarjeta · ○ solo enlace · — ausente. Contrato = parte `api/*.json` de
la que se lee (ver `contratos/`). Pestañas por su `data-tab` y su texto visible. Situación al 28-11-2026 (`main` = publicado).

## 1. Funcionalidades

| Funcionalidad | Portinatx | Pirineo | Decidir | Ruta | Portal | Contrato |
|---|---|---|---|---|---|---|
| Avisos oficiales (AEMET CAP, MeteoAlarm) | ● Vigilancia | ● Situación | ◐ tarjeta | ◐ | — | `core.official` / `core.avisos`, `core.avisos_cobertura` |
| Nivel propio (diagnóstico experimental) | ● Vigilancia | ◐ Situación | ● | — | ◐ | `core.precaution`, `core.nowcast` / `core.status` |
| Estaciones y observación | ● Superficie | ◐ Superficie (oculta) | — | — | — | `series.surface`, `series.gauges` / `core.obs`, `core.metar` |
| Radar | ● Satélite | ◐ Satélite/radar (oculta) | — | — | — | `radar.frames` |
| Satélite | ● Satélite | ◐ (oculta) | — | — | — | `sat.layers` |
| Rayos | ◐ (`hazard.rayos`) | — | — | — | — | `core.hazard` |
| Mapa de campos del modelo | ◐ Territorio | ● Mapa | — | ● | — | — / `grid.fields`, `dem` |
| Relieve y corte vertical | ◐ Territorio | ● Corte y cotas (oculta) | — | ◐ perfil de ruta | — | `atmos.terrain` / `dem`, `core.corte` |
| Cota de nieve | — | ● Mapa, Situación | ◐ | ● | — | `core.perfil`, `grid.fields` |
| Cota efectiva por punto (orografía fina) | — | **— (calculada, no mostrada)** | — | — | — | `core.orografia` |
| Cubeta fría (mínimas de fondo de valle) | — | **— (calculada, no mostrada)** | — | — | — | `core.cubeta_fria` |
| Föhn | — | ◐ Superficie (oculta; estado «UNKNOWN» en crudo, `pirineo_app.html:1047`) | — | — | — | `core.foehn` |
| Inversión observada | — | ◐ Superficie (oculta) | — | — | — | `core.inversion_obs` |
| Perfil atmosférico, hodógrafa y θe | ● Atmósfera | ● Atmósfera | — | — | — | `atmos.profile` / `core.perfil`, `core.atmosfera_detalle` |
| Ensemble | ● Ensemble | ◐ 15 días | — | — | — | `series.ensemble` / `extended` |
| Comparación de modelos | ● Modelos | ● Modelos (oculta) | — | — | — | `modx` / `core.modelos` |
| Mar: oleaje, corrientes, marea meteorológica | ● Mar | — | ◐ barca | — | — | `mar.*` |
| Predicción a 15 días y teleconexiones | — | ● 15 días | — | — | — | `extended` |
| Carreteras y aludes | — | ○ enlaces | ◐ | ◐ | — | `core.enlaces` (`core.carreteras` sin uso) |
| Forense y aprendizaje | ● Forense | ● Forense (oculta) | — | — | — | `forense` / `core` |
| Gobernanza, fuentes, edad de los datos | ● Gobernanza | ● Fuentes y estado (oculta) | ◐ | — | — | `core.governance`, `core.sources` / `core.fuentes*`, `core.status` |
| Ruta GPX (local, privada) | — | ○ botón | — | ● | — | `dem`, `grid` |
| Bilingüe ES/EN | ● | ● | ● | ● | ● | — |
| Funcionamiento sin red / instantánea | ● | ● | ● | ● | ● | `public_fetch.js` |
| Temporada (SEPI) | — | — | — | — | — | Sin contrato; UNKNOWN hasta su validación |
| Animación temporal | ◐ fotogramas de radar | ◐ deslizador de hora | — | ◐ | — | `radar.frames`, `grid.time` |
| Terreno 3D | — | — | — | — | — | Prototipo aislado en `lab/terrain/` (GEO-06) |

## 2. Lecturas para el rediseño

1. **El contrato de producto del #77** (mapa primero; vistas Ahora / Pronóstico / Atmósfera / Terreno / Nieve /
   Forense / SEPI) ya tiene datos para todas las vistas salvo SEPI y Terreno 3D. Hay dos funciones del Pirineo
   que pueden aparecer en la vista Nieve sin tocar el motor: `orografia` y `cubeta_fria`.
2. **Las dos consolas comparten funciones con nombres y estructuras distintas** (Vigilancia/Situación,
   Superficie/Diagnóstico, Gobernanza/Fuentes y estado). Sirven de base para unificar la arquitectura de información.
3. **Rayos y animación no tienen vista propia.** El equipo E debe partir de `radar.frames` (observado) y
   `grid.time` (modelo) por separado, sin interpolar entre ambos.
