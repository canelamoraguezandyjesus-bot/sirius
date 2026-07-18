"""Deterministic context assembly for LLM requests.

Section order is fixed and matches the approved architecture (SIRIUS-ARQ-0.1,
S6.1 "Orden del contexto") for the sections V5 implements: identity, active
project, current memories, recent conversation history, current user message.
The architecture also lists "reglas de comportamiento" and "decisiones
vigentes relacionadas" as separate sections; the former lives inside the
identity's ``personality_instructions``, and the latter has no entity yet
(V4 only modelled a generic Memory, not the "decisión" specialisation from
DR-009) — both are intentional scope reductions, not a contradiction.

``project`` is optional (SIRIUS-ARQ-0.1 S3, ``LLMRequest.project_context:
str | None``): between completing a project (RF-018) and creating the next
one, Sirius legitimately has zero configured ``ACTIVE`` projects. That is
not a bootstrap failure — only a missing identity or main conversation is.
"""

from __future__ import annotations

from dataclasses import dataclass

from sirius.domain.conversation import Message, MessageStatus
from sirius.domain.identity import Identity
from sirius.domain.memory import Memory
from sirius.domain.project import Project, is_configured
from sirius.ports.conversation_repository import ConversationRepository
from sirius.ports.identity_repository import IdentityRepository
from sirius.ports.memory_repository import MemoryRepository
from sirius.ports.project_repository import ProjectRepository

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
    never the placeholder itself.
    """

    identity: Identity
    project: Project | None
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
    """

    def __init__(
        self,
        identity_repository: IdentityRepository,
        project_repository: ProjectRepository,
        memory_repository: MemoryRepository,
        conversation_repository: ConversationRepository,
        recent_messages_limit: int = _DEFAULT_RECENT_MESSAGES_LIMIT,
    ) -> None:
        self._identity_repository = identity_repository
        self._project_repository = project_repository
        self._memory_repository = memory_repository
        self._conversation_repository = conversation_repository
        self._recent_messages_limit = recent_messages_limit

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

        memories = tuple(self._memory_repository.list_current_memories())
        all_messages = self._conversation_repository.list_messages(conversation.id)
        # SIRIUS-ARQ-0.1 S5.1/S5.2: "Mensajes parciales conservan su
        # contenido y quedan excluidos del contexto normal." A CANCELLED or
        # FAILED SIRIUS message stays in the conversation history (for
        # traceability) but must never feed a future context.
        completed_messages = [m for m in all_messages if m.status is MessageStatus.COMPLETED]
        recent_messages = tuple(completed_messages[-self._recent_messages_limit :])

        return Context(
            identity=identity,
            project=project,
            memories=memories,
            recent_messages=recent_messages,
            current_user_message=current_user_message,
        )
