# ADR-177 — La guarda de piezas sin llamante deriva su inventario del codigo del motor

- Estado: PROPUESTO
- Fecha: 2026-09-12
- Aprobación: la fusión de la PR por el propietario

## Nota de arranque (escrita ANTES de tocar el código de la guarda)

### El fallo, medido antes de escribir esta nota

`tests/automation/test_piezas_con_llamante.py` vigila la familia «pieza correcta
sin lector». Lo hace sobre un diccionario escrito a mano, `PIEZAS`, con **cuatro
nombres de módulo**: `authority_reversion`, `seven_day_streak`,
`projection_verifier` y `supervisor`.

La octava aparición de la familia no la vio, y no podía verla. ADR-173 la
encontró a mano:

```
$ grep -rn "cerrada" src/sirius_engine/reflect.py   → sin coincidencias
$ grep -rln "\.cerrada\b" src/ scripts/             → sin coincidencias
```

`MirroredWorkItem.cerrada` (`src/sirius_engine/domain/mirror.py:249`) es un
**campo de un dataclass**, no un módulo. `mirror_projection.py:926` lo **escribe**
—`cerrada=metadatos.metadatos.estado_gh == "closed"`— y nadie lo **leía**. Una
guarda cuya cobertura es un dato de entrada escrito a mano no puede ver lo que
no se escribió en ella, y en esa lista no cabía siquiera la forma de la pieza:
las cuatro entradas son nombres de módulo.

**La medida, sobre el árbol de `9efaa3c`** (el guion está en la sección
«Comprobación que la sostiene»):

| | piezas |
|---|---|
| entran hoy por la lista a mano | **4** (4 módulos, 0 definiciones, 0 campos) |
| módulos públicos del motor | 75 |
| entrarían derivadas del código | **826** — 75 módulos, 354 definiciones públicas de nivel superior, 397 campos anotados públicos |
| de esas 826, hoy **sin llamante en producción** | **36** — 7 módulos, 17 definiciones, 12 campos |

La lista a mano cubre el **5,3 %** de los módulos del motor y el **0,48 %** de
sus piezas públicas. Y de las 36 piezas que hoy están sin llamante, la lista a
mano no vigila ninguna: las cuatro que vigila están todas vivas.

### 1. ¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo OBSERVAR el fallo?

El fallo vive en la **dirección** de `PIEZAS`: es una entrada, y una guarda no
puede descubrir nada por una entrada que alguien tiene que acordarse de
rellenar. El arreglo va al mismo fichero y la invierte: el inventario se
**deriva** recorriendo `src/sirius_engine` con `ast`, y lo escrito a mano pasa a
ser la lista de **excepciones** —lo que se resta, no lo que se suma—.

**Sí puede observar el fallo, y por eso este arreglo es posible:** las dos
mitades del caso `cerrada` están en el mismo árbol que la guarda ya recorre. La
pieza es un nodo `AnnAssign` dentro de un `ClassDef` de `domain/mirror.py`; el
lector que le faltaba sería un `ast.Attribute` en `src/` o `scripts/`. No hace
falta ninguna fuente nueva, ni ejecutar el motor, ni recordar nada de otra
pasada.

Y hay una distinción que es el centro del caso: **escribir un campo no es
leerlo**. `cerrada=...` en el constructor de `mirror_projection.py` es un
argumento con nombre, no una lectura; si la guarda lo contara, `cerrada` habría
parecido viva justo en el sitio donde estaba muerta. La derivación cuenta
lecturas de atributo (`ast.Attribute` en contexto `Load`) y no cuenta `keyword`.

### 2. ¿Qué NO va a garantizar esto?

Escrito antes, no como excusa después:

- **No garantiza que la pieza se EJECUTE.** Comprueba que alguien la **nombre**
  en producción —la importe, la llame, le lea el atributo—, no que ese camino se
  recorra en un run real. Un llamante que a su vez está muerto sigue contando
  como llamante. Es la misma renuncia que ya tenía la guarda vieja; lo que
  cambia es a cuántas piezas se aplica.
- **No ve las piezas que no son públicas ni de nivel superior.** Quedan fuera:
  los nombres con `_` delante, los métodos de instancia, los miembros de `Enum`
  y las claves de diccionario. La cobertura que gana está medida (826 de un
  total mayor), no es total.
