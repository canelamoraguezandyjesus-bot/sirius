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
    # Un plazo absoluto del llamador manda sobre el número de intentos: sin esto,
    # los reintentos de una lectura seguían gastando tiempo (y esperas) despues
    # de que el presupuesto se hubiera agotado.
    local remaining=0
    if [ "${SIRIUS_GH_DEADLINE:-0}" -gt 0 ]; then
      remaining=$(( SIRIUS_GH_DEADLINE - $(_sirius_now) ))
      if [ "$remaining" -le 0 ]; then
        echo "sirius_retry: plazo agotado; no reintento: $*" >&2
        return "$status"
      fi
      [ "$delay" -gt "$remaining" ] && delay="$remaining"
    fi
    echo "sirius_retry: intento ${n}/${attempts} fallo (status ${status}); reintento en ${delay}s" >&2
    sleep "$delay"
    n=$((n + 1))
    delay=$((delay * 2))
  done
}

# --- Frontera de confianza de los comentarios ---------------------------------

# Filtro jq de autor de confianza. Los bloques estructurados que la
# automatización vuelve a leer de la incidencia — `## OBSERVACIONES_ESTRUCTURADAS`
# (dirige al corrector, que empuja commits con el PAT), `## RONDA_HALLAZGOS`
# (gobierna la convergencia) y los marcadores `Head SHA:` (gobiernan la
# verificación de head) — son instrucciones de facto para pasos con permisos de
# escritura. Sin filtro, cualquiera con permiso de comentar podría sembrarlos:
# el saneado en banda de sirius_apply_verdict.sh impide falsificarlos DENTRO de
# un bloque legítimo, pero no publicar uno propio en un comentario aparte, que
# además ganaría por ser el más reciente. Solo se aceptan comentarios del
# propietario del repositorio (identidad del PAT de la automatización; misma
# frontera de confianza que el `fusiona` del §8) o del bot de Actions, cuyo
# login no es suplantable.
#
# Deliberadamente NO se acepta `MEMBER`. En un repositorio de organización esa
# asociación la tiene cualquier miembro de la organización, incluidos los que
# solo pueden leer y comentar: bastaría con que uno sembrara marcadores
# `sirius-round` con números altos para gobernar si arranca el corrector, que
# corre con el PAT y permisos de escritura. El alcance de confianza se limita a
# quien ya podía autorizar un merge.
SIRIUS_TRUSTED_AUTHOR_JQ='select(.author_association == "OWNER" or (.user.login // "") == "github-actions[bot]")'
# Mismo filtro para la vía de respaldo GraphQL, que nombra los campos de otra
# forma (`authorAssociation`, `author.login`). El respaldo conserva así la
# garantía en vez de degradarla: un error transitorio de REST no puede abrir la
# puerta a un historial sembrado por un tercero.
SIRIUS_TRUSTED_AUTHOR_GRAPHQL_JQ='select(.authorAssociation == "OWNER" or ((.author.login // "") | ltrimstr("app/")) == "github-actions")'

# El filtro se aplica en TODAS las vías de lectura de comentarios, sin excepción.
# Dejar una sola vía sin filtrar reintroduce el problema por la puerta de atrás:
# `sirius_comment_once` y `sirius_transition` deciden si ya publicaron un
# comentario buscando su marcador de idempotencia en el historial, y esos
# marcadores son predecibles (`sirius-quality:<head>:failure` se deriva del SHA
# público de la PR). Con una lectura sin filtrar, un tercero que publicase el
# marcador ANTES que el flujo conseguía que la transición se diera por hecha y
# omitiera su propio comentario: la etiqueta se aplicaba, pero el registro
# oficial (`## CI_FAILURE`) no llegaba a existir. Como el resto de lecturas sí
# filtra por autor, ese comentario ajeno tampoco se contaba después, así que el
# fallo de Quality quedaba invisible para `ci_failure_streak` y el tope de
# `MAX_CI_FAILURE_STREAK` podía eludirse indefinidamente, manteniendo vivo al
# corrector —que corre con permisos de escritura— sin cota. Filtrando también
# aquí, un marcador ajeno simplemente no existe para la automatización: el
# comentario oficial se publica siempre y la deduplicación sigue operando entre
# comentarios propios, que es lo único que prueba que el paso ya se ejecutó.

