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
    """CLAUDE-REVISOR-001, remodelada en la ronda 4 (CODEX-001): si un
    perfil promete 'veredicto_json' en su contrato_salida, debe poder pedir
    'veredicto.escribir' y resolverla bajo su propio PermissionEnvelope.
    'veredicto.escribir' es una capacidad de escritura real
    (`escritura: true` en el registro) y exige un ámbito de escritura
    efectivo como cualquier otra -reviewer lo satisface con un ámbito
    acotado al canal del motor (`permisos.escritura: veredicto`), no con
    `repo`: eso no lo saca de ser de solo lectura del repositorio (ver
    ``test_reviewer_sigue_sin_poder_resolver_repo_escribir`` más abajo)."""
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


@pytest.mark.parametrize("nombre_capacidad", ["repo.escribir", "pr.crear"])
def test_un_ambito_de_escritura_acotado_no_cuela_una_capacidad_de_otro_ambito(
    nombre_capacidad: str,
) -> None:
    """CODEX-001 (incidencia #202, ronda 5): un ámbito de escritura no nulo
    ya no basta por sí solo para resolver cualquier capacidad de escritura
    -tiene que ser uno de los ámbitos que el registro declara compatibles
    con esa capacidad en concreto. Envelope construido directamente (no vía
    un perfil real) para probar el cruce que señaló la revisión: un ámbito
    acotado al canal del motor (``veredicto``) no resuelve ``repo.escribir``
    ni ``pr.crear``, que solo aceptan el ámbito ``repo``."""
    envelope = PermissionEnvelope(
        capacidades_concedidas=frozenset({nombre_capacidad}), escritura="veredicto", red=False
    )
    with pytest.raises(CapabilityNotGrantedError):
        resolve_capabilities(solicitadas=(nombre_capacidad,), envelope=envelope, registro=_REGISTRO)


@pytest.mark.parametrize("ambito", ["repo", "veredicto"])
def test_veredicto_escribir_resuelve_bajo_cualquiera_de_sus_dos_ambitos_compatibles(
    ambito: str,
) -> None:
    """`veredicto.escribir` declara `ambitos_escritura: [repo, veredicto]`
    en el registro -a diferencia de `repo.escribir`/`pr.crear`, que solo
    aceptan `repo`- porque tanto los perfiles de escritura amplia en el
    repositorio como el perfil de solo lectura con el ámbito acotado al
    canal del motor necesitan poder escribir el veredicto."""
    envelope = PermissionEnvelope(
        capacidades_concedidas=frozenset({"veredicto.escribir"}), escritura=ambito, red=False
    )
    (resuelta,) = resolve_capabilities(
        solicitadas=("veredicto.escribir",), envelope=envelope, registro=_REGISTRO
    )
    assert resuelta.nombre == "veredicto.escribir"


def test_reviewer_sigue_sin_poder_resolver_repo_escribir() -> None:
    """CODEX-001 (incidencia #202, ronda 4): darle a reviewer un ámbito de
    escritura no nulo (`veredicto`, para poder resolver 'veredicto.escribir')
    no debe colarle `repo.escribir` -la guarda general de escritura no se
    debilita, y lo que de verdad impide `repo.escribir` es que no está en la
    lista `capacidades` del perfil, con independencia del ámbito declarado."""
    perfil = load_agent_profile("reviewer")
    assert perfil.permisos.escritura is not None
    assert perfil.permisos.escritura != "repo"
    envelope = compute_permission_envelope(perfil)
    with pytest.raises(CapabilityNotGrantedError):
        resolve_capabilities(solicitadas=("repo.escribir",), envelope=envelope, registro=_REGISTRO)
