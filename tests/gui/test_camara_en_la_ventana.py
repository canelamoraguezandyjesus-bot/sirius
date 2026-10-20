"""La ventana ve con la cámara al abrirse, y dice si ve o por qué no (pieza D de la 0.4,
ADR-262).

Las pruebas de aceptación (``tests/acceptance/test_robot_0_4_ojos.py``) miran lo que ve
el propietario con el conductor. Estas miran los bordes de la ventana que allí no salen:
que la cámara que se desenchufa se dice sin esperar a nada, que un fallo que no se espera
se dice y no se borra, que Model Studio la suelta y la recupera, y que al cerrarse la
suelta y para su bucle. Sirius va montado de verdad, con una cámara y un detector de
mentira.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

import sirius.composition_root as composition_root
from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.local_sight import NO_CAMERA
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.infrastructure.local_sight_installation import SIGHT_INSTALL_COMMAND, face_model_path
from sirius.infrastructure.paths import resolve_paths
from sirius.main import _build_listening_main_window, _build_main_window
from sirius.ports.embeddings import EmbeddingError
from sirius.ports.local_sight import CameraUnavailable, SeenFace, SightEngines, SightUnavailable
from sirius.presentation.main_window import SEEING, SIGHT_REFRESH_MS
from sirius.presentation.validated_main_window import ValidatedMainWindow

pytestmark = pytest.mark.gui


class _SinHuellas:
    model_name = "sin-huellas"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        del texts
        raise EmbeddingError("sin huellas")


@dataclass
class _Camara:
    abierta: bool = False
    aperturas: int = 0
    cierres: int = 0
    falla_al_abrir: CameraUnavailable | None = None
    falla_al_leer: CameraUnavailable | None = None

    def open(self) -> None:
        self.aperturas += 1
        if self.falla_al_abrir is not None:
            raise self.falla_al_abrir
        self.abierta = True

    def read(self) -> str | None:
        if self.falla_al_leer is not None:
            raise self.falla_al_leer
        return "fotograma" if self.abierta else None

    def close(self) -> None:
        self.cierres += 1
        self.abierta = False


@dataclass
class _Detector:
    name: str = "mediapipe"

    def detect(self, frame: str) -> tuple[SeenFace[str], ...]:
        del frame
        return ()


@dataclass
class _Ojos:
    camara: _Camara = field(default_factory=_Camara)
    detector: _Detector = field(default_factory=_Detector)
    falla_al_cargar: Exception | None = None

    def carga(self) -> SightEngines[str, str]:
        if self.falla_al_cargar is not None:
            raise self.falla_al_cargar
        return SightEngines(self.camara, self.detector)


def _monta(tmp_path: Path, ojos: _Ojos) -> ConversationDependencies:
    rutas = resolve_paths()
    initialize_persistence(rutas)
    deps = build_conversation_dependencies(
        rutas.data_dir / "sirius.db",
        tmp_path / "copias",
        secret_store=FakeSecretStore(),
        text_embedder=_SinHuellas(),
        sight_engines=ojos.carga,
    )
    deps.initial_project_use_case.create_initial_project("Charla", "Charlar")
    return deps


def _ventana(qtbot: QtBot, deps: ConversationDependencies) -> ValidatedMainWindow:
    """La ventana de verdad, sin el bucle de la vista: la vista la atiende la prueba."""
    ventana = _build_main_window(deps, [])
    qtbot.addWidget(ventana)
    return ventana


def _dice(ventana: ValidatedMainWindow) -> str:
    etiqueta = ventana.camera_label
    return etiqueta.text() if etiqueta.isVisibleTo(ventana) else ""


def test_al_abrirse_ve_y_lo_dice(qtbot: QtBot, tmp_path: Path) -> None:
    ojos = _Ojos()
    ventana = _ventana(qtbot, _monta(tmp_path, ojos))

    assert ojos.camara.abierta
    assert _dice(ventana) == SEEING == "Cámara: te veo"


def test_sin_camara_dice_por_que_y_sigue(qtbot: QtBot, tmp_path: Path) -> None:
    ojos = _Ojos()
    ojos.camara.falla_al_abrir = CameraUnavailable("no hay cámara, o la tiene otro programa")
    ventana = _ventana(qtbot, _monta(tmp_path, ojos))

    assert _dice(ventana) == NO_CAMERA.format(reason="no hay cámara, o la tiene otro programa")
    assert ventana.message_input.isEnabled(), "sin cámara se le sigue escribiendo"


def test_si_la_camara_se_desenchufa_lo_dice_sin_esperar_a_nada(
    qtbot: QtBot, tmp_path: Path
) -> None:
    ojos = _Ojos()
    deps = _monta(tmp_path, ojos)
    ventana = _ventana(qtbot, deps)
    ojos.camara.falla_al_leer = CameraUnavailable("la cámara ha dejado de dar imagen")

    deps.local_sight.look()

    assert SIGHT_REFRESH_MS == 500
    esperado = NO_CAMERA.format(reason="la cámara ha dejado de dar imagen")
    qtbot.waitUntil(lambda: _dice(ventana) == esperado, timeout=2000)
    assert not ojos.camara.abierta


def test_un_fallo_que_no_se_espera_al_abrir_la_vista_se_dice_y_no_se_borra(
    qtbot: QtBot, tmp_path: Path
) -> None:
    ojos = _Ojos(falla_al_cargar=RuntimeError("algo de Marta"))
    ventana = _ventana(qtbot, _monta(tmp_path, ojos))
    esperado = "No puedo verte: ha fallado (RuntimeError). Sigo oyéndote y hablando."

    assert _dice(ventana) == esperado
    qtbot.wait(SIGHT_REFRESH_MS * 2 + 100)
    assert _dice(ventana) == esperado, "el indicador lo borra al refrescarse"


def test_en_model_studio_suelta_la_camara_y_al_volver_la_abre(qtbot: QtBot, tmp_path: Path) -> None:
    ojos = _Ojos()
    ventana = _ventana(qtbot, _monta(tmp_path, ojos))

    ventana.open_model_studio()

    assert not ojos.camara.abierta, "OBS la puede querer para grabar"
    qtbot.wait(SIGHT_REFRESH_MS + 100)
    assert not ojos.camara.abierta, "el indicador al refrescarse no la vuelve a abrir"

    ventana.close_model_studio()

    assert ojos.camara.abierta
    assert _dice(ventana) == SEEING


def test_sin_camara_al_entrar_en_model_studio_no_la_busca_al_salir(
    qtbot: QtBot, tmp_path: Path
) -> None:
    ojos = _Ojos()
    ojos.camara.falla_al_abrir = CameraUnavailable("no hay cámara, o la tiene otro programa")
    ventana = _ventana(qtbot, _monta(tmp_path, ojos))

    ventana.open_model_studio()
    ventana.close_model_studio()

    assert ojos.camara.aperturas == 1


def test_al_cerrarse_suelta_la_camara(qtbot: QtBot, tmp_path: Path) -> None:
    ojos = _Ojos()
    ventana = _ventana(qtbot, _monta(tmp_path, ojos))

    ventana.close()

    assert not ojos.camara.abierta
    assert ojos.camara.cierres == 1


def test_la_ventana_de_verdad_trae_su_bucle_de_la_vista_y_lo_para_al_cerrarse(
    qtbot: QtBot, tmp_path: Path
) -> None:
    ojos = _Ojos()
    ventana = _build_listening_main_window(_monta(tmp_path, ojos), [])
    qtbot.addWidget(ventana)
    bucle = ventana._sight_loop
    assert bucle is not None and bucle.running
    assert ventana._listening_loop is not None, "cada uno con su bucle"

    ventana.close()

    assert bucle.wait(5)
    assert not ojos.camara.abierta


# --- Cómo se monta ---------------------------------------------------------------------


def test_sin_decir_con_que_ve_es_la_vista_de_verdad_y_no_carga_nada_hasta_empezar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cargas: list[Path] = []

    def carga(modelo: Path) -> SightEngines[str, str]:
        cargas.append(modelo)
        raise SightUnavailable("falta el modelo de las caras")

    monkeypatch.setattr(composition_root, "load_sight_engines", carga)
    rutas = resolve_paths()
    initialize_persistence(rutas)
    deps = build_conversation_dependencies(
        rutas.data_dir / "sirius.db",
        tmp_path / "copias",
        secret_store=FakeSecretStore(),
        text_embedder=_SinHuellas(),
    )
    assert cargas == [], "construir no carga la vista"

    aviso = deps.local_sight.start()

    assert cargas == [face_model_path()]
    assert SIGHT_INSTALL_COMMAND in aviso


def test_el_oido_le_pregunta_a_la_vista_si_le_miran_con_el_mismo_reloj(tmp_path: Path) -> None:
    deps = _monta(tmp_path, _Ojos())

    assert deps.local_listening._looked_at == deps.local_sight.talker_looked_since
    assert deps.local_sight._clock is deps.local_listening.clock
