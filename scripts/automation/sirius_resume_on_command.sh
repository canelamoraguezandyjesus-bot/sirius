#!/usr/bin/env bash
# Sirius — levantar una parada del ciclo con una orden explícita del propietario.
#
# La automatización sabe pararse: `sirius:blocked-decision` es lo que aplica la
# política de convergencia cuando el ciclo revisión-corrección deja de progresar
# (`sirius_convergence.py`). Esa parada es correcta y no se toca. Lo que faltaba
# era la vía de vuelta: una decisión humana no tenía por dónde ENTRAR.
#
# Sin ella, la parada es irreversible en la práctica. `decide()` mide sobre TODO
# el historial publicado, así que reponer la etiqueta disparadora vuelve a
# bloquear en el acto, y levantar la parada obliga a editar la incidencia a mano
# o a hacer el trabajo fuera del ciclo. Ocurrió en la #186: el propietario
# autorizó una ronda más y hubo que hacerla a mano, fuera de la automatización.
#
# Este script no relaja la política. Publica un marcador
# `<!-- sirius-convergence-reset:<head> -->` que `history_after_last_resume()`
# usa como frontera: las rondas anteriores siguen publicadas y auditables, pero
# dejan de servir de listón. Una parada por `sin-progreso` volverá a saltar en
# cuanto haya dos rondas planas POSTERIORES al marcador.
#
# Es el mismo patrón que `sirius_merge_on_command.sh` —orden exacta del
# propietario, reverificación autoritativa por REST, idempotencia por marcador—
# y por las mismas razones. El workflow que lo invoca ya filtró en el evento que
# el comentario viene del propietario (`author_association == OWNER`); aquí se
# vuelve a comprobar todo por REST, porque el evento describe el pasado y la
# decisión se toma sobre el presente.
#
# Uso: sirius_resume_on_command.sh <owner/repo> <issue> <comment_id> <comment_body>

set -uo pipefail

SIRIUS_RESUME_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
# shellcheck source=scripts/automation/sirius_issue.sh
source "${SIRIUS_RESUME_DIR}/sirius_issue.sh"

REPO="${1:?uso: sirius_resume_on_command.sh <owner/repo> <issue> <comment_id> <comment_body>}"
ISSUE="${2:?uso: sirius_resume_on_command.sh <owner/repo> <issue> <comment_id> <comment_body>}"
COMMENT_ID="${3:?uso: sirius_resume_on_command.sh <owner/repo> <issue> <comment_id> <comment_body>}"
COMMENT_BODY="${4:-}"

block() {
  # block <explicacion> — publica el motivo una sola vez por comentario y detiene.
  local why="$1"
  local marker="<!-- sirius-resume-blocked:${COMMENT_ID} -->"
  echo "::error::Reanudacion detenida para #${ISSUE} (comentario ${COMMENT_ID}): ${why}"
  local body_file
  body_file="$(mktemp)"
  printf '%s\n\n%s\n\n%s\n' \
    "$marker" \
    "🛑 **No he podido reanudar el ciclo**" \
    "$why" >"$body_file"
  sirius_comment_once "$REPO" "$ISSUE" "$marker" "$body_file" \
    || echo "::warning::No se pudo publicar la explicacion del bloqueo en #${ISSUE}." >&2
  rm -f "$body_file"
}

# --- 1) La orden debe ser exactamente "continua" ------------------------------
# Exacta y sin texto adicional, igual que `fusiona`: una mención casual de la
# palabra en una discusión no puede reanudar un ciclo que se detuvo por algo.
trimmed="$(printf '%s' "$COMMENT_BODY" | tr -d '\r' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
lowered="$(printf '%s' "$trimmed" | tr '[:upper:]' '[:lower:]')"
if [ "$lowered" != "continua" ] && [ "$lowered" != "continúa" ]; then
  echo "El comentario de #${ISSUE} no es la orden exacta 'continua'; no se actua."
  exit 0
fi

# --- 2) Reverificacion autoritativa del estado --------------------------------
# Un fallo de LECTURA no es "no esta bloqueada". Distinguirlos importa: tratar
# un 503 como ausencia de la etiqueta dejaría la orden del propietario tirada en
# silencio, que es el mismo callejon mudo que este script viene a eliminar.
if ! labels_now="$(sirius_retry gh api "repos/${REPO}/issues/${ISSUE}" --jq '.labels[].name')"; then
  echo "::error::No se pudieron leer las etiquetas de #${ISSUE}; no puedo distinguir una incidencia no bloqueada de un fallo de lectura. Reintentable."
  exit 1
