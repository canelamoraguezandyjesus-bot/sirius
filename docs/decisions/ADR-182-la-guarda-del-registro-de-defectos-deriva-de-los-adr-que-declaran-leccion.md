# ADR-182 — La guarda del registro de defectos deriva de los ADR que declaran leccion

- Estado: PROPUESTO
- Fecha: 2026-09-13
- Aprobación: la fusión de la PR por el propietario

## Nota de arranque (escrita ANTES de contar nada y ANTES de tocar la guarda)

### El fallo, medido antes de escribir esta nota

`docs/audits/registro_defectos.yml` lleva sin una entrada nueva desde el
31-08-2026 (`5cc3f18`) y desde entonces han entrado a `main` los ADR 116 a 180:
cero defectos registrados. ADR-174 midió esa sequía y la dejó **fuera de
alcance por escrito** —«que lleve desde el 31-08 sin una entrada es un problema
suyo, y no lo arregla este ADR»—. Este ADR es ese problema, y no vuelve a
medirlo.

**La raíz no es la sequía: es que nada la puede ver.** Las ocho comprobaciones
de `tests/automation/test_registro_de_defectos.py` verifican la **coherencia de
lo ya escrito** —que no haya identificadores repetidos, que los ficheros
citados existan, que un abierto tenga incidencia, que un cerrado diga su commit
de cierre— y **ninguna pregunta si lo que pasó se escribió**. Por eso llevan
doce días y 61 ADR en verde sobre un registro dormido.

Las dos consecuencias, reproducidas en este árbol (`673b2f4`, el head de `main`)
antes de decidir nada:

```
$ uv run python -c "import yaml,pathlib,collections; d=yaml.safe_load(
    pathlib.Path('docs/audits/registro_defectos.yml').read_text('utf-8'))['defectos'];
    print(len(d), collections.Counter(x['estado'] for x in d))"
32 Counter({'cerrado': 32})

$ uv run pytest tests/automation/test_registro_de_defectos.py -q -rs
39 passed, 1 skipped in 0.17s
SKIPPED [1] ...:245: este árbol no deja leer la historia de `main` ...
```

1. **Los 32 defectos están cerrados.** Así que
   `test_todo_defecto_abierto_tiene_una_incidencia_que_lo_siga` —documentado
   como «el corazón de la prueba»— filtra por `estado == "abierto"`, se queda
   con la lista vacía y asevera `[] == []`. Está verde en vacío desde que se
   cerró el último defecto, y lo seguiría estando con el registro dormido para
   siempre.
2. **Una de las ocho no llega ni a correr en CI.**
   `test_ningun_defecto_abierto_tiene_ya_su_arreglo_en_main` se salta donde el
   clon es superficial, que es exactamente Quality (y este runner: `git
   rev-list --count HEAD` → `1`). ADR-080 lo dejó escrito y este ADR no lo
   cambia; lo apunta porque estrecha aún más el cerco: de ocho comprobaciones,
   una no corre y otra asevera sobre el vacío.

Es la **tercera aparición** de la familia `regla-que-depende-de-que-alguien-se-
acuerde`, que la vista de lecciones de `MEMORIA.md` cuenta hoy en 2 (ADR-174 y
ADR-179) y es la única familia repetida. ADR-001 §2 manda parar y buscar la
raíz cuando una familia va por la segunda.

### El criterio de «un ADR corrige un defecto», declarado ANTES de contar

Mide primero y decide después. Se cuentan **tres** señales candidatas sobre los
ADR 116 a 180, y las tres se declaran aquí antes de ejecutar el conteo:

- **(A) Declara una lección con `familia:`.** No es un criterio inventado para
  esta guarda: es la definición que el repositorio **ya tiene**. ADR-174 fijó
  que una lección se escribe *solo si sin ella alguien repetiría el error*, y
  «repetir un error» es exactamente un defecto. La emite el propio árbol de
  forma mecánica y ya comprobada —`sirius_engine.memoria.leer_leccion`,
  `problemas_de_la_leccion`, `tests/automation/test_mina_de_lecciones.py`— y no
  necesita git.
