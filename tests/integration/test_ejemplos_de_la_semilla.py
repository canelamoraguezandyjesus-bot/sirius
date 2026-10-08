"""Los ejemplos de la semilla en cada turno, con Sirius montado de verdad (ADR-240)."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.domain.robot_seed import EXAMPLES_FRAME, ROBOT_SEED_EXAMPLES
from sirius.infrastructure.paths import resolve_paths
from sirius.ports.llm import LLMCompleted, LLMRequest, LLMStreamEvent, LLMTextDelta

pytestmark = pytest.mark.integration


@dataclass
class _Modelo:
    model_name: str = "grabador"
    peticiones: list[LLMRequest] = field(default_factory=list)

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterator[LLMStreamEvent]:
        self.peticiones.append(request)
        yield LLMTextDelta("Vale.")
        yield LLMCompleted(text="Vale.", input_tokens=1, output_tokens=1)

    def cancel(self, operation_id: str) -> None:
        del operation_id


@dataclass
class _Huellas:
    """Un modelo de huellas que apunta cada tanda que le piden."""

    model_name: str = "huellas"
    tandas: list[list[str]] = field(default_factory=list)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.tandas.append(list(texts))
        return [[float(len(texto)), 1.0] for texto in texts]


@dataclass
class _Sirius:
    deps: ConversationDependencies
    modelo: _Modelo
    huellas: _Huellas

    def di(self, texto: str) -> None:
        self.deps.send_message_use_case.send_message(texto)


@pytest.fixture
def sirius(tmp_path: Path) -> Iterator[_Sirius]:
    rutas = resolve_paths(tmp_path / "datos")
    initialize_persistence(rutas)
    huellas = _Huellas()
    deps = build_conversation_dependencies(
        rutas.data_dir / "sirius.db",
        rutas.backups_dir,
        secret_store=FakeSecretStore(),
        text_embedder=huellas,
    )
    modelo = _Modelo()
    deps.send_message_use_case.set_llm_provider(modelo)
    if not deps.initial_project_use_case.is_configured():
        deps.initial_project_use_case.create_initial_project("Charla", "Charlar")
    yield _Sirius(deps, modelo, huellas)
    deps.close_database_connections()


def _mostrados(peticion: LLMRequest) -> list[str]:
    return [
        e.said
        for e in ROBOT_SEED_EXAMPLES
        if f"{e.who}: «{e.said}»\nSirius: «{e.reply}»" in peticion.instructions
    ]


def test_cada_turno_pide_la_huella_de_su_mensaje_una_vez_y_las_de_los_ejemplos_solo_la_primera(
    sirius: _Sirius,
) -> None:
    """La búsqueda de recuerdos y los ejemplos usan la misma huella del mensaje, y las de los
    ejemplos no cambian: Ollama no hace el mismo trabajo dos veces en un turno."""
    sirius.di("Hola, ¿qué tal todo?")
    sirius.di("Hoy hace un día estupendo.")

    pedidas = [texto for tanda in sirius.huellas.tandas for texto in tanda]
    assert pedidas.count("Hola, ¿qué tal todo?") == 1
    assert pedidas.count("Hoy hace un día estupendo.") == 1
    ejemplos = [texto for texto in pedidas if texto in {e.said for e in ROBOT_SEED_EXAMPLES}]
    assert sorted(ejemplos) == sorted({e.said for e in ROBOT_SEED_EXAMPLES})


def test_cada_peticion_de_la_charla_lleva_tres_ejemplos_con_su_aviso(sirius: _Sirius) -> None:
    for frase in ("Buenos días, Sirius.", "¿Qué estás haciendo?", "Dime algo bonito."):
        sirius.di(frase)

    for peticion in sirius.modelo.peticiones:
        assert EXAMPLES_FRAME in peticion.instructions
        assert len(_mostrados(peticion)) == 3
