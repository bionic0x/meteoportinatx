# Backlog integrado de desarrollo

La dirección vigente exige paridad entre ambas zonas; véase [Zonas modulares](../ZONAS-MODULARES.md) para lo implementado y pendiente. Este documento conserva el backlog inicial.

Este backlog es una propuesta ejecutable derivada de la revisión. Ninguna tarea figura como implementada. P0 = integridad necesaria antes de usar la capacidad afectada; P1 = validación y piloto; P2 = ampliación condicionada a resultados. Los responsables son funciones recomendadas, no personas ya asignadas.

| ID | Prioridad y responsable | Entrega concreta | Dependencia | Aceptación |
|---|---|---|---|---|
| D01 | P0 · ciencia/datos | Cobertura por variable y ventana en nieve y precipitación | Ninguna | Ausencia total, serie parcial, ventana truncada y valores no finitos no se publican como acumulación completa; caso de 1 cero + 23 ausencias preserva incertidumbre |
| D02 | P0 · ciencia | Respaldo efectivo por métrica en metaanálisis | D01 | Una familia sin nieve no incrementa el contador de familias de nieve; métricas sin respaldo permanecen ausentes |
| D03 | P0 · backend/datos | Identidad del ciclo completo y política explícita de revisiones | Ninguna | Cambiar cualquier parte cambia la identidad o se rechaza de forma explícita; puntero, índice y contenido siguen concordando tras repetición y fallo intermedio |
| D04 | P0 · frontend/backend | Contrato CORS de frescura y prueba entre orígenes | Ninguna | Navegador puede leer la cabecera permitida; selecciona backend fresco y fallback etiquetado cuando corresponde; error de fuente no se presenta como dato actual |
| D05 | P0 · datos | Tiempos de origen, run, ingesta y publicación con estado de cobertura | D01 | Un ciclo recién emitido con fuentes antiguas muestra su degradación; umbrales de frescura diferenciados por producto documentados |
| D06 | P1 · plataforma | Archivo durable con restauración verificada | D03 | Se restaura en ubicación nueva y se verifican contenidos e índice; restricciones de retención, acceso y coste documentadas |
| D07 | P1 · frontend/datos | Fijar generación durante toda la carga de una pantalla | D03, D04 | Cambiar CURRENT entre peticiones no mezcla partes de generaciones distintas; fallback coherente y procedencia por parte, sin sobrescritura por la última respuesta |
| S01 | P1 · ciencia | Catálogo de episodios y protocolo prerregistrado | D03, D05 | Estaciones, unidades, ventanas, revisiones de observación y splits definidos; ningún episodio cruza ajuste y evaluación |
| S02 | P1 · ciencia | Evaluación retrospectiva reproducible frente a baselines | S01 | Resultados por fenómeno/horizonte/territorio, muestra efectiva e incertidumbre; misma muestra para comparar modelos; se informa también cuando no hay mejora |
| U01 | P1 · producto | Entrevistas y mapa de decisiones del segmento costero | Ninguna | Evidencia de problemas recurrentes y alternativas actuales; hallazgos separados de opiniones del equipo |
| U02 | P1 · producto/diseño | Prototipo de parte y revisión postepisodio | U01, D05 para datos reales | Participantes distinguen aviso oficial, diagnóstico, incertidumbre y antigüedad; errores de interpretación registrados |
| U03 | P1 · producto/backend | Explicación pública trazable con campos publicables | U02, D05 | Se puede explicar el diagnóstico con fuentes y razones públicas; no se reutilizan notas privadas ni se eliminan las protecciones existentes |
| O01 | P1 · operaciones | Medición de fiabilidad y coste por ciclo | D03, D05 | Registro de fuentes fallidas, reintentos, latencias, duración, volumen y disponibilidad; alertas operativas probadas sin automatizar decisiones meteorológicas |
| L01 | P1 · producto/datos | Inventario de derechos de uso y cuotas | Ninguna | Cada fuente tiene términos, atribución, retención y uso comercial revisados; incógnitas bloquean la promesa afectada |
| P01 | P1 · producto/ciencia | Piloto costero acotado con criterio de cierre | D01–D07, U02–U03, O01, L01 | Promesas compatibles con resultados disponibles; si no hay habilidad predictiva demostrada, alcance limitado a interpretación y trazabilidad; utilidad y coste medidos |
| E01 | P2 · ciencia/producto | Piloto Pirineo con validación propia | D01, D02, S01, U01 adaptada a montaña | Verificación de nieve/altitud/fase y utilidad para usuario concreto; ningún factor costero heredado |
| E02 | P2 · plataforma/producto | API estable y expansión de servicio | P01, L01 | Contratos versionados, coste marginal conocido y demanda contrastada; límites de servicio observados y comunicados |

## Primera iteración sugerida

Trabajar D01–D04 como correcciones acotadas con pruebas de regresión, y abrir U01 en paralelo. Incorporar D05 antes de usar resultados como «actuales». Esto produce una base concreta para aprender de datos y usuarios sin esperar a tener una plataforma completa.

No fijar un número universal de días que certifique calibración. La duración depende de la diversidad de episodios y de las observaciones disponibles. Las estimaciones de esfuerzo deberán hacerse al descomponer cada tarea sobre el código; esta revisión no incluye compromisos de fechas o presupuesto.