- **(B) El texto del ADR nombra un identificador `H-N` que está en el
  registro.** Es la señal que uniría los dos documentos sin tocar ninguno.
- **(C) Declara una lección con `familia:` **y** una prueba que la hace
  cumplir** (`lo hace cumplir:` apuntando a un fichero de `tests/`). Subconjunto
  de (A): las lecciones que ya llegaron a código.

Y se declara también **qué haría descartar cada una**: una señal sirve para
derivar la guarda si (i) sale del propio repositorio y no de una lista que
alguien rellena, (ii) se puede leer sin la historia de git —porque en Quality no
la hay—, y (iii) el conjunto que produce **no está vacío hoy**, porque una
guarda sobre un conjunto vacío es justo el fallo que este ADR viene a cerrar.

### 1. ¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo OBSERVAR el fallo?

El fallo vive en la **dirección** de las ocho comprobaciones: todas leen el
registro y preguntan si lo escrito es coherente. Ninguna tiene una segunda
fuente contra la que contrastar, así que un registro vacío o dormido es, para
ellas, un registro perfecto.

El arreglo va al mismo fichero de pruebas y le da esa segunda fuente: el
inventario de «lo que pasó» se **deriva** de `docs/decisions/`, y lo escrito a
mano pasa a ser lo que se **resta** —las excepciones, con su razón al lado—. Es
la misma inversión que ADR-179 hizo con `PIEZAS`, y por el mismo motivo: *a una
lista de inclusión le puede faltar una entrada y sigue verde; a una de exclusión
que sobra se la ve.*

**Sí puede observar el fallo:** las dos mitades están en el árbol que la prueba
ya lee. El defecto declarado vive en el bloque `## La lección` de un fichero de
`docs/decisions/`, y su acuse de recibo vive en `docs/audits/registro_defectos.yml`.
No hace falta la red, ni la historia de git, ni ejecutar el motor —y eso es
justo lo que impide que esta guarda herede el salto de la comprobación 8—.

### 2. ¿Qué NO va a garantizar esto?

Escrito antes, no como excusa después:

- **No garantiza que el defecto registrado esté bien descrito.** Comprueba que
  cada ADR que declara haber corregido un defecto tenga una entrada que lo
  acuse, no que esa entrada diga la verdad. Eso lo sostiene la revisión.
- **No ve el defecto que no produjo ADR.** Un arreglo que se fusiona sin ADR no
  entra en el inventario derivado. El alcance de la señal es «lo que el
  repositorio declaró como lección», no «todo lo que se rompió».
- **Se le puede escapar por la puerta de `ninguna:`.** Un ADR puede declarar
  «este ADR no dejó ninguna lección» y quedarse fuera del inventario. Es una
  declaración escrita y falsable —`test_mina_de_lecciones.py` obliga a elegir
  entre una cosa y la otra, y a razonarla—, pero ningún mecanismo impide
  escribirla en falso.
- **No alcanza a los ADR anteriores a `PRIMER_ADR_CON_LECCION` (174).** Para
  ellos no hay bloque de lección que leer, y rellenárselo hoy sería escribir de
  memoria lo que en su día no se capturó, que es lo que ADR-174 declinó hacer
  a propósito.
- **No cierra el salto de la comprobación 8.** El clon superficial de Quality
  sigue dejando `test_ningun_defecto_abierto_tiene_ya_su_arreglo_en_main` sin
  correr; ADR-080 explica qué haría falta y está fuera del alcance de
  WI-20260913-000235. La guarda nueva no depende de git precisamente para no
  heredarlo.
- **No retira ni reescribe ninguna entrada histórica.** El registro conserva
  todo defecto pasado con su commit de cierre, y las cifras fechadas de ADR-174
  son evidencia y no se tocan.

