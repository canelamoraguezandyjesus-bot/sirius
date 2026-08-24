# ADR-064 — Diario del despachador durable reutiliza ADR-061

- Estado: APROBADO
- Fecha: 2026-08-22
- Aprobación: fusión de la PR de la incidencia #242 por el propietario
- Enmendado: ADR-082 supera su premisa de proceso persistente (decisión I4, #270)

## Contexto y problema

H-11 (`docs/audits/registro_defectos.yml`, incidencia #242) es el hermano
exacto de H-10 (incidencia #236, cerrado por ADR-061): la única
implementación de `DispatchJournal` (`ports/dispatch_journal.py`) es
`InMemoryDispatchJournal`, cuyo propio docstring lo declara un hueco
deliberado -"la representación durable, si hiciera falta, es una decisión
posterior". `C2-P3` promete una sola activación por `WorkItem`, y el diario
es la fuente de la que el despachador lee si ya activó un `work_id`
(`dispatcher.dispatch_work_item`, guarda 1). Con el diario en memoria, esa
garantía solo vale dentro de un proceso: dos ejecuciones del despachador
sobre el mismo `WorkItem` -o un proceso que muere entre reservar y grabar y
se reinicia- pueden producir una segunda incidencia para el mismo trabajo.

La incidencia #242 es explícita: **si la respuesta correcta es la de
ADR-061, se aplica y se dice que se aplica, en vez de razonarla otra vez**.
Este ADR hace exactamente eso, y solo se detiene a decidir en el único punto
donde el caso difiere de verdad: la coordinación de `reservar`/`liberar`
-que `SupervisorJournal` ni siquiera tiene- no existía cuando ADR-061 se
escribió.

## Criterio de parada (escrito ANTES de decidir)

1. El criterio de parada 1 de ADR-061 se reutiliza sin cambios: si la
   durabilidad exigiera inventar mecanismo de escritura propio en vez de
   reutilizar sin modificar `adapters/durable/journal.py`
   (`append_durably`/`replay`), se descarta el outbox propio. No hay motivo
   para esperar que aplique distinto aquí: el registro a persistir
   (`DispatchEpisode`) es del mismo tamaño y forma que `SupervisionEpisode`.
2. Punto que sí es nuevo respecto a ADR-061: `reservar`/`liberar`
   coordinan, con un `threading.Event` en memoria, cuál de dos llamadas
   concurrentes escribe (revisión de la incidencia #240, ronda 2). Un
   `Event` no es serializable. Si cerrar H-11 exigiera que una reserva EN
   CURSO -no un episodio ya grabado- sobreviviera a un reinicio, eso sería
   mecanismo nuevo sin precedente y forzaría reabrir la decisión. Antes de
   escribir código: los requisitos de aceptación de la incidencia #242 piden
   que la reserva **grabada** (el episodio) sobreviva y que dos ejecuciones
   produzcan una sola incidencia -no que una reserva en curso sin episodio
   sobreviva-, así que la coordinación de `reservar`/`liberar` se queda
   exactamente donde está (en memoria, por proceso) y solo `record`/
   `episode_for`/`episodes` ganan persistencia. Si al escribir la prueba
   H11-P2 (dos ejecuciones, una sola incidencia) resultara que hace falta
   algo más, se para aquí y se reabre esta decisión.
3. La prueba por mutación exigida por la incidencia (con el diario en
   memoria en lugar del durable, la prueba de supervivencia al reinicio debe
   caer) debe caer de verdad. Si pasa con los dos, la prueba no prueba nada
   y se corrige antes de seguir.

## Opciones consideradas

**(a) Fusionar con el diario de eventos del `WorkEngineStore`.** Descartada
por la misma razón que ADR-061 la descartó para el supervisor: acopla dos
puertos que C1/C2 mantienen separados a propósito, y el diario de eventos
modela transiciones tipadas de `WorkItem`/`Run`, no "qué orden, qué
incidencia, qué etiqueta" de un episodio de despacho.

**(b) Un outbox propio, reutilizando `durable/journal.py` -la misma decisión
que ADR-061.** Mantiene los puertos separados, reutiliza sin modificar el
módulo genérico ya probado, y el único código nuevo es la serialización de
`DispatchEpisode` a JSON -exactamente el mismo coste que ADR-061 ya
argumentó para `SupervisionEpisode`.

**(c, descartada sin desarrollar) Persistir también la reserva EN CURSO
-antes de grabar el episodio-, para que una reserva huérfana por un proceso
muerto se reconozca al reabrir.** El criterio de parada 2 la descarta: no la
exige ningún requisito de la incidencia #242, y closing H-11 con (b) ya dejó
por escrito -en las Consecuencias, abajo- que este caso queda pendiente para
cuando el despachador corra desatendido (D2), igual que ADR-061 dejó escrita
la falta de atomicidad entre "escalar" y "marcar pendiente" para su propio
caso.

## Decisión

Se elige **(b), la misma decisión de ADR-061**, implementada como
`sirius_engine.adapters.durable.dispatch_journal.DurableDispatchJournal`,
sobre un fichero JSON Lines independiente, reutilizando sin modificar
`append_durably`/`replay` de `adapters/durable/journal.py`.

Un único tipo de registro -`dispatch_episode_recorded`-, con el mismo
formato de línea que `journal.py` ya usa (checksum SHA-256, `fsync` de
fichero y de directorio en cada anexo). Al abrir, se reproduce el diario una
sola vez y se reconstruye `_por_work_id`/`_episodios` en memoria, igual que
`DurableSupervisorJournal._load`.

Diferencia explícita con ADR-061 (la que motivó el criterio de parada 2):
`reservar`/`liberar` -que `SupervisorJournal` ni siquiera tiene como
operaciones- se quedan enteramente en memoria (`_lock` + `_en_curso` con
`threading.Event`), idénticas a `InMemoryDispatchJournal`. Solo `record`
(y, por tanto, `episode_for`/`episodes` tras reabrir) gana persistencia. Una
reserva obtenida pero nunca grabada ni liberada -el proceso murió entre
`reservar` y `record`- no sobrevive a un reinicio: un proceso nuevo no
encuentra `_en_curso` y puede reservar de nuevo, el mismo comportamiento que
ya tiene hoy `liberar` tras una guarda rechazada. Ningún requisito de la
incidencia #242 exige más que eso; se documenta como límite conocido en
Consecuencias, no como un hueco descubierto tarde.

`InMemoryDispatchJournal` no cambia.

## Comprobación que la sostiene

- Criterio de parada 1: `DurableDispatchJournal` importa
  `append_durably`/`replay` de `adapters/durable/journal.py` sin modificar
  ese módulo -`git diff --stat -- src/sirius_engine/adapters/durable/journal.py`
  vacío en esta rama.
- Criterio de parada 2: `reservar`/`liberar` no tocan el fichero, solo
  `_lock`/`_en_curso`/`threading.Event` -mismo código que
  `InMemoryDispatchJournal`- (`src/sirius_engine/adapters/durable/dispatch_journal.py`).
  H11-P2 (`tests/engine/test_durable_dispatch_journal.py::test_h11_p2_dos_ejecuciones_del_despachador_producen_una_sola_incidencia`)
  pasa sin necesitar más que eso: no hizo falta reabrir la decisión.
- Criterio de parada 3 (prueba por mutación):
  `test_mutacion_diario_en_memoria_en_vez_de_durable_no_sobrevive_al_reinicio`
  sustituye el diario durable por `InMemoryDispatchJournal` y comprueba que
  la segunda "ejecución" NO reconoce el episodio de la primera -cae
  exactamente la propiedad que H11-P1/H11-P2 exigen, y el mismo test
  contrasta con la implementación real, que sí sobrevive.
- Resultado de la suite completa en esta rama:

  ```
  $ uv run ruff format --check .
  472 files already formatted
  $ uv run ruff check .
  All checks passed!
  $ uv run mypy src tests
  Success: no issues found in 450 source files
  $ uv run pytest -q
  3253 passed, 6 skipped in 295.39s (0:04:55)
  ```

## Consecuencias

- `DispatchJournal` sigue sin conocer nada de `WorkEngineStore`, igual que
  `SupervisorJournal`: ninguna dependencia nueva entre puertos.
- El proceso que despache en producción de forma desatendida (D2, futuro)
  deberá construir `DurableDispatchJournal` sobre un fichero propio -hoy
  `dispatch_cli.py` sigue construyendo `InMemoryDispatchJournal` en cada
  invocación, fuera del alcance permitido de la incidencia #242 (no se toca
  el despachador ni su cableado); ese cableado es justo el trabajo que D2
  hereda, con el adaptador durable ya disponible.
- Una reserva obtenida pero no grabada ni liberada -el proceso murió justo
  entre `reservar` y `record`- no sobrevive a un reinicio: un proceso nuevo
  puede volver a reservar el mismo `work_id`. Si el `crear_incidencia` de la
  llamada muerta ya había llegado a GitHub antes de morir, un reintento
  podría crear una segunda incidencia -el mismo riesgo que H-11 describe
  como "alto cuando el motor corra desatendido"-. No es un caso nuevo sin
  manejar: es exactamente el límite que el criterio de parada 2 decidió no
  cerrar aquí, y queda escrito para que D2 no lo descubra tarde.

## Alternativas descartadas y por qué

**(a) Fusionar con el diario de eventos del `WorkEngineStore`.** Misma razón
que ADR-061: acopla dos puertos separados a propósito y pierde el sitio para
el texto libre ("qué orden", "qué incidencia de GitHub") que el diario de
eventos no modela.

**(c) Persistir también la reserva en curso.** Mecanismo sin precedente,
no exigido por ningún requisito de la incidencia #242, y que reabriría el
criterio de parada 1 (durabilidad sin `append_durably`/`replay` puro no
bastaría: haría falta un segundo tipo de registro con su propia limpieza al
liberar, o un mecanismo de expiración -ninguno de los dos existe hoy en el
repositorio). Se difiere a D2, con el límite documentado arriba.
