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

M14 (SIRIUS-ARQ-0.2 §11.2/§11.5, incidencia #486) adds two more pure
functions, wired only in ``RankRelevantKnowledgeUseCase._rank_via_staged_engine``'s
category amplification behind the same gate: ``category_index_matches_query``
(multi-activation, in parallel to ``category_matches_query`` above, which
keeps its single-activation rule for the closed-gate state) and
``candidate_in_declared_scope`` (the scope restriction over that
amplification). Neither one is used by ``rank_relevant_knowledge`` itself.

M15 (SIRIUS-ARQ-0.2 §11.2/§11.5, incidencia #490) adds three more pure
functions, wired only in ``ContextBuilder._apply_relevance_filter`` behind
the same gate: ``candidate_currently_valid`` (G8's temporal-applicability
half), ``truncate_to_hard_limit`` (G12's hard-limit half) and
``rescue_max_criticality_candidates`` (RF-25/RF-26, replacing M10's
candado-union as the integrity mechanism for max-criticality candidates).
None of the three is used by ``rank_relevant_knowledge`` itself.

M13 (SIRIUS-ARQ-0.2 §11.5, incidencia #489) factors ``category_index_activated``
out of ``category_index_matches_query``: the same activation boolean, without
a candidate's ``category``, so the amplification's caller can decide whether
querying persistence for the category-filtered subset is worth it at all
*before* asking, instead of loading the whole corpus to find out candidate by
candidate.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sirius.domain.decision import Decision, DecisionStatus
from sirius.domain.memory import Memory, MemoryStatus

__all__ = [
    "KnowledgeKind",
    "RankedKnowledge",
    "candidate_currently_valid",
    "candidate_in_declared_scope",
    "category_index_activated",
    "category_index_matches_query",
    "category_matches_query",
    "rank_relevant_knowledge",
    "rescue_max_criticality_candidates",
    "subject_matches_query",
    "truncate_to_hard_limit",
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


def category_index_activated(query_text: str, vocabulary: frozenset[str]) -> bool:
    """M13 (SIRIUS-ARQ-0.2 §11.5, incidencia #489): the same activation
    condition ``category_index_matches_query`` checks, factored out of the
    per-candidate check below so a caller that needs to decide *before*
    querying persistence (whether it is worth asking the repository for the
    category-filtered subset at all) does not have to duplicate the
    normalization rule and risk it diverging (ADR-008's own precedent for
    this kind of factoring: ``activated_category_term`` did the same for
    ``category_matches_query`` in the pre-M14 attempt at this optimization).

    A blank query, or one that activates no vocabulary term at all, is not
    activated — exactly like ``category_index_matches_query`` for any
    candidate.
    """
    normalized_query = query_text.strip().casefold()
    if not normalized_query:
        return False
    return any(term.casefold() in normalized_query for term in vocabulary)


def category_index_matches_query(
    category: str | None, query_text: str, vocabulary: frozenset[str]
) -> bool:
    """M14 (SIRIUS-ARQ-0.2 §11.2/§11.5, incidencia #486): the searchable
    category index's multi-activation, wired behind ``category_matching_enabled``
    in parallel to ``category_matches_query`` above (which keeps its single-
    activation rule unchanged for the closed-gate state). Replica of
    ``activa_categoria_buscable``
    (``tests/acceptance/staged_engine_category_and_relevance.py:317-336``,
    ADR-113): the index stores the whole vocabulary as the same content for
    every non-ordinary identity, so **any** vocabulary term present in the
    query activates the category for every candidate that already has one —
    a query naming two or more vocabulary terms at once still activates it,
    unlike ``category_matches_query``'s single-activation rule.

    ``category`` is ``None`` for a candidate with no classification yet
    (D7 point 2) — never a match, exactly like ``category_matches_query``. A
    blank query, or one that activates no vocabulary term at all, matches
    nothing either. Delegates the activation rule itself to
    ``category_index_activated``.
    """
    if category is None:
        return False
    return category_index_activated(query_text, vocabulary)


def candidate_in_declared_scope(
    candidate_project_id: int | None, *, active_project_id: int | None
) -> bool:
    """M14 (SIRIUS-ARQ-0.2 §11.2/§11.5, incidencia #486): the scope
    restriction over ``category_index_matches_query``'s activation. Replica
    of ``_en_ambito_declarado``
    (``tests/acceptance/staged_engine_category_and_relevance.py:339-356``,
    ADR-114): without an active project, the request's own scope is global
    and admits every candidate; with one, a candidate is only admitted if
    its own project matches the active one, or if the candidate itself is
    globally scoped (``candidate_project_id`` is ``None`` — only possible
    for a ``Memory``, never a ``Decision``, whose ``project_id`` is always
    set).
    """
    if active_project_id is None:
        return True
    return candidate_project_id is None or candidate_project_id == active_project_id


def candidate_currently_valid(
    valid_from: datetime | None, valid_to: datetime | None, *, target_time: datetime
) -> bool:
    """M15 (SIRIUS-ARQ-0.2 §11.2/§11.5, incidencia #490): the temporal-
    applicability half of ``G8`` — ``valid_from``/``valid_to`` against the
    request's target time, without the corte-de-registro half, which no
    real request declares either. Replica of ``_g8``
    (``src/sirius/domain/staged_engine_gates.py:194-210``) and its harness
    twin ``vigente_en_tiempo_objetivo``
    (``tests/acceptance/staged_engine_category_and_relevance.py:516-541``,
    ADR-115).

    ``Memory``/``Decision`` declare no ``valid_from``/``valid_to`` axis yet
    (SIN_EJES — ``staged_engine_gates.py``'s own module docstring already
    documents this degradation for every gate that needs an axis Sirius
    does not persist today): every real caller passes ``None, None`` here,
    so this degrades to always ``True`` — the same "falla abierta, no
    descarta" contract the gate already has for ``SIN_EJES``, not a new
    policy invented for this incidence.
    """
    if valid_from is not None and valid_from > target_time:
        return False
    return not (valid_to is not None and valid_to <= target_time)


def truncate_to_hard_limit(
    candidates: Sequence[RankedKnowledge],
    *,
    hard_limit: int,
    max_criticality_category: str | None,
) -> tuple[RankedKnowledge, ...]:
    """M15 (SIRIUS-ARQ-0.2 §11.2/§11.5, incidencia #490): the hard-limit
    half of ``G12`` — keep only the first ``hard_limit`` candidates,
    prioritising the max-criticality category (the only criticidad axis a
    real ``Memory``/``Decision`` carries; D7's vocabulary has no
    ``IMPORTANTE`` tier). Replica of ``aplicar_g12``
    (``src/sirius/domain/staged_engine_gates.py:304-332``) and its harness
    twin ``truncar_por_limite_duro``
    (``tests/acceptance/staged_engine_category_and_relevance.py:544-574``,
    ADR-115).

    Returns the survivors in their ORIGINAL relative order (never the
    criticidad-first order used only to decide who survives): who is kept
    is this function's only concern, never how the result is displayed —
    the same contract ``_apply_relevance_filter`` already relies on for the
    filter/candado union.
    """

    def is_max_criticality(candidate: RankedKnowledge) -> bool:
        return (
            max_criticality_category is not None
            and candidate.item.category == max_criticality_category
        )

    prioritised = sorted(candidates, key=lambda candidate: not is_max_criticality(candidate))
    survivors = {id(candidate) for candidate in prioritised[:hard_limit]}
    return tuple(candidate for candidate in candidates if id(candidate) in survivors)


def rescue_max_criticality_candidates(
    candidates: Sequence[RankedKnowledge],
    kept_by_filter: Sequence[RankedKnowledge],
    *,
    max_criticality_category: str | None,
) -> tuple[RankedKnowledge, ...]:
    """M15 (RF-25/RF-26, SIRIUS-ARQ-0.2 §11.2/§11.5, incidencia #490): the
    ORIGINAL critics rule the laboratory measured
    (``experiments/adr002/modelo_local/filtro.py:filtrar``, rama
    ``evidence/adr001-spikes``), replacing M10's candado-union as the
    integrity mechanism for max-criticality candidates when the gate is
    open. Replica of ``aplicar_regla_de_criticas_original``
    (``tests/acceptance/staged_engine_category_and_relevance.py:472-513``,
    ADR-112/113).

    RF-25: if ``kept_by_filter`` conserved at least one of ``candidates``,
    a max-criticality candidate the filter discarded is rescued back — the
    filter can never be allowed to drop a critical identity while it did
    conserve something else for the same query. RF-26: if the filter
    conserved none of ``candidates`` at all, that verdict is respected
    whole — no rescue, not even for a max-criticality candidate.

    This never touches a candidate with no category yet — that one stays
    unconditionally protected regardless of the filter's verdict, exactly
    as before this incidence (see ``ContextBuilder._apply_relevance_filter``,
    which unions this function's result with that unconditional set rather
    than folding it in here).
    """
    if not kept_by_filter:
        return ()
    kept_ids = {id(candidate) for candidate in kept_by_filter}
    return tuple(
        candidate
        for candidate in candidates
        if id(candidate) not in kept_ids
        and max_criticality_category is not None
        and candidate.item.category == max_criticality_category
    )


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
