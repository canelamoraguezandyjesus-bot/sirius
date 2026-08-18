# ADR-029 — Promocionar el patrón de escritura de S1 a almacén de referencia del Work Engine, más el barrido de recuperación (A2)

- Estado: PROPUESTO
- Fecha: 2026-08-18
- Aprobación: la fusión de la PR que cierra la incidencia #186, por el propietario.

## Nota de arranque (ADR-001, publicada antes del primer commit de código)

Este ADR se abre antes de escribir el primer fichero de código de la rama,
con esta sección ya completa. El resto del documento (Opciones, Decisión,
Comprobación, Consecuencias) se rellena al terminar, con los resultados
reales.

**Por qué esta nota vive aquí y no como comentario en la incidencia #186**:
el contrato operativo de este rol («Rol: implementador genérico de Sirius»,
sección «Contrato que debes respetar») dice explícitamente: «Ese comentario
[`PR abierta: <URL>`] es lo único que puedes escribir en la incidencia». La
skill `disciplina-evidencia` pide publicar la nota «donde el humano pueda
verla (la incidencia si existe; si no, el ADR de la rama)». Ante el
conflicto, gana el contrato operativo explícito de esta ejecución — el mismo
criterio que ya adoptó ADR-026 para S1 (incidencia #182), con el mismo
razonamiento. Este ADR y la descripción de la PR (enlazada por el comentario
`PR abierta: <URL>`) son donde vive la evidencia.

### 1. ¿Dónde vive el fallo y dónde va el arreglo?

No hay un fallo que corregir: A2 es una promoción de un patrón ya decidido
(ADR-026, S1) desde código desechable (`experiments/work_engine_spike_i3/`)
a código de producción (`src/sirius_engine/`), más una pieza nueva —el
barrido de recuperación (arquitectura §3.5)— que no existía en S1. La
pregunta equivalente aquí es: **¿puede la comprobación observar lo que
afirma?** Sí, en dos frentes distintos:

- Para el patrón de escritura promovido, la comprobación es la MISMA que ya
  validó ADR-026: un proceso escritor real que se autotermina con
  `os.kill(os.getpid(), signal.SIGKILL)` en un punto nombrado, y un proceso
  padre que nunca muere y reabre el diario para comprobar el estado. Se
  reutiliza el arnés (`KillPoint`, `append_durably` con `kill_at` inyectable),
  apuntado ahora al camino de producción en `src/sirius_engine/adapters/durable/`
  en vez de al de `experiments/`.
- Para el barrido de recuperación, no existe un arnés de kill-injection
  previo porque la pieza es nueva. La comprobación aquí es un doble de
  pruebas del puerto del mundo (`RunWorldObserver`) que el test controla por
  completo: se construye un escenario donde un `Run` queda en un estado no
  terminal, se simula que el motor "estaba caído" (no se llama al barrido),
  se hace que el doble del mundo devuelva el desenlace remoto real ocurrido
  mientras tanto, y se comprueba que el barrido reconcilia el almacén al
  estado correcto exactamente una vez, incluso si se invoca dos veces
  seguidas.

### 2. Qué NO va a garantizar esto (escrito antes de implementar)

- **Hereda íntegro el límite más importante de ADR-026**: este arnés no
  demuestra que `fsync` sea necesario ante un fallo real de alimentación o
  caída del sistema operativo — `kill -9` no vacía la caché de páginas del
  kernel. Se sigue documentando como límite conocido, no se oculta ni se
  reintenta cerrar aquí (exigiría inyección de fallos a nivel de sistema de
  ficheros, fuera de alcance).
- No fija la representación física definitiva del almacén (I3+I4, D2): esta
  es, otra vez, una implementación **de referencia**. La suite se escribe
  contra el puerto `WorkEngineStore`, nunca contra el adaptador concreto,
  para que un sustituto futuro la pase sin tocarla.
- No implementa despacho real a Workers, ni acceso real a GitHub o a
  procesos del sistema operativo: el barrido de recuperación consulta el
  mundo a través de `RunWorldObserver`, un puerto propio cuya única
  implementación en este bloque es un doble de pruebas. La implementación
  real de ese puerto es A3 (espejo de la vía GitHub) y bloques posteriores,
  no A2.
- No cubre concurrencia multiproceso sobre el mismo diario (heredado de
  ADR-026: el arnés asume un único escritor).
- No cubre `fsync` mentiroso del sistema de ficheros o del disco.
- «Recalcular el siguiente paso» de un `WorkItem` en A2 se acota a lo que el
  propio dominio ya modela para la espera asíncrona: liberar el paso de
  `WAITING` a `ACTIVE` (`observe_work_item_external_fact`) cuando todos los
  `Run` vivos de ese `WorkItem` han llegado a un desenlace observable. A2 no
  inventa un despachador de trabajo nuevo: eso pertenece al Supervisor y a
  bloques posteriores (A4/A5) que sí tienen permisos y adapters de Worker.

### 3. Criterio de parada (decidido ahora, antes de ver ningún resultado)

**Se declara terminado (`READY_FOR_REVIEW`)** cuando, y solo cuando, todo lo
siguiente es cierto a la vez:

1. `DurableWorkEngineStore` implementa el puerto `WorkEngineStore` completo
   (`WorkItem` y `Run`, no un subconjunto como S1), y la batería de
   comportamiento existente en `tests/engine/` (ya escrita contra el puerto)
   pasa parametrizada sobre `InMemoryWorkEngineStore` **y**
   `DurableWorkEngineStore` sin modificar los cuerpos de esas pruebas.
2. La matriz punto-de-muerte × resultado de S1 (seis puntos nombrados,
   `WorkItem` y `Run`) se reproduce contra el camino de producción
   (`src/sirius_engine/adapters/durable/`), con el mismo resultado exacto que
   documentó `RESULTADOS.md` de S1.
3. El barrido de recuperación tiene una prueba que demuestra, con un `Run`
   cuyo terminal remoto ocurrió mientras el motor estaba "caído": el
   reinicio no pierde ni duplica trabajo, y el `WorkItem` en `WAITING`
   asociado se libera a `ACTIVE` cuando corresponde.
4. Ejecutar el barrido dos veces seguidas sobre el mismo estado deja
   exactamente el mismo resultado que ejecutarlo una vez (mismos eventos,
   ningún evento nuevo en la segunda pasada).
5. Al menos cuatro mutaciones sembradas y vistas fallar: quitar el `fsync`
   (mediante un espía que comprueba que se invoca; una escritura sin él dejó
   de invocarlo y el espía lo detecta, aunque el arnés de kill-injection no
   pueda distinguir el resultado por la razón del punto 2 de esta nota),
   quitar la comprobación de checksum, quitar `recover_invalid_tail`, y
   romper la idempotencia del barrido de recuperación (una segunda pasada
   que ya no es no-operativa).
6. Los límites conocidos (sección 2 de esta nota, más los heredados de
   ADR-026) quedan escritos en este ADR y no se pierden.
7. La prueba estructural de frontera `sirius`/`sirius_engine` sigue en verde
   sin excepciones nuevas.
8. Las cuatro validaciones obligatorias + `git diff --check` en verde.

**Se detiene con `BLOCKED_BY_DECISION`** si en algún momento el trabajo
exige fijar la representación física definitiva del almacén, añadir una
dependencia nueva al proyecto, o decidir cómo se despacha trabajo real a un
Worker (fuera del alcance explícito de la incidencia #186).

**Se detiene con `FAILED_SAFELY`** si el entorno del runner no permite que
un proceso hijo se autotermine con `SIGKILL` de forma fiable y observable
por el padre (la misma condición que ya declaró ADR-026), o si `main` no
contiene `src/sirius_engine/domain/` ni `experiments/work_engine_spike_i3/`
al empezar (dependencia declarada por la incidencia como no satisfecha).

**Regla de las dos rondas** (disciplina-evidencia §2): si dos rondas de
revisión seguidas encuentran hallazgos de la misma familia (por ejemplo, dos
puntos distintos de la matriz sin resolver duplicación, o dos escenarios
distintos del barrido perdiendo trabajo), se para de parchear caso a caso y
se revisa el diseño entero de la pieza afectada.

### 4. ¿Qué haría el fallo imposible en vez de improbable?

- El patrón de escritura ya lo resolvió ADR-026 (autoterminación inyectada
  dentro del propio escritor, checksum por registro, cola inválida
  recortada antes de reintentar): A2 lo hereda sin reabrir esa decisión.
- Para el barrido: hacerlo **puramente derivado** del diario
  (`list_events()` + `rebuild_state`, sin estado mutable propio fuera de lo
  que el almacén ya persiste) hace que una segunda pasada sobre el mismo
  diario sea idempotente por construcción, no por disciplina de quien la
  invoca — no hay ningún contador ni marca "ya visto" que una segunda
  ejecución pudiera olvidar poner a cero. Un `Run` ya reconciliado a
  `FINISHED` sale del conjunto "no terminado" que el barrido recorre, así
  que no hay ninguna rama de código que pueda volver a tocarlo.

---

## Contexto y problema

A1 (incidencia #177, PR #178) entregó el dominio, el puerto `WorkEngineStore`
y la única implementación existente, `InMemoryWorkEngineStore`. S1
(incidencia #182, PR #185, ADR-026) evaluó y decidió el patrón de escritura
seguro del almacén -diario append-only con `fsync`, checksum SHA-256 por
registro e idempotencia por clave- contra un subconjunto desechable del
puerto en `experiments/work_engine_spike_i3/`. La incidencia #186 (A2) pide
dos entregas: promocionar ese patrón a una implementación **de referencia**
del puerto completo, y el barrido de recuperación al arrancar (arquitectura
§3.5), que no existía en S1.

## Opciones consideradas

El patrón de escritura no se reabre (ver «Método: adoptar lo ya probado, no
reinventar» de la incidencia #186): la comparativa completa de patrones ya
quedó resuelta en ADR-026 y `experiments/work_engine_spike_i3/RESULTADOS.md`.
Lo único que este ADR decide de nuevo es el barrido de recuperación, con dos
opciones:

| Opción | Encaje | Decisión |
|---|---|---|
| Barrido con estado propio (p. ej. una tabla "runs ya reconciliados") | Añade una fuente de verdad nueva que puede desincronizarse del diario, y exige que alguien la limpie o migre | Descartada |
| Barrido puramente derivado del diario (`list_events()` + `rebuild_state`), sin memoria propia entre invocaciones | Directo: reutiliza exactamente lo que A1 ya entrega; la idempotencia es una consecuencia del diseño (§4 de esta nota), no una comprobación aparte | **Adoptada** |

Para "recalcular el siguiente paso" de un `WorkItem` (arquitectura §3.5), se
consideró también inventar un despachador mínimo que decidiera qué Worker
lanzar a continuación. Descartado: A2 no tiene Adapters de Worker, permisos
ni presupuesto (eso es A4/A5); construirlo aquí sería decidir por cuenta
propia algo fuera del alcance permitido de la incidencia #186 (sección
«Fuera de alcance»). Se acota a lo que el propio dominio de A1 ya modela
para la espera asíncrona: liberar `WAITING -> ACTIVE` vía
`observe_work_item_external_fact` cuando todos los `Run` vivos del
`WorkItem` alcanzaron un desenlace observable.

## Decisión

1. **Promover el patrón de escritura de S1** desde
   `experiments/work_engine_spike_i3/` a código de producción en
   `src/sirius_engine/adapters/durable/` (`journal.py`, `entity_codec.py`),
   sin reabrir el diseño: mismo diario JSON Lines, mismo `KillPoint`/
   `append_durably` con el hook de corte inyectable, mismo
   `recover_invalid_tail`, mismo `replay` con la distinción cola-truncada
   vs. corrupción-interna.
2. **Implementar el puerto `WorkEngineStore` completo** (`WorkItem` y `Run`,
   las ~36 operaciones, no el subconjunto que cubrió S1) en
   `DurableWorkEngineStore` (`src/sirius_engine/adapters/durable/store.py`),
   reproduciendo exactamente la semántica de `InMemoryWorkEngineStore`
   (incluida la cascada de invalidación de Runs en `change_work_item_scope`
   y el guardián de recurso mutable en `dispatch_run`). A diferencia de S1
   (que releía el diario entero en cada llamada, límite conocido #6 de
   `RESULTADOS.md`), este almacén reproduce el diario **una sola vez** al
   construirse y mantiene un índice en memoria actualizado de forma
   incremental en cada anexo.
3. **Añadir `idempotency_key` como parámetro opcional** en cada método de
   escritura del almacén durable (no en el puerto: es una extensión
   compatible, igual que ya hacía el `durable_store.py` de S1), para que un
   llamador que reintente la misma petición lógica tras un reinicio no
   duplique el evento.
4. **Parametrizar la batería de comportamiento existente** (`tests/engine/`,
   ya escrita contra el puerto desde A1) sobre `InMemoryWorkEngineStore` y
   `DurableWorkEngineStore` en `conftest.py` (`STORE_FACTORIES`), sin tocar
   el cuerpo de ninguna prueba existente.
5. **Barrido de recuperación** (`src/sirius_engine/recovery.py`,
   `run_recovery_sweep`): puramente derivado del diario
   (`rebuild_state(store.list_events())`), con un puerto propio
   `RunWorldObserver` (`src/sirius_engine/ports/world.py`) para consultar el
   desenlace remoto de cada `Run` no terminado. Reconcilia cada `Run` según
   lo que el mundo reporte (`SUCCEEDED`/`FAILED`/`LOST`/`CANCELLED`/
   `PENDING`), promoviendo primero el `Run` al estado mínimo que la
   transición terminal exige (`PREPARED -> DISPATCHED[-> RUNNING]`) cuando
   el motor murió antes de registrar un paso intermedio que el desenlace
   real implica. Libera `WorkItem` en `WAITING` a `ACTIVE` cuando todos sus
   `Run` vivos ya terminaron. En A2, la única implementación de
   `RunWorldObserver` es un doble de pruebas (`FakeRunWorldObserver`); la
   real es A3 y bloques posteriores.

## Comprobación que la sostiene

- **Requisito 1 (batería contra el puerto, ambas implementaciones)**:
  `uv run pytest tests/engine/ -q --deselect tests/engine/test_spike_i3_durability.py`
  → **145 passed** (la batería completa de A1, parametrizada x2 sin cambiar
  ningún cuerpo de prueba).
- **Requisito 2 (matriz punto-de-muerte contra producción)**:
  `tests/engine/test_durable_journal.py` reproduce la matriz de seis puntos
  nombrados de S1 contra `src/sirius_engine/adapters/durable/`, con
  `tests/engine/_durable_writer_process.py` como arnés (subproceso real,
  `SIGKILL` inyectado por el propio escritor) — 13 pruebas: 6 de la matriz +
  reintento sin duplicación tras reinicio + ciclo de vida real reabierto +
  4 mutaciones. `tests/engine/test_spike_i3_durability.py` (S1, 24 pruebas)
  se conserva sin tocar, como evidencia fechada de la incidencia #182.
- **Requisitos 3 y 4 (barrido de recuperación, con idempotencia)**:
  `tests/engine/test_recovery_sweep.py`, 16 pruebas — incluye un `Run`
  `RUNNING` que tuvo éxito mientras el motor "estaba caído" (libera también
  el `WorkItem WAITING` asociado), un `Run` `DISPATCHED` promovido hasta
  `RUNNING` antes de cerrarse, un `Run` `PREPARED` promovido hasta
  `DISPATCHED` antes de fallar, `LOST` respetando el `deadline`, un
  `WorkItem WAITING` con dos `Run` que solo se libera cuando ambos
  terminaron, y la prueba directa de requisito 4: ejecutar el barrido dos
  veces seguidas sobre el mismo estado no anexa ningún evento nuevo.
- **Requisito 5 (mutaciones)**: cuatro sembradas y vistas fallar —
  `test_mutacion_quitar_el_checksum_acepta_un_registro_corrupto`,
  `test_mutacion_quitar_la_comprobacion_de_idempotencia_duplica`,
  `test_mutacion_quitar_recover_invalid_tail_funde_el_reintento_con_la_cola_rota`
  (las tres en `test_durable_journal.py`) y
  `test_mutacion_quitar_el_filtro_de_runs_terminados_rompe_la_idempotencia`
  (`test_recovery_sweep.py`, sobre el barrido). Para `fsync`, el arnés de
  kill-injection no puede distinguir su ausencia (ver «Qué NO va a
  garantizar esto» arriba), así que
  `test_mutacion_quitar_el_fsync_deja_de_invocarlo` usa un espía sobre
  `os.fsync` en vez de la matriz: la implementación real lo invoca
  exactamente una vez por anexo; un mutante que borre esa línea dejaría la
  lista de llamadas vacía.
- **Requisito 7 (frontera intacta)**:
  `uv run pytest tests/engine/test_boundary.py -q` → **2 passed**.
- **Las cuatro validaciones obligatorias + `git diff --check`, en verde**
  sobre el repositorio completo: `uv run ruff format --check .` (376
  ficheros), `uv run ruff check .` (sin hallazgos), `uv run mypy src tests`
  (358 ficheros, sin errores) y `uv run pytest` con
  `QT_QPA_PLATFORM=offscreen` fijado a mano (nota operativa de la
  incidencia #186: `implement-sirius-work.yml` no lo fija, a diferencia de
  `quality.yml`) → **2521 passed, 3 skipped, 289.49 s**. `git diff --check
  --cached` sin salida.

## Consecuencias

- **A2 queda satisfecha sin fijar la representación física definitiva**: la
  suite completa de `tests/engine/` corre sobre el puerto, y
  `DurableWorkEngineStore` es un adaptador más -intercambiable en
  `conftest.py`- no una migración. D2 (o el propietario adelantando I4)
  sigue siendo quien fija la representación definitiva.
- **Límites conocidos, heredados de ADR-026 y sin cerrar aquí** (repetidos
  también en la nota de arranque, sección 2, para que no se pierdan):
  1. Este arnés no demuestra que `fsync` sea necesario ante un fallo real de
     alimentación o caída del SO (`kill -9` no vacía la caché de páginas del
     kernel); se compensa parcialmente con el espía sobre `os.fsync`, que sí
     demuestra que el código lo invoca, no que sea necesario.
  2. `fsync` mentiroso del sistema de ficheros/disco: no cubierto.
  3. Corrupción del medio: solo detección (checksum + distinción cola
     truncada/corrupción interna), sin reparación ni redundancia.
  4. Concurrencia multiproceso sobre el mismo diario: el arnés y el almacén
     asumen un único escritor; no probado ni protegido.
- **Límites nuevos de A2**:
  5. El barrido de recuperación no despacha trabajo nuevo ni decide qué
     Worker usar: solo reconcilia `Run` existentes contra el mundo y libera
     la espera asíncrona de un `WorkItem`. El despacho real es A4/A5 y el
     Supervisor.
  6. `RunWorldObserver` solo tiene, en A2, un doble de pruebas
     (`FakeRunWorldObserver`). La implementación real que lee GitHub o
     procesos locales es A3 y bloques posteriores; hasta entonces, el
     barrido no tiene ningún efecto fuera de pruebas.
  7. La promoción de un `Run` al estado mínimo que exige su transición
     terminal (`_ensure_dispatched`/`_ensure_running` en `recovery.py`)
     asume que un desenlace remoto reportado por el mundo implica que los
     pasos intermedios sí ocurrieron, aunque el diario no los registrara
     antes de que el motor muriera. Es una inferencia razonable (el mundo no
     reporta un desenlace de algo que nunca se despachó), pero es una
     inferencia, no una observación directa de esos pasos intermedios.
  8. `mark_run_lost` respeta el `deadline` del `Run` (arquitectura §3.3): si
     el mundo reporta `LOST` antes de que venza, el barrido no actúa y
     "repite la consulta" en la siguiente pasada, tal como exige el
     requisito de reinicio de la incidencia — no hay temporizador propio
     que dispare esa siguiente pasada; eso es responsabilidad de quien
     invoque `run_recovery_sweep` (fuera de alcance de A2).
