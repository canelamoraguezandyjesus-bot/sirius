# ADR-120 — M15: RF-25/RF-26 sustituye el candado de M10 y G8/G12 se aplican sobre el conjunto combinado, ambos tras la puerta

- Estado: PROPUESTO
- Fecha: 2026-08-31
- Aprobación: fusión de la PR por el propietario

## Contexto y problema

`docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md:1970-2006`
(§11.5-M15) pide, tras la puerta `category_matching_enabled`: (1) que RF-25/
RF-26 (la regla de las críticas ORIGINAL del laboratorio) sustituya el
candado-unión de `ContextBuilder._apply_relevance_filter`
(`src/sirius/application/context.py:239-258` antes de este cambio) como
mecanismo de integridad de críticas; (2) que G8 (vigencia temporal) y G12
(criticidad y límite duro) — ya portadas en
`src/sirius/domain/staged_engine_gates.py` para el motor por etapas — se
apliquen sobre el conjunto combinado motor+categoría antes de que RF-25/RF-26
actúe. El arnés del banco de 47 casos (ADR-112/113/115,
`tests/acceptance/staged_engine_category_and_relevance.py`) ya reproduce las
tres piezas contra el banco; este encargo (incidencia #490) las porta a
`ContextBuilder`, no al arnés.

El problema concreto: `Memory`/`Decision` (`src/sirius/domain/memory.py`,
`src/sirius/domain/decision.py`) no declaran ningún eje `valid_from`/
`valid_to` — ni ningún concepto de "límite duro por consulta" llega hoy a
`ContextBuilder` (§11.3 ya fija, para toda esta ola, "el límite se mantiene
sin atar... ningún encargo de esta ola introduce un límite duro por consulta
real"). G8/G12, tal como la arquitectura las describe, son puertas
genéricas que necesitan esos dos datos. ¿Cómo se portan de forma fiel sin
inventar un eje de esquema o una política de límite que esta incidencia no
tiene autoridad para diseñar?

## Criterio de parada (escrito ANTES de decidir)

Si para escribir una prueba de G8 o G12 que se ejecute a través de
`ContextBuilder.build()` contra datos reales hiciera falta añadir un campo
nuevo a `Memory`/`Decision`, o inventar un límite duro de producto no citado
en ningún ADR/arquitectura existente, paro y emito `BLOCKED_BY_DECISION`: eso
sería una decisión de esquema/producto fuera del alcance de "el cambio en el
código que pide el objetivo, con sus pruebas, y nada más". Si en cambio las
funciones puras que reproducen G8/G12 se pueden portar, cablear y probar
directamente (con datos sintéticos, no necesariamente a través de
`ContextBuilder`) sin tocar ningún esquema ni inventar una política de
límite nueva, seguir adelante es el camino correcto.

## Opciones consideradas

1. **No implementar G8/G12 en absoluto**, alegando que están inertes hoy.
   Descartada: el objetivo de la incidencia los pide explícitamente, y
   "ya portadas en `staged_engine_gates.py`" indica que la arquitectura los
   considera parte necesaria del diseño de esta ola, no opcionales.
2. **Reutilizar `Candidata`/`Peticion`/`aplicar_g12` de `staged_engine_gates.py`
   directamente**, construyendo un `Candidata` sintético por cada
   `RankedKnowledge`. Descartada: exige rellenar campos ajenos a
   `Memory`/`Decision` (`LecturaSemantica`, `senal`, `razon` para G10/G11,
   que G8/G12 no necesitan pero el tipo `Candidata` sí exige) — más
   acoplamiento que reutilización real, y una abstracción que no encaja.
3. **Portar dos funciones puras nuevas** (`candidate_currently_valid`,
   `truncate_to_hard_limit`) en `sirius.domain.relevance`, con la misma
   firma semántica que `_g8`/`aplicar_g12` y sus réplicas del arnés
   (`vigente_en_tiempo_objetivo`/`truncar_por_limite_duro`), citando su
   origen — mismo patrón que M14 ya usó para
   `category_index_matches_query`/`candidate_in_declared_scope`. Elegida.

## Decisión

Se implementa la opción 3. `candidate_currently_valid(valid_from, valid_to,
*, target_time)` y `truncate_to_hard_limit(candidates, *, hard_limit,
max_criticality_category)` viven en `sirius/domain/relevance.py`, con la
misma semántica que sus réplicas del arnés, probadas directamente con datos
sintéticos (`tests/unit/test_relevance_domain.py`).

`ContextBuilder._apply_relevance_filter` las cablea así, cuando
`category_matching_enabled` es `True`:

- G8: se llama con `valid_from=None, valid_to=None` para todo candidato
  real — la misma degradación SIN_EJES que `staged_engine_gates.py` ya
  documenta para cualquier puerta que necesite un eje que Sirius no
  persiste ("falla abierta, no descarta"). La puerta se ejecuta de verdad
  (no se omite la llamada), pero hoy siempre es `True`.
- G12: se llama con un límite fijo, `_HARD_LIMIT_SIN_ATAR = 100_000` —
  mismo valor y misma justificación que
  `rank_relevant_knowledge._LIMITE_SIN_ATAR` (§11.3: "el límite se
  mantiene sin atar" para toda esta ola). Con cualquier volumen real de
  memorias/decisiones vigentes muy por debajo de esa cifra, la puerta
  nunca trunca nada hoy.

Ambas puertas quedan operativas y correctamente cableadas — no se omite su
ejecución — pero son inertes sobre datos reales hasta que (a) una
migración de esquema añada `valid_from`/`valid_to` a `Memory`/`Decision`, o
(b) una decisión de producto registre un límite duro real por consulta.
Ninguna de las dos decisiones es de esta incidencia.

RF-25/RF-26 (`rescue_max_criticality_candidates`) sustituye la mitad de
máxima-criticidad del candado-unión, solo cuando `category_matching_enabled`
es `True`: `ContextBuilder` gana ese parámetro nuevo (por defecto `False`),
de modo que todo llamador existente —incluidos los tests de M10 que
construyen `ContextBuilder` con un puerto y `max_criticality_category`
directamente, sin pasar el parámetro nuevo— sigue ejercitando el candado
byte a byte. La protección incondicional de "sin categoría todavía" no
cambia en ninguno de los dos caminos.

## Comprobación que la sostiene

- `uv run pytest tests/unit/test_relevance_domain.py
  tests/integration/test_context_builder.py
  tests/unit/test_composition_root_relevance_gate.py -q` → 93 passed.
- Las pruebas nuevas de `tests/unit/test_relevance_domain.py`
  (`test_candidate_currently_valid_*`, `test_truncate_to_hard_limit_*`,
  `test_rf25_*`/`test_rf26_*`/`test_rescue_*`) fallan con
  `ImportError: cannot import name 'candidate_currently_valid'` contra el
  código anterior a este cambio (confirmado con `git stash` sobre
  `src/sirius/application/context.py`, `src/sirius/composition_root.py`,
  `src/sirius/domain/relevance.py`, ejecutando la misma suite, y
  restaurado con `git stash pop`) — la evidencia ADR-001 de que la prueba
  se vio fallar antes del cambio.
- `test_rf26_does_not_rescue_when_the_filter_declared_total_absence` y
  `test_category_matching_enabled_false_keeps_the_old_candado_byte_for_byte`
  (`tests/integration/test_context_builder.py`) ejercitan el mismo
  escenario exacto (un único candidato de categoría "salud", filtro que
  descarta todo) bajo los dos valores de `category_matching_enabled`, y
  confirman el resultado opuesto: el candado (`False`) siempre protege el
  candidato; RF-26 (`True`) no lo rescata cuando el filtro no conservó
  nada.

## Consecuencias

- G8/G12 quedan correctamente diseñadas, cableadas y con pruebas unitarias
  directas de su semántica, pero no cambian ningún comportamiento
  observable de `ContextBuilder` hoy — quien lea solo la suite de
  integración de `ContextBuilder` no verá a G8/G12 descartar ni truncar
  nada, porque no hay datos reales que las activen todavía.
- Si un encargo futuro añade `valid_from`/`valid_to` a `Memory`/`Decision`,
  o un límite duro real por consulta, el único cambio que necesita en
  `ContextBuilder` es dejar de pasar `None, None` / `_HARD_LIMIT_SIN_ATAR`
  — las funciones puras y sus pruebas no cambian.
- `ContextBuilder.__init__` gana un parámetro más
  (`category_matching_enabled: bool = False`); `composition_root.py` lo
  cablea desde el mismo booleano que ya gobierna
  `RankRelevantKnowledgeUseCase`.

## Alternativas descartadas y por qué

Ver «Opciones consideradas» arriba (1 y 2).
