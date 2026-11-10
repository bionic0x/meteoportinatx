# Modelo meteorológico y programa de validación

MeteoPortinatx tiene una base útil como observatorio local que reúne observación, modelos externos y diagnóstico físico. Su desarrollo científico debe centrarse primero en conservar la procedencia de cada dato, impedir que la falta de información produzca certezas y medir si cada transformación añade valor fuera de la muestra. El código disponible no acredita una superioridad predictiva sobre los proveedores originales.

Revisión del código `fded39b710e1981cb2583adff2462244c151be9f`, realizada el 10 de noviembre de 2026. Se han aplicado las perspectivas **Spatial Data Scientist** y **Research Synthesist** de `msitarzewski/agency-agents`, revisión `8ae6164602c95ca78828b148b9052460ee426885`. Son guías de trabajo para este análisis, no acreditaciones profesionales ni fuentes de validación meteorológica.

## Alcance y fuerza de la evidencia

Se revisaron los tres motores Python, las pruebas del metaanálisis e integración, y las notas públicas de arquitectura y forense. No se consultaron archivos históricos privados, observaciones originales de la DANA, artículos científicos externos ni respuestas actuales de los proveedores. Por tanto, esto es una revisión técnica y un diseño de investigación, no una revisión bibliográfica sistemática ni un backtest meteorológico.

| Evidencia | Qué permite concluir | Qué no demuestra |
|---|---|---|
| Código ejecutable y pruebas sintéticas | Algoritmos, contratos, condiciones límite y defectos reproducibles | Exactitud meteorológica en campo |
| Documentación pública de un episodio | Hipótesis y lecciones declaradas por el proyecto | Replicación independiente de sus cifras |
| Reproducciones locales descritas aquí | Comportamiento con entradas concretas | Frecuencia real de esos fallos en el proveedor |
| Plan y métricas siguientes | Cómo evaluar una mejora | Que la mejora ya exista o esté validada |

## 1. Qué modelo existe realmente

Hay cuatro capas que conviene distinguir en documentación y producto:

1. **Fuentes externas:** observaciones, radar, avisos y pronósticos numéricos. Un mismo proveedor de acceso puede servir modelos de instituciones diferentes; eso no independiza sus errores ni garantiza disponibilidad independiente.
2. **Diagnóstico local:** interpretación del perfil térmico, nieve, viento, mar y reglas de evidencia. Son transformaciones y heurísticas aplicadas a datos externos.
3. **Síntesis:** ventanas temporales, fracciones ensemble, comparación de familias y desacuerdos. La síntesis aporta legibilidad, pero puede ocultar diferencias de cobertura y procedencia si se resume demasiado.
4. **Aprendizaje retrospectivo experimental:** puntuación de pronósticos frente a observaciones y factores de corrección. El aprendizaje necesita validación separada de los datos con los que se ajusta.

En costa, `src/portinatx_degen.py:2662` y `:2710` forman parte de la separación entre precaución propia, avisos y diagnóstico. La capa forense reúne emparejamientos, métricas, correcciones y regímenes en `src/portinatx_degen.py:4024`. Es una arquitectura apropiada para explicar por qué una señal merece atención sin atribuir autoridad oficial al consenso de modelos.

En montaña, `src/pirineo.py:320` construye diagnósticos desde perfiles verticales; `src/pirineo.py:707` resume valores puntuales. El horizonte extendido usa familias ECMWF, NCEP y DWD (`src/pirineo_meta.py:35`), mantiene separados los deterministas y declara las fracciones como no calibradas (`src/pirineo_meta.py:232`). Las teleconexiones son contexto y no modifican probabilidades (`src/pirineo_meta.py:366`, `:420`). Estas restricciones deben conservarse.

## 2. Hallazgos concretos y prioridades

### P0 — La cobertura incompleta de nieve puede convertirse en ausencia de nieve

`daily_member` (`src/pirineo_meta.py:194`) suma los valores de nieve no nulos cuando existe al menos uno. La condición `measurable` comprueba cobertura de precipitación, no cobertura de nieve. `family_summaries` (`:232`) utiliza después esos acumulados para percentiles y fracciones de superación.

