# Un núcleo común, perfiles por zona

Dirección fijada el 11 de noviembre de 2026: Portinatx y Pirineo son dos zonas del mismo producto, con capacidades generales compartidas y módulos específicos de su territorio. Pirineo es una zona interior y excluye el mar. Nuevos usuarios deben poder seleccionar puntos y módulos para su territorio. La disponibilidad de un módulo depende de sus fuentes; no se trasladan umbrales locales de aviso de una región a otra.

## Implementado en esta iteración

`src/zone_engine.py`, accesible mediante `nowcast.py zone`, usa un único flujo para ambas zonas y para perfiles personalizados. No necesita dependencias externas a Python. El paquete portable `.pyz` incluye este motor.

| Módulo | Datos seleccionados | Aplicación |
|---|---|---|
| `forecast` | Temperatura, rocío, precipitación, nieve, viento y rachas, 7 días | Igual para cualquier punto; diagnóstico diario UTC con cobertura y bulbo húmedo aproximado |
| `ensemble` | Temperatura, precipitación y nieve por miembros de ECMWF/NCEP/DWD, 7 días solicitados | Mismo conector en ambas zonas; disponibilidad y alcance reales dependen del proveedor |
| `terrain` | Elevación puntual | Igual para cualquier punto; todavía no descarga un DEM regional |
| `marine` | Altura, dirección y periodo de ola, 7 días | Solo perfiles costeros o mixtos; excluido de Pirineo y de perfiles interiores |

Las plantillas difieren en puntos y selección predeterminada. Pirineo incluye inicialmente tres puntos representativos y no selecciona mar; no es un inventario completo de sus estaciones. Pueden editarse o añadirse puntos hasta el límite de 25 por paquete. El catálogo es común; la selección respeta el territorio. `setting: inland` impide activar `marine`. Portinatx usa `coastal`. Un perfil nuevo es interior por defecto; puede declararse `--setting coastal` o `mixed` cuando corresponda.

## Comandos

Desde la raíz del repositorio:

```bash
# Inspeccionar perfiles y módulos disponibles, sin red.
python3 src/nowcast.py zone list

# Consultar peticiones iniciales y fuentes seleccionadas.
python3 src/nowcast.py zone plan portinatx
python3 src/nowcast.py zone plan pirineo

# Exportar una plantilla editable. No sobrescribe archivos existentes.
python3 src/nowcast.py zone template pirineo --output /tmp/mi-pirineo.json

# Crear una zona propia y elegir únicamente los módulos necesarios.
python3 src/nowcast.py zone init --id mi_zona --name 'Mi zona' \
  --latitude 41.4 --longitude 2.1 --setting inland --modules forecast,ensemble,terrain \
  --output /tmp/mi-zona.json
python3 src/nowcast.py zone plan /tmp/mi-zona.json

# Descarga real, sujeta a acceso de red, disponibilidad y condiciones de proveedor.
python3 src/nowcast.py zone fetch /tmp/mi-zona.json --output /tmp/mi-zona.zip
```

También funciona `python3 dist/MeteoPortinatx.pyz zone …`. El build regenera `dist/zones/portinatx.json` y `dist/zones/pirineo.json`; copie esas plantillas fuera de `dist/` antes de personalizarlas. No ejecuta los motores regionales heredados con coordenadas cambiadas: el nuevo flujo tiene su propio perfil y sus resultados quedan dentro del paquete elegido.

## Paquete generado

- `zone.json`: perfil, puntos y selección de módulos.
- `manifest.json`: fecha de recogida, URL, estado, cobertura disponible y SHA-256 por archivo.
- `data/<punto>/<modulo>.json`: respuesta del proveedor validada estructuralmente; conserva unidades, tiempos y valores ausentes.
- `diagnostics/<punto>/ensemble.json`: fracciones de miembros de lluvia ≥10 mm y nieve ≥5 cm por familia; soporte y denominadores por variable, días completos y unidades verificadas. No son probabilidades calibradas.
- `diagnostics/<punto>/marine.json`: máximos diarios de altura y periodo, dirección media circular; solo cuando se selecciona mar.
- `diagnostics/<punto>/daily.json`: acumulados diarios de lluvia/nieve, racha máxima, temperatura mínima y bulbo húmedo mínimo para `forecast`. Solo hay total diario cuando están las 24 horas UTC y todos los valores necesarios. Se mantiene cobertura por variable.

