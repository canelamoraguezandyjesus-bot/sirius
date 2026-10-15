"""El corte en frases de lo que la charla va escribiendo (ADR-243, PA-R03-02).

Lo que se dice, trozo a trozo, tiene que ser lo que da ``final_speech_text`` con la
respuesta entera, salvo los blancos y las frases de solo puntos, que no se dicen: se corta
lo mismo de mil maneras y se compara. Esa es ``prepare_speech_text`` sin lo que se quedó
sin cerrar al acabar. Y una frase solo sale cuando está cerrada y lo que sigue ya no puede
cambiarla: ni a media frase, ni con un bloque de código abierto, ni con una marca sin
cerrar, ni antes de ver qué viene detrás.
"""

from __future__ import annotations

import random
import re

import pytest

from sirius.application import prepare_speech_text as preparacion
from sirius.application.prepare_speech_text import prepare_speech_text
from sirius.application.speech_cutter import SpeechCutter, final_speech_text

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
    # Ronda 1 de Codex sobre la PR #688, y lo que salió al buscar la raíz: detrás de una
    # frase, en la misma línea, no son una raya, una viñeta, un título ni una cita; una
    # puntuación detrás de los blancos se pega a la frase de antes; y la sangría de una
    # línea dice si un guion es una viñeta y una almohadilla, un título.
    "Uno. ---\nDos. - tres. # cuatro. > cinco.",
    "Uno.\n- dos. ---\n# tres",
    "Uno. . Dos. Hola. ... Adiós. Vale. , y luego. ; y: ¿sí? ! Fin.",
    "- Uno.\n    - Con cuatro no es viñeta.\n  - Con dos sí.\n\n"
    "    # Con cuatro no es título.\n# Este sí\nFin.",
)

#: Con qué se arman textos al azar: palabras, puntuación, saltos de línea, sangrías y las
#: marcas que ``prepare_speech_text`` quita o deja.
PIEZAS = (
    "Hola", "dos", "y", ". ", ", ", "; ", ": ", "? ", "! ", "… ", "\n", "\n\n", "  ", "    ",
    "- ", "* ", "+ ", "# ", "> ", "1. ", "---", "«", "»", "(", ")", "¿", "¡", "3.45", "...",
    "**", "*", "_", "`", "```", "[x](https://a.b)", "https://a.b/c ",
)  # fmt: skip


def _sin_blancos(texto: str) -> str:
    return " ".join(texto.split())


def _dicho(trozos: list[str]) -> list[str]:
    corte = SpeechCutter()
    frases: list[str] = []
    for trozo in trozos:
        frases.extend(corte.feed(trozo))
    frases.extend(corte.finish())
    return frases


def _lo_que_se_dice(preparado: str) -> str:
    """Las frases de lo preparado, sin las de solo puntos, que no se dicen."""
    frases = re.split(r"(?<=[.!?…])\s+", preparado)
    return _sin_blancos(" ".join(frase for frase in frases if frase.strip(" .\t\n")))


def _trocea(texto: str, azar: random.Random) -> list[str]:
    trozos: list[str] = []
    while texto:
        largo = azar.randint(1, 12)
        trozos.append(texto[:largo])
        texto = texto[largo:]
    return trozos


@pytest.mark.parametrize("respuesta", RESPUESTAS)
def test_trozo_a_trozo_dice_lo_mismo_que_con_la_respuesta_entera(respuesta: str) -> None:
    esperado = _sin_blancos(final_speech_text(respuesta))
    azar = random.Random(respuesta)
    maneras = [[respuesta], list(respuesta)] + [_trocea(respuesta, azar) for _ in range(300)]

    distintas = [trozos for trozos in maneras if _sin_blancos(" ".join(_dicho(trozos))) != esperado]

    assert distintas == []


def test_con_textos_al_azar_tambien_dice_lo_mismo_que_con_el_texto_entero() -> None:
    # Ronda 1 de Codex sobre la PR #688: los casos de una familia salen de textos que nadie
    # pondría en una lista, así que se arman 500 al azar, y cada uno se corta de 12 maneras.
    azar = random.Random(243)
    distintos = []
    for _ in range(500):
        texto = "".join(azar.choice(PIEZAS) for _ in range(azar.randint(2, 14)))
        esperado = _lo_que_se_dice(final_speech_text(texto))
        maneras = [[texto], list(texto)] + [_trocea(texto, azar) for _ in range(10)]
        if any(_lo_que_se_dice(" ".join(_dicho(trozos))) != esperado for trozos in maneras):
            distintos.append(texto)

    assert distintos == []


def test_una_frase_sale_en_cuanto_se_cierra_y_no_antes() -> None:
    corte = SpeechCutter()

    assert corte.feed("Primera frase, jefe.") == [], "sin el blanco de detrás puede seguir"
    assert corte.feed(" ") == [], "y con él, lo que venga aún puede pegarse a ella"
    assert corte.feed("Y la seg") == ["Primera frase, jefe."]
    assert corte.feed("unda.") == []
    assert corte.finish() == ["Y la segunda."]


