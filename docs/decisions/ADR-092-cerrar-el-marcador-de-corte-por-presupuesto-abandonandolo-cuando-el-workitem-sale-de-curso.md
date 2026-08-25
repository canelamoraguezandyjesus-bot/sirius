# ADR-092 — Cerrar el marcador de corte por presupuesto abandonándolo cuando el WorkItem sale de curso

- Estado: APROBADO
- Fecha: 2026-08-25
- Aprobación: fusión de la PR de la incidencia #353 por el propietario
- Esta es también la nota de arranque de la rama `fix/h-20-segunda-mitad-marcador-corte-presupuesto` (skill `disciplina-evidencia`): se publica ANTES del primer cambio de código, no después.

## Contexto y problema

`docs/audits/registro_defectos.yml` registra H-20 con su primera mitad ya
cerrada (`4f91f99fb75bde506825e41ed1a211e31c176ce3`, incidencia #345): la
divergencia entre `DurableWorkEngineStore` e `InMemoryWorkEngineStore` cuando
un corte por presupuesto golpea un WorkItem que YA estaba `PAUSED` antes de
pedirse el corte. Queda abierta la segunda mitad (incidencia #353), un guion
distinto y medido:

1. `cancel_all_live_runs_and_escalate_work_item` anexa
   `work_item_budget_cutoff_started` porque el WorkItem SÍ está en curso
   (`ACTIVE`) en ese momento -pasa la guarda que cerró la primera mitad-.
2. La cascada muere antes de escalar (p. ej. un fallo de `fsync` de
   directorio). El marcador ya es durable; el WorkItem sigue `ACTIVE`.
3. Un humano PAUSA el WorkItem -acción ajena al corte- antes de que nadie
   reabra el almacén.
4. Al reabrir, `_reconcile_pending_budget_cutoffs` encuentra el marcador con
   el WorkItem `PAUSED` (no en curso) y hace `continue`. Ese `continue` no
   deja ningún rastro durable de que el marcador dejó de aplicar: sigue
   pendiente en el diario.
5. Un humano reanuda el WorkItem a propósito -queda `ACTIVE`, con una fecha
   muy posterior a la del corte original-.
6. Al reabrir el almacén una segunda vez, la reconciliación encuentra el
   marcador todavía pendiente con el WorkItem otra vez en curso, cree que hay
   un corte a medias vigente y repite la cascada con el `now` viejo del
   marcador: escala un WorkItem sano a `NEEDS_DECISION` con una fecha
   ANTERIOR a la de su propia pausa y reanudación, ya anexadas en el diario.

## Nota de arranque — las cuatro preguntas (publicadas antes del primer cambio)

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en el
   `continue` de `_reconcile_pending_budget_cutoffs`
   (`src/sirius_engine/adapters/durable/store.py`). El arreglo va en el mismo
   sitio, y SÍ puede observar el fallo que arregla: a diferencia de la
   cascada (que puede morir a mitad, CODEX-001 ronda 8), la reconciliación
   corre en `_load()`, al reabrir el almacén, cuando el proceso ya está vivo
   y con el diario íntegro delante -el mismo patrón que ya resolvió el
   "observador dentro de lo observado" para el propio marcador-.
   `memory_store.py` no necesita ningún cambio: no persiste ningún marcador
   ni reconcilia nada al construirse, así que este defecto -que depende de
   REABRIR un almacén- no puede ocurrir ahí (se añade una prueba de
   coherencia que lo confirma, no un arreglo).
2. **¿Qué NO va a garantizar esto?** No decide si una pausa/reanudación
   *genuinamente relacionada* con el presupuesto (alguien reanuda un
   WorkItem que sigue sin presupuesto) debe recibir un corte: eso lo decide
   la próxima llamada real a `registrar_gasto`, con un marcador y un `now`
   frescos, no la reconciliación de un intento ya interrumpido. Tampoco
   reescribe ni reordena eventos ya anexados -el diario sigue siendo
   append-only-, solo evita que un intento de corte obsoleto vuelva a
   dispararse fuera de tiempo.
3. **Criterio de parada, decidido antes de medir.** Se escribe primero la
   prueba que reproduce la secuencia completa (pasos 1-6) y se comprueba que
   FALLA contra el código actual. Después se implementa UNA de las dos
   opciones de abajo y se mide contra la misma prueba: si el resultado deja
   (a) al WorkItem `ACTIVE`, sin escalar, y (b) las fechas de sus eventos en
   orden no decreciente, la opción se acepta; si no cumple ambas, se
   descarta y se prueba la otra opción; si ninguna cumple ambas sin tocar la
   semántica de un corte legítimo, se para y se emite `BLOCKED_BY_DECISION`.
4. **¿Qué hace el fallo imposible, no solo improbable?** Cerrar el marcador
   de forma durable en el MISMO movimiento en que se detecta que ya no
   aplica -no "en la próxima oportunidad"-, para que ninguna reapertura
   futura pueda volver a encontrarlo pendiente. Comprobado con una prueba que
   reabre el almacén una TERCERA vez, tras el cierre, y verifica que el
   marcador no reaparece ni se repite el cierre.

## Opciones consideradas

- **A.** El `continue` de `_reconcile_pending_budget_cutoffs` cierra el
  marcador de forma durable -anexando un evento nuevo,
  `work_item_budget_cutoff_abandoned`, sin escalar ni tocar ningún Run-
  cuando encuentra al WorkItem fuera de `ESTADOS_EN_CURSO`.
- **B.** La reconciliación deja de usar el `now` del marcador cuando el
  WorkItem se ha movido después de él: en vez de `continue`, calcula un
  `now` a partir de `work_item.updated_at` (nunca un reloj real) y ejecuta
  igual la cascada cuando el WorkItem vuelve a estar en curso.

## Decisión

Opción A.

## Comprobación que la sostiene

Prueba nueva
(`tests/engine/test_durable_journal.py::test_reabrir_dos_veces_tras_pausar_y_reanudar_no_escala_un_corte_a_medias_con_fecha_hacia_atras`),
vista FALLAR contra el código sin corregir:

```
$ git stash push -- src/sirius_engine/adapters/durable/store.py src/sirius_engine/domain/events.py
$ uv run pytest tests/engine/test_durable_journal.py -k pausar_y_reanudar -v
...
FAILED ...AssertionError: un WorkItem sano, pausado y reanudado por un humano
tras un corte por presupuesto que murio a mitad, no debe acabar escalado a
needs_decision por su cuenta (quedo en needs_decision)
$ git stash pop
```

**Medición que decide entre A y B** (no por gusto): se implementó la Opción B
temporalmente -`now = work_item.updated_at if work_item.updated_at >
started_at else started_at`, sin `continue` temprano- y se corrió la MISMA
prueba:

```
now (Opción B) = 2026-08-25T09:00:00Z  (la fecha de la reanudación: el
                                          orden del diario queda correcto)
estado final    = NEEDS_DECISION        (sigue escalando al WorkItem sano)
```

La Opción B sí corrige el síntoma de fecha (el criterio 3(b) del arranque se
cumple: `updated_at` pasa a ser la fecha de la reanudación, no precede a
ningún suceso previo), pero **no cumple el criterio 3(a)**: sigue escalando a
`NEEDS_DECISION` un WorkItem que un humano acababa de reanudar sin relación
con el corte interrumpido -exactamente el desenlace que la incidencia #353
mide y describe como el defecto ("un WorkItem sano que un humano reanudó
acaba en needs_decision por su cuenta"), no solo su fecha-. Por el criterio de
parada publicado arriba, la Opción B se descarta.

Con la Opción A, la misma prueba pasa en verde:

```
$ uv run pytest tests/engine/test_durable_journal.py -q
30 passed in 0.76s
```

Y la suite completa del proyecto, en verde (ver PR de la incidencia #353 para
la salida completa de `uv run ruff format --check .`, `uv run ruff check .`,
`uv run mypy src tests`, `uv run pytest` y `git diff --check`).

## Consecuencias

- Nuevo tipo de evento, `work_item_budget_cutoff_abandoned`, añadido a
  `EventKind` (`src/sirius_engine/domain/events.py`): un WorkItem puede
  ahora tener, en su historial, un corte iniciado y luego abandonado sin
  escalar -un desenlace legítimo que antes no dejaba ningún rastro durable-.
- `_absorb` reconoce el nuevo evento para limpiar `_pending_budget_cutoffs`
  al reproducir el diario, simétrico a como ya lo hacía
  `work_item_escalated`.
- `memory_store.py` no cambia: se añade una prueba de coherencia
  (`test_el_almacen_en_memoria_nunca_necesita_reconciliar_un_corte_por_no_reabrirse_jamas`)
  que ejecuta el mismo guion de pausa/reanudación contra los dos almacenes y
  compara estado y fecha, igual que hizo la primera mitad de H-20.
- Un corte interrumpido y luego abandonado por una pausa externa NO vuelve a
  intentarse automáticamente si el WorkItem se reanuda más tarde: si el
  presupuesto sigue agotado, lo detectará la siguiente llamada real a
  `registrar_gasto`, con su propio marcador y su propio `now`. Esto es
  intencional (pregunta 2 del arranque) y coherente con que el corte
  original ya no describe el estado actual del WorkItem tras una
  intervención humana que no tuvo nada que ver con él.

## Alternativas descartadas y por qué

- **Opción B** (usar `work_item.updated_at` como `now` y seguir escalando):
  descartada por la medición de arriba -corrige el orden de fechas pero no
  el defecto sustantivo que la incidencia #353 mide-.
- **Usar un reloj real en la reconciliación**: descartada sin necesidad de
  medir; contradice el invariante ya documentado de
  `_reconcile_pending_budget_cutoffs` ("nunca un reloj real") y reintroduce
  la misma familia de fallo que motivó ese invariante -un desenlace que
  depende de CUÁNDO se reabre el almacén, no de qué pasó-.
