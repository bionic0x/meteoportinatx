# P0 — Forecast Ledger / archivo de verificación prospectiva

**Idioma / Language:** Español · [English](FORECAST-LEDGER-P0.en.md)

**Estado:** prototipo local aislado (no desplegado, no integrado en alertas). Implementación de la prioridad [#7](https://github.com/bionic0x/meteoportinatx/issues/7), a partir de [investigación Agency Agents #6](https://github.com/bionic0x/meteoportinatx/pull/6). **No implica que MeteoPortinatx tenga habilidad predictiva demostrada.**

## 1. Propósito y alcance

Congelar un pronóstico **antes** de que comience su ventana de validez, guardar después la observación, y documentar exactamente qué parejas se pueden comparar. Se evita la ilusión de un backtest generado con datos posteriores. **No se modifica** la regla institucional, el motor de alerta, los datos públicos ni los conectores CNP.

`src/forecast_ledger.py` es Python 3.10+ sin paquetes externos, ni acceso a Internet. Opera sobre un directorio **privado gestionado por el usuario**; no usar Render Free para archivado. Los registros se crean por escritura temporal `fsync` y hard link atómico que nunca sustituye un registro anterior. Su identificador deriva de una clave canónica (modelo, sitio, emisión y ventana). Si la misma identidad intenta ingresar una predicción cambiada, se **rechaza**. No es un reloj seguro ni un sistema de notarización: quien controla el disco puede borrar o reemplazar toda la evidencia.

## 2. Esquema de datos y límites

**Pronóstico:** `event_id`, `domain` (`portinatx`/`pirineo`), `site_id`, lat/lon, `issued_at`, `provider_run_at`, `valid_from`, `valid_to`, `provider`, `model`, `family`, `variable`, `unit`, `mode` (`amount` o `threshold`), `prediction`, `source_id`, `source_license`. Opcionales: `threshold`, `probability_raw` (solo umbrales), `baseline`, y hashes SHA-256 de configuración, datos o commit.

La hora real de captura local es `captured_at`. **PROSPECTIVE** exige `issued_at` anterior a la validez y `captured_at < valid_from`. Cualquier carga después se etiqueta **HINDCAST**, incluso si el archivo afirma que el pronóstico fue emitido antes. No existe una opción para forzar `PROSPECTIVE`.

**Observación:** ventana `observed_from`, `observed_to`, identificación de estación, coordenadas, valor en unidad canónica, `source_type` (`instrument` o `community`), `qc` (`INSTRUMENT_QC_PASS`, `UNKNOWN`, `REJECTED`), fuente y licencia. El valor es una declaración del importador, **no una validación externa**. Un reporte `community` no puede declararse `INSTRUMENT_QC_PASS`. No se admiten campos imprevistos, nombres personales, comentarios ni enlaces con credenciales. Conservamos solo identificadores técnicos.

Variables iniciales: precipitación (`mm`), nieve (`cm`), temperatura (`C`), racha (`m/s`) y altura significativa de ola (`m`). **No se convierte nieve producida en natural**, no se mezclan periodos de acumulación y no se extrapola una estación remota a un punto cercano sin control geográfico.

## 3. Pareo conservador y scoring

Se exige simultáneamente: mismo episodio, dominio, sitio, variable y unidad; coincidencia **exacta** entre ventana de pronóstico y ventana observada; distancia geodésica no superior al radio declarado (`3 km` por defecto); una única observación instrumental marcada QC PASS. Si hay más de una medida QC PASS, el par se excluye como ambiguo hasta definir una regla explícita; nunca se elige arbitrariamente el máximo.

Otros motivos se informan: pronóstico HINDCAST/tardío, ventana futura, observación inexistente, observación fuera de radio o QC desconocido, ausencia de ventana idéntica y múltiples estaciones candidatas. **Ausencia ≠ 0.** Importaciones externas se reconstruyen, pero no se puntúan como prospectivas sin atestación externa.

- `amount`: `MAE`, sesgo con signo (`pronóstico - observado`), `n_pairs`, episodios independientes.
- `threshold`: matriz `TP/FP/FN/TN`, `CSI`, `POD`, `FAR`; `None` cuando un denominador no existe. Si hay probabilidad original, Brier explícitamente **raw/uncalibrated**, no `P(alerta)` calibrada.
- Comparativa: solo contra una predicción `baseline=true` emparejada con **la misma** observación y umbral. `mean_loss_reduction` es descriptivo, no inferencia ni victoria científica.
- Toda salida declara `verification_status=EXPLORATORY_UNCALIBRATED` y `meteorological_skill_verified=false`.

## 4. Ejecución local

```bash
# Directorio privado **fuera del repositorio**; no usar /tmp ni Render Free.
export METEO_LEDGER="$HOME/meteoportinatx-private/forecast-ledger"
python3 src/forecast_ledger.py --root "$METEO_LEDGER" add-forecast --json /ruta/forecast.json
# Cuando la ventana ya haya concluido y haya un instrumento con QC conocido:
python3 src/forecast_ledger.py --root "$METEO_LEDGER" add-observation --json /ruta/instrument-observation.json
python3 src/forecast_ledger.py --root "$METEO_LEDGER" verify
python3 src/forecast_ledger.py --root "$METEO_LEDGER" score --max-distance-km 3
python3 src/forecast_ledger.py --root "$METEO_LEDGER" export --out "$HOME/meteoportinatx-private/backup-20261111.json"

# En otra máquina: verifica el archivo pero **no eleva** automáticamente
# los pronósticos importados a pruebas de predicción prospectiva.
python3 src/forecast_ledger.py --root "$HOME/meteoportinatx-restore" import --bundle "$HOME/meteoportinatx-private/backup-20261111.json"
```

Los ficheros JSON deben contener exactamente los campos enumerados. Por ejemplo, un pronóstico de lluvia para una hora futura en UTC:

```json
{
  "event_id": "episode-20261111-demo", "domain": "portinatx", "site_id": "portinatx",
  "lat": 39.1136, "lon": 1.5180, "valid_from": "2026-11-12T11:00:00Z",
  "valid_to": "2026-11-12T12:00:00Z", "issued_at": "2026-11-11T08:00:00Z",
  "provider_run_at": "2026-11-11T06:00:00Z", "provider": "example",
  "model": "synthetic-v0", "family": "synthetic", "variable": "precipitation_mm",
  "unit": "mm", "mode": "amount", "prediction": 5.0, "source_id": "example-demo",
  "source_license": "SYNTHETIC", "baseline": false
}
```

Este ejemplo es **sintético**, no una predicción meteorológica real. Para conservar carácter prospectivo la captura debe ocurrir antes de `valid_from`, y el emisor/modelo ha de estar documentado. Los valores pueden fallar si se ejecuta fuera de la ventana ilustrativa.

## 5. Campaña prospectiva de 90 días

**Estado actual: la validación de 90 días NO está iniciada ni terminada, y no se dará por completada anticipadamente.** Su estado no se declara en ningún documento: lo calcula `campaign-status` a partir del diario y los registros. Lo que el código garantiza: `COMPLETADO` exige a la vez 90 días con ciclos que anotan registros nuevos (sin ids repetidos y capturados en su intervalo), 2160 h reales, cobertura por horas UTC, 20 observaciones QC PASS distintas emparejadas y anotadas en el diario, repartidas en al menos 10 días, y un recibo de restauración desde una copia en otro sistema de archivos. Lo que **no** garantiza: que los datos sean auténticos frente a quien controla el disco (no hay firma ni sello externo), que `INSTRUMENT_QC_PASS` sea un control real (lo declara el importador), ni que «otro sistema de archivos» sea otro disco físico (ver límites en §5.1–5.3). Además está **bloqueada por A1** (ver §5.6): con el cableado actual no sale ningún par puntuable.

### 5.1 Diario encadenado de ciclos

`<METEO_LEDGER>/journal/cycles.jsonl` es un diario de solo adición. `scripts/forensic_cycle.py` añade un asiento en **todos** los ciclos (`OK`, `NO_DATA`, `DEGRADED`, `ERROR`), así que los huecos y fallos dejan rastro aunque `cycle-health.json` se sobrescriba. Cada asiento lleva `seq`, `timestamp` (UTC, reloj del equipo), `state`, `added_ids`, `added_sha256` (mapa id → SHA-256 del archivo de cada registro añadido), `prev_hash` y `hash` (SHA-256 canónico del asiento sin `hash`; el primero enlaza con 64 ceros).

`verify` recalcula la cadena (secuencia, `prev_hash`, hash, forma canónica, tiempo no decreciente), exige que exista cada id citado y que su archivo conserve el SHA-256 anotado, y comprueba que cada recibo de restauración esté íntegro y anclado a un asiento existente. Devuelve en primer nivel `integridad`:

| `integridad` | Cuándo | Código de salida de `verify` |
|---|---|---|
| `VERIFICADA` | Diario íntegro y todos los asientos con hash de archivo. | 0 |
| `ROTA` | Motivo en `motivo`: `DIARIO_ID_AUSENTE`, `DIARIO_REGISTRO_ALTERADO` (valor editado), `DIARIO_ID_DUPLICADO` (id ya anotado en un asiento anterior), `DIARIO_ID_FUERA_DE_INTERVALO` (`captured_at` fuera del intervalo entre el asiento anterior y el suyo), `DIARIO_HASH_ALTERADO`, `DIARIO_SECUENCIA_ROTA`, `DIARIO_COLA_INCOMPLETA`, `DIARIO_RECIBO_HUERFANO`, `DIARIO_RECIBO_ALTERADO`… | 1 |
| `UNKNOWN` | Ledger antiguo sin diario (`SIN_DIARIO`, **no se migra**) o asientos del primer formato sin `added_sha256` (`parcial: ASIENTOS_SIN_HASH`): se comprueba la existencia, no el contenido. | 3 |

Un registro con formato inválido sigue saliendo con código 2, como antes. El campo `ok` se mantiene (`ok = integridad ≠ ROTA`). El selftest y el CI solo comprueban estos códigos en tests sintéticos (`tests/test_forecast_ledger.py`, `tests/test_ledger_campaign.py`); ningún paso del CI ni `forensic_cycle.py` depende del código de salida de `verify`.

**Cola incompleta (una línea a medias tras un corte).** `append_journal` no la borra ni la repara: no escribe y devuelve `DIARIO_COLA_INCOMPLETA`; el ciclo sigue capturando y queda `DEGRADED` con ese motivo en `cycle-health.json`, y la campaña pasa a `INVALIDO:DIARIO_COLA_INCOMPLETA`. Recuperación manual (decisión del titular): (1) copiar el root entero a un archivo de solo lectura como evidencia; (2) **no reescribir** el diario antiguo; (3) iniciar una campaña nueva con `METEO_LEDGER` apuntando a un directorio nuevo y vacío. El mismo procedimiento vale para cualquier `INVALIDO`.

**Límites que quedan:** quien controla el disco puede reescribir toda la cadena, los registros y los recibos de forma coherente (no hay firma ni sello externo). Un truncado del final del diario **sin** recibos posteriores no es detectable. La comprobación de intervalo usa el reloj del equipo: un reloj sin NTP puede producir falsos `DIARIO_ID_FUERA_DE_INTERVALO` o encubrir capturas tardías. Los registros añadidos fuera de `forensic_cycle.py` (p. ej. `nowcast.py export` directo) no figuran en el diario.

### 5.2 Estados y contadores (`campaign-status`)

```bash
python3 src/forecast_ledger.py --root "$METEO_LEDGER" campaign-status [--max-gap-hours 48] [--min-coverage 0.8] [--min-pair-days 10]
```

La función `ledger_campaign.campaign_status(ledger, *, max_gap_hours, min_coverage, min_pair_days)` **no acepta fecha de inicio ni de fin**. Un *ciclo con datos* es un asiento `OK` con `added_ids` no vacío; un *día con datos* es un día UTC con al menos uno. Un `OK` sin registros nuevos no cuenta.

**Ventana congelada.** La ventana empieza en el primer ciclo con datos y se congela en el *asiento de anclaje*: el primer ciclo con datos en que se cumplen a la vez 90 días con datos y al menos 90 × 24 h reales desde el inicio. Cobertura, pares y huecos se calculan sobre esa ventana. Lo posterior no cambia el estado: se informa en `vigilancia_posterior` (`HUECO_POSTERIOR` si hay un hueco mayor que el umbral).

| Estado | Condición |
|---|---|
| `SIN_INICIAR` | Diario ausente o vacío. |
| `EN_CURSO` (`día N/90`) | Cadena íntegra, sin hueco mayor que el umbral y ventana sin cerrar. |
| `INVALIDO:<motivo>` | Integridad `ROTA` (`DIARIO_…`), registro corrupto, asiento con `timestamp` posterior a ahora + 10 min (`TIMESTAMP_FUTURO`), hueco entre ciclos con datos mayor que el umbral dentro de la ventana (`HUECO_MAYOR_QUE_UMBRAL`) o, con la ventana abierta, tiempo desde el último ciclo con datos mayor que el umbral (`HUECO_ABIERTO_MAYOR_QUE_UMBRAL`). |
| `DATOS_COMPLETOS_COBERTURA_INSUFICIENTE` | Ventana cerrada con `horas_con_datos / ciclos_esperados` < umbral: horas UTC distintas con al menos un ciclo con datos frente a horas UTC de la ventana. Varios ciclos en la misma hora cuentan una vez. |
| `DATOS_COMPLETOS_PARES_INSUFICIENTES` | Ventana cerrada con menos de **20 observaciones QC PASS distintas** emparejadas (mínimo de D-021) o repartidas en menos de **N días UTC** (`--min-pair-days`, 10 por defecto). Solo cuentan pares cuyo pronóstico y observación figuran en el diario dentro de la ventana; la baseline no cuenta; 20 modelos contra una observación cuentan como 1. |
| `DATOS_COMPLETOS_RESTAURACION_NO_PROBADA` | Lo anterior se cumple, pero no hay recibo válido con `origen: copia_externa`, `mismo_dispositivo: false`, `n_observaciones_emparejadas ≥ 20` y anclado en el asiento de anclaje o después. Un recibo `copia_local` o en el mismo dispositivo nunca basta (motivo en `motivo_restauracion`). |
| `COMPLETADO` | Todo a la vez: 90 días con datos, ≥ 2160 h reales, cobertura horaria ≥ umbral, ≥ 20 observaciones emparejadas en ≥ N días, cadena íntegra y recibo válido desde una copia en otro dispositivo. |

**Umbrales, decisión del titular** (propuestos por la auditoría, no calibrados): hueco máximo 48 h; cobertura horaria mínima 0,8; observaciones emparejadas repartidas en al menos 10 días UTC. Los ciclos `ERROR`/`NO_DATA` no cierran un hueco. Los estados `DATOS_COMPLETOS_*` intermedios no pueden convertirse en `COMPLETADO` dentro de la misma campaña salvo el de restauración (basta con un recibo externo válido). El resumen textual solo dice «completado» si el estado es `COMPLETADO` y nunca dice «restauración probada».

Contadores: días con datos, horas reales de la ventana, ciclos esperados / registrados / `OK` / con datos, cobertura, ciclos por estado, huecos (> 1,5 h entre ciclos con datos) y hueco máximo, hueco abierto, fracción de observaciones `UNKNOWN` en la ventana, horas con datos, pares brutos, observaciones emparejadas (sin baseline) y días con pares en la ventana, y exclusiones por motivo (del archivo entero). **Límite:** los episodios se cuentan como días (`event_id` = día de la ventana); días consecutivos de un mismo temporal no son independientes.

### 5.3 Simulacro de restauración

```bash
# Solo comprueba que este disco se lee (origen: copia_local; nunca basta para COMPLETADO):
METEO_LEDGER="$HOME/meteoportinatx-private/forecast-ledger" python3 scripts/ledger_restore_drill.py
# Restaura DESDE una copia externa ya existente (otro disco, clon del repositorio privado):
METEO_LEDGER="$HOME/meteoportinatx-private/forecast-ledger" python3 scripts/ledger_restore_drill.py --source /media/respaldo/forecast-ledger
```

Toma el mismo bloqueo que el ciclo, copia `local/` y `journal/cycles.jsonl` del origen a un directorio limpio temporal y, con el mismo reloj, compara frente al ledger original `verify`, el diario, `score` (con sus exclusiones) y el SHA-256 del bundle. `--source` debe ser un directorio absoluto existente fuera del ledger; la copia debe estar sincronizada con el ledger, o el recibo sale `ok: false`. Emite un recibo con hash en `journal/restore-receipts/<sha256>.json` con `origen`, `journal_seq`, cabeza del diario, `n_pares` brutos y `n_observaciones_emparejadas` restaurados, y `mismo_dispositivo` (mismo `st_dev` que el ledger). `COMPLETADO` exige `mismo_dispositivo: false`, pero otro sistema de archivos no prueba otro disco físico (puede ser otra partición del mismo disco). **`import` no sirve para esto:** deja cada registro como `IMPORTED_UNATTESTED`, fuera de la puntuación. **Límite:** el recibo no está firmado ni sellado; quien controle el disco puede falsificarlo.

### 5.4 Métricas (tras la campaña)

- **Estratos:** dominio / sitio / variable / modelo / plazo (1–2, 3–4, 5–6 h) / mes / régimen; denominadores, fracción `UNKNOWN` y exclusiones por estrato.
- **Baselines:** persistencia de Hs (existe; desde este cambio no se congela si la última Hs tiene más de 120 min, D-021) y **climatología mensual de precipitación: aún no existe**.
- **Intervalos:** bootstrap por bloques de episodio, solo con ≥ 10 bloques; si no, `INSUFICIENTE`. No declarar mejora por pares sintéticos.
- **Deriva:** MAE y sesgo mensuales frente a la persistencia; cambios en la fracción `UNKNOWN` y en los rechazos; cambios de nombre de modelo; latencia `captured_at − issued_at`.

### 5.5 Activación: qué necesita el titular

Nada de esto lo puede hacer el código ni un agente:

1. **Repositorio privado** para la copia duradera del ledger. Se **descarta una rama huérfana en el repositorio público**: publicaría las mediciones (fuera de alcance, ver abajo) y abre dudas de licencia PORTUS.
2. **PAT de grano fino o deploy key de alcance mínimo** (solo escritura de contenidos en ese repositorio privado). **Nunca en el repositorio ni en prompts**; vigilar su caducidad.
3. **Protección de rama** en el repositorio privado (sin force-push ni borrado). Git no es WORM.
4. **Equipo Linux encendido** con el temporizador systemd instalado, `loginctl enable-linger <usuario>` (sin linger el servicio de usuario se detiene al cerrar sesión), reloj con NTP y **disco cifrado**.
5. **Umbrales de invalidez** (hueco máximo, 48 h por defecto; cobertura horaria mínima, 0,8 por defecto; días mínimos con pares, 10 por defecto) y **criterio QC de PORTUS** (gate QC 1 de D-021).
6. **Copia externa en otro disco** sincronizada del ledger y un simulacro con `--source` sobre ella al cerrar la ventana.

### 5.6 Bloqueante A1: 0 pares puntuables con el cableado actual

En Portinatx la precipitación no tiene pluviómetro a ≤ 3 km y la Hs de PORTUS entra como `UNKNOWN`; en Pirineo hay observaciones Météo-France con `INSTRUMENT_QC_PASS` pero ningún pronóstico congelado en esas coordenadas. Resultado: **0 pares puntuables**. Arrancar los 90 días así acabaría como mucho en `DATOS_COMPLETOS_PARES_INSUFICIENTES`. Propuesta (cambio aparte, **no implementado aquí**): congelar pronósticos en las coordenadas de las estaciones Météo-France del Pirineo con QC PASS; para PORTUS, que el titular cierre el criterio QC (qué banderas o controles convierten una Hs en `INSTRUMENT_QC_PASS`).

**Fuera de alcance deliberadamente:** scraping de ClimayNievePirineos/foros sin permiso, entrenamiento automático de pesos, pronósticos oficiales, publicación pública del archivo de mediciones, ingesta de usuarios y ejecución de alertas. En caso de conflicto entre una descripción del modelo y una medición no comparable, salida `UNKNOWN/NO_COMPARABLE`.

## 6. Reality Checker — evaluación de esta entrega

- **Software:** pruebas de estado, temporalidad, paridad espacial/temporal, privacidad de esquema, fallos de integridad, export/import y baseline; matriz CI por verificar en esta PR.
- **Persistencia real:** **NEEDS WORK**; no existe un almacén externo duradero ni respaldo automatizado. El export JSON requiere copia independiente y verificación de recuperación.
- **Integridad forense:** **NOT ATTESTED**; hashes sin firma externa no detectan eliminación/reemplazo de todo el archivo.
- **Precisión meteorológica:** **NOT MEASURED**; todas las pruebas son sintéticas.
- **Estado operativo:** **EXPERIMENTAL / NO DEPLOY**.

## 7. Registro en sombra desde el ciclo (#7, opcional)

`src/ledger_shadow.py` conecta el ciclo de Portinatx con este ledger **solo si** `METEO_LEDGER` apunta a un directorio privado fuera del repositorio (dentro del repositorio se rechaza). No modifica niveles, avisos ni datos públicos; cualquier fallo se ignora y queda en el resultado de `export` (`ledger_sombra`).

- **Pronósticos congelados antes de su ventana**, una vez por hora UTC (los ciclos de 5 min no multiplican registros):
  - precipitación horaria (mm) de cada modelo determinista en el punto de Portinatx, próximas 1–6 h;
  - Hs (m) del modelo de oleaje **en la posición de cada boya** PORTUS (#8), próximas 1–6 h, y su referencia de persistencia (`baseline=true`, última Hs medida; no se congela si tiene más de 120 min, D-021).
- **Observaciones** de las boyas para horas ya cerradas (primera muestra de la hora). Los valores ausentes nunca se congelan como 0.
- El `event_id` usa el día de la ventana, para que pronóstico y observación compartan identidad.

**Límites (gate de #7 aún abierto):**
- PORTUS no aporta aquí un control de calidad, así que las observaciones entran con `qc=UNKNOWN` y el ledger las excluye (`NO_QC_PASS_INSTRUMENT_WITHIN_RADIUS`) hasta que el propietario defina un criterio de QC verificado.
- La precipitación en el sitio no tiene pluviómetro instrumental a ≤3 km: queda congelada sin pareja posible.
- `provider_run_at` es el instante de descarga (cota superior), no la hora real del run.
- El almacén duradero, las copias y la prueba de restauración siguen siendo responsabilidad del operador.

```bash
export METEO_LEDGER="$HOME/meteoportinatx-private/forecast-ledger"
python3 src/nowcast.py export --domain portinatx
python3 src/forecast_ledger.py --root "$METEO_LEDGER" verify
```

## 8. Ciclo supervisado en equipo persistente (Linux, opcional)

`scripts/forensic_cycle.py` ejecuta una captura de Portinatx y verifica el ledger privado. Un bloqueo impide dos ejecuciones simultáneas de este comando; no impide que otro proceso use `nowcast.py` directamente. El proceso exige `METEO_LEDGER` como ruta absoluta fuera del repositorio, crea el directorio privado con modo 700 o rechaza uno existente accesible por grupo u otros y escribe `cycle-health.json` de forma atómica con recuentos, fecha y estado `OK`, `NO_DATA`, `DEGRADED` o `ERROR`. No guarda la salida ni los mensajes de error de proveedores, que podrían incluir credenciales. `OK` solo certifica que el ciclo y la comprobación local terminaron, **no** que la predicción sea buena, que las observaciones tengan QC o que las copias funcionen. Una ejecución sin registros nuevos (incluidos ciclos repetidos en la misma hora) se marca `NO_DATA` y no se considera éxito. La ejecución tiene límite de 20 minutos; un bloqueo activo devuelve código 75. Cada ciclo, sea cual sea su estado, añade además un asiento al diario encadenado (§5.1); si no puede escribirlo, el ciclo queda en `ERROR`, y si el diario tiene la cola incompleta, en `DEGRADED` sin escribir ni reparar nada.

En un Linux de tu propiedad que permanezca encendido, con el repositorio ya instalado y datos/configuración privados del motor, ejecuta primero manualmente:

```bash
export METEO_LEDGER="$HOME/meteoportinatx-private/forecast-ledger"
python3 /RUTA/ABSOLUTA/meteoportinatx/scripts/forensic_cycle.py
cat "$METEO_LEDGER/cycle-health.json"
```

Para la programación se proporcionan `scripts/systemd/meteo-forensic.service` y `.timer`: copia ambos a `~/.config/systemd/user/`, sustituye `/PATH/TO` por rutas absolutas reales en el servicio y ejecuta `systemctl --user daemon-reload`, `systemctl --user enable --now meteo-forensic.timer` y `systemctl --user list-timers meteo-forensic.timer`. Inspecciona `systemctl --user status meteo-forensic.service` y `journalctl --user -u meteo-forensic.service`. El servicio corre al inicio y cada hora mientras el equipo y el servicio de usuario estén activos. El temporizador puede recuperar una ejecución perdida al volver, **no recrea retrospectivamente predicciones ni observaciones de las horas sin servicio**. El servicio de usuario se detiene al cerrar sesión salvo que actives `loginctl enable-linger <usuario>`. No pongas claves en estos ficheros; el motor carga su configuración local privada.

Este mecanismo **no se ha instalado en ningún equipo** ni crea alojamiento duradero. Render Free tiene almacenamiento efímero y no es adecuado para este archivo; GitHub Pages/Actions no son un ledger privado persistente. Una copia de seguridad independiente y una restauración comprobada siguen siendo imprescindibles. Un fallo o ausencia del equipo no genera capturas; vigila la edad de `cycle-health.json` y el temporizador desde fuera del proceso. La disponibilidad de datos y el estado de QC conservan las limitaciones de la sección 7.
