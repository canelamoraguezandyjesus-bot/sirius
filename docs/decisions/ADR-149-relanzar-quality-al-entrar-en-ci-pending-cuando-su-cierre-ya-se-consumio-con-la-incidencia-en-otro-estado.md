# ADR-149 — Relanzar Quality al entrar en `ci-pending` cuando su cierre ya se consumió con la incidencia en otro estado

- Estado: PROPUESTO
- Fecha: 2026-09-06
- Aprobación: la fusión de esta PR por el propietario (toca `.github/**`, que
  el propietario abrió al operador para el motor; ficha del operador, deuda 3
  de la bitácora de fallos y mejoras del ciclo).

Esta es también la nota de arranque de la rama `claude/deuda-3-quality-relanzado`,
publicada antes del primer cambio de código, con las cuatro preguntas de la
disciplina de evidencia (ADR-001).

## Contexto y problema

La ruta de avance (`advance-sirius-after-quality.yml`) consume el
`workflow_run` de Quality y encamina la incidencia según su estado de origen:
`ci-pending` (cualquier resultado), `failed-safely` y `ready-for-merge` (solo
verdes; H-34 y ADR-142). Pero Quality arranca con el **push** de la PR, y la
incidencia entra en `ci-pending` **después**, cuando el rol termina y
`sirius_apply_verdict.sh` aplica su veredicto (`READY_FOR_REVIEW` o `FIXED`).
Si Quality termina antes de esa transición, su `workflow_run` llega con la
incidencia todavía en `implementing` o `repairing`, no hay candidata, y el
resultado se pierde: el ciclo queda mudo hasta que una persona relanza el run
a mano.

Ocurre por dos vías, las dos medidas en vivo:

- **Rojo rápido del implementador**: la PR #546 (incidencia #545) tuvo un
  rojo de `ruff check` a los 21 s del push; el veredicto llegó un minuto
  después; nadie encaminó el rojo hasta el relanzamiento manual (entrada 41
  de la bitácora).
- **El corrector, siempre en carrera**: tras su push ejecuta la cadena
  completa de comprobación (unos 9 min) antes de escribir `FIXED`, lo mismo
  que tarda Quality: el verde de la PR #542 (incidencia #541) llegó en
  `repairing` y se perdió (entrada 40); antes, tres veces el mismo día
  (entradas 3 y 18).

