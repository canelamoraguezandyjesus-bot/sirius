# ADR-185 — la puerta de la memoria se parte en tres interruptores antes de abrirla

- Estado: PROPUESTO
- Fecha: 2026-09-13
- Aprobación: el propietario, al fusionar la PR de la incidencia #603 (WI-20260913-PUERTA-1)

## Nota de arranque (publicada ANTES del primer commit)

El contrato de esta ronda solo permite un comentario en la incidencia —la URL
de la PR—, así que la nota de arranque que exige ADR-001 se publica aquí, que
es la segunda ubicación que la propia skill `disciplina-evidencia` nombra («la
incidencia si existe; si no, el ADR de la rama»).

1. **¿Dónde vive el problema y dónde va el arreglo?** El problema no es un
   fallo: es que **no se puede observar**. `category_matching_enabled` vive en
   `composition_root.build_conversation_dependencies` y desde ahí enciende
   siete cosas a la vez, así que cuando se abra y la latencia se salga de los
   300 ms de RNF-003 —ya medida entre 438 y 780 ms P95 con el paquete entero—
   no habrá manera de decir cuál de las siete lo hizo. El arreglo va en el
   mismo sitio que el problema, y **puede observarlo**: el cableado es
   exactamente lo que hay que partir, y una prueba que capture los `kwargs`
   que `composition_root` pasa ve la partición entera sin ejecutar nada del
   motor.
2. **¿Qué NO garantiza esto?** Cuatro cosas, escritas antes:
   - **No mide nada de latencia.** No abre ninguna puerta, así que no produce
     ni una cifra nueva de RNF-003. Atribuir el coste a una pieza será posible
     *después*, cuando alguien encienda una sola; hoy solo queda instalado el
     mecanismo para poder hacerlo.
   - **No separa motor de índices ni de siembra.** En
     `RankRelevantKnowledgeUseCase` un único booleano gobierna a la vez el
     motor por etapas, el índice de categoría, el de criticidad y la siembra
     M20 (`rank_relevant_knowledge.py:274-280, 500, 551, 611-676`). Desde
     `composition_root` esa costura no existe, y partirla exigiría tocar el
     caso de uso, que está fuera de alcance.
   - **No protege de una edición manual incoherente de `settings.json`.** Las
     claves nuevas son independientes: quien ponga `relevance_filter_enabled`
     sin motor obtiene el filtro sobre el camino de hoy, que es un estado
     legítimo pero no probado contra datos reales.
   - **No cambia quién decide abrir.** D7 punto 6 sigue mandando: la puerta se
     abre cuando el propietario registre el umbral, no antes.
3. **Criterio de parada (decidido antes de ejecutar nada).** Se para y se
   entrega `BLOCKED_BY_DECISION` o `FAILED_SAFELY`, sin acomodar el criterio,
   si ocurre cualquiera de estas tres:
   - **alguna de las siete pruebas existentes de
     `tests/unit/test_composition_root_relevance_gate.py` tiene que tocarse**
     para poner el cambio en verde —son la definición de «idéntico a hoy», y
     que una se mueva significa que el estado cerrado cambió—;
   - **el recuento del banco `--peticion` se mueve en una sola cifra** respecto
     de `17/47; 162; 78/81; 0`;
   - **la partición exige tocar** `RankRelevantKnowledgeUseCase`,
     `ContextBuilder` o `InterpreteDePeticion`.
4. **¿Qué haría el fallo imposible en vez de improbable?** El fallo a evitar es
   que el estado cerrado se mueva sin que nadie se entere. Lo que lo hace
   imposible, y no solo improbable, es comparar **la construcción entera**
   —no una bandera suelta— contra la de puerta cerrada: `_gate_snapshot()`
   fotografía los diez argumentos que las puertas pueden mover, y
   `test_all_four_keys_false_builds_exactly_todays_closed_construction` y
   `test_a_truthy_non_boolean_value_leaves_each_new_switch_closed` afirman
   igualdad de la foto completa, no de los campos que alguien recordase mirar.
   Lo que NO queda imposible: que una pieza nueva entre en el futuro por
   detrás de la maestra sin pasar por `puertas_de_memoria`. Eso hoy es solo
   prosa y el comentario del cableado.

