# Informe 3 · Usos, experiencia de producto y potencial de MeteoPortinatx

**Lentes:** Product Manager, UX Researcher, Trend Researcher. **Estado:** hipótesis razonadas, sin entrevistas ni medición de adopción reales. No se presentan como validación de mercado.

## 1. Dos experiencias, no un tablero único

| Pregunta a responder | Usuario | Vista en <=10s | Horizonte | Fuente primaria | Acción admisible |
|---|---|---|---|---|---|
| ¿Qué sucede ahora en Portinatx? | residente/operador | lluvia/rayos/viento separados, datos y edad, avisos | 0–2h | radar, pluvio, rayos, AEMET | consultar avisos oficiales / tomar precauciones propias |
| ¿Puede haber episodio severo esta tarde? | residente/gestor | riesgo observado vs previsto vs institucional | 2–24h | AEMET, ensembles, radar | planificar, no sustituir protección civil |
| ¿Dónde nevó de verdad? | esquiador/guía | nieve reciente por cota/vertiente con observación y fuente | 0–72h | estaciones, webcams verificadas, partes | escoger dónde consultar partes oficiales |
| ¿Qué valle recibe mejor con esta circulación? | aficionado avanzado | corte de viento/relieve y divergencia de modelos | 1–5 días | DEM, perfiles, modelos | planificar excursión condicionada |
| ¿Fue correcta la predicción? | meteorólogo/comunidad | pronóstico emitido vs observación y error | postepisodio | registro congelado + QC | estudio reproducible |
| ¿Cómo replicar esta herramienta en otro lugar? | desarrollador/ONG | contrato declarativo de dominio y fuentes | meses | catálogo licenciado | adaptar código sin hardcoding |

**Principio:** 3 señales visibles por defecto, detalles científicos bajo pestaña `Método`. El panel actual de decenas de secciones queda como vista experto, no pantalla inicial. Si falta un feed se muestra su edad y `UNKNOWN`, no verde/calmo.

## 2. Diseño de la pantalla «respuesta en diez segundos»

Arriba: `SITUACIÓN`, `RIESGO OBSERVADO`, `AVISO OFICIAL`, cada uno con fuente y hora. Después `CAMBIO RECIENTE` (¿mejora o empeora?) y `GRADO DE CERTEZA` (no traducir fracción de miembros a probabilidad calibrada). Un único enlace `¿Por qué?` muestra radar, estaciones, modelos y discrepancias. Un modo `Episodio` muestra cronología verificable con marcador de red comunitaria **sin verificación**. Otro modo `Investigación` permite descargar evidencia referenciada cuando licencia y privacidad lo permitan.

**Tres ejemplos de tarea** para test cualitativo: localizar última hora de lluvia; entender por qué el radar dice calma y un pluviómetro mide >umbral; comparar nieve natural norte/sur en Cerdanya. Se reclutan mínimo 5 participantes por tarea y segmento para identificar problemas de interacción, no para afirmar métricas poblacionales de adopción.

## 3. Diferenciación real (sin marketing no sustentado)

- AEMET/Météo-France/Meteocat, modelos públicos y portales de estaciones ofrecen datos meteorológicos básicos. MeteoPortinatx **no** tiene una ventaja propietaria en esos datos.
- Posible ventaja en metodología: tres ejes explícitos, `UNKNOWN` honesto, archivo de verificaciones, explicación de discrepancias geográficas y observaciones comunitarias con trazabilidad.
- La comunidad pirenaica aporta conocimiento local, pero necesita licencia/permiso, control de sesgo de selección y revisión. No aporta automáticamente precisión de nowcasting.
- Una web Pages refrescada cada seis horas es un **brief de situación**, no monitor continuo ni sistema de alerta crítica.

## 4. Valor por segmento (priorización inicial)

| Segmento | Problema | Ganancia potencial | Dificultad | Prioridad |
|---|---|---|---|---|
| Residentes Portinatx | interpretar fenómeno en microzona | alta si breve, fresca y trazable | latencia/fiabilidad | P1 |
| Esquiadores Font-Romeu/Cerdanya/Capcir | laderas, cota de nieve, orientación, vento/foehn | alta como complemento | validación local difícil | P1 |
| Aficionados/observadores de foros | seguir y reconstruir episodios | alta como colaboración científica | derechos/ruido | P1 piloto manual |
| Refugios/guías | interpretación situada | potencial medio-alto | responsabilidad civil y fiabilidad | P2, nunca señal de seguridad autónoma |
| Investigadores/periodistas | reproducibilidad de casos extremos | alta en pocos usuarios especializados | dataset y licencias | P1 |
| Protección Civil/operadores críticos | decisiones en crisis | valor hipotético | exigencias regulatorias operacionales | fuera de alcance hasta validación externa |
| Producto turístico masivo | previsión genérica | bajo: mercado saturado | coste adquisición/comoditización | descartar ahora |

## 5. Valoración de potencial

**Potencial alto como plataforma abierta y replicable de auditoría meteorológica local** si construye un archivo y métricas que otros puedan recomputar. **Potencial moderado como producto de nicho** de uso recurrente en costa/montaña con modo de usuario simple. **Potencial no demostrado como herramienta de seguridad operativa o negocio masivo**. No hay aún cifras de audiencia, engagement, willingness to pay, SLO ni skill score fuera de muestra: prohibido inventar TAM, cuota, ROI o precisión.

Métricas para decidir: visitas a ficha de episodio / sesiones que encuentran respuesta en <10s / uso de enlace a aviso oficial / datos con frescura dentro de SLA / nº episodios con pronóstico congelado y verdad observada / % reportes comunitarios corroborados / reducción cuantificada de error vs baseline. La *monetización*, si se planteara, depende de comprobar derechos y resolver el servicio de datos; no es una prioridad de esta fase. La infraestructura de esta propuesta añade **cero recursos cloud de pago**.

## 6. Roadmap propuesto y gates de inversión

| Fase | Trabajo | Producto verificable | Gate |
|---|---|---|---|
| R0 / integridad | completar matriz fuentes/contratos y errores científicos ya identificados | registro P0 de defectos y tests | ninguna falsa comparación espacial en UI |
| R1 / datos | pronósticos congelados, medidos y emparejamiento geoespacial | 30-90 días de archivo con checksums + ensayos de restore | capacidad de reconstruir episodios de punta a punta |
| R2 / nowcast | advección radar y verificación por lead; reglas sombra | error vs persistencia por 10/30/60/120min | mejora robusta sin elevar falso negativo |
| R3 / comunidad | piloto manual CNP/Nevasport/Meteoforum, con autorización | fichas con source URL y QC, sin PII ni copyright | derechos y moderación conformes |
| R4 / UX | modos `Ahora`, `Episodio`, `Investigación` | pruebas de 10 segundos y accesibilidad | mayoría de usuarios encuentra la respuesta esperada |
| R5 / portabilidad | manifiesto declarativo `Domain` | tercer dominio simulado sin cambio de motor | test de geografía, fuente y licencia para dominio nuevo |

No establecer fecha comercial de lanzamiento ni activar datos de foros automáticamente antes de estas puertas.
