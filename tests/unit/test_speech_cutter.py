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
from markdown_it import MarkdownIt

from sirius.application import prepare_speech_text as preparacion
from sirius.application import speech_cutter as cortador
from sirius.application.prepare_speech_text import prepare_speech_text
from sirius.application.speech_cutter import SpeechCutter, final_speech_text
from sirius.presentation import message_view as ventana

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


def test_lo_que_sigue_a_un_bloque_empieza_su_linea() -> None:
    # Una viñeta o un título detrás de un bloque siguen siéndolo: la marca del bloque deja
    # detrás su salto de línea.
    respuesta = "Mira:\n```\nx\n```\n- Uno.\n# Dos."

    assert final_speech_text(respuesta) == "Mira:. Te dejo el código en pantalla. Uno. Dos."
    assert _dicho(list(respuesta)) == ["Mira:.", "Te dejo el código en pantalla.", "Uno.", "Dos."]


def test_la_frase_que_presenta_un_bloque_no_espera_a_lo_que_aun_no_se_sabe_dentro() -> None:
    # Una línea a medias dentro del bloque aún puede ser una raya, y unas comillas dentro
    # aún pueden abrir otro bloque en la ventana, pero el bloque ya es código: la frase que
    # lo presenta sale sin esperar.
    assert SpeechCutter().feed("Mira:\n```py\nx = 1\n``") == ["Mira:."]
    # Lo de detrás sí espera, porque la raya que cierra el bloque abriría otro en la
    # ventana si llegaran más comillas.
    corte = SpeechCutter()

    assert corte.feed("Mira:\n```py\nx = ```y\n") == ["Mira:."]
    assert corte.feed("```\nFin. Y") == []
    assert corte.finish() == ["Te dejo el código en pantalla.", "Fin.", "Y"]


def test_un_bloque_sangrado_no_se_dice_aunque_su_primera_linea_aun_llegue() -> None:
    corte = SpeechCutter()

    assert corte.feed("Hola.\n\n    secreto. Más ") == []
    assert corte.finish() == ["Hola.", "Te dejo el código en pantalla."]


def test_tres_comillas_a_media_linea_no_abren_un_bloque() -> None:
    # Ronda 4 de Codex sobre la PR #688: para Markdown solo es una raya la que empieza una
    # línea. A media línea son las de un código en línea, salvo que la ventana las cierre
    # como un bloque (``test_tres_comillas_a_media_linea_son_codigo_si_la_ventana_las_cierra``).
    assert final_speech_text("Usa ```x``` aquí y `a`.") == "Usa x aquí y a."
    # Ni dos comillas, ni una raya con cuatro blancos delante: lo de detrás se dice.
    assert final_speech_text("Mira:\n``\nY sigue.").endswith("Y sigue.")
    assert final_speech_text("Mira:\n    ```\nY sigue.").endswith("Y sigue.")
    assert _dicho(["Uno. ```", ": `. Y"]) == ["Uno.:.", "Y"]
    assert _dicho(["Usa `x y ```python\nprint(1). Dos.\n"]) == [
        "Usa x y python.",
        "print(1).",
        "Dos.",
    ]
    # Tampoco delante de un bloque: siguen siendo un código en línea.
    assert final_speech_text("Usa ```x``` y `z`.\n```py\nsecreto\n```") == (
        "Usa x y z. Te dejo el código en pantalla."
    )
    # Y con otra comilla detrás en su línea la ventana tampoco abre nada: no se espera.
    assert SpeechCutter().feed("Uno ```a`. Dos. ") == ["Uno a."]


