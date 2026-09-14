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
