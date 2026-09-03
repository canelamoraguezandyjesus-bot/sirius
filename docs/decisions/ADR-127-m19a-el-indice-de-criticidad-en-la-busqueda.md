# ADR-127 — M19a: el índice de criticidad en la búsqueda

- Estado: PROPUESTO
- Fecha: 2026-09-03
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]

Esta es también la nota de arranque de la rama
`feature/m19a-indice-criticidad-busqueda` (incidencia #512, Work ID
WI-20260903-000204), publicada antes del primer cambio de código, con las
cuatro preguntas de la disciplina de evidencia (ADR-001).

## Contexto y problema

`docs/audits/evidencia-experimento-filtro-fiel-al-laboratorio.md`, sección
«Decisión del propietario y plan (02-09-2026)», y ADR-126 (M18b, ya fusionado
en `main`) fijaron que `category` (de qué va) y `criticality` (cuánto
importa) son dos señales independientes, y que «el índice de categoría, la
regla de rescate RF-25/RF-26 y la siembra pasan a mirar la criticidad, no el
tema». M18b introdujo la señal (`Memory.criticality`/`Decision.criticality`,
`list_current_memories_by_criticality`/`list_current_decisions_by_criticality`)
sin cablearla a nada. M19 se parte en dos encargos en serie porque el rescate
(M19b) se mide con Ollama y el índice (M19a, este encargo) no — cada uno cabe
en una ejecución.

Medido en `scripts/medir_variantes_de_criticidad.py` (M18b, sin cambios en
esa medición): con el índice de categoría mirando el **tema** (`trabajo`,
`personal`, `salud`…, ADR-116) en vez de la criticidad, la búsqueda de
producción pierde 9 críticas del banco de 47, todas `NO_ENTRO` — las
consultas que piden lo crítico («Dame todas las restricciones esenciales…»,
«¿Qué restricciones de transporte tengo?») no activan el índice porque su
vocabulario es temático, no contiene «restriccion»/«esencial». La variante
`A_porte_fiel` (vocabulario del laboratorio + categoría derivada de la
criticidad) ya midió, sobre el arnés de examen, que ese vocabulario baja las
críticas `NO_ENTRO` de 9 a 3.

## Nota de arranque (cuatro preguntas, ADR-001)

**1. ¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo
observar el fallo que arregla?**

El fallo vive en `RankRelevantKnowledgeUseCase._rank_via_staged_engine`
(`src/sirius/application/rank_relevant_knowledge.py`): el único bloque de
ampliación que existe hoy (`solo_por_categoria`) solo mira `category`, nunca
`criticality`, así que una consulta que pide lo crítico con vocabulario de
criticidad nunca activa ninguna ampliación. El arreglo vive en el mismo
método — un segundo bloque de ampliación, `solo_por_criticidad`, que reutiliza
exactamente el mismo patrón (activación de índice, dedup contra el motor y
contra el otro bloque, restricción de ámbito) con el otro par
puerto/vocabulario. Sí puede observarse: cada pieza nueva tiene su propia
prueba unitaria (activación, `RankedKnowledge.criticality_match`, `_sort_key`)
o de integración (el bloque completo contra SQLite real), y el banco de 47
casos mide el resultado agregado con `scripts/medir_variantes_de_criticidad.py`
y `test_pa_0_2_rec_01_banco_evidencia.py`.

**2. ¿Qué NO va a garantizar esto?**

- No toca RF-25/RF-26 ni G8/G12 (`ContextBuilder._apply_relevance_filter`,
  `_MAX_CRITICALITY_CATEGORY`): eso es M19b, el siguiente encargo en la serie.
- No añade la siembra en contexto (M20) ni la propuesta automática de
  criticidad (M21).
- No cambia `category`, `_CATEGORY_VOCABULARY`, `category_locked` ni la
  semántica D7: el índice de categoría existente sigue exactamente igual,
  byte a byte, con la misma entrada.
