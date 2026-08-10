#!/usr/bin/env bash
# Sirius — reconciliador de estados de automatización.
#
# Detecta incidencias de trabajo atascadas y las repara SOLO cuando el estado
# correcto es inequívoco; todo lo demás se informa sin tocar nada.
#
# Se ejecuta bajo demanda (workflow_dispatch) y, desde la incidencia #138,
# también de forma periódica. El contrato v1.6 §9.1 permite esa excepción con
# una frontera precisa: la vigilancia periódica sigue prohibida como MOTOR del
# flujo —no inicia bloques, no avanza un ciclo sano, no fusiona— y solo se
# admite como red de seguridad que observa estados que ningún evento puede ya
# revivir.
#
# Casos que corrige (inequívocos):
#   A. Incidencia ABIERTA con marcador `<!-- sirius-completed:SHA -->` (no
#      ambiguo): la PR se fusionó y el cierre quedó a medias (incidencia #50).
#      -> garantiza `sirius:completed`, retira etiquetas transitorias y cierra.
#      No publica comentarios nuevos.
#   B. Incidencia en `sirius:ci-pending` cuya única PR abierta referenciada tiene
#      Quality en verde para su head actual: la transición de avance se perdió.
#      -> reintenta la transición estándar (idempotente, via sirius_transition).
#
# Casos que solo informa: eventos sin consumir, estados en curso, decisiones
# humanas pendientes, contradicciones de etiquetas y ci-pending sin CI verde.
#
# De esos, los estados que solo la MAQUINA puede mover se informan además con un
# comentario en la propia incidencia cuando llevan demasiado tiempo puestos
# (incidencia #138). Motivo: `issues: labeled` no vuelve a dispararse con una
# etiqueta ya aplicada, así que si la ejecución que debía moverlo murió, nada lo
# moverá nunca; y un resumen de job que nadie abre no es una detección.
#
# Nunca hace merge, nunca inicia bloques y nunca decide producto.
#
# Uso: sirius_reconcile.sh <owner/repo>

set -uo pipefail

SIRIUS_RECONCILE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
# shellcheck source=scripts/automation/sirius_issue.sh
source "${SIRIUS_RECONCILE_DIR}/sirius_issue.sh"

# Aplica una transición cuya etiqueta debe DESPERTAR a otro workflow (aquí,
# ci-pending -> review-requested): si hay un token de identidad real disponible
# en SIRIUS_TRIGGER_TOKEN, la escribe con él (en una subshell) para que el
# `issues: labeled` no lo suprima la regla anti-recursión del GITHUB_TOKEN; las
# lecturas de este script (incidencias, PRs, check-runs) siguen con GH_TOKEN. Si
# la variable no está definida, cae al GH_TOKEN vigente (comportamiento previo).
trigger_transition() {
  (
    [ -n "${SIRIUS_TRIGGER_TOKEN:-}" ] && export GH_TOKEN="$SIRIUS_TRIGGER_TOKEN"
    sirius_transition "$@"
  )
}

# label_applied_at <repo> <issue> <etiqueta> — imprime "<fecha ISO> <id evento>"
# de la ÚLTIMA vez que se aplicó esa etiqueta, o NADA si no se puede saber.
#
# La fecha la da GitHub, que es quien la posee. Deducirla de `updated_at` de la
# incidencia sería reconstruir desde fuera un hecho ajeno —cualquier comentario
# la mueve— y ese es exactamente el error que abrió esta incidencia. Si la
# lectura falla, no se imprime nada: sin dato no se afirma antigüedad.
label_applied_at() {
  # `-X GET` es OBLIGATORIO. `gh api` usa GET por defecto pero cambia a POST en
  # cuanto se le añade un parámetro con `-f`, y `/issues/{n}/events` solo
  # existe en GET: sin esto TODA lectura fallaba, `marca` salía vacía y la rama
  # de fallo seguro impedía publicar un solo aviso. La detección entera habría
  # estado muerta en producción sin que ninguna prueba lo notara. Hallazgo P1
  # de Codex en la PR #143; la otra llamada paginada de este script ya lo hacía
  # bien, así que la regla estaba escrita aquí al lado.
  #
  # `--slurp` es igual de obligatorio. Con `--paginate` a secas, `gh` emite un
  # array JSON POR PÁGINA y `--jq` se aplica a cada uno por separado: `last`
  # daría el último de CADA página, una línea por página, y el llamador acabaría
  # cogiendo la fecha de una y el id de otra. Con `--slurp` llega un solo array
  # de páginas, y `add` las aplana en una sola lista. Hallazgo P2 de Codex.
  sirius_retry gh api -X GET "repos/${1}/issues/${2}/events" -f per_page=100 \
    --paginate --slurp \
    --jq "(add // []) | [.[] | select(.event == \"labeled\" and .label.name == \"${3}\")] \
          | if length == 0 then empty else (last | \"\(.created_at) \(.id)\") end" \
    2>/dev/null
}

