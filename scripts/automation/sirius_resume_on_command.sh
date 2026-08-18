#!/usr/bin/env bash
# Sirius — levantar una parada del ciclo con una orden explícita del propietario.
#
# La automatización sabe pararse de dos maneras: `sirius:blocked-decision`, que
# aplica la política de convergencia cuando el ciclo revisión-corrección deja de
# progresar (`sirius_convergence.py`), y `sirius:failed-safely`, que aplica
# cualquier rol cuando su fase no pudo terminar. Las dos paradas son correctas y
# no se tocan. Lo que faltaba era la vía de vuelta: una decisión humana no tenía
# por dónde ENTRAR, y sin ella la parada es irreversible en la práctica.
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

# Las paradas que una orden del propietario sabe levantar.
#
# ADR-030 dio salida a `sirius:blocked-decision` y dejó fuera
# `sirius:failed-safely` con este razonamiento: «su salida está documentada en
# sirius_validate_activation.sh y consiste en retirar la etiqueta tras leer el
# diagnóstico». Ese razonamiento era FALSO, y la #193 lo demostró: esa línea
# habla de reactivar el trabajo DESDE CERO con `sirius:implement-requested`, no
# de retomar la ronda interrumpida; y ningún workflow escucha `unlabeled`, así
# que retirar la etiqueta no dispara absolutamente nada. Una parada segura sobre
# una PR con Quality en verde y tres rondas de trabajo acumulado no tenía
# ninguna vía de vuelta que no fuese cirugía manual.
SIRIUS_PARADAS_REANUDABLES="sirius:blocked-decision sirius:failed-safely"

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
parada=""
for etiqueta in $SIRIUS_PARADAS_REANUDABLES; do
  if printf '%s\n' "$labels_now" | grep -Fxq "$etiqueta"; then
    parada="$etiqueta"
    break
  fi
done
if [ -z "$parada" ]; then
  echo "#${ISSUE} no esta en ninguna parada reanudable (${SIRIUS_PARADAS_REANUDABLES}); no se actua."
  exit 0
fi

# --- 3) Una unica PR asociada, y su head ---------------------------------------
# El marcador lleva el head para que quede escrito SOBRE QUÉ se autorizó
# continuar. Sin eso, un reset serviría para siempre y para cualquier commit
# posterior, que es justo lo que una autorización puntual no debe ser.
# El codigo de salida importa tanto como la salida: 2 significa que NO se pudo
# leer, y entonces el vacio no dice nada. Con `< <(...)` ese codigo se perdia y
# un 503 se publicaba como "no hay ninguna PR".
pr_list="$(mktemp)"
if ! sirius_find_pr_for_issue "$REPO" "$ISSUE" >"$pr_list"; then
  rm -f "$pr_list"
  echo "::error::No se pudo leer la incidencia #${ISSUE} para localizar su PR; no puedo distinguir que no haya ninguna de que no haya podido leerla. Reintentable."
  exit 1
fi
mapfile -t pr_numbers <"$pr_list"
rm -f "$pr_list"
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

# --- 3bis) A qué fase se vuelve --------------------------------------------
# Reanudar es reponer el EVENTO que la parada consumió, no elegir una etiqueta
# bonita. Cada rol tiene exactamente un disparador, y `sirius_apply_verdict.sh`
# ya fija la correspondencia rol->fase en curso (implementer/reviewer/corrector
# -> implementing/reviewing/repairing); aquí se repone el disparador hermano.
#
# `sirius:blocked-decision` solo lo emite la política de convergencia, que
# siempre para al corrector: su vuelta es fija. `sirius:failed-safely` lo puede
# emitir cualquiera de los tres, así que la fase se LEE del historial publicado
# —el marcador del veredicto lleva el rol— en vez de suponerla.
destino_de_rol() {
  case "$1" in
    implementer) printf 'sirius:implement-requested\n' ;;
    reviewer) printf 'sirius:review-requested\n' ;;
    corrector) printf 'sirius:repair-requested\n' ;;
    *) return 1 ;;
  esac
}