- No abre la puerta `category_matching_enabled` por defecto: sigue cerrada
  en producción hasta que una decisión posterior la abra; con la puerta
  cerrada, `criticality_vocabulary` vacío es el único estado alcanzable, como
  ya ocurre con `category_vocabulary`.
- No garantiza que las tres identidades de B04-CA-34 (DEC-003, MEM-014,
  MEM-016) entren: esas solo se piden por «Prepara el contexto de
  planificación de Alfa», que no contiene ninguna palabra del vocabulario de
  criticidad — es la siembra (M20), no el índice.

**3. Criterio de parada (decidido antes de ver ningún resultado)**

Predicción escrita antes de construir, sobre el banco de 47 casos:

- `uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q -s`,
  fila del paquete completo: aciertos exactos **7/47** (sin cambio), críticas
  `NO_ENTRO` **9 → 3** (quedan solo las tres de B04-CA-34: DEC-003, MEM-014,
  MEM-016 — la siembra, M20), elementos de más **285 → 260** (±5), cobertura
  **62 → 68/81**.
- `uv run python scripts/medir_variantes_de_criticidad.py`: la variante `hoy`
  (que pasa a ejercitar el índice de criticidad real) reproduce esas mismas
  cifras; `A_porte_fiel` no aporta ya nada distinto de `hoy` salvo la
  categoría derivada de criticidad (que `hoy` no tiene).
- Con la puerta `category_matching_enabled` cerrada, ningún resultado de
  `rank()` cambia: las pruebas existentes que fijan ese comportamiento siguen
  pasando sin tocarlas.

Si las críticas `NO_ENTRO` no bajan a 3, o si los elementos de más superan
300, se para y se busca la raíz — no se ajusta el vocabulario para cuadrar el
número (regla de las dos rondas, ADR-001).

**4. ¿Qué hace esto imposible, en vez de improbable?**

Que un candidato hallado solo por criticidad se pierda en el intercalado por
no ser nunca «relacionado»: `RankedKnowledge.criticality_match` amplía
`is_related` exactamente como `category_match` ya lo hace (M9) — sin esa
ampliación, `rank_relevant_knowledge` (llamada dentro de
`_intercalar_por_categoria` para ordenar y para decidir el intercalado)
filtraría en silencio todo candidato de solo-criticidad que no tenga además
un `fts_match`/`subject_matches_query`, vaciando el bloque entero sin ningún
error visible. Una prueba unitaria (`test_a_criticality_match_alone_makes_an_
otherwise_unrelated_candidate_related`) y una de integración (el bloque
completo contra SQLite real) lo fijan explícitamente. También hace imposible
que un candidato ya admitido por el motor o por el bloque de categoría se
duplique en el bloque de criticidad: el dedup comprueba `(kind, id)` contra
los dos conjuntos antes de añadir, nunca solo contra uno.

## Opciones consideradas

1. **Fusionar los dos vocabularios en el índice de categoría existente**
   (`_CATEGORY_VOCABULARY | criticality_vocabulary`, un solo bloque).
   Descartada: la incidencia prohíbe tocar `_CATEGORY_VOCABULARY`/`category`/
   `category_locked`/la semántica D7, y fusionar vocabularios cambiaría qué
   activa el índice de categoría existente para consultas que hoy no lo
   activan — exactamente lo que `B_arreglo_ingenuo` (medido en M18b) ya
   demostró que dispara los elementos de más muy por encima de la variante
   fiel al laboratorio.
2. **Un flag de activación propio para el índice de criticidad**, separado de
   `category_matching_enabled`. Descartada: la incidencia no autoriza una
   puerta nueva (fuera de alcance, «no abras la puerta por defecto» ya se
   refiere a la existente); el índice de criticidad es una ampliación más
   detrás de la misma puerta D7 punto 6, igual que el de categoría.
