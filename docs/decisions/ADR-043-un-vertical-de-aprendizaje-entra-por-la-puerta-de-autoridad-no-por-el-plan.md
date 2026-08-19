# ADR-043 — Un vertical de aprendizaje entra por la puerta de autoridad, no por el plan

- Estado: PROPUESTO
- Fecha: 2026-08-19
- Aprobación: pendiente; en este repositorio, la fusión de la PR por el propietario

Este ADR es además la **nota de arranque** de la rama
`claude/sirius-learning-audit-ixtr0g` (ADR-001, skill `disciplina-evidencia`):
se escribió y se publicó **antes del primer cambio de contenido**, y su criterio
de parada se decidió **antes de ver ningún resultado de la auditoría**.

## Contexto y problema

El propietario aporta dos documentos —`01_HERMES_LEARNING_AUDIT` (auditoría
factual del mecanismo de aprendizaje de Hermes Agent) y
`02_SIRIUS_LEARNING_INTEGRATION_BRIEF` (brief normativo)— y pide **integración
de diseño, no implementación**: contrastar los adjuntos contra el repositorio,
auditar las costuras de aprendizaje del Work Engine, determinar el punto mínimo
de enganche y proponer dónde entra este vertical en el plan.

El fallo que este trabajo debe evitar no es técnico: es de autoridad. Un brief
bien escrito se lee como una decisión tomada. Si sus contenidos aterrizan
directamente en `PLAN.md`, en el contrato operativo o en `docs/canonical/`, el
repositorio pasa a declarar como aprobado algo que nadie aprobó. Es exactamente
la familia de deriva que `WORK_PROCESS_AUDIT.md` ya registró (PROC-010,
PROC-011) y que ADR-005 cerró para V8.

### ¿Puede el sitio del arreglo observar el fallo que arregla?

Sí, y de forma mecánica. El fallo se manifiesta como una cosa concreta y
observable: **el diff de esta rama tocando un fichero que declara estado o
autoridad aprobados**. El arreglo vive en el mismo sitio que el fallo —el propio
diff—, así que puede observarlo sin reconstruir la semántica de ningún otro
sistema. El predicado es comprobable con un comando, no vigilado a mano:

```
git diff --name-only origin/main...HEAD
```

no debe contener `docs/canonical/**`, `docs/implementation/PLAN.md`,
`docs/implementation/AUTOMATION_OPERATING_CONTRACT.md`,
`docs/implementation/SIRIUS_WORK_ENGINE_PLAN_IMPLEMENTACION.md`,
`docs/implementation/SIRIUS_WORK_ENGINE_ARQUITECTURA_MINIMA.md`,
`REPOSITORY_STATUS.md`, `src/**`, `.github/**` ni `scripts/**`.

El informe de integración es **evidencia** y vive en `docs/audits/`. Este ADR es
la **propuesta**, y su estado es PROPUESTO hasta que el propietario lo fusione.

### Qué NO garantiza esto (escrito antes de auditar)

- **No autoriza el Learning Engine**, ni su implementación, ni una reserva de
  hueco en el plan aprobado. Un ADR PROPUESTO no mueve una fase.
- **No audita Hermes.** El repositorio `NousResearch/hermes-agent` no está en el
  alcance de esta sesión. El adjunto 01 se toma como **descripción dada** sobre
  Hermes; solo se verifica contra el código lo que afirma **sobre Sirius**.
- **No arregla la PR #207.** Cualquier defecto que la auditoría encuentre en A5
  se reporta, no se corrige aquí: tocar A5 para meter aprendizaje está prohibido
  por el propio brief y por el criterio de parada de más abajo.
- **No mide nada cuantitativo**: ni coste por candidato, ni calidad de modelos,
  ni algoritmo de deduplicación, ni umbrales de auto-promoción. Esas decisiones
  se miden, no se adivinan, y no hay datos que medir todavía.
- **No fija el backend físico** del conocimiento (fichero, SQLite, vector store):
  ADR-019 hace depender la representación definitiva de I3 **e** I4, y I4 sigue
  sin resolverse.
- **No garantiza que el punto de enganche recomendado sobreviva** a las enmiendas
  C1 y C2 del contrato (E1b), que todavía no existen.

