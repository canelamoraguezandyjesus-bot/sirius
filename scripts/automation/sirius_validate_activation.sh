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
# completo (todas las secciones obligatorias del contrato); la instantanea del
# evento declara el mismo `Perfil:` que el cuerpo vigente (si no, el evento es
# rancio: sale con 2 sin tocar etiquetas, ADR-221); `Perfil: rol@N` resoluble
# con el manifiesto (ADR-221), con aviso si N no es la vigente.
#
# Codigos de salida: 0 (valida, o rechazada con la etiqueta retirada y el
# motivo publicado), 1 (no se pudo completar; reintentable), 2 (evento rancio:
# nada validado, nada tocado, el aviso en la incidencia).
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
  # Justo antes de la UNICA mutacion destructiva, otra vez el cuerpo vigente:
  # publicar el rechazo puede llevar hasta 90 s de reintentos, y en ese rato
  # alguien puede haber corregido el cuerpo y vuelto a aplicar la etiqueta; la
  # que hay ahora seria la de OTRA activacion y retirarla la mataria (ronda 11
  # de Codex en la PR #670). Se compara el cuerpo ENTERO, no solo su perfil:
  # completar un cuerpo truncado sin tocar el `Perfil:` tambien es otra
  # activacion (ronda 12). Si el cuerpo ya no es el juzgado, este evento es
  # rancio: la etiqueta se conserva y se sale con 2, como arriba. La ventana
  # entre esta relectura y el `--remove-label` no la cierra la API (no hay
  # «retirar solo si el cuerpo no cambio»): es la misma raiz que el evento
  # rancio, la carga del workflow no dice de quien es la etiqueta presente.
  if [ -n "${cuerpo_juzgado_definido:-}" ]; then
    local cuerpo_ahora=""
    if ! cuerpo_ahora="$(sirius_read_issue_body "$REPO" "$ISSUE")"; then
      echo "::error::No se pudo releer el cuerpo de #${ISSUE} antes de retirar la etiqueta; se CONSERVA sirius:implement-requested. Reintentable." >&2
      return 1
    fi
    if [ "$cuerpo_ahora" != "$cuerpo_juzgado" ]; then
      echo "::error::El cuerpo de #${ISSUE} cambio mientras se publicaba el rechazo (${reason}): la sirius:implement-requested que hay puede ser de otra activacion y se CONSERVA; este evento es rancio." >&2
      exit 2
    fi
  fi
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
# El cuerpo que se va a juzgar, leido UNA vez y entero: `reject()` vuelve a
# leerlo justo antes de retirar la etiqueta y, si cambio mientras se publicaba
# el rechazo, no la toca (rondas 11 y 12 de Codex en la PR #670). Entero y no
# solo su `Perfil:`: completar un cuerpo truncado sin tocar el perfil tambien es
# otra activacion, y la etiqueta que hay entonces es la suya.
cuerpo_juzgado="$(<"$body_file")"
cuerpo_juzgado_definido=1
if ! missing="$(python3 "${SIRIUS_GATE_DIR}/validate_issue_body.py" "$body_file" 2>&1)"; then
  rm -f "$body_file"
  reject "cuerpo-incompleto" \
    "El cuerpo de la incidencia está truncado o incompleto. Detalle del validador: ${missing}" \
    "Edita el cuerpo hasta que contenga todas las secciones obligatorias del contrato (compara con una incidencia completa como #55)." || exit 1
  exit 0
fi

