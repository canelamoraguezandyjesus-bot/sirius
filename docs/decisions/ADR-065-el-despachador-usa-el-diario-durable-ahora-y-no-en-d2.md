# ADR-065 — El despachador usa el diario durable ahora y no en D2

- Estado: APROBADO
- Fecha: 2026-08-22
- Aprobación: la fusión de la PR #252 por el propietario
- Nota de arranque de esta rama: este ADR. **Se publica después del primer
  commit, y eso es un incumplimiento** — ver «Sobre el orden» al final. No se
  disimula fechándolo antes.

## Contexto y problema

ADR-064 (H-11, incidencia #242) construyó `DurableDispatchJournal` y **dejó
escrito que cablearlo en producción quedaba para D2**, por analogía con lo que
ADR-061 hizo con el diario del supervisor. La PR #248 lo repitió en su cuerpo:
«No se toca `dispatcher.py` ni `dispatch_cli.py`: cablear el adaptador durable
en producción queda para D2».

Esta decisión **levanta ese aplazamiento**. No es ejecución de ADR-064: lo
contradice en su parte diferida, y por eso necesita ADR propio.

## Qué evidencia cambió

El aplazamiento se apoyaba en que el hueco no costaba nada todavía. Al diseñar
el verificador de proyección de D1 (incidencia #250) se midió que sí cuesta, y
en dos sitios:

1. **Repetir una orden creaba una segunda incidencia del mismo trabajo.** El
   único camino de producción que despacha, `sirius-despachar`, construía
   `InMemoryDispatchJournal()` cableado, uno nuevo por invocación: cada
   ejecución nacía sin memoria de lo ya despachado. Y de una incidencia cuelga
   un ciclo entero —implementador, Quality, dos revisores— sobre trabajo que ya
   estaba en marcha.
2. **Sin episodio persistido no hay clave de unión motor↔incidencia entre
   ejecuciones.** El verificador de proyección que D1 necesita sale
   `NO_COMPARABLE` siempre, y el reloj de los 7 días que el contrato §11.2 exige
   antes de conmutar la canonicidad de una clase **no arranca nunca**.

El punto (2) es el que rompe el argumento original: el aplazamiento decía «hasta
D2», pero D1 va antes que D2 y lo necesita. La analogía con ADR-061 no se
sostenía porque el diario del supervisor no es clave de unión de nada.

## Criterio de parada

Si cablear el adaptador exigiera (a) cambiar `dispatcher.py` o el contrato del
puerto `DispatchJournal`, (b) ampliar los verbos de escritura en GitHub, o (c)
tocar `.github/**`, se para y se pregunta: eso sería rediseñar C2, no
conectarlo. Dos rondas de revisión con defectos de la misma familia paran la
implementación para buscar la raíz.

Ninguna de las tres se activó: el cambio vive entero en `dispatch_cli.py`.

## Decisión

**1. El diario del despachador es durable al ejecutar de verdad.** Solo con
`--ejecutar`. El ensayo sigue en memoria a propósito: no debe dejar rastro, y
esa propiedad ya estaba fijada por ADR-063.

**2. Vive junto al del motor, como hermano** (`<diario>-despacho.jsonl`), y no
dentro de él. Mismo criterio que separó el del supervisor (ADR-061) y el del
despachador (ADR-064): el diario de eventos del `WorkEngineStore` modela
transiciones tipadas de `WorkItem`/`Run` y no tiene sitio para «qué orden» ni
«qué incidencia» nació de una activación.

**3. Repetir la misma orden es idempotente, no un error.** Apareció al escribir
la prueba: la guarda del almacén saltaba **antes** que el diario. Como el
`work_id` se deriva del instante de la orden, dos invocaciones seguidas
comparten uno, y `create_work_item` levantaba `DuplicateIdError` — la persona
veía una traza en vez de «ya estaba despachado». Ahora, si el trabajo ya existe
se reutiliza y se deja que el despachador consulte su diario, que es quien sabe
si hubo activación.

## Comprobación que lo sostiene

Prueba por mutación, vista fallar antes de darla por buena (ADR-001):

```
$ # con `journal = InMemoryDispatchJournal()` en lugar del durable
$ uv run pytest tests/engine/test_dispatch_cli.py -q -k "segunda_incidencia"
FAILED test_repetir_la_misma_orden_no_crea_una_segunda_incidencia
1 failed, 7 deselected

$ # restaurado el diario durable
$ uv run pytest tests/engine/test_dispatch_cli.py -q -k "segunda_incidencia"
1 passed, 7 deselected
```

Validaciones obligatorias, todas en verde sobre el árbol completo:

```
$ uv run ruff format --check .      474 files already formatted
$ uv run ruff check .               All checks passed!
$ uv run mypy src tests             Success: no issues found in 451 source files
$ uv run pytest -q                  3288 passed, 6 skipped in 315.58s
```

## Lo que esto NO garantiza

- **No cierra H-13.** Dos procesos *solapados* que abren el diario antes de que
  ninguno grabe siguen reservando los dos y crearían dos incidencias. Es el
  límite que ADR-064 aceptó y difirió a D2, y sigue abierto a propósito: cerrarlo
  exige persistir la reserva en curso o un bloqueo de sistema operativo, que es
  otra decisión.
- **No desbloquea D1.** Cierra uno de los cuatro bloqueos que la incidencia #250
  registró (H-B). Siguen abiertos la especificación derogada del plan (H-A), el
  subconjunto comparable con agujeros (H-C) y las cuatro falsas alarmas
  estructurales (H-D).
- **No dice quién invoca el comando.** Hoy lo invoca una persona; que lo invoque
  un proceso sigue siendo otra decisión, como ya dejó escrito ADR-063.

## Sobre el orden: este ADR llega tarde

ADR-001 exige la nota de arranque **antes del primer commit**. Aquí se escribió
después: el trabajo se abordó como si fuera ejecución de H-11 —conectar un
adaptador ya construido— y solo al revisar la rama se vio que ADR-064 había
diferido explícitamente ese cableado, lo que convierte el trabajo en una
decisión y no en una tarea.

Queda escrito en vez de disimulado, porque el fallo tiene enseñanza: **lo que
distingue una ejecución de una decisión no es el tamaño del cambio, sino si
contradice algo ya escrito.** Tres líneas de cableado que levantan un
aplazamiento aprobado son una decisión; doscientas que aplican uno no lo son.
La comprobación barata que lo habría cazado antes de empezar: releer el ADR del
bloque del que sale el trabajo, buscando qué difirió.
