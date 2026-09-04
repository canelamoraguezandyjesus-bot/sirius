# ADR-136 — El reflejo del desenlace de GitHub vuelve al almacén del motor

- Estado: PROPUESTO
- Fecha: 2026-09-04
- Aprobación: la fusión de la PR de la incidencia #529 por el propietario.

## Contexto y problema

El motor despacha por la vía GitHub (C2, incidencia #240) y desde entonces no
vuelve a enterarse de nada: `dispatch_work_item` escribe la incidencia y
aplica la etiqueta inicial, pero ninguna llamada de producción vuelve a tocar
el `WorkEngineStore` después. Medido en `src/`: `dispatch_work_item_async`
tiene cero llamantes, y lo mismo `begin_work_item_execution`,
`begin_work_item_check`, `begin_work_item_review`, `approve_work_item_review`,
`request_work_item_repair` y `resume_work_item_after_repair` — los seis
puertos que hacen avanzar la fase del ciclo revisar-reparar (§3.4). Solo
`deliver_work_item`, `fail_work_item_safely`, `observe_work_item_external_fact`
y `escalate_work_item` tenían ya llamantes reales, pero desde
`governance.py`/`supervisor.py` (presupuesto, recuperación de Runs perdidos),
nunca desde el desenlace real de una incidencia.

Consecuencia medida en el diario real (rama `estado-del-motor`,
`diario.jsonl`, 04-09-2026): los siete `WorkItem` de la ola de criticidad
(#508, #510, #512, #514, #516, #518, #520 — WI-20260902-174417 y siguientes)
llevan, cada uno, exactamente dos sucesos (`work_item_created`,
`work_item_activated`) y se quedan ahí en `ACTIVE`/`PREPARAR` para siempre,
aunque sus siete incidencias reales están cerradas y fusionadas. Cada pasada
de `sirius-racha` sobre ellos sale `NO_COMPARABLE` citando el §11.2 del
contrato (`docs/implementation/AUTOMATION_OPERATING_CONTRACT.md:650`): «el
contador no puede empezar antes de que el motor lleve el estado por sí
mismo». La incidencia #376 (H-25, ADR-101) ya declaró esa precondición como
hecho explícito (`CLASES_CON_ESTADO_PROPIO` vacío) en vez de inferirla por
caso; esta incidencia (#529, bloque C1) es la mitad que hace el hecho dejar
de ser cierto — cablear el retorno del desenlace de GitHub al almacén.

## Nota de arranque (disciplina de evidencia, ADR-001)

Cuatro preguntas, decididas antes de escribir la primera línea de
`reflect.py`:

1. **¿Qué se construye?** Una función pura (`reflejar_desenlace`) que, dado
   el `WorkItem` vigente y lo que el espejo de solo lectura (A3) proyecta de
   su incidencia, calcula el camino MÍNIMO de transiciones del almacén hacia
   ese objetivo; y un ejecutor mecánico (`aplicar_pasos`) que llama, uno a
   uno, exactamente los puertos que `ports/store.py` ya declara. Ningún
   puerto ni suceso nuevo.
2. **¿Qué prueba lo falsifica?** Por cada etiqueta del mapa
   `mirror_projection._LABEL_STATE`, la secuencia de sucesos exacta,
   verificada contra `store.list_events()`; idempotencia de una segunda
   pasada; «nunca hacia atrás»; espejo contradictorio y sin etiqueta; y una
   integración con `DurableWorkEngineStore` sobre una copia real del diario
   de la ola de criticidad. Todas estaban en rojo antes de escribir
   `reflect.py` — no existía el módulo, así que `ImportError` era el rojo de
   partida de las 19 pruebas de `test_reflect.py`, las 6 de
   `test_reflect_cli.py`, las 4 nuevas de `test_mirror_projection.py` y las 2
   de `test_reflejar_desenlace_github.py`.
3. **¿Qué NO cubre esto?** El enganche a `.github/**` (C1b, ADR-002, decisión
   del propietario); declarar `programacion` en `CLASES_CON_ESTADO_PROPIO`
   (C2, ADR-101) — se hace después de observar una pasada real de este
   reflejo, no aquí; ningún cambio a `sirius-despachar`, `sirius-supervisar`
   ni `sirius-racha` más allá de lo imprescindible para compartir la lectura
   del espejo (de hecho, ninguno de los tres se tocó).
4. **Criterio de parada.** Si reflejar una etiqueta del mapa exigiera un
   suceso o un puerto que el almacén no tuviera hoy, parar con
   `BLOCKED_BY_DECISION`. No hizo falta: las once transiciones que usa
   `reflect.py` (`begin_work_item_execution`, `begin_work_item_check`,
   `begin_work_item_review`, `approve_work_item_review`,
   `request_work_item_repair`, `resume_work_item_after_repair`,
   `deliver_work_item`, `fail_work_item_safely`, `escalate_work_item`,
   `reactivate_work_item`, `resolve_work_item_decision`) ya existían, con o
   sin llamante previo. Las dos últimas se sumaron en la ronda de corrección
   de la revisión independiente (CODEX-002, PR #530): ver «Reanudación de una
   parada por orden del propietario» más abajo.

**Predicción, escrita antes de correr la integración real:** el reflejo de
las siete incidencias reales produce, por incidencia, entre 4 y 9 sucesos, y
cero sucesos en una segunda pasada; ninguna métrica del banco de memoria
cambia (este encargo no toca `src/sirius`). **Resultado:** cada una de las
siete produjo exactamente 5 sucesos (`work_item_execution_started`,
`work_item_check_started`, `work_item_review_started`,
`work_item_review_approved`, `work_item_delivered`) — dentro del rango
predicho, en el extremo bajo porque el reflejo es una única pasada
retroactiva sobre el desenlace FINAL de cada incidencia (`sirius:completed`),
no una reconstrucción de cada vuelta del bucle revisar-reparar que
atravesaron en su momento; el camino mínimo hacia un objetivo `completed` no
tiene forma de saber cuántas reparaciones hubo por el camino, ni falta que le
hace — solo necesita alcanzar `ENTREGAR` antes de `deliver_work_item`, que es
exactamente lo que la ventana 3 de `projection_verifier` exige. La segunda
pasada, medida en la misma prueba de integración, produjo cero sucesos para
las siete. El banco de memoria no se tocó (cero cambios bajo `src/sirius`,
confirmado por `git diff --stat`).

## Decisión interpretativa: qué significa «lo registra» para hacia-atrás y contradicción

El objetivo de la incidencia dice, para el caso «hacia atrás»: «no toca nada
y lo registra como divergencia observada con `observe_work_item_external_fact`».
Literalmente, ese puerto solo transiciona `WAITING -> ACTIVE`
(`domain/work_item.py::observe_external_fact`) — y ningún `WorkItem`
despachado por la vía real está nunca en `WAITING`, porque
`dispatch_work_item_async` (el único camino hacia ese estado) tampoco tiene
llamante, y cablearlo está fuera de alcance de C1 («no toques
`sirius-despachar`»). Invocar literalmente `observe_work_item_external_fact`
en el caso «hacia atrás» habría lanzado `IllegalTransitionError` en el ÚNICO
escenario real donde ese caso puede ocurrir (un `WorkItem` `ACTIVE` cuyo
espejo proyecta algo anterior) — es decir, habría convertido la salvaguarda
en el propio defecto que existe para evitar.

**Decisión:** `reflejar_desenlace` NO invoca ningún puerto del almacén en los
casos «hacia atrás» y «etiquetas contradictorias» — devuelve
`ResultadoReflejo(pasos=(), divergencia=<motivo>)`, y es el llamador
(`sirius-reflejar` o una prueba) quien decide qué hacer con ese motivo
(hoy: imprimirlo). Es una resolución técnica de una instrucción que, tomada
al pie de la letra, viola una precondición ya existente del dominio — no una
decisión de producto/arquitectura/seguridad que requiera pararse: el propio
código del almacén (`work_item.py`, con pruebas desde A1) es la autoridad
sobre qué transiciones son legales, y ninguna lectura razonable del objetivo
pretende que `reflejar_desenlace` provoque una excepción sin capturar en
producción. Registrado aquí en vez de en silencio para que quien revise
pueda estar en desacuerdo con el criterio.

## Reanudación de una parada por orden del propietario (corrección CODEX-002, PR #530)

La revisión independiente de la PR de esta incidencia encontró que la regla
«nunca hacia atrás» de arriba trataba como divergencia permanente un caso que
sí es hacia delante: `sirius_resume_on_command.sh:338-350` reanuda una parada
(`sirius:blocked-decision`/`sirius:failed-safely`) por orden explícita del
propietario reponiendo la etiqueta ACTIVA que la parada había retirado, sin
tocar el `WorkItem` del motor -que se queda en `NEEDS_DECISION`/
`FAILED_SAFELY`-. La primera versión de `reflejar_desenlace` no reconocía esa
combinación (espejo `ACTIVE`, motor parado) como una reanudación autoritativa
ya registrada: la trataba igual que cualquier otro `WorkItem` que no está
`ACTIVE`, y devolvía divergencia («no hay camino hacia delante») en cada
pasada, para siempre -el motor nunca llegaba al desenlace final de una
incidencia reanudada-.

**Corrección:** cuando el espejo proyecta `ACTIVE` y el motor está en
`FAILED_SAFELY` o `NEEDS_DECISION`, el plan antepone el paso de reanudación
correspondiente -`reactivate_work_item` (`FAILED_SAFELY -> ACTIVE`) o
`resolve_work_item_decision(..., continuar=True)`
(`NEEDS_DECISION -> ACTIVE`)- antes de calcular el camino de fase con
`_camino_de_fase`, exactamente igual que en cualquier otro caso ACTIVE. Esto
no rompe «nunca hacia atrás»: ninguno de los dos puertos toca `fase` (ni
`fail_safely` ni `escalate` la tocaron al parar), así que el camino se sigue
calculando desde la misma `work_item.fase` de antes de la parada, con la
misma caminata determinista de la sección «Opciones consideradas». No es
vocabulario nuevo: los dos puertos (`reactivate_work_item`,
`resolve_work_item_decision`) ya existían en `ports/store.py` sin llamante de
producción, igual que las otras nueve transiciones que usa este módulo.

Probado en `tests/engine/test_reflect.py`
(`test_reanudacion_desde_failed_safely_reactiva_antes_de_caminar_la_fase`,
`test_reanudacion_desde_needs_decision_resuelve_la_decision_antes_de_caminar_la_fase`):
un motor que falla en fase EJECUTAR y cuyo espejo, tras la reanudación,
proyecta `ACTIVE`/COMPROBAR produce exactamente `(PASO_REACTIVADO,
PASO_COMPROBACION_INICIADA)` (o el equivalente con
`PASO_DECISION_RESUELTA`), y termina en `ACTIVE`/COMPROBAR real tras
aplicarlo contra `InMemoryWorkEngineStore`. Cada una de las dos pruebas
incluye también una segunda pasada sobre el motor ya reactivado, con el mismo
espejo, que confirma `pasos == ()` (idempotencia; corrección
CLAUDE-REVIEWER-001, ronda 3, PR #530 — la primera versión de estas dos
pruebas solo comprobaba la primera pasada, a diferencia de las demás pruebas
de idempotencia del mismo fichero).

## Reanudación generalizada a PLANNED y DELIVERED (corrección CODEX-001, ronda 3, PR #530)

La corrección CODEX-002 (ronda 2, arriba) solo anteponía el paso de
reanudación (`work_item_reactivated`/`work_item_decision_resolved`) dentro de
la rama en la que el espejo proyecta `ACTIVE`. La revisión independiente de
la ronda 3 encontró que eso deja sin cubrir dos caminos reales por los que
una reanudación autorizada NO aterriza en `ACTIVE`:

1. **`destino_de_rol`** (`sirius_resume_on_command.sh:180-186`) repone
   `sirius:implement-requested` para el implementador, y esa etiqueta
   proyecta `PLANNED`/`PREPARAR` (`mirror_projection.py:173-175`), no
   `ACTIVE` — así que ni siquiera una reflexión inmediata tras la reanudación
   reactivaba esa clase de parada.
2. Si el ciclo real avanza deprisa tras la reanudación -o esta reflexión no
   se ejecuta hasta después de que la incidencia ya cerró-, el espejo puede
   pasar directamente a `DELIVERED` sin que ninguna pasada observe el
   `ACTIVE` intermedio; la rama `DELIVERED` rechazaba entonces el `WorkItem`
   detenido como "hacia atrás" para siempre.

**Corrección:** el cálculo de `pasos_reanudacion` se hizo común a las cinco
ramas de estado del espejo (antes vivía solo dentro de la rama `ACTIVE`):
se dispara exactamente cuando el motor está en `FAILED_SAFELY` o
`NEEDS_DECISION` y el espejo deja de proyectar ese MISMO estado detenido
-nunca por la sola presencia de un espejo `PLANNED` o `DELIVERED`, que es
justo la salvaguarda que pide el hallazgo: "sin convertir cualquier
retroceso ordinario a PLANNED ni cualquier desenlace terminal en permiso
para reactivar"-. Un `estado_efectivo` (el estado ya reanudado, o el mismo
si no hubo reanudación) sustituye a `work_item.estado` en las comprobaciones
"¿hay camino hacia delante?" de las ramas `FAILED_SAFELY`, `NEEDS_DECISION`,
`PLANNED` (con el paso de reanudación gateado además por
`pasos_reanudacion` no vacío, para no tocar el comportamiento ya probado de
un motor que nunca se paró) y `DELIVERED`; la rama `ACTIVE` queda igual que
en la ronda 2. Ningún puerto ni vocabulario nuevo: los mismos dos de
CODEX-002.

Probado en `tests/engine/test_reflect.py`
(`test_reanudacion_que_aterriza_en_planned_reactiva_sin_camino_de_fase`,
`test_etiqueta_planned_sigue_hacia_atras_si_el_motor_nunca_paro`,
`test_reanudacion_que_aterriza_en_delivered_reactiva_y_camina_hasta_entregar`):
un motor `FAILED_SAFELY`/`PREPARAR` con espejo `PLANNED`/`PREPARAR` produce
ahora `(PASO_REACTIVADO,)` en vez de cero pasos; el mismo espejo `PLANNED`
contra un motor que nunca se paró (`ACTIVE`) sigue siendo divergencia
-la salvaguarda no tocó ese caso, ya cubierto desde la ronda 1-; y un motor
`FAILED_SAFELY`/`COMPROBAR` con espejo `DELIVERED` produce
`(PASO_REACTIVADO, PASO_REVISION_INICIADA, PASO_REVISION_APROBADA,
PASO_ENTREGADO)` y entrega de verdad contra `InMemoryWorkEngineStore`.

## Opciones consideradas

1. **Rango escalar de fase** (`PREPARAR=0 < EJECUTAR=1 < ... < ENTREGAR=5`) y
   comparar índices para decidir «hacia delante»/«hacia atrás». Descartada:
   el bucle real revisar-reparar tiene una arista que retrocede
   (`REPARAR -> COMPROBAR`, `resume_work_item_after_repair`) que es, sin
   embargo, forzosamente hacia delante EN EL TIEMPO cuando el motor ya
   refleja un REPARAR anterior y la incidencia avanzó a `ci-pending`. Un
   rango escalar fijo no puede representar esa arista sin, a la vez, dejar
   colarse retrocesos falsos.
2. **Grafo dirigido + BFS genérico.** Más general de lo que hace falta: el
   objetivo pide un camino MÍNIMO y determinista (un único camino canónico
   por par origen-destino, «en orden de fase»), no el más corto entre varios
   empatados — la ambigüedad entre reparar desde REVISAR o desde COMPROBAR
   (el domino permite las dos) se resolvería de forma no determinista sin
   una regla explícita, y BFS no la trae por sí solo.
3. **(Elegida) Caminata determinista de una arista fija por fase**, con una
   única excepción (REVISAR bifurca a REPARAR solo si el objetivo es
   REPARAR, si no bifurca a ENTREGAR) y una única arista de retorno
   (REPARAR -> COMPROBAR, tomada siempre que el motor está en REPARAR y el
   objetivo no lo es). Determinista, sin ambigüedad, y su propia ausencia de
   arista de avance («ENTREGAR sin coincidir con el objetivo») ES la regla
   «nunca hacia atrás»: no hace falta una comprobación aparte, la propiedad
   emerge de que el grafo real no tiene más aristas que ir hacia delante.

## Decisión

`src/sirius_engine/reflect.py`: `reflejar_desenlace(work_item, espejo,
episodio) -> ResultadoReflejo` (pura, sin almacén) calcula el plan;
`aplicar_pasos(store, work_id, pasos, now=...)` lo ejecuta contra cualquier
`WorkEngineStore` (memoria o durable). `src/sirius_engine/reflect_cli.py`
(`sirius-reflejar`, cáscara sin decisiones, mismo patrón que
`sirius-supervisar`/D2 y `sirius-racha`/D1) itera los `WorkItem` despachados
y no terminales, lee su espejo con `leer_y_proyectar_work_item` (ya existía,
A3) y aplica (o, con `--ensayo`, solo imprime) el plan.

`MirroredWorkItem` gana un campo (`diagnostico_fallo: str | None`), poblado
en `mirror_projection.py` desde el mismo cuerpo de comentario que
`sirius_apply_verdict.sh` ya publica para `FAILED_SAFELY`/
`USAGE_LIMIT_REACHED` — no un vocabulario nuevo, la interpretación de uno que
ya se escribe en producción y que A3 no leía todavía. `head_sha` (ya
existente) resultó suficiente para el SHA de fusión de `completed`: el mismo
comentario de `complete-sirius-after-merge.yml` que planta
`<!-- sirius-completed:<sha> -->` también escribe «- Merge SHA: `<sha>`», que
`_SHA_MARKER_RE` ya interpretaba.

**Corrección CODEX-001 (ronda 2, PR #530 — distinta de la CODEX-001 de la
ronda 3 descrita más arriba; el revisor independiente reinicia la
numeración en cada ronda, así que el mismo identificador nombra dos
hallazgos distintos según la ronda):** la primera versión de
`_DIAGNOSTICO_FALLO_RE` solo reconocía el marcador que publica el VEREDICTO
de un rol (`sirius-verdict:<rol>:FAILED_SAFELY:<tag>` o
`:USAGE_LIMIT_REACHED:<tag>`), pero las puertas deterministas que también
aplican `sirius:failed-safely` -`stop_gate` en `review-sirius-work.yml`, las
paradas de `parada ...` en `repair-sirius-work.yml`, `stop_safely` en
`sirius_apply_verdict.sh`- publican en su lugar
`sirius-verdict:<rol>:precheck:<motivo>[:<tag>]`, con el mismo cuerpo y la
misma cabecera fija (`🔴 **Me he detenido de forma segura**`). La expresión
no los reconocía, así que el diagnóstico de cualquier parada de puerta se
leía como `None`. Se amplió la expresión para aceptar también
`precheck` como tercer campo del marcador, sin tocar el resto de la gramática
-el filtro de la cabecera fija que sigue ya excluye las paradas `precheck`
que aplican otra etiqueta (`convergencia-<motivo>` -> `blocked-decision`,
`head-movido-tras-ci` -> `ci-pending`, que usan cabeceras `🟡` distintas) y
los comentarios de `notify-sirius-state.yml`, que usan el marcador
`sirius-notification:`, no `sirius-verdict:`-. Probado en
`tests/engine/test_mirror_projection.py`
(`test_diagnostico_fallo_se_extrae_de_una_parada_precheck`,
`test_diagnostico_fallo_de_precheck_con_otra_etiqueta_no_cuenta`,
`test_diagnostico_fallo_de_notificacion_no_cuenta`).

**Recomendación de enganche para C1b** (fuera de alcance, decisión del
propietario, ADR-002): llamar a `uv run sirius-reflejar` justo después de
cada cambio de etiqueta que ya aplican `advance-sirius-after-quality.yml`,
`review-sirius-work.yml`, `repair-sirius-work.yml` y
`complete-sirius-after-merge.yml` — mismo punto del ciclo donde
`sirius-racha` ya lee el espejo hoy, así que no añade una lectura nueva a la
cuota de la API.

## Comprobación que la sostiene

- `tests/engine/test_reflect.py` (24 pruebas): las cinco secuencias exactas
  del mapa de etiquetas activas, `blocked-decision` (1 paso), `planned` (0
  pasos, hacia atrás), idempotencia (dos casos), nunca-hacia-atrás,
  contradicción, sin etiqueta, `completed` con SHA de fusión (incluida la
  prueba de que camina TODAS las fases intermedias, no salta a
  `deliver_work_item`), `failed-safely` con y sin diagnóstico de confianza,
  el cierre del bucle `REPARAR -> COMPROBAR`, las dos pruebas de reanudación
  de una parada por orden del propietario (corrección CODEX-002, PR #530,
  cada una con su segunda pasada de idempotencia añadida en la ronda 3 —
  CLAUDE-REVIEWER-001), las tres pruebas de reanudación generalizada a
  `PLANNED`/`DELIVERED` (corrección CODEX-001, ronda 3, PR #530), y las dos
  pruebas de mutación de abajo.
- `tests/engine/test_reflect_cli.py` (6 pruebas): ensayo no toca nada,
  ejecución real aplica y dice cuántos pasos, un `WorkItem` terminal se
  salta sin volver a leer su incidencia, una incidencia ilegible no corta
  las demás, espejo sin etiqueta no dice nada, `completed` con SHA entrega
  de verdad.
- `tests/engine/test_mirror_projection.py` (7 pruebas nuevas):
  `diagnostico_fallo` desde el último comentario de confianza, el más
  reciente cuando hay varios, un comentario no confiable no cuenta, ausente
  sin comentario de fallo, y las tres de la corrección CODEX-001 de la ronda 2
  (PR #530): una parada `precheck` sí cuenta, una parada `precheck` con otra
  etiqueta no cuenta, un comentario de notificación no cuenta.
- `tests/automation/test_reflejar_desenlace_github.py` (2 pruebas,
  integración con `DurableWorkEngineStore` y `DurableDispatchJournal` reales
  sobre copias de `tests/automation/fixtures/diario_ola_criticidad.jsonl` y
  `diario_despacho_ola_criticidad.jsonl` — extracto EXACTO, mismas 14 y 7
  líneas respectivamente con su `checksum_sha256` intacto, de
  `git show origin/estado-del-motor:diario.jsonl` /
  `diario-despacho.jsonl`, 04-09-2026): antes de reflejar, comparar con la
  clase declarada SOLO dentro de la prueba (nunca en
  `CLASES_CON_ESTADO_PROPIO` real) ya no cae en el `NO_COMPARABLE` de
  precondición del §11.2 — cae en la ventana 3 real («fusión sin pasar por
  ready-for-merge»), una evaluación honesta del estado real, no un silencio
  por falta de jurisdicción; después de reflejar las siete, la misma
  comparación sale `COINCIDE` en los dos ejes para las siete, y una segunda
  pasada no añade ningún suceso. Los espejos de `sirius:completed` son
  representativos del desenlace documentado (issue #529: «cerradas y
  fusionadas») con SHAs de relleno, no una segunda lectura de red — este
  entorno no tiene ni token ni acceso a GitHub.
- Comandos ejecutados, en verde, sobre el árbol de la corrección CODEX-001/
  CODEX-002 (PR #530, ronda 3, 2026-09-04): `uv run ruff format --check .`
  (601 ficheros ya formateados), `uv run ruff check .` (todas las
  comprobaciones superadas), `uv run mypy src tests` (569 ficheros, sin
  incidencias), `uv run pytest` (4752 passed, 15 skipped, 2 xfailed en
  425.34s — los xfailed y skipped son preexistentes, ninguno de este bloque;
  las 3 pruebas nuevas de esta ronda, todas en `test_reflect.py`
  -`test_reanudacion_que_aterriza_en_planned_reactiva_sin_camino_de_fase`,
  `test_etiqueta_planned_sigue_hacia_atras_si_el_motor_nunca_paro`,
  `test_reanudacion_que_aterriza_en_delivered_reactiva_y_camina_hasta_entregar`-,
  están incluidas en el recuento; confirmado también con
  `uv run pytest --collect-only -q` sobre el árbol de esta ronda antes de
  correr la suite completa, 4769 = 4752 + 15 + 2).
- **Reconciliación de la cifra de la ronda 2 (corrección CLAUDE-REVIEWER-002,
  ronda 3):** la ronda 1 (head `e759958`) documentó «4743 passed»; la ronda 2
  (head `72e6218`) documentó «4749 passed», una diferencia de 6, mientras que
  `git diff e759958..72e6218 -- tests/` solo añade 5 funciones `def test_`
  nuevas (2 en `test_reflect.py`, 3 en `test_mirror_projection.py`) — no hay
  ninguna sexta prueba, nuevo caso de `@pytest.mark.parametrize`, ni cambio de
  resultado de una prueba preexistente de por medio. La cifra que no
  cuadraba era la de la ronda 1: `uv run pytest --collect-only -q` mide 4761
  pruebas recogidas en el head `e759958` y 4766 en `72e6218` -una diferencia
  de 5, la que predice el diff-, y `uv run pytest` recién ejecutado sobre
  `72e6218` (antes de aplicar ningún cambio de esta ronda) confirma
  exactamente 4749 passed, 15 skipped, 2 xfailed (4766 en total, igual que lo
  recogido). Con los mismos 15 skipped/2 xfailed en ambos heads, la ronda 1
  debió documentar 4744 passed (4761 − 15 − 2), no 4743: un error de
  transcripción de esa ronda, no un defecto de la ronda 2. La cifra de la
  ronda 2 («4749 passed») ya era correcta y no se ha tocado; se deja esta
  nota para que la discrepancia quede explicada en vez de repetirse.

### Las dos mutaciones (nota de arranque, criterio 2)

1. **Quitar «nunca hacia atrás».** Se cambió, a mano, la rama final de
   `_camino_de_fase` (el caso «`ENTREGAR` sin coincidir con el objetivo») de
   `return None` a `fase = WorkItemPhase.PREPARAR` (retroceder en vez de
   declarar que no hay arista de avance). Cayeron
   `test_nunca_hacia_atras_si_el_motor_ya_paso_el_objetivo` y
   `test_mutacion_quitar_nunca_hacia_atras_la_detecta_esta_prueba`, las dos
   con un plan que inventaba pasos donde no hay ninguna transición real.
   Revertida.
2. **Quitar la idempotencia.** Se quitó, en la rama `FAILED_SAFELY`, la
   comprobación `if work_item.estado is WorkItemState.FAILED_SAFELY: return
   ResultadoReflejo(pasos=())` anterior a la de «no es ACTIVE». El plan
   seguía saliendo vacío en la segunda pasada -por la razón EQUIVOCADA, «no
   es ACTIVE» en vez de «ya está ahí»-, así que `segundo.pasos == ()` seguía
   pasando; lo que cayó fue la aserción añadida a propósito,
   `test_mutacion_quitar_idempotencia_la_detecta_esta_prueba`, que comprueba
   `segundo.divergencia is None` -sin idempotencia explícita, un `WorkItem`
   que ya está exactamente donde el espejo dice queda acusado de divergencia
   en vez de reconocido como ya alcanzado-. Revertida.

Las dos mutaciones se aplicaron y revirtieron a mano sobre
`src/sirius_engine/reflect.py` durante la implementación; no quedan en el
árbol ni en el historial de commits de esta rama.

## Consecuencias

- El motor ya puede llevar, por sí mismo, el desenlace real de una
  incidencia despachada — la precondición literal del §11.2 deja de ser
  falsa para cualquier `WorkItem` sobre el que se corra `sirius-reflejar`.
  Sigue siendo falsa en producción HOY porque nada invoca el comando
  todavía (C1b) y `CLASES_CON_ESTADO_PROPIO` sigue vacío (C2): esta
  incidencia entrega la maquinaria, no el interruptor.
- Once puertos del almacén que existían sin llamante de producción (o con
  uno de un contexto distinto) tienen ahora un camino real de producción
  -`sirius-reflejar`- que puede invocarlos. Ninguno cambió de forma. Los
  últimos dos (`reactivate_work_item`, `resolve_work_item_decision`) se
  sumaron en la ronda de corrección de la revisión independiente
  (CODEX-002, PR #530).
- `MirroredWorkItem` creció un campo obligatorio (`diagnostico_fallo`): las
  tres construcciones directas fuera de `mirror_projection.py`
  (`test_authority_reversion.py`, `test_projection_verifier.py`) se
  actualizaron con `diagnostico_fallo=None`.

## Alternativas descartadas y por qué

- **Llamar a `observe_work_item_external_fact` literalmente en «hacia
  atrás»**, tal como una lectura superficial del objetivo sugiere: descartada
  por violar la precondición `WAITING` del propio dominio en el único
  escenario real donde el caso ocurre (ver «Decisión interpretativa» arriba).
- **Reparar siempre por el camino corto (desde COMPROBAR cuando sea posible,
  no solo desde REVISAR)**: el dominio permite las dos entradas a REPARAR,
  pero el objetivo describe un único orden canónico
  (`... REVISAR -> REPARAR/ENTREGAR`); tomar el atajo desde COMPROBAR
  ahorraría un suceso pero introduciría una ambigüedad que el objetivo no
  pide resolver, y ninguno de los siete `WorkItem` reales de la ola de
  criticidad necesitó esa rama.
- **Enganchar `sirius-reflejar` a `.github/**` en esta misma incidencia**:
  prohibido explícitamente (C1b es del propietario, ADR-002); se deja como
  recomendación documentada, no como cambio.
