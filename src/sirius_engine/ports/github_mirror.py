"""Puerto de lectura de la vía GitHub para el espejo (A3, incidencia #193).

Tres proveedores separados -metadatos, cuerpo, comentarios- más uno para el
run de Actions, cada uno con su propio resultado ``LecturaEstado``. Están
separados a propósito, no fusionados en una única lectura "de la incidencia":
el requisito 2 exige poder simular el fallo de CADA proveedor por separado, y
un método único que internamente combine varias llamadas no podría exponer
cuál de ellas falló sin inventar una estructura de error compuesta.

Cada método devuelve ``estado=OK`` incluso cuando no hay nada que contar (p.
ej. una incidencia sin comentarios): eso es "leí y no hay". Solo
``estado=NO_DISPONIBLE`` significa "no pude leer". Los dos casos son tipos de
retorno distintos, nunca el mismo valor con distinto significado según el
contexto -que es exactamente el defecto que
``scripts/automation/sirius_reconcile.sh`` acumuló cinco veces (incidencia
#193, requisito 2).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol


class LecturaEstado(StrEnum):
    """Resultado de un intento de lectura: se pudo leer, o no se pudo."""

    OK = "ok"
    NO_DISPONIBLE = "no_disponible"


@dataclass(frozen=True, slots=True)
class Comentario:
    """Un comentario de la incidencia, con los metadatos que gobiernan la confianza."""

    autor_login: str
    autor_asociacion: str
    cuerpo: str
    creado_en: datetime


@dataclass(frozen=True, slots=True)
class MetadatosIncidencia:
    """Metadatos estructurales de la incidencia: no son texto libre de terceros."""

    numero: int
    titulo: str
    estado_gh: str
    etiquetas: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LecturaMetadatos:
    estado: LecturaEstado
    metadatos: MetadatosIncidencia | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class LecturaCuerpo:
    estado: LecturaEstado
    cuerpo: str | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class LecturaComentarios:
    estado: LecturaEstado
    comentarios: tuple[Comentario, ...] | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class RunActions:
    """Estado de un run de GitHub Actions, tal y como lo reporta la API."""

    run_id: str
    estado_run: str
    conclusion: str | None
    head_sha: str | None
    url: str | None


@dataclass(frozen=True, slots=True)
class LecturaRunActions:
    estado: LecturaEstado
    run: RunActions | None = None
    error: str | None = None


class GitHubMirrorPort(Protocol):
    """Contrato que cualquier lector de la vía GitHub debe satisfacer.

    Solo lectura: ningún método de este puerto escribe en GitHub, ni podría
    -no expone ninguna operación de escritura-. La implementación real
    (adapters/github_cli_mirror.py) y la de pruebas
    (adapters/fixture_mirror.py) son intercambiables detrás de este mismo
    contrato.
    """

    def leer_metadatos(self, *, repo: str, numero: int) -> LecturaMetadatos: ...

    def leer_cuerpo(self, *, repo: str, numero: int) -> LecturaCuerpo: ...

    def leer_comentarios(self, *, repo: str, numero: int) -> LecturaComentarios: ...

    def leer_run_actions(self, *, repo: str, run_id: str) -> LecturaRunActions: ...
