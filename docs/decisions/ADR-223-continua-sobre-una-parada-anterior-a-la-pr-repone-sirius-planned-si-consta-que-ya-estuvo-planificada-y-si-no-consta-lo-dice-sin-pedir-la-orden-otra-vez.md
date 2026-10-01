# ADR-223 — `continua` sobre una parada anterior a la PR repone `sirius:planned` si consta que ya estuvo planificada, y si no consta lo dice sin pedir la orden otra vez

- Estado: APROBADO
- Fecha: 2026-10-01
- Aprobación: la fusión de la PR por el motor con aprobación dual (ADR-205).
- Nota de arranque:
  `docs/audits/arranque-2026-10-01-continua-sobre-una-parada-anterior-a-la-pr.md`,
  publicada en el commit `104ae3dd` (01-10-2026, 08:13 UTC), antes del primer
  commit de arreglo.

## Contexto y problema

Cuando una incidencia se para **antes de producir rama ni PR**, el guion de
reanudación (`sirius_resume_on_command.sh`, camino `sin_pr`, H-23) repone la
etiqueta de la fase que se paró —`sirius:implement-requested`— y publica
«🟢 Reinicio autorizado por el propietario». Pero reponer esa etiqueta es
volver a **activar** la incidencia, y la puerta de activación (#60) exige
`sirius:planned` junto al evento: `planned` se consumió en la primera
activación y la puerta no la repone por su cuenta (#60). La puerta rechazaba el
reinicio en segundos (`sin-planned`), retiraba el evento, y la incidencia
quedaba **sin ninguna etiqueta**: inerte, muda, y además invisible para el
reconciliador, porque «sin etiquetas» no es un estado que nadie vigile
(bitácora del ciclo, entrada 126; deuda 36).

Medido en el volcado de septiembre (mina del 30-09): **9 reinicios sin PR**, y
**3 de ellos** seguidos de un rechazo `sin-planned` en el acto: #545 (05-09),
#581 (11-09) y #653 (20-09). Uno de cada tres reinicios anunció en verde una
reanudación que se rechazó sola.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque: el reinicio no añade `sirius:planned` ni ninguna
etiqueta reservada a una persona; con `planned` presente, el reinicio sin PR se
comporta exactamente como hoy; el aviso no empieza por «continua»; tres
mutaciones vistas caer.

**Desviación, a la vista.** La primera versión de este ADR cumplió ese criterio
al pie de la letra (no añadía `planned`) y Codex mostró en la ronda 1 de la PR
#671 que, para cumplirlo, le pedía al propietario aplicar la etiqueta **y
repetir la orden**, contra una regla suya de `AGENTS.md` («No pidas repetir una
acción ya realizada»). El criterio se cambia aquí y se dice: el reinicio sí
repone `sirius:planned`, pero **solo cuando consta en la cronología de la
incidencia que ya estuvo planificada**; nunca la inventa. Lo demás del
criterio se conserva.

## Opciones consideradas

1. **Que el reinicio reponga las dos etiquetas siempre**, leyendo el
   `continua` del propietario como certificación del alcance. Rechazada:
   inventaría una planificación donde nunca la hubo, y planificar es el gesto
   humano que la puerta de activación protege a propósito (#60).
2. **Que la puerta deje pasar un reinicio sin `planned`.** Rechazada por lo
   mismo: la puerta rechaza por diseño.
3. **Que el reinicio mire `planned` antes de anunciar y, si falta, lo diga y no
   toque nada**, pidiendo aplicar `planned` y repetir **continua**. Fue la
   primera versión de este ADR; Codex la tumbó en la ronda 1 de la PR #671:
   pide dos veces lo mismo (`AGENTS.md`), y una orden que no se atiende sin
   repetirla es la mitad de la parada muda que este ADR venía a quitar.
4. **Que el reinicio reponga `planned` solo si consta que la incidencia ya
   estuvo planificada** (la cronología de etiquetas: un `labeled
   sirius:planned`, lo haya puesto una persona a mano, el formulario de
   incidencias al abrirla una persona, o el despachador, que la pone como
   etiqueta inicial de toda incidencia que crea y solo crea con una orden del
   propietario enlazada, contrato §12.1), **y si no consta, lo diga sin pedir
   la orden otra vez**. Esta. Con la planificación que hubo y la orden
   `continua`, que solo acepta del propietario, reponer la etiqueta no
   inventa ninguna aprobación: devuelve la que la máquina consumió para
   repetir la misma activación. La primera versión de este punto decía que el
   motor nunca aplica `sirius:planned` y que por tanto todo `labeled` era una
   decisión humana; era falso (`dispatcher.py`, `ETIQUETA_INICIAL`; la
   plantilla `.github/ISSUE_TEMPLATE/sirius-work-item.yml`) y lo cazó Codex
   en la ronda 3 de la PR #671. La regla no cambia; lo que cambia es lo que
   se afirma de ella, en el guion, en la nota del reinicio y aquí.

## Decisión

En el camino `sin_pr`, cuando la fase de destino es `sirius:implement-requested`
y la incidencia no lleva `sirius:planned`, el guion:

1. **Lee la cronología** de la incidencia (`GET /issues/N/events`, paginada) y
   cuenta los `labeled` de `sirius:planned`. Si la cronología no se puede leer,
   **el run falla** sin concluir nada: ni repone `planned` ni publica «nunca
   planificada», que sería una conclusión falsa (ronda 2 de Codex).
2. **Si consta al menos uno, repone `sirius:planned` y retira la parada en una
   misma transición, que no despierta a nadie, y pone el evento en último
   lugar**: la puerta de activación, que despierta con el evento, tiene que
   encontrar `planned` puesta y la parada ya retirada. El reinicio en verde
   dice que la repuso, cuántas veces constaba y por qué. Una sola orden,
   ninguna repetición.
3. **Si no consta ninguno, no repone nada ni consume la parada**
   (`failed-safely` o `blocked-decision` se quedan): no hay aprobación que
   devolver. Publica **una vez por orden** (marcador
   `sirius-resume-sin-planned:<id del comentario>`) que la incidencia nunca
   tuvo `planned`, que planificarla es una decisión que el guion no toma, y
   que lo que hace falta es **la activación misma**, en el orden que la puerta
   necesita —retirar la parada, aplicar `sirius:planned` y, en último lugar,
   `sirius:implement-requested`: cada etiqueta es un evento aparte, la puerta
   arranca con la última y rechaza una parada que siga puesta (ronda 3 y
   ronda 4 de Codex: la primera versión decía «a la vez», que una persona no
   puede hacer, y la ronda 4 cazó que este punto seguía diciéndolo)—, no
   repetir la orden. El aviso no empieza por «continua». Si el aviso no se
   puede publicar, **el run falla** y queda reintentable: un aviso prometido
   que no llega es la parada muda otra vez.
4. Con `planned` presente, se conserva, se publica el reinicio sin mencionar
   ninguna reposición, **se retira la parada y después se repone el evento**.
5. **El orden es el mismo para el guion y para la persona** —la parada fuera,
   `planned` puesta, el evento en último lugar—, y por la misma razón: cada
   etiqueta es un evento aparte, el evento despierta a la puerta y la puerta
   rechaza, y retira el evento, si la parada sigue puesta
   (`INCOMPATIBLE_STATES` en `sirius_validate_activation.sh`). Hasta la ronda 5
   de Codex el guion ponía el evento y retiraba la parada después, el orden
   natural de `sirius_set_issue_labels`, y en esa ventana la puerta podía leer
   las dos etiquetas y dejar la incidencia solo con `planned`: mudo otra vez,
   después de anunciar el reinicio. `sirius_remove_issue_labels` (nuevo en
   `sirius_issue.sh`, verificado por REST como su hermano) retira sin añadir.
   El coste se asume y se dice: si la última llamada falla, la incidencia queda
   sin parada y sin evento, un `continua` nuevo no tendría parada que levantar,
   y el error del run nombra la etiqueta que falta y que se aplica a mano.

## Comprobación que la sostiene

`tests/automation/test_reanudar_ejecutando_el_guion.py` ejecuta el guion de
verdad con el doble de `gh`, que sirve ahora también la cronología de la
incidencia (`events_<n>.json`), puede negarse a servirla y puede negarse a
publicar un comentario. Los
casos existentes de reinicio sin PR siembran `sirius:planned`, porque sin él
nunca pudieron reanudar de verdad; y seis pruebas de este ADR:

- `test_una_parada_sin_pr_sin_planned_repone_planned_si_consta_que_ya_estuvo_planificada`:
  cronología con un `labeled sirius:planned` → `planned` y el evento repuestos
  (en ese orden), la parada retirada, el reinicio en verde dice que la repuso,
  y no hay aviso de falta.
- `test_una_parada_sin_pr_nunca_planificada_no_anuncia_en_verde_ni_pide_la_orden_otra_vez`:
  cronología vacía → la parada se conserva, nada se repone, el aviso lleva su
  marcador, no se publica el reinicio en verde y el texto no pide volver a
  escribir la orden.
- `test_el_aviso_de_sin_planned_no_empieza_por_continua`.
- `test_si_el_aviso_de_sin_planned_no_se_puede_publicar_el_run_falla`.
- `test_si_la_cronologia_no_se_puede_leer_el_run_falla_sin_concluir_nada`: la
  API de eventos falla → el run falla, nada se repone, nada se publica.
- `test_una_parada_sin_pr_con_planned_se_reanuda_y_conserva_planned` (y no
  menciona ninguna reposición).
- `test_una_incidencia_planificada_por_el_despachador_tambien_repone_planned`
  (ronda 3 de Codex): con `planned` puesta por el despachador la reposición
  es la misma, y la nota no afirma quién la puso.
- El aviso de «nunca planificada» da los pasos **en el orden que la puerta
  necesita**: retirar la parada, aplicar `planned` y, en último lugar,
  `implement-requested` (ronda 3 de Codex: cada etiqueta es un evento aparte,
  la puerta arranca con la última y rechaza una parada que siga puesta; la
  primera versión decía «a la vez», que una persona no puede hacer).
- El guion sigue ese mismo orden (ronda 5 de Codex: tres rondas seguidas de la
  misma familia —el orden de las etiquetas frente a una puerta que despierta
  con la última—, y la raíz era que el guion usaba el orden «poner y luego
  quitar» del ayudante). `test_una_parada_sin_pr_sin_planned_repone_planned_si_consta_que_ya_estuvo_planificada`
  exige `ADD planned` → `REMOVE parada` → `ADD evento`;
  `test_la_parada_se_retira_antes_de_reponer_el_evento` lo exige con `planned`
  ya puesta y con PR (`REMOVE parada` → `ADD evento`); y
  `test_si_el_evento_no_se_puede_reponer_el_run_dice_que_etiqueta_falta`
  comprueba el coste asumido: parada ya retirada, evento sin aplicar, run rojo
  y el error nombra la etiqueta que hay que aplicar a mano.

**Mutaciones** (cada una aplicada sobre el guion, la prueba ejecutada, el
fichero restaurado):

| | Mutación | Resultado |
|---|---|---|
| M1 | el reinicio deja de mirar `planned` | cae `una_parada_sin_pr_sin_planned_repone_planned_si_consta_que_ya_estuvo_planificada`, `una_parada_sin_pr_nunca_planificada_no_anuncia_en_verde_ni_pide_la_orden_otra_vez` |
| M2 | el aviso de «nunca planificada» consume la parada | cae `una_parada_sin_pr_nunca_planificada_no_anuncia_en_verde_ni_pide_la_orden_otra_vez` |
| M3 | con `planned` presente el reinicio deja de reponer la fase | cae `una_parada_sin_pr_reactiva_la_fase_que_se_paro`, `una_parada_sin_pr_NO_manda_el_trabajo_al_corrector`, `un_implementador_bloqueado_sin_pr_repite_su_fase_desde_cero` |
| M4 | reponer `planned` sin mirar la cronología | cae `una_parada_sin_pr_nunca_planificada_no_anuncia_en_verde_ni_pide_la_orden_otra_vez` |
| M5 | no reponer `planned` aunque conste que ya estuvo planificada | cae `una_parada_sin_pr_sin_planned_repone_planned_si_consta_que_ya_estuvo_planificada` |
| M6 | un aviso que no se puede publicar no hace fallar el run | cae `si_el_aviso_de_sin_planned_no_se_puede_publicar_el_run_falla` |
| M7 | una cronología que no se puede leer cuenta como «nunca planificada» | cae `si_la_cronologia_no_se_puede_leer_el_run_falla_sin_concluir_nada` |
| M8 | el guion vuelve a poner el evento antes de retirar la parada (ronda 5) | cae `una_parada_sin_pr_sin_planned_repone_planned_si_consta_que_ya_estuvo_planificada`, `la_parada_se_retira_antes_de_reponer_el_evento` |
| M9 | un evento que no se puede aplicar no hace fallar el run | cae `si_el_evento_no_se_puede_reponer_el_run_dice_que_etiqueta_falta` |

- El fichero entero en verde (30 pruebas); `bash -n`; `ruff`, `mypy` sobre la
  prueba. Batería entera: en la PR.

## Consecuencias

- Un `continua` sobre una parada pre-PR de una incidencia que ya estuvo
  planificada **reanuda de verdad con una sola orden**; antes la dejaba sin
  etiquetas y en silencio, y la primera versión de este ADR la dejaba parada
  con deberes para el propietario.
- La autorización queda escrita en la incidencia: el reinicio en verde dice que
  repuso `planned`, cuántas veces constaba y por qué. Si el propietario decide
  que su `continua` no debe valer para eso, la hoja de decisiones lo recoge y
  este camino vuelve a pedir la activación a mano.
- La única incidencia que no se reanuda sola es la que nunca tuvo `planned`:
  ahí sí falta una decisión humana, y se le pide la activación, no la orden.

## Alternativas descartadas y por qué

Las de «Opciones consideradas».

## La lección

- familia: `prosa-que-el-cambio-deja-falsa`
- sin esto se repetiría: un camino de reinicio escrito cuando activar era una etiqueta, que anuncia «autorizado» sin releer la puerta que ahora exige dos; el aviso en verde era verdad el día que se escribió y dejó de serlo sin que nadie lo tocara.
- lo hace cumplir: `tests/automation/test_reanudar_ejecutando_el_guion.py`
