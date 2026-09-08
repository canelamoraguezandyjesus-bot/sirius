# ADR-164 — La pregunta se convierte en una petición propia interpretada, no en la política uniforme de hoy

- Estado: PROPUESTO
- Fecha: 2026-09-08
- Aprobación: la fusión de esta PR por el propietario.

## Nota de arranque (publicada ANTES del primer commit de código)

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en
   `_peticion_ordinaria` (`src/sirius/application/rank_relevant_knowledge.py`):
   una sola política —M1, EXHAUSTIVA, tiempo objetivo «ahora», sin corte,
   propósito fijo— para las 47 preguntas del banco y para toda pregunta real.
   El arreglo NO vive dentro de esa función: vive **antes**, en un intérprete
   nuevo (`sirius.application.interpret_query_request`) que produce la
   `Peticion` y al que `rank()` llama en su lugar. El sitio del arreglo puede
   observar el fallo porque la `Peticion` emitida es un valor inspeccionable:
   una prueba puede capturarla y comparar campo a campo con la que el banco
   declara, cosa que la política uniforme nunca permitió distinguir.
2. **¿Qué NO va a garantizar esto?** No garantiza ninguna cifra del banco en
   CI: la inferencia de modo, cardinalidad, límite y tiempo la hace el modelo
   local, que no está en CI. En CI se fija la parte por reglas (permiso y
   propósito), la forma de la `Peticion` y el cableado; las cifras del banco
   solo las da Ollama real en la máquina del propietario. Tampoco garantiza el
   propósito por caso del banco (`planificar_viaje`, `verificar_fuente`…): el
   propósito es una regla del producto declarada por quien llama, no algo que
   se derive de la frase. Tampoco abre `category_matching_enabled`.
3. **Criterio de parada (decidido ANTES de ver ningún resultado).** La
   predicción de la medición con Ollama real, escrita antes de ejecutarla:
   **≥16/47 exactas, ≤162 elementos de más, 0 críticas perdidas, ≥73/81
   hallados**, y la coincidencia campo a campo con las 47 `peticion_p2` en
   **≥45 de 47** para modo, cardinalidad, límite, tiempo objetivo y corte de
   registro (el listón que ADR-148 fija para dar la palanca 1 por buena). Si
   sale por debajo, se registra el número tal cual y se para: no se ajusta la
   predicción después de verlo. Dos rondas de revisión con defectos de la
   misma familia → se para y se busca la raíz (ADR-001).
4. **¿Qué haría el fallo imposible en vez de improbable?** Que ninguna
   `Peticion` pudiera construirse sin declarar de dónde sale cada campo. No se
   hace en este encargo: obligaría a cambiar `Peticion`, que es contrato
   portado del laboratorio y está fuera del alcance. Lo que sí se hace es la
   forma débil: el único constructor de peticiones de producción pasa a ser el
   intérprete, y `_peticion_ordinaria` queda explícitamente como el respaldo
   de «el modelo no supo decidir», no como la política.

## Contexto y problema

Hasta este cambio, producción interrogaba al motor por etapas con **una sola
política para toda pregunta**: `_peticion_ordinaria`
(`src/sirius/application/rank_relevant_knowledge.py`) fijaba modo `M1`,
cardinalidad `EXHAUSTIVA`, tiempo objetivo «ahora», sin corte de registro y un
propósito fijo. El banco de 47 casos, en cambio, lleva su petición **por
caso** —modo, propósito, permiso, cardinalidad, límite, tiempo objetivo y
corte de registro, bajo `peticion_p2`— y el motor **ya honra esos campos**:
`G1` el propósito, `G6`/`G7` el modo y `admite_no_vigentes`, `G8` el tiempo
objetivo y el corte (`src/sirius/domain/staged_engine_gates.py`).

ADR-148 midió qué costaba esa política uniforme y lo repitió el 08-09 sobre
`82b04b4` con las mismas cifras: inyectar la petición del caso, sin tocar nada
más y sin filtro, mueve las exactas de **0/47 a 16/47** y el ruido de **487 a
162**, con 0 críticas perdidas y 73/81 hallados. Es la **palanca 1** del plan
de la línea de memoria, la de mayor salto medido, y la primera que se
construye.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3, y no se ha tocado después de ver ningún
número: **≥16/47 exactas, ≤162 de más, 0 críticas perdidas, ≥73/81 hallados**,
y **≥45/47** de coincidencia campo a campo con las `peticion_p2` del banco
(el listón que ADR-148 fija para dar la palanca 1 por buena). Esa medición
necesita Ollama real y **no la cierra este ciclo**: se entrega el comando
exacto para que la ejecute el propietario.

## Opciones consideradas

1. **Inferirlo todo con el modelo, permiso incluido.** Descartada: el permiso
   gobierna qué se puede mirar, y hacerlo depender de lo que un modelo crea
   entender de una frase convierte una frase persuasiva en una ampliación de
   lo que Sirius se autoriza a leer.
