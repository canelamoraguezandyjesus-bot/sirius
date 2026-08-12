"""Cómo suena Sirius al confirmar una orden de grabación.

§4.1 de ``SIRIUS-MODEL-STUDIO-UI-001`` pide *«confirmación hablada corta y
clara»* para las órdenes simples, y su principio de personalidad fija el orden:
*«Primero debe quedar claro qué ocurrió o cuál es la respuesta. Después puede
aparecer humor seco, sarcasmo, provocación contextual o un insulto de confianza
permitido.»* Estas frases respetan ese orden: el hecho primero, la gracia
después, y nunca al revés.

**Las frases están escritas aquí, no las genera el modelo.** Tres razones, por
orden de importancia:

1. Una frase generada podría afirmar algo que no ocurrió. Estas no pueden:
   solo se eligen **después** de que el sistema de captura haya confirmado el
   estado, y cada una está atada a ese estado concreto.
2. Son instantáneas. Al dar una orden mientras se graba, esperar un segundo a
   que llegue una respuesta rompe el ritmo.
3. No cuestan nada, y una sesión de grabación son muchas órdenes.

**El humor desaparece cuando algo va mal.** El manual de identidad lo dice en su
Anexo A —*«error técnico serio: reduce humor»*— y §4.1 lo repite para acciones
críticas. Un fallo se cuenta tal cual, sin adornos.

Rotan en orden, no al azar: así la misma sesión no repite la primera frase dos
veces seguidas y las pruebas siguen siendo reproducibles.
"""

from __future__ import annotations

from sirius.application.capture_commands import CaptureCommand
from sirius.application.studio_capture import CaptureFeedback
from sirius.domain.model_studio import StudioCaptureState

_STARTED: tuple[str, ...] = (
    "Grabando. A ver qué sale.",
    "Grabando. Intenta no quedarte callado mirando la protoboard.",
    "Grabando. Tú habla, que yo ya me encargo del resto.",
    "Grabando. Esta vez suéldalo bien.",
    "Grabando. El público espera.",
)

_ALREADY_RECORDING: tuple[str, ...] = (
    "Ya estaba grabando. Pero gracias por confirmarlo.",
    "Sigo grabando desde antes. No hace falta insistir.",
    "Grabando iba ya. Dos veces no graba más rápido.",
)

_STOPPED: tuple[str, ...] = (
    "Parado. Ahí queda.",
    "Parado. A ver qué salvamos de eso.",
    "Parado y guardado. Respira.",
    "Corto. Ya está en el disco.",
)

_NOT_RECORDING: tuple[str, ...] = (
    "No había nada grabando. Paramos el aire, entonces.",
    "Nada que parar: no estábamos grabando.",
)

_PAUSED: tuple[str, ...] = (
    "En pausa. Aprovecha y ordena la mesa.",
    "Pausado. Sigo aquí cuando vuelvas.",
    "En pausa. Tómate el café.",
)

_RESUMED: tuple[str, ...] = (
    "Seguimos.",
    "Otra vez en marcha. Por donde íbamos.",
    "Reanudado. No te despistes ahora.",
)

_MARKED: tuple[str, ...] = (
    "Marcado. Ya lo encontrarás luego.",
    "Apuntado. Espero que fuera algo bueno.",
    "Marca puesta. Te la debo para el montaje.",
)

_SCENE_SWITCHED: tuple[str, ...] = (
    "Cambiado.",
    "Ahí lo tienes.",
    "Plano cambiado. Ponte guapo.",
    "Cambiado. Mucho mejor así.",
)

_EMERGENCY_STOPPED: tuple[str, ...] = (
    "Cortado. ¿Qué ha pasado?",
    "Parado en seco.",
)

_STATUS_RECORDING: tuple[str, ...] = (
    "Sí, grabando.",
    "Grabando, sí. Llevamos un rato.",
)

_STATUS_IDLE: tuple[str, ...] = (
    "No, no estoy grabando.",
    "Ahora mismo no grabo nada.",
)

_PHRASES: dict[tuple[CaptureCommand, StudioCaptureState], tuple[str, ...]] = {
    (CaptureCommand.START_RECORDING, StudioCaptureState.GRABANDO): _STARTED,
    (CaptureCommand.STOP_RECORDING, StudioCaptureState.PREPARADO): _STOPPED,
    (CaptureCommand.PAUSE_RECORDING, StudioCaptureState.PAUSADO): _PAUSED,
    (CaptureCommand.RESUME_RECORDING, StudioCaptureState.GRABANDO): _RESUMED,
    (CaptureCommand.MARK_MOMENT, StudioCaptureState.GRABANDO): _MARKED,
    (CaptureCommand.SWITCH_SCENE, StudioCaptureState.PREPARADO): _SCENE_SWITCHED,
    (CaptureCommand.SWITCH_SCENE, StudioCaptureState.GRABANDO): _SCENE_SWITCHED,
    (CaptureCommand.SWITCH_SCENE, StudioCaptureState.PAUSADO): _SCENE_SWITCHED,
    (CaptureCommand.EMERGENCY_STOP, StudioCaptureState.PREPARADO): _EMERGENCY_STOPPED,
    (CaptureCommand.GET_STATUS, StudioCaptureState.GRABANDO): _STATUS_RECORDING,
    (CaptureCommand.GET_STATUS, StudioCaptureState.PAUSADO): _STATUS_RECORDING,
    (CaptureCommand.GET_STATUS, StudioCaptureState.PREPARADO): _STATUS_IDLE,
}

_SERIOUS_STATES = frozenset(
    {
        StudioCaptureState.ERROR,
        StudioCaptureState.INCIERTO,
        StudioCaptureState.INICIANDO,
        StudioCaptureState.DETENIENDO,
        StudioCaptureState.CAMBIANDO,
    }
)
"""Estados en los que no se bromea.

Los tres últimos no son fallos: son órdenes en vuelo. Bromear sobre algo que
todavía no ha pasado se parece demasiado a afirmar que ya pasó.
"""


def spoken_confirmation(command: CaptureCommand, feedback: CaptureFeedback, turn: int = 0) -> str:
    """Qué dice Sirius al confirmar una orden ya resuelta.

    ``turn`` es un contador que crece con cada orden de la sesión: hace rotar
    las frases sin usar azar, así que la misma sesión no repite y las pruebas
    siguen dando siempre lo mismo.

    Cuando algo falla o el estado no está confirmado, devuelve el mensaje
    factual tal cual, sin una sola broma.
    """
    if not feedback.succeeded or feedback.state in _SERIOUS_STATES:
        return feedback.message or feedback.state.label

    # Casos en los que el hecho contradice la orden: se dice el hecho, y se
    # dice con gracia, pero nunca se sugiere que la orden hizo algo que no hizo.
    if command is CaptureCommand.START_RECORDING and feedback.message:
        return _rotate(_ALREADY_RECORDING, turn)
    if command is CaptureCommand.STOP_RECORDING and feedback.message:
        return _rotate(_NOT_RECORDING, turn)

    phrases = _PHRASES.get((command, feedback.state))
    if phrases is None:
        # Sin frase para esta combinación se prefiere el hecho a inventar una:
        # una confirmación que no encaja con lo que pasó es peor que una seca.
        return feedback.message or feedback.state.label
    return _rotate(phrases, turn)


def _rotate(phrases: tuple[str, ...], turn: int) -> str:
    return phrases[turn % len(phrases)]
