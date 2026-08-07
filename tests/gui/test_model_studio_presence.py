"""Presencia de partículas de Model Studio (§3 de SIRIUS-MODEL-STUDIO-UI-001)."""

from __future__ import annotations

from itertools import pairwise

from PySide6.QtGui import QColor, QImage
from pytestqt.qtbot import QtBot

from sirius.domain.model_studio import StudioInteractionState
from sirius.presentation.model_studio import theme
from sirius.presentation.model_studio.presence_widget import (
    DEFAULT_SEED,
    PresenceWidget,
    _blink_openness,
)

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


def _vertical_extent(
    image: QImage, x_range: tuple[float, float], y_range: tuple[float, float]
) -> int:
    """Alto en píxeles de lo dibujado dentro de esa ventana normalizada."""
    center = _SIZE / 2
    half = _SIZE * 0.86 / 2
    x_min, x_max = (center + value * half for value in x_range)
    y_min, y_max = (center + value * half for value in y_range)
    rows = [y for x, y in _lit_pixels(image) if x_min <= x <= x_max and y_min <= y <= y_max]
    return max(rows) - min(rows) if rows else 0


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
    """Dos bloques geométricos arriba y una boca de barras debajo.

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
    """Animación ligera: el coste de pintar está acotado por diseño."""
    widget = PresenceWidget(animated=False)
    qtbot.addWidget(widget)

    assert 200 <= widget.particle_count <= 500


def test_presence_is_square(qtbot: QtBot) -> None:
    """Ocupa el ancho de la columna y la misma altura, para que el contexto
    quede pegado debajo en vez de dejar un hueco en medio."""
    widget = PresenceWidget(animated=False)
    qtbot.addWidget(widget)

    assert widget.hasHeightForWidth()
    assert widget.heightForWidth(480) == 480


# --- Ojos robóticos: parpadeo sutil e irregular -------------------------


def test_eyes_blink_fully_but_rarely() -> None:
    """El parpadeo llega a cerrar del todo y ocupa una parte mínima del tiempo.

    Un parpadeo que nunca cierra no se ve; uno que ocurre a todas horas
    distrae mientras se graba.
    """
    samples = [_blink_openness(index * 0.01) for index in range(4000)]

    assert min(samples) < 0.05, "el ojo nunca llega a cerrarse"
    fully_open = sum(1 for value in samples if value >= 0.999)
    assert fully_open / len(samples) > 0.90, "parpadea demasiado a menudo"


def test_blinks_are_irregular() -> None:
    """Los intervalos entre parpadeos no son todos iguales: por eso parecen
    aleatorios, aunque la función sea determinista y reproducible."""
    closed_times = []
    previous = 1.0
    for index in range(6000):
        time = index * 0.01
        value = _blink_openness(time)
        if value < 0.5 <= previous:
            closed_times.append(time)
        previous = value

    assert len(closed_times) >= 3
    gaps = [round(second - first, 2) for first, second in pairwise(closed_times)]
    assert len(set(gaps)) > 1, f"parpadeo con ritmo fijo: {gaps}"


def test_blinking_flattens_the_eyes(qtbot: QtBot) -> None:
    """Al parpadear, el bloque del ojo se aplasta en vertical."""
    closed_at = min((index * 0.01 for index in range(4000)), key=lambda time: _blink_openness(time))

    def eye_height(time: float) -> int:
        widget = PresenceWidget(animated=False)
        qtbot.addWidget(widget)
        widget.resize(_SIZE, _SIZE)
        widget.advance(time)
        return _vertical_extent(_render(widget), (-0.40, -0.10), (-0.30, 0.02))

    assert eye_height(closed_at) < eye_height(0.0)


# --- Boca abstracta: barras tipo ecualizador ----------------------------


def test_mouth_is_almost_flat_at_rest(qtbot: QtBot) -> None:
    widget = PresenceWidget(animated=False)
    qtbot.addWidget(widget)
    widget.resize(_SIZE, _SIZE)
    widget.advance(2.5)

    # Ventana estrecha a propósito: con |x| <= 0.10 el campo de partículas
    # no llega hasta y = 0.32, así que aquí solo hay boca.
    height = _vertical_extent(_render(widget), (-0.10, 0.10), (0.10, 0.32))

    assert height < _SIZE * 0.06, "la boca en reposo debería ser casi una línea"


def test_mouth_bars_rise_while_speaking(qtbot: QtBot) -> None:
    """Al hablar, las barras suben y bajan de forma continua.

    No hay análisis de audio ni sincronización labial: el movimiento sale de
    un pulso constante, así que basta con avanzar el tiempo para verlo.
    """

    def mouth_height(state: StudioInteractionState, time: float) -> int:
        widget = PresenceWidget(animated=False)
        qtbot.addWidget(widget)
        widget.resize(_SIZE, _SIZE)
        widget.set_state(state)
        widget.advance(time)
        return _vertical_extent(_render(widget), (-0.10, 0.10), (0.10, 0.32))

    speaking = max(
        mouth_height(StudioInteractionState.HABLANDO, 2.0 + step * 0.05) for step in range(12)
    )
    resting = mouth_height(StudioInteractionState.PREPARADO, 2.0)

    assert speaking > resting * 1.8


def test_mouth_keeps_moving_while_speaking(qtbot: QtBot) -> None:
    """Agitación continua: dos instantes distintos no dan la misma boca."""
    widget = PresenceWidget(animated=False)
    qtbot.addWidget(widget)
    widget.resize(_SIZE, _SIZE)
    widget.set_state(StudioInteractionState.HABLANDO)

    widget.advance(2.0)
    first = _render(widget)
    widget.advance(0.12)

    assert _render(widget) != first


# --- Contenedor ---------------------------------------------------------


def test_container_is_four_corner_marks_not_a_closed_frame(qtbot: QtBot) -> None:
    """Encuadra la entidad como interfaz; un marco cerrado la leería como cuadro.

    Lo que distingue una marca de esquina de las partículas sueltas del campo
    no es que el lado esté vacío —el campo rodea toda la presencia— sino que
    la marca es un trazo continuo: en la esquina hay una tirada larga de
    píxeles seguidos, y en el centro del lado no.
    """
    widget = PresenceWidget(animated=False)
    qtbot.addWidget(widget)
    widget.resize(_SIZE, _SIZE)
    lit = set(_lit_pixels(_render(widget)))

    center = _SIZE / 2
    half = _SIZE * 0.86 / 2

    def longest_run(x_range: tuple[float, float], y_range: tuple[float, float]) -> int:
        x_min, x_max = (int(center + value * half) for value in x_range)
        y_min, y_max = (int(center + value * half) for value in y_range)
        best = 0
        for y in range(y_min, y_max + 1):
            run = 0
            for x in range(x_min, x_max + 1):
                run = run + 1 if (x, y) in lit else 0
                best = max(best, run)
        return best

    for strip in ((-0.74, -0.70), (0.70, 0.74)):
        left_corner = longest_run((-0.74, -0.56), strip)
        right_corner = longest_run((0.56, 0.74), strip)
        middle = longest_run((-0.20, 0.20), strip)

        assert left_corner > 15, f"falta la marca izquierda en {strip}"
        assert right_corner > 15, f"falta la marca derecha en {strip}"
        assert middle < 8, f"el lado {strip} está cerrado: trazo de {middle} píxeles"
