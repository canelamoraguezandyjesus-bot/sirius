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


def test_next_identity_version_increments() -> None:
    assert next_identity_version(_version(version=1)) == 2
    assert next_identity_version(_version(version=5)) == 6


def test_identity_is_immutable() -> None:
    identity = Identity(id=1, current_version=_version(), created_at=datetime.now(UTC))

    with pytest.raises(AttributeError):
        identity.current_version = _version(version=2)  # type: ignore[misc]