**Reproducción ejecutada:** se tomó `fixture(days=1)` de `tests/test_pirineo_meta.py`, con 12 miembros y precipitación completa. Se sustituyó cada serie de nieve por `[0] + [None] * 23`. El resultado fue `snow_cm={p10:0,p50:0,p90:0}`, `snow_ge5_fraction=0` y `snow_ge10_fraction=0`. Solo se conocía una hora de las 24.

Esto contradice el objetivo de distinguir dato ausente y nieve nula. No prueba que el proveedor esté enviando ese patrón hoy; demuestra que el motor lo aceptaría. El parser determinista también suma cobertura parcial (`src/pirineo_meta.py:118`), y las ventanas de 24/72 horas suman valores disponibles sin publicar completitud (`src/pirineo.py:707`).

**Cambio propuesto:** declarar para cada acumulado la ventana exacta, número de intervalos esperados y válidos, y cobertura. Para un acumulado de día completo, exigir todos los intervalos o publicar explícitamente un acumulado parcial; un umbral menor debe justificarse por variable y no utilizarse para inferir un total diario. Si una fracción de miembros no tiene acumulados válidos, excluir esos miembros y declarar el denominador; con soporte insuficiente, devolver `UNKNOWN`.

**Aceptación:** nieve con 1/24 intervalos nunca se representa como total diario cero; un día completamente observado sin nieve sí produce cero; límites de día, duplicados, desorden y cadencia irregular tienen pruebas específicas. Aplicar el mismo contrato a pronóstico determinista y ensemble.

### P0 — El soporte por familias se declara a escala de fila, no de variable

`combine` (`src/pirineo_meta.py:275`) renormaliza correctamente cada variable con las familias que tienen dato. Sin embargo, `n_independent_families` y `evidence_status` cuentan todas las familias presentes en la fila, aunque no todas aporten nieve.

**Reproducción ejecutada:** ECMWF aportó nieve; NCEP conservó datos de bulbo húmedo, pero sus dos fracciones de nieve se establecieron a `None`. El agregado devolvió nieve de ECMWF con `n_independent_families=2` y `evidence_status=multi-family`.

**Cambio propuesto:** publicar por variable `contributing_families`, `n_families`, denominadores de miembros, cobertura y pesos efectivos. El agregado de nieve del ejemplo debe decir una familia. Es preferible «familias institucionales» a «familias independientes»: no se ha demostrado independencia estadística de errores.

**Aceptación:** perder una variable en una familia reduce su soporte y no produce certeza artificial; perder todas produce `UNKNOWN`; la interfaz muestra el soporte de la variable que está interpretando.

### P1 — Hora de recolección no equivale a inicialización del modelo

La salida extendida usa `issued_utc` del ciclo de consulta y declara `model_run_init: UNVERIFIED` (`src/pirineo_meta.py:451`, `:485`). `compare_issued` (`:313`) compara ciclos de consulta distintos. Una diferencia de resultados puede ser una nueva corrida, actualización parcial, cambio de familias disponibles o revisión del proveedor; el código no acredita cuál.

**Cambio propuesto:** conservar `collected_at`, `forecast_reference_time`, `valid_time`, identificador de producto/modelo, revisión, hashes y cobertura. Cuando no se conoce la inicialización, mostrar «cambio entre consultas», sin atribuirlo a una nueva corrida. No mezclar productos con disponibilidad temporal diferente en una evaluación como si se hubiesen conocido simultáneamente.

**Aceptación:** dos consultas de la misma corrida no crean dos muestras independientes; cambios de composición se distinguen de revisiones meteorológicas; los datos sin inicialización verificable no sirven para afirmar skill a una antelación exacta.

### P1 — Los 30 días del replay son un umbral de código, no garantía de calibración

`score_replay` (`src/pirineo_meta.py:332`) agrupa errores Brier por fecha válida, y `_normalize_weights` (`:254`) activa ponderación con al menos 30 fechas por familia. Esto evita contar cada estación como un día nuevo, pero no prueba independencia de episodios consecutivos ni establece particiones de ajuste y evaluación. Además, el resumen agrupa por familia sin estratificar umbral, estación o antelación; un Brier agregado puede comparar mezclas de casos diferentes.

