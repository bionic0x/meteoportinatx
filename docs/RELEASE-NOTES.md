# Release 0.4.0 — fusión Portinatx + Pirineo

Fecha: 10 de noviembre de 2026.

## Integración realizada

- Preservado motor costero **0.6.1** frente al adjunto anterior 0.6.0: contiene las correcciones CET/CEST y las reglas de avisos.
- Conservado motor pirenaico **0.3.0** con DEM, modelo físico 0–72 h y módulo 15 días.
- Añadida **interfaz de Portinatx** ausente en la release 0.3.0 del repositorio.
- Nuevo `src/nowcast.py` con exportación y servidor común: `/`, `/portinatx/`, `/pirineo/`.
- Estados, alertas, caches y periodicidades de los dos dominios aislados. No se acepta el riesgo de mezclar lluvia convectiva de Ibiza y nieve de montaña.
- Nuevo generador `scripts/build_site.py` con validación estricta de ambos dominios y edad de datos antes de cambiar `site/`.
- Lanzadores y aplicación `.pyz` unificados; se conservan herramientas en `src/portinatx_degen.py` y `src/pirineo.py` para acceso avanzado.
- Se preserva la secuencia DANA como histórico dentro del paquete de entrega local; el repositorio público solo incluye una síntesis sin detalles domésticos privados. El informe forense posterior tiene prioridad al interpretar el sesgo del oleaje.
- Se añaden pruebas de integración, seguridad de rutas, salida sin conexión, frescura y empaquetado en CI. Sin conexión a hosting ni workflow de despliegue.

## Sin prometer

- Un test sintético positivo no equivale a validación meteorológica en vivo.
- No existe calibración estacional de nieve por varios inviernos en esta release.
- El sistema no garantiza disponibilidad de AROME/ICON/ECMWF ni de ningún proveedor en el momento de consulta.
- La versión está preparada para desplegarse **después** de conectar un proveedor de hosting y el proceso de recolección persistente.

Véase [Arquitectura unificada](ARQUITECTURA-UNIFICADA.md) para decisiones y limitaciones.
