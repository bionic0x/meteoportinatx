# MeteoPortinatx: usos, propuesta de valor y potencial

Análisis del código en `fded39b710e1981cb2583adff2462244c151be9f`. Perfiles utilizados como guías de trabajo: [Product Manager](https://github.com/msitarzewski/agency-agents/blob/8ae6164602c95ca78828b148b9052460ee426885/product/product-manager.md) y [UX Researcher](https://github.com/msitarzewski/agency-agents/blob/8ae6164602c95ca78828b148b9052460ee426885/design/design-ux-researcher.md). Se aplican sus métodos de priorización por resultados, investigación y contraste de hipótesis. Este documento no representa entrevistas realizadas, una auditoría visual ni una medición de mercado.

## 1. Decisión de producto recomendada

Desarrollar primero una herramienta costera para preparar decisiones y revisar episodios en Portinatx. La promesa inicial defendible es reunir, fechar y explicar la evidencia que una persona necesita consultar: qué dicen los avisos oficiales, qué se observa realmente cerca del lugar, qué anticipan los modelos y qué información falta. La mejora de precisión frente a otras previsiones sigue siendo una hipótesis que necesita validación independiente.

**Propuesta de valor para probar:** «Antes de reorganizar una actividad en Portinatx, consulta en un mismo lugar el aviso oficial, las observaciones disponibles y la discrepancia entre previsiones; conserva después lo que sabías cuando decidiste». La última parte requiere completar y verificar persistencia y exportación de informes; no se ofrece ya como servicio duradero.

El producto puede aportar valor aunque no gane a todos los modelos: menor tiempo para consultar fuentes, mejor comprensión de límites y una revisión reproducible de decisiones son beneficios distintos de reducir error meteorológico. Deben medirse por separado. Un usuario más confiado pero peor informado no constituye una mejora.

## 2. Qué soporta hoy esta promesa

| Evidencia del repositorio | Implicación para el usuario | Límite de la evidencia |
|---|---|---|
| `src/portinatx_degen.py:4171` construye `official`, `hazard`, `precaution`, `coverage`, `channels` y `sources` | Base sólida para distinguir procedencia, observación y juicio propio | La presencia de campos no demuestra que el usuario comprenda las diferencias |
| `src/nowcast.py:49` conserva el ciclo costero y exporta ambos dominios por separado | Un proyecto puede ofrecer dos experiencias especializadas | No permite trasladar umbrales costeros a nieve o montaña |
| `src/pirineo.py:839` exporta puntos, perfiles, föhn, inversiones, observaciones y avisos | Hay material para planificación por altitud y lugar | No demuestra estado de una pista, carretera o estabilidad del manto nivoso |
| `src/pirineo.py:847` enlaza boletines de aludes y fuentes de tráfico | El producto puede dirigir al responsable competente en la decisión | Los enlaces no equivalen a integrar y validar su información |
| `src/nowcast_backend.py:80` proyecta información pública y retira narrativas privadas | Existe una separación útil entre tablero público y evidencia del propietario | Algunas explicaciones y condiciones de salida desaparecen de la vista pública |
| `src/nowcast_backend.py:331` informa estado por dominio; `:373` sirve `/healthz` | La disponibilidad del proceso y la disponibilidad meteorológica se pueden mostrar por separado | Un HTTP 200 no prueba frescura ni cobertura suficiente |
| `.github/workflows/deploy.yml:13` programa instantáneas cada seis horas | Es viable una consulta periódica con hora de emisión visible | No es vigilancia convectiva continua |
| `render.yaml:8` y `:19` declaran servicio gratuito y ausencia de disco requerido | Es una vía de demostración con coste de infraestructura acotado por su configuración | No sustenta una promesa de archivo permanente o servicio continuo |
| `docs/FORENSE-PUBLICO.md:3` delimita el estudio a un episodio | El análisis postepisodio tiene un punto de partida concreto | No demuestra superioridad general, probabilidad calibrada o resultados comerciales |

Dos detalles condicionan especialmente la propuesta de valor:

1. La frescura debe referirse a la información que sostiene cada decisión, además de la hora del ciclo. Una exportación reciente con observaciones antiguas no es «ahora». El estado CLI en `src/nowcast.py:75` comprueba inventario de archivos; no debe convertirse por sí solo en un indicador comercial de disponibilidad de datos.
2. El paso de vista privada a pública elimina `precaution.decision`, `exit_conditions`, razones y evidencia de canales (`src/nowcast_backend.py:98`). Si se promete explicar «por qué», hace falta una explicación pública específica con datos publicables y trazables. Reutilizar notas privadas no es una solución aceptable.

Hay además una hipótesis de defecto de integración a verificar: `src/public_fetch.js:10` exige leer `X-Meteo-Freshness`, pero el bloque CORS en `src/nowcast_backend.py:359` no añade `Access-Control-Expose-Headers`. En una consulta entre orígenes el navegador puede ocultar esa cabecera y forzar el respaldo estático. Es un hallazgo de lectura de código, pendiente de prueba de navegador; afecta directamente a cualquier promesa de preferir datos en vivo.

## 3. Segmentos y decisiones concretas

Son segmentos candidatos, no personas validadas por entrevistas. La prioridad combina adecuación al territorio existente, acceso a evidencia, repetición de la decisión y coste de un error. No se asignan puntuaciones de mercado sin datos.

| Prioridad | Usuario candidato | Decisión y horizonte | Resultado que habría que demostrar | Dependencia que limita el uso |
|---|---|---|---|---|
| P0 | Gestores de alojamientos y actividades exteriores en Portinatx | Preparar una alternativa, revisar equipamiento, comunicar incertidumbre; día siguiente y revisión del mismo día | Menos consultas dispersas; comprensión correcta de aviso, observación y escenario | Conocer exposición real del lugar; evitar convertir lluvia prevista en inundación del inmueble |
| P0 | Aficionados avanzados y colaboradores de observación | Documentar un episodio y contrastar previsión/medición | Registro reproducible de qué se sabía antes; detección de datos dudosos | Archivo duradero, control de calidad y permiso para reutilizar observaciones |
| P1 | Operadores de actividades náuticas | Preparar opciones y consultar estado/avisos antes de su propia evaluación | Mejor lectura de discrepancia modelo/boya y exposición local | Validación marina espacial; decisión profesional y fuente oficial siguen siendo necesarias |
| P1 | Visitantes y residentes | Elegir una franja para una actividad flexible | Localizar incertidumbre y antigüedad rápidamente | Alta sensibilidad a mensajes simplistas; demostrar ventaja sobre su aplicación habitual |
| P2 | Alojamientos, guías y visitantes del Pirineo | Planificar desplazamiento y alternativas según cotas; corto plazo, escenarios a más días | Comprensión por altitud y horizonte, con revisión antes de salir | Observación local, caminos/carreteras y boletines de aludes independientes |
| P2 | Docentes y analistas | Comparar modelos y explicar eventos | Aprendizaje con fuentes fechadas y casos reproducibles | Licencias, anonimización y distinción entre ejemplo y validación científica |
| Aplazar | Servicios de emergencia, automatización de cierres o acciones sobre instalaciones | Decisiones de seguridad con consecuencias inmediatas | Exigirían otro nivel de validación, cobertura y operación | No existe evidencia de preparación suficiente para esta promesa |

**Costa primero, Pirineo como segundo recorrido.** Portinatx reduce el ámbito geográfico del primer piloto y dispone de material forense local. Es una elección de foco, no una afirmación de mayor habilidad predictiva. El Pirineo ya tiene código y debe conservarse; su valor debe probarse con usuarios, altitudes, estaciones y regímenes propios. Replicar un panel no equivale a replicar evidencia. La estacionalidad puede cambiar la prioridad si aparecen colaboradores y observaciones verificables antes en montaña.

## 4. Tres recorridos propuestos

Estos recorridos son especificaciones para investigación y diseño. No describen resultados de una prueba con usuarios.

### Preparar una actividad costera

1. La persona elige lugar y franja temporal; el sistema muestra alcance geográfico y antigüedad de las fuentes pertinentes.
2. Consulta tres bloques diferenciados: aviso oficial vigente; observaciones disponibles; previsión y discrepancias. Una fuente ausente se identifica antes de interpretar el riesgo.
3. Ve qué cambió desde la consulta anterior y qué dato justificaría revisar su plan. Los cambios de modelo no se presentan como hechos ya observados.
4. Decide según su procedimiento y deja, si lo desea, una nota privada sobre la alternativa elegida. La aplicación conserva la versión consultada cuando exista archivo verificable.
5. Tras el episodio compara el resultado con la información disponible entonces. No se reescribe retrospectivamente el pronóstico original.

Aceptación propuesta: ante un caso con radar ausente, el participante no concluye «no llueve»; identifica la ausencia y la fuente oficial. Ante datos desactualizados, sabe que necesita una comprobación adicional. Se mide el tiempo de consulta, pero un ahorro de tiempo nunca compensa este error de comprensión.

### Revisar un episodio

1. Seleccionar intervalo, punto o zona y la emisión original.
2. Ver las observaciones comparables y las exclusiones de calidad, tiempo o distancia.
3. Comparar cada modelo con una referencia sencilla y con su propia salida sin corrección.
4. Separar error de amplitud, desplazamiento espacial, retraso y representatividad.
5. Exportar un informe con fuentes y limitaciones. Una corrección experimental queda etiquetada y no modifica automáticamente el circuito operativo.

El caso marino del repositorio ilustra el valor: la comparación espacialmente apareada cambió la interpretación de una aparente subestimación general (`docs/FORENSE-PUBLICO.md:19`). Es evidencia de la importancia del método, no prueba de que una funcionalidad comercial ya funcione para usuarios.

### Planificar en montaña

La persona selecciona lugar, altitud y fecha; distingue observaciones, diagnóstico de corto plazo y escenarios de varios días. Antes de salir vuelve a consultar carreteras y boletín de aludes correspondiente. La salida propuesta expresa rango y limitaciones; no emite «pista abierta» ni «ruta segura» a partir de nieve prevista. En pruebas de comprensión se incluye un caso con nieve pronosticada pero sin datos de acceso.

## 5. Investigación y puertas de decisión

Todos los tamaños y umbrales siguientes son propuestas de planificación. No son resultados ni una garantía de potencia estadística. Deben fijarse antes de ver resultados; muestras pequeñas sirven para descubrir problemas, no para estimar el mercado.

| Etapa / responsable propuesto | Pregunta | Diseño y datos | Puerta para continuar |
|---|---|---|---|
| Descubrimiento / producto e investigación, primera iteración | ¿Existe una decisión repetida y costosa de preparar? | 8–12 entrevistas exploratorias entre gestores, aficionados y operadores; pedir el último caso real, herramientas y consecuencias. Reclutar fuera del círculo promotor y registrar casos que contradigan la hipótesis | Elegir un segmento solo si al menos 4 participantes independientes describen espontáneamente el mismo problema y 3 aceptan aportar casos a un piloto. Es señal cualitativa, no demanda estimada |
| Comprensión / investigación y diseño, segunda iteración | ¿Se entiende incertidumbre, procedencia y frescura? | 6–8 sesiones con tareas y casos: fuente caída, datos antiguos, discrepancia de modelos y aviso oficial. Comparación dentro de cada persona con su procedimiento habitual y orden alternado | Todos identifican quién emite el aviso oficial; cualquier interpretación de ausencia como calma o del diagnóstico como garantía impide ampliar el piloto hasta corregir y repetir esos casos |
| Piloto asistido / producto y operación, varias semanas con episodios pertinentes | ¿Mejora el trabajo en condiciones reales? | 3–5 colaboradores, registro de consultas/decisiones y entrevistas breves; mantener sus procedimientos habituales. Comparar consultas equivalentes, no días tranquilos frente a tormentas | Propuesta: al menos 3 colaboradores repiten uso en 3 ocasiones relevantes sin insistencia del equipo; mediana de tiempo de preparación menor que su referencia sin aumentar errores críticos. Si no ocurren episodios útiles, declarar evidencia insuficiente |
| Valor económico / producto, después del piloto | ¿Alguien asigna presupuesto o recursos? | Presentar oferta concreta con alcance, dependencia de fuentes, soporte y precio a estudiar; separar pagador de usuario | Antes de una inversión comercial importante, obtener compromisos verificables de al menos 2 organizaciones independientes o financiación explícita de una vía comunitaria. Entusiasmo o respuestas hipotéticas no bastan |
| Expansión / responsable científico y producto | ¿El beneficio se reproduce en otro lugar o estación? | Nuevo conjunto independiente y usuarios del nuevo ámbito; repetir comprensión y contraste meteorológico | Cumplir criterios científicos y de uso del nuevo ámbito. No heredar el resultado de Ibiza al Pirineo |

Guion mínimo de entrevista: «Cuéntame la última vez que cambiaste un plan por el tiempo»; «¿Qué fuentes consultaste y en qué orden?»; «¿Qué dato faltaba?»; «¿Cómo verificaste después si la decisión fue buena?»; «¿Quién pagaría o mantendría una herramienta?»; «¿Qué te haría dejar de usarla?». Preguntar por hechos antes de presentar la solución reduce respuestas complacientes.

Incluir participantes con distintos niveles de conocimiento, uso móvil al exterior, menor visión, dificultades para distinguir colores y conexión limitada. Probar texto, iconos, lectura por teclado o lector de pantalla en el prototipo correspondiente. La accesibilidad pendiente de prueba no se presume resuelta por tener HTML. Obtener consentimiento, minimizar datos personales y guardar entrevistas fuera del repositorio público.

## 6. Medición que une ciencia y producto

Una métrica principal candidata es **decisiones documentadas con fuentes pertinentes y vigentes correctamente interpretadas** por colaborador activo y ocasión relevante. Es más exigente que contar visitas y evita premiar consultas compulsivas. «Correctamente» exige una rúbrica: identificó aviso oficial, hora/ámbito, datos ausentes y límites del horizonte. No equivale a acertar el tiempo.

Panel mínimo del piloto:

- Utilidad: tiempo de preparar la decisión frente a la referencia personal; recurrencia por ocasión pertinente; razón explícita de abandono.
- Comprensión: errores de procedencia, frescura y ausencia; capacidad de explicar discrepancia e identificar información pendiente.
- Ciencia: resultados fuera de muestra por variable, horizonte y régimen; usar el protocolo de validación del modelo, no satisfacción del usuario como sustituto.
- Operación: proporción de consultas con fuentes críticas vigentes, latencia del ciclo, fallos de proveedor, uso del respaldo estático, huecos del archivo y recuperación tras reinicio.
- Negocio: compromisos verificables, coste de soporte y mantenimiento por colaborador; disposición declarada a pagar queda separada de pago o contrato real.

Instrumentación propuesta, aún no implementada: eventos `view_loaded`, `source_state_seen`, `official_source_opened`, `scenario_compared`, `decision_saved`, `report_exported`, `fallback_used`. Guardar versión del producto, dominio, identificador de ciclo, horizonte y estado de fuente; evitar notas privadas, coordenadas domésticas o identificadores personales en telemetría pública. Publicar conteos agregados cuando proceda. Las notas de decisión requieren almacenamiento con control de acceso y retención definida.

## 7. Posicionamiento y posibilidades comerciales

El usuario ya puede combinar servicios oficiales, aplicaciones generales de meteorología, visualizadores de modelos y observaciones locales. AEMET, los servicios oficiales pirenaicos y los boletines de aludes son fuentes de autoridad; aplicaciones como Windy o meteoblue son referencias candidatas para estudiar hábitos de consulta. No se ha realizado una comparación actual de sus funciones, precios o calidad. No se puede afirmar un vacío de mercado ni una superioridad.

La comparación que importa es una tarea completa: cuánto cuesta obtener una conclusión fundada para un lugar, cuánta información se pierde y si se puede reconstruir después. Un panel con más capas puede empeorar esta tarea. La diferenciación a demostrar sería la combinación de contexto local, incertidumbre explícita, continuidad de la evidencia y explicación comprensible.

Opciones de evolución, ordenadas por dependencia de evidencia:

1. **Observatorio abierto y aprendizaje comunitario.** Portal de fuentes y análisis públicos; colaboradores aportan observaciones con autorización y calidad conocida. Requiere propietario del mantenimiento y financiación sostenible aunque el acceso sea gratuito.
2. **Informes y acompañamiento para organizaciones locales.** Resúmenes de episodios, comparaciones y preparación de alternativas. Piloto manual antes de automatizar. Facturar trabajo verificable exige distinguir información meteorológica de una obligación de disponibilidad continua.
3. **Espacio privado de planificación y archivo.** Varios lugares, decisiones, informes y roles. Depende de persistencia, autenticación y investigación que demuestre esa necesidad; la API pública actual es de solo lectura y no proporciona estas capacidades.
4. **API o marca blanca.** Solo tras estabilizar contratos, licencias, control de acceso, soporte y costes. Reexponer datos de terceros no crea por sí solo derecho de redistribución comercial.

No se proponen precios, ingresos o tamaño de mercado como hechos. Para medir mercado de abajo arriba: identificar organizaciones con el mismo trabajo, verificar frecuencia y pagador, medir conversión real de pilotos y aplicar un rango de precio efectivamente aceptado. Evitar multiplicar toda la actividad turística por una suscripción supuesta.

## 8. Modelo de costes y viabilidad

Separar coste de demostrar el producto del de operarlo con compromisos. Una configuración gratuita no elimina trabajo humano, cuotas de proveedor, almacenamiento o soporte.

Estimación mensual propuesta:

`coste_total = cómputo + almacenamiento + copias + transferencia + licencias/API + observación propia + horas_mantenimiento × tarifa_interna + soporte + revisión_científica`

Para presupuestar peticiones por proveedor:

`peticiones_mes = Σ_dominio(ciclos_mes × llamadas_por_ciclo × factor_reintentos) − aciertos_caché`

Medir llamadas, bytes y duraciones en una ejecución real. Si un servicio duerme o los ciclos duran más de lo previsto, no usar el intervalo nominal para declarar capacidad. Para almacenamiento, usar tamaño medio observado por ciclo, ciclos efectivamente archivados, retención y número de copias; los snapshots públicos no sustituyen al histórico privado necesario para evaluación.

`contribución_por_cliente = ingreso_neto − coste_variable_de_datos − cómputo_incremental − soporte_incremental`

Solo tiene sentido calcular clientes para cubrir costes fijos si la contribución es positiva y existe precio observado. Construir escenarios bajo/base/alto con rangos medidos; informar aparte las horas no remuneradas. La restricción actual de recursos gratuitos se mantiene: cualquier propuesta que requiera gasto es una opción futura, no una activación autorizada.

## 9. Riesgos y decisiones de alcance

| Riesgo | Cómo aparece | Medida y criterio |
|---|---|---|
| Fatiga por avisos | Cambios menores del modelo provocan mensajes repetidos | No activar push por cada oscilación. Antes de incorporarlo: preferencias, agrupación por episodio, historial y tasa de mensajes sin nueva información útil |
| Falsa seguridad | `UNKNOWN`, un radar caído o un snapshot viejo se interpretan como ausencia de peligro | Pruebas de comprensión con casos degradados; bloquear la expansión del piloto ante ese error |
| Precisión aparente | Un número local o porcentaje oculta límites espaciales y calibración | Mostrar qué representa, horizonte, fuente y cobertura; separar probabilidades de frecuencia de miembros y etiquetas diagnósticas |
| Dependencia de la infraestructura | Salud del servidor se vende como datos en vivo | Medir frescura por fuente y probar fallback, reinicio y cadencia; sin evidencia no prometer vigilancia continua |
| Pérdida de aprendizaje | El histórico desaparece al reiniciar una instancia efímera | Verificar archivo y restauración antes de ofrecer revisión histórica persistente |
| Sobreexposición de información | Notas de propietarios o ubicaciones privadas terminan en la vista pública | Conservar proyección pública mínima y revisar cada nuevo campo; telemetría sin notas privadas |
| Generalización indebida | Una DANA o un lugar se convierte en «modelo mejorado para todo» | Evaluación por eventos independientes y territorio; publicar alcance de cada conclusión |
| Coste y derechos de datos | Crecen llamadas, usuarios o redistribución | Registro de procedencia/licencia, medición de consumo y prueba de economía antes de ampliar |

## 10. Hoja de ruta de producto por evidencia

| Orden | Entregable | Responsable propuesto | Horizonte de trabajo | Criterio de salida |
|---|---|---|---|---|
| Ahora | Contrato de promesa pública y estados de datos | Producto + científico + ingeniería | Primera iteración | Cada frase de producto se relaciona con evidencia o se etiqueta como experimental; ejemplos degradados definidos |
| Ahora | Entrevistas y selección de un trabajo costero | Investigación + producto | Primera/segunda iteración | Puerta de descubrimiento anterior; registro de evidencia favorable y contraria |
| Siguiente | Prototipo del resumen para decidir y comparar | Diseño + ingeniería | Tras seleccionar segmento | Comprensión aprobada, incluyendo accesibilidad y datos ausentes |
| Siguiente | Piloto asistido y archivo verificable | Operación + científico + producto | Ventana con episodios pertinentes | Recurrencia, utilidad, estado de fuentes y reproducción de casos medidos |
| Después | Oferta comercial o vía comunitaria sostenible | Producto + responsable económico | Tras piloto | Compromisos y costes conocidos; soporte explícito |
| Después | Segundo territorio o API | Responsable científico + ingeniería | Tras superar puertas del primer ámbito | Evidencia independiente y derechos/operación resueltos |

Los responsables son funciones a asignar, no personas contratadas ni agentes ejecutando servicios permanentes. El siguiente resultado útil es un piloto acotado que permita decidir con evidencia si el producto merece más complejidad.
