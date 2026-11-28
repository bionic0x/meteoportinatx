# GEO-07: interacción de frentes y tormentas con el relieve. Protocolo científico (v0.2)

**Estado: BORRADOR v0.2, no congelado.** La selección definitiva de episodios (07-2d) y cualquier calibración con episodios reales quedan **bloqueadas** hasta la congelación (07-2c).
- **Congelación:** la hace el titular, al fusionar el PR que lo congele, **antes de seleccionar los episodios de prueba y antes de calcular ninguna habilidad**. Desde entonces, los cambios van al registro (§13) con fecha y motivo.
- **Alcance:** es un protocolo de investigación. No modifica el motor operacional ni emite avisos. No sustituye a AEMET, Meteocat, Météo-France ni al SMA.

Relación con otros documentos:
- [`SEPI-GEO-01.md`](SEPI-GEO-01.md): relieve y exposición en 16 sectores.
- [`SEPI-GEO-06.md`](SEPI-GEO-06.md): explorador.
- [`PIRINEO-OROGRAFIA-CUBETA-CARRETERAS.md`](PIRINEO-OROGRAFIA-CUBETA-CARRETERAS.md): diagnósticos actuales del motor, con Smith y Barstad y el föhn del norte.

## 1. Pregunta y no-objeto
**Pregunta.** ¿Mejora una física reducida del flujo y el relieve el diagnóstico de lo que ocurre en el Pirineo oriental, frente a referencias sencillas y frente a los diagnósticos actuales del motor? Lo que ocurre es:
- dónde llueve o nieva más o menos;
- dónde se bloquea, se canaliza o desciende el aire;
- dónde se inician y hacia dónde se mueven las células convectivas.

**No-objeto:**
- Ninguna simulación de fluidos (CFD) en esta fase.
- Ninguna predicción operativa ni aviso.
- Las animaciones de escenarios no se presentan como previsión (§10).

## 2. Submódulos
| ID | Fenómeno | Salida diagnóstica | Firma observable para verificar |
|---|---|---|---|
| GEO-07a | Zonas frontales | Máscara frontal por gradiente de θe a 850 hPa y su desplazamiento | Giro del viento, salto de θe y presión en estaciones; paso por pares de estaciones |
| GEO-07b | Bloqueo o desbordamiento | Régimen por sector: bloqueo, transición o paso por encima (Fr, §4) | Represamiento a barlovento (subida de presión, giro del viento paralelo a la barrera) y diferencia de precipitación entre vertientes |
| GEO-07c | Realce y sombra | Factor de realce del modelo lineal ya existente, degradado cuando hay bloqueo | Cociente de precipitación barlovento/sotavento en pares de estaciones |
| GEO-07d | Canalización | Aceleración y giro esperados en valles y collados (ejes de valle, TPI, orientación) | Viento y racha en estaciones de collado y de valle (Puymorens, Envalira, Segre) |
| GEO-07e | Föhn | Probabilidad diagnóstica de descenso compresivo, del norte **y del sur** | En sotavento: subida de T y de θ, bajada de HR y racha (pares de §5) |
| GEO-07f | Disparo convectivo | Zonas preferentes de iniciación por hora (crestas con TPI > 0, insolación, convergencia de brisas, CAPE/CIN) | Primer eco de radar o primer rayo |
| GEO-07g | Desplazamiento de células | Probabilidad de cruzar o detenerse en una divisoria, según el viento de dirección y las barreras | Trayectoria de radar |
| GEO-07h | Verificación forense | Ficha por episodio con predicción frente a observación | — |

## 3. Variables de entrada
| Variable | Uso | Fuente prevista | Disponibilidad |
|---|---|---|---|
| U y V en 925, 850, 700 y 500 hPa | Flujo incidente | Perfiles por punto del motor (Open-Meteo) y ERA5 | Motor: OBSERVADO en tiempo real; histórico sin archivo duradero. ERA5: necesita la clave del CDS |
| T, θ y θe por niveles | Estabilidad y frentes | Ídem | Ídem |
| Humedad específica e IVT | Transporte de humedad | ERA5 | Necesita el CDS |
| Velocidad vertical | Ascenso | ERA5 | Necesita el CDS |
| CAPE / CIN | Potencial convectivo | Modelos por punto | OBSERVADO en el motor |
| N (Brunt–Väisälä) | Estratificación | Derivada del perfil (§4) | — |
| DEM, barreras por sector y TPI | Interacción con el relieve | GEO-01 (GLO-30) | OBSERVADO |
| Estaciones | Verificación | Météo-France (MTO/QUOT), XEMA y SMA | Parcial; hay conectores en el repositorio |
| Radar | 07f, 07g y 07h | Archivo verificable de Meteocat, AEMET o Météo-France (Coméphore para la lámina en Francia) | **UNKNOWN** (acceso al archivo y licencia por verificar) |
| Rayos | 07f y 07h | MTG-LI (desde julio de 2024) y otras redes con licencia y cobertura verificadas | Archivo corto; licencia por verificar |

