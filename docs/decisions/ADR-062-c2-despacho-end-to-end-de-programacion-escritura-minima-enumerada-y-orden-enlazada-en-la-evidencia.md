# ADR-062 — C2 — despacho end-to-end de programación: escritura mínima enumerada y orden enlazada en la evidencia

- Estado: APROBADO
- Fecha: 2026-08-21
- Aprobación: la fusión de la PR de la incidencia #240 por el propietario
- Nota de arranque de esta rama: este ADR. Publicado y con criterio de parada
  fijado antes del primer commit de código de este bloque.

## Contexto y problema

C2 (incidencia #240) cierra el círculo del propietario-no-mensajero para la
clase `programacion`: el motor debe generar el cuerpo de una incidencia desde
la plantilla real, aplicar `sirius:implement-requested` con su propia
identidad, y dejar el episodio completo en un diario propio — sin que el
propietario toque GitHub. El contrato v1.8 §12.1 lo autoriza con una condición
sin excepción: **solo si existe una orden explícita del propietario,
registrada y enlazada en la evidencia del WorkItem**. El motor no tenía, hasta
este bloque, ningún adapter que escribiera en GitHub — toda la infraestructura
existente (`github_cli_mirror.py`, `github_actions_run_probe.py`) es de solo
lectura — así que este bloque estrena esa capacidad, con el riesgo que declara
la propia incidencia: que la escritura se amplíe "ya que estamos" más allá de
las dos operaciones enumeradas (crear la incidencia, aplicar la etiqueta), o
que la comprobación de "orden enlazada" se relaje y el motor pase de
transportar órdenes a inventarlas.

`WorkItem.evidencia` (arquitectura §3.1: "referencias al diario y a
artefactos") existe en el dominio desde A1 pero, antes de este bloque, ningún
código lo poblaba: era un campo sin consumidor. C2 es su primer consumidor
real.

## Criterio de parada (escrito ANTES de decidir)

Antes de escribir código: si terminar este bloque exige (a) cablear
`SIRIUS_BOT_TOKEN` en un workflow de `.github/`, (b) ampliar la escritura del
adapter más allá de "crear incidencia" + "aplicar etiqueta", o (c) relajar de
cualquier forma la comprobación de orden enlazada para que un WorkItem sin
evidencia pueda activarse — se detiene con `BLOCKED_BY_DECISION` o
`FAILED_SAFELY` según corresponda, y no se decide por cuenta propia. Dos
rondas de revisión con defectos de la misma familia (por ejemplo, dos hallazgos
sobre el mismo verbo de escritura no enumerado) paran la implementación para
buscar la raíz en vez de seguir parcheando puntualmente.

Las seis pruebas de terminado de la incidencia (C2-P1 a C2-P6) y las tres
mutaciones de la sección siguiente son el criterio objetivo de "terminado":
sin las nueve en verde (seis pruebas + tres mutaciones sembradas y revertidas),
el bloque no se declara `READY_FOR_REVIEW`.

## Opciones consideradas

1. **Requerir una llamada de red real a GitHub para verificar "orden
   enlazada"** (por ejemplo, comprobar que existe un comentario del
   propietario en una incidencia). Descartada: el despachador debe poder
   decidir sobre un `WorkItem` que puede no tener proyección GitHub todavía
   (es él quien la va a crear); exigir una lectura de red para una guarda que
   debe ser determinista y comprobable sin infraestructura contradice el
   patrón ya establecido por `gate.py`/`work_intake.py` (puros, sin E/S).
2. **Usar `WorkItem.contexto_origen` como la señal de orden enlazada**, en vez
   de `evidencia`. Descartada: `contexto_origen` es "referencias autorizadas
   (proyecto, incidencias, documentos, decisiones)" — un campo más amplio y ya
   usado con otro propósito (proyectar `WorkerRequest`); mezclar ambos usos
   haría ambigua la señal. `evidencia` es exactamente "qué lo demuestra" según
   la arquitectura §3.1, y no tenía consumidor: es el campo correcto.
3. **Definir un prefijo reconocible dentro de `evidencia`**
   (`orden-propietario:<referencia>`) y una función pura
   (`orden_enlazada`) que lo busca. **Elegida.** Determinista, sin E/S,
   comprobable con un `WorkItem` construido directamente en una prueba
   (`dataclasses.replace`), y no exige tocar `create_work_item`/`WorkEngineStore`
   — ninguna otra vertical queda afectada.
4. **Ampliar el puerto de escritura con métodos de conveniencia** (por ejemplo,
   un método combinado `crear_y_etiquetar`). Descartada: el alcance permitido
   de la incidencia es explícito ("la escritura es MÍNIMA y enumerada"); un
   método combinado sigue siendo dos verbos de escritura reales pero oculta la
   cuenta, y la prueba estructural de C2-P4 dejaría de poder contarlos por
   separado.
5. **Guardar el diario de despacho en el mismo `SupervisorJournal` de C1**
   (reutilizar el puerto existente). Descartada: C1 indexa por `run_id` (un
   Run puede perderse y repararse varias veces); C2 indexa por `work_id` (un
   WorkItem de clase `programacion` se despacha una única vez, nunca por Run).
   Forzar la misma clave rompería la semántica de idempotencia de C1. Se creó
   un puerto hermano (`DispatchJournal`) en vez de sobrecargar el existente.

## Decisión

1. **Orden enlazada**: `WorkItem.evidencia` es una tupla de texto libre; una
   entrada que empieza por el marcador `orden-propietario:` seguido de una
   referencia no vacía es la señal exigida por el contrato §12.1.
   `sirius_engine.domain.dispatch.orden_enlazada(work_item)` es la función
   pura y total que la busca; sin ella, `dispatch_work_item` levanta
   `OrdenNoEnlazadaError` **antes** de proyectar o escribir nada.
2. **Escritura mínima enumerada**: `GitHubWriterPort`
   (`sirius_engine/ports/github_writer.py`) declara exactamente dos métodos —
   `crear_incidencia`, `aplicar_etiqueta` — y una prueba estructural
   (`test_github_writer_port.py`, `test_github_cli_writer.py`) falla si el
   puerto o el adapter real ganan un tercero. El adapter real
   (`GitHubCliWriter`, `adapters/github_cli_writer.py`) usa `gh issue create`
   / `gh issue edit --add-label` vía `subprocess`, con el mismo patrón de
   `ejecutar` inyectable que `github_cli_mirror.py` (A3): ninguna prueba toca
   la red de verdad.
3. **Credencial**: `GitHubCliWriter` lee `SIRIUS_BOT_TOKEN` del entorno del
   proceso en `__post_init__` (al construirse, no en el primer uso) y levanta
   `MissingCredentialError` con el nombre exacto de la variable si falta. No
   se cablea ningún workflow — eso queda fuera de este bloque, tal como exige
   la incidencia #240.
4. **Idempotencia (una sola activación por WorkItem)**: `DispatchJournal`
   (puerto hermano de `SupervisorJournal`, indexado por `work_id`) se consulta
   ANTES de cualquier otra guarda; si ya hay un episodio para el `work_id`, se
   devuelve ese mismo episodio sin escribir nada más.
5. **Cuerpo desde la plantilla**: `generar_cuerpo_incidencia` proyecta las once
   secciones que exige `scripts/automation/validate_issue_body.py` con el
   contenido real del `WorkItem`, más el campo `Perfil: <ref>@<version>` de A4
   (`profile_field.project_perfil_field`). Se valida con el propio script
   real, no con una copia de sus reglas.
6. **Alcance de clase**: el despachador solo actúa sobre
   `WorkItemClass.PROGRAMACION` (`ClaseNoDespachableError` en cualquier otro
   caso) — es exactamente lo que la incidencia #240 autoriza; documentación
   (C3) y auditoría (C4) son bloques futuros, no se inventan aquí.

## Comprobación que la sostiene

Las seis pruebas de terminado, cada una en el fichero donde su comprobación es
más directa:

- **C2-P1** (`tests/engine/test_dispatcher.py::test_c2_p1_*`): sin orden
  enlazada, `OrdenNoEnlazadaError` y ninguna escritura; con orden enlazada, se
  despacha.
- **C2-P2** (`tests/engine/test_issue_body_projection.py`): el cuerpo generado
  se valida ejecutando `scripts/automation/validate_issue_body.py` como
  subproceso real (misma vía que `tests/automation/test_validate_issue_body.py`).
- **C2-P3** (`test_dispatcher.py::test_c2_p3_*`): dos pasadas sobre el mismo
  WorkItem producen una sola activación (dos llamadas de escritura en total,
  no cuatro).
- **C2-P4** (`test_github_writer_port.py`, `test_github_cli_writer.py`,
  `test_dispatcher.py::test_c2_p4_*`): el puerto y el adapter real solo
  exponen los dos verbos enumerados; un doble de prueba lanza
  `AssertionError` ante cualquier otro.
- **C2-P5** (`test_github_cli_writer.py::test_sin_credencial_*`): sin
  `SIRIUS_BOT_TOKEN` en el entorno, `MissingCredentialError` al construir el
  adapter, antes de cualquier escritura.
- **C2-P6** (`test_dispatcher.py::test_c2_p6_*`): el episodio se reconstruye
  leyendo solo `journal.episodes()`, sin invocar `writer` ni GitHub.

Comandos ejecutados y resultado:

```
uv run ruff format --check .   → 468 files already formatted
uv run ruff check .            → All checks passed!
uv run mypy src tests          → Success: no issues found in 446 source files
uv run pytest -q               → 3220 passed, 6 skipped in 323.55s
git diff --check               → sin salida (limpio)
uv run pytest tests/engine/test_boundary.py -q   → 2 passed (sin modificarlo)
```

Prueba por mutación (sembrada, verificada y revertida en la misma sesión, sin
dejar rastro en el árbol final):

1. **Quitar la comprobación de la orden enlazada** — se sustituyó
   `if referencia_orden is None: raise OrdenNoEnlazadaError(...)` por
   `referencia_orden = orden_enlazada(work_item) or "sin-orden"` en
   `dispatcher.py`. Resultado: `test_c2_p1_sin_orden_enlazada_no_aplica_la_etiqueta`
   cae (`Failed: DID NOT RAISE OrdenNoEnlazadaError`). Revertido; suite verde
   de nuevo.
2. **Permitir un verbo de escritura no enumerado** — se añadió un método
   `comentar(...)` a `GitHubWriterPort`. Resultado:
   `test_el_puerto_declara_exactamente_los_dos_verbos_enumerados` cae
   (`Extra items in the left set: 'comentar'`). Revertido; suite verde de
   nuevo.
3. **Quitar el marcador de idempotencia** — se eliminó el bloque
   `episodio_previo = journal.episode_for(...); if episodio_previo is not
   None: return ...` de `dispatch_work_item`. Resultado:
   `test_c2_p3_dos_pasadas_producen_una_sola_activacion` cae
   (`assert False is True` sobre `segundo.ya_despachado`). Revertido; suite
   verde de nuevo.

Las tres mutaciones hicieron caer exactamente la prueba que debían: ninguna
prueba resultó "sorda" a su propia guarda.

## Consecuencias

- El motor gana su primera capacidad de escritura real en GitHub, acotada por
  construcción a dos verbos y comprobada estructuralmente — no solo por
  convención de código.
- `WorkItem.evidencia` deja de ser un campo sin consumidor: su primer uso real
  fija su convención (`orden-propietario:<referencia>`), que cualquier bloque
  futuro que también necesite registrar evidencia debería respetar o extender
  explícitamente, no reinterpretar.
- Riesgo aceptado y documentado, no resuelto por este bloque: si
  `aplicar_etiqueta` falla DESPUÉS de que `crear_incidencia` ya tuvo éxito, no
  se registra episodio (misma disciplina que `supervisor.py` en C1: "un fallo
  no deja el trabajo peor, pero tampoco lo completa solo") y un reintento
  futuro volvería a crear una incidencia nueva en vez de reutilizar la ya
  creada. Es la misma limitación que C1 ya acepta para sus propias acciones;
  cerrarla (por ejemplo, buscando en GitHub una incidencia ya creada para el
  mismo `work_id` antes de reintentar) es trabajo de un bloque futuro, no de
  C2 — ampliar la lectura para resolverlo tampoco está en el alcance permitido
  de la incidencia #240.
- Cablear `SIRIUS_BOT_TOKEN` en un workflow real, y el encargo de demostración
  real end-to-end con un WorkItem real, quedan fuera de este bloque por
  decisión explícita de la incidencia #240 (frontera de `.github/**` y
  demostración supervisada), no por omisión.

## Alternativas descartadas y por qué

Ver «Opciones consideradas» arriba: cada alternativa incluye su razón de
descarte en el mismo punto, para no duplicar el argumento.
