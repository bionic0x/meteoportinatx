# SEPI F04: climatologías bimestrales del Pirineo oriental (descriptivas, 28-11-2026)

**Estado:** PR 2 del protocolo SEPI-P v0.4 (`SEPI-P-PROTOCOLO.md`, §9).
- **Qué contiene:** caracterización descriptiva de los tres periodos del invierno, cada uno por separado.
- **Qué no contiene:** ninguna previsión, ninguna habilidad y ninguna relación entre periodos. Las matrices de transición están escritas y probadas con datos sintéticos, pero **no se han ejecutado sobre S2M**: `phase04_transitions.py` se niega a hacerlo mientras el protocolo no esté congelado.
- **Tablas:** [`datos/sepi-f04/`](datos/sepi-f04/README.md).

## Cobertura
Las series S2M de los 24 estratos (6 macizos × 4 estratos) están completas: ningún invierno ni periodo queda en UNKNOWN por falta de datos (`bimonthly_coverage.csv`). Se cumple ΔSWE = G − L con error 0 en todas las filas.

## Lectura descriptiva del estrato primario (2.100 m, llano)
**ΔSWE** (balance de agua equivalente del periodo, kg/m²), percentiles 10, 50 y 90 sobre los 58 inviernos:

| Dominio | P1 nov–dic | P2 ene–feb | P3 mar–abr |
|---|---|---|---|
| Couserans (control) | 43 · 157 · 284 | 103 · 209 · 445 | −265 · 71 · 277 |
| Haute-Ariège | 19 · 119 · 272 | 67 · 169 · 366 | −236 · −15 · 217 |
| Orlu–St-Barthélemy | 17 · 130 · 286 | 89 · 192 · 411 | −271 · −4 · 230 |
| Andorra | 6 · 43 · 118 | 18 · 69 · 156 | −214 · −89 · 53 |
| Capcir–Puymorens | 1 · 51 · 145 | 17 · 78 · 199 | −245 · −86 · 50 |
| Cerdagne–Canigou | 0 · 51 · 193 | −4 · 76 · 241 | −279 · −72 · 65 |

**Formación del manto según el criterio SEPI** (7 días seguidos con HS ≥ 30 cm antes del 31-dic). Proporción de inviernos sin formación:

| Dominio | Sin formación |
|---|---|
| Couserans | 16 % |
| Haute-Ariège | 22 % |
| Orlu | 28 % |
| Cerdagne | 59 % |
| Capcir | 64 % |
| Andorra | 71 % |

**Lectura (OBSERVADO en S2M, descriptivo):**
- **Hay un gradiente oeste–este marcado.** Los macizos orientales y meridionales (Andorra, Capcir y Cerdagne) ganan menos de la mitad de SWE en P1 y P2 que los septentrionales u occidentales. En más de la mitad de los inviernos no forman manto a 2.100 m antes de fin de año, según este criterio.
- **En P3, el balance mediano es negativo** en todos los dominios salvo Couserans: la pérdida domina en marzo–abril.
- **La dispersión de P3 es grande** (P10 de −214 a −279 y P90 de 50 a 277). P3 es el periodo con más variabilidad interanual.

Estas cifras describen la distribución de cada periodo y **no dicen nada sobre si un periodo anticipa el siguiente**: eso es la hipótesis del PR 3.

## Variables degeneradas (descriptivo)
- **d100** solo se calcula a 2.100 m en llano, en P2 y P3, y es degenerado (P90 = 0) en Andorra.
- **La regla P90 = 0 se aplica solo a variables no negativas.** En ΔSWE, que tiene signo, un P90 = 0 no indica falta de varianza. Es una concreción de redacción del §3 que hay que anotar en el registro del protocolo.

## Límites
- **Los 58 inviernos son la referencia descriptiva.** En el backtesting se recalcula todo solo con el entrenamiento de cada pliegue.
- **S2M es un modelo,** con la ruptura de 2002. **G y L** son aproximaciones del balance diario.
- **Verificación independiente:** pendiente, a partir del 2-12-2026.
