"""Capability Resolver v0 (arquitectura §6, incidencia #202: A4-P4 y A4-P5)."""

from __future__ import annotations

import pytest

from sirius_engine.capability_registry import load_capability_registry
from sirius_engine.capability_resolver import resolve_capabilities
from sirius_engine.domain.errors import CapabilityNotGrantedError, UnknownCapabilityError
from sirius_engine.domain.permission_envelope import PermissionEnvelope

_REGISTRO = load_capability_registry()


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
