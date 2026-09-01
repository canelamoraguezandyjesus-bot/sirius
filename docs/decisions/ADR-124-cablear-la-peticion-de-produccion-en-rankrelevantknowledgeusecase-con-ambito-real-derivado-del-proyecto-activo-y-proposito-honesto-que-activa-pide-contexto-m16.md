# ADR-124 — Cablear la petición de producción en RankRelevantKnowledgeUseCase con ámbito real derivado del proyecto activo y propósito honesto que activa pide_contexto (M16)

- Estado: APROBADO
- Fecha: 2026-09-01
- Aprobación: fusión de la PR por el propietario

**Esta sección es también la nota de arranque de la rama** (skill
`disciplina-evidencia`, ADR-001): se publica y se commitea antes de tocar
ningún archivo de código de este encargo.

## Contexto y problema

Incidencia #504 (Work ID WI-20260901-003259), M16 de la ola de paridad en
producción (ADR-119, incidencia #478), especificación exacta en
`docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md` §11.3 y
§11.5-M16.

Hoy `_peticion_ordinaria`
(`src/sirius/application/rank_relevant_knowledge.py:86-107`) fija siempre
`Ambito(global_=True, proyectos=())`, sin importar el proyecto activo, aunque
`_rank_via_staged_engine` ya lee `self._project_repository.get_active_project()`
dos líneas antes de construir la petición (`rank_relevant_knowledge.py:238-241`)
para calcular `project_matches_active`. Ese mismo dato nunca llega a
`Peticion.ambito`, así que `G4` (`src/sirius/domain/staged_engine_gates.py:135-152`,
`peticion.ambito.autoriza(item.project_id)`) admite hoy cualquier candidato de
cualquier proyecto: el motor por etapas no restringe por ámbito en producción,
pese a que M14 (ya fusionado) sí restringe por ámbito la ampliación por
categoría (`candidate_in_declared_scope`, sección `solo_por_categoria`).

El propósito (`_PROPOSITO_RECUPERACION_ORDINARIA = "recuperacion de contexto
relevante (B6b)"`) ya contiene la subcadena `"contexto"`
(`PROPOSITO_DE_CONTEXTO`, `tests/acceptance/staged_engine_category_and_relevance.py:257`),
así que `pide_contexto(proposito)` ya evalúa `True` para toda petición real sin
tocar el literal — pero eso no está confirmado por ninguna prueba de
producción hoy, solo por lectura del código. §11.3 exige que este hecho quede
fijado por una prueba explícita, no solo ser cierto por casualidad de
redacción.

M13, M14 y M15 (índice de categoría multi-activación, restricción de ámbito de
esa ampliación, RF-25/RF-26 y G8/G12 sobre el conjunto combinado) ya están
fusionados en `main` y viven en `RankRelevantKnowledgeUseCase._rank_via_staged_engine`
y en `ContextBuilder._apply_relevance_filter`
(`src/sirius/application/context.py:274-339`); no se reescribe ninguno de los
dos. Lo único que falta cablear es la parte de la petición misma: ámbito real
y una prueba que confirme el propósito honesto.

### 1. ¿Dónde vive el fallo y dónde voy a poner el arreglo?

El fallo (la brecha, no un bug: es exactamente lo que §11.1 punto 6 y §11.3
diagnostican como pendiente) vive en `_peticion_ordinaria`
(`src/sirius/application/rank_relevant_knowledge.py:86-107`): construye
`Ambito` sin recibir el proyecto activo. El arreglo vive en el mismo sitio —
`_peticion_ordinaria` gana un parámetro `active_project_id` que
`_rank_via_staged_engine` ya tiene calculado dos líneas antes de llamarla
(línea 239, `active_project_id = active_project.id if active_project is not
None else None`) y se lo pasa. El sitio del arreglo SÍ puede observar el
fallo: es la misma función que hoy construye la `Peticion` incompleta, con el
dato que le falta ya disponible en su único caller real.

### 2. ¿Qué NO va a garantizar esto?

- No garantiza alcanzar el suelo D1 (29/47, ≤1 crítica, 63/81, P95 ≤300 ms):
  eso es M17, explícitamente diferido por el propio objetivo de la
  incidencia.
- No cambia `Modo`, `Cardinalidad` ni `limite_objetivo`/`limite_duro`: siguen
  fijos en `M1_ORDINARIO`/`EXHAUSTIVA`/`_LIMITE_SIN_ATAR`, tal como §11.3
  ordena explícitamente no tocar.
- No porta `siembra_de_contexto`: sigue fuera de alcance por la precondición
  documentada (M15, §11.2), sin resolver.
- No cambia nada con la puerta `category_matching_enabled` cerrada: el ámbito
  real solo se calcula dentro de `_rank_via_staged_engine`, que solo se
  ejecuta con la puerta abierta; `_rank_via_current_pipeline` no se toca.
- No resuelve la brecha que §11.3 ya nombra como no cerrable esta ola
  (cardinalidad/límite por caso, que exigen un oráculo de resultado esperado
  que ninguna consulta real tiene).

### 3. Criterio de parada (escrito ANTES de decidir, antes de ver ningún resultado)

Escrito antes de ejecutar cualquier prueba o benchmark:

- Si al derivar el ámbito real se observa que alguna prueba de identidad
  existente para el **estado cerrado** (`category_matching_enabled=False`)
  deja de producir el mismo resultado byte a byte, PARO: esa ruta no debe
  tocarse por este encargo y una regresión ahí es una señal de que el cambio
  se filtró fuera del bloque `_rank_via_staged_engine`.
- Si el banco de 47 casos, tras M13-M16 integradas, produce
  `aciertos_exactos`, `elementos_de_mas`, `omisiones_criticas` o `cobertura`
  peor de lo que ADR-113 midió sin ámbito real (27/47, 102 elementos de más,
  4 omisiones críticas, 59/81) de forma que sugiera un error de cableado (no
  una cifra simplemente peor por la brecha ya reconocida en §11.3), reviso el
  cableado antes de publicar la cifra; si la cifra es simplemente peor sin
  indicio de error, la publico igual, sin maquillarla — el objetivo lo pide
  explícitamente («si sale peor de lo esperado, ese es el dato»).
- Si cerrar esta brecha exige tocar el corpus, `resultado_esperado`, alguna
  adjudicación del banco de 47 casos, o decidir una política de límite duro
  por consulta real, PARO y emito `BLOCKED_BY_DECISION`: ninguna de esas
  cosas está autorizada por el alcance de esta incidencia.
- Dos rondas de revisión seguidas con hallazgos de la misma familia →
  paro de parchear, busco la raíz y la registro aquí antes de seguir.

### 4. ¿Qué haría el fallo IMPOSIBLE en vez de improbable?

Dos pruebas nuevas en `tests/integration/test_rank_relevant_knowledge.py`
verifican, contra el objeto `Peticion` real construido dentro de
`_rank_via_staged_engine` (no contra una descripción del comportamiento
esperado):

- con un proyecto activo configurado, `Peticion.ambito ==
  Ambito(global_=False, proyectos=(active_project_id,))`;
- sin proyecto activo, `Peticion.ambito == Ambito(global_=True,
  proyectos=())`;
- `pide_contexto(Peticion.proposito)` es `True` para toda petición real,
  importando `pide_contexto`/`PROPOSITO_DE_CONTEXTO` del propio arnés
  (`tests/acceptance/staged_engine_category_and_relevance.py`) en vez de
  reimplementar la regla en el test.

Como `Peticion` es un dataclass interno de `_rank_via_staged_engine`, la
prueba no puede capturarlo por un mock sin tocar producción: en su lugar se
observa el efecto público que el ámbito real produce en `G4` — un candidato
del motor (no de la ampliación por categoría, que M14 ya restringe por su
cuenta) que pertenece a otro proyecto deja de aparecer en el resultado cuando
hay un proyecto activo, y sigue apareciendo sin proyecto activo. Esa
observación por comportamiento hace el fallo imposible de pasar
desapercibido: si `_peticion_ordinaria` volviera a fijar `global_=True`
siempre, esas pruebas fallarían.

## Opciones consideradas

1. **Pasar `active_project_id` como parámetro nuevo de `_peticion_ordinaria`**
   (elegida): el dato ya existe en el único caller real, cero repositorios
   nuevos, cero E/S adicional.
2. Que `_peticion_ordinaria` reciba el `project_repository` y llame ella misma
   a `get_active_project()`: descartada — duplicaría la misma consulta que
   `_rank_via_staged_engine` ya hace, sin ganar nada, y esparciría la
   responsabilidad de resolver el proyecto activo en dos sitios.
3. Cambiar el propósito literal a otra redacción: descartada — el literal
   actual ya satisface `pide_contexto` (contiene `"contexto"`); cambiarlo sin
   necesidad sería tocar más de lo que el objetivo pide.

## Decisión

Añadir un parámetro `active_project_id: int | None` a `_peticion_ordinaria`,
pasado desde `_rank_via_staged_engine` con el mismo valor que ya calcula para
`project_matches_active`, y derivar `Ambito` con la misma regla que
`candidate_in_declared_scope`/`project_matches_active` ya usan: proyecto activo
presente → `Ambito(global_=False, proyectos=(active_project_id,))`; ausente →
`Ambito(global_=True, proyectos=())`. Mantener el propósito literal existente
(ya satisface `pide_contexto`) y añadir las pruebas que lo confirman
explícitamente.

### Hallazgos durante la implementación, con la raíz encontrada antes de publicar la cifra

Aplicando el criterio de parada de arriba: al re-ejecutar el banco de 47 casos
tras cablear el ámbito real, la primera cifra medida fue **cobertura 0/81
(0.0%)** — una caída, no una brecha reconocida, así que se paró a buscar la
raíz en vez de publicarla:

1. `_ejecutar_banco_paquete_completo` (`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`)
   construye un único `RankRelevantKnowledgeUseCase`/`ContextBuilder` y
   ejecuta los 47 casos en secuencia contra ellos, pero solo deja **un**
   proyecto `ACTIVE` para las 47 consultas (el que `_create_projects` deja
   activo al terminar) — correcto mientras el ámbito era inerte
   (`_create_projects` lo documentaba así explícitamente: "cuál quede activo
   no importa para las cuatro métricas"), pero cada caso del banco declara su
   propio `ambito` (`PRJ-ALFA`/`PRJ-BETA`/`PRJ-GAMMA`/`PRJ-MADEIRA`/`GLOBAL`,
   `tests/acceptance/fixtures/evidence_bank_47_casos.json`), ya usado por el
   arnés de examen vía `peticion_desde_caso`. Con el ámbito real de M16, cada
   caso necesitaba su propio proyecto activo, no uno fijo — se añadió
   `_set_active_project` (SQL directo sobre `projects.status`/`is_active`,
   nunca a través del caso de uso real e irreversible por diseño de
   `ProjectRepository`) para simularlo caso a caso, sin tocar el banco, el
   corpus ni ninguna adjudicación. Tras el arreglo: **7/47, 285 elementos de
   más, 9 omisiones críticas, cobertura 62/81 (76.5%)** — coherente con el
   arnés de examen (63/81) en vez de contradictorio con él.
2. `ContextBuilder` en ambos arneses de medición (`_ejecutar_banco_paquete_completo`
   y `_build_context_builder_with_relevance_filter` de
   `tests/integration/test_local_performance.py`) se construía **sin**
   `category_matching_enabled=True`, pese a que `composition_root` pasa la
   misma bandera a `RankRelevantKnowledgeUseCase` y a `ContextBuilder`
   (`src/sirius/composition_root.py:462,483`) — un vestigio de cuando M15
   (RF-25/RF-26+G8/G12) todavía no estaba fusionado. Corregido en ambos
   sitios para medir de verdad "M13-M16 integradas", no una aproximación con
   el candado de M10.

Ninguno de los dos es un defecto en `_peticion_ordinaria`: el código de
producción (`src/sirius/application/rank_relevant_knowledge.py`) se comprobó
línea a línea contra `G4`/`candidate_in_declared_scope` antes de aceptar que
el problema estaba en el arnés de medición, no en el cableado — la sección
"Qué haría el fallo IMPOSIBLE" de arriba (las cuatro pruebas de
`tests/unit/test_peticion_ordinaria.py` y
`tests/integration/test_rank_relevant_knowledge.py::test_staged_engine_rejects_a_motor_admitted_candidate_outside_the_active_project`)
siguió en verde durante todo el diagnóstico.

## Correcciones tras revisión

Dos rondas de revisión independiente sobre la PR #505 encontraron
divergencias reales entre `G4` y `candidate_in_declared_scope` (M14) que la
decisión de arriba no había previsto. Se corrigieron en el propio código, sin
reabrir el diseño ya aprobado:

- **Ronda 2 (commit `c2105666`, corrige CLAUDE-REV-M16-001 y CODEX-001):**
  `Ambito.autoriza` (`src/sirius/domain/staged_engine_contracts.py`)
  rechazaba `project_id=None` en cuanto la petición declaraba un proyecto
  activo, divergiendo de `candidate_in_declared_scope` y descartando por G4
  memorias de ámbito global que el motor por etapas sí encontraba. Se cambió
  para tratar `project_id=None` como siempre autorizado — la misma regla que
  `candidate_in_declared_scope` ya aplicaba a la ampliación por categoría de
  M14.
- **Ronda 3 (commit `344a74a`, corrige CODEX-001):** esa misma excepción de
  `project_id=None`, pensada para el candidato sin eje de ámbito declarado,
  se aplicaba también en `_g4` (`src/sirius/domain/staged_engine_gates.py`)
  cuando el eje venía declarado explícitamente (p. ej. `"PROYECTO"`) sin
  `project_id` resuelto, colando un candidato que se declara de proyecto sin
  poder verificar su pertenencia. Se limitó la excepción al caso sin eje
  declarado; con el eje declarado y sin `project_id`, la petición cerrada
  cierra el ámbito y solo una petición global lo sigue admitiendo.

## Comprobación que la sostiene

- Prueba por mutación (ADR-001 punto 3): con `_peticion_ordinaria` forzada
  temporalmente a `Ambito(global_=True, proyectos=())` siempre (revirtiendo
  solo esa expresión), `test_ambito_is_scoped_to_the_active_project_when_one_is_configured`
  y `test_staged_engine_rejects_a_motor_admitted_candidate_outside_the_active_project`
  fallan como se espera; restaurado el código, las 36 pruebas de
  `tests/integration/test_rank_relevant_knowledge.py`+`tests/unit/test_peticion_ordinaria.py`
  pasan.
- `uv run ruff format --check .`: 579 archivos ya formateados.
- `uv run ruff check .`: todas las comprobaciones superadas.
- `uv run mypy src tests`: sin incidencias en 549 archivos fuente.
- `uv run pytest`: 4518 aprobadas, 15 omitidas (Ollama real/QtMultimedia,
  igual que antes de este encargo), 2 falladas-como-se-espera
  (`xfail(strict=True)` de M11, sin XPASS — el suelo D1/RNF-003 sigue sin
  alcanzarse, evaluarlo es M17, no este encargo).
- `git diff --check`: sin espacios en blanco conflictivos.

## Consecuencias

**Banco de 47 casos (PA-0.2-REC-01), pipeline real con M13-M16 integradas
(`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py::test_el_banco_se_ejecuta_contra_el_paquete_completo_de_produccion_como_evidencia_adicional`,
`-s` para ver la impresión):**

| Métrica | Antes de M16 (M13/M14 wired, ámbito global) | Con M16 |
|---|---|---|
| aciertos_exactos | 4/47 | **7/47** |
| elementos_de_mas | (no comparable: medido con el defecto de arnés arriba) | **285** |
| omisiones_criticas | (ídem) | **9** |
| cobertura | (ídem) | **62/81 (76.5%)** |

Frente al arnés de examen (semántica de laboratorio completa, con siembra):
29/47, 50 de más, 0 críticas, 63/81 (77.8%). Ninguna de las cuatro alcanza el
suelo D1 (§11.5-M17 lo evalúa, no este encargo) — el resultado no estaba
predeterminado (§11.2/§11.5 lo advierten explícitamente) y se publica tal
cual salió: `elementos_de_mas` alto es consistente con la brecha ya nombrada
en §11.3 y no cerrada por este encargo (cardinalidad `EXHAUSTIVA`/límite sin
atar por consulta real, sin el oráculo de resultado esperado que solo el
banco tiene).

**RNF-003, benchmark de ADR-008/§6.4/§11.4, pipeline real con M13-M16
integradas (`tests/integration/test_local_performance.py::test_construir_contexto_con_el_paquete_completo_activo_en_los_tres_escenarios`):**

| Escenario | P95 | Límite |
|---|---|---|
| Ollama disponible dentro del presupuesto | 489.0 ms | 300 ms |
| Ollama ausente (conexión rechazada) | 468.5 ms | 300 ms |
| Ollama acepta la conexión y agota el timeout | 524.0 ms | 300 ms |

Las tres siguen por encima de 300 ms (RNF-003 no se cumple, sin sorpresa: es
el mismo diagnóstico de §11.4 que M13 en solitario no promete cerrar) pero
bajan frente al rango 438-780 ms que ADR-117 midió antes de M13-M16 —
consistente con que el ámbito real reduce el volumen de candidatos que el
motor y la ampliación por categoría procesan cuando hay un proyecto activo.
Las dos pruebas `xfail(strict=True)` (aciertos_exactos ≥29/47 y P95 ≤300 ms)
siguen fallando-como-se-espera, sin XPASS — M17 evalúa el suelo D1/RNF-003
final, no este encargo.

**Wiring:** M14 (índice de categoría multi-activación con restricción de
ámbito) y M15 (RF-25/RF-26, G8/G12) ya vivían en
`RankRelevantKnowledgeUseCase._rank_via_staged_engine`/
`ContextBuilder._apply_relevance_filter` antes de esta incidencia; M16 añade
el ámbito real y confirma el propósito honesto de `_peticion_ordinaria`, y
corrige dos arneses de medición que construían `ContextBuilder` sin la misma
bandera `category_matching_enabled` que `RankRelevantKnowledgeUseCase` ya
tenía, para que "M13-M16 integradas" mida lo que de verdad se cablea, no una
aproximación.

## Alternativas descartadas y por qué

Ver «Opciones consideradas» arriba.
