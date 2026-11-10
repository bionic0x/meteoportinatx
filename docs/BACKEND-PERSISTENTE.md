# Backend 0.5.1: Render Free y persistencia real

## Estado desplegado

El servicio público `meteoportinatx-backend-free` usa Python de biblioteca estándar en **Render Free** (Frankfurt), sin disco ni base de datos de pago. La API HTTP escucha en el puerto asignado por Render y ofrece `/healthz`, `/v1/status`, `/v1/{dominio}/api/{parte}.json` y `/v1/forensics/summary` como rutas de lectura. `POST` devuelve 405.

**No es persistente ni continuo.** Render Free puede dormir, reiniciar o descartar su almacenamiento local. En consecuencia, `state.json`, los ciclos originales, SQLite y la cadena SHA-256 son **temporales**. El intervalo configurado de Portinatx (300 segundos) y Pirineo (10 800 segundos) es una intención *best effort* únicamente mientras el proceso está activo, no un SLA ni un sistema de avisos.

## Integración segura

El servidor declara `X-Meteo-Freshness` y `X-Meteo-Snapshot` y expone ambas cabeceras por CORS exclusivamente al origen de GitHub Pages (y dos orígenes locales de desarrollo). La web descarga **todas** las partes de cada dominio del mismo snapshot; si alguna falta, está caducada, difiere el identificador o falla la conexión, carga **todas** las partes desde GitHub Pages. No se mezclan generaciones ni procedencias.

La proyección pública `portinatx/core` usa lista blanca explícita, incluso para subcampos de avisos institucionales, fuentes, canales y gobernanza. La evidencia escrita por el propietario no se exporta; los cambios nuevos de esquema se niegan por defecto. Las observaciones y pronósticos están etiquetados como estimaciones propias y nunca como avisos oficiales.

## Forense y verificación

Los datos meteorológicos completos se mantienen en las rutas privadas del motor. SQLite almacena metadatos y enlaza hashes de `core` por dominio; el comando `verify` comprueba la coherencia de esa cadena y el último `core` público si existe. **No es una firma externa ni un registro antimanipulación**: quien pueda alterar la base también puede recalcular la cadena. En Render Free tampoco sobrevive a las suspensiones. Para aprendizaje forense acumulativo hacen falta almacenamiento y copias de seguridad externas, que no están configuradas.

## Operación

```bash
python src/nowcast_backend.py serve --port 10000
python src/nowcast_backend.py status
python src/nowcast_backend.py verify
```

Comprobar `/healthz`, `/v1/status` y la exposición de las cabeceras CORS. En GitHub Actions, configurar `METEO_BACKEND_URL` únicamente con el origen HTTPS público de Render y ejecutar la publicación de Pages; la interfaz conserva el respaldo estático.

## Limitaciones

- Sin persistencia, altas garantías de actualización o cron ininterrumpido.
- Datos históricos de la DANA no se recuperan automáticamente en Render Free.
- Los ensayos sintéticos no sustituyen una validación con fuentes meteorológicas en vivo.
- Los modelos de IA y sus productos requieren comprobar frescura, disponibilidad y procedencia.
- Consultar siempre AEMET / Protección Civil y los servicios oficiales de montaña para decisiones de seguridad.