# --- 4) El `Perfil: rol@N` se puede resolver (ADR-221) -------------------------
# Con el MISMO resolutor que usa el implementador (resolver_prompt.py, H-28):
# si aqui no resuelve, alli tampoco, y el ciclo moriria a los seis segundos
# con la incidencia en failed-safely y la razon solo en el log del run
# (#653, 20-09-2026). Dos resolutores serian dos verdades; es uno.
cuerpo="$(<"$body_file")"
# Se juzga el cuerpo que el implementador VA A EJECUTAR: la instantanea del
# evento (`github.event.issue.body`, que el workflow pasa en ISSUE_BODY), no el
# cuerpo actual de la API. Si alguien edita el cuerpo despues de la etiqueta
# cambiando solo la version del perfil, el reparto no lo ve (compara el rol) y
# el implementador moriria con la version vieja mientras esta puerta daba por
# bueno el cuerpo nuevo (ronda 1 de Codex en la PR #670). Sin ISSUE_BODY (la
# cadena local) se juzga el cuerpo actual. `-` y no `:-`: una instantanea
# VACIA (el evento llego sin cuerpo y alguien lo escribio despues) es lo que el
# implementador ejecutaria, y se juzga vacia (ronda 2 de Codex en la PR #670).
cuerpo_a_ejecutar="${ISSUE_BODY-$cuerpo}"
# Y ANTES de juzgarla: si la instantanea y el cuerpo vigente declaran perfiles
# distintos, este evento es RANCIO. Alguien edito el `Perfil:` despues de la
# etiqueta, y puede haberla retirado y vuelto a aplicar: la
# `sirius:implement-requested` que hay ahora puede ser la de OTRA activacion,
# posterior, con su propio evento y su propia puerta. Rechazar aqui retiraria
# la etiqueta de esa otra -esta puerta corre en su propio workflow, con su
# propio grupo de concurrencia, y puede llegar tarde- y el trabajo se
# perderia sin que nadie lo viera (ronda 5 de Codex en la PR #670). Es el
# mismo razonamiento que el reparto (`sirius_reparto_activacion.sh`, ADR-167)
# aplica al rol, aqui aplicado al `rol@N` entero: no se valida, no se ejecuta,
# no se toca ninguna etiqueta, y se dice una vez por pareja de perfiles. Sale
# con 2, como el reparto, para que quien llama termine en rojo sin consumir.
if [ -n "${ISSUE_BODY+x}" ]; then
  # Las dos instantaneas se leen con el MISMO parser que el resolutor
  # (`profile_field`, via `resolver_prompt.py --perfil`): un `sed` propio leia
  # `implementer@4junk` como `implementer@4` y `Implementer@4` como valido, y
  # daba por iguales dos cuerpos que el resolutor juzga distintos; la puerta
  # seguia, rechazaba la instantanea y retiraba una etiqueta que puede ser de
  # otra activacion (ronda 6 de Codex en la PR #670). Sin parser no se juzga.
  if ! perfil_evento="$(ISSUE_BODY="$cuerpo_a_ejecutar" python3 "${SIRIUS_GATE_DIR}/resolver_prompt.py" --perfil)"; then
    echo "::error::No se pudo leer el Perfil de la instantanea del evento de #${ISSUE} con el parser canonico; no se valida ni se toca ninguna etiqueta. Reintentable." >&2
    exit 1
  fi
  if ! perfil_actual="$(ISSUE_BODY="$cuerpo" python3 "${SIRIUS_GATE_DIR}/resolver_prompt.py" --perfil)"; then
    echo "::error::No se pudo leer el Perfil del cuerpo vigente de #${ISSUE} con el parser canonico; no se valida ni se toca ninguna etiqueta. Reintentable." >&2
    exit 1
  fi
  if [ "$perfil_evento" != "$perfil_actual" ]; then
    rm -f "$body_file"
    marker_rancio="<!-- sirius-activation:evento-rancio:${perfil_evento:-ninguno}:${perfil_actual:-ninguno} -->"
    rancio_file="$(mktemp)"
    printf '%s\n\n%s\n\n%s\n\n%s\n\n%s\n%s\n' \
      "$marker_rancio" \
      "⚠️ **Activación no validada: el cuerpo cambió después de la etiqueta**" \
      "Cuando se aplicó \`sirius:implement-requested\`, el cuerpo declaraba \`Perfil: ${perfil_evento:-ninguno}\`; ahora declara \`Perfil: ${perfil_actual:-ninguno}\`. El implementador ejecutaría la instantánea del evento, no el cuerpo vigente, así que este evento **no se valida ni se ejecuta**." \
      "**Tampoco se ha tocado ninguna etiqueta.** No hay forma de saber si la \`sirius:implement-requested\` que hay ahora es la de esta activación o la de otra posterior, y retirar la activación de otro sería peor que dejar este evento sin atender." \
      "- **Si ya volviste a activar** con el cuerpo de ahora, esa activación tiene su propio evento y su propia puerta: déjala correr, aquí no hay nada más que hacer." \
      "- **Si no**, retira \`sirius:implement-requested\` y vuelve a aplicarla: solo un evento nuevo lleva el cuerpo nuevo." >"$rancio_file"
    if ! sirius_comment_once "$REPO" "$ISSUE" "$marker_rancio" "$rancio_file"; then
      rm -f "$rancio_file"
      echo "::error::El perfil de #${ISSUE} cambio desde que se aplico la etiqueta (evento: ${perfil_evento:-ninguno}; ahora: ${perfil_actual:-ninguno}) y no se pudo publicar el aviso; no se valida ni se toca ninguna etiqueta. Reintentable." >&2
      exit 2
    fi
    rm -f "$rancio_file"
    echo "::error::El perfil de #${ISSUE} cambio desde que se aplico la etiqueta (evento: ${perfil_evento:-ninguno}; ahora: ${perfil_actual:-ninguno}): este evento es rancio, no se valida ni se ejecuta y no se ha tocado ninguna etiqueta. El aviso esta en la incidencia." >&2
    exit 2
  fi
