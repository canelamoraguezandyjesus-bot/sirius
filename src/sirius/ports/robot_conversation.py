"""Puertos de la charla del robot: modo, marcas y resúmenes (pieza D de ADR-233), el juez (E)
y el sueño (G)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Protocol

from sirius.domain.conversation_mode import ConversationMode
from sirius.domain.conversation_summary import ConversationSummary
from sirius.domain.facts import ProposedFact
from sirius.domain.reply_judge import JudgeScore, TrickVerdict
from sirius.domain.reply_mark import MarkedReply, ReplyMark
from sirius.ports.llm import LLMProvider


class ConversationModeRepository(Protocol):
    def get_mode(self, conversation_id: int) -> ConversationMode:
        """El modo vigente; normal si nunca cambió."""
        ...

    def set_mode(self, conversation_id: int, mode: ConversationMode) -> None: ...


class ReplyMarkRepository(Protocol):
    def record_model(self, message_id: int, model: str | None) -> None:
        """Apunta con qué modelo se dio una respuesta, al darla."""
        ...

    def set_mark(self, message_id: int, mark: ReplyMark) -> None:
        """Marca una respuesta de Sirius; marcarla otra vez cambia la marca."""
        ...

    def marked_replies(self) -> list[MarkedReply]:
        """Las respuestas marcadas, en el orden de la charla."""
        ...


class ConversationSummaryRepository(Protocol):
    def latest(self, conversation_id: int) -> ConversationSummary | None: ...

    def add(self, conversation_id: int, up_to_sequence: int, content: str) -> None: ...


class ConversationSummarizer(Protocol):
    def summarize(self, text: str, provider: LLMProvider) -> str:
        """Resume ``text`` con el modelo de la charla. Puede fallar con cualquier error."""
        ...


class JudgeScoreRepository(Protocol):
    def add_score(self, message_id: int, score: int, *, warned: bool) -> None:
        """Guarda la nota del juez a una respuesta y si con ella avisó."""
        ...

    def judge_scores(self) -> list[JudgeScore]:
        """Las notas del juez, en el orden de las respuestas."""
        ...

    def unjudged_replies(self) -> list[tuple[int, str]]:
        """Las respuestas completas de la 0.2 que el juez aún no ha puntuado, en orden.

        De la 0.2 son las que tienen apuntado con qué modelo se dieron (pieza D):
        las de antes se dieron con otra semilla y no se puntúan.
        """
        ...


class ReplyJudge(Protocol):
    """El juez (pieza E de ADR-233). Sus dos preguntas pueden fallar con cualquier error."""

    def score(self, reply: str) -> int:
        """Del 1 al 5, cuánto suena a Sirius ``reply``."""
        ...

    def verdict(self, bad_idea: str, reply: str) -> TrickVerdict:
        """Si ``reply`` le lleva la contraria a ``bad_idea`` o le da la razón."""
        ...


class DaySummaryRepository(Protocol):
    """Los resúmenes del día que deja el sueño (pieza G de ADR-233, ADR-239)."""

    def save_day(self, day: date, content: str) -> None: ...

    def day_summary(self, day: date) -> str | None: ...

    def latest_days(self, limit: int) -> list[tuple[date, str]]:
        """Los últimos ``limit`` días resumidos, del más viejo al más nuevo."""
        ...

    def dreamed_days(self) -> set[date]: ...


class FactExtractor(Protocol):
    """El sueño: saca hechos de lo que dijo el propietario un día (pieza G, ADR-239)."""

    def extract(self, text: str, provider: LLMProvider) -> Sequence[ProposedFact]:
        """Los hechos que propone ``text``, con el modelo ``provider``. Puede fallar."""
        ...
