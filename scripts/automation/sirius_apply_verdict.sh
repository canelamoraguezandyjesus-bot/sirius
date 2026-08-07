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
# Para los resultados de revisión (REVIEW_APPROVED y CHANGES_REQUESTED) el
# veredicto debe declarar además `reviewed_head_sha`, y se exige coincidencia
# exacta entre tres valores: ese SHA declarado, el head actual de la PR y el
# último head que superó Quality registrado en la incidencia (contrato
# §4.1). En el modo de revisión dual el JSON puede venir del agregador
# determinista (sirius_aggregate_reviews.py) en lugar del revisor Claude.
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

SIRIUS_RUN_TAG="${GITHUB_RUN_ID:-manual}-${GITHUB_RUN_ATTEMPT:-1}"
SIRIUS_ROUND_TAG="${GITHUB_RUN_ID:-manual}"

transition() {
  local marker="$1" body_file="$2" add="$3" color="$4" desc="$5"
  sirius_transition "$REPO" "$ISSUE" "$marker" "$body_file" \
    "$add" "$color" "$desc" "noclose" "$IN_PROGRESS_LABEL"
}

stop_safely() {
  local reason="$1" why="$2"
  local marker="<!-- sirius-verdict:${ROLE}:precheck:${reason}:${SIRIUS_RUN_TAG} -->"
  local body_file
  body_file="$(mktemp)"
  printf '%s\n\n%s\n\n%s\n' \
    "$marker" \
    "🔴 **Me he detenido de forma segura**" \
    "$why" >"$body_file"
  if ! transition "$marker" "$body_file" "sirius:failed-safely" "D93F0B" \
    "Estado temporal: fallo operativo detenido de forma segura"; then
    # Si el historial es ilegible, la transición no puede deduplicar y se
    # detiene antes de mutar estado. El aviso de parada no es un registro de
    # ronda ni gobierna la convergencia y su marcador incluye el run, por lo que
    # publicarlo directamente conserva trazabilidad sin crear una ronda falsa.
    echo "::warning::No se pudo registrar la parada segura (${reason}) mediante la transición verificada; aplicando el estado y el aviso de diagnóstico." >&2
    if ! sirius_ensure_label "$REPO" "sirius:failed-safely" "D93F0B" \
      "Estado temporal: fallo operativo detenido de forma segura" \
      || ! sirius_set_issue_labels "$REPO" "$ISSUE" "sirius:failed-safely" "$IN_PROGRESS_LABEL"; then
      echo "::error::No se pudo aplicar la etiqueta de parada segura (${reason}) para #${ISSUE}; reintentable." >&2
    fi
    if ! sirius_retry gh issue comment "$ISSUE" --repo "$REPO" --body-file "$body_file"; then
      echo "::error::No se pudo publicar el diagnóstico de parada segura (${reason}) para #${ISSUE}; reintentable." >&2
    fi
  fi
  rm -f "$body_file"
  exit 1
}

if [ ! -s "$VERDICT_FILE" ]; then
  stop_safely "sin-veredicto" \
    "El rol \`${ROLE}\` no escribió ningún veredicto. Sin un resultado estructurado no puedo saber en qué quedó el trabajo."
fi
if ! verdict="$(jq -r '.verdict // empty' "$VERDICT_FILE" 2>/dev/null)" || [ -z "$verdict" ]; then
  stop_safely "veredicto-invalido" \
    "El archivo de veredicto del rol \`${ROLE}\` no es JSON válido o no tiene el campo \`verdict\`."
fi

sanitize_untrusted_text() {
  jq -Rrs 'gsub("```"; "\u0027\u0027\u0027") | gsub("(?<p>[Hh][Ee][Aa][Dd]|[Mm][Ee][Rr][Gg][Ee])(\\s+[Ss][Hh][Aa]\\s*:)"; "\(.p)-sha:")'
}
sanitize_untrusted_json() {
  jq -c 'walk(if type == "string" then gsub("```"; "\u0027\u0027\u0027") | gsub("(?<p>[Hh][Ee][Aa][Dd]|[Mm][Ee][Rr][Gg][Ee])(\\s+[Ss][Hh][Aa]\\s*:)"; "\(.p)-sha:") else . end)'
}

summary="$(jq -r '.summary // "(sin resumen)"' "$VERDICT_FILE" 2>/dev/null | sanitize_untrusted_text)"

case "$ROLE" in
  implementer) allowed="READY_FOR_REVIEW BLOCKED_BY_DECISION FAILED_SAFELY USAGE_LIMIT_REACHED" ;;
  reviewer) allowed="REVIEW_APPROVED CHANGES_REQUESTED BLOCKED_BY_DECISION FAILED_SAFELY" ;;
  corrector) allowed="FIXED BLOCKED_BY_DECISION FAILED_SAFELY" ;;
esac
if ! printf '%s\n' "$allowed" | tr ' ' '\n' | grep -Fxq "$verdict"; then
  stop_safely "veredicto-fuera-de-conjunto" \
    "El rol \`${ROLE}\` devolvió el veredicto \`${verdict}\`, que no es uno de los permitidos para ese rol (\`${allowed}\`)."
fi

locate_verified_pr() {
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

sha_matches() {
  local full cand
  full="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  cand="$(printf '%s' "$2" | tr '[:upper:]' '[:lower:]')"
  case "$cand" in
    '' | *[!0-9a-f]*) return 1 ;;
  esac
  if [ "${#cand}" -lt 7 ] || [ "${#cand}" -gt 40 ]; then
    return 1
  fi
  case "$full" in
    "$cand"*) return 0 ;;
  esac
  return 1
}

