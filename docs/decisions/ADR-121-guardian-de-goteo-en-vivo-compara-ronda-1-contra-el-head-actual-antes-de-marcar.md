# ADR-121 — Guardian de goteo en vivo compara ronda 1 contra el head actual antes de marcar

- Estado: PROPUESTO
- Fecha: 2026-08-31
- Aprobación: fusión de la PR por el propietario
- Contexto: incidencia #496 (Work ID WI-20260831-202513), que implementa la
  propuesta 1 de §7 de `docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-08.md`
  (informe de la mina, incidencia #493, fusionado en la PR #494)
- Relacionadas: ADR-078 (mismo `parse_round_records`, misma disciplina de
  medir antes de fijar un criterio; también documenta por qué las decisiones
  de cablear a `.github/**` quedan fuera de este tipo de bloque), incidencia
  #267 (criterio de entrada de cualquier guardián mecánico: solo entra si
  informa, y solo gana autoridad si la tasa medida en producción lo justifica)

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
2. **¿Qué NO va a garantizar esto?**
   - No bloquea nada, no cambia ninguna transición de estado ni descarta
     ningún hallazgo: es solo informativo (regla (a) de la incidencia #496 y
     criterio de entrada de la incidencia #267 -un guardián mecánico gana
     autoridad para bloquear solo después de medirse en producción-).
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
3. **Criterio de parada, decidido antes de escribir ninguna prueba:**
   - Las cinco pruebas exigidas por la incidencia #496 (fichero sin cambios →
     marca; línea fuera de todo hunk → marca; línea dentro de un hunk añadido
     → no marca; lectura de la API caída → no marca y lo declara; ronda 1 →
     nunca marca) tienen que verse FALLAR con una implementación trivial
     ("siempre marca" o "nunca marca", según el caso) antes de aceptarse como
     verdes con la implementación real (prueba por mutación, disciplina de
     evidencia §3).
   - Dos rondas de revisión seguidas con defectos de la misma familia →
     parar y buscar la causa raíz en vez de seguir parcheando.
   - Si cablear el guardián al flujo real de publicación exige tocar
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

## Contexto y problema

`docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-08.md` (§3, §5 y §7.1)
midió que el 30.6% de los hallazgos que el revisor CLAUDE publica en rondas
N>1 son "goteo real": el fichero y la línea citados ya eran idénticos en la
ronda 1, así que el hallazgo pudo -y debió- verse entonces. El propio
mecanismo que la mina usó para medirlo a mano (`gh api
repos/.../compare/{head_ronda_1}...{head_actual}`, restringido al fichero
citado) es reproducible en vivo, en el momento exacto en que se publica cada
ronda, en vez de aplicarse meses después sobre datos históricos.

## Criterio de parada (escrito ANTES de decidir)

Ver "Nota de arranque" arriba, punto 3. Ninguno se disparó: las cinco
pruebas exigidas pasan por mutación (ver "Comprobación que la sostiene"), no
hubo dos rondas de revisión con la misma familia de defecto, cablear el
guardián a `sirius_apply_verdict.sh` no tocó `.github/**`, y las validaciones
obligatorias están en verde.

## Opciones consideradas

1. **Guardián puro + CLI cargado por ruta de fichero, invocado desde
   `sirius_apply_verdict.sh` con `python3` de sistema** (elegida). Mismo
   patrón que `scripts/automation/sirius_convergence.py` ya usa para
   `round_history.py`: ese script se ejecuta con el `python3` del sistema,
   sin el proyecto instalado (`repair-sirius-work.yml`), así que un `import
   sirius_engine...` normal rompería en producción aunque pasara toda la
   suite bajo `uv run pytest`. Se descarta la alternativa de un import normal
   (como usa `round_family_detector_cli.py`, que hoy no está cableado a
   ningún workflow) precisamente porque este guardián SÍ queda cableado.