**Sin radar ni rayos con archivo verificable, 07f y 07g quedan en UNKNOWN.** No se sustituyen por la salida de un modelo.

## 4. Física inicial (modelo reducido)
Implementación de referencia: `scripts/geo07_core.py`, con pruebas sintéticas en `tests/test_geo07_core.py` (#83).
- **Número de Froude de la barrera:** Fr = Ū⊥ / (N · h).
  - **Normal de la barrera:** la normal **geométrica** de la cresta, n̂, que apunta hacia barlovento. Se calcula a partir de dos puntos de la línea de cumbres (`crest_normal`). El sector de procedencia de GEO-01 solo sirve para elegir el tramo de cresta, no como orientación.
  - **Ū⊥ = U·n̂, promediada por espesor:** Ū⊥ = (1/(z₂ − z₁)) ∫ U⊥(z) dz, integrada por trapecios. Los niveles de presión están espaciados de forma irregular, así que no se usa la media aritmética. Los niveles válidos deben cubrir al menos el 50 % de h (valor sin calibrar).
  - **h:** altura de la cresta sobre la base de barlovento (`barrera_m` de GEO-01), no la altitud de la cima.
  - **N seca:** N² = (g/θ̄)·Δθ/Δz.
  - **N saturada:** Durran y Klemp (1982, ec. 36), con la hipótesis declarada qw = qs (sin condensado conocido). Sustituye a la aproximación por θe de la v0.1.
  - **Saturación de la capa:** HR ≥ 90 % en todos sus niveles, en ninguno o solo en algunos. Si es parcial, el Fr principal es el seco y el húmedo se informa como cota.
  - **N principal y sensibilidad:** la principal se calcula entre los extremos de la capa. Como sensibilidad se informan N² por subcapas, la seca frente a la húmeda y la lista de subcapas inestables. Una subcapa inestable dentro de una capa estable en bloque se declara explícitamente y no se oculta.
- **Regímenes (hipótesis sin calibrar):** bloqueo si Fr < 0,5; transición si 0,5 ≤ Fr < 1,5; paso por encima si Fr ≥ 1,5. Se ajustan **solo** con los episodios de entrenamiento, después de congelar, y se fijan antes de la prueba.
- **Guardas explícitas.** Devuelven un estado y nunca 0:
  - **Valor no físico:** NaN, ±∞, p ≤ 0, HR fuera de 0–100 % o T fuera de −100…+60 °C invalidan todo el cálculo y dan UNKNOWN. No se descartan en silencio.
  - **Niveles bajo el terreno:** se descartan. Si quedan menos de 2 niveles, o cubren menos del 50 % de h, el resultado es UNKNOWN.
  - **Inestabilidad:** N² principal ≤ 0 da «no aplicable (inestable)».
  - **Dirección del viento:** si el arco mínimo que contiene las direcciones de **todos** los niveles supera 45°, el estado es «flujo mal definido».
  - **Flujo no incidente:** Ū⊥ < 2 m/s, incluido el flujo paralelo o desde sotavento, da «flujo no incidente».
  - **Humedad ausente:** la saturación y la N húmeda quedan en UNKNOWN. El estado es PARCIAL: solo se da Fr seco y no se asigna régimen. Realce, sombra y föhn también quedan en UNKNOWN.
- **Realce y sombra:** el modelo lineal de Smith y Barstad ya existente solo vale con Fr alto. Con bloqueo, el realce se desplaza a barlovento. La forma de esa degradación se fija con los episodios de entrenamiento.
- **Föhn:** se evalúan el del norte (Puymorens → Cerdanya; Envalira → Andorra) y el del sur, el «vent du sud» del Ariège (Cerdanya → Ax/Foix). La firma Δθ/ΔHR de `foehn_signature` **reproduce la regla del motor (R1)**: sirve de referencia, no de validación observacional independiente. La verificación usa las variables observadas del §5, no la propia regla.

## 5. Pares y puntos de verificación (provisional; la lista definitiva sale de la auditoría 07-2a)
| Fenómeno | Barlovento | Sotavento o punto |
|---|---|---|
| Föhn del norte | Porté-Puymorens | Puigcerdà / Bourg-Madame |
| Föhn del norte | Pas de la Casa | Encamp |
| Föhn del sur | Puigcerdà / Font-Romeu | Ax-les-Thermes / Foix |
| Realce y sombra con N/NO | Vertiente norte (L'Hospitalet, Porté) | Cerdanya (Puigcerdà, Das) |
| Realce con E/SE | Canigó, Vallespir y Núria | Ariège |
| Canalización | Col de Puymorens, Envalira | Fondo del Segre |

Las estaciones concretas se fijan con una **auditoría objetiva** de cobertura horaria (07-2a), no por los resultados. Criterio propuesto, pendiente de congelar: completitud horaria de T, HR y viento ≥ 80 % en cada estación del par, durante al menos el 75 % de los meses del periodo. Una estación sin cobertura suficiente queda en UNKNOWN y nunca se rellena.

## 6. Universo, muestra y división (sin sesgo hacia lo espectacular)
1. **Universo de días elegibles (07-2a, permitido antes de congelar).** Son elegibles los días del periodo candidato con datos suficientes en el clasificador sinóptico y en las estaciones de al menos un par. Construir el universo **no** implica mirar las salidas del núcleo ni la firma observada en esos días.
2. **Clasificación de régimen.** Fuente principal: **ERA5**. Cada día se clasifica a 700 hPa como N/NO, O, SO, S, E/SE, débil anticiclónico o convectivo estival. El régimen convectivo usa CAPE ≥ **500 J/kg**, con sensibilidad secundaria a 250 y 1.000 J/kg. **CERRA** sirve para contrastar el método de clasificación y su sensibilidad espacial; no es una observación independiente.
3. **Periodo.** Candidato: **2015–2025**, condicionado a la cobertura que mida 07-2a. El periodo definitivo se fija al congelar.
4. **Episodios.** Un episodio es una serie máxima de días consecutivos con el mismo régimen. Todos sus días comparten identificador. La división, el muestreo por bloques y el bootstrap trabajan con episodios completos. Un temporal de cuatro días nunca queda partido entre entrenamiento y prueba.
5. **División cronológica por episodios.** El primer 2/3 del periodo se dedica a entrenamiento y el último 1/3 a prueba. El corte se coloca en una frontera de episodio y se deja un **embargo de 3 días**, que se descartan, para cortar la autocorrelación (propuesta). La prueba se abre una sola vez.
6. **Dos evaluaciones complementarias:**
   - **Balanceada:** muestra estratificada con el mismo número de días por régimen. Objetivo de diseño: **90 días por régimen**, repartidos en 60 de entrenamiento y 30 de prueba. Semilla **20261128**. Incluye días sin fenómeno. Compara el comportamiento en cada régimen, pero altera la frecuencia natural, así que **no** sirve para calibrar probabilidades ni para dar métricas agregadas.
   - **Representativa:** todos los días elegibles del periodo de prueba, con su frecuencia natural. Se usa para la calibración, las falsas alarmas y la habilidad operacional.
   Si un régimen no llega al objetivo, se usan todos sus días y el déficit se declara. No se rellena con días de otro periodo.
7. **Episodios conocidos** (DANA de octubre de 2026, nevadas de 2025–26): sirven como demostraciones y estudios de caso, pero **no entran en la evaluación de habilidad**.
8. **Archivo del motor (R1):** sin archivo histórico duradero, R1 se valida **de forma prospectiva** desde que exista el almacenamiento.

## 7. Referencias que GEO-07 tiene que superar
| Referencia | Descripción |
|---|---|
| R0 | Climatología de la firma por régimen (frecuencia en el entrenamiento) |
| R1 | Diagnósticos actuales del motor: Smith y Barstad sin bloqueo y regla de föhn del norte de `pirineo.py` |
| R2 | Salida directa del modelo numérico en el punto (precipitación, racha, T y HR) |

## 8. Métricas y criterio de aceptación
| Submódulo | Métrica principal | Secundarias |
|---|---|---|
| 07b, 07e (sí/no) | Brier Skill Score frente a R0 y R1 | ROC-AUC, fiabilidad, POD/FAR |
| 07c (cociente) | CRPSS del cociente log(barlovento/sotavento) frente a R1 | Sesgo, Spearman |
| 07d (viento) | MAE vectorial frente a R2 | Sesgo de dirección |
| 07f (iniciación) | Fraction Skill Score por escala (5, 10 y 20 km) frente a R0 | Distancia al primer eco |
| 07g (desplazamiento) | Error de posición a +30 y +60 min frente a la extrapolación lineal de radar | Brier de «cruza la divisoria» |

- **Contraste:** diferencias pareadas por episodio, con bootstrap por bloques de episodios consecutivos y Holm por submódulo.
- **Estados:** PASS, REJECT y UNKNOWN, con los mismos criterios que SEPI-P (§7 de `SEPI-P-PROTOCOLO.md`). No superar el umbral no es REJECT.

## 9. Contrato de salida (para la UI futura)
Cada diagnóstico es una serie temporal georreferenciada con:
- procedencia: modelo, ejecución, hora válida y versión de GEO-07;
- estado: OK, PARCIAL, UNKNOWN, «no aplicable (inestable)», «flujo mal definido» o «flujo no incidente», con su motivo;
- incertidumbre, cuando la haya;
- la etiqueta **«diagnóstico experimental»**.

Nada de esto se publica en las consolas sin un PR de integración aparte, con evidencia de PASS.

## 10. Tipos de animación (no deben confundirse)
| Tipo | Datos | Naturaleza |
|---|---|---|
| Reproducción | Radar o satélite archivados | Observación |
| Reproducción de previsión | Campos en horas válidas sucesivas | Modelo |
| Partículas | Viento interpolado | Representación visual, no trayectoria |
| Escenarios GEO-07 | Diagnósticos o casos sintéticos | Experimental |

## 11. Fases
| Fase | Contenido | Condición |
|---|---|---|
| 07-0 | Inventario de datos (`GEO-07-INVENTARIO-DATOS.md`) | Ninguna |
| 07-1 | Núcleo físico con guardas y pruebas sintéticas | Ninguna |
| 07-2a | Auditoría de cobertura y universo de días elegibles | Permitida antes de congelar; sin mirar salidas ni firmas |
| 07-2b | Definición de la muestra, las reglas y los criterios estadísticos (este documento) | Permitida antes de congelar |
| 07-2c | **Congelación formal del protocolo** | Obligatoria; la hace el titular |
| 07-2d | Selección reproducible de episodios y separación entrenamiento/prueba | **Solo después de 07-2c** |
| 07-3 | Calibración con los episodios de entrenamiento | 07-2d |
| 07-4 | Prueba única y verificación independiente | 07-3 |
| 07-5 | Integración en la UI y en el explorador GEO-06 | PASS en algún submódulo |

**Viabilidad actual por submódulo (orden de investigación):**
- **Primer bloque:** 07e (föhn), 07c (realce y sombra) y 07d (canalización). Se pueden verificar con estaciones, más pluviómetros y Coméphore para 07c.
- **07b (bloqueo):** el núcleo existe; la validación está pendiente.
- **07a (zonas frontales):** limitado mientras no haya campos históricos (CDS).
- **07f (disparo convectivo):** limitado por el archivo de radar y de rayos.
- **07g (desplazamiento de células):** UNKNOWN sin un archivo de radar adecuado.
- **07h (forense):** depende de la persistencia y de las observaciones archivadas.

## 12. Decisiones del titular
| Parámetro | Decisión (28-11-2026) | Estado |
|---|---|---|
| Clasificación sinóptica | ERA5 como referencia principal | Propuesta; requiere la clave CDS |
| CERRA | Contraste del método y de la sensibilidad espacial, no observación independiente | Propuesta |
| Archivo del motor | Validación prospectiva | Propuesta |
| Periodo | 2015–2025, condicionado a la cobertura | **Abierto hasta 07-2a** |
| Semilla | 20261128 | Propuesta |
| Muestra balanceada | 90 días por régimen (60 de entrenamiento y 30 de prueba) | **Objetivo de diseño; abierto hasta 07-2a** |
| División | Primer 2/3 de entrenamiento y último 1/3 de prueba, por episodios, con embargo de 3 días | Propuesta (el embargo es nuevo en la v0.2) |
| CAPE convectivo | 500 J/kg; sensibilidad secundaria a 250 y 1.000 J/kg | Propuesta |
| Radar | Archivo verificable de Meteocat, AEMET o Météo-France | Propuesta |
| Rayos | MTG-LI y otras redes con licencia y cobertura verificadas | Propuesta |
| Pares de estaciones | Tras la auditoría objetiva (criterio del §5) | **Abierto hasta 07-2a** |

Todo se confirma o se corrige en el PR de congelación (07-2c). Hasta entonces no se seleccionan episodios definitivos ni se calibran umbrales con datos reales.

## 13. Registro de decisiones
| Fecha | Decisión | Tipo |
|---|---|---|
| 28-11-2026 | Borrador v0.1 a partir del encargo del titular: submódulos 07a–h, variables, Fr = U⊥/(N·h_eff) con guardas y casos de validación por régimen | Borrador |
| 28-11-2026 | v0.2: fases 07-2a–d; decisiones del titular sobre ERA5, CERRA, semilla, muestra, división y CAPE; evaluación balanceada y representativa; división por episodios con embargo; normal geométrica, Ū⊥ por espesor, N saturada de Durran y Klemp y guardas de validación física | Borrador |
