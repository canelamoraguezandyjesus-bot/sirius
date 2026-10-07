"""Modo, marcas, recordatorio y resúmenes de la charla, en SQLite (pieza D de ADR-233)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path

import pytest

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_robot_conversation import (
    build_sqlite_robot_conversation_repository,
)
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.robot_conversation import (
    ConversationModeUseCase,
    ConversationSummaryService,
    MarkReplyUseCase,
)
from sirius.application.send_message import SendMessageUseCase
from sirius.composition_root import build_conversation_dependencies
from sirius.domain.conversation import MessageRole
from sirius.domain.conversation_mode import (
    ENTERING_SERIOUS_MODE,
    MODE_INSTRUCTIONS,
    ConversationMode,
)
from sirius.domain.reply_mark import ReplyMark
from sirius.domain.robot_seed import ROBOT_SEED_REMINDER
from sirius.infrastructure.paths import resolve_paths
from sirius.ports.llm import (
    LLMCompleted,
    LLMError,
    LLMErrorKind,
    LLMProvider,
    LLMRequest,
    LLMStreamEvent,
    LLMTextDelta,
)

pytestmark = pytest.mark.integration


def _base(tmp_path: Path) -> Path:
    base = tmp_path / "sirius.db"
    upgrade_to_head(base)
    build_sqlite_conversation_repository(base).get_or_create_main_conversation()
    return base


def test_el_modo_empieza_normal_y_se_guarda(tmp_path: Path) -> None:
    base = _base(tmp_path)
    repositorio = build_sqlite_robot_conversation_repository(base)
    conversacion = build_sqlite_conversation_repository(base).get_or_create_main_conversation()

    assert repositorio.get_mode(conversacion.id) is ConversationMode.NORMAL
    repositorio.set_mode(conversacion.id, ConversationMode.SERIO)
    repositorio.set_mode(conversacion.id, ConversationMode.PARA)

    otro = build_sqlite_robot_conversation_repository(base)
    assert otro.get_mode(conversacion.id) is ConversationMode.PARA


def test_soltar_el_modo_desde_la_ventana(tmp_path: Path) -> None:
    base = _base(tmp_path)
    repositorio = build_sqlite_robot_conversation_repository(base)
    conversaciones = build_sqlite_conversation_repository(base)
    repositorio.set_mode(
        conversaciones.get_or_create_main_conversation().id, ConversationMode.SERIO
    )
    caso = ConversationModeUseCase(conversaciones, repositorio)

    assert caso.current() is ConversationMode.SERIO
    caso.release()
    assert caso.current() is ConversationMode.NORMAL


def test_las_marcas_guardan_el_modelo_y_se_pueden_cambiar(tmp_path: Path) -> None:
    base = _base(tmp_path)
    conversaciones = build_sqlite_conversation_repository(base)
    conversacion = conversaciones.get_or_create_main_conversation()
    pregunta = conversaciones.append_message(conversacion.id, MessageRole.USER, "hola")
    respuesta = conversaciones.append_message(
        conversacion.id, MessageRole.SIRIUS, "Buenos días, jefe.", identity_version=2
    )
    repositorio = build_sqlite_robot_conversation_repository(base)
    caso = MarkReplyUseCase(repositorio)

    repositorio.record_model(respuesta.id, "qwen-x")
    caso.mark(respuesta.id, ReplyMark.NO_ES_SIRIUS)
    caso.mark(respuesta.id, ReplyMark.ES_SIRIUS)

    [marcada] = caso.marked_replies()
    assert (marcada.message_id, marcada.mark, marcada.model, marcada.identity_version) == (
        respuesta.id,
        ReplyMark.ES_SIRIUS,
        "qwen-x",
        2,
    )
    assert caso.count(last=50) == (1, 1)
    with pytest.raises(ValueError, match="no es una respuesta de Sirius"):
        caso.mark(pregunta.id, ReplyMark.ES_SIRIUS)


def test_solo_hay_dos_marcas() -> None:
    assert {marca.value for marca in ReplyMark} == {"eso es Sirius", "eso no"}


def test_el_resumen_vigente_es_el_que_llega_mas_lejos(tmp_path: Path) -> None:
    base = _base(tmp_path)
    repositorio = build_sqlite_robot_conversation_repository(base)
    conversacion = build_sqlite_conversation_repository(base).get_or_create_main_conversation()

    assert repositorio.latest(conversacion.id) is None
    repositorio.add(conversacion.id, 28, "primero")
    repositorio.add(conversacion.id, 64, "segundo")

    vigente = repositorio.latest(conversacion.id)
    assert vigente is not None
    assert (vigente.up_to_sequence, vigente.content) == (64, "segundo")


class _Modelo:
    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        del request
        yield LLMTextDelta(text="vale")
        yield LLMCompleted(text="vale", input_tokens=1, output_tokens=1)

    def cancel(self, operation_id: str) -> None:
        del operation_id


class _ResumidorQueFalla:
    def summarize(self, text: str, provider: LLMProvider) -> str:
        del text, provider
        msg = "sin modelo"
        raise RuntimeError(msg)


def test_si_resumir_falla_la_charla_sigue_y_no_se_guarda_nada(tmp_path: Path) -> None:
    base = _base(tmp_path)
    conversaciones = build_sqlite_conversation_repository(base)
    conversacion = conversaciones.get_or_create_main_conversation()
    for n in range(20):
        conversaciones.append_message(conversacion.id, MessageRole.USER, f"pregunta {n}")
        conversaciones.append_message(conversacion.id, MessageRole.SIRIUS, f"respuesta {n}")
    repositorio = build_sqlite_robot_conversation_repository(base)
    servicio = ConversationSummaryService(conversaciones, repositorio, _ResumidorQueFalla())

    assert servicio.maybe_summarize(conversacion.id, _Modelo()) is False
    assert repositorio.latest(conversacion.id) is None


def test_los_textos_de_los_modos_son_distintos_y_el_vacile_solo_es_del_serio() -> None:
    assert MODE_INSTRUCTIONS[ConversationMode.SERIO] != MODE_INSTRUCTIONS[ConversationMode.PARA]
    assert MODE_INSTRUCTIONS[ConversationMode.NORMAL] == ""
    assert "vale, jefe" in ENTERING_SERIOUS_MODE


class _ModeloQueGraba:
    model_name = "qwen-x"

    def __init__(self, *, falla: bool = False) -> None:
        self.falla = falla
        self.instrucciones: list[str] = []

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        self.instrucciones.append(request.instructions)
        if self.falla:
            yield LLMError(kind=LLMErrorKind.CONNECTION, message="No se pudo contactar.")
            return
        yield LLMCompleted(text="vale", input_tokens=1, output_tokens=1)

    def cancel(self, operation_id: str) -> None:
        del operation_id


def _sirius(tmp_path: Path, modelo: _ModeloQueGraba) -> tuple[Path, SendMessageUseCase]:
    rutas = resolve_paths()
    initialize_persistence(rutas)
    base = rutas.data_dir / "sirius.db"
    dependencias = build_conversation_dependencies(
        base, tmp_path / "copias", secret_store=FakeSecretStore()
    )
    dependencias.initial_project_use_case.create_initial_project("Charla", "Charlar")
    dependencias.send_message_use_case.set_llm_provider(modelo)
    return base, dependencias.send_message_use_case


def _modelos_apuntados(base: Path) -> list[tuple[int, str | None]]:
    with sqlite3.connect(base) as conexion:
        return list(conexion.execute("SELECT message_id, model FROM reply_marks"))


def test_cada_respuesta_completa_apunta_con_que_modelo_se_dio(tmp_path: Path) -> None:
    base, enviar = _sirius(tmp_path, _ModeloQueGraba())

    resultado = enviar.send_message("hola")

    assert _modelos_apuntados(base) == [(resultado.sirius_message.id, "qwen-x")]


def test_una_respuesta_fallida_no_apunta_modelo(tmp_path: Path) -> None:
    base, enviar = _sirius(tmp_path, _ModeloQueGraba(falla=True))

    enviar.send_message("hola")

    assert _modelos_apuntados(base) == []


def test_el_recordatorio_va_despues_de_las_instrucciones_de_model_studio(tmp_path: Path) -> None:
    modelo = _ModeloQueGraba()
    _, enviar = _sirius(tmp_path, modelo)

    enviar.send_message("hola", extra_instructions="Respuestas breves: estamos grabando.")

    [instrucciones] = modelo.instrucciones
    assert instrucciones.rstrip().endswith(ROBOT_SEED_REMINDER)
    assert instrucciones.index("Respuestas breves") < instrucciones.index(ROBOT_SEED_REMINDER)


def test_ponte_serio_vacila_solo_al_entrar(tmp_path: Path) -> None:
    modelo = _ModeloQueGraba()
    _, enviar = _sirius(tmp_path, modelo)

    enviar.send_message("Ponte serio, que tengo que decidir algo.")
    enviar.send_message("Hago veinte mil kilómetros al año.")

    entrando, siguiendo = modelo.instrucciones
    serio = MODE_INSTRUCTIONS[ConversationMode.SERIO]
    assert serio in entrando and ENTERING_SERIOUS_MODE in entrando
    assert serio in siguiendo and ENTERING_SERIOUS_MODE not in siguiendo


def test_lo_ya_resumido_sale_de_los_mensajes_recientes_aunque_quepa(tmp_path: Path) -> None:
    modelo = _ModeloQueGraba()
    base, enviar = _sirius(tmp_path, modelo)
    for n in range(1, 4):
        enviar.send_message(f"Mensaje número {n} del propietario.")
    conversacion = build_sqlite_conversation_repository(base).get_or_create_main_conversation()
    # Resumido hasta el segundo turno: el primer mensaje y su respuesta, y el segundo y la suya.
    build_sqlite_robot_conversation_repository(base).add(conversacion.id, 4, "RESUMEN CORTO")

    enviar.send_message("Mensaje número 4 del propietario.")

    ultima = modelo.instrucciones[-1]
    assert "# Resumen de la charla\nRESUMEN CORTO" in ultima
    assert "Mensaje número 1 del propietario." not in ultima
    assert "Mensaje número 2 del propietario." not in ultima
    assert "Mensaje número 3 del propietario." in ultima
