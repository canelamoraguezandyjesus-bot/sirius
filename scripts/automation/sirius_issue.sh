#!/usr/bin/env bash
# Sirius — biblioteca de E/S robusta de incidencias de GitHub para la automatización.
#
# Motivación (ver incidencia #55): la lectura de una incidencia mediante una sola
# vía (GraphQL/MCP) puede devolver 502/503 o un cuerpo truncado. Ninguna Routine
# ni workflow debe depender de una sola vía de lectura, ni aceptar un cuerpo
# truncado, ni sobrescribir una incidencia sin verificar la escritura.
#
# Esta biblioteca ofrece:
#   - reintentos limitados con espera creciente (sirius_retry);
#   - lectura robusta: REST (gh api) como vía principal, GraphQL (gh issue view)
#     como respaldo independiente (sirius_read_issue_body / _comments);
#   - validación estructural del cuerpo (sirius_body_is_complete);
#   - lectura de un contrato de trabajo con validación (sirius_read_workitem_body);
#   - escritura con verificación posterior por longitud y hash y copia de
#     seguridad del cuerpo anterior (sirius_write_issue_body);
#   - creación idempotente de etiquetas (sirius_ensure_label);
#   - extracción robusta de Head/Merge SHA (sirius_extract_sha).
#
# Requisitos en tiempo de ejecución: gh, jq, python3. Diseñada para ser segura
# con `set -u` y `set -o pipefail` y para NO depender de `set -e`: cada función
# controla sus propios códigos de retorno.
#
# Uso: source scripts/automation/sirius_issue.sh

SIRIUS_AUTOMATION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
SIRIUS_VALIDATOR="${SIRIUS_AUTOMATION_DIR}/validate_issue_body.py"

# sirius_retry <cmd...> — ejecuta el comando y lo reintenta ante cualquier fallo
# (incluye 5xx/timeouts de la API). Configurable con SIRIUS_RETRY_ATTEMPTS y
# SIRIUS_RETRY_BASE_DELAY (segundos). Devuelve el último código de salida.
sirius_retry() {
  local attempts="${SIRIUS_RETRY_ATTEMPTS:-4}"
  local delay="${SIRIUS_RETRY_BASE_DELAY:-2}"
  local n=1
  local status=0
  while true; do
    if "$@"; then
      return 0
    else
      status=$?
    fi
    if [ "$n" -ge "$attempts" ]; then
      echo "sirius_retry: fallo tras ${attempts} intento(s): $*" >&2
      return "$status"
    fi
    echo "sirius_retry: intento ${n}/${attempts} fallo (status ${status}); reintento en ${delay}s" >&2
    sleep "$delay"
    n=$((n + 1))
    delay=$((delay * 2))
  done
}

# --- Vías de lectura de bajo nivel (una sola llamada, sin reintento) ----------

_sirius_body_rest() {
  # Vía principal: GitHub REST directo.
  gh api "repos/${1}/issues/${2}" --jq '.body // ""'
}

_sirius_body_graphql() {
  # Vía de respaldo independiente.
  gh issue view "${2}" --repo "${1}" --json body --jq '.body // ""'
}

_sirius_comments_rest() {
  gh api --paginate "repos/${1}/issues/${2}/comments" --jq '.[].body'
}

_sirius_comments_graphql() {
  gh issue view "${2}" --repo "${1}" --json comments --jq '.comments[].body'
}

# --- Lectura robusta ----------------------------------------------------------

# sirius_read_issue_body <repo> <issue> — imprime el cuerpo; REST con reintentos y,
# si falla, GraphQL con reintentos. Devuelve !=0 solo si TODAS las vías fallan.
sirius_read_issue_body() {
  local repo="$1" num="$2" body=""
  if body="$(sirius_retry _sirius_body_rest "$repo" "$num")"; then
    printf '%s' "$body"
    return 0
  fi
  echo "sirius_read_issue_body: REST agotado para #${num}; probando GraphQL" >&2
  if body="$(sirius_retry _sirius_body_graphql "$repo" "$num")"; then
    printf '%s' "$body"
    return 0
  fi
  echo "sirius_read_issue_body: todas las vias fallaron para #${num}" >&2
  return 1
}

# sirius_read_issue_comments <repo> <issue> — imprime los cuerpos de comentarios,
# REST con reintentos y respaldo GraphQL. !=0 solo si todas las vías fallan.
sirius_read_issue_comments() {
  local repo="$1" num="$2" out=""
  if out="$(sirius_retry _sirius_comments_rest "$repo" "$num")"; then
    printf '%s' "$out"
    return 0
  fi
  echo "sirius_read_issue_comments: REST agotado para #${num}; probando GraphQL" >&2
  if out="$(sirius_retry _sirius_comments_graphql "$repo" "$num")"; then
    printf '%s' "$out"
    return 0
  fi
  echo "sirius_read_issue_comments: todas las vias fallaron para #${num}" >&2
  return 1
}

