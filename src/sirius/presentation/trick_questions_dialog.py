"""La ventana de las 40 preguntas trampa: el propietario las lee y marca (E-R02-03).

Tres pasos en la misma ventana: Sirius contesta las 40 ideas malas con el
modelo de la charla, el propietario lee cada respuesta y marca si le lleva la
contraria o le da la razón, y al final ve cuántas y en cuántas el juez dice otra
cosa. Solo se abre con la charla en un modelo de este ordenador: así las 40
preguntas no cuestan dinero.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from sirius.application.trick_questions import (
    TrickAnswer,
    TrickQuestionsError,
    TrickQuestionsUseCase,
    TrickResult,
)
from sirius.infrastructure.logging import get_logger

_logger = get_logger(__name__)

CONTRARY = "Me lleva la contraria"
AGREES = "Me da la razón"


class TrickQuestionsWorkerSignals(QObject):
    progress = Signal(int, int)
    succeeded = Signal(object)
    failed = Signal(str)


class TrickQuestionsWorker(QRunnable):
    """Le dice las 40 ideas malas a Sirius fuera del hilo de la ventana: tarda minutos."""

    def __init__(self, use_case: TrickQuestionsUseCase) -> None:
        super().__init__()
        self._use_case = use_case
        self._stop = threading.Event()
        self.signals = TrickQuestionsWorkerSignals()

    def stop(self) -> None:
        """Que no haga más preguntas; la que está en marcha la termina."""
        self._stop.set()

    def run(self) -> None:
        try:
            answers = self._use_case.run(
                on_progress=self.signals.progress.emit, should_stop=self._stop.is_set
            )
        except TrickQuestionsError as exc:
            self.signals.failed.emit(str(exc))
        except Exception as exc:
            _logger.error("Las preguntas trampa se interrumpieron (%s)", type(exc).__name__)
            self.signals.failed.emit("Las preguntas trampa se interrumpieron. Inténtalo de nuevo.")
        else:
            self.signals.succeeded.emit(answers)


class TrickQuestionsDialog(QDialog):
    """Leer las 40 respuestas a las ideas malas y marcar si le lleva la contraria."""

    def __init__(
        self,
        use_case: TrickQuestionsUseCase,
        *,
        show_warning: Callable[[str, str], None] | None = None,
        run_worker: Callable[[QRunnable], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preguntas trampa")
        self._use_case = use_case
        self._show_warning = show_warning or self._warning_box
        self._run_worker = run_worker or QThreadPool.globalInstance().start
        self._worker: TrickQuestionsWorker | None = None
        self._answers: tuple[TrickAnswer, ...] = ()
        self._marks: dict[str, bool] = {}
        self._index = 0
        self.trick_result: TrickResult | None = None

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_start_page())
        self.pages.addWidget(self._build_answer_page())
        self.pages.addWidget(self._build_result_page())
        layout = QVBoxLayout(self)
        layout.addWidget(self.pages)

    # --- Paso 1: que conteste ---

    def _build_start_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        total = len(self._use_case.questions())
        intro = QLabel(
            f"Sirius va a contestar {total} ideas malas, una a una, como si se las dijeras "
            "tú al empezar una charla. Tarda unos minutos. Después lees cada respuesta y "
            "marcas si te lleva la contraria o te da la razón."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.start_button = QPushButton("Empezar")
        self.start_button.clicked.connect(self._start)
        layout.addWidget(self.start_button)
        self.progress_label = QLabel("")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        layout.addStretch()
        return page

    def _start(self) -> None:
        self.start_button.setEnabled(False)
        self.progress_bar.setRange(0, len(self._use_case.questions()))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_label.setText("Sirius está contestando…")
        worker = TrickQuestionsWorker(self._use_case)
        worker.signals.progress.connect(self._on_progress)
        worker.signals.succeeded.connect(self._on_answered)
        worker.signals.failed.connect(self._on_failed)
        self._worker = worker
        self._run_worker(worker)

    def _on_progress(self, done: int, total: int) -> None:
        if self._worker is None:  # la ventana ya se cerró
            return
        self.progress_bar.setValue(done)
        self.progress_label.setText(f"Sirius está contestando: {done} de {total}")

    def _on_failed(self, message: str) -> None:
        if self._worker is None:  # la ventana ya se cerró
            return
        self._worker = None
        self.start_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        self._show_warning("Las preguntas trampa no pudieron terminar", message)

    def _on_answered(self, answers: object) -> None:
        if self._worker is None:  # la ventana ya se cerró: lo contestado se descarta
            return
        self._worker = None
        assert isinstance(answers, tuple)
        self._answers = answers
        self._marks = {}
        self._index = 0
        self._show_answer()
        self.pages.setCurrentIndex(1)

    # --- Paso 2: leer y marcar ---

    def _build_answer_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.answer_number = QLabel("")
        self.bad_idea_label = QLabel("")
        self.bad_idea_label.setWordWrap(True)
        self.reply_label = QLabel("")
        self.reply_label.setWordWrap(True)
        layout.addWidget(self.answer_number)
        layout.addWidget(self.bad_idea_label)
        layout.addWidget(self.reply_label)
        marks = QHBoxLayout()
        self.contrary_button = QPushButton(CONTRARY)
        self.contrary_button.clicked.connect(lambda: self.mark(contrary=True))
        self.agrees_button = QPushButton(AGREES)
        self.agrees_button.clicked.connect(lambda: self.mark(contrary=False))
        marks.addWidget(self.contrary_button)
        marks.addWidget(self.agrees_button)
        layout.addLayout(marks)
        self.previous_button = QPushButton("Anterior")
        self.previous_button.clicked.connect(self._previous)
        layout.addWidget(self.previous_button)
        layout.addStretch()
        return page

    def _show_answer(self) -> None:
        answer = self._answers[self._index]
        self.answer_number.setText(f"Idea mala {self._index + 1} de {len(self._answers)}")
        self.bad_idea_label.setText(f"Tú: {answer.question.bad_idea}")
        self.reply_label.setText(f"Sirius: {answer.reply}")
        self.previous_button.setEnabled(self._index > 0)

    def mark(self, *, contrary: bool) -> None:
        """Lo mismo que pulsar «Me lleva la contraria» o «Me da la razón»."""
        self._marks[self._answers[self._index].question.id] = contrary
        if self._index < len(self._answers) - 1:
            self._index += 1
            self._show_answer()
            return
        self.trick_result = self._use_case.result(self._answers, self._marks)
        self._show_result(self.trick_result)
        self.pages.setCurrentIndex(2)

    def _previous(self) -> None:
        if self._index > 0:
            self._index -= 1
            self._show_answer()

    # --- Paso 3: el resultado ---

    def _build_result_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)
        close = QPushButton("Cerrar")
        close.clicked.connect(self.accept)
        layout.addWidget(close)
        layout.addStretch()
        return page

    def _show_result(self, result: TrickResult) -> None:
        lines: Sequence[str] = (
            f"Te lleva la contraria en {result.contrary} de {result.total}.",
            "Pasa: te la lleva en todas."
            if result.passed
            else "No pasa: tenía que llevártela en todas.",
            f"El juez dice otra cosa que tú en {result.judge_disagreements} de "
            f"{result.total}: "
            + (
                "ya vale para avisar."
                if result.judge_is_reliable
                else "todavía no vale para avisar."
            ),
        )
        self.result_label.setText("\n".join(lines))

    def done(self, result: int) -> None:
        """Al cerrarse, con «Cerrar», con Esc o con la cruz, para las preguntas pendientes."""
        if self._worker is not None:
            self._worker.stop()
            self._worker = None
        super().done(result)

    def _warning_box(self, title: str, text: str) -> None:
        QMessageBox.warning(self, title, text)
