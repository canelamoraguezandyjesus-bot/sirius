# ADR-053 — «No pude observar» es un valor del puerto, y el barrido no lo convierte en éxito

- Estado: APROBADO
- Fecha: 2026-08-21
- Aprobación: la fusión de la PR por el propietario
- Contexto: defecto H-2 del parte `docs/audits/DEFECTOS_ENCONTRADOS_2026-08-20.md`, incidencia #214
- Relacionadas: ADR-036 (una lectura caída no es una ausencia; misma familia, otro sitio),
  ADR-029 (barrido de recuperación de A2), ADR-034 (el espejo marca cada proyección),
  ADR-001 (disciplina de evidencia)

## Contexto y problema

`src/sirius_engine/recovery.py`, antes de esta rama:

```python
store.succeed_run(live.run_id, resultado=observation.resultado or {}, now=now)
```

`observation.resultado` es `Mapping[str, object] | None`. `None` significa «no
se pudo leer el resultado» y `{}` significa «se leyó, y el Worker no devolvió
campos». `or {}` las colapsaba en la misma escritura del diario.

Y el puerto no ofrecía forma de decir «no pude observar»: `RemoteRunStatus`
enumeraba `PENDING`, `SUCCEEDED`, `FAILED`, `LOST` y `CANCELLED`. Un observador
cuya lectura se cayera solo podía **mentir** (`SUCCEEDED`), **inventar**
(`FAILED`/`LOST`) o **callar** (`PENDING`, que afirma que el Run sigue vivo).

No es una lectura del código: se reprodujo ejecutando, contra el almacén en
memoria, con un observador que dice `SUCCEEDED` y `resultado=None`:

```
$ uv run python scratchpad/repro_h2.py
barrido            : RecoverySweepResult(reconciled_run_ids=('RUN-0001',), released_work_item_ids=('WI-0001',))
Run.estado         : finished
Run.desenlace      : succeeded
Run.resultado      : {}
WorkItem.estado    : active
eventos del Run    : ['run_prepared', 'run_dispatched', 'run_confirmed_running', 'run_succeeded']

estados del puerto : ['PENDING', 'SUCCEEDED', 'FAILED', 'LOST', 'CANCELLED']
```

Un fallo de lectura quedó escrito en el diario como `run_succeeded` con
resultado vacío, y además liberó el `WorkItem` de `WAITING` a `ACTIVE` como si
el paso hubiera entregado algo.

Es **la familia que ADR-036 ya cerró para el espejo** —«una lectura caída no es
una ausencia»— reaparecida en el barrido de recuperación, que es el único camino
por el que el resultado real de un Worker llega al diario. Hoy es latente porque
la única implementación de `RunWorldObserver` es un doble de pruebas; por eso es
barato ahora y caro después: cuando C1 traiga el observador real, un 502 se
convertirá en «este trabajo salió bien y no entregó nada», y eso queda en el
diario, que es append-only.

## Criterio de parada (escrito ANTES de decidir)

