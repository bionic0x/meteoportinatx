# SEPI F05: concreciones de implementación, fijadas ANTES de ejecutar (28-11-2026)

**Referencia:** protocolo `docs/SEPI-P-PROTOCOLO.md`, congelado en `1ae92c1`, con la anotación de estado en `f5eeb96`, que no cambia el método.

Este documento recoge solo lo que el protocolo deja abierto. **Se publica en un commit anterior a la primera ejecución sobre S2M**, para que conste que estas decisiones no se tomaron después de ver los resultados. Si se cambia algo después, se anota abajo con fecha y motivo, y se declara como posterior a la consulta.

Autorización de ejecución: titular, 28-11-2026, en el chat. Las conclusiones esperan a la verificación independiente.

| N.º | Aspecto | Concreción | Base en el protocolo |
|---|---|---|---|
| C1 | Estado inicial | P1: día 31-oct; P2: 31-dic; P3: último día de febrero. SWE₀ y HS₀ de S2M ese día, en el mismo estrato | §4 (inicialización inmediatamente anterior) |
| C2 | Objetivos evaluados | ΔSWE (primaria). Secundarias: G_SWE, L_SWE, G_HS, d30, d100 (solo 2.100 m llano, en P2 y P3) y día de formación (solo P1) | §3 |
| C3 | Día de formación | Ordinal desde el 1-nov (1–61). El censurado («> 31 dic») se codifica como 62 para el CRPS; es una aproximación declarada | §3 (censura) |
| C4 | M0 | Miembros = objetivos de los inviernos de entrenamiento, con pesos iguales | §5 |
| C5 | M0b | Recta MCO objetivo ~ año en el entrenamiento; miembros = ajuste en el año de prueba + residuos del entrenamiento | §5 |
| C6 | M0c-R | Recta MCO objetivo ~ SWE₀ en el entrenamiento; miembros = ajuste con el SWE₀ de prueba + residuos del entrenamiento. Si SWE₀ no tiene varianza en el entrenamiento, se vuelve a M0 | §5 |
| C7 | M0d-R | Predictores primarios: SWE₀ y HS₀. La variante con el balance de SWE en 30 días (SWE₀ − SWE del día −30) es análisis secundario, «M0d-R+» | §5 (prioridades) |
| C8 | Selección en M0d | 6 configuraciones (k ∈ {3, 5, 7} × ponderación uniforme o inversa). Origen móvil interno con los 15 primeros inviernos del pliegue como entrenamiento inicial; se elige el CRPS medio mínimo; en caso de empate, k mayor y ponderación uniforme. El invierno inmediatamente anterior queda excluido de los análogos, también en los pliegues internos | §5 |
| C9 | Coherencia física | ΔSWE ≥ −SWE₀ (se trunca el miembro). Además, las variables no negativas (G, L, G_HS, días, formación) se truncan en 0, y los días en n_días como máximo. Se registra la proporción de miembros truncados | §3 (ΔSWE); el resto es una concreción |
| C10 | CRPS | CRPS exacto de la distribución empírica ponderada: Σ wᵢ\|xᵢ − y\| − ½ ΣΣ wᵢwⱼ\|xᵢ − xⱼ\|. No es la versión «fair»: el protocolo la reserva para SEAS5 | §7, §11 |
| C11 | CRPSS y MSSS | CRPSS = 1 − ΣCRPS_mod / ΣCRPS_M0 sobre los inviernos de prueba. MSSS con la media ponderada del conjunto. MAE y sesgo de la media ponderada. Spearman entre media y observación | §7 |
| C12 | RPSS | Terciles con los límites del entrenamiento de cada pliegue; probabilidades a partir de los pesos de los miembros; RPSS frente a M0 | §7 |
| C13 | Bootstrap | Circular por bloques de 5 sobre los 35 inviernos de prueba, B = 2.000, semilla 20261128. Los mismos índices para todos los dominios, estratos, objetivos y modelos de un periodo | §6, §7 |
| C14 | Condición 3 de §7 | En G_SWE o L_SWE: el mismo contraste (p unilateral < 0,05 **sin** Holm, porque es secundario) y CRPSS > 0 | §7 |
| C15 | REJECT | Cota superior del IC percentil al 90 % del CRPSS < 0,05 | §7 |
| C16 | Matrices de transición | Terciles de ΔSWE P1 → P2 y P2 → P3 en los inviernos de prueba, con los límites calculados solo con los inviernos anteriores (origen móvil). Hay una tabla por dominio y estrato | §9 y `phase04_transitions.py` |
| C17 | Emisiones | Cada predicción (modelo, dominio, estrato, periodo, objetivo, invierno) se archiva como JSON inmutable con su SHA-256 en `SEPI_DATA/f05/emisiones/` y un manifiesto | §4 |
| C18 | Degeneración | Por pliegue: una variable no negativa con P90 = 0 en el entrenamiento → predicción UNKNOWN en ese pliegue | §3 |
| C19 | Cobertura | S2M está completo (F04). Si faltara un dato, el invierno queda fuera de la prueba de esa variable y se informa | §3 |

## Registro de cambios posteriores a la ejecución
| Fecha | Cambio | Motivo | ¿Posterior a ver resultados? |
|---|---|---|---|
| — | — | — | — |
