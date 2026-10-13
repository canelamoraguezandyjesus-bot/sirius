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
altavoz. Una pieza que atajara, metiendo el texto en la charla sin oírlo o
contestando sin hablar, no las pasa (rondas 1 y 2 de Codex sobre la PR #686).
"""

from __future__ import annotations

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
        if not sonido.es_silencio and sonido.de_quien == "propietario"
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
    assert conductor.transcriptor.transcritos == ["Buenos días, Sirius."]
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
    assert conductor.transcriptor.transcritos == []
    assert not conductor.hubo_peticion_al_modelo_en_el_ultimo_turno_de_voz()

    turno = conductor.calla(2)

    assert sum(1 for sonido in conductor.oido.vistos if sonido.es_silencio) >= 3
    assert conductor.transcriptor.transcritos == ["Sirius, estaba pensando que"]
    assert turno.oido == "Sirius, estaba pensando que"
    assert turno.contestado == "Respuesta 1 de Sirius."


@pieza("B", "«olvida eso» dicho por voz olvida")
def test_olvida_eso_dicho_por_voz_olvida(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)
    conductor.oye("Sirius, la clave de la alarma es Zarzamora.")
    assert conductor.busca_en_toda_la_base("Zarzamora") != [], (
        "lo dicho por voz tiene que guardarse"
    )

    turno = conductor.oye("Olvida eso.")

    assert turno.para_el
    assert conductor.transcriptor.transcritos[-1] == "Olvida eso."
    assert conductor.busca_en_toda_la_base("Zarzamora") == []
    assert not conductor.lo_vio_el_modelo_en_el_ultimo_turno("Zarzamora")


# --- PA-R03-02 · Habla con Piper, frase a frase desde la primera --------------


@pieza("C", "empieza a hablar con la primera frase, antes de que el modelo acabe")
def test_empieza_a_hablar_con_la_primera_frase_antes_de_que_el_modelo_acabe(
    tmp_path: Path,
) -> None:
    conductor = ConductorDeVoz(tmp_path)
    conductor.el_modelo_contesta_despacio(
        ["Primera frase, jefe.", " Y la segunda, que es más larga y tarda más."]
    )

    turno = conductor.oye("Sirius, cuéntame algo.")

    assert turno.hablado == (
        "Primera frase, jefe.",
        "Y la segunda, que es más larga y tarda más.",
    )
    assert [frase.texto for frase in conductor.voz.frases] == list(turno.hablado)
    assert conductor.voz.frases[0].momento < conductor.momento_en_que_el_modelo_acabo()
    assert [sonido.texto for sonido, _ in conductor.altavoz.sonados] == list(turno.hablado)


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
    assert conductor.voz_con_la_que_habla().startswith("es_ES-")
    assert [(s.texto, s.de_quien) for s, _ in conductor.altavoz.sonados] == [
        ("Respuesta 1 de Sirius.", "sirius")
    ]


# --- PA-R03-03 · Su propia voz no se toma por la del propietario --------------


@pieza("C", "su propia voz, de vuelta por el micro, no empieza un turno")
def test_su_propia_voz_no_empieza_un_turno(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)
    conductor.altavoz.con_eco = True

    turno = conductor.oye("Buenos días, Sirius.")

    assert turno.hablado == ("Respuesta 1 de Sirius.",)
    # El eco existió: el altavoz lo devolvió al micro.
    assert any(
        s.de_quien == "sirius" for s in (*conductor.micro.leidos, *conductor.micro.pendientes)
    )
    assert conductor.transcriptor.transcritos == ["Buenos días, Sirius."]
    assert len(conductor.peticiones) == 1
    assert conductor.charla_guardada()[-2:] == (
        ("propietario", "Buenos días, Sirius."),
        ("Sirius", "Respuesta 1 de Sirius."),
    )


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
    assert any(s.de_quien == "sirius" for s in conductor.micro.leidos)
    assert conductor.altavoz.parado_en is None
    assert conductor.transcriptor.transcritos == ["Sirius, cuéntame tu vida."]
    assert len(conductor.peticiones) == 1

    leidos_antes = len(conductor.micro.leidos)
    corte = conductor.oye_mientras_habla("Espera, espera, que tengo prisa.")

    # La voz del propietario, con el eco sonando a la vez, sí atraviesa.
    assert conductor.transcriptor.transcritos == [
        "Sirius, cuéntame tu vida.",
        "Espera, espera, que tengo prisa.",
    ]
    assert conductor.altavoz.parado_en is not None
    assert conductor.altavoz.parado_en > min(_momentos_de_su_voz(conductor, leidos_antes))
    assert corte.oido == "Espera, espera, que tengo prisa."
    assert corte.contestado == "Vale, vale."


# --- PA-R03-05 · No guarda audio ----------------------------------------------


@pieza("D", "tras varios turnos de voz no queda ningún audio guardado")
def test_tras_varios_turnos_de_voz_no_queda_ningun_audio_guardado(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)

    for frase in ("Buenos días, Sirius.", "¿Qué tal has dormido?", "Pues yo fatal."):
        conductor.oye(frase)
    conductor.cierra()

    assert conductor.escrituras_en_disco() == []
    assert conductor.ficheros_de_audio_nuevos() == []
    assert conductor.audio_en_la_base() == []
    assert conductor.busca_en_toda_la_base("Pues yo fatal.") != []


@pieza("D", "lo que no era para él no se guarda ni como texto")
def test_lo_que_no_era_para_el_no_se_guarda_ni_como_texto(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)

    turno = conductor.oye("Y mañana, cielos despejados en toda la península.")
    conductor.cierra()

    assert conductor.transcriptor.transcritos == [
        "Y mañana, cielos despejados en toda la península."
    ]
    assert not turno.para_el
    assert conductor.busca_en_toda_la_base("cielos despejados") == []
    assert conductor.escrituras_en_disco() == []
    assert conductor.ficheros_de_audio_nuevos() == []


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

    seguida = conductor.oye("¿Has dormido bien?")

    assert seguida.para_el
    assert seguida.contestado == "Respuesta 2 de Sirius."

    conductor.reloj.avanza(conductor.segundos_de_charla() + 1)
    tarde = conductor.oye("¿Has dormido bien?")

    assert conductor.transcriptor.transcritos[-1] == "¿Has dormido bien?"
    assert not tarde.para_el
    assert tarde.contestado is None
    assert len(conductor.peticiones) == 2


@pieza("D", "lo que no es para él no llega al modelo")
def test_lo_que_no_es_para_el_no_llega_al_modelo(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)

    turno = conductor.oye("Vamos con el tiempo: mañana lloverá en el norte.")

    assert conductor.transcriptor.transcritos == [
        "Vamos con el tiempo: mañana lloverá en el norte."
    ]
    assert not turno.para_el
    assert not conductor.hubo_peticion_al_modelo_en_el_ultimo_turno_de_voz()
    assert turno.hablado == ()
    assert conductor.altavoz.sonados == []
    assert conductor.peticiones == []


# --- PA-R03-07 · Se le puede cortar -------------------------------------------


@pieza("E", "si el propietario habla mientras Sirius habla, Sirius se calla y atiende lo nuevo")
def test_si_el_propietario_habla_sirius_se_calla_y_atiende_lo_nuevo(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(
        tmp_path, respuestas=["Una respuesta larguísima que no acaba nunca.", "Vale, vale."]
    )
    conductor.altavoz.sigue_sonando = True
    conductor.oye("Sirius, cuéntame tu vida.")
    assert conductor.altavoz.parado_en is None

    leidos_antes = len(conductor.micro.leidos)
    corte = conductor.oye_mientras_habla("Espera, espera, que tengo prisa.")

    # Medio segundo desde que el micro leyó su voz hasta que el altavoz paró, con
    # los relojes de los dobles.
    assert conductor.altavoz.parado_en is not None
    empezo_a_hablar = min(_momentos_de_su_voz(conductor, leidos_antes))
    assert (conductor.altavoz.parado_en - empezo_a_hablar) * 1000 < 500
    assert corte.oido == "Espera, espera, que tengo prisa."
    assert corte.contestado == "Vale, vale."
    assert corte.hablado == ("Vale, vale.",)


@pieza("E", "lo que iba a decir queda escrito entero aunque le corten")
def test_lo_que_iba_a_decir_queda_escrito_entero_aunque_le_corten(tmp_path: Path) -> None:
    larga = "Una respuesta larguísima que no acaba nunca."
    conductor = ConductorDeVoz(tmp_path, respuestas=[larga, "Vale, vale."])
    conductor.altavoz.sigue_sonando = True
    conductor.oye("Sirius, cuéntame tu vida.")

    conductor.oye_mientras_habla("Espera, espera, que tengo prisa.")

    assert conductor.altavoz.parado_en is not None
    assert ("Sirius", larga) in conductor.charla_guardada()


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

    assert turno.oido is None
    assert conductor.orden_para_instalar_la_voz() in turno.aviso
    assert conductor.descargas() == 0
    assert conductor.conexiones_de_red() == []


@pieza("C", "oye y habla con las herramientas locales del plan")
def test_oye_y_habla_con_las_herramientas_locales_del_plan(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)

    assert dict(conductor.herramientas()) == _HERRAMIENTAS_DEL_PLAN


# --- PA-R03-09 · La tubería de Sirius añade poco ------------------------------


@pieza("C", "con oído, modelo y voz instantáneos, la tubería añade menos de 200 ms")
def test_del_final_de_su_voz_al_primer_sonido_la_tuberia_anade_menos_de_200_ms(
    tmp_path: Path,
) -> None:
    conductor = ConductorDeVoz(tmp_path)
    tiempos: list[float] = []

    for n in range(1, 21):
        leidos_antes = len(conductor.micro.leidos)
        sonados_antes = len(conductor.altavoz.sonados)
        turno = conductor.oye(f"Sirius, pregunta número {n}.")
        assert turno.hablado == (f"Respuesta {n} de Sirius.",)
        # Del último sonido con su voz que leyó el micro al primero que sonó por el
        # altavoz, con los relojes de los dobles.
        fin_de_su_voz = max(_momentos_de_su_voz(conductor, leidos_antes))
        _sonido, primer_sonido = conductor.altavoz.sonados[sonados_antes]
        tiempos.append((primer_sonido - fin_de_su_voz) * 1000)

    assert percentil(tiempos, 95) < 200


# --- PA-R03-10 · Elegir su voz a ciegas ---------------------------------------


@pieza("F", "la prueba de voces da cinco frases con cuatro a seis voces barajadas y sin nombre")
def test_la_prueba_de_voces_da_cinco_frases_con_cuatro_a_seis_voces_barajadas_y_sin_nombre(
    tmp_path: Path,
) -> None:
    conductor = ConductorDeVoz(tmp_path)

    hoja = conductor.hoja_de_voces()

    assert len(hoja.frases) == 5
    assert 4 <= len(hoja.candidatas) <= 6
    nombres = {conductor.voz_tras(candidata.etiqueta) for candidata in hoja.candidatas}
    assert len(nombres) == len(hoja.candidatas)
    assert any(nombre.startswith("es_ES-") for nombre in nombres)
    assert any("chatterbox" in nombre.casefold() for nombre in nombres)
    for candidata in hoja.candidatas:
        assert set(candidata.muestras) == set(hoja.frases)
        assert candidata.etiqueta not in nombres
        assert candidata.etiqueta in hoja.lo_que_ve_el_propietario
        # Cada botón de escuchar suena de verdad, con la voz y la frase que dice.
        for frase in hoja.frases:
            sonido = conductor.escucha_en_la_hoja(candidata.etiqueta, frase)
            assert sonido.texto == frase
            assert sonido.de_quien == conductor.voz_tras(candidata.etiqueta)
            assert conductor.altavoz.sonados[-1][0] == sonido
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
    hoja = conductor.hoja_de_voces()
    elegida = hoja.candidatas[-1]
    nombre = conductor.voz_tras(elegida.etiqueta)

    conductor.elige_voz(elegida.etiqueta)
    conductor.reabre()

    assert conductor.voz_con_la_que_habla() == nombre
    conductor.oye("Buenos días, Sirius.")
    assert conductor.altavoz.sonados[-1][0].de_quien == nombre


@pieza("F", "no hay forma de clonar una voz")
def test_no_hay_forma_de_clonar_una_voz(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)

    assert not conductor.hay_forma_de_clonar_una_voz()
