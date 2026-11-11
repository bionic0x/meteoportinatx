# Pirineo 0.6.1 — observatorio ampliado

**Ámbito:** Andorra, Puymorens, Cerdanya/Cerdagne, Capcir. Paridad de **navegación, presentación y trazabilidad** con Portinatx, NO de instrumentación. No se heredan datos ni umbrales de mar.

| Vista | Contrato efectivo |
|---|---|
| Vigilancia | Tres ejes separados: aviso institucional AEMET CAP / MeteoAlarm, observación ≤90 min, diagnóstico meteorológico por modelo; fallo de fuente → UNKNOWN |
| Satélite/radar | Enlaces a visores oficiales EUMETSAT, AEMET y Meteocat; raster de Pirineos y rayos siguen **NOT_INTEGRATED**; sin simular cobertura |
| Atmósfera | T, Td, HR, nubosidad, viento, racha y dos perfiles ARPEGE, 700 hPa, Froude, isocero y Tw0 |
| Territorio/corte | DEM Terrarium, mapa de temperaturas, precipitación, nieve por vertiente y corte Andorra–Puymorens–Cerdanya |
| Superficie | AEMET, Meteoclimatic, METAR, Meteociel (red secundaria), Météo-France DPObs opcional (red oficial); inversión/föhn y procedencia |
| Puntos | Pronóstico a altitud DEM y métricas de 24–72 h para collados y estaciones |
| Modelos | AROME HD, ICON-EU, ECMWF IFS por punto; bloques de tres horas de T, Td, HR, viento, nubes, lluvia y nieve |
| Ensemble | Metaanálisis independiente existente ECMWF/ENS, GEFS, ICON-EPS a 15 días; sin probabilidades calibradas |
| Forense | Revisiones entre salidas y contexto ERA5-Land cuando existe; no confundir variaciones de pronóstico con skill observada |
| Gobernanza | Estados y edades de caché por fuente, ausencia de clave o permiso CNP, trazabilidad de las condiciones |
| Laboratorio | Umbral hipotético de racha solo en navegador, sin modificaciones en motor, avisos ni ledger |

## Seguridad, magnitudes y vacío de datos

- El frontend lee datos publicados del **dominio Pirineo**, no los endpoints de Portinatx. La actualización está sujeta al colector local y al workflow de Pages; no equivale a vigilancia continua.
- La compactación de lluvia y nieve exige las **tres horas completas** y con medidas finitas no negativas. Si falta algún dato del bloque, el valor es null, nunca cero.
- Las estaciones AEMET y Météo-France se etiquetan oficiales; Meteociel es secundario y no tiene la misma trazabilidad que la medida original.
- Las observaciones de Météo-France son **datos brutos en tiempo real** (retención 24 h, no archivo climatológico QC). Se limita el número de estaciones, se preserva identificador de 8 dígitos, se emplea hora UTC explícita, se validan unidades K / m/s / Pa y se rechaza >120 min. La lluvia horaria y la racha instantánea no se etiquetan como total diario.
- El conector solo se activa con secreto de Actions llamado METEOFRANCE_API_KEY, por cabecera apikey (tipo API Key del portal; diferente de un token OAuth2 Bearer); no se registra, publica ni envía a terceros. Si falta, marca la fuente sin clave. No se ha verificado el acceso real desde GitHub Actions todavía.
- Los nombres e identificadores se consultan al catálogo oficial; Météo-France modificó identificadores el 16/04/2026, por lo que no se codifican códigos históricos fijos.
- El catálogo no está garantizado en todos los sectores: sin estación o con datos fuera de vigencia, UNKNOWN.
- Avalanchas, rayos, capa de inversión y radar bloqueado por cordilleras requieren fuentes y verificación independientes, especialmente para esquí y montaña. Mantenemos la jerarquía de avisos oficiales.

### Referencias

- https://www.data.gouv.fr/dataservices/api-donnees-dobservation
- https://confluence-meteofrance.atlassian.net/wiki/spaces/OpenDataMeteoFrance/pages/853639294/
- https://confluence-meteofrance.atlassian.net/wiki/spaces/OpenDataMeteoFrance/pages/1603796993/

### Verificación en vivo de autenticación

El despliegue Pages #43069942357 publicó las doce pestañas y el motor 0.6.1, pero la consulta DPObs v2 a /liste-stations recibió HTTP 401 con Authorization: Bearer. La credencial instalada tiene el formato API Key del portal, no el de un acceso OAuth2; el cliente envía ahora apikey. Una publicación posterior debe confirmar HTTP 200 y estaciones frescas antes de declarar esta fuente activa. El probe #43069851447 ensayó la ruta DPObs v1 (no cubierta por la suscripción v2) y concluyó 403: no demuestra que la API v2 esté inactiva. Ninguna clave se ha incluido en archivos ni registros.
