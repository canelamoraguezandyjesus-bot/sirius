# ADR-057 — Supervisor de la vía GitHub: detectar Runs perdidos y actuar

- Estado: PROPUESTO
- Fecha: 2026-08-21
- Aprobación: fusión de la PR de la incidencia #232 por el propietario

## Contexto y problema

C1 (incidencia #232, Work ID `SIRIUS-WORK-ENGINE-C1-001`) autoriza al motor,
por primera vez, a **actuar** sobre sus propios Runs (contrato v1.8 §12.2):
reintentar, sustituir el Worker o escalar cuando uno se pierde. Hasta ahora
(A2, recuperación al arrancar) el motor solo reconciliaba contra el mundo con
un doble de pruebas; A3 solo mira la vía GitHub, sin tocar nada; y S3 midió
seis bordes reales de `STATUS` sobre runs de Actions, pero declaró **NO
CONCLUYENTES** dos cotas que el plan daba por hecho que C1 consumiría: la
cadencia mínima de sondeo, y el umbral de "puede seguir vivo" de un run en
`queued` con `total_jobs==0`.

Tres preguntas de diseño no las responde el plan ni el contrato, y hay que
decidirlas para poder escribir código:

1. **¿Cómo se decide `LOST` sin inventar la cota que S3 dejó abierta?**
2. **¿Cómo se evita que el motor y `sirius_reconcile.sh` actúen dos veces
   sobre el mismo atasco**, si sus dominios pudieran solaparse?
3. **¿Qué significa "reactivar" en un sistema donde C2 (el despachador real
   hacia GitHub) todavía no existe?**

## Criterio de parada (escrito ANTES de decidir)

Antes de escribir una sola línea de `src/sirius_engine/supervisor.py` se fijó
esto:

- Si alguna decisión de diseño exige un número que S3 declaró NO CONCLUYENTE
  (cadencia de sondeo, umbral de `queued` sin duración) y no hay forma de
  dejarlo configurable con su valor por defecto marcado como provisional:
  **parar y emitir `BLOCKED_BY_DECISION`**, no inventar la cifra.
- Si "reactivar" resulta exigir escribir en GitHub (aplicar una etiqueta,
  disparar un workflow) y no existe todavía ningún adapter de escritura en
  este repositorio: **no construir uno nuevo por iniciativa propia** -eso es
  literalmente la descripción de C2 ("el despachador y la escritura mínima en
  GitHub")-, sino limitar C1 a la capa de dominio (crear el Run del siguiente
  intento) y decirlo explícitamente como límite conocido.
- Toda prueba de terminado (C1-P1 a C1-P5) tiene que poder construirse sin
  tocar la red ni GitHub real, con dobles deterministas -igual que exige el
  requisito de validaciones obligatorias de la incidencia.
- Dos rondas seguidas de un defecto de la misma familia (p. ej., una prueba
  que no distingue "se saltó la acción" de "se intentó y falló") paran el
  trabajo para buscar la raíz, no para parchear la prueba (regla de las dos
  rondas, ADR-001).

## Opciones consideradas

### 1. Cómo decidir `LOST` sin inventar la cota de S3

- **(a) Fijar un umbral de duración para `total_jobs==0` en `queued`** (p.
  ej., "20 minutos sin job = perdido"). Descartada: es exactamente la cifra
  que S3 declaró NO CONCLUYENTE, y ADR-046/el informe de S3 avisan
  expresamente de que un run puede seguir en `queued` sano durante horas
  (fila 2 de la tabla, medida real: >48 h).
- **(b) Reutilizar `Run.deadline`, que ya existía antes de esta incidencia**
  (arquitectura §3.3, consumido por `Run.mark_lost` desde A1/A2). El
  observador nuevo (`GitHubActionsRunObserver`) combina la señal estructural
  medida por S3 (`total_jobs==0`: "no arrancó todavía") con esa cota
  absoluta, y solo entonces reporta `LOST`. **Adoptada**: no introduce
  ningún número nuevo -la duración la fijó quien preparó el Run, en un
  bloque anterior a este-, y es exactamente el mecanismo que
  `recovery.py`/`Run.mark_lost` ya esperaban recibir de "bloques
  posteriores" (su propio docstring lo dice).

### 2. Cómo evitar la carrera con el reconciliador

- **(a) Leer los comentarios-marcador del reconciliador** (`<!--
  sirius-stuck:... -->`) antes de actuar, vía el espejo de solo lectura
  (A3). Descartada como mecanismo PRINCIPAL: exige mapear un `WorkItem` del
  motor a un número de incidencia de GitHub, un dato que el dominio actual
  no modela (`WorkItem` no tiene campo de número de incidencia), y
  construirlo sin que la incidencia lo pida sería inventar alcance.
- **(b) Restringir la jurisdicción del motor a `WorkItem` de autoridad
  `MOTOR`** (contrato §11, `domain/authority.py`, ya existente desde E1a).
  El reconciliador (`sirius_reconcile.sh`) solo vigila incidencias de
  GitHub, es decir, exclusivamente `WorkItem` de autoridad `INCIDENCIA`
  (`programacion`, `auditoria`). Si el supervisor nunca actúa sobre esa
  autoridad, los dos dominios no se solapan nunca, y "no hay carrera" deja
  de depender de una lectura -es una propiedad estructural-.
  **Adoptada como guarda primaria**, más un marcador de idempotencia propio
  (`SupervisorJournal.has_episode`, C1-P2) para que dos pasadas del PROPIO
  supervisor sobre el mismo `Run` produzcan una sola acción. Las dos
  guardas se verificaron con mutación real contra el código de producción
  (ver más abajo): quitar cualquiera de las dos hace fallar su prueba.

### 3. Qué significa "reactivar" sin despachador real

- **(a) Construir un adapter de escritura a GitHub** (aplicar
  `sirius:implement-requested` + `sirius:planned`, la "receta exacta" que
  `sirius_reconcile.sh::reactivation_labels` usa) para que la reactivación
  tenga efecto real. Descartada: la incidencia prohíbe expresamente tocar
  `.github/**` y `scripts/automation/**`, no añadir dependencias nuevas, y
  el plan de implementación asigna esa escritura mínima explícitamente a
  C2 ("el despachador"), que depende de C1 -no al revés-. Construirla aquí
  adelantaría trabajo de otro bloque sin que nadie lo haya pedido.
- **(b) Limitar C1 a la capa de dominio**: "reactivar" crea un nuevo `Run`
  (`store.retry_run`, ya existente desde A1) con el mismo Worker; "sustituir"
  crea uno con otro Worker (`store.substitute_run_worker`, también
  existente); "escalar" usa `escalate_work_item` +
  `construir_escalada(causa=AUSENCIA_DE_CONVERGENCIA)` (arquitectura §10,
  causa 7, ya existente desde A5). **Adoptada**: el "reponer lo que el
  consumo retiró" de la incidencia se traduce, al nivel que C1 gobierna hoy,
  en reponer el intento -el mismo principio que
  `reactivation_labels`, sin construir su equivalente de escritura a
  GitHub, que no está autorizado ni es necesario mientras no exista un
  despachador que lo consuma-.

## Decisión

Añadir, dentro de `src/sirius_engine/`, sin modificar ningún fichero
existente salvo los tres formateados por `ruff format`:

- `domain/supervision.py`: `SupervisionDecision`, `SupervisorPolicy`
  (`max_reactivaciones`, `max_sustituciones`, `worker_alternativo`, todos
  con valor por defecto marcado como provisional -ninguno viene de una
  medición de S3-), `decidir_politica` (función pura sobre `Run.intento`) y
  `SupervisionEpisode`.
- `ports/run_actions_probe.py` + `adapters/github_actions_run_probe.py`
  (real, sobre `gh api`) + `adapters/fixture_run_actions_probe.py` (doble de
  pruebas): la lectura estructural (`total_jobs`) que A3 no exponía.
- `adapters/github_actions_run_observer.py`: implementación real de
  `ports.world.RunWorldObserver` (A2), con la clasificación de las seis
  filas de S3-P1 y la regla de LOST de la opción 1(b).
- `ports/supervisor_journal.py` + `adapters/memory_supervisor_journal.py`:
  el diario de episodios de supervisión y el marcador de idempotencia.
- `supervisor.py`: `supervise_runs`, que reutiliza
  `recovery.run_recovery_sweep` (A2) y aplica las cuatro guardas
  (idempotencia, propiedad, jurisdicción, no-creación-de-trabajo)
  documentadas en su propio docstring.

## Comprobación que la sostiene

Todas las validaciones obligatorias, en verde sobre el árbol completo:

```
$ uv run ruff format --check .
454 files already formatted
$ uv run ruff check .
All checks passed!
$ uv run mypy src tests
Success: no issues found in 432 source files
$ git diff --check
(sin salida)
```

50 pruebas nuevas, todas verdes
(`uv run pytest tests/engine/test_supervisor.py
tests/engine/test_supervision_policy.py
tests/engine/test_github_actions_run_observer.py
tests/engine/test_github_actions_run_probe.py -q` → `50 passed`), cubriendo
C1-P1 a C1-P5 tal como los enumera la incidencia.

**Prueba por mutación (ADR-001 §3), sembrada de verdad contra
`src/sirius_engine/supervisor.py`, vista fallar y revertida:**

1. Quitar el bloque `if work_item is None: skipped_foreign.append(...);
   continue` (la comprobación de propiedad) →
   `pytest tests/engine/test_supervisor.py -k c1_p3` →
   **2 failed** (`AttributeError: 'NoneType' object has no attribute
   'clase'` en `_bajo_jurisdiccion_del_motor`, justo donde un Run ajeno sin
   `WorkItem` propio ya no se detiene). Revertido; vuelve a **24 passed**
   sobre el módulo completo.
2. Quitar `if journal.has_episode(run_id): continue` (el marcador de
   idempotencia) → `pytest tests/engine/test_supervisor.py -k c1_p2` →
   **2 failed** (`SupervisionError(run_id='RUN-0001', mensaje="Run
   'RUN-0001-S2' already exists")`: la segunda pasada reintenta la MISMA
   reactivación en vez de saltársela). Revertido; vuelve a **24 passed**.
   La primera versión de esta mutación no la detectaba ninguna prueba -el
   fallo se capturaba en `errors` y `acted` seguía vacío en ambos casos,
   idéntico al comportamiento correcto-; se reforzó
   `test_c1_p2_dos_pasadas_sobre_el_mismo_atasco_producen_una_sola_accion`
   para exigir también `segunda.errors == ()`, no solo `segunda.acted ==
   ()`, antes de aceptar la mutación como cubierta (regla de las dos
   rondas, ADR-001: el primer intento de prueba no distinguía "se saltó" de
   "se intentó y falló").
3. Añadir `store.create_work_item(...)` dentro de la rama `ESCALATE`
   (`_escalar`, tras `escalate_work_item`) →
   `pytest tests/engine/test_supervisor.py -k c1_p4` → **2 failed**
   (`AssertionError`: el conjunto de `work_id` del diario gana
   `WI-0001-SEGUIMIENTO`). Revertido; vuelve a **24 passed**. La primera
   versión de `_todos_los_work_ids` (el helper de la prueba) miraba un único
   `work_id` fijo y no habría detectado un `WorkItem` inventado bajo otro
   id: se corrigió para derivarlo del diario completo
   (`rebuild_state(store.list_events()).work_item_versions`) antes de
   aceptar la mutación como cubierta.

Ninguna mutación sobrevivió sin que su prueba cayera; las dos rondas que sí
fallaron al principio (mutaciones 2 y 3) se debieron a debilidad de la
prueba, no del código, y se corrigieron antes de seguir -exactamente la
regla de las dos rondas que este mismo ADR cita como criterio de parada-.

`tests/engine/test_boundary.py` sigue en verde sin haberlo modificado
(ninguna importación nueva cruza la frontera `sirius`/`sirius_engine`).

## Consecuencias

- El motor puede, por primera vez, cerrar el ciclo de un Run perdido sin
  intervención humana para `WorkItem` de autoridad `MOTOR`, con el episodio
  completo (qué observó, qué decidió, por qué) en su propio diario.
- Para `WorkItem` de autoridad `INCIDENCIA` (`programacion`, `auditoria`
  -las clases que hoy corren como esta misma incidencia #232-), el
  supervisor no actúa todavía: sigue dependiendo enteramente de
  `sirius_reconcile.sh` como red de seguridad, sin cambio de
  comportamiento observable para esas clases. Este es el límite conocido
  más importante de C1, y lo hereda C2 como trabajo pendiente cuando
  construya el despachador real para esa autoridad.
- "Reactivar" y "sustituir" hoy solo crean el siguiente `Run` en el dominio
  del motor (`PREPARED`); no disparan ninguna ejecución real en GitHub
  Actions, porque ese despachador (C2) todavía no existe. Un futuro
  consumidor de `WorkEngineStore` que sí despache tendrá que recoger esos
  `Run` en `PREPARED` igual que recoge cualquier otro.
- `SupervisorPolicy.max_reactivaciones`/`max_sustituciones` son valores por
  defecto provisionales (1 y 1), no cotas medidas: quedan explícitamente
  configurables para que ajustarlos no exija tocar código, y su
  justificación ("fallar rápido hacia el propietario") queda escrita en el
  propio módulo.

## Alternativas descartadas y por qué

Ver "Opciones consideradas" arriba; las tres decisiones (cota de LOST,
coordinación con el reconciliador, alcance de "reactivar") comparten el
mismo criterio: ninguna inventa un dato que otro bloque (S3, C2) dejó
abierto a propósito, y las tres se apoyan en piezas del dominio que ya
existían antes de esta incidencia (`Run.deadline`, `domain/authority.py`,
`retry_run`/`substitute_run_worker`/`escalate_work_item`) en vez de crear
mecanismos paralelos.
