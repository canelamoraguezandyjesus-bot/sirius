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


#: Cuántas cosas se citan como mucho en una sola frase, antes de pasar a "y N
#: más". Vale igual para las referencias encontradas y para los sitios que no
#: se dejaron leer: el destinatario de este texto es una persona leyendo una
#: línea, no un programa recorriendo una lista.
_MAXIMO_CITADO = 5


def _citar(identificadores: Sequence[str]) -> str:
    """Citar hasta :data:`_MAXIMO_CITADO` identificadores y contar el resto."""
    mostrados = "; ".join(identificadores[:_MAXIMO_CITADO])
    restantes = len(identificadores) - _MAXIMO_CITADO
    if restantes > 0:
        return f"{mostrados}; y {restantes} más"
    return mostrados


def _resumir_contexto(contexto: ContextoRecuperado | None) -> str:
    """El texto que lee una persona. Nunca dice "no hay" de lo que no se pudo mirar.

    Es la única función que convierte un ``ContextoRecuperado`` en lenguaje
    natural, y por eso es donde se decide si Sirius miente. Hasta la
    incidencia #224 (defecto **H-9**) no miraba ``proveedores_fallidos``: con
    las tres fuentes caídas respondía "No encontré referencias para X", que es
    una ausencia que nadie había comprobado. Es la familia de ADR-036 -"una
    lectura caída no es una ausencia"- un nivel por encima de H-5 (ADR-050) y
    peor que él: H-5 perdía el dato dentro de una estructura, donde un
    programa podía notarlo; esto se lo dice a una persona, en su idioma, con
    una frase que suena a respuesta.

    Las tres situaciones se dicen distintas, y las dos que ya existían se
    dicen **igual que antes** (ADR-059):

    - Se pudo mirar en todo y no había nada → "No encontré referencias...".
    - Se pudo mirar en todo y había → "Encontré N referencia(s)...".
    - Quedaron sitios sin leer → se dice, y se dice **cuáles**, tanto si
      además se encontró algo como si no. Avisar solo cuando no se encontró
      nada dejaría media mentira: una respuesta parcial que se lee como
      completa.

    Los identificadores (``historial_git``, ``arbol:<ruta>``,
    ``incidencia:<n>:cuerpo``) se citan tal como llegan, sin traducir: son
    citas, igual que las de las referencias encontradas, y una tabla de
    traducción aquí se quedaría muda en silencio ante un proveedor nuevo.
    Lo que sí tiene que entenderse sin saber qué es un "proveedor" es la
    frase que los envuelve.
    """
    if contexto is None:
        return "No hay fuentes de contexto.recuperar configuradas para esta sesión."
    sin_leer = contexto.proveedores_fallidos
    if not contexto.referencias:
        if not sin_leer:
            return f"No encontré referencias para {contexto.consulta!r}."
        return (
            f"No pude mirar en todos los sitios, así que no puedo decirte si hay algo sobre "
            f"{contexto.consulta!r}: {len(sin_leer)} sitio(s) no se dejaron leer "
            f"({_citar(sin_leer)}). En los que sí pude mirar no había nada."
        )
    citas = "; ".join(f"{r.tipo}:{r.identificador}" for r in contexto.referencias[:_MAXIMO_CITADO])
    encontrado = (
        f"Encontré {len(contexto.referencias)} referencia(s) para {contexto.consulta!r}: {citas}"
    )
    if not sin_leer:
        return encontrado
    return (
        f"{encontrado}. Aviso: puede que no sea todo, porque {len(sin_leer)} sitio(s) "
        f"no se dejaron leer ({_citar(sin_leer)}); ahí no he podido mirar."
    )


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
