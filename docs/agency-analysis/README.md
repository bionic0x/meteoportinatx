# MeteoPortinatx: modelo, usos y potencial

> Actualización del 11/11/2026: el usuario ha fijado paridad funcional entre Portinatx y Pirineo y paquetes seleccionables por zona. Esta dirección sustituye la priorización geográfica inicial de este análisis. La primera implementación y sus límites están en [Zonas modulares](../ZONAS-MODULARES.md). Los hallazgos siguientes corresponden al commit examinado; las correcciones posteriores se describen allí.

## Decisión recomendada

Desarrollar MeteoPortinatx como un observatorio local que ayuda a interpretar evidencias meteorológicas y revisar decisiones, con Portinatx como primer piloto. Su oportunidad está en unir procedencia, contexto territorial, discrepancias entre modelos y aprendizaje de episodios. La superioridad predictiva frente a un proveedor concreto todavía debe demostrarse.

Mantener Pirineo como segundo dominio científico, con validación propia de nieve, altitud y representatividad. Compartir infraestructura y contratos de datos permite ahorrar trabajo; compartir calibraciones de costa y montaña no está justificado.

La prioridad solicitada es equilibrar rigor meteorológico, usos y potencial de producto. Este dossier desarrolla esa estrategia y un programa de ejecución. Las mejoras descritas son propuestas: esta entrega añade documentación, no modifica el motor ni despliega servicios.

## Cómo se ha trabajado