@pytest.mark.parametrize(
    "respuesta",
    [
        # Las comillas de una línea de código no cierran el bloque.
        'Mira:\n```python\nprint("``` dentro")\npassword = "secreto"',
        'Mira:\n```python\nprint("``` dentro")\npassword = "secreto"\n```\nFin.',
        # Ni una raya más corta, ni otra con algo detrás, ni una de virgulillas.
        'Mira:\n````\n```\npassword = "secreto"\n````\nFin.',
        'Mira:\n```\n```python\npassword = "secreto"\n```\nFin.',
        'Mira:\n~~~\n```\npassword = "secreto"\n```\n~~~\nFin.',
        # Ni una comilla suelta de antes que se empareja con la raya.
        'Mira `a:\n```python\npassword = "secreto"\n```\nFin.',
        # Ronda 5: dentro de una cita, y lo que salió al buscar la raíz: dentro de una lista,
        # con la sangría que sea, en la línea del número, o sangrado sin rayas.
        '> ```python\n> password = "secreto"\n> ```',
        'Mira:\n> ```python\n> password = "secreto"\n> ```\nFin.',
        'Pasos:\n\n1. Instala:\n\n    ```bash\n    password = "secreto"\n    ```\n\n2. Fin.',
        '- Mira:\n    ```\n    password = "secreto"\n    ```\n- Fin.',
        '1. ```\n   password = "secreto"\n   ```\n2. Fin.',
        'Mira:\n\n    password = "secreto"\n\nFin.',
        # Ni con comillas en una línea de código dentro de una cita, ni tras una línea de
        # HTML, que la ventana enseña como texto.
        '> ```python\n> print("``` dentro")\n> password = "secreto"\n> ```',
        '<div>\n~~~\npassword = "secreto"\n~~~\n</div>',
        # Y lo que la ventana enseña como código con su propia regla.
        'Mira: ```python\npassword = "secreto"\n```\nFin.',
        'Mira:\n\t```\n\tpassword = "secreto"\n\t```\nFin.',
    ],
)
def test_lo_de_dentro_de_un_bloque_de_codigo_no_se_dice_nunca(respuesta: str) -> None:
    # Rondas 4 y 5 de Codex sobre la PR #688: es código lo que lo es para CommonMark, con
    # sus citas y sus listas, o para la ventana.
    entera = final_speech_text(respuesta)
    azar = random.Random(respuesta)
    maneras = [[respuesta], list(respuesta)] + [_trocea(respuesta, azar) for _ in range(50)]

    assert "secreto" not in entera
    assert "Te dejo el código en pantalla." in entera
    assert [trozos for trozos in maneras if "secreto" in " ".join(_dicho(trozos))] == []


def test_tres_comillas_tras_una_frase_no_son_un_bloque_aunque_lleguen_solas() -> None:
    # A media línea, tres comillas no son una raya para CommonMark, ni aunque la línea se
    # acabe con ellas, y si no hay otras detrás, la ventana tampoco abre un bloque.
    assert final_speech_text("Uno. ```\nDos.") == "Uno. . Dos."

    assert _dicho(["Uno. ```\n", "Dos."]) == ["Uno.", "Dos."]


def test_tres_comillas_tras_una_frase_no_dejan_cortar_por_si_abren_un_bloque() -> None:
    # A media línea no abren un bloque: si se cortara delante, lo que viniera después
    # podría emparejarlas con una comilla y dejar a la vista una coma.
    assert final_speech_text("Uno. ```\n, x`") == "Uno., x"

    assert _dicho(["Uno. ```\n", ", x`"]) == ["Uno., x"]


def test_unas_virgulillas_tras_una_frase_no_abren_un_bloque() -> None:
    # Tampoco si lo que sigue llega en otro trozo: lo que queda tras el corte sigue sin
    # empezar una línea, y la línea siguiente, sí.
    respuesta = "Uno. ~~~ y sigue\nnada secreto\n~~~\nFin. Y"
    assert final_speech_text(respuesta) == (
        "Uno. ~~~ y sigue. nada secreto. Te dejo el código en pantalla."
    )
    corte = SpeechCutter()

    assert corte.feed("Uno. ~~~ y sigue") == ["Uno."]
    assert corte.feed("\nnada secreto\n~~~\nFin. Y") == ["~~~ y sigue.", "nada secreto."]
    assert corte.finish() == ["Te dejo el código en pantalla."]