La puerta del corrector ya resuelve la misma carrera en su rama
«head-movido-tras-ci» (`repair-sirius-work.yml`, revisión de la PR #477):
devuelve la incidencia a `ci-pending`, consulta con el `github.token` si hay
un run de Quality terminado para el head y lo relanza con el PAT, porque un
`workflow_run` emitido a partir del `GITHUB_TOKEN` no despierta al avance
(anti-recursión). Ese remedio existe solo allí; el punto de entrada general a
`ci-pending` no lo tiene.

## Nota de arranque (cuatro preguntas, ADR-001)

**1. ¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo
observar el fallo que arregla?** El fallo es una carrera entre dos eventos
independientes (el cierre de Quality y la transición a `ci-pending`); no vive
en ningún componente, vive entre dos. El arreglo va en el único sitio que sabe
cuándo la incidencia ACABA de entrar en `ci-pending`: la rama
`READY_FOR_REVIEW | FIXED` de `scripts/automation/sirius_apply_verdict.sh`,
justo después de la transición verificada. Sí puede observar el fallo: en ese
instante consulta los runs de Quality del head (`actions/workflows/quality.yml/runs?head_sha=…`)
y ve si alguno ya terminó. Es el mismo dato que la puerta del corrector ya lee.

**2. ¿Qué NO va a garantizar esto?** No cambia la ruta de avance ni sus
orígenes; no decide nada sobre el resultado (un rojo relanzado sigue siendo un
rojo y va al corrector; un verde, a revisión). No cubre un cierre de Quality
que llegue DESPUÉS de la transición: ese ya se consume bien. No garantiza que
el relanzamiento no cueste otra ejecución completa de Quality (unos 9 min):
lo cuesta, y es el precio de no depender de un evento que ya pasó. No toca el
reconciliador ni añade orígenes nuevos.

**3. Criterio de parada (decidido antes de ver ningún resultado).** Las
pruebas nuevas del `gh` simulado se ven FALLAR contra el guion sin la llamada
(mutación: quitar `relanzar_quality_si_ya_termino` de la rama de avance) y
pasar con ella; ninguna prueba existente cambia de intención; la cadena
completa como una sola invocación termina con código 0. Si el relanzamiento
exigiera cambiar la ruta de avance, o si una prueba existente hubiera que
debilitarla, se para y se busca la raíz. En vivo: el primer ciclo en el que
Quality cierre antes de la transición debe dejar un comentario
`QUALITY_RELANZADO` y encaminarse solo, sin relanzamiento manual; si vuelve a
hacer falta la cirugía manual, este ADR queda desmentido y se revisa.

**4. ¿Qué hace esto imposible, en vez de improbable?** Que un cierre de
Quality anterior a la transición quede sin consumir: al entrar en
`ci-pending`, o hay un run activo (su cierre natural encaminará) o hay uno
terminado (se relanza y su nuevo cierre encaminará) o no hay ninguno (el push
aún no lo disparó; llegará con la incidencia ya en `ci-pending`). Las tres
ramas están cubiertas por prueba. Lo que sigue siendo posible: que la lectura
o el relanzamiento fallen; entonces el paso termina en rojo, reintentable, con
la incidencia ya en `ci-pending` y sin marcador de relanzamiento, para que una
reejecución del paso lo intente otra vez. Una lectura caída nunca se
interpreta como «no hay run terminado».

## Criterio de parada (escrito ANTES de decidir)

Ver punto 3 de la nota de arranque. El resultado medido se registra en
«Comprobación que la sostiene».

## Opciones consideradas

1. **Hacer que la ruta de avance busque también en `implementing`/`repairing`.**
   Descartada: consumir un resultado mientras el rol todavía trabaja
   encaminaría la incidencia por debajo de un veredicto que aún no existe
   (un rojo mandaría al corrector mientras el implementador sigue empujando).
2. **Consultar el último run de Quality al entrar en `ci-pending` y encaminar
   directamente desde el veredicto.** Descartada: duplicaría la lógica de la
   ruta de avance en un segundo sitio (candidatas, ambigüedad, marcadores).
3. **Relanzar el run terminado al entrar en `ci-pending`** (elegida): el mismo
   remedio que la puerta del corrector ya aplica, en el punto de entrada
   general; la ruta de avance no cambia y consume el nuevo cierre como
   cualquier otro.
4. **Dejarlo como receta manual documentada.** Es lo que hay hoy; ha costado
   cuatro intervenciones en dos días.

## Decisión

`sirius_apply_verdict.sh` gana `relanzar_quality_si_ya_termino`, llamada en
la rama `READY_FOR_REVIEW | FIXED` inmediatamente después de la transición
verificada a `ci-pending`:

- Lee los runs de Quality del head (`event=pull_request`) con
  `SIRIUS_READ_TOKEN` (el `github.token` del paso, con `actions: read`) si el
  workflow lo da, y con el token de la invocación si no.
- Si hay alguno en cola o corriendo, no hace nada: su cierre natural
  encaminará la incidencia.
- Si no hay ninguno, no hace nada: el push aún no lo disparó.
- Si el más reciente está terminado, lo relanza (`POST …/rerun`) con el
  token de la invocación, el PAT, y publica una vez el marcador
  `sirius-quality-relanzado:<head>:<run>` con un comentario
  `QUALITY_RELANZADO`. El marcador hace idempotente el relanzamiento ante una
  reejecución del paso.
- Una lectura caída, una respuesta ilegible o un relanzamiento fallido
  terminan el paso en rojo (reintentable) con la incidencia ya en
  `ci-pending` y sin marcador.

Los dos workflows que aplican veredictos de avance dan al paso
`SIRIUS_READ_TOKEN: ${{ github.token }}`; `implement-sirius-work.yml` gana el
permiso `actions: read` (el del corrector ya lo tenía). La ruta de avance no
cambia.

## Comprobación que la sostiene

Ejecutado el 06-09-2026 en el contenedor del operador, sobre esta rama:

1. **Pruebas nuevas** en `tests/automation/test_sirius_apply_verdict.py`
   (ocho, con el `gh` simulado, que ahora sirve los runs de Quality del head
   y registra el relanzamiento con el token que lo pide): relanza un run
   terminado y publica el marcador una vez; no relanza si hay uno en curso;
   no relanza sin runs; `FIXED` del corrector también relanza; un marcador
   ya publicado no repite; el relanzamiento fallido deja el paso en rojo con
   la incidencia en `ci-pending` y sin `failed-safely`; la consulta caída
   deja el paso en rojo, no en verde; la lectura va con el token de lectura
   y el POST con el de la invocación. Más tres guardianes en
   `tests/automation/test_quality_relanzado_al_entrar_en_ci_pending.py`
   (token de lectura en los dos workflows, `actions: read` en los dos, y la
   llamada en la rama de avance con la doctrina de tokens).
2. **Mutación (ADR-001), vista caer y restaurada por copia:** sustituir la
   llamada `relanzar_quality_si_ya_termino` de la rama de avance por `true`
   hace caer **6 de las 9** pruebas seleccionadas
   (`uv run pytest tests/automation/test_sirius_apply_verdict.py -k "relanza
   or quality or consulta_de_runs or lectura_va_con"` → `6 failed, 3 passed`);
   las tres que siguen pasando afirman ausencias (sin runs, run en curso,
   marcador ya publicado), como deben. Restaurado el guion, `git diff` solo
   contiene las 75 líneas de este cambio.
3. **Batería de automatización completa** (`uv run pytest tests/automation`):
   `1174 passed, 10 skipped, 1 failed` antes de actualizar el guardián
   `test_there_is_no_measured_diagnosis_step`, que fija el entorno completo
   del paso del veredicto del corrector y vio la variable nueva; se añade
   `SIRIUS_READ_TOKEN` a su lista con su motivo (no lleva texto ni entra en
   ningún comentario). Ninguna otra prueba cambia.
4. **Cadena completa como una sola invocación** (`ruff format --check`,
   `ruff check`, `mypy src tests`, `pytest`): resultado y código de salida
   transcritos en el cuerpo de la PR, sobre su head definitivo.
5. **Lo que NO se ha medido:** el caso en vivo. El primer ciclo en el que
   Quality cierre antes de la transición tiene que dejar su
   `QUALITY_RELANZADO` y encaminarse solo; hasta entonces la deuda 3 queda
   «arreglo fusionado, sin dato en vivo».

## Corrección (06-09-2026, 14:51 UTC): el fallo del relanzamiento se cuenta en la incidencia

Primer caso real, en #545: Quality terminó para `242e8b3` a las 14:50:20 y
el veredicto `FIXED` entró en `ci-pending` a las 14:51:10 —la carrera exacta
de la deuda 3—. Gracias a ADR-152 corrió este guion desde `main`: la lectura
con el `github.token` encontró el run terminado (34039974177) y el
relanzamiento con el PAT devolvió cuatro veces `HTTP 403: Resource not
accessible by personal access token`. El paso terminó en 1 y la incidencia se
quedó en `ci-pending`, tal como esta decisión prescribe.

Dos cosas que esta decisión no había dicho:

1. **El PAT necesita el permiso «Actions: Read and write»** en el
   repositorio para `POST actions/runs/{id}/rerun`. La lectura no lo
   necesita (va con el `github.token` y `actions: read`), así que las
   pruebas con el `gh` simulado no podían verlo. Es un gesto del propietario
   en la configuración del token, pedido el 06-09; hasta entonces, cada
   carrera perdida exige relanzar el run a mano.
2. **Un `::error` en el log no lo lee nadie.** La incidencia se quedó 14
   minutos en `ci-pending` sin ningún rastro visible hasta que el operador la
   miró. Ahora, cuando la consulta o el relanzamiento fallan, el guion
   publica una sola vez (marcador `sirius-quality-sin-encaminar:<head>:<fase>[:<run>]`)
   un aviso `QUALITY_SIN_ENCAMINAR` con la fase, el detalle que dio `gh`, el
   run terminado si se conoce y el gesto que desbloquea (relanzar a mano, o
   el permiso del PAT si el detalle es el 403). El paso sigue terminando en 1
   y la incidencia sigue en `ci-pending`: nada cambia en el encaminamiento,
   solo deja de ser silencioso.

Guardianes: los dos casos de fallo (`consulta-runs-fallida`,
`relanzamiento-fallido`) exigen el aviso con el detalle de `gh` y el
marcador; un tercer caso fija que reejecutar el paso con el marcador ya
publicado no duplica el aviso. Vistos fallar contra el guion anterior.

## Consecuencias

- La receta manual «reponer `ci-pending` y relanzar el run» deja de ser
  necesaria para esta carrera; sigue valiendo para las demás situaciones que
  el reconciliador cubre.
- Cada carrera perdida cuesta ahora una ejecución extra de Quality (unos
  9 min) en vez de una intervención humana. La puerta del corrector conserva
  su rama propia: cubre un caso distinto (el head se movió con la incidencia
  en `repair-requested`).
- Deuda 3 de la bitácora: saldada cuando esta PR se fusione y el primer caso
  en vivo deje su `QUALITY_RELANZADO`.

## Alternativas descartadas y por qué

Ver «Opciones consideradas».