Publicado en la incidencia #214 antes del primer commit
([comentario](https://github.com/canelamoraguezandyjesus-bot/sirius/issues/214#issuecomment-5366541864)),
junto con las otras tres preguntas de la nota de arranque:

> - **Paro y escalo si el arreglo exige tocar `WorkEngineStore`, el diario o el
>   dominio de `Run`** —un evento nuevo, una transición nueva o un estado
>   nuevo—. Esas transiciones las fijó A2 (ADR-029) y no se redecide de
>   madrugada por un defecto latente.
> - **Paro si aparece una segunda familia distinta** por el camino: la registro
>   y **no** la arreglo en este lote.
> - **Doy el arreglo por bueno solo si las dos mutaciones caen**: (a) volver a
>   `resultado or {}` tumba una prueba; (b) tratar el valor nuevo como `PENDING`
>   tumba otra.
> - **Y una condición anti-vacua**, la lección de ADR-036 («devolver 2 siempre»
>   habría pasado por arreglo): tiene que haber una prueba de que un `SUCCEEDED`
>   con resultado **legible y vacío** (`{}`) **sí** cierra como éxito.

Se cumplió sin activar ninguna parada: el arreglo no toca `WorkEngineStore`, ni
el diario, ni el dominio de `Run`, y no apareció ninguna familia nueva.

## Opciones consideradas

1. **Solo el barrido**: no cerrar como éxito si `resultado is None`, sin tocar el
   puerto. El observador sigue sin poder decir «no pude leer» cuando el fallo no
   es del resultado sino del estado entero.
2. **Solo el puerto**: añadir `UNKNOWN` y confiar en que los observadores lo
   usen. El `or {}` sigue vivo para el observador que reporte `SUCCEEDED` con un
   resultado ilegible.
3. **Las dos cosas**, y que el barrido trate igual ambas observaciones
   inutilizables: no escribir nada y reportarlas a quien lo invocó.
4. **Hacerlo imposible de expresar**: validar en `RunWorldObservation` que
   `SUCCEEDED` exige `resultado is not None`, o partir el tipo en una unión
   etiquetada por estado.

## Decisión

**La tercera.** Tres piezas:

### 1. El puerto puede decir «no pude observar»

`RemoteRunStatus.UNKNOWN`. La distinción que fija su docstring es la que importa:
todos los demás valores son **afirmaciones sobre el Run**; `UNKNOWN` es una
afirmación sobre **la lectura**. No es `PENDING` —que afirma que el Run sigue
vivo, que es justo lo que no se sabe— ni `LOST` —que afirma un aislamiento
demostrado—. Quien lo reporte explica en `diagnostico` por qué falló la lectura:
el barrido no puede saberlo.

`RunWorldObservation` documenta la otra mitad: `resultado=None` es «no se pudo
leer» y `{}` es «se leyó y no había campos».

### 2. Un desenlace sin resultado legible no cierra el Run

`_reconcile_run` devuelve ahora tres valores en vez de dos
(`RunSweepOutcome`), porque «no hice nada» escondía dos cosas que no se parecen:
*no había nada que hacer* y *no pude saber si lo había*. `SUCCEEDED` con
`resultado=None` y `UNKNOWN` caen ambos en `UNOBSERVED`, y `UNOBSERVED` **no
escribe en el diario**.

Por qué no escribe: el diario registra hechos del mundo, y un fallo de lectura no
lo es. Cerrar como `SUCCEEDED` afirmaría «terminó bien y no entregó nada»;
cerrarlo como `FAILED` o `LOST` afirmaría un desenlace que nadie observó. El Run
se queda vivo y la siguiente pasada vuelve a preguntar —«como mucho repite una
consulta», que es la promesa de §3.5—. Si el mundo nunca vuelve a ser legible,
su `deadline` acaba habilitando `LOST`, que es la vía que §3.3 ya prevé.

### 3. Pero no se queda callado

`RecoverySweepResult.unobserved_runs`: cada `Run` inobservable, con su
diagnóstico —el del observador si lo dio, y si no uno propio que dice lo único
que al barrido le consta—. No inventar un desenlace **y** no decir nada habría
sido el mismo defecto con otra cara: quien invoca el barrido es el único que
puede registrarlo o avisar, y ahora recibe el dato.

## Comprobación que la sostiene

Batería del fichero tocado (la completa la valida Quality en la PR):

```
$ uv run pytest tests/engine/test_recovery_sweep.py -q
32 passed in 0.13s
```

### La prueba, vista fallar antes del arreglo

Con los tipos nuevos ya en su sitio pero sin la lógica arreglada:

```
$ uv run pytest tests/engine/test_recovery_sweep.py -q -k "sin_resultado_legible or no_pudo_observar or no_es_sigue_vivo or inobservable or resultado_legible_y_vacio"
>       assert result.reconciled_run_ids == ()
E       AssertionError: assert ('RUN-0001',) == ()
E         Left contains one more item: 'RUN-0001'
...
E       AssertionError: RemoteRunStatus no manejado: <RemoteRunStatus.UNKNOWN: 'unknown'>
8 failed, 2 passed, 22 deselected in 0.43s
```

Las 2 que pasaban ya entonces son la prueba anti-vacua (`{}` sí cierra como
éxito): esa dirección nunca estuvo rota, y era importante comprobar que el
arreglo no la rompía.

### Prueba por mutación (ADR-001 §3)

Cuatro mutaciones sembradas, vistas fallar y revertidas —reescribiendo el texto
original guardado, nunca con `git checkout --`—:

| Mutación | Qué cayó |
| --- | --- |
| (a) volver a `resultado=observation.resultado or {}` | 2 — `test_barrido_no_cierra_como_exito_un_desenlace_sin_resultado_legible` |
| (b) tratar `UNKNOWN` como `PENDING` (`NOTHING_TO_DO`) | 6 — las tres pruebas de `UNKNOWN` |
| (c) el «arreglo falso»: no cerrar NUNCA como éxito | 12 — incluida `test_un_resultado_legible_y_vacio_si_cierra_el_run_como_exito` |
| (d) quedarse callado: no llenar `unobserved_runs` | 8 — las cuatro pruebas del reporte |

La (c) es la que importa más, y es la lección de ADR-036 aplicada aquí: sin ella,
«no cerrar nunca» habría pasado por arreglo, matando el único caso en que el
barrido puede concluir algo. La (d) mide la mitad que no es «no inventes»: es
«no te calles».

Validaciones completas: `ruff format --check`, `ruff check`, `mypy src tests` y
`pytest tests/engine/test_recovery_sweep.py`, todo en verde en el commit.

## Consecuencias

- Ningún fallo de lectura puede volver a quedar escrito en el diario como un
  éxito sin entrega. El diario es append-only: lo que entra mal no se corrige,
  se acumula.
- El observador real de C1 nace con vocabulario para decir la verdad, y su
  docstring le dice exactamente qué devolver cuando la consulta falla.
- **Un `Run` inobservable se queda vivo, y su `WorkItem` en `WAITING`.** Es
  deliberado y es un coste: si el mundo queda ilegible mucho tiempo, ese trabajo
  se atasca hasta que venza su `deadline`. Un atasco visible y reportado es
  preferible a un éxito falso e irreversible, pero conviene que quien invoque el
  barrido haga algo con `unobserved_runs` en vez de descartarlo.
- Las pruebas de éxito del barrido pasan a decir `resultado={}` explícitamente.
  No se debilitó ninguna: antes `None` y `{}` daban lo mismo, así que no
  expresaban cuál de las dos cosas querían decir; ahora lo dicen.

## Lo que esto NO garantiza

Escrito en la nota de arranque antes de empezar, no ahora:

- **No garantiza que el observador real diga la verdad.** Uno que reporte
  `SUCCEEDED` con `resultado={}` cuando en realidad no leyó nada sigue cerrando
  el Run como éxito vacío, y el barrido no puede distinguir eso de un Worker que
  terminó sin devolver campos. Lo que se consigue es que el observador tenga que
  **elegir** decirlo, en vez de que el barrido lo haga por él a partir de un
  `None`.
- **No cierra la familia ADR-036 en el resto del repositorio**: H-5 (incidencia
  #216) es el mismo patrón en `context_recall`, y esta rama no lo toca.
- **No añade plazo ni reintento propios** para un Run inobservable.

## Alternativas descartadas y por qué

**Arreglar solo el barrido, sin `UNKNOWN`.** Cubre el caso en que lo ilegible es
el resultado, y deja fuera el caso más común del mundo real: que sea ilegible el
estado entero. El observador seguiría teniendo que mentir para poder responder.

**Añadir solo `UNKNOWN`, sin tocar el `or {}`.** Deja el defecto exacto de H-2
vivo para cualquier observador que reporte `SUCCEEDED` con un resultado que no
pudo leer, que es literalmente el caso del que nació la incidencia.

**Hacerlo imposible: prohibir `SUCCEEDED` sin resultado al construir la
observación** (`__post_init__`, o una unión etiquetada por estado). Es la
respuesta a la cuarta pregunta de la nota de arranque, y la razón de no hacerlo
se publicó **antes** de decidirla: esa validación deja al barrido sin nada que
decidir, y con ello **la mutación (a) dejaría de ser detectable** —el arreglo del
barrido pasaría a ser código inalcanzable, y la prueba que lo mide, vacua—.
Prefiero la guarda donde se toma la decisión que se escribe en el diario,
sostenida por una prueba que la mide. Queda anotado como el siguiente paso
natural si C1 demuestra que los observadores se equivocan al construir la
observación: entonces el coste (código muerto en el barrido) estaría justificado
por un fallo real y no por una hipótesis.

**Cerrar el Run como `FAILED` cuando no se puede observar.** Inventa un
desenlace. Un Worker que terminó bien y cuyo resultado no se pudo leer no falló,
y `FAILED` en el diario dispara reintento y sustitución (§3.3) por algo que no
ocurrió.

**Registrar la no-observación en el diario** (un evento `run_unobserved`). Habría
exigido tocar `WorkEngineStore` y el conjunto de eventos, que es exactamente lo
que el criterio de parada prohibía en este lote. Además, el diario es el registro
de lo que le pasó al trabajo, no el registro de lo que le pasó al motor mientras
miraba; mezclarlos merece su propia decisión del propietario.
