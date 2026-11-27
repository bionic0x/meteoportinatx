# SEPI — inventario verificado de fuentes de nieve, nivología y clima del Pirineo oriental (1968–2026)

**Estado:** inventario de fuentes revisado el 27-11-2026. La auditoría de datos brutos se hizo descargando los ficheros. Es un documento de trabajo de una línea experimental: no es un aviso ni un producto oficial. Diseño y resultados en [`SEPI.md`](SEPI.md); scripts en [`scripts/sepi/`](../scripts/sepi/README.md).

## Conclusiones

- **Ninguna red observacional única y homogénea describe los 58 inviernos** de 1968–69 a 2025–26 en todo el Pirineo oriental.
- **S2M (SAFRAN–Crocus, Météo-France) es la columna vertebral** para Capcir, la Cerdagne francesa, el Canigó, el Ariège y Andorra. Hay que tener en cuenta:
  - **Incluye un macizo propio para Andorra, el n.º 71.** Los pertinentes son Couserans 69, Haute-Ariège 70, Andorre 71, Orlu–St-Barthélemy 72, Capcir–Puymorens 73 y Cerdagne–Canigou 74.
  - **No tiene macizos para la vertiente catalana** (Cerdanya, Ripollès, Núria, Cadí-Moixeró). Que SAFRAN asimile observaciones españolas a través de NIVOMET no crea esos dominios.
  - **No es una observación.** Cada macizo, de unos 1.000 km², se considera homogéneo a una cota dada, con tramos de 300 m, terreno llano o laderas de 20° y 40° en ocho orientaciones.
  - **Tiene una ruptura de forzamiento en 2002:** ERA-40 hasta esa fecha, ARPEGE después, con densidad de observaciones cambiante (Vernay et al., 2022, ESSD 14, 1707–1733).
- **El CSV abierto de S2M es un canal de publicación distinto de AERIS v2020.2** (doi:10.25326/37). Se versionan por separado y no se mezclan.
- **Andorra: Ransol-FEDA (99130004, 1.641 m) midió espesor de nieve a mano de 1934 a 2002**, según su ficha en meteo.ad. Es la mejor observación nival anterior a 1985 en la vertiente sur. Para Engolasters y FEDA Central no hay verificado que exista continuidad nival.
- **Catalunya: la serie manual de AEMET en Núria (1.970 m, lectura a las 08 h) empieza el 01-02-1985.** Antes de esa fecha no se ha localizado ninguna serie diaria de espesor en abierto.
- **NIVOBS:** que la red del ICGC funcione «desde 1985–86» no está demostrado. El ICGC sitúa el inicio del trabajo sobre aludes a finales de 1986 y la difusión pública del BPA hacia 1990–91.
- **Invierno 2025–26:** el ICGC contó **1.073 aludes** (publicación del 22-06-2026; la cifra de 1.049 viene de fuentes secundarias). Es actividad de aludes, no una métrica de espesor: por sí sola no ordena el invierno en un ranking nival.

## Auditoría de datos brutos (27-11-2026)

Las tres comprobaciones que el inventario dejaba pendientes se hicieron descargando los ficheros del espejo público de Météo-France (`https://meteofrance.s3.sbg.io.cloud.ovh.net/data/...`). Es el mismo contenido que enlazan las fichas de data.gouv.fr; desde el entorno de trabajo la API de data.gouv.fr cortaba la conexión.

### 1. Nieve en QUOT 66/09: apertura de una estación ≠ serie nival

Para cada estación y cada variable nival se calcularon los inviernos de diciembre a abril con al menos el 90 % y el 50 % de días válidos. En total son 58 inviernos y 8.772 días esperados por serie.

