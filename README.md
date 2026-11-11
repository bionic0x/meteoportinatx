# MeteoPortinatx Unified · 0.6.0

Radar, avisos Meteoalarm, observaciones METAR y evaluación forense comparten motor para Portinatx y Pirineo. Pirineo excluye mar. [Perfiles, descargas y guía forense](docs/ZONAS-MODULARES.md).

Un solo desarrollo con dos dominios separados: **Portinatx (Ibiza)** y **Pirineo (Andorra, Cerdanya y Capcir)**. El núcleo costero sigue en 0.6.1, el motor pirenaico y su metaanálisis en 0.6.1; la aplicación, API y web usan la versión de integración **0.6.0**.

> Diagnósticos experimentales: **no sustituyen avisos oficiales** (AEMET / protección civil / Meteocat / SMA / Météo-France). Ausencia de una fuente ≠ calma. El aprendizaje forense no altera los avisos oficiales.

## Zonas y módulos compartidos

Portinatx y Pirineo son dos perfiles del mismo proyecto. El nuevo comando `zone`
permite crear perfiles por coordenadas, seleccionar módulos y descargar paquetes
con datos, diagnósticos diarios, ensembles, cobertura y hashes. También verifica e
instala paquetes, conserva un histórico por zona y genera informes HTML sin conexión.
Pirineo excluye el módulo marino. Todo está incluido en el `.pyz`.

```bash
python3 src/nowcast.py zone plan portinatx
python3 src/nowcast.py zone plan pirineo
python3 src/nowcast.py zone --help
```

Consulta [zonas modulares y estado de la paridad](docs/ZONAS-MODULARES.md).
La adquisición, diagnóstico diario, radar, avisos, observaciones e informes forenses son comunes. Las interfaces territoriales conservan sus algoritmos especializados; su paridad completa sigue pendiente.

## Sitio y backend

- **GitHub Pages:** https://bionic0x.github.io/meteoportinatx/ — sitio público con Portinatx y Pirineo, compilado por GitHub Actions cada seis horas y al modificar las fuentes.
- **Render Free (vista previa):** https://meteoportinatx-backend-free.onrender.com/ — API Python de solo lectura. La instancia puede dormirse tras inactividad. No hay disco persistente ni coste contratado; archivos locales, SQLite y cadenas de hashes se pueden perder al suspender, reiniciar o desplegar.
- **Puente web:** `public_fetch.js` descarga un dominio completo desde una única generación del backend, comprueba su `X-Meteo-Snapshot` y `X-Meteo-Freshness` mediante CORS y usa **todos** los archivos de Pages si la API falla o mezcla generaciones. Se activa con la variable **pública** de GitHub Actions `METEO_BACKEND_URL` tras verificar la API; nunca deben añadirse secretos en esa variable.

No hay garantía de ciclos cada cinco minutos en Render Free. GitHub Pages conserva sus propios snapshots incluso con Render suspendido, pero **su cadencia tampoco equivale a nowcast continuo**. El archivo forense de Render Free es volátil: el nombre `forensics.sqlite3` no implica durabilidad.

## Uso local

Requiere Python 3.10+ y biblioteca estándar. El motor puede usar internet y claves opcionales en archivos locales excluidos de Git.

```bash
python3 src/nowcast.py selftest
python3 src/nowcast.py serve --port 8787 --portinatx-interval 300 --pirineo-interval 10800
python3 src/nowcast.py export
python3 scripts/build_site.py
python3 scripts/build.py
python3 scripts/integrity.py --check
```

El portal local es http://localhost:8787/, con `/portinatx/` y `/pirineo/`; incluye las rutas `/public_fetch.js` y `/public_config.js` para que las pantallas no produzcan 404. Las actualizaciones locales se permiten solo desde el mismo origen. El backend público **no** tiene rutas `POST` de actualización.

## Estructura

| Componente | Responsabilidad |
|---|---|
| `src/portinatx_degen.py` | Radar, pluviómetros, CAP, viento, mar, modelos, forense privado |
| `src/pirineo.py` y `src/pirineo_meta.py` | Relieve, perfiles, nieve y ensembles a 15 días |
| `src/nowcast.py` | Orquestador y servidor local unificados |
| `src/nowcast_backend.py` | Colectores Render, API de lectura, snapshots y auditoría temporal |
| `src/public_fetch.js` | Carga atómica por dominio; fallback estático completo |
| `src/route_engine.js`, `src/pirineo_ruta.html` | Planificador GPX privado en navegador (`docs/RUTAS-PIRINEO.md`) |
| `scripts/build_site.py` | Validación de datos y generación atómica de sitio |
| `scripts/integrity.py` | Generación y comprobación de SHA256SUMS, verificado en CI |
| `tests/` | Pruebas sintéticas Python + prueba JS del puente y sus fallos |