require_reviewed_head() {
  local reviewed_sha scan_file last_ci_sha
  reviewed_sha="$(jq -r '.reviewed_head_sha // empty' "$VERDICT_FILE" 2>/dev/null)"
  if [ -z "$reviewed_sha" ]; then
    stop_safely "sin-reviewed-head" \
      "El veredicto \`${verdict}\` no declara \`reviewed_head_sha\`. Sin esa declaración no puedo demostrar qué versión se revisó, así que no aplico el resultado."
  fi
  if ! sha_matches "$head_sha" "$reviewed_sha"; then
    stop_safely "reviewed-head-distinto" \
      "El veredicto \`${verdict}\` declara haber revisado \`${reviewed_sha}\`, pero el head actual de la PR es \`${head_sha}\`. No aplico un resultado de revisión sobre otra versión."
  fi
  scan_file="$(mktemp)"
  sirius_scan_text "$REPO" "$ISSUE" "$scan_file"
  last_ci_sha="$(sirius_extract_sha "$scan_file")"
  rm -f "$scan_file"
  if [ "$last_ci_sha" = "no-head" ] || [ "$last_ci_sha" != "$head_sha" ]; then
    stop_safely "head-inconsistente" \
      "El veredicto es \`${verdict}\`, pero el head actual de la PR (\`${head_sha}\`) no coincide con el último head que superó Quality (\`${last_ci_sha}\`). El resultado sería sobre una versión obsoleta; descarto la ronda de forma segura."
  fi
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
    require_reviewed_head
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
    resolve_pr
    require_reviewed_head
    observations="$(printf '%s' "$observations" | sanitize_untrusted_json)"
    if [ -z "$observations" ] || [ "$observations" = "[]" ]; then
      stop_safely "sanitizacion-fallida" \
        "No se pudieron sanear las observaciones estructuradas antes de publicarlas; me detengo para no entregar al corrector un bloque corrupto."
    fi
    readable="$(printf '%s' "$observations" | jq -r '.[] | "- **\(.id // "?")** (\(.severidad // "?")) \(.archivo // "?"): \(.problema // "?")\n  - Criterio esperado: \(.criterio_esperado // "?")\n  - Prueba: \(.prueba // "?")\n  - Límites de corrección: \(.limites_correccion // "?")"')"
    pr_hint="https://github.com/${REPO}/pull/${pr_number}"

    if ! round_number="$(sirius_next_round_number "$REPO" "$ISSUE")"; then
      stop_safely "historial-de-rondas-ilegible" \
        "No he podido leer el historial de rondas de esta incidencia, así que no puedo numerar esta ronda sin arriesgarme a repetir un número ya usado y corromper la medida de convergencia. Me detengo de forma segura."
    fi
    round_verdict="$(mktemp)"
    round_record="$(mktemp)"
    jq -n --argjson obs "$observations" '{observations: $obs}' >"$round_verdict"
    if ! python3 "${SIRIUS_VERDICT_DIR}/sirius_convergence.py" record \
      --verdict-file "$round_verdict" --round "$round_number" \
      --head "$head_sha" --output "$round_record"; then
      rm -f "$round_verdict" "$round_record"
      stop_safely "registro-de-ronda-fallido" \
        "No se pudo construir el registro de convergencia de esta ronda; sin él la puerta del corrector no puede medir progreso y me detengo de forma segura."
    fi
    round_json="$(cat "$round_record")"
    rm -f "$round_verdict" "$round_record"

    marker="<!-- sirius-verdict:reviewer:changes:${head_sha}:${SIRIUS_ROUND_TAG} -->"
    body_file="$(mktemp)"
    {
      printf '%s\n\n%s\n' "$marker" "## CHANGES_REQUESTED"
      printf '- PR: %s\n' "$pr_hint"
      printf '%s\n\n%s\n\n## OBSERVACIONES_ESTRUCTURADAS\n```json\n%s\n```\n' "${summary}" "${readable}" "${observations}"
      printf '\n<!-- sirius-round:%s -->\n\n## RONDA_HALLAZGOS\n```json\n%s\n```\n' \
        "${round_number}" "${round_json}"
    } >"$body_file"
    if ! transition "$marker" "$body_file" "sirius:repair-requested" "FBCA04" "Evento consumible: corregir observaciones técnicas registradas"; then
      rm -f "$body_file"
      exit 1
    fi
    rm -f "$body_file"
    ;;

  BLOCKED_BY_DECISION)
    marker="<!-- sirius-verdict:${ROLE}:blocked:${SIRIUS_RUN_TAG} -->"
    body_file="$(mktemp)"
    printf '%s\n\n%s\n\n%s\n' "$marker" "🟡 **Necesito una decisión**" "${summary}" >"$body_file"
    if ! transition "$marker" "$body_file" "sirius:blocked-decision" "D4C5F9" "Estado: requiere una decisión humana"; then
      rm -f "$body_file"
      exit 1
    fi
    rm -f "$body_file"
    ;;

  FAILED_SAFELY | USAGE_LIMIT_REACHED)
    marker="<!-- sirius-verdict:${ROLE}:${verdict}:${SIRIUS_RUN_TAG} -->"
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
