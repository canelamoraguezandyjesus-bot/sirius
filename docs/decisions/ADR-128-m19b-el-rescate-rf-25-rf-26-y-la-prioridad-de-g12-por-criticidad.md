# ADR-128 — M19b: el rescate RF-25/RF-26 y la prioridad de G12 por criticidad

- Estado: PROPUESTO
- Fecha: 2026-09-03
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]

Esta es también la nota de arranque de la rama
`feature/m19b-rescate-por-criticidad` (incidencia #514, Work ID
WI-20260903-005039), publicada antes del primer cambio de código, con las
cuatro preguntas de la disciplina de evidencia (ADR-001).

## Contexto y problema

`docs/audits/evidencia-experimento-filtro-fiel-al-laboratorio.md`, sección
«Resultado en la máquina del propietario (Ollama real, 02-09-2026)», midió
que la regla de rescate RF-25/RF-26 (`rescue_max_criticality_candidates`,
`src/sirius/domain/relevance.py`) rescata por `category ==
max_criticality_category`, y esa categoría en producción es `"salud"`
(ADR-116, provisional) — ninguna crítica del banco de 47 casos lleva esa
categoría, así que DEC-003 (CRITICO, categoría `finanzas`) en B04-CA-23 fue
descartada por el modelo y ninguna regla la rescató
(`TIRADO_POR_EL_FILTRO`, 1 de las 10 críticas perdidas medidas ese día).