### 3. Criterio de parada (decidido ANTES de ver ningún resultado del conteo ni de la guarda nueva)

- **Si la señal elegida produce hoy un conjunto vacío, paro y no la doy por
  buena.** Derivar un inventario vacío sería cambiar una prueba vacua por otra,
  que es exactamente el fallo que este ADR persigue.
- **Si alguna de las mutaciones sembradas no pone la guarda en rojo, paro y no
  la doy por buena.** Una guarda que no se ha visto fallar no es evidencia
  (ADR-001 §3).
- **Si para dejar la batería en verde hiciera falta declarar una excepción cuya
  razón no pueda escribir con una comprobación detrás, paro y emito
  `BLOCKED_BY_DECISION`.** Una lista de excepciones con razones inventadas
  parece cobertura y no lo es.
- **Si dos rondas seguidas trajeran defectos de la familia
  `regla-que-depende-de-que-alguien-se-acuerde`, dejo de parchear y busco la
  raíz** (regla de las dos rondas, ADR-001 §2).

### 4. ¿Qué haría el fallo IMPOSIBLE en vez de improbable?

El fallo concreto —«el registro se queda dormido y ninguna prueba lo nota»—
queda **imposible** para lo que el repositorio declara: el día en que un ADR
declare una lección sin que el registro acuse su defecto, la batería se pone en
rojo. No hay lista de inclusión que rellenar y no hay conjunto vacío sobre el
que aseverar: el inventario nace del árbol.

Lo que queda **improbable y no imposible** es escaparse por las dos puertas de
la sección 2: declarar `ninguna:` en falso, o arreglar algo sin ADR. Contra la
primera va `test_mina_de_lecciones.py`, que obliga a escribir la razón; contra
la segunda no va nada mecánico, y así queda dicho.

## Contexto y problema

Un registro puede morir de dos maneras y este repositorio solo vigilaba una.
Puede **pudrirse** —un defecto abierto sin incidencia, una ruta que ya no
existe, una fila borrada en vez de cerrada—, y contra eso hay ocho
comprobaciones desde el 21-08-2026. Y puede **dormirse**: seguir siendo
perfectamente coherente y dejar de recibir lo que pasa. Contra eso no había
nada, porque las ocho leen el registro y solo el registro: sin una segunda
fuente, un registro dormido es indistinguible de un repositorio sin defectos.

## Criterio de parada (escrito ANTES de decidir)

El de la sección 3 de la nota de arranque, publicado en el commit `738298b`
antes de contar nada y antes de tocar la guarda. Ninguna de las cuatro
condiciones se cumplió: la señal elegida produce hoy seis ADR y no un conjunto
vacío, las ocho mutaciones sembradas pusieron la guarda en rojo, las cinco
excepciones tienen detrás una comprobación que las sostiene, y no hubo dos
rondas con defectos de la misma familia.

## Opciones consideradas

Las tres señales candidatas de la nota de arranque, ya contadas (la medida está
abajo):

1. **(A) El ADR declara una lección con `familia:`** — 5 de los 62 ADR del
   rango. La elegida.
2. **(B) El ADR nombra un `H-N` que está en el registro** — 4 de 62.
3. **(C) (A) y además una prueba que la hace cumplir** — 5 de 62, exactamente
   los mismos que (A).

## Decisión

La guarda del registro de defectos gana una segunda mitad, y esa mitad **deriva
su inventario de `docs/decisions/`**: un ADR que declara una lección con
`familia:` declara, por la definición que ADR-174 ya fijó —una lección se
escribe *solo si sin ella alguien repetiría el error*—, que algo mordió. El
registro tiene que acusarlo con una entrada que diga `adr: <número>`.

Lo escrito a mano es `SIN_DEFECTO_REGISTRADO`: **lo que se resta**, con su
razón al lado. Restar en vez de sumar es la mitad de la decisión, y es la que
hace que esto no vuelva a pasar: *a una lista de inclusión le puede faltar una
entrada y sigue verde; a una de exclusión que sobra se la ve.* Es la misma
inversión que ADR-179 hizo con `PIEZAS`, aplicada a la tercera aparición de la
misma familia.

