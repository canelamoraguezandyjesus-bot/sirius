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
#   2  El evento es rancio: el perfil cambió desde que se aplicó la etiqueta.
#      Ya se ha explicado en la incidencia y NO se ha tocado nada. La puerta que
#      llama DEBE terminar en rojo: el encargo que pedía ese evento no se ha
#      atendido y nadie lo va a atender.
#   3  No se pudo decidir —lectura o publicación fallida—. También en rojo: no se
#      afirma nada que no se haya podido comprobar.
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
# ESTA RAMA NO ESCRIBE (ADR-167, cuarta ronda). Retiraba `sirius:implement-requested`
# para dejar el estado recuperable, y esa escritura solo sería legítima si la
# etiqueta que retira fuese la que trajo ESTE evento. No hay forma de saberlo:
#
#   1. Se activa una orden con `Perfil: investigador`; su evento A queda en cola.
#   2. El propietario cambia el perfil a programación, retira la etiqueta y la
#      vuelve a aplicar: nace el evento B.
#   3. Arranca A. La etiqueta que ve es la de B, y la retiraba.
#   4. Arranca B, encuentra solo `sirius:planned` y declina. El encargo se pierde.
#
# La tercera ronda intentó acotarlo mirando si el rechazo ya estaba publicado,
# pero la AUSENCIA de ese marcador no demuestra que la etiqueta sea de este
# evento —en la secuencia de arriba no hay marcador ninguno—. Distinguirlas
# exigiría una identidad del evento que la carga del workflow no trae, e
# inventarla sería ampliar la arquitectura para tapar la ambigüedad.
#
# Así que la salida es la conservadora: se explica y se para. La activación que
# haya se CONSERVA, para que la atienda el evento que sí le corresponde; y si no
# hay ninguna otra, el comentario dice qué hacer. Y no promete que otro evento
# vaya a atenderla: la etiqueta no demuestra que exista ese otro evento -el
# propietario pudo editar solo el perfil, sin reactivar-, así que el aviso
# describe los DOS casos y deja la decisión en quien sí puede distinguirlos.
# Dejar este evento sin atender es peor que un encargo perdido, pero mucho menos
# malo que borrar el de otro.
#
# EL MARCADOR IDENTIFICA EL PAR CONCRETO, no «hubo un rechazo alguna vez»: dos
# eventos rancios distintos merecen cada uno su explicación.
marcador="<!-- sirius-reparto:perfil-cambiado:${PERFIL_EVENTO:-ninguno}:${perfil_actual:-ninguno} -->"
cuerpo="$(mktemp)"
{
  printf '%s\n\n' "$marcador"
  printf '⛔ **Activación no atendida** (`perfil-cambiado`)\n\n'
  printf 'Cuando se aplicó `sirius:implement-requested`, el cuerpo declaraba `Perfil: %s`; ahora declara `Perfil: %s`.\n\n' \
    "${PERFIL_EVENTO:-ninguno}" "${perfil_actual:-ninguno}"
  printf 'Esa activación pedía un trabajo distinto del que describe la orden de ahora, y ejecutar el de ahora seria cambiar el tipo de trabajo sin que nadie lo haya pedido. **No se ha ejecutado nada.**\n\n'
  printf '**Tampoco se ha tocado ninguna etiqueta.** No hay forma de saber si la `sirius:implement-requested` que hay ahora es la de esta activacion o la de otra posterior, y retirar la activacion de otro seria peor que dejar este evento sin atender.\n\n'
  printf '**Siguiente accion.** La etiqueta, por si sola, NO permite distinguir estos dos casos, asi que lo decides tu:\n\n'
  printf -- '- **Si ya volviste a activar** con el perfil de ahora, esa activacion tiene su propio evento y lo atendera la puerta que corresponda: dejala correr, aqui no hay nada mas que hacer.\n'
  printf -- '- **Si solo editaste el perfil** y no volviste a activar, la `sirius:implement-requested` que hay es la de esta activacion y ya no la va a atender nadie. Comprueba que no haya una ejecucion en curso, retira la etiqueta y vuelve a aplicarla para generar una activacion nueva.\n\n'
  printf '@%s\n' "$OWNER_LOGIN"
} > "$cuerpo"

if ! sirius_comment_once "$REPO" "$ISSUE" "$marcador" "$cuerpo"; then
  echo "::error::No se pudo publicar el diagnostico de perfil cambiado en #${ISSUE}; reintentable. No se ha tocado nada." >&2
  rm -f "$cuerpo"
  exit 3
fi
rm -f "$cuerpo"
echo "Evento rancio en #${ISSUE}: el perfil cambio de '${PERFIL_EVENTO:-ninguno}' a '${perfil_actual:-ninguno}'. Explicado; NO se ha tocado ninguna etiqueta." >&2
exit 2
