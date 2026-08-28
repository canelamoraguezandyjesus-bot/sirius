# Evidencia — H-27: la frontera WorkItem–Run

Fecha: 2026-08-28. Rama `h27-frontera-workitem-run`. Nota de arranque:
`arranque-h27-frontera-workitem-run.md` (las cuatro preguntas se responden
aquí, en su orden).

## Qué se construyó

- `prepare_run` exige padre existente (`UnknownWorkItemError`) y no terminal
  (`ParentNotInProgressError`), en los DOS stores (durable y memoria).
- `deliver_work_item` rechaza la entrega (`LiveRunsPreventDeliveryError`) si
  algún Run del WorkItem está en `LIVE_STATES` **o** arrastra el peligro de
  H-26 (`has_unconfirmed_cancellation`, que desde H-26 incluye
  LOST+UNCONFIRMED).
- Errores nuevos en `domain/errors.py`; ningún cambio en las máquinas locales.

## Las cuatro preguntas del arranque

**1. ¿Las pruebas nuevas se vieron FALLAR, en memoria Y durable, en las dos
direcciones?** Sí. Las cuatro pruebas nuevas de `test_cancellation.py`
(`test_h27_un_run_sin_padre_no_se_prepara`,
`test_h27_un_padre_terminal_no_acepta_intentos_nuevos`,
`test_h27_no_se_entrega_con_un_hijo_vivo`,
`test_h27_el_peligro_de_h26_tambien_impide_entregar`) se escribieron antes de
las guardas y fallaron en los dos parámetros del fixture `store`. Además, las
cuatro mutaciones de abajo caen con "1 failed, 1 passed": mutar SOLO el store
durable deja el parámetro de memoria en verde, lo que demuestra que cada
backend está guardado por separado (no comparten la guarda).

**2. ¿Un padre PAUSADO admite preparar?** Sí — la guarda es
`estado in TERMINAL_STATES`, no `estado not in ESTADOS_EN_CURSO`. Decidido con
las definiciones delante (`domain/work_item.py`):
`TERMINAL_STATES = {CANCELLED, DELIVERED}` y
`ESTADOS_EN_CURSO = {ACTIVE, WAITING}`. Razones: (a) la combinación que el
informe declara imposible es la del padre TERMINAL con hijos — un padre
pausado o planificado puede volver a estar en curso, así que un intento suyo
no es historia imposible, es historia temprana; (b) las capas que ACTÚAN ya
exigen `ESTADOS_EN_CURSO` antes de crear Runs de reemplazo (el supervisor en
`_reactivar_o_sustituir`, H-22), así que endurecer aquí sería política nueva
no pedida por el informe, no una guarda de consistencia.

**3. ¿La entrega con el peligro de H-26 activo se rechaza?** Sí:
`test_h27_el_peligro_de_h26_tambien_impide_entregar` construye el
LOST+UNCONFIRMED de H-26 y la entrega revienta; la mutación M4 (ignorar
`has_unconfirmed_cancellation` en la entrega) la hace caer dejando en verde la
de hijo vivo — la cláusula es load-bearing por sí sola.

**4. ¿El replay de historia existente sigue funcionando?** Sí. La fixture de
`test_journal_replay` que el informe señaló (entregaba WI-1 y DESPUÉS le creaba
Runs; cancelaba WI-2 y después le nacía RUN-4) se REORDENÓ a la secuencia
válida —los intentos viven durante EJECUTAR y terminan antes de entregar—
conservando la misma variedad de operaciones; los 8 tests de replay pasan. La
capacidad de leer historia no cambió: el replay sigue siendo una pasada sobre
instantáneas, sin guardas.

## Consecuencias en pruebas existentes (criterio de parada (a) del arranque)

22 pruebas del motor construían Runs sin padre o entregaban con hijos vivos.
Se trajeron aquí ANTES de tocarlas y se decidió con cada una delante:

- `conftest.make_run` ahora crea y activa el padre si no existe (la mayoría de
  las 22 solo necesitaban un padre real).
- `test_worker_ref._preparar_run_durable` crea y activa WI-0001.
- `test_politicas_por_estado._delivered` cierra el Run (`succeed_run`) antes
  de las fases y la entrega — era exactamente la combinación inválida.
- `test_h22_..._entregado` (supervisor): el Run se pierde EN EL ALMACÉN antes
  de entregar — tras H-27 es el único orden posible, y el supervisor sigue
  midiendo lo mismo (padre DELIVERED ⇒ diferir, no resucitar).
- Los tres tests de Run ajeno (C1-P3) ya no pueden fabricarse por
  `prepare_run` — cerrarles esa puerta ES H-27. El vector que queda es la
  historia previa: un diario escrito antes de la frontera o compartido con
  otro sistema. `test_c1_p3...` y `test_mutacion_quitar_la_comprobacion...`
  construyen ahora ese diario legacy con las piezas del propio adapter
  (`append_durably` + `run_to_dict`, un registro con el Run ya RUNNING) y
  quedan durable-only: el backend de memoria nace vacío y solo se llena por
  la puerta recién cerrada, no puede tener historia legacy.
  `test_run_gobernado_..._directamente` construye el Run de dominio a pelo —
  el caso literal del docstring de `_run_gobernado_por_el_motor` ("fabricado
  fuera del almacén"). La defensa en profundidad del supervisor sigue medida:
  `retry_run` NO consulta al padre, así que sin la comprobación de propiedad
  el supervisor todavía pariría Runs bajo WorkItems inexistentes (la mutación
  lo demuestra, como antes).

## Mutaciones (ADR-001 §3), todas vistas caer y revertidas

| Mutación (store durable) | Resultado |
| --- | --- |
| M1: `padre is None` deja de rechazar | CAE (`..._sin_padre_no_se_prepara[durable]`) |
| M2: padre terminal acepta hijos | CAE (`..._padre_terminal...[durable]`) |
| M3: entregar ignora hijos vivos | CAE (`..._hijo_vivo[durable]`) |
| M4: entregar ignora el peligro de H-26 | CAE, y `..._hijo_vivo` sigue verde (M4 ≠ M3) |

## Rondas

Ronda 1: guardas + 4 pruebas nuevas → 22 existentes en rojo (la deuda de
fixtures que el propio informe nombró) → resueltas como arriba. Ronda 2: el
guardián del registro exigió cerrar H-26/H-29/H-31 (arreglos ya en main) →
cerrados con sus commits de fusión, byte a byte idénticos a los de la rama de
H-30 para que la segunda fusión autorresuelva. Familias distintas: no aplica
la regla de parar.

## Estado final

`tests/engine`: 965 en verde (1 skip preexistente). Registro de defectos: 40
en verde. Suite completa, ruff, format y mypy: en el resumen de la PR.
