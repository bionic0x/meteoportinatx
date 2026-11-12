# Permission record — ClimayNievePirineos (#9)

**Language / Idioma:** [Español](CNP-PERMISO-20261111.md) · English

**Status on 11 November 2026: data sharing with attribution expressly permitted by the provider; automated access and cadence not specified.** The page [Station usage and characteristics](https://www.climaynievepirineos.com/estaciones/UsoYCaracteristicasCYNP.htm), consulted on 11 November 2026, states at the end that data may be used in media, websites, forums and blogs with a source credit or link to the specific station. It also describes the network as private. It does not specify endpoints, automated extraction frequency, historical retention or commercial terms. The automated access gate remains in place as a precaution while these points are clarified; this must not be presented as an express prohibition by the provider. The forum and images are outside this evidence.

## Evidence status

| Field | Status |
|---|---|
| Source and responsible party identified in the article | Marco Lobera / ClimayNievePirineos; contact's current status to be verified |
| Programmatic reading of station tables | NOT SPECIFIED in the article |
| Rate limits, times and automated caching | NOT SPECIFIED; table updates every 10 min are not an extraction limit |
| Sharing data on websites and other media | PERMITTED with source credit or station link; historical-series and retention details not specified |
| Coordinates and instrument metadata confirmed per station | PENDING |
| Permission for images, comments or forum text | NO; outside scope |
| Public evidence | Provider article consulted 11 November 2026; revocation and automated terms unspecified |

## Query pending to the administrator

Subject: Request for authorisation for non-commercial use of station data in MeteoPortinatx

> We are developing MeteoPortinatx, a free experimental tool for Cerdanya, Capcir and Andorra. We have seen that you permit sharing data with attribution. We would like to clarify the conditions for querying ClimayNievePirineos station tables through an automated process. We are not requesting access to the private forum or copying photographs, messages or personal data. Is querying authorised, under what rate limit, for which URLs and stations, with what attribution and retention/republication policy? Are aggregated and comparative metrics permitted? Is there a preferred feed or API? We would also appreciate knowing how permission can be revoked and the source of each sensor's coordinates/metadata.

Do not send to inferred third-party addresses. Record a response with UTC date, sender/role and verification channel in a **private** file; add only the authorisation record and its terms to the public repository, without the contact's personal data or private screenshots. Review `robots.txt` and policies as well as authorisation; neither substitutes for the other.

## Gate for enabling automated access

- Record the public evidence of sharing with attribution and clarify applicable terms for automated access, endpoints, frequency and project purposes.
- Agree request rate, identifying `User-Agent`, `If-Modified-Since`/cache, retention limits and revocation mechanism.
- Verify coordinates and sensor metadata; test time zone/DST, instrument age, duplicates and suspicious observation detection.
- Community accounts remain `UNVERIFIED` with zero weight in warnings, without copying names, photos or forum text.
- Removal protocol: disable variable, stop requests, revoke credentials and delete copies according to permission.

**Operational status:** `tests/test_community_permission.py` already checks that the network is not accessed without permission. No authorisation request was sent from this session. #9 remains open.

## Automatic activation once the necessary conditions are documented

Permission no longer depends on a variable: it is the `permisos/cnp.json` file (template and fields in `permisos/README.md`). Commit it to `main` with the actual terms:

- **Period:** activates on `valido_desde` and automatically deactivates after `valido_hasta`. Supports permissions for a specified or indefinite period (`null`).
- **Scope:** `ambito` determines whether it covers only private/local use or also Pages and Render (`METEO_PUBLIC_BUILD=1`). With private-only scope, the public website never uses it.
- **Attribution:** displayed whenever the data are used.
- **Cadence:** `intervalo_min_minutos` sets the minimum interval between queries.
- **Notice:** daily `credential-expiry.yml` workflow warns 14 days before expiry.
- **Revocation:** delete the file or move `valido_hasta` earlier.

`CNP_PERMISSION_VERIFIED=1` remains only as a private local switch and is ignored in public builds.
