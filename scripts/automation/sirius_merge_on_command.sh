#!/usr/bin/env bash
# Sirius — ejecutor de merge autorizado por comentario explícito del propietario.
#
# El contrato operativo (AUTOMATION_OPERATING_CONTRACT.md §8) exige que el
# merge permanezca bajo control humano. Este script no cambia esa regla: solo
# delega la EJECUCIÓN técnica del merge, para un trabajo concreto y ya
# aprobado, a la automatización, cuando el propietario del repositorio escribe
# la orden exacta "fusiona" en la incidencia que está en `sirius:ready-for-merge`.
# La autorización sigue siendo del usuario para ese merge concreto.
#
# El workflow que invoca este script ya filtró en el evento que el comentario
# proviene del propietario (`author_association == OWNER`) y que la incidencia
# tenía la etiqueta en el momento del evento. Este script vuelve a verificar
# todo por REST antes de actuar (protección contra condiciones de carrera) y
# comprueba, además:
#   - que la orden es EXACTAMENTE "fusiona" (sin texto adicional), para no
#     disparar el merge por una mención casual de la palabra;
#   - que hay una única PR asociada a la incidencia;
#   - que esa PR está abierta, no es borrador y no está ya fusionada;
#   - que no tiene conflictos con la rama base;
#   - que no ha recibido commits nuevos después del último Head/Merge SHA
#     aprobado mencionado en la incidencia (evita fusionar cambios sin revisar);
#   - que Quality está en verde sobre ese head exacto.
#
# Cualquier condición no cumplida detiene el merge y publica una explicación
# concreta en la incidencia (una sola vez por comentario, vía marcador). Este
# script nunca cierra la incidencia ni cambia sus etiquetas: eso lo hace
# `complete-sirius-after-merge.yml` cuando llega el evento de PR fusionada.
#
# Uso: sirius_merge_on_command.sh <owner/repo> <issue> <comment_id> <comment_body>

set -uo pipefail

SIRIUS_MERGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
# shellcheck source=scripts/automation/sirius_issue.sh
source "${SIRIUS_MERGE_DIR}/sirius_issue.sh"

REPO="${1:?uso: sirius_merge_on_command.sh <owner/repo> <issue> <comment_id> <comment_body>}"
ISSUE="${2:?uso: sirius_merge_on_command.sh <owner/repo> <issue> <comment_id> <comment_body>}"
COMMENT_ID="${3:?uso: sirius_merge_on_command.sh <owner/repo> <issue> <comment_id> <comment_body>}"
COMMENT_BODY="${4:-}"

block() {
  # block <explicacion> — publica el motivo una sola vez por comentario y detiene.
  local why="$1"
  local marker="<!-- sirius-merge-blocked:${COMMENT_ID} -->"
  echo "::error::Merge detenido para #${ISSUE} (comentario ${COMMENT_ID}): ${why}"
  local body_file
  body_file="$(mktemp)"
  printf '%s\n\n%s\n\n%s\n' \
    "$marker" \
    "🛑 **No he podido fusionar**" \
    "$why" >"$body_file"
  sirius_comment_once "$REPO" "$ISSUE" "$marker" "$body_file" \
    || echo "::warning::No se pudo publicar la explicacion del bloqueo en #${ISSUE}." >&2
  rm -f "$body_file"
}

# --- 1) La orden debe ser exactamente "fusiona" -------------------------------
# Se recorta antes la firma de atribución que algunas herramientas AÑADEN SOLAS
# al final de cada comentario: quien comenta por API no controla lo que el
# servidor le anexa, y sin esto la orden es inescribible por esa vía. Se recorta
# ese bloque y solo ese —desde una línea que sea únicamente guiones hasta el
# final—; cualquier otro texto sigue invalidando la orden, que es lo que esta
# guarda protege. La autorización sigue siendo del propietario: el workflow ya
# exigió `author_association == OWNER` y este guion lo reverifica por REST.
sin_firma="$(printf '%s' "$COMMENT_BODY" | tr -d '\r' \
  | sed -e '/^[[:space:]]*---[[:space:]]*$/,$d')"
trimmed="$(printf '%s' "$sin_firma" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
lowered="$(printf '%s' "$trimmed" | tr '[:upper:]' '[:lower:]')"
if [ "$lowered" != "fusiona" ]; then
  echo "El comentario de #${ISSUE} no es la orden exacta 'fusiona'; no se actua."
  exit 0
fi

# --- 2) Reverificacion autoritativa de la etiqueta (evita condiciones de carrera) ---
labels_now="$(sirius_retry gh api "repos/${REPO}/issues/${ISSUE}" --jq '.labels[].name')" || labels_now=""
if ! printf '%s\n' "$labels_now" | grep -Fxq "sirius:ready-for-merge"; then
  echo "#${ISSUE} ya no esta en sirius:ready-for-merge; no se actua."
  exit 0
fi

# --- 3) Una unica PR asociada --------------------------------------------------
# Ver la nota del contrato en `sirius_find_pr_for_issue`: salida 2 = no se pudo
# leer, y ese vacio no es una ausencia. Publicar "no hay PR" cuando lo que hubo
# fue un 503 manda al propietario a buscar un problema inexistente.
pr_list="$(mktemp)"
if ! sirius_find_pr_for_issue "$REPO" "$ISSUE" >"$pr_list"; then
  rm -f "$pr_list"
  echo "::error::No se pudo leer la incidencia #${ISSUE} para localizar su PR; no puedo distinguir que no haya ninguna de que no haya podido leerla. Reintentable."
  exit 1
