# Publicación en GitHub Pages — MeteoPortinatx Unified v0.4.0

## Hosting de lectura: GitHub Pages

- URL de destino, **no confirmar hasta comprobar el workflow**: `https://bionic0x.github.io/meteoportinatx/`.
- Único paso de administración manual, si Pages aún no está activado: repositorio → Settings → Pages → Build and deployment → Source: **GitHub Actions**.
- Después: Actions → **Publish unified meteorological website** → Run workflow. El despliegue automático se activa al modificar `main` y cada seis horas (`23 */6 * * *`, UTC). GitHub Actions puede demorar tareas programadas.
- Si faltan datos, son antiguos, o falla alguna exportación, la publicación **se detiene** y no falsifica datos meteorológicos. El sitio ya publicado puede quedar obsoleto; comprobar `core.issued` y los registros de la ejecución.

## Garantías y limitaciones

La automatización ejecuta un único `src/nowcast.py export` para ambos dominios, valida el paquete antes de subirlo con `scripts/build_site.py`, y publica mediante `actions/upload-pages-artifact` y `actions/deploy-pages`. La página incluye `/portinatx/` y `/pirineo/`.

**NO es un servicio de vigilancia cada cinco minutos**: el intervalo nominal son seis horas y los archivos son estáticos. No ofrece notificación push, monitoreo activo, ni archivo forense persistente entre ejecuciones del runner. Para esas funciones hay que desplegar la aplicación Python en un servicio con disco persistente y ejecución programada, con secretos del servidor y control de acceso para acciones de actualización.

Solo se cachea `dem.json` (relieve no sensible). El estado, la forense personal y `config.env` jamás se cachean ni se incluyen en el artefacto de Pages. `AEMET_API_KEY` es opcional como GitHub Secret y no debe aparecer en código, logs o JSON. Si la conexión con un proveedor falla, se identifica como `UNKNOWN` o error.

Los resultados muestran estimaciones diagnósticas, no alertas oficiales; siguen mandando AEMET, Protección Civil, SMA, Météo-France y boletines de montaña. Uso de Open-Meteo sujeto a sus condiciones de uso y atribución CC BY 4.0.
