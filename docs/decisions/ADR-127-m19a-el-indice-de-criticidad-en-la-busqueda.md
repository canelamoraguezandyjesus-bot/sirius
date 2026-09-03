# ADR-127 — M19a: el índice de criticidad en la búsqueda

- Estado: PROPUESTO
- Fecha: 2026-09-03
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]

**Nota sobre líneas citadas por la incidencia:** #512 cita
`composition_root.py:631` como segundo punto de cableado del parámetro nuevo,
junto a `:489`. En el estado actual del árbol, `:631` es
`ConversationDependencies.category_vocabulary` (el vocabulario que expone la
interfaz de etiquetado manual, D7 punto 3) — un campo sin relación con
`RankRelevantKnowledgeUseCase` ni con esta ampliación de búsqueda. Verificado
con `grep -n "RankRelevantKnowledgeUseCase(" src/sirius/composition_root.py`:
una única construcción en todo el fichero, en `:484-493`. No se toca `:631`.

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

Comandos ejecutados tras completar la implementación (vocabulario en
`composition_root.py`, parámetro `criticality_vocabulary` en
`RankRelevantKnowledgeUseCase`, bloque `solo_por_criticidad` en
`_rank_via_staged_engine`, `RankedKnowledge.criticality_match` y su
ampliación de `is_related`/`_sort_key`), en este orden:

1. `uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q -s`
   → `27 passed, 1 skipped, 1 xfailed`. Fila del paquete completo:
   `aciertos_exactos=7/47 elementos_de_mas=290 omisiones_criticas=3
   cobertura=68/81 (84.0%)` — coincide con la predicción en aciertos exactos
   (7/47), omisiones críticas (9→3, quedan solo B04-CA-34: DEC-003, MEM-014,
   MEM-016) y cobertura (68/81). `elementos_de_mas` mide 290, dentro del
   límite del criterio de aceptación (≤300) pero por encima de la banda
   ±5 sobre 260 que la nota de arranque estimaba a partir de la variante
   `A_porte_fiel` (M18b) — explicado abajo, no es motivo de parada porque el
   criterio de parada escrito es el límite de 300, no esa banda.
2. `uv run python scripts/medir_variantes_de_criticidad.py` →
   `hoy=7/47,290,3,68/81` / `A_porte_fiel=7/47,260,3,68/81` /
   `B_arreglo_ingenuo=7/47,354,3,68/81`. `hoy` y `A_porte_fiel` coinciden
   ahora en las tres métricas de búsqueda (exactos, `NO_ENTRO`, cobertura) —
   confirma que el índice de criticidad cierra la causa (a) de la evidencia
   igual que lo hacía la variante fiel al laboratorio. La diferencia de
   `elementos_de_mas` (290 vs 260) es explicable, no un error: `hoy` sigue
   ejecutando el índice de categoría temático (ADR-116) EN PARALELO al de
   criticidad —los dos bloques de ampliación conviven, tal como pide la
   incidencia («sin tocar `_CATEGORY_VOCABULARY`»)—, mientras que
   `A_porte_fiel` **sustituye** la categoría por la derivada de criticidad en
   vez de sumarla; `hoy` trae, además de lo que aporta el índice de
   criticidad, lo que ya aportaba el índice de categoría antes de este
   encargo (285 en la medición base de M18b) más el neto de criticidad. Sigue
   por debajo del límite duro de 300 que fija el criterio de aceptación de la
   incidencia.
3. `uv run ruff format --check .` → `587 files already formatted`.
4. `uv run ruff check .` → `All checks passed!`.
5. `uv run mypy src tests` → `Success: no issues found in 555 source files`.
6. `uv run pytest -q` (suite completa) → `4563 passed, 15 skipped, 2 xfailed`
   en 407 s. Ningún fallo, ninguna prueba debilitada u omitida. (La primera
   corrida completa encontró un fallo real y distinto de la implementación:
   `tests/automation/test_citas_de_los_adr.py` — este ADR cita
   `experiments/adr002/lateral/categoria.py` con línea concreta, réplica del
   vocabulario del laboratorio, y esa ruta vive en `evidence/adr001-spikes`,
   nunca fusionada a `main`; se corrigió registrando `_ADR_127` en la entrada
   ya existente de `RAMA_DE_ORIGEN_NO_FUSIONADA` para esa ruta —el mismo
   mecanismo que ya usan ADR-112/113/114 para la misma cita—, no ocultando ni
   debilitando la prueba.)
7. `git diff --check` → limpio (sin salida, código de salida 0).
8. Prueba por mutación (ADR-001) sobre el dedup del bloque de criticidad
   contra lo admitido por el motor: se sustituyó temporalmente la condición
   `if clave in admitidos_por_el_motor or clave in ya_admitidos_por_categoria`
   por `if clave in ya_admitidos_por_categoria` (quitando la mitad del dedup
   contra el motor) en el bloque de memorias de `solo_por_criticidad`; se
   confirmó que
   `test_staged_engine_criticality_block_never_duplicates_a_candidate_the_motor_already_admitted`
   **falla** (`assert [1, 1] == [1]`, el candidato aparece duplicado), y se
   restauró el código real, confirmando que la prueba vuelve a pasar — la
   prueba sí detecta la ausencia del dedup que dice sostener.
9. Pruebas nuevas vistas fallar antes del cambio (ADR-001): las unitarias de
   `criticality_match`/`is_related`/`_sort_key`
   (`tests/unit/test_relevance_domain.py`) y las de integración del bloque
   `solo_por_criticidad` (`tests/integration/test_rank_relevant_knowledge.py`)
   fallaban con `TypeError: RankRelevantKnowledgeUseCase.__init__() got an
   unexpected keyword argument 'criticality_vocabulary'` (o, para las
   puramente de dominio, con `RankedKnowledge` sin el campo) contra el código
   de antes de este encargo — reproducido explícitamente durante el propio
   desarrollo (el mismo error resurgió al revertir por accidente
   `rank_relevant_knowledge.py` mientras se hacía la prueba por mutación del
   punto 8, y las siete pruebas de integración de criticidad fallaron con
   exactamente ese `TypeError` hasta reaplicar el cambio).

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
