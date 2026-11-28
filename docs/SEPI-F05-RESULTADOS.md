# SEPI F05: persistencia, análogos y predictibilidad bimestral (28-11-2026)

**Estado: resultados SIN VERIFICAR.**
- **Ejecución:** autorizada por el titular el 28-11-2026, con el protocolo congelado en `1ae92c1` y las concreciones de implementación de [`SEPI-F05-CONCRECIONES.md`](SEPI-F05-CONCRECIONES.md), publicadas en el commit `5ba70de` **antes** de la primera ejecución.
- **Aceptación:** ninguna conclusión se da por aceptada hasta la verificación independiente (a partir del 2-12-2026).
- **Resultados negativos:** se publican todos.
- **Cambios tras ver resultados:** ninguno en hiperparámetros, objetivos ni criterios.

**No es una previsión ni un aviso.** Mide si el estado del manto en S2M al empezar cada periodo habría servido para anticipar ese periodo, en los inviernos 1991–92 a 2025–26.

Tablas en [`datos/sepi-f05/`](datos/sepi-f05/README.md).

## Diseño (resumen)
- **Modelos:**
  - M0: climatología;
  - M0b: climatología con tendencia;
  - M0c-R: estado inicial SWE₀, con regresión y residuos;
  - M0d-R: análogos por SWE₀ y HS₀, con k ∈ {3, 5, 7} y ponderación elegidos dentro del pliegue;
  - M0d-R+, secundario: los mismos análogos más el balance de SWE de los 30 días anteriores.
- **Modelos operacionales:** M0c-O y M0d-O siguen en UNKNOWN.
- **Validación:** origen móvil (entrenamiento desde 1968–69), con 35 inviernos de prueba.
- **Contraste:** CRPS pareado con bootstrap circular por bloques (B = 2.000, semilla 20261128) y Holm sobre 6 dominios por periodo.
- **Hipótesis primarias:** H-P1, H-P2 y H-P3, cada una M0c-R frente a M0 en ΔSWE a 2.100 m en llano.

## Hipótesis primarias (2.100 m en llano, ΔSWE, M0c-R frente a M0)

| Periodo | Dominio | CRPSS | IC 90 % | p | p Holm (6) | Estable 2002 | G/L | Estado |
|---|---|---|---|---|---|---|---|---|
| P1 nov–dic | Couserans | +0,01 | −0,02 … +0,04 | 0,28 | 1,00 | no | no | REJECT |
| | Haute-Ariège | +0,01 | −0,02 … +0,05 | 0,28 | 1,00 | no | no | REJECT |
| | Andorra | −0,04 | −0,10 … +0,01 | 0,86 | 1,00 | no | no | REJECT |
| | Orlu | +0,01 | −0,01 … +0,02 | 0,33 | 1,00 | no | no | REJECT |
| | Capcir | +0,01 | −0,02 … +0,03 | 0,25 | 1,00 | no | no | REJECT |
| | Cerdagne | −0,00 | −0,02 … +0,01 | 0,73 | 1,00 | no | no | REJECT |
| P2 ene–feb | Couserans | −0,04 | −0,10 … +0,01 | 0,88 | 1,00 | sí | no | REJECT |
| | Haute-Ariège | −0,05 | −0,10 … −0,02 | 0,99 | 1,00 | sí | no | REJECT |
| | Andorra | −0,00 | −0,01 … −0,00 | 0,95 | 1,00 | sí | sí | REJECT |
| | Orlu | −0,01 | −0,04 … +0,01 | 0,82 | 1,00 | no | no | REJECT |
| | Capcir | −0,01 | −0,02 … −0,00 | 0,92 | 1,00 | sí | no | REJECT |
| | Cerdagne | +0,00 | −0,04 … +0,06 | 0,46 | 1,00 | no | no | UNKNOWN |
| P3 mar–abr | Couserans | −0,01 | −0,03 … +0,01 | 0,80 | 1,00 | sí | no | REJECT |
| | Haute-Ariège | −0,03 | −0,07 … +0,00 | 0,93 | 1,00 | sí | no | REJECT |
| | **Andorra** | **+0,36** | +0,25 … +0,42 | 0,001 | 0,003 | sí | sí | **PASS-R** |
| | Orlu | −0,02 | −0,03 … −0,00 | 0,96 | 1,00 | sí | no | REJECT |
| | **Capcir** | **+0,26** | +0,18 … +0,32 | 0,001 | 0,003 | sí | sí | **PASS-R** |
| | Cerdagne | +0,14 | +0,01 … +0,24 | 0,031 | 0,124 | sí | sí | UNKNOWN |

Con Holm sobre las 18 pruebas, como se exige para afirmaciones sobre la temporada completa, Andorra P3 y Capcir P3 siguen por debajo de 0,05 (p = 0,009 ambos), y Cerdagne P3 no (p = 0,50).

## Respuesta a las tres preguntas (OBSERVADO en S2M; sin verificar)

**1. Noviembre–diciembre: ¿el estado inicial informa sobre la formación del manto?**
No. Es REJECT en los 6 dominios, como se declaró de antemano: el 1 de noviembre casi nunca hay manto. Para la fecha de formación y los días ≥ 30 cm, ningún modelo supera a la climatología de forma clara (CRPSS entre −0,21 y +0,04).

