# ADR-048 — La capa que llama a las reglas también necesita su tabla exhaustiva de estados

- Estado: APROBADO
- Fecha: 2026-08-21
- Aprobación: la fusión de la PR por el propietario
- Contexto: §5 de `docs/implementation/DONDE_ESTAMOS_2026-08-21.md` (guardas 1 y 2)
- Relacionadas: ADR-045 (H-3), ADR-047 (registro de defectos), ADR-001 (disciplina de evidencia)

## Contexto y problema

Dos defectos, el mismo error, el mismo fichero:

- **H-3**: el corte por presupuesto no salía de `WAITING`. Sobrevivió a la
  batería completa, a dos revisores independientes y a **cinco** rondas de
  corrección, y entró en `main`.
- **H-7**: `resolver_fallo_tecnico`, la función hermana, tiene el mismo fallo.
  Sobrevivió además a la corrección de H-3.

La forma común, dicha una vez:

> Una función de política da por supuesto en qué estado está el trabajo, y sus
> pruebas solo la arrancan desde el estado feliz.

Y hay una asimetría que explica por qué se colaron. Una capa más abajo esto **no
puede** pasar: `tests/engine/test_work_item_transitions.py` recorre cada
operación del dominio contra cada estado —96 casillas— y añadir un estado nuevo
rompe la batería hasta que alguien rellene la casilla. Lo que no tenía esa tabla
era **la capa que llama a las reglas**. Ahí vivían los dos.

Un revisor lee lo que está escrito. Esto era **una ausencia**.

## Criterio de parada (escrito ANTES de decidir)

El mismo que se fijó para el registro de defectos, porque la exigencia del
propietario es la misma:

> Vale si, y solo si, **es determinista y no depende de ningún modelo** —su
> miedo declarado es que el sistema solo aguante mientras pague un modelo caro—
> y si, **reintroduciendo H-3 y H-7 por separado, la guarda nueva los caza ella
> sola**, sin apoyarse en las pruebas concretas que se escribieron para cada
> uno. Si necesita esas pruebas, no es una guarda: es un parche con otro nombre.

## Opciones consideradas

1. Añadir una prueba por cada defecto encontrado, según aparezcan.
2. Exigir un umbral de cobertura de pruebas.
3. Una tabla exhaustiva de la capa de política, análoga a la que ya existe una
   capa más abajo.

## Decisión

**La tercera**, con dos piezas:

**Guarda 1 — `tests/engine/test_politicas_por_estado.py`.** Cada función de
política contra cada estado del WorkItem, en ambos almacenes. La propiedad que
fija no es un detalle de cada política sino una invariante de todas:

> Ninguna política puede lanzar `IllegalTransitionError` desde ningún estado.

Una política **puede** decidir no hacer nada desde un estado —un aviso que llega
tarde sobre un trabajo ya entregado no tiene que escalar—, pero no puede
reventar: reventar deja el Run muerto y el WorkItem colgado sin que nadie se
entere. Es literalmente lo que hicieron H-3 y H-7.

**Guarda 2 — que ninguna operación se quede fuera de la tabla de abajo.** Las
operaciones con guarda de estado se leen del código con `ast`, no de una lista
escrita a mano: una lista a mano se desactualiza en silencio, que es el fallo que
esto viene a impedir. Se reconocen las dos formas que usa el dominio —
`self._require(...)` y el `raise IllegalTransitionError` escrito directamente —
porque `change_scope` y `reprioritize` usan la segunda y por eso nadie notó que
faltaban.

Y una tercera pieza que no estaba en la propuesta: `ESTADOS_EN_CURSO`. El
conjunto `{ACTIVE, WAITING}` se llamaba `BUDGET_CUTOFF_ESCALABLE_STATES`, por el
primer sitio donde hizo falta. Con dos políticas usándolo, pasa a llamarse por lo
que **es**: los dos estados en que puede haber un Run vivo.

## Comprobación que la sostiene

