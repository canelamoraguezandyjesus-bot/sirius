# ADR-058 — La fase entra en la tabla de estados como coordenada dependiente, y el eje fase gana su propia guarda

- Estado: APROBADO
- Fecha: 2026-08-21
- Aprobación: la fusión de la PR por el propietario
- Contexto: defecto **H-8**, incidencia #219; hueco declarado en ADR-048
- Relacionadas: ADR-048 (las dos guardas), ADR-047 (registro de defectos), ADR-036 («no pude» no es «no hay»), ADR-001 (disciplina de evidencia)

## Contexto y problema

`tests/engine/test_work_item_transitions.py` cruza cada operación del dominio
contra cada estado, y es la razón por la que la capa de reglas no tiene huecos.
Tenía uno: **ocho** operaciones de `WorkItem` con guarda de estado no estaban en
ella.

- `change_scope` y `reprioritize` rechazan los estados terminales, pero con un
  `raise IllegalTransitionError` escrito directamente en vez de `_require(...)`,
  y por eso nadie las vio.
- `begin_execution`, `begin_check`, `begin_review`, `approve_review`,
  `request_repair` y `resume_after_repair` se leen como «operaciones de fase» —
  y lo son— pero llevan `_require(ACTIVE)` **además** de la guarda de fase. Son
  operaciones de estado a todos los efectos.

ADR-048 las declaró y las dejó vigiladas con una lista, `FUERA_DE_LA_TABLA_HOY`,
en vez de cerrarlas el mismo día. El motivo que dio entonces es exactamente el
problema de este ADR:

> Meterlas en la tabla no es teclear ocho líneas. `test_work_item_transitions.py`
> modela **estados**; estas seis exigen estado **y** fase a la vez, así que la
> tabla necesita otra dimensión o una tabla hermana. Eso es diseño.

Y hay una trampa dentro de ese diseño que es la razón real de que esto no sea
mecánico. Una casilla nueva puede estar puesta y **no medir nada**: si el
WorkItem se prepara en una fase que la guarda de fase rechaza, la operación
lanza igual con `_require(ACTIVE)` y sin él. Solo cambia el tipo del error. Una
tabla llena de casillas así se ve exhaustiva, pasa la revisión, y no sostiene
nada. Es la misma familia que H-3 y H-7: **una prueba que solo arranca desde la
casilla feliz**, ahora en el eje de la fase.

## Criterio de parada (escrito ANTES de decidir)

