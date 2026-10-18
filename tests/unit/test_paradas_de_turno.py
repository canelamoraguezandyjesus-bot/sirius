"""Las paradas de turno: que el modelo no siga el diálogo de sus instrucciones (incidencia #700).

Las instrucciones llevan ejemplos escritos por turnos, «Él: «…»» y «Sirius: «…»». El
18-10-2026, en la prueba a ciegas, el propietario vio a los tres modelos quedarse
escribiendo respuesta tras respuesta: un modelo pequeño sigue el diálogo, se inventa lo que
dice el otro y se lo contesta, hasta su tope. Cada petición lleva sus comienzos de turno
como paradas, y Ollama deja de escribir en cuanto el modelo empieza uno.
"""

from __future__ import annotations

import ast
import json
import random
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from sirius.adapters.llm.ollama_chat import OllamaChatProvider
from sirius.application.blind_test import BlindTestUseCase
from sirius.application.dream import LLMFactExtractor
from sirius.application.reply_judge import LLMReplyJudge
from sirius.application.robot_conversation import LLMConversationSummarizer
from sirius.application.send_message import recent_message_turns, render_recent_message
from sirius.application.trick_questions import TrickQuestionsUseCase
from sirius.domain.conversation import Message, MessageRole
from sirius.domain.conversation_summary import said_turns, summary_input
from sirius.domain.identity import Identity, IdentityVersion, SeedExample
from sirius.domain.reply_judge import TrickVerdict
from sirius.domain.robot_seed import example_turns, render_examples
from sirius.domain.trick_questions import TRICK_QUESTIONS
from sirius.ports.llm import LLMCompleted, LLMRequest, LLMStreamEvent

_EJEMPLOS = (
    SeedExample("Él", "Buenos días, Sirius.", "Buenos días, jefe."),
    SeedExample("Una amiga suya", "Hola, soy Marta.", "¿Qué tal, Marta?"),
    SeedExample("Él", "¿Qué estás haciendo?", "Pensar en ti, fíjate."),
)
_TURNOS = {"\nÉl:", "\nUna amiga suya:", "\nSirius:"}


def test_los_turnos_de_los_ejemplos_son_quien_habla_y_sirius_sin_repetir() -> None:
    assert example_turns(_EJEMPLOS) == ("\nÉl:", "\nUna amiga suya:", "\nSirius:")


def test_sin_ejemplos_no_hay_paradas() -> None:
    assert example_turns(()) == ()


def test_cada_parada_es_como_empieza_un_turno_en_lo_que_lee_el_modelo() -> None:
    """Si cambia cómo se escriben los ejemplos, las paradas tienen que cambiar con ellos."""
    escrito = f"\n{render_examples(_EJEMPLOS)}"

    for parada in example_turns(_EJEMPLOS):
        assert f"{parada} «" in escrito, parada


# --- Ollama -------------------------------------------------------------------------


def _lineas(texto: str) -> str:
    lineas = [
        {"message": {"role": "assistant", "content": texto}, "done": False},
        {"message": {"role": "assistant", "content": ""}, "done": True},
    ]
    return "\n".join(json.dumps(linea) for linea in lineas) + "\n"


def _cuerpo(peticion: LLMRequest) -> dict[str, Any]:
    cuerpos: list[dict[str, Any]] = []

    def contestar(request: httpx.Request) -> httpx.Response:
        cuerpos.append(json.loads(request.content))
        return httpx.Response(200, text=_lineas("Vale."))

    proveedor = OllamaChatProvider("modelo-de-prueba", transport=httpx.MockTransport(contestar))
    list(proveedor.stream_response(peticion))
    [cuerpo] = cuerpos
    return cuerpo


def test_ollama_recibe_las_paradas_de_la_peticion() -> None:
    peticion = LLMRequest(
        operation_id="op-1",
        instructions="Eres Sirius.",
        input_text="Hola",
        stop=("\nÉl:", "\nSirius:"),
    )

    assert _cuerpo(peticion)["options"]["stop"] == ["\nÉl:", "\nSirius:"]


