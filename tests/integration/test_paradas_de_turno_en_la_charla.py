"""Las paradas de turno en la charla y en la voz de las órdenes, con Sirius montado de verdad.

Incidencia #700: las instrucciones llevan ejemplos y mensajes escritos por turnos, y un modelo
pequeño puede seguir escribiendo el del otro hasta su tope. Cada petición lleva como paradas
los comienzos de turno que hay en sus instrucciones, ni uno más ni uno menos.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.send_message import COMMAND_VOICE_TASK
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.domain.robot_seed import ROBOT_SEED_EXAMPLES, ROBOT_SEED_NAME
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

#: Cómo puede empezar un turno de los ejemplos de la semilla, y uno de los mensajes recientes.
_DE_LOS_EJEMPLOS = {f"\n{who}:" for who in {e.who for e in ROBOT_SEED_EXAMPLES} | {ROBOT_SEED_NAME}}
_DE_LOS_MENSAJES = {"\n[user]", "\n[sirius]"}


@dataclass
class _Modelo:
    model_name: str = "grabador"
    peticiones: list[LLMRequest] = field(default_factory=list)
    #: Si la próxima respuesta falla, como un Ollama que se cae a mitad.
    falla: bool = False

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterator[LLMStreamEvent]:
        self.peticiones.append(request)
        if self.falla:
            self.falla = False
            yield LLMError(kind=LLMErrorKind.CONNECTION, message="Ollama se ha caído.")
            return
        yield LLMTextDelta("Vale.")
        yield LLMCompleted(text="Vale.", input_tokens=1, output_tokens=1)

    def cancel(self, operation_id: str) -> None:
        del operation_id


@dataclass
class _Huellas:
    model_name: str = "huellas"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[float(len(texto)), 1.0] for texto in texts]


@dataclass
class _Sirius:
    deps: ConversationDependencies
    modelo: _Modelo

    def di(self, texto: str) -> None:
        self.deps.send_message_use_case.send_message(texto)

    def de_la_charla(self) -> list[LLMRequest]:
        return [p for p in self.modelo.peticiones if COMMAND_VOICE_TASK not in p.instructions]

    def de_las_ordenes(self) -> list[LLMRequest]:
        return [p for p in self.modelo.peticiones if COMMAND_VOICE_TASK in p.instructions]


@pytest.fixture
def sirius(tmp_path: Path) -> Iterator[_Sirius]:
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
    yield _Sirius(deps, modelo)
    deps.close_database_connections()


def _turnos_que_lee(peticion: LLMRequest) -> set[str]:
    """Los comienzos de turno que hay de verdad en sus instrucciones."""
    instrucciones = f"\n{peticion.instructions}"
    ejemplos = {turno for turno in _DE_LOS_EJEMPLOS if f"{turno} «" in instrucciones}
    mensajes = {turno for turno in _DE_LOS_MENSAJES if f"{turno} " in instrucciones}
    return ejemplos | mensajes


def test_cada_turno_de_la_charla_para_en_los_comienzos_de_turno_que_lee(
    sirius: _Sirius,
) -> None:
    sirius.di("Buenos días, Sirius.")
    sirius.di("Hoy me voy a pedir otra pizza.")

    primera, segunda = sirius.de_la_charla()
    assert set(primera.stop) == _turnos_que_lee(primera)
    assert f"\n{ROBOT_SEED_NAME}:" in primera.stop
    assert "\n[user]" not in primera.stop, "el primer turno aún no lleva mensajes recientes"
    assert set(segunda.stop) == _turnos_que_lee(segunda)
    assert {"\n[user]", "\n[sirius]"} <= set(segunda.stop)


def test_la_voz_de_una_orden_para_en_los_turnos_de_sus_ejemplos(sirius: _Sirius) -> None:
    sirius.di("La clave de la alarma es Zarzamora.")

    sirius.di("Olvida eso.")

    [voz] = sirius.de_las_ordenes()
    assert voz.stop
    assert set(voz.stop) == _turnos_que_lee(voz)


def test_con_mensajes_recientes_de_uno_solo_para_solo_en_los_suyos(sirius: _Sirius) -> None:
    """Una respuesta que falla no va a los mensajes recientes: la charla siguiente lleva
    solo los de él, y una parada «[sirius]» no empezaría ningún turno de lo que lee el
    modelo (ronda 1 de Codex sobre la PR #701)."""
    sirius.modelo.falla = True
    sirius.di("Buenos días, Sirius.")

    sirius.di("¿Me oyes ahora?")

    segunda = sirius.de_la_charla()[-1]
    assert "\n[user] Buenos días, Sirius." in f"\n{segunda.instructions}"
    assert "\n[sirius] " not in f"\n{segunda.instructions}"
    assert set(segunda.stop) == _turnos_que_lee(segunda)
    assert "\n[user]" in segunda.stop
    assert "\n[sirius]" not in segunda.stop
