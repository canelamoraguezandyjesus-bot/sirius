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

Seis traducciones no obvias, escritas aquí porque cada una es una decisión:

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
- **Validar la fecha no basta: hay que NORMALIZARLA, y el corte de registro
  es de grano DÍA** (incidencia #570). `_PATRON_ISO` admite tres escrituras
  del mismo día —`2026-03-01`, `2026-03-01T00:00:00Z` y
  `2026-03-01 00:00:00`— y `G8` compara el corte con `created_at` por orden
  lexicográfico. `created_at` llega de SQLite como `str(datetime)`, con
  separador **espacio** (`staged_engine_port`), y el espacio (`0x20`) ordena
  siempre antes que la `T` (`0x54`): devolviendo la cadena verbatim, la forma
  con `T` no excluía **nada** registrado el propio día del corte y las otras
  dos excluían el día entero. Decidía el formato que el modelo eligiera esa
  vez, no la pregunta. Se canoniza, por tanto, en un solo sitio —el
  adaptador—, y con dos semánticas distintas porque las dos comparaciones lo
  son:
  - **corte de registro → final del día CIVIL que nombra**,
    `"AAAA-MM-DD 23:59:59.999999"`, la misma forma de `created_at` y por
    tanto comparable con ella. La semántica elegida para «¿qué sabía yo el
    D?» es **lo registrado al final de D**: la pregunta es de grano día, la
    hora que el modelo escriba —o deje de escribir— es formato y no
    información, y la elección no puede quedar en manos del accidente. Errar
    hacia incluir el día D nunca esconde canon; errar hacia excluirlo sí. El
    día se lee de lo **escrito**, antes de convertir a UTC (incidencia #570,
    ronda 3): tomarlo después movería `2026-03-01T00:30:00+02:00` al 28 de
    febrero y excluiría entero el 1 de marzo, que es el día por el que se
    pregunta. Y el desfase declarado **no se descarta** (incidencia #570,
    ronda 4): descartarlo falla en el sentido contrario y peor, porque con un
    desfase NEGATIVO el día civil termina después del final del día en UTC
    —el 1 de marzo en `-05:00` no acaba hasta las `2026-03-02 04:59:59` UTC—
    y cortar antes escondería lo registrado en sus últimas cinco horas. El
    corte emitido es el **más tardío** de los dos finales, el del día civil
    en el desfase declarado llevado a UTC y el del día en UTC: es la única
    escritura que respeta en los dos sentidos el criterio asimétrico de la
    viñeta.
  - **tiempo objetivo → instante en UTC escrito con el sufijo `Z`**, el
    mismo con el que el corpus declara `valid_from`/`valid_to`. `G8` los
    compara **como cadenas** (`valid_from > objetivo`), y `"…Z"` no es
    lexicográficamente comparable con `"…+00:00"`: el `+` (`0x2B`) ordena
    antes que la `Z` (`0x5A`), así que en una coincidencia EXACTA de
    instante el veredicto se invertía —un ítem cuyo `valid_from` es justo el
    tiempo objetivo pasaba de admitido a «aún no vigente», y uno cuyo
    `valid_to` coincide, de expirado a admitido—. El corpus tiene tres de
    esas fronteras exactas (`B04-CA-22`/`DEC-009`, `B04-CA-26`/`DEC-002` y
    `DEC-003`, `B04-CA-44`/`DEC-011`), hoy latentes porque producción
    entrega todo ítem con `SIN_EJES` y la medición corre con `con_ejes=False`
    (incidencia #570, ronda 3). Se corrige emitiendo la forma con la que se
    compara, no tocando `G8`. **El respaldo se alinea igual**: sin modelo, el
    «ahora» de `InterpreteDePeticion` también sale con `Z`, porque un
    respaldo con otra forma reintroduciría el mismo desajuste en la frontera.
    Una fecha desnuda es su medianoche, que es como el banco adjudica los
    casos con tiempo objetivo declarado (`B04-CA-06`:
    `2026-09-15T00:00:00Z`).
- **El «hoy» de la instrucción se resuelve en CADA consulta, no en el
  constructor** (incidencia #570). El adaptador se construye una sola vez por
  arranque (`composition_root.build_conversation_dependencies`) y Sirius es
  una aplicación de escritorio que se deja abierta durante días: con el «hoy»
  congelado, «¿qué decidí ayer?» quedaría anclada al día del arranque y el
  desfase crecería sin límite y en silencio. El parámetro `ahora` sigue
  existiendo y manda cuando el llamador lo fija —la medición del banco usa su
  `ahora_declarado`—; lo que cambia es solo el caso `ahora=None`.

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

**La normalización del instante, vista FALLAR por mutación** (incidencia
#570, ronda 2). Cuatro mutaciones, una por cada pieza corregida, sobre el
árbol ya construido:

```
# corte_de_registro=_corte_de_registro(...) -> _iso_declarado(...)
FAILED tests/integration/test_rank_relevant_knowledge.py::test_las_tres_escrituras_del_corte_de_hoy_admiten_el_mismo_conjunto[] - assert [] == [1]
FAILED tests/integration/test_rank_relevant_knowledge.py::test_las_tres_escrituras_del_corte_de_hoy_admiten_el_mismo_conjunto[ 00:00:00] - assert [] == [1]

# tiempo_objetivo=_tiempo_objetivo(...) -> _iso_declarado(...)
E  AssertionError: assert '2026-03-20T00:00:00Z' == '2026-03-20T00:00:00+00:00'

# self._ahora = ahora  ->  congelado en el constructor (la conducta anterior)
FAILED tests/unit/test_ollama_query_intent_classifier.py::test_el_hoy_de_la_instruccion_se_resuelve_en_cada_consulta

# instante_utc: momento.replace(tzinfo=UTC) -> momento
FAILED tests/unit/test_ollama_query_intent_classifier.py::test_instante_utc_lee_el_mismo_instante_escrito_de_tres_formas[2026-03-01 00:00:00]
```

La primera es la que importa: con la mutación puesta, la escritura con `T`
**pasa** y las otras dos fallan devolviendo `[]` — exactamente el defecto,
que la forma elegida por el modelo decidiera el conjunto admitido.
Restaurado el código, las tres escrituras devuelven `[1]`.

**Lo que la ronda 2 canonizó MAL, visto FALLAR por mutación** (incidencia
#570, ronda 3). Cuatro mutaciones más, cada una restaurando la conducta
anterior a esta ronda, sobre el árbol ya construido:

```
# _corte_de_registro: date.fromisoformat(texto[:10]) -> momento.date()
FAILED tests/unit/test_ollama_query_intent_classifier.py::test_el_corte_conserva_el_dia_civil_que_la_pregunta_nombra[2026-03-01T00:30:00+02:00]
E  AssertionError: assert '2026-02-28 23:59:59.999999' == '2026-03-01 23:59:59.999999'

# _tiempo_objetivo: .replace(_DESFASE_EXPLICITO, _SUFIJO_UTC_DEL_CORPUS) fuera
FAILED tests/unit/test_ollama_query_intent_classifier.py::test_el_objetivo_emitido_da_el_mismo_veredicto_de_g8_que_el_del_banco
E  AssertionError: assert (False, 'aun ...mpo objetivo') == (True, '')

# _FINAL_DEL_DIA = time(23, 59, 59, 999999) -> time(0, 0, 0)
FAILED tests/unit/test_ollama_query_intent_classifier.py::test_el_corte_emitido_no_es_el_instante_que_el_banco_declara_y_eso_esta_decidido
E  AssertionError: assert '2026-03-01 00:00:00.000000' == '2026-03-01 23:59:59.999999'

# respaldo: _ahora_como_lo_declara_el_corpus -> self._clock.utc_now().isoformat()
FAILED tests/unit/test_interpret_query_request.py::test_sin_clasificador_la_peticion_es_la_uniforme_de_siempre
E  AssertionError: assert '2026-06-15T00:00:00+00:00' == '2026-06-15T00:00:00Z'
```

La segunda es la que importa y la que ninguna prueba de la ronda 2 cubría:
no afirma la CADENA emitida —eso ya lo hacía
`test_el_tiempo_objetivo_sale_en_utc_con_el_sufijo_del_corpus`, y pasaba con
el defecto puesto—, sino que el **veredicto de `_g8`** sea el mismo con la
ventana que emite el intérprete y con la que declara el banco, sobre la
frontera exacta real del corpus (`B04-CA-26` y el `valid_from` de `DEC-003`,
ambos `2026-04-01T00:00:00Z`). Con `+00:00` el ítem se rechazaba como «aún no
vigente»; con `Z` se admite, igual que con la ventana del banco. Restaurado
el código, las cuatro pasan.

**Lo que esto SÍ cambia en la predicción de la medición con Ollama, dicho
sin ajustar la predicción.** La predicción escrita antes de medir
(`coincidencia campo a campo >= 45/47`) **se mantiene sin tocar**: se declara
aquí su efecto, no se reescribe el número.

La ronda 2 de esta ficha afirmó que «ningún caso del banco declara
`corte_de_registro`». **Era falso**, y la propia línea «`corte: 45/47`» que
esta ficha imprime lo desmentía: **dos** de los 47 lo declaran —`B04-CA-32`
(«¿Qué sabía Sirius sobre el aforo el 1 de marzo?», `2026-03-01T00:00:00Z`) y
`B04-CA-47` (`2026-02-15T00:00:00Z`)—, y los dos lo declaran a **medianoche**.
Corregida la premisa, la elección de semántica se pesa contra esos dos casos y
**se conserva el final del día**, con su consecuencia declarada:

- `scripts/medir_interprete_de_peticion.py::_campos` compara el campo `corte`
  como **instante**. El intérprete emite `2026-03-01 23:59:59.999999` donde
  `peticion_desde_caso` lee `2026-03-01T00:00:00Z`: son instantes distintos,
  así que esos dos casos **no pueden coincidir nunca** en el campo `corte`, ni
  con un modelo perfecto. El **techo** del campo queda en **45/47**, el mismo
  número que el suelo sin modelo que esta ficha publica.
- Es una diferencia de **semántica declarada**, no de inferencia: la
  comparación campo a campo del guion la penaliza igual, y conviene leerla
  así cuando se lea el resultado.
- Se acepta, y por qué: el listón `>=45/47` es de **peticiones idénticas**, no
  del campo `corte`; el margen de 2 que concede lo consume este artefacto solo
  si esos dos casos coinciden en todo lo demás. La alternativa —canonizar el
  corte a la medianoche declarada— reproduciría el número del banco pero
  cambiaría la respuesta del producto: «¿qué sabía yo el 1 de marzo?» dejaría
  fuera todo lo registrado durante el 1 de marzo. Errar hacia incluir el día D
  no esconde canon; errar hacia excluirlo sí, y esa es la propiedad que manda
  sobre una cifra de medición.
- Lo que la corrección deja fijado en una prueba, no en la prosa:
  `test_el_corte_emitido_no_es_el_instante_que_el_banco_declara_y_eso_esta_decidido`
  lee el banco, comprueba que los casos que declaran corte son exactamente
  esos dos y afirma que lo emitido es el final de su **mismo día civil** y no
  su medianoche.

En `tiempo_objetivo` la normalización solo puede **añadir** coincidencias —una
escritura sin zona que antes se puntuaba como fallo por comparar ingenuo con
consciente ahora se lee como el mismo instante—, nunca quitarlas; el cambio de
`+00:00` a `Z` de la ronda 3 no la mueve, porque el guion compara ese campo
como instante y las dos formas nombran el mismo.

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

Esa captura es la de la ronda anterior y **no se ha vuelto a ejecutar** en
esta: sin modelo, el intérprete no pasa por el adaptador —cae en la política
uniforme— y las dos formas que la medición compara ya eran conscientes, así
que la normalización de esta ronda no puede moverla.

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
Anclada al árbol de **`5c0862f`**, el que trae el código y las pruebas de la
ronda 3 (incidencia #570):

```
614 files already formatted
All checks passed!
Success: no issues found in 580 source files
5176 passed, 17 skipped, 2 xfailed in 461.32s (0:07:41)
check=0
```

`git diff --check` sale limpio (`0`) sobre ese árbol. Lo único posterior a
`5c0862f` es **esta sección de la ficha**: un cambio documental que no toca
código ni pruebas, y que existe precisamente porque la ronda 2 dejó esta
sección anclada a un árbol que ya no era el head.

**Historia de la misma cadena en las rondas anteriores** —se conserva
declarada como tal, no como la cifra vigente—: `882b796` (el commit del código
de la ronda 1) y `d247af9` (el árbol que estrenó esta ficha) midieron los dos
`5154 passed, 17 skipped, 2 xfailed` con `check=0`, en `442.60s` y `436.89s`
respectivamente. La diferencia hasta las 5176 de hoy son los guardianes
añadidos en las rondas 2 y 3.

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
- **`rank()` deja de devolver solo lo vigente, y su contrato lo dice ahora**
  (incidencia #570). El puerto real nunca declara el eje de confirmación
  (`SIN_EJES`, `staged_engine_port`), y con `confirmacion is None` la puerta
  `G6` (`staged_engine_gates._g6`, líneas 177-184) solo rechaza un item no
  vigente en `M1`: en `M2`, `M3`, `M4` y `M5` —los cuatro modos restantes que
  el modelo local puede inferir, no solo el histórico— `rank()` devuelve
  también memorias archivadas y decisiones sustituidas, que `ContextBuilder`
  inyecta en el contexto del turno. Es la semántica declarada del motor y la
  que el banco espera; lo que faltaba era decirlo en el docstring de `rank()`,
  que seguía prometiendo «every vigente memory/decision».

## Alternativas descartadas y por qué

Ver «Opciones consideradas»: inferir el permiso con el modelo (convierte una
frase en una ampliación de permisos) y derivarlo todo por reglas léxicas (no
sostiene el modo ni la cardinalidad de las 47 consultas del banco).
