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

**Ninguna fila de esta tabla está verificada contra el código fuente del repositorio.** Ubicación, función y estado proceden de fragmentos y páginas de terceros (blogs, documentación espejo, foros) listados en «Fuentes»; no se ha leído directamente `NousResearch/hermes-agent` (ver «Lo que NO queda demostrado»). La ejecución original (gpt-researcher) no registró, por fila, cuál de las 33 URL de «Fuentes» sustenta cada dato aislado: por eso la columna «Fuente por fila» se declara **ND (no determinada)** en las once filas, en vez de inventar una atribución URL-a-fila que no se puede sostener con lo que quedó registrado.

| Componente | Ubicación (según fragmentos, no verificada) | Función (según fragmentos) | Estado (según fragmentos, no verificado) | Fuente por fila |
|---|---|---|---|---|
| **AIAgent** | `run_agent.py` | Bucle principal: orquestación, prompt, herramientas, reintentos, persistencia | Implementado | ND |
| **skill_manage** | `skills/skill_manage.py` | Crea/actualiza/borra las habilidades propias del agente | Implementado | ND |
| **Curator** | `skills/curator.py` | Archiva habilidades de bajo valor | Implementado | ND |
| **Atropos** | `atropos/` | RL para entrenar la llamada a herramientas | Implementado | ND |
| **GEPA Optimizer** | `evolution/gepa.py` | Evolución genético-Pareto de habilidades, descripciones de herramientas y prompt a partir de trazados de ejecución | Implementado | ND |
| **Batch Runner** | `batch_runner.py` | Ejecuta el agente en paralelo y guarda trayectorias (harness de evaluación) | Implementado | ND |
| **Trajectory Saving** | `agent/trajectory.py` | Guarda conversaciones (formato ShareGPT) como datos para el aprendizaje | Implementado | ND |
| **RL Environments** | `environments/` | Entornos de refuerzo reutilizables como funciones de fitness | Implementado | ND |
| **Darwinian Evolver** | `evolution/darwinian.py` | Evolucionaría el código de las herramientas | Planificado | ND |
| **Continuous Improvement Loop** | `improvement/pipeline.py` | Integraría los componentes anteriores en una mejora continua | Planificado | ND |
| **Memory Layers** | `~/.hermes/*.md`, SQLite | Memoria persistente entre sesiones; no decide, solo almacena | Implementado | ND |

**ND = no determinado**: no queda registro, en la ejecución original ni en esta corrección, de qué fragmento concreto (de cuál de las 33 URL listadas en «Fuentes», con qué fecha) sustenta la ubicación, la función o el estado de esa fila en particular. Ubicación, función y estado son, como conjunto, lo que describen los fragmentos y páginas de terceros citados en «Fuentes»; pero no puede afirmarse cuál URL concreta sustenta cuál fila sin verificarlo de nuevo contra esas fuentes, verificación que esta corrección no realiza (ver «Lo que NO queda demostrado»).

Ningún componente se llama literalmente «Control». Según los fragmentos consultados —no verificados directamente en el código—, el mejor candidato es **GEPA Optimizer**, al que esas fuentes describen como ya implementado (no planificado): sería el único que modifica el comportamiento del propio agente (habilidades, herramientas, prompt) a partir de sus propias ejecuciones. Las mismas fuentes describen a `AIAgent` como controlador del bucle de *ejecución*, no de la auto-mejora, y a `Continuous Improvement Loop` como mejor encaje conceptual pero marcado como planificado, no como código existente. Ninguna de estas tres afirmaciones de estado —que GEPA esté implementado, que `AIAgent` no decida mejoras, o que los dos bucles restantes estén solo planificados— se ha confirmado contra el repositorio; quedan como lo que dicen los fragmentos, no como hechos verificados.

### (b) Cómo funciona GEPA Optimizer

GEPA Optimizer toma como entrada los trazados de ejecución que el agente guarda de sus propias sesiones (habilidad/herramienta invocada, prompt usado, resultado) y los usa como señal de fitness para una búsqueda evolutiva genético-Pareto: genera variantes de habilidades, descripciones de herramientas y secciones del prompt, y conserva las no dominadas en el frente de Pareto. **No se ha determinado, a partir de los fragmentos consultados, si el resultado se aplica automáticamente sobre los artefactos del agente o si solo se propone a la espera de aprobación humana**: los fragmentos describen que la búsqueda produce las variantes ganadoras, pero ninguno documenta ni confirma el paso final de aplicación, por lo que esa transición queda como no demostrada (ver «Lo que NO queda demostrado»).

### (c) Licencia y reutilización (veredicto incidencia #172)

Licencia **MIT**, que permite reutilizar, modificar y redistribuir el código —incluido GEPA Optimizer suelto— conservando aviso de copyright y licencia. El veredicto de la incidencia #172 («Hermes») es explícito: **no adoptar Hermes como núcleo de Sirius**, pero deja abierto que sea Worker externo, runtime de un perfil, fuente de skills reutilizables o referencia de implementación, con la salvaguarda de no entregarle memoria, estado, permisos ni el ciclo canónico de Sirius. Aplicado a GEPA Optimizer: la licencia no lo impide y el veredicto #172 lo permite como **fuente de skills reutilizables** o **referencia de implementación**, nunca como poseedor de memoria/estado/permisos/ciclo canónico (reservados al Motor de Trabajo). No se evaluó la viabilidad técnica de extraerlo del resto del framework.

## Lo que NO queda demostrado

- El código fuente de Hermes Agent no se verificó directamente; el informe se apoya en fragmentos y páginas de terceros citados en «Fuentes», no en lectura línea a línea del repositorio.
- **La atribución de la tabla de componentes es a nivel de conjunto, no por fila**: no queda registrado qué URL concreta de las 33 listadas sustenta la ubicación, función o estado de cada componente individual (columna «Fuente por fila» = ND en las once filas).
- Ningún componente localizado se llama literalmente «control»; GEPA Optimizer es la mejor coincidencia razonada, no una cita textual del propietario.
- No se confirmó si «Continuous Improvement Loop» y «Darwinian Evolver» ya existen en el repositorio a 2026-08-31, más allá de figurar como planificados en los fragmentos.
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
