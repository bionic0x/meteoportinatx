# Zonas modulares · recuperación y contrato operativo

## Alcance

La arquitectura comparte utilidades entre zonas, pero **no comparte umbrales locales de alarma**.
Perfiles de origen: `portinatx` (coastal) y `pirineo` (inland). El Pirineo **no** incluye el mar.
Los perfiles personalizados son locales y deben validarse antes de iniciar la adquisición.

Funciones recuperadas del historial de Codex:
- `zone_engine.py`: perfiles con coordenadas, módulos `forecast`, `ensemble`, `terrain` y `marine`, y diagnósticos diarios con cobertura por variable.
- `weather_core.py`: percentiles, fracciones de miembros por institución, bulbo húmedo y estadística marina circular.
- `zone_packages.py`: manifiesto, hashes, archivo histórico por zona, comprobación y comparación de capturas.
- `zone_report.py`: informe HTML de lectura sin conexión, con escapes, datos ausentes y filtro por punto.
- `zone_evidence.py`: normalización offline de metadatos procedentes de radar, avisos, estaciones y forense sin autoridad para alertar.

## Uso

```bash
python3 src/nowcast.py zone list
python3 src/nowcast.py zone plan portinatx
python3 src/nowcast.py zone template pirineo --output pirineo.json
python3 src/nowcast.py zone fetch pirineo --output captura.zip
python3 src/nowcast.py zone inspect captura.zip
python3 src/nowcast.py zone install captura.zip --root ./archivo
python3 src/nowcast.py zone history pirineo --root ./archivo
python3 src/nowcast.py zone report --current pirineo --root ./archivo --output pirineo.html
python3 src/nowcast.py evidence pirineo evidencias.json --as-of 2026-11-11T00:00:00+00:00
```

`evidencias.json` es un documento `{"schema":1,"items":[...]}`. Cada registro incluye
`kind` (`radar`, `warning`, `station`, `forensic`), `source_id`, `observed_at`
(ISO-8601 con offset), `latitude`, `longitude`, `radius_km` y `source_type`.
Las estaciones y los registros forenses precisan `qc=PASS` y `source_type=instrument`;
radar requiere `source_type=radar` y avisos `source_type=institutional`. **Esos campos
son declaraciones, no verificación criptográfica de identidad.**

El estado `PRESENT_UNVERIFIED` significa únicamente que existe un registro espacial y
temporalmente relevante. `UNKNOWN` significa falta de datos utilizables, **nunca ausencia
de peligro**. No se publican propiedades privadas, decisiones de evacuación o avisos de
protección civil a partir de este canal.

## Límites y gates científicos

1. La API Open-Meteo estuvo bloqueada por la política de red del entorno Codex (403).
   La existencia del módulo no demuestra conectividad ni frescura actuales.
2. La descarga `terrain` devuelve una altura de punto; **no** un modelo digital del
   terreno o batimetría.
3. Las fracciones ensemble son crudas y sin calibrar, no probabilidades observadas.
   Una salida con cobertura incompleta no debe convertirse en cero.
4. Las cifras de nieve son válidas solo con día UTC completo y unidades compatibles.
5. El contrato de evidencias no adquiere aún radar real, avisos oficiales ni sensores:
   faltan los adaptadores autenticados y derechos/licencias de acceso.
6. No está conectado todavía con el Forecast Ledger P0 prospectivo; no declarar
   superioridad predictiva hasta acumular episodios medidos independientes.
7. El backend Render Free conserva almacenamiento efímero; su estado no equivale
   a archivo forense duradero ni a monitorización continua.

La validación mínima del paquete: pruebas `unittest`, selftests del motor,
`python3 scripts/integrity.py --check`, empaquetado portable, pruebas browser
cuando Playwright/Chromium están instalados y verificación de datos reales
frescos antes de habilitar fuentes operativas. No se activan nuevas alarmas
ni se modifica la configuración de Render automáticamente.