def test_una_peticion_sin_paradas_no_pide_ninguna() -> None:
    peticion = LLMRequest(operation_id="op-1", instructions="Eres Sirius.", input_text="Hola")

    assert "stop" not in _cuerpo(peticion)["options"]


# --- La prueba a ciegas y las preguntas trampa ---------------------------------------


class _Identidades:
    """Una identidad con ejemplos de dos que hablan."""

    def _identidad(self) -> Identity:
        version = IdentityVersion(
            id=1,
            identity_id=1,
            version=3,
            name="Sirius",
            description="El software del robot.",
            personality_instructions="Gracioso ante todo.",
            created_at=datetime(2026, 10, 18, tzinfo=UTC),
            examples=_EJEMPLOS,
        )
        return Identity(id=1, current_version=version, created_at=version.created_at)

    def get_or_create_current_identity(self) -> Identity:
        return self._identidad()

    def get_current_identity(self) -> Identity:
        return self._identidad()


class _Modelo:
    def __init__(self) -> None:
        self.peticiones: list[LLMRequest] = []

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterator[LLMStreamEvent]:
        self.peticiones.append(request)
        yield LLMCompleted(text="Ni de broma.", input_tokens=1, output_tokens=1)

    def cancel(self, operation_id: str) -> None:
        del operation_id


def _turnos_que_lee(peticion: LLMRequest) -> set[str]:
    """Los comienzos de turno que hay de verdad en sus instrucciones."""
    return {turno for turno in _TURNOS if f"{turno} «" in f"\n{peticion.instructions}"}


def test_cada_respuesta_de_la_prueba_a_ciegas_para_en_los_turnos_de_sus_ejemplos() -> None:
    modelos = {"uno": _Modelo(), "dos": _Modelo()}
    caso = BlindTestUseCase(
        identity_repository=_Identidades(),  # type: ignore[arg-type]
        provider_for=lambda nombre: modelos[nombre],
        list_models=lambda: tuple(sorted(modelos)),
        model_capabilities=lambda nombre: ("completion",),
        choose_model=lambda nombre: None,
        current_model=lambda: None,
        rng=random.Random(7),
    )

    caso.prepare(["uno", "dos"])

    for modelo in modelos.values():
        assert modelo.peticiones
        for peticion in modelo.peticiones:
            assert set(peticion.stop) == _turnos_que_lee(peticion) == _TURNOS


class _Juez:
    def verdict(self, bad_idea: str, reply: str, **_: object) -> TrickVerdict:
        del bad_idea, reply
        return TrickVerdict.DISCREPA

    def cancel_verdicts(self) -> None:
        pass


def test_cada_respuesta_a_una_pregunta_trampa_para_en_los_turnos_de_sus_ejemplos() -> None:
    modelo = _Modelo()
    caso = TrickQuestionsUseCase(
        _Identidades(),  # type: ignore[arg-type]
        local_chat_provider=lambda: modelo,
        judge=_Juez(),  # type: ignore[arg-type]
    )

    caso.run()

    assert len(modelo.peticiones) == len(TRICK_QUESTIONS)
    for peticion in modelo.peticiones:
        assert set(peticion.stop) == _turnos_que_lee(peticion) == _TURNOS


# --- Ronda 1 de Codex sobre la PR #701: el juez, los roles que están, y el resumen y el
# sueño, que reciben la charla escrita por turnos ---------------------------------------


class _ModeloQueJuzga(_Modelo):
    """Contesta lo que vale para una nota y para un veredicto a la vez: un 4 y «discrepa»."""

    def stream_response(self, request: LLMRequest) -> Iterator[LLMStreamEvent]:
        self.peticiones.append(request)
        yield LLMCompleted(text="4, discrepa", input_tokens=1, output_tokens=1)