**2. Enero–febrero: ¿el estado antecedente anticipa el balance nival?**
No en el balance. ΔSWE da REJECT en 5 dominios y UNKNOWN en Cerdagne, y tampoco hay habilidad en las ganancias, G_SWE.
**Sí en la conservación**, como análisis secundario: el estado al 31-dic anticipa los **días con HS ≥ 30 cm** de enero–febrero:
- M0c-R: CRPSS de +0,18 a +0,40, con p < 0,05 en 5 de 6 dominios. Cerdagne alcanza +0,40.
- d100 a 2.100 m: CRPSS de +0,18 a +0,33, con p < 0,05 en Couserans, Haute-Ariège y Orlu.

Es persistencia del manto existente, no previsión de nevadas.

**3. Marzo–abril: ¿hay predictibilidad sobre acumulación, pérdidas y conservación?**
- **Pérdidas y balance: sí, en Andorra y Capcir (PASS-R).** En Cerdagne hay señal, pero sin pasar Holm (UNKNOWN).
- **Acumulación (G_SWE): no**, en ningún dominio ni con ningún modelo.
- **Conservación (días ≥ 30 cm): sí**, con CRPSS de +0,12 a +0,37 en 5 dominios.

**Lectura obligatoria del PASS-R.** La componente que cumple el criterio 3 es **L_SWE** (pérdidas), con CRPSS de +0,23 en Andorra, +0,27 en Capcir y +0,27 en Cerdagne. **G_SWE no tiene habilidad.** Es justo el caso que el protocolo advierte (§7, §8): un manto mayor a 1 de marzo pierde más nieve en marzo–abril, por pura aritmética del balance.
- **Qué significa el PASS-R:** habilidad para anticipar **cuánta nieve puede perderse y cuánta se conserva**.
- **Qué no significa:** capacidad de anticipar la meteorología de primavera.

Las matrices de transición lo muestran sin modelo. Con terciles por origen móvil, un P2 en el tercil alto va seguido de un P3 en el tercil bajo en 13 de 13 inviernos en Capcir, 12 de 13 en Andorra y 8 de 9 en Cerdagne.

**Por qué solo los macizos orientales y meridionales.** En Couserans, Haute-Ariège y Orlu, a 2.100 m, el manto de marzo suele seguir acumulando, así que el estado inicial no determina el balance. Andorra, Capcir y Cerdagne, más secos y más soleados, están más cerca del régimen de fusión. SUPUESTO físico, pendiente de verificar.

## Otros resultados (secundarios, descriptivos)
- **Análogos (M0d-R y M0d-R+):** casi siempre **peores** que M0c-R y que la climatología en ΔSWE en P1 y P2 (hasta −0,33). Solo se acercan a M0c-R en P3 y en los días con umbral. Con 23–57 inviernos de entrenamiento, los k vecinos dan distribuciones demasiado estrechas. La configuración más elegida fue k = 7 uniforme (48 %).
- **La climatología con tendencia (M0b) supera claramente a M0 en el ΔSWE de P3, en los 6 dominios** (CRPSS de +0,24 a +0,39, con p < 0,05). **Esta habilidad se concentra después de 2002:** D̄ antes y después de 2002 es 1–8 frente a 51–52 en Haute-Ariège y Couserans. Coincide con la ruptura del forzamiento de SAFRAN en 2002, y **no puede separarse de una tendencia climática real** con estos datos. Hace falta la prueba con CERRA-Land.
- **M0c-R está sesgado en P3:** su media pronostica, en media, entre 50 y 176 mm más de ΔSWE del observado en los 6 dominios, es decir, menos pérdida de la que hubo. Es coherente con primaveras recientes que pierden más nieve que el pasado de entrenamiento. Una combinación de estado inicial y tendencia no está en el protocolo y sería un análisis nuevo, que habría que registrar antes de probarlo.
- **Coherencia física:** en P3, un 14–29 % del peso de los miembros de ΔSWE se truncó en −SWE₀, según el modelo (`log.csv`). La degeneración por pliegue solo afectó a d100: 35 pliegues de P2 y 12 de P3, todos en Andorra.

## Qué permite y qué no para el invierno 2026–27
- **Los resultados son retrospectivos (R).** Para aprovechar la señal de P3 en Andorra y Capcir hace falta un estado del manto disponible el 1 de marzo: S2M en tiempo real (UNKNOWN), NIVOSE o ERA5-Land. Hay que auditarlo antes (M0c-O sigue en UNKNOWN).
- **Para noviembre–diciembre y enero–febrero no hay habilidad demostrada** con el estado inicial: la referencia sigue siendo la climatología de F04.

## Límites
- **Sin verificación independiente.**
- **Todo descansa en S2M:** objetivo y predictor salen del mismo modelo, que tiene la ruptura de 2002.
- **Una sola fuente y ninguna observación independiente.**
- **El día de formación censurado** se codifica como 62 (concreción C3).

## Reproducción
```bash
export SEPI_DATA=$HOME/sepi-data
python scripts/sepi/phase04_climatology.py
python scripts/sepi/phase05_persistence.py      # requiere el protocolo congelado; ~1 min
python scripts/sepi/phase04_transitions.py      # matrices; ahora se ejecuta dentro de phase05
```
