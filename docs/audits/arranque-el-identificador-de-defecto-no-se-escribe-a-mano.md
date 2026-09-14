# Nota de arranque — el identificador de un defecto deja de escribirse a mano

Rama `mejora/el-identificador-de-defecto-no-se-escribe-a-mano`, 14-09-2026.
Publicada **antes del primer commit de código**, como exige ADR-001. Decisión del
propietario esa madrugada, con estas palabras: que el `H-N` **deje de escribirse
a mano**, derivándolo o sustituyéndolo por una clave que no pueda chocar —la
incidencia o el ADR, que ya son únicos—, y **hacer la colisión imposible, no
improbable**.

## Lo que pasó, contado

En **una sola noche, tres colisiones**:

| Cuándo | Quién chocó con quién | Cómo se vio |
|---|---|---|
| 13-09 ~16:28 | `H-38`: ADR-184 (#602) y ADR-185 (#604) | al traer `main` a la rama de #602 |
| 13-09 ~16:28 | `H-39`: ADR-184 (#602) y ADR-187 (#611) | **`main` en rojo** tras la segunda fusión |
| 14-09 ~03:30 | `H-43`: ADR-191 (#622) y ADR-190 (#620) | la segunda rama todavía sin fusionar |

Las tres tienen la misma forma: **dos ramas abiertas a la vez eligen el
siguiente número mirando cada una su propio árbol**, y las dos aciertan. Nadie
miente y nadie se despista; el dato que consultan simplemente no incluye lo que
la otra rama está haciendo.

La tercera ocurrió **mientras se escribía el ADR de la cola**, que es otra cosa.
La cola no arregla esto: pone las ramas en fila para fusionar, pero dos ramas
pueden coger el mismo número aunque se fusionen una detrás de otra.

Es exactamente el modo en que nacieron los **dos ADR-016** que hoy conviven en el
registro de decisiones, y que la skill `adr` describe como lo que su guion **no**
cierra.

## 1. ¿Dónde vive el fallo y dónde va el arreglo?

El fallo vive en que **el identificador es un dato inventado**: alguien lee el
máximo que ve y suma uno. El arreglo no puede ser «mirar mejor» —ADR-180 ya hizo
eso para los ADR, consultando las ramas del remoto, y aun así el aviso que
imprime no impide nada—, porque cualquier lectura tiene una ventana entre mirar y
escribir.

El arreglo va en **qué se escribe**, no en cómo se elige: si el identificador se
deriva de algo que ya es único por construcción, no hay nada que elegir y no hay
ventana. La pregunta que caza la raíz —*¿puede el sitio del arreglo observar el
fallo?*— se contesta sola: no hace falta observar nada si el fallo no puede
ocurrir.

## 2. ¿Qué NO va a garantizar esto?

- **No renumera el pasado.** Los 43 identificadores que ya existen se quedan como
  están; reescribirlos rompería las citas de los ADR y de los commits de cierre
  que los nombran (`H-13: ...`), que es la convención que ADR-080 hizo vigilar.
- **No impide que dos ramas describan el mismo defecto dos veces.** Eso es otra
  cosa —trabajo duplicado, no identificador duplicado— y esta rama no lo toca.
- **No arregla los dos ADR-016.** El registro de decisiones tiene su propio
  identificador y su propio guion; aquí solo se toca el registro de defectos. Si
  la forma que salga sirve para los ADR, se dirá, pero no se aplica aquí.

## 3. Criterio de parada (decidido ANTES de mirar ningún resultado)

- **La colisión tiene que quedar imposible, no improbable.** Si la forma elegida
  todavía permite que dos ramas elijan lo mismo —aunque sea con una ventana más
  estrecha—, no vale y se dice.
- **No se rompe ninguna cita existente.** Si el cambio deja sin resolver una sola
  de las referencias `H-N` que hoy hay en ADR, commits o pruebas, se para.
- **La guarda de ADR-182 sigue en pie**: todo ADR que declara lección sigue
  teniendo su entrada, y la guarda sigue cazando su ausencia. Se prueba
  sembrando.
- **No se toca el contrato operativo** ni `docs/canonical/**`.
- Cada regla nueva trae **una mutación sembrada y vista caer**.
- Si al medir resultara que las tres colisiones se explican por una causa
  distinta de la que esta nota supone, se dice y se replantea.

## 4. ¿Qué haría el fallo imposible en vez de improbable?

Que el identificador **no se elija**. Dos formas, y la decisión entre ellas es de
esta rama:

- **(a) Derivarlo de la incidencia**, que GitHub ya garantiza única y que cada
  entrada del registro ya declara en su campo `incidencia`. Dos ramas distintas
  tienen incidencias distintas, así que no hay nada que chocar. Coste: una
  entrada sin incidencia detrás no tendría identificador, y hay que ver si
  existen.
- **(b) Derivarlo del ADR**, que también es único y que cada entrada declara en
  su campo `adr`. Mismo argumento, pero el número de ADR **sí ha chocado** en el
  pasado (los dos ADR-016), así que heredaría ese defecto.

La medida que decide: cuántas entradas del registro tienen hoy `incidencia` y
cuántas tienen `adr`, y si alguna no tiene ninguno de los dos.
