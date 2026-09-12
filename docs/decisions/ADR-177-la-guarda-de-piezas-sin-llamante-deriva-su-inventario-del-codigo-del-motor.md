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

Pendiente de completar al cerrar el trabajo.

## Criterio de parada (escrito ANTES de decidir)

El de la sección 3 de la nota de arranque.

## Opciones consideradas

Pendiente de completar al cerrar el trabajo.

## Decisión

Pendiente de completar al cerrar el trabajo.

## Comprobación que la sostiene

Pendiente de completar al cerrar el trabajo.

## Consecuencias

Pendiente de completar al cerrar el trabajo.

## Alternativas descartadas y por qué

Pendiente de completar al cerrar el trabajo.

## La lección

Pendiente de completar al cerrar el trabajo.
