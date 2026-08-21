# Resultados del spike I1 — bordes de STATUS sobre runs de Actions (incidencia #211)

Código y evidencia desechables (ADR-020): esto **no fija** ninguna pieza del
motor, solo mide. Decisión completa, con nota de arranque, criterio de
parada y límites, en
[`docs/decisions/ADR-046-spike-i1-bordes-de-status-sobre-runs-de-actions.md`](../../docs/decisions/ADR-046-spike-i1-bordes-de-status-sobre-runs-de-actions.md).

Todas las mediciones de esta página se ejecutaron de verdad, con `gh api`,
contra el historial real de `canelamoraguezandyjesus-bot/sirius` (repositorio
público, creado 2026-07-12; medido el 2026-08-21), desde este mismo runner de
GitHub Actions — no desde un contenedor de sesión distinto (la confusión que
costó una ronda entera en ADR-042). El repositorio tiene 4413 runs de Actions
en el momento de medir.

## Tabla borde × observación (S3-P1)

Seis filas: las cuatro exigidas (cancelado, no arrancado, `skipped`,
completado con éxito) más dos adicionales que hicieron falta para que la
tabla demuestre la distinción que pide el requisito 3 de la incidencia
("un run que no llegó a arrancar" ≠ "un run que falló ejecutando") y para
mostrar que "no arrancó" tiene dos variantes observables distintas. Cada fila
viene de un run real de este repositorio; el comando y el campo exacto que
sostiene la clasificación están al lado. Reproducidas y comprobadas por
`tests/engine/test_spike_i1_boundary.py` sobre los fixtures congelados de
`fixtures/*.json` (la misma forma que devuelve la API real).

