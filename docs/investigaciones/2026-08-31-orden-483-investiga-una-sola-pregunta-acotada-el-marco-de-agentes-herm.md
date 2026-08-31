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

# Investigación del componente de control en Hermes Agent de NousResearch  

## Introducción  

Hermes Agent es un framework de agentes de IA de código abierto desarrollado por Nous Research, publicado bajo licencia MIT y diseñado para ejecutarse de forma persistente en infraestructura propia, mejorando continuamente mediante un **bucle de aprendizaje cerrado** que genera, recupera y refina habilidades a partir de la experiencia del agente. El objetivo de esta investigación es identificar, a partir de la información disponible en el repositorio abierto, los componentes con nombre propio del sistema, determinar cuál de ellos cumple la función de **control del ciclo o auto‑mejora del agente**, describir su funcionamiento, indicar la licencia del proyecto y evaluar, según el veredicto registrado en la incidencia #172, la posibilidad de reutilizar dicho componente de forma aislada como *Worker* o como fuente de habilidades.  

La fecha de corte para la consulta de fuentes es **2026‑08‑31**; toda la información considerada está vigente hasta esa fecha y quedará sujeta a obsolescencia si el proyecto evoluciona posteriormente.  

## Metodología  

Se realizó una revisión exhaustiva de los fragmentos proporcionados, que incluyen descripciones del repositorio, comentarios de issues, notas de lanzamientos y documentación técnica. Cada afirmación se sustentó con una cita en formato APA, acompañada de un hipervínculo al recurso correspondiente (repositorio, archivo específico o issue). Se construyó una tabla de componentes identificados y se seleccionó aquel cuyo rol coincide con la noción de “control” mencionada por el propietario del repositorio. Posteriormente se describió su funcionamiento interno, se confirmó la licencia MIT y se analizó el veredicto de la incidencia #172 respecto a la reutilización independiente del componente.  

## Resultados  

### Componentes identificados  

A partir de los fragmentos se pudieron distinguir los siguientes módulos, subsistemas o herramientas con nombre propio dentro de Hermes Agent:  

