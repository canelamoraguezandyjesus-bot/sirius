# ADR-219 — El motor dice lo que hace: el veredicto nombra su PR, el aviso de «listo» no pide una autorización que ya no necesita y una casi-orden recibe respuesta

- Estado: APROBADO
- Fecha: 2026-10-01
- Aprobación: la fusión de la PR por el motor con aprobación dual (ADR-205).
- Nota de arranque: `docs/audits/arranque-2026-10-01-el-motor-dice-lo-que-hace.md`,
  publicada en el commit `4191995d` (01-10-2026, 07:26 UTC), antes del primer
  commit de arreglo.

## Contexto y problema

Tres textos del motor, tres formas de no decir lo que pasa. Los tres vienen de
la bitácora del ciclo (entradas 29, 100 y 146) y los midió la mina de
septiembre (§6.4) sobre el volcado de la API del mes:

1. **El veredicto `CHANGES_REQUESTED` nunca nombró su PR.** La línea
   `- PR: <pista>` existía en `sirius_apply_verdict.sh` y no se publicó ni una
   vez: **0 de 128** veredictos en septiembre, 0 de 240 desde que existe.
   Reproducido en bash: `printf '- PR: %s\n' …` empieza por guion y bash lo lee
   como opción (`printf: - : invalid option`); el error salía al log del run,
   `set -e` no lo detenía porque el `printf` estaba dentro de un bloque `{ … }`
   redirigido, y el resto del comentario se publicaba sin la línea. El
   corrector que lee el veredicto no sabe en qué PR trabaja.