| # | Caso | Run real | Comando | Campos que lo deciden | Clasificación | Latencia de cola | Duración del job | Desvío de cierre | `/logs` |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Cancelado** | [`32216181668`](https://github.com/canelamoraguezandyjesus-bot/sirius/actions/runs/32216181668) (Quality, 2026-08-19) — mismo incidente que documenta ADR-042 (#202) | `gh api repos/…/actions/runs/32216181668/jobs` | `total_jobs=1`, `conclusion=cancelled`, `runner_id=1000001704` | `CANCELADO` | 2 s (04:33:19→04:33:21) | 20 min 16 s (04:33:21→04:53:37) | 1 s (04:53:37→04:53:38) | `200` |
| 2 | **No arrancado (perpetuo)** | [`32217400860`](https://github.com/canelamoraguezandyjesus-bot/sirius/actions/runs/32217400860) (Advance Sirius after Quality) — **sigue en `queued` al medir, >48 h después de crearse** | `gh api repos/…/actions/runs/32217400860` + `.../jobs` + `--silent .../logs` | `status=queued`, `conclusion=null`, `total_jobs=0` | `NO_ARRANCADO` | — (nunca se asignó job) | — | — | **`404`** |
| 3 | **No arrancado (cancelado sin job)** | [`29793001470`](https://github.com/canelamoraguezandyjesus-bot/sirius/actions/runs/29793001470) (Revisar bloque Sirius, 2026-07-21) | igual, run_id `29793001470` | `status=completed`, `conclusion=cancelled`, `total_jobs=0` | `NO_ARRANCADO` | — | — | — | `200` (zip vacío, 22 bytes) |
| 4 | **`skipped`** | [`32439900059`](https://github.com/canelamoraguezandyjesus-bot/sirius/actions/runs/32439900059) (Corregir bloque Sirius, 2026-08-21) — guarda `if:` del job no se cumple | igual, run_id `32439900059` | `conclusion=skipped`, `total_jobs=1`, `runner_id=null`, `steps=[]` | `SKIPPED` | 1 s | 0 s | 10 s | `200` (zip vacío) |
| 5 | **Completado con éxito** | [`32438622606`](https://github.com/canelamoraguezandyjesus-bot/sirius/actions/runs/32438622606) (Quality, 2026-08-21) | igual, run_id `32438622606` | `conclusion=success`, `total_jobs=1`, `runner_id=1000001807` | `COMPLETADO_EXITO` | 3 s (02:05:36→02:05:39) | 5 min 28 s (02:05:39→02:11:07) | 1 s (02:11:07→02:11:08) | `200` |
| 6 | **Completado con fallo** (adicional, no exigido por S3-P1) | [`32434919237`](https://github.com/canelamoraguezandyjesus-bot/sirius/actions/runs/32434919237) (Fusionar bloque Sirius, 2026-08-21) | igual, run_id `32434919237` | `conclusion=failure`, `total_jobs=1`, `runner_id=1000001802` | `COMPLETADO_FALLO` | 5 s | 9 s | 1 s | `200` |

**Comprobación ejecutada** (recortada; comando completo en cada fila de la
tabla):

```
$ gh api repos/canelamoraguezandyjesus-bot/sirius/actions/runs/32217400860 --jq '{status,conclusion,created_at,run_started_at,updated_at}'
{"conclusion":null,"created_at":"2026-08-19T04:53:40Z","run_started_at":"2026-08-19T04:53:40Z","status":"queued","updated_at":"2026-08-19T04:53:40Z"}

$ gh api repos/canelamoraguezandyjesus-bot/sirius/actions/runs/32217400860/jobs
{"total_count":0,"jobs":[]}

$ gh api --silent repos/canelamoraguezandyjesus-bot/sirius/actions/runs/32217400860/logs; echo "rc=$?"
gh: Not Found (HTTP 404)
rc=1
```

```
$ gh api repos/canelamoraguezandyjesus-bot/sirius/actions/runs/32439900059/jobs --jq '.jobs[0] | {status,conclusion,runner_id,runner_name,steps}'
{"status":"completed","conclusion":"skipped","runner_id":null,"runner_name":null,"steps":[]}
```

`tests/engine/test_spike_i1_boundary.py::test_cada_fixture_clasifica_al_borde_que_le_corresponde`
reproduce las seis filas sobre los fixtures y afirma la clasificación de
cada una; comando ejecutado: `uv run pytest tests/engine/test_spike_i1_boundary.py -v`
→ **8 passed**.

## Hallazgos que S3-P1 pedía poder distinguir

1. **"No arrancó" tiene dos variantes observables, y ninguna coincide
   exactamente con lo que describía la incidencia** ("duración ~2 s,
   `runner_id: 0`, `runner_name` vacío y 404 al pedir los registros"). Lo
   medido en este repositorio:
   - **Variante perpetua** (fila 2): un run puede quedarse en `status=queued`
     **indefinidamente** (sigue así más de 48 horas después de crearse, al
     momento de escribir esto). `total_count` de jobs es `0` -nunca se creó
     ni un solo job, así que no hay `runner_id` que leer, ni `0` ni ningún
     otro valor-, y `/logs` responde **404**. Esta es la variante más
     relevante para C1: la cota de `LOST` tiene que contemplar que "sigue en
     cola" pueda significar "para siempre", no solo "un momento antes de
     arrancar".
   - **Variante cancelada sin job** (fila 3): el run llega a
     `status=completed`/`conclusion=cancelled` en ~1 s, también con
     `total_count=0`, pero `/logs` responde **200** con un zip vacío
     (22 bytes) en vez de 404. El código HTTP de `/logs` por sí solo **no**
     basta como señal de "no arrancó": dos runs con la misma ausencia
     estructural de job (`total_jobs=0`) dan códigos distintos según si el
     run llegó a cerrarse o se quedó abierto. La señal fiable es
     `total_jobs==0`, no el código de `/logs`.
   - Ninguna de las dos trae un job con `runner_id: 0` literal: cuando
     GitHub nunca llega a crear el job, no hay objeto de job del que leer
     ningún campo -ni `0` ni vacío-, `total_count` es directamente `0`. La
     sonda (`boundary.clasificar`) usa por eso `total_jobs==0`, no
     `runner_id==0`, como señal estructural (documentado en el propio código
     y en la nota de arranque del ADR-046).
2. **Un job `skipped` SÍ se crea, con `runner_id`/`runner_name` en `null`
   (no `0`) y `steps=[]`** (fila 4) -distinto de "no arrancó", que no crea
   job en absoluto. Esta es la distinción más fina que exigió el
   requisito 3: dos casos con "ningún runner real asignado" (`skipped` y
   `no_arrancado`) se separan por si existe o no un registro de job, no por
   los campos del runner.
3. **Un run que falló ejecutando (fila 6) siempre tiene un job con
   `runner_id` numérico real y una duración > 0.** Es la contraparte que
   demuestra que "no arrancó" y "falló" son estructuralmente distinguibles,
   no solo por vocabulario: `test_no_arrancado_nunca_se_confunde_con_completado_fallo`
   lo afirma expresamently.
4. **El run-level `updated_at` va detrás del job-level `completed_at` por 1
   segundo** en las tres filas completadas con éxito/fallo/cancelación
   (filas 1, 5, 6): la API tarda un instante en propagar "el job terminó" a
   "el run terminó". Cadencia de sondeo más fina que ese margen no gana
   nada.
5. **Latencia cola→runner observada: 2-5 s** en los tres casos que sí
   llegaron a tener un job (filas 1, 5, 6). Nunca 0.

## Retención / runs expirados — **NO CONCLUYENTE**

El run más antiguo accesible por la API
(`gh api "repos/…/actions/runs?per_page=100&page=45" --jq '[.workflow_runs[]|.created_at]|min'`)
es del `2026-07-12T23:27:55Z`, el mismo día de creación del repositorio
(`created_at` del repositorio: `2026-07-12T01:06:52Z`). Los 4413 runs
existentes son enumerables sin ningún hueco visible. **No hay, en este
repositorio, ningún run con más de 40 días de antigüedad al medir**, así que
no se puede observar el borde de retención agotada sin fabricarlo -y
fabricarlo (dejar pasar meses, o cambiar la retención configurada del
repositorio) no es una medición de solo lectura sobre el historial ya
existente que la incidencia permite. **Declarado NO CONCLUYENTE**, tal y como
anticipó la nota de arranque del ADR-046: haría falta un repositorio con más
de 90 días de historial (la retención por defecto de GitHub Actions) para
responder esto con una medición real en vez de con la documentación de
GitHub, que ADR-036 prohíbe sustituir por la comprobación.

## Rate limits (requisito 3 de la incidencia)

**Coste por endpoint, medido con `gh api rate_limit` antes/después de cada
llamada:**

```
$ gh api rate_limit --jq '.resources.core'
{"limit":5000,"remaining":4987,"reset":1787280287,"resource":"core","used":13}
# ... llamada a gh api repos/…/actions/runs/32216181668 ...
$ gh api rate_limit --jq '.resources.core.remaining'
4986
```

- `GET rate_limit` **no consume cuota** (comprobado: tres llamadas
  consecutivas devolvieron el mismo `remaining`).
- `GET .../actions/runs/{id}`, `.../jobs`, `.../logs` y el listado paginado
  cuestan **1 punto cada uno**, confirmado con antes/después separados por
  varios segundos.
- **Hallazgo no anticipado en la nota de arranque**: medir el coste con un
  antes/después *inmediato* (sin ninguna pausa entre la llamada real y la
  siguiente lectura de `rate_limit`) dio, en dos ocasiones, una diferencia de
  **0** donde debía haber 1 -el contador de GitHub es
  distribuido/eventualmente consistente y puede no reflejar todavía la
  llamada que se acaba de hacer. Repetido con más margen entre llamadas, el
  coste de 1 punto por lectura fue consistente. **Implicación para C1**: no
  tratar `X-Ratelimit-Remaining` leído justo después de una llamada como una
  cota exacta e inmediata del presupuesto restante; dejar margen.
- **La respuesta exacta al agotar el límite real (403, cuerpo, cabeceras) se
  declara NO CONCLUYENTE.** El token de `gh` de este runner es compartido con
  cualquier otra automatización concurrente de este mismo repositorio (los
  workflows de Sirius corren constantemente, según el propio historial de
  runs medido arriba); vaciar la cuota real (4987 peticiones en el momento de
  medir) la dejaría sin cupo hasta el reinicio de la ventana, exactamente el
  riesgo que la nota de arranque del ADR-046 declaró antes de medir. Haría
  falta un token dedicado, sin automatización concurrente compartiéndolo,
  para responder esto con una medición real.

## Cotas propuestas para C1 (S3-P2)

Cada cota está justificada por una fila concreta de la tabla de arriba; C1
decide si las adopta, esto no lo fija.

| Cota propuesta | Valor | Fila que la sostiene |
|---|---|---|
| Cadencia mínima de sondeo | **≥ 5 s** entre lecturas del mismo run | Fila 1/5/6: el desvío de cierre run↔job es de 1 s; sondear más rápido que esto no añade información nueva, solo gasta cuota. |
| Umbral de "puede seguir vivo" para un run en `queued` sin job | **Ninguno por duración**: un run en `queued` con `total_jobs==0` puede seguir así indefinidamente (fila 2, >48 h y contando) | El propio caso 2: cualquier umbral de minutos/horas fabricado sin esta medición se habría equivocado. |
| Señal de "no arrancó" (para el bound `LOST`) | `total_jobs == 0` (no un umbral de duración, no el código de `/logs`) | Filas 2 y 3: mismo `total_jobs==0`, duraciones y códigos de `/logs` distintos (perpetuo vs. cancelado en ~1 s). |
| Señal de "`skipped`" | `conclusion == "skipped"` (a nivel run) o `job.conclusion == "skipped"` | Fila 4: coincide en ambos niveles en el único caso medido. |
| Señal de "cancelado con trabajo real perdido" | `total_jobs > 0` y `conclusion == "cancelled"` | Fila 1: distingue de la fila 3, que también es `cancelled` pero con `total_jobs==0`. |
| Coste de presupuesto por ciclo de sondeo de un run | 1 punto de `rate_limit` por endpoint leído (`run`, `jobs`, `logs` si hace falta) | Medición de "Rate limits" arriba. |
| Margen sobre `X-Ratelimit-Remaining` leído en caliente | No confiar en el valor si se leyó a menos de varios segundos de la llamada que se está contabilizando | Hallazgo de eventual consistencia, arriba. |

## Prueba por mutación (ADR-001 §3, requisito 4 de la incidencia)

Tres mutaciones sembradas, cada una vista fallar y revertida (comandos
ejecutados de verdad, no razonados):

1. **Tratar "no arrancado" como "fallido"** — en
   `experiments/work_engine_spike_i1/boundary.py::clasificar`, la rama
   `if obs.total_jobs == 0: return EstadoBorde.NO_ARRANCADO` se cambió a
   `return EstadoBorde.COMPLETADO_FALLO`. Comando:
   `uv run pytest tests/engine/test_spike_i1_boundary.py -v` →
   **4 failed, 4 passed** (`test_cada_fixture_clasifica_al_borde_que_le_corresponde`,
   `test_no_arrancado_nunca_se_confunde_con_completado_fallo`,
   `test_tabla_incluye_una_fila_por_borde_exigido`,
   `test_logs_404_del_caso_no_arrancado_perpetuo_se_conserva_como_dato`).
   Revertido; vuelve a **8 passed**.
2. **Introducir una escritura en la sonda** — en `probe.py`, el
   `__post_init__` de `GitHubActionsProbe` dejó de envolver `ejecutar` con
   `SoloLecturaEjecutor` (`pass` en vez de la línea real). Comando:
   `uv run pytest tests/engine/test_spike_i1_probe.py -v` → **1 failed, 23
   passed** (`test_probe_envuelve_el_ejecutor_inyectado_con_el_guarda`:
   *"DID NOT RAISE EscrituraProhibida"*). Revertido; vuelve a **24 passed**.
3. **Meter un reloj real en el camino de la medición** — en `boundary.py`,
   `_segundos_entre` ganó una línea `datetime.now()` al principio. Comando:
   `uv run pytest tests/engine/test_spike_i1_boundary.py -v` → **1 failed, 7
   passed** (`test_boundary_py_no_contiene_ninguna_llamada_a_reloj_real`:
   *`datetime.now() en línea 102`*). Revertido; vuelve a **8 passed**.

Las tres cayeron exactamente en la prueba que se esperaba, y ninguna otra:
no hubo que ampliar ni corregir ninguna prueba para que la mutación se
notara (a diferencia de S1/S3-spike-i3, donde una mutación sin prueba
dedicada habría pasado desapercibida). Suite completa del spike tras
revertir las tres: `uv run pytest tests/engine/test_spike_i1_probe.py
tests/engine/test_spike_i1_boundary.py tests/engine/test_boundary.py` →
**34 passed**.

## Solo lectura, demostrado (S3-P3)

`SoloLecturaEjecutor` (`probe.py`) rechaza, ANTES de invocar el ejecutor
real o de pruebas: cualquier argv que no empiece por `api`, cualquier
bandera de escritura o de cuerpo (`--method`, `-X`, `-f`, `-F`, `--input`), y
cualquier endpoint que contenga un sufijo mutante conocido (`/cancel`,
`/rerun`, `/approve`, `/dispatches`, `/labels`, `/comments`, `/merge`,
`/reviews`, `/force-cancel`). `GitHubActionsProbe` envuelve `ejecutar` con
este guarda en su propio `__post_init__`, así que la propiedad vale para
CUALQUIER ejecutor que se le inyecte, real o de pruebas -no es una
comprobación que dependa de que el código de producción "se acuerde" de
llamar al guarda en cada método nuevo.
`tests/engine/test_spike_i1_probe.py::test_solo_lectura_ejecutor_rechaza_toda_forma_de_escritura`
prueba nueve formas distintas de intentar escribir, todas rechazadas antes
de tocar el ejecutor interno (afirmado con un contador de llamadas, no solo
con la excepción). Comando: `uv run pytest tests/engine/test_spike_i1_probe.py -v`
→ **24 passed**.

## Determinismo (S3-P4)

`construir_tabla` y `clasificar` son funciones puras sobre
`ObservacionRun` -sin `gh`, sin red, sin reloj real. Comprobado en dos
capas:

1. **Dinámica**: `test_construir_tabla_es_determinista_sobre_los_mismos_fixtures`
   construye la tabla dos veces sobre los mismos fixtures y afirma
   igualdad estructural completa (`tabla_1 == tabla_2`).
2. **Estática**: `_sin_llamadas_a_reloj_real` recorre el AST de `boundary.py`
   y `probe.py` (mismo método que `tests/engine/test_boundary.py` usa para
   la frontera `sirius`/`sirius_engine`) y afirma que ninguna llamada a
   `datetime.now`, `time.time`, `time.monotonic` ni `time.perf_counter`
   aparece en ninguno de los dos módulos -hace la ausencia de reloj real
   comprobable por inspección del árbol sintáctico, no solo por convención
   o por una prueba dinámica que podría no ejercitar la línea exacta que lo
   introduce.

## Comparativa de lo considerado

| Enfoque | ¿Se implementó y probó? | Decisión |
|---|---|---|
| **Campos estructurales de la API (`total_jobs`, `runner_id`, `conclusion`) como señal de clasificación** | Sí — `boundary.clasificar`, seis fixtures reales, mutación 1 vista fallar | **Adoptado**: es lo único que sobrevive a la mutación "no arrancado = fallido" sin inventar un umbral de duración. |
| Umbral de duración (p. ej. "menos de N segundos = no arrancó") | No implementado | **Descartado sin probar**: la fila 2 (no arrancado, perpetuo, >48 h) lo habría clasificado como "arrancó y sigue corriendo" -exactamente el riesgo que la incidencia declaró como principal ("medir solo el camino feliz"). |
| Código HTTP de `/logs` como señal única de "no arrancó" | Medido, no adoptado como señal única | Las filas 2 y 3 comparten `total_jobs==0` pero dan códigos distintos (`404` vs. `200` vacío): por sí solo, `/logs` sub-clasificaría un mismo borde en dos. Se conserva como columna informativa, no como criterio de clasificación. |
| Guarda de solo lectura por inspección de código (revisión manual) | No | **Descartado**: no es verificable en cada ejecución ni cae con una mutación real; `SoloLecturaEjecutor` sustituye la promesa por un guarda que corre en cada llamada (S3-P3). |
| Exhaustar el rate limit real para ver el 403 exacto | No, deliberadamente (nota de arranque) | **Descartado**: el token es compartido con automatización concurrente de este mismo repositorio; vaciarlo la dejaría sin cuota hasta el reinicio de la ventana. Declarado NO CONCLUYENTE con lo que haría falta para responderlo. |

## Límites conocidos (escritos antes de declarar terminado)

1. **Seis runs, no una muestra estadística.** La tabla cubre los bordes a
   propósito (requisito 2), no una distribución representativa de latencias.
   Los números de latencia de cola (2-5 s) y desvío de cierre (1 s) son
   anecdóticos de estos seis runs concretos, útiles como cota de orden de
   magnitud, no como percentil.
2. **No mide bajo sondeo concurrente.** Todo lo anterior es un proceso
   secuencial midiendo un run a la vez; C1 en producción podría sondear
   varios runs a la vez, con un patrón de coste distinto.
3. **La respuesta exacta al agotar el rate limit real queda sin medir**, por
   la razón de riesgo compartido explicada arriba -no por falta de tiempo.
4. **El borde de retención agotada queda NO CONCLUYENTE**: este repositorio
   es demasiado joven (40 días) para haberlo alcanzado.
5. **La sonda no se probó contra `gh` real dentro de la suite de pytest**
   (a propósito: ninguna prueba de este repositorio accede a la red,
   requisito 7). Los seis fixtures son la captura congelada de las
   llamadas reales documentadas arriba, no una simulación inventada.
6. **La clasificación de "no arrancó" asume que `total_jobs==0` implica
   "nunca se asignó un runner".** Es cierto en los dos casos medidos de
   este repositorio (uno perpetuo, uno cancelado en ~1 s); no se probó
   sobre un run con reintentos (`run_attempt > 1`) o con una matriz de
   jobs paralelos donde solo algunos lleguen a crearse -escenario que no
   apareció en el historial disponible al medir.

## Qué demuestra esto para C1 (sin decidirlo)

Si C1 reutiliza esta sonda, hereda gratis: el guarda de solo lectura
(`SoloLecturaEjecutor`), la distinción estructural "no arrancó" vs.
"`skipped`" vs. "falló" vs. "cancelado" por campos de la API en vez de
umbrales de duración, y la cadencia mínima razonada (≥5 s). Lo que C1 tiene
que resolver que este spike deja fuera a propósito: sondeo concurrente de
múltiples runs, una política de reintento/backoff ante `NO_DISPONIBLE`
real (esta sonda solo reporta el estado, no reintenta -mismo principio que
A3 en `github_cli_mirror.py`), y la acción a tomar cuando un run cruza la
cota de `LOST` (este spike no implementa C1, solo mide para que C1 pueda
escribirse con cotas reales en vez de inventadas).
