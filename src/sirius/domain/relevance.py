"""Deterministic, checkable relevance ordering for read-only knowledge
retrieval (B6b; SIRIUS-ARQ-0.1 S7.5; D-11).

S7.5 "Búsqueda y relevancia" is explicit that the retrieval score "no será
una fórmula opaca permanente: se implementará como ordenación simple y
comprobable", combining "filtros estructurados y FTS5" and never embeddings.
Its own priority list, top to bottom, is: proyecto activo, estado
APROBADA/VIGENTE, tipo DECISIÓN cuando el asunto coincide, coincidencia
FTS5, recencia — with two negative terms it says are subtracted:
"elemento general no relacionado" and "estado histórico". The B6b issue
fixes the positive terms as an explicit sort key over three booleans and one
integer (never a numeric score), in this descending order: a
matching-subject APPROVED decision first, then active-project membership,
then an FTS5 hit, then recency, with a final, stable tie-break by id. The
two negative terms are never subtracted from a score here — the issue's own
wording is "se excluyen por filtro... no se restan": ``rank_relevant_knowledge``
drops them *before* ranking instead. "Estado histórico" is a memory that is
not CURRENT or a decision that is not APPROVED; "elemento general no
relacionado" is a candidate with neither a matching subject nor an FTS5 hit.
Both are re-checked by this module itself, never merely assumed from the
caller — mirrors ``sirius.domain.precedence``'s own "re-checks status
itself" guarantee, so this stays correct even if called with an unfiltered
candidate list.

Like ``sirius.domain.precedence``, this module has no semantic understanding
of content: "asunto coincide" and "coincidencia FTS5" are both explicit,
caller-supplied booleans computed by the application layer (plain-string
subject containment, and a real FTS5 ``MATCH`` against ``knowledge_fts``
respectively) — nothing here inspects ``content`` itself or scores anything
by similarity.

M9 (SIRIUS-ARQ-0.2 §6.2, D7) adds a fourth structural signal,
``category_match``, inserted after the FTS5 hit and before recency in
``_sort_key`` — weaker than an explicit query match, because a candidate's
category comes from a save-time classification, not from the query itself.
``category_matches_query`` computes it deterministically, without a model. It
also widens "elemento general no relacionado" (``is_related``): a candidate
with neither a matching subject nor an FTS5 hit can still be related through
a category match alone, so it stays found by that signal even when the other
two are absent.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from sirius.domain.decision import Decision, DecisionStatus
from sirius.domain.memory import Memory, MemoryStatus

__all__ = [
    "KnowledgeKind",
    "RankedKnowledge",
    "category_matches_query",
    "rank_relevant_knowledge",
    "subject_matches_query",
]


class KnowledgeKind(StrEnum):
    """Which entity a ``RankedKnowledge`` wraps. Mirrors the ``kind`` column
    ``knowledge_fts`` already stores (B6a) — the same "conocimiento"
    grouping ``GetKnowledgeOverviewUseCase`` (B4f) uses."""

    MEMORY = "memory"
    DECISION = "decision"


@dataclass(frozen=True, slots=True)
class RankedKnowledge:
    """One candidate plus the explicit, inspectable criteria S7.5 ranks on.

    ``subject_matches_query`` (S7.5's "tipo DECISIÓN cuando el asunto
    coincide") only ever applies to a decision — a memory candidate must
    always be constructed with it ``False``. That is enforced below rather
    than merely documented, since it is the one criterion S7.5 ties to a
    specific ``kind``.
    """

    kind: KnowledgeKind
    item: Memory | Decision
    subject_matches_query: bool
    project_matches_active: bool
    fts_match: bool
    category_match: bool = False
    """The fourth structural signal (M9, SIRIUS-ARQ-0.2 §6.2): whether the
    candidate's already-persisted ``category`` (D7, §6.1) equals the single
    category ``category_matches_query`` deterministically activates from the
    query text. ``False`` by default so every existing caller that never
    passes it keeps building a valid ``RankedKnowledge`` — the same "no
    signal, never a penalty" default the other three booleans imply through
    an unrelated/non-current candidate being filtered instead."""

    def __post_init__(self) -> None:
        if self.kind is KnowledgeKind.MEMORY and self.subject_matches_query:
            msg = (
                "subject_matches_query only ever applies to a decision "
                "(S7.5: 'tipo DECISIÓN cuando el asunto coincide')."
            )
            raise ValueError(msg)

    @property
    def item_id(self) -> int:
        return self.item.id

    @property
    def is_current(self) -> bool:
        """Whether this candidate is actually vigente. A ``False`` here is
        S7.5's "estado histórico" negative term — filtered out, never
        subtracted."""
        if self.kind is KnowledgeKind.MEMORY:
            assert isinstance(self.item, Memory)
            return self.item.status is MemoryStatus.CURRENT
        assert isinstance(self.item, Decision)
        return self.item.status is DecisionStatus.APPROVED

    @property
    def is_related(self) -> bool:
        """Whether this candidate is related to the query at all. A
        ``False`` here is S7.5's other negative term, "elemento general no
        relacionado" — a matching subject, an actual FTS5 hit, or (M9,
        SIRIUS-ARQ-0.2 §6.2) a category match, never project membership or
        recency alone. ``category_match`` can only ever add a candidate here,
        never remove one the other two already keep: it stays ``False`` for
        every real candidate while D7 point 6's activation gate is closed."""
        return self.subject_matches_query or self.fts_match or self.category_match


