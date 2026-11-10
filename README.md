# MeteoPortinatx Unified · 0.5.1

Un solo desarrollo con dos dominios separados: **Portinatx (Ibiza)** y **Pirineo (Andorra, Cerdanya y Capcir)**. El núcleo costero sigue en 0.6.1, el motor pirenaico y su metaanálisis en 0.3.0; la aplicación, API y web usan la versión de integración **0.5.1**.

> Diagnósticos experimentales: **no sustituyen avisos oficiales** (AEMET / protección civil / Meteocat / SMA / Météo-France). Ausencia de una fuente ≠ calma. El aprendizaje forense no altera los avisos oficiales.

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
| `scripts/build_site.py` | Validación de datos y generación atómica de sitio |
| `scripts/integrity.py` | Generación y comprobación de SHA256SUMS, verificado en CI |
| `tests/` | Pruebas sintéticas Python + prueba JS del puente y sus fallos |

**Seguridad:** el `core` público de Portinatx tiene campos permitidos explícitos, la evidencia manual y los controles privados no salen en la API. El estado completo permanece en directorios de datos locales; en Render Free se considera **temporal**, no forense duradero. El almacenamiento en disco externo exige configuración adicional aún no realizada.

## Pruebas y operaciones

CI ejecuta Python 3.10 y 3.11, prueba la carga web en Node, verifica `SHA256SUMS.txt` y genera un `.pyz`. El resultado de las pruebas sintéticas **no calibra** la predicción meteorológica ni garantiza disponibilidad de proveedores externos. El despliegue de Pages requiere datos reales recientes de ambos dominios y falla cerrado si faltan.

Ver [arquitectura](docs/ARQUITECTURA-UNIFICADA.md), [notas de versión](docs/RELEASE-NOTES.md) y [guía del backend gratuito](docs/BACKEND-PERSISTENTE.md).
