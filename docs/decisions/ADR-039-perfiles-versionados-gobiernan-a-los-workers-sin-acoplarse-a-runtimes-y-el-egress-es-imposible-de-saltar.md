# ADR-039 — Perfiles versionados gobiernan a los Workers sin acoplarse a runtimes, y el egress es imposible de saltar

- Estado: APROBADO — por la fusión de la PR que acompaña a esta rama.
- Fecha: 2026-08-19
- Aprobación: la fusión de la PR de este bloque (A4) por el propietario.
- Este documento ES la nota de arranque de la rama (skill `disciplina-evidencia`):
  publicada aquí, no como comentario en la incidencia, porque el contrato de
  ejecución de esta ronda («implementador genérico de Sirius», incidencia #202)
  restringe los comentarios de la incidencia a un único texto fijo
  (`PR abierta: <URL>`). El ADR es el lugar visible que sí queda disponible, tal
  como la propia skill prevé («si no [existe la incidencia como canal libre],
  el ADR de la rama»).

## Contexto y problema

La incidencia #202 (SIRIUS-WORK-ENGINE-A4-001) pide el último bloque de la
Fase A del Work Engine que no necesita ninguna decisión humana previa:
perfiles de agente versionados, la proyección determinista `WorkerRequest`
(arquitectura §5.1), un `PermissionEnvelope` calculado por el motor
(deny-by-default), un Capability Resolver v0 con registro versionado (§6) y
un validador de egress fail-closed (§6.1).

Hoy ninguna de estas piezas existe como código: el gobierno de un Worker vive
disperso en tres sitios que no se comunican entre sí —el paso "Preparar
instrucciones para Claude Code" de `.github/workflows/implement-sirius-work.yml`
concatena el prompt de rol con un puñado de líneas de contexto; el modo
`--dangerously-skip-permissions` no calcula ningún permiso real; y no existe
ninguna política de clasificación para el contexto que viajaría a un Worker
con red externa. La arquitectura mínima (`SIRIUS_WORK_ENGINE_ARQUITECTURA_MINIMA.md`
§5.1, §6, §6.1) ya especifica la forma que debe tener esto; A4 la construye.

## Criterio de parada (escrito ANTES de decidir)

Publicado antes de tocar código, siguiendo el método de la skill
`disciplina-evidencia`:

1. **¿Dónde vive el fallo (la ausencia) y dónde va el arreglo? ¿Puede el sitio
   del arreglo OBSERVAR lo que soluciona?** La ausencia de proyección
   determinista, `PermissionEnvelope` y egress fail-closed vive fuera de
   `src/sirius_engine/` (dispersa en el workflow y en el modo de ejecución del
   Worker). El arreglo vive DENTRO de `src/sirius_engine/` —código nuevo, no el
   sitio que falla— y sí puede observar lo que debe igualar: la prueba de
   no-divergencia (A4-P2) no reimplementa la lógica del workflow en Python,
   ejecuta el guión bash REAL del paso "Preparar instrucciones para Claude
   Code" (leído de `.github/workflows/implement-sirius-work.yml`, nunca
   modificado) y compara su salida, byte a byte, contra la proyección de este
   bloque. Si el workflow cambiara ese paso sin que la proyección lo siguiera,
   la prueba cae en rojo automáticamente, en vez de depender de que alguien se
   acuerde de revisar la coincidencia a mano.
