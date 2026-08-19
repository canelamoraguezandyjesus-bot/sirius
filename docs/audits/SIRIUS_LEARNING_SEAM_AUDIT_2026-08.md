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

> Consecuencia de numeración para esta rama: `scripts/siguiente_adr.py` devuelve
> `43` tanto en `main` como en la rama de A5. Este trabajo toma **ADR-043**; el
> duplicado de A5 debería renumerarse a **ADR-044**, no a 043.

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
| d | «Agent Profile no contiene provider/model/credenciales/estado» | **CIERTO** | `domain/profile.py:38-48`: `ref, version, mision, procedimiento_ref, capacidades, permisos, contrato_entrada, contrato_salida`. Sin modelo ni proveedor |
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

- `AgentProfile` **no tiene** campo de modelo ni proveedor (`domain/profile.py:38-48`).
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

### 2.3 Piezas que ya existen con otro nombre

Tres, y ninguna es reutilizable tal cual:

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

- `AgentProfile` (`domain/profile.py:38-48`): sin modelo, sin proveedor, sin
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
- `validar_egress_fail_closed` (`egress.py:29`): un fragmento **sin clasificar**
  impide arrancar siempre; con red concedida, cualquier fragmento no
  `exportable` también.
- **Veredicto — y es una buena noticia**: la invariante «el Extractor y el
  Refutador **no pueden** crear/modificar/borrar conocimiento activo» **sí es
  expresable de forma estructural hoy**, sin código nuevo del motor. Basta que
  el conocimiento activo se escriba a través de una capacidad registrada (p. ej.
  `conocimiento.escribir`, `escritura: true`, `ambitos_escritura:
  [conocimiento]`) y que los perfiles de Extractor y Refutador declaren
  `permisos.escritura: null`. El Resolver rechaza entonces esa capacidad por dos
  motivos independientes, sin depender de ninguna instrucción de prompt. Es la
  diferencia entre «se lo hemos pedido» y «no puede».

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

## 4. Qué ya existe y se reutiliza tal cual

Sin construir nada:

| Necesidad del brief | Ya existe | Dónde |
|---|---|---|
| Historia durable e íntegra del trabajo | Diario JSONL con checksum y `fsync` | `adapters/durable/journal.py` |
| Reconstrucción de «qué pasó» | `rebuild_state()` + `list_events()` | `domain/events.py:56`, `ports/store.py:202` |
| Recuperación determinista antes de gastar IA | `contexto.recuperar` sin LLM, con citas | `context_recall.py` |
| «Lectura caída ≠ no hay» | `proveedores_fallidos` | `context_recall.py:55-59` (ADR-036) |
| Filtro de fuente no confiable en la vía GitHub | `es_autor_de_confianza` | `mirror_projection.py:80-82` |
| Least privilege estructural | `PermissionEnvelope` + Resolver + registro cerrado | §3.6 |
| Egress fail-closed por fragmento | `validar_egress_fail_closed` | `egress.py:29` |
| Perfiles sustituibles sin modelo dentro | `AgentProfile` + `profile_registry` | `domain/profile.py` |
| Refutación obligatoria por hallazgo | Regla ya vigente para el Auditor | ADR-010 |
| Conocimiento versionado, corregible y reversible (diseño) | Memoria/decisiones de V4 | `src/sirius/domain/memory.py`, `decision.py`, `precedence.py` |
| «Inspect AI no es dueño del ciclo» | Ya decidido | `SIRIUS_WORK_ENGINE_INVENTARIO.md:187` |
| «No hay Agente de memoria» | Ya decidido | Arquitectura §9 |

Nueve de las trece piezas que el brief describe como diseño nuevo **ya están
construidas o ya están decididas**. Es el resultado más importante de este
contraste: el vertical de aprendizaje es mucho más pequeño de lo que los
adjuntos sugieren, y lo que queda es sobre todo **una puerta de promoción y un
canal de presentación**, no una arquitectura.

---

## 5. Gaps mínimos

Ordenados por lo que bloquean. «Mínimo» significa: sin esto, la garantía
correspondiente no se puede afirmar.

