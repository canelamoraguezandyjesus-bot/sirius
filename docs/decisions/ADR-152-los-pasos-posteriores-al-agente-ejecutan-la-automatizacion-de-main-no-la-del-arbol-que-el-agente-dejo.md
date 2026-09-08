# ADR-152 — Los pasos posteriores al agente ejecutan la automatización de `main`, no la del árbol que el agente dejó

- Estado: PROPUESTO
- Fecha: 2026-09-06
- Aprobación: la fusión de esta PR por el propietario (toca `.github/**`;
  ficha del operador).

Esta es también la nota de arranque de la rama
`claude/adr-152-automatizacion-de-main`, publicada antes del primer cambio,
con las cuatro preguntas de la disciplina de evidencia (ADR-001).

## Contexto y problema

Los cuatro workflows de rol (`implement-sirius-work.yml`,
`review-sirius-work.yml`, `repair-sirius-work.yml`, `investigar-orden.yml`)
hacen checkout de `main`, ejecutan un agente, y después aplican su veredicto
con `bash scripts/automation/sirius_apply_verdict.sh` (la revisión, además,
recoge y agrega con `python3 scripts/automation/sirius_codex_review.py` y
`sirius_aggregate_reviews.py`). Esas rutas son **relativas al árbol de
trabajo**, y el árbol de trabajo, cuando llega ese paso, es **el que el agente
dejó**: el corrector hace checkout de la rama de la PR para corregirla; el
implementador crea una rama y trabaja en ella; el revisor puede traerse el head
de la PR para ejecutar pruebas.

El dato: en la incidencia #545, el corrector de la ronda 2 (run 34007489545,
06-09-2026) empujó `3380f09` a las 03:14:02; Quality cerró en rojo a las
03:14:31; el paso «Aplicar el veredicto» corrió de 03:15:25 a 03:15:31 con el
entorno nuevo de ADR-149 (`SIRIUS_READ_TOKEN` a la vista en el log) y **no
ejecutó ni una línea de `relanzar_quality_si_ya_termino`**: entre la
publicación del comentario (03:15:31.126) y el «Veredicto FIXED aplicado»
(03:15:31.129) pasan tres milisegundos, sin ninguna consulta. `main` tenía la
función desde `6ba5901` (02:31), pero la rama de la PR
(`feature/reflejo-salida-de-parada-con-permiso-escrito`, creada desde
`a07c5d5`) tiene un `sirius_apply_verdict.sh` con **cero** apariciones de
ella, y ese fue el guion que se ejecutó. El rojo se perdió y hubo que
corregirlo a mano.

El defecto tiene dos caras, y la segunda pesa más que la primera:

1. **Corrección:** cualquier arreglo de la automatización solo actúa en las
   ramas que ya lo contienen. ADR-149 (y todo lo que venga) no rige para las
   PR abiertas antes de él.
2. **Integridad:** los pasos posteriores al agente corren con el PAT
   (`SIRIUS_BOT_TOKEN`), que mueve etiquetas, publica comentarios y relanza
   runs. Ejecutar ahí el guion del árbol que el agente dejó significa que el
   agente —o cualquier cosa que el agente lea y obedezca— puede elegir qué
   automatización aplica su propio veredicto. El diseño del ciclo dice lo
   contrario: «Claude NUNCA muta etiquetas ni cierra la incidencia por su
   cuenta … `sirius_apply_verdict.sh` es quien aplica esa decisión,
   reverificando todo por su cuenta» (cabecera de `implement-sirius-work.yml`).
   Esa reverificación solo vale si el guion es el de `main`.

## Nota de arranque (cuatro preguntas, ADR-001)

1. **¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo
   observar el fallo?** Vive en los workflows, en la ruta con la que invocan
   la automatización después del agente. El arreglo va ahí: una copia de
   `scripts/automation` tomada de `main` nada más hacer checkout, antes de
   que el agente toque nada, y los pasos posteriores la ejecutan por ruta
   absoluta. Se observa en el log del run: el paso de congelación imprime el
   commit del que copió, y los guardianes leen el YAML.