| Estación (NUM_POSTE, alt.) | NEIGETOT06 con datos | Inviernos ≥90 % | Lectura |
|---|---|---|---|
| Ascou-Lavail (09023002, 1.090 m) | 1972–2023 | 44 | La serie nival observada más larga de la zona |
| Aulus-les-Bains (09029001, 733 m) | 1969–2018 | 45 | Larga, pero baja (Couserans) |
| L'Hospitalet (09139001, 1.425 m) | 1969–2005 | 33 | Ancla para 1969–1984 en Orlu/Haute-Ariège |
| Ste-Léocadie (66181001, 1.320 m) | 1982–2015 | 25 | Cerdagne |
| Porté-Puymorens (66147001, 1.620 m) | 1981–2013 | 22 | **No desde 1964:** la estación abre en 1964, la nieve empieza en 1981 |
| Formiguères (66082001 + 66082004) | 1983–2005 / 2006–2026 | 22 + 17 | Capcir, con cambio de estación en 2005–06 |
| Font-Romeu (66124004, 1.964 m) | 1984–2002 | 14 | Corta |
| Canigou / Port d'Aula (nivosas, ~2.150 m) | 1996/97–2026 | 24 | Automáticas de cresta |
| **Mont-Louis (66117001, 1.600 m)** | 1971–2019 | **9** | **No es serie nival larga:** la estación abre en 1922, pero la nieve es discontinua |
| Ax-les-Thermes (09032001, 713 m) | 1972–1987 | 13 | Corta y baja |

Las estaciones de esquí de la red nivo (código terminado en 4xx: Les Angles, Formiguère 1.753 m, Ascou-Pailhères, Mijanès, Beille, Guzet, Ax-Bonascre) **no llegan a ningún invierno completo**. Observan solo durante la temporada de apertura, con 0–2 inviernos ≥90 %.

### 2. Red nivo-météorologique: estaciones en la zona (generada por `scripts/sepi/audit_nivo.py`, 1996–2026)

| Estación | Altitud | Años | Id WIGOS |
|---|---|---|---|
| Les Angles | 2.108 m | 1996– | — |
| Formiguère | 1.753 m | 1996–2025 | — |
| Mijanès | 1.530 m | 1996– | — |
| Ascou-Pailhères | 1.500 m | 1996– | — |
| Mont d'Olmes | 1.472 m | 1996– | — |
| Beille | 1.789 m | 1996– | — |
| Guzet | 1.384 m | 1996– | — |
| **Porte Puymorens** | 2.085 m | **1996–2009** | sin id |
| **Ax-Bonascre** | 1.715 m | **1996–2024** | sin id |
| Sentein | 1.000 m | 2001– | — |
| Goulier | 1.468 m | 2002–2025 | — |
| Font-Romeu-Galinera | 2.144 m | 2003– | — |
| Le Chioula | 1.600 m | 2005– | — |
| St-Pierre-dels-Forcats | 2.350 m | 2008–2025 | — |
| PORTE-PUYMORENS | 2.087 m | 2010– | nuevo id |
| Puigmal | 2.250 m | 2023–24 | 4 registros |
| Ax-Saquet | 1.997 m | 2024– | — |
| Cambre d'Aze | 1.945 m | 2026 | — |
| Station Formiguères | 2.095 m | 2026 | — |

- No hay estaciones andorranas ni catalanas.
- Los ficheros de 2025 y 2026 cambian el separador de `,` a `;`.
- **Las estaciones antiguas no tienen id WIGOS**, así que agrupar solo por id las omite.

### 3. S2M en CSV

- **Disponible de 1958 a 2026**, con el año en curso actualizado; el último día descargado es el 26-11-2026.
- Los macizos presentes son 1–23, 30, 40–57 y **64–74**. No hay ningún macizo catalán.
- Columnas: `num_massif;dat;altitude;exposition;pente;neigetot;equivalent_eau;ecoulement`.
- `exposition = -1` es terreno llano; 0–315, la orientación en grados. `pente` vale 0, 20 o 40.
- Las unidades de `neigetot` (cm) y de `equivalent_eau` (mm) se infieren de los valores; están pendientes de confirmar con `descriptif_champs.pdf`, que no se pudo abrir.

## Tabla maestra

