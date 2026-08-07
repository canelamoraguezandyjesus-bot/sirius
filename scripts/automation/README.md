# Automatización de Sirius — utilidades de E/S robusta

Estas utilidades hacen fiable la automatización genérica de Sirius 0.1 (ver
`docs/implementation/AUTOMATION_OPERATING_CONTRACT.md` y
`docs/implementation/SIRIUS_GENERIC_ROUTINES_0.1.md`). Nacieron de la incidencia
#55, donde una lectura por una sola vía (GraphQL/MCP) devolvió 502/503 y cuerpos
truncados y una escritura posterior corrompió el cuerpo de la incidencia.

## `sirius_issue.sh`

Biblioteca Bash para leer y escribir incidencias sin depender de una sola vía y
sin aceptar contenido truncado. Está pensada para ser segura con `set -u` y
`set -o pipefail` y para **no** depender de `set -e`.

```bash
source scripts/automation/sirius_issue.sh
```

Funciones principales:

- `sirius_read_issue_body <repo> <n>` — cuerpo por REST con reintentos y respaldo
  GraphQL.
- `sirius_read_issue_comments <repo> <n>` — comentarios por REST con respaldo
  GraphQL. Ambas vías filtran por autor de confianza (propietario o
  `github-actions[bot]`), igual que `sirius_dump_comments` y `sirius_scan_text`:
  ninguna lectura de comentarios de esta biblioteca ve texto de terceros.
- `sirius_read_workitem_body <repo> <n> <archivo>` — lee de forma robusta y solo
  acepta el cuerpo si contiene todas las secciones obligatorias del contrato
  (rechaza respuestas truncadas).
- `sirius_write_issue_body <repo> <n> <archivo> [respaldo]` — rechaza cuerpos de
  origen truncados, respalda el cuerpo anterior, escribe de una sola vez por REST
  y verifica por relectura (longitud + hash).
- `sirius_comment_once <repo> <n> <marcador> <archivo>` — publica el comentario
  solo si el marcador no está ya. Publicar contra la API **no puede ser
  exactamente-una-vez**: `gh issue comment` no es idempotente y no hay clave de
  idempotencia del servidor, así que un resultado ambiguo (GitHub acepta y la
  respuesta se pierde) deja el comentario publicado sin que se pueda demostrar.
  Por eso la garantía vive en los **lectores** —`parse_round_records` cuenta una
  ronda por número y `ci_failure_streak` cuenta heads distintos—: un duplicado es
  ruido en la incidencia, nunca una medida falseada. Siendo inocuo el duplicado,
  reintenta hasta agotar un **plazo total** (`SIRIUS_COMMENT_BUDGET_SECONDS`,
  90 s), comprobado antes de cada llamada y con la espera recortada a lo que
  queda; perder el registro sí hace daño, porque `complete-sirius-after-merge`
  cierra la incidencia antes de publicar y luego solo busca las abiertas. Tras un
  fallo relee: si el marcador aparece, termina sin republicar.
- `sirius_ensure_label <repo> <nombre> <color> <descripcion>` — etiqueta
  idempotente.
- `sirius_scan_text` / `sirius_extract_sha` — extracción robusta de Head/Merge SHA
  (comentarios más recientes primero, luego el cuerpo; `no-head` si no hay).
- `sirius_retry <cmd...>` — reintentos limitados con espera creciente
  (`SIRIUS_RETRY_ATTEMPTS`, `SIRIUS_RETRY_BASE_DELAY`).

Requisitos en ejecución: `gh`, `jq`, `python3`.

Los workflows invocan estos scripts con `python3` a secas y sin
`actions/setup-python`: se ejecutan con el intérprete del sistema del runner
`ubuntu-latest` (hoy 3.12), no con el 3.14 del entorno de desarrollo. La
sintaxis nueva pasa Quality y revienta en producción, así que
`tests/automation/test_sirius_runner_python_compat.py` analiza cada script con
la versión de lenguaje del runner. Si los workflows pasan a fijar el intérprete,
`RUNNER_PYTHON` debe subir en el mismo cambio.

