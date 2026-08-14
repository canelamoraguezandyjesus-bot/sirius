from datetime import UTC, datetime

import pytest

from sirius.domain.identity import (
    INITIAL_IDENTITY_DESCRIPTION,
    INITIAL_IDENTITY_NAME,
    INITIAL_PERSONALITY_INSTRUCTIONS,
    Identity,
    IdentityVersion,
    next_identity_version,
)


def _version(version: int = 1) -> IdentityVersion:
    return IdentityVersion(
        id=1,
        identity_id=1,
        version=version,
        name="Sirius",
        description="descripcion",
        personality_instructions="instrucciones",
        created_at=datetime.now(UTC),
    )


def test_canonical_seed_is_not_empty() -> None:
    assert INITIAL_IDENTITY_NAME == "Sirius"
    assert INITIAL_IDENTITY_DESCRIPTION.strip() != ""
    assert INITIAL_PERSONALITY_INSTRUCTIONS.strip() != ""


def test_canonical_seed_includes_the_external_actions_policy() -> None:
    """RF-035 "Sin acciones externas" (A-01, PA-024): the seed rejects
    requests to execute files, commands, web, or automations, since Sirius
    0.1 has no such capability (Producto S3/S5, S10)."""
    assert (
        "no ejecuta acciones externas y rechaza las solicitudes de ejecutar "
        "archivos, comandos, web o automatizaciones, por estar fuera del "
        "alcance de 0.1." in INITIAL_PERSONALITY_INSTRUCTIONS
    )


def test_next_identity_version_increments() -> None:
    assert next_identity_version(_version(version=1)) == 2
    assert next_identity_version(_version(version=5)) == 6


def test_identity_is_immutable() -> None:
    identity = Identity(id=1, current_version=_version(), created_at=datetime.now(UTC))

    with pytest.raises(AttributeError):
        identity.current_version = _version(version=2)  # type: ignore[misc]


# --- Humor y confianza (Manual §5.2 y Anexo A) --------------------------


def test_the_seed_authorises_the_humour_the_manual_approved() -> None:
    """El manual autoriza bromas, provocaciones e insultos consentidos.

    La semilla decía solo «humor contextual», que es más tibio que lo aprobado.
    """
    assert "insultos coloquiales consentidos" in INITIAL_PERSONALITY_INSTRUCTIONS
    assert "humor seco, sarcasmo" in INITIAL_PERSONALITY_INSTRUCTIONS


def test_the_seed_puts_the_fact_before_the_joke() -> None:
    """Principio de personalidad de SIRIUS-MODEL-STUDIO-UI-001 §4.1."""
    assert "Primero debe quedar claro qué ocurrió" in INITIAL_PERSONALITY_INSTRUCTIONS


def test_the_seed_turns_the_humour_off_when_something_breaks() -> None:
    """Anexo A del manual: error técnico serio reduce el humor."""
    assert "reduce el humor" in INITIAL_PERSONALITY_INSTRUCTIONS
    assert "pérdida de datos" in INITIAL_PERSONALITY_INSTRUCTIONS


def test_the_seed_names_forcing_jokes_as_a_failure() -> None:
    """Anexo A: el fallo de identidad es «forzar un chiste en cada mensaje»."""
    assert "Forzar un chiste en cada mensaje" in INITIAL_PERSONALITY_INSTRUCTIONS
