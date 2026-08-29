"""Sustitución explícita de decisiones: el defecto funcional y su cierre.

El caso manual que falló era este: existía una decisión aprobada sobre un
asunto, se creaba y **se aprobaba** otra incompatible sobre el mismo asunto, se
ordenaba que la nueva sustituyera a la anterior, y las dos seguían vigentes con
el mismo peso y sin vínculo entre ellas. La causa era que la regla de dominio
solo admitía como sustituta una decisión todavía PROPUESTA, así que la orden se
rechazaba, y la interfaz solo ofrecía candidatas propuestas, así que la
decisión ya aprobada no aparecía siquiera en el selector.

Estas pruebas cablean los adaptadores SQLite reales detrás de los casos de uso
reales, los mismos que invoca la interfaz, y comprueban de punta a punta que la
sustitución es explícita, atómica, persistente y observable, y que una simple
contradicción no sustituye nunca por su cuenta.
"""

import sqlite3
from pathlib import Path

import pytest

from sirius.adapters.llm.fake import FakeLLMProvider
from sirius.adapters.llm.token_counter import CharacterHeuristicTokenCounter
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_decision_repository import (
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_event_repository import build_sqlite_event_repository
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.persistence.sqlite_knowledge_search_repository import (
    build_sqlite_knowledge_search_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_memory_suggestion_repository import (
    build_sqlite_memory_suggestion_repository,
)
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.application.approve_decision import ApproveDecisionUseCase
from sirius.application.context import ContextBuilder
from sirius.application.knowledge_overview import GetKnowledgeOverviewUseCase
from sirius.application.propose_decision import ProposeDecisionUseCase
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.application.supersede_decision import (
    InvalidDecisionSupersessionError,
    SupersedeDecisionUseCase,
)
from sirius.domain.decision import Decision, DecisionStatus
from sirius.domain.event import DECISION_SUPERSEDED_EVENT_TYPE

SUBJECT = "Día de la reunión semanal"


def _supersession_events(database_path: Path) -> int:
    """Cuántos eventos de sustitución hay registrados, leídos de la tabla real."""
    connection = sqlite3.connect(str(database_path))
    try:
        row = connection.execute(
            "SELECT COUNT(*) FROM events WHERE event_type = ?",
            (DECISION_SUPERSEDED_EVENT_TYPE,),
        ).fetchone()
        return int(row[0])
    finally:
        connection.close()


class _Fixture:
    """Los casos de uso reales sobre una base sintética, como en la interfaz."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        upgrade_to_head(database_path)
        project_repository = build_sqlite_project_repository(database_path)
        project_repository.ensure_bootstrap_project()
        self.project_id = project_repository.create_project(
            "Proyecto de prueba",
            "Objetivo de prueba",
            state_summary="En curso",
            blockers=(),
            next_step="Siguiente paso",
        ).id
        build_sqlite_identity_repository(database_path).get_or_create_current_identity()
        build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()

        unit_of_work = build_sqlite_unit_of_work(database_path)
        self.propose = ProposeDecisionUseCase(unit_of_work)
        self.approve = ApproveDecisionUseCase(unit_of_work)
        self.supersede = SupersedeDecisionUseCase(unit_of_work)
        self.decisions = build_sqlite_decision_repository(database_path)
        self.overview = GetKnowledgeOverviewUseCase(
            build_sqlite_memory_repository(database_path),
            self.decisions,
            build_sqlite_memory_suggestion_repository(database_path),
        )

    def approved_decision(self, content: str, *, subject: str = SUBJECT) -> Decision:
        proposal = self.propose.propose(subject, self.project_id, content)
        return self.approve.approve(proposal.id, confirmed=True)

    def proposed_decision(self, content: str, *, subject: str = SUBJECT) -> Decision:
        return self.propose.propose(subject, self.project_id, content)

    def current_ids(self) -> list[int]:
        return [decision.id for decision in self.decisions.list_current_decisions()]

    def build_context_decisions(self) -> tuple[Decision, ...]:
        """Las decisiones que ContextBuilder enviaría al proveedor."""
        memory_repository = build_sqlite_memory_repository(self.database_path)
        project_repository = build_sqlite_project_repository(self.database_path)
        conversation_repository = build_sqlite_conversation_repository(self.database_path)
        ranking = RankRelevantKnowledgeUseCase(
            memory_repository=memory_repository,
            decision_repository=self.decisions,
            project_repository=project_repository,
            knowledge_search_repository=build_sqlite_knowledge_search_repository(
                self.database_path
            ),
        )
        builder = ContextBuilder(
            identity_repository=build_sqlite_identity_repository(self.database_path),
            project_repository=project_repository,
            memory_repository=memory_repository,
            conversation_repository=conversation_repository,
            decision_repository=self.decisions,
            rank_relevant_knowledge_use_case=ranking,
            event_repository=build_sqlite_event_repository(self.database_path),
            token_counter=CharacterHeuristicTokenCounter(),
        )
        return builder.build(current_user_message="¿Cuándo es la reunión?").decisions


@pytest.mark.integration
def test_an_approved_decision_can_explicitly_supersede_another_approved_one(
    tmp_path: Path,
) -> None:
    """El caso manual completo: puntos 1, 2, 3, 4 y 6 del contrato."""
    fixture = _Fixture(tmp_path / "sirius.db")
    previous = fixture.approved_decision("La reunión es los martes")
    replacement = fixture.approved_decision("La reunión es los jueves")

    # Antes de ordenar nada, las dos están vigentes: la contradicción por sí
    # sola no sustituye (punto 10).
    assert sorted(fixture.current_ids()) == sorted([previous.id, replacement.id])

    result = fixture.supersede.supersede(previous.id, replacement.id, confirmed=True)

    # 2. La nueva queda vigente.
    assert result.id == replacement.id
    assert result.status is DecisionStatus.APPROVED
    # 3. La anterior queda SUSTITUIDA.
    assert fixture.decisions.get_decision(previous.id).status is DecisionStatus.SUPERSEDED
    # 4. La anterior deja de aparecer entre las vigentes.
    assert fixture.current_ids() == [replacement.id]
    # 6. Existe vínculo entre anterior y sucesora.
    assert result.supersedes_decision_id == previous.id


@pytest.mark.integration
def test_the_superseded_decision_is_still_queryable_as_history(tmp_path: Path) -> None:
    """Punto 5: sustituida no es borrada."""
    fixture = _Fixture(tmp_path / "sirius.db")
    previous = fixture.approved_decision("La reunión es los martes")
    replacement = fixture.approved_decision("La reunión es los jueves")
    fixture.supersede.supersede(previous.id, replacement.id, confirmed=True)

    historical = fixture.decisions.get_decision(previous.id)

    assert historical.status is DecisionStatus.SUPERSEDED
    assert historical.current_revision.content == "La reunión es los martes"
    assert historical.subject == SUBJECT


@pytest.mark.integration
def test_states_and_link_survive_reopening_the_store(tmp_path: Path) -> None:
    """Punto 7: al reiniciar Sirius, estado y vínculo persisten."""
    database_path = tmp_path / "sirius.db"
    fixture = _Fixture(database_path)
    previous = fixture.approved_decision("La reunión es los martes")
    replacement = fixture.approved_decision("La reunión es los jueves")
    fixture.supersede.supersede(previous.id, replacement.id, confirmed=True)

    # Repositorio nuevo sobre el mismo fichero: equivale a reabrir la aplicación.
    reopened = build_sqlite_decision_repository(database_path)

    assert reopened.get_decision(previous.id).status is DecisionStatus.SUPERSEDED
    assert reopened.get_decision(replacement.id).status is DecisionStatus.APPROVED
    assert reopened.get_decision(replacement.id).supersedes_decision_id == previous.id
    assert [decision.id for decision in reopened.list_current_decisions()] == [replacement.id]


@pytest.mark.integration
def test_the_context_sent_to_the_provider_holds_only_the_new_decision(tmp_path: Path) -> None:
    """Punto 8: el constructor de contexto no envía las dos como equivalentes."""
    fixture = _Fixture(tmp_path / "sirius.db")
    previous = fixture.approved_decision("La reunión es los martes")
    replacement = fixture.approved_decision("La reunión es los jueves")

    # Antes: las dos entran en el contexto con el mismo peso. Esto es lo que el
    # usuario veía y lo que hacía que Sirius se contradijera.
    before = fixture.build_context_decisions()
    assert sorted(decision.id for decision in before) == sorted([previous.id, replacement.id])

    fixture.supersede.supersede(previous.id, replacement.id, confirmed=True)

    after = fixture.build_context_decisions()
    assert [decision.id for decision in after] == [replacement.id]
    assert all(decision.status is DecisionStatus.APPROVED for decision in after)
    contents = [decision.current_revision.content for decision in after]
    assert contents == ["La reunión es los jueves"]
    assert "martes" not in " ".join(contents)


@pytest.mark.integration
def test_the_observable_overview_shows_only_the_new_decision_as_current(tmp_path: Path) -> None:
    """Punto 9: lo que el panel de la interfaz lee como vigente."""
    fixture = _Fixture(tmp_path / "sirius.db")
    previous = fixture.approved_decision("La reunión es los martes")
    replacement = fixture.approved_decision("La reunión es los jueves")
    fixture.supersede.supersede(previous.id, replacement.id, confirmed=True)

    overview = fixture.overview.get_overview()

    assert [decision.id for decision in overview.current_decisions] == [replacement.id]
    assert previous.id not in [decision.id for decision in overview.current_decisions]
    assert previous.id not in [decision.id for decision in overview.proposed_decisions]


@pytest.mark.integration
def test_two_contradictory_decisions_are_never_superseded_automatically(tmp_path: Path) -> None:
    """Punto 10: la contradicción no autoriza una sustitución silenciosa.

    Se aprueban dos decisiones incompatibles y además se conversa con el
    proveedor, que es el único camino automático que existe. Nada sustituye.
    """
    database_path = tmp_path / "sirius.db"
    fixture = _Fixture(database_path)
    previous = fixture.approved_decision("La reunión es los martes")
    replacement = fixture.approved_decision("La reunión es los jueves")

    from sirius.application.send_message import SendMessageUseCase

    memory_repository = build_sqlite_memory_repository(database_path)
    project_repository = build_sqlite_project_repository(database_path)
    conversation_repository = build_sqlite_conversation_repository(database_path)
    ranking = RankRelevantKnowledgeUseCase(
        memory_repository=memory_repository,
        decision_repository=fixture.decisions,
        project_repository=project_repository,
        knowledge_search_repository=build_sqlite_knowledge_search_repository(database_path),
    )
    context_builder = ContextBuilder(
        identity_repository=build_sqlite_identity_repository(database_path),
        project_repository=project_repository,
        memory_repository=memory_repository,
        conversation_repository=conversation_repository,
        decision_repository=fixture.decisions,
        rank_relevant_knowledge_use_case=ranking,
        event_repository=build_sqlite_event_repository(database_path),
        token_counter=CharacterHeuristicTokenCounter(),
    )
    send = SendMessageUseCase(
        context_builder=context_builder,
        conversation_repository=conversation_repository,
        llm_provider=FakeLLMProvider(),
    )
    send.send_message("Esas dos decisiones se contradicen, ¿no?", operation_id="op-1")

    assert sorted(fixture.current_ids()) == sorted([previous.id, replacement.id])
    assert fixture.decisions.get_decision(previous.id).status is DecisionStatus.APPROVED
    assert fixture.decisions.get_decision(replacement.id).supersedes_decision_id is None


@pytest.mark.integration
def test_self_supersession_is_rejected(tmp_path: Path) -> None:
    """Punto 11."""
    fixture = _Fixture(tmp_path / "sirius.db")
    decision = fixture.approved_decision("La reunión es los martes")

    with pytest.raises(InvalidDecisionSupersessionError, match="cannot supersede itself"):
        fixture.supersede.supersede(decision.id, decision.id, confirmed=True)

    assert fixture.decisions.get_decision(decision.id).status is DecisionStatus.APPROVED
    assert fixture.current_ids() == [decision.id]


@pytest.mark.integration
def test_an_invalid_supersession_leaves_no_partial_change(tmp_path: Path) -> None:
    """Punto 12: distinto asunto, nada se escribe a medias."""
    fixture = _Fixture(tmp_path / "sirius.db")
    previous = fixture.approved_decision("La reunión es los martes")
    other_subject = fixture.proposed_decision("Usar SQLite", subject="Motor de persistencia")
    events_before = _supersession_events(fixture.database_path)

    with pytest.raises(InvalidDecisionSupersessionError, match="same subject and project"):
        fixture.supersede.supersede(previous.id, other_subject.id, confirmed=True)

    assert fixture.decisions.get_decision(previous.id).status is DecisionStatus.APPROVED
    assert fixture.decisions.get_decision(other_subject.id).status is DecisionStatus.PROPOSED
    assert fixture.decisions.get_decision(other_subject.id).supersedes_decision_id is None
    assert fixture.current_ids() == [previous.id]
    # Ni un evento de sustitución quedó registrado.
    assert _supersession_events(fixture.database_path) == events_before


@pytest.mark.integration
def test_repeating_the_same_supersession_is_rejected_in_a_controlled_way(tmp_path: Path) -> None:
    """Punto 13: la segunda vez se rechaza sin dejar nada a medias.

    El contrato actual no es idempotente: la anterior ya está SUSTITUIDA, y de
    ahí no hay camino de vuelta, así que repetir la orden es un error de
    dominio explícito y no un cambio silencioso.
    """
    fixture = _Fixture(tmp_path / "sirius.db")
    previous = fixture.approved_decision("La reunión es los martes")
    replacement = fixture.approved_decision("La reunión es los jueves")
    fixture.supersede.supersede(previous.id, replacement.id, confirmed=True)

    with pytest.raises(InvalidDecisionSupersessionError, match="Cannot supersede a decision"):
        fixture.supersede.supersede(previous.id, replacement.id, confirmed=True)

    assert fixture.decisions.get_decision(previous.id).status is DecisionStatus.SUPERSEDED
    assert fixture.decisions.get_decision(replacement.id).status is DecisionStatus.APPROVED
    assert fixture.decisions.get_decision(replacement.id).supersedes_decision_id == previous.id
    assert fixture.current_ids() == [replacement.id]


@pytest.mark.integration
def test_a_supersession_chain_never_closes_a_cycle(tmp_path: Path) -> None:
    """La cadena de sustituciones se puede recorrer siempre: nunca hay ciclo."""
    fixture = _Fixture(tmp_path / "sirius.db")
    first = fixture.approved_decision("Los martes")
    second = fixture.approved_decision("Los jueves")
    fixture.supersede.supersede(first.id, second.id, confirmed=True)
    third = fixture.approved_decision("Los viernes")
    fixture.supersede.supersede(second.id, third.id, confirmed=True)

    # La cadena es recorrible y termina.
    chain: list[int] = []
    current = fixture.decisions.get_decision(third.id)
    while current.supersedes_decision_id is not None:
        assert current.id not in chain
        chain.append(current.id)
        current = fixture.decisions.get_decision(current.supersedes_decision_id)
    assert chain == [third.id, second.id]
    assert current.id == first.id

    # Y una decisión ya sustituida no puede volver a ser la sustituta.
    with pytest.raises(InvalidDecisionSupersessionError):
        fixture.supersede.supersede(third.id, first.id, confirmed=True)


@pytest.mark.integration
def test_a_still_proposed_decision_can_also_supersede(tmp_path: Path) -> None:
    """El camino original de B4c sigue funcionando: sustituir también aprueba."""
    fixture = _Fixture(tmp_path / "sirius.db")
    previous = fixture.approved_decision("La reunión es los martes")
    proposal = fixture.proposed_decision("La reunión es los jueves")

    result = fixture.supersede.supersede(previous.id, proposal.id, confirmed=True)

    assert result.status is DecisionStatus.APPROVED
    assert result.supersedes_decision_id == previous.id
    assert fixture.current_ids() == [result.id]
