"""Los hechos y las órdenes de memoria desde la ventana (pieza G de ADR-233, ADR-239).

La ventana de verdad, montada como al arrancar: «Proponer guardar…» solo sale en
lo que dice él, tras «olvida lo de…» la pantalla deja de decir qué había que
olvidar, y al abrirse sueña los días que faltan, sin que el turno se cruce con él.
"""

from __future__ import annotations

import threading
from collections.abc import Iterable, Sequence
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from pytestqt.qtbot import QtBot
from sqlalchemy import update

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import MessageModel
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.config.settings import load_settings, save_settings
from sirius.domain.conversation import MessageRole
from sirius.domain.facts import ProposedFact
from sirius.infrastructure.paths import resolve_paths
from sirius.main import _build_main_window
from sirius.ports.embeddings import EmbeddingError
from sirius.ports.llm import LLMCompleted, LLMProvider, LLMRequest, LLMStreamEvent
from sirius.presentation.message_view import MessageItemWidget

pytestmark = pytest.mark.gui


class _Modelo:
    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        del request
        yield LLMCompleted(text="Vale.", input_tokens=1, output_tokens=1)

    def cancel(self, operation_id: str) -> None:
        del operation_id


class _SinHuellas:
    model_name = "sin-huellas"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        del texts
        raise EmbeddingError("sin huellas")


class _Resumidor:
    def summarize(self, text: str, provider: LLMProvider) -> str:
        del provider
        return f"Resumen: {text}"


class _Extractor:
    def extract(self, text: str, provider: LLMProvider) -> list[ProposedFact]:
        del text, provider
        return [ProposedFact("propietario", "trabajo", "Trabaja de electricista")]


class _ResumidorQueEspera(_Resumidor):
    """Se queda en el primer día que resume hasta que lo suelten."""

    def __init__(self) -> None:
        self.empezado = threading.Event()
        self.suelta = threading.Event()
        self.resumidos: list[str] = []

    def summarize(self, text: str, provider: LLMProvider) -> str:
        self.empezado.set()
        self.suelta.wait(timeout=5)
        self.resumidos.append(text)
        return super().summarize(text, provider)


def _sirius(
    tmp_path: Path, resumidor: _Resumidor | None = None
) -> tuple[ConversationDependencies, Path]:
    rutas = resolve_paths()
    initialize_persistence(rutas)
    base = rutas.data_dir / "sirius.db"
    dependencias = build_conversation_dependencies(
        base,
        tmp_path / "copias",
        secret_store=FakeSecretStore(),
        text_embedder=_SinHuellas(),
        conversation_summarizer=resumidor or _Resumidor(),
        fact_extractor=_Extractor(),
    )
    dependencias.initial_project_use_case.create_initial_project("Charla", "Charlar")
    dependencias.send_message_use_case.set_llm_provider(_Modelo())
    return dependencias, base


def _ventana(qtbot: QtBot, dependencias: ConversationDependencies) -> Any:
    ventana = _build_main_window(dependencias, [])
    qtbot.addWidget(ventana)
    qtbot.waitUntil(lambda: not ventana.dream_in_progress, timeout=5000)
    return ventana


def _di(qtbot: QtBot, ventana: Any, texto: str) -> None:
    ventana.message_input.setText(texto)
    ventana.send_button.click()
    qtbot.waitUntil(lambda: ventana.send_button.isEnabled(), timeout=5000)


def _mensajes(ventana: Any) -> list[tuple[str, MessageItemWidget]]:
    lista = ventana.message_list
    salida = []
    for fila in range(lista.count()):
        widget = lista.itemWidget(lista.item(fila))
        assert isinstance(widget, MessageItemWidget)
        salida.append((lista.item(fila).text(), widget))
    return salida


def test_proponer_guardar_solo_sale_en_lo_que_dice_el(qtbot: QtBot, tmp_path: Path) -> None:
    dependencias, _ = _sirius(tmp_path)
    ventana = _ventana(qtbot, dependencias)
    ventana._prompt_multiline_with_default = lambda title, label, initial: initial

    _di(qtbot, ventana, "Vivo en Valencia.")

    (_, suyo), (_, de_sirius) = _mensajes(ventana)
    assert not suyo.propose_suggestion_button().isHidden()
    assert de_sirius.propose_suggestion_button().isHidden()

    suyo.propose_suggestion_button().click()

    pendientes = dependencias.get_knowledge_overview_use_case.get_overview().pending_suggestions
    assert [s.content for s in pendientes] == ["Vivo en Valencia."]


