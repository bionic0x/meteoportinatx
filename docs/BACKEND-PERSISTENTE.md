> **ACTUALIZACIÓN 2026-11-10 · modo exclusivamente gratuito.** El despliegue actual utiliza Render Free sin disco persistente. Esta guía documenta la arquitectura duradera original, **que no se activa** porque exige recursos de pago. En la instancia gratuita, los ciclos guardados localmente y SQLite son volátiles y desaparecen con sleep, restart o deploy; tampoco existe una garantía de ejecución cada cinco minutos. La web GitHub Pages sigue siendo el respaldo de datos de ambos dominios. Véase [Render Free](https://render.com/docs/free).

# MeteoPortinatx Backend 0.5.0 — despliegue verificable

## Objetivo y límites

La interfaz pública sigue en GitHub Pages. Un único servicio Python aloja dos colectores (`portinatx`: 300 s después de completar cada ciclo; `pirineo`: 10 800 s), archivos de estado privados bajo un disco persistente y API HTTP de lectura. El horario es **best effort**: no hay una garantía de latencia de 5 min; el propio ciclo de Portinatx puede tardar varios minutos. El servidor no emite avisos oficiales.

### Persistencia

Render Blueprint `render.yaml` configura `starter` (de pago) con disco `/var/data` de 5 GB. Render Free **no** conserva estado local entre reinicios. El motor guarda `state.json`, `cycles/`, `log.jsonl`, cachés y ensambles bajo `PORTINATX_HOME` / `PIRINEO_HOME`; el servicio agrega `forensics.sqlite3` en modo WAL, cadena SHA256 por dominio y archivos históricos inmutables del Pirineo (core/series/extended comprimidos). Las instantáneas públicas se proyectan en directorios versionados y el puntero `CURRENT.json` se sustituye atómicamente. Las colecciones fallidas mantienen el último snapshot pero lo etiquetan `STALE`. **No hay poda automática de históricos forenses**: monitorizar espacio en disco y configurar copia de seguridad antes de producción. Las instantáneas públicas intermedias se limitan a las 12 últimas por dominio.

### API

- `GET /healthz` — disponibilidad del proceso (no garantiza frescura de observaciones).
- `GET /v1/status` — hora, frescura, éxito/error por dominio.
- `GET /v1/{portinatx|pirineo}/api/{core|...}.json` — proyección pública de datos, con `X-Meteo-Freshness` y CORS limitado al origen de GitHub Pages.
- `GET /v1/forensics/summary` — metadatos SHA y cadena forense sin observaciones privadas.
- `POST` — **405** siempre. No existe endpoint de actualización pública.

La vista pública de `portinatx/core` elimina texto libre de disensos, pruebas del propietario, overrides, predicciones privadas, evidencias de canales y decisiones. El contenido interno no está expuesto por rutas arbitrarias. La gobernanza completa permanece en disco privado. No usar esta API para decisiones de emergencias.

### Puesta en marcha

1. Instalar/conectar el plugin **Render**, revisar coste de `Starter` y volumen de 5 GB y aprobar el cargo. Importar el Blueprint del repositorio `bionic0x/meteoportinatx` en el dashboard de Render.
2. Confirmar que `https://<dominio-render>/healthz` devuelve `200`, comprobar que `GET /v1/status` pasa a `FRESH` después de completar colectores y que `POST /v1/portinatx/api/refresh` devuelve `405`.
3. En GitHub → Settings → Secrets and variables → Actions → **Variables**, crear `METEO_BACKEND_URL` con el origen HTTPS real (sin ruta, barras finales ni credenciales).
4. Ejecutar manualmente `Publish unified meteorological website`. El generador incorpora `public_config.js` con la URL pública, nunca claves. Las vistas prefieren API en tiempo real; si falla, sirven el snapshot marcado como respaldo. GitHub Pages continúa actualizándose cada seis horas.
5. Revisar gestión de copias de seguridad del disco y espacio disponible, límites de peticiones a proveedores y dispositivos móviles. Probar recuperación real tras reinicio del servicio: los tests unitarios no sustituyen un ensayo en Render.

### Manual local

```bash
NOWCAST_DATA_ROOT=$PWD/backend_state PORTINATX_HOME=$PWD/backend_state/portinatx PIRINEO_HOME=$PWD/backend_state/portinatx/pirineo python src/nowcast_backend.py serve --port 10000
curl http://localhost:10000/healthz
curl http://localhost:10000/v1/status
```

### Riesgos reconocidos

- Un disco Render solo permite una instancia. No escalar a múltiples instancias con el mismo SQLite.
- El proceso requiere internet y depende de los proveedores; `UNKNOWN` no equivale a tiempo seco.
- La persistencia del disco no reemplaza backups externos de los ciclos inmutables.
- Un estado sin datos aún sirve `/healthz`, pero `/v1/status` señala `UNKNOWN` y las rutas de datos devuelven 503.
- No se activan avisos push ni endpoints de control remoto sin una política de autenticación y autorización independiente.
