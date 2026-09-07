# ADR-157 — Cada parada deja su propio marcador de notificación

- Estado: PROPUESTO
- Fecha: 2026-09-07
- Aprobación: mandato del propietario del 07-09-2026 («ponte a trabajar», y la
  regla de la disciplina de evidencia que él mismo fijó en `CLAUDE.md`: dos
  rondas con defectos de la misma familia obligan a buscar la raíz) y la
  fusión de esta PR (toca `.github/**`: ficha del operador).

Esta es también la nota de arranque de la rama
`claude/adr-157-cada-parada-deja-su-marcador`, publicada antes del primer
cambio, con las cuatro preguntas de la disciplina de evidencia (ADR-001).

## Contexto y problema

El encargo #545 (PR #546, ADR-147) lleva **cinco rondas de revisión con
hallazgos de la misma familia**: rondas 4, 5, 6 y 9 (identificadores R4-002,
R5-001, CODEX-001, R6-001, R6-002, R7-001, R7-002). Todos dicen, con
palabras distintas, lo mismo: el reflector no puede saber **qué parada es
cuál** cuando dos paradas del mismo tipo ocurren sobre el mismo head.

La causa no está en el reflector. Está en el emisor:

```
# .github/workflows/notify-sirius-state.yml, línea 67
marker="<!-- sirius-notification:${STATE_LABEL}:${head_sha} -->"
```

Ese marcador es la idempotencia del notificador —«una sola notificación por
incidencia, estado y SHA»—, y por eso **una segunda parada del mismo estado
sobre el mismo head no deja ningún rastro**: el comentario no se publica. El
historial de la incidencia guarda una ocurrencia donde hubo dos.

Lo dice literalmente el hallazgo CLAUDE-R7-001 de la ronda 9 (07-09, 16:39):
«`notify-sirius-state.yml` deduplica por `sirius-notification:<etiqueta>:<head>`,
así que una SEGUNDA `blocked-decision` sobre el mismo head no deja marcador
propio; en el historial solo está el aviso de la PRIMERA». Y el caso es real,
no teórico: la propia incidencia #545 tiene UN marcador
`sirius-notification:sirius:failed-safely:bc33b82…` y **tres** comentarios de
parada sobre ese head (medido en la ronda 5, runs 34048494054, 34058533259 y
34084006339).

Cada ronda ha respondido a esto con una heurística nueva sobre la evidencia
que falta —emparejar por rango, alinear desde el final, alinear desde el
principio, abstenerse cuando no cabe—, y cada heurística ha traído su propio
caso límite, que la ronda siguiente ha encontrado. Es exactamente el patrón
que `CLAUDE.md` prohíbe seguir: «dos rondas de revisión con defectos de la
misma familia → parar y buscar la raíz, no seguir parcheando».

## Nota de arranque (cuatro preguntas, ADR-001)

1. **¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo
   observar el fallo?** El fallo vive en el EMISOR: el notificador destruye,
   al publicar, la distinción entre dos ocurrencias del mismo estado sobre el
   mismo head. El arreglo va ahí: el marcador incorpora el run que lo produjo
   (`sirius-notification:<etiqueta>:<head>:<run>`), de modo que cada evento de
   etiqueta deja su propio comentario y la reejecución del MISMO run sigue sin
   duplicar. Se observa en el historial de una incidencia con dos paradas
   iguales: hoy hay un comentario, después habrá dos.
2. **¿Qué NO garantiza esto?** No arregla por sí solo el recorrido del
   reflector (#546): las incidencias vivas hoy conservan historiales donde
   faltan marcadores, así que la heurística de #546 sigue haciendo falta como
   respaldo para el historial ANTIGUO. Lo que cambia es que deja de ser el
   camino principal: a partir de esta fusión, la evidencia que el reflector
   necesita existe. Tampoco cambia el contenido de los avisos, ni las
   etiquetas, ni el encaminamiento, ni el orden en que se publican.
3. **Criterio de parada (decidido antes de ver ningún resultado).** El
   guardián nuevo ve FALLAR el workflow de `main` (su marcador no lleva el
   run) y pasa con el cambio; los guardianes existentes del notificador
   siguen verdes; la cadena completa termina en 0. En vivo: la próxima
   incidencia que se pare dos veces sobre el mismo head deja DOS comentarios
   de notificación, uno por parada. Si tras esta fusión una incidencia con dos
   paradas iguales sigue dejando un solo marcador, este ADR queda desmentido.
4. **¿Qué hace esto imposible, en vez de improbable?** Que el motor borre, al
   publicar, la evidencia que sus propios lectores necesitan después. La
   idempotencia deja de significar «un aviso por estado y head» —que confunde
   dos sucesos distintos— y pasa a significar «un aviso por evento», que es
   lo que de verdad se quiere no duplicar.

## Criterio de parada (escrito ANTES de decidir)

Ver punto 3 de la nota de arranque.

## Opciones consideradas

1. **El marcador lleva el run del evento que lo produjo** (elegida). Una
   línea del emisor; conserva la idempotencia real (reejecutar el mismo run
   no duplica) y devuelve al historial la distinción entre dos sucesos.
2. **Seguir afinando la heurística del reflector.** Es lo que llevan cinco
   rondas y sigue trayendo casos límite: la evidencia que necesita no existe,
   y ninguna cantidad de código la crea.
3. **Que el reflector se abstenga siempre que haya ambigüedad.** Conservador y
   correcto, pero convierte en «divergencia declarada» toda recuperación con
   dos paradas iguales, que es justo el caso que el encargo vino a resolver.
4. **Quitar la idempotencia del notificador.** Un aviso por cada reejecución
   del mismo run, incluidos los reintentos de infraestructura: ruido en la
   incidencia sin ganar evidencia.

## Decisión

- `.github/workflows/notify-sirius-state.yml`: el marcador pasa a
  `<!-- sirius-notification:<etiqueta>:<head>:<run> -->`, con `<run>` el
  identificador del run de Actions que atiende el evento de etiqueta. La
  comprobación de duplicado sigue siendo exacta sobre ese marcador, así que
  reejecutar el mismo run no publica un segundo aviso.
- Guardián: el marcador que escribe el workflow incluye el run, y el texto de
  la idempotencia dice lo que el marcador hace.

## Comprobación que la sostiene

- Guardián visto fallar contra el workflow de `main` y en verde con el
  cambio; los tres guardianes existentes del notificador, intactos:
  transcritos en el cuerpo de la PR.
- Cadena completa como una sola invocación, anclada a su árbol (ADR-154):
  transcrita en el cuerpo de la PR.
- Lo que NO se ha medido: el caso en vivo (criterio 3), que necesita una
  incidencia que se pare dos veces sobre el mismo head después de esta
  fusión.

## Consecuencias

- El historial de una incidencia vuelve a ser un registro fiel: tantos avisos
  como sucesos. Los lectores (el reflector de #546, y cualquiera que venga)
  dejan de tener que adivinar.
- Las incidencias ya vividas conservan sus huecos: el respaldo heurístico de
  #546 sigue siendo necesario para ellas, y así queda declarado en ADR-147.
- Una incidencia que rebote varias veces por el mismo estado tendrá más
  comentarios que antes. Es el precio de no mentir en el registro.

## Alternativas descartadas y por qué

Ver «Opciones consideradas».
