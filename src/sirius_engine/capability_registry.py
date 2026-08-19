"""Registro versionado de capacidades del Capability Resolver v0 (arquitectura §6).

Dato, no código: vive en
``docs/implementation/work_engine/perfiles/registro_capacidades.yml``,
heredero directo del patrón cerrado de ``registro_de_acciones.yml`` (PR
#171): comparación siempre por NOMBRE de capacidad, sin degradar una
capacidad ausente a otra parecida. Una capacidad no registrada no se
resuelve (:mod:`sirius_engine.capability_resolver`).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

import yaml

_REGISTRO_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "implementation"
    / "work_engine"
    / "perfiles"
    / "registro_capacidades.yml"
)


@dataclass(frozen=True, slots=True)
class CapabilityDefinition:
    """Una entrada del registro: la capacidad y sus propiedades relevantes para el egress."""

    nombre: str
    #: Categoría abstracta de proveedor del diagrama de §6 (nunca un nombre
    #: de herramienta): p. ej. ``herramienta_nativa``, ``skill``, ``mcp``,
    #: ``api_cli``, ``funcion_local``, ``delegacion``.
    proveedor: str
    red: bool
    escritura: bool


@dataclass(frozen=True, slots=True)
class CapabilityRegistry:
    version: int
    capacidades: Mapping[str, CapabilityDefinition]

    def obtener(self, nombre: str) -> CapabilityDefinition | None:
        return self.capacidades.get(nombre)


def _campo_texto(datos: Mapping[str, object], campo: str, *, contexto: str) -> str:
    valor = datos.get(campo)
    if not isinstance(valor, str) or not valor:
        raise ValueError(f"{contexto}: el campo {campo!r} debe ser texto no vacío")
    return valor


def _campo_bool(datos: Mapping[str, object], campo: str, *, contexto: str) -> bool:
    valor = datos.get(campo, False)
    if not isinstance(valor, bool):
        raise ValueError(f"{contexto}: el campo {campo!r} debe ser booleano")
    return valor


def _cargar_definicion(nombre: str, datos: object) -> CapabilityDefinition:
    if not isinstance(datos, Mapping):
        raise ValueError(f"capacidad {nombre!r}: la entrada debe ser un mapeo")
    contexto = f"capacidad {nombre!r}"
    return CapabilityDefinition(
        nombre=nombre,
        proveedor=_campo_texto(datos, "proveedor", contexto=contexto),
        red=_campo_bool(datos, "red", contexto=contexto),
        escritura=_campo_bool(datos, "escritura", contexto=contexto),
    )


def load_capability_registry(path: Path | None = None) -> CapabilityRegistry:
    """Cargar el registro desde el YAML versionado.

    Determinista: mismo fichero -> mismo :class:`CapabilityRegistry`, sin
    depender del orden de iteración de ningún diccionario intermedio (el
    resultado se envuelve en ``MappingProxyType`` sobre un ``dict`` ya
    construido en el orden fijo del propio fichero YAML, que PyYAML preserva).
    """
    ruta = path or _REGISTRO_PATH
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, Mapping):
        raise ValueError(f"{ruta}: el registro debe ser un mapeo de nivel superior")
    version = datos.get("version")
    if not isinstance(version, int):
        raise ValueError(f"{ruta}: el campo 'version' debe ser un entero")
    capacidades_datos = datos.get("capacidades")
    if not isinstance(capacidades_datos, Mapping):
        raise ValueError(f"{ruta}: el campo 'capacidades' debe ser un mapeo")
    capacidades = {
        str(nombre): _cargar_definicion(str(nombre), definicion)
        for nombre, definicion in capacidades_datos.items()
    }
    return CapabilityRegistry(version=version, capacidades=MappingProxyType(capacidades))
