# Publicación en GitHub Pages — MeteoPortinatx Unified v0.5.1

## Hosting de lectura: GitHub Pages

- URL pública, con publicación confirmada por el workflow: `https://bionic0x.github.io/meteoportinatx/`.
- Configuración ya aplicada: repositorio → Settings → Pages → Build and deployment → Source: **GitHub Actions**.
- Después: Actions → **Publish unified meteorological website** → Run workflow. El despliegue automático se activa al modificar `main` y cada seis horas (`23 */6 * * *`, UTC). GitHub Actions puede demorar tareas programadas.
- Si faltan datos, son antiguos, o falla alguna exportación, la publicación **se detiene** y no falsifica datos meteorológicos. El sitio ya publicado puede quedar obsoleto; comprobar `core.issued` y los registros de la ejecución.

## Garantías y limitaciones

La automatización ejecuta un único `src/nowcast.py export` para ambos dominios, valida el paquete antes de subirlo con `scripts/build_site.py`, y publica mediante `actions/upload-pages-artifact` y `actions/deploy-pages`. La página incluye `/portinatx/` y `/pirineo/`.

**NO es un servicio de vigilancia cada cinco minutos**: el intervalo nominal son seis horas y los archivos son estáticos. No ofrece notificación push, monitoreo activo, ni archivo forense persistente entre ejecuciones del runner. Render Free ofrece actualmente un backend experimental de solo lectura pero se suspende tras inactividad y no conserva SQLite ni `state.json`; por tanto no habilita vigilancia continua ni archivo forense duradero. Se necesita almacenamiento externo independiente y ejecución regular garantizada para esas funcionalidades.

Solo se cachea `dem.json` (relieve no sensible). El estado, la forense personal y `config.env` jamás se cachean ni se incluyen en el artefacto de Pages. `AEMET_API_KEY` es opcional como GitHub Secret y no debe aparecer en código, logs o JSON. Si la conexión con un proveedor falla, se identifica como `UNKNOWN` o error.

Los resultados muestran estimaciones diagnósticas, no alertas oficiales; siguen mandando AEMET, Protección Civil, SMA, Météo-France y boletines de montaña. Uso de Open-Meteo sujeto a sus condiciones de uso y atribución CC BY 4.0.

## Puente de datos v0.5.1

El backend expone `X-Meteo-Snapshot` y `X-Meteo-Freshness` por CORS. El navegador carga cada dominio como un conjunto atómico: si las partes tienen distinta generación, faltan o caducan, se usa **el conjunto completo** de GitHub Pages. La URL se configura opcionalmente mediante `METEO_BACKEND_URL`, variable pública de Actions. **No se activa hasta desplegar la corrección en Render y validar sus cabeceras reales**. Nunca se pasan claves ni estados privados al navegador.
