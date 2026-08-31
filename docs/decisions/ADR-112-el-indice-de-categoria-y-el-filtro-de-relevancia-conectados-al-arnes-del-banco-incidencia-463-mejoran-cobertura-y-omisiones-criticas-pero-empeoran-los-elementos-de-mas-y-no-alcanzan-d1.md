# ADR-112 — El índice de categoría y el filtro de relevancia, conectados al arnés del banco (incidencia #463), mejoran cobertura y omisiones críticas pero empeoran los elementos de más y no alcanzan D1

- Estado: PROPUESTO
- Fecha: 2026-08-30
- Aprobación: fusión de la PR por el propietario — este ADR documenta el
  diagnóstico que la propia incidencia #463 pide si, tras conectar el índice
  de categoría y el filtro de relevancia al arnés, la cifra sigue por debajo
  del suelo D1.

## Contexto y problema

ADR-111 (incidencia #461) midió el motor por etapas portado con la petición
por caso ya idéntica a la del laboratorio (modo, propósito, permiso,
cardinalidad y límite por consulta), pero **sin** índice de categoría (M9,
SIRIUS-ARQ-0.2 §6.2) ni filtro de relevancia (M10, §6.3): 23/47, 90 elementos
de más, 10 omisiones críticas, cobertura 63/81 (77.8%). Su diagnóstico, con
cita de fichero y línea: el 29/47 que la Definición de Producto registra
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:63-74`) es
el resultado conjunto del motor de búsqueda **con** el índice de categoría
**y** el filtro de relevancia con modelo local vía Ollama — ninguna de las dos
piezas estaba conectada al arnés del banco todavía, aunque ambas ya existen
como código de producto en `main` (M8 — incidencia #448/PR #448 —, M9 —
incidencia #449/450 — y M10 — incidencia #452 —, las tres detrás de la puerta
`category_matching_enabled`, D7 punto 6, cerrada por defecto).

La incidencia #463 autoriza exactamente esa conexión: alimentar las
categorías canónicas de cada elemento desde el propio corpus congelado y
activar la señal `category_match`/vocabulario en el camino del arnés (solo en
el arnés: el producto real sigue detrás de la puerta D7 punto 6, sin
cambios); y portar como fixture del arnés las respuestas congeladas de la
corrida que produjo las cifras de D1, construyendo un doble determinista del
filtro que las reproduce (misma decisión por elemento que aquella corrida),
aplicado con el mismo candado de M10.

**Las piezas conectadas**:

- `tests/acceptance/staged_engine_category_and_relevance.py` — módulo nuevo
  del arnés, con:
  - `VOCABULARIO_DE_CATEGORIA`: portado sin modificar de
    `experiments/adr002/lateral/categoria.py:72-78` (`VOCABULARIO`, rama
    `evidence/adr001-spikes`) — las cinco palabras con las que alguien
    pediría la categoría que el laboratorio deriva de la criticidad del
    canon: `esencial`, `restriccion`, `critica`, `obligatoria`,
    `imprescindible`.
  - `categoria_del_item`: replica `identidades_con_categoria`
    (`experiments/adr002/lateral/categoria.py:99-113`) — todo item cuya
    criticidad aplicada no sea `None` (el fixture del banco nunca declara el
    nivel `ORDINARIO` explícito) entra en la única categoría de este arnés,
    `CATEGORIA_DE_MAXIMA_CRITICIDAD = "restriccion"`.
  - `indice_de_categoria`: la ampliación de M9 (§6.2) sobre lo que el motor
    no admitió, reutilizando **sin modificar**
    `sirius.domain.relevance.category_matches_query` — la misma señal ya
    aprobada, nunca reimplementada.
  - `filtro_congelado_conserva`: el doble determinista del filtro de
    relevancia, que reproduce, elemento a elemento, el veredicto de la
    corrida congelada portada en
    `tests/acceptance/fixtures/relevance_filter_frozen_run.json` (de
    `resultado_modelo_local_v0.7.json`, fila "4. filtro con regla, con
    categoria", commit `8ff535b91dc6a7a2c42eb886699ebdefd902e4fd` de
    `evidence/adr001-spikes` — el mismo corpus que el fixture del banco, sin
    diferencias byte a byte comprobadas contra el commit
    `dfdcdaff04dcba10939cc0b0569c55b6a636296f` que ya citaba su procedencia).
    Falla abierto para cualquier identidad o caso que la corrida congelada
    nunca examinó.
  - `aplicar_candado`: la misma unión de tres conjuntos que
    `ContextBuilder._apply_relevance_filter`
    (`src/sirius/application/context.py:239-258`, M10) — lo que el filtro
    conservó, la categoría de máxima criticidad, y sin categoría todavía.
- `tests/acceptance/fixtures/relevance_filter_frozen_run.json` — el veredicto
  crudo del modelo, verbatim, por caso e identidad, con su procedencia citada
  en el propio fichero.
- `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`
  (`_ejecutar_banco_motor_portado`) — cableado para aplicar, tras lo que el
  motor admite, el índice de categoría y después el filtro con su candado,
  en ese orden (mismo orden que `ContextBuilder._rank_related_knowledge`).

**No se porta** la fila "5. con siembra en contexto" de
`resultado_modelo_local_v0.7.json`, que es la que efectivamente reproduce
29/47, 21, 1, 63/81 (idéntico a D1). Esa fila añade una siembra de las
críticas del ámbito cuando la petición declara que ensambla contexto
(`experiments/adr002/lateral/categoria.py:_pide_contexto`), un mecanismo que
**no** forma parte del diseño aprobado de `category_match`
(SIRIUS-ARQ-0.2 §6.2): esa sección compara únicamente el texto de la consulta
contra el vocabulario cerrado, nunca el propósito de la petición. Añadirlo
habría sido ampliar el diseño ya aprobado por iniciativa propia de esta
incidencia — justo lo que `CLAUDE.md` prohíbe.

**Resultado medido**,
`uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q -s`:

| métrica | petición por caso (ADR-111) | + índice de categoría y filtro (este ADR) | objetivo D1/D2 |
|---|---|---|---|
| aciertos_exactos | 23/47 | **23/47** (sin cambio) | ≥ 29/47 |
| elementos_de_mas | 90 | **108** (empeora) | ≤ 21 |
| omisiones_criticas | 10 | **9** (mejora) | ≤ 1 |
| cobertura | 63/81 (77.8%) | **64/81 (79.0%)** (mejora) | ≥ 63/81 |

Dos de las cuatro métricas mejoran (omisiones críticas y cobertura), una
empeora (elementos de más) y una queda igual (aciertos exactos). Ninguna
alcanza el suelo de D1. La cobertura sí supera el suelo provisional de D2
(64/81 > 63/81), como ya ocurría con ADR-111.

## Diagnóstico: por qué las dos piezas, ya conectadas, no cierran la brecha

**El índice de categoría solo puede activarse en un caso de los cinco que
debería alcanzar.** `category_matches_query`
(`src/sirius/domain/relevance.py:142-171`) exige que la consulta active
**exactamente un** término del vocabulario cerrado —"una consulta que activa
más de una categoría a la vez es ambigua y no cuenta como coincidencia"
(`test_category_matches_query_is_false_when_the_query_activates_more_than_one_category`,
`tests/unit/test_relevance_domain.py`), diseño ya aprobado en la PR #450
(M9), no algo que esta incidencia pueda tocar. De las cinco consultas del
banco que contienen alguna palabra del vocabulario (`B04-CA-02`, `26`, `31`,
`38`, `44`), cuatro contienen `"esencial"` y `"restriccion"` a la vez y quedan
sin activación por diseño; solo `B04-CA-02` ("¿Qué restricciones de
transporte tengo?") activa un único término y puede beneficiarse de la señal
(`test_solo_una_consulta_del_banco_activa_el_indice_de_categoria_sin_ambiguedad`,
`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`). El laboratorio no
tenía esta restricción: indexaba las cinco palabras del vocabulario juntas
sobre una tabla FTS5 lateral (`experiments/adr002/lateral/categoria.py`) y
cualquier coincidencia con cualquiera de ellas contaba — de ahí que, en el
laboratorio, la categoría por sí sola bajara las omisiones críticas de 11 a 5
(ADR-111, sección «Contexto y problema»). Aquí, restringida a una sola consulta sin
ambigüedad, el índice de categoría **sí** amplía el conjunto admitido —de ahí
que omisiones críticas baje de 10 a 9 y cobertura suba de 63/81 a 64/81— pero
mucho menos que en el laboratorio, y con el coste de contaminación que
`elementos_de_mas` = 108 registra (`indice_de_categoria` no filtra por
ámbito, igual que la referencia ya aprobada
`RankRelevantKnowledgeUseCase._rank_via_staged_engine`'s `solo_por_categoria`,
`src/sirius/application/rank_relevant_knowledge.py:243-280`).

**El candado de M10 protege el 100 % de los candidatos de este banco, así
que el filtro de relevancia nunca descarta nada.** El candado
(`ContextBuilder._apply_relevance_filter`,
`src/sirius/application/context.py:239-258`, reproducido por
`aplicar_candado`) protege la unión de tres conjuntos: lo que el filtro
conservó, todo candidato de la categoría de máxima criticidad, y todo
candidato sin categoría todavía. Este banco solo tiene dos estados de
categoría posibles —`"restriccion"` (la única categoría de máxima
criticidad que el arnés deriva) o `None` (todo lo demás)—, así que la unión
cubre siempre el conjunto completo de candidatos
(`test_el_candado_protege_todo_candidato_de_este_banco`). El laboratorio no
tenía este candado: su propio candado interno
(`experiments/adr002/modelo_local/filtro.py:filtrar`, "si el modelo se queda
con algunas, no puede tirar una crítica") protege únicamente los elementos
que el canon marca como críticos, no todo lo sin categoría — un candado
distinto, con un propósito distinto (M10 protege lo *no clasificado todavía*
como salvaguarda de un etiquetado en curso; el laboratorio protege lo
*conocido como crítico*). Sobre un banco con una sola categoría no ordinaria,
la fórmula ya aprobada de M10 no dejaba ningún candidato expuesto al
veredicto del modelo: todo el movimiento medido en este ADR lo produce el
índice de categoría por sí solo, nunca el filtro.

Ninguna de las dos piezas es un defecto de esta incidencia ni de su
implementación: ambas son la lectura literal de diseño ya aprobado
(`category_matches_query`'s regla de activación única, PR #450; el candado de
`ContextBuilder`, PR #452) aplicado sobre un banco que, a diferencia del
canon con muchas categorías temáticas que D7 imagina para producción, solo
declara una.

## Criterio de parada (escrito ANTES de decidir)

Antes de medir tras conectar el índice de categoría y el filtro de
relevancia: si la cifra de aciertos exactos quedara por debajo de 29/47 (o
cualquiera de las otras tres por debajo de su suelo D1) con las dos piezas ya
conectadas exactamente como las aprueban §6.2/§6.3 (sin ampliar su diseño por
iniciativa propia, en particular sin portar la siembra en contexto que la
fila 5 de la corrida congelada usa y que §6.2 no describe), no forzaría la
aserción dura de D1 en la prueba del banco, no debilitaría ninguna cota de no
regresión por debajo de lo medido, y compararía la composición exacta de la
brecha citando fichero y línea de la causa estructural, dejando la decisión
al propietario. Ocurrió exactamente eso: 23/47 (sin cambio), 108 elementos de
más (empeora), 9 omisiones críticas (mejora), 64/81 cobertura (mejora);
diagnóstico completo de por qué, con cita de fichero y línea, en la sección
anterior.

## Opciones consideradas

1. **Portar también la siembra en contexto del laboratorio
   (`_pide_contexto`) para alcanzar 29/47** — descartada: ese mecanismo no
   forma parte del diseño ya aprobado de `category_match` (§6.2, que compara
   solo el texto de la consulta, nunca el propósito de la petición).
   Añadirlo habría ampliado el diseño aprobado por iniciativa propia de esta
   incidencia, justo lo que `CLAUDE.md` prohíbe ("no rediseñes Sirius por
   iniciativa propia") y lo que el criterio de parada de ADR-111 ya
   descartó para la petición por caso.
2. **Relajar la regla de activación única de `category_matches_query` o el
   candado de M10 para que el filtro tenga efecto sobre este banco** —
   descartada: ambas son diseño ya aprobado (PR #450, PR #452), fuera del
   alcance permitido de esta incidencia, que autoriza *conectar* las piezas
   al arnés, no *modificarlas*.
3. **Afirmar el suelo D1 igualmente, o debilitar las cotas de no regresión
   por debajo de lo medido** — descartada explícitamente por la incidencia
   ("no debilites ni falsees nada") y por `CLAUDE.md` (disciplina de
   evidencia).
4. **Conectar exactamente las dos piezas aprobadas, medir, actualizar las
   cotas de no regresión a la cifra medida (23/47, ≤108, ≤9, ≥64/81), y
   documentar el diagnóstico con cita de fichero y línea** — elegida. El
   objetivo aprobado de esta incidencia es conectar el índice de categoría y
   el filtro de relevancia al arnés y medir; el resultado (mejora en
   cobertura y omisiones críticas, empeora en elementos de más, aciertos
   exactos sin cambio) es la medición honesta de esa conexión, y el
   diagnóstico deja localizado, con fichero y línea, por qué las dos piezas
   ya aprobadas no reproducen el 29/47 del laboratorio sobre este banco.

## Decisión

Opción 4. El índice de categoría y el filtro de relevancia (con su candado)
quedan conectados y en uso en el arnés del banco
(`_ejecutar_banco_motor_portado`, vía
`tests.acceptance.staged_engine_category_and_relevance`); el camino real del
producto no cambia (sigue detrás de `category_matching_enabled`, D7 punto 6,
como ya fijaron ADR-109/110/111). Las cotas de no regresión de la prueba del
motor portado se actualizan a la cifra medida en este ADR (aciertos_exactos
≥23, elementos_de_mas ≤108, omisiones_criticas ≤9, elementos_hallados ≥64);
el suelo D1 (≥29/47, ≤21, ≤1) **no** queda afirmado como aserción dura, por
la misma razón que ADR-109/110/111: afirmarlo dejaría `uv run pytest` en
rojo, y debilitar cualquier cota por debajo de lo medido falsearía la prueba.

Decisión que falta y que no corresponde a esta incidencia: si el propietario
quiere ordenar, como encargo aparte, ampliar el diseño aprobado de
`category_match` para que una consulta con varios términos del vocabulario
cuente como coincidencia (reabriendo §6.2), o registrar un candado más
estrecho que el de M10 para el uso de este banco (reabriendo §6.3), o portar
la siembra en contexto del laboratorio como una pieza nueva de diseño — o si
prefiere dejar D1 sin alcanzar por esta vía y esperar a que el propio
etiquetado de categoría por Ollama (M8, ya construido) produzca, contra
`Memory`/`Decision` reales, un vocabulario más rico del que este banco
congelado no puede tener evidencia por sí solo.

## Comprobación que la sostiene

- `uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q -s`:
  imprime `aciertos_exactos=23/47 elementos_de_mas=90 omisiones_criticas=10
  cobertura=63/81 (77.8%)` para la petición por caso sin las dos piezas
  (ADR-111, sin cambios) y `aciertos_exactos=23/47 elementos_de_mas=108
  omisiones_criticas=9 cobertura=64/81 (79.0%)` con el índice de categoría y
  el filtro de relevancia conectados (este ADR).
- `test_solo_una_consulta_del_banco_activa_el_indice_de_categoria_sin_ambiguedad`
  fija, contra el propio fixture del banco, que de las cinco consultas que
  contienen alguna palabra del vocabulario congelado solo una
  (`B04-CA-02`) activa un único término; las otras cuatro
  (`B04-CA-26/31/38/44`) activan dos a la vez y quedan sin señal por la regla
  de activación única de `category_matches_query`
  (`src/sirius/domain/relevance.py:142-171`), confirmada además contra
  `tests/unit/test_relevance_domain.py::
  test_category_matches_query_is_false_when_the_query_activates_more_than_one_category`.
- `test_el_candado_protege_todo_candidato_de_este_banco` fija, contra el
  propio fixture del banco, que `aplicar_candado` (misma fórmula que
  `ContextBuilder._apply_relevance_filter`,
  `src/sirius/application/context.py:239-258`) protege el 100 % de los
  candidatos incluso frente a un filtro que no conservara nada, porque este
  banco solo declara dos estados de categoría posibles.
- `test_el_doble_del_filtro_de_relevancia_reproduce_la_corrida_congelada`
  verifica, contra
  `tests/acceptance/fixtures/relevance_filter_frozen_run.json`, que
  `filtro_congelado_conserva` reproduce, para cada identidad que la corrida
  congelada examinó en cada uno de los 47 casos, la misma decisión que esa
  corrida — la garantía de fidelidad que la incidencia #463 pide.
- Comparación byte a byte (`git diff`) de
  `experiments/adr002/benchmark/cases_v0_5.json`,
  `references_v0_5.json`, `conformance_corpus_v0_6.json`,
  `property_keys_v0_2.json` y `applied_criticality_v0_1.json` entre los
  commits `8ff535b91dc6a7a2c42eb886699ebdefd902e4fd` (el de
  `resultado_modelo_local_v0.7.json`) y
  `dfdcdaff04dcba10939cc0b0569c55b6a636296f` (el que ya citaba la
  procedencia del fixture del banco) en `evidence/adr001-spikes`: sin
  diferencias — el corpus que produjo la corrida congelada es exactamente el
  mismo que porta este fixture.
- Lectura de `experiments/adr002/benchmark/cases_v0_5.json` (`nivel_1[].
  identificador_canonico`) y `experiments/adr002/projection/contracts.py`
  (`identidad_canonica`, `MEM-007 -> MEMORIA:7`): confirman el mapeo
  `N1-NN -> B04-CA-NN` y `MEMORIA:n/DECISION:n -> MEM-NNN/DEC-NNN` usado para
  portar `relevance_filter_frozen_run.json`, verificado con un guion Python
  que reconcilió los 47 casos del banco contra los 50 de la corrida congelada
  sin ninguna identidad sin resolver.
- `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src
  tests`, `uv run pytest`, `git diff --check`: los cinco en verde — ver PR
  para el resultado completo (4300 pruebas superadas, 10 saltadas, ninguna
  nueva salvo el modo opcional contra Ollama real).

## Consecuencias

- Positivas: el índice de categoría y el filtro de relevancia (con su
  candado) quedan conectados y en uso en el arnés del banco, citando su
  origen, sin modificar ninguna de las dos piezas ya aprobadas ni la puerta
  que las cierra en producción. Dos de las cuatro métricas mejoran de forma
  real (omisiones críticas 10→9, cobertura 63/81→64/81, superando el suelo
  provisional de D2), y el diagnóstico deja localizado, con fichero y línea,
  exactamente por qué las dos piezas ya aprobadas no reproducen el 29/47 del
  laboratorio: la regla de activación única de `category_matches_query`
  limita el índice de categoría a un caso de cinco posibles en este banco, y
  el candado de M10 protege el 100 % de los candidatos porque el banco solo
  declara una categoría no ordinaria.
- Negativas/riesgos: D1 sigue sin poder declararse cumplido (23/47 < 29/47) y
  elementos_de_mas empeora frente a ADR-111 (90 → 108); PA-0.2-REC-01 sigue
  sin poder declararse superada por esta vía. El filtro de relevancia, tal
  como está aprobado y conectado, no aporta ninguna reducción de
  contaminación sobre este banco concreto — su efecto solo sería medible
  sobre un canon con más de una categoría no ordinaria, que este banco
  congelado no tiene.

## Alternativas descartadas y por qué

Ver «Opciones consideradas» arriba: la opción 1 habría ampliado el diseño ya
aprobado de `category_match` por iniciativa propia; la opción 2 habría
modificado diseño ya aprobado fuera del alcance permitido de esta incidencia;
la opción 3 habría falseado la prueba.
