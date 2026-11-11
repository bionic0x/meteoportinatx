# Sin publicar — cobertura por familia y frescura uniforme (#16)

- `fuse()` exige al menos un canal observado vivo de la familia lluvia: con solo viento y mar vivos declara cobertura insuficiente, marca lluvia `UNKNOWN` y no desescala.
- Cada canal registra la hora de su dato más reciente (`data_time`). Sin hora, más viejo que `CFG["channel_max_age_min"]` o fechado en el futuro, pasa a `UNKNOWN` antes de la fusión. El eje oficial no cambia.
- Radar con la misma imagen con ecos en todos los frames → congelado, `UNKNOWN`. Frames vacíos idénticos (cielo despejado) siguen siendo válidos.
- Modelos y oleaje con todos los valores `None` → `UNKNOWN`; los huecos ya no se cuentan como 0 mm.
- `core.json`, la API pública y la vista de Portinatx muestran la edad del dato de cada canal.
- Límites de edad de partida, sin calibrar; revisar con el archivo de pronósticos (#7).

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