Cuatro cierres mecánicos la sostienen:

- una excepción para un ADR que **ya no existe o ya no declara lección** pone la
  batería en rojo;
- una excepción para un ADR que el registro **ya acusa** también, para que se
  borre en cuanto sobra;
- una excepción **sin razón escrita** también;
- y —el que cierra la salida fácil— **si ningún ADR del inventario derivado
  MENOS las excepciones está acusado por el registro**, rojo. La resta es la
  parte que lo cierra: aseverar sobre «cualquier campo `adr`» dejaba la salida
  abierta —eximir uno a uno los ADR con lección, con una entrada histórica
  sosteniendo el verde— y la corrección del 13-09-2026 la tapó midiendo contra
  el inventario vivo (`_inventario_vivo_que_el_registro_acusa`). La
  intersección con el inventario cierra además la otra mitad: un acuse que
  apunta fuera de él (`adr: 1`) ya no sostiene la guarda.

Tres detalles no son cosméticos:

- **`adr` es un campo opcional y solo de las entradas nuevas.** Ninguna de las
  32 entradas anteriores se retira ni se reescribe: el registro conserva todo
  defecto pasado con su commit de cierre, y las cifras fechadas de ADR-174 son
  evidencia y no se tocan.
- **No se toca git.** La comprobación que sí lo toca
  (`test_ningun_defecto_abierto_tiene_ya_su_arreglo_en_main`) no llega a correr
  en Quality; esta lee dos ficheros del árbol y corre en todas partes.
- **La anti-vacua del corazón no exige que haya defectos abiertos.** Que todos
  estén cerrados es un estado sano, no un fallo. Lo que exige es que el
  criterio siga distinguiendo, y para eso lo ejerce sobre defectos sembrados en
  la propia prueba.

## Comprobación que la sostiene

### La medida: tres señales contadas después de declararlas

Con el criterio publicado en `738298b` y ejecutado sobre el árbol de `673b2f4`,
sobre los **62** ADR distintos que el rango 116–180 tiene en `docs/decisions/`
(el encargo dice 61; la diferencia son los huecos 165, 177 y 178, que no
existen, y el conteo por ficheros presentes da 62):

| señal | ADR que la cumplen | cuáles |
|---|---|---|
| (A) declara lección con `familia:` | **5** | 174, 175, 176, 179, 180 |
| (B) nombra un `H-N` del registro | **4** | 118, 136, 145, 154 |
| (C) (A) + prueba que la hace cumplir | **5** | 174, 175, 176, 179, 180 |

**Por qué (B) queda descartada, y no por poco: es circular.** Solo encuentra
ADR que ya nombran un defecto **que ya está en el registro**, así que por
construcción no puede exigir jamás una entrada nueva. Como guarda contra un
registro dormido vale exactamente cero: los cuatro que caza —118, 136, 145,
154— citan H-14, H-23, H-25 y H-28, todos escritos ya. Y encima es la señal por
mención, que es el falso positivo que ADR-080 descartó midiendo en esta misma
familia de ficheros.

**(C) no aporta nada sobre (A):** hoy produce el mismo conjunto, y añade una
condición que responde a otra pregunta —si la lección llegó a código—, no a la
que aquí se hace. Se queda (A), que además es la única de las tres que cumple
las tres condiciones declaradas: sale del árbol, se lee sin git y produce un
conjunto no vacío.

**Estado del registro y de la guarda vieja, medido en el mismo árbol:**

```
$ ... print(len(d), collections.Counter(x['estado'] for x in d))
32 Counter({'cerrado': 32})
$ uv run pytest tests/automation/test_registro_de_defectos.py -q -rs
39 passed, 1 skipped in 0.17s
$ git rev-list --count HEAD
1
```

### Lo que este ADR deja escrito en el registro

