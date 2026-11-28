# Tablas de SEPI F05: persistencia y análogos (SIN VERIFICAR)

Generadas por `scripts/sepi/phase05_persistence.py` con el protocolo congelado en `1ae92c1` y las concreciones de `docs/SEPI-F05-CONCRECIONES.md`, a partir de S2M de **Météo-France** (Licence Ouverte 2.0). Es un resultado retrospectivo experimental: no es una previsión ni un aviso. Interpretación en `docs/SEPI-F05-RESULTADOS.md`.

| Fichero | Contenido |
|---|---|
| `primary_hypotheses.csv` | H-P1 a H-P3: M0c-R frente a M0, ΔSWE, 2.100 m en llano. CRPSS, IC90, p, Holm por periodo y sobre 18, estabilidad en 2002, componentes G/L y estado |
| `skill.csv` | Cada modelo frente a M0, por dominio, estrato, periodo y objetivo: CRPSS, IC90, p, MSSS, RPSS, MAE, sesgo, Spearman y D̄ antes y después de 2002 |
| `predictions.csv.gz` | Predicciones individuales fuera de muestra: media, P10, P50, P90, número de miembros, CRPS, RPS, fracción truncada y configuración de los análogos |
| `transition_matrix.csv` | Terciles de ΔSWE P1→P2 y P2→P3, con límites por origen móvil, en los inviernos de prueba |
| `log.csv.gz` | Exclusiones, degeneraciones por pliegue, configuraciones elegidas y truncados |
| `emisiones_manifest.json` | SHA-256 de las 105 instantáneas de emisión, por inicialización e invierno. Los JSON (60 MB) quedan en `SEPI_DATA/f05/emisiones/` |

Unidades: SWE en kg/m² (= mm); días; formación en días desde el 1-nov (62 = censurado).