El ZIP no incorpora claves ni código remoto. Nunca se sobrescribe un paquete existente. Un proveedor fallido queda como `UNKNOWN`; el conjunto queda `PARTIAL` si solo algunos módulos responden. El comando devuelve código 1 si no se descargaron todas las respuestas seleccionadas. `AVAILABLE` describe una respuesta descargada, no ausencia de huecos, habilidad meteorológica ni calibración: consultar la cobertura y los valores nulos.

La elevación puntual no equivale a un modelo de relieve. Los acumulados de nieve no equivalen a espesor del manto, transitabilidad ni riesgo de aludes. Los diagnósticos compartidos no adoptan los umbrales de Portinatx ni los de Pirineo.

## Usar los paquetes sin conexión

```bash
# Comprobar integridad, inventario, perfil y respuesta de cada fuente.
python3 src/nowcast.py zone inspect /tmp/mi-zona.zip

# Guardar por zona y hash; no mezcla datos de ubicaciones diferentes.
python3 src/nowcast.py zone install /tmp/mi-zona.zip --root /tmp/mis-observatorios
python3 src/nowcast.py zone history mi_zona --root /tmp/mis-observatorios

# Crear una vista HTML autónoma, sin librerías ni peticiones externas al abrirla.
python3 src/nowcast.py zone report --current mi_zona --root /tmp/mis-observatorios \
  --output /tmp/mi-zona.html
# También se puede revisar directamente un paquete parcial sin activarlo.
python3 src/nowcast.py zone report --pack /tmp/mi-zona.zip --output /tmp/revision.html

# Comparar dos consultas de la misma configuración, en días válidos comunes.
python3 src/nowcast.py zone compare /tmp/consulta-anterior.zip /tmp/consulta-nueva.zip
```

El informe muestra puntos, fuentes, cobertura por variable, escenarios por familias y mar únicamente en los perfiles que lo incluyen. La etiqueta de instantánea y las fechas son visibles: el HTML no se convierte en información actual al abrirlo. El filtro de puntos funciona sin conectividad. Se recalculan los diagnósticos con el código local a partir de los datos verificados, sin ejecutar contenido del paquete.

El verificador rechaza duplicados, rutas no previstas, inventarios incompletos, valores numéricos inválidos y hashes discordantes. No extrae el ZIP ni carga código del paquete. Límite: 128 MiB comprimidos/descomprimidos, 25 MB por entrada y 256 entradas. Los checksums permiten detectar corrupción; no son firma de autoría ni validación meteorológica.

El archivo conserva cada ZIP por su SHA-256. Solo un paquete `AVAILABLE` puede activar `CURRENT`, y una captura anterior no reemplaza a otra posterior. Un paquete parcial o fallido queda archivado para revisión y conserva el último completo. Los campos ausentes siguen teniendo cobertura incompleta aunque un paquete sea `AVAILABLE`. El archivo se usa con un único instalador a la vez; no es un servicio multiusuario.

`compare` compara acumulados y extremos del mismo día válido, punto, perfil y unidad. Exige una consulta posterior; los valores ausentes o unidades no verificadas dan delta desconocido. Es un cambio entre consultas, no error frente a observaciones ni prueba de skill. Cambiar puntos o módulos requiere un análisis separado, no una comparación aparentemente equivalente.

## Paridad que todavía falta