**GAP-1 — Identidad de modelo/runtime por Run.** `Run.worker` es una cadena sin
estructura; ni el perfil ni el `WorkerRequest` llevan modelo. Sin esto,
«Refutador con modelo distinto» no es comprobable (§2.2). *No es alcance de
aprendizaje*: la arquitectura §3.3 ya lo pide y el código diverge. Debe cerrarse
donde nace el dato, es decir, **cuando exista el primer adapter de Worker real**
(B1 / C2), no antes y no por el aprendizaje.

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

**No es un gap**: la imposibilidad estructural de escribir conocimiento activo.
Eso ya se puede expresar con el Resolver y el registro de capacidades (§3.6).

---

## 6. Dónde enganchar el aprendizaje, y por qué ahí

### 6.1 Las cuatro opciones reales, evaluadas

| Opción | Dónde | ¿Rompe un WorkItem entregado si falla? | ¿Toca el dominio? | ¿Toca A5? | ¿Exige clase nueva? | Veredicto |
|---|---|---|---|---|---|---|
| **O1** Dentro de la transición | `domain/work_item.py:186` `deliver()` | **Sí** | Sí | No | No | **Descartada**: el dominio es puro y sin efectos; un fallo del sidecar viviría dentro de la entrega |
| **O2** Dentro del puerto de almacén | `ports/store.py:73` `deliver_work_item()` | **Sí** | Puerto | No | No | **Descartada**: obliga a todas las implementaciones y mete el aprendizaje en la transición terminal |
| **O3** WorkItem de clase `aprendizaje` despachado por el motor | `WorkItemClass` + `_TABLA_AUTORIDAD` | No | Sí | **Sí** | **Sí** | **Descartada**: prohibida por el encargo y por el contrato §11.1; además convierte al aprendizaje en trabajo del motor y al sidecar en actor con autoridad |
| **O4** Lector del diario, fuera del camino de escritura | `ports/store.py:202` `list_events()` / el JSONL de `adapters/durable/journal.py` | **No** | **No** | **No** | **No** | **RECOMENDADA** |

### 6.2 La opción recomendada, en una frase

> **El aprendizaje v0 es un lector del diario, no un actor del motor. No tiene
> hook, no tiene estado en el motor, no crea WorkItems, no escribe nada activo, y
> se invoca por una orden del propietario.**

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
- **No exige tocar el dominio, ni el puerto, ni el códec, ni A5.** Cierra por
  construcción los criterios de parada 1 y 2 de ADR-043.
- **El motor sigue siendo dueño del estado**: el diario es la fuente, y el lector
  no tiene forma de escribir en él (`list_events()` es de lectura; el fichero se
  abre en `O_APPEND` solo desde `append_durably`).
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
ni `docs/canonical/`, ni `docs/evolution/STATUS.md`. Comprobable:

```
$ git diff --name-only origin/main...HEAD
docs/audits/SIRIUS_LEARNING_SEAM_AUDIT_2026-08.md
docs/decisions/ADR-043-….md
```

Ese predicado es el «arreglo que puede observar el fallo» de ADR-043.

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

### 8.3 Colocación propuesta

**Una fase propia, después del HITO M3, y no dentro de ninguna fase aprobada.**
No se reordena nada: se añade al final.

```
… FASE C … ── HITO M3 ──
 └─ FASE L — aprendizaje (PROPUESTA, no aprobada)
     L0  decisión del propietario: ampliar la excepción + puerta          [DECISIÓN]
     L1  lector de diario + Evidence Dossier determinista (sin modelo, sin candidatos)
     L2  perfiles Extractor y Refutador + staging propio; SHADOW: se generan
         candidatos y NO se activa nada
     L3  propuesta con cambio exacto y hash + canal de presentación (GAP-3)
     L4  Promotion Gate determinista + conocimiento activo v1
     L5  Curator, periódico + por señales, con cuarentena reversible
```

Razones de que sea después de M3, y no en M3 ni antes:

1. **GAP-6, corpus.** Hoy el motor ha ejecutado **cero** WorkItems reales
   (§1.2). M3 es el primer hito en el que existen tres clases de trabajo reales
   (programación, documentación, auditoría) ejecutadas por el motor. Diseñar
   aprendizaje contra casos ficticios produce reglas ficticias.