## Contexto y problema

`category_matching_enabled` es, desde M9/M11 y ADR-109, la única puerta de todo
el camino de memoria por categoría. Un solo `is True` leído en
`composition_root.py:516-566` cablea siete cosas: el vocabulario de categoría,
el de criticidad, la bandera del caso de uso, el clasificador de intención del
intérprete (ADR-164), el filtro de relevancia, el techo de criticidad y la
bandera del `ContextBuilder`.

Esa puerta única sirvió mientras lo importante era que **nada** se encendiera
por accidente. Deja de servir en cuanto llega el momento de abrirla, por una
razón concreta y medida: RNF-003 pone el presupuesto en 300 ms P95 y la
medición con el paquete entero abierto da entre 438 y 780 ms, **sin poder
atribuir ni un milisegundo a una pieza**. Un interruptor que enciende siete
cosas solo admite dos respuestas —«mejor» o «peor»— y ninguna de las dos dice
qué hacer después.

Las costuras que el código admite hoy, leídas y no supuestas, son tres:

1. **El motor por etapas** y sus índices y siembra viven tras el booleano del
   caso de uso. Es una sola costura, no cuatro: la siembra M20 corre dentro de
   `if self._category_matching_enabled and peticion.amplia_por_categoria`
   (`rank_relevant_knowledge.py:611-676`) y el vocabulario de criticidad solo
   alimenta la marca `criticality_match`, así que «motor sin índices» no se
   puede expresar desde el cableado.
2. **El clasificador de intención** (ADR-164) solo tiene efecto si el motor
   corre: `_peticion` (282-306) únicamente se llama desde
   `_recuperar_por_etapas`.
3. **El filtro de relevancia** es una costura propia del `ContextBuilder`:
   `relevance_filter_port` decide si hay filtro (`context.py:332`) y
   `category_matching_enabled` decide el camino de puerta abierta —G8, cota
   dura y rescate por criticidad— frente al candado cerrado (`context.py:391`),
   que es el único que lee `max_criticality_category` (400).

## Opciones consideradas

1. **Partir la puerta en tres interruptores finos, sin abrir ninguno** (la
   elegida): tres claves nuevas en `settings.json`, apagadas por defecto, más
   la maestra de siempre con su significado intacto.
2. **Abrir las piezas de una en una a mano**, editando el cableado en cada
   medición y revirtiéndolo después. Deja la atribución en manos de quien mida
   y no la deja escrita en ningún sitio comprobable.
3. **Partir además el booleano del caso de uso** para separar motor, índices y
   siembra. Es una segunda partición legítima, pero exige tocar
   `RankRelevantKnowledgeUseCase`, que está fuera de alcance y es una decisión
   aparte.
4. **Esperar a que el propietario registre el umbral de D7 punto 6** y partir
   entonces. Invierte el orden: llegado ese momento, abrir seguiría siendo un
   gesto de todo o nada.

## Decisión

Se añade `src/sirius/config/memory_gates.py` con una función **pura**,
`puertas_de_memoria(settings) -> PuertasDeMemoria`, y un `dataclass(frozen=True)`
de tres booleanos. `composition_root` la llama **una vez** y cablea según esta
tabla:

| clave en `settings.json` | qué enciende |
|---|---|
| `staged_engine_enabled` | el motor por etapas con sus dos vocabularios (índices de categoría y criticidad, siembra M20) |
| `query_intent_enabled` | el clasificador de intención local de ADR-164, **solo si `staged_engine_enabled` también está encendido** |
| `relevance_filter_enabled` | el filtro de relevancia local, el techo de criticidad y el camino de puerta abierta del `ContextBuilder` |
| `category_matching_enabled` (la de siempre) | **las tres a la vez**, exactamente el significado de §6.3 |

