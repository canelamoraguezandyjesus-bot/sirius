"""AgentProfile versionado como dato (arquitectura §5.1, incidencia #202).

Perfiles reales, cargados desde ``docs/implementation/work_engine/perfiles/``.
La lista (``PERFILES_REALES``, en ``conftest.py``) se lee del propio
directorio (``glob``), no de una tupla escrita a mano en cada fichero, y la
comparten las cuatro suites de invariantes de perfiles
(test_agent_profile.py, test_capability_resolver.py,
test_permission_envelope.py, test_worker_request.py): un `.yml` nuevo con un
`procedimiento_ref` roto pasaría en verde si solo una de las cuatro lo viera
(incidencia #247, bloque C3b, hallazgos R8 y CODEX-002). Ninguna prueba aquí
depende de nombres de herramienta: solo de la forma del dato.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sirius_engine.domain.errors import UnknownAgentProfileError
from sirius_engine.profile_registry import load_agent_profile

from .conftest import PERFILES_REALES as _PERFILES_REALES

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_hay_perfiles_que_comprobar() -> None:
    """Un glob vacío dejaría toda la familia sin vigilancia y en verde."""
    assert len(_PERFILES_REALES) >= 4, "faltan perfiles en docs/implementation/work_engine/perfiles"


@pytest.mark.parametrize("ref", _PERFILES_REALES)
def test_carga_todos_los_perfiles_reales(ref: str) -> None:
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


def test_ambito_de_escritura_vacio_es_un_error(tmp_path: Path) -> None:
    """CODEX-001: una cadena vacía no es un ámbito de escritura válido -el
    resolver no debe poder confundirla con "sin escritura" (None) ni con un
    ámbito real."""
    (tmp_path / "vacio.yml").write_text(
        "ref: vacio\n"
        "version: 1\n"
        "mision: probar\n"
        "procedimiento_ref: README.md\n"
        "capacidades: [repo.escribir]\n"
        "permisos:\n"
        '  escritura: ""\n'
        "  red: false\n"
        "contrato_entrada: [x]\n"
        "contrato_salida: [y]\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="escritura"):
        load_agent_profile("vacio", perfiles_dir=tmp_path)


def test_ambito_de_escritura_solo_espacios_es_un_error(tmp_path: Path) -> None:
    """CODEX-003 (incidencia #202, ronda 4): un ámbito formado solo por
    espacios es tan inválido como la cadena vacía -truthy en Python, así que
    la comprobación anterior (que solo rechazaba la cadena vacía) lo dejaba
    pasar como si fuera un ámbito real."""
    (tmp_path / "espacios.yml").write_text(
        "ref: espacios\n"
        "version: 1\n"
        "mision: probar\n"
        "procedimiento_ref: README.md\n"
        "capacidades: [repo.escribir]\n"
        "permisos:\n"
        '  escritura: "   "\n'
        "  red: false\n"
        "contrato_entrada: [x]\n"
        "contrato_salida: [y]\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="escritura"):
        load_agent_profile("espacios", perfiles_dir=tmp_path)


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
