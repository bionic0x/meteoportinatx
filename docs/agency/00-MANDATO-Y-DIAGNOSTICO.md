# MeteoPortinatx — Agency Agents / investigación integral (v0, 2026-11-11)

**Tipo de documento:** diagnóstico de investigación, NO especificación de producción ni dictamen científico acreditado.
**Base inspeccionada:** `bionic0x/meteoportinatx` `main` (unified 0.5.1), y perfiles de `msitarzewski/agency-agents` main, 11-11-2026.
**Alcance:** Portinatx/Islas Baleares y Pirineo/Cerdanya-Capcir-Andorra, con estudio de ampliación a terceros dominios.
**Estado del programa:** primera ronda de análisis y contratos entregados. Las personas/agentes independientes NO se han ejecutado en una plataforma multiagente; se han aplicado sus roles como *lentes de revisión* y se deja un runbook reproducible para una ejecución posterior. La revisión del Reality Checker es preliminar.

## 1. Conclusión ejecutiva

MeteoPortinatx tiene una arquitectura y una doctrina útiles —tres ejes de peligro, trazabilidad, rechazo de la falsa calma `UNKNOWN`, módulos de montaña y metaanálisis por familias—, pero **no ha demostrado habilidad predictiva fuera de muestra**. El motor costero no debe presentarse como un modelo de probabilidad meteorológica calibrado: `fuse()` en `src/portinatx_degen.py` calcula máximos observados/modelizados/institucionales, aplica confirmaciones y gates de excepción, y la desescalada usa decisiones gobernadas por histéresis. La variedad de entradas no equivale a independencia de fuentes.

La oportunidad principal no es competir con AEMET o ECMWF en generación de datos, sino **convertir mediciones, modelos, reportes de campo y errores históricos en decisiones explicables a escala local**. Dos productos distintos comparten datos pero no tienen la misma cadencia: (a) *brief de situación* de 6 horas de GitHub Pages; (b) *seguimiento en casi tiempo real* que requiere un colector despierto, datos de baja latencia y métricas verificadas. Render Free no cumple el requisito de permanencia y no retiene las series SQLite al dormirse.

## 2. Puntos observados en código (evidencia, no validación externa)

| Claim | Evidencia / archivo | Interpretación | Limitación |
|---|---|---|---|
| La fusión es una regla determinista de máximos y gates | `src/portinatx_degen.py:fuse()` | Conjunto de reglas de decisión, no ML calibrado | No se ha medido POD/FAR fuera de muestra |
| La precaución es independiente del aviso institucional y del peligro observado | `local_hazard_state()`, `fuse()`, `deescalation_decision()` | Arquitectura valiosa para explicar decisiones | Algunos estados dependen de notas manuales privadas |
| Se consultan 4 estaciones CNP aproximadas | `src/pirineo.py:CNP_STATIONS`, `src_cnp()` | Existe un parser HTML de tablas, no una API contrastada | Licencia y estabilidad de endpoints sin confirmar; acceso web dio 403 |
| La cota de nieve en tabla usa `prof.get('sur', [])` | `src/pirineo.py:build()`/`summarize_points(...)` | Riesgo de sesgo topográfico al extrapolar | Requiere validación espacial orientaciones N/S |
| `sea_model_check` compara máxima de vector modelizado con observaciones de boyas NE | `src/portinatx_degen.py:sea_model_check()` | No hay apareamiento estación-intervalo/forecast lead | No presentar como verificación de sesgo local de oleaje |
| Backend usa SQLite en Render Free | `src/nowcast_backend.py`, `render.yaml` | Pruebas de código y API, almacenamiento temporal | No existe archivo forense perdurable en producción |
| El puente web evita mezclar generaciones | `src/public_fetch.js` | Resuelve consistencia de partes del mismo ciclo | No garantiza precisión física ni siempre datos frescos |

**Discrepancia prioritaria:** la etiqueta UI `±17 km` debe contrastarse con distancias y radio real de estaciones; hay señales previas de pares a 27–30 km. No cambiar el texto sin prueba de distancia geodésica y contrato del algoritmo.