2. **¿Qué NO garantiza esto?** No cambia qué hace la automatización, solo de
   dónde se ejecuta. No protege los pasos ANTERIORES al agente (puerta,
   consumo del evento, prompt), que ya corren sobre `main` limpio. No impide
   que un agente modifique `scripts/automation` en su rama: impide que esa
   modificación se ejecute con el PAT en el mismo run. No cubre a `quality.yml`
   ni al resto de workflows sin agente.
3. **Criterio de parada (decidido antes de ver ningún resultado).** Los
   guardianes nuevos ven FALLAR el YAML actual (invocaciones por ruta
   relativa después del agente; ningún paso de congelación) y pasan con el
   cambio; los guardianes existentes que fijan pasos y líneas del veredicto se
   actualizan a propósito y con motivo, nunca se debilitan; la aritmética de
   presupuesto del corrector se mantiene bajo su techo (85, ADR-150); la
   cadena completa termina en 0. En vivo: la siguiente ronda de un rol sobre
   una rama anterior a ADR-149 debe mostrar en su log el paso de congelación
   y, si Quality cerró antes de la transición, un `QUALITY_RELANZADO`.
4. **¿Qué hace esto imposible, en vez de improbable?** Que el guion aplicado
   dependa del árbol del agente: la copia se toma antes de arrancarlo y los
   pasos posteriores no vuelven a mirar `scripts/automation` del árbol. Lo
   garantiza un guardián que, por cada workflow con agente, exige el paso de
   congelación antes del agente y prohíbe cualquier referencia a
   `scripts/automation/` en los pasos posteriores.

## Criterio de parada (escrito ANTES de decidir)

Ver punto 3 de la nota de arranque.

## Opciones consideradas

1. **Copiar `scripts/automation` a `${RUNNER_TEMP}/automation-de-main` nada
   más hacer checkout y ejecutar los pasos posteriores desde ahí** (elegida).
   Autocontenida: `sirius_apply_verdict.sh` carga `sirius_issue.sh` y sus
   ayudantes Python desde su propio directorio (`SIRIUS_VERDICT_DIR`), y
   `sirius_convergence.py`/`sirius_drip_guard_cli.py` cargan sus hermanos por
   ruta propia con `importlib`; `sirius_codex_review.py` y
   `sirius_aggregate_reviews.py` son solo biblioteca estándar. No depende del
   estado de `git` después del agente.
2. **Restaurar `scripts/automation` desde `origin/main` al empezar el paso del
   veredicto** (`git checkout origin/main -- scripts/automation`). Descartada:
   depende de que el árbol y el repositorio sigan sanos después del agente, y
   de que `origin/main` siga siendo `main` al cabo de una hora (una fusión
   entre medias haría que el veredicto lo aplicara una automatización distinta
   de la que arrancó el run).
3. **Prohibir al agente cambiar de rama.** Descartada: el corrector TIENE que
   trabajar en la rama de la PR; es su función.
4. **Dejarlo así y documentarlo.** Descartada por la cara de integridad.

## Decisión

- En los cuatro workflows con agente, un paso «Congelar la automatización de
  main» inmediatamente después de `Checkout`: `cp -R scripts/automation
  "${RUNNER_TEMP}/automation-de-main"`, con el commit de origen en el log.
- Los pasos posteriores al agente invocan la copia: `bash
  "${RUNNER_TEMP}/automation-de-main/sirius_apply_verdict.sh"` (los cuatro),
  y en la revisión `python3 "${RUNNER_TEMP}/automation-de-main/
  sirius_codex_review.py" collect …` y `python3 "${RUNNER_TEMP}/
  automation-de-main/sirius_aggregate_reviews.py" …`. El disparo de Codex,
  anterior al agente, no cambia.
- Presupuesto del corrector (ADR-150): el paso nuevo declara
  `timeout-minutes: 1` y «Install uv» baja de 3 a 2 para que la suma siga en
  80 bajo los 85 del job (`uv` se instala en segundos, con caché).
- Guardián nuevo, `tests/automation/test_automatizacion_congelada_de_main.py`:
  por cada workflow con agente, el paso de congelación existe y precede al
  agente; todo paso posterior que invoque `sirius_apply_verdict.sh`,
  `sirius_codex_review.py` o `sirius_aggregate_reviews.py` lo hace desde la
  copia; ningún paso posterior nombra `scripts/automation/`.

