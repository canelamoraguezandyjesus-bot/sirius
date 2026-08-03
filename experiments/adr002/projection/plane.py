"""Plano comun de la proyeccion: lo que **solo** la capa comun puede abrir.

Implementa el protocolo ``PlanoComun`` del contrato comun sobre el fichero
``reservado.sqlite3``. Ningun candidato recibe esta clase ni la ruta que abre:
el motor la toma como parametro propio y nunca la pasa a ``candidatas()`` ni a
``leer()``.

Aqui vive la **unica** traduccion de vocabulario entre el corpus y el contrato
comun: el corpus dice ``CRITICO`` y el contrato dice ``CRITICA``. La traduccion
esta en la proyeccion, que conoce las dos partes, y no en la capa comun, que no
puede conocer el vocabulario del banco sin dejar de ser neutral.
"""

from __future__ import annotations

import sqlite3
from typing import Final

from experiments.adr002.candidates.common.contracts import (
    Criticidad,
    CriticidadAplicada,
)
from experiments.adr002.projection.contracts import (
    Plano,
    ProyeccionError,
    ProyeccionExperimental,
)

#: Traduccion cerrada del vocabulario de niveles. Un nivel del corpus que no
#: figure aqui **aborta**: elegir el «mas parecido» reinterpretaria el nivel, y
#: el traspaso a ``B05`` debe ser integro.
NIVELES: Final[dict[str, Criticidad]] = {
    "ORDINARIO": Criticidad.ORDINARIA,
    "IMPORTANTE": Criticidad.IMPORTANTE,
    "CRITICO": Criticidad.CRITICA,
}


class PlanoReservado:
    """Lectura de solo lectura del plano reservado, por identidad canonica."""

    def __init__(self, proyeccion: ProyeccionExperimental, consumidor: str = "common") -> None:
        self._conexion: sqlite3.Connection = proyeccion.abrir(Plano.RESERVADO, consumidor)
        self._propiedades: dict[str, str | None] = {
            str(f["identidad"]): (None if f["valor"] is None else str(f["valor"]))
            for f in self._conexion.execute("SELECT identidad, valor FROM property_key")
        }
        self._criticidad: dict[str, CriticidadAplicada] = {}
        for fila in self._conexion.execute(
            "SELECT identidad, nivel, razon_segura, fuente_de_politica, regla_de_politica "
            "FROM criticidad_aplicada WHERE nivel IS NOT NULL"
        ):
            bruto = str(fila["nivel"])
            if bruto not in NIVELES:
                msg = (
                    f"nivel de criticidad desconocido: {bruto!r}; la traduccion es "
                    f"cerrada y no elige el nivel mas parecido"
                )
                raise ProyeccionError(msg)
            self._criticidad[str(fila["identidad"])] = CriticidadAplicada(
                nivel=NIVELES[bruto],
                razon_segura=str(fila["razon_segura"]),
                fuente_de_politica=str(fila["fuente_de_politica"]),
                regla_de_politica=str(fila["regla_de_politica"]),
            )

    def close(self) -> None:
        self._conexion.close()

    def __enter__(self) -> PlanoReservado:
        return self

    def __exit__(self, *_excepcion: object) -> None:
        self.close()

    def property_key(self, identidad: str) -> str | None:
        """Ausente y nula son lo mismo aqui: ninguna de las dos agrupa."""
        return self._propiedades.get(identidad)

    def criticidad_aplicada(self, identidad: str) -> CriticidadAplicada | None:
        """Sin entrada congelada no hay nivel. Ninguna etapa puede crear uno."""
        return self._criticidad.get(identidad)


__all__ = ["NIVELES", "PlanoReservado"]