- **No mira el paquete `sirius`**, solo `sirius_engine`. El objetivo dice «el
  paquete del motor» y esto no se extiende por iniciativa propia.
- **Confunde homónimos.** La derivación reconoce piezas por su identificador, y
  **84 identificadores del motor los comparten 274 piezas** (`estado` lo usan 15,
  `work_id` 13, `motivo` 10). Si dos piezas se llaman igual, el llamante de una
  vale por la otra: la guarda puede dar por viva una pieza muerta que comparte
  nombre con otra viva. Es un falso negativo, nunca un falso positivo, y esa es
  la dirección en la que una guarda debe equivocarse.
- **No decide qué hacer con las 36 piezas sin llamante que descubre.** Cablearlas
  o retirarlas es trabajo de otras incidencias —está fuera del alcance de
  WI-20260912-154847—. Aquí quedan declaradas como dato, con su razón escrita y
  la fecha en que se encontraron, y la guarda impide que la lista crezca en
  silencio.

### 3. Criterio de parada (decidido ANTES de ver ningún resultado de la guarda nueva)

- **Si alguna de las mutaciones sembradas no pone la guarda en rojo, paro y no
  la doy por buena.** Una guarda que no se ha visto fallar no es evidencia
  (ADR-001 §3), y esta familia ya ha producido cuatro guardianes vacuos en este
  repositorio —los que el docstring de `_sin_comentarios` enumera—.
- **Si para dejar la batería en verde hiciera falta declarar una excepción cuya
  razón no pueda escribir con una comprobación detrás, paro y emito
  `BLOCKED_BY_DECISION`.** Una lista de excepciones con razones inventadas es
  peor que la lista a mano de hoy: parece cobertura.
- **Si dos rondas seguidas trajeran defectos de la familia «el guardián se
  conforma con que algo esté NOMBRADO»**, dejo de parchear y busco la raíz
  (regla de las dos rondas, ADR-001 §2).

### 4. ¿Qué haría el fallo IMPOSIBLE en vez de improbable?

El fallo concreto —«la guarda no vio la pieza porque nadie la escribió en la
lista»— queda **imposible**: ya no hay lista de entrada que rellenar, y una
pieza pública nueva del motor entra en el inventario el día que se escribe.

Lo que queda **improbable y no imposible** es que una pieza se escape por la
puerta nueva, la de las excepciones, que sí se escribe a mano. Contra eso van
dos cierres mecánicos: una excepción que **ya tiene llamante** pone la batería
en rojo, para que se borre en cuanto sobra; y una excepción que **ya no
corresponde a ninguna pieza** también. Lo que ningún mecanismo puede impedir es
que alguien escriba una razón falsa; eso lo sostiene la revisión, no el código,
y así queda dicho.

## Contexto y problema

Una guarda cuya cobertura es un **dato de entrada** no descubre nada: confirma
lo que alguien se acordó de escribir en ella. `PIEZAS` eran cuatro nombres de
módulo, llevaba tres meses en verde y en ese tiempo no encontró ni un caso —las
cuatro piezas que vigilaba estaban vivas—. La octava aparición de la familia la
encontró una persona leyendo código para ADR-173.

## Criterio de parada (escrito ANTES de decidir)

El de la sección 3 de la nota de arranque, publicado en el commit `969f2c0`
antes de tocar el código de la guarda. Ninguna de las tres condiciones se
cumplió: las siete mutaciones sembradas pusieron la guarda en rojo, las 45
excepciones tienen detrás la comprobación que las sostiene, y no hubo dos rondas
con defectos de la misma familia.

## Opciones consideradas

1. **Ampliar la lista a mano** con `MirroredWorkItem.cerrada` y los casos que se
   vean. Arregla el síntoma y deja la enfermedad: la novena pieza tampoco
   estaría en la lista.
2. **Derivar el inventario del código y declarar las excepciones** (la elegida).
3. **Derivar y exigir alcanzabilidad real desde los puntos de entrada** (un
   grafo de llamadas). Mide lo que de verdad importa —que la pieza se ejecute—
   pero necesita resolver importaciones e indirecciones, y una guarda que se
   equivoca en falso se acaba silenciando. Descartada, con su motivo escrito
   abajo.

## Decisión

El inventario de `tests/automation/test_piezas_con_llamante.py` se **deriva** de
`src/sirius_engine` con `ast`, en tres formas de pieza: `modulo:`,
`definicion:` y `campo:`. Lo escrito a mano pasa a ser
`SIN_LLAMANTE_CONOCIDO`, lo que se **resta**.

