# ADR-166 — El cargador del banco da a cada ítem la fecha de registro que el corpus declara

- Estado: PROPUESTO
- Fecha: 2026-09-08
- Aprobación: la fusión de esta PR por el propietario.

## Nota de arranque (publicada ANTES del primer commit de código)

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en el
   cargador del banco —`_load_canon_item`,
   `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`—, que crea los 97
   ítems del canon llamando a los casos de uso reales y deja, por tanto, el
   `created_at` que el reloj de la máquina pone: **todos con la fecha del día
   en que se mide**. El arreglo va **en el mismo sitio**, y por eso hay que
   decir por qué puede funcionar: el sitio del arreglo SÍ puede observar el
   fallo, porque `created_at` no es un estado interno del cargador sino una
   columna de la base que el puerto real lee
   (`src/sirius/adapters/persistence/staged_engine_port.py:138` y `:158`); una
   prueba puede abrir la base cargada y comparar columna a columna con lo que
   el corpus declara, y hoy sale la fecha de la ejecución. El arreglo **no**
   va en `G8` ni en el puerto: la puerta compara bien, lo que estaba mal era
   el dato que se le daba (ADR-148, hueco H2).
2. **¿Qué NO va a garantizar esto?** No garantiza que `ejes_p2.valid_from`
   sea la fecha de registro «verdadera» de cada ítem: es la única fecha que el
   corpus congelado declara por ítem, y el corpus no separa registro de
   vigencia. No cierra H1, H3 ni H4. No adelanta ni corrige la derivación de
   ejes en el puerto (incidencia #572), que sigue parada. No abre
   `category_matching_enabled`. No cambia nada del producto: en producción
   `created_at` ya es la fecha real de registro, así que ningún usuario ve
   diferencia — esto corrige el **arnés**, no el producto. Y no garantiza que
   ninguna otra métrica del banco se mueva: si se mueve, se transcribe y se
   explica caso a caso, no se ajusta ninguna cota. *(Añadido tras la primera
   revisión de esta PR, y por eso se dice cuándo: tampoco garantiza que
   `updated_at` lleve la fecha del corpus — el arnés queda **fechado a
   medias** y `updated_at` sigue siendo la del reloj del día de la medición.
   El límite, con su dato medido y su procedencia, está en «Consecuencias».)*
3. **Criterio de parada (decidido ANTES de ver ningún resultado).**
   - Si el motivo del descarte de `DEC-012` en `B04-CA-32` **antes** del
     cambio NO es `G8` «posterior al corte de registro», la premisa de
     ADR-148 H2 es falsa: se para y se registra, no se sigue.
   - Si el suelo sin ejes derivados —`--peticion`: `16/47; 162; 73/81; 0`—
     **empeora** en cualquiera de las cuatro métricas, se para y se registra
     el número tal cual.
   - Si `B04-CA-32` no pasa de fallar a acertar, o pasa por un motivo
     distinto de `G8`/corte de registro, se para y se registra.
   - Si cerrar el hueco exigiera tocar `G8`, el puerto, el corpus o
     `resultado_esperado`, se para y se pide decisión: está fuera de alcance.
4. **¿Qué haría el fallo IMPOSIBLE en vez de improbable?** Que ningún ítem del
   banco pueda nacer con la fecha del reloj. Se hace de la única forma que lo
   consigue por construcción: la fecha se fija **dentro del propio cargador**,
   en el mismo punto donde se crea el ítem y antes de devolverlo, y la prueba
   recorre **los 95 ítems que el canon crea** —los 97 que el corpus porta
   menos los dos que porta sin texto a propósito, que no llegan a crear fila
   y por tanto no tienen `created_at` que mirar—, no una muestra, comparando
   `created_at` con lo que el corpus declara para cada uno. *(La cifra decía
   «97» hasta la primera revisión de esta PR; se corrige aquí porque la
   prueba fija `len(esperados) == 95` y una ficha no puede afirmar una
   cobertura que su prueba no tiene.)* Lo que NO queda imposible, y se
   dice: que alguien escriba un cuarto arnés que llame a los casos de uso sin
   pasar por el cargador. Reunir en un único bucle las tres cargas que hoy
   existen (`_ejecutar_banco`, `_ejecutar_banco_motor_portado`,
   `_ejecutar_banco_paquete_completo`) es un refactor que esta incidencia no
   autoriza; queda dicho aquí en vez de simulado con una garantía que el
   alcance no puede dar.

## Contexto y problema

ADR-148 dejó cuatro huecos que las tres palancas del plan no cierran. El
segundo, **H2, el corte de registro**, lo describía así:

> **H2, el corte de registro** (B04-CA-32, «qué sabía el 1 de marzo»): G8
> compara con el `created_at` real
> (`src/sirius/domain/staged_engine_gates.py:214-216`) y el cargador del
> banco crea todos los ítems el día de la medición — artefacto del arnés; en
> el producto la fecha es real. Se corrige en el cargador, sin tocar el
> corpus ni `resultado_esperado`.

Es exactamente eso, y **no es un defecto del producto**: en producción
`created_at` lo pone el reloj en el momento en que el recuerdo se guarda de
verdad, que es su fecha de registro real. El artefacto vivía en el arnés:
`_load_canon_item`
(`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`) crea los 97 ítems
del canon llamando a los casos de uso reales, uno detrás de otro, en el
instante en que corre la medición. Los 97 nacían con la fecha de hoy, así
que cualquier petición con un corte de registro anterior los descartaba en
bloque.

Medido antes de tocar nada, sobre `22e880e` y con el puerto de producción
(`SIN_EJES`) y la petición de cada caso:

```
DEC-012 -> DECISION:12
resultados: []
puertas de DEC-012: [('DECISION:12', 'G8', 'posterior al corte de registro')]
```

La premisa de ADR-148 queda comprobada, no supuesta: el motivo del descarte
era literalmente `G8` «posterior al corte de registro». (El criterio de
parada del punto 3 de la nota de arranque decía que si el motivo hubiera
sido otro, se paraba; no hizo falta.)

Hay una segunda comprobación, independiente y anterior a este trabajo, que
dice lo mismo: la corrida congelada del laboratorio
(`tests/acceptance/fixtures/relevance_filter_frozen_run.json`) registra para
`B04-CA-32` `{"entraron_al_filtro": ["DEC-012"], "conservados_por_el_modelo":
[]}`. Es decir, **en el laboratorio la etapa de búsqueda sí producía
`DEC-012`** para ese caso —el laboratorio tenía fechas de verdad— y quien lo
descartó fue el modelo del filtro, no una puerta. Aquí ni siquiera llegaba al
filtro.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3, íntegro. Ninguno de sus cuatro supuestos
de parada se activó: el motivo del descarte era `G8`/corte de registro; el
suelo `--peticion` no empeoró en ninguna de las cuatro métricas; `B04-CA-32`
pasó de fallar a acertar por esa causa; y no hizo falta tocar `G8`, el
puerto, el corpus ni `resultado_esperado`.

## Opciones consideradas

1. **Fechar cada ítem con lo que el corpus declara** (la elegida). El corpus
   congelado declara una fecha por ítem, `ejes_p2.valid_from`, y el cargador
   la escribe en `created_at`.
2. **Fechar todo el canon en un instante único anterior a los cortes** (por
   ejemplo `2026-01-01`, que es lo que la medición 3 de la incidencia #572
   hizo para aislar el artefacto). Cierra el hueco con menos código, pero
   sustituye un dato falso —«todos hoy»— por otro —«todos el mismo día»—, y
   deja el banco incapaz de distinguir nunca un ítem registrado antes de otro.
   Como instrumento de diagnóstico está bien; como dato del arnés, no.
3. **Cambiar `G8`** para que ignore el corte cuando el ítem no declara fecha.
   Descartada por el enunciado del encargo y por el diagnóstico: la puerta
   compara bien. El error estaba en el dato.
4. **Añadir la fecha al corpus**, como campo nuevo por ítem. Fuera de alcance:
   el corpus no se toca.

## Decisión

**El cargador del banco escribe en `created_at` la fecha que el corpus
congelado declara para cada ítem**, en el mismo punto en que lo crea y antes
de devolverlo (`_fecha_de_registro` + `_fijar_fecha_de_registro`, invocadas
desde `_load_canon_item`).

- **La fecha declarada es `ejes_p2.valid_from`.** Es la única fecha que el
  fixture declara ítem a ítem: `ahora_declarado` es del banco entero, y los
  casos solo traen `tiempo_objetivo`/`corte_registro`, que son de la
  pregunta, no del ítem. Se dice sin adornarlo: el corpus **no separa**
  registro de vigencia, así que esta ficha no afirma que `valid_from` sea la
  fecha de registro «verdadera» de cada ítem, solo que es la que el corpus
  declara y la única disponible sin inventar nada.
- **Un ítem —exactamente uno— queda registrado en el futuro del corpus, y se
  declara con el recuento al lado.** Como el corpus no separa registro de
  vigencia, para `DEC-004` («A partir de septiembre el proveedor de mensajería
  cambia a Norte») la fecha que declara es una vigencia futura:
  `valid_from: 2026-09-01T00:00:00Z`, posterior al `ahora_declarado` del
  propio banco (`2026-06-15T00:00:00Z`). El cargador la escribe tal cual, así
  que ese ítem recibe una fecha de registro posterior al «ahora» del banco y
  `G8` lo descartaría como «posterior al corte de registro» ante cualquier
  corte entre esas dos fechas. **Hoy no mueve ninguna métrica**, y también eso
  está contado: los dos únicos casos que declaran corte (`B04-CA-32` y
  `B04-CA-47`) no esperan `DEC-004`, y el único que lo espera (`B04-CA-06`) no
  declara corte. Quien añada un caso con un corte posterior a `2026-06-15`
  tiene que contarlo; el guardián
  `test_solo_dec_004_recibe_un_registro_posterior_al_ahora_del_banco` deja el
  hecho fijado en vez de esperar a que se redescubra.
- **La FORMA en que se escribe `created_at` importa, no solo el valor.** `G8`
  compara `created_at` contra el corte **lexicográficamente**
  (`src/sirius/domain/staged_engine_gates.py:213-215`) — la «deuda 20» que la
  incidencia #574 nombra por su nombre—, así que la forma no es un detalle de
  presentación: escrita como `2026-01-01T00:00:00.000000Z` ordenaría distinto
  frente a un corte `2026-03-01T00:00:00Z` que escrita
  `2026-01-01 00:00:00.000000`. Se elige la segunda —separador espacio, sin
  `T` ni `Z`— porque es la que el esquema de Sirius 0.1 escribe de verdad (la
  del dialecto de SQLAlchemy para sus columnas `DateTime`) y con la que se
  hizo la medición de esta ficha. La fija
  `test_el_registro_escrito_lleva_la_forma_que_g8_compara` contra un literal
  propio, **sin pasar por `_FORMATO_DE_REGISTRO_EN_SQLITE`**: si el lado
  esperado leyera la misma constante que el cargador, los dos se moverían a la
  vez y no fijaría nada.
- **Lo que el corpus no fecha se fecha en su `ahora_declarado`
  (`2026-06-15T00:00:00Z`), y se dice por qué.** Exactamente uno de los 97
  ítems declara `valid_from: null`: `MEM-005`, «El contrato de mantenimiento
  se renovó, pero no consta desde cuándo» — la ausencia es deliberada y el
  propio texto la explica. No se inventa una fecha anterior: se usa el
  **«ahora» que el banco declara para sí mismo**. Con el alcance que ese
  argumento de verdad tiene, y no más: ese instante **no** es el más tardío
  que el corpus admite —`DEC-004` declara `valid_from: 2026-09-01`, dos meses
  y medio posterior, y el cargador lo escribe tal cual—, pero sí es posterior
  o igual a la fecha de registro de **todos los ítems menos ese uno**. De ahí
  que sea la elección conservadora frente a **los dos únicos cortes de
  registro que el banco declara** (`2026-03-01` y `2026-02-15`, ambos no
  posteriores al `ahora_declarado`): frente a cualquiera de ellos, lo no
  fechado no se cuela por un corte anterior, que es justo lo que una fecha
  inventada haría. El recuento —«exactamente uno»— es una comprobación, no
  una impresión: `test_solo_mem_005_no_declara_fecha_y_el_corpus_dice_por_que`.
- **La escritura es directa sobre la fila ya creada**, no por los casos de
  uso: ningún caso de uso de Sirius 0.1 acepta una fecha de creación —la pone
  el reloj, y eso es correcto en el producto—, y cambiar su firma para un
  arnés de pruebas sería llevar el laboratorio al producto.
- **`G8` no se toca**, ni el puerto, ni el corpus, ni ninguna adjudicación.

## Comprobación que la sostiene

**Las dos pruebas de propiedad, vistas FALLAR por mutación.** Retiradas las
dos líneas que fijan la fecha (`_fijar_fecha_de_registro(...)` en las dos
ramas de `_load_canon_item`), es decir restaurada exactamente la conducta
anterior a esta ficha, sobre el árbol ya construido:

```
FAILED tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py::test_el_cargador_fecha_cada_item_con_el_registro_que_el_corpus_declara - AssertionError: assert {('memory', 1....100979', ...} == {('memory', 1....000000', ...}
FAILED tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py::test_b04_ca_32_entra_porque_su_registro_ya_no_es_posterior_al_corte - AssertionError: assert [('DECISION:1...de registro')] == []
2 failed, 2 passed, 30 deselected in 2.20s
```

El detalle que la primera imprime es la firma del artefacto: los 95 valores
escritos, todos del mismo instante del reloj de la máquina, donde el corpus
declara once fechas distintas. El de la segunda es el descarte literal
`('DECISION:12', 'G8', 'posterior al corte de registro')`. Restauradas las
dos líneas, las dos pasan.

**El lado esperado de la primera prueba se lee del corpus, no de la
implementación, y también se vio fallar.** La primera revisión de esta PR
señaló que `esperados` se calculaba llamando a `_fecha_de_registro`, la misma
función que decide lo que el cargador escribe: los dos lados de la comparación
se movían a la vez, así que la prueba comprobaba que la base coincide con la
implementación y no con lo que el corpus declara. Ahora el lado esperado lee
`item["ejes_p2"]["valid_from"]` del fixture (y, para el único `null`,
`_REGISTRO_DE_LO_NO_FECHADO`). La mutación que lo demuestra es la que la
revisión propuso, y que la versión anterior de la prueba dejaba en **verde**
(`1 passed`): en `_fecha_de_registro`, la rama del `None` devuelve un instante
ajeno al corpus, `2026-12-01T00:00:00Z`, en vez de
`_REGISTRO_DE_LO_NO_FECHADO`. Con el lado esperado leído del corpus, esa misma
mutación deja la prueba en rojo:

```
E       AssertionError: assert {('memory', 1....000000', ...} == {('memory', 1....000000', ...}
E         Differing items:
E         {('memory', 5): '2026-12-01 00:00:00.000000'} != {('memory', 5): '2026-06-15 00:00:00.000000'}
1 failed, 33 deselected in 3.72s
```

**Los dos guardianes del corpus, vistos FALLAR por mutación.** No fijan
conducta sino hechos del fixture sobre los que se apoya la decisión, así que
se mutó lo que cada uno guarda:

```
# _REGISTRO_DE_LO_NO_FECHADO: "2026-06-15T00:00:00Z" -> "2026-01-01T00:00:00Z"
E  AssertionError: assert '2026-06-15T00:00:00Z' == '2026-01-01T00:00:00Z'

# el recuento leyendo el eje equivocado: ejes_p2["valid_from"] -> ejes_p2["valid_to"]
E  AssertionError: assert ['MEM-001', '...DEC-003', ...] == ['MEM-005']
E    Left contains 91 more items, first extra item: 'MEM-002'
```

**Los dos guardianes de la tercera revisión, vistos FALLAR por mutación.**
El de `DEC-004` guarda un hecho del fixture, así que se mutó el hecho —leer
`ejes_p2["valid_to"]` en vez de `valid_from`—; el de la forma escrita guarda
una decisión del cargador, así que se mutó la decisión —
`_FORMATO_DE_REGISTRO_EN_SQLITE` de `"%Y-%m-%d %H:%M:%S.%f"` a
`"%Y-%m-%dT%H:%M:%S.%fZ"`, la forma con `T`/`Z`—:

```
# ejes_p2["valid_from"] -> ejes_p2["valid_to"] en el guardian de DEC-004
E       AssertionError: assert [] == ['DEC-004']
E         Right contains one more item: 'DEC-004'

# _FORMATO_DE_REGISTRO_EN_SQLITE: "%Y-%m-%d %H:%M:%S.%f" -> "%Y-%m-%dT%H:%M:%S.%fZ"
E       AssertionError: assert ['2026-01-01T...000000Z', ...] == []
E         Left contains 95 more items, first extra item: '2026-01-01T00:00:00.000000Z'
```

La segunda mutación es exactamente la que, **antes** de este guardián,
sobrevivía: con ella puesta, las cuatro pruebas anteriores de esta ficha
seguían en verde —el lado esperado de
`test_el_cargador_fecha_cada_item_con_el_registro_que_el_corpus_declara` usa
la misma constante que el cargador, así que los dos lados se movían juntos, y
`B04-CA-32` decide su comparación en el sexto carácter, donde las dos formas
coinciden—. Ahora la mata el guardián nuevo, que compara contra un literal
independiente.

**El recuento del banco, transcrito ANTES y DESPUÉS en las cuatro
configuraciones** (`uv run python scripts/diagnosticar_busqueda_del_banco.py`
con y sin `--ejes`/`--peticion`; sin Ollama, solo etapa de búsqueda). Antes,
sobre `22e880e`; después, sobre el árbol de esta ficha:

| configuración | antes | después |
|---|---|---|
| sin banderas | 0/47; 487; 72/81; 0 | **0/47; 487; 72/81; 0** (idéntico) |
| `--ejes` | 0/47; 421; 71/81; 0 | **0/47; 421; 71/81; 0** (idéntico) |
| `--peticion` | 16/47; 162; 73/81; 0 | **17/47; 162; 74/81; 0** |
| `--ejes --peticion` | 20/47; 144; 73/81; 0 | **21/47; 144; 74/81; 0** |

(Las cuatro cifras son, en orden: aciertos exactos, elementos de más,
cobertura, omisiones críticas.) El suelo que la incidencia protege
—`--peticion`: `16/47; 162; 73/81; 0`— **no empeora en ninguna de sus cuatro
métricas**: dos suben y dos se quedan.

**Cualquier caso que cambia de resultado, explicado uno a uno.** Se diffaron
las cuatro salidas completas caso a caso, no solo los totales. Las dos
configuraciones sin la petición del caso salen **byte a byte idénticas** —era
de esperar y ahora está comprobado: la política uniforme no declara corte de
registro, así que `G8` nunca miraba `created_at` en ellas—. En las dos con
petición del caso cambia **un solo caso**, el mismo en ambas:

- **`B04-CA-32`** («¿Qué sabía Sirius sobre el aforo el 1 de marzo?», corte
  `2026-03-01T00:00:00Z`, espera exactamente `DEC-012`): pasa de
  `faltan=['DEC-012'] entraron=[] extras=0` a acierto exacto. `DEC-012`
  declara `valid_from: 2026-01-01T00:00:00Z`, anterior al corte; antes se
  fechaba hoy y `G8` lo descartaba como «posterior al corte de registro».
  Ningún elemento de más aparece con él: el caso pasa de 0 extras a 0 extras,
  y por eso `elementos_de_mas` no se mueve en ninguna de las dos columnas.

Y un caso que **no** cambia y conviene declarar, porque es el otro que podría
haberlo hecho: **`B04-CA-47`** es el único otro caso del banco que declara
corte de registro (`2026-02-15T00:00:00Z`). Su `resultado_esperado` está
vacío y era acierto exacto antes y después; el cambio no le mete ningún
elemento de más. Los dos casos con corte del banco quedan, pues, correctos.

**Los tres arneses de aceptación no mueven ninguna de sus cifras**, medido
antes y después:

```
M7 (pipeline actual):        10/47; 218; 10 críticas; 57/81   (antes y después)
motor por etapas portado:    29/47;  50;  0 críticas; 63/81   (antes y después)
paquete completo (M16):       0/47; 487;  0 críticas; 72/81   (antes y después)
```

Con una precisión que importa y que no se deduce del número: en el arnés del
motor portado, `B04-CA-32` sigue dando `obtenido = []`, pero **por otra
causa**. Antes la etapa de búsqueda no producía `DEC-012` en absoluto (`G8`);
ahora sí lo produce —comprobado con la traza, `resultados: ['DECISION:12']`,
`parada: ('S1', 'objetivos resueltos: 1/1')`— y quien lo retira aguas abajo es
la corrida congelada del laboratorio, que para ese caso declara
`{"entraron_al_filtro": ["DEC-012"], "conservados_por_el_modelo": []}` y cuya
regla RF-26 respeta entera la ausencia declarada por el modelo. Es decir: el
arnés ha pasado a comportarse **como el laboratorio**, que es lo que se
buscaba; el veredicto del modelo sobre ese ítem es otro asunto y no es de esta
ficha.

**Cadena completa como UNA SOLA invocación** (ADR-145, ADR-153) con
`pwsh -File scripts/check.ps1` y su código de salida capturado (ADR-154).
Anclada al árbol de **`c8dfbed`**, el que trae los dos guardianes de la
tercera revisión de esta PR:

```
5185 passed, 17 skipped, 2 xfailed in 529.86s (0:08:49)
check=0
```

De esa invocación se transcribe la cola capturada —la terna de `pytest` y el
código de salida—; `check=0` solo sale si `ruff format --check`, `ruff check`
y `mypy src tests` pasaron antes, porque el guion corta en el primero que
falle. La quinta validación que la incidencia exige transcribir también queda
asentada sobre ese mismo árbol: `git diff --check 22e880e c8dfbed` no imprime
nada y sale con código `0` —limpio—. Lo único posterior a `c8dfbed` es **esta
sección de la ficha**: cambios documentales que no tocan código ni pruebas, y
que existen porque la sección tiene que anclarse al árbol que la cadena
midió.

(Las cifras anteriores de esta sección —`5183 passed, 17 skipped, 2 xfailed in
487.87s`, anclada a `5200b4f`, y `5183 passed, 17 skipped, 2 xfailed in
445.07s`, anclada a `63822b0`— seguían siendo cada una la de su árbol; se
sustituyen porque cada ronda de correcciones tocó pruebas, así que la cadena
volvió a correr entera sobre el árbol nuevo. Los dos pasados de más —5183 a
5185— son exactamente los dos guardianes que la tercera revisión pidió.)

**Guardianes deterministas añadidos** (los seis corren en CI, sin Ollama),
todos en `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`:

- `test_el_cargador_fecha_cada_item_con_el_registro_que_el_corpus_declara`:
  recorre **los 95 ítems que el canon crea** (97 menos los dos que porta sin
  texto a propósito, que no llegan a crear fila y por tanto no tienen
  `created_at` que mirar), no una muestra, y compara `created_at` columna a
  columna con lo que el corpus declara para cada uno —el lado esperado se
  construye leyendo `ejes_p2.valid_from` del fixture, no llamando a
  `_fecha_de_registro`, para que un cambio de la regla no mueva los dos lados
  a la vez—; fija además que hay once fechas distintas, porque el artefacto
  tenía la firma contraria —una sola compartida por todos—.
- `test_b04_ca_32_entra_porque_su_registro_ya_no_es_posterior_al_corte`: no se
  conforma con que el caso acierte, mira el **motivo**: exige que la traza no
  traiga el descarte `G8` «posterior al corte de registro» para `DEC-012` y
  que el resultado sea exactamente ese ítem.
- `test_el_registro_de_lo_no_fechado_es_el_ahora_que_el_corpus_declara`: ata
  la constante al `ahora_declarado` del fixture, para que no envejezca sola.
- `test_solo_mem_005_no_declara_fecha_y_el_corpus_dice_por_que`: cuenta los
  ítems sin fecha declarada en vez de suponerlos, y comprueba que el propio
  texto del corpus declara la ausencia.
- `test_solo_dec_004_recibe_un_registro_posterior_al_ahora_del_banco`: cuenta
  los ítems cuya fecha declarada es posterior al `ahora_declarado` del banco
  —exactamente uno, `DEC-004`— y fija además por qué hoy no mueve ninguna
  métrica: los dos casos que declaran corte no lo esperan y el que lo espera
  no declara corte.
- `test_el_registro_escrito_lleva_la_forma_que_g8_compara`: fija la forma de
  los 95 `created_at` escritos (`AAAA-MM-DD HH:MM:SS.ffffff`, separador
  espacio, sin `T` ni `Z`) contra un literal propio, no contra
  `_FORMATO_DE_REGISTRO_EN_SQLITE`.

## Consecuencias

- El banco de 47 casos deja de medir, en su etapa de búsqueda, un artefacto
  del arnés. Medir la palanca 2 (incidencia #572) vuelve a medir la palanca.
- **El arnés queda fechado a medias, y quien mida la ventana de vigencia tiene
  que contarlo.** Esta ficha fecha con lo que el corpus declara `created_at` de
  los ítems, y solo eso: `_fijar_fecha_de_registro` emite `UPDATE memories SET
  created_at` y `UPDATE decisions SET created_at`, así que **quedan con el reloj
  de la máquina dos columnas concretas, `memory_revisions.created_at` y
  `decisions.updated_at`**. No son dos columnas cualesquiera: son justo de donde
  la palanca 2 deriva su ventana de vigencia —las memorias, de la revisión
  vigente (`58fa079e:src/sirius/adapters/persistence/staged_engine_port.py:86-89`
  trae `r.created_at AS revision_created_at` y `:262` hace
  `valid_from=_vigencia(fila["revision_created_at"])`); las decisiones, de
  `d.updated_at` (`:98` y `:290`)—. Para lo que este encargo cierra es
  suficiente, y eso es comprobable: `G8` compara `created_at` y solo
  `created_at` (`src/sirius/domain/staged_engine_gates.py:213-215`), que es
  también la única de las dos columnas que el puerto lee
  (`src/sirius/adapters/persistence/staged_engine_port.py:71` y `:78`). Pero
  **cualquier palanca que derive su ventana de vigencia de esas dos columnas
  seguirá midiendo, en esa parte, el reloj de la máquina y no el corpus**, y
  quien la mida con este arnés tiene que descontarlo en vez de atribuir a la
  palanca un efecto que es del arnés. La consecuencia no es hipotética y está
  medida sobre el merge real de esta rama con la de la palanca 2 —el dato es del
  propietario, publicado en la incidencia #574 el 08-09-2026 a las 13:12 y
  precisado a las 13:25, no una estimación de esta ficha—: sobre `58fa079e` con
  ADR-166 dentro la terna es `18/47; 57; 40/81; 9 críticas`, o sea que esa rama
  **sigue perdiendo NUEVE omisiones críticas**, exactamente las mismas que sola
  (`17/47; 57; 39/81; 9`); lo que ADR-166 le aporta es un acierto exacto y una
  ocurrencia, que son `B04-CA-32`. Fechando además `created_at` de las
  revisiones y los `updated_at`, esa rama pierde `0` (`16/47; 164; 73/81; 0`).
  (La cifra de cinco omisiones críticas que esta ficha publicó en el árbol
  `63822b0` era errónea: venía de una sonda del propietario que fechaba también
  las revisiones, y él mismo la retractó en la incidencia #574; su comentario de
  las 12:45 no vale como procedencia.) No se fecha aquí porque el propietario
  lo dejó expresamente fuera en esa misma incidencia («no hay que fecharlo para
  cumplir este encargo»); queda declarado como límite conocido, con su
  procedencia al lado, en vez de callado.
- **El producto no cambia**: ni una línea de `src/`. En producción
  `created_at` ya era la fecha real de registro; lo que se corrige es el dato
  con el que se alimentaba al motor en el laboratorio.
- El hueco H2 de ADR-148 queda cerrado. H1, H3 y H4 siguen abiertos y esta
  ficha no los toca.
- `scripts/diagnosticar_busqueda_del_banco.py` se actualiza en su cabecera
  —solo el docstring— para no seguir publicando como vigentes unas cifras que
  este cambio mueve. Es el único fichero fuera del cargador, sus pruebas y
  esta ficha que se toca, y se toca porque afirmaba un número que ha dejado
  de ser cierto.
- Queda dicho lo que NO queda imposible: alguien puede escribir un cuarto
  arnés que llame a los casos de uso sin pasar por este cargador y volver a
  fechar con el reloj. Unificar en una sola función los tres bucles de carga
  que hoy existen sería el arreglo estructural, y es un refactor que esta
  incidencia no autoriza; se declara aquí en vez de simularlo con una
  garantía que el alcance no puede dar.

## Alternativas descartadas y por qué

- **Fechar todo el canon en `2026-01-01`** (opción 2): sustituye un dato falso
  por otro. Sirve como sonda de diagnóstico —para eso lo usó la incidencia
  #572—, no como dato del arnés.
- **Tocar `G8`** (opción 3): la puerta compara bien; el dato era el malo.
  Además, el encargo lo prohíbe expresamente y manda parar si la
  investigación demostrase lo contrario. No lo demostró: la demostró correcta.
- **Añadir un campo de fecha al corpus** (opción 4): el corpus congelado no se
  toca.
- **Fechar `MEM-005` con la fecha más temprana del canon**: sería inventar una
  fecha que el corpus se niega a declarar, y encima la más permisiva frente a
  un corte de registro. Se elige el `ahora_declarado` del banco —que no es la
  fecha más tardía del corpus, pero sí una no anterior a ninguno de los dos
  cortes de registro que el banco declara— y se declara.
- **Refactorizar los tres bucles de carga en uno**: fuera del alcance de la
  incidencia. Declarado arriba como límite conocido, no disimulado.