El nuevo flujo comparte adquisición, empaquetado y diagnóstico básico. Las dos interfaces heredadas y todos sus algoritmos especializados **todavía no tienen paridad completa**. El paquete de zona no alimenta automáticamente esas interfaces.

| Capacidad que debe extraerse al núcleo común | Trabajo pendiente |
|---|---|
| Satélite y cobertura geográfica exacta | Radar, METAR y avisos por áreas implementados; pendientes satélite, polígonos oficiales y otras redes locales |
| DEM regional, perfiles verticales y diagnóstico de relieve | Descarga regional acotada, caché, procedencia y parametrización de puntos, transectos y exposiciones |
| Calibración y replay físico | Archivo y evaluación forense diaria implementados; pendientes correcciones aprendidas, simulación física e inferencia fuera de muestra |
| Metaanálisis extendido y diagnóstico marino | Eliminar estaciones/boyas/ventanas fijas; conservar soporte por variable y verificación temporal/espacial |
| Configurador gráfico | Informe común y descargas web implementados; pendiente edición visual del perfil |
| Instalación/importación de packs | Verificación, archivo por zona, historial e informe implementados; pendiente caché incremental de proveedores y gestión multiusuario |

Esta matriz sustituye la prioridad anterior de tratar Pirineo únicamente como expansión posterior: las capacidades compartidas deben desarrollarse y probarse sobre ambas zonas.

## Correcciones asociadas

Se corrigió cobertura diaria de nieve y soporte por métrica en el metaanálisis, y cobertura de ventanas 24/72 h en montaña. En la web, el contador junto a nieve se refiere ahora a familias que aportan esa métrica.

El backend identifica el paquete público completo mediante un manifiesto; publicar contenido distinto con el mismo `issued` provoca un error explícito. Para una corrección debe emitirse un nuevo ciclo. Los punteros antiguos con hash de core siguen siendo legibles; su republicación requiere una nueva emisión. El nuevo `sha256` de publicación representa el manifiesto completo, no exclusivamente `core.json`.

Un fallo al escribir CURRENT deja el índice registrado y el puntero anterior; reintentar exactamente el mismo ciclo repara el puntero sin duplicar la cadena. El servicio mantiene el modelo existente de un único publicador por directorio de datos. No se ha añadido coordinación de múltiples procesos ni recuperación automática de CURRENT al arrancar.

## Verificación y límites actuales

Se verifican ambos perfiles, exclusión del mar en Pirineo, perfiles personalizados, hashes, instalación, histórico, comparación y fallos de proveedor con pruebas offline. Chromium comprueba el backend entre orígenes y el informe común en móvil, incluidos filtro de puntos y valores ausentes. En este navegador gestionado se sirve el HTML por HTTP local porque la política bloquea `file://`; la vista no necesita servicios ni recursos externos.

La consulta real a `api.open-meteo.com` sigue recibiendo `CONNECT 403` en este entorno. Por ello, las descargas de proveedores no están verificadas en vivo. No se cambiaron las reglas de red ni la configuración publicada. Antes de habilitar uso real hay que permitir los dominios necesarios, comprobar respuestas y revisar cuotas, atribución y términos de uso.

## Radar, avisos y observaciones compartidos (0.6.0)

Las plantillas de ambas zonas seleccionan ahora `radar`, `warnings` y `observations`. No hacen falta claves para estos adaptadores públicos; disponibilidad, cuota, cobertura y condiciones dependen del proveedor. Las peticiones idénticas se reutilizan dentro de cada descarga, incluidos metadatos y teselas de radar.

