# Data source permissions

**Language / Idioma:** [Español](README.md) · English

One file per source. Until it exists, the source is **disabled**: the engine makes no requests.

To enable ClimayNievePirineos when authorisation arrives, copy `cnp.example.json` as `cnp.json`, fill in the actual terms and commit it to `main`. There is no need to change code or variables.

| Field | Meaning |
|---|---|
| `fuente` | `climaynievepirineos` |
| `otorgado_por` | Who authorises it (role or organisation, without personal data) |
| `fecha_autorizacion` | Document date (YYYY-MM-DD) |
| `valido_desde` / `valido_hasta` | Validity period, both dates inclusive. `valido_hasta: null` = indefinite |
| `ambito` | `["privado"]`: local use only. `["privado", "publico"]`: also Pages and Render |
| `atribucion` | Text displayed whenever the data are used |
| `intervalo_min_minutos` | Agreed minimum interval between queries (≥10) |
| `referencia` | Where written authorisation is archived (private record) |

**Behaviour:**

- Automatically activates on `valido_desde` and deactivates after `valido_hasta`.
- On Pages and Render (`METEO_PUBLIC_BUILD=1`) it activates only if `ambito` includes `publico`.
- A file with unknown fields, invalid dates or incomplete data is treated as absent.
- The daily `credential-expiry.yml` workflow fails (and GitHub notifies) when 14 days or fewer remain until `valido_hasta`.
- Revocation: delete `cnp.json` (or move `valido_hasta` earlier) and commit the change; the next run stops querying.
- Private local use without a file: set `CNP_PERMISSION_VERIFIED=1` in your `config.env`. It is never valid on Pages or Render.
