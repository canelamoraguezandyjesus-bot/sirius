# Evidencia — el identificador de un defecto no puede seguir eligiéndose

Rama `mejora/el-identificador-de-defecto-no-se-escribe-a-mano`, 14-09-2026. Las
cuatro preguntas y el criterio de parada están en
`docs/audits/arranque-el-identificador-de-defecto-no-se-escribe-a-mano.md`,
confirmadas antes del primer commit de código.

## La afirmación

El identificador `H-N` se elige leyendo el máximo que hay y sumando uno. Dos
ramas abiertas a la vez leen cada una su propio árbol, las dos aciertan, y las
dos escriben el mismo número. No hay descuido: **el dato que se consulta no
incluye lo que la otra rama está haciendo**.

## La comprobación: tres colisiones en una noche

| Cuándo | Quién chocó con quién | Cómo se vio |
|---|---|---|
| 13-09 ~16:28 | `H-38`: ADR-184 (#602) y ADR-185 (#604) | al traer `main` a la rama de #602 |
| 13-09 ~16:28 | `H-39`: ADR-184 (#602) y ADR-187 (#611) | **`main` en rojo** tras la segunda fusión |
| 14-09 ~03:30 | `H-43`: ADR-191 (#622) y ADR-190 (#620) | la segunda rama aún sin fusionar |

La tercera ocurrió **mientras se escribía el ADR de la cola**. Vale la pena
decirlo porque separa las dos cosas: la cola pone las ramas en fila para
fusionar, pero **dos ramas pueden coger el mismo número aunque se fusionen una
detrás de otra**. Son defectos distintos y hacen falta los dos arreglos.

Es el mismo modo en que nacieron los **dos ADR-016** del registro de decisiones,
que la skill `adr` describe explícitamente como lo que su guion **no** cierra:
«solo ve el árbol local; dos ramas abiertas a la vez sobre el mismo `main` pueden
obtener ambas el mismo número».

## La medida que decide la forma — y que refuta mi propia nota de arranque

La nota de arranque proponía dos formas: derivar el identificador de la
**incidencia** o del **ADR**, «que ya son únicos». La medida dice que ninguna de
las dos sirve tal cual.

Sobre las 43 entradas de `docs/audits/registro_defectos.yml` en `0019c730`:

| | |
|---|---|
| Entradas totales | 43 |
| Con campo `incidencia` | 30 |
| Con campo `adr` | 11 |
| Con los dos | 10 |
| Solo `incidencia` | 20 |
| Solo `adr` | 1 |
| **Sin ninguno de los dos** | **12** |

Las doce: `H-1`…`H-9`, `H-12`, `H-15`, `H-24`. Son las más antiguas, de antes de
que el motor creara una incidencia por encargo.

**Qué queda descartado con esto:**

- **Derivar de la incidencia, sin más**, no puede aplicarse a 12 entradas
  existentes. El criterio de parada dice que no se renumera el pasado, así que la
  forma tiene que convivir con identificadores viejos que no se derivan de nada.
- **Derivar del ADR** hereda además un defecto conocido: el número de ADR **sí ha
  chocado** —los dos ADR-016—, así que cambiaría una colisión por otra. ADR-180
  estrechó esa ventana consultando las ramas del remoto, y esa mejora funcionó
  esta misma noche (el guion se saltó ADR-190 porque estaba cogido en una rama
  sin fusionar), pero estrechar una ventana no es cerrarla, y el criterio de
  parada de esta rama exige **imposible, no improbable**.

**Lo que la medida NO dice**, y hace falta antes de decidir: si toda entrada
**nueva** trae incidencia. Las 12 sin ella son todas antiguas, pero «todas las
recientes la traen» no es lo mismo que «ninguna futura puede no traerla», y esa
diferencia es justo la que separa una regla de una costumbre. Se mide antes de
elegir la forma.

## Lo que NO queda demostrado

- **Las tres colisiones son de una sola noche.** No se ha recorrido la historia
  del registro para contar cuántas hubo antes; tres en doce horas basta para
  decidir que hay que arreglarlo, pero no para afirmar una frecuencia.
- **No se ha comprobado el coste de cada colisión.** Dos de las tres se
  arreglaron renumerando en minutos; la segunda dejó `main` en rojo y costó una
  PR entera (#618 y su predecesora #617, cerrada por obsoleta). Eso es una
  observación, no una medida.
- **La forma todavía no está elegida.** Esta nota descarta dos candidatas y dice
  qué falta medir; la decisión va en su ADR.

## La segunda medida: la incidencia tampoco sirve, y por dos motivos

La nota de arranque dejaba pendiente medir si toda entrada **nueva** trae
incidencia. Se midió sobre las 20 últimas entradas, y el resultado descarta la
incidencia por dos razones distintas, ninguna de las cuales estaba prevista:

**Uno. La incidencia no es única por defecto.** Siete entradas —`H-26` a
`H-32`— declaran la **misma** incidencia, la #396. Y dos más, `H-40` y `H-43`,
declaran las dos la #608, cada una en una rama distinta. Así que `H-<incidencia>`
no solo no resuelve la colisión: la **provoca** en un caso que hoy no la tiene.

**Dos. Tampoco está siempre.** `H-35` es reciente —de la tanda de ADR-178— y no
tiene incidencia; tiene ADR. Así que «toda entrada nueva trae incidencia» es
falso, y con un contraejemplo de esta misma semana.

**Lo que sí está siempre desde ADR-182:** el campo `adr`. De las once entradas
desde `H-33` —que es cuando la guarda de ADR-182 empezó a exigirlo— **las once lo
tienen**, incluida la que no tiene incidencia. Las nueve anteriores no lo tienen,
y son justamente las de antes de esa guarda.

| Entrada | incidencia | adr |
|---|---|---|
| H-33 … H-43 | 10 de 11 | **11 de 11** |
| H-24 … H-32 | 8 de 9 | 0 de 9 |

## Lo que esto deja sobre la mesa

Queda una sola candidata con sentido: **que el identificador del defecto sea su
ADR**, en vez de un segundo número paralelo. Dicho de otra forma: **dejar de
tener dos sistemas de numeración** y quedarse con el que ya está coordinado.

A favor:

- El número de ADR **sí se coordina entre ramas** desde ADR-180: el guion
  consulta las ramas del remoto y se salta los números cogidos. Funcionó esta
  misma noche —se saltó el 190 porque estaba cogido en una rama sin fusionar—.
  El `H-N`, en cambio, no lo coordina nadie.
- Hay **una** guarda de unicidad que mantener en vez de dos
  (`test_registro_de_decisiones.py` ya falla si dos ADR comparten número).
- La relación defecto↔ADR ya es obligatoria desde ADR-182, así que no se inventa
  ningún dato: se deja de duplicar uno.

En contra, y hay que decirlo:

- **No es «imposible», es «coordinado».** Los dos ADR-016 existen y demuestran
  que ese número ha chocado. Lo que cambia es que pasa a haber **un solo sitio**
  donde puede chocar, con un guion que lo coordina y una guarda que lo caza, en
  vez de dos sitios de los que uno no tiene ninguna de las dos cosas.
- El criterio de parada de esta rama pedía **imposible**. Esto no lo es, y no se
  va a vender como si lo fuera: lo honesto es decir que reduce dos namespaces a
  uno y que el que queda es el que ya tiene coordinación y guarda.

## Lo que falta comprobar antes de decidir

- **Si un ADR puede declarar más de un defecto.** Si puede, el identificador
  derivado del ADR necesita un desempate dentro del mismo ADR, y entonces vuelve
  a haber algo que elegir —aunque sea dentro de una sola rama, donde sí se ven
  los dos—. La guarda de ADR-182 sugiere una lección por ADR, pero eso hay que
  leerlo en el código, no suponerlo.
- **Qué pasa con las 32 entradas sin `adr`.** No se renumeran (criterio de
  parada), así que el formato tiene que admitir las dos formas a la vez, y la
  guarda tiene que saber cuál exigir a una entrada nueva.

## Las dos comprobaciones que faltaban, hechas

**¿Puede un ADR declarar más de un defecto?** Hoy no lo hace ninguno: **11 ADR
citados, 11 entradas**, uno a uno. Y la guarda de ADR-182 exige *al menos* una
entrada por ADR que declare lección, no *exactamente* una, así que la relación
uno-a-uno es una costumbre, no una regla. Se convierte en regla aquí, que es
justo lo que hace derivable el identificador.

**¿Qué pasa con las entradas sin `adr`?** Son 32 y no se tocan. No hace falta un
formato doble ni una lista de excepciones: **el identificador sigue siendo
`H-<número>`, y lo único que cambia es de dónde sale el número**. Los
identificadores históricos llegan hasta `H-43`; los ADR van por el 191. Como los
números de ADR ya están muy por encima del máximo histórico, `H-<adr>` no puede
chocar con ninguno de los viejos. Sin cambio de formato, sin dos formas
conviviendo, sin nada que recordar.

## La forma elegida

**El número de un defecto nuevo ES el número de su ADR.** `H-191` para el defecto
que declara ADR-191. Nadie elige nada: se copia un dato que la entrada ya está
obligada a declarar desde ADR-182.

**La frontera se escribe una vez y no crece.** La regla vale para toda entrada
cuyo `adr` sea mayor o igual que el ADR que introduce esta decisión. Es **una
constante**, no una lista de excepciones que alguien tenga que ampliar —esa es
justamente la familia `lista-a-mano` que este arreglo no debe reproducir—. Las
once entradas anteriores que tienen `adr` (`H-33`…`H-43`) se quedan como están:
renumerarlas rompería el vínculo con su commit de cierre, cuyo mensaje empieza
por `H-N: ` y que la guarda de ADR-080 lee.

**Lo que esto es y lo que no es**, otra vez y sin adornos: reduce **dos sistemas
de numeración a uno**, y el que queda es el único que tiene guion que lo coordina
entre ramas (ADR-180) y guarda que caza los repetidos
(`test_registro_de_decisiones.py`). No es imposible —los dos ADR-016 demuestran
que ese número ha chocado— pero pasa a haber **un solo sitio donde puede chocar**
en vez de dos, y ese sitio es el que sí está defendido.
