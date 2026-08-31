---
titulo: Investigación de la orden #483
fecha: 2026-08-31
autor: el investigador del motor (B1, ADR-099; configuración de ADR-098)
pregunta: >-
  Investiga UNA sola pregunta, acotada: el marco de agentes HERMES de NousResearch (repositorio abierto). (a) Enumera sus componentes o agentes con nombre propio y di cuál de ellos se dedica al control del ciclo o a la auto-mejora del propio agente — buscamos recuperar el nombre exacto de un componente que el propietario recuerda como «control» o parecido —; (b) describe en un párrafo cómo funciona ese componente (qué datos usa, qué decide, si se auto-aplica o propone); (c) di qué licencia tiene el proyecto y si ese componente podría reutilizarse suelto como Worker o fuente de skills, según el veredicto ya registrado en la incidencia #172 de este repositorio (Hermes no como núcleo). Si el Hermes de NousResearch no tiene tal componente, di cuál es el proyecto homónimo que sí lo tiene y responde sobre él, dejando clara la distinción. ENTREGABLE: una nota breve (una página) con fuentes citadas y fechadas y su caducidad declarada, como exigen las investigaciones de este repositorio. No modifiques nada fuera del documento de la investigación.
caduca_con:
  - los datos y las fuentes que cita el informe
  - la fecha de esta ejecución: es UNA pasada del investigador, no un hecho estable
estado: VIGENTE
---

# Investigación de la orden #483 — 2026-08-31

> Informe producido por el investigador del motor (gpt-researcher 0.15.1, `research_report`, NVIDIA + Tavily) a partir del `## Objetivo` de la incidencia. Las fuentes están al final; el número de fuentes es la misma unión que gobierna la medición del banco.

## Hermes Agent (NousResearch): el componente de control

