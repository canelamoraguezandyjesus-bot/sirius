"""Grabación, escenas y marcas de Model Studio: pruebas MS de #127.

Cubre las que no exigen cámaras ni programas reales, que son casi todas: MS-001
a MS-006, MS-007, MS-009, MS-010, MS-011, MS-013 y MS-014. Las que sí exigen
hardware —MS-008 con archivo reproducible, MS-012, MS-015 a MS-018— quedan para
la ventana manual autorizada.

Todo va con un sistema de captura simulado: sin red, sin puertos y sin OBS.
"""

from __future__ import annotations

import pytest

from sirius.adapters.capture.fake import FakeCaptureBackend, FakeCaptureJournal
from sirius.application.studio_capture import StudioCaptureUseCase
from sirius.domain.capture import Scene, SceneRegistry
from sirius.domain.model_studio import StudioCaptureState
from sirius.ports.capture_backend import CaptureError, CaptureErrorKind

_SCENES = SceneRegistry(
    (
        Scene("pantalla", "Pantalla", "Pantalla", ("pantalla", "escritorio"), is_fallback=True),
        Scene("frontal", "Cámara frontal", "Cámara frontal", ("frontal", "camara frontal")),
        Scene("cenital", "Cámara cenital", "Cámara cenital", ("cenital", "desde arriba")),
    )
)


def _use_case(
    backend: FakeCaptureBackend | None = None,
    scenes: SceneRegistry = _SCENES,
    journal: FakeCaptureJournal | None = None,
    *,
    enabled: bool = False,
) -> StudioCaptureUseCase:
    return StudioCaptureUseCase(
        backend=backend or FakeCaptureBackend(),
        scenes=scenes,
        journal=journal,
        enabled=enabled,
    )


def _enabled(
    backend: FakeCaptureBackend | None = None, journal: FakeCaptureJournal | None = None
) -> tuple[StudioCaptureUseCase, FakeCaptureBackend]:
    backend = backend or FakeCaptureBackend()
    use_case = _use_case(backend, journal=journal)
    use_case.enable()
    return use_case, backend


# --- MS-001: desactivado no conecta ni graba ----------------------------


def test_disabled_module_never_connects_or_records() -> None:
    """Abrir Sirius no puede conectar ni grabar nada."""
    backend = FakeCaptureBackend()
    use_case = _use_case(backend)

    assert not use_case.is_enabled
    assert not backend.is_connected()

    feedback = use_case.start_recording()

    assert feedback.state is StudioCaptureState.DESACTIVADO
    assert not feedback.succeeded
    assert "start_recording" not in backend.commands


def test_disabled_module_refuses_every_command() -> None:
    use_case = _use_case()

    for feedback in (
        use_case.start_recording(),
        use_case.stop_recording(),
        use_case.pause_recording(),
        use_case.switch_scene("frontal"),
        use_case.mark_moment(),
    ):
        assert feedback.state is StudioCaptureState.DESACTIVADO
        assert not feedback.succeeded


# --- MS-002: PREPARADO solo tras confirmar ------------------------------


def test_ready_only_after_the_backend_confirms() -> None:
    use_case, backend = _enabled()

    assert use_case.last_known_state is StudioCaptureState.PREPARADO
    # No se declaró preparado por conectar: se preguntó.
    assert "get_status" in backend.commands


def test_a_failed_connection_never_reports_ready() -> None:
    backend = FakeCaptureBackend(
        connect_error=CaptureError(CaptureErrorKind.AUTHENTICATION, "contraseña")
    )
    use_case = _use_case(backend)

    feedback = use_case.enable()

    assert feedback.state is StudioCaptureState.ERROR
    assert not feedback.succeeded
    assert "contraseña" in feedback.message


def test_without_authorized_scenes_the_module_does_not_turn_on() -> None:
    use_case = _use_case(scenes=SceneRegistry())

    feedback = use_case.enable()

    assert feedback.state is StudioCaptureState.DESACTIVADO
    assert not use_case.is_enabled


# --- MS-003 y MS-004: una orden, una sola sesión ------------------------


def test_one_order_starts_exactly_one_recording() -> None:
    use_case, backend = _enabled()

    feedback = use_case.start_recording()

    assert feedback.state is StudioCaptureState.GRABANDO
    assert feedback.state.is_recording_confirmed
    assert backend.commands.count("start_recording") == 1


def test_starting_twice_does_not_open_a_second_session() -> None:
    """Idempotente: repetir la orden no duplica la grabación."""
    use_case, backend = _enabled()
    use_case.start_recording()

    feedback = use_case.start_recording()

    assert feedback.succeeded
    assert feedback.state is StudioCaptureState.GRABANDO
    assert "segunda sesión" in feedback.message
    assert backend.commands.count("start_recording") == 1


def test_a_recording_started_by_hand_is_noticed() -> None:
    """Si alguien pulsó grabar en el propio programa, no se abre otra.

    La comprobación pregunta al backend en vez de mirar lo que Sirius recuerda,
    y por eso se entera.
    """
    use_case, backend = _enabled()
    backend.simulate_manual_recording()

    feedback = use_case.start_recording()

    assert "segunda sesión" in feedback.message
    assert backend.commands.count("start_recording") == 0


