# Release 0.5.1 — correcciones de integración y seguridad

- Reparada lectura de `X-Meteo-Freshness` mediante `Access-Control-Expose-Headers`.
- Añadida `X-Meteo-Snapshot` y verificación de que cada pantalla usa una sola generación de datos, con fallback estático completo.
- Sustituida la copia indiscriminada del `core` público por una proyección explícita de campos permitidos.
- Corregidos los assets JS del servidor local y el empaquetado `.pyz`.
- Unificada versión en motores de integración, portal, manifiesto, release y documentación.
- Regenerada la tabla SHA-256 con verificación obligatoria en CI.
- Render Free desplegado como servicio experimental sin disco: su histórico forense es temporal, no durable.
- Validación ampliada a Python 3.10/3.11 y pruebas Node del puente. Los proveedores meteorológicos aún requieren verificación de campo.

## Histórico — Release 0.4.0

La sección siguiente describe **el estado histórico de la fusión 0.4.0**, anterior al despliegue de GitHub Pages y del backend Render Free. No representa el estado operativo actual.

---

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

## 0.6.0 — Núcleo regional compartido (11 noviembre 2026)

- Portinatx y Pirineo comparten paquetes configurables, previsión, ensembles, radar RainViewer, avisos Meteoalarm por áreas y observaciones METAR cercanas. Pirineo excluye mar.
- Informe HTML sin conexión, archivo por hash, comparación de consultas y descargas de aplicación/perfiles/paquetes desde Pages. Las interfaces territoriales especializadas siguen disponibles.
- Verificación forense local de pronósticos congelados frente a medidas revisadas: puertas temporales y espaciales, unidades y ventanas compatibles, duplicados, errores por episodio, referencia común y Brier. JSON y HTML con trazabilidad y exclusiones; sin recalibración automática.
- Cobertura completa requerida para acumulados diarios y soporte por métrica; paquetes públicos del backend identificados por manifiesto completo, conservando proyección de privacidad y carga web de una misma instantánea.
- El despliegue exige previsión útil en cada punto; las fuentes complementarias fallidas se muestran como desconocidas. No se publican datos de pruebas ni observaciones forenses privadas.
- Validación local con respuestas de prueba y navegador real. Los proveedores en vivo no se han verificado desde el entorno de desarrollo por restricciones de red. La ejecución de Actions y el despliegue de Pages se verifican por separado; Render requiere su propio despliegue.