def test_tres_comillas_a_media_linea_son_codigo_si_la_ventana_las_cierra() -> None:
    # La ventana separa sus bloques con su propia regla: tres comillas en cualquier sitio y
    # hasta las tres siguientes. Lo que enseña como código no se dice, y mientras no se sabe
    # si se cierran, lo de detrás espera. «Dos.» va detrás de una raya que para CommonMark
    # abre un bloque que no se cierra: también es código.
    corte = SpeechCutter()

    assert corte.feed("Uno. Mira ```py\nsecreto\n") == ["Uno."]
    assert corte.feed("```\nDos.") == []
    assert corte.finish() == ["Mira Te dejo el código en pantalla."]
    # Aunque lo que sigue a las comillas en su línea parezca el final de una frase, y
    # aunque una comilla de antes se empareje con ellas y no deje ninguna suelta.
    for primero in (
        "Uno. Mira ```py. Hola ",
        "Uno. Usa `a y ```py\n",
        "Uno. Usa `a y ```py. Hola ",
    ):
        corte = SpeechCutter()

        assert corte.feed(primero) == ["Uno."]
        assert corte.feed("\nsecreto\n```\nDos.") == []
        assert "secreto" not in " ".join(corte.finish())


def test_la_voz_separa_los_bloques_de_la_ventana_con_su_misma_regla() -> None:
    # Si la ventana cambia cómo separa sus bloques, esto avisa: la voz tiene que seguirla, o
    # diría lo que la ventana enseña como código.
    regla = ventana._FENCED_CODE_BLOCK

    assert (cortador._WINDOW_CODE_BLOCK.pattern, cortador._WINDOW_CODE_BLOCK.flags) == (
        regla.pattern,
        regla.flags,
    )


@pytest.mark.parametrize("delante", ["1. ", "1. 2. ", "> 1. ", "- 1. "])
def test_un_numero_de_lista_espera_a_saber_si_su_linea_abre_un_bloque(delante: str) -> None:
    # «1. » parece el final de una frase, pero detrás puede empezar la raya de un bloque, o
    # otro número, y entonces la línea entera es código: lo cazaron los textos al azar al
    # buscar la raíz. Mientras no se sabe, la línea espera entera, y la frase de antes con
    # ella, porque la línea podría empezar por una puntuación que se le pega.
    sangria = "".join(marca if marca == ">" else " " for marca in delante)
    corte = SpeechCutter()

    assert corte.feed(f"Hola.\n{delante}~") == []
    assert corte.feed(f"~~\n{sangria}secreto\n{sangria}~~~\nFin. Y") == [
        "Hola.",
        "Te dejo el código en pantalla.",
        "Fin.",
    ]
    # Y si no la abre, se dice como siempre.
    corte = SpeechCutter()

    assert corte.feed(f"Hola.\n{delante}") == []
    assert corte.feed("Uno. Y") == ["Hola.", *_dicho([f"{delante}Uno."])]
    # Y llegando letra a letra, que es cuando unas cifras aún pueden ser otro número.
    for respuesta in (
        f"Hola.\n{delante}~~~\n{sangria}secreto\n{sangria}~~~\nFin. Y",
        f"Hola.\n{delante}Uno. Y",
    ):
        assert _dicho(list(respuesta)) == _dicho([respuesta])


def test_lo_sangrado_dentro_de_una_lista_se_dice_y_fuera_es_codigo() -> None:
    # Para CommonMark, cuatro blancos dentro de una lista son la sangría de su párrafo, y
    # fuera, tras una línea en blanco, un bloque de código.
    assert final_speech_text("1. Paso:\n\n    Explicación del paso.") == (
        "1. Paso:. Explicación del paso."
    )
    assert final_speech_text("Paso:\n\n    secreto\n\nFin.") == (
        "Paso:. Te dejo el código en pantalla. Fin."
    )