# sirius_scan_text <repo> <issue> <out_file> — escribe, en out_file, texto para
# escanear un SHA: primero los comentarios más recientes y después el cuerpo.
# Best-effort y no bloqueante (siempre devuelve 0); REST con respaldo GraphQL.
sirius_scan_text() {
  local repo="$1" num="$2" out="$3" comments="" body=""
  : >"$out"
  if comments="$(sirius_retry gh api "repos/${repo}/issues/${num}/comments" --jq 'reverse | .[].body')"; then
    printf '%s\n' "$comments" >>"$out"
  elif comments="$(sirius_retry gh issue view "$num" --repo "$repo" --json comments --jq '[.comments[].body] | reverse | .[]')"; then
    printf '%s\n' "$comments" >>"$out"
  fi
  if body="$(sirius_read_issue_body "$repo" "$num")"; then
    printf '%s\n' "$body" >>"$out"
  fi
  return 0
}

# --- Validación estructural ---------------------------------------------------

# sirius_body_is_complete <file> — 0 si el cuerpo del archivo contiene todas las
# secciones obligatorias del contrato; !=0 si está truncado o incompleto.
sirius_body_is_complete() {
  python3 "$SIRIUS_VALIDATOR" "$1"
}

# sirius_read_workitem_body <repo> <issue> <out_file> — lee el contrato de trabajo
# de forma robusta y solo lo acepta si está completo. Escribe el cuerpo en
# out_file. Estrategia: REST -> validar; si truncado, GraphQL -> validar. Devuelve
# !=0 si ninguna vía entrega un cuerpo completo (parada segura autorizada).
sirius_read_workitem_body() {
  local repo="$1" num="$2" out_file="$3" body=""
  if body="$(sirius_retry _sirius_body_rest "$repo" "$num")"; then
    printf '%s' "$body" >"$out_file"
    if sirius_body_is_complete "$out_file" >/dev/null 2>&1; then
      return 0
    fi
    echo "sirius_read_workitem_body: cuerpo REST incompleto/truncado para #${num}; probando GraphQL" >&2
  else
    echo "sirius_read_workitem_body: REST agotado para #${num}; probando GraphQL" >&2
  fi
  if body="$(sirius_retry _sirius_body_graphql "$repo" "$num")"; then
    printf '%s' "$body" >"$out_file"
    if sirius_body_is_complete "$out_file" >/dev/null 2>&1; then
      return 0
    fi
    echo "sirius_read_workitem_body: cuerpo GraphQL incompleto/truncado para #${num}" >&2
  fi
  echo "sirius_read_workitem_body: no se obtuvo un cuerpo completo para #${num}" >&2
  return 1
}

# --- Escritura verificada -----------------------------------------------------

# sirius_write_issue_body <repo> <issue> <body_file> [backup_file] — escribe el
# cuerpo de la incidencia de forma segura:
#   1. rechaza la escritura si el cuerpo de origen está truncado/incompleto;
#   2. guarda una copia recuperable del cuerpo anterior (best-effort);
#   3. escribe de una sola vez mediante REST (gh api PATCH --input);
#   4. vuelve a leer por REST y compara longitud y hash;
#   5. falla si el contenido almacenado no coincide con el preparado.
# La comparación normaliza saltos de línea finales (GitHub puede recortar uno).
sirius_write_issue_body() {
  local repo="$1" num="$2" body_file="$3" backup_file="${4:-}"

  if ! sirius_body_is_complete "$body_file" >/dev/null 2>&1; then
    echo "sirius_write_issue_body: el cuerpo de origen esta truncado/incompleto; no se escribe #${num}" >&2
    return 1
  fi

  if [ -n "$backup_file" ]; then
    if sirius_read_issue_body "$repo" "$num" >"$backup_file" 2>/dev/null; then
      echo "sirius_write_issue_body: copia del cuerpo anterior de #${num} en ${backup_file}" >&2
    else
      echo "sirius_write_issue_body: aviso: no se pudo respaldar el cuerpo anterior de #${num}" >&2
    fi
  fi

  local payload
  payload="$(mktemp)"
  if ! jq -n --rawfile b "$body_file" '{body: $b}' >"$payload"; then
    echo "sirius_write_issue_body: no se pudo construir el payload JSON para #${num}" >&2
    rm -f "$payload"
    return 1
  fi

  if ! sirius_retry gh api -X PATCH "repos/${repo}/issues/${num}" --input "$payload" >/dev/null; then
    echo "sirius_write_issue_body: fallo al escribir el cuerpo de #${num}" >&2
    rm -f "$payload"
    return 1
  fi
  rm -f "$payload"

  local readback
  readback="$(mktemp)"
  if ! sirius_read_issue_body "$repo" "$num" >"$readback"; then
    echo "sirius_write_issue_body: no se pudo releer #${num} para verificar" >&2
    rm -f "$readback"
    return 1
  fi

  if python3 - "$body_file" "$readback" <<'PY'
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    want = fh.read().rstrip("\n")
with open(sys.argv[2], encoding="utf-8") as fh:
    got = fh.read().rstrip("\n")

if len(want) != len(got) or want != got:
    sys.stderr.write(
        f"verificacion fallida: longitud preparada={len(want)} almacenada={len(got)}\n"
    )
    sys.exit(1)
sys.exit(0)
PY
  then
    rm -f "$readback"
    echo "sirius_write_issue_body: verificacion correcta para #${num}" >&2
    return 0
  fi
  rm -f "$readback"
  echo "sirius_write_issue_body: el contenido almacenado no coincide; escritura considerada fallida para #${num}" >&2
  return 1
}

