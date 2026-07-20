#!/usr/bin/env bash
# Sirius — reconciliador manual de estados de automatización.
#
# Detecta incidencias de trabajo atascadas y las repara SOLO cuando el estado
# correcto es inequívoco; todo lo demás se informa sin tocar nada. Diseñado para
# ejecutarse bajo demanda (workflow_dispatch): el contrato operativo prohíbe la
# vigilancia horaria como motor del flujo, así que este script no se programa.
#
# Casos que corrige (inequívocos):
#   A. Incidencia ABIERTA con marcador `<!-- sirius-completed:SHA -->` (no
#      ambiguo): la PR se fusionó y el cierre quedó a medias (incidencia #50).
#      -> garantiza `sirius:completed`, retira etiquetas transitorias y cierra.
#      No publica comentarios nuevos.
#   B. Incidencia en `sirius:ci-pending` cuya única PR abierta referenciada tiene
#      Quality en verde para su head actual: la transición de avance se perdió.
#      -> reintenta la transición estándar (idempotente, via sirius_transition).
#
# Casos que solo informa: eventos sin consumir, estados en curso, decisiones
# humanas pendientes, contradicciones de etiquetas y ci-pending sin CI verde.
#
# Nunca hace merge, nunca inicia bloques y nunca decide producto.
#
# Uso: sirius_reconcile.sh <owner/repo>

set -uo pipefail

SIRIUS_RECONCILE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
# shellcheck source=scripts/automation/sirius_issue.sh
source "${SIRIUS_RECONCILE_DIR}/sirius_issue.sh"

REPO="${1:?uso: sirius_reconcile.sh <owner/repo>}"

STATE_LABELS="sirius:planned sirius:implement-requested sirius:implementing sirius:ci-pending sirius:review-requested sirius:reviewing sirius:repair-requested sirius:repairing sirius:ready-for-merge sirius:blocked-decision sirius:failed-safely sirius:completed"
TRANSIENT_CSV="sirius:planned,sirius:implement-requested,sirius:implementing,sirius:ci-pending,sirius:review-requested,sirius:reviewing,sirius:repair-requested,sirius:repairing,sirius:ready-for-merge,sirius:blocked-decision,sirius:failed-safely"

report() {
  # report <nivel> <mensaje> — stdout + resumen del job si existe.
  echo "[$1] $2"
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    echo "- **$1** $2" >>"$GITHUB_STEP_SUMMARY"
  fi
}

overall_rc=0

# Incidencias abiertas (se excluyen PRs, que el endpoint /issues incluye).
mapfile -t open_issues < <(
  sirius_retry gh api -X GET "repos/${REPO}/issues" \
    -f state=open -f per_page=100 --paginate \
    --jq '.[] | select(has("pull_request") | not) | .number'
)

