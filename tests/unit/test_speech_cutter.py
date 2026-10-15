"""El corte en frases de lo que la charla va escribiendo (ADR-243, PA-R03-02).

Lo que se dice, trozo a trozo, tiene que ser lo que da ``prepare_speech_text`` con la
respuesta entera, salvo los blancos: se corta lo mismo de mil maneras y se compara. Y
una frase solo sale cuando está cerrada: ni a media frase, ni con un bloque de código
abierto, ni con una marca sin cerrar.
"""

from __future__ import annotations

import random

import pytest

from sirius.application.prepare_speech_text import prepare_speech_text
from sirius.application.speech_cutter import SpeechCutter

#: Respuestas como las de la charla: con frases, párrafos, listas, enlaces, negritas,
#: código en línea y en bloque, títulos, números con punto y comillas.
RESPUESTAS = (
    "Primera frase, jefe. Y la segunda, más larga. Y la tercera, que tarda más.",
    "Mira **esto**:\n\n```python\nprint(1)\n```\n\nY ya está, listo.",
    "# Plan\n\n- Uno: **rápido**.\n- Dos: `lento`.\n\nVale, ¿empezamos?",
    "Lee [la guía](https://ejemplo.org/guia.html) y dime. ¡Venga!",
    "Son las 3.45 y el 2.º punto dice «hola». ¿Seguro?... Sí.",
    "Un _detalle_ y un nombre_con_guiones, ojo.\n\nOtra línea sin punto",
    "```\ncódigo sin lenguaje. Con puntos. Dentro.\n```\nFuera del bloque. Bien.",
    "> Una cita.\n\n1. Primero.\n2. Segundo.\n\n---\n\nFin.",
    "Texto con *cursiva que cruza. frases* y sigue.",
    "Solo una frase sin punto final",
    "¿Qué tal?\n¡Bien!\nVale.",
    "Tabla:\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\nHecho.",
    "Usa `x.y()` y luego `z`. Después, nada más.",
    "Usa `x y ```python\nprint(1). Dos.\n```\nFin.",
)


def _sin_blancos(texto: str) -> str:
    return " ".join(texto.split())


def _dicho(trozos: list[str]) -> list[str]:
    corte = SpeechCutter()
    frases: list[str] = []
    for trozo in trozos:
        frases.extend(corte.feed(trozo))
    frases.extend(corte.finish())
    return frases


def _trocea(texto: str, azar: random.Random) -> list[str]:
    trozos: list[str] = []
    while texto:
        largo = azar.randint(1, 12)
        trozos.append(texto[:largo])
        texto = texto[largo:]
    return trozos


@pytest.mark.parametrize("respuesta", RESPUESTAS)
def test_trozo_a_trozo_dice_lo_mismo_que_con_la_respuesta_entera(respuesta: str) -> None:
    esperado = _sin_blancos(prepare_speech_text(respuesta))
    azar = random.Random(respuesta)
    maneras = [[respuesta], list(respuesta)] + [_trocea(respuesta, azar) for _ in range(300)]

    distintas = [trozos for trozos in maneras if _sin_blancos(" ".join(_dicho(trozos))) != esperado]

    assert distintas == []


def test_una_frase_sale_en_cuanto_se_cierra_y_no_antes() -> None:
    corte = SpeechCutter()

    assert corte.feed("Primera frase, jefe.") == [], "sin el blanco de detrás puede seguir"
    assert corte.feed(" Y la seg") == ["Primera frase, jefe."]
    assert corte.feed("unda.") == []
    assert corte.finish() == ["Y la segunda."]


def test_de_una_vez_da_todas_las_que_ya_estan_cerradas() -> None:
    corte = SpeechCutter()

    assert corte.feed("Una. Dos. Tr") == ["Una.", "Dos."]
    assert corte.finish() == ["Tr"]


def test_con_un_bloque_de_codigo_abierto_espera_a_que_se_cierre() -> None:
    corte = SpeechCutter()

    assert corte.feed("Mira:\n```python\nprint(1). Y más.\n") == ["Mira:."]
    assert corte.feed("```\nListo. ") == ["Te dejo el código en pantalla.", "Listo."]


def test_un_bloque_abierto_espera_aunque_una_comilla_suelta_se_coma_sus_marcas() -> None:
    # Preparado, «`x y ```» empareja sus cuatro comillas y no deja marca: lo para el bloque.
    corte = SpeechCutter()

    assert corte.feed("Usa `x y ```python\nprint(1). Dos.\n") == []


def test_con_una_marca_sin_cerrar_espera_a_que_se_cierre() -> None:
    corte = SpeechCutter()

    assert corte.feed("Esto es **muy. ") == []
    assert corte.feed("importante**. Fin") == ["Esto es muy.", "importante."]


def test_al_acabar_da_lo_que_quedaba_y_empieza_de_cero() -> None:
    corte = SpeechCutter()
    corte.feed("Hola, jefe")

    assert corte.finish() == ["Hola, jefe"]
    assert corte.finish() == []


def test_lo_que_no_se_lee_no_da_ninguna_frase() -> None:
    assert _dicho(["---"]) == []
    assert _dicho(["\n\n", "  "]) == []
