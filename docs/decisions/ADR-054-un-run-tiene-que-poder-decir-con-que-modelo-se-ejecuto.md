# ADR-054 — Un Run tiene que poder decir con qué modelo se ejecutó

- Estado: APROBADO
- Fecha: 2026-08-21
- Aprobación: la fusión de esta PR por el propietario
- Contexto: hallazgo **H-6 (GAP-1)** de `docs/audits/DEFECTOS_ENCONTRADOS_2026-08-20.md`, incidencia #217
- Relacionadas: ADR-001 (disciplina de evidencia), ADR-036 («no pude leerlo» no es «no hay nada»), ADR-039 (perfiles versionados gobiernan a los Workers sin acoplarse a runtimes), ADR-026/ADR-029 (diario durable)

## Contexto y problema

La arquitectura §3.3 define el campo `worker` de un Run como «adapter + perfil
+ (si aplica) **modelo/runtime concretos usados**».

El código tenía `worker: str` (`src/sirius_engine/domain/run.py:71`): una cadena
libre, sin estructura y sin registro. En las pruebas era literalmente
`"claude-code"` — que no es ni un modelo ni un perfil, es el nombre del adapter.

La consecuencia no es cosmética. Con una cadena libre el motor **no puede**:

- comparar dos Runs por modelo,
- explicar por qué se sustituyó un Worker en términos de con qué se ejecutó,
- ni sostener **ninguna** afirmación sobre qué modelo hizo qué.

Lo último es lo que pesa. Es el dato que hace falta para contestar «¿rinde igual
un modelo pequeño y barato que uno caro?», que es la pregunta que el propietario
quiere poder contestar antes de cambiar de modelo, y es la puerta del vertical
de aprendizaje: sin saber con qué se hizo cada cosa, no hay nada de lo que
aprender.

El momento natural de arreglarlo, según el propio parte, es «cuando exista el
primer Worker real (B1 o C2), que es cuando el dato nace». La razón de hacerlo
ahora y no entonces está en la incidencia #217: **si se llega a B1/C2 sin
haberlo diseñado, el dato se pierde y ya no se recupera.** Un Run que no anotó
su modelo no puede anotarlo después.

## Criterio de parada (escrito ANTES de decidir)

Publicado en la incidencia #217 antes del primer commit y antes de ver ningún
resultado: <https://github.com/canelamoraguezandyjesus-bot/sirius/issues/217#issuecomment-5366542480>.
Reproducido aquí íntegro. Paro cuando se cumplan las cinco:

1. Existe una prueba que exige que un Run diga con qué modelo y runtime se
   ejecutó, y **la he visto fallar**, con su salida pegada.
2. La **mutación** de volver a la cadena libre tumba esa prueba. Si no la
   tumba, la prueba no vale y la arreglo.
3. El modelo sobrevive al viaje por el diario durable: escribir, cerrar,
   reabrir y leer devuelve el mismo `WorkerRef`.
4. Un Run no puede reescribir a posteriori con qué modelo se ejecutó.
5. `ruff format --check`, `ruff check`, `mypy src tests` y `pytest` de **las
   rutas tocadas** en verde. La batería completa la valida Quality en la PR.

Y lo que **no** se amplía, decidido también antes: registro de Workers, cambios
en `AgentProfile`, cableado de `project_worker_request`, ni rellenar el dato en
ningún camino real.

## Opciones consideradas

1. **Dejarlo para B1/C2**, como sugería el parte. Es cuando nace el dato, pero
   es también cuando ya no hay dónde ponerlo si nadie lo diseñó antes: el
   primer Worker real produciría Runs cuyo modelo no consta en ninguna parte, y
   esos Runs no se pueden reparar hacia atrás.
2. **Convención sobre la cadena**: seguir con `worker: str` y acordar un formato
   (`"adapter/perfil@version#modelo"`). Cero cambios de tipo, y cero garantías:
   nada impide escribir `"claude-code"` otra vez, y quien lo escriba así no se
   entera hasta que alguien intenta comparar dos Runs.
3. **Objeto de valor** `WorkerRef` con adapter y perfil obligatorios y
   modelo/runtime opcionales, y anotación del modelo en la transición que ya
   existe para ello.
4. **Objeto de valor con modelo obligatorio.** Cumple §3.3 al pie de la letra
   pero obliga a inventarse un modelo hoy, que no se conoce: cambiaría un hueco
   honesto por un dato falso.

## Decisión

**La tercera.**

