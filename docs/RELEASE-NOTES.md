# Release 0.3.0 — Meta-análisis meteorológico pirenaico

**10-11-2026**. Base Pirineo Nowcast 0.2.0.

### Hecho

- 15 días: ECMWF ENS, GEFS, ICON-EPS y modelos deterministas (GFS/IFS/ICON/AROME/AIFS) con informes de cobertura por modelo.
- 12 referencias altitudinales para seis estaciones; 72 h de físico vertical y DEM intactos.
- Normalización de familias y conteos de miembros reales, calidad de datos y fallo de fuente aislado.
- Revisión por salida y fecha válida sin lookahead; hipótesis contrarian solo si dos familias se revisan en la misma dirección.
- Control estricto de índices teleconectivos, etiquetas `CONTEXT_ONLY`, `STALE_OR_FUTURE`, `UNKNOWN`.
- Forense Brier con 30 fechas independientes mínimas para corregir pesos.
- Interfaz accesible `15 días · metaanálisis`; fuente, hora de captura y estados UNKNOWN/PARTIAL/OK.
- Nuevas pruebas automatizadas y construcción de sitio estático.

### Evidencia de pruebas locales

- **106/106** del motor MeteoPortinatx (lógica sintética).
- **13/13** del motor Pirineo original.
- **12/12** de metaanálisis + integración.
- JavaScript de la página validado sintácticamente.
- No se han ejecutado ni verificado en esta construcción las llamadas reales de los modelos o un despliegue remoto.

### Bloqueo para actualización en producción

El sitio conocido está alojado en un entorno ChatGPT Sites, pero no hay una herramienta de escritura disponible en esta sesión para sustituir el despliegue existente. El repositorio GitHub MeteoPortinatx no aparece entre los repositorios accesibles en la conexión GitHub actual. No se declara publicación en producción.

### Política de evidencia

NO calcular probabilidades locales calibradas a partir del número total de miembros. NO dar por válidos los avisos de IA sin evidencia troposférica. NO tratar registros históricos ERA5 como instrumentales sin etiqueta. NO inventar inicializaciones de modelo, espesores observados, ni aperturas de remontes.
