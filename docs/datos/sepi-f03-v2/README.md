# Tablas de SEPI F03 v2

Generadas por `scripts/sepi/phase03_v2.py` (protocolo en `docs/SEPI-PROTOCOLO.md`) a partir de datos de **Météo-France**: S2M CSV «Données de Modèle de Simulation Nivologique» y observación diaria QUOT de los departamentos 66 y 09, publicados bajo **Licence Ouverte / Open Licence 2.0**. Descarga del 27-11-2026, con datos hasta el 26-11-2026. Son tablas derivadas de una línea de investigación experimental: no son datos oficiales ni avisos.

| Fichero | Contenido |
|---|---|
| `season_metrics_v2.csv` | Métricas estacionales por macizo, cota, geometría e invierno |
| `rankings_v2.csv` | Índice I, puesto, excepcional, extremo, deficitario, `prob_excepcional` y `n_variantes_excepcional` (variante principal) |
| `ranking_delta.csv` | Puesto en v1 frente a v2 y en cada variante, con la causa del cambio |
| `exceptional_winters_delta.csv` | Entradas y salidas de la categoría excepcional, con su causa |
| `ranking_uncertainty.csv` | Bootstrap por bloques: I_p05/p50/p95 y probabilidad de ser excepcional (incertidumbre muestral del umbral) |
| `sensitivity_analysis.csv` | Todas las variantes (réplica v1, efectos individuales, principal y sensibilidades) |
| `validation_classes_v2.csv` | Clases A/B/C por macizo e invierno según el protocolo, §5 |
| `coverage_v2.csv` | Cobertura por serie e invierno (≥90 % y hueco ≤7 días) |
| `resumen_v2.txt` | Resumen textual de la ejecución |

Reproducción: `SEPI_DATA=<carpeta fuera del repo> python scripts/sepi/fetch_hist.py && python scripts/sepi/phase03.py && python scripts/sepi/phase03_v2.py`. Hay que ejecutar `phase03.py` primero, porque genera `out_f03_ranking.csv`, necesario para la comparativa.
