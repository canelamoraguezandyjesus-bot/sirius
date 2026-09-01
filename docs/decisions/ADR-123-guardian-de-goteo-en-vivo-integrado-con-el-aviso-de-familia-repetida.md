# ADR-123 — Guardián de goteo en vivo, integrado con el aviso de familia repetida

- Estado: APROBADO
- Fecha: 2026-08-31
- Aprobación: fusión de la PR por el propietario
- Contexto: incidencia #496 (Work ID WI-20260831-202513), que implementa la
  propuesta 1 de §7 de `docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-08.md`
  (informe de la mina, incidencia #493, fusionado en la PR #494); integrada
  sobre `main` en la incidencia #501 (Work ID WI-20260831-211729), porque la
  rama original (`feature/496-guardian-goteo`, PR #499) quedó por detrás de la
  PR #497 (incidencia #495) que cableó, mientras tanto, el aviso de familia
  repetida en el mismo punto de publicación.
- Relacionadas: ADR-121 (cablea el aviso de familia repetida al mismo
  comentario `CHANGES_REQUESTED`; este ADR documenta cómo coexisten los dos),
  ADR-078 (mismo `parse_round_records`, misma disciplina de medir antes de
  fijar un criterio; también documenta por qué las decisiones de cablear a
  `.github/**` quedan fuera de este tipo de bloque), incidencia #267 (criterio
  de entrada de cualquier guardián mecánico: solo entra si informa, y solo
  gana autoridad si la tasa medida en producción lo justifica)

## Nota de arranque (antes del primer commit, ADR-001)

1. **¿Dónde vive el fallo y dónde va el arreglo?** El "fallo" que se ataca es
   el goteo de hallazgos tardíos que la mina midió en `§3`: el revisor CLAUDE
   publica, en rondas N>1, hallazgos sobre contenido que ya era idéntico en
   la ronda 1 (30.6% de sus 36 hallazgos tardíos muestreados, frente al 2.2%
   de CODEX). El arreglo vive en `scripts/automation/sirius_apply_verdict.sh`
   -el único punto donde se construye y publica el comentario
   `CHANGES_REQUESTED` de una ronda- y en un módulo puro nuevo,
   `src/sirius_engine/drip_guard.py`. Ese punto SÍ puede observar el fallo:
   en el momento de publicar la ronda N ya conoce el head que se está
   publicando (`head_sha`), el historial completo de rondas anteriores (vía
   `sirius_dump_comments` + `parse_round_records`, que ya expone el head de
   la ronda 1) y las observaciones exactas que va a publicar -exactamente los
   mismos datos que el informe de la mina usó a mano en `§3.1`, ahora en el
   momento en que importan y no meses después en una auditoría.

   Sobre ese mismo punto, `main` ya trae fusionado (PR #497, incidencia #495)
   el aviso de familia repetida: los dos avisos leen y anotan el mismo
   `history_dump` en el mismo bloque `CHANGES_REQUESTED`, así que la
   integración tiene que decidir cómo comparten ese punto sin pisarse.
2. **¿Qué NO va a garantizar esto?**
   - No bloquea nada, no cambia ninguna transición de estado ni descarta
     ningún hallazgo: es solo informativo (regla (a) de la incidencia #496 y
     criterio de entrada de la incidencia #267 -un guardián mecánico gana
     autoridad para bloquear solo después de medirse en producción-). Lo
     mismo vale, sin cambios, para el aviso de familia repetida (ADR-121):
     ninguno de los dos gana autoridad sobre el otro ni sobre la transición.
   - No detecta el matiz de "línea de contexto sin tocar cuya línea hermana
     del mismo hunk sí cambió", que la propia mina documenta como sus dos
     únicos falsos positivos conocidos (`§459` rondas 3 y 4, `§5`): se declara
     limitación conocida (ver "Consecuencias"), no se implementa la
     heurística de comparar líneas hermanas dentro del mismo hunk.
   - No aplica cuando el hallazgo no cita una línea de un fichero real del
     repositorio (el nivel "manual" del informe de la mina, `§3.1`): sin línea
     no hay heurística mecánica posible sin razonar sobre el `patch` completo,
     y ese nivel queda fuera de esta incidencia. El guardián simplemente no
     opina sobre esos hallazgos.
   - No garantiza disponibilidad: una lectura fallida de
     `gh api .../compare` nunca se trata como "no hubo cambios" (regla (c) de
     la incidencia #496); el guardián se calla y lo declara.
   - La integración no cambia la política de convergencia real: el registro
     (`sirius_convergence.py record`) se sigue construyendo a partir de las
     observaciones SIN anotar por ninguno de los dos avisos.
3. **Criterio de parada, decidido antes de escribir ninguna prueba:**
   - Las cinco pruebas exigidas por la incidencia #496 (fichero sin cambios →
     marca; línea fuera de todo hunk → marca; línea dentro de un hunk añadido
     → no marca; lectura de la API caída → no marca y lo declara; ronda 1 →
     nunca marca) tienen que verse FALLAR con una implementación trivial
     ("siempre marca" o "nunca marca", según el caso) antes de aceptarse como
     verdes con la implementación real (prueba por mutación, disciplina de
     evidencia §3).
   - Las dos pruebas de extremo a extremo del cableado en
     `sirius_apply_verdict.sh` tienen que verse FALLAR contra el `main`
     actual (sin el guardián cableado) antes de aceptarse como verdes tras la
     integración.
   - Las pruebas ya existentes de `sirius_apply_verdict.sh` -incluidas las
     dos que el aviso de familia repetida añadió (ADR-121)- no pueden cambiar
     de resultado: si alguna se rompe al integrar el guardián de goteo, es una
     señal de que los dos avisos se están pisando y hay que parar a revisar el
     diseño, no a parchear la prueba.
   - Dos rondas de revisión seguidas con defectos de la misma familia →
     parar y buscar la causa raíz en vez de seguir parcheando.
   - Si integrar el guardián al flujo real de publicación exige tocar
     `.github/**`, el bloque se detiene con `BLOCKED_BY_DECISION`: la
     incidencia #496 fija ese límite explícitamente y ADR-078 ya documentó
     por qué ese tipo de cableado es una decisión aparte (ADR-002).
   - Todas las validaciones obligatorias del proyecto en verde antes de abrir
     la PR.
4. **¿Qué haría el fallo imposible, no solo improbable?** El resultado del
   guardián se modela con un tipo explícito de tres valores (marca posible /
   no marca / sin información), nunca con un booleano: una lectura fallida de
   la API produce el mismo valor que "sin información", que es
   estructuralmente distinto de "el fichero no cambió" (que sí es información
   positiva). No hay ninguna rama del código que pueda convertir un fallo de
   lectura en una marca, porque esa rama de "marcar" solo se alcanza cuando el
   resultado de comparación llegó con éxito. La prueba por mutación (punto 3)
   verifica esto en las dos direcciones para cada uno de los cinco escenarios.
   Sobre la integración: el registro de convergencia lee `$observations`
   (variable que ninguno de los dos avisos reasigna), nunca la variable
   anotada `readable_observations`/`readable`, así que un fallo de
   serialización de cualquiera de los dos avisos no puede alterar la huella
   ni la gravedad agregada que sostienen la política de convergencia real.

## Contexto y problema

`docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-08.md` (§3, §5 y §7.1)
midió que el 30.6% de los hallazgos que el revisor CLAUDE publica en rondas
N>1 son "goteo real": el fichero y la línea citados ya eran idénticos en la
ronda 1, así que el hallazgo pudo -y debió- verse entonces. El propio
mecanismo que la mina usó para medirlo a mano (`gh api
repos/.../compare/{head_ronda_1}...{head_actual}`, restringido al fichero
citado) es reproducible en vivo, en el momento exacto en que se publica cada
ronda, en vez de aplicarse meses después sobre datos históricos.

La incidencia #496 implementó ese guardián en la rama
`feature/496-guardian-goteo` (head `8901612`, PR #499), con el módulo puro,
su CLI y sus pruebas completas y en verde. Mientras esa rama esperaba
revisión, la PR #497 (incidencia #495) fusionó a `main` el cableado del aviso
de familia repetida en el mismo punto exacto de `sirius_apply_verdict.sh`
-la rama `CHANGES_REQUESTED`, justo antes de publicar el comentario-, lo que
dejó a la PR #499 con un conflicto que ella misma había anticipado. Esta
incidencia (#501) reincorpora el guardián de goteo resolviendo ese conflicto:
integra el material ya construido y medido sobre el `main` real, en vez de
volver a implementarlo desde cero.

## Criterio de parada (escrito ANTES de decidir)

Ver "Nota de arranque" arriba, punto 3. Ninguno se disparó: las cinco pruebas
del módulo puro y las dos de extremo a extremo del cableado pasan por
mutación (ver "Comprobación que la sostiene"), no hubo dos rondas de revisión
con la misma familia de defecto, integrar el guardián a
`sirius_apply_verdict.sh` no tocó `.github/**`, las pruebas ya existentes de
ese fichero -incluidas las de familia repetida- no cambiaron de resultado, y
las validaciones obligatorias están en verde.

## Opciones consideradas

1. **Guardián puro + CLI cargado por ruta de fichero, invocado desde
   `sirius_apply_verdict.sh` con `python3` de sistema, reutilizando el
   `history_dump` que la rama `CHANGES_REQUESTED` ya lee una vez para numerar
   la ronda y comprobar familia repetida** (elegida). Mismo patrón que
   `scripts/automation/sirius_convergence.py` ya usa para `round_history.py`:
   ese script se ejecuta con el `python3` del sistema, sin el proyecto
   instalado (`repair-sirius-work.yml`), así que un `import sirius_engine...`
   normal rompería en producción aunque pasara toda la suite bajo `uv run
   pytest`. Reutilizar el volcado ya leído (en vez de que el guardián de
   goteo pida el suyo propio, como hacía la rama original antes de la
   integración) mantiene en una sola lectura a la API lo que antes hacía cada
   llamador por separado.
2. **Meter la lógica directamente en `sirius_convergence.py`.** Descartada:
   ese script tiene una responsabilidad concreta (política de convergencia,
   `record`/`decide`) y mezclar un guardián informativo sin relación con esa
   decisión habría acoplado dos cosas que cambian por motivos distintos. El
   guardián no participa en absoluto de la decisión CONTINUE/BLOCK.
3. **Reproducir la heurística de "línea hermana del mismo hunk" (`§459`
   rondas 3-4) para eliminar los 2 falsos positivos conocidos.** Descartada
   para esta primera versión: la propia incidencia #496 permite declararla
   como limitación conocida en vez de implementarla, y la nota de arranque
   (punto 2) ya la declara así.
4. **Sección propia `AVISO_GOTEO_POSIBLE`, separada de
   `OBSERVACIONES_ESTRUCTURADAS`, en vez de anotar cada observación en la
   línea legible.** Descartada: habría duplicado, en dos sitios del mismo
   comentario, la lista de hallazgos (una vez sin marcar en
   `OBSERVACIONES_ESTRUCTURADAS`, otra vez marcada aparte), y el corrector que
   re-extrae ese bloque JSON tendría que cruzar las dos secciones a mano para
   saber cuál hallazgo tiene la marca. Anotar `posible_goteo` en la propia
   línea legible de cada hallazgo -sin tocar el bloque JSON
   `OBSERVACIONES_ESTRUCTURADAS`, que sigue siendo `$observations` sin
   anotar- mantiene una sola fuente por hallazgo y dos afirmaciones
   independientes conviviendo sin remitirse la una a la otra.

## Decisión

Se implementa el guardián de goteo como:

- `src/sirius_engine/drip_guard.py`: módulo puro (mismo patrón que
  `round_family_detector.py`) con `evaluate_finding` (evalúa un hallazgo
  contra los registros de ronda ya parseados y un `fetch` de comparación
  inyectado) y `annotate_observations` (anota una lista de observaciones con
  el mensaje exacto que pide la incidencia #496 cuando corresponde). El
  resultado de cada evaluación es `DripVerdict`, un enum de tres valores
  (`POSIBLE_GOTEO`, `SIN_MARCA`, `SIN_INFORMACION`) -nunca un booleano-, para
  que un fallo de lectura no pueda confundirse por tipo con "no hubo
  cambios". También vive aquí `gh_compare_file`, la única función impura del
  módulo: invoca `gh api .../compare/{head1}...{head2}` (biblioteca estándar,
  `subprocess`) y traduce cualquier fallo (proceso, JSON, timeout) en `None`.
- `scripts/automation/sirius_drip_guard_cli.py`: línea de órdenes que carga
  `round_history.py` y `drip_guard.py` por ruta de fichero (como
  `sirius_convergence._cargar_round_history`), lee el historial de
  comentarios ya volcado y las observaciones de la ronda que se va a
  publicar, y escribe la lista anotada. Nunca falla el proceso completo: ante
  cualquier error (historial ilegible, `gh` no disponible) escribe las
  observaciones sin anotar y lo declara por `stderr`, porque el guardián es
  estrictamente informativo (regla (a) de la incidencia #496).
- `scripts/automation/sirius_apply_verdict.sh` (rama `CHANGES_REQUESTED`):
  después de sanear las observaciones (`sanitize_untrusted_json`, para que el
  guardián nunca razone sobre texto no neutralizado) y de leer el
  `history_dump` (que la rama ya lee una vez, compartido con la numeración de
  ronda y con el aviso de familia repetida), se invoca el CLI con el head de
  la ronda 1 -leído de ese mismo historial- y el head actual. El campo
  `posible_goteo`, si aparece, se añade a la línea legible de cada
  observación (`readable`); el registro de convergencia
  (`sirius_convergence.py record`, que decide el bloqueo real del ciclo)
  sigue construyéndose a partir de `$observations` SIN anotar: el guardián no
  puede, ni por accidente de serialización, alterar la huella
  (`fingerprint`) ni la gravedad agregada que sostienen la política de
  convergencia real.

No se cablea nada en `.github/**`: el punto de invocación es
`sirius_apply_verdict.sh`, que ya vive en `scripts/automation/` y que los
workflows existentes ya invocan sin cambios en esta incidencia.

### Integración con el aviso de familia repetida (incidencia #501)

Los dos avisos -goteo (este ADR) y familia repetida (ADR-121)- conviven en el
mismo comentario `CHANGES_REQUESTED`, publicado por el mismo bloque de
`sirius_apply_verdict.sh`. La integración decide, y deja escrito aquí, cómo:

- **Una sola lectura compartida.** Los dos avisos leen el mismo
  `history_dump` (`sirius_dump_comments`, volcado una vez): el guardián de
  goteo lo usa ANTES de que se le añada el registro de la ronda actual (solo
  necesita el head de la ronda 1, ya presente en el historial), y el aviso de
  familia repetida lo usa DESPUÉS, con el registro de la ronda actual ya
  anexado (necesita ver la ronda actual para poder comparar familias). El
  orden de las dos llamadas en el script sigue exactamente ese requisito de
  datos, no una preferencia arbitraria.
- **Orden de las secciones en el comentario publicado, de arriba abajo:**
  1. `## CHANGES_REQUESTED` y el resumen del revisor (sin cambios).
  2. `## OBSERVACIONES_ESTRUCTURADAS`: la lista legible (`readable`), con la
     marca `⚠️ Guardián de goteo: …` insertada en la línea de cada
     observación afectada, seguida del bloque JSON sin anotar
     (`$observations`).
  3. `## AVISO_FAMILIA_REPETIDA` (ADR-121), si aplica: sección aparte, porque
     -a diferencia del goteo, que es una propiedad de un hallazgo
     individual- la familia repetida es una propiedad de la RONDA completa
     frente al historial, y no tiene un hallazgo único al que anclarse dentro
     de la lista.
  4. `## RONDA_HALLAZGOS` (registro de convergencia, sin cambios).

  Ningún aviso se inserta entre el marcador oculto
  (`<!-- sirius-verdict:... -->`) y `## CHANGES_REQUESTED`, ni entre
  `## RONDA_HALLAZGOS` y su bloque JSON: los dos analizadores que re-extraen
  esas dos anclas (`require_reviewed_head`/el gate del corrector y
  `parse_round_records`) siguen encontrando exactamente el mismo texto
  inmediatamente después de cada marcador.
- **Independencia de fallos.** Cada aviso es best-effort por separado: un
  fallo del guardián de goteo (CLI, `gh api compare`, JSON corrupto) publica
  `$observations` sin anotar y dejar el resto del flujo -incluido el aviso de
  familia repetida- intacto; un fallo del detector de familia repetida
  (`sirius_convergence.py family-check`) deja `family_notice` vacío y no
  afecta en nada al guardián de goteo ni a la lista de observaciones. Ninguno
  de los dos puede tumbar al otro ni la transición de estado.
- **Ninguno cambia la transición.** La etiqueta `sirius:repair-requested` se
  sigue aplicando siempre en la rama `CHANGES_REQUESTED`, exactamente igual
  que antes de que existiera cualquiera de los dos avisos.

## Comprobación que la sostiene

`uv run pytest tests/engine/test_drip_guard.py
tests/automation/test_sirius_drip_guard_cli.py
tests/automation/test_sirius_apply_verdict.py -q` cubre, cada uno de los
cinco escenarios exigidos por la incidencia #496, visto fallar primero con
mutaciones introducidas a propósito sobre la implementación real (prueba por
mutación, disciplina de evidencia §3) y en verde restaurado:

- fichero sin cambios entre la ronda 1 y la ronda actual → `POSIBLE_GOTEO`
  (`test_fichero_sin_cambios_entre_ronda_1_y_n_marca`).
- línea citada fuera de todo hunk modificado (fichero cambió en otro punto)
  → `POSIBLE_GOTEO` (`test_linea_fuera_de_todo_hunk_marca`).
- línea citada dentro de un hunk, en una línea añadida/modificada →
  `SIN_MARCA` (`test_linea_dentro_de_un_hunk_anadido_no_marca`; mutada a
  "siempre marca" y vista fallar antes de restaurar).
- lectura de la API de comparación caída (`fetch` devuelve `None`) →
  `SIN_INFORMACION`, nunca `POSIBLE_GOTEO`
  (`test_lectura_de_la_api_caida_no_marca_y_se_declara_distinta_de_sin_cambios`;
  mutada a "trata el fallo como sin cambios" y vista fallar antes de
  restaurar).
- ronda 1 (no hay ronda anterior con la que comparar) → siempre `SIN_MARCA`,
  incluso con un `fetch` que marcaría
  (`test_ronda_1_nunca_marca_ni_siquiera_si_el_fetch_diria_que_si`).

`tests/automation/test_sirius_apply_verdict.py` fija el cableado de extremo a
extremo dentro de `sirius_apply_verdict.sh`, con `gh api compare` simulado:
un hallazgo sobre un fichero sin cambios desde la ronda 1 aparece marcado en
el comentario publicado
(`test_drip_guard_marks_a_finding_whose_file_did_not_change_since_round_1`,
vista FALLAR contra el cableado anterior a esta integración) y uno sobre una
línea añadida no lo está
(`test_drip_guard_does_not_mark_a_finding_on_an_added_line`), sin romper
ninguna de las pruebas ya existentes de ese fichero -incluidas las dos que el
aviso de familia repetida añadió (ADR-121)-.

Suite completa: `uv run ruff format --check .`, `uv run ruff check .`,
`uv run mypy src tests`, `uv run pytest` y `git diff --check`, todas en verde
(ver PR).

## Consecuencias

- El guardián reduce, pero no elimina, el goteo tardío: sobre la muestra de
  la mina habría señalado 10 de 12 goteos reales confirmados (83.3%), con 2
  falsos positivos conocidos y no implementados (`§459` rondas 3 y 4, ver
  "Nota de arranque" punto 2 y "Opciones consideradas" punto 3). Ampliar esa
  cobertura es trabajo aparte, sujeto a medir primero (criterio de la
  incidencia #267), no de este bloque.
- No cambia ninguna transición de estado del ciclo revisión-corrección: un
  hallazgo marcado como posible goteo se corrige exactamente igual que uno
  sin marcar. La marca sirve para medir la tasa real en producción antes de
  darle cualquier autoridad (criterio de la incidencia #267). Lo mismo vale
  para el aviso de familia repetida (ADR-121): los dos coexisten como
  observación pura de producción, sin ninguna autoridad todavía.
- Solo actúa sobre hallazgos que citan una línea de un fichero real del
  repositorio. Un hallazgo que cita el cuerpo de una Pull Request, un mensaje
  de commit o prosa sin ruta (el nivel "manual" del informe de la mina, con
  el 80.9% de los hallazgos tardíos de la muestra) queda fuera del alcance de
  este guardián y no recibe ninguna marca, ni positiva ni negativa.
- Depende de que `gh` esté disponible en el runner que ejecuta
  `sirius_apply_verdict.sh` (ya lo está: el resto del script ya depende de
  `gh` para todo lo demás, incluido el propio aviso de familia repetida). Si
  `gh api compare` falla o se agota el tiempo de espera, el guardián se calla
  para esa observación concreta y el resto del flujo de publicación de la
  ronda continúa sin cambios.
- Cada ronda `CHANGES_REQUESTED` con `python3` disponible ejecuta ahora dos
  procesos Python adicionales sobre el mismo `history_dump`
  (`sirius_drip_guard_cli.py` y `sirius_convergence.py family-check`), en vez
  de uno: coste medido como aceptable frente al de leer dos veces el
  historial de comentarios por la API, que es lo que se evitó al compartir el
  volcado.

## Alternativas descartadas y por qué

Ver "Opciones consideradas" arriba.
