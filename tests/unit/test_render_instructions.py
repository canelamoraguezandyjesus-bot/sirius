"""Unit tests for render_instructions() (B3b/B3c, D-02): the deterministic
"# Proyecto activo" section sent to the provider.

Pure and synchronous: builds a ``Context`` directly from domain dataclasses,
never touching SQLite, a repository, or a real/fake LLM provider.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sirius.application.context import Context
from sirius.application.send_message import render_instructions
from sirius.domain.decision import Decision, DecisionRevision, DecisionStatus
from sirius.domain.identity import Identity, IdentityVersion
from sirius.domain.project import Project, ProjectRevision, ProjectStatus, normalize_blockers

_NOW = datetime.now(UTC)


def _identity() -> Identity:
    version = IdentityVersion(
        id=1,
        identity_id=1,
        version=1,
        name="Sirius",
        description="descripción de identidad",
        personality_instructions="instrucciones de personalidad",
        created_at=_NOW,
    )
    return Identity(id=1, current_version=version, created_at=_NOW)


def _project(
    *, name: str = "Sirius 0.1", objective: str = "Cerrar B3b", blockers: str = ""
) -> Project:
    revision = ProjectRevision(
        id=1,
        project_id=1,
        version=1,
        objective=objective,
        state_summary="en curso",
        blockers=normalize_blockers(blockers),
        next_step="escribir pruebas",
        source_event_id=None,
        created_at=_NOW,
    )
    return Project(
        id=1,
        name=name,
        status=ProjectStatus.ACTIVE,
        current_revision=revision,
        created_at=_NOW,
        updated_at=_NOW,
        completed_at=None,
    )


def _decision(*, decision_id: int = 1, subject: str = "Motor de persistencia") -> Decision:
    revision = DecisionRevision(
        id=decision_id,
        decision_id=decision_id,
        version=1,
        content="Usar SQLite local",
        source_event_id=None,
        created_at=_NOW,
    )
    return Decision(
        id=decision_id,
        subject=subject,
        project_id=1,
        status=DecisionStatus.APPROVED,
        current_revision=revision,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _context(project: Project, decisions: tuple[Decision, ...] = ()) -> Context:
    return Context(
        identity=_identity(),
        project=project,
        decisions=decisions,
        memories=(),
        recent_messages=(),
        current_user_message="hola",
    )


def _context_without_project(decisions: tuple[Decision, ...] = ()) -> Context:
    return Context(
        identity=_identity(),
        project=None,
        decisions=decisions,
        memories=(),
        recent_messages=(),
        current_user_message="hola",
    )


def test_render_instructions_includes_the_project_name() -> None:
    text = render_instructions(_context(_project(name="Mi Proyecto")))

    assert "Nombre: Mi Proyecto" in text


def test_render_instructions_includes_the_project_objective() -> None:
    text = render_instructions(_context(_project(objective="Aprender Sirius")))

    assert "Objetivo: Aprender Sirius" in text


def test_render_instructions_includes_the_updated_current_state() -> None:
    revision = ProjectRevision(
        id=1,
        project_id=1,
        version=1,
        objective="objetivo",
        state_summary="estado actualizado",
        blockers=(),
        next_step="siguiente",
        source_event_id=None,
        created_at=_NOW,
    )
    project = Project(
        id=1,
        name="Sirius",
        status=ProjectStatus.ACTIVE,
        current_revision=revision,
        created_at=_NOW,
        updated_at=_NOW,
        completed_at=None,
    )

    text = render_instructions(_context(project))

    assert "Estado: estado actualizado" in text


def test_render_instructions_includes_the_updated_next_step() -> None:
    revision = ProjectRevision(
        id=1,
        project_id=1,
        version=1,
        objective="objetivo",
        state_summary="estado",
        blockers=(),
        next_step="siguiente paso actualizado",
        source_event_id=None,
        created_at=_NOW,
    )
    project = Project(
        id=1,
        name="Sirius",
        status=ProjectStatus.ACTIVE,
        current_revision=revision,
        created_at=_NOW,
        updated_at=_NOW,
        completed_at=None,
    )

    text = render_instructions(_context(project))

    assert "Siguiente paso: siguiente paso actualizado" in text


def test_render_instructions_includes_blockers_when_present() -> None:
    text = render_instructions(_context(_project(blockers="bloqueo uno\nbloqueo dos")))

    assert "Bloqueos: bloqueo uno\nbloqueo dos" in text


def test_render_instructions_uses_ninguno_registrado_when_blockers_is_empty() -> None:
    text = render_instructions(_context(_project(blockers="")))

    assert "Bloqueos: Ninguno registrado." in text


def test_render_instructions_project_section_never_mentions_decisions() -> None:
    """B3b's project section still excludes decisions — no fabricated
    content there. The dedicated "# Decisiones vigentes relacionadas"
    section (B6d) is a separate concern, covered below."""
    text = render_instructions(_context(_project()))

    project_section = text.split("# Proyecto activo\n", 1)[1].split("\n\n", 1)[0]
    assert "decisi" not in project_section.lower()


def test_render_instructions_includes_related_decisions_section() -> None:
    """B6d, SIRIUS-ARQ-0.1 S6.1: "decisiones vigentes relacionadas" is its
    own section, distinct from the project's own fields."""
    decision = _decision(decision_id=7, subject="Motor de persistencia")
    text = render_instructions(_context(_project(), decisions=(decision,)))

    assert "# Decisiones vigentes relacionadas" in text
    assert "- (7) [Motor de persistencia] Usar SQLite local" in text