El efectivo de cada pieza es **la maestra o su clave fina**, con una sola
excepción: la petición propia exige además el motor. Un interruptor nunca queda
«encendido pero inerte», porque prometería una observación que no existe.

La regla de lectura no se relaja: **solo el literal booleano `True` cuenta**
(`is True`), en las tres claves nuevas igual que en la maestra desde la
incidencia #471/CODEX-001. `staged_engine_port` y `staged_engine_candidate` se
siguen pasando siempre, abierta o cerrada la puerta.

Este ADR **extiende** el contrato de una sola clave de SIRIUS-ARQ-0.2 §6.3 con
tres claves finas y deja la maestra con su significado intacto. No enmienda la
Arquitectura Técnica ni `STATUS.md`: eso lo hace el propietario. **No se abre
ningún interruptor**, ni aquí ni en ningún `settings.json` de ejemplo.

## Comprobación que la sostiene

Todo lo de abajo se ejecutó sobre el árbol de esta rama
(`feature/wi-20260913-puerta-1-tres-interruptores`, base `main` en `c64f416`).
Ninguna cifra va sin el comando que la produjo.

### Las pruebas vistas FALLAR antes del cableado (ADR-001)

Con las tres pruebas nuevas escritas y `composition_root` todavía leyendo la
clave única —es decir, con las claves nuevas simplemente ignoradas—:

```
$ uv run pytest tests/unit/test_composition_root_relevance_gate.py -q
FAILED ...::test_staged_engine_switch_alone_wires_only_the_engine
FAILED ...::test_relevance_filter_switch_alone_wires_only_the_filter
FAILED ...::test_query_intent_switch_with_the_engine_wires_only_the_interpreter
FAILED ...::test_the_master_key_alone_equals_the_three_switches_together
4 failed, 12 passed in 2.04s
```

Tras el cableado, `16 passed`. Las doce que ya pasaban antes incluyen **las
siete existentes, intactas**: el criterio de parada no llegó a dispararse.

### Mutaciones transcritas

Tres mutaciones, aplicadas una a una y revertidas después. Cada una dice qué
prueba la caza, que es la única forma de saber que la prueba no es vacua.

**M1 — intercambiar el cableado de dos interruptores** (que
`relevance_filter_enabled` encienda el motor, sustituyendo
`puertas.motor_por_etapas` por `puertas.filtro_de_relevancia` en los dos
vocabularios y en la bandera del caso de uso):

```
FAILED ...::test_staged_engine_switch_alone_wires_only_the_engine - assert frozenset() == frozenset({'a...'salud', ...})
FAILED ...::test_relevance_filter_switch_alone_wires_only_the_filter - assert frozenset({'a...'salud', ...}) == frozenset()
FAILED ...::test_query_intent_switch_with_the_engine_wires_only_the_interpreter - assert False is True
3 failed, 13 passed
```

**M2 — permitir el interruptor inerte** (quitar `and motor_por_etapas` del
cálculo de `peticion_propia`):

```
FAILED ...::test_puertas_de_memoria_lee_las_cuatro_claves_en_tabla - AssertionError: {'query_intent_enabled': True}
FAILED ...::test_query_intent_without_the_engine_never_builds_the_classifier - assert ['qwen3:4b-instruct'] == []
2 failed, 14 passed
```

**M3 — relajar la regla de lectura** (`bool(settings.get(...))` en vez de
`is True`):

```
FAILED ...::test_gate_stays_closed_on_a_truthy_but_non_boolean_value - assert [('qwen3:4b-instruct', 30.0)] == []
FAILED ...::test_puertas_de_memoria_lee_las_cuatro_claves_en_tabla - AssertionError: {'category_matching_enabled': 'true'}
FAILED ...::test_a_truthy_non_boolean_value_leaves_each_new_switch_closed - AssertionError: ('staged_engine_enabled', 'true')
3 failed, 13 passed
```