# --- MS-005 y MS-006: escenas de la lista blanca ------------------------


def test_an_authorized_scene_is_activated_exactly() -> None:
    use_case, backend = _enabled()

    feedback = use_case.switch_scene("cenital")

    assert feedback.succeeded
    assert feedback.scene_id == "cenital"
    assert "switch_scene:Cámara cenital" in backend.commands


def test_a_scene_can_be_named_out_loud() -> None:
    """La voz y la interfaz producen el mismo comando interno (MS-017)."""
    use_case, _ = _enabled()

    by_voice = use_case.switch_scene("desde arriba")
    by_id = use_case.switch_scene("cenital")

    assert by_voice.scene_id == by_id.scene_id == "cenital"


def test_accents_and_capitals_do_not_break_a_spoken_scene() -> None:
    """Una transcripción escribe «cámara» o «camara» según le parece."""
    use_case, _ = _enabled()

    assert use_case.switch_scene("CÁMARA FRONTAL").scene_id == "frontal"
    assert use_case.switch_scene("camara frontal").scene_id == "frontal"


def test_an_unknown_scene_does_not_change_the_shot() -> None:
    """Adivinar la escena más parecida sería cambiar de plano por error."""
    use_case, backend = _enabled()
    use_case.switch_scene("frontal")
    commands_before = list(backend.commands)

    feedback = use_case.switch_scene("la de la ventana")

    assert not feedback.succeeded
    assert "no está autorizada" in feedback.message
    assert backend.commands == commands_before


def test_a_scene_that_exists_in_obs_but_is_not_authorized_is_refused() -> None:
    """La lista blanca manda sobre lo que el programa tenga configurado."""
    backend = FakeCaptureBackend(scene_names=("Pantalla", "Escena secreta"))
    use_case = _use_case(backend)
    use_case.enable()

    feedback = use_case.switch_scene("Escena secreta")

    assert not feedback.succeeded
    assert not any(command.startswith("switch_scene") for command in backend.commands)


# --- MS-007: pausa, o se dice que no se puede ---------------------------


def test_pause_and_resume_work_when_the_backend_supports_them() -> None:
    use_case, _ = _enabled()
    use_case.start_recording()

    assert use_case.pause_recording().state is StudioCaptureState.PAUSADO
    assert use_case.resume_recording().state is StudioCaptureState.GRABANDO


def test_a_backend_without_pause_says_so_instead_of_pretending() -> None:
    use_case, _ = _enabled(FakeCaptureBackend(supports_pause=False))
    use_case.start_recording()

    feedback = use_case.pause_recording()

    assert not feedback.succeeded
    assert "no admite" in feedback.message


# --- MS-009: parar dos veces es seguro ----------------------------------


def test_stopping_twice_is_safe_and_not_destructive() -> None:
    use_case, _ = _enabled()
    use_case.start_recording()

    first = use_case.stop_recording()
    second = use_case.stop_recording()

    assert first.state is StudioCaptureState.PREPARADO
    assert second.succeeded
    assert "No había ninguna grabación" in second.message


def test_stopping_returns_the_resulting_file() -> None:
    """#127: la grabación queda identificada y reproducible."""
    use_case, _ = _enabled()
    use_case.start_recording()

    feedback = use_case.stop_recording()

    assert feedback.output_path


# --- MS-010: marcas de momento ------------------------------------------


def test_a_mark_records_its_relative_time_and_a_label() -> None:
    journal = FakeCaptureJournal()
    use_case, backend = _enabled(journal=journal)
    use_case.start_recording()
    backend.advance(95.0)

    feedback = use_case.mark_moment("aquí suelda")

    assert feedback.succeeded
    assert use_case.marks[-1].label == "aquí suelda"
    assert use_case.marks[-1].elapsed_seconds == pytest.approx(95.0)
    assert journal.marks == [("aquí suelda", 95.0)]
    assert "01:35" in feedback.message


def test_a_mark_without_a_label_still_gets_one() -> None:
    use_case, _ = _enabled()
    use_case.start_recording()

    use_case.mark_moment()

    assert use_case.marks[-1].label


def test_marking_without_a_recording_is_refused() -> None:
    """Marcaría un momento de un vídeo que no existe."""
    use_case, _ = _enabled()

    feedback = use_case.mark_moment("algo")

    assert not feedback.succeeded
    assert use_case.marks == ()


def test_a_new_recording_starts_with_no_marks() -> None:
    use_case, _ = _enabled()
    use_case.start_recording()
    use_case.mark_moment("de la toma anterior")
    use_case.stop_recording()

    use_case.start_recording()

    assert use_case.marks == ()


# --- MS-011: un timeout no afirma éxito ---------------------------------


