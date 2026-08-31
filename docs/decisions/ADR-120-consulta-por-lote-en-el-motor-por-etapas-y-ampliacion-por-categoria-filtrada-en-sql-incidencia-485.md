# ADR-120 — Sustituir el bucle de consultas por clave/prefijo y el barrido completo del corpus por consulta en lote / filtrada en SQL (M13, incidencia #485)

- Estado: APROBADO
- Fecha: 2026-08-31
- Aprobación: fusión de la PR por el propietario

## Contexto y problema

§11.4 (puntos 1 y 2) de `docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md`
diagnostica, por lectura directa del código, dos de las tres causas
plausibles de que «construir contexto» con el paquete completo activo mida
438-780 ms en vez de los ~120 ms que ADR-008 mide con la puerta cerrada:

1. `StagedEnginePort.por_clave_exacta`/`por_prefijo_de_sujeto`
   (`src/sirius/adapters/persistence/staged_engine_port.py`) ejecutan **dos
   consultas SQL por cada clave o prefijo**, dentro de un bucle Python, en
   vez de una sola consulta por lote — a diferencia del patrón que
   `_por_ids_mixtos` ya usa para ids, y que ADR-008 ya adoptó para el
   listado de revisiones vigentes.
2. El bloque `solo_por_categoria` de `_rank_via_staged_engine`
   (`src/sirius/application/rank_relevant_knowledge.py:243-280`) recorre,
   con la puerta `category_matching_enabled` abierta, la totalidad de
   `list_current_memories()`/`list_current_decisions()` en cada llamada a
   `rank()` — un segundo barrido completo del corpus, filtrado en Python en
   vez de en SQL.

M13 (§11.5) encarga sustituir ambos por consulta en lote / filtrada en SQL,
sin alterar qué se admite ni en qué orden — invariante innegociable de la
incidencia, verificado por las pruebas de identidad existentes
(`tests/integration/test_rank_relevant_knowledge.py`,
`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`, el arnés de
examen).

## Nota de arranque (las cuatro preguntas, ADR-001 / disciplina-evidencia)

**1. ¿Dónde vive el fallo y dónde voy a poner el arreglo? ¿Puede el sitio del
arreglo observar el fallo que arregla?**

El fallo vive en dos sitios y el arreglo va en esos mismos sitios:

- `por_clave_exacta`/`por_prefijo_de_sujeto`: el bucle `for clave in
  utiles`/`for prefijo in utiles` que dispara dos `session.execute` por
  iteración. El arreglo sustituye ese bucle por una única consulta con
  `WHERE subject_key IN (...)` (u `OR ... LIKE` encadenado para el prefijo,
  que no admite `IN`), mismo patrón de marcas nombradas que
  `_por_ids_mixtos` ya usa. Sí puede observar el fallo: un contador de
  sentencias SQL ejecutadas (event listener `before_cursor_execute` de
  SQLAlchemy, el mismo instrumento que
  `tests/integration/test_memory_decision_list_query_count.py` ya usa para
  ADR-008) cuenta exactamente cuántas consultas emite cada método para *n*
  claves/prefijos; el arreglo se mide con el mismo contador que primero
  demuestra el fallo.
- `solo_por_categoria`: la llamada a `list_current_memories()`/
  `list_current_decisions()` sin filtro. El arreglo sustituye esa llamada
  por un nuevo método del puerto (`list_current_memories_by_category`/
  `list_current_decisions_by_category`) que ejecuta `WHERE category IN
  (...)` en SQL. `category_matches_query` (`sirius.domain.relevance`) ya
  garantiza que una consulta activa como mucho una categoría del
  vocabulario a la vez (activación ambigua → no coincide con nada), así que
  el conjunto de categorías relevantes para una llamada a `rank()` es
  siempre 0 o 1 elemento — nunca hace falta iterar el vocabulario completo
  ni el corpus completo para calcularlo. Sí puede observar el fallo: una
  prueba con un repositorio real sobre un corpus con muchos elementos fuera
  de la categoría solicitada y pocos dentro cuenta las filas que el
  repositorio devuelve.

**2. ¿Qué NO va a garantizar esto?**

No garantiza que RNF-003 P95 baje a ≤300 ms — eso lo mide M17 aparte, sobre
el paquete M13-M16 integrado, y §11.4 ya deja escrito que esta arquitectura
no lo promete de antemano. No cambia qué candidatos se admiten ni su orden
(invariante del encargo). No toca el bloque `solo_por_categoria` más allá de
sustituir la fuente de datos por una filtrada — M14 lo sustituye entero
después, y esta incidencia no adelanta esa sustitución. No reduce el número
de consultas al mínimo teórico (una sola consulta universal para todas las
etapas): solo elimina el crecimiento lineal con *n* claves/prefijos y el
barrido completo del corpus.

**3. Criterio de parada, decidido antes de medir:**

Si tras sustituir el bucle de `por_clave_exacta`/`por_prefijo_de_sujeto` por
una consulta en lote el número de sentencias SQL sigue creciendo con *n*
(medido con el contador de ADR-008), la causa no era el bucle de Python y
hay que decirlo en el ADR en vez de seguir tocando el mismo código. Si tras
filtrar `solo_por_categoria` en SQL el número de filas que el repositorio
devuelve sigue dependiendo del tamaño total del corpus en vez del tamaño del
subconjunto que coincide con la categoría activada, parar y diagnosticar en
vez de parchear más.

**4. ¿Qué hace el fallo imposible en vez de improbable?**

