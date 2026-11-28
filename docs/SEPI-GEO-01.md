# SEPI-GEO-01: relieve Copernicus GLO-30 frente al sistema actual (diagnóstico, 28-11-2026)

**Estado:** diagnóstico autorizado por el titular el 28-11-2026.
- **No modifica** `src/pirineo_orografia.json`, el motor operativo ni el protocolo SEPI-P.
- **Sustituir los índices actuales** por los nuevos requiere otro PR, con evidencia de mejora frente a observaciones (GEO-03).
- **Verificación independiente:** pendiente, a partir del 2-12-2026.

Tablas en [`datos/sepi-geo01/`](datos/sepi-geo01/README.md). Los rásteres pesados quedan fuera del repositorio, en `SEPI_DATA/terrain/`.

## Datos y requisitos geoespaciales

| Parámetro | Valor |
|---|---|
| Fuente | Copernicus DEM GLO-30 y GLO-90 (modelo digital de **superficie**: incluye bosque y edificios), AWS Open Data |
| Teselas | 12 de 1° × 1° por producto (41–43° N, 1° O–2° E), con SHA-256 en sus manifiestos |
| Coordenadas de origen | EPSG:4326; alturas referidas a EGM2008 |
| Proyección de trabajo | EPSG:32631 (UTM 31N), con distancias en metros |
| Dominio | El del motor (42,15–43,05 N; 1,15–2,65 E) más un margen de 22 km, mayor que el radio máximo de 20 km |
| NODATA | NaN, nunca cero. Núcleo: 0 celdas sin dato y 0 celdas rellenadas con cero (OBSERVADO, `verify_report.json`) |
| MDT nacionales | Diferidos a GEO-02. Las diferencias entre referencias verticales no se dan por menores de 1 m hasta verificarlas |

## Variantes comparadas en los 129 puntos del motor

| Variante | Qué es |
|---|---|
| V0 | Motor actual: valores guardados (GLO-90 de la API de Open-Meteo, muestreado en nodos de 0,01°) |
| V0r | Réplica local de V0: GLO-90 muestreado en los mismos nodos, con el mismo algoritmo |
| V1k | GLO-90 **promediado** en celdas de 0,01°, con el mismo algoritmo |
| V3k | GLO-30 promediado en celdas de 0,01°, con el mismo algoritmo |
| V1 | GLO-90 nativo, 90 m |
| V2 | GLO-30 agregado a 90 m (bloques de 3×3) |
| V3 | GLO-30 nativo, 30 m |

V0r, V1k y V3k separan dos efectos que V0→V1 mezcla: el del **DEM** y el de la **definición a otra escala**.

## Resultados principales (OBSERVADO; los 129 puntos salvo que se indique)

### 1. La réplica reproduce el motor
Para el índice de cubeta (CPI), V0→V0r da un MAE de 0,18 y una correlación de rangos ρ = 0,992; para el TPI del motor, MAE de 20 m y ρ = 0,997. Las diferencias residuales salen del muestreo de la API frente al de la tesela local.

### 2. A la escala del motor (1 km), cambiar de DEM casi no cambia nada
- **CPI, V1k→V3k:** MAE 0,05; P95 0,17; ρ = 0,9996.
- **TPI, V1k→V3k:** MAE 2,5 m; ρ = 0,9999.
- **Muestrear frente a promediar** (V0r→V1k) mueve más que el DEM: CPI con MAE 0,26 y ρ = 0,992; TPI con MAE 29 m.

Conclusión: **pasar a GLO-30 no aporta nada si se mantiene la malla de 1 km.** El valor está en usar la resolución nativa.

