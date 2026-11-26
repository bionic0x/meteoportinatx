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

**Estado actual: la validación de 90 días NO está iniciada ni terminada.** Su estado no se declara en ningún documento: lo calcula `campaign-status` a partir del diario y los registros. Además está **bloqueada por A1** (ver §5.6): con el cableado actual no sale ningún par puntuable.

### 5.1 Diario encadenado de ciclos

`<METEO_LEDGER>/journal/cycles.jsonl` es un diario de solo adición. `scripts/forensic_cycle.py` añade un asiento en **todos** los ciclos (`OK`, `NO_DATA`, `DEGRADED`, `ERROR`), así que los huecos y fallos dejan rastro aunque `cycle-health.json` se sobrescriba. Cada asiento lleva `seq`, `timestamp` (UTC, reloj del equipo), `state`, `added_ids` (ids de registros nuevos en `local/` durante el ciclo), `prev_hash` y `hash` (SHA-256 canónico del asiento sin `hash`; el primero enlaza con 64 ceros).

`verify` recalcula la cadena (secuencia, `prev_hash`, hash, forma canónica, tiempo no decreciente) y exige que exista cada id citado. Si falta un registro o el diario está alterado devuelve `ok: false` con `motivo` (p. ej. `DIARIO_ID_AUSENTE`, `DIARIO_HASH_ALTERADO`, `DIARIO_SECUENCIA_ROTA`) y la CLI sale con código 1. Un ledger antiguo sin diario **no se migra**: `verify` informa `journal.estado=SIN_DIARIO`, `integridad=UNKNOWN`, no «roto». Límites: quien controla el disco puede reescribir la cadena entera de forma coherente (no hay firma ni sello externo); los registros añadidos fuera de `forensic_cycle.py` (p. ej. `nowcast.py export` directo) no figuran en el diario.

### 5.2 Estados y contadores (`campaign-status`)

```bash
python3 src/forecast_ledger.py --root "$METEO_LEDGER" campaign-status [--max-gap-hours 48]
```

La función `ledger_campaign.campaign_status(ledger, *, max_gap_hours)` **no acepta fecha de inicio ni de fin**. N = días UTC con al menos un ciclo `OK` en el diario.

| Estado | Condición |
|---|---|
| `SIN_INICIAR` | Diario ausente o vacío. |
| `EN_CURSO` (`día N/90`) | Cadena íntegra, sin hueco mayor que el umbral, N < 90. |
| `INVALIDO:<motivo>` | Cadena rota o id ausente (`DIARIO_…`), registro corrupto, hueco entre ciclos `OK` mayor que el umbral (`HUECO_MAYOR_QUE_UMBRAL`) o tiempo desde el último `OK` mayor que el umbral (`HUECO_ABIERTO_MAYOR_QUE_UMBRAL`). Exige reiniciar la campaña. |
| `DATOS_COMPLETOS_RESTAURACION_NO_PROBADA` | N ≥ 90 y cadena íntegra, pero sin recibo de restauración válido. **Nunca** se informa como completada. |
| `COMPLETADO` | N ≥ 90, cadena íntegra y recibo de restauración válido anclado en un asiento del diario igual o posterior al día 90. |

**Umbral de hueco: 48 h por defecto. Es una decisión del titular**, propuesta por la auditoría y no calibrada; los ciclos `ERROR`/`NO_DATA` no cierran un hueco. El resumen textual solo dice «completado» si el estado es `COMPLETADO`.

Contadores: días con datos; ciclos esperados (horas entre el primer y el último asiento a cadencia horaria) frente a registrados y `OK`; ciclos por estado; huecos (> 1,5 h entre `OK`), hueco máximo y hueco abierto; fracción de observaciones `UNKNOWN`; pares emparejados y exclusiones por motivo. **Límite:** los episodios se cuentan como días (`event_id` = día de la ventana); días consecutivos de un mismo temporal no son independientes. Tampoco se exige aún cobertura horaria mínima ni un mínimo de pares para `COMPLETADO`: con 0 pares, `COMPLETADO` solo certificaría el archivo, no medición alguna.

### 5.3 Simulacro de restauración

```bash
METEO_LEDGER="$HOME/meteoportinatx-private/forecast-ledger" python3 scripts/ledger_restore_drill.py
```

