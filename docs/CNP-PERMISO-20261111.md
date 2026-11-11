# Registro de permisos — ClimayNievePirineos (#9)

**Estado al 11/11/2026: permiso NO VERIFICADO.** `CNP_PERMISSION_VERIFIED` debe quedar **sin definir** (o distinto de `1`). El motor no debe realizar peticiones automáticas a las tablas HTML ni al foro. Una página accesible públicamente no equivale a una licencia de scraping ni de redistribución.

## Estado de las evidencias

| Campo | Estado |
|---|---|
| Titular del contenido y contacto vigente verificado | PENDIENTE |
| Autorización expresa para lectura programática de tablas de estaciones | NO RECIBIDA |
| Límites de frecuencia, horarios y caching | NO AUTORIZADOS |
| Reproducción/publicación de valores o series, atribución y conservación | NO AUTORIZADOS |
| Coordenadas y metadatos instrumentales confirmados por estación | PENDIENTE |
| Permiso para imágenes, comentarios o textos de foros | NO; fuera de alcance |
| Fecha, evidencia escrita y condiciones de revocación | NO DISPONIBLES |

## Solicitud que deberá enviarse al administrador confirmado
Asunto: Solicitud de autorización para uso no comercial de datos de estaciones en MeteoPortinatx

> Estamos desarrollando MeteoPortinatx, herramienta experimental y gratuita para Cerdanya, Capcir y Andorra. Solicitamos permiso escrito para consultar mediante un proceso automatizado las tablas de estaciones de ClimayNievePirineos. No solicitamos acceder al foro privado ni copiar fotografías, mensajes o datos personales. ¿Se autoriza la consulta, bajo qué límite de frecuencia, a qué URLs y estaciones, con qué atribución y política de conservación/republicación? ¿Se permiten métricas agregadas y comparativas? ¿Existe un feed o API preferido? Agradeceríamos también saber cómo revocar el permiso y la fuente de coordenadas/metadatos de cada sensor.

No enviar a direcciones inferidas de terceros. Registrar respuesta con fecha UTC, emisor/rol y medio de verificación en un expediente **privado**; incorporar solo la constancia de autorización y sus términos al repositorio público, sin datos personales del contacto ni capturas privadas. Revisar `robots.txt` y políticas, además de la autorización; ninguno sustituye al otro.

## Gate para habilitar `CNP_PERMISSION_VERIFIED=1`
- Evidencia escrita verificable del administrador/titular; autorización cubre acceso automatizado, endpoints, frecuencia, redistribución y fines del proyecto.
- Tasa de peticiones, `User-Agent` identificativo, `If-Modified-Since`/caché, límites de retención y mecanismo de revocación acordados.
- Coordenadas y metadatos del sensor contrastados; pruebas de zona horaria/DST, edad instrumental, duplicados y detección de observación sospechosa.
- Los testimonios comunitarios siguen `UNVERIFIED` con peso cero en alertas y sin copiar nombres, fotos, textos de foro.
- Protocolo de retirada: desactivar variable, detener peticiones, revocar credenciales y eliminar copias conforme al permiso.

**Estado operativo:** el test `tests/test_community_permission.py` ya verifica que, sin permiso, no se accede a la red. No se ha enviado ninguna solicitud de autorización desde esta sesión. #9 permanece abierta.
