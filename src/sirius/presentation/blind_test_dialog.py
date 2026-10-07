"""La ventana de la prueba a ciegas: el propietario elige el modelo de la charla (PA-R02-03).

Cuatro pasos en la misma ventana: elegir dos o tres de los modelos que tiene
Ollama, esperar mientras contestan las 20 preguntas, elegir en cada pregunta la
respuesta que más le suena a Sirius sin saber de quién es, y confirmar el
ganador. Los nombres de los modelos no aparecen hasta el resultado. Nada se
guarda hasta que él pulsa «Usar … para la charla».
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from sirius.application.blind_test import BlindTestUseCase
from sirius.domain.blind_test import (
    MAX_MODELS,
    MIN_MODELS,
    BlindTestError,
    BlindTestResult,
    BlindTestSheet,
)
from sirius.infrastructure.logging import get_logger

_logger = get_logger(__name__)


class BlindTestWorkerSignals(QObject):
    progress = Signal(int, int)
    succeeded = Signal(object)
    failed = Signal(str)


class BlindTestWorker(QRunnable):
    """Pregunta a los modelos fuera del hilo de la ventana: tarda minutos."""

    def __init__(self, use_case: BlindTestUseCase, models: Sequence[str]) -> None:
        super().__init__()
        self._use_case = use_case
        self._models = tuple(models)
        self._stop = threading.Event()
        self.signals = BlindTestWorkerSignals()

    def stop(self) -> None:
        """Que no haga más preguntas; la que está en marcha la termina."""
        self._stop.set()

    def run(self) -> None:
        try:
            sheet = self._use_case.prepare(
                self._models, on_progress=self.signals.progress.emit, should_stop=self._stop.is_set
            )
        except BlindTestError as exc:
            self.signals.failed.emit(str(exc))
        except Exception as exc:
            _logger.error("La prueba a ciegas se interrumpió (%s)", type(exc).__name__)
            self.signals.failed.emit("La prueba a ciegas se interrumpió. Inténtalo de nuevo.")
        else:
            self.signals.succeeded.emit(sheet)


class BlindTestDialog(QDialog):
    """Elegir a ciegas el modelo con el que conversa Sirius."""

    def __init__(
        self,
        use_case: BlindTestUseCase,
        *,
        show_warning: Callable[[str, str], None] | None = None,
        show_information: Callable[[str, str], None] | None = None,
        run_worker: Callable[[QRunnable], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Prueba a ciegas")
        self._use_case = use_case
        self._show_warning = show_warning or self._warning_box
        self._show_information = show_information or self._information_box
        self._run_worker = run_worker or QThreadPool.globalInstance().start
        self._worker: BlindTestWorker | None = None
        self._sheet: BlindTestSheet | None = None
        self._choices: dict[int, str] = {}
        self._index = 0
        self._result: BlindTestResult | None = None

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_models_page())
        self.pages.addWidget(self._build_progress_page())
        self.pages.addWidget(self._build_question_page())
        self.pages.addWidget(self._build_result_page())
        layout = QVBoxLayout(self)
        layout.addWidget(self.pages)
        self._load_models()

    # --- Paso 1: elegir los modelos ---

    def _build_models_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        intro = QLabel(
            "Elige dos o tres de los modelos que tienes en Ollama. Cada uno contestará "
            "20 preguntas como Sirius, y tú elegirás sin saber de quién es cada respuesta."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.models_box = QVBoxLayout()
        layout.addLayout(self.models_box)
        self.models_status = QLabel("")
        self.models_status.setWordWrap(True)
        layout.addWidget(self.models_status)
        self.start_button = QPushButton("Empezar")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self._start)
        layout.addWidget(self.start_button)
        layout.addStretch()
        self.model_checks: list[QCheckBox] = []
        return page

    def _load_models(self) -> None:
        try:
            models = self._use_case.installed_models()
        except BlindTestError as exc:
            self.models_status.setText(str(exc))
            return
        if len(models) < MIN_MODELS:
            self.models_status.setText(
                "Ollama tiene menos de dos modelos instalados: hacen falta dos o tres "
                "para compararlos."
            )
        for model in models:
            check = QCheckBox(model)
            check.toggled.connect(self._refresh_start)
            self.models_box.addWidget(check)
            self.model_checks.append(check)

    def _selected_models(self) -> list[str]:
        return [check.text() for check in self.model_checks if check.isChecked()]

    def _refresh_start(self) -> None:
        self.start_button.setEnabled(MIN_MODELS <= len(self._selected_models()) <= MAX_MODELS)

    def _start(self) -> None:
        models = self._selected_models()
        self.progress_bar.setRange(0, len(models) * len(self._use_case.questions()))
        self.progress_bar.setValue(0)
        self.progress_label.setText("Preguntando a los modelos…")
        self.pages.setCurrentIndex(1)
        worker = BlindTestWorker(self._use_case, models)
        worker.signals.progress.connect(self._on_progress)
        worker.signals.succeeded.connect(self._on_prepared)
        worker.signals.failed.connect(self._on_failed)
        self._worker = worker
        self._run_worker(worker)

    # --- Paso 2: mientras contestan ---

    def _build_progress_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.progress_label = QLabel("")
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        layout.addStretch()
        return page

    def _on_progress(self, done: int, total: int) -> None:
        if self._worker is None:  # la ventana ya se cerró
            return
        self.progress_bar.setValue(done)
        self.progress_label.setText(f"Preguntando a los modelos: {done} de {total}")

    def _on_failed(self, message: str) -> None:
        if self._worker is None:  # la ventana ya se cerró
            return
        self._worker = None
        self.pages.setCurrentIndex(0)
        self._show_warning("La prueba a ciegas no pudo terminar", message)

    def _on_prepared(self, sheet: object) -> None:
        if self._worker is None:  # la ventana ya se cerró: la hoja se descarta
            return
        self._worker = None
        assert isinstance(sheet, BlindTestSheet)
        self._sheet = sheet
        self._choices = {}
        self._index = 0
        self._show_question()
        self.pages.setCurrentIndex(2)

    # --- Paso 3: elegir a ciegas ---

    def _build_question_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.question_number = QLabel("")
        self.question_text = QLabel("")
        self.question_text.setWordWrap(True)
        layout.addWidget(self.question_number)
        layout.addWidget(self.question_text)
        self.options_box = QVBoxLayout()
        layout.addLayout(self.options_box)
        self.option_group = QButtonGroup(page)
        self.option_group.buttonClicked.connect(self._on_option)
        self.option_buttons: list[QRadioButton] = []
        buttons = QHBoxLayout()
        self.previous_button = QPushButton("Anterior")
        self.previous_button.clicked.connect(self._previous)
        self.next_button = QPushButton("Siguiente")
        self.next_button.clicked.connect(self._next)
        buttons.addWidget(self.previous_button)
        buttons.addWidget(self.next_button)
        layout.addLayout(buttons)
        layout.addStretch()
        return page

    def _show_question(self) -> None:
        assert self._sheet is not None
        item = self._sheet.items[self._index]
        self.question_number.setText(f"Pregunta {self._index + 1} de {len(self._sheet.items)}")
        self.question_text.setText(item.question)
        for button in self.option_buttons:
            self.option_group.removeButton(button)
            self.options_box.removeWidget(button)
            button.deleteLater()
        self.option_buttons = []
        for letter, answer in item.options:
            button = QRadioButton(f"{letter}) {answer}")
            button.setProperty("letter", letter)
            button.setChecked(self._choices.get(self._index) == letter)
            self.option_group.addButton(button)
            self.options_box.addWidget(button)
            self.option_buttons.append(button)
        self.previous_button.setEnabled(self._index > 0)
        last = self._index == len(self._sheet.items) - 1
        self.next_button.setText("Ver el resultado" if last else "Siguiente")
        self.next_button.setEnabled(self._index in self._choices)

    def _on_option(self, button: QRadioButton) -> None:
        self._choices[self._index] = str(button.property("letter"))
        self.next_button.setEnabled(True)

    def choose_letter(self, letter: str) -> None:
        """Lo mismo que pulsar la respuesta ``letter`` de la pregunta en pantalla."""
        for button in self.option_buttons:
            if button.property("letter") == letter:
                button.click()
                return
        msg = f"La pregunta en pantalla no tiene respuesta {letter!r}"
        raise ValueError(msg)

    def _previous(self) -> None:
        if self._index > 0:
            self._index -= 1
            self._show_question()

    def _next(self) -> None:
        assert self._sheet is not None
        if self._index < len(self._sheet.items) - 1:
            self._index += 1
            self._show_question()
            return
        self._result = self._use_case.result(self._sheet, self._choices)
        self._show_result()
        self.pages.setCurrentIndex(3)

    # --- Paso 4: el resultado ---

    def _build_result_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)
        self.result_buttons = QVBoxLayout()
        layout.addLayout(self.result_buttons)
        layout.addStretch()
        self.use_buttons: list[QPushButton] = []
        return page

    def _show_result(self) -> None:
        assert self._result is not None and self._sheet is not None
        votes = self._result.votes
        total = len(self._sheet.items)
        recuento = ", ".join(f"{model}: {votes[model]}" for model in self._sheet.models)
        if self._result.winner is not None:
            self.result_label.setText(
                f"Has elegido {self._result.winner} en {votes[self._result.winner]} de "
                f"{total} preguntas ({recuento})."
            )
            candidates: tuple[str, ...] = (self._result.winner,)
        else:
            self.result_label.setText(f"Empate ({recuento}). Elige tú con cuál se queda Sirius.")
            candidates = self._result.tied
        for button in self.use_buttons:
            self.result_buttons.removeWidget(button)
            button.deleteLater()
        self.use_buttons = []
        for model in candidates:
            button = QPushButton(f"Usar {model} para la charla")
            button.clicked.connect(lambda _=False, chosen=model: self._use(chosen))
            self.result_buttons.addWidget(button)
            self.use_buttons.append(button)

    def _use(self, model: str) -> None:
        self._use_case.choose(model)
        self._show_information(
            "Modelo elegido", f"Desde ahora Sirius conversa con {model}, en tu ordenador."
        )
        self.accept()

    def done(self, result: int) -> None:
        """Al cerrarse, a medias o no, para las preguntas pendientes."""
        if self._worker is not None:
            self._worker.stop()
            self._worker = None
        super().done(result)

    def _warning_box(self, title: str, text: str) -> None:
        QMessageBox.warning(self, title, text)

    def _information_box(self, title: str, text: str) -> None:
        QMessageBox.information(self, title, text)