| Fuente | Naturaleza | Cobertura útil | Geometría | Variables | Acceso y licencia | Estado |
|---|---|---|---|---|---|---|
| S2M CSV (Météo-France) | Modelo / reanálisis nival | 1958 → 2026 | Macizo × 300 m × orientación / pendiente | Espesor, SWE, escorrentía | data.gouv.fr «Données de Modèle de Simulation Nivologique»; espejo `REF_CC/NIVO`. Licence Ouverte 2.0 | **Descargado y auditado** |
| S2M AERIS v2020.2 | Modelo completo | 1958–2021 | NetCDF FORCING + PRO | Meteorología SAFRAN + manto Crocus | doi:10.25326/37 | Verificado en el artículo; acceso actual no auditado |
| Red nivo (NIVOSE) | Observación | 1996 → 2026 | Puesto, cada 12 h | Espesor, nieve fresca, T, HR, viento, perfil | data.gouv.fr «archive-reseau-nivo-meteorologique»; espejo `OBS/NIVOSE`. LO 2.0 | **Descargado; lista auditada** |
| QUOT 66/09 | Observación | Según la estación (ver la auditoría) | Diaria | T, P, viento, HNEIGEF, NEIGETOT06 | data.gouv.fr «donnees-climatologiques-de-base-quotidiennes»; espejo `BASE/QUOT`. LO 2.0 | **Descargado; nieve auditada** |
| SIM / SAFRAN-ISBA | Modelo de superficie | 1958 → | ~8 km | Forzamiento y balances | data.gouv.fr «donnees-changement-climatique-sim-quotidienne». LO 2.0 | Verificado (no es de acceso restringido) |
| Ransol-FEDA 99130004 | Observación manual | 1934–2002 | 1.641 m, diaria | Tx/Tn, P, **espesor** | meteo.ad (ficha de estación); datos por petición | Verificado; desde 2003 la automática no lista la nieve |
| Engolasters / FEDA Central | Observación | 1934 → | Estación | T/P; nieve sin confirmar | feda.ad | Inicio verificado; continuidad nival no |
| CLIM'PY Andorra | Homogeneización + reconstrucción | Históricas; nieve 1980–2016 rellenada con SAFRAN-Crocus | Estaciones | T/P y nieve | AR+I (petición) | Etiquetar como «observación + reconstrucción», nunca como observación pura |
| Núria manual (AEMET) | Observación | 01-02-1985 → | 1.970 m, a las 08 h | Espesor | InfoGruixNEU del ICGC (solo gráficos) | Verificado; antes de 1985 no localizado |
| ICGC (BPA, boletines) | Observación / documentación | Finales de 1986 → | Pirineo catalán | Nieve, aludes, perfiles | ICGC (petición) | Verificado; NIVOBS 1985–86 pendiente |
| XEMA (Meteocat) | Observación automática | 2009–2026 en uso | Estación | Espesor, P, T | API Meteocat (clave) | En uso desde la fase 01 |
| CADTEP (Meteocat) | Observación homogeneizada | 1950 → | Diaria / mensual | T/P (sin nieve) | meteo.cat | Verificado |
| ERHIN (MITECO/CHE) | Observación | Campañas desde finales de los años 80 | Pértigas / cuencas | Espesor, densidad, VAFN | Por petición | Verificado; sin datos brutos abiertos |
| ERA5-Land | Reanálisis | 1950 → | ~9 km | Nieve, SWE, T/P | CDS (cuenta) | Verificado |
| CERRA-Land | Reanálisis regional | 09-1984 → | 5,5 km | Nieve y superficie | CDS (cuenta) | Verificado; **la extensión a 1961 no se puede descargar al 27-11-2026** |
| CLIMPY v3 | Observación interpolada | 1981–2020 | 1 km diaria | P, Tmax, Tmin | zenodo.org/records/10972236 | Verificado; 1.343 estaciones de origen |
| Alonso-González et al. 2018 | Simulación nival | 1980–2014 | 10 km + bandas de 100 m | Espesor, SWE | ESSD | Verificado; no es observación |
| MODIS (Gascoin) / Theia | Satélite | 2000–2015 / era Sentinel-2 | 500 m / 20–30 m | Cubierta nival | Zenodo 162299 / Theia | Verificado; no da espesor |
| E-OBS v34.0e | Observación interpolada | 1950 – 30-06-2026 | 0,1° / 0,25° | T/P | ecad.eu | Verificado; sin nieve |
| ROCIO_IBEB | Observación interpolada | 1951–2022 | 5 km | P/T | AEMET | Verificado; no llega a 2026 |
| Iberia01 / STEAD | Observación interpolada | 1971–2015 / 1901–2014 | ~0,1° | P/T / Tx–Tn | Repositorios científicos | Verificado |
| CPC teleconexiones | Índice | 1950 → | Mensual | NAO, EA, EA/WR, SCAND… | NOAA | Verificado |
| SSWC (NOAA) | Catálogo | Hasta 2023 (tabla ampliada) | Evento | Calentamientos estratosféricos súbitos mayores | csl.noaa.gov/groups/csl8/sswcompendium/majorevents.html | Verificado; 2024–26, por calcular |
| WeMO (UB) | Índice | Serie larga | Diaria / mensual | WeMOi | UB | Concepto verificado; fechas del fichero pendientes (el servidor devolvía error) |
| OPCC / Pyrenees4Clima | Síntesis | Actual | Pirineos | Indicadores | OPCC | Resultados de 2026; el nuevo informe integral sigue en preparación |