`H-33`, la primera entrada desde el 31-08-2026: «el registro de defectos podía
quedarse dormido sin que ninguna comprobación lo notara», con `adr: 182` y
`incidencia: 597`. Queda en `abierto` a propósito: mientras esta PR no se
fusione, el defecto **sigue vivo en `main`**, y escribir `cerrado` con un
`cerrado_por` que todavía no existe sería exactamente la clase de dato de
memoria que este ADR se niega a producir. Como efecto secundario, el corazón de
la prueba deja de aseverar sobre el conjunto vacío también con los datos reales.

Los otros cinco ADR con lección quedan en `SIN_DEFECTO_REGISTRADO`, uno a uno y
con su razón. No se registran retroactivamente por el mismo motivo por el que
ADR-174 no rellenó los anteriores a él —sería escribir hoy, de memoria, lo que
en su día no se capturó— y por un impedimento medido: su `cerrado_por` es un
commit de `main` que este árbol no tiene.

### Las mutaciones, sembradas y vistas caer

Nueve. En dos de ellas se comprueban **las dos direcciones** que exige ADR-001
§3: la guarda vieja pasa con la mutación puesta y la nueva falla.

| # | mutación | guarda vieja | guarda nueva |
|---|---|---|---|
| M1 | quitar `adr: 182` de `H-33`: ADR-182 declara lección y el registro no lo acusa | **40 passed** | **rojo** en `test_todo_adr_que_declara_un_defecto_deja_su_entrada_en_el_registro` y en `test_al_menos_un_defecto_acusa_el_adr_que_lo_corrigio` |
| M2 | eximir a ADR-182, que el registro **sí** acusa | — | rojo en `test_ninguna_excepcion_sobra[ADR-182]` |
| M3 | eximir a un ADR que no existe (999) | — | rojo en `test_cada_excepcion_sigue_correspondiendo_a_un_adr_que_declara_un_defecto[ADR-999]` |
| M4 | dejar una excepción sin razón escrita | — | rojo en `test_cada_excepcion_declara_su_razon[ADR-180]` |
| M5 | que una entrada acuse un ADR inventado (`adr: 999`) | — | rojo en `test_el_adr_que_un_defecto_acusa_existe_de_verdad` |
| M6 | que la derivación deje de ver `familia:` | — | rojo en 6, empezando por `test_el_inventario_de_adr_con_defecto_se_deriva_y_no_esta_vacio` |
| M7 | aflojar el criterio del corazón **y** dejar el registro sin ningún abierto | **39 passed** | **rojo** en `test_el_criterio_del_corazon_muerde_aunque_no_haya_ningun_abierto` |
| M8 | eximir **todos** los ADR del inventario **y** hacer que `H-33` acuse a un ADR ajeno a él (`adr: 1`): la salida fácil ante un rojo, sin que `test_ninguna_excepcion_sobra` la delate | **verde**: la aserción original solo pedía que existiera algún campo `adr` | **rojo** en `test_al_menos_un_defecto_acusa_el_adr_que_lo_corrigio`, y solo ahí (`1 failed, 62 passed, 1 skipped`) |
| M9 | estrechar el patrón de nombre a `\d{3}` exactos, que es como estaba escrito | — | **rojo** en `test_los_lectores_de_adr_ven_un_numero_de_cuatro_cifras`: «el patrón de nombre no reconoce ADR-1000-…» |

**M8 se sembró dos veces, y la primera no cayó.** Tal como se escribió al
principio, esta comprobación aseveraba que `_acuses_del_registro()` no estuviera
vacío, y esa función solo lee `docs/audits/registro_defectos.yml`: eximir ADR no
la tocaba, así que la salida por exclusión seguía abierta y el verde lo sostenía
una entrada histórica. Lo vio la revisión de la ronda 1 (CLAUDE-REV-597-001,
CODEX-001). La aserción se midió ahora contra el inventario derivado menos las
excepciones, y con eso la mutación de la fila M8 sí cae. La columna «guarda
vieja» de esa fila es la aserción anterior a la corrección, no la batería de
antes de este ADR.