### 3. La geometría local sí cambia con la resolución, y más que con el DEM
| Variable | V1→V2 (DEM, 90 m) | V2→V3 (resolución, mismo DEM) | V1→V3 (total) |
|---|---|---|---|
| Pendiente (MAE · P95, grados) | 1,8 · 6,6 | 3,3 · 10,8 | 3,2 · 8,7 |
| Orientación (MAE, grados) | 17 | 30 | 31 |
| TPI 250 m (MAE, m) | 5,7 | 6,7 | 6,9 |
| TPI 5 km (MAE, m) | 7,1 | 5,3 | 11,3 |
| Factor de vista del cielo (MAE) | — | — | 0,008 (ρ = 0,91) |

La pendiente y la orientación dependen de la escala. El TPI regional (≥ 1 km) es estable (ρ ≥ 0,996), y el factor de vista del cielo cambia poco.

### 4. El índice de cubeta no se traslada bien a resolución nativa
Con el CPI nativo de GEO-01 (P75 en 13 km sobre la malla de 1 km y área drenada máxima en 1 km), V0→V1 en los pueblos da ρ = 0,67, y V2→V3 da ρ = 0,80.
- **Hay casos inestables:**
  - Llívia: 4,8 en V0, 8,4 en V1, 0,0 en V3.
  - Puigcerdà: 2,9 en V0, ≈ 0 en V1 y V3.
  - Das, la referencia del motor: 2,9 en V0, 1,75 en V1, 3,99 en V3.
- **Por qué:** a 30–90 m, el área drenada depende de que el punto caiga o no cerca del cauce D8.
- **Consecuencia para el motor:** el motor escala ΔTmax por CPI/CPI(Das), así que estos cambios moverían directamente el diagnóstico de inversión. **No se propone sustituir el CPI.** Un CPI nativo necesita otra definición menos frágil (altura sobre el fondo del valle, profundidad de la depresión respecto al collado de salida y factor de vista del cielo) y validación térmica (GEO-03).

### 5. Altitudes de las cimas (44 cimas, frente a la cota de referencia del motor, que procede de GeoNames)
| DEM y método | Mediana (m) | MAE (m) | \|Δ\| > 50 m |
|---|---|---|---|
| GLO-30, bilineal | −28 | 45 | 12 |
| GLO-30, máximo en 90 m | −11 | 29 | 4 |
| GLO-30, máximo en 250 m | −9 | 21 | 4 |
| GLO-90, bilineal | −62 | 69 | 25 |
| GLO-90, máximo en 250 m | −25 | 33 | 6 |

- **Lectura:** GLO-30 rebaja menos las cimas. El hecho de que el máximo en 250 m se acerque a la referencia indica sobre todo errores de geolocalización de las coordenadas de GeoNames y suavizado del DEM. **No sustituye a la altitud del punto.**
- **Casos > 50 m con GLO-30 y máximo en 250 m:** Pic de Noufonts (−194 m), Tossa d'Alp (−90 m), Pic de la Mina (−76 m) y Pic d'Envalira (+68 m; nombre y cota ya marcados en el motor como «por verificar»). Lo más probable es que sean errores de coordenada o de cota de referencia (SUPUESTO).

### 6. Comprobaciones (`verify_terrain.py`)
- **Algoritmos:** Horn, TPI y D8 vectorizados coinciden con las referencias en Python puro (diferencia < 1e-6).
- **Teselas:** el SHA-256 coincide con los manifiestos.
- **Costuras de GLO-30:** salto mediano de 2,7–4,7 m en las juntas, frente a 2,9–4,4 m entre píxeles vecinos. La excepción es la junta de 1° E, con 7,4 m frente a 3,8 m. Está por debajo del umbral, pero hay que vigilarla.

## Exposición orográfica direccional (base del módulo GEO-07)
`exposure_by_sector.csv` da, para cada punto y para 16 sectores de procedencia del flujo (hasta 20 km a barlovento, en V1 y V3):
- la altura de la barrera;
- su distancia;
- el ángulo de abrigo;
- la pendiente de barlovento.

Es una descripción estática del relieve, **no una predicción**.

