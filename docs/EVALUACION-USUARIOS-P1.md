# Evaluación con usuarios de la vista de decisión (issue #11)

**Idioma / Language:** Español · [English](EVALUACION-USUARIOS-P1.en.md)

**Estado:** protocolo listo; sesiones **no realizadas**. Ningún resultado de este documento existe todavía. No se debe inventar adopción, satisfacción ni habilidad predictiva.

## Qué se evalúa

La vista `/decidir/`, con tres niveles: 01 Decidir · 02 Seguir datos · 03 Investigar. Se evalúa sobre la instantánea pública o el servidor local, nunca en un episodio real de peligro. Pregunta: ¿cada perfil encuentra en ≤15 s lo que necesita, sin leer calma donde falta dato?

## Participantes

- Al menos **5 personas por segmento**: casa junto a torrente, barca, segunda residencia en el Pirineo, esquí y montaña. El segmento «investigar el episodio» es opcional.
- Personas reales del segmento, no el propio mantenedor. Se reclutan de forma voluntaria y sin compensación que condicione las respuestas.

## Tareas (las mismas para todos, en este orden)

1. **Estado oficial.** «¿Hay algún aviso oficial vigente y quién lo emite?» Éxito: nivel y organismo correctos, o «no verificado» si así figura.
2. **Edad del dato.** «¿De cuándo son estos datos?» Éxito: identifica la edad del ciclo y si es reciente o antigua.
3. **Ausencia ≠ calma.** Se muestra un caso preparado con cobertura de lluvia insuficiente (instantánea de prueba). «¿Está tranquilo?» Éxito: responde que no se puede saber. Fallo crítico: responde «sí, está tranquilo».

Para montaña, la tarea 3 se sustituye por: «¿Está tu punto por encima de la cota de nieve?» Éxito: lee la cota de su vertiente, o «—» si no hay dato, sin suponer que está por debajo.

## Medidas

| Medida | Cómo | Umbral orientativo |
|---|---|---|
| Éxito por tarea | Sí / no / parcial, anotado por el observador | ≥80 % por segmento |
| Tiempo hasta respuesta | Cronómetro desde que se formula la pregunta | Tareas 1–2: ≤15 s |
| Fallos críticos | Calma inferida donde hay UNKNOWN, o estimación propia tomada por aviso oficial | **0** |
| Móvil | Misma sesión en un teléfono a 360 px | Sin bloqueo de tarea |
| Accesibilidad | Nivel sin depender del color; navegación con teclado | Sin bloqueo de tarea |

Con 5 personas por segmento, los porcentajes son **descriptivos**, no estadísticos. Se publican con su denominador (p. ej. «4/5»).

## Privacidad y registro

- Sin nombres, contactos, ubicaciones de vivienda ni grabaciones de pantalla con datos personales. Cada sesión se identifica como `S-<segmento>-<n>`.
- Plantilla de registro, una fila por tarea: `sesion, segmento, dispositivo, tarea, exito, segundos, fallo_critico, observacion_breve`. `observacion_breve` se limita a la conducta observada; nunca se copian citas literales.
- Los registros se guardan fuera del repositorio. En el repositorio solo se publica el resumen agregado.

## Después

Cada fallo crítico abre una issue con la captura de la instantánea de prueba (sin datos personales) y la tarea afectada. No se modifica el nivel de alerta ni la fusión por resultados de usabilidad.