2. **El aviso de «listo para fusionar» pedía «escribe fusiona».** Era verdad
   hasta ADR-205 (20-09-2026, 18:09 UTC): 38 avisos en septiembre lo dijeron
   con razón. Desde entonces el motor fusiona solo cuando los dos revisores
   aprueban el mismo head, y el aviso siguió pidiendo una autorización que no
   hacía falta: **1 vez** (#653, 21-09 14:24), y lo habría repetido en cada
   «listo» siguiente. El propietario escribió `fusiona` tres veces en #653
   antes de que nadie le dijera que no hacía falta.
3. **Una orden `continua` casi exacta salía en silencio.** El guion de
   reanudación exige la palabra sola (quitando la firma); si el comentario
   empieza por `continua` y sigue con algo, salía con `exit 0` y «no es la
   orden exacta» solo en el log del run. En septiembre pasó **1 vez** (#523,
   04-09 15:57: «continua  Decisión registrada: …»). Es un caso: demasiado
   pequeño para sostener una tasa. Se arregla por el coste de callar, no por la
   frecuencia: el propietario ordena, nada pasa, y nadie le dice por qué.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque: no tocar la máquina de estados, solo los textos y la
respuesta; que el aviso de casi-orden no pueda dispararse a sí mismo; tres
mutaciones vistas caer.

## Opciones consideradas

1. **Quitar la línea `- PR:`** ya que nunca salió y nadie la echó de menos.
   Rechazada: el corrector la necesita (ADR-175 puso la PR en el tablero por
   lo mismo), y «nadie la echó de menos» mide la ceguera, no la utilidad.
2. **Que la casi-orden se interprete como orden** (tomar la primera palabra).
   Rechazada: la orden exacta existe para que una frase que menciona
   «continua» no reanude el motor; lo que falta es la respuesta, no la
   permisividad.
3. **Arreglar los tres textos y añadir la respuesta a la casi-orden, con las
   pruebas que fijan cada uno. Esta.**

## Decisión

1. `sirius_apply_verdict.sh` publica la línea con `printf '%s\n' "- PR: …"`:
   el texto va como argumento, nunca como formato. Vale para los dos caminos
   del veredicto (con y sin familia repetida).
2. El aviso de `ready-for-merge` (`notify-sirius-state.yml`) dice lo que va a
   pasar: «el motor fusiona la PR por sí solo en cuanto los dos revisores
   aprueban el mismo head (ADR-205): no necesitas autorizarlo», y conserva la
   salida de emergencia: «si en una hora sigue sin fusionarse, escribe
   **fusiona**». La descripción de la etiqueta en `sirius_apply_verdict.sh`
   dice lo mismo.
3. `sirius_resume_on_command.sh`: si el comentario no es la orden exacta pero
   su primera palabra es `continua`/`continúa`, publica una vez por comentario
   (marcador `sirius-resume-not-an-order:<id>`) un aviso que dice que no ha
   reanudado y cuál es la orden exacta. El aviso lo publica
   `github-actions[bot]`: `resume-sirius-on-command.yml` da al guion
   `GH_TOKEN: github.token` y solo cambia a `SIRIUS_TRIGGER_TOKEN` para mover
   etiquetas, y el workflow de reanudación solo escucha comentarios con
   `author_association == OWNER`, así que el aviso no puede dispararse a sí
   mismo por identidad (lo precisó Codex en la ronda 1 de la PR #666: la nota
   de arranque decía «publica como `OWNER`», y no es así). Que además **no
   empiece por «continua»** es defensa en profundidad para el día en que el
   token cambie. Un comentario que no empieza por esa palabra sigue sin
   respuesta, como antes.

## Comprobación que la sostiene

- `tests/automation/test_sirius_apply_verdict.py::test_changes_requested_names_the_pr_on_its_own_line`:
  el veredicto generado por el guion lleva `- PR: <pista>` en su propia línea.
- `tests/automation/test_sirius_notifications.py::test_el_aviso_de_listo_no_pide_una_autorizacion_que_el_motor_ya_no_necesita`:
  el bloque de `ready-for-merge` no contiene «Solo falta tu autorización»,
  nombra ADR-205 y conserva **fusiona** como salida de emergencia.
- `tests/automation/test_reanudar_ejecutando_el_guion.py::test_una_orden_casi_exacta_avisa_en_vez_de_callar`
  y `::test_un_comentario_que_no_es_una_orden_sigue_sin_respuesta`: los dos
  lados de la regla, ejecutando el guion de verdad con el doble de `gh`.
- Mutaciones (cada una aplicada, la batería de los cuatro ficheros ejecutada,
  el fichero restaurado): M1 `printf '- PR: %s\n'` de vuelta → cae
  `names_the_pr_on_its_own_line`; M2 «Solo falta tu autorización» de vuelta →
  cae `no_pide_una_autorizacion`; M3 la casi-orden sin aviso → cae
  `avisa_en_vez_de_callar`.
- Batería entera sobre `727bda1f`: **7 471 en verde**, 16 saltadas, 2 xfail
  (15 min 17 s). `ruff format --check`, `ruff check`, `mypy src tests`:
  limpios. Comprobador de documentos sobre este ADR y la nota: sin defectos.
  `MEMORIA.md` e `INDICE.md` regenerados y comprobados.
- Tras el cambio, medido sobre el propio guion con el doble de `gh`: el
  veredicto generado lleva `- PR: <pista>` en su propia línea (antes, 0 de 128
  en septiembre); el bloque de «listo» no contiene «Solo falta tu
  autorización»; la casi-orden recibe su aviso y el comentario que no es orden
  no recibe nada.

## Consecuencias

- El corrector lee la PR en el veredicto desde la próxima ronda; el tablero
  (ADR-175) la seguía dando, así que no hubo pérdida de camino, sí de claridad.
- El propietario deja de escribir `fusiona` por costumbre; si alguna vez el
  motor no fusiona en una hora, la salida sigue ahí.
- Una casi-orden recibe un comentario; el log del run deja de ser el único
  sitio donde se explica una parada.

## Alternativas descartadas y por qué

Las de «Opciones consideradas».

## La lección

- familia: `prosa-que-el-cambio-deja-falsa`
- sin esto se repetiría: cambiar la regla (ADR-205) y dejar el aviso que la contaba al propietario diciendo la regla vieja; y dar por publicada una línea de un comentario sin haber leído nunca un comentario publicado.
- lo hace cumplir: `tests/automation/test_sirius_notifications.py`