**Cambio propuesto:** exigir identificador de evento, variable, umbral, estación, antelación, disponibilidad y versión; deduplicar pronósticos; evaluar familias sobre casos comunes. Usar un bloque de ajuste, uno de validación y un test final cronológico intacto; comparar la ponderación aprendida con pesos iguales por familia. Un mínimo de fechas puede seguir siendo condición operativa, pero no autoriza por sí solo una afirmación de fiabilidad.

**Aceptación:** no hay fechas/eventos compartidos entre ajuste y test; toda ponderación es reconstruible con información disponible antes de su emisión; resultados incluyen tamaño efectivo, ocurrencias positivas y negativas e intervalos de incertidumbre.

### P1 — Física aproximada de nieve y representatividad espacial

Las cotas son desplazamientos fijos respecto al cero de bulbo húmedo: −300 m para copo, −100 m para cuajado y +200 m para acumulación (`src/pirineo.py:320`). Kuchera se calcula a partir de la máxima temperatura seleccionada de la columna y se limita a 4–25 (`:312`). La inversión observada es una regresión altitud/temperatura entre estaciones frescas (`:405`), por lo que mezcla altitud con orientación, masa de aire y representatividad si las estaciones no son comparables.

Estos cálculos son hipótesis físicas útiles para diagnóstico. No constituyen una simulación de microfísica, energía del suelo, compactación, fusión ni estabilidad del manto. Una cota precisa en metros puede dar una impresión de exactitud mayor que la evidencia disponible.

En el extendido, base y cumbre comparten latitud/longitud y cambian la elevación enviada al proveedor (`src/pirineo_meta.py:85`). Eso no modela automáticamente sus exposiciones, relieve intermedio ni redistribución por viento.

**Cambio propuesto:** contrastar cotas contra transectos de observación y documentar su definición; publicar intervalos por régimen; identificar elevación de rejilla y del punto, distancia y exposición. Asegurar que niveles de presión bajo terreno no entren en diagnósticos locales. Separar nieve caída, agua equivalente, nieve sobre suelo y transitabilidad.

**Aceptación:** un resultado contiene procedencia y cobertura; no se deriva apertura de pistas o riesgo de aludes de centímetros previstos; sesgo y cobertura de intervalos se evalúan por altitud, orientación, régimen y antelación.

### P1 — Aprendizaje forense: distinguir descripción y mejora predictiva

`forensic_scores` (`src/portinatx_degen.py:3823`) calcula MAE, RMSE, cocientes y contingencias. `learn` (`:3934`) contrae factores hacia uno y aprende pesos. `regime_learning` (`:4062`) exige tres episodios para factores descriptivos y evita aplicación automática. Son salvaguardas útiles, pero tres episodios y una contracción no prueban generalización.

`forensic_waves` (`:3909`) agrega pares horarios por modelo, y la confianza de `learn` depende del número de pares. Horas sucesivas de un temporal están correlacionadas: ese número no equivale a episodios independientes. En lluvia, `n_eff` suma pesos de fechas; tampoco es una estimación completa de tamaño efectivo ante autocorrelación.

**Cambio propuesto:** presentar esos valores como soporte descriptivo, registrar episodios y estimar incertidumbre por bloques. Evaluar por separado corrección de amplitud, desplazamiento espacial y desfase temporal. Una corrección de ubicación no debe aprenderse usando la observación futura del evento evaluado.

Las cifras de la DANA en `docs/FORENSE-PUBLICO.md` son un estudio retrospectivo declarado por el proyecto. Los originales privados no se examinaron aquí. En particular, el propio documento descarta el multiplicador universal ×2 de oleaje tras emparejar espacialmente modelo y boya: esa cautela debe sobrevivir a cualquier nueva síntesis.

## 3. Programa de validación reproducible

### Reproducción de los dos P0

Ejecutado desde la raíz del repositorio, sin red ni escritura de datos de aplicación:

```bash
python3 - <<'PY'
import sys
sys.path[:0] = ['src', 'tests']
import pirineo_meta as p
from test_pirineo_meta import fixture
sample = fixture(days=1)
for row in sample:
    for key in row['hourly']:
        if key.startswith('snowfall'):
            row['hourly'][key] = [0] + [None] * 23
s = p.family_summaries(p.parse_ensemble(sample, 'ecmwf_ifs025_ensemble'),
                       'ecmwf_ifs025_ensemble')
print('P0 cobertura:', s['masella:upper']['2026-11-10']['snow_cm'])
a = p.family_summaries(p.parse_ensemble(fixture(days=1),
    'ecmwf_ifs025_ensemble'), 'ecmwf_ifs025_ensemble')
b = p.family_summaries(p.parse_ensemble(fixture(days=1, model='ncep_gefs_seamless'),
    'ncep_gefs_seamless'), 'ncep_gefs_seamless')
for days in b.values():
    for row in days.values():
        row['snow_ge5_fraction'] = row['snow_ge10_fraction'] = None
r, _ = p.combine({'ecmwf_ifs025_ensemble': a, 'ncep_gefs_seamless': b})
row = r['masella']['upper']['2026-11-10']
print('P0 soporte:', row['snow_ge5_member_fraction'],
      row['n_independent_families'], row['evidence_status'])
PY
```

Salida observada: `P0 cobertura: {'p10': 0.0, 'p50': 0.0, 'p90': 0.0}` y `P0 soporte: 1.0 2 multi-family`. La primera salida deriva de cobertura de nieve 1/24; la segunda tiene solo una familia con dato de nieve. Son casos de regresión pendientes, no pruebas superadas del comportamiento deseado.

### Unidad y archivo de evaluación

Cada registro debe conservar producto/modelo/versión, familia, corrida, emisión/recolección, validez y ventana, coordenadas, elevación, unidades, variable, umbral, miembro, fuente y versión de observación, controles de calidad y disponibilidad. Añadir identificador de episodio y hashes del dato bruto. Toda transformación debe registrar versión y parámetros.

Mantener UTC internamente y una convención explícita para ventanas de día local; comprobar los días de 23 y 25 horas. No comparar acumulados con intervalos distintos. Congelar lo disponible en el momento de decidir: las observaciones revisadas pueden incorporarse como verdad de verificación identificada, nunca como predictor retrospectivo.

### Diseño temporal y espacial

1. Crear un inventario de episodios, incluyendo días tranquilos y falsas alarmas. Separar lluvia convectiva, frentes, viento y temporal marino; en montaña, procesos de nieve y deshielo.
2. Dividir cronológicamente por episodios completos. Durante desarrollo usar evaluación con origen móvil; reservar el último bloque como test final que no decide parámetros.
3. Hacer una segunda prueba por zonas/estaciones retenidas para detectar sobreajuste local. Evaluar sensibilidad a distancia, altura y agregación; inspeccionar autocorrelación espacial de residuos.
4. Comparar modelos en la misma intersección de casos válidos y presentar también cobertura total. Un sistema no debe parecer mejor porque omite los episodios difíciles.
5. Estimar intervalos con remuestreo por episodios o bloques coherentes. Si el número de eventos independientes es pequeño, publicar la imprecisión y mantener el resultado como exploratorio.

No fijar un número universal de episodios que garantice calidad. Planificar tamaño según frecuencia del evento, efecto útil y precisión de intervalos; para eventos raros puede requerirse más de una temporada. Publicar los recuentos por estrato y no ocultar celdas sin soporte.

### Baselines y métricas