M3 es además la comprobación de que la prueba existente de la incidencia #471
sigue sosteniendo lo suyo después del cambio: la caza la mutación, no el
optimismo.

### El banco, antes y después

Medición de la **etapa de búsqueda sin filtro** —no es el arnés ni la medición
con Ollama, y no se compara con ellos—. La predicción, escrita antes de medir
en la propia incidencia: **no se mueve ni una cifra**, porque ni el arnés ni el
guion de diagnóstico pasan por `composition_root`.

```
$ uv run python scripts/diagnosticar_busqueda_del_banco.py --peticion
[ejes=no peticion=real] SIN FILTRO: 17/47 exactos; 162 de mas; 78/81 hallados; omisiones criticas=0
código de salida 0
```

Antes del cambio (árbol de `c64f416`) y después (árbol de esta rama): idéntico,
`17/47; 162; 78/81; 0`, código de salida 0 en las dos. Coincide con la
referencia de la incidencia sobre `main` en `7aae33c`/`f5295be`.

### La cadena obligatoria

Una sola invocación de `scripts/check.ps1` —Ruff format, Ruff lint, mypy sobre
`src` y `tests`, y `pytest` completo— en verde sobre el árbol de esta rama. La
terna concreta y su código de salida van en el cuerpo de la PR, junto al SHA
del árbol sobre el que corrió; aquí no se clava ningún SHA como «el head»,
porque esa forma caduca al escribirla (#581). La regla comprobable es la que
queda escrita: **la cadena corre entera sobre el árbol que se propone fusionar
y sale en verde**, y `git diff --check <base> <head>` se ejecuta con las dos
revisiones, nunca a secas (deuda 25).

## Consecuencias

- `settings.json` admite tres claves más. Todas nacen apagadas y ninguna se
  escribe en ningún fichero de ejemplo ni en ninguna prueba de integración de
  producción. `MainWindow._save_configuration()` ya parte de `load_settings()`
  y conserva las claves que no conoce (`main_window.py:2617-2633`), así que
  sobreviven a un guardado desde la interfaz sin tocar la interfaz.
- Abrir una pieza y mirar qué aporta pasa a ser un gesto de una línea en
  `settings.json`, que es justo lo que RNF-003 necesitará cuando el propietario
  registre el umbral de D7 punto 6.
- La lectura de las puertas queda en un módulo puro y probado en tabla, fuera
  de la función de 300 líneas del `composition_root`; quien añada una pieza
  nueva tiene un solo sitio donde declarar su interruptor.
- Queda pendiente, como decisión aparte, partir el booleano del caso de uso
  para separar motor, índices y siembra. Mientras no se haga, «motor sin
  índices» no es un estado expresable.

## Alternativas descartadas y por qué

- **Abrir a mano en cada medición** (opción 2): la atribución no queda escrita
  en ninguna parte y se repite entera en cada ronda.
- **Partir también el booleano del caso de uso** (opción 3): exige tocar
  `RankRelevantKnowledgeUseCase`, fuera del alcance de #603, y es una decisión
  con consecuencias de ranking que merece su propio ADR.
- **Esperar al umbral** (opción 4): el momento de partir una puerta es antes de
  abrirla, no cuando ya está abierta y la medición no se deja atribuir.
- **Una sola clave con una lista de piezas** (p. ej. `memory_gates: ["engine"]`):
  cambia la forma del ajuste, obliga a validar una lista de cadenas y rompe la
  regla de lectura de `is True` que la incidencia #471 dejó fijada.

## La lección

- familia: `interruptor-que-enciende-mas-de-lo-que-se-puede-medir`
- sin esto se repetiría: poner una sola puerta delante de varias piezas
  independientes y descubrir, al abrirla, que el resultado —aquí 438-780 ms
  P95 frente a los 300 ms de RNF-003— no se puede atribuir a ninguna de ellas.
- lo hace cumplir: `tests/unit/test_composition_root_relevance_gate.py`
