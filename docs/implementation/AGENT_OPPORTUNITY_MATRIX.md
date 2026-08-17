# SIRIUS — Matriz de oportunidades de agentes (Fase 0)

- **Fecha:** 12 de agosto de 2026 · **Base:** inventario PROC-### de [`WORK_PROCESS_AUDIT.md`](WORK_PROCESS_AUDIT.md)
- **Regla de priorización:** trabajo humano eliminado / (coste + riesgo de automatización). No por espectacularidad.
- **Este documento recomienda; no decide.** Ninguna implementación queda autorizada por él.

## 1. Puntuación

Criterios 0–5 (encargo §7): FR frecuencia · MIN minutos humanos por ejecución · REP repetitividad/estructura · EV evidencia/datos disponibles · VER verificabilidad automática del resultado · ERR coste de errores actuales · RIE riesgo de permisos si se automatiza (5 = riesgo bajo) · HAN valor de eliminar el handoff.

| PROC | Proceso | FR | MIN | REP | EV | VER | ERR | RIE | HAN | Total |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 005 | Desatascar estados (forense) | 5 | 4 | 4 | 5 | 4 | 5 | 4 | 5 | **36** |
| 010/013 | Deriva documental derivada + KB | 3 | 3 | 5 | 5 | 5 | 4 | 5 | 4 | **34** |
| 001 | Redactar work items | 4 | 3 | 4 | 4 | 3 | 4 | 4 | 5 | **31** |
| 003 | Vigilancia/notificaciones | 5 | 2 | 4 | 5 | 3 | 4 | 3 | 5 | 31 |
| 007 | Coordinación revisión dual (resto manual) | 3 | 3 | 4 | 5 | 4 | 4 | 4 | 4 | 31 |
| 015 | Auditorías periódicas | 2 | 4 | 4 | 4 | 3 | 4 | 5 | 3 | 29 |
| 011/012 | ADRs y specs (borradores) | 3 | 3 | 3 | 4 | 3 | 3 | 4 | 4 | 27 |
| 008 | Validación Windows (captura) | 2 | 4 | 3 | 4 | 3 | 5 | 5 | 3 | 29* |
| 014 | Investigación técnica | 2 | 5 | 2 | 3 | 2 | 3 | 2 | 4 | 23 |
| 002 | Arranque de bloques (cola) | 4 | 1 | 5 | 5 | 4 | 2 | 2 | 4 | 27 |
| 004 | Autorizar merge | 5 | 1 | 5 | 5 | 5 | 2 | 1 | 3 | 27 |
| 021 | Coste/modelos (libro mayor) | 3 | 1 | 5 | 3 | 5 | 3 | 5 | 2 | 27 |
| 006 | Meta-reparación de la automatización | 4 | 5 | 2 | 5 | 2 | 5 | 1 | 3 | 27 |
| 016 | Defectos intermitentes | 1 | 3 | 3 | 5 | 3 | 3 | 4 | 3 | 25 |
| 020 | Operar sesiones | 4 | 3 | 2 | 3 | 2 | 3 | 2 | 4 | 23 |
| 017 | Medición de rendimiento | 1 | 1 | 5 | 5 | 5 | 3 | 5 | 2 | 27 |
| 018 | Gobernanza/backlog | 1 | 2 | 3 | 5 | 4 | 2 | 4 | 2 | 23 |
| 009 | Registro de estado | 1 | 1 | 5 | 5 | 5 | 4 | 4 | 2 | 27 |
| 019 | Transporte de contexto (transversal) | 5 | 3 | 3 | 4 | 2 | 5 | 2 | 5 | 29* |

\* PROC-008 y PROC-019 puntúan alto pero su eliminación es de diseño/estructura, no de agente único; se reparten entre los demás.

## 2. Clasificación

**Automatizar ya (alto toil, bajo riesgo, verificable):**
- PROC-005 en su mitad de **diagnóstico** (no la reactivación): forense de solo lectura + informe verificable. → Piloto (§10).
- PROC-010/013: detección de deriva documental + borradores en `docs/implementation/`. → Piloto 2.
- PROC-021: libro mayor de ejecuciones desde datos que los workflows ya tienen (sin agente nuevo; instrumentación).