2. **Derivarlo todo por reglas léxicas, sin modelo.** Descartada como plan:
   el modo y la cardinalidad de las 47 consultas del banco no salen de una
   lista de palabras (`«¿Qué decisión de presupuesto usábamos antes?»` es
   `M2` por lo que pide, no por una palabra clave). Sí se conserva su
   consecuencia útil: lo que no necesita modelo —permiso y propósito— queda
   del lado determinista, y ahí se prueba en CI.
3. **Repartir por origen: el modelo lo que depende de entender la frase, las
   reglas lo que gobierna el permiso** (elegida).

## Decisión

**La pregunta se convierte en una `Peticion` propia, y el reparto de quién
decide cada campo es explícito.**

- **`sirius.domain.query_intent.IntencionDeConsulta`**: valor puro y cerrado
  con los cinco campos que la pregunta declara —modo, cardinalidad, límite,
  tiempo objetivo y corte de registro—. El permiso y el propósito **no están
  ahí**, y eso es la decisión, no un olvido.
- **`sirius.ports.query_intent_classifier.QueryIntentClassifierPort`**:
  puerto de un solo método que **nunca lanza**; «no he podido decidir» se
  informa con `None`, igual que `CategoryClassifierPort`.
- **`sirius.adapters.ollama_query_intent_classifier`**: tercer cliente del
  mismo servicio Ollama **local** (D7 punto 5) —nunca el proveedor de pago, y
  nunca un segundo componente de red—, con el contrato HTTP ya validado
  contra el modelo real (ADR-125): `/api/chat`, `think: false`, esquema JSON
  cerrado, URL absoluta de localhost y `follow_redirects=False`. Falla
  abierto ante cualquier problema.
- **`sirius.application.interpret_query_request.InterpreteDePeticion`**:
  compone la `Peticion`. El modelo aporta los cuatro ejes; las reglas del
  producto aportan permiso y propósito, con la **misma traducción que el
  traductor del banco declara**: `Peticion` no tiene campo de permiso, y un
  permiso sin autorizar se traduce como **propósito vacío**, que `G1` bloquea
  antes de recuperar.
- **`rank_relevant_knowledge`**: `_peticion_ordinaria` deja de ser la política
  y pasa a ser el **respaldo**; su construcción se traslada al intérprete, de
  modo que no hay dos sitios donde se decida qué es una petición ordinaria.
  `rank()` sigue recibiendo solo la consulta: ningún llamador puede inyectar
  un propósito (§11.5-M16 intacto).
- **`composition_root`**: el intérprete se cablea detrás de la **misma puerta
  cerrada por defecto** (`category_matching_enabled`) que ya gobierna el resto
  del camino del motor. Con la puerta cerrada, el adaptador local **ni se
  instancia**.

Cuatro traducciones no obvias, escritas aquí porque cada una es una decisión:

- **El límite inferido entra como OBJETIVO, nunca como duro.** `G12` trunca
  por el límite duro; truncar por una cifra que un modelo creyó leer en la
  pregunta perdería elementos sin recurso. El banco distingue `DURO` de
  `OBJETIVO` porque es adjudicación declarada, no inferencia.
- **`objetivos` se queda en 1.** La cuota de `EXACTA` del banco es
  `max(1, len(caso["resultado_esperado"]))`: adjudicación que producción no
  tiene y no inventa.
- **Una fecha que no es ISO-8601 se descarta como si no se hubiera
  declarado.** `G8` compara la fecha con `created_at` por orden
  lexicográfico: una cadena arbitraria podría excluir el canon entero en
  silencio.
- **Un límite no positivo se descarta.** Una cuota de 0 satisface la
  suficiencia de forma trivial y vaciaría la respuesta.

## Comprobación que la sostiene

**La prueba de aceptación, vista FALLAR por mutación.** Revertido el cableado
—`_peticion` volviendo siempre a `_peticion_ordinaria`, la conducta anterior a
esta ficha— sobre el árbol ya construido:

```
FAILED tests/integration/test_rank_relevant_knowledge.py::test_produccion_emite_la_peticion_derivada_de_la_consulta_no_la_uniforme
  AssertionError: assert <Modo.M1_ORDINARIO: 'M1'> is <Modo.M2_HISTORICO: 'M2'>
FAILED tests/integration/test_rank_relevant_knowledge.py::test_un_corte_de_registro_derivado_excluye_lo_registrado_despues
  assert [1] == []
2 failed, 1 passed, 48 deselected
```

La tercera —`test_sin_interprete_la_peticion_emitida_sigue_siendo_la_uniforme`,
el candado del pasado— **pasa con la mutación y sin ella**, que es justo lo
que se le pide. Restaurado el código, las tres pasan.

**El respaldo es el de siempre, medido de punta a punta.** Con Ollama
inalcanzable —el adaptador falla abierto y el intérprete cae en la política
uniforme—, `scripts/medir_interprete_de_peticion.py` reproduce **exactamente**
la fila «Hoy: petición fija» de ADR-148 sobre el banco completo:

