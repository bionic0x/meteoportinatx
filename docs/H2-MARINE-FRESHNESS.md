# H2 — Frescura instrumental de PORTUS y radar HF (11-11-2026)

## Riesgo corregido

La vigencia de la caché de red no constituye una observación reciente. `cached_source`
puede recuperar con `status="ok"` una medida cuyo `data_time` es antiguo.
La advertencia textual de que una boya estaba `STALE` no impedía que su
altura de ola participara en el nivel observado.

## Contrato implementado

- `status` describe el resultado del conector; **no** es sinónimo de dato vivo.
- `freshness = FRESH | STALE | UNKNOWN` se calcula sobre la hora de la medida
  con zona UTC explícita, **nunca** `fetched_at` ni la edad del cache.
- `FRESH`: edad entre −10 minutos y el límite de la familia. `STALE`:
  más antiguo o adelantado más de 10 minutos. `UNKNOWN`: sin hora válida
  o sin zona horaria, o fuente fallida.
- Límites conservadores provisionales, **no un SLA de proveedor**:
  **PORTUS genérico 120 min; PORTUS oleaje 120 min; viento 60 min;
  nivel del mar 120 min; radar HF SOCIB 90 min**. Se deben calibrar
  contra la cadencia observada de cada producto.
- Una misma respuesta PORTUS puede etiquetar **oleaje STALE**, **viento
  FRESH** y **nivel FRESH**. La fecha global del proveedor es insuficiente.
- Los canales `mar_boyas` y `viento_estaciones` solo utilizan muestras
  de su magnitud cuya fecha sea FRESH. Un dato antiguo no suma nivel,
  no valida cobertura y no implica calma.
- `sea_model_check` omite muestras de oleaje antiguas, aunque PORTUS siga
  disponible para otras variables. Su comparación modelo/observación
  **aún necesita** pareo espacial y temporal (#8).
- El `core` público conserva solo `name/status/data_time`, la etiqueta
  de frescura, edad, límite y los tres estados de familia autorizados;
  nunca exporta payloads ni detalles privados de la fuente.

## Pruebas sintéticas

`tests/test_marine_freshness.py` cubre caché HF todavía válida en tiempo de
descarga pero caducada en medida, verano/invierno con la hora local duplicada
el 25 de octubre, timestamps sin zona, fechas futuras, fallo de proveedor,
oleaje extremo antiguo vs oleaje modesto reciente, viento ausente con
mareógrafo reciente y proyección pública segura.

## Limitaciones y próxima iteración

Este parche no audita en vivo la frecuencia de PORTUS, no determina una
probabilidad de temporal ni cambia avisos institucionales, umbrales oficiales,
Render o el backend en producción. `radar_hf` es una corriente regional del
canal de Ibiza: no constituye por sí solo una medición en Portinatx ni
interviene en la fusión de alarmas.

En #22 resta contrastar los límites con datos reales, asegurar control
histórico de cambios de cadencia y desglosar el estado por estación. El
compare de boya/modelo debe corregirse por separado bajo #8.