# reactivation_labels <etiqueta> — las etiquetas que hay que APLICAR, en orden,
# para que el ciclo vuelva a arrancar desde ese estado.
#
# Segunda ronda del mismo defecto, así que aquí se cambia el enfoque en vez de
# poner otro parche (regla de las dos rondas, ADR-001).
#
#   Ronda 1: el aviso decía «quita `sirius:repairing` y vuelve a ponerla». Eso
#   dispara `issues: labeled` pero no pasa el `if:` del workflow.
#   Ronda 2: proponer solo la etiqueta del `if:` TAMPOCO basta para
#   `implementing`. El paso «Consumir el evento» de `implement-sirius-work.yml`
#   retira `sirius:implement-requested` Y `sirius:planned`, y
#   `sirius_validate_activation.sh` exige `planned`: sin ella rechaza la
#   activación y retira la etiqueta otra vez.
#
# La raíz de las dos es la misma: el reconciliador estaba reconstruyendo desde
# fuera las condiciones de admisión de otro sistema. La regla que sí se sostiene
# —y que las pruebas leen de los propios workflows— es que **hay que reponer lo
# que el paso de consumo retiró**, con la etiqueta disparadora en último lugar
# para que la puerta encuentre el resto ya puesto.
reactivation_labels() {
  case "$1" in
    sirius:implementing) printf 'sirius:planned sirius:implement-requested' ;;
    sirius:reviewing)    printf 'sirius:review-requested' ;;
    sirius:repairing)    printf 'sirius:repair-requested' ;;
    *)                   printf '%s' "$1" ;;
  esac
}

# stale_minutes <repo> <issue> <etiqueta> — minutos que la etiqueta lleva
# puesta, o nada si no se puede saber. Sin dato no se afirma antigüedad.
stale_minutes() {
  local marca desde epoch
  marca="$(label_applied_at "$1" "$2" "$3")"
  [ -n "$marca" ] || return 0
  desde="${marca%% *}"
  epoch="$(date -u -d "$desde" +%s 2>/dev/null || true)"
  [ -n "$epoch" ] || return 0
  printf '%s' $(( ( $(_sirius_now) - epoch ) / 60 ))
}

REPO="${1:?uso: sirius_reconcile.sh <owner/repo>}"

STATE_LABELS="sirius:planned sirius:implement-requested sirius:implementing sirius:ci-pending sirius:review-requested sirius:reviewing sirius:repair-requested sirius:repairing sirius:ready-for-merge sirius:blocked-decision sirius:failed-safely sirius:completed"

# Estados que SOLO puede mover la máquina. Si uno se queda puesto, nada lo va a
# mover: la etiqueta ya está aplicada y `issues: labeled` no vuelve a disparar.
MACHINE_LABELS="sirius:implement-requested sirius:review-requested sirius:repair-requested sirius:implementing sirius:reviewing sirius:repairing"

# Minutos a partir de los cuales un estado de máquina se declara atascado. Tiene
# que superar con holgura el job más largo de la automatización —hoy el revisor,
# 85 minutos— más su cola; por debajo de eso, un ciclo perfectamente vivo se
# denunciaría como muerto. RECON-STUCK-006 ata este número a los
# `timeout-minutes` reales de los workflows: escrito a mano se queda viejo solo
# (ADR-003).
STUCK_MINUTES="${SIRIUS_STUCK_MINUTES:-180}"
TRANSIENT_CSV="sirius:planned,sirius:implement-requested,sirius:implementing,sirius:ci-pending,sirius:review-requested,sirius:reviewing,sirius:repair-requested,sirius:repairing,sirius:ready-for-merge,sirius:blocked-decision,sirius:failed-safely"

