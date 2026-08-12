# SIRIUS — Auditoría de procesos de trabajo (Fase 0)

- **Estado:** COMPLETADA (inventario y conclusiones añadidos tras la inspección; la nota de arranque de abajo se publicó ANTES de cualquier conclusión, commit `732a0ac`).
- **Fecha de arranque:** 11 de agosto de 2026 · **Fecha de cierre:** 12 de agosto de 2026
- **Encargo:** auditoría de procesos de trabajo (process mining) previa al diseño de agentes. No se implementan agentes en esta fase.
- **Vertical:** solo documentación en `docs/implementation/`. Sin cambios en código, `.claude/`, `.github/`, permisos ni workflows.
- **Documento hermano:** [`AGENT_OPPORTUNITY_MATRIX.md`](AGENT_OPPORTUNITY_MATRIX.md) (priorización, arquitectura de agentes, política de Internet, piloto recomendado).

## Nota de arranque

1. **¿Dónde vive el fallo y dónde va el arreglo?** El «fallo» que se estudia es trabajo humano repetitivo que no deja traza estructurada (transferencia de contexto, vigilancia, reconciliación, coordinación). El «arreglo» (este inventario y la matriz de oportunidades) vive en `docs/implementation/`. ¿Puede el sitio del arreglo OBSERVAR el fallo? **Solo parcialmente.** Desde el repositorio y GitHub se observa lo que pasó por PRs, issues, comentarios, commits, workflows y documentos. NO son observables desde aquí: las conversaciones de ChatGPT, el trabajo local en Windows no comiteado, las sesiones interactivas de Claude Code no publicadas y el tiempo/atención humanos. Todo lo no observable se registrará como límite o como hipótesis marcada, nunca como hecho.
2. **¿Qué NO va a garantizar este trabajo?**
   - No garantiza un inventario exhaustivo: los canales no observables pueden contener procesos enteros que aquí no aparezcan.
   - No garantiza tiempos humanos medidos: no existe time-tracking; toda cifra de minutos u horas será una estimación y se marcará como tal.
   - No garantiza que la hipótesis rectora («el cuello de botella ya no es escribir código sino la coordinación de conocimiento alrededor del código») quede confirmada ni refutada de forma concluyente; solo se contrasta contra las trazas disponibles.
   - No garantiza que los candidatos de agentes propuestos sean viables: eso lo decidirá el diseño y el piloto posterior.
