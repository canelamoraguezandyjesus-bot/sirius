"""Carga de :class:`AgentProfile` versionados desde datos en el árbol (arquitectura §5.1).

Un fichero YAML por ``ref`` en ``docs/implementation/work_engine/perfiles/``;
el ``version`` vive DENTRO del fichero, no en su nombre. v0: un único
fichero activo por ``ref`` -varias versiones simultáneas del mismo perfil es
una ampliación posterior, no una decisión que tome este bloque.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import yaml

from sirius_engine.domain.errors import UnknownAgentProfileError
from sirius_engine.domain.profile import AgentProfile, ProfilePermissions

_PERFILES_DIR = (
    Path(__file__).resolve().parents[2] / "docs" / "implementation" / "work_engine" / "perfiles"
)


def _campo_texto(datos: Mapping[str, object], campo: str, *, contexto: str) -> str:
    valor = datos.get(campo)
    if not isinstance(valor, str) or not valor:
        raise ValueError(f"{contexto}: el campo {campo!r} debe ser texto no vacío")
    return valor


def _campo_entero(datos: Mapping[str, object], campo: str, *, contexto: str) -> int:
    valor = datos.get(campo)
    if not isinstance(valor, int) or isinstance(valor, bool):
        raise ValueError(f"{contexto}: el campo {campo!r} debe ser un entero")
    return valor


def _campo_lista_texto(
    datos: Mapping[str, object], campo: str, *, contexto: str
) -> tuple[str, ...]:
    valor = datos.get(campo)
    if not isinstance(valor, list) or not all(isinstance(item, str) for item in valor):
        raise ValueError(f"{contexto}: el campo {campo!r} debe ser una lista de texto")
    return tuple(valor)


def _cargar_permisos(datos: Mapping[str, object], *, contexto: str) -> ProfilePermissions:
    permisos_datos = datos.get("permisos")
    if not isinstance(permisos_datos, Mapping):
        raise ValueError(f"{contexto}: el campo 'permisos' debe ser un mapeo")
    escritura = permisos_datos.get("escritura")
    if escritura is not None and (not isinstance(escritura, str) or not escritura.strip()):
        raise ValueError(f"{contexto}: 'permisos.escritura' debe ser texto no vacío o nulo")
    red = permisos_datos.get("red", False)
    if not isinstance(red, bool):
        raise ValueError(f"{contexto}: 'permisos.red' debe ser booleano")
    return ProfilePermissions(escritura=escritura, red=red)


def _perfil_desde_datos(datos: Mapping[str, object], *, contexto: str) -> AgentProfile:
    return AgentProfile(
        ref=_campo_texto(datos, "ref", contexto=contexto),
        version=_campo_entero(datos, "version", contexto=contexto),
        mision=_campo_texto(datos, "mision", contexto=contexto),
        procedimiento_ref=_campo_texto(datos, "procedimiento_ref", contexto=contexto),
        capacidades=_campo_lista_texto(datos, "capacidades", contexto=contexto),
        permisos=_cargar_permisos(datos, contexto=contexto),
        contrato_entrada=_campo_lista_texto(datos, "contrato_entrada", contexto=contexto),
        contrato_salida=_campo_lista_texto(datos, "contrato_salida", contexto=contexto),
    )


def load_agent_profile(ref: str, *, perfiles_dir: Path | None = None) -> AgentProfile:
    """Cargar el perfil ``ref`` desde su fichero de datos versionado.

    Determinista: mismo fichero -> mismo :class:`AgentProfile`.
    :class:`~sirius_engine.domain.errors.UnknownAgentProfileError` si no hay
    fichero para ``ref``, o si el ``ref`` declarado dentro del fichero no
    coincide con el nombre pedido (protege contra un fichero mal renombrado).
    """
    directorio = perfiles_dir or _PERFILES_DIR
    ruta = directorio / f"{ref}.yml"
    if not ruta.is_file():
        raise UnknownAgentProfileError(ref)
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, Mapping):
        raise ValueError(f"{ruta}: el perfil debe ser un mapeo de nivel superior")
    perfil = _perfil_desde_datos(datos, contexto=str(ruta))
    if perfil.ref != ref:
        raise UnknownAgentProfileError(ref)
    return perfil