def test_al_reabrir_la_ventana_el_boton_sigue_solo_en_lo_suyo(qtbot: QtBot, tmp_path: Path) -> None:
    dependencias, _ = _sirius(tmp_path)
    dependencias.send_message_use_case.send_message("Vivo en Valencia.")

    ventana = _ventana(qtbot, dependencias)

    (_, suyo), (_, de_sirius) = _mensajes(ventana)
    assert not suyo.propose_suggestion_button().isHidden()
    assert de_sirius.propose_suggestion_button().isHidden()


def test_tras_olvida_lo_de_la_pantalla_ya_no_dice_que_habia_que_olvidar(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencias, _ = _sirius(tmp_path)
    ventana = _ventana(qtbot, dependencias)
    _di(qtbot, ventana, "Mi vecino Ramiro me tiene frito.")

    _di(qtbot, ventana, "Olvida lo de mi vecino Ramiro.")

    textos = [texto for texto, _ in _mensajes(ventana)]
    assert not any("Ramiro" in texto for texto in textos[2:]), textos


def test_al_abrirse_suena_los_dias_de_antes_y_avisa_de_lo_que_propone(
    qtbot: QtBot, tmp_path: Path
) -> None:
    dependencias, base = _sirius(tmp_path)
    ajustes = dict(load_settings())
    ajustes["ollama_chat_model"] = "modelo-local"
    save_settings(ajustes)
    resultado = dependencias.send_message_use_case.send_message("Hoy he cableado un edificio.")
    motor = build_engine(base)
    with motor.begin() as conexion:
        ayer = (resultado.user_message.created_at - timedelta(days=1)).replace(tzinfo=None)
        conexion.execute(
            update(MessageModel)
            .where(MessageModel.role == MessageRole.USER)
            .values(created_at=ayer)
        )
    motor.dispose()

    ventana = _ventana(qtbot, dependencias)

    assert "1 hecho para confirmar" in ventana.status_label.text()
    pendientes = dependencias.facts_use_case.pending_facts()
    assert [s.content for s in pendientes] == ["Trabaja de electricista"]


def test_el_turno_espera_al_dia_que_esta_sonando_y_el_sueno_no_vuelve_entre_turnos(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """La ronda 2 de Codex de la pieza F, llevada al sueño: el turno no empieza hasta
    que acaba el día que está soñando. Los días que quedan los sueña la próxima vez
    que se abra, no entre turno y turno, donde cada uno haría esperar al siguiente."""
    resumidor = _ResumidorQueEspera()
    dependencias, base = _sirius(tmp_path, resumidor)
    ajustes = dict(load_settings())
    ajustes["ollama_chat_model"] = "modelo-local"
    save_settings(ajustes)
    anteayer = dependencias.send_message_use_case.send_message("Anteayer fui a la obra.")
    ayer = dependencias.send_message_use_case.send_message("Ayer fui al médico.")
    motor = build_engine(base)
    with motor.begin() as conexion:
        for dias, resultado in ((2, anteayer), (1, ayer)):
            conexion.execute(
                update(MessageModel)
                .where(MessageModel.id == resultado.user_message.id)
                .values(
                    created_at=(resultado.user_message.created_at - timedelta(days=dias)).replace(
                        tzinfo=None
                    )
                )
            )
    motor.dispose()
    ventana = _build_main_window(dependencias, [])
    qtbot.addWidget(ventana)
    assert resumidor.empezado.wait(timeout=5)

    ventana.message_input.setText("Hola")
    ventana.send_button.click()
    assert ventana._active_send_worker is None
    resumidor.suelta.set()

    qtbot.waitUntil(lambda: ventana.send_button.isEnabled(), timeout=5000)
    qtbot.waitUntil(lambda: not ventana.dream_in_progress, timeout=5000)
    qtbot.wait(50)
    assert [texto for texto in resumidor.resumidos if "obra" in texto or "médico" in texto] == [
        "Él: Anteayer fui a la obra."
    ]