- Proyecto examinado: `bionic0x/meteoportinatx`, commit `fded39b710e1981cb2583adff2462244c151be9f`.
- Perfiles utilizados: repositorio original [`msitarzewski/agency-agents`](https://github.com/msitarzewski/agency-agents/tree/8ae6164602c95ca78828b148b9052460ee426885), commit `8ae6164602c95ca78828b148b9052460ee426885`.
- Se ejecutaron tres agentes en paralelo, orientados a ciencia y validación, producto y usos, e ingeniería de datos y arquitectura. Una revisión integradora contrastó los hallazgos con el código.
- Los perfiles se emplearon como guías de trabajo. Esto no equivale a revisión por meteorólogos acreditados, investigación con usuarios ni evaluación predictiva con datos independientes.
- La configuración publicada del entorno se mantiene sin cambios. El catálogo original se consultó desde una copia local; no se instaló una aplicación de escritorio ni se alteró la configuración global de agentes.

## Entregables

| Documento | Pregunta que resuelve |
|---|---|
| [Modelo y validación](MODELO-Y-VALIDACION.md) | ¿Qué calcula hoy, qué límites tiene y cómo demostrar una mejora? |
| [Usos y potencial](USOS-Y-POTENCIAL.md) | ¿A quién puede servir, para qué decisiones y cómo comprobar que aporta valor? |
| [Arquitectura y ejecución](ARQUITECTURA-Y-EJECUCION.md) | ¿Qué hace falta para conservar evidencia y operar el servicio de forma fiable? |
| [Backlog integrado](BACKLOG.md) | ¿En qué orden ejecutar el trabajo y con qué criterios de aceptación? |

## 1. Qué significa «modelo» en este proyecto

Hay tres capas diferentes que conviene desarrollar y comunicar por separado:

1. **Modelos meteorológicos de origen.** Predicciones NWP y de IA producidas por terceros. MeteoPortinatx no entrena un modelo global de la atmósfera.
2. **Modelo local de interpretación.** Reglas, observaciones, radar, cálculos diagnósticos, combinación por familias y análisis forense. Aquí reside gran parte del trabajo propio del proyecto.
3. **Modelo de producto y servicio.** Qué decisión facilita, con qué frescura y soporte, y quién sostendría su coste. No hay evidencia de demanda o ingresos en esta revisión.

En la implementación existen separación entre aviso oficial, peligro observado y precaución propia; una capa pirenaica de diagnóstico físico; y un metaanálisis extendido por familias. Son buenos fundamentos para hacer explícitas las incertidumbres. Sus tests de lógica no acreditan precisión meteorológica.

La corrección experimental de lluvia debe competir contra predicciones originales sobre episodios que no se usaron para ajustarla. Los cocientes del episodio DANA documentado en el repositorio son antecedentes de investigación, no parámetros generales de producción. La misma disciplina se aplica a una corrección de oleaje o a una estimación de nieve.

## 2. Hallazgos que cambian las prioridades

| Hallazgo | Evidencia disponible | Implicación |
|---|---|---|
| La agregación de nieve puede convertir una serie casi ausente en 0 cm si otra variable tiene suficiente cobertura | Reproducción sintética del camino `daily_member` → `family_summaries`; detalle en el informe científico | La cobertura debe validarse por variable y ventana antes de presentar cantidades o fracciones |
| Una salida puede declarar varias familias aunque solo una aporte una determinada métrica | Inspección y reproducción de `combine` | Mostrar familias efectivas por métrica; diversidad institucional no prueba independencia estadística |
| Cambiar datos no centrales bajo una misma emisión puede mantener una versión pública anterior; cambiar el core bajo esa emisión puede separar el índice del puntero público | Reproducción offline con `Store` en un directorio temporal | Identificar y publicar ciclos completos de forma coherente antes de usar el archivo para evaluar mejoras |
| La web exige `X-Meteo-Freshness`, pero el backend no lo expone para lectura JavaScript CORS | Contraste de `src/public_fetch.js:10` con `src/nowcast_backend.py:359`; sin prueba de navegador en esta revisión | Probar el recorrido real entre orígenes; una respuesta HTTP correcta por sí sola no valida la integración |
| Emitir un JSON reciente no garantiza que todas sus fuentes sean recientes | Contratos de recopilación y publicación; análisis de arquitectura | Separar tiempos de fuente, ejecución del modelo, recogida y publicación |

Estos hallazgos no se han corregido en esta entrega. Las reproducciones son casos controlados; no miden frecuencia ni impacto en datos meteorológicos reales.

## 3. Producto inicial propuesto

**Usuario inicial:** una persona que coordina actividad o mantenimiento local en Portinatx y consulta varias fuentes antes de decidir. Es una hipótesis de segmento que debe comprobarse mediante entrevistas y observación de su trabajo.

**Trabajo a resolver:** reducir el esfuerzo de reunir información, entender qué ha cambiado y dejar constancia de por qué se revisó un plan. Un parte útil responde a cinco preguntas: qué se observa, qué se prevé, cuánto respaldo tiene, qué dato falta y cuándo revisar de nuevo.

**Alcance del piloto:** parte de planificación local más revisión posterior de episodios, con enlace visible a avisos oficiales y registro de la decisión humana. Las cadencias reales del sistema deben determinar los horizontes ofrecidos. Una instantánea periódica no sostiene por sí sola una promesa de vigilancia continua.

**Ejemplo de salida propuesta, sin valores meteorológicos inventados:**

> Ámbito: Portinatx · ventana de planificación seleccionada. Aviso oficial: estado y enlace a la fuente. Observaciones: sello horario y cobertura. Predicción: rango y discrepancias por familia. Incertidumbre: fuentes faltantes y representación espacial. Próxima revisión: hora o condición definida por el responsable. Decisión: registrada por la persona usuaria.

Para Pirineo, el equivalente debe identificar emplazamiento, elevación, ventana, naturaleza de la nieve estimada y cobertura de cada variable. Las métricas de costa no se reutilizan como prueba de calidad del diagnóstico de montaña.

## 4. Potencial y condiciones para capturarlo

| Línea | Valor posible | Evidencia necesaria antes de ampliarla |
|---|---|---|
| Observatorio local abierto | Explicación verificable y trazabilidad de cambios | Comprensión por usuarios, calidad de fuentes y atribución |
| Servicio para operadores locales | Informes, seguimiento de decisiones y ahorro de tiempo | Uso repetido, utilidad frente al flujo actual y compromiso comercial real |
| Archivo y evaluación por episodios | Comparar errores de amplitud, tiempo y posición | Archivo íntegro, ventanas comparables y observaciones con control de calidad |
| Informes especializados de costa o montaña | Diagnóstico territorial más pertinente | Validación independiente por dominio y revisión experta |
| API o expansión geográfica | Reutilización del núcleo y distribución | Contratos estables, costes medidos, derechos de redistribución y transferibilidad demostrada |

La ventaja defendible sería un conjunto de episodios bien documentados, comparaciones reproducibles y una experiencia útil para decisiones locales. Añadir más modelos, más agentes o más pantallas no demuestra esa ventaja.

## 5. Secuencia de desarrollo

**Primero, confianza en el dato.** Corregir los casos reproducidos, registrar cobertura y edad por variable, hacer verificable el ciclo completo y cerrar la prueba de navegador entre orígenes. La salida ante falta de evidencia debe conservar esa falta de evidencia.

**Después, banco de evaluación.** Congelar pronósticos emitidos, emparejar observaciones y separar entrenamiento, calibración y evaluación por tiempo y episodio. Comparar con baselines sencillos y proveedores originales sobre exactamente los mismos casos. Estimar incertidumbre por bloques de episodio; no tratar cada estación-hora como caso independiente.

**En paralelo, aprendizaje de producto.** Contrastar el flujo actual de usuarios, probar un parte comprensible y registrar utilidad y errores de interpretación. Se puede investigar demanda antes de mejorar el modelo, siempre que la demostración identifique datos y limitaciones correctamente.

**Finalmente, piloto y decisión de expansión.** Operar con promesas acotadas y medir frescura, completitud, calidad meteorológica y utilidad. Ampliar a Pirineo, API o servicio comercial cuando sus criterios estén satisfechos. El calendario meteorológico puede obligar a esperar episodios representativos; un plazo de software no garantiza evidencia científica.

## 6. Criterios de decisión

- **Datos:** los casos de ausencia y publicación incoherente quedan cubiertos por pruebas de regresión; existe evidencia de restauración del archivo si se ofrece histórico persistente.
- **Ciencia:** las mejoras se evalúan fuera de muestra con métricas, umbrales y ventanas definidos antes del análisis. Una mejora media no compensa automáticamente deterioros en fenómenos de mayor consecuencia.
- **Producto:** usuarios del segmento pueden interpretar fuentes, incertidumbre y antigüedad; utilizan el parte en decisiones reales y explican su utilidad frente a alternativas.
- **Economía:** se mide el coste por ciclo completo y por usuario, se revisan licencias y cuotas, y se contrasta disposición real a pagar antes de extrapolar ingresos.

Los umbrales numéricos del piloto que propongan los informes son objetivos de diseño, no resultados obtenidos. Deben acordarse y registrarse antes de medir.

## Alcance de la evidencia

Esta entrega se basa en lectura del código, documentación y reproducciones locales controladas de fallos. Los resultados de onboarding anteriores acreditan pruebas de software y arranque en aquella instancia; no se presentan como nuevas pruebas de precisión ni como verificación del despliegue publicado. No se han realizado entrevistas, estudio de mercado con fuentes externas, evaluación histórica independiente, prueba visual completa ni validación de proveedores en vivo en esta fase.
