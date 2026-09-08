#!/usr/bin/env bash
# Sirius — quién atiende una activación: el reparto entre las dos puertas.
#
# POR QUÉ EXISTE ESTE GUION (ADR-167, segunda ronda). `sirius:implement-requested`
# la escuchan DOS workflows —`implement-sirius-work.yml` e `investigar-orden.yml`—
# y el reparto lo decide el campo `Perfil:` del cuerpo. Cada puerta leía ese
# campo por su cuenta, y de MOMENTOS distintos: el implementador del cuerpo del
# EVENTO, el de investigación del cuerpo ACTUAL. Con eso, un cuerpo editado entre
# el evento y el arranque producía dos desenlaces igual de malos, los dos
# reproducidos:
#
#   - evento `investigador`, cuerpo actual `programador`: las dos declinaban y la
#     incidencia se quedaba en `planned` + `implement-requested` SIN QUE NADIE la
#     atendiera.
#   - evento `programador`, cuerpo actual `investigador`: las dos la atendían.
#     Investigación la retiraba en `sirius:failed-safely` y el implementador
#     ejecutaba el modelo sobre la MISMA orden.
#
# La raíz no era el orden de las comprobaciones: era que la decisión estaba
# duplicada. Aquí vive una sola vez, y las dos puertas la llaman.
#
# LA REGLA, en dos partes:
#
#   1. Atiende la puerta cuyo perfil coincide con el cuerpo ACTUAL. Como el
#      cuerpo actual es uno solo, no puede haber dos dueñas ni ninguna.
#   2. Si el perfil CAMBIÓ desde el evento, no la atiende nadie: ese evento pedía
#      otro trabajo. Ejecutar el de ahora sería cambiar el tipo de trabajo en
#      silencio. Se rechaza con explicación y se retira `sirius:implement-requested`
#      conservando `sirius:planned`, que es la política de rechazo del validador
#      de activación: el estado queda RECUPERABLE —volver a aplicar la etiqueta
#      reactiva— y nada se pierde.
#
# Quién publica ese rechazo está decidido, no repartido al azar: lo hace la
# puerta que SERÍA la dueña según el cuerpo actual. La otra recibe «no es tuya» y
# se calla. Así el comentario y la retirada de la etiqueta ocurren una sola vez
# aunque los dos workflows corran a la vez.
#
# Uso:
#   sirius_reparto_activacion.sh <owner/repo> <issue> <perfil_del_evento> <esta_puerta>
#
# `<esta_puerta>` es `investigador` para `investigar-orden.yml`, y `otros` para
# `implement-sirius-work.yml`, que atiende todo perfil que no sea `investigador`.
#
# CÓDIGOS DE SALIDA, y solo estos cuatro significan algo:
#
#   0  La atiende esta puerta. Imprime el perfil actual en la salida estándar.
#   1  No es de esta puerta. Declina en silencio; no toques nada.
#   2  El evento es rancio (el perfil cambió). YA se ha explicado en la
#      incidencia y se ha retirado `sirius:implement-requested`. Declina.
#   3  No se pudo decidir —lectura o escritura fallida—. La puerta que llama
#      DEBE terminar en rojo: no se afirma nada que no se haya podido comprobar.
#   4  AMBIGÜEDAD que este guion no puede resolver: este mismo evento rancio ya
#      se rechazó y se retiró su etiqueta una vez, y la incidencia vuelve a
#      llevar `sirius:implement-requested`. Esa etiqueta puede ser una activación
#      NUEVA —el propietario siguió el diagnóstico y volvió a aplicarla— o la
#      misma de antes si aquella retirada no llegó a confirmarse. No se puede
#      distinguir con lo que la API deja ver, así que NO SE ESCRIBE NADA y la
#      puerta que llama termina en rojo para que lo mire una persona. Borrar una
#      activación nueva por un evento viejo es peor que un job rojo.
#
# Quien llame tiene que tratarlos con un `case`, nunca con un `if ... -ne 0`: ese
# atajo es justo el defecto que ADR-167 corrigió en el lector del registro.

set -uo pipefail

_REPARTO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
# shellcheck source=scripts/automation/sirius_issue.sh
source "${_REPARTO_DIR}/sirius_issue.sh"

REPO="${1:?uso: sirius_reparto_activacion.sh <owner/repo> <issue> <perfil_evento> <esta_puerta>}"
ISSUE="${2:?uso: sirius_reparto_activacion.sh <owner/repo> <issue> <perfil_evento> <esta_puerta>}"
PERFIL_EVENTO="${3-}"
ESTA_PUERTA="${4:?uso: la puerta que llama: «investigador» u «otros»}"
OWNER_LOGIN="${REPOSITORY_OWNER:-${REPO%%/*}}"

perfil_de() {
  printf '%s' "$1" | sed -n 's/^Perfil: *\([A-Za-z_-][A-Za-z_-]*\)@.*/\1/p' | head -1
}

cuerpo_actual=""
if ! cuerpo_actual="$(sirius_read_issue_body "$REPO" "$ISSUE")"; then
  echo "::error::No se pudo leer el cuerpo de #${ISSUE}; no se puede decidir quien atiende la activacion." >&2
  exit 3
fi
perfil_actual="$(perfil_de "$cuerpo_actual")"

case "$ESTA_PUERTA" in
  investigador) [ "$perfil_actual" = "investigador" ] && mia=si || mia=no ;;
  otros)        [ "$perfil_actual" = "investigador" ] && mia=no || mia=si ;;
  *) echo "::error::Puerta desconocida: ${ESTA_PUERTA}." >&2; exit 3 ;;
