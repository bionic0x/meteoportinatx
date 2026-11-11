# Sin publicar — vigilancia de la clave de Météo-France

- `credential-expiry.yml` vigila también `METEOFRANCE_KEY_EXPIRES` si se registra (opcional; los tokens del portal tienen la caducidad que se elija al generarlos).
- `meteofrance-probe.yml` y `scripts/probe_meteofrance.py` prueban `METEOFRANCE_API_KEY` contra DPObs con el conector `src/meteo_france_obs.py` (#38): código HTTP del catálogo y recuentos por estación, nunca la clave.
- Atribución de Météo-France con la hora del último dato cuando sus observaciones se usan.

# Sin publicar — lote de issues #7 #8 #9 #10 #11 #18 #20 #21 #23

- **#20/#21** Rayos en familia eléctrica propia: no confirman ni son confirmados por la lluvia para `alarm`; su nivel sigue visible. Escala 39/40/42/45 dBZ con 1 y 2 frames fuertes.
- **#8** Radio real de la vecindad de modelos (30,2 km, no «±17 km»). Oleaje modelo/boya solo emparejado por boya y hora (±30 min), si no `NO_COMPARABLE`. Cotas del Pirineo por vertiente norte/sur de cada punto.
- **#18/#23** `scripts/check_backend_parity.py` y workflow `backend-parity.yml` (falla si Render no sirve la versión de `RELEASE_STATUS.json`). Presencia de `AEMET_API_KEY` informada sin revelar el valor. Fuente del eje oficial (`AEMET_CAP+METEOALARM`, `SOLO_METEOALARM`, `NINGUNA`) en `core`, API y vistas.
- **#10** `src/radar_motion.py`: vector de movimiento de ecos, ETA 0–120 min con rango y `MOTION_UNKNOWN`. Sustituye a la «velocidad de acercamiento».
- **#7** `src/ledger_shadow.py`: registro en sombra opcional (`METEO_LEDGER`) de pronósticos congelados antes de su ventana. Observaciones PORTUS con `qc=UNKNOWN`, por lo que todavía no se puntúan.
- **#9** Sin acceso automático a ClimayNievePirineos salvo `CNP_PERMISSION_VERIFIED=1`.
- **#11** La vista de decisión muestra la fuente oficial y la cota de la vertiente. Protocolo de evaluación con usuarios en `docs/EVALUACION-USUARIOS-P1.md` (sin sesiones realizadas).

## Pirineo — Sidecar climatológico ERA5-Land (experimental)

Se incorpora generador manual con pruebas sintéticas y notas informativas de lluvia a 24 h. Sin descargas reales, sin credenciales provisionadas, sin impacto en alertas ni Render Free. Pendiente validar el formato del CDS y los términos de redistribución.

# Sin publicar — motor del Pirineo 0.6.1 (paridad con el costero y física de montaña)

`src/pirineo.py` y `src/pirineo_meta.py` pasan de 0.3.0 a 0.6.1. El número alinea el motor de montaña con las garantías del núcleo costero 0.6.1; no indica calibración.

**Ausencia de dato = UNKNOWN, nunca 0**
- Föhn sin perfil, sin previsión en el par o sin horas comunes → `estado: UNKNOWN` y `horas: null` (antes «0 h», que se leía como «sin föhn»). Se emparejan horas por instante UTC (Open-Meteo y MET Norway) y cuenta la señal de cualquier modelo, no solo el primero (`por_modelo`).
- Valores «ahora» de un punto (T, Td, Tw, viento) → `null` si la serie no cubre la hora actual con ±90 min, en vez de tomar el valor de otra hora.
- Malla: un acumulado de 3 h con algún hueco → `null`, no la suma con huecos a 0.
- `core.fuentes_edad_min`: edad del dato servido por cada fuente con caché.

**Física de montaña**
- Perfil con la superficie del modelo: se descartan los niveles de presión bajo el terreno (p. ej. 925 hPa bajo la Cerdanya) y se añade el nivel de 2 m a la presión de superficie.
- Capa cálida sobre aire bajo cero en el fondo (lago frío): `capa_calida` (base, tope, T máx., T del fondo) y `riesgo_engelante` si hay precipitación. En ese caso no se dan cotas de nieve; antes el isocero de la capa alta ocultaba el aire bajo cero del valle.
- Metaanálisis: bulbo húmedo psicrométrico a la presión de cada estación (antes Stull a 1013 hPa, con desvíos de décimas justo en el umbral de fase). La fracción `wet_bulb_le0` solo cuenta miembros con precipitación: un día seco y frío ya no da 1,0. El umbral de fase sólida usa el mismo 0,7 °C que el motor 0–72 h.
- Inversión observada: solo se afirma con ≥300 m de desnivel y pendiente mayor que dos veces su error típico; si no, `concluyente: false` y la vista no dibuja la recta.

**Sin cambiar:** el umbral de fase sigue siendo una hipótesis sin calibrar; el enfriamiento por fusión no se modeliza; la inversión sigue mezclando cuencas; el föhn del sur no se evalúa; el motor regional (`zone_engine.py`) aún usa Stull.

# Sin publicar — confirmación independiente para alarm y Z–R explícita (#17)

- Ninguna observación aislada da `alarm`: cada canal observado aporta como mucho `alert` a la fusión. El rojo solo llega por confirmación independiente (grupo, raíz y familia distintos, con una observación local), por el gate de alta resolución o por el suelo del aviso oficial, que no cambia. Los motivos indican cuándo se ha aplicado el techo.
- El umbral de QPE del radar se evalúa solo con `CFG["radar_threshold_zr"]` (Marshall–Palmer, coherente con 45 dBZ). Con la relación «tropical» el `alert` saltaba ya hacia 40 dBZ; ahora sigue mostrándose solo como diagnóstico.
- Tests del canal de rayos: niveles por recuento, distancia, localidad y salto de actividad.

# Sin publicar — cobertura por familia y frescura uniforme (#16)

- `fuse()` exige al menos un canal observado vivo de la familia lluvia: con solo viento y mar vivos declara cobertura insuficiente, marca lluvia `UNKNOWN` y no desescala.
- Cada canal registra la hora de su dato más reciente (`data_time`). Sin hora, más viejo que `CFG["channel_max_age_min"]` o fechado en el futuro, pasa a `UNKNOWN` antes de la fusión. El eje oficial no cambia.
- Radar con la misma imagen con ecos en todos los frames → congelado, `UNKNOWN`. Frames vacíos idénticos (cielo despejado) siguen siendo válidos.
- Modelos y oleaje con todos los valores `None` → `UNKNOWN`; los huecos ya no se cuentan como 0 mm.
- `core.json`, la API pública y la vista de Portinatx muestran la edad del dato de cada canal.
- Límites de edad de partida, sin calibrar; revisar con el archivo de pronósticos (#7).

# Sin publicar — catálogo de fuentes y conocimiento con procedencia

- Nuevo `src/knowledge_base.py` (stdlib): catálogo de fuentes con licencia/verificación, priors marcados HYPOTHESIS, procedencia de umbrales (`THRESHOLD_PROVENANCE`; Meteoalerta Anexo 1 = `None`, sin valores inventados) y lectura validada de sidecars JSON.
- Nueva fuente `contexto` (`kind="context"`): UNKNOWN si no hay sidecar válido; no entra en la fusión ni cambia niveles. El backend no la cuenta como fuente costera utilizable.
- Pirineo: la rampa de fase de `snow_frac` pasa de 0,5 °C a 0,7 °C de bulbo húmedo (literatura de Cataluña, sin calibrar localmente) y `profile_diag` añade `tw07_m`. Las cotas heurísticas de copo/cuajado/acumulación no cambian.
- `docs/CATALOGO-FUENTES.md`. Sin sidecar real, sin conectores probados en vivo. No se ha cambiado ninguna versión.

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
