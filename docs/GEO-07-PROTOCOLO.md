# GEO-07: interacción de frentes y tormentas con el relieve. Protocolo científico (v0.1)

**Estado: BORRADOR, no congelado.**
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
| Radar | 07f, 07g y 07h | Meteocat o Météo-France | **UNKNOWN** (acceso al archivo y licencia por verificar) |
| Rayos | 07f y 07h | Por determinar | **UNKNOWN** (licencia y archivo) |

**Sin radar ni rayos con archivo verificable, 07f y 07g quedan en UNKNOWN.** No se sustituyen por la salida de un modelo.

## 4. Física inicial (modelo reducido)
- **Número de Froude de la barrera:** Fr = U⊥ / (N · h_eff).
  - **U⊥:** componente del viento **normal a la barrera**, promediada en la capa entre la base de barlovento y la cota de la cresta. La orientación de la barrera sale del sector de procedencia de GEO-01.
  - **h_eff:** altura de la barrera **sobre la base de barlovento**, a partir de `barrera_m` de GEO-01 para el sector de procedencia. No es la altitud de la cima.
  - **N:** N² = (g/θ̄)·Δθ/Δz en la misma capa. Si la capa está saturada (HR ≥ 90 % en los niveles que la limitan), se usa la N húmeda (N_m), y se informa de cuál se ha usado.
- **Regímenes (hipótesis que hay que calibrar):** bloqueo si Fr < 0,5; transición si 0,5 ≤ Fr < 1,5; paso por encima si Fr ≥ 1,5. Los umbrales se ajustan **solo** con episodios de entrenamiento y se congelan antes de la prueba.
- **Guardas explícitas, que devuelven UNKNOWN o «no aplicable», nunca 0:**
  - **Inestabilidad:** N² ≤ 0 o capa inestable → «Fr no aplicable (inestable)».
  - **Niveles bajo el terreno:** se descartan. Si quedan menos de 2 niveles en la capa → UNKNOWN.
  - **Viento mal definido:** |U⊥| < 2 m/s o dispersión de dirección > 45° en la capa → «flujo mal definido».
  - **Humedad ausente:** realce, sombra y föhn quedan en UNKNOWN; el régimen sí puede calcularse.
- **Realce y sombra:** el modelo lineal de Smith y Barstad ya existente vale solo con Fr alto. Con bloqueo, el realce se desplaza a barlovento. La forma exacta de esa degradación se fija con los episodios de entrenamiento.
- **Föhn:** sotavento con régimen de paso por encima o de transición, humedad a barlovento y descenso en sotavento. Se evalúan el del norte (Puymorens → Cerdanya; Envalira → Andorra) y el del sur, el «vent du sud» del Ariège (Cerdanya → Ax/Foix).

## 5. Pares y puntos de verificación (provisional; se congela con el protocolo)
| Fenómeno | Barlovento | Sotavento o punto |
|---|---|---|
| Föhn del norte | Porté-Puymorens | Puigcerdà / Bourg-Madame |
| Föhn del norte | Pas de la Casa | Encamp |
| Föhn del sur | Puigcerdà / Font-Romeu | Ax-les-Thermes / Foix |
| Realce y sombra con N/NO | Vertiente norte (L'Hospitalet, Porté) | Cerdanya (Puigcerdà, Das) |
| Realce con E/SE | Canigó, Vallespir y Núria | Ariège |
| Canalización | Col de Puymorens, Envalira | Fondo del Segre |

Las estaciones concretas dependen del inventario de cobertura horaria. Una estación sin cobertura suficiente queda en UNKNOWN y nunca se rellena.

## 6. Selección de episodios (sin sesgo hacia lo espectacular)
1. **Periodo y fuente fijados antes de mirar resultados:** reanálisis o archivo del motor en un periodo cerrado. Cada día se clasifica de forma objetiva por régimen a 700 hPa: N/NO, O, SO, S, E/SE, débil anticiclónico y convectivo estival (CAPE > umbral fijado).
2. **Muestra estratificada:** el mismo número de días por régimen, con la semilla fijada, **incluyendo días sin fenómeno** (sin precipitación, sin föhn y sin convección). Así la habilidad incluye las falsas alarmas.
3. **División cronológica:** los primeros 2/3 sirven para entrenar y calibrar umbrales; el último tercio, para la prueba, que se abre una sola vez.
4. **Episodios conocidos** (DANA de octubre de 2026, nevada de 2025–26): se pueden usar como casos ilustrativos, pero **no cuentan para la habilidad** si se eligieron por su resultado.

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
- estado: OK, UNKNOWN, «no aplicable» o «flujo mal definido»;
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
| 07-0 | Inventario de datos (radar, rayos, cobertura horaria de estaciones, archivo del motor) | Ninguna |
| 07-1 | Núcleo físico (Fr, N, U⊥, guardas) con pruebas sintéticas | Ninguna |
| 07-2 | Selección de episodios y congelación del protocolo | Inventario 07-0 y decisiones del §12 |
| 07-3 | Calibración con los episodios de entrenamiento | Protocolo congelado |
| 07-4 | Prueba única y verificación independiente | 07-3 |
| 07-5 | Integración en la UI y en el explorador GEO-06 | PASS en algún submódulo |

## 12. Decisiones pendientes del titular (antes de congelar)
1. Periodo y fuente para clasificar los días: ERA5 (necesita el CDS) o archivo del motor (no duradero).
2. Número de días por régimen y semilla.
3. Fuentes de radar y rayos, y su licencia (07-0).
4. Lista definitiva de pares de estaciones (§5), tras el inventario.
5. Umbral de CAPE para el régimen convectivo estival.

## 13. Registro de decisiones
| Fecha | Decisión | Tipo |
|---|---|---|
| 28-11-2026 | Borrador v0.1 a partir del encargo del titular: submódulos 07a–h, variables, Fr = U⊥/(N·h_eff) con guardas y casos de validación por régimen | Borrador |