1. `src/sirius_engine/domain/worker_ref.py` define `WorkerRef`: `adapter`,
   `perfil_ref` y `perfil_version` obligatorios; `modelo` y `runtime`
   opcionales. `Run.worker` pasa a ser un `WorkerRef`.
2. La forma la impide el tipo, no un revisor. Un `WorkerRef` sin adapter, sin
   perfil o con una versión de perfil no positiva es **inconstruible**; y
   `modelo=""` también, para que un dato ausente no pueda disfrazarse de
   presente. `None` significa «no se sabe» y se conserva como tal (ADR-036).
3. El modelo/runtime concretos se anotan en `confirm_running`
   (`DISPATCHED -> RUNNING`), que §3.3 ya define como el instante en que
   `STATUS` confirma que el Worker aceptó el encargo: es la primera observación
   que puede aportarlos, y así no se inventan ni una transición ni un suceso
   nuevos. Ambos argumentos son opcionales; omitirlos deja intacto lo que ya
   constara.
4. **La historia no se reescribe.** Anotar un modelo distinto del que ya consta
   levanta `WorkerRuntimeConflictError` en vez de sobrescribir: un Run que puede
   cambiar de modelo a posteriori no sostiene ninguna afirmación sobre qué
   modelo hizo qué.
5. **El reintento no hereda el modelo del intento anterior.** Hereda adapter y
   perfil —son la elección del llamador— pero no modelo ni runtime, que son una
   observación del intento anterior. Un Run recién `PREPARED` no puede afirmar
   con qué modelo se ejecutó: aún no lo ha hecho. La sustitución de Worker sí
   recibe el `WorkerRef` completo, porque ahí lo elige explícitamente quien
   sustituye.
6. El diario durable persiste la estructura entera. Un diario escrito **antes**
   de este ADR no se lee: su `worker` es una cadena que no dice bajo qué perfil
   se ejecutó el Run, y adivinarlo aquí convertiría un dato ausente en uno
   presente. `worker_ref_from_dict` lo declara ilegible y dice por qué.

