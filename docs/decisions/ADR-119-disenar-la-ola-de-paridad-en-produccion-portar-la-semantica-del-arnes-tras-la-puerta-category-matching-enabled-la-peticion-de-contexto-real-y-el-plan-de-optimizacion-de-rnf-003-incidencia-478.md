# ADR-119 — Diseñar la ola de paridad en producción: portar la semántica del arnés tras la puerta category_matching_enabled, la petición de contexto real y el plan de optimización de RNF-003 (incidencia #478)

- Estado: PROPUESTO
- Fecha: 2026-08-31
- Aprobación: fusión de la PR por el propietario

## Contexto y problema

M11 (incidencias #471/#473, ADR-117) dejó el circuito de la puerta
`category_matching_enabled` completamente cableado pero con su suelo de
criterio explícitamente NO aprobado: con la puerta abierta, el camino real de
producción (`RankRelevantKnowledgeUseCase`/`ContextBuilder` tal como los
construye `composition_root`) mide **4/47** aciertos exactos y P95
**438,8-496,1 ms** (tres pasadas, este runner) / **718,5-778,2 ms** (otro
runner, comentario del corrector en la incidencia #471), frente al **29/47**,
**≤1** omisión crítica y **63/81** de cobertura que el arnés de examen ya
fusionado (`tests/acceptance/staged_engine_category_and_relevance.py`,
ADR-109..ADR-115) blinda como aserción dura sobre una traducción de laboratorio
que nunca se ejecuta en producción. ADR-117 registró esa brecha como
"decisión de producto de la siguiente ola, del propietario" (su sección
«Estado del hito: decisión», última viñeta) y la codificó como conocimiento
ejecutable: dos pruebas `pytest.mark.xfail(strict=True)` —
`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py::test_el_suelo_del_criterio_de_m11_aciertos_exactos_29_47_en_el_paquete_completo`
y
`tests/integration/test_local_performance.py::test_el_suelo_de_rnf_003_p95_300ms_en_los_tres_escenarios_del_paquete_completo`—
que fallan-como-se-espera hoy y que un XPASS con `strict=True` convertiría en
fallo de suite, obligando a retirar la marca.

El propietario ordena ahora, en la incidencia #478 (31-08-2026, referencia
`sesion-cli`), cerrar esa brecha: «si recuerda 29 cosas de 47 a mí no me
vale… necesito que lo recuerde bien». El objetivo de esa incidencia fija que
el camino real, con la puerta abierta, debe alcanzar las cifras que el arnés
ya blinda (≥29/47 exactos, críticas ≤1, cobertura ≥63/81 — ADR-115), con la
línea de llegada exacta ya escrita como esas dos pruebas `xfail(strict=True)`:
la ola termina cuando pasen y obliguen a retirar la marca.

Este ADR registra la decisión de **diseño** (sin tocar código ni pruebas,
salvo citas desplazadas) que la incidencia #478 exige: qué piezas del arnés
se portan al camino real tras la puerta, qué le pasa a la semántica de puerta
abierta que M9/M10 ya construyeron (`category_matches_query` de activación
única, `src/sirius/domain/relevance.py:142-171`; el candado-unión de M10,
`src/sirius/application/context.py:239-258`), cómo se diseña la petición de
producción que hoy no existe por caso, y el plan de optimización de RNF-003.
El diseño completo, con sus citas de fichero y línea, vive en
`docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md` §11 (esta
incidencia); este ADR es el registro de la decisión, no una copia de ese
diseño.

## Criterio de parada (escrito ANTES de decidir)

Fijado antes de leer ADR-109..ADR-117 con intención de diseñar nada:

1. Si la causa medida de la brecha (4/47 frente a 29/47) resulta ser un
   defecto de implementación reproducible por una corrección puntual —no una
   ausencia estructural de piezas enteras—, este ADR no se escribe como
   decisión de sustitución de semántica: se redirige a un `BLOCKED_BY_DECISION`
   señalando el defecto concreto, porque corregir un defecto no es diseñar una
   ampliación.
2. Si cerrar la brecha exige leer o modificar el corpus/`resultado_esperado`
   congelados del banco de 47 casos, o tocar el arnés de examen ya fusionado
   (`tests/acceptance/staged_engine_category_and_relevance.py`) o sus
   aserciones, se para: la incidencia #478 lo prohíbe explícitamente y ADR-117
   ya rechazó esa vía por la misma razón (mezclar qué mide el examen con qué
   mide producción).
3. Si alguna pieza de la petición de producción por defecto (§11.3 de la
   Arquitectura) exige inventar información que una consulta real no tiene
   —un oráculo de "resultados esperados" para `Cardinalidad.EXACTA`, por
   ejemplo—, esa pieza se nombra y se cuantifica como brecha no cerrable con
   la información disponible, nunca se rellena con un valor inventado para
   maquillar una métrica.
4. Ninguna cifra de este ADR es una medición nueva: son las ya publicadas por
   ADR-109..ADR-117 y por la comprobación estática de las citas de código
   vigentes en `main` a fecha de esta incidencia. Si una cifra citada no
   coincide con lo que el fichero real dice en esa línea, se para y se corrige
   la cita, nunca se ajusta el fichero para que coincida con la cifra
   recordada.

## Opciones consideradas

Para la semántica de puerta abierta (activación de categoría e integridad de
críticas):

- (a) Dejar `category_matches_query` (activación única) y el candado-unión de
  M10 como el diseño único, también con la puerta abierta, y aceptar que el
  suelo D1 solo se alcanza en el arnés, nunca en producción.
- (b) Sustituir, **solo con la puerta abierta**, la activación única y el
  candado-unión por las piezas que ADR-113/114/115 ya midieron necesarias y
  suficientes en el arnés (categoría buscable de activación múltiple con
  restricción de ámbito, regla de críticas original RF-25/RF-26, siembra en
  contexto, G8/G12 sobre esa ampliación), conservando el diseño (a) intacto
  como estado-cerrado. De estas piezas, la siembra en contexto queda excluida
  del alcance que este ADR decide portar: su precondición documentada (banco
  con solo 2/47 casos que la ejercitan, confirmada «por construcción») sigue
  sin resolverse, así que se aplaza a un encargo posterior — ver «Decisión»
  más abajo.

Para la petición en producción:

- (a) Seguir sin declarar modo/propósito/cardinalidad/límite por consulta real
  (política uniforme actual, `_peticion_ordinaria`,
  `src/sirius/application/rank_relevant_knowledge.py:84-105`).
- (b) Diseñar una petición por defecto que derive ámbito y propósito de
  información que el ensamblado de contexto ya posee honestamente (proyecto
  activo, hecho de que `ContextBuilder` siempre ensambla contexto), dejando
  fuera de alcance lo que solo un oráculo de caso de prueba puede declarar
  (modo/cardinalidad/límite por caso).

Para RNF-003:

- (a) Bajar el `timeout` del filtro de relevancia para forzar el P95 bajo
  300 ms.
- (b) Diagnosticar el coste dominante real (ADR-117 ya descarta el `timeout`
  del filtro) y diseñar un plan de optimización sobre esa causa.

## Decisión

**Semántica de puerta abierta: opción (b), acotada a cuatro de las cinco
piezas.** Se diseña sustituir, exclusiva y únicamente cuando
`category_matching_enabled` es `True`, la activación única y el candado-unión
de M10 por las piezas que ADR-113 (causas 1 y 2 de ADR-112), ADR-114
(restricción de ámbito) y ADR-115 (G8/G12 sobre la ampliación) ya midieron en
el arnés como necesarias para alcanzar 29/47, ≤1 crítica y 63/81 de cobertura
— categoría buscable de activación múltiple con restricción de ámbito, regla
de críticas original RF-25/RF-26, y G8/G12 sobre esa ampliación. La quinta
pieza que ADR-113 también midió, la siembra en contexto, **no** forma parte
de lo que este ADR decide portar: la definición de Producto documenta que
`siembra_de_contexto` se confirma «por construcción» (solo 2 de los 47 casos
del banco la ejercitan, no de forma independiente), y el plan de pruebas fija
como precondición de PA-0.2-REC-01 que el banco se amplíe con casos
independientes que la ejerciten, o que se retire del código, antes de poder
portarla — ninguna de las dos se ha resuelto todavía. Portar
`siembra_de_contexto` queda como decisión de un encargo posterior, condicionado
a que el propietario registre esa precondición como resuelta, igual que D3
(§6.6) deja aplazada la omisión léxica. El detalle de esta exclusión vive en
`docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md` §11.2 y
§11.5 (M15). Se justifica citando el coste medido de no sustituir las cuatro
piezas que sí se deciden: ADR-111 mide 23/47 con la petición por caso ya
portada pero sin estas piezas; ADR-112 mide que, conectadas sin más, el
candado de M10 protege el 100 % del banco (neutraliza el filtro) y
`category_matches_query` de activación única deja fuera 4 de 5 consultas que
activan más de un término del vocabulario a la vez; y el camino real de
producción, con exactamente esas dos piezas del diseño (a) vigentes, mide
**4/47** hoy (ADR-117) — una cifra peor que el 23/47 aislado de ADR-111 porque
además le falta la petición por caso (§11.3). El diseño (a) —activación
única, candado-unión— **se conserva literalmente, sin cambiar una línea de
comportamiento**, como el estado-cerrado: con la puerta cerrada (el valor por
defecto y el único que `composition_root` fija hoy en la construcción con la
que Sirius arranca), el camino de producción sigue siendo exactamente el de
hoy, verificado por las pruebas de identidad ya existentes
(`tests/unit/test_composition_root_relevance_gate.py`,
`tests/integration/test_rank_relevant_knowledge.py`,
`tests/integration/test_context_builder.py`), que esta incidencia no toca ni
debilita.

**Petición en producción: opción (b), con la brecha nombrada donde no se
cierra.** Se diseña una petición por defecto que deriva ámbito del proyecto
activo (información que `RankRelevantKnowledgeUseCase.rank()` ya lee,
`src/sirius/application/rank_relevant_knowledge.py:193-194`) y propósito del
hecho estructural, siempre verdadero, de que la única llamada real a `rank()`
ocurre desde `ContextBuilder._rank_related_knowledge` para ensamblar el
contexto del turno (`src/sirius/application/context.py:221-237`). No se
inventa modo, cardinalidad `EXACTA` ni límite `DURO` por consulta real: ADR-110
mide que la política uniforme sin estas piezas por caso llega a 11/47 y
ADR-111 mide que portar la traducción completa por caso (`peticion_desde_caso`,
`tests/acceptance/staged_engine_case_translation.py:120-153`) sube a 23/47 —una
ganancia de +12/47 que este documento no puede atribuir a un campo aislado
porque ambos ADR midieron el efecto combinado de los cuatro campos a la vez—,
y ese traductor construye `cardinalidad`/`limite`/`objetivos` a partir de un
campo del fixture del banco (`peticion_p2`) que una consulta real de
conversación no tiene ni puede tener sin inventar un oráculo de "cuántos
resultados se esperan". Esta parte de la brecha —cuánto de esos +12/47
depende específicamente de declarar cardinalidad `EXACTA`/límite `DURO` por
caso, en vez de ámbito y propósito reales— queda **cuantificada como no
cerrable con información disponible en producción** en
`docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md` §11.3,
nunca oculta ni rellenada con un valor supuesto.

**RNF-003: opción (b).** El plan de optimización ataca las tres causas
concretas que la lectura del código expone, ninguna es el `timeout` del
filtro (ADR-117 ya lo descarta con el escenario (b), conexión rechazada, en
la misma banda que (a)/(c)): (1) la política `EXHAUSTIVA` de
`_peticion_ordinaria` deshabilita la parada temprana `S1` por diseño
(`src/sirius/domain/staged_engine_stops.py:54-55`), así que `recuperar()`
recorre siempre las cuatro etapas `E1`-`E4`
(`src/sirius/domain/staged_engine.py:292-323`) en cada llamada; (2)
`StagedEnginePort.por_clave_exacta`/`por_prefijo_de_sujeto`
(`src/sirius/adapters/persistence/staged_engine_port.py:223-243`,
`:267-296`) ejecutan dos consultas SQL **por cada clave/prefijo**, dentro de
un bucle Python, en vez de una consulta por lote (el patrón que ADR-008 ya
adoptó para el listado de revisiones vigentes); (3)
`RankRelevantKnowledgeUseCase._rank_via_staged_engine` recorre además, en el
bloque `solo_por_categoria`, la totalidad de `list_current_memories()`/
`list_current_decisions()` (`src/sirius/application/rank_relevant_knowledge.py:243-280`)
— un segundo barrido completo del corpus, además de lo que el motor por
etapas ya recorre por su cuenta. El diseño y el detalle de medición viven en
§11.4 de la Arquitectura Técnica 0.2; este ADR no ejecuta el benchmark (es
diseño, no medición) — la medición queda asignada a un encargo M13+
específico (§11.5).

## Comprobación que la sostiene

Ninguna cifra de este ADR es una medición nueva de esta incidencia (criterio
de parada 4). Verificación estática de cada cita, por lectura directa contra
`main` en el momento de esta incidencia:

- `src/sirius/domain/relevance.py:142-171` (`category_matches_query`,
  activación única: `if len(activated) != 1: return False`).
- `src/sirius/application/context.py:239-258` (`_apply_relevance_filter`, el
  candado-unión de tres conjuntos).
- `src/sirius/application/rank_relevant_knowledge.py:84-105`
  (`_peticion_ordinaria`, política fija), `:132-151` (`rank`, la puerta que
  delega en `_rank_via_staged_engine`), `:153-282` (`_rank_via_staged_engine`),
  `:193-194` (lectura del proyecto activo ya disponible).
- `src/sirius/domain/staged_engine_stops.py:54-55` (`S1` deshabilitada en
  `EXHAUSTIVA`).
- `src/sirius/domain/staged_engine.py:253-333` (`recuperar`, el bucle
  `for etapa in ETAPAS_DE_EXPANSION` sin parada temprana bajo `EXHAUSTIVA`).
- `src/sirius/adapters/persistence/staged_engine_port.py:223-243`,
  `:267-296` (los dos bucles con dos consultas SQL por iteración).
- `tests/acceptance/staged_engine_category_and_relevance.py:317-336`
  (`activa_categoria_buscable`), `:339-356` (`_en_ambito_declarado`),
  `:403-409` (`pide_contexto`), `:412-444` (`siembra_de_contexto`), `:472-513`
  (`aplicar_regla_de_criticas_original`), `:516-540`
  (`vigente_en_tiempo_objetivo`), `:544-574` (`truncar_por_limite_duro`).
- `tests/acceptance/staged_engine_case_translation.py:120-153`
  (`peticion_desde_caso`).
- `docs/decisions/ADR-109-*.md`, `ADR-110-*.md`, `ADR-111-*.md`,
  `ADR-112-*.md`, `ADR-113-*.md`, `ADR-114-*.md`, `ADR-115-*.md`,
  `ADR-117-*.md`: cada cifra citada en este ADR (1/47, 10/47, 11/47, 23/47,
  27/47, 29/47, 4/47, los P95 de ADR-117) reproduce literalmente la tabla o el
  texto de decisión de su propio ADR, sin recalcularla.
- Comprobación de que las dos pruebas `xfail(strict=True)` de M11 existen hoy
  en `main`: `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py:2135`
  (`test_el_suelo_del_criterio_de_m11_aciertos_exactos_29_47_en_el_paquete_completo`)
  y `tests/integration/test_local_performance.py:631`
  (`test_el_suelo_de_rnf_003_p95_300ms_en_los_tres_escenarios_del_paquete_completo`).
- `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src
  tests`, `uv run pytest`, `git diff --check`: ejecutados sobre el estado
  final de esta incidencia (solo documentación nueva; ver el PR para el
  resultado exacto) — no hay código ni prueba nuevos que este ADR deba probar
  por ejecución, porque es una decisión de diseño, no una implementación.

## Consecuencias

- Positivas: el propietario tiene ahora un plan de encargos concreto (M13 en
  adelante, §11.5 de la Arquitectura) con dependencias y criterio de
  aceptación verificable, en vez de una brecha señalada sin camino de cierre;
  la decisión de sustituir semántica tras la puerta queda tomada y justificada
  con las cifras que ya la sostienen, sin repetir la disyuntiva sin resolver
  que estancó dos veces la incidencia #471; la parte de la brecha que ninguna
  petición de producción honesta puede cerrar queda nombrada, no escondida.
- Negativas/riesgos: este documento no implementa nada — las cifras 29/47,
  ≤1 crítica, 63/81 y P95 ≤300 ms sobre el camino real de producción siguen
  sin alcanzarse hasta que M13+ se ejecuten; el plan de optimización de
  RNF-003 (§11.4) es un diagnóstico de causas, no una medición de que
  cerrarlas basta para bajar de ~450 ms a 300 ms — el propio M17 (§11.5)
  existe precisamente para medirlo, y podría no bastar, en cuyo caso M17 lo
  registra igual que ADR-117 registró el incumplimiento de M11, sin
  maquillarlo.

## Alternativas descartadas y por qué

Bajar el `timeout` del filtro de relevancia para forzar RNF-003 se descartó
por la misma razón que ya dio ADR-117: el escenario sin Ollama (fallo abierto
inmediato, sin esperar ningún `timeout`) ya mide en la misma banda que los
otros dos, así que el `timeout` no es la causa dominante y bajarlo maquillaría
la cifra sin cerrarla. Mantener la activación única y el candado-unión también
con la puerta abierta (opción (a) de semántica) se descartó porque perpetuaría
indefinidamente la brecha de 4/47 que esta incidencia existe para cerrar, sin
ninguna vía de diseño alternativa que la incidencia #478 o los ADR previos
propongan. Inventar un valor de cardinalidad/límite por consulta real para
imitar la petición por caso del laboratorio se descartó porque exigiría un
oráculo de "resultados esperados" que ninguna consulta de conversación real
declara — presentar un valor inventado como si derivara de la consulta
falsearía exactamente el tipo de evidencia que esta incidencia exige no
esconder.
