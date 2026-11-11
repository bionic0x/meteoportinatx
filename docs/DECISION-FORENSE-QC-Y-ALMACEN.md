# D-021 — QC instrumental y archivo forense duradero (#7)

**Decisión: 11/11/2026 · estado: política adoptada, almacén remoto NO provisionado.**
Alcance: archivo de investigación y benchmark PROSPECTIVE fuera de muestra.
Sin efectos sobre alertas, modelos, vigilancia 24/7 ni Render Free.

## 1. Fuente de verdad y durabilidad
Se elige **un repositorio GitHub PRIVADO exclusivo** (`meteoportinatx-forecast-ledger-private`) como almacén remoto primario, y **una segunda copia cifrada independiente** en un equipo/disco gestionado por el propietario (backup semanal). No almacenar secretos, datos personales, posición de la vivienda ni observaciones introducidas por el dueño. Solo identificadores y coordenadas públicas verificadas de estaciones, métricas instrumentales autorizadas, predicciones congeladas, motivos QC y hashes. Evitar Git LFS y archivos masivos; segmentar por fecha y episodio.

Motivación: Render Free carece de disco persistente y los artefactos de GitHub Actions expiran; ambos quedan descartados como sistema de registro duradero. Git privado mantiene historial y gestión de acceso, **pero Git no es WORM ni garantiza inmutabilidad ni backup**. La segunda copia, el registro de hashes SHA-256 y pruebas de restauración son imprescindibles. No afirmar «archivo duradero verificado» hasta demostrar una restauración desde la copia externa de **20 pares** pronóstico/observación con los mismos hashes, puntuación y exclusiones. Proteger rama y acceso mínimo donde la cuenta lo permita. No activar servicios de pago. Crear el repositorio privado y el secreto de autenticación de solo alcance necesario requiere intervención del titular: el conector actual no ofrece crear repositorios ni escribir secretos.

El ledger local `src/forecast_ledger.py` mantiene la cronología `issued_at`, `provider_run_at`, `valid_from`, `valid_to` y `captured_at`. Sólo capturas anteriores a la validez son prospectivas; las importaciones remotas quedan excluidas del benchmark prospectivo salvo atestación independiente. Escribir primero localmente (operación atómica), replicar después; registrar recibos y SHA-256. Si la réplica falla, comunicar `ARCHIVE_AT_RISK` sin fingir que está respaldado.

## 2. Criterio QC para boyas PORTUS (Hs)

| Control | Resultado |
|---|---|
| Identidad de boya, coordenadas verificadas, instrumento, proveedor, unidad y fecha/hora UTC con zona | Falta alguno: `UNKNOWN` |
| Muestra no finita, Hs negativa, timestamp imposible, flag proveedor explícitamente inválido, identidad contradictoria | `REJECTED` |
| Hmax presente pero menor que Hs, Tp no positivo, dirección fuera de 0–360°, saltos bruscos no corroborados, duplicados/conflictos de la misma boya/hora | `UNKNOWN`, revisión manual; no declarar error físico automático en episodios extremos |
| Muestra físicamente plausible sin **flag de calidad del proveedor documentado**, o sin trazabilidad hasta la medición original | `UNKNOWN` (**no** promocionar a PASS por el mero hecho de proceder de una API oficial) |
| Flag de calidad del proveedor inequívocamente bueno, semántica documentada, estación/UTC/unidad verificadas, sin anomalías ni duplicados | `INSTRUMENT_QC_PASS` tras revisión/auditoría independiente del adaptador |

La implementación actual de `src_portus` NO publica un campo explícito de calidad instrumental de origen: **por defecto el archivo forense debe clasificar esas lecturas como `UNKNOWN`** hasta incorporar y validar el indicador del proveedor. No alterar retroactivamente un `UNKNOWN` original: conservar revisión y evidencia como nuevo registro enlazado. No mezclar Hs con Hmax, oleaje de fondo o altura dentro de Portinatx.

**Frescura ≠ QC retrospectivo:** para decisiones en directo, la observación Hs caduca al superar 120 min (criterio operativo actual, sujeto a calibración con la cadencia real de PORTUS); una lectura histórica válida no se rechaza únicamente por ser antigua. Cada dato conserva `observed_at` en UTC, `captured_at`, `source_id` y hash de origen. No usar hora de descarga como hora de instrumento. Duplicados deben conservarse con motivo de exclusión o deduplicación verificable.

**Pareo de verificación** (distinto del QC instrumental): mismo identificador de estación y dominio espacial, mismas unidades, misma ventana de validez (en el ledger, coincidencia exacta), modelo en la coordenada real de la boya y tiempo de modelo a ±30 min solo para diagnóstico `sea_model_check`. Para skill prospectivo se exige además modelo previamente congelado y misma observación verificada. No comparar máximo de pronóstico a 72 h en la bahía contra última boya a 68–172 km. Ausencia de par válido: `NO_COMPARABLE`, no «modelo acertó/falló».

## 3. Gates de activación
1. Identificar los flags QC de PORTUS, su diccionario y periodicidad (documentación del proveedor); añadir muestras reales autorizadas y tests.
2. Aprovisionar repositorio privado, credencial mínima, backup cifrado externo y prueba de restauración de 20 pares; documentar integridad y revocación de acceso.
3. Ejecutar 90 días en sombra con línea base, denominadores, episodios independientes, motivos de exclusión y sin tocar pesos de alerta.
4. Activar únicamente tras revisar datos, permiso de reutilización y fallos de cron. Mientras tanto #7 **abierta**.

Fuentes: `docs/FORECAST-LEDGER-P0.md`, `src/forecast_ledger.py`, [Puertos del Estado, tiempo real](https://portus.puertos.es/Portus/html/info/infotr.html) y [FAQ sobre representatividad de boyas](https://www.puertos.es/servicios/oceanografia/faqs).