Restar en vez de sumar es la mitad de la decisión, y es la que hace que esto no
vuelva a pasar: **a una lista de inclusión le puede faltar una entrada y sigue
verde; a una de exclusión que sobra se la ve.** Tres cierres lo sostienen: una
excepción que ya no corresponde a ninguna pieza pone la batería en rojo; una
excepción cuya pieza **ya tiene llamante** también, para que se borre en cuanto
sobra; y una excepción sin razón escrita, también.

Dos detalles de la derivación no son cosméticos:

- **Se lee el AST, no el texto.** Un nombre que solo aparece en un comentario o
  en un docstring no existe en el AST, así que no cuenta sin tener que recortar
  el texto a mano —y `annotate_observations` deja de confundirse con
  `annotate_observations_with_verdicts`, que una búsqueda por subcadena da por
  la misma—.
- **Escribir un campo no es leerlo.** Para las piezas `campo:` solo cuenta
  `ast.Attribute` en contexto `Load`. `mirror_projection.py:926` **escribe**
  `cerrada=...` como argumento con nombre; si eso contara, `cerrada` habría
  parecido viva justo en el sitio donde estaba muerta.

## Comprobación que la sostiene

### La medida: 4 piezas a mano contra 826 derivadas

Con el árbol de `9efaa3c` y el guion de derivación de la propia guarda:

| | piezas |
|---|---|
| lista a mano `PIEZAS` | **4** módulos, 0 definiciones, 0 campos |
| módulos públicos del motor | 75 |
| inventario derivado | **826** — 75 módulos, 354 definiciones, 397 campos |
| sin llamante en producción | **45** — 7 módulos, 17 definiciones, 21 campos |

La lista a mano cubría el **5,3 %** de los módulos y el **0,48 %** de las piezas
públicas, y ninguna de las cuatro estaba muerta: por eso no encontró nada en
tres meses. El inventario derivado corre en 2 s y la batería pasa de 5 pruebas a
923.

Las 45 piezas sin llamante son deuda que la derivación destapó, no un fallo
nuevo. Tres son dobles de sustitución que viven en `src/` a propósito; las otras
42 están muertas de verdad, y entre ellas hay dos que valen por sí solas:
`governance.registrar_gasto` —«la ÚNICA función de este bloque que actualiza el
gasto», dice su propio docstring, y no la llama ningún camino de producción— y
`memoria.problemas_de_la_leccion`, que ADR-174 declaró «la única definición de
qué es una lección bien declarada» y que hoy solo ejecuta su batería. Cablearlas
o retirarlas está fuera del alcance de WI-20260912-154847 y queda declarado con
su razón, pieza por pieza.

### Las mutaciones, sembradas y vistas caer

Siete, las dos primeras las que pedía el encargo. En las tres primeras se
comprueban **las dos direcciones** que exige ADR-001 §3: la guarda vieja pasa
con la mutación puesta y la nueva falla.

| # | mutación | guarda vieja | guarda nueva |
|---|---|---|---|
| M1 | quitar los tres lectores reales de `espejo.cerrada` (`reflect.py`, `tablero.py`, `reflect_cli.py`) | **5 passed** | **rojo** en `campo:domain.mirror.MirroredWorkItem.cerrada` y en `test_la_pieza_que_tumbo_la_guarda_esta_vigilada` |
| M2 | sembrar una pieza pública nueva sin llamante (módulo, clase y campo) | **5 passed** | **rojo** en las tres |
| M3 | nombrar esa pieza **solo** en un comentario y en un docstring de producción | **6 passed** con la pieza en su propia lista | **sigue en rojo** en las tres |
| M4 | declarar como excepción una pieza que sí tiene llamante (`modulo:supervisor`) | — | rojo en `test_ninguna_excepcion_sobra` |
| M5 | que el inventario deje de ver los campos | — | rojo en `test_el_inventario_se_deriva_y_no_esta_vacio` y en `test_la_pieza_que_tumbo_la_guarda_esta_vigilada` |
| M6 | declarar como excepción una pieza que no existe | — | rojo en `test_cada_excepcion_sigue_correspondiendo_a_una_pieza` |
| M7 | dejar una excepción sin razón escrita | — | rojo en `test_cada_excepcion_declara_su_razon` |