2. **¿Qué NO va a garantizar esto?**
   - No garantiza que `implement-sirius-work.yml` YA USE los perfiles: ese
     cambio de workflow es C3, hecho en sesión interactiva (ADR-002), fuera de
     este bloque. A4 entrega la proyección, el campo `Perfil: <ref>@<version>`
     y la prueba de que, si se usara hoy, produciría el mismo resultado.
   - No garantiza una política de egress completa: solo v0 (clasificación
     obligatoria por fragmento + incompatibilidad estructural red+escritura).
   - No garantiza que Codex o el Auditor tengan Adapter activo: solo su
     perfil versionado como dato.
   - No garantiza que el registro de capacidades sea exhaustivo: es v0,
     cerrado pero mínimo, ampliable por decisión explícita (mismo patrón
     heredado de `registro_de_acciones.yml`, PR #171).
3. **Criterio de parada, decidido ahora:**
   - Si la prueba de no-divergencia (A4-P2) exigiera tocar `.github/**` o
     `scripts/automation/**` para que la proyección coincidiera, me detengo con
     `BLOCKED_BY_DECISION` y no aplico el cambio (regla explícita de la
     incidencia).
   - Si hiciera falta una dependencia nueva más allá de `pyyaml` (ya presente
     en el proyecto), me detengo con `BLOCKED_BY_DECISION`.
   - Dos rondas de revisión propia con defectos de la misma familia (por
     ejemplo, dos casos de degradación silenciosa en el Resolver) → paro,
     busco la raíz en vez de seguir parcheando.
   - Cierro con `READY_FOR_REVIEW` solo si las cinco pruebas de terminado
     (A4-P1..P5) están en verde, las tres mutaciones sembradas exigidas por la
     incidencia fallan como se espera, y las cuatro validaciones obligatorias +
     `git diff --check` + `tests/engine/test_boundary.py` (sin tocarlo) están
     en verde.
4. **¿Qué hace el fallo IMPOSIBLE en vez de improbable?**
   - Capacidad no registrada: `resolve_capabilities` lanza
     `UnknownCapabilityError`, sin ninguna rama de código que devuelva un
     proveedor por defecto o "el más parecido".
   - Permisos: `PermissionEnvelope` se calcula por una única función pura del
     motor (`compute_permission_envelope`) a partir del perfil; ninguna
     función pública de este bloque acepta un envelope construido por otra
     vía, así que no existe un camino por el que un Worker se declare sus
     propios permisos.
   - Egress: la clasificación se comprueba ANTES de construir el
     `WorkerRequest` (dentro de `project_worker_request`, antes de resolver
     ninguna capacidad); la construcción falla entera, no hay un
     `WorkerRequest` parcial que alguien pueda usar por error.
   - Determinismo: todos los tipos de entrada (`WorkItem`, `AgentProfile`,
     `PermissionEnvelope`, `ContextFragment`) son `frozen=True` con tuplas o
     `MappingProxyType`, así que no hay mutación oculta entre dos llamadas a
     `project_worker_request` con los mismos argumentos.

## Opciones consideradas

1. **Perfiles como texto duplicado dentro de cada fichero de datos** (copiar
   el contenido de `scripts/automation/prompts/*.md` dentro del YAML del
   perfil). Descartada: crea dos fuentes de verdad que pueden divergir sin que
   nada lo detecte, exactamente el riesgo que la propia incidencia nombra como
   principal ("perfiles que digan más que los prompts reales").
2. **`PermissionEnvelope` como estructura que el propio `AgentProfile`
   expone directamente** (sin una función de cómputo separada). Descartada:
   no deja sitio para que el motor aplique ninguna regla propia (como la
   incompatibilidad de egress §6.1 regla 1) sin que el perfil tenga que
   conocerla; separar `compute_permission_envelope` dijo explícitamente
   "esto lo calcula el motor", no el dato.
3. **Prueba de no-divergencia (A4-P2) reimplementando en Python la lógica de
   concatenación del workflow**, en vez de ejecutar su guión bash real.
   Descartada: es exactamente el patrón que permite que el prompt real
   cambie sin que la prueba se entere —dos implementaciones del mismo
   algoritmo que pueden divergir en silencio—. Ejecutar el guión bash
   extraído del propio fichero YAML del workflow (leído, nunca modificado)
   cierra esa vía de deriva.
4. **Egress fail-closed aplicado sin condición, a todo fragmento de contexto
   sin importar si el Worker tiene red o no.** Descartada tal cual: forzaría
   a que hasta el contexto puramente interno de un Worker sin ningún acceso a
   red (el implementador, que nunca sale del repositorio) se clasificara
   como "exportable", una etiqueta que no describe la realidad y que
   generaría fricción sin ganancia de seguridad. Se adoptó una regla en dos
   partes en su lugar: la clasificación es SIEMPRE obligatoria (un fragmento
   sin clasificar bloquea `START` pase lo que pase, arquitectura §4.1), y la
   exigencia de que sea específicamente `"exportable"` se activa solo cuando
   el perfil tiene red externa concedida (§6.1 regla 2: "todo contexto que
   viaja a un Worker con red externa pasa por ExportSafeBrief"). Es la
   lectura literal de la arquitectura citada por la propia incidencia
   ("validador de egress fail-closed (§6.1) con clasificación por
   fragmento").

## Decisión

Se implementan, dentro de `src/sirius_engine/` y `tests/engine/`:

- **`domain/profile.py`**: `AgentProfile` y `ProfilePermissions` — perfil de
  agente versionado como dato puro. Nunca nombra herramientas: solo misión,
  referencia al procedimiento real en el árbol (`procedimiento_ref`),
  capacidades abstractas, permisos declarados y contrato de entrada-salida.
- **`docs/implementation/work_engine/perfiles/*.yml`**: los cuatro perfiles
  reales —`implementer`, `reviewer`, `corrector`, `auditor`— como datos
  versionados. Cada uno referencia su procedimiento real
  (`scripts/automation/prompts/*.md` o `AUDITOR_AGENT_V0.md`) sin duplicar su
  texto.
- **`domain/context_fragment.py`**: `ContextFragment`, con clasificación
  obligatoria (`"privado" | "exportable" | None`) como dato del WorkPackage
  (arquitectura §4.1).
- **`domain/permission_envelope.py`**: `PermissionEnvelope` y
  `compute_permission_envelope` — el envelope efectivo de un Run, calculado
  SIEMPRE por el motor a partir del perfil, deny-by-default (concede
  exactamente lo declarado, nunca más), y fail-closed ante la
  incompatibilidad estructural de §6.1 regla 1 (red externa + escritura
  irrestricta a la vez → `EgressIncompatibleError`, ninguna concesión).
- **`capability_registry.py`** + `docs/implementation/work_engine/perfiles/registro_capacidades.yml`:
  registro CERRADO de capacidades, heredero directo del patrón de
  `registro_de_acciones.yml` (PR #171): comparación por nombre exacto, sin
  degradar una capacidad ausente a la más parecida.
- **`capability_resolver.py`**: `resolve_capabilities` — dos guardas
  independientes sin degradación: capacidad no registrada →
  `UnknownCapabilityError` (A4-P4); capacidad registrada pero no concedida
  por el envelope → `CapabilityNotGrantedError`, nunca recortada ni sustituida
  (A4-P5).
- **`egress.py`**: `validar_egress_fail_closed` — un fragmento sin clasificar
  bloquea `START` siempre; con red externa concedida, además exige
  `"exportable"` en cada fragmento (A4-P3).
- **`worker_request.py`**: `WorkerRequest` y `project_worker_request` — la
  proyección determinista completa (WorkPackage + perfil + capacidades +
  envelope → WorkerRequest), con el orden fijo egress-antes-que-resolución
  (A4-P1).
- **`adapters/github_worker_request.py`**: `project_github_prompt` y
  `read_procedure_text` — la proyección específica del Adapter GitHub que
  reproduce, byte a byte, la concatenación que hoy hace
  `implement-sirius-work.yml` (A4-P2).
- **`profile_field.py`**: `parse_perfil_field` / `project_perfil_field` — el
  campo declarativo `Perfil: <ref>@<version>` del cuerpo de un Work Item,
  retrocompatible (su ausencia es un valor válido: `None`).
- **`profile_registry.py`**: `load_agent_profile` — carga determinista de un
  perfil versionado desde su fichero de datos.

No se modificó `.github/**` ni `scripts/automation/**`: la incidencia #202 lo
prohíbe explícitamente y ninguna parte de este bloque lo necesitó — la prueba
de no-divergencia LEE el workflow para ejecutarlo tal cual, no lo edita.

## Comprobación que la sostiene

Las cuatro validaciones obligatorias, en verde sobre el repositorio completo:

```
$ uv run ruff format --check .
408 files already formatted

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests
Success: no issues found in 389 source files

$ QT_QPA_PLATFORM=offscreen uv run pytest -q
2704 passed, 5 skipped in 434.46s (0:07:14)

$ git diff --cached --check
(sin salida; exit 0)

$ QT_QPA_PLATFORM=offscreen uv run pytest tests/engine/test_boundary.py -q
2 passed in 0.18s   # sin modificar el fichero
```

Nota sobre la primera ejecución completa de la suite: apareció un único fallo
aislado, `tests/gui/test_model_studio_integration.py::test_nothing_is_said_twice`
(un `waitUntil` de Qt con margen de 5000 ms para que un `FakeTextToSpeech`
reciba una segunda petición). Repetido en aislamiento, pasó
(`1 passed in 2.32s`); es un test de temporización de la interfaz de voz, ajeno
por completo a este bloque (no toca `src/sirius_engine/`, `docs/implementation/work_engine/`
ni ningún fichero de este cambio) y sensible a la carga del runner al correr
junto a más de 2700 pruebas. Se deja constancia aquí en vez de silenciarlo.

**Prueba por mutación (ADR-001 §3), las tres exigidas por la incidencia,
sembradas y vistas fallar, luego revertidas:**

1. Quitar la comprobación de clasificación de egress
   (`validar_egress_fail_closed` sustituida por un `return` inmediato) →
   ```
   $ QT_QPA_PLATFORM=offscreen uv run pytest tests/engine/test_egress.py tests/engine/test_worker_request.py -q
   5 failed, 13 passed in 0.39s
   FAILED tests/engine/test_egress.py::test_fragmento_sin_clasificar_impide_start_incluso_sin_red
   FAILED tests/engine/test_egress.py::test_fragmento_sin_clasificar_impide_start_con_red
   FAILED tests/engine/test_egress.py::test_fragmento_privado_con_red_concedida_impide_start
   FAILED tests/engine/test_egress.py::test_el_primer_fragmento_inseguro_de_varios_bloquea
   FAILED tests/engine/test_worker_request.py::test_fragmento_sin_clasificar_impide_construir_el_worker_request
   ```
   A4-P3 (y sus consecuencias en `WorkerRequest`) cayó como se esperaba.
   Revertido con `git checkout -- src/sirius_engine/egress.py`.

2. Hacer que el `PermissionEnvelope` conceda por defecto en vez de denegar
   (en `capability_resolver.resolve_capabilities`, se retiró la comprobación
   `if nombre not in envelope.capacidades_concedidas: raise ...`) →
   ```
   $ QT_QPA_PLATFORM=offscreen uv run pytest tests/engine/test_capability_resolver.py -q
   2 failed, 3 passed in 0.05s
   FAILED tests/engine/test_capability_resolver.py::test_capacidad_registrada_pero_no_concedida_impide_la_resolucion
   FAILED tests/engine/test_capability_resolver.py::test_no_concede_una_version_recortada_de_la_capacidad
   ```
   A4-P5 cayó como se esperaba. Revertido con
   `git checkout -- src/sirius_engine/capability_resolver.py`.

3. Introducir una diferencia en la proyección del prompt del implementador
   (en `adapters/github_worker_request.py`, la cabecera del bloque de
   contexto pasó de `"## Contexto de esta ejecución\n"` a
   `"## Contexto de esta ejecución (MUTACION-A4-P2)\n"`) →
   ```
   $ QT_QPA_PLATFORM=offscreen uv run pytest tests/engine/test_worker_request.py -q -k "no_divergencia or reproduce_el_prompt"
   2 failed, 9 deselected in 0.07s
   FAILED tests/engine/test_worker_request.py::test_la_proyeccion_del_perfil_implementer_reproduce_el_prompt_real_del_workflow
   FAILED tests/engine/test_worker_request.py::test_la_no_divergencia_vale_para_otra_incidencia_y_otro_repositorio
   ```
   A4-P2 cayó como se esperaba. Revertido con
   `git checkout -- src/sirius_engine/adapters/github_worker_request.py`.

Tras revertir las tres mutaciones, se repitió la batería completa
(`ruff format --check`, `ruff check`, `mypy src tests`,
`pytest tests/engine -q` → `312 passed`) para confirmar que el árbol quedó
exactamente como antes de sembrar.

## Consecuencias

- La vía GitHub existente (`implement-sirius-work.yml`, los tres prompts de
  rol) queda intacta: A4 no la conecta a los perfiles todavía —eso es C3, con
  sesión interactiva (ADR-002)— pero deja probado que, si se conectara hoy, el
  prompt real no cambiaría ni un carácter para el rol `implementer`.
- Cualquier bloque futuro (B1 investigador, C1-C4) que necesite un
  `WorkerRequest`, un `PermissionEnvelope` o el Resolver ya tiene la pieza
  construida y probada; no hace falta reabrir este diseño.
- El campo `Perfil: <ref>@<version>` queda definido y probado, pero sin
  ningún productor real todavía: ninguna incidencia lo declara hoy. Es
  responsabilidad de C2/C3 empezar a emitirlo.
- El registro de capacidades (`registro_capacidades.yml`) incluye
  `web.buscar` sin que ningún perfil de este bloque la pida: existe porque
  §6 la usa como ejemplo canónico de capacidad de red y porque sin ella no
  se podría probar la incompatibilidad estructural de §6.1 regla 1. B1 la
  usará de verdad.
- Límite conocido: el Resolver v0 no expone ninguna noción de "entrega
  parcial declarada" (arquitectura §6 regla 4, el precedente de
  `leer_github` parcial). No hizo falta para las cinco pruebas de terminado
  de este bloque; queda para cuando exista un Adapter real que la necesite.

## Adenda: rondas de corrección posteriores a la fusión de la nota original

La sección «Comprobación que la sostiene» de arriba documenta únicamente el
estado del bloque en su commit original (`a895f28`). La revisión
independiente de la PR que acompaña a esta rama (incidencia #202) encontró
defectos en rondas posteriores; esta adenda deja constancia de cada una en
el mismo lugar donde vive la evidencia original, en vez de dejarla solo en
comentarios de la incidencia (skill `disciplina-evidencia`: el ADR es el
registro autoritativo).

### Ronda 2 (commit `0ff8c4f`)

- **CODEX-001** — `pyyaml` estaba declarado solo como dependencia de
  desarrollo (`dev`) en `pyproject.toml`, pero `profile_registry.py` y
  `capability_registry.py` lo importan en tiempo de ejecución para cargar
  los perfiles y el registro de capacidades desde YAML: sin él, cualquier
  entorno de producción que instale solo las dependencias del proyecto
  rompe al primer `load_agent_profile`. Movido a `dependencies`.
- **CODEX-002** — `resolve_capabilities` comprobaba que la capacidad
  estuviera en `capacidades_concedidas`, pero no cruzaba las propiedades
  `red`/`escritura` del registro contra el `PermissionEnvelope` efectivo:
  una capacidad marcada `red: true` o `escritura: true` en el registro se
  resolvía igual aunque el envelope no autorizara esa propiedad. Corregido
  añadiendo las dos guardas (`capability_resolver.py`) y dos pruebas
  (`test_capacidad_de_red_no_se_resuelve_sin_envelope_con_red`,
  `test_capacidad_de_escritura_no_se_resuelve_sin_envelope_con_escritura`).
  Efecto colateral no buscado: al ser `veredicto.escribir` una capacidad
  marcada `escritura: true` en el registro de esa ronda, esta guarda dejó de
  resolverla para `reviewer` (perfil de solo lectura, `permisos.escritura:
  null`), así que la capacidad se retiró de `reviewer.yml` para que la
  suite volviera a estar en verde -sin notar que `reviewer.yml` seguía
  prometiendo `veredicto_json` en su `contrato_salida`. Ese es exactamente
  el defecto que corrige la ronda 3 (CLAUDE-REVISOR-001, abajo).
- Comprobación: `uv run ruff format --check .`, `uv run ruff check .`,
  `uv run mypy src tests` y `QT_QPA_PLATFORM=offscreen uv run pytest -q` en
  verde (2706 passed según el comentario `CORRECCION_APLICADA` de la
  incidencia #202; no se repitió aquí por no formar parte del alcance de
  esta adenda).

### Ronda 3 (esta corrección)

- **CLAUDE-REVISOR-001 (P2)** — `veredicto.escribir` estaba modelado en
  `registro_capacidades.yml` con `escritura: true`, la misma propiedad
  genérica que `repo.escribir`/`pr.crear` usan para "escritura en el
  repositorio". Pero escribir el veredicto JSON en la ruta externa que da
  el motor (`SIRIUS_VERDICT_FILE`) no es escritura en el repo -es la misma
  distinción que el propio registro ya hace para `red` con la vía GitHub
  existente ("no cuenta como red externa: es el plano de control de
  confianza"). Corregido marcando `veredicto.escribir` con `escritura:
  false` y restaurando la capacidad en `reviewer.yml`. Añadida
  `test_el_artefacto_veredicto_json_es_resoluble_bajo_el_envelope_propio`
  (parametrizada sobre los cuatro perfiles reales), que falla si algún
  perfil promete `veredicto_json` en su `contrato_salida` sin poder
  resolver `veredicto.escribir` bajo su propio `PermissionEnvelope`.
- **CODEX-001 (P2, ronda 3)** — `_cargar_permisos` aceptaba
  `permisos.escritura: ""` (cadena vacía) como si fuera un ámbito de
  escritura válido, porque solo rechazaba `None`; `compute_permission_envelope`
  lo copiaba literalmente y `resolve_capabilities` lo trataba como "hay
  ámbito" (`envelope.escritura is None` es falso para `""`), concediendo
  `repo.escribir` sin un ámbito real. Corregido rechazando también la
  cadena vacía en `profile_registry._cargar_permisos`. Añadida
  `test_ambito_de_escritura_vacio_es_un_error`.
- **CLAUDE-REVISOR-002 (P3)** — esta misma adenda, que documenta las dos
  rondas anteriores en el ADR en vez de dejarlas solo en comentarios de la
  incidencia.
- Comprobación, las cuatro validaciones obligatorias en verde sobre el
  repositorio completo tras aplicar los tres cambios de esta ronda:

  ```
  $ uv run ruff format --check .
  408 files already formatted

  $ uv run ruff check .
  All checks passed!

  $ uv run mypy src tests
  Success: no issues found in 389 source files

  $ QT_QPA_PLATFORM=offscreen uv run pytest -q
  2710 passed, 6 skipped in 287.55s (0:04:47)
  ```

### Ronda 4 (esta corrección)

- **CODEX-001 (P2)** — la ronda 3 marcó `veredicto.escribir` con
  `escritura: false` para esquivar la guarda general del Resolver (§6 regla
  2), aunque el procedimiento real del revisor (`scripts/automation/prompts/reviewer.md:106-109,145-154`)
  ejecuta una escritura de sistema de archivos real sobre `SIRIUS_VERDICT_FILE`.
  El riesgo: cualquier futura capacidad que escriba fuera del repo podría
  reutilizar la misma clasificación para saltarse el permiso. Corregido
  devolviendo `veredicto.escribir` a `escritura: true` (un efecto de
  escritura real exige un ámbito de escritura efectivo, sin excepción) y
  dándole a `reviewer` un ámbito acotado al canal del motor
  (`permisos.escritura: veredicto`), distinto de `repo` -nunca `repo` ni
  concediéndole `repo.escribir`/`pr.crear`, que siguen gateadas por no estar
  en la lista `capacidades` del perfil, con independencia del ámbito
  declarado. Añadida `test_reviewer_sigue_sin_poder_resolver_repo_escribir`,
  que falla si ese ámbito llegara a colarle una capacidad de escritura sobre
  el repositorio.
- **CODEX-002 (P2)** — `reviewer.yml` y `registro_capacidades.yml` cambiaron
  su contenido normativo en la ronda 3 (la lista de capacidades de
  `reviewer` y la semántica de `veredicto.escribir`) sin incrementar
  `version`, dejando ambiguo qué permisos gobernaron un Run identificado
  como `reviewer@1`. Corregido incrementando `version: 1 -> 2` en ambos
  ficheros (que además cambian de contenido normativo otra vez en esta
  misma ronda, por CODEX-001 de arriba).
- **CODEX-003 (P2)** — `profile_registry._cargar_permisos` rechazaba la
  cadena vacía (`""`) como ámbito de escritura desde la ronda 3, pero no un
  ámbito formado solo por espacios (`"   "`): esa cadena es truthy en
  Python, así que pasaba la validación y `compute_permission_envelope` la
  conservaba como si fuera un ámbito real. Corregido comprobando
  `escritura.strip()` en vez de `escritura` a secas. Añadida
  `test_ambito_de_escritura_solo_espacios_es_un_error`.
- Comprobación, las cuatro validaciones obligatorias en verde sobre el
  repositorio completo tras aplicar los tres cambios de esta ronda:

  ```
  $ uv run ruff format --check .
  408 files already formatted

  $ uv run ruff check .
  All checks passed!

  $ uv run mypy src tests
  Success: no issues found in 389 source files

  $ QT_QPA_PLATFORM=offscreen uv run pytest -q
  2712 passed, 6 skipped in 332.51s (0:05:32)
  ```

### Ronda 5 (esta corrección)

- **CODEX-001 (P2)** — la ronda 4 le dio a `reviewer` un ámbito de escritura
  acotado (`permisos.escritura: veredicto`) y confió en que la única guarda
  contra que ese ámbito colara `repo.escribir`/`pr.crear` fuera que esas dos
  capacidades no estuvieran en la lista `capacidades` del perfil. Pero
  `resolve_capabilities` seguía sin comprobar nada más específico que
  "¿hay algún ámbito no nulo?": una prueba directa
  (`PermissionEnvelope({"repo.escribir"}, escritura="veredicto", red=False)`)
  resolvía `repo.escribir` igual, y lo mismo con `pr.crear` -el resolver no
  vinculaba cada capacidad de escritura con un ámbito compatible, así que
  cualquier perfil futuro que combinara el ámbito `veredicto` con esas
  capacidades en su lista `capacidades` las habría resuelto sin que nada lo
  impidiera. Corregido añadiendo `ambitos_escritura` al registro de
  capacidades (`registro_capacidades.yml`, `capability_registry.py`): cada
  capacidad con `escritura: true` declara ahora la lista cerrada de ámbitos
  de `permisos.escritura` bajo los que se resuelve (`repo.escribir` y
  `pr.crear` solo aceptan `repo`; `veredicto.escribir` acepta `repo` y
  `veredicto`, porque tanto los perfiles de escritura amplia como el perfil
  de solo lectura con ámbito acotado necesitan escribir el veredicto). El
  Resolver (`capability_resolver.py`) cambia la guarda de "¿ámbito no nulo?"
  a "¿el ámbito del envelope está entre los ámbitos compatibles de la
  capacidad?". Añadidas
  `test_un_ambito_de_escritura_acotado_no_cuela_una_capacidad_de_otro_ambito`
  (la prueba directa citada por la revisión, parametrizada sobre
  `repo.escribir` y `pr.crear`) y
  `test_veredicto_escribir_resuelve_bajo_cualquiera_de_sus_dos_ambitos_compatibles`
  en `tests/engine/test_capability_resolver.py`, y dos casos nuevos de
  registro malformado (`escritura: true` sin ámbitos, `escritura: false` con
  ámbitos) en `tests/engine/test_capability_registry.py`. Incrementado
  `version: 2 -> 3` en `registro_capacidades.yml` (cambio normativo, mismo
  criterio que CODEX-002 de la ronda 4).
- Comprobación, las cuatro validaciones obligatorias en verde sobre el
  repositorio completo tras aplicar el cambio de esta ronda:

  ```
  $ uv run ruff format --check .
  406 files already formatted (tras `ruff format .`, que reformateó los 2
  ficheros de esta ronda)

  $ uv run ruff check .
  All checks passed!

  $ uv run mypy src tests
  Success: no issues found in 389 source files

  $ QT_QPA_PLATFORM=offscreen uv run pytest -q
  2719 passed, 6 skipped in 351.65s (0:05:51)
  ```

## Alternativas descartadas y por qué

Ver «Opciones consideradas» arriba: las cuatro alternativas evaluadas se
descartaron por la misma razón de fondo —introducían una segunda fuente de
verdad (perfil vs. prompt real, prueba vs. workflow real) o le devolvían al
perfil una decisión que la incidencia asigna explícitamente al motor
(el cálculo del `PermissionEnvelope`).
