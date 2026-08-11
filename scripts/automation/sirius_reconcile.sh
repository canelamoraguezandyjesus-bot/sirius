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
          | if length == 0 then empty else (last | \"\(.created_at) \(.id)\") end"
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
# Sustitucion de COMANDO, no de proceso. Con `mapfile < <(...)` el estado de
# salida se pierde: un 503 o un 403 dejaba la lista vacia, `overall_rc` en 0 y
# el resumen del job VACIO, byte a byte igual que un repositorio sano sin
# incidencias. Las cuatro pasadas diarias se apagaban con aspecto de exito, que
# es el peor desenlace para una red de seguridad: no detectar y ademas parecer
# que se ha comprobado. Auditoria de la PR #146.
if ! open_list="$(sirius_retry gh api -X GET "repos/${REPO}/issues" \
  -f state=open -f per_page=100 --paginate \
  --jq '.[] | select(has("pull_request") | not) | .number')"; then
  report ERROR "No se pudieron listar las incidencias abiertas de ${REPO}; esta pasada NO ha comprobado nada."
  exit 1
fi
# `<<<""` produce un elemento vacio que el guardia del bucle ya descarta.
mapfile -t open_issues <<<"$open_list"

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
  #
  # Con una excepcion, y no es cosmetica: `sirius:planned` +
  # `sirius:implement-requested` es el UNICO estado en que
  # `implement-requested` existe en produccion sana.
  # `sirius_validate_activation.sh` EXIGE `planned`, e
  # `implement-sirius-work.yml` retira las dos juntas al consumir el evento.
  # Contarlo como contradiccion acusaba de incoherente a una activacion normal
  # en cada pasada y —peor— el `continue` cortaba antes del bucle de estados,
  # asi que una activacion cuyo run muriera antes de consumir el evento NO
  # recibia aviso nunca: justo el caso que esta red existe para cubrir.
  # Auditoria de la PR #146.
  par_de_activacion="$(printf '%s\n' "$sirius_labels" | sort | tr '\n' ' ')"
  state_count="$(printf '%s\n' "$sirius_labels" | grep -c . || true)"
  if [ "${state_count:-0}" -gt 1 ] &&
     [ "$par_de_activacion" != "sirius:implement-requested sirius:planned " ]; then
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
    open_pr="" open_head="" open_draft=""
    for url in "${pr_urls[@]:-}"; do
      [ -z "${url:-}" ] && continue
      prnum="${url##*/}"
      # Se pide tambien `draft`: `advance-sirius-after-quality.yml` se NIEGA a
      # transicionar una PR en borrador, y `quality.yml` SI corre en borrador.
      # Sin mirarlo, el caso B hacia justo lo que el productor del evento habia
      # decidido no hacer —arrancar al revisor sobre algo que una persona dejo
      # aparcado a proposito—, contra los limites 2 y 5 del §9.1. Es el error de
      # siempre: decidir por otro sistema sin leer su predicado. Auditoria #146.
      prjson="$(sirius_retry gh api "repos/${REPO}/pulls/${prnum}" --jq '{state: .state, head: .head.sha, draft: (.draft // false)}' 2>/dev/null)" || continue
      if [ "$(printf '%s' "$prjson" | jq -r '.state')" = "open" ]; then
        if [ -n "$open_pr" ]; then open_pr="AMBIGUA"; break; fi
        open_pr="$prnum"
        open_head="$(printf '%s' "$prjson" | jq -r '.head')"
        open_draft="$(printf '%s' "$prjson" | jq -r '.draft')"
      fi
    done
    if [ -z "$open_pr" ]; then
      report AVISO "#${issue}: ci-pending sin PR abierta referenciada; requiere revisión humana."
    elif [ "$open_pr" = "AMBIGUA" ]; then
      report CONTRADICCION "#${issue}: ci-pending con varias PR abiertas referenciadas; requiere revisión humana."
    else
      conclusion="$(sirius_retry gh api "repos/${REPO}/commits/${open_head}/check-runs" \
        --jq '[.check_runs[] | select(.name == "quality")] | (first.conclusion // "none")' 2>/dev/null)" || conclusion="none"
      if [ "$open_draft" = "true" ]; then
        report AVISO "#${issue}: ci-pending con la PR #${open_pr} en borrador; el productor del evento tampoco la avanzaria, no se transiciona."
      elif [ "$conclusion" = "success" ]; then
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
        report AVISO "#${issue}: ci-pending con Quality '${conclusion}' para ${open_head}; aqui no se transiciona."
        # Solo `failure` y `timed_out` son corregibles: es lo que
        # `advance-sirius-after-quality.yml` manda al corrector, y cualquier otra
        # conclusion —`cancelled`, `skipped`, `neutral`, `stale`,
        # `action_required`— la manda a `failed-safely`. Avisar en todas
        # prescribiria una correccion sin causa tecnica demostrada y esquivaria
        # la parada segura de la maquina de estados. Hallazgo de Codex en #146.
        case "$conclusion" in
          failure|timed_out) avisar_ci_atascado="si" ;;
          *) report HUMANO "#${issue}: ci-pending con Quality '${conclusion}'; no es un fallo corregible, espera una accion humana." ;;
        esac
      fi
    fi

    # `sirius:ci-pending` tambien lo mueve SOLO la maquina, y su unico motor
    # —`advance-sirius-after-quality.yml`, con `on: workflow_run`— es un evento
    # de un solo uso: con Quality en rojo y ese run muerto no se aplica
    # `repair-requested`, luego no hay commit nuevo, luego Quality no vuelve a
    # correr y no hay `workflow_run` nuevo. Callejon cerrado.
    #
    # Era el unico estado de maquina que no recibia aviso en la incidencia,
    # mientras la cabecera de este guion afirmaba que todos lo reciben. No entra
    # en MACHINE_LABELS: el `continue` de arriba corta antes, y
    # `reactivation_labels` devolveria la propia etiqueta, que no dispara nada.
    # Auditoria de la PR #146.
    if [ "${avisar_ci_atascado:-}" = "si" ]; then
      marca_ci="$(label_applied_at "$REPO" "$issue" "sirius:ci-pending")"
      if [ -z "$marca_ci" ]; then
        report AVISO "#${issue}: ci-pending; no pude fechar el estado, no afirmo si esta atascado."
      else
        desde_ci="${marca_ci%% *}"
        evento_ci="${marca_ci##* }"
        epoch_ci="$(date -u -d "$desde_ci" +%s 2>/dev/null || true)"
        if [ -z "$epoch_ci" ]; then
          report AVISO "#${issue}: ci-pending; fecha ilegible (${desde_ci}), no afirmo antiguedad."
        else
          edad_ci=$(( ( $(_sirius_now) - epoch_ci ) / 60 ))
          if [ "$edad_ci" -lt "$STUCK_MINUTES" ]; then
            report EN-CURSO "#${issue}: ci-pending desde hace ${edad_ci} min; dentro de lo normal."
          else
            report ATASCO "#${issue}: ci-pending lleva ${edad_ci} min con Quality ya resuelto; se avisa en la incidencia."
            # La puerta del corrector EXIGE un bloque de observaciones
            # estructuradas: sin el se detiene con `sin-observaciones` y aplica
            # `failed-safely`. Prescribir `repair-requested` a ciegas mandaba a
            # una persona a hacer algo que en la mitad de los casos no arranca
            # nada — cuarta vez que escribo una receta sin leer las condiciones
            # de quien la recibe. Aqui no se adivina: se comprueba. Hallazgo de
            # Codex en la PR #146.
            # Se mira el volcado que este bucle YA leyo, en vez de pedir los
            # comentarios otra vez: la respuesta es la misma y ahorra una
            # llamada dentro del presupuesto de la pasada.
            #
            # Comprueba la PRESENCIA del bloque, que es un hecho verificable. Un
            # bloque presente pero mal formado seguiria sin servirle al
            # corrector; el aviso por eso afirma que existe, no que vaya a
            # funcionar seguro.
            if grep -q '^## OBSERVACIONES_ESTRUCTURADAS' "$comments_file"; then
              que_hacer="2. Esta incidencia ya tiene un bloque de observaciones estructuradas, que es lo que la puerta del corrector exige: quitar \`sirius:ci-pending\` y aplicar \`sirius:repair-requested\`."
            else
              que_hacer="2. Esta incidencia **no** tiene observaciones estructuradas, asi que aplicar \`sirius:repair-requested\` no arrancaria nada: el corrector se detendria con \`sin-observaciones\`. Hace falta una ronda de revision que las publique, o resolver el fallo de Quality a mano."
            fi
            marker_ci="<!-- sirius-stuck:sirius:ci-pending:${evento_ci} -->"
            ci_file="$(mktemp)"
            printf '%s\n\n%s\n\n%s\n\n%s\n\n%s\n%s\n\n%s\n' \
              "$marker_ci" \
              "🕒 **Este bloque lleva ${edad_ci} minutos sin avanzar**" \
              "Sigue en \`sirius:ci-pending\` desde ${desde_ci}. Quality ya termino en \`${conclusion}\` para \`${open_head}\`, asi que no va a volver a correr por su cuenta: sin un commit nuevo no hay evento nuevo, y sin evento nuevo nada mueve este estado." \
              "El reconciliador **no ha reparado nada**. Transicionar desde aqui seria decidir que la correccion procede, y eso no lo puede saber." \
              "1. Mirar en Actions por que fallo Quality en la PR #${open_pr}." \
              "${que_hacer}" \
              "Si tras eso el bloque sigue sin arrancar, la ejecucion de Actions dice por que: es el unico sitio donde consta siempre." >"$ci_file"
            if sirius_comment_once "$REPO" "$issue" "$marker_ci" "$ci_file"; then
              report AVISADO "#${issue}: aviso de atasco publicado (o ya estaba)."
            else
              report ERROR "#${issue}: no se pudo publicar el aviso de atasco; reintentable."
              overall_rc=1
            fi
            rm -f "$ci_file"
          fi
        fi
      fi
      unset avisar_ci_atascado
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
    # SIETE conversiones para SIETE argumentos. `printf` REUTILIZA el formato
    # cuando sobran argumentos, asi que con seis la ultima linea salia pegada
    # a la anterior —en Markdown eso la mete DENTRO del punto 2— y detras se
    # colaban diez lineas en blanco. Auditoria de la PR #146.
    printf '%s\n\n%s\n\n%s\n\n%s\n\n%s\n%s\n\n%s\n' \
      "$marker" \
      "🕒 **Este bloque lleva ${edad_min} minutos sin avanzar**" \
      "Sigue en \`${lbl}\` desde ${desde}. Ese estado solo lo mueve la automatización, y una etiqueta ya aplicada no vuelve a disparar \`issues: labeled\`: si la ejecución que debía moverlo murió, no hay nada que lo mueva." \
      "El reconciliador **no ha reparado nada**. No puede saber si esa ejecución murió o sigue viva, y decidirlo desde fuera sería inventárselo." \
      "1. Mirar en Actions si queda alguna ejecución viva para esta incidencia." \
      "2. Si no queda ninguna, ${como_hacerlo}" \
      "Si tras eso el bloque sigue sin arrancar, la ejecución de Actions dice por qué: es el único sitio donde consta siempre." >"$stuck_file"
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