2. **GAP-1 y GAP-2 nacen antes.** La identidad de modelo por Run y el esquema de
   `WorkResult` **no son alcance de aprendizaje**: son divergencias respecto a la
   arquitectura §3.3 y §4.2 que se manifiestan en cuanto haya un Worker real.
   Corresponde cerrarlas en **B1** (primer Worker externo) y **C2** (despacho
   real), por su propio mérito. Si se cierran ahí, la Fase L no necesita tocar el
   dominio en absoluto. **Esto es una recomendación, no un cambio de alcance de
   esos bloques: la decide el propietario.**
3. **El disparo automático depende de D2/I4** (§2.1). Mientras el motor no corra
   como servicio supervisado, «al terminar el WorkItem» significa «cuando el
   propietario lo pida». Colocar la fase después de M3 permite que la versión
   automática llegue con D2 en vez de necesitar una excepción periódica nueva
   contra el contrato §9.1.

### 8.4 Lo que **no** debe reservarse ahora

Ni hueco en el plan aprobado, ni número de bloque, ni línea en `PLAN.md`, ni
entrada en la tabla de autoridad. Una fase que no está aprobada no se anota como
si lo estuviera: es la deriva PROC-011 (los siete primeros ADR siguieron
«PROPUESTO» tras fusionarse) vista del revés.

---

## 9. De manual a automático: las fases, con su condición de salida

Cada fase declara **qué la deja pasar a la siguiente**. Ninguna se declara
superada por sensación.

**Fase 0 — Sombra manual (L1+L2).**
El propietario ordena la revisión. Se generan candidatos. **Nada se activa.**
Ni siquiera se presenta como propuesta: se acumula y se mide.
*Salida*: haber visto suficientes WorkItems reales de **al menos dos clases
distintas** y tener medidas —no estimadas— las métricas de §10.3.

**Fase 1 — Propuesta manual (L3+L4).**
Candidato → Refutador independiente → cambio exacto con hash → aprobación
humana → Promotion Gate → activo. Sigue sin haber nada automático salvo la
generación del candidato.
*Salida*: una tasa de rechazo humano que el propietario considere aceptable, y
cero incidentes de las invariantes de §10.1.

**Fase 2 — Mantenimiento (L5).**
Curator entra, con cuarentena reversible. Toda corrección suya vuelve al mismo
pipeline de candidato → refutación → aprobación.
*Salida*: cuarentenas correctas y reversibles, verificadas.

**Fase 3 — Auto-promoción por clases (DISEÑADA, DESACTIVADA).**
Debe quedar escrita desde el primer día como destino y **no activarse**. El
criterio se decidirá con métricas reales de Sirius. **No se inventa ningún
umbral en este informe**, y recomiendo desconfiar de cualquiera que aparezca sin
datos detrás.
Restricción permanente, sea cual sea el umbral: **automatizar la promoción no
automatiza el gobierno.** Seguridad, permisos, privacidad, autoridad y
arquitectura siguen el contrato y los ADR, siempre.

---

## 10. Pruebas y puertas antes de activar nada

### 10.1 Invariantes que deben ser imposibles de violar, no improbables

Cada una con la forma de prueba que la sostiene. Todas deben verse **fallar** con
la mutación sembrada antes de darse por buenas (ADR-001, prueba por mutación).

