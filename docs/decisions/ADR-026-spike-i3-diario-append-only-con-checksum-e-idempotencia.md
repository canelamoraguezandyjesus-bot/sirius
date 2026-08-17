# ADR-026 — Adoptar diario append-only con `fsync`, checksum por registro e idempotencia por clave como patrón de escritura seguro del spike I3

- Estado: PROPUESTO
- Fecha: 2026-08-17
- Aprobación: la fusión de la PR que cierra la incidencia #182, por el propietario.

## Nota de arranque (ADR-001, publicada antes del primer commit de código)

Este ADR se abre en el primer commit de la rama, con esta sección ya escrita
y sin ninguna otra. El resto del documento (Decisión, Comprobación,
Consecuencias) se completa al terminar el spike, con los resultados reales.

**Por qué esta nota vive aquí y no como comentario en la incidencia #182**: el
contrato operativo de este rol («Rol: implementador genérico de Sirius»,
sección «Contrato que debes respetar») dice explícitamente: «Ese comentario
[`PR abierta: <URL>`] es lo único que puedes escribir en la incidencia». La
skill `disciplina-evidencia` pide publicar la nota «donde el humano pueda
verla (la incidencia si existe; si no, el ADR de la rama)». Ante el
conflicto, gana el contrato operativo explícito de esta ejecución: es más
específico, más reciente y lleva detrás el historial de incidentes de esta
misma incidencia (#182, rondas con runs 31985897583 y 31990550597) sobre lo
que pasa cuando el rol decide por su cuenta salirse del contrato. La matriz,
la comparativa y el patrón elegido —que la incidencia pide «publicar... en
esta incidencia»— se satisfacen en su lugar en la descripción de la PR (que
el comentario `PR abierta: <URL>` enlaza) y en
`experiments/work_engine_spike_i3/RESULTADOS.md`, dentro del propio diff.

### 1. ¿Dónde vive el fallo y dónde va el arreglo?

No es una corrección de un fallo existente: es una decisión de diseño
(spike). La pregunta equivalente para un arnés de pruebas es: **¿puede el
sitio de la comprobación OBSERVAR lo que afirma?** Sí, por construcción: el
punto de corte lo decide el propio proceso escritor, que se autotermina con
`os.kill(os.getpid(), signal.SIGKILL)` justo después de completar las
acciones que le tocan hasta ese punto nombrado — no un temporizador externo
que mata «en algún momento» y podría acertar entre transiciones en vez de
dentro (el riesgo que la propia incidencia declara). El proceso PADRE, que
nunca muere, es quien reabre el diario y comprueba el estado reconstruido.

### 2. Qué NO va a garantizar esto (escrito antes de implementar)

- **No demuestra durabilidad real ante fallo de alimentación o caída del
  SO.** `kill -9` mata el proceso, pero el kernel no vacía su caché de
  páginas al hacerlo: los bytes que un `write()` ya entregó al kernel siguen
  visibles al releer el fichero en la MISMA máquina, se haya llamado a
  `fsync` o no. Este arnés puede demostrar orden y atomicidad de la
  escritura (registro completo vs. truncado, sin duplicación), pero NO puede
  demostrar por sí solo que `fsync` sea necesario — eso exigiría inyección de
  fallos a nivel de sistema de ficheros (`dm-flakey`, ALICE, Jepsen), fuera
  de alcance de un spike en un runner de CI. Se documenta como límite
  conocido, no se oculta.
- No cubre `fsync` mentiroso del sistema de ficheros/disco.
- No cubre corrupción del medio más allá de lo que el checksum por registro
  detecta (truncamiento y alteración de bytes ya escritos), ni reparación
  (solo detección; sin redundancia).
- No cubre concurrencia multiproceso: el arnés asume un único escritor.
- No implementa el puerto `WorkEngineStore` completo: solo el subconjunto de
  operaciones de `WorkItem` necesario para ejercitar el patrón
  (crear/activar/cancelar/fallar-a-salvo), no `Run`, no las fases del ciclo
  revisar-reparar (`entregar` las exige) ni el resto. Suficiente para
  demostrar el patrón de escritura; no es una migración.
- No fija la representación definitiva del almacén (eso es I3+I4, D2).

### 3. Criterio de parada (decidido ahora, antes de ver ningún resultado)

**Se declara terminado (`READY_FOR_REVIEW`)** cuando, y solo cuando, todo lo
siguiente es cierto a la vez:

1. Al menos un patrón queda implementado con un arnés de kill-injection que
   cubre, con puntos NOMBRADOS (no aleatorios), como mínimo: antes de abrir
   el fichero, entre apertura y escritura, escritura truncada (torn write
   inyectado deliberadamente, no una interrupción real de la syscall — se
   documenta por qué esa es la forma honesta de probarlo determinista),
   escrito-sin-`fsync`, `fsync`-sin-cerrar, y cierre completo.
2. Un caso adicional de duplicación por reintento (la mitad «sin
   duplicación» del requisito, vía clave de idempotencia) tras un reinicio
   simulado.
3. Cada punto de la matriz clasifica el resultado como exactamente uno de
   «no ocurrió» o «ocurrió una sola vez» — nunca «a medias» ni «dos veces» —
   y la prueba lo comprueba con una aserción, no con inspección manual.
4. Al menos dos mutaciones sembradas (una que desactive la detección de
   truncamiento, otra que desactive la idempotencia) y vistas fallar en un
   punto concreto de la matriz.
5. Límites conocidos (sección 2 de esta nota) escritos en el ADR final y en
   `RESULTADOS.md`.
6. Comparativa de los patrones considerados, con motivo de adopción o
   descarte de cada uno (probado o no), en `RESULTADOS.md` y en la PR.
7. Las cuatro validaciones obligatorias + `git diff --check` en verde.

**Se detiene con `BLOCKED_BY_DECISION`** si, en cualquier momento, el patrón
que mejor encaja exige una dependencia nueva del proyecto (prohibida por el
alcance) — se documenta cuál y por qué antes de parar.

**Se detiene con `FAILED_SAFELY`** si el entorno del runner no permite que un
proceso hijo se autotermine con `SIGKILL` de forma fiable y observable por el
padre (por ejemplo, un sandbox que intercepte la señal) — sin inventar una
alternativa que no demuestre una muerte real, porque eso sería el falso verde
que la incidencia ya advierte como riesgo principal.

**Regla de las dos rondas** (disciplina-evidencia §2): si dos rondas de
revisión seguidas encuentran hallazgos de la misma familia en la matriz (por
ejemplo, dos puntos distintos sin resolver «duplicación»), se para de
parchear caso a caso y se revisa el diseño del patrón entero.

### 4. ¿Qué haría el fallo imposible en vez de improbable?

- Autoterminación inyectada DENTRO del propio código del escritor, en el
  punto nombrado, en vez de un observador externo que mata por temporización:
  el punto de corte es determinista por construcción, no una carrera contra
  el reloj — hace el «falso verde por matar entre transiciones» detectable
  antes de escribir una sola prueba, porque el punto SIEMPRE es el nombrado.
- El checksum por registro convierte «¿se truncó la escritura?» en un hecho
  verificable por el replay (comparación de hash), no en una suposición.
- La prueba de mutación demuestra que la propiedad depende realmente del
  mecanismo (checksum / idempotencia) — sin ella, no hay forma de distinguir
  una prueba que pasa porque el patrón funciona de una que pasa porque no
  comprueba nada.
- Ninguno de estos hace imposible el límite de la sección 2 (kill -9 no
  simula pérdida de página de caché): eso es un límite del método de prueba
  disponible en un runner de CI, no un defecto que este diseño pueda cerrar;
  se documenta en vez de fingir que se cierra.

---

## Contexto y problema

La incidencia #182 (S1, spike I3 del plan de implementación del Work Engine)
pide decidir el patrón de escritura seguro del almacén: un proceso matado con
`kill -9` en cualquier punto del ciclo de una transición no debe dejar ni
pérdida ni duplicación al rearrancar. No fija la representación definitiva
del almacén (eso es I3+I4, D2); solo evalúa el patrón y una representación de
referencia. A1 (incidencia #177, ya fusionada) entrega el dominio, el puerto
`WorkEngineStore` y un diario de eventos append-only **en memoria**
(`InMemoryWorkEngineStore`), con `rebuild_state` como reproducción
determinista del diario.

## Opciones consideradas

Ver la tabla completa, con motivo de adopción o descarte de cada una,
probada o no, en
[`experiments/work_engine_spike_i3/RESULTADOS.md`](../../experiments/work_engine_spike_i3/RESULTADOS.md#comparativa-de-los-patrones-considerados).
Resumen: reemplazo atómico (descartado, mal encaje con un diario de muchos
eventos pequeños), SQLite WAL (descartado por ahora, complejidad de adopción
sin ventaja de durabilidad demostrable sobre el diario), registro de
intención + reconciliación (descartado para transiciones internas del
almacén -no hay "acción" separada del "desenlace" cuando la única acción
observable es el propio anexo durable-, pero sigue siendo el patrón correcto
para acciones externas como el despacho de un `Run`, fuera de alcance de
S1), e idempotencia por identificador monótono (adoptada, como componente).

## Decisión

Adoptar **diario append-only con `fsync`, checksum SHA-256 por registro y
clave de idempotencia**, como extensión directa del diario append-only que
A1 ya entregó (`Event` + `rebuild_state`): el mismo diseño, escrito a fichero
en vez de a una lista en memoria, con la validación necesaria para
sobrevivir a `kill -9` en cualquier punto del ciclo.

Se implementó en `experiments/work_engine_spike_i3/` (desechable): el núcleo
de escritura durable con seis puntos de corte nombrados
(`durable_journal.py`), el subproceso real que los ejecuta
(`writer_process.py`), la (de)serialización de `WorkItem` y de `Run`
(`entity_codec.py`), y un almacén mínimo del puerto sobre ese diario
(`durable_store.py`) que cubre crear/activar/cancelar/fallar-a-salvo de
`WorkItem` (no el CRUD de `Run` ni el resto — subconjunto deliberado, ver
límite conocido §2). La matriz de seis puntos se repite también sobre una
transición representativa de `Run` (`run_prepared`) directamente contra
`append_durably`/`replay`, sin pasar por `durable_store.py` — corrección
posrevisión (hallazgo CODEX-002, ronda 2): la definición de I3 exige
`WorkItem` **y** `Run` en la evidencia, no solo en el CRUD.

Corrección posrevisión adicional (hallazgo CODEX-001, ronda 2):
`append_durably()` ahora empieza cada anexo llamando a
`recover_invalid_tail()`, que recorta y sincroniza la cola inválida que un
`kill -9` en `mid_write_torn` pudo dejar. Sin esto, un reintento se
escribía (por `O_APPEND`) detrás de esa cola, y la línea fundida (cola +
registro nuevo) seguía sin analizar como JSON válido — `replay` la
descartaba entera, reintento incluido, indefinidamente. Detalle y prueba en
`RESULTADOS.md` §"Recuperar la cola truncada antes de reintentar".

## Comprobación que la sostiene

- **Matriz completa** en `experiments/work_engine_spike_i3/RESULTADOS.md` y
  reproducida por `tests/engine/test_spike_i3_durability.py`: 23 pruebas — 6
  puntos de corte nombrados para `WorkItem` más los mismos 6 para `Run`
  (matados con `SIGKILL` inyectado por el propio proceso escritor,
  subproceso real vía `subprocess.run`), duplicación por reintento tras
  reinicio, un ciclo de vida real reabierto desde cero, recuperación de la
  cola truncada tras `mid_write_torn` (kill → reapertura → reintento
  produce exactamente un evento nuevo preservando el prefijo válido),
  recuperación de un registro completo escrito salvo su `\n` final (prefijo
  de N-1 bytes → reapertura → reintento produce exactamente un evento nuevo
  sin fundirse con el prefijo), una prueba dedicada de que
  `recover_invalid_tail` es no-operativa sobre un diario ya limpio, y dos
  mutaciones. Comando ejecutado:
  `uv run pytest tests/engine/test_spike_i3_durability.py -v` → **23
  passed**.
- **Mutación vista fallar en dos puntos concretos** (requisito 4): quitar la
  comparación de checksum hace que un registro con un byte alterado se
  acepte como válido (`test_mutacion_quitar_el_checksum_acepta_un_registro_corrupto`);
  quitar la comprobación de `idempotency_key` antes de anexar produce dos
  registros para el mismo reintento en vez de uno
  (`test_mutacion_quitar_la_comprobacion_de_idempotencia_duplica`).
- **Las cuatro validaciones obligatorias + `git diff --check`, en verde**
  sobre el repositorio completo: `uv run ruff format --check .` (350
  ficheros), `uv run ruff check .` (sin hallazgos), `uv run mypy src tests`
  (338 ficheros, sin errores — `experiments/` se resuelve como dependencia
  de `tests/engine/test_spike_i3_durability.py` sin tocar `pyproject.toml`,
  comprobado empíricamente antes de escribir el arnés completo), `uv run
  pytest` con `QT_QPA_PLATFORM=offscreen` (2242 passed, 3 skipped, 302,34 s
  — ver «Consecuencias» sobre por qué se fijó esa variable a mano) y `git
  diff --check --cached` sin salida.

## Consecuencias

- El patrón queda evaluado y con evidencia reproducible en CI (requisito 3):
  `tests/engine/` sí lo recorre `pytest`, a diferencia de `experiments/`.
- **No se afirma que el arnés demuestre que `fsync` sea necesario ante fallo
  real de alimentación**: la matriz muestra el mismo resultado
  ("ocurrió una vez") con y sin `fsync` de por medio, porque `kill -9` no
  vacía la caché de páginas del kernel. Es el límite conocido más importante
  de este spike y queda escrito, no oculto (`RESULTADOS.md` §"Límites
  conocidos").
- **No fija la representación definitiva del almacén**: A2 puede reutilizar
  este patrón (`Event`/`rebuild_state` de A1 sin cambios, detección de cola
  corrupta, idempotencia por clave), pero eso lo decide D2 (o antes, si el
  propietario adelanta I4), no este ADR.
- **Hallazgo colateral, sin corregir aquí (fuera de alcance de S1)**:
  `.github/workflows/implement-sirius-work.yml` no fija
  `QT_QPA_PLATFORM=offscreen` como sí hace `quality.yml` (línea 29). Sin esa
  variable, `uv run pytest` completo aborta con un `Fatal Python error`
  dentro de Qt (`QGuiApplicationPrivate::createPlatformIntegration`) al
  llegar a la suite de GUI, reproducido dos veces en esta misma ejecución.
  Se adaptó fijando la variable a mano al invocar `pytest` (no toca
  workflows, prohibido por el alcance de esta incidencia); se documenta aquí
  para que quien revise A2 (o el propietario) decida si vale la pena
  igualarlo en el workflow real.
- Queda pendiente, si el propietario lo quiere: el CRUD completo de `Run`
  en `durable_store.py` para las nuevas piezas de A2 (la matriz ya cubre su
  transición de escritura, ver arriba), e implementar un índice en memoria
  para que `_next_sequence`/la comprobación de idempotencia no relean el
  diario entero en cada anexo (límite conocido #6).