```
[interprete] SIN FILTRO: 0/47 exactos; 487 de mas; 72/81 hallados; omisiones criticas=0
COINCIDENCIA CAMPO A CAMPO: 9/47 peticiones idénticas
   modo: 37/47   admite_no_vigentes: 42/47   cardinalidad: 13/47
   limite: 42/47  tiempo_objetivo: 43/47      corte: 45/47
```

Dos cosas dice ese número, y conviene no confundirlas: la primera línea
demuestra que **cablear el intérprete sin modelo no cambia nada** (`0/47;
487; 72/81; 0`, las mismas cuatro cifras que ADR-148 publica y repitió el
08-09); la segunda es el **suelo sin modelo** de la coincidencia campo a
campo, 9/47, el número que la inferencia real tiene que batir. Ninguna de las
dos es la medida de la palanca.

**Lo que NO se ha medido, y quién lo mide.** La coincidencia campo a campo con
Ollama real y las cuatro cifras del banco con la petición interpretada. El
comando exacto, para la máquina del propietario:

```
uv run python scripts/medir_interprete_de_peticion.py
```

(y `--modelo <otro>` para medir un modelo distinto). Hace **una** llamada por
caso —47 en total—, imprime la coincidencia campo a campo y después las cuatro
cifras del banco. La predicción escrita ANTES de ejecutarlo está arriba y en
el propio guion. Si sale por debajo, se registra el número tal cual y se para;
la palanca 1 no se da por cerrada hasta que el propietario la corra.

**Cadena completa como UNA SOLA invocación** (ADR-145, ADR-153) con
`pwsh -File scripts/check.ps1` y su código de salida capturado (ADR-154).
Anclada al árbol de `882b796`, el commit del código:

```
614 files already formatted
All checks passed!
Success: no issues found in 580 source files
5154 passed, 17 skipped, 2 xfailed in 442.60s (0:07:22)
check=0
```

**Repetida sobre `d247af9`**, el árbol que ya trae esta ficha —en vez de dar
por hecho que un cambio documental no mueve nada, que es justo lo que ADR-154
prohíbe suponer—:

```
614 files already formatted
All checks passed!
Success: no issues found in 580 source files
5154 passed, 17 skipped, 2 xfailed in 436.89s (0:07:16)
check=0
```

`git diff --check` sale limpio (`0`) sobre los dos árboles. Lo único posterior
a `d247af9` es este párrafo.

**Guardianes deterministas añadidos** (los que corren en CI, sin Ollama):
`tests/unit/test_interpret_query_request.py` (14: respaldo, los cuatro ejes,
la regla del permiso campo a campo incluido el caso sin autorizar, el ámbito
de M16), `tests/unit/test_ollama_query_intent_classifier.py` (16: fallo
abierto, contrato HTTP literal, localhost-only, y que el esquema **no pide
nunca** permiso ni propósito), dos en
`tests/unit/test_composition_root_relevance_gate.py` (puerta cerrada: el
adaptador ni se instancia; puerta abierta: recibe el modelo local) y tres en
`tests/integration/test_rank_relevant_knowledge.py`.

## Consecuencias

- La puerta `category_matching_enabled` **no se abre** en este cambio, y con
  ella cerrada el comportamiento de producción es idéntico al anterior: el
  camino del motor por etapas no se ejecuta siquiera.
- `docs/evolution/STATUS.md` **no se actualiza todavía**, aunque ADR-148
  previera hacerlo al fusionar el primer encargo del plan: la palanca 1 no
  está cerrada hasta que el propietario ejecute la medición de arriba, y
  actualizar el estado antes afirmaría más de lo que el dato sostiene.
- La siembra de M20 (ADR-129) sigue activándose en toda llamada real: el
  propósito lo fija la regla del producto y sigue conteniendo «contexto».
  ADR-148 previó revisarla «cuando la palanca 1 mida»; esa revisión llega con
  la medición, no aquí.
- Deuda declarada, sin disimular: con el modelo puesto, cada consulta añade
  una llamada local más por turno. Su coste en tiempo no se ha medido —RNF-003
  ya está suspendido en este camino por ADR-125— y se medirá junto con las
  cifras del banco.
- El propósito por caso del banco (`planificar_viaje`, `verificar_fuente`…)
  **nunca lo va a reproducir** este intérprete, y se dice antes de que lo
  encuentre una revisión: es una declaración del caso, no algo derivable de la
  frase, y en producción lo fija la regla. Por eso la medición campo a campo
  compara los cinco campos inferidos y **no** el propósito.

## Alternativas descartadas y por qué

Ver «Opciones consideradas»: inferir el permiso con el modelo (convierte una
frase en una ampliación de permisos) y derivarlo todo por reglas léxicas (no
sostiene el modo ni la cardinalidad de las 47 consultas del banco).
