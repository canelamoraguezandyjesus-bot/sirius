"""Puerto de escritura MÍNIMA en la vía GitHub (C2, incidencia #240).

El motor no tenía, hasta este bloque, ningún adapter que escribiera en
GitHub (``github_cli_mirror.py`` y ``github_actions_run_probe.py`` son de
solo lectura). Este puerto estrena esa capacidad con la disciplina que su
propio riesgo exige: **la escritura es mínima y enumerada**. Dos
operaciones, ni una más -crear la incidencia desde la plantilla y aplicar la
etiqueta de activación-; nada de comentar, cerrar, editar una incidencia
ajena ni tocar una PR (alcance permitido de la incidencia #240). Cualquier
verbo nuevo que un futuro bloque necesite es una decisión aparte, con su
propio ADR: no se amplía este puerto "ya que estamos".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class IncidenciaCreada:
    """Lo que devuelve crear una incidencia: lo mínimo para poder etiquetarla después."""

    numero: int
    url: str | None = None


class GitHubWriterPort(Protocol):
    """Contrato que cualquier escritor de la vía GitHub debe satisfacer.

    Exactamente dos operaciones -ver el docstring del módulo-. Una prueba
    estructural (``tests/engine/test_github_writer_port.py``) comprueba que
    este ``Protocol`` nunca gana un tercer método sin que alguien lo decida
    a propósito (C2-P4).
    """

    def crear_incidencia(
        self, *, repo: str, titulo: str, cuerpo: str, etiquetas: tuple[str, ...]
    ) -> IncidenciaCreada:
        """Crear una incidencia nueva desde el cuerpo ya proyectado. Ninguna otra escritura."""
        ...

    def aplicar_etiqueta(self, *, repo: str, numero: int, etiqueta: str) -> None:
        """Aplicar UNA etiqueta a una incidencia ya existente. Nunca la retira, nunca comenta."""
        ...

    def buscar_incidencia_por_work_id(self, *, repo: str, work_id: str) -> IncidenciaCreada | None:
        """La LECTURA de adopción de H-29 (auditoría #396), y ninguna más.

        No es una escritura: localiza la incidencia cuyo cuerpo declara
        ``## Work ID`` con ``work_id``, para que un reintento tras una caída
        ADOPTE el efecto ya producido en vez de duplicarlo. Se añadió con la
        justificación explícita que la prueba estructural del puerto exige:
        sin esta lectura, la intención durable solo sabría PARAR el reintento,
        nunca converger a una única incidencia. Devuelve ``None`` si no hay
        ninguna; los fallos de red se propagan -ante la duda, el llamador no
        crea nada-.
        """
        ...