fi
if ! printf '%s\n' "$labels_now" | grep -Fxq "sirius:blocked-decision"; then
  echo "#${ISSUE} no esta en sirius:blocked-decision; no se actua."
  exit 0
fi

# --- 3) Una unica PR asociada, y su head ---------------------------------------
# El marcador lleva el head para que quede escrito SOBRE QUÉ se autorizó
# continuar. Sin eso, un reset serviría para siempre y para cualquier commit
# posterior, que es justo lo que una autorización puntual no debe ser.
mapfile -t pr_numbers < <(sirius_find_pr_for_issue "$REPO" "$ISSUE")
if [ "${#pr_numbers[@]}" -eq 0 ]; then
  block "No he encontrado ninguna PR asociada a esta incidencia, así que no puedo saber sobre qué head autorizas continuar."
  exit 1
fi
if [ "${#pr_numbers[@]}" -ne 1 ]; then
  list="$(printf '#%s, ' "${pr_numbers[@]}")"
  block "Esta incidencia referencia varias PR distintas (${list%, }); me detengo para no reanudar sobre la equivocada."
  exit 1
fi
pr_number="${pr_numbers[0]}"

if ! pr_json="$(sirius_retry gh api "repos/${REPO}/pulls/${pr_number}" \
  --jq '{state: .state, merged: .merged, head: .head.sha}')"; then
  block "No he podido leer el estado de la PR #${pr_number}."
  exit 1
fi
if [ "$(printf '%s' "$pr_json" | jq -r '.merged')" = "true" ]; then
  block "La PR #${pr_number} ya está fusionada; no hay ciclo que reanudar."
  exit 1
fi
if [ "$(printf '%s' "$pr_json" | jq -r '.state')" != "open" ]; then
  block "La PR #${pr_number} no está abierta; no hay ciclo que reanudar."
  exit 1
fi
head_sha="$(printf '%s' "$pr_json" | jq -r '.head')"

# --- 4) El marcador de reset, ANTES de reponer la etiqueta ---------------------
# El orden importa y no es cosmético: si la etiqueta se aplicara primero, el
# corrector podría arrancar, leer un historial todavía sin marcador y volver a
# bloquear — y el propietario vería su orden rechazada por la misma parada que
# acababa de levantar. Se publica el permiso y solo después se abre la puerta.
marker="<!-- sirius-convergence-reset:${head_sha} -->"
body_file="$(mktemp)"
printf '%s\n\n%s\n\n%s\n\n%s\n' \
  "$marker" \
  "🟢 **Ciclo reanudado por orden del propietario**" \
  "Las rondas anteriores siguen publicadas y son auditables, pero dejan de contar como listón de convergencia. La medida vuelve a empezar desde aquí, sobre el head \`${head_sha}\`." \
  "Si el ciclo vuelve a estancarse —dos rondas consecutivas sin progreso a partir de este punto— se detendrá otra vez, con el mismo criterio." >"$body_file"
if ! sirius_comment_once "$REPO" "$ISSUE" "$marker" "$body_file"; then
  rm -f "$body_file"
  echo "::error::No se pudo publicar el marcador de reanudacion en #${ISSUE}; no repongo la etiqueta para no arrancar sin permiso escrito. Reintentable."
  exit 1
fi
rm -f "$body_file"

# --- 5) Reponer la etiqueta disparadora ----------------------------------------
# `sirius:repair-requested` es la que despierta al corrector, y es la que la
# parada retiró. La ESCRITURA va con el PAT si está disponible: un
# `issues: labeled` emitido con el GITHUB_TOKEN no dispara otros workflows
# (regla anti-recursión de GitHub), así que sin él la etiqueta se aplicaría y no
# despertaría a nadie — otra parada muda, la que este script existe para acabar.
if ! sirius_ensure_label "$REPO" "sirius:repair-requested" "1D76DB" \
  "Evento consumible: corregir las observaciones de la revisión"; then
  echo "::error::No se pudo asegurar la etiqueta sirius:repair-requested para #${ISSUE}; reintentable."
  exit 1
fi
if ! ( export GH_TOKEN="${SIRIUS_TRIGGER_TOKEN:-${GH_TOKEN:-}}"
       sirius_set_issue_labels "$REPO" "$ISSUE" "sirius:repair-requested" "sirius:blocked-decision" ); then
  echo "::error::No se pudo reponer sirius:repair-requested en #${ISSUE}; reintentable."
  exit 1
fi

echo "Ciclo de #${ISSUE} reanudado por orden del propietario sobre ${head_sha}."
