"""Renderizado seguro de Markdown y bloques de código copiables (B8a+B8b, RF-008, SP-07).

Widget usado como ``QListWidget.setItemWidget`` en ``MainWindow``. El contenido
del mensaje se trata siempre como Markdown, nunca como HTML: ``MarkdownNoHTML``
hace que cualquier HTML/script embebido en el texto se muestre literal
(escapado) en vez de interpretarse o descartarse en silencio. No se llama
``setHtml`` con contenido del mensaje en ningún camino de este módulo, y al
usar ``QTextEdit`` (no ``QTextBrowser``) no hay navegación automática de
enlaces ni carga de recursos externos: la interacción de solo lectura no
incluye ``LinksAccessibleByMouse``.

B8b segmenta de forma determinista el contenido consolidado por sus bloques de
código cercados (```` ``` ````): cada tramo de prosa se sigue renderizando con
``_MessageBody``/``setMarkdown`` (sin reimplementar B8a) y cada bloque de
código se muestra en un área monoespaciada de solo lectura (también
``_MessageBody``, en modo texto plano — nunca interpretado como Markdown ni
HTML) con un botón "Copiar" que coloca el código exacto, sin vallas ni
identificador de lenguaje, en el portapapeles.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QResizeEvent, QTextDocument
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

_MARKDOWN_FEATURES = (
    QTextDocument.MarkdownFeature.MarkdownDialectGitHub
    | QTextDocument.MarkdownFeature.MarkdownNoHTML
)

# B8b: a fenced code block opens with ``` (optionally followed by a language
# token on the same line, e.g. ```python) and a newline, and closes at the
# next literal ```. Inline code (single backtick) never matches this and
# stays inside the surrounding prose, rendered by B8a's safe Markdown.
_FENCED_CODE_BLOCK = re.compile(r"```[^\n`]*\n(.*?)```", re.DOTALL)

# Holgura vertical para que la última línea no quede pegada al borde. No es un
# límite de altura: la altura sale siempre del alto real del documento.
_VERTICAL_PADDING = 8

# Ancho de reflujo provisional mientras el widget aún no tiene ancho real (no
# está dentro de la lista todavía). En cuanto lo tiene, ``resizeEvent``
# recalcula y ``height_changed`` propaga la altura verdadera.
_PROVISIONAL_WIDTH = 400


@dataclass(frozen=True)
class _Segment:
    is_code: bool
    text: str


def _segment_message(text: str) -> list[_Segment]:
    """Split ``text`` into prose/code segments, preserving the original order.

    Only complete, well-formed fenced blocks become code segments; an
    unterminated fence is left as prose. A message with no fenced block
    yields exactly one prose segment, so it renders identically to B8a.
    """
    segments: list[_Segment] = []
    cursor = 0
    for match in _FENCED_CODE_BLOCK.finditer(text):
        prose = text[cursor : match.start()]
        if prose:
            segments.append(_Segment(is_code=False, text=prose))
        code = match.group(1)
        # The newline right before the closing fence is the line terminator
        # of the code's last line, not part of the code itself.
        if code.endswith("\n"):
            code = code[:-1]
        segments.append(_Segment(is_code=True, text=code))
        cursor = match.end()
    trailing = text[cursor:]
    if trailing or not segments:
        segments.append(_Segment(is_code=False, text=trailing))
    return segments


class _MessageBody(QTextEdit):
    """Área de texto de solo lectura que ajusta su alto al contenido."""

    # Emitida cada vez que la altura fija realmente cambia (construcción con
    # ancho todavía no real, primer reflow con el ancho real de la columna,
    # o un resize posterior de la ventana) — quien contenga este widget debe
    # volver a pedir su tamaño y propagarlo al QListWidgetItem, porque Qt no
    # hace eso automáticamente por sí solo.
    height_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setReadOnly(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        # Sin barras propias: el alto del widget siempre iguala al del
        # documento, así que nunca hay contenido que quede fuera de la vista.
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("background: transparent; border: none;")
        self._content_height = 0
        # Un reajuste de alto puede provocar, por la cadena de señales, otro
        # cambio de geometría que vuelva a entrar aquí dentro de la misma
        # pila. En Windows eso ocurre de verdad: al acoplar la ventana el
        # sistema entrega WM_SIZE de forma síncrona durante SetWindowPos, así
        # que resizeEvent se reejecuta sin pasar por el bucle de eventos.
        self._syncing_height = False

    def set_markdown_content(self, text: str) -> None:
        self.document().setMarkdown(text, _MARKDOWN_FEATURES)
        self._sync_height()

    def set_plain_content(self, text: str) -> None:
        self.setPlainText(text)
        self._sync_height()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._sync_height()

    def sizeHint(self) -> QSize:
        """El alto pedido es el alto real del documento, nunca un valor fijo."""
        hint = super().sizeHint()
        if self._content_height:
            return QSize(hint.width(), self._content_height)
        return hint

    def minimumSizeHint(self) -> QSize:
        """Impide que el layout comprima el cuerpo y esconda líneas."""
        hint = super().minimumSizeHint()
        if self._content_height:
            return QSize(0, self._content_height)
        return hint

    def _sync_height(self) -> None:
        """Recalcula el alto pedido a partir del ancho disponible.

        El guardia protege el CÁLCULO, no el aviso. Mientras se mide no se
        puede volver a medir —ahí es donde se realimentaba—, pero la señal se
        emite ya fuera del guardia: lo que ocurra después es un recálculo
        legítimo con la geometría nueva, y suprimirlo dejaría alturas obsoletas.
        """
        if self._syncing_height:
            return
        self._syncing_height = True
        try:
            width = self.viewport().width() or self.width() or _PROVISIONAL_WIDTH
            self.document().setTextWidth(width)
            height = int(self.document().size().height()) + _VERTICAL_PADDING
            changed = self._content_height != height
            if changed:
                self._content_height = height
                self.updateGeometry()
        finally:
            self._syncing_height = False

        if changed:
            self.height_changed.emit()


class _CodeBlockWidget(QWidget):
    """Un bloque de código cercado: monoespaciado, de solo lectura, con "Copiar".

    ``code`` es el texto exacto entre las vallas (sin vallas ni identificador
    de lenguaje); "Copiar" lo coloca tal cual en el portapapeles del sistema.
    El área de texto reutiliza ``_MessageBody`` en modo texto plano (nunca
    Markdown ni HTML), por lo que cualquier HTML/script dentro del bloque se
    muestra siempre literal (SP-07).
    """

    def __init__(self, code: str) -> None:
        super().__init__()
        self._code = code

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        header = QHBoxLayout()
        header.addStretch(1)
        self.copy_button = QPushButton("Copiar")
        self.copy_button.setToolTip("Copiar el código de este bloque")
        self.copy_button.clicked.connect(self._copy_code)
        header.addWidget(self.copy_button)
        layout.addLayout(header)

        self.body = _MessageBody()
        monospace_font = QFont("monospace")
        monospace_font.setStyleHint(QFont.StyleHint.Monospace)
        self.body.setFont(monospace_font)
        self.body.set_plain_content(code)
        layout.addWidget(self.body)

    def _copy_code(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self._code)


class MessageItemDelegate(QStyledItemDelegate):
    """Evita que la lista pinte además el texto plano del item.

    ``QListWidgetItem.text()`` se conserva íntegro porque es el contrato de
    accesibilidad de B8a/RF-008: es lo que lee un lector de pantalla. El
    problema es que el delegate por defecto lo pintaba TAMBIÉN sobre la fila,
    en una sola línea y recortado con puntos suspensivos (``ElideRight`` es el
    valor por omisión de ``QListView``), justo debajo del ``MessageItemWidget``,
    que es transparente. El resultado visible eran dos textos superpuestos en
    el mismo rectángulo y una elipsis en mensajes que en realidad estaban
    completos.

    Aquí se sigue pintando el fondo y el estado de la fila, pero no el texto:
    el contenido visible lo aporta únicamente el widget.

    El vaciado se hace en ``initStyleOption`` y NO en ``paint``. Es
    imprescindible: ``QStyledItemDelegate.paint`` copia la opción que recibe y
    vuelve a llamar a ``initStyleOption`` sobre esa copia, de modo que
    cualquier texto borrado antes de delegar en ``super().paint`` reaparece.
    Como ``initStyleOption`` es virtual, vaciarlo aquí sí alcanza al pintado
    real.
    """

    def initStyleOption(
        self,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> None:
        super().initStyleOption(option, index)
        option.text = ""


class MessageItemWidget(QWidget):
    """Un mensaje completo (prefijo "Tú"/"Sirius" + cuerpo) para un item de la lista."""

    # Emitida cada vez que el tamaño real de este widget puede haber
    # cambiado (contenido nuevo o reflow tardío de algún segmento interno).
    # ``MainWindow`` la conecta a ``item.setSizeHint(widget.sizeHint())``
    # para que la fila reservada en el QListWidget nunca quede más baja de
    # lo que el contenido necesita.
    size_changed = Signal()

    # SIRIUS-ARQ-0.2 §3.6 (M6): emitida al pulsar «Proponer guardar…», solo
    # visible para un turno de Sirius ya completado (``set_message`` con
    # ``show_propose_suggestion=True``). Lleva el id del mensaje y su
    # contenido tal cual, para que quien la escuche —``MainWindow``— pueda
    # precargar el diálogo y llamar a
    # ``ProposeMemorySuggestionUseCase.propose(...)`` sin volver a leer nada
    # de este widget.
    propose_suggestion_requested = Signal(int, str)

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 6)
        layout.setSpacing(2)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self._prefix_label = QLabel()
        header.addWidget(self._prefix_label)
        header.addStretch(1)
        self._propose_suggestion_button = QPushButton("Proponer guardar…")
        self._propose_suggestion_button.setToolTip(
            "Proponer este mensaje como recuerdo, pendiente de confirmación."
        )
        self._propose_suggestion_button.setVisible(False)
        self._propose_suggestion_button.clicked.connect(self._emit_propose_suggestion_requested)
        header.addWidget(self._propose_suggestion_button)
        layout.addLayout(header)

        self._content_container = QWidget()
        self._content_layout = QVBoxLayout(self._content_container)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(4)
        layout.addWidget(self._content_container)

        self._segment_bodies: list[_MessageBody] = []
        # Mismo motivo que en ``_MessageBody``: la cadena de señales puede
        # volver a entrar aquí dentro de la misma pila.
        self._syncing_size = False
        # Último tamaño anunciado: solo se avisa cuando cambia de verdad.
        self._last_hint = QSize()
        self._message_id: int | None = None
        self._raw_content = ""

    def _emit_propose_suggestion_requested(self) -> None:
        if self._message_id is not None:
            self.propose_suggestion_requested.emit(self._message_id, self._raw_content)

    def set_message(
        self,
        prefix: str,
        body_text: str,
        *,
        bold: bool,
        message_id: int | None = None,
        show_propose_suggestion: bool = False,
    ) -> None:
        """Renderiza el contenido final consolidado, segmentado en prosa Markdown
        segura (B8a) y bloques de código copiables (B8b), en el orden original.

        ``show_propose_suggestion`` (M6, §3.6) solo la marca ``True`` el
        llamador para un turno de Sirius ya completado; ``message_id`` es
        entonces el id de ese mensaje, el que
        ``ProposeMemorySuggestionUseCase.propose(...)`` recibirá como
        ``message_id`` si se pulsa el botón.
        """
        self._set_prefix(prefix, bold=bold)
        self._clear_content()
        self._message_id = message_id
        self._raw_content = body_text
        self._propose_suggestion_button.setVisible(show_propose_suggestion)
        for segment in _segment_message(body_text):
            if segment.is_code:
                block = _CodeBlockWidget(segment.text)
                block.body.height_changed.connect(self._on_segment_height_changed)
                self._content_layout.addWidget(block)
                self._segment_bodies.append(block.body)
            else:
                prose = _MessageBody()
                prose.height_changed.connect(self._on_segment_height_changed)
                prose.set_markdown_content(segment.text)
                self._content_layout.addWidget(prose)
                self._segment_bodies.append(prose)
        self._sync_size_when_laid_out()

    def set_streaming_text(self, prefix: str, body_text: str, *, bold: bool) -> None:
        """Renderiza el texto parcial en streaming como texto plano, en un único
        tramo sin segmentar (más simple y estable, decisión de B8a).

        Un turno todavía en streaming no está completado, así que
        «Proponer guardar…» (M6, §3.6) se mantiene oculto aquí sin
        excepción; solo ``set_message`` puede volver a mostrarlo.
        """
        self._set_prefix(prefix, bold=bold)
        self._clear_content()
        self._propose_suggestion_button.setVisible(False)
        plain = _MessageBody()
        plain.height_changed.connect(self._on_segment_height_changed)
        plain.set_plain_content(body_text)
        self._content_layout.addWidget(plain)
        self._segment_bodies.append(plain)
        self._sync_size_when_laid_out()

    def rendered_plain_text(self) -> str:
        """The concatenated plain text of every segment, prose and code alike,
        in order — e.g. to assert Markdown syntax is gone and code is intact."""
        return "\n".join(body.toPlainText() for body in self._segment_bodies)

    def rendered_html(self) -> str:
        """The concatenated rich text of every segment — e.g. to assert raw HTML
        stayed escaped everywhere (SP-07), including inside a code block."""
        return "".join(body.toHtml() for body in self._segment_bodies)

    def propose_suggestion_button(self) -> QPushButton:
        """«Proponer guardar…» (M6, §3.6) — visible only when ``set_message``
        was last called with ``show_propose_suggestion=True``."""
        return self._propose_suggestion_button

    def copy_buttons(self) -> list[QPushButton]:
        """The "Copiar" buttons currently shown, one per code block, in order."""
        buttons: list[QPushButton] = []
        for i in range(self._content_layout.count()):
            item = self._content_layout.itemAt(i)
            widget = item.widget() if item is not None else None
            if isinstance(widget, _CodeBlockWidget):
                buttons.append(widget.copy_button)
        return buttons

    def _set_prefix(self, prefix: str, *, bold: bool) -> None:
        font = self._prefix_label.font()
        font.setBold(bold)
        self._prefix_label.setFont(font)
        self._prefix_label.setText(prefix)

    def _clear_content(self) -> None:
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self._segment_bodies = []
        # El alto pedido que se recuerda pertenecía al contenido que se acaba
        # de tirar, así que deja de ser una referencia válida y hay que
        # olvidarlo. Conservarlo suprimía el aviso que corrige la fila:
        # `_sync_size` solo emite `size_changed` cuando el tamaño pedido
        # CAMBIA, y al consolidar un mensaje de streaming el contenido nuevo
        # acaba pidiendo el mismo alto que pedía el anterior. Con `_last_hint`
        # todavía en ese valor, la comparación daba "sin cambios" y no se
        # emitía nada —pero para entonces `MainWindow` ya había sincronizado la
        # fila con un `sizeHint` prematuro, medido antes de que el cuerpo nuevo
        # recibiera el ancho real de la columna—. La fila se quedaba con aquel
        # alto corto (24 px con un contenido que necesita 54) y el mensaje
        # aparecía recortado justo al terminar de escribirse.
        self._last_hint = QSize()

    def _on_segment_height_changed(self) -> None:
        self._sync_size()

    def _sync_size_when_laid_out(self) -> None:
        """Vuelve a medir en cuanto el layout haya colocado el contenido nuevo.

        Medir justo después de reconstruir el contenido da un tamaño prematuro:
        los cuerpos se rellenan ANTES de entrar en el layout, así que miden con
        el ancho provisional y no vuelven a avisar si el ancho real da el mismo
        alto. El `sizeHint` del widget sí cambia después, por su cuenta y sin
        señal, cuando Qt coloca los hijos — y para entonces `MainWindow` ya ha
        sincronizado la fila con el valor prematuro.

        Ese era el mensaje recortado al terminar de escribirse: la fila se
        quedaba en 24 px con un contenido que pedía 54. Una segunda pasada en
        el turno siguiente del bucle de eventos compara ya el tamaño asentado y
        emite el aviso que corrige la fila. No es una espera arbitraria: es el
        primer instante en que la medida es válida.
        """
        self._sync_size()
        # Atado a ``self``: Qt cancela el disparo si el widget muere antes de
        # que llegue. Sin el contexto, un widget destruido entre medias hacía
        # que ``_sync_size`` tocara un layout ya borrado —«Internal C++ object
        # already deleted»— y la excepción salía en el bucle de eventos, es
        # decir en cualquier prueba que estuviera corriendo en ese momento, no
        # en la que creó el widget.
        QTimer.singleShot(0, self, self._sync_size)

    def _sync_size(self) -> None:
        """Avisa de que el alto pedido cambió. NO impone geometría propia.

        Antes esto llamaba a ``adjustSize()``, y esa llamada era el motor del
        bucle: ``adjustSize`` redimensiona el widget al ancho de su propio
        sizeHint, pero quien manda sobre su geometría es el contenedor (la
        lista, o el layout que lo aloja), que acto seguido le reimpone el ancho
        de la columna. Cada ida y vuelta reflui el texto a un alto distinto,
        que dispara otro ``height_changed``, que vuelve a llamar aquí. Además
        de realimentarse, se veía: con el contenedor a 900 px el cuerpo se
        quedaba clavado en 256, el ancho que ``adjustSize`` le imponía.

        El alto correcto llega igualmente al contenedor por ``sizeHint()``,
        que sí refleja el alto real del documento; no hace falta forzar
        ninguna geometría desde aquí.
        """
        if self._syncing_size:
            return
        self._syncing_size = True
        try:
            # Recalcular el layout SIN redimensionar el widget: ``activate()``
            # refresca el sizeHint que el contenedor va a leer, que es lo único
            # que hacía falta de ``adjustSize``, pero no toca la geometría, que
            # es lo que realimentaba el bucle.
            # ``invalidate()`` tira la caché de sizeHint; ``activate()`` la
            # recalcula. Hay que hacerlo en los DOS niveles: los cuerpos viven
            # en ``_content_layout``, dentro de ``_content_container``, y si
            # solo se invalida el layout exterior el contenedor sigue
            # devolviendo el alto del ancho ANTERIOR. Ese desfase de un paso
            # era lo que ``adjustSize`` tapaba, al coste de pelearse con la
            # geometría y realimentar el bucle.
            self._content_layout.invalidate()
            self._content_container.updateGeometry()
            layout = self.layout()
            if layout is not None:
                layout.invalidate()
                layout.activate()
            self.updateGeometry()
            hint = self.sizeHint()
            changed = hint != self._last_hint
            if changed:
                self._last_hint = hint
        finally:
            self._syncing_size = False

        # El aviso va fuera del guardia, para que el recálculo legítimo que
        # provoque no quede suprimido; y solo se emite si el tamaño pedido
        # cambió de verdad. Esa condición es la que hace converger la cadena:
        # cuando la medida se estabiliza, deja de haber avisos y el ciclo
        # termina solo, en vez de rebotar indefinidamente.
        if changed:
            self.size_changed.emit()
