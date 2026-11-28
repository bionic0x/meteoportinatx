# SEPI F03 v2: 58 inviernos con el protocolo congelado (28-11-2026)

**Estado:** reanálisis metodológico según [`SEPI-PROTOCOLO.md`](SEPI-PROTOCOLO.md) §4. No sustituye a la v1 exploratoria (PR #66, sección «Fase 03» de [`SEPI.md`](SEPI.md)), que se conserva intacta; la comparación está en [`SEPI-FASE03-COMPARATIVA.md`](SEPI-FASE03-COMPARATIVA.md). Es investigación experimental, no un aviso ni un pronóstico. **Que el cálculo sea reproducible no valida S2M frente a la realidad observada.**

Script: `scripts/sepi/phase03_v2.py`. Tablas en `docs/datos/sepi-f03-v2/`. Derivan de datos de Météo-France (S2M y QUOT, Licence Ouverte 2.0) y están descritas en el README de esa carpeta.

## Método (decisiones congeladas)
- **Inviernos:** 58, de 1968–69 a 2025–26, del 1 de diciembre al 30 de abril, identificados por el año de inicio. Son 8.772 días por serie.
- **Cobertura:** todas las series S2M superan el criterio (≥90 % de días y ningún hueco de más de 7 días). Las anclas se filtran con el mismo criterio (`coverage_v2.csv`).
- **Estratos:**
  - macizos 69 (control), 70 Haute-Ariège, 71 Andorra, 72 Orlu, 73 Capcir–Puymorens y 74 Cerdagne–Canigou;
  - 1.800 y 2.100 m;
  - llano, N 20° y NO 20°, por separado.

  En total, 36 estratos.
- **Métricas:** HS medio, HS máximo, días ≥30 cm y días ≥100 cm. También se guardan el SWE, la fecha del máximo y la duración de la cubierta continua.
- **Índice:** I es la mediana de los percentiles de rango medio de las cuatro métricas respecto a la referencia.
  - **Excepcional:** I > P90 de I (cuantil lineal, tipo 7).
  - **Extremo:** I > P95.
  - **Deficitario:** I < P10.
- **Métricas degeneradas:** se conservan. La métrica d100 tiene P90 = 0 a 1.800 m en Andorra, Capcir y Cerdagne. Su exclusión se trata como sensibilidad aparte.
- **Sensibilidades:**
  - sin métricas degeneradas;
  - referencia 1991–2020 (inviernos 1990–91 a 2019–20);
  - sin tendencia lineal.
- **Incertidumbre muestral del umbral:** bootstrap circular por bloques de 5 inviernos, con 2.000 réplicas. Se remuestrea la distribución de referencia y se recalcula para cada invierno su I y si queda por encima del P90 remuestreado. Así se obtiene `prob_excepcional`. **Esto no mide el error físico de S2M.**
- **Estabilidad metodológica:** `n_variantes_excepcional` cuenta cuántas de las cuatro variantes v2 lo clasifican como excepcional: la principal, la que excluye las métricas degeneradas, la de referencia 1991–2020 y la que quita la tendencia.
- **Clases de validación (§5 del protocolo):** **A** exige dos controles independientes confirmados, y hoy no hay ninguno porque la asimilación de SAFRAN es UNKNOWN. **B** indica al menos un ancla directa concordante en tercil, con independencia desconocida. **C** significa que el resultado es esencialmente del modelo; se marca aparte si las anclas discrepan.

## Resultados
- **Excepcionales:** entre 5 y 6 por estrato (media 5,9), como cabe esperar de un P90 sobre 58 inviernos.
- **2025–26 en Cerdagne–Canigou: es el resultado más robusto.** Ocupa el puesto 1 de 58 en los 6 estratos (dos cotas × tres geometrías) y queda por encima del P90 en el 100 % de las réplicas bootstrap y en las 4 variantes. Clase B, con dos anclas concordantes de independencia desconocida, ambas nivosas de cresta.
- **2025–26 en Capcir–Puymorens:** excepcional en 5 de 6 estratos, con `prob_excepcional` entre 0,76 y 1,00. La excepción es N 20° a 1.800 m (puesto 7, probabilidad 0,44). Clase B.
- **2025–26 en Orlu:** excepcional solo en llano a 1.800 m.
- **2025–26 en Andorra y Haute-Ariège:** no es excepcional en ningún estrato. En Haute-Ariège queda entre los puestos 25 y 39.
- **Excepcionales en llano a 1.800 m, dominios 70–74:**

| Dominio | Inviernos excepcionales |
|---|---|
| Haute-Ariège | 1980–81, 2004–05, 2013–14, 2012–13, 1993–94, 1970–71 |
| Andorra | 1995–96, 2013–14, 1970–71, 1973–74, 2017–18, 1971–72 |
| Orlu | 1971–72, 1980–81, 2004–05, 2025–26, 1977–78, 2012–13 |
| Capcir | 2025–26, 1985–86, 1980–81, 1971–72, 1973–74, 1970–71 |
| Cerdagne | 2025–26, 1991–92, 1995–96, 2005–06, 2019–20, 2017–18 |

- **Candidatos históricos** (dominios 70–74, 1.800 m; número de dominios en que son excepcionales en llano / N 20° / NO 20°):

| Invierno | Llano | N 20° | NO 20° |
|---|---|---|---|
| 1971–72 | 3 | 2 | 3 |
| 1985–86 | 1 | 1 | 1 |
| 1995–96 | 2 | 2 | 2 |
| **2003–04** | **0** | **0** | **0** |
| 2012–13 | 2 | 4 | 4 |
| 2013–14 | 2 | 2 | 3 |
| 2017–18 | 2 | 2 | 1 |
| 2025–26 | 3 | 1 | 2 |

  **2003–04 no es excepcional en ningún estrato:** es un falso positivo de la lista de candidatos.
- **Estabilidad frente a las decisiones:**
  - Excluir las métricas degeneradas cambia el 0,4 % de las clasificaciones (3 entran y 5 salen).
  - La referencia 1991–2020 cambia el 3,2 % (35 entran y 31 salen).
  - Quitar la tendencia cambia el 4,4 % (45 entran y 46 salen).
  - Los inviernos limítrofes con P90 son los más sensibles.
- **Clases** (dominios 70–74):

| Tramo | B | C |
|---|---|---|
| 1968–84 | 18 | 62 |
| 1985–2002 | 49 | 41 |
| 2003–2026 | 54 | 66 |

  No hay ninguna clase A.

## Límites y pendiente
- **S2M es un modelo.** No tiene macizos en la vertiente catalana: la Cerdanya catalana, Núria y Cadí no están representadas.
- **Independencia de las anclas: UNKNOWN.** Las nivosas y las estaciones de Météo-France pueden estar asimiladas por SAFRAN. Por eso la clase B no equivale a una confirmación independiente.
- **Ruptura de 2002: pendiente.** No es posible contrastarla con CERRA-Land sin la cuenta del CDS del titular. La sensibilidad a la referencia 1991–2020 y a la tendencia no sustituye esa prueba.
- **Concordancia de las anclas:** se mide por tercil del HS medio en la cota de cada ancla (no del índice I) y en terreno llano. La asignación de cada ancla a su macizo sigue siendo UNKNOWN sin los contornos oficiales.
- **Sin agregado regional:** no se ha calculado, de acuerdo con el protocolo.
- **El bootstrap mide solo la incertidumbre del umbral climatológico.** El error físico de S2M queda sin cuantificar.
