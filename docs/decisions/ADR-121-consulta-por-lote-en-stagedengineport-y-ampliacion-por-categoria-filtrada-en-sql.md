# ADR-121 — Consulta por lote en StagedEnginePort y ampliación por categoría filtrada en SQL (M13, incidencia #489, integrado sobre M14)

- Estado: APROBADO
- Fecha: 2026-08-31
- Aprobación: fusión de la PR por el propietario

## Contexto y problema

§11.4 (puntos 1 y 2) de `docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md`
diagnostica, por lectura directa del código, dos de las tres causas
plausibles de que «construir contexto» con el paquete completo activo mida
438-780 ms en vez de los ~120 ms que ADR-008 mide con la puerta cerrada:

1. `StagedEnginePort.por_clave_exacta`/`por_prefijo_de_sujeto`
   (`src/sirius/adapters/persistence/staged_engine_port.py`) ejecutaban
   **dos consultas SQL por cada clave o prefijo**, dentro de un bucle
   Python, en vez de una sola consulta por lote — a diferencia del patrón
   que `_por_ids_mixtos` ya usa para ids, y que ADR-008 ya adoptó para el
   listado de revisiones vigentes.
2. El bloque `solo_por_categoria` de `_rank_via_staged_engine`
   (`src/sirius/application/rank_relevant_knowledge.py`) recorría, con la
   puerta `category_matching_enabled` abierta, la totalidad de
   `list_current_memories()`/`list_current_decisions()` en cada llamada a
   `rank()` — un segundo barrido completo del corpus, filtrado en Python en
   vez de en SQL.

M13 (§11.5) encarga sustituir ambos por consulta en lote / filtrada en SQL,
sin alterar qué se admite ni en qué orden — invariante innegociable de la
incidencia, verificado por las pruebas de identidad existentes
(`tests/integration/test_rank_relevant_knowledge.py`,
`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`, el arnés de
examen).

