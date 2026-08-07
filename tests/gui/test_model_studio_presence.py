"""Presencia de partículas de Model Studio (§3 de SIRIUS-MODEL-STUDIO-UI-001)."""

from __future__ import annotations

from PySide6.QtGui import QColor, QImage
from pytestqt.qtbot import QtBot

from sirius.domain.model_studio import StudioInteractionState
from sirius.presentation.model_studio import theme
from sirius.presentation.model_studio.presence_widget import DEFAULT_SEED, PresenceWidget

_SIZE = 360


def _render(widget: PresenceWidget) -> QImage:
    image = QImage(_SIZE, _SIZE, QImage.Format.Format_ARGB32)
    image.fill(QColor(theme.BACKGROUND))
    widget.render(image)
    return image


def _lit_pixels(image: QImage) -> list[tuple[int, int]]:
    """Píxeles que no son el fondo negro: los puntos dibujados."""
    lit: list[tuple[int, int]] = []
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if color.red() + color.green() + color.blue() > 24:
                lit.append((x, y))
    return lit


def test_presence_is_deterministic_for_the_same_seed(qtbot: QtBot) -> None:
    """La misma semilla dibuja la misma presencia: nada depende del azar."""
    first = PresenceWidget(seed=DEFAULT_SEED, animated=False)
    second = PresenceWidget(seed=DEFAULT_SEED, animated=False)
    qtbot.addWidget(first)
    qtbot.addWidget(second)
    first.resize(_SIZE, _SIZE)
    second.resize(_SIZE, _SIZE)

    assert _render(first) == _render(second)


def test_different_seeds_produce_different_presences(qtbot: QtBot) -> None:
    first = PresenceWidget(seed=1, animated=False)
    second = PresenceWidget(seed=2, animated=False)
    qtbot.addWidget(first)
    qtbot.addWidget(second)
    first.resize(_SIZE, _SIZE)
    second.resize(_SIZE, _SIZE)

    assert _render(first) != _render(second)


def test_only_blue_tones_on_black(qtbot: QtBot) -> None:
    """§3.1: paleta limitada a azules. Ni un punto donde el rojo domine."""
    widget = PresenceWidget(animated=False)
    qtbot.addWidget(widget)
    widget.resize(_SIZE, _SIZE)
    image = _render(widget)

    for x, y in _lit_pixels(image):
        color = image.pixelColor(x, y)
        assert color.blue() > color.red(), f"punto no azul en {(x, y)}"
        assert color.blue() >= color.green(), f"punto no azul en {(x, y)}"


def test_two_eyes_and_a_mouth_are_drawn(qtbot: QtBot) -> None:
    """§3: dos concentraciones de puntos arriba y una curva debajo.

    Se comprueba por densidad, no por forma: los dos cuadrantes superiores
    tienen que estar claramente más poblados que el centro entre ellos, y bajo
    ellos tiene que existir la boca.
    """
    widget = PresenceWidget(animated=False)
    qtbot.addWidget(widget)
    widget.resize(_SIZE, _SIZE)
    lit = _lit_pixels(_render(widget))

    center = _SIZE / 2
    half = _SIZE * 0.86 / 2

    def count(x_range: tuple[float, float], y_range: tuple[float, float]) -> int:
        x_min, x_max = (center + value * half for value in x_range)
        y_min, y_max = (center + value * half for value in y_range)
        return sum(1 for x, y in lit if x_min <= x <= x_max and y_min <= y <= y_max)

    left_eye = count((-0.36, -0.12), (-0.26, 0.0))
    right_eye = count((0.12, 0.36), (-0.26, 0.0))
    between_eyes = count((-0.06, 0.06), (-0.26, 0.0))
    mouth = count((-0.34, 0.34), (0.16, 0.34))

    assert left_eye > 0
    assert right_eye > 0
    assert mouth > 0
    # El entrecejo queda despejado: no hay contorno de cabeza ni nariz.
    assert left_eye > between_eyes
    assert right_eye > between_eyes


def test_nothing_is_drawn_outside_the_field(qtbot: QtBot) -> None:
    """Sin base, sin cuello y sin marco: las esquinas quedan negras."""
    widget = PresenceWidget(animated=False)
    qtbot.addWidget(widget)
    widget.resize(_SIZE, _SIZE)
    image = _render(widget)

    corner = int(_SIZE * 0.04)
    for x, y in ((0, 0), (_SIZE - 1, 0), (0, _SIZE - 1), (_SIZE - 1, _SIZE - 1)):
        region = image.copy(max(0, x - corner), max(0, y - corner), corner, corner)
        assert not _lit_pixels(region)


def test_advance_changes_the_frame_while_animated(qtbot: QtBot) -> None:
    widget = PresenceWidget(animated=False)
    qtbot.addWidget(widget)
    widget.resize(_SIZE, _SIZE)
    widget.set_state(StudioInteractionState.PENSANDO)

    before = _render(widget)
    widget.advance(0.5)

    assert _render(widget) != before


def test_deactivated_state_is_frozen(qtbot: QtBot) -> None:
    """Apagado no consume fotogramas: avanzar el tiempo no cambia nada."""
    widget = PresenceWidget(animated=False)
    qtbot.addWidget(widget)
    widget.resize(_SIZE, _SIZE)
    widget.set_state(StudioInteractionState.DESACTIVADO)

    before = _render(widget)
    widget.advance(2.0)

    assert _render(widget) == before


def test_listening_brightens_the_eyes(qtbot: QtBot) -> None:
    """§3.2: los ojos pulsan al escuchar, y se nota respecto al reposo."""

    def eye_brightness(state: StudioInteractionState) -> int:
        widget = PresenceWidget(animated=False)
        qtbot.addWidget(widget)
        widget.resize(_SIZE, _SIZE)
        widget.set_state(state)
        # Instante en el que el pulso está en su máximo.
        widget.advance(0.374)
        image = _render(widget)
        center = _SIZE / 2
        half = _SIZE * 0.86 / 2
        total = 0
        for x, y in _lit_pixels(image):
            in_eye_x = center - 0.36 * half <= x <= center - 0.12 * half
            in_eye_y = center - 0.26 * half <= y <= center
            if in_eye_x and in_eye_y:
                total += image.pixelColor(x, y).blue()
        return total

    assert eye_brightness(StudioInteractionState.ESCUCHANDO) > eye_brightness(
        StudioInteractionState.PREPARADO
    )


def test_animation_stops_when_hidden(qtbot: QtBot) -> None:
    """Mientras el usuario trabaja en la interfaz técnica no se gasta CPU."""
    widget = PresenceWidget()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitUntil(lambda: widget._timer.isActive(), timeout=2000)

    widget.hide()

    assert not widget._timer.isActive()


def test_particle_count_stays_bounded(qtbot: QtBot) -> None:
    """§10: animación ligera. El coste de pintar está acotado por diseño."""
    widget = PresenceWidget(animated=False)
    qtbot.addWidget(widget)

    assert 200 <= widget.particle_count <= 400
