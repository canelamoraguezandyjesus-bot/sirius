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

## Criterio de parada (escrito ANTES de decidir)

## Opciones consideradas

## Decisión

## Comprobación que la sostiene

## Consecuencias

## Alternativas descartadas y por qué

## La lección
