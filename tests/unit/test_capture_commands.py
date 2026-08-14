"""Órdenes de captura dichas o escritas (MS-017 de #127).

Lo más importante que comprueban estas pruebas no es lo que se reconoce, sino
lo que **no** se reconoce: hablar de una cámara no puede cambiar de plano, y
preguntar «¿para qué sirve esto?» no puede detener una grabación.
"""

from __future__ import annotations

import pytest

from sirius.application.capture_commands import CaptureCommand, interpret
from sirius.domain.capture import Scene, SceneRegistry

_SCENES = SceneRegistry(
    (
        Scene("pantalla", "Pantalla", "Pantalla", ("pantalla", "escritorio"), is_fallback=True),
        Scene("cenital", "Cámara cenital", "Cámara cenital", ("cenital", "desde arriba")),
        Scene("frontal", "Cámara frontal", "Cámara frontal", ("frontal", "mi cara")),
    )
)


def _command(text: str) -> CaptureCommand | None:
    intent = interpret(text, _SCENES)
    return intent.command if intent is not None else None


# --- Lo que sí es una orden ---------------------------------------------


@pytest.mark.parametrize(
    "text",
    ["graba", "Graba", "GRABA", "empieza a grabar", "dale a grabar", "¡Graba!"],
)
def test_starting_is_recognised(text: str) -> None:
    assert _command(text) is CaptureCommand.START_RECORDING


@pytest.mark.parametrize(
    "text",
    ["para", "Para.", "deja de grabar", "corta la grabación", "detente", "para de grabar"],
)
def test_stopping_is_recognised(text: str) -> None:
    assert _command(text) is CaptureCommand.STOP_RECORDING


@pytest.mark.parametrize("text", ["pausa", "pausar", "haz una pausa"])
def test_pausing_is_recognised(text: str) -> None:
    assert _command(text) is CaptureCommand.PAUSE_RECORDING


@pytest.mark.parametrize("text", ["sigue", "continúa", "reanuda", "seguimos", "sigue grabando"])
def test_resuming_is_recognised(text: str) -> None:
    assert _command(text) is CaptureCommand.RESUME_RECORDING


@pytest.mark.parametrize("text", ["marca", "marca esto", "apunta esto"])
def test_marking_is_recognised(text: str) -> None:
    assert _command(text) is CaptureCommand.MARK_MOMENT


@pytest.mark.parametrize("text", ["parada de emergencia", "para ya", "corta ya", "emergencia"])
def test_the_emergency_stop_is_recognised(text: str) -> None:
    assert _command(text) is CaptureCommand.EMERGENCY_STOP


@pytest.mark.parametrize(
    "text",
    ["¿estás grabando?", "estamos grabando", "cómo va la grabación", "estado de la grabación"],
)
def test_asking_the_state_is_recognised(text: str) -> None:
    assert _command(text) is CaptureCommand.GET_STATUS


# --- Cambiar de cámara ---------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "cambia a cenital",
        "cambia a la cenital",
        "cambia a la cámara cenital",
        "cámbiate a la cenital",
        "pon la cenital",
        "ponme la cámara cenital",
        "pasa a cenital",
        "activa la cámara cenital",
        "ve a la cenital",
        "saca la cenital",
        "dame la cámara cenital",
    ],
)
def test_a_scene_can_be_asked_for_in_many_ways(text: str) -> None:
    intent = interpret(text, _SCENES)

    assert intent is not None
    assert intent.command is CaptureCommand.SWITCH_SCENE
    assert intent.scene_id == "cenital"


def test_a_scene_can_be_asked_for_by_its_spoken_alias() -> None:
    intent = interpret("cambia a desde arriba", _SCENES)

    assert intent is not None
    assert intent.scene_id == "cenital"


def test_accents_and_capitals_do_not_matter() -> None:
    assert interpret("CAMBIA A LA CÁMARA FRONTAL", _SCENES) is not None
    assert interpret("cambia a la camara frontal", _SCENES) is not None


def test_the_longest_prefix_wins() -> None:
    """«cambia a la cámara X» no puede dejar «la cámara X» como nombre."""
    intent = interpret("cambia a la cámara frontal", _SCENES)

    assert intent is not None
    assert intent.scene_id == "frontal"


def test_an_unauthorized_scene_is_not_a_command() -> None:
    """Va a la conversación como una frase más: no se adivina la más parecida."""
    assert interpret("cambia a la cámara del salón", _SCENES) is None


def test_without_authorized_scenes_nothing_switches() -> None:
    assert interpret("cambia a la cenital", SceneRegistry()) is None


# --- Marcas con etiqueta -------------------------------------------------


def test_a_mark_can_carry_a_label() -> None:
    intent = interpret("marca esto como el primer led", _SCENES)

    assert intent is not None
    assert intent.command is CaptureCommand.MARK_MOMENT
    assert intent.label == "el primer led"


def test_a_mark_label_that_is_a_whole_speech_is_not_a_command() -> None:
    """Una etiqueta es corta; un párrafo entero es conversación."""
    long_text = "marca esto como " + "y luego pasó una cosa muy larga " * 5

    assert interpret(long_text, _SCENES) is None


# --- Lo que NO puede ser una orden, que es lo importante ----------------


@pytest.mark.parametrize(
    "text",
    [
        "¿para qué sirve esta resistencia?",
        "para qué necesito la protoboard",
        "esto es para el servo",
        "sigue habiendo un problema con el led",
        "marca de la placa que compré",
        "¿qué cámara me recomiendas?",
        "la cámara cenital se ve mal, ¿qué hago?",
        "he puesto la cámara frontal en la mesa",
        "¿cómo activo la cámara cenital desde el móvil?",
        "cuéntame cómo se graba con OBS",
        "emergencia sería si se quema el led",
    ],
)
def test_talking_about_something_never_executes_it(text: str) -> None:
    """La frase entera tiene que ser la orden. Mencionarla no basta."""
    assert interpret(text, _SCENES) is None


def test_an_empty_message_is_not_a_command() -> None:
    assert interpret("", _SCENES) is None
    assert interpret("   \n  ", _SCENES) is None


def test_a_question_about_stopping_is_not_stopping() -> None:
    assert interpret("¿puedo parar la grabación cuando quiera?", _SCENES) is None


def test_a_normal_message_goes_to_the_conversation() -> None:
    assert interpret("Sirius, ¿por dónde empiezo con el Arduino?", _SCENES) is None


# --- Contrato cerrado ----------------------------------------------------


def test_every_command_of_the_contract_can_be_reached_by_voice() -> None:
    """#127 fija nueve órdenes; ocho se pueden dar hablando.

    ``LIST_SCENES`` no está: las escenas autorizadas ya se ven en el panel, y
    hacer que Sirius las recite en voz alta no aporta nada durante una
    grabación.
    """
    reachable = {
        _command("graba"),
        _command("para"),
        _command("pausa"),
        _command("sigue"),
        _command("marca"),
        _command("parada de emergencia"),
        _command("¿estás grabando?"),
        interpret("cambia a la cenital", _SCENES).command,  # type: ignore[union-attr]
    }

    assert reachable == set(CaptureCommand)
