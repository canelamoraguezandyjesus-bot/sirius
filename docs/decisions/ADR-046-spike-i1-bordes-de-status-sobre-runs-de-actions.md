# ADR-046 — Spike I1: bordes de STATUS sobre runs de Actions

- Estado: PROPUESTO
- Fecha: 2026-08-21
- Aprobación: la fusión de la PR que cierra la incidencia #211, por el propietario.
- Contexto: incidencia #211 (S3, spike I1 del plan de implementación del Work Engine)

## Nota de arranque (ADR-001, publicada antes del primer commit de código)

Este ADR se abre en el primer commit de la rama, con esta sección ya escrita
y sin ninguna otra. El resto del documento (Decisión, Comprobación,
Consecuencias) se completa al terminar el spike, con los resultados reales.

**Por qué esta nota vive aquí y no como comentario en la incidencia #211,
pese a que la incidencia pide "publicado como comentario en esta
incidencia"**: mismo conflicto que resolvió ya
[ADR-026](ADR-026-spike-i3-diario-append-only-con-checksum-e-idempotencia.md)
para S1, y con la misma resolución. El contrato operativo de este rol («Rol:
implementador genérico de Sirius», sección «Contrato que debes respetar»)
dice explícitamente: «Ese comentario [`PR abierta: <URL>`] es lo único que
puedes escribir en la incidencia». Ante el conflicto, gana el contrato
operativo explícito de esta ejecución: es más específico, más reciente, y ya
fijó este mismo precedente sin objeción del propietario en S1. La tabla
borde×observación, las cotas propuestas y la comprobación de solo-lectura
—que la incidencia #211 pide "publicadas en esta incidencia"— se satisfacen
en su lugar en la descripción de la PR (que el comentario `PR abierta: <URL>`
enlaza) y en `experiments/work_engine_spike_i1/RESULTADOS.md`, dentro del
propio diff.

### 1. ¿Dónde vive el fallo y dónde va el arreglo?

No es una corrección de un defecto: es una medición (spike, sin decisión de
arquitectura). La pregunta equivalente es: **¿puede el sitio de la medición
OBSERVAR lo que afirma?** Sí, por construcción: la sonda lee directamente del
mismo endpoint (`gh api repos/{repo}/actions/runs/...` y
`.../jobs`) que consumirá C1 en producción — no un caché derivado, ni una
proyección de terceros, sino la fuente de verdad de GitHub para el estado de
un run. El repositorio en el que corre esta sesión (`canelamoraguezandyjesus-bot/sirius`)
es un runner real de GitHub Actions con historial real de runs (incluidos los
bordes citados por la incidencia: #202 y #206, cancelados por el paso de Qt
colgado 20 min — ver ADR-042), así que medir aquí mide el mismo sistema que
usará C1, no una extrapolación desde un contenedor de sesión distinto (la
lección explícita de ADR-042, citada en las salvaguardas de la incidencia).

### 2. Qué NO va a garantizar esto (escrito antes de medir)

- **No exhaustará el límite real de peticiones (5000/hora) para observar el
  403 exacto de agotamiento.** El token de `gh` en este runner es compartido
  con cualquier otra automatización concurrente de este mismo repositorio;
  vaciarlo a propósito la dejaría sin cuota hasta el reset. Se mide el coste
  por endpoint (cuánto decrementa `X-RateLimit-Remaining` cada llamada) y se
  documentan los encabezados reales devueltos en cada respuesta; la
  respuesta exacta al agotar se declara **NO CONCLUYENTE**, con lo que haría
  falta para responderla (un token dedicado, sin automatización concurrente
  compartiéndolo).
- **No mide bajo sondeo concurrente** (varias sondas a la vez contra el mismo
  repositorio): un solo proceso secuencial, como haría un supervisor.
- **No fija la cadencia definitiva de C1.** Propone cotas justificadas por
  fila de tabla; la decisión de adoptarlas es de C1, no de este spike.
- **No provoca bordes nuevos.** Alcance de solo lectura: si un borde (p. ej.
  un run expirado por retención) no existe ya en el historial accesible por
  la API, se declara NO CONCLUYENTE en vez de lanzar o cancelar un run para
  fabricarlo — eso violaría el alcance de solo lectura de la propia
  incidencia.
- No mide latencia de estados en repositorios ajenos a este, ni en otra
  cuenta o plan de GitHub: los límites y la latencia observada valen para
  este repositorio, no como propiedad universal de la API.

### 3. Criterio de parada (decidido ahora, antes de ver ningún resultado)

**Se declara terminado (`READY_FOR_REVIEW`)** cuando, y solo cuando, todo lo
siguiente es cierto a la vez:

