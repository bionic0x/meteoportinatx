# Catálogo de fuentes, contexto climatológico y conocimiento con procedencia

**Estado:** contrato y lectura implementados y probados con datos sintéticos. **Ningún sidecar real existe todavía** y **ninguna fuente nueva se ha probado contra su servicio real**. Nada de esto altera niveles de alerta. Documento hermano en el proyecto Claude: `claude/catalogo-fuentes-y-conocimiento.md`.

## 1. Qué se añadió

| Pieza | Dónde | Efecto |
|---|---|---|
| Catálogo de fuentes con licencia y estado de verificación | `src/knowledge_base.py` (`SOURCE_CATALOG`) | Documentación ejecutable; test de consistencia |
| Priors con procedencia (`HYPOTHESIS`) | `knowledge_base.PRIORS`, `SYNOPTIC_PRIORS` | Solo el umbral de bulbo húmedo se usa; los sinópticos `used_in_fusion=False` |
| Procedencia de umbrales | `knowledge_base.THRESHOLD_PROVENANCE`, `METEOALERTA_ANNEX1 = None` | Declara qué umbrales de `CFG` no están verificados; test contra deriva |
| Lectura validada de sidecar | `knowledge_base.read_sidecar`, `context_bundle` | `ok / sin_datos / caducado / invalido`; nunca lanza |
| Fuente `contexto` | `portinatx_degen.src_contexto` (`kind="context"`) | `deshabilitado` si no hay sidecar válido (UNKNOWN). No entra en `fuse` |
| Nota de contexto de lluvia | `portinatx_degen.context_notes`, clave `context` del snapshot | Sitúa mm/1 h observados en la banda climatológica; informativo |
| Bloque `contexto` en Pirineo | `pirineo.py` (core) | Estado y procedencia de sidecars de Pirineo, sin valores |
| Fase por bulbo húmedo 0,7 °C | `pirineo.snow_frac`, `profile_diag.tw07_m` | Rampa centrada en 0,7 °C (antes 0,5 °C sin procedencia); `tw07_m` es diagnóstico adicional. Offsets de cota existentes sin cambios |
| El backend no cuenta `context` como fuente utilizable | `nowcast_backend.py` | Una fuente de contexto no puede sostener la publicación si fallan todas las reales |

## 2. Principios

1. **Núcleo sin dependencias.** `xarray`, `cdsapi`, `copernicusmarine`, `satpy`, `scores`… van en un sidecar aparte que escribe JSON. Si falta, el núcleo no se rompe.
2. **Contexto ≠ observación ≠ aviso ≠ modelo.** Un reanálisis sirve de prior o de percentil de contexto, nunca de confirmación.
3. **Ausencia de dato no es calma.** Cualquier estado ≠ `ok` ⇒ UNKNOWN.
4. **Sin umbrales inventados.** Los umbrales Meteoalerta están en los Anexos 1/2 del plan (no obtenidos). `METEOALERTA_ANNEX1` queda en `None` hasta cargarlos con procedencia.
5. **Calibrar con muestra suficiente.** Umbral de fase y percentiles son hipótesis hasta tener ≥30 eventos locales.

## 3. Contrato del sidecar

Fichero `<dir>/<nombre>.json`; `<dir>` = `$METEO_SIDECAR_DIR` o `<HOME>/sidecar`. Nombres conocidos y caducidad máxima:

| Nombre | Dominio | Caducidad |
|---|---|---|
| `climatologia_era5land` | portinatx | 45 d |
| `climatologia_cerra` | pirineo | 45 d |
| `sst_cmems` | portinatx | 48 h |
| `nieve_hrsi` | pirineo | 7 d |
| `verificacion_scores` | portinatx | 10 d |

```json
{
  "schema": 1,
  "name": "climatologia_era5land",
  "generated_at": "2026-11-11T06:00:00+00:00",
  "source": "ERA5-Land, celda más próxima a Portinatx, 1991-2020",
  "licence": "CC-BY 4.0",
  "domain": "portinatx",
  "kind": "context",
  "values": {"precip_1h_mm": {"p50": 0.2, "p90": 4.0, "p95": 8.0, "p99": 20.0, "max": 55.0}}
}
```

Se rechaza (`invalido`) si: falta una clave, hay claves no previstas, `schema` ≠ 1, `name/kind/domain` incoherentes, `generated_at` sin zona o en el futuro, `values` no es un objeto finito y acotado (NaN/Infinity), o el nombre no cumple `^[a-z0-9_]{1,40}$`. Esquema de `values` hoy interpretado: solo `precip_1h_mm` (tabla de percentiles, monótona). El resto de sidecars se leen y publican su estado, pero ningún código interpreta aún sus valores.

## 4. Qué NO está hecho

- No hay sidecar real (descarga de ERA5-Land/CERRA/CMEMS/HR-S&I, cálculo de percentiles) ni su workflow.
- Los umbrales de Meteoalerta no se han cargado.
- 0,7 °C es literatura de Cataluña aplicada a Cerdanya/Andorra sin calibrar; la rampa y `tw07_m` son hipótesis.
- Licencias marcadas `UNVERIFIED` en el catálogo deben comprobarse antes de redistribuir datos derivados (Meteocat en particular).
- El archivo horario de AEMET (B954/LEIB) debe empezar a archivarse ya: no hay backfill. Conecta con `docs/FORECAST-LEDGER-P0.md`.

## Sidecar adicional: ERA5-Land Pirineo (manual y experimental)

El generador `scripts/sidecar_era5land_pirineo.py` calcula tablas mensuales de lluvia diaria en días húmedos para puntos del Pirineo a partir de series temporales ERA5-Land. Su convención de acumulados y la estructura CSV se validan de forma sintética; **no se ha ejecutado ninguna petición real al CDS**. Antes de uso operativo hay que ejecutar `--probe` y comprobar cobertura, periodos, metadatos, condiciones de licencia y atribución.

Comandos de referencia: `python scripts/sidecar_era5land_pirineo.py --probe` y `python scripts/sidecar_era5land_pirineo.py --from-dir DIR --out data/sidecar`. El workflow `.github/workflows/sidecar-era5land.yml` es exclusivamente manual y genera un artefacto para revisión; no modifica el sitio ni Render.

La salida opcional `climatologia_era5land_pirineo.json` es un prior científico. `pirineo.core.contexto.notas_lluvia_24h` solo muestra la comparación de pronósticos frente a percentiles; no modifica avisos, cálculo de nieve ni niveles de alarma. Falta de fichero, formato inválido o caducidad => `UNKNOWN`.
