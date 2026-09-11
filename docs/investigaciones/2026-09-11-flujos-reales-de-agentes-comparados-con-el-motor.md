---
titulo: Flujos reales de agentes de código, comparados con el motor de Sirius
fecha: 2026-09-11
autor: "Claude (claude.ai, con búsqueda web) a petición del propietario, con el prompt de la sesión de Claude Code; verificación de los ficheros citados por esa sesión el mismo día"
pregunta: >-
  Qué personas, equipos y repositorios muestran un flujo completo parecido al motor
  (orden, implementación por agente, revisión, corrección, fusión, registro, memoria
  compartida entre herramientas y bucle de aprendizaje), qué hacen que el motor no
  hace, y cómo resuelven la memoria común y los pendientes.
caduca_con:
  - "el contenido de los trece repositorios citados, verificado el 11-09-2026 en su último commit"
  - "la documentación de Supermemory y Mem0 sobre Claude Code, Codex y ChatGPT, que cambia cada pocas semanas"
  - "los artículos, vídeos y fechas de publicación, que esta sesión no pudo abrir"
estado: VIGENTE
---

# Flujos reales de agentes de código, comparados con el motor de Sirius

## Cómo llegó y qué se ha verificado

El propietario pidió el 11-09-2026 *«mirar cómo lo hacen otros, sacar ideas, mirar
su lógica»* antes de seguir. La sesión de Claude Code redactó el prompt; el
propietario lo ejecutó en claude.ai con búsqueda web y trajo el informe que va
íntegro al final. Esta sesión no tiene navegador, pero sí puede clonar
repositorios públicos, y eso es lo que comprobó:

- **Los trece repositorios citados existen y están vivos** (último commit entre
  el 23-01-2026 y el 11-09-2026) `[V, clonados el 11-09-2026]`.
- **Los dieciséis ficheros que el informe cita como evidencia existen** en la
  ruta indicada, y los pasajes que el informe atribuye a cada uno están ahí
  `[V]`: `skills/lfg/SKILL.md` y las guías `ce-compound` y `ce-compound-refresh`
  de Compound Engineering; `continuous_claude.sh` (con `SHARED_TASK_NOTES.md`,
  contexto de reparación de CI y de comentarios de revisión, y límites
  `MAX_RUNS`, `MAX_COST`, `MAX_DURATION`); `elixir/WORKFLOW.md` de Symphony (un
  «workpad» por incidencia con `Plan`, `Acceptance Criteria` y `Validation`, y
  adaptador de GitHub Issues); `docs/architecture.md` de Agent Orchestrator
  («Display status is never stored. It is computed at read time from durable
  facts») y su `AGENTS.md` con el incidente de macOS convertido en regla;
  `README.md` de Beads (sobre Dolt; «do not create MEMORY.md files»; «Do not use
  markdown TODO lists»); `CLAUDE.md` de Ralph; `AGENTS.MD` de agent-scripts;
  `examples/ci-failure-auto-fix.yml` (excluye forks y sus propias ramas
  `claude-auto-fix-ci-`); `docs/AGENT-SETUP.md` de Engram; `docs/intended-usage.md`
  de Gentle-AI.
- **Lo que cambia la investigación de la mañana** (la de memorias compartidas):
  `supermemoryai/codex-supermemory` documenta captura automática por hooks
  (`UserPromptSubmit` recuerda, `Stop` guarda, contenedor por repositorio) y
  Supermemory tiene una guía oficial **para ChatGPT Web**
  (`apps/docs/supermemory-mcp/chatgpt-web.mdx`) `[V]`. Mem0 documenta el plugin
  de Codex con hooks y aclara que en Codex Cloud solo queda el MCP directo, sin
  hooks (`docs/integrations/codex.mdx:66-84`) `[V]`, y no tiene guía de ChatGPT.
- **Lo que NO se ha podido verificar** `[H]`: los artículos, los vídeos, las
  fechas de publicación, la PR de BAML y el hilo de Boris Cherny. Se toman como
  lo que el informe dice de ellos, que él mismo marca como «relato» o «demo».

## Lo que el motor ya hace, punto por punto