### La condición del criterio de parada: la guarda los caza SOLA

Se reintrodujeron los dos defectos por separado, en el sitio real de cada uno, y
se ejecutó **solo** el fichero de la guarda nueva:

```
MUTACION «reintroducir H-7 (quitar el paso WAITING->ACTIVE)»        -> 2 failed, 31 passed
MUTACION «reintroducir H-3 en los dos almacenes»                    -> 2 failed, 31 passed
```

Los caza sin ayuda de las pruebas escritas para cada defecto. Ese era el listón.

### H-7, reproducido antes de arreglarlo

```
estado mientras el Worker externo corre: waiting
EXCEPCION: IllegalTransitionError - cannot fail_safely WorkItem while in state WAITING
  WorkItem despues: waiting
  Run despues     : finished
```

Peor que H-3 en un punto: el Run **sí** queda muerto, así que el trabajo espera
para siempre a algo que ya no existe.

### La guarda encontró un defecto el día que se estrenó, y mayor de lo previsto

La auditoría del 20-08 señaló **dos** operaciones fuera de la tabla. La guarda
encontró **ocho**:

```
AssertionError: operaciones del dominio con guarda de estado que nadie prueba
contra cada estado: ['approve_review', 'begin_check', 'begin_execution',
'begin_review', 'request_repair', 'resume_after_repair']
```

Las seis nuevas se leen como «operaciones de fase» y por eso pasaron
desapercibidas, pero llevan `_require(ACTIVE)` **además** de la guarda de fase.
Queda como defecto **H-8** (incidencia #219) en el registro de ADR-047, no
tapado dentro de este cambio: meterlas en la tabla exige que la tabla modele
estado **y** fase, y eso es diseño.

### No depende de ningún modelo

Es una tabla y un bucle, más un `ast.parse`. No razona, no invoca nada, no sale a
la red. Sigue funcionando igual con un modelo pequeño y barato.

### Validaciones obligatorias

```
uv run ruff format --check .   -> 432 files already formatted
uv run ruff check .            -> All checks passed!
uv run mypy src tests          -> Success: no issues found in 413 source files
uv run pytest -q               -> 2897 passed, 6 skipped
git diff --check               -> limpio
```

## Consecuencias

- La clase de defecto que costó H-3 y H-7 deja de poder llegar a `main` en
  silencio: cualquier política que reviente desde cualquier estado rompe la
  batería.
- Una operación **nueva** con guarda de estado que nazca fuera de la tabla
  también la rompe.
- El hueco de las ocho operaciones queda **declarado y vigilado** en vez de
  descubierto por casualidad: hay una prueba que falla si alguien las mete en la
  tabla y se olvida de quitarlas de la lista de excepciones.
- Coste: quien añada una política nueva tiene que declararla en la tabla. Es
  deliberado — ese es el momento en que uno se pregunta qué pasa desde cada
  estado, que es la pregunta que nadie se hizo.

## Alternativas descartadas y por qué

**Una prueba por defecto encontrado.** Es lo que se hizo con H-3, y no impidió
H-7 en el fichero de al lado. Una prueba por síntoma no cubre la familia.

**Exigir un umbral de cobertura.** Descartada **con la medición**, no por
intuición. Sobre el árbol exacto anterior al arreglo de H-3 la cobertura daba
`93%` — la misma cifra que después— y la línea del defecto figuraba cubierta al
100 %, ejecutada siempre desde el estado bueno. La cobertura cuenta **líneas
ejecutadas**, no **estados visitados**. Un umbral habría dado una sensación de
seguridad exactamente igual de falsa.

**Meter las ocho operaciones en la tabla ahora.** Sería cerrar el hallazgo el
mismo día, y resulta tentador. Se descarta porque la tabla actual modela estados
y esas seis exigen estado y fase a la vez: hacerlo de tapadillo dentro de otro
cambio es la clase de atajo que este repositorio evita. Va en la incidencia #219.
