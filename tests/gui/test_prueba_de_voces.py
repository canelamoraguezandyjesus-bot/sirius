"""La ventana de la prueba de voces (pieza F de ADR-241, ADR-246; PA-R03-10).

Sirius va montado de verdad, con un oído, cinco voces y sus altavoces de mentira; preparar
la hoja corre aquí en el mismo hilo (``run_worker`` lo ejecuta en el acto), así que cada
paso se ve sin esperar. Las pruebas de aceptación miran la hoja con el conductor; estas
miran que la ventana enseña esa misma hoja, tal cual, y que mientras está abierta Sirius no
escucha.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from _hojas_en_su_pantalla import mira_que_es_una_ventana_que_cabe
from PySide6.QtCore import QRunnable
from PySide6.QtWidgets import QMainWindow
from pytestqt.qtbot import QtBot

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.config.local_voice import LocalVoiceSettings, SpeakingVoice
from sirius.config.settings import load_settings
from sirius.domain.voice_test import VOICE_TEST_PHRASES
from sirius.infrastructure.local_voice_installation import (
    LISTENING_MODEL_FILES,
    LocalVoiceInstallation,
    speaking_voice_files,
    voice_dir,
)
from sirius.infrastructure.paths import resolve_paths
from sirius.main import _build_main_window
from sirius.ports.embeddings import EmbeddingError
from sirius.ports.local_voice import Captured, ListeningEngines, SpeakingEngines, TurnSignal
from sirius.presentation.voice_test_dialog import VoiceTestDialog

pytestmark = pytest.mark.gui


class _SinHuellas:
    model_name = "sin-huellas"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        del texts
        raise EmbeddingError("sin huellas")


class _Micro:
    def __init__(self) -> None:
        self.abierto = False

    def open(self) -> None:
        self.abierto = True

    def close(self) -> None:
        self.abierto = False

    def read(self) -> Captured[str] | None:
        return None


class _Detector:
    def listen(self, chunk: str) -> TurnSignal:
        del chunk
        return TurnSignal.QUIET

    def reset(self) -> None:
        pass


class _Transcriptor:
    def transcribe(self, chunks: Sequence[str]) -> str:
        del chunks
        return ""


@dataclass
class _Voz:
    nombre: str

    def say(self, text: str) -> str:
        return f"{self.nombre}: {text}"


@dataclass
class _Altavoz:
    sonados: list[str] = field(default_factory=list)
    soltado: bool = False
    playing: bool = False
    latency: float = 0.0
    started: int = 0

    def play(self, sound: str) -> None:
        self.sonados.append(sound)
        self.started += 1

    def stop(self) -> None:
        pass

    def close(self) -> None:
        self.soltado = True


@dataclass
class _Sirius:
    deps: ConversationDependencies
    micro: _Micro
    #: Cada altavoz que se ha cargado, con el nombre de su voz.
    altavoces: list[tuple[str, _Altavoz]]

    def sonado(self) -> list[str]:
        return [sonido for _voz, altavoz in self.altavoces for sonido in altavoz.sonados]


def _instala_las_voces() -> None:
    """El modelo de oír y todas las voces, donde los deja la orden de instalar: de mentira."""
    oir = LocalVoiceInstallation(LocalVoiceSettings()).listening_model_dir
    oir.mkdir(parents=True, exist_ok=True)
    for nombre in (*LISTENING_MODEL_FILES, "vocabulary.txt"):
        (oir / nombre).write_bytes(b"de mentira")
    for voz in SpeakingVoice:
        carpeta = voice_dir(voz)
        carpeta.mkdir(parents=True, exist_ok=True)
        for nombre in speaking_voice_files(voz.value):
            (carpeta / nombre).write_bytes(b"de mentira")


def _monta(tmp_path: Path, *, con_las_voces: bool = True) -> _Sirius:
    rutas = resolve_paths()
    initialize_persistence(rutas)
    if con_las_voces:
        _instala_las_voces()
    micro = _Micro()
    altavoces: list[tuple[str, _Altavoz]] = []

    def habla(modelo: Path) -> SpeakingEngines[str]:
        nombre = modelo.name.removesuffix(".onnx")
        altavoz = _Altavoz()
        altavoces.append((nombre, altavoz))
        return SpeakingEngines(_Voz(nombre), altavoz)

    deps = build_conversation_dependencies(
        rutas.data_dir / "sirius.db",
        tmp_path / "copias",
        secret_store=FakeSecretStore(),
        text_embedder=_SinHuellas(),
        listening_engines=lambda: ListeningEngines(micro, _Detector(), _Transcriptor()),
        speaking_engines=habla,
    )
    deps.initial_project_use_case.create_initial_project("Charla", "Charlar")
    return _Sirius(deps, micro, altavoces)


@dataclass
class _Dialogos:
    avisos: list[tuple[str, str]] = field(default_factory=list)
    informes: list[tuple[str, str]] = field(default_factory=list)


def _hoja(qtbot: QtBot, sirius: _Sirius, dialogos: _Dialogos) -> VoiceTestDialog:
    def en_el_acto(trabajo: QRunnable) -> None:
        trabajo.run()

    hoja = VoiceTestDialog(
        sirius.deps.voice_test_use_case,
        show_warning=lambda titulo, texto: dialogos.avisos.append((titulo, texto)),
        show_information=lambda titulo, texto: dialogos.informes.append((titulo, texto)),
        run_worker=en_el_acto,
    )
    qtbot.addWidget(hoja)
    return hoja


def test_la_hoja_ensena_lo_que_dice_su_vista_y_ningun_nombre(qtbot: QtBot, tmp_path: Path) -> None:
    sirius = _monta(tmp_path)
    hoja = _hoja(qtbot, sirius, _Dialogos())

    assert hoja.start_button.isEnabled()
    hoja.start_button.click()

    assert hoja.pages.currentIndex() == 2
    caso = sirius.deps.voice_test_use_case
    assert hoja._sheet is not None
    assert hoja.visible_text() == caso.view(hoja._sheet).lines()
    visible = "\n".join(hoja.visible_text()).casefold()
    for escondido in (*(voz.value for voz in SpeakingVoice), "piper", "chatterbox", "es_es"):
        assert escondido.casefold() not in visible
    assert len(hoja.listen_buttons) == len(SpeakingVoice) * len(VOICE_TEST_PHRASES)


def test_cada_boton_suena_su_muestra_y_elegir_deja_esa_voz(qtbot: QtBot, tmp_path: Path) -> None:
    sirius = _monta(tmp_path)
    dialogos = _Dialogos()
    hoja = _hoja(qtbot, sirius, dialogos)
    hoja.start_button.click()
    assert hoja._sheet is not None
    etiqueta = hoja._sheet.candidates[1].label
    voz = hoja._sheet.voice_behind(etiqueta)

    # Una fila por frase, con un botón por voz en el orden de la hoja: la tercera frase con
    # la segunda voz.
    boton = hoja.listen_buttons[2 * len(SpeakingVoice) + 1]
    assert boton.text() == etiqueta
    boton.click()

    assert sirius.sonado() == [f"{voz.value}: {VOICE_TEST_PHRASES[2]}"]
    elegir = next(b for b in hoja.choose_buttons if etiqueta in b.text())
    elegir.click()

    assert load_settings()["local_speaking_voice"] == voz.value
    assert dialogos.informes and "voz que has elegido" in dialogos.informes[0][1]
    assert hoja.result() == VoiceTestDialog.DialogCode.Accepted
    # Al cerrarse suelta las voces que cargó para la hoja.
    assert all(altavoz.soltado for _nombre, altavoz in sirius.altavoces)


def test_la_hoja_se_minimiza_se_maximiza_y_cabe_en_su_pantalla(
    qtbot: QtBot, tmp_path: Path
) -> None:
    hoja = _hoja(qtbot, _monta(tmp_path), _Dialogos())
    hoja.start_button.click()

    mira_que_es_una_ventana_que_cabe(hoja, hoja.pages, qtbot)


def test_sin_todas_las_voces_no_se_prepara_y_dice_que_falta(qtbot: QtBot, tmp_path: Path) -> None:
    sirius = _monta(tmp_path, con_las_voces=False)
    hoja = _hoja(qtbot, sirius, _Dialogos())

    assert not hoja.start_button.isEnabled()
    assert "Para la prueba de voces me falta instalar" in hoja.start_status.text()
    assert sirius.altavoces == []


def test_mientras_la_hoja_esta_abierta_no_escucha_y_al_cerrarla_vuelve(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sirius = _monta(tmp_path)
    ventanas: list[QMainWindow] = []
    ventana = _build_main_window(sirius.deps, ventanas)
    qtbot.addWidget(ventana)
    oido = sirius.deps.local_listening
    oido.start()
    assert oido.listening and sirius.micro.abierto
    durante: list[bool] = []
    monkeypatch.setattr(
        type(ventana), "_run_voice_test_dialog", lambda self, caso: durante.append(oido.listening)
    )

    assert ventana.voice_test_button.text() == "Elegir su voz a ciegas…"
    ventana.voice_test_button.click()

    assert durante == [False]
    assert oido.listening and sirius.micro.abierto
