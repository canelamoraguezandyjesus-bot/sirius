# ADR-178 — La autoridad por clase se deriva de la vía GitHub que el despachador declara, no de una segunda tabla a mano

- Estado: PROPUESTO
- Fecha: 2026-09-12
- Aprobación: la fusión de la PR por el propietario

## Nota de arranque (escrita ANTES de tocar una línea de código)

### Lo medido antes de escribir esta nota (12-09-2026, sobre `main` y `estado-del-motor`)

| Dónde | Qué dice |
|---|---|
| `src/sirius_engine/domain/authority.py`, `_TABLA_AUTORIDAD` (ADR-041, v1.7) | `DOCUMENTACION -> MOTOR`, `INVESTIGACION -> MOTOR`; el docstring lo justifica con «A5 nunca publica nada en GitHub» |
| `src/sirius_engine/dispatcher.py`, `TABLA_ACTIVACION` | cuatro clases con vía GitHub: `PROGRAMACION`, `AUDITORIA`, `DOCUMENTACION` (ADR-088) e `INVESTIGACION` (ADR-099) |
| ADR-088 y ADR-099 | **cero** menciones de «autoridad»: añadieron la fila a una tabla y no tocaron la otra |
| Diario real (rama «estado-del-motor», 76 encargos) | documentación **10** (8 entregados, 2 cancelados), investigación **5** (2 entregados, 2 cancelados, 1 activo), auditoría 1, programación 60 |
| Diario de despacho | episodios de despacho a GitHub: documentación **10 de 10**, investigación **5 de 5** |
| «racha_siete_dias.jsonl» | 345 líneas de programación, 11 de auditoría, **0 de documentación, 0 de investigación** |
| Contrato §11.1 | «documental publicada (PR en el repo): sí, incidencia, conmuta» -fila que el código no tiene-; «investigación: no» -falso desde ADR-099-, anotada por ADR-161: «la fila sigue aquí porque `TABLA_ACTIVACION` sigue teniendo la clase» |
| `tests/engine/test_authority.py` | fija `DOCUMENTACION` e `INVESTIGACION` como «nativas sin proyección GitHub -> MOTOR»: **la prueba fija el error** |

Lo que eso significa: **quince encargos corrieron enteros en la vía GitHub habiendo
nacido con autoridad «motor»**. Con esa autoridad, `sirius-racha` no los mide
nunca (contrato §11.2: solo mide clases `incidencia`), así que no pueden
conmutar jamás; `supervisor._bajo_jurisdiccion_del_motor` los declara del motor
y el reconciliador no los vigila; y `authority_reversion` no puede revertirlos.
Nadie lo vio porque lo que se comprueba es la copia, no la relación.

### 1. ¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo OBSERVAR el fallo?

El fallo vive en que **«qué clases existen en la vía GitHub» está escrito dos
veces**: en `TABLA_ACTIVACION`, que es la que manda porque el despachador la
usa, y en `_TABLA_AUTORIDAD`, que es una copia de agosto (ADR-041). El contrato
§11.1 lo dice con su propia columna: la autoridad es función de «¿Existe en la
vía GitHub?». Cuando ADR-088 y ADR-099 añadieron filas a la primera tabla, la
segunda se quedó como estaba, y es la familia que ADR-033 nombró: la lista a
mano que se queda corta en cuanto alguien añade una entrada en otro sitio.

El arreglo va al dominio: **una sola definición** de las clases con vía GitHub,
de la que la autoridad se **deriva**; `TABLA_ACTIVACION` queda atada a esa
definición por una guarda. Y el contrato §11.1 se comprueba **contra el
código** en la batería, leyendo su columna. El sitio del arreglo sí observa el
fallo: si mañana alguien añade una clase a la vía GitHub sin tocar la
definición, la guarda falla; si el contrato y el código discrepan, la guarda
falla.

### 2. ¿Qué NO va a garantizar esto?

