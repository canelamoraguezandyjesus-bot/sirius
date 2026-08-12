"""Vocabulario de estados de Model Studio (R-04 de la reconciliación)."""

from __future__ import annotations

import pytest

from sirius.domain.model_studio import StudioCaptureState, StudioInteractionState


def test_every_interaction_state_has_a_visible_label() -> None:
    """Ningún estado puede llegar a la barra superior sin texto que mostrar."""
    for state in StudioInteractionState:
        assert state.label
        assert state.label == state.label.upper()


def test_every_capture_state_has_a_visible_label() -> None:
    for state in StudioCaptureState:
        assert state.label
        assert state.label == state.label.upper()


def test_reconciled_interaction_states_are_all_present() -> None:
    """Las tres piezas listaban conjuntos distintos e incompatibles (MS-A06).

    ``SINTETIZANDO`` faltaba en la especificación de interfaz y ``EJECUTANDO``
    faltaba en #126; ambos existen aquí, y la lista completa es la unificada.
    """
    assert {state.name for state in StudioInteractionState} == {
        "DESACTIVADO",
        "PREPARADO",
        "ESCUCHANDO",
        "TRANSCRIBIENDO",
        "REVISANDO",
        "PENSANDO",
        "EJECUTANDO",
        "SINTETIZANDO",
        "HABLANDO",
        "ERROR",
    }


def test_reconciled_capture_states_are_all_present() -> None:
    """``INICIANDO``, ``CAMBIANDO`` y ``DETENIENDO`` faltaban en la interfaz."""
    assert {state.name for state in StudioCaptureState} == {
        "DESACTIVADO",
        "PREPARADO",
        "INICIANDO",
        "GRABANDO",
        "PAUSADO",
        "CAMBIANDO",
        "DETENIENDO",
        "ERROR",
        "INCIERTO",
    }


@pytest.mark.parametrize(
    "state",
    [
        StudioInteractionState.DESACTIVADO,
        StudioInteractionState.TRANSCRIBIENDO,
        StudioInteractionState.PENSANDO,
        StudioInteractionState.EJECUTANDO,
        StudioInteractionState.SINTETIZANDO,
    ],
)
def test_states_with_work_in_flight_block_typing(state: StudioInteractionState) -> None:
    assert not state.accepts_typing


@pytest.mark.parametrize(
    "state",
    [
        StudioInteractionState.PREPARADO,
        StudioInteractionState.ESCUCHANDO,
        StudioInteractionState.REVISANDO,
        StudioInteractionState.HABLANDO,
        StudioInteractionState.ERROR,
    ],
)
def test_states_without_work_in_flight_allow_typing(state: StudioInteractionState) -> None:
    """Escribir tiene que seguir siendo posible incluso tras un error."""
    assert state.accepts_typing


def test_only_confirmed_recording_turns_on_the_red_indicator() -> None:
    """#127: la confirmación procede del backend, no de la frase del modelo.

    ``INICIANDO`` e ``INCIERTO`` son justo los momentos en los que sería fácil
    —y falso— dar por hecho que ya se está grabando.
    """
    for state in StudioCaptureState:
        assert state.is_recording_confirmed is (state is StudioCaptureState.GRABANDO)
