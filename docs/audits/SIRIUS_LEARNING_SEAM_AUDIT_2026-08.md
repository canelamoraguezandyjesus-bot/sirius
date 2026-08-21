# Sirius — Auditoría de costuras de aprendizaje e informe de integración

- **Estado:** EVIDENCIA / INFORME. **No autoriza implementación, no cambia el plan
  aprobado, no enmienda el contrato operativo y no reordena ninguna fase.**
- **Fecha:** 2026-08-19
- **Encargo:** integrar en Sirius el diseño de aprendizaje de los dos documentos
  aportados por el propietario (`01_HERMES_LEARNING_AUDIT`,
  `02_SIRIUS_LEARNING_INTEGRATION_BRIEF`), **sin implementar** el Learning Engine.
- **Base verificada:** `main` = `a25ee3b` («Las bibliotecas de Qt dejan de poder
  costar el trabajo entero (#208)»); rama de la PR #207 = `9e3a79b`.
- **Nota de arranque:** ADR-043 (cuatro preguntas y criterio de parada publicados
  antes del primer cambio de contenido, ADR-001).
- **Propuesta asociada:** ADR-043, en estado `PROPUESTO`. Nada de este informe es
  una decisión aprobada.

Este documento es **evidencia**, no autoridad. Donde afirma algo sobre el
comportamiento del sistema, cita `ruta:línea` o el comando que lo comprueba.
Donde no pudo comprobarlo, lo dice.

> **Conclusión, antes de los detalles.** Sirius **no tiene construido** un
> Learning System, ni cerca. Lo que sí tiene, y es lo que este contraste
> encontró, es un conjunto de **patrones, invariantes y mecanismos análogos ya
> demostrados** para casi todo lo que el brief plantea como problema abierto:
> refutación independiente entre proveedores distintos, agregación determinista
> que falla cerrado, aprobación ligada a un hash exacto, conocimiento versionado
> con procedencia y supersede, tratamiento de una fuente externa como dato y no
> como instrucción, y un sidecar de solo lectura con frontera estructural.
>
> **Que exista el patrón no significa que el sistema esté medio construido.** Esos
> mecanismos viven repartidos en tres sitios con reglas distintas —
> `scripts/automation`, `src/sirius` y `src/sirius_engine`—, varios están al otro
> lado de fronteras que una prueba hace cumplir, y otros están construidos pero
> **todavía sin cablear** dentro del motor. La clasificación honesta de qué se
> puede reutilizar físicamente, qué solo conceptualmente y qué hay que
> implementar detrás de las interfaces del Work Engine está en §4, y **esa
> clasificación es todavía una investigación pendiente**, no un resultado.
>
> La regla que sostiene todo el informe: **reuse before build, pero también
> abstraction before coupling.** No hay que reinventar lo que Sirius ya demostró;
> tampoco hay que arrastrar el motor hacia la vía GitHub o hacia `src/sirius`
> para aprovechar código, porque eso rompe las fronteras que ADR-019 y ADR-020
> establecieron a propósito.
>
> **No recomiendo construir el Learning System todavía**, y la razón fuerte no es
> el inventario de patrones: es que **no hay experiencia real de la que aprender**
> (§6.6).
>
> «Todavía no» **no significa «ya veremos»**: §8.4 fija una puerta de **siete
> condiciones comprobables con un comando cada una**, hoy las siete en `NO`. El
> momento más temprano posible es **justo después del hito M3 —ocho bloques del
> plan por delante, más A5 que sigue abierto—, y solo si GAP-1 se engancha a B1 o
> a C2**. Si GAP-1 no se engancha a ningún bloque, la puerta no se abre sola
> nunca, y ese es el único punto que hay que vigilar de aquí a entonces.
>
> Dos rondas adversariales devolvieron objeciones de la misma familia y **la regla
> de las dos rondas (ADR-001) se activó**: §14 escribe el patrón, la raíz, las
> correcciones a lo que este informe afirmó de más y la decisión de retirar y
> escalar.

---

## 1. Estado real encontrado

### 1.1 Lo que el motor tiene hoy

Fase A del plan (`SIRIUS_WORK_ENGINE_PLAN_IMPLEMENTACION.md` §1): **A1–A4
fusionados; A5 abierto**. El motor existe como dominio puro más almacén durable
más espejo de solo lectura más perfiles/permisos. Verificado leyendo el árbol:

| Bloque | Evidencia en `main` |
|---|---|
| A1 núcleo | `src/sirius_engine/domain/work_item.py`, `domain/run.py`, `domain/events.py` |
| S1 spike I3 | `experiments/work_engine_spike_i3/` (único spike ejecutado) |
| A2 almacén durable | `adapters/durable/journal.py`, `adapters/durable/store.py`, `recovery.py` |
| A3 espejo + contexto | `mirror_projection.py`, `adapters/github_cli_mirror.py`, `context_recall.py` |
| A4 perfiles + permisos | `domain/profile.py`, `domain/permission_envelope.py`, `capability_registry.py`, `capability_resolver.py`, `egress.py`, `worker_request.py` |

### 1.2 Lo que el motor **no** tiene, y es decisivo para el aprendizaje

**No existe el contrato de Worker.** No hay `ports/worker.py` ni ninguna
implementación de `START/STATUS/RESULT/CANCEL` (arquitectura §5):

```
$ ls src/sirius_engine/ports/
__init__.py  github_mirror.py  store.py  world.py
```

Los cuatro adapters existentes (`fixture_mirror`, `github_cli_mirror`,
`github_worker_request`, `memory_store`) son de **lectura o proyección**. En
consecuencia: **el motor no ha despachado nunca ningún Worker, no ha ejecutado
nunca ningún WorkItem real y no existe ni un solo `WorkResult` real de un Worker
real en ningún almacén.** No hay corpus del que aprender. Esto no es una opinión
sobre madurez: es la ausencia de un puerto.

### 1.3 A5 / PR #207: abierto y **con una comprobación en rojo real**

Estado por API el 2026-08-19: `state: open`, `merged: false`, head `9e3a79b`,
base `a25ee3b` (al día con `main`), 22 ficheros, `mergeable_state: unstable`.

La causa del rojo está identificada y **no es intermitente**. La rama introduce
`ADR-042-gobierno-previo-al-primer-worker-externo-…md` mientras `main` ya
contiene `ADR-042-un-paso-de-preparacion-sin-plazo-propio-….md`. Dos ADR con el
mismo número es exactamente lo que ADR-032 prohíbe y lo que
`tests/automation/test_registro_de_decisiones.py` hace imposible en `main`.
Reproducido sobre un worktree de la propia rama:

```
$ uv run pytest tests/automation/test_registro_de_decisiones.py -q
FAILED test_no_new_number_is_ever_reused
  Left contains 1 more item:
  {42: ['ADR-042-gobierno-previo-al-primer-worker-externo-…md',
        'ADR-042-un-paso-de-preparacion-sin-plazo-propio-…md']}
1 failed, 3 passed
```

Es la familia de defecto que ADR-032 registró (dos ramas leen el mismo listado
y eligen el mismo número), y la prueba está haciendo justo su trabajo. **No se
corrige aquí**: tocar A5 está prohibido por el propio encargo. Se reporta con la
recomendación concreta en §12.

> **Sobre la numeración, y qué NO se deduce de aquí.** Esta rama es exploratoria
> y no está aprobada; **no reserva ningún número frente a A5**, que es trabajo
> del Work Engine actualmente autorizado. El ADR de esta rama lleva un número
> provisional y tendrá que recalcularlo si alguna vez se integra. Lo único que
> este informe registra es el hecho: **hay una colisión real en A5**, y al
> corregirla el duplicado debe tomar **el siguiente número válido en `main` en
> ese momento**, calculado con `scripts/siguiente_adr.py` contra `main`. Esta
> rama no se toca ni se consulta para eso.

### 1.4 Otras PR abiertas

`#171` (investigador por etiqueta, con recomendación registrada de cerrar sin
fusionar, plan §6) y `#117`. Ninguna afecta al aprendizaje.

---

## 2. Contraste de los dos adjuntos contra el repositorio

Se verificó **una por una** cada afirmación que los adjuntos hacen *sobre
Sirius*. Las afirmaciones sobre Hermes no se verificaron: el repositorio
`NousResearch/hermes-agent` no está en el alcance de esta sesión, y así se
declaró antes de empezar (ADR-043, «qué NO garantiza esto»).

| # | Afirmación del adjunto | Veredicto | Evidencia |
|---|---|---|---|
| a | «PR #207 (A5) seguía abierto» | **CIERTO, y peor de lo que sugiere** | Abierto y con `test_registro_de_decisiones` en rojo (§1.3) |
| b | «Sirius en `main` `a25ee3b`» | **CIERTO** | `git log -1` |
| c | «El diseño debe respetar WorkPackage y WorkResult» (los da por piezas existentes) | **FALSO en código** | No existe ningún tipo `WorkPackage` ni `WorkResult`. Son `Mapping[str, object]` opacos: `domain/run.py:72` (`work_package`), `domain/run.py:81` (`resultado`), `domain/work_item.py:85` (`resultado`) |
| d | «Agent Profile no contiene provider/model/credenciales/estado» | **CIERTO** | `domain/profile.py:33-48`: `ref, version, mision, procedimiento_ref, capacidades, permisos, contrato_entrada, contrato_salida`. Sin modelo ni proveedor |
| e | «PermissionEnvelope existe» | **CIERTO** | `domain/permission_envelope.py:22-30`, deny-by-default, `ENVELOPE_VACIO` |
| f | «journal / evidence existe» | **CIERTO y sólido** | `adapters/durable/journal.py`: JSON Lines, `checksum_sha256` por registro, `fsync`, recorte de cola truncada (ADR-026, ADR-029) |
| g | «context recovery existe» | **CIERTO** | `context_recall.py`: tres proveedores deterministas, **sin LLM**, y `proveedores_fallidos` separado de «no hay» (ADR-036) |
| h | «Inspect AI como laboratorio» | **PARCIAL — no es una pieza, es una idea, y ya estaba decidida** | No hay `inspect_ai` en el árbol. Aparece solo en documentos. `SIRIUS_WORK_ENGINE_INVENTARIO.md:187` ya lo resolvió: «Inspect AI como dueño del ciclo → **Descartar** (queda como evaluador futuro, fuera del motor)». El adjunto propone como decisión nueva algo **que el repo ya decidió igual** |
| i | «M3 es candidato natural» | **PARCIAL** | M3 existe (C1+C2+C3+C4) pero llega después de B1, y su cierre exige que la vía Codex se haya ejercitado de verdad. Ver §8 para la colocación que sostiene la evidencia |
| j | «no hay base de datos» | **PARCIAL** | El motor no usa ninguna DB: su almacén es JSON Lines. Pero **Sirius 0.1 sí tiene SQLite + Alembic** (`migrations/`, `alembic.ini`, `src/sirius/adapters/persistence/`). La frontera de §2.3 explica por qué eso no ayuda |
| k | «El review se lanza **automáticamente** al terminar el WorkItem» | **NO IMPLEMENTABLE HOY sin enmienda de contrato** | Ver §2.1 |
| l | «Se analizan éxitos, fallos, cancelaciones y **FAILED_SAFELY**» | **CONTRADICE el modelo de estado** | `FAILED_SAFELY` **no es terminal**: `work_item.py:36` fija `TERMINAL_STATES = {CANCELLED, DELIVERED}` y `work_item.py:145` define `reactivate()`. Un hook «al entrar en estado terminal» no vería jamás un `FAILED_SAFELY` |
| m | «El Refutador debe usar un modelo distinto del proponente» | **NO VERIFICABLE por el motor hoy** | Ver §2.2. Es el hallazgo más importante de esta auditoría |
| n | «Curator/Extractor como Agent Profiles sustituibles» | **CIERTO y encaja** | `profile_registry.py` + `docs/implementation/work_engine/perfiles/*.yml` admiten perfiles nuevos como dato, sin tocar código |
| o | «Worker/model/provider/runtime sustituibles» | **CIERTO hoy** | `grep -niE "claude\|openai\|anthropic\|gpt-\|sonnet\|opus" src/sirius_engine/` no devuelve ningún acoplamiento: solo comentarios que citan el nombre de un workflow o el identificador de un revisor |

### 2.1 «Automáticamente al terminar» choca con la prohibición §9 del contrato

El brief pide un `Learning Hook` que se dispare solo. Hoy hay exactamente tres
formas de conseguirlo, y las tres están cerradas:

1. **Dentro del dominio** (`WorkItem.deliver()`): imposible por construcción. El
   dominio es de instantáneas inmutables sin efectos (`work_item.py:1-9`); meter
   ahí una revisión rompería a la vez la pureza y la garantía «un fallo de
   aprendizaje no rompe un WorkItem ya entregado».
2. **Dentro del puerto de almacén** (`deliver_work_item`): obligaría a *todas*
   las implementaciones del puerto (`ports/store.py:73`) a arrastrar el
   aprendizaje, y un fallo del sidecar viviría dentro de la transición terminal.
   Exactamente la garantía que el brief exige que no se rompa.
3. **Un barrido periódico**: el contrato §9 prohíbe «usar vigilancia periódica
   como **motor** del flujo», y §9.1 admite **una** ejecución periódica, ya
   gastada por el reconciliador. Una segunda sale del amparo de la excepción y
   necesita decisión nueva.

**Conclusión honesta**: el disparo automático no es una decisión de diseño
pendiente, es una **enmienda de contrato pendiente**. Hasta que el motor corra
como servicio supervisado (D2, bloqueado por I4), la única forma limpia de
lanzar la revisión es **una orden**: un comando que el propietario invoca. Eso
no es una degradación del diseño; es la fase «manual» que el propio brief §10
pide como punto de partida.

### 2.2 «Modelo distinto» es hoy una promesa que el motor no puede comprobar

Esta es la costura que la auditoría vino a buscar, y está rota. Tres lecturas
independientes lo confirman:

- `AgentProfile` **no tiene** campo de modelo ni proveedor (`domain/profile.py:33-48`).
- `WorkerRequest` —la proyección exacta del encargo— lleva `perfil_ref` y
  `perfil_version`, y **ningún** identificador de modelo (`worker_request.py:44-54`).
- `Run.worker` es **una sola cadena sin estructura** (`domain/run.py:71`), y
  `prepare_run(..., worker: str, ...)` (`ports/store.py:132`) no impone ninguna
  forma. La arquitectura §3.3 sí pide más: «worker: adapter + perfil + (si
  aplica) **modelo/runtime concretos usados**».

Es decir: **el código diverge de la arquitectura aprobada en §3.3**, con
independencia del aprendizaje. Sin un identificador de modelo comparable y
estructurado en el Run, la frase «el Refutador usa un modelo distinto del
proponente» no la puede afirmar el motor: solo la puede *prometer* un prompt. Y
una garantía que solo vive en un prompt no es una garantía.

Por el criterio de parada 3 de ADR-043, esto se declara así y no se suaviza:
**la invariante «Refutador con modelo distinto» NO es sostenible hoy.** Lo que
falta es exactamente un dato (§5, GAP-1), y cerrarlo es una corrección de
divergencia con la arquitectura, no una ampliación de alcance por aprendizaje.

### 2.3 Patrones que Sirius ya ha demostrado — y por qué eso no es lo mismo que tenerlos disponibles

Los que este contraste encontró primero, con la advertencia que gobierna toda la
sección: **patrón demostrado no es componente disponible**. Ninguno es
reutilizable tal cual desde el motor. No es un inventario cerrado —§14.3 añade
los del carril de automatización— y la clasificación completa vive en §4.1:

1. **MEMORY declarativa versionada con procedencia obligatoria — ya existe, en
   el producto.** `src/sirius/domain/memory.py`: `Memory` + `MemoryRevision`
   (revisión inmutable, `version`, `origin` obligatorio, `source_event_id`,
   `subject_key`, `project_id`, `MemoryStatus`). Con corrección por revisión
   nueva, archivado, borrado con redacción, y **detección determinista de
   conflictos de precedencia** (`src/sirius/domain/precedence.py`). Es,
   literalmente, buena parte de lo que el brief §5 propone diseñar de cero.
   **Pero**: `tests/engine/test_boundary.py` prohíbe que `sirius_engine` importe
   `sirius` y viceversa, en ambos sentidos. Reutilizar el modelo de V4 desde el
   motor **no es posible sin romper una frontera aprobada** (ADR-020). Lo que sí
   es reutilizable es el **diseño** (revisión inmutable + origen obligatorio +
   supersede + precedencia), no el código.
2. **SKILL ya está definido en la arquitectura**, y con una frontera que el
   brief conviene respetar: §6 regla 6 dice que una skill es «un paquete de
   capacidad/procedimiento reutilizable […] **nunca autoridad ni memoria**», y
   que el Resolver la trata como un proveedor más. El brief no crea el concepto:
   lo hereda, y su formato **no debe** convertirse en dependencia del motor.
3. **La refutación por hallazgo ya es un patrón registrado.** ADR-010 (`docs/decisions/ADR-010-…md:66-67`):
   «Cada hallazgo cumple el esquema FINDING-### con evidencia concreta **e
   intento de refutación**; sin ambos, no entra en el informe final». El
   Refutador del brief no inventa una figura nueva: **generaliza una regla que
   Sirius ya aplica al Auditor**. Eso es un argumento a su favor, y a la vez la
   razón de no montarle un aparato nuevo.

Además, la arquitectura §9 ya cerró la pregunta de fondo del brief antes de que
se hiciera: **«No hay "Agente de memoria": ningún empleado con estado propio»**,
y el sustrato de memoria «ya existe en el producto […]; exponerlo es trabajo
futuro sobre código existente». El brief coincide con eso. Conviene decirlo:
en este punto no estamos decidiendo, estamos confirmando.

---

## 3. Learning seam audit, costura por costura

Lo que el encargo pide auditar, con el veredicto de si sirve como costura de
aprendizaje **hoy**, sin cambiar nada.

### 3.1 `WorkItem` — `domain/work_item.py`

- Estados: 8 (`work_item.py:27-35`). `TERMINAL_STATES = {CANCELLED, DELIVERED}`
  (`:36-37`). **`FAILED_SAFELY` no es terminal** (`:145` `reactivate()`).
- Puntos de entrada a terminal: exactamente tres —`deliver()` (`:186`, exige
  fase `ENTREGAR`), `cancel()` (`:105`) y `resolve_decision(continuar=False)`
  (`:119`). Es un conjunto pequeño y cerrado: bueno para razonar, inútil como
  punto de enganche (son funciones puras que devuelven instantáneas).
- `clase: WorkItemClass` es un **StrEnum cerrado de 7 miembros** (`:52-61`).
- `resultado: Mapping[str, object] | None` (`:85`): opaco. El motor no sabe qué
  hay dentro.
- `evidencia: tuple[str, ...]` (`:84`): **referencias en texto**, sin estructura.
- **Veredicto**: contiene el objetivo, el entregable, el criterio de terminado y
  los límites — material de sobra para un dossier. No contiene, ni referencia de
  forma tipada, qué Worker/modelo hizo qué.

### 3.2 `Run` — `domain/run.py`

- `worker: str` (`:71`) — sin estructura (ver §2.2, GAP-1).
- `work_package: Mapping[str, object]` (`:72`) — instantánea exacta de lo
  enviado, pero opaca.
- `resultado: Mapping[str, object] | None` (`:81`) — íd.
- Sí existe, y es valioso para aprendizaje: `intento` (`:73`), `sustituye_a` y
  `motivo_sustitucion` (`:85-86`), `desenlace` con `LOST` incluido (`:41-46`),
  `invalidado_por_alcance` (`:90`), `diagnostico` (`:82`), `ultima_observacion`
  + `observado_en` (`:79-80`).
- **Veredicto**: el Run ya distingue «falló», «lo cancelaron», «se perdió» y «lo
  sustituyeron, por este motivo». Eso es exactamente la materia prima de un
  aprendizaje negativo bien acotado. Lo único que falta es *con qué modelo*.

### 3.3 `WorkPackage` / `WorkResult` — **no existen como tipos**

Son `Mapping[str, object]` sin esquema en todo el motor. La arquitectura §4.1 y
§4.2 los define con campos concretos (`no_comprobado`, `comprobaciones`,
`metricas`, `artefactos`…). Un Learning Extractor que dependa de esos campos
depende de un contrato **que hoy nadie valida**. Es GAP-2.

### 3.4 Diario y evidencia — `domain/events.py`, `adapters/durable/journal.py`

- `Event` = `sequence`, `occurred_at`, `aggregate_type`, `aggregate_id`, `kind`,
  `entity: WorkItem | Run` (`events.py:31-40`). **Lleva la instantánea completa
  del agregado**, no un delta.
- `EventKind` es un `Literal` **cerrado** de 33 valores (`events.py:96-124`),
  incluidos `work_item_delivered`, `work_item_cancelled`,
  `work_item_failed_safely`, `run_failed`, `run_marked_lost`, `run_retried`,
  `run_worker_substituted`.
- `rebuild_state()` (`events.py:56`) reconstruye estado plegando el diario, de
  forma determinista y sin reejecutar transiciones.
- Persistencia: JSON Lines, un `checksum_sha256` por registro sobre la
  codificación canónica, `fsync` por anexo, recorte de cola truncada y
  `InternalCorruptionError` si la corrupción no es una cola
  (`adapters/durable/journal.py:1-45`).
- **Veredicto**: **esta es la mejor costura del sistema, y ya está construida.**
  Un lector del diario obtiene, sin tocar nada: qué pasó, en qué orden, con qué
  instantánea, y con integridad comprobable. `list_events()`
  (`ports/store.py:202`) ya lo expone. Es la base del enganche recomendado (§6).

### 3.5 `context.recuperar` — `context_recall.py`

- Tres proveedores deterministas (árbol, incidencias/PR, git), **ningún LLM**
  (`context_recall.py:1-27`).
- Devuelve `Referencia(tipo, identificador, fragmento)`: **cita, no sintetiza**.
- `proveedores_fallidos` separado del resultado: una lectura caída nunca se
  convierte en «no hay» (ADR-036).
- Reutiliza `es_autor_de_confianza` (`mirror_projection.py:80-82`): solo
  comentarios del propietario (`OWNER`) o del bot.
- **Veredicto**: es el «recuperación determinista antes de gastar IA» que el
  adjunto 01 recomienda copiar de Hermes. **Ya está copiado.** Y su filtro de
  autor es, además, la primera línea contra inyección persistente por
  comentario de terceros.

### 3.6 Perfiles, `PermissionEnvelope`, Resolver y egress

- `AgentProfile` (`domain/profile.py:33-48`): sin modelo, sin proveedor, sin
  credenciales, sin estado. Sustituibilidad intacta.
- `compute_permission_envelope` (`domain/permission_envelope.py:36`):
  deny-by-default estricto (`capacidades_concedidas = frozenset(capacidades)`,
  ni una más) y **fail-closed** ante red + escritura (`EgressIncompatibleError`
  antes de conceder nada, sin degradar a «solo lectura»).
- `resolve_capabilities` (`capability_resolver.py:41`): tres guardas sin
  degradación — capacidad no registrada, no concedida, y **ámbito de escritura
  incompatible** (`envelope.escritura not in definicion.ambitos_escritura`).
- Registro cerrado, versión 3, ocho capacidades
  (`docs/implementation/work_engine/perfiles/registro_capacidades.yml`):
  `incidencia.leer`, `repo.leer`, `repo.escribir`, `pr.crear`,
  `validaciones.ejecutar`, `veredicto.escribir`, `contexto.recuperar`,
  `web.buscar`.
- `validar_egress_fail_closed` (`egress.py:25`): un fragmento **sin clasificar**
  impide arrancar siempre; con red concedida, cualquier fragmento no
  `exportable` también.
- **Veredicto — CORREGIDO en la ronda 2, ver §14.4 (C-1 y C-2).** La invariante «el Extractor y
  el Refutador **no pueden** crear/modificar/borrar conocimiento activo» es
  **expresable** con estas piezas: un perfil con `permisos.escritura: null` y una
  capacidad `conocimiento.escribir` registrada con `ambitos_escritura:
  [conocimiento]` serían rechazados por el Resolver por dos motivos
  independientes, sin depender de ningún prompt.
  **Pero hoy no está en vigor.** *(Corregido en la ronda 3: las dos redacciones
  anteriores decían que los cuatro símbolos «no tienen ningún llamador en
  `src/`», y eso era **falso** para tres de ellos.)* Lo cierto, y más estrecho:
  la proyección de A4 **sí está ensamblada** en `src/`: `project_worker_request`
(`worker_request.py:57`) encadena envelope, egress y resolución de capacidades
(`worker_request.py:65-67`). Lo que **no existe es ningún llamador de esa
proyección**: solo la invocan las pruebas. Ningún camino de ejecución del motor
construye un `WorkerRequest`, así que las tres guardas nunca corren en
producción. La única superficie que hoy restringe de verdad a
  un Worker es `--allowedTools` en el YAML del workflow, y para el revisor está
  configurada como `--dangerously-skip-permissions --allowedTools "Bash,Read,Grep,Glob"`
  (`.github/workflows/review-sirius-work.yml:280`). El Auditor sí es estricto
  (`audit-sirius-repository.yml:151-152`), consistente con ADR-016.
  Segundo límite, también de la ronda 2: `PermissionEnvelope.escritura` es **un
  solo nombre de ámbito**, no una ruta ni un recurso. Si el conocimiento activo
  se materializa como ficheros del repositorio, un perfil con `escritura: repo`
  lo cubriría igual que cubre el código. La separación exige un ámbito propio, y
  eso es trabajo, no una propiedad que ya esté ahí.

### 3.7 Presupuesto, escalado y notificación (A5, rama abierta)

- `Budget` **no se persiste**: es un valor inmutable que el llamador conserva y
  pasa entre invocaciones (`a5:domain/budget.py:1-17`). El límite se lee de
  `WorkItem.limites["presupuesto"]["limite"]`.
  **Consecuencia dura**: un sidecar que corre *después* de que el WorkItem sea
  terminal **no puede cargarse a su presupuesto** — no hay dónde. El coste del
  aprendizaje es gasto nuevo, y gasto nuevo es la causa 2 de escalado.
- `CausaEscalado` es un StrEnum **cerrado de siete causas**
  (`a5:domain/escalation.py:28-56`), copiadas al pie de la letra de la
  arquitectura §10.
- `Escalada` (`a5:domain/escalation.py:59-72`) se construye **solo desde un
  WorkItem** (`construir_escalada`), copiando su instantánea completa.
- `NotificationPort.notificar(escalada: Escalada)` (`a5:ports/notification.py:19`)
  es la única superficie de aviso, y **solo acepta una `Escalada`**.
- **Veredicto**: el canal de presentación de una propuesta de aprendizaje **no
  existe**. Una propuesta de MEMORY/SKILL con su diff no es ninguna de las siete
  causas, y no nace de un WorkItem. Meterla por ahí exigiría o inventar una
  octava causa (prohibido: la lista es cerrada por arquitectura §10) o
  desnaturalizar la causa 1. Es GAP-3.

### 3.8 Autoridad por clase (A5, rama abierta) — **la puerta que cierra el diseño**

`a5:domain/authority.py:47-56` implementa la tabla del contrato v1.7 §11.1 como
función **total** sobre `WorkItemClass`, sin valor por defecto:

```python
def autoridad_de_clase(clase: WorkItemClass) -> Autoridad:
    return _TABLA_AUTORIDAD[clase]   # KeyError explícito si falta la clase
```

Y el contrato lo dice sin rodeos (§11.1): **«Una clase que no aparezca aquí no
puede crear WorkItems hasta que se añada.»**

Por tanto, un WorkItem de clase `aprendizaje` exigiría, a la vez:

1. modificar `WorkItemClass` en `main` (dominio);
2. modificar `_TABLA_AUTORIDAD` **en la rama de A5** — prohibido por el encargo;
3. enmendar el contrato operativo v1.7 §11.1 — decisión del propietario
   (ADR-041).

Esto **activa el criterio de parada 2** de ADR-043. La consecuencia de diseño es
limpia y no es un rodeo: **el aprendizaje v0 no crea WorkItems.**

### 3.9 Frontera `sirius` ↔ `sirius_engine`

`tests/engine/test_boundary.py` prohíbe las importaciones en ambos sentidos, por
AST. Verificado. Implica que el modelo de memoria/decisiones de V4 (§2.3) es
**referencia de diseño, no biblioteca**.

---

## 4. Qué está demostrado en Sirius, y de qué forma podría reutilizarse

Esta sección sustituye a la primera redacción, que titulaba «qué ya existe y se
reutiliza tal cual» y contaba piezas. Contar piezas confundía **patrón
demostrado** con **componente disponible**, que es exactamente el error que este
mismo informe le reprocha al brief. La corrección está en §14.4, C-3.

La forma correcta de mirarlo es por **mecanismo requerido**, y clasificando cómo
se podría reutilizar cada uno:

| | Forma de reutilización |
|---|---|
| **A** | **Reutilización física directa** — el código se usa tal cual, sin cruzar ninguna frontera |
| **B** | **Extracción de una primitiva compartida** — hay lógica común que merece vivir en un sitio neutral del que dependan ambos lados |
| **C** | **Reutilización mediante adapter o puerto** — el mecanismo sirve, pero tiene que entrar por una interfaz del Work Engine |
| **D** | **Reutilización solo conceptual** — lo que viaja es el invariante o la regla, no el código |
| **E** | **Implementación nueva justificada** — no existe nada equivalente, o lo existente no puede cruzar |

Regla que gobierna la clasificación: **reuse before build, pero también
abstraction before coupling.** Una reutilización física que obligue al motor a
depender de la vía GitHub, de `gh`, del formato de un veredicto de PR o de
`src/sirius` **no es una ganancia**: es el acoplamiento que ADR-019 y ADR-020
separaron a propósito, y que `tests/engine/test_boundary.py` hace cumplir.

### 4.1 La clasificación

**Aviso sobre esta tabla: la columna «forma» es una hipótesis de trabajo, no un
resultado.** Determinarla de verdad es la investigación D-9 (§12), y varias filas
solo se pueden cerrar con datos que hoy no existen.

| Mecanismo que el aprendizaje necesitaría | Qué hay ya, y dónde | Estado real | Forma |
|---|---|---|---|
| Historia durable e íntegra de lo ocurrido | Diario JSON Lines con checksum por registro y `fsync`, `sirius_engine/adapters/durable/journal.py` | Construido, misma capa. **Sin un solo registro en disco** | **A** |
| Reconstruir «qué pasó» sin reejecutar nada | `rebuild_state()`, `domain/events.py:58`; `list_events()`, `ports/store.py:202` | Construido, función pura | **A** |
| Recuperación determinista antes de gastar IA | `contexto.recuperar`, `context_recall.py`: tres proveedores, ningún LLM, cita en vez de sintetizar | Construido, pero **no es llave en mano**: `recuperar_contexto(...)` exige que el llamador le pase ya montados el puerto de GitHub, los números de incidencia y las entradas de `git log`. Y un proveedor no puede reportar su fallo (H-5) | **A** para la función; **C** para poder usarla de verdad, porque falta quien ensamble sus insumos |
| «Una lectura caída no es una ausencia» | ADR-036, más `proveedores_fallidos` | **Invariante demostrada**, implementada en dos de tres proveedores | **D** + defecto |
| Filtro de fuente no confiable | `es_autor_de_confianza`, `mirror_projection.py:80-82` | Construido para comentarios. El cuerpo de la incidencia lo esquiva y el puerto impide arreglarlo (H-1) | **A** para lo que cubre; **E** para lo que no |
| Least privilege por perfil, deny-by-default | `PermissionEnvelope` + Resolver + registro cerrado de capacidades | Construido y **encadenado** por `project_worker_request` (`worker_request.py:65-67`), pero **esa proyección no la llama nadie en `src/`**: las guardas no corren en producción. El mecanismo de ámbitos sí está en uso como dato —`reviewer.yml` declara `escritura: veredicto` y por eso no resuelve `repo.escribir`—; lo que falta para el conocimiento activo es **un ámbito propio**, no el mecanismo | **C** — falta el llamador, no la pieza |
| Egress fail-closed por fragmento | `egress.py:25` | Construido y llamado desde la proyección (`worker_request.py:66`), pero **en todo `src/` no se construye ni un `ContextFragment`**: sin fragmentos que validar, la guarda no protege nada en producción | **C** |
| Perfiles sustituibles sin modelo dentro | `AgentProfile` + `profile_registry` | Construido. Sin identidad de modelo/runtime (GAP-1, §5) | **A**, con la divergencia abierta |
| Refutación obligatoria por hallazgo | ADR-010: cada hallazgo exige evidencia **e intento de refutación** | **Es una regla, no un componente** | **D** |
| Dos revisores de proveedores distintos + agregación determinista que falla cerrado | `scripts/automation/sirius_aggregate_reviews.py` | Construido y probado (`tests/automation/test_sirius_aggregate_reviews.py`). **Corregido en la ronda 3**: la redacción anterior lo descalificaba diciendo que estaba «acoplado a `gh` y al ciclo de etiquetas», y **eso es falso** — el fichero importa solo `argparse`, `json`, `re`, `sys`, `typing`, y no toca `gh`, etiquetas, red ni entorno. Su acoplamiento real es al **esquema del veredicto JSON** y al concepto de `reviewed_head_sha`. Su ejecución en modo dual depende además de la variable de repositorio `SIRIUS_CODEX_REVIEW_ENABLED` (`review-sirius-work.yml:95,100-104`), cuyo valor no está en el árbol (I5 del plan) | **B** — es el mejor candidato a primitiva compartida de toda la tabla, precisamente porque es Python puro y determinista |
| Aprobación ligada al cambio exacto | `sirius_apply_verdict.sh:15-17`: coincidencia exacta entre el SHA declarado, el head de la PR y el último head que superó Quality | Construido y operando, **en bash**, atado a `reviewed_head_sha` y a una PR | **D** — el invariante viaja, el mecanismo no |
| Fuente externa tratada como dato, nunca como instrucción | `sirius_aggregate_reviews.py:20-21`, explícito en su contrato | Construido | **D** |
| Conocimiento versionado con procedencia obligatoria, corrección por revisión nueva, supersede y archivado reversible | `src/sirius/domain/{memory,decision,precedence}.py` (V4) | Construido y probado, **al otro lado de una frontera que una prueba hace cumplir** (`tests/engine/test_boundary.py`) | **D**; **B** o **C** solo si el propietario decide abrir esa vía. **Nunca A** |
| Detección determinista de contradicciones y solapamientos (lo que el brief llama Curator) | `src/sirius/domain/precedence.py`: nombra a todos los implicados, nunca elige ganador en silencio | Construido, misma frontera | **D**; **B**/**C** con decisión |
| Presupuesto con corte determinista y escalado | `a5:governance.py` + `a5:domain/budget.py` | Construido **en una rama sin fusionar**, y **roto fuera de `ACTIVE`** (H-3). Además `Budget` no se persiste | **C** si algún día sirve; hoy no sirve para esto |
| Canal para presentar una propuesta al propietario | `a5:ports/notification.py` | Construido, pero **solo transporta `Escalada`**, y sus siete causas son cerradas por arquitectura §10 | **E**, o una decisión de contrato |
| Staging durable de candidatos | Patrón de escritura seguro de S1 (ADR-026), ya probado | El patrón está demostrado; el almacén enumera `WorkItem` y `Run` en su códec | **B** (extraer la primitiva de escritura) o **E** |
| Conocimiento activo del motor (MEMORY/SKILL) | — | No existe | **E**, y además bloqueado por D-4 (¿segunda memoria?) |
| Identidad de modelo/runtime por Run | — | No existe. Es divergencia con arquitectura §3.3 (GAP-1) | **E**, pero **no es una necesidad del aprendizaje**: ver §5 y D-6 |

### 4.2 Qué se concluye de verdad de esa tabla

1. **La reutilización física directa (A) es poca y toda de lectura dentro del
   propio motor.** Enumerada sin «se limita a»: `rebuild_state`
   (`domain/events.py:58`), el filtro de autor (`mirror_projection.py:80`, que
   `context_recall.py` ya reutiliza), y `AgentProfile` + `profile_registry` como
   dato versionado. El diario **no** es A limpia: ver §6.5. Y `contexto.recuperar`
   es A como función y **C** para usarla de verdad, porque nadie ensambla hoy sus
   insumos. Es real y es útil, y es mucho menos de lo que las dos primeras
   redacciones de este informe daban a entender.
2. **De `scripts/automation` sale el mejor candidato a primitiva compartida, y
   la primera redacción lo descartó con un motivo falso.** `sirius_apply_verdict.sh`
   sí está atado a la vía GitHub (es bash y habla con la PR): eso es **D**. Pero
   `sirius_aggregate_reviews.py` **no**: es Python de biblioteca estándar, sin
   `gh`, sin etiquetas, sin red y sin entorno, y su regla de agregación es una
   función determinista sobre dos veredictos y un SHA. Es **B**, y merece
   evaluarse como tal en D-9.
3. **Todo lo que viene de `src/sirius` es D por defecto**, y solo pasa a B o C con
   una decisión del propietario, porque la frontera está comprobada por una
   prueba, no sugerida por un documento.
4. **Dos mecanismos centrales están construidos y encadenados, pero su
   proyección no la llama nadie** (permisos y egress): `project_worker_request`
   solo se invoca desde las pruebas. Eso no es reutilización pendiente: es
   **trabajo del propio Work Engine** que el plan sitúa en C2/C3.
5. **Lo que el aprendizaje necesitaría y no existe en ninguna forma** son tres
   cosas: conocimiento activo del motor, un canal para presentar una propuesta, y
   un staging durable. Las tres son **E** o **B**.

La frase que resume el resultado, y que sustituye a cualquier recuento de piezas:

> **No debemos reinventar mecanismos que Sirius ya ha demostrado, pero todavía
> hay que decidir qué se reutiliza conceptualmente, qué puede reutilizarse
> físicamente y qué requiere una implementación propia detrás de las interfaces
> del Work Engine.**

Esa decisión es D-9 (§12), y es una investigación, no un párrafo.


---

## 5. Gaps mínimos

Ordenados por lo que bloquean. «Mínimo» significa: sin esto, la garantía
correspondiente no se puede afirmar.

**GAP-1 — Identidad estructurada de Worker/modelo/runtime por Run.**
`Run.worker` es una cadena libre (`domain/run.py:71`); ni `AgentProfile`
(`domain/profile.py:36-48`) ni `WorkerRequest` (`worker_request.py:44-54`) llevan
modelo. La arquitectura §3.3 sí lo pide: «worker: adapter + perfil + (si aplica)
**modelo/runtime concretos usados**».

**Esto se registra como divergencia general respecto de la arquitectura
aprobada, no como una necesidad inventada por el aprendizaje.** Vale por sí
misma, sin que exista ningún Learning System: sin ese dato el motor no puede
comparar dos Runs, ni explicar en qué se diferenció una sustitución de Worker,
ni sostener ninguna afirmación sobre qué modelo produjo qué — que es justo lo
que arquitectura §6 regla 3 pide cuando dice que «dos runs solo son comparables
si su resolución coincide».

Que además sea la condición de la invariante «Refutador con modelo distinto»
(§2.2) es una **consecuencia**, no la razón.

*No se implementa aquí* (esta rama no toca `src/`). Debe resolverse **cuando
nazca el dato, en el primer adapter o Worker real**, salvo que el plan o el
propietario decidan otra cosa. Ese momento es el de B1 o C2 según el plan
vigente; fijarlo con más precisión es decisión de quien lleve esos bloques.

**GAP-2 — `WorkPackage`/`WorkResult` sin esquema.** Son `Mapping` opacos (§3.3).
Un Extractor que lea `no_comprobado` o `comprobaciones` lee campos que nadie
valida. Se cierra igual que GAP-1: al haber un Worker que los produzca.

**GAP-3 — No hay canal para presentar una propuesta al propietario.**
`NotificationPort` solo transporta `Escalada`, y las siete causas son cerradas
(§3.7). Una aprobación ligada a un hash exacto no tiene por dónde llegar.

**GAP-4 — El almacén no admite una entidad nueva sin tocarlo.**
`entity_codec.py` enumera `WorkItem` y `Run` explícitamente; `WorkEngineStore`
(`ports/store.py`) tiene una firma por transición. Un `LearningCandidate`
persistido *dentro* del motor exige tocar puerto, códec y almacén durable.
**Alternativa que evita el gap entero**: que el staging viva **fuera** del
almacén del motor, en su propio fichero append-only con el mismo patrón de
escritura ya probado (S1/ADR-026). El motor no debe poseer el estado del
aprendizaje: el aprendizaje no es trabajo del motor.

**GAP-5 — No hay puerto de Worker.** Sin `START/STATUS/RESULT/CANCEL` (§1.2) no
hay ninguna forma de ejecutar al Extractor ni al Refutador **como Workers
gobernados**. Ejecutarlos por fuera del contrato sería exactamente la vía
paralela que ADR-020 prohíbe.

**GAP-6 — No hay corpus.** Cero WorkItems reales ejecutados. Es el gap que
ningún diseño cierra y ninguna prisa acorta.

**GAP-7 — Presupuesto no persistente.** `Budget` lo lleva el llamador (§3.7): el
coste del aprendizaje es gasto nuevo y sin cauce contable propio.

**GAP-8 — La imposibilidad de escribir conocimiento activo es expresable, pero
no está en vigor.** La primera redacción de este informe la sacó de la lista de
gaps diciendo que «ya se puede expresar». Se puede expresar, y **no corre**: la proyección de A4 **sí está ensamblada** en `src/`: `project_worker_request`
(`worker_request.py:57`) encadena envelope, egress y resolución de capacidades
(`worker_request.py:65-67`). Lo que **no existe es ningún llamador de esa
proyección**: solo la invocan las pruebas. Ningún camino de ejecución del motor
construye un `WorkerRequest`, así que las tres guardas nunca corren en
producción (§3.6). Y
`PermissionEnvelope.escritura` es un nombre de ámbito, no una ruta: separar
«puede escribir su staging» de «no puede escribir conocimiento activo» exige un
ámbito propio que hoy no existe en el registro.

---

## 6. Dónde enganchar el aprendizaje, y por qué ahí

### 6.1 Las cuatro opciones reales, evaluadas

| Opción | Dónde | ¿Rompe un WorkItem entregado si falla? | ¿Toca el dominio? | ¿Toca A5? | ¿Exige clase nueva? | Veredicto |
|---|---|---|---|---|---|---|
| **O1** Dentro de la transición | `domain/work_item.py:186` `deliver()` | **Sí** | Sí | No | No | **Descartada**: el dominio es puro y sin efectos; un fallo del sidecar viviría dentro de la entrega |
| **O2** Dentro del puerto de almacén | `ports/store.py:73` `deliver_work_item()` | **Sí** | Puerto | No | No | **Descartada**: obliga a todas las implementaciones y mete el aprendizaje en la transición terminal |
| **O3** WorkItem de clase `aprendizaje` despachado por el motor | `WorkItemClass` + `_TABLA_AUTORIDAD` | No | Sí | **Sí** | **Sí** | **Descartada**: prohibida por el encargo y por el contrato §11.1; además convierte al aprendizaje en trabajo del motor y al sidecar en actor con autoridad |
| **O4** Lector del diario, fuera del camino de escritura | `ports/store.py:202` `list_events()` — **por el puerto, nunca leyendo el fichero** | **No** | **No** | **No** | **No** | Mejor clasificada (§6.2), con las garantías acotadas en §6.5 |
| **O5** WorkItem de una clase **ya existente** con autoridad `motor` (p. ej. `MIXTA` o `CONSULTA_LARGA`) | `a5:domain/authority.py`, filas ya presentes | No | No | No | **No** | Descartada **con argumento, no por imposibilidad** — ver abajo |

**Sobre O5, y sobre un error de la primera redacción.** Las dos versiones
anteriores presentaban «el aprendizaje v0 no es un WorkItem» como una
**consecuencia forzada** por la tabla de autoridad y el contrato §11.1. La ronda
3 lo refutó y tiene razón: el bloqueo solo aparece si la clase se llama
`aprendizaje`. La tabla de A5 ya asigna autoridad `motor` a `CONVERSACION_NO_APLICA`,
`INVESTIGACION`, `DOCUMENTACION`, `CONSULTA_LARGA` y `MIXTA`, así que un WorkItem
de aprendizaje **podría** nacer bajo una de ellas sin tocar el enum, ni la tabla,
ni el contrato.

Se descarta igualmente, y con argumento explícito:

1. `clase` es un campo **descriptivo** que alimenta la autoridad y la proyección
   (arquitectura §3.1). Meter aprendizaje bajo `MIXTA` haría que la tabla de
   autoridad describiera mal el trabajo que gobierna — el defecto es de
   honestidad del modelo de datos, no de permisos.
2. Convertirlo en WorkItem devuelve al motor la propiedad de su ciclo de vida y
   lo mete en la cola de presupuesto y despacho: justo lo que O4 evita, y lo que
   hace que un fallo del aprendizaje pueda tocar el estado del motor.
3. El contrato §9 sigue prohibiendo iniciar trabajo sin orden del propietario, así
   que cada WorkItem de aprendizaje necesitaría su orden de todos modos: la
   supuesta ventaja de «entrar por el cauce normal» no ahorra nada.

Los tres son argumentos, no pruebas. **Que O5 quede descartada es una decisión de
producto**, y sube como tal (§12, D-2).

### 6.2 La opción mejor clasificada — que **no** es lo mismo que recomendarla

> **Si algún día se construye**: el aprendizaje v0 es un lector del diario, no un
> actor del motor. No tiene hook, no tiene estado en el motor, no crea WorkItems,
> no escribe nada activo, y se invoca por una orden del propietario.

**Corrección de la ronda 2 (§16)**: la primera redacción marcó esta opción como
«RECOMENDADA». No lo es, y etiquetarla así era responderme sola una pregunta que
no me toca. La comparación de §6.1 puntúa seis ejes **todos internos al motor**
(rompe lo entregado, autoridad, puerto, dominio, A5, clase nueva) y **omite el
único criterio de parada que ata a este repositorio**: `AGENTS.md` obliga a
detenerse ante «introducir otro proceso, servidor, agente o base de datos», y
esta opción introduce **un staging propio** y **un punto de entrada que no
existe** (`pyproject.toml` declara `sirius`, `sirius-voz` y `sirius-obs`, ninguno
del motor). Los dispara los dos.

Lo que queda en pie es el **orden**: O4 sobre O1, O2 y O3 es correcto y ninguna
de las cuatro lentes adversariales lo refutó. Lo que cambia es el estatus: **de
recomendación a pregunta al propietario** (§12, D-1).

Cómo funciona, concretamente:

1. El propietario da una orden (`aprende de WI-2026-0007`, o «revisa lo cerrado
   esta semana»). **La orden es el disparo**, igual que lo es para cualquier otro
   trabajo (contrato §9: nada empieza sin orden del usuario).
2. Un lector determinista recorre el diario ya existente y selecciona los eventos
   relevantes: `work_item_delivered`, `work_item_cancelled`,
   `work_item_failed_safely`, `run_failed`, `run_marked_lost`, `run_retried`,
   `run_worker_substituted` (`domain/events.py:96-124`). Como el `Event` lleva la
   instantánea completa del agregado, **el dossier se construye sin consultar
   nada más**.
3. Ese dossier —compacto, con referencias, no con el historial entero— es la
   entrada del Extractor. El detalle se hidrata bajo demanda con
   `contexto.recuperar`, que ya cita en vez de sintetizar.
4. El resultado son cero o más candidatos, escritos en un **staging propio,
   fuera del almacén del motor**, con el patrón de escritura append-only +
   checksum + `fsync` que S1 ya demostró seguro (ADR-026). `NO_CANDIDATE` es un
   resultado sano y frecuente.
5. Nada más ocurre automáticamente.

### 6.3 Por qué este punto y no otro

- **No puede romper lo ya entregado.** No está en el camino de escritura de
  ninguna transición. Es la única de las cuatro opciones de la que eso se puede
  afirmar sin condiciones, y es una garantía explícita del brief §2.
- **No convierte al aprendizaje en coordinador.** No crea trabajo, no activa
  nada, no toca etiquetas, no observa nada vivo. Lee historia cerrada.
- **No exige tocar el dominio, ni el códec, ni A5.** *(Corregido en la ronda 3:
  decía además «ni el puerto», y eso o es falso o cuesta la garantía de solo
  lectura. Ver §6.5.)*
- **El motor sigue siendo dueño del estado**: el diario es la fuente y el lector
  no escribe. *(Corregido en la ronda 3: eso es hoy una **convención**, no una
  propiedad estructural. Ver §6.5.)*
- **Se entra por el puerto, nunca por el fichero.** El formato JSON Lines con
  checksum vive en `adapters/durable/journal.py`, que es **un detalle de un
  adaptador concreto**. Leerlo directamente ataría el aprendizaje a una
  representación que ADR-019 deja explícitamente abierta hasta D2. La única vía
  admisible es `WorkEngineStore.list_events()`. *(La primera redacción ofrecía las
  dos como equivalentes; era un acoplamiento accidental y se retira.)*
- **Reversibilidad total**: borrar el directorio de staging deja el sistema
  exactamente como estaba. No hay migración que revertir.
- **Coincide con el precedente que el repositorio ya validó**: A3 entró como
  **espejo de solo lectura** antes que C1 supervisara y C2 despachara. El
  aprendizaje debe entrar por la misma puerta, y en ese orden.

### 6.4 Lo que esta opción **no** resuelve, dicho antes de que lo pregunten

- **No es automático.** Ver §2.1: el disparo automático necesita enmienda de
  contrato o el servicio supervisado de D2. Esto es la fase manual del propio
  brief §10, no un recorte.
- **No cubre `FAILED_SAFELY` como «terminal»**, porque no lo es (§2, fila l). El
  lector puede seleccionarlo igualmente por su evento, pero conviene saber que
  ese WorkItem **puede reactivarse después**, y que un aprendizaje extraído de un
  fracaso que luego se resolvió es justo el que el adjunto 01 §3.7 avisa de no
  convertir en regla. Regla derivada: **de un `FAILED_SAFELY` no se extrae nada
  hasta que su WorkItem alcance un estado terminal de verdad.**
- **No hace verificable la independencia del Refutador** (GAP-1). Mientras no lo
  sea, el candidato **espera**, que es exactamente lo que el brief §8 manda.

### 6.5 Qué es estructural hoy y qué es solo convención

**Esta subsección es la corrección de raíz de la ronda 3.** Tres objeciones
independientes resultaron ser la misma: **el informe afirmaba como estructural
una garantía que hoy solo es convención** — exactamente el estándar que él mismo
exige en §10.1 («invariantes que deben ser imposibles de violar, no
improbables») y en §2.2 («una garantía que solo vive en un prompt no es una
garantía»). Se aplicaba una vara para el brief y otra para la propuesta propia.

Corregido de una vez, en vez de frase a frase:

| Garantía que la propuesta afirmaba | Qué es de verdad hoy |
|---|---|
| «El lector no puede escribir el estado» | **Convención.** `WorkEngineStore` (`ports/store.py:24`) es **un solo Protocol** con 36 métodos, de los que solo cinco son de lectura. Quien recibe el almacén para llamar a `list_events()` puede llamar igual a `cancel_work_item` o a `deliver_work_item`. **No existe ningún puerto de solo lectura** en `src/sirius_engine/ports/` |
| «El fichero solo se abre en `O_APPEND`, desde `append_durably`» | **Falso.** `adapters/durable/journal.py:165` exporta `recover_invalid_tail`, que abre en `os.O_WRONLY` (`:189`) y **trunca** (`:191`). El módulo que sabe leer es el mismo que sabe truncar |
| «No exige tocar el puerto» | **Incompatible con la anterior.** O se entra por `list_events()` —y entonces se sostiene un handle con las 31 escrituras— o se lee el fichero —y entonces se depende de una representación que ADR-019 deja abierta hasta D2. **No hay tercera vía en el código** |
| «El staging es reversible del todo y no acopla nada» | **Parcial.** Reutilizar el patrón de escritura de `adapters/durable/journal.py` para el staging es el mismo acoplamiento a un adapter concreto que §6.3 acaba de rechazar para la lectura, aplicado al revés. O es **E** con su coste dicho, o es **B** con la primitiva extraída de verdad |
| «`test_boundary.py` garantiza que B exige decisión» | **No lo garantiza.** Esa prueba compara **nombres de import directo** (`name == pkg or name.startswith(pkg + ".")`), no el grafo de dependencias. Un tercer paquete neutral del que dependieran los dos lados dejaría las dos pruebas en verde creando justo la dependencia compartida que la frontera existe para impedir. La frontera es **norma**, no garantía, para la ruta B |
| «Se entra por el puerto» resuelve el acoplamiento | **Lo traslada.** No existe ningún composition root del motor: `DurableWorkEngineStore` solo se instancia en pruebas. Quien construya el almacén decide qué adapter usa el motor y dónde vive su diario — y hoy ese primero sería el sidecar de un vertical no autorizado |

**Lo que sobrevive intacto** de §6.1–§6.4, y conviene decirlo para no tirar lo
bueno con lo malo: el **orden** de las opciones. O4 sigue siendo la única de las
cuatro que no toca el dominio, ni el códec, ni A5, y la única de la que se puede
afirmar sin condiciones que un fallo del sidecar no rompe un WorkItem entregado.
Lo que cae no es la elección: son las garantías de más que se le colgaron.

**Lo que esto convierte en decisión del propietario** (§12, D-10): para que un
lector sea de solo lectura **de verdad** hace falta una interfaz nueva del motor
—un puerto de lectura del diario— y eso es alcance de C2/D2, no de una auditoría.

### 6.6 Por qué, aun siendo el punto correcto, no se construye todavía

El orden de las opciones de §6.1 es una conclusión técnica y sobrevivió a las
cuatro lentes adversariales. **La recomendación de calendario es otra cosa, y es
«todavía no».** Las razones no son el inventario de patrones de §4 —eso sería
confundir «hay algo parecido» con «está resuelto»—, sino cinco hechos:

1. **No existe todavía ningún Worker gobernado de extremo a extremo por el Work
   Engine.** No hay puerto de Worker (`ls src/sirius_engine/ports/` → sin él), no
   hay adapter de ejecución, y ningún workflow ni script referencia
   `sirius_engine`.
2. **No existe corpus.** Cero WorkItems reales; ningún diario en disco
   (`find . -name "*.jsonl"` no devuelve nada). Los únicos WorkItems que han
   existido son fixtures de prueba.
3. **Varias invariantes necesarias no son comprobables todavía** (§2.2 y §14.4):
   la independencia del refutador no tiene dato, y las guardas de permisos y
   egress, aunque encadenadas, no las ejecuta ningún camino de producción.
4. **Construir el pipeline ahora obligaría a decidir abstracciones sin datos
   reales**: la forma del dossier, el esquema del candidato, la deduplicación y
   los umbrales se decidirían contra fixtures inventadas, que es exactamente lo
   que el adjunto 01 avisa de no hacer.
5. **Primero tiene que avanzar el Work Engine hasta producir experiencia real.**
   Hasta entonces, cualquier lector del diario es un lector perfecto de un
   fichero vacío.

Ninguna de esas cinco se arregla diseñando mejor. Se arreglan avanzando el motor.
Por eso **no se propone ninguna fase**, ni un hueco reservado, ni una lista de
bloques: eso sería fijar una forma para un trabajo cuyos datos de entrada aún no
existen.

---

## 7. HISTORY / MEMORY / SKILL / GOVERNANCE: la separación, mapeada al repositorio

El encargo pide separarlas sin ambigüedad. Ya están casi todas, y con dueño.

| Capa | Qué es | Quién es su dueño hoy | Puede autoaprenderse |
|---|---|---|---|
| **HISTORY / EVIDENCE** | Lo ocurrido: WorkItems, Runs, tool calls, checks, reviews, reparaciones, artefactos | El motor. Diario append-only con checksum (`adapters/durable/journal.py`); espejo no autoritativo de GitHub (`mirror_projection.py`) | **No se aprende: se registra.** Es la fuente, nunca el producto |
| **MEMORY** | Hechos declarativos durables y contextualizados | Hoy: `src/sirius/domain/memory.py` para el producto. En el motor: **no existe** | Sí, como **candidato**; jamás activo sin aprobación |
| **SKILL** | Procedimiento reutilizable para una clase de trabajo | Ya definido por arquitectura §6 regla 6: proveedor del Resolver, **«nunca autoridad ni memoria»** | Sí, como candidato. Su promoción es una **frontera de seguridad** (adjunto 01, H-06) |
| **GOVERNANCE / DECISION** | Autoridad: producto, arquitectura, permisos, privacidad, presupuesto, orden del plan | El propietario, vía ADR y contrato operativo | **Nunca.** Ni como candidato |

Dos precisiones que el repositorio ya impone y conviene no perder:

1. **La cuarta capa no es «aprendizaje difícil», es una capa distinta.** ADR-041
   fija la autoridad *antes* de que exista el primer WorkItem; el contrato §11.1
   dice que una clase sin fila no puede crear WorkItems. Ninguna de esas cosas es
   un hecho que un modelo pueda proponer: son actos del propietario. La regla
   operativa que se deriva: **si un candidato, aplicado, cambiaría quién decide
   algo, qué se puede gastar, qué se puede exportar o qué permisos existen, no es
   un candidato — es una escalada.**
2. **Procedencia ≠ aplicabilidad, y el repositorio ya tiene la mitad.**
   `Memory.origin` es obligatorio y `MemoryRevision.source_event_id` enlaza con
   el hecho que lo originó (`src/sirius/domain/memory.py:36-42`). Lo que no
   existe en ninguna parte es la **aplicabilidad** (clase de tarea, capacidades,
   entorno, versiones, predicados). Al diseñarla, el campo debe nacer separado
   del de procedencia desde el primer día: fundirlos es el error que hace que «lo
   descubrió el Programador» se lea como «pertenece al Programador».

---

## 8. Dónde entra esto en el plan, y qué puerta hay que pasar antes

### 8.1 Lo que este informe **no** hace

No edita `SIRIUS_WORK_ENGINE_PLAN_IMPLEMENTACION.md`, ni el contrato operativo,
ni `docs/canonical/`, ni `docs/evolution/STATUS.md`, ni `src/`, ni `.github/`, ni
`scripts/`.

El predicado que lo comprueba —`git diff --name-only origin/main...HEAD`— y su
resultado vigente **viven en un solo sitio**: la sección «Comprobación que la
sostiene» de ADR-043. Aquí se enlaza y no se transcribe. *(La ronda 3 encontró
las dos copias anteriores divergidas: ambas decían dos ficheros cuando ya eran
tres. Es la familia que ADR-005 eliminó de V8, cometida por este mismo informe.)*


### 8.2 Por qué hace falta una puerta, y no solo una recomendación

La excepción vigente en `docs/evolution/STATUS.md:27-35` autoriza el Work Engine
**«estrictamente según ADR-020 y su plan aprobado»**, y mantiene explícitamente
sin autorizar «adoptar frameworks o proveedores no aprobados» y «cualquier
multiagente abierto más allá de la delegación supervisada descrita en ese
diseño». Un vertical de aprendizaje **no está en ADR-020 ni en su plan**. Por
tanto no está amparado, ni siquiera en su versión mínima. Necesita una decisión
del propietario que **amplíe la excepción**, exactamente igual que la
implementación del motor necesitó E0.

Además, `AGENTS.md` («criterio de parada») obliga a detenerse ante «introducir
otro proceso, servidor, agente o base de datos». El diseño de §6 evita el
proceso y la base de datos, pero **sí introduce perfiles de agente nuevos**
(Extractor, Refutador, Curator). Eso basta para exigir decisión.

### 8.3 Colocación: ninguna, todavía

**Corregido tras la ronda 2 y tras la revisión del propietario.** La primera
redacción proponía una «Fase L» con seis bloques después del hito M3. **Se
retira entera.** Proponer una fase es fijar la forma del trabajo, y §6.6 explica
por qué no hay datos para fijarla: no hay Worker gobernado, no hay corpus, y
varias invariantes no son comprobables. Una fase inventada sobre eso no ordena
nada — solo parece que sí.

Lo que sí se puede afirmar sobre colocación, y es todo:

- **No va dentro de ninguna fase aprobada**, y desde luego no dentro de A5.
- **No se reserva hueco ni número de bloque** en `PLAN.md`. Una fase no aprobada
  anotada como si lo estuviera es la deriva PROC-011 vista del revés.
- **Ni siquiera M3 es suficiente por sí solo**: M3 entrega tres clases de trabajo
  reales, pero **ningún bloque del plan programa GAP-1**, y sin ese dato la
  invariante del refutador independiente sigue sin ser comprobable.
- **Lo que decide el momento es la evidencia**, no el calendario: cuando existan
  WorkItems reales ejecutados por Workers reales, habrá con qué contrastar este
  diseño. Antes no.


### 8.4 Cuándo volver a mirar: la condición, no la fecha

«Todavía no» sin una condición comprobable no es una respuesta. Esto la fija.

**No hay fecha porque no hay dato para fijarla** — inventar un mes sería
exactamente lo que este informe le reprocha al brief. Lo que sí se puede fijar es
una **puerta observable**: siete condiciones, cada una comprobable con un comando,
sin juicio de nadie. Mientras alguna esté en `NO`, la respuesta sigue siendo
«todavía no», y no hace falta preguntar a nadie para saberlo.

#### La puerta

| # | Condición | Cómo se comprueba | Hoy |
|---|---|---|---|
| 1 | Existe **puerto de Worker** (`START/STATUS/RESULT/CANCEL`) | `ls src/sirius_engine/ports/` | **NO** |
| 2 | Existe **un adapter de Worker real** | `ls src/sirius_engine/adapters/` | **NO** |
| 3 | El diario tiene **registros reales en disco** | `find . -name "*.jsonl" -not -path "./.git/*"` | **NO** |
| 4 | El corpus tiene **las tres formas** de las que el aprendizaje extrae: un WorkItem entregado, uno fallado, y un Run con Worker sustituido | eventos `work_item_delivered`, `work_item_failed_safely`, `run_worker_substituted` en el diario | **NO** |
| 5 | **GAP-1 cerrado**: el Run lleva identidad estructurada de modelo/runtime | `grep -E "modelo\|runtime" src/sirius_engine/domain/run.py` | **NO** |
| 6 | **H-2 cerrado**: el observador puede decir «no pude mirar» | `grep UNKNOWN src/sirius_engine/ports/world.py` | **NO** |
| 7 | **H-3 cerrado**: el corte de presupuesto funciona fuera de `ACTIVE` | prueba de gobierno que parta de `WAITING` | **NO** |

Siete de siete en `NO`. Esa es la distancia real, y por eso no hay fecha.

#### Sobre la condición 4, que es la única que podría parecer arbitraria

No es un umbral estadístico inventado: es un **mínimo estructural**. El
aprendizaje extrae de tres formas de experiencia y solo de tres —algo que salió
bien y se puede reutilizar, algo que salió mal con alcance acotado, y algo que
falló con un Worker y funcionó con otro—. Si el corpus no tiene las tres, no hay
nada que contrastar y cualquier candidato se estaría midiendo contra una sola
forma. Cuántos de cada una hacen falta **es una decisión que se toma mirando los
primeros números**, no antes: el lector determinista de §6.2 no llama a ningún
modelo, así que contarlos es gratis.

#### Traducido al plan aprobado

Qué bloque entrega cada condición, según
`SIRIUS_WORK_ENGINE_PLAN_IMPLEMENTACION.md`:

| Condición | La entrega |
|---|---|
| 1 y 2 | **B1** (primer Worker externo real) |
| 3 y 4 | **C2** (despacho end-to-end de programación) + **C3** (documentación) — dos clases distintas |
| 5 (GAP-1) | **ningún bloque la programa hoy** — ver abajo |
| 6 (H-2) | A2/C1, como corrección de defecto |
| 7 (H-3) | A5, como corrección de defecto |

Entre hoy y ahí hay, por el plan vigente: **A5** (abierto y en rojo) y después
**S2, B1, E1b, S3, C1, C2, C3 y C4** — ocho bloques más, con los hitos M2 y M3
por medio.

#### El punto que hace que la puerta no se abra sola

**La condición 5 no la programa ningún bloque.** GAP-1 es una divergencia con la
arquitectura §3.3 que nadie ha asignado. Si no se engancha a **B1 o a C2** —que
es donde nace el dato, y es la decisión D-6—, entonces M3 llega, el resto de
condiciones se cumple, y la puerta **sigue cerrada indefinidamente** sin que
nadie sepa por qué.

Dicho al revés, que es como hay que leerlo: **el momento más temprano posible es
justo después de M3, y solo si GAP-1 se engancha a B1 o C2.** Si no se engancha,
no hay momento.

#### Qué hacer el día que las siete estén en `SÍ`

Nada automático. Volver a este informe, ejecutar el lector determinista —que no
llama a ningún modelo y por tanto no gasta— sobre el corpus real, mirar los dos
únicos números que la sombra puede producir (candidatos por WorkItem y porcentaje
`NO_CANDIDATE`) y **entonces** decidir D-1 con datos delante en vez de con este
diseño delante.


---

## 9. De manual a automático: el orden de activación, si alguna vez

Esto **no es un plan ni una secuencia de bloques** —§8.3 explica por qué no se
propone ninguna—: es el orden en que las capacidades tendrían que habilitarse
*si* alguna vez se construyeran, con la condición que deja pasar a la siguiente.
Se conserva porque fija una propiedad que sí importa hoy: **nada se activa por
sensación**.

**Etapa 0 — Sombra manual.**
El propietario ordena la revisión. Se generan candidatos. **Nada se activa.**
Ni siquiera se presenta como propuesta: se acumula y se mide.
*Salida*: haber visto WorkItems reales de **al menos dos clases distintas** y
tener medidas —no estimadas— **las dos métricas que la sombra sí puede producir**
(candidatos por WorkItem y porcentaje `NO_CANDIDATE`). Las otras siete de §10.3
no son puerta de esta etapa: no puede generarlas.

**Etapa 1 — Propuesta manual.**
Candidato → Refutador independiente → cambio exacto con hash → aprobación
humana → Promotion Gate → activo. Sigue sin haber nada automático salvo la
generación del candidato.
*Salida*: una tasa de rechazo humano que el propietario considere aceptable, y
cero incidentes de las invariantes de §10.1.

**Etapa 2 — Mantenimiento.**
Curator entra, con cuarentena reversible. Toda corrección suya vuelve al mismo
pipeline de candidato → refutación → aprobación.
*Salida*: cuarentenas correctas y reversibles, verificadas.

**Etapa 3 — Auto-promoción por clases (DISEÑADA, DESACTIVADA).**
Debe quedar escrita desde el primer día como destino y **no activarse**. El
criterio se decidirá con métricas reales de Sirius. **No se inventa ningún
umbral en este informe**, y recomiendo desconfiar de cualquiera que aparezca sin
datos detrás.
Restricción permanente, sea cual sea el umbral: **automatizar la promoción no
automatiza el gobierno.** Seguridad, permisos, privacidad, autoridad y
arquitectura siguen el contrato y los ADR, siempre.

---

## 10. Pruebas y puertas antes de activar nada

### 10.1 Invariantes que deberían ser imposibles de violar, no improbables

**Corregido en la ronda 3, y es una corrección incómoda.** La redacción anterior
presentaba trece invariantes como si fueran comprobables y prometía prueba por
mutación «para todas». Ni una cosa ni la otra:

- **Solo una (I9) es comprobable hoy**, y ya se cumple sin trabajo: el
  `work_package` es una instantánea real —`MappingProxyType(dict(...))` en
  `run.py:238`—, así que mutar el dict del llamador después de `prepare_run` no
  cambia ni el Run ni el evento del diario. Verificado ejecutándolo.
- **Las otras doce vigilan objetos que no existen**: no hay candidato, ni
  staging, ni Gate, ni conocimiento activo, ni un solo registro en el diario.
- **Tres no son invariantes**: I4, I7 y I13 describen comportamiento de un modelo,
  no una propiedad estructural, y no admiten mutación determinista. Son
  **fixtures de evaluación** y su sitio es §10.2.
- **La promesa de mutación solo se sostiene para las estructurales**: I3, I10,
  I11 y I12.

Se conserva la lista porque es una **lista de comprobación útil para quien
algún día construya esto**, no porque describa un estado verificable. Cada fila
lleva ahora de qué depende.

| # | Invariante | Cómo se hace estructural (no por prompt) |
|---|---|---|
| I1 *(depende de GAP-8; absorbe I8)* | Un modelo de aprendizaje no puede escribir conocimiento activo | El perfil declara `permisos.escritura: null`; la escritura de conocimiento es una capacidad registrada con `ambitos_escritura: [conocimiento]`. El Resolver la rechaza por dos guardas independientes (§3.6). Mutación: dar el ámbito al perfil y ver la prueba fallar |
| I2 *(depende de GAP-1)* | No se promueve sin Refutador de modelo distinto | **Hoy imposible de comprobar** (§2.2). Prueba pendiente de GAP-1. Mientras tanto, el Gate **debe fallar cerrado**: sin dato de modelo, no promueve |
| I3 | Una aprobación no permite aplicar un diff distinto | El Gate recalcula el hash del cambio materializado y lo compara con el aprobado. Mutación: alterar un byte y ver que no promueve |
| I4 *(no es invariante: fixture)* | Un fallo transitorio no produce una prohibición general | Fixture: `run_failed` seguido de `run_retried` con `SUCCEEDED`. El candidato negativo, si existe, debe nombrar el recovery, no el fallo |
| I5 | Dos WorkItems que descubren lo mismo no crean dos conocimientos activos | *(La celda anterior repetía la invariante en voz activa en vez de dar un mecanismo.)* El único mecanismo demostrado en Sirius es deliberadamente conservador: `sirius_aggregate_reviews.py:17-19` **solo** elimina duplicados exactos —misma fuente, mismo fichero, mismo cuerpo normalizado— «porque es preferible conservar dos hallazgos parecidos con su procedencia que borrar uno incorrectamente». Ese es el punto de partida, no un algoritmo semántico |
| I6 | Un candidato rechazado no vuelve idéntico | El rechazo se conserva con motivo y hash; reabrir exige evidencia materialmente nueva |
| I7 | Una fuente maliciosa no convierte texto fuente en instrucción persistente | La evidencia entra como **dato citado**, nunca como instrucción. Reutiliza `es_autor_de_confianza` y el patrón de `Referencia` (cita, no síntesis) |
| ~~I8~~ | *Fundida en I1 en la ronda 3: su propia celda decía «mismo mecanismo que I1», así que eran una invariante contada dos veces* | — |
| I9 | Una actualización de conocimiento no cambia el snapshot de un Run en marcha | El `WorkPackage` ya es «instantánea exacta de lo enviado» (`run.py:72`), inmutable por diseño. La versión del conocimiento se fija ahí |
| I10 | Un fallo de aprendizaje no convierte un WorkItem entregable en fallido | Estructural por §6: el lector está fuera del camino de escritura. Mutación: hacer explotar el lector y comprobar que el WorkItem sigue `DELIVERED` |
| I11 | El Promotion Gate falla cerrado | Cualquier dato ausente (refutador, hash, procedencia, clasificación) **no promueve**. Mutación: quitar cada dato por turnos |
| I12 | Ningún aprendizaje eleva permisos, egress, presupuesto ni autoridad | **Corregido (ronda 3): lista de permitidos, no de prohibidos.** Enumerar rutas prohibidas es «una regla que enumera vehículos» (ADR-033) — la anterior ya se dejaba fuera `.github/**`, que es hoy la única superficie que restringe de verdad a un Worker. El Gate rechaza **todo** cambio fuera del conjunto explícito de rutas de conocimiento, igual que el envelope concede «exactamente las capacidades que el perfil declara, ni una más» |
| I13 *(no es invariante: fixture; depende de GAP-1)* | Un aprendizaje negativo nace estrecho, y eso no depende del buen juicio del modelo | **Reescrita en la ronda 3**: comprobar que los campos *estén presentes* lo satisface cualquier texto de relleno. Lo que hay que comprobar es **contraste**: que el `negative_scope` **coincida** con la identidad registrada en el Run. Y eso no se puede hoy, porque esa identidad no existe (GAP-1). Se declara **no sostenible hoy**, con el mismo criterio de parada 3 que I2 |

I12 merece una nota: es la traducción mecánica de «GOVERNANCE nunca se
autoaprende» (§7). Una lista de rutas prohibidas es comprobable; una promesa de
buen juicio no.

### 10.2 Fixtures mínimas de evaluación

**Corregido en la ronda 3.** La redacción anterior decía que las diez «ahora se
pueden construir como secuencias de eventos del diario». Es cierto solo para
cuatro: fallo de un Worker y éxito de otro (`run_worker_substituted`), fallo
transitorio seguido de reintento correcto (`run_failed` → `run_retried`),
corrección del revisor (`work_item_repair_requested`) y éxito sin nada nuevo. Dos
más dependen de que `WorkResult` tenga esquema (GAP-2) y las otras cuatro
dependen de objetos que no existen. Las diez siguen siendo las fixtures
correctas; lo que no es cierto es que ya se puedan escribir. Éxito con técnica reutilizable; éxito sin nada nuevo; fallo de un
Worker y éxito de otro (`run_worker_substituted`); fallo por credencial/setup;
fallo transitorio seguido de reintento correcto (`run_failed` → `run_retried`);
corrección del revisor (`work_item_repair_requested`); candidato duplicado;
candidato que contradice conocimiento activo; candidato atractivo sin evidencia;
evidencia con inyección de prompt.

### 10.3 Métricas de sombra (se miden, no se fijan)

**De las nueve, solo dos son medibles en la etapa de sombra** —candidatos por
WorkItem y porcentaje `NO_CANDIDATE`—: las otras siete necesitan un Refutador,
un humano aprobando o conocimiento activo que cuarentenar, y ninguna de esas
cosas ocurre en sombra. La salida de la Etapa 0 se lee con esas dos, no con las
nueve.

Candidatos por WorkItem; porcentaje `NO_CANDIDATE`; rechazados por el humano;
rechazados por el Refutador; duplicados; reaperturas por evidencia nueva;
promocionados y luego cuarentenados; coste y tiempo **por candidato útil**;
desacuerdo entre modelos. **Ningún umbral se fija en este informe.**

### 10.4 Puertas documentales que este trabajo ya tuvo que pasar

`tests/automation/test_registro_de_decisiones.py` (numeración de ADR única) y
`tests/unit/test_pa_sp_traceability.py` (trazabilidad requisito–prueba). La
primera es la que hoy tiene A5 en rojo (§1.3).

---

## 11. Pasada adversarial contra mi propia propuesta

Ronda 1, hecha por mí contra el diseño de §6 antes de entregarlo. Cada objeción
se intentó **demostrar**, no plantear. Las correcciones aplicadas están marcadas
como tales; las objeciones que sobreviven se dicen sin adornos.

### A1 — «Esto es el Auditor otra vez, con el diario en vez del repositorio»

**Intento de demostración.** ADR-010 define un componente que: lee solo; produce
hallazgos estructurados; **exige a cada hallazgo evidencia concreta e intento de
refutación**; y cuyos hallazgos **no se convierten en trabajo automáticamente**.
Mi Extractor lee solo, produce candidatos con evidencia, cada uno se refuta, y
ninguno se activa solo. Las formas son casi la misma forma.

**Veredicto: la objeción acierta en la cabeza del pipeline y falla en la cola.**
El Auditor audita *el repositorio* y entrega un informe que muere cuando el
propietario lo lee. El Extractor audita *trabajo ya ejecutado* y produce un
artefacto durable que puede convertirse en conocimiento activo. La diferencia
real es el tramo `staging → Gate → activo`, que el Auditor no tiene.

**Corrección aplicada**: el Extractor y el Refutador **no inventan un arnés nuevo**. Reutilizan el
patrón de perfil y el esquema de hallazgo del Auditor (`AUDITOR_AGENT_V0.md`,
`FINDING-###` con evidencia + refutación) y añaden solo los campos que el
Auditor no necesita: aplicabilidad, alcance negativo, cambio exacto y hash. Si
al construirlo resulta que el Extractor **es** el Auditor con otro perfil, mejor:
eso es una capacidad, no un subsistema.

### A2 — «El Refutador es un revisor más con otro nombre»

**Intento de demostración.** *(Precisado en la ronda 3: la redacción anterior
decía «el motor ya tiene… un Worker de perfil independiente», y eso mezclaba lo
construido con lo escrito.)* El motor tiene la **fase** `REVISAR`
(`domain/work_item.py:44-52`) con sus transiciones en el puerto
(`ports/store.py:90-102`) y un perfil `reviewer` como dato versionado
(`perfiles/reviewer.yml`). El **Worker** que la ejecuta y la salida cerrada
`APPROVED | CHANGES_REQUIRED | DECISION_REQUIRED` viven hoy en la vía GitHub, no
en el motor: el motor no tiene puerto de Worker. Aun así, el mecanismo —perfil
independiente, contrato de salida cerrado, el revisor no arregla lo que revisa—
está demostrado, y el Refutador es exactamente eso.

**Veredicto: la objeción acierta en el mecanismo.** Lo que el Refutador añade no
es un componente: es **una exigencia de independencia más fuerte** (modelo
distinto) sobre un mecanismo que ya existe.

**Corrección aplicada**: el Refutador se especifica como **un perfil que usa el
contrato de revisión existente**, no como una pieza nueva. Y su única exigencia
propia —modelo distinto— es justo la que hoy **no se puede comprobar** (§2.2).
Dicho de otro modo: el Refutador no es trabajo nuevo; **GAP-1 sí**.

### A3 — «El Evidence Dossier es una vista que ya existe»

**Intento de demostración.** `rebuild_state()` reconstruye un WorkItem completo
desde el diario, de forma determinista y con la instantánea entera en cada
evento. Un «dossier» sería una proyección sobre eso.

**Veredicto: la objeción es correcta, y encontró un defecto en mi diseño.** Yo
estaba a punto de describir el dossier como un artefacto. Si se persiste, pasa a
haber **dos relatos de lo ocurrido** —el diario y el dossier— que pueden
divergir: la familia exacta que ADR-005 eliminó de V8.

**Corrección aplicada**: el Evidence Dossier es una **función pura sobre
eventos**, se calcula cada vez y **no se persiste nunca**. Si hace falta
reproducirlo, se reproduce desde el diario, que ya lleva checksum por registro.

### A4 — «Estás construyendo la segunda memoria de Sirius» — **objeción que sobrevive**

**Intento de demostración.** La arquitectura §9 dice que el sustrato de memoria
«ya existe en el producto (`knowledge_fts` + ranking determinista + presupuesto
de contexto en `src/sirius/application/`)» y que **exponerlo como capacidad es
trabajo futuro sobre código existente**. Mi propuesta crea una MEMORY activa del
motor. Si algún día `contexto.recuperar` consulta la memoria del producto,
Sirius tendrá **dos memorias** con dos ciclos de vida y dos autoridades.

**Veredicto: la objeción sobrevive entera. No la puedo cerrar con evidencia.**
La frontera `test_boundary.py` impide compartir el código, pero no impide —ni
resuelve— compartir el *concepto*. Construir la MEMORY del motor antes de decidir
si la memoria del producto debe servir al motor es exactamente el error de
ADR-005 cometido a mayor escala.

**Consecuencia aplicada al diseño**: **el conocimiento activo del motor queda
bloqueado** hasta que el propietario decida la pregunta de arquitectura §9. Todo
lo anterior —leer, extraer, refutar, proponer— no lo necesita: produce
candidatos y propuestas, no conocimiento activo. Es una decisión real, y sube
como tal (§12, D-4).

### A5 — «Un lector que hay que invocar a mano no es aprendizaje, es un informe»

**Intento de demostración.** Si el disparo es una orden, y el propietario no la
da, no se aprende nada y el vertical entero es teatro.

**Veredicto: la objeción es justa en la fase 0, y aun así la fase 0 se sostiene.**
Lo que la fase 0 entrega no es aprendizaje: es **medición**. Y tiene una virtud
que la versión automática no tiene: si el propietario nunca la invoca, eso **es
el dato** que dice que no hay que construir el resto — obtenido por el precio de
un lector de ficheros, no por el de un pipeline entero. Lo automático cuesta hoy
una enmienda de contrato (§2.1) sobre un corpus que no existe (GAP-6). El orden
correcto es ese, no el inverso.

### A6 — «Encarece el sistema sin valor demostrado»

**Intento de demostración.** Refutar cada candidato exige un modelo fuerte. Con
corpus cero, el coste por candidato útil no está definido — ni siquiera acotado.
Y `Budget` no se persiste (§3.7): el sidecar **no tiene** presupuesto al que
cargarse.

**Veredicto: la objeción acierta, y no se resuelve con diseño.** Se resuelve con
una decisión de gasto del propietario, que es la causa 2 de escalado. Sube a §12
(D-3). Añado la restricción que sí puedo poner: **la fase 0 no llama a ningún
modelo caro sin tope explícito**, y el corte, al no poder vivir en el `Budget`
del WorkItem, tiene que ser un tope propio y declarado.

### A7 — «El staging es un segundo estado del motor»

**Intento de demostración.** Un almacén paralelo con entidades propias es estado
que alguien posee. ¿No rompe eso «el motor posee el estado» (ADR-019)?

**Veredicto: la objeción no sobrevive, pero deja una regla.** El staging no
guarda hechos del motor: guarda **propuestas**, que son un hecho distinto y del
que el motor no es dueño. Lo que sí sería un defecto es que el staging copiara
estado del motor.

**Regla derivada, aplicada**: el staging guarda **referencias** (`work_id`,
`run_id`, `sequence` del evento), **nunca copias del estado del WorkItem**. Si
alguna vez necesita saber en qué estado quedó algo, lo lee del diario.

### A8 — «Nada impide de verdad que un fallo se generalice»

**Intento de demostración.** Mi diseño dice que los aprendizajes negativos nacen
estrechos. Pero eso es una instrucción al Extractor, y una instrucción no es una
garantía — es justo lo que critico del «modelo distinto» en §2.2. Estaba
aplicando dos varas.

**Veredicto: la objeción acierta contra mí. Es la crítica más útil de esta
ronda.**

**Corrección aplicada**: se convierte en invariante determinista del Gate
(I13, §10.1): **un candidato negativo sin `negative_scope` que nombre
explícitamente Worker, modelo, runtime, versión y entorno observados no
promociona.** Es una comprobación de campos, no un juicio. Y nótese que
`negative_scope` depende de GAP-1: sin identidad de modelo, ni siquiera se puede
rellenar. Los dos problemas son el mismo problema.

### A9 — «Viola la governance vigente»

**Intento de demostración.** `docs/evolution/STATUS.md:27-35` autoriza el motor
«estrictamente según ADR-020 y su plan aprobado»; el aprendizaje no está ahí.
`AGENTS.md` obliga a parar ante «otro proceso, servidor, agente o base de datos».
El contrato §9 prohíbe iniciar trabajo sin orden y §9.1 ya gastó la única
ejecución periódica permitida.

**Veredicto: la objeción acierta por completo, y por eso este documento no es un
plan.** Es un informe más un ADR `PROPUESTO`. El diseño de §6 evita el proceso
nuevo y la base de datos nueva, pero **sí** introduce perfiles de agente nuevos y
**sí** queda fuera de la excepción vigente. Ambas cosas exigen decisión del
propietario, y así se piden (§12, D-1).

### A10 — «Inspect AI»

**Intento de demostración.** El brief lo propone como laboratorio. ¿Es una pieza?

**Veredicto: no es una pieza, y proponerlo ahora sería violar la governance.** No
existe en el árbol (§2, fila h); el repositorio **ya decidió** dejarlo fuera del
motor (`SIRIUS_WORK_ENGINE_INVENTARIO.md:187`); y adoptarlo entra en «adoptar
frameworks o proveedores no aprobados», expresamente **no autorizado**. No se
recomienda (§13).

### Balance de la ronda

Diez objeciones. **Cuatro obligaron a corregir el diseño** (A1 arnés reutilizado,
A3 dossier no persistido, A7 el staging solo referencias, A8 alcance negativo
como invariante del Gate), **dos sobreviven sin cerrar** (A4 la segunda memoria,
A6 el coste) y **suben al propietario** como decisiones reales, y **cuatro se
sostienen** (A2, A5, A9, A10) con la propuesta ya escrita para respetarlas.

No hay todavía dos rondas con defectos de la misma familia, así que la regla de
las dos rondas (ADR-001) no obliga a parar. Pero conviene anotar el patrón que
ya asoma: **de las cuatro correcciones, tres son la misma familia — «lo que
creía una pieza nueva ya existía»** (A1 el arnés, A3 el dossier, y en el fondo
A4). Si la ronda siguiente vuelve a producir esa familia, la regla se activa y lo
que toca no es parchear el diseño: es aceptar que **este vertical es mucho más
pequeño que su brief** y reescribirlo a esa escala.

---

## 12. Lo que queda abierto, en tres listas separadas

**Reestructurado en la ronda 3.** Las dos redacciones anteriores presentaban
«nueve decisiones del propietario» y no lo eran: había dentro investigaciones
técnicas que se cierran con datos y defectos ya reportados que no necesitan
ninguna firma. Mezclarlos infla la lista y esconde cuáles son de verdad tuyas.

Además, **casi todo cuelga de la primera**: si D-1 se responde «no», las demás no
llegan a plantearse. No son nueve decisiones paralelas.

### 12.A — Decisiones que solo puede tomar el propietario

Son seis. Ninguna se cierra con evidencia: todas cambian alcance, autoridad,
gasto o una frontera aprobada.

**D-1 — ¿Se autoriza siquiera explorar este vertical?**
La excepción de `docs/evolution/STATUS.md:27-35` ampara el Work Engine
«estrictamente según ADR-020 y su plan aprobado». El aprendizaje no está en ese
plan, así que **hoy no está autorizado ni en su forma mínima**. Además introduce
perfiles de agente nuevos, que activan el criterio de parada de `AGENTS.md`.
*Bloquea*: todo lo demás. *Recomiendo*: **no autorizar nada todavía**, por las
cinco razones de §6.6. Si aun así se quisiera un primer paso, el único que no
introduce ningún agente ni gasto es un lector determinista del diario que
construya el dossier y no llame a ningún modelo — y hoy leería un fichero que no
existe, así que ni siquiera eso aporta evidencia todavía.

**D-2 — ¿El aprendizaje llega a ser alguna vez un WorkItem?** *(Ampliada en la
ronda 3 para absorber la opción O5.)*
Dos caminos, y solo uno estaba contado antes:
- **Clase nueva `aprendizaje`**: hoy imposible sin enmienda. `WorkItemClass` es
  cerrado y el contrato §11.1 dice que «una clase que no aparezca aquí no puede
  crear WorkItems hasta que se añada», lo que exige enmendar la v1.7 y tocar la
  tabla de A5.
- **Clase ya existente con autoridad `motor`** (`MIXTA`, `CONSULTA_LARGA`…):
  **sí es posible hoy**, sin tocar nada. La ronda 3 refutó que estuviera
  bloqueado, y tenía razón: la primera redacción presentaba como imposibilidad lo
  que era una elección.
*Recomiendo*: **no**, por los tres argumentos de §6.1 (el campo `clase` dejaría
de describir el trabajo; el motor recuperaría la propiedad del ciclo de vida; y
el contrato §9 obliga igualmente a una orden por cada WorkItem). Pero son
argumentos, no una imposibilidad, así que **la decisión es tuya**.

**D-3 — Presupuesto del aprendizaje. BLOQUEANTE tras la ronda 2.**
No es que el presupuesto sea incómodo de aplicar: es que **no se puede aplicar en
absoluto**. Comprobado ejecutando (§14.5, H-3): `registrar_gasto` sobre un
WorkItem `DELIVERED` lanza `IllegalTransitionError`, porque el corte determinista
escala y escalar exige `ACTIVE`. Y como el aprendizaje no es un WorkItem, no hay
`work_id` al que cargar nada. Un sidecar gastaría **sin límite, sin corte, sin
`NEEDS_DECISION`, sin escalada y sin notificación**.
*Recomiendo*: **no ejecutar ninguna llamada a modelo desde el aprendizaje hasta
que exista una puerta de gasto que le sirva.** No es una cifra lo que falta: es
el mecanismo.

**D-4 — ¿Segunda memoria? (la objeción A4, que sobrevivió)**
La arquitectura §9 dice que el sustrato de memoria ya existe en el producto y que
exponerlo como capacidad es trabajo futuro sobre código existente. Si el motor
construye su propia MEMORY activa antes de decidir eso, Sirius acaba con dos.
*Bloquea*: el conocimiento activo del motor, y solo eso. *Recomiendo*: decidir esta
pregunta antes de construir ningún conocimiento activo del motor, y no antes de
tener candidatos reales que mirar.

**D-5 — ¿Enviar evidencia privada a un proveedor nuevo?**
La exigencia «el Refutador usa un modelo distinto del proponente» puede implicar
un proveedor distinto, y con él evidencia del repositorio privado saliendo hacia
un tercero que hoy no la recibe. `AGENTS.md` obliga a parar ante «enviar más
datos a terceros». Conviene además saber que la política de egress implementada
clasifica **capacidades** (`web.buscar`), no el transporte del propio modelo:
`egress.py` **no** cubre este caso por sí solo.
*Recomiendo*: tratarlo como decisión de privacidad explícita (causa 5 de
escalado), y preferir, si existe, un refutador local o del proveedor ya en uso
antes que uno nuevo.

**D-10 — ¿Se añade un puerto de solo lectura del diario? *(nueva, ronda 3)***
Hoy `WorkEngineStore` (`ports/store.py:24`) es **un solo Protocol con 36 métodos**,
de los que cinco son de lectura, y **no existe ningún puerto de solo lectura**.
Por tanto: o un lector entra por `list_events()` sosteniendo un handle con las 31
escrituras, o lee el fichero y depende de una representación que ADR-019 deja
abierta hasta D2. **No hay tercera vía** (§6.5).
*Bloquea*: que «el aprendizaje no puede escribir el estado» pase de convención a
garantía estructural. Y no solo al aprendizaje: cualquier consumidor de solo
lectura del motor tiene hoy el mismo problema.
*Recomiendo*: tratarlo como interfaz nueva del motor, alcance de C2/D2, decidida
por quien lleve esos bloques. **No es alcance de una auditoría, y desde luego no
de un vertical sin autorizar.**

### 12.B — Investigaciones técnicas: se cierran con datos, no con una firma

Lo que necesitan del propietario es, como mucho, **cuándo** se hacen y quién las
paga; no **si** son correctas.

**D-6 — ¿Cuándo se cobra el trabajo de cerrar GAP-1?** *(reclasificada en la
ronda 3: no es «si se corrige», es «en qué bloque»)*
`Run.worker` es una cadena sin estructura y no hay identidad de modelo/runtime
(GAP-1); `WorkPackage`/`WorkResult` no tienen esquema (GAP-2). Ambas son
divergencias respecto de la arquitectura **aprobada**, no ampliaciones pedidas
por el aprendizaje. Cerrarlas donde nacen —el primer Worker real— cambia el
alcance de bloques aprobados, y eso es del propietario.
*Recomiendo*: cerrarlo, y **por su propio mérito**: sin identidad de modelo no se
pueden comparar dos Runs, ni explicar en qué se diferenció una sustitución de
Worker, ni sostener las invariantes I2 e I13. **El «sí» no necesita firma**: es
conformidad con una arquitectura ya aprobada, y está reportado como H-6 en el
parte de defectos. Lo único abierto es la secuenciación.

**D-7 — ¿Cuándo, si acaso, el disparo pasa a ser automático?**
Hoy exige o enmendar el contrato §9/§9.1 (que ya gastó su única ejecución
periódica en el reconciliador) o esperar a D2, donde el motor corre como
servicio supervisado y el barrido es parte de su propio ciclo.
*Recomiendo*: **esperar a D2**. Gastar una enmienda de contrato para automatizar
un sidecar sobre un corpus inexistente es el peor cambio posible por unidad de
riesgo.


**D-9 — Investigación de reutilización: qué se reutiliza, en qué forma, y a qué
coste de acoplamiento.**

Sustituye a la formulación anterior, que decía «hacer crecer lo existente». Era
vaga y, peor, daba por hecho lo que hay que investigar.

Sirius tiene **patrones e invariantes demostrados** para casi todo lo que el
brief plantea (§4). No están disponibles como componentes: viven en tres sitios
con reglas distintas, y una prueba (`tests/engine/test_boundary.py`) impide que
dos de ellos se toquen. Lo que hay que decidir, **mecanismo por mecanismo**, es
en cuál de estas cinco formas se reutiliza:

| | Forma |
|---|---|
| **A** | Reutilización física directa |
| **B** | Extracción de una primitiva compartida |
| **C** | Reutilización mediante adapter o puerto del Work Engine |
| **D** | Reutilización solo conceptual: viaja el invariante, no el código |
| **E** | Implementación nueva justificada |

Condiciones que la investigación no puede saltarse:

1. **`tests/engine/test_boundary.py` se respeta.** `sirius` y `sirius_engine` no
   se importan en ningún sentido. Cualquier reutilización entre ellos es B o C,
   nunca A, y exige decisión.
2. **La ownership de cada capa se respeta.** El motor posee estado y ciclo de
   vida (ADR-019); el producto posee su propio dominio; la automatización posee
   la vía GitHub. Nada de eso se mezcla para ahorrar código.
3. **Los contratos existentes se respetan.** Un mecanismo que hoy depende de una
   PR, de `gh` o del formato de un veredicto no puede entrar al motor sin
   desatarlo primero de eso.
4. **No se fuerza la reutilización física si aumenta el acoplamiento o rompe una
   frontera.** La regla es **reuse before build, pero también abstraction before
   coupling**. Preferir B o D a un A que arrastre dependencias.

La tabla de §4.1 es la **hipótesis de partida** de esa investigación, no su
resultado; varias filas solo se pueden cerrar con datos que hoy no existen.

*Cuándo se hace*: **no ahora.** La ronda 3 señaló la contradicción de la
redacción anterior, que la declaraba «bloqueante» y a la vez decía que no
bloqueaba nada — y además varias filas de §4.1 están fijadas a estados que el
propio plan cambiará antes de que exista ningún aprendizaje. Se degrada a lo que
es: **la pregunta que se hace cuando exista un candidato concreto de extracción**,
con la tabla de §4.1 como punto de partida a reverificar entonces, no como
resultado.
*Es decisión del propietario*, no técnica, en un punto concreto: **si se abre o
no la vía para extraer primitivas compartidas entre `src/sirius` y
`src/sirius_engine`.** Eso cambia una frontera aprobada y no lo decide una
auditoría.


### 12.C — Ya decidido o ya reportado: no requiere ninguna decisión nueva

Se conservan aquí para que no se pierdan, con la etiqueta explícita de que **no
son decisiones**.

**D-8 — La colisión de ADR-042 en la PR #207. NO es una decisión.**
*(Reclasificada en la ronda 3.)* ADR-032 ya decidió la regla —el número es el
máximo existente más uno— y el defecto está reportado como **H-4** en el parte.
Lo único que queda es aplicarlo.
No es de aprendizaje, pero deja A5 con una comprobación en rojo real y
reproducida (§1.3, H-4). *Recomiendo*: al corregirla, el duplicado toma **el
siguiente número válido en `main` en ese momento**, calculado con
`scripts/siguiente_adr.py` contra `main`, y se vuelve a pasar
`tests/automation/test_registro_de_decisiones.py`.
**Esta rama no reserva ningún número frente a A5** y no debe consultarse para
calcularlo: es exploratoria y sin aprobar, mientras que A5 es trabajo del Work
Engine ya autorizado. Si esta rama llega a integrarse alguna vez, será ella la
que recalcule su propio número. *(La primera redacción recomendaba que A5 tomara
el 044 «porque este trabajo toma el 043». Retirado: invertía la prioridad.)*


---

## 13. Qué NO recomiendo construir

- **Un Learning Agent, un Memory Agent o cualquier coordinador.** La arquitectura
  §9 ya lo cerró («No hay "Agente de memoria"») y §2 del brief lo repite. El
  diseño de §6 no tiene ninguno: tiene un lector y dos perfiles.
- **Una clase de trabajo `aprendizaje`.** Ver D-2. Cuesta una enmienda de
  contrato, toca A5 y convierte al aprendizaje en trabajo del motor, que es justo
  lo que no debe ser.
- **Un hook dentro del dominio o del puerto de almacén.** Rompe la garantía de
  que un fallo de aprendizaje no toca un WorkItem entregado (§6.1, O1 y O2).
- **Un segundo barrido periódico.** El contrato §9.1 permite exactamente uno y
  ya está gastado.
- **Una base de datos, un vector store o un backend de memoria.** ADR-019 hace
  depender la representación definitiva de I3 **e** I4, e I4 sigue abierta.
  Además `AGENTS.md` obliga a parar ante «introducir otra base de datos». El
  staging de la fase de sombra cabe en un fichero append-only con el patrón que
  S1 ya probó.
- **Inspect AI, ahora.** No está en el árbol, el repositorio ya decidió dejarlo
  fuera del motor (`SIRIUS_WORK_ENGINE_INVENTARIO.md:187`) y adoptarlo es
  «adoptar frameworks o proveedores no aprobados», expresamente no autorizado.
  Como laboratorio futuro de evaluación sigue siendo una buena idea; como trabajo
  de este vertical, no.
- **Un Evidence Dossier persistido.** Ver §11, A3: crea un segundo relato de lo
  ocurrido. Es una función, no un artefacto.
- **Un arnés nuevo para el Extractor o el Refutador.** Ver §11, A1 y A2:
  reutilizar el perfil y el esquema del Auditor y el contrato de revisión
  existente. Si el resultado es que el Extractor es el Auditor con otro perfil,
  eso es la respuesta correcta, no un atajo.
- **Auto-promoción, umbrales, algoritmo de deduplicación semántica y política de
  presupuesto autónomo.** Se miden, no se adivinan, y no hay nada que medir
  todavía (GAP-6).
- **Experimentos proactivos.** El propio brief los deja fuera de v0, y con corpus
  cero no hay hipótesis que valga la pena probar.

---

## 14. Ronda 2: la regla de las dos rondas se activó

Cuatro refutaciones independientes (duplicación, ownership/governance, seguridad,
coste/orden), con lentes distintas, contra el diseño de §6. **Verifiqué cada
hallazgo contra el código antes de aceptarlo** (ADR-001 §4); lo que sigue es lo
que resistió esa verificación, con la comprobación que lo sostiene.

### 14.1 El patrón, escrito antes de decidir qué hacer con él

La ronda 1 (§11) devolvió cinco objeciones de la familia **«esta pieza ya existe
con otro nombre»**: A1 (el Auditor), A2 (el Refutador), A3 (el dossier), A4 (la
segunda memoria), A7 (el staging). Concedí tres y declaré una insalvable. Al
cerrar §11 escribí que si la ronda siguiente devolvía la misma familia, la regla
se activaría.

**La devolvió, y con más fuerza.** La ronda 2 encontró tres piezas más de la
misma familia, y son justamente las que yo había dado por inexistentes.

Por ADR-001, aquí **se prohíbe seguir parcheando el diseño**. Toca escribir la
raíz y decidir: seguir, retirar o escalar.

### 14.2 La raíz

**El brief se escribió contra los documentos de Sirius, no contra su código.**
Por eso especifica como diseño nuevo un conjunto de capacidades que este
repositorio ya construyó y probó, en dos carriles distintos. No es un defecto del
brief como pieza de pensamiento: es lo que pasa cuando se diseña sobre una
descripción en vez de sobre un árbol de ficheros. Pero cambia el entregable: lo
que hacía falta no era un diseño de vertical, sino **este contraste**.

### 14.3 El argumento con el que salvé A1 en la ronda 1 era falso

En §11, A1, defendí que el Auditor «falla en la cola»: que el tramo
`staging → Gate → activo` no existe en Sirius. **Existe, y no una vez sino dos.**

- **Carril de automatización**: fichero de veredicto (staging) →
  `scripts/automation/sirius_aggregate_reviews.py` (Gate determinista) →
  `scripts/automation/sirius_apply_verdict.sh` (aplicación previa reverificación).
  Y el agregador es, literalmente, lo que el brief pide: **dos revisores de
  proveedores distintos** (Claude + Codex), **sin votos, promedios ni arbitraje
  por otro modelo**, con **fail-closed** ante JSON ausente o inválido y ante SHA
  distinto o no demostrable, y aprobación **solo si ambos aprueban el mismo SHA**
  (`sirius_aggregate_reviews.py:8-23`). La ligadura al hash exacto es
  `sirius_apply_verdict.sh:15-17`: coincidencia exacta entre el `reviewed_head_sha`
  declarado, el head actual de la PR y el último head que superó Quality.
- **Carril del producto**: propuesta → aprobación humana explícita → decisión
  activa, con sustitución y archivado reversibles
  (`src/sirius/domain/{memory,decision,precedence}.py`).

Es decir: **el «Refutador de modelo distinto», el «Promotion Gate determinista
que falla cerrado» y la «aprobación ligada al cambio exacto» son invariantes que
Sirius ya ha demostrado que sabe sostener.** Mi error de la ronda 1 fue afirmar
que no existían en ninguna parte.

**Y el error contrario, que la primera corrección cometió, es igual de grave**:
de ahí no se sigue que estén disponibles. Ese tramo vive en scripts de CI atados
a una PR, a `gh` y a un fichero de veredicto, y en un dominio al otro lado de una
frontera que una prueba hace cumplir. Traerlos al motor tal cual sería acoplar el
motor a la vía GitHub o romper `test_boundary.py`. Lo que viaja es el invariante;
el mecanismo, salvo decisión expresa, no (§4).

### 14.4 Correcciones a lo que este informe afirmó de más

| # | Lo que dije | Lo que es | Comprobación |
|---|---|---|---|
| C-1 | «La invariante del Extractor **sí es expresable** de forma estructural hoy, sin código nuevo» | Expresable sí; **en vigor no** — pero la corrección misma se afirmó mal: ver C-7 | `grep -rn project_worker_request src/` |
| C-7 *(ronda 3)* | «Los cuatro símbolos no tienen ningún llamador en `src/` — solo en `tests/`» | **FALSO para tres de los cuatro.** `worker_request.py:65-67` llama a `compute_permission_envelope`, `validar_egress_fail_closed` y `resolve_capabilities`. Lo verdadero es más estrecho: **nadie llama a `project_worker_request`** fuera de las pruebas, así que ningún camino de producción construye un `WorkerRequest`. El grep que sostenía la afirmación **excluía el fichero donde estaban los llamadores** | `grep -rnE "compute_permission_envelope\|resolve_capabilities\|validar_egress_fail_closed" src/` → tres aciertos en `worker_request.py`; `grep -rn project_worker_request src/` → solo su definición |
| C-2 | (no lo dije) | `PermissionEnvelope.escritura` es **un nombre de ámbito**, no una ruta. Si el conocimiento se materializa como ficheros del repo, `escritura: repo` lo cubre igual que el código. Separarlo es trabajo | `domain/permission_envelope.py:22-30` |
| C-3 | «Nueve de trece piezas ya existen» → corregido a «doce de trece» | **Las dos cifras estaban mal planteadas.** Contar piezas confunde *patrón demostrado* con *componente disponible*. La cuenta se retira entera y se sustituye por la clasificación A–E de §4, que dice de cada mecanismo **en qué forma** podría reutilizarse y a qué coste de acoplamiento | §4.1 |
| C-4 | «Diario con integridad comprobable» | Comprobable frente a **corrupción del medio**, no frente a manipulación: el checksum es SHA-256 **sin clave**, recalculable por cualquiera que pueda escribir el fichero | `adapters/durable/journal.py:1-20` |
| C-5 | «Opción RECOMENDADA» | **Mejor clasificada, no recomendada.** La matriz omitía el criterio de parada de `AGENTS.md`, que esta opción dispara dos veces (staging propio; punto de entrada inexistente) | §6.2, ya corregido |
| C-6 | Coloqué el vertical «después de M3» | El calendario correcto es **«todavía no»**, sin fecha. Ningún bloque del plan programa GAP-1, así que **M3 tampoco entrega el dato que el vertical necesita** | `PLAN` §2, bloques C1–C4 |

Y una objeción de la ronda 2 que acepto sin matices: **ADR-043 no es norma
vigente.** Es mi propia nota de arranque, en `PROPUESTO` y sin fusionar. Apoyar
el ranking en «los criterios de parada 1 y 2 de ADR-043» en vez de en `AGENTS.md`
y el contrato es lo que produjo el punto ciego de C-5.

### 14.5 Hallazgos independientes descubiertos durante esta auditoría

**Estos hallazgos NO son requisitos del Learning System.** Son defectos y
divergencias del Work Engine que existen hoy, y seguirían existiendo aunque este
vertical no se construyera nunca. Se reportan aquí porque es donde aparecieron.
**Ninguno autoriza tocar nada desde esta rama**, y ninguno debe convertirse en
dependencia artificial del aprendizaje: solo lo son donde exista una relación
técnica demostrable, y eso se dice explícitamente en cada ficha.

El parte accionable, con reproducción ejecutable de cada uno, está en
`docs/audits/DEFECTOS_ENCONTRADOS_2026-08-20.md`. Aquí van la ficha corta y,
sobre todo, **la relación con el aprendizaje**, que es lo que este informe tiene
que dejar claro.

---

**H-1 — El cuerpo de la incidencia entra sin filtro de autor, dentro de una
función que promete lo contrario.**

- **Impacto**: `_texto_cronologico_de_confianza` gobierna la numeración de rondas
  y la racha de fallos de CI vía `sirius_convergence.parse_round_records`. La
  función afirma una propiedad de confianza que no tiene. Alcance real acotado:
  **nada de la automatización escribe el cuerpo** de una incidencia (solo
  etiquetas y comentarios), así que el texto viene del propietario o de ChatGPT
  al redactar el work item.
- **Evidencia**: `mirror_projection.py:188-197` filtra comentarios con
  `es_autor_de_confianza` y luego concatena `cuerpo` sin filtrar;
  `ports/github_mirror.py:61-65` (`LecturaCuerpo`) no tiene campo de autor, así
  que no se puede filtrar sin tocar el puerto.
- **Por qué es independiente**: el defecto está en la proyección del espejo (A3)
  y afecta al ciclo de revisión/convergencia que ya opera. No necesita que exista
  ningún aprendizaje para importar.
- **Dónde debería tratarse**: con quien lleve A3 y el puerto del espejo, en su
  propia rama.
- **¿Bloquea Learning?** **No.** Solo *convendría* arreglarlo antes de que alguna
  vez se lea evidencia de la vía GitHub para construir un dossier — pero eso está
  a mucha distancia, y no es una dependencia.

---

**H-2 — «No pude leer el resultado» se convierte en «éxito con resultado
vacío».**

- **Impacto**: **crítico para la calidad de la evidencia futura.** Es el único
  camino por el que el resultado real de un Worker llega al diario. Un Run que se
  cierra como `SUCCEEDED` con resultado vacío contamina de forma indistinguible
  el registro del que después se responde «¿qué pasó con X?».
- **Evidencia**: `recovery.py:93-95`,
  `store.succeed_run(live.run_id, resultado=observation.resultado or {}, now=now)`;
  y `ports/world.py:23-33` (`RemoteRunStatus`) enumera `PENDING`, `SUCCEEDED`,
  `FAILED`, `LOST`, `CANCELLED` — **sin `UNKNOWN`**, así que el observador no
  tiene forma de decir «no pude mirar». Es la familia que **ADR-036 ya cerró para
  el espejo**, reaparecida en el barrido de recuperación.
- **Por qué es independiente**: es un defecto de A2, y degrada la evidencia para
  cualquier consumidor —una consulta del propietario, el supervisor de C1, una
  auditoría— no solo para un extractor.
- **Dónde debería tratarse**: con quien lleve A2/C1. Hoy es **latente** (la única
  implementación de `RunWorldObserver` es un doble de pruebas), y por eso es
  barato ahora y caro cuando llegue el observador real.
- **¿Bloquea Learning?** **No lo bloquea, pero es la relación técnica más real de
  las tres**: cualquier aprendizaje se extrae de esa evidencia, y aprender de un
  «éxito» que en realidad fue una lectura fallida produce exactamente la clase de
  conocimiento falso que todo el pipeline existe para impedir. Conviene
  arreglarlo antes, no porque el aprendizaje lo exija, sino porque sin él la
  evidencia no vale para nadie.

---

**H-3 — El corte de presupuesto no funciona fuera de `ACTIVE`.**
*(Descripción canónica y reproducción: `DEFECTOS_ENCONTRADOS_2026-08-20.md`, H-3.
Aquí solo la relación con el aprendizaje.)*

- **Impacto**: **bloquea cualquier automatización que gaste modelos fuera de un
  WorkItem gobernado**, y además rompe el gobierno dentro del caso normal.
  Comprobado ejecutando: al agotarse el presupuesto, `registrar_gasto` mata el
  Run y después llama a `escalate_work_item`, que exige `ACTIVE`. Un Worker
  asíncrono deja el WorkItem en `WAITING` —que es cuando se gasta—, así que queda
  el Run muerto, el WorkItem esperando a un Run que ya no existe, sin escalada,
  sin notificación, y con el `Budget` actualizado perdido en la excepción.
- **Evidencia**: `a5:governance.py` (orden `fail_run` → `escalate_work_item`),
  `domain/work_item.py` (`escalate` exige `ACTIVE`); reproducción completa en el
  parte de defectos. Las cuatro pruebas de `tests/engine/test_governance.py`
  parten todas de `ACTIVE`.
- **Por qué es independiente**: es un defecto de A5, en su garantía principal, y
  se manifiesta con el primer Worker externo real —B1— mucho antes de que exista
  ningún aprendizaje.
- **Dónde debería tratarse**: en la rama de A5, por quien la lleve. **No desde
  aquí.**
- **¿Bloquea Learning?** **Sí, y de forma dura, pero no solo a Learning.** Bloquea
  a cualquier cosa que gaste modelos fuera de un WorkItem activo. Como además el
  aprendizaje **no es un WorkItem** (§3.8), no hay ni siquiera un `work_id` al
  que cargar el gasto: no es que la puerta esté rota, es que no hay puerta. Por
  eso D-3 pasa de incómoda a bloqueante.

---

Una divergencia más, que no es un defecto pero pertenece a esta lista:
**GAP-1** (§5) —la identidad estructurada de Worker/modelo/runtime por Run— es
una divergencia respecto de la arquitectura §3.3 que vale por sí misma, con o
sin aprendizaje. Se registra como tal en §5, y **no se implementa aquí**.


### 14.6 La decisión que exige la regla

Seguir, retirar o escalar. **Escalar, y retirar la parte que sobra.**

- **Se retira** la recomendación de construir un vertical de aprendizaje. **La
  razón fuerte no es que «ya existan las piezas»** —esa formulación estaba mal
  planteada y se corrigió en §4—: es que **no hay experiencia real de la que
  aprender**. Las cinco razones están en §6.6: no hay Worker gobernado de extremo
  a extremo, no hay corpus, varias invariantes no son comprobables, construir
  ahora obligaría a fijar abstracciones sin datos, y lo que tiene que avanzar
  primero es el motor.
- **Se retira** también la «Fase L» que la primera redacción proponía (§8.3).
  Fijar una fase es fijar la forma del trabajo, y no hay datos para fijarla.
- **Se conserva** el contraste (§1–§5), que es lo que de verdad hacía falta, y el
  análisis de enganche (§6) con su estatus corregido: la respuesta a «si algún
  día, por dónde», no una propuesta de empezar.
- **Sube al propietario** la investigación de reutilización (D-9): qué mecanismo
  se reutiliza físicamente, cuál por primitiva extraída, cuál por adapter, cuál
  solo como invariante y cuál hay que implementar — respetando
  `test_boundary.py`, la ownership de cada capa y los contratos existentes, bajo
  la regla **reuse before build, abstraction before coupling**.


### 14.7 Una objeción de la ronda 2 que no acepto entera

Se argumentó que el lector **es** un coordinador, porque una orden produce N
candidatos y cada uno encadena Refutador, Curator y Gate. Acepto el fondo —
encadena invocaciones de modelo sin ninguna puerta de gasto, que es exactamente
H-3 — y no acepto la etiqueta: «coordinador» en el vocabulario de este
repositorio (ADR-019, arquitectura §2) significa poseer ciclo de vida y estado, y
un lector del diario no posee ninguno de los dos. La corrección correcta no es
llamarlo coordinador: es que **sin puerta de gasto no debe existir**.

---

## 15. Ronda 3: qué encontró y qué se corrigió

Seis lentes pedidas por el propietario: reutilización falsa, acoplamiento
accidental, duplicación real, patrón contra componente, decisiones de producto
disfrazadas de técnicas, y trabajo futuro sin valor. **Cada hallazgo se verificó
contra el código antes de aceptarlo**; los tres más graves se comprobaron
ejecutando.

### 15.1 El error factual más serio de todo el trabajo

Las dos redacciones anteriores afirmaban, en **siete sitios de los tres
documentos**, que `compute_permission_envelope`, `resolve_capabilities`,
`validar_egress_fail_closed` y `project_worker_request` «no tienen ningún
llamador en `src/` — solo en `tests/`». **Es falso para tres de los cuatro**:
`worker_request.py:65-67` los llama.

Y lo peor no es el error: es cómo se produjo. El grep que lo «comprobó**
excluía `worker_request.py` para «quitar ruido» — es decir, **excluía el único
fichero donde estaban los llamadores**. Se presentó además como una corrección
de la ronda 2, bajo un encabezado que dice «verifiqué cada hallazgo contra el
código». Un filtro de conveniencia convirtió una comprobación en su contrario.

Lo verdadero es más estrecho y sostiene igual la conclusión: **nadie llama a
`project_worker_request` fuera de las pruebas**, así que ningún camino de
producción construye un `WorkerRequest` y las guardas no corren. Corregido en los
siete sitios.

### 15.2 La familia de la ronda 3: convención presentada como estructura

Tres objeciones independientes resultaron ser la misma, y es una familia
**distinta** de la de las rondas 1 y 2: el informe afirmaba como estructural una
garantía que hoy es solo convención — el mismo estándar que le exige al brief.
Corregido de raíz en **§6.5**, no frase a frase.

### 15.3 Las demás correcciones aplicadas

| Qué decía | Qué es | Dónde |
|---|---|---|
| El agregador de revisión dual está «acoplado a `gh` y al ciclo de etiquetas», así que «nunca A» | **Falso.** Importa solo `argparse`, `json`, `re`, `sys`, `typing`; cero coincidencias de `gh`, etiquetas, red o entorno. Su acoplamiento real es al esquema del veredicto. Es el **mejor candidato a primitiva compartida** de toda la tabla | §4.1, §4.2 |
| «Operando a diario» | Su modo dual depende de `SIRIUS_CODEX_REVIEW_ENABLED`, cuyo valor no está en el árbol (I5 del plan). Construido y probado sí; operando, no comprobado | §4.1 |
| «El aprendizaje v0 no es un WorkItem» como consecuencia forzada | **Es una decisión, no una imposibilidad.** Podría nacer bajo una clase existente con autoridad `motor` (`MIXTA`, `CONSULTA_LARGA`). Se descarta igual, pero con argumento explícito, y sube como decisión | §6.1, D-2 |
| «Nueve decisiones del propietario» | Eran cuatro decisiones, tres investigaciones técnicas y una cosa ya decidida. §12 se parte en tres listas | §12 |
| Trece invariantes con prueba por mutación «para todas» | Una es comprobable hoy (I9, y ya se cumple); tres no son invariantes sino fixtures; la promesa de mutación solo vale para cuatro | §10.1 |
| «Las diez fixtures ya se pueden construir como secuencias de eventos» | Cuatro sí; dos dependen de GAP-2; cuatro dependen de objetos que no existen | §10.2 |
| I12 como lista de rutas prohibidas | Una regla que enumera vehículos siempre tiene un hueco más (ADR-033) — se dejaba fuera `.github/**`. Invertida a lista de permitidos | §10.1 |
| El predicado del diff, transcrito en dos documentos | Las dos copias habían divergido: decían dos ficheros cuando ya eran tres. Ahora vive **solo** en ADR-043 | §8.1 |
| H-3 descrito en tres sitios, ya divergido | El ADR describía el caso débil (`DELIVERED`) y perdía el grave (`WAITING`). Descripción canónica única en el parte de defectos | §14.5, ADR |
| Citas `ruta:línea` desplazadas ±1..3 | Barrido mecánico: `egress.py:25`, `events.py:58`, `work_item.py:38`, `profile.py:33-48`, `worker_request.py:44-54` | todo el informe |

### 15.4 Lo que la ronda 3 intentó tumbar y no pudo

- **El orden de las opciones de enganche.** Las tres lentes que lo atacaron
  coinciden: O4 sigue siendo la única que no toca dominio, códec ni A5, y la
  única de la que se puede afirmar que un fallo del sidecar no rompe un WorkItem
  entregado. Lo que cayó no fue la elección: fueron las garantías de más.
- **La distinción central del marco corregido**: «que exista el patrón no
  significa que el sistema esté medio construido».
- **Los hechos duros**: no hay puerto de Worker, no hay corpus, no hay ningún
  diario en disco, el motor no está referenciado por ningún workflow.
- **I9**: se intentó demostrar que «el `WorkPackage` es instantánea inmutable»
  era falso —`Mapping` no es inmutable en Python—, y se comprobó ejecutando que
  sí lo es: `run.py:238` guarda `MappingProxyType(dict(...))`, así que mutar el
  dict del llamador no cambia ni el Run ni el evento.

### 15.5 Por qué esta es la última ronda

La familia de la ronda 3 es nueva, así que la regla de las dos rondas no obliga a
parar por ella. Pero el propietario pidió no parchear indefinidamente, y el
criterio para dejarlo es observable: **de las objeciones de esta ronda, ninguna
cambió una sola conclusión.** Todas fueron de precisión, de clasificación o de
sobreafirmación. Cuando una ronda deja de mover las conclusiones y solo mueve la
redacción, seguir es pulir, no auditar.


## 16. Lo que este informe NO garantiza

Repetido de ADR-043 porque es donde toca leerlo:

- No autoriza nada. La única forma de que algo de aquí quede aprobado es que el
  propietario fusione ADR-043 y tome las decisiones de §12.
- No audita Hermes. `NousResearch/hermes-agent` no está en el alcance de esta
  sesión; el adjunto 01 se toma como descripción dada sobre Hermes y solo se
  verificó lo que afirma sobre Sirius.
- No arregla la PR #207 ni ninguna otra.
- No mide coste, calidad de modelos, deduplicación ni umbrales.
- No fija el backend físico del conocimiento.
- No garantiza que el enganche recomendado sobreviva a las enmiendas C1 y C2 del
  contrato (E1b), que aún no existen.

## 17. Comprobaciones que sostienen este informe

```
git log -1 --oneline                       -> a25ee3b (main)
API de GitHub, pull request 207            -> open, merged:false, unstable, head 9e3a79b
uv run pytest tests/automation/test_registro_de_decisiones.py   (en la rama A5)
                                           -> 1 failed: ADR-042 duplicado
uv run python scripts/siguiente_adr.py --solo-numero            -> 43
ls src/sirius_engine/ports/                -> sin puerto de Worker
ls experiments/                            -> solo work_engine_spike_i3
grep -rniE "claude|openai|anthropic|gpt-|sonnet|opus" src/sirius_engine/
                                           -> ningún acoplamiento a modelo o proveedor
grep -rn "WorkPackage|WorkResult" src/     -> ningún tipo; solo Mapping opacos
grep -rni "inspect.ai|inspect_ai" .        -> solo documentos, nunca código
tests/engine/test_boundary.py              -> sirius <-> sirius_engine, prohibido en ambos sentidos
```

Añadidas al verificar la ronda 3:

```
grep -rnE "compute_permission_envelope|resolve_capabilities|validar_egress_fail_closed" src/
                                           -> TRES aciertos en worker_request.py:65-67
                                              (desmiente lo que este informe afirmó
                                              en las rondas 1 y 2)
grep -rn project_worker_request src/       -> solo su definición y su docstring:
                                              nadie construye un WorkerRequest
sed -n '26,32p' scripts/automation/sirius_aggregate_reviews.py
                                           -> argparse, json, re, sys, typing.
                                              Cero gh, etiquetas, red o entorno
grep -n SIRIUS_CODEX_REVIEW_ENABLED .github/workflows/review-sirius-work.yml
                                           -> el modo dual depende de una variable
                                              de repositorio ausente del árbol
grep -n "os.open\|ftruncate" src/sirius_engine/adapters/durable/journal.py
                                           -> recover_invalid_tail abre O_WRONLY (:189)
                                              y trunca (:191)
grep -c "    def " src/sirius_engine/ports/store.py
                                           -> 36 métodos en un solo Protocol; no hay
                                              puerto de solo lectura
registrar_gasto sobre un WorkItem en WAITING (ejecutado)
                                           -> Run muerto, WorkItem en waiting,
                                              IllegalTransitionError, sin escalada
```

Añadidas al verificar la ronda 2:

```
grep -rn "project_worker_request|compute_permission_envelope|resolve_capabilities|
          validar_egress_fail_closed|ContextFragment\(" src/ tests/
                                           -> ningún llamador en src/; solo en tests/
grep -rln sirius_engine .github/ scripts/  -> vacío: el motor no está cableado a nada
sed -n '/\[project.scripts\]/,/^\[/p' pyproject.toml
                                           -> sirius, sirius-voz, sirius-obs (ninguno del motor)
find . -name "*.jsonl" -not -path "./.git/*"
                                           -> vacío: no existe ningún diario en disco
grep -n allowedTools .github/workflows/*.yml
                                           -> revisor: --dangerously-skip-permissions
                                              --allowedTools "Bash,Read,Grep,Glob"
                                              auditor: Read,Grep,Glob,Write,Bash(git log:*)…
                                              + --disallowedTools "Task"
registrar_gasto sobre un WorkItem DELIVERED (ejecutado)
                                           -> IllegalTransitionError: cannot escalate
                                              WorkItem while in state DELIVERED
```
