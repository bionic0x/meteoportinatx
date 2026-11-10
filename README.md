# Pirineo Nowcast 0.3.0 · Meta-ensamble y forense

**Fecha de entrega:** 10 de noviembre de 2026. **Base:** Pirineo Nowcast 0.2.0 y MeteoPortinatx Nowcast 0.6.1 (código fuente recuperado del proyecto). **Estado:** compilado y probado con datos sintéticos, no desplegado en el sitio preexistente. Las llamadas de modelos reales deberán ejecutarse en un entorno con acceso a Internet.

## Qué aporta esta actualización

- Mantiene el motor original de **0–72 h**: relieve Terrarium/DEM, altitud real en los puntos de control, perfiles atmosféricos, isocero y cero de bulbo húmedo, cotas de copo/cuajado/acumulación, Kuchera, Froude, föhn, inversión y avisos oficiales.
- Añade **`src/pirineo_meta.py`**, horizonte de **15 días** en 6 estaciones y dos cotas por estación: Masella, La Molina, Font-Romeu, Les Angles, Formiguères y Porté-Puymorens.
- Interroga **ECMWF ENS, NCEP GEFS e ICON-EPS** con miembros reales. Informa fracciones de miembros con ≥5 cm y ≥10 cm de nieve nueva y condiciones de bulbo húmedo, sin denominarlas probabilidades calibradas.
- Contrasta por separado las salidas **ECMWF IFS, GFS, ICON-EU, AROME HD y ECMWF AIFS**. Las predicciones deterministas no cuentan como miembros independientes ni sustituyen la incertidumbre del ensemble. Los modelos de corto alcance pueden no cubrir los 15 días.
- Pondera inicialmente **cada familia operativa por igual**, nunca cada miembro por igual entre instituciones. Solo modifica ponderaciones si existe un replay con **al menos 30 fechas verificadas por familia**.
- Conserva las previsiones emitidas en archivos `META-<UTC>-<sha>.json` inmutables y compara exclusivamente las mismas fechas válidas entre ciclos. Detecta señales contrarian solo tras **revisión coincidente en dos familias independientes**; la señal es de vigilancia, no de alerta oficial.
- Integra ENSO, NAO, AO, estratosfera y SST del Atlántico únicamente como **contexto verificable y fechado**. No aumenta los porcentajes de nieve por analogías históricas.
- Añade a la interfaz una pestaña **«15 días · metaanálisis»**, con estado de cada fuente, acceso por estación/cota y advertencia sobre incertidumbre.

## Ejecutar

Desde la raíz del proyecto, con Python 3.10 o superior:

```bash
python3 src/pirineo_meta.py selftest
python3 src/pirineo.py selftest
python3 src/portinatx_degen.py selftest

# Necesita Internet; conserva el estado entre ejecuciones.
export PORTINATX_HOME="$PWD/estado-portinatx"
export PIRINEO_HOME="$PWD/estado-pirineo"
python3 src/pirineo.py export

# Prepara una copia navegable. La publicación en el hosting requiere una acción adicional.
python3 scripts/build_site.py
python3 -m http.server 8789 --directory site
```

`estado-pirineo/app/{core,dem,grid,series,extended}.json` queda listo para ser servido como `site/api/*.json`. Se reevalúan los modelos extendidos cada 3 h y se admite caché de respaldo hasta 6 h, marcada. Si el proveedor no responde, la salida indica `UNKNOWN` en lugar de fabricar predicciones.

`PIRINEO_EXTENDED=0` permite desactivar la nueva capa sin tocar el motor original. El `src/pirineo_meta.py` también admite `export --home <directorio>`, que genera exclusivamente `app/extended.json` sin construir el DEM ni la salida del resto del motor.

## Inyectar teleconexiones verificadas

De forma opcional, crear `estado-pirineo/teleconnections.json` con objetos `{ "source": "fuente verificable", "valid_at": "2026-11-10", "value":  ... }` para las claves `enso_nino34`, `nao`, `ao`, `stratospheric_10hpa` y `north_atlantic_sst`. El motor clasifica entradas desconocidas, anticuadas o posteriores al ciclo; en todos los casos `used_in_local_probability=false`. **No hay un proveedor automático de estos índices en esta entrega.**

## Datos históricos para calibración

El motor acepta `estado-pirineo/replay/cases.jsonl`. Una línea es una previsión emitida en fecha `issued_at` y un evento observado en `valid_at`, con `observed_at`, `family`, `fraction` (0–1) y `observation` (0 o 1). Se rechazan plazos fuera de 24–360 h, predicciones posteriores al tiempo válido y observaciones no publicadas al ejecutar la calibración. La puntuación es Brier por **fecha válida**, para evitar dar demasiado peso a días con muchos registros.

La calibración por resultados históricos **no está activada sin datos de verificación reales**. Nunca se usan tres inviernos El Niño como estimador numérico de probabilidades locales. Para ensayos históricos exhaustivos, utilizar los modelos previos de Open-Meteo `Previous Runs` (hasta 7 días) y `Single Runs` (corridas completas archivadas), más observaciones o ERA5 claramente rotulada como referencia reanalizada. No mezclar reanálisis y observación instrumental como si fueran equivalentes.

## Limitaciones que se muestran en la aplicación

1. Los 15 días **no** disponen aquí de cotas derivadas de perfiles verticales independientes por miembro: la cota fiable del perfil sigue siendo la del motor 0–72 h. El índice de bulbo húmedo extendido es **puntual**, referido a una altitud, y no es una cota nivológica.
2. Los centímetros modelizados son **nieve nueva**, no espesor conservado ni número de kilómetros abiertos.
3. La operación de cañones necesita bulbo húmedo, duración y datos de infraestructura; el algoritmo no predice apertura de remontes.
4. Las coordenadas son referencias por estación, y las elevaciones base/cima son aproximadas. La resolución real de GFS/ENS no captura todas las inversiones, sombra orográfica o transporte por viento.
5. Los tiempos de captura no se atribuyen falsamente a la hora de inicialización del modelo: `model_run_init=UNVERIFIED` hasta que un proveedor exponga el metadato.
6. No se ha validado la accesibilidad online de los endpoints durante la construcción de esta release; las pruebas realizadas son locales, sobre fixtures sintéticos.
7. No se han modificado ni rebajado los avisos oficiales (AEMET, SMA, Meteocat, Météo-France) ni sus jerarquías de seguridad.

## Estructura

- `src/portinatx_degen.py`: motor original MeteoPortinatx (reconstruido del archivo de proyecto, lógica conservada).
- `src/pirineo.py`: motor de montaña v0.3.0 con nueva salida `extended`.
- `src/pirineo_meta.py`: fusión, captura, escenarios, teleconexiones y replay.
- `src/pirineo_app.html`: web con la nueva pestaña.
- `scripts/build_site.py`: copia HTML y JSON para hosting estático.
- `tests/`: pruebas de integración y motor extendido.
- `docs/RELEASE-NOTES.md`: alcance, evidencias de pruebas y criterios para publicar.

## Publicación

Esta carpeta es un **candidato de release**. Para cambiar el sitio existente hace falta una conexión de escritura con el hosting o repositorio que lo alimenta; disponer de una URL de lectura no permite desplegar. El paquete no ejecuta cambios remotos por su cuenta.