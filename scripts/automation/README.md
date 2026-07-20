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
  GraphQL.
- `sirius_read_workitem_body <repo> <n> <archivo>` — lee de forma robusta y solo
  acepta el cuerpo si contiene todas las secciones obligatorias del contrato
  (rechaza respuestas truncadas).
- `sirius_write_issue_body <repo> <n> <archivo> [respaldo]` — rechaza cuerpos de
  origen truncados, respalda el cuerpo anterior, escribe de una sola vez por REST
  y verifica por relectura (longitud + hash).
- `sirius_ensure_label <repo> <nombre> <color> <descripcion>` — etiqueta
  idempotente.
- `sirius_scan_text` / `sirius_extract_sha` — extracción robusta de Head/Merge SHA
  (comentarios más recientes primero, luego el cuerpo; `no-head` si no hay).
- `sirius_retry <cmd...>` — reintentos limitados con espera creciente
  (`SIRIUS_RETRY_ATTEMPTS`, `SIRIUS_RETRY_BASE_DELAY`).

Requisitos en ejecución: `gh`, `jq`, `python3`.

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