| Lo que hacen ellos | Lo que hay en el motor | Estado |
|---|---|---|
| Devolver al agente los fallos de CI y los comentarios de revisión, con intentos limitados (Continuous Claude, `ci-failure-auto-fix.yml`) | `advance-sirius-after-quality.yml` aplica `sirius:repair-requested` cuando Quality falla; `review-sirius-work.yml` lo aplica con CHANGES_REQUESTED; `sirius_convergence.py` para el ciclo por la regla de las dos rondas | **Ya está** `[V]` |
| El estado se deriva de hechos duraderos, nunca de «ya terminé» (Agent Orchestrator) | Regla de `sirius_transition` (incidencia #50: el marcador no es prueba), reflector que lee GitHub, diario con `checksum_sha256` | **Ya está** `[V]` |
| Revisar exactamente la versión candidata (Gentle-AI) | Marcadores `<head>:<run>` (ADR-157, ADR-159); cifras ancladas al árbol (ADR-154) | **Ya está** `[V]` |
| Criterios de aceptación explícitos por tarea (Symphony) | Secciones obligatorias del cuerpo de la orden y `criterio_terminado` en cada WorkItem | **Ya está** `[V]` |
| Una sola fuente de instrucciones para Claude y Codex (agent-scripts) | `AGENTS.md`, y `CLAUDE.md` remite a él | **Ya está** `[V]` |
| Investigar y planificar antes de tocar código, y revisar el plan (HumanLayer) | Nota de arranque publicada antes del primer commit (ADR-001); `docs/investigaciones/` con caducidad | **Ya está** `[V]` |
| Reconciliación periódica de estados atascados (propuesta del informe) | `sirius_reconcile.sh` corre periódico: corrige dos casos inequívocos e informa el resto. Pero el reflector **no cierra** un encargo cuya incidencia se cerró sin etiqueta terminal (`reflect.py`, reglas 1 y 2): por eso `DESENLACES.md` enseña 21 encargos de agosto «activos» | **A medias** `[V]` |
| Aprendizaje en dos pasadas: capturar tras una solución verificada; revisar después lo capturado contra el código, con Keep/Update/Consolidate/Replace/Delete (Compound) | La mina es **un** informe (31-08-2026), sin pasada periódica; no se captura ninguna lección tras cada corrección; la caducidad existe para investigaciones y el estado SUPERADO para ADR, no para lecciones | **Falta** `[V]` |
| Un solo comentario de trabajo por incidencia, actualizado (el «workpad» de Symphony) | Un comentario por hecho, con marcador: avisos de estado, veredictos, reparto | **Distinto**, no peor: el nuestro es un historial; el suyo, un tablero. Se puede tener las dos cosas |
| Memoria compartida con captura automática en Claude Code, Codex CLI y ChatGPT (Supermemory) | Nada montado; decisión 11 de ADR-171 | **Falta**, con el proveedor ya identificado `[V]` |
| Registrar si la captura de memoria falló, no solo si el trabajo salió bien (los hooks de codex-supermemory salen sin interrumpir) | No aplica hasta montar la memoria | **Pendiente** |
| Tareas con dependencias y reclamación entre agentes (Beads, Gas Town) | Un encargo por incidencia, despachado por el motor; sin dependencias | **No hace falta** con un solo propietario y un encargo a la vez |

## Lo que se propone debatir, por orden de valor y coste

1. **Montar la captura con Supermemory** y exigirle la prueba mínima que el
   informe propone antes de darla por buena: guardar una decisión con
   identificador desde Claude Code; recuperarla desde Codex CLI, desde una tarea
   de Codex Cloud y desde ChatGPT; cambiarla diciendo qué sustituye; interrumpir
   una sesión y ver qué quedó. Reparto sin cambios: decisiones y documentos al
   repositorio con prueba; pendientes, contexto y preferencias a la memoria.
   Coste: minutos de montaje, una regla en `AGENTS.md`, y las dos comprobaciones
   del propietario (créditos del plan Free; si su ChatGPT admite conectores MCP).
2. **Cerrar el hueco del reflector**: cuando la incidencia de un encargo está
   cerrada en GitHub sin etiqueta terminal, el diario debería decirlo en vez de
   dejar el encargo «activo» para siempre. Toca la máquina de estados del motor
   (las órdenes anteriores prohibían «aristas nuevas»), así que es una decisión
   del propietario con ADR propio.
3. **La mina en dos pasadas**, copiando el criterio de Compound: tras cada
   corrección que termina en verde, capturar una lección solo si «sin este
   documento, otro volvería a cometer el error o a repetir la investigación»;
   cada pocas semanas, revisar las lecciones contra el código y mantenerlas,
   actualizarlas, consolidarlas, sustituirlas o borrarlas, con evidencia. Las
   lecciones que puedan hacerse cumplir con una prueba se convierten en prueba.
4. **Un tablero por incidencia** al estilo del workpad de Symphony: un
   comentario que el motor actualiza con plan, criterios y validación, además
   de los avisos por hecho que ya existen. Reduce lo que el propietario tiene
   que leer; toca los cuatro workflows críticos, así que va detrás de lo demás.
5. **Registrar el éxito o fallo de la captura de memoria** en el diario cuando
   la memoria esté montada: un hook que sale en silencio no es una captura.

Nada de esto se ha implementado. Es la lista para el debate que el propietario
pidió: «primero mirar, analizar, debatimos, implementamos y probamos».

---

## El informe, tal como llegó

# Flujos reales de agentes: comparación con tu motor de GitHub

Investigación cerrada el **11 de septiembre de 2026**. Ventana prioritaria: **11 de diciembre de 2025–11 de septiembre de 2026**.

**Los ejemplos más aprovechables para tu caso son Compound Engineering, Continuous Claude, Agent Orchestrator y Symphony.** Los dos primeros aportan ejecución, revisión y corrección; Compound añade aprendizaje documentado. Agent Orchestrator aborda el trabajo de vigilar agentes. Symphony publica un contrato especialmente claro para pasar de incidencia a trabajo revisado y cerrado. Mi orden pondera parecido y facilidad de aprovechar piezas en el motor que ya tienes, no popularidad. [Compound Engineering](https://github.com/EveryInc/compound-engineering-plugin), [Continuous Claude](https://github.com/AnandChowdhary/continuous-claude), [Agent Orchestrator](https://github.com/Untrivial-ai/agent-orchestrator), [Symphony](https://github.com/openai/symphony).

**No he verificado un ejemplo público que reúna todo tu ciclo**, incluida la entrada por voz, la captura automática de todas las sesiones de ChatGPT y Codex en la nube, la memoria común y una mina periódica que mejore el sistema sin mantenimiento del dueño. Esto describe el resultado de esta investigación, no demuestra que no exista.

He inspeccionado artículos, documentación, instrucciones, scripts y configuraciones publicados. No he ejecutado estos sistemas con cuentas de pago ni he visto íntegramente los vídeos. Una configuración pública permite comprobar qué está programado o exigido al agente; no demuestra que siempre lo cumpla. Distingo:

- **Código:** fichero o configuración pública inspeccionada.
- **Ejecución:** resultado público concreto comprobable, como una PR fusionada.
- **Relato:** lo cuenta el autor; no he reproducido la ejecución.
- **Demo:** existe una demostración enlazada; indico sus límites cuando los conozco.

Las fechas corresponden a la publicación indicada, no necesariamente al nacimiento del repositorio. **s. f.** significa que no he podido verificar una fecha absoluta de publicación. Los repositorios se han contrastado en su estado accesible durante esta investigación.

## 1. Once fuentes, ordenadas por parecido

| # | Quién, enlaces, fecha y formato | Qué enseña exactamente y evidencia | Las tres ideas que copiaría | Qué no aplica a tu caso |
|---|---|---|---|---|
| **1** | **Kieran Klaassen y Trevin Chow / Every — Compound Engineering.** [Repositorio](https://github.com/EveryInc/compound-engineering-plugin), [artículo de Kieran](https://every.to/p/compound-engineering-gets-an-upgrade). **29-05-2026; actualizado 09-07-2026.** Artículo, repo y demo. | **Código/instrucciones:** el flujo actual planifica, implementa, simplifica, revisa y registra aprendizajes. `/lfg` aplica correcciones, prueba, abre PR y sigue CI con reparaciones limitadas; deja la fusión pendiente. [Fichero real de lfg](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/lfg/SKILL.md). | **1)** Revisión seguida de reparación y nueva comprobación. **2)** Aprendizajes recuperables en `docs/solutions/`. **3)** Mantenimiento que contrasta esos aprendizajes con el código vigente. [Captura](https://github.com/EveryInc/compound-engineering-plugin/blob/main/docs/guides/ce-compound.md), [mantenimiento](https://github.com/EveryInc/compound-engineering-plugin/blob/main/docs/guides/ce-compound-refresh.md). | Es un conjunto de instrucciones y herramientas para agentes: hay que conectarlo con tu disparador de incidencias. No demuestra memoria integral entre tus tres servicios. Su autor conserva la elección inicial del producto y la comprobación de su uso al final. [Artículo](https://every.to/p/compound-engineering-gets-an-upgrade). |
| **2** | **Anand Chowdhary — Continuous Claude.** [Repo](https://github.com/AnandChowdhary/continuous-claude), [explicación con salida de una ejecución](https://anandchowdhary.com/open-source/2025/continuous-claude). **15-11-2025**, origen fuera de ventana; código actual revisado. Artículo y repo. | **Código + relato de ejecución:** automatiza ramas, PR, comprobaciones, revisión, reparaciones y fusión. Permite implementador y revisor de proveedores distintos, incluidos Claude y Codex. Publica el motor completo en [continuous_claude.sh](https://raw.githubusercontent.com/AnandChowdhary/continuous-claude/main/continuous_claude.sh). | **1)** Revisor separado y configurable. **2)** Devolver al agente tanto fallos de CI como comentarios de revisión. **3)** Separar la siguiente tarea, en `SHARED_TASK_NOTES.md`, del conocimiento duradero. [Script](https://raw.githubusercontent.com/AnandChowdhary/continuous-claude/main/continuous_claude.sh). | Su automatización incluye fusionar; tendrías que conservar tu aprobación final. Es un proceso ejecutable que requiere entorno y credenciales, no tu mismo disparador de Actions. Sus notas no sincronizan automáticamente ChatGPT. [Repo](https://github.com/AnandChowdhary/continuous-claude). |
| **3** | **Prateek Karnal — Agent Orchestrator**, publicado inicialmente en Composio. [Artículo](https://composio.dev/blog/the-self-improving-ai-system-that-built-itself), [repo actual](https://github.com/Untrivial-ai/agent-orchestrator). **25-02-2026.** Artículo, repo y demostración integrada. | **Relato detallado:** asigna tareas, observa CI y devuelve comentarios al agente correspondiente; el autor también describe retrospectivas automáticas. **Código actual:** el proyecto ha cambiado de propietario/ruta y fue reescrito; el entorno vigente usa un servicio Go y aplicación Electron. [AGENTS.md actual](https://github.com/Untrivial-ai/agent-orchestrator/blob/main/AGENTS.md). | **1)** Automatizar el transporte de errores y revisiones. **2)** Derivar el estado de hechos duraderos, no de «ya terminé». **3)** Registrar resultados de sesiones para detectar fallos del propio motor. [Artículo](https://composio.dev/blog/the-self-improving-ai-system-that-built-itself), [arquitectura vigente](https://github.com/Untrivial-ai/agent-orchestrator/blob/main/docs/architecture.md). | No copiaría las instrucciones antiguas de instalación como si describieran el repo actual. Las retrospectivas del artículo son un **relato**, no una mina vigente que haya auditado. La aplicación añade infraestructura que tu motor quizá ya resuelve. [AGENTS.md](https://github.com/Untrivial-ai/agent-orchestrator/blob/main/AGENTS.md). |
| **4** | **Equipo de OpenAI — Symphony.** [Repo](https://github.com/openai/symphony), [WORKFLOW.md real](https://github.com/openai/symphony/blob/main/elixir/WORKFLOW.md). **20-07-2026:** incorporación verificable del adaptador GitHub. Repo y demo. [Commit fechado](https://github.com/openai/symphony/commit/044f204f161038f8a12823bbf42f85f089fc77df). | **Código/instrucciones:** recoge incidencias, crea entornos separados y ejecuta Codex; el contrato publicado cubre implementación, revisión, retrabajo, aprobación y cierre. **Ya admite GitHub Issues**, además de Linear; el ejemplo de proceso sigue expresado en estados de Linear. [README técnico](https://github.com/openai/symphony/blob/main/elixir/README.md). | **1)** Un comentario de trabajo actualizado por incidencia. **2)** Criterios de aceptación y pruebas explícitos. **3)** Separar «listo para revisión» de «fusionado y cerrado». [WORKFLOW.md](https://github.com/openai/symphony/blob/main/elixir/WORKFLOW.md). | Es una excepción a tu preferencia por personas/equipos pequeños. Se presenta como proyecto experimental de ingeniería. Usa un servicio con Codex local mediante `app-server`, no demuestra Codex Cloud ni incluye tu mina. [Repo](https://github.com/openai/symphony), [README técnico](https://github.com/openai/symphony/blob/main/elixir/README.md). |
| **5** | **Ryan Carson / snarktank — Compound Product.** [Repo](https://github.com/snarktank/compound-product), [instrucciones del trabajador](https://github.com/snarktank/compound-product/blob/main/scripts/CLAUDE.md). **s. f.; consultado 11-09-2026.** Repo con scripts y configuración de ejemplo. | **Código:** informes diarios → prioridad elegida → especificación → tareas → iteraciones → PR. Publica `config.example.json`, `prd.json`, `progress.txt` y [loop.sh](https://github.com/snarktank/compound-product/blob/main/scripts/loop.sh). | **1)** Convertir señales operativas en una propuesta concreta. **2)** Descomponerla en tareas pequeñas verificables. **3)** Conservar progreso fuera de la conversación. [Repo](https://github.com/snarktank/compound-product). | Tú debes proporcionar la fuente de informes; no prueba que capture todos los fallos por sí solo. No verifiqué una revisión independiente completa ni una ejecución periódica pública. El bucle publicado invoca Amp o Claude y confía en el agente para las comprobaciones: no sustituye tu CI obligatorio. [Script](https://github.com/snarktank/compound-product/blob/main/scripts/loop.sh). |
| **6** | **Steve Yegge — Gas Town + Beads.** [Artículo](https://steve-yegge.medium.com/welcome-to-gas-town-4f25ee16dd04), [Gas Town](https://github.com/gastownhall/gastown), [Beads](https://github.com/gastownhall/beads). **01-01-2026.** Artículo largo y repos. | **Código + relato:** trabajadores separados, tareas persistentes, vigilancia, recuperación y cola de integración. Gas Town aporta orquestación; Beads aporta pendientes y dependencias. El Beads actual utiliza **Dolt**, no solamente el antiguo enfoque de JSONL en git. [Gas Town](https://github.com/gastownhall/gastown), [Beads](https://github.com/gastownhall/beads). | **1)** Tareas con dependencias y reclamación por un agente. **2)** Recuperar trabajo tras interrupciones. **3)** Integración central que verifica y devuelve cambios problemáticos. [Beads](https://github.com/gastownhall/beads), [Gas Town](https://github.com/gastownhall/gastown). | El propio Yegge cuenta que el sistema inicial requería intervención frecuente y era caro. Añadir otra base de pendientes junto a Issues puede duplicar tu trabajo. Beads desaconseja listas TODO y memoria paralelas en Markdown: choca con una instalación que trate `MEMORIA.md` como segundo registro editable. [Artículo](https://steve-yegge.medium.com/welcome-to-gas-town-4f25ee16dd04), [Beads](https://github.com/gastownhall/beads). |
| **7** | **Alan Buscaglia / Gentleman Programming — Gentle-AI + Engram. En español.** [Gentle-AI](https://github.com/Gentleman-Programming/gentle-ai), [Engram](https://github.com/Gentleman-Programming/engram), [vídeo del ecosistema](https://www.youtube.com/watch?v=UoS_LP-PCG8). **26-03-2026:** archivo del antecesor Agent Teams Lite; fecha absoluta del vídeo no verificada. [Aviso de sustitución](https://github.com/Gentleman-Programming/agent-teams-lite). | **Código/configuración:** instala agentes, memoria y un proceso de especificación, implementación y verificación. Publica [configuración de memoria por cliente](https://github.com/Gentleman-Programming/engram/blob/main/docs/AGENT-SETUP.md). El vídeo está identificado y enlazado por el autor; no lo he visto íntegro. | **1)** Instalación común que evita copiar configuraciones a mano. **2)** Protocolo explícito de guardar, buscar y recuperar memoria tras compactar. **3)** Una identidad estable del proyecto entre herramientas. [Uso previsto](https://github.com/Gentleman-Programming/gentle-ai/blob/main/docs/intended-usage.md), [configuración Engram](https://github.com/Gentleman-Programming/engram/blob/main/docs/AGENT-SETUP.md). | El uso previsto conserva aprobaciones en decisiones importantes. Su revisión RDD es opcional y no bloquea por sí misma commit, push o PR. No he verificado la sincronización completa con ChatGPT y Codex Cloud. [Gentle-AI](https://github.com/Gentleman-Programming/gentle-ai), [uso previsto](https://github.com/Gentleman-Programming/gentle-ai/blob/main/docs/intended-usage.md). |
| **8** | **Geoffrey Huntley — Ralph; implementación pública de Ryan Carson.** [Explicación original](https://ghuntley.com/ralph/), [snarktank/ralph](https://github.com/snarktank/ralph). **14-07-2025**, origen fuera de ventana; repo consultado actualmente. Artículo y repo. | **Código:** la técnica reinicia el agente en un bucle. La implementación de Carson utiliza un listado de historias, progreso persistente y reglas para comprobar, marcar y registrar cada tarea. No atribuyo ese repo a Huntley. [CLAUDE.md real](https://github.com/snarktank/ralph/blob/main/CLAUDE.md). | **1)** Una historia por iteración. **2)** Contexto nuevo con estado conservado en ficheros. **3)** Extraer patrones reutilizables, no copiar todo el diálogo a las instrucciones. [CLAUDE.md](https://github.com/snarktank/ralph/blob/main/CLAUDE.md). | Ralph por sí mismo no aporta incidencia, revisor independiente, GitHub Actions, sincronización entre servicios ni aprobación de fusión. Un mensaje de «completo» depende del agente: tu CI y el estado real de la PR deben seguir siendo la comprobación externa. [Técnica](https://ghuntley.com/ralph/), [repo](https://github.com/snarktank/ralph). |
| **9** | **Peter Steinberger — agent-scripts y su flujo personal.** [Artículo](https://steipete.me/posts/2025/shipping-at-inference-speed), [repo](https://github.com/steipete/agent-scripts), [AGENTS.MD real](https://github.com/steipete/agent-scripts/blob/main/AGENTS.MD). **28-12-2025.** Artículo y repo. | **Relato personal + código:** órdenes breves, agentes que ejecutan y prueban, instrucciones comunes y automatizaciones de desarrollo. El repo publica cómo compartir reglas entre Claude Code y Codex mediante archivos/enlaces comunes y sincronización de herramientas. [Repo](https://github.com/steipete/agent-scripts). | **1)** Una fuente común para las instrucciones. **2)** Documentación localizable por tarea. **3)** Dar al agente un modo de ejecutar y observar el resultado. [Repo](https://github.com/steipete/agent-scripts), [artículo](https://steipete.me/posts/2025/shipping-at-inference-speed). | En el artículo él mantiene criterio técnico, prueba el producto y dice no usar un gestor de tareas para ese trabajo personal. Eso no satisface tu necesidad de que alguien mantenga los pendientes por ti. Su configuración local no se convierte automáticamente en memoria de ChatGPT. [Artículo](https://steipete.me/posts/2025/shipping-at-inference-speed). |
| **10** | **Dex Horthy / HumanLayer — Advanced Context Engineering.** [Artículo](https://www.humanlayer.dev/blog/advanced-context-engineering), [fichero de investigación](https://github.com/humanlayer/humanlayer/blob/main/.claude/commands/research_codebase.md), [sesión de programación](https://www.youtube.com/watch?v=42AzKZRNhsk). **29-08-2025**, fuera de ventana. Artículo, vídeo, prompts y PR real. | **Ejecución verificable:** la [PR BAML #2259](https://github.com/BoundaryML/baml/pull/2259) existe y fue fusionada el **05-08-2025**. El artículo enlaza investigación, planificación e implementación. Eso prueba un resultado concreto, no autonomía completa. | **1)** Investigar antes de planificar cambios difíciles. **2)** Compactar lo relevante en documentos. **3)** Revisar el plan antes de multiplicar cambios incorrectos. [Artículo](https://www.humanlayer.dev/blog/advanced-context-engineering). | Su método depende de alguien capaz de detectar investigación o planes equivocados. Publica fallos reales de esa fase. Es útil para el interior de tu motor, menos para tu objetivo de no supervisar. [Artículo](https://www.humanlayer.dev/blog/advanced-context-engineering). |
| **11** | **Boris Cherny / equipo de Claude Code.** [Hilo original](https://x.com/bcherny/status/2007179832300581177?lang=en), [guía oficial](https://code.claude.com/docs/en/best-practices), [claude-code-action](https://github.com/anthropics/claude-code-action). **02-01-2026**, hilo; guía y repo vivos. Hilo, documentación y YAML. | **Código:** hay ejemplos públicos separados para invocar Claude, revisar PR y reparar CI. No son una copia verificable de todo el entorno personal de Boris. [claude.yml](https://github.com/anthropics/claude-code-action/blob/main/examples/claude.yml), [revisión](https://github.com/anthropics/claude-code-action/blob/main/examples/pr-review-comprehensive.yml), [reparación](https://github.com/anthropics/claude-code-action/blob/main/examples/ci-failure-auto-fix.yml). | **1)** Convertir comprobaciones necesarias en mecanismos ejecutables. **2)** Proporcionar pruebas que el agente pueda ejecutar. **3)** Prevenir que una reparación vuelva a disparar infinitamente al corrector. [Guía](https://code.claude.com/docs/en/best-practices), [YAML de reparación](https://github.com/anthropics/claude-code-action/blob/main/examples/ci-failure-auto-fix.yml). | Los ejemplos requieren composición y configuración. El reparador publicado excluye PR de forks y sus propias ramas de reparación; no sirve indiscriminadamente para cualquier incidencia pública. No aporta una memoria común con ChatGPT. [YAML](https://github.com/anthropics/claude-code-action/blob/main/examples/ci-failure-auto-fix.yml). |

### Vídeos y demostraciones: por dónde empezar

1. **Gentleman Programming, en español:** [El ECOSISTEMA de IA que le falta a tu agente | Engram + SDD + Skills](https://www.youtube.com/watch?v=UoS_LP-PCG8). La [publicación de Alan](https://es.linkedin.com/posts/alanbuscaglia_el-ecosistema-de-ia-que-le-falta-a-tu-agente-activity-7441271860966674433-oKHi) permite comprobar la atribución. No he verificado fecha absoluta ni cada paso mostrado.
2. **Dex Horthy:** [sesión de programación sobre context engineering](https://www.youtube.com/watch?v=42AzKZRNhsk), enlazada desde su [artículo](https://www.humanlayer.dev/blog/advanced-context-engineering). Es el conjunto más sólido de vídeo, prompts y cambio real enlazado que encontré; la fusión de la PR sí está comprobada.
3. **Symphony:** [demo en Vimeo](https://player.vimeo.com/video/1186371009?h=5626e4b899), enlazada en el [repo oficial](https://github.com/openai/symphony). La documentación describe seguimiento de trabajo y entrega de evidencias; no doy por observada una ejecución completa del vídeo.
4. **Compound Engineering:** [demo y materiales](https://github.com/EveryInc/compound-engineering-plugin/tree/main/assets/demo). El README declara que es una **recreación comprimida de dos sesiones reales**, con nombres y rutas cambiados. No es una grabación continua sin editar. [Declaración del proyecto](https://github.com/EveryInc/compound-engineering-plugin).

### Puntos de partida que comprobé y no pondría entre los once principales

- **Cline Memory Bank:** publica una estructura útil de documentos para contexto, decisiones y progreso, además de instrucciones de actualización. No muestra por sí sola el ciclo de incidencia, revisor, corrector y fusión, ni sincronización automática entre servicios. [Guía original](https://docs.cline.bot/best-practices/memory-bank).
- **Harper Reed:** su explicación del **16-02-2025** cubre conversación para especificar, planificación y generación de código; es anterior a la ventana y requiere intervención del dueño. No la presentaría como demostración del motor autónomo que buscas. [Artículo original](https://harper.blog/2025/02/16/my-llm-codegen-workflow-atm/).
- **Simon Willison:** su colección es útil para evaluar prácticas de agentes, pero es una colección de patrones, no la publicación de un único sistema que cubra todo tu ciclo. [Agentic Engineering Patterns](https://simonwillison.net/guides/agentic-engineering-patterns/).
- **Mem0 y Supermemory:** los trato a continuación como componentes de memoria. No los cuento como personas que demuestran todo el flujo de desarrollo.

## 2. Patrones que se repiten

No todos hacen todo esto, pero son las coincidencias más claras de la muestra:

- **Dejan estado fuera del chat.** Usan archivos de progreso, una incidencia o una base de tareas para que el siguiente agente pueda continuar. [Ralph](https://github.com/snarktank/ralph), [Symphony](https://github.com/openai/symphony/blob/main/elixir/WORKFLOW.md), [Beads](https://github.com/gastownhall/beads).
- **Dividen el trabajo y hacen explícito qué significa terminar.** Aparece como historia verificable, plan o criterios de aceptación. [Instrucciones de Ralph](https://github.com/snarktank/ralph/blob/main/CLAUDE.md), [instrucciones de Compound Product](https://github.com/snarktank/compound-product/blob/main/scripts/CLAUDE.md).
- **Devuelven errores al agente.** Automatizar esa devolución evita que el dueño actúe como mensajero entre CI, revisor e implementador. [Continuous Claude](https://github.com/AnandChowdhary/continuous-claude), [Agent Orchestrator](https://composio.dev/blog/the-self-improving-ai-system-that-built-itself).
- **La memoria útil es seleccionada y recuperable.** Guardan una solución, decisión o patrón; no se limitan a inyectar toda la bitácora en cada sesión. [Compound: captura](https://github.com/EveryInc/compound-engineering-plugin/blob/main/docs/guides/ce-compound.md), [HumanLayer](https://www.humanlayer.dev/blog/advanced-context-engineering).
- **La autonomía necesita límites y estados de excepción.** Hay presupuestos de reparación, bloqueos o revisión humana; «trabaja solo» no implica «todo acaba bien». [lfg](https://github.com/EveryInc/compound-engineering-plugin/blob/main/skills/lfg/SKILL.md), [Continuous Claude](https://raw.githubusercontent.com/AnandChowdhary/continuous-claude/main/continuous_claude.sh).

## 3. Lo que ellos hacen y tú no has descrito, paso a paso

No he inspeccionado tu repositorio porque no has facilitado su URL. Estas son **posibles diferencias respecto a tu descripción**, no carencias comprobadas de tu implementación.

| Paso de tu ciclo | Qué buscaría o añadiría en tu motor | Fuente concreta |
|---|---|---|
| **Orden** | Convertir la orden en criterios de aceptación y un plan recuperable. Si aparece trabajo fuera de alcance, abrir otra incidencia vinculada, sin ampliar silenciosamente la actual. La entrada por voz hasta la etiqueta no está demostrada en estas fuentes. | [WORKFLOW de Symphony](https://github.com/openai/symphony/blob/main/elixir/WORKFLOW.md). |
| **Implementación** | Ejecutar una unidad pequeña con estado persistente y comprobar que el siguiente intento continúa esa unidad o toma la siguiente. | [CLAUDE.md de Ralph](https://github.com/snarktank/ralph/blob/main/CLAUDE.md). |
| **Revisión** | Identificar exactamente qué versión se revisó. Gentle-AI congela el candidato antes de su revisión RDD; eso evita confundir una revisión antigua con la del cambio corregido. | [Gentle-AI](https://github.com/Gentleman-Programming/gentle-ai). |
| **Corrección** | Recoger automáticamente errores de CI y comentarios nuevos; limitar intentos y dejar una explicación del bloqueo cuando se agota el presupuesto. | [Motor Continuous Claude](https://raw.githubusercontent.com/AnandChowdhary/continuous-claude/main/continuous_claude.sh). |
| **Fusión** | Mantener tu aprobación y comprobar el resultado real antes de declarar la tarea cerrada. «PR preparada» debe ser un estado distinto de «incidencia resuelta». | [Contrato de Symphony](https://github.com/openai/symphony/blob/main/elixir/WORKFLOW.md). |
| **Registro** | Además de la bitácora, registrar hechos con identidad de tarea, PR y ejecución. El estado visible debe derivarse de esos hechos y poder recuperarse tras reiniciar. | [Arquitectura de Agent Orchestrator](https://github.com/Untrivial-ai/agent-orchestrator/blob/main/docs/architecture.md). |
| **Memoria** | Distinguir registro, resumen de continuidad y conocimiento duradero. Instalar mecanismos tanto de captura como de recuperación, con la misma identidad del repositorio en cada cliente. | [Supermemory para Codex](https://github.com/supermemoryai/codex-supermemory), [Engram por cliente](https://github.com/Gentleman-Programming/engram/blob/main/docs/AGENT-SETUP.md). |
| **Aprendizaje** | Hacer dos pasadas: extraer una lección tras una solución verificada; después revisar si las lecciones anteriores siguen siendo válidas. Una mina que solo añade texto acumula contradicciones. | [ce-compound](https://github.com/EveryInc/compound-engineering-plugin/blob/main/docs/guides/ce-compound.md), [ce-compound-refresh](https://github.com/EveryInc/compound-engineering-plugin/blob/main/docs/guides/ce-compound-refresh.md). |

**Mi adaptación para tu mina:** cada propuesta debería enlazar el fallo original, explicar la causa, proponer una modificación concreta y decir cómo se comprobará. Si la regla puede hacerse cumplir con una prueba, convertirla en prueba; si conserva una razón que el código no expresa, documentarla. Es una recomendación derivada del criterio de captura de [Compound Engineering](https://github.com/EveryInc/compound-engineering-plugin/blob/main/docs/guides/ce-compound.md), no una función que haya comprobado en tu motor.

## 4. Memoria común y pendientes que se mantengan solos

### 4a. Cómo comparten memoria entre herramientas

Hay que separar **las mismas instrucciones**, **el mismo almacén** y **la captura automática**. Un archivo común resuelve la primera parte. Un MCP da acceso a un almacén. Los hooks —acciones disparadas por eventos de la sesión— pueden capturar y recuperar información sin que tú lo pidas. El ejemplo de Mem0 distingue expresamente instalar su plugin de conectar solo el MCP. [agent-scripts](https://github.com/steipete/agent-scripts), [Mem0 para Codex](https://docs.mem0.ai/integrations/codex).

| Solución | Claude Code | Codex CLI | Codex en la nube | ChatGPT | Qué está comprobado y qué falta |
|---|---|---|---|---|---|
| **Archivos comunes en el repo** | Peter publica una referencia común para las reglas de Claude y Codex. | Codex tiene un mecanismo documentado de lectura de `AGENTS.md`. | Necesita recibir los archivos dentro de su entorno de tarea. | No he verificado que una conversación normal lea automáticamente esos archivos. | Compartir instrucciones no comparte por sí mismo las conversaciones. `MEMORIA.md` debe formar parte de un protocolo explícito de lectura. [Peter](https://github.com/steipete/agent-scripts), [documentación oficial de AGENTS.md](https://developers.openai.com/codex/guides/agents-md). |
| **Supermemory** | Plugin público con captura y recuperación. [Repo Claude](https://github.com/supermemoryai/claude-supermemory). | Hooks públicos para recuperar contexto al empezar/recibir una orden y guardar turnos completados. [Repo Codex](https://github.com/supermemoryai/codex-supermemory). | No he verificado captura automática equivalente del plugin local. | El proveedor documenta conexión MCP, autorización e instrucciones para usar memoria. [Guía ChatGPT](https://supermemory.ai/docs/supermemory-mcp/chatgpt-web). | Los plugins de código comparten contenedor por repositorio. En ChatGPT hay que apuntar al espacio correspondiente; conectar la cuenta no demuestra que todas las conversaciones se graben. [Contenedores](https://github.com/supermemoryai/codex-supermemory), [ámbitos MCP](https://supermemory.ai/docs/supermemory-mcp/mcp). |
| **Mem0** | Plugin documentado con captura automática y ámbito por repositorio. [Guía Claude](https://docs.mem0.ai/integrations/claude-code). | Plugin con hooks; el MCP directo carece de esos hooks. [Guía Codex](https://docs.mem0.ai/integrations/codex). | Su guía prescribe MCP directo y aclara que los hooks locales no se aplican a esos contenedores. | He verificado MCP alojado, pero no una guía equivalente que demuestre captura completa en ChatGPT. [MCP Mem0](https://docs.mem0.ai/platform/mem0-mcp). | La documentación distingue memoria de proyecto, personal y de sesión. Deben concordar sus identidades entre clientes; no basta el nombre comercial del servicio. [Ámbitos de memoria](https://docs.mem0.ai/integrations/claude-code). |
| **Engram / Gentle-AI** | Configuración y protocolo públicos. | Configura MCP e instrucciones para conservar memoria al compactar. | No he verificado una solución completa de captura/sincronización para tu uso en la nube. | No he verificado esa integración completa. | El flujo local documenta exportación a `.engram/` e importación en otra máquina; esos comandos son pasos adicionales si no se automatizan. [Configuración por cliente](https://github.com/Gentleman-Programming/engram/blob/main/docs/AGENT-SETUP.md), [sincronización](https://github.com/Gentleman-Programming/gentle-ai/blob/main/docs/intended-usage.md). |

**Supermemory ofrece la evidencia pública más directa para tu combinación Claude Code + Codex CLI + acceso desde ChatGPT.** Es una valoración de las fuentes localizadas, no una comparación de calidad, precio o fiabilidad de los servicios. Sus plugins documentan una identidad común basada en el remoto git; su MCP permite seleccionar el espacio. No he verificado que el espacio visible en ChatGPT coincida automáticamente con el contenedor de los plugins: esa unión debe comprobarse expresamente. [Plugin Claude](https://github.com/supermemoryai/claude-supermemory), [espacios MCP](https://supermemory.ai/docs/supermemory-mcp/mcp), [ChatGPT](https://supermemory.ai/docs/supermemory-mcp/chatgpt-web).

**Mem0 tampoco es «solo MCP» hoy:** documenta plugins con captura. Pero distingue claramente esa capacidad local de la conexión directa para Codex Cloud. No convertiría una demostración local en la promesa de que la nube registra lo mismo. [Claude Code](https://docs.mem0.ai/integrations/claude-code), [Codex y Cloud](https://docs.mem0.ai/integrations/codex).

Para tu caso, mi recomendación es conservar **Issues para pendientes, ADR para decisiones aceptadas y la bitácora para hechos**. `MEMORIA.md` puede seguir siendo una vista generada; el servicio de memoria puede ayudar a encontrar contexto y lecciones. Esto evita dar a dos agentes versiones editables e independientes del mismo estado. Es una propuesta mía apoyada en la separación entre hechos operativos y contexto de [Agent Orchestrator](https://github.com/Untrivial-ai/agent-orchestrator/blob/main/docs/architecture.md) y la memoria seleccionada de [Compound](https://github.com/EveryInc/compound-engineering-plugin/blob/main/docs/guides/ce-compound.md).

La prueba mínima que exigiría antes de elegir servicio es: guardar una decisión con un identificador único desde Claude, recuperarla desde Codex CLI, desde una tarea nueva de Codex Cloud y desde ChatGPT; cambiarla indicando qué sustituye y repetir la lectura. Después interrumpir una sesión y comprobar qué se conservó. Es una **prueba propuesta**, no una prueba que yo haya ejecutado.

### 4b. Dónde apuntan pendientes y cómo se cierran

| Sistema | Dónde quedan | Quién los mantiene y cómo termina el trabajo |
|---|---|---|
| **Symphony** | Gestor de incidencias y comentario de trabajo asociado. | El agente actualiza el plan y las comprobaciones; el contrato separa revisión, retrabajo y cierre después de integrar. El gestor sigue siendo el registro del estado. [WORKFLOW.md](https://github.com/openai/symphony/blob/main/elixir/WORKFLOW.md). |
| **Beads** | Base de tareas con dependencias y estados. | El agente crea descubrimientos, reclama trabajo disponible y lo cierra; cerrar un bloqueo permite que otras tareas queden disponibles. Beads mantiene las tareas; Gas Town aporta la ejecución y la integración. [Beads](https://github.com/gastownhall/beads), [Gas Town](https://github.com/gastownhall/gastown). |
| **Ralph / Compound Product** | Historias de `prd.json` y registro `progress.txt`. | El agente toma una historia pendiente, ejecuta comprobaciones y marca su resultado. Es un protocolo escrito para el agente, no una garantía externa de que todo lo declarado sea correcto. [Ralph: instrucciones](https://github.com/snarktank/ralph/blob/main/CLAUDE.md), [Compound Product: instrucciones](https://github.com/snarktank/compound-product/blob/main/scripts/CLAUDE.md). |
| **Continuous Claude** | Notas de continuidad, ramas y PR. | Cada sesión deja el siguiente trabajo; el motor recoge comprobaciones y comentarios y continúa las reparaciones según sus límites. Las notas no sustituyen el estado de GitHub. [Script completo](https://raw.githubusercontent.com/AnandChowdhary/continuous-claude/main/continuous_claude.sh). |
| **Peter, en el artículo de diciembre** | No describe un gestor formal para su trabajo personal. | Mantiene prioridades y decisiones él mismo. Es precisamente una parte que no copiaría para tu objetivo. [Artículo](https://steipete.me/posts/2025/shipping-at-inference-speed). |

**La pieza que añadiría a tu esquema es una reconciliación automática periódica:** comparar incidencias, PR y ejecuciones; cerrar lo realmente integrado, reactivar lo interrumpido y abrir incidencias para bloqueos o aprendizajes pendientes. Su propósito sería que ni tú ni una memoria semántica tengáis que mantener el estado a mano. Es una adaptación propuesta a partir de los estados derivados de [Agent Orchestrator](https://github.com/Untrivial-ai/agent-orchestrator/blob/main/docs/architecture.md) y el cierre explícito de [Symphony](https://github.com/openai/symphony/blob/main/elixir/WORKFLOW.md).

## 5. Fallos que reconocen y respuestas que publican

Distingo una corrección ya incorporada de una intención futura. Las consecuencias para tu motor son recomendaciones mías.

| Fuente | Fallo reconocido por la propia fuente | Qué cambió, recomienda o dejó pendiente | Consecuencia para ti |
|---|---|---|---|
| **Karnal / Agent Orchestrator** | El dueño acabó vigilando CI y copiando comentarios entre agentes. También relata trabajos que se desviaban del objetivo. | Automatizó la devolución de errores. En febrero dejó como trabajo futuro un control más estrecho durante la sesión y mejor escalado; no lo presento como terminado en esa fecha. [Artículo](https://composio.dev/blog/the-self-improving-ai-system-that-built-itself). | Registrar también cuándo el agente se desvía, no solo si al final pasa CI. |
| **Equipo actual de Agent Orchestrator** | Su `AGENTS.md` registra un incidente de publicación de macOS con varios responsables y artefactos divergentes. | Impone un único responsable de publicación y comprobación explícita de artefactos. Es una lección convertida en regla real del repo. [AGENTS.md](https://github.com/Untrivial-ai/agent-orchestrator/blob/main/AGENTS.md). | Buena muestra de «fallo → regla concreta» para tu mina. |
| **Steve Yegge** | En el lanzamiento cuenta correcciones duplicadas, trabajo y diseños perdidos, intervención frecuente y coste elevado. | Expone esas limitaciones; el artículo no demuestra que estuvieran resueltas. [Relato original](https://steve-yegge.medium.com/welcome-to-gas-town-4f25ee16dd04). | Copiar persistencia y recuperación antes de multiplicar agentes. |
| **Dex Horthy** | Una investigación descartó erróneamente un fallo real; otra tarea falló por investigar insuficientemente las dependencias. | Rehacer investigación y revisar su calidad antes de implementar. [Relato](https://www.humanlayer.dev/blog/advanced-context-engineering). | «Investigar primero» también necesita comprobación; un buen formato no garantiza una conclusión correcta. |
| **Compound Engineering** | Las soluciones guardadas pueden apuntar a rutas antiguas, contradecirse o recomendar prácticas ya inválidas. | Publica una pasada que conserva, actualiza, consolida, sustituye o elimina con evidencia; los casos ambiguos pueden quedar señalados. [ce-compound-refresh](https://github.com/EveryInc/compound-engineering-plugin/blob/main/docs/guides/ce-compound-refresh.md). | Tu mina debe mantener conocimiento existente además de producir propuestas nuevas. |
| **Gentleman Programming** | La distribución duplicada de Agent Teams Lite y Gentle-AI provocaba divergencia y copias manuales. | Archiva Agent Teams Lite y concentra la distribución en Gentle-AI. [Aviso del repo archivado](https://github.com/Gentleman-Programming/agent-teams-lite). | Una sola fuente para reglas compartidas; generar las adaptaciones de cada cliente. |
| **Engram / Gentle-AI** | Un mismo proyecto podía terminar con nombres distintos y memorias separadas. | Documenta detección desde el remoto git, normalización y consolidación de proyectos. [Uso previsto](https://github.com/Gentleman-Programming/gentle-ai/blob/main/docs/intended-usage.md). | La identidad del proyecto merece una comprobación automática. |
| **Supermemory para Codex** | Los hooks pueden fallar si el servicio no responde o falta autenticación. | Salen sin interrumpir Codex. Eso mantiene la sesión operativa, pero no demuestra que se haya guardado memoria. [Comportamiento publicado](https://github.com/supermemoryai/codex-supermemory). | Tu bitácora debería registrar éxito o fallo de la captura, no solo éxito del trabajo de código. |

**Orden de aprovechamiento que propongo:** primero, el seguimiento de PR y correcciones de Continuous Claude; después, el contrato de estados de Symphony; después, captura y mantenimiento de aprendizajes de Compound; finalmente, probar la memoria cruzada con el mismo proyecto en las cuatro superficies —Claude Code, Codex CLI, Codex Cloud y ChatGPT—. Es una recomendación para ampliar tu motor existente, no una invitación a instalar once sistemas. [Continuous Claude](https://github.com/AnandChowdhary/continuous-claude), [Symphony](https://github.com/openai/symphony), [Compound](https://github.com/EveryInc/compound-engineering-plugin).

## 6. Búsquedas exactas realizadas

Estas son las consultas enviadas al buscador, en orden, incluidas las que dieron malos resultados y las que tienen una sintaxis poco útil. No he corregido retrospectivamente las cadenas. Los filtros de dominio, cuando los hubo, aparecen aparte. No apliqué un filtro temporal automático: prioricé y contrasté las fechas de los resultados.

Además abrí directamente los repositorios, archivos, artículos y enlaces citados en el informe. Esas aperturas y búsquedas de texto dentro de las páginas no son consultas nuevas al buscador.

1. `Codex cloud AGENTS.md MCP` — filtro de dominios: `developers.openai.com`.
2. `Geoffrey Huntley Ralph loop github`.
3. `Kieran Klaassen compound engineering github review learnings`.
4. `Steve Yegge Beads Gas Town github workflow`.
5. `site.github.com/EveryInc/compound-engineering-plugin`.
6. `site.ghuntley.com/ralph/`.
7. `site.github.com/steveyegge/beads`.
8. `site.developers.openai.com/codex/guides/agents-md`.
9. `Dex Horthy advanced context engineering github humanlayer 2025 2026 video`.
10. `Boris Cherny workflow CLAUDE.md January 2026 github`.
11. `Peter Steinberger agent scripts shipping speed inference workflow 2026`.
12. `Harper Reed Simon Willison agentic workflow 2026`.
13. `"github" "agent-orchestrator" "Composio"`.
14. `"Ryan Carson" "compound" "github"`.
15. `"continuous-claude" "github"`.
16. `"HumanLayer" "advanced-context-engineering-for-coding-agents"`.
17. `Composio agent orchestrator github`.
18. `Ryan Carson compound product github nightly`.
19. `Anand Chowdhary continuous claude GitHub`.
20. `Dex Horthy advanced context engineering coding agents`.
21. `site:supermemory.ai docs claude code codex chatgpt MCP automatic memory`.
22. `site:docs.mem0.ai openmemory claude code codex chatgpt automatic`.
23. `site:docs.cline.bot memory bank`.
24. `flujo agentes Claude Codex github revisión memoria Ralph español repositorio`.
25. `Gentleman Programming Engram agent teams lite workflow` — filtro de dominios: `github.com`, `youtube.com`.
26. `Boris Cherny how I use Claude Code January 2026` — filtro de dominios: `x.com`, `anthropic.com`.
27. `Harper Reed my workflow agentic coding 2026` — filtro de dominios: `harper.blog`.
28. `Simon Willison agentic engineering patterns 2026` — filtro de dominios: `simonwillison.net`.
29. `"The Self-Improving AI System That Built Itself"`.
30. `"Compound Engineering Gets an Upgrade"`.
31. `"Boris Cherny" "CLAUDE.md" "2026"`.
32. `"Gentleman" "Engram" "youtube"`.
33. `"Gentleman Programming" "ECOSISTEMA" "Engram"`.
34. `"Kieran Klaassen" "Compound Engineering" "2026" "youtube.com/watch"`.
35. `"Geoffrey Huntley" "Ralph" "2026" "youtube.com/watch"`.
36. `"Harper Reed" "2026" "workflow"`.
37. `"El ECOSISTEMA" "Engram" "SDD"`.
38. `"GentlemanProgramming" "Engram" "Tutorial"`.
39. `"Kieran Klaassen" "The Era of Compound Engineering"`.
40. `"Inventing the Ralph Wiggum Loop" "Geoffrey"`.

