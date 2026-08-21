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

## Decisión

## Comprobación que la sostiene

[Evidencia concreta: comandos ejecutados, resultados, enlaces exactos. Sin
esta sección, el ADR afirma más de lo que el dato sostiene.]

## Consecuencias

## Alternativas descartadas y por qué
