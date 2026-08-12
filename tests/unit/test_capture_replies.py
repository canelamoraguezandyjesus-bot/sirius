"""Cómo suena Sirius al confirmar una orden de grabación.

Lo que más importa aquí no es que las frases tengan gracia, sino que **nunca
afirmen algo que no ocurrió** y que **desaparezcan cuando algo va mal**.
"""

from __future__ import annotations

import pytest

from sirius.application.capture_commands import CaptureCommand
from sirius.application.capture_replies import spoken_confirmation
from sirius.application.studio_capture import CaptureFeedback
from sirius.domain.model_studio import StudioCaptureState


def _ok(state: StudioCaptureState, message: str = "") -> CaptureFeedback:
    return CaptureFeedback(state=state, message=message, succeeded=True)


# --- El hecho primero, la gracia después ---------------------------------


def test_starting_confirms_that_it_is_recording() -> None:
    reply = spoken_confirmation(CaptureCommand.START_RECORDING, _ok(StudioCaptureState.GRABANDO))

    assert "rabando" in reply


def test_stopping_confirms_that_it_stopped() -> None:
    reply = spoken_confirmation(CaptureCommand.STOP_RECORDING, _ok(StudioCaptureState.PREPARADO))

    assert reply
    assert "rabando." not in reply


def test_asking_while_recording_answers_yes() -> None:
    reply = spoken_confirmation(CaptureCommand.GET_STATUS, _ok(StudioCaptureState.GRABANDO))

    assert reply.lower().startswith(("sí", "grabando"))


def test_asking_while_idle_answers_no() -> None:
    reply = spoken_confirmation(CaptureCommand.GET_STATUS, _ok(StudioCaptureState.PREPARADO))

    assert "no" in reply.lower()


# --- Sin humor cuando algo va mal ---------------------------------------


def test_a_failure_is_told_plainly_with_no_joke() -> None:
    """Anexo A del manual: error técnico serio reduce el humor."""
    failure = CaptureFeedback(
        state=StudioCaptureState.ERROR,
        message="La contraseña del sistema de grabación no es válida.",
        succeeded=False,
    )

    assert spoken_confirmation(CaptureCommand.START_RECORDING, failure) == failure.message


def test_an_uncertain_state_is_told_plainly() -> None:
    uncertain = CaptureFeedback(
        state=StudioCaptureState.INCIERTO,
        message="No sé si se está grabando.",
        succeeded=False,
    )

    assert spoken_confirmation(CaptureCommand.STOP_RECORDING, uncertain) == uncertain.message


@pytest.mark.parametrize(
    "state",
    [
        StudioCaptureState.INICIANDO,
        StudioCaptureState.DETENIENDO,
        StudioCaptureState.CAMBIANDO,
    ],
)
def test_an_order_in_flight_never_gets_a_joke(state: StudioCaptureState) -> None:
    """Bromear sobre algo que aún no ha pasado se parece a afirmar que ya pasó."""
    in_flight = CaptureFeedback(state=state, message="", succeeded=True)

    assert spoken_confirmation(CaptureCommand.START_RECORDING, in_flight) == state.label


# --- Nunca sugiere que la orden hizo algo que no hizo --------------------


def test_starting_when_already_recording_says_so() -> None:
    already = _ok(StudioCaptureState.GRABANDO, "Ya estaba grabando; no he abierto una segunda.")

    reply = spoken_confirmation(CaptureCommand.START_RECORDING, already)

    assert "ya" in reply.lower() or "antes" in reply.lower()


def test_stopping_when_nothing_was_recording_says_so() -> None:
    nothing = _ok(StudioCaptureState.PREPARADO, "No había ninguna grabación en curso.")

    reply = spoken_confirmation(CaptureCommand.STOP_RECORDING, nothing)

    assert "no" in reply.lower()


def test_an_unknown_combination_falls_back_to_the_fact() -> None:
    """Antes una confirmación seca que una que no encaje con lo que pasó."""
    odd = _ok(StudioCaptureState.DESACTIVADO, "Model Studio tiene la grabación desactivada.")

    assert spoken_confirmation(CaptureCommand.MARK_MOMENT, odd) == odd.message


# --- Rotación ------------------------------------------------------------


def test_consecutive_orders_do_not_repeat_the_same_phrase() -> None:
    feedback = _ok(StudioCaptureState.GRABANDO)

    first = spoken_confirmation(CaptureCommand.START_RECORDING, feedback, turn=0)
    second = spoken_confirmation(CaptureCommand.START_RECORDING, feedback, turn=1)

    assert first != second


def test_the_rotation_is_reproducible() -> None:
    """Sin azar: el mismo turno da siempre la misma frase."""
    feedback = _ok(StudioCaptureState.GRABANDO)

    assert spoken_confirmation(
        CaptureCommand.START_RECORDING, feedback, turn=7
    ) == spoken_confirmation(CaptureCommand.START_RECORDING, feedback, turn=7)


def test_the_rotation_never_runs_out() -> None:
    feedback = _ok(StudioCaptureState.GRABANDO)

    assert spoken_confirmation(CaptureCommand.START_RECORDING, feedback, turn=1000)


# --- Ninguna frase es un párrafo ----------------------------------------


def test_every_confirmation_is_short_enough_to_say_out_loud() -> None:
    """§4.1: confirmación hablada corta y clara."""
    for command in CaptureCommand:
        for state in StudioCaptureState:
            for turn in range(6):
                reply = spoken_confirmation(command, _ok(state), turn)
                assert len(reply) <= 90, f"{command}/{state}: «{reply}»"
