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

# Identificador único de esta ejecución. Los veredictos de parada (FAILED_SAFELY,
# BLOCKED_BY_DECISION y las paradas precheck de este script) llevaban antes un
# marcador fijo por rol; dos paradas seguidas compartían marcador y la segunda
# se dedupaba, ocultando su motivo (incidencia observada en el piloto sobre #66).
# Con este sufijo cada parada publica su propio comentario con su diagnóstico,
# sin perder la idempotencia dentro del mismo INTENTO. El alcance importa y es
# estrecho: SIRIUS_RUN_TAG incluye GITHUB_RUN_ATTEMPT, así que solo dedupa entre
# invocaciones que conservan run E intento. Reejecutar el workflow incrementa el
# intento, cambia el marcador y publica una parada nueva; eso es deliberado
# —cada reejecución merece su propio diagnóstico— y es justamente el motivo de
# que el registro de convergencia necesite OTRO sufijo, sin el intento (ver
# SIRIUS_ROUND_TAG, debajo). De los veredictos de avance,
# READY_FOR_REVIEW, FIXED y REVIEW_APPROVED van anclados SOLO al head SHA, que
# ya los hace únicos y estables.
#
# CHANGES_REQUESTED es la excepción y no debe alinearse con ellos «por
# coherencia»: su marcador es head + run (ver SIRIUS_ROUND_TAG, justo debajo).
# Arrastra el registro de convergencia, así que anclarlo solo al head o al
# contenido haría que dos rondas con los mismos hallazgos sobre el mismo head se
# dedupasen, congelando el historial justo en el escenario de estancamiento que
# la política de convergencia existe para detectar.
SIRIUS_RUN_TAG="${GITHUB_RUN_ID:-manual}-${GITHUB_RUN_ATTEMPT:-1}"

# Identificador de RONDA (sin el número de reintento). El marcador de
# CHANGES_REQUESTED arrastra el registro de convergencia, y ese registro debe
# publicarse UNA sola vez por ronda: con el sufijo por intento, reejecutar el
# mismo run de Actions (attempt 2) generaba un marcador distinto, no dedupaba y
# publicaba un SEGUNDO registro con el mismo head. La ronda siguiente veía dos
# registros consecutivos sobre el mismo head y bloqueaba por `head-sin-avance`
# un trabajo que sí había avanzado. Con el run como identificador, una
# reejecución es idempotente y una ronda nueva —que siempre es un run nuevo—
# sigue registrándose por separado.
SIRIUS_ROUND_TAG="${GITHUB_RUN_ID:-manual}"

