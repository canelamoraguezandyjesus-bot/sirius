#!/usr/bin/env bash
# Sirius — puerta de validación de activación (`sirius:implement-requested`).
#
# Motivación (incidencia #60): una incidencia se activó sin `sirius:planned` y,
# tras corregirlo a mano, volvió a detenerse porque su cuerpo estaba truncado.
# Cada parada segura de la Routine implementadora cuesta una ejecución externa y
# deja la incidencia en `sirius:failed-safely`. Esta puerta valida las
# precondiciones EN el repositorio, en cuanto se aplica la etiqueta de
# activación, y rechaza temprano con un diagnóstico preciso.
#
# Política (la más segura de las tres posibles):
#   - NO corrige automáticamente: añadir `sirius:planned` equivaldría a aprobar
#     planificación, decisión humana por contrato.
#   - NO se detiene en `failed-safely`: la incidencia no ha fallado; la
#     activación era inválida. Se retira solo el evento.
#   - RECHAZA ANTES: retira `sirius:implement-requested`, conserva el resto de
#     etiquetas tal cual y explica exactamente qué falta, mencionando al
#     propietario una sola vez.
#
# La Routine implementadora conserva sus propias comprobaciones (defensa en
# profundidad): esta puerta no puede garantizar ejecutarse antes que ella, solo
# reducir la ventana y dejar el estado limpio y reintentable.
#
# Comprobaciones (en orden): incidencia abierta y no PR; `sirius:planned`
# presente; sin otros estados sirius activos/terminales; cuerpo estructuralmente
# completo (todas las secciones obligatorias del contrato).
#
# Idempotencia: el comentario de rechazo lleva un marcador por motivo
# (`<!-- sirius-activation:rejected:<motivo> -->`); repetir el mismo error no
# duplica el comentario (solo se retira la etiqueta de nuevo). Un motivo
# distinto sí genera un comentario nuevo.
#
# Uso: sirius_validate_activation.sh <owner/repo> <numero-incidencia>

set -uo pipefail

SIRIUS_GATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
# shellcheck source=scripts/automation/sirius_issue.sh
source "${SIRIUS_GATE_DIR}/sirius_issue.sh"

REPO="${1:?uso: sirius_validate_activation.sh <owner/repo> <issue>}"
ISSUE="${2:?uso: sirius_validate_activation.sh <owner/repo> <issue>}"
OWNER_LOGIN="${REPOSITORY_OWNER:-${REPO%%/*}}"

# Estados sirius incompatibles con una activación nueva (todo salvo planned y el
# propio evento). failed-safely incluido: exige revisar el diagnóstico y
# retirarla conscientemente antes de reactivar.
INCOMPATIBLE_STATES="sirius:implementing sirius:ci-pending sirius:review-requested sirius:reviewing sirius:repair-requested sirius:repairing sirius:ready-for-merge sirius:blocked-decision sirius:failed-safely sirius:completed"

reject() {
  # reject <motivo-slug> <explicacion> <accion>
  local reason="$1" why="$2" action="$3"
  local marker="<!-- sirius-activation:rejected:${reason} -->"
  echo "::warning::Activacion invalida de #${ISSUE} (${reason}); se retira sirius:implement-requested."
  local body_file
  body_file="$(mktemp)"
  printf '%s\n\n%s\n\n%s\n\n%s\n\n%s\n' \
    "$marker" \
    "⛔ **Activación rechazada** (\`${reason}\`)" \
    "$why" \
    "**Siguiente acción:** ${action} Después, vuelve a aplicar \`sirius:implement-requested\`." \
    "@${OWNER_LOGIN}" >"$body_file"
  local rc=0
  if ! sirius_comment_once "$REPO" "$ISSUE" "$marker" "$body_file"; then
    # Sin diagnostico NO se retira la etiqueta. Retirarla igualmente dejaba la
    # incidencia solo en `sirius:planned`, sin comentario y sin ningun evento
    # que la reviva: un callejon MUDO, y encima invisible para el reconciliador,
    # porque `planned` es un estado de reposo legitimo y no esta en
    # MACHINE_LABELS. Es exactamente la clase de fallo que la incidencia #138
    # vino a eliminar, reintroducida por la puerta que debia protegerla.
    #
    # Conservandola, el estado queda como estaba: se pierde tiempo, no se pierde
    # la incidencia. Y no hay bucle, porque `issues: labeled` solo dispara al
    # APLICAR la etiqueta.
    #
    # Lo que esto NO significa, y conviene no leer de mas: que el reconciliador
    # vaya a avisar. Solo lo hara en el camino `sin-planned`, donde queda
    # `planned` + `implement-requested`, que es el par que el reconciliador
    # reconoce. En `estado-incompatible` o `cuerpo-incompleto` la incidencia
    # queda con otras etiquetas y hace falta que una persona la mire.
    # Hallazgo P2 de Codex en la PR #146.
    echo "::error::No se pudo publicar el comentario de rechazo en #${ISSUE}; se CONSERVA sirius:implement-requested para no dejar la incidencia muda." >&2
    rm -f "$body_file"
    return 1
  fi
  rm -f "$body_file"
  # Retirar el evento y verificar que quedo retirado (estado limpio, reintentable).
  sirius_retry gh issue edit "$ISSUE" --repo "$REPO" --remove-label "sirius:implement-requested" >/dev/null 2>&1 || true
  local labels_now=""
  if ! labels_now="$(sirius_retry gh api "repos/${REPO}/issues/${ISSUE}" --jq '.labels[].name')"; then
    echo "::error::No se pudo verificar la retirada del evento en #${ISSUE}; reintentable." >&2
    return 1
  fi
  if printf '%s\n' "$labels_now" | grep -Fxq "sirius:implement-requested"; then
    echo "::error::sirius:implement-requested sigue presente en #${ISSUE}; reintentable." >&2
    return 1
  fi
  return "$rc"
}

