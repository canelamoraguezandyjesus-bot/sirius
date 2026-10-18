"""Marcar respuestas, soltar el modo y resumir la charla (pieza D de ADR-233), y el juez (E)."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from sirius.domain.conversation import MessageStatus
from sirius.domain.conversation_mode import ConversationMode
from sirius.domain.conversation_summary import messages_to_summarize, summary_input
from sirius.domain.reply_judge import (
    HIGHEST_SCORE,
    LOWEST_SCORE,
    JudgeScore,
    is_low,
    recent_mean,
    warns,
)
from sirius.domain.reply_mark import MarkedReply, ReplyMark
from sirius.infrastructure.logging import get_logger
from sirius.ports.conversation_repository import ConversationRepository
from sirius.ports.llm import LLMCancelled, LLMCompleted, LLMError, LLMProvider, LLMRequest
from sirius.ports.robot_conversation import (
    ConversationModeRepository,
    ConversationSummarizer,
    ConversationSummaryRepository,
    JudgeScoreRepository,
    ReplyJudge,
    ReplyMarkRepository,
)

__all__ = [
    "ConversationModeUseCase",
    "ConversationSummaryService",
    "LLMConversationSummarizer",
    "MarkReplyUseCase",
    "ReplyJudgeService",
    "SummaryCut",
    "summary_operation_id",
]

_logger = get_logger(__name__)


class MarkReplyUseCase:
    """«Eso es Sirius» y «eso no» en cada respuesta (PA-R02-06)."""

    def __init__(self, repository: ReplyMarkRepository) -> None:
        self._repository = repository

    def possible_marks(self) -> frozenset[ReplyMark]:
        return frozenset(ReplyMark)

    def mark(self, message_id: int, mark: ReplyMark) -> None:
        self._repository.set_mark(message_id, mark)

    def marked_replies(self) -> list[MarkedReply]:
        return self._repository.marked_replies()

    def recent(self, last: int) -> list[MarkedReply]:
        """Las ``last`` últimas respuestas marcadas: las que cuenta ``count``."""
        return self._repository.marked_replies()[-last:] if last > 0 else []

    def count(self, last: int) -> tuple[int, int]:
        """Cuántas «eso es Sirius» hay entre las ``last`` últimas marcadas, y cuántas son."""
        recientes = self.recent(last)
        sirius = sum(1 for reply in recientes if reply.mark is ReplyMark.ES_SIRIUS)
        return sirius, len(recientes)


class ConversationModeUseCase:
    """El modo de la charla tal como lo ve y lo suelta la ventana (PA-R02-04)."""

    def __init__(
        self,
        conversation_repository: ConversationRepository,
        mode_repository: ConversationModeRepository,
    ) -> None:
        self._conversation_repository = conversation_repository
        self._mode_repository = mode_repository

    def current(self) -> ConversationMode:
        conversation = self._conversation_repository.get_main_conversation()
        if conversation is None:
            return ConversationMode.NORMAL
        return self._mode_repository.get_mode(conversation.id)

    def release(self) -> None:
        """Lo mismo que «ya puedes volver a ser tú», con el botón."""
        conversation = self._conversation_repository.get_main_conversation()
        if conversation is not None:
            self._mode_repository.set_mode(conversation.id, ConversationMode.NORMAL)


class ConversationSummaryService:
    """Resume la charla cuando toca (PA-R02-05). Si falla, la charla sigue."""

    def __init__(
        self,
        conversation_repository: ConversationRepository,
        summary_repository: ConversationSummaryRepository,
        summarizer: ConversationSummarizer,
    ) -> None:
        self._conversation_repository = conversation_repository
        self._summary_repository = summary_repository
        self._summarizer = summarizer

    def maybe_summarize(
        self, conversation_id: int, provider: LLMProvider, operation_id: str | None = None
    ) -> bool:
        """Resume si hay 18 turnos sin resumir. Devuelve si guardó un resumen.

        ``operation_id`` es el del turno que acaba: la petición del resumen lleva
        ``summary_operation_id`` de él, y cortar ese turno la corta también. Un resumen
        cortado no guarda nada, y lo hace el turno siguiente (ADR-254).
        """
        previous = self._summary_repository.latest(conversation_id)
        since = previous.up_to_sequence if previous is not None else 0
        unsummarized = [
            message
            for message in self._conversation_repository.list_messages(conversation_id)
            if message.status is MessageStatus.COMPLETED and message.sequence > since
        ]
        to_summarize = messages_to_summarize(unsummarized, after_a_summary=previous is not None)
        if not to_summarize:
            return False
        text = summary_input(previous.content if previous is not None else None, to_summarize)
        request_id = summary_operation_id(operation_id) if operation_id is not None else None
        try:
            content = self._summarizer.summarize(text, provider, request_id).strip()
        except SummaryCut:
            _logger.info("Le cortaron mientras resumía: lo resume el turno siguiente")
            return False
        except Exception as exc:  # resumir nunca puede romper la charla
            _logger.warning("No se pudo resumir la charla (%s)", type(exc).__name__)
            return False
        if not content:
            return False
        self._summary_repository.add(conversation_id, to_summarize[-1].sequence, content)
        return True


class ReplyJudgeService:
    """El juez de cada respuesta (PA-R02-08): puntúa, guarda la nota y avisa si baja.

    No va dentro del turno: la ventana lo lanza en segundo plano al acabar cada
    uno, con la respuesta ya en pantalla, porque el modelo no debe meterse en el
    turno (inf. 3) y una petición de más en cada mensaje la notaría el
    propietario. Si el juez falla o no da una nota del 1 al 5, esa respuesta se
    queda sin nota y la charla sigue: el juez es un aviso, no una puerta.
    """

    def __init__(self, judge: ReplyJudge, repository: JudgeScoreRepository) -> None:
        self._judge = judge
        self._repository = repository

    def judge_pending(self, should_stop: Callable[[], bool] = lambda: False) -> bool:
        """Puntúa, en orden, las respuestas que aún no tienen nota. Devuelve si avisó.

        ``should_stop`` se mira antes de cada una: la ventana lo usa para que el
        juez deje libre el modelo cuando el propietario escribe. Si el juez falla
        con una respuesta, para ahí y lo intenta la vez siguiente.
        """
        warned_now = False
        scores = [judged.score for judged in self._repository.judge_scores()]
        for message_id, reply in self._repository.unjudged_replies():
            if should_stop():
                break
            try:
                score = self._judge.score(reply, should_stop=should_stop)
            except Exception as exc:  # el juez nunca puede romper la charla
                # Si le pidieron parar, es su nota cortada (cancel): eso no es un fallo.
                if not should_stop():
                    _logger.warning("El juez no pudo puntuar (%s)", type(exc).__name__)
                break
            if not LOWEST_SCORE <= score <= HIGHEST_SCORE:
                _logger.warning("El juez dio una nota fuera de escala: %s", score)
                break
            scores.append(score)
            warned = warns(scores)
            self._repository.add_score(message_id, score, warned=warned)
            warned_now = warned_now or warned
        return warned_now

    def cancel(self) -> None:
        """Corta la nota que está pidiendo, si pide una: esa respuesta se queda sin nota y
        se puntúa la vez siguiente (ADR-252)."""
        self._judge.cancel()

    def scores(self) -> list[JudgeScore]:
        return self._repository.judge_scores()

    def recent_mean(self) -> float | None:
        """La media de las 10 últimas notas, o ``None`` si aún no hay 10."""
        return recent_mean([judged.score for judged in self._repository.judge_scores()])

    def is_low(self) -> bool:
        """Si la media de las 10 últimas está por debajo de 3,5: la ventana lo enseña."""
        return is_low([judged.score for judged in self._repository.judge_scores()])


_SUMMARY_NOT_FINISHED = "El resumen no terminó."

_SUMMARY_INSTRUCTIONS = (
    "Resume esta charla entre Sirius y su dueño en español, en pocas líneas y en tercera "
    "persona. Conserva nombres, fechas, lo que se decidió y lo que quedó pendiente. No "
    "inventes nada que no esté en el texto."
)


def summary_operation_id(operation_id: str) -> str:
    """La operación del resumen que se pide al acabar el turno ``operation_id``: cortar el
    turno corta también su resumen, y lo nuevo no espera a él (ADR-254)."""
    return f"resumen-{operation_id}"


class SummaryCut(RuntimeError):
    """Le cortaron al modelo el resumen a mitad: no se guarda nada (ADR-254)."""


class LLMConversationSummarizer:
    """Resume con el mismo modelo que conversa: la charla no sale del ordenador."""

    def summarize(self, text: str, provider: LLMProvider, operation_id: str | None = None) -> str:
        request = LLMRequest(
            operation_id=operation_id or summary_operation_id(str(uuid.uuid4())),
            instructions=_SUMMARY_INSTRUCTIONS,
            input_text=text,
        )
        for event in provider.stream_response(request):
            if isinstance(event, LLMCompleted):
                return event.text
            if isinstance(event, LLMError):
                raise RuntimeError(event.message)
            if isinstance(event, LLMCancelled):
                raise SummaryCut(_SUMMARY_NOT_FINISHED)
        raise RuntimeError(_SUMMARY_NOT_FINISHED)