## Criterio de parada (escrito ANTES de ver ningún resultado)

Cualquiera de estas condiciones detiene la recomendación y la convierte en una
pregunta al propietario, en vez de en un diseño:

1. **A5 y el dominio son intocables.** Si el enganche mínimo exige modificar
   `src/sirius_engine/domain/**`, el puerto de almacén, o cualquier fichero de la
   rama de la PR #207, no se propone diseño v0: sube la pregunta.
2. **Clase de trabajo nueva = decisión del propietario.** Si el vertical exige
   una fila nueva en la tabla de autoridad por clase (contrato v1.7 §11,
   ADR-041), eso no entra como recomendación técnica: entra como enmienda de
   contrato, que es del propietario.
3. **Una garantía no verificable se declara insostenible, no se suaviza.** Si
   alguna de las tres invariantes duras —el Extractor no puede escribir
   conocimiento activo; el Refutador usa un modelo distinto *y el motor puede
   comprobarlo*; el Promotion Gate falla cerrado— resulta **no comprobable** con
   lo que el motor tiene, se escribe «no sostenible hoy» y por qué. No se
   reformula para que parezca cumplida.
4. **Regla de las dos rondas.** Si dos rondas de refutación adversarial devuelven
   objeciones de la misma familia, se prohíbe seguir parcheando el diseño: se
   escribe el patrón, se busca la raíz y se decide seguir, retirar o escalar.
5. **Sin corpus no hay aprendizaje.** Si el motor no ha ejecutado todavía ningún
   WorkItem real con un Worker real, la recomendación de calendario debe ser
   «todavía no», por muy bueno que resulte el diseño. Un Learning Engine sin
   experiencia de la que aprender es un generador de ruido con coste.

## Opciones consideradas

Para el punto de enganche de una revisión sidecar al cerrar un WorkItem, con el
código real delante (informe §6.1):

1. **Dentro de la transición del dominio** (`domain/work_item.py:186`,
   `deliver()`). Descartada: el dominio son instantáneas inmutables sin efectos,
   y un fallo del sidecar viviría dentro de la entrega.
2. **Dentro del puerto de almacén** (`ports/store.py:73`,
   `deliver_work_item()`). Descartada: obliga a toda implementación del puerto y
   mete el aprendizaje en la transición terminal.
3. **Un WorkItem de clase `aprendizaje` despachado por el motor.** Descartada:
   exige tocar `WorkItemClass`, la tabla de autoridad de A5 —prohibido— y el
   contrato v1.7 §11.1, que dice literalmente que «una clase que no aparezca
   aquí no puede crear WorkItems hasta que se añada».
4. **Un lector del diario, fuera del camino de escritura** (`list_events()` /
   el JSONL de `adapters/durable/journal.py`). Elegida.

Para la forma de ENTRADA de este trabajo en el repositorio:

- **A. Editar `PLAN.md` y el contrato con el vertical de aprendizaje.**
  Descartada: declararía aprobado algo que nadie aprobó.
- **B. Informe en `docs/audits/` + ADR `PROPUESTO`, sin tocar ningún documento
  de estado o autoridad.** Elegida.

## Decisión

**Dos decisiones, y ninguna autoriza construir nada.**

1. **Forma de entrada.** El contraste de los adjuntos y la auditoría de costuras
   entran como evidencia en
   `docs/audits/SIRIUS_LEARNING_SEAM_AUDIT_2026-08.md`. Ningún documento que
   declare estado, autoridad, plan o alcance aprobados se modifica. Lo que pueda
   convertirse en decisión vive aquí, en estado `PROPUESTO`, y solo la fusión de
   la PR por el propietario lo aprueba.

2. **Si algún día se construye, se engancha por la opción 4.** El aprendizaje
   v0 **no es un WorkItem**: es un lector del diario, invocado por una orden del
   propietario, que no crea trabajo, no toca estado del motor y no puede escribir
   conocimiento activo. Es la única de las cuatro opciones que no exige tocar el
   dominio, ni el puerto, ni A5, ni el contrato.
   **Corregido tras la segunda ronda adversarial**: «la mejor de las cuatro» no
   es «recomendada». La comparación puntúa seis ejes internos al motor y omitía el
   criterio de parada de `AGENTS.md` —«introducir otro proceso, servidor, agente o
   base de datos»—, que esta opción dispara dos veces: el staging propio y un
   punto de entrada que no existe (`pyproject.toml` declara `sirius`, `sirius-voz`
   y `sirius-obs`, ninguno del motor). El estatus correcto es **pregunta al
   propietario**, no recomendación.