def test_el_juez_para_en_los_turnos_de_los_ejemplos_que_ve_enteros() -> None:
    modelo = _ModeloQueJuzga()
    juez = LLMReplyJudge(_Identidades(), lambda: modelo)  # type: ignore[arg-type]

    juez.score("Buenos días, jefe.")
    juez.verdict("Me voy a comprar un barco.", "Ni de broma.")

    assert len(modelo.peticiones) == 2
    for peticion in modelo.peticiones:
        assert set(peticion.stop) == _turnos_que_lee(peticion) == _TURNOS


def _mensaje(rol: MessageRole, texto: str) -> Message:
    return Message(1, 1, 1, rol, texto, datetime(2026, 10, 18, tzinfo=UTC))


def test_las_paradas_de_los_mensajes_recientes_son_solo_de_los_que_estan() -> None:
    suyo = _mensaje(MessageRole.USER, "Hola.")
    de_sirius = _mensaje(MessageRole.SIRIUS, "Hola, jefe.")

    assert recent_message_turns([]) == ()
    assert recent_message_turns([suyo, suyo]) == ("\n[user]",)
    assert recent_message_turns([de_sirius, suyo, de_sirius]) == ("\n[sirius]", "\n[user]")
    escrito = "\n" + "\n".join(render_recent_message(m) for m in (suyo, de_sirius))
    for parada in recent_message_turns([suyo, de_sirius]):
        assert f"{parada} " in escrito, "cada parada empieza un mensaje de lo que lee"


def test_lo_que_se_da_a_resumir_o_a_sonar_para_en_los_turnos_que_lleva() -> None:
    suyo = _mensaje(MessageRole.USER, "Me he comprado un barco.")
    de_sirius = _mensaje(MessageRole.SIRIUS, "¿Otro?")

    assert said_turns(summary_input(None, [suyo, de_sirius])) == ("\nÉl:", "\nSirius:")
    assert said_turns(summary_input("Habló de barcos.", [suyo])) == ("\nÉl:",)
    assert said_turns("Resumen anterior:\nHabló de barcos.") == ()


def test_el_resumen_y_los_hechos_del_sueno_paran_en_los_turnos_de_lo_que_reciben() -> None:
    modelo = _Modelo()
    charla = "Él: Me he comprado un barco.\nSirius: ¿Otro?"
    dia = "Él: Me he comprado un barco.\nÉl: Mañana lo estreno."

    LLMConversationSummarizer().summarize(charla, modelo)
    LLMFactExtractor().extract(dia, modelo)

    resumen, hechos = modelo.peticiones
    assert resumen.stop == ("\nÉl:", "\nSirius:")
    assert hechos.stop == ("\nÉl:",)


def _nombre(funcion: ast.expr) -> str:
    if isinstance(funcion, ast.Name):
        return funcion.id
    if isinstance(funcion, ast.Attribute):
        return funcion.attr
    return ""


def test_toda_peticion_al_modelo_dice_sus_paradas_aunque_sean_ninguna() -> None:
    """Olvidar las paradas de una petición nueva no puede pasar sin que se vea: cada
    ``LLMRequest`` del código las dice, aunque sea ``stop=()``. Si lleva diálogo, las
    pruebas de arriba miran que sean las suyas (ronda 1 de Codex sobre la PR #701)."""
    raiz = Path(__file__).resolve().parents[2] / "src"
    peticiones: list[str] = []
    sin_paradas: list[str] = []
    for fichero in sorted(raiz.rglob("*.py")):
        for nodo in ast.walk(ast.parse(fichero.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.Call) and _nombre(nodo.func) == "LLMRequest":
                donde = f"{fichero.relative_to(raiz).as_posix()}:{nodo.lineno}"
                peticiones.append(donde)
                if not any(clave.arg == "stop" for clave in nodo.keywords):
                    sin_paradas.append(donde)

    assert len(peticiones) >= 7, peticiones
    assert sin_paradas == []
