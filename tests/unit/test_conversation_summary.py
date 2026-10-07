"""Cuándo y qué se resume de una charla larga (pieza D de ADR-233, PA-R02-05)."""

from __future__ import annotations

from datetime import UTC, datetime

from sirius.domain.conversation import Message, MessageRole, MessageStatus
from sirius.domain.conversation_summary import (
    TURNS_BETWEEN_SUMMARIES,
    TURNS_KEPT_VERBATIM,
    messages_to_summarize,
    summary_input,
)


def _charla(turnos: int) -> list[Message]:
    mensajes: list[Message] = []
    for n in range(1, turnos + 1):
        for rol, texto in (
            (MessageRole.USER, f"pregunta {n}"),
            (MessageRole.SIRIUS, f"respuesta {n}"),
        ):
            mensajes.append(
                Message(
                    id=len(mensajes) + 1,
                    conversation_id=1,
                    sequence=len(mensajes) + 1,
                    role=rol,
                    content=texto,
                    created_at=datetime(2026, 10, 7, tzinfo=UTC),
                    status=MessageStatus.COMPLETED,
                )
            )
    return mensajes


def test_entre_15_y_20_turnos_como_pide_el_plan() -> None:
    assert 15 <= TURNS_BETWEEN_SUMMARIES <= 20


def test_con_menos_turnos_no_se_resume_nada() -> None:
    assert messages_to_summarize(_charla(TURNS_BETWEEN_SUMMARIES - 1)) == ()


def test_al_llegar_se_resume_todo_menos_los_ultimos_turnos() -> None:
    charla = _charla(TURNS_BETWEEN_SUMMARIES)

    resumidos = messages_to_summarize(charla)

    turnos_resumidos = TURNS_BETWEEN_SUMMARIES - TURNS_KEPT_VERBATIM
    assert len(resumidos) == 2 * turnos_resumidos
    assert resumidos[-1].content == f"respuesta {turnos_resumidos}"


def test_lo_que_se_da_a_resumir_lleva_el_resumen_anterior_y_quien_dijo_que() -> None:
    texto = summary_input("Hablaron de coches.", _charla(1))

    assert texto.startswith("Resumen anterior:\nHablaron de coches.")
    assert "Él: pregunta 1" in texto
    assert "Sirius: respuesta 1" in texto
