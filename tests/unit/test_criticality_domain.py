"""Unit tests for ``Criticality`` (M18b, ADR-126): exactly two members,
never a third, and ``None`` — ordinario, nadie la ha marcado — is not one of
them."""

from __future__ import annotations

import pytest

from sirius.domain.criticality import Criticality


def test_criticality_has_exactly_two_members() -> None:
    assert {member.value for member in Criticality} == {"CRITICO", "IMPORTANTE"}


def test_criticality_round_trips_the_canon_vocabulary() -> None:
    """``criticidad.nivel`` del banco de 47 casos usa literalmente estos dos
    valores (ver `tests/acceptance/fixtures/evidence_bank_47_casos.json`)."""
    assert Criticality("CRITICO") is Criticality.CRITICO
    assert Criticality("IMPORTANTE") is Criticality.IMPORTANTE


def test_an_unknown_level_is_not_a_valid_criticality() -> None:
    with pytest.raises(ValueError, match="ORDINARIO"):
        Criticality("ORDINARIO")
