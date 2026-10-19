"""Los gestos en la charla, con Sirius montado de verdad (pieza C de la 0.4, ADR-261).

El modelo escribe a trozos, como Ollama, y una etiqueta puede llegar partida entre dos.
Lo que llega a quien enseña y dice la respuesta va sin etiquetas, cada gesto de la lista
en su sitio, y lo que se guarda tampoco las lleva: ni la respuesta acabada ni la que se
quedó a medias.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.domain.conversation import MessageStatus
from sirius.domain.gestures import gestures_line
from sirius.infrastructure.paths import resolve_paths
from sirius.ports.llm import (
    LLMCompleted,
    LLMError,
    LLMErrorKind,
    LLMRequest,
    LLMStreamEvent,
    LLMTextDelta,
)

pytestmark = pytest.mark.integration


@dataclass
class _Modelo:
    """Contesta a trozos lo que le digan; con ``falla``, se cae tras el último."""

    trozos: list[str] = field(default_factory=list)
    falla: bool = False
    model_name: str = "a-trozos"
    peticiones: list[LLMRequest] = field(default_factory=list)

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterator[LLMStreamEvent]:
        self.peticiones.append(request)
        for trozo in self.trozos:
            yield LLMTextDelta(trozo)
        escrito = "".join(self.trozos)
        if self.falla:
            yield LLMError(LLMErrorKind.CONNECTION, "Ollama se ha caído.", escrito)
            return
        yield LLMCompleted(text=escrito, input_tokens=1, output_tokens=len(escrito))

    def cancel(self, operation_id: str) -> None:
        del operation_id


@dataclass
class _Huellas:
    model_name: str = "huellas"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[float(len(texto)), 1.0] for texto in texts]


@pytest.fixture
def sirius(tmp_path: Path) -> Iterator[tuple[ConversationDependencies, _Modelo]]:
    rutas = resolve_paths(tmp_path / "datos")
    initialize_persistence(rutas)
    deps = build_conversation_dependencies(
        rutas.data_dir / "sirius.db",
        rutas.backups_dir,
        secret_store=FakeSecretStore(),
        text_embedder=_Huellas(),
    )
    modelo = _Modelo()
    deps.send_message_use_case.set_llm_provider(modelo)
    if not deps.initial_project_use_case.is_configured():
        deps.initial_project_use_case.create_initial_project("Charla", "Charlar")
    yield deps, modelo
    deps.close_database_connections()


def test_una_etiqueta_partida_entre_trozos_ni_se_ve_ni_se_guarda_y_su_gesto_va_en_su_sitio(
    sirius: tuple[ConversationDependencies, _Modelo],
) -> None:
    deps, modelo = sirius
    modelo.trozos = ["Hombre, [ceja", "_arriba] eso habrá ", "que verlo. [bai", "lar]"]
    lo_que_llega: list[tuple[str, str]] = []

    resultado = deps.send_message_use_case.send_message(
        "Me voy a comprar un barco.",
        on_delta=lambda texto: lo_que_llega.append(("texto", texto)),
        on_gesture=lambda gesto: lo_que_llega.append(("gesto", gesto)),
    )

    escrito = "".join(texto for que, texto in lo_que_llega if que == "texto")
    assert escrito == "Hombre, eso habrá que verlo."
    assert [texto for que, texto in lo_que_llega if que == "gesto"] == ["ceja_arriba"]
    hasta_el_gesto = lo_que_llega.index(("gesto", "ceja_arriba"))
    assert "".join(t for _, t in lo_que_llega[:hasta_el_gesto]) == "Hombre, "
    assert resultado.outcome is MessageStatus.COMPLETED
    assert resultado.sirius_message.content == "Hombre, eso habrá que verlo."

    deps.send_message_use_case.send_message("¿Y qué más?")
    leido = modelo.peticiones[-1].instructions
    assert "Hombre, eso habrá que verlo." in leido
    assert "[ceja" not in leido.replace(gestures_line(), "")


def test_la_charla_le_dice_al_modelo_que_gestos_tiene(
    sirius: tuple[ConversationDependencies, _Modelo],
) -> None:
    deps, modelo = sirius
    modelo.trozos = ["Vale."]

    deps.send_message_use_case.send_message("Buenos días.")

    [peticion] = modelo.peticiones
    assert gestures_line() in peticion.instructions


def test_una_respuesta_que_se_cae_no_guarda_la_etiqueta_que_dejo_a_medias(
    sirius: tuple[ConversationDependencies, _Modelo],
) -> None:
    deps, modelo = sirius
    modelo.trozos = ["Vale, ", "[ceja_arr"]
    modelo.falla = True
    gestos: list[str] = []

    resultado = deps.send_message_use_case.send_message("Hola.", on_gesture=gestos.append)

    assert resultado.outcome is MessageStatus.FAILED
    assert resultado.sirius_message.content == "Vale, "
    assert gestos == []


def test_un_gesto_al_final_de_la_respuesta_tambien_llega_cuando_acaba(
    sirius: tuple[ConversationDependencies, _Modelo],
) -> None:
    """Lo último que escribe el modelo espera a ver qué sigue: una etiqueta al final puede
    ser el principio de un enlace. Al acabar la respuesta, llega."""
    deps, modelo = sirius
    modelo.trozos = ["Claro.", " [gui", "no]"]
    lo_que_llega: list[tuple[str, str]] = []

    deps.send_message_use_case.send_message(
        "¿Me guiñas un ojo?",
        on_delta=lambda texto: lo_que_llega.append(("texto", texto)),
        on_gesture=lambda gesto: lo_que_llega.append(("gesto", gesto)),
    )

    assert lo_que_llega == [("texto", "Claro."), ("gesto", "guino")]