- `radar`: hasta tres imágenes recientes de RainViewer, teselas de 256 px a zoom 7 alrededor de cada punto. Se guardan imagen, hash, fecha y posición del punto para verlas sin red. Se rechazan imágenes de más de dos horas; se marcan antiguas desde 20 minutos. Cobertura no verificada, sin conversión a lluvia local ni aviso. No es una animación continua; una imagen transparente no demuestra tiempo seco. Atribución: [RainViewer](https://www.rainviewer.com/), revisar sus condiciones antes de redistribuir o ampliar uso.
- `warnings`: boletines Atom oficiales distribuidos por [Meteoalarm](https://meteoalarm.org/), filtrados por nombres de áreas configurados, inicio y vencimiento. Se muestra frescura del boletín y países fallidos. No hay resolución geográfica por polígonos ni garantía de exhaustividad. Un boletín sin coincidencias no acredita ausencia de avisos. Conservar atribución a Meteoalarm y al organismo emisor y revisar condiciones nacionales.
- `observations`: METAR de [Aviation Weather Center](https://aviationweather.gov/) de estaciones elegidas, hasta 100 km, últimas 24 horas, marcadas antiguas desde dos horas. Viento de nudos a km/h; campos ausentes permanecen nulos. La distancia y altitud pueden impedir representatividad local. No se usan automáticamente como verdad diaria para entrenar o verificar nieve/lluvia.

Los datos de previsión/elevación/ensemble/mar proceden de [Open-Meteo](https://open-meteo.com/), con atribución CC BY 4.0 y condiciones de uso de la API. Los ZIP contienen respuestas normalizadas para los tres adaptadores nuevos; las respuestas de modelo conservan su estructura y unidades.

En un perfil personalizado, además de añadir los módulos deseados, configura por ejemplo:

```json
"sources": {
  "metar": ["LESU", "LFMP"],
  "warning_feeds": [
    {"country": "spain", "areas": ["pirineo de girona", "pirineo de lleida"]},
    {"country": "france", "areas": ["pyrénées-orientales", "ariège"]},
    {"country": "andorra", "areas": ["andorra"]}
  ]
}
```

Revisar los nombres reales de las áreas del proveedor para cada territorio. Los informes muestran el alcance configurado y los fallos. Las estaciones de la plantilla son referencias cercanas, no instrumentación de cada ladera. `plan` enumera las peticiones iniciales; el radar añade teselas a partir de metadatos y avisos consulta todos los países configurados.

## Forense: del archivo a la evaluación

1. Descargar y archivar paquetes **antes** del episodio. Conservarlos con `zone install`; el hash identifica el contenido, pero no certifica fecha ni autoría frente a manipulación.
2. Revisar independientemente las medidas y preparar un JSON de observaciones como el ejemplo inferior. La declaración `VERIFIED` es responsabilidad del revisor; las pistas comunitarias de `episode_evidence` siguen sin verificar y no entran automáticamente en este flujo.
3. Ejecutar la evaluación y revisar pares, exclusiones, soporte, distancias, tiempos y fuentes. Se elige la última captura elegible anterior al día; una captura posterior o con un módulo recogido después del inicio queda excluida. No se escoge retrospectivamente el pronóstico que mejor coincide.
4. Conservar JSON, HTML, medidas originales y paquetes. El informe del paquete permite revisar radar, avisos y observaciones disponibles en la captura. Este replay es una reconstrucción de evidencia archivada, no una simulación física ni recuperación de datos que no se archivaron.

```bash
python3 MeteoPortinatx.pyz zone forensic \
  --forecasts archivo-antes-1.zip archivo-antes-2.zip \
  --observations medidas-revisadas.json \
  --output evaluacion.json --html evaluacion.html --max-distance-km 1
```

Ejemplo **ficticio** de formato, no una observación real:

```json
[
  {
    "event": "episodio_ejemplo", "point": "masella",
    "variable": "precipitation", "value": 20, "unit": "mm", "aggregation": "sum",
    "start": "2026-11-11T00:00:00Z", "end": "2026-11-12T00:00:00Z",
    "observed_at": "2026-11-12T01:00:00Z",
    "latitude": 42.35, "longitude": 1.9,
    "source_url": "https://example.org/medida-revisada", "source_id": "instrumento_ejemplo",
    "review_status": "VERIFIED", "baseline": 30
  }
]
```

Se exige un día exacto UTC completo y medida posterior al cierre. Variables: `precipitation` mm/sum, `snowfall` cm/sum, `temperature_2m` °C/min, `wind_gusts_10m` km/h/max; solo en perfiles con mar, `wave_height` m/max, `wave_period` s/max y `wave_direction` °/circular_mean. Los valores ausentes o con unidades no verificadas no puntúan. Coordenadas dentro de 1 km por defecto (configurable hasta 20); esto no verifica altitud, exposición ni calidad instrumental. El indicador `collection_lead_hours` se refiere a la captura, no a una inicialización de modelo autenticada.

Resultados: sesgo, MAE, RMSE, diferencia de MAE con la referencia opcional `baseline` sobre pares comunes, Brier para lluvia ≥10 mm y nieve ≥5 cm cuando hay ensembles válidos. Los errores de dirección son circulares. Cada episodio pesa igual, con número de pares y episodios visible; el usuario debe verificar independencia de las etiquetas. Duplicados idénticos se deduplican y contradictorios se rechazan. Sin intervalos de confianza, calibración aprendida ni prueba de generalización: esos pasos requieren más episodios independientes y una separación temporal de ajuste/prueba.

Los archivos forenses **no se publican automáticamente**. Pages solo recoge perfiles predefinidos y datos públicos obtenidos durante su ejecución. No importa el estado local ni observaciones privadas.

## Publicación y red

El workflow de Pages construye el programa, valida ambos dominios, recoge módulos regionales y publica `/zones/portinatx/`, `/zones/pirineo/` y `/downloads/`. Exige al menos un día de temperatura completo por punto. Los fallos complementarios no bloquean la previsión: quedan visibles como no disponibles. Una nueva ejecución falla antes de subir el sitio si falta previsión básica; la versión desplegada anterior permanece. La programación es cada seis horas: radar, METAR y avisos pueden envejecer mucho antes de la próxima actualización. Consultar las fuentes originales para situación actual.

Dominios adicionales necesarios para verificar desde un entorno restringido: `api.open-meteo.com`, `ensemble-api.open-meteo.com`, `marine-api.open-meteo.com`, `api.rainviewer.com`, `tilecache.rainviewer.com`, `feeds.meteoalarm.org`, `aviationweather.gov`. La comprobación de despliegues requiere `api.github.com`, `bionic0x.github.io` y, para Render, su dominio de servicio y la API pertinente. No se modificó la configuración publicada del entorno.


## Compatibilidad con las incorporaciones de main

Se conserva `nowcast.py evidence PERFIL evidencias.json --as-of FECHA`: normaliza metadatos offline `schema:1, items:[]` con clases radar/warning/station/forensic. La presencia espacial y temporal queda como `PRESENT_UNVERIFIED`; no autentica la fuente ni autoriza avisos. Las estaciones y evidencias forenses exigen las declaraciones `qc=PASS` y `source_type=instrument`; el contrato mantiene separación respecto a los adaptadores públicos y medidas revisadas del evaluador.

El paquete portable también incluye el [Forecast Ledger P0](FORECAST-LEDGER-P0.md), accesible como `python3 MeteoPortinatx.pyz ledger --root /ruta/privada ...`. Conserva su captura prospectiva, importaciones externas no certificadas, integridad, pareo y métricas por umbral. Su esquema requiere emisión, inicialización del proveedor, procedencia y licencia explícitas: no se rellenan esos campos inventando datos desde un ZIP. `zone forensic` ofrece evaluación diaria y contexto archivado de zonas personalizadas; el ledger ofrece registro prospectivo con su contrato P0. No se cruzan ni convierten automáticamente entre sí. Ambos evitan entrenamiento o cambio de avisos a partir de evidencias comunitarias no verificadas.

Las vistas `/decidir/` y sus cinco perfiles de uso se conservan. Las descargas e informes regionales amplían la web sin sustituir sus fuentes ni reglas.