**Diferencia frente al primer intento (incidencia #485, PR #487, rama
`feature/m13-batch-queries-staged-engine-y-categoria`, cerrada por
conflicto):** aquel intento partía de antes de que M14 (incidencia #486,
PR #488) sustituyera `solo_por_categoria` por el índice de categoría
buscable de activación múltiple con restricción de ámbito. Sobre ese `main`
más antiguo, `category_matches_query` exigía activación única (como mucho
un término del vocabulario a la vez), así que bastaba con extraer esa regla
(`activated_category_term`) y consultar el repositorio filtrado por ese
único término. M14, ya fusionado, cambia la regla que la ampliación aplica:
`category_index_matches_query` activa la categoría para **todo** candidato
con categoría no nula en cuanto la consulta contiene **cualquier** término
del vocabulario — sin comparar la categoría del candidato contra un término
concreto (réplica de `activa_categoria_buscable`, ADR-113: el índice de
categoría buscable guarda las cinco/siete palabras del vocabulario juntas
como el mismo contenido para toda identidad no ordinaria). Esta incidencia
(#489) reintegra el material reutilizable del primer intento —
`por_clave_exacta`/`por_prefijo_de_sujeto` en lote (sin cambios, es
independiente de M14) y `list_current_memories_by_category`/
`list_current_decisions_by_category` en los puertos y adaptadores SQLite
(sin cambios de firma) — pero sustituye la integración en
`_rank_via_staged_engine` para que la consulta SQL exprese la regla de M14,
no la de M9 que el primer intento asumía.

## Nota de arranque (las cuatro preguntas, ADR-001 / disciplina-evidencia)

**1. ¿Dónde vive el fallo y dónde voy a poner el arreglo? ¿Puede el sitio del
arreglo observar el fallo que arregla?**

El fallo vive en dos sitios y el arreglo va en esos mismos sitios:

- `por_clave_exacta`/`por_prefijo_de_sujeto`: el bucle `for clave in
  utiles`/`for prefijo in utiles` que dispara dos `session.execute` por
  iteración. El arreglo sustituye ese bucle por una única sentencia
  `UNION ALL` de una subconsulta por clave/prefijo (cada una con su propio
  `ORDER BY id LIMIT`, para conservar la cota independiente por clave/prefijo
  que ya exigió la ronda 2 de la incidencia #485/CLAUDE-M13-001/CODEX-001).
  Sí puede observar el fallo: un contador de sentencias SQL ejecutadas
  (`event.listen(Engine, "before_cursor_execute", ...)`, el mismo
  instrumento que `tests/integration/test_memory_decision_list_query_count.py`
  ya usa para ADR-008) cuenta exactamente cuántas consultas emite cada
  método para *n* claves/prefijos; el arreglo se mide con el mismo contador
  que primero demuestra el fallo.
- `solo_por_categoria`: la llamada a `list_current_memories()`/
  `list_current_decisions()` sin filtro, ya reescrita por M14 para usar
  `category_index_matches_query`/`candidate_in_declared_scope` en vez de
  `category_matches_query`. El arreglo antepone una decisión barata en
  Python — `category_index_activated(query_text, vocabulary)`, la misma
  condición de activación que `category_index_matches_query` exige junto
  con `category is not None`, factorizada para no tocar el repositorio si
  la consulta no activa nada — y, cuando activa, sustituye la enumeración
  completa por `list_current_memories_by_category`/
  `list_current_decisions_by_category` filtrados en SQL por
  `self._category_vocabulary` (el vocabulario cerrado completo, D7 punto 1:
  toda categoría real, tanto la del clasificador automático como la que un
  usuario fija a mano, es siempre `None` o un miembro de ese vocabulario —
  así que `WHERE category IN (vocabulario)` es exactamente la misma
  condición que `category is not None`, resuelta en SQL en vez de en
  Python). Sí puede observar el fallo: una prueba con un repositorio real
  sobre un corpus con muchos elementos sin categoría y pocos ya
  categorizados cuenta las filas que el repositorio devuelve.

**2. ¿Qué NO va a garantizar esto?**

No garantiza que RNF-003 P95 baje a ≤300 ms — eso lo mide M17 aparte, sobre
el paquete M13-M16 integrado, y §11.4 ya deja escrito que esta arquitectura
no lo promete de antemano. No cambia qué candidatos se admiten ni su orden
(invariante del encargo): la restricción de ámbito
(`candidate_in_declared_scope`) se sigue aplicando en Python, sobre el
subconjunto ya filtrado por SQL, exactamente igual que antes de esta
incidencia. No reduce el número de consultas al mínimo teórico (una sola
consulta universal para todas las etapas): solo elimina el crecimiento
lineal con *n* claves/prefijos y el barrido completo del corpus.

**3. Criterio de parada, decidido antes de medir:**

Si tras sustituir el bucle de `por_clave_exacta`/`por_prefijo_de_sujeto` por
una consulta en lote el número de sentencias SQL sigue creciendo con *n*
(medido con el contador de ADR-008), la causa no era el bucle de Python y
hay que decirlo en el ADR en vez de seguir tocando el mismo código. Si tras
filtrar `solo_por_categoria` en SQL el número de filas que el repositorio
devuelve sigue dependiendo del tamaño total del corpus en vez del tamaño del
subconjunto ya categorizado, parar y diagnosticar en vez de parchear más. Si
alguna prueba de identidad existente
(`tests/integration/test_rank_relevant_knowledge.py`,
`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`, el arnés de
examen) cambia de resultado, la integración con M14 está mal resuelta y hay
que pararse a diagnosticar la divergencia semántica, no forzar el verde.

**4. ¿Qué hace el fallo imposible en vez de improbable?**

Tres pruebas de integración nuevas o reutilizadas, verificadas por mutación
(restaurando el bucle/el barrido completo, comprobando que la prueba nueva
falla con la versión vieja y pasa con la corregida):

- `tests/integration/test_staged_engine_port_batch_queries.py` (reutilizada
  tal cual del primer intento, independiente de M14): cuenta las sentencias
  SQL que `por_clave_exacta`/`por_prefijo_de_sujeto` ejecutan para un
  conjunto pequeño de claves/prefijos frente a uno mucho mayor, y afirma que
  el conteo **no crece**; dos pruebas adicionales confirman que cada
  clave/prefijo conserva su propia cota de filas dentro del `UNION ALL`.
- `tests/integration/test_rank_relevant_knowledge_category_query_rows.py`
  (reescrita para la semántica de M14): con la puerta abierta y un corpus
  donde la mayoría de elementos no tiene categoría todavía y una minoría sí,
  cuenta las filas que el repositorio devuelve para `solo_por_categoria` y
  afirma que ese número depende del tamaño del subconjunto ya categorizado,
  no del tamaño total de recuerdos/decisiones vigentes ni de cuántas veces
  crece el corpus sin clasificar — contar solo invocaciones a
  `list_current_*` no basta, porque ya se invocan una sola vez por `rank()`
  antes de este encargo (§11.5-M13, literal). Verificado por mutación:
  revertidos los cambios de este encargo, ambas pruebas de este archivo
  fallan (`veces_enumeracion_completa == 1` en vez de `0`, y
  `AttributeError: 'SqliteMemoryRepository' object has no attribute
  'list_current_memories_by_category'`).

## Opciones consideradas

1. **Consulta en lote con `UNION ALL` (claves/prefijos), y
   `list_current_*_by_category` filtrado por el vocabulario completo en SQL
   — elegida.** Mismo patrón que `_por_ids_mixtos` (ids) y ADR-008
   (revisiones vigentes) ya establecen en este código; no introduce
   abstracciones nuevas, y expresa en SQL exactamente la condición que
   `category_index_matches_query` ya exige en Python.
2. **Consultar por el único término literalmente presente en la consulta
   (el enfoque del primer intento, pre-M14).** Descartada: bajo la regla de
   M14 (`activa_categoria_buscable`, ADR-113), cualquier término del
   vocabulario activa la categoría para **todo** candidato categorizado, no
   solo para los candidatos cuya categoría coincide con ese término
   literal — filtrar por el término presente en vez del vocabulario
   completo excluiría candidatos que la semántica real sí admite,
   rompiendo el invariante de identidad frente a las pruebas de M14
   recién fusionadas.
3. **Cachear `list_current_memories()`/`list_current_decisions()` entre
   llamadas dentro de la misma petición.** Descartada: §11.4 punto 2 ya
   señala que un índice en memoria construido a partir de esa misma llamada
   "no reduce nada, sigue leyendo el corpus completo" — el corpus se sigue
   leyendo entero una vez, exactamente el fallo que M13 corrige.

## Decisión

`StagedEnginePort.por_clave_exacta` sustituye su bucle de dos consultas por
clave por una única sentencia `UNION ALL` (una subconsulta por clave, cada
una con su propio `ORDER BY id LIMIT`) sobre `memories` y otra igual sobre
`decisions`. `por_prefijo_de_sujeto` hace lo mismo con `LIKE` por prefijo en
vez de igualdad. Ninguno de los dos cambia con M14: son independientes de
`solo_por_categoria`.

`MemoryRepository`/`DecisionRepository` ganan
`list_current_memories_by_category`/`list_current_decisions_by_category`,
implementados en SQLite con `WHERE status = ... AND category IN (...)`
(comparación insensible a mayúsculas). `sirius.domain.relevance` gana
`category_index_activated(query_text, vocabulary) -> bool`, la condición de
activación que `category_index_matches_query` ya comprobaba internamente,
factorizada para que un caller pueda decidir *antes* de tocar el
repositorio si vale la pena consultarlo. `_rank_via_staged_engine` llama a
`category_index_activated` primero; si no activa nada, el resultado de
`solo_por_categoria` es vacío sin tocar el repositorio, exactamente como
ya ocurría. Si activa, consulta `list_current_memories_by_category`/
`list_current_decisions_by_category` con `self._category_vocabulary`
completo (no con el término literal presente en la consulta) y aplica
`candidate_in_declared_scope` en Python sobre ese subconjunto ya filtrado —
la misma restricción de ámbito que M14 introdujo, sin tocarla.

## Comprobación que la sostiene

- `uv run ruff format --check .` — 574 files already formatted.
- `uv run ruff check .` — All checks passed!
- `uv run mypy src tests` — Success: no issues found in 545 source files.
- `uv run pytest` — 4436 passed, 15 skipped, 2 xfailed (los mismos dos xfail
  preexistentes de M11, sin cambios).
- `git diff --check` — sin salida.
- `tests/integration/test_staged_engine_port_batch_queries.py`: 4 passed.
- `tests/integration/test_rank_relevant_knowledge_category_query_rows.py`: 2
  passed; verificado por mutación contra el código previo a este encargo
  (falla con `veces_enumeracion_completa == 1` y con
  `AttributeError` al no existir el método nuevo).
- `tests/integration/test_rank_relevant_knowledge.py`: 30 passed, sin
  cambiar ninguna aserción de resultado frente a antes de este encargo
  (incluidas las seis pruebas de M14 recién fusionadas).
- `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`: 27 passed, 1
  skipped (Ollama real, no disponible en CI), 1 xfailed (mismo xfail
  preexistente de M11) — mismo resultado que antes de este encargo.

## Consecuencias

`StagedEnginePort` y los repositorios de memoria/decisión ganan un método
más cada uno; ninguna interfaz pública pierde nada. `solo_por_categoria`
sigue siendo el mismo bloque conceptual que M14 dejó (índice de activación
múltiple con restricción de ámbito), pero ya no depende del tamaño total del
corpus para calcular su resultado: depende del tamaño del subconjunto ya
categorizado. El número de consultas de `por_clave_exacta`/
`por_prefijo_de_sujeto` deja de depender de *n*.

## Alternativas descartadas y por qué

Ver «Opciones consideradas» arriba — consultar por el término literal
(semántica pre-M14) y cachear en memoria quedan descartadas por las razones
ya dadas allí.
