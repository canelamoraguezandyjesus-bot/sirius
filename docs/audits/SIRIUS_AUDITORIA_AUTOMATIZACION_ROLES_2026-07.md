# SIRIUS — Auditoría de robustez de la automatización de roles (Claude Code)

**Fecha:** 21 de julio de 2026
**Ámbito:** Los tres workflows de rol (implementador/revisor/corrector) que ejecutan Claude Code real vía `anthropics/claude-code-action@v1`, el script determinista `sirius_apply_verdict.sh` y la configuración de permisos `.claude/settings.json`.
**Motivación:** Dejar la automatización estable y fluida tras un piloto en vivo sobre la incidencia de humo #66 (SIRIUS-SMOKE-001), que reveló varios problemas de configuración y de observabilidad.
**No modifica:** Producto, Arquitectura Técnica, ATD ni alcance de Sirius 0.1.

## 1. Qué quedó PROBADO en vivo (no rehacer)

Durante el piloto sobre #66 se validó, con ejecuciones reales, que:

- La cadena etiqueta-evento → workflow dispara correctamente.
- La puerta de activación (`sirius_validate_activation.sh`), el consumo del evento y el marcado de estado funcionan.
- Claude Code se ejecuta de verdad dentro del runner (última ejecución: 37 turnos, ~4 min).
- `sirius_apply_verdict.sh` aplica el veredicto de forma determinista y **nunca deja que el agente mute etiquetas**; ante un veredicto ausente o de parada, ejecuta una parada segura.
- La transición auto-reparadora (marcador presente con estado incompleto) se comporta como se diseñó.

## 2. Problemas encontrados y resueltos durante el piloto (previos a esta auditoría)

| # | Síntoma | Causa | Resolución |
|---|---------|-------|------------|
| 1 | `Could not fetch an OIDC token` | Faltaba `id-token: write` | PR #67 |
| 2 | `Unexpected input(s) 'allowed_tools', 'max_turns'` | No son entradas de la acción; van en `claude_args` | PR #67 |
| 3 | Claude paraba a los 2 turnos (`permission_denials_count`) | Faltaba `--dangerously-skip-permissions` (modo headless deniega herramientas interactivas) | PR #68 |
| 4 | Veto total de `gh` bloqueaba leer/abrir PR/comentar | `Bash(gh *)` en `deny`, que gana sobre skip-permissions | PR #69 (allow acotado de gh) |

## 3. Hallazgos de esta auditoría y correcciones

### H-1 — Los motivos de parada del agente se perdían (observabilidad) · CORREGIDO
Los marcadores de idempotencia de `FAILED_SAFELY`, `BLOCKED_BY_DECISION` y las paradas `precheck` del script eran fijos por rol (`<!-- sirius-verdict:implementer:FAILED_SAFELY -->`). Dos paradas del mismo tipo en runs distintos compartían marcador, y `sirius_comment_once` dedupaba la segunda: **el diagnóstico del segundo run no se publicaba en ningún sitio**, y la salida del agente está oculta por seguridad. Resultado: depuración a ciegas.

**Corrección:** los marcadores de veredicto de parada del agente llevan ahora un sufijo único por run (`${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}`). Cada parada publica su propio comentario con su motivo, sin perder la idempotencia dentro del mismo run. Los veredictos de avance (`READY_FOR_REVIEW`/`FIXED`/`REVIEW_APPROVED`/`CHANGES_REQUESTED`) siguen anclados al head SHA o al hash del contenido, que ya los hace únicos y estables. Las paradas *precheck* deterministas del gate del corrector (límite de ciclos, sin PR, sin observaciones) conservan marcador fijo a propósito: su motivo no varía y no queremos spam.

### H-2 — Creación de archivos nuevos probablemente denegada (permisos) · CORREGIDO
`.claude/settings.json` autorizaba `Edit(./src/**)` y `Edit(./tests/**)` pero **no `Write(...)`**. El implementador crea módulos y pruebas nuevos con la herramienta **Write**; como `deny` gana sobre `--dangerously-skip-permissions`, la creación de archivos nuevos quedaba en la ambigüedad de la política. Es la hipótesis principal de las denegaciones residuales del último run.

**Corrección:** se añaden al `allow` `Write(./src/**)`, `Write(./tests/**)`, `Write(./migrations/**)`, `Write(./docs/implementation/**)` (espejo de los `Edit` ya permitidos) y los comandos git no destructivos que el flujo necesita explícitamente (`git checkout/switch/add/commit/fetch/rev-parse/remote/push`) más `uv sync`/`uv run`. Los vetos peligrosos se conservan intactos. Combinado con H-1, si aún quedara alguna denegación, el comentario del agente ahora la nombra.

### H-3 — Ruido y cancelaciones por concurrencia · CORREGIDO
Los tres workflows escuchan `issues: labeled` y compartían el grupo `sirius-work-<incidencia>`. Una sola etiqueta despierta a los tres (los que no coinciden saltan su job), y además el evento de `sirius:planned` y el de `sirius:implement-requested` competían por el mismo grupo, llegando a **cancelar el run bueno** (observado en el piloto).

**Corrección:** el grupo de concurrencia pasa a ser por **rol + incidencia + etiqueta**: `sirius-<rol>-<incidencia>-<label>`. Así los tres workflows no colisionan entre sí para un mismo evento, y el evento de `planned` no cancela al de `implement-requested`. Se conserva la exclusión única para dos eventos idénticos sobre la misma incidencia (evita duplicados reales).

## 4. Pruebas

- `tests/automation/test_sirius_apply_verdict.py`: 17 casos (2 nuevos) — verifican que dos runs distintos publican su propio motivo (`FAILED_SAFELY` con sufijo por run) y que un reintento del mismo run sigue siendo idempotente.
- Suite completa `tests/automation/`: 91 en verde.
- YAML de los tres workflows validado; `claude_args` y grupos de concurrencia revisados.

## 5. Validación en vivo pendiente

Estas correcciones son de configuración de una acción externa que no puede probarse sin ejecutarla. El siguiente run del implementador sobre #66 debería, o bien completar el ciclo (crear la función, abrir PR, veredicto `READY_FOR_REVIEW`, incidencia a `sirius:ci-pending`), o bien —si quedara alguna denegación— **decir exactamente cuál** gracias a H-1. Coste: un run de Quality (PR) + un run del implementador. El merge de cualquier PR sigue requiriendo autorización humana explícita.

## 6. Estado del contrato

Ningún cambio altera el contrato de estados, el límite de dos ciclos de corrección, ni el control humano del merge (`AUTOMATION_OPERATING_CONTRACT.md` §8). El revisor conserva su token de solo lectura (`contents: read`): aunque los permisos de herramientas se amplíen, no puede hacer push.