# --- Etiquetas ----------------------------------------------------------------

# sirius_ensure_label <repo> <name> <color> <description> — idempotente.
sirius_ensure_label() {
  local repo="$1" name="$2" color="$3" description="$4"
  if gh label view "$name" --repo "$repo" >/dev/null 2>&1; then
    gh label edit "$name" --repo "$repo" --color "$color" --description "$description" >/dev/null
  else
    gh label create "$name" --repo "$repo" --color "$color" --description "$description" >/dev/null
  fi
}

# sirius_set_issue_labels <repo> <issue> <add_label> [remove_label...] — aplica
# add_label y retira remove_label..., de forma idempotente y VERIFICADA por REST.
# Devuelve 0 solo si, tras la operacion, add_label esta presente y cada
# remove_label esta ausente. Reintenta cada operacion; segura para reejecuciones.
sirius_set_issue_labels() {
  local repo="$1" num="$2" add="$3"
  shift 3
  local removes=("$@")
  sirius_retry gh issue edit "$num" --repo "$repo" --add-label "$add" >/dev/null 2>&1 || true
  local r
  for r in "${removes[@]}"; do
    [ -z "${r:-}" ] && continue
    sirius_retry gh issue edit "$num" --repo "$repo" --remove-label "$r" >/dev/null 2>&1 || true
  done
  # Verificacion autoritativa del estado final.
  local labels=""
  if ! labels="$(sirius_retry gh api "repos/${repo}/issues/${num}/labels" --jq '.[].name')"; then
    echo "sirius_set_issue_labels: no se pudo verificar las etiquetas de #${num}" >&2
    return 1
  fi
  if ! printf '%s\n' "$labels" | grep -Fxq "$add"; then
    echo "sirius_set_issue_labels: la etiqueta ${add} no quedo aplicada en #${num}" >&2
    return 1
  fi
  for r in "${removes[@]}"; do
    [ -z "${r:-}" ] && continue
    if printf '%s\n' "$labels" | grep -Fxq "$r"; then
      echo "sirius_set_issue_labels: la etiqueta ${r} no se retiro de #${num}" >&2
      return 1
    fi
  done
  return 0
}

# sirius_close_issue <repo> <issue> — cierre idempotente: 0 si cierra o si ya
# estaba cerrada; !=0 si no se pudo dejar cerrada.
sirius_close_issue() {
  local repo="$1" num="$2"
  if sirius_retry gh issue close "$num" --repo "$repo" --reason completed >/dev/null 2>&1; then
    return 0
  fi
  local state=""
  state="$(sirius_retry gh api "repos/${repo}/issues/${num}" --jq '.state')" || return 1
  [ "$state" = "closed" ] && return 0
  return 1
}

# sirius_comment_once <repo> <issue> <marker> <body_file> — publica el comentario
# solo si el marcador no existe ya. 0 si publica o si ya existia; !=0 si falla al
# publicar.
sirius_comment_once() {
  local repo="$1" num="$2" marker="$3" file="$4" existing=""
  existing="$(sirius_read_issue_comments "$repo" "$num" 2>/dev/null)"
  if printf '%s' "$existing" | grep -Fq "$marker"; then
    echo "sirius_comment_once: marcador ya presente en #${num} (${marker})" >&2
    return 0
  fi
  sirius_retry gh issue comment "$num" --repo "$repo" --body-file "$file"
}

