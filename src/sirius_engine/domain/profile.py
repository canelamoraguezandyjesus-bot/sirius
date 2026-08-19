"""AgentProfile: perfil de agente versionado como dato (arquitectura §5.1, §6).

Un perfil describe QUÉ puede hacer un rol -misión, procedimiento, capacidades
abstractas, permisos declarados y el contrato de entrada-salida- nunca CON QUÉ
herramienta concreta: los nombres de herramienta viven en el runtime del
Worker que ejecuta el procedimiento, no en el perfil (incidencia #202,
alcance permitido: "Sin nombres de herramienta concretos").

``ProfilePermissions`` es lo que el perfil DECLARA necesitar, no el permiso
efectivo de un Run: ese lo calcula el motor
(:mod:`sirius_engine.domain.permission_envelope`), nunca el propio perfil ni
el Worker.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProfilePermissions:
    """Permisos que el perfil declara necesitar (arquitectura §5.1)."""

    #: ``None`` = sin escritura; una cadena no vacía nombra el ámbito de
    #: escritura (p. ej. ``"repo"``). Nunca un booleano: un ámbito con nombre
    #: deja sitio a ámbitos más finos sin cambiar el tipo.
    escritura: str | None
    #: True si el perfil necesita alcanzar redes externas (``web.*``).
    red: bool


@dataclass(frozen=True, slots=True)
class AgentProfile:
    """Perfil de agente versionado (§5.1: ``AgentProfileRef(version/hash)``)."""

    ref: str
    version: int
    mision: str
    #: Ruta relativa al repo del procedimiento en texto (el runbook real);
    #: nunca el texto duplicado aquí, para que no pueda divergir de la fuente.
    procedimiento_ref: str
    #: Capacidades abstractas que el perfil pide, en el orden declarado
    #: -nunca un ``set``: el orden debe ser el mismo entre dos cargas para
    #: que la proyección sea determinista (A4-P1).
    capacidades: tuple[str, ...]
    permisos: ProfilePermissions
    contrato_entrada: tuple[str, ...]
    contrato_salida: tuple[str, ...]
