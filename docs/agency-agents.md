# Divisiones para MeteoPortinatx

Siete perfiles para sesiones Codex con subagentes, adaptados de [agency-agents](https://github.com/msitarzewski/agency-agents) en el commit `8ae6164602c95ca78828b148b9052460ee426885`. Los perfiles son instrucciones breves adaptadas al proyecto; no incorporan el ejecutable o servicio de terceros. La licencia MIT y el aviso de copyright se conservan en `docs/agency-agents-LICENSE.txt`.

| División | Alcance |
|---|---|
| datos | Fuentes, permisos, ingestión, calidad |
| geoespacial | DEM, coordenadas, cotas y vertientes |
| backend | Contratos, motor, archivo y zonas horarias |
| operaciones | Actions, Pages, persistencia, vigilancia |
| calidad | Validación independiente y evidencia |
| interfaz | Consola, accesibilidad y estados de fuentes |
| seguridad | Credenciales, permisos y dependencias |

## Uso

Abre el repositorio en una versión de Codex compatible con subagentes y con confianza en la configuración del proyecto. Solicita, por ejemplo: «Usa datos y calidad para revisar DPObs y XEMA en paralelo; operaciones comprueba el despliegue; integra los resultados con evidencias». El coordinador debe asignar tareas independientes y evitar escrituras concurrentes en los mismos archivos. La configuración de agentes no programa tareas, no crea procesos persistentes, no activa notificaciones ni demuestra por sí sola una conexión meteorológica. La disponibilidad y los permisos de cada agente dependen del entorno de ejecución. No copies credenciales a las instrucciones, archivos o registros.

El diagnóstico meteorológico sigue las instrucciones del proyecto: separar observación de hipótesis y modelo, probabilidad de impacto de severidad condicional, y expresar incertidumbre y hora de los datos. Los avisos oficiales se identifican como tales. No se debe declarar validada una fuente por el mero éxito de fixtures o mocks.

Para validar sintaxis localmente: `python3 -c 'import pathlib,tomllib; [tomllib.loads(p.read_text()) for p in pathlib.Path(".codex").rglob("*.toml")]'`. Esto solo valida sintaxis TOML; el reconocimiento de perfiles y la delegación requieren probarlos en una sesión compatible.
