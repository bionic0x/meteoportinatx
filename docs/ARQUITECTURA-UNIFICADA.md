# MeteoPortinatx Unified 0.5.1 — arquitectura y decisiones

**Fecha:** 2026-11-10. **Ámbito:** un proyecto, dos dominios meteorológicos, un ciclo de release.

## Contratos de seguridad y observación

- `src/portinatx_degen.py` 0.6.1 es el núcleo costero y biblioteca compartida. No se sustituye por el archivo adjunto 0.6.0 porque perdería el respaldo CET/CEST, las ventanas forenses de 23/25 h y los cambios de CAP. Conserva los tres ejes **aviso oficial / peligro observado / precaución propia**. Un modelo no se convierte en observación; un fallo de fuente no significa tiempo tranquilo.
- `src/pirineo.py` 0.3.0 consume utilitarios del núcleo para el dominio pirenaico. DEM Terrarium, nivel húmedo, cotas de copo/cuajado/acumulación, SLR Kuchera, foehn, inversión y avisos de montaña. Conserva su propia carpeta de datos, cadencia y etiqueta diagnóstica.
- `src/pirineo_meta.py` 0.3.0 crea la perspectiva 15 días por familia ECMWF/GEFS/ICON (no multiplica la independencia por número de miembros); diferencia de los deterministas GFS/IFS/ICON/AROME/AIFS. La capa se aísla del diagnóstico físico 0–72 h y de la jerarquía de seguridad. Los índices ENSO, NAO/AO, estratosfera y océano son **contexto fechado y no multiplicadores de probabilidades**. Sin ≥30 fechas verificadas, no se ajustan los pesos por skill.
- `src/nowcast.py` 0.5.1 actúa como orquestador; no aplica los umbrales de Ibiza a la montaña ni los de nieve a la costa. `PORTINATX_HOME` y `PIRINEO_HOME` siguen siendo independientes; el archivo `state.json` y el archivo de ciclos nunca se versionan.
- Los observatorios se sirven en `/portinatx/` y `/pirineo/`. Sus APIs son `/portinatx/api/{core,radar,series,atmos,sat,mar,modx,forense}.json` y `/pirineo/api/{core,dem,grid,series,extended}.json`; las rutas de lectura están enumeradas, no se sirven arbitrariamente archivos del disco.
- En local, el servidor escucha **solo** en 127.0.0.1. Solo acepta POST para `/[dominio]/api/refresh`, con verificación de Host y Origin; no expone credenciales. En hosting estático **no hay ejecución en el servidor ni actualización mediante el botón**; se precisa un colector programado con persistencia y publicación posterior.

## Interpretación de las fuentes de octubre 2026

1. informe histórico `seguimiento-dana-17-20-oct-2026.md` (no publicado) registra la evolución en tiempo real y sus hipótesis. NO se reescriben los juicios anteriores en retrospectiva.
2. informe histórico `calibracion-portinatx-dana-adam.md` (no publicado) contiene calibración tentativa con un solo episodio (n=2 días intensos). Sus factores son **hipótesis**, no parámetros generales de producción.
3. informe histórico `forense-dana-17-20-oct-2026.md` (no publicado) usa Previous Runs emitidos realmente, D0/D1/D2 y observaciones en hora local. Su comparación espacialmente apareada de modelos de mar con boyas (modelo/observación ~0,87–0,99) **corrige** la hipótesis inicial de infravaloración por 2–2,5×, que comparaba la bocana con boyas lejanas. No introducir factor de oleaje ×2.
4. La lluvia convectiva de una DANA apareció infrapronosticada en un punto; el régimen *DANA de levante* no debe heredarse como calibración universal para nieve de montaña, tormentas estivales ni mar. El motor solo muestra la corrección en Forense como experimental y evita modificar precaución/avisos.
5. especificación histórica `ESPECIFICACION-MOTOR-CONECTORES_v0.6.0.md` (no publicada) inserta fragmentos literales del código **0.6.0** y es una instantánea histórica, no la fuente de verdad vigente. La fuente ejecutable actual es `src/portinatx_degen.py` 0.6.1.

Los informes originales completos se conservan en el paquete de entrega, no se suben al repositorio público. Véase [síntesis forense pública](FORENSE-PUBLICO.md).

## Diagrama

```text
src/nowcast.py  (CLI, servidor localhost, contratos compartidos)
  ├── Portinatx 0.6.1
  │    ├── observación + radar/satélite + meteo marina + NWP/IA
  │    ├── 3 ejes de seguridad + CAP + forense por evento
  │    └── HOME/app/{core,radar,series,atmos,sat,mar,modx,forense}.json
  └── Pirineo 0.3.0
       ├── DEM/perfiles/observación montañosa/avisos
       ├── meta-ensamble 15d, contrarian, teleconexiones, Brier
       └── HOME/app/{core,dem,grid,series,extended}.json

Portadas independientes /portinatx/ y /pirineo/ ← portal común /
                                   ↓
scripts/build_site.py: valida ambas salidas + antigüedad, copia todo a staging,
                    reemplazo de site/ solo si todos los archivos son válidos
```

## Pruebas y pendientes antes de conectar hosting

- Pruebas sintéticas existentes del núcleo costero, Pirineo y metaanálisis: deben permanecer verdes. Las pruebas no demuestran fiabilidad meteorológica ni éxito de conexión en tiempo real.
- Suite `tests/test_unified.py`: rutas, claves, separación de estado, rechazo de JSON ausente/malformado/antiguo, actualización solo desde mismo origen, empaquetado y salida integrada.
- CI verifica pruebas Python 3.10 y 3.11, pruebas JS del puente, integridad SHA-256 y empaquetado. GitHub Pages ya tiene publicación programada y un backend Render Free está disponible en modo experimental.
- El archivo forense **no es durable** en Render Free: se requiere un almacenamiento externo independiente para conservar histórico y aprendizaje entre reinicios. Los avisos son los oficiales; las fuentes y la meteorología mantienen estados de frescura independientes. No subir ni `state.json` ni `config.env` ni datos sensibles.
- La web estática admite *solo* versiones de ciclos ya emitidos; por diseño no fabrica datos ante falta de conectores.