# sanitize_untrusted_text / sanitize_untrusted_json viven en sirius_issue.sh
# (este script la carga arriba). Se movieron alli porque tambien los necesita
# quien publica texto de agente FUERA de este script: el informe del Auditor
# (ADR-016) sale como github-actions[bot], que esta dentro del filtro de
# confianza, y sin este saneado gobernaria rondas y observaciones.

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
  # El diagnóstico NO es texto de confianza: varias llamadas interpolan valores
  # crudos del veredicto (`.verdict` cuando no está en el conjunto permitido,
  # `.reviewed_head_sha` cuando no resuelve al head). Este comentario lo publica
  # la automatización, así que cae del lado confiable del filtro de autor y lo
  # leen después los escáneres deterministas: sin sanear, un marcador colado en
  # esos valores se contaba como ronda o como resultado de Quality. Se sanea en
  # este único punto, que es por donde pasan todas las paradas.
  why="$(printf '%s' "$why" | sanitize_untrusted_text)"
  local marker="<!-- sirius-verdict:${ROLE}:precheck:${reason}:${SIRIUS_RUN_TAG} -->"
  local body_file
  body_file="$(mktemp)"
  printf '%s\n\n%s\n\n%s\n' \
    "$marker" \
    "🔴 **Me he detenido de forma segura**" \
    "$why" >"$body_file"
  # Enlace al job (incidencia #135). Una parada que solo dice "no escribió
  # veredicto" obliga a buscar a mano dónde mirar. Esto es un HECHO, no una
  # medida: no se calcula ni se interpreta nada, así que no puede ser falso.
  #
  # Hubo un intento anterior de publicar aquí un diagnóstico medido —commits
  # nuevos, si el head avanzó, estado del árbol—. Se retiró: cinco rondas de
  # revisión encontraron siete defectos en él, TODOS de la misma familia (una
  # afirmación que el dato no sostenía), y además podía volver rojo el job que
  # venía a diagnosticar. Un diagnóstico al que se le cree tiene que decir solo
  # lo que sostiene, y aquí lo único que se sostiene sin medir es dónde mirar.
  if [ -n "${GITHUB_RUN_ID:-}" ] && [ -n "${GITHUB_REPOSITORY:-}" ]; then
    # El intento forma parte de la dirección; no es un adorno. `/actions/runs/ID`
    # resuelve SIEMPRE al último intento, y SIRIUS_RUN_TAG incluye el intento a
    # propósito para que cada reejecución publique su propia parada. Sin
    # `/attempts/N`, la parada del intento 1 enlazaría al registro del intento 2:
    # un enlace que promete «esta ejecución» y entrega otra. Es exactamente el
    # defecto que retiró al diagnóstico medido —afirmar más de lo que el dato
    # sostiene— y aquí se evita sin medir nada, componiendo la dirección con los
    # identificadores que Actions ya da por ciertos.
    local run_url="${GITHUB_SERVER_URL:-https://github.com}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"
    if [ -n "${GITHUB_RUN_ATTEMPT:-}" ]; then
      run_url="${run_url}/attempts/${GITHUB_RUN_ATTEMPT}"
    fi
    # «Ejecución», no «job»: la dirección apunta al run, que puede contener
    # varios jobs. Decir «job» ya sería afirmar de más.
    printf '\n- Registro de esta ejecución: %s\n' "$run_url" >>"$body_file"
  fi

  if ! transition "$marker" "$body_file" "sirius:failed-safely" "D93F0B" \
    "Estado temporal: fallo operativo detenido de forma segura"; then
    # La transición verificada se niega a actuar cuando no puede leer el
    # historial: sin lectura no hay deduplicación, y mutar a ciegas es lo que
    # 6e02b30 cerró. Pero perder el diagnóstico de una parada segura es peor que
    # arriesgar un duplicado, así que aquí se aplica el estado y se publica el
    # aviso por la vía directa.
    #
    # El duplicado es un riesgo REAL dentro de UNA SOLA ejecución, y conviene no
    # minimizarlo: el POST de `gh issue comment` no es idempotente y
    # `sirius_retry` lo repite, así que un resultado ambiguo —GitHub acepta la
    # petición y la respuesta se pierde— ya deja una copia publicada; si además
    # se agotan los reintentos, `sirius_comment_once` devuelve fallo y esta vía
    # publica otra. El marcador acota las ejecuciones DISTINTAS; no elimina los
    # resultados ambiguos del POST.
    #
    # Es tolerable para ESTE marcador porque no lo cuenta ninguna medida:
    # `parse_round_records` exige `<!-- sirius-round:N -->` con su bloque
    # `## RONDA_HALLAZGOS` y `ci_failure_streak` exige marcadores
    # `sirius-quality:`. Un aviso `precheck` repetido es ruido en la incidencia,
    # no puede falsear la convergencia ni la racha de CI, y perder el
    # diagnóstico sí sería un fallo silencioso. NO se generalice a los registros
    # de ronda, donde publicar sin deduplicar sí falsearía la medida.
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

# --- 1) El veredicto debe existir y ser JSON válido con "verdict" -------------
if [ ! -s "$VERDICT_FILE" ]; then
  stop_safely "sin-veredicto" \
    "El rol \`${ROLE}\` no escribió ningún veredicto. Sin un resultado estructurado no puedo saber en qué quedó el trabajo."
