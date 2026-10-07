"""Las huellas de los recuerdos desde la ventana (pieza F de ADR-233, ADR-238).

La ventana de verdad, montada como al arrancar, con un modelo de huellas de
mentira: calcula las que faltan al abrirse y al guardar un recuerdo, y para
mientras dura un turno.
"""

from __future__ import annotations

import threading
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import pytest
from pytestqt.qtbot import QtBot

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.infrastructure.paths import resolve_paths
from sirius.main import _build_main_window
from sirius.ports.llm import LLMCompleted, LLMRequest, LLMStreamEvent

pytestmark = pytest.mark.gui


class _Huellas:
    """Una huella por frase. Con ``espera``, cada llamada se queda parada hasta que la suelten."""

    model_name = "huellas-de-prueba"

    def __init__(self) -> None:
        self.pedidas: list[str] = []
        self.espera: threading.Event | None = None
        self.parada = threading.Event()

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if self.espera is not None:
            self.parada.set()
            self.espera.wait(timeout=5)
        self.pedidas.extend(texts)
        return [[1.0, float(len(texto))] for texto in texts]


class _Modelo:
    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        yield LLMCompleted(text="Hecho.", input_tokens=1, output_tokens=1)

    def cancel(self, operation_id: str) -> None:
        del operation_id


def _sirius(tmp_path: Path, huellas: _Huellas) -> ConversationDependencies:
    rutas = resolve_paths()
    initialize_persistence(rutas)
    dependencias = build_conversation_dependencies(
        rutas.data_dir / "sirius.db",
        tmp_path / "copias",
        secret_store=FakeSecretStore(),
        text_embedder=huellas,
    )
    dependencias.initial_project_use_case.create_initial_project("Charla", "Charlar")
    dependencias.send_message_use_case.set_llm_provider(_Modelo())
    return dependencias


def _ventana(qtbot: QtBot, dependencias: ConversationDependencies) -> Any:
    ventana = _build_main_window(dependencias, [])
    qtbot.addWidget(ventana)
    qtbot.waitUntil(lambda: not ventana.embedding_in_progress, timeout=5000)
    return ventana


def test_al_abrirse_la_ventana_calcula_las_huellas_que_faltan(qtbot: QtBot, tmp_path: Path) -> None:
    huellas = _Huellas()
    dependencias = _sirius(tmp_path, huellas)
    dependencias.save_manual_memory_use_case.save("Le pirra el cocido.")
    dependencias.save_manual_memory_use_case.save("Tiene una moto vieja.")

    _ventana(qtbot, dependencias)

    assert sorted(huellas.pedidas) == ["Le pirra el cocido.", "Tiene una moto vieja."]


def test_al_guardar_un_recuerdo_desde_la_ventana_se_calcula_su_huella(
    qtbot: QtBot, tmp_path: Path
) -> None:
    huellas = _Huellas()
    dependencias = _sirius(tmp_path, huellas)
    ventana = _ventana(qtbot, dependencias)
    panel = ventana.knowledge_widget
    panel._prompt_multiline = lambda title, label: "Su hermana Lucía es enfermera."

    panel.save_memory_button.click()

    # Al abrirse no faltaba ninguna: solo cargó el modelo.
    qtbot.waitUntil(
        lambda: huellas.pedidas == ["hola", "Su hermana Lucía es enfermera."], timeout=5000
    )
    qtbot.waitUntil(lambda: not ventana.embedding_in_progress, timeout=5000)


def test_mientras_dura_un_turno_las_huellas_paran_y_siguen_despues(
    qtbot: QtBot, tmp_path: Path
) -> None:
    huellas = _Huellas()
    dependencias = _sirius(tmp_path, huellas)
    for n in range(20):
        dependencias.save_manual_memory_use_case.save(f"Recuerdo número {n}.")
    huellas.espera = threading.Event()
    ventana = _build_main_window(dependencias, [])
    qtbot.addWidget(ventana)
    assert huellas.parada.wait(timeout=5)

    trabajador = ventana._active_embedding_worker
    assert trabajador is not None

    ventana.message_input.setText("Hola")
    ventana.send_button.click()
    assert trabajador._stop.is_set()
    huellas.espera.set()

    qtbot.waitUntil(lambda: ventana.send_button.isEnabled(), timeout=5000)
    qtbot.waitUntil(lambda: not ventana.embedding_in_progress, timeout=5000)
    # El primer grupo lo acabó; el resto lo calculó al acabar el turno. El turno pidió
    # la huella de su pregunta.
    assert "Hola" in huellas.pedidas
    recuerdos = sorted(texto for texto in huellas.pedidas if texto != "Hola")
    assert recuerdos == sorted(f"Recuerdo número {n}." for n in range(20))


def test_al_abrirse_sin_huellas_pendientes_carga_el_modelo_para_el_primer_turno(
    qtbot: QtBot, tmp_path: Path
) -> None:
    huellas = _Huellas()
    dependencias = _sirius(tmp_path, huellas)

    _ventana(qtbot, dependencias)

    assert huellas.pedidas == ["hola"]


def test_cerrar_la_ventana_no_deja_que_las_huellas_vuelvan_a_arrancar(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Con otra vuelta pendiente al cerrar, nada vuelve a arrancar: la ventana puede
    seguir viva tras un cambio de proyecto, con los mismos repositorios que la nueva
    (ronda 1 de Codex)."""
    from sirius.presentation import main_window
    from sirius.presentation.memory_embedding_worker import MemoryEmbeddingWorker

    huellas = _Huellas()
    dependencias = _sirius(tmp_path, huellas)
    dependencias.save_manual_memory_use_case.save("Le pirra el cocido.")
    huellas.espera = threading.Event()
    ventana = _build_main_window(dependencias, [])
    qtbot.addWidget(ventana)
    assert huellas.parada.wait(timeout=5)
    ventana._start_embedding()  # se guardó otro recuerdo mientras tanto: toca otra vuelta
    assert ventana._embed_again
    arrancados: list[MemoryEmbeddingWorker] = []

    class _Contado(MemoryEmbeddingWorker):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            arrancados.append(self)

    monkeypatch.setattr(main_window, "MemoryEmbeddingWorker", _Contado)

    ventana.close()
    huellas.espera.set()

    qtbot.waitUntil(lambda: not ventana.embedding_in_progress, timeout=5000)
    qtbot.wait(50)
    assert arrancados == []
    assert not ventana.embedding_in_progress