## 3. Roles utilizados para esta primera ronda

Los perfiles provienen del repositorio MIT `msitarzewski/agency-agents`, con instrucciones y checklists propios, pero los análisis de este documento **no se hacen pasar por ejecuciones paralelas reales de dichos agentes**.

1. **Statistician + Model QA Specialist:** hipótesis comprobables, verificación, calibración, skill vs baselines.
2. **Geographer + Spatial Data Scientist:** vecindad, representatividad, radar/advección, nieve por vertientes, oleaje.
3. **Spatial Data Engineer + Research Synthesist:** inventario y procedencia de fuentes, archivo de episodios y controles de acceso/licencia.
4. **Product Manager + UX Researcher:** casos de uso, interfaz de diez segundos, decisiones por perfil.
5. **Trend Researcher:** oportunidad de nicho, competidores, canal comunitario y riesgos de valor.
6. **Reality Checker:** rechaza las declaraciones no respaldadas y prohíbe activar integraciones no auditadas.

## 4. Decisiones de arquitectura

- **Verdad instrumental:** el aviso oficial es la fuente institucional; observaciones verificadas son señales físicas; mensajes de foro son pistas de campo no verificadas. No sumar votos, likes ni posts para elevar el peligro.
- **Dossier por episodio:** guardar previsión congelada de `issue_time`, parámetros, lugar, proveedor, horizonte y versión de código; luego añadir observación medida, con su tiempo y validación. El hecho de que un post sea posterior al episodio no lo convierte en dato de entrenamiento sin auditoría temporal.
- **Autenticidad espacial:** siempre punto/área, CRS, altitud, exposición, distancia, tiempo de medida y representatividad. No mezclar 72 h de un campo de modelo con última observación de una boya lejana.
- **Desacoplamiento:** los foros no entran en el motor de alertas. Un nuevo módulo genera registros `UNVERIFIED` y prohíbe entrenamiento/peso automáticamente, con posibilidad de revisión humana documentada.
- **Coste:** conservar infraestructura de coste contratado cero; no elevar Render Free, no contratar discos/servicios ni esconder un gasto de API bajo el término «gratis».

## 5. Hipótesis de producto a verificar

- H1: una ficha *¿qué está ocurriendo aquí?* con 3 respuestas (qué/por qué/frescura) se entiende en <=10 segundos en una prueba de usabilidad, mejor que el panel de unas 60 secciones.
- H2: conservar pronósticos preepisodio y verificar contra pluviómetros/observaciones reduce sobreajuste y permite demostrar mejoras; no se promete mejora sin backtest.
- H3: la evidencia comunitaria etiquetada reduce el tiempo hasta identificar un fallo de un proveedor, sin aumentar las falsas alarmas; requiere consentimiento/acceso y verificación independiente.
- H4: el valor para equipos de montaña/microclimas es investigación y análisis replicable, no reemplazo de los servicios oficiales o aval operativo de seguridad.

## 6. Entregables de esta rama

- `01-MODELO-Y-VERIFICACION.md` — auditoría operativa, esquema de benchmark, plan de calibración.
- `02-EPISODIOS-Y-COMUNIDAD.md` — ingestión comunitaria permitida y archivo forense independiente.
- `03-USOS-Y-POTENCIAL.md` — producto, segmentos, KPI, secuencia de inversión.
- `04-ROSTER-Y-HANDOFFS.md` — roles Agency Agents, prompts, contratos y gates.
- `05-REALITY-CHECK.md` — dictamen escéptico y pendientes de validación.
- `06-FUENTES-Y-LICENCIAS.md` — fuentes externas, permisos y estado de acceso.
- `src/episode_evidence.py` + `tests/test_episode_evidence.py` — prototipo **manual, desconectado de la API** para testear privacidad, normalización e idempotencia de reportes de comunidad.

**Puertas de salida:** CI PASS es condición necesaria, no suficiente. Merge/despliegue/integración pública requieren revisión independiente de fuentes, pruebas con casos reales y autorización explícita de cambios de impacto operativo.
