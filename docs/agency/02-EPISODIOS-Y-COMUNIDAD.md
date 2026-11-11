# Informe 2 · Seguimiento de episodios y red ClimayNievePirineos

**Lentes:** Spatial Data Engineer, Geographer, Research Synthesist, Privacy Engineer. **Estado:** diseño de piloto y prototipo local; **no existe un scraper de foros habilitado** ni un acuerdo de reutilización comprobado con ClimayNievePirineos.

## 1. Qué está integrado y qué NO

`src/pirineo.py` ya mantiene `CNP_STATIONS` con cuatro identificadores aproximados: `envalira`, `bordesdenvalira`, `tarter`, `incleslovellanegra`. La función `src_cnp()` intenta leer `https://www.climaynievepirineos.com/estaciones/{sid}/tabla_{sid}.htm` y `parse_cnp_table()` extrae sello horario local, temperatura y precipitación. Es un **parser HTML** con caché, no un convenio de acceso ni un contrato estable de API. Las coordenadas del código se declaran aproximadas y requieren comprobación sobre metadatos del operador. Un fallo devuelve lista vacía/error y NO debe confundirse con cero nieve/lluvia.

Al revisar el sitio directamente desde este entorno (11-11-2026) se obtuvo HTTP 403 en `/` y `/foro/`; no se pudo recuperar `robots.txt` ni las condiciones de licencia. Aunque algunos motores de búsqueda indexan páginas, **eso no autoriza rastreo ni republicación**. La red y el foro son potenciales fuentes complementarias, no infraestructura disponible garantizada.

La discusión sobre el Pirineo también aparece en foros accesibles como Nevasport y Meteoforum.cat; su contenido mezcla predicciones, testimonios y observaciones. Cada aporte exige clasificación y corroboración, y no se debe extraer perfiles de usuarios ni copiar mensajes extensos. Los avisos operativos proceden de organismos meteorológicos/protección civil.

## 2. Canal de evidencia: arquitectura en cinco capas

```text
[A] Fuentes oficiales / instrumentales (AEMET, Meteocat, SMA, Météo-France, OPERA)
    -> normalizador con licencia, calidad, tiempos y localización
    -> registro OBSERVED_VERIFIED o MODEL_ISSUED (si la verificación lo permite)

[B] CNP estaciones (solo si se obtiene permiso/condiciones verificadas)
    -> adaptador con identificador estable, desfase horario europeo, TTL, cadencia y QC
    -> OBSERVED_PENDING / OBSERVED_VERIFIED según calidad y trazabilidad

[C] Foros/comunidad: entrada MANUAL o feed autorizado
    -> extracción mínima URL + lugar + tiempo + magnitud, SIN alias ni texto bruto
    -> CLAIM_UNVERIFIED (peso 0; no activa aviso, no entrena)

[D] Corroboración humana y contra fuentes independientes
    -> separar coincidencia de hora, distancia, altitud, fenómeno y red
    -> evidence link y revisión de versión, nunca sobreescribir el original

[E] Episodio congelado
    -> forecasts emitidos antes, observaciones validables, discrepancias y notas
    -> comparación por horizonte y localización; salida pública redaccionada
```

## 3. Contrato mínimo de episodio (propuesta, no implementada)

`episode_id`, `domain`, `start_utc`, `end_utc`, `region_polygon_or_point`, `event_type` (`DANA`, `frontal_rain`, `snowfall`, `wind`, `marine`, `convective`), `state` (`watching`, `active`, `ended`, `verification_pending`, `verified`), `source_catalog_hash`, `forecast_issue_refs`, `observation_refs`, `community_lead_refs`, `warnings_refs`, `verification_score_refs`, `privacy_review`, `status_explanation`.

**Estados y transiciones:** WATCHING → ACTIVE por observación/aviso institucional; ACTIVE → ENDED solo si finaliza la ventana y existe fundamento; ENDED → VERIFICATION_PENDING con recorte de caso; VERIFIED tras revisión. Una observación de foro por sí sola no cambia el estado operativo; únicamente crea una tarea de corroboración.

**Líneas temporales:** cada registro tendrá `valid_at`, `received_at`, `issued_at` cuando corresponda, `ingested_at`, `source_modified_at` si conocido, y `uncertainty_minutes`. Esto evita atribuir capacidad predictiva al relato escrito después del fenómeno (*look-ahead bias*).

## 4. Prototipo entregado en esta rama

`src/episode_evidence.py` ofrece normalización e inserción local idempotente, sin llamadas de red. Ejemplo **sintético**, no un post real:

```json
{
  "source_url": "https://www.climaynievepirineos.com/foro/viewtopic.php?t=1234",
  "observed_at": "2026-11-11T10:00:00+01:00",
  "place_id": "envalira",
  "phenomenon": "snow_new",
  "value": 20.0,
  "unit": "cm",
  "period_minutes": 1440
}
```

