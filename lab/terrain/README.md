# Laboratorio GEO-06: explorador de relieve del Pirineo oriental

Página estática y aislada de las consolas operativas. **No se publica en GitHub Pages:** `scripts/build_site.py` no la copia. Publicarla es una decisión del titular.

## Uso local
```bash
cd lab/terrain && python3 -m http.server 8765      # el navegador necesita http(s); file:// no sirve
# http://localhost:8765/                            paquete versionado (z ≤ 10, ≈ 113 m/píxel)
# http://localhost:8765/?datos=completo             paquete completo, si se ha generado (data-full/, no versionado)
```

## Funciones
| Función | Estado |
|---|---|
| Relieve GLO-30 sombreado y navegación 2D/3D | Hecho. La exageración vertical es solo visual |
| Curvas de nivel | Hecho: 200 m en el paquete versionado; 100 m con `--completo --curvas-m 100` |
| Inspector de altitud, pendiente y orientación | Hecho, con la altitud **real** leída de las teselas e interpolación bilineal |
| Pendiente por clases | Hecho: 15–30, 30–35, 35–40, 40–45 y > 45°. No es un boletín de aludes |
| Corte topográfico arbitrario | Hecho: 200 muestras, altitud real, mínimo, máximo, desnivel positivo y fracción sin dato |
| TPI 1 y 5 km, factor de vista del cielo y exposición en 16 sectores | Hecho, solo en los 129 puntos del motor (GEO-01) |
| Modo sin WebGL | Hecho: relieve sombreado estático con explicación |
| Superposición meteorológica (P1) y volumen atmosférico (P2) | Pendiente |
| Comparación de rendimiento con CesiumJS | Pendiente |

## Dependencias y licencias
- **MapLibre GL JS 5.24.1** (BSD-3-Clause), cargada desde jsDelivr con integridad SRI. No hay ningún código de terceros copiado en el repositorio.
- **Sin mapa base de terceros.** Solo relieve propio.
- **Datos:** Copernicus DEM GLO-30, © DLR e.V. 2010-2014 y © Airbus Defence and Space GmbH 2014-2018, proporcionado en el marco de COPERNICUS por la UE y la ESA.

## Regenerar los datos
```bash
SEPI_DATA=$HOME/sepi-data python scripts/fetch_dem_pirineo.py --download
SEPI_DATA=$HOME/sepi-data python scripts/build_terrain_tiles.py                              # data/ (~14 MB)
SEPI_DATA=$HOME/sepi-data python scripts/build_terrain_tiles.py --completo --zmax 12 --curvas-m 100   # data-full/
```
