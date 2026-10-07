"""La memoria propia de Sirius: qué vuelve y qué no (pieza E de ADR-233, PA-R02-07)."""

from __future__ import annotations

from datetime import UTC, datetime

from sirius.domain.conversation import Message, MessageRole, MessageStatus
from sirius.domain.own_memory import (
    IS_YOU_HEADING,
    NOT_YOU_HEADING,
    OWN_MEMORY_LIMIT,
    QUOTE_LIMIT,
    SAID_HEADING,
    OwnMemory,
    build_own_memory,
    render_own_memory,
    shared_topic_words,
    topic_words,
)
from sirius.domain.reply_mark import MarkedReply, ReplyMark


def _mensaje(
    numero: int,
    texto: str | None,
    *,
    rol: MessageRole = MessageRole.SIRIUS,
    estado: MessageStatus = MessageStatus.COMPLETED,
) -> Message:
    return Message(
        id=numero,
        conversation_id=1,
        sequence=numero,
        role=rol,
        content=texto,
        created_at=datetime(2026, 10, 7, tzinfo=UTC),
        status=estado,
    )


def _marca(mensaje: Message, marca: ReplyMark) -> MarkedReply:
    return MarkedReply(
        message_id=mensaje.id,
        sequence=mensaje.sequence,
        mark=marca,
        model="qwen-x",
        identity_version=2,
    )


def test_las_palabras_del_tema_van_sin_tildes_y_sin_las_vacias() -> None:
    assert topic_words("¿Qué opinas de la tortilla con cebolla, Sirius? Dímelo en 2026.") == {
        "tortilla",
        "cebolla",
        "dimelo",
    }


def test_el_singular_y_el_plural_son_el_mismo_tema() -> None:
    assert shared_topic_words(topic_words("cebollas y opiniones"), "Una cebolla, una opinión.") == 2
    assert shared_topic_words(topic_words("tortilla"), "Hoy toca paella.") == 0


def test_vuelve_lo_que_dijo_del_tema_y_no_lo_que_ya_va_en_la_peticion() -> None:
    vieja = _mensaje(2, "La tortilla, con cebolla, y no hay debate.")
    reciente = _mensaje(8, "Con cebolla, ya te lo dije: la tortilla es así.")
    otra = _mensaje(4, "El coche, mejor de segunda mano.")

    memoria = build_own_memory(
        "¿La tortilla con cebolla o sin?", [vieja, otra, reciente], [], in_request={reciente.id}
    )

    assert memoria.said == ("La tortilla, con cebolla, y no hay debate.",)


def test_lo_marcado_eso_no_nunca_vuelve_como_lo_que_ya_dijo() -> None:
    rechazada = _mensaje(2, "Estimado usuario, la tortilla con cebolla es una opción válida.")

    memoria = build_own_memory(
        "¿La tortilla con cebolla?", [rechazada], [_marca(rechazada, ReplyMark.NO_ES_SIRIUS)]
    )

    assert memoria.said == ()
    assert memoria.not_you == (rechazada.content,)


def test_gana_lo_que_comparte_mas_palabras_y_luego_lo_mas_reciente_y_sale_en_orden() -> None:
    respuestas = [
        _mensaje(2, "La tortilla, mejor con cebolla."),
        _mensaje(4, "Tortilla, siempre."),
        _mensaje(6, "Tortilla para cenar."),
        _mensaje(8, "Tortilla otra vez."),
        _mensaje(10, "La cebolla de la tortilla, bien pochada."),
    ]

    memoria = build_own_memory("tortilla con cebolla", respuestas, [])

    assert len(memoria.said) == OWN_MEMORY_LIMIT
    assert memoria.said == (
        "La tortilla, mejor con cebolla.",
        "Tortilla otra vez.",
        "La cebolla de la tortilla, bien pochada.",
    )


def test_solo_cuentan_sus_respuestas_completas_y_no_borradas() -> None:
    mensajes = [
        _mensaje(1, "La tortilla con cebolla.", rol=MessageRole.USER),
        _mensaje(2, "La tortilla, a medias.", estado=MessageStatus.CANCELLED),
        _mensaje(3, None),
    ]

    assert not build_own_memory("tortilla", mensajes, [])


def test_lo_que_si_es_y_lo_que_no_es_son_las_tres_ultimas_de_cada_marca() -> None:
    respuestas = [_mensaje(n, f"Respuesta {n}.") for n in range(1, 11)]
    marcas = [_marca(m, ReplyMark.ES_SIRIUS) for m in respuestas[:5]]
    marcas += [_marca(m, ReplyMark.NO_ES_SIRIUS) for m in respuestas[5:]]

    memoria = build_own_memory("hola", respuestas, marcas)

    assert memoria.is_you == ("Respuesta 3.", "Respuesta 4.", "Respuesta 5.")
    assert memoria.not_you == ("Respuesta 8.", "Respuesta 9.", "Respuesta 10.")


def test_lo_que_ya_vuelve_como_dicho_no_se_repite_como_lo_que_si_es() -> None:
    buena = _mensaje(2, "La tortilla, con cebolla.")

    memoria = build_own_memory("¿tortilla?", [buena], [_marca(buena, ReplyMark.ES_SIRIUS)])

    assert memoria.said == (buena.content,)
    assert memoria.is_you == ()


def test_cada_respuesta_va_en_una_linea_y_recortada() -> None:
    larga = _mensaje(2, "Tortilla.\n" + "palabra " * 100)

    [cita] = build_own_memory("tortilla", [larga], []).said

    assert "\n" not in cita
    assert len(cita) == QUOTE_LIMIT
    assert cita.endswith("…")


def test_sin_nada_no_se_escribe_ninguna_seccion_y_con_algo_solo_la_suya() -> None:
    assert render_own_memory(OwnMemory()) == []

    lineas = render_own_memory(OwnMemory(not_you=("Estimado usuario.",)))

    assert NOT_YOU_HEADING in lineas
    assert SAID_HEADING not in lineas
    assert IS_YOU_HEADING not in lineas
    assert "- «Estimado usuario.»" in lineas
