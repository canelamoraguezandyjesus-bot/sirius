"""``SesionCLI``: la interfaz v0 (objetivo 5, incidencia #206).

"Sesión/CLI, sin estado propio: Telegram será otro adapter (D3)". Cada
turno se resuelve enteramente con lo que el llamador inyecta -almacén,
notificador, fuentes de ``contexto.recuperar``-; la sesión no cachea ningún
WorkItem ni ninguna respuesta entre turnos. Une, en el orden de arquitectura
§8.5, los tres bloques ya construidos: clasificar (``intent_interpreter``),
decidir (``gate``) y aplicar (``work_intake``); para las consultas al
pasado, delega en ``contexto.recuperar`` (A3) en vez de tocar ningún
WorkItem.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sirius_engine.context_recall import (
    ContextoRecuperado,
    LecturaHistorialGit,
    recuperar_contexto,
)
from sirius_engine.domain.intent import TipoIntencion
from sirius_engine.gate import ResultadoPuerta, decidir
from sirius_engine.intent_interpreter import interpretar_intencion_v0
from sirius_engine.ports.github_mirror import GitHubMirrorPort
from sirius_engine.ports.notification import NotificationPort
from sirius_engine.ports.store import WorkEngineStore
from sirius_engine.work_intake import ResultadoIntake, aplicar_decision


@dataclass(frozen=True, slots=True)
class RespuestaTurno:
    """Lo que un turno produce. ``intake`` es ``None`` salvo que se creara un WorkItem."""

    mensaje: str
    intake: ResultadoIntake | None = None
    contexto: ContextoRecuperado | None = None


@dataclass(frozen=True, slots=True)
class ContextoRecuperarConfig:
    """Fuentes que ``contexto.recuperar`` necesita para responder consultas al pasado."""

    raiz_repo: Path
    port: GitHubMirrorPort
    repo: str
    numeros_incidencias: Sequence[int]
    lectura_historial_git: LecturaHistorialGit


def _resumir_contexto(contexto: ContextoRecuperado | None) -> str:
    if contexto is None:
        return "No hay fuentes de contexto.recuperar configuradas para esta sesión."
    if not contexto.referencias:
        return f"No encontré referencias para {contexto.consulta!r}."
    citas = "; ".join(f"{r.tipo}:{r.identificador}" for r in contexto.referencias[:5])
    return f"Encontré {len(contexto.referencias)} referencia(s) para {contexto.consulta!r}: {citas}"


class SesionCLI:
    """Interfaz v0: sesión/CLI, sin estado propio."""

    def __init__(
        self,
        *,
        store: WorkEngineStore,
        notificar: NotificationPort | None = None,
        contexto_recuperar: ContextoRecuperarConfig | None = None,
    ) -> None:
        self._store = store
        self._notificar = notificar
        self._contexto_recuperar = contexto_recuperar

    def procesar_turno(self, mensaje: str, *, work_id: str, now: datetime) -> RespuestaTurno:
        """Procesar un turno. Nunca dos: la puerta decide en una sola pasada."""
        signal = interpretar_intencion_v0(mensaje)
        decision = decidir(signal)

        if decision.resultado is ResultadoPuerta.NO_CREAR:
            if signal.tipo is TipoIntencion.CONSULTAR_PASADO:
                contexto = self._consultar_pasado(signal.consulta or mensaje, now=now)
                return RespuestaTurno(mensaje=_resumir_contexto(contexto), contexto=contexto)
            if signal.tipo is TipoIntencion.AMBIGUA:
                return RespuestaTurno(mensaje=decision.pregunta_aclaratoria or decision.motivo)
            return RespuestaTurno(mensaje=decision.motivo)

        intake = aplicar_decision(
            decision,
            store=self._store,
            work_id=work_id,
            peticion_original=mensaje,
            now=now,
            notificar=self._notificar,
        )
        assert intake.work_item is not None
        assert intake.autoridad is not None
        if decision.resultado is ResultadoPuerta.CREAR_Y_ACTIVAR:
            texto = (
                f"Entendido: {intake.work_item.objetivo!r}. Creado y activado "
                f"{intake.work_item.work_id} (autoridad: {intake.autoridad.value})."
            )
        else:
            assert intake.escalada is not None
            texto = (
                f"{intake.work_item.work_id} necesita tu decisión antes de seguir "
                f"({intake.escalada.causa.value}): {decision.motivo}"
            )
        return RespuestaTurno(mensaje=texto, intake=intake)

    def _consultar_pasado(self, consulta: str, *, now: datetime) -> ContextoRecuperado | None:
        if self._contexto_recuperar is None:
            return None
        cfg = self._contexto_recuperar
        return recuperar_contexto(
            consulta,
            raiz_repo=cfg.raiz_repo,
            port=cfg.port,
            repo=cfg.repo,
            numeros_incidencias=cfg.numeros_incidencias,
            lectura_historial_git=cfg.lectura_historial_git,
            ahora=now,
        )