**Pilotar (valor alto, requiere evaluación):**
- PROC-001: borradores de work item generados desde el hallazgo de origen.
- PROC-014: Research Agent con web en perfil separado (requiere decisión de permisos — §5).
- PROC-015: auditor periódico de solo lectura con lentes paralelas.
- PROC-007c: recolector de hallazgos post-merge de Codex.

**Asistir, no ejecutar (la máquina prepara; el humano decide):**
- PROC-005 reactivación (retirar/poner etiquetas): receta preparada, gesto humano — pasar a automático exigiría cambio de contrato (decisión).
- PROC-008: guiones y captura estructurada de validación Windows; la ejecución es humana por naturaleza.
- PROC-011/012: borradores de ADR/spec; el contenido decisorio es humano.
- PROC-016: adjuntar historial de reapariciones; decidir es humano.

**Mantener humano (estratégico/irreversible):**
- PROC-004 (`fusiona`): técnicamente automatizable al 100 % con todo verde, pero es la última puerta de gobernanza; cambiarla es decisión de política, no oportunidad técnica. Posible relajación puntual (PRs solo-docs) = decisión del propietario.
- PROC-002 arranque: la orden de trabajo es humana por contrato; una cola pre-aprobada sería un cambio de contrato pequeño (preparable, no decidible aquí).
- PROC-006: cambios de workflows/contrato — ADR-002 fijó la frontera deliberadamente.
- Todas las decisiones de producto/arquitectura/gasto y la evaluación PS-01…PS-07.

## 3. Candidatos de agentes: confirmación, fusión o descarte

