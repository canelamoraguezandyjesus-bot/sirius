"""Proyección del espejo de solo lectura de la vía GitHub (A3, incidencia #193).

Interpreta lo que ya devuelve :mod:`sirius_engine.ports.github_mirror` -
metadatos, cuerpo, comentarios, run de Actions- y produce las proyecciones NO
autoritativas de :mod:`sirius_engine.domain.mirror`.

Reutiliza, en vez de reinventar, la semántica de marcadores que
``scripts/automation/sirius_issue.sh`` y ``sirius_convergence.py`` llevan
meses probando en producción (incidencia #193, «Método: reutilizar la
semántica ya probada, no reinventarla»):

- ``sirius-round``/``RONDA_HALLAZGOS`` y la racha de fallos de Quality
  (``sirius-quality``) se interpretan **importando**
  ``scripts/automation/sirius_convergence.py`` -su ``ROUND_RECORD_RE``,
  ``parse_round_records``, ``ci_failure_streak`` y
  ``history_after_last_resume`` son las mismas funciones que gobiernan la
  convergencia real, no una segunda copia que podría divergir-. El mismo
  patrón de añadir ``scripts/`` a ``sys.path`` ya lo usa
  ``tests/engine/conftest.py`` para ``experiments/``, y ``pyproject.toml``
  ya trata ``scripts/`` como raíz de imports para pytest (``pythonpath``) y
  mypy (``mypy_path``): este módulo hace en tiempo de ejecución lo mismo que
  esos dos ya asumen en tiempo de comprobación.
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
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from automation import sirius_convergence  # noqa: E402
from sirius_engine.domain.mirror import (  # noqa: E402
    EspejoIlegibleError,
    MirroredRun,
    MirroredWorkItem,
    OrigenLectura,
    RondaHallazgos,
    VeredictoPublicado,
)
from sirius_engine.domain.work_item import WorkItemPhase, WorkItemState  # noqa: E402
from sirius_engine.ports.github_mirror import (  # noqa: E402
    Comentario,
    GitHubMirrorPort,
    LecturaComentarios,
    LecturaCuerpo,
    LecturaEstado,
    LecturaMetadatos,
    LecturaRunActions,
)

# --- Filtro de autor de confianza ------------------------------------------
#
# Mismo predicado que SIRIUS_TRUSTED_AUTHOR_JQ en scripts/automation/sirius_issue.sh:
#   select(.author_association == "OWNER" or (.user.login // "") == "github-actions[bot]")
_BOT_LOGIN = "github-actions[bot]"


def es_autor_de_confianza(comentario: Comentario) -> bool:
    """Compartido con :mod:`sirius_engine.context_recall`: un único filtro de confianza."""
    return comentario.autor_asociacion == "OWNER" or comentario.autor_login == _BOT_LOGIN


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

# "<!-- sirius-verdict:<rol>:<resto> -->" — el número de campos tras el rol
# varía (precheck lleva un motivo y una etiqueta de ejecución de más), así que
# se captura todo el contenido y se separa por ":" en vez de fijar un número
# de grupos.
_VERDICT_MARKER_RE = re.compile(r"<!--\s*sirius-verdict:([^>]*?)\s*-->")

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


def _estado_y_fase(etiquetas: Sequence[str]) -> tuple[WorkItemState | None, WorkItemPhase | None]:
    presentes = set(etiquetas)
    reconocida: str | None = None
    for candidata in _LABEL_PRIORITY:
        if candidata in presentes:
            reconocida = candidata
    if reconocida is None:
        return None, None
    return _LABEL_STATE[reconocida]


def _texto_cronologico_de_confianza(cuerpo: str, comentarios: Sequence[Comentario]) -> str:
    """Cuerpo + comentarios de confianza, del más antiguo al más reciente.

    Mismo orden que espera ``sirius_convergence.parse_round_records``/
    ``ci_failure_streak`` («el historial de la incidencia en orden
    cronológico»): los comentarios ya llegan ordenados por el puerto, así que
    aquí solo se filtra por confianza y se concatena.
    """
    de_confianza = [c.cuerpo for c in comentarios if es_autor_de_confianza(c)]
    return "\n".join((*de_confianza, cuerpo))


def _interpretar_rondas(texto_vigente: str) -> tuple[RondaHallazgos, ...]:
    registros = sirius_convergence.parse_round_records(texto_vigente)
    return tuple(
        RondaHallazgos(
            numero=int(registro["round"]),
            head=str(registro.get("head") or ""),
            pendientes=int(registro["pending"]),
            gravedad_total=int(registro["severity_total"]),
        )
        for registro in registros
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

    texto_vigente = sirius_convergence.history_after_last_resume(
        _texto_cronologico_de_confianza(cuerpo.cuerpo, comentarios.comentarios)
    )
    estado, fase = _estado_y_fase(metadatos.metadatos.etiquetas)

    return MirroredWorkItem(
        work_id=f"{repo}#{numero}",
        estado=estado,
        fase=fase,
        etiquetas=metadatos.metadatos.etiquetas,
        cerrada=metadatos.metadatos.estado_gh == "closed",
        pr_url=_interpretar_pr_url(cuerpo.cuerpo, comentarios.comentarios),
        head_sha=_interpretar_head_sha(cuerpo.cuerpo, comentarios.comentarios),
        rondas=_interpretar_rondas(texto_vigente),
        veredictos=_interpretar_veredictos(comentarios.comentarios),
        fallos_quality_consecutivos=sirius_convergence.ci_failure_streak(texto_vigente),
        origen=OrigenLectura(fuente=f"github:{repo}#{numero}", leido_en=ahora),
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
