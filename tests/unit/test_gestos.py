"""Las etiquetas de los gestos, quitadas de lo que escribe el modelo (pieza C de la 0.4,
ADR-261).

Las pruebas de aceptación (``tests/acceptance/test_robot_0_4_gestos.py``) miran la ventana,
la voz y la base de verdad. Estas miran el filtro: qué es una etiqueta y qué no, qué
blanco se va con ella, y que a trozos dé lo mismo que entero, se corte por donde se corte.
"""

from __future__ import annotations

import itertools
import random

import pytest

from sirius.domain.gestures import (
    GESTURES,
    Gesture,
    GestureFilter,
    gestures_line,
    normalize,
    strip_gestures,
)

#: Lo que escribe el modelo, lo que queda y los gestos de la lista que hace.
_CASOS: list[tuple[str, str, tuple[str, ...]]] = [
    (
        "Hombre, [ceja_arriba] eso habrá que verlo.",
        "Hombre, eso habrá que verlo.",
        ("ceja_arriba",),
    ),
    ("Vale, [bailar] lo que tú digas.", "Vale, lo que tú digas.", ()),
    ("[sonrisa] Claro.", "Claro.", ("sonrisa",)),
    ("Claro. [sonrisa]", "Claro.", ("sonrisa",)),
    ("Claro. [sonrisa] ", "Claro.", ("sonrisa",)),
    ("Eso es mentira [ceja_arriba].", "Eso es mentira.", ("ceja_arriba",)),
    ("Hola[sonrisa].", "Hola.", ("sonrisa",)),
    ("Hombre,[ceja_arriba] eso", "Hombre, eso", ("ceja_arriba",)),
    ("Vale. [sonrisa]\n\nMe parece bien.", "Vale.\n\nMe parece bien.", ("sonrisa",)),
    ("Hola [sonrisa] [guino] amigo", "Hola amigo", ("sonrisa", "guino")),
    ("[sonrisa][guino]Hola", "Hola", ("sonrisa", "guino")),
    ("[Guiño] Ya.", "Ya.", ("guino",)),
    ("[ceja arriba] Ya.", "Ya.", ("ceja_arriba",)),
    ("[OJOS-EN-BLANCO] Qué remedio.", "Qué remedio.", ("ojos_en_blanco",)),
    # Lo que no es una etiqueta se queda como está.
    ("datos[clave] y lista[0]", "datos[clave] y lista[0]", ()),
    ("Mira [texto](https://ejemplo.org) ya", "Mira [texto](https://ejemplo.org) ya", ()),
    ("`[sonrisa]` es la etiqueta", "`[sonrisa]` es la etiqueta", ()),
    (
        "```\n[database]\nx = 1\n```\n[guino] Hecho.",
        "```\n[database]\nx = 1\n```\nHecho.",
        ("guino",),
    ),
    # Un bloque abierto con cuatro comillas no lo cierran tres, sino cuatro o más.
    (
        "````\n```\n[sonrisa] dentro\n```\n````\n[guino] Fuera.",
        "````\n```\n[sonrisa] dentro\n```\n````\nFuera.",
        ("guino",),
    ),
    ("````\n[sonrisa]\n`````\n[guino] Hecho.", "````\n[sonrisa]\n`````\nHecho.", ("guino",)),
    ("Una [nota del autor] aquí", "Una [nota del autor] aquí", ()),
    ("- [x] hecho\n- [ ] no", "- [x] hecho\n- [ ] no", ()),
    ("Cita [1] y [a] y [uno dos tres cuatro]", "Cita [1] y [a] y [uno dos tres cuatro]", ()),
    ("Y [uno_dos_tres_cuatro] no", "Y [uno_dos_tres_cuatro] no", ()),
    ("Abro [ y no cierro", "Abro [ y no cierro", ()),
    ("Acaba en [sonr", "Acaba en [sonr", ()),
    ("Sin nada raro.  Dos blancos  y fin  ", "Sin nada raro.  Dos blancos  y fin  ", ()),
    ("", "", ()),
]


@pytest.mark.parametrize(("texto", "limpio", "gestos"), _CASOS, ids=[c[0][:30] for c in _CASOS])
def test_quita_las_etiquetas_y_da_los_gestos_de_la_lista(
    texto: str, limpio: str, gestos: tuple[str, ...]
) -> None:
    assert strip_gestures(texto) == (limpio, gestos)


