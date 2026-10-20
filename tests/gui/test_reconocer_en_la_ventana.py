"""Dar y quitar el permiso para que Sirius te reconozca, en la ventana (pieza E de la 0.4,
ADR-263).

Las pruebas de aceptación (``tests/acceptance/test_robot_0_4_reconocer.py``) miran que
reconoce y que borra, con el conductor. Estas miran la ventana: que dar permiso solo se
ofrece con la cámara viendo, que pide el nombre y explica qué guarda antes de empezar, que
dice en qué paso va, que se puede cancelar, y que quitar el permiso borra sus huellas o
dice que no ha podido. Sirius va montado de verdad, con una cámara, un detector y unos
reconocedores de mentira.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

import sirius.composition_root as composition_root
from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.recognition import (
    FACE_SAMPLES,
    LONGEST_NAME,
    LOOK_AT_ME,
    SAY_IT,
    EnrollmentStep,
)
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.infrastructure.local_sight_installation import (
    face_recognition_dir,
    voice_recognition_dir,
)
from sirius.infrastructure.paths import resolve_paths
from sirius.main import _build_main_window
from sirius.ports.embeddings import EmbeddingError
from sirius.ports.local_sight import CameraUnavailable, SeenFace, SightEngines
from sirius.ports.recognition import Print, RecognitionEngines, RecognitionUnavailable
from sirius.presentation.main_window import ENROLL_HELP, NOT_FORGOTTEN
from sirius.presentation.validated_main_window import ValidatedMainWindow

pytestmark = pytest.mark.gui

_HUELLAS: dict[str, Print] = {"marta": (1.0, 0.0, 0.0), "pepe": (0.0, 1.0, 0.0)}


class _SinHuellas:
    model_name = "sin-huellas"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        del texts
        raise EmbeddingError("sin huellas")


@dataclass
class _Camara:
    falla_al_abrir: CameraUnavailable | None = None

    def open(self) -> None:
        if self.falla_al_abrir is not None:
            raise self.falla_al_abrir

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


class _Caras:
    name = "insightface"

    def fingerprint(self, crop: str) -> Print:
        return _HUELLAS[crop]


class _Voces:
    name = "speechbrain-ecapa"

    def fingerprint(self, chunks: Sequence[str]) -> Print | None:
        return _HUELLAS["".join(chunks)]


def _monta(tmp_path: Path, camara: _Camara | None = None) -> ConversationDependencies:
    rutas = resolve_paths()
    initialize_persistence(rutas)
    detector = _Detector()
    deps = build_conversation_dependencies(
        rutas.data_dir / "sirius.db",
        tmp_path / "copias",
        secret_store=FakeSecretStore(),
        text_embedder=_SinHuellas(),
        sight_engines=lambda: SightEngines(camara or _Camara(), detector),
        recognition_engines=lambda: RecognitionEngines(_Caras(), _Voces()),
    )
    deps.initial_project_use_case.create_initial_project("Charla", "Charlar")
    return deps


def _ventana(qtbot: QtBot, deps: ConversationDependencies) -> ValidatedMainWindow:
    ventana = _build_main_window(deps, [])
    qtbot.addWidget(ventana)
    ventana._refresh_camera()
    return ventana


def _da_permiso(deps: ConversationDependencies, nombre: str, huella: str) -> None:
    """Como lo dan la ventana, la vista y el oído, sin pasar por ellos."""
    deps.recognition.begin(nombre)
    for _ in range(FACE_SAMPLES):
        deps.recognition.take_face(huella)
    deps.recognition.take_voice([huella])
    assert _paso(deps) is EnrollmentStep.DONE


def _paso(deps: ConversationDependencies) -> EnrollmentStep:
    """En qué va el permiso, leído de nuevo cada vez."""
    return deps.recognition.enrollment.step


def _huellas_guardadas() -> int:
    with closing(sqlite3.connect(resolve_paths().data_dir / "sirius.db")) as conexion:
        (cuantas,) = conexion.execute("SELECT COUNT(*) FROM recognition_prints").fetchone()
    return int(cuantas)


def _visible(ventana: ValidatedMainWindow, nombre: str) -> bool:
    widget = getattr(ventana, nombre)
    return bool(widget.isVisibleTo(ventana))


def test_con_la_camara_viendo_se_ofrece_dar_permiso(qtbot: QtBot, tmp_path: Path) -> None:
    ventana = _ventana(qtbot, _monta(tmp_path))

    assert _visible(ventana, "recognize_button")
    assert ventana.recognize_button.text() == "Que me reconozca"
    for nombre in ("enroll_name", "enroll_confirm", "enroll_cancel", "enroll_help"):
        assert not _visible(ventana, nombre), f"{nombre} se ve sin haber pedido dar permiso"


def test_sin_camara_no_se_ofrece_dar_permiso(qtbot: QtBot, tmp_path: Path) -> None:
    sin_camara = _Camara(CameraUnavailable("no hay cámara, o la tiene otro programa"))
    ventana = _ventana(qtbot, _monta(tmp_path, sin_camara))

    assert not _visible(ventana, "recognize_button")


def test_dar_permiso_pide_su_nombre_explica_que_guarda_y_dice_en_que_paso_va(
    qtbot: QtBot, tmp_path: Path
) -> None:
    deps = _monta(tmp_path)
    ventana = _ventana(qtbot, deps)

    ventana.recognize_button.click()
    assert _visible(ventana, "enroll_name")
    assert _visible(ventana, "enroll_help")
    assert ventana.enroll_help.text() == ENROLL_HELP
    assert "cifradas" in ENROLL_HELP and "solo en este ordenador" in ENROLL_HELP
    assert "quitar el permiso" in ENROLL_HELP
    assert not _visible(ventana, "recognize_button")
    assert _paso(deps) is EnrollmentStep.IDLE, "aún no ha empezado"

    ventana.enroll_name.setText("Marta")
    ventana.enroll_confirm.click()

    assert _paso(deps) is EnrollmentStep.FACE
    assert ventana.enroll_label.text() == LOOK_AT_ME.format(name="Marta")
    assert _visible(ventana, "enroll_label")
    assert _visible(ventana, "enroll_cancel")
    assert not _visible(ventana, "enroll_name")
    for _ in range(FACE_SAMPLES):
        deps.recognition.take_face("marta")
    ventana._refresh_camera()
    assert ventana.enroll_label.text() == SAY_IT.format(name="Marta")


def test_el_nombre_no_pasa_de_lo_que_cabe_y_uno_vacio_no_empieza_nada(
    qtbot: QtBot, tmp_path: Path
) -> None:
    deps = _monta(tmp_path)
    ventana = _ventana(qtbot, deps)
    ventana.recognize_button.click()

    ventana.enroll_name.setText("   ")
    ventana.enroll_confirm.click()

    assert _paso(deps) is EnrollmentStep.IDLE
    assert _visible(ventana, "enroll_name"), "sigue pidiendo el nombre"
    assert ventana.enroll_name.maxLength() == LONGEST_NAME


def test_cancelar_deja_el_permiso_sin_guardar_nada(qtbot: QtBot, tmp_path: Path) -> None:
    deps = _monta(tmp_path)
    ventana = _ventana(qtbot, deps)
    ventana.recognize_button.click()
    ventana.enroll_name.setText("Marta")
    ventana.enroll_name.returnPressed.emit()
    assert deps.recognition.wants_face()

    ventana.enroll_cancel.click()

    assert _paso(deps) is EnrollmentStep.IDLE
    assert not _visible(ventana, "enroll_label")
    assert _visible(ventana, "recognize_button")
    assert _huellas_guardadas() == 0


def test_quitar_el_permiso_borra_sus_huellas_y_deja_de_ofrecerlo(
    qtbot: QtBot, tmp_path: Path
) -> None:
    deps = _monta(tmp_path)
    _da_permiso(deps, "Marta", "marta")
    _da_permiso(deps, "Pepe", "pepe")
    ventana = _ventana(qtbot, deps)
    assert [ventana.forget_combo.itemText(i) for i in range(ventana.forget_combo.count())] == [
        "Marta",
        "Pepe",
    ]
    assert _visible(ventana, "forget_button")

    ventana.forget_combo.setCurrentText("Pepe")
    ventana._refresh_camera()
    assert ventana.forget_combo.currentText() == "Pepe", "mirar otra vez no cambia la elegida"
    ventana.forget_button.click()

    assert _huellas_guardadas() == 2
    assert deps.recognition.people() == ("Marta",)
    assert ventana.forget_combo.count() == 1
    ventana.forget_combo.setCurrentText("Marta")
    ventana.forget_button.click()
    assert _huellas_guardadas() == 0
    assert not _visible(ventana, "forget_button")
    assert not _visible(ventana, "forget_combo")


def test_si_no_se_pueden_borrar_sus_huellas_lo_dice(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    deps = _monta(tmp_path)
    _da_permiso(deps, "Marta", "marta")
    ventana = _ventana(qtbot, deps)

    def ocupada(person: str) -> int:
        msg = "database is locked"
        raise sqlite3.OperationalError(msg)

    monkeypatch.setattr(deps.recognition._store, "remove", ocupada)
    ventana.forget_button.click()

    assert ventana.error_label.text() == NOT_FORGOTTEN.format(name="Marta")
    assert _huellas_guardadas() == 2
    assert deps.recognition.people() == ("Marta",)


def test_los_botones_dicen_lo_que_hacen_para_un_lector_de_pantalla(
    qtbot: QtBot, tmp_path: Path
) -> None:
    ventana = _ventana(qtbot, _monta(tmp_path))

    assert ventana.recognize_button.accessibleName() == "Dar permiso para que Sirius te reconozca"
    assert ventana.forget_button.accessibleName() == "Quitar el permiso y borrar sus huellas"
    assert ventana.forget_combo.accessibleName() == "A quién olvidar"
    assert ventana.enroll_label.accessibleName() == "El permiso para reconocerte"


# --- Cómo se monta ---------------------------------------------------------------------


def test_sin_decir_con_que_reconoce_carga_lo_de_la_orden_de_instalar_y_solo_al_hacer_falta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # PA-R04-10 lee con qué reconoce de los reconocedores que construye
    # `load_recognition_engines`; esto fija que es lo que carga Sirius sin dobles.
    cargas: list[tuple[Path, Path]] = []

    def carga(caras: Path, voces: Path) -> RecognitionEngines[str, str]:
        cargas.append((caras, voces))
        raise RecognitionUnavailable("de mentira")

    monkeypatch.setattr(composition_root, "load_recognition_engines", carga)
    rutas = resolve_paths()
    initialize_persistence(rutas)
    deps = build_conversation_dependencies(
        rutas.data_dir / "sirius.db",
        tmp_path / "copias",
        secret_store=FakeSecretStore(),
        text_embedder=_SinHuellas(),
    )
    deps.recognition.begin("Marta")
    assert cargas == [], "construirlo y empezar a dar permiso no cargan nada"

    deps.recognition.take_face("marta")

    assert cargas == [(face_recognition_dir(), voice_recognition_dir())]
    assert _paso(deps) is EnrollmentStep.FAILED
