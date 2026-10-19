"""La edad, montada como en producción (pieza F de la 0.4, ADR-264): sin doble del
estimador, con una cámara y un detector de mentira. Sin el modelo de la edad, que en las
pruebas no está, la edad de quien se ve no se sabe, y la petición lleva la regla: ante la
duda, no insulta. Con el doble del estimador, lo miran las pruebas de aceptación."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from sirius import composition_root
from sirius.adapters.llm.fake import FakeLLMProvider
from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.age import care_block
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.infrastructure.local_sight_installation import face_recognition_dir
from sirius.infrastructure.paths import resolve_paths
from sirius.ports.age import AgeUnavailable
from sirius.ports.embeddings import EmbeddingError
from sirius.ports.llm import LLMRequest, LLMStreamEvent
from sirius.ports.local_sight import SeenFace, SightEngines

pytestmark = pytest.mark.integration


class _SinHuellas:
    model_name = "sin-huellas"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        del texts
        raise EmbeddingError("sin huellas")


class _Camara:
    def open(self) -> None:
        return None

    def read(self) -> str:
        return "fotograma"

    def close(self) -> None:
        return None


@dataclass
class _Detector:
    name: str = "mediapipe"
    caras: list[tuple[SeenFace[str], ...]] = field(default_factory=list)

    def detect(self, frame: str) -> tuple[SeenFace[str], ...]:
        del frame
        return self.caras.pop(0) if self.caras else ()


class _ModeloQueApunta(FakeLLMProvider):
    """Contesta como el de mentira y apunta cada petición."""

    def __init__(self) -> None:
        super().__init__()
        self.peticiones: list[LLMRequest] = []

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        self.peticiones.append(request)
        yield from super().stream_response(request)


def _monta(
    tmp_path: Path, detector: _Detector
) -> tuple[ConversationDependencies, _ModeloQueApunta]:
    rutas = resolve_paths()
    initialize_persistence(rutas)
    deps = build_conversation_dependencies(
        rutas.data_dir / "sirius.db",
        tmp_path / "copias",
        secret_store=FakeSecretStore(),
        text_embedder=_SinHuellas(),
        sight_engines=lambda: SightEngines(_Camara(), detector),
    )
    deps.initial_project_use_case.create_initial_project("Charla", "Charlar")
    modelo = _ModeloQueApunta()
    deps.send_message_use_case.set_llm_provider(modelo)
    return deps, modelo


def test_sin_el_modelo_de_la_edad_con_alguien_delante_lleva_la_regla_ante_la_duda(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    detector = _Detector(caras=[(SeenFace(0.5, False, False, "alguien"),)])
    deps, modelo = _monta(tmp_path, detector)

    with caplog.at_level(logging.INFO):
        assert deps.local_sight.start() == ""
        deps.local_sight.look()
        deps.send_message_use_case.send_message("hola")

    assert deps.local_sight.in_front_ages() == (None,)
    [peticion] = modelo.peticiones
    assert care_block() in peticion.instructions
    assert "No se puede estimar la edad: falta el modelo de la edad" in caplog.text


def test_lo_que_monta_sirius_sin_dobles_es_el_modelo_de_la_edad_con_los_de_insightface(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cargados: list[Path] = []

    def carga(carpeta: Path) -> None:
        cargados.append(carpeta)
        raise AgeUnavailable("de mentira")

    monkeypatch.setattr(composition_root, "load_age_estimator", carga)
    detector = _Detector(caras=[(SeenFace(0.5, False, False, "alguien"),)] * 2)
    deps, _ = _monta(tmp_path, detector)

    assert cargados == [], "montarlo no carga nada"
    deps.local_sight.start()
    deps.local_sight.look()
    deps.local_sight.look()

    assert cargados == [face_recognition_dir()], "una vez, donde lo deja la orden de instalar"


def test_sin_nadie_delante_o_sin_camara_no_la_lleva(tmp_path: Path) -> None:
    deps, modelo = _monta(tmp_path, _Detector(caras=[()]))

    deps.send_message_use_case.send_message("sin cámara")
    deps.local_sight.start()
    deps.local_sight.look()
    deps.send_message_use_case.send_message("sin nadie")

    assert [care_block() in p.instructions for p in modelo.peticiones] == [False, False]


def test_las_preguntas_trampa_y_la_prueba_a_ciegas_llevan_la_regla_con_la_misma_vista(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Ronda 2 de Codex sobre la PR #703: también escriben como Sirius, y se enseña.
    a_ciegas: list[_ModeloQueApunta] = []

    def ollama(modelo: str, **opciones: object) -> _ModeloQueApunta:
        del modelo, opciones
        nuevo = _ModeloQueApunta()
        a_ciegas.append(nuevo)
        return nuevo

    monkeypatch.setattr(composition_root, "OllamaChatProvider", ollama)
    monkeypatch.setattr(composition_root, "_local_chat", lambda proveedor: proveedor)
    detector = _Detector(caras=[(SeenFace(0.5, False, False, "alguien"),)])
    deps, modelo = _monta(tmp_path, detector)
    deps.local_sight.start()
    deps.local_sight.look()

    deps.trick_questions_use_case.run()
    deps.blind_test_use_case.prepare(["uno", "dos"])

    trampa = [p for p in modelo.peticiones if care_block() in p.instructions]
    assert len(trampa) == 40, "las 40 preguntas trampa, sin el modelo de la edad: ante la duda"
    assert len(a_ciegas) == 2
    assert all(care_block() in p.instructions for m in a_ciegas for p in m.peticiones)
    assert sum(len(m.peticiones) for m in a_ciegas) == 40
