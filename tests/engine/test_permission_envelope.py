"""PermissionEnvelope: deny-by-default, calculado por el motor (arquitectura §5.1, §6.1).

Ningún camino público de :mod:`sirius_engine.domain.permission_envelope`
acepta un envelope construido por otra cosa que no sea
:func:`compute_permission_envelope` a partir de un ``AgentProfile`` -no hay
parámetro alguno que permita a un Worker declararse sus propios permisos.
"""

from __future__ import annotations

import pytest

from sirius_engine.domain.errors import EgressIncompatibleError
from sirius_engine.domain.permission_envelope import (
    ENVELOPE_VACIO,
    compute_permission_envelope,
)
from sirius_engine.domain.profile import AgentProfile, ProfilePermissions
from sirius_engine.profile_registry import load_agent_profile

from .conftest import PERFILES_REALES


def _perfil(*, capacidades: tuple[str, ...], escritura: str | None, red: bool) -> AgentProfile:
    return AgentProfile(
        ref="perfil-de-prueba",
        version=1,
        mision="probar",
        procedimiento_ref="README.md",
        capacidades=capacidades,
        permisos=ProfilePermissions(escritura=escritura, red=red),
        contrato_entrada=("x",),
        contrato_salida=("y",),
    )


def test_envelope_vacio_no_concede_nada() -> None:
    assert ENVELOPE_VACIO.capacidades_concedidas == frozenset()
    assert ENVELOPE_VACIO.escritura is None
    assert ENVELOPE_VACIO.red is False


def test_concede_exactamente_las_capacidades_declaradas_ni_una_mas() -> None:
    perfil = _perfil(capacidades=("repo.leer", "validaciones.ejecutar"), escritura=None, red=False)
    envelope = compute_permission_envelope(perfil)
    assert envelope.capacidades_concedidas == frozenset({"repo.leer", "validaciones.ejecutar"})
    assert envelope.escritura is None
    assert envelope.red is False


def test_perfil_sin_capacidades_produce_un_envelope_sin_capacidades() -> None:
    perfil = _perfil(capacidades=(), escritura=None, red=False)
    envelope = compute_permission_envelope(perfil)
    assert envelope.capacidades_concedidas == frozenset()


def test_red_y_escritura_irrestricta_a_la_vez_es_estructuralmente_incompatible() -> None:
    """Arquitectura §6.1 regla 1: la combinación no se degrada, no se resuelve."""
    perfil = _perfil(capacidades=("web.buscar",), escritura="repo", red=True)
    with pytest.raises(EgressIncompatibleError):
        compute_permission_envelope(perfil)


def test_red_sin_escritura_es_compatible() -> None:
    perfil = _perfil(capacidades=("web.buscar",), escritura=None, red=True)
    envelope = compute_permission_envelope(perfil)
    assert envelope.red is True
    assert envelope.escritura is None


@pytest.mark.parametrize("ref", PERFILES_REALES)
def test_todos_los_perfiles_reales_calculan_un_envelope_sin_incompatibilidad(ref: str) -> None:
    perfil = load_agent_profile(ref)
    envelope = compute_permission_envelope(perfil)
    assert envelope.capacidades_concedidas == frozenset(perfil.capacidades)