# sirius_transition <repo> <issue> <marker> <body_file> <add_label> <color>
#                   <desc> <close_flag: close|noclose> <remove_csv>
# Transicion de estado ATOMICA e idempotente. No depende de `set -e`: comprueba
# explicitamente cada codigo de retorno y se detiene ante el primer fallo. El
# comentario con marcador de idempotencia SOLO se publica despues de que todas las
# operaciones criticas (etiqueta garantizada, etiquetas aplicadas y, si procede,
# cierre) hayan terminado y se hayan verificado. Un fallo deja la ejecucion
# reintentable (no se publica marcador) y devuelve !=0.
sirius_transition() {
  local repo="$1" num="$2" marker="$3" file="$4"
  local add="$5" color="$6" desc="$7" close_flag="$8" remove_csv="$9"

  # Idempotencia con verificacion: un marcador presente NO basta por si solo.
  # Historicamente (incidencia #50) un flujo antiguo publico el marcador y murio
  # antes de aplicar la etiqueta/cierre; salir temprano solo por el marcador
  # dejaba ese estado atascado para siempre. Si el marcador existe, se verifica
  # el estado final real: si ya esta aplicado, no se repite nada; si falta, se
  # completa la transicion SIN publicar un comentario duplicado.
  local existing="" marker_present=0
  existing="$(sirius_read_issue_comments "$repo" "$num" 2>/dev/null)"
  if printf '%s' "$existing" | grep -Fq "$marker"; then
    marker_present=1
    local verified=1 labels_now="" state_now=""
    labels_now="$(sirius_retry gh api "repos/${repo}/issues/${num}/labels" --jq '.[].name' 2>/dev/null)" || verified=0
    printf '%s\n' "$labels_now" | grep -Fxq "$add" || verified=0
    if [ "$close_flag" = "close" ] && [ "$verified" -eq 1 ]; then
      state_now="$(sirius_retry gh api "repos/${repo}/issues/${num}" --jq '.state' 2>/dev/null)" || verified=0
      [ "$state_now" = "closed" ] || verified=0
    fi
    if [ "$verified" -eq 1 ]; then
      echo "sirius_transition: transicion ya registrada y verificada para #${num} (${marker})" >&2
      return 0
    fi
    echo "sirius_transition: marcador presente pero estado incompleto en #${num}; se completa sin duplicar comentario." >&2
  fi

  # 1) Etiqueta terminal garantizada.
  if ! sirius_ensure_label "$repo" "$add" "$color" "$desc"; then
    echo "::error::No se pudo garantizar la etiqueta ${add} (#${num}); transicion detenida (reintentable)." >&2
    return 1
  fi

  # 2) Etiquetas aplicadas y verificadas.
  local removes=()
  if [ -n "${remove_csv:-}" ]; then
    IFS=',' read -r -a removes <<<"$remove_csv"
  fi
  if ! sirius_set_issue_labels "$repo" "$num" "$add" "${removes[@]}"; then
    echo "::error::No se pudo aplicar la transicion de etiquetas (#${num}); detenida (reintentable)." >&2
    return 1
  fi

  # 3) Cierre obligatorio cuando corresponde.
  if [ "$close_flag" = "close" ]; then
    if ! sirius_close_issue "$repo" "$num"; then
      echo "::error::No se pudo cerrar la incidencia #${num}; transicion detenida (reintentable)." >&2
      return 1
    fi
  fi

  # 4) Solo ahora, tras completar y verificar todo, se publica el marcador
  #    (salvo que ya existiera: entonces la reanudacion no debe duplicarlo).
  if [ "$marker_present" -eq 0 ]; then
    if ! sirius_comment_once "$repo" "$num" "$marker" "$file"; then
      echo "::error::No se pudo publicar el comentario de transicion (#${num})." >&2
      return 1
    fi
  fi
  return 0
}

# --- Extracción de SHA --------------------------------------------------------

# sirius_extract_sha <file> — imprime el primer Head/Merge SHA (7-40 hex) del
# texto (pensado para comentarios más recientes primero + cuerpo). Si no hay
# ninguno imprime "no-head". Nunca falla.
sirius_extract_sha() {
  local sha=""
  sha="$(sed -nE 's/.*(Head|Merge) SHA:[[:space:]]*`?([0-9a-fA-F]{7,40}).*/\2/p' "$1" | head -n 1)"
  if [ -z "${sha:-}" ]; then
    sha="no-head"
  fi
  printf '%s' "$sha"
}
