# Addendum a la especificación de conectores — fuente `contexto` (kind="context")

**Fecha:** 2026-11-11 · Complementa `claude/especificacion-motor-conectores.md` (no la sustituye; esa especificación se regenera desde el motor y no se ha reescrito a mano). Catálogo y procedencia: `claude/catalogo-fuentes-y-conocimiento.md`.

## Cambios al contrato descrito en §3 de la especificación

1. **Nuevo `kind`: `context`.** `SourceResult.kind` y `Channel.kind` admitían `obs | model | ensemble | institutional`. `context` se usa solo en `SourceResult` (no hay canal `context`). `fuse` filtra por `institutional`, `obs`, `model` y `ensemble`, por lo que **una fuente `context` no puede modificar ningún nivel**. Test: `selftest` («kind='context' no cuenta como canal en la fusión») y `tests/test_knowledge_base.py`.
2. **Registro de fuentes.** Se añade al final de `SOURCES`: `("contexto", "context", lambda: src_contexto())`. Sin caché propia (lee ficheros locales).
3. **Estados.** Sin sidecar válido → `status="deshabilitado"` y `detail` con el estado de cada fichero (`sin_datos`, `caducado`, `invalido`). Con al menos uno `ok` → `status="ok"`. En ningún caso se interpreta ausencia como calma.
4. **Backend.** `nowcast_backend` ya no cuenta como «fuente costera utilizable» una fuente con `kind="context"`: si todas las fuentes reales fallan, el ciclo no se publica aunque el sidecar esté `ok`.
5. **Snapshot.** Clave nueva `context` = `{estado, notas[], detalle, aviso}`. `notas` sitúa la lluvia observada (`*_r1` del canal `lluvia_observada`) en la banda `p50–p90 … p99–max` de la climatología local del sidecar `climatologia_era5land` (`values.precip_1h_mm`). Es informativa. La proyección pública del backend es por lista blanca, así que esta clave **no se publica** en la API pública de Portinatx (sí en el snapshot local y en `render`).
6. **Pirineo.** El `core` incluye `contexto` con estado y procedencia de los sidecars del dominio (sin valores), y `profile_diag` añade `tw07_m`.

## Pruebas
`portinatx_degen.py selftest`: 110 OK (106 previas + 4). `pirineo.py selftest`: 15 OK. `unittest discover`: 109 tests OK (1 omitido), incluidos 19 nuevos en `tests/test_knowledge_base.py`. Todas con datos sintéticos; no validan umbrales ni servicios reales.

## Límites
Ningún sidecar real existe; ningún conector nuevo se ha probado en vivo. Version del motor sin cambiar (0.6.1) y `RELEASE_STATUS.json` sin tocar.
