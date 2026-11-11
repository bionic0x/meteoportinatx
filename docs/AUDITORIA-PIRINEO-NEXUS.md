# Pirineo: revisión de producto, experiencia y diseño

Revisión del observatorio publicado el 11 de noviembre de 2026. Se recorrieron las doce secciones en escritorio, con capturas de las pantallas. Los resultados describen lo observado en ese ciclo; las fuentes y sus datos pueden cambiar. No se ha completado una auditoría de accesibilidad, contraste instrumental, lector de pantalla ni una prueba de uso en teléfonos reales.

## Qué dificulta la experiencia

| Vista revisada | Hallazgo | Prioridad |
|---|---|---|
| Vigilancia | Los avisos corresponden a zonas y periodos diferentes; el estado de una fuente no demuestra que el punto elegido esté libre de peligro. Hay tarjetas con etiqueta y valor demasiado juntos. | Alta |
| Atmósfera | Los gráficos ocupan gran parte de la pantalla; conviven dos controles de hora correspondientes a fuentes distintas sin explicarlo suficientemente. | Alta |
| Territorio y corte | En el mapa aparecen nombres y cotas superpuestos, especialmente en localidades cercanas. Los selectores de modelos pueden confundirse con casillas. | Alta |
| Puntos | La tabla extensa no ofrece búsqueda y algunas cabeceras abreviadas obligan a interpretar su significado. | Media |
| Modelos | El punto de control se elegía en otra vista, sin presentarse claramente junto a la comparación. | Alta |
| Ensemble de 15 días | El punto inicial puede diferir del de Vigilancia. Las fracciones del ensemble no son probabilidades de impacto calibradas. | Alta |
| Satélite y radar | Se ofrecen visores externos, sin ingestión propia; debe seguir claramente indicado. | Media |
| Superficie | La información técnica compite por la atención con los demás controles generales. | Media |
| Forense | El resumen presenta bloques de texto y valores difíciles de escanear; no hay habilidad predictiva demostrada sin validación prospectiva. | Media |
| Gobernanza | Un estado UNKNOWN puede coexistir con un motivo «ok» cuando falta edad verificable; distinguir el resultado de la fuente de su frescura. | Alta |
| Laboratorio | Los resultados y sus límites requieren jerarquía visual para no confundir simulación con aviso. | Media |

## Primera intervención

- Agrupar las doce secciones por tareas, preservando los enlaces existentes y mostrando la sección activa.
- Identificar la hora de mapas y modelos por separado de la hora del perfil atmosférico; limitar el tamaño de los gráficos.
- Añadir la elección del punto en Modelos y sincronizarla con el punto de control del observatorio.
- Identificar avisos vigentes, próximos, finalizados o sin horario verificable según el reloj del dispositivo, sin atribuirlos automáticamente al punto elegido. La información oficial sigue siendo la referencia.
- Separar visualmente etiquetas y valores en Vigilancia, Forense, Gobernanza y Laboratorio.

## Próximos trabajos

1. Resolver la correspondencia geográfica entre avisos oficiales y localidad con geometrías y cobertura verificadas; mostrar el ámbito y su frescura.
2. Diseñar un estado de punto compartido entre todas las vistas, incluido el ensemble, sin modificar silenciosamente las selecciones existentes.
3. Resolver colisiones de etiquetas en el mapa y en los perfiles, y añadir búsqueda y cabeceras claras a la tabla de puntos.
4. Revisar Gobernanza para diferenciar motivo de consulta, edad y estado derivado.
5. Validar en móvil real, teclado, lector de pantalla y contraste; probar comprensión con personas que utilizan la herramienta.

Los cambios de interfaz no convierten los modelos en observaciones ni introducen alertas oficiales o datos en tiempo real. Un estado desconocido no significa ausencia de peligro.