**M3 es la que mide lo que se ganó.** La guarda vieja, con la pieza sembrada
metida en su propio diccionario y nombrada únicamente en un docstring de
`cli.py`, pasó en verde: `_sin_comentarios` recortaba lo que va detrás de `#`,
pero un docstring es una cadena y sobrevivía al recorte. Es el defecto que su
propio docstring describía —«un guardián que se conforma con que algo esté
NOMBRADO no comprueba que esté LLAMADO»— sin haberlo cerrado del todo. Leer el
AST lo cierra de raíz: en el AST no hay comentarios, y un docstring es un
`Constant`, no un `Name`.

### Un falso hallazgo, escrito aquí para que nadie lo repita

A mitad de este trabajo di por roto `main`: cinco ficheros con `except A, B:`
—`openai_transcription.py:58`, `sqlite_backup_service.py:242`,
`context_recall.py:104`, esta misma guarda y `test_obs_websocket_backend.py:94`—
y un `ast.parse` que los rechazaba. Llegué a «repararlos» con paréntesis.

**No estaban rotos.** El proyecto declara `target-version = "py314"` y desde
PEP 758 esa forma es sintaxis válida; el `ruff format` del propio repositorio
quita los paréntesis por redundantes, y fue él quien deshizo el cambio. Lo que
fallaba era el intérprete con el que yo leía el árbol —un Python 3.12 del
sistema, no el del proyecto—. El commit quedó revertido y no hay ni una línea de
esos ficheros en esta rama.

Vale la pena dejarlo escrito porque la trampa es reincidente: **cualquier
herramienta que analice este árbol tiene que correr con el intérprete del
proyecto**, y esta guarda es una de ellas —lee el motor entero con `ast`—. Bajo
`uv run pytest` lo hace; leído a mano con otro Python, no.

## Consecuencias

- La familia «pieza sin lector» tiene por primera vez un detector que **encuentra
  casos nuevos** en vez de confirmar los viejos: hoy encontró 42 piezas muertas
  de verdad, entre ellas dos que dos ADR distintos daban por cableadas.
- Una pieza pública nueva del motor **nace vigilada**. Quien la escriba sin
  cablearla tendrá que cablearla, retirarla, o declararla con su razón.
- La deuda queda contada y con fecha. Las 45 entradas de
  `SIN_LLAMANTE_CONOCIDO` son un inventario que se puede vaciar por incidencias,
  y cada vez que se cablea una, la batería exige borrar su entrada.
- La batería pasa de 5 a 923 casos y tarda 2 s. El coste es real y está medido.
- Lo que sigue sin cubrirse está en la sección 2 de la nota de arranque: no se
  mira el paquete `sirius`, no se ven los métodos ni los miembros de `Enum`, y
  84 identificadores homónimos pueden dar por viva una pieza muerta. Son falsos
  negativos, nunca falsos positivos.

## Alternativas descartadas y por qué

- **Ampliar la lista a mano.** Deja la enfermedad intacta: la novena pieza
  tampoco estaría escrita.
- **Exigir alcanzabilidad real desde los puntos de entrada.** Mide lo que de
  verdad importa, pero necesita resolver importaciones, indirecciones y
  despachos por tabla; un grafo incompleto produce falsos positivos, y una
  guarda que grita en falso se acaba ignorando —es la decisión de diseño que
  `test_citas_de_los_adr.py` ya tomó y ADR-052 dejó escrita—. Queda como
  siguiente paso posible, no como este.
- **Sacar el detector a producción**, como hizo ADR-174 con
  `problemas_de_la_leccion`. Allí hacía falta porque el detector lo usan dos
  cosas —la vista de `MEMORIA.md` y las pruebas— y una guardia que no ejecuta el
  detector que dice probar no prueba nada (ADR-172). Aquí no hay segundo
  consumidor, así que sacarlo solo añadiría una pieza pública más... que, por
  cierto, esta misma batería exigiría cablear.

## La lección

- familia: `regla-que-depende-de-que-alguien-se-acuerde`
- sin esto se repetiría: escribir un guardián sobre una lista de inclusión
  rellenada a mano, que solo puede confirmar lo que alguien recordó meter en
  ella y por eso nunca encuentra el caso nuevo.
- lo hace cumplir: `tests/automation/test_piezas_con_llamante.py`
