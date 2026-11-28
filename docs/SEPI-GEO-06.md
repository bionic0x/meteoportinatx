# GEO-06: explorador de relieve (laboratorio, 28-11-2026)

**Estado:** laboratorio experimental, aislado de las consolas y **no publicado**. No modifica ningún algoritmo operacional.

Se encuentra en [`lab/terrain/`](../lab/terrain/README.md). Productos generados por `scripts/build_terrain_tiles.py` a partir de Copernicus GLO-30 (GEO-00) y de las tablas de GEO-01.

## Decisiones técnicas
- **Motor cartográfico:** MapLibre GL JS 5.24.1, cargado desde CDN con SRI y sin copiar su código. La 6.x se ha descartado de momento porque solo se distribuye como módulos ES. **La comparación con CesiumJS sigue pendiente;** no se ha añadido como dependencia.
- **Elevación:** teselas Terrarium de 256 px.
  - **Paquete versionado:** z7–10, ≈ 113 m/píxel a 42,5° N, 8,6 MB.
  - **Paquete completo local:** hasta z12, ≈ 28 m/píxel, no versionado.
  - **Fuente única para todo:** la misma tesela alimenta el sombreado, el 3D, el inspector y los cortes.
  - **NODATA:** se codifica como transparencia, nunca como 0 m.
- **Altitud real frente a exageración:** la exageración vertical solo afecta al dibujo 3D. El inspector y los cortes decodifican la altitud real de las teselas.
- **Resolución declarada:** la cabecera muestra los metros por píxel del paquete cargado. Las pendientes a ~113 m son menores que las reales a 30 m.
- **Modo sin WebGL:** imagen estática con relieve sombreado.

## Comprobaciones (OBSERVADO)
- **Funciones puras** (`lab/terrain/terrain_core.js`): 6 pruebas en Node, añadidas al CI. Terrarium en Python con 2 pruebas.
- **Teselas frente al DEM de origen, en z10:** Puigcerdà 1.206 m frente a 1.212 m, Puigmal 2.896 m frente a 2.906 m y Pas de la Casa 2.104 m frente a 2.108 m. Las diferencias corresponden al píxel de 113 m.
- **Renderizado en Chrome sin interfaz (WebGL por software):** 2D, 3D, sombreado, pendiente, curvas, puntos, inspector y corte topográfico (42,3 km, de 1.199 a 2.757 m). 0 errores de carga tras corregir la plantilla de URL.
- **No probado:** rendimiento en móvil real ni accesibilidad con lector de pantalla. Quedan para la verificación independiente y el QA de UI-09.

## Límites
- **GLO-30 es un modelo de superficie:** incluye el dosel y los edificios.
- **Pendiente por clases:** es geometría del DEM, no un boletín de aludes.
- **Diagnósticos de los puntos:** proceden de GEO-01 y no están validados.
- **Sin campos meteorológicos.** Cuando se añadan, no se interpolarán para aparentar una resolución de 30 m.
