"""Separar la sugerencia de recuerdo del texto que da un modelo (SIRIUS-ARQ-0.2 §3.2).

``render_instructions()`` pide al modelo que, si hay algo que merezca recordarse,
lo añada al final de su respuesta detrás de ``MEMORY_SUGGESTION_DELIMITER``. Todo
adaptador de ``LLMProvider`` tiene que quitar el delimitador y lo que le sigue
antes de que exista un solo ``LLMTextDelta`` o un evento final. Vivía dentro del
adaptador de OpenAI; desde que la charla puede ir también por Ollama (pieza C de
ADR-233), lo usan los dos y vive aquí.
"""

from __future__ import annotations

from sirius.ports.llm import MEMORY_SUGGESTION_DELIMITER


def split_delimiter(
    raw: str, delimiter: str = MEMORY_SUGGESTION_DELIMITER
) -> tuple[str, str | None]:
    """One-shot split of an already-complete raw string (§3.2). Used only as
    the defensive fallback for a response with no incremental deltas at all;
    the real streaming path uses ``MemorySuggestionSplitter`` instead, which
    stays safe across chunk boundaries."""
    index = raw.find(delimiter)
    if index == -1:
        return raw, None
    return raw[:index], raw[index + len(delimiter) :].strip() or None


def longest_prefix_as_suffix(text: str, delimiter: str) -> int:
    """Length of the longest suffix of ``text`` that is also a prefix of
    ``delimiter`` — the only part of ``text`` that could still turn into the
    delimiter once more raw output arrives."""
    max_check = min(len(text), len(delimiter) - 1)
    for length in range(max_check, 0, -1):
        if text.endswith(delimiter[:length]):
            return length
    return 0


class MemorySuggestionSplitter:
    """Splits a raw provider text stream into delimiter-free chunks plus an
    optional trailing memory suggestion (SIRIUS-ARQ-0.2 §3.2).

    Streaming-safe: at most ``len(delimiter) - 1`` trailing characters are
    ever held back between calls to ``feed``, so an occurrence of the
    delimiter split across two (or more) consecutive raw chunks is still
    detected — the safe prefix already returned by an earlier call never
    contains the delimiter or any part of the raw proposal.
    """

    def __init__(self, delimiter: str = MEMORY_SUGGESTION_DELIMITER) -> None:
        self._delimiter = delimiter
        self._pending = ""
        self._found = False
        self._suggestion_parts: list[str] = []

    def feed(self, raw_chunk: str) -> str:
        """Consume one raw chunk; return the portion, if any, safe to show/persist now."""
        if self._found:
            self._suggestion_parts.append(raw_chunk)
            return ""
        self._pending += raw_chunk
        index = self._pending.find(self._delimiter)
        if index != -1:
            safe = self._pending[:index]
            after = self._pending[index + len(self._delimiter) :]
            self._found = True
            self._pending = ""
            if after:
                self._suggestion_parts.append(after)
            return safe
        overlap = longest_prefix_as_suffix(self._pending, self._delimiter)
        if overlap == 0:
            safe, self._pending = self._pending, ""
            return safe
        safe, self._pending = self._pending[:-overlap], self._pending[-overlap:]
        return safe

    def finish(self, *, completed: bool) -> tuple[str, str | None]:
        """Call once the raw stream ends (successfully, cancelled, or failed).

        ``completed`` must be ``True`` only for a genuine ``response.completed``
        terminal event; ``False`` for cancellation, failure, or any other
        anomalous end. When ``self._pending`` still holds text (at most
        ``len(delimiter) - 1`` characters — see the class docstring), that
        text is only known to be ordinary trailing content once the stream
        has truly completed with no more raw output coming; on any anomalous
        end it could still turn into the delimiter, so it must be discarded
        rather than surfacing it as visible/persisted text.

        Returns ``(trailing_safe_text, memory_suggestion)``: whatever safe
        text was still held back, and the proposal — stripped, or ``None`` if
        empty or the delimiter never appeared. Idempotent-shaped: safe to call
        exactly once per stream, which every call site here does.
        """
        if self._found:
            return "", "".join(self._suggestion_parts).strip() or None
        trailing, self._pending = self._pending, ""
        return (trailing, None) if completed else ("", None)