3. **Segundo bloque de ampliación paralelo, misma puerta, vocabulario y
   repositorio propios** (elegida): calca la forma exacta que
   `solo_por_categoria` ya estableció — activación por índice
   (`category_index_activated`, reutilizada tal cual con el otro
   vocabulario), consulta a `list_current_*_by_criticality`, dedup contra lo
   admitido por el motor y contra el otro bloque, restricción de ámbito
   (`candidate_in_declared_scope`), señal estructural nueva
   (`criticality_match`) que amplía `is_related` y entra en `_sort_key`
   justo después de `category_match`.

## Decisión

Añadir un segundo bloque de ampliación, `solo_por_criticidad`, en
`RankRelevantKnowledgeUseCase._rank_via_staged_engine`, con la misma forma
que `solo_por_categoria` pero sobre `criticality`/`list_current_*_by_criticality`
en vez de `category`/`list_current_*_by_category`:

- Vocabulario nuevo, `_CRITICALITY_VOCABULARY` (`composition_root.py`),
  portado literal de `tests/acceptance/staged_engine_category_and_relevance.py:244-251`
  (`VOCABULARIO_DE_CATEGORIA`, a su vez portado de
  `experiments/adr002/lateral/categoria.py:72-78`): `{"esencial",
  "restriccion", "critica", "obligatoria", "imprescindible"}`.
- `RankRelevantKnowledgeUseCase` gana el parámetro `criticality_vocabulary:
  frozenset[str] = frozenset()`, cableado a producción/medición exactamente
  donde `category_vocabulary` ya lo está: `composition_root.py` (la
  construcción real, detrás de la misma puerta),
  `tests/integration/test_local_performance.py` (la medición de RNF-003 con
  el paquete completo) y
  `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py::_ejecutar_banco_
  paquete_completo` (el arnés del banco de 47). La incidencia también cita
  `composition_root.py:631`; en el estado actual del árbol esa línea es
  `ConversationDependencies.category_vocabulary` (el vocabulario que expone
  la interfaz de etiquetado manual, D7 punto 3) — un campo sin relación con
  `RankRelevantKnowledgeUseCase` ni con esta ampliación de búsqueda, así que
  no se toca; el único punto real de cableado en `composition_root.py` es la
  construcción de `RankRelevantKnowledgeUseCase` (una única llamada en todo
  el fichero).
- Activación: `category_index_activated(query_text, self._criticality_vocabulary)`
  — la misma función, reutilizada con el otro vocabulario (la función ya es
  genérica: no depende de nada específico de categoría), sin duplicar la
  normalización.
- `RankedKnowledge.criticality_match: bool = False`, quinta señal
  estructural, con el mismo estilo de docstring que `category_match` —
  incluida su ampliación de `is_related` (ver pregunta 4 arriba).
  `_sort_key` la incorpora justo después de `not candidate.category_match`.
- `ContextBuilder`/`_apply_relevance_filter`, `rescue_max_criticality_
  candidates`, `truncate_to_hard_limit` y `_MAX_CRITICALITY_CATEGORY`: sin
  tocar (M19b).

## Comprobación que la sostiene

(completar tras implementar y ejecutar las cuatro validaciones obligatorias y
las dos mediciones del criterio de parada)

## Consecuencias

- `RankRelevantKnowledgeUseCase.rank()`, con la puerta abierta y el
  vocabulario de criticidad cableado, encuentra candidatos que ni el motor
  por etapas ni el índice de categoría encontraban, cuando la consulta
  contiene una palabra del vocabulario de criticidad.
- `RankedKnowledge` gana una señal estructural más; ningún candidato
  existente cambia de orden relativo porque todo caller que no construye
  `criticality_match` explícitamente sigue recibiendo `False`.
- `scripts/medir_variantes_de_criticidad.py` deja de tener sentido tal como
  está escrito: su variante `hoy` pasa a ejercitar el índice de criticidad
  real (antes ausente), así que dice de más que "hoy" ya no es un control
  sin cambios; se actualiza su docstring y predicción impresa para reflejarlo,
  sin tocar su lógica de medición.

## Alternativas descartadas y por qué

Ver «Opciones consideradas» arriba.