## Comprobación que la sostiene

- El dato: run 34007489545, job 101417273387, paso «Aplicar el veredicto»
  (03:15:25 → 03:15:31), con `SIRIUS_READ_TOKEN` en su entorno y sin ninguna
  línea de `relanzar_quality_si_ya_termino`; `git show
  origin/feature/reflejo-salida-de-parada-con-permiso-escrito:scripts/automation/sirius_apply_verdict.sh
  | grep -c relanzar_quality_si_ya_termino` → `0`; en `origin/main` la
  función está en la línea 310 y su llamada en la 424.
- Guardianes vistos fallar y pasar, guardianes existentes actualizados con
  motivo, y cadena completa como una sola invocación: transcritos en el cuerpo
  de la PR sobre su head definitivo.
- Lo que NO se ha medido: el caso en vivo (criterio 3).

## Corrección (06-09-2026, 04:31 UTC): la copia reproduce el trazado del árbol

La opción 1 afirmaba que la copia era «autocontenida», y no lo era del todo:
`sirius_apply_verdict.sh` sí carga sus ayudantes desde su propio directorio,
pero dos de esos ayudantes —`sirius_convergence.py` y
`sirius_drip_guard_cli.py`— alcanzan `src/sirius_engine/round_history.py` (y
`round_family_detector.py`, `drip_guard.py`) por **`parents[2]` de su propia
ruta**, es decir, dan por hecho que viven en `<raíz>/scripts/automation/`.
Con la copia plana en `${RUNNER_TEMP}/automation-de-main/`, `parents[2]` es
`/home/runner/work` y el módulo compartido no existe.

El dato: primer run con la copia, la revisión de #550 sobre `098bdfe` (run
34011306916, 04:21 → 04:31). La congelación, la recogida de Codex y la
agregación funcionaron; el veredicto (`CHANGES_REQUESTED`) cayó al registrar
la ronda con `FileNotFoundError:
/home/runner/work/src/sirius_engine/round_history.py` en los dos ayudantes, y
la incidencia paró en `failed-safely` con `registro-de-ronda-fallido`. Nada
se perdió salvo la ronda: la parada segura hizo su trabajo.

Corrección, misma decisión: la copia reproduce el **trazado** del árbol —
`${RUNNER_TEMP}/automation-de-main/scripts/automation/` y
`${RUNNER_TEMP}/automation-de-main/src/sirius_engine/`— y los pasos
posteriores invocan `…/automation-de-main/scripts/automation/<guion>`. Así
`parents[2]` de cualquier guion copiado es la raíz de la copia, que contiene
`src/sirius_engine`. Ningún guion cambia. El guardián gana un caso que ata las
dos cosas: para cada ayudante de `scripts/automation` que alcance
`src/sirius_engine` por `parents[2]`, la congelación copia `src/sirius_engine`
bajo el mismo trazado y las invocaciones apuntan a `scripts/automation` dentro
de la copia.

Lo que enseña: «autocontenido» se comprueba ejecutando, no leyendo. El
guardián de la forma no podía ver esto; lo vio el primer run real. Queda
como criterio: la próxima vez que un paso cambie de dónde se ejecuta un guion,
listar todo lo que ese guion resuelve por `__file__` antes de dar por hecho
que la copia basta.

## Consecuencias

- Toda mejora de la automatización actúa desde el primer run posterior a su
  fusión, sea cual sea la rama de la PR. ADR-149 pasa a regir de verdad para
  las PR abiertas antes de él (#546 incluida).
- Un agente no puede elegir la automatización que aplica su veredicto.
- Cada run copia un directorio pequeño una vez: coste despreciable.
- Deuda declarada: los pasos anteriores al agente siguen invocando por ruta
  relativa; es correcto hoy (árbol de `main` limpio) y queda dicho para que
  nadie mueva un paso detrás del agente sin cambiar su ruta.

## Alternativas descartadas y por qué

Ver «Opciones consideradas».
