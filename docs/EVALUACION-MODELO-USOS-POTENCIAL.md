# Evaluación del modelo, los usos y el potencial

Fecha: 11 de noviembre de 2026. Base de código: `main` en `fded39b` (0.5.0). No incluye los cambios de [bionic0x/meteoportinatx#5](https://github.com/bionic0x/meteoportinatx/pull/5).

## Método

Se activaron seis perfiles de la colección pública [agency-agents](https://github.com/msitarzewski/agency-agents), la misma de la que procede el marco de gobernanza «Ante Agency Agents / NEXUS» del motor costero (`src/portinatx_degen.py:2153`). Cada perfil revisó el repositorio por separado y sin modificarlo:

| Perfil | Pregunta |
|---|---|
| Statistician (`academic/`) | ¿Qué calcula el modelo y qué evidencia lo respalda? |
| Model QA Specialist (`specialized/`) | ¿Qué riesgos lógicos, físicos y de prueba tiene? |
| Spatial Data Scientist (`gis/`) | ¿Cómo trata el espacio y el relieve? |
| Product Manager (`product/`) | ¿Para quién sirve y para qué no? |
| Trend Researcher (`product/`) | ¿Qué hueco ocupa y qué potencial tiene? |
| Reality Checker (`testing/`) | ¿Se sostienen las conclusiones anteriores? |

Convenciones: **[V]** verificado en código (con `archivo:línea`), **[I]** inferencia no comprobada con datos. Las referencias de línea son de `fded39b` y pueden desplazarse. Los enlaces externos se citan como fuente; lo no contrastado se marca «no verificado».

Conclusión general: **el proyecto es una buena referencia metodológica de nicho, con disciplina honesta sobre la incertidumbre, pero hoy no puede demostrar pericia predictiva** porque no conserva los pares pronóstico–observación necesarios para medirla.

---

## 1. El modelo

### 1.1 Qué calcula de verdad

**Portinatx** es un sistema de reglas, no un modelo probabilístico:

- **Fusión por máximo** [V] (`src/portinatx_degen.py:2078-2083`): nivel = máx(suelo institucional, observación, modelos topados en `alert`). `alarm` exige confirmación independiente: otra observación de otro grupo y otra raíz de fuente, al menos una local (`:2091-2103`), o dos runs de alta resolución consecutivos centrados más señal local (`:2106-2110`, `:1011-1035`).
- **Histéresis asimétrica** [V] (`:2128-2149`): sube al instante; baja un escalón tras 3 ciclos seguidos y nunca con cobertura insuficiente o retención manual. Bajar desde `alert` exige además un pluviómetro vecino fresco (`:2331-2342`).
- **Umbrales** [V] fijados a mano en `CFG` (`:240-309`); el propio motor los declara «de partida, no calibrados» (`:2248`). Los de suelo saturado salen de dos observaciones (`:258-261`).
- **Ensembles** [V]: fracción bruta de miembros que superan 50 mm/24 h, 100 mm/12 h y 30 mm/1 h, convertida a nivel con cortes fijos (`:1847-1866`). El «conjunto» es la media simple de fracciones de 5 sistemas (`:3417-3458`).
- **Predicciones falsables** [V] (`:2363-2429`): binarias y deterministas (p. ej. «≥2 mm en 60 min» si la intensidad es ≥5 mm/h), verificadas como HIT/MISS/UNVERIFIABLE con ventana −10/+20 min. El resumen es un conteo.
- **Forense** [V]: pares estación-día-modelo-antelación (`:3793-3816`) con olvido de 10 días de semivida sobre 14 días de memoria (`:3586-3595`); MAE, RMSE, POD/FAR/CSI a 10 y 30 mm (`:3823-3849`); factor de corrección contraído hacia 1 (`:3936-3943`); pesos por modelo ∝ 1/(MAE relativo + 0,2) (`:3948-3952`). La corrección por régimen está bloqueada hasta 3 episodios y nunca se aplica sola (`:4062-4082`).

**Pirineo** es física determinista con constantes fijas:

- Cotas de nieve = cero de bulbo húmedo −300/−100/+200 m, nieve/agua de Kuchera y fracción sólida en rampa lineal [V] (`src/pirineo.py:269-275`, `:312-317`, `:345-347`).
- Solo dos perfiles ARPEGE (norte y sur) con 5 niveles de presión [V] (`:104-105`); inversión por una única regresión T–altitud para todo el dominio [V] (`:405-418`); föhn con 3 pares fijos y solo flujo norte [V] (`:87-88`, `:396`).
- Metaanálisis 3–15 días [V] (`src/pirineo_meta.py:232-272`): fracciones de miembros por familia ECMWF/GEFS/ICON con pesos iguales; pasan a 1/(Brier+0,02) solo con ≥30 días válidos y tope 0,65. El «contrarian» salta con Δ≥0,2 en dos familias (`:420-431`). Las teleconexiones nunca entran en el cálculo (`:376-385`).

### 1.2 Dónde la afirmación supera a la evidencia

1. **Las «P(…)» no son probabilidades.** Las cadenas de evidencia de Portinatx rotulan como `P(24h≥50)` fracciones de miembros sin calibrar [V] (`portinatx_degen.py:1855`, `:1867`). `pirineo_meta.py` es más honesto («raw-member-fraction», `:250`).
2. **Falsa independencia.** IFS/AIFS y GEFS/AIGEFS comparten centro [V] (`:3359-3365`) y probablemente análisis inicial [I]; promediarlos con igual peso exagera el consenso. En la forense, 11 estaciones de una isla el mismo día son casi una sola observación: POD/FAR/CSI cuentan estación-días [V] (`:3834-3840`).
3. **«Mejor modelo» con comparación múltiple en muestra**: 5 modelos × 3 antelaciones sobre unos 3 días de lluvia (`docs/FORENSE-PUBLICO.md`). El factor aprendido nunca se evalúa fuera de muestra [V].
4. **Gate de régimen inalcanzable**: exige 3 episodios, pero el archivo se poda a 14 días [V] (`:3639`).
5. **Ponderación por Brier dormida**: no hay código que escriba `replay/cases.jsonl`; solo lo lee [V] (`pirineo.py:858`).
6. **Contrarian sin descontar ruido**: con 30 miembros y p≈0,5, Δ≥0,2 entre dos runs ocurre por azar en torno al 6 % de los punto-días [I, cálculo binomial], y se evalúan unos 90 por ciclo.
7. **Las predicciones no tienen referencia**: «sigue lloviendo» es persistencia, y las de cese solo se emiten cuando el motor decide bajar [V] (`:2376`), lo que introduce selección.
8. **La regla del máximo acumula falsas alarmas** al crecer el número de canales; no hay FAR medida del nivel fusionado.
9. **Histéresis contada en ciclos, no en minutos**, mientras el hosting gratuito no garantiza cadencia.

### 1.3 Problemas espaciales

- **Etiqueta de vecindad errónea** [V]: el texto dice «±17 km» (`portinatx_degen.py:1795`, `:1855`), pero dos de los 7 puntos están a 27–30 km.
- **`sea_model_check` no está emparejado** [V] (`:2253-2267`): compara el máximo de 72 h del modelo en Portinatx con el Hs actual de boyas a 80–175 km, y con un sector (330–100°) distinto del de la bahía (290–60°, `:224-225`). Contradice la afirmación del README de que el oleaje solo se compara apareado. La forense sí empareja correctamente (`:3760-3771`).
- **Red de pluviómetros al sur del sitio** [I, según el análisis espacial; no reproducido]: las estaciones estarían en latitud ≤39,085 y el sitio está en 39,115 (`:202`), lo que confina el desplazamiento de centroides al casco de la red.
- **Sesgo radar–pluviómetro** [V] (`:2433-2463`): usa el máximo 3×3 de dBZ, compara tasa instantánea con acumulados de 8–90 min y coordenadas de núcleo urbano.
- **Escorrentía con proxy fuera de cuenca** [V]: la estación B908X, limitada por el propio código a `watch` (`:1609-1614`).
- **Movimiento del radar escalar** [V] (`:1671-1675`): la pendiente de la distancia al eco más cercano confunde crecimiento con desplazamiento.
- **Pirineo**: la cota de nieve del mapa y de la tabla usa solo el perfil sur [V] (`src/pirineo_app.html:334`, `:341`, `:457`); el enfriamiento por fusión está documentado pero no se aplica [V] (`pirineo.py:111`); la inversión mezcla Cerdanya, Andorra y Capcir en una sola recta [V]; la orientación y la pendiente no entran en la física [V]. Posible doble corrección de altitud, porque Open-Meteo ya ajusta la temperatura a la cota pedida [I].
- **Desajuste de escala** [I]: una cala de 300–500 m o una pista de esquí frente a modelos de 1,5–25 km.

### 1.4 Auditoría de calidad del modelo

El selftest pasa entero (106 + 13 comprobaciones propias y la batería unittest). Los hallazgos salen de leer el código y de sondas con entradas sintéticas; prueban lógica, no acierto.

**Gravedad alta**

- **H1. La cobertura cuenta canales, no fenómenos** [V, reproducido]. Con lluvia observada, pluviómetros, radar y rayos sin datos, pero viento y mar vivos, `fuse` devuelve `quiet` con `insufficient=False` (`portinatx_degen.py:2119-2120`). Basta con dos canales observados vivos de cualquier tipo. Es exactamente el caso que el diseño quiere evitar: ausencia de datos de lluvia leída como calma. `HAZARD_FAMILY` existe (`:2175`) pero no se usa para la cobertura.
- **H2. Datos viejos o vacíos que cuentan como observación válida** [V, según la auditoría]: una boya de hace 5 h sigue disponible; un radar con frames de hace 6 h o todos duplicados da `available=True` y nivel 0 (`:1664`); modelos u oleaje con todos los valores en `None` se convierten en 0 (`:1780`, `:1885`); `ch_rain_obs` no controla la edad de AEMET ni de METAR.
- **H3. Ningún ciclo de Portinatx se puede reproducir** [V]: el snapshot congelado elimina los payloads de las fuentes (`:2804`), `state.json` y las cachés se sobrescriben, `now_utc()` se llama dentro de los canales sin poder inyectar el reloj y no se guarda hash de `CFG`. Solo el backend guarda en bruto el Pirineo.

**Gravedad media**

- **M1. Una sola observación puede dar `alarm`** [V]: la confirmación independiente solo se exige cuando el máximo observado es 2. Un canal que llega a 3 por sí solo (rayos ≥50 flashes, B908X ≥60 mm/h, un pluviómetro vecino) da `alarm` directamente (`:2083`, `:2091`). `ch_lightning` no tiene test.
- **M2. El umbral del radar depende de la relación Z–R** [V]: se toma el máximo de Marshall-Palmer y la «tropical» (`:1692`); con la tropical, 40 dBZ ya dan unos 21,6 mm/h, así que `alert` salta hacia 40 dBZ y no a los 45 configurados.
- **M3. Las anomalías caducan a las 6 h sin revisión** (`:2300`), contra la doctrina de no normalizarlas en silencio (`:2159`).
- **M4. Histéresis en ciclos**: de `alarm` a `quiet` en 9 ciclos (unos 45 min a 300 s); el botón «Actualizar» despierta el bucle y acelera la bajada (`:4458`).
- **M5. Ola modelizada y boya mal emparejadas** en `sea_model_check` (ver 1.3).
- **M6. Física de montaña** [V]: con un lago frío en el valle, `_zero_height` devuelve el cruce por encima de la capa cálida (con −3 °C a 1100 m da un isocero de 2000 m y no avisa de lluvia engelante); `wet_bulb_c` usa la aproximación de Stull a 1013 hPa, que a 1500–2400 m se desvía hasta unos 0,45 °C justo alrededor del umbral Tw ≤ 0,5; la fracción de bulbo húmedo ≤0 no depende de que haya precipitación (un día seco da 1,0); Kuchera toma Tmax solo entre 850 y 500 hPa.
- **M7. Föhn e inversión**: sin perfil, `foehn_diag` devuelve 0 horas en lugar de «desconocido»; `obs_inversion` declara inversión con +1 °C/km entre estaciones que difieren 100 m, sin umbral de ruido.

**Gravedad baja:** sin presión no se detecta frente de racha; el índice ICC con solo CAPE da 1,0; la documentación dice n_eff/(n_eff+8) (`:2916`) y el código usa 5 (`:3591`); a los rayos se les asigna la hora del fichero, no la de cada flash (`:1404`).

**Lo que las pruebas no cubren:** `cycle()` completo; los canales de rayos, mar, viento y escorrentía; `sea_model_check`, `corrected_outlook` y la forense de oleaje; `foehn_diag` y la ventisca del Pirineo; datos caducados o vacíos fuera de radar y pluviómetros; sensibilidad de umbrales; cualquier verificación contra lo observado.

**Gobernanza** (`:2153-2590`). Garantiza trazabilidad de cada nivel, que nunca se baje por debajo del aviso oficial y que bajar desde `alert` o `alarm` exija un pluviómetro. No garantiza calibración, independencia real entre canales que comparten fenómeno pero no raíz, ni integridad criptográfica: el SHA de las predicciones detecta reescrituras del propio código, no la manipulación de `state.json`.

### 1.5 Programa de verificación propuesto

**Almacén.** Dos JSONL solo-añadir, escritos por el cron de Actions que ya existe, en una rama de datos o repositorio aparte:

- `forecasts-AAAA-MM.jsonl`: congelado al emitir (sha, `issued_at`, run, antelación, fracción o miembros).
- `obs-AAAA-MM.jsonl`: añadido después.

Se unen solo al evaluar. Se puede rellenar el pasado con los «previous runs» de Open-Meteo que el motor ya consulta (`portinatx_degen.py:3588`). La memoria forense debería pasar de 14 días a al menos dos años.

**Evitar fugas.** Congelar umbrales y plan de análisis antes de cada temporada; evaluar con origen rodante (aprendido hasta t−1, puntuado en t); remuestrear por episodio, no por estación; excluir de cualquier test la DANA del 18–19/10, porque ya se usó para ajustar.

**Métricas.** Brier con descomposición y BSS frente a climatología para excedencias; CRPS e histograma de rangos para cantidades; POD/FAR/CSI, sesgo de frecuencia y SEDI para sucesos raros; intervalos por bootstrap de días; FSS para la verificación espacial.

**Referencias a batir.** Persistencia (predicción a 60 min), climatología mensual (Brier), modelo bruto y media simple (factor y pesos), pesos iguales (familias) y el aviso AEMET (eje de precaución).

**Tamaños realistas** [I, a confirmar con `cmd_climo`, `portinatx_degen.py:4566`]:

| Dominio | Suceso | Frecuencia estimada |
|---|---|---|
| Ibiza | ≥10 mm/día | 12–15 días/año |
| Ibiza | ≥30 mm/día | 3–4 días/año |
| Ibiza | ≥100 mm/12 h | menos de 1 por lustro |
| Pirineo, ~2000 m | ≥5 cm/día | 20–30 días/temporada |
| Pirineo, ~2000 m | ≥30 cm/día | 2–4 días/temporada |

Los umbrales bajos (1–10 mm, 5–10 cm) son calibrables en uno o dos años. Las DANA y las grandes nevadas no lo son: deben tratarse como estudios de caso y decirlo así.

---

## 2. Los usos

### 2.1 A quién sirve hoy

Las personas son hipótesis: no hay analítica ni entrevistas, y el único usuario evidenciado es el propietario-operador.

| Persona | Qué quiere resolver | Qué le sirve ya |
|---|---|---|
| Propietario junto a un torrente (caso de origen) | ¿Subo cosas, muevo el coche, vuelvo antes? | Tres ejes, radar, pluviómetros, condiciones de salida; push ntfy solo en local |
| Patrón o dueño de barca | ¿Refuerzo amarras? ¿Qué mar entra en la bocana? | Boyas PORTUS, oleaje de 7 modelos, radar HF, batimetría |
| Segunda residencia en el Pirineo | ¿Nieva a la cota de casa o de la carretera? | Cotas a 72 h, avisos oficiales, enlaces a carreteras, 15 días |
| Esquiador o montañero | ¿A qué cota nieva, hay föhn o inversión? | Relieve, corte vertical, föhn, inversión, enlaces a boletines de aludes |
| Aficionado | Entender el episodio y qué modelo acierta | Sondeo, hodógrafa, ensembles, predicciones falsables, forense |

El aficionado y el operador están sobreservidos (unas 60 secciones en Portinatx). El resto necesita una respuesta en diez segundos y hoy tiene que buscarla entre gráficos.

### 2.2 Usos apropiados y excluidos

**Apropiados:** contexto y anticipación a horas o días, preparación doméstica no urgente, planificación de viajes a montaña, aprendizaje y auditoría de modelos, segunda opinión siempre subordinada al aviso oficial.

**Excluidos de forma explícita:**

- Decisiones de emergencia (evacuar, cruzar un torrente): mandan AEMET, Protección Civil y el 112.
- Riesgo de aludes: el motor no lo calcula; solo enlaza boletines.
- Seguridad en navegación: la boya más próxima está a decenas de kilómetros.
- Cualquier «todo despejado», pista abierta o carretera transitable: `UNKNOWN` no es calma.

Los avisos de alcance ya existen, pero dispersos y en letra pequeña. Se propone una franja fija con el mismo texto en las tres páginas, la edad del dato grande junto a cada eje, la exclusión junto al dato en los bloques de mar y montaña, y lenguaje de precaución, nunca imperativo.

### 2.3 Brechas entre lo calculado y lo accionable

- **Cadencia:** el ciclo convectivo está pensado para unos 5 min; la web pública se renueva cada 6 h. Para el torrente es un informe de situación, no un nowcast.
- **Notificaciones:** ntfy existe en el motor costero, pero solo para quien ejecuta el servidor local. No hay nada en la web pública ni en el Pirineo.
- **Síntesis:** no hay pantalla «qué significa para mí hoy».
- **Idioma:** solo castellano, para un público balear, andorrano y francés (demanda no verificada).
- **Móvil y accesibilidad:** el HTML de Portinatx pesa unos 170 KB con decenas de gráficos; los niveles parecen depender del color; no hay pruebas de contraste ni de lector de pantalla.
- **Confianza:** el libro de predicciones es el gran diferenciador, pero en modo gratuito no persiste.
- **Documentación contradictoria** sobre el estado de despliegue (corregida en parte por el PR #5).

---

## 3. El potencial

### 3.1 Paisaje y hueco

| Actor | Qué hace que el proyecto no | Qué deja abierto |
|---|---|---|
| AEMET, Meteocat, Météo-France, servicio andorrano | Autoridad legal, redes propias, predictores humanos | Avisan por zonas, no por cala o cota |
| Open-Meteo | Modelos y ensembles normalizados por API | No interpreta, no fusiona avisos, no verifica |
| Windy, Meteoblue, yr.no | Escala y apps pulidas | No separan aviso oficial de juicio propio ni auditan sus aciertos locales (no verificado) |
| Nowcasting radar ([pysteps](https://pysteps.readthedocs.io/)) | Extrapolación probabilística 0–6 h | Requiere radar en bruto y dependencias pesadas |
| Modelos de IA global ([AIFS](https://www.ecmwf.int/en/forecasts/datasets/aifs-machine-learning-data), [GraphCast/GenCast](https://developers.google.com/weathernext/guides/osmodel)) | Pronóstico global abierto | No resuelven convección anclada al relieve |

El forense del propio repositorio ilustra el límite: en la DANA del 17–20/10, IFS y AIFS previeron unas 0,35 veces la lluvia medida y AROME 0,65 veces (`docs/FORENSE-PUBLICO.md`; un único episodio).

**Nicho:** una capa de interpretación auditada por micro-dominio que diga qué afirma la autoridad, qué se observa, qué precaución añade el sistema y cuánto acertó antes. No se encontró equivalente abierto, aunque la ausencia no queda demostrada.

### 3.2 Tendencias que lo facilitan

- ECMWF abre su catálogo en tiempo real bajo CC BY 4.0 sin coste desde el 1-10-2025 ([ECMWF](https://www.ecmwf.int/node/29328)).
- Datos meteorológicos de alto valor de la UE (Reglamento 2023/138, aplicable desde junio de 2024) ([data.europa.eu](https://data.europa.eu/en/news-events/news/high-value-datasets-what-has-changed-and-what-will-come-next)).
- Datos públicos de Météo-France gratuitos desde el 1-1-2024 ([ministerio francés](https://www.ecologie.gouv.fr/ouverture-des-donnees-publiques-du-ministere-au-1er-janvier-2024-toutes-donnees-publiques-meteo)).
- Avisos CAP de AEMET con clave gratuita ([datos.gob.es](https://datos.gob.es/es/blog/los-conjuntos-de-datos-meteorologicos-de-alto-valor)); términos de MeteoAlarm no verificados.
- Cómputo gratuito suficiente para instantáneas, no para vigilancia. GitHub desactiva los workflows programados tras 60 días sin actividad en repositorios públicos ([GitHub Docs](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows)).

### 3.3 Diferenciación real

Es de método, no de datos: todo lo que usa es replicable por terceros.

1. Tres ejes separados (oficial, observado, precaución propia): la defensa principal frente a parecer un aviso alternativo.
2. Libro de verificación con cadena SHA-256 y puntuación por evento; hoy con muestra de un episodio.
3. `UNKNOWN` honesto: un dato ausente nunca se convierte en 0 mm.
4. Contexto de terreno: DEM, cotas de nieve, föhn, inversión, oleaje apareado en la forense.
5. Cero dependencias y un `.pyz` portable: fácil de replicar, pero limita el nowcasting radar serio.

### 3.4 Vectores de crecimiento, de más a menos realista

| # | Vector | Primer experimento barato | Riesgo principal |
|---|---|---|---|
| 1 | Colaboración en verificación de DANA | Publicar un conjunto mínimo reproducible del episodio de octubre y pedir revisión académica | Licencia de observaciones ciudadanas; n=1 |
| 2 | Uso educativo | Cuaderno con un caso de cota de nieve y el selftest | Que se lea como predicción oficial |
| 3 | Kit de replicación | Tercer dominio de prueba solo con configuración, midiendo llamadas por ciclo | Límite no comercial de <10 000 llamadas/día de Open-Meteo ([términos](https://open-meteo.com/en/terms)) |
| 4 | Vista para visitantes | Traducir solo etiquetas y descargo (EN/DE/FR/CA) | Responsabilidad legal: el turista lee «aviso» |
| 5 | Domótica | Sensor de solo lectura con frescura y eje, sin acciones | Automatizar sobre datos caducos o `UNKNOWN` |
| 6 | Observaciones ciudadanas | Formulario manual post-evento con 5 voluntarios | RGPD, calidad, carga del mantenedor |

**Transferibilidad** [V]: el decodificador PNG, las teselas, el DEM Terrarium, la arquitectura de canales y la física de perfil ya son genéricos. Están escritos a mano los identificadores `LEIB` y `B908X`, la tabla `station_km`, los sectores marinos, la costa y coordenadas del sitio en el JavaScript, y en el Pirineo `BOX`, `POIS`, `FOEHN_PAIRS` y `CORTE`. Un tercer dominio exige antes un objeto «Dominio» declarativo.

### 3.5 Riesgos para la idea

- **Dependencia de Open-Meteo:** punto único de fallo; su nivel gratuito excluye uso comercial.
- **Licencias heterogéneas:** AEMET preveía revisarlas; la XEMA de Meteocat figura como propiedad intelectual de Meteocat ([ficha](https://datos.gob.es/es/catalogo/a09002970-datos-meteorologicos-de-la-xema)); Andorra no verificado.
- **Responsabilidad:** el marco legal español sobre avisos no oficiales no está verificado; conviene consulta jurídica antes de cualquier vista para visitantes.
- **Estado efímero:** el libro forense no tiene almacén duradero gratuito.
- **Un solo mantenedor** con conocimiento local tácito.
- **Validez estadística:** hasta acumular eventos independientes, el libro demuestra disciplina, no pericia.

---

## 4. Hoja de ruta integrada

Ordenada por valor frente a esfuerzo. Cada punto lleva la prueba que demostraría que funciona.

**Ahora (días)**

1. **Cobertura por fenómeno y frescura uniforme** (H1, H2): exigir al menos una fuente viva de la familia «lluvia» y tratar como no disponible lo caducado, vacío o duplicado. Es el único hallazgo que contradice la regla central del proyecto. *Prueba:* con solo viento y mar vivos, `insufficient=True` y lluvia `UNKNOWN`; casos parametrizados por canal (radar de 6 h, boya de 5 h, modelo vacío, METAR viejo).
2. **Archivo persistente de pares pronóstico–observación** en una rama de datos escrita por Actions. Condición previa de todo lo demás. *Prueba:* tras una semana, cada ciclo publicado tiene su línea congelada y verificable por hash.
3. **Saneamiento de etiquetas y comparaciones:** «fracción de miembros» en lugar de «P(…)», vecindad real en km, `sea_model_check` emparejado o reetiquetado, perfil norte/sur por zona en el Pirineo. *Prueba:* test que falle si una cadena de evidencia contiene «P(» sin calibración declarada.
4. **Franja común de alcance y edad del dato visible** en las tres páginas. *Prueba:* ninguna vista muestra un nivel sin su antigüedad.

**Siguiente (semanas)**

5. **Referencias e intervalos** en forense y predicciones (persistencia, climatología, modelo bruto), con n contado en días. *Prueba:* el panel forense muestra BSS y su intervalo.
6. **Advección de radar** por correlación cruzada entre los frames que ya se guardan: vector de movimiento y hora de llegada. *Prueba:* reproducción de episodios archivados con error de hora de llegada medido frente a persistencia.
7. **Test de origen rodante de la forense:** mostrar el «consenso aprendido» solo si bate a la media bruta fuera de muestra. *Prueba:* test unitario con serie sintética donde el factor aprendido debe perder.
8. **Tarjeta «resumen en 10 segundos»** sobre los tres ejes. *Prueba:* 3–5 personas dicen el nivel oficial y la edad del dato en menos de 15 s.

**Más adelante (condicionado a datos o demanda)**

9. Cota de nieve por zona con anclaje observado y corrección por intensidad.
10. Verificación espacial por FSS para fijar radios con datos.
11. Ciclos reproducibles (H3): guardar entradas en bruto con hash, inyectar el reloj y versionar `CFG`. *Prueba:* `replay(cycle_id)` produce un snapshot idéntico byte a byte.
12. `alarm` siempre con confirmación independiente (M1) y una relación Z–R explícita para el umbral (M2). *Prueba:* rayos ≥50 sin lluvia → `alert`; 42 dBZ → no `alert`.
13. Física de montaña robusta (M6, M7): capa cálida o lago frío, Tw a la presión real, fase condicionada a precipitación, umbral de ruido en la inversión.
14. Cuenca D8 con lluvia areal de radar para sustituir el proxy B908X.
15. Objeto «Dominio» declarativo antes de cualquier tercer observatorio.
16. Calibración de fracciones solo en umbrales con ≥30 sucesos.

**No-objetivos:** ser un servicio de avisos; índice de aludes, parte de pistas o recomendación de salida al mar; SLA o vigilancia cada 5 min en la web pública; cuentas de usuario o infraestructura de pago; presentar valores como probabilidades calibradas; ampliar territorios con un solo mantenedor.

---

## 5. Contraste del Reality Checker

Siguiendo la postura del perfil (por defecto «NEEDS WORK», evidencia antes que aprobación), se recomprobaron directamente en el código las afirmaciones con más peso en las conclusiones:

| Afirmación | Resultado |
|---|---|
| H1: sin canales de lluvia, `fuse` da `quiet` sin cobertura insuficiente | **Confirmada** con canales sintéticos: `quiet False 2/6` |
| La vecindad rotulada «±17 km» llega a 27–30 km | **Confirmada**: desplazamientos de hasta 0,35° de longitud (`:218-219`) |
| Las cadenas de evidencia rotulan «P(24h≥50)» sobre fracciones de miembros | **Confirmada** (`:1855`, `:1867`) |
| `sea_model_check` compara el máximo modelizado a 72 h con la última lectura de boya, con otro sector | **Confirmada** (`:2253-2267` frente a `:224-225`) |
| Los umbrales se declaran no calibrados | **Confirmada** (`:2248`) |
| La memoria forense se poda a `FORENSIC["days"]` | **Confirmada** (`:3639`) |
| No hay código que escriba `replay/cases.jsonl` | **Confirmada**: solo hay lectura (`pirineo.py:858`) |
| Las predicciones de cese solo se emiten cuando el motor baja | **Confirmada** (`:2376`) |
| Red de pluviómetros al sur del sitio | **No reproducida**; queda como inferencia |
| Tamaños muestrales climatológicos | **No comprobables** sin datos; quedan como inferencia |
| Licencias de MeteoAlarm, Andorra y redes ciudadanas | **No verificadas** |

Veredicto: **NEEDS WORK** como sistema predictivo, por H1 y por la ausencia de verificación; **aceptable** como herramienta diagnóstica personal y referencia metodológica, siempre subordinada a los avisos oficiales.
