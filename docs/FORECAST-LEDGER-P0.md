# P0 — Forecast Ledger / archivo de verificación prospectiva

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

## 5. 90 días de investigación y criterios para integrar un conector

1. **Semana 1–2:** comprobar el contrato de fuentes, unidad, periodo, coordenadas, licencia y captura anterior al inicio. No copiar datos personales ni contenido de foro al ledger.
2. **Semanas 2–12:** un conector supervisado congela automáticamente cada pronóstico emitido *antes* del suceso; almacenamiento externo de coste cero previamente verificado, con exportaciones y pruebas de restauración. **El conector aún no existe**: la ejecución actual es manual.
3. **Tras 90 días:** estratificar por familia/estación/horizonte/régimen; calcular denominadores, fracción `UNKNOWN`, casos excluidos; comparar baselines y estimar intervalos bloqueados por episodio si el número independiente lo permite. No declarar mejora por 20 pares sintéticos.
4. **Gates:** procedencia y licencias verificadas; instrumentación activa; controles de desconexión; datos persistentes con restore validado; skill fuera de muestra; reporte de falsas alarmas y fallos críticos.

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
  - Hs (m) del modelo de oleaje **en la posición de cada boya** PORTUS (#8), próximas 1–6 h, y su referencia de persistencia (`baseline=true`, última Hs medida).
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

`scripts/forensic_cycle.py` ejecuta una captura de Portinatx y verifica el ledger privado. Un bloqueo impide dos ejecuciones simultáneas de este comando; no impide que otro proceso use `nowcast.py` directamente. El proceso exige `METEO_LEDGER` como ruta absoluta fuera del repositorio, crea el directorio privado con modo 700 o rechaza uno existente accesible por grupo u otros y escribe `cycle-health.json` de forma atómica con recuentos, fecha y estado `OK`, `NO_DATA`, `DEGRADED` o `ERROR`. No guarda la salida ni los mensajes de error de proveedores, que podrían incluir credenciales. `OK` solo certifica que el ciclo y la comprobación local terminaron, **no** que la predicción sea buena, que las observaciones tengan QC o que las copias funcionen. Una ejecución sin registros nuevos (incluidos ciclos repetidos en la misma hora) se marca `NO_DATA` y no se considera éxito. La ejecución tiene límite de 20 minutos; un bloqueo activo devuelve código 75.

En un Linux de tu propiedad que permanezca encendido, con el repositorio ya instalado y datos/configuración privados del motor, ejecuta primero manualmente:

```bash
export METEO_LEDGER="$HOME/meteoportinatx-private/forecast-ledger"
python3 /RUTA/ABSOLUTA/meteoportinatx/scripts/forensic_cycle.py
cat "$METEO_LEDGER/cycle-health.json"
```

Para la programación se proporcionan `scripts/systemd/meteo-forensic.service` y `.timer`: copia ambos a `~/.config/systemd/user/`, sustituye `/PATH/TO` por rutas absolutas reales en el servicio y ejecuta `systemctl --user daemon-reload`, `systemctl --user enable --now meteo-forensic.timer` y `systemctl --user list-timers meteo-forensic.timer`. Inspecciona `systemctl --user status meteo-forensic.service` y `journalctl --user -u meteo-forensic.service`. El servicio corre al inicio y cada hora mientras el equipo y el servicio de usuario estén activos. El temporizador puede recuperar una ejecución perdida al volver, **no recrea retrospectivamente predicciones ni observaciones de las horas sin servicio**. Comprueba la configuración del servicio de usuario del sistema: puede detenerse al cerrar sesión. No pongas claves en estos ficheros; el motor carga su configuración local privada.

Este mecanismo **no se ha instalado en ningún equipo** ni crea alojamiento duradero. Render Free tiene almacenamiento efímero y no es adecuado para este archivo; GitHub Pages/Actions no son un ledger privado persistente. Una copia de seguridad independiente y una restauración comprobada siguen siendo imprescindibles. Un fallo o ausencia del equipo no genera capturas; vigila la edad de `cycle-health.json` y el temporizador desde fuera del proceso. La disponibilidad de datos y el estado de QC conservan las limitaciones de la sección 7.
