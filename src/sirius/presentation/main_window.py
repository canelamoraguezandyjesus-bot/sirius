"""Ventana principal de Sirius 0.1."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QPoint, QRunnable, Qt, QThreadPool, QTimer, QUrl, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from sirius.application.api_key_settings import ApiKeySettingsError, ApiKeySettingsUseCase
from sirius.application.approve_decision import ApproveDecisionUseCase
from sirius.application.archive_decision import ArchiveDecisionUseCase
from sirius.application.archive_memory import ArchiveMemoryUseCase
from sirius.application.budget_status import GetBudgetStatusUseCase
from sirius.application.capture_commands import CaptureCommand, CaptureIntent, interpret
from sirius.application.capture_replies import spoken_confirmation
from sirius.application.correct_memory import CorrectMemoryUseCase
from sirius.application.create_backup import CreateBackupUseCase
from sirius.application.decision_origin import GetDecisionOriginUseCase
from sirius.application.delete_memory import DeleteMemoryUseCase
from sirius.application.detect_precedence_conflicts import DetectPrecedenceConflictsUseCase
from sirius.application.export_structured import ExportStructuredUseCase
from sirius.application.get_conversation_history import (
    ConversationNotInitializedError,
    GetConversationHistoryUseCase,
)
from sirius.application.knowledge_overview import GetKnowledgeOverviewUseCase
from sirius.application.memory_origin import GetMemoryOriginUseCase
from sirius.application.project_continuity import ProjectContinuityUseCase
from sirius.application.project_errors import ProjectContinuityError
from sirius.application.project_lifecycle import ProjectLifecycleUseCase
from sirius.application.propose_decision import ProposeDecisionUseCase
from sirius.application.restore_backup import RestoreBackupUseCase
from sirius.application.save_manual_memory import SaveManualMemoryUseCase
from sirius.application.send_message import SendMessageResult, SendMessageUseCase
from sirius.application.studio_brief import MODEL_STUDIO_BRIEF
from sirius.application.studio_capture import CaptureFeedback, StudioCaptureUseCase
from sirius.application.studio_voice import (
    ListeningStarted,
    NothingToSay,
    SpeechStarted,
    StudioVoiceUseCase,
    TranscriptReady,
    VoiceFailure,
)
from sirius.application.supersede_decision import SupersedeDecisionUseCase
from sirius.application.validate_backup import ValidateBackupUseCase
from sirius.config.llm_provider_settings import (
    LLMProviderConfigurationError,
    LLMProviderKind,
    resolve_openai_provider_settings,
    resolve_provider_kind,
)
from sirius.config.settings import load_settings, save_settings
from sirius.domain.capture import SceneRegistry
from sirius.domain.conversation import MessageRole, MessageStatus
from sirius.domain.model_studio import StudioCaptureState, StudioInteractionState
from sirius.infrastructure.logging import get_logger
from sirius.ports.backup import (
    BackupManifest,
    BackupRestoreResult,
    BackupResult,
    BackupValidationResult,
)
from sirius.presentation.backup_worker import (
    CreateBackupWorker,
    RestoreBackupWorker,
    ValidateBackupWorker,
)
from sirius.presentation.context_panel_widget import ContextPanelWidget
from sirius.presentation.conversation_worker import SendMessageWorker
from sirius.presentation.error_messages import failed_send_message
from sirius.presentation.export_worker import ExportWorker
from sirius.presentation.knowledge_widget import KnowledgeWidget
from sirius.presentation.message_view import MessageItemDelegate, MessageItemWidget
from sirius.presentation.model_studio.settings_dialog import StudioSettingsDialog
from sirius.presentation.model_studio.studio_page import StudioPage
from sirius.presentation.project_continuity_widget import ProjectContinuityWidget
from sirius.presentation.studio_workers import CaptureWorker, SpeakWorker, TranscribeWorker

_logger = get_logger(__name__)

# Reparto inicial de la pestaña de conversación. La conversación es la
# superficie principal de Sirius, así que arranca con una proporción claramente
# mayor y con un ancho mínimo por debajo del cual no se la puede estrechar; la
# columna lateral tiene un tope razonable y el usuario puede plegarla.
_CONVERSATION_MINIMUM_WIDTH = 420
_CONVERSATION_INITIAL_WIDTH = 760
_SIDE_PANEL_INITIAL_WIDTH = 300
_SIDE_PANEL_MAXIMUM_WIDTH = 420

# Margen para considerar que la vista está «al final» del historial: el usuario
# que está leyendo el último mensaje no siempre queda en el píxel exacto.
_AT_BOTTOM_TOLERANCE_PX = 8

# Páginas del widget central. Model Studio no sustituye la interfaz técnica:
# convive con ella y se conmuta.
TECHNICAL_PAGE_INDEX = 0
MODEL_STUDIO_PAGE_INDEX = 1

VOICE_PREVIEW_TEXT = "Hola. Soy Sirius, y esta es mi voz. Uno, dos, tres."
"""Frase de prueba al elegir voz.

Corta y con números: lo que distingue una voz de otra al oírlas seguidas es la
entonación de una frase normal, no un párrafo.
"""

EARLY_SPEECH_MINIMUM_CHARACTERS = 60
"""Cuánto tiene que haber escrito Sirius para empezar a hablar sin terminar.

Grabando, esperar a la respuesta entera y encima a que se fabrique la voz son
dos esperas seguidas mirando a la cámara. Con esto la primera se solapa con la
segunda.

Sesenta caracteres, y siempre cortando en final de frase: un trozo más corto
suele ser un «Sí.» suelto que no gana nada, y partir a mitad de frase sonaría
a corte. Se parte **una sola vez** por respuesta: el resto va entero al acabar,
así que son dos peticiones y no diez, y el coste total no cambia.
"""

_SENTENCE_ENDINGS = (". ", "! ", "? ", ".\n", "!\n", "?\n")

CAPTURE_HEARTBEAT_MILLISECONDS = 5_000
"""Cada cuánto se le pregunta a OBS cómo está mientras el panel está abierto.