2. **Meter la lógica directamente en `sirius_convergence.py`.** Descartada:
   ese script tiene una responsabilidad concreta (política de convergencia,
   `record`/`decide`) y mezclar un guardián informativo sin relación con esa
   decisión habría acoplado dos cosas que cambian por motivos distintos. El
   guardián no participa en absoluto de la decisión CONTINUE/BLOCK.
3. **Reproducir la heurística de "línea hermana del mismo hunk" (`§459`
   rondas 3-4) para eliminar los 2 falsos positivos conocidos.** Descartada
   para esta primera versión: la propia incidencia #496 permite declararla
   como limitación conocida en vez de implementarla, y la nota de arranque
   (punto 2) ya la declara así. Detectar "una línea hermana dentro del mismo
   hunk cambió y por eso esta línea de contexto revela algo nuevo" exige
   juicio sobre el contenido semántico del cambio, no solo su posición en el
   diff -exactamente el tipo de heurística que el criterio de entrada de la
   incidencia #267 pide medir antes de construir, no adivinar-.

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
  guardián nunca razone sobre texto no neutralizado) y antes de construir el
  comentario legible, se invoca el CLI con el head de la ronda 1 -leído del
  mismo historial que ya usa `sirius_next_round_number`- y el head actual. El
  campo `posible_goteo`, si aparece, se añade a la línea legible de cada
  observación. El registro de convergencia (`sirius_convergence.py record`,
  que decide el bloqueo real del ciclo) sigue construyéndose a partir de las
  observaciones SIN anotar: el guardián no puede, ni por accidente de
  serialización, alterar la huella (`fingerprint`) ni la gravedad agregada
  que sostienen la política de convergencia real.

No se cablea nada en `.github/**`: el punto de invocación es
`sirius_apply_verdict.sh`, que ya vive en `scripts/automation/` y que los
workflows existentes ya invocan sin cambios en esta incidencia.

## Comprobación que la sostiene

`uv run pytest tests/engine/test_drip_guard.py
tests/automation/test_sirius_drip_guard_cli.py
tests/automation/test_sirius_apply_verdict.py -q` cubre, cada uno de los
cinco escenarios exigidos visto fallar primero con dos mutaciones
introducidas a propósito sobre la implementación real (prueba por mutación,
disciplina de evidencia §3) y en verde restaurado:

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

`tests/automation/test_sirius_apply_verdict.py` añade el cableado de extremo
a extremo dentro de `sirius_apply_verdict.sh`, con `gh api compare`
simulado: un hallazgo sobre un fichero sin cambios desde la ronda 1 aparece
marcado en el comentario publicado
(`test_drip_guard_marks_a_finding_whose_file_did_not_change_since_round_1`) y
uno sobre una línea añadida no lo está
(`test_drip_guard_does_not_mark_a_finding_on_an_added_line`), sin romper
ninguna de las pruebas ya existentes de ese fichero (39 pruebas, todas en
verde).

Suite completa: `uv run ruff format --check .`, `uv run ruff check .`,
`uv run mypy src tests`, `uv run pytest` (4480 passed, 15 skipped, 2 xfailed)
y `git diff --check`, todas en verde (ver PR).

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
  darle cualquier autoridad (criterio de la incidencia #267).
- Solo actúa sobre hallazgos que citan una línea de un fichero real del
  repositorio. Un hallazgo que cita el cuerpo de una Pull Request, un mensaje
  de commit o prosa sin ruta (el nivel "manual" del informe de la mina, con
  el 80.9% de los hallazgos tardíos de la muestra) queda fuera del alcance de
  este guardián y no recibe ninguna marca, ni positiva ni negativa.
- Depende de que `gh` esté disponible en el runner que ejecuta
  `sirius_apply_verdict.sh` (ya lo está: el resto del script ya depende de
  `gh` para todo lo demás). Si `gh api compare` falla o se agota el tiempo de
  espera, el guardián se calla para esa observación concreta y el resto del
  flujo de publicación de la ronda continúa sin cambios.

## Alternativas descartadas y por qué

Ver "Opciones consideradas" arriba.