- No decide si `INVESTIGACION` y `AUDITORIA` deben salir de `TABLA_ACTIVACION`:
  eso es la ejecución pendiente de ADR-161, y es una decisión del propietario.
  Mientras estén, su autoridad es `incidencia`, que es lo que el contrato ya
  anota para ellas.
- No cambia la autoridad con la que nacieron los quince encargos históricos.
  Catorce son terminales; el activo (`WI-20260828-122242`, investigación de un
  carril retirado) es un caso aparte y se deja dicho, no resuelto.
- No hace conmutar a documentación: conmutar exige siete días medidos (§11.2), y
  medir empieza hoy, no termina hoy.
- No reescribe §11.1 entero: solo las dos filas que el código desmiente, y con
  la nota de que «documental no publicada» no tiene hoy ninguna vía en el motor.

### 3. Criterio de parada (decidido ANTES de ver ningún resultado)

Se da por terminado cuando, y solo cuando:

- (a) `autoridad_de_clase` devuelve `INCIDENCIA` para toda clase de
  `TABLA_ACTIVACION` y `MOTOR` para las demás, y sigue siendo **total** (una
  clase nueva sin sitio revienta explícito, como hasta ahora).
- (b) Una guarda falla si `set(TABLA_ACTIVACION) != CLASES_CON_VIA_GITHUB`.
- (c) Una guarda lee la tabla §11.1 del contrato y comprueba su columna
  «¿Existe en la vía GitHub?» contra el código, con las filas que no son clases
  (conversación, reparación/espera/cancelación) excluidas de forma explícita y
  contadas, para que no pase en vacío.
- (d) Mutaciones vistas caer: quitar `DOCUMENTACION` de la definición; volver a
  escribir `_TABLA_AUTORIDAD` a mano con `MOTOR` para documentación; desatar la
  guarda de `TABLA_ACTIVACION`; cambiar la fila del contrato sin tocar el código.
- (e) Una pasada en seco de `sirius-racha` sobre el diario real enseña que
  documentación **entra** en la medición (los diez son terminales, así que hoy
  no añade líneas: se dice el número, sea el que sea).
- (f) Batería entera en verde, `ruff` y `mypy` en verde.
- (g) Las pruebas de `test_authority.py` que hoy fijan `MOTOR` para documentación
  e investigación **cambian**, y el ADR dice por qué: fijaban la copia.

Parada anticipada: si derivar exige que el dominio importe al despachador
(inversión de la dependencia), se para y la definición se mueve al dominio; si
aparece una decisión que es del propietario (quitar una fila del contrato), se
deja anotada y no se toma aquí.

### 4. ¿Qué haría el fallo IMPOSIBLE en vez de improbable?

Que la autoridad no sea una tabla sino una **función de la única lista** de
clases con vía GitHub, y que el contrato se lea en la batería como dato, no
como prosa. Con las dos cosas, «añadir una clase a la vía GitHub» toca un solo
sitio y el resto se deriva; y «el contrato dice una cosa y el código otra» ya
no puede fusionarse en verde.

