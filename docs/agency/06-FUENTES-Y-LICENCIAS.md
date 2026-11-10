# Catálogo inicial de fuentes y estado de acceso — 2026-11-11

Convención: `VERIFIED_PUBLIC` = documentación oficial consultada; no significa que cualquier producto del portal esté exento de límites; `INDIRECT` = fuente secundaria/indexación; `BLOCKED` = no hubo acceso directo ni autorización; `IN_CODE` = integración existente, permiso por confirmar.

| Origen | Clase | Situación | URL / referencia |
|---|---|---|---|
| AEMET OpenData | observación / predicción / avisos | `VERIFIED_PUBLIC` API gratuita, catalogada; clave y atribución según producto | https://www.aemet.es/es/datos_abiertos/AEMET_OpenData |
| AEMET condiciones | permiso / atribución | `VERIFIED_PUBLIC` prohíbe desnaturalizar los datos; citar origen | https://www.aemet.es/es/nota_legal |
| Météo-France obs | observación estaciones francesas | `VERIFIED_PUBLIC` API con cuenta y condiciones; conjuntos 6min/hora | https://www.data.gouv.fr/dataservices/api-donnees-dobservation |
| Météo-France catálogo | licencias diferenciadas | `VERIFIED_PUBLIC` unas libres y otras sujetas a licencia/pago | https://meteofrance.fr/missions/la-collecte-et-la-mise-disposition-des-donnees-meteorologiques |
| EUMETNET OPERA | radar europeo | `VERIFIED_PUBLIC` productos CIRRUS 5min 1km y NIMBUS 15min 2km; acceso MeteoGate con CC BY 4.0 y límites del servicio | https://www.eumetnet.eu/observations/weather-radar-network/ |
| ClimayNievePirineos estaciones | estaciones y metadatos | `IN_CODE` 4 rutas HTML en `src/pirineo.py` pero propietario/licencia/coords pendientes | https://www.climaynievepirineos.com/estaciones.htm |
| ClimayNievePirineos foro | testimonios episodios | `BLOCKED` navegación directa devolvió HTTP 403; TOS, robots y derecho de reutilización no verificados | https://www.climaynievepirineos.com/foro/ |
| Presentación histórica CyNP | contexto red y foro | `INDIRECT`, discusión histórica 2006, no demuestra acceso 2026 ni licencia | https://foro.tiempo.com/presentacion-web-sobre-el-clima-de-los-pirineos-t47767.0.html |
| Nevasport seguimiento 2026–27 | análisis de modelos por comunidad | `SECONDARY` posts no son mediciones oficiales; separar predicción y observación | https://www.nevasport.com/phorum/read.php?48%2C4698611%2C4701183%2Cquote=1 |
| Meteoforum.cat Nov 2026 | reportes locales / fotos | `SECONDARY`; permisos de reutilización sin verificar | https://www.meteoforum.cat/thread/596-seguiment-meteorol%C3%B2gic-novembre-2026/ |
| Agency Agents | roles de revisión | `VERIFIED_PUBLIC` README + perfiles y licencia MIT; NO motor autónomo alojado | https://github.com/msitarzewski/agency-agents |

## Lo que hace falta antes de aceptar datos de comunidad

1. **Permiso / términos:** contacto con CNP o revisión verificable de licencias y robots; no intentar saltar 403; no asumir que enlazar permite copiar.
2. **Datos de estación:** coordenadas, altitud, variables, calidad, sello horario y latencia; distinguir nieve natural vs acumulación de producción artificial, estación expuesta vs abrigo.
3. **Foros:** URL estable, fecha original, lugar/cota, fenómeno y ventana de acumulación. No almacenar alias, identificadores personales, domicilio, fotos, texto completo ni comentarios irrelevantes. Evitar duplicados/reposts.
4. **Reconocimiento:** marcar `UNVERIFIED` hasta contraste independiente, sin cambiar alertas ni skill score.
5. **Retención y derechos:** definir período de conservación, opción de borrar aportación cuando corresponda, audit trail técnico y base legal apropiada antes de servicio público.

## Prioridad de fuentes para un MVP gratuito

Primero AEMET OpenData y productos abiertos verificables de Météo-France y EUMETNET; después Catálogo SMA/Meteocat según documentación específica; por último contribuciones voluntarias y, solo si se permite, estaciones CNP. **No es necesario construir de cero un radar europeo si ya hay compuesto OPERA accesible y usable según licencia**. La implementación concreta y la cobertura real de cada producto quedan por validar con llamadas de prueba y límites de cuota.