| Objetivo | Referencias mínimas | Métricas y desglose |
|---|---|---|
| Lluvia acumulada | Proveedor bruto; media/mediana simple; climatología compatible | MAE, RMSE, sesgo, POD/FAR/CSI por umbral y antelación; cobertura; error de desplazamiento separado de amplitud |
| Probabilidad de evento | Frecuencia climatológica entrenada; fracción cruda; pesos iguales por familia | Brier y Brier skill frente a baseline; diagramas de fiabilidad con recuentos; resolución y discriminación; coste de falsas alarmas y omisiones |
| Distribución de precipitación/nieve | Ensemble original y mezcla simple | CRPS donde haya distribución suficiente; cobertura y anchura de intervalos; histogramas de rango con sus límites de dependencia |
| Cota y fase | Salida bruta del proveedor; regla fija actual | Error de cota en metros con definición observacional; matriz lluvia/mixta/nieve; sesgo por altitud y régimen |
| Nieve nueva | Proveedor bruto; relación fija nieve/agua como comparación | MAE/sesgo en cm y agua equivalente cuando se observe; ventanas de medición y compactación explícitas |
| Oleaje | Modelo en coordenadas de boya; persistencia a horizonte apropiado | Sesgo/RMSE de Hs, periodo y dirección; error de pico y hora; separación por boya, exposición y temporal |
| Decisión práctica | Decisión habitual del usuario; alternativa sin el producto | Anticipación útil, omisiones, falsas alarmas por episodio, coste/pérdida y carga de revisión; primero en modo sombra |

No usar MAE como única puerta para extremos, ni porcentaje de acierto dominado por días sin evento. No comparar Brier entre umbrales con prevalencias muy distintas sin contexto. En costa, altura significativa en boya, rompiente y rebase en una cala son objetivos diferentes.

### Experimentos escalonados

**E0 — Integridad:** completar contratos de cobertura y procedencia, reproducir los fallos P0 y añadir pruebas de regresión. Es el requisito previo para un histórico útil.

**E1 — Referencia sin ajuste:** congelar pronósticos originales y observaciones controladas, producir un informe de skill y disponibilidad por objetivo. Si no hay suficientes eventos, publicar el inventario y la incertidumbre, no coeficientes nuevos.

**E2 — Correcciones mínimas:** comparar sesgo por régimen con contracción y pesos iguales; probar complejidad adicional solo si mejora el test y no empeora extremos ni disponibilidad. Una ablación debe mostrar qué aporta DEM, perfil, ensemble y corrección por separado.

**E3 — Calibración probabilística:** calibradores simples elegidos con validación interna y ajustados únicamente sobre el pasado. Mantener conjuntos independientes para medir fiabilidad. La etiqueta «probabilidad calibrada» se concede por variable, umbral, zona y horizonte, nunca globalmente.

**E4 — Uso en sombra:** generar resúmenes/avisos candidatos sin depender de ellos para operaciones críticas; comparar con decisiones reales y revisión humana. Tras reunir evidencia, definir criterios de activación y reversión para cada uso.

## 4. Contrato científico recomendado para el producto

Cada tarjeta debería responder: **qué se espera, dónde, durante qué ventana, de qué fuentes procede, qué datos faltan, qué desacuerdo hay y cuándo revisar**. Mantener visibles los tres ejes de costa; en montaña distinguir nieve nueva de estado de pistas y boletín de aludes.

En 0–72 h puede mostrarse diagnóstico local condicionado a observaciones y perfiles disponibles. En 3–15 días conviene priorizar escenarios, persistencia del patrón y dispersión, con menor detalle local. La resolución visual no debe exceder la resolución efectiva del dato. Un cambio de escenario debe indicar si nace de nueva información meteorológica o pérdida de fuentes.

El potencial científico más defendible es acumular evidencia local auditable y convertirla en mejores decisiones y explicaciones. Un modelo neuronal propio, un multiplicador por teleconexiones o una puntuación única de «confianza» deben esperar a una comparación que demuestre su utilidad frente a alternativas más sencillas.

## 5. Primera entrega técnica propuesta

Priorizar una entrega pequeña con tres resultados revisables: contrato de cobertura por variable; soporte por familias también por variable; exportación de un registro de verificación congelado con procedencia temporal. Acompañarla de reproducciones de los dos P0, pruebas de regresión y un informe de cobertura real cuando la red permita consultar proveedores. No se han modificado motores ni ejecutado esa entrega durante esta revisión.

El criterio de avance será que ningún dato incompleto parezca una observación de cero y que toda afirmación predictiva pueda remontarse a sus fuentes y evaluarse. A partir de ahí, el proyecto podrá medir con rigor qué valor añaden su interpretación local y su aprendizaje retrospectivo.
