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

El motor habla mucho y no dice dónde está. Cada hecho deja su comentario con su
marcador —y eso está bien, y costó rondas afinarlo (ADR-157, ADR-158)—, pero
el resultado es que una incidencia de veintiún comentarios no tiene ni una
línea que diga «voy por comprobar, Quality pasó, hay un hallazgo pendiente y la
PR es esta».

Symphony lo llama *workpad* y la investigación del 11-09 ya lo anotó como
**«distinto, no peor: el nuestro es un historial; el suyo, un tablero. Se puede
tener las dos cosas»**. Esto añade el tablero sin tocar el historial.

## Opciones consideradas

1. **Reescribir el aviso de estado para que sea el tablero.** Descartada: los
   avisos son el registro de lo que pasó, los lee el espejo para acreditar
   transiciones (`sirius-notification`) y reescribirlos rompería ADR-157.
2. **Publicarlo desde `reflejar-desenlace.yml`**, que ya lee el espejo de cada
   encargo vivo y ya monta `uv`. Descartada por lo que ese workflow declara en
   su propia cabecera: *«Sin `issues: write`: este comando solo LEE el espejo
   por `gh`»*. Esa frontera la puso alguien a propósito.
3. **Publicarlo desde `notify-sirius-state.yml`** (la elegida): ya se dispara
   con las seis etiquetas del ciclo, ya tiene `issues: write` y ya escribe en
   esa misma incidencia en ese mismo evento.
4. **Un fichero `TABLERO.md` por encargo en la rama del motor.** Descartada: el
   propietario mira las incidencias, no la rama de memoria, y `DESENLACES.md`
   ya cubre la vista agregada (ADR-171).

## Decisión

**Uno. Un solo comentario por incidencia, reescrito en cada cambio de estado.**
Lleva: qué se pidió (del cuerpo declarado), por dónde va el ciclo, qué se ha
comprobado (Quality y rondas, con sus números), dónde está la evidencia (PR,
head, etiquetas) y **qué se espera del propietario ahora**. Si el encargo está
detenido, enseña el diagnóstico.

**Dos. El cuerpo lo produce una función pura** —`sirius_engine.tablero`— a
partir de lo que el espejo YA proyecta y de lo que `leer_cuerpo_declarado` YA
extrae. Ni una lectura nueva de GitHub: `sirius-tablero` hace las tres lecturas
del puerto una sola vez y las reparte entre la proyección y el lector de
secciones.

**Tres. Publicarlo es `sirius_comment_upsert`**, la otra mitad de
`sirius_comment_once`: aquella publica un HECHO, que ocurre una vez; esta
mantiene un ESTADO, que cambia. Dos reglas, las dos para no acabar con dos
tableros: si el historial no se puede leer **no se crea nada** —crear a ciegas
publicaría un tablero más en cada mal minuto de la API—, y cuando hay varios se
edita **el más antiguo**, para que todas las pasadas converjan en el mismo. No
borra nada: esta biblioteca no borra.

**Cuatro. El marcador no se copia.** El workflow lo saca de la primera línea
del cuerpo que el propio generador produce. Tenerlo escrito en dos sitios
significaría que el día que cambiara en uno el motor publicaría un tablero
nuevo dejando huérfano al anterior.

**Cinco. El paso falla abierto**, como el aviso que ya vive ahí: sin `uv`, sin
entorno, sin espejo legible o sin poder publicar, deja un `::warning::` y sale
en verde. Un tablero que no se pudo pintar no altera el estado de la incidencia
ni bloquea el ciclo.

## Comprobación que la sostiene

**45 pruebas nuevas**, y las mutaciones que las sostienen.

Del publicador (`sirius_comment_upsert`), que es donde puede salir algo caro —
una incidencia con una colección de tableros—, cuatro mutaciones sembradas en
la biblioteca de shell y vistas caer:

| Mutación | Prueba que cae |
|---|---|
| Edita el tablero más NUEVO en vez del más antiguo | la de converger siempre en el mismo |
| Si el historial no se puede leer, crea a ciegas | la de no publicar nada |
| Se quita la frontera de confianza del filtro | la de no reescribir el comentario de un tercero |
| El cuerpo se manda en crudo en vez de como JSON | la de comillas, acentos y saltos |

Cada una tumba exactamente una prueba y ninguna más; con la biblioteca
restaurada, las 7 en verde.

Del generador, 20 pruebas que fijan lo que enseña y —igual de importante— lo
que **no inventa**: sin PR dice que no hay ninguna, sin Quality dice que no se
ha observado ninguna ejecución, y un cuerpo sin secciones da media foto en vez
de una tabla falsa. Una prueba comprueba que el módulo no importa `datetime`,
`subprocess`, `urllib` ni `os`: si dejara de ser puro, dos pasadas seguidas
darían cuerpos distintos y el tablero parpadearía.

Y una prueba que ata el workflow al comando: si alguien renombrara el punto de
entrada o el paso, se ve en rojo en vez de en un tablero que dejó de
actualizarse sin que nadie lo notara.

`ruff format --check`, `ruff check` y `mypy src tests` en verde.

## Consecuencias

- **El plazo del workflow sube de 5 a 8 minutos.** El paso monta `uv` y
  sincroniza; con caché son segundos —medido en `reflejar-desenlace.yml`:
  instalar 2 s, sincronizar 3 s—, pero una caché fría no cabía en el anterior.
  Sigue siendo la red de seguridad de un workflow secundario.
- **Coste en minutos de Actions: prácticamente cero.** El job ya existía y ya
  se facturaba por minuto empezado; esto le añade segundos, no minutos.
- **El tablero no se actualiza con `sirius:ci-pending`**, que no está entre las
  seis etiquetas que disparan este workflow: en esa ventana enseña el estado
  anterior. Ampliar el disparador es cambiar cuándo corre un workflow y no
  entra aquí.
- **No puede ser exactamente-una-vez.** La edición sí es idempotente; la
  primera publicación no, por la limitación que `sirius_comment_once` ya
  documenta. Si llegaran a existir dos tableros, las pasadas siguientes
  convergen en el más antiguo y el duplicado se queda quieto.
- **El historial no cambia en nada.**

## Alternativas descartadas y por qué

Las cuatro de arriba. Y una quinta: **que el tablero incluyera el texto
completo del objetivo y del criterio**. Descartada: los cuerpos de este
repositorio llegan a mil palabras y el tablero dejaría de leerse de un vistazo,
que es su única razón de ser. Se recorta por palabras y el cuerpo entero está a
un clic, arriba, en la propia incidencia.

## La lección

- familia: `pieza-sin-lector`
- sin esto se repetiría: proyectar en cada pasada el estado entero de una incidencia -fase, rondas, Quality, PR, diagnóstico- y no enseñárselo nunca a quien tiene que decidir; es la novena vez que un dato correcto de esta casa no tiene lector, tres días después de la octava.
- lo hace cumplir: `tests/engine/test_tablero.py`
