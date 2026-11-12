# Registro de permisos — ClimayNievePirineos (#9)

**Idioma / Language:** Español · [English](CNP-PERMISO-20261111.en.md)

**Estado al 11/11/2026: difusión de datos con atribución expresamente permitida por el proveedor; acceso automatizado y su cadencia no especificados.** La página [Modo de utilización y características de las estaciones](https://www.climaynievepirineos.com/estaciones/UsoYCaracteristicasCYNP.htm), consultada el 11/11/2026, indica al final que los datos pueden utilizarse en medios, webs, foros y blogs, citando la fuente o enlazando la estación concreta. La página también describe su red como privada. No concreta endpoints, frecuencia de extracción automatizada, retención histórica ni condiciones comerciales. El gate de acceso automatizado se mantiene por prudencia mientras se aclaran esos extremos; esto no debe presentarse como prohibición expresa del proveedor. El foro y las imágenes quedan fuera de esta evidencia.

## Estado de las evidencias

| Campo | Estado |
|---|---|
| Origen y responsable identificados en el artículo | Marco Lobera / ClimayNievePirineos; vigencia del contacto por verificar |
| Lectura programática de tablas de estaciones | NO ESPECIFICADA en el artículo |
| Límites de frecuencia, horarios y caché automatizada | NO ESPECIFICADOS; actualización de tablas cada 10 min no equivale a límite de extracción |
| Difusión de datos en webs y otros medios | PERMITIDA con cita de la fuente o enlace a la estación; detalles de series históricas y conservación no especificados |
| Coordenadas y metadatos instrumentales confirmados por estación | PENDIENTE |
| Permiso para imágenes, comentarios o textos de foros | NO; fuera de alcance |
| Evidencia pública | Artículo del proveedor consultado el 11/11/2026; revocación y condiciones automatizadas no especificadas |

## Consulta pendiente al administrador
Asunto: Solicitud de autorización para uso no comercial de datos de estaciones en MeteoPortinatx

> Estamos desarrollando MeteoPortinatx, herramienta experimental y gratuita para Cerdanya, Capcir y Andorra. Hemos visto que autorizáis difundir datos con atribución. Querríamos aclarar las condiciones para consultar mediante un proceso automatizado las tablas de estaciones de ClimayNievePirineos. No solicitamos acceder al foro privado ni copiar fotografías, mensajes o datos personales. ¿Se autoriza la consulta, bajo qué límite de frecuencia, a qué URLs y estaciones, con qué atribución y política de conservación/republicación? ¿Se permiten métricas agregadas y comparativas? ¿Existe un feed o API preferido? Agradeceríamos también saber cómo revocar el permiso y la fuente de coordenadas/metadatos de cada sensor.

No enviar a direcciones inferidas de terceros. Registrar respuesta con fecha UTC, emisor/rol y medio de verificación en un expediente **privado**; incorporar solo la constancia de autorización y sus términos al repositorio público, sin datos personales del contacto ni capturas privadas. Revisar `robots.txt` y políticas, además de la autorización; ninguno sustituye al otro.

## Gate para habilitar acceso automatizado
- Registrar la evidencia pública de difusión con atribución y aclarar las condiciones aplicables al acceso automatizado, endpoints, frecuencia y fines del proyecto.
- Tasa de peticiones, `User-Agent` identificativo, `If-Modified-Since`/caché, límites de retención y mecanismo de revocación acordados.
- Coordenadas y metadatos del sensor contrastados; pruebas de zona horaria/DST, edad instrumental, duplicados y detección de observación sospechosa.
- Los testimonios comunitarios siguen `UNVERIFIED` con peso cero en alertas y sin copiar nombres, fotos, textos de foro.
- Protocolo de retirada: desactivar variable, detener peticiones, revocar credenciales y eliminar copias conforme al permiso.

**Estado operativo:** el test `tests/test_community_permission.py` ya verifica que, sin permiso, no se accede a la red. No se ha enviado ninguna solicitud de autorización desde esta sesión. #9 permanece abierta.

## Activación automática al documentar las condiciones necesarias

El permiso ya no depende de una variable: es el fichero `permisos/cnp.json` (plantilla y campos en `permisos/README.md`). Basta con subirlo a `main` con los términos reales:
- **Periodo:** se activa el día `valido_desde` y se desactiva sola tras `valido_hasta`. Admite permisos por un periodo determinado o indefinidos (`null`).
- **Ámbito:** `ambito` decide si cubre solo el uso privado/local o también Pages y Render (`METEO_PUBLIC_BUILD=1`). Con ámbito solo privado, la web pública nunca lo usa.
- **Atribución:** se muestra siempre que se usan los datos.
- **Cadencia:** `intervalo_min_minutos` fija el tiempo mínimo entre consultas.
- **Aviso:** el workflow diario `credential-expiry.yml` avisa 14 días antes del vencimiento.
- **Revocación:** borrar el fichero o adelantar `valido_hasta`.

`CNP_PERMISSION_VERIFIED=1` queda solo como interruptor local privado y se ignora en compilaciones públicas.
