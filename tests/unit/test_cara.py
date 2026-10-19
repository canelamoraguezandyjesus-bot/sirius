"""La vida de la cara de Sirius, sin ventana (piezas B y C de ADR-259).

Las pruebas de aceptación (``tests/acceptance/test_robot_0_4_cara.py`` y
``test_robot_0_4_gestos.py``) miran lo que dibuja la ventana de verdad. Estas miran el
modelo que la mueve: el parpadeo, la mirada, la respiración, la boca y los gestos, con un
reloj que avanza a mano.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from itertools import groupby, pairwise

import pytest

from sirius.domain.face import (
    BLINK_CLOSED,
    BLINK_CLOSING,
    BLINK_EVERY,
    BLINK_OPENING,
    BREATH_PERIOD,
    GAZE_REACH,
    GESTURE_SECONDS,
    GESTURES_WAITING,
    FaceLife,
    FacePose,
)
from sirius.domain.gestures import GESTURES

_INICIO = 1_000_000.0


def _poses(vida: FaceLife, segundos: float, cada: float = 0.01) -> list[tuple[float, float]]:
    pasos = round(segundos / cada)
    return [(_INICIO + n * cada, vida.pose(_INICIO + n * cada).eyes) for n in range(pasos + 1)]


def test_parpadea_entre_dos_y_seis_segundos_y_nunca_igual() -> None:
    ojos = _poses(FaceLife(seed=3), 120.0)

    cierres = [t for (_, antes), (t, ahora) in pairwise(ojos) if antes > 0.5 >= ahora]
    huecos = [despues - antes for antes, despues in pairwise(cierres)]
    assert all(BLINK_EVERY[0] - 0.02 <= hueco <= BLINK_EVERY[1] + 0.02 for hueco in huecos)
    assert len(set(round(hueco, 2) for hueco in huecos)) > len(huecos) // 2


def test_un_parpadeo_se_cierra_del_todo_y_dura_un_cuarto_de_segundo() -> None:
    ojos = _poses(FaceLife(seed=5), 10.0, cada=0.005)

    cerrados = [t for t, abiertos in ojos if abiertos <= 0.0]
    assert cerrados, "nunca cierra del todo"
    primero = next(t for t, abiertos in ojos if abiertos < 1.0)
    vuelve = next(t for t, abiertos in ojos if t > primero and abiertos >= 1.0)
    assert vuelve - primero == pytest.approx(
        BLINK_CLOSING + BLINK_CLOSED + BLINK_OPENING, abs=0.011
    )


def test_la_mirada_se_queda_cerca_del_frente() -> None:
    vida = FaceLife(seed=7)

    miradas = [vida.pose(_INICIO + n * 0.05).gaze for n in range(2_000)]

    assert all(abs(x) <= GAZE_REACH[0] and abs(y) <= GAZE_REACH[1] for x, y in miradas)
    assert len({(round(x, 3), round(y, 3)) for x, y in miradas}) > 10


def test_respira_con_su_periodo() -> None:
    vida = FaceLife(seed=1)

    medio = vida.pose(_INICIO).breath
    cuarto = vida.pose(_INICIO + BREATH_PERIOD / 4).breath

    assert medio == pytest.approx(0.0)
    assert cuarto == pytest.approx(1.0)


def test_la_boca_alcanza_el_volumen_en_un_quinto_de_segundo_y_se_cierra_en_silencio() -> None:
    vida = FaceLife(seed=1)
    vida.pose(_INICIO)

    abierta = vida.pose(_INICIO + 0.2, level=0.8).mouth
    cerrada = vida.pose(_INICIO + 0.4, level=0.0).mouth

    assert abierta == pytest.approx(0.8, abs=0.01)
    assert cerrada <= 0.01
    assert vida.pose(_INICIO + 0.6, level=3.0).mouth <= 1.0, "más de 1 es 1"


def test_el_mismo_reloj_y_la_misma_semilla_dan_la_misma_cara() -> None:
    una, otra = FaceLife(seed=9), FaceLife(seed=9)

    assert [una.pose(_INICIO + n * 0.1) for n in range(600)] == [
        otra.pose(_INICIO + n * 0.1) for n in range(600)
    ]


def test_un_reloj_que_vuelve_atras_no_la_mueve_hacia_atras() -> None:
    vida = FaceLife(seed=2)
    vida.pose(_INICIO)
    despues = vida.pose(_INICIO + 3.0)

    assert vida.pose(_INICIO + 1.0) == despues


def test_un_salto_de_una_hora_no_deja_nada_a_medias() -> None:
    vida = FaceLife(seed=4)
    vida.pose(_INICIO)

    tras_la_hora = [vida.pose(_INICIO + 3_600 + n * 0.02) for n in range(500)]

    assert any(pose.eyes <= 0.2 for pose in tras_la_hora), "tras el salto no parpadea"
    assert all(abs(pose.gaze[0]) <= GAZE_REACH[0] for pose in tras_la_hora)


def test_tras_dias_sin_mirarla_empieza_de_nuevo_en_el_acto() -> None:
    vida = FaceLife(seed=6)
    vida.pose(_INICIO)

    empieza = time.perf_counter()
    vida.pose(_INICIO + 3 * 86_400)
    tarda = time.perf_counter() - empieza

    assert tarda < 0.05, "repasa cada parpadeo de tres días en vez de empezar de nuevo"
    siguientes = [vida.pose(_INICIO + 3 * 86_400 + n * 0.02) for n in range(500)]
    assert any(pose.eyes <= 0.2 for pose in siguientes), "tras el salto no parpadea"


#: Lo que hace cada gesto de la lista, en lo que dice la vida de la cara: de 0, nada, a 1.
_LO_QUE_HACE: dict[str, Callable[[FacePose], float]] = {
    "ceja_arriba": lambda pose: pose.brow_raise,
    "cejas_arriba": lambda pose: pose.brows,
    "cejas_fruncidas": lambda pose: -pose.brows,
    "sonrisa": lambda pose: pose.smile,
    "guino": lambda pose: pose.wink,
    "ojos_en_blanco": lambda pose: pose.gaze[1],
    "asiente": lambda pose: abs(pose.head[1]),
    "niega": lambda pose: abs(pose.head[0]),
}


def _en_reposo(pose: FacePose) -> bool:
    return (
        pose.gesture is None
        and pose.brows == pose.brow_raise == pose.wink == pose.smile == 0.0
        and pose.head == (0.0, 0.0)
    )


def test_cada_gesto_de_la_lista_dice_lo_que_hace() -> None:
    assert set(_LO_QUE_HACE) == set(GESTURES) == set(GESTURE_SECONDS)


@pytest.mark.parametrize("gesto", GESTURES)
def test_cada_gesto_se_hace_dura_lo_suyo_y_vuelve_al_reposo(gesto: str) -> None:
    vida = FaceLife(seed=3)
    vida.pose(_INICIO)

    vida.make(gesto)
    poses = [vida.pose(_INICIO + n * 0.01) for n in range(1, 300)]

    haciendolo = [pose for pose in poses if pose.gesture == gesto]
    cuanto = [_LO_QUE_HACE[gesto](pose) for pose in haciendolo]
    assert len(haciendolo) * 0.01 == pytest.approx(GESTURE_SECONDS[gesto], abs=0.02)
    assert max(cuanto) >= 0.5, "no se le nota"
    assert cuanto[0] < 0.15 and cuanto[-1] < 0.15, "empieza o acaba de golpe"
    hacia_el_final = cuanto[round(len(cuanto) * 0.55) : round(len(cuanto) * 0.8)]
    assert max(hacia_el_final) >= 0.5, "se deshace antes de tiempo"
    assert all(_en_reposo(pose) for pose in poses[len(haciendolo) + 1 :])


def test_los_gestos_van_uno_detras_de_otro_y_los_de_mas_se_dejan() -> None:
    vida = FaceLife(seed=3)
    vida.pose(_INICIO)

    for gesto in ("sonrisa", "guino", "asiente", "niega", "ceja_arriba"):
        vida.make(gesto)
    haciendo = [vida.pose(_INICIO + n * 0.01).gesture for n in range(1, 600)]
    hechos = [(gesto, len(list(veces))) for gesto, veces in groupby(haciendo) if gesto]

    assert GESTURES_WAITING == 3
    assert [gesto for gesto, _ in hechos] == ["sonrisa", "guino", "asiente"]
    for gesto, veces in hechos:
        assert veces * 0.01 == pytest.approx(GESTURE_SECONDS[gesto], abs=0.02), gesto


def test_un_gesto_que_no_es_de_la_lista_no_se_hace() -> None:
    vida = FaceLife(seed=3)
    vida.pose(_INICIO)

    vida.make("bailar")

    assert all(_en_reposo(vida.pose(_INICIO + n * 0.01)) for n in range(1, 200))


def test_asentir_va_abajo_y_arriba_y_negar_a_un_lado_y_al_otro() -> None:
    for gesto, eje in (("asiente", 1), ("niega", 0)):
        vida = FaceLife(seed=3)
        vida.pose(_INICIO)
        vida.make(gesto)

        cabeza = [vida.pose(_INICIO + n * 0.01).head for n in range(1, 120)]

        assert min(c[eje] for c in cabeza) < -0.3 and max(c[eje] for c in cabeza) > 0.3
        assert all(c[1 - eje] == 0.0 for c in cabeza)
