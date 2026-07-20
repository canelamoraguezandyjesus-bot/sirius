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