> **Nació como ADR-177 y se renumeró a 178 el 12-09-2026.** Ese día había
> **tres** ADR-177 distintos, cada uno en su rama abierta y ninguno en `main`:
> la ampliación por categoría (PR #590, la más antigua), este, y la guarda de
> piezas sin llamante (PR #593, del motor). `scripts/siguiente_adr.py` no lo
> evita y lo dice él mismo: consulta las ramas **del clon**, y una rama que no
> se ha traído no existe para él. Es el modo exacto en que nacieron los dos
> ADR-016 que ADR-032 conserva. Se renumeró el más nuevo de los dos que podían
> moverse; la PR #590 conserva el 177 por ser la primera.

## Contexto y problema

El contrato operativo (§11.1) fija la autoridad de cada clase de trabajo por
una sola pregunta: **¿existe en la vía GitHub?** Si sí, la incidencia es la
fuente de verdad hasta que conmute; si no, lo es el almacén del motor. El
código responde a esa pregunta en dos sitios distintos: `TABLA_ACTIVACION`
(`src/sirius_engine/dispatcher.py`), que es la que decide de verdad qué se
despacha a GitHub, y `_TABLA_AUTORIDAD` (`src/sirius_engine/domain/authority.py`),
escrita en agosto (ADR-041) y no tocada desde entonces. ADR-088 y ADR-099
añadieron documentación e investigación a la primera y no a la segunda, y
ninguna prueba lo vio porque `tests/engine/test_authority.py` fija la copia,
no la relación entre las dos. Lo medido está en la nota de arranque: quince
encargos reales corrieron en GitHub con autoridad «motor», y el contador de
los siete días no ha medido nunca ninguno de ellos.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, apartado 3: (a) autoridad derivada y total, (b)
guarda que ata `TABLA_ACTIVACION` a la definición única, (c) guarda que lee la
tabla §11.1 del contrato como dato, (d) cuatro mutaciones vistas caer, (e) una
pasada en seco de la racha sobre el diario real, (f) batería, `ruff` y `mypy`
en verde, (g) las pruebas que fijaban la copia cambian y el ADR dice por qué.
Parada anticipada si derivar exige que el dominio importe al despachador, o si
aparece una decisión que es del propietario.

## Opciones consideradas

1. **Corregir a mano las dos filas** de la tabla de autoridad (documentación e
   investigación a `incidencia`). Arregla el síntoma y deja las dos listas: la
   próxima clase que entre en la vía GitHub volverá a divergir, igual que
   divergieron ADR-088 y ADR-099. Descartada.
2. **Derivar la autoridad de `TABLA_ACTIVACION` importándola desde el
   dominio.** Invierte la dependencia -el dominio importaría al despachador,
   que importa puertos y proyección-: es la parada anticipada que la nota de
   arranque preveía. Descartada.
3. **Una sola definición en el dominio, autoridad derivada, despachador atado
   por una guarda, contrato leído como dato.** Elegida; es la decisión de
   abajo.
4. **Partir `DOCUMENTACION` en dos clases** (publicada y no publicada) para
   calcar las dos filas del contrato. El motor no tiene ninguna vía para la no
   publicada -diez de diez encargos de documentación se despacharon a GitHub-,
   así que sería una clase sin fila en la tabla de activación ni forma de
   nacer. Descartada, y el contrato lo dice ahora en su propia fila.

## Decisión

La autoridad por clase se deriva de una sola definición en el dominio de qué clases existen en la vía GitHub (`CLASES_CON_VIA_GITHUB`, en `src/sirius_engine/domain/authority.py`), con su complemento `CLASES_SIN_VIA_GITHUB` declarado también a propósito para que la función siga siendo total y una clase nueva sin declarar reviente como fijó ADR-041; `TABLA_ACTIVACION` queda atada a esa definición por una guarda, y la tabla §11.1 del contrato se lee como dato en la batería y se comprueba fila a fila contra el código. Con eso, documentación e investigación pasan a nacer con autoridad «incidencia», que es lo que llevan siendo de hecho desde ADR-088 y ADR-099.

En concreto:

- `src/sirius_engine/domain/authority.py`: `CLASES_CON_VIA_GITHUB` (programación,
  auditoría, documentación, investigación), `CLASES_SIN_VIA_GITHUB`
  (conversación, consulta larga, mixta) y `_TABLA_AUTORIDAD` construida SOLO
  con lo declarado en una de las dos. `_CLASES_CONMUTABLES` sigue derivándose
  de la tabla, así que documentación e investigación pueden ahora aparecer en
  el registro de conmutaciones (§11.3) y revertir (§11.4).
- `src/sirius_engine/dispatcher.py`: `TABLA_ACTIVACION` no cambia; su
  comentario dice de qué depende. La atadura es
  `test_la_via_github_del_despachador_es_exactamente_la_de_la_autoridad`.
- Contrato §11.1: la fila de investigación dice «sí» en la vía GitHub y
  «incidencia», con su retirada acordada anotada como estaba; la de
  «documental no publicada» dice que no tiene clase en el motor; la de
  «documental publicada» cita ADR-088. Y un párrafo nuevo dice que esa
  columna es la definición y que la batería la comprueba.
- `tests/engine/test_authority.py`: las particiones que fijaban la copia
  cambian de lado; y cinco pruebas nuevas: derivación y totalidad, las dos
  clases del defecto, la atadura al despachador, el contrato leído como dato
  (con anti-vacua: la tabla entera cartografiada, fila por fila) y la
  mutación del lector del contrato.
- `tests/engine/test_seven_day_streak_cli.py` y `tests/engine/test_supervisor.py`
  usaban documentación e investigación como ejemplos de «clase MOTOR»:
  fijaban la copia. Pasan a `CONSULTA_LARGA`, y la racha gana la prueba de
  que documentación **entra** en la medición.

Quién cambia de comportamiento, medido sobre los llamadores de
`autoridad_de_clase`: `sirius-racha` (§11.2) empieza a medir esas dos clases;
`supervisor._bajo_jurisdiccion_del_motor` deja de tratarlas como del motor, así
que el reconciliador las vigila; `work_intake` las hace nacer con
`incidencia`; `authority_reversion` puede revertirlas. `dispatch_cli` solo las
enseña.

## Comprobación que la sostiene

Sobre el árbol de esta rama, el 12-09-2026:

- `uv run ruff format --check`, `uv run ruff check src tests`: en verde.
  `uv run mypy src`: en verde.
- Pruebas afectadas (`test_authority`, `test_supervisor`,
  `test_seven_day_streak_cli`, `test_authority_reversion`,
  `test_seven_day_streak`, `test_dispatcher`, `test_reflect_cli`,
  `test_carriles_retirados`): **393 en verde**.
- Las cuatro mutaciones del criterio de parada, sembradas y vistas caer sobre
  `test_authority.py`, `test_seven_day_streak_cli.py` y `test_supervisor.py`:

| Mutación | Pruebas que caen |
|---|---|
| Documentación fuera de la vía GitHub, a mano, como antes | **6**, entre ellas la atadura al despachador y el contrato como dato |
| La tabla vuelve a escribirse a mano con `MOTOR` para documentación | **6**, entre ellas la de derivación y totalidad |
| Alguien añade una clase al despachador y no a la autoridad | 1: la atadura |
| El contrato cambia una fila sin tocar el código | 2: el contrato como dato y el lector mutado |
| (ronda 1) Una fila vuelve a dar por pendiente una retirada ejecutada | 1 |
| (ronda 1) Se saca una clase retirada de la vía GitHub | 6, y 5 si además se quita del despachador |

- Medición (e), sobre el diario real de `estado-del-motor` (76 encargos, 3 no
  terminales): la pasada de la racha **recorría** 2 encargos y con la autoridad
  nueva recorre **3**. El que entra es `WI-20260828-122242`, investigación,
  `active` desde el 28-08, de un carril ya retirado. Ningún encargo de
  documentación entra hoy: los diez son terminales.
- Batería entera sobre el árbol de `9366581` (`uv run pytest -q`, sin `-x`): **5.462 en verde**, 17 omitidas, 2 xfail, en 10 minutos. Con `-x`, la primera pasada se paró en `tests/engine/test_work_intake.py`, otra prueba que fijaba la copia; se arregló y se relanzó entera.

## Consecuencias

- **Documentación e investigación entran en la pasada de `sirius-racha`**, que
  hasta hoy ni las miraba (cero líneas suyas en el registro), y el
  reconciliador las vigila.

  **Entrar en la pasada no es empezar a medir para conmutar, y la diferencia
  importa** (hallazgo de la primera ronda de revisión; la primera versión de
  este ADR las confundía). La precondición de §11.2 la implementa
  `projection_verifier.precondicion_estado_propio`, y su conjunto
  `CLASES_CON_ESTADO_PROPIO` está **vacío**: reproducido, el verificador
  devuelve `NO_COMPARABLE` para **las siete clases**, incluida `programacion`.
  Un `NO_COMPARABLE` no es un día verde -lo dice el propio módulo- así que
  siete días así acumulan **cero**. Lo que ADR-178 cambia es que esas dos
  clases **entren** en el bucle y dejen líneas en el registro; el día en que la
  medición empiece de verdad lo decide otro bloque, el que cablee el retorno
  del desenlace de GitHub al almacén (H-25, incidencia #376), y ese es el único
  sitio desde el que una clase entra en `CLASES_CON_ESTADO_PROPIO`.
- **`WI-20260828-122242` va a salir en la próxima pasada**, con resultado
  `NO_COMPARABLE` por esa precondición -no como divergencia-: es una
  investigación activa de un carril retirado, atascada desde el 28-08. Qué
  hacer con ella -cancelarla o cerrar su incidencia- es una decisión del
  propietario, y este ADR solo la hace visible en el registro.
- Los quince encargos históricos no se reescriben: la autoridad se consulta
  por clase, así que a efectos de racha, supervisor y reversión ya cuentan
  como `incidencia`; el diario conserva lo que fue.
- **Añadir una clase a la vía GitHub toca tres sitios**, y olvidar cualquiera
  pone Quality en rojo: `CLASES_CON_VIA_GITHUB`, `TABLA_ACTIVACION` y la fila
  del contrato. Antes tocaba dos y nadie vigilaba el tercero.
- Una clase nueva de `WorkItemClass` sin declarar en ninguno de los dos lados
  sigue reventando con `KeyError` (ADR-041): derivar no ha abierto ningún
  valor por defecto en silencio.
- **No toca la retirada de los carriles de investigación y auditoría, que ya
  está ejecutada** (ADR-161 la acordó, ADR-163 la ejecutó, ADR-167 la
  corrigió). La primera versión de este ADR la daba por pendiente y decía que
  consistía en quitar esas clases de `TABLA_ACTIVACION`: las dos cosas son
  falsas, y la segunda es **lo contrario** de lo que el contrato manda. §13.2
  dice, con esas palabras, que `TABLA_ACTIVACION` **sigue conteniendo**
  `AUDITORIA` e `INVESTIGACION` y que las filas de §11.1 y §12.4 no se borran,
  porque «un contrato que declarase inexistente una clase que el registro sigue
  describiendo sería falso, y la retirada dejaría de ser reversible con solo
  quitar una línea». La fuente de verdad de qué carril está retirado es
  `docs/implementation/work_engine/carriles_retirados.json`, y reactivar uno es
  quitar su entrada de ahí y fusionar.

  **Retirada y autoridad son cosas distintas**, y por eso esto no cambia nada
  de lo que ADR-178 decide: una clase con el carril retirado sigue en la vía
  GitHub -sus encargos históricos viven ahí- y conserva su autoridad; lo que
  cambia es que `sirius-despachar` ya no admite órdenes suyas.

## La primera ronda de revisión: dos textos míos que eran falsos

Ningún hallazgo en el cambio de autoridad. Los dos son **documentales, ciertos y
reproducidos**, y los dos con el mismo patrón: yo afirmando de memoria en vez de
preguntarle al código.

### 1. Prometí una divergencia que el verificador no va a ver

Escribí que `WI-20260828-122242` «va a salir en la próxima pasada como
divergencia vigilada». Falso. `projection_verifier.CLASES_CON_ESTADO_PROPIO`
está **vacío**, y `precondicion_estado_propio` va ANTES que cualquier ventana
de tolerancia: reproducido, el verificador devuelve `NO_COMPARABLE` para **las
siete clases**, `programacion` incluida. Un `NO_COMPARABLE` no es un día verde
-lo dice el propio módulo-, así que siete días así acumulan cero.

La distinción que me faltaba, y que ahora está escrita en las consecuencias:
**entrar en la pasada y añadir líneas al registro no es empezar a medir para
conmutar.** ADR-178 hace lo primero para documentación e investigación. Lo
segundo empieza el día en que algo devuelva el desenlace de GitHub al almacén
(H-25, incidencia #376), que es el único sitio desde el que una clase entra en
ese conjunto.

### 2. Di por pendiente una retirada ejecutada, y la describí al revés

Escribí que ADR-178 «no decide la ejecución pendiente de ADR-161 (sacar
investigación y auditoría de `TABLA_ACTIVACION`)». Dos errores en una frase: la
retirada **está ejecutada** desde ADR-163 (corregida por ADR-167), y sacar esas
clases de `TABLA_ACTIVACION` es **lo contrario** de lo que el contrato manda.
§13.2 lo dice con estas palabras: «`TABLA_ACTIVACION` **sigue conteniendo**
`AUDITORIA` e `INVESTIGACION`, y las filas de §11.1 y §12.4 tampoco se borran»,
porque un contrato que declarase inexistente una clase que el registro sigue
describiendo sería falso y la retirada dejaría de ser reversible. La fuente de
verdad es `docs/implementation/work_engine/carriles_retirados.json`, y
reactivar un carril es quitar su entrada de ahí y fusionar.

El revisor señaló el riesgo real: ese texto **podría llevar a otra IA a hacer un
cambio contrario a lo aprobado**. Y en este repositorio eso no es teórico: el
primer párrafo de `## Decisión` de cada ADR se publica en `MEMORIA.md`, que es
lo primero que lee toda IA que entra (ADR-171, y la misma familia que costó una
ronda en ADR-176).

### De dónde salió mi error, que es lo que de verdad hay que arreglar

No lo inventé: **las dos filas de §11.1 decían «EJECUCIÓN PENDIENTE»** mientras
§13.2, en el mismo documento, decía que ADR-163 la había ejecutado. El contrato
se contradecía a sí mismo desde ADR-163, y yo copié la mitad equivocada de la
fila que estaba editando.

Es la misma familia que este ADR arregla -dos sitios que hablan del mismo hecho
y divergen-, así que se cierra igual, **derivando del dato**: las dos filas
dicen ahora «CARRIL RETIRADO … EJECUTADO por ADR-163», y dos guardas nuevas lo
sostienen contra `carriles_retirados.json`, que §13.2 declara fuente de verdad.

| Mutación | Pruebas que caen |
|---|---|
| Una fila del contrato vuelve a dar la retirada por pendiente | 1: la del texto contra el registro |
| Alguien saca investigación de la vía GitHub, que es lo que el texto erróneo invitaba a hacer | **6** |
| …y además la quita del despachador, para que la atadura no lo tape | **5**, entre ellas la de §13.2 |

La tercera es la que justifica la guarda nueva: quitando la clase de los **dos**
sitios a la vez, las dos tablas vuelven a coincidir y la atadura de arriba se
queda callada. Lo que no se calla es §13.2.

## Alternativas descartadas y por qué

Las cuatro opciones de arriba, con su razón cada una. Y una quinta: **dejar
la tabla como estaba y cambiar solo el contrato** para que dijera «motor».
Descartada porque sería escribir en el contrato lo que el código hace por
error: quince encargos gobernados por una incidencia con la que el motor no
se comparaba nunca.

## La lección

- familia: `lista-a-mano`
- sin esto se repetiría: escribir dos veces «qué clases existen en la vía GitHub» -una tabla que decide y una copia que se queda vieja- y comprobar la copia en vez de la relación; es la familia que ADR-033 nombró, y aquí dejó quince encargos sin medir durante dos semanas.
- lo hace cumplir: `tests/engine/test_authority.py`