Toma el mismo bloqueo que el ciclo, copia `local/` y `journal/cycles.jsonl` a un directorio limpio temporal, y con el mismo reloj compara `verify`, `score` y el SHA-256 del bundle exportado. Emite un recibo con hash en `journal/restore-receipts/<sha256>.json`. **`import` no sirve para esto:** deja cada registro como `IMPORTED_UNATTESTED`, fuera de la puntuación. El recibo prueba que la copia de este disco se restaura; no prueba que exista una copia externa ni la atestigua. El simulacro debe repetirse sobre la copia externa real (clon del repo privado o disco de respaldo).

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
5. **Umbrales de invalidez** (hueco máximo, cobertura mínima, pares mínimos) y **criterio QC de PORTUS** (gate QC 1 de D-021).

### 5.6 Bloqueante A1: 0 pares puntuables con el cableado actual

En Portinatx la precipitación no tiene pluviómetro a ≤ 3 km y la Hs de PORTUS entra como `UNKNOWN`; en Pirineo hay observaciones Météo-France con `INSTRUMENT_QC_PASS` pero ningún pronóstico congelado en esas coordenadas. Resultado: **0 pares puntuables**. Arrancar los 90 días así solo mediría la disponibilidad del archivo. Propuesta (cambio aparte, **no implementado aquí**): congelar pronósticos en las coordenadas de las estaciones Météo-France del Pirineo con QC PASS; para PORTUS, que el titular cierre el criterio QC (qué banderas o controles convierten una Hs en `INSTRUMENT_QC_PASS`).

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

`scripts/forensic_cycle.py` ejecuta una captura de Portinatx y verifica el ledger privado. Un bloqueo impide dos ejecuciones simultáneas de este comando; no impide que otro proceso use `nowcast.py` directamente. El proceso exige `METEO_LEDGER` como ruta absoluta fuera del repositorio, crea el directorio privado con modo 700 o rechaza uno existente accesible por grupo u otros y escribe `cycle-health.json` de forma atómica con recuentos, fecha y estado `OK`, `NO_DATA`, `DEGRADED` o `ERROR`. No guarda la salida ni los mensajes de error de proveedores, que podrían incluir credenciales. `OK` solo certifica que el ciclo y la comprobación local terminaron, **no** que la predicción sea buena, que las observaciones tengan QC o que las copias funcionen. Una ejecución sin registros nuevos (incluidos ciclos repetidos en la misma hora) se marca `NO_DATA` y no se considera éxito. La ejecución tiene límite de 20 minutos; un bloqueo activo devuelve código 75. Cada ciclo, sea cual sea su estado, añade además un asiento al diario encadenado (§5.1); si no puede escribirlo, el ciclo queda en `ERROR`.

En un Linux de tu propiedad que permanezca encendido, con el repositorio ya instalado y datos/configuración privados del motor, ejecuta primero manualmente:

```bash
export METEO_LEDGER="$HOME/meteoportinatx-private/forecast-ledger"
python3 /RUTA/ABSOLUTA/meteoportinatx/scripts/forensic_cycle.py
cat "$METEO_LEDGER/cycle-health.json"
```

Para la programación se proporcionan `scripts/systemd/meteo-forensic.service` y `.timer`: copia ambos a `~/.config/systemd/user/`, sustituye `/PATH/TO` por rutas absolutas reales en el servicio y ejecuta `systemctl --user daemon-reload`, `systemctl --user enable --now meteo-forensic.timer` y `systemctl --user list-timers meteo-forensic.timer`. Inspecciona `systemctl --user status meteo-forensic.service` y `journalctl --user -u meteo-forensic.service`. El servicio corre al inicio y cada hora mientras el equipo y el servicio de usuario estén activos. El temporizador puede recuperar una ejecución perdida al volver, **no recrea retrospectivamente predicciones ni observaciones de las horas sin servicio**. El servicio de usuario se detiene al cerrar sesión salvo que actives `loginctl enable-linger <usuario>`. No pongas claves en estos ficheros; el motor carga su configuración local privada.

Este mecanismo **no se ha instalado en ningún equipo** ni crea alojamiento duradero. Render Free tiene almacenamiento efímero y no es adecuado para este archivo; GitHub Pages/Actions no son un ledger privado persistente. Una copia de seguridad independiente y una restauración comprobada siguen siendo imprescindibles. Un fallo o ausencia del equipo no genera capturas; vigila la edad de `cycle-health.json` y el temporizador desde fuera del proceso. La disponibilidad de datos y el estado de QC conservan las limitaciones de la sección 7.