Hermes Agent es un framework de agentes de código abierto de Nous Research, licencia MIT, diseñado para mejorar continuamente mediante un bucle cerrado que genera, recupera y refina habilidades a partir de su propia experiencia ([NousResearch, 2026](https://github.com/nousresearch/hermes-agent)). Fecha de corte de las fuentes: 2026‑08‑31; la información caduca si el proyecto evoluciona después.

### (a) Componentes con nombre propio

**Ninguna fila de esta tabla está verificada contra el código fuente del repositorio ni contra una fuente registrada propia.** La ejecución original (gpt-researcher) no registró, por fila, cuál de las 33 URL de «Fuentes» sustenta cada dato aislado, y ninguna de esas 33 fuentes nombra explícitamente —en el título o la URL ya citados en «Fuentes»— la ubicación, función o estado de un componente concreto: no hay, para ninguna fila, una excepción atribuible que aplicar. Por eso **ubicación, función, estado y fuente se declaran ND (no determinado)** en las once filas, en vez de inventar una atribución que no se puede sostener con lo que quedó registrado. Solo el nombre de cada componente se conserva: es la pista que esta investigación logró recuperar, no un dato verificado (ver «Lo que NO queda demostrado»).

| Componente | Ubicación | Función | Estado | Fuente por fila |
|---|---|---|---|---|
| **AIAgent** | ND | ND | ND | ND |
| **skill_manage** | ND | ND | ND | ND |
| **Curator** | ND | ND | ND | ND |
| **Atropos** | ND | ND | ND | ND |
| **GEPA Optimizer** | ND | ND | ND | ND |
| **Batch Runner** | ND | ND | ND | ND |
| **Trajectory Saving** | ND | ND | ND | ND |
| **RL Environments** | ND | ND | ND | ND |
| **Darwinian Evolver** | ND | ND | ND | ND |
| **Continuous Improvement Loop** | ND | ND | ND | ND |
| **Memory Layers** | ND | ND | ND | ND |

**ND = no determinado**: no queda registro, en la ejecución original ni en esta corrección, de qué fragmento concreto (de cuál de las 33 URL listadas en «Fuentes», con qué fecha) sustenta la ubicación, la función o el estado de esa fila en particular, y ninguna de esas 33 fuentes nombra ese dato explícitamente en su título o URL. No puede afirmarse cuál URL concreta sustenta cuál fila sin verificarlo de nuevo contra esas fuentes, verificación que esta corrección no realiza (ver «Lo que NO queda demostrado»).

Ningún componente se llama literalmente «Control». El nombre que esta investigación recupera como pista es **GEPA Optimizer**: los fragmentos consultados (no verificados directamente en el código) lo asocian con la evolución de habilidades, herramientas y prompt a partir de las propias ejecuciones del agente, y describen a `AIAgent` más como controlador del bucle de *ejecución* que de la auto-mejora, y a `Continuous Improvement Loop` como mejor encaje conceptual pero sin confirmar si ya existe como código. Como ninguna fuente registrada permite atribuir por fila la ubicación, función o estado de estos componentes (ver tabla), esta identificación de GEPA Optimizer como el componente de «control» es una **pista recuperada, pendiente de verificación dirigida** contra el repositorio — no un hallazgo verificado. No puede afirmarse que GEPA Optimizer esté implementado, que `AIAgent` no decida mejoras, o que otros componentes estén solo planificados: son afirmaciones de los fragmentos consultados, no hechos confirmados en esta corrección.

### (b) Cómo funciona GEPA Optimizer

**Esto es lo que describen los fragmentos consultados, no un hallazgo verificado línea a línea contra el código** (la función de GEPA Optimizer figura como ND en la tabla de (a); ver «Lo que NO queda demostrado»). Según esos fragmentos, GEPA Optimizer tomaría como entrada los trazados de ejecución que el agente guarda de sus propias sesiones (habilidad/herramienta invocada, prompt usado, resultado) y los usaría como señal de fitness para una búsqueda evolutiva genético-Pareto: generaría variantes de habilidades, descripciones de herramientas y secciones del prompt, y conservaría las no dominadas en el frente de Pareto. **No se ha determinado, a partir de los fragmentos consultados, si el resultado se aplica automáticamente sobre los artefactos del agente o si solo se propone a la espera de aprobación humana**: los fragmentos describen que la búsqueda produce las variantes ganadoras, pero ninguno documenta ni confirma el paso final de aplicación, por lo que esa transición queda como no demostrada (ver «Lo que NO queda demostrado»).

### (c) Licencia y reutilización (veredicto incidencia #172)

Licencia **MIT**, que permite reutilizar, modificar y redistribuir el código —incluido GEPA Optimizer suelto— conservando aviso de copyright y licencia. El veredicto de la incidencia #172 («Hermes») es explícito: **no adoptar Hermes como núcleo de Sirius**, pero deja abierto que sea Worker externo, runtime de un perfil, fuente de skills reutilizables o referencia de implementación, con la salvaguarda de no entregarle memoria, estado, permisos ni el ciclo canónico de Sirius. Aplicado a GEPA Optimizer: la licencia no lo impide y el veredicto #172 lo permite como **fuente de skills reutilizables** o **referencia de implementación**, nunca como poseedor de memoria/estado/permisos/ciclo canónico (reservados al Motor de Trabajo). No se evaluó la viabilidad técnica de extraerlo del resto del framework.

## Lo que NO queda demostrado

- El código fuente de Hermes Agent no se verificó directamente; el informe se apoya en fragmentos y páginas de terceros citados en «Fuentes», no en lectura línea a línea del repositorio.
- **La atribución de la tabla de componentes es a nivel de conjunto, no por fila, y ninguna de las 33 fuentes nombra esos datos explícitamente por componente**: no queda registrado qué URL concreta sustenta la ubicación, función o estado de cada componente individual, por lo que las cuatro columnas —ubicación, función, estado y fuente— se declaran ND en las once filas; solo el nombre de cada componente se conserva, como pista recuperada por la investigación.
- Ningún componente localizado se llama literalmente «control»; GEPA Optimizer es la mejor coincidencia razonada, no una cita textual del propietario ni un hallazgo verificado: es una **pista recuperada, pendiente de verificación dirigida** contra el repositorio.
- No se confirmó si «Continuous Improvement Loop» y «Darwinian Evolver» ya existen en el repositorio a 2026-08-31, más allá de figurar como planificados en los fragmentos.
- **La verificación dato por dato (ubicación, función, estado de cada componente) queda fuera del alcance de esta incidencia**: requeriría una misión de investigación dirigida, futura, con el registro de fuente por fila como requisito explícito del encargo — algo que esta ejecución no tuvo.
- **No se ha comprobado si GEPA Optimizer aplica sus cambios de forma automática o si requiere aprobación humana**; los fragmentos consultados no documentan esa transición en ningún sentido.
- No se evaluó la viabilidad técnica ni el esfuerzo de extraer GEPA Optimizer del resto del framework para reutilizarlo suelto.
- Esta nota caduca con sus fuentes (ver cabecera): es una fotografía a 2026-08-31, no un hecho estable sobre un proyecto en desarrollo activo.

## Fuentes

- https://ajay-arunachalam08.medium.com/the-self-improving-ai-agent-hermes-agent-0e75d7e97a13
- https://blakecrosley.com/guides/hermes
- https://blogs.nvidia.com/blog/rtx-ai-garage-hermes-agent-dgx-spark
- https://dev.to/arshtechpro/hermes-agent-a-self-improving-ai-agent-that-runs-anywhere-2b7d
- https://dev.to/truongpx396/hermes-agent-deep-dive-build-your-own-guide-1pcc
- https://github.com/NousResearch/hermes-agent-self-evolution
- https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/skills.md
- https://github.com/NousResearch/hermes-agent/issues/337
- https://github.com/nousresearch/hermes-agent
- https://hackernoon.com/lang/es/hermes-agent-vs-openclaw-which-ai-agent-framework-wins-in-2026
- https://hermes-agent.ai/blog/self-improving-ai-guide
- https://hermes-agent.nousresearch.com/
- https://hermes-agent.nousresearch.com/docs
- https://hermes-agent.nousresearch.com/docs/
- https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
- https://hermes-agent.org
- https://hermes-agent.org/
- https://hermes-ai.net/
- https://mranand.substack.com/p/inside-hermes-agent-how-a-self-improving
- https://myclaw.ai/es/blog/hermes-agent
- https://mynextdeveloper.com/es/blogs/what-is-hermes-agent-and-how-does-it-compare-to-other-ai-tools
- https://saulius.io/blog/hermes-agent-self-improving-ai-architecture
- https://www.digitalapplied.com/blog/hermes-agent-v0-10-self-improving-open-source-guide
- https://www.hostinger.com/co/tutoriales/que-es-hermes-agent
- https://www.hostinger.com/tutorials/what-are-hermes-agent-skills
- https://www.hostinger.com/tutorials/what-are-hermes-agent-skills/
- https://www.nxcode.io/resources/news/hermes-agent-complete-guide-self-improving-ai-2026
- https://www.reddit.com/r/LocalLLM/comments/1t47ec0/has_anyone_here_explored_hermes_agent_by_nous/
- https://www.revolutioninai.com/2026/04/how-does-hermes-agent-work-explained.html
- https://www.turingpost.com/p/hermes
- https://www.webreactiva.com/blog/hermes-agent
- https://www.youtube.com/watch
- https://x.com/Saboo_Shubham_/status/2060032838720954635?lang=en
