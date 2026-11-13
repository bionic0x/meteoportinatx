# Paridad de algoritmos: alcance y evidencia

**Idioma / Language:** Español · [English](PARIDAD-ALGORITMOS.en.md)

Revisión Agency Agents del 13 de noviembre de 2026 sobre la base `9ba40bf`.
División de Ingeniería: perfiles Backend Architect y Frontend Developer de Ante/Agency Agents. Backend, Geoespacial y Calidad iniciaron la revisión paralela; alcanzaron el límite de uso de la cuenta tras entregar diagnóstico, núcleo inicial y pruebas. El coordinador completó adaptadores, integración, revisión y verificación; no se declara una revisión independiente final terminada por esos agentes.
Referencias: perfiles de `.codex/agents/` y [contrato de coordinación](agency-agents.md).

La paridad exige ejecutar el mismo algoritmo sobre entradas equivalentes y conservar sus
condiciones de validez. Dos pestañas con el mismo nombre, o dos conectores que responden,
no demuestran paridad física. Un adaptador regional puede aportar datos diferentes sin
que cambie el algoritmo; un dato ausente debe seguir siendo desconocido.

## Matriz de capacidades

| Capacidad | Portinatx | Pirineo | Perfiles de zona | Estado de la paridad |
|---|---|---|---|---|
| Acumulados diarios y soporte ensemble por familia | Motor territorial y paquetes | Motor territorial y paquetes | `weather_core` y `zone_engine` comunes | Compartido en paquetes; modelos, horizontes y resúmenes territoriales aún distintos |
| Perfil atmosférico puntual: termodinámica, inestabilidad, viento y cizalladura | `portinatx_degen.derive_profile` | `pirineo_atmos.derive` | Módulo atmosférico de esta entrega | Compartido: `atmospheric_core.derive` utilizado por ambos adaptadores y el módulo `atmosphere`; paridad de lógica probada con entradas sintéticas |
| Gradientes espaciales de viento | Stencil del modelo alrededor de Portinatx | Sin stencil equivalente en la adquisición actual | Sin malla vecina en un perfil puntual | Pendiente adquisición regional; no inventar divergencia o vorticidad con un solo punto |
| Radar: imágenes, edad y punto de referencia | Conector territorial y paquete | Paquete y visores externos en consola | `zone_sources.radar` | Adquisición común de imágenes; no paridad de diagnóstico de ecos |
| Radar: movimiento, ETA y autoverificación de ventana | `radar_motion` conectado al canal costero | Sin conexión equivalente en el motor territorial | PNG archivados; sin rejilla dBZ equivalente | Pendiente. Requiere mosaico, paleta validada, cobertura y conversión trazable |
| Avisos y observaciones | Redes y reglas locales | Redes y reglas locales | METAR/Meteoalarm configurables | Contrato compartido de paquetes; instrumentación y cobertura no equivalentes |
| DEM regional y exposición | Relieve costero y batimetría separada | Terrarium, cotas y transectos pirenaicos | Elevación puntual | Pendiente parametrizar extensión, resolución, datum/nodata y descarga regional |
| Nieve, capa cálida y engelamiento | Sin diagnóstico territorial equivalente | `profile_diag`, `warm_layer`, `point_snow_levels` | Sin estos diagnósticos en el paquete | Pendiente extracción; cotas heurísticas no equivalen a manto observado ni riesgo de aludes |
| Inversión observada y föhn | Sin pares regionales equivalentes | `obs_inversion`, `foehn_diag` | Sin configuración de pares/vertientes | Pendiente. Exige relieve, estaciones comparables y alineación temporal |
| Frente de racha y respuesta hidrológica | `gust_front`, `ch_runoff`, `irh_now` | Sin diagnóstico equivalente | Sin configuración de cuencas | Pendiente; no transferir los umbrales de la cala a cuencas de montaña |
| Metaanálisis extendido y revisión entre ciclos | Modelos ampliados y superensemble locales | Metaanálisis a 15 días, revisiones por familia | Ensemble común a 7 días solicitados | Paridad parcial; geometría, soporte y horizontes deben parametrizarse |
| Evaluación forense diaria y archivo de paquetes | Disponible | Disponible | `zone_forensics`, `zone_packages` | Compartido; pruebas sintéticas no acreditan calibración ni durabilidad remota |
| Desplazamiento, desfase y aprendizaje por regímenes | Diagnósticos forenses territoriales | Revisiones entre salidas | Sin equivalente completo | Pendiente separar evaluación observada, cambio entre pronósticos y ajuste aprendido |
| Mar, oleaje, corrientes y batimetría | Especialización costera | Excluido | Solo perfiles costeros/mixtos | Exclusión deliberada del Pirineo, no una carencia de paridad |

Referencias de implementación: `src/portinatx_degen.py`, `src/pirineo.py`,
`src/pirineo_meta.py`, `src/pirineo_atmos.py`, `src/weather_core.py`,
`src/radar_motion.py`, `src/zone_engine.py`, `src/zone_sources.py` y `src/zone_forensics.py`.

## Contraejemplo que motiva el bloque atmosférico