Publicado en el [comentario de arranque de la incidencia #219](https://github.com/canelamoraguezandyjesus-bot/sirius/issues/219#issuecomment-5372785335)
antes de tocar ningún fichero. Literal:

> Vale si, y **solo** si:
>
> 1. `FUERA_DE_LA_TABLA_HOY` desaparece —la constante, la excepción que la
>    usaba y la prueba que la vigilaba— y la guarda 2 de ADR-048 pasa **sin
>    lista de excepciones**;
> 2. quitar la guarda de estado a **cada una de las ocho**, una a una, hace
>    fallar la batería de los dos ficheros. **Las ocho, no dos.** Dos es el
>    mínimo que me piden; ocho es lo que hace falta para poder afirmar que
>    ninguna casilla es vacua;
> 3. es determinista y no invoca ningún modelo: tablas, un bucle y un
>    `ast.parse`.
>
> Si alguna de las ocho tiene una mutación que **no** hace fallar nada, esa
> casilla es vacua. No la tapo con otra prueba: lo digo, y arreglo la casilla o
> explico por qué la mutación es equivalente.

## Opciones consideradas

1. **Cruce completo estado × fase × operación.** La tabla gana la fase como
   dimensión independiente: 8 × 6 × 20 = **960 casillas**.
2. **Tabla hermana sola**, solo para las operaciones de fase, dejando la tabla
   de estados como estaba y las ocho fuera de ella.
3. **La fase como coordenada *dependiente* de la tabla de estados, más una
   tabla hermana para el eje fase.**

## Decisión

**La tercera**, en tres piezas.

**Pieza 1 — la fase entra en la tabla A como coordenada dependiente.** Cada
operación declara en `FASE_DEL_ENSAYO` la fase en la que se la ensaya: la única
en la que su guarda de fase **no** salta. Las trece que no miran la fase se
ensayan en `PREPARAR`. Así la tabla A sigue preguntando una sola cosa —*¿desde
qué estados es legal esta operación?*— y la fase deja de ser un factor libre que
puede enmascarar la respuesta. La tabla pasa de 96 a **160 casillas** y las ocho
quedan cruzadas contra los ocho estados.

**Pieza 2 — la tabla B, para el eje fase.** `ACTIVE` fijo × 6 fases × las 7
operaciones con guarda de fase (las seis del ciclo más `deliver`) = **42
casillas**, con `LEGAL_PHASE_FROM` como oráculo escrito a mano de §3.4, igual
que `LEGAL_FROM` lo es de §3.2. Aquí lo que se exige es
`IllegalPhaseTransitionError`, no la de estado.

**Pieza 3 — la guarda hermana del eje fase**, en
`tests/engine/test_politicas_por_estado.py`. Esta no la pedía la incidencia, y
es la diferencia entre cerrar ocho defectos y cerrar la familia que los produce.
H-8 nació porque el eje **estado** tenía la guarda 2 de ADR-048 y el eje **fase**
no tenía ninguna: una operación con `_require_phase` podía nacer fuera de toda
tabla sin romper nada. Ahora `_metodos_del_dominio_con_guarda(...)` está
parametrizado y sirve a los dos ejes, y
`test_ninguna_operacion_de_fase_se_queda_fuera_de_la_tabla` cierra el segundo.

Con eso, `FUERA_DE_LA_TABLA_HOY` desaparece: la constante, la excepción del
`assert` y `test_la_lista_de_excepciones_no_se_queda_obsoleta`, que se queda sin
sujeto.

### El límite honesto, dicho aquí y fijado en una prueba

`PLANNED` y `DELIVERED` admiten **una sola fase** cada uno (`PREPARAR` y
`ENTREGAR`). En esos dos estados, una operación con guarda de fase no se puede
ensayar en la fase que su guarda acepta. Son **doce casillas** en las que lo que
separa «saltó la guarda de estado» de «saltó la guarda de fase» no es que la
operación fuera a tener éxito sin la guarda, sino únicamente **el tipo del
error**: `IllegalTransitionError` e `IllegalPhaseTransitionError` son hermanas,
ninguna subclase de la otra.

Eso es un supuesto de diseño del que dependen doce casillas, así que no se deja
implícito: `test_las_dos_guardas_lanzan_errores_que_no_se_confunden` lo fija, y
`test_las_casillas_sin_fase_preparable_son_exactamente_estas` enumera las doce
para que no crezcan sin que se note. Cada una de las siete operaciones con
guarda de fase conserva **al menos seis casillas plenas** en los otros seis
estados.

Y una distinción que este repositorio ya pagó una vez (ADR-036): que `PLANNED`
solo admita `PREPARAR` está sostenido por un **argumento**, escrito junto a
`FASE_UNICA` con sus tres patas y las pruebas que sostienen cada una, no por una
búsqueda exhaustiva de caminos. Es «no se puede», no «no supe»; pero es un
argumento, y se lee como tal.

## Comprobación que la sostiene

### Primero, verlo fallar

Quitando solo la excepción, sobre `origin/main` (`3f9773a`):

```
$ uv run pytest tests/engine/test_politicas_por_estado.py -q -k fuera_de_la_tabla
AssertionError: operaciones del dominio con guarda de estado que nadie prueba
contra cada estado: ['approve_review', 'begin_check', 'begin_execution',
'begin_review', 'change_scope', 'reprioritize', 'request_repair',
'resume_after_repair']
1 failed, 34 deselected in 0.08s
```

Ocho, las mismas ocho. La incidencia #219 solo listaba seis en su salida pegada
porque `change_scope` y `reprioritize` estaban explícitas en la lista.

### La condición 2 del criterio de parada: las quince mutaciones

Cada mutación siembra **una** guarda quitada y solo una; el original vive en una
variable de Python y se restaura siempre. Contra
`tests/engine/test_work_item_transitions.py` y
`tests/engine/test_politicas_por_estado.py`:

| Mutación | Resultado | Quién la caza |
| --- | --- | --- |
| `[estado]` quitar `_require(ACTIVE)` a `begin_execution` | 14 failed, 71 passed | `test_only_approved_operations_succeed_from_each_state` |
| `[estado]` … a `begin_check` | 14 failed, 71 passed | idem |
| `[estado]` … a `begin_review` | 14 failed, 71 passed | idem |
| `[estado]` … a `approve_review` | 14 failed, 71 passed | idem |
| `[estado]` … a `request_repair` | 14 failed, 71 passed | idem |
| `[estado]` … a `resume_after_repair` | 14 failed, 71 passed | idem |
| `[estado]` quitar la guarda de terminales a `change_scope` | 4 failed, 81 passed | idem |
| `[estado]` … a `reprioritize` | 4 failed, 81 passed | idem |
| `[fase]` quitar `_require_phase` a `begin_execution` | 11 failed, 74 passed | `test_only_approved_phase_operations_succeed_from_each_phase` |
| `[fase]` … a `begin_check` | 11 failed, 74 passed | idem |
| `[fase]` … a `begin_review` | 11 failed, 74 passed | idem |
| `[fase]` … a `approve_review` | 11 failed, 74 passed | idem |
| `[fase]` … a `request_repair` | 11 failed, 74 passed | idem |
| `[fase]` … a `resume_after_repair` | 11 failed, 74 passed | idem |
| `[fase]` … a `deliver` | 11 failed, 74 passed | idem |

```
MUTACIONES QUE NO HICIERON FALLAR NADA: ninguna
restaurado identico al original: True
```

### Las dos direcciones: ¿lo cazaba ya otra prueba?

Quince mutaciones cazadas no distinguen «mi tabla lo caza» de «ya lo cazaba
otro». Así que las mismas quince se corrieron contra **`tests/engine` entero**,
dos veces: con los ficheros de tabla de `origin/main` y con los de esta rama.
Resultado idéntico en las dos ejecuciones.

| Mutación | Batería ANTES | Batería DESPUÉS |
| --- | --- | --- |
| `estado/begin_execution` | ROJA | ROJA |
| `estado/begin_check` | **VERDE** | ROJA |
| `estado/begin_review` | **VERDE** | ROJA |
| `estado/approve_review` | **VERDE** | ROJA |
| `estado/request_repair` | **VERDE** | ROJA |
| `estado/resume_after_repair` | **VERDE** | ROJA |
| `estado/change_scope` | ROJA | ROJA |
| `estado/reprioritize` | **VERDE** | ROJA |
| `fase/begin_execution` | **VERDE** | ROJA |
| `fase/begin_check` … `fase/deliver` (6) | ROJA | ROJA |

**Siete de las quince eran invisibles para la batería del motor entera** — 597
pruebas, verde — y ahora no lo son. Y las que ya estaban cazadas conviene
decirlas con precisión, porque «ya estaba cubierto» no es lo mismo que «estaba
cubierto de forma exhaustiva»:

- `estado/begin_execution` lo cazaba
  `test_phase_operations_require_the_work_item_to_be_active`: **una** casilla
  (`begin_execution` desde `PLANNED`), la única de 48.
- `estado/change_scope` lo cazaba `test_scope_change_rejected_from_a_terminal_state`:
  **una** casilla (`CANCELLED`). `DELIVERED` no se probaba.
- Las seis de `[fase]` las cazaba `test_phase_operations_are_rejected_out_of_order`,
  que arranca siempre desde `PREPARAR`: 5 operaciones × 1 fase de 6. Por eso
  `fase/begin_execution` se le escapaba — es la única que **sí** es legal en
  `PREPARAR`, así que la prueba no la incluía.

Esas tres pruebas quedan subsumidas por las tablas nuevas. **No se han borrado**:
pasan igual y cuestan milisegundos.

### ¿Debilitó el rediseño alguna casilla que ya funcionaba?

Esta es la pregunta que ninguna batería en verde contesta, y hay que hacérsela
porque el rediseño **cambió la fase en la que se ensaya cada casilla de la tabla
A**. Antes, todos los preparadores pasaban por `_to_active`, que recorría el
ciclo hasta `ENTREGAR`; ahora cada operación se ensaya en su propia fase. Una
casilla que antes medía su guarda podría haber dejado de medirla, en silencio.

Se descarta mutando **las 19 guardas de estado del agregado entero**, no solo
las ocho de H-8:

```
guardas de estado encontradas en el agregado: 19
  OK  quitar la guarda de estado a activate              -> 14 failed, 71 passed
  OK  quitar la guarda de estado a cancel                -> 12 failed, 73 passed
  OK  quitar la guarda de estado a escalate              -> 14 failed, 71 passed
  OK  quitar la guarda de estado a resolve_decision      -> 14 failed, 71 passed
  OK  quitar la guarda de estado a dispatch_async        -> 14 failed, 71 passed
  OK  quitar la guarda de estado a observe_external_fact -> 14 failed, 71 passed
  OK  quitar la guarda de estado a fail_safely           -> 14 failed, 71 passed
  OK  quitar la guarda de estado a reactivate            -> 14 failed, 71 passed
  OK  quitar la guarda de estado a begin_execution       -> 14 failed, 71 passed
  OK  quitar la guarda de estado a begin_check           -> 14 failed, 71 passed
  OK  quitar la guarda de estado a begin_review          -> 14 failed, 71 passed
  OK  quitar la guarda de estado a approve_review        -> 14 failed, 71 passed
  OK  quitar la guarda de estado a request_repair        -> 14 failed, 71 passed
  OK  quitar la guarda de estado a resume_after_repair   -> 14 failed, 71 passed
  OK  quitar la guarda de estado a deliver               -> 14 failed, 71 passed
  OK  quitar la guarda de estado a pause                 -> 10 failed, 75 passed
  OK  quitar la guarda de estado a resume                -> 14 failed, 71 passed
  OK  quitar la guarda de estado a change_scope          ->  4 failed, 81 passed
  OK  quitar la guarda de estado a reprioritize          ->  4 failed, 81 passed

GUARDAS DE ESTADO QUE NINGUNA CASILLA MIDE: ninguna
restaurado identico: True
```

No se debilitó ninguna, y de paso queda dicho algo más fuerte que lo que pedía
la incidencia: **hoy no hay ni una sola guarda de estado en `WorkItem` que la
tabla A no mida.** Antes de este cambio había siete.

### Las guardas nuevas tampoco son vacuas

Una guarda anti-vacua que nadie muta es una guarda que nadie ha comprobado. Cada
mutación siembra el descuido que la guarda dice impedir:

| Mutación de la guarda | Resultado | Quién la caza |
| --- | --- | --- |
| ensayar `begin_check` en una fase donde su guarda de fase salta | 4 failed | `test_la_fase_del_ensayo_es_la_que_la_guarda_de_fase_acepta` |
| sacar `reprioritize` de `OPERATIONS` (el descuido que causó H-8) | 2 failed | `test_ninguna_operacion_del_dominio_se_queda_fuera_de_la_tabla` |
| sacar `deliver` de `OPERACIONES_CON_GUARDA_DE_FASE` | 3 failed | `test_ninguna_operacion_de_fase_se_queda_fuera_de_la_tabla` |
| olvidar que `DELIVERED` solo admite `ENTREGAR` | 3 failed | `test_las_casillas_sin_fase_preparable_son_exactamente_estas` |
| hacer la guarda de fase subclase de la de estado | 13 failed | `test_las_dos_guardas_lanzan_errores_que_no_se_confunden` |

```
GUARDAS QUE NO CAZARON SU PROPIO DESCUIDO: ninguna
```

La última es la que importa para el límite honesto: confirma que las doce
casillas débiles dejan de medir la guarda de estado exactamente cuando el
supuesto se rompe, y que la rotura no es silenciosa.

### No depende de ningún modelo

Dos tablas, dos bucles y dos `ast.parse`. No razona, no invoca nada, no sale a
la red. Las 202 casillas cuestan 1,5 s en las dos implementaciones del almacén.

### Validaciones obligatorias

```
uv run ruff format --check .   -> 442 files already formatted
uv run ruff check .            -> All checks passed!
uv run mypy src tests          -> Success: no issues found in 420 source files
uv run pytest tests/engine -q  -> 616 passed, 1 skipped
git diff --check               -> limpio
```

La batería completa (~3100 pruebas, con GUI) la corre Quality en la PR: en este
contenedor hay varios agentes a la vez y un intento anterior murió por OOM
(exit 137).

## Consecuencias

- Las ocho operaciones de H-8 quedan cruzadas contra los ocho estados. El hueco
  que ADR-048 declaró queda cerrado y su lista de excepciones borrada.
- El eje **fase** tiene ahora la misma guarda que el eje **estado**: una
  operación nueva con `_require_phase` que nazca fuera de la tabla rompe la
  batería. Esto es lo que impide que H-8 vuelva a ocurrir en el otro eje, en vez
  de solo arreglar los ocho casos de hoy.
- Quien añada una operación al dominio tiene que declarar en qué fase se la
  ensaya. Es deliberado: es el momento en que uno se pregunta qué pasa desde
  cada estado **y** desde cada fase.
- Doce casillas de la tabla A son más débiles que las otras 148, y está escrito
  dónde y por qué. No es una carencia oculta: es la carencia dicha.
- El coste de la tabla A sube de 96 a 160 casillas y aparecen 42 nuevas. Sigue
  costando ~1,5 s.

## Alternativas descartadas y por qué

**El cruce completo estado × fase × operación (960 casillas).** Es la lectura
literal de «la tabla gana una dimensión», y se descarta con el dato: **13 de las
20 operaciones no miran la fase**, así que sus seis variantes de fase son el
mismo ensayo repetido seis veces. Eso no es exhaustividad, es ruido, y multiplica
por seis la tabla que un revisor tiene que leer para creerse el oráculo. Una
tabla que nadie lee deja de guardar — que es, literalmente, cómo ocho
operaciones se quedaron fuera de la de 96.

**La tabla hermana sola, dejando las ocho fuera de la tabla de estados.** Habría
sido más barata y habría dejado en pie el defecto: `change_scope` y
`reprioritize` no son operaciones de fase y no tienen sitio en una tabla de
fases, así que seguirían sin cruzarse contra los ocho estados. Y las seis del
ciclo tienen guarda de **estado**; probarlas solo en el eje fase es justamente el
error de lectura que las mantuvo ocultas.

**Preparar las doce casillas débiles con una fase cualquiera y no decir nada.**
Es la opción que deja la tabla «completa» a la vista. Se descarta porque es
exactamente la trampa descrita en el contexto: casillas que parecen medir la
guarda de estado y no la miden. Preferimos doce casillas declaradas como más
débiles a 160 casillas de las que no se sabe cuáles miden.

**Inventar una prueba para tapar las doce.** No hay ninguna que las tape: la
combinación no existe en el dominio. Fabricar un `WorkItem` en `PLANNED` con fase
`EJECUTAR` saltándose las operaciones sería probar un estado que el sistema no
puede alcanzar, y ADR-001 lo prohíbe explícitamente («si es EQUIVALENTE, dilo y
explica por qué; NO inventes una prueba para taparlo»).
