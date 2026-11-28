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
- **Primeros puestos:** no cambian. 2025–26 es el puesto 1 en los 4 estratos compartidos de Cerdagne y en Capcir a 1.800 m en llano, en las dos versiones. En Capcir a 1.800 m en N 20° es el 7.º en ambas.

## Cambios en la categoría «excepcional»
- **Salidas:** ninguna. Los 44 casos excepcionales de la v1 lo siguen siendo en la v2.
- **Entradas:** 98 casos nuevos. 94 se deben solo a la regla, porque «I > P90 de I» es mucho menos estricta que «todas las métricas ≥ P90». Los otros 4 resultan de la regla y de conservar d100 a la vez: Cerdagne 1.800 m en llano en 2005–06, 2017–18 y 2019–20, y Andorra 1.800 m en llano en 1971–72.
- **Lectura:** con la regla de la v1 había entre 0 y 3 excepcionales por estrato compartido (44 en total). Con la v2 hay entre 5 y 6, lo esperable para un P90 de 58 inviernos.
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
- **Clases de validación:** la v1 asignaba clase A a 230 filas de estrato e invierno (92 a 1.800 y 2.100 m), entre ellas a 2025–26 en los 4 estratos de Cerdagne. La v2 no asigna ninguna A, porque el protocolo exige independencia confirmada de las anclas y esa independencia es UNKNOWN. **2025–26 en Cerdagne baja, por tanto, de A en la v1 a B en la v2.** Es un cambio de criterio, no de datos. Las clases tampoco son comparables uno a uno: la v1 tenía además la clase SA, sin ancla, que en la v2 pasa a C.

## Verificación independiente (parcial)
Un agente verificador escribió su propia implementación desde el protocolo, en `/home/claude/verif-f03v2/` fuera del repositorio, sin importar `phase03_v2.py`. Se quedó sin cuota antes de redactar su informe, así que se ejecutaron sus scripts tal como los dejó. Resultados (OBSERVADO):
- **Variante principal**, 2.088 filas de los 36 estratos: el índice I, el P90, el puesto y la marca «excepcional» son idénticos (diferencia máxima 0).
- **Sensibilidades**: ninguna discrepancia en la marca «excepcional». Las cifras de entradas, salidas y coincidencia reproducen las de la tabla anterior.
- **Réplica de la v1** frente a `out_f03_ranking.csv`: 0 discrepancias en la marca «excepcional», 0 en el conjunto de métricas y 28 en el puesto. Son los 28 empates ya documentados.
- **Bootstrap**, con otra semilla: diferencia máxima de `prob_excepcional` de 0,03, diferencia media de 0,0016 y ninguna fila por encima de 0,05. Es compatible con el ruido de Monte Carlo para B = 2.000.

Falta lo que el verificador no llegó a hacer:
- revisar el texto de los documentos frente a las tablas;
- revisar las clases de validación;
- emitir un veredicto formal.

Las tres correcciones de este documento posteriores a la primera versión salen de esa revisión parcial: el máximo de excepcionales en la v1, las clases A de la v1 y el puesto de Capcir en N 20°.

## Límites de la comparativa
- **El alcance es de cálculo y de metodología.** La comparativa no informa sobre si S2M acierta frente a las observaciones.
- **NO 20°** no se puede comparar con la v1.
- **El bootstrap remuestrea la referencia dentro de la propia muestra.** Cada invierno forma parte de su propia referencia en cerca del 64 % de las réplicas. Por eso `prob_excepcional` mide la estabilidad del umbral, no una probabilidad fuera de la muestra. El verificador también calculó la probabilidad solo con las réplicas en que el invierno falta de la referencia: es mayor o igual (Capcir N 20° 1.800 m, 0,56 frente a 0,44). La lectura no cambia.
- **Los efectos individuales y conjuntos** se miden solo para las dos decisiones que cambian la clasificación: la regla y las métricas degeneradas. La referencia y la tendencia son sensibilidades exclusivas de la v2.