3. **No se recomienda construir el vertical, y el calendario es «todavía no».**
   Dos rondas adversariales devolvieron objeciones de la misma familia —«esta
   pieza ya existe con otro nombre»— y **la regla de las dos rondas se activó**.
   La raíz: **el brief se escribió contra los documentos de Sirius, no contra su
   código**. Doce de sus trece piezas ya existen construidas y probadas, en dos
   carriles. En particular, el argumento con el que salvé el diseño en la primera
   ronda era falso: el tramo `staging → Gate → activo` **sí existe**, y es
   `sirius_aggregate_reviews.py` (dos revisores de proveedores distintos, reglas
   fijas, fail-closed ante JSON inválido o SHA no demostrable, aprobación solo si
   ambos aprueban el mismo SHA) más `sirius_apply_verdict.sh` (coincidencia exacta
   entre el SHA declarado, el head de la PR y el último head que superó Quality).
   Se retira, por tanto, la recomendación de construir; se conserva el contraste,
   que es lo que hacía falta; y sube al propietario la pregunta que ordena a las
   demás: **si lo que debe crecer es el mecanismo ya probado, en vez de uno nuevo
   al lado** (informe §12, D-9).

Se declara además, sin suavizarlas (criterio de parada 3): **de las seis
garantías no negociables del encargo, cinco no son sostenibles hoy dentro del
motor.** La primera redacción de este ADR declaró solo una; la segunda ronda
encontró las otras cuatro y se aplica el mismo criterio a todas (informe §14.4):

- «Extractor y Refutador no escriben conocimiento activo»: **expresable, no en
  vigor**. `compute_permission_envelope`, `resolve_capabilities`,
  `validar_egress_fail_closed` y `project_worker_request` no tienen ningún
  llamador en `src/` — solo en `tests/`. La única superficie que hoy restringe a
  un Worker es `--allowedTools` en el YAML, y para el revisor está configurada con
  `Bash` y `--dangerously-skip-permissions`.
- «Aprobación ligada al hash exacto»: existe y funciona, pero **solo en bash y
  solo sobre la vía GitHub**; un lector del diario con staging propio no hereda
  ninguna de esas comprobaciones.
- «Fail-closed»: dos fallos abiertos verificados en los caminos que el pipeline
  usaría (`recovery.py:93-95` y `context_recall.py:262`).
- «El egress para la evidencia privada»: `validar_egress_fail_closed` solo sabe
  mirar `ContextFragment`, y **en todo `src/` no se construye ni uno**.
- «El Refutador usa un modelo distinto del proponente»: **no comprobable.** Ni
`AgentProfile` (`domain/profile.py:38-48`), ni `WorkerRequest`
(`worker_request.py:44-54`), ni `Run.worker` (`domain/run.py:71`) llevan
identidad de modelo, así que el motor no puede comprobarla. Es además una
divergencia respecto de la arquitectura §3.3, que sí la pide. Mientras no se
cierre, el Promotion Gate tiene que fallar cerrado: sin dato de modelo, no
promueve.

## Comprobación que la sostiene

```
git log -1 --oneline                     -> a25ee3b (main)
API de GitHub, pull request 207          -> open, merged:false, unstable, head 9e3a79b
uv run pytest tests/automation/test_registro_de_decisiones.py  (worktree de A5)
                                         -> 1 failed: ADR-042 duplicado con main
uv run python scripts/siguiente_adr.py --solo-numero           -> 43
uv run pytest tests/automation/test_registro_de_decisiones.py \
             tests/unit/test_pa_sp_traceability.py             -> 126 passed
ls src/sirius_engine/ports/              -> __init__ github_mirror store world
                                            (no hay puerto de Worker)
ls experiments/                          -> solo work_engine_spike_i3
grep -rn "WorkPackage\|WorkResult" src/  -> ningún tipo; solo Mapping opacos
grep -rniE "claude|openai|anthropic|gpt-|sonnet|opus" src/sirius_engine/
                                         -> ningún acoplamiento a modelo o proveedor
grep -rni "inspect.ai|inspect_ai" .      -> solo documentos, nunca código
```