| # | Invariante | Cómo se hace estructural (no por prompt) |
|---|---|---|
| I1 | Un modelo de aprendizaje no puede escribir conocimiento activo | El perfil declara `permisos.escritura: null`; la escritura de conocimiento es una capacidad registrada con `ambitos_escritura: [conocimiento]`. El Resolver la rechaza por dos guardas independientes (§3.6). Mutación: dar el ámbito al perfil y ver la prueba fallar |
| I2 | No se promueve sin Refutador de modelo distinto | **Hoy imposible de comprobar** (§2.2). Prueba pendiente de GAP-1. Mientras tanto, el Gate **debe fallar cerrado**: sin dato de modelo, no promueve |
| I3 | Una aprobación no permite aplicar un diff distinto | El Gate recalcula el hash del cambio materializado y lo compara con el aprobado. Mutación: alterar un byte y ver que no promueve |
| I4 | Un fallo transitorio no produce una prohibición general | Fixture: `run_failed` seguido de `run_retried` con `SUCCEEDED`. El candidato negativo, si existe, debe nombrar el recovery, no el fallo |
| I5 | Dos WorkItems que descubren lo mismo no crean dos conocimientos activos | Dedup contra activos + staged + rechazados **antes** de crear |
| I6 | Un candidato rechazado no vuelve idéntico | El rechazo se conserva con motivo y hash; reabrir exige evidencia materialmente nueva |
| I7 | Una fuente maliciosa no convierte texto fuente en instrucción persistente | La evidencia entra como **dato citado**, nunca como instrucción. Reutiliza `es_autor_de_confianza` y el patrón de `Referencia` (cita, no síntesis) |
| I8 | La cuarentena del Curator es reversible y el Curator no borra ni reescribe | El Curator no tiene capacidad de escritura de conocimiento; solo puede marcar. Mismo mecanismo que I1 |
| I9 | Una actualización de conocimiento no cambia el snapshot de un Run en marcha | El `WorkPackage` ya es «instantánea exacta de lo enviado» (`run.py:72`), inmutable por diseño. La versión del conocimiento se fija ahí |
| I10 | Un fallo de aprendizaje no convierte un WorkItem entregable en fallido | Estructural por §6: el lector está fuera del camino de escritura. Mutación: hacer explotar el lector y comprobar que el WorkItem sigue `DELIVERED` |
| I11 | El Promotion Gate falla cerrado | Cualquier dato ausente (refutador, hash, procedencia, clasificación) **no promueve**. Mutación: quitar cada dato por turnos |
| I12 | Ningún aprendizaje eleva permisos, egress, presupuesto ni autoridad | El Gate rechaza cualquier candidato cuyo cambio toque perfiles, registro de capacidades, contrato, ADR o `docs/canonical/`. Es una comprobación de rutas, determinista |
| I13 | Un aprendizaje negativo nace estrecho, y eso no depende del buen juicio del modelo | El Gate rechaza todo candidato negativo cuyo `negative_scope` no nombre Worker, modelo, runtime, versión y entorno observados. Comprobación de campos, no juicio. **Depende de GAP-1**: sin identidad de modelo, el campo no se puede rellenar (ver §11, A8) |

I12 merece una nota: es la traducción mecánica de «GOVERNANCE nunca se
autoaprende» (§7). Una lista de rutas prohibidas es comprobable; una promesa de
buen juicio no.

### 10.2 Fixtures mínimas de evaluación

Las diez del brief §16 siguen siendo las correctas, y ahora se pueden construir
de una forma que antes no: **como secuencias de eventos del diario**, no como
conversaciones. Éxito con técnica reutilizable; éxito sin nada nuevo; fallo de un
Worker y éxito de otro (`run_worker_substituted`); fallo por credencial/setup;
fallo transitorio seguido de reintento correcto (`run_failed` → `run_retried`);
corrección del revisor (`work_item_repair_requested`); candidato duplicado;
candidato que contradice conocimiento activo; candidato atractivo sin evidencia;
evidencia con inyección de prompt.

### 10.3 Métricas de sombra (se miden, no se fijan)

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

**Corrección aplicada**: L1/L2 **no inventan un arnés nuevo**. Reutilizan el
patrón de perfil y el esquema de hallazgo del Auditor (`AUDITOR_AGENT_V0.md`,
`FINDING-###` con evidencia + refutación) y añaden solo los campos que el
Auditor no necesita: aplicabilidad, alcance negativo, cambio exacto y hash. Si
al construirlo resulta que el Extractor **es** el Auditor con otro perfil, mejor:
eso es una capacidad, no un subsistema.

### A2 — «El Refutador es un revisor más con otro nombre»

**Intento de demostración.** El motor ya tiene la fase REVISAR con un Worker de
perfil independiente y salida cerrada (`APPROVED | CHANGES_REQUIRED |
DECISION_REQUIRED`, arquitectura §3.4), y la regla de que el revisor no arregla
lo que revisa. El Refutador es exactamente eso.

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

**Consecuencia aplicada al diseño**: **L4 (conocimiento activo) queda bloqueado**
hasta que el propietario decida la pregunta de §9. Las fases L1–L3 no la
necesitan: producen candidatos y propuestas, no conocimiento activo. Es una
decisión real, y sube como tal (§12, D-4).

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