Antes de la unificación, calidad ejecutó ambos diagnósticos sobre el mismo perfil sintético:
terreno a 1600 m, presión superficial de 850 hPa y velocidad vertical de −0,2 Pa/s.
La fuente se deriva de `MountainAtmosphere.source()` en `tests/test_pirineo_atmos.py`.

| Magnitud | Implementación costera anterior | Implementación pirenaica anterior |
|---|---|---|
| Temperatura a 850 hPa, nivel a 1500 m | 5 °C, aunque está bajo terreno | Desconocida |
| Índice K | 23,9 | Desconocido por nivel enterrado |
| Velocidad vertical a 700 hPa | +0,2 tras invertir el signo de Pa/s | Desconocida; falta magnitud geométrica verificable |
| Bulbo húmedo superficial | 3,7 °C usando presión reducida/default | 3,55 °C usando presión superficial |
| Altura de cizalladura a 700 hPa | 3,0 km sobre nivel del mar | 1,4 km sobre terreno |

Estos resultados son una reproducción sintética del desacuerdo, no observaciones
meteorológicas. Reutilizar el algoritmo costero sin corregir sus supuestos no resolvería
la paridad: propagaría extrapolaciones subterráneas y unidades incompatibles.

## Criterios verificables para el núcleo atmosférico

1. **Equivalencia:** el núcleo y los dos adaptadores territoriales devuelven los mismos
   niveles e índices comunes para una entrada equivalente, tanto a nivel del mar como
   en altura. Las etiquetas de ubicación pueden diferir; los valores físicos no.
2. **Terreno:** solo son utilizables niveles sobre el terreno del modelo y con presión
   inferior a la superficial. Terreno o presión desconocidos no autorizan extrapolar.
3. **Unidades:** las conversiones documentadas conservan el resultado; unidades ausentes
   o incompatibles no producen índices. Pa/s no se convierte a m/s invirtiendo el signo.
4. **Altura:** cizalladura referida al terreno, con su altura real visible. Un nivel de
   500 hPa no es automáticamente una capa exacta de 0–6 km sobre cualquier relieve.
5. **Cobertura:** ninguna entrada ausente, no finita o inválida se convierte en cero.
   Índices compuestos exigen todas sus componentes; faltas o signo vertical no verificado
   dejan el compuesto desconocido.
6. **Geografía:** el cálculo puntual no depende de `SITE` ni de una latitud global. Los
   gradientes espaciales solo se calculan con una geometría explícita y vecinos válidos.
7. **Distribución:** el módulo puede seleccionarse en ambas plantillas y en una zona
   personalizada, viajar en ZIP verificado y mostrarse en un informe offline. El perfil
   interior sigue rechazando `marine`.
8. **Compatibilidad:** los contratos públicos conservan sus campos; pruebas de ausencia
   de datos y consumidores existentes siguen pasando. Las nuevas guardas pueden reducir
   valores antes mostrados sin soporte: ese cambio debe documentarse, no ocultarse.

La verificación de esta entrega se limita al bloque atmosférico y sus adaptadores. La
matriz superior no debe marcarse completa por haber unificado ese bloque. Tampoco una
CI correcta valida fuentes reales, semántica vertical del proveedor, calibración local,
alertas oficiales, archivo remoto duradero o disponibilidad continua.

## Orden recomendado de los siguientes bloques

- Rejilla y cobertura de radar compartidas antes de conectar movimiento/ETA al Pirineo.
- Geometría regional descargable y pares de estaciones antes de generalizar föhn,
  inversión, cotas de nieve y diagnósticos de cuencas.
- Horizontes y revisiones ensemble comunes, con soporte por variable y familia.
- Evaluación prospectiva por episodio antes de compartir correcciones aprendidas.

Cada bloque debe incluir entrada, salida, cobertura, unidades, geografía y pruebas
contrarias explícitas. El mar permanece como especialización costera.


## Entrega y comprobaciones

- Un único núcleo puro sin `SITE`, red ni importación del motor costero. Los adaptadores conservan los campos consumidos por las consolas.
- El conector costero conserva elevación, presión superficial y metadatos de cada vecino; los gradientes usan separación de celdas devueltas, con geometría y tiempo compatibles. Sin vecinos verificables quedan desconocidos.
- La altura de obstáculo para Froude debe conocerse sobre el terreno modelizado: se elimina el valor costero implícito de 400 m.
- `atmosphere` se selecciona en ambas plantillas y puede descargarse solo en un perfil nuevo. Consulta 3 días, viento en m/s y presión superficial. Conserva datos, diagnóstico y hash; al leer se recalcula usando el núcleo.
- Las entradas de unidades ausentes/incompatibles ya no habilitan índices. El laboratorio HTML conserva ese bloqueo, incluido el signo vertical y todas las componentes de los índices sintéticos.
- Pruebas: `tests/test_atmospheric_core.py`, `tests/test_pirineo_atmos.py`, `tests/test_zone_atmosphere.py`, `tests/test_atmospheric_ui.py` y suite de integración. La prueba de laboratorio usa Chromium real; las mediciones y perfiles de prueba son sintéticos.

Las fuentes remotas y las consolas desplegadas requieren comprobación por separado. La paridad de este bloque no completa radar advectivo, nieve, föhn, cuencas, metaanálisis ni calibración; permanecen en la matriz con sus requisitos.
