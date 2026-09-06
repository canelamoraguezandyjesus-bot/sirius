"""Doble de pruebas de :class:`GitHubMirrorPort` (A3, incidencia #193).

Se configura por respuesta exacta -una :class:`LecturaMetadatos`,
:class:`LecturaCuerpo`, :class:`LecturaComentarios`,
:class:`LecturaRunActions` o :class:`LecturaRunsEnVentana` por clave-, así una
prueba puede simular el fallo de un proveedor concreto sin tocar los demás
(requisito 2: «una prueba debe demostrarlo simulando el fallo de cada proveedor
por separado»). Una clave
sin configurar devuelve ``NO_DISPONIBLE`` en vez de fallar con
``KeyError``: un doble que no sabe qué responder está, con más razón,
"sin poder leer".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sirius_engine.ports.github_mirror import (
    LecturaComentarios,
    LecturaCuerpo,
    LecturaEstado,
    LecturaMetadatos,
    LecturaRunActions,
    LecturaRunsEnVentana,
)


@dataclass
class FixedGitHubMirrorReader:
    """Implementación de :class:`GitHubMirrorPort` respaldada por respuestas fijas."""

    metadatos_por_incidencia: dict[tuple[str, int], LecturaMetadatos] = field(default_factory=dict)
    cuerpos_por_incidencia: dict[tuple[str, int], LecturaCuerpo] = field(default_factory=dict)
    comentarios_por_incidencia: dict[tuple[str, int], LecturaComentarios] = field(
        default_factory=dict
    )
    runs_por_id: dict[tuple[str, str], LecturaRunActions] = field(default_factory=dict)
    #: Una ÚNICA respuesta por repositorio, no una por ventana: la ventana la
    #: calcula quien llama a partir de su `ahora` real, y obligar a una prueba a
    #: adivinar ese par de instantes exactos para configurar el doble no
    #: probaría nada sobre la ventana -solo sobre la aritmética de la propia
    #: prueba-. Un repositorio sin configurar sigue devolviendo NO_DISPONIBLE.
    runs_en_ventana_por_repo: dict[str, LecturaRunsEnVentana] = field(default_factory=dict)

    def leer_metadatos(self, *, repo: str, numero: int) -> LecturaMetadatos:
        return self.metadatos_por_incidencia.get(
            (repo, numero),
            LecturaMetadatos(estado=LecturaEstado.NO_DISPONIBLE, error="fixture sin configurar"),
        )

    def leer_cuerpo(self, *, repo: str, numero: int) -> LecturaCuerpo:
        return self.cuerpos_por_incidencia.get(
            (repo, numero),
            LecturaCuerpo(estado=LecturaEstado.NO_DISPONIBLE, error="fixture sin configurar"),
        )

    def leer_comentarios(self, *, repo: str, numero: int) -> LecturaComentarios:
        return self.comentarios_por_incidencia.get(
            (repo, numero),
            LecturaComentarios(estado=LecturaEstado.NO_DISPONIBLE, error="fixture sin configurar"),
        )

    def leer_run_actions(self, *, repo: str, run_id: str) -> LecturaRunActions:
        return self.runs_por_id.get(
            (repo, run_id),
            LecturaRunActions(estado=LecturaEstado.NO_DISPONIBLE, error="fixture sin configurar"),
        )

    def listar_runs_en_ventana(
        self, *, repo: str, desde: datetime, hasta: datetime
    ) -> LecturaRunsEnVentana:
        return self.runs_en_ventana_por_repo.get(
            repo,
            LecturaRunsEnVentana(
                estado=LecturaEstado.NO_DISPONIBLE, error="fixture sin configurar"
            ),
        )