@pytest.mark.parametrize(
    "respuesta",
    [
        # Unas comillas que aún pueden abrir un bloque en la ventana, y detrás un bloque
        # sangrado ya entero: ese bloque no hace seguro lo de delante, que aún puede ser
        # texto, y la frase de antes espera con ello.
        "¿Seguro? ```\n\n    x\n`",
        # Un bloque de la ventana que se abre con las tres últimas de cinco comillas y se
        # cierra con las tres primeras de cuatro: las que sobran no se emparejan con la
        # marca del bloque.
        ")`````\n````x`\nx\n```",
        # Una comilla suelta delante de dos bloques seguidos: no se corta entre las dos
        # rayas de la marca de uno, que se emparejarían con ella.
        "``a`\n\n    x\n~~~\n",
        "`b\n>~~~\n~~~```\n",
        # Un bloque entero por detrás de unas comillas que aún pueden abrir uno en la
        # ventana: lo que hay entre ellos no se dice mientras no se sepa qué es.
        "` ```a\n\n    x\n```",
    ],
)
def test_lo_que_cazaron_los_textos_al_azar_dice_lo_mismo_trozo_a_trozo(respuesta: str) -> None:
    esperado = _lo_que_se_dice(final_speech_text(respuesta))

    assert _lo_que_se_dice(" ".join(_dicho([respuesta]))) == esperado
    assert _lo_que_se_dice(" ".join(_dicho(list(respuesta)))) == esperado


def _respuesta_con_codigo(azar: random.Random) -> str:
    """Una respuesta al azar con bloques de código: con rayas de comillas o virgulillas, que
    cierran o no, sangrados o con comillas a media línea, dentro de citas, de viñetas, de
    números o con un tabulador delante. Lo de dentro lleva secretos numerados."""
    numeros = iter(range(10_000))

    def secreto() -> str:
        return f"secreto{next(numeros)}"

    def cercado() -> list[str]:
        raya = azar.choice(["```", "````", "~~~"])
        dentro = [
            azar.choice([secreto(), f'print("``` {secreto()}")', f"{raya[:3]}x {secreto()}"])
            for _ in range(azar.randint(1, 3))
        ]
        cierre = azar.choice([[raya], [raya + raya[0]], [" " + raya], []])
        return [raya + azar.choice(["", "py"]), *dentro, *cierre]

    def a_media_linea() -> list[str]:
        return ["Mira ```" + azar.choice(["", "py"]), secreto(), azar.choice(["```", "Nada."])]

    def sangrado() -> list[str]:
        return ["", f"    {secreto()}"]

    def parrafo() -> list[str]:
        return [azar.choice(["Hola.", "Vale, **sigue**.", "Usa `pip` aquí.", "¿Seguro?", "Fin"])]

    lineas: list[str] = []
    for _ in range(azar.randint(1, 4)):
        bloque = azar.choice([parrafo, cercado, cercado, sangrado, a_media_linea])()
        delante = azar.choice(["", "", "> ", "- ", "1. ", "\t"])
        sangria = {"- ": "    ", "1. ": "   "}.get(delante, delante)
        lineas += [delante + bloque[0], *(sangria + linea for linea in bloque[1:])]
        lineas += [""] * azar.randint(0, 1)
    return azar.choice(["\n", "\r\n"]).join(lineas)


def _secretos_en_codigo(respuesta: str) -> set[str]:
    """Los secretos que son código para CommonMark o que la ventana enseña como código."""
    bloques = [
        token.content
        for token in MarkdownIt("commonmark", {"html": False}).parse(respuesta)
        if token.type in {"fence", "code_block"}
    ]
    bloques += [tramo.text for tramo in ventana._segment_message(respuesta) if tramo.is_code]
    return set(re.findall(r"secreto\d+", "\n".join(bloques)))