# --- 1) Incidencia abierta y no PR --------------------------------------------
issue_json="$(sirius_retry gh api "repos/${REPO}/issues/${ISSUE}" --jq '{state: .state, is_pr: (has("pull_request"))}')"
if [ -z "${issue_json:-}" ]; then
  echo "::warning::No se pudo leer #${ISSUE}; no se valida (la Routine mantiene sus propias comprobaciones)."
  exit 0
fi
if [ "$(printf '%s' "$issue_json" | jq -r '.is_pr')" = "true" ]; then
  echo "#${ISSUE} es una PR; la activacion no aplica."
  exit 0
fi
if [ "$(printf '%s' "$issue_json" | jq -r '.state')" != "open" ]; then
  reject "incidencia-cerrada" \
    "La incidencia no está abierta: no puede activarse una implementación sobre un trabajo cerrado." \
    "Reabre la incidencia solo si el trabajo sigue vigente." || exit 1
  exit 0
fi

# --- 2) Etiquetas: planned presente y sin estados incompatibles ----------------
labels="$(sirius_retry gh api "repos/${REPO}/issues/${ISSUE}" --jq '.labels[].name')" || {
  echo "::warning::No se pudieron leer las etiquetas de #${ISSUE}; no se valida."
  exit 0
}

conflict=""
for st in $INCOMPATIBLE_STATES; do
  if printf '%s\n' "$labels" | grep -Fxq "$st"; then conflict="$st"; break; fi
done
if [ -n "$conflict" ]; then
  reject "estado-incompatible" \
    "La incidencia ya está en \`${conflict}\`: activarla de nuevo duplicaría trabajo o pisaría un estado que requiere otra acción (revisar un diagnóstico, esperar una decisión o cerrar un ciclo)." \
    "Resuelve primero el estado \`${conflict}\` (retíralo conscientemente si ya no aplica)." || exit 1
  exit 0
fi

if ! printf '%s\n' "$labels" | grep -Fxq "sirius:planned"; then
  reject "sin-planned" \
    "Falta \`sirius:planned\`. Esa etiqueta certifica que el alcance está definido y aprobado; ninguna automatización puede añadirla por ti." \
    "Confirma que el alcance está realmente aprobado y aplica \`sirius:planned\`." || exit 1
  exit 0
fi

# --- 3) Cuerpo estructuralmente completo ---------------------------------------
body_file="$(mktemp)"
if ! sirius_read_issue_body "$REPO" "$ISSUE" >"$body_file"; then
  rm -f "$body_file"
  echo "::warning::No se pudo leer el cuerpo de #${ISSUE}; no se valida."
  exit 0
fi
if ! missing="$(python3 "${SIRIUS_GATE_DIR}/validate_issue_body.py" "$body_file" 2>&1)"; then
  rm -f "$body_file"
  reject "cuerpo-incompleto" \
    "El cuerpo de la incidencia está truncado o incompleto. Detalle del validador: ${missing}" \
    "Edita el cuerpo hasta que contenga todas las secciones obligatorias del contrato (compara con una incidencia completa como #55)." || exit 1
  exit 0
fi
rm -f "$body_file"

echo "Activacion valida de #${ISSUE}: abierta, sirius:planned presente, sin estados incompatibles y cuerpo completo."
exit 0