## 12. Decisiones que de verdad necesitan al propietario

Solo las que no se pueden cerrar con evidencia. Cada una dice qué bloquea y qué
recomiendo, para que se pueda decidir sin reconstruir nada.

**D-1 — ¿Se autoriza siquiera explorar este vertical?**
La excepción de `docs/evolution/STATUS.md:27-35` ampara el Work Engine
«estrictamente según ADR-020 y su plan aprobado». El aprendizaje no está en ese
plan, así que **hoy no está autorizado ni en su forma mínima**. Además introduce
perfiles de agente nuevos, que activan el criterio de parada de `AGENTS.md`.
*Bloquea*: todo lo demás. *Recomiendo*: autorizar **solo la Fase L0–L1**
(lector de diario y dossier determinista, sin modelos y sin candidatos), que no
introduce ningún agente, y volver a decidir con esa evidencia delante.

**D-2 — ¿El aprendizaje llega a ser alguna vez una clase de trabajo?**
Hoy no puede: `WorkItemClass` es cerrado y el contrato §11.1 dice que «una clase
que no aparezca aquí no puede crear WorkItems hasta que se añada» — lo que exige
enmendar el contrato v1.7 y tocar la tabla de A5.
*Recomiendo*: **no**, ni ahora ni en v0. El diseño de §6 está construido
precisamente para no necesitarlo. Si más adelante se quiere, es una enmienda de
contrato con su propio ADR, no un efecto colateral.

**D-3 — Presupuesto del aprendizaje.**
`Budget` no se persiste (§3.7) y el sidecar corre después de que el WorkItem sea
terminal: **no hay presupuesto al que cargarse**. Cualquier llamada a modelo es
gasto nuevo, causa 2 de escalado.
*Recomiendo*: fijar un tope explícito y pequeño para la fase de sombra, y que el
corte al agotarlo sea determinista. No fijo ninguna cifra: no tengo dato.

**D-4 — ¿Segunda memoria? (la objeción A4, que sobrevivió)**
La arquitectura §9 dice que el sustrato de memoria ya existe en el producto y que
exponerlo como capacidad es trabajo futuro sobre código existente. Si el motor
construye su propia MEMORY activa antes de decidir eso, Sirius acaba con dos.
*Bloquea*: **L4 (conocimiento activo)**, y solo eso. *Recomiendo*: decidir esta
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

**D-6 — ¿Se corrige la divergencia con la arquitectura §3.3 en B1/C2?**
`Run.worker` es una cadena sin estructura y no hay identidad de modelo/runtime
(GAP-1); `WorkPackage`/`WorkResult` no tienen esquema (GAP-2). Ambas son
divergencias respecto de la arquitectura **aprobada**, no ampliaciones pedidas
por el aprendizaje. Cerrarlas donde nacen —el primer Worker real— cambia el
alcance de bloques aprobados, y eso es del propietario.
*Recomiendo*: sí, y **por su propio mérito**: sin identidad de modelo tampoco se
puede comparar dos Runs, ni explicar por qué se sustituyó un Worker, ni sostener
la invariante I2 ni la I13.

**D-7 — ¿Cuándo, si acaso, el disparo pasa a ser automático?**
Hoy exige o enmendar el contrato §9/§9.1 (que ya gastó su única ejecución
periódica en el reconciliador) o esperar a D2, donde el motor corre como
servicio supervisado y el barrido es parte de su propio ciclo.
*Recomiendo*: **esperar a D2**. Gastar una enmienda de contrato para automatizar
un sidecar sobre un corpus inexistente es el peor cambio posible por unidad de
riesgo.

**D-8 — La colisión de ADR-042 en la PR #207.**
No es de aprendizaje, pero bloquea A5 con una comprobación en rojo real y
reproducida (§1.3). *Recomiendo*: renumerar el ADR de A5 a **ADR-044** —no a
043, que toma este trabajo— y volver a pasar
`tests/automation/test_registro_de_decisiones.py`. Es la decisión del propietario
sobre su propia PR; aquí solo se reporta con la evidencia.

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

## 14. Lo que este informe NO garantiza

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

## 15. Comprobaciones que sostienen este informe

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