# --- Vías de lectura de bajo nivel (una sola llamada, sin reintento) ----------

_sirius_body_rest() {
  # Vía principal: GitHub REST directo.
  _sirius_gh api "repos/${1}/issues/${2}" --jq '.body // ""'
}

_sirius_body_graphql() {
  # Vía de respaldo independiente.
  _sirius_gh issue view "${2}" --repo "${1}" --json body --jq '.body // ""'
}

# _sirius_now — segundos absolutos. `EPOCHSECONDS` es un builtin de Bash 5 y
# evita un fork por llamada; `date` es el respaldo.
_sirius_now() {
  if [ -n "${EPOCHSECONDS:-}" ]; then
    printf '%s' "$EPOCHSECONDS"
  else
    date +%s
  fi
}

# _sirius_gh <args...> — invoca `gh` acotado por SIRIUS_GH_DEADLINE, un instante
# ABSOLUTO, no una duración.
#
# La diferencia importa y fue un defecto real: con una duración fija, cada
# reintento de una lectura la heredaba entera, así que `timeout` acotaba cada
# invocación pero no el conjunto —`timeout` mata la invocación que lanza, no
# comparte plazo entre procesos— y una lectura con sus cuatro intentos REST más
# los cuatro de GraphQL podía multiplicar el presupuesto por seis o más. Con un
# instante absoluto, cada llamada recalcula lo que queda y el conjunto no puede
# rebasarlo.
#
# Sin la variable el comportamiento es el de siempre (sin límite): esto solo se
# activa donde hay un presupuesto que respetar.
_sirius_gh() {
  local deadline="${SIRIUS_GH_DEADLINE:-0}" remaining=0
  if [ "$deadline" -gt 0 ]; then
    remaining=$(( deadline - $(_sirius_now) ))
    if [ "$remaining" -le 0 ]; then
      echo "_sirius_gh: plazo agotado; no lanzo la llamada" >&2
      return 124
    fi
    if command -v timeout >/dev/null 2>&1; then
      timeout "$remaining" gh "$@"
      return $?
    fi
    # Degradar en silencio dejaría la llamada sin acotar justo donde el llamador
    # pidió acotarla; al menos queda dicho en el registro del job.
    echo "_sirius_gh: 'timeout' no disponible; la llamada NO queda acotada" >&2
  fi
  gh "$@"
}

_sirius_comments_rest() {
  _sirius_gh api --paginate "repos/${1}/issues/${2}/comments" \
    --jq "[.[] | ${SIRIUS_TRUSTED_AUTHOR_JQ}] | .[].body"
}

