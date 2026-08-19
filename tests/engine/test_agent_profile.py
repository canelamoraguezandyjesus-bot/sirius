"""AgentProfile versionado como dato (arquitectura §5.1, incidencia #202).

Perfiles reales: los tres roles del ciclo de programación
(implementer/reviewer/corrector) más el Auditor, cargados desde
``docs/implementation/work_engine/perfiles/``. Ninguna prueba aquí depende
de nombres de herramienta: solo de la forma del dato.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sirius_engine.domain.errors import UnknownAgentProfileError
from sirius_engine.profile_registry import load_agent_profile

_PERFILES_REALES = ("implementer", "reviewer", "corrector", "auditor")

_REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("ref", _PERFILES_REALES)
def test_carga_los_cuatro_perfiles_reales(ref: str) -> None:
    perfil = load_agent_profile(ref)
    assert perfil.ref == ref
    assert perfil.version >= 1
    assert perfil.mision.strip()
    assert perfil.capacidades
    assert perfil.contrato_entrada
    assert perfil.contrato_salida


@pytest.mark.parametrize("ref", _PERFILES_REALES)
def test_el_procedimiento_referenciado_existe_en_el_arbol(ref: str) -> None:
    """El perfil apunta al runbook real; no lo copia (para que no puedan divergir)."""
    perfil = load_agent_profile(ref)
    ruta_procedimiento = _REPO_ROOT / perfil.procedimiento_ref
    assert ruta_procedimiento.is_file(), (
        f"perfil {ref!r} referencia un procedimiento que no existe: {perfil.procedimiento_ref}"
    )


@pytest.mark.parametrize("ref", _PERFILES_REALES)
def test_ninguna_capacidad_es_un_nombre_de_herramienta_de_runtime(ref: str) -> None:
    """Alcance permitido: "un perfil describe qué puede hacer un rol, no con qué binario"."""
    nombres_de_herramienta_prohibidos = {
        "bash",
        "read",
        "write",
        "edit",
        "grep",
        "glob",
        "webfetch",
        "websearch",
    }
    perfil = load_agent_profile(ref)
    capacidades_en_minuscula = {c.lower() for c in perfil.capacidades}
    assert not (capacidades_en_minuscula & nombres_de_herramienta_prohibidos)


def test_perfil_desconocido_lanza_error_explicito() -> None:
    with pytest.raises(UnknownAgentProfileError):
        load_agent_profile("no-existe-este-perfil")


def test_carga_desde_un_directorio_alternativo(tmp_path: Path) -> None:
    (tmp_path / "propio.yml").write_text(
        "ref: propio\n"
        "version: 3\n"
        "mision: probar\n"
        "procedimiento_ref: README.md\n"
        "capacidades: [repo.leer]\n"
        "permisos:\n"
        "  escritura: null\n"
        "  red: false\n"
        "contrato_entrada: [x]\n"
        "contrato_salida: [y]\n",
        encoding="utf-8",
    )
    perfil = load_agent_profile("propio", perfiles_dir=tmp_path)
    assert perfil.version == 3
    assert perfil.capacidades == ("repo.leer",)


def test_ref_interno_distinto_del_nombre_de_fichero_es_un_error(tmp_path: Path) -> None:
    (tmp_path / "esperado.yml").write_text(
        "ref: otro\n"
        "version: 1\n"
        "mision: probar\n"
        "procedimiento_ref: README.md\n"
        "capacidades: [repo.leer]\n"
        "permisos:\n"
        "  escritura: null\n"
        "  red: false\n"
        "contrato_entrada: [x]\n"
        "contrato_salida: [y]\n",
        encoding="utf-8",
    )
    with pytest.raises(UnknownAgentProfileError):
        load_agent_profile("esperado", perfiles_dir=tmp_path)