def test_lo_que_es_codigo_para_commonmark_o_para_la_ventana_no_se_dice_nunca() -> None:
    # Ronda 5 de Codex sobre la PR #688, y la raíz de las rondas 2 a 5: qué es código ya no
    # lo deciden reglas propias. Aquí lo dicen un analizador de CommonMark y la ventana, con
    # respuestas al azar, enteras o a medias, y cada una cortada de cinco maneras.
    azar = random.Random(2435)
    dichos, distintos = [], []
    for _ in range(150):
        respuesta = _respuesta_con_codigo(azar)
        for texto in (respuesta, respuesta[: azar.randint(0, len(respuesta))]):
            esperado = final_speech_text(texto)
            secretos = _secretos_en_codigo(texto)
            for trozos in [[texto], list(texto)] + [_trocea(texto, azar) for _ in range(3)]:
                dicho = " ".join(_dicho(trozos))
                if secretos & set(re.findall(r"secreto\d+", f"{dicho} {esperado}")):
                    dichos.append(texto)
                if _lo_que_se_dice(dicho) != _lo_que_se_dice(esperado):
                    distintos.append(texto)

    assert dichos == []
    assert distintos == []


def test_dos_guiones_bajos_entre_letras_no_se_dicen() -> None:
    # Ronda 4 de Codex sobre la PR #688: al acabar se quitan, y mientras tanto no se corta.
    assert final_speech_text("Hola__mundo. Y") == "Holamundo. Y"

    assert _dicho(["Hola__mundo. Y"]) == ["Holamundo.", "Y"]


def test_la_raya_de_un_bloque_se_reconoce_con_su_linea_entera() -> None:
    # Con tres comillas aún sin el resto de su línea no se sabe si abren un bloque: aquí
    # son un código en línea, y la coma que dejan se pega a la frase de antes.
    assert final_speech_text("Mira:\n```,```. Y") == "Mira:.,. Y"

    assert _dicho(["Mira:\n```", ",```. Y"]) == ["Mira:.,.", "Y"]


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


@pytest.mark.parametrize("marca", ["-", "+"])
def test_un_guion_o_un_mas_tras_una_frase_esperan_a_ver_que_sigue(marca: str) -> None:
    # Solos, lo de detrás preparado por separado los tomaría por una viñeta y los quitaría.
    assert _dicho([f"Uno. {marca}", " , dos. Y"]) == ["Uno.", f"{marca}, dos.", "Y"]


def test_al_acabar_se_dice_la_ultima_linea_aunque_pudiera_ser_una_raya() -> None:
    # Mientras la charla sigue, una última línea que empieza por comillas o cifras espera por
    # si es la raya de un bloque; al acabar ya no lo será, y se dice.
    assert _dicho(["Hola.\n`pip` lo instala."]) == ["Hola.", "pip lo instala."]
    assert _dicho(["Hola.\n2 manzanas."]) == ["Hola.", "2 manzanas."]


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
    # Y lo siguiente vuelve a empezar una línea: ahí tres comillas abren un bloque.
    dichas = corte.feed("```\nsecreto\n```\nFin. Y") + corte.finish()
    assert dichas == ["Te dejo el código en pantalla.", "Fin.", "Y"]


@pytest.mark.parametrize(
    ("respuesta", "dichas"),
    [
        ("Mira:\n```python\nprint('secreto')", ["Mira:.", "Te dejo el código en pantalla."]),
        ("Esto es **muy importante", ["Esto es muy importante"]),
        ("Y esto es _también", ["Y esto es también"]),
        ("Muy importante**", ["Muy importante"]),
        ("**5 puntos", ["5 puntos"]),
        # Ronda 4: dos o más seguidas son siempre lo que sobra de un énfasis.
        ("Mira a**muy", ["Mira amuy"]),
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
