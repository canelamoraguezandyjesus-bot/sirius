"""Pruebas de aceptación de la versión 0.3 del robot: la voz.

Salen de la sección 0.3 de ``docs/evolution/PLAN_DEL_ROBOT.md`` (§5) y llevan
su ``PA-R03-NN`` de ``docs/evolution/PRUEBAS_0.3_DEL_ROBOT.md``. Hablan como el
plan: el propietario dice algo por el micro, Sirius le oye y le contesta
hablando. Lo que hace falta saber del código está en ``conductor_robot_0_3``.

Los dobles del conductor llevan escrito lo que suena, en vez de ondas: estas
pruebas demuestran que lo oído llega donde debe, que lo que dice es lo que
escribió y que nada sale ni se guarda, no que el oído o la voz de verdad
acierten. Eso lo miden las evaluaciones del propietario en su ordenador.

Cada prueba mira el camino, no solo el final: que el sonido pasó por el micro,
el texto por el transcriptor, la petición por el modelo y la frase por el
altavoz. Y lo mira en lo que apuntan los dobles en el acto de leer, transcribir,
decir y sonar, nunca en una cifra o un recuento que dé el conductor: una pieza
que atajara, metiendo el texto en la charla sin oírlo o contestando sin hablar,
no las pasa (rondas 1 a 3 de Codex y revisión propia de la PR #686).
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest
from conductor_robot_0_3 import ConductorDeVoz, percentil, pieza

from sirius.application.prepare_speech_text import prepare_speech_text

pytestmark = pytest.mark.acceptance

_HERRAMIENTAS_DEL_PLAN = {
    "voz": "silero",
    "fin de turno": "smart-turn",
    "texto": "faster-whisper",
    "habla": "piper",
}


def _sin_blancos(texto: str) -> str:
    """El texto con los blancos y saltos de línea reducidos a un espacio."""
    return " ".join(texto.split())


def _momentos_de_su_voz(conductor: ConductorDeVoz, desde: int) -> list[float]:
    """Cuándo leyó el micro cada sonido con voz del propietario, desde el índice ``desde``.

    Son los relojes de los dobles, no cifras del conductor: una pieza que tardara
    de más no podría devolver un cero (ronda 3 de Codex sobre la PR #686).
    """
    leidos = conductor.micro.leidos[desde:]
    momentos = conductor.micro.leido_en[desde:]
    return [
        momento
        for sonido, momento in zip(leidos, momentos, strict=True)
        if not sonido.es_silencio and sonido.de("propietario")
    ]


# --- PA-R03-01 · Lo que dice por voz entra en la charla -----------------------


@pieza("B", "lo que dice por voz entra en la charla como un mensaje más")
def test_lo_que_dice_por_voz_llega_a_la_charla_como_un_mensaje_mas(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)

    turno = conductor.oye("Buenos días, Sirius.")

    # El camino entero: micro, transcriptor, modelo y base.
    assert [(s.texto, s.de_quien) for s in conductor.micro.leidos if not s.es_silencio] == [
        ("Buenos días, Sirius.", "propietario")
    ]
    assert conductor.transcriptor.transcritos == ("Buenos días, Sirius.",)
    assert conductor.peticiones[-1].texto == "Buenos días, Sirius."
    assert turno.oido == "Buenos días, Sirius."
    assert turno.para_el
    assert turno.contestado == "Respuesta 1 de Sirius."
    assert conductor.charla_guardada()[-2:] == (
        ("propietario", "Buenos días, Sirius."),
        ("Sirius", "Respuesta 1 de Sirius."),
    )


@pieza("B", "la respuesta a lo dicho por voz pasa por la misma charla que lo escrito")
def test_la_respuesta_a_lo_dicho_por_voz_pasa_por_la_misma_charla_que_lo_escrito(
    tmp_path: Path,
) -> None:
    conductor = ConductorDeVoz(tmp_path)
    semilla = conductor.semilla_del_robot()
    recordatorio = conductor.recordatorio_de_la_semilla()

    conductor.oye("Buenos días, Sirius.")
    conductor.di("Buenos días, Sirius.")

    por_voz, escrita = conductor.peticiones[-2:]
    assert por_voz.texto == escrita.texto
    for peticion in (por_voz, escrita):
        assert semilla.instrucciones in peticion.instrucciones
        assert peticion.instrucciones.rstrip().endswith(recordatorio.strip())
        assert len(conductor.ejemplos_en(peticion)) == 3
    # Los mismos tres ejemplos, que salen del mensaje; solo cambia el orden (ADR-240).
    assert set(conductor.ejemplos_en(por_voz)) == set(conductor.ejemplos_en(escrita))


@pieza("B", "el turno acaba cuando el detector dice que ha terminado, no en el primer silencio")
def test_el_turno_acaba_cuando_el_detector_dice_que_ha_terminado_y_no_en_el_primer_silencio(
    tmp_path: Path,
) -> None:
    conductor = ConductorDeVoz(tmp_path)
    conductor.oido.pide_silencios(3)

    a_medias = conductor.oye("Sirius, estaba pensando que", y_calla=1)

    assert a_medias.oido is None
    assert conductor.oido.fines == ()
    assert conductor.peticiones == []

    todavia = conductor.calla(1)

    assert todavia.oido is None
    assert conductor.oido.fines == ()
    assert conductor.peticiones == []

    turno = conductor.calla(1)

    # El detector dio el fin en el tercer silencio, y Sirius cerró el turno ahí.
    assert len(conductor.oido.fines) == 1
    assert conductor.oido.vistos[conductor.oido.fines[0]].es_silencio
    assert sum(1 for audio in conductor.oido.vistos if audio.es_silencio) == 3
    assert conductor.transcriptor.transcritos == ("Sirius, estaba pensando que",)
    assert turno.oido == "Sirius, estaba pensando que"
    assert turno.contestado == "Respuesta 1 de Sirius."
    assert [p.texto for p in conductor.peticiones] == ["Sirius, estaba pensando que"]


@pieza("B", "«olvida eso» dicho por voz olvida")
def test_olvida_eso_dicho_por_voz_olvida(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)
    conductor.oye("Sirius, la clave de la alarma es Zarzamora.")
    assert conductor.busca_en_toda_la_base("Zarzamora") != [], (
        "lo dicho por voz tiene que guardarse"
    )

    peticiones_antes = len(conductor.peticiones)
    turno = conductor.oye("Olvida eso.")
    conductor.cierra()

    assert turno.para_el
    assert conductor.transcriptor.transcritos[-1] == "Olvida eso."
    assert conductor.busca_en_toda_la_base("Zarzamora") == []
    # Y el modelo no lo vio en este turno: ni en lo que se le dijo ni en sus instrucciones.
    for peticion in conductor.peticiones[peticiones_antes:]:
        assert "zarzamora" not in peticion.texto.casefold()
        assert "zarzamora" not in peticion.instrucciones.casefold()
    # Olvidado de verdad: tampoco queda en el diario, que sí puede escribir.
    assert not conductor.el_diario_contiene("Zarzamora")


# --- PA-R03-02 · Habla con Piper, frase a frase desde la primera --------------


@pieza("C", "empieza a hablar con la primera frase, antes de que el modelo acabe")
def test_empieza_a_hablar_con_la_primera_frase_antes_de_que_el_modelo_acabe(
    tmp_path: Path,
) -> None:
    conductor = ConductorDeVoz(tmp_path)
    # Tres trozos: la primera frase queda confirmada con el segundo, y el modelo
    # sigue escribiendo el tercero.
    conductor.el_modelo_contesta_despacio(
        ["Primera frase, jefe.", " Y la segunda, más larga.", " Y la tercera, que tarda más."],
        pausa=0.5,
    )

    turno = conductor.oye("Sirius, cuéntame algo.")

    assert turno.hablado == (
        "Primera frase, jefe.",
        "Y la segunda, más larga.",
        "Y la tercera, que tarda más.",
    )
    assert [frase.texto for frase in conductor.voz.frases] == list(turno.hablado)
    assert [sonido.texto for sonido, _ in conductor.altavoz.sonados] == list(turno.hablado)
    # La primera frase se pidió a la voz y sonó antes de que el modelo acabara,
    # con el reloj del modelo de mentira, que apunta cuándo terminó.
    acabo = conductor.modelo.acabo_en
    assert acabo is not None
    assert conductor.voz.frases[0].momento < acabo
    assert conductor.altavoz.sonados[0][1] < acabo


@pieza("C", "dice todo lo que escribió y nada más, sin marcas ni código")
def test_lo_que_dice_es_lo_que_escribio_sin_marcas_ni_codigo(tmp_path: Path) -> None:
    escrito = "Mira **esto**:\n\n```python\nprint(1)\n```\n\nY ya está, listo."
    conductor = ConductorDeVoz(tmp_path, respuestas=[escrito])

    turno = conductor.oye("Sirius, enséñame el código.")

    assert turno.contestado == escrito
    # La locución entera es lo escrito preparado para leerse, sin quitar ni añadir
    # nada; solo cambia el corte en frases. Y es la misma en lo que se le pidió a
    # la voz y en lo que sonó por el altavoz, no solo en el resumen del turno.
    assert _sin_blancos(" ".join(turno.hablado)) == _sin_blancos(prepare_speech_text(escrito))
    assert [frase.texto for frase in conductor.voz.frases] == list(turno.hablado)
    assert [sonido.texto for sonido, _ in conductor.altavoz.sonados] == list(turno.hablado)
    assert "print(1)" not in " ".join(turno.hablado)


@pieza("C", "habla con una voz de Piper en español de España")
def test_habla_con_una_voz_de_piper_en_espanol_de_espana(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)

    conductor.oye("Buenos días, Sirius.")

    assert conductor.herramientas()["habla"] == "piper"
    # La voz con la que se pidió la frase, y con la que sonó, la apuntan los dobles.
    frases = conductor.voz.frases
    assert [frase.texto for frase in frases] == ["Respuesta 1 de Sirius."]
    assert frases[0].voz.startswith("es_ES-")
    assert [(s.texto, s.de_quien, s.voz) for s, _ in conductor.altavoz.sonados] == [
        ("Respuesta 1 de Sirius.", "sirius", frases[0].voz)
    ]


# --- PA-R03-03 · Su propia voz no se toma por la del propietario --------------


@pieza("C", "su propia voz, de vuelta por el micro, no empieza un turno")
def test_su_propia_voz_no_empieza_un_turno(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)
    conductor.altavoz.con_eco = True

    turno = conductor.oye("Buenos días, Sirius.")

    assert turno.hablado == ("Respuesta 1 de Sirius.",)
    # El eco existió: el altavoz lo devolvió al micro. Antes de la cancelación de
    # eco, mientras habla no escucha y el eco se pierde con el micro cerrado; con
    # ella (pieza E), se lee y se cancela. En los dos casos: ni se transcribe, ni
    # hay petición, ni turno.
    eco = (*conductor.micro.perdidos, *conductor.micro.leidos)
    assert [s.texto for s in eco if s.de("sirius")] == ["Respuesta 1 de Sirius."]
    assert conductor.transcriptor.transcritos == ("Buenos días, Sirius.",)
    assert len(conductor.peticiones) == 1
    assert conductor.charla_guardada()[-2:] == (
        ("propietario", "Buenos días, Sirius."),
        ("Sirius", "Respuesta 1 de Sirius."),
    )

    conductor.calla(2)

    # Tampoco después: dos silencios más no sacan ningún turno del eco.
    assert conductor.transcriptor.transcritos == ("Buenos días, Sirius.",)
    assert len(conductor.peticiones) == 1


@pieza("E", "con la cancelación de eco, su propia voz sigue sin empezar un turno ni le corta")
def test_con_la_cancelacion_de_eco_su_propia_voz_sigue_sin_empezar_un_turno(
    tmp_path: Path,
) -> None:
    conductor = ConductorDeVoz(
        tmp_path, respuestas=["Una respuesta larguísima que no acaba nunca.", "Vale, vale."]
    )
    conductor.altavoz.con_eco = True
    conductor.altavoz.sigue_sonando = True

    turno = conductor.oye("Sirius, cuéntame tu vida.")

    assert turno.hablado == ("Una respuesta larguísima que no acaba nunca.",)
    # Con cancelación de eco el micro sigue abierto mientras habla, el eco entra
    # por él y no sale del cancelador: ni transcripción, ni turno, ni corte.
    assert conductor.micro.abierto
    assert any(s.de("sirius") for s in conductor.micro.leidos)
    assert conductor.altavoz.parado_en is None
    assert list(conductor.transcriptor.transcritos) == ["Sirius, cuéntame tu vida."]
    assert len(conductor.peticiones) == 1

    # El detector tarda en dar el turno por acabado: callarse no puede esperarle.
    conductor.oido.pide_silencios(3)
    leidos_antes = len(conductor.micro.leidos)
    a_medias = conductor.oye_mientras_habla("Espera, espera, que tengo prisa.")

    # La voz del propietario llega en un mismo audio con el eco encima, y aun así
    # atraviesa: Sirius se calla al oírla, con el turno aún abierto.
    assert any(s.de("propietario") and s.de("sirius") for s in conductor.micro.leidos)
    assert a_medias.oido is None
    assert conductor.altavoz.parado_en is not None
    assert conductor.altavoz.parado_en > min(_momentos_de_su_voz(conductor, leidos_antes))

    corte = conductor.calla(2)

    assert list(conductor.transcriptor.transcritos) == [
        "Sirius, cuéntame tu vida.",
        "Espera, espera, que tengo prisa.",
    ]
    assert corte.oido == "Espera, espera, que tengo prisa."
    assert corte.contestado == "Vale, vale."

    conductor.calla(2)

    # Y el eco de «Vale, vale.», que también volvió por el micro, tampoco empieza nada.
    assert len(conductor.transcriptor.transcritos) == 2
    assert len(conductor.peticiones) == 2

    conductor.altavoz.acaba()
    # El detector sigue pidiendo tres silencios (ADR-245: con uno solo, el turno se quedaba
    # abierto y esta parte no podía pasar).
    repetida = conductor.oye("Vale, vale.", y_calla=3)

    # Lo que Sirius dijo alguna vez no es eco para siempre: dicho por el propietario
    # con el altavoz callado, se oye y se contesta.
    assert repetida.oido == "Vale, vale."
    assert repetida.contestado == "Respuesta 3 de Sirius."
    assert len(conductor.peticiones) == 3


# --- PA-R03-05 · No guarda audio ----------------------------------------------


@pieza("D", "tras varios turnos de voz no queda ningún audio guardado")
def test_tras_varios_turnos_de_voz_no_queda_ningun_audio_guardado(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)

    for frase in ("Buenos días, Sirius.", "¿Qué tal has dormido?", "Pues yo fatal."):
        conductor.oye(frase)
    conductor.cierra()

    assert conductor.escrituras_en_disco() == []
    assert conductor.ficheros_nuevos() == []
    assert conductor.audio_en_la_base() == []
    assert conductor.audio_en_el_diario() == []
    assert conductor.busca_en_toda_la_base("Pues yo fatal.") != []


@pieza("D", "lo que no era para él no se guarda ni como texto")
def test_lo_que_no_era_para_el_no_se_guarda_ni_como_texto(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)

    turno = conductor.oye("Y mañana, cielos despejados en toda la península.")
    conductor.cierra()

    assert conductor.transcriptor.transcritos == (
        "Y mañana, cielos despejados en toda la península.",
    )
    assert not turno.para_el
    assert conductor.busca_en_toda_la_base("cielos despejados") == []
    assert not conductor.el_diario_contiene("cielos despejados")
    assert conductor.escrituras_en_disco() == []
    assert conductor.ficheros_nuevos() == []


# --- PA-R03-06 · Sabe cuándo le hablan a él -----------------------------------


@pieza("D", "con su nombre, siempre es para él")
def test_con_su_nombre_siempre_es_para_el(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)
    conductor.reloj.avanza(3600)

    turno = conductor.oye("Oye, Sirius, ¿qué hora es?")

    assert turno.para_el
    assert turno.contestado == "Respuesta 1 de Sirius."

    conductor.reloj.avanza(3600)
    turno = conductor.oye("¿Y tú qué opinas, sirius?")

    assert turno.para_el
    assert turno.contestado == "Respuesta 2 de Sirius."
    assert [p.texto for p in conductor.peticiones] == [
        "Oye, Sirius, ¿qué hora es?",
        "¿Y tú qué opinas, sirius?",
    ]


@pieza("D", "sin su nombre, es para él solo mientras dura la charla")
def test_sin_su_nombre_es_para_el_solo_mientras_dura_la_charla(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)
    conductor.oye("Buenos días, Sirius.")
    # La charla dura algo: ni cero, que obligaría a decir su nombre siempre, ni
    # tanto que al rato conteste a la tele.
    charla = conductor.segundos_de_charla()
    assert 5 <= charla <= 120

    conductor.reloj.avanza(charla - 1)
    seguida = conductor.oye("¿Has dormido bien?")

    assert seguida.para_el
    assert seguida.contestado == "Respuesta 2 de Sirius."

    conductor.reloj.avanza(charla + 1)
    tarde = conductor.oye("¿Has dormido bien?")

    assert conductor.transcriptor.transcritos[-1] == "¿Has dormido bien?"
    assert not tarde.para_el
    assert tarde.contestado is None
    assert len(conductor.peticiones) == 2


@pieza("D", "lo que no es para él no llega al modelo")
def test_lo_que_no_es_para_el_no_llega_al_modelo(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)

    turno = conductor.oye("Vamos con el tiempo: mañana lloverá en el norte.")

    assert conductor.transcriptor.transcritos == (
        "Vamos con el tiempo: mañana lloverá en el norte.",
    )
    assert not turno.para_el
    assert turno.hablado == ()
    assert conductor.voz.frases == ()
    assert conductor.altavoz.sonados == ()
    assert conductor.peticiones == []


# --- PA-R03-07 · Se le puede cortar -------------------------------------------


@pieza("E", "si el propietario habla mientras Sirius habla, Sirius se calla y atiende lo nuevo")
def test_si_el_propietario_habla_sirius_se_calla_y_atiende_lo_nuevo(tmp_path: Path) -> None:
    larga = "Una respuesta larguísima que no acaba nunca."
    conductor = ConductorDeVoz(tmp_path, respuestas=[larga])
    conductor.altavoz.sigue_sonando = True
    conductor.oye("Sirius, cuéntame tu vida.")
    assert conductor.altavoz.parado_en is None
    # Ni la respuesta nueva ni el detector pueden hacerle esperar: la respuesta
    # tarda, y el detector no da el turno por acabado hasta el tercer silencio.
    conductor.el_modelo_contesta_despacio(["Vale, vale."], pausa=0.6)
    conductor.oido.pide_silencios(3)

    leidos_antes = len(conductor.micro.leidos)
    a_medias = conductor.oye_mientras_habla("Espera, espera, que tengo prisa.")

    # Se calló al oír su voz, con el turno aún abierto: medio segundo desde que el
    # micro leyó su voz hasta que el altavoz paró, con los relojes de los dobles.
    assert a_medias.oido is None
    parado_en = conductor.altavoz.parado_en
    assert parado_en is not None
    empezo_a_hablar = min(_momentos_de_su_voz(conductor, leidos_antes))
    assert 0 <= (parado_en - empezo_a_hablar) * 1000 < 500

    corte = conductor.calla(2)

    # Y paró antes de que sonara la respuesta nueva, que atiende después.
    assert parado_en < conductor.altavoz.sonados[-1][1]
    assert [s.texto for s, _ in conductor.altavoz.sonados] == [larga, "Vale, vale."]
    assert corte.oido == "Espera, espera, que tengo prisa."
    assert corte.contestado == "Vale, vale."
    assert corte.hablado == ("Vale, vale.",)


@pieza("E", "al cortarle deja de escribir, y lo nuevo llega al modelo enseguida")
def test_al_cortarle_deja_de_escribir_y_lo_nuevo_llega_al_modelo_enseguida(
    tmp_path: Path,
) -> None:
    # Lo decidió el propietario el 17-10-2026 (ADR-254): al cortarle, Sirius deja de
    # escribir la respuesta, aunque quede a medias en la charla, y lo nuevo no espera a que
    # el modelo acabe. Desde el 15-10-2026 la escribía entera (ADR-245): con una respuesta
    # larga, lo nuevo esperaba decenas de segundos.
    trozos = (
        "Una respuesta larguísima.",
        " Que sigue y sigue.",
        " Y que no acaba nunca.",
        " Ni a la de tres.",
        " Ni a la de cuatro.",
    )
    conductor = ConductorDeVoz(tmp_path, respuestas=["Vale, vale."])
    conductor.altavoz.sigue_sonando = True
    sono_antes_de_hablar: list[bool] = []

    def le_corta_cuando_suene_la_primera_frase() -> None:
        # En un hilo aparte, para no retener al modelo: se espera a que la primera frase
        # suene de verdad, y entonces el propietario habla encima, con el modelo aún
        # escribiendo los trozos que faltan.
        limite = time.perf_counter() + 5
        while not conductor.altavoz.sonados and time.perf_counter() < limite:
            time.sleep(0.01)
        sono_antes_de_hablar.append(bool(conductor.altavoz.sonados))
        conductor.habla_encima("Espera, espera, que tengo prisa.")

    hilo = threading.Thread(target=le_corta_cuando_suene_la_primera_frase, daemon=True)
    # Sin cortarle, el modelo tardaría 5 s en escribirla entera.
    conductor.el_modelo_contesta_despacio(trozos, pausa=1.0, tras_el_primer_trozo=hilo.start)
    # El detector pide dos silencios: lo que dice encima se cierra con el que suena aquí
    # abajo, en cuanto Sirius acaba con lo de antes, que es cuando lo atendería (ADR-245).
    conductor.oido.pide_silencios(2)

    conductor.oye("Sirius, cuéntame tu vida.", y_calla=2)
    hilo.join(timeout=5)
    conductor.calla(1)

    assert sono_antes_de_hablar == [True], "la primera frase tenía que sonar antes del corte"
    parado_en = conductor.altavoz.parado_en
    assert parado_en is not None
    # Lo nuevo llegó al modelo en menos de 1 s desde que calló, con los relojes de los
    # dobles: no esperó a que el modelo acabara de escribir lo de antes.
    assert len(conductor.modelo.pedidas_en) == 2
    assert 0 <= conductor.modelo.pedidas_en[1] - parado_en < 1
    assert conductor.peticiones[-1].texto == "Espera, espera, que tengo prisa."
    # Y dejó de escribir: queda lo que llevaba escrito, a medias, y no la respuesta entera.
    escrito = conductor.modelo.escrito_al_cortar
    entera = "".join(trozos)
    assert escrito is not None
    assert escrito != entera
    assert entera.startswith(escrito)
    assert ("Sirius", escrito) in conductor.charla_guardada()
    assert ("Sirius", entera) not in conductor.charla_guardada()


@pieza("E", "la charla apunta hasta dónde oyó lo que le cortaron")
def test_la_charla_apunta_hasta_donde_oyo_lo_que_le_cortaron(tmp_path: Path) -> None:
    # Lo decidió el propietario el 15-10-2026 (ADR-245): la charla apunta hasta dónde la
    # oyó, para que el modelo no dé por dicho lo que no sonó. Desde el 17-10-2026 queda lo
    # que llevaba escrito cuando le cortaron, no la respuesta entera (ADR-254).
    trozos = ("Una respuesta larguísima.", " Que sigue y sigue.", " Y que no acaba nunca.")
    entera = "".join(trozos)
    conductor = ConductorDeVoz(tmp_path)
    conductor.altavoz.sigue_sonando = True

    def le_corta_cuando_suene_la_primera_frase() -> None:
        limite = time.perf_counter() + 2
        while not conductor.altavoz.sonados and time.perf_counter() < limite:
            time.sleep(0.01)
        conductor.habla_encima("Espera, espera, que tengo prisa.")

    hilo = threading.Thread(target=le_corta_cuando_suene_la_primera_frase, daemon=True)
    conductor.el_modelo_contesta_despacio(trozos, pausa=0.6, tras_el_primer_trozo=hilo.start)
    conductor.oido.pide_silencios(2)
    conductor.oye("Sirius, cuéntame tu vida.", y_calla=2)
    hilo.join(timeout=5)

    corte = conductor.calla(1)

    # Lo que dijo encima va a la charla, y el modelo lee con ello lo que llevaba escrito
    # cuando le cortaron y que de ello solo sonó la primera frase.
    assert corte.oido == "Espera, espera, que tengo prisa."
    sonado = [s.texto for s, _ in conductor.altavoz.sonados]
    assert sonado[:1] == ["Una respuesta larguísima."]
    assert "Que sigue y sigue." not in sonado
    escrito = conductor.modelo.escrito_al_cortar
    assert escrito is not None
    assert escrito != entera
    assert ("Sirius", escrito) in conductor.charla_guardada()
    assert conductor.lo_que_oyo_de(escrito, conductor.peticiones[-1]) == (
        "Una respuesta larguísima."
    )


# --- PA-R03-08 · Nada sale del ordenador --------------------------------------


@pieza("B", "ninguna petición sale del ordenador durante un turno de voz")
def test_ninguna_peticion_sale_durante_un_turno_de_voz(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)

    for frase in ("Buenos días, Sirius.", "¿Qué tal has dormido?"):
        turno = conductor.oye(frase)
        assert turno.contestado is not None

    assert conductor.conexiones_de_red() == []


@pieza("B", "el oído y la voz del robot solo pueden ir a este ordenador")
def test_el_oido_y_la_voz_del_robot_solo_pueden_ir_a_este_ordenador(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)

    assert conductor.destinos_posibles_de_la_voz() == frozenset({"este ordenador"})


@pieza("B", "si falta un modelo, dice qué orden ejecutar y no lo baja él")
def test_si_falta_un_modelo_dice_que_orden_ejecutar_y_no_lo_baja_el(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)
    conductor.quita_los_modelos_de_voz()

    turno = conductor.oye("Buenos días, Sirius.")

    orden = conductor.orden_para_instalar_la_voz()
    assert orden.strip(), "sin orden no hay nada que decirle"
    assert turno.aviso.strip()
    assert orden in turno.aviso
    # Ni oye, ni contesta, ni baja nada: ninguna conexión y ningún proceso.
    assert turno.oido is None
    assert turno.hablado == ()
    assert conductor.peticiones == []
    assert conductor.conexiones_de_red() == []
    assert conductor.procesos_lanzados() == []


@pieza("C", "oye y habla con las herramientas locales del plan")
def test_oye_y_habla_con_las_herramientas_locales_del_plan(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)

    assert dict(conductor.herramientas()) == _HERRAMIENTAS_DEL_PLAN


# --- PA-R03-09 · La tubería de Sirius añade poco ------------------------------


@pieza("C", "con micro, oído, modelo y voz instantáneos, la tubería añade menos de 200 ms")
def test_del_final_de_su_voz_al_primer_sonido_la_tuberia_anade_menos_de_200_ms(
    tmp_path: Path,
) -> None:
    # Los dobles no tardan nada, el micro tampoco: no se le da ritmo al audio. Los
    # 200 ms incluyen la charla escrita de la 0.2 entera, que no es doble: su línea
    # base, `di()` solo, fue 34 ms en el P95 de 20 turnos en la nube el 13-10-2026
    # (ADR-241).
    conductor = ConductorDeVoz(tmp_path)
    tiempos: list[float] = []

    for n in range(1, 21):
        leidos_antes = len(conductor.micro.leidos)
        sonados_antes = len(conductor.altavoz.sonados)
        turno = conductor.oye(f"Sirius, pregunta número {n}.")
        # Dijo lo que escribió, una frase. No es la respuesta n del modelo grabador: la
        # charla de la 0.2 le pide un resumen en el turno 18, y el resumen se lleva una
        # (ADR-243, al pasar por primera vez esta prueba).
        assert turno.contestado is not None
        assert turno.hablado == (turno.contestado,)
        # Del último sonido con su voz que leyó el micro al primero que sonó por el
        # altavoz, con los relojes de los dobles.
        fin_de_su_voz = max(_momentos_de_su_voz(conductor, leidos_antes))
        _sonido, primer_sonido = conductor.altavoz.sonados[sonados_antes]
        tiempos.append((primer_sonido - fin_de_su_voz) * 1000)

    assert all(tiempo >= 0 for tiempo in tiempos), "el altavoz no puede sonar antes del micro"
    assert percentil(tiempos, 95) < 200


# --- PA-R03-10 · Elegir su voz a ciegas ---------------------------------------


@pieza("F", "la prueba de voces da cinco frases con cuatro a seis voces barajadas y sin nombre")
def test_la_prueba_de_voces_da_cinco_frases_con_cuatro_a_seis_voces_barajadas_y_sin_nombre(
    tmp_path: Path,
) -> None:
    conductor = ConductorDeVoz(tmp_path)

    hoja = conductor.hoja_de_voces()

    assert len(hoja.frases) == 5
    assert len(set(hoja.frases)) == 5
    assert all(frase.strip() for frase in hoja.frases)
    assert 4 <= len(hoja.candidatas) <= 6
    nombres = {conductor.voz_tras(candidata.etiqueta) for candidata in hoja.candidatas}
    assert len(nombres) == len(hoja.candidatas)
    de_piper = [n for n in nombres if n.startswith("es_ES-") and "chatterbox" not in n.casefold()]
    assert len(de_piper) >= 2
    assert any("chatterbox" in nombre.casefold() for nombre in nombres)
    # Cada muestra salió de la voz, con esa frase y esa voz; no la fabricó la hoja.
    pedidas = {(frase.texto, frase.voz) for frase in conductor.voz.frases}
    for candidata in hoja.candidatas:
        assert set(candidata.muestras) == set(hoja.frases)
        for frase in hoja.frases:
            assert (frase, conductor.voz_tras(candidata.etiqueta)) in pedidas
        assert candidata.etiqueta not in nombres
        assert candidata.etiqueta in hoja.lo_que_ve_el_propietario
        # Escuchar cada muestra suena de verdad por el altavoz, con esa voz y esa
        # frase, y es la muestra de la hoja, no otra.
        for frase in hoja.frases:
            antes = len(conductor.altavoz.sonados)
            conductor.escucha_en_la_hoja(candidata.etiqueta, frase)
            nuevos = [sonido for sonido, _ in conductor.altavoz.sonados[antes:]]
            assert nuevos == [candidata.muestras[frase]]
            assert (nuevos[0].texto, nuevos[0].de_quien, nuevos[0].voz) == (
                frase,
                "sirius",
                conductor.voz_tras(candidata.etiqueta),
            )
    for frase in hoja.frases:
        assert frase in hoja.lo_que_ve_el_propietario
    visible = hoja.lo_que_ve_el_propietario.casefold()
    for escondido in (*nombres, "piper", "chatterbox", "es_es"):
        assert escondido.casefold() not in visible

    ordenes = {
        tuple(conductor.voz_tras(c.etiqueta) for c in conductor.hoja_de_voces().candidatas)
        for _ in range(20)
    }
    assert len(ordenes) > 1


@pieza("F", "la voz que elige el propietario queda para hablar")
def test_la_voz_que_elige_el_propietario_queda_para_hablar(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)

    # Sea cual sea la que elija, también la de personaje: queda al volver a abrir
    # Sirius, otro conductor sobre la misma base y los mismos ajustes, y es con la
    # que se pide y suena la frase del turno siguiente. Cada vuelta abre su hoja en
    # el Sirius vivo, porque las etiquetas son de cada hoja barajada.
    primera = conductor.hoja_de_voces()
    nombres = [conductor.voz_tras(candidata.etiqueta) for candidata in primera.candidatas]
    for nombre in nombres:
        hoja = conductor.hoja_de_voces()
        etiqueta = next(
            c.etiqueta for c in hoja.candidatas if conductor.voz_tras(c.etiqueta) == nombre
        )

        conductor.elige_voz(etiqueta)
        conductor.cierra()
        conductor = ConductorDeVoz(tmp_path)
        conductor.oye("Buenos días, Sirius.")

        assert conductor.voz.frases[-1].voz == nombre
        assert conductor.altavoz.sonados[-1][0].voz == nombre


@pieza("F", "no hay forma de clonar una voz")
def test_no_hay_forma_de_clonar_una_voz(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)

    assert not conductor.hay_forma_de_clonar_una_voz()
