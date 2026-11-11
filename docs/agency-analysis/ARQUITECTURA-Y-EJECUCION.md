# Arquitectura y ejecución: fiabilidad antes de ampliar la cobertura

Análisis de `fded39b710e1981cb2583adff2462244c151be9f`, 10 de noviembre de 2026. Perfiles aplicados como guías: **Software Architect** y **Data Engineer**, de msitarzewski/agency-agents, commit `8ae6164602c95ca78828b148b9052460ee426885`. Las recomendaciones son propuestas; no se ha cambiado código, infraestructura ni configuración publicada. Los proveedores reales no se han validado en este análisis.

## Decisión arquitectónica propuesta

Conservar un **monolito modular Python con dos dominios**, almacenamiento local sencillo y publicación de instantáneas verificables. La próxima inversión debe resolver identidad de los datos, conservación del histórico y entrega al navegador. Añadir microservicios, Kafka o un lakehouse hoy multiplicaría operación sin resolver los fallos observados.

La aplicación tiene una separación útil entre motor costero, motor de montaña, orquestación y entrega. Aún necesita un contrato transversal que permita responder: «¿Qué conjunto exacto de datos, disponible en qué momento, produjo esta recomendación y con qué cobertura?».

## Mapa actual y consecuencias

| Componente | Evidencia | Implicación |
|---|---|---|
| Motor costero y motor de montaña | `src/nowcast.py:49` | Se conservan ciclos y estados distintos; la orquestación no debería fusionar umbrales meteorológicos. |
| Servidor local con dos recolectores | `src/nowcast.py:95`, `src/nowcast.py:188` | Adecuado para investigación y uso personal; su estado no demuestra disponibilidad remota. |
| Backend público de lectura con exportaciones en subprocesos | `src/nowcast_backend.py:282`, `src/nowcast_backend.py:391` | Un fallo de exportación puede conservar la última generación publicada; hay límites de ejecución de 245/1800 segundos. |
| Versiones públicas y puntero CURRENT | `src/nowcast_backend.py:218` | Reduce exposición de JSON incompletos por petición; no garantiza por sí solo que varias peticiones de una pantalla lean la misma generación. |
| Índice SQLite WAL, cadena SHA-256 y archivo privado de montaña | `src/nowcast_backend.py:155`, `src/nowcast_backend.py:212` | Base razonable para replay; necesita manifiesto integral, resolución de conflictos y respaldo verificable. |
| Web estática dual | `scripts/build_site.py:44` | Se valida ambos dominios antes de reemplazar el sitio. Una avería pirenaica puede bloquear también una nueva publicación costera; es una política de producto explícita que conviene revisar. |
| API preferida con fallback a snapshot | `src/public_fetch.js:3` | Buena estrategia de degradación, afectada actualmente por CORS y potencial mezcla de generaciones. |
| GitHub Actions cada seis horas y Render Free efímero | `.github/workflows/deploy.yml:15`, `render.yaml:17` | Una instantánea programada y un proceso que puede dormir no sustentan promesas de vigilancia continua cada cinco minutos. |

La configuración publicada del entorno de desarrollo no equivale a un despliegue operativo de estos servicios.

## Hallazgos prioritarios

### A1 — El navegador no puede leer la señal de frescura entre orígenes

**Confirmado por inspección del código; no reproducido en navegador en esta revisión.** `public_fetch.js:10` exige `X-Meteo-Freshness === "fresh"`. El backend envía ese encabezado y permite el origen de Pages, pero no incluye `Access-Control-Expose-Headers` (`nowcast_backend.py:359`). Ese encabezado personalizado no es visible para JavaScript en una respuesta CORS ordinaria; el cliente entra en fallback incluso con HTTP 200 y datos frescos.

La prueba actual usa `http.client` (`tests/test_backend.py:124`), que no aplica la política de exposición de encabezados del navegador. Por eso comprobar su existencia en HTTP no cubre el contrato real.

**Aceptación propuesta:** prueba en navegador con frontend y API en orígenes diferentes: backend fresco → origen mostrado backend; backend caducado o caído → fallback explícito. Exponer sólo los encabezados de lectura necesarios y añadir un plazo de espera para que una conexión colgada no retrase indefinidamente el fallback.

