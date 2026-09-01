# ADR-124 — Cablear la petición de producción en RankRelevantKnowledgeUseCase con ámbito real derivado del proyecto activo y propósito honesto que activa pide_contexto (M16)

- Estado: PROPUESTO
- Fecha: 2026-09-01
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]

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

## Comprobación que la sostiene

(Se completa tras implementar y ejecutar las validaciones obligatorias — ver
el cierre de este ADR más abajo, actualizado antes del commit final.)

## Consecuencias

(Se completa con las cuatro métricas del banco de 47 casos y el P95 del
benchmark de ADR-008/§6.4/§11.4, medidos sobre esta integración — ver cierre.)

## Alternativas descartadas y por qué

Ver «Opciones consideradas» arriba.