**Seguridad:** el `core` público de Portinatx tiene campos permitidos explícitos, la evidencia manual y los controles privados no salen en la API. El estado completo permanece en directorios de datos locales; en Render Free se considera **temporal**, no forense duradero. El almacenamiento en disco externo exige configuración adicional aún no realizada.

## Pruebas y operaciones

CI ejecuta Python 3.10 y 3.11, prueba la carga web en Node, verifica `SHA256SUMS.txt` y genera un `.pyz`. El resultado de las pruebas sintéticas **no calibra** la predicción meteorológica ni garantiza disponibilidad de proveedores externos. El despliegue de Pages requiere datos reales recientes de ambos dominios y falla cerrado si faltan.

Ver [arquitectura](docs/ARQUITECTURA-UNIFICADA.md), [notas de versión](docs/RELEASE-NOTES.md) y [guía del backend gratuito](docs/BACKEND-PERSISTENTE.md). La [evaluación del modelo, los usos y el potencial](docs/EVALUACION-MODELO-USOS-POTENCIAL.md) añade hallazgos de auditoría reproducidos y una hoja de ruta priorizada.

## Verificación prospectiva de pronósticos (investigación P0, sin despliegue)

El módulo aislado [`src/forecast_ledger.py`](src/forecast_ledger.py) congela pronósticos **antes** del inicio de su ventana y permite compararlos luego con una observación instrumental QC PASS del mismo periodo y lugar. También registra exclusiones (`UNKNOWN`, ventana futura, hindcast, falta de medida) y ofrece exportación, importación y un verificador de integridad local. Un import externo **no** se convierte en prueba prospectiva certificada. Consultar [protocolo P0](docs/FORECAST-LEDGER-P0.md).

**No cambia ninguna alerta, no requiere Render ni extrae foros.** Guarda el archivo **fuera** del repositorio y con copias de seguridad independientes: no hay almacenamiento persistente gratuito configurado. Las métricas son experimentales, sin skill meteorológico medido ni probabilidades calibradas.

## Paquetes de zona y evidencias comunes (experimental)

Portinatx y Pirineo comparten la adquisición modular, los indicadores de cobertura, la evaluación
por familias ensemble y los informes HTML verificables. El perfil del Pirineo es interior y excluye
mar; los perfiles personalizados deben elegir explícitamente coordenadas, módulos y entorno.

```bash
python3 src/nowcast.py zone list
python3 src/nowcast.py zone plan portinatx
python3 src/nowcast.py zone plan pirineo
python3 src/nowcast.py zone template pirineo --output pirineo.json
python3 src/nowcast.py zone fetch pirineo --output captura.zip
python3 src/nowcast.py zone inspect captura.zip
python3 src/nowcast.py zone install captura.zip --root /ruta/archivo
python3 src/nowcast.py zone report --pack captura.zip --output informe.html
python3 src/nowcast.py evidence pirineo evidencias.json --as-of 2026-11-11T00:00:00+00:00
```

Los paquetes declaran por variable datos presentes, unidades y procedencia. Los adaptadores de radar, avisos y METAR realizan adquisición pública; su acceso en vivo no se ha podido verificar en este entorno. El comando independiente `evidence` conserva el contrato de metadatos sin autenticar: `PRESENT_UNVERIFIED` no es una alerta oficial ni prueba científica. La evaluación `zone forensic` revisa días archivados; `ledger` mantiene el registro prospectivo P0 con su esquema estricto. Ver [zonas modulares](docs/ZONAS-MODULARES.md).

## Decision P0 — vistas por perfil (preparación MeteoPortinatx 0.6)

La ruta `/decidir/` propone cinco lecturas rápidas sobre **los mismos `core.json`**: casa junto a torrente, barca/amarre, segunda residencia, esquí/montaña y análisis meteorológico. Presenta avisos institucionales, mediciones y estimaciones por separado, con fecha/origen visible y `UNKNOWN` cuando el ciclo es antiguo. Cada caso enlaza a la consola científica completa. **No cambia umbrales, modelos, forense, fuentes ni proveedores.**

En GitHub Pages se publica desde `src/decision_app.html` y `src/decision_cards.js`; el servidor local también los sirve en `/decidir/`. La interfaz no guarda perfiles ni hace recomendaciones de evacuación/navegación. Leer [contrato de producto, frescura y pruebas](docs/DECISION-P0.md). `METEO_BACKEND_URL` continúa siendo opcional y la cadencia de Pages (6 h) **no permite ofrecer un nowcast continuo**.