### A2 — La identidad de publicación sólo cubre core.json

**Reproducido offline con un Store temporal; no se tocaron datos persistentes.** El hash y el nombre de generación se calculan exclusivamente a partir de `core.json` (`nowcast_backend.py:209`, `nowcast_backend.py:223`). Si cambia `series.json` manteniendo core e issued, el directorio existente gana y la actualización se descarta (`nowcast_backend.py:229`).

En una reproducción mínima pirenaica, publicar `series.value=1` y republicar `series.value=2` con el mismo core dejó servido el valor **1**. Esto importa al reprocesar, corregir un adaptador o regenerar partes; no es necesario que ocurra en cada ciclo normal para invalidar la garantía de identidad del paquete.

**Aceptación propuesta:** un manifiesto canónico con hash de cada parte, esquema, versión del motor y configuración; su hash identifica toda la generación. Mismo manifiesto es idempotente; cualquier parte diferente produce una versión diferente o un conflicto explícito.

### A3 — Una corrección con el mismo issued puede separar índice y publicación

**Reproducido offline.** SQLite impone `UNIQUE(domain, issued)` (`nowcast_backend.py:169`) y usa `INSERT OR IGNORE` (`nowcast_backend.py:241`), mientras que CURRENT se actualiza posteriormente sin comprobar si la inserción representó ese contenido (`nowcast_backend.py:243`).

En la reproducción, cambiar core conservando issued produjo un nuevo hash público; el índice mantuvo una sola fila y el hash anterior. La comparación puntero/índice devolvió **False**.

**Aceptación propuesta:** separar emisión meteorológica e identidad de revisión. Un evento repetido con contenido idéntico no crea duplicados; un contenido distinto con la misma identidad declarada se rechaza o registra como revisión enlazada. Tras reinicio o interrupción en cada fase, CURRENT debe referenciar una generación completa presente en el índice. La cadena debe verificarse de extremo a extremo, no sólo existir.

### A4 — Frescura del ciclo no equivale a frescura del dato

El backend usa edad de `issued` para `fresh/stale` (`nowcast_backend.py:257`); el constructor estático también (`build_site.py:32`). La validación backend requiere al menos una fuente costera `status=ok` o una lista no vacía de puntos de montaña (`nowcast_backend.py:198`). Son controles de publicación, no una garantía de cobertura suficiente para cada decisión.

El propio motor conserva `data_time` (`portinatx_degen.py:439`), pero algunos adaptadores de modelos lo rellenan con la hora de consulta (`portinatx_degen.py:845`). No puede interpretarse uniformemente como hora de inicialización del modelo ni de observación.

**Aceptación propuesta:** campos distintos para `retrieved_at`, `observed_at`, `model_run_at`, `valid_from/to`, `issued_at`, y calidad/disponibilidad por fuente y variable. Cada decisión debe declarar sus entradas mínimas y caducidades. Un ciclo nuevo con radar antiguo sigue teniendo radar antiguo. Mostrar desconocido cuando falta un componente necesario, aunque otros componentes sean utilizables.

### A5 — La pantalla puede combinar datos de distinta generación

Cada petición resuelve CURRENT nuevamente (`nowcast_backend.py:252`). Las páginas cargan partes individualmente (`portinatx_app.html:586`, `pirineo_app.html:242`), y el fallback también se decide por parte. Una actualización intermedia o un fallo parcial puede mezclar core reciente con mar/radar anterior; `S.remote`/`D.remote` se sobrescribe según la última parte recibida.

**Aceptación propuesta:** recuperar primero un manifiesto y fijar una generación durante toda la carga; conservar procedencia, emisión y estado por parte. Mostrar un conjunto anterior coherente si el nuevo está incompleto. La retención de doce versiones (`nowcast_backend.py:244`) debe respetar lectores concurrentes o dar un error recuperable y recargar el manifiesto.

### A6 — Persistencia y salud requieren evidencia operativa