def subject_matches_query(subject: str, query_text: str) -> bool:
    """Whether a decision's ``subject`` (asunto) "coincide" with a query
    text (S7.5): plain, case-insensitive substring containment in either
    direction — never a similarity score or embeddings. Blank on either
    side never matches."""
    normalized_subject = subject.strip().casefold()
    normalized_query = query_text.strip().casefold()
    if not normalized_subject or not normalized_query:
        return False
    return normalized_subject in normalized_query or normalized_query in normalized_subject


def category_matches_query(
    category: str | None, query_text: str, vocabulary: frozenset[str]
) -> bool:
    """Whether a candidate's already-persisted ``category`` (D7, §6.1)
    equals the single category ``query_text`` deterministically activates
    against the closed vocabulary (M9, SIRIUS-ARQ-0.2 §6.2) — plain,
    case-insensitive substring containment against ``vocabulary``, never a
    call to ``CategoryClassifierPort`` or Ollama: classifying a candidate at
    save time (§6.1) and comparing two already-known values at query time
    (here) are deliberately two different operations, and only the first
    ever uses a model.

    ``category`` is ``None`` when the candidate has no classification yet
    (D7 point 2's open failure) — never a match, the candidate keeps being
    found through the other three signals instead. A blank query, or one
    that activates no vocabulary term at all, matches nothing — it does not
    penalize, exactly like ``subject_matches_query`` when the query names no
    subject. A query that activates more than one vocabulary term at once is
    ambiguous and also matches nothing: this function only ever affirms a
    single, unambiguous activation, never guesses among several.
    """
    if category is None:
        return False
    normalized_query = query_text.strip().casefold()
    if not normalized_query:
        return False
    activated = {term.casefold() for term in vocabulary if term.casefold() in normalized_query}
    if len(activated) != 1:
        return False
    return category.casefold() in activated


def _synthetic_id(candidate: RankedKnowledge) -> int:
    """The same synthetic id space ``knowledge_fts`` itself uses (B6a):
    ``memory_id * 2`` (even) for memories, ``decision_id * 2 + 1`` (odd) for
    decisions — so a memory and a decision can never tie on this final,
    stable tie-break, reusing an id space this codebase already established
    instead of inventing a new one."""
    if candidate.kind is KnowledgeKind.MEMORY:
        return candidate.item_id * 2
    return candidate.item_id * 2 + 1


def _sort_key(candidate: RankedKnowledge) -> tuple[bool, bool, bool, bool, float, int]:
    return (
        not candidate.subject_matches_query,
        not candidate.project_matches_active,
        not candidate.fts_match,
        not candidate.category_match,
        -candidate.item.updated_at.timestamp(),
        _synthetic_id(candidate),
    )


def rank_relevant_knowledge(candidates: Sequence[RankedKnowledge]) -> tuple[RankedKnowledge, ...]:
    """Filter out non-vigente and unrelated candidates, then sort the rest by
    S7.5's explicit criteria tuple (never a numeric score): matching-subject
    APPROVED decision, active-project membership, FTS5 hit, recency —
    descending in that order — with a final, stable tie-break by the
    synthetic id ``knowledge_fts`` itself uses to keep memories and
    decisions apart (B6a).
    """
    related_and_current = [
        candidate for candidate in candidates if candidate.is_current and candidate.is_related
    ]
    return tuple(sorted(related_and_current, key=_sort_key))