fi
if ! verdict="$(jq -r '.verdict // empty' "$VERDICT_FILE" 2>/dev/null)" || [ -z "$verdict" ]; then
  stop_safely "veredicto-invalido" \
    "El archivo de veredicto del rol \`${ROLE}\` no es JSON válido o no tiene el campo \`verdict\`."
fi

summary="$(jq -r '.summary // "(sin resumen)"' "$VERDICT_FILE" 2>/dev/null | sanitize_untrusted_text)"

case "$ROLE" in
  implementer) allowed="READY_FOR_REVIEW BLOCKED_BY_DECISION FAILED_SAFELY USAGE_LIMIT_REACHED" ;;
  reviewer) allowed="REVIEW_APPROVED CHANGES_REQUESTED BLOCKED_BY_DECISION FAILED_SAFELY" ;;
  corrector) allowed="FIXED CHECKS_UNRELATED BLOCKED_BY_DECISION FAILED_SAFELY" ;;
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
  # Salida 2 = no se pudo leer. Sin esto, un 503 se convertia en `sin-pr`, que
  # es una AFIRMACION sobre la incidencia y ademas la manda a parada segura con
  # un diagnostico falso. `historial-ilegible` dice lo que de verdad paso.
  local pr_list
  pr_list="$(mktemp)"
  if ! sirius_find_pr_for_issue "$REPO" "$ISSUE" >"$pr_list"; then
    rm -f "$pr_list"
    printf 'FAIL\thistorial-ilegible\tNo he podido leer la incidencia para localizar su PR, asi que no puedo distinguir que no haya ninguna de que no haya podido leerla. Reintentable.\n'
    return 0
  fi
  mapfile -t pr_numbers <"$pr_list"
  rm -f "$pr_list"
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

# resolve_pr — SIN argumentos: opera sobre globales, no sobre parámetros. Lee
# `verdict` (a través de locate_verified_pr, que lo usa en sus mensajes) y deja
# escritos `pr_number` y `head_sha`. Ejecuta locate_verified_pr y aplica
# stop_safely si falló (esto sí corre en el shell principal, no en la subshell).
# Termina el script si falla.
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

# sha_matches <sha-completo> <candidato> — 0 solo si el candidato resuelve sin
# ambigüedad al SHA completo: igual, o una abreviatura hexadecimal de al menos
# 7 caracteres que sea prefijo exacto. Nunca acepta cadenas vacías o no hex.
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

