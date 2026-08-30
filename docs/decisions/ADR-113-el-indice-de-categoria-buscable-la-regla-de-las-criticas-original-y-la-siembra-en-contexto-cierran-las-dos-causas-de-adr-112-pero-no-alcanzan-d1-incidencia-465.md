# ADR-113 — El índice de categoría buscable, la regla de las críticas original y la siembra en contexto cierran las dos causas de ADR-112 pero no alcanzan D1 (incidencia #465)

- Estado: PROPUESTO
- Fecha: 2026-08-30
- Aprobación: fusión de la PR por el propietario — este ADR documenta el
  diagnóstico que la propia incidencia #465 pide si, tras cerrar las dos
  causas que ADR-112 dejó nombradas y portar la tercera pieza de la PR #117,
  la cifra sigue por debajo del suelo D1.

## Contexto y problema

ADR-112 (incidencia #463) conectó el índice de categoría (M9, §6.2) y el
filtro de relevancia con el candado de M10 (§6.3) al arnés del banco de 47
casos, con la semántica **estricta** ya aprobada del producto: 23/47, 108
elementos de más, 9 omisiones críticas, cobertura 64/81 (79.0%). Diagnosticó,
con cita de fichero y línea, dos causas por las que esa conexión no alcanza
D1 (aciertos exactos ≥ 29/47, elementos de más ≤ 21, omisiones críticas ≤ 1):

1. **Semántica de categoría del laboratorio.** `category_matches_query`
   (`src/sirius/domain/relevance.py:142-171`) exige que la consulta active
   **exactamente un** término del vocabulario cerrado — diseño ya aprobado de
   M9 (PR #450). De las cinco consultas del banco con alguna palabra del
   vocabulario, cuatro (`B04-CA-26/31/38/44`) activan `"esencial"` y
   `"restriccion"` a la vez y quedan sin señal por esa regla; solo
   `B04-CA-02` activa un único término. El laboratorio no tenía esa
   restricción: indexaba las cinco palabras juntas sobre una tabla FTS5
   lateral (`experiments/adr002/lateral/categoria.py`, rama
   `evidence/adr001-spikes`) como el mismo contenido para toda identidad no
   ordinaria, así que cualquier coincidencia con cualquiera de ellas activaba
   la categoría — la pieza que PR #117 llama **la categoría buscable**
   ("medida, sin modelo... por sí sola lleva las omisiones de 11 a 5. No
   requiere Ollama").
2. **El candado de M10 neutraliza el filtro en este banco.**
   `ContextBuilder._apply_relevance_filter`
   (`src/sirius/application/context.py:239-258`, reproducido por
   `aplicar_candado`) protege la unión de "conservado por el filtro", "todo
   candidato de la categoría de máxima criticidad" y "todo candidato sin
   categoría todavía". Con solo dos estados de categoría posibles en este
   banco (`"restriccion"` o `None`), esa unión cubre el 100% de los
   candidatos: el filtro de relevancia nunca descarta nada, cualquiera que
   sea su veredicto (`test_el_candado_protege_todo_candidato_de_este_banco`).

La incidencia #465 autoriza cerrar ambas causas —**únicamente en el camino
del arnés del banco** (`tests/acceptance/`), sin modificar
`sirius.domain.relevance.category_matches_query` ni ninguna pieza de
producto, que sigue siendo diseño aprobado detrás de la puerta
`category_matching_enabled`— y portar una tercera pieza que ADR-112 dejó
explícitamente fuera de alcance: **la siembra al ensamblar contexto**, la
tercera pieza que PR #117 declara ("se sostiene por diseño, y una prueba deja
ese hecho asertado").

**Las piezas conectadas** (todas en
`tests/acceptance/staged_engine_category_and_relevance.py`):

- `activa_categoria_buscable` — la «categoría buscable» de la PR #117:
  activa si la consulta contiene **cualquiera** de las cinco palabras del
  vocabulario, sin exigir que sea la única. `indice_de_categoria` la usa en
  vez de `category_matches_query`, sin llamarla ni reproducir su
  restricción.
- `aplicar_regla_de_criticas_original` — la regla de las críticas ORIGINAL
  del laboratorio (`experiments/adr002/modelo_local/filtro.py:filtrar`,
  RF-25/RF-26): si el filtro conserva algunas, no puede descartar una
  crítica (se rescata); si declara que ninguna responde, ese veredicto se
  respeta entero, sin rescate. Sustituye a `aplicar_candado` (M10) en
  `_ejecutar_banco_motor_portado`; `aplicar_candado` se conserva en el
  módulo, con su prueba, como la evidencia exacta de la causa 2.
- `pide_contexto`/`siembra_de_contexto` — portadas de
  `experiments/adr002/lateral/categoria.py:_pide_contexto` (rama
  `evidence/adr001-spikes`): si la petición declara, en su propio campo
  `proposito`, que ensambla el contexto de un proyecto, siembra toda
  identidad vigente de categoría no ordinaria dentro del ámbito declarado
  (más las de ámbito global, que `G4` admite siempre, función `_g4` de
  `src/sirius/domain/staged_engine_gates.py`).

**Resultado medido**,
`uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q -s`,
por causa, sobre el motor con petición por caso (ADR-111) como línea base:

| configuración | aciertos exactos | elementos de más | omisiones críticas | cobertura |
|---|---|---|---|---|
| 0. motor solo (ADR-111) | 23/47 | 90 | 10 | 63/81 |
| 1. + categoría buscable (causa 1) | 20/47 | 153 | 4 | 69/81 |
| 2. + regla RF-25/RF-26 (causa 1) | 27/47 | 102 | 4 | 59/81 |
| 3. + siembra en contexto (causa 2) | **27/47** | **110** | **0** | **63/81** |
| objetivo D1/D2 | ≥ 29/47 | ≤ 21 | ≤ 1 | ≥ 63/81 |

La fila 3 es la medición final. Dos de las cuatro métricas alcanzan el suelo
de D1/D2 (`omisiones_criticas` 0 ≤ 1; `cobertura` 63/81 ≥ 63/81, en el
límite exacto); las otras dos no (`aciertos_exactos` 27 < 29;
`elementos_de_mas` 110 > 21).

## Diagnóstico mecánico de la brecha restante, con fichero y línea

**La causa dominante de `elementos_de_mas` es que el índice de categoría no
restringe por ámbito, y la «categoría buscable» amplía de una consulta a
cinco las que lo disparan.** `indice_de_categoria`
(`tests/acceptance/staged_engine_category_and_relevance.py`) reproduce, sin
restricción de ámbito, la misma lógica que la referencia de producto que
imita: `RankRelevantKnowledgeUseCase._rank_via_staged_engine`'s
`solo_por_categoria` (`src/sirius/application/rank_relevant_knowledge.py:
243-280`) — "`category_match` es una señal de M9, no un filtro de alcance".
Con la activación única de ADR-112, solo `B04-CA-02` disparaba esa admisión
sin ámbito; con la «categoría buscable» de la causa 1 la disparan cinco
(`B04-CA-02/26/31/38/44`), multiplicando la contaminación de identidades de
proyectos ajenos a la consulta. Comparación elemento a elemento contra el
fixture (`tests/acceptance/fixtures/evidence_bank_47_casos.json`):
`B04-CA-02` sola aporta 18 elementos de más, `B04-CA-35` 15, `B04-CA-44` y
`B04-CA-31` 14 cada una, `B04-CA-03` 12 (motor solo, sin relación con la
categoría), `B04-CA-38` 9, `B04-CA-26` 8 — la mayoría, identidades de
`MEM-101`..`MEM-112` (expediente Gamma) y del vocabulario de categoría
(`DEC-003`, `DEC-010`, `MEM-001/014/016/025`) que no pertenecen al proyecto
de la consulta.

La regla RF-25/RF-26 (causa 1) sí filtra buena parte de ese ruido —de ahí
que `elementos_de_mas` baje de 153 (fila 1) a 102 (fila 2) al aplicarla—,
pero no lo suficiente para bajar de 21 porque solo actúa sobre lo que la
corrida congelada examinó para cada caso
(`tests/acceptance/fixtures/relevance_filter_frozen_run.json`) y falla
abierto para el resto (`aplicar_regla_de_criticas_original`, mismo contrato
que `filtro_congelado_conserva`): el arnés puede construir, por la propia
diferencia de arquitectura de candidato que ADR-111 ya diagnosticó, un
candidato que la corrida congelada nunca vio para ese caso, y ese candidato
pasa intacto sin que ninguna regla lo examine.

**`aciertos_exactos` sube de 23 a 27 gracias casi enteramente a la regla
RF-25/RF-26** (fila 1→2: 20→27), no a la categoría buscable por sí sola (que
de hecho lo baja de 23 a 20, fila 0→1, porque contamina casos que antes eran
exactos). La siembra en contexto (fila 2→3) no mueve `aciertos_exactos` (se
queda en 27): ni `B04-CA-33` ni `B04-CA-34` —los dos únicos casos que la
siembra puede tocar— llegan a ser un acierto exacto, porque el motor y la
categoría ya les habían admitido, antes de la siembra, identidades que no
pertenecen al resultado esperado (ver detalle: `B04-CA-33` queda con 5
elementos de más, `B04-CA-34` con 4, tras la siembra).

Ninguna de las tres piezas es un defecto de esta incidencia ni de su
implementación: las tres son la lectura literal de lo que la incidencia #465
autoriza portar, aplicadas sobre un arnés cuya arquitectura de candidato
—ya diagnosticada por ADR-111— sigue sin coincidir con la del laboratorio.
Esta incidencia **no** autoriza restringir `indice_de_categoria` por ámbito:
hacerlo ampliaría el diseño ya aprobado de `category_match`/
`solo_por_categoria` por iniciativa propia, justo lo que `CLAUDE.md` prohíbe
("no rediseñes Sirius por iniciativa propia") y lo que el criterio de parada
de esta incidencia excluye explícitamente.

## Criterio de parada (escrito ANTES de decidir)

Antes de medir tras cerrar las dos causas de ADR-112 y portar la siembra en
contexto: si la cifra de aciertos exactos quedara por debajo de 29/47 (o
cualquiera de las otras tres por debajo de su suelo D1) con las tres piezas
conectadas exactamente como las autoriza la incidencia #465 (sin ampliar
ningún diseño de producto por iniciativa propia, en particular sin
restringir `indice_de_categoria` por ámbito ni ampliar el banco), no
forzaría la aserción dura de D1 sobre las cuatro métricas a la vez, no
debilitaría ninguna cota de no regresión por debajo de lo medido, afirmaría
como aserción dura cada métrica individual que sí alcance su suelo D1/D2
citándolo, y compararía la composición exacta de la brecha restante citando
fichero y línea de la causa estructural, dejando la decisión final al
propietario. Ocurrió exactamente eso: 27/47 (< 29), 110 elementos de más
(> 21), 0 omisiones críticas (≤ 1, alcanzado), cobertura 63/81 (≥ 63/81,
alcanzado); diagnóstico completo de por qué, con cita de fichero y línea, en
la sección anterior.

## Opciones consideradas

1. **Restringir `indice_de_categoria` por ámbito para bajar
   `elementos_de_mas`** — descartada: `category_match`/`solo_por_categoria`
   (diseño ya aprobado, PR #450/#457) declaran explícitamente que esa señal
   "no es un filtro de alcance". Restringirla por ámbito en el arnés sería
   ampliar ese diseño por iniciativa propia de esta incidencia, fuera de lo
   que #465 autoriza.
2. **Ampliar el banco con casos independientes de la siembra, o retirarla,
   para resolver la salvedad (a) de la Definición §3.2** — descartada para
   esta incidencia: #465 la deja citada expresamente como "pendiente
   registrada del propietario para la declaración formal de
   PA-0.2-REC-01 — este encargo no la resuelve".
3. **Afirmar el suelo D1 igualmente sobre las cuatro métricas, o debilitar
   las cotas de no regresión por debajo de lo medido** — descartada
   explícitamente por la incidencia ("termina en verde sin debilitar ni
   falsear nada") y por `CLAUDE.md` (disciplina de evidencia).
4. **Conectar exactamente las piezas autorizadas, medir, actualizar las
   cotas de no regresión a la cifra medida (27/47, ≤110, ≤0, ≥63/81),
   afirmar como aserción dura las dos métricas que sí alcanzan D1/D2
   (omisiones críticas, cobertura), y documentar el diagnóstico mecánico con
   cita de fichero y línea** — elegida.

## Decisión

Opción 4. `activa_categoria_buscable`, `aplicar_regla_de_criticas_original` y
`siembra_de_contexto` quedan conectadas y en uso en
`_ejecutar_banco_motor_portado`
(`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`); el camino real
del producto no cambia (sigue detrás de `category_matching_enabled`, D7
punto 6). Las cotas de no regresión de la prueba del motor portado se
actualizan a la cifra medida en este ADR (`_MINIMO_ACIERTOS_EXACTOS_MOTOR`
= 27, `_MAXIMO_ELEMENTOS_DE_MAS_MOTOR` = 110,
`_MAXIMO_OMISIONES_CRITICAS_MOTOR` = 0, `_MINIMO_ELEMENTOS_HALLADOS_MOTOR`
= 63); además, `omisiones_criticas ≤ 1` y `cobertura ≥ 63/81` quedan
afirmadas como aserciones duras aparte, citando D1/D2, porque esta medición
sí las alcanza. `aciertos_exactos ≥ 29/47` y `elementos_de_mas ≤ 21` **no**
quedan afirmados como aserción dura, por la misma razón que ADR-109/110/111/
112: afirmarlos dejaría `uv run pytest` en rojo, y debilitar cualquier cota
por debajo de lo medido falsearía la prueba.

La marca «por construcción» que PR #117 exige para la siembra en contexto
viaja en el docstring de
`test_la_siembra_en_contexto_la_confirman_solo_los_dos_casos_por_
construccion` (`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`) y en
este ADR: el banco solo tiene dos casos (`B04-CA-33`, `B04-CA-34`) con el
propósito que activa la siembra, así que no puede confirmarla de forma
independiente. La salvedad (a) de la Definición §3.2 (ampliar el banco con
casos independientes de la siembra, o retirarla) queda pendiente, registrada
para el propietario, para la declaración formal de PA-0.2-REC-01 — esta
incidencia no la resuelve.

Decisión que falta y que no corresponde a esta incidencia: si el propietario
quiere ordenar, como encargo aparte, restringir `category_match`/
`indice_de_categoria` por ámbito (reabriendo §6.2), ampliar el banco con
casos independientes de la siembra o retirarla (cerrando la salvedad (a) de
la Definición §3.2), o esperar a que el propio etiquetado de categoría por
Ollama (M8) produzca, contra `Memory`/`Decision` reales, un vocabulario más
rico del que este banco congelado no puede tener evidencia por sí solo.

## Comprobación que la sostiene

- `uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q -s`:
  imprime `aciertos_exactos=27/47 elementos_de_mas=110 omisiones_criticas=0
  cobertura=63/81 (77.8%)` para el motor portado con las tres piezas de la
  incidencia #465 conectadas; `aciertos_exactos=10/47 ... cobertura=57/81
  (70.4%)` para M7 (sin cambios, ADR-109).
- `test_las_cinco_consultas_del_banco_activan_la_categoria_buscable_del_
  arnes` fija, contra el propio fixture del banco, que las cinco consultas
  con alguna palabra del vocabulario activan `activa_categoria_buscable`
  (`B04-CA-02/26/31/38/44`), en contraste directo con
  `test_solo_una_consulta_del_banco_activa_category_matches_query_sin_
  ambiguedad`, que fija que solo una (`B04-CA-02`) activa la función de
  producto sin ambigüedad — la misma cita de fichero y línea que ADR-112,
  confirmando que la restricción de producto sigue intacta.
- `test_la_regla_de_criticas_original_si_descarta_a_diferencia_del_candado_
  de_m10`, `test_la_regla_de_criticas_original_rescata_una_critica_
  descartada_por_el_modelo` y
  `test_la_regla_de_criticas_original_falla_abierto_para_lo_no_examinado`
  fijan, con casos controlados contra el fixture congelado, las tres ramas
  de RF-25/RF-26 (respeta ausencia total sin rescate, rescata una crítica
  descartada cuando el modelo sí eligió algunas, falla abierto para lo no
  examinado).
- `test_la_siembra_en_contexto_la_confirman_solo_los_dos_casos_por_
  construccion` fija, contra el propio fixture, que `B04-CA-33` y
  `B04-CA-34` son los únicos dos casos cuyo `peticion_p2.proposito` declara
  que ensambla contexto.
- `test_siembra_de_contexto_respeta_el_ambito_declarado` fija, con un caso
  controlado, que `siembra_de_contexto` admite identidades del proyecto
  declarado y de ámbito global, pero no de otro proyecto.
- Diagnóstico mecánico de `elementos_de_mas`: guion Python ad hoc que separa
  la contribución de cada una de las tres piezas por configuración (tabla de
  la sección «Contexto y problema», reproducible ejecutando
  `_ejecutar_banco_motor_portado` con cada combinación de
  `indice_de_categoria`/`siembra_de_contexto`/`aplicar_regla_de_criticas_
  original` activada o no) y el desglose caso a caso de `elementos_de_mas`
  contra `evidence_bank_47_casos.json` citado en la sección de diagnóstico.
- `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src
  tests`, `uv run pytest`, `git diff --check`: los cinco en verde — ver PR
  para el resultado completo (4307 pruebas superadas, 10 saltadas, ninguna
  nueva salvo el modo opcional contra Ollama real).

## Consecuencias

- Positivas: las dos causas que ADR-112 dejó nombradas quedan cerradas en el
  arnés, sin tocar ninguna pieza de producto ni ampliar su diseño; la
  tercera pieza de la PR #117 (siembra en contexto) queda portada, con su
  estatuto «por construcción» declarado sin ocultarlo, tanto en el docstring
  de la prueba como en este ADR. Dos de las cuatro métricas de D1/D2 quedan
  afirmadas como aserción dura (omisiones críticas ≤ 1, cobertura ≥ 63/81),
  y `aciertos_exactos` mejora de 23/47 a 27/47 frente a ADR-112. El
  diagnóstico deja localizada, con fichero y línea, la causa estructural
  exacta de la brecha restante en `elementos_de_mas`: la falta de
  restricción por ámbito de `category_match`, ya presente antes de esta
  incidencia y ahora más visible porque la categoría buscable la dispara
  cinco veces en vez de una.
- Negativas/riesgos: D1 sigue sin poder declararse cumplido en las cuatro
  métricas a la vez (27/47 < 29/47; 110 > 21); PA-0.2-REC-01 sigue sin poder
  declararse superada por esta vía. `elementos_de_mas` empeora frente a
  ADR-112 (108 → 110) y `elementos_hallados` retrocede de 64/81 a 63/81
  (aunque sigue en el suelo D1/D2) — el precio de que la regla RF-25/RF-26,
  a diferencia del candado de M10, sí descarta candidatos correctos que el
  doble determinista del modelo no conservó para ese caso concreto.

## Alternativas descartadas y por qué

Ver «Opciones consideradas» arriba: la opción 1 habría ampliado diseño ya
aprobado de producto por iniciativa propia; la opción 2 resuelve una
salvedad que la incidencia #465 deja expresamente pendiente para el
propietario; la opción 3 habría falseado la prueba.
