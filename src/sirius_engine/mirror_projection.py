"""Proyección del espejo de solo lectura de la vía GitHub (A3, incidencia #193).

Interpreta lo que ya devuelve :mod:`sirius_engine.ports.github_mirror` -
metadatos, cuerpo, comentarios, run de Actions- y produce las proyecciones NO
autoritativas de :mod:`sirius_engine.domain.mirror`.

Reutiliza, en vez de reinventar, la semántica de marcadores que
``scripts/automation/sirius_issue.sh`` y ``sirius_convergence.py`` llevan
meses probando en producción (incidencia #193, «Método: reutilizar la
semántica ya probada, no reinventarla»):

- ``sirius-round``/``RONDA_HALLAZGOS`` y la racha de fallos de Quality
  (``sirius-quality``) se interpretan con ``parse_round_records``,
  ``ci_failure_streak`` y ``history_after_last_resume`` de
  :mod:`sirius_engine.round_history` -las mismas funciones que gobiernan la
  convergencia real de ``scripts/automation/sirius_convergence.py``, no una
  segunda copia que podría divergir: ``scripts/automation/round_history.py``
  es un enlace simbólico a este módulo, no una copia-. Antes de H-13
  (incidencia #275) este módulo insertaba ``scripts/`` en ``sys.path`` e
  importaba el script de automatización directamente; eso funcionaba en el
  checkout de desarrollo pero rompía con ``ModuleNotFoundError`` en cuanto
  alguien llamaba a la proyección desde una instalación real del paquete,
  porque ``scripts/`` no viaja en el wheel (incidencia #272). Importar el
  módulo compartido -que sí vive dentro de ``sirius_engine``- de forma
  normal, sin ningún truco de ``sys.path``, es lo que arregla eso.
- El filtro de autor de confianza (``OWNER`` o ``github-actions[bot]``) es el
  MISMO predicado booleano que ``SIRIUS_TRUSTED_AUTHOR_JQ`` en
  ``sirius_issue.sh``, trasladado a Python porque no existe una forma de
  *importar* jq: es una referencia de semántica, no una reinterpretación -un
  comentario cuenta como confiable si y solo si cumple exactamente la misma
  condición en las dos implementaciones.
- Los marcadores ``sirius-verdict``, ``Head/Merge SHA`` y ``PR abierta:`` no
  tienen módulo Python de referencia (viven como `sed`/`grep` en bash), así
  que aquí se interpretan con una expresión regular equivalente, documentada
  junto al literal bash que reproduce.

Ninguna función de este módulo escribe en GitHub ni llama a la red: todas
reciben ya los datos leídos (vía el puerto) y son deterministas -misma
entrada, misma salida- para que la reconstrucción del ciclo de una
incidencia sea reproducible (requisito 5).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime

from sirius_engine.domain.mirror import (
    EspejoIlegibleError,
    EstadoAcreditado,
    EventoQuality,
    FormaDePermiso,
    MirroredRun,
    MirroredWorkItem,
    OrigenLectura,
    PermisoDeReanudacion,
    RondaHallazgos,
    VeredictoPublicado,
)
from sirius_engine.domain.work_item import WorkItemPhase, WorkItemState
from sirius_engine.ports.github_mirror import (
    Comentario,
    ContenidoConAutor,
    CuerpoIncidencia,
    GitHubMirrorPort,
    LecturaComentarios,
    LecturaCuerpo,
    LecturaEstado,
    LecturaMetadatos,
    LecturaRunActions,
)
from sirius_engine.round_history import (
    ci_failure_streak,
    history_after_last_resume,
    parse_round_records,
)

# --- Filtro de autor de confianza ------------------------------------------
#
# Mismo predicado que SIRIUS_TRUSTED_AUTHOR_JQ en scripts/automation/sirius_issue.sh:
#   select(.author_association == "OWNER" or (.user.login // "") == "github-actions[bot]")
_BOT_LOGIN = "github-actions[bot]"


def es_autor_de_confianza(contenido: ContenidoConAutor) -> bool:
    """Compartido con :mod:`sirius_engine.context_recall`: un único filtro de confianza.

    Toma cualquier :class:`ContenidoConAutor` -un :class:`Comentario` o el
    :class:`CuerpoIncidencia`- y no un ``Comentario`` concreto, para que el
    cuerpo de la incidencia pase por ESTE predicado y no por otro parecido.
    Cuando aceptaba solo comentarios, el cuerpo no tenía forma de llegar aquí
    y se concatenaba sin filtrar (defecto H-1, incidencia #215, ADR-051).
    """
    return contenido.autor_asociacion == "OWNER" or contenido.autor_login == _BOT_LOGIN


def es_del_propietario(contenido: ContenidoConAutor) -> bool:
    """La mitad ESTRICTA del filtro de confianza: solo el propietario, no el bot.

    Mismo `author_association == "OWNER"` con el que
    `.github/workflows/resume-sirius-on-command.yml` filtra el evento antes de
    invocar a `sirius_resume_on_command.sh`. Se separa de
    :func:`es_autor_de_confianza` porque hay exactamente un hecho del historial
    que no puede aceptarse del bot: la orden `continua`. Un marcador es un
    recibo que la automatización emite; la orden es la palabra del propietario,
    y dejar que el bot la escribiera sería dejar que la automatización se diera
    permiso a sí misma (ADR-147).
    """
    return contenido.autor_asociacion == "OWNER"


# --- Marcadores sin módulo Python de referencia -----------------------------
#
# Espejo de `sirius_extract_sha` (sirius_issue.sh): primer SHA de 7-40 hex tras
# "Head SHA:"/"Merge SHA:", con backtick opcional.
_SHA_MARKER_RE = re.compile(r"(?:Head|Merge)\s+SHA:\s*`?([0-9a-fA-F]{7,40})")

# Literal publicado por el runner implementador: "PR abierta: <URL>". Exige un
# esquema http(s) real -no basta "PR abierta:" a secas- porque la incidencia
# #186 real trae un contraejemplo: un comentario de precheck que CITA el
# marcador como texto («Comentario 'PR abierta: <URL>' publicado…») sin
# publicar ninguno. Sin esta exigencia, esa cita se leería como la URL
# literal "<URL>'" -divergencia silenciosa exactamente del tipo que este
# bloque existe para evitar.
_PR_ABIERTA_RE = re.compile(r"PR abierta:\s*(https?://\S+)")

# Mismo marcador que publica el ciclo Quality
# (`round_history.CI_FAILURE_MARKER_RE`/`CI_SUCCESS_MARKER_RE`), pero
# capturando head Y conclusión de CUALQUIER resultado (no solo si cuenta para
# la racha): a diferencia de ``round_history.ci_failure_streak``, que
# reduce el historial a un contador, esta expresión sirve para reconstruir la
# secuencia completa de eventos observados -la usa el espejo de solo lectura
# (A3) para no perder los fallos que un éxito posterior ya cerró para la
# racha pero que siguen siendo hechos ocurridos en el ciclo-. Vive aquí, y no
# en sirius_engine.round_history, porque esta expresión no gobierna ninguna
# decisión de convergencia real, solo la reconstrucción de solo lectura
# (incidencia #193).
_QUALITY_EVENT_RE = re.compile(
    r"<!--\s*sirius-quality:([0-9a-fA-F]+):(failure|timed_out|success)\s*-->"
)

# "<!-- sirius-verdict:<rol>:<resto> -->" — el número de campos tras el rol
# varía (precheck lleva un motivo y una etiqueta de ejecución de más), así que
# se captura todo el contenido y se separa por ":" en vez de fijar un número
# de grupos.
_VERDICT_MARKER_RE = re.compile(r"<!--\s*sirius-verdict:([^>]*?)\s*-->")

# Cuerpo exacto que publica toda parada segura que aplica `sirius:failed-safely`
# (incidencia #529, ampliado en la #530 tras el hallazgo CODEX-001):
#   <!-- sirius-verdict:<rol>:<verdict>:<SIRIUS_RUN_TAG> -->
#
#   🔴 **Me he detenido de forma segura**
#
#   <diagnóstico>
#
# `<verdict>` no es siempre `FAILED_SAFELY`/`USAGE_LIMIT_REACHED` -el veredicto
# que publica el propio agente-: las puertas deterministas de
# `review-sirius-work.yml` (`stop_gate`), `repair-sirius-work.yml` (`sin_tiempo`
# y las paradas de `parada ... "sirius:failed-safely" ...`) y
# `sirius_apply_verdict.sh` (`stop_safely`) publican en su lugar
# `precheck:<motivo>[:<run>]` y aplican EXACTAMENTE la misma etiqueta con el
# mismo cuerpo. Antes de esta corrección esta expresión solo reconocía el
# primer caso, así que el diagnóstico de cualquier parada de puerta se leía
# como `None` (defecto CODEX-001, PR #530).
#
# El resto de paradas `precheck` que existen en el repositorio -las de
# `convergencia-<motivo>` y `head-movido-tras-ci`, que aplican
# `sirius:blocked-decision`/`sirius:ci-pending`- no se aceptan: publican una
# cabecera distinta (`🟡 ...`), así que el filtro de la cabecera fija que
# sigue ya las excluye sin necesidad de enumerarlas aquí. Los comentarios de
# notificación de `notify-sirius-state.yml` tampoco entran: usan el marcador
# `sirius-notification:`, no `sirius-verdict:`, así que no coinciden con este
# prefijo aunque citen la misma cabecera.
# Se captura solo el diagnóstico -lo que sigue a la cabecera fija-, no el
# marcador ni el emoji: eso ya lo interpreta `_interpretar_veredictos`.
_DIAGNOSTICO_FALLO_RE = re.compile(
    r"<!--\s*sirius-verdict:[^:]+:(?:FAILED_SAFELY|USAGE_LIMIT_REACHED|precheck):[^>]*-->"
    r"\s*\n+.*?Me he detenido de forma segura.*?\n+(.*)",
    re.DOTALL,
)

# Los tres marcadores que `sirius_resume_on_command.sh` publica ANTES de
# reponer la etiqueta activa (líneas 297-324 de ese guion), en ese orden
# exacto por diseño: el permiso escrito siempre precede a la etiqueta que
# autoriza (CODEX-001, ronda 4, PR #530). `sirius-convergence-reset` y
# `sirius-resume-stop` llevan un SHA de head; `sirius-restart-sin-pr` lleva
# `<incidencia>:<run>-<intento>` porque una parada sin PR no tiene head sobre
# el que continuar (comentario del propio guion, líneas 305-309).
#
# Su sola PRESENCIA en el historial no basta -eso bastaba en la versión de la
# ronda 4 y reabría exactamente lo que esa ronda quería cerrar (hallazgo
# CLAUDE-REVISOR-001/CODEX-002, ronda 5, PR #530): una incidencia que se para,
# se reanuda, y vuelve a pararse por algo NUEVO y sin relación seguía leyendo
# el marcador de la reanudación anterior -ya consumida- como si autorizara
# también la parada posterior. `_interpretar_reanudacion_publicada` usa este
# marcador junto con `_STOP_MARKER_RE` de abajo para exigir que el más
# reciente de los dos, en el historial de confianza, sea el de reanudación.
_RESUME_MARKER_RE = re.compile(
    r"<!--\s*sirius-(?:resume-stop|convergence-reset|restart-sin-pr):[^>]*-->"
)

# El marcador que publica CUALQUIER parada -de veredicto de rol o de puerta
# determinista- que deja la incidencia en `sirius:failed-safely` o
# `sirius:blocked-decision`: los mismos cuatro valores de veredicto que
# `sirius_resume_on_command.sh` lee para decidir a qué fase volver
# (`FAILED_SAFELY`/`USAGE_LIMIT_REACHED`/`precheck`/`blocked`). Deliberadamente
# NO incluye `approved`/`changes`/`CHECKS_UNRELATED` -esos veredictos no paran
# el ciclo, así que no cuentan como "parada vigente" a efectos de anclar la
# reanudación-.
#
# `precheck` en sí no basta: la rama `head-movido-tras-ci` de
# `repair-sirius-work.yml` (líneas 425-433) publica exactamente ese verdict
# -`<!-- sirius-verdict:corrector:precheck:head-movido-tras-ci -->`- y
# devuelve la incidencia a `sirius:ci-pending`, no a `failed-safely` ni a
# `blocked-decision`: no es una parada, es un evento consumible que sigue el
# camino normal. Tratarlo como parada hacía que una reanudación publicada
# ANTES de esa rama -que no cerró nada, porque no había nada que cerrar- se
# leyera como ya consumida por ella (CODEX-001, ronda 6, PR #530). El resto de
# `precheck` (`puerta-sin-tiempo`, `historial-ilegible`, `ronda-innumerable`,
# `convergencia-<motivo>`, `observaciones-ilegibles`, `sin-observaciones`,
# `decisiones-ilegibles`, y los de `sirius_apply_verdict.sh`/
# `review-sirius-work.yml`) sí aplican `failed-safely`/`blocked-decision` y
# siguen contando como parada vigente.
_STOP_MARKER_RE = re.compile(
    r"<!--\s*sirius-verdict:[^:]+:"
    r"(?:FAILED_SAFELY|USAGE_LIMIT_REACHED|blocked"
    r"|precheck(?!:head-movido-tras-ci\s*-->))"
    r"(?::[^>]*)?-->"
)

# Marcador que `notify-sirius-state.yml` publica cada vez que se APLICA una de
# las seis etiquetas que vigila (`implementing`, `repair-requested`,
# `ready-for-merge`, `blocked-decision`, `failed-safely`, `completed`):
#
#   marker="<!-- sirius-notification:${STATE_LABEL}:${head_sha} -->"
#
# A diferencia de las etiquetas vigentes -que son la FOTO de ahora mismo-,
# estos marcadores son el CAMINO: cada uno prueba, fechado y por escrito, que
# la incidencia estuvo en ese estado. `head_sha` vale `no-head` cuando la
# incidencia todavía no tenía ningún SHA publicado (mismo guion), así que aquí
# se captura tal cual, sin exigir forma de SHA.
#
# El guion deduplica por marcador COMPLETO -etiqueta y head-, así que la
# secuencia no es exhaustiva: una etiqueta repuesta sobre el mismo head no
# publica un segundo marcador. Eso la hace incompleta, nunca falsa; el
# recorrido acreditado (ADR-147) solo necesita que lo que diga haya ocurrido,
# no que diga todo lo que ocurrió.
_NOTIFICATION_MARKER_RE = re.compile(r"<!--\s*sirius-notification:(sirius:[a-z-]+):([^\s>]*)\s*-->")

# La orden exacta del propietario que `sirius_resume_on_command.sh` acepta como
# permiso para reanudar (líneas 72-89 de ese guion), reproducida aquí paso a
# paso porque no hay forma de *importar* un `sed`:
#
#   sin_firma="$(printf '%s' "$COMMENT_BODY" | tr -d '\r' \
#     | sed -e '/^[[:space:]]*---[[:space:]]*$/,$d')"
#   trimmed="$(printf '%s' "$sin_firma" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
#   lowered="$(printf '%s' "$trimmed" | tr '[:upper:]' '[:lower:]')"
#   if [ "$lowered" != "continua" ] && [ "$lowered" != "continúa" ]; then ... exit 0
#
# La excepción del bloque de atribución tras `---` es deliberada y medida en
# ese guion: quien comenta por API no controla la firma que el servidor le
# anexa. Cualquier OTRO texto sigue invalidando la orden.
_ORDEN_FIRMA_RE = re.compile(r"^[ \t]*---[ \t]*$.*", re.DOTALL | re.MULTILINE)
_ORDENES_DE_CONTINUAR = ("continua", "contin\u00faa")


def _es_orden_de_continuar(texto: str) -> bool:
    """El MISMO predicado que la guarda 1 de ``sirius_resume_on_command.sh``.

    El paso de minúsculas es ASCII a propósito: `tr '[:upper:]' '[:lower:]'` en
    la localización C del runner no toca la `Ú`, así que usar `str.lower()`
    aceptaría un `CONTINÚA` que el guion rechaza -es decir, inventaría un
    permiso que el propietario no llegó a dar-. Ser fiel aquí es ser
    conservador.
    """
    sin_retornos = texto.replace("\r", "")
    sin_firma = _ORDEN_FIRMA_RE.sub("", sin_retornos)
    normalizada = "".join(chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in sin_firma.strip())
    return normalizada in _ORDENES_DE_CONTINUAR


# --- Etiquetas -> (estado, fase) --------------------------------------------
#
# Vocabulario real de `.github/workflows/*.yml` (bootstrap-sirius-automation-labels.yml
# y los workflows que las aplican): cada etiqueta gobierna una única fase del
# ciclo revisar-reparar de arquitectura §3.4, o un estado terminal/de espera de
# §3.2. La tabla es la interpretación única del vocabulario; ningún otro sitio
# de este módulo vuelve a decidir qué etiqueta significa qué estado.
_LABEL_STATE: dict[str, tuple[WorkItemState, WorkItemPhase | None]] = {
    "sirius:planned": (WorkItemState.PLANNED, WorkItemPhase.PREPARAR),
    "sirius:implement-requested": (WorkItemState.PLANNED, WorkItemPhase.PREPARAR),
    "sirius:implementing": (WorkItemState.ACTIVE, WorkItemPhase.EJECUTAR),
    "sirius:audit-requested": (WorkItemState.ACTIVE, WorkItemPhase.EJECUTAR),
    "sirius:ci-pending": (WorkItemState.ACTIVE, WorkItemPhase.COMPROBAR),
    "sirius:review-requested": (WorkItemState.ACTIVE, WorkItemPhase.REVISAR),
    "sirius:reviewing": (WorkItemState.ACTIVE, WorkItemPhase.REVISAR),
    "sirius:repair-requested": (WorkItemState.ACTIVE, WorkItemPhase.REPARAR),
    "sirius:repairing": (WorkItemState.ACTIVE, WorkItemPhase.REPARAR),
    "sirius:ready-for-merge": (WorkItemState.ACTIVE, WorkItemPhase.ENTREGAR),
    "sirius:blocked-decision": (WorkItemState.NEEDS_DECISION, None),
    "sirius:failed-safely": (WorkItemState.FAILED_SAFELY, None),
    "sirius:completed": (WorkItemState.DELIVERED, WorkItemPhase.ENTREGAR),
}

# Orden determinista de desempate cuando, contra lo normal, hay más de una
# etiqueta `sirius:*` reconocida a la vez: gana la más avanzada en el ciclo,
# nunca el orden -no determinista- en el que la API las haya devuelto.
_LABEL_PRIORITY: tuple[str, ...] = (
    "sirius:planned",
    "sirius:implement-requested",
    "sirius:implementing",
    "sirius:audit-requested",
    "sirius:ci-pending",
    "sirius:review-requested",
    "sirius:reviewing",
    "sirius:repair-requested",
    "sirius:repairing",
    "sirius:ready-for-merge",
    "sirius:blocked-decision",
    "sirius:failed-safely",
    "sirius:completed",
)


# Único par de etiquetas de estado que puede coexistir sin ser una
# contradicción: `sirius_validate_activation.sh` EXIGE `sirius:planned` y
# `implement-sirius-work.yml` retira las dos juntas al consumir el evento
# (scripts/automation/sirius_reconcile.sh:250-268, auditoría de la PR #146).
_PAR_DE_ACTIVACION_VALIDO = frozenset({"sirius:planned", "sirius:implement-requested"})


def _estado_y_fase(
    etiquetas: Sequence[str],
) -> tuple[WorkItemState | None, WorkItemPhase | None, bool]:
    presentes = set(etiquetas) & _LABEL_STATE.keys()
    if not presentes:
        return None, None, False
    if len(presentes) > 1 and presentes != _PAR_DE_ACTIVACION_VALIDO:
        return None, None, True
    reconocida: str | None = None
    for candidata in _LABEL_PRIORITY:
        if candidata in presentes:
            reconocida = candidata
    if reconocida is None:
        return None, None, False
    estado, fase = _LABEL_STATE[reconocida]
    return estado, fase, False


def _historial_de_confianza(
    cuerpo: CuerpoIncidencia, comentarios: Sequence[Comentario]
) -> tuple[tuple[str, bool], ...]:
    """``(texto, es_del_propietario)`` del cuerpo y los comentarios DE CONFIANZA, en orden.

    Un único recorrido para todo el módulo: el cuerpo primero -es lo primero
    que existe en una incidencia- y los comentarios en el orden en que ya
    llegan del puerto. La posición en esta tupla es lo que
    :class:`~sirius_engine.domain.mirror.EstadoAcreditado` y
    :class:`~sirius_engine.domain.mirror.PermisoDeReanudacion` guardan como
    ``orden``, y por eso las dos escalas son comparables sin ponerse de
    acuerdo: son la misma.

    El indicador de propietario viaja EMPAREJADO con su texto, no en una lista
    paralela, para que no exista ninguna forma de desalinearlos.
    """
    historial: list[tuple[str, bool]] = []
    if es_autor_de_confianza(cuerpo):
        historial.append((cuerpo.texto, es_del_propietario(cuerpo)))
    historial.extend(
        (comentario.cuerpo, es_del_propietario(comentario))
        for comentario in comentarios
        if es_autor_de_confianza(comentario)
    )
    return tuple(historial)


def _textos_de_confianza(
    cuerpo: CuerpoIncidencia, comentarios: Sequence[Comentario]
) -> tuple[str, ...]:
    """Solo los textos de :func:`_historial_de_confianza`, mismas posiciones."""
    return tuple(texto for texto, _ in _historial_de_confianza(cuerpo, comentarios))


def _comentarios_de_confianza(
    cuerpo: CuerpoIncidencia, comentarios: Sequence[Comentario]
) -> tuple[tuple[int, Comentario], ...]:
    """Los COMENTARIOS de confianza con su posición en :func:`_historial_de_confianza`.

    Existe para lo que solo un comentario tiene y el cuerpo no: un instante de
    publicación. El desplazamiento inicial se calcula con el MISMO predicado
    que decide si el cuerpo entra en el historial, así que las dos numeraciones
    no pueden desalinearse -no hay dos recorridos que mantener de acuerdo, hay
    uno y un desplazamiento-.
    """
    inicio = 1 if es_autor_de_confianza(cuerpo) else 0
    return tuple(
        (inicio + posicion, comentario)
        for posicion, comentario in enumerate(
            comentario for comentario in comentarios if es_autor_de_confianza(comentario)
        )
    )


def _texto_cronologico_de_confianza(
    cuerpo: CuerpoIncidencia, comentarios: Sequence[Comentario]
) -> str:
    """Cuerpo y comentarios DE CONFIANZA, del más antiguo al más reciente.

    Mismo orden que espera ``round_history.parse_round_records``/
    ``ci_failure_streak`` («el historial de la incidencia en orden
    cronológico»): los comentarios ya llegan ordenados por el puerto.

    Dos cosas que esta función afirmaba y no hacía (defecto H-1, incidencia
    #215, ADR-051), corregidas aquí:

    - **«de confianza»**: filtraba los comentarios por autor y concatenaba el
      cuerpo sin filtrar, porque ``LecturaCuerpo`` no transportaba autor. El
      resultado gobierna la numeración de rondas y la racha de fallos de
      Quality, así que quien pudiera escribir el cuerpo gobernaba las dos.
      Ahora el cuerpo pasa por el MISMO ``es_autor_de_confianza`` que los
      comentarios: el sitio del texto ya no cambia la respuesta.
    - **«del más antiguo al más reciente»**: el cuerpo -lo primero que existe
      en una incidencia- se concatenaba al FINAL. No se notaba en las rondas
      porque ``parse_round_records`` ordena por número de marcador, pero sí en
      ``history_after_last_resume``, que **corta** el texto por la última
      orden de continuar: un ``sirius-convergence-reset`` en el cuerpo se leía
      como posterior a todo y borraba el historial entero.

    Un cuerpo que no supera el filtro se descarta **en silencio**, igual que
    ya se descartaba un comentario ajeno. Es deliberado: lo que se busca es
    que cuerpo y comentario reciban el mismo trato, no un canal de aviso
    nuevo. Si algún día hiciera falta observarlo, es un campo de
    ``MirroredWorkItem`` y otra decisión.
    """
    return "\n".join(_textos_de_confianza(cuerpo, comentarios))


def _interpretar_rondas(texto_vigente: str) -> tuple[RondaHallazgos, ...]:
    registros = parse_round_records(texto_vigente)
    return tuple(
        RondaHallazgos(
            numero=int(registro["round"]),
            head=str(registro.get("head") or ""),
            pendientes=int(registro["pending"]),
            gravedad_total=int(registro["severity_total"]),
        )
        for registro in registros
    )


def _interpretar_eventos_quality(texto_vigente: str) -> tuple[EventoQuality, ...]:
    """Secuencia completa de eventos Quality, en el orden en que se publicaron.

    A diferencia de ``round_history.ci_failure_streak`` -que colapsa el
    historial a la racha vigente desde el último ``success``-, aquí no se
    descarta nada: un ``failure`` cerrado por un ``success`` posterior sobre
    el mismo head deja de contar para la racha, pero sigue siendo un evento
    ocurrido en el ciclo.
    """
    return tuple(
        EventoQuality(head=match.group(1), conclusion=match.group(2))
        for match in _QUALITY_EVENT_RE.finditer(texto_vigente)
    )


def _interpretar_veredictos(comentarios: Sequence[Comentario]) -> tuple[VeredictoPublicado, ...]:
    veredictos: list[VeredictoPublicado] = []
    for comentario in comentarios:
        if not es_autor_de_confianza(comentario):
            continue
        for match in _VERDICT_MARKER_RE.finditer(comentario.cuerpo):
            partes = match.group(1).split(":")
            if len(partes) < 2:
                continue
            veredictos.append(
                VeredictoPublicado(
                    rol=partes[0],
                    veredicto=partes[1],
                    referencia=":".join(partes[2:]),
                    publicado_en=comentario.creado_en,
                )
            )
    return tuple(veredictos)


def _interpretar_pr_url(cuerpo: str, comentarios: Sequence[Comentario]) -> str | None:
    # Más reciente primero, como `sirius_scan_text`: el marcador que importa
    # es el último publicado por una identidad de confianza.
    for comentario in reversed(comentarios):
        if not es_autor_de_confianza(comentario):
            continue
        match = _PR_ABIERTA_RE.search(comentario.cuerpo)
        if match:
            return match.group(1)
    match = _PR_ABIERTA_RE.search(cuerpo)
    return match.group(1) if match else None


def _interpretar_head_sha(cuerpo: str, comentarios: Sequence[Comentario]) -> str | None:
    for comentario in reversed(comentarios):
        if not es_autor_de_confianza(comentario):
            continue
        match = _SHA_MARKER_RE.search(comentario.cuerpo)
        if match:
            return match.group(1)
    match = _SHA_MARKER_RE.search(cuerpo)
    return match.group(1) if match else None


def _interpretar_reanudacion_publicada(
    cuerpo: CuerpoIncidencia, comentarios: Sequence[Comentario]
) -> bool:
    """``True`` solo si el marcador de reanudación más reciente es POSTERIOR
    a la última parada publicada en el historial de confianza.

    Mismo filtro de confianza que el resto de marcadores -``sirius_comment_once``
    los publica el propio bot o el evento ya viene filtrado por
    ``author_association == OWNER`` en el workflow que invoca al guion-, y el
    cuerpo entra por el mismo predicado que ``_texto_cronologico_de_confianza``
    para no reabrir el defecto H-1 (incidencia #215, ADR-051) de tratar el
    cuerpo distinto que los comentarios.

    La primera versión de esta función devolvía ``True`` en cuanto CUALQUIER
    marcador de reanudación aparecía en TODO el historial, con ``any(...)`` sin
    noción de orden -a diferencia de ``_interpretar_pr_url``/
    ``_interpretar_head_sha`` en este mismo fichero, que sí anclan al
    comentario más reciente con ``reversed(comentarios)``-. Consecuencia: una
    vez publicado un marcador, cualquier parada NUEVA y sin relación de esa
    misma incidencia se leía como ya reanudada (CLAUDE-REVISOR-001/CODEX-002,
    ronda 5, PR #530). Aquí se recorre el historial en orden cronológico
    -cuerpo primero, comentarios en el orden en que ya llegan del puerto- y se
    compara la posición del último marcador de reanudación con la del último
    marcador de parada (``_STOP_MARKER_RE``): sin parada posterior a la
    reanudación, o sin ninguna parada en absoluto, el marcador sigue vigente.
    """
    textos = _textos_de_confianza(cuerpo, comentarios)

    ultimo_resume: int | None = None
    ultima_parada: int | None = None
    for indice, texto in enumerate(textos):
        if _RESUME_MARKER_RE.search(texto):
            ultimo_resume = indice
        if _STOP_MARKER_RE.search(texto):
            ultima_parada = indice
    if ultimo_resume is None:
        return False
    return ultima_parada is None or ultimo_resume > ultima_parada


def _interpretar_historial_estados(
    cuerpo: CuerpoIncidencia, comentarios: Sequence[Comentario]
) -> tuple[EstadoAcreditado, ...]:
    """Los estados acreditados por marcadores ``sirius-notification``, en orden.

    Mismo filtro de confianza y mismo orden cronológico que
    :func:`_textos_de_confianza` -cuerpo primero, comentarios en el orden en
    que ya llegan del puerto-, y la MISMA tabla ``_LABEL_STATE`` que interpreta
    la foto: una etiqueta no significa una cosa cuando está puesta y otra
    cuando la nombra un marcador. Una etiqueta que la tabla no reconozca se
    ignora en silencio, igual que en :func:`_estado_y_fase`.

    Deliberadamente NO se corta por ``history_after_last_resume``: una orden de
    reanudación mueve el listón de la convergencia -cuántas rondas cuentan-,
    no borra los estados por los que la incidencia pasó antes. El recorrido
    acreditado ancla en el estado guardado del motor, que puede ser anterior a
    esa orden (ADR-147).

    Cada ocurrencia se lleva su propia evidencia, no la del ciclo entero
    (CODEX-002 y CODEX-003, ronda 2, PR #546):

    - el **instante** del comentario que la publicó (``None`` si el marcador
      viene del cuerpo, que no tiene instante propio);
    - el **diagnóstico** que le corresponde, si acredita una parada
      ``FAILED_SAFELY``: el último publicado hasta su posición, que es donde
      ``sirius_apply_verdict.sh`` lo escribe -el comentario del veredicto va
      ANTES de aplicar la etiqueta, y la etiqueta es lo que dispara este
      marcador-. ``None`` si no hay ninguno hasta aquí: entonces no se
      atribuye ninguno.
    """
    diagnosticos = _interpretar_diagnosticos_fallo(cuerpo, comentarios)
    instantes = {
        orden: comentario.creado_en
        for orden, comentario in _comentarios_de_confianza(cuerpo, comentarios)
    }
    acreditados: list[EstadoAcreditado] = []
    for orden, texto in enumerate(_textos_de_confianza(cuerpo, comentarios)):
        for match in _NOTIFICATION_MARKER_RE.finditer(texto):
            etiqueta = match.group(1)
            if etiqueta not in _LABEL_STATE:
                continue
            estado, fase = _LABEL_STATE[etiqueta]
            acreditados.append(
                EstadoAcreditado(
                    etiqueta=etiqueta,
                    estado=estado,
                    fase=fase,
                    head=match.group(2),
                    orden=orden,
                    publicado_en=instantes.get(orden),
                    diagnostico=(
                        _diagnostico_hasta(diagnosticos, orden)
                        if estado is WorkItemState.FAILED_SAFELY
                        else None
                    ),
                )
            )
    return tuple(acreditados)


def _diagnostico_hasta(diagnosticos: Sequence[tuple[int, str]], orden: int) -> str | None:
    """El último diagnóstico publicado en el historial hasta ``orden``, o ``None``."""
    atribuible: str | None = None
    for posicion, texto in diagnosticos:
        if posicion > orden:
            break
        atribuible = texto
    return atribuible


def _interpretar_permisos_reanudacion(
    cuerpo: CuerpoIncidencia, comentarios: Sequence[Comentario]
) -> tuple[PermisoDeReanudacion, ...]:
    """La CRONOLOGÍA de los permisos escritos del propietario, del más antiguo al más reciente.

    Dos formas, con el mismo peso y en la misma lista (ADR-147, decisión del
    propietario en #545):

    - el **marcador** de reanudación (``_RESUME_MARKER_RE``, los tres tipos que
      ``sirius_resume_on_command.sh`` publica antes de reponer la etiqueta),
      con el filtro de confianza de siempre: lo publica ``github-actions[bot]``;
    - la **orden** exacta ``continua``, que exige ``author_association ==
      "OWNER"`` y no el filtro general -``continua`` es palabra del
      propietario, no del bot, y aceptarla del bot sería dejar que la
      automatización se diera permiso a sí misma-.

    El marcador es el recibo de la máquina y la orden es el permiso mismo. Las
    dos formas hacen falta porque el recibo puede faltar ESTRUCTURALMENTE:
    ``sirius_comment_once`` deduplica por el texto completo del marcador y el
    de ``sirius-resume-stop`` solo lleva el head, así que dos reanudaciones
    sobre un mismo head nunca dejan un segundo recibo (medición de la primera
    ronda de #545 sobre el historial real de la #537).

    ``orden`` es la posición del texto en el historial de confianza, la misma
    escala que usa :func:`_interpretar_historial_estados`. Un texto que
    contenga las dos cosas produce dos permisos con el mismo ``orden``; el
    consumo en orden del recorrido los toma uno detrás de otro, que es lo
    correcto: son dos permisos escritos, no uno.
    """
    permisos: list[PermisoDeReanudacion] = []
    for orden, (texto, del_propietario) in enumerate(_historial_de_confianza(cuerpo, comentarios)):
        for match in _RESUME_MARKER_RE.finditer(texto):
            permisos.append(
                PermisoDeReanudacion(
                    forma=FormaDePermiso.MARCADOR, referencia=match.group(0), orden=orden
                )
            )
        if del_propietario and _es_orden_de_continuar(texto):
            permisos.append(
                PermisoDeReanudacion(forma=FormaDePermiso.ORDEN, referencia="continua", orden=orden)
            )
    return tuple(permisos)


def _interpretar_diagnosticos_fallo(
    cuerpo: CuerpoIncidencia, comentarios: Sequence[Comentario]
) -> tuple[tuple[int, str], ...]:
    """La CRONOLOGÍA de los diagnósticos de parada, cada uno con su posición.

    Nunca en el cuerpo -a diferencia de SHA/PR-: ``FAILED_SAFELY`` es un
    veredicto de un rol de ejecución, y esos solo se publican como comentario
    (misma fuente que :func:`_interpretar_veredictos`). El cuerpo entra igual
    en el recorrido, pero solo para que la posición esté en la MISMA escala que
    la de :func:`_interpretar_historial_estados`.

    Antes de la ronda 2 de la PR #546 solo existía el último diagnóstico de
    toda la incidencia, y el recorrido acreditado se lo ponía a TODAS las
    paradas que recreaba: dos paradas seguidas con diagnósticos distintos se
    escribían las dos con el segundo (CODEX-003). Conservar la cronología es lo
    que permite atribuirle a cada parada la suya.
    """
    diagnosticos: list[tuple[int, str]] = []
    for orden, comentario in _comentarios_de_confianza(cuerpo, comentarios):
        match = _DIAGNOSTICO_FALLO_RE.search(comentario.cuerpo)
        if match:
            texto = match.group(1).strip()
            if texto:
                diagnosticos.append((orden, texto))
    return tuple(diagnosticos)


def _interpretar_diagnostico_fallo(
    cuerpo: CuerpoIncidencia, comentarios: Sequence[Comentario]
) -> str | None:
    """El diagnóstico de la ÚLTIMA parada publicada: el que le toca a la foto vigente.

    Es el último elemento de :func:`_interpretar_diagnosticos_fallo` y no un
    segundo recorrido: la foto y las paradas históricas leen exactamente la
    misma cronología, así que no pueden discrepar sobre qué es un diagnóstico.
    """
    diagnosticos = _interpretar_diagnosticos_fallo(cuerpo, comentarios)
    return diagnosticos[-1][1] if diagnosticos else None


def proyectar_work_item(
    *,
    repo: str,
    numero: int,
    metadatos: LecturaMetadatos,
    cuerpo: LecturaCuerpo,
    comentarios: LecturaComentarios,
    ahora: datetime,
) -> MirroredWorkItem:
    """Proyectar una incidencia ya leída a un :class:`MirroredWorkItem`.

    Lanza :class:`EspejoIlegibleError` si CUALQUIERA de los tres proveedores
    no pudo leer (requisito 2): sin metadatos, cuerpo o comentarios no hay
    forma honesta de decir "no hay etiqueta"/"no hay PR"/"no hay rondas", así
    que la función se niega a fingir una proyección completa con datos
    parciales.
    """
    if metadatos.estado is not LecturaEstado.OK or metadatos.metadatos is None:
        raise EspejoIlegibleError("metadatos", metadatos.error or "lectura no disponible")
    if cuerpo.estado is not LecturaEstado.OK or cuerpo.cuerpo is None:
        raise EspejoIlegibleError("cuerpo", cuerpo.error or "lectura no disponible")
    if comentarios.estado is not LecturaEstado.OK or comentarios.comentarios is None:
        raise EspejoIlegibleError("comentarios", comentarios.error or "lectura no disponible")

    texto_vigente = history_after_last_resume(
        _texto_cronologico_de_confianza(cuerpo.cuerpo, comentarios.comentarios)
    )
    estado, fase, etiquetas_contradictorias = _estado_y_fase(metadatos.metadatos.etiquetas)

    return MirroredWorkItem(
        work_id=f"{repo}#{numero}",
        estado=estado,
        fase=fase,
        etiquetas=metadatos.metadatos.etiquetas,
        etiquetas_contradictorias=etiquetas_contradictorias,
        cerrada=metadatos.metadatos.estado_gh == "closed",
        pr_url=_interpretar_pr_url(cuerpo.cuerpo.texto, comentarios.comentarios),
        head_sha=_interpretar_head_sha(cuerpo.cuerpo.texto, comentarios.comentarios),
        rondas=_interpretar_rondas(texto_vigente),
        veredictos=_interpretar_veredictos(comentarios.comentarios),
        eventos_quality=_interpretar_eventos_quality(texto_vigente),
        fallos_quality_consecutivos=ci_failure_streak(texto_vigente),
        origen=OrigenLectura(fuente=f"github:{repo}#{numero}", leido_en=ahora),
        diagnostico_fallo=_interpretar_diagnostico_fallo(cuerpo.cuerpo, comentarios.comentarios),
        reanudacion_publicada=_interpretar_reanudacion_publicada(
            cuerpo.cuerpo, comentarios.comentarios
        ),
        historial_estados=_interpretar_historial_estados(cuerpo.cuerpo, comentarios.comentarios),
        permisos_reanudacion=_interpretar_permisos_reanudacion(
            cuerpo.cuerpo, comentarios.comentarios
        ),
    )


def leer_y_proyectar_work_item(
    port: GitHubMirrorPort, *, repo: str, numero: int, ahora: datetime
) -> MirroredWorkItem:
    """Orquesta las tres lecturas del puerto y proyecta el resultado."""
    return proyectar_work_item(
        repo=repo,
        numero=numero,
        metadatos=port.leer_metadatos(repo=repo, numero=numero),
        cuerpo=port.leer_cuerpo(repo=repo, numero=numero),
        comentarios=port.leer_comentarios(repo=repo, numero=numero),
        ahora=ahora,
    )


def proyectar_run(
    *, run_id: str, lectura: LecturaRunActions, ahora: datetime
) -> MirroredRun | None:
    """Proyectar el run de Actions ya leído.

    Lanza :class:`EspejoIlegibleError` si no se pudo leer. Devuelve ``None``
    -legítimamente, no un fallo- cuando la lectura fue correcta pero no
    existe ningún run para ese id: "leí y no hay" también aplica aquí.
    """
    if lectura.estado is not LecturaEstado.OK:
        raise EspejoIlegibleError("run_actions", lectura.error or "lectura no disponible")
    if lectura.run is None:
        return None
    return MirroredRun(
        run_id=lectura.run.run_id,
        estado_run=lectura.run.estado_run,
        conclusion=lectura.run.conclusion,
        head_sha=lectura.run.head_sha,
        url=lectura.run.url,
        origen=OrigenLectura(fuente=f"github-actions:{run_id}", leido_en=ahora),
    )


def leer_y_proyectar_run(
    port: GitHubMirrorPort, *, repo: str, run_id: str, ahora: datetime
) -> MirroredRun | None:
    return proyectar_run(
        run_id=run_id,
        lectura=port.leer_run_actions(repo=repo, run_id=run_id),
        ahora=ahora,
    )
