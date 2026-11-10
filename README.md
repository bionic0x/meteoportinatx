# MeteoPortinatx Unified · 0.4.0

**Un solo desarrollo, dos observatorios.** Válido para **Portinatx (Ibiza)** y **Pirineo (Andorra, Cerdanya, Capcir)**. Unifica la CLI, las vistas web, el empaquetado, las pruebas y la gestión de releases, sin mezclar las reglas de aviso de cada territorio.

> Estimación diagnóstica, no aviso oficial ni probabilidad calibrada. En Ibiza mandan AEMET y Protección Civil; en el Pirineo, AEMET/Meteocat, SMA, Météo-France y los boletines oficiales de aludes.

## Inicio rápido

Requiere Python **3.10+**, biblioteca estándar y conexión a Internet para el ciclo real.

```bash
# Ver ambos observatorios en un único servidor LOCAL; inicia dos recolectores.
python3 src/nowcast.py serve --port 8787 --portinatx-interval 300 --pirineo-interval 10800 --open
# Navegador: http://localhost:8787/

# Ejecutar una exportación de ambos dominios, sin interfaz
python3 src/nowcast.py export
# Solo uno de ellos
python3 src/nowcast.py export --domain pirineo

# Estado sin conexiones externas
python3 src/nowcast.py status
# 106+13 tests internos + pruebas del metaanálisis y test de integración
python3 src/nowcast.py selftest

# Genera un paquete único con el motor y ambas interfaces; sin desplegar
python3 scripts/build.py
python3 dist/MeteoPortinatx.pyz serve
```

El portal ofrece `/portinatx/` y `/pirineo/`. En el servidor local Portinatx admite «Actualizar ahora» y Pirineo también. El servidor permanece en **127.0.0.1** y rechaza intentos de refresh desde otro origen.

## Web estática para despliegue posterior

Primero deben existir los JSON exportados en los dos dominios. El generador valida JSON, inventario y **frescura del `core.issued` (24 h por defecto)**. Si falta un elemento, **no modifica `site/`**.

```bash
python3 src/nowcast.py export
python3 scripts/build_site.py
python3 -m http.server 8789 --directory site
# sitio: /, /portinatx/, /pirineo/
```

`site/` es un artefacto local que se ignora en Git. El despliegue web y la conexión con el colector remoto quedan **expresamente pendientes**; no hay workflow de deploy activo. Si un proveedor no responde, sus datos deben aparecer como `UNKNOWN` o error; no como 0 mm/0 cm.

## Arquitectura

| Archivo | Papel |
|---|---|
| `src/nowcast.py` | CLI y servidor común, estado de cada dominio, exportación dual |
| `src/nowcast_hub.html` | Portada con enlace a ambos observatorios y frescura del ciclo |
| `src/portinatx_degen.py` | Núcleo costero 0.6.1 con radar, avisos, modelo/IA, mar y forense |
| `src/portinatx_app.html` | Vista Portinatx: 3 ejes de aviso, radar, mar, modelos, forense |
| `src/pirineo.py` | Dominio montaña 0.3.0, DEM, nieve, perfiles, föhn, inversión |
| `src/pirineo_meta.py` | Horizonte 15 días, familias ENS/GEFS/ICON-EPS, contrarian, verificaciones |
| `src/pirineo_app.html` | Vista Pirineo: relieve, cotas, cortes, nieve, 15 días |
| `scripts/build_site.py` | Prepublicación web atómica, obligatoriamente dual |
| `scripts/build.py` | `.pyz` portable con ambos observatorios; PyInstaller opcional |
| `docs/FORENSE-PUBLICO.md` | Síntesis de anomalías y correcciones verificables sin datos domésticos privados |

Los historiales viven fuera del repositorio, en `PORTINATX_HOME` (por defecto `./portinatx_state`) y `PIRINEO_HOME` (por defecto `<PORTINATX_HOME>/pirineo`). `config.env`, `state.json`, `cycles/`, claves, cachés y `site/` están excluidos de Git.

## Modelo y límites científicos

Portinatx conserva los **tres ejes**: aviso oficial, peligro observado y precaución propia. La corrección por régimen (ej. DANA 17–20 octubre) es experimental y no altera la precaución. Las comparaciones de oleaje solo se hacen **modelo/boya espacialmente apareados**; no se aplica factor universal.

En el Pirineo, el 0–72 h usa **DEM Terrarium**, perfiles verticales, bulbo húmedo, tres cotas de nieve, relación nieve/agua tipo Kuchera, inversión y föhn. El 3–15 d añade datos de ensembles **ECMWF/GEFS/ICON** por familia, sin contar miembros como modelos independientes; deterministas IFS/GFS/AROME/AIFS se muestran por separado. ENSO, NAO/AO, vórtice y Atlántico son hipótesis contextuales verificadas, no multiplicadores de nieve. La calibración histórica necesita casos independientes; los valores no son probabilidades oficiales ni predicción de pistas abiertas.

Consulta [Arquitectura unificada](docs/ARQUITECTURA-UNIFICADA.md), [release notes](docs/RELEASE-NOTES.md) y [síntesis forense pública](docs/FORENSE-PUBLICO.md). Los documentos históricos originales se conservan en la entrega local, no en el repositorio público.

## Estado

**Código integrado para validación:** sí. **Conexión con hosting, credenciales y publicación web:** fase siguiente, no ejecutada en esta entrega.
