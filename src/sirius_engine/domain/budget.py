"""Presupuesto de un WorkItem/Run: valor explícito, nunca leído de estado oculto.

Arquitectura §9 punto 9 ("Permisos y presupuesto": "límites de gasto/turnos/
tiempo; corte y escalado al agotar"). El límite declarado vive en
``WorkItem.limites["presupuesto"]["limite"]`` (dato fijado en la creación,
§3.1); el CONSUMO se sigue con :class:`Budget`, un valor inmutable que el
llamador conserva y pasa entre invocaciones -misma disciplina que ``now``
en todo el motor (arquitectura, dominio: nunca leído de un reloj real).

``Budget`` NO vive dentro de ``WorkItem.limites``: actualizarlo ahí
obligaría a pasar por ``change_work_item_scope``, que invalida y cancela
TODOS los Runs vivos del WorkItem como efecto colateral (arquitectura §3.2)
-correcto para un cambio real de alcance, catastrófico para la contabilidad
rutinaria de un gasto (ADR-042).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace


class BudgetExhaustedError(Exception):
    """Señal de que un gasto llevaría el presupuesto por debajo de cero.

    :func:`Budget.consumir` nunca lanza esto para un gasto que agota
    exactamente el presupuesto (``consumido == limite`` es un estado válido,
    ``agotado``); solo para un gasto que lo dejaría NEGATIVO, que no
    describe ningún coste real.
    """

    def __init__(self, limite: float, consumido: float, coste: float) -> None:
        super().__init__(
            f"no se puede registrar un gasto de {coste} sobre un presupuesto "
            f"con límite {limite} y consumido {consumido}: dejaría el consumo "
            "por debajo de cero"
        )
        self.limite = limite
        self.consumido = consumido
        self.coste = coste


@dataclass(frozen=True, slots=True)
class Budget:
    """Presupuesto inmutable: ``limite`` declarado, ``consumido`` hasta ahora."""

    limite: float
    consumido: float = 0.0

    def __post_init__(self) -> None:
        if self.limite < 0:
            raise ValueError(f"el límite de presupuesto no puede ser negativo: {self.limite}")
        if self.consumido < 0:
            raise ValueError(f"el consumo de presupuesto no puede ser negativo: {self.consumido}")

    @property
    def restante(self) -> float:
        return self.limite - self.consumido

    @property
    def agotado(self) -> bool:
        """Corte determinista: agotado en cuanto ``consumido >= limite``, nunca antes."""
        return self.consumido >= self.limite

    def consumir(self, coste: float) -> Budget:
        """Registrar un gasto. Nunca muta ``self``; devuelve un ``Budget`` nuevo."""
        if coste < 0:
            raise ValueError(f"el coste de un gasto no puede ser negativo: {coste}")
        return replace(self, consumido=self.consumido + coste)


def leer_limite_declarado(limites: Mapping[str, object]) -> float:
    """Leer el límite de presupuesto declarado en ``WorkItem.limites`` (§3.1).

    Es el único lugar que interpreta la forma ``{"presupuesto": {"limite":
    ...}}``: si la forma no coincide, falla explícito en vez de asumir un
    presupuesto ilimitado.
    """
    presupuesto = limites.get("presupuesto")
    if not isinstance(presupuesto, Mapping) or "limite" not in presupuesto:
        raise ValueError(
            "WorkItem.limites debe declarar {'presupuesto': {'limite': <numero>}} "
            f"para que el gobierno de A5 pueda seguir su consumo; recibido: {limites!r}"
        )
    limite = presupuesto["limite"]
    if not isinstance(limite, (int, float)) or isinstance(limite, bool):
        raise ValueError(f"'presupuesto.limite' debe ser numérico, recibido: {limite!r}")
    return float(limite)