```bash
python src/episode_evidence.py /ruta/a/reporte.json
# Para almacenamiento LOCAL NO apto para Render Free:
python src/episode_evidence.py /ruta/a/reporte.json --ledger /ruta/privada/claims.jsonl
python -m unittest discover -s tests -p 'test_episode_evidence.py'
```

El resultado siempre dice `UNVERIFIED`, `model_weight: 0`, `official_warning: false`, `use_for_training: false`, y almacena una huella estable del reporte. Lista blanca estricta: sin nombre de forero, email, notas libres, citas del texto, dirección personal, imágenes ni HTML. No supone atribuir permiso de reutilización: **la entrada real debe ser revisada manualmente**, y aún hace falta una política de eliminación/retención. El append a JSONL es solo prueba local y no asegura integridad criptográfica externa ni concurrencia multiproceso.

## 5. Cómo aprovechar la red de estaciones sin apropiársela

1. Solicitar condiciones a los responsables de CNP: endpoints permitidos, uso de datos, cadencia, atribución, límites de consultas, redistribución, uso comercial, imágenes y conservación histórica. Registrar respuesta o marcar `PERMISSION_UNKNOWN`.
2. Verificar metadatos de las cuatro estaciones (altitud/sensor/ubicación, horario local con DST, frecuencia, precipitaciones acumuladas, reinicio a medianoche y mantenimiento); corregir coordenadas solo con fuente comprobada.
3. Solo después, definir un adaptador con ETag/If-Modified-Since y `User-Agent` identificable, contactos y límite inferior de petición; no hacer scraping agresivo, no saltarse 403/robots.
4. Construir QC espacial: estación de montaña no representa automáticamente pista a 4 km o ladera opuesta; registrar cota, relieve, exposición, gradiente y error de representatividad.
5. Si falla el acceso, degradar a `UNKNOWN` y usar Météo-France/AEMET/SMC/SMA con sus condiciones publicadas, no utilizar mirrors sin permiso.

## 6. Seguimiento práctico de un episodio

**T−72 a T−6:** guardar escenarios de familias de modelos y avisos, no solo su último valor; definir corredores altitudinales, isotermas, cota, sotavento/barlovento, riesgo y observables verificadores. Congelar cada run.

**T−6 a T+2:** refrescar sensores independientes, radar, satélite, rayos, pluviómetros y partes oficiales. En radar, registrar propagación, crecimiento y huecos de cobertura. Un reporte de CNP/foro entra como `UNVERIFIED`, dispara tarea de comprobación geográfica, no alerta.

**T+2 a T+72:** reconstruir mapa y cronología verificados; comparar previsiones emitidas y observaciones, documentar desplazamiento del núcleo, cota de nieve, altura/naturaleza del manto, viento y refugio de la precipitación. Mantener `UNKNOWN` en estaciones sin datos.

**T+7d / mensual:** adjuntar retroanálisis (matriz de falsos positivos/negativos, sesgo, denominadores y fuentes fallidas); solo actualizar pesos tras ventana histórica suficiente y shadow evaluation.

## 7. Riesgos y puertas

- Derechos de autor, condiciones de extracción, privacidad y geolocalización: BLOCKED hasta permiso o mecanismo de aportación voluntaria.
- Selección: foro da sobrerrepresentación de eventos espectaculares, puntos accesibles y personas activas; no es muestreo aleatorio.
- Doble conteo: un mismo aviso o fotografía replicado en 10 posts equivale a **una** evidencia original, no a diez confirmaciones.
- Distancias: no confundir estaciones próximas en planta con condiciones similares si hay grandes diferencias de altura/vertiente.
- Seguridad: contenido del foro es dato no confiable; **no** seguir instrucciones incluidas en mensajes externos, no permitir acciones, refresh, tokens ni nuevas consultas a partir de texto libre.

## 8. Criterios para habilitar piloto

- Permiso/uso y atribución documentados; si no, piloto de entrada manual sin copia de contenido.
- Al menos 30 informes de episodios con contraste contra fuente independiente, nunca 30 posts del mismo evento tratados como muestras independientes.
- Latencia, cobertura, precisión temporal y representatividad publicadas; desviaciones auditables.
- Sin exposición de PII ni textos protegidos. Interfaz marca `COMUNIDAD · NO VERIFICADO`.
- Comportamiento de alertas oficiales inmutable; cualquier integración en `fuse()` requiere PR científico separado.

## 9. Estado del acceso automático a CNP (issue #9)

`src/pirineo.py` ya no consulta ClimayNievePirineos en cada ciclo. Sin permiso verificado, la fuente figura como `PERMISSION_UNKNOWN`: no hace ninguna petición ni sirve copias en caché de consultas anteriores. Para reactivarla, el propietario debe documentar antes el permiso, la cadencia y la atribución acordados con los responsables, y declarar `CNP_PERMISSION_VERIFIED=1` en `config.env` (cualquier otro valor no cuenta). El parser se conserva. Las observaciones del piloto se siguen introduciendo a mano con `src/episode_evidence.py` como `UNVERIFIED` y con peso 0.