Y el predicado que hace observable el fallo que este ADR previene:

```
git diff --name-only origin/main...HEAD
  docs/audits/SIRIUS_LEARNING_SEAM_AUDIT_2026-08.md
  docs/decisions/ADR-043-un-vertical-de-aprendizaje-entra-por-la-puerta-de-autoridad-no-por-el-plan.md
```

Ningún documento de estado, plan, contrato ni canónico aparece en esa lista.

## Consecuencias

- El propietario recibe un informe con evidencia y **ocho decisiones** aisladas
  (informe §12), en vez de un plan editado que dé por hechas cosas que no lo son.
- El vertical de aprendizaje queda **sin autorizar**, que es su estado real: la
  excepción de `docs/evolution/STATUS.md:27-35` ampara el Work Engine
  «estrictamente según ADR-020 y su plan aprobado», y esto no está en ese plan.
- Queda registrado que **nueve de las trece piezas** que el brief describe como
  diseño nuevo ya existen o ya estaban decididas (informe §4). El trabajo real es
  mucho menor que su brief, y esa es la conclusión más útil de todo el ejercicio.
- Queda registrada una divergencia entre el código y la arquitectura §3.3
  (identidad de modelo/runtime por Run) que **no es alcance de aprendizaje** y
  que conviene cerrar por su propio mérito cuando exista el primer Worker real.
- Queda reportado, con la prueba reproducida, que la PR #207 está en rojo por dos
  ADR-042 en el registro. Para no repetir la colisión, este trabajo toma el 043 y
  el duplicado de A5 debería renumerarse a **044**.
- Quedan registrados tres defectos verificados que **no son de aprendizaje** y
  existen hoy (informe §14.5): el cuerpo de la incidencia entra sin filtro de
  autor dentro de `_texto_cronologico_de_confianza` y el puerto lo hace
  imposible de arreglar (`mirror_projection.py:188-197`,
  `ports/github_mirror.py:61-65`); «no pude leer el resultado» se convierte en
  «éxito con resultado vacío» en el barrido de recuperación y `RemoteRunStatus`
  no tiene `UNKNOWN` (`recovery.py:93-95`, `ports/world.py:23-33`, familia que
  ADR-036 ya cerró para el espejo); y `registrar_gasto` sobre un WorkItem
  `DELIVERED` lanza `IllegalTransitionError`, así que el presupuesto no puede
  gobernar nada posterior a la entrega.
- Si el propietario no autoriza nada, no queda ninguna deuda: borrar estos dos
  documentos deja el repositorio exactamente como estaba.

## Alternativas descartadas y por qué

- **Reservar un hueco en el plan aprobado** («Fase L» anotada en `PLAN.md`
  aunque sin construir). Descartada: una fase no aprobada anotada como si lo
  estuviera es la deriva PROC-011 vista del revés, y no cuesta nada añadirla más
  tarde si se aprueba.
- **Copiar el patrón de Hermes tal cual** (revisión de fondo que escribe directa
  en memoria/skills). Descartada por el propio adjunto 01 y por el modelo de
  autoridad de Sirius: el modelo que detecta el aprendizaje no puede activarlo.
- **Un Learning Agent o un Memory Agent.** Descartada: la arquitectura §9 ya lo
  cerró («No hay "Agente de memoria"»), y el diseño elegido no lo necesita.
- **Adoptar Inspect AI ahora.** Descartada: no está en el árbol, el inventario ya
  decidió dejarlo fuera del motor (`SIRIUS_WORK_ENGINE_INVENTARIO.md:187`) y
  adoptarlo entra en «adoptar frameworks o proveedores no aprobados», que sigue
  expresamente no autorizado.
- **Un segundo barrido periódico para disparar la revisión sola.** Descartada: el
  contrato §9.1 permite exactamente una ejecución periódica y ya está gastada por
  el reconciliador.