case "$parada" in
  sirius:blocked-decision)
    etiqueta_destino="sirius:repair-requested"
    ;;
  sirius:failed-safely)
    dump_file="$(mktemp)"
    # Un fallo de LECTURA no es "no hay parada registrada". Sin historial no se
    # puede saber qué fase se detuvo, y adivinarla reanudaría la equivocada.
    if ! sirius_dump_comments "$REPO" "$ISSUE" "$dump_file"; then
      rm -f "$dump_file"
      echo "::error::No se pudieron leer los comentarios de #${ISSUE}; no puedo saber que fase se detuvo. Reintentable."
      exit 1
    fi
    # Las dos formas que publica una parada segura: el veredicto FAILED_SAFELY
    # del rol y las paradas `precheck` del propio guion. En ambas el rol es el
    # segundo campo. Se toma la ultima, que es la parada vigente.
    rol_parado="$(grep -oE '<!-- sirius-verdict:(implementer|reviewer|corrector):(FAILED_SAFELY|precheck):' \
      "$dump_file" | tail -n 1 | cut -d: -f2)"
    rm -f "$dump_file"
    if ! etiqueta_destino="$(destino_de_rol "$rol_parado")"; then
      block "La incidencia esta en \`sirius:failed-safely\` pero no encuentro publicado que fase se detuvo, asi que no se a cual devolverla. Aplica a mano la etiqueta de la fase que quieras repetir."
      exit 1
    fi
    ;;
  *)
    echo "::error::Parada '${parada}' sin vuelta declarada; esto es un defecto de este guion."
    exit 1
    ;;
esac

# --- 4) El permiso escrito, ANTES de reponer la etiqueta ----------------------
# El orden importa y no es cosmético: si la etiqueta se aplicara primero, el
# corrector podría arrancar, leer un historial todavía sin marcador y volver a
# bloquear — y el propietario vería su orden rechazada por la misma parada que
# acababa de levantar. Se publica el permiso y solo después se abre la puerta.
#
# El marcador NO es el mismo para las dos paradas, y confundirlos sería grave.
# `sirius-convergence-reset` mueve el listón de la política de convergencia:
# vale para `blocked-decision`, que es precisamente una parada por falta de
# progreso. Publicarlo en un `failed-safely` borraría el listón sin que nadie
# lo hubiera pedido, y un ciclo de verdad estancado podría correr para siempre.
# Una parada operativa no tiene rondas que perdonar: solo hay que repetir la
# fase que se cayó.
body_file="$(mktemp)"
if [ "$parada" = "sirius:blocked-decision" ]; then
  marker="<!-- sirius-convergence-reset:${head_sha} -->"
  printf '%s\n\n%s\n\n%s\n\n%s\n' \
    "$marker" \
    "🟢 **Ciclo reanudado por orden del propietario**" \
    "Las rondas anteriores siguen publicadas y son auditables, pero dejan de contar como listón de convergencia. La medida vuelve a empezar desde aquí, sobre el head \`${head_sha}\`." \
    "Si el ciclo vuelve a estancarse —dos rondas consecutivas sin progreso a partir de este punto— se detendrá otra vez, con el mismo criterio." >"$body_file"
else
  marker="<!-- sirius-resume-stop:${head_sha} -->"
  printf '%s\n\n%s\n\n%s\n\n%s\n' \
    "$marker" \
    "🟢 **Parada segura levantada por orden del propietario**" \
    "Se repite la fase que se detuvo (\`${etiqueta_destino}\`) sobre el head \`${head_sha}\`. El historial de rondas queda intacto: esta reanudación **no** perdona ninguna ronda ni mueve el listón de convergencia." \
    "Si la fase se vuelve a caer, se detendrá otra vez con su diagnóstico." >"$body_file"
fi
if ! sirius_comment_once "$REPO" "$ISSUE" "$marker" "$body_file"; then
  rm -f "$body_file"
  echo "::error::No se pudo publicar el marcador de reanudacion en #${ISSUE}; no repongo la etiqueta para no arrancar sin permiso escrito. Reintentable."
  exit 1
fi
rm -f "$body_file"

# --- 5) Reponer la etiqueta disparadora ----------------------------------------
# La etiqueta de destino es el disparador de la fase que se detuvo, y es la que
# la parada retiró. La ESCRITURA va con el PAT si está disponible: un
# `issues: labeled` emitido con el GITHUB_TOKEN no dispara otros workflows
# (regla anti-recursión de GitHub), así que sin él la etiqueta se aplicaría y no
# despertaría a nadie — otra parada muda, la que este script existe para acabar.
if ! sirius_ensure_label "$REPO" "$etiqueta_destino" "1D76DB" \
  "Evento consumible: repuesto por orden del propietario"; then
  echo "::error::No se pudo asegurar la etiqueta ${etiqueta_destino} para #${ISSUE}; reintentable."
  exit 1
fi
if ! ( export GH_TOKEN="${SIRIUS_TRIGGER_TOKEN:-${GH_TOKEN:-}}"
       sirius_set_issue_labels "$REPO" "$ISSUE" "$etiqueta_destino" "$parada" ); then
  echo "::error::No se pudo reponer ${etiqueta_destino} en #${ISSUE}; reintentable."
  exit 1
fi

echo "Parada ${parada} de #${ISSUE} levantada por orden del propietario: repuesta ${etiqueta_destino} sobre ${head_sha}."
