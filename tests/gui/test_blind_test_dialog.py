"""La ventana de la prueba a ciegas (pieza C de ADR-233, PA-R02-03).

El trabajo de preguntar a los modelos corre aquí en el mismo hilo
(``run_worker`` lo ejecuta en el acto), así que cada paso se ve sin esperar.
"""

from __future__ import annotations

import random
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from PySide6.QtCore import QRunnable
from PySide6.QtWidgets import QAbstractButton, QLabel, QMainWindow
from pytestqt.qtbot import QtBot

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.blind_test import BlindTestUseCase
from sirius.composition_root import build_conversation_dependencies
from sirius.config.settings import save_settings
from sirius.domain.blind_test import BLIND_TEST_QUESTIONS, BlindTestError
from sirius.domain.identity import Identity, IdentityVersion
from sirius.infrastructure.paths import resolve_paths
from sirius.main import _build_main_window
from sirius.ports.llm import LLMCompleted, LLMError, LLMErrorKind, LLMRequest, LLMStreamEvent
from sirius.presentation.blind_test_dialog import BlindTestDialog

pytestmark = pytest.mark.gui

_FRUTAS = {"qwen-x": "pera", "gemma-y": "manzana", "mistral-z": "uva"}


class _Identidades:
    def get_or_create_current_identity(self) -> Identity:
        version = IdentityVersion(
            id=1,
            identity_id=1,
            version=2,
            name="Sirius",
            description="El software del robot.",
            personality_instructions="Gracioso ante todo.",
            created_at=datetime(2026, 10, 7, tzinfo=UTC),
        )
        return Identity(id=1, current_version=version, created_at=version.created_at)


class _Modelo:
    def __init__(self, nombre: str, *, falla: bool = False) -> None:
        self._fruta = _FRUTAS[nombre]
        self._falla = falla

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        if self._falla:
            yield LLMError(kind=LLMErrorKind.CONNECTION, message="No se pudo contactar.")
            return
        numero = BLIND_TEST_QUESTIONS.index(request.input_text) + 1
        yield LLMCompleted(text=f"{self._fruta} {numero}", input_tokens=1, output_tokens=1)

    def cancel(self, operation_id: str) -> None:
        del operation_id


class _Entorno:
    def __init__(
        self, *, instalados: tuple[str, ...] | None = None, falla: str | None = None
    ) -> None:
        self.elegidos: list[str] = []
        self.avisos: list[tuple[str, str]] = []
        self.informes: list[tuple[str, str]] = []
        self._instalados = instalados

        def listar() -> tuple[str, ...]:
            if self._instalados is None:
                msg = "No se pudo preguntar a Ollama qué modelos tiene. ¿Está abierto?"
                raise BlindTestError(msg)
            return self._instalados

        self.caso = BlindTestUseCase(
            identity_repository=_Identidades(),  # type: ignore[arg-type]
            provider_for=lambda nombre: _Modelo(nombre, falla=nombre == falla),
            list_models=listar,
            choose_model=self.elegidos.append,
            current_model=lambda: self.elegidos[-1] if self.elegidos else None,
            rng=random.Random(4),
        )

    def ventana(self, qtbot: QtBot) -> BlindTestDialog:
        def correr(trabajo: QRunnable) -> None:
            trabajo.run()

        dialogo = BlindTestDialog(
            self.caso,
            show_warning=lambda titulo, texto: self.avisos.append((titulo, texto)),
            show_information=lambda titulo, texto: self.informes.append((titulo, texto)),
            run_worker=correr,
        )
        qtbot.addWidget(dialogo)
        return dialogo


def _marca(dialogo: BlindTestDialog, *modelos: str) -> None:
    for check in dialogo.model_checks:
        check.setChecked(check.text() in modelos)


def _textos_visibles(dialogo: BlindTestDialog) -> str:
    pagina = dialogo.pages.currentWidget()
    etiquetas = [w.text() for w in pagina.findChildren(QLabel) if w.isVisibleTo(dialogo)]
    botones = [w.text() for w in pagina.findChildren(QAbstractButton) if w.isVisibleTo(dialogo)]
    return "\n".join(etiquetas + botones)


def test_ofrece_los_modelos_de_ollama_y_solo_deja_empezar_con_dos_o_tres(qtbot: QtBot) -> None:
    dialogo = _Entorno(instalados=("gemma-y", "mistral-z", "qwen-x")).ventana(qtbot)

    assert [check.text() for check in dialogo.model_checks] == ["gemma-y", "mistral-z", "qwen-x"]
    assert not dialogo.start_button.isEnabled()
    _marca(dialogo, "qwen-x")
    assert not dialogo.start_button.isEnabled()
    _marca(dialogo, "qwen-x", "gemma-y")
    assert dialogo.start_button.isEnabled()
    _marca(dialogo, "qwen-x", "gemma-y", "mistral-z")
    assert dialogo.start_button.isEnabled()