3. **Criterio de parada** (decidido antes de ver resultados; el encargo §13 es la fuente):
   1. todos los procesos repetidos observables en la muestra (PRs #119–#149, issues asociadas, workflows, scripts, docs, historial git; más trazas anteriores como línea base) tienen ficha PROC-###;
   2. cada proceso tiene al menos una evidencia concreta o se marca explícitamente como hipótesis;
   3. los principales handoffs humano↔herramienta están representados;
   4. se puede explicar dónde se va el tiempo humano y por qué;
   5. existe un ranking de automatización basado en trabajo eliminado y riesgo;
   6. queda recomendado un único primer piloto;
   7. no quedan categorías de trabajo conocidas (taxonomía A–F del encargo §4) sin revisar.
   - **Regla de las dos rondas aplicada aquí:** si dos rondas de verificación consecutivas descubren la misma familia de trabajo manual omitida, se detiene la catalogación incremental y se revisa la taxonomía completa antes de seguir añadiendo procesos.
4. **¿Qué haría el fallo IMPOSIBLE en vez de improbable?** Que el contexto se capture una sola vez en un artefacto canónico legible por todas las herramientas (Work Item), de modo que la transferencia manual deje de ser necesaria por construcción. No se construye en esta fase; la auditoría lo evalúa solo como diseño candidato. Se dice explícitamente por qué no se hace ahora: el encargo prohíbe implementar y el coste de equivocarse de diseño antes del inventario es exactamente el fallo que esta auditoría existe para evitar.

## Declaración de alcance de decisión

Este trabajo produce **recomendaciones**, no decisiones. Al cerrarse la auditoría no hay ninguna decisión aprobada por el propietario, así que **no se registra ADR** (skill `disciplina-evidencia` §5, dicho explícitamente). Si el propietario aprueba el piloto recomendado, esa aprobación deberá dejar su propio ADR.

## Metodología ejecutada

1. Lectura directa de las fuentes normativas: `AGENTS.md`, `CLAUDE.md`, skill `disciplina-evidencia` (SKILL.md y patrones.md), hook `recordar_parada.py`, comandos `/work` y `/check`, `.claude/settings.json`, contrato operativo v1.6, `STATUS.md`, `PLAN.md`, `V8_EXECUTION.md`, `REPOSITORY_STATUS.md`, onboarding y base de conocimiento de `docs/operations/`.
2. Barrido paralelo con nueve lectores independientes de solo lectura (workflow `sirius-process-audit-sweep`, run `wf_cd90abb5-c67`): (1) maquinaria de automatización (13 workflows + `scripts/automation/**` + prompts + plantilla de incidencia); (2) documentación de implementación y estado; (3) decisiones, auditorías, operaciones, evolución y robótica; (4) disciplina + historial git completo; (5) PRs #118–#128; (6) PRs #129–#139; (7) PRs #141–#149 e issues #138/#140; (8) issues de trabajo #123–#148; (9) gobernanza (#8–#25) y línea base de la automatización (#42–#90). Cada lector devolvió hechos con evidencia, trabajo humano observado, límites de la automatización, handoffs, fricción, latencias con timestamps, inferencias marcadas y citas.
3. Comprobaciones por mutación de cifras que sostienen conclusiones (conteos de commits por documento: 28/20/19/15 confirmados; 24 sesiones `Claude-Session:` distintas confirmadas por `git log --all`).
4. Síntesis del inventario PROC-### y de la matriz, y verificación adversarial posterior (crítica de completitud contra la taxonomía A–F, verificación por muestreo de evidencias, intento de refutación de la hipótesis rectora y del piloto).

## Fuentes inspeccionadas

- Repositorio en `origin/main` (`5589cfd`, 2026-08-11): `AGENTS.md`, `CLAUDE.md`, `.claude/**`, `.github/workflows/**` (13), `.github/ISSUE_TEMPLATE/sirius-work-item.yml`, `scripts/automation/**` (5 sh, 4 py, 3 prompts), `docs/implementation/**`, `docs/decisions/**` (ADR-001…007), `docs/audits/**` (4), `docs/operations/**` (2), `docs/evolution/**`, `docs/robotics/head/**`, `docs/canonical/STATUS.md` (solo lectura), `REPOSITORY_STATUS.md`, historial git completo (141 commits en main, 112 ramas remotas).
- GitHub: PRs #74–#90 (línea base), #118–#149 (muestra principal) con cuerpos, comentarios, revisiones, hilos y commits; issues #8, #9, #10, #14, #15, #25, #42–#75 (línea base), #123–#148 (muestra principal) con todos sus comentarios.

## Límites de observabilidad (qué parte de la historia NO se vio)

1. **Conversaciones de ChatGPT**: cero trazas directas. Su papel se reconstruye por el contrato (§0: «limitado a crear la incidencia inicial y aplicar la etiqueta de arranque»), por la issue #25 (patrón manual pre-automatización) y por una única cita indirecta de chat («perfecto mira si termino si si fusiona y continuanos», issue #43). Cuánto trabajo de redacción/decisión ocurre hoy en ChatGPT es **no observable**.
2. **Sesiones interactivas de Claude Code**: solo se ven sus efectos (commits con trailer `Claude-Session:`, comentarios con pie `_Generated by Claude Code_`). La dirección verbal del propietario dentro de la sesión —aprobaciones, denegaciones de permisos, decisiones intermedias— es no observable; hay señales de que existe y es sustancial (`permission_denials_count: 1` en #135; «un comando me fue denegado», PR #136; «en la sesión que motivó esto el propietario no escribió `/comando` ni una vez», PR #139).
3. **Trabajo local en Windows**: solo entra al repo como declaración (B13 «Completo por declaración del propietario… Sin evidencia escrita») o como evidencia transcrita a mano (PR #122). El esfuerzo real es no observable.
4. **Tiempo y atención humanos**: no hay time-tracking. Toda duración «humana» de este documento es cota inferior de latencia de atención (cuándo respondió), no esfuerzo medido (cuánto trabajó). Las cifras de minutos marcadas **EST** son estimaciones.
5. **Identidad compartida**: la cuenta `canelamoraguezandyjesus-bot` la usan tres actores — el humano, las sesiones de Claude Code (con su PAT) y pasos de workflow (PAT). La atribución se hizo por señales de contenido (pie de Claude, marcadores HTML `<!-- sirius-* -->`, brevedad informal humana). Donde la señal falta, la atribución es inferencia y así se marca.

## Actores del sistema (modelo de atribución)

| Actor | Identidad en GitHub | Qué hace | Señal de atribución |
|---|---|---|---|
| Propietario (humano) | `canelamoraguezandyjesus-bot` | decide, etiqueta, comenta `fusiona`, fusiona, valida Windows, desatasca | comentarios cortos informales sin pie («Fusiona », retiradas de etiqueta) |
| Sesión interactiva Claude Code | misma cuenta | implementa en ramas, diagnostica, redacta issues/ADRs/PRs, responde hilos | pie `_Generated by Claude Code_`, trailer `Claude-Session:` |
| Tubería (workflows + PAT) | misma cuenta o `github-actions[bot]` | implementador/revisor/corrector, Quality, transiciones, notificaciones, merge autorizado | marcadores HTML deterministas (`<!-- sirius-* -->`) |
| Codex (revisor externo) | `chatgpt-codex-connector[bot]` | segunda revisión de solo lectura; correcciones bajo orden en #122 | identidad propia de conector |
| ChatGPT (panel de mando) | sin identidad propia | crear incidencia inicial + etiqueta de arranque (contrato §0); históricamente redactor de mandatos y ejecutor del merge (eliminado en v1.2/v1.3) | ninguna directa (límite de observabilidad) |

Consecuencia auditada: la «puerta humana» del sistema es en realidad una **puerta de cuenta** (el revisor de la issue #43 bloqueó cinco veces por no poder verificar qué actor había autorizado; un `fusiona` publicado por una sesión de Claude en #75 lo demuestra).

## Línea temporal (eras del proceso)

1. **Manual puro** (12–18 jul): commits directos del humano a `main`; patrón #25: ChatGPT redacta mandato multiparte → el humano lo une y lo pega en Claude → Claude implementa local → el humano hace push → ChatGPT crea/revisa PR y fusiona con autorización expresa. El humano es el bus de todo.
2. **Construcción y depuración de la tubería** (19–22 jul): contrato v1.0-v1.3; issues de humo #47/#66/#75; maratón del 21-jul (≥7 ciclos diagnóstico→fix→merge→re-etiquetar en un día, PRs #67–#78); 14 bloques fusionados en 23 h el 21–22 jul.
3. **Sesiones interactivas largas** (23 jul–2 ago): una sola sesión (`0171zgh…`, 55 commits) produce las PRs #118–#121 con validación manual en Windows declarada en cada cuerpo; spikes de investigación en ramas (sesión `01QrGat…`, 155 commits).
4. **Revisión dual y su dolor** (2–7 ago): #122 (97 commits, 81 comentarios, 14 revisiones de Codex, rescates BASE64, sigue abierta); #124 (10 rondas en un día); v1.4/v1.5 aprobadas el 3-ago.
5. **Disciplina de evidencia y meta-reparación** (7–11 ago): #136 (19 defectos en 8 rondas) → #138 → ADR-001…007 en 4 días; red de seguridad programada (v1.6); ciclo autónomo B12e (#148/#149) funcionando y hoy atascado en `failed-safely`.

## Diagramas de los flujos actuales

### Ciclo feliz de un bloque (con los toques humanos numerados)

```text
[H1] redactar work item ──> issue (plantilla 12 campos)
[H2] sirius:planned + sirius:implement-requested
        │
        v (máquina, minutos)
  validate-activation ─> implement (Claude Code, rama+PR+veredicto)
        ─> Quality ─> advance ─> revisión (Claude [+ Codex]) ─> agregador
        ─> [verde] ready-for-merge ──> notificación @propietario
        ─> [hallazgos] corrector (convergencia §5.1) ─> Quality ─> …
        │
[H3] leer notificación (GitHub Mobile)
[H4] comentar `fusiona`  ──> merge-sirius-work reverifica y fusiona
        ─> complete ─> sirius:completed ─> cierre
[H5] (implícito) decidir el siguiente bloque ─> vuelta a H1
```

Medido: los tramos de máquina duran minutos (issue #148: PR abierta 14 min tras la issue; ronda revisión+corrección ~10–20 min; merge tras `fusiona`: 18–31 s). Toda espera larga es espera de atención humana (16 min a 37 h).

### Ciclo de fallo (donde se concentra el trabajo humano actual)

```text
run muere / veredicto ausente / Codex mudo / PAT sin alcance / decisión real
        │
        v
  sirius:failed-safely ó sirius:blocked-decision  ──> notificación única
        │                                              (si la dedupe no la silencia)
        v
[H] mirar Actions, leer logs, comparar heads, verificar si el diagnóstico
    de la máquina es verdad  («forense», p.ej. #148: el veredicto provisional
    "Ronda interrumpida" era falso; el run acabó en verde)
        │
        ├─ causa transitoria → [H] retirar etiqueta «a conciencia» + reponer evento
        ├─ defecto de la automatización → [H] abrir sesión Claude Code → PR de fix
        │   → revisión → merge → re-etiquetar   (PROC-006, ≥15 PRs de esto)
        └─ decisión real → [H] decidir y registrarla
```

### Flujo documental y de decisión

```text
conversación externa (ChatGPT/Claude, no observable)
        │  [H] transporta el resultado
        v
spec / encargo / aprobación ──> PR documental (p.ej. #128: 3d 22h en cola)
        │
bloque fusionado ──> (agente) actualiza tabla única de V8_EXECUTION (ADR-005)
        │
fallo o hallazgo ──> sesión Claude ──> ADR en docs/decisions/ ──> [H] fusiona
        │
derivados (KB, onboarding, issues de gobernanza #8-#25): SIN proceso de
actualización → se quedan fósiles (KB audita contrato v1.1; vigente v1.6)
```

### Coordinación de revisión externa (versión manual, PR #122; automatizada en v1.4)

```text
[H] @codex review (con head, run, "dónde apretar") ─> Codex revisa (3-6 min)
[H] verificar afirmaciones de Codex (404s, commits fantasma)
[H] @codex address that feedback (spec redactada a mano, hasta 3.665 chars)
[H] rescatar trabajo no publicado (volcados BASE64 de 57 KB por comentario)
[H] ejecutar build/verify en Windows y devolver errores
     └── la v1.4 automatizó el disparo/recolección/agregación; el resto sigue manual
```

## Inventario de procesos (PROC-###)

Formato de ficha: **Disparador · Objetivo · Entradas · Pasos y herramientas · Quién hace cada paso · Salida · Frecuencia observada · Tiempo humano (EST = estimación, sin time-tracking) · Fricción · Riesgo si se automatiza · Decisión que debe seguir siendo humana · Evidencia · Oportunidad de eliminación · Mecanismo candidato · Métrica de éxito.**

---

### PROC-001 — Redactar el work item (incidencia-contrato)

- **Disparador:** el propietario decide qué bloque toca (fin del anterior; hallazgo que exige trabajo nuevo).
- **Objetivo:** una incidencia con los 12 campos obligatorios de la plantilla (Work ID, objetivo, alcance/fuera de alcance, requisitos, pruebas, comandos, salvaguardas, prohibición de merge automático).
- **Entradas:** estado vigente (V8_EXECUTION), decisión de alcance, a veces un hallazgo previo (p.ej. #148 nace del hallazgo N+1 de #147).
- **Pasos y herramientas:** conversación (ChatGPT o sesión Claude) → redacción del cuerpo → publicación en GitHub → plantilla aplica `sirius:planned`.
- **Quién:** contenido: agente conversacional (inferencia fuerte: prosa, tablas medidas y primera persona de agente en #131/#137/#148); curación y publicación: propietario.
- **Salida:** issue estructurada (fuente de verdad del bloque, contrato §2).
- **Frecuencia:** 1 por bloque; ~30 bloques en la muestra; 9 cuerpos recientes suman ≈7.400–7.800 palabras.
- **Tiempo humano:** EST 10–30 min por issue si la redacta un agente y el humano cura; más si la escribe él.
- **Fricción:** transporte chat→GitHub (copia manual); cuerpos truncados por el conector de escritura (incidentes #55/#60, 5–6 casos); etiquetar antes de terminar de pegar produce rechazos (#126: 3 rechazos en 6 min).
- **Riesgo si se automatiza:** una issue mal derivada autoriza trabajo equivocado (la issue ES el contrato); inventar alcance está prohibido (AGENTS.md).
- **Decisión humana:** el alcance y la orden de arranque (contrato §9: prohibido iniciar bloques sin orden).
- **Evidencia:** plantilla `sirius-work-item.yml` (12 campos required); cuerpos de #123–#148; contrato §0/§2; validate-activation.
- **Oportunidad:** que el agente que ya detectó el trabajo (p.ej. la medición de #147) genere el borrador del work item directamente en GitHub y el humano solo edite/apruebe y etiquete — elimina el transporte y el truncado, no la decisión.
- **Mecanismo candidato:** Work Coordinator (AG-06) en su versión mínima: «borrador de work item desde hallazgo».
- **Métrica:** minutos humanos por issue creada; % de issues rechazadas por la puerta de validación.

### PROC-002 — Certificar y arrancar un bloque

- **Disparador:** work item listo.
- **Objetivo:** certificar planificación (`sirius:planned`) y emitir el evento (`sirius:implement-requested`).
- **Pasos:** aplicar dos etiquetas; si la puerta rechaza (cerrada, sin planned, cuerpo truncado, estado incompatible), corregir y reintentar.
- **Quién:** propietario (o ChatGPT en su nombre); la máquina tiene prohibido aplicar la etiqueta de arranque (§9.1: «No aplica **nunca** `sirius:implement-requested`»).
- **Salida:** bloque en marcha.
- **Frecuencia:** 1 por bloque + 1 por reactivación; ≥9 eventos de re-etiquetado documentados (5 reactivaciones en #43 en una tarde; reintentos en #126, #66, #88).
- **Tiempo humano:** EST 1–5 min el caso feliz; los rechazos en cadena multiplican (3 rechazos en 6 min en #126 y el estado quedó 6 días parado).
- **Fricción:** la etiqueta es un clic de certificación que no aporta información cuando el work item ya está aprobado; la confusión sobre QUÉ etiqueta arranca costó una PR entera (#146 «Proponer la etiqueta que sí arranca el trabajo»).
- **Riesgo si se automatiza:** arranque de trabajo sin orden humana — prohibido por contrato; una cola aprobada exigiría cambio de contrato (decisión).
- **Decisión humana:** la orden de arranque en sí.
- **Evidencia:** contrato §9/§9.1; `validate-sirius-activation.yml`; rechazos de #126; PR #146.
- **Oportunidad:** cola de bloques pre-aprobada en lote («aprueba B12e-B12g; arrancad uno al terminar el anterior») — cambio de contrato pequeño que elimina n−1 clics y n−1 esperas de atención.
- **Mecanismo:** cambio de contrato + workflow existente (no requiere agente).
- **Métrica:** nº de intervenciones humanas por bloque arrancado; latencia fin-de-bloque→arranque-del-siguiente.

### PROC-003 — Vigilar el ciclo y atender notificaciones

- **Disparador:** mención `@propietario` en 6 estados (contrato §7) — o su ausencia cuando algo muere sin notificar.
- **Objetivo:** enterarse del estado y decidir si actuar.
- **Pasos:** leer la notificación (GitHub Mobile), abrir la incidencia, a veces mirar Actions.
- **Quién:** propietario, único sensor de los estados terminales fuera de GitHub («no notifica fuera de GitHub», ADR-004).
- **Frecuencia:** ≥2 notificaciones por bloque en el ciclo feliz; más en fallos. ~30 bloques + ~20 incidentes en la muestra.
- **Tiempo humano:** EST 1–5 min por notificación; el coste real es la **latencia** y la interrupción: 16 min–37 h hasta `fusiona`; 14 h 50 min hasta el rescate de #148 (madrugada); >6 días en #126.
- **Fricción:** dedupe que silenció una segunda parada distinta (#60, «el usuario pudo creer que su corrección había funcionado»); vigilancia síncrona no registrada (merges de #144/#145 en 3–4 min = babysitting activo).
- **Riesgo si se automatiza:** vigilancia como motor del flujo está prohibida (§9, excepción acotada §9.1); un filtro que clasifique mal una parada la vuelve invisible.
- **Decisión humana:** qué merece su atención — pero hoy decide leyendo crudo.
- **Evidencia:** `notify-sirius-state.yml`; latencias medidas (tabla §Dónde se va el tiempo); ADR-004.
- **Oportunidad:** no más notificaciones sino **mejores**: cada aviso terminal llegando ya con el diagnóstico verificado y la acción recomendada (ver PROC-005), para que leer = decidir.
- **Mecanismo:** Agente de triaje (ver matriz, piloto recomendado).
- **Métrica:** minutos entre notificación y acción efectiva; nº de veces que el humano tiene que abrir Actions para entender un aviso.

### PROC-004 — Autorizar el merge (`fusiona`)

- **Disparador:** `sirius:ready-for-merge` (o PR de sesión con verde).
- **Objetivo:** autorización humana explícita del merge; la máquina reverifica todo por REST y ejecuta.
- **Pasos:** leer el aviso → comentar exactamente `fusiona` sobre la incidencia (no la PR) → si la puerta bloquea, reparar contabilidad y repetir.
- **Quién:** propietario (author_association == OWNER). La ejecución técnica es de `merge-sirius-work.yml`.
- **Frecuencia:** 1 por PR; ≥30 fusiones en la muestra (14 en 23 h el 21–22 jul; lote de 4 en 32 min el 10-ago).
- **Tiempo humano:** EST <1 min el gesto; el coste real es latencia de atención (mediana en decenas de minutos; picos de 23–37 h).
- **Fricción:** canal equivocado (2 `fusiona` en la PR de #124 sin efecto; «Fusiona » en PR #87 39 min después del merge); puerta bloqueada por contabilidad ausente (#123: «No encuentro ningun Head SHA aprobado» → el humano lo registró a mano); cuando todo está verde el comentario no aporta información nueva (todas las verificaciones ya son automáticas, `sirius_merge_on_command.sh`).
- **Riesgo si se automatiza:** el merge es la última puerta de gobernanza; automatizarlo en general está explícitamente prohibido y NO se propone.
- **Decisión humana:** la autorización de merge como política (contrato §8) — su valor es de responsabilidad, no técnico.
- **Evidencia:** contrato §8; merge-sirius-work.yml; secuencia completa en #123 (5 comentarios y 13 min para un clic).
- **Oportunidad:** (a) eliminar la fricción del gesto (que la puerta registre sola el head aprobado — ya corregido en parte); (b) decisión de política pendiente del propietario: si PRs solo-docs con todo verde merecen una vía de autorización en lote.
- **Mecanismo:** ninguno nuevo; a lo sumo cambio de política (decisión humana).
- **Métrica:** nº de `fusiona` fallidos por fricción; latencia ready-for-merge→merge.

### PROC-005 — Desatascar estados parados (forense y reactivación)

- **Disparador:** `failed-safely` / `blocked-decision` / estado que no avanza (aviso del reconciliador o silencio sospechoso).
- **Objetivo:** distinguir fallo real de fallo falso, decidir si reactivar, y re-emitir el evento correcto.
- **Entradas:** incidencia, logs de runs de Actions, heads, veredictos, registros de ronda.
- **Pasos observados (caso #148, 2026-08-11T19:51Z):** verificar que el run 31459955362 terminó en verde → comprobar que el head no cambió → constatar que el veredicto provisional «Ronda interrumpida antes de terminar» mentía → comprobar el par de convergencia (1,2) → retirar `sirius:failed-safely` «a conciencia» → reponer el evento → documentarlo («Se deja escrito para que la retirada no sea un gesto ciego»).
- **Quién:** propietario, a menudo con una sesión de Claude Code como instrumento (comentarios forenses con pie de Claude bajo su cuenta).
- **Salida:** ciclo reactivado, o decisión, o issue de diagnóstico nueva (#135).
- **Frecuencia:** ≥15–20 episodios en 3,5 semanas (#43×5, #50, #55, #60×2, #66×4, #126 —aún parado—, #133, #135, #140, #148×2 —aún parado—). La familia «corrector sin veredicto» apareció 3 veces en 5 días.
- **Tiempo humano:** EST 15–60 min por episodio de forense + redacción; más la latencia de detección (hasta v1.6, «dependía de que un humano notara primero justo aquello que la automatización debía notar por él»).
- **Fricción:** el diagnóstico de la máquina puede ser falso y creerse («un valor plausible y falso se cree, mientras que un error se investiga»); el mismo forense se repite (el propietario tuvo que rehacer en la ronda 4 de #148 lo que ya había hecho a las 19:51); los avisos históricos prescribían acciones que no funcionaban (4 veces en la misma PR, ADR-004).
- **Riesgo si se automatiza:** reactivar sin verificar repite el ciclo en vacío (#126: «Hay que retirarla a conciencia o el ciclo se repetirá igual»); un diagnóstico automático no confiable es peor que ninguno; mutar etiquetas roza la prohibición de vigilancia-motor (§9/§9.1).
- **Decisión humana:** reactivar tras un fallo no mecánico; toda decisión de producto/arquitectura detrás de un `blocked-decision`.
- **Evidencia:** #148 (14 h 50 min hasta el rescate; timeline completa), #126 (≥6 días), #140 (13 h), `sirius_reconcile.sh` (recetas de reactivación redactadas por la máquina), contrato §9.1.
- **Oportunidad:** la mayor de la auditoría en relación coste/riesgo: **preparar el desatasco** (forense verificado + clasificación transitorio/defecto/decisión + receta) para que el humano solo verifique y ejecute el gesto. La reactivación 100 % automática de casos mecánicos exigiría cambio de contrato (fase posterior).
- **Mecanismo candidato:** Agente de triaje de paradas (piloto recomendado; ver matriz §10).
- **Métrica:** minutos humanos por desatasco; % de diagnósticos del agente verificados correctos; nº de reactivaciones en vacío.

### PROC-006 — Depurar y endurecer la propia automatización

- **Disparador:** un fallo del pipeline (PROC-005 lo destapa) o un hallazgo de revisor sobre la maquinaria.
- **Objetivo:** corregir el defecto estructural para que esa familia de fallo no vuelva.
- **Pasos:** diagnóstico (sesión Claude) → PR de fix → revisión (a menudo Codex) → merge humano → re-etiquetar el trabajo parado → observar.
- **Quién:** sesión de Claude Code dirigida por el propietario; Codex como revisor; propietario fusiona y re-arranca.
- **Salida:** PRs de reparación + a menudo un ADR y una entrada en `patrones.md`.
- **Frecuencia:** la mayor familia de PRs de la muestra: ≥15 PRs claramente de meta-reparación (#67–#78, #87, #89, #90, #129, #130, #132, #136, #141/#142, #143, #146) frente a un puñado de PRs de producto. La maratón del 21-jul encadenó ≥7 ciclos en un día; #136 consumió 8 rondas/19 defectos; #146, 9 rondas/15 h para «cambiar el texto de un aviso».
- **Tiempo humano:** EST horas por episodio (dirigir la sesión, leer rondas, fusionar, re-etiquetar). No medible con precisión (límite 2).
- **Fricción:** los defectos vienen en familias que las rondas encuentran de una en una («un solo revisor comparte sesgo consigo mismo entre rondas»); trabajo tirado y rehecho dos veces (#140→#141 descartada→#142); merge antes de la revisión prometida (#143, admitido: «El fallo de proceso es mío»); el PAT sin alcance `workflow` convierte cada fix de workflows en trabajo de sesión (ADR-002, frontera deliberada).
- **Riesgo si se automatiza:** un agente que modifica la automatización modifica sus propias salvaguardas — exactamente lo que ADR-002 decidió impedir. Este proceso debe REDUCIRSE (menos fallos), no delegarse entero.
- **Decisión humana:** todo cambio de contrato y de workflows.
- **Evidencia:** serie H-1…H-7 (auditoría de roles), patrones.md (7 patrones, todos nacidos aquí), ADR-001…ADR-004, coste medido de intentos fallidos ($8.47/121 turnos el run 29868614857; $1.42/48 turnos el 31188643115).
- **Oportunidad:** indirecta — cada mejora de PROC-005 (triaje) y la auditoría paralela de lentes (ya adoptada en ADR-004) reducen rondas; el benchmark de «PRs doradas» (matriz §9) puede convertir los 19 defectos de #136 y los 8 de #146 en corpus de regresión para revisores.
- **Métrica:** nº de episodios de meta-reparación por semana; rondas por PR de fix.

### PROC-007 — Coordinar la revisión adversarial (Claude ↔ Codex)

- **Disparador:** PR que necesita segunda opinión (manual: #122, #124, #141–#146) o pipeline dual activado (#132/#133, #148/#149).
- **Objetivo:** hallazgos independientes verificados sobre el head exacto que pasó CI.
- **Pasos (versión manual):** redactar `@codex review` con head+run+dónde apretar → esperar 3–6 min → verificar afirmaciones de Codex contra el repo (404s, commits fantasma) → transportar hallazgos al corrector o corregir → repetir. En #122 además: `@codex address that feedback` con especificaciones de hasta 3.665 caracteres, y rescate de trabajo no publicado por volcados BASE64 (57.613 caracteres en 2 bloques).
- **Quién:** en #122 el propietario en persona (~46 comentarios sin pie); en #124-#146 la sesión de Claude redacta y el humano supervisa; en el pipeline v1.4, la máquina entera.
- **Frecuencia:** ~25 `@codex review` manuales en la muestra; 14 revisiones de Codex en #122, 10 en #124, 13 en #136, 6+ en #146.
- **Tiempo humano:** EST 5–15 min por ronda manual, más verificación de cada hallazgo (obligatoria por disciplina §4: dos hallazgos válidos de #136 traían el mecanismo equivocado).
- **Fricción:** cuota de Codex agotada corta el ciclo (2 h 54 min en #139); el recolector automático declaró timeout con la respuesta de Codex publicada 18 min antes (#148 ronda 4 — defecto de detección); Codex afirma trabajo no hecho («Tu informe anterior es materialmente incorrecto… NO existe en ese HEAD (404)»).
- **Riesgo si se automatiza más:** «dos modelos dicen lo mismo» convertido en «es verdad» — el agregador actual evita votos precisamente por eso; la verificación de hallazgos contra el código debe permanecer (humana o de un agente verificador con evidencia).
- **Decisión humana:** aceptar/rechazar hallazgos con juicio de modelo de amenaza (1 caso observado en #122).
- **Evidencia:** PR #122 y #124 completas; contrato §4.1; `sirius_codex_review.py`.
- **Oportunidad:** ya capturada en v1.4 para el ciclo de bloques; queda (a) arreglar la detección del resultado (defecto activo en #148), (b) transportar hallazgos post-merge de Codex a rondas nuevas sin humano (hoy los transporta el propietario), (c) el patrón «auditoría paralela de N lentes» como servicio reutilizable.
- **Métrica:** rondas por PR; hallazgos válidos por ronda; nº de rescates manuales.

### PROC-008 — Validación manual en Windows real

- **Disparador:** trabajo que exige el entorno físico del propietario (builds, GUI, Credential Manager, micrófono; puertas V8.2/V8.3).
- **Objetivo:** evidencia de que lo construido funciona en el Windows real.
- **Pasos:** ejecutar guiones/builds en Windows 11 → capturar resultados → devolverlos al repo (transcripción o declaración).
- **Quién:** propietario, único ejecutor físico. La máquina prepara guiones (CLOUD_SMOKE_TEST.md los tiene tipados).
- **Frecuencia:** declarada en los cuerpos de #118–#121 (4 validaciones); ≥2 tandas en #122; pendientes permanentes: Credential Manager, ejecutable, PS-01…PS-07, PA-E2E-01, voz (#126), grabación 1080p (#134).
- **Tiempo humano:** EST 15–60 min por tanda; no observable con precisión.
- **Fricción:** es EL bloqueo material de V8 («Lo que bloquea V8.2 y V8.3 no es código: es Windows real y una clave real»); la PR #122 lleva >9 días esperando «una sola ejecución correcta en Windows: build y verify, dos veces, desde árbol limpio»; B13 quedó cerrado «por declaración del propietario… Sin evidencia escrita en el repositorio»; la evidencia entra al repo transcrita a mano (fallos de OneDrive, ZIP de otro commit).
- **Riesgo si se automatiza:** fingir una prueba física no ejecutada — prohibido explícitamente (AG-08 del encargo: «No debe fingir haber ejecutado una prueba física que no ejecutó»).
- **Decisión humana:** la ejecución física misma y su aceptación.
- **Evidencia:** V8_EXECUTION B13/B14; PR #122; REPOSITORY_STATUS §Pendiente de validación manual.
- **Oportunidad:** no eliminar sino **estructurar**: guion por prueba + captura estructurada del resultado (formulario/issue) para que el propietario no reconstruya después qué probó, y para que «declarado» y «demostrado» no se confundan (el caso B13 ya mordió).
- **Mecanismo candidato:** External Validation Assistant (AG-08), versión checklist.
- **Métrica:** pruebas físicas con evidencia estructurada / total; tiempo de preparación por tanda.

### PROC-009 — Mantener el registro de estado y evidencia

- **Disparador:** cada bloque fusionado; cada corrección de evidencia.
- **Objetivo:** que el estado de V8 y la evidencia de cada bloque sean legibles y verdaderos.
- **Pasos:** el implementador actualiza la tabla única de `V8_EXECUTION.md` dentro de la misma PR (desde ADR-005); asientos correctores manuales cuando la evidencia quedó atrasada.
- **Quién:** agente implementador (tabla); propietario/sesión (asientos correctores, cierres por declaración).
- **Frecuencia:** V8_EXECUTION.md: 28 commits (el archivo más modificado del repo); REPOSITORY_STATUS 20; PLAN 19; contrato 15.
- **Tiempo humano:** hoy bajo en el ciclo feliz (lo hace el agente); los episodios de corrección fueron caros (deriva de 19 días en filas «PR pendiente»; fila B4e nunca registrada hasta la auditoría de B4f).
- **Fricción histórica:** tres copias del estado contradiciéndose (PLAN parado en B3b mientras se fusionaban 8 bloques; «Tener el mismo hecho en dos tablas fue lo que las dejó contradiciéndose»); la causa raíz era de permisos (el agente no puede escribir `REPOSITORY_STATUS.md` y la PR de sincronización «dependía de que alguien se acordara»).
- **Riesgo si se automatiza más:** un registro único falso es peor que tres contradictorios — por eso ADR-005 lo protegió con test (`test_documentation_single_source.py`, 4 mutaciones verificadas).
- **Decisión humana:** cierres por declaración (B13) y aceptación de evidencia.
- **Evidencia:** ADR-005; V8_EXECUTION registro y asientos correctores; git log (28/20/19/15 confirmado por esta auditoría).
- **Oportunidad:** ya mayormente eliminada por ADR-005/006 (estructural, no agente). Queda: detección de evidencia faltante o solo-declarada (B13 sin salida de build adjunta) — trabajo de auditor documental.
- **Mecanismo candidato:** parte del Documentation & State Agent (AG-01).
- **Métrica:** días de deriva máxima detectada; nº de asientos correctores necesarios por mes.

### PROC-010 — Reconciliar documentación derivada

- **Disparador:** hoy, ninguno sistemático — se hace cuando alguien lo nota (ese es el problema).
- **Objetivo:** que los documentos derivados (KB, onboarding, gobernanza, README) no contradigan el estado vigente.
- **Estado observado:** `CLAUDE_SIRIUS_KNOWLEDGE_BASE.md` audita el contrato **v1.1** cuando el vigente es **v1.6** (obsoleta desde el 20-jul); su §17 aún describe «máximo 2 ciclos» (eliminado en v1.5); las issues de gobernanza #8/#9/#10/#14/#15/#25 llevan desde el 15–17 jul sin tocar y prescriben acciones ya superadas («Crear y revisar la PR de feat/v8-backup-ui»); la auditoría citada por #126 no existe en `main` (vive en una rama); la spec que #134 debía cumplir estuvo 4 días sin poder leerse desde `main` (PR #128 en cola).
- **Quién:** propietario/sesión, episódicamente (≥6 commits `docs: reconcile/sincronizar` en julio; sesión ADR-005 el 10-ago).
- **Frecuencia:** episódica; la deriva es continua («La deriva no es un accidente, es el comportamiento por diseño de la disposición actual», ADR-005 — resuelto para ESTADO, no para derivados).
- **Tiempo humano:** EST 1–3 h por episodio de reconciliación; el coste mayor es indirecto: cada sesión nueva se onboardea contra documentos falsos.
- **Riesgo si se automatiza:** reescribir documentos autoritativos sin decisión (los canónicos deben quedar fuera); un reconciliador que «corrige» decide.
- **Decisión humana:** qué documento manda cuando dos se contradicen (la jerarquía existe: onboarding §Jerarquía).
- **Evidencia:** KB fechada 20-jul/commit `07ac239`; issues #8–#25 (updated_at); PR #144; hallazgos MS-A07/MS-A08.
- **Oportunidad:** **detección** automática de deriva (contrato vs KB, gobernanza fósil, referencias rotas, evidencia solo-declarada) + borradores de corrección en `docs/implementation/` — el humano decide. Nadie tiene hoy este trabajo asignado: es toil invisible hasta que muerde.
- **Mecanismo candidato:** Documentation & State Agent (AG-01), modo detector.
- **Métrica:** nº de contradicciones vigentes detectadas y corregidas; edad máxima de un documento derivado desactualizado.

### PROC-011 — Registrar decisiones

- **Disparador:** un trabajo produce una decisión (fallo, hallazgo, aprobación).
- **Objetivo:** decisión localizable con contexto, alternativas y consecuencias.
- **Estado observado:** CUATRO registros paralelos: `docs/decisions/` (ADR-001…007, todos nacidos entre el 8 y el 11-ago, todos de la vertical de automatización); §10 del contrato (v1.0→v1.6, decisiones de gobierno); `docs/evolution/DECISIONS.md` + `docs/robotics/head/DECISIONS.md` (EV-*, D-HEAD-*, aprobados en bloque el 22-jul); y decisiones en registros propios (model_studio: «R-11 decidida — el envolvente de gasto se queda en 20 USD»). El registro ADR estuvo vacío ~4 semanas pese a existir su convención (hallazgo C9 de la auditoría de julio: «decisiones operativas registradas solo en issues/PRs»).
- **Quién:** sesión de Claude redacta; propietario aprueba fusionando («Aprobación: la fusión de la PR por el propietario»).
- **Frecuencia:** 7 ADRs en 4 días una vez instrumentada la disciplina; antes, 0 en 4 semanas.
- **Tiempo humano:** EST 15–45 min por ADR (dirigir + revisar).
- **Fricción:** «las decisiones acababan enterradas en comentarios de PR» (ADR-001); los 7 ADRs siguen con cabecera «PROPUESTO» pese a estar fusionados (la aprobación es implícita en el merge — inconsistencia menor que confundirá a futuros lectores).
- **Riesgo si se automatiza:** convertir exploración en decisión (prohibido); un ADR generado que registre una decisión NO tomada.
- **Decisión humana:** la decisión misma, siempre.
- **Evidencia:** docs/decisions/*; contrato §10; H2/C9; git log.
- **Oportunidad:** borrador de ADR generado desde el contexto real (issue+PR+discusión) cuando se detecta una decisión sin registrar; e índice unificado de los 4 registros para que buscar una decisión no exija saber dónde vive.
- **Mecanismo candidato:** Decision Preparation Agent (AG-04) en modo borrador; índice = AG-01.
- **Métrica:** decisiones detectadas sin registro; tiempo de redacción humana por ADR.

### PROC-012 — Redactar especificaciones y documentos de dirección

- **Disparador:** una decisión de producto/dirección tomada en conversación externa.
- **Objetivo:** spec versionada en el repo (Model Studio UI-001, paquete de spikes, documentos rectores).
- **Pasos:** conversación (no observable) → documento → PR documental → merge; a veces materialización DOCX automática (`materialize-approved-docx.yml`).
- **Quién:** agente conversacional redacta (inferencia); propietario aprueba; workflow materializa DOCX.
- **Frecuencia:** ~6 documentos de dirección en la muestra (spikes 25-jul, Model Studio UI-001, rectores del 22-jul…).
- **Tiempo humano:** EST 30 min–2 h por documento (curación).
- **Fricción:** la PR documental espera días en cola (#128: 3 d 22 h) mientras otros procesos la necesitan (MS-A07); una spec se construyó sin issue que la autorizara (MS-A03 → #134 creada a posteriori para tapar el hueco).
- **Riesgo si se automatiza:** el contenido ES decisión de producto; solo el formato/transporte es mecanizable.
- **Decisión humana:** todo el contenido normativo.
- **Evidencia:** PR #128; issues #127/#134; docs/evolution/ARTIFACTS.md; workflow de DOCX.
- **Oportunidad:** eliminar el transporte (borrador directo en rama + PR auto-preparada) y el hueco de gobernanza (toda spec nace con su work item).
- **Mecanismo candidato:** AG-01/AG-04 compartido con PROC-011.
- **Métrica:** días entre aprobación conversacional y disponibilidad en `main`.

### PROC-013 — Reconstruir contexto al abrir cada sesión (onboarding)

- **Disparador:** cada sesión nueva de Claude Code/Cowork (24 sesiones distintas en un mes).
- **Objetivo:** que la sesión trabaje con el estado real y las reglas vigentes.
- **Pasos:** lectura obligatoria de 5–12 documentos (onboarding §Orden obligatorio; /work §1); para «una nueva sesión principal», auditoría inicial de 7 pasos con informe fechado.
- **Quién:** el agente lee; el propietario paga el coste indirecto: mantener fieles los documentos que las sesiones leen («el contexto entre sesiones viaja por documentos del repo que alguien debe mantener fieles») y re-explicar lo que falte.
- **Frecuencia:** 24 sesiones/mes observadas; 3 sesiones concentran 276 commits (una sesión larga se reutiliza días para amortizar el contexto — inferencia apoyada en #124/#132/#136 compartiendo sesión).
- **Tiempo humano:** EST 5–20 min por sesión nueva en dar contexto no documentado; invisible pero multiplicado por 24.
- **Fricción:** la KB que debía acelerar el onboarding está obsoleta (PROC-010); el «Estado ejecutivo» del onboarding está congelado a 20-jul con la advertencia «puede quedar obsoleto».
- **Riesgo si se automatiza:** una KB regenerada con errores envenena TODAS las sesiones siguientes (por eso debe ser verificable contra fuentes).
- **Decisión humana:** ninguna en el caso feliz.
- **Evidencia:** CLAUDE_PROJECT_ONBOARDING.md; CLAUDE_SIRIUS_KNOWLEDGE_BASE.md (§25: mantenimiento manual exigido al final de cada sesión — no observado desde el 20-jul); 24 sesiones por trailer.
- **Oportunidad:** regeneración periódica y verificada de la KB (cada afirmación con su fuente y test de frescura tipo ADR-005/006), y reutilización de sesión como práctica documentada.
- **Mecanismo candidato:** AG-01 (la KB es documentación derivada).
- **Métrica:** afirmaciones de la KB contradichas por fuentes vigentes (hoy: varias; objetivo: 0 con fecha de última verificación visible).

### PROC-014 — Investigación técnica

- **Disparador:** pregunta abierta (arquitectura de memoria, modelos, hardware, recuperación) — hoy ad hoc.
- **Objetivo:** conclusión con evidencia y alternativas para decidir.
- **Estado observado:** los spikes de ADR-001 (paquete operativo 0.2) se ejecutaron en UNA sesión masiva (`01QrGat…`, 155 commits en ramas, 26-jul→3-ago, mensajes en inglés) fuera de la tubería de bloques; el backlog de investigaciones futuras vive en #15 y #10 (fósiles desde el 15-jul); las auditorías de julio re-derivaron varias veces el mismo conocimiento (estado real vs documentado, permisos de tokens) porque no había registro intermedio.
- **Quién:** sesión de Claude dirigida por el propietario. Sin acceso web en el perfil del repo (deny WebSearch/WebFetch/curl) — la investigación con fuentes externas ocurre fuera (ChatGPT/Claude.ai, no observable).
- **Frecuencia:** episódica pero intensa (1 campaña de spikes ≈ 1 semana; 4 auditorías en 2 días).
- **Tiempo humano:** EST horas por investigación (dirigir, leer, decidir); el coste oculto es la **repetición** (investigar dos veces lo que quedó en otra conversación).
- **Riesgo si se automatiza:** agente con web + repo privado + escritura = superficie de prompt injection (análisis en matriz §5); conclusiones no contrastadas tomadas como verdad.
- **Decisión humana:** aceptar la recomendación; todo gasto.
- **Evidencia:** SIRIUS_0.2_ADR001_PAQUETE_OPERATIVO_SPIKES_v1.0.md; sesión 01QrGat (155 commits); #15/#10; inferencia I-repetición del lector de decisiones.
- **Oportunidad:** encargos de investigación acotados con presupuesto, entregando informe con fuentes contrastadas e intento de refutación — en perfil separado con web y sin escritura de código (AG-02). Frecuencia real a validar con el propietario (ver preguntas).
- **Mecanismo candidato:** Research Agent (AG-02); Evaluator (AG-05) para contrastar.
- **Métrica:** investigaciones reutilizadas vs repetidas; horas humanas por investigación.

### PROC-015 — Auditorías del repositorio y del sistema

- **Disparador:** hito o sospecha (incorporación de Claude, activación de la automatización, cierre de B4f) — o dos rondas de hallazgos de la misma familia (regla ADR-004: «cuando una pieza acumula dos rondas de hallazgos, deja de revisarse en serie y se audita en paralelo con lentes explícitas»).
- **Objetivo:** hallazgos verificables sobre estado, deuda, contradicciones.
- **Estado observado:** campaña de 4 auditorías en 2 días (20–21 jul), cada una con informe fechado y decisiones D-1…D-7 pedidas al propietario; auditoría adversarial de 6 lentes en paralelo en ADR-004 (destapó 8 defectos que 9 rondas seriales no vieron); esta misma auditoría (Fase 0) sigue el patrón.
- **Quién:** sesión de Claude ejecuta; propietario encarga y decide sobre los hallazgos.
- **Frecuencia:** ~5 auditorías en un mes.
- **Tiempo humano:** EST 1–3 h por auditoría (encargar, leer, decidir); la ejecución ya es del agente.
- **Fricción:** los informes envejecen sin proceso de caducidad (la auditoría de julio sigue citándose con datos superados); una auditoría citada por una issue no está en `main`.
- **Riesgo si se automatiza:** hallazgos no verificados que consumen atención (falsos positivos); el auditor no debe modificar nada.
- **Decisión humana:** qué hallazgos actuar.
- **Evidencia:** docs/audits/ (4 informes); ADR-004 §auditoría de lentes.
- **Oportunidad:** auditoría periódica de solo lectura con hallazgos verificados (cada afirmación con comprobación adjunta) — el patrón de 6 lentes ya demostró superioridad sobre rondas seriales.
- **Mecanismo candidato:** Repository Auditor (AG-03) + Evidence/QA (AG-05).
- **Métrica:** hallazgos válidos/falsos; hallazgos por hora humana invertida.

### PROC-016 — Seguimiento de defectos intermitentes

- **Disparador:** prueba flaky que tumba Quality (#131/#137: `test_streaming_message_grows…`).
- **Objetivo:** distinguir defecto de producto de ruido de test; decidir arreglar o convivir.
- **Estado observado:** ciclo completo documentado: detección (falla 5/5 en solitario) → issue con tablas medidas → reaparición → diagnóstico con causa medida y 3 intentos descartados (uno con prueba vacua cazada por mutación) → decisión del propietario en 9 min (opción B: no arreglar; «Esta incidencia se queda abierta a propósito: cerrarla borraría el único sitio donde está escrito por qué esa prueba falla a veces»).
- **Quién:** máquina detecta (CI rojo); sesión diagnostica; propietario decide.
- **Frecuencia:** 1 defecto con 2 issues y ≥3 apariciones en la muestra; coste lateral: tiñó de rojo PRs ajenas (#124) y una prueba intermitente «hace de esa reejecución la norma» (convergencia).
- **Tiempo humano:** EST 30–60 min acumulados por defecto.
- **Riesgo si se automatiza:** silenciar pruebas para conseguir verde está prohibido (§9).
- **Decisión humana:** convivir vs arreglar.
- **Evidencia:** #131, #137, comentario diagnóstico del 10-ago.
- **Oportunidad:** menor; el proceso ya funciona razonablemente. Detectar re-apariciones y adjuntar el historial automáticamente ahorraría la parte mecánica.
- **Mecanismo:** parte de AG-03/AG-05.
- **Métrica:** tiempo detección→decisión.

### PROC-017 — Medición de rendimiento y evidencia antes/después

- **Disparador:** requisito de plan de pruebas (PA-025/RNF-003) o hallazgo (N+1 de B12c).
- **Objetivo:** afirmar límites solo con holgura demostrada (ADR-007: criterio 10 %/100 % publicado ANTES de medir).
- **Estado observado:** B12c midió P50/P95 (30 repeticiones, conjunto de referencia), destapó el riesgo de producto (contexto al 89–100 % de sus 300 ms; 501 consultas para 500 recuerdos), y el ciclo B12e (#148/#149) exige medición antes/después — todo ejecutado por agentes, decisión pendiente del propietario.
- **Quién:** agente mide; propietario decide sobre el riesgo destapado.
- **Frecuencia:** 2 PRs en la muestra (#147, #149).
- **Tiempo humano:** bajo ya (leer y decidir).
- **Evidencia:** ADR-007; V8_EXECUTION B12c; #148.
- **Oportunidad:** ya bien automatizado; generalizar el patrón «criterio publicado antes de medir» a otros agentes.
- **Métrica:** mediciones con criterio previo publicado / total.

### PROC-018 — Gobernanza y backlog

- **Disparador:** debería ser periódico; no lo es.
- **Objetivo:** que el Panel Maestro (#8), reglas (#14), backlog (#15), roadmap (#10) y patrón operativo (#25) reflejen la realidad.
- **Estado observado:** todos fósiles desde el 15–17 jul pese a su propia «Regla de mantenimiento»; el estado migró de facto a los documentos del repo sin decisión registrada de abandonar las issues; limpieza episódica en lote (#42/#45 cerradas 3 días tarde).
- **Tiempo humano:** hoy cero (abandonado) — el coste es de confusión futura, no de minutos.
- **Decisión humana:** decidir si ese canal se mantiene, se archiva o se sustituye (es una decisión pendiente real).
- **Evidencia:** updated_at de #8–#25; contenido superado citado en el barrido.
- **Oportunidad:** detectarlo (AG-01) y preparar la decisión (archivar vs regenerar); no automatizar el mantenimiento de un canal que quizá deba morir.
- **Métrica:** issues de gobernanza contradictorias con el estado vigente.

### PROC-019 — Transporte de contexto y autorizaciones entre herramientas

- **Disparador:** cualquier trabajo que cruce ChatGPT ↔ GitHub ↔ sesión Claude ↔ Windows.
- **Objetivo:** que la herramienta siguiente sepa lo que la anterior produjo o decidió.
- **Formas observadas:** mandato multiparte unido a mano (era 1, #25); cuerpos de issue pegados (con truncados); autorización dada en chat y reconstruida a posteriori en GitHub para que fuera verificable (#43: «perfecto mira si termino si si fusiona y continuanos»); evidencia de logs transcrita a issues (#135, #148); hallazgos post-merge de Codex transportados a rondas nuevas; contenido rescatado por BASE64 (#122); encargos largos (como el presente) pegados en una sesión.
- **Quién:** propietario, como bus.
- **Frecuencia:** transversal a casi todos los PROC; es la categoría A del encargo.
- **Tiempo humano:** EST 5–20 min por cruce; el coste mayor es el error de transporte (truncados: 5–6 incidentes con corrupción real, incluido un commit que «en realidad borraba 704 líneas»).
- **Riesgo si se automatiza:** un bus automático de contexto con permisos amplios es el superagente prohibido; debe resolverse por DISEÑO (contexto capturado una vez en el work item) más que por agente mensajero.
- **Decisión humana:** las autorizaciones (que deben quedar en canal verificable — lección de #43).
- **Evidencia:** #25, #43, #122, #135, #148; incidentes INC-1/6/7.
- **Oportunidad:** la estructural del encargo §10: work item canónico como bus (ChatGPT crea/actualiza; Claude recibe el identificador; los resultados vuelven al mismo sitio). Ya es la dirección del contrato; falta cerrar los flancos que siguen a mano (evidencia de logs, hallazgos post-merge, resultados de Windows).
- **Métrica:** cruces manuales por bloque; incidentes de transporte.

### PROC-020 — Operar sesiones de agentes

- **Disparador:** trabajo que la tubería no puede hacer (workflows, docs raíz, diagnóstico, investigación).
- **Objetivo:** que una sesión interactiva haga el trabajo con el contexto correcto.
- **Pasos:** abrir sesión → darle el contexto (issue, encargo) → dirigir (aprobar permisos, decidir en bifurcaciones) → recibir el resultado → fusionar/aplicar.
- **Quién:** propietario como operador; la sesión como ejecutor.
- **Frecuencia:** 24 sesiones en un mes; picos: 6 PRs de reparación desde una sesión en un día (21-jul); 3 PRs de una sesión en una noche (10-ago).
- **Tiempo humano:** EST 10–60 min de dirección por sesión productiva (no observable con precisión; señales de denegaciones de permisos y decisiones intermedias).
- **Fricción:** el humano relanza la sesión tras cada notificación (inferencia sobre la sesión compartida de #124/#132/#136); el trabajo de un run muerto se rehace en sesión (#140: la rama local del implementador murió con el runner y la sesión REHÍZO el arreglo desde el diagnóstico — trabajo tirado).
- **Riesgo si se automatiza:** «un sistema de agentes que no obligue al propietario a convertirse en operador de agentes» es la meta declarada del encargo — pero un lanzador automático de sesiones con permisos del propietario concentra riesgo (identidad compartida).
- **Decisión humana:** qué se lanza y con qué presupuesto.
- **Evidencia:** trailers de sesión; #140 (55 min después del bloqueo, sesión nueva); permission_denials.
- **Oportunidad:** encargos empaquetados (runbooks versionados en el repo que una sesión ejecuta con «sigue X para #N») reducen la dirección por sesión; a futuro, el Coordinator (AG-06).
- **Métrica:** intervenciones del operador por sesión; trabajo rehecho por pérdida de contexto.

### PROC-021 — Gestionar coste y modelos de agentes

- **Disparador:** hoy, solo cuando duele (un run caro o una cuota agotada).
- **Objetivo:** saber cuánto cuesta cada ejecución y qué modelo conviene.
- **Estado observado:** el coste se captura ad hoc cuando un fallo lo expone ($8.47/121 turnos, run 29868614857 en PR #90; $1.42/48 turnos/382 s, run 31188643115 en #135; «modelo claude-sonnet-5» citado una vez); la cuota de Codex paró la revisión 2 h 54 min (#139); presupuesto de Actions gestionado por diseño (cadencia de 6 h justificada por minutos; Quality Windows solo bajo demanda «porque factura 2x»); decisión R-11 de model_studio: envolvente de gasto 20 USD.
- **Quién:** propietario, reactivamente.
- **Frecuencia:** 4–5 menciones de coste en un mes; ninguna sistemática.
- **Tiempo humano:** bajo hoy; el riesgo es de ceguera (no hay serie histórica de coste/turnos/resultado por rol).
- **Decisión humana:** presupuestos y cambios de modelo.
- **Evidencia:** PR #90; #135; #139; quality.yml; reconcile §9.1; model_studio R-11.
- **Oportunidad:** libro mayor de ejecuciones (run, rol, modelo, turnos, coste, desenlace) alimentado de lo que los workflows ya saben — prerequisito del Model Evaluator/Router (AG-07), que sin datos es prematuro.
- **Métrica:** % de ejecuciones de agentes con coste y desenlace registrados.

---

## Trabajo de pegamento (síntesis de la Fase 3)

Puntos donde la presencia del propietario existe solo porque dos sistemas no están conectados (o no se confía la conexión):

| # | Pegamento | Evidencia | ¿Conectable? |
|---|---|---|---|
| G1 | Chat → GitHub: pegar cuerpos de work item | #126 truncados; contrato §0 | Sí (borrador directo por agente; el humano aprueba) |
| G2 | Logs de Actions → issue: transcribir evidencia forense | #135, #148 | Sí (triaje automático de solo lectura) |
| G3 | Notificación → decisión: leer crudo y reconstruir qué pasó | latencias 14 h 50 m | Sí (aviso con diagnóstico verificado adjunto) |
| G4 | Sandbox Codex → repo: rescates BASE64 | #122 (57 KB en comentarios) | Parcial (ya mitigado al mover revisión al pipeline; corrección sigue manual) |
| G5 | Hallazgos post-merge → ronda nueva | #143→#146 | Sí (recolector de hallazgos sobre `main`) |
| G6 | Windows real → repo: declaración/transcripción | B13 «sin evidencia escrita»; #122 | Parcial (captura estructurada; la ejecución sigue humana) |
| G7 | Chat de autorización → registro verificable | #43 (5 bloqueos) | Resuelto para merge (`fusiona`); pendiente para otras autorizaciones |
| G8 | Estado real → documentos derivados (KB, gobernanza) | KB v1.1 vs v1.6 | Sí (detector de deriva + borradores) |
| G9 | Head aprobado → puerta de merge: contabilidad manual | #123 | Ya corregido en la maquinaria (endurecimiento v1.4) |
| G10 | Sesión ↔ sesión: re-dar contexto que quedó en otra conversación | inferencia (spikes; encargo presente) | Por diseño (work item canónico), no por mensajero |

## Dónde se va el tiempo humano (síntesis de latencias y esfuerzo)

**Hecho central medido:** la máquina opera en minutos; las esperas largas son siempre de atención humana. Ciclo autónomo #148: issue→PR 14 min, ronda revisión+corrección 10–20 min, merge tras `fusiona` 18–31 s. Esperas humanas: `fusiona` 16 min–37 h; rescate de parada falsa 14 h 50 min; #126 ≥6 días; #122 >9 días esperando la ejecución Windows.

Ordenado por coste humano estimado (frecuencia × esfuerzo + latencia inducida), con la advertencia del límite 4 (sin time-tracking):

1. **Desatascar y hacer forense de la automatización** (PROC-005/006): ≥15–20 episodios/mes, EST 15–60 min cada uno, más las PRs de meta-reparación que generan (horas). La familia dominante de agosto.
2. **Supervisar la revisión adversarial manual** (PROC-007, era #122): ~25 rondas manuales con verificación; en vías de reducción por v1.4, pero el defecto de detección de #148 la mantiene viva.
3. **Validación física en Windows** (PROC-008): pocas tandas pero bloquean V8 entera; latencia de días.
4. **Redactar/curar work items y specs** (PROC-001/012): ~7.600 palabras solo en 9 issues.
5. **Vigilar y autorizar** (PROC-003/004): gestos de minutos multiplicados por ~30 bloques, con coste real en latencia/interrupción.
6. **Reconciliar documentación derivada** (PROC-010/013/018): episódico pero con coste compuesto (sesiones onboardeadas contra documentos falsos).
7. **Investigar y auditar** (PROC-014/015): intenso cuando ocurre; la ejecución ya es de agentes, el coste humano es dirección y decisión.

## Contraste de la hipótesis rectora (encargo §16)

> «El mayor cuello de botella de Sirius ya no es escribir código; es la coordinación de conocimiento y trabajo alrededor del código.»

**A favor (hechos):** V8.1 «no tiene ya trabajo automatizable pendiente» — lo que bloquea es Windows real y clave real; el ciclo de código corre en minutos sin humano (#148: 33 min, 3 rondas autónomas); las esperas dominantes son humanas (tabla anterior); la muestra de agosto es casi toda meta-trabajo (reparación, disciplina, documentación), no producto; el propio contrato nació para «eliminar trabajo manual repetitivo» y sus 6 versiones son la historia de ir quitando coordinación manual.

**Matices que la evidencia obliga a añadir (la versión fuerte NO se sostiene tal cual):**
1. El mayor consumidor humano de agosto no fue «coordinación de conocimiento» genérica sino **supervisar y reparar la propia automatización** — ingeniería de la máquina, con 19+15+8 defectos en tres episodios y patrones propios ya catalogados. Un plan de agentes que añada máquinas sin presupuestar su mantenimiento REPITE este coste, no lo elimina.
2. El bloqueo material de Sirius 0.1 hoy es **físico** (Windows real, clave real, evaluación humana PS-01…PS-07) — ningún agente lo elimina; solo se puede estructurar su captura (PROC-008).
3. La parte de coordinación que queda es real pero está **concentrada**: desatascos, transporte de evidencia, autorizaciones, documentación derivada. Es eliminable por partes pequeñas, no requiere «más autonomía del programador» — coherente con la conclusión de la PR #139 (la tubería «consume decisiones ya tomadas; el resto del trabajo las produce»).

**Veredicto:** hipótesis confirmada en su forma débil (el código ya no es el cuello de botella), refinada en su forma fuerte: el siguiente salto no es un coordinador universal, sino eliminar las tres bolsas concretas — supervisión de fallos, transporte de contexto/evidencia, y deriva documental — sin crear una nueva bolsa de mantenimiento de agentes.

**Qué NO demuestra la evidencia:** cuánto tiempo real pasa el propietario en ChatGPT/sesiones (no observable); que la frecuencia de fallos de la automatización vaya a mantenerse (podría decaer al estabilizarse — o no: cada capa nueva trajo su familia de defectos); que la investigación sea un toil frecuente (solo hay una campaña observada).

## Cumplimiento del criterio de parada

1. Procesos repetidos observables con ficha: 21 fichas cubren todo lo repetido hallado en la muestra ✔
2. Cada ficha lleva evidencia concreta o marca de hipótesis/estimación (EST, inferencias señaladas) ✔
3. Handoffs principales representados (G1–G10) ✔
4. Explicación de dónde se va el tiempo humano ✔ (con el límite declarado: latencias medidas, esfuerzos estimados)
5. Ranking por trabajo eliminado y riesgo → `AGENT_OPPORTUNITY_MATRIX.md` ✔
6. Un único piloto recomendado → matriz §10 ✔
7. Taxonomía A–F del encargo §4 revisada: A (transferencia) → PROC-001/019; B (documentación) → PROC-009–013; C (investigación/decisión) → PROC-011/014; D (GitHub/coordinación) → PROC-002–007/018; E (validación/evidencia) → PROC-008/016/017; F (administración de agentes) → PROC-020/021 ✔
- Regla de las dos rondas: la verificación adversarial posterior a este borrador se registra en la matriz §12; si dos rondas destapan la misma familia omitida, se revisará la taxonomía entera antes de ampliar el inventario.

## Adenda (12 de agosto de 2026)

Las afirmaciones «a fecha de hoy» de este documento describen el estado del 11–12 de agosto y varias caducaron horas después de escribirse (patrón «afirmaciones que caducan al retirar lo que describían»):

- La issue #148 salió de `sirius:failed-safely` tras una **segunda** intervención humana la misma noche, la PR #149 se fusionó (squash `d7cec31`) y la incidencia quedó `sirius:completed`, cerrada por `github-actions[bot]` el 2026-08-11T21:35:03Z. El episodio completo suma DOS desatascos humanos para un cambio de una consulta — dato adicional a favor de la ficha PROC-005, no en contra.
- La PR #122 y la issue #126 seguían en el estado descrito al escribir esta adenda; verificar antes de citar.
