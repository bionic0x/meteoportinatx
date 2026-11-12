# Permisos de fuentes de datos

**Idioma / Language:** Español · [English](README.en.md)

Un fichero por fuente. Mientras no exista, la fuente está **desactivada**: el motor no hace ninguna petición.

Para activar ClimayNievePirineos cuando llegue la autorización, copia `cnp.example.json` como `cnp.json`, rellénalo con los términos reales y súbelo a `main`. No hace falta tocar código ni variables.

| Campo | Significado |
|---|---|
| `fuente` | `climaynievepirineos` |
| `otorgado_por` | Quién autoriza (rol u organización, sin datos personales) |
| `fecha_autorizacion` | Fecha del documento (AAAA-MM-DD) |
| `valido_desde` / `valido_hasta` | Periodo de validez, ambos incluidos. `valido_hasta: null` = indefinido |
| `ambito` | `["privado"]`: solo uso local. `["privado", "publico"]`: también Pages y Render |
| `atribucion` | Texto que se mostrará siempre que se usen los datos |
| `intervalo_min_minutos` | Tiempo mínimo entre consultas acordado (≥10) |
| `referencia` | Dónde está archivada la autorización escrita (expediente privado) |

**Comportamiento:**
- Se activa sola el día `valido_desde` y se desactiva sola después de `valido_hasta`.
- En Pages y Render (`METEO_PUBLIC_BUILD=1`) solo se activa si `ambito` incluye `publico`.
- Un fichero con campos desconocidos, fechas inválidas o datos incompletos se trata como ausente.
- El workflow diario `credential-expiry.yml` falla (y GitHub avisa) cuando quedan 14 días o menos para `valido_hasta`.
- Revocación: borra `cnp.json` (o adelanta `valido_hasta`) y súbelo; la siguiente ejecución deja de consultar.
- Uso local privado sin fichero: `CNP_PERMISSION_VERIFIED=1` en tu `config.env`. Nunca vale en Pages ni en Render.