1. La tabla borde×observación cubre, con comando y salida real recortada al
   lado, como mínimo los cuatro bordes exigidos por S3-P1: cancelado, no
   arrancado, `skipped`, completado con éxito — cada fila con una llamada de
   API ejecutada de verdad contra el historial de este repositorio, nunca
   una cota razonada sin medición.
2. Un run "no arrancado" queda distinguido estructuralmente (campos de la
   API: `runner_id == 0`, `runner_name` vacío, 404 al pedir registros) de un
   run que falló ejecutando — nunca por un umbral de duración adivinado.
3. Cotas de cadencia y por etiqueta de estado propuestas para C1, cada una
   con la fila de tabla que la sostiene (S3-P2).
4. Una prueba falla si la sonda intenta cualquier verbo de escritura
   (S3-P3), verificando cada llamada real hecha durante las pruebas, no solo
   leyendo el código en busca de verbos prohibidos.
5. La sonda, sobre los mismos datos guardados (fixtures JSON de la medición
   real), produce el mismo resultado en cada ejecución — ningún reloj real
   ni llamada de red en el camino de prueba (S3-P4).
6. Al menos tres mutaciones sembradas (clasificar "no arrancado" como
   "fallido"; introducir una escritura; meter un reloj real) vistas fallar
   cada una en la prueba que le corresponde, y revertidas.
7. Las cuatro validaciones obligatorias + `git diff --check` +
   `tests/engine/test_boundary.py` sin modificar, todas en verde.

**Se detiene con `BLOCKED_BY_DECISION`** si, en cualquier momento, medir un
borde exige tocar `.github/**` o `scripts/automation/**`, o decidir algo de
producto/arquitectura no cubierto por la incidencia.

**Se detiene con `FAILED_SAFELY`** si `gh api` no responde desde este runner
(sin red, sin token) — comprobado ya en el arranque: `gh api rate_limit`
respondió con datos reales, así que esta salida no aplica salvo que la red
se degrade a mitad de la medición.

**Un borde individual (no el spike entero) se declara NO CONCLUYENTE** si no
existe ya en el historial accesible por la API (retención agotada, permisos)
o si medirlo exigiera provocarlo o exhaustar el límite real de peticiones —
nunca se sustituye por lo que diga la documentación de GitHub sin haberlo
comprobado aquí (ADR-036).

**Regla de las dos rondas** (disciplina-evidencia §2): si dos rondas de
revisión seguidas encuentran defectos de la misma familia (por ejemplo, dos
bordes distintos mal clasificados por el mismo motivo), se para de parchear
caso a caso y se revisa el diseño del clasificador entero.

### 4. ¿Qué haría el fallo imposible en vez de improbable?

- El clasificador de bordes (`boundary_classifier.py`) es una función PURA
  sobre los campos que la API ya devuelve (`status`, `conclusion`,
  `jobs[].runner_id`, `jobs[].runner_name`, `jobs[].started_at`, código de
  estado HTTP del endpoint de registros) — nunca una heurística de duración.
  Dos runs con la misma duración pero campos distintos (uno con
  `runner_id == 0`, otro con un `runner_id` real y `conclusion == "failure"`)
  clasifican distinto por construcción, no por ajuste de umbral.
- S3-P3 hace la propiedad "nunca escribe" verificable por inspección de cada
  llamada real capturada durante la prueba (un doble que registra el `argv`
  completo de cada invocación y falla si contiene `--method` con un verbo
  distinto de `GET`, o cualquier endpoint mutante como `/cancel`/`/rerun`),
  en vez de una promesa leída en el código de producción.
- S3-P4 hace la sonda determinista por construcción: el generador de tabla
  recibe las respuestas de la API ya capturadas (fixtures), nunca invoca
  `gh` ni `datetime.now()` en su camino de prueba — misma entrada, misma
  tabla, siempre.

---

## Contexto y problema

## Opciones consideradas

La incidencia #211 (S3, spike I1 del plan de implementación del Work Engine)
pide medir, sobre runs reales de Actions de este repositorio, lo que decide
las cotas de `LOST` que C1 necesitará: latencia real de transiciones de
estado, comportamiento de los bordes (no solo el camino feliz), límites de
peticiones, y con eso una cadencia de sondeo y cotas por etiqueta de estado
propuestas. Depende de A3 (ya fusionado); es independiente de E1b y de la
Fase B.

## Opciones consideradas

