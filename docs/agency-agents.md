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

## Contrato de coordinación

Cada división recibe una tarea acotada, una base o commit y, si va a escribir, una lista de archivos propios. Las tareas independientes pueden ejecutarse en paralelo; el coordinador integra y resuelve cualquier solapamiento. Calidad revisa el comportamiento y la evidencia de las demás divisiones, pero un resultado de CI no sustituye a una prueba real de las fuentes.

El retorno de cada división identifica: **resultado**, commit o fuente y hora, pruebas ejecutadas con su resultado, limitaciones y siguiente paso. El estado `UNKNOWN` se usa cuando falta evidencia; no equivale a tranquilidad meteorológica ni a una comprobación superada. Las credenciales nunca forman parte de los mensajes o archivos de los agentes.

| División | Entregable mínimo específico |
|---|---|
| datos | Fuente, variable, estación, hora de medición, unidades, QC y permiso. |
| geoespacial | Coordenadas, cotas, resolución, emparejamiento espacial y sus límites. |
| backend | Contrato modificado, compatibilidad, aislamiento y pruebas de fallo. |
| operaciones | Workflow, commit, publicación efectiva, fecha de datos y persistencia real. |
| calidad | Reproducción, esperado y observado, resultados PASS/FAIL/UNKNOWN. |
| interfaz | Estado y procedencia visibles, accesibilidad y comprobaciones en distintos tamaños. |
| seguridad | Amenaza, evidencia sin secretos, corrección y riesgo residual. |

Los archivos definen perfiles, no siete procesos permanentes. El límite `max_threads = 6` se aplica a la concurrencia admitida por el entorno; no garantiza que siete divisiones puedan trabajar simultáneamente. Según la disponibilidad de herramientas, una tarea puede ejecutarse secuencialmente y debe indicarse con honestidad. Para comprobar la activación real, inicia una nueva sesión Codex con el proyecto autorizado, solicita una tarea independiente a dos perfiles y comprueba que los nombres y respuestas aparecen en la sesión. Registrar esa observación por separado de la comprobación estática de TOML.
