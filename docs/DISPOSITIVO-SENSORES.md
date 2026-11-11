# Sensores y háptica del teléfono — experimental

La vista `/dispositivo/` usa el mismo `core.json` que las consolas y solo funciona con la página abierta y visible. No es un servicio de avisos, ni cambia umbrales, modelos o fuentes. Sin probar en teléfonos reales; la compatibilidad y permisos dependen del dispositivo y navegador. Se requiere HTTPS o localhost para sensores que lo exijan.

La vibración se activa mediante un botón. Una vez fijada una línea base, señala una subida de nivel o la pérdida de un diagnóstico anterior (esta última, como máximo una vez por minuto). Al cambiar de dominio, ocultar la página o volver a mostrarla se reinicia la línea base. La ausencia de vibración no significa ausencia de peligro; consulta los avisos oficiales.

La página comprueba la edad del ciclo (60 minutos en Portinatx, 360 en Pirineo) y muestra `Sin diagnóstico` cuando es antiguo, inválido o falta. El ciclo puede contener mediciones más antiguas. En Portinatx se usa el máximo disponible de aviso oficial verificado, canales observados públicos y precaución si su cobertura no es insuficiente; en Pirineo, el estado de avisos vigentes si la fuente está disponible. El resumen no es un aviso oficial ni garantiza que todas las fuentes estén disponibles.

## Lecturas

| Canal | Origen | Caducidad |
|---|---|---|
| Presión, temperatura, humedad | Puente nativo externo | 5 minutos |
| Luz, campo magnético, movimiento, rumbo | APIs del navegador, si están disponibles y autorizadas | 15 segundos |
| Altitud | Geolocalización, activación independiente | 2 minutos |

La página no incluye aplicación nativa. Un envoltorio externo podría entregar una lectura mediante `MeteoDeviceBridge.push('presion', 1013.2, Date.now())`; recibe `{ok, reason}`. Los valores se validan y se mantienen en memoria de la página. No se generan peticiones de red con las lecturas de sensores; la página sí solicita los datos meteorológicos. La solicitud de geolocalización se hace solo al activarla y el código conserva únicamente la altitud, no las coordenadas. El navegador o el proveedor de geolocalización pueden tratar datos según sus propias políticas.

Una lectura inexistente es `UNKNOWN`; una lectura que caduca se muestra `STALE` y sin valor. Se rechazan lecturas no numéricas, fuera de rango, antiguas, futuras o desordenadas; la memoria de las series es acotada. La tendencia de presión requiere al menos seis lecturas, 30 minutos, huecos de hasta 20 minutos y un dato reciente. Si detecta más de 25 m de variación de altitud, indica `NO_COMPARABLE`; sin altitud suficiente la estabilidad vertical es `UNKNOWN`. Es una orientación sobre presión no calibrada y no altera avisos ni niveles.

La vibración, los sensores, la brújula y Wake Lock pueden no estar disponibles; se debe verificar en Android e iOS reales antes de declarar compatibilidad. Al detener los sensores, las lecturas conservadas caducan normalmente.

## Comprobación

`node tests/test_device_sensors.cjs` verifica los contratos puros de validación, caducidad, tendencia y háptica con datos sintéticos. Las pruebas de integración comprueban las rutas locales y la salida estática. No equivalen a una prueba física de sensores ni a garantizar que el teléfono avise durante un episodio.