report() {
  # report <nivel> <mensaje> — stdout + resumen del job si existe.
  echo "[$1] $2"
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    echo "- **$1** $2" >>"$GITHUB_STEP_SUMMARY"
  fi
}

overall_rc=0

# Incidencias abiertas (se excluyen PRs, que el endpoint /issues incluye).
mapfile -t open_issues < <(
  sirius_retry gh api -X GET "repos/${REPO}/issues" \
    -f state=open -f per_page=100 --paginate \
    --jq '.[] | select(has("pull_request") | not) | .number'
)

for issue in "${open_issues[@]:-}"; do
  [ -z "${issue:-}" ] && continue

  labels="$(sirius_retry gh api "repos/${REPO}/issues/${issue}/labels" --jq '.[].name' 2>/dev/null)" || {
    report AVISO "No se pudieron leer las etiquetas de #${issue}; se omite."
    continue
  }
  sirius_labels="$(printf '%s\n' "$labels" | grep '^sirius:' || true)"

  comments_file="$(mktemp)"
  body_file="$(mktemp)"
  sirius_read_issue_comments "$REPO" "$issue" >"$comments_file" 2>/dev/null || true
  sirius_read_issue_body "$REPO" "$issue" >"$body_file" 2>/dev/null || true

  completed_marker="$(grep -oE '<!-- sirius-completed:[0-9a-fA-F]{7,40} -->' "$comments_file" | head -n 1 || true)"

  # --- Caso A: fusionada y completada a medias (marcador sin cierre) ----------
  if [ -n "$completed_marker" ]; then
    report ATASCO "#${issue}: abierta con marcador de completado (${completed_marker}); se repara el cierre."
    fixed=1
    sirius_ensure_label "$REPO" "sirius:completed" "006B75" "Estado terminal: bloque fusionado y cerrado" || fixed=0
    if [ "$fixed" -eq 1 ]; then
      removes_arr=()
      IFS=',' read -r -a removes_arr <<<"$TRANSIENT_CSV"
      sirius_set_issue_labels "$REPO" "$issue" "sirius:completed" "${removes_arr[@]}" || fixed=0
    fi
    if [ "$fixed" -eq 1 ]; then
      sirius_close_issue "$REPO" "$issue" || fixed=0
    fi
    if [ "$fixed" -eq 1 ]; then
      report CORREGIDO "#${issue}: etiquetas saneadas y cerrada como completada (sin comentarios nuevos)."
    else
      report ERROR "#${issue}: no se pudo completar el cierre; reintentable."
      overall_rc=1
    fi
    rm -f "$comments_file" "$body_file"
    continue
  fi

  # --- Contradicción: más de una etiqueta de estado sirius -------------------
  state_count="$(printf '%s\n' "$sirius_labels" | grep -c . || true)"
  if [ "${state_count:-0}" -gt 1 ]; then
    report CONTRADICCION "#${issue}: varias etiquetas sirius simultáneas ($(printf '%s' "$sirius_labels" | tr '\n' ' ')); requiere revisión humana."
    rm -f "$comments_file" "$body_file"
    continue
  fi

  # --- Caso B: ci-pending con Quality ya resuelto -----------------------------
  if printf '%s\n' "$sirius_labels" | grep -Fxq "sirius:ci-pending"; then
    # Antes de reparar hay que saber que la transición se PERDIÓ, no que está
    # en camino. Quality acaba de ponerse verde y `advance-sirius-after-quality`
    # puede estar encolado o corriendo ahora mismo: reparar en esa ventana no es
    # arreglar un estado roto, es adelantarse al productor del evento y avanzar
    # un ciclo sano. Eso viola los límites 2 y 5 del §9.1 del contrato, que esta
    # misma PR declara. Hallazgo P1 de Codex en la PR #143.
    #
    # Desde fuera no hay forma de distinguir "perdido" de "en vuelo" salvo por
    # el tiempo, así que se exige la misma antigüedad que para declarar un
    # atasco. Se aplica también a las ejecuciones manuales: la distinción no
    # depende de quién dispare, sino de si el productor tuvo tiempo de actuar.
    edad_ci="$(stale_minutes "$REPO" "$issue" "sirius:ci-pending")"
    if [ -z "$edad_ci" ]; then
      report AVISO "#${issue}: ci-pending; no pude fechar el estado, así que no reparo a ciegas."
      rm -f "$comments_file" "$body_file"
      continue
    fi
    if [ "$edad_ci" -lt "$STUCK_MINUTES" ]; then
      report EN-CURSO "#${issue}: ci-pending desde hace ${edad_ci} min; el flujo por eventos aún puede avanzarlo."
      rm -f "$comments_file" "$body_file"
      continue
    fi
    mapfile -t pr_urls < <(
      cat "$body_file" "$comments_file" \
        | grep -oE "https://github\.com/${REPO}/pull/[0-9]+" | sort -u
    )
    open_pr="" open_head=""
    for url in "${pr_urls[@]:-}"; do
      [ -z "${url:-}" ] && continue
      prnum="${url##*/}"
      prjson="$(sirius_retry gh api "repos/${REPO}/pulls/${prnum}" --jq '{state: .state, head: .head.sha}' 2>/dev/null)" || continue
      if [ "$(printf '%s' "$prjson" | jq -r '.state')" = "open" ]; then
        if [ -n "$open_pr" ]; then open_pr="AMBIGUA"; break; fi
        open_pr="$prnum"
        open_head="$(printf '%s' "$prjson" | jq -r '.head')"
      fi
    done
    if [ -z "$open_pr" ]; then
      report AVISO "#${issue}: ci-pending sin PR abierta referenciada; requiere revisión humana."
    elif [ "$open_pr" = "AMBIGUA" ]; then
      report CONTRADICCION "#${issue}: ci-pending con varias PR abiertas referenciadas; requiere revisión humana."
    else
      conclusion="$(sirius_retry gh api "repos/${REPO}/commits/${open_head}/check-runs" \
        --jq '[.check_runs[] | select(.name == "quality")] | (first.conclusion // "none")' 2>/dev/null)" || conclusion="none"
      if [ "$conclusion" = "success" ]; then
        report ATASCO "#${issue}: ci-pending pero Quality esta en verde para ${open_head}; se reintenta la transicion."
        marker="<!-- sirius-quality:${open_head}:success -->"
        tfile="$(mktemp)"
        printf '%s\n\n%s\n\n%s\n%s\n%s\n%s\n' \
          "$marker" \
          "## QUALITY_SUCCESS" \
          "- PR: https://github.com/${REPO}/pull/${open_pr}" \
          "- Head SHA: \`${open_head}\`" \
          "- Resultado: \`success\` (reconciliado)" \
          "- Siguiente transicion: revision independiente." >"$tfile"
        if trigger_transition "$REPO" "$issue" "$marker" "$tfile" \
          "sirius:review-requested" "8250DF" "Evento consumible: iniciar revisión independiente" \
          "noclose" "sirius:ci-pending"; then
          report CORREGIDO "#${issue}: transicion ci-pending -> review-requested reconciliada."
        else
          report ERROR "#${issue}: la transicion reconciliadora fallo; reintentable."
          overall_rc=1
        fi
        rm -f "$tfile"
      elif [ "$conclusion" = "none" ]; then
        report AVISO "#${issue}: ci-pending y Quality aun sin resultado para ${open_head}; nada que reconciliar."
      else
        report AVISO "#${issue}: ci-pending con Quality '${conclusion}' para ${open_head}; el workflow de avance debe gestionarlo (no se transiciona aqui)."
      fi
    fi
    rm -f "$comments_file" "$body_file"
    continue
  fi

  # --- Solo informe -----------------------------------------------------------
  #
  # Aquí abajo el reconciliador NO repara: informa. Lo que sí hace desde la
  # incidencia #138 es hacer VISIBLE el informe cuando un estado que solo la
  # máquina puede mover lleva más de `STUCK_MINUTES` puesto.
  for lbl in $MACHINE_LABELS; do
    printf '%s\n' "$sirius_labels" | grep -Fxq "$lbl" || continue
    case "$lbl" in
      *-requested) nivel=PENDIENTE; que="evento sin consumir";;
      *)           nivel=EN-CURSO;  que="ejecución en curso o muerta";;
    esac

    marca="$(label_applied_at "$REPO" "$issue" "$lbl")"
    if [ -z "$marca" ]; then
      # Sin fecha no se afirma antigüedad. Interpretar una lectura fallida como
      # "lleva mucho" publicaría una acusación falsa en la incidencia.
      report AVISO "#${issue}: ${lbl} (${que}); no pude fechar el estado, así que no digo si está atascado."
      continue
    fi
    desde="${marca%% *}"
    evento_id="${marca##* }"
    desde_epoch="$(date -u -d "$desde" +%s 2>/dev/null || true)"
    if [ -z "$desde_epoch" ]; then
      report AVISO "#${issue}: ${lbl} (${que}); fecha ilegible (${desde}), no afirmo antigüedad."
      continue
    fi
    edad_min=$(( ( $(_sirius_now) - desde_epoch ) / 60 ))

    if [ "$edad_min" -lt "$STUCK_MINUTES" ]; then
      report "$nivel" "#${issue}: ${lbl} (${que}) desde hace ${edad_min} min; dentro de lo normal."
      continue
    fi

    report ATASCO "#${issue}: ${lbl} lleva ${edad_min} min sin avanzar; se avisa en la incidencia."
    # Marcador por APLICACIÓN de etiqueta, no por etiqueta: si el estado se
    # vuelve a poner más tarde es un atasco nuevo y merece aviso nuevo, pero la
    # misma aplicación no puede avisar en cada pasada programada.
    reactivar="$(reactivation_labels "$lbl")"
    if [ "$reactivar" = "$lbl" ]; then
      como_hacerlo="quitar \`${lbl}\` y volver a ponerla: es la misma etiqueta."
    else
      # Dentro de comillas SIMPLES la tilde invertida es literal: escaparla
      # publica el backslash tal cual y el aviso sale con `\`etiqueta\`` en vez
      # de código. Las otras líneas van entre comillas DOBLES, donde sí hay que
      # escaparla; el mismo carácter necesita cosas distintas en cada contexto.
      lista="$(printf '`%s`, ' $reactivar)"
      como_hacerlo="quitar \`${lbl}\` y aplicar, en este orden: ${lista%, }."
    fi
    marker="<!-- sirius-stuck:${lbl}:${evento_id} -->"
    stuck_file="$(mktemp)"
    printf '%s\n\n%s\n\n%s\n\n%s\n\n%s\n%s\n' \
      "$marker" \
      "🕒 **Este bloque lleva ${edad_min} minutos sin avanzar**" \
      "Sigue en \`${lbl}\` desde ${desde}. Ese estado solo lo mueve la automatización, y una etiqueta ya aplicada no vuelve a disparar \`issues: labeled\`: si la ejecución que debía moverlo murió, no hay nada que lo mueva." \
      "El reconciliador **no ha reparado nada**. No puede saber si esa ejecución murió o sigue viva, y decidirlo desde fuera sería inventárselo." \
      "1. Mirar en Actions si queda alguna ejecución viva para esta incidencia." \
      "2. Si no queda ninguna, ${como_hacerlo}" \
      "3. Si aun así faltara alguna condición, la puerta de activación lo dirá en un comentario aquí mismo y retirará la etiqueta. No se queda en silencio, así que no hace falta acertar a la primera." >"$stuck_file"
    if sirius_comment_once "$REPO" "$issue" "$marker" "$stuck_file"; then
      report AVISADO "#${issue}: aviso de atasco publicado (o ya estaba)."
    else
      report ERROR "#${issue}: no se pudo publicar el aviso de atasco; reintentable."
      overall_rc=1
    fi
    rm -f "$stuck_file"
  done
  for lbl in sirius:blocked-decision sirius:failed-safely sirius:ready-for-merge; do
    if printf '%s\n' "$sirius_labels" | grep -Fxq "$lbl"; then
      report HUMANO "#${issue}: ${lbl}; espera una accion humana."
    fi
  done
  rm -f "$comments_file" "$body_file"
done

exit "$overall_rc"