def test_de_una_vez_da_todas_las_que_ya_estan_cerradas() -> None:
    corte = SpeechCutter()

    assert corte.feed("Una. Dos. Tr") == ["Una.", "Dos."]
    assert corte.finish() == ["Tr"]


def test_con_un_bloque_de_codigo_abierto_espera_a_que_se_cierre() -> None:
    corte = SpeechCutter()

    # La frase que lo presenta no espera al bloque: cerrado, dice que queda en pantalla.
    assert corte.feed("Mira:\n```python\nprint(1). Y más.\n") == ["Mira:."]
    assert corte.feed("```\nListo. Y") == ["Te dejo el código en pantalla.", "Listo."]


def test_tres_comillas_que_no_se_cierran_son_un_bloque_al_acabar() -> None:
    # Ronda 2 de Codex sobre la PR #688: entera, la respuesta las empareja con una comilla
    # suelta y dejaría a la vista «:». Al acabar se cierran, y son un bloque.
    assert prepare_speech_text("Uno. ```: `. Y") == "Uno.:. Y"

    assert _dicho(["Uno. ```", ": `. Y"]) == ["Uno.", "Te dejo el código en pantalla."]


def test_un_bloque_abierto_espera_aunque_una_comilla_suelta_se_coma_sus_marcas() -> None:
    # Preparado, «`x y ```» empareja sus cuatro comillas y no deja marca: lo para el bloque.
    corte = SpeechCutter()

    assert corte.feed("Usa `x y ```python\nprint(1). Dos.\n") == []


@pytest.mark.parametrize("resto", ["---", "- dos", "# no es título", "> no es cita"])
def test_lo_que_sigue_a_una_frase_en_su_linea_no_es_principio_de_linea(resto: str) -> None:
    # Ronda 1 de Codex sobre la PR #688: entera, la respuesta no lo toma por una marca.
    respuesta = f"Uno. {resto}"

    assert _dicho([respuesta]) == ["Uno.", prepare_speech_text(respuesta).removeprefix("Uno. ")]
    # También cuando lo que sigue llega en otro trozo.
    assert _dicho(["Uno. ", f"{resto}. Fin"]) == ["Uno.", f"{resto}.", "Fin"]
    assert _dicho([f"Uno.\n{resto}"]) == _dicho(["Uno."]) + _dicho([resto])


@pytest.mark.parametrize(
    "trozos",
    [
        ["Uno. ", ", dos. Y"],
        ["Uno. *", ", dos*. Y"],
        ["Uno. _", ", dos_. Y"],
        ["Uno. `", ", dos`. Y"],
        ["Uno. [", ", dos](https://ejemplo.org). Y"],
        ["Uno.\n-", " , dos. Y"],
        ["Uno.\n+", " , dos. Y"],
    ],
)
def test_si_lo_que_sigue_puede_pegarse_a_la_frase_espera_a_verlo(trozos: list[str]) -> None:
    # Una puntuación detrás de los blancos se pega a la frase de antes, y una marca puede
    # dejarla a la vista al cerrarse: con lo primero que llega aún no se sabe.
    corte = SpeechCutter()

    dichas = [frase for trozo in trozos for frase in corte.feed(trozo)]

    assert prepare_speech_text("".join(trozos)) == "Uno., dos. Y"
    assert dichas == ["Uno., dos."]


def test_la_sangria_de_una_linea_se_queda_con_ella() -> None:
    # Con cuatro blancos, un guion ya no es una viñeta, y la frase de antes no espera a más.
    corte = SpeechCutter()

    assert corte.feed("- Uno.\n    - dos") == ["Uno."]
    assert corte.finish() == ["- dos"]


def test_una_marca_que_se_empareja_con_otra_ya_llegada_no_deja_cortar() -> None:
    # Entera, la primera estrella va con la de «5*3», que entre cifras no se quita al
    # acabar: si ya ha llegado, el corte lo ve. Si aún no, aquí se diría «5*3», el caso que
    # ADR-243 da por no visto.
    assert final_speech_text("*a*. Hola 5*3. Fin") == "a. Hola 53. Fin"

    assert _dicho(["*a*. Hola 5*3. Fin"]) == ["a.", "Hola 53.", "Fin"]


def test_con_una_marca_sin_cerrar_espera_a_que_se_cierre() -> None:
    corte = SpeechCutter()

    assert corte.feed("Esto es **muy. impor") == []
    assert corte.feed("tante**. Fin") == ["Esto es muy.", "importante."]


def test_al_acabar_da_lo_que_quedaba_y_empieza_de_cero() -> None:
    corte = SpeechCutter()
    assert corte.feed("Hola. Jefe") == ["Hola."]

    assert corte.finish() == ["Jefe"]
    assert corte.finish() == []


