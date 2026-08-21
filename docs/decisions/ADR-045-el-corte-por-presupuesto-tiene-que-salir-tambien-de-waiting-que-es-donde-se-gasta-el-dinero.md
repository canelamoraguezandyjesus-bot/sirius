# ADR-045 — El corte por presupuesto tiene que salir también de WAITING, que es donde se gasta el dinero

- Estado: APROBADO
- Fecha: 2026-08-21
- Aprobación: la fusión de la PR de A5 (incidencia #206 / PR #207) por el propietario
- Contexto: hallazgo **H-3** de `docs/audits/DEFECTOS_ENCONTRADOS_2026-08-20.md`
- Relacionadas: ADR-019 (el motor posee el estado), ADR-043 (gobierno previo al primer Worker externo), ADR-001 (disciplina de evidencia)

## Contexto y problema

A5 existe para una garantía: **al agotarse el presupuesto, se corta**. La
incidencia #206 lo escribe como salvaguarda —«no dejar ningún camino en que el
presupuesto se agote y el Run continúe»— y la arquitectura §10 lo recoge como
causa 2 de `NEEDS_DECISION`, «incluye agotar el presupuesto del WorkItem»,
**sin condicionarlo al estado**.

No cortaba. Fallaba justo en el caso normal.

`escalate()` exige `ACTIVE` (`domain/work_item.py`), pero un Worker asíncrono
deja el WorkItem en `WAITING` (`dispatch_work_item_async`, arquitectura §3.2), y
`WAITING` es **exactamente el estado en el que hay un proceso externo corriendo
y gastando**. Al agotarse el presupuesto ahí, el corte lanzaba
`IllegalTransitionError`: no escalaba, no notificaba, y el `Budget` actualizado
se perdía con la excepción, rompiendo una promesa explícita del docstring de
`registrar_gasto` («el nuevo valor… se devuelve siempre… tanto si corta como si
no»).

El defecto sobrevivió a dos revisores independientes y a cinco rondas de
corrección, y la incidencia llegó a `sirius:ready-for-merge` con él dentro.

## Criterio de parada (escrito ANTES de decidir)

El criterio no lo puso esta sesión: lo puso la auditoría que encontró el
defecto, antes de que nadie escribiera una línea de arreglo, y aquí se adopta
tal cual. `DEFECTOS_ENCONTRADOS_2026-08-20.md` §H-3 lista lo que el arreglo
tiene que satisfacer:

1. cortar y escalar **desde cualquier estado no terminal**, no solo `ACTIVE`;
2. no dejar estado inconsistente;
3. el `Budget` actualizado **nunca** se pierde;
4. decidir **explícitamente** qué pasa en estado terminal;
5. prueba vista fallar antes de arreglar (ADR-001).

Y se le añadió, antes de tocar nada, la regla de las dos rondas de ADR-001: **si
aparecía un segundo defecto de la misma familia, parar y atacar la raíz en vez
de parchear uno a uno**. Apareció. Ver «Comprobación».

## Opciones consideradas

1. **Añadir una arista `WAITING → NEEDS_DECISION` al dominio.** Cambia la
   máquina de estados aprobada de §3.2.
2. **Reutilizar `observe_work_item_external_fact`** (`WAITING → ACTIVE`) y
   escalar después.
3. **Usar la arista existente `WAITING → ACTIVE`, pero anexándola con un nombre
   de suceso propio**, y escalar después.

## Decisión

**La tercera.** El corte, tras cancelar los Runs vivos:

- si el WorkItem ya está en `NEEDS_DECISION`, lo devuelve tal cual (sigue siendo
  reanudable, como lo dejó la ronda 3);
- si está en `WAITING`, lo devuelve a `ACTIVE` por la arista que el diagrama
  **ya tiene**, anexando `work_item_budget_cutoff_stopped_waiting`, y escala;
- si está en cualquier otro estado —`PLANNED`, `PAUSED`, `FAILED_SAFELY` o
  terminal— **no escala y no lanza**: los Runs vivos quedan cancelados, el
  presupuesto actualizado se devuelve, y no se inventa una escalada que nadie
  puede resolver. Esto responde al punto 4 del criterio de parada, que pedía
  decidirlo explícitamente.

Los estados desde los que el corte puede escalar quedan **nombrados** en el
dominio, no repartidos por los adaptadores:

```python
BUDGET_CUTOFF_ESCALABLE_STATES = frozenset({WorkItemState.ACTIVE, WorkItemState.WAITING})
```

**No se añade ninguna arista nueva al diagrama de §3.2.** `WAITING → ACTIVE` y
`ACTIVE → NEEDS_DECISION` ya existen las dos; lo que faltaba era recorrerlas. Por
eso esta decisión no enmienda la arquitectura, que además A5 tiene prohibido
tocar.

El nombre de suceso propio es la diferencia con la opción 2: anexar
`work_item_observed_external_fact` habría dejado en el diario la afirmación de
que se observó un hecho externo, que es **falsa**. El WorkItem deja de esperar
porque acabamos de cancelar aquello que esperaba.

## Comprobación que la sostiene

### El defecto, reproducido sobre el head vivo de A5

Sobre `3f16c3b` —el head que tenía la etiqueta `sirius:ready-for-merge`—, con
`uv run python`:

```
estado mientras el Worker corre: waiting
EXCEPCION: IllegalTransitionError - cannot escalate WorkItem while in state WAITING
  WorkItem despues : waiting
  Run despues      : running
```

### Por qué sobrevivió a dos revisores y cinco rondas

Las siete pruebas de gobierno **parten todas de `ACTIVE`**:

```
$ grep -c "WAITING\|dispatch_work_item_async\|waiting" tests/engine/test_governance.py
0
```

El hueco no estaba en lo que el código hacía, sino en un estado que ninguna
prueba visitaba. Ningún revisor lee los estados que faltan; los lee quien mira
la máquina de estados, que es lo que hizo la auditoría.

### La regla de las dos rondas se activó: la misma familia, segunda aparición

Al arreglar la cascada apareció el mismo error en el camino de recuperación tras
caída, escrito por otra mano y en otro fichero:

```python
if work_item is None or work_item.estado is not work_item_ops.WorkItemState.ACTIVE:
    continue
```

Es decir: si el proceso moría a mitad de un corte con el WorkItem en `WAITING`
—el caso del dinero—, **reabrir el almacén se lo saltaba para siempre**. Dos
apariciones independientes obligan a nombrar la raíz en vez de parchear dos
sitios: *el corte por presupuesto se escribió suponiendo que el WorkItem está
`ACTIVE`, cuando el estado en que se gasta el dinero es `WAITING`*. De ahí que
el conjunto se declare una sola vez en el dominio y lo usen los tres puntos.

### Las tres mutaciones, sembradas y vistas fallar

| Mutación | ¿La caza? |
| --- | --- |
| Quitar el paso `WAITING → ACTIVE` del corte | sí — `test_agotar_el_presupuesto_desde_waiting_corta_y_escala` |
| Quitar la guarda de estado no escalable | sí — `test_un_coste_tardio_sobre_un_trabajo_ya_detenido_no_escala_ni_revienta` |
| Devolver la recuperación a mirar solo `ACTIVE` | sí — `test_reabrir_el_almacen_termina_un_corte_que_quedo_a_medias_en_waiting` |

Las dos primeras se comprobaron sobre **ambas** implementaciones del almacén
(memoria y durable), que es como está parametrizado ese fichero.

La primera prueba se escribió **antes** del arreglo y se la vio fallar en las
dos implementaciones:

```
FAILED test_agotar_el_presupuesto_desde_waiting_corta_y_escala[_make_in_memory_store]
FAILED test_agotar_el_presupuesto_desde_waiting_corta_y_escala[_make_durable_store]
```

### Validaciones obligatorias

```
uv run ruff format --check .   -> 430 files already formatted
uv run ruff check .            -> All checks passed!
uv run mypy src tests          -> Success: no issues found in 411 source files
uv run pytest -q               -> 2846 passed, 6 skipped
git diff --check               -> limpio
```

`mypy` cazó de paso que el nuevo suceso no estaba en la lista cerrada de tipos
de `domain/events.py`: el diario no admite un `kind` que nadie haya declarado, y
eso es una guarda, no un estorbo.

## Consecuencias

- La garantía principal de A5 pasa a cumplirse en el estado en que se gasta el
  dinero, que era el único en que no se cumplía.
- Una caída a mitad del corte con un Worker externo vivo ya no deja el trabajo
  esperando para siempre a un Run cancelado: reabrir el almacén lo termina.
- El diario gana un tipo de suceso, `work_item_budget_cutoff_stopped_waiting`,
  que dice por qué el WorkItem dejó de esperar. Un diario que miente sobre la
  causa es peor que uno que calle.
- Un coste que llega tarde sobre un trabajo ya detenido queda registrado sin
  escalar y **sin romper**.
- Queda escrito, para la próxima: **una prueba que solo visita el camino feliz
  de la máquina de estados no prueba la máquina de estados.** Es el hueco por el
  que se coló esto, y no lo cierra ningún revisor.

## Alternativas descartadas y por qué

**Añadir `WAITING → NEEDS_DECISION` al dominio.** Es la lectura más directa de
§10, pero enmienda el diagrama aprobado de §3.2 y A5 tiene prohibido modificar
la arquitectura. Y resulta innecesaria: el camino ya existe recorriendo dos
aristas dibujadas. Si algún día el diagrama se enmienda por otro motivo, esta
decisión no lo estorba.

**Reutilizar `observe_work_item_external_fact` tal cual.** Funciona y no cuesta
nada, y por eso estuvo a punto de elegirse. Se descartó por una sola razón, que
basta: dejaría escrito en el diario que se observó un hecho externo cuando lo
que ocurrió es que el motor canceló lo que se esperaba. El diario es la
evidencia de la que vive todo este método; un suceso con nombre falso la
envenena en el sitio exacto donde alguien irá a buscar por qué se paró un
trabajo caro.

**Escalar desde cualquier estado no terminal, incluidos `PAUSED` y
`FAILED_SAFELY`.** Es lo que pedía literalmente el punto 1 del criterio de
parada, y no se hizo. Escalar un trabajo ya pausado o ya fallado produce una
decisión que el propietario no puede tomar —no hay nada que reanudar— y añade
ruido a la única bandeja que tiene. Se cumple el espíritu del punto 1 —el corte
nunca revienta y el presupuesto nunca se pierde, salga de donde salga— y se
declina su letra, que es lo que el punto 4 autorizaba a decidir.
