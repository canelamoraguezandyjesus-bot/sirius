# ADR-159 — El recibo de una reanudación distingue cada permiso escrito, no solo su head

- Estado: PROPUESTO
- Fecha: 2026-09-08
- Aprobación: mandato del propietario del 07/08-09-2026 («acaba lo que queda
  pendiente», 03:1x UTC+2), que ordena saldar las deudas abiertas antes de
  empezar la línea de memoria, y la fusión de esta PR (toca
  `scripts/automation/**`: ficha del operador).

Esta es también la nota de arranque de la rama
`claude/adr-159-recibo-por-permiso`, publicada antes del primer cambio de
código, con las cuatro preguntas de la disciplina de evidencia (ADR-001).

## Contexto y problema

`sirius_resume_on_command.sh` publica, antes de reponer la etiqueta que
reanuda el ciclo, un **recibo** de la autorización. Son tres marcadores y solo
uno de ellos identifica el suceso:

| marcador | forma | ¿dos reanudaciones dejan dos recibos? |
|---|---|---|
| `sirius-restart-sin-pr` | `<incidencia>:<run>-<intento>` | **sí** (ADR-094, patrón ADR-140) |
| `sirius-convergence-reset` | `<head>` | no |
| `sirius-resume-stop` | `<head>` | no |

`sirius_comment_once` deduplica por el **texto completo** del marcador, así que
dos reanudaciones sobre el MISMO head publican el primer recibo y suprimen el
segundo. El historial de la incidencia guarda entonces una autorización donde
hubo dos, y eso no es una molestia cosmética: es la premisa 4 del encargo #539,
que se dio por cierta, resultó falsa y obligó a rehacer el trabajo entero como
#545. Quedó registrada como **deuda 15** de la bitácora del ciclo.

Es la MISMA familia que ADR-157 (07-09-2026), que ya la arregló para el otro
emisor: `notify-sirius-state.yml` deduplicaba su aviso por
`<etiqueta>:<head>` y una segunda parada sobre el mismo head no dejaba rastro
propio. Aquel arreglo —que el marcador lleve el run del evento— es el que se
aplica aquí a los dos marcadores que faltan. El emisor no puede destruir al
publicar la evidencia que sus lectores necesitan después.

**La medición que lo hace urgente y no teórico**: esta misma noche, con #546
detenida por el tope de uso de Codex, la operación publicó reintentos con
`continua` sobre el head `c2db289`. Todos ellos comparten un único recibo
`sirius-resume-stop:c2db289…`. La incidencia #545 no puede decir cuántas veces
se la reanudó; la bitácora sí, porque las horas se anotaron a mano.

### El lector que se rompe en silencio, y es el motivo de que esto no sea de una línea

`round_history.RESUME_MARKER_RE` es
`<!--\s*sirius-convergence-reset:[0-9a-fA-F]+\s*-->`: exige **hexadecimal
puro** hasta el cierre. Añadirle `:<run>-<intento>` al marcador sin tocar ese
patrón haría que `history_after_last_resume` dejara de encontrarlo y, por
tanto, **de cortar el historial**. Consecuencia observable: el freno de
convergencia dejaría de reiniciarse con la orden del propietario, que es
exactamente la entrada que ADR-030 le dio para no condenar el trabajo
autorizado. Sería una regresión grave y muda —nada falla, simplemente el
`continua` deja de perdonar rondas—, y es lo que este ADR tiene que impedir.

El otro lector, `mirror_projection._RESUME_MARKER_RE`, usa `[^>]*` y admite las
dos formas sin cambio. `sirius_resume_on_command.sh:237` busca por nombre de
marcador y tampoco se rompe.

## Nota de arranque (cuatro preguntas, ADR-001)

1. **¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo
   observar el fallo?** Vive en el EMISOR: las líneas 317 y 324 de
   `sirius_resume_on_command.sh` componen un marcador que no distingue dos
   autorizaciones sobre el mismo head. El arreglo va ahí —los dos marcadores
   ganan `:${GITHUB_RUN_ID:-manual}-${GITHUB_RUN_ATTEMPT:-1}`, la forma que
   `sirius-restart-sin-pr` ya usa— y, en el mismo cambio, en el lector que esa
   forma rompería (`round_history.RESUME_MARKER_RE`). Se observa en el texto
   del comentario publicado y en el corte que `history_after_last_resume`
   devuelve.
2. **¿Qué NO garantiza esto?** No reescribe el pasado: los historiales ya
   publicados siguen con sus huecos, y por eso los dos lectores tienen que
   admitir las dos formas —la histórica y la nueva—. No cambia cuántos permisos
   cuenta `_interpretar_permisos_reanudacion` para un historial ANTIGUO. No
   toca el colapso orden+recibo de CLAUDE-R5-003 (que se decide por posición,
   no por el texto del marcador). No arregla el tercer emisor de la familia si
   lo hubiera: solo estos dos marcadores.
