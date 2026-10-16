"""Cuándo y qué se resume de una charla larga (pieza D de ADR-233, PA-R02-05)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from sirius.domain.conversation import (
    CUT_HEARD_IN_SUMMARY,
    CUT_NOTHING_HEARD_IN_SUMMARY,
    Message,
    MessageRole,
    MessageStatus,
)
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


def test_entre_un_resumen_y_el_siguiente_tambien_pasan_18_turnos() -> None:
    """Ronda 2 de Codex: los cuatro turnos que el primer resumen deja sin resumir ya
    contaron para él; si contaran otra vez, el segundo llegaría 14 turnos después."""
    charla = _charla(60)
    respuestas = [m for m in charla if m.role is MessageRole.SIRIUS]
    hasta = messages_to_summarize(charla[: 2 * TURNS_BETWEEN_SUMMARIES])[-1].sequence
    turnos_al_resumir = []
    for turno in range(TURNS_BETWEEN_SUMMARIES + 1, 61):
        sin_resumir = [m for m in charla[: 2 * turno] if m.sequence > hasta]
        resumidos = messages_to_summarize(sin_resumir, after_a_summary=True)
        if resumidos:
            turnos_al_resumir.append(turno)
            hasta = resumidos[-1].sequence

    assert respuestas[TURNS_BETWEEN_SUMMARIES - 1].content == "respuesta 18"
    assert turnos_al_resumir == [36, 54]


def test_lo_que_se_da_a_resumir_lleva_el_resumen_anterior_y_quien_dijo_que() -> None:
    texto = summary_input("Hablaron de coches.", _charla(1))

    assert texto.startswith("Resumen anterior:\nHablaron de coches.")
    assert "Él: pregunta 1" in texto
    assert "Sirius: respuesta 1" in texto


def test_una_respuesta_que_le_cortaron_se_resume_con_lo_que_se_oyo() -> None:
    # Ronda 1 de Codex sobre la PR #690 (ADR-245): si no, al resumirla quedaría por dicha
    # entera, y la nota se perdería del contexto de después.
    pregunta, respuesta, otra_pregunta, otra = _charla(2)
    cortada = replace(respuesta, heard_when_cut="respuesta")
    nada = replace(otra, heard_when_cut="")

    texto = summary_input(None, [pregunta, cortada, otra_pregunta, nada])

    assert texto.splitlines() == [
        "Él: pregunta 1",
        "Sirius: respuesta 1",
        CUT_HEARD_IN_SUMMARY.format(heard="respuesta"),
        "Él: pregunta 2",
        "Sirius: respuesta 2",
        CUT_NOTHING_HEARD_IN_SUMMARY,
    ]