Ver la tabla completa, con motivo de adopción o descarte de cada una, en
[`experiments/work_engine_spike_i1/RESULTADOS.md`](../../experiments/work_engine_spike_i1/RESULTADOS.md#comparativa-de-lo-considerado).
Resumen: clasificar por campos estructurales de la API (`total_jobs`,
`runner_id`, `conclusion`) en vez de por un umbral de duración adivinado
(adoptado), un código HTTP de `/logs` como señal única de "no arrancó"
(medido, no adoptado -dos runs con el mismo borde dieron códigos distintos),
una guarda de solo lectura por revisión manual del código en vez de un
guarda ejecutable (descartada, no sobrevive a una mutación real), y
exhaustar el rate limit real para observar el 403 exacto (descartado
deliberadamente, declarado NO CONCLUYENTE: el token es compartido con
automatización concurrente de este mismo repositorio).

## Decisión

Implementar la sonda en `experiments/work_engine_spike_i1/` (desechable):
`probe.py` (`GitHubActionsProbe` sobre `gh api`, con `SoloLecturaEjecutor`
como guarda ejecutable de solo lectura -no una promesa leída en el código-,
mismo patrón de `ejecutar` inyectable que `sirius_engine.adapters.github_cli_mirror`
de A3) y `boundary.py` (clasificador puro `clasificar()` + `construir_tabla()`,
sin `gh`, sin red, sin reloj real). Seis fixtures JSON en `fixtures/`
capturan la forma real de la API para seis runs reales de este repositorio,
elegidos para cubrir los cuatro bordes exigidos por S3-P1 (cancelado, no
arrancado, `skipped`, completado con éxito) más dos adicionales
(no-arrancado-cancelado-sin-job y completado-con-fallo) que hicieron falta
para que la tabla demostrara la distinción que pide el requisito 3 de la
incidencia.

La señal de clasificación adoptada es `total_jobs == 0` para "no arrancó"
-comprobado primero, antes que cualquier otra rama-, no un umbral de
duración ni el código HTTP de `/logs` en solitario: la medición encontró dos
variantes reales de "no arrancó" (un run que se queda en `queued` de forma
perpetua, y uno que se cancela en ~1 s sin llegar a crear ningún job) que
comparten `total_jobs==0` pero difieren en duración y en el código de
`/logs` (404 vs. 200 con cuerpo vacío). Cualquier señal basada en duración o
en `/logs` en solitario habría clasificado mal al menos uno de los dos.

Cotas propuestas para C1 (cadencia mínima de sondeo, señales de
clasificación por borde, coste de presupuesto por ciclo de sondeo), cada una
justificada por una fila de la tabla medida, en
[`RESULTADOS.md` §"Cotas propuestas para C1"](../../experiments/work_engine_spike_i1/RESULTADOS.md#cotas-propuestas-para-c1-s3-p2).
No las fija: la decisión de adoptarlas es de C1.

## Comprobación que la sostiene

- **Tabla borde×observación** con seis filas, cada una con el comando de
  `gh api` ejecutado de verdad y su salida recortada, en
  [`RESULTADOS.md`](../../experiments/work_engine_spike_i1/RESULTADOS.md#tabla-borde--observación-s3-p1)
  y reproducida por `tests/engine/test_spike_i1_boundary.py` sobre los
  fixtures congelados. Comando: `uv run pytest tests/engine/test_spike_i1_boundary.py -v`
  → **8 passed**.
- **Solo lectura demostrada** (S3-P3):
  `tests/engine/test_spike_i1_probe.py::test_solo_lectura_ejecutor_rechaza_toda_forma_de_escritura`
  prueba nueve formas de intentar escribir (verbo explícito, endpoints
  mutantes, banderas de cuerpo, comando de escritura de otro subcomando de
  `gh`), todas rechazadas ANTES de llegar al ejecutor interno -afirmado con
  un contador de llamadas, no solo con la excepción. Comando:
  `uv run pytest tests/engine/test_spike_i1_probe.py -v` → **24 passed**.
- **Determinismo** (S3-P4): `construir_tabla` produce el mismo resultado dos
  veces sobre los mismos fixtures (prueba dinámica), y un guarda estático
  basado en AST -mismo método que `tests/engine/test_boundary.py` usa para
  la frontera `sirius`/`sirius_engine`- afirma que ni `boundary.py` ni
  `probe.py` contienen ninguna llamada a `datetime.now`, `time.time`,
  `time.monotonic` ni `time.perf_counter`.
- **Tres mutaciones sembradas, vistas fallar cada una en la prueba que le
  correspondía, y revertidas** (requisito 4 de la incidencia, detalle
  completo con los comandos y la salida exacta en
  [`RESULTADOS.md` §"Prueba por mutación"](../../experiments/work_engine_spike_i1/RESULTADOS.md#prueba-por-mutación-adr-001-3-requisito-4-de-la-incidencia)):
  tratar "no arrancado" como "fallido" → 4 pruebas caen; quitar el guarda de
  solo lectura del `__post_init__` de la sonda → 1 prueba cae
  (`test_probe_envuelve_el_ejecutor_inyectado_con_el_guarda`); meter
  `datetime.now()` en el camino de la medición → 1 prueba cae (el guarda
  AST). Ninguna mutación pasó desapercibida.
- **`tests/engine/test_boundary.py` sigue en verde sin haberlo modificado**
  (exigido explícitamente por la incidencia): `git diff -- tests/engine/test_boundary.py`
  sin salida.
- **Las cuatro validaciones obligatorias + `git diff --check`, en verde**
  sobre el repositorio completo: `uv run ruff format --check .`,
  `uv run ruff check .`, `uv run mypy src tests` (413 ficheros,
  `experiments/` se resuelve como dependencia de
  `tests/engine/test_spike_i1_*.py` sin tocar `pyproject.toml`, igual que
  hizo S1), `uv run pytest` con `QT_QPA_PLATFORM=offscreen`, y
  `git diff --check` sin salida.

## Consecuencias

- **Lo que queda justificado por medición real** de este repositorio, no por
  documentación de GitHub ni por intuición: la señal estructural de "no
  arrancó" (`total_jobs==0`, no un umbral de duración -el hallazgo más
  importante del spike, ver "Decisión") y el coste de presupuesto por ciclo
  de sondeo (1 punto de rate limit por endpoint leído).
- **Y dos cotas que este spike NO entrega, declaradas así a propósito**
  (rondas 4 y 5 de revisión, hallazgos CODEX-002 y CLAUDE-REVISOR-001):
  - **Cadencia mínima de sondeo: NO CONCLUYENTE.** Lo único medido es un
    desvío de propagación run↔job de **1 s**; de ahí no se deriva ningún
    intervalo. Una versión anterior de este ADR publicaba «≥5 s» como
    sostenida por la medición, y eso era un salto sin derivación: **C1 no
    debe tomar de aquí ninguna cifra de cadencia.**
  - **Cota de `LOST`: NO CONCLUYENTE.** `total_jobs == 0` está medido como
    señal de "todavía no existe job", pero una observación puntual no
    distingue un run recién encolado de uno atascado 48 h. Convertir esa
    señal en cota de `LOST` exige medir la evolución en el tiempo, y eso no
    cabe en un spike de solo lectura sobre el historial.
  El detalle y qué haría falta para cerrarlas, en la tabla "Cotas propuestas
  para C1" de `experiments/work_engine_spike_i1/RESULTADOS.md`, que es la
  fuente; este ADR no puede decir nada distinto de ella.
- **No se afirma la respuesta exacta al agotar el rate limit real (403,
  cabeceras).** Declarado NO CONCLUYENTE en la nota de arranque y sostenido
  en la medición: exhaustarlo de verdad dejaría sin cuota al token
  compartido con la automatización concurrente de este mismo repositorio.
  Queda escrito qué haría falta (un token dedicado) para quien quiera
  cerrarlo.
- **No se afirma el comportamiento de un run expirado por retención.** Este
  repositorio tiene 40 días de historial; la retención por defecto de
  GitHub Actions es de 90. Declarado NO CONCLUYENTE, no sustituido por
  documentación de terceros (ADR-036).
- No fija ninguna pieza del motor: C1 decide si reutiliza esta sonda, el
  clasificador, o ninguno de los dos.

## Alternativas descartadas y por qué

**Umbral de duración para "no arrancó"** (p. ej. "menos de N segundos").
Descartada por evidencia directa: el caso "no arrancado perpetuo" medido
lleva más de 48 horas en `queued` al momento de escribir este ADR. Cualquier
umbral fijo lo habría clasificado mal, y es exactamente el riesgo principal
que la incidencia declaró ("medir solo el camino feliz").

**Código HTTP de `/logs` como única señal de "no arrancó".** Medido, no
adoptado: los dos runs "no arrancados" del historial dieron códigos
distintos (404 el perpetuo, 200 con cuerpo vacío el cancelado en ~1 s) pese
a compartir la misma ausencia estructural de job. Se conserva como columna
informativa de la tabla, no como criterio de clasificación.

**Revisión manual del código como garantía de solo lectura**, en vez de un
guarda ejecutable. Descartada: no es verificable en cada ejecución real, y
una mutación que quite la comprobación (probada de verdad, ver "Comprobación
que la sostiene") no la habría detectado sin `SoloLecturaEjecutor` corriendo
en cada llamada.

**Exhaustar el rate limit real** para observar el 403 exacto de agotamiento.
Descartada antes de medir (nota de arranque) y confirmada al medir: el token
de `gh` de este runner es el mismo que usa cualquier otra automatización
concurrente de `canelamoraguezandyjesus-bot/sirius` -y el propio historial
medido en este spike muestra que esos workflows corren constantemente.
Vaciar la cuota real (miles de peticiones) la dejaría sin cupo para esa
automatización hasta el reinicio de la ventana horaria: exactamente el tipo
de efecto en un sistema compartido que el alcance de solo lectura de esta
incidencia prohíbe.
