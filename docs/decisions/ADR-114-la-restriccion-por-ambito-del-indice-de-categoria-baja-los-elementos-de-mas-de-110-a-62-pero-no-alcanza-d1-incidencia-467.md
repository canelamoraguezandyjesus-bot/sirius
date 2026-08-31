# ADR-114 — La restricción por ámbito del índice de categoría baja los elementos de más de 110 a 62 pero no alcanza D1 (incidencia #467)

- Estado: PROPUESTO
- Fecha: 2026-08-30
- Aprobación: fusión de la PR por el propietario — este ADR documenta el
  diagnóstico que la propia incidencia #467 pide si, tras restringir por
  ámbito el índice de categoría del arnés, la cifra sigue por debajo del
  suelo D1.

## Contexto y problema

ADR-113 (incidencia #465) cerró las dos causas que ADR-112 había nombrado y
portó la siembra al ensamblar contexto, midiendo 27/47, 110 elementos de
más, 0 omisiones críticas, cobertura 63/81 — y diagnosticó, con cita de
fichero y línea, que la causa dominante de `elementos_de_mas` era que
`indice_de_categoria` no restringía por ámbito: activaba la categoría y
admitía **todas** las identidades de máxima criticidad del banco, sin
importar su proyecto, igual que `RankRelevantKnowledgeUseCase._rank_via_
staged_engine`'s `solo_por_categoria` (`src/sirius/application/
rank_relevant_knowledge.py:243-280`, diseño ya aprobado de producto:
"`category_match` es una señal de M9, no un filtro de alcance"). ADR-113
descartó explícitamente restringir por ámbito en esa incidencia, por
ampliar diseño de producto sin autorización.

La incidencia #467 autoriza exactamente esa restricción, **únicamente en el
camino del arnés** (`tests/acceptance/`), reproduciendo la semántica de
ámbito tal como la aplica el laboratorio en
`experiments/adr002/lateral/categoria.py` (rama `evidence/adr001-spikes`,
solo lectura). Esa fuente no filtra por ámbito dentro de sí misma —indexa
las cinco palabras del vocabulario para toda identidad no ordinaria, sin
mirar el proyecto— sino que declara expresamente que el filtro vive aguas
abajo, en la puerta `G4`:

- `categoria.py:46-49`: "POR QUE ESTO NO ES UN BARRIDO [...] la razon es el
  ambito: `G4` filtra por proyecto antes de entregar, de modo que `N1-31`
  se queda con los criticos **de su ambito** [...] Los doce del expediente
  Gamma son de otro ambito y no salen. El filtro de ambito ya existia; lo
  que faltaba era llegar a la puerta."
- `categoria.py:174-175` (docstring de `_pide_contexto`, la misma pieza que
  sostiene `siembra_de_contexto`, incidencia #465 causa 2): "El ambito hace
  el resto: `G4` filtra por proyecto, de modo que entran las criticas de
  ese proyecto y no las de otro."

Es la **misma** cita y la **misma** fuente que ya sostenía
`siembra_de_contexto`: el laboratorio nunca tuvo dos reglas de ámbito
distintas —una para el índice de categoría y otra para la siembra—, tuvo
una sola, `G4`, aplicada aguas abajo de ambas piezas. Verificado contra la
fuente (no hay ninguna otra mención de ámbito en `categoria.py`), la misma
restricción de ámbito que `siembra_de_contexto` ya aplicaba (incidencia
#465) se aplica aquí también a `indice_de_categoria`, con el mismo criterio:
`_en_ambito_declarado` (`tests/acceptance/staged_engine_category_and_
relevance.py:287-304`) — dentro del proyecto que la petición declara, o de
ámbito global (`PRJ-GLOBAL`), que `G4` admite siempre
(`src/sirius/domain/staged_engine_gates.py:135-152`, la clase
`AMBITO_GLOBAL` de la puerta).

## Criterio de parada (escrito ANTES de decidir)

Antes de medir tras restringir `indice_de_categoria` por ámbito: si la
cifra de aciertos exactos quedara por debajo de 29/47 (o cualquiera de las
otras tres por debajo de su suelo D1) con la restricción conectada
exactamente como la autoriza la incidencia #467 (sin tocar el motor, sin
tocar `aplicar_regla_de_criticas_original`/el fixture congelado, sin
ampliar el banco, sin cambiar la activación de la «categoría buscable»), no
forzaría la aserción dura de D1 sobre las cuatro métricas a la vez, no
debilitaría ninguna cota de no regresión por debajo de lo medido, afirmaría
como aserción dura cada métrica individual que sí alcance su suelo D1/D2
citándolo, y compararía la composición exacta de la brecha restante,
elemento a elemento contra los artefactos congelados, nombrando para cada
elemento sobrante la consulta, el elemento y la etapa del arnés que lo
produce, con fichero y línea, dejando la decisión final al propietario.
Ocurrió exactamente eso: 27/47 (< 29), 62 elementos de más (> 21), 0
omisiones críticas (≤ 1, alcanzado), cobertura 63/81 (≥ 63/81, alcanzado);
diagnóstico completo de por qué, con cita de fichero y línea, en la sección
siguiente.

## Comprobación que la sostiene

`uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q -s`
imprime, para el motor portado con las cuatro piezas conectadas (categoría
buscable con restricción por ámbito, RF-25/RF-26, siembra en contexto):
`aciertos_exactos=27/47 elementos_de_mas=62 omisiones_criticas=0
cobertura=63/81 (77.8%)`.

Medido por configuración (línea base: motor con petición por caso,
ADR-111):

| configuración | aciertos exactos | elementos de más | omisiones críticas | cobertura |
|---|---|---|---|---|
| 0. motor solo (ADR-111) | 23/47 | 90 | 10 | 63/81 |
| 1. + categoría buscable (causa 1, ADR-113) | 20/47 | 153 | 4 | 69/81 |
| 2. + regla RF-25/RF-26 (causa 1, ADR-113) | 27/47 | 102 | 4 | 59/81 |
| 3. + siembra en contexto (causa 2, ADR-113) | 27/47 | 110 | 0 | 63/81 |
| 4. + índice de categoría por ámbito (#467) | **27/47** | **62** | **0** | **63/81** |
| objetivo D1/D2 | ≥ 29/47 | ≤ 21 | ≤ 1 | ≥ 63/81 |

La fila 4 es la medición final: `elementos_de_mas` baja de 110 a 62 (-44%)
al cerrar la causa que ADR-113 diagnosticó; `aciertos_exactos`,
`omisiones_criticas` y `cobertura` no se mueven frente a la fila 3.

**Diagnóstico elemento a elemento de los 62 `elementos_de_mas` restantes**,
contra `tests/acceptance/fixtures/evidence_bank_47_casos.json` y
`relevance_filter_frozen_run.json`, agrupados por la etapa del arnés que
produjo cada uno y por qué `aplicar_regla_de_criticas_original`
(`tests/acceptance/staged_engine_category_and_relevance.py:420-461`) no lo
descarta:

**Grupo A — 39 elementos, el motor por etapas los admite directamente**
(`sirius.domain.staged_engine.recuperar`), antes de que `indice_de_
categoria`/`siembra_de_contexto` intervengan. La restricción de ámbito de
esta incidencia no tiene autoridad sobre lo que el motor ya admitió, y
#467 no autoriza tocar el motor:

| caso | elementos | por qué RF-25/RF-26 no los descarta |
|---|---|---|
| B04-CA-03 | MEM-101..112 (12) | conservados por el doble del modelo (`filtro_congelado_conserva`) — mismo caso y cifra que ADR-113 ya nombraba "motor solo, ajeno a la categoría" |
| B04-CA-35 | MEM-903/906/910/911/912/913/914/915/917/919/921/925/930/931/939 (15) | ídem — mismo caso y cifra que ADR-113 |
| B04-CA-04 | MEM-906, MEM-925 (2) | conservados por el doble del modelo |
| B04-CA-05 | DEC-003 (1) | conservado por el doble del modelo |
| B04-CA-20 | MEM-016 (1) | conservado por el doble del modelo |
| B04-CA-21 | MEM-014 (1) | conservado por el doble del modelo |
| B04-CA-34 | MEM-011 (1) | conservado por el doble del modelo |
| B04-CA-43 | MEM-012 (1) | conservado por el doble del modelo |
| B04-CA-14 | MEM-025 (1) | RF-25: el modelo descartó MEM-025 pero conservó otras del caso, y es de categoría no ordinaria — se rescata |
| B04-CA-20 | DEC-010 (1) | RF-25, igual que la fila anterior |
| B04-CA-25 | DEC-003, DEC-010 (2) | RF-25, igual que la fila anterior |
| B04-CA-30 | DEC-010 (1) | RF-25, igual que la fila anterior |

**Grupo B — 20 elementos, fallo abierto de `aplicar_regla_de_criticas_
original` sobre candidatos que la corrida congelada nunca examinó para ese
caso** (`entraron_al_filtro` no los incluye para ese `caso_id`; mismo
contrato de apertura que `filtro_congelado_conserva`). Las 20 identidades
ya están dentro del ámbito correcto del caso —si no lo estuvieran,
`indice_de_categoria`/`siembra_de_contexto` las habría excluido antes de
llegar aquí—, así que la restricción de ámbito de esta incidencia no puede
cerrar esta causa: falta que la corrida congelada las hubiera examinado, y
#467 no autoriza tocar `aplicar_regla_de_criticas_original` ni el fixture
congelado:

| caso | elemento(s) | etapa que lo admitió |
|---|---|---|
| B04-CA-26 | MEM-112 (1) | `indice_de_categoria` |
| B04-CA-38 | MEM-001, MEM-111, MEM-112 (3) | `indice_de_categoria` |
| B04-CA-44 | MEM-001, MEM-106/107/108/109/110/111/112 (8) | `indice_de_categoria` |
| B04-CA-33 | DEC-010, MEM-001, MEM-014, MEM-016, MEM-025 (5) | `siembra_de_contexto` |
| B04-CA-34 | DEC-010, MEM-001, MEM-025 (3) | `siembra_de_contexto` |

**Grupo C — 3 elementos, la «categoría buscable» activa una consulta y
admite una identidad de su propio ámbito que aun así el resultado esperado
no incluye** (todas vía `indice_de_categoria`, ya dentro de ámbito): el
precio de precisión ya diagnosticado por ADR-112/ADR-113 para la causa 1
(activar por **cualquiera** de las cinco palabras del vocabulario, no por
una sola, a diferencia de `category_matches_query`). No es un problema de
ámbito, así que la restricción de esta incidencia no lo toca:

| caso | elemento | ámbito del caso | proyecto del elemento |
|---|---|---|---|
| B04-CA-02 | MEM-001 | PRJ-MADEIRA | PRJ-GLOBAL (admitido siempre) |
| B04-CA-26 | MEM-001 | PRJ-GAMMA | PRJ-GLOBAL (admitido siempre) |
| B04-CA-31 | MEM-001 | PRJ-ALFA | PRJ-GLOBAL (admitido siempre) |

Suma: 39 + 20 + 3 = 62, exactamente `elementos_de_mas` de la fila 4. Ninguna
de las tres causas es un defecto de esta incidencia ni de su
implementación: las tres son la lectura literal de lo que la incidencia
#467 autoriza (restringir `indice_de_categoria` por ámbito, nada más)
aplicada sobre un arnés cuyas otras piezas —el motor (ADR-111), la corrida
congelada y la activación de la «categoría buscable» (ADR-112/ADR-113)— ya
estaban fuera de su alcance antes de empezar.

`test_indice_de_categoria_respeta_el_ambito_declarado`
(`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`) fija, con un
caso controlado, que `indice_de_categoria` admite identidades del proyecto
declarado y de ámbito global, pero no de otro proyecto — se vio fallar
antes del cambio (`TypeError: indice_de_categoria() got an unexpected
keyword argument 'ambito_declarado'`) y pasa después.

`uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src
tests`, `uv run pytest`, `git diff --check`: los cinco en verde — ver PR
para el resultado completo.

## Opciones consideradas

1. **No restringir por ámbito y dejar la causa medida sin cerrar** —
   descartada: la incidencia #467 autoriza explícitamente cerrarla, y
   dejarla abierta habría desperdiciado una autorización ya concedida sin
   razón técnica.
2. **Restringir por ámbito solo `indice_de_categoria` y no reutilizar el
   criterio de `siembra_de_contexto`** — descartada: habría duplicado la
   misma lógica de ámbito dos veces en el módulo, con riesgo de que
   diverjan con el tiempo; la fuente del laboratorio es la misma cita para
   ambas piezas (una sola puerta `G4` aguas abajo), así que comparten un
   único criterio (`_en_ambito_declarado`).
3. **Ampliar además la activación de la categoría buscable, el motor o la
   corrida congelada para cerrar los grupos B y C** — descartada
   explícitamente: ninguna de esas piezas está en el alcance permitido de
   la incidencia #467 ("el cambio en el código que pide el objetivo, con
   sus pruebas, y nada más"); tocarlas habría sido rediseñar por iniciativa
   propia, lo que `CLAUDE.md` prohíbe.
4. **Afirmar el suelo D1 igualmente sobre las cuatro métricas, o debilitar
   las cotas de no regresión por debajo de lo medido** — descartada
   explícitamente por la incidencia ("terminando en verde sin debilitar ni
   falsear nada") y por la disciplina de evidencia de `CLAUDE.md`.
5. **Conectar la restricción de ámbito exactamente como la autoriza #467,
   medir, actualizar la cota de no regresión de `elementos_de_mas` a la
   cifra medida (62), afirmar como aserción dura las dos métricas que sí
   alcanzan D1/D2 (omisiones críticas, cobertura), y documentar el
   diagnóstico elemento a elemento con cita de fichero y línea** —
   elegida.

## Decisión

Opción 5. `indice_de_categoria` (`tests/acceptance/staged_engine_category_
and_relevance.py:307-348`) recibe `ambito_declarado` y `proyecto_por_
identidad` y restringe la admisión al ámbito declarado más el ámbito
global, con el mismo criterio (`_en_ambito_declarado`,
`:287-304`) que ya usaba `siembra_de_contexto`; el sitio de llamada en
`_ejecutar_banco_motor_portado`
(`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`) pasa esos dos
argumentos. El camino real del producto no cambia: `category_match`/
`solo_por_categoria` siguen sin restricción de ámbito, detrás de la puerta
`category_matching_enabled` (D7 punto 6), diseño ya aprobado que esta
incidencia no toca.

La cota de no regresión `_MAXIMO_ELEMENTOS_DE_MAS_MOTOR` baja de 110 a 62
(la cifra medida, nunca por debajo); `_MINIMO_ACIERTOS_EXACTOS_MOTOR` (27),
`_MAXIMO_OMISIONES_CRITICAS_MOTOR` (0) y `_MINIMO_ELEMENTOS_HALLADOS_MOTOR`
(63) no cambian. `omisiones_criticas ≤ 1` y `cobertura ≥ 63/81` siguen
afirmadas como aserciones duras aparte, citando D1/D2. `aciertos_exactos ≥
29/47` y `elementos_de_mas ≤ 21` **no** quedan afirmados como aserción
dura, por la misma razón que ADR-109/110/111/112/113: afirmarlos dejaría
`uv run pytest` en rojo, y debilitar cualquier cota por debajo de lo medido
falsearía la prueba.

Decisión que falta y que no corresponde a esta incidencia: si el
propietario quiere ordenar, como encargo aparte, ampliar el banco con casos
que aíslen los tres grupos diagnosticados (para poder atacarlos con
autorización explícita), reabrir la corrida congelada del filtro de
relevancia para que examine los candidatos del grupo B, o cambiar la
activación de la «categoría buscable» del grupo C — ninguna de las tres
está autorizada por la incidencia #467.

## Consecuencias

- Positivas: la causa dominante de `elementos_de_mas` que ADR-113
  diagnosticó queda cerrada en el arnés, sin tocar ninguna pieza de
  producto ni ampliar su diseño; `elementos_de_mas` baja un 44% (110 → 62)
  sin mover ninguna otra métrica en sentido negativo. El diagnóstico deja
  localizada, elemento a elemento con fichero y línea, la composición
  exacta de la brecha restante en tres grupos disjuntos que suman
  exactamente 62.
- Negativas/riesgos: D1 sigue sin poder declararse cumplido en las cuatro
  métricas a la vez (27/47 < 29/47; 62 > 21); PA-0.2-REC-01 sigue sin poder
  declararse superada por esta vía. Los grupos B y C exigirían, para
  cerrarse, autorización sobre piezas que #467 deja fuera de alcance (la
  corrida congelada del filtro y la activación de la categoría buscable).

## Alternativas descartadas y por qué

Ver «Opciones consideradas» arriba: la opción 1 habría desperdiciado la
autorización que #467 concede; la opción 2 habría duplicado lógica que
comparte la misma fuente y el mismo criterio; la opción 3 habría ampliado
diseño de producto o piezas del arnés fuera del alcance permitido; la
opción 4 habría falseado la prueba.