## `sirius_codex_review.py`

Disparador y recolector de la revisión nativa de Codex para la revisión dual
(contrato operativo §4.1, bandera `SIRIUS_CODEX_REVIEW_ENABLED`). `trigger`
publica (o reutiliza de forma idempotente) el comentario `@codex review` con un
marcador oculto por head; solo reutiliza un disparador **propio** (autor igual a
la identidad real del token y cuerpo idéntico a la plantilla), para que un
comentario ajeno con el mismo marcador no pueda hacer valer una revisión no
solicitada por el workflow; `collect` espera el resultado del conector oficial
(allowlist `SIRIUS_CODEX_ALLOWED_AUTHORS`), verifica que la revisión
corresponde exactamente al head esperado (`commit_id` o marcador
`Reviewed commit:`), reconoce la aprobación explícita (revisión `APPROVED` o
reacción `+1` del conector sobre el disparador; `eyes` solo indica
procesamiento) y escribe un JSON normalizado. Timeout configurable
(`SIRIUS_CODEX_REVIEW_TIMEOUT_SECONDS`, 1200 s por defecto) y limitado por
`SIRIUS_CODEX_REVIEW_MAX_TIMEOUT_SECONDS` (1500 s) para que el resultado se
escriba siempre antes de que expire el paso del workflow; cualquier caso no
identificable con seguridad termina en `FAILED_SAFELY`. Un resultado no se
entrega al verlo por primera vez: hay que observarlo dos veces igual con una
ventana de estabilidad de por medio (`SIRIUS_CODEX_SETTLE_SECONDS`, 60 s), que
cualquier hallazgo nuevo reinicia, porque el conector puede publicar en varias
tandas; la ventana está acotada por el plazo absoluto. No usa la API de OpenAI
y nunca modifica código.

## `sirius_aggregate_reviews.py`

Agregador determinista de la revisión dual: combina el JSON del revisor Claude
y el JSON normalizado de Codex en un único veredicto compatible con
`sirius_apply_verdict.sh`, con reglas fijas de precedencia (inválido → fallo
seguro; SHA no demostrable → fallo seguro; fallo de cualquiera → fallo seguro;
bloqueo de Claude; cambios de cualquiera; aprobación solo si ambos aprueban el
mismo SHA), deduplicación solo de duplicados exactos y procedencia conservada
con prefijos `CLAUDE-`/`CODEX-`.

## `sirius_convergence.py`

Política de convergencia del ciclo revisión-corrección (contrato §5.1), que
sustituye al tope fijo de dos ciclos. `record` emite el registro de una ronda
(huella estable por hallazgo, severidad, procedencia, head y totales), que
`sirius_apply_verdict.sh` publica en la incidencia bajo
`## RONDA_HALLAZGOS`. `decide` lee ese historial y determina si la corrección
puede continuar (`CONTINUE`) o debe pasar a decisión humana (`BLOCK`) por falta
de progreso en dos rondas consecutivas, reaparición de un hallazgo resuelto,
oscilación entre estados anteriores, head sin avanzar o historial ilegible.
Módulo puro, sin red.

## `validate_issue_body.py`

Validador estructural puro (sin red) del cuerpo de una incidencia de trabajo. Se
usa desde la biblioteca y desde las pruebas. Como CLI sale con 0 si el cuerpo es
completo y con 1 si está truncado o le faltan secciones obligatorias:

```bash
python3 scripts/automation/validate_issue_body.py cuerpo.md
```

## Pruebas

`tests/automation/` ejercita ambas utilidades con un `gh` simulado (sin red):
lectura correcta, 502/503 seguido de éxito por REST, respaldo GraphQL, cuerpo
truncado o incompleto rechazado, todas las vías fallan → parada segura, escritura
verificada y detección de escritura corrupta, e idempotencia de etiquetas.