for issue in "${open_issues[@]:-}"; do
  [ -z "${issue:-}" ] && continue

  labels="$(sirius_retry gh api "repos/${REPO}/issues/${issue}/labels" --jq '.[].name' 2>/dev/null)" || {
    report AVISO "No se pudieron leer las etiquetas de #${issue}; se omite."
    continue
  }
  sirius_labels="$(printf '%s\n' "$labels" | grep '^sirius:' || true)"

  comments_file="$(mktemp)"
  body_file="$(mktemp)"
  sirius_read_issue_comments "$REPO" "$issue" >"$comments_file" 2>/dev/null || true
  sirius_read_issue_body "$REPO" "$issue" >"$body_file" 2>/dev/null || true

  completed_marker="$(grep -oE '<!-- sirius-completed:[0-9a-fA-F]{7,40} -->' "$comments_file" | head -n 1 || true)"

  # --- Caso A: fusionada y completada a medias (marcador sin cierre) ----------
  if [ -n "$completed_marker" ]; then
    report ATASCO "#${issue}: abierta con marcador de completado (${completed_marker}); se repara el cierre."
    fixed=1
    sirius_ensure_label "$REPO" "sirius:completed" "006B75" "Estado terminal: bloque fusionado y cerrado" || fixed=0
    if [ "$fixed" -eq 1 ]; then
      removes_arr=()
      IFS=',' read -r -a removes_arr <<<"$TRANSIENT_CSV"
      sirius_set_issue_labels "$REPO" "$issue" "sirius:completed" "${removes_arr[@]}" || fixed=0
    fi
    if [ "$fixed" -eq 1 ]; then
      sirius_close_issue "$REPO" "$issue" || fixed=0
    fi
    if [ "$fixed" -eq 1 ]; then
      report CORREGIDO "#${issue}: etiquetas saneadas y cerrada como completada (sin comentarios nuevos)."
    else
      report ERROR "#${issue}: no se pudo completar el cierre; reintentable."
      overall_rc=1
    fi
    rm -f "$comments_file" "$body_file"
    continue
  fi

  # --- Contradicción: más de una etiqueta de estado sirius -------------------
  state_count="$(printf '%s\n' "$sirius_labels" | grep -c . || true)"
  if [ "${state_count:-0}" -gt 1 ]; then
    report CONTRADICCION "#${issue}: varias etiquetas sirius simultáneas ($(printf '%s' "$sirius_labels" | tr '\n' ' ')); requiere revisión humana."
    rm -f "$comments_file" "$body_file"
    continue
  fi

  # --- Caso B: ci-pending con Quality ya resuelto -----------------------------
  if printf '%s\n' "$sirius_labels" | grep -Fxq "sirius:ci-pending"; then
    mapfile -t pr_urls < <(
      cat "$body_file" "$comments_file" \
        | grep -oE "https://github\.com/${REPO}/pull/[0-9]+" | sort -u
    )
    open_pr="" open_head=""
    for url in "${pr_urls[@]:-}"; do
      [ -z "${url:-}" ] && continue
      prnum="${url##*/}"
      prjson="$(sirius_retry gh api "repos/${REPO}/pulls/${prnum}" --jq '{state: .state, head: .head.sha}' 2>/dev/null)" || continue
      if [ "$(printf '%s' "$prjson" | jq -r '.state')" = "open" ]; then
        if [ -n "$open_pr" ]; then open_pr="AMBIGUA"; break; fi
        open_pr="$prnum"
        open_head="$(printf '%s' "$prjson" | jq -r '.head')"
      fi
    done
    if [ -z "$open_pr" ]; then
      report AVISO "#${issue}: ci-pending sin PR abierta referenciada; requiere revisión humana."
    elif [ "$open_pr" = "AMBIGUA" ]; then
      report CONTRADICCION "#${issue}: ci-pending con varias PR abiertas referenciadas; requiere revisión humana."
    else
      conclusion="$(sirius_retry gh api "repos/${REPO}/commits/${open_head}/check-runs" \
        --jq '[.check_runs[] | select(.name == "quality")] | (first.conclusion // "none")' 2>/dev/null)" || conclusion="none"
      if [ "$conclusion" = "success" ]; then
        report ATASCO "#${issue}: ci-pending pero Quality esta en verde para ${open_head}; se reintenta la transicion."
        marker="<!-- sirius-quality:${open_head}:success -->"
        tfile="$(mktemp)"
        printf '%s\n\n%s\n\n%s\n%s\n%s\n%s\n' \
          "$marker" \
          "## QUALITY_SUCCESS" \
          "- PR: https://github.com/${REPO}/pull/${open_pr}" \
          "- Head SHA: \`${open_head}\`" \
          "- Resultado: \`success\` (reconciliado)" \
          "- Siguiente transicion: revision independiente." >"$tfile"
        if sirius_transition "$REPO" "$issue" "$marker" "$tfile" \
          "sirius:review-requested" "8250DF" "Evento consumible: iniciar revisión independiente" \
          "noclose" "sirius:ci-pending"; then
          report CORREGIDO "#${issue}: transicion ci-pending -> review-requested reconciliada."
        else
          report ERROR "#${issue}: la transicion reconciliadora fallo; reintentable."
          overall_rc=1
        fi
        rm -f "$tfile"
      elif [ "$conclusion" = "none" ]; then
        report AVISO "#${issue}: ci-pending y Quality aun sin resultado para ${open_head}; nada que reconciliar."
      else
        report AVISO "#${issue}: ci-pending con Quality '${conclusion}' para ${open_head}; el workflow de avance debe gestionarlo (no se transiciona aqui)."
      fi
    fi
    rm -f "$comments_file" "$body_file"
    continue
  fi

  # --- Solo informe -----------------------------------------------------------
  for lbl in sirius:implement-requested sirius:review-requested sirius:repair-requested; do
    if printf '%s\n' "$sirius_labels" | grep -Fxq "$lbl"; then
      report PENDIENTE "#${issue}: evento ${lbl} sin consumir; comprobar la Routine externa correspondiente."
    fi
  done
  for lbl in sirius:implementing sirius:reviewing sirius:repairing; do
    if printf '%s\n' "$sirius_labels" | grep -Fxq "$lbl"; then
      report EN-CURSO "#${issue}: ${lbl}; verificar que la Routine sigue activa."
    fi
  done
  for lbl in sirius:blocked-decision sirius:failed-safely sirius:ready-for-merge; do
    if printf '%s\n' "$sirius_labels" | grep -Fxq "$lbl"; then
      report HUMANO "#${issue}: ${lbl}; espera una accion humana."
    fi
  done
  rm -f "$comments_file" "$body_file"
done

exit "$overall_rc"