def test_a_timeout_leaves_the_state_uncertain_not_stopped() -> None:
    """No saber no es lo mismo que saber que no."""
    backend = FakeCaptureBackend(
        command_error=CaptureError(CaptureErrorKind.TIMEOUT, "sin respuesta")
    )
    use_case = _use_case(backend)
    use_case.enable()

    feedback = use_case.start_recording()

    assert feedback.state is StudioCaptureState.INCIERTO
    assert not feedback.succeeded
    assert "comprobarlo" in feedback.message


def test_an_uncertain_state_never_lights_the_red_indicator() -> None:
    for state in (
        StudioCaptureState.INCIERTO,
        StudioCaptureState.INICIANDO,
        StudioCaptureState.DETENIENDO,
        StudioCaptureState.ERROR,
    ):
        assert not state.is_recording_confirmed


def test_refreshing_reconciles_the_real_state() -> None:
    """La reconciliación de #127: tras un corte, se vuelve a preguntar."""
    use_case, backend = _enabled()
    backend.simulate_manual_recording()

    feedback = use_case.refresh_status()

    assert feedback.state is StudioCaptureState.GRABANDO


# --- MS-013: fuente perdida, reserva o degradación ----------------------


def test_the_fallback_scene_is_the_marked_one() -> None:
    use_case, _ = _enabled()

    feedback = use_case.fall_back_to_safe_scene()

    assert feedback.scene_id == "pantalla"


def test_without_a_fallback_the_degradation_is_reported() -> None:
    use_case = StudioCaptureUseCase(FakeCaptureBackend(), SceneRegistry(), enabled=True)

    feedback = use_case.fall_back_to_safe_scene()

    assert not feedback.succeeded


# --- Parada de emergencia ------------------------------------------------


def test_emergency_stop_acts_immediately_and_leaves_a_trace() -> None:
    """Si alguien pulsa esto, quiere que deje de grabar ya."""
    journal = FakeCaptureJournal()
    use_case, backend = _enabled(journal=journal)
    use_case.start_recording()

    feedback = use_case.emergency_stop()

    assert feedback.state is StudioCaptureState.PREPARADO
    assert "stop_recording" in backend.commands
    assert any(entry[0] == "emergency_stop" for entry in journal.entries)


def test_a_failed_emergency_stop_never_claims_success() -> None:
    backend = FakeCaptureBackend(
        command_error=CaptureError(CaptureErrorKind.TIMEOUT, "sin respuesta")
    )
    use_case = _use_case(backend)
    use_case.enable()

    feedback = use_case.emergency_stop()

    assert feedback.state is StudioCaptureState.INCIERTO
    assert not feedback.succeeded


def test_emergency_stop_is_recorded_even_when_disabled() -> None:
    journal = FakeCaptureJournal()
    use_case = _use_case(journal=journal)

    use_case.emergency_stop()

    assert any(entry[0] == "emergency_stop" for entry in journal.entries)


# --- MS-014: cierre y reapertura ----------------------------------------


def test_disabling_does_not_stop_an_ongoing_recording() -> None:
    """Cerrar Sirius no puede llevarse por delante una toma en curso."""
    use_case, backend = _enabled()
    use_case.start_recording()

    use_case.disable()

    assert "stop_recording" not in backend.commands
    assert not backend.is_connected()


def test_reopening_asks_the_backend_instead_of_assuming() -> None:
    """Al volver, el estado se pregunta; no se recuerda."""
    backend = FakeCaptureBackend()
    first_session = _use_case(backend)
    first_session.enable()
    first_session.start_recording()
    first_session.disable()

    second_session = _use_case(backend)
    feedback = second_session.enable()

    assert feedback.state is StudioCaptureState.GRABANDO
    assert backend.commands.count("get_status") >= 2


# --- Registro local mínimo ----------------------------------------------


def test_the_journal_records_commands_without_any_audiovisual_content() -> None:
    journal = FakeCaptureJournal()
    use_case, backend = _enabled(journal=journal)
    use_case.start_recording()
    backend.advance(10.0)
    use_case.switch_scene("frontal")
    use_case.mark_moment("prueba")
    use_case.stop_recording()

    recorded = " ".join(f"{c} {r} {d}" for c, r, d in journal.entries)

    assert "start_recording" in recorded
    assert "switch_scene" in recorded
    assert "stop_recording" in recorded
    # Sin rutas de vídeo ni contenido: solo comando, resultado y escena.
    assert ".mkv" not in recorded
    assert "C:/" not in recorded


# --- Lista blanca -------------------------------------------------------


def test_duplicate_scene_identifiers_are_rejected_at_construction() -> None:
    with pytest.raises(ValueError, match="mismo identificador"):
        SceneRegistry(
            (
                Scene("uno", "Uno", "Uno"),
                Scene("uno", "Otro", "Otro"),
            )
        )


def test_an_ambiguous_alias_resolves_to_nothing() -> None:
    """Dos escenas con el mismo alias son un error de configuración."""
    registry = SceneRegistry(
        (
            Scene("a", "A", "A", ("camara",)),
            Scene("b", "B", "B", ("camara",)),
        )
    )

    assert registry.resolve("camara") is None
