"""Deterministic context assembly for LLM requests.

Section order is fixed and matches the approved architecture (SIRIUS-ARQ-0.1,
S6.1 "Orden del contexto"): identity (with "reglas de comportamiento" inside
``personality_instructions``), active project, current decisions vigentes
relacionadas (B6d), pertinent memories (B6b/B6c), recent conversation
history, current user message.

``project`` is optional (SIRIUS-ARQ-0.1 S3, ``LLMRequest.project_context:
str | None``): between completing a project (RF-018) and creating the next
one, Sirius legitimately has zero configured ``ACTIVE`` projects. That is
not a bootstrap failure — only a missing identity or main conversation is.

B6d wires together, without reimplementing any of them: B6b's relevance
ordering (``RankRelevantKnowledgeUseCase``/``sirius.domain.relevance``), B6c's
budget/trim (``apply_context_budget``/``TokenCounter``), and B4e's precedence
filter (``find_prevailing_decision``). ``current_user_message`` is the B6b
relevance query text; the budget's ``protected_tokens`` covers exactly the
sections that are never trimmed here — identity/rules, the active project (if
any), and the current user message itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from sirius.application.context_budget import (
    DEFAULT_MAX_KNOWLEDGE_ITEMS,
    DEFAULT_TOKEN_BUDGET,
    apply_context_budget,
)
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.domain.conversation import Message, MessageStatus
from sirius.domain.decision import Decision
from sirius.domain.event import Event
from sirius.domain.identity import Identity
from sirius.domain.memory import Memory
from sirius.domain.precedence import find_prevailing_decision
from sirius.domain.project import Project, blockers_to_text, is_configured
from sirius.domain.relevance import KnowledgeKind, RankedKnowledge
from sirius.ports.conversation_repository import ConversationRepository
from sirius.ports.decision_repository import DecisionRepository
from sirius.ports.event_repository import EventRepository
from sirius.ports.identity_repository import IdentityRepository
from sirius.ports.memory_repository import MemoryRepository
from sirius.ports.project_repository import ProjectRepository
from sirius.ports.relevance_filter import RelevanceFilterPort
from sirius.ports.token_counter import TokenCounter

_DEFAULT_RECENT_MESSAGES_LIMIT = 20


class ContextAssemblyError(RuntimeError):
    """Raised when a piece of data ContextBuilder requires does not exist yet.

    ContextBuilder never creates data itself; seeding the main conversation
    and the current identity is the exclusive responsibility of
    ``initialize_persistence()``. This error means that bootstrap has not
    run (or has not completed) against this storage. The active project is
    deliberately not part of this list: its absence (no project configured
    yet, or the previous one was just completed) is a normal, expected
    state, not a bootstrap failure — see ``Context.project``.
    """


@dataclass(frozen=True, slots=True)
class Context:
    """Deterministic, ordered context assembled before calling any LLM provider.

    Field order mirrors the section order given above; callers must not
    reorder or flatten these into a single opaque string before this point.
    ``project`` is ``None`` whenever there is no configured ``ACTIVE``
    project — absent entirely, still the bootstrap placeholder, or every
    existing project is ``COMPLETED`` — never a ``COMPLETED`` project and
    never the placeholder itself. ``decisions`` holds only APPROVED
    (vigente) decisions, ranked by B6b and trimmed by B6c same as
    ``memories``; an empty tuple is the safe, expected state when none are
    relevant or none exist.
    """

    identity: Identity
    project: Project | None
    decisions: tuple[Decision, ...]
    memories: tuple[Memory, ...]
    recent_messages: tuple[Message, ...]
    current_user_message: str


class ContextBuilder:
    """Assembles ``Context`` from ports only; never touches SQLite/SQLAlchemy.

    Strictly read-only: it queries the pure ``get_*`` lookups exclusively and
    never the ``get_or_create_*`` ones, so building a context can never create
    or modify a row. If the main conversation or the current identity does
    not exist yet, it raises ``ContextAssemblyError`` instead of creating it
    — that seeding is ``initialize_persistence()``'s job alone. The active
    project is resolved, never required: see ``Context.project``.

    B4e (DR-011) minimal connection: a current memory whose explicit
    ``subject_key``/``project_id`` matches a single, unambiguous APPROVED
    decision is excluded from ``Context.memories`` — that decision already
    prevails over it, so presenting both as equally current knowledge would
    contradict the precedence Sirius already established through an explicit
    approval. This is the only conflict-related filtering ``ContextBuilder``
    performs: a memory with no explicit subject, or one whose subject has no
    unambiguous prevailing decision (including a genuine, unresolved
    conflict between current memories), is never touched here — resolving
    that stays out of scope until B4f's interface exists.

    B6d: relevance (B6b) and budget (B6c) decide which memories, which
    decisions, and which recent messages actually make it into ``Context`` —
    never "every current memory" as before. ``recent_messages_limit`` bounds
    how many of the most recent completed messages are even considered as
    budget candidates (unchanged pre-filter); the budget then decides the
    final subset.
    """

    def __init__(
        self,
        identity_repository: IdentityRepository,
        project_repository: ProjectRepository,
        memory_repository: MemoryRepository,
        conversation_repository: ConversationRepository,
        decision_repository: DecisionRepository,
        rank_relevant_knowledge_use_case: RankRelevantKnowledgeUseCase,
        event_repository: EventRepository,
        token_counter: TokenCounter,
        recent_messages_limit: int = _DEFAULT_RECENT_MESSAGES_LIMIT,
        token_budget: int = DEFAULT_TOKEN_BUDGET,
        max_knowledge_items: int = DEFAULT_MAX_KNOWLEDGE_ITEMS,
        relevance_filter_port: RelevanceFilterPort | None = None,
        max_criticality_category: str | None = None,
    ) -> None:
        self._identity_repository = identity_repository
        self._project_repository = project_repository
        self._memory_repository = memory_repository
        self._conversation_repository = conversation_repository
        self._decision_repository = decision_repository
        self._rank_relevant_knowledge_use_case = rank_relevant_knowledge_use_case
        self._event_repository = event_repository
        self._token_counter = token_counter
        self._recent_messages_limit = recent_messages_limit
        self._token_budget = token_budget
        self._max_knowledge_items = max_knowledge_items
        # M10 (SIRIUS-ARQ-0.2 §6.3): both default to the closed D7 point 6
        # gate — no relevance filter runs at all, so every existing caller
        # that never passes them keeps building the exact same Context it
        # does today. Wiring a real adapter and the real max-criticality
        # category from settings is M11's job (composition_root), not this
        # constructor's.
        self._relevance_filter_port = relevance_filter_port
        self._max_criticality_category = max_criticality_category

    def build(self, current_user_message: str) -> Context:
        """Assemble a Context; deterministic for the same underlying data.

        Raises ``ContextAssemblyError`` if bootstrap has not seeded the
        identity or the main conversation yet. Never raises for the active
        project's absence: ``Context.project`` is simply ``None`` in that
        case (no configured ``ACTIVE`` project — absent, still the
        placeholder, or every project is ``COMPLETED``).
        """
        identity = self._identity_repository.get_current_identity()
        if identity is None:
            msg = "No current identity found; has initialize_persistence() run?"
            raise ContextAssemblyError(msg)

        active_project = self._project_repository.get_active_project()
        project = (
            active_project if active_project is not None and is_configured(active_project) else None
        )

        conversation = self._conversation_repository.get_main_conversation()
        if conversation is None:
            msg = "No main conversation found; has initialize_persistence() run?"
            raise ContextAssemblyError(msg)

        ranked_knowledge = self._rank_related_knowledge(current_user_message)

        all_messages = self._conversation_repository.list_messages(conversation.id)
        # SIRIUS-ARQ-0.1 S5.1/S5.2: "Mensajes parciales conservan su
        # contenido y quedan excluidos del contexto normal." A CANCELLED or
        # FAILED SIRIUS message stays in the conversation history (for
        # traceability) but must never feed a future context.
        completed_messages = [m for m in all_messages if m.status is MessageStatus.COMPLETED]
        recent_candidates = tuple(completed_messages[-self._recent_messages_limit :])

        protected_tokens = self._protected_tokens(identity, project, current_user_message)
        source_events = self._resolve_source_events(ranked_knowledge)

        selection = apply_context_budget(
            protected_tokens=protected_tokens,
            ranked_knowledge=ranked_knowledge,
            recent_messages=recent_candidates,
            token_counter=self._token_counter,
            source_events=source_events,
            token_budget=self._token_budget,
            max_knowledge_items=self._max_knowledge_items,
        )

        memories = tuple(
            candidate.item
            for candidate in selection.knowledge
            if isinstance(candidate.item, Memory)
        )
        decisions = tuple(
            candidate.item
            for candidate in selection.knowledge
            if isinstance(candidate.item, Decision)
        )

        return Context(
            identity=identity,
            project=project,
            decisions=decisions,
            memories=memories,
            recent_messages=selection.recent_messages,
            current_user_message=current_user_message,
        )

    def _rank_related_knowledge(self, current_user_message: str) -> tuple[RankedKnowledge, ...]:
        """B6b-ranked vigente knowledge related to ``current_user_message``,
        minus any memory B4e's precedence filter excludes (see the class
        docstring) — decisions are never excluded by that filter, only
        memories — and then M10's relevance filter (§6.3), a second filter
        after precedence and before ``apply_context_budget``, guarded by its
        own candado."""
        ranked_knowledge = self._rank_relevant_knowledge_use_case.rank(current_user_message)
        current_decisions = self._decision_repository.list_current_decisions()
        after_precedence = tuple(
            candidate
            for candidate in ranked_knowledge
            if not self._excluded_by_precedence(candidate, current_decisions)
        )
        if self._relevance_filter_port is None:
            return after_precedence
        return self._apply_relevance_filter(current_user_message, after_precedence)

    def _apply_relevance_filter(
        self, current_user_message: str, candidates: tuple[RankedKnowledge, ...]
    ) -> tuple[RankedKnowledge, ...]:
        """The candado (§6.3): a single call to ``RelevanceFilterPort``,
        never a second one, recombined as the union of three sets — what the
        filter kept, every candidate of the vocabulary's max-criticality
        category, and every candidate with no category yet — preserving the
        order §6.2 already fixed on ``candidates``. A candidate the filter
        would have discarded still survives here if either of the other two
        sets protects it; the filter alone never has the final word."""
        assert self._relevance_filter_port is not None
        filtered = self._relevance_filter_port.filter_candidates(current_user_message, candidates)
        kept_positions = {id(candidate) for candidate in filtered}
        kept_positions.update(
            id(candidate)
            for candidate in candidates
            if candidate.item.category is None
            or candidate.item.category == self._max_criticality_category
        )
        return tuple(candidate for candidate in candidates if id(candidate) in kept_positions)

    @staticmethod
    def _excluded_by_precedence(
        candidate: RankedKnowledge, decisions: tuple[Decision, ...] | list[Decision]
    ) -> bool:
        if candidate.kind is not KnowledgeKind.MEMORY:
            return False
        memory = candidate.item
        assert isinstance(memory, Memory)
        if memory.subject_key is None or memory.project_id is None:
            return False
        return (
            find_prevailing_decision(memory.subject_key, memory.project_id, decisions) is not None
        )

    def _resolve_source_events(
        self, ranked_knowledge: tuple[RankedKnowledge, ...]
    ) -> tuple[Event, ...]:
        """Every recorded source event of a ranked candidate's current
        revision, resolved via ``EventRepository.get_source`` — never a list
        query, since B4a's ``EventRepository`` only offers single-id lookup.
        Feeds B6c's message-survival rule; a candidate with no
        ``source_event_id``, or one whose event no longer resolves, is
        simply omitted rather than raising."""
        source_event_ids = {
            candidate.item.current_revision.source_event_id
            for candidate in ranked_knowledge
            if candidate.item.current_revision.source_event_id is not None
        }
        events = (self._event_repository.get_source(event_id) for event_id in source_event_ids)
        return tuple(event for event in events if event is not None)

    def _protected_tokens(
        self, identity: Identity, project: Project | None, current_user_message: str
    ) -> int:
        """The token cost of the sections B6c must never trim: identity
        (with rules/permissions inside ``personality_instructions``), the
        active project's rendered fields if any, and the current user
        message itself."""
        version = identity.current_version
        texts = [
            "\n".join([version.name, version.description, version.personality_instructions]),
            current_user_message,
        ]
        if project is not None:
            revision = project.current_revision
            assert revision is not None  # a configured project always has one
            texts.append(
                "\n".join(
                    [
                        project.name,
                        revision.objective,
                        revision.state_summary,
                        blockers_to_text(revision.blockers),
                        revision.next_step,
                    ]
                )
            )
        return sum(self._token_counter.count_tokens(text) for text in texts)