Lo que **no** hace, tal y como se publicó en la nota de arranque: no crea
registro de Workers, no valida que un modelo exista, no toca `AgentProfile` (un
perfil describe qué puede hacer un rol, nunca con qué herramienta concreta —
incidencia #202, ADR-039), no cablea `project_worker_request`, y **no rellena el
dato en ningún camino de producción**, porque hoy no hay ningún Worker real que
lo produzca. Esto abre el sitio; llenarlo es B1/C2.

## Comprobación que la sostiene

### 1. El defecto, reproducido ejecutando (antes de tocar nada)

Con `uv run python`, sobre `main` (`450df1b`): preparar un Run, preguntarle su
modelo, e intentar anotarlo al confirmar que el Worker aceptó.

```
1) tipo de Run.worker: str | valor: 'claude-code'
2) preguntar el modelo: AttributeError: 'str' object has no attribute 'modelo'
3) anotar el modelo al aceptar: TypeError: InMemoryWorkEngineStore.confirm_run_running() got an unexpected keyword argument 'modelo'
4) objeto de valor: ModuleNotFoundError: No module named 'sirius_engine.domain.worker_ref'
```

### 2. La prueba, vista fallar antes del arreglo

```
$ uv run pytest tests/engine/test_worker_ref.py -q
ERROR collecting tests/engine/test_worker_ref.py
tests/engine/test_worker_ref.py:24: in <module>
    from sirius_engine.domain.errors import WorkerRuntimeConflictError
E   ImportError: cannot import name 'WorkerRuntimeConflictError' from 'sirius_engine.domain.errors'
1 error in 0.18s
```

### 3. La prueba, en verde después

```
$ uv run pytest tests/engine/test_worker_ref.py -q
26 passed in 0.10s
```

Son 26 porque cada prueba de contrato corre contra las dos implementaciones del
puerto (`InMemoryWorkEngineStore` y `DurableWorkEngineStore`), como el resto de
`tests/engine/`.

### 4. Prueba por mutación

Cada mutación siembra de vuelta un defecto y comprueba que **alguna** prueba
cae. Ninguna sobrevivió.

| Mutación | Qué siembra | Resultado |
|---|---|---|
| M1 | `run.py` entero como en `origin/main` (vuelta a la cadena libre) | **15 de 26 fallan** |
| M2 | `confirm_running` deja de anotar modelo/runtime | **9 fallan** |
| M3 | `record_execution` sobrescribe en vez de fallar | **2 fallan** (`test_un_run_no_puede_reescribir_con_que_modelo_se_ejecuto`) |
| M4 | se admite `modelo=""` como dato conocido | **4 fallan** (`test_un_worker_mal_formado_es_inconstruible[modelo/runtime]`) |
| M5 | el diario persiste solo el adapter | **1 falla** (`test_el_modelo_sobrevive_al_reinicio_del_almacen_durable`) |
| M6 | el reintento hereda el modelo del intento anterior | **2 fallan** (`test_un_reintento_no_hereda_el_modelo_del_intento_anterior`) |

Sobre M5, para no afirmar de más: solo cae una prueba porque la otra de
round-trip comprueba el caso en que **no** hay modelo, y para ese caso la
mutación es equivalente. No se añade una prueba para taparlo: el caso ya está
cubierto por la que sí cae.

### 5. Validaciones

```
$ uv run ruff format --check .
433 files already formatted

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests
Success: no issues found in 414 source files

$ uv run pytest tests/engine/test_worker_ref.py tests/engine/test_retry_and_substitution.py \
    tests/engine/test_scope_change.py tests/engine/test_journal_replay.py \
    tests/engine/test_run_transitions.py tests/engine/test_recovery_sweep.py \
    tests/engine/test_governance.py tests/engine/test_cancellation.py \
    tests/engine/test_boundary.py tests/engine/test_durable_journal.py \
    tests/engine/test_spike_i3_durability.py \
    tests/automation/test_registro_de_defectos.py \
    tests/automation/test_registro_de_decisiones.py -q
222 passed in 1.95s
```

La batería completa **no se ejecuta aquí a propósito**: un intento anterior de
este mismo trabajo murió con OOM (exit 137) por correr las ~2900 pruebas en
paralelo con otros agentes en el mismo contenedor. La valida Quality en la PR.

## Consecuencias

- El motor ya **puede** contestar «¿qué modelo hizo esto?» y «¿rinden igual dos
  modelos bajo el mismo perfil?». Hoy contestaría «no se sabe» para todo Run
  real, porque no hay Workers reales; lo que cambia es que ahora eso es un hueco
  con nombre y no un dato que nunca existió.
- `mypy` obliga a todos los llamadores a la vez: el cambio de tipo es el que
  hace imposible volver a la cadena libre por descuido.
- **Rompe la lectura de diarios durables anteriores.** Es deliberado y no afecta
  a nada en marcha: no hay ningún diario en producción, y las pruebas escriben
  el suyo. Si algún día lo hubiera, la migración exige decir bajo qué perfil
  corrió cada Run viejo, que es precisamente el dato que no está.
- `experiments/work_engine_spike_i3/entity_codec.py` cambia dos líneas: importa
  el dominio de producción, así que no podía quedarse atrás. El spike sigue
  reproduciendo su matriz punto-de-muerte igual (24 pruebas en verde).
- B1/C2 heredan un hueco muy concreto que llenar: pasar `modelo` y `runtime` a
  `confirm_run_running` desde el `STATUS` del Worker real.

## Alternativas descartadas y por qué

- **Esperar a B1/C2** (opción 1): es cuando nace el dato, pero también cuando ya
  es tarde. El coste de adelantarlo es un cambio de tipo mecánico; el coste de
  retrasarlo es una tanda de Runs cuyo modelo no consta y no se puede
  reconstruir.
- **Convención sobre la cadena** (opción 2): no impide nada. El defecto que se
  cierra aquí es exactamente el de un campo que acepta cualquier cosa; cambiar
  el formato acordado sin cambiar el tipo lo deja intacto.
- **Modelo obligatorio** (opción 4): obligaría a inventar un valor hoy. Cambiar
  un hueco honesto por un dato falso es peor que el defecto original, y
  contradice ADR-036.
- **Meter el modelo en `AgentProfile`**: contradice ADR-039 e incidencia #202.
  Un perfil dice qué puede hacer un rol; el modelo es un hecho de ejecución.
- **Un campo suelto `modelo: str | None` en `Run`**, sin objeto de valor: deja
  `worker` siendo la misma cadena libre, y con ella la imposibilidad de saber
  bajo qué perfil versionado corrió. §3.3 pide los tres datos juntos porque solo
  juntos permiten comparar.
- **Aceptar diarios viejos adivinando el perfil**: convertiría «no pude leerlo»
  en un dato inventado. ADR-036 dice exactamente lo contrario.
