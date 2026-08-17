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
  (crear/activar/cancelar/fallar-a-salvo/entregar), no `Run` ni el resto.
  Suficiente para demostrar el patrón de escritura; no es una migración.
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

*El resto de este documento (Contexto, Opciones consideradas, Decisión,
Comprobación, Consecuencias) se completa al terminar el spike.*
