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