def test_render_instructions_decisions_section_falls_back_safely_when_empty() -> None:
    """No current decisions is the safe, expected state — the header still
    renders, with no fabricated bullet."""
    text = render_instructions(_context(_project(), decisions=()))

    assert "# Decisiones vigentes relacionadas" in text
    assert (
        "- ("
        not in text.split("# Decisiones vigentes relacionadas\n", 1)[1].split(
            "# Memorias vigentes", 1
        )[0]
    )


def test_render_instructions_section_order_matches_sirius_arq_s6_1() -> None:
    decision = _decision()
    text = render_instructions(_context(_project(), decisions=(decision,)))

    identity_index = text.index("# Identidad")
    project_index = text.index("# Proyecto activo")
    decisions_index = text.index("# Decisiones vigentes relacionadas")
    memories_index = text.index("# Memorias vigentes")
    messages_index = text.index("# Mensajes recientes")

    assert identity_index < project_index < decisions_index < memories_index < messages_index


def test_render_instructions_project_section_order_matches_the_documented_format() -> None:
    text = render_instructions(_context(_project(name="N", objective="O", blockers="B")))

    section = text.split("# Proyecto activo\n", 1)[1].split("\n\n", 1)[0]
    lines = section.splitlines()
    assert lines[0].startswith("Nombre:")
    assert lines[1].startswith("Objetivo:")
    assert lines[2].startswith("Estado:")
    assert lines[3].startswith("Bloqueos:")
    assert lines[4].startswith("Siguiente paso:")


def test_render_instructions_omits_the_project_section_when_there_is_no_active_project() -> None:
    """SIRIUS-ARQ-0.1 S3 (LLMRequest.project_context: str | None): with zero
    configured ACTIVE projects, the section is absent entirely — no
    placeholder text, no fabricated project."""
    text = render_instructions(_context_without_project())

    assert "# Proyecto activo" not in text
    assert "Nombre:" not in text
    assert "Objetivo:" not in text


def test_render_instructions_still_includes_every_other_section_without_a_project() -> None:
    text = render_instructions(_context_without_project())

    assert "# Identidad" in text
    assert "# Decisiones vigentes relacionadas" in text
    assert "# Memorias vigentes" in text
    assert "# Mensajes recientes" in text
