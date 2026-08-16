"""`ADR002-A` mas uno o varios indices laterales consultados en `E1`."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from experiments.adr002.candidates.adr002_a import lexical
from experiments.adr002.candidates.adr002_a.candidate import CandidatoA
from experiments.adr002.candidates.common.contracts import Candidata, ContextoDeEtapa, Etapa

#: Cuantos terminos de la consulta se llevan al indice lateral, y cuantas filas
#: se traen. Los dos valores vienen de la version medida y **no se han tocado**:
#: cambiarlos ahora mezclaria el efecto del indice con el de otro ajuste.
TERMINOS_MAXIMOS: Final = 16
FILAS_MAXIMAS: Final = 64
LOTE: Final = 16


@dataclass(frozen=True, slots=True)
class Fuente:
    """Un indice lateral, con lo que aporta y con que se le pregunta.

    Cada fuente lleva **sus** terminos extra porque no se preguntan igual: al
    indice de categoria se le anaden las palabras de categoria cuando la
    peticion declara que ensambla contexto, y al indice de texto se le anaden
    las palabras que el modelo escribe al ver la consulta. Mezclarlas haria que
    una medida no fuera atribuible a ninguna de las dos.
    """

    ruta: Path
    tabla: str
    razon: str
    senal: str
    terminos_extra: Callable[[ContextoDeEtapa], Sequence[str]] | None = field(default=None)


class ConIndiceLateral(CandidatoA):
    """Consulta indices **aparte** y materializa por identidad por el puerto.

    No enumera el canon, no lee texto de fuera del puerto y no toca el indice
    medido. Lo lateral es un derivado, y se comporta como tal.
    """

    def __init__(self, fuentes: Sequence[Fuente]) -> None:
        super().__init__()
        self._fuentes = tuple(fuentes)

    def _identidades(self, fuente: Fuente, contexto: ContextoDeEtapa) -> list[str]:
        terminos = list(lexical.terminos_significativos(contexto.peticion.consulta))[
            :TERMINOS_MAXIMOS
        ]
        if fuente.terminos_extra is not None:
            for extra in fuente.terminos_extra(contexto):
                if extra not in terminos:
                    terminos.append(extra)
        if not terminos:
            return []
        consulta = " OR ".join(f'"{t}"' for t in terminos)
        conexion = sqlite3.connect(f"file:{fuente.ruta}?mode=ro", uri=True)
        try:
            filas = conexion.execute(
                f"SELECT identidad FROM {fuente.tabla} "
                f"WHERE {fuente.tabla} MATCH ? LIMIT {FILAS_MAXIMAS}",
                (consulta,),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        finally:
            conexion.close()
        return [str(f[0]) for f in filas]

    def candidatas(self, contexto: ContextoDeEtapa) -> Sequence[Candidata]:
        base = list(super().candidatas(contexto))
        if contexto.etapa is not Etapa.E1:
            return base
        ya = set(contexto.ya_recuperados) | {c.item.id for c in base}
        extra: list[Candidata] = []
        for fuente in self._fuentes:
            nuevas = [i for i in self._identidades(fuente, contexto) if i not in ya]
            if not nuevas:
                continue
            ya.update(nuevas)
            for inicio in range(0, len(nuevas), LOTE):
                lote = tuple(nuevas[inicio : inicio + LOTE])
                for item in contexto.puerto.por_identificadores(lote).items:
                    extra.append(
                        Candidata(
                            item=item,
                            etapa=Etapa.E1,
                            lectura=self.leer(item, contexto.peticion.consulta),
                            razon=fuente.razon,
                            senal=fuente.senal,
                        )
                    )
        return [*base, *extra]


__all__ = ["FILAS_MAXIMAS", "LOTE", "TERMINOS_MAXIMOS", "ConIndiceLateral", "Fuente"]
