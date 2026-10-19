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
plano. Si falla, ese día se queda sin soñar y lo intenta la vez siguiente. Al cerrar
Sirius se corta, también la petición en curso, para que salir no espere al modelo; ese
día queda igual por soñar (ADR-253).
"""

from __future__ import annotations

import json
import threading
import uuid
from collections.abc import Callable, Iterable, Iterator
from datetime import UTC, date, timedelta

from sirius.application.facts import FactProposals
from sirius.domain.conversation import Message, MessageRole, MessageStatus
from sirius.domain.conversation_summary import OWNER_SPEAKER, said_turns
from sirius.domain.facts import OWNER, Certainty, ProposedFact, is_sirius, person_key
from sirius.domain.plain_text import plain
from sirius.infrastructure.logging import get_logger
from sirius.ports.conversation_repository import ConversationRepository
from sirius.ports.llm import LLMCompleted, LLMError, LLMProvider, LLMRequest, LLMStreamEvent
from sirius.ports.memory_repository import FactRepository
from sirius.ports.memory_suggestion_repository import FactSuggestionRepository
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
        suggestions: FactSuggestionRepository,
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
        #: Lo que está soñando ``dream_pending`` ahora, para que ``cancel`` lo corte.
        self._dreaming: _Dreaming | None = None
        self._lock = threading.Lock()

    def cancel(self) -> None:
        """Corta lo que está soñando ``dream_pending``: la petición en curso, y desde ahí
        no sale ninguna más hasta que acabe. Es para cerrar Sirius sin esperar al modelo
        (ADR-253). El día a medias queda por soñar, porque su resumen se guarda lo último."""
        with self._lock:
            dreaming = self._dreaming
        if dreaming is not None:
            dreaming.cut()

    def dream(self, day: date) -> list[ProposedFact]:
        """Sueña ``day``. Devuelve los hechos que deja propuestos."""
        return self._dream(day, _Dreaming())

    def _dream(self, day: date, dreaming: _Dreaming) -> list[ProposedFact]:
        said = self._said_by_owner(day)
        if not said:
            return []
        local = self._local_model()
        if local is None:
            _logger.info("Sin modelo de este ordenador: hoy no sueña")
            return []
        provider = _AskingThrough(local, dreaming)
        text = "\n".join(f"{OWNER_SPEAKER}: {line}" for line in said)
        try:
            summary = self._summarizer.summarize(text, provider).strip()
        except Exception as exc:  # soñar nunca puede romper nada: se intenta otro día
            if dreaming.is_cut:
                return _cut_short()
            _logger.warning("El sueño no pudo resumir el día (%s)", type(exc).__name__)
            summary = ""
        try:
            proposed = list(self._extractor.extract(text, provider))
        except Exception as exc:  # sin hechos propuestos, el día queda por soñar
            if dreaming.is_cut:
                return _cut_short()
            _logger.warning("El sueño no pudo proponer hechos (%s)", type(exc).__name__)
            return []
        # Una vez cada hecho, aunque el modelo lo repita en la misma respuesta.
        new: list[ProposedFact] = []
        seen: set[tuple[str, str]] = set()
        for fact in proposed:
            key = _fact_key(fact.person, fact.text)
            if fact.text.strip() and key not in seen and not self._already_known(fact):
                seen.add(key)
                new.append(fact)
        for fact in new:
            try:
                self._proposals.propose(fact, by_sirius=True, dreamed_day=day)
            except ValueError as exc:  # p. ej., un hecho con «quién lo dijo» Sirius
                _logger.warning("El sueño propuso un hecho que no vale (%s)", exc)
        # El resumen es lo que marca el día como soñado: se guarda el último, cuando
        # ya está propuesto lo que tocaba. Si algo falla antes, el día queda por soñar
        # y lo ya propuesto no se repite la vez siguiente (ronda 1 de Codex).
        if summary:
            self._days.save_day(day, summary)
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
        dreaming = _Dreaming()
        with self._lock:
            self._dreaming = dreaming
        try:
            done = 0
            for day in days:
                if should_stop() or dreaming.is_cut:
                    break
                self._dream(day, dreaming)
                done += 1
            return done
        finally:
            with self._lock:
                self._dreaming = None

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
        """Si ya está apuntado como hecho vigente, propuesto o contestado.

        Todo lo que él contestó cuenta, que sí o que no: volver a soñar un día que
        quedó a medias no puede proponerle otra vez lo que ya contestó, aunque lo que
        confirmó haya cambiado después (rondas 2 y 3 de Codex).
        """
        key = _fact_key(fact.person, fact.text)
        for memory in self._facts.list_current_facts(fact.person):
            if _fact_key(fact.person, memory.current_revision.content or "") == key:
                return True
        answered = [
            *self._suggestions.list_pending_suggestions(),
            *self._suggestions.list_answered_suggestions(),
        ]
        return any(
            _fact_key(suggestion.person or "", suggestion.content) == key for suggestion in answered
        )


class _Dreaming:
    """Las peticiones de un sueño mientras duran, para poder cortarlas: cortado, corta la
    que esté en curso y ya no deja salir ninguna más (ADR-253)."""

    def __init__(self) -> None:
        self._asking: dict[str, LLMProvider] = {}
        self._cut = False
        self._lock = threading.Lock()

    @property
    def is_cut(self) -> bool:
        with self._lock:
            return self._cut

    def cut(self) -> None:
        with self._lock:
            self._cut = True
            asking = list(self._asking.items())
        for operation_id, provider in asking:
            provider.cancel(operation_id)

    def ask(self, provider: LLMProvider, request: LLMRequest) -> Iterator[LLMStreamEvent]:
        """La respuesta de ``provider`` a ``request``, apuntada mientras dura. Cortado el
        sueño, no pregunta: sin respuesta, quien la esperaba falla y el día queda por soñar."""
        with self._lock:
            if self._cut:
                return
            self._asking[request.operation_id] = provider
        try:
            yield from provider.stream_response(request)
        finally:
            with self._lock:
                del self._asking[request.operation_id]


class _AskingThrough:
    """``provider``, con cada petición apuntada en ``dreaming`` para poder cortarla."""

    def __init__(self, provider: LLMProvider, dreaming: _Dreaming) -> None:
        self._provider = provider
        self._dreaming = dreaming

    def health_check(self) -> bool:
        return self._provider.health_check()

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        return self._dreaming.ask(self._provider, request)

    def cancel(self, operation_id: str) -> None:
        self._provider.cancel(operation_id)


def _cut_short() -> list[ProposedFact]:
    _logger.info("El sueño se cortó: ese día queda por soñar")
    return []


def _fact_key(person: str, text: str) -> tuple[str, str]:
    """Cómo se reconoce un hecho ya visto: de quién es y qué dice, sin tildes ni mayúsculas."""
    return person_key(person), plain(text).strip()


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
            stop=said_turns(text),
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
