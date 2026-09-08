"""Qué carriles están retirados, y con qué explicación (ADR-161, ejecutado por ADR-162).

La fuente de verdad es un dato versionado —
``docs/implementation/work_engine/carriles_retirados.json``— y no una constante
de código, por la misma razón que ``TABLA_ACTIVACION`` sí vive en código: aquella
concede permisos y derivarla de un fichero editable dejaría que el motor se los
concediera solos; esta los **quita**, y quitarlos tiene que poder hacerse —y
deshacerse— cambiando un dato y fusionando, sin tocar código ni pruebas. Es la
propiedad reversible que ADR-161 pedía.

El fichero es JSON y no YAML a propósito: los guiones que lo leen desde los
workflows corren con el ``python3`` a secas del runner, que no trae ``pyyaml``
(mismo motivo que ``scripts/automation/manifiesto.json``).

**Este módulo no decide nada**: informa. Quien rechaza es el despachador.

No importa nada de ``sirius_engine`` en tiempo de ejecución, y eso es
deliberado: ``scripts/automation/sirius_carril_retirado.py`` lo carga **por ruta
de fichero** desde los workflows, donde el proyecto no está instalado. Un import
interno lo rompería, y el mensaje dejaría de tener una sola redacción.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - solo para el comprobador de tipos
    from sirius_engine.domain.work_item import WorkItemClass

_REGISTRO = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "implementation"
    / "work_engine"
    / "carriles_retirados.json"
)


@dataclass(frozen=True, slots=True)
class CarrilRetirado:
    """Una entrada del registro: por qué se retiró y a dónde va ese trabajo ahora."""

    clase: str
    retirado_por: str
    ejecutado_por: str
    fecha: str
    motivo: str
    a_donde_va: str

    def explicacion(self) -> str:
        """El texto que ve quien intenta usar el carril. Una sola redacción para
        las tres piezas que lo publican, para que no puedan divergir."""
        return (
            f"El carril «{self.clase}» está retirado desde el {self.fecha} "
            f"({self.retirado_por}, ejecutado por {self.ejecutado_por}).\n"
            f"Motivo: {self.motivo}\n"
            f"A dónde va ahora: {self.a_donde_va}\n"
            "Nada se ha borrado: código, perfiles, informes, investigaciones, ADR e "
            "historial siguen en el repositorio. Reactivarlo es quitar su entrada de "
            "docs/implementation/work_engine/carriles_retirados.json y fusionar."
        )


@lru_cache(maxsize=1)
def _cargar(ruta: str) -> dict[str, CarrilRetirado]:
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    carriles: dict[str, CarrilRetirado] = {}
    for clase, fila in dict(datos.get("carriles", {})).items():
        carriles[clase] = CarrilRetirado(
            clase=clase,
            retirado_por=str(fila["retirado_por"]),
            ejecutado_por=str(fila["ejecutado_por"]),
            fecha=str(fila["fecha"]),
            motivo=str(fila["motivo"]),
            a_donde_va=str(fila["a_donde_va"]),
        )
    return carriles


def carriles_retirados(*, registro: Path | None = None) -> dict[str, CarrilRetirado]:
    """Todas las entradas del registro, indexadas por el valor de la clase."""
    return dict(_cargar(str(registro or _REGISTRO)))


def carril_retirado(
    clase: WorkItemClass | str, *, registro: Path | None = None
) -> CarrilRetirado | None:
    """La entrada de ``clase`` si está retirada, o ``None`` si sigue activa.

    Admite el enum y su valor en texto: el enum es lo que usa el motor, y el
    texto es lo que llega desde un workflow, que no puede importarlo.
    """
    valor = clase if isinstance(clase, str) else clase.value
    return carriles_retirados(registro=registro).get(valor)
