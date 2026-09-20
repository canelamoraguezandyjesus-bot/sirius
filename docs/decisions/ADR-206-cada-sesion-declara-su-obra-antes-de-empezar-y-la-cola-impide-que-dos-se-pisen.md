# ADR-206 — Cada sesión declara su obra antes de empezar, y una guarda impide que dos se pisen

- Estado: APROBADO
- Fecha: 2026-09-20
- Aprobación: el propietario, el 20-09-2026: «créate una cola o lo que sea para
  hacerlo todo así no se pisan».
- Nota de arranque: la de ADR-204, que cubre esta tanda entera.

## Contexto y problema

El paso 4 de la auditoría midió lo que cuesta no tener esto. El 10-08-2026 el
propietario tenía **cuatro sesiones abiertas a la vez** y lo dijo con estas
palabras: «tienes permiso mientras no me jodas el trabajo que tengo avanzado ya
en las otras sesiones activas de model estudio, revisión codex claude code y
auditoría forense adr002». Lo que pasó:

| Cuándo | Qué se pisó |
|---|---|
| 10-08, 21:45 | Una sesión compilaba el mismo repositorio que otra en la misma máquina; la `.venv` y el worktree quedaron corruptos, y costó dos horas |
| 10-08 → 14-08 | Una sesión cerró B12 (ADR-006 y ADR-007, del 10-08); cuatro días después otra encargó al motor **construir B12**, incidencia #165. El implementador automático se paró solo porque el trabajo ya existía |
| 14-08 | Dos ramas distintas escribieron **dos ADR-016** el mismo día |
| 14-08 | ADR-005, escrito por una sesión, invalidó las ediciones que otra estaba haciendo sobre los mismos documentos |

Dos de esas cuatro ya tienen su arreglo: **ADR-016** («el estado se lee de
`main`, no de la rama») y **ADR-180** («el número del siguiente ADR se calcula
contra las ramas del remoto»). Lo que sigue sin arreglo es lo que queda: **una
sesión no puede saber qué ficheros está tocando otra sesión viva.**

El motor sí lo resolvió para sus ramas: `scripts/automation/sirius_cola.py`
pregunta una sola cosa —¿es la punta de `main` ancestro de este head?— y de esa
condición sale una cola sin cerrojos. Pero eso ordena **el aterrizaje**, no el
arranque: dos sesiones pueden empezar la misma obra y las dos estar al día.

## Criterio de parada (escrito ANTES de decidir)

Si al medirlo resultara que las colisiones se explican todas por ADR-016 y
ADR-180 —es decir, por leer el estado mal, no por trabajar a la vez—, no hace
falta nada nuevo y esta decisión se retira. Se comprueba caso por caso sobre
las cuatro colisiones medidas antes de decidir.

Y un segundo criterio, de diseño: **si la solución necesita un cerrojo que
alguien tenga que soltar, se descarta.** Aquí los procesos mueren —un runner se
cae, una sesión se corta, el contenedor se recicla— y un turno pillado exige
que alguien lo libere a mano. Es la familia
`regla-que-depende-de-que-alguien-se-acuerde`, que esta casa lleva cerrando
desde ADR-174.

## Decisión

**Una sesión declara su obra abriendo su pull request en cuanto tiene su primer
commit**, aunque sea borrador, y **antes de empezar comprueba si otra obra viva
toca sus mismos ficheros**. La comprobación la hace
`scripts/automation/sirius_obra_en_curso.py`, que recibe la lista de ficheros
que la sesión va a tocar y el listado de las pull requests abiertas con los
suyos, y responde qué se solapa y con quién.

Si hay solape, la sesión **no empieza**: lo dice, nombra la otra obra, y espera
o cambia de vertical. No es un cerrojo —no guarda nada, no hay nada que
liberar— sino la misma forma que `sirius_cola.py`: se leen dos datos y se
comparan.

**Fail-closed.** Si el listado de obras vivas no se puede leer, la guarda no
dice «adelante»: dice que no sabe, y no saber es un motivo para parar. Un
listado vacío por un error de red es indistinguible de «no hay nadie más», y
esa es exactamente la confusión que produjo la #165.

## Comprobación que la sostiene

**El criterio de parada, comprobado caso por caso:** de las cuatro colisiones,
ADR-016 explica la segunda y ADR-180 la tercera. La primera (dos compilaciones
sobre el mismo árbol) y la cuarta (dos sesiones editando los mismos documentos)
**no las explica ninguno de los dos**: en las dos, cada sesión leía bien y aun
así no podía ver a la otra. El criterio no se dispara y la decisión se sostiene.

**La implementación:** `scripts/automation/sirius_obra_en_curso.py`, función
pura sin red, con `tests/automation/test_obra_en_curso.py`. Recibe ficheros y
devuelve solapes; quien lee GitHub es quien la llama, que es donde vive la
disciplina de reintento —la misma separación que `sirius_misma_obra.py` adoptó
por la lección de H-14.

## Consecuencias

- `AGENTS.md` gana la regla: declarar la obra al primer commit y comprobar el
  solape antes de empezar.
- Una sesión que encuentre solape lo dice en vez de trabajar en balde. El coste
  es esa parada; el que se ahorra está medido: una tarde entera el 14-08 y dos
  horas de entorno roto el 10-08.
- **Lo que esto no resuelve:** dos sesiones que empiecen a la vez, en el mismo
  minuto, antes de que ninguna tenga commit. Es una ventana estrecha y cerrarla
  exigiría un cerrojo, que el criterio de parada descarta. Queda declarada.

## Alternativas descartadas y por qué

- **Un fichero de turnos en `main` que cada sesión edita.** Es un cerrojo con
  otro nombre: una sesión que muere deja su turno cogido, y además ninguna
  sesión interactiva puede escribir en `main`.
- **Limitar a una sesión a la vez.** Resolvería el problema y quita al
  propietario algo que usa de verdad: el 10-08 llevaba cuatro y cada una
  avanzaba en su frente. La decisión de cuántas lleva es suya, no de una regla.
- **Que lo vigile el motor.** El motor no ve las sesiones interactivas: solo ve
  incidencias y ramas. Por eso la guarda vive donde la sesión empieza.

## La lección

- familia: `dos-sesiones-que-no-se-ven`
- sin esto se repetiría: dos sesiones volverían a construir lo mismo o a
  pisarse los documentos, y nadie lo sabría hasta que una de las dos
  descubriera que su trabajo ya existía.
- lo hace cumplir: `tests/automation/test_obra_en_curso.py`
