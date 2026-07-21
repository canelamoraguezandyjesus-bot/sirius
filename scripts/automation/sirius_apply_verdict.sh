#!/usr/bin/env bash
# Sirius — aplicación determinista del veredicto de un rol de Claude Code.
#
# Los workflows de rol (implementador/revisor/corrector) ejecutan Claude Code
# dentro del runner para hacer el trabajo real, pero NUNCA dejan que el propio
# agente mute etiquetas ni cierre la incidencia: Claude solo escribe un
# veredicto en un archivo JSON de forma fija (ver scripts/automation/prompts/).
# Este script es quien aplica esa decisión, reverificando por su cuenta todo
# lo que se pueda verificar (existencia y estado de la PR, head actual,
# consistencia con el head que pasó CI) en vez de confiar en lo que el agente
# afirme. Un veredicto ausente, corrupto o fuera del conjunto permitido para
# el rol se trata como un fallo seguro, nunca como éxito silencioso.
#
# Uso: sirius_apply_verdict.sh <owner/repo> <issue> <role> <verdict_file> [cycle]
#   role: implementer | reviewer | corrector
#   cycle: solo corrector; número de ciclo de reparación que se está cerrando.

set -uo pipefail

SIRIUS_VERDICT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
# shellcheck source=scripts/automation/sirius_issue.sh
source "${SIRIUS_VERDICT_DIR}/sirius_issue.sh"

REPO="${1:?uso: sirius_apply_verdict.sh <owner/repo> <issue> <role> <verdict_file> [cycle]}"
ISSUE="${2:?uso: sirius_apply_verdict.sh <owner/repo> <issue> <role> <verdict_file> [cycle]}"
ROLE="${3:?uso: sirius_apply_verdict.sh <owner/repo> <issue> <role> <verdict_file> [cycle]}"
VERDICT_FILE="${4:?uso: sirius_apply_verdict.sh <owner/repo> <issue> <role> <verdict_file> [cycle]}"
CYCLE="${5:-}"

case "$ROLE" in
  implementer) IN_PROGRESS_LABEL="sirius:implementing" ;;
  reviewer) IN_PROGRESS_LABEL="sirius:reviewing" ;;
  corrector) IN_PROGRESS_LABEL="sirius:repairing" ;;
  *)
    echo "::error::sirius_apply_verdict: rol desconocido '${ROLE}'." >&2
    exit 1
    ;;
esac

# transition <marker> <body_file> <add_label> <color> <desc>
transition() {
  local marker="$1" body_file="$2" add="$3" color="$4" desc="$5"
  sirius_transition "$REPO" "$ISSUE" "$marker" "$body_file" \
    "$add" "$color" "$desc" "noclose" "$IN_PROGRESS_LABEL"
}

stop_safely() {
  # stop_safely <reason-slug> <explicacion> — parada segura determinista
  # (no depende del veredicto del agente: el propio script detectó algo
  # inconsistente y no continúa). Siempre termina el script con estado !=0:
  # es una anomalía que debe quedar visible como fallo del job (igual que
  # los casos de ambigüedad de advance-sirius-after-quality.yml), no un
  # rechazo esperado como el de la puerta de activación.
  local reason="$1" why="$2"
  local marker="<!-- sirius-verdict:${ROLE}:precheck:${reason} -->"
  local body_file
  body_file="$(mktemp)"
  printf '%s\n\n%s\n\n%s\n' \
    "$marker" \
    "🔴 **Me he detenido de forma segura**" \
    "$why" >"$body_file"
  if ! transition "$marker" "$body_file" "sirius:failed-safely" "D93F0B" \
    "Estado temporal: fallo operativo detenido de forma segura"; then
    echo "::error::No se pudo aplicar la parada segura (${reason}) para #${ISSUE}; reintentable." >&2
  fi
  rm -f "$body_file"
  exit 1
}

# --- 1) El veredicto debe existir y ser JSON válido con "verdict" -------------
if [ ! -s "$VERDICT_FILE" ]; then
  stop_safely "sin-veredicto" \
    "El rol \`${ROLE}\` no escribió ningún veredicto. Sin un resultado estructurado no puedo saber en qué quedó el trabajo."
fi
if ! verdict="$(jq -r '.verdict // empty' "$VERDICT_FILE" 2>/dev/null)" || [ -z "$verdict" ]; then
  stop_safely "veredicto-invalido" \
    "El archivo de veredicto del rol \`${ROLE}\` no es JSON válido o no tiene el campo \`verdict\`."
fi
summary="$(jq -r '.summary // "(sin resumen)"' "$VERDICT_FILE" 2>/dev/null)"