_sirius_comments_graphql() {
  _sirius_gh issue view "${2}" --repo "${1}" \
    --json comments --jq "[.comments[] | ${SIRIUS_TRUSTED_AUTHOR_GRAPHQL_JQ}] | .[].body"
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
# Solo comentarios de autor de confianza, por las dos vías (ver la frontera de
# confianza más arriba): lo que devuelve esta función gobierna la idempotencia
# de las transiciones y la localización de la PR, así que un comentario ajeno
# no puede figurar en él.
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
#
# La lectura REST DEBE paginar: sin --paginate la API devuelve solo los 30
# comentarios más antiguos y el "reverse" nunca vería los recientes, así que a
# partir de ~30 comentarios el SHA extraído sería uno viejo y las verificaciones
# de head fallarían en falso (parada head-obsoleto/head-inconsistente con un
# head correcto).
#
# _sirius_comments_newest_first <repo> <issue> — cuerpos de los comentarios del
# más reciente al más antiguo, con TODAS las páginas. Deliberadamente NO usa
# `gh api --slurp` (opción relativamente reciente cuya ausencia degradaría la
# paginación en silencio): con `--paginate --jq` el filtro se aplica por página
# y las salidas se concatenan, así que cada comentario sale como un JSON
# compacto por línea y python3 —requisito ya declarado de esta biblioteca—
# invierte el orden y emite los cuerpos íntegros. Invertir líneas de texto
# plano no serviría: los cuerpos son multilínea.

_sirius_comments_newest_first() {
  # La lectura y la transformación van SEPARADAS a propósito. Encadenadas en una
  # tubería, el estado de salida sería el de `python3` —que siempre acierta— y
  # el de `gh` se perdería salvo que el llamador tuviera `pipefail` activo: un
  # 503 se convertiría en "no hay comentarios" en vez de en un fallo, el
  # respaldo GraphQL nunca se intentaría y el corrector vería una incidencia sin
  # observaciones. Esta biblioteca no debe depender de las opciones de shell del
  # llamador para algo de lo que dependen decisiones.
  local raw=""
  raw="$(_sirius_gh api --paginate "repos/${1}/issues/${2}/comments?per_page=100" \
    --jq "[.[] | ${SIRIUS_TRUSTED_AUTHOR_JQ}] | .[] | @json")" || return 1
  printf '%s\n' "$raw" | python3 -c '
import json, sys
bodies = []
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        bodies.append(json.loads(line).get("body") or "")
    except json.JSONDecodeError:
        continue
for body in reversed(bodies):
    sys.stdout.write(body + "\n")
'
}

sirius_scan_text() {
  local repo="$1" num="$2" out="$3" comments="" body=""
  : >"$out"
  if comments="$(sirius_retry _sirius_comments_newest_first "$repo" "$num")"; then
    printf '%s\n' "$comments" >>"$out"
  elif comments="$(sirius_retry _sirius_gh issue view "$num" --repo "$repo" --json comments --jq "[.comments[] | ${SIRIUS_TRUSTED_AUTHOR_GRAPHQL_JQ}] | reverse | .[].body")"; then
    printf '%s\n' "$comments" >>"$out"
  fi
  if body="$(sirius_read_issue_body "$repo" "$num")"; then
    printf '%s\n' "$body" >>"$out"
  fi
  return 0
}

# sirius_extract_observations <repo> <issue> — imprime el bloque JSON de la
# ronda de observaciones más reciente (el que publica sirius_apply_verdict.sh
# bajo "## OBSERVACIONES_ESTRUCTURADAS" en un CHANGES_REQUESTED), o nada si no
# hay ninguna. Best-effort: nunca falla por sí sola.
sirius_extract_observations() {
  # Igual que sirius_scan_text: la lectura REST pagina para que el bloque de la
  # ronda más reciente sea visible también en incidencias con muchos comentarios.
  local repo="$1" num="$2" comments=""
  comments="$(sirius_retry _sirius_comments_newest_first "$repo" "$num" 2>/dev/null)" \
    || comments="$(sirius_retry _sirius_gh issue view "$num" --repo "$repo" --json comments --jq "[.comments[] | ${SIRIUS_TRUSTED_AUTHOR_GRAPHQL_JQ}] | reverse | .[].body" 2>/dev/null)" \
    || comments=""
  printf '%s' "$comments" | python3 -c '
import re, sys
text = sys.stdin.read()
m = re.search(r"## OBSERVACIONES_ESTRUCTURADAS\s*```json\s*(.*?)\s*```", text, re.DOTALL)
if m:
    sys.stdout.write(m.group(1))
'
  return 0
}

# sirius_dump_comments <repo> <issue> <out_file> — vuelca los comentarios en
# orden cronológico (del más antiguo al más reciente) para analizarlos. Pagina
# igual que el resto de lecturas. Best-effort: deja el archivo vacío si no se
# puede leer, y devuelve !=0 para que el llamador decida.
sirius_dump_comments() {
  # Orden cronológico natural: con `--paginate --jq` el filtro se aplica por
  # página y las salidas se concatenan en orden, así que aquí no hace falta
  # invertir nada ni depender de `--slurp`.
  local repo="$1" num="$2" out="$3" body=""
  : >"$out"
  if body="$(sirius_retry _sirius_gh api --paginate "repos/${repo}/issues/${num}/comments?per_page=100" --jq "[.[] | ${SIRIUS_TRUSTED_AUTHOR_JQ}] | .[].body")"; then
    printf '%s\n' "$body" >>"$out"
    return 0
  fi
  if body="$(sirius_retry _sirius_gh issue view "$num" --repo "$repo" --json comments --jq "[.comments[] | ${SIRIUS_TRUSTED_AUTHOR_GRAPHQL_JQ}] | .[].body")"; then
    printf '%s\n' "$body" >>"$out"
    return 0
  fi
  echo "sirius_dump_comments: ninguna via pudo leer los comentarios de #${num}" >&2
  echo "sirius_dump_comments: no se pudieron leer los comentarios de #${num}" >&2
  return 1
}

# sirius_next_round_number <repo> <issue> [dump_file] — número de la siguiente
# ronda de revisión-corrección: el mayor `<!-- sirius-round:N -->` publicado más
# uno. Si no hay ninguno devuelve 1.
#
# Devuelve !=0 y NO imprime número cuando el historial no se puede leer. Antes
# devolvía 1 en ese caso, y eso corrompía el historial en silencio: con rondas
# 1..3 ya publicadas, una lectura fallida numeraba la ronda siguiente como 1
# otra vez. `parse_round_records` ordena por el número del marcador, así que esa
# ronda nueva se colaba al PRINCIPIO del historial; la política de convergencia
# medía progreso contra una secuencia falsa y podía tanto bloquear un trabajo
# que progresaba como dejar correr uno estancado. Numerar a ciegas es peor que
# detenerse: el llamador convierte el fallo en parada segura.
#
# `dump_file` opcional evita una segunda lectura de la API cuando el llamador ya
# tiene un volcado válido de los comentarios.
sirius_next_round_number() {
  local repo="$1" num="$2" provided="${3:-}" dump="" highest="" owned=0
  if [ -n "$provided" ]; then
    dump="$provided"
  else
    dump="$(mktemp)"
    owned=1
    if ! sirius_dump_comments "$repo" "$num" "$dump" >/dev/null 2>&1; then
      rm -f "$dump"
      echo "sirius_next_round_number: historial ilegible para #${num}; no numero una ronda a ciegas" >&2
      return 1
    fi
  fi
  highest="$(grep -oE '<!-- sirius-round:[0-9]+ -->' "$dump" 2>/dev/null | grep -oE '[0-9]+' | sort -n | tail -1)"
  [ "$owned" -eq 1 ] && rm -f "$dump"
  printf '%s' "$(( ${highest:-0} + 1 ))"
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

  if ! sirius_retry _sirius_gh api -X PATCH "repos/${repo}/issues/${num}" --input "$payload" >/dev/null; then
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
# `gh label create --force` es un "upsert": crea la etiqueta si no existe y, si ya
# existe, actualiza su color y descripcion. NO se usa `gh label view` (subcomando
# inexistente que hacia caer en `gh label create`, que a su vez fallaba con
# "already exists" para una etiqueta existente y detenia la transicion).
sirius_ensure_label() {
  local repo="$1" name="$2" color="$3" description="$4"
  sirius_retry _sirius_gh label create "$name" --repo "$repo" \
    --color "$color" --description "$description" --force >/dev/null
}

# sirius_set_issue_labels <repo> <issue> <add_label> [remove_label...] — aplica
# add_label y retira remove_label..., de forma idempotente y VERIFICADA por REST.
# Devuelve 0 solo si, tras la operacion, add_label esta presente y cada
# remove_label esta ausente. Reintenta cada operacion; segura para reejecuciones.
sirius_set_issue_labels() {
  local repo="$1" num="$2" add="$3"
  shift 3
  local removes=("$@")
  sirius_retry _sirius_gh issue edit "$num" --repo "$repo" --add-label "$add" >/dev/null 2>&1 || true
  local r
  for r in "${removes[@]}"; do
    [ -z "${r:-}" ] && continue
    sirius_retry _sirius_gh issue edit "$num" --repo "$repo" --remove-label "$r" >/dev/null 2>&1 || true
  done
  # Verificacion autoritativa del estado final.
  local labels=""
  if ! labels="$(sirius_retry _sirius_gh api "repos/${repo}/issues/${num}" --jq '.labels[].name')"; then
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
  if sirius_retry _sirius_gh issue close "$num" --repo "$repo" --reason completed >/dev/null 2>&1; then
    return 0
  fi
  local state=""
  state="$(sirius_retry _sirius_gh api "repos/${repo}/issues/${num}" --jq '.state')" || return 1
  [ "$state" = "closed" ] && return 0
  return 1
}

# sirius_comment_once <repo> <issue> <marker> <body_file> — publica el comentario
# solo si el marcador no existe ya. 0 si publica o si ya existia; !=0 si falla al
# leer el historial autoritativo o al publicar.
#
# "Ya existe" significa que lo publico una identidad de confianza: la busqueda
# usa sirius_read_issue_comments, que filtra por autor. Un marcador ajeno no
# suprime el comentario oficial (ver la frontera de confianza). Si ninguna vía
# puede leer los comentarios, NO se interpreta como historial vacío: se falla de
# forma segura para no publicar un duplicado autoritativo a ciegas.
sirius_comment_once() {
  # El plazo se EXPORTA para que lo vean `_sirius_gh` y `sirius_retry`, así que
  # tiene que retirarse en TODAS las salidas: si se escapara, acotaría llamadas
  # posteriores de la misma shell con un instante ya vencido y las haría fallar
  # sin motivo. Un envoltorio lo garantiza mejor que recordar hacerlo en cada
  # `return`, que es justo la clase de olvido que esta sesión ya ha cometido.
  local status=0
  _sirius_comment_once_bounded "$@" || status=$?
  unset SIRIUS_GH_DEADLINE
  return "$status"
}

_sirius_comment_once_bounded() {
  local repo="$1" num="$2" marker="$3" file="$4" existing=""

  # El presupuesto arranca ANTES de la lectura de deduplicación: también es una
  # llamada a la API y también puede quedarse esperando.
  local budget="${SIRIUS_COMMENT_BUDGET_SECONDS:-90}"
  # Instante ABSOLUTO, compartido con `_sirius_gh` y con `sirius_retry`: es lo
  # que hace que el plazo acote el CONJUNTO y no cada llamada por separado.
  local deadline=$(( $(_sirius_now) + budget ))
  # Un plazo HEREDADO más estricto manda sobre el propio. Sin esto los plazos no
  # se componen: cada capa se concedía el suyo ignorando el de arriba, así que
  # un llamador que reservaba 120s para publicar veía cómo esta función se daba
  # 90s MÁS por su cuenta —hasta 210s en total— y el presupuesto del paso que
  # lo envolvía se desbordaba. Una cota que la capa de abajo puede ampliar no
  # es una cota.
  if [ "${SIRIUS_GH_DEADLINE:-0}" -gt 0 ] && [ "$SIRIUS_GH_DEADLINE" -lt "$deadline" ]; then
    deadline="$SIRIUS_GH_DEADLINE"
  fi
  export SIRIUS_GH_DEADLINE="$deadline"
  local delay="${SIRIUS_RETRY_BASE_DELAY:-2}"
  local after="" remaining=0

  remaining=$(( deadline - $(_sirius_now) ))
  if ! existing="$(sirius_read_issue_comments "$repo" "$num")"; then
    echo "sirius_comment_once: historial ilegible para #${num}; no publico ${marker} a ciegas" >&2
    return 1
  fi
  if printf '%s' "$existing" | grep -Fq "$marker"; then
    echo "sirius_comment_once: marcador ya presente en #${num} (${marker})" >&2
    return 0
  fi

  # Publicar contra la API de GitHub NO puede ser exactamente-una-vez: el POST de
  # `gh issue comment` no es idempotente y no hay clave de idempotencia del lado
  # del servidor. Un resultado ambiguo —GitHub acepta y la respuesta se pierde—
  # deja el comentario publicado sin que esta ejecución pueda saberlo, y tampoco
  # la siguiente si la lectura aún no lo refleja. Cualquier diseño que persiga la
  # unicidad SOLO aquí acota la ventana; no la cierra.
  #
  # Por eso la garantía vive en los LECTORES, que sí están en nuestra mano: un
  # duplicado no significa nada distinto de un original. `parse_round_records`
  # cuenta una ronda por número aunque su registro aparezca repetido, y
  # `ci_failure_streak` cuenta heads distintos, no marcadores.
  #
  # Siendo el duplicado inocuo, reintentar vuelve a ser lo correcto: perder el
  # registro sí hace daño. `complete-sirius-after-merge` cierra la incidencia
  # ANTES de publicar y después solo busca incidencias abiertas, así que un único
  # 5xx sin reintento dejaba la incidencia cerrada y sin su registro, de forma
  # irrecuperable: reejecutar ya no la encuentra.
  #
  # La relectura se conserva para no duplicar gratuitamente: si confirma que el
  # comentario llegó, se termina sin republicar.
  #
  # La cota es un PLAZO TOTAL y se aplica en TRES sitios, porque fallar en
  # cualquiera de ellos lo vacía de contenido: se comprueba antes de cada
  # llamada, la espera se recorta a lo que queda, y cada proceso `gh` se lanza
  # con el tiempo restante como límite (ver _sirius_gh). Sin lo tercero, una
  # llamada bloqueada esperando a GitHub consumía el resto del job —los
  # workflows que llaman aquí corren con `timeout-minutes: 5`— y la transición se
  # cancelaba antes de que este script emitiera su parada controlada.
  while true; do
    remaining=$(( deadline - $(_sirius_now) ))
    if [ "$remaining" -le 0 ]; then
      echo "sirius_comment_once: agotado el plazo de ${budget}s publicando ${marker} en" \
        "#${num}; parada reintentable" >&2
      return 1
    fi
    if _sirius_gh issue comment "$num" --repo "$repo" \
      --body-file "$file"; then
      return 0
    fi
    remaining=$(( deadline - $(_sirius_now) ))
    if [ "$remaining" -gt 0 ] \
      && after="$(sirius_read_issue_comments "$repo" "$num")" \
      && printf '%s' "$after" | grep -Fq "$marker"; then
      echo "sirius_comment_once: el POST devolvio error pero el comentario si llego a" \
        "#${num} (${marker}); no se republica" >&2
      return 0
    fi
    remaining=$(( deadline - $(_sirius_now) ))
    if [ "$remaining" -le 0 ]; then
      echo "sirius_comment_once: agotado el plazo de ${budget}s publicando ${marker} en" \
        "#${num}; parada reintentable" >&2
      return 1
    fi
    [ "$delay" -gt "$remaining" ] && delay="$remaining"
    echo "sirius_comment_once: no he podido confirmar la publicacion de ${marker} en" \
      "#${num}; reintento en ${delay}s (quedan ${remaining}s de plazo)" >&2
    sleep "$delay"
    delay=$(( delay * 2 ))
  done
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
  #
  # Esta lectura es autoritativa. Si falla REST y también GraphQL, la transición
  # se detiene ANTES de mutar etiquetas o cierre: tratar el fallo como una lista
  # vacía permitiría que una reejecución publicase una segunda ronda con el mismo
  # marcador de run y corrompiese el historial de convergencia.
  local existing="" marker_present=0
  if ! existing="$(sirius_read_issue_comments "$repo" "$num")"; then
    echo "::error::No se pudo leer el historial de comentarios de #${num}; transicion detenida antes de mutar estado." >&2
    return 1
  fi
  if printf '%s' "$existing" | grep -Fq "$marker"; then
    marker_present=1
    local verified=1 labels_now="" state_now=""
    labels_now="$(sirius_retry _sirius_gh api "repos/${repo}/issues/${num}" --jq '.labels[].name' 2>/dev/null)" || verified=0
    printf '%s\n' "$labels_now" | grep -Fxq "$add" || verified=0
    if [ "$close_flag" = "close" ] && [ "$verified" -eq 1 ]; then
      state_now="$(sirius_retry _sirius_gh api "repos/${repo}/issues/${num}" --jq '.state' 2>/dev/null)" || verified=0
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

# --- Localización de PR referenciada ------------------------------------------

# sirius_find_pr_for_issue <repo> <issue> — imprime, una por línea, los números
# de PR de este repositorio mencionados en el cuerpo o los comentarios de la
# incidencia (a partir de su URL completa) que estén ACTUALMENTE ABIERTAS. Sin
# duplicados.
#
# Código de salida, y es la mitad del contrato:
#   0 — se pudo leer. Cero líneas significa «leí y no hay ninguna»: es un HECHO.
#   2 — NO se pudo leer. No imprime nada, y ese vacío no significa nada.
#
# Antes devolvía 0 siempre y las tres lecturas llevaban `2>/dev/null || :`, así
# que un 503 salía por el mismo sitio que una incidencia sin PR. En la #193, con
# GitHub degradado, el ejecutor de órdenes le publicó al propietario «No he
# encontrado ninguna PR asociada a esta incidencia» con la PR abierta delante.
# Afirmar de más es peor que callarse: una lectura caída es reintentable y no
# pide nada de nadie; una PR de verdad ausente sí. El llamador necesita poder
# distinguirlas, y para eso tiene que llegarle la diferencia.
#
# El filtro por estado abierto es deliberado: una incidencia puede arrastrar en
# comentarios antiguos la URL de una PR ya cerrada o superada (p. ej. un
# relanzamiento tras descartar un intento previo). Contarla como vigente haría
# que el resolutor viese "varias PR" y se detuviera en falso. Solo cuentan las
# PR abiertas — y si el estado de una candidata no se puede leer, eso también es
# un fallo de lectura (2), no una omisión silenciosa.
sirius_find_pr_for_issue() {
  local repo="$1" num="$2" body_file="" comments_file="" candidates="" pr="" state=""
  body_file="$(mktemp)"
  comments_file="$(mktemp)"
  # Un fallo de LECTURA no es "no hay PR". Antes las tres lecturas llevaban
  # `2>/dev/null || :` y el vacio resultante viajaba hasta el llamador como un
  # hecho: en la incidencia #193, con GitHub devolviendo 503, el ejecutor de
  # ordenes le publico al propietario "No he encontrado ninguna PR asociada a
  # esta incidencia" mientras la PR estaba abierta. Es peor que callarse: manda
  # a una persona a buscar un problema que no existe.
  if ! sirius_read_issue_body "$repo" "$num" >"$body_file" 2>/dev/null; then
    rm -f "$body_file" "$comments_file"
    echo "sirius_find_pr_for_issue: no se pudo leer el cuerpo de #${num}; no distingo ausencia de fallo de lectura" >&2
    return 2
  fi
  if ! sirius_read_issue_comments "$repo" "$num" >"$comments_file" 2>/dev/null; then
    rm -f "$body_file" "$comments_file"
    echo "sirius_find_pr_for_issue: no se pudieron leer los comentarios de #${num}; no distingo ausencia de fallo de lectura" >&2
    return 2
  fi
  candidates="$(cat "$comments_file" "$body_file" \
    | grep -oE "https://github\.com/${repo}/pull/[0-9]+" \
    | sed -E 's#.*/pull/##' \
    | sort -u)"
  rm -f "$body_file" "$comments_file"
  local pr_json=""
  for pr in $candidates; do
    [ -z "$pr" ] && continue
    # Lo mismo con el estado: sin poder leerlo no se sabe si sigue abierta.
    # Descartarla en silencio convertia una PR ilegible en una PR inexistente.
    if ! pr_json="$(sirius_retry _sirius_gh api "repos/${repo}/pulls/${pr}" 2>/dev/null)"; then
      echo "sirius_find_pr_for_issue: no se pudo leer el estado de la PR #${pr}; no distingo cerrada de ilegible" >&2
      return 2
    fi
    state="$(printf '%s' "$pr_json" | jq -r '.state // empty' 2>/dev/null || true)"
    if [ "$state" = "open" ]; then
      printf '%s\n' "$pr"
    fi
  done
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

# sanitize_untrusted_text — neutraliza, en texto que procede de un agente o de
# Codex (y que puede arrastrar contenido de la PR), las TRES secuencias que los
# escáneres deterministas de la incidencia reinterpretan al releer comentarios:
#   - las vallas ``` (podrían cerrar antes de tiempo o falsificar el bloque
#     "## OBSERVACIONES_ESTRUCTURADAS ```json ... ```" que consume el gate del
#     corrector mediante sirius_extract_observations);
#   - los marcadores "Head SHA:"/"Merge SHA:" (envenenarían sirius_extract_sha
#     en verificaciones de head posteriores);
#   - la apertura "<!--" de un comentario HTML. Esta es la que faltaba, y su
#     ausencia era explotable: los marcadores que gobiernan la convergencia
#     (`<!-- sirius-round:N -->`) y la racha de CI (`<!-- sirius-quality:...-->`)
#     son comentarios HTML, y los publica la automatización, así que caen del
#     lado CONFIABLE del filtro de autor. Un texto no confiable que colara uno
#     de esos marcadores en un cuerpo publicado por el script quedaba contado
#     por `parse_round_records` o por `ci_failure_streak`: bastaba para fabricar
#     una ronda con cero hallazgos (progreso falso, corrector vivo sin cota) o
#     un `sirius-quality:<sha>:success` que reinicia la racha de fallos de CI.
#     Romper la apertura basta: ambos escáneres exigen el literal "<!--".
# El contenido sigue siendo legible y fiel; solo se desactivan los marcadores.
# (\u0027 es una comilla simple, escapada para no cerrar la cadena del programa jq.)
sanitize_untrusted_text() {
  jq -Rrs 'gsub("```"; "\u0027\u0027\u0027") | gsub("(?<p>[Hh][Ee][Aa][Dd]|[Mm][Ee][Rr][Gg][Ee])(\\s+[Ss][Hh][Aa]\\s*:)"; "\(.p)-sha:") | gsub("<!--"; "&lt;!--")'
}
sanitize_untrusted_json() {
  jq -c 'walk(if type == "string" then gsub("```"; "\u0027\u0027\u0027") | gsub("(?<p>[Hh][Ee][Aa][Dd]|[Mm][Ee][Rr][Gg][Ee])(\\s+[Ss][Hh][Aa]\\s*:)"; "\(.p)-sha:") | gsub("<!--"; "&lt;!--") else . end)'
}
