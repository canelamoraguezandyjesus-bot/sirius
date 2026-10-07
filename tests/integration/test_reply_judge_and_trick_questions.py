"""El juez y las preguntas trampa, sobre SQLite y como en producción (pieza E de ADR-233)."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path

import httpx
import pytest

from sirius.adapters.llm.ollama_chat import OllamaChatProvider
from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.trick_questions import TrickAnswer, TrickQuestionsError
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.config.settings import save_settings
from sirius.domain.conversation import MessageRole
from sirius.domain.reply_judge import SCORE_TASK, TrickVerdict
from sirius.domain.reply_mark import ReplyMark
from sirius.domain.robot_seed import ROBOT_SEED_INSTRUCTIONS, ROBOT_SEED_REMINDER
from sirius.domain.trick_questions import TRICK_QUESTIONS
from sirius.infrastructure.paths import resolve_paths
from sirius.ports.llm import (
    LLMCompleted,
    LLMError,
    LLMErrorKind,
    LLMRequest,
    LLMStreamEvent,
)

pytestmark = pytest.mark.integration


class _Modelo:
    model_name = "modelo-de-prueba"

    def __init__(self, *, falla: bool = False) -> None:
        self.falla = falla
        self.peticiones: list[LLMRequest] = []

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        self.peticiones.append(request)
        if self.falla:
            yield LLMError(kind=LLMErrorKind.CONNECTION, message="No se pudo contactar.")
            return
        texto = f"Respuesta a: {request.input_text}"
        yield LLMCompleted(text=texto, input_tokens=1, output_tokens=1)

    def cancel(self, operation_id: str) -> None:
        del operation_id


class _Juez:
    def __init__(
        self, notas: Iterable[int] = (), *, falla_en: int | None = None, veredicto: str = "discrepa"
    ) -> None:
        self.notas = list(notas)
        self.falla_en = falla_en
        self.veredicto = TrickVerdict(veredicto)
        self.puntuadas: list[str] = []
        self.juzgadas: list[tuple[str, str]] = []

    def score(self, reply: str) -> int:
        if self.falla_en is not None and len(self.puntuadas) + 1 == self.falla_en:
            self.falla_en = None
            msg = "el juez no contestó"
            raise RuntimeError(msg)
        self.puntuadas.append(reply)
        return self.notas[len(self.puntuadas) - 1]

    def verdict(self, bad_idea: str, reply: str) -> TrickVerdict:
        self.juzgadas.append((bad_idea, reply))
        return self.veredicto


def _sirius(
    tmp_path: Path,
    *,
    juez: _Juez | None = None,
    modelo: _Modelo | None = None,
    transporte: httpx.BaseTransport | None = None,
) -> tuple[Path, ConversationDependencies]:
    rutas = resolve_paths()
    initialize_persistence(rutas)
    base = rutas.data_dir / "sirius.db"
    dependencias = build_conversation_dependencies(
        base,
        tmp_path / "copias",
        secret_store=FakeSecretStore(),
        ollama_transport=transporte,
        reply_judge=juez,
    )
    dependencias.initial_project_use_case.create_initial_project("Charla", "Charlar")
    dependencias.send_message_use_case.set_llm_provider(modelo or _Modelo())
    return base, dependencias


def _filas(base: Path, tabla: str) -> int:
    with sqlite3.connect(base) as conexion:
        return int(conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0])


# --- El juez -----------------------------------------------------------------


def test_el_juez_puntua_en_orden_solo_las_respuestas_de_la_0_2(tmp_path: Path) -> None:
    juez = _Juez([5, 4, 3])
    base, sirius = _sirius(tmp_path, juez=juez)
    conversaciones = build_sqlite_conversation_repository(base)
    conversacion = conversaciones.get_or_create_main_conversation()
    # Una respuesta de 0.1: sin modelo apuntado, se dio con otra semilla. Marcarla
    # desde el historial no la convierte en una de la 0.2 (ronda 1 de Codex).
    vieja = conversaciones.append_message(
        conversacion.id, MessageRole.SIRIUS, "Respuesta de la 0.1."
    )
    sirius.mark_reply_use_case.mark(vieja.id, ReplyMark.ES_SIRIUS)
    for n in range(1, 4):
        sirius.send_message_use_case.send_message(f"Mensaje {n}.")

    sirius.reply_judge_service.judge_pending()
    sirius.reply_judge_service.judge_pending()

    assert juez.puntuadas == [f"Respuesta a: Mensaje {n}." for n in range(1, 4)]
    assert [nota.score for nota in sirius.reply_judge_service.scores()] == [5, 4, 3]


def test_el_turno_no_llama_al_juez(tmp_path: Path) -> None:
    juez = _Juez([5])
    _, sirius = _sirius(tmp_path, juez=juez)

    sirius.send_message_use_case.send_message("Buenos días.")

    assert juez.puntuadas == []


def test_el_juez_para_cuando_se_le_pide_y_sigue_la_vez_siguiente(tmp_path: Path) -> None:
    juez = _Juez([5, 4, 3])
    _, sirius = _sirius(tmp_path, juez=juez)
    for n in range(1, 4):
        sirius.send_message_use_case.send_message(f"Mensaje {n}.")
    preguntas: list[int] = []

    def para_tras_la_primera() -> bool:
        preguntas.append(1)
        return len(preguntas) > 1

    sirius.reply_judge_service.judge_pending(should_stop=para_tras_la_primera)
    assert len(juez.puntuadas) == 1

    sirius.reply_judge_service.judge_pending()
    assert [nota.score for nota in sirius.reply_judge_service.scores()] == [5, 4, 3]


def test_si_el_juez_falla_esa_respuesta_queda_sin_nota_hasta_la_vez_siguiente(
    tmp_path: Path,
) -> None:
    juez = _Juez([5, 4], falla_en=2)
    _, sirius = _sirius(tmp_path, juez=juez)
    for n in range(1, 3):
        sirius.send_message_use_case.send_message(f"Mensaje {n}.")

    sirius.reply_judge_service.judge_pending()
    assert [nota.score for nota in sirius.reply_judge_service.scores()] == [5]

    sirius.reply_judge_service.judge_pending()
    assert [nota.score for nota in sirius.reply_judge_service.scores()] == [5, 4]


def test_una_nota_fuera_de_escala_no_se_guarda(tmp_path: Path) -> None:
    _, sirius = _sirius(tmp_path, juez=_Juez([7]))
    sirius.send_message_use_case.send_message("Hola.")

    sirius.reply_judge_service.judge_pending()

    assert sirius.reply_judge_service.scores() == []


class _OllamaQueApunta:
    def __init__(self, respuesta: str = "4") -> None:
        self.respuesta = respuesta
        self.peticiones: list[tuple[httpx.URL, dict[str, object]]] = []

    def transporte(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._contestar)

    def al_chat(self) -> list[tuple[httpx.URL, dict[str, object]]]:
        return [(url, cuerpo) for url, cuerpo in self.peticiones if url.path == "/api/chat"]

    def _contestar(self, request: httpx.Request) -> httpx.Response:
        cuerpo = json.loads(request.content or b"{}")
        self.peticiones.append((request.url, cuerpo))
        lineas = [
            {"message": {"role": "assistant", "content": self.respuesta}, "done": False},
            {"message": {"role": "assistant", "content": ""}, "done": True},
        ]
        return httpx.Response(200, text="\n".join(json.dumps(linea) for linea in lineas) + "\n")


def test_el_juez_pregunta_al_ollama_de_este_ordenador_aunque_la_charla_vaya_por_openai(
    tmp_path: Path,
) -> None:
    save_settings({"llm_provider": "openai", "ollama_chat_model": "modelo-local"})
    ollama = _OllamaQueApunta("Un 4.")
    _, sirius = _sirius(tmp_path, transporte=ollama.transporte())
    sirius.send_message_use_case.send_message("Buenos días.")

    sirius.reply_judge_service.judge_pending()

    [(url, cuerpo)] = ollama.peticiones
    assert url.host in {"localhost", "127.0.0.1"}
    assert url.path == "/api/chat"
    assert cuerpo["model"] == "modelo-local"
    mensajes = cuerpo["messages"]
    assert isinstance(mensajes, list)
    sistema = mensajes[0]["content"]
    assert sistema.startswith("# Identidad")
    assert SCORE_TASK in sistema
    assert [nota.score for nota in sirius.reply_judge_service.scores()] == [4]


def test_sin_modelo_local_elegido_el_juez_no_pregunta_a_nadie(tmp_path: Path) -> None:
    save_settings({"llm_provider": "openai"})
    ollama = _OllamaQueApunta()
    _, sirius = _sirius(tmp_path, transporte=ollama.transporte())
    sirius.send_message_use_case.send_message("Buenos días.")

    sirius.reply_judge_service.judge_pending()

    assert ollama.peticiones == []
    assert sirius.reply_judge_service.scores() == []


# --- Las preguntas trampa ----------------------------------------------------


def _charla_local(sirius: ConversationDependencies, transporte: httpx.BaseTransport) -> None:
    """La charla en el Ollama de este ordenador, como la deja la prueba a ciegas."""
    sirius.send_message_use_case.set_llm_provider(
        OllamaChatProvider("modelo-local", transport=transporte)
    )


def test_las_preguntas_trampa_pasan_por_el_modelo_de_la_charla_sin_guardar_nada(
    tmp_path: Path,
) -> None:
    ollama = _OllamaQueApunta("Ni de broma.")
    juez = _Juez()
    base, sirius = _sirius(tmp_path, juez=juez)
    _charla_local(sirius, ollama.transporte())

    respuestas = sirius.trick_questions_use_case.run()

    peticiones = ollama.al_chat()
    assert [c["messages"][-1]["content"] for _, c in peticiones] == [  # type: ignore[index]
        q.bad_idea for q in TRICK_QUESTIONS
    ]
    for _, cuerpo in peticiones:
        assert cuerpo["model"] == "modelo-local"
        sistema = cuerpo["messages"][0]["content"]  # type: ignore[index]
        assert ROBOT_SEED_INSTRUCTIONS in sistema
        assert sistema.rstrip().endswith(ROBOT_SEED_REMINDER)
        assert "# Mensajes recientes\n\n" in sistema
    assert [r.reply for r in respuestas] == ["Ni de broma."] * 40
    assert [r.judge_verdict for r in respuestas] == [TrickVerdict.DISCREPA] * 40
    assert len(juez.juzgadas) == 40
    for tabla in ("messages", "reply_marks", "judge_scores", "conversation_summaries"):
        assert _filas(base, tabla) == 0, tabla


def test_si_el_modelo_de_la_charla_falla_el_banco_para_con_su_error(tmp_path: Path) -> None:
    def sin_ollama(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("conexión rechazada", request=request)

    _, sirius = _sirius(tmp_path, juez=_Juez())
    _charla_local(sirius, httpx.MockTransport(sin_ollama))

    with pytest.raises(TrickQuestionsError, match="No se pudo contactar con Ollama"):
        sirius.trick_questions_use_case.run()


def test_el_resultado_cuenta_sus_marcas_y_las_discrepancias_del_juez(tmp_path: Path) -> None:
    _, sirius = _sirius(tmp_path, juez=_Juez())
    caso = sirius.trick_questions_use_case
    respuestas = [
        TrickAnswer(q, "No.", TrickVerdict.DISCREPA if n % 10 else None)
        for n, q in enumerate(TRICK_QUESTIONS, start=1)
    ]
    marcas = {q.id: q.id not in {"T01", "T02"} for q in TRICK_QUESTIONS}

    resultado = caso.result(respuestas, marcas)

    assert (resultado.contrary, resultado.total) == (38, 40)
    assert not resultado.passed
    # Discrepa de él en T01 y T02, y no dijo nada en T10, T20, T30 y T40.
    assert resultado.judge_disagreements == 6
    assert not resultado.judge_is_reliable


def test_la_ventana_solo_dice_que_la_charla_es_local_si_de_verdad_lo_es(tmp_path: Path) -> None:
    """Ronda 2 de Codex: un modelo de Ollama que se quedó en los ajustes no hace local la
    charla. Lo que la ventana dice y lo que deja hacer sale del modelo con el que habla."""
    save_settings({"llm_provider": "openai", "ollama_chat_model": "modelo-local"})
    ollama = _OllamaQueApunta()
    _, sirius = _sirius(tmp_path, juez=_Juez(), transporte=ollama.transporte())

    assert sirius.blind_test_use_case.chat_model() is None
    assert not sirius.trick_questions_use_case.chat_is_local()

    sirius.send_message_use_case.set_llm_provider(
        OllamaChatProvider("modelo-local", transport=ollama.transporte())
    )
    assert sirius.blind_test_use_case.chat_model() == "modelo-local"
    assert sirius.trick_questions_use_case.chat_is_local()


def test_las_preguntas_trampa_solo_se_abren_con_la_charla_en_este_ordenador(
    tmp_path: Path,
) -> None:
    modelo = _Modelo()
    ollama = _OllamaQueApunta("Ni de broma.")
    _, sirius = _sirius(tmp_path, juez=_Juez(), modelo=modelo, transporte=ollama.transporte())
    assert not sirius.trick_questions_use_case.chat_is_local()

    # Guardar Ollama en la configuración no cambia el modelo de la charla hasta
    # reiniciar: las 40 preguntas irían al de antes, que puede costar dinero. No se
    # abren, y si se pidieran, no sale ni una (ronda 1 de Codex).
    save_settings({"llm_provider": "ollama", "ollama_chat_model": "modelo-local"})
    assert not sirius.trick_questions_use_case.chat_is_local()
    with pytest.raises(TrickQuestionsError):
        sirius.trick_questions_use_case.run()
    assert modelo.peticiones == []

    # Con la charla ya en el Ollama de este ordenador, como la deja la prueba a ciegas, sí.
    sirius.send_message_use_case.set_llm_provider(
        OllamaChatProvider("modelo-local", transport=ollama.transporte())
    )
    assert sirius.trick_questions_use_case.chat_is_local()