def test_la_lista_va_como_la_escribe_el_modelo_y_lleva_el_ejemplo_del_plan() -> None:
    assert "ceja_arriba" in GESTURES
    assert len(set(GESTURES)) == len(GESTURES)
    assert all(normalize(gesto) == gesto for gesto in GESTURES)


def test_sus_instrucciones_nombran_cada_gesto_entre_corchetes() -> None:
    linea = gestures_line()

    assert all(f"[{gesto}]" in linea for gesto in GESTURES)


def _a_trozos(
    texto: str, cortes: list[int], *, cortada: bool = False
) -> tuple[str, tuple[str, ...]]:
    filtro = GestureFilter()
    piezas = []
    previo = 0
    for corte in [*cortes, len(texto)]:
        piezas += filtro.feed(texto[previo:corte])
        previo = corte
    piezas += filtro.finish(cut=cortada)
    return (
        "".join(pieza for pieza in piezas if isinstance(pieza, str)),
        tuple(pieza.name for pieza in piezas if isinstance(pieza, Gesture)),
    )


def test_a_trozos_da_lo_mismo_que_entero_se_corte_por_donde_se_corte() -> None:
    for texto, _, _ in _CASOS:
        entero = strip_gestures(texto)
        posibles = range(len(texto) + 1)
        assert all(_a_trozos(texto, [corte]) == entero for corte in posibles), texto
        assert _a_trozos(texto, list(range(1, len(texto)))) == entero, f"letra a letra: {texto}"
        if len(texto) <= 45:
            assert all(
                _a_trozos(texto, list(cortes)) == entero
                for cortes in itertools.combinations(posibles, 2)
            ), texto


_PEDAZOS = (
    "Hola", "qué", " ", "  ", "\n", "\n\n", ".", ",", "!", "¿", "«", "»", "(", ")", "[", "]",
    "`", "```", "x", "1", "_", "-", "ñ", "datos", "[sonrisa]", "[ceja_arriba]", "[bailar]",
    "[Guiño]", "[ojos en blanco]", "[texto](u)",
)  # fmt: skip


def _al_azar(semilla: int, cuantos: int) -> list[str]:
    azar = random.Random(semilla)
    return [
        "".join(azar.choice(_PEDAZOS) for _ in range(azar.randint(0, 14))) for _ in range(cuantos)
    ]


def test_al_azar_a_trozos_da_lo_mismo_y_ningun_gesto_queda_a_la_vista() -> None:
    azar = random.Random(11)
    for texto in _al_azar(7, 3_000):
        cortes = sorted(azar.sample(range(len(texto) + 1), min(len(texto) + 1, 4)))
        for cortada in (False, True):
            limpio = strip_gestures(texto, cut=cortada)
            assert _a_trozos(texto, cortes, cortada=cortada) == limpio, (texto, cortes)
            if "`" not in texto:
                assert not any(
                    f"[{gesto}]" in limpio[0] and f"[{gesto}](" not in limpio[0]
                    for gesto in GESTURES
                ), texto


def test_lo_que_no_lleva_corchetes_no_cambia_ni_un_byte() -> None:
    for texto in _al_azar(5, 3_000):
        sin_corchetes = texto.replace("[", "")
        assert strip_gestures(sin_corchetes) == (sin_corchetes, ())
        assert strip_gestures(sin_corchetes, cut=True) == (sin_corchetes, ())


def test_cada_gesto_va_delante_de_lo_primero_que_se_ve_detras_de_el() -> None:
    filtro = GestureFilter()

    piezas = filtro.feed("Vale. [sonrisa] Me parece") + filtro.feed(" bien.") + filtro.finish()

    assert piezas == ["Vale. ", Gesture("sonrisa"), "Me parece", " bien."]


def test_un_blanco_del_final_espera_por_si_va_delante_de_una_etiqueta() -> None:
    filtro = GestureFilter()

    assert filtro.feed("uno ") == ["uno"]
    assert filtro.feed("[guino].") == [Gesture("guino"), "."]
    assert filtro.finish() == []


def test_una_respuesta_cortada_deja_la_etiqueta_a_medias_y_lo_demas_tal_cual() -> None:
    assert strip_gestures("Hola, [ceja_arr", cut=True) == ("Hola, ", ())
    assert strip_gestures("Hola, [ceja_arriba]", cut=True) == ("Hola, ", ())
    assert strip_gestures("uno dos ", cut=True) == ("uno dos ", ())
    assert strip_gestures("Mira `[sonr", cut=True) == ("Mira `[sonr", ())
