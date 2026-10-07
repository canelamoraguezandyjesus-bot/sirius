"""Los botones «Eso es Sirius» y «Eso no» de cada respuesta (pieza D de ADR-233, PA-R02-06)."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.composition_root import build_conversation_dependencies
from sirius.domain.reply_mark import ReplyMark
from sirius.infrastructure.paths import resolve_paths
from sirius.main import _build_main_window
from sirius.ports.llm import LLMCompleted, LLMRequest, LLMStreamEvent
from sirius.presentation.message_view import MessageItemWidget

pytestmark = pytest.mark.gui


def _respuesta(qtbot: QtBot, *, marcas: bool, marca: ReplyMark | None = None) -> MessageItemWidget:
    widget = MessageItemWidget()
    qtbot.addWidget(widget)
    widget.set_message(
        "Sirius",
        "Buenos días, jefe.",
        bold=True,
        message_id=7,
        show_propose_suggestion=True,
        show_marks=marcas,
        current_mark=marca,
    )
    return widget


def test_solo_las_respuestas_completas_llevan_los_dos_botones(qtbot: QtBot) -> None:
    con = _respuesta(qtbot, marcas=True)
    sin = _respuesta(qtbot, marcas=False)

    assert [b.text() for b in con.mark_buttons] == ["Eso es Sirius", "Eso no"]
    assert all(not b.isHidden() for b in con.mark_buttons)
    assert all(b.isHidden() for b in sin.mark_buttons)


def test_pulsar_avisa_con_el_mensaje_y_la_marca_y_deja_solo_ese_pulsado(qtbot: QtBot) -> None:
    widget = _respuesta(qtbot, marcas=True)
    avisos: list[tuple[int, str]] = []
    widget.mark_requested.connect(lambda mensaje, marca: avisos.append((mensaje, marca)))
    es_sirius, eso_no = widget.mark_buttons

    eso_no.click()
    es_sirius.click()

    assert avisos == [(7, "eso no"), (7, "eso es Sirius")]
    assert es_sirius.isChecked() and not eso_no.isChecked()


def test_la_marca_guardada_se_ve_al_cargar_la_charla(qtbot: QtBot) -> None:
    widget = _respuesta(qtbot, marcas=True, marca=ReplyMark.NO_ES_SIRIUS)

    es_sirius, eso_no = widget.mark_buttons
    assert eso_no.isChecked() and not es_sirius.isChecked()


class _Modelo:
    model_name = "modelo-de-prueba"

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        yield LLMCompleted(text="Buenos días, jefe.", input_tokens=1, output_tokens=1)

    def cancel(self, operation_id: str) -> None:
        del operation_id


def test_si_no_se_puede_guardar_la_marca_los_botones_vuelven_a_la_que_habia(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ronda 1 de Codex: la ventana nunca enseña una marca que la base no tiene."""
    rutas = resolve_paths()
    initialize_persistence(rutas)
    sirius = build_conversation_dependencies(
        rutas.data_dir / "sirius.db", tmp_path / "copias", secret_store=FakeSecretStore()
    )
    sirius.initial_project_use_case.create_initial_project("Charla", "Charlar")
    sirius.send_message_use_case.set_llm_provider(_Modelo())
    respuesta = sirius.send_message_use_case.send_message("Buenos días.").sirius_message
    sirius.mark_reply_use_case.mark(respuesta.id, ReplyMark.NO_ES_SIRIUS)

    def disco_lleno(message_id: int, mark: ReplyMark) -> None:
        raise OSError("disco lleno")

    monkeypatch.setattr(sirius.mark_reply_use_case, "mark", disco_lleno)
    ventana = _build_main_window(sirius, [])
    qtbot.addWidget(ventana)
    avisos: list[str] = []
    ventana._show_warning = lambda titulo, texto: avisos.append(titulo)
    lista = ventana.message_list
    [widget] = [
        w
        for w in (lista.itemWidget(lista.item(i)) for i in range(lista.count()))
        if isinstance(w, MessageItemWidget) and not w.mark_buttons[0].isHidden()
    ]
    es_sirius, eso_no = widget.mark_buttons
    assert eso_no.isChecked() and not es_sirius.isChecked()

    es_sirius.click()

    assert avisos == ["No se pudo guardar la marca"]
    assert eso_no.isChecked() and not es_sirius.isChecked()
