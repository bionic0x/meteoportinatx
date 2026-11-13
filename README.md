# MeteoPortinatx

**Español** · [English](README.en.md)

### Del Mediterráneo al Pirineo. Una manera de mirar el tiempo más de cerca.

Una tormenta puede pasar a pocos kilómetros de Portinatx y cambiar el mar sin dejar lluvia en tierra. En la Cerdanya, una inversión térmica o unos cientos de metros de altitud pueden separar la lluvia de la nieve. **MeteoPortinatx nace para entender esas diferencias locales**, reunir la evidencia disponible y hacer visible lo que todavía no sabemos.

[**Explorar MeteoPortinatx**](https://bionic0x.github.io/meteoportinatx/) · [Portinatx](https://bionic0x.github.io/meteoportinatx/portinatx/) · [Pirineo](https://bionic0x.github.io/meteoportinatx/pirineo/) · [Vistas para decidir](https://bionic0x.github.io/meteoportinatx/decidir/) · [Documentación](docs/ARQUITECTURA-UNIFICADA.md)

> **Proyecto experimental.** Los diagnósticos no sustituyen los avisos oficiales de AEMET, Protección Civil, Meteocat, SMA o Météo-France. Un dato ausente no significa calma. El aprendizaje forense no modifica los avisos oficiales.

## Dos territorios, una mirada compartida

| 🌊 Portinatx e Ibiza | 🏔️ Pirineo oriental |
|---|---|
| Radar, lluvia, tormentas, viento, avisos y condiciones marinas para la costa norte de Ibiza. | Cerdanya, Capcir y Andorra: relieve, cotas, nieve, estaciones, modelos y ensembles. |
| La geografía de una cala importa: una célula cercana o un frente de racha pueden tener impactos distintos en pocos kilómetros. | El fondo del valle, las laderas y las divisorias no viven la misma meteorología. El perfil pirenaico excluye el módulo marino. |

Ambos perfiles comparten adquisición modular, diagnósticos, indicadores de cobertura e informes. El perfil atmosférico ya utiliza un único núcleo con controles de terreno y unidades en ambas consolas y en los paquetes de zona. Otros algoritmos especializados mantienen requisitos territoriales; [matriz de paridad](docs/PARIDAD-ALGORITMOS.md). La aplicación y la web están en **0.6.0**; los motores costero y pirenaico, en **0.6.1**. [Ver perfiles y zonas](docs/ZONAS-MODULARES.md).

## De la evidencia a la decisión

**Observar.** Consulta mediciones, radar, METAR y avisos, con su origen y antigüedad. Un dato viejo o inaccesible debe seguir siendo visible como incertidumbre, no como una medición nueva.

**Interpretar.** Compara modelos y ensembles con la geografía local. El relieve, la exposición y la distancia importan tanto como el valor de un mapa.

**Decidir.** La vista [«Decidir»](https://bionic0x.github.io/meteoportinatx/decidir/) organiza la información para cinco situaciones: vivienda junto a torrente, barca o amarre, segunda residencia, esquí y montaña, y análisis meteorológico. Separa avisos, observaciones y estimaciones y enlaza a las consolas completas. Es una ayuda de lectura: no da órdenes de evacuación ni de navegación. [Cómo funciona](docs/DECISION-P0.md).

**Aprender.** El archivo prospectivo experimental congela pronósticos antes del evento y permite contrastarlos después con observaciones comparables y calidad verificable. Registra también exclusiones e incertidumbre. Todavía no demuestra que las probabilidades estén calibradas ni que el archivo sea persistente por sí solo. [Protocolo forense](docs/FORECAST-LEDGER-P0.md).

## Explora las herramientas

- **Consolas territoriales:** una lectura científica de [Portinatx](https://bionic0x.github.io/meteoportinatx/portinatx/) y del [Pirineo](https://bionic0x.github.io/meteoportinatx/pirineo/), sobre el mismo núcleo compartido.
- **Planificador de rutas:** carga un GPX en el navegador y explora condiciones por tramo y hora. El recorrido permanece en el navegador. Sus límites y variables están documentados en [Rutas Pirineo](docs/RUTAS-PIRINEO.md).
- **Paquetes de zona:** prepara, verifica e instala capturas con datos, diagnósticos, cobertura y hashes; también puedes generar informes HTML sin conexión. [Guía de zonas](docs/ZONAS-MODULARES.md).
- **Contexto climatológico:** el proyecto incluye conocimiento con procedencia y herramientas experimentales para sidecars, sin confundir contexto con una observación o una alerta. [Catálogo de fuentes](docs/CATALOGO-FUENTES.md).

En **Atmósfera · Pirineo**, el perfil detallado compara puntos representativos de las vertientes norte y sur: perfiles térmicos, hodógrafa, cizalladura e indicadores por hora. Son campos modelizados; los niveles bajo terreno se excluyen y los campos no disponibles se muestran como `UNKNOWN`. Los índices experimentales no están calibrados en Pirineos.

## Fuentes y confianza

La consola pirenaica integra AEMET, Meteocat XEMA y Météo-France DPObs. Una publicación del 11 de noviembre de 2026 incluyó observaciones de las tres redes y del archivo horario francés; la disponibilidad posterior depende de los proveedores, las credenciales y la frescura de cada medición. Los visores de radar y satélite pirenaicos son externos: comprueba su cobertura y antigüedad. En RainViewer, la hora del mosaico no garantiza la hora de cada radar.

[**ClimayNievePirineos**](https://www.climaynievepirineos.com/estaciones/UsoYCaracteristicasCYNP.htm) es una red privada no oficial cuyo autor permite difundir datos citando la fuente o enlazando la estación. El artículo no establece una frecuencia máxima de consultas automáticas. El conector conserva actualmente un control de activación propio del proyecto: `permisos/cnp.json` o, solo en local privado, `CNP_PERMISSION_VERIFIED=1`; no es una prohibición expresada en el artículo. [Registro de condiciones](docs/CNP-PERMISO-20261111.md).

El manual describe la intensidad de la tabla general como **máximo diario**, no como intensidad actual. El parser de páginas individuales conserva el campo `intensidad_mmh`, cuya semántica necesita verificación antes de tratarlo como instantáneo. El manual de 2014 también describe posibles subestimaciones de lluvia y viento; son advertencias orientativas que dependen de la estación, no factores de corrección universales.

## Sensores y háptica del teléfono (experimental)

La ruta `/dispositivo/` ofrece vibración opcional al subir la señal del ciclo o perderse un diagnóstico y muestra sensores compatibles con el navegador. Barómetro, termómetro e higrómetro requieren un puente nativo externo que no se incluye. Las mediciones se mantienen en el dispositivo y caducan; activar altitud requiere permiso de geolocalización. Solo funciona con la página abierta y visible: **no es una alerta push ni vigilancia continua**. La ausencia de vibración no significa ausencia de peligro. [Contrato y límites](docs/DISPOSITIVO-SENSORES.md).

## En marcha en tu equipo

Requiere Python 3.10 o superior y biblioteca estándar. Algunas fuentes necesitan credenciales opcionales, que deben mantenerse fuera de Git.

```bash
python3 src/nowcast.py selftest
python3 src/nowcast.py serve --port 8787 --portinatx-interval 300 --pirineo-interval 10800
```

Abre [localhost:8787](http://localhost:8787/) y navega a `/portinatx/`, `/pirineo/` o `/decidir/`. El servidor local restringe la actualización al mismo origen; la API pública es de solo lectura.

Para trabajar con zonas y construir la aplicación:

```bash
python3 src/nowcast.py zone list
python3 src/nowcast.py zone plan portinatx
python3 src/nowcast.py zone plan pirineo
python3 src/nowcast.py zone fetch pirineo --output captura.zip
python3 src/nowcast.py zone inspect captura.zip
python3 src/nowcast.py zone report --pack captura.zip --output informe.html
python3 src/nowcast.py export
python3 scripts/build_site.py
python3 scripts/build.py
python3 scripts/integrity.py --check
```

También se pueden crear plantillas de perfiles, instalar paquetes y consultar evidencias con `zone template`, `zone install` y `evidence`. [Comandos y contratos](docs/ZONAS-MODULARES.md).

## Publicación, persistencia y límites

[GitHub Pages](https://bionic0x.github.io/meteoportinatx/) publica capturas generadas por Actions cada seis horas y al modificar fuentes. Esa cadencia **no equivale a vigilancia continua**. El despliegue exige datos recientes de ambos dominios y falla si faltan.

El [backend Render Free](https://meteoportinatx-backend-free.onrender.com/) es una vista previa de lectura: puede dormirse y su almacenamiento local es volátil. No hay disco persistente configurado. El puente web puede usar el backend mediante la variable pública `METEO_BACKEND_URL` y, si falla o mezcla generaciones, recurre al conjunto completo de archivos de Pages. Nunca pongas secretos en esa variable. [Guía del backend](docs/BACKEND-PERSISTENTE.md).

El ciclo supervisado para el archivo prospectivo de Portinatx incluye plantillas de systemd, pero requiere instalación en un equipo Linux con almacenamiento persistente y copias independientes. La presencia de las plantillas **no significa que esté programado ni activo**. [Instalación y límites](docs/FORECAST-LEDGER-P0.md).

## Por dentro

| Componente | Función |
|---|---|
| `src/portinatx_degen.py` | Motor costero: radar, observaciones, avisos, mar, modelos y forense privado. |
| `src/pirineo.py` y `src/pirineo_meta.py` | Motor de montaña: relieve, perfiles, nieve y ensembles. |
| `src/nowcast.py` y `src/nowcast_backend.py` | Orquestación, servidor local y backend de lectura. |
| `src/public_fetch.js` | Carga coherente por dominio y alternativa estática. |
| `src/route_engine.js` y `src/pirineo_ruta.html` | Planificador GPX privado en navegador. |
| `scripts/build_site.py`, `scripts/build.py` y `scripts/integrity.py` | Sitio, aplicación portátil e integridad SHA-256. |
| `tests/` | Regresiones sintéticas de motores, interfaces y contratos. |

CI comprueba Python 3.10 y 3.11, pruebas JavaScript, integridad y construcción de la aplicación portátil. Las pruebas sintéticas no calibran un pronóstico ni garantizan la disponibilidad de fuentes externas.

El repositorio también configura siete [divisiones de agentes Codex](docs/agency-agents.md): datos, geoespacial, backend, operaciones, calidad, interfaz y seguridad. Son perfiles para sesiones compatibles; no crean agentes persistentes ni programan trabajo por sí solos.

[Arquitectura](docs/ARQUITECTURA-UNIFICADA.md) · [Notas de versión](docs/RELEASE-NOTES.md) · [Evaluación y hoja de ruta](docs/EVALUACION-MODELO-USOS-POTENCIAL.md) · [Zonas modulares](docs/ZONAS-MODULARES.md)
