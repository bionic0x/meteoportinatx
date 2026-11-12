# H1 — cobertura crítica de lluvia y frescura (parche conservador)

**Idioma / Language:** Español · [English](H1-RAIN-COVERAGE.en.md)

**Objetivo:** evitar que dos observaciones de viento/mar acrediten una falsa sensación de calma cuando la familia lluvia está caída. La fusión mantiene los tres ejes y el suelo oficial.

## Contrato implementado

- `fuse()` exige **simultáneamente** al menos dos observaciones vivas y ≥1 observación de lluvia de `lluvia_observada` (METAR/AEMET/PWS), `pluviometros` (Meteoclimatic) o `radar` (RainViewer).
- Rayos, viento, mar, estimaciones de escorrentía y modelos no sustituyen una observación de precipitación. La disponibilidad se calcula tras QC y validación de timestamp.
- Si falta la familia lluvia: `insufficient=true`, motivo `COBERTURA INSUFICIENTE DE LLUVIA`, `rain_coverage=0/3`, decisión de desescalada `HOLD`, sin rebaja de niveles existentes. `quiet` se mantiene como rango interno, pero **no es una certificación de calma**.
- Horas de **observación**, no de descarga: radar máximo 30 min; AEMET/METAR máximo 90 min; PWS 30 min (QC existente); Meteoclimatic 45 min (edad de estación existente). Hasta 10 min de tolerancia a futuros por desfase; después `UNKNOWN`.
- API pública: lista blanca ampliada únicamente para el booleano `insufficient` y `rain_coverage`; no notas privadas. Vista de propietario: si falla H1 no presenta una precaución `quiet` como diagnóstico disponible.
- El nivel oficial conserva su jerarquía; las reglas de escalada M1/M2 quedan sin cambios y requieren investigación independiente.

## Pruebas y límites

Pruebas nuevas: viento+mar vivos/lluvia caída, bloqueo de 5 ciclos de desescalada, restitución de lluvia vía radar, rayos insuficientes, aviso institucional, AEMET/METAR y radar caducados, observaciones recientes, fechas futuras y ausentes. Se actualizan los fixtures de radar de selftest a tiempos relativos para probar frescura real.

**No incluye:** calibración, persistencia remota del ledger, credenciales privadas AEMET, reconfiguración de Render, conexión de foros, investigación H2 (radar HF) ni resolución de M1/M2. Los resultados de los tests no acreditan skill meteorológico.


## Integración con #24
Este parche mantiene el esquema de frescura por `Channel.data_time` introducido en #24 y corrige un matiz H1: `rayos` y `escorrentia_torrentes` pertenecen a la familia de peligros lluvia, pero no demuestran **cobertura pluviométrica**. Conserva `families` y añade `rain_coverage` para la vista de decisión; los tests viejos se adaptan a `apply_freshness()`.
