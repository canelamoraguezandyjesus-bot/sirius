"""Las piezas de una versión del robot y la marca de las pruebas que esperan una.

Cada versión del plan (``docs/evolution/PLAN_DEL_ROBOT.md``) entra por piezas,
una PR cada una, y sus pruebas de aceptación se escriben antes que el código
(§3 del plan). Una prueba de una pieza que no ha entrado no corre: su
``pieza(...)`` la para al empezar con ``PiezaPendiente``, bajo un ``xfail``
estricto que solo acepta esa excepción. Así la prueba falla por la razón
esperada o falla de verdad, nunca a medias: una prueba de una pieza tardía que
diera sus primeros pasos con lo que ya trajo otra anterior fallaría por una
aserción, y no por la pieza, el día que entrase la anterior (ADR-233).

Nació en el conductor de la 0.2 y se saca aquí para que la 0.3 y las siguientes
usen el mismo mecanismo, con el arreglo dentro, en vez de copiarlo.
"""

from __future__ import annotations

import functools
from collections.abc import Callable, Mapping
from typing import TypeVar, cast

import pytest

_Prueba = TypeVar("_Prueba", bound=Callable[..., object])


class PiezaPendiente(NotImplementedError):
    """La pieza que haría esto todavía no ha entrado."""

    def __init__(self, letra: str, adr: str, que_trae: str) -> None:
        super().__init__(f"pieza {letra} de {adr} pendiente: {que_trae}")
        self.letra = letra


class Piezas:
    """Las piezas de una versión: cuáles hay, qué trae cada una y cuáles han entrado.

    ``adr`` es el de la tabla de piezas; ``adr_de`` dice qué piezas vienen de
    otro, como la H de la 0.2, que decidió el propietario después (ADR-240).
    """

    def __init__(
        self,
        adr: str,
        piezas: Mapping[str, str],
        entregadas: frozenset[str],
        *,
        adr_de: Mapping[str, str] | None = None,
    ) -> None:
        self.adr = adr
        self.piezas: Mapping[str, str] = dict(piezas)
        self.entregadas = frozenset(entregadas)
        self._adr_de: Mapping[str, str] = dict(adr_de or {})
        desconocidas = sorted(self.entregadas - self.piezas.keys())
        if desconocidas:
            msg = f"{adr} no tiene las piezas {desconocidas}, y se dan por entregadas"
            raise ValueError(msg)

    def adr_de(self, letra: str) -> str:
        return self._adr_de.get(letra, self.adr)

    def pendiente(self, letra: str) -> PiezaPendiente:
        """La excepción que levanta el conductor donde la pieza ``letra`` aún no está."""
        return PiezaPendiente(letra, self.adr_de(letra), self.piezas[letra])

    def pieza(self, letra: str, que: str) -> Callable[[_Prueba], _Prueba]:
        """Marca una prueba como dependiente de la pieza ``letra``.

        Entregada la pieza, no hace nada y la prueba corre entera. Mientras no lo
        está, la prueba no corre: levanta ``PiezaPendiente`` al empezar, bajo un
        ``xfail`` estricto que solo acepta esa excepción. El cuerpo lo siguen
        comprobando ruff y mypy desde el primer día.
        """
        if letra not in self.piezas:
            msg = f"{self.adr} no tiene pieza {letra!r}"
            raise ValueError(msg)
        if letra in self.entregadas:
            return lambda prueba: prueba
        marca = pytest.mark.xfail(
            strict=True,
            raises=PiezaPendiente,
            reason=(
                f"Pieza {letra} de {self.adr_de(letra)} ({self.piezas[letra]}): {que}. Cuando "
                "entre, se añade su letra a PIEZAS_ENTREGADAS y esta marca desaparece."
            ),
        )

        def aplicar(prueba: _Prueba) -> _Prueba:
            @functools.wraps(prueba)
            def pendiente(*args: object, **kwargs: object) -> None:
                del args, kwargs
                raise self.pendiente(letra)

            return cast("_Prueba", marca(pendiente))

        return aplicar