3. **Criterio de parada (decidido antes de ver ningún resultado).** (a) Un
   guardián nuevo ve FALLAR `history_after_last_resume` de `main` con el
   marcador NUEVO —no corta, devuelve el texto entero— y pasa con el cambio;
   (b) un guardián nuevo ve que dos reanudaciones sobre el MISMO head producen
   dos marcadores DISTINTOS, y falla contra el guion de `main`; (c) los
   guardianes existentes de `round_history`, de `mirror_projection` y del
   guion siguen verdes con la forma HISTÓRICA, sin tocar ninguno; (d) la
   cadena completa termina en 0. Que un guardián de (c) haya que relajarlo
   desmiente este ADR y obliga a parar.
4. **¿Qué hace esto imposible, en vez de improbable?** Que dos permisos
   escritos del propietario sobre el mismo head se confundan con uno en el
   historial de la incidencia. Y, del lado del lector, que un marcador con run
   deje de reiniciar el listón de convergencia.

## Criterio de parada (escrito ANTES de decidir)

Ver punto 3 de la nota de arranque.

## Opciones consideradas

1. **Que los dos marcadores lleven el run y el intento del evento, y que el
   lector estricto admita las dos formas** (elegida). Es exactamente lo que
   ADR-157 hizo para el notificador y lo que `sirius-restart-sin-pr` ya hacía
   desde ADR-094: una sola forma en todo el sistema, y la reejecución del
   mismo run sigue sin duplicar nada.
2. **Que `sirius_comment_once` deduplique por algo que no sea el texto.**
   Toca a todos sus llamadores a la vez, incluidos los que dependen de la
   deduplicación exacta. Alcance mucho mayor y riesgo repartido por todo el
   motor. Descartada.
3. **Dejar el marcador y contar las reanudaciones por las órdenes `continua`.**
   Es lo que #546 ya hace como respaldo, y por eso el motor funciona hoy. Pero
   deja el historial mintiendo para cualquier otro lector, y la orden puede
   faltar cuando la reanudación la dispara otra automatización. Descartada:
   arregla al lector, no al emisor.
4. **Añadir solo el intento (`GITHUB_RUN_ATTEMPT`).** No distingue dos
   reanudaciones servidas por runs distintos, que es el caso normal.
   Descartada.

## Decisión

- `scripts/automation/sirius_resume_on_command.sh`: los marcadores
  `sirius-convergence-reset` y `sirius-resume-stop` pasan a
  `<head>:<run>-<intento>`, con el mismo respaldo `manual`/`1` que usa
  `sirius-restart-sin-pr` cuando el guion corre fuera de Actions.
- `src/sirius_engine/round_history.py`: `RESUME_MARKER_RE` acepta el head
  seguido OPCIONALMENTE de `:<run>-<intento>`, de modo que los historiales
  publicados antes de esta ficha se siguen cortando igual.
- Los textos que afirman en PRESENTE que el recibo «solo lleva el head» —el
  comentario de cabecera del guion, el bloque de `_RESUME_MARKER_RE` y el
  docstring de `_interpretar_permisos_reanudacion` en `mirror_projection.py`—
  quedan acotados al árbol en que fueron ciertos y citando este ADR. Es la
  lección de ADR-157: cambiar el comportamiento sin actualizar el texto que lo
  describe deja una afirmación falsa firmada, y la encontró un revisor, no yo.

## Comprobación que la sostiene

- Guardianes vistos fallar contra el emisor y el lector de `main`, y en verde
  con el cambio: transcritos en el cuerpo de la PR.
- Cadena completa como una sola invocación, anclada a su árbol (ADR-154):
  transcrita en el cuerpo de la PR.
- Lo que NO se ha medido: el caso en vivo. Se salda cuando una incidencia
  reciba DOS reanudaciones sobre el mismo head y el historial muestre dos
  recibos distintos.

## Consecuencias

- La deuda 15 de la bitácora queda saldada del lado del emisor.
- El respaldo que #546 construyó —contar también la orden `continua`— NO se
  retira: sigue haciendo falta para los historiales ya publicados, y para las
  reanudaciones cuyo recibo dispare otra automatización.
- Un historial NUEVO con dos reanudaciones sobre el mismo head pasa a proyectar
  DOS permisos donde antes proyectaba uno. Eso es el objetivo, no un efecto
  secundario: es lo que permite acreditar la segunda salida de parada.
