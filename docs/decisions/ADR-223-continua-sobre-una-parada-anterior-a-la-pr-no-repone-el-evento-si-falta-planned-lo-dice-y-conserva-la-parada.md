# ADR-223 — `continua` sobre una parada anterior a la PR no repone el evento si falta `sirius:planned`: lo dice y conserva la parada

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
activación y «ninguna automatización puede añadirla». La puerta rechazaba el
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

## Opciones consideradas

1. **Que el reinicio reponga las dos etiquetas** (`planned` incluida), leyendo
   el `continua` del propietario como certificación del alcance. Rechazada
   aquí: cambia lo que `planned` significa —el gesto humano que la puerta de
   activación protege a propósito—, y eso es una decisión del propietario, no
   de este guion. Si la quiere, es un ADR suyo y la puerta cambiaría con él.
2. **Que la puerta deje pasar un reinicio sin `planned`.** Rechazada por lo
   mismo: la puerta rechaza por diseño.
3. **Que el reinicio mire `planned` antes de anunciar y, si falta, lo diga y no
   toque nada. Esta.**

## Decisión

En el camino `sin_pr`, cuando la fase de destino es `sirius:implement-requested`
y la incidencia no lleva `sirius:planned`, el guion:

1. **No repone el evento ni consume la parada** (`failed-safely` o
   `blocked-decision` se quedan): no hay nada que las releve.
2. Publica **una vez por orden** (marcador `sirius-resume-sin-planned:<id del
   comentario>`) que no ha reanudado, por qué (la activación exige `planned`,
   que se consumió y que solo una persona repone), qué habría pasado si
   repusiera solo el evento, y qué hace falta: aplicar `sirius:planned` y
   volver a escribir **continua**. El aviso no empieza por «continua».
3. Con `planned` presente, todo sigue igual: se repone el evento, se conserva
   `planned` y se publica el reinicio.

## Comprobación que la sostiene

`tests/automation/test_reanudar_ejecutando_el_guion.py` ejecuta el guion de
verdad con el doble de `gh`. Los casos existentes de reinicio sin PR siembran
ahora `sirius:planned`, porque sin él nunca pudieron reanudar de verdad; y tres
pruebas nuevas:

- `test_una_parada_sin_pr_sin_planned_no_anuncia_en_verde_ni_consume_la_parada`:
  la parada se conserva, el evento no se repone, `planned` no aparece, el
  aviso lleva su marcador y no se publica el reinicio en verde.
- `test_el_aviso_de_sin_planned_no_empieza_por_continua`.
- `test_una_parada_sin_pr_con_planned_se_reanuda_y_conserva_planned`.

**Mutaciones** (cada una aplicada sobre el guion, la prueba ejecutada, el
fichero restaurado):

| | Mutación | Resultado |
|---|---|---|
| M1 | el reinicio deja de mirar `planned` | cae `…sin_planned_no_anuncia_en_verde…` |
| M2 | el aviso consume la parada | cae la misma: la parada desaparece |
| M3 | con `planned` presente el reinicio deja de reponer la fase | cae `…con_planned_se_reanuda…` |

- El fichero entero en verde; `bash -n`; `ruff`, `mypy` sobre la prueba.
  Batería entera: en la PR.

## Consecuencias

- Un `continua` sobre una parada pre-PR sin `planned` deja la incidencia como
  estaba, con un comentario que dice el gesto que falta; antes la dejaba sin
  etiquetas y en silencio.
- El propietario sigue siendo quien repone `planned`. Si decide que su
  `continua` debe valer como `planned`, va a la hoja de decisiones; este ADR
  no lo decide por él.

## Alternativas descartadas y por qué

Las de «Opciones consideradas».

## La lección

- familia: `prosa-que-el-cambio-deja-falsa`
- sin esto se repetiría: un camino de reinicio escrito cuando activar era una etiqueta, que anuncia «autorizado» sin releer la puerta que ahora exige dos; el aviso en verde era verdad el día que se escribió y dejó de serlo sin que nadie lo tocara.
- lo hace cumplir: `tests/automation/test_reanudar_ejecutando_el_guion.py`