## Independencia de las anclas

S2M asimila observaciones meteorológicas y nivológicas del entorno. SAFRAN usa la red nivo y las estaciones de Météo-France, y NIVOMET aporta observaciones españolas y andorranas. Por eso **una correlación alta entre S2M y una estación que entra en el análisis infla la confianza**. En SEPI, las anclas de Météo-France y las nivosas se tratan como **observación posiblemente asimilada**, y no como validación independiente. No se ha comprobado cuáles entran realmente en SAFRAN cada año: es un dato UNKNOWN que habría que pedir al CNRM-CEN. Las anclas más independientes son las que no pertenecen a la red francesa: XEMA, Núria y, si se obtiene, Ransol 1934–2002. Aun así, pueden entrar vía NIVOMET.

## Adquisición pendiente (por orden de valor para 1968–1984)

1. **SMN Andorra / FEDA / AR+I:** Ransol diaria original 1934–2002 con espesor de nieve; inventario de variables de Engolasters y Central; CLIM'PY con una marca que distinga observado, interpolado y reconstruido.
2. **AEMET Catalunya:** Núria antes del 01-02-1985, La Molina y Puigcerdà/Llívia con campos de nieve originales y metadatos.
3. **ICGC:** inventario cronológico de NIVOBS (altas y bajas por observador y variable) y diarios de Núria.
4. **MITECO/CHE:** tabla histórica por pértiga (fecha, cota, espesor, densidad, SWE) con coordenadas.
5. **EDF-DTG, SHF y dominios esquiables:** primero el inventario (código, coordenadas, variable, método, fechas). Hasta tenerlo no se les atribuye cobertura.
6. **CNRM-CEN:** qué estaciones se asimilan en SAFRAN para el Pirineo oriental y en qué años, necesario para separar anclas independientes de asimiladas.
7. **Con cuenta o clave, que gestiona el titular y que nunca va al repositorio:** CDS (CERRA-Land para la prueba de 2002, ERA5) y AEMET OpenData.

## Huecos sin solución en abierto

- **Vertiente catalana (Cerdanya–Ripollès–Núria–Cadí), 1968–1984:** no hay serie diaria de espesor abierta y comprobada.
- **Estaciones de esquí francesas antes de 1996:** sus observaciones no están publicadas.
- **Toda la cordillera:** no existe un espesor de nieve homogeneizado y abierto.
