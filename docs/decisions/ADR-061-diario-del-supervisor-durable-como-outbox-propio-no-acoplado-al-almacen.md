# ADR-061 — Diario del supervisor durable como outbox propio, no acoplado al almacen

- Estado: APROBADO
- Fecha: 2026-08-21
- Aprobación: fusión de la PR de la incidencia #238 por el propietario
- Enmendado: ADR-082 supera la premisa de un disco que sobrevive al proceso: dentro de GitHub Actions los dos diarios solo son durables si se versionan en el repositorio (decisión I4, #270)

## Contexto y problema

H-10 (`docs/audits/registro_defectos.yml`, incidencia #236) es el defecto que
ADR-057 registró a propósito en vez de arreglar a destiempo: la marca de
«escalada pendiente de notificar» de `SupervisorJournal`
(`ports/supervisor_journal.py`) solo vive en
`InMemorySupervisorJournal` — si el proceso muere entre escalar y notificar,
la marca desaparece, y con ella la garantía (CODEX-004) de que un fallo de
notificación no pierde ni duplica el aviso al propietario.

La adenda de ADR-057 (21-08-2026) ya dejó constancia de que satisfacerlo exige
uno de dos diseños sin precedente en el repositorio, y que los dos reabren la
decisión que ese ADR difirió:

**(a)** fusionar la durabilidad con el diario de sucesos de
`DurableWorkEngineStore` (`adapters/durable/store.py`), acoplando dos puertos
hoy separados a propósito — la propia `SupervisionEpisode`
(`domain/supervision.py`) documenta por qué: ese diario modela transiciones
tipadas de `WorkItem`/`Run`, y no tiene sitio para el texto libre de "qué
observó y por qué decidió" que un episodio de supervisión necesita.

**(b)** un *outbox* propio, con su propio ciclo de vida — que no existe en
ningún sitio del repositorio.

Este ADR toma esa decisión ahora que C1 (incidencia #232, PR #233) y A2
(`DurableWorkEngineStore`, ADR-026, ADR-029) ya están fusionadas, entra dentro
del alcance permitido de la incidencia #238 y va deliberadamente **delante**
de C2: el día que C2 cablee el supervisor de verdad, este defecto pasa de
inalcanzable a alcanzable en el mismo commit.

## Criterio de parada (escrito ANTES de decidir)

Antes de mirar código de más, el criterio que decide entre (a) y (b):

1. Si satisfacer la durabilidad con (b) exigiera inventar mecanismo de
   escritura propio —abrir el fichero, hacer `fsync`, calcular checksum,
   reproducir la cola— en vez de reutilizar sin modificar el módulo genérico
   ya probado `sirius_engine/adapters/durable/journal.py`
   (`append_durably`/`replay`, con su propia matriz punto-de-muerte en
   `tests/engine/test_durable_journal.py`), se descarta (b) y se elige (a):
   el coste real que el defecto de ADR-057 atribuye a (b) — "construir
   concurrencia y durabilidad desde cero" — se materializaría de verdad, y ya
   no sería defendible frente a reutilizar lo que (a) ya trae de fábrica.
2. Si (a) exigiera cambiar el contrato de `WorkEngineStore` de forma que
   rompiera a sus llamadores actuales, se descarta (a) sin más — es una
   condición de parada explícita de la incidencia #238, no solo de este ADR.
3. La prueba por mutación (ADR-001 §3, exigida por la incidencia: no
   persistir la marca, quitar la correlación con `run_id`, reenviar el aviso
   al reabrir) debe hacer caer la prueba correspondiente. Si alguna mutación
   no tumba ninguna prueba, la prueba se corrige antes de seguir — no se
   declara la decisión verificada sin eso.

## Opciones consideradas

**(a) Fusionar con el diario de `DurableWorkEngineStore`.**
Gana atomicidad real con `escalate_work_item` (una sola escritura, un solo
`fsync`, sin ventana entre "escalar" y "marcar pendiente"). Cuesta acoplar dos
puertos que hoy son independientes a propósito: `SupervisorJournal` pasaría a
depender del formato interno de eventos del motor (`domain.events.Event`,
`AggregateType`), y cualquier llamador de `WorkEngineStore` que no supervise
—hoy todos, según la propia adenda de ADR-057— arrastraría sin necesidad la
maquinaria de supervisión. Además el propio dominio (`SupervisionEpisode`)
documenta por qué esa fusión es semánticamente forzada: el diario de eventos
modela transiciones tipadas, no el texto libre de una decisión de política.

**(b) Un outbox propio, reutilizando `durable/journal.py`.** Mantiene los
puertos separados, tal como `ports/supervisor_journal.py` ya documenta como
decisión deliberada de C1. El módulo `durable/journal.py` es genérico —JSON
Lines con `fsync` + checksum SHA-256 por registro, idempotencia de
reproducción, recuperación de cola truncada— y **no está acoplado a
`WorkEngineStore`**: lo usa `DurableWorkEngineStore`, pero no lo exige. Un
segundo diario, en su propio fichero, con sus propios tipos de registro,
reutiliza exactamente ese módulo sin tocarlo ni duplicar su lógica de
escritura/recuperación. El coste que la adenda de ADR-057 atribuye a esta vía
—"construir concurrencia y durabilidad desde cero"— **no se materializa**:
lo único nuevo es la serialización de `SupervisionEpisode` y de la marca de
escalada pendiente a JSON, no el mecanismo de persistencia en sí.

La atomicidad que (a) ganaría de más —una sola escritura para "escalar +
marcar pendiente"— no la exige ningún requisito de la incidencia: el orden ya
vigente en `supervisor.py._escalar` (marcar pendiente *después* de que
`escalate_work_item` confirme, *antes* de notificar) tolera perfectamente que
sean dos escrituras durables independientes en dos diarios distintos — cada
una atómica por separado (ADR-026), y su composición ya la ejercitan las
pruebas CODEX-004 y CODEX-001 en `test_supervisor.py`, ninguna de las cuales
depende de que ambas mutaciones compartan una sola transacción de fichero.

## Decisión

Se elige **(b): un outbox propio**, implementado como
`sirius_engine.adapters.durable.supervisor_journal.DurableSupervisorJournal`,
sobre un fichero JSON Lines independiente del diario del `WorkEngineStore`,
reutilizando sin modificar `append_durably`/`replay` de
`adapters/durable/journal.py`.

Tres tipos de registro, todos con el mismo formato de línea que ya usa
`journal.py` (checksum SHA-256, `fsync` de fichero y de directorio en cada
anexo):

- `supervision_episode_recorded`: el episodio completo (mismos campos que
  `SupervisionEpisode`), append-only.
- `pending_escalation_recorded`: `work_id` + `run_id` que dejó la escalada
  pendiente de notificar (CODEX-001).
- `pending_escalation_cleared`: `work_id` cuya marca se limpió tras entregar
  la notificación.

Al abrir (`__init__`), se reproduce el diario una sola vez y se reconstruye el
índice en memoria (`_episodios`, `_run_ids_atendidos`,
`_escaladas_pendientes`) aplicando los registros en orden — el último
`pending_escalation_recorded`/`pending_escalation_cleared` para un `work_id`
dado gana, que es exactamente lo que hace correlacionable y sobreviviente a
un reinicio la marca que CODEX-001 exigió en C1.

`InMemorySupervisorJournal` no cambia: sigue siendo la implementación que usan
las pruebas rápidas de `tests/engine/test_supervisor.py` (H10-P5).

## Comprobación que la sostiene

- El criterio de parada 1 se cumple: `DurableSupervisorJournal` importa
  `append_durably`/`replay` de `adapters/durable/journal.py` sin modificar ese
  módulo ni reimplementar `fsync`/checksum/recuperación de cola — ver
  `git diff --stat -- src/sirius_engine/adapters/durable/journal.py`, vacío.
- El criterio de parada 2 no aplica: no se tocó `WorkEngineStore`.
- El criterio de parada 3 (prueba por mutación) y las cinco pruebas de
  terminado (H10-P1 a H10-P5) están en
  `tests/engine/test_durable_supervisor_journal.py`; las tres mutaciones
  exigidas hacen caer exactamente la prueba prevista antes de revertirse.
  Resultado de la suite completa:

  ```
  $ uv run pytest tests/engine/test_durable_supervisor_journal.py tests/engine/test_supervisor.py -q
  ```

  (ver el resumen de la ejecución en la descripción de la PR de la
  incidencia #238; se omite pegar aquí la salida completa por brevedad, pero
  el comando es reproducible tal cual).

## Consecuencias

- `SupervisorJournal` sigue sin conocer nada de `WorkEngineStore`, y
  viceversa: la separación deliberada de C1 se conserva, no se abre una
  dependencia nueva entre los dos puertos.
- El proceso que use el supervisor en producción (C2, futuro) deberá abrir
  **dos** ficheros durables distintos —el del `WorkEngineStore` y el del
  `SupervisorJournal`— en vez de uno. Es el coste que (b) acepta a cambio de
  no acoplar los puertos; queda escrito aquí para que C2 no lo descubra tarde.
- No hay atomicidad entre "escalar en el almacén" y "marcar pendiente en el
  diario de supervisión": son dos escrituras durables independientes. Si el
  proceso muere entre una y otra, el `WorkItem` queda `NEEDS_DECISION` sin
  marca de correlación — el mismo escenario que ya cubre
  `test_codex001_needs_decision_por_otra_causa_no_se_trata_como_notificacion_fallida`
  (se difiere, no se notifica sin correlación), así que no es un estado nuevo
  sin manejar, solo uno que ya tenía prueba antes de esta incidencia.

## Alternativas descartadas y por qué

**(a) Fusionar con el diario de `DurableWorkEngineStore`.** Descartada por lo
que cuesta, no por lo que gana: acopla dos puertos que C1 separó a propósito,
y la separación no era un accidente — es la que permite que `SupervisorJournal`
no tenga sitio para el texto libre de una decisión de política mientras el
diario de eventos solo modela transiciones tipadas (razón que el propio
domino, `SupervisionEpisode`, ya documentaba antes de este ADR). Se pierde,
frente a (a): la atomicidad de una sola escritura para "escalar + marcar
pendiente" — pero ningún requisito de la incidencia #238 la exige, y el orden
ya vigente en `_escalar` (marcar ANTES de notificar) tolera dos escrituras
durables independientes sin dejar una ventana sin cubrir por las pruebas
CODEX-001/CODEX-004 ya existentes.