esac

if [ "$mia" = "no" ]; then
  echo "Perfil actual '${perfil_actual:-ninguno}': esta activacion no la atiende esta puerta." >&2
  exit 1
fi

if [ "$PERFIL_EVENTO" = "$perfil_actual" ]; then
  printf '%s\n' "$perfil_actual"
  exit 0
fi

# El perfil cambió entre el evento y ahora. Ni el trabajo que pedía el evento ni
# el que pide el cuerpo de ahora se ejecutan: hace falta una activación nueva.
#
# EL MARCADOR IDENTIFICA EL PAR CONCRETO, no «hubo un rechazo alguna vez»: dos
# eventos rancios distintos merecen cada uno su explicación, y el par es lo único
# que los distingue.
marcador="<!-- sirius-reparto:perfil-cambiado:${PERFIL_EVENTO:-ninguno}:${perfil_actual:-ninguno} -->"

# UN EVENTO VIEJO NO PUEDE CONSUMIR UNA ACTIVACIÓN NUEVA (ADR-167, tercera
# ronda). Esta rama retira `sirius:implement-requested`, y esa escritura solo es
# legítima si la etiqueta que retira es la que trajo ESTE evento. Reproducido:
# rechazado el evento y retirada la etiqueta, el propietario vuelve a aplicarla
# siguiendo el diagnóstico; si se reejecuta el job viejo, la retiraba otra vez y
# borraba la activación nueva.
#
# Lo que sí se puede probar: si este mismo par ya tiene su explicación publicada,
# el rechazo YA se entregó una vez. Entonces, si la etiqueta vuelve a estar, o es
# una activación nueva o es que aquella retirada no se confirmó, y **no hay forma
# de distinguirlo** con lo que la API deja ver. Se para sin escribir (código 4).
if ! _comentarios="$(sirius_read_issue_comments "$REPO" "$ISSUE")"; then
  echo "::error::No se pudo leer el historial de #${ISSUE}; no se puede saber si este evento rancio ya se rechazo. Reintentable." >&2
  exit 3
fi
if printf '%s' "$_comentarios" | grep -Fq "$marcador"; then
  if ! _etiquetas="$(sirius_retry gh api "repos/${REPO}/issues/${ISSUE}" --jq '.labels[].name')"; then
    echo "::error::No se pudieron leer las etiquetas de #${ISSUE}; reintentable." >&2
    exit 3
  fi
  if ! printf '%s\n' "$_etiquetas" | grep -Fxq "sirius:implement-requested"; then
    echo "Evento rancio en #${ISSUE}: ya se rechazo y la etiqueta no esta. Nada que hacer." >&2
    exit 2
  fi
  echo "::error::#${ISSUE}: este evento rancio (perfil '${PERFIL_EVENTO:-ninguno}' -> '${perfil_actual:-ninguno}') ya se rechazo y se retiro su etiqueta, y la incidencia vuelve a llevar sirius:implement-requested. Puede ser una activacion NUEVA o la misma sin retirar, y no se puede distinguir: NO se toca nada. Si la activacion de ahora es buena, dejala correr; si no, retirala a mano." >&2
  exit 4
fi

cuerpo="$(mktemp)"
{
  printf '%s\n\n' "$marcador"
  printf '⛔ **Activación rechazada** (`perfil-cambiado`)\n\n'
  printf 'Cuando se aplicó `sirius:implement-requested`, el cuerpo declaraba `Perfil: %s`; ahora declara `Perfil: %s`.\n\n' \
    "${PERFIL_EVENTO:-ninguno}" "${perfil_actual:-ninguno}"
  printf 'Esa activación pedía un trabajo distinto del que describe la orden de ahora, y ejecutar el de ahora seria cambiar el tipo de trabajo sin que nadie lo haya pedido. No se ha ejecutado nada.\n\n'
  printf '**Siguiente accion:** comprueba que el cuerpo dice el trabajo que quieres. Despues, vuelve a aplicar `sirius:implement-requested`.\n\n'
  printf '@%s\n' "$OWNER_LOGIN"
} > "$cuerpo"

if ! sirius_comment_once "$REPO" "$ISSUE" "$marcador" "$cuerpo"; then
  # Misma politica que el validador de activacion, y por el mismo motivo: sin
  # diagnostico NO se retira la etiqueta, porque eso dejaria la incidencia en un
  # callejon mudo. Conservandola se pierde tiempo, no la incidencia.
  echo "::error::No se pudo publicar el rechazo por perfil cambiado en #${ISSUE}; se CONSERVA sirius:implement-requested para no dejar la incidencia muda." >&2
  rm -f "$cuerpo"
  exit 3
fi
rm -f "$cuerpo"

sirius_retry gh issue edit "$ISSUE" --repo "$REPO" --remove-label "sirius:implement-requested" >/dev/null 2>&1 || true
etiquetas=""
if ! etiquetas="$(sirius_retry gh api "repos/${REPO}/issues/${ISSUE}" --jq '.labels[].name')"; then
  echo "::error::No se pudo verificar la retirada del evento en #${ISSUE}; reintentable." >&2
  exit 3
fi
if printf '%s\n' "$etiquetas" | grep -Fxq "sirius:implement-requested"; then
  echo "::error::sirius:implement-requested sigue presente en #${ISSUE}; reintentable." >&2
  exit 3
fi
echo "Evento rancio en #${ISSUE}: el perfil cambio de '${PERFIL_EVENTO:-ninguno}' a '${perfil_actual:-ninguno}'. Explicado y evento retirado; hace falta una activacion nueva." >&2
exit 2