@pytest.mark.parametrize(
    ("respuesta", "dichas"),
    [
        ("Mira:\n```python\nprint('secreto')", ["Mira:.", "Te dejo el código en pantalla."]),
        ("Esto es **muy importante", ["Esto es muy importante"]),
        ("Y esto es _también", ["Y esto es también"]),
        ("Muy importante**", ["Muy importante"]),
        ("**5 puntos", ["5 puntos"]),
        ("Usa `rm -rf", ["Usa rm -rf"]),
        # Ronda 3: de un enlace a medias se dice el texto, como de uno entero.
        ("Lee [la gu", ["Lee la gu"]),
        ("Lee [la guía]", ["Lee la guía"]),
        ("Lee [la guía](", ["Lee la guía"]),
        ("Lee [la guía](https://ejemplo.org", ["Lee la guía"]),
        ("Mira [la guía](https://x y luego más.", ["Mira la guía y luego más."]),
        # Si su paréntesis se cierra más adelante, es un enlace entero para la preparación.
        ("Mira [a](b c) y ya", ["Mira a y ya"]),
        ("La nota [1]", ["La nota 1"]),
        # Entre blancos, letras o cifras, una estrella puede ser una multiplicación y un
        # guion bajo, parte de un nombre.
        ("Son 5 * 3, 5*3 y a_b", ["Son 5 * 3, 5*3 y a_b"]),
    ],
)
def test_al_acabar_lo_que_quedo_sin_cerrar_no_se_dice_como_codigo_ni_marca(
    respuesta: str, dichas: list[str]
) -> None:
    # Ronda 2 de Codex sobre la PR #688: ``prepare_speech_text`` solo quita lo emparejado.
    assert _dicho([respuesta]) == dichas
    assert final_speech_text(respuesta) == " ".join(dichas)


def test_una_estrella_entre_blancos_al_principio_de_lo_que_queda_se_queda() -> None:
    # Lo que queda al acabar empieza donde un corte se llevó los blancos: entera, la
    # respuesta tiene un blanco delante de esa estrella, y la deja.
    assert final_speech_text("dos\n- * x") == "dos. * x"

    assert _dicho(["dos\n- * x"]) == ["dos.", "* x"]


#: Lo que no puede llegar a la voz de una respuesta de la prueba, acabe donde acabe: una
#: comilla de código, un corchete, una estrella (ninguna es una multiplicación) o un
#: guion bajo que no va entre letras o cifras.
_MARCA = re.compile(r"[`\[\]*]|(?<![^\W_])_|_(?![^\W_])")


@pytest.mark.parametrize("respuesta", RESPUESTAS)
def test_acabe_donde_acabe_la_respuesta_no_se_dice_ninguna_marca(respuesta: str) -> None:
    # Rondas 2 y 3 de Codex sobre la PR #688, de la misma familia: lo que se queda a medias
    # al acabar. Se para la respuesta en cada carácter, como si el modelo acabara ahí.
    con_marcas = [
        respuesta[:fin]
        for fin in range(len(respuesta) + 1)
        if _MARCA.search(final_speech_text(respuesta[:fin]))
    ]

    assert con_marcas == []


def test_al_acabar_se_sabe_que_hacer_con_cada_construccion_de_prepare_speech_text() -> None:
    # Rondas 2 y 3 de Codex sobre la PR #688: si ``prepare_speech_text`` gana o pierde una
    # construcción, esta prueba falla hasta que ``final_speech_text`` diga qué hace con
    # ella a medias.
    patrones = {
        nombre for nombre, valor in vars(preparacion).items() if isinstance(valor, re.Pattern)
    }

    assert patrones == {
        # Con cierre, y lo que se hace con ellas a medias: el bloque se cierra; del enlace
        # se cierra el destino y se quitan los corchetes; del código en línea, las comillas
        # sueltas; y del énfasis, lo que abre o cierra una palabra.
        "_CODE_FENCE",
        "_FENCE_LANGUAGE",
        "_MARKDOWN_LINK",
        "_INLINE_CODE",
        "_EMPHASIS",
        # Sin cierre: están enteras en cuanto empiezan.
        "_BARE_URL",
        "_HEADING",
        "_LIST_BULLET",
        "_BLOCKQUOTE",
        "_HORIZONTAL_RULE",
        # Blancos.
        "_BLANK_RUN",
        "_SPACE_RUN",
    }


def test_lo_que_no_se_lee_no_da_ninguna_frase() -> None:
    assert _dicho(["---"]) == []
    assert _dicho(["\n\n", "  "]) == []


def test_una_frase_de_solo_puntos_no_se_dice() -> None:
    # Con una raya delante, la respuesta entera empieza por un punto suelto, que no se oye.
    assert prepare_speech_text("---\nHola. Adiós.") == ". Hola. Adiós."

    assert _dicho(["---\nHola. Adiós."]) == ["Hola.", "Adiós."]
