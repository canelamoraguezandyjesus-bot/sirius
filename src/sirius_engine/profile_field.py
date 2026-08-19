"""Campo declarativo ``Perfil: <ref>@<version>`` del cuerpo de un Work Item (arquitectura §5.1).

Retrocompatible por diseño: si el campo no está presente,
:func:`parse_perfil_field` devuelve ``None`` y el llamador decide el valor
por defecto de siempre -este módulo entrega solo la proyección y la lectura
del campo, nunca decide qué hacer si está ausente (incidencia #202, alcance
permitido). Conectar este campo al paso real de un workflow es C3, en
sesión interactiva (ADR-002); fuera de este bloque.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: "Perfil: <ref>@<version>" como línea propia dentro del cuerpo, en el
#: mismo estilo que el resto de campos de la plantilla de Work Item (p. ej.
#: "Rama base: main"). El ref sigue la misma forma de nombre de fichero que
#: usan los perfiles reales (minúsculas, dígitos, guion y guion bajo).
_PERFIL_FIELD_RE = re.compile(r"^Perfil:\s*([a-z][a-z0-9_-]*)@(\d+)\s*$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class ProfileRef:
    """Referencia versionada a un :class:`~sirius_engine.domain.profile.AgentProfile`."""

    ref: str
    version: int


def parse_perfil_field(cuerpo: str) -> ProfileRef | None:
    """Leer ``Perfil: <ref>@<version>`` del cuerpo de un Work Item.

    Devuelve ``None`` si el campo no está declarado -una incidencia sin este
    campo sigue siendo válida (retrocompatibilidad). Si aparece más de una
    vez, se queda con la primera ocurrencia, igual que el resto de campos de
    la plantilla no se repiten en la práctica.
    """
    match = _PERFIL_FIELD_RE.search(cuerpo)
    if match is None:
        return None
    return ProfileRef(ref=match.group(1), version=int(match.group(2)))


def project_perfil_field(profile_ref: ProfileRef) -> str:
    """Proyectar la línea ``Perfil: <ref>@<version>`` para el cuerpo de un Work Item."""
    return f"Perfil: {profile_ref.ref}@{profile_ref.version}"
