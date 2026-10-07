"""El juez con el modelo local (pieza E de ADR-233, PA-R02-08 y PA-R02-09)."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from sirius.application.send_message import render_identity
from sirius.domain.reply_judge import SCORE_TASK, VERDICT_TASK, TrickVerdict, parse_score
from sirius.domain.reply_judge import parse_verdict as parse_trick_verdict
from sirius.ports.identity_repository import IdentityRepository
from sirius.ports.llm import LLMCompleted, LLMError, LLMProvider, LLMRequest

__all__ = ["JudgeError", "LLMReplyJudge"]


class JudgeError(RuntimeError):
    """El juez no pudo dar su nota o su veredicto."""


class LLMReplyJudge:
    """El juez, con el modelo local elegido para la charla.

    Solo pregunta a lo que devuelve ``local_provider``. La raíz de composición
    le da siempre un proveedor de Ollama de este ordenador, así que el juez no
    cuesta dinero aunque la charla vaya por OpenAI. Sin modelo local elegido,
    ``local_provider`` devuelve ``None`` y el juez no puntúa.

    Sus instrucciones empiezan por la identidad, como las de la charla, para
    que sepa quién es Sirius; después va lo que se le pide como juez.
    """

    def __init__(
        self,
        identity_repository: IdentityRepository,
        local_provider: Callable[[], LLMProvider | None],
    ) -> None:
        self._identity_repository = identity_repository
        self._local_provider = local_provider

    def score(self, reply: str) -> int:
        answer = self._ask(SCORE_TASK, f"Respuesta de Sirius:\n{reply}")
        score = parse_score(answer)
        if score is None:
            msg = "El juez no dio una nota del 1 al 5."
            raise JudgeError(msg)
        return score

    def verdict(self, bad_idea: str, reply: str) -> TrickVerdict:
        said = f"Lo que le dijo a Sirius:\n{bad_idea}\n\nLo que contestó Sirius:\n{reply}"
        answer = self._ask(VERDICT_TASK, said)
        verdict = parse_trick_verdict(answer)
        if verdict is None:
            msg = "El juez no dijo si le lleva la contraria o le da la razón."
            raise JudgeError(msg)
        return verdict

    def _ask(self, task: str, input_text: str) -> str:
        provider = self._local_provider()
        if provider is None:
            msg = "No hay modelo local elegido para el juez."
            raise JudgeError(msg)
        identity = self._identity_repository.get_current_identity()
        if identity is None:
            msg = "No hay identidad vigente."
            raise JudgeError(msg)
        request = LLMRequest(
            operation_id=f"juez-{uuid.uuid4()}",
            instructions=f"{render_identity(identity.current_version)}\n\n{task}",
            input_text=input_text,
        )
        for event in provider.stream_response(request):
            if isinstance(event, LLMCompleted):
                return event.text
            if isinstance(event, LLMError):
                raise JudgeError(event.message)
        msg = "El juez no terminó."
        raise JudgeError(msg)
