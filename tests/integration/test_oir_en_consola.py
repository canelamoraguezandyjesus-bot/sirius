"""``sirius-oye`` con Sirius montado de verdad: cuenta cada turno de voz como la ventana
uno escrito, con lo guardado y no con lo oído (rondas 13 y 14 de Codex sobre la PR #687,
ADR-242). El micro, el detector y el transcriptor son de mentira; la charla, la memoria y
la base, las de verdad."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.local_listening import LocalListening
from sirius.application.memory_commands import FORGET_ABOUT_STORED
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.infrastructure.paths import resolve_paths
from sirius.listen_console import listen
from sirius.ports.embeddings import EmbeddingError
from sirius.ports.llm import (
    LLMCompleted,
    LLMError,
    LLMErrorKind,
    LLMRequest,
    LLMStreamEvent,
    LLMTextDelta,
)
from sirius.ports.local_voice import Captured, ListeningEngines, SpeakingEngines, TurnSignal
from sirius.presentation.error_messages import describe_error

pytestmark = pytest.mark.integration


class _Modelo:
    """Un modelo de este ordenador que contesta «Vale.», o que escribe un poco y falla."""

    runs_on_this_computer = True
    model_name = "de-aqui"

    def __init__(self) -> None:
        self.falla_a_medias = False
        self.se_rompe = False

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterator[LLMStreamEvent]:
        del request
        if self.se_rompe:
            yield LLMTextDelta("Ho")
            msg = "un fallo que no es del modelo: la base se cerró"
            raise RuntimeError(msg)
        if self.falla_a_medias:
            yield LLMTextDelta("Ho")
            yield LLMError(kind=LLMErrorKind.TIMEOUT, message="tarda", partial_text="Ho")
            return
        yield LLMTextDelta("Vale.")
        yield LLMCompleted(text="Vale.", input_tokens=1, output_tokens=1)

    def cancel(self, operation_id: str) -> None:
        del operation_id


class _SinHuellas:
    model_name = "sin-huellas"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        del texts
        raise EmbeddingError("sin huellas")


class _Micro:
    def __init__(self) -> None:
        self.trozos: list[str] = []

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def read(self) -> Captured[str] | None:
        return Captured(self.trozos.pop(0)) if self.trozos else None


class _Detector:
    def listen(self, chunk: str) -> TurnSignal:
        return TurnSignal.ENDED if chunk == "fin" else TurnSignal.VOICE

    def reset(self) -> None:
        pass


class _Transcriptor:
    def __init__(self) -> None:
        self.dira = ""

    def transcribe(self, chunks: Sequence[str]) -> str:
        del chunks
        return self.dira


class _Voz:
    """Apunta cada frase que Sirius dice en voz alta."""

    def __init__(self) -> None:
        self.frases: list[str] = []

    def say(self, text: str) -> str:
        self.frases.append(text)
        return text


class _Altavoz:
    playing = False
    latency = 0.0
    level = 0.0

    def __init__(self) -> None:
        #: Suena en el acto: todo lo que toma empieza a sonar.
        self.started = 0

    def play(self, sound: str) -> None:
        del sound
        self.started += 1

    def stop(self) -> None:
        pass

    def close(self) -> None:
        pass


class _TodoInstalado:
    install_command = "la orden de instalar"

    def missing(self) -> tuple[str, ...]:
        return ()


@dataclass
class _Sirius:
    deps: ConversationDependencies
    modelo: _Modelo
    micro: _Micro
    transcriptor: _Transcriptor
    voz: _Voz
    oido: LocalListening[str]
    codigo: int = 0

    def dice_por_voz(self, frase: str) -> list[str]:
        """Suena ``frase`` por el micro y devuelve lo que escribe ``sirius-oye``."""
        self.transcriptor.dira = frase
        self.micro.trozos = ["voz", "fin"]
        dicho: list[str] = []
        vueltas = iter([True, False])
        self.codigo = listen(
            self.oido,
            dicho.append,
            keep_going=lambda: next(vueltas),
            pause=lambda: None,
            history=self.deps.get_history_use_case.get_history,
        )
        return dicho[1:]


@pytest.fixture
def sirius(tmp_path: Path) -> Iterator[_Sirius]:
    rutas = resolve_paths(tmp_path / "datos")
    initialize_persistence(rutas)
    deps = build_conversation_dependencies(
        rutas.data_dir / "sirius.db",
        rutas.backups_dir,
        secret_store=FakeSecretStore(),
        text_embedder=_SinHuellas(),
    )
    modelo = _Modelo()
    deps.send_message_use_case.set_llm_provider(modelo)
    if not deps.initial_project_use_case.is_configured():
        deps.initial_project_use_case.create_initial_project("Charla", "Charlar")
    micro, transcriptor, voz = _Micro(), _Transcriptor(), _Voz()
    oido: LocalListening[str] = LocalListening(
        chat=deps.send_message_use_case,
        installation=_TodoInstalado(),
        load_engines=lambda: ListeningEngines(micro, _Detector(), transcriptor),
        load_speaking=lambda: SpeakingEngines(voz, _Altavoz()),
        memory_suggestions=deps.propose_memory_suggestion_use_case,
    )
    yield _Sirius(deps, modelo, micro, transcriptor, voz, oido)
    deps.close_database_connections()


def test_una_orden_de_olvido_por_voz_no_sale_por_la_consola(sirius: _Sirius) -> None:
    sirius.deps.send_message_use_case.send_message("Mi vecino Ramiro me tiene frito.")

    # Con su nombre, como hay que llamarle fuera de la charla (ADR-244).
    dicho = sirius.dice_por_voz("Sirius, olvida lo de mi vecino Ramiro.")

    assert dicho[0] == f"Tú: {FORGET_ABOUT_STORED}"
    assert dicho[1].startswith("Sirius: ")
    assert not any("Ramiro" in linea for linea in dicho)
    # Ni por el altavoz: dice la respuesta de la orden, que ya no lo nombra (ADR-243).
    assert sirius.voz.frases
    assert not any("Ramiro" in frase for frase in sirius.voz.frases)


def test_si_la_charla_falla_a_medias_la_consola_lo_ensena_como_la_ventana(
    sirius: _Sirius,
) -> None:
    sirius.modelo.falla_a_medias = True

    dicho = sirius.dice_por_voz("Hola, Sirius.")

    assert dicho[:2] == ["Tú: Hola, Sirius.", "Sirius: Ho (fallido)"]
    assert dicho[2].startswith(describe_error(LLMErrorKind.TIMEOUT) + " (ref: ")


def test_si_la_charla_se_rompe_la_consola_cuenta_lo_guardado_y_sale_sin_volcado(
    sirius: _Sirius,
) -> None:
    # Ronda 15 de Codex sobre la PR #687: lo suyo quedó guardado antes de romperse, y es
    # lo que se cuenta, como la ventana al releer la charla; después, su aviso y error.
    sirius.deps.send_message_use_case.send_message("Lo de antes.")
    sirius.modelo.se_rompe = True

    dicho = sirius.dice_por_voz("Hola, Sirius.")

    assert sirius.codigo == 1
    assert dicho[0] == "Tú: Hola, Sirius."
    assert dicho[1].startswith(describe_error(None) + " (ref: ")
    assert len(dicho) == 2
    assert not sirius.oido.listening
