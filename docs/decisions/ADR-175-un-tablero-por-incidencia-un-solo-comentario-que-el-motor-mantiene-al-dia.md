# ADR-175 — Un tablero por incidencia: un solo comentario que el motor mantiene al día

- Estado: PROPUESTO
- Fecha: 2026-09-12
- Aprobación: la fusión de la PR por el propietario

## Nota de arranque (escrita ANTES de tocar una línea de código)

### Lo medido antes de escribir esta nota

Las **40 incidencias más recientes del ciclo** (de la #473 a la #579) acumulan
**1.019 comentarios**. Mediana: **21 por incidencia**. Media: 25,5. Máximo:
**157** (#545). **21 de las 40 pasan de veinte comentarios**; 13 pasan de
treinta.

Para saber qué está pasando en una incidencia hay que leerse veintiún
comentarios, y ninguno de ellos dice el estado: cada uno es un **hecho** con su
marcador —un aviso de estado, un veredicto, un registro de ronda, un reparto—,
publicado una vez y nunca vuelto a tocar. El motor publica **historial**. No
publica **estado**.

Y no es que no lo sepa: el espejo ya proyecta el estado entero en cada pasada.
`MirroredWorkItem` trae `estado`, `fase`, `etiquetas`, `pr_url`, `head_sha`,
`rondas` (número, head, pendientes, gravedad), `veredictos`, `eventos_quality`,
`fallos_quality_consecutivos`, `diagnostico_fallo` y `cerrada`. Y
`leer_cuerpo_declarado` ya parte el cuerpo de la incidencia en objetivo,
entregable, fuera de alcance, criterio de terminado y plan. **Todo eso se
calcula ya, y a un humano no se le enseña nunca.** Es la misma forma que ADR-173
encontró con el campo `cerrada`: el dato está, lo lee la máquina para lo suyo, y
nadie lo pone donde haga falta.

La investigación del 11-09-2026 lo dejó anotado tal cual, comparando con el
«workpad» de Symphony: *«Un solo comentario de trabajo por incidencia,
actualizado | Un comentario por hecho, con marcador | **Distinto, no peor: el
nuestro es un historial; el suyo, un tablero. Se puede tener las dos cosas»*.

### 1. ¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo OBSERVAR el fallo?

El fallo no está en lo que el motor sabe, sino en lo que **enseña**. El arreglo
va a `notify-sirius-state.yml`, que es el workflow que ya escribe comentarios de
estado, que ya se dispara con las seis etiquetas del ciclo y que **ya tiene
`issues: write`**. Ni un disparador nuevo, ni un permiso nuevo, ni otro nivel de
automatización: el motor ya escribe en esa incidencia, en ese mismo evento.

Se descartó alojarlo en `reflejar-desenlace.yml` —que ya lee el espejo de cada
encargo vivo y ya monta `uv`— por una razón escrita en su propia cabecera: *«Sin
`issues: write`: este comando solo LEE el espejo por `gh`»*. Esa frontera la
puso alguien a propósito y no se cruza para ahorrar cinco segundos de
instalación.

**¿Puede el sitio del arreglo observar el fallo?** Sí: el cuerpo del tablero se
calcula del mismo espejo que se lee en ese paso, y si el espejo no se puede
leer, no hay tablero y se dice —el paso es secundario y falla abierto, como la
notificación que ya vive ahí.

### 2. ¿Qué NO va a garantizar esto?

- **No sustituye al historial.** Los avisos, veredictos y registros de ronda
  siguen igual: son el registro de lo que pasó, y ADR-157/ADR-158 se pelearon
  por ellos. El tablero es la foto de AHORA; el historial, la película.
- **No se actualiza con todas las etiquetas.** Solo con las seis que disparan
  ese workflow (`implementing`, `repair-requested`, `ready-for-merge`,
  `blocked-decision`, `failed-safely`, `completed`). Con `sirius:ci-pending`,
  que no está entre ellas, el tablero se queda en el estado anterior. Ampliar el
  disparador es cambiar cuándo corre un workflow y no entra aquí.
- **No puede ser exactamente-una-vez.** Es la limitación que
  `sirius_comment_once` ya documenta: el POST de un comentario no es idempotente
  y una respuesta perdida puede dejar un tablero publicado sin que esta
  ejecución lo sepa. La EDICIÓN sí es idempotente, así que el riesgo se limita a
  la primera publicación. Mitigación: se busca el tablero por su marcador y se
  edita **el primero**; nunca se borra ni se toca ningún otro comentario.
- **No inventa estado.** Lo que el espejo no expone no aparece. El tablero dice
  de dónde sale cada cosa.
- **No toca comentarios ajenos.** Solo su propio marcador, y solo entre
  comentarios de autor de confianza, con el mismo filtro que ya usa el resto de
  la biblioteca.
- **No arregla que el ciclo esté parado.** El último encargo se despachó el
  06-09-2026; el tablero se verá cuando vuelva a haber trabajo.

### 3. Criterio de parada (decidido ANTES de ver ningún resultado)

- **(a)** Si el tablero exigiera un permiso que el workflow no tenga ya, o un
  disparador nuevo, **se para**: sería ampliar la automatización, y eso tiene su
  puerta en el contrato operativo.
- **(b)** Si el cuerpo necesitara un dato que el espejo no expone hoy, **se
  para**: no se añade una lectura nueva de GitHub para pintar un tablero.
- **(c)** Si un fallo del tablero pudiera alterar el estado de la incidencia o
  bloquear el ciclo, **se para y se rediseña**. El paso tiene que fallar abierto
  igual que la notificación que ya vive ahí.
- **(d)** Ninguna prueba nueva se da por buena sin haberla visto fallar contra
  una versión rota a propósito (ADR-001 §3).

### 4. ¿Qué haría el fallo IMPOSIBLE en vez de improbable?

Que el tablero no se pueda olvidar: **su cuerpo lo produce una función pura, con
su prueba, y se publica en el mismo paso que ya publica la notificación**. No
hay un camino aparte que alguien pueda saltarse, ni un fichero que alguien deba
acordarse de actualizar —que es exactamente el fallo que ADR-174 midió en la
mina—.

Lo que esto NO hace imposible: que el espejo se equivoque. El tablero enseña lo
que el espejo dice, y dice que eso es lo que enseña.

## Contexto y problema

(se completa al cerrar el trabajo)

## Decisión

(se completa al cerrar el trabajo)

## Comprobación que la sostiene

(se completa al cerrar el trabajo)

## Consecuencias

(se completa al cerrar el trabajo)

## La lección

- ninguna: se completa al cerrar el trabajo
