"""Capability Resolver v0 (arquitectura §6, incidencia #202: A4-P4 y A4-P5)."""

from __future__ import annotations

import pytest

from sirius_engine.capability_registry import load_capability_registry
from sirius_engine.capability_resolver import resolve_capabilities
from sirius_engine.domain.errors import CapabilityNotGrantedError, UnknownCapabilityError
from sirius_engine.domain.permission_envelope import (
    PermissionEnvelope,
    compute_permission_envelope,
)
from sirius_engine.profile_registry import load_agent_profile

_REGISTRO = load_capability_registry()

_PERFILES_REALES = ("implementer", "reviewer", "corrector", "auditor")


def _envelope(*capacidades: str) -> PermissionEnvelope:
    return PermissionEnvelope(
        capacidades_concedidas=frozenset(capacidades), escritura=None, red=False
    )


def test_resuelve_capacidades_concedidas_en_el_orden_solicitado() -> None:
    envelope = _envelope("repo.leer", "validaciones.ejecutar")
    resueltas = resolve_capabilities(
        solicitadas=("validaciones.ejecutar", "repo.leer"),
        envelope=envelope,
        registro=_REGISTRO,
    )
    assert [r.nombre for r in resueltas] == ["validaciones.ejecutar", "repo.leer"]
    assert resueltas[0].proveedor == _REGISTRO.obtener("validaciones.ejecutar").proveedor  # type: ignore[union-attr]


def test_capacidad_no_registrada_no_se_resuelve() -> None:
    """A4-P4: pedir una capacidad ausente del registro no la resuelve, y el fallo es explícito."""
    envelope = _envelope("capacidad.inventada")
    with pytest.raises(UnknownCapabilityError):
        resolve_capabilities(
            solicitadas=("capacidad.inventada",), envelope=envelope, registro=_REGISTRO
        )


def test_capacidad_registrada_pero_no_concedida_impide_la_resolucion() -> None:
    """A4-P5: un envelope sin la capacidad pedida IMPIDE la resolución, nunca la degrada."""
    envelope = _envelope("repo.leer")  # no concede "repo.escribir"
    with pytest.raises(CapabilityNotGrantedError):
        resolve_capabilities(solicitadas=("repo.escribir",), envelope=envelope, registro=_REGISTRO)


def test_no_concede_una_version_recortada_de_la_capacidad() -> None:
    """Ninguna capacidad parcialmente concedida aparece en el resultado: todo o nada."""
    envelope = _envelope("repo.leer")
    with pytest.raises(CapabilityNotGrantedError):
        resolve_capabilities(
            solicitadas=("repo.leer", "repo.escribir"), envelope=envelope, registro=_REGISTRO
        )
    # La excepción se lanza antes de devolver ningún resultado parcial: no
    # hay forma de recuperar "repo.leer" ya resuelto de la llamada anterior.


def test_solicitud_vacia_resuelve_una_tupla_vacia() -> None:
    envelope = _envelope()
    assert resolve_capabilities(solicitadas=(), envelope=envelope, registro=_REGISTRO) == ()


def test_capacidad_de_red_no_se_resuelve_sin_envelope_con_red() -> None:
    """CODEX-002: nombrar la capacidad en capacidades_concedidas no basta si el
    envelope no autoriza red -el registro y los permisos efectivos deben cruzarse."""
    envelope = PermissionEnvelope(
        capacidades_concedidas=frozenset({"web.buscar"}), escritura=None, red=False
    )
    with pytest.raises(CapabilityNotGrantedError):
        resolve_capabilities(solicitadas=("web.buscar",), envelope=envelope, registro=_REGISTRO)


def test_capacidad_de_escritura_no_se_resuelve_sin_envelope_con_escritura() -> None:
    """CODEX-002: idéntica guarda para escritura -nombrar la capacidad no basta."""
    envelope = PermissionEnvelope(
        capacidades_concedidas=frozenset({"repo.escribir"}), escritura=None, red=False
    )
    with pytest.raises(CapabilityNotGrantedError):
        resolve_capabilities(solicitadas=("repo.escribir",), envelope=envelope, registro=_REGISTRO)


@pytest.mark.parametrize("ref", _PERFILES_REALES)
def test_el_artefacto_veredicto_json_es_resoluble_bajo_el_envelope_propio(ref: str) -> None:
    """CLAUDE-REVISOR-001: si un perfil promete 'veredicto_json' en su
    contrato_salida, debe poder pedir 'veredicto.escribir' y resolverla bajo
    su propio PermissionEnvelope -sin que eso exija ampliar su ámbito de
    escritura del repositorio (permisos.escritura no nulo). Perfiles de solo
    lectura (reviewer, auditor) deben poder cumplir su propio contrato de
    salida sin dejar de ser de solo lectura."""
    perfil = load_agent_profile(ref)
    if "veredicto_json" not in perfil.contrato_salida:
        pytest.skip(f"perfil {ref!r} no promete 'veredicto_json' en su contrato_salida")
    assert "veredicto.escribir" in perfil.capacidades, (
        f"perfil {ref!r} promete 'veredicto_json' pero no pide 'veredicto.escribir'"
    )
    envelope = compute_permission_envelope(perfil)
    (resuelta,) = resolve_capabilities(
        solicitadas=("veredicto.escribir",), envelope=envelope, registro=_REGISTRO
    )
    assert resuelta.nombre == "veredicto.escribir"