Render usa `/tmp` y `NOWCAST_REQUIRE_DISK=0` (`render.yaml:17`). Las doce generaciones públicas no constituyen un histórico científico. El archivo privado y SQLite requieren almacenamiento durable, política de retención y restauración probada. Una cadena de hashes ayuda a detectar alteraciones respecto de una referencia confiable; no prueba exactitud meteorológica ni impide que un actor con acceso reescriba todo el archivo y su cadena.

`/healthz` devuelve 200 cuando el servidor puede atender (`nowcast_backend.py:373`). Es una sonda de vida, no de frescura meteorológica. `durable_state` se deriva de configuración (`nowcast_backend.py:342`); comprobar un montaje al arrancar no demuestra copias de seguridad ni recuperación tras pérdida del volumen.

**Aceptación propuesta:** separar vida del proceso, preparación del servicio y cobertura de datos. Simular pérdida/restauración del almacén y verificar los manifiestos y fechas preservados. No cambiar el requisito de gratuidad sin una decisión explícita de producto y presupuesto.

## Contrato de datos mínimo propuesto

Cada observación debe incluir fuente, identificador de estación/celda, posición y altitud, variable, unidad, tiempo o ventana de medida, fecha de recepción, calidad y hash de contenido. Cada pronóstico añade proveedor, familia, modelo, inicialización, miembro, plazo y periodo de validez. Un valor ausente se representa como ausencia con motivo, nunca como cero.

La clave de deduplicación se basa en identidad semántica, no en momento de descarga. Una revisión del proveedor se conserva con su versión o hash y relación con el valor previo. Para evaluación se usa únicamente el pronóstico disponible antes de la decisión, junto con las revisiones observacionales claramente identificadas.

Capas prácticas:

1. Respuesta original o referencia reproducible, según licencia y privacidad.
2. Registros normalizados con unidades, tiempos, calidad y deduplicación.
3. Diagnóstico derivado, manifiesto de entradas, versión de reglas y proyección pública.

Esto puede empezar con archivos comprimidos y SQLite. Separar datos privados de exportaciones públicas es obligatorio para mantener el contrato existente, sin introducir una plataforma distribuida.

## Alternativas y costes

| Alternativa | Aporta | Renuncia o condición |
|---|---|---|
| Local + snapshot estático | Bajo coste operativo; buen laboratorio y boletín periódico | El equipo local debe ejecutar y conservar datos; no garantiza vigilancia remota continua. |
| Servicio continuo + almacenamiento durable + snapshot de respaldo | Archivo para validación, cadencia controlable, API coherente | Tiene coste o exige infraestructura propia y operación; hay que medir disponibilidad y capacidad. |
| Recolección programada desacoplada + almacén de objetos + API de lectura | Aísla fallos de captura y entrega, permite replay | Más credenciales, permisos, despliegues y gestión de consistencia; justificar con volumen/usuarios. |

Para el próximo piloto, elegir la primera o segunda según la decisión que se vaya a apoyar. No migrar a la tercera por anticipación.

Modelo de coste mensual propuesto, sin precios supuestos:

`C = cómputo + almacenamiento retenido + peticiones API + salida de datos + copias + observabilidad + horas de operación`.

A las cadencias configuradas, un mes teórico de 30 días y funcionamiento ininterrumpido supone 8.640 ciclos costeros y 240 pirenaicos. **Son ciclos calculados, no consumo medido ni número de peticiones**: cada ciclo puede realizar múltiples consultas, reintentos y cachés. Medir bytes, latencia y peticiones por proveedor antes de proyectar costes.

Para Open-Meteo, AEMET, Meteoalarm, radar, boyas, estaciones comunitarias y DEM: registrar condiciones vigentes de consulta, caché, redistribución, atribución, acceso comercial, cuotas y retención. Accesibilidad técnica no equivale a permiso comercial. No se han verificado aquí contratos/licencias actuales ni tarifas.

## Backlog ejecutable por dependencias

