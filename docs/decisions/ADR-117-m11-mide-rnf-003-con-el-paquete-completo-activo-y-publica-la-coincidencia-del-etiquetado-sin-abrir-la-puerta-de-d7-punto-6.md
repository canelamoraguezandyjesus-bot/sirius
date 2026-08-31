# ADR-117 — M11 mide RNF-003 con el paquete completo activo y publica la coincidencia del etiquetado, sin abrir la puerta de D7 punto 6

- Estado: PROPUESTO
- Fecha: 2026-08-31
- Aprobación: fusión de la PR por el propietario

## Contexto y problema

M11 (incidencia #471, WI-20260831-054212, SIRIUS-ARQ-0.2 §6.4/§6.5/§8-M11)
cablea la puerta de activación de D7 punto 6 (`category_matching_enabled`)
en `composition_root` —cerrada por defecto— y, con ella abierta solo dentro
de las pruebas, produce tres piezas de evidencia que el objetivo de la
incidencia exige publicar sin declarar conformidad ni fijar ningún umbral
por su cuenta:

1. El P95 de «construir contexto» con el paquete completo activo (índice de
   categoría + filtro de relevancia con candado), en los tres escenarios que
   §6.4 fija (Ollama disponible, ausente, y aceptando la conexión sin
   responder hasta agotar el `timeout`).
2. Las cuatro métricas de PA-0.2-REC-01 sobre el banco de 47 casos, con la
   puerta abierta y dobles deterministas, ejecutadas contra el camino de
   código real de producción (`RankRelevantKnowledgeUseCase`/
   `ContextBuilder` tal como `composition_root` los construiría) — **nunca**
   contra el arnés de examen ya fusionado (incidencias #457-#469,
   ADR-109..ADR-115), que este encargo no toca.
3. La coincidencia del etiquetado automático de Ollama (D7 punto 6) contra
   las etiquetas canónicas de ADR-116.

Ninguna de las tres cifras autoriza, por sí sola, abrir la puerta en
`settings.json`: eso queda para el propietario, a la vista de estas
medidas, en dos pasos separados de este encargo (§6.3).

## Criterio de parada (escrito ANTES de decidir)

Fijado antes de ejecutar ninguna de las tres mediciones: (1) si el P95 del
paquete completo activo supera los 300 ms de RNF-003 en este runner, se
publica la cifra igual —ADR-007 ya exige no declarar conformidad sin un
orden de magnitud de holgura— y no se afirma como aserción dura, nunca se
ajusta el `timeout` del adaptador para forzarla artificialmente por debajo
del límite si el coste dominante no es el propio `timeout`; (2) si el banco
con la puerta abierta (paquete completo de producción) da cifras distintas
de las del arnés de examen ya fusionado, se publican ambas y se explica la
diferencia citando fichero y línea, sin tocar el arnés de examen ni sus
aserciones, y sin intentar que el paquete completo iguale esa cifra
modificando el pipeline de producción fuera del alcance de esta incidencia;
(3) la cifra real de coincidencia del etiquetado (D7 punto 6) solo se
publica si esta máquina expone un Ollama real; si no lo expone —como es el
caso de este runner, que no está autorizado a instalarlo—, se deja
constancia explícita de que la cifra no se pudo producir aquí, en vez de
simularla o de sustituirla por el resultado del doble determinista de la
suite (que mide el arnés, no la fiabilidad real de Ollama, ver
`test_d7_punto_6_coincidencia_etiquetado.py`).

## Opciones consideradas

Para RNF-003 con el paquete completo activo: (a) afirmar el límite de 300 ms
como aserción dura si la medición lo cumple, con holgura o sin ella; (b)
seguir el mismo patrón de ADR-007 que ya usa este módulo — afirmar solo el
guardarraíl de disparate, y registrar la cifra real como evidencia sin
declarar conformidad. Para el banco con la puerta abierta: (a) modificar el
arnés de examen ya fusionado para que también recorra el paquete completo de
producción; (b) añadir una ejecución nueva, separada, contra el camino de
código real, sin tocar el arnés existente. Para D7 punto 6: (a) fijar un
umbral exigible dentro de este mismo encargo; (b) publicar la cifra —cuando
exista— y dejar el umbral para el propietario, en `STATUS.md`.

## Decisión

**RNF-003: opción (b), mismo patrón de ADR-007.** Medido el 31 de agosto de
2026, mismo conjunto de referencia de ADR-008 (5.000 mensajes, 500
recuerdos, 100 decisiones, 10 proyectos) y misma máquina, tres pasadas del
mismo código, con `timeout_seconds=composition_root._RELEVANCE_FILTER_TIMEOUT_SECONDS`
(50 ms):

| Escenario | P95 (tres pasadas) | Límite | Uso |
|---|---|---|---|
| (a) Ollama disponible dentro del presupuesto | 447,4 / 438,9 / 446,7 ms | 300 ms | 146 a 149 % |
| (b) Ollama ausente (conexión rechazada) | 438,8 / 435,8 / 441,5 ms | 300 ms | 145 a 147 % |
| (c) Ollama acepta la conexión y agota el timeout | 493,8 / 494,0 / 496,1 ms | 300 ms | 165 % |

Tabla completa y su explicación en el docstring del módulo
(`tests/integration/test_local_performance.py`), reproducida por
`test_construir_contexto_con_el_paquete_completo_activo_en_los_tres_escenarios`.
**RNF-003 no se cumple hoy con el paquete completo activo, sobre este
runner de CI** — las tres cifras superan los 300 ms, y el escenario (b)
(conexión rechazada, sin ningún coste de red) está en la misma banda que
(a)/(c), lo que localiza el coste dominante en construir la petición del
motor por etapas y recorrer sus doce puertas (ADR-109) sobre el conjunto de
referencia, no en el transporte HTTP del filtro de relevancia: bajar
`_RELEVANCE_FILTER_TIMEOUT_SECONDS` no habría cerrado esta brecha, así que
no se ha tocado. Se afirma solo el guardarraíl de disparate de ADR-007
(1.500 ms, muy por debajo de las cifras medidas) como aserción dura; el
requisito de 300 ms lo comprueba PA-025 en la máquina real del usuario, no
este runner compartido.

**Banco con la puerta abierta: opción (b), ejecución nueva y separada.**
`test_el_banco_se_ejecuta_contra_el_paquete_completo_de_produccion_como_evidencia_adicional`
(`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`) añade una cuarta
ejecución del banco, contra `RankRelevantKnowledgeUseCase`/`ContextBuilder`
construidos exactamente como `composition_root` los construiría con la
puerta abierta, sin tocar ninguna línea del arnés de examen ni sus
aserciones existentes. Medido:

| | aciertos exactos | elementos de más | omisiones críticas | cobertura |
|---|---|---|---|---|
| Arnés de examen (ADR-109..ADR-115, ya fusionado) | 29/47 | 50 | 0 | 63/81 (77,8 %) |
| Paquete completo de producción (M11, esta incidencia) | 4/47 | 609 | 9 | 59/81 (72,8 %) |

Las cuatro métricas empeoran, de forma sustancial, frente al arnés de
examen. La causa no es un defecto de esta medición ni del arnés de examen:
son dos pipelines distintos, y la diferencia se explica citando fichero y
línea, tal como exige el objetivo de la incidencia:

- El arnés de examen reimplementa una semántica de laboratorio que **no
  existe en el código de producción**: la «categoría buscable» con
  activación múltiple (`staged_engine_category_and_relevance.py:318-333`,
  `activa_categoria_buscable`) — cualquier coincidencia con **cualquiera**
  de las cinco palabras del vocabulario del laboratorio activa la
  categoría para todas las identidades, a diferencia de
  `category_matches_query` real (`src/sirius/domain/relevance.py:142-171`),
  que exige activación única sobre las siete categorías reales—, la regla
  de las críticas original RF-25/RF-26
  (`staged_engine_category_and_relevance.py`, `aplicar_regla_de_criticas_original`),
  la siembra al ensamblar contexto (`siembra_de_contexto`) y la restricción
  por ámbito del índice de categoría (incidencia #467). Ninguna de esas
  cuatro piezas está cableada en
  `RankRelevantKnowledgeUseCase._rank_via_staged_engine`
  (`src/sirius/application/rank_relevant_knowledge.py:153-282`): esa
  función solo amplía sobre `category_matches_query` con activación única y
  sin restricción por ámbito (líneas 201-204, 244-280) — de ahí que
  `elementos_de_mas` suba de 50 a 609: sin restricción por ámbito ni por
  activación única, y sin las dos puertas G8/G12 que la ampliación del
  arnés de examen sí hereda (incidencia #469), el índice de categoría real
  sobre-admite de forma mucho más agresiva.
- `build_staged_engine_port` (`src/sirius/adapters/persistence/
  staged_engine_port.py:341-349`), llamado en esta medición sin
  `ejes_por_identidad` —igual que `composition_root`, nunca con los ejes
  poblados a mano desde el corpus que sí usa el arnés de examen
  (`test_pa_0_2_rec_01_banco_evidencia.py:532-660`, función
  `_ejecutar_banco_motor_portado`)—, entrega todo item real
  con `ejes=SIN_EJES` (documentado en el propio módulo, líneas 24-33): las
  puertas P2 que dependen de esos ejes degradan en vez de evaluar el eje
  real, otra causa de divergencia frente al arnés de examen, que sí los
  puebla.
- `omisiones_criticas` sube de 0 a 9: sin la regla de las críticas original
  ni la siembra en contexto, algunas identidades críticas que el arnés de
  examen rescataba explícitamente ya no se admiten por ningún camino en el
  paquete completo de producción.

Esta comparación no es una regresión de esta incidencia: **ninguna de las
cuatro piezas de la semántica de laboratorio forma parte del alcance de
M8-M11** — el objetivo que las incidencias #463/#465/#467/#469 autorizaron
las confinó explícitamente al arnés de evaluación («únicamente en este
arnés», ver sus propios ADR). Cerrar esa brecha en el código de producción
es una decisión de alcance nueva, fuera de lo que esta incidencia autoriza.

**D7 punto 6: opción (b), publicar cuando exista.** El mecanismo de la
suite (`test_el_arnes_mide_la_coincidencia_de_un_clasificador_con_respuestas_deterministas`)
mide, con un doble determinista, 92/95 (96,8 %) sobre un guion con tres
discrepancias deliberadas — confirma que el arnés cuenta aciertos y fallos
correctamente, no la fiabilidad real de Ollama. El mecanismo real
(`test_medicion_real_de_coincidencia_contra_ollama_local`,
`requires_real_ollama`) se salta en este runner: no hay un Ollama real en
`localhost:11434` y este entorno no está autorizado a instalarlo. **La
cifra real de evidencia que D7 punto 6 exige no se ha podido producir en
esta ejecución** — queda pendiente de que alguien la ejecute a propósito en
una máquina con `ollama serve` corriendo. El umbral exigible se registra en
`docs/evolution/STATUS.md`, sección **D7** (el propietario ya declaró allí,
en el registro del 29 de agosto de 2026: "el umbral exigible lo registra el
propietario a la vista de esa medición — mismo patrón que D2"); esta
incidencia no edita `STATUS.md` ni fija el umbral, solo deja escrito, aquí y
en el docstring de `test_d7_punto_6_coincidencia_etiquetado.py`, dónde y
cómo se registra.

## Comprobación que la sostiene

- `uv run pytest tests/integration/test_local_performance.py -q -k paquete_completo -s`,
  ejecutado tres veces sobre esta máquina: produce las tres filas de la
  tabla de RNF-003 de arriba (ver también el docstring del módulo).
- `uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q -k "paquete_completo_de_produccion or canonicas_se_recalculan" -s`:
  imprime `aciertos_exactos=4/47 elementos_de_mas=609 omisiones_criticas=9
  cobertura=59/81 (72.8%)` para el paquete completo, frente a
  `aciertos_exactos=29/47 elementos_de_mas=50 omisiones_criticas=0
  cobertura=63/81 (77.8%)` del arnés de examen ya fusionado (impreso por
  `test_el_banco_se_ejecuta_contra_el_motor_portado_y_reporta_las_cuatro_metricas`,
  sin tocar esa prueba).
- `uv run pytest tests/acceptance/test_d7_punto_6_coincidencia_etiquetado.py -q -s`:
  1 passed (el doble determinista, 92/95), 1 skipped (`requires_real_ollama`,
  sin Ollama real en este runner).
- `uv run pytest tests/unit/test_composition_root_relevance_gate.py tests/gui/test_settings_ui.py -q`:
  confirma que, con la puerta cerrada (el estado con el que M11 la deja al
  fusionar), `composition_root` construye exactamente lo mismo que hoy, y
  que `_save_configuration()` conserva `category_matching_enabled` tras
  guardar cualquier otro ajuste.
- `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src
  tests`, `uv run pytest` (suite completa): ver el PR de M11 para el
  resultado exacto.

## Consecuencias

- Positivas: la puerta de D7 punto 6 queda completamente cableada —el
  circuito de settings.json hasta `RankRelevantKnowledgeUseCase`/
  `ContextBuilder`— sin abrirla; el propietario tiene ahora, por primera
  vez, la cifra real de RNF-003 con el paquete completo activo y la
  comparación explicada entre el arnés de examen y el código de producción,
  en vez de una promesa de que "se comportará igual".
- Negativas/riesgos: RNF-003 no se cumple hoy con el paquete completo activo
  en este runner de CI, y el paquete completo de producción mide muy por
  debajo del arnés de examen en las cuatro métricas de PA-0.2-REC-01 —
  ninguna de las dos cifras autoriza abrir la puerta en `settings.json` sin
  trabajo adicional (cerrar la brecha de rendimiento del motor por etapas
  bajo carga, o portar al código de producción alguna de las piezas que hoy
  solo vive en el arnés de examen). La cifra real de coincidencia del
  etiquetado (D7 punto 6) sigue sin producirse: el umbral que el propietario
  registre en `STATUS.md` no puede apoyarse todavía en un dato real, solo en
  el mecanismo ya construido y verificado por su doble determinista.

## Alternativas descartadas y por qué

Forzar el P95 de RNF-003 bajo 300 ms bajando `_RELEVANCE_FILTER_TIMEOUT_SECONDS`
se descartó porque el escenario (b) —conexión rechazada, sin esperar nunca
al `timeout`— ya está en la misma banda que (a)/(c): el coste dominante no
es el `timeout` del filtro, así que bajarlo habría maquillado la cifra sin
cerrar la causa real, y esta incidencia prohíbe declarar conformidad sin
holgura (ADR-007). Modificar el arnés de examen ya fusionado para que
recorriera el paquete completo de producción se descartó porque el objetivo
de la incidencia lo prohíbe explícitamente ("sin tocar el arnés del examen
ya fusionado ni sus aserciones") y porque mezclaría dos preguntas distintas
—qué mide el examen y qué mide producción— en una sola ejecución. Simular o
extrapolar la cifra real de D7 punto 6 a partir del doble determinista de la
suite se descartó porque el propio arnés lo advierte por diseño: el doble
mide si el arnés cuenta bien, no si Ollama clasifica bien, y presentar una
como la otra falsearía la evidencia que el propietario necesita para fijar
el umbral.