case "$ROLE" in
  implementer) allowed="READY_FOR_REVIEW BLOCKED_BY_DECISION FAILED_SAFELY USAGE_LIMIT_REACHED" ;;
  reviewer) allowed="REVIEW_APPROVED CHANGES_REQUESTED BLOCKED_BY_DECISION FAILED_SAFELY" ;;
  corrector) allowed="FIXED BLOCKED_BY_DECISION FAILED_SAFELY" ;;
esac
if ! printf '%s\n' "$allowed" | tr ' ' '\n' | grep -Fxq "$verdict"; then
  stop_safely "veredicto-fuera-de-conjunto" \
    "El rol \`${ROLE}\` devolvió el veredicto \`${verdict}\`, que no es uno de los permitidos para ese rol (\`${allowed}\`)."
fi

# --- 2) Veredictos que exigen localizar y verificar la PR ----------------------
# `locate_verified_pr` NUNCA llama a `stop_safely` ni a `exit` directamente:
# se invoca mediante sustitución de comandos (`$(...)`), que corre en una
# subshell, así que un `exit` ahí dentro solo mataría la subshell y el script
# principal seguiría con variables vacías sin que nadie lo notara. En su
# lugar imprime un resultado con tabuladores que el llamador interpreta.
locate_verified_pr() {
  # Salida: "OK\t<pr>\t<head>" o "FAIL\t<motivo-slug>\t<explicacion>".
  mapfile -t pr_numbers < <(sirius_find_pr_for_issue "$REPO" "$ISSUE")
  if [ "${#pr_numbers[@]}" -eq 0 ]; then
    printf 'FAIL\tsin-pr\tEl rol `%s` reporto `%s`, pero no encuentro ninguna PR asociada a esta incidencia (falta el comentario con su URL).\n' "$ROLE" "$verdict"
    return 0
  fi
  if [ "${#pr_numbers[@]}" -ne 1 ]; then
    printf 'FAIL\tvarias-pr\tEsta incidencia referencia varias PR distintas; no puedo continuar sin ambiguedad.\n'
    return 0
  fi
  local pr="${pr_numbers[0]}"
  local pr_json
  pr_json="$(sirius_retry gh api "repos/${REPO}/pulls/${pr}" --jq '{state: .state, draft: .draft, head: .head.sha}')" || pr_json=""
  if [ -z "$pr_json" ]; then
    printf 'FAIL\tpr-illegible\tNo he podido leer el estado de la PR #%s.\n' "$pr"
    return 0
  fi
  local pr_state pr_draft pr_head
  pr_state="$(printf '%s' "$pr_json" | jq -r '.state')"
  pr_draft="$(printf '%s' "$pr_json" | jq -r '.draft')"
  pr_head="$(printf '%s' "$pr_json" | jq -r '.head')"
  if [ "$pr_state" != "open" ] || [ "$pr_draft" = "true" ]; then
    printf 'FAIL\tpr-no-lista\tLa PR #%s no esta abierta y lista (estado `%s`, borrador `%s`).\n' "$pr" "$pr_state" "$pr_draft"
    return 0
  fi
  printf 'OK\t%s\t%s\n' "$pr" "$pr_head"
}

# resolve_pr <verdict-actual> — ejecuta locate_verified_pr, aplica
# stop_safely si falló (esto sí corre en el shell principal) y deja
# pr_number/head_sha listos. Termina el script si falla.
resolve_pr() {
  local result status field2 field3
  result="$(locate_verified_pr)"
  status="$(printf '%s' "$result" | cut -f1)"
  field2="$(printf '%s' "$result" | cut -f2)"
  field3="$(printf '%s' "$result" | cut -f3)"
  if [ "$status" != "OK" ]; then
    stop_safely "$field2" "$field3"
  fi
  pr_number="$field2"
  head_sha="$field3"
}