**M1 y M7 son las que miden lo que se ganó.** En M1 la guarda vieja pasa entera
—40 passed— con un ADR que dice haber corregido un defecto y un registro que no
lo menciona: es la sequía, reproducida en pequeño. En M7 el criterio del corazón
se afloja hasta invertirse y la guarda vieja sigue verde —39 passed— porque con
los 32 defectos cerrados filtra sobre el vacío y no llega a ejercerlo; la
anti-vacua nueva lo caza sin depender de cómo esté el registro.

### La batería completa

`uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src tests` y
`uv run pytest` en verde sobre esta rama: **6410 passed, 17 skipped, 2 xfailed**
en 9 min 50 s. La guarda de este fichero pasa de 40 a 63 casos y sigue costando
milisegundos.

## Consecuencias

- **El registro no puede volver a dormirse en silencio.** El día en que un ADR
  declare una lección sin que el registro acuse su defecto, la batería se pone
  en rojo. Es la primera comprobación de este fichero que pregunta si lo que
  pasó se escribió.
- **El registro se despierta**: `H-33` es la primera entrada en trece días.
- **La deuda queda contada y con fecha**: cinco ADR con lección y sin entrada,
  uno a uno y con su razón, en vez de una sequía que nadie mide.
- **Un defecto nuevo cuesta una línea más**, el `adr:`. A cambio, los dos
  documentos dejan de poder contradecirse en silencio.
- **La guarda no depende de git**, así que corre entera en Quality —a
  diferencia de la comprobación 8, que sigue saltándose ahí—.
- Lo que sigue sin cubrirse está en la sección 2 de la nota de arranque, y hay
  dos puertas abiertas que conviene no olvidar: un ADR puede declarar
  `ninguna:` y quedarse fuera del inventario, y un arreglo sin ADR no entra en
  él. La primera la sostiene `test_mina_de_lecciones.py`, que obliga a escribir
  la razón; la segunda no la sostiene nada mecánico.

## Alternativas descartadas y por qué

- **Exigir que el registro reciba una entrada cada N días.** Mide el reloj, no
  el trabajo: en una semana sin defectos obligaría a inventar uno, y esa es la
  forma más rápida de que un registro deje de significar algo.
- **Derivar la señal de las menciones `H-N` en los ADR (opción B).** Circular,
  como está medido arriba: solo ve defectos ya escritos, así que nunca puede
  pedir una entrada nueva. Y es la señal por mención que ADR-080 ya descartó.
- **Registrar retroactivamente los cinco ADR con lección.** Sería escribir hoy,
  de memoria, lo que en su día no se capturó —lo que ADR-174 declinó hacer con
  los ADR anteriores a él—, y además su `cerrado_por` no está en este árbol.
  Quedan declarados como excepción, con su razón y su fecha, que es un dato
  verdadero en vez de uno reconstruido.
- **Exigir que el conjunto de defectos abiertos no esté vacío**, como anti-vacua
  del corazón. Es falso como criterio: que todo defecto conocido esté cerrado es
  el estado sano. Lo que hay que impedir es que el criterio deje de morder, y
  eso se comprueba ejerciéndolo sobre defectos sembrados.
- **Arreglar de paso el salto de la comprobación 8** en el clon superficial de
  Quality. ADR-080 explica qué haría falta y está fuera del alcance de
  WI-20260913-000235; la guarda nueva evita el problema no dependiendo de git.

## La lección

- familia: `regla-que-depende-de-que-alguien-se-acuerde`
- sin esto se repetiría: poner a vigilar un registro con comprobaciones que solo miran la coherencia de lo ya escrito; el registro deja de recibir lo que pasa, ninguna de ellas puede notarlo y el verde lo confirma —aquí fueron doce días y 61 ADR sin una entrada.
- lo hace cumplir: `tests/automation/test_registro_de_defectos.py`