Dos pruebas de integración nuevas, cada una verificada por mutación
(restaurando el bucle/el barrido completo, comprobando que la prueba nueva
falla con la versión vieja y pasa con la corregida):

- Una prueba que cuenta las sentencias SQL que
  `por_clave_exacta`/`por_prefijo_de_sujeto` ejecutan para un conjunto
  pequeño de claves/prefijos frente a uno mucho mayor, y afirma que el
  conteo **no crece** — no una comparación de invocaciones al método, sino
  de sentencias SQL reales sobre SQLite.
- Una prueba que, con la puerta `category_matching_enabled` abierta y un
  corpus donde la categoría solicitada es un subconjunto pequeño frente al
  total, cuenta las filas que el repositorio devuelve para
  `solo_por_categoria` y afirma que ese número depende del tamaño del
  subconjunto de la categoría, no del tamaño total de recuerdos/decisiones
  vigentes — contar solo invocaciones a `list_current_*` no basta, porque
  ya se invocan una sola vez por `rank()` antes de este encargo (§11.5-M13,
  literal).

## Opciones consideradas

1. **Consulta en lote con `IN (...)` (claves) / `OR ... LIKE` encadenado
   (prefijos), y nuevo método del puerto filtrado por categoría en SQL —
   elegida.** Mismo patrón que `_por_ids_mixtos` (ids) y ADR-008
   (revisiones vigentes) ya establecen en este código; no introduce
   abstracciones nuevas.
2. **Cachear `list_current_memories()`/`list_current_decisions()` entre
   llamadas dentro de la misma petición.** Descartada: §11.4 punto 2 ya
   señala que un índice en memoria construido a partir de esa misma llamada
   "no reduce nada, sigue leyendo el corpus completo" — el corpus se sigue
   leyendo entero una vez, exactamente el fallo que M13 corrige.
3. **Añadir un índice de categoría buscable (activación múltiple, ámbito).**
   Es M14, no M13: la nota de dependencias del objetivo prohíbe adelantarlo
   aquí porque M14 sustituye `solo_por_categoria` entero y cualquier avance
   dejaría un conflicto para esa incidencia paralela.

## Decisión

`StagedEnginePort.por_clave_exacta` sustituye su bucle de dos consultas por
clave por una única consulta con `subject_key IN (...)` sobre `memories` y
otra con `subject IN (...)` sobre `decisions` (dos consultas totales para
*n* claves, no `2n`). `por_prefijo_de_sujeto` sustituye su bucle por una
única consulta por tabla con una cláusula `LIKE` por prefijo unida con `OR`
(el operador `IN` no expresa coincidencia de prefijo; `OR` encadenado sigue
siendo una sola sentencia SQL, igual que el diagnóstico de §11.4 punto 1
autoriza explícitamente — "`IN (...)` (o `OR` encadenado)").

`MemoryRepository`/`DecisionRepository` ganan
`list_current_memories_by_category`/`list_current_decisions_by_category`,
implementados en SQLite con `WHERE status = ... AND category IN (...)`
(comparación insensible a mayúsculas, igual que
`category_matches_query`). `_rank_via_staged_engine` calcula, antes de
recorrer nada, la única categoría que la consulta activa contra el
vocabulario (`activated_category_term`, nueva función pública de
`sirius.domain.relevance`, extraída de la lógica de activación que
`category_matches_query` ya tenía) y solo llama a los métodos nuevos cuando
hay una categoría activada — si la consulta activa cero o más de una, el
resultado de `solo_por_categoria` es vacío sin tocar el repositorio, como ya
ocurría antes de este encargo.

## Comprobación que la sostiene

- `tests/integration/test_staged_engine_port_batch_queries.py` (nuevo):
  cuenta sentencias SQL con el mismo `event.listen(Engine,
  "before_cursor_execute", ...)` que
  `tests/integration/test_memory_decision_list_query_count.py`, para
  `por_clave_exacta` y `por_prefijo_de_sujeto`, con pocos y muchos
  argumentos.
- `tests/integration/test_rank_relevant_knowledge_category_query_rows.py`
  (nuevo): cuenta filas devueltas por
  `list_current_memories_by_category`/`list_current_decisions_by_category`
  a través de `_rank_via_staged_engine`, sobre un corpus con muchos
  elementos fuera de la categoría solicitada.
- Suite completa (`uv run ruff format --check .`, `uv run ruff check .`,
  `uv run mypy src tests`, `uv run pytest`, `git diff --check`) en verde —
  detalle en la PR.
- Las pruebas de identidad existentes
  (`tests/integration/test_rank_relevant_knowledge.py`,
  `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`, el arnés de
  examen) siguen pasando sin cambiar ninguna aserción de resultado.

## Consecuencias

`StagedEnginePort` y los repositorios de memoria/decisión ganan un método
más cada uno; ninguna interfaz pública pierde nada. `solo_por_categoria`
sigue siendo el mismo bloque conceptual (M14 lo sustituye después), pero ya
no depende del tamaño total del corpus para calcular su resultado. El
número de consultas de `por_clave_exacta`/`por_prefijo_de_sujeto` deja de
depender de *n*; sigue dependiendo de si hay memorias y decisiones que
consultar (dos sentencias, no una), igual que `_por_ids_mixtos` ya acepta.

## Alternativas descartadas y por qué

Ver «Opciones consideradas» arriba — cachear en memoria y adelantar el
índice de M14 quedan descartadas por las razones ya dadas allí.