fi
mapfile -t pr_numbers <"$pr_list"
rm -f "$pr_list"
if [ "${#pr_numbers[@]}" -eq 0 ]; then
  block "No he encontrado ninguna PR asociada a esta incidencia. Comprueba que el cuerpo o los comentarios referencien su URL completa."
  exit 1
fi
if [ "${#pr_numbers[@]}" -ne 1 ]; then
  list="$(printf '#%s, ' "${pr_numbers[@]}")"
  block "Esta incidencia referencia varias PR distintas (${list%, }); me detengo para no fusionar la equivocada."
  exit 1
fi
pr_number="${pr_numbers[0]}"

# --- 4) Estado de la PR ---------------------------------------------------------
pr_json="$(sirius_retry gh api "repos/${REPO}/pulls/${pr_number}" \
  --jq '{state: .state, draft: .draft, merged: .merged, mergeable_state: .mergeable_state, head: .head.sha}')" || pr_json=""
if [ -z "$pr_json" ]; then
  block "No he podido leer el estado de la PR #${pr_number}."
  exit 1
fi

if [ "$(printf '%s' "$pr_json" | jq -r '.merged')" = "true" ]; then
  echo "La PR #${pr_number} ya estaba fusionada; no se repite la accion."
  exit 0
fi

pr_state="$(printf '%s' "$pr_json" | jq -r '.state')"
pr_draft="$(printf '%s' "$pr_json" | jq -r '.draft')"
current_head="$(printf '%s' "$pr_json" | jq -r '.head')"
mergeable_state="$(printf '%s' "$pr_json" | jq -r '.mergeable_state')"

if [ "$pr_state" != "open" ] || [ "$pr_draft" = "true" ]; then
  block "La PR #${pr_number} no esta abierta y lista (estado \`${pr_state}\`, borrador \`${pr_draft}\`)."
  exit 1
fi
if [ "$mergeable_state" = "dirty" ]; then
  block "La PR #${pr_number} tiene conflictos con la rama base; resuélvelos antes de volver a escribir \`fusiona\`."
  exit 1
fi

# --- 5) Sin cambios posteriores a la ultima aprobacion conocida ----------------
scan_file="$(mktemp)"
sirius_scan_text "$REPO" "$ISSUE" "$scan_file"
approved_head="$(sirius_extract_sha "$scan_file")"
rm -f "$scan_file"

if [ "$approved_head" = "no-head" ]; then
  block "No encuentro ningun Head SHA aprobado registrado en esta incidencia; no puedo confirmar que la PR #${pr_number} sigue igual que cuando se revisó."
  exit 1
fi
if [ "$current_head" != "$approved_head" ]; then
  block "La PR #${pr_number} tiene commits posteriores a la ultima aprobacion registrada (\`${approved_head}\` -> \`${current_head}\`); necesita otra revisión antes de fusionar."
  exit 1
fi

# --- 6) Quality en verde sobre ese head exacto ---------------------------------
conclusion="$(sirius_retry gh api "repos/${REPO}/commits/${current_head}/check-runs" \
  --jq '[.check_runs[] | select(.name == "quality")] | (first.conclusion // "none")')" || conclusion="none"
if [ "$conclusion" != "success" ]; then
  block "Quality no esta en verde sobre \`${current_head}\` (resultado: \`${conclusion}\`); no puedo fusionar."
  exit 1
fi

# --- 7) Merge --------------------------------------------------------------------
# El merge se ejecuta con un token de identidad real (SIRIUS_TRIGGER_TOKEN) si
# está disponible: así el evento `pull_request` de "fusionada" no queda suprimido
# por la regla anti-recursión del GITHUB_TOKEN y dispara el cierre automático
# (`complete-sirius-after-merge.yml`), que pasa la incidencia a `sirius:completed`.
# Todas las verificaciones previas de este script siguen con GH_TOKEN. Si la
# variable no está definida, cae al GH_TOKEN vigente (comportamiento previo).
_sirius_do_merge() {
  (
    [ -n "${SIRIUS_TRIGGER_TOKEN:-}" ] && export GH_TOKEN="$SIRIUS_TRIGGER_TOKEN"
    gh pr merge "$pr_number" --repo "$REPO" --squash
  )
}
merge_err_file="$(mktemp)"
sirius_retry _sirius_do_merge >/dev/null 2>"$merge_err_file"
merge_err="$(cat "$merge_err_file" 2>/dev/null || true)"
rm -f "$merge_err_file"

# Verificacion autoritativa: el codigo de salida de `gh pr merge` no basta por
# si solo (un fallo tardio tras un exito real no debe reportarse como fallo).
merged_now="$(sirius_retry gh api "repos/${REPO}/pulls/${pr_number}" --jq '.merged' 2>/dev/null)" || merged_now=""
if [ "$merged_now" = "true" ]; then
  echo "PR #${pr_number} fusionada por orden de #${ISSUE} (comentario ${COMMENT_ID})."
  exit 0
fi

block "El comando de fusion fallo: ${merge_err:-sin detalle}"
exit 1
