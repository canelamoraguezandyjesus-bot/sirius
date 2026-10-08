"""El sueño: resumir el día y proponer hechos (pieza G de ADR-233, ADR-239).

El paso 4 de la memoria: «"Sueño" nocturno: con el ordenador libre, el modelo
resume el día y propone hechos nuevos. Quedan pendientes del sí del propietario».

- **Solo lee lo que dijo el propietario.** Pide a la conversación sus mensajes, y
  se queda con los suyos por quién los escribió: lo que dijo Sirius ni siquiera
  se lee (PA-R02-14).
- **Solo con el modelo de este ordenador**, el de Ollama elegido para la charla,
  como el juez: el sueño nunca pregunta a OpenAI y no cuesta dinero. Sin modelo
  local, no sueña.
- **Nada entra sin su sí.** Los hechos que propone quedan como sugerencias; los
  que ya están apuntados o pendientes no se vuelven a proponer.

La ventana sueña al abrirse los días anteriores que aún no ha soñado, en segundo
plano. Si falla, ese día se queda sin soñar y lo intenta la vez siguiente.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from datetime import UTC, date, timedelta

from sirius.application.facts import FactProposals
from sirius.domain.conversation import Message, MessageRole, MessageStatus
from sirius.domain.facts import OWNER, Certainty, ProposedFact, is_sirius, person_key
from sirius.domain.plain_text import plain
from sirius.infrastructure.logging import get_logger
from sirius.ports.conversation_repository import ConversationRepository
from sirius.ports.llm import LLMCompleted, LLMError, LLMProvider, LLMRequest
from sirius.ports.memory_repository import FactRepository
from sirius.ports.memory_suggestion_repository import MemorySuggestionRepository
from sirius.ports.robot_conversation import (
    ConversationSummarizer,
    DaySummaryRepository,
    FactExtractor,
)

__all__ = ["DAYS_BACK", "DreamService", "LLMFactExtractor", "parse_facts", "said_on"]

_logger = get_logger(__name__)

#: Cuántos días atrás sueña como mucho al abrirse la ventana.
DAYS_BACK = 7


def said_on(message: Message) -> date:
    """El día en que se dijo ``message``, en la hora de este ordenador."""
    created = message.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return created.astimezone().date()


class DreamService:
    """Sueña un día: lo resume, guarda el resumen y deja propuestos los hechos nuevos."""

    def __init__(
        self,
        conversations: ConversationRepository,
        days: DaySummaryRepository,
        summarizer: ConversationSummarizer,
        extractor: FactExtractor,
        proposals: FactProposals,
        facts: FactRepository,
        suggestions: MemorySuggestionRepository,
        local_model: Callable[[], LLMProvider | None],
    ) -> None:
        self._conversations = conversations
        self._days = days
        self._summarizer = summarizer
        self._extractor = extractor
        self._proposals = proposals
        self._facts = facts
        self._suggestions = suggestions
        self._local_model = local_model

    def dream(self, day: date) -> list[ProposedFact]:
        """Sueña ``day``. Devuelve los hechos que deja propuestos."""
        said = self._said_by_owner(day)
        if not said:
            return []
        provider = self._local_model()
        if provider is None:
            _logger.info("Sin modelo de este ordenador: hoy no sueña")
            return []
        text = "\n".join(f"Él: {line}" for line in said)
        try:
            summary = self._summarizer.summarize(text, provider).strip()
        except Exception as exc:  # soñar nunca puede romper nada: se intenta otro día
            _logger.warning("El sueño no pudo resumir el día (%s)", type(exc).__name__)
            summary = ""
        if summary:
            self._days.save_day(day, summary)
        try:
            proposed = list(self._extractor.extract(text, provider))
        except Exception as exc:  # sin hechos propuestos, el resumen ya quedó
            _logger.warning("El sueño no pudo proponer hechos (%s)", type(exc).__name__)
            return []
        new = [fact for fact in proposed if fact.text.strip() and not self._already_known(fact)]
        for fact in new:
            try:
                self._proposals.propose(fact, by_sirius=True)
            except ValueError as exc:  # p. ej., un hecho con «quién lo dijo» Sirius
                _logger.warning("El sueño propuso un hecho que no vale (%s)", exc)
        return new

    def dream_pending(self, today: date, should_stop: Callable[[], bool] = lambda: False) -> int:
        """Sueña los días anteriores a ``today`` que aún no tienen resumen. Devuelve cuántos."""
        dreamed = self._days.dreamed_days()
        days = sorted(
            {
                said_on(message)
                for message in self._owner_messages()
                if today - timedelta(days=DAYS_BACK) <= said_on(message) < today
            }
            - dreamed
        )
        done = 0
        for day in days:
            if should_stop():
                break
            self.dream(day)
            done += 1
        return done

    def latest_summary(self) -> str | None:
        """El resumen del último día soñado, o ``None`` si aún no ha soñado ninguno."""
        days = self._days.latest_days(1)
        return days[-1][1] if days else None

    def _said_by_owner(self, day: date) -> list[str]:
        """Lo que dijo el propietario ``day``: solo sus mensajes, nunca los de Sirius."""
        return [
            message.content or "" for message in self._owner_messages() if said_on(message) == day
        ]

    def _owner_messages(self) -> list[Message]:
        conversation = self._conversations.get_main_conversation()
        if conversation is None:
            return []
        return [
            message
            for message in self._conversations.list_messages(conversation.id)
            if message.role is MessageRole.USER
            and message.status is MessageStatus.COMPLETED
            and message.content
        ]

    def _already_known(self, fact: ProposedFact) -> bool:
        """Si ya está apuntado como hecho vigente, o propuesto, o él ya dijo que no."""
        text = plain(fact.text).strip()
        for memory in self._facts.list_current_facts(fact.person):
            if plain(memory.current_revision.content or "").strip() == text:
                return True
        for suggestion in self._suggestions.list_pending_suggestions():
            same_person = person_key(suggestion.person or "") == person_key(fact.person)
            if same_person and plain(suggestion.content).strip() == text:
                return True
        return False


_EXTRACT_INSTRUCTIONS = (
    "Te paso lo que te contó hoy tu dueño, solo sus frases. Saca los hechos que merezca "
    "la pena recordar de él o de las personas que nombra: dónde vive, a qué se dedica, "
    "gustos, fechas, quién dijo qué. Contesta solo con líneas JSON, una por hecho, así: "
    '{"persona": "propietario", "tema": "trabajo", "texto": "Trabaja de electricista", '
    '"dicho_por": "propietario", "seguridad": "segura", "desde": "2026-09-01"}. '
    "«persona» es «propietario» si el hecho es suyo, o el nombre de la otra persona. "
    "«dicho_por» es quién lo dijo, según él. «seguridad» es «dudosa» si no lo tenía "
    "claro. «desde» solo si dijo desde cuándo. No inventes nada. Si no hay hechos, "
    "contesta con una línea vacía."
)


class LLMFactExtractor:
    """Saca hechos con el modelo de este ordenador, en líneas JSON que se leen con cuidado."""

    def extract(self, text: str, provider: LLMProvider) -> list[ProposedFact]:
        request = LLMRequest(
            operation_id=f"sueno-{uuid.uuid4()}",
            instructions=_EXTRACT_INSTRUCTIONS,
            input_text=text,
        )
        for event in provider.stream_response(request):
            if isinstance(event, LLMCompleted):
                return parse_facts(event.text)
            if isinstance(event, LLMError):
                raise RuntimeError(event.message)
        msg = "El sueño no terminó."
        raise RuntimeError(msg)


def parse_facts(text: str) -> list[ProposedFact]:
    """Los hechos de la respuesta del modelo. Lo que no se entiende, se deja fuera.

    Nunca un hecho que dijo Sirius: si el modelo lo propone, no se lee.
    """
    items: list[object] = []
    stripped = text.strip()
    if stripped.startswith("["):
        try:
            loaded = json.loads(stripped)
        except ValueError:
            loaded = []
        items = list(loaded) if isinstance(loaded, list) else []
    else:
        for line in stripped.splitlines():
            line = line.strip().rstrip(",")
            if not line.startswith("{"):
                continue
            try:
                items.append(json.loads(line))
            except ValueError:
                continue
    facts: list[ProposedFact] = []
    for item in items:
        fact = _fact_from(item)
        if fact is not None:
            facts.append(fact)
    return facts


def _fact_from(item: object) -> ProposedFact | None:
    if not isinstance(item, dict):
        return None
    person, text = item.get("persona"), item.get("texto")
    if not isinstance(person, str) or not isinstance(text, str):
        return None
    if not person.strip() or not text.strip():
        return None
    topic = item.get("tema")
    said_by = item.get("dicho_por")
    said_by = said_by.strip() if isinstance(said_by, str) and said_by.strip() else OWNER
    if is_sirius(said_by):
        return None
    certainty = Certainty.DOUBTFUL if item.get("seguridad") == "dudosa" else Certainty.SURE
    since = None
    raw_since = item.get("desde")
    if isinstance(raw_since, str):
        try:
            since = date.fromisoformat(raw_since.strip())
        except ValueError:
            since = None
    return ProposedFact(
        person=person.strip(),
        topic=topic.strip() if isinstance(topic, str) and topic.strip() else None,
        text=text.strip(),
        since=since,
        said_by=said_by,
        certainty=certainty,
    )
