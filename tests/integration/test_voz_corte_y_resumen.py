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
import threading
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


def test_si_le_cortan_mientras_resume_lo_nuevo_no_espera_al_resumen(tmp_path: Path) -> None:
    """Revisión del corte (ADR-254): el resumen va con la operación del turno, y cortarle
    mientras resume lo corta también. Lo nuevo llega al modelo enseguida, sin esperar al
    resumen, y el resumen lo hace el turno siguiente, sin lo que sonaba."""
    conductor = ConductorDeVoz(tmp_path)
    for turno in range(1, TURNS_BETWEEN_SUMMARIES):
        assert conductor.oye(f"Sirius, la pregunta {turno}.").contestado is not None

    pedidas: list[tuple[str, float]] = []
    contesta = conductor.modelo.stream_response

    def le_corta() -> None:
        # En un hilo aparte, para no retener al modelo, con el resumen a medias.
        conductor.habla_encima("Espera, espera, que tengo prisa.")

    def resume_despacio_la_primera_vez(request: LLMRequest) -> Iterable[LLMStreamEvent]:
        pedidas.append((request.operation_id, time.perf_counter()))
        if request.operation_id.startswith("resumen-") and len(pedidas) == 2:
            hilo = threading.Thread(target=le_corta, daemon=True)
            # Sin cortarle, el resumen tardaría 3 s.
            conductor.modelo.contesta_despacio(
                ["Un resumen ", "que tarda ", "muchísimo."],
                pausa=1.0,
                tras_el_primer_trozo=hilo.start,
            )
        yield from contesta(request)

    conductor.modelo.stream_response = resume_despacio_la_primera_vez  # type: ignore[method-assign]
    conductor.altavoz.sigue_sonando = True
    conductor.oido.pide_silencios(2)
    ultima = conductor.oye(f"Sirius, la pregunta {TURNS_BETWEEN_SUMMARIES}.", y_calla=2)
    respuesta = ultima.contestado
    assert respuesta is not None
    corte = conductor.calla(1)

    # Pidió el resumen tras la respuesta 18 y le cortaron con él a medias: lo nuevo llegó al
    # modelo en menos de 1 s desde que calló, con el reloj de los dobles.
    assert corte.oido == "Espera, espera, que tengo prisa."
    respuesta_18, resumen_cortado, lo_nuevo = pedidas[:3]
    assert resumen_cortado[0] == f"resumen-{respuesta_18[0]}"
    parado_en = conductor.altavoz.parado_en
    assert parado_en is not None
    assert resumen_cortado[1] < parado_en
    esperado = lo_nuevo[1] - parado_en
    assert 0 <= esperado < 1, f"lo nuevo esperó {esperado:.2f} s desde que calló"
    assert conductor.peticiones[-2].texto == "Espera, espera, que tengo prisa."

    # El resumen cortado no guardó nada; lo hizo el turno siguiente, y sin lo que sonaba.
    [resumen_siguiente] = pedidas[3:]
    assert resumen_siguiente[0] == f"resumen-{lo_nuevo[0]}"
    with closing(sqlite3.connect(conductor.base)) as conexion:
        resumenes = conexion.execute(
            "SELECT up_to_sequence, content FROM conversation_summaries"
        ).fetchall()
        (suya,) = conexion.execute(
            "SELECT sequence FROM messages WHERE content = ?", (respuesta,)
        ).fetchone()
    [(hasta, contenido)] = resumenes
    assert "muchísimo" not in contenido
    assert hasta < suya