fi
# Solo se exime un rol que pertenezca a OTRO carril del manifiesto: ese tiene
# su propio ejecutor y su propia puerta de reparto (`investigador`, el
# investigador medido de investigar-orden.yml), y esta puerta no afirma nada
# sobre el. Un rol que no esta en ningun carril -una errata como
# `implementr`- NO se exime: el reparto lo mandaria al implementador y
# moriria alli, asi que aqui se rechaza por el resolutor. Un cuerpo SIN
# `Perfil:` tambien se juzga: ninguna puerta de reparto lo atiende y el
# implementador pararia en rojo.
# Con el parser canonico (`resolver_prompt.py --perfil`), no con un `sed`: el
# `sed` leia `investigador@2junk` como `investigador` y lo eximia, y el carril
# ajeno ejecutaria una orden cuyo `Perfil:` canonico no existe (ronda 9 de
# Codex en la PR #670). Lo que no es un perfil cae al resolutor y se rechaza.
if ! perfil_a_ejecutar="$(ISSUE_BODY="$cuerpo_a_ejecutar" python3 "${SIRIUS_GATE_DIR}/resolver_prompt.py" --perfil)"; then
  rm -f "$body_file"
  echo "::error::No se pudo leer el Perfil del cuerpo a ejecutar de #${ISSUE} con el parser canonico; no se valida ni se toca ninguna etiqueta. Reintentable." >&2
  exit 1
fi
rol_declarado="${perfil_a_ejecutar%@*}"
roles_de_otros_carriles="$(python3 - "${SIRIUS_GATE_DIR}/prompts/manifiesto.json" <<'PY'
import json, sys
carriles = json.load(open(sys.argv[1], encoding="utf-8"))["carriles"]
propios = {clave.split("@")[0] for clave in carriles["ejecucion"]}
ajenos = {clave.split("@")[0] for carril, claves in carriles.items() if carril != "ejecucion" for clave in claves}
print(" ".join(sorted(ajenos - propios)))
PY
)"
if [ -n "$rol_declarado" ] && printf ' %s ' "$roles_de_otros_carriles" | grep -Fq " ${rol_declarado} "; then
  rm -f "$body_file"
  echo "Activacion valida de #${ISSUE}: abierta, sirius:planned presente, sin estados incompatibles y cuerpo completo; el perfil \`${rol_declarado}\` es de otro carril del manifiesto (${roles_de_otros_carriles}) y esta puerta no lo juzga."
  exit 0
fi
if ! detalle="$(ISSUE_BODY="$cuerpo_a_ejecutar" python3 "${SIRIUS_GATE_DIR}/resolver_prompt.py" --carril ejecucion 2>&1 >/dev/null)"; then
  rm -f "$body_file"
  detalle="${detalle#::error::prompt sin resolver (ejecucion): }"
  reject "perfil-sin-resolver" \
    "El cuerpo declara un \`Perfil: rol@N\` que el manifiesto no puede resolver, así que el implementador pararía en rojo antes de empezar. Detalle del resolutor: ${detalle}" \
    "Pon en el cuerpo \`Perfil: rol@N\` con un rol y una versión registrados en \`scripts/automation/prompts/manifiesto.json\` (la versión vigente de cada rol está en \`docs/implementation/work_engine/perfiles/<rol>.yml\`)." || exit 1
  exit 0
fi

# --- 5) Un rol@N valido pero no vigente se avisa, no se rechaza ----------------
# `rol@N` significa UN texto (H-28) y una version antigua sigue siendo
# ejecutable a proposito; lo que faltaba era decirlo (deuda 35 de la bitacora).
aviso="$(ISSUE_BODY="$cuerpo_a_ejecutar" python3 "${SIRIUS_GATE_DIR}/resolver_prompt.py" --carril ejecucion --vigencia 2>/dev/null)" || aviso=""
rm -f "$body_file"
if [ -n "$aviso" ]; then
  declarado="$perfil_a_ejecutar"
  marker_aviso="<!-- sirius-activation:aviso:perfil-no-vigente:${declarado} -->"
  aviso_file="$(mktemp)"
  printf '%s\n\n%s\n\n%s\n' \
    "$marker_aviso" \
    "ℹ️ **Perfil no vigente** (\`${declarado}\`)" \
    "$aviso" >"$aviso_file"
  # Si el aviso no se puede publicar, la activacion NO se da por valida: el
  # aviso es lo unico que deja en la incidencia la version que se va a ejecutar
  # y como recuperarla, y sin el se consumiria el perfil antiguo en silencio.
  # Se conserva la activacion (ninguna etiqueta tocada) y se sale con 3, que
  # quien llama trata como «no se pudo completar; reintentable» (ronda 9 de
  # Codex en la PR #670).
  if ! sirius_comment_once "$REPO" "$ISSUE" "$marker_aviso" "$aviso_file"; then
    rm -f "$aviso_file"
    echo "::error::No se pudo publicar el aviso de perfil no vigente en #${ISSUE}; la activacion se conserva (ninguna etiqueta tocada) y este run termina sin validarla: relanzalo desde Actions. Reintentable." >&2
    exit 3
  fi
  rm -f "$aviso_file"
fi

echo "Activacion valida de #${ISSUE}: abierta, sirius:planned presente, sin estados incompatibles, cuerpo completo y perfil resoluble."
exit 0