Cinco segundos es el compromiso: lo bastante corto para que un OBS cerrado se
note enseguida —y no veinte minutos después—, y lo bastante largo para que no
sea un goteo constante de peticiones mientras se graba.
"""

# Estados con los que termina cualquier operación de copia de seguridad. Se
# guardan además en la propiedad ``siriusBackupState`` de la etiqueta que los
# muestra: el texto es para la persona, la propiedad es el estado en sí, que ni
# depende de la redacción ni se pierde al reescribir un mensaje.
BACKUP_STATE_IN_PROGRESS = "en curso"
BACKUP_STATE_CREATED = "creada"
BACKUP_STATE_VALIDATED = "validada"
BACKUP_STATE_RESTORED = "restaurada"
BACKUP_STATE_CANCELLED = "cancelada"
BACKUP_STATE_REJECTED = "rechazada"

#: Nombre de la propiedad Qt donde vive el estado, legible desde las pruebas.
BACKUP_STATE_PROPERTY = "siriusBackupState"

# Cada estado se distingue también por color, no solo por el texto: en curso y
# cancelada son neutros (nada ha cambiado), creada/validada/restaurada
# confirman, y rechazada avisa.
_BACKUP_STATE_STYLES = {
    BACKUP_STATE_IN_PROGRESS: "color: #444444;",
    BACKUP_STATE_CREATED: "color: #1b7f3b; font-weight: bold;",
    BACKUP_STATE_VALIDATED: "color: #1b7f3b; font-weight: bold;",
    BACKUP_STATE_RESTORED: "color: #1b7f3b; font-weight: bold;",
    BACKUP_STATE_CANCELLED: "color: #8a6d00; font-weight: bold;",
    BACKUP_STATE_REJECTED: "color: #b3261e; font-weight: bold;",
}


def _first_sentence_end(text: str) -> int | None:
    """Dónde acaba la primera frase, si ya hay bastante como para hablar.

    Devuelve ``None`` mientras no haya un final de frase pasado el mínimo:
    partir a mitad de frase sonaría a corte, y adelantar tres palabras no
    ahorra ninguna espera.
    """
    if len(text) < EARLY_SPEECH_MINIMUM_CHARACTERS:
        return None
    cortes = [
        text.find(final, EARLY_SPEECH_MINIMUM_CHARACTERS - 1) + len(final)
        for final in _SENTENCE_ENDINGS
        if text.find(final, EARLY_SPEECH_MINIMUM_CHARACTERS - 1) != -1
    ]
    return min(cortes) if cortes else None


class MainWindow(QMainWindow):
    """Ventana principal de Sirius: conversación y configuración.

    Never receives a ``SecretStore`` and never calls ``get_secret``: the only
    secret-related dependency it holds is ``ApiKeySettingsUseCase``, whose
    API cannot return the key's value (AGENTS.md: "No accedas a ... secretos
    desde la interfaz").

    Emits ``project_completed`` exactly once, right after
    ``ProjectContinuityWidget`` reports the active project was actually
    completed (RF-018). The caller (``sirius.main``) is responsible for
    closing this window and opening ``InitialProjectWindow`` next — this
    window never creates a replacement project itself.
    """

    project_completed = Signal()

    def __init__(
        self,
        send_message_use_case: SendMessageUseCase,
        get_history_use_case: GetConversationHistoryUseCase,
        get_budget_status_use_case: GetBudgetStatusUseCase,
        api_key_settings_use_case: ApiKeySettingsUseCase,
        project_continuity_use_case: ProjectContinuityUseCase,
        project_lifecycle_use_case: ProjectLifecycleUseCase,
        save_manual_memory_use_case: SaveManualMemoryUseCase,
        get_memory_origin_use_case: GetMemoryOriginUseCase,
        correct_memory_use_case: CorrectMemoryUseCase,
        archive_memory_use_case: ArchiveMemoryUseCase,
        delete_memory_use_case: DeleteMemoryUseCase,
        propose_decision_use_case: ProposeDecisionUseCase,
        approve_decision_use_case: ApproveDecisionUseCase,
        get_decision_origin_use_case: GetDecisionOriginUseCase,
        supersede_decision_use_case: SupersedeDecisionUseCase,
        archive_decision_use_case: ArchiveDecisionUseCase,
        detect_precedence_conflicts_use_case: DetectPrecedenceConflictsUseCase,
        get_knowledge_overview_use_case: GetKnowledgeOverviewUseCase,
        create_backup_use_case: CreateBackupUseCase,
        validate_backup_use_case: ValidateBackupUseCase,
        restore_backup_use_case: RestoreBackupUseCase,
        export_structured_use_case: ExportStructuredUseCase,
        close_database_connections: Callable[[], None],
        *,
        studio_voice_use_case: StudioVoiceUseCase | None = None,
        studio_capture_use_case: StudioCaptureUseCase | None = None,
        save_studio_voice: Callable[[str], None] | None = None,
        show_warning: Callable[[str, str], None] | None = None,
        show_information: Callable[[str, str], None] | None = None,
        confirm_restore: Callable[[str, str], bool] | None = None,
        choose_backup_file: Callable[[str], str] | None = None,
        open_containing_folder: Callable[[Path], None] | None = None,
        confirm_export: Callable[[str, str], bool] | None = None,
        choose_export_directory: Callable[[str], str] | None = None,
    ) -> None:
        super().__init__()
        self._send_message_use_case = send_message_use_case
        self._get_history_use_case = get_history_use_case
        self._get_budget_status_use_case = get_budget_status_use_case
        self._api_key_settings_use_case = api_key_settings_use_case
        self._project_continuity_use_case = project_continuity_use_case
        self._project_lifecycle_use_case = project_lifecycle_use_case
        self._save_manual_memory_use_case = save_manual_memory_use_case
        self._get_memory_origin_use_case = get_memory_origin_use_case
        self._correct_memory_use_case = correct_memory_use_case
        self._archive_memory_use_case = archive_memory_use_case
        self._delete_memory_use_case = delete_memory_use_case
        self._propose_decision_use_case = propose_decision_use_case
        self._approve_decision_use_case = approve_decision_use_case
        self._get_decision_origin_use_case = get_decision_origin_use_case
        self._supersede_decision_use_case = supersede_decision_use_case
        self._archive_decision_use_case = archive_decision_use_case
        self._detect_precedence_conflicts_use_case = detect_precedence_conflicts_use_case
        self._get_knowledge_overview_use_case = get_knowledge_overview_use_case
        self._create_backup_use_case = create_backup_use_case
        self._validate_backup_use_case = validate_backup_use_case
        self._restore_backup_use_case = restore_backup_use_case
        self._export_structured_use_case = export_structured_use_case
        # Not a use case: the minimal SQLAlchemy-lifecycle mechanism a safe
        # restoration needs (see ConversationDependencies' docstring). Called
        # right before RestoreBackupUseCase so the atomic file replace is not
        # blocked by this window's own pooled connections.
        self._close_database_connections = close_database_connections
        self._studio_voice_use_case = studio_voice_use_case
        self._studio_capture_use_case = studio_capture_use_case
        self._last_spoken_text: str | None = None
        self._voice_before_preview: str | None = None
        # Cola de voz: el audio tiene que sonar en el orden en que se escribió,
        # así que solo se sintetiza un trozo a la vez y el siguiente espera a
        # que el anterior termine de sonar.
        self._speech_queue: list[tuple[str, bool]] = []
        self._speech_busy = False
        self._spoken_prefix_length = 0
        self._early_speech_used = False
        # La voz elegida tiene que sobrevivir al cierre: la raíz de composición
        # pasa cómo guardarla, porque la ventana no toca la configuración.
        self._save_studio_voice = save_studio_voice
        self._active_voice_worker: QRunnable | None = None
        self._active_capture_worker: QRunnable | None = None
        self._capture_busy = False
        self._capture_turn = 0
        self._pending_capture_command: CaptureCommand | None = None
        # Latido del Módulo Captura: preguntarle a OBS cada pocos segundos es
        # lo único que permite enterarse de que se ha caído sin esperar a la
        # siguiente orden. Solo corre con el panel abierto.
        self._capture_heartbeat = QTimer(self)
        self._capture_heartbeat.setInterval(CAPTURE_HEARTBEAT_MILLISECONDS)
        self._capture_heartbeat.timeout.connect(self._poll_capture_state)
        # Dialogs are shown only through these seams: production defaults to
        # real Qt dialogs, but tests inject recording/no-op doubles so
        # scripts/check.ps1 never opens a real window on the desktop.
        self._show_warning = show_warning or self._default_show_warning
        self._show_information = show_information or self._default_show_information
        self._confirm_restore = confirm_restore or self._default_confirm_restore
        self._choose_backup_file = choose_backup_file or self._default_choose_backup_file
        self._open_containing_folder = (
            open_containing_folder or self._default_open_containing_folder
        )
        self._confirm_export = confirm_export or self._default_confirm_export
        self._choose_export_directory = (
            choose_export_directory or self._default_choose_export_directory
        )
        self._is_sending = False
        self._is_backup_busy = False
        self._is_export_busy = False
        self._close_requested = False
        # Ruta de la última copia creada en esta sesión. Es lo que permite
        # abrir su carpeta, reutilizarla sin volver a buscarla a mano y
        # arrancar el selector de archivos donde de verdad está la copia.
        self._last_backup_path: Path | None = None
        # Etiqueta cuyo desplazamiento está pendiente de que el diseño
        # termine de converger (ver _scroll_settings_to).
        self._pending_feedback_label: QLabel | None = None
        self._active_operation_id: str | None = None
        self._streaming_item: QListWidgetItem | None = None
        self._streaming_text = ""
        # El historial arranca siguiendo el final: al abrir, lo útil es lo
        # último dicho. Deja de seguirlo si el usuario se desplaza hacia arriba.
        self._follow_history_bottom = True
        self._scrolling_history = False
        # B7b: text of the in-flight send (for _on_crashed, which has no
        # SendMessageResult to read it back from) and, once a send ends in
        # FAILED/crashed, the text "Reintentar" resends unchanged (RF-007).
        self._active_send_text: str | None = None
        self._last_failed_text: str | None = None
        # QThreadPool.start() does not keep a Python-level reference to a
        # QRunnable: without this, a worker whose run() finishes very
        # quickly can be garbage-collected before its queued cross-thread
        # signal is delivered, silently losing the result. Cleared once the
        # in-flight operation's slot has run. Kept separate per worker kind:
        # a send and a backup operation never run concurrently, but each
        # slot must only ever clear its own worker.
        self._active_send_worker: QRunnable | None = None
        self._active_backup_worker: QRunnable | None = None
        self._active_export_worker: QRunnable | None = None
        self._thread_pool = QThreadPool()

        self.setWindowTitle("Sirius 0.1")
        self.resize(900, 620)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_conversation_tab(), "Conversación")
        self.tabs.addTab(self._build_knowledge_tab(), "Memoria y decisiones")
        self.tabs.addTab(self._build_settings_tab(), "Configuración")

        # Model Studio es una página conmutable de esta misma ventana, no una
        # segunda aplicación (SIRIUS-MODEL-STUDIO-UI-001 §2): mismo proceso,
        # misma base de datos y los mismos casos de uso. La interfaz técnica
        # queda intacta en la página 0 y conmutar oculta por completo la barra
        # de pestañas, que es lo que da el modo limpio de §9.1 sin trucos.
        self._pages = QStackedWidget()
        self._pages.addWidget(self._build_technical_page())
        self._pages.addWidget(self._build_studio_page())
        self.setCentralWidget(self._pages)

        self._load_history()
        self._refresh_studio_context()

    def _default_show_warning(self, title: str, text: str) -> None:
        QMessageBox.warning(self, title, text)

    def _default_show_information(self, title: str, text: str) -> None:
        QMessageBox.information(self, title, text)

    def _default_confirm_restore(self, title: str, text: str) -> bool:
        answer = QMessageBox.question(
            self,
            title,
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _default_choose_backup_file(self, title: str) -> str:
        # Arranca en la carpeta de la última copia creada en esta sesión: sin
        # esto el selector abre en un directorio cualquiera y encontrar la
        # copia recién hecha depende de que la persona recuerde su ruta.
        start_directory = ""
        if self._last_backup_path is not None:
            start_directory = str(self._last_backup_path.parent)
        path_text, _ = QFileDialog.getOpenFileName(
            self, title, start_directory, "Copias de Sirius (*.siriusbackup)"
        )
        return path_text

    def _default_open_containing_folder(self, path: Path) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))

    def _default_confirm_export(self, title: str, text: str) -> bool:
        answer = QMessageBox.question(
            self,
            title,
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _default_choose_export_directory(self, title: str) -> str:
        return QFileDialog.getExistingDirectory(self, title)

    # --- Conversación --------------------------------------------------

    # --- Model Studio ----------------------------------------------------

    def _build_technical_page(self) -> QWidget:
        """Página 0: la interfaz de siempre, con el acceso a Model Studio arriba.

        El contenido no cambia en nada; solo se le antepone el botón que abre
        la superficie de grabación.
        """
        self.open_studio_button = QPushButton("Model Studio")
        self.open_studio_button.setToolTip(
            "Abrir la superficie audiovisual de Sirius, pensada para grabar."
        )
        self.open_studio_button.setAccessibleName("Abrir Model Studio")
        self.open_studio_button.clicked.connect(self.open_model_studio)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addStretch(1)
        header.addWidget(self.open_studio_button)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(6, 6, 6, 0)
        layout.setSpacing(6)
        layout.addLayout(header)
        layout.addWidget(self.tabs, 1)
        return page

    def _build_studio_page(self) -> QWidget:
        """Página 1: Model Studio.

        La página es solo una vista: recibe la conversación ya resuelta por
        esta ventana y devuelve intenciones por señales. No conoce casos de
        uso ni proveedores, así que conectar después la voz o la captura no
        obliga a tocarla.
        """
        self.studio_page = StudioPage()
        self.studio_page.send_requested.connect(self._handle_studio_send)
        self.studio_page.cancel_requested.connect(self._handle_cancel_clicked)
        self.studio_page.exit_requested.connect(self.close_model_studio)
        self.studio_page.microphone_clicked.connect(self._handle_microphone_clicked)
        self.studio_page.stop_voice_clicked.connect(self._handle_stop_voice_clicked)
        self.studio_page.repeat_clicked.connect(self._handle_repeat_clicked)
        self.studio_page.read_all_clicked.connect(self._handle_read_all_clicked)
        self.studio_page.settings_clicked.connect(self._handle_studio_settings_clicked)
        self.studio_page.mute_toggled.connect(self._handle_mute_toggled)
        self.studio_page.set_voice_available(
            self._studio_voice_use_case is not None,
            "todavía no disponible",
        )
        if self._studio_voice_use_case is not None:
            self._studio_voice_use_case.set_speech_finished_callback(self._on_speech_finished)

        self.studio_page.capture_panel_toggled.connect(self._handle_capture_panel_toggled)
        self.studio_page.emergency_stop_clicked.connect(self._handle_emergency_stop)
        self.studio_page.capture_panel.record_clicked.connect(self._handle_record_clicked)
        self.studio_page.capture_panel.stop_clicked.connect(self._handle_stop_recording_clicked)
        self.studio_page.capture_panel.pause_clicked.connect(self._handle_pause_clicked)
        self.studio_page.capture_panel.resume_clicked.connect(self._handle_resume_clicked)
        self.studio_page.capture_panel.mark_clicked.connect(self._handle_mark_clicked)
        self.studio_page.capture_panel.scene_selected.connect(self._handle_scene_selected)
        self.studio_page.set_capture_available(
            self._studio_capture_use_case is not None,
            "todavía no disponible",
        )
        if self._studio_capture_use_case is not None:
            self.studio_page.capture_panel.set_scenes(
                [
                    (scene.scene_id, scene.display_name)
                    for scene in self._studio_capture_use_case.authorized_scenes()
                ]
            )
        return self.studio_page

    # --- Captura de Model Studio ------------------------------------------

    def _handle_capture_panel_toggled(self, opened: bool) -> None:
        """Abrir el panel enciende el módulo; cerrarlo lo apaga y desconecta.

        Encenderlo no es grabar: solo conecta y pregunta el estado. Y apagarlo
        no detiene nada de lo que ya estuviera grabando.
        """
        if self._studio_capture_use_case is None:
            return
        # Abrir el panel es empezar de cero: se limpia lo que quedara dicho.
        self.studio_page.capture_panel.set_message("")
        use_case = self._studio_capture_use_case
        self._run_capture(use_case.enable if opened else use_case.disable)
        if opened:
            self._capture_heartbeat.start()
        else:
            self._capture_heartbeat.stop()

    def _poll_capture_state(self) -> None:
        """Le pregunta a OBS cómo está, sin que nadie haya dado una orden.

        Sin esto, Sirius solo se entera de que OBS se ha caído la próxima vez
        que le mandas algo: si cierras OBS sin querer y sigues hablando, la
        barra seguiría diciendo GRABANDO durante veinte minutos. #127 lo dice
        con todas las letras —el sistema de captura es la autoridad—, y una
        autoridad a la que no se pregunta no manda nada.

        Se salta sola si ya hay una orden en vuelo: la respuesta de esa orden
        trae el estado igualmente y preguntar dos veces no aporta.
        """
        use_case = self._studio_capture_use_case
        if use_case is None or self._capture_busy or not use_case.is_enabled:
            return
        self._run_capture(use_case.refresh_status)

    def _handle_record_clicked(self) -> None:
        self._run_capture_command("start_recording")

    def _handle_stop_recording_clicked(self) -> None:
        self._run_capture_command("stop_recording")

    def _handle_pause_clicked(self) -> None:
        self._run_capture_command("pause_recording")

    def _handle_resume_clicked(self) -> None:
        self._run_capture_command("resume_recording")

    def _handle_mark_clicked(self) -> None:
        self._run_capture_command("mark_moment")

    def _handle_scene_selected(self, scene_id: str) -> None:
        if self._studio_capture_use_case is None:
            return
        use_case = self._studio_capture_use_case
        self._run_capture(lambda: use_case.switch_scene(scene_id))

    def _handle_emergency_stop(self) -> None:
        """Corta la grabación de inmediato, sin preguntar nada antes."""
        if self._studio_capture_use_case is None:
            return
        self._run_capture(self._studio_capture_use_case.emergency_stop)

    def _run_capture_command(self, name: str) -> None:
        if self._studio_capture_use_case is None:
            return
        self._run_capture(getattr(self._studio_capture_use_case, name))

    def _run_capture(self, command: Callable[[], CaptureFeedback]) -> None:
        """Ejecuta una orden de captura, de una en una.

        Dos órdenes a la vez pueden terminar en orden distinto al que se
        pidieron y dejar el módulo en un estado que nadie eligió —encender y
        apagar deprisa es lo fácil de hacer sin querer—. Mientras hay una en
        vuelo, las nuevas se descartan; al terminar, ``_sync_capture_module``
        comprueba si el módulo quedó como el usuario pidió y lo corrige.
        """
        if self._capture_busy:
            return
        self._capture_busy = True
        worker = CaptureWorker(command)
        worker.signals.finished.connect(self._on_capture_finished)
        worker.signals.crashed.connect(self._on_capture_crashed)
        self._active_capture_worker = worker
        self._thread_pool.start(worker)

    def _on_capture_finished(self, feedback: object) -> None:
        self._active_capture_worker = None
        self._capture_busy = False
        if not isinstance(feedback, CaptureFeedback):
            return
        # El estado que se pinta es el que devolvió el backend, nunca uno
        # supuesto: por eso se adopta tal cual y no se corrige aquí.
        self.studio_page.set_capture_state(feedback.state)
        self.studio_page.capture_panel.set_elapsed(feedback.recording_seconds)
        if feedback.message:
            # Solo se pisa el mensaje si hay algo nuevo que decir. La orden
            # correctora de _sync_capture_module no trae mensaje, y sin este
            # guardia borraría un rechazo justo después de enseñarlo.
            self.studio_page.capture_panel.set_message(feedback.message)
        if feedback.scene_id is not None:
            self.studio_page.capture_panel.set_active_scene(feedback.scene_id)
        if self.studio_page.interaction_state is StudioInteractionState.EJECUTANDO:
            # La orden vino hablada o escrita: el usuario espera respuesta.
            self._mirror_studio_state(StudioInteractionState.PREPARADO)
            self._announce_capture(feedback)
            self._capture_turn += 1
        self._sync_capture_module()

    def _announce_capture(self, feedback: CaptureFeedback) -> None:
        """Cuenta cómo quedó la orden: en pantalla y, si hay voz, en voz alta.

        Lo que se anuncia es el estado que devolvió el sistema de captura, no
        una frase compuesta por el modelo. Es la diferencia entre informar y
        afirmar algo que nadie ha confirmado.
        """
        spoken = (
            spoken_confirmation(self._pending_capture_command, feedback, self._capture_turn)
            if self._pending_capture_command is not None
            else feedback.message or feedback.state.label
        )
        if not feedback.succeeded:
            self.studio_page.set_error(spoken)
        self._speak_if_studio_is_open(spoken, MessageStatus.COMPLETED)

    def _sync_capture_module(self) -> None:
        """Corrige el módulo si quedó al revés de lo que el usuario pidió.

        Pasa cuando se abre y se cierra el panel más deprisa de lo que tarda
        una orden: la segunda se descartó, y aquí se vuelve a emitir.
        """
        if self._studio_capture_use_case is None or self._capture_busy:
            return
        wanted = self.studio_page.capture_panel_open
        if wanted == self._studio_capture_use_case.is_enabled:
            return
        use_case = self._studio_capture_use_case
        self._run_capture(use_case.enable if wanted else use_case.disable)

    def _on_capture_crashed(self, error_message: str) -> None:
        del error_message  # el mensaje al usuario es seguro y genérico
        self._capture_busy = False
        self.studio_page.set_capture_state(StudioCaptureState.INCIERTO)
        self.studio_page.capture_panel.set_message(
            "No sé cómo ha quedado la grabación. Vuelve a abrir el panel para comprobarlo."
        )

    # --- Voz de Model Studio ---------------------------------------------

    def _handle_microphone_clicked(self) -> None:
        """Un clic empieza a escuchar; otro para y transcribe.

        No hay que mantener nada pulsado (decisión del usuario del 7 de agosto
        de 2026): grabando el montaje de HEAD-R1 no se tiene una mano libre
        para sujetar el ratón.
        """
        if self._studio_voice_use_case is None or self._is_sending:
            return
        if self._studio_voice_use_case.is_listening:
            self._stop_listening_and_transcribe()
            return

        outcome = self._studio_voice_use_case.start_listening()
        if isinstance(outcome, VoiceFailure):
            self._report_voice_failure(outcome)
            return
        if isinstance(outcome, ListeningStarted):
            self.studio_page.set_error("")
            self._mirror_studio_state(StudioInteractionState.ESCUCHANDO)

    def _stop_listening_and_transcribe(self) -> None:
        if self._studio_voice_use_case is None:
            return
        self._mirror_studio_state(StudioInteractionState.TRANSCRIBIENDO)
        worker = TranscribeWorker(self._studio_voice_use_case)
        worker.signals.finished.connect(self._on_transcribed)
        worker.signals.crashed.connect(self._on_voice_crashed)
        self._active_voice_worker = worker
        self._thread_pool.start(worker)

    def _on_transcribed(self, outcome: object) -> None:
        self._active_voice_worker = None
        if isinstance(outcome, VoiceFailure):
            self._report_voice_failure(outcome)
            return
        if not isinstance(outcome, TranscriptReady):
            return

        # Nada se persiste todavía: el texto va a la caja para que el usuario
        # lo corrija, lo cancele o lo envíe. Solo al enviar entra en la
        # conversación.
        self.studio_page.set_input_text(outcome.text)
        self._mirror_studio_state(StudioInteractionState.REVISANDO)
        self.studio_page.set_error(
            "Se alcanzó el máximo de grabación; revisa el texto antes de enviarlo."
            if outcome.stopped_by_limit
            else ""
        )

    def _speak_if_studio_is_open(self, text: str | None, status: MessageStatus) -> None:
        """Lee la respuesta en voz alta, solo dentro de Model Studio.

        En la interfaz técnica no se habla: nadie espera que un chat de trabajo
        empiece a sonar solo.
        """
        if self._studio_voice_use_case is None or not self.model_studio_open:
            self._reset_speech_stream()
            return
        if not text or status is not MessageStatus.COMPLETED:
            # Cancelada o fallida: si ya se había empezado a leer, se calla.
            self._silence_pending_speech()
            return
        self._last_spoken_text = text
        pendiente = text[self._spoken_prefix_length :] if self._early_speech_used else text
        self._reset_speech_stream()
        if pendiente.strip():
            self._enqueue_speech(pendiente)

    def _reset_speech_stream(self) -> None:
        self._spoken_prefix_length = 0
        self._early_speech_used = False

    def _silence_pending_speech(self) -> None:
        """Deja de leer una respuesta que se canceló o falló a mitad."""
        self._speech_queue.clear()
        self._reset_speech_stream()
        if self._studio_voice_use_case is not None:
            self._studio_voice_use_case.stop_speaking()
        self._speech_busy = False

    def _enqueue_speech(self, text: str, *, read_code: bool = False) -> None:
        self._speech_queue.append((text, read_code))
        self._pump_speech()

    def _pump_speech(self) -> None:
        """Saca el siguiente trozo, solo si no hay ninguno sonando."""
        if self._speech_busy or not self._speech_queue:
            return
        text, read_code = self._speech_queue.pop(0)
        self._speech_busy = True
        self._start_speaking(text, MessageStatus.COMPLETED, read_code=read_code)

    def _start_speaking(self, text: str, status: MessageStatus, *, read_code: bool = False) -> None:
        if self._studio_voice_use_case is None:
            return
        self._mirror_studio_state(StudioInteractionState.SINTETIZANDO)
        worker = SpeakWorker(self._studio_voice_use_case, text, status, read_code=read_code)
        worker.signals.finished.connect(self._on_spoken)
        worker.signals.crashed.connect(self._on_voice_crashed)
        self._active_voice_worker = worker
        self._thread_pool.start(worker)

    def _on_spoken(self, outcome: object) -> None:
        self._active_voice_worker = None
        if isinstance(outcome, VoiceFailure):
            # Un fallo de voz no puede dejar la cola atascada para siempre.
            self._speech_busy = False
            self._speech_queue.clear()
            self._report_voice_failure(outcome)
            return
        if isinstance(outcome, SpeechStarted):
            self._mirror_studio_state(StudioInteractionState.HABLANDO)
            return
        if isinstance(outcome, NothingToSay):
            # Nada que decir de este trozo: el siguiente no tiene que esperar.
            self._speech_busy = False
            self._pump_speech()
            if not self._speech_busy:
                self._mirror_studio_state(StudioInteractionState.PREPARADO)

    def _on_speech_finished(self) -> None:
        """La voz terminó sola: se vuelve a PREPARADO.

        Solo desde ``HABLANDO``. Si mientras sonaba ya se estaba pensando otra
        respuesta o escuchando el micrófono, ese estado es el que manda: el
        final de un audio no puede pisar algo que empezó después.
        """
        self._speech_busy = False
        if self._speech_queue:
            # Queda respuesta por leer: enlaza sin volver a PREPARADO, para que
            # la barra no parpadee entre trozo y trozo.
            self._pump_speech()
            return
        if self.studio_page.interaction_state is StudioInteractionState.HABLANDO:
            self._mirror_studio_state(StudioInteractionState.PREPARADO)

    def _handle_stop_voice_clicked(self) -> None:
        if self._studio_voice_use_case is None:
            return
        self._studio_voice_use_case.stop_speaking()
        self._mirror_studio_state(StudioInteractionState.PREPARADO)

    def _handle_repeat_clicked(self) -> None:
        if self._studio_voice_use_case is None or self._last_spoken_text is None:
            return
        self._start_speaking(self._last_spoken_text, MessageStatus.COMPLETED)

    def _handle_read_all_clicked(self) -> None:
        """Lee la última respuesta **entera**, incluido el código.

        Normalmente la voz resume un bloque de código en «te dejo el código en
        pantalla», que es lo correcto casi siempre. Grabando hay un momento en
        que sí quieres oírlo, para comentarlo mientras se ve, y hasta ahora la
        única forma era leerlo tú.
        """
        if self._studio_voice_use_case is None or self._last_spoken_text is None:
            return
        self._start_speaking(self._last_spoken_text, MessageStatus.COMPLETED, read_code=True)

    def _handle_studio_settings_clicked(self) -> None:
        """Abre los ajustes rápidos: qué voz usa Sirius, probándola."""
        if self._studio_voice_use_case is None:
            return
        dialog = StudioSettingsDialog(
            voices=self._studio_voice_use_case.available_voices(),
            current=self._studio_voice_use_case.voice,
            parent=self,
        )
        dialog.test_requested.connect(self._preview_voice)
        if dialog.exec() and dialog.selected_voice:
            self._apply_studio_voice(dialog.selected_voice)
        else:
            # Cancelar no puede dejar puesta la voz que solo se estaba probando.
            self._apply_studio_voice(
                self._voice_before_preview or self._studio_voice_use_case.voice
            )

    def _preview_voice(self, voice: str) -> None:
        """Prueba una voz sin adoptarla: elegir a oído exige oírlas."""
        use_case = self._studio_voice_use_case
        if use_case is None:
            return
        if self._voice_before_preview is None:
            self._voice_before_preview = use_case.voice
        use_case.set_voice(voice)
        self._start_speaking(VOICE_PREVIEW_TEXT, MessageStatus.COMPLETED)

    def _apply_studio_voice(self, voice: str) -> None:
        use_case = self._studio_voice_use_case
        if use_case is None:
            return
        use_case.set_voice(voice)
        self._voice_before_preview = None
        if self._save_studio_voice is not None:
            self._save_studio_voice(use_case.voice)

    def _handle_mute_toggled(self, muted: bool) -> None:
        if self._studio_voice_use_case is None:
            return
        self._studio_voice_use_case.set_muted(muted)

    def _report_voice_failure(self, failure: VoiceFailure) -> None:
        """Un fallo de voz se cuenta y se sigue: el chat escrito no se toca."""
        self.studio_page.set_error(failure.message)
        self._mirror_studio_state(StudioInteractionState.ERROR)

    def _on_voice_crashed(self, error_message: str) -> None:
        del error_message  # no se muestra literal: el mensaje al usuario es seguro y genérico
        self.studio_page.set_error("La voz ha fallado, pero la conversación sigue igual.")
        self._mirror_studio_state(StudioInteractionState.ERROR)

    @property
    def model_studio_open(self) -> bool:
        return self._pages.currentIndex() == MODEL_STUDIO_PAGE_INDEX

    def open_model_studio(self) -> None:
        """Conmuta a la superficie de grabación. Idempotente."""
        self._pages.setCurrentIndex(MODEL_STUDIO_PAGE_INDEX)
        self._refresh_studio_context()
        self.studio_page.input.setFocus()

    def close_model_studio(self) -> None:
        """Vuelve a la interfaz técnica, saliendo antes del modo limpio.

        Salir corta la voz y el micrófono: nada puede seguir escuchando ni
        sonando en una superficie que ya no está a la vista.
        """
        if self.studio_page.clean_mode:
            self.studio_page.toggle_clean_mode()
        self._silence_voice()
        # Fuera de Model Studio no hay a quién enseñarle el estado, así que
        # tampoco hay motivo para seguir preguntándoselo a OBS.
        self._capture_heartbeat.stop()
        self._pages.setCurrentIndex(TECHNICAL_PAGE_INDEX)

    def _silence_voice(self) -> None:
        """Cierra micrófono y reproducción. Idempotente."""
        if self._studio_voice_use_case is None:
            return
        self._studio_voice_use_case.cancel_listening()
        self._studio_voice_use_case.stop_speaking()
        self._mirror_studio_state(StudioInteractionState.PREPARADO)

    def _handle_studio_send(self, text: str) -> None:
        """Envío pedido desde Model Studio.

        Pasa por el mismo ``_start_send`` que la interfaz técnica —y por tanto
        por el mismo ``SendMessageUseCase``, la misma identidad, la misma
        memoria y el mismo historial—, con los mismos bloqueos.
        """
        if not text.strip():
            return
        if self._is_sending or self._is_backup_busy or self._is_export_busy:
            return

        # Una orden de captura no es conversación: se ejecuta y no se guarda en
        # el historial. Lo que confirma que se está grabando es el estado que
        # devuelve el sistema de captura, no una frase del modelo.
        intent = self._capture_intent(text)
        if intent is not None:
            self._execute_capture_intent(intent)
            return
        # Grabando, una explicación de tres párrafos es un vídeo que nadie
        # termina de ver (#126). La indicación es efímera: no se guarda.
        self._start_send(text, extra_instructions=MODEL_STUDIO_BRIEF)

    def _capture_intent(self, text: str) -> CaptureIntent | None:
        """Qué orden de captura es esta frase, si es que es alguna.

        Sin Módulo Captura no hay órdenes que reconocer: todo va a la
        conversación, que es lo que el usuario espera.
        """
        if self._studio_capture_use_case is None:
            return None
        return interpret(text, SceneRegistry(self._studio_capture_use_case.authorized_scenes()))

    def _execute_capture_intent(self, intent: CaptureIntent) -> None:
        """Ejecuta la orden reconocida, por la misma vía que los botones.

        MS-017: decirlo en voz alta y pulsar el botón producen exactamente el
        mismo comando interno, con las mismas comprobaciones y la misma lista
        blanca. Aquí no hay un camino paralelo.
        """
        use_case = self._studio_capture_use_case
        if use_case is None:
            return

        self.studio_page.input.clear()
        self.studio_page.set_error("")
        self.studio_page.capture_panel.set_message("")
        self._pending_capture_command = intent.command
        self._mirror_studio_state(StudioInteractionState.EJECUTANDO)

        if intent.command is CaptureCommand.SWITCH_SCENE and intent.scene_id is not None:
            scene_id = intent.scene_id
            self._run_capture(lambda: use_case.switch_scene(scene_id))
            return
        if intent.command is CaptureCommand.MARK_MOMENT:
            label = intent.label or ""
            self._run_capture(lambda: use_case.mark_moment(label))
            return
        if intent.command is CaptureCommand.GET_STATUS:
            self._run_capture(use_case.refresh_status)
            return
        self._run_capture(getattr(use_case, intent.command.value))

    def _refresh_studio_context(self) -> None:
        """Alimenta la columna izquierda con el proyecto activo y su contexto.

        Un proyecto sin configurar no es un error que deba verse al grabar:
        la columna lo dice en lenguaje claro y la conversación sigue igual.
        """
        try:
            summary = self._project_continuity_use_case.get_summary()
        except ProjectContinuityError:
            self.studio_page.set_project_name("")
            self.studio_page.set_context_summary("")
            return
        self.studio_page.set_project_name(summary.name)
        self.studio_page.set_context_summary(summary.current_state)

    def _mirror_studio_state(self, state: StudioInteractionState) -> None:
        self.studio_page.set_interaction_state(state)

    def _build_conversation_tab(self) -> QWidget:
        self.project_continuity_widget = ProjectContinuityWidget(
            self._project_continuity_use_case,
            self._project_lifecycle_use_case,
            show_warning=self._show_warning,
        )
        self.project_continuity_widget.project_completed.connect(self.project_completed.emit)

        # B5: panel de contexto completo, de solo lectura, junto al bloque de
        # continuidad. Reutiliza casos de uso ya recibidos; no crea ninguno.
        self.context_panel_widget = ContextPanelWidget(
            self._project_continuity_use_case,
            self._get_knowledge_overview_use_case,
            self._get_memory_origin_use_case,
            self._get_decision_origin_use_case,
            show_warning=self._show_warning,
            show_information=self._show_information,
        )

        self.message_list = QListWidget()
        # Bugfix (historial solapado): con el modo por defecto (Fixed), Qt no
        # vuelve a calcular la posición/tamaño de los itemWidget cuando la
        # columna cambia de ancho (p. ej. al redimensionar la ventana), lo
        # que deja obsoleto el ancho de reflow usado por cada mensaje.
        self.message_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        # Bugfix (mensajes recortados con puntos suspensivos): el delegate por
        # omisión pintaba el texto del item en una sola línea recortada bajo el
        # widget transparente del mensaje. Con este delegate el texto del item
        # sigue existiendo para accesibilidad pero ya no se pinta.
        self.message_list.setItemDelegate(MessageItemDelegate(self.message_list))
        # Defensa adicional: si algún camino futuro volviera a pintar texto de
        # item, que no lo recorte.
        self.message_list.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.message_list.setWordWrap(True)
        # Desplazamiento por píxeles: con el modo por item, un mensaje más alto
        # que el viewport no se puede recorrer por dentro.
        self.message_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        # Separación vertical explícita entre mensajes.
        self.message_list.setSpacing(4)
        self.message_list.setAccessibleName("Historial de la conversación")

        # Seguimiento del final del historial, dirigido por señales (sin
        # temporizadores ni sondeo): ``rangeChanged`` avisa cuando el contenido
        # crece —incluido el primer cálculo real de geometría, que ocurre
        # después de construir la ventana— y ``valueChanged`` recuerda si el
        # usuario se ha ido hacia arriba a leer, caso en el que no se le mueve
        # la vista.
        history_scrollbar = self.message_list.verticalScrollBar()
        history_scrollbar.rangeChanged.connect(self._on_history_range_changed)
        history_scrollbar.valueChanged.connect(self._on_history_scrolled)

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Escribe un mensaje para Sirius")
        self.message_input.returnPressed.connect(self._handle_send_clicked)

        self.send_button = QPushButton("Enviar")
        self.send_button.clicked.connect(self._handle_send_clicked)

        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self._handle_cancel_clicked)
        self.cancel_button.setVisible(False)

        self.retry_button = QPushButton("Reintentar")
        self.retry_button.clicked.connect(self._handle_retry_clicked)
        self.retry_button.setVisible(False)

        input_row = QHBoxLayout()
        input_row.addWidget(self.message_input)
        input_row.addWidget(self.send_button)
        input_row.addWidget(self.cancel_button)
        input_row.addWidget(self.retry_button)

        self.status_label = QLabel("")
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #b00020;")

        # B7c/RF-030/PA-018: non-blocking notice, never a modal dialog —
        # sending stays allowed even while this is shown. Empty text is the
        # hidden state; _refresh_budget_warning fills or clears it.
        self.budget_warning_label = QLabel("")
        self.budget_warning_label.setStyleSheet("color: #8a6d00;")
        self.budget_warning_label.setWordWrap(True)

        # La conversación es la superficie principal de Sirius: ocupa su propia
        # columna, con el historial como único elemento que crece. Antes esta
        # columna compartía un QVBoxLayout con el bloque de continuidad y el
        # panel de contexto, que se llevaban la mayor parte del alto y dejaban
        # el historial reducido a una franja donde nada se podía leer.
        conversation_column = QWidget()
        conversation_layout = QVBoxLayout(conversation_column)
        conversation_layout.setContentsMargins(0, 0, 0, 0)
        conversation_layout.addWidget(self.message_list, 1)
        conversation_layout.addLayout(input_row)
        conversation_layout.addWidget(self.status_label)
        conversation_layout.addWidget(self.error_label)
        conversation_layout.addWidget(self.budget_warning_label)
        conversation_column.setMinimumWidth(_CONVERSATION_MINIMUM_WIDTH)

        # Proyecto, contexto, recuerdos y decisiones son secundarios: van a una
        # columna lateral con su propio desplazamiento, para que su alto no
        # empuje nunca al historial.
        side_column = QWidget()
        side_layout = QVBoxLayout(side_column)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.addWidget(self.project_continuity_widget)
        side_layout.addWidget(self.context_panel_widget)
        side_layout.addStretch(1)

        self.side_panel_scroll = QScrollArea()
        self.side_panel_scroll.setWidgetResizable(True)
        self.side_panel_scroll.setWidget(side_column)
        self.side_panel_scroll.setMaximumWidth(_SIDE_PANEL_MAXIMUM_WIDTH)

        self.conversation_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.conversation_splitter.addWidget(conversation_column)
        self.conversation_splitter.addWidget(self.side_panel_scroll)
        # La conversación se queda con el espacio que sobra al redimensionar.
        self.conversation_splitter.setStretchFactor(0, 3)
        self.conversation_splitter.setStretchFactor(1, 1)
        # El usuario puede plegar la columna lateral por completo arrastrando.
        self.conversation_splitter.setChildrenCollapsible(True)
        self.conversation_splitter.setSizes(
            [_CONVERSATION_INITIAL_WIDTH, _SIDE_PANEL_INITIAL_WIDTH]
        )

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.conversation_splitter)
        return container

    def _build_knowledge_tab(self) -> QWidget:
        self.knowledge_widget = KnowledgeWidget(
            self._get_knowledge_overview_use_case,
            self._save_manual_memory_use_case,
            self._get_memory_origin_use_case,
            self._correct_memory_use_case,
            self._archive_memory_use_case,
            self._delete_memory_use_case,
            self._propose_decision_use_case,
            self._approve_decision_use_case,
            self._get_decision_origin_use_case,
            self._supersede_decision_use_case,
            self._archive_decision_use_case,
            self._detect_precedence_conflicts_use_case,
            self._project_continuity_use_case,
            show_warning=self._show_warning,
            show_information=self._show_information,
        )

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.knowledge_widget)
        return container

    def _load_history(self) -> None:
        self._replace_history_with_authoritative_state()
        self._refresh_budget_warning()

    def _refresh_budget_warning(self) -> None:
        """Recompute the non-blocking budget notice (B7c).

        Called on open and after every completed send — the only moments
        spend can have changed. Never blocks sending: it only ever sets or
        clears a label.
        """
        status = self._get_budget_status_use_case.get_status()
        aviso = (
            f"Aviso: llevas {status.spent_usd:.2f} USD de "
            f"{status.monthly_limit_usd:.2f} USD de gasto este mes."
            if status.is_near_limit
            else ""
        )
        self.budget_warning_label.setText(aviso)
        # También en Model Studio: quedarse sin presupuesto grabando es el peor
        # momento para enterarse, y hasta ahora el aviso solo se veía en la
        # interfaz técnica, que es justo donde no se está mirando.
        self.studio_page.set_budget_notice(aviso)

    def _replace_history_with_authoritative_state(self) -> None:
        """Rebuild the visible list from GetConversationHistoryUseCase.

        Used at startup and to reconcile after a cancelled or failed send: an
        optimistic/streamed message that never actually persisted disappears;
        one that did persist before the failure (e.g. the provider failed
        afterwards) stays, because it is really there.
        """
        self.message_list.clear()
        self.studio_page.clear_history()
        self._streaming_item = None
        try:
            messages = self._get_history_use_case.get_history()
        except ConversationNotInitializedError:
            self.error_label.setText("No se pudo cargar el historial de la conversación.")
            return

        for message in messages:
            self._append_message_item(message.role, message.content, message.status)

        # Al abrir o recargar, el punto útil del historial es el final: lo
        # último dicho. Sin esto la vista se queda arriba y el usuario cree que
        # falta la conversación reciente.
        self._scroll_history_to_bottom()

    def _is_history_at_bottom(self) -> bool:
        scrollbar = self.message_list.verticalScrollBar()
        if scrollbar.maximum() == 0:
            return True
        return scrollbar.value() >= scrollbar.maximum() - _AT_BOTTOM_TOLERANCE_PX

    def _scroll_history_to_bottom(self) -> None:
        """Lleva la vista al final, sin poder reentrar.

        ``setValue`` puede provocar que la lista recalcule geometría y vuelva
        a emitir ``rangeChanged``, que llama otra vez aquí. Sin el guardia esa
        ida y vuelta se realimenta; con entrega síncrona de eventos, como la
        de Windows al acoplar la ventana, se realimenta dentro de la misma
        pila.
        """
        if self._scrolling_history:
            return
        self._scrolling_history = True
        try:
            scrollbar = self.message_list.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        finally:
            self._scrolling_history = False

    def _on_history_range_changed(self, _minimum: int, _maximum: int) -> None:
        """El historial creció (mensaje nuevo, streaming o reflujo por ancho).

        Solo se sigue el final si el usuario ya estaba ahí; si se había
        desplazado hacia arriba a leer, moverle la vista sería el salto
        errático que hay que evitar.
        """
        if self._follow_history_bottom:
            self._scroll_history_to_bottom()

    def _on_history_scrolled(self, _value: int) -> None:
        self._follow_history_bottom = self._is_history_at_bottom()

    def _append_message_item(
        self,
        role: MessageRole,
        content: str | None,
        status: MessageStatus = MessageStatus.COMPLETED,
    ) -> QListWidgetItem:
        item = QListWidgetItem("")
        self._set_item_text(item, role, content, status)
        if role is MessageRole.SIRIUS:
            font = item.font()
            font.setBold(True)
            item.setFont(font)
        self.message_list.addItem(item)

        # B8a/RF-008/SP-07: the item's own text above stays authoritative for
        # accessibility and is never removed; this widget is the visible,
        # safe-Markdown rendering shown to the user (setItemWidget does not
        # affect QListWidgetItem.text()).
        prefix = "Tú" if role is MessageRole.USER else "Sirius"
        widget = MessageItemWidget()
        # Bugfix (historial solapado): el ancho real de la columna solo
        # existe una vez que el widget está dentro de la lista, así que la
        # altura calculada en la construcción puede quedar corta. size_changed
        # se conecta antes de poblar contenido para capturar también el
        # reflow tardío (ancho real, streaming, o un resize posterior) y
        # mantener el sizeHint del item siempre al día con la altura real.
        widget.size_changed.connect(lambda: self._sync_item_height(item, widget))
        self.message_list.setItemWidget(item, widget)
        widget.set_message(
            prefix, self._compose_markdown_body(content, status), bold=role is MessageRole.SIRIUS
        )
        item.setSizeHint(widget.sizeHint())

        # Model Studio es una segunda vista de la MISMA conversación: se
        # alimenta desde aquí en vez de repetir la lógica de envío, historial
        # y streaming, que sigue viviendo en un solo sitio.
        self.studio_page.append_message(role, content, status)
        return item

    def _sync_item_height(self, item: QListWidgetItem, widget: MessageItemWidget) -> None:
        """Mantiene el sizeHint de la fila igual al alto real del widget.

        Se dispara en cada reflujo: cuando el widget recibe por fin el ancho
        real de la columna, mientras crece en streaming y cada vez que cambia
        el ancho disponible al redimensionar la ventana. El seguimiento del
        final lo resuelve ``rangeChanged``, no hace falta tocar el scroll aquí.
        """
        item.setSizeHint(widget.sizeHint())

    @staticmethod
    def _set_item_text(
        item: QListWidgetItem, role: MessageRole, content: str | None, status: MessageStatus
    ) -> None:
        prefix = "Tú" if role is MessageRole.USER else "Sirius"
        item.setText(f"{prefix}: {MainWindow._compose_markdown_body(content, status)}")

    @staticmethod
    def _compose_markdown_body(content: str | None, status: MessageStatus) -> str:
        suffix = {
            MessageStatus.CANCELLED: " (cancelado)",
            MessageStatus.FAILED: " (fallido)",
        }.get(status, "")
        # REDACTED (B4d) is the only status whose content is ever None: the
        # placeholder replaces it instead of literally rendering "None".
        shown_content = "(mensaje redactado)" if status is MessageStatus.REDACTED else content
        return f"{shown_content}{suffix}"

    def _handle_send_clicked(self) -> None:
        text = self.message_input.text()
        if not text.strip():
            return
        if self._is_sending or self._is_backup_busy or self._is_export_busy:
            return

        self.message_input.clear()
        self._start_send(text)

    def _handle_retry_clicked(self) -> None:
        # Resends the failed attempt's text unchanged, with a new
        # operation_id, through the same path as a normal send — never
        # touches message_input, which may hold an unrelated draft.
        if self._last_failed_text is None:
            return
        if self._is_sending or self._is_backup_busy or self._is_export_busy:
            return

        self._start_send(self._last_failed_text)

    def _start_send(self, text: str, *, extra_instructions: str = "") -> None:
        self._is_sending = True
        self._active_operation_id = str(uuid.uuid4())
        self._active_send_text = text
        self._last_failed_text = None
        self._streaming_item = None
        self._streaming_text = ""
        self.send_button.setEnabled(False)
        self.cancel_button.setVisible(True)
        self.cancel_button.setEnabled(True)
        self.message_input.setEnabled(False)
        self._set_backup_controls_enabled(False)
        self.export_button.setEnabled(False)
        self.project_continuity_widget.set_external_busy(True)
        self.knowledge_widget.set_external_busy(True)
        self.context_panel_widget.set_external_busy(True)
        self.status_label.setText("Sirius está pensando...")
        self.error_label.setText("")
        self.studio_page.set_error("")
        self._mirror_studio_state(StudioInteractionState.PENSANDO)
        self._update_retry_button()

        self._append_message_item(MessageRole.USER, text)

        worker = SendMessageWorker(
            self._send_message_use_case,
            text,
            self._active_operation_id,
            extra_instructions=extra_instructions,
        )
        worker.signals.delta.connect(self._on_delta)
        worker.signals.finished.connect(self._on_finished)
        worker.signals.crashed.connect(self._on_crashed)
        self._active_send_worker = worker
        self._thread_pool.start(worker)

    def _update_retry_button(self) -> None:
        has_pending_retry = self._last_failed_text is not None
        self.retry_button.setVisible(has_pending_retry)
        self.retry_button.setEnabled(
            has_pending_retry
            and not self._is_sending
            and not self._is_backup_busy
            and not self._is_export_busy
        )

    def _handle_cancel_clicked(self) -> None:
        # Idempotent: disabling the button after the first click prevents
        # repeated calls, and SendMessageUseCase.cancel() is itself
        # idempotent even if called more than once for the same operation.
        if self._active_operation_id is None:
            return
        self.cancel_button.setEnabled(False)
        self.status_label.setText("Cancelando...")
        # Interrumpir es interrumpir: si ya estaba leyendo, deja de leer.
        self._silence_pending_speech()
        self._send_message_use_case.cancel(self._active_operation_id)

    def _on_delta(self, text: str) -> None:
        self._streaming_text += text
        if self._streaming_item is None:
            self._streaming_item = self._append_message_item(MessageRole.SIRIUS, "")
        self._set_item_text(
            self._streaming_item, MessageRole.SIRIUS, self._streaming_text, MessageStatus.COMPLETED
        )
        # B8a: streamed deltas render as plain text while in flight (simpler
        # and stable); _on_finished consolidates the final text as Markdown.
        widget = self.message_list.itemWidget(self._streaming_item)
        if isinstance(widget, MessageItemWidget):
            widget.set_streaming_text("Sirius", self._streaming_text, bold=True)
            self._sync_item_height(self._streaming_item, widget)
        self.studio_page.update_last_message(self._streaming_text, MessageStatus.COMPLETED)
        self._speak_first_sentence_early()

    def _speak_first_sentence_early(self) -> None:
        """Empieza a hablar en cuanto hay una primera frase entera.

        Se corta en final de frase y una sola vez por respuesta. Lo que se dice
        es literalmente lo que ya está escrito en pantalla, no un adelanto ni
        un resumen.

        **Contrapartida asumida:** hablar antes de terminar significa que una
        respuesta cancelada a mitad puede haber sonado en parte. Se compensa
        cortando la voz en seco al cancelar o fallar, que es lo que pasa cuando
        interrumpes a alguien: deja de hablar, no sigue.
        """
        if self._early_speech_used or self._studio_voice_use_case is None:
            return
        if not self.model_studio_open:
            return
        corte = _first_sentence_end(self._streaming_text)
        if corte is None:
            return
        self._early_speech_used = True
        self._spoken_prefix_length = corte
        self._enqueue_speech(self._streaming_text[:corte])

    def _on_finished(self, result: SendMessageResult) -> None:
        # ``result.sirius_message`` is the row SendMessageUseCase actually
        # persisted (COMPLETED with the full reply, or CANCELLED/FAILED with
        # whatever partial text streamed) — authoritative, no need to reload.
        if self._streaming_item is None:
            self._streaming_item = self._append_message_item(
                MessageRole.SIRIUS, result.sirius_message.content, result.sirius_message.status
            )
        else:
            self._set_item_text(
                self._streaming_item,
                MessageRole.SIRIUS,
                result.sirius_message.content,
                result.sirius_message.status,
            )
            widget = self.message_list.itemWidget(self._streaming_item)
            if isinstance(widget, MessageItemWidget):
                widget.set_message(
                    "Sirius",
                    self._compose_markdown_body(
                        result.sirius_message.content, result.sirius_message.status
                    ),
                    bold=True,
                )
                self._sync_item_height(self._streaming_item, widget)
            self.studio_page.update_last_message(
                result.sirius_message.content, result.sirius_message.status
            )

        operation_id = result.sirius_message.operation_id
        if result.outcome is MessageStatus.CANCELLED:
            self.error_label.setText("Envío cancelado.")
            self.studio_page.set_error("Envío cancelado.")
        elif result.outcome is MessageStatus.FAILED:
            self.error_label.setText(failed_send_message(result.error_kind, operation_id))
            self.studio_page.set_error(failed_send_message(result.error_kind, operation_id))
            # Only a genuine failure offers "Reintentar" (D-05/B7b): a
            # CANCELLED outcome is a deliberate stop and never sets this.
            self._last_failed_text = self._active_send_text
        self._refresh_budget_warning()
        self._finish_sending()
        # Después de _finish_sending, que es quien devuelve el estado a
        # PREPARADO: si se hablara antes, ese reajuste borraría SINTETIZANDO.
        self._speak_if_studio_is_open(result.sirius_message.content, result.sirius_message.status)

    def _on_crashed(self, error_message: str) -> None:
        del error_message  # not shown verbatim: keep the user-facing message safe and generic
        operation_id = self._active_operation_id
        self._replace_history_with_authoritative_state()
        self.error_label.setText(failed_send_message(None, operation_id))
        self.studio_page.set_error(failed_send_message(None, operation_id))
        self._last_failed_text = self._active_send_text
        self._finish_sending()

    def _finish_sending(self) -> None:
        self._is_sending = False
        self._active_operation_id = None
        self._active_send_worker = None
        self._active_send_text = None
        self._streaming_item = None
        self._streaming_text = ""
        self.send_button.setEnabled(True)
        self.cancel_button.setVisible(False)
        self.message_input.setEnabled(True)
        self.status_label.setText("")
        self._set_backup_controls_enabled(True)
        self.export_button.setEnabled(True)
        self.project_continuity_widget.set_external_busy(False)
        self.knowledge_widget.set_external_busy(False)
        self.context_panel_widget.set_external_busy(False)
        # Un fallo deja el estado en ERROR y el motivo a la vista; un envío
        # normal vuelve a PREPARADO. En ninguno de los dos casos la superficie
        # se queda colgada en PENSANDO.
        self._mirror_studio_state(
            StudioInteractionState.ERROR
            if self._last_failed_text is not None
            else StudioInteractionState.PREPARADO
        )
        self._update_retry_button()
        if self._close_requested:
            self._close_requested = False
            self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Cierra micrófono y voz, y luego aplica el cierre diferido de siempre.

        Un temporal de audio no puede sobrevivir al cierre de la ventana.

        The worker keeps running to completion on its own thread; once it
        finishes, ``_finish_sending``/``_finish_backup_operation`` notices the
        pending request and closes the window from the main thread. Nothing
        is killed and no write is left half-done.
        """
        self._silence_voice()
        self._capture_heartbeat.stop()
        if self._is_sending:
            self._close_requested = True
            if self._active_operation_id is not None:
                self._send_message_use_case.cancel(self._active_operation_id)
            event.ignore()
            return
        if self._is_backup_busy:
            self._close_requested = True
            event.ignore()
            return
        if self._is_export_busy:
            self._close_requested = True
            event.ignore()
            return
        super().closeEvent(event)

    # --- Configuración ---------------------------------------------------

    def _build_settings_tab(self) -> QWidget:
        title = QLabel("Configuración inicial de Sirius")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Vamos a preparar los datos básicos antes de comenzar.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Cómo quieres que Sirius te llame")

        self.data_path_input = QLineEdit()

        settings = load_settings()
        self.name_input.setText(settings.get("user_name", ""))
        self.data_path_input.setText(settings.get("data_path", "datos"))

        form = QFormLayout()
        form.addRow("Tu nombre:", self.name_input)
        form.addRow("Carpeta de datos:", self.data_path_input)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems([kind.value for kind in LLMProviderKind])
        try:
            current_provider = resolve_provider_kind(settings)
        except LLMProviderConfigurationError:
            current_provider = LLMProviderKind.FAKE
        self.provider_combo.setCurrentText(current_provider.value)

        self.model_input = QLineEdit()
        self.max_output_tokens_input = QLineEdit()
        self.budget_input = QLineEdit()
        try:
            provider_defaults = resolve_openai_provider_settings(settings)
        except LLMProviderConfigurationError:
            provider_defaults = resolve_openai_provider_settings({})
        self.model_input.setText(provider_defaults.model)
        self.max_output_tokens_input.setText(str(provider_defaults.max_output_tokens))
        self.budget_input.setText(str(provider_defaults.monthly_budget_usd))

        form.addRow("Proveedor:", self.provider_combo)
        form.addRow("Modelo:", self.model_input)
        form.addRow("Máximo de tokens de salida:", self.max_output_tokens_input)
        form.addRow("Presupuesto mensual (USD):", self.budget_input)

        save_button = QPushButton("Guardar configuración")
        save_button.clicked.connect(self._save_configuration)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Nueva clave de API de OpenAI")

        self.key_status_label = QLabel()
        self.key_feedback_label = QLabel("")
        self._refresh_key_status_label()

        save_key_button = QPushButton("Guardar clave")
        save_key_button.clicked.connect(self._save_api_key)
        delete_key_button = QPushButton("Eliminar clave")
        delete_key_button.clicked.connect(self._delete_api_key)

        key_form = QFormLayout()
        key_form.addRow("Clave de API de OpenAI:", self.api_key_input)

        key_buttons_row = QHBoxLayout()
        key_buttons_row.addWidget(save_key_button)
        key_buttons_row.addWidget(delete_key_button)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(form)
        layout.addWidget(save_button)
        layout.addLayout(key_form)
        layout.addLayout(key_buttons_row)
        layout.addWidget(self.key_status_label)
        layout.addWidget(self.key_feedback_label)
        layout.addWidget(self._build_backup_group())
        layout.addWidget(self._build_export_group())
        layout.addStretch()

        # The backup/recovery section grew this tab beyond the default
        # 900x620 window: wrap it (same tab, same controls, no new screen)
        # in a resizable scroll area so every control — including the
        # restore section — stays reachable by mouse and by keyboard.
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(container)
        # Guardado porque el resultado de una operación de copia se escribe en
        # etiquetas que están al final de la pestaña, fuera del área visible
        # con la ventana a su tamaño por omisión: sin desplazar hasta ellas, el
        # mensaje se escribe donde nadie lo ve y la operación parece muda.
        self._settings_scroll_area = scroll_area
        return scroll_area

    # --- Copia de seguridad y restauración --------------------------------

    def _build_backup_group(self) -> QGroupBox:
        group = QGroupBox("Copia de seguridad y restauración")
        layout = QVBoxLayout(group)

        layout.addWidget(self._build_create_backup_section())
        layout.addWidget(self._build_validate_backup_section())
        layout.addWidget(self._build_restore_backup_section())
        return group

    def _build_create_backup_section(self) -> QWidget:
        self.create_backup_password_input = QLineEdit()
        self.create_backup_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.create_backup_password_repeat_input = QLineEdit()
        self.create_backup_password_repeat_input.setEchoMode(QLineEdit.EchoMode.Password)

        form = QFormLayout()
        form.addRow("Contraseña de la copia:", self.create_backup_password_input)
        form.addRow("Repite la contraseña:", self.create_backup_password_repeat_input)

        self.create_backup_button = QPushButton("Crear copia cifrada")
        self.create_backup_button.clicked.connect(self._handle_create_backup_clicked)

        self.create_backup_status_label = QLabel("")
        self.create_backup_status_label.setWordWrap(True)

        # La ruta completa, siempre a la vista y seleccionable con el ratón:
        # un aviso modal que se cierra no deja rastro de dónde quedó la copia.
        self.create_backup_path_label = QLabel("")
        self.create_backup_path_label.setWordWrap(True)
        self.create_backup_path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.open_backup_folder_button = QPushButton("Abrir carpeta")
        self.open_backup_folder_button.clicked.connect(self._handle_open_backup_folder_clicked)
        self.use_last_backup_button = QPushButton("Usar esta copia")
        self.use_last_backup_button.setToolTip(
            "Pone la ruta de esta copia en los campos de validar y restaurar."
        )
        self.use_last_backup_button.clicked.connect(self._handle_use_last_backup_clicked)
        # Sin copia creada todavía no hay carpeta que abrir ni ruta que reusar.
        self.open_backup_folder_button.setEnabled(False)
        self.use_last_backup_button.setEnabled(False)

        last_backup_row = QHBoxLayout()
        last_backup_row.addWidget(self.open_backup_folder_button)
        last_backup_row.addWidget(self.use_last_backup_button)
        last_backup_row.addStretch()

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addLayout(form)
        layout.addWidget(self.create_backup_button)
        layout.addWidget(self.create_backup_status_label)
        layout.addWidget(self.create_backup_path_label)
        layout.addLayout(last_backup_row)
        return container

    def _build_validate_backup_section(self) -> QWidget:
        self.validate_backup_path_input = QLineEdit()
        self.validate_backup_path_input.setPlaceholderText("Ningún archivo seleccionado")
        self.validate_backup_browse_button = QPushButton("Examinar...")
        self.validate_backup_browse_button.clicked.connect(
            self._handle_validate_backup_browse_clicked
        )

        path_row = QHBoxLayout()
        path_row.addWidget(self.validate_backup_path_input)
        path_row.addWidget(self.validate_backup_browse_button)

        self.validate_backup_password_input = QLineEdit()
        self.validate_backup_password_input.setEchoMode(QLineEdit.EchoMode.Password)

        form = QFormLayout()
        form.addRow("Archivo (.siriusbackup):", path_row)
        form.addRow("Contraseña de la copia:", self.validate_backup_password_input)

        self.validate_backup_button = QPushButton("Validar copia")
        self.validate_backup_button.clicked.connect(self._handle_validate_backup_clicked)

        self.validate_backup_result_label = QLabel("")
        self.validate_backup_result_label.setWordWrap(True)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addLayout(form)
        layout.addWidget(self.validate_backup_button)
        layout.addWidget(self.validate_backup_result_label)
        return container

    def _build_restore_backup_section(self) -> QWidget:
        self.restore_backup_path_input = QLineEdit()
        self.restore_backup_path_input.setPlaceholderText("Ningún archivo seleccionado")
        self.restore_backup_browse_button = QPushButton("Examinar...")
        self.restore_backup_browse_button.clicked.connect(
            self._handle_restore_backup_browse_clicked
        )

        path_row = QHBoxLayout()
        path_row.addWidget(self.restore_backup_path_input)
        path_row.addWidget(self.restore_backup_browse_button)

        self.restore_backup_password_input = QLineEdit()
        self.restore_backup_password_input.setEchoMode(QLineEdit.EchoMode.Password)

        form = QFormLayout()
        form.addRow("Archivo (.siriusbackup):", path_row)
        form.addRow("Contraseña de la copia:", self.restore_backup_password_input)

        self.restore_backup_button = QPushButton("Restaurar copia")
        self.restore_backup_button.clicked.connect(self._handle_restore_backup_clicked)

        self.restore_backup_status_label = QLabel("")
        self.restore_backup_feedback_label = QLabel("")
        self.restore_backup_feedback_label.setWordWrap(True)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addLayout(form)
        layout.addWidget(self.restore_backup_button)
        layout.addWidget(self.restore_backup_status_label)
        layout.addWidget(self.restore_backup_feedback_label)
        return container

    def _set_backup_controls_enabled(self, enabled: bool) -> None:
        self.create_backup_button.setEnabled(enabled)
        self.create_backup_password_input.setEnabled(enabled)
        self.create_backup_password_repeat_input.setEnabled(enabled)
        self.validate_backup_button.setEnabled(enabled)
        self.validate_backup_browse_button.setEnabled(enabled)
        self.validate_backup_path_input.setEnabled(enabled)
        self.validate_backup_password_input.setEnabled(enabled)
        self.restore_backup_button.setEnabled(enabled)
        self.restore_backup_browse_button.setEnabled(enabled)
        self.restore_backup_path_input.setEnabled(enabled)
        self.restore_backup_password_input.setEnabled(enabled)
        # Estos dos solo tienen sentido si ya hay una copia creada; mientras
        # una operación está en curso se apagan como todos los demás.
        has_last_backup = enabled and self._last_backup_path is not None
        self.open_backup_folder_button.setEnabled(has_last_backup)
        self.use_last_backup_button.setEnabled(has_last_backup)

    def _set_backup_feedback(self, label: QLabel, state: str, detail: str) -> None:
        """Escribe el resultado de una operación de copia y lo hace visible.

        El estado viaja en la propiedad ``siriusBackupState`` además de en el
        texto: ``validada``, ``restaurada``, ``cancelada`` y ``rechazada`` son
        cuatro desenlaces distintos, y distinguirlos no puede depender de cómo
        esté redactada la frase.

        Desplazar hasta la etiqueta es parte del trabajo, no un adorno: estas
        etiquetas están al final de una pestaña más alta que la ventana, así
        que sin esto el mensaje queda fuera del área visible y la operación se
        percibe como que «no pasa nada».
        """
        label.setProperty(BACKUP_STATE_PROPERTY, state)
        label.setStyleSheet(_BACKUP_STATE_STYLES[state])
        label.setText(detail)
        self._scroll_settings_to(label)

    def _scroll_settings_to(self, label: QLabel) -> None:
        """Desplaza la pestaña hasta dejar la etiqueta ENTERA a la vista.

        En dos tiempos, y el segundo no sobra. ``setText`` solo encola el
        recálculo, y una etiqueta con ajuste de línea no llega a su altura
        final de una vez: medido en la pestaña real, la confirmación de una
        copia válida pasa por 14, 32, 44 y 70 px conforme el diseño converge,
        porque su propio ancho cambia según aparezca o no la barra de
        desplazamiento. El primer desplazamiento deja el mensaje a la vista
        de inmediato; el segundo, ya en el bucle de eventos, corrige la
        posición con el diseño terminado. Se pasa ``self`` como contexto para
        que Qt descarte la llamada si la ventana se cierra antes de disparar.
        """
        self._ensure_label_visible(label)
        self._pending_feedback_label = label
        QTimer.singleShot(0, self, self._ensure_pending_feedback_visible)

    def _ensure_pending_feedback_visible(self) -> None:
        label = self._pending_feedback_label
        self._pending_feedback_label = None
        if label is not None:
            self._ensure_label_visible(label)

    def _ensure_label_visible(self, label: QLabel) -> None:
        """Deja la etiqueta entera dentro del área visible de Configuración.

        No usa ``ensureWidgetVisible``: ese método trabaja con el alto que la
        etiqueta tiene AHORA, y mientras el diseño converge ese alto se queda
        corto, con lo que el final del mensaje sigue asomando por debajo del
        borde (medido: 6 px de recorte con una confirmación de cinco líneas).
        Aquí se activa el diseño del contenido y se cuenta con el alto que la
        etiqueta va a tener con su ancho actual —``heightForWidth``—, que es
        el dato que no depende de en qué pasada de diseño estemos.
        """
        scroll_area = self._settings_scroll_area
        content = scroll_area.widget()
        if content is not None:
            layout = content.layout()
            if layout is not None:
                layout.activate()

        viewport_height = scroll_area.viewport().height()
        top = label.mapTo(scroll_area.viewport(), QPoint(0, 0)).y()
        height = max(label.height(), label.heightForWidth(label.width()))
        scrollbar = scroll_area.verticalScrollBar()

        overflow = top + height - viewport_height
        if overflow > 0:
            scrollbar.setValue(scrollbar.value() + overflow)
        elif top < 0:
            scrollbar.setValue(scrollbar.value() + top)

    @staticmethod
    def _clear_backup_feedback(label: QLabel) -> None:
        label.setProperty(BACKUP_STATE_PROPERTY, None)
        label.setStyleSheet("")
        label.setText("")

    def _start_backup_operation(self) -> None:
        self._is_backup_busy = True
        self._set_backup_controls_enabled(False)
        self.send_button.setEnabled(False)
        self.message_input.setEnabled(False)
        self.export_button.setEnabled(False)
        self.project_continuity_widget.set_external_busy(True)
        self.knowledge_widget.set_external_busy(True)
        self.context_panel_widget.set_external_busy(True)
        self._update_retry_button()

    def _finish_backup_operation(self) -> None:
        self._is_backup_busy = False
        self._active_backup_worker = None
        self._set_backup_controls_enabled(True)
        self.send_button.setEnabled(True)
        self.message_input.setEnabled(True)
        self.export_button.setEnabled(True)
        self.project_continuity_widget.set_external_busy(False)
        self.knowledge_widget.set_external_busy(False)
        self.context_panel_widget.set_external_busy(False)
        self._update_retry_button()
        if self._close_requested:
            self._close_requested = False
            self.close()

    @staticmethod
    def _format_backup_summary(manifest: BackupManifest, size_bytes: int) -> str:
        return (
            f"Fecha: {manifest.created_at.isoformat()}\n"
            f"Versión de aplicación: {manifest.app_version}\n"
            f"Esquema: {manifest.schema_version}\n"
            f"Tamaño: {size_bytes:,} bytes"
        )

    # --- Crear copia -------------------------------------------------------

    def _handle_create_backup_clicked(self) -> None:
        if self._is_sending or self._is_backup_busy or self._is_export_busy:
            return

        password = self.create_backup_password_input.text()
        repeat = self.create_backup_password_repeat_input.text()
        self.create_backup_password_input.clear()
        self.create_backup_password_repeat_input.clear()

        if not password:
            self._show_warning("Falta la contraseña", "Escribe una contraseña para la copia.")
            return
        if password != repeat:
            self._show_warning(
                "Las contraseñas no coinciden",
                "Escribe la misma contraseña en los dos campos.",
            )
            return

        self._start_backup_operation()
        self._set_backup_feedback(
            self.create_backup_status_label, BACKUP_STATE_IN_PROGRESS, "Creando copia cifrada..."
        )

        worker = CreateBackupWorker(self._create_backup_use_case, password)
        worker.signals.succeeded.connect(self._on_create_backup_succeeded)
        worker.signals.failed.connect(self._on_create_backup_failed)
        self._active_backup_worker = worker
        self._thread_pool.start(worker)

    def _on_create_backup_succeeded(self, result: BackupResult) -> None:
        # Captured before _finish_backup_operation() clears the flag: a
        # pending close must not pop up a new dialog once the window is on
        # its way out.
        should_notify = not self._close_requested
        # Antes de _finish_backup_operation(), que es quien decide si «Abrir
        # carpeta» y «Usar esta copia» pueden encenderse.
        self._last_backup_path = result.path
        self._finish_backup_operation()
        self._set_backup_feedback(
            self.create_backup_status_label,
            BACKUP_STATE_CREATED,
            "Copia cifrada creada correctamente.",
        )
        self.create_backup_path_label.setText(f"Archivo: {result.path}")
        if should_notify:
            self._show_information(
                "Copia creada",
                f"Copia cifrada creada correctamente en:\n{result.path}\n\n"
                'La ruta queda escrita en la pestaña "Configuración", con los '
                'botones "Abrir carpeta" y "Usar esta copia".',
            )

    def _on_create_backup_failed(self, message: str) -> None:
        should_notify = not self._close_requested
        self._finish_backup_operation()
        self._set_backup_feedback(
            self.create_backup_status_label,
            BACKUP_STATE_REJECTED,
            f"No se pudo crear la copia. {message}",
        )
        if should_notify:
            self._show_warning("No se pudo crear la copia", message)

    def _handle_open_backup_folder_clicked(self) -> None:
        if self._last_backup_path is None:
            return
        self._open_containing_folder(self._last_backup_path)

    def _handle_use_last_backup_clicked(self) -> None:
        """Lleva la ruta de la última copia a validar y a restaurar.

        Es la alternativa directa a volver a buscar a mano, en un selector de
        archivos, la copia que Sirius acaba de crear.
        """
        if self._last_backup_path is None:
            return
        path_text = str(self._last_backup_path)
        self.validate_backup_path_input.setText(path_text)
        self.restore_backup_path_input.setText(path_text)

    # --- Validar copia -------------------------------------------------------

    def _handle_validate_backup_browse_clicked(self) -> None:
        path_text = self._choose_backup_file("Seleccionar copia de seguridad")
        if path_text:
            self.validate_backup_path_input.setText(path_text)

    def _handle_validate_backup_clicked(self) -> None:
        if self._is_sending or self._is_backup_busy or self._is_export_busy:
            return

        path_text = self.validate_backup_path_input.text().strip()
        password = self.validate_backup_password_input.text()
        self.validate_backup_password_input.clear()

        if not path_text:
            self._show_warning("Falta el archivo", "Selecciona un archivo .siriusbackup.")
            return
        if not password:
            self._show_warning("Falta la contraseña", "Escribe la contraseña de la copia.")
            return

        self._start_backup_operation()
        self._set_backup_feedback(
            self.validate_backup_result_label, BACKUP_STATE_IN_PROGRESS, "Validando copia..."
        )

        worker = ValidateBackupWorker(self._validate_backup_use_case, Path(path_text), password)
        worker.signals.succeeded.connect(self._on_validate_backup_succeeded)
        worker.signals.failed.connect(self._on_validate_backup_failed)
        self._active_backup_worker = worker
        self._thread_pool.start(worker)

    def _on_validate_backup_succeeded(self, result: BackupValidationResult) -> None:
        should_notify = not self._close_requested
        self._finish_backup_operation()
        summary = self._format_backup_summary(result.manifest, result.size_bytes)
        # El resumen por sí solo no dice si la copia sirve: enumera fecha,
        # versión y tamaño, y ante esos datos no se distingue «válida» de
        # «no he hecho nada». La confirmación tiene que ser explícita.
        confirmation = "Copia validada: la contraseña es correcta y el archivo está íntegro."
        self._set_backup_feedback(
            self.validate_backup_result_label,
            BACKUP_STATE_VALIDATED,
            f"{confirmation}\n{summary}",
        )
        if should_notify:
            self._show_information("Copia validada", f"{confirmation}\n\n{summary}")

    def _on_validate_backup_failed(self, message: str) -> None:
        should_notify = not self._close_requested
        self._finish_backup_operation()
        self._set_backup_feedback(
            self.validate_backup_result_label,
            BACKUP_STATE_REJECTED,
            f"Copia rechazada: {message}",
        )
        if should_notify:
            self._show_warning("Copia rechazada", message)

    # --- Restaurar copia -----------------------------------------------------

    def _handle_restore_backup_browse_clicked(self) -> None:
        path_text = self._choose_backup_file("Seleccionar copia a restaurar")
        if path_text:
            self.restore_backup_path_input.setText(path_text)

    def _handle_restore_backup_clicked(self) -> None:
        if self._is_sending or self._is_backup_busy or self._is_export_busy:
            return

        path_text = self.restore_backup_path_input.text().strip()
        password = self.restore_backup_password_input.text()
        self.restore_backup_password_input.clear()

        if not path_text:
            self._show_warning("Falta el archivo", "Selecciona un archivo .siriusbackup.")
            return
        if not password:
            self._show_warning("Falta la contraseña", "Escribe la contraseña de la copia.")
            return

        self._start_backup_operation()
        self._set_backup_feedback(
            self.restore_backup_status_label, BACKUP_STATE_IN_PROGRESS, "Validando copia..."
        )
        self._clear_backup_feedback(self.restore_backup_feedback_label)

        backup_path = Path(path_text)
        worker = ValidateBackupWorker(self._validate_backup_use_case, backup_path, password)
        worker.signals.succeeded.connect(
            lambda result: self._on_restore_validation_succeeded(result, backup_path, password)
        )
        worker.signals.failed.connect(self._on_restore_validation_failed)
        self._active_backup_worker = worker
        self._thread_pool.start(worker)

    def _on_restore_validation_succeeded(
        self, result: BackupValidationResult, backup_path: Path, password: str
    ) -> None:
        self._clear_backup_feedback(self.restore_backup_status_label)

        # A close was requested while the pre-validation was still running:
        # honor it instead of popping up a destructive confirmation dialog
        # for a window that is on its way out. _finish_backup_operation()
        # already closes the window when a close is pending.
        if self._close_requested:
            self._finish_backup_operation()
            return

        summary = self._format_backup_summary(result.manifest, result.size_bytes)
        confirmed = self._confirm_restore(
            "Confirmar restauración",
            "Esta acción sustituirá todos los datos actuales de Sirius por los de la "
            "copia seleccionada.\n\n"
            "Antes de reemplazar nada, Sirius creará automáticamente una copia de "
            "seguridad de los datos actuales.\n\n"
            "Si la copia que vas a restaurar es antigua, puede reintroducir información "
            "que ya habías eliminado.\n\n"
            "La clave de API de OpenAI no forma parte de la copia y no se restaurará: "
            "tendrás que volver a configurarla si hace falta.\n\n"
            f"{summary}\n\n"
            "¿Deseas continuar?",
        )
        if not confirmed:
            self._finish_backup_operation()
            self._set_backup_feedback(
                self.restore_backup_feedback_label,
                BACKUP_STATE_CANCELLED,
                "Restauración cancelada. No se ha modificado ningún dato.",
            )
            return

        self._set_backup_feedback(
            self.restore_backup_status_label, BACKUP_STATE_IN_PROGRESS, "Restaurando..."
        )
        # Must run before RestoreBackupUseCase: this window's own pooled
        # connections to sirius.db would otherwise block the atomic file
        # replace on Windows (confirmed empirically; see PLAN.md). If this
        # fails, the restore must never be attempted: restore the interface,
        # log only the exception type, and never show the raw exception.
        try:
            self._close_database_connections()
        except Exception as exc:
            _logger.error(
                "No se pudieron cerrar las conexiones antes de restaurar (%s)",
                type(exc).__name__,
            )
            self._finish_backup_operation()
            self._clear_backup_feedback(self.restore_backup_status_label)
            self._reject_restore("No se pudo preparar la restauración. Inténtalo de nuevo.")
            return

        worker = RestoreBackupWorker(self._restore_backup_use_case, backup_path, password)
        worker.signals.succeeded.connect(self._on_restore_backup_succeeded)
        worker.signals.failed.connect(self._on_restore_backup_failed)
        self._active_backup_worker = worker
        self._thread_pool.start(worker)

    def _reject_restore(self, message: str) -> None:
        """Deja constancia visible de que la restauración NO se ha hecho.

        Que la restauración no se ejecute ante una contraseña incorrecta es lo
        correcto; hacerlo en silencio no lo es. Aviso modal y estado
        ``rechazada`` en la etiqueta, que es lo que queda después de cerrarlo.
        """
        should_notify = not self._close_requested
        self._set_backup_feedback(
            self.restore_backup_feedback_label,
            BACKUP_STATE_REJECTED,
            f"Restauración rechazada: {message}\nNo se ha modificado ningún dato.",
        )
        if should_notify:
            self._show_warning(
                "No se pudo restaurar",
                f"{message}\n\nNo se ha modificado ningún dato.",
            )

    def _on_restore_validation_failed(self, message: str) -> None:
        self._finish_backup_operation()
        self._clear_backup_feedback(self.restore_backup_status_label)
        self._reject_restore(message)

    def _on_restore_backup_succeeded(self, result: BackupRestoreResult) -> None:
        # Deliberately not `_finish_backup_operation()`: the window is about
        # to close, and re-enabling now-obsolete controls would be pointless.
        self._is_backup_busy = False
        self._active_backup_worker = None
        self.project_continuity_widget.set_external_busy(False)
        self.knowledge_widget.set_external_busy(False)
        self.context_panel_widget.set_external_busy(False)
        self._clear_backup_feedback(self.restore_backup_status_label)
        self._set_backup_feedback(
            self.restore_backup_feedback_label,
            BACKUP_STATE_RESTORED,
            "Copia restaurada correctamente.",
        )
        message = "Los datos se restauraron correctamente."
        if result.safety_backup_path is not None:
            message += (
                "\n\nSe guardó una copia de seguridad de los datos anteriores en:\n"
                f"{result.safety_backup_path}"
            )
        message += "\n\nSirius se cerrará ahora. Ábrelo de nuevo para continuar."
        self._show_information("Restauración completada", message)
        self.close()

    def _on_restore_backup_failed(self, message: str) -> None:
        # The connections were already disposed before this attempt; that is
        # harmless even on failure (SQLAlchemy reconnects lazily on next use)
        # because RestoreBackupUseCase guarantees the file on disk is left
        # either untouched or correctly rolled back.
        self._finish_backup_operation()
        self._clear_backup_feedback(self.restore_backup_status_label)
        self._reject_restore(message)

    # --- Exportación (B9b/S12.1/RF-031/PA-020) --------------------------

    def _build_export_group(self) -> QGroupBox:
        group = QGroupBox("Exportación de datos")
        layout = QVBoxLayout(group)

        self.export_button = QPushButton("Exportar")
        self.export_button.clicked.connect(self._handle_export_clicked)

        self.export_status_label = QLabel("")
        self.export_status_label.setWordWrap(True)

        layout.addWidget(self.export_button)
        layout.addWidget(self.export_status_label)
        return group

    def _handle_export_clicked(self) -> None:
        if self._is_sending or self._is_backup_busy or self._is_export_busy:
            return

        # S12.1: the personal-data/no-API-key notice is mandatory and must
        # come first — cancelling here must never call the use case.
        confirmed = self._confirm_export(
            "Exportar datos",
            "Vas a crear una exportación legible de tu conversación, tu "
            "proyecto activo, tus recuerdos y tus decisiones vigentes.\n\n"
            "Puede contener información personal. No incluye tu clave de "
            "API de OpenAI.\n\n"
            "¿Deseas continuar?",
        )
        if not confirmed:
            return

        destination_text = self._choose_export_directory("Selecciona la carpeta destino")
        if not destination_text:
            return

        self._start_export_operation()
        self.export_status_label.setText("Exportando...")

        worker = ExportWorker(self._export_structured_use_case, Path(destination_text))
        worker.signals.succeeded.connect(self._on_export_succeeded)
        worker.signals.failed.connect(self._on_export_failed)
        self._active_export_worker = worker
        self._thread_pool.start(worker)

    def _start_export_operation(self) -> None:
        self._is_export_busy = True
        self.export_button.setEnabled(False)
        self.send_button.setEnabled(False)
        self.message_input.setEnabled(False)
        self._set_backup_controls_enabled(False)
        self.project_continuity_widget.set_external_busy(True)
        self.knowledge_widget.set_external_busy(True)
        self.context_panel_widget.set_external_busy(True)
        self._update_retry_button()

    def _finish_export_operation(self) -> None:
        self._is_export_busy = False
        self._active_export_worker = None
        self.export_button.setEnabled(True)
        self.send_button.setEnabled(True)
        self.message_input.setEnabled(True)
        self._set_backup_controls_enabled(True)
        self.project_continuity_widget.set_external_busy(False)
        self.knowledge_widget.set_external_busy(False)
        self.context_panel_widget.set_external_busy(False)
        self._update_retry_button()
        if self._close_requested:
            self._close_requested = False
            self.close()

    def _on_export_succeeded(self, path: Path) -> None:
        should_notify = not self._close_requested
        self._finish_export_operation()
        self.export_status_label.setText("")
        if should_notify:
            self._show_information(
                "Exportación completada",
                f"La exportación se creó correctamente en:\n{path}",
            )

    def _on_export_failed(self, message: str) -> None:
        should_notify = not self._close_requested
        self._finish_export_operation()
        self.export_status_label.setText("")
        if should_notify:
            self._show_warning("No se pudo exportar", message)

    def _refresh_key_status_label(self) -> bool:
        try:
            has_key = self._api_key_settings_use_case.has_key()
        except ApiKeySettingsError:
            self.key_status_label.setText("Clave de API: estado no disponible.")
            self.key_feedback_label.setText(
                "No se pudo consultar el almacén seguro de credenciales de Windows."
            )
            return False

        self.key_status_label.setText(
            "Clave de API: configurada." if has_key else "Clave de API: no configurada."
        )
        return True

    def _save_api_key(self) -> None:
        key = self.api_key_input.text().strip()
        if not key:
            self.key_feedback_label.setText("")
            self._show_warning("Falta la clave", "Escribe una clave antes de guardarla.")
            return
        try:
            self._api_key_settings_use_case.save_key(key)
        except ApiKeySettingsError:
            self.key_feedback_label.setText("")
            self._show_warning(
                "No se pudo guardar",
                "No se pudo guardar la clave en el almacén seguro de Windows.",
            )
            return
        finally:
            self.api_key_input.clear()

        if self._refresh_key_status_label():
            # An inline, non-modal status replaces a success dialog here: saving
            # a key is a frequent action and must never require a click to
            # dismiss (V7A: no QMessageBox for this specific confirmation).
            self.key_feedback_label.setText("Clave guardada.")

    def _delete_api_key(self) -> None:
        try:
            self._api_key_settings_use_case.delete_key()
        except ApiKeySettingsError:
            self.key_feedback_label.setText("")
            self._show_warning(
                "No se pudo eliminar",
                "No se pudo eliminar la clave del almacén seguro de Windows.",
            )
            return

        if self._refresh_key_status_label():
            self.key_feedback_label.setText("")
        self._show_information("Clave eliminada", "La clave de API se ha eliminado.")

    def _save_configuration(self) -> None:
        name = self.name_input.text().strip()
        data_path = self.data_path_input.text().strip()

        if not name:
            self._show_warning("Falta información", "Escribe primero tu nombre.")
            return

        try:
            max_output_tokens = int(self.max_output_tokens_input.text().strip())
            monthly_budget_usd = float(self.budget_input.text().strip())
        except ValueError:
            self._show_warning(
                "Valor inválido",
                "El máximo de tokens y el presupuesto mensual deben ser números.",
            )
            return

        if max_output_tokens <= 0 or monthly_budget_usd <= 0:
            self._show_warning(
                "Valor inválido",
                "El máximo de tokens y el presupuesto mensual deben ser mayores que cero.",
            )
            return

        data: dict[str, Any] = {
            "user_name": name,
            "data_path": data_path,
            "llm_provider": self.provider_combo.currentText(),
            "openai_model": self.model_input.text().strip(),
            "openai_max_output_tokens": max_output_tokens,
            "openai_monthly_budget_usd": monthly_budget_usd,
        }
        save_settings(data)

        self._show_information(
            "Configuración guardada",
            f"Sirius recordará que debe llamarte {name}.",
        )