## GEO-07: módulo de interacción de frentes y tormentas con el relieve (diseño, por pedido del titular)
**Objetivo.** Anticipar cómo se modifica un frente o una tormenta al interactuar con el relieve:
- bloqueo o paso por encima;
- canalización por valles y collados;
- realce a barlovento y sombra a sotavento;
- disparo convectivo en crestas.

Aplica a cada punto del Pirineo oriental y para los flujos N, NO, O, S, SE y E.

**Diseño propuesto** (es una hipótesis hasta validarla):

| Componente | Entrada | Salida |
|---|---|---|
| Régimen de bloqueo | Viento y estabilidad del perfil (N, de la temperatura potencial entre 850 y 700 hPa) + altura de la barrera por sector (GEO-01) | Número de Froude Fr = U/(N·h): bloqueo o rodeo (Fr ≲ 1) frente a paso por encima (Fr ≳ 1); umbrales por calibrar |
| Realce y sombra | Modelo lineal de Smith y Barstad ya existente (válido con Fr alto) + exposición por sector | Factor de realce y su degradación cuando hay bloqueo |
| Canalización | Orientación de los ejes de valle y collados (TPI multiescala, orientación) | Aceleración y giro esperados (Segre, Puymorens, Envalira) |
| Föhn y sotavento | Exposición en la vertiente opuesta + humedad a barlovento | Probabilidad diagnóstica de descenso compresivo y desecación |
| Disparo convectivo | Crestas (TPI positivo), insolación (orientación, factor de vista), convergencia de brisas de valle | Zonas preferentes de iniciación por hora |
| Desplazamiento de células | Viento de dirección (700–500 hPa) + barreras | Probabilidad de que una célula cruce o se detenga en una divisoria |

**Validación necesaria antes de cualquier uso:** archivo de radar, rayos y estaciones (XEMA, Météo-France, SMA) en episodios pasados, con el mismo rigor que SEPI: protocolo fijado antes de mirar resultados, comparación con una referencia sencilla y publicación de los resultados negativos.

**Estado:** GEO-01 deja preparada la exposición por sector; el motor de GEO-07 **no está implementado**. Se propone como PR propio después de GEO-03.

## Hoja de ruta
| Fase | Alcance | Estado |
|---|---|---|
| GEO-00 | Descarga de GLO-30 y GLO-90 con manifiesto | Hecho |
| GEO-01 | Derivados y comparación V0–V3 | Este PR, en borrador |
| GEO-01b | Redefinición de la cubeta fría a escala nativa (altura sobre el fondo del valle, collado de salida, factor de vista del cielo) | Propuesto |
| GEO-02 | MDT nacionales (RGE ALTI, ICGC, Andorra) | Diferido |
| GEO-03 | Validación térmica con estaciones | Pendiente |
| GEO-04 | Corrección orográfica de temperatura y viento | Pendiente |
| GEO-05 | Innivación natural y artificial por estación | Pendiente |
| GEO-06 | Visualización 3D | Pendiente |
| GEO-07 | Interacción de frentes y tormentas con el relieve | Diseño (arriba) |

## Límites
- **GLO-30 es un modelo de superficie:** en zonas boscosas, la altura y las pendientes incluyen el dosel.
- **Las cotas y coordenadas de referencia** son las del motor (GeoNames), no oficiales. 17 de los 129 puntos no tienen cota.
- **Un cambio grande de un índice no demuestra que el nuevo sea mejor.** Eso lo decide GEO-03 con observaciones.
- **El CPI nativo es una definición de este PR,** no la del motor, y se ha mostrado inestable.

## Reproducción
```bash
export SEPI_DATA=$HOME/sepi-data     # fuera del repositorio
python scripts/fetch_dem_pirineo.py --download            # ~480 MB
python scripts/build_terrain_derivatives.py                # numpy, scipy, rasterio, numba; ~1 min
python scripts/compare_orografia.py
python scripts/verify_terrain.py
```