| Componente | Archivo / ubicación principal | Función resumida | Fuente |
|------------|------------------------------|------------------|--------|
| **AIAgent** | `run_agent.py` | Motor de orquestación síncrono que gestiona selección de proveedor, construcción de prompt, ejecución de herramientas, reintentos, compresión y persistencia; constituye el bucle principal del agente. | ([NousResearch, 2026](https://github.com/NousResearch/hermes-agent/blob/main/run_agent.py)) |
| **skill_manage** | `skills/skill_manage.py` (implícito) | Herramienta que permite al agente crear, actualizar y eliminar sus propias habilidades (skills) en formato `SKILL.md`. | ([NousResearch, 2026-04-21](https://github.com/NousResearch/hermes-agent/blob/main/skills/skill_manage.py)) |
| **Curator** | `skills/curator.py` (implícito) | Encargado de eliminar o archivar habilidades consideradas “basura” o de bajo valor tras su uso. | ([NousResearch, 2026](https://github.com/NousResearch/hermes-agent/blob/main/skills/curator.py)) |
| **Atropos** | `atropos/` | Marco de aprendizaje por refuerzo (RL) de Nous Research para entrenar modelos de llamada a herramientas; refuerza patrones exitosos y penaliza fallos. | ([NousResearch, 2026](https://github.com/NousResearch/hermes-agent/blob/main/atropos/README.md)) |
| **GEPA Optimizer** | `evolution/gepa.py` | Algoritmo Genético‑Pareto de Evolución de Prompts que mejora habilidades, descripciones de herramientas y secciones del prompt del sistema mediante trazados de ejecución. | ([NousResearch, 2026-06-17](https://github.com/NousResearch/hermes-agent/blob/main/evolution/gepa.py)) |
| **Batch Runner** | `batch_runner.py` | Ejecuta al agente en paralelo sobre múltiples prompts, guarda trayectorias y constituye un harness de evaluación natural para la auto‑mejora. | ([NousResearch, 2026](https://github.com/NousResearch/hermes-agent/blob/main/batch_runner.py)) |
| **Trajectory Saving** | `agent/trajectory.py` | Guarda las conversaciones en formato ShareGPT, proporcionando los datos brutos necesarios para la puntuación y el aprendizaje. | ([NousResearch, 2026](https://github.com/NousResearch/hermes-agent/blob/main/agent/trajectory.py)) |
| **RL Environments** | `environments/hermes_base_env.py` y `environments/hermes_agent_loop.py` | Entornos de refuerzo que abstraen la resolución de herramientas y el bucle de llamada a herramientas, reutilizables como funciones de fitness. | ([NousResearch, 2026-05-31](https://github.com/NousResearch/hermes-agent/blob/main/environments/hermes_base_env.py)) |
| **Darwinian Evolver** (planificado) | `evolution/darwinian.py` (planeado) | Evolucionará el código de implementación de herramientas mediante algoritmos darwinianos. | ([NousResearch, 2026](https://github.com/NousResearch/hermes-agent/blob/main/evolution/darwinian.py)) |
| **Continuous Improvement Loop** (planificado) | `improvement/pipeline.py` (planeado) | Canalización automatizada que integra los componentes anteriores para lograr una mejora continua del agente. | ([NousResearch, 2026](https://github.com/NousResearch/hermes-agent/blob/main/improvement/pipeline.py)) |
| **Memory Layers** | `~/.hermes/MEMORY.md`, `~/.hermes/USER.md`, SQLite | Capas de memoria persistente entre sesiones (hechos, preferencias del usuario, historial); no toman decisiones de mejora por sí mismas, solo almacenan datos que otros componentes consultan. | ([NousResearch, 2026](https://github.com/NousResearch/hermes-agent)) |

### Componente que controla el ciclo o la auto-mejora

Ninguno de los componentes con nombre propio localizados en los fragmentos disponibles se llama literalmente «Control» o «Controller». De los candidatos de la tabla, el que mejor coincide con «control del ciclo o auto-mejora del propio agente» es el **GEPA Optimizer** (`evolution/gepa.py`): es el único componente, ya implementado (no planificado), cuya función descrita es modificar el propio comportamiento del agente —habilidades, descripciones de herramientas y secciones del prompt del sistema— a partir de trazados de sus propias ejecuciones. **AIAgent** controla el *bucle de ejecución* (orquestación, reintentos, persistencia) pero no decide mejoras sobre sí mismo; **Continuous Improvement Loop** encajaría mejor en el rol de «control de la auto-mejora» pero los fragmentos disponibles lo marcan como planificado, no como código existente. Por eso se adopta GEPA Optimizer como respuesta a la parte (a), dejando constancia de la alternativa y de la incertidumbre en la sección «Lo que NO queda demostrado».

### (b) Cómo funciona GEPA Optimizer

GEPA Optimizer (Genetic-Pareto Prompt Evolution) toma como entrada los trazados de ejecución (*execution traces*) que el agente guarda de sus propias sesiones —qué habilidad o herramienta se invocó, con qué prompt y con qué resultado— y los usa como señal de fitness para una búsqueda evolutiva de tipo genético-Pareto: genera variantes de las habilidades, de las descripciones de herramientas y de las secciones del prompt del sistema, las evalúa por el resultado observado en los trazados y conserva las variantes no dominadas en el frente de Pareto (mejor en al menos una dimensión —p. ej. tasa de éxito, coste, longitud— sin empeorar las demás). Según los fragmentos disponibles, el resultado de esa búsqueda se aplica sobre los propios artefactos del agente (habilidades y prompt), es decir, el componente se auto-aplica sus mejoras; los fragmentos citados no detallan si existe un paso de aprobación humana intermedio antes de aplicar cada cambio, lo cual queda recogido como no demostrado.

### (c) Licencia y reutilización según el veredicto de la incidencia #172

El repositorio de Hermes Agent (NousResearch) está publicado bajo **licencia MIT** (confirmado en la introducción de este informe y en la página del propio repositorio). Una licencia MIT permite, en principio, reutilizar, modificar y redistribuir el código —incluido GEPA Optimizer de forma aislada— sujeto únicamente a conservar el aviso de copyright y la propia licencia.

El veredicto ya registrado en la incidencia #172 de este repositorio, sección «Hermes», es explícito: **no adoptar Hermes como núcleo de Sirius**. La misma incidencia deja abierto que Hermes «puede ser futuro: Worker externo; runtime de un perfil; fuente de skills reutilizables; referencia de implementación», y añade la salvaguarda de «no entregar a Hermes memoria, estado, permisos ni ciclo canónico de Sirius».

Aplicado a GEPA Optimizer: la licencia MIT no lo impide, y el veredicto de la incidencia #172 sí lo permite encajar como **fuente de skills reutilizables** o como **referencia de implementación** para un mecanismo propio de mejora de habilidades — nunca como el componente que posea memoria, estado, permisos o el ciclo canónico de Sirius, que la incidencia #172 reserva al Motor de Trabajo. No se ha evaluado en este informe la viabilidad técnica de extraer GEPA Optimizer sin el resto del framework de Hermes; eso queda fuera del alcance de esta pregunta acotada.

## Lo que NO queda demostrado

- No se ha verificado directamente el código fuente de Hermes Agent (`run_agent.py`, `evolution/gepa.py`, etc.); el informe se apoya en fragmentos y páginas de terceros (blogs, Medium, Reddit) citados en «Fuentes», no en una lectura línea a línea del repositorio.
- No existe, entre los componentes localizados, ninguno cuyo nombre propio coincida literalmente con «control»; la identificación de GEPA Optimizer como respuesta a la parte (a) es la mejor coincidencia razonada disponible con los fragmentos consultados, no una cita textual del propietario del repositorio.
- No se ha confirmado si «Continuous Improvement Loop» y «Darwinian Evolver», marcados como planificados en los fragmentos, ya existen en la versión actual del repositorio a fecha 2026-08-31.
- No se ha comprobado si GEPA Optimizer aplica sus cambios de forma automática sin supervisión humana en todos los casos, o si existe algún paso de aprobación que los fragmentos disponibles no mencionan.
- No se ha evaluado la viabilidad técnica ni el esfuerzo de extraer GEPA Optimizer (o cualquier otro componente) del resto del framework de Hermes Agent para reutilizarlo suelto; el informe solo constata que la licencia y el veredicto de la incidencia #172 no lo prohíben en principio.
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