case "$verdict" in
  READY_FOR_REVIEW | FIXED)
    resolve_pr
    pr_url="https://github.com/${REPO}/pull/${pr_number}"
    marker="<!-- sirius-verdict:${ROLE}:${verdict}:${head_sha} -->"
    body_file="$(mktemp)"
    if [ "$ROLE" = "corrector" ] && [ -n "$CYCLE" ]; then
      printf '%s\n\n%s\n\n%s\n%s\n%s\n%s\n' \
        "$marker" "<!-- sirius-repair-cycle:${CYCLE} -->" \
        "## CORRECCION_APLICADA" \
        "- PR: ${pr_url}" \
        "- Head SHA: \`${head_sha}\`" \
        "${summary}" >"$body_file"
    else
      printf '%s\n\n%s\n%s\n%s\n%s\n' \
        "$marker" \
        "## IMPLEMENTACION_LISTA" \
        "- PR: ${pr_url}" \
        "- Head SHA: \`${head_sha}\`" \
        "${summary}" >"$body_file"
    fi
    if ! transition "$marker" "$body_file" "sirius:ci-pending" "FBCA04" "Evento consumible: en espera de Quality"; then
      rm -f "$body_file"
      exit 1
    fi
    rm -f "$body_file"
    ;;

  REVIEW_APPROVED)
    resolve_pr
    scan_file="$(mktemp)"
    sirius_scan_text "$REPO" "$ISSUE" "$scan_file"
    last_ci_sha="$(sirius_extract_sha "$scan_file")"
    rm -f "$scan_file"
    if [ "$last_ci_sha" = "no-head" ] || [ "$last_ci_sha" != "$head_sha" ]; then
      stop_safely "head-inconsistente" \
        "El revisor aprobó, pero el head actual de la PR (\`${head_sha}\`) no coincide con el último head que superó Quality (\`${last_ci_sha}\`). No aprobar sin volver a ejecutar CI sobre el head exacto."
    fi
    pr_url="https://github.com/${REPO}/pull/${pr_number}"
    marker="<!-- sirius-verdict:reviewer:approved:${head_sha} -->"
    body_file="$(mktemp)"
    printf '%s\n\n%s\n%s\n%s\n%s\n' \
      "$marker" \
      "## REVIEW_APPROVED" \
      "- PR: ${pr_url}" \
      "- Head SHA: \`${head_sha}\`" \
      "${summary}" >"$body_file"
    if ! transition "$marker" "$body_file" "sirius:ready-for-merge" "0E8A16" "Estado: listo para fusionar (requiere tu autorización)"; then
      rm -f "$body_file"
      exit 1
    fi
    rm -f "$body_file"
    ;;

  CHANGES_REQUESTED)
    observations="$(jq -c '.observations // []' "$VERDICT_FILE" 2>/dev/null)" || observations="[]"
    if [ "$observations" = "[]" ] || [ -z "$observations" ]; then
      stop_safely "sin-observaciones" \
        "El revisor pidió \`CHANGES_REQUESTED\` sin ninguna observación estructurada; no hay nada concreto que corregir."
    fi
    readable="$(printf '%s' "$observations" | jq -r '.[] | "- **\(.id // "?")** (\(.severidad // "?")) \(.archivo // "?"): \(.problema // "?")\n  - Criterio esperado: \(.criterio_esperado // "?")\n  - Prueba: \(.prueba // "?")\n  - Límites de corrección: \(.limites_correccion // "?")"')"
    pr_hint=""
    mapfile -t pr_numbers < <(sirius_find_pr_for_issue "$REPO" "$ISSUE")
    if [ "${#pr_numbers[@]}" -eq 1 ]; then
      pr_hint="https://github.com/${REPO}/pull/${pr_numbers[0]}"
    fi
    marker="<!-- sirius-verdict:reviewer:changes:$(printf '%s' "$observations" | sha256sum | cut -c1-16) -->"
    body_file="$(mktemp)"
    {
      printf '%s\n\n%s\n' "$marker" "## CHANGES_REQUESTED"
      [ -n "$pr_hint" ] && printf '- PR: %s\n' "$pr_hint"
      printf '%s\n\n%s\n\n## OBSERVACIONES_ESTRUCTURADAS\n```json\n%s\n```\n' "${summary}" "${readable}" "${observations}"
    } >"$body_file"
    if ! transition "$marker" "$body_file" "sirius:repair-requested" "FBCA04" "Evento consumible: corregir observaciones técnicas registradas"; then
      rm -f "$body_file"
      exit 1
    fi
    rm -f "$body_file"
    ;;

  BLOCKED_BY_DECISION)
    marker="<!-- sirius-verdict:${ROLE}:blocked -->"
    body_file="$(mktemp)"
    printf '%s\n\n%s\n\n%s\n' "$marker" "🟡 **Necesito una decisión**" "${summary}" >"$body_file"
    if ! transition "$marker" "$body_file" "sirius:blocked-decision" "D4C5F9" "Estado: requiere una decisión humana"; then
      rm -f "$body_file"
      exit 1
    fi
    rm -f "$body_file"
    ;;

  FAILED_SAFELY | USAGE_LIMIT_REACHED)
    marker="<!-- sirius-verdict:${ROLE}:${verdict} -->"
    body_file="$(mktemp)"
    printf '%s\n\n%s\n\n%s\n' "$marker" "🔴 **Me he detenido de forma segura**" "${summary}" >"$body_file"
    if ! transition "$marker" "$body_file" "sirius:failed-safely" "D93F0B" "Estado temporal: fallo operativo detenido de forma segura"; then
      rm -f "$body_file"
      exit 1
    fi
    rm -f "$body_file"
    ;;
esac

echo "Veredicto ${verdict} del rol ${ROLE} aplicado para #${ISSUE}."
exit 0