M18b (ADR-126) ya dio a cada `Memory`/`Decision` una señal independiente,
`criticality: Criticality | None` (CRITICO/IMPORTANTE/`None`), y M19a
(ADR-127, incidencia #512, ya en `main`, head `cacc632`) ya hizo que la
*búsqueda* ampliara por esa señal en vez de por tema. M19b es la segunda
mitad de la misma decisión del propietario (02-09-2026, misma auditoría,
sección «Decisión del propietario y plan»): que el *rescate* (RF-25/RF-26)
y la *prioridad al truncar* (G12, `truncate_to_hard_limit`) miren también la
criticidad, no el tema — únicamente detrás de la puerta
`category_matching_enabled` ya existente, sin abrirla por defecto.

## Nota de arranque (cuatro preguntas, ADR-001)

**1. ¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo
observar el fallo que arregla?**

El fallo vive en `rescue_max_criticality_candidates` y
`truncate_to_hard_limit` (`src/sirius/domain/relevance.py`): ambas reciben
`max_criticality_category: str | None` y comparan `candidate.item.category`
contra él — la señal de *tema*, no la de *cuánto importa*. El arreglo vive
en las mismas dos funciones, que dejan de recibir la categoría:
`rescue_max_criticality_candidates` pasa a recibir un predicado
`is_protected: Callable[[RankedKnowledge], bool]` (RF-25/RF-26 solo
necesitan "protegido o no"); `truncate_to_hard_limit` pasa a recibir
`protection_rank: Callable[[RankedKnowledge], int]` (corregido en la ronda
2 de esta revisión, CODEX-001: una primera versión reutilizó el mismo
booleano para G12, lo que dejaba a un IMPORTANTE llegado antes en la lista
sobrevivir sobre un CRITICO llegado después; G12 necesita un rango de tres
niveles — CRITICO=0, IMPORTANTE=1, ordinario=2 — porque prioriza *entre*
candidatos protegidos al truncar, algo que RF-25/RF-26 nunca necesitan
decidir). En `ContextBuilder._apply_relevance_filter`
(`src/sirius/application/context.py`), con la puerta ABIERTA,
`_is_protected_by_criticality` (booleano, `criticality is not None`)
construye el predicado de RF-25/RF-26 y `_criticality_protection_rank`
(entero de tres niveles) construye el de G12 — ninguno de los dos mira ya
`category`. Sí puede observarse: cada pieza tiene su propia prueba unitaria
de dominio (RF-25/RF-26 y G12 con predicados de criticidad, ambas vistas
fallar antes del cambio con `TypeError` por el parámetro inexistente) y de
integración (`ContextBuilder` real con un doble de filtro que descarta un
CRITICO de categoría `finanzas`), y el banco de 47 casos mide el agregado.

**2. ¿Qué NO va a garantizar esto?**

- No toca el camino con la puerta CERRADA: el candado de M10
  (`category is None or category == max_criticality_category`) sigue
  byte a byte, porque `_MAX_CRITICALITY_CATEGORY` sigue gobernando ese
  camino (y D7).
- No toca la protección incondicional de `category is None` en el camino
  ABIERTO (contrato de D7 punto 2) — sigue exactamente igual.
- No toca `RankRelevantKnowledgeUseCase`, el índice de categoría ni el de
  criticidad (M19a): esos ya miran `criticality` desde el encargo anterior.
- No añade la siembra de contexto (M20) ni la propuesta automática de
  criticidad (M21), ni cambia `_HARD_LIMIT_SIN_ATAR` ni abre
  `category_matching_enabled` por defecto.
- No garantiza, sin Ollama (este runner), ningún cambio en el banco de 47
  casos: el doble de filtro que nunca descarta no le da a RF-25/RF-26 nada
  que rescatar, así que las cuatro métricas del paquete completo deben
  seguir siendo exactamente las de M19a (7/47, 290, 3, 68/81). Solo en la
  máquina del propietario, con Ollama real, se puede medir el efecto sobre
  `TIRADO_POR_EL_FILTRO` — esta ejecución no tiene Ollama y no lo mide.

**3. Criterio de parada (decidido antes de ver ningún resultado)**

Predicción escrita antes de construir:

- En este runner, sin Ollama, el banco de 47 casos NO cambia respecto a
  M19a: `uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`
  sigue dando aciertos exactos 7/47, elementos de más 290, omisiones
  críticas 3 (las tres de B04-CA-34), cobertura 68/81; y
  `uv run python scripts/medir_variantes_de_criticidad.py` sigue dando
  `hoy` = 3 `NO_ENTRO`.
- En la máquina del propietario, con Ollama real
  (`uv run python scripts/medir_banco_con_ollama_real.py --diagnostico`,
  modelo `qwen3:4b-instruct`, espera 30 s), **medido el 05-09-2026 sobre
  main `a07c5d5`, ya con M20 (ADR-129) fusionada**: 47 llamadas, 0
  rendiciones, 0,8 min. Críticas `TIRADO_POR_EL_FILTRO` **1 → 0** — la
  predicción propia de este encargo se cumple: ninguna crítica descartada
  por el modelo quedó sin rescatar — y críticas perdidas totales **10 → 0**.
  El tramo 10 → 3 de M19b y el 3 → 0 de M20 no pueden separarse a
  posteriori, porque la medición llegó con los dos encargos dentro; lo que
  sí es atribuible a este es que la única pérdida de la clase que RF-25/RF-26
  gobierna desapareció. Resto de la medición: aciertos exactos 8/47,
  cobertura 70/81, 218 elementos de más — registro completo, con la
  comparación contra el 02-09, en
  `docs/audits/evidencia-experimento-filtro-fiel-al-laboratorio.md`, sección
  «Resultado en la máquina del propietario (Ollama real, 05-09-2026)».

Si en este runner cambia cualquier métrica del banco de 47 casos, este
encargo ha tocado algo que no debía (el camino sin Ollama no puede verse
afectado por un cambio que solo actúa cuando el filtro descarta algo) y se
para a buscar la causa en vez de ajustar código para cuadrar el número
(regla de las dos rondas, ADR-001).

**4. ¿Qué hace esto imposible, en vez de improbable?**

Que un candidato IMPORTANTE (no solo CRITICO) se quede sin protección: el
predicado es `criticality is not None`, nunca `criticality is
Criticality.CRITICO`, así que ambos niveles quedan protegidos por igual —
exactamente como el laboratorio original protegía todo lo etiquetado
`restriccion` sin distinguir niveles dentro de «no ordinario»
(`tests/acceptance/staged_engine_category_and_relevance.py:472-513`,
`aplicar_regla_de_criticas_original`). Una prueba unitaria que rescata un
IMPORTANTE descartado (no solo un CRITICO) lo fija explícitamente, y la
mutación descrita abajo (estrechar el predicado a solo CRITICO) confirma
que esa prueba SÍ detecta la ausencia de esa protección.

## Opciones consideradas

1. **Añadir `criticality` como una segunda comparación en las mismas dos
   funciones**, junto a `max_criticality_category` (`category == X or
   criticality is not None`). Descartada: mantendría el camino ABIERTO
   mirando dos señales a la vez cuando el encargo pide que mire solo la
   criticidad; y dejaría sin sentido el parámetro `max_criticality_category`
   en las dos llamadas del camino abierto, que ya no lo necesitarían para
   nada.
2. **Duplicar las dos funciones** (`rescue_max_criticality_candidates`/
   `rescue_by_criticality_candidates`) para no tocar la firma existente.
   Descartada: el candado del camino CERRADO nunca llama a estas dos
   funciones (usa su propia unión inline en `_apply_relevance_filter`), así
   que no hay ningún llamador real que dependa de la firma actual salvo el
   camino ABIERTO que este encargo sí puede cambiar; duplicar el cuerpo casi
   idéntico de las dos funciones para una única diferencia (qué predicado se
   evalúa) es la abstracción equivocada que el propio criterio de simplicidad
   del repositorio desaconseja.
3. **Una función inyectada por el llamador en cada una de las dos** (elegida,
   la que pide el propio encargo): las dos funciones de dominio dejan de
   saber nada sobre `category` ni sobre `criticality` — solo aplican lo que
   reciben —, y `ContextBuilder` decide qué construir según el estado de la
   puerta. El camino CERRADO no las llama en absoluto (sigue con su unión
   inline byte a byte), así que cambiar su firma no lo toca.

   No es la misma función para las dos, y esa es la corrección de la ronda 2
   (CODEX-001): `rescue_max_criticality_candidates` (RF-25/RF-26) recibe un
   **predicado booleano**, `is_protected: Callable[[RankedKnowledge], bool]`
   —solo necesita distinguir protegido de no protegido—, mientras que
   `truncate_to_hard_limit` (G12) recibe un **rango entero**,
   `protection_rank: Callable[[RankedKnowledge], int]` (menor sobrevive
   antes), porque prioriza *entre* candidatos protegidos al truncar y un
   booleano los agruparía en un solo nivel, dejando a un IMPORTANTE llegado
   antes sobrevivir sobre un CRITICO llegado después. La primera versión de
   esta opción usaba el booleano para las dos; se descartó al medirlo contra
   la prioridad que `aplicar_g12` ya fijaba
   (`src/sirius/domain/staged_engine_gates.py:333`).

## Decisión

`rescue_max_criticality_candidates` (`src/sirius/domain/relevance.py`)
cambia su parámetro `max_criticality_category: str | None` por
`is_protected: Callable[[RankedKnowledge], bool]`: RF-25/RF-26 solo
necesitan distinguir protegido de no protegido, nunca priorizar entre dos
candidatos protegidos. Se conserva el nombre público
`rescue_max_criticality_candidates` (cambiarlo obligaría a tocar más
superficie de la necesaria); su docstring documenta que «máxima
criticidad» ahora la decide el predicado que reciba, y que
`ContextBuilder` es quien lo construye según la puerta.

`truncate_to_hard_limit` cambia el mismo parámetro por
`protection_rank: Callable[[RankedKnowledge], int]`, no por un booleano: a
diferencia de RF-25/RF-26, G12 prioriza *entre* candidatos protegidos al
truncar por el límite duro, y un booleano agruparía CRITICO e IMPORTANTE en
un mismo nivel, dejando que el orden de llegada decidiera cuál sobrevive
entre los dos. Esto se corrigió en la ronda 2 de esta revisión (CODEX-001):
la primera versión reutilizaba el mismo `is_protected` booleano también
para G12, y una prueba dedicada
(`test_truncate_to_hard_limit_prioritises_critico_over_importante_even_when_importante_arrives_first`,
`tests/unit/test_relevance_domain.py`) demostró que un IMPORTANTE llegado
antes en la lista sobrevivía sobre un CRITICO llegado después. Menor
sobrevive antes, con tres niveles — CRITICO=0, IMPORTANTE=1, ordinario=2 —,
el mismo orden que `aplicar_g12` ya usaba
(`src/sirius/domain/staged_engine_gates.py:333`, `ORDEN_DE_CRITICIDAD`).

`ContextBuilder._apply_relevance_filter`
(`src/sirius/application/context.py`) gana dos funciones privadas de
módulo: `_is_protected_by_criticality(candidate) -> candidate.item.criticality
is not None`, que pasa como `is_protected` a la llamada de
`rescue_max_criticality_candidates` (RF-25/RF-26); y
`_criticality_protection_rank(candidate) -> int`, que pasa como
`protection_rank` a la llamada de `truncate_to_hard_limit` (G12), con
CRITICO=0, IMPORTANTE=1 y ordinario=2. El camino CERRADO no cambia: sigue
comparando `category is None or category == self._max_criticality_category`
inline, sin pasar por ninguna de las dos funciones de dominio. La
protección incondicional de `category is None` en el camino ABIERTO
tampoco cambia. `_MAX_CRITICALITY_CATEGORY`
(`composition_root.py:164`) se conserva sin modificar; su docstring pasa a
decir que solo gobierna ya el camino cerrado.

## Comprobación que la sostiene

Comandos ejecutados tras completar la implementación (predicado
`is_protected` en `rescue_max_criticality_candidates`, `protection_rank` en
`truncate_to_hard_limit`, `_is_protected_by_criticality` y
`_criticality_protection_rank` en `ContextBuilder`, camino cerrado intacto),
en este orden — los pasos 1 a 4 corresponden a la ronda 1 de esta revisión
(antes de que `protection_rank` sustituyera a `is_protected` en G12); el
paso 5 se repitió al completar la ronda 2 (CODEX-001) y refleja ya esa
corrección:

1. Pruebas nuevas vistas fallar antes del cambio (ADR-001):
   `uv run pytest tests/unit/test_relevance_domain.py -q` contra el código
   de antes de este encargo → `11 failed, 60 passed`, las 11 con
   `TypeError: truncate_to_hard_limit()`/`rescue_max_criticality_candidates()
   got an unexpected keyword argument 'is_protected'`. Las de integración
   preexistentes que este encargo reescribe con criticidad
   (`test_rf25_rescues_a_max_criticality_candidate_the_filter_discarded`,
   `test_g12_hard_limit_exclusion_survives_the_real_context_builder_composition`)
   fallaban tras el cambio de dominio y antes de actualizar sus dobles:
   `assert {1} == {1, 2}` (no rescatado) — confirmando que, sin el
   cableado nuevo de `ContextBuilder`, el rescate sigue mirando `category`.
2. Tras completar la implementación:
   `uv run pytest tests/unit/test_relevance_domain.py
   tests/integration/test_context_builder.py -q` → `105 passed`.
3. `uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q -s`
   → fila del paquete completo:
   `aciertos_exactos=7/47 elementos_de_mas=290 omisiones_criticas=3
   cobertura=68/81 (84.0%)` — **idéntica a M19a**, tal como predecía el
   criterio de parada (sin Ollama, el doble de filtro nunca descarta, así
   que RF-25/RF-26 no tiene nada que rescatar y el resultado no puede
   cambiar). `27 passed, 1 skipped, 1 xfailed`.
4. `uv run python scripts/medir_variantes_de_criticidad.py` →
   `hoy=7/47,290,3,68/81` — `hoy` = 3 `NO_ENTRO`, idéntico a M19a, como
   predecía el criterio de parada.
5. `uv run ruff format --check .` → `587 files already formatted`.
   `uv run ruff check .` → `All checks passed!`.
   `uv run mypy src tests` → `Success: no issues found in 555 source files`.
   `uv run pytest -q` (suite completa) → `4570 passed, 15 skipped, 2 xfailed`
   en 445 s — cifra tras la corrección de la ronda 2 (CODEX-001), que añadió
   `protection_rank` a G12 y su prueba de regresión
   `test_truncate_to_hard_limit_prioritises_critico_over_importante_even_when_importante_arrives_first`
   (una prueba más que la ronda 1, que había cerrado con `4569 passed`).
   Ningún fallo, ninguna prueba debilitada u omitida. `git diff --check` →
   limpio (sin salida, código de salida 0).
6. Prueba por mutación (ADR-001), en dos niveles:
   - Dominio: `test_rf25_rescue_mutation_excluding_importante_is_caught_by_the_importante_test`
     (`tests/unit/test_relevance_domain.py`) construye el mismo montaje que
     `test_rf25_rescues_a_discarded_importante_when_the_filter_kept_something`
     con un predicado estrechado a `criticality is Criticality.CRITICO` y
     confirma que ya no rescata (`rescued == ()`), mientras el predicado real
     (`_is_not_ordinary`) sí rescata en la prueba hermana — ambas en el mismo
     `pytest` verde de arriba.
   - Cableado real: se sustituyó temporalmente
     `ContextBuilder._is_protected_by_criticality` por
     `candidate.item.criticality is Criticality.CRITICO` (excluyendo
     IMPORTANTE) en `src/sirius/application/context.py` y se ejecutó
     `uv run pytest tests/integration/test_context_builder.py -q -k
     "importante or critico or rf25"`: **la prueba del IMPORTANTE rescatado
     falla** (`assert {1} == {1, 2}`, no rescatado) mientras las tres
     pruebas del CRITICO siguen en verde — exactamente la asimetría que
     demuestra que la protección alcanza a los dos niveles, no solo a uno.
     Revertida la mutación, las cuatro vuelven a pasar
     (`4 passed` con el mismo comando). Las dos pruebas del CRITICO
     (`test_rf25_rescues_a_max_criticality_candidate_the_filter_discarded`,
     `test_rf25_rescues_a_discarded_critico_of_a_non_max_criticality_category_when_gate_is_open`)
     y la nueva del IMPORTANTE
     (`test_rf25_rescues_a_discarded_importante_candidate_the_filter_discarded`)
     asignan a su vez una categoría ordinaria no nula (`"otros"`) al
     candidato descartado, precisamente para que la protección incondicional
     de `category is None` (D7 punto 2, sin tocar por este encargo) no
     pudiera explicar el rescate por sí sola y la mutación quedara aislada a
     la señal de criticidad — la primera versión de estas pruebas, sin
     categoría, no habría detectado la mutación (se comprobó: con esa
     versión, la del IMPORTANTE también pasaba bajo la mutación, por la
     protección incondicional).

## Consecuencias

- Con la puerta ABIERTA, un CRITICO o IMPORTANTE de cualquier categoría
  (no solo `"salud"`) que el filtro de relevancia descarte se rescata si el
  filtro conservó algo más para la misma consulta (RF-25), y se prioriza
  sobre lo ordinario al truncar por el límite duro de G12.
- Con la puerta CERRADA, el comportamiento de hoy no cambia: mismo candado,
  misma constante, mismas pruebas.
- `_MAX_CRITICALITY_CATEGORY` deja de tener ningún efecto en el camino
  abierto; solo sigue gobernando el candado del camino cerrado y D7.

## Alternativas descartadas y por qué

Ver «Opciones consideradas» arriba.