def test_mientras_elige_no_ve_ningun_nombre_y_al_final_se_queda_el_que_mas_eligio(
    qtbot: QtBot,
) -> None:
    entorno = _Entorno(instalados=("gemma-y", "mistral-z", "qwen-x"))
    dialogo = entorno.ventana(qtbot)
    _marca(dialogo, "qwen-x", "gemma-y", "mistral-z")
    dialogo.start_button.click()

    assert dialogo.pages.currentIndex() == 2
    for numero in range(1, 21):
        visibles = _textos_visibles(dialogo)
        for modelo in _FRUTAS:
            assert modelo not in visibles
        boton = next(b for b in dialogo.option_buttons if f"manzana {numero}" in b.text())
        dialogo.choose_letter(str(boton.property("letter")))
        dialogo.next_button.click()

    assert dialogo.pages.currentIndex() == 3
    assert "gemma-y en 20 de 20" in dialogo.result_label.text()
    assert entorno.elegidos == []
    [usar] = dialogo.use_buttons
    usar.click()
    assert entorno.elegidos == ["gemma-y"]
    assert entorno.informes == [
        ("Modelo elegido", "Desde ahora Sirius conversa con gemma-y, en tu ordenador.")
    ]


def test_no_deja_pasar_de_pregunta_sin_elegir_y_deja_volver_atras(qtbot: QtBot) -> None:
    dialogo = _Entorno(instalados=("gemma-y", "qwen-x")).ventana(qtbot)
    _marca(dialogo, "qwen-x", "gemma-y")
    dialogo.start_button.click()

    assert not dialogo.next_button.isEnabled()
    assert not dialogo.previous_button.isEnabled()
    dialogo.choose_letter("A")
    dialogo.next_button.click()
    assert "Pregunta 2 de 20" in _textos_visibles(dialogo)
    dialogo.previous_button.click()
    assert "Pregunta 1 de 20" in _textos_visibles(dialogo)
    assert dialogo.next_button.isEnabled()


def test_con_empate_elige_el_propietario_entre_los_empatados(qtbot: QtBot) -> None:
    entorno = _Entorno(instalados=("gemma-y", "qwen-x"))
    dialogo = entorno.ventana(qtbot)
    _marca(dialogo, "qwen-x", "gemma-y")
    dialogo.start_button.click()

    for numero in range(1, 21):
        fruta = "pera" if numero <= 10 else "manzana"
        boton = next(b for b in dialogo.option_buttons if f"{fruta} {numero}" in b.text())
        dialogo.choose_letter(str(boton.property("letter")))
        dialogo.next_button.click()

    assert "Empate" in dialogo.result_label.text()
    assert sorted(b.text() for b in dialogo.use_buttons) == [
        "Usar gemma-y para la charla",
        "Usar qwen-x para la charla",
    ]
    next(b for b in dialogo.use_buttons if "qwen-x" in b.text()).click()
    assert entorno.elegidos == ["qwen-x"]


def test_si_ollama_no_esta_abierto_lo_dice_y_no_deja_empezar(qtbot: QtBot) -> None:
    dialogo = _Entorno(instalados=None).ventana(qtbot)

    assert "Ollama" in dialogo.models_status.text()
    assert dialogo.model_checks == []
    assert not dialogo.start_button.isEnabled()


def test_si_un_modelo_no_contesta_avisa_y_vuelve_a_elegir_modelos(qtbot: QtBot) -> None:
    entorno = _Entorno(instalados=("gemma-y", "qwen-x"), falla="qwen-x")
    dialogo = entorno.ventana(qtbot)
    _marca(dialogo, "qwen-x", "gemma-y")
    dialogo.start_button.click()

    assert dialogo.pages.currentIndex() == 0
    [(titulo, texto)] = entorno.avisos
    assert titulo == "La prueba a ciegas no pudo terminar"
    assert "qwen-x" in texto
    assert entorno.elegidos == []


def test_cerrar_a_medias_para_las_preguntas_y_no_avisa_de_nada(qtbot: QtBot) -> None:
    entorno = _Entorno(instalados=("gemma-y", "qwen-x"))
    preguntas: list[str] = []

    class _ModeloQueApunta(_Modelo):
        def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
            preguntas.append(request.input_text)
            return super().stream_response(request)

    entorno.caso._provider_for = _ModeloQueApunta
    pendientes: list[QRunnable] = []
    dialogo = BlindTestDialog(
        entorno.caso,
        show_warning=lambda titulo, texto: entorno.avisos.append((titulo, texto)),
        run_worker=pendientes.append,
    )
    qtbot.addWidget(dialogo)
    _marca(dialogo, "gemma-y", "qwen-x")
    dialogo.start_button.click()

    dialogo.reject()
    [trabajo] = pendientes
    trabajo.run()

    assert preguntas == []
    assert entorno.avisos == []
    assert entorno.elegidos == []


def test_la_configuracion_dice_con_que_modelo_conversa_sirius(qtbot: QtBot, tmp_path: Path) -> None:
    save_settings({"llm_provider": "ollama", "ollama_chat_model": "gemma-y"})
    rutas = resolve_paths()
    initialize_persistence(rutas)
    dependencias = build_conversation_dependencies(
        rutas.data_dir / "sirius.db", tmp_path / "copias", secret_store=FakeSecretStore()
    )
    dependencias.initial_project_use_case.create_initial_project("Charla", "Charlar")
    ventanas: list[QMainWindow] = []

    ventana = _build_main_window(dependencias, ventanas)
    qtbot.addWidget(ventana)

    assert ventana.chat_model_label.text() == "Sirius conversa con gemma-y, en este ordenador."
    assert ventana.blind_test_button.text() == "Elegir el modelo a ciegas…"