# require_reviewed_head — endurecimiento de la revisión (contrato §4.1):
# cualquier resultado de revisión (aprobación O cambios solicitados) debe
# demostrar sobre qué versión se pronunció. Exige que el JSON declare
# `reviewed_head_sha`, que coincida con el head actual de la PR (pr_number/
# head_sha ya resueltos por resolve_pr) y que ese head siga siendo el último
# que superó Quality según la incidencia. Si cualquiera de los tres difiere,
# parada segura: nunca se aplica un veredicto sobre una versión distinta.
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

  CHECKS_UNRELATED)
    # El corrector comprobó y el fallo de Quality no es atribuible a su trabajo.
    #
    # Hasta ahora no existía forma de decir eso. El corrector solo tenía `FIXED`
    # —que presupone un push—, así que emitirlo sin empujar dejaba la incidencia
    # en `ci-pending` esperando un evento `pull_request` que nadie iba a emitir:
    # sin push no hay evento, sin evento no hay Quality, y `ci-pending` no avisa
    # a nadie. Ocurrió dos veces el mismo día, con dos pruebas inestables
    # distintas (Qt en la #186, SQLite en la PR #191).
    #
    # Las tres condiciones de abajo NO son ceremonia: son lo que distingue este
    # veredicto de una excusa. Sin ellas, `CHECKS_UNRELATED` sería una forma de
    # esquivar una construcción rota reejecutándola indefinidamente.
    resolve_pr
    scan_file="$(mktemp)"
    sirius_scan_text "$REPO" "$ISSUE" "$scan_file"

    # (a) Tiene que haber un fallo de Quality registrado PARA ESTE head. Si el
    # corrector fue despertado por observaciones de revisión y no por CI, este
    # veredicto no describe nada real.
    if ! grep -qiE "<!--[[:space:]]*sirius-quality:${head_sha}:(failure|timed_out)[[:space:]]*-->" "$scan_file"; then
      rm -f "$scan_file"
      stop_safely "sin-fallo-de-ci-que-atribuir" \
        "El veredicto es \`CHECKS_UNRELATED\`, pero no hay ningún fallo de Quality registrado para el head actual (\`${head_sha}\`). Ese veredicto solo tiene sentido cuando la ronda la disparó un \`CI_FAILURE\`."
    fi

    # (b) Una sola reejecución por head. Si el fallo se repite sobre el MISMO
    # commit ya no es intermitencia: es reproducible, y reintentar deja de ser
    # diagnóstico para convertirse en un bucle. La cota vive aquí, en el dato
    # publicado, y no en una variable del proceso: el corrector es otro proceso
    # en cada ronda y no recuerda nada.
    if grep -qF "<!-- sirius-verdict:corrector:CHECKS_UNRELATED:${head_sha} -->" "$scan_file"; then
      rm -f "$scan_file"
      stop_safely "ci-ajeno-reincidente" \
        "Ya se reejecutaron las comprobaciones una vez para el head \`${head_sha}\` por considerarlas ajenas, y han vuelto a fallar sobre el mismo commit. Eso no es intermitencia: es reproducible. Se requiere una decisión humana."
    fi

    # (c) El identificador del run que hay que reejecutar sale del propio
    # comentario `CI_FAILURE`, que ya lo publica. Se toma el más reciente porque
    # `sirius_scan_text` entrega los comentarios del más nuevo al más antiguo.
    rerun_id="$(grep -oE "actions/runs/[0-9]+" "$scan_file" | head -n 1 | grep -oE "[0-9]+" || true)"
    rm -f "$scan_file"
    if [ -z "$rerun_id" ]; then
      stop_safely "sin-run-que-reejecutar" \
        "El veredicto es \`CHECKS_UNRELATED\` pero no he encontrado en la incidencia el identificador del run de Quality que habría que reejecutar. Me detengo en vez de dejar la incidencia esperando un evento que nadie va a emitir."
    fi

    # La reejecución va con el token de esta invocación, que es el PAT: un
    # `workflow_run` emitido a partir del GITHUB_TOKEN no despertaría a
    # `advance-sirius-after-quality.yml` (regla anti-recursión de GitHub) y la
    # incidencia se quedaría igual de muda que sin este veredicto.
    if ! sirius_retry gh api -X POST "repos/${REPO}/actions/runs/${rerun_id}/rerun-failed-jobs" >/dev/null; then
      stop_safely "reejecucion-fallida" \
        "No he podido reejecutar los trabajos fallidos del run \`${rerun_id}\`. Me detengo en vez de dejar la incidencia esperando un resultado que no va a llegar."
    fi

    pr_url="https://github.com/${REPO}/pull/${pr_number}"
    marker="<!-- sirius-verdict:corrector:CHECKS_UNRELATED:${head_sha} -->"
    body_file="$(mktemp)"
    printf '%s\n\n%s\n\n%s\n%s\n%s\n\n%s\n\n%s\n' \
      "$marker" \
      "## COMPROBACIONES_REEJECUTADAS" \
      "- PR: ${pr_url}" \
      "- Head SHA: \`${head_sha}\`" \
      "- Run reejecutado: https://github.com/${REPO}/actions/runs/${rerun_id}" \
      "${summary}" \
      "Si vuelven a fallar sobre este mismo commit, el fallo es reproducible y la incidencia se detendrá para decisión humana." >"$body_file"
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
    # Mismo endurecimiento que la aprobación (contrato §4.1): tampoco se
    # solicita corrección a partir de una revisión hecha sobre otra versión.
    resolve_pr
    require_reviewed_head
    # Las observaciones arrastran texto no confiable (hallazgos de Codex,
    # contenido de la PR): se neutralizan sus marcadores ANTES de incrustarlas
    # en el comentario, para que el bloque OBSERVACIONES_ESTRUCTURADAS que el
    # gate del corrector re-extrae no pueda romperse ni falsificarse.
    observations="$(printf '%s' "$observations" | sanitize_untrusted_json)"
    if [ -z "$observations" ] || [ "$observations" = "[]" ]; then
      stop_safely "sanitizacion-fallida" \
        "No se pudieron sanear las observaciones estructuradas antes de publicarlas; me detengo para no entregar al corrector un bloque corrupto."
    fi
    pr_hint="https://github.com/${REPO}/pull/${pr_number}"

    # Registro de convergencia (contrato §5, v1.5). Sustituye al contador ciego
    # de ciclos: publica las huellas estables de los hallazgos de esta ronda
    # para que la puerta del corrector pueda medir progreso real entre rondas
    # en vez de detenerse en un número fijo.
    #
    # El historial se lee UNA sola vez y se reutiliza para tres cosas: numerar
    # la ronda (abajo), el guardián de goteo (justo debajo) y, más adelante,
    # comprobar familia repetida (incidencia #495) sobre el historial + esta
    # ronda. Antes cada llamador pedía su propio volcado; con uno solo el
    # número de lecturas a la API no cambia (`sirius_next_round_number` ya
    # hacía exactamente una cuando no recibía volcado) y ninguno de los dos
    # avisos añade ninguna.
    history_dump="$(mktemp)"
    if ! sirius_dump_comments "$REPO" "$ISSUE" "$history_dump" >/dev/null 2>&1; then
      rm -f "$history_dump"
      stop_safely "historial-de-rondas-ilegible" \
        "No he podido leer el historial de rondas de esta incidencia, así que no puedo numerar esta ronda sin arriesgarme a repetir un número ya usado y corromper la medida de convergencia. Me detengo de forma segura."
    fi
    if ! round_number="$(sirius_next_round_number "$REPO" "$ISSUE" "$history_dump")"; then
      rm -f "$history_dump"
      stop_safely "historial-de-rondas-ilegible" \
        "No he podido leer el historial de rondas de esta incidencia, así que no puedo numerar esta ronda sin arriesgarme a repetir un número ya usado y corromper la medida de convergencia. Me detengo de forma segura."
    fi

    # Guardián de goteo en vivo (incidencia #496, ADR-123): SOLO informa -no
    # bloquea, no cambia ninguna transición de estado, no descarta ningún
    # hallazgo-. Reutiliza el mismo `history_dump` de arriba (head de la
    # ronda 1) contra el head actual, y anota cada observación cuyo
    # fichero/línea ya era idéntico entonces. Es best-effort por diseño: si
    # falla por cualquier motivo, publica las observaciones sin anotar en vez
    # de bloquear la ronda; el registro de convergencia de más abajo sigue
    # construyéndose a partir de `$observations` SIN anotar en cualquier caso.
    drip_obs_file="$(mktemp)"
    drip_out_file="$(mktemp)"
    printf '%s' "$observations" >"$drip_obs_file"
    if python3 "${SIRIUS_VERDICT_DIR}/sirius_drip_guard_cli.py" \
      --repo "$REPO" --comments-file "$history_dump" --round "$round_number" \
      --head "$head_sha" --observations "$drip_obs_file" --output "$drip_out_file" \
      && [ -s "$drip_out_file" ] && jq -e . "$drip_out_file" >/dev/null 2>&1; then
      readable_observations="$(cat "$drip_out_file")"
    else
      readable_observations="$observations"
    fi
    rm -f "$drip_obs_file" "$drip_out_file"
    readable="$(printf '%s' "$readable_observations" | jq -r '.[] | "- **\(.id // "?")** (\(.severidad // "?")) \(.archivo // "?"): \(.problema // "?")\n  - Criterio esperado: \(.criterio_esperado // "?")\n  - Prueba: \(.prueba // "?")\n  - Límites de corrección: \(.limites_correccion // "?")" + (if .posible_goteo then "\n  - ⚠️ Guardián de goteo: \(.posible_goteo)" else "" end)')"

    round_verdict="$(mktemp)"
    round_record="$(mktemp)"
    jq -n --argjson obs "$observations" '{observations: $obs}' >"$round_verdict"
    if ! python3 "${SIRIUS_VERDICT_DIR}/sirius_convergence.py" record \
      --verdict-file "$round_verdict" --round "$round_number" \
      --head "$head_sha" --output "$round_record"; then
      rm -f "$round_verdict" "$round_record" "$history_dump"
      stop_safely "registro-de-ronda-fallido" \
        "No se pudo construir el registro de convergencia de esta ronda; sin él la puerta del corrector no puede medir progreso y me detengo de forma segura."
    fi
    round_json="$(cat "$round_record")"
    rm -f "$round_verdict" "$round_record"

    # Aviso informativo de familia repetida (ADR-078, incidencia #495): el
    # detector ya existe y ya está medido (4 aciertos, 0 falsos sobre 14
    # incidencias candidatas), pero nunca tuvo llamante. Esta comprobación
    # SOLO informa -no bloquea ni cambia la transición de más abajo, ni el
    # `sirius:repair-requested` que sigue aplicándose siempre-: se publica el
    # dato para poder medir su tasa de aciertos y falsos en producción real
    # antes de darle autoridad (criterio de la incidencia #267). Un fallo al
    # comprobarlo (python3 ausente, historial corrupto) se ignora en silencio
    # por el mismo motivo: no puede convertirse en una parada segura de algo
    # que solo informa.
    printf '\n<!-- sirius-round:%s -->\n\n## RONDA_HALLAZGOS\n```json\n%s\n```\n' \
      "$round_number" "$round_json" >>"$history_dump"
    family_notice=""
    family_result="$(mktemp)"
    if python3 "${SIRIUS_VERDICT_DIR}/sirius_convergence.py" family-check \
      --comments-file "$history_dump" --output "$family_result" >/dev/null 2>&1; then
      if [ "$(jq -r '.hay_familia_repetida // false' "$family_result" 2>/dev/null)" = "true" ]; then
        family_notice="$(jq -r '[.evidencias[].detalle] | map("- " + .) | join("\n")' "$family_result" 2>/dev/null)"
      fi
    fi
    rm -f "$family_result" "$history_dump"

    # El marcador incluye head Y run: NO puede depender solo del contenido. Si
    # dos rondas distintas encontraran exactamente los mismos hallazgos —el caso
    # de estancamiento que la política de convergencia existe para detectar—, un
    # marcador por contenido se deduparía y la segunda ronda no publicaría su
    # registro. El historial se congelaría en una sola ronda y `sin-progreso` y
    # `head-sin-avance` no podrían dispararse nunca: justo el escenario que debe
    # terminar sería el único que no termina. Con head + run, una reejecución del
    # mismo run sigue siendo idempotente y una ronda nueva siempre se registra.
    # El sufijo es el de RONDA (run sin intento): ver SIRIUS_ROUND_TAG.
    marker="<!-- sirius-verdict:reviewer:changes:${head_sha}:${SIRIUS_ROUND_TAG} -->"
    body_file="$(mktemp)"
    {
      printf '%s\n\n%s\n' "$marker" "## CHANGES_REQUESTED"
      printf '- PR: %s\n' "$pr_hint"
      printf '%s\n\n%s\n\n## OBSERVACIONES_ESTRUCTURADAS\n```json\n%s\n```\n' "${summary}" "${readable}" "${observations}"
      if [ -n "$family_notice" ]; then
        printf '\n## AVISO_FAMILIA_REPETIDA\n%s\n\nAviso informativo (ADR-078, incidencia #495): no bloquea ni cambia esta transición.\n' \
          "$family_notice"
      fi
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
