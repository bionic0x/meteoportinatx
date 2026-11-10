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

# Consultar exactamente qué peticiones se realizarán.
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
| Radar, satélite, observaciones y avisos oficiales | Adaptadores configurables por país/región, cobertura y autorización del proveedor |
| DEM regional, perfiles verticales y diagnóstico de relieve | Descarga regional acotada, caché, procedencia y parametrización de puntos, transectos y exposiciones |
| Forense, replay y calibración | Registro y evaluación por zona, variable y episodio, conservando separación de ajuste y test |
| Metaanálisis extendido y diagnóstico marino | Eliminar estaciones/boyas/ventanas fijas; conservar soporte por variable y verificación temporal/espacial |
| Interfaz común y selector de descargas | Informe HTML común implementado; pendiente integrar descargas y observatorios heredados en una aplicación interactiva |
| Instalación/importación de packs | Verificación, archivo por zona, historial e informe implementados; pendiente caché incremental de proveedores y gestión multiusuario |

Esta matriz sustituye la prioridad anterior de tratar Pirineo únicamente como expansión posterior: las capacidades compartidas deben desarrollarse y probarse sobre ambas zonas.

## Correcciones asociadas

Se corrigió cobertura diaria de nieve y soporte por métrica en el metaanálisis, y cobertura de ventanas 24/72 h en montaña. En la web, el contador junto a nieve se refiere ahora a familias que aportan esa métrica.

El backend identifica el paquete público completo mediante un manifiesto; publicar contenido distinto con el mismo `issued` provoca un error explícito. Para una corrección debe emitirse un nuevo ciclo. Los punteros antiguos con hash de core siguen siendo legibles; su republicación requiere una nueva emisión. El nuevo `sha256` de publicación representa el manifiesto completo, no exclusivamente `core.json`.

Un fallo al escribir CURRENT deja el índice registrado y el puntero anterior; reintentar exactamente el mismo ciclo repara el puntero sin duplicar la cadena. El servicio mantiene el modelo existente de un único publicador por directorio de datos. No se ha añadido coordinación de múltiples procesos ni recuperación automática de CURRENT al arrancar.

## Verificación y límites actuales

Se verifican ambos perfiles, exclusión del mar en Pirineo, perfiles personalizados, hashes, instalación, histórico, comparación y fallos de proveedor con pruebas offline. Chromium comprueba el backend entre orígenes y el informe común en móvil, incluidos filtro de puntos y valores ausentes. En este navegador gestionado se sirve el HTML por HTTP local porque la política bloquea `file://`; la vista no necesita servicios ni recursos externos.

La consulta real a `api.open-meteo.com` sigue recibiendo `CONNECT 403` en este entorno. Por ello, las descargas de proveedores no están verificadas en vivo. No se cambiaron las reglas de red ni la configuración publicada. Antes de habilitar uso real hay que permitir los dominios necesarios, comprobar respuestas y revisar cuotas, atribución y términos de uso.
