# NEXUS · Revisión de producto y diseño de Pirineo

## Mandato y límites

Iniciativa: hacer comprensible y utilizable la consola del Pirineo en móvil y escritorio sin desvirtuar la evidencia meteorológica. El propietario de producto y responsable de decisiones es Javier Peiró. El encargo de revisión y la implementación reversible derivan de su instrucción; la existencia de un perfil no concede permisos ni autoridad adicionales.

Adaptación del runbook **Startup MVP** de [Ante — NEXUS](https://github.com/bionic0x/Ante-agency-agents/tree/9c54ba227875633068e4eee919770b324b745d9c), fijado al commit `9c54ba227875633068e4eee919770b324b745d9c`. Alcance: revisión de producto, interfaz, experiencia, identidad gráfica, accesibilidad y claridad de datos del Pirineo. No se establece una duración ni una meta numérica de validación sin datos. No se alteran fuentes, avisos, umbrales, modelos ni disponibilidad de publicación por el mero rediseño.

**Objeto:** que una persona encuentre lugar, hora, aviso oficial, condiciones observadas y pronóstico con sus fuentes y limitaciones. **No-objeto:** maximizar secciones, novedad visual o apariencia de precisión. **Resultado mínimo:** problemas priorizados a partir de capturas, propuesta coherente, cambios verificables y revisión independiente de regresiones y límites; las pruebas con usuarios reales siguen pendientes hasta realizarse.

**Hipótesis:** una jerarquía por tarea y por momento permitirá localizar información más fácilmente. Es hipótesis, no resultado medido. **Refutación:** si usuarios no encuentran la información prioritaria o confunden avisos, mediciones y estimaciones, revisar la solución. **Alternativa:** la dificultad puede estar en datos ausentes o demasiado antiguos y no resolverse con diseño. Conservar lo que ya funciona y mantener `UNKNOWN` visible.

## Coordinación y entregas

| Rol de Codex | Función | Entrega |
|---|---|---|
| `nexus_assurance` | Objetivo, límites y coherencia | Registro de decisión y condiciones de parada |
| `nexus_coordinacion` | Alcance, dependencias y archivos | Plan y síntesis sin escrituras simultáneas |
| `nexus_arquitectura_ux` | Arquitectura de información | Flujos y navegación por tareas |
| `nexus_investigacion_ux` | Revisión basada en evidencia | Hallazgos con captura, ubicación y severidad |
| `nexus_diseno_ui` | Interfaz y estados | Jerarquía, componentes y respuesta móvil |
| `nexus_marca` / `nexus_grafico` | Identidad, tipografía y tono | Propuesta de lenguaje visual territorial |
| `nexus_frontend` | Implementación acotada | Código y pruebas de regresión |
| `nexus_verificacion` | Cuestionamiento independiente | Contraste de evidencia, límites y verificación |

Los roles trabajan bajo coordinación del agente principal, con máximo de concurrencia establecido por el host; pueden agruparse en una misma tarea si el entorno no admite más agentes. La auditoría debe partir de capturas reales y distinguir evidencia, hipótesis y pruebas pendientes. El agente de verificación no debe dar por validadas afirmaciones no medidas ni revisar solo cambios que él mismo produjo. El registro asociado es [`NEXUS-PIRINEO-CLAIMS.json`](NEXUS-PIRINEO-CLAIMS.json).

**Criterio de pausa:** si se pierde trazabilidad de fuente o hora, se confunde un dato modelizado con una observación o un aviso oficial, se altera semántica de riesgo, o una comprobación falla, corregir o aislar el cambio antes de publicarlo. La accesibilidad, el contraste y el funcionamiento real de móvil requieren validación; no se dan por probados por el mero hecho de instalar perfiles. El propietario conserva cualquier decisión material y la aceptación de riesgos.

## Instalación y procedencia

El conversor y el instalador originales se ejecutaron con `--tool codex` y una selección explícita de nueve perfiles. Los archivos instalados en `.codex/nexus/` conservan las instrucciones generadas, con un contexto adicional para MeteoPortinatx; los campos de nombre y descripción se declaran en `.codex/config.toml`. Los siete perfiles previos se mantienen. Licencias y atribución: [MIT de AgentLand](nexus-LICENSE.txt) y [avisos de terceros, incluido OpenClaw Community](nexus-THIRD-PARTY-NOTICES.md). La fuente de `brand-designer` es `design/openclaw-brand-designer.md`; el resto usa los perfiles `design-*`, `engineering-frontend-developer`, `testing-reality-checker`, `agents-orchestrator` y `specialized-strategic-assurance-lead` del commit fijado.

Esto configura perfiles para **sesiones Codex compatibles y proyectos de confianza**. Ni el instalador ni los archivos convocan agentes, ejecutan NEXUS Relay, prueban compatibilidad en todos los hosts o crean procesos persistentes. No se ha desplegado Relay: su documentación lo describe como piloto local con límites y requisitos propios. El uso de los perfiles durante una sesión depende del host y de las autorizaciones disponibles.
