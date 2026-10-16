"""La ventana de la prueba de voces: el propietario elige su voz a ciegas (PA-R03-10).

Tres pasos en la misma ventana: preparar las voces, que dicen las cinco frases, esperar
mientras las dicen, y escuchar cada frase con cada voz, sin saber cuál es cuál, hasta
elegir una. Lo que se ve es la vista de la hoja (``VoiceTestView``) tal cual: etiquetas,
frases y botones, ningún nombre de voz. Ningún botón deja darle un audio a una voz, y
nada se guarda hasta que él pulsa «Elegir…» (ADR-246).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from sirius.application.voice_test import VoiceTestUseCase
from sirius.domain.voice_test import VoiceTestError, VoiceTestSheet
from sirius.infrastructure.logging import get_logger

_logger = get_logger(__name__)

#: Lo que dice la ventana antes de preparar las voces.
PREPARE_INTRO = (
    "Vas a oír cinco frases con varias voces, por tu altavoz y sin saber cuál es cuál. "
    "Mientras esta ventana está abierta, Sirius no te escucha."
)


class VoiceTestWorkerSignals(QObject):
    progress = Signal(int, int)
    succeeded = Signal(object)
    failed = Signal(str)


class VoiceTestWorker(QRunnable):
    """Prepara las voces fuera del hilo de la ventana: la de personaje tarda."""

    def __init__(self, use_case: VoiceTestUseCase) -> None:
        super().__init__()
        self._use_case = use_case
        self._stop = threading.Event()
        self.signals = VoiceTestWorkerSignals()

    def stop(self) -> None:
        """Que no pida más frases; la que está en marcha la termina."""
        self._stop.set()

    def run(self) -> None:
        try:
            sheet = self._use_case.prepare(
                on_progress=self.signals.progress.emit, should_stop=self._stop.is_set
            )
        except VoiceTestError as exc:
            self.signals.failed.emit(str(exc))
        except Exception as exc:
            _logger.error("La prueba de voces se interrumpió (%s)", type(exc).__name__)
            self.signals.failed.emit("La prueba de voces se interrumpió. Inténtalo de nuevo.")
        else:
            self.signals.succeeded.emit(sheet)


class VoiceTestDialog(QDialog):
    """Elegir a ciegas la voz con la que habla Sirius."""

    def __init__(
        self,
        use_case: VoiceTestUseCase,
        *,
        show_warning: Callable[[str, str], None] | None = None,
        show_information: Callable[[str, str], None] | None = None,
        run_worker: Callable[[QRunnable], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Prueba de voces")
        self._use_case = use_case
        self._show_warning = show_warning or self._warning_box
        self._show_information = show_information or self._information_box
        self._run_worker = run_worker or QThreadPool.globalInstance().start
        self._worker: VoiceTestWorker | None = None
        self._sheet: VoiceTestSheet[Any, Any] | None = None

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_start_page())
        self.pages.addWidget(self._build_progress_page())
        self.pages.addWidget(self._build_sheet_page())
        layout = QVBoxLayout(self)
        layout.addWidget(self.pages)
        self._check_installed()

    # --- Paso 1: preparar ---

    def _build_start_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        intro = QLabel(PREPARE_INTRO)
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.start_status = QLabel("")
        self.start_status.setWordWrap(True)
        layout.addWidget(self.start_status)
        self.start_button = QPushButton("Preparar las voces")
        self.start_button.clicked.connect(self._start)
        layout.addWidget(self.start_button)
        layout.addStretch()
        return page

    def _check_installed(self) -> None:
        """Sin todas las voces instaladas, la hoja no se abre a medias: dice qué falta."""
        missing = self._use_case.missing()
        self.start_status.setText(" ".join(missing))
        self.start_button.setEnabled(not missing)

    def _start(self) -> None:
        total = len(self._use_case.voices()) * len(self._use_case.phrases())
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Preparando las voces…")
        self.pages.setCurrentIndex(1)
        worker = VoiceTestWorker(self._use_case)
        worker.signals.progress.connect(self._on_progress)
        worker.signals.succeeded.connect(self._on_prepared)
        worker.signals.failed.connect(self._on_failed)
        self._worker = worker
        self._run_worker(worker)

    # --- Paso 2: mientras dicen las frases ---

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
        self.progress_label.setText(f"Preparando las voces: {done} de {total} frases")

    def _on_failed(self, message: str) -> None:
        if self._worker is None:  # la ventana ya se cerró
            return
        self._worker = None
        self.pages.setCurrentIndex(0)
        self._show_warning("La prueba de voces no pudo prepararse", message)

    def _on_prepared(self, sheet: object) -> None:
        if self._worker is None:  # la ventana ya se cerró: la hoja se descarta
            return
        self._worker = None
        assert isinstance(sheet, VoiceTestSheet)
        self._sheet = sheet
        self._show_sheet()
        self.pages.setCurrentIndex(2)

    # --- Paso 3: escuchar y elegir ---

    def _build_sheet_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.sheet_intro = QLabel("")
        self.sheet_intro.setWordWrap(True)
        layout.addWidget(self.sheet_intro)
        self.sheet_grid = QGridLayout()
        layout.addLayout(self.sheet_grid)
        self.choose_row = QHBoxLayout()
        layout.addLayout(self.choose_row)
        layout.addStretch()
        self.listen_buttons: list[QPushButton] = []
        self.choose_buttons: list[QPushButton] = []
        return page

    def _show_sheet(self) -> None:
        """Pinta la vista de la hoja tal cual: la explicación, una fila por frase con un botón
        por voz para escucharla, y un botón por voz para elegirla."""
        assert self._sheet is not None
        view = self._use_case.view(self._sheet)
        self.sheet_intro.setText(view.intro)
        for row, (phrase, labels) in enumerate(view.rows):
            text = QLabel(phrase)
            text.setWordWrap(True)
            self.sheet_grid.addWidget(text, row, 0)
            for column, label in enumerate(labels, start=1):
                button = QPushButton(label)
                button.clicked.connect(
                    lambda _=False, chosen=label, said=phrase: self.listen(chosen, said)
                )
                self.sheet_grid.addWidget(button, row, column)
                self.listen_buttons.append(button)
        for label, caption in view.choices:
            button = QPushButton(caption)
            button.clicked.connect(lambda _=False, chosen=label: self.choose(chosen))
            self.choose_row.addWidget(button)
            self.choose_buttons.append(button)

    def listen(self, label: str, phrase: str) -> None:
        """Lo mismo que pulsar el botón de ``label`` en la fila de ``phrase``."""
        assert self._sheet is not None
        try:
            self._use_case.listen(self._sheet, label, phrase)
        except VoiceTestError as exc:
            self._show_warning("No se puede escuchar", str(exc))

    def choose(self, label: str) -> None:
        """Lo mismo que pulsar «Elegir…» de ``label``: queda su voz para hablar."""
        assert self._sheet is not None
        self._use_case.choose(self._sheet, label)
        self._show_information(
            "Voz elegida", "Desde el turno siguiente, Sirius habla con la voz que has elegido."
        )
        self.accept()

    def visible_text(self) -> tuple[str, ...]:
        """El texto de la hoja tal como se ve, botones incluidos, en el orden de la vista."""
        texts = [self.sheet_intro.text()]
        columns = self.sheet_grid.columnCount()
        for row in range(self.sheet_grid.rowCount()):
            for column in range(columns):
                item = self.sheet_grid.itemAtPosition(row, column)
                widget = item.widget() if item is not None else None
                if isinstance(widget, QLabel | QPushButton):
                    texts.append(widget.text())
        texts.extend(button.text() for button in self.choose_buttons)
        return tuple(texts)

    def done(self, result: int) -> None:
        """Al cerrarse, a medias o no, para lo que se estuviera preparando y suelta las
        voces."""
        if self._worker is not None:
            self._worker.stop()
            self._worker = None
        self._use_case.close()
        super().done(result)

    def _warning_box(self, title: str, text: str) -> None:
        QMessageBox.warning(self, title, text)

    def _information_box(self, title: str, text: str) -> None:
        QMessageBox.information(self, title, text)
