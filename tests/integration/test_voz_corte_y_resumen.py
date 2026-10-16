"""El corte de lo que suena y el resumen de la charla, con Sirius de verdad (ADR-245).

La ronda 3 de Codex sobre la PR #690 dijo que, si le cortan mientras la charla resume en
el turno 18, el resumen da por oída entera la respuesta que sonaba, porque el corte se
guarda al volver de la charla. No pasa: el resumen deja fuera las cuatro últimas
respuestas (``TURNS_KEPT_VERBATIM``), y la que suena es la última. Esta prueba hace su
caso con el conductor de la 0.3, que es Sirius de verdad con los dobles del oído y la voz,
y queda de guarda: si el resumen llegara algún día a la respuesta que suena, falla.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Iterable
from contextlib import closing
from pathlib import Path

import pytest
from conductor_robot_0_3 import ConductorDeVoz

from sirius.domain.conversation_summary import TURNS_BETWEEN_SUMMARIES
from sirius.ports.llm import LLMRequest, LLMStreamEvent

pytestmark = pytest.mark.integration


def test_si_le_cortan_mientras_resume_el_resumen_no_lleva_lo_que_sonaba(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)
    for turno in range(1, TURNS_BETWEEN_SUMMARIES):
        assert conductor.oye(f"Sirius, la pregunta {turno}.").contestado is not None

    # En el turno 18 la charla resume después de guardar la respuesta, que sigue sonando,
    # y mientras resume el propietario le habla encima: su caso.
    resumidos: list[str] = []
    parado_mientras_resumia: list[bool] = []
    contesta = conductor.modelo.stream_response

    def resume_y_le_cortan(request: LLMRequest) -> Iterable[LLMStreamEvent]:
        if request.operation_id.startswith("resumen-"):
            resumidos.append(request.input_text)
            conductor.habla_encima("Espera, espera, que tengo prisa.")
            limite = time.perf_counter() + 2
            while conductor.altavoz.parado_en is None and time.perf_counter() < limite:
                time.sleep(0.01)
            parado_mientras_resumia.append(conductor.altavoz.parado_en is not None)
        yield from contesta(request)

    conductor.modelo.stream_response = resume_y_le_cortan  # type: ignore[method-assign]
    conductor.altavoz.sigue_sonando = True
    conductor.oido.pide_silencios(2)
    ultima = conductor.oye(f"Sirius, la pregunta {TURNS_BETWEEN_SUMMARIES}.", y_calla=2)
    respuesta = ultima.contestado
    assert respuesta is not None

    # Le cortó mientras resumía, y el resumen no llevaba lo que sonaba.
    assert parado_mientras_resumia == [True]
    [resumido] = resumidos
    assert "Sirius, la pregunta 1." in resumido
    assert respuesta not in resumido
    with closing(sqlite3.connect(conductor.base)) as conexion:
        (hasta,) = conexion.execute(
            "SELECT max(up_to_sequence) FROM conversation_summaries"
        ).fetchone()
        (suya,) = conexion.execute(
            "SELECT sequence FROM messages WHERE content = ?", (respuesta,)
        ).fetchone()
    assert hasta < suya

    # Lo que dijo encima va a la charla, y el modelo lee la respuesta con su corte.
    corte = conductor.calla(1)
    assert corte.oido == "Espera, espera, que tengo prisa."
    assert conductor.lo_que_oyo_de(respuesta, conductor.peticiones[-1]) is not None