| Candidato (encargo §8 / prompt) | Veredicto según evidencia |
|---|---|
| AG-01 Documentation & State | **Confirmado**, acotado a documentación DERIVADA (KB, onboarding, gobernanza, índices, evidencia faltante). El registro de estado ya lo resolvió ADR-005 estructuralmente. Nunca toca canónicos. |
| AG-02 Research | **Confirmado como necesidad, pospuesto como piloto**: frecuencia real no demostrada por trazas (una campaña de spikes); exige perfil web separado (decisión de permisos). |
| AG-03 Repository Auditor | **Confirmado**; el patrón «6 lentes en paralelo» de ADR-004 ya demostró superioridad sobre rondas seriales. Solo lectura estricta. |
| AG-04 Decision Preparation | **Fusionar con AG-01** (borradores de ADR/spec e índice de decisiones); no justifica agente propio aún. |
| AG-05 Evidence/QA | **Confirmado como rol transversal**, no como agente permanente: verificación adversarial de afirmaciones de otros agentes (el repo ya lo hace a mano; #136 demostró el coste de no hacerlo). |
| AG-06 Work Coordinator | **Descartado por ahora**: el bus ya existe (work item de GitHub, contrato §2); construir un coordinador antes de estabilizar las piezas repetiría el patrón «capa nueva → familia nueva de defectos» (H-1…H-7, #136). Reevaluar tras pilotos 1–3. |
| AG-07 Model Evaluator/Router | **Pospuesto**: sin libro mayor de ejecuciones (PROC-021) no hay datos para enrutar. Primero instrumentar. |
| AG-08 External Validation Assistant | **Confirmado en versión mínima** (guion + captura estructurada); el caso B13 «cerrado por declaración, sin evidencia escrita» es exactamente su justificación. |
| BUILDER (prompt Fase 5) | **Ya existe**: es la tubería actual (implementador/corrector con permisos acotados). No se propone cambiarla. |
| EVALUATOR/CRITIC (prompt) | = AG-05. Regla que la evidencia impone: «dos modelos dicen lo mismo» NUNCA se convierte en «es verdad» sin comprobación contra la fuente (el agregador actual ya evita votos; mantener). |

## 4. Arquitectura de permisos (mínimo privilegio)

Principio confirmado por la evidencia: perfiles separados por función, nunca un superagente. La frontera actual (deny web + deny workflows + deny canónicos + merge humano) ha contenido daños reales (ADR-002; truncados del conector; #43).

| Perfil | Lee repo | Escribe | Web | GitHub | Secretos | Merge |
|---|---|---|---|---|---|---|
| Builder (actual, sin cambios) | sí | src/tests/migrations/docs-impl | no | acotado | no | no |
| Triaje (piloto) | sí | nada (informe en comentario/issue vía humano en fase 1) | no | lectura | no | no |
| Docs/State (AG-01) | sí | docs/implementation (borradores) | no | lectura | no | no |
| Auditor (AG-03) | sí | nada (informe) | opcional-lectura futura | lectura | no | no |
| Research (AG-02) | solo lectura | informes fuera del código | sí | lectura | no | no |

## 5. Política de Internet (decisión argumentada, pendiente de aprobación)

**Por qué está bloqueada hoy:** el perfil del repo combina lectura de repo privado + escritura + git + GitHub; añadirle web crearía la cadena completa de prompt injection indirecto (contenido no confiable → instrucciones → escritura/publicación). El repo ya trata contenido externo como no confiable por diseño (lecturas filtradas por autor de confianza en `sirius_issue.sh`: los bloques estructurados «son instrucciones de facto para pasos con permisos de escritura»). La misma lógica aplica a la web.

**Cuándo permitirla y a quién:** solo en perfiles sin capacidad de escritura sobre código ni push a ramas de trabajo (Research/Auditor), en sesión aislada (cloud/sandbox), con salida = informe que un humano (o AG-05) revisa antes de que influya en trabajo con permisos.

**Mitigaciones concretas:** separación de canales (todo texto web se trata como dato, citable pero no ejecutable); sin secretos en el entorno; sin acceso a `settings`/workflows; presupuesto de tiempo/coste por encargo; registro de fuentes consultadas en el informe (observabilidad §7).

**Qué datos de Sirius pueden llegar a terceros:** las consultas de búsqueda no deben contener código privado ni datos personales; regla práctica: el Research Agent formula preguntas genéricas (tecnologías, hardware, precios) y solo cruza con el repo en local. Esto debe quedar escrito en su prompt de sistema cuando se diseñe.

## 6. Capa multimodelo mínima

No construir abstracción propia ahora. Lo mínimo razonable si se compara modelos más adelante: (a) Claude vía Claude Code / Agent SDK (ya en uso); (b) Codex vía conector GitHub (ya integrado, sin API de pago); (c) NVIDIA NIM y modelos locales (Ollama/vLLM/llama.cpp) exponen API compatible con OpenAI, así que una configuración `{base_url, model, key}` sobre un cliente OpenAI cubre todos sin framework. La «capa» es un archivo de configuración + el libro mayor de ejecuciones, no una plataforma. Decidir solo después de que exista una tarea real de comparación (benchmark §8).

## 7. Observabilidad y métricas

Registro por ejecución (JSONL en `docs/implementation/agent_runs/` o similar): id, agente, misión, modelo, proveedor, duración, turnos, tokens in/out, tool calls, errores/reintentos, coste, desenlace, evaluación. Fuentes ya disponibles sin instrumentar nada nuevo: `claude-code-action` expone coste/turnos/duración (ya citados a mano en #135 y PR #90); Actions da duración y logs; Codex no expone métricas (solo sus comentarios) — se registra lo observable. Primer paso barato: que cada veredicto estructurado que ya se publica incluya el bloque de métricas; hoy se pierde.

## 8. Benchmark interno de Sirius (diseño futuro, no ahora)

Idea con datos propios: «PRs doradas» — reejecutar revisiones sobre PRs pasadas con defectos conocidos y numerados (#136: 19; #146: 8+6; #124: 21 hilos) y medir hallazgos válidos/falsos/coste/velocidad por modelo. Barato, reproducible, sin clave nueva. Solo tiene sentido tras el libro mayor (§7).

## 9. Orden recomendado de pilotos

1. **Triaje de paradas** (§10) — elimina la bolsa nº 1 de toil con riesgo mínimo.
2. **Detector de deriva documental (AG-01 modo lectura)** — elimina la bolsa de reconciliación y protege el contexto de TODAS las sesiones.
3. **Libro mayor de ejecuciones** (instrumentación, no agente).
4. **Research Agent** con perfil web separado (tras decisión de permisos del propietario).
5. Reevaluar Coordinator/Router con datos.

## 10. Piloto único recomendado: Agente de Triaje de Paradas

**Por qué este:** es la mayor bolsa de trabajo humano recurrente medida (≥15–20 desatascos/mes, EST 15–60 min de forense cada uno, más latencias de horas-días), ya ocurrió DOS veces exactamente el mismo forense manual documentado (#148 19:51Z y la ronda 4 pendiente), su resultado es verificable contra la realidad (el diagnóstico se comprueba mirando el run), no toca Sirius ni la automatización, y es útil aunque falle (cada informe deja un punto de partida). Cumple la práctica recomendada de extraer una skill tras observar la tarea real repetida, no antes.

- **Misión:** dada una incidencia en `sirius:failed-safely`/`sirius:blocked-decision` (o señalada por el reconciliador), verificar el estado real de la máquina y entregar un diagnóstico con evidencia y una recomendación única.
- **Entradas:** número de incidencia; acceso de LECTURA a repo, issues, PRs, runs de Actions.
- **Pasos fijos (runbook versionado):** leer incidencia y último veredicto → localizar el run → comparar desenlace real del run con lo que el veredicto afirma → verificar head vigente vs aprobado → estado del par de convergencia → clasificar: (a) parada correcta por causa transitoria/mecánica, (b) defecto de la automatización, (c) decisión real → redactar informe con CADA afirmación acompañada de su comprobación (disciplina-evidencia §4) → recomendar exactamente una acción (receta de etiquetas ya en el formato que `sirius_reconcile.sh` usa) o declarar «no lo sé» con lo que faltó por mirar.
- **Salidas:** comentario/informe estructurado en la incidencia (en fase 1, lo publica el propietario o la sesión bajo su supervisión).
- **Herramientas:** Claude Code en sesión (cloud o local), solo lectura; sin WebSearch/WebFetch; sin escritura de código.
- **Permisos:** los del perfil actual de sesión SIN usar escritura; explícitamente prohibido mutar etiquetas, cerrar issues, hacer push.
- **Modelo inicial:** el de las sesiones actuales (Sonnet para el runbook; escalar a un modelo mayor solo si los primeros casos fallan). **Alternativos:** cualquier modelo vía el mismo runbook (es texto).
- **Límites:** ≤15 min de sesión, ≤40 turnos, EST ≤1–2 USD equivalentes por ejecución (dentro del plan actual; sin API de pago nueva).
- **Reintentos:** ninguno automático; si falla, el informe parcial queda y el humano sigue como hoy.
- **Observabilidad:** cada ejecución añade línea al libro mayor (§7): incidencia, clasificación, ¿verificado correcto por el humano?, minutos ahorrados estimados.
- **Criterio de éxito (medible):** en las primeras 10 ejecuciones, ≥8 diagnósticos confirmados correctos por el propietario Y reducción del gesto humano a ≤5 min por desatasco; cero afirmaciones sin comprobación adjunta.
- **Criterio de fracaso:** un solo diagnóstico confiado-y-falso que el propietario detecte (la cita que gobierna: «un valor plausible y falso se cree, mientras que un error se investiga») → parar, aplicar regla de dos rondas al diseño.
- **Intervención humana:** lanza el propietario (fase 1 manual: «triaje de #N»); él ejecuta la acción recomendada. Nada se reactiva solo.
- **Riesgos:** diagnóstico plausible-falso (mitigado por comprobaciones obligatorias adjuntas y validación humana de los primeros 10); deriva del runbook respecto a la maquinaria real (mitigado: el runbook vive en `docs/implementation/` y cita los scripts vigentes).
- **Rollback:** dejar de lanzarlo. No deja estado.
- **Qué se aprende aunque fracase:** un catálogo real de causas de parada con frecuencia (dato que hoy no existe), y una medición de si un agente puede sostener la disciplina de evidencia sin supervisión — insumo directo para decidir sobre AG-03/AG-05.

**Refutación intentada (disciplina §4):** (a) «El toil de desatascos decaerá solo al estabilizarse la automatización» — posible, pero la serie histórica muestra que cada capa nueva trajo su familia de defectos (H-1…H-7 → #136 → #148); mientras se añadan capas (revisión dual, reconciliador) habrá paradas. Si decae, el piloto habrá costado casi nada. (b) «El detector de deriva documental es más seguro» — cierto, pero elimina menos minutos y su dolor es latente, no agudo; queda como piloto 2. (c) «Es la zona donde el sistema más veces se equivocó diagnosticando» — exacto: por eso el piloto NO decide ni actúa, solo prepara con comprobaciones adjuntas, y su criterio de fracaso es de tolerancia cero. (d) «La hipótesis del propietario apuntaba a Research/Docs/Auditor» — la evidencia de frecuencia manda: investigar es episódico; desatascar es semanal.

## 11. Roadmap posterior (si el piloto funciona)

Pilotos 2–4 (§9) → cola de bloques pre-aprobada (cambio de contrato pequeño, elimina n−1 arranques) → reactivación automática SOLO de la clase (a) transitoria-mecánica con cambio de contrato y ventana de observación → Research Agent con perfil web → benchmark de PRs doradas → reevaluar Coordinator/Router. En paralelo, decisiones de política que solo el propietario puede tomar (§13).

## 12. Verificación realizada sobre esta auditoría

- Comprobación por mutación de cifras portantes: conteos de commits por documento (28/20/19/15) y sesiones distintas (24) re-derivados de `git log` de forma independiente ✔
- Convergencia entre lectores independientes: los 9 informes coinciden en los hechos compartidos (timeline de #148, secuencia de #123, latencias, atribución de identidades) sin contradicciones materiales ✔
- Ronda adversarial completa (refutación externa de hipótesis y piloto por agentes independientes): **abreviada por indicación del propietario de cerrar el trabajo**; en su lugar, refutación interna en §10. Queda declarado como límite: este documento tuvo UNA ronda de verificación, no dos.

## 13. Preguntas que solo el propietario puede resolver

1. **Tiempos reales:** ¿cuánto te cuesta hoy, en minutos, un desatasco típico y una tanda de validación Windows? (calibra las métricas del piloto; desde el repo solo se miden latencias).
2. **Identidad:** ¿quieres separar la identidad de los agentes de tu cuenta (`canelamoraguezandyjesus-bot`)? Hoy humano, sesiones y PAT son indistinguibles para la propia maquinaria (#43, «puerta de cuenta») y para cualquier auditoría futura.
3. **Perfil web:** ¿autorizas crear, en fase posterior, un perfil Research separado con WebSearch/WebFetch, sin escritura de código, y bajo qué envolvente de gasto?
4. **Merge:** ¿mantienes `fusiona` universal o quieres una vía distinta para PRs solo-documentales con todo verde? (hoy el gesto no aporta información cuando todo está verde; su valor es de gobernanza y esa valoración es tuya).
5. **Cola de bloques:** ¿aceptarías pre-aprobar lotes («B12e-B12g en orden») para eliminar n−1 arranques manuales? Exige cambio de contrato.
6. **ChatGPT:** ¿qué papel real tiene hoy (redacción de work items, decisiones, otra cosa)? Es el mayor punto ciego de esta auditoría y condiciona el diseño del handoff (encargo §10).
7. **Gobernanza fósil:** ¿#8/#9/#10/#14/#15/#25 se archivan, se regeneran o se migran a documentos? Hoy contradicen el estado vigente.
