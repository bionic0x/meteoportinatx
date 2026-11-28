# Tablas de SEPI F04: climatologías bimestrales (descriptivas)

Generadas por `scripts/sepi/phase04_climatology.py` según `docs/SEPI-P-PROTOCOLO.md` v0.4, §2–§3, con datos S2M de **Météo-France** (Licence Ouverte / Open Licence 2.0). Proceden de una línea de investigación experimental: no son datos oficiales, ni avisos, ni previsiones.

**Alcance:** distribuciones marginales de cada periodo **por separado**. No hay relaciones entre periodos (transiciones, correlaciones o regresiones del estado inicial) ni ninguna habilidad; quedan bloqueadas hasta congelar el protocolo (§9).

- **Periodos:** P1 noviembre–diciembre, P2 enero–febrero y P3 marzo–abril.
- **Inviernos:** 1968–69 a 2025–26, identificados por el año de inicio.
- **Macizos:** 69 a 74.
- **Estratos:** 2.100 m en llano (primario); 1.800 m en llano, N 20° y NO 20° (secundarios).
- **Unidades:** SWE en kg/m² (= mm); HS en cm; `formation_day` en días desde el 1 de noviembre (1 = 1 de noviembre).

| Fichero | Contenido |
|---|---|
| `bimonthly_metrics.csv` | Por macizo, estrato, invierno y periodo: SWE₀, ΔSWE, G_SWE, L_SWE, G_HS, d30, d100 (solo 2.100 m llano en P2 y P3), SWE y HS al cierre, y fecha de formación del manto según el criterio SEPI (solo P1; «censurado» = no alcanzada antes del 31-dic) |
| `bimonthly_coverage.csv` | Días observados y requisitos de cobertura por variable (§3) |
| `bimonthly_climatology.csv` | n, desconocidos, media, desviación, mínimo, máximo y fracción de ceros; para la formación, la fracción censurada |
| `bimonthly_percentiles.csv` | P10, P25, P33, P50, P67, P75 y P90. Tipo 7 lineal; para la fecha de formación, tipo 1 con censura |
| `degenerate_variables.csv` | P90 de las variables no negativas y marca de degenerada (P90 = 0) sobre el conjunto completo. Es descriptivo: en el PR 3 se evalúa por pliegue |
| `manifest.json` | SHA-256 de la entrada y del protocolo, commit, métodos, unidades y alcance |

**Límites:**
- **G y L son aproximaciones del balance diario,** no nevada ni fusión.
- **S2M es un modelo,** con la ruptura de su forzamiento en 2002.
- **La climatología usa los 58 inviernos completos.** En el backtesting (PR 3) se recalcula solo con el entrenamiento de cada pliegue.

Reproducción: `SEPI_DATA=<carpeta fuera del repo> python scripts/sepi/fetch_hist.py && python scripts/sepi/phase04_climatology.py`
