"""Renderizado seguro de Markdown para un mensaje de la conversación (B8a, RF-008, SP-07).

Widget usado como ``QListWidget.setItemWidget`` en ``MainWindow``. El contenido
del mensaje se trata siempre como Markdown, nunca como HTML: ``MarkdownNoHTML``
hace que cualquier HTML/script embebido en el texto se muestre literal
(escapado) en vez de interpretarse o descartarse en silencio. No se llama
``setHtml`` con contenido del mensaje en ningún camino de este módulo, y al
usar ``QTextEdit`` (no ``QTextBrowser``) no hay navegación automática de
enlaces ni carga de recursos externos: la interacción de solo lectura no
incluye ``LinksAccessibleByMouse``.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QResizeEvent, QTextDocument
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QTextEdit, QVBoxLayout, QWidget

_MARKDOWN_FEATURES = (
    QTextDocument.MarkdownFeature.MarkdownDialectGitHub
    | QTextDocument.MarkdownFeature.MarkdownNoHTML
)


class _MessageBody(QTextEdit):
    """Área de texto de solo lectura que ajusta su alto al contenido."""

    def __init__(self) -> None:
        super().__init__()
        self.setReadOnly(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("background: transparent; border: none;")

    def set_markdown_content(self, text: str) -> None:
        self.document().setMarkdown(text, _MARKDOWN_FEATURES)
        self._sync_height()

    def set_plain_content(self, text: str) -> None:
        self.setPlainText(text)
        self._sync_height()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._sync_height()

    def _sync_height(self) -> None:
        width = self.viewport().width() or self.width() or 400
        self.document().setTextWidth(width)
        height = int(self.document().size().height()) + 8
        if self.height() != height:
            self.setFixedHeight(height)


class MessageItemWidget(QWidget):
    """Un mensaje completo (prefijo "Tú"/"Sirius" + cuerpo) para un item de la lista."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 6)
        layout.setSpacing(2)
        self._prefix_label = QLabel()
        layout.addWidget(self._prefix_label)
        self._body = _MessageBody()
        layout.addWidget(self._body)

    def set_message(self, prefix: str, body_text: str, *, bold: bool) -> None:
        """Renderiza el contenido final consolidado como Markdown seguro."""
        self._set_prefix(prefix, bold=bold)
        self._body.set_markdown_content(body_text)
        self._sync_size()

    def set_streaming_text(self, prefix: str, body_text: str, *, bold: bool) -> None:
        """Renderiza el texto parcial en streaming como texto plano (más simple y estable)."""
        self._set_prefix(prefix, bold=bold)
        self._body.set_plain_content(body_text)
        self._sync_size()

    def rendered_plain_text(self) -> str:
        """The body's rendered plain text, e.g. to assert Markdown syntax is gone."""
        return self._body.toPlainText()

    def rendered_html(self) -> str:
        """The body's rendered rich text, e.g. to assert raw HTML stayed escaped (SP-07)."""
        return self._body.toHtml()

    def _set_prefix(self, prefix: str, *, bold: bool) -> None:
        font = self._prefix_label.font()
        font.setBold(bold)
        self._prefix_label.setFont(font)
        self._prefix_label.setText(prefix)

    def _sync_size(self) -> None:
        self.adjustSize()
        self.updateGeometry()
