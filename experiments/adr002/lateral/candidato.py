"""`ADR002-A` mas un indice lateral consultado en `E1`."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Sequence
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


class ConIndiceLateral(CandidatoA):
    """Consulta un indice **aparte** y materializa por identidad por el puerto.

    No enumera el canon, no lee texto de fuera del puerto y no toca el indice
    medido. Lo lateral es un derivado, y se comporta como tal.
    """

    def __init__(
        self,
        ruta: Path,
        *,
        tabla: str,
        razon: str,
        senal: str,
        terminos_extra: Callable[[ContextoDeEtapa], Sequence[str]] | None = None,
    ) -> None:
        super().__init__()
        self._ruta = ruta
        self._tabla = tabla
        self._razon = razon
        self._senal = senal
        #: Terminos que se anaden a los de la consulta, decididos por quien
        #: construye el candidato a partir de **la peticion**, no del texto.
        self._terminos_extra = terminos_extra

    def candidatas(self, contexto: ContextoDeEtapa) -> Sequence[Candidata]:
        base = list(super().candidatas(contexto))
        if contexto.etapa is not Etapa.E1:
            return base
        terminos = list(lexical.terminos_significativos(contexto.peticion.consulta))[
            :TERMINOS_MAXIMOS
        ]
        if self._terminos_extra is not None:
            for extra in self._terminos_extra(contexto):
                if extra not in terminos:
                    terminos.append(extra)
        if not terminos:
            return base
        consulta = " OR ".join(f'"{t}"' for t in terminos)
        conexion = sqlite3.connect(f"file:{self._ruta}?mode=ro", uri=True)
        try:
            filas = conexion.execute(
                f"SELECT identidad FROM {self._tabla} "
                f"WHERE {self._tabla} MATCH ? LIMIT {FILAS_MAXIMAS}",
                (consulta,),
            ).fetchall()
        except sqlite3.OperationalError:
            filas = []
        finally:
            conexion.close()

        ya = set(contexto.ya_recuperados) | {c.item.id for c in base}
        nuevas = [str(f[0]) for f in filas if str(f[0]) not in ya]
        if not nuevas:
            return base
        extra: list[Candidata] = []
        for inicio in range(0, len(nuevas), LOTE):
            lote = tuple(nuevas[inicio : inicio + LOTE])
            for item in contexto.puerto.por_identificadores(lote).items:
                extra.append(
                    Candidata(
                        item=item,
                        etapa=Etapa.E1,
                        lectura=self.leer(item, contexto.peticion.consulta),
                        razon=self._razon,
                        senal=self._senal,
                    )
                )
        return [*base, *extra]


__all__ = ["FILAS_MAXIMAS", "LOTE", "TERMINOS_MAXIMOS", "ConIndiceLateral"]
