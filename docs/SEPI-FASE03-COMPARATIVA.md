# SEPI F03: comparativa entre la v1 exploratoria y la v2 con protocolo (28-11-2026)

**Estado:** comparación de sensibilidad metodológica. La v1 (PR #66, commit de fusión `cc73bb1`) se conserva sin cambios. La divergencia entre las dos versiones es en sí misma un resultado sobre la robustez del índice SEPI. Método de la v2 en [`SEPI-FASE03-V2.md`](SEPI-FASE03-V2.md) y protocolo en [`SEPI-PROTOCOLO.md`](SEPI-PROTOCOLO.md).

Tablas en `docs/datos/sepi-f03-v2/`:
- `ranking_delta.csv`: puesto en la v1 y en cada variante, con su causa.
- `exceptional_winters_delta.csv`: entradas y salidas de la categoría «excepcional», con su causa.
- `sensitivity_analysis.csv`: todas las variantes.

## Cómo se aíslan los efectos

Las decisiones nuevas se aplican primero una a una y después juntas, sobre los estratos que comparten las dos versiones: 6 macizos × 1.800 y 2.100 m × llano y N 20°, es decir, 1.392 filas de estrato e invierno.

| Variante | Regla de «excepcional» | Métricas degeneradas | Para qué sirve |
|---|---|---|---|
| V0, réplica de la v1 | Todas las métricas usadas ≥ P90 | Excluidas | Comprobar que el código v2 reproduce la v1 |
| V1, solo la regla | I > P90 de I | Excluidas | Efecto de la regla |
| V2, solo las degeneradas | Todas ≥ P90 | Conservadas | Efecto de conservar d100 |
| V3, principal | I > P90 de I | Conservadas | Las dos decisiones juntas |

- **La etiqueta del invierno** (año de inicio frente a año final) no cambia ningún cálculo; solo renombra.
- **La cobertura** (≥90 % y hueco ≤7 días) no cambia nada en S2M, porque todas sus series están completas. Solo afecta a las anclas.
- **La geometría NO 20°** es nueva en la v2 y no tiene equivalente en la v1.

**La réplica V0 reproduce la v1 al 100 %** en la clasificación «excepcional» y en el puesto, salvo en 28 filas. En esas 28 filas, dos inviernos tienen exactamente el mismo índice: la v1 los desempataba por un error de redondeo en coma flotante, mientras que la v2 los trata como empate. Nunca afecta a la categoría excepcional.

## Cambios de puesto

| Causa | Filas | \|Δ puesto\| medio | Máximo |
|---|---|---|---|
| Sin cambio | 1.191 | 0 | 0 |
| Conservar d100 en el índice | 173 | 1,9 | 7 |
| Empate exacto, que la v1 desempataba por redondeo | 28 | 1 | 1 |

- **Dónde se concentran:** solo en los estratos donde d100 es degenerada, a 1.800 m en Andorra, Capcir y Cerdagne y en Andorra a 2.100 m en llano. Al conservar una métrica casi siempre a 0, el índice comprime las diferencias en la mitad baja del ranking y mueve algo los puestos intermedios.
- **Mayores desplazamientos:**
  - Capcir 1.800 m, 2024–25: del puesto 47 al 54.
  - Cerdagne 1.800 m, 1971–72: del 4 al 9.
  - Andorra 1.800 m, 1980–81: del 6 al 11.
- **Primeros puestos:** no cambian. En Cerdagne y Capcir a 1.800 m, 2025–26 sigue en el puesto 1 en las dos versiones.

## Cambios en la categoría «excepcional»
- **Salidas:** ninguna. Los 44 casos excepcionales de la v1 lo siguen siendo en la v2.
- **Entradas:** 98 casos nuevos. 94 se deben solo a la regla, porque «I > P90 de I» es mucho menos estricta que «todas las métricas ≥ P90». Los otros 4 resultan de la regla y de conservar d100 a la vez: Cerdagne 1.800 m en llano en 2005–06, 2017–18 y 2019–20, y Andorra 1.800 m en llano en 1971–72.
- **Lectura:** con la regla de la v1 había entre 0 y 4 excepcionales por estrato. Con la v2 hay entre 5 y 6, lo esperable para un P90 de 58 inviernos.
  - La v1 identificaba inviernos **extremos en todas las métricas a la vez**.
  - La v2 identifica el **decil superior del índice compuesto**.
  
  No son contradictorias: la v1 es un subconjunto estricto de la v2.

## Sensibilidades de la v2 (los 36 estratos, incluido NO 20°)

| Sensibilidad frente a la principal | Coincidencia | Entran | Salen |
|---|---|---|---|
| Sin métricas degeneradas | 99,6 % | 3 | 5 |
| Referencia 1991–2020 | 96,8 % | 35 | 31 |
| Sin tendencia lineal | 95,6 % | 45 | 46 |

- Los cambios se concentran en inviernos cerca del P90. Ninguna sensibilidad mueve los puestos más altos de cada estrato.
- La referencia 1991–2020 y la versión sin tendencia redistribuyen excepcionalidad entre décadas. Es coherente con una tendencia negativa de la nieve en S2M, pero **no distingue una tendencia climática de un cambio del sistema**, como la ruptura de forzamiento de 2002, que sigue pendiente.

## Qué se mantiene y qué cambia en las conclusiones
- **Se mantiene, y sale reforzado:** 2025–26 en Cerdagne–Canigou es el resultado más robusto. Ocupa el puesto 1 en los 6 estratos de las dos versiones, con `prob_excepcional` = 1,00 y 4 de 4 variantes. Sigue en clase B, porque sus anclas tienen independencia desconocida.
- **Se mantiene:** no hay un número 1 regional. El orden depende del dominio, la cota y la geometría.
- **Cambia:** con la regla del protocolo, la categoría «excepcional» es más amplia. Inviernos como 2012–13 (4 de 5 dominios en N 20° y NO 20° a 1.800 m), 1993–94, 1970–71 y 2019–20 pasan a ser excepcionales en algún estrato.
- **Nuevo:** 2003–04, candidato histórico, no es excepcional en ningún estrato de ninguna versión.
- **Clases de validación:** la v2 no tiene clases A, cuando la v1 llegó a tener alguna. Se debe a que el protocolo exige independencia confirmada.

## Límites de la comparativa
- **El alcance es de cálculo y de metodología.** La comparativa no informa sobre si S2M acierta frente a las observaciones.
- **NO 20°** no se puede comparar con la v1.
- **Los efectos individuales y conjuntos** se miden solo para las dos decisiones que cambian la clasificación: la regla y las métricas degeneradas. La referencia y la tendencia son sensibilidades exclusivas de la v2.