| Prioridad | Trabajo | Dependencia | Criterio de cierre |
|---|---|---|---|
| P0 | Corregir contrato CORS y timeout de fallback | Ninguna | Navegador con dos orígenes demuestra selección backend/fallback correcta. |
| P0 | Manifiesto integral e idempotencia/revisiones | Esquema de identidad acordado | Casos A2/A3 dejan de perder actualizaciones o divergir; interrupciones recuperables. |
| P0 | Estados y procedencia por parte/fuente | Contrato temporal | Inyectar fuente antigua, ausente y nueva; ningún caso hereda frescura ficticia del ciclo. |
| P1 | Fijar generación durante carga | Manifiesto integral | Cambio de CURRENT entre peticiones no mezcla generaciones; fallback coherente. |
| P1 | Archivo durable y restauración | Presupuesto/retención/licencias | Restauración aislada reproduce un ciclo y conserva sus hashes; objetivos de pérdida/recuperación acordados. |
| P1 | Telemetría de captura y calidad | Contrato de fuente | Métricas distinguen proveedor caído, cuota agotada, dato antiguo, parseo fallido y timeout. |
| P1 | Replay científico congelado | Archivo + versiones/configuración | Misma entrada/versiones reproduce salidas; cambios de reglas no alteran evidencia histórica. |
| P2 | Desacoplar publicación por dominio | Política de producto | Fallo de Pirineo no impide boletín costero válido; portal muestra estado individual. |
| P2 | Escalar usuarios/territorios | Piloto útil y coste medido | Demanda y carga reales justifican cada nueva dependencia. |

## Validación y observabilidad

La base existente incluye tests de redacción, conservación de snapshot, datos ausentes, cadena y API de lectura (`tests/test_backend.py:48`). No se reejecutó la suite completa: este trabajo es inspección y dos reproducciones nuevas, locales y efímeras.

Registrar por ciclo: duración total, espera/reintentos, bytes, edad de cada fuente, cobertura por variable, versión/hash publicado, razón de rechazo y latencia hasta cliente. Excluir secretos, coordenadas privadas y textos del propietario de logs públicos. Separar fallo de transporte, dato válido pero antiguo y error científico posterior.

Antes de un piloto real deben completarse: acceso efectivo a proveedores, exportación dual con procedencia y fechas inspeccionadas, ensayo navegador/API, recuperación de archivo y medición de cadencia. Los tests offline habilitan desarrollo; no certifican esos resultados en producción.

## Reproducción mínima de A2 y A3

Ejecutar desde la raíz del repositorio con Python 3.10+. Usa únicamente un directorio temporal y no consulta proveedores. Los resultados siguientes son los observados en el commit analizado; tras corregir el comportamiento deben cambiar o producir un conflicto explícito.

```bash
python3 - <<'PY'
import sys, json, tempfile
from pathlib import Path
sys.path.insert(0, "src")
import nowcast_backend as backend

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    app = root / "app"
    app.mkdir()
    store = backend.Store(root / "store")
    core = {"issued": backend.iso_utc(),
            "puntos": [{"id": "test", "alt": 1000}]}
    for part in backend.PARTS["pirineo"]:
        payload = core if part == "core" else {"value": 1}
        (app / (part + ".json")).write_text(json.dumps(payload))
    store.publish("pirineo", app)

    # A2: cambia una parte, conservando core e issued.
    (app / "series.json").write_text(json.dumps({"value": 2}))
    store.publish("pirineo", app)
    served = json.loads(store.read_public("pirineo", "series")[0])
    print("Valor servido tras actualizar series a 2:", served["value"])

    # A3: cambia core, conservando el mismo issued.
    core["puntos"][0]["alt"] = 2000
    (app / "core.json").write_text(json.dumps(core))
    store.publish("pirineo", app)
    pointer = store.read_public("pirineo", "core")[2]
    summary = store.summary("pirineo")
    print("Puntero coincide con indice:",
          pointer["sha256"] == summary["cycles"][0]["sha256"])
    print("Filas del indice:", summary["cycle_count_in_window"])
PY
```

Salida observada: valor servido **1**, coincidencia **False**, filas **1**. Estos casos demuestran comportamiento bajo republicación controlada; no estiman su incidencia en ciclos reales.


